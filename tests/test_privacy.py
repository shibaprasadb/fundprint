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
            t = f.read_text()
            assert not any(w in t for w in ("localStorage", "sessionStorage", "indexedDB")), f
