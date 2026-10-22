# Fundprint

*A CASual look at your mutual fund statement.*

## Why this exists
Indian DIY mutual fund investors get one portfolio XIRR from their fund app. That number blends money invested five years ago with money invested last month, so it can't say what is really driving your returns, and it never says whether a plain index fund would have done better. Fundprint reads your CAMS/KFintech statement in your browser and looks at your returns in four ways:
- **By time held.** Returns for each holding-period bucket (under 1 year, 1-3, 3-5, 5+), against the same purchases replayed into a Nifty 50 index fund.
- **Fund by fund.** Which of your equity funds are ahead of or behind their Nifty 50 twin (the same purchases on the same dates), and how much of your equity money each one holds.
- **How regularly you invest.** What share of your purchases followed a regular monthly pattern, and your usual investing day, shown against the Nifty 50.
- **Easy to try.** Start with a made-up sample portfolio, or follow the step-by-step guide to request your own statement. Percentages only, no rupee amounts, and nothing leaves your browser.

## Your data stays with you
**Nothing is stored. Your file is read and dropped when you close the tab.**

Fundprint runs entirely in your browser. Your statement is never uploaded to any server. See [PRIVACY.md](PRIVACY.md) for the rules and how to check them yourself: open DevTools → Network, upload a statement, and watch that your file is never sent anywhere. Or load the page, turn on airplane mode, and upload your statement: it still works.

## Analytics
The live page counts visits with [Umami](https://umami.is), to see how many people use it. No cookies, only anonymised visit data, and nothing from your statement. To check, open the Network tab: the only requests to another site are the small page-view requests to `gateway.umami.is`. More in [PRIVACY.md](PRIVACY.md#analytics).

`web/umami.js` is an unedited copy of `https://cloud.umami.is/script.js`, copied on 14 Oct 2026. Umami is MIT licensed. To update it: download the new file, read it in full (what it sends and where), replace the copy, and update the hash in `tests/test_privacy.py`.

## What it shows
Per holding-period bucket (<1Y, 1-3Y, 3-5Y, 5Y+): share of your money, XIRR, absolute return, and the gap to the Nifty 50. Then two whole-portfolio charts: each equity fund against its Nifty 50 twin, and how regular your investing has been. Percentages only, no rupee amounts, so every screen is safe to screenshot.

## How it's calculated
1. Read the Detailed CAS (CAMS/KFintech) with [casparser](https://github.com/codereverie/casparser).
2. Keep only units still held. Sold units come off the oldest purchases first. Bounced SIPs are removed; reinvested dividends cost nothing.
3. Put each held purchase in a bucket by age, and work out XIRR per bucket.
4. Replay the same amounts on the same dates into UTI Nifty 50 Index Fund (Direct, Growth) and compare.

The reference notebook is in [notebooks/xirr_analysis.ipynb](notebooks/xirr_analysis.ipynb).

## Run it locally
```bash
pip install -r requirements-dev.txt
nbstripout --install              # once after cloning: clears notebook outputs when you commit
python scripts/refresh_data.py     # downloads the public benchmark and category data
streamlit run app/Home.py
pytest
```

## How it's deployed
The app runs in the browser with [stlite](https://github.com/whitphx/stlite) (Streamlit compiled to run client-side), as plain static files.
- `scripts/fetch_vendor.py` downloads stlite 1.11.0, a trimmed Pyodide 0.29.3 and a few pure-Python wheels into `web/vendor/`, so the page loads no outside script at all (the Umami visit counter is a fixed copy in `web/umami.js`).
- `scripts/build_web.py` assembles the site in `dist/`.
- Everything the build downloads is pinned to an exact version and checked against a SHA-256 hash written in `scripts/fetch_vendor.py`. On a mismatch the script deletes the file and stops. To move to a new version, change the version and hash there, and compare the hash with what the publisher lists.
- The CI jobs install from `requirements-ci.txt`, a full list of exact versions and hashes (`pip install --require-hashes`). `requirements.txt` and `requirements-dev.txt` stay the short files you edit; make the lock again with the command at the top of `requirements-ci.txt`, read what changed, and open a pull request.
- The deploy has two jobs: `build` (installs, tests, downloads, builds; no secrets) and `deploy` (holds the deploy key; runs no Python and no script from this repo). GitHub Actions are pinned to full commit IDs.
- `.github/workflows/deploy.yml` pushes `dist/` into a separate `lab` repo (published at `lab.shibaprasadb.com/fundprint`). GitHub Pages stays OFF in this repo.
- `.github/workflows/refresh-data.yml` refreshes the public benchmark and category data every day.

Try the browser build locally:
```bash
python scripts/fetch_vendor.py && python scripts/build_web.py
cd dist && python -m http.server 8766   # then open http://localhost:8766
```
Note: the browser build uses casparser 0.8.1 (reads PDFs with pdfminer). Newer versions need a PDF library that has no browser build yet.

## The CAMS form screenshot
The Home page checklist shows `app/assets/cams_form_annotated.png`. To make a new one, take a plain screenshot of the CAMS form with **Detailed** selected and run `python scripts/annotate_cams_form.py path/to/screenshot.png`. The script wipes the email, PAN and password boxes and draws the numbered markers. Keep the original screenshot out of the repo. If the image file is missing, the page simply shows the table without it.

## Limitations
- Units already sold aren't counted (active holdings only), so results look slightly kinder than reality.
- Cash paid out by IDCW payout plans isn't counted as a return.
- XIRR reflects timing as well as fund quality; the index replay is there to separate the two.
- CAMS/KFintech detailed CAS only (no NSDL/CDSL).

## Disclaimer
Fundprint is an analytics tool, not investment advice. Past returns don't predict future returns. Fundprint is not affiliated with CAMS, KFintech, AMFI, or any fund house. Benchmark: UTI Nifty 50 Index Fund – Direct Growth, using public NAV data.

Design notes and specs: see [docs/specs](docs/specs/).

## Licence
MIT
