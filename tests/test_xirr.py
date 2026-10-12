import math

import numpy as np
import pandas as pd
import pytest
from pyxirr import xirr as pyxirr

from fundprint.xirr import xirr


def test_doubling_in_two_years():
    r = xirr(["2020-01-01", "2021-12-31"], [-100, 200])  # 730 days
    assert r == pytest.approx(math.sqrt(2) - 1, abs=1e-9)


def test_two_deposits_known_answer():
    t0 = pd.Timestamp("2020-01-01")
    dates = [t0, t0 + pd.Timedelta(days=int(0.5 * 365)), t0 + pd.Timedelta(days=730)]
    assert 100 * xirr(dates, [-1000, -1000, 2600]) == pytest.approx(16.13, abs=0.01)


def test_same_sign_is_nan():
    assert math.isnan(xirr(["2020-01-01", "2021-01-01"], [100, 100]))


def test_matches_pyxirr_on_random_flows():
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(500):
        n = int(rng.integers(3, 25))
        days = np.sort(rng.integers(0, 3000, n))
        dates = pd.Timestamp("2018-01-01") + pd.to_timedelta(days, unit="D")
        amounts = -rng.uniform(100, 5000, n)
        amounts[-1] = -amounts[:-1].sum() * rng.uniform(0.6, 2.5)
        if days[-1] == 0:
            continue
        ref = pyxirr(list(dates.date), list(amounts))
        ours = xirr(dates, amounts)
        if ref is None or not np.isfinite(ref):
            continue
        worst = max(worst, abs(ours - ref))
    assert worst < 1e-6
