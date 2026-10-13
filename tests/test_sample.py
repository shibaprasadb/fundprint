"""The made-up sample portfolio has to be varied enough that every chart and bucket shows something."""
import pandas as pd

from fundprint.classify import classify_isin
from fundprint.lots import ORDER, held_lots, summarise
from fundprint.sample import sample_cas, sample_categories

TODAY = pd.Timestamp("2026-10-13")


def test_sample_covers_years_of_sips_lump_sums_and_sales():
    p = sample_cas(TODAY)
    assert (TODAY - p.txns.date.min()).days > 5 * 365
    kinds = p.txns.kind.value_counts()
    assert kinds["PURCHASE_SIP"] > 50 and kinds["PURCHASE"] >= 3 and kinds["REDEMPTION"] >= 3
    assert (p.txns.groupby("scheme").units.sum() > 0).all()   # nothing sold that was never bought


def test_sample_has_equity_and_one_debt_fund():
    p, cats = sample_cas(TODAY), sample_categories()
    classes = [classify_isin(i, n, cats) for i, n in zip(p.schemes["isin"], p.schemes.scheme)]
    assert classes.count("Equity") >= 2 and classes.count("Debt") == 1


def test_every_bucket_has_something():
    p = sample_cas(TODAY)
    s = summarise(held_lots(p.txns, p.schemes, TODAY))
    assert list(s.index) == ORDER


def test_sample_passes_the_history_checks():
    """The sample goes through the same shape as a real statement: no units before the first purchase."""
    p = sample_cas(TODAY)
    first = p.txns.sort_values("date", kind="stable").groupby("scheme").head(1)
    assert (first.units > 0).all()
