"""Checks that the vendor download script pins everything (no network needed)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_vendor", ROOT / "scripts" / "fetch_vendor.py")
fv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fv)

SHA = re.compile(r"^[0-9a-f]{64}$")


def test_every_pypi_wheel_has_an_exact_version():
    for spec_ in fv.PYPI_WHEELS:
        assert re.fullmatch(r"[A-Za-z0-9._-]+==[0-9][A-Za-z0-9.]*", spec_), spec_


def test_every_pypi_wheel_has_a_hash():
    """Each pinned package must have exactly one wheel file in the hash table, and nothing else is listed."""
    prefixes = set()
    for spec_ in fv.PYPI_WHEELS:
        name, version = spec_.split("==")
        prefixes.add(re.sub(r"[-_.]+", "_", name).lower() + "-" + version + "-")
    for prefix in prefixes:
        files = [n for n in fv.WHEEL_SHA256 if re.sub(r"[-_.]+", "_", n).lower().startswith(re.sub(r"[-_.]+", "_", prefix))]
        assert len(files) == 1, prefix
    assert len(fv.WHEEL_SHA256) == len(prefixes)


def test_every_pinned_download_has_a_valid_hash():
    hashes = [fv.STLITE_SHA256, fv.LOCK_SHA256, *fv.PYODIDE_SHA256.values(), *fv.WHEEL_SHA256.values()]
    assert all(SHA.match(h) for h in hashes)
    assert len(set(hashes)) == len(hashes)


def test_all_pyodide_core_files_are_pinned():
    assert set(fv.PYODIDE_SHA256) == {"pyodide.mjs", "pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
                                      "python_stdlib.zip"}
