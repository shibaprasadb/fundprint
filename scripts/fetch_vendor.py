"""Download the third-party files the browser build needs, so the site can serve
them itself and the page never contacts another domain (rules P5 and P7).

Downloads into web/vendor/ (not committed to git; the deploy job runs this):
  stlite/   Streamlit running in the browser
  pyodide/  Python in the browser: the runtime plus only the packages we use
  wheels/   small pure-Python packages that Pyodide doesn't ship

Versions and SHA-256 hashes are pinned below. Change them here and nowhere else. Every file is
checked against its hash; on a mismatch the file is deleted and the script stops. To move to a new
version, download it, work out the new hash, and compare it with what the publisher lists.
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
# pure-Python packages from PyPI (the first three are Streamlit's own needs). Exact versions only.
PYPI_WHEELS = ["protobuf==7.36.2", "itsdangerous==2.2.0", "python-multipart==0.0.32", "pdfminer.six==20240706",
               "casparser==0.8.1", "casparser-isin==2026.6.9", "colorama==0.4.6"]

# SHA-256 of every file we download. The Pyodide packages are checked against the hashes inside
# pyodide-lock.json, and that file is itself checked here before it is used.
STLITE_SHA256 = "dddf3f8d74c1f95915428d03f79ede9031c99ce2db624f8fb7899461952aebd2"  # @stlite/browser tarball
LOCK_SHA256 = "3256ffc76388de0e37f4b34d42ab484268d1afc675179ff97b2a5bb14f84ccac"    # pyodide-lock.json as downloaded
PYODIDE_SHA256 = {
    "pyodide.mjs": "23213d27e9dacbda6f25f955fb38dabfc40ada082c04ee253047ea5dddcaa3b5",
    "pyodide.js": "718d40f1c015dd25ec724cc8fc4e2325d6a45a92ae225121ff6953f224a16f72",
    "pyodide.asm.js": "1263f02b5b26099b96112378156f242dd98b39a8201ba7765e5fe3d455c5ce91",
    "pyodide.asm.wasm": "e2f4ee75b325e35eb31bfb8c613d4dd5098f5502c156a97847686875b5025480",
    "python_stdlib.zip": "4298b6ee445cb724c3973437da47789752b9e6ff4e26619026b283ec801fc46b",
}
WHEEL_SHA256 = {
    "casparser-0.8.1-py3-none-any.whl": "29a6f825426520b66a26654a104cb26695c40cb47c6757fd8472dcdb78248d61",
    "casparser_isin-2026.6.9-py3-none-any.whl": "d5d43765a3479f710914b524a452968b72d21aea6ef199ebad1839553ed7ab76",
    "colorama-0.4.6-py2.py3-none-any.whl": "4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6",
    "itsdangerous-2.2.0-py3-none-any.whl": "c6242fc49e35958c8b15141343aa660db5fc54d4f13a1db01a3f5891b98700ef",
    "pdfminer.six-20240706-py3-none-any.whl": "f4f70e74174b4b3542fcb8406a210b6e2e27cd0f0b5fd04534a8cc0d8951e38c",
    "protobuf-7.36.2-py3-none-any.whl": "bdb3a345d48db958e6ce1f18e508beb0cc981d64f24088427549c866cd039f1e",
    "python_multipart-0.0.32-py3-none-any.whl": "ff6d3f776f16878c894e52e107296ffc890e913c611b1a4ec6c44e2821fe2e23",
}

# Remembers (outside the folder that gets published) that the unpacked stlite folder came from a
# tarball with the right hash, so a second run can tell it is still the checked one.
STLITE_MARKER = VENDOR.parent / ".stlite-sha256"


def sha256_of(data_or_path):
    if isinstance(data_or_path, (bytes, bytearray)):
        return hashlib.sha256(data_or_path).hexdigest()
    h = hashlib.sha256()
    with open(data_or_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(name, expected, actual):
    sys.exit(f"HASH MISMATCH for {name}\n  expected {expected}\n  actual   {actual}\n"
             "The file was deleted and nothing was built.")


def check(path, expected):
    """Stop (and delete the file) if the file does not have the expected SHA-256."""
    actual = sha256_of(path)
    if actual != expected:
        Path(path).unlink(missing_ok=True)
        fail(Path(path).name, expected, actual)


def get(url, dest, sha256):
    """Download a file unless it is already there, and check it either way."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print("  ", url.split("/")[-1])
        urllib.request.urlretrieve(url, dest)
    check(dest, sha256)


