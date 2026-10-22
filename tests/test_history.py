"""Spec 006: statements that start after the first purchase. Warn, don't block. Made-up data only."""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from fundprint.benchmark import load_bench
from fundprint.history import HistoryIssues, history_issues, plain, warning_text
from fundprint.insights import periodicity
from fundprint.lots import held_lots
from fundprint.parse import ParsedCas, from_dict

TODAY = pd.Timestamp("2026-01-01")
NAME = "Alpha Flexi Cap Fund - Direct Plan - Growth"


def parsed(funds):
    """funds: list of (name, open, close, rows) with rows as (date, kind, units, amount)."""
    txns, schemes = [], []
    for i, (name, open_units, close, rows) in enumerate(funds):
        folio = f"F{i}"
        schemes.append({"folio": folio, "scheme": name, "isin": f"INF{i}", "nav": 10.0, "nav_date": TODAY,
                        "open": open_units, "close": close})
        txns += [{"folio": folio, "scheme": name, "isin": f"INF{i}", "date": pd.Timestamp(d), "kind": k,
                  "units": u, "amount": a} for d, k, u, a in rows]
    cols = ["folio", "scheme", "isin", "date", "kind", "units", "amount"]
    return ParsedCas(pd.DataFrame(txns, columns=cols), pd.DataFrame(schemes), None, TODAY)


def held_units(p):
    cf = held_lots(p.txns, p.schemes, TODAY)
    return (cf[cf.amount > 0].amount / 10.0).round(6).tolist()


def test_merger_switch_in_first_with_open_zero_is_not_partial():
    rows = [("2021-03-01", "SWITCH_IN_MERGER", 50.0, 500.0), ("2022-01-05", "PURCHASE_SIP", 10.0, 100.0)]
    p = parsed([(NAME, 0.0, 60.0, rows)])
    assert not history_issues(p)
    assert warning_text(history_issues(p)) == ""
    assert held_units(p) == [50.0, 10.0]


def test_open_balance_without_sales_is_left_out_and_named():
    rows = [("2022-01-05", "PURCHASE", 10.0, 100.0), ("2023-01-05", "PURCHASE", 5.0, 60.0)]
    p = parsed([(NAME, 40.0, 55.0, rows)])
    assert held_units(p) == [10.0, 5.0]           # the 40 opening units aren't there
    issues = history_issues(p)
    assert issues.partial == ["Alpha Flexi Cap Fund"] and issues.unreconciled == []
    text = warning_text(issues)
    assert "Some of your history is missing." in text and "- Alpha Flexi Cap Fund" in text


def test_sale_uses_opening_units_first_then_earliest_purchase():
    rows = [("2022-01-05", "PURCHASE", 10.0, 100.0),
            ("2023-01-05", "PURCHASE", 10.0, 120.0),
            ("2024-01-05", "REDEMPTION", -15.0, -200.0)]   # 8 opening units, then 7 from the first purchase
    p = parsed([(NAME, 8.0, 13.0, rows)])
    cf = held_lots(p.txns, p.schemes, TODAY)
    buys = cf[cf.amount < 0].sort_values("date")
    assert buys.date.tolist() == [pd.Timestamp("2022-01-05"), pd.Timestamp("2023-01-05")]
    assert (-buys.amount).tolist() == pytest.approx([100.0 * 3 / 10, 120.0])
    assert held_units(p) == [3.0, 10.0]
    assert not history_issues(p).unreconciled


def test_fund_held_only_from_opening_balance_is_absent_but_named():
    p = parsed([(NAME, 25.0, 25.0, []),
                ("Beta Small Cap Fund - Direct Plan - Growth", 30.0, 20.0,       # a sale, but no purchase
                 [("2025-01-05", "REDEMPTION", -10.0, -120.0)]),
                ("Gamma Index Fund - Direct Growth", 0.0, 10.0, [("2024-01-05", "PURCHASE", 10.0, 100.0)])])
    cf = held_lots(p.txns, p.schemes, TODAY)
    assert set(cf.scheme) == {"Gamma Index Fund - Direct Growth"}
    assert history_issues(p).partial == ["Alpha Flexi Cap Fund", "Beta Small Cap Fund"]


def test_periodicity_ignores_the_opening_balance():
    bench = load_bench([{"date": "2019-01-01", "nav": 100.0}, {"date": "2026-01-01", "nav": 200.0}])
    rows = [(f"2024-{m:02d}-05", "PURCHASE_SIP", 1.0, 10.0) for m in range(1, 10)]
    with_open = periodicity(parsed([(NAME, 40.0, 49.0, rows)]).txns, bench)
    without = periodicity(parsed([(NAME, 0.0, 9.0, rows)]).txns, bench)
    assert len(with_open.purchases) == len(without.purchases) == 9
    assert with_open.pct == without.pct


