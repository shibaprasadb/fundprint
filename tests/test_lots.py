import pandas as pd
import pytest

from fundprint.lots import held_lots, summarise
from fundprint.parse import ParsedCas, from_dict, CasError

TODAY = pd.Timestamp("2026-01-01")


def make(rows, nav=10.0):
    txns = pd.DataFrame(rows, columns=["date", "kind", "units", "amount"])
    txns["date"] = pd.to_datetime(txns["date"])
    txns["folio"], txns["scheme"], txns["isin"] = "F1", "Fund A", "INF1"
    schemes = pd.DataFrame([{"folio": "F1", "scheme": "Fund A", "isin": "INF1", "nav": nav, "nav_date": TODAY}])
    return txns, schemes


def test_bounced_sip_has_no_effect():
    txns, schemes = make([
        ("2025-01-05", "PURCHASE_SIP", 10.0, 100.0),
        ("2025-02-05", "PURCHASE_SIP", 7.5, 75.0),
        ("2025-02-08", "REVERSAL", -7.5, -75.0),
    ])
    cf = held_lots(txns, schemes, TODAY)
    assert (cf.amount < 0).sum() == 1 and cf.amount.min() == pytest.approx(-100)


def test_reinvested_dividend_costs_nothing():
    txns, schemes = make([
        ("2025-01-05", "PURCHASE", 10.0, 100.0),
        ("2025-06-05", "DIVIDEND_REINVEST", 1.0, 0.0),
    ])
    cf = held_lots(txns, schemes, TODAY)
    value = cf[cf.amount > 0].amount.sum()
    assert value == pytest.approx(11.0 * 10.0)
    assert -cf[cf.amount < 0].amount.sum() == pytest.approx(100.0)


def test_partial_redemption_takes_oldest_first():
    txns, schemes = make([
        ("2020-01-05", "PURCHASE", 10.0, 100.0),
        ("2025-01-05", "PURCHASE", 10.0, 200.0),
        ("2025-06-05", "REDEMPTION", -15.0, -300.0),
    ])
    cf = held_lots(txns, schemes, TODAY)
    out = cf[cf.amount < 0]
    assert len(out) == 1                       # the oldest lot is gone entirely
    assert out.bucket.iloc[0] == "<1Y" or out.bucket.iloc[0] == "1-3Y"
    assert -out.amount.iloc[0] == pytest.approx(200.0 * 5 / 10)   # 5 of 10 units left


def test_summary_shares_add_to_100():
    txns, schemes = make([
        ("2020-01-05", "PURCHASE", 10.0, 100.0),
        ("2025-09-05", "PURCHASE", 10.0, 100.0),
    ])
    s = summarise(held_lots(txns, schemes, TODAY))
    assert s["share_%"].sum() == pytest.approx(100.0)
    assert list(s.index) == ["5Y+", "<1Y"]     # oldest first, empty buckets skipped


def test_summary_cas_is_rejected():
    with pytest.raises(CasError):
        from_dict({"cas_type": "SUMMARY", "folios": []})