def fetch_stlite():
    out = VENDOR / "stlite"
    if out.exists() and STLITE_MARKER.exists() and STLITE_MARKER.read_text().strip() == STLITE_SHA256:
        return
    print("stlite", STLITE)
    shutil.rmtree(out, ignore_errors=True)
    meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/@stlite/browser/{STLITE}"))
    with tempfile.TemporaryDirectory() as tmp:
        tgz = Path(tmp) / "stlite.tgz"
        urllib.request.urlretrieve(meta["dist"]["tarball"], tgz)
        check(tgz, STLITE_SHA256)
        with tarfile.open(tgz) as t:
            t.extractall(tmp, filter="data")
        shutil.copytree(Path(tmp) / "package" / "build", out, ignore=shutil.ignore_patterns("*.map", "*.d.ts"))
    STLITE_MARKER.write_text(STLITE_SHA256)


def fetch_pyodide():
    out = VENDOR / "pyodide"
    out.mkdir(parents=True, exist_ok=True)
    print("pyodide", PYODIDE)
    for f, sha in PYODIDE_SHA256.items():
        get(f"{PYODIDE_BASE}/{f}", out / f, sha)
    # The lock file on disk is rewritten below (trimmed, and our wheels added), so it can never be
    # compared with the original. Read the original again every run and check that instead (120 KB).
    raw = urllib.request.urlopen(f"{PYODIDE_BASE}/pyodide-lock.json").read()
    if sha256_of(raw) != LOCK_SHA256:
        fail("pyodide-lock.json", LOCK_SHA256, sha256_of(raw))
    full = json.loads(raw)
    lock = full["packages"]
    by_name = {k.lower().replace("_", "-"): v for k, v in lock.items()}
    want, todo = set(), [p.lower().replace("_", "-") for p in PYODIDE_PACKAGES]
    while todo:
        n = todo.pop()
        if n in want or n not in by_name:
            continue
        want.add(n)
        todo += [d.lower().replace("_", "-") for d in by_name[n].get("depends", [])]
    for n in sorted(want):
        info = by_name[n]
        get(f"{PYODIDE_BASE}/{info['file_name']}", out / info["file_name"], info["sha256"])
    # keep only what we downloaded, so the browser can't ask for anything else
    for k in list(lock):
        if k.lower().replace("_", "-") not in want:
            del lock[k]
    (out / "pyodide-lock.json").write_text(json.dumps(full))
    print(f"   {len(want)} packages")


def fetch_wheels():
    out = VENDOR / "wheels"
    out.mkdir(parents=True, exist_ok=True)
    print("wheels")
    for old in out.glob("*.whl"):          # a wheel left over from an older version must not be served
        if old.name not in WHEEL_SHA256:
            old.unlink()
    for spec in PYPI_WHEELS:
        subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary=:all:",
                        "--platform", "any", "--python-version", "3.13", "--implementation", "py",
                        "-d", str(out), spec], check=True)
    found = {p.name for p in out.glob("*.whl")}
    if found != set(WHEEL_SHA256):
        sys.exit(f"Wheel files do not match the pinned list.\n  expected {sorted(WHEEL_SHA256)}\n  got      {sorted(found)}")
    for name, sha in WHEEL_SHA256.items():
        check(out / name, sha)
    print("  ", *sorted(found), sep="\n   ")


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
