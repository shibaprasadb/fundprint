"""Download the third-party files the browser build needs, so the site can serve
them itself and the page never contacts another domain (rules P5 and P7).

Downloads into web/vendor/ (not committed to git; the deploy job runs this):
  stlite/   Streamlit running in the browser
  pyodide/  Python in the browser: the runtime plus only the packages we use
  wheels/   small pure-Python packages that Pyodide doesn't ship

Versions are pinned below. Change them here and nowhere else.
"""
import hashlib
import json
import re
import shutil
import zipfile
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "web" / "vendor"

STLITE = "1.11.0"
PYODIDE = "0.29.3"   # the version stlite 1.11.0 is built against
PYODIDE_BASE = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full"

# packages we ask Pyodide for; their own dependencies are added automatically.
# This list is Streamlit's needs (seen in the browser console) plus ours.
PYODIDE_PACKAGES = [
    "micropip", "packaging", "pandas", "numpy", "scipy", "matplotlib", "pydantic", "python-dateutil",
    "sqlite3", "click", "rich", "cryptography", "charset-normalizer", "pyarrow", "altair",
    "Pillow", "fastparquet", "jsonschema", "Jinja2", "starlette", "anyio", "narwhals",
    "pyodide-http", "typing-extensions", "tornado", "pygments", "ssl", "openssl", "libopenblas",
]
# pure-Python packages from PyPI (the first three are Streamlit's own needs) (the wheel files get served from our own site)
PYPI_WHEELS = ["protobuf>=7.34.1,<8", "itsdangerous<3,>=2.1.2", "python-multipart<1,>=0.0.10", "pdfminer.six==20240706", "casparser==0.8.1",
               "casparser-isin", "colorama"]

CORE_FILES = ["pyodide.mjs", "pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
              "python_stdlib.zip", "pyodide-lock.json"]


def get(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    print("  ", url.split("/")[-1])
    urllib.request.urlretrieve(url, dest)


def fetch_stlite():
    out = VENDOR / "stlite"
    if out.exists():
        return
    print("stlite", STLITE)
    meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/@stlite/browser/{STLITE}"))
    with tempfile.TemporaryDirectory() as tmp:
        tgz = Path(tmp) / "stlite.tgz"
        urllib.request.urlretrieve(meta["dist"]["tarball"], tgz)
        with tarfile.open(tgz) as t:
            t.extractall(tmp, filter="data")
        shutil.copytree(Path(tmp) / "package" / "build", out, ignore=shutil.ignore_patterns("*.map", "*.d.ts"))


def fetch_pyodide():
    out = VENDOR / "pyodide"
    print("pyodide", PYODIDE)
    for f in CORE_FILES:
        get(f"{PYODIDE_BASE}/{f}", out / f)
    lock = json.loads((out / "pyodide-lock.json").read_text())["packages"]
    by_name = {k.lower().replace("_", "-"): v for k, v in lock.items()}
    want, todo = set(), [p.lower().replace("_", "-") for p in PYODIDE_PACKAGES]
    while todo:
        n = todo.pop()
        if n in want or n not in by_name:
            continue
        want.add(n)
        todo += [d.lower().replace("_", "-") for d in by_name[n].get("depends", [])]
    for n in sorted(want):
        get(f"{PYODIDE_BASE}/{by_name[n]['file_name']}", out / by_name[n]["file_name"])
    # keep only what we downloaded, so the browser can't ask for anything else
    keep = {n for n in want}
    for k in list(lock):
        if k.lower().replace("_", "-") not in keep:
            del lock[k]
    full = json.loads((out / "pyodide-lock.json").read_text())
    full["packages"] = lock
    (out / "pyodide-lock.json").write_text(json.dumps(full))
    print(f"   {len(want)} packages")


def fetch_wheels():
    out = VENDOR / "wheels"
    out.mkdir(parents=True, exist_ok=True)
    print("wheels")
    for spec in PYPI_WHEELS:
        subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary=:all:",
                        "--platform", "any", "--python-version", "3.13", "--implementation", "py",
                        "-d", str(out), spec], check=True)
    print("  ", *sorted(p.name for p in out.glob("*.whl")), sep="\n   ")


# what each downloaded wheel needs from the rest of the lock file. casparser's real list includes
# rapidfuzz (no browser build), so it is left out on purpose; rapidfuzz/ in the app is a stand-in.
WHEEL_DEPENDS = {
    "casparser": ["pydantic", "python-dateutil", "click", "colorama", "rich", "pdfminer-six", "casparser-isin"],
    "pdfminer-six": ["charset-normalizer", "cryptography"],
}


def register_wheels():
    """Copy our wheels next to Pyodide's and list them in its lock file, so every
    requirement (even Streamlit's own, like protobuf) is found locally."""
    pyo = VENDOR / "pyodide"
    lock_path = pyo / "pyodide-lock.json"
    lock = json.loads(lock_path.read_text())
    for whl in sorted((VENDOR / "wheels").glob("*.whl")):
        dist, version = whl.name.split("-")[:2]
        name = re.sub(r"[-_.]+", "-", dist).lower()
        shutil.copy(whl, pyo / whl.name)
        with zipfile.ZipFile(whl) as z:
            tops = sorted({n.split("/")[0] for n in z.namelist()
                           if not n.split("/")[0].endswith((".dist-info", ".data")) and not n.endswith(".pth")})
        lock["packages"][name] = {
            "name": name, "version": version, "file_name": whl.name, "install_dir": "site",
            "sha256": hashlib.sha256(whl.read_bytes()).hexdigest(), "package_type": "package",
            "imports": [t.removesuffix(".py") for t in tops], "depends": WHEEL_DEPENDS.get(name, []),
        }
    lock_path.write_text(json.dumps(lock))
    print("registered", len(list((VENDOR / "wheels").glob("*.whl"))), "wheels in the lock file")


if __name__ == "__main__":
    fetch_stlite()
    fetch_pyodide()
    fetch_wheels()
    register_wheels()
