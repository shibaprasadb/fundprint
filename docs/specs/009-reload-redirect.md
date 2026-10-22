# Fundprint: Reloading a page lands on Home

> **Status:** Implemented

After opening the results page, the address bar shows `lab.shibaprasadb.com/fundprint/Time_in_Market`. Streamlit sets it while you move between pages; nothing is downloaded. Reloading that address, or opening it later, asked GitHub Pages for a file that did not exist, so it showed its own "404 File not found" page with no way back to Fundprint.

The diagnosis and the options weighed are in [docs/reload-404-diagnosis.md](../reload-404-diagnosis.md).

## What the app does

`scripts/build_web.py` writes one small file per page in `app/pages/`, named the way Streamlit names the page in the address bar (the file name without its number and `.py`): `dist/Time_in_Market.html`. GitHub Pages serves it for `/fundprint/Time_in_Market`. The file:

- sends the browser to `./`, which is the Fundprint home page, straight away (`<meta http-equiv="refresh">`), with a plain "Go to Fundprint" link as a fallback;
- has no script and a security policy of `default-src 'none'`, so it loads and runs nothing, Umami included;
- sits inside `/fundprint/`, so nothing is added at the root of the shared `lab.shibaprasadb.com` address.

Home is the right place to land: after a reload nothing from the statement is left, by design. A new page in `app/pages/` gets its file with no extra work.

The home address `/fundprint` (no slash) already works: GitHub Pages sends it on to `/fundprint/`.

## Checks

- [x] `tests/test_build_web.py`: the page name matches Streamlit's; the file has no script, no outside address and only points to `./`; after a build, every page has its file.
- [x] In Chromium and WebKit, opening the file on a local copy lands on `/fundprint/` and the home page draws, with no console errors.
- [ ] After deploying: `curl -sI https://lab.shibaprasadb.com/fundprint/Time_in_Market` returns 200. (Checked before this change: GitHub Pages on `lab` serves `/fundprint/index` from `index.html`, so a `.html` file answers for its name.)
- [ ] In a browser: see the sample, reload on the results page, and the home page loads.
