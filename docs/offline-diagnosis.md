# Offline diagnosis: why Fundprint breaks when the network drops

**Status:** diagnosis, 22 Oct 2026. Option A3 below was approved and is built as [spec 008](specs/008-offline.md).

**Symptom.** Load the page online, turn Wi-Fi off, upload a statement: the password box is replaced by
`TypeError: Failed to fetch dynamically imported module: …/vendor/stlite/TextInput-dPTdIBJQ-DoloAT-p.js`.

**How this was measured.** `scripts/diagnose_offline.py` drives Chromium (and WebKit, the engine behind every
iPhone browser) through the whole flow with Playwright: sample data, then upload
`tests/fixtures/sample_cas_locked.pdf` (synthetic), then password, then every part of the results page (both
radio choices, both expanders, a chart download). It logs every request with its time from **T0**. T0 is when the
loading note has gone, the home page is fully drawn (uploader included) and Streamlit is idle. Runs were made
against the live site and against a local copy of `dist/` served the way GitHub Pages serves it
(`Cache-Control: max-age=600`). No real statement was used anywhere. To repeat it:

```bash
python scripts/build_web.py && python scripts/diagnose_offline.py --scenarios online,offline,upload-only,reconnect,refresh
```

Logs (JSON, one per scenario) go to a temporary folder; `--url` points it at the live site and `--browser webkit`
switches engine.

## What the build looks like

| Part | Where it comes from | Notes |
|---|---|---|
| stlite 1.11.0 | npm tarball `@stlite/browser`, hash-pinned in `scripts/fetch_vendor.py`, `package/build` copied to `web/vendor/stlite/` | 201 JS chunks (28.3 MB raw, 7.3 MB gzip), names carry content hashes (`TextInput-dPTdIBJQ-DoloAT-p.js`). Loaded with `import()` relative to `stlite.js`. |
| Fonts, CSS, one `.wasm` | `vendor/stlite/assets/` and `vendor/stlite/stlite.css` (same tarball) | Self-hosted. Nothing from Google Fonts or any other host. |
| Pyodide 0.29.3 | Downloaded at **build time** from `cdn.jsdelivr.net/pyodide/v0.29.3/full`, hash-checked, served from `/fundprint/vendor/pyodide/` | Started by `web/pyodide-start.mjs`. The browser never calls jsdelivr. |
| Python packages | stlite `requirements` in `web/boot.js`, installed **at boot** from the local `pyodide-lock.json` (our wheels are added to it at build time) | No runtime `micropip` from PyPI. |
| Service worker, manifest | None | `lab.shibaprasadb.com/sw.js` is a 404. |
| Cache headers | GitHub Pages: `cache-control: max-age=600` plus an ETag | Cannot be changed on Pages. |

## 1. Late requests (everything after T0)

Online run. Raw sizes are from the local copy; wire sizes are gzip as sent by the live site.

| Step that triggered it | Group | Files | Raw | On the wire | Examples |
|---|---|---|---|---|---|
| Idle for 5 s after T0 | – | 0 | – | – | |
| "See it with sample data" → results page | stlite chunk | 45 | 3.3 MB | 0.78 MB | `PageLink`, `Radio`, `ImageList` (charts), `DownloadButton`, `Spinner`, `DataFrame` and its helpers (`styled-components`, `pandasStylerUtils`, d3 parts) |
| same | stlite asset | 1 | 5.5 MB | 1.7 MB | `assets/1b1a876c211e4f13.wasm` (parquet-wasm, used by the table) |
| same | analytics | 1 | – | – | Umami page view |
| Radio, expanders, chart download | – | 0 | – | – | |
| Back to Home | analytics | 1 | – | – | Umami page view |
| Upload the test statement | stlite chunk | 8 | 24 KB | 11 KB | `TextInput`, `Input`, `TextField`, `InputInstructions`, `useTextField` … |
| Password → results → every section | analytics | 1 | – | – | Umami page view |
| Any step | Pyodide core | **0** | | | |
| Any step | Python package | **0** | | | |
| Any step | font or CSS | **0** | | | |

Whichever path reaches the results page first (sample or own statement) pulls the 45 chunks and the wasm. Up to
T0 the page loads 110 files (66 MB raw).

**Edge case seen on the live site.** The page's own "ready" signal (the loading note going away) fires about
0.3 s before the home page finishes drawing. In that gap 5 more chunks and 2 fonts load, including the file
uploader's own chunk. Going offline inside that gap broke the uploader itself, not just the password box.

### What breaks offline

| Scenario | Result |
|---|---|
| Load online, go offline, sample then upload | 5 of 11 steps pass. No charts, no table, no radio, no download buttons, no password box. Each shows the same `Failed to fetch dynamically imported module` error. Only plain text and expanders work. |
| Load online, go offline, upload straight away | Exactly the reported error (live and local). The password box never appears. WebKit fails the same way (`Importing a module script failed.`). |
| Same, then back online and choose the file again | **Still broken.** The browser keeps the failed import for the life of the page and does not even retry the request. Only a reload recovers. |
| Full successful online run, then offline and reload | The reload fails on the HTML page itself (`net::ERR_INTERNET_DISCONNECTED`), so the browser shows its own offline page. Nothing of the app loads. |

