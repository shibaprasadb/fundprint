"""Build the public data files in /data. Runs daily on GitHub Actions.

The browser never calls mfapi.in or AMFI. This script (on a GitHub server)
fetches the public data and commits it as static files that the app reads.

If a fetch fails or returns much less than yesterday, the old file is kept
and the script exits with an error so the job fails loudly.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fundprint.benchmark import BENCH  # noqa: E402
from fundprint.classify import asset_class, category_text  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
MFAPI = f"https://api.mfapi.in/mf/{BENCH}"
AMFI = "https://portal.amfiindia.com/spages/NAVAll.txt"
MAX_SHRINK = 0.10   # refuse to overwrite if the new file is >10% smaller


def fetch_benchmark():
    raw = requests.get(MFAPI, timeout=60).json()["data"]
    rows = [{"date": datetime.strptime(r["date"], "%d-%m-%Y").strftime("%Y-%m-%d"), "nav": float(r["nav"])}
            for r in raw]
    return sorted(rows, key=lambda r: r["date"])


def fetch_categories():
    text = requests.get(AMFI, timeout=120).text
    out, category = {}, ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ";" not in line:
            # header lines: fund-house names have no brackets, category lines do
            if "(" in line and "Scheme" in line:
                category = line
            continue
        parts = line.split(";")
        if len(parts) < 6 or parts[0] == "Scheme Code":
            continue
        code, isin1, isin2, name = parts[0], parts[1], parts[2], parts[3]
        for isin in (isin1, isin2):
            if isin and isin != "-":
                out[isin] = {"amfi_code": code, "scheme_name": name, "amfi_category": category,
                             "asset_class": asset_class(category, name)}
    return out


def write_safely(name, new, old_path):
    if old_path.exists():
        old = json.loads(old_path.read_text())
        if len(new) < len(old) * (1 - MAX_SHRINK):
            raise SystemExit(f"{name}: new file has {len(new)} rows vs {len(old)} before; keeping the old one")
    old_path.write_text(json.dumps(new, separators=(",", ":")))
    return len(new)


def main():
    DATA.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bench = fetch_benchmark()
    cats = fetch_categories()
    if not bench or not cats:
        raise SystemExit("A source returned no data; keeping the old files")
    n_bench = write_safely("benchmark_nav", bench, DATA / "benchmark_nav.json")
    n_cats = write_safely("scheme_categories", cats, DATA / "scheme_categories.json")
    (DATA / "manifest.json").write_text(json.dumps({
        "benchmark": {"amfi_code": BENCH, "source": MFAPI, "fetched_at": now, "rows": n_bench,
                      "latest_date": bench[-1]["date"]},
        "scheme_categories": {"source": AMFI, "fetched_at": now, "rows": n_cats},
    }, indent=2))
    print(f"benchmark rows: {n_bench}, ISINs: {n_cats}")


if __name__ == "__main__":
    main()
