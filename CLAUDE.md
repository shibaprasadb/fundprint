# CLAUDE.md: Fundprint

Standing rules for any change in this repo. Read this first, every session.

**Fundprint** (*a CASual look at your mutual fund statement*) lets Indian mutual fund investors upload their CAMS/KFintech Consolidated Account Statement (CAS) and see returns by holding period compared with a Nifty 50 index fund. Live at `lab.shibaprasadb.com/fundprint`. Open source.

## Where things are
- `README.md`: for users. What it is, privacy, how to verify.
- `PRIVACY.md`: the privacy promise in full and how to check it.
- `ARCHITECTURE.md`: how the app is built and deployed.
- `docs/specs/`: numbered design specs, oldest first. Check each file's **Status** line; superseded parts are history, not instructions.
- `notebooks/`: the original analysis notebook (reference for the maths only).

## Non-negotiable rules

### Privacy (the product depends on these)
The promise shown in the app, word for word: **"Nothing is stored. Your file is read and dropped when you close the tab."**
1. **Everything runs in the browser** (stlite / Pyodide). No backend, ever.
2. **Never write the uploaded file or anything derived from it to disk**, including the in-browser filesystem. Work in memory only.
3. **Never cache user data.** No `st.cache_data` / `st.cache_resource` on anything that touches the PDF, the password or parsed results. Caching is only for public static data.
4. **No browser storage of user data:** no localStorage, sessionStorage, IndexedDB or cookies.
5. **The only outside service the page may talk to is Umami,** for allowlisted, data-free events. No other trackers, fonts or external scripts.
6. **Keep the Content-Security-Policy tight:** `'self'` plus the Umami host only.
7. **No runtime calls to mfapi.in, AMFI or anything else from the browser.** Public data is refreshed by the scheduled GitHub Action into `data/`.
8. **Errors never show statement data.** Plain messages only; no tracebacks; never log or print DataFrames, folio numbers, PAN, names or amounts.
9. **The PDF password is used once and discarded.** Never keep it in session state.
10. **No real statements in the repo, ever.** Synthetic test data only; `*.pdf` stays git-ignored; notebooks are committed with outputs cleared.

### What the app shows
- **No rupee amounts anywhere:** text, tables, charts, axis labels, tooltips or downloads. Percentages, XIRR, gaps and public NAV values only. Invested and current value are internal working numbers.
- **Descriptive wording only, never advice.** Say "ahead of / behind the index over this period". Never "you should", "switch", "exit", "bad fund", "underperforming".
- The benchmark is a **Nifty 50 index fund** (UTI Nifty 50 Index Fund, Direct Growth). Say so wherever a comparison is shown.

### Analytics (Umami)
- Only `umami.track(name)` with a name from the allowlist in `index.html`. **No event data, ever.**
- Every new event must be added to both the allowlist and `fundprintBeforeSend`.
- Nothing derived from the statement may appear in an event, URL or link.

### Hosting
- The app is published **only** through the `lab` repo (`lab.shibaprasadb.com/fundprint`).
- **GitHub Pages stays OFF in this repo.** No `gh-pages` branch, no Pages workflow, no `actions/deploy-pages` here.

### Attribution
- Credit is **shibaprasadb.com** only. No personal name in the app, README, page metadata or code comments.

## How to work
- Keep core logic in `fundprint/` free of Streamlit imports, so it can be tested on its own.
- Write code comments and docs in plain, simple English. No buzzwords.
- README content leads with the use case and the problem it solves; setup comes after.
- Run the test suite before every commit, including the privacy checks (no caching of user data, no browser storage, no rupee amounts).
- New features get a new numbered spec in `docs/specs/`. When a spec is replaced, update the old one's **Status** line instead of deleting it.
- If a request would break any rule above, stop and say so instead of working around it.
