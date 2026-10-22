"""Make one start-up download hang, fail or crawl, and record what the user sees. Diagnosis only.

This changes nothing in the app. It serves dist/ the way GitHub Pages does (the server from
diagnose_offline.py), breaks one file on purpose, and watches the page in Chromium for WATCH seconds.
Faults come either from Playwright (the browser never gets an answer, a 404, a reset) or from the
test server itself (no answer, half a file, a slow but steady file). No statement is used.
See docs/startup-stall-diagnosis.md.

Usage (needs `pip install playwright` and `playwright install chromium`; not part of the app):
  python scripts/build_web.py
  python scripts/diagnose_startup_stall.py all
  python scripts/diagnose_startup_stall.py baseline hang-pkg-pandas
  DIST=/path/to/changed/copy TAG=fix- python scripts/diagnose_startup_stall.py hang-pkg-pandas

Writes <TAG><scenario>.json and .png into OUT (default: fundprint-stall/ in the temp folder).
"""
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import diagnose_offline  # noqa: E402  (same Pages-like server, queue size 256)
import functools, http.server, threading  # noqa: E402

if os.environ.get("DIST"):
    diagnose_offline.DIST = Path(os.environ["DIST"])

SERVER_FAULT = {}   # path substring -> "headers" (never answer) | "body" (send half, then stop)


