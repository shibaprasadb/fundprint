"""No-rupee check: open the sample from the Home page, render Time in Market and look for money text."""
import re
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))  # the app imports `ui` directly

BANNED = re.compile(r"₹|\bRs\b|\bINR\b|lakh|crore", re.I)


def _run(scope):
    """Click "See it with sample data" on Home, which lands on the Time in Market page."""
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=90)
    at.run()
    at.button[0].click().run()
    if scope:
        at.switch_page("pages/1_Time_in_Market.py").run()   # later widget changes rerun this page, not Home
        at.radio[0].set_value(scope).run()
    return at


def test_time_in_market_has_no_rupee_text():
    for scope in (None, "Equity funds only"):
        at = _run(scope)
        assert not at.exception
        text = " ".join(str(e.value) for e in [*at.markdown, *at.caption])
        text += " ".join(df.value.to_string() for df in at.dataframe)
        assert len(at.dataframe) == 1 and not BANNED.search(text)


def test_sample_banner_shows_on_the_analysis_page():
    at = _run(None)
    assert any("sample portfolio (made-up data)" in i.value for i in at.info)
