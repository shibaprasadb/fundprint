# Contributing to Fundprint

Thanks for helping. Fundprint is a small, privacy-first project, so a few rules matter more than usual.

## Ways to help
- **Feedback or ideas:** use the in-app **Feedback** form (https://tally.so/r/2EqQGg) or open a GitHub issue.
- **Bug reports:** open a GitHub issue with what you did, what you expected, what happened instead, any error code shown, and your browser and device.
- **Code:** see below.

**Issues are public. Never paste or attach your statement, PAN, folio numbers, fund names or amounts.** Describe what happened instead.

**Security problems:** don't open a public issue. See [SECURITY.md](SECURITY.md).

## How to contribute code
1. **Open an issue first** for anything bigger than a small fix, so we can agree on the approach before you write it.
2. Fork the repo and create a branch from `main`.
3. Make your change, with tests.
4. Open a pull request that links the issue and says what changed and why.

## Run it locally
```bash
pip install -r requirements-dev.txt
nbstripout --install           # once after cloning: clears notebook outputs when you commit
streamlit run app/Home.py      # the app
pytest                         # the tests
```
Use the built-in **sample data** to try things out. Don't use your own statement while developing.

## Try the browser build
The live site is a browser build, which differs a little from `streamlit run` (for example, it has the header bar). To try it:
```bash
python scripts/refresh_data.py     # downloads the public benchmark and category data
python scripts/fetch_vendor.py && python scripts/build_web.py
cd dist && python -m http.server 8766   # then open http://localhost:8766
```
- `scripts/fetch_vendor.py` downloads stlite 1.11.0, a trimmed Pyodide 0.29.3 and a few pure-Python wheels into `web/vendor/`. Each file is checked against a SHA-256 hash written in the script; on a mismatch the script deletes the file and stops. To move to a new version, change the version and hash there, and compare the hash with what the publisher lists.
- The browser build uses casparser 0.8.1 (reads PDFs with pdfminer). Newer versions need a PDF library that has no browser build yet.
- The deploy has two jobs: `build` (installs, tests, downloads, builds; no secrets) and `deploy` (holds the deploy key; runs no Python and no script from this repo). GitHub Actions are pinned to full commit IDs. GitHub Pages stays OFF in this repo.

## What a pull request needs
- **All tests pass**, including the privacy checks (no caching of user data, no browser storage, no rupee amounts on screen).
- **New logic has tests** using **synthetic data only.**
- **It follows the rules in [CLAUDE.md](CLAUDE.md).** In short:
  - everything runs in the browser, and nothing from the statement is stored, cached or sent;
  - no rupee amounts anywhere; percentages only;
  - descriptive wording only, never investment advice;
  - no new external services or trackers;
  - every comparison names the benchmark (UTI Nifty 50 Index Fund, Direct Growth);
  - a new Umami event must be added to `ALLOWED_EVENTS` in `web/feedback.js` (checked by `fundprintBeforeSend`), and never carries event data.
- **Core logic stays in `fundprint/`,** with no Streamlit imports.
- **Plain-English code comments** that explain *why*, not just *what*.
- **New features get a short spec** in `docs/specs/` (next number, with a Status line).
- **If you change `requirements.txt` or `requirements-dev.txt`,** regenerate `requirements-ci.txt` with the command at the top of that file and check what changed.

## Never commit
- Real CAS statements or any file containing personal or portfolio data.
- Notebooks with outputs (clear them first; `nbstripout`, installed with the dev requirements, does this for you).
- Secrets or API keys.

Pull requests that break the privacy rules won't be merged, however useful the feature.

## Maintainer notes

### Updating the Umami script
`web/umami.js` is an unedited copy of `https://cloud.umami.is/script.js`, copied on 14 Oct 2026. Umami is MIT licensed. To update it: download the new file, read it in full (what it sends and where), replace the copy, and update the hash in `tests/test_privacy.py`.

### The CAMS form screenshot
The Home page checklist shows `app/assets/cams_form_annotated.png`. To make a new one, take a plain screenshot of the CAMS form with **Detailed** selected and run `python scripts/annotate_cams_form.py path/to/screenshot.png`. The script wipes the email, PAN and password boxes and draws the numbered markers. Keep the original screenshot out of the repo. If the image file is missing, the page simply shows the table without it.

## Licence
By contributing, you agree that your contributions are released under the project's [MIT License](LICENSE).
