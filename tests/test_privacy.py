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


def test_no_browser_storage_in_app_code():
    """Returning visitors upload again: nothing is saved to resume later."""
    banned = ("localStorage", "sessionStorage", "indexedDB", "document.cookie", "<script", "components.html")
    for f in (ROOT / "app").rglob("*.py"):
        text = f.read_text()
        assert not any(w in text for w in banned), f


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
