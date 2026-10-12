"""A made-up portfolio for the "Try with sample data" button and for tests.

Nothing here comes from a real statement. Prices follow a seeded random walk,
so the output is the same every time.
"""
import numpy as np
import pandas as pd

from .parse import ParsedCas

# (scheme name, isin, yearly drift, yearly volatility, monthly SIP years)
FUNDS = [
    ("Sample Flexi Cap Fund - Direct Growth", "INF000SAMPLE1", 0.14, 0.16, 6.0),
    ("Sample Nifty 50 Index Fund - Direct Growth", "INF000SAMPLE2", 0.11, 0.14, 4.0),
    ("Sample Small Cap Fund - Direct Growth", "INF000SAMPLE3", 0.18, 0.24, 2.5),
    ("Sample Liquid Fund - Direct Growth", "INF000SAMPLE4", 0.065, 0.005, 1.0),
]


def sample_cas(today=None, seed=7):
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    rng = np.random.default_rng(seed)
    txns, schemes, first_dates = [], [], []
    for i, (name, isin, mu, sigma, years) in enumerate(FUNDS):
        sip_dates = pd.date_range(today - pd.DateOffset(years=int(years), months=int(years % 1 * 12)),
                                  today - pd.DateOffset(months=1), freq="MS") + pd.Timedelta(days=4)
        first_dates.append(sip_dates[0])
        days = pd.date_range(sip_dates[0], today, freq="D")
        steps = rng.normal(mu / 365, sigma / np.sqrt(365), len(days))
        navs = pd.Series(100 * np.exp(np.cumsum(steps)), index=days)
        for d in sip_dates:
            amount = 5000.0
            txns.append({"folio": f"SAMPLE{i}", "scheme": name, "isin": isin, "date": d,
                         "kind": "PURCHASE_SIP", "units": amount / navs[d], "amount": amount})
        # sell a slice of the oldest units in the first fund, to exercise FIFO
        if i == 0:
            d = today - pd.Timedelta(days=200)
            txns.append({"folio": f"SAMPLE{i}", "scheme": name, "isin": isin, "date": d,
                         "kind": "REDEMPTION", "units": -30.0, "amount": -30.0 * navs[d]})
        schemes.append({"folio": f"SAMPLE{i}", "scheme": name, "isin": isin,
                        "nav": float(navs.iloc[-1]), "nav_date": today})
    return ParsedCas(pd.DataFrame(txns), pd.DataFrame(schemes), min(first_dates), today)


def sample_categories():
    """Matching rows for the sample funds, same shape as data/scheme_categories.json."""
    cats = ["Equity Scheme - Flexi Cap Fund", "Other Scheme - Index Funds",
            "Equity Scheme - Small Cap Fund", "Debt Scheme - Liquid Fund"]
    classes = ["Equity", "Equity", "Equity", "Debt"]
    return {isin: {"amfi_code": str(900000 + i), "scheme_name": name,
                   "amfi_category": f"Open Ended Schemes({cats[i]})", "asset_class": classes[i]}
            for i, (name, isin, *_) in enumerate(FUNDS)}
