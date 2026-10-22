# Fundprint: Works offline once loaded

> **Status:** Implemented

If the network dropped after the page had loaded, uploading a statement failed: the password box was replaced by `TypeError: Failed to fetch dynamically imported module: …/TextInput-….js`. Charts, the results table, the radio and the download buttons broke the same way. Coming back online did not help; only a reload did.

The full diagnosis, with request logs and the options weighed, is in [docs/offline-diagnosis.md](../offline-diagnosis.md).

## Why it happened

stlite downloads each widget's code the first time that widget appears on screen. The home page uses only a few kinds of widget, so the code for the password box, charts, buttons and results table was downloaded later, when the user might already be offline. The browser then remembers the failed download for the life of the page. Python and its packages were never the problem: they are all loaded at start-up.

## What the app does

1. **The page downloads the code for every kind of widget the app draws, while it loads.** `scripts/build_web.py` has a short list of widget names (`PRELOAD_WIDGETS`). For each one it finds its files in `vendor/stlite/`, follows what they import, and writes a `<link rel="modulepreload">` tag for each file into `dist/index.html`, where the marker comment is. About 40 small files, under 1 MB, all from this site. If stlite renames a widget, the build stops with a message.
2. **The results table is a plain Markdown table** (`ui.markdown_table`), not `st.dataframe`. Streamlit's table grid, and `st.table` too, needs a 5.5 MB file that it downloads the first time a table is shown, and Safari does not keep a preloaded copy of it. The table has 4 rows of percentages, so only sorting, resizing and the grid's CSV button are lost. Only fixed labels and formatted numbers go into it.

Reloading while offline still does not work: the browser needs the network to load the page itself. Making that work would need a service worker, which would keep the app's files on the device. That is a separate decision.

## Adding a new kind of widget

Add its name to `PRELOAD_WIDGETS` in `scripts/build_web.py`. The name is the start of its file name in `vendor/stlite/` (for example `Checkbox`, `Slider`, `Selectbox`). `tests/test_offline.py` fails until you do, as long as the new widget is on the path the test walks. To see exactly what loads late, run `python scripts/diagnose_offline.py`.

## Checks

- [x] `tests/test_build_web.py`: the marker is in `web/index.html`; the import walk follows a widget's own files and not other widgets; a missing widget stops the build; the built page preloads every listed widget.
- [x] `tests/test_offline.py`, in Chromium and WebKit, against `dist/` served with `no-cache`: load the page, go offline, upload the synthetic locked PDF, type its password, see the results and the table, switch to equity funds, open "Funds included", download a chart. No errors, and no files requested after start-up. It failed in both browsers before this change (timed out waiting for the password box).
- [x] The deploy job runs both after `build_web.py`, with `FUNDPRINT_OFFLINE_TEST=required`, so a missing Playwright or build fails the job instead of skipping the test.
- [ ] On a phone: load the page, wait until the note is gone, turn on airplane mode, tap **See it with sample data**, then go back and upload a statement. Everything draws.
