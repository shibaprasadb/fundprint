"""Two whole-portfolio views: each equity fund against its Nifty 50 twin, and
how regular the investing has been.

Both return percentages and labels only. Cost is used inside these functions
to weight things and is never returned as an amount.
"""
import re
from typing import NamedTuple

import numpy as np
import pandas as pd

from .xirr import xirr

YOUNG_YEARS = 1.0           # average age under this: read absolute return, not XIRR
MAX_FUNDS = 12              # most funds shown in the twin chart

# ---- A. Which funds are ahead of their index twin? ----

_TRAILING = re.compile(
    r"\s*[-–]?\s*(direct plan|regular plan|direct|regular|growth option|growth|idcw|dividend|payout|reinvestment)\s*$",
    re.I)


def short_name(name):
    """'Axis Bluechip Fund - Direct Plan - Growth Option' -> 'Axis Bluechip Fund'."""
    n = re.sub(r"\(\s*(non[- ]?)?demat\s*\)", "", name, flags=re.I)
    n = re.sub(r"\s*[-–]\s*(direct|regular)\b.*$", "", n, flags=re.I)
    prev = None
    while prev != n:
        prev, n = n, _TRAILING.sub("", n)
    return n.strip(" -–") or name


class FundGaps(NamedTuple):
    table: pd.DataFrame     # name, share_%, gap_pp, young. Most ahead first.
    n_hidden: int           # equity funds left out because only the largest MAX_FUNDS are shown


def _twin(buys, bench):
    """Benchmark units bought on each purchase date, as a column next to the buys."""
    b = pd.merge_asof(buys.sort_values("date"), bench, on="date", suffixes=("", "_bench"))
    return b.assign(idx_units=-b.amount / b.nav)


def fund_gaps(cf, bench, today, max_funds=MAX_FUNDS):
    """Per equity fund: gap to its Nifty 50 twin, in percentage points.

    `cf` is held_lots() output with an `asset_class` column. The same fund in
    several folios is one fund. Lots older than the benchmark history are left out.
    """
    cf = cf[cf.asset_class == "Equity"]
    cf = cf[~cf.lot.isin(cf.loc[(cf.amount < 0) & (cf.date < bench.date.min()), "lot"])]
    last = bench.iloc[-1]
    today = pd.Timestamp(today)
    rows = []
    for _, g in cf.groupby(cf["isin"].fillna(cf.scheme), sort=False):
        buys = g[g.amount < 0].astype({"date": "datetime64[ns]"})
        cost = -buys.amount
        twin = _twin(buys, bench)
        value_now = g.amount[g.amount > 0].sum()
        twin_now = twin.idx_units.sum() * last.nav
        age = np.average((today - buys.date).dt.days / 365.25, weights=cost)
        young = age < YOUNG_YEARS
        if young:
            gap = 100 * (value_now / cost.sum() - twin_now / cost.sum())
        else:
            twin_cf = pd.concat([buys[["date", "amount"]],
                                 pd.DataFrame({"date": [last.date], "amount": [twin_now]})])
            gap = 100 * (xirr(g.date, g.amount) - xirr(twin_cf.date, twin_cf.amount))
        rows.append({"name": short_name(g.scheme.iloc[0]), "cost": cost.sum(), "gap_pp": gap, "young": bool(young)})

    t = pd.DataFrame(rows, columns=["name", "cost", "gap_pp", "young"]).dropna(subset=["gap_pp"])
    n_hidden = max(len(t) - max_funds, 0)
    t = t.nlargest(max_funds, "cost")
    t["share_%"] = 100 * t.cost / t.cost.sum() if len(t) else np.nan
    t = t.sort_values("gap_pp", ascending=False)[["name", "share_%", "gap_pp", "young"]].reset_index(drop=True)
    return FundGaps(t, n_hidden)


def gaps_title(t):
    return f"{int((t.gap_pp > 0).sum())} of {len(t)} equity funds are ahead of their Nifty 50 twin"


# ---- B. How regular is your investing? ----

PERIODICITY_GROUP = "fund"        # "fund": usual day worked out per fund. "all": one usual day for everything.
PERIODICITY_WINDOW_DAYS = 5       # a purchase is periodic within this many days of the usual day
PERIODICITY_MIN_PURCHASES = 3     # a group needs this many purchases in its zone to count as a pattern
MAX_USUAL_DAYS = 3                # usual days named in the subtitle before "and others"
MONTH_DAYS = 31                   # the month is treated as a circle of 31 days

