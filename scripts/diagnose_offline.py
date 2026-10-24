"""Find out what the page downloads after it has loaded, and what breaks when the network goes off.

Diagnosis only: this changes nothing in the app. It drives a real browser (Playwright, Chromium)
through the whole flow and writes one JSON log per scenario:

  online       load, then sample data, upload the test statement, password, results
  offline      load online, go offline, then the same flow
  upload-only  load online, go offline, upload straight away (the reported bug)
  reconnect    like upload-only, then back online and choose the file again (no reload)
  refresh      after a full online run, go offline and reload the page

Only synthetic files are used: the sample portfolio and tests/fixtures/sample_cas_locked.pdf.

Usage (needs `pip install playwright` and `playwright install chromium`; not part of the app):
  python scripts/build_web.py
  python scripts/diagnose_offline.py                 # serves dist/ locally at /fundprint/
  python scripts/diagnose_offline.py --url https://lab.shibaprasadb.com/fundprint/
"""
import argparse
import functools
import http.server
import json
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CACHE_CONTROL = "max-age=600"   # what GitHub Pages sends
FIXTURE = ROOT / "tests/fixtures/sample_cas_locked.pdf"
PASSWORD = "secret123"   # the fixture's test password, not a real one


# ---- a local copy of the site, served the way GitHub Pages serves it ----

class PagesLikeHandler(http.server.SimpleHTTPRequestHandler):
    """Serves dist/ under /fundprint/ with GitHub Pages' cache header (max-age=600)."""

    def translate_path(self, path):
        path = urlparse(path).path
        if not path.startswith("/fundprint/"):
            return str(DIST / "__missing__")
        return super().translate_path(path[len("/fundprint"):])

    def end_headers(self):
        self.send_header("Cache-Control", CACHE_CONTROL)
        super().end_headers()

    def log_message(self, *args):
        pass


def serve_dist():
    handler = functools.partial(PagesLikeHandler, directory=str(DIST))
    # The page asks for well over 100 files at once. Python's default queue of 5 waiting connections
    # drops some of them (connection reset), which looks like an app bug but is the test server.
    http.server.ThreadingHTTPServer.request_queue_size = 256
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}/fundprint/"


# ---- what counts as private, for the privacy check ----