def test_units_off_by_more_than_a_hundredth_dont_reconcile():
    rows = [("2022-01-05", "PURCHASE", 10.0, 100.0)]
    assert not history_issues(parsed([(NAME, 0.0, 10.005, rows)]))
    issues = history_issues(parsed([(NAME, 0.0, 10.5, rows)]))
    assert issues.partial == [] and issues.unreconciled == ["Alpha Flexi Cap Fund"]
    text = warning_text(issues)
    assert text.startswith("**Some funds don't add up.**") and "history is missing" not in text
    assert "[send feedback](https://tally.so/r/2EqQGg)" in text


def test_both_blocks_share_one_warning():
    text = warning_text(HistoryIssues(["A"], ["B"]))
    assert text.index("history is missing") < text.index("don't add up")


def test_complete_statement_has_no_warning():
    from fundprint.sample import sample_cas
    assert not history_issues(sample_cas(TODAY))


def test_more_than_five_funds_lists_five_then_the_rest():
    text = warning_text(HistoryIssues([f"Fund {c}" for c in "ABCDEFGH"], []))
    listed = re.findall(r"^- (.*)$", text, re.M)
    assert listed == ["Fund A", "Fund B", "Fund C", "Fund D", "Fund E", "and 3 more"]


def test_same_fund_in_two_folios_is_named_once():
    p = parsed([(NAME, 5.0, 5.0, []), ("Alpha Flexi Cap Fund - Regular Plan - Growth", 5.0, 5.0, [])])
    assert history_issues(p).partial == ["Alpha Flexi Cap Fund"]


@pytest.mark.parametrize("evil", ["![x](https://evil.example/a.png)", "[click](https://evil.example)",
                                  "<img src=x>", "www.evil.example", "$x^2$", "a@evil.example"])
def test_fund_names_cant_become_links_images_or_html(evil):
    """FP-01: names come from the PDF, so every punctuation mark is escaped before it reaches Markdown."""
    safe = plain(evil)
    assert not re.search(r"(?<!\\)[!\[\]()<>$@.:/]", safe)
    assert safe.replace("\\", "") == evil


def test_parser_no_longer_raises_for_open_balance():
    cas = {"cas_type": "DETAILED", "statement_period": {"from": "01-Jan-2023", "to": "01-Jan-2026"},
           "folios": [{"folio": "1", "schemes": [{
               "scheme": NAME, "isin": "INF0", "open": 40.0, "close": 50.0,
               "valuation": {"date": "2026-01-01", "nav": 10.0},
               "transactions": [{"date": "2024-01-05", "type": "PURCHASE", "units": 10.0, "amount": 100.0}]}]}]}
    assert history_issues(from_dict(cas)).partial == ["Alpha Flexi Cap Fund"]


# ---- on the page --------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))  # the app imports `ui` directly
BANNED = re.compile(r"₹|\bRs\b|\bINR\b|lakh|crore", re.I)


def _page_with(p):
    from streamlit.testing.v1 import AppTest
    from fundprint.sample import sample_categories
    at = AppTest.from_file(str(ROOT / "app/pages/1_Time_in_Market.py"), default_timeout=90)
    at.session_state["parsed"] = p
    at.session_state["categories"] = sample_categories()
    at.session_state["is_sample"] = False
    return at.run()


def test_page_warns_and_still_shows_results_without_rupees():
    from fundprint.sample import sample_cas
    p = sample_cas(TODAY)
    p.schemes.loc[0, "open"] = 12.0                        # first fund started before the statement
    p.schemes.loc[0, "close"] += 12.0
    at = _page_with(p)
    assert not at.exception
    assert len(at.warning) == 1 and "Sample Flexi Cap Fund" in at.warning[0].value
    assert any("| Held for |" in m.value for m in at.markdown)   # results table still renders
    assert [h.value for h in at.header] == ["By time in market", "The big picture"]
    text = " ".join(str(e.value) for e in [*at.warning, *at.markdown, *at.caption])
    assert not BANNED.search(text)
    assert not re.search(r"\d", at.warning[0].value)      # no unit counts or amounts in the warning


def test_page_has_no_warning_for_a_complete_statement():
    from fundprint.sample import sample_cas
    assert len(_page_with(sample_cas(TODAY)).warning) == 0