PURCHASE_KINDS = ("PURCHASE", "PURCHASE_SIP")


def counted_purchases(txns):
    """Purchases the investor made, still counted if sold since.

    Reinvested dividends, switch-ins, STP transfers and rows without units are left out,
    and so is a purchase together with the reversal that cancelled it.
    """
    t = txns[txns.units.gt(0) & txns.kind.isin(PURCHASE_KINDS) | (txns.kind == "REVERSAL")]
    keep = []
    for _, g in t.groupby(["folio", "scheme"], sort=False):
        g = g.sort_values("date", kind="stable")
        buys = g[g.kind.isin(PURCHASE_KINDS)]
        for _, r in g[g.kind == "REVERSAL"].iterrows():
            match = buys[(buys.date <= r.date) & ((buys.units + r.units).abs() < 0.001)]
            if len(match):
                buys = buys.drop(match.index[-1])
        keep.append(buys)
    if not keep:
        return txns.iloc[0:0]
    return pd.concat(keep).sort_values("date", kind="stable")


def day_distance(d, m):
    """Days between two days of the month, counting round the month end: 30th and 2nd are 3 apart."""
    gap = abs(d - m)
    return min(gap, MONTH_DAYS - gap)


def _usual_day(days):
    """The most common day of the month. Ties go to the day whose zone holds most purchases, then the earliest."""
    counts = days.value_counts()
    tied = counts[counts == counts.max()].index
    cover = {m: int((days.map(lambda d: day_distance(d, m)) <= PERIODICITY_WINDOW_DAYS).sum()) for m in tied}
    return min(tied, key=lambda m: (-cover[m], m))


class Periodicity(NamedTuple):
    purchases: pd.DataFrame   # date, nav, periodic
    pct: int                  # % of purchases (by count) that were periodic
    usual_days: list          # day of month, most purchases covered first
    levels: pd.DataFrame      # benchmark nav per date, indexed by date


def periodicity(txns, bench):
    """Mark each purchase periodic or one-off. None when there are no purchases inside the benchmark history."""
    p = counted_purchases(txns)
    p = p[p.date >= bench.date.min()]
    if p.empty:
        return None
    p = p.assign(day=p.date.dt.day, group=p["isin"].fillna(p.scheme) if PERIODICITY_GROUP == "fund" else "all",
                 periodic=False)
    covered = {}   # usual day -> purchases it covers
    for _, g in p.groupby("group", sort=False):
        usual = _usual_day(g.day)
        in_zone = g.day.map(lambda d: day_distance(d, usual)) <= PERIODICITY_WINDOW_DAYS
        if in_zone.sum() >= PERIODICITY_MIN_PURCHASES:
            p.loc[g.index[in_zone], "periodic"] = True
            covered[usual] = covered.get(usual, 0) + int(in_zone.sum())

    levels = bench[["date", "nav"]]
    p = pd.merge_asof(p.astype({"date": "datetime64[ns]"}).sort_values("date"), levels, on="date")
    usual_days = sorted(covered, key=lambda d: (-covered[d], d))
    return Periodicity(p[["date", "nav", "periodic"]], int(round(100 * p.periodic.mean())),
                       usual_days, levels.set_index("date"))


def ordinal(n):
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"the {n}{suffix}"


def periodicity_title(pr):
    if not pr.usual_days:
        return "Your transactions don't follow a regular monthly pattern"
    return f"{pr.pct}% of your transactions followed a regular pattern"


def periodicity_subtitle(pr):
    """Two short lines: what periodic means, then the usual day(s). Nothing else."""
    if not pr.usual_days:
        return ""
    line = f"Made within {PERIODICITY_WINDOW_DAYS} days of your usual investing day for that fund."
    shown = [ordinal(d) for d in pr.usual_days[:MAX_USUAL_DAYS]]
    if len(pr.usual_days) == 1:
        return f"{line}\nYour usual day: {shown[0]}."
    more = " and others" if len(pr.usual_days) > MAX_USUAL_DAYS else ""
    return f"{line}\nYour usual days: {', '.join(shown)}{more}."
