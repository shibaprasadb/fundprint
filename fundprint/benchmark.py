"""Replay the same purchases, on the same dates, into an index fund.

This is the "Public Market Equivalent" idea: if each rupee you invested had
gone into the index fund that day instead, what would it be worth now?
"""
import pandas as pd

from .lots import ORDER, summarise

# One constant so more benchmarks can be added later.
BENCH = 120716  # AMFI code: UTI Nifty 50 Index Fund - Direct Plan - Growth

PUBLIC_COLUMNS = [
    "share_%", "my_xirr_%", "nifty_xirr_%", "xirr_gap_%", "my_abs_%", "nifty_abs_%",
]


def load_bench(rows):
    """[{date, nav}, ...] -> DataFrame sorted by date."""
    b = pd.DataFrame(rows)
    b["date"] = pd.to_datetime(b["date"]).astype("datetime64[ns]")
    b["nav"] = b["nav"].astype(float)
    return b.sort_values("date").reset_index(drop=True)


def compare(cf, bench, order=ORDER):
    """Your buckets next to the index fund.

    Returns (table, n_excluded). The table has percentages only. Lots bought
    before the benchmark's history starts are left out of BOTH sides, and
    counted in n_excluded, so the comparison stays like for like.
    """
    last = bench.iloc[-1]
    buys = cf[cf.amount < 0].astype({"date": "datetime64[ns]"}).sort_values("date")
    early = buys.date < bench.date.min()
    excluded_lots = set(buys.loc[early, "lot"])
    cf = cf[~cf.lot.isin(excluded_lots)]
    buys = buys[~early]
    if cf.empty:
        return pd.DataFrame(columns=PUBLIC_COLUMNS), len(excluded_lots)

    # benchmark NAV on the purchase day, or the last trading day before it
    buys = pd.merge_asof(buys, bench, on="date")
    buys["idx_units"] = -buys.amount / buys.nav
    bench_cf = pd.concat([
        buys[["bucket", "date", "amount"]],
        buys.groupby("bucket").idx_units.sum().mul(last.nav).rename("amount")
            .reset_index().assign(date=last.date),
    ])

    mine, nifty = summarise(cf, order), summarise(bench_cf, order)
    table = pd.DataFrame({
        "share_%": mine["share_%"],
        "my_xirr_%": mine["xirr_%"],
        "nifty_xirr_%": nifty["xirr_%"],
        "xirr_gap_%": mine["xirr_%"] - nifty["xirr_%"],
        "my_abs_%": mine["abs_%"],
        "nifty_abs_%": nifty["abs_%"],
    })
    return table[PUBLIC_COLUMNS], len(excluded_lots)