def private_markers():
    """Strings that must never appear in a request: the password, bits of the PDF, parsed holdings."""
    import sys
    sys.path.insert(0, str(ROOT))
    from fundprint.parse import parse_cas
    pdf = FIXTURE.read_bytes()
    parsed = parse_cas(pdf, PASSWORD)
    markers = {PASSWORD}
    markers |= {f.split("/")[0].strip() for f in parsed.schemes.folio}
    markers |= set(parsed.schemes["scheme"]) | set(parsed.schemes["isin"])
    return markers, [pdf[i:i + 64] for i in range(0, len(pdf), len(pdf) // 8)][:8]


# ---- recording ----

def group_of(url):
    u = urlparse(url)
    p = u.path
    if "umami" in u.netloc or p.endswith("/umami.js"):
        return "analytics"
    if u.scheme in ("data", "blob"):
        return "inline (data:/blob:)"
    if "/vendor/stlite/assets/" in p or p.endswith(".css"):
        return "font or CSS" if p.endswith((".woff", ".woff2", ".ttf", ".css")) else "stlite asset"
    if "/vendor/stlite/wheels/" in p:
        return "Python package"
    if "/vendor/stlite/" in p and p.endswith(".js"):
        return "stlite chunk"
    if "/vendor/pyodide/" in p:
        name = p.rsplit("/", 1)[-1]
        if name.startswith(("pyodide", "python_stdlib")):
            return "Pyodide core"
        return "Python package"
    if "/app/" in p or p.endswith("app-manifest.json"):
        return "app file"
    return "other"


class Recorder:
    def __init__(self, context, page):
        self.t0 = None
        self.step = "boot"
        self.rows = []
        self.console = []
        self.by_req = {}
        context.on("request", self.on_request)
        context.on("requestfinished", self.on_finished)
        context.on("requestfailed", self.on_failed)
        page.on("console", lambda m: m.type in ("error", "warning") and self.console.append(
            {"t": self.now(), "step": self.step, "type": m.type, "text": m.text[:300]}))
        page.on("pageerror", lambda e: self.console.append(
            {"t": self.now(), "step": self.step, "type": "pageerror", "text": str(e)[:300]}))

    def now(self):
        return None if self.t0 is None else round(time.monotonic() - self.t0, 2)

    def on_request(self, req):
        row = {"t": self.now(), "step": self.step, "url": req.url, "host": urlparse(req.url).netloc,
               "type": req.resource_type, "method": req.method, "group": group_of(req.url),
               "status": None, "size": None, "failure": None, "post": req.post_data_buffer}
        self.by_req[id(req)] = row
        self.rows.append(row)

    def on_finished(self, req):
        row = self.by_req.get(id(req))
        if row is None:
            return
        try:
            resp = req.response()
            row["status"] = resp.status if resp else None
            row["from_cache"] = bool(resp and resp.from_service_worker) or None
            row["size"] = req.sizes()["responseBodySize"]
        except Exception:
            pass

    def on_failed(self, req):
        row = self.by_req.get(id(req))
        if row is not None:
            row["failure"] = req.failure

    def privacy(self, markers, pdf_chunks):
        hits, outside = [], set()
        for r in self.rows:
            body = r["post"] or b""
            text = r["url"] + body.decode("utf-8", "replace")
            for m in markers:
                if m and m in text:
                    hits.append({"url": r["url"], "marker": "<redacted>"})
            if any(c in body for c in pdf_chunks):
                hits.append({"url": r["url"], "marker": "PDF bytes"})
            if r["host"] and not r["host"].startswith(("127.0.0.1", "lab.shibaprasadb.com")):
                outside.add(r["host"])
        return {"private_data_found_in": hits, "outside_hosts": sorted(outside)}

    def dump(self):
        out = []
        for r in self.rows:
            r = dict(r)
            post = r.pop("post") or b""
            r["post_bytes"] = len(post)
            if r["group"] == "analytics" and post:   # Umami's own payload: page path and title only
                r["post_body"] = post.decode("utf-8", "replace")
            out.append(r)
        return out


# ---- the flow ----

def wait_ready(page, timeout=240_000):
    """T0: the loading note is gone AND the whole home page is drawn (the uploader is there, Streamlit
    is idle). The note alone is not enough: on the live site it goes before the uploader is drawn."""
    page.wait_for_selector("#loading-note", state="detached", timeout=timeout)
    page.get_by_role("button", name="Try it with a sample portfolio").wait_for(timeout=timeout)
    page.locator('[data-testid="stFileUploaderDropzone"]').wait_for(timeout=timeout)
    settle(page, quiet=3)


def settle(page, quiet=1.5, limit=60):
    """Wait until Streamlit has finished its run (no 'running' indicator) and things are quiet."""
    end = time.monotonic() + limit
    page.wait_for_timeout(500)
    while time.monotonic() < end:
        busy = page.locator('[data-testid="stStatusWidget"], [data-testid="stSpinner"]').count()
        if not busy:
            page.wait_for_timeout(quiet * 1000)
            if not page.locator('[data-testid="stStatusWidget"], [data-testid="stSpinner"]').count():
                return
        page.wait_for_timeout(300)


def broken_widgets(page):
    """Text of any element-level error box Streamlit drew (for example a chunk that failed to load)."""
    texts = page.locator('[data-testid="stAlertContentError"], [data-testid="stException"]').all_inner_texts()
    return sorted({t.strip()[:200] for t in texts})


def check(rec, page, report, label, fn):
    rec.step = label
    entry = {"step": label, "ok": True, "error": None}
    try:
        fn()
        settle(page)
    except Exception as e:  # keep going: we want the whole picture, not the first failure
        entry["ok"] = False
        entry["error"] = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
    entry["broken_widgets"] = broken_widgets(page)
    entry["at"] = rec.now()
    report.append(entry)
    return entry["ok"]


def results_tour(rec, page, report, tag):
    def charts_drawn():
        page.get_by_text("Returns by holding period").wait_for(timeout=60_000)
        settle(page, limit=120)
        n = page.locator('[data-testid="stImage"] img, [data-testid="stPyplot"] img, img[src^="blob:"]').count()
        if n < 2:
            raise RuntimeError(f"only {n} chart image(s) drawn")
        page.locator('[data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stMarkdown"] table').first.wait_for(timeout=15_000)

    check(rec, page, report, f"{tag}: results page and charts", charts_drawn)
    check(rec, page, report, f"{tag}: radio 'Equity funds only'",
          lambda: page.get_by_text("Equity funds only").click(timeout=10_000))
    check(rec, page, report, f"{tag}: expander 'Funds included'",
          lambda: page.get_by_text("Funds included").click(timeout=10_000))
    check(rec, page, report, f"{tag}: radio back to 'All funds'",
          lambda: page.get_by_text("All funds", exact=True).click(timeout=10_000))
    check(rec, page, report, f"{tag}: expander 'How this is calculated'",
          lambda: page.get_by_text("How this is calculated").click(timeout=10_000))

    def download():
        with page.expect_download(timeout=10_000):
            page.get_by_role("button", name="Download PNG").first.click(timeout=10_000)
    check(rec, page, report, f"{tag}: download a chart", download)


def go_home(page):
    page.locator('[data-testid="stSidebarNav"] a').filter(has_text="Home").first.click(timeout=10_000)
    page.get_by_text("Already have your statement?").wait_for(timeout=30_000)


def upload_flow(rec, page, report):
    check(rec, page, report, "upload the test statement",
          lambda: page.locator('input[type="file"]').set_input_files(str(FIXTURE), timeout=10_000))

    def password():
        box = page.locator('input[type="password"]')
        box.wait_for(timeout=20_000)
        box.fill(PASSWORD)
        page.get_by_role("button", name="Show my results").click(timeout=10_000)
    ok = check(rec, page, report, "enter password and press 'Show my results'", password)
    if ok:
        results_tour(rec, page, report, "statement")


def full_flow(rec, page, report):
    rec.step = "idle after ready"
    page.wait_for_timeout(5000)
    report.append({"step": "idle after ready", "ok": True, "at": rec.now(), "broken_widgets": broken_widgets(page)})
    if check(rec, page, report, "click 'Try it with a sample portfolio'",
             lambda: page.get_by_role("button", name="Try it with a sample portfolio").click(timeout=10_000)):
        results_tour(rec, page, report, "sample")
    check(rec, page, report, "back to Home", lambda: go_home(page))
    upload_flow(rec, page, report)


def run(pw, url, scenario, out_dir, markers, pdf_chunks, block_umami, engine="chromium"):
    browser = getattr(pw, engine).launch()
    context = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 900})
    if block_umami:
        # Keep diagnostic runs out of the live visit counts. The request is still logged first.
        context.route("https://gateway.umami.is/**", lambda r: r.abort())
    page = context.new_page()
    rec = Recorder(context, page)
    report = []
    page.goto(url)
    try:
        wait_ready(page)
    except PWTimeout:
        page.screenshot(path=str(out_dir / f"{scenario}-boot-failed.png"))
        (out_dir / f"{scenario}-boot-failed.json").write_text(json.dumps(
            {"console": rec.console, "requests": rec.dump()}, indent=1, default=str))
        browser.close()
        print(f"{scenario:12} the page never became ready (online); see {scenario}-boot-failed.*")
        return
    rec.t0 = time.monotonic()
    for r in rec.rows:          # everything before T0 is marked as such
        r["t"] = r["t"] if r["t"] is not None else "before T0"
    rec.step = "ready (T0)"

    if scenario == "online":
        full_flow(rec, page, report)
    elif scenario == "offline":
        context.set_offline(True)
        full_flow(rec, page, report)
    elif scenario == "upload-only":
        context.set_offline(True)
        upload_flow(rec, page, report)
    elif scenario == "reconnect":
        context.set_offline(True)
        upload_flow(rec, page, report)
        context.set_offline(False)
        rec.step = "back online"
        check(rec, page, report, "back online: choose the file again",
              lambda: page.locator('input[type="file"]').set_input_files(str(FIXTURE), timeout=10_000))
        check(rec, page, report, "back online: password box shows",
              lambda: page.locator('input[type="password"]').wait_for(timeout=20_000))
    elif scenario == "refresh":
        full_flow(rec, page, report)
        context.set_offline(True)
        rec.step = "reload while offline"
        try:
            page.reload(timeout=30_000)
            reloaded = "page loaded"
        except Exception as e:
            reloaded = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
        try:
            wait_ready(page, timeout=90_000)
            app = "app became ready"
        except PWTimeout:
            app = "app did not become ready within 90 s"
        page.screenshot(path=str(out_dir / "refresh-offline.png"))
        report.append({"step": "reload while offline", "ok": app == "app became ready", "reload": reloaded,
                       "app": app, "at": rec.now(), "body_text": page.locator("body").inner_text()[:300]})

    result = {"scenario": scenario, "url": url, "steps": report, "console": rec.console,
              "privacy": rec.privacy(markers, pdf_chunks), "requests": rec.dump()}
    (out_dir / f"{scenario}.json").write_text(json.dumps(result, indent=1, default=str))
    browser.close()
    late = [r for r in result["requests"] if isinstance(r["t"], (int, float))]
    failed = [r for r in late if r["failure"]]
    print(f"{scenario:12} steps ok {sum(s['ok'] for s in report)}/{len(report)}  "
          f"requests {len(result['requests'])}  after T0 {len(late)}  failed after T0 {len(failed)}  "
          f"outside hosts {result['privacy']['outside_hosts']}  private hits {len(result['privacy']['private_data_found_in'])}")


def main():
    global DIST, CACHE_CONTROL
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="site to test (default: serve dist/ locally)")
    ap.add_argument("--scenarios", default="online,offline,upload-only,refresh")
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "fundprint-diagnosis"))
    ap.add_argument("--dist", help="folder to serve instead of dist/ (for trying a fix)")
    ap.add_argument("--cache-control", default=CACHE_CONTROL, help="header for the local server; no-cache "
                    "shows what happens once the browser's copy is out of date")
    ap.add_argument("--browser", default="chromium", choices=["chromium", "webkit"],
                    help="webkit is the engine behind Safari and every iPhone browser")
    ap.add_argument("--allow-umami", action="store_true", help="let page views reach Umami (live site only)")
    args = ap.parse_args()
    DIST = Path(args.dist).resolve() if args.dist else DIST
    CACHE_CONTROL = args.cache_control
    url = args.url or serve_dist()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    markers, pdf_chunks = private_markers()
    with sync_playwright() as pw:
        for s in args.scenarios.split(","):
            run(pw, url, s, out_dir, markers, pdf_chunks, block_umami=not args.allow_umami, engine=args.browser)


if __name__ == "__main__":
    main()
