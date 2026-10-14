# Fundprint: Product & Build Spec

> **Fundprint**: *a CASual look at your mutual fund statement.*
> Lives at `lab.shibaprasadb.com/fundprint`. Open source. Runs in your browser.

This spec is the brief for building Fundprint with Claude Code. It comes with one reference file: `xirr_analysis.ipynb`, a working notebook that already contains the core analysis logic (parsing, FIFO, bucketing, XIRR, Nifty 50 replay, charts). Treat the notebook as the **source of truth for the maths**, and this spec as the source of truth for **everything else**.

---

## 0. The privacy promise (read this first)

This is the product. Every other feature is secondary to it.

The app must show this line, word for word, above the upload box:

> **Nothing is stored. Your file is read and dropped when you close the tab.**

Directly under it:

> Fundprint runs entirely in your browser. Your statement is never uploaded to any server.
> Don't take our word for it: the [code is open source](<repo link>), and you can open your browser's Network tab to check that your file is never sent anywhere.

### What makes the promise true (hard rules, no exceptions)

| # | Rule | Why |
|---|---|---|
| P1 | **All parsing and analysis runs in the browser** (stlite / Pyodide). There is no backend. | The file physically cannot reach a server we run. |
| P2 | **Never write the uploaded file or anything derived from it to disk**, including the Pyodide in-memory filesystem. Work only with `io.BytesIO` and in-memory objects. | Nothing to leave behind. |
| P3 | **Never cache user data.** No `st.cache_data` / `st.cache_resource` on any function that receives the PDF, the password, or anything parsed from them. Caching is allowed **only** for static public data (benchmark NAVs, scheme categories). | Streamlit caches can outlive a single run. |
| P4 | **No browser storage of user data**: no `localStorage`, `sessionStorage`, IndexedDB or cookies holding anything from the statement. | Survives closing the tab otherwise. |
| P5 | **No trackers, third-party fonts or external scripts.** The only outside request is the anonymous Umami page-view count, sent by a fixed copy of Umami's script kept in the repo (`web/umami.js`) and served from our own domain (page views only, nothing from the statement; see PRIVACY.md). Self-host the stlite/Pyodide assets so the page loads only from its own domain. | Keeps the Network tab clean and checkable. |
| P6 | **Add a Content-Security-Policy `<meta>` tag** with `connect-src 'self'` plus the Umami host, and nothing else. | The browser itself blocks any attempt to send data elsewhere, even by a buggy dependency. |
| P7 | **No network calls at runtime except fetching the app's own static files** (`/data/*.json`, Python wheels) and the anonymous Umami counts. Never call mfapi.in, AMFI or anything else from the browser. | All public data is pre-fetched by a scheduled job (see §5). |
| P8 | **Errors never show statement data.** Catch exceptions around parsing and analysis; show a plain message ("Couldn't read this statement. Is it a CAMS/KFintech detailed CAS?"). Set `client.showErrorDetails = false`. Never `print()` or log DataFrames, folio numbers, PAN, names or amounts. | Tracebacks and logs leak values. |
| P9 | **The PDF password is used once to open the file and then discarded.** Use `st.text_input(type="password")`; don't keep it in session state. | |
| P10 | **No real statements in the repo, ever.** `.gitignore` all `*.pdf`; use only synthetic test data; strip notebook outputs (`nbstripout` pre-commit hook). The reference notebook must be committed **with outputs cleared**. | The repo is public. |

### How a user (or reviewer) can verify it

Document this in the README and the in-app "How it works" section:
1. Open DevTools → Network, upload a statement, and watch: after the app has loaded, the only requests that leave the site are small ones to Umami.
2. Read the CSP tag in the page source.
3. Read the code: there is no server code to hide anything in.

**Acceptance test for the promise:** with DevTools open, load the app, upload a synthetic CAS, and run every analysis. After the app loads, **every** network request goes either to the app's own domain or to Umami (`gateway.umami.is` for the counts; the script itself is served from our own domain), and every Umami request is a plain page view with Umami's standard fields. Make this a manual checklist item for every release, and an automated Playwright test if feasible (§9).

---

## 1. Why this exists

**Who it's for:** Indian DIY mutual fund investors who want to understand their own portfolio better than their fund app shows them.

