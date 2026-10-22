# Fundprint: Start-up never hangs silently

> **Status:** Implemented

Start-up downloads about 60 files (Python, its packages, Streamlit). Nothing had a time limit. If one file stopped arriving, the note "First-time load takes 5-10 secs. Almost there…" stayed for good with no message. When a file failed outright, the user saw one of several confusing error boxes, one of them a raw Python traceback (against rule 8).

The diagnosis, with every fault tried and what the user saw, is in [docs/startup-stall-diagnosis.md](../startup-stall-diagnosis.md).

## What the app does

1. **Stalled downloads start again** (`web/pyodide-start.mjs`). Every download from this site made by the Python worker goes through a small wrapper. If no new data arrives for **20 seconds**, the download starts again, at most twice, then once more with no time limit. A slow download that keeps arriving is never cut off. Only this site's `GET` requests are touched.
   - Pyodide asks for each package with its SHA-256 from the lock file. With that set, the browser holds the whole file back until it has all arrived, so a stall looks the same as a slow download. So the wrapper downloads without it and makes the same SHA-256 check itself before handing the file to Pyodide. A file that doesn't match is refused, as before.
2. **After 60 seconds the note says so** (`web/boot.js`): "This is taking longer than usual. A slow or busy connection can cause this." with a **Reload** button. The spinner keeps going.
3. **A failed start-up says so plainly**: "Fundprint could not finish loading. Check your connection and reload the page." with a **Reload** button. This covers stlite's own start-up error (`loadError`) and a failed download of `stlite.js` or the app list, which used to stop `boot.js` before it could show anything.
4. **stlite's own start-up error box is off** (`disableErrorToasts: true`), because it shows the raw error text. Its small progress messages ("Loading Pyodide.", "Installing packages.") stay on, as they are the only sign of progress.

Both messages are fixed text. Nothing from an error, a file name or the page goes into them. The Reload button's click handler lives in `boot.js`, because the security policy blocks handlers written in the HTML.

`boot.js` uses `mount(...)._kernel`, which stlite treats as internal. `tests/test_app.py` checks it is still in the pinned stlite, so an stlite upgrade that removes it fails the tests.

## Not covered

- A file that keeps failing on every try still ends in a message, not a working app. A retry can only help a stall that clears up.
- Timings were checked on a fast local machine. On a slow phone connection 20 s with *no data at all* is still a real stall, but check the numbers there before relying on them.
- Downloads made by the page itself rather than the Python worker (stlite's own script files) are not retried. If one fails, the plain failure message shows.

## Checks

- [x] `tests/test_app.py`: the 60-second note, the two fixed messages and nothing else, `disableErrorToasts`, the `loadError` listener, stlite loaded inside `try`, the 20-second retry with its SHA-256 check, and that the pinned stlite still has `_kernel` and `disableErrorToasts`.
- [x] `scripts/diagnose_startup_stall.py` against the new build: normal start-up ready in 5 s, as before; one package, the Python core (`pyodide.asm.wasm`) or half of all packages hanging on the first try: ready in 25–26 s (never before); a package arriving slowly over 45 s: ready in 50 s, not cut off; a package that never arrives: the 60-second note with Reload; `stlite.js`, the Streamlit wheel or the lock file missing (404): the plain failure message, with no traceback and no other error box.
- [x] The whole flow (sample data, upload, password, every part of the results) in Chromium and WebKit with `scripts/diagnose_offline.py`: 17 of 17 steps.
- [x] `tests/test_offline.py` still passes in Chromium and WebKit.
- [ ] On a phone: normal start-up looks the same as before.
