"""Assemble the static site in dist/ (the folder that gets published).

dist/ holds everything the browser loads, so the page only ever talks to its
own domain. Run scripts/fetch_vendor.py first to download the third-party
files (stlite, Python-in-the-browser packages, wheels) into web/vendor/.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# files the browser app needs, as (source, path inside the app)
APP_FILES = (
    [(ROOT / "app/Home.py", "Home.py"), (ROOT / "app/ui.py", "ui.py"),
     (ROOT / "app/pages/1_Time_in_Market.py", "pages/1_Time_in_Market.py")]
    + [(p, f"assets/{p.name}") for p in sorted((ROOT / "app/assets").glob("*.png"))]
    + [(p, f"fundprint/{p.name}") for p in sorted((ROOT / "fundprint").glob("*.py"))]
    + [(p, f"rapidfuzz/{p.name}") for p in sorted((ROOT / "web/rapidfuzz_stub").glob("*.py"))]
    + [(ROOT / "data" / n, f"data/{n}") for n in ("benchmark_nav.json", "scheme_categories.json", "manifest.json")]
)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "app").mkdir(parents=True)
    for src, rel in APP_FILES:
        out = DIST / "app" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, out)
    (DIST / "app-manifest.json").write_text(json.dumps({"files": [rel for _, rel in APP_FILES]}))
    for name in ("index.html", "og-image.png", "boot.js", "pyodide-start.mjs", "umami.js", "feedback.js"):
        shutil.copy(ROOT / "web" / name, DIST / name)
    vendor = ROOT / "web/vendor"
    if vendor.exists():
        # web/vendor/wheels is only a download area: its files are already inside vendor/pyodide
        def skip(folder, names):
            drop = set(shutil.ignore_patterns("*.map", "*.d.ts")(folder, names))
            if Path(folder) == vendor:
                drop.add("wheels")
            return drop
        shutil.copytree(vendor, DIST / "vendor", ignore=skip)
    print(f"built {DIST} ({sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file()) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
