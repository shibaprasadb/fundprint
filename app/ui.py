"""Bits shared by every page: page style, the privacy panel, footer, public data loading."""
import base64
import html
import json
import logging
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
FAVICON = HERE / "assets" / "favicon.png"
FORM_IMAGE_ALT = ("CAMS statement form with Detailed selected, the from-date set early, "
                  "and a password field.")
PROMISE = "Nothing is stored. Your file is read and dropped when you close the tab."
PROMISE_WHERE = "Fundprint runs entirely in your browser."
PROMISE_DETAIL = (
    f"Don't take my word for it: the <a href=\"{REPO_URL}\">code is open source</a>, and your browser's "
    "Network tab will show nothing being sent."
)
PRIVACY_URL = f"{REPO_URL}/blob/main/PRIVACY.md"
HOW_IT_WORKS_URL = f"{REPO_URL}/blob/main/ARCHITECTURE.md"
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


# One small block of style, injected on every page. Colours match web/index.html (the header and the
# loading screen live there): paper #FAF8F3, ink #1B2333, navy #002147 (links, controls, headings),
# brick #C0392B (only the Gap column), grey #5F5F5F, hairline rule #D9D4C7.
CSS = """<style>
html, body, .stApp{background:#FAF8F3}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
[data-testid="stToolbar"], [data-testid="stHeader"], [data-testid="stDecoration"], #MainMenu, footer{display:none !important}
.block-container{padding-top:4.5rem}
h1, h2, h3{color:#002147;font-weight:600;scroll-margin-top:4rem}
h1{font-size:2.25rem} h2{font-size:1.5rem;border-bottom:1px solid #D9D4C7;padding-bottom:.35rem} h3{font-size:1.15rem}
table, [data-testid="stDataFrame"]{font-variant-numeric:tabular-nums}
[data-testid="stMarkdownContainer"] strong{font-variant-numeric:tabular-nums}
[data-testid="stCaptionContainer"]{font-size:.85rem;color:#5F5F5F;opacity:1}
a{color:#002147}

.kicker{font-variant-caps:small-caps;letter-spacing:.06em;color:#5F5F5F;margin:0 0 .25rem 0}
.standfirst{font-size:1.15rem;color:#1B2333;margin:0 0 1rem 0}
.panel{background:#F1EEE6;border-left:3px solid #002147;padding:.9rem 1.1rem;margin:1rem 0;color:#1B2333}
.panel p{margin:0 0 .4rem 0}
.panel p:last-child{margin-bottom:0}
.panel a{color:#002147}

/* Buttons: navy outline on paper. The only filled navy control is the file uploader's button. */
.stButton button, [data-testid="stFormSubmitButton"] button{background:#FAF8F3;color:#002147;border:1px solid #002147;font-weight:400;min-height:2.75rem}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover{background:#F1EEE6;border-color:#002147;color:#002147}
[data-testid="stFileUploaderDropzone"] button{background:#002147;color:#FFFFFF;border:1px solid #002147;font-weight:400}
[data-testid="stFileUploaderDropzone"] button:hover{background:#0A3A70;color:#FFFFFF;border-color:#0A3A70}
.stLinkButton a, [data-testid="stLinkButton"] a{background:none;border:0;padding:0;min-height:0;color:#002147;font-weight:400;justify-content:flex-start}
.stLinkButton a:hover, [data-testid="stLinkButton"] a:hover{background:none;text-decoration:underline;color:#002147}
[data-testid="stPageLink"] a{color:#002147}
[data-testid="stPageLink"] a:hover{background:none;text-decoration:underline}
[data-testid="stCode"] pre, [data-testid="stCode"] code{background:transparent;color:#1B2333;font-size:.95rem}
[data-testid="stCode"] pre{padding:.2rem 0}

/* Download links sit under the chart, small and grey, on the right */
[data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]){display:flex;justify-content:flex-end;width:100% !important}
[data-testid="stDownloadButton"] button{background:none;border:0;padding:0;min-height:0;color:#5F5F5F;font-size:.85rem;font-weight:400}
[data-testid="stDownloadButton"] button:hover{background:none;color:#002147;text-decoration:underline}

/* Plain disclosure: no box, serif label */
[data-testid="stExpander"] details{border:0;background:transparent;border-radius:0}
[data-testid="stExpander"] summary{padding-left:0;font-family:"Source Serif","Source Serif 4",Georgia,serif;font-size:1.15rem;font-weight:600;color:#002147}

/* Tables: header row on paper-2, hairline row rules, no vertical lines */
[data-testid="stMarkdownContainer"] table{border-collapse:collapse;width:100%;font-size:.9rem}
[data-testid="stMarkdownContainer"] th, [data-testid="stMarkdownContainer"] td{border:0;border-bottom:1px solid #D9D4C7;padding:.5rem .6rem;color:#1B2333}
[data-testid="stMarkdownContainer"] th{background:#F1EEE6;font-weight:600}
.fp-wrap{overflow-x:auto}
.fp-table th, .fp-table td{text-align:right}
.fp-table td{white-space:nowrap}
.fp-table th, .fp-table td{padding:.5rem .4rem}
.fp-table th:first-child, .fp-table td:first-child{text-align:left}
[data-testid="stMarkdownContainer"] .fp-table td.gap-ahead{color:#C0392B;font-weight:600}
[data-testid="stMarkdownContainer"] .fp-table td.gap-behind{color:#5F5F5F}

.footer{border-top:1px solid #D9D4C7;margin-top:3rem;padding-top:1rem;font-size:.85rem;color:#5F5F5F}
.footer p{margin:0 0 .4rem 0}
.footer a{color:#5F5F5F;text-decoration:underline}

@media (max-width: 640px){
  .stButton, [data-testid="stFormSubmitButton"]{width:100% !important}
  [data-testid="stElementContainer"]:has(.stButton, [data-testid="stFormSubmitButton"]){width:100% !important}
  .stButton button, [data-testid="stFormSubmitButton"] button{width:100% !important;justify-content:center}
  .stLinkButton a, [data-testid="stLinkButton"] a, [data-testid="stPageLink"] a, [data-testid="stDownloadButton"] button{min-height:44px;display:inline-flex;align-items:center}
  [data-testid="stMarkdownContainer"] table:not(.fp-table){display:block;overflow-x:auto}
}
</style>"""


