"""Work out which purchases are still held, put them in age buckets,
and summarise each bucket.

Ported from the reference notebook (cells "Work out which purchases are
still held" and "XIRR for each bucket").
"""
import numpy as np
import pandas as pd

from .xirr import xirr

# Bucket edges in years. One list, so a later version can let users change it.
BUCKET_EDGES = [(1, "<1Y"), (3, "1-3Y"), (5, "3-5Y")]
LAST_BUCKET = "5Y+"
ORDER = [LAST_BUCKET] + [name for _, name in reversed(BUCKET_EDGES)]  # oldest first

CF_COLUMNS = ["lot", "bucket", "date", "amount", "folio", "scheme", "isin"]


def bucket_for(age_years, edges=BUCKET_EDGES, last=LAST_BUCKET):
    for limit, name in edges:
        if age_years < limit:
            return name
    return last


def held_lots(txns, schemes, today, edges=BUCKET_EDGES, last=LAST_BUCKET):
    """Two cash flows per purchase that is still held.

    - money out on the purchase date (only the share of units still held)
    - money in on the NAV date: units still held x latest NAV
    Both rows share a `lot` id so they can be kept or dropped together.
    """
    today = pd.Timestamp(today)
    nav = schemes.set_index(["folio", "scheme"])
    rows, lot_id = [], 0
    for (folio, scheme), g in txns.groupby(["folio", "scheme"], sort=False):
        g = g.sort_values("date", kind="stable")
        buys = g[g.units > 0].copy()

        # A reversal (bounced SIP, failed payment) cancels one specific
        # earlier purchase, so remove that purchase instead of counting a sale.
        for i, r in g[g.kind == "REVERSAL"].iterrows():
            match = buys[(buys.date <= r.date) & ((buys.units + r.units).abs() < 0.001)]
            if len(match):
                buys = buys.drop(match.index[-1])
                g = g.drop(i)

        # Units sold or switched out
        sold = -g.loc[g.units < 0, "units"].sum()

        # First in, first out: the oldest purchases are sold first.
        buys["held"] = (buys.units.cumsum() - sold).clip(lower=0).clip(upper=buys.units)
        buys = buys[buys.held > 0.001]

        latest_nav, nav_date = nav.loc[(folio, scheme), ["nav", "nav_date"]]
        isin = g["isin"].iloc[0]
        for d, u, a, h in zip(buys.date, buys.units, buys.amount, buys.held):
            b = bucket_for((today - d).days / 365.25, edges, last)
            lot_id += 1
            rows.append((lot_id, b, d, -a * h / u, folio, scheme, isin))
            rows.append((lot_id, b, nav_date, h * latest_nav, folio, scheme, isin))
    return pd.DataFrame(rows, columns=CF_COLUMNS)


def summarise(cf, order=ORDER):
    """Per bucket: invested, value, xirr_%, abs_%, share_%.

    `invested` and `value` are working numbers for the maths only. They must
    never be shown to the user (v1 shows percentages only).
    """
    out = {}
    for b, x in cf.groupby("bucket"):
        inv = -x.amount[x.amount < 0].sum()
        val = x.amount[x.amount > 0].sum()
        out[b] = {
            "invested": inv,
            "value": val,
            "xirr_%": 100 * xirr(x.date, x.amount),
            "abs_%": 100 * (val / inv - 1) if inv else np.nan,
        }
    df = pd.DataFrame.from_dict(out, orient="index", columns=["invested", "value", "xirr_%", "abs_%"])
    df["share_%"] = 100 * df.invested / df.invested.sum() if len(df) else np.nan
    return df.reindex([b for b in order if b in df.index])
