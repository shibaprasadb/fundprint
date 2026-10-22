"""Assemble the static site in dist/ (the folder that gets published).

dist/ holds everything the browser loads, so the page only ever talks to its
own domain. Run scripts/fetch_vendor.py first to download the third-party
files (stlite, Python-in-the-browser packages, wheels) into web/vendor/.
"""
import json
import re
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

# stlite downloads a widget's code the first time that widget appears on screen. If the network has gone
# by then (airplane mode after the page loaded), the widget breaks with "Failed to fetch dynamically
# imported module". So the code for every kind of widget the app draws is downloaded with the page
# instead (spec 008). When the app starts using a new kind of widget, add its name here;
# tests/test_offline.py fails until you do. Names are the start of the file names in vendor/stlite/.
PRELOAD_WIDGETS = ("TextInput", "Radio", "ImageList", "DownloadButton", "PageLink", "Spinner",
                   "FileUploader", "StreamlitSyntaxHighlighter")
PRELOAD_MARKER = "<!-- preload tags are added here by scripts/build_web.py -->"
STATIC_IMPORT = re.compile(r'(?:from\s*|import\s*)["\']\./([A-Za-z0-9_.\-]+\.js)["\']')
LATE_IMPORT = re.compile(r'import\(\s*["\']\./([A-Za-z0-9_.\-]+\.js)["\']')


def preload_files(stlite_dir, widgets=PRELOAD_WIDGETS):
    """The stlite files the listed widgets need: each widget's own files plus everything they import.

    A widget file often loads its main part later with import(); those are followed only when they
    belong to the same widget, because following every import() would pull in all of stlite.
    """
    stlite_dir = Path(stlite_dir)
    start = []
    for w in widgets:
        found = sorted(f.name for f in stlite_dir.glob(f"{w}-*.js") if f.name.split("-")[0] == w)
        if not found:
            raise SystemExit(f"No stlite file for widget {w!r}. Was stlite updated? Check PRELOAD_WIDGETS.")
        start += found
    seen, todo = set(), start
    while todo:
        name = todo.pop()
        if name in seen or not (stlite_dir / name).exists():
            continue
        seen.add(name)
        code = (stlite_dir / name).read_text()
        todo += STATIC_IMPORT.findall(code)
        todo += [m for m in LATE_IMPORT.findall(code) if m.split("-")[0] == name.split("-")[0]]
    return sorted(seen)


def add_preload_tags(html, names):
    if PRELOAD_MARKER not in html:
        raise SystemExit("web/index.html has lost the preload marker comment")
    tags = "\n".join(f'  <link rel="modulepreload" href="./vendor/stlite/{n}">' for n in names)
    return html.replace("  " + PRELOAD_MARKER, tags) if names else html

# Streamlit puts each page's name in the address bar (/fundprint/Time_in_Market). Reloading that address
# asked GitHub Pages for a file that doesn't exist, so it showed its own 404 page. Each page gets a tiny
# file with that name that sends the browser to the home page (spec 009). After a reload nothing from
# the statement is left anyway, so home is the right place. The file has no script and loads nothing.
REDIRECT_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'">
  <meta http-equiv="refresh" content="0; url=./">
  <meta name="robots" content="noindex">
  <title>Fundprint</title>
</head>
<body>
  <p><a href="./">Go to Fundprint</a></p>
</body>
</html>
"""


def page_address(page_file):
    """The name Streamlit shows in the address bar: the file name without its number and .py."""
    return re.sub(r"^\d+_", "", Path(page_file).stem)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "app").mkdir(parents=True)
    for src, rel in APP_FILES:
        out = DIST / "app" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, out)
    for page in sorted((ROOT / "app/pages").glob("*.py")):
        (DIST / f"{page_address(page)}.html").write_text(REDIRECT_PAGE)
    (DIST / "app-manifest.json").write_text(json.dumps({"files": [rel for _, rel in APP_FILES]}))
    for name in ("index.html", "og-image.png", "boot.js", "pyodide-start.mjs", "umami.js", "feedback.js"):
        shutil.copy(ROOT / "web" / name, DIST / name)
    vendor = ROOT / "web/vendor"
    if vendor.exists():
        index = DIST / "index.html"
        index.write_text(add_preload_tags(index.read_text(), preload_files(vendor / "stlite")))
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
