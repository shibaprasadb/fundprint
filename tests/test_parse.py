"""End to end: made-up CAS PDF -> parsed tables -> held lots -> XIRR.

The expected numbers are the same ones the browser spike produced inside
stlite (web/spike), so a mismatch here means desktop and browser have drifted.
"""
import pandas as pd
import pytest

from fundprint.lots import held_lots, summarise
from fundprint.parse import CasError, parse_cas

PLAIN, LOCKED = "tests/fixtures/sample_cas.pdf", "tests/fixtures/sample_cas_locked.pdf"


def read(path, pw=""):
    return parse_cas(open(path, "rb").read(), pw)


@pytest.mark.parametrize("path,pw", [(PLAIN, ""), (LOCKED, "secret123")])
def test_parse_matches_browser(path, pw):
    p = read(path, pw)
    assert len(p.txns) == 58
    assert p.txns.units.sum() == pytest.approx(3178.231)
    assert sorted(p.schemes["isin"]) == ["INF109K012M7", "INF194K01W62"]
    assert p.period_start == pd.Timestamp("2020-01-01")
    s = summarise(held_lots(p.txns, p.schemes, pd.Timestamp("2026-10-09")))
    assert s["xirr_%"].round(2).to_dict() == {"3-5Y": 13.96, "1-3Y": 14.72, "<1Y": 16.40}


def test_wrong_password_message_has_no_file_data():
    with pytest.raises(CasError, match="password"):
        read(LOCKED, "nope")


def test_garbage_file_is_a_friendly_error():
    with pytest.raises(CasError, match="Couldn't read"):
        parse_cas(b"not a pdf", "")
