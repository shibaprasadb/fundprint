"""Simple static checks for the privacy rules (P3, P4)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_cache_on_user_data_code():
    for f in [*(ROOT / "fundprint").glob("*.py"), *(ROOT / "app").rglob("*.py")]:
        text = f.read_text()
        if f.name == "ui.py":      # only public data is cached here, on purpose
            assert text.count("st.cache") == 1
            continue
        assert "st.cache" not in text, f


def test_no_browser_storage_in_web():
    for f in (ROOT / "web").rglob("*"):
        if f.is_file() and f.suffix in {".html", ".js"} and "vendor" not in f.parts:
            if f.name == "umami.js":   # reviewed copy, pinned by hash below; reads only the umami.disabled flag
                continue
            t = f.read_text()
            assert not any(w in t for w in ("localStorage", "sessionStorage", "indexedDB")), f


def test_no_browser_storage_in_app_code():
    """Returning visitors upload again: nothing is saved to resume later."""
    banned = ("localStorage", "sessionStorage", "indexedDB", "document.cookie", "<script", "components.html")
    for f in (ROOT / "app").rglob("*.py"):
        text = f.read_text()
        assert not any(w in text for w in banned), f


def _web_text_files():
    for f in (ROOT / "web").rglob("*"):
        if f.is_file() and "vendor" not in f.parts and f.suffix in {".html", ".js", ".css", ".json"}:
            yield f
    yield from (ROOT / "lab-template").rglob("*.html")


def test_old_umami_script_address_is_gone():
    for f in _web_text_files():
        assert "cloud.umami.is" not in f.read_text(), f


def test_no_script_tag_loads_from_another_site():
    import re
    html = (ROOT / "web/index.html").read_text()
    for src in re.findall(r"<script[^>]*\ssrc=[\"']([^\"']+)", html):
        assert not src.startswith("http"), src


def test_policy_script_src_has_no_outside_address():
    import re
    html = (ROOT / "web/index.html").read_text()
    script_src = re.search(r"script-src([^;\"]*)", html).group(1)
    assert "https:" not in script_src, script_src


def test_umami_tag_only_counts_the_live_site():
    assert 'data-domains="lab.shibaprasadb.com"' in (ROOT / "web/index.html").read_text()


def test_umami_script_is_the_reviewed_copy():
    """Any change to web/umami.js must be deliberate. To update: download the new script, read it in full
    (what it sends and where), replace web/umami.js, then put its new SHA-256 here."""
    import hashlib
    digest = hashlib.sha256((ROOT / "web/umami.js").read_bytes()).hexdigest()
    assert digest == "91a876d767646fd5b7701b6fabf97f8a99ae53b94e7e5b58d465bad1e5d763e0"

def test_notebooks_have_no_outputs():
    """A notebook run on a real statement would print the whole portfolio, so none may carry outputs."""
    import json
    skip = {".ipynb_checkpoints", ".venv", "dist"}
    for f in ROOT.rglob("*.ipynb"):
        rel = f.relative_to(ROOT)
        if skip & set(rel.parts) or rel.parts[:2] == ("web", "vendor"):
            continue
        for i, cell in enumerate(json.loads(f.read_text()).get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            assert not cell.get("outputs") and cell.get("execution_count") is None, (
                f"{rel} cell {i} has outputs. Clear all outputs in Jupyter, or run `nbstripout {rel}`, "
                "then run the tests again."
            )


def test_feedback_link_is_plain_and_counted_once():
    """The feedback form opens in a new tab; only a bare click:feedback event is allowed to Umami."""
    url = "https://tally.so/r/2EqQGg"
    html = (ROOT / "web/index.html").read_text()
    assert f'href="{url}" target="_blank" rel="noopener noreferrer"' in html
    assert "<iframe" not in html and "tally.so" not in html.split("Content-Security-Policy")[1].split(">")[0]
    js = (ROOT / "web/feedback.js").read_text()
    assert 'ALLOWED_EVENTS = ["click:feedback"]' in js
    assert 'data-before-send="fundprintBeforeSend"' in html
    assert f'href="{url}"' in (ROOT / "app/ui.py").read_text() or url in (ROOT / "app/ui.py").read_text()