**The problem:** every app shows one portfolio XIRR. That number blends money invested five years ago with money invested last month, so it can't tell you whether your older money is doing well or your newer money is dragging. It also never tells you whether the same money would have done better in a plain index fund.

**What Fundprint does:** you upload your Consolidated Account Statement (CAS), and Fundprint breaks your returns down by how long each purchase has been held. It compares each bucket against what the *same purchases on the same dates* would have earned in a Nifty 50 index fund. All of it happens in your browser.

**Why it's built this way:** a CAS contains PAN, address, phone, email and every transaction, and nobody should have to trust a stranger's server with that. So Fundprint has no server.

This product is also a public portfolio piece. Code quality, README clarity and the "how it's calculated" explanation matter as much as the features.

---

## 2. Scope

### v1 (this build)
- Landing page with the privacy promise, upload and password.
- One analysis module: **Time in Market** (XIRR by holding period vs Nifty 50).
- "Try with sample data" button (synthetic portfolio, no upload needed).
- **Percentages only: no rupee amounts anywhere** (see §7, "No rupee amounts").
- Download charts as PNG (generated in the browser).

### Not in v1
- Other analyses (overlap, cost drag, SIP timing). Design the structure so they can be added as new pages (§4).
- Accounts, saving, history, comparisons across uploads.
- Investment recommendations of any kind (see §8).
- Any display of rupee amounts (invested, current value, gains in ₹). A later version may add this as an opt-in; v1 does not.
- NSDL/CDSL demat CAS (CAMS/KFintech detailed CAS only for v1).

---

## 3. Architecture

### Decision: stlite on static hosting
- **stlite** runs Streamlit inside the browser using Pyodide (Python compiled to WebAssembly).
- The app is a folder of static files, hosted on **GitHub Pages**.
- Each visitor's browser does its own computing: no server, no hosting cost, no "app is asleep" screen.
- Trade-off: first load is several seconds while Python downloads. Show a friendly loading message: *"Loading Python in your browser… this happens once per visit."*
- Trade-off: Python runs on one thread in the tab, so the UI can't redraw during heavy steps. Spinners may not animate; put a `time.sleep(0.1)` before long blocking calls so the spinner appears (known stlite workaround).

Pin the stlite version (last checked: `@stlite/browser@0.85.1`; check for the latest at build time) and record it in the README.

### Step 0: the go/no-go spike (do this before anything else)

Build a bare stlite page that installs casparser and parses a **synthetic** CAS in the browser. Known risks to resolve:

| Dependency | Status in browser | Plan |
|---|---|---|
| `pypdfium2` (PDF reading) | Has a `pyemscripten` wasm wheel on PyPI | Check it matches the Pyodide version stlite ships. If not, fall back to `casparser.read_cas_pdf(..., force_pdfminer=True)` with `pdfminer.six` (pure Python; `cryptography` is in Pyodide). |
| `casparser-isin` → `rapidfuzz` | **No wasm build** | Install casparser with `deps=False`, install its other deps one by one, and provide a tiny stub `rapidfuzz` module (`fuzz`, `process`, `utils` with no-op functions) so imports succeed. The fuzzy path only runs when a statement is missing ISINs, and we handle that ourselves (§6.2). |
| `pyxirr` (Rust) | No wasm build | Replace with our own `xirr()` (§6.6). Keep `pyxirr` only as a test oracle in CI. |
| `click`, `rich`, `colorama`, `python-dateutil`, `pydantic` | Pure Python, or in Pyodide | Install via micropip. |
| `pandas`, `numpy`, `scipy`, `matplotlib` | In Pyodide | Load from the Pyodide distribution. |

**Spike passes if** a synthetic CAS PDF (password-protected and not) parses to the same `transactions` table in the browser as on desktop Python.