class FaultyHandler(diagnose_offline.PagesLikeHandler):
    def do_GET(self):
        for key, kind in SERVER_FAULT.items():
            if key in self.path:
                if kind == "headers":
                    time.sleep(600)
                    return
                if kind == "slow":          # whole file, evenly over about 45 seconds
                    f = self.send_head()
                    if f:
                        data = f.read(); f.close()
                        step = max(1, len(data) // 90)
                        for i in range(0, len(data), step):
                            self.wfile.write(data[i:i + step]); self.wfile.flush(); time.sleep(0.5)
                    return
                if kind == "body":
                    f = self.send_head()
                    if f:
                        data = f.read(); f.close()
                        self.wfile.write(data[: len(data) // 2]); self.wfile.flush()
                        time.sleep(600)
                    return
        return super().do_GET()


def serve_dist():
    handler = functools.partial(FaultyHandler, directory=str(diagnose_offline.DIST))
    http.server.ThreadingHTTPServer.request_queue_size = 256
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}/fundprint/"

from playwright.async_api import async_playwright  # noqa: E402

OUT = Path(os.environ.get("OUT", Path(tempfile.gettempdir()) / "fundprint-stall"))
OUT.mkdir(exist_ok=True)
TAG = os.environ.get("TAG", "")

# name: (url substring, action, extra)   action = hang | 404 | abort | delay
SCENARIOS = {
    "baseline": (None, None, None),
    "hang-pkg-pandas": ("/vendor/pyodide/pandas-", "hang", None),
    "404-pkg-pandas": ("/vendor/pyodide/pandas-", "404", None),
    "abort-pkg-pandas": ("/vendor/pyodide/pandas-", "abort", None),
    "delay30-pkg-pandas": ("/vendor/pyodide/pandas-", "delay", 30),
    "hang-pkg-casparser": ("/vendor/pyodide/casparser-", "hang", None),
    "hang-wasm": ("/vendor/pyodide/pyodide.asm.wasm", "hang", None),
    "404-wasm": ("/vendor/pyodide/pyodide.asm.wasm", "404", None),
    "hang-stdlib": ("/vendor/pyodide/python_stdlib.zip", "hang", None),
    "hang-lock": ("/vendor/pyodide/pyodide-lock.json", "hang", None),
    "404-lock": ("/vendor/pyodide/pyodide-lock.json", "404", None),
    "hang-streamlit-wheel": ("/vendor/stlite/wheels/streamlit-", "hang", None),
    "404-streamlit-wheel": ("/vendor/stlite/wheels/streamlit-", "404", None),
    "hang-stlite-index": ("/vendor/stlite/index-", "hang", None),
    "404-stlite-js": ("/vendor/stlite/stlite.js", "404", None),
    "hang-manifest": ("/app-manifest.json", "hang", None),
    "404-app-file": ("/app/Home.py", "404", None),
    "hang-many-pkgs": ("MANY", "hang", None),   # ~20 wheels hang, like the live incident
    # The first try hangs and a second try works: what a retry should recover from (spec 010)
    "hang-once-pkg-pandas": ("/vendor/pyodide/pandas-", "hang-once", None),
    "hang-once-wasm": ("/vendor/pyodide/pyodide.asm.wasm", "hang-once", None),
    "hang-once-many-pkgs": ("MANY", "hang-once", None),
    # faults made by the server itself, through the real network stack
    "srv-noanswer-pandas": ("/vendor/pyodide/pandas-", "server", "headers"),
    "srv-halfbody-pandas": ("/vendor/pyodide/pandas-", "server", "body"),
    "srv-slow45-pandas": ("/vendor/pyodide/pandas-", "server", "slow"),
    "srv-halfbody-wasm": ("/vendor/pyodide/pyodide.asm.wasm", "server", "body"),
    "srv-noanswer-wasm": ("/vendor/pyodide/pyodide.asm.wasm", "server", "headers"),
}


async def run(name, base, watch):
    pattern, action, extra = SCENARIOS[name]
    SERVER_FAULT.clear()
    if action == "server":
        SERVER_FAULT[pattern] = extra
        pattern = None
    log = {"scenario": name, "events": [], "requests": [], "matched": []}
    t0 = time.monotonic()
    now = lambda: round(time.monotonic() - t0, 1)
    held = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        many = set()
        hung_once = set()
        half = set()

        def matches(url):
            if pattern == "MANY":
                if "/vendor/pyodide/" in url and url.endswith(".whl"):
                    if url not in many:
                        many.add(url)
                        if len(many) % 2 == 0:
                            half.add(url)
                    return url in half          # about half of all wheels
                return False
            return pattern is not None and pattern in url

        async def handler(route):
            url = route.request.url
            if not matches(url):
                await route.continue_()
                return
            log["matched"].append({"t": now(), "url": url.split("/fundprint/")[-1], "action": action})
            if action == "hang" or (action == "hang-once" and url not in hung_once):
                hung_once.add(url)
                held.append(route)          # never answered
            elif action == "hang-once":
                await route.continue_()     # a second try gets the file
            elif action == "404":
                await route.fulfill(status=404, body="Not Found")
            elif action == "abort":
                await route.abort("connectionreset")
            elif action == "delay":
                await asyncio.sleep(extra)
                await route.continue_()

        await ctx.route("**/*", handler)
        page = await ctx.new_page()
        page.on("console", lambda m: m.type in ("error", "warning") and log["events"].append(
            {"t": now(), "kind": "console." + m.type, "text": m.text[:400]}))
        page.on("pageerror", lambda e: log["events"].append({"t": now(), "kind": "pageerror", "text": str(e)[:400]}))
        ctx.on("requestfailed", lambda r: log["events"].append(
            {"t": now(), "kind": "requestfailed", "text": r.url.split("/fundprint/")[-1] + " " + str(r.failure)}))
        page.on("worker", lambda w: log["events"].append({"t": now(), "kind": "worker", "text": w.url[:80]}))

        await page.goto(base, wait_until="commit")
        state, seen_toasts = None, []
        end = time.monotonic() + watch
        while time.monotonic() < end:
            s = await asyncio.wait_for(page.evaluate("""() => {
                const note = document.getElementById('loading-note');
                const toasts = [...document.querySelectorAll('.Toastify__toast')].map(t => t.innerText.trim().slice(0, 300));
                const ready = !!document.querySelector('[data-testid="stFileUploaderDropzone"]');
                const exc = [...document.querySelectorAll('[data-testid="stException"], [data-testid="stAlert"], [role="dialog"]')]
                              .map(e => e.innerText.trim().slice(0, 300));
                return {note: !!note, toasts, ready, exc};
            }"""), 15)
            for t in s["toasts"]:
                if t not in seen_toasts:
                    seen_toasts.append(t)
                    log["events"].append({"t": now(), "kind": "toast", "text": t})
            if s != state:
                log["events"].append({"t": now(), "kind": "state", "text": json.dumps(
                    {"note": s["note"], "ready": s["ready"], "exc": s["exc"], "toasts": len(s["toasts"])})})
                state = s
            if s["ready"] and not s["note"] and name == "baseline":
                await asyncio.sleep(3)
                break
            await asyncio.sleep(1)
        log["final"] = state
        log["final_t"] = now()
        await asyncio.wait_for(page.screenshot(path=str(OUT / f"{TAG}{name}.png")), 30)
        for r in held:
            try:
                await r.abort()
            except Exception:
                pass
        await browser.close()
    (OUT / f"{TAG}{name}.json").write_text(json.dumps(log, indent=1))
    print(f"== {TAG}{name}: note={state['note']} ready={state['ready']} exc={state['exc']} "
          f"toasts={seen_toasts} matched={len(log['matched'])}", flush=True)


async def main():
    names = sys.argv[1:] or ["baseline"]
    if names == ["all"]:
        names = list(SCENARIOS)
    watch = int(os.environ.get("WATCH", 90))
    base = serve_dist()
    for n in names:
        await run(n, base, watch)


asyncio.run(main())
