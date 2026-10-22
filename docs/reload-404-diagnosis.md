# Reloading the results page gives a 404: diagnosis

**Status:** Diagnosis. Option A was approved and is built as [spec 009](specs/009-reload-redirect.md), as a `.html` file (GitHub Pages on `lab` serves `/fundprint/index` from `index.html`, so the folder fallback was not needed).
**Date:** 22 Oct 2026

## The problem in one line

After you open the results page, the address bar shows `lab.shibaprasadb.com/fundprint/Time_in_Market`.
If you reload, or open that address later, GitHub Pages shows its own "404 File not found" page, with no
way back to Fundprint.

## What was checked

All checks used the live site and the built-in sample data only. No real statement was used.

### In the browser

| Step | What the app did | Address bar after |
|---|---|---|
| Open `/fundprint/` | Home page loads | `/fundprint/` |
| Tap "See it with sample data" | `history.pushState` to `/fundprint/Time_in_Market` | `/fundprint/Time_in_Market` |
| Tap "Use your own statement →" | `history.pushState` to `/fundprint` | `/fundprint` (no trailing slash) |
| Browser Back | Results page shown again, inside the app, no page load | `/fundprint/Time_in_Market` |
| Reload on `/fundprint/Time_in_Market` | GitHub Pages "Page not found" | same |

So moving between pages and Back/Forward all work while the tab is open. Only a fresh load of the
results address fails.

### On the server (`curl -I`)

| Address | Answer |
|---|---|
| `/fundprint/` | 200, the app |
| `/fundprint` | 301 to `/fundprint/`, then the app. **The Home address works.** |
| `/fundprint/Time_in_Market` | 404, GitHub's default page |
| `/404.html` and `/fundprint/404.html` | 404. Neither exists, so GitHub shows its built-in page. |

The `lab` repo serves from `main`, folder `/`, with the custom domain `lab.shibaprasadb.com`. Its root holds
only `.nojekyll`, `CNAME`, `index.html` and `fundprint/`.

### Why the address changes

The address is set by Streamlit's own page handling inside stlite (stlite 1.11.0, file
`web/vendor/stlite/index-*.js`, function `maybeUpdatePageUrl`). On each page change it builds
`<base path>/<page name>` and calls `history.pushState`:

- The base path is the address the app was opened at (`/fundprint/`), with the last slash removed, so `/fundprint`.
- The page name comes from the file name `app/pages/1_Time_in_Market.py`, with the number and `.py` removed.
- For Home the page name is empty, which gives `/fundprint` (the code drops the trailing slash on purpose).

stlite has no setting to turn this off. It only skips it for `file:` addresses. When the page loads,
stlite also reads the address to pick which page to show, which is how Back works.

### What a reload can show at best

By design nothing is kept between loads, so after a reload the statement (or the sample) is gone. Even if the
results address loaded the app, the results page would only say "Upload a statement (or see the sample) on
the Home page first." The best a reload can do is land on Home. Every option below is judged on that.

## Privacy check of the address

- The address only ever holds a fixed page name (`Time_in_Market`) or nothing. The app uses no
  `st.query_params` and no widget is tied to the address, so nothing from the statement can reach it.
- Umami's script also wraps `pushState`, so it already counts a page view for `/fundprint/Time_in_Market`
  when someone opens the results page. That is the page name only and passes `fundprintBeforeSend` as a
  plain page view. Nothing changes here unless a fix stops the address changing (see option B).

## Options

### A. A small redirect file at `/fundprint/Time_in_Market` (recommended)

Add a tiny static page, published as `fundprint/Time_in_Market.html`, that sends the visitor to `./`
(which is `/fundprint/`) with a `<meta http-equiv="refresh">` tag and a plain "Go to Fundprint" link as a
fallback. No script, and its own strict policy, for example
`<meta http-equiv="Content-Security-Policy" content="default-src 'none'">`.

GitHub Pages serves `name.html` when someone asks for `/name`. This was seen on the owner's other Pages
site: `www.shibaprasadb.com/blog` returns 200 from `blog.html`. If it ever does not work with `.nojekyll`,
the fallback is a folder, `fundprint/Time_in_Market/index.html`, pointing to `../`. GitHub answers
`/fundprint/Time_in_Market` with a 301 to the folder, then serves it. That is one extra hop but certain.

- **What the user sees:** reload on the results page shows a blank page for a moment, then the normal
  Fundprint Home page loading. No GitHub 404.
