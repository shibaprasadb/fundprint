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