def quiet_logs():
    """Keep only warnings and errors in the log.

    The browser build sets the root logger to DEBUG and sends every line to the page.
    Matplotlib and Pillow then write hundreds of lines for each chart, which is real
    work on a phone and can stall or crash the tab.
    """
    logging.getLogger().setLevel(logging.WARNING)
    for name in ("matplotlib", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)


def prepare_charts():
    """Load the chart code and build Matplotlib's font cache.

    Python cannot redraw while this runs, so call it before the first widget. The loading
    note stays up until then. A later call does almost nothing. This touches no user data.
    """
    import io

    quiet_logs()

    import fundprint.charts  # sets the in-memory backend before any figure is drawn
    import fundprint.insights  # noqa: F401
    import fundprint.xirr  # noqa: F401
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(1, 1))
    fig.text(0.5, 0.5, "Fundprint")
    fig.savefig(io.BytesIO(), format="png", dpi=72)
    plt.close(fig)


def setup():
    """Call first on every page: quiet logs and the page style. The header bar is in web/index.html."""
    quiet_logs()
    st.markdown(CSS, unsafe_allow_html=True)


FEEDBACK_URL = "https://tally.so/r/2EqQGg"


def panel(html):
    """A calm note: paper-2 background with a thin navy rule on the left. `html` is fixed text, never statement data."""
    st.markdown(f'<div class="panel">{html}</div>', unsafe_allow_html=True)


def promise_box():
    """The privacy promise and how to check it, in a neutral panel."""
    panel(f"<p><strong>{PROMISE}</strong></p><p>{PROMISE_WHERE}</p><p>{PROMISE_DETAIL}</p>")


def sample_banner():
    """Shown on the analysis pages while the made-up portfolio is in use."""
    panel("<p><strong>You're looking at a made-up sample portfolio.</strong></p>")
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
        'style="width:100%;height:auto;border:1px solid #D9D4C7;border-radius:4px">',
        unsafe_allow_html=True,
    )