- **Files changed:**
  - `scripts/build_web.py`: write one redirect file per page in `app/pages/`, named from the file
    (strip the `N_` prefix and `.py`), so a future page gets one without anyone remembering to add it.
  - A test (for example in `tests/test_privacy.py` or a new build test) that each page has a redirect
    file, and that the file has no `<script>` and no outside address.
  - A release check, next to the existing one in `docs/specs/001-core.md` section 3:
    `curl -sI https://lab.shibaprasadb.com/fundprint/Time_in_Market` returns 200.
  - No change to `deploy.yml`: it already copies all of `dist/` into `lab/fundprint/`.
- **Shared web address:** nothing new at the `lab` root. The file sits inside `/fundprint/`, which only
  the Fundprint deploy writes, and it has no script, so it fits the terms in ARCHITECTURE.md.
- **Privacy:** the file holds only a fixed link. It loads nothing and runs nothing, so Umami does not run
  on it either. No statement data is involved.
- **Limits:** the user lands on Home, not on results, which is the best possible after a reload anyway.
  The Home address `/fundprint` already works through GitHub's own 301, so it needs nothing.

### B. Stop the address from changing

Wrap `history.pushState` in `web/boot.js` before stlite starts, so any path stlite asks for under
`/fundprint/` is replaced with `/fundprint/`. The address would then always be `/fundprint/` and a reload
always lands on Home.

- **What the user sees:** the address never changes. Back from results still returns to Home: stlite reads
  `/fundprint/` as Home. A second Back may redraw Home again instead of leaving the site.
- **Files changed:** `web/boot.js` only, plus a test.
- **Shared web address:** no change to the `lab` root.
- **Privacy:** none, but it changes what Umami sees. Umami also wraps `pushState`, and which wrapper runs
  first depends on load order, so results page views may stop being counted, or be counted under `/fundprint/`.
- **Why not first choice:** it relies on how stlite handles page changes internally, which may change in a
  future stlite update without any warning. It also changes analytics in a way that is hard to predict.

### C. A `404.html` at the `lab` root

GitHub Pages uses one custom `404.html` per site, at the root of the publishing source. GitHub's docs only
talk about putting it in the publishing source. For `lab` that means `lab.shibaprasadb.com/404.html`. A file at
`fundprint/404.html` would not be used for missing addresses under `/fundprint/`. This was not tested on
the live site, because that would mean adding the file.

- **What the user sees:** a reload of the results page would show this page, which could link or send them
  to `/fundprint/`.
- **Files changed:** a new file in the **`lab` repo root**, not under `fundprint/`. The deploy only replaces
  `lab/fundprint/` (and touches `.nojekyll`), so this needs either a hand commit to `lab` or a deploy change
  that writes outside `fundprint/`.
- **Shared web address:** yes, this touches it. The page would answer for every missing address on
  `lab.shibaprasadb.com`, including other lab projects. Sending only Fundprint addresses to Fundprint needs a
  script that reads the address, which adds a script on the shared origin for all of `lab`.
- **Other:** the reply still has HTTP status 404. Fine for people, but the browser and any link checker
  see an error.
- **Why not:** it is wider than the problem, lives outside this repo's deploy, and adds weight to the
  shared-origin risk we have chosen to keep small.

### D. Make Fundprint a single page

Draw the results inside `Home.py` (switched by a value in session state) instead of a second Streamlit page,
so the address never changes.

- **What the user sees:** the address stays `/fundprint/`. Reload lands on Home. Browser Back from results
  would leave Fundprint, because no history entry is added.
- **Files changed:** `app/Home.py`, `app/pages/1_Time_in_Market.py` (moved), `app/ui.py`, `scripts/build_web.py`,
  and the tests that open the results page (`tests/test_app.py`, `tests/test_history.py`, others).
- **Shared web address / privacy:** no change. Umami would no longer count results views as a separate page.
- **Why not:** a large change to fix a reload, and it makes Back worse.

### E. Leave it

It only happens on a reload or a saved results address, and data is gone after a reload anyway. But the
GitHub 404 page has no link back, looks broken and does not mention Fundprint. A share of the results address
from the address bar would also lead people to a dead page.

## Recommendation

**Option A**, generated by `scripts/build_web.py` for every page in `app/pages/`, with a test and a release
check. It is the smallest change, stays inside `/fundprint/`, runs no script, does not depend on stlite's
internals, and takes a reload to the best place it can go: the Home page.

After deploying, check:
- `curl -sI https://lab.shibaprasadb.com/fundprint/Time_in_Market` gives 200 (or 301 then 200 if the folder
  fallback is used).
- In a browser: sample data, then reload on the results page, lands on Home with no console errors.
- Moving between pages and Back still behave as in the table above.