### Privacy check (same runs, live and local, online and offline)

- No request URL or body held the password, the folio number, any scheme name or ISIN, or any of eight 64-byte
  slices taken from the PDF. The upload step makes no network request apart from the `TextInput` chunk: the file
  goes from the page to Python in memory.
- The only host other than `lab.shibaprasadb.com` was `gateway.umami.is`: one page view on load and one on each page
  switch. Each carries the website id, screen size, language, page title (`Fundprint`, `Fundprint · Time in Market`),
  hostname, page path (`/fundprint/`, `/fundprint/Time_in_Market`) and the previous path. There is no event data
  and nothing from the statement. (During the live runs these requests were logged, then blocked, so test runs did
  not count as visits.)

## 2. Root cause

stlite ships Streamlit's front end split into many small files, one per widget type, and fetches a widget's file
the first time that widget appears on screen. The home page uses only a few widget types. So the password box, the
radio, the chart images, the download buttons and the table (with its 5.5 MB wasm) are fetched only when they first
appear, which is after the user has gone offline. A failed fetch then stays failed until the page is reloaded.
Python and all its packages are fully loaded at start-up; nothing on the Python side is fetched late.

## 3. Fix options

Each option was judged against the same flow, offline, in Chromium and WebKit. "Prototype" means it was tried on a
scratch copy of `dist/` served with `no-cache`, so the browser's HTTP cache could not hide a problem.

| Option | Extra on first load | Complexity | Works after an offline refresh? | Notes |
|---|---|---|---|---|
| **A1. `modulepreload` for all of `vendor/stlite/*.js`**, generated at build time | +201 requests, +7.3 MB gzip, 28 MB of JS for the phone to parse (includes Plotly 6.4 MB and DeckGL 4 MB, which we never use) | Low | No | No upkeep, but heavy on phones, where the app has already had memory trouble (spec 007). Does **not** cover the table's wasm (see A2). |
| **A2. `modulepreload` for only the widgets we use**, generated at build time | +59 requests. With the wasm preloaded too: 66 → 76 MB raw before T0 | Low: ~30 lines in `build_web.py` plus a list of widget names | No | The build walks stlite's static imports from the widget files we use. That walk covered all 53 late chunks. **Prototype: Chromium passed everything. WebKit loaded every chunk from the preloads, but ignored the wasm preload, so the table broke offline.** A `<link rel="preload">` is not enough for the wasm on iPhones. |
| **A3. A2 + show the results table as a plain Markdown table** instead of `st.dataframe` | +27 requests, **+0.9 MB raw** (66.0 → 66.8 MB) | Low: A2 plus ~4 lines in `app/pages/1_Time_in_Market.py` | No | Streamlit decodes every pandas table (`st.dataframe` **and** `st.table`, both tested) with the 5.5 MB wasm. A Markdown table needs neither the wasm nor the 3 MB of grid code. The table is 4 rows of percentages, so little is lost: no column sort or resize, and no CSV button in the grid toolbar. **Prototype: passed every step in Chromium and WebKit, with zero requests after T0.** |
| **B. Service worker** at `/fundprint/sw.js` (scope `/fundprint/`) that precaches the app | Same downloads as today plus the late set, but kept on the device after the tab closes (~60–75 MB in Cache Storage) | High: versioned caches per build, update handling (daily data refresh), never caching Umami or anything but GET, a kill switch, Safari quirks | **Yes**, the only option that does | The app's code (not user data) would stay on the device, so `PRIVACY.md` and the "What is stored" table need a new row and the owner's sign-off. A stuck or buggy worker keeps users on an old version until it is replaced. It does not widen the shared-origin risk, but it is one more thing on that origin to keep correct. |
| **C. Render every widget at start-up** (hidden text input, radio, table, image, download button, page link) | Same files as A2 | Medium and fragile: dummy widgets in `Home.py`, CSS to hide them, breaks when Streamlit moves its split points | No | Would load and keep the wasm in memory for sure, but adds work to start-up on phones. A3 gets the same result without hidden widgets. Not prototyped. |
| **D. Load every Python package at boot** | – | – | – | **Already the case.** Zero Python or Pyodide requests after T0, so this does nothing for the bug. |

## 4. Recommended fix

**A3: build-time `modulepreload` for the widgets the app uses, and the results table as a Markdown table.**

With A3 this sentence is true in both Chromium and WebKit: *"Load the page, wait until it is ready, turn on
airplane mode, upload your statement, and it still works."* It costs under 1 MB extra on first load. It does not
make an offline **refresh** work; only a service worker (B) does that. Treat B as a separate decision.

Prototype results (A3, scratch copy, `no-cache`):

