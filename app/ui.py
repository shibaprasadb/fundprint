"""Bits shared by every page: the promise banner, footer, public data loading."""
import base64
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
APP_URL = "https://lab.shibaprasadb.com/fundprint"
CAMS_URL = "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement"
FORM_IMAGE = HERE / "assets" / "cams_form_annotated.png"
FORM_IMAGE_ALT = ("CAMS statement form with Detailed selected, the from-date set early, "
                  "and a password field.")
PROMISE = "Nothing is stored. Your file is read and dropped when you close the tab."
PROMISE_WHERE = "Fundprint runs entirely in your browser. Your statement is never uploaded to any server."
PROMISE_DETAIL = (
    f"Don't take our word for it: the [code is open source]({REPO_URL}), and you can open your "
    "browser's Network tab to check that your file is never sent anywhere."
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


# The pages use the wide layout; the first rule stops them stretching edge to edge on very large screens.
# The primary button (see it with sample data) is made big. On phones every button fills the width.
CSS = """<style>
.block-container{max-width:1200px}
button[kind="primary"]{padding:0.9rem 2rem;min-height:3.5rem}
button[kind="primary"] p{font-size:1.2rem}
h3[id^="step-"]{font-size:1.25rem}
.stLinkButton a{background:#D9F2DE;border-color:#7CC98B;color:#14532D}
.stLinkButton a:hover{background:#C6EBCD;border-color:#4FB365;color:#14532D}
@media (max-width: 640px){
  [data-testid="stElementContainer"]:has(.stButton, .stLinkButton, [data-testid="stFormSubmitButton"], [data-testid="stPageLink"]){width:100% !important}
  .stButton, .stLinkButton, [data-testid="stFormSubmitButton"], [data-testid="stPageLink"]{width:100% !important}
  .stButton button, .stLinkButton a, [data-testid="stFormSubmitButton"] button, [data-testid="stPageLink"] a{width:100% !important;justify-content:center}
}
</style>"""


def sidebar_note():
    st.markdown(CSS, unsafe_allow_html=True)
    st.sidebar.markdown("🔒 Runs in your browser. Nothing is stored.")


OXFORD_BLUE = "#002147"
FEEDBACK_URL = "https://tally.so/r/2EqQGg"


def _bar(html):
    st.markdown(
        f'<div style="background:{OXFORD_BLUE};color:#FFFFFF;padding:1.2rem 1.5rem;'
        f'border-radius:0.5rem;margin-bottom:1rem">{html}</div>',
        unsafe_allow_html=True,
    )


def header_bar():
    """The name and tagline in an Oxford Blue bar."""
    _bar('<div style="font-size:2.2rem;font-weight:700;line-height:1.2">Fundprint (Beta)</div>'
         '<div style="font-style:italic;margin-top:0.3rem">A CASual look at your mutual fund statement.</div>')


def section_bar(title):
    """A section heading in the same Oxford Blue bar."""
    _bar(f'<div style="font-size:1.6rem;font-weight:700;line-height:1.2">{title}</div>')


def promise_box():
    """The privacy promise in a light red box, so it is the first thing people notice."""
    st.markdown(
        '<div style="background:#FDECEA;border:1px solid #F5C2BD;border-radius:0.5rem;'
        'padding:0.9rem 1.1rem;margin-bottom:1rem;color:#1A1A1A">'
        f'<p style="margin:0 0 0.4rem 0"><strong>{PROMISE}</strong></p>'
        f'<p style="margin:0">{PROMISE_WHERE}</p></div>',
        unsafe_allow_html=True,
    )


def sample_banner():
    """Shown on the analysis pages while the made-up portfolio is in use."""
    st.info("**You're looking at a sample portfolio (made-up data).**")
    st.page_link("Home.py", label="Use your own statement →")


def show_error(message, step=None):
    """A friendly error with a link to the checklist step that helps. Never any statement data."""
    st.error(message)
    if step:
        st.markdown(f"[Go to Step {step} ↓](#step-{step})")


def _step(number, title):
    st.subheader(f"Step {number}. {title}", anchor=f"step-{number}")


def _form_image():
    """The annotated screenshot of the CAMS form, or nothing when the file isn't there."""
    if not FORM_IMAGE.exists():
        return
    data = base64.b64encode(FORM_IMAGE.read_bytes()).decode()
    left, _ = st.columns([5, 1])   # a readable width on a computer; the columns stack to full width on a phone
    left.markdown(
        f'<img src="data:image/png;base64,{data}" alt="{FORM_IMAGE_ALT}" '
        'style="width:100%;height:auto;border:1px solid #E6E6E6;border-radius:0.5rem">',
        unsafe_allow_html=True,
    )


def cas_checklist():
    """Four steps to request a Detailed statement from CAMS. Plain words: 'statement', not 'CAS'."""
    st.subheader("Don't have your statement yet?")
    st.markdown("It takes about a minute to request. **Request it now and come back when the email arrives.** "
                "Bookmark this page, or copy its link:")
    st.code(APP_URL, language=None)

    _step(1, "Open the CAMS statement page")
    st.link_button("Open CAMS statement page ↗", CAMS_URL)   # opens in a new tab
    st.caption("Fundprint stays open in this tab.")

    _step(2, "Fill in the form like this")
    st.markdown("""
| Field | Choose | Note |
|---|---|---|
| ① Statement type | **Detailed** (includes transaction listing) | **Required.** A Summary statement won't work. |
| ② Period / from date | **A date before your first-ever investment** | Earlier is fine. Missing history makes results wrong. |
| To date | Today | |
| Folio listing | Any option | All work. |
| Email + PAN | Yours | The PDF is emailed to you. |
| ③ Password | **Something simple you'll remember** | You'll type it here once. Fundprint never stores it. |
""")
    _form_image()

    _step(3, "Check your email")
    st.markdown("The statement usually arrives from CAMS within a few minutes as a PDF attachment. "
                "If you can't see it, check Spam or Promotions.")

    _step(4, "Come back and upload it")
    st.markdown("Upload the PDF above and type the password you just set.")
    st.caption("Already have a CAS from KFintech or CAMS? That works too, as long as it's the Detailed one.")


def footer(manifest):
    link = 'style="color:#FFFFFF;text-decoration:underline"'
    _bar(
        f'<div style="font-size:0.85rem">{DISCLAIMER}</div>'
        f'<div style="font-size:0.85rem;margin-top:0.5rem">'
        f'Benchmark data as of {manifest["benchmark"]["latest_date"]} · '
        f'<a href="{REPO_URL}" {link}>Source code</a> · '
        f'<a href="{FEEDBACK_URL}" target="_blank" rel="noopener noreferrer" {link}>Feedback</a> · '
        f'Built by <a href="https://shibaprasadb.com" {link}>shibaprasadb.com</a></div>'
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
