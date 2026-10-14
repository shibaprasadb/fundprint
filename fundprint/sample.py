"""A made-up portfolio for the "See it with sample data" button and for tests.

Nothing here comes from a real statement. Prices follow a seeded random walk,
so the output is the same every time.
"""
import numpy as np
import pandas as pd

from .parse import ParsedCas

# Per fund: name, isin, yearly drift, yearly volatility, years of monthly SIPs (0 = none),
# lump sums as (days ago, amount), sales as (days ago, share of the units held that day).
FUNDS = [
    ("Sample Flexi Cap Fund - Direct Growth", "INF000SAMPLE1", 0.14, 0.16, 6.0,
     [(2000, 100000.0), (700, 75000.0)], [(1100, 0.10), (200, 0.05)]),
    ("Sample Nifty 50 Index Fund - Direct Growth", "INF000SAMPLE2", 0.02, 0.14, 4.0,
     [(1500, 50000.0), (400, 50000.0)], [(250, 0.08)]),
    ("Sample Small Cap Fund - Direct Growth", "INF000SAMPLE3", 0.06, 0.24, 2.5,
     [(300, 40000.0)], []),
    ("Sample Short Duration Debt Fund - Direct Growth", "INF000SAMPLE4", 0.07, 0.01, 0,
     [(1300, 150000.0), (600, 100000.0), (130, 50000.0)], [(150, 0.15)]),
    ("Sample Gold ETF Fund of Fund - Direct Growth", "INF000SAMPLE5", 0.10, 0.15, 0,
     [(1000, 60000.0), (450, 40000.0)], []),
]
SIP_AMOUNT = 5000.0
# SIP day of the month per fund; the default is the 5th. The 30th lands on the 1st or 2nd in some months.
SIP_DAY = {"INF000SAMPLE2": 20, "INF000SAMPLE3": 30}


def sample_cas(today=None, seed=7):
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    rng = np.random.default_rng(seed)
    txns, schemes, first_dates = [], [], []
    for i, (name, isin, mu, sigma, sip_years, lumps, sales) in enumerate(FUNDS):
        folio = f"SAMPLE{i}"
        buys = [(d, "PURCHASE", amount) for d, amount in
                ((today - pd.Timedelta(days=ago), amount) for ago, amount in lumps)]
        if sip_years:
            start = today - pd.DateOffset(years=int(sip_years), months=int(sip_years % 1 * 12))
            sip_dates = pd.date_range(start, today - pd.DateOffset(months=1), freq="MS") + pd.Timedelta(days=SIP_DAY.get(isin, 5) - 1)
            buys += [(d, "PURCHASE_SIP", SIP_AMOUNT) for d in sip_dates]
        buys.sort(key=lambda b: b[0])
        first_dates.append(buys[0][0])

        days = pd.date_range(buys[0][0], today, freq="D")
        steps = rng.normal(mu / 365, sigma / np.sqrt(365), len(days))
        navs = pd.Series(100 * np.exp(np.cumsum(steps)), index=days)

        rows = [{"folio": folio, "scheme": name, "isin": isin, "date": d, "kind": kind,
                 "units": amount / navs[d], "amount": amount} for d, kind, amount in buys]
        # sales take a share of the units held that day (oldest units go first when the app counts them)
        for ago, share in sales:
            d = today - pd.Timedelta(days=ago)
            units = share * sum(r["units"] for r in rows if r["date"] <= d)
            rows.append({"folio": folio, "scheme": name, "isin": isin, "date": d,
                         "kind": "REDEMPTION", "units": -units, "amount": -units * navs[d]})
        txns += rows
        schemes.append({"folio": folio, "scheme": name, "isin": isin,
                        "nav": float(navs.iloc[-1]), "nav_date": today})
    return ParsedCas(pd.DataFrame(txns), pd.DataFrame(schemes), min(first_dates), today)


def sample_categories():
    """Matching rows for the sample funds, same shape as data/scheme_categories.json."""
    cats = ["Equity Scheme - Flexi Cap Fund", "Other Scheme - Index Funds",
            "Equity Scheme - Small Cap Fund", "Debt Scheme - Short Duration Fund",
            "Other Scheme - FoF Domestic"]
    classes = ["Equity", "Equity", "Equity", "Debt", "Commodity"]
    return {isin: {"amfi_code": str(900000 + i), "scheme_name": name,
                   "amfi_category": f"Open Ended Schemes({cats[i]})", "asset_class": classes[i]}
            for i, (name, isin, *_) in enumerate(FUNDS)}
