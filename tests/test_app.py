"""No-rupee check: render the Vintage page with sample data and look for money text."""
import re
import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))  # the app imports `ui` directly

from fundprint.sample import sample_cas, sample_categories  # noqa: E402

BANNED = re.compile(r"₹|\bRs\b|\bINR\b|lakh|crore", re.I)


def _run(scope):
    at = AppTest.from_file("app/pages/1_Vintage.py", default_timeout=90)
    at.session_state["parsed"] = sample_cas(pd.Timestamp.today())
    at.session_state["categories"] = sample_categories()
    at.session_state["is_sample"] = True
    at.run()
    if scope:
        at.radio[0].set_value(scope).run()
    return at


def test_vintage_has_no_rupee_text():
    for scope in (None, "Equity funds only"):
        at = _run(scope)
        assert not at.exception
        text = " ".join(str(e.value) for e in [*at.markdown, *at.caption])
        text += " ".join(df.value.to_string() for df in at.dataframe)
        assert len(at.dataframe) == 1 and not BANNED.search(text)
