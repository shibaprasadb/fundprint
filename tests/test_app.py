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
        assert sum("| Held for |" in m.value for m in at.markdown) == 1 and not BANNED.search(text)


def test_sample_banner_shows_on_the_analysis_page():
    at = _run(None)
    assert any("sample portfolio (made-up data)" in i.value for i in at.info)


def test_big_picture_section_ignores_the_scope_toggle():
    for scope in (None, "Equity funds only"):
        at = _run(scope)
        assert not at.exception
        assert [h.value for h in at.header] == ["By time in market", "The big picture"]
        captions = [c.value for c in at.caption]
        assert any("the toggle above doesn't change them" in c for c in captions)
        assert any("aren't shown here" in c for c in captions)



def test_fund_names_never_go_through_markdown():
    """FP-01: names from the PDF are shown with st.text, never as Markdown or a widget label,
    so "![x](/path)" can't become an image request and a web address can't become a link."""
    page = (ROOT / "app/pages/1_Time_in_Market.py").read_text()
    assert "st.text(s)" in page and 'st.text("\\n".join(f"• {n}"' in page
    assert 'st.selectbox("Asset class"' in page
    for widget in ("selectbox", "write", "markdown", "caption", "warning", "radio", "checkbox", "expander"):
        assert not re.search(rf"st\.{widget}\((s|n|name|scheme)\b", page), widget


def test_python_starts_without_stack_switching():
    """Spec 007: iPhone browsers crash Pyodide when it uses stack switching, so boot.js starts Python
    through pyodide-start.mjs, which hides that feature first. The build must ship that file."""
    web = ROOT / "web"
    assert 'pyodideUrl: here("./pyodide-start.mjs")' in (web / "boot.js").read_text()
    start = (web / "pyodide-start.mjs").read_text()
    assert "delete WebAssembly.Suspending" in start and "delete WebAssembly.Suspender" in start
    build = (ROOT / "scripts" / "build_web.py").read_text()
    assert '"pyodide-start.mjs"' in build