# Step 2 of the checklist: how to fill in the CAMS form. Also shown under the missing-history warning.
STEP_2_TABLE = """
| Field | Choose | Note |
|---|---|---|
| ① Statement type | **Detailed** (includes transaction listing) | **Required.** A Summary statement won't work. |
| ② Period / from date | **A date before your first-ever investment** | **Required.** Earlier is fine. Missing history makes results wrong. |
| To date | Today | |
| Folio listing | Any option | All work. |
| Email + PAN | Yours | The PDF is emailed to you. |
| ③ Password | **Something simple you'll remember** | You'll type it here once. Fundprint never stores it. |
"""


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
    st.markdown(STEP_2_TABLE)
    _form_image()

    _step(3, "Check your email")
    st.markdown("The statement usually arrives from CAMS within a few minutes as a PDF attachment. "
                "If you can't see it, check Spam or Promotions.")

    _step(4, "Come back and upload it")
    st.markdown("Upload the PDF above and type the password you just set.")
    st.caption("Already have a CAS from KFintech or CAMS? That works too, as long as it's the Detailed one.")


def history_warning(text):
    """The missing-history / doesn't-add-up warning (spec 006). It never blocks the results.

    `text` comes from fundprint.history.warning_text, which escapes the fund names.
    """
    st.warning(text)
    if "history is missing" in text:
        with st.expander("How to do this"):
            st.markdown("Request a new statement from CAMS and set the **from date** before your first-ever "
                        "investment. Fill in the form like this:")
            st.markdown(STEP_2_TABLE)
            st.link_button("Open CAMS statement page ↗", CAMS_URL)   # opens in a new tab


def footer(manifest):
    st.markdown(
        '<div class="footer">'
        "<p>Runs entirely in your browser. Nothing is stored or uploaded.</p>"
        f"<p>{DISCLAIMER}</p>"
        f'<p>Benchmark data as of {manifest["benchmark"]["latest_date"]} · '
        f'<a href="{REPO_URL}">Source code</a> · '
        f'<a href="{PRIVACY_URL}">Privacy</a> · '
        f'<a href="{FEEDBACK_URL}" target="_blank" rel="noopener noreferrer">Feedback</a> · '
        'Built by <a href="https://shibaprasadb.com">shibaprasadb.com</a></p></div>',
        unsafe_allow_html=True,
    )


def pct(v):
    """Format a percentage, or 'n/a' when it couldn't be calculated."""
    return "n/a" if pd.isna(v) else f"{v:.1f}%".replace("-", "\u2212")   # a true minus sign


def gap_pts(v):
    """A gap between two percentages, in percentage points, signed, with a true minus sign."""
    if pd.isna(v):
        return "n/a"
    text = f"{abs(v):.1f}"
    return f"+{text}" if v > 0 else f"\u2212{text}" if v < 0 else text


def results_table(table):
    """The comparison as a plain HTML table. Only the Gap column is coloured: brick when ahead, grey when behind.

    Used instead of st.dataframe: that grid needs a 5.5 MB file the browser only downloads the first
    time a table is shown, so it broke when the network had dropped by then (spec 008). Only fixed
    labels and formatted numbers go in here, never text from the statement.
    """
    heads = ["Held for", "Share of money", "Your XIRR", "Nifty 50 XIRR", "Gap (pts)",
             "Your absolute return", "Nifty 50 absolute return"]
    rows = []
    for label, r in table.iterrows():
        gap = r["xirr_gap_%"]
        kind = "gap-ahead" if gap > 0 else "gap-behind"
        cells = [pct(r["share_%"]), pct(r["my_xirr_%"]), pct(r["nifty_xirr_%"])]
        cells_after = [pct(r["my_abs_%"]), pct(r["nifty_abs_%"])]
        body = "".join(f"<td>{html.escape(c)}</td>" for c in cells)
        body += f'<td class="{kind if not pd.isna(gap) else ""}">{gap_pts(gap)}</td>'
        body += "".join(f"<td>{html.escape(c)}</td>" for c in cells_after)
        rows.append(f"<tr><td>{html.escape(str(label))}</td>{body}</tr>")
    head = "".join(f"<th>{h}</th>" for h in heads)
    return (f'<div class="fp-wrap"><table class="fp-table"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


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
