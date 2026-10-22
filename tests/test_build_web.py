"""Spec 008: the build adds preload tags for the widgets the app draws after start-up (no network needed)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_web", ROOT / "scripts" / "build_web.py")
bw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bw)


def test_index_has_the_preload_marker():
    assert bw.PRELOAD_MARKER in (ROOT / "web/index.html").read_text()


def test_preload_follows_imports_but_not_other_widgets(tmp_path):
    files = {
        "TextInput-aa-bb.js": 'import { x } from "./Input-cc-dd.js"; const y = () => import("./TextInput-ee-ff.js");',
        "TextInput-ee-ff.js": 'import "./helper-gg-hh.js";',
        "Input-cc-dd.js": 'const big = () => import("./PlotlyChart-ii-jj.js");',   # another widget: not followed
        "helper-gg-hh.js": "",
        "PlotlyChart-ii-jj.js": "",
    }
    for name, code in files.items():
        (tmp_path / name).write_text(code)
    got = bw.preload_files(tmp_path, widgets=("TextInput",))
    assert got == ["Input-cc-dd.js", "TextInput-aa-bb.js", "TextInput-ee-ff.js", "helper-gg-hh.js"]


def test_a_renamed_widget_stops_the_build(tmp_path):
    with pytest.raises(SystemExit, match="TextInput"):
        bw.preload_files(tmp_path, widgets=("TextInput",))


def test_tags_replace_the_marker():
    html = f"<head>\n  {bw.PRELOAD_MARKER}\n</head>"
    out = bw.add_preload_tags(html, ["A-1-2.js"])
    assert out == '<head>\n  <link rel="modulepreload" href="./vendor/stlite/A-1-2.js">\n</head>'


def test_the_built_page_preloads_every_listed_widget():
    built = ROOT / "dist/index.html"
    if not (ROOT / "dist/vendor").exists():
        pytest.skip("needs a full build in dist/")
    html = built.read_text()
    for w in bw.PRELOAD_WIDGETS:
        assert f'href="./vendor/stlite/{w}-' in html, w


# Spec 009: reloading a page's address lands on Home instead of GitHub's 404 page.

def test_page_address_matches_streamlit():
    assert bw.page_address("app/pages/1_Time_in_Market.py") == "Time_in_Market"
    assert bw.page_address("12_Two_Words.py") == "Two_Words"


def test_redirect_page_only_points_home():
    html = bw.REDIRECT_PAGE
    assert "<script" not in html.lower() and "://" not in html             # runs nothing, links nowhere else
    assert "default-src 'none'" in html                                   # loads nothing
    assert 'content="0; url=./"' in html and 'href="./"' in html


def test_every_page_has_a_redirect_file():
    if not (ROOT / "dist/index.html").exists():
        pytest.skip("needs a build in dist/")
    for page in (ROOT / "app/pages").glob("*.py"):
        assert (ROOT / "dist" / f"{bw.page_address(page)}.html").read_text() == bw.REDIRECT_PAGE
