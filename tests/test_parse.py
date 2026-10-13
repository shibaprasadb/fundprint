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


def test_pdf_library_writes_no_debug_logs():
    """Hosts that set the root logger to DEBUG (the browser build does, and forwards every line to the
    page) must not get a flood of messages from the PDF library. Without the fix, pdfminer writes
    about 20,000 lines for this tiny file, which freezes or crashes a browser tab on a real statement."""
    import logging

    pdfminer_high_level = pytest.importorskip("pdfminer.high_level")

    class Count(logging.Handler):
        n = 0

        def emit(self, record):
            Count.n += 1

    root, handler, old = logging.getLogger(), Count(logging.DEBUG), logging.getLogger().level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        pdfminer_high_level.extract_text(PLAIN)
    finally:
        root.removeHandler(handler)
        root.setLevel(old)
    assert Count.n < 50, f"{Count.n} log lines from the PDF library"


# ---- clear errors and partial history -------------------------------------------------------

def _cas(open_units=0, close_units=100, txns=((("2022-01-05"), "PURCHASE_SIP", 100.0),), kind="DETAILED"):
    """A tiny made-up casparser dict with one fund, to try the history checks."""
    return {
        "cas_type": kind,
        "statement_period": {"from": "01-Jan-2020", "to": "09-Oct-2026"},
        "folios": [{"folio": "1", "schemes": [{
            "scheme": "Fund", "isin": "INF000000001", "open": open_units, "close": close_units,
            "valuation": {"date": "2026-10-09", "nav": 10.0},
            "transactions": [{"date": d, "type": k, "units": u, "amount": abs(u) * 10} for d, k, u in txns],
        }]}],
    }


def test_complete_history_is_accepted():
    from fundprint.parse import from_dict
    assert len(from_dict(_cas()).txns) == 1


@pytest.mark.parametrize("cas", [
    _cas(open_units=40, close_units=140),                                              # units held on day one
    _cas(close_units=-100, txns=(("2022-01-05", "REDEMPTION", -100.0),)),               # first move is a sale
    _cas(close_units=90),                                                              # units don't add up
])
def test_partial_history_is_a_friendly_error(cas):
    from fundprint.parse import from_dict
    with pytest.raises(CasError, match="start after your first investment") as e:
        from_dict(cas)
    assert e.value.step == 2


def test_summary_cas_points_to_step_2():
    from fundprint.parse import from_dict
    with pytest.raises(CasError, match="Summary statement. Please request the \\*\\*Detailed\\*\\* one") as e:
        from_dict(_cas(kind="SUMMARY"))
    assert e.value.step == 2


def test_error_messages_match_the_spec():
    with pytest.raises(CasError) as wrong:
        read(LOCKED, "nope")
    assert str(wrong.value) == "That password didn't open the file. It's the one you set on the CAMS form."
    assert wrong.value.step == 2
    with pytest.raises(CasError) as bad:
        parse_cas(b"not a pdf", "")
    assert str(bad.value) == "Couldn't read this file. Is it a CAMS or KFintech statement PDF?"
    assert bad.value.step is not None
