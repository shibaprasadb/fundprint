"""The two whole-portfolio views, on made-up data only."""
import re

import pandas as pd
import pytest

from fundprint.benchmark import load_bench
from fundprint import insights
from fundprint.charts import gaps_chart, periodicity_chart
from fundprint.insights import fund_gaps, gaps_title, periodicity, periodicity_subtitle, periodicity_title, short_name
from tests.test_benchmark import growing_bench
from tests.test_lots import TODAY

BANNED = re.compile(r"₹|\bRs\b|\bINR\b|lakh|crore", re.I)


def lots(rows, start_id=1):
    """rows: (date, cost, growth per year or None -> 'value now' given) for one fund -> cash flows."""
    out = []
    for i, (fund, d, cost, rate, cls) in enumerate(rows, start_id):
        d = pd.Timestamp(d)
        value = cost * (1 + rate) ** ((TODAY - d).days / 365.0)
        for when, amt in ((d, -cost), (TODAY, value)):
            out.append((i, "x", when, amt, fund["folio"], fund["scheme"], fund["isin"], cls))
    return pd.DataFrame(out, columns=["lot", "bucket", "date", "amount", "folio", "scheme", "isin", "asset_class"])


def fund(name, isin="INF1", folio="F1"):
    return {"folio": folio, "scheme": name, "isin": isin}


def test_fund_moving_with_the_benchmark_has_no_gap():
    cf = lots([(fund("A"), d, 100.0, 0.10, "Equity") for d in ("2020-03-05", "2022-03-05")])
    g = fund_gaps(cf, growing_bench(), TODAY).table
    assert g.gap_pp.iloc[0] == pytest.approx(0.0, abs=0.1)


def test_fund_growing_faster_is_ahead_by_the_difference():
    cf = lots([(fund("A"), d, 100.0, 0.15, "Equity") for d in ("2019-03-05", "2021-03-05")])
    g = fund_gaps(cf, growing_bench(), TODAY).table
    assert g.gap_pp.iloc[0] == pytest.approx(5.0, abs=0.3)


def test_same_scheme_in_two_folios_is_one_bar():
    cf = lots([(fund("A", folio="F1"), "2020-03-05", 100.0, 0.12, "Equity"),
               (fund("A", folio="F2"), "2021-03-05", 300.0, 0.12, "Equity")])
    g = fund_gaps(cf, growing_bench(), TODAY).table
    assert len(g) == 1 and g.name.iloc[0] == "A" and g["share_%"].iloc[0] == pytest.approx(100.0)


def test_young_money_uses_absolute_return_and_is_flagged():
    cf = lots([(fund("A"), "2025-10-01", 100.0, 0.30, "Equity")])
    row = fund_gaps(cf, growing_bench(), TODAY).table.iloc[0]
    assert row.young
    days = (TODAY - pd.Timestamp("2025-10-01")).days / 365.0
    assert row.gap_pp == pytest.approx(100 * (1.30 ** days - 1.10 ** days), abs=0.2)   # abs gap, not an annualised one


def test_only_equity_funds_appear_and_sorted_most_ahead_first():
    cf = pd.concat([
        lots([(fund("Eq behind", "I1"), "2020-03-05", 100.0, 0.05, "Equity")]),
        lots([(fund("Eq ahead", "I2"), "2020-03-05", 100.0, 0.20, "Equity")], 10),
        lots([(fund("Debt fund", "I3"), "2020-03-05", 100.0, 0.07, "Debt")], 20),
        lots([(fund("Hybrid fund", "I4"), "2020-03-05", 100.0, 0.07, "Hybrid")], 30),
    ])
    t = fund_gaps(cf, growing_bench(), TODAY).table
    assert list(t.name) == ["Eq ahead", "Eq behind"]
    assert gaps_title(t) == "1 of 2 equity funds are ahead of their Nifty 50 twin"


