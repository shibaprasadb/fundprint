"""The two whole-portfolio views, on made-up data only."""
import re

import pandas as pd
import pytest

from fundprint.benchmark import load_bench
from fundprint.charts import gaps_chart, timing_chart
from fundprint.insights import (
    CLASS_ORDER, fund_gaps, gaps_title, near_high, purchase_timing, short_name, timing_title, title_for,
)
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


# ---- near a high ----

def series(navs, start="2024-01-01"):
    d = pd.date_range(start, periods=len(navs), freq="D")
    return load_bench([{"date": x.strftime("%Y-%m-%d"), "nav": v} for x, v in zip(d, navs)])


def test_near_high_matches_hand_made_series_including_the_boundary():
    nh = near_high(series([100, 96, 95, 94.99, 100, 120, 113.9, 114])).tolist()
    assert nh == [True, True, True, False, True, True, False, True]    # 95 and 114 sit exactly on the line


def test_old_peaks_drop_out_of_the_window():
    navs = [200] + [100] * 400
    nh = near_high(series(navs))
    assert not nh.iloc[10] and nh.iloc[-1]


# ---- when did you buy ----

def timing_cf():
    """Bench: 100 for 5 days (near), a jump to 200 (near), then 100 again (not near). One lot per day."""
    navs = [100, 100, 200, 200, 100, 100]
    bench = series(navs)
    days = bench.date
    rows = [  # (day index, cost, class)
        (0, 100.0, "Equity"), (1, 300.0, "Equity"), (4, 100.0, "Equity"),       # equity: 400 near / 500
        (2, 50.0, "Debt"), (4, 50.0, "Debt"),                                   # debt: 50 near / 100
        (3, 100.0, "Commodity"),                                                # commodity: all near
    ]
    f = fund("A")
    cf = pd.DataFrame([(i, "x", days[d], -c, f["folio"], f["scheme"], f["isin"], cls) for i, (d, c, cls) in enumerate(rows)],
                      columns=["lot", "bucket", "date", "amount", "folio", "scheme", "isin", "asset_class"])
    return cf, bench


def test_near_high_share_is_cost_weighted_within_each_class():
    cf, bench = timing_cf()
    t = purchase_timing(cf, bench)
    assert t.near_pct["Equity"] == pytest.approx(80.0)
    assert t.near_pct["Debt"] == pytest.approx(50.0)
    assert t.near_pct["Commodity"] == pytest.approx(100.0)
    assert t.all_pct == pytest.approx(100 * 550 / 700)
    assert t.classes == ["Equity", "Debt", "Commodity"]     # Other is not held, so it is not listed


def test_baseline_counts_only_trading_days_between_first_and_last_purchase():
    cf, bench = timing_cf()
    first = cf.copy()
    first = first[first.date.between(bench.date[1], bench.date[3])]   # purchases on days 1-3 only
    t = purchase_timing(first, bench)
    assert t.baseline_pct == pytest.approx(100.0)                      # days 1,2,3 are all near a high
    t = purchase_timing(cf, bench)
    assert t.baseline_pct == pytest.approx(80.0)                       # days 0-4 (last purchase): 4 near, 1 not


def test_other_is_listed_only_at_five_percent_of_the_money():
    cf, bench = timing_cf()
    f = fund("B")
    small = pd.DataFrame([(99, "x", bench.date[1], -10.0, f["folio"], f["scheme"], f["isin"], "Hybrid")], columns=cf.columns)
    assert "Other" not in purchase_timing(pd.concat([cf, small]), bench).classes      # 10 of 710 is under 5%
    big = small.assign(amount=-100.0)
    t = purchase_timing(pd.concat([cf, big]), bench)
    assert t.classes[-1] == "Other"


def test_title_uses_equity_and_falls_back_to_all_funds():
    cf, bench = timing_cf()
    t = purchase_timing(cf, bench)
    assert timing_title(t) == title_for(80.0 - t.baseline_pct)
    no_equity = purchase_timing(cf[cf.asset_class != "Equity"], bench)
    assert timing_title(no_equity) == title_for(no_equity.all_pct - no_equity.baseline_pct)


def test_title_rule_at_plus_six_zero_and_minus_six():
    assert title_for(6).startswith("More of your money")
    assert title_for(0) == "Your buying looks close to random timing"
    assert title_for(-6).startswith("Less of your money")
    assert title_for(5) == title_for(-5) == "Your buying looks close to random timing"


def test_every_class_in_the_order_list_is_known_to_the_chart():
    assert CLASS_ORDER == ["Equity", "Debt", "Commodity", "Other"]


# ---- no rupee amounts in either chart ----

def test_charts_carry_no_rupee_text():
    cf, bench = timing_cf()
    figs = [timing_chart(purchase_timing(cf, bench), bench.date.iloc[-1])]
    eq = lots([(fund("A"), "2020-03-05", 100.0, 0.12, "Equity"), (fund("B", "I2"), "2022-03-05", 50.0, 0.05, "Equity")])
    figs.append(gaps_chart(fund_gaps(eq, growing_bench(), TODAY).table))
    for fig in figs:
        text = " ".join(t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text")))
        assert text.strip() and not BANNED.search(text)
