import numpy as np
import pandas as pd
import pytest

from fundprint.benchmark import compare, load_bench
from fundprint.lots import held_lots
from tests.test_lots import TODAY, make


def growing_bench(start="2010-01-01", rate=0.10):
    days = pd.date_range(start, TODAY, freq="D")
    t = (days - days[0]).days / 365.0
    return load_bench([{"date": d.strftime("%Y-%m-%d"), "nav": 10 * (1 + rate) ** x} for d, x in zip(days, t)])


def test_benchmark_growing_10_percent_gives_10_percent_xirr():
    txns, schemes = make([
        ("2018-03-05", "PURCHASE", 10.0, 100.0),
        ("2018-09-05", "PURCHASE", 10.0, 100.0),
        ("2023-05-05", "PURCHASE", 10.0, 100.0),
    ])
    table, n = compare(held_lots(txns, schemes, TODAY), growing_bench())
    assert n == 0
    assert table["nifty_xirr_%"].tolist() == pytest.approx([10.0] * len(table), abs=0.05)


def test_old_purchase_is_excluded_not_a_crash():
    txns, schemes = make([
        ("2005-03-05", "PURCHASE", 10.0, 100.0),
        ("2023-05-05", "PURCHASE", 10.0, 100.0),
    ])
    table, n = compare(held_lots(txns, schemes, TODAY), growing_bench("2012-01-01"))
    assert n == 1 and "5Y+" not in table.index


def test_table_has_percentages_only():
    txns, schemes = make([("2020-03-05", "PURCHASE", 10.0, 100.0)])
    table, _ = compare(held_lots(txns, schemes, TODAY), growing_bench())
    assert all(c.endswith("%") for c in table.columns)