**If the spike fails:** fall back to a server-hosted Streamlit app (Hugging Face Spaces or Render; avoid Community Cloud's 12-hour sleep). Keep rules P2, P3, P8, P9 and P10 and the exact promise line, and replace the "never uploaded" sentence with: *"Your file is processed in memory on the server and discarded when your session ends. Nothing is written to disk or logged."* Raise this with Shiba before switching; don't switch silently.

### Hosting and URL
- Target: `https://lab.shibaprasadb.com/fundprint`.
- `shibaprasadb.com` is already on **GitHub Pages**. Leave that repo untouched.
- Set up the lab as follows:
  1. Create a new public repo **`lab`** with GitHub Pages enabled and a `CNAME` file containing `lab.shibaprasadb.com`.
  2. At the DNS provider, add a `CNAME` record: `lab` → `<github-username>.github.io`. Then enable "Enforce HTTPS" in the `lab` repo's Pages settings once the certificate is issued.
  3. The `fundprint` repo's `deploy.yml` builds the static app and pushes it into the `lab` repo under `/fundprint/` (using a deploy key or fine-grained token scoped to the `lab` repo only).
  4. The `lab` repo gets a simple `index.html` listing lab projects (Fundprint first). Future projects deploy into their own folder the same way.
> ⚠️ **GitHub Pages must stay switched OFF in the `fundprint` repo.**
>
> `shibaprasadb.com` (the main user site) has a custom domain. On GitHub, that means any *other* repo with Pages switched on is automatically published at `shibaprasadb.com/<repo-name>`. If Pages were on in `fundprint`, the app would also appear at `shibaprasadb.com/fundprint`: a duplicate of `lab.shibaprasadb.com/fundprint`, and possibly an outdated one.
>
> - The **`lab` repo is the only place the app is published.**
> - Do not add a `gh-pages` branch, a `docs/` Pages folder or a Pages workflow to `fundprint`.
> - `deploy.yml` in `fundprint` must only push built files into the `lab` repo; it must never call `actions/deploy-pages` on `fundprint` itself.
> - Release checklist item: confirm `https://shibaprasadb.com/fundprint` returns 404.

### Repo
- Name: `fundprint`. The README and repo description must carry the tagline ("a CASual look at your mutual fund statement") so it reads as clearly distinct from the unrelated product at fundprint.co.
- Licence: MIT. Dependencies: casparser (MIT), matplotlib, pyxirr (Unlicense, test-only).

---

## 4. Repo structure

```
fundprint/
├── README.md                  # leads with the use case (see §10)
├── PRIVACY.md                 # the promise, the rules, how to verify
├── LICENSE                    # MIT
├── SPEC.md                    # this file
├── fundprint/                 # core logic: pure Python, no Streamlit imports
│   ├── parse.py               # CAS → transactions DataFrame
│   ├── lots.py                # reversals, FIFO, held lots, buckets, cash flows
│   ├── xirr.py                # our own XIRR (no pyxirr)
│   ├── benchmark.py           # replay purchases into the index fund
│   ├── classify.py            # ISIN → asset class
│   └── charts.py              # matplotlib figures (facet + allocation)
├── app/
│   ├── Home.py                # landing: promise, upload, password, sample data
│   ├── pages/
│   │   └── 1_Time_in_Market.py  # the v1 analysis
│   └── ui.py                  # shared bits: promise banner, percentage formatting, disclaimer
├── web/
│   ├── index.html             # stlite mount, CSP meta tag, loading message
│   └── vendor/                # self-hosted stlite + Pyodide assets (P5)
├── data/                      # public data, refreshed daily by CI
│   ├── benchmark_nav.json
│   ├── scheme_categories.json
│   └── manifest.json          # source URLs + last-updated dates
├── scripts/
│   ├── refresh_data.py        # builds /data from mfapi.in + AMFI
│   └── make_sample.py         # builds synthetic sample portfolio + test CAS fixtures
├── tests/
│   ├── fixtures/              # synthetic only (P10)
│   └── test_*.py
├── notebooks/
│   └── xirr_analysis.ipynb    # reference, outputs stripped
├── .github/workflows/
│   ├── refresh-data.yml
│   ├── tests.yml
│   └── deploy.yml
└── .gitignore                 # *.pdf, .ipynb_checkpoints, etc.
```

Keep `fundprint/` free of Streamlit so it can be tested normally and reused by future pages.

---

## 5. Public data pipeline (`refresh-data.yml`)

Runs daily on GitHub Actions (the GitHub server does the fetching, never the user's browser), plus manual trigger. Commits updated JSON to `data/`.

1. **Benchmark NAV history**: UTI Nifty 50 Index Fund – Direct Plan – Growth, AMFI code **120716**, from `https://api.mfapi.in/mf/120716`. Store as `[{date: "YYYY-MM-DD", nav: float}]`, sorted ascending.
2. **Scheme categories**: from AMFI's daily NAV file (`https://portal.amfiindia.com/spages/NAVAll.txt`; verify the URL and format). Rows are `;`-separated (scheme code, ISIN growth/payout, ISIN reinvestment, name, NAV, date), grouped under category header lines such as `Open Ended Schemes(Equity Scheme - Flexi Cap Fund)`. Output: `{isin: {amfi_code, scheme_name, amfi_category, asset_class}}`, one entry for **each** ISIN on a row.
3. **manifest.json**: sources, fetch timestamps, row counts. Show "Benchmark data as of <date>" in the app footer.
4. **Fail safe:** if a fetch fails or returns suspiciously little data (e.g. fewer rows than yesterday by >10%), don't overwrite; keep yesterday's file and fail the job loudly.

`BENCH` must stay configurable (one constant) for adding more benchmarks later.

---

## 6. Core logic

Port from the notebook. Behaviour must match it; the notebook cells are referenced below.

### 6.1 Parse (`parse.py`)
- `casparser.read_cas_pdf(BytesIO(pdf_bytes), password)`; if the result has `.model_dump()`, call it (newer casparser returns a pydantic object).
- Reject non-DETAILED statements with a clear message ("This looks like a Summary CAS. Please request the Detailed one.").
- Flatten to one row per transaction: `key = (folio, scheme)`, `isin`, `date`, `kind` (transaction type as string), `units`, `amount`.
- Also capture per scheme: latest `nav` and its `valuation.date`.
- Skip rows with `units is None` (stamp duty, STT, TDS).
- **Reinvested dividends (`DIVIDEND_REINVEST`) cost 0**: the money came from the fund's own NAV, not the investor's pocket.

### 6.2 Classify (`classify.py`)
- Exact match on ISIN against `scheme_categories.json`. Direct and Regular plans have different ISINs, so no fuzzy matching is needed.
- Map AMFI categories to `asset_class` ∈ {Equity, Debt, Hybrid, Commodity, Other}:
  - `Equity Scheme - *` → Equity; `Debt Scheme - *` → Debt; `Hybrid Scheme - *` → Hybrid.
  - `Other Scheme - Index Funds` / `ETFs`: decide by scheme name (Nifty/Sensex/equity indices → Equity; SDL/G-Sec/Gilt/Bond/Target Maturity/CRISIL debt indices → Debt; Gold/Silver → Commodity).
  - `Other Scheme - FoF *`: Gold/Silver in name → Commodity; otherwise Other.
- If there's no ISIN or no match, mark it **Unclassified**. The UI lets the user set the asset class per fund (a dropdown in an expander), kept in session only.
- Keep the mapping rules in one readable table in code, with tests.

### 6.3 Held lots (`lots.py`), from the notebook's "Work out which purchases are still held"
Per fund (`key`), sorted by date:
1. `buys` = rows with `units > 0` (purchases, SIPs, switch-ins, reinvested dividends).
2. **Reversals** (`kind == "REVERSAL"`, e.g. a bounced SIP): remove the most recent earlier buy with the same unit count (|Δ| < 0.001), and drop the reversal row. Don't treat it as a sale.
3. `sold` = total of remaining negative units (redemptions, switch-outs).
4. **FIFO**: `held = clip(cumsum(buys.units) − sold, 0, buys.units)`; drop lots with `held ≤ 0.001`.
5. Each held lot gives two cash flows:
   - `(purchase_date, −amount × held / units)`, the cost of the units still held;
   - `(nav_date, held × latest_nav)`, what they're worth now.
6. **Switches and reinvestment count as fresh purchases** from their own date (Shiba's rule: "start from 0").

### 6.4 Buckets
- Age = `(today − purchase_date).days / 365.25`.
- Default buckets: `<1Y`, `1-3Y`, `3-5Y`, `5Y+` (bounds: 1, 3, 5 years), displayed oldest first.
- Keep bucket edges as one config list so a later version can let users change them.

### 6.5 Summary per bucket
Compute `invested`, `value`, `xirr_%`, `abs_%` (= value / invested − 1), and `share_%` (= bucket invested / total invested). Only non-empty buckets, in fixed order.

`invested` and `value` are **internal working values only**. They are needed for the maths, but they must never be displayed, put in a table, written into a chart, or included in any download (§7).

### 6.6 XIRR (`xirr.py`): our own, no pyxirr
- Day count: actual days / 365 (ACT/365F, the same as Excel and pyxirr).
- Exactly 2 cash flows → closed form: `r = (CF1 / −CF0)^(1/t) − 1`.
- Otherwise: Newton–Raphson from `guess = clamp(Σinflows / Σ|outflows| − 1, −0.9, 0.1)`, tolerance 1e-9, max 50 steps; if that fails, `scipy.optimize.brentq` on `[−0.999999, 100]`; if that fails, return NaN and show "n/a".
- **Tests must match pyxirr to 1e-6** on a range of random and edge-case cash flows (pyxirr is installed in CI only).

### 6.7 Benchmark replay (`benchmark.py`), from the notebook's `vs_nifty()`
- For each purchase cash flow (amount < 0), find the benchmark NAV on that date, or the last trading day before it (`merge_asof`, backward).
- `idx_units = −amount / nav`; final value per bucket = Σ idx_units × latest benchmark NAV, dated at the latest benchmark date.
- Run the same summary as §6.5 → `nifty_xirr_%`, `nifty_abs_%`; `xirr_gap_%` = mine − nifty. (`nifty_value` is internal only, like `invested`/`value`.)
- If a purchase is older than the benchmark history, exclude that lot from the comparison and show a note. Don't crash, and don't guess a value.

### 6.8 Scope filter
- "All funds" or "Equity only" (asset_class == Equity). The equity view should list which funds are included, in an expander.

### Known limitation to document (not fix in v1)
- Units already sold aren't counted (active holdings only), which makes results look slightly kinder than reality.
- IDCW **payout** cash isn't counted as a return, so those funds' XIRR is understated. Show a note if any IDCW payout plans are detected.
- XIRR measures timing as well as fund quality; the benchmark replay is there to separate the two.

---

## 7. UI

### Global
- Promise banner (§0) at the top of the landing page; a short version ("🔒 Runs in your browser. Nothing is stored.") in the sidebar on every page.
- **No rupee amounts.** v1 shows percentages only: share of money per bucket, XIRR, absolute return and the gap to the Nifty 50. No ₹ figures in text, tables, chart labels, axis ticks, tooltips or downloads, and no amounts that can be worked backwards (e.g. don't show both a ₹ total and a percentage). This also makes every screen safe to screenshot and share.
- Footer: disclaimer (§8), "Benchmark data as of <date>", repo link, and "Built by **shibaprasadb.com**" (links to https://shibaprasadb.com; no personal name anywhere in the app).

### Home
1. Title + tagline.
2. Promise block (§0), word for word.
3. "How to get your CAS" (collapsible): request a **Detailed** statement from CAMS or KFintech, with the start date set before your first investment and "with zero balance folios" or "without" either fine. Include the CAMS link.
4. Upload (`st.file_uploader`, PDF only, one file) + password field.
5. "Or try with sample data" button.
6. After parsing: a small summary (number of funds, statement period, unclassified count; no amounts) and a button to go to Time in Market.

Hold parsed data in `st.session_state` only (in memory, gone when the tab closes). Never in caches (P3).

### Time in Market page
1. Controls: scope (All / Equity only), plus the Unclassified-fund fixer if needed.
2. **Allocation chart**: share of money invested per bucket (horizontal bars, biggest bucket highlighted).
3. **Facet chart**: columns = buckets, rows = XIRR (top) and absolute return (bottom); bars "My funds" vs "Nifty 50"; title generated from the data, e.g. "Equity funds beat the Nifty 50 in 2 of 3 buckets" (for <1Y the comparison uses absolute return, otherwise XIRR).
4. **Table**: per bucket: share of money (%), my XIRR, Nifty XIRR, gap, my absolute return, Nifty absolute return. Percentages only.
5. **"How this is calculated"** expander: plain-English version of §6, including the Public Market Equivalent idea, why <1Y XIRR is faded, and the limitations.
6. Download buttons for each chart (PNG).

### Copy tone
Plain, friendly, descriptive. Never "you should", "switch to", "bad fund", "underperforming fund". Use "ahead of / behind the index over this period".

---

## 8. Compliance and disclaimer

Fundprint shows analytics, not advice. Showing a user's own returns next to an index is factual; recommending actions could count as investment advice, which needs SEBI registration in India.

Footer and README text:
> Fundprint is an analytics tool, not investment advice. Past returns don't predict future returns. Fundprint is not affiliated with CAMS, KFintech, AMFI, or any fund house. Benchmark: UTI Nifty 50 Index Fund – Direct Growth, using public NAV data.

---

## 9. Testing

All fixtures synthetic (P10). `scripts/make_sample.py` builds them.

**Unit tests with known answers** (from checks already done on the notebook):
- One purchase that doubles in exactly 730 days → XIRR = √2 − 1 = **41.42%**.
- Two deposits (₹1,000 at t=0, ₹1,000 at t=0.5y) worth ₹2,600 at t=2y → **16.13%**.
- Bounced SIP (purchase + matching reversal) → no effect on held lots.
- Reinvested dividend → units added at zero cost.
- Partial redemption → FIFO takes units from the oldest lots first.
- Benchmark that grows exactly 10%/yr → Nifty XIRR = **10.0%** in every bucket.
- A purchase older than the benchmark history → excluded with a note, no crash.
- Our `xirr()` vs pyxirr on 500 random cash-flow sets → max difference < 1e-6.
- Classification table: one case per mapping rule, plus Unclassified.

**End-to-end:** a synthetic CAS PDF (with and without password) → parse → Time in Market tables match expected numbers.

**Privacy tests:**
- Static check: no `st.cache_*` decorator on any function in `parse.py`, `lots.py`, `benchmark.py`, or app code that touches user data (a simple grep-based test).
- Static check: no `localStorage`/`sessionStorage`/`indexedDB` in `web/`.
- No-rupee check: render the Time in Market page with sample data (Streamlit `AppTest`) and assert that no text element, table cell or chart label contains `₹`, `Rs`, `INR`, `lakh`, `crore`, or any of the internal `invested`/`value` numbers.
- Playwright (if feasible): load the deployed page, upload the synthetic CAS, run Time in Market, and assert that every request goes to the app's own domain or to Umami, and that every Umami request is a plain page view.

---

## 10. README (written for the use case first)

Follow this order, in plain English. Avoid buzzwords like "ledger", "moat", "load-bearing", "source of truth".

1. **Why this exists**: 3 sentences: who it's for, the single-XIRR problem, what Fundprint shows instead.
2. **Your data stays with you**: the promise word for word, and how to verify it (§0).
3. **What it shows**: a screenshot of the facet chart made from **sample data only**.
4. **How it's calculated**: short version of §6, with a link to the notebook.
5. **Run it locally**: `pip install -r requirements.txt && streamlit run app/Home.py`.
6. **How it's deployed**: stlite + GitHub Pages, and the data refresh job.
7. **Limitations**, **Disclaimer**, **Licence**.

Code comments: plain English, explain *why* rather than *what*.

---

## 11. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | **Browser spike** | Synthetic CAS parses in stlite (§3), or the fallback is agreed with Shiba |
| M1 | Core logic + tests | `fundprint/` passes all §9 unit tests; matches the notebook on the same synthetic data |
| M2 | Data pipeline | `refresh-data.yml` produces `data/*.json`; fail-safe works |
| M3 | Streamlit UI (local) | Home + Time in Market work with `streamlit run`; no rupee amounts anywhere (no-rupee test passes) |
| M4 | stlite build + deploy | Live at `lab.shibaprasadb.com/fundprint`; assets self-hosted; CSP in place |
| M5 | Privacy acceptance | Network-tab check passes (§0); README + PRIVACY.md done; `shibaprasadb.com/fundprint` returns 404 (Pages off in `fundprint`, §3) |
| M6 | Launch | Blog post on shibaprasadb.com links to it |

---

## 12. Later modules (design for, don't build)

Each new analysis = one new file in `app/pages/` + logic in `fundprint/`, reusing the parsed session data:
- **Overlap**: how much your funds hold the same stocks.
- **Cost**: what Regular plans cost compared with Direct.
- **SIP timing**: did lump sums or SIPs do better in your own history?
- **Bucket edges**: let users set their own holding-period cut-offs.
- **Benchmarks**: pick from Nifty 50, Nifty 500, or a debt index for debt funds.

---

## 13. Decisions log
- `shibaprasadb.com` is on GitHub Pages → lab set up as a separate `lab` repo (§3).
- v1 shows **no rupee amounts at all**: percentages only (§7).
- Attribution is **shibaprasadb.com** only; no full name in the app, README byline or page metadata.
- Repo is named `fundprint`; **GitHub Pages stays OFF in it**. The app is published only via the `lab` repo (§3).