def test_only_the_largest_twelve_funds_are_shown():
    cf = pd.concat([lots([(fund(f"F{i}", f"I{i}"), "2020-03-05", 100.0 + i, 0.12, "Equity")], i * 10) for i in range(15)])
    r = fund_gaps(cf, growing_bench(), TODAY)
    assert len(r.table) == 12 and r.n_hidden == 3 and r.table["share_%"].sum() == pytest.approx(100.0)
    assert "F0" not in set(r.table.name)


def test_a_single_equity_fund_still_shows():
    cf = lots([(fund("Only"), "2020-03-05", 100.0, 0.12, "Equity")])
    assert len(fund_gaps(cf, growing_bench(), TODAY).table) == 1


def test_lots_older_than_the_benchmark_are_left_out():
    cf = lots([(fund("A"), "2005-03-05", 1000.0, 0.30, "Equity"), (fund("A"), "2020-03-05", 100.0, 0.10, "Equity")])
    g = fund_gaps(cf, growing_bench("2010-01-01"), TODAY).table
    assert g.gap_pp.iloc[0] == pytest.approx(0.0, abs=0.1)


def test_short_names_drop_plan_and_option_text():
    assert short_name("Axis Bluechip Fund - Direct Plan - Growth Option") == "Axis Bluechip Fund"
    assert short_name("Parag Parikh Flexi Cap Fund - Direct Growth") == "Parag Parikh Flexi Cap Fund"
    assert short_name("HDFC Index Fund Nifty 50 Plan (Non Demat)") == "HDFC Index Fund Nifty 50 Plan"
    assert short_name("Axis Growth Opportunities Fund - Regular Plan - Growth") == "Axis Growth Opportunities Fund"


# ---- how regular is your investing ----

def txns(rows):
    """rows: (date, kind, units, scheme, folio) -> transactions. Amount is units x 10."""
    df = pd.DataFrame(rows, columns=["date", "kind", "units", "scheme", "folio"])
    df["date"] = pd.to_datetime(df["date"])
    df["isin"] = "I-" + df.scheme
    df["amount"] = df.units * 10.0
    return df


def sips(scheme, day, months=12, kind="PURCHASE_SIP", folio="F1", start="2024-01-01"):
    return [(d.replace(day=day), kind, 5.0, scheme, folio) for d in pd.date_range(start, periods=months, freq="MS")]


def test_monthly_sip_on_the_fifth_is_fully_periodic():
    pr = periodicity(txns(sips("A", 5)), growing_bench())
    assert pr.pct == 100 and pr.usual_days == [5]
    assert periodicity_title(pr) == "100% of your investments followed a regular pattern"
    assert periodicity_subtitle(pr).endswith("Your usual day: the 5th.")


def test_each_fund_gets_its_own_usual_day(monkeypatch):
    t = txns(sips("A", 5) + sips("B", 20))
    pr = periodicity(t, growing_bench())
    assert pr.pct == 100 and pr.usual_days == [5, 20]
    assert periodicity_subtitle(pr).endswith("Your usual days: the 5th, the 20th.")
    monkeypatch.setattr(insights, "PERIODICITY_GROUP", "all")
    assert periodicity(t, growing_bench()).pct == 50     # the 20th SIPs are far from the 5th


def test_zone_wraps_around_the_month_end():
    assert insights.day_distance(28, 30) == 2 and insights.day_distance(28, 2) == 5 and insights.day_distance(28, 4) == 7
    rows = sips("A", 28, 6) + [("2024-08-30", "PURCHASE", 5.0, "A", "F1"), ("2024-09-02", "PURCHASE", 5.0, "A", "F1"),
                               ("2024-09-04", "PURCHASE", 5.0, "A", "F1")]
    p = periodicity(txns(rows), growing_bench()).purchases
    flag = dict(zip(p.date.dt.strftime("%Y-%m-%d"), p.periodic))
    assert flag["2024-08-30"] and flag["2024-09-02"] and not flag["2024-09-04"]


