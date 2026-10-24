"""Spec 008: load the page, go offline, then use the whole app. Nothing may need the network after start-up.

Needs a full build (scripts/fetch_vendor.py, then scripts/build_web.py) and Playwright with its browsers
(`python -m playwright install chromium webkit`). Skipped otherwise, so the quick test run still works.
Uses only the synthetic test statement.
"""
import functools
import http.server
import os
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FIXTURE = ROOT / "tests/fixtures/sample_cas_locked.pdf"   # synthetic
PASSWORD = "secret123"                                     # the fixture's test password
# The deploy job sets this, so the test can never be skipped there by accident.
REQUIRED = os.environ.get("FUNDPRINT_OFFLINE_TEST") == "required"

try:
    from playwright import sync_api
except ImportError:
    if REQUIRED:
        raise
    pytest.skip("needs Playwright", allow_module_level=True)
if not (DIST / "vendor").exists():
    if REQUIRED:
        raise RuntimeError("needs a full build in dist/")
    pytest.skip("needs a full build in dist/", allow_module_level=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves dist/ at /fundprint/, like the live site, but tells the browser not to rely on its cache,
    so the test passes because of the fix and not because a file happened to be cached."""

    def translate_path(self, path):
        return super().translate_path(path.removeprefix("/fundprint"))

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site():
    # The page asks for 100+ files at once; Python's default queue of 5 would drop some of them.
    http.server.ThreadingHTTPServer.request_queue_size = 256
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(DIST)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/fundprint/"
    server.shutdown()


def wait_until_drawn(page, quiet_ms=1500, limit_s=120):
    """Wait until Streamlit has finished drawing: no spinner or "running" sign for a short while."""
    busy = page.locator('[data-testid="stSpinner"], [data-testid="stStatusWidget"]')
    page.wait_for_timeout(500)
    for _ in range(int(limit_s * 1000 / 250)):
        if busy.count() == 0:
            page.wait_for_timeout(quiet_ms)
            if busy.count() == 0:
                return
        page.wait_for_timeout(250)
    raise AssertionError("the page never finished drawing")


def results_drawn(page):
    """The results page is complete: its own table (not the checklist on Home) and the charts."""
    page.locator('[data-testid="stMarkdown"] table', has_text="Held for").wait_for(timeout=120_000)
    wait_until_drawn(page)
    charts = page.locator('[data-testid="stImage"] img, [data-testid="stPyplot"] img, img[src^="blob:"]').count()
    assert charts >= 2, f"only {charts} chart(s) drawn"


@pytest.mark.parametrize("engine", ["chromium", "webkit"])   # webkit is the engine of every iPhone browser
def test_whole_flow_works_offline_after_load(site, engine):
    with sync_api.sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(site)
        page.wait_for_selector("#loading-note", state="detached", timeout=240_000)
        page.locator('[data-testid="stFileUploaderDropzone"]').wait_for()
        page.wait_for_timeout(3000)

        late = []
        context.on("request", lambda r: late.append(r.url))
        context.set_offline(True)

        page.locator('input[type="file"]').set_input_files(str(FIXTURE))
        page.locator('input[type="password"]').fill(PASSWORD, timeout=20_000)
        page.get_by_role("button", name="Show my results").click()
        results_drawn(page)
        page.get_by_text("Equity funds only").click()
        page.get_by_text("Funds included").wait_for(timeout=30_000)
        results_drawn(page)
        with page.expect_download():
            page.get_by_role("button", name="Download PNG").first.click()
        wait_until_drawn(page)

        errors = page.locator('[data-testid="stAlertContentError"], [data-testid="stException"]').all_inner_texts()
        browser.close()
    assert not errors, errors
    # blob: addresses are charts drawn in memory. Umami page views may be tried; offline they just fail.
    assert [u for u in late if not u.startswith("blob:") and "umami" not in u] == [], "files fetched after start-up"