| Browser | Offline, sample then upload (17 steps) | Offline, upload straight away (8 steps) | Requests after T0 | Private data in any request |
|---|---|---|---|---|
| Chromium | 17/17 | 8/8 | 0 | none |
| WebKit | 17/17 | 8/8 | 0 (only in-memory `blob:` chart images) | none |

The preload list for A3 starts from 6 widget files: `TextInput`, `Radio`, `ImageList` (charts), `DownloadButton`,
`PageLink`, `Spinner`. The walk follows each file's static imports, plus `import()` calls to files of the same
widget, and gives 36 files. If a later change adds a new widget type, the offline test fails until the name is added.

One limit: a preload that fails during the initial load (a flaky phone connection) is not retried, so that widget
would again load late. The fix makes the app work offline once loaded; it cannot guarantee the load itself.

Files it would change:
- `scripts/build_web.py`: list the widget files we use, walk their imports, write the `modulepreload` tags into
  `dist/index.html` at a marker.
- `web/index.html`: the marker comment where the tags go.
- `app/pages/1_Time_in_Market.py`: draw the results table with `st.markdown` (fixed column names, bucket labels
  and percentages only, no text from the PDF) instead of `st.dataframe`.
- `tests/test_offline.py` (new) and a pinned `playwright` in `requirements-dev.txt` / `requirements-ci.txt`.
- `.github/workflows/deploy.yml`: install Chromium and WebKit and run the offline test after `build_web.py`.
- `docs/specs/008-offline.md` (new spec).
- `README.md` / `PRIVACY.md`: add the airplane-mode check to "how to verify", only once the test passes.
- Optional: in `web/boot.js`, remove the loading note only once the home page is fully drawn, so "ready" means ready.

## 5. Proposed test

`tests/test_offline.py`, next to `tests/test_privacy.py`. It skips itself when Playwright or `dist/` is missing, so
the normal `pytest -q` keeps working. Both were checked by running this exact test: today's build **fails** in
Chromium and WebKit (timed out waiting for the password box), and the A3 prototype **passes** in both. Serving with `no-cache` makes sure it
passes because of the fix, not because of the browser's HTTP cache. `scripts/diagnose_offline.py` already runs this
flow and more (sample data, both radio choices, expanders) if a fuller check is wanted.

```python
"""Load the page, go offline, then use the whole app: nothing may need the network after start-up."""
import functools
import http.server
import threading
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FIXTURE = ROOT / "tests/fixtures/sample_cas_locked.pdf"   # synthetic
pytestmark = pytest.mark.skipif(not (DIST / "vendor").exists(), reason="run scripts/build_web.py first")


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        return super().translate_path(path.removeprefix("/fundprint"))

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")   # no help from the HTTP cache
        super().end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def site():
    http.server.ThreadingHTTPServer.request_queue_size = 256   # the page asks for 100+ files at once
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(DIST)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/fundprint/"
    server.shutdown()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_whole_flow_works_offline_after_load(site, engine):
    with sync_api.sync_playwright() as pw:
        browser = getattr(pw, engine).launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(site)
        page.wait_for_selector("#loading-note", state="detached", timeout=240_000)
        page.locator('[data-testid="stFileUploaderDropzone"]').wait_for()
        page.wait_for_timeout(3000)

        late = []
        context.on("request", lambda r: late.append(r.url))
        context.set_offline(True)

        page.locator('input[type="file"]').set_input_files(str(FIXTURE))
        page.locator('input[type="password"]').fill("secret123", timeout=20_000)   # the fixture's test password
        page.get_by_role("button", name="Show my results").click()
        page.get_by_text("Returns by holding period").wait_for(timeout=120_000)
        page.locator('[data-testid="stMarkdown"] table').first.wait_for(timeout=60_000)   # the results table
        page.get_by_text("Equity funds only").click()
        with page.expect_download():
            page.get_by_role("button", name="Download this chart (PNG)").first.click()

        errors = page.locator('[data-testid="stAlertContentError"]').all_inner_texts()
        browser.close()
        assert not errors, errors
        # blob: URLs are charts drawn in memory; Umami page views are allowed (and fail quietly offline)
        assert [u for u in late if not u.startswith("blob:") and "umami" not in u] == [], "files fetched after start-up"
```

## Other things seen along the way (not this bug)

1. **Reloading the results page online gives a 404.** Streamlit puts `/fundprint/Time_in_Market` in the address
   bar, and GitHub Pages has no such file (`curl -I` returns 404).
2. **Start-up sometimes never finishes**, with no message. Once on the live site, 20 Python package downloads
   never completed and the loading note stayed for more than 4 minutes. This was after many back-to-back test
   loads, so it may have been throttling, but the page has no timeout or error for it. Three similar local stalls
   all happened before a fault in the test server was fixed: it dropped connections when 100+ files were asked
   for at once. None happened after that. Not investigated further.
3. **One "Couldn't read this file" on the valid fixture**, online, in 1 of 5 local online runs. It did not happen
   again. Not investigated.
