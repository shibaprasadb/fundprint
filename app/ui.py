"""Bits shared by every page: the promise banner, footer, public data loading."""
import json
import sys
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

# On a computer the data folder sits next to app/; in the browser build the files are
# mounted flat, so data/ sits next to this file.
HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "data").exists() else HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPO_URL = "https://github.com/shibaprasadb/fundprint"  # update if the repo lives elsewhere
PROMISE = "**Nothing is stored. Your file is read and dropped when you close the tab.**"
PROMISE_DETAIL = (
    "Fundprint runs entirely in your browser. Your statement is never uploaded to any server.\n\n"
    f"Don't take our word for it: the [code is open source]({REPO_URL}), and you can open your "
    "browser's Network tab to check that nothing is sent."
)
DISCLAIMER = (
    "Fundprint is an analytics tool, not investment advice. Past returns don't predict future "
    "returns. Fundprint is not affiliated with CAMS, KFintech, AMFI, or any fund house. "
    "Benchmark: UTI Nifty 50 Index Fund – Direct Growth, using public NAV data."
)


# Caching is fine here: this is public data that holds nothing from the user's file (rule P3).
@st.cache_data
def load_public_data():
    d = ROOT / "data"
    bench = json.loads((d / "benchmark_nav.json").read_text())
    cats = json.loads((d / "scheme_categories.json").read_text())
    manifest = json.loads((d / "manifest.json").read_text())
    return bench, cats, manifest


def sidebar_note():
    # The pages use the wide layout; this stops them stretching edge to edge on very large screens.
    st.markdown("<style>.block-container{max-width:1200px}</style>", unsafe_allow_html=True)
    st.sidebar.markdown("🔒 Runs in your browser. Nothing is stored.")


def footer(manifest):
    st.divider()
    st.caption(DISCLAIMER)
    st.caption(
        f"Benchmark data as of {manifest['benchmark']['latest_date']} · "
        f"[Source code]({REPO_URL}) · Built by [shibaprasadb.com](https://shibaprasadb.com)"
    )


def pct(v):
    """Format a percentage, or 'n/a' when it couldn't be calculated."""
    return "n/a" if pd.isna(v) else f"{v:.1f}%"


def report_failure(exc):
    """Show a safe error: the kind of error and where in our code it happened.

    Never shows the error message or any values, because those could contain
    details from the statement (rule P8).
    """
    frames = traceback.extract_tb(exc.__traceback__)
    last = frames[-1] if frames else None
    where = f"{Path(last.filename).name}, line {last.lineno}, in {last.name}" if last else "unknown place"
    st.error(
        "Something went wrong while showing this page. "
        f"Error type: {type(exc).__name__}. Location: {where}. "
        "Nothing from your statement is shown here."
    )
