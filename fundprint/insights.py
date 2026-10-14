"""Two whole-portfolio views: each equity fund against its Nifty 50 twin, and
when the money went in against the Nifty 50's 52-week highs.

Both return percentages and labels only. Cost is used inside these functions
to weight things and is never returned as an amount.
"""
import re
from typing import NamedTuple

import numpy as np
import pandas as pd

from .xirr import xirr

NEAR_HIGH_FRACTION = 0.95   # "near a high" = within 5% of the 52-week high
HIGH_WINDOW_DAYS = 365      # the 52-week window, in calendar days
YOUNG_YEARS = 1.0           # average age under this: read absolute return, not XIRR
MAX_FUNDS = 12              # most funds shown in the twin chart
OTHER_MIN_SHARE = 5.0       # "Other" is listed only when it is at least this % of the money
TITLE_BAND_PP = 5.0         # a gap this close to the market counts as "close to random"

CLASS_ORDER = ["Equity", "Debt", "Commodity", "Other"]


def timing_class(asset_class):
    """Equity, Debt and Commodity stay as they are. Hybrid, Other and Unclassified become Other."""
    return asset_class if asset_class in CLASS_ORDER[:3] else "Other"


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


# ---- B. When did you buy? ----

def near_high(bench):
    """True on each benchmark date where the NAV is within 5% of its 52-week high."""
    nav = bench.set_index("date").nav
    return nav >= NEAR_HIGH_FRACTION * nav.rolling(f"{HIGH_WINDOW_DAYS}D").max()


class Timing(NamedTuple):
    purchases: pd.DataFrame     # date, nav, share (fraction of all money), cls, near
    near_pct: dict              # class -> % of that class's money bought near a high
    all_pct: float              # same, for all money together
    classes: list               # classes to list in the headline and legend, in order
    baseline_pct: float         # % of trading days near a high, first to last purchase
    levels: pd.DataFrame        # benchmark nav and near-high flag per date, indexed by date


def purchase_timing(cf, bench):
    """Where each held purchase sits against the Nifty 50's 52-week highs.

    `cf` is held_lots() output with an `asset_class` column, all funds.
    Returns None when no purchase falls inside the benchmark history.
    """
    buys = cf[(cf.amount < 0) & (cf.date >= bench.date.min())].astype({"date": "datetime64[ns]"})
    if buys.empty:
        return None
    near = near_high(bench)
    levels = pd.DataFrame({"date": near.index, "nav": bench.nav.to_numpy(), "near": near.to_numpy()})
    p = pd.merge_asof(buys.sort_values("date"), levels, on="date")
    p = pd.DataFrame({"date": p.date, "nav": p.nav, "near": p.near, "cost": -p.amount,
                      "cls": p.asset_class.map(timing_class)})
    p["share"] = p.cost / p.cost.sum()

    def pct(x):
        return 100 * x.cost[x.near].sum() / x.cost.sum()

    near_pct = {c: pct(x) for c, x in p.groupby("cls")}
    money = p.groupby("cls").share.sum() * 100
    classes = [c for c in CLASS_ORDER if c in near_pct and (c != "Other" or money[c] >= OTHER_MIN_SHARE)]
    window = near.loc[p.date.min():p.date.max()]
    baseline = 100 * window.mean() if len(window) else float("nan")
    return Timing(p.drop(columns="cost"), near_pct, pct(p), classes, baseline, levels.set_index("date"))


def headline_figure(t):
    """The class the title is judged on: Equity, or all money when there is no equity."""
    return t.near_pct.get("Equity", t.all_pct)


def timing_title(t):
    return title_for(headline_figure(t) - t.baseline_pct)


def title_for(diff):
    if diff > TITLE_BAND_PP:
        return "More of your money went in near market highs than random timing would suggest"
    if diff < -TITLE_BAND_PP:
        return "Less of your money went in near market highs than random timing would suggest"
    return "Your buying looks close to random timing"