def test_two_purchases_are_below_the_minimum_pattern():
    t = txns([("2024-03-05", "PURCHASE", 5.0, "A", "F1"), ("2024-03-05", "PURCHASE", 5.0, "A", "F1")])
    pr = periodicity(t, growing_bench())
    assert pr.pct == 0 and pr.usual_days == []


def test_a_single_lump_sum_is_one_off():
    pr = periodicity(txns([("2024-03-05", "PURCHASE", 50.0, "A", "F1")]), growing_bench())
    assert pr.pct == 0 and not pr.purchases.periodic.any()


def test_internal_moves_and_reversed_purchases_are_not_counted():
    rows = sips("A", 5, 3) + [
        ("2024-06-05", "DIVIDEND_REINVEST", 1.0, "A", "F1"), ("2024-06-05", "SWITCH_IN", 4.0, "A", "F1"),
        ("2024-06-05", "STP_IN", 4.0, "A", "F1"), ("2024-07-05", "PURCHASE_SIP", 7.5, "A", "F1"),
        ("2024-07-08", "REVERSAL", -7.5, "A", "F1"), ("2024-07-09", "STAMP_DUTY", 0.0, "A", "F1"),
    ]
    assert len(insights.counted_purchases(txns(rows))) == 3


def test_sold_purchases_still_count():
    rows = sips("A", 5, 4) + [("2024-12-01", "REDEMPTION", -20.0, "A", "F1")]
    assert len(insights.counted_purchases(txns(rows))) == 4


def test_same_fund_in_two_folios_is_one_group():
    rows = sips("A", 5, 2, folio="F1") + sips("A", 5, 2, folio="F2", start="2024-03-01")
    assert periodicity(txns(rows), growing_bench()).pct == 100    # 2 + 2 purchases reach the minimum of 3 together


def test_same_day_sips_in_three_funds_are_three_purchases():
    rows = [(d, k, u, s, "F1") for s in "ABC" for d, k, u, _, _ in sips(s, 5, 3)]
    assert len(periodicity(txns(rows), growing_bench()).purchases) == 9


def test_ties_resolve_by_window_coverage_then_earliest_day():
    days = pd.Series([10, 10, 20, 20, 22])          # 10 and 20 tie on count; 20's zone also holds 22
    assert insights._usual_day(days) == 20
    assert insights._usual_day(pd.Series([3, 3, 25, 25])) == 3     # equal coverage: earliest


def test_usual_days_list_is_capped_with_and_others():
    pr = insights.Periodicity(None, 80, [5, 10, 15, 20], None)
    assert periodicity_subtitle(pr).endswith("the 5th, the 10th, the 15th and others.")
    assert insights.ordinal(1) == "the 1st" and insights.ordinal(22) == "the 22nd" and insights.ordinal(11) == "the 11th"


def test_no_pattern_gives_the_plain_title_and_no_usual_day_line():
    pr = periodicity(txns([("2024-03-05", "PURCHASE", 5.0, "A", "F1"), ("2024-07-20", "PURCHASE", 5.0, "B", "F1")]),
                     growing_bench())
    assert periodicity_title(pr) == "Your investments don't follow a regular monthly pattern"
    assert periodicity_subtitle(pr) == ""


# ---- no rupee amounts in either chart ----

def test_charts_carry_no_rupee_text():
    pr = periodicity(txns(sips("A", 5) + [("2024-03-12", "PURCHASE", 80.0, "B", "F1")]), growing_bench())
    figs = [periodicity_chart(pr, growing_bench().date.iloc[-1])]
    eq = lots([(fund("A"), "2020-03-05", 100.0, 0.12, "Equity"), (fund("B", "I2"), "2022-03-05", 50.0, 0.05, "Equity")])
    figs.append(gaps_chart(fund_gaps(eq, growing_bench(), TODAY).table))
    for fig in figs:
        text = " ".join(t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text")))
        assert text.strip() and not BANNED.search(text)
