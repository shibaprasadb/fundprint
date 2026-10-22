# Start-up stall: diagnosis

**Status:** Diagnosis (2026-10-22). Option C was approved and is built as [spec 010](specs/010-startup-stall.md).
One correction: option D below says CLAUDE.md rules out a service worker. CLAUDE.md only rules one out at the
root of `lab.shibaprasadb.com` (`/sw.js`), not inside `/fundprint/`.

## In short

- **Start-up has no time limit anywhere.** If any one of the ~60 files it downloads stops arriving, the page shows
  "First-time load takes 5-10 secs. Almost there…" for good, with no message. This happened locally for every
  start-up file tried: Pyodide itself, the package list, any Python package, the Streamlit wheel, stlite's own
  scripts and the app manifest.
- **When a file fails outright instead of hanging, the user sees one of four different things**, none of them in
  plain English. One is a raw Python traceback in a red box, which goes against rule 8 ("no tracebacks"). No case
  showed statement data; no statement exists at start-up.
- **The live incident** (about 20 package downloads with no answer, note up for 4+ minutes) looks exactly like the
  "25 packages never answer" test here. Whether GitHub/Fastly throttled the site could not be proven without
  hammering the live site, which was not done. Whatever the cause, the page gives the user no way out and no hint
  to reload.
- **Recommended fix (two small files in `web/`):**
  1. `boot.js`: after 60 s, change the note to "This is taking longer than usual…" with a Reload button; on a
     start-up error, say "Fundprint could not finish loading. Check your connection and reload the page."
  2. `pyodide-start.mjs`: restart a download that has had **no new data for 20 s** (up to twice), checking the
     file's hash itself.

  Both were tried on a scratch copy of `dist/`. With them, the "25 packages never answer" case loaded in 25 s
  instead of never, a slow but steady download was left alone, and a file that never arrives ends with the plain
  message instead of a silent spinner.

## How it was tested

`scripts/diagnose_startup_stall.py` (new, diagnosis only, not part of the app) serves `dist/` with the same
GitHub-Pages-like server as `scripts/diagnose_offline.py` (`request_queue_size` 256), breaks one file on purpose
and watches the page in Chromium (Playwright) for 90-110 s. Faults come from two places:

- **Playwright routing:** the browser never gets an answer (hang), gets a 404, or the connection is reset. A
  30-second delay was also tried.
- **The test server itself, through the real network stack:** no answer at all, half the file then nothing, or the
  whole file sent slowly but steadily over 45 s.

Only the app's own start-up was used; no statement, sample or real, was involved. Healthy local start-up takes
about 6 s from opening the page to the uploader being drawn.

One trap for anyone re-running this: the Mac went to sleep between steps and froze several runs, which at first
looked like more stalls. Keep the machine awake during long runs.

## What the user sees today

"The note" is the white box with the spinner: "First-time load takes 5-10 secs. Almost there…". stlite also shows
its own small progress messages at the bottom right ("Loading Pyodide.", "Installing packages." and so on); they are
on by default and stay spinning when start-up stops.

| File | Fault | What the user sees (after 90 s or more) |
|---|---|---|
| A Python package (`pandas`, `casparser`), or 25 packages at once | Never answers | The note for good. Progress messages stuck at "Installing packages." |
| `pandas` package | Half sent, then nothing | Same: the note for good |
| `pandas` package | Sent slowly over 45 s | Loads fine in 52 s |
| `pandas` package | 30 s late | Loads fine |
| `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json` | Never answers | The note for good. Progress stuck at "Loading Pyodide." |
| `pyodide.asm.wasm` | Half sent, or 404 | The note for good (a 404 is only logged to the console) |
| Streamlit wheel (`vendor/stlite/wheels/`) | Never answers | The note for good |
| `vendor/stlite/stlite.js`, a stlite script chunk, `app-manifest.json` | Never answers, or 404 | The note for good, and nothing else at all: `boot.js` never gets past its first line |
| `pyodide-lock.json` | 404 | The note for good, plus a red box: "Error during booting up", `Unexpected token 'N', "Not Found" is not valid JSON` |
| Streamlit wheel | 404 | The note for good, plus a red box: "Error during booting up" and a **raw Python traceback** from micropip |
| `pandas` package | 404, or connection reset | Start-up "finishes": the note goes and Streamlit's red box says "This app has encountered an error… (if you're on Streamlit Cloud, click on 'Manage app'…)" |
| `app/Home.py` | 404 | The note stays, plus a "Script execution error… SyntaxError" box quoting "Not Found" |

Screenshots of every case are in the shared notes folder of the session that ran this (`startup-stall/`), not in
the repo.

## Why it happens

1. **Nothing has a time limit.** stlite's worker (its code is embedded in `vendor/stlite/index-*.js`) waits on
   `fetch`, `pyodide.loadPackage` and `micropip.install` with no timer. A browser does not give up on a request that
   is connected but gets no data, so one silent file stops everything.
2. **The browser hides package progress.** Pyodide asks for each package with an `integrity` hash. Chrome then
   holds the whole answer back until the file has fully arrived and been checked. So for packages, "has it started
   arriving?" can't be seen from outside; a plain timer around `fetch` measures the whole download.
3. **The note only ever goes away.** `boot.js` removes it once the first real element is drawn and never changes
   it otherwise. Because `boot.js` imports `stlite.js` on its first line, if that file fails, `boot.js` doesn't run
   at all.
4. **stlite's own error box shows the raw error.** `mount()` is called without `disableErrorToasts`, so a start-up
   error is shown as "Error during booting up" plus the error text, which for Python errors is a traceback.
   (`client.showErrorDetails: none` only affects Streamlit's own boxes, not this one.)
5. **Pyodide does not stop on a missing package.** It logs the failure and carries on, so a missing package
   shows up later as an app error rather than a start-up error.

## Where a time limit or message can go

- **`web/boot.js`, around `mount`.** `mount()` returns an object whose `_kernel` sends `loadProgress`,
  `loadError` and `loadFinished` events. The leading underscore means stlite treats it as internal; the version is
  pinned, but a test should check that it is still there on each stlite upgrade. A plain timer needs nothing from
  stlite.
- **The loading note (`#loading-note` in `index.html`).** Its text can be swapped and a Reload button added. The
  security policy blocks inline scripts, so the button's click handler has to live in `boot.js`, not in an
  `onclick` attribute.
- **stlite options.** `disableErrorToasts` hides the traceback box; `disableProgressToasts` hides the bottom-right
  progress messages. stlite has no time-limit option.
- **`web/pyodide-start.mjs`.** It runs inside the worker before Pyodide starts, and every start-up download there
  (Pyodide, packages, micropip, app files) goes through the worker's `fetch`. It is the only place a retry can be
  added without editing vendored files.
- **Not:** an inline script in `index.html` (blocked by the security policy), or edits to `vendor/` (re-fetched
  and hash-pinned by `fetch_vendor.py`).

Every message must be fixed text. Nothing from the error, the page or a file name goes into it (rule 8).

## Options

| | What | Tested | For | Against |
|---|---|---|---|---|
| **A** | **Plain messages only** (`boot.js`): 60 s "taking longer" note with Reload; "could not finish loading" on `loadError` or if `stlite.js` or the manifest fails; `disableErrorToasts: true` | Yes | ~25 lines. The user is never left with a silent spinner. No traceback. | Fixes nothing by itself: the user still has to reload. |
| **B** | A **+ a simple timer retry**: cancel and ask again if `fetch` hasn't finished in 20 s | Yes | Short | **Cuts off slow but healthy downloads**: the 45-s `pandas` took 91 s and was downloaded three times (point 2 above). Misses a half-sent `pyodide.asm.wasm`, which has no hash, so its `fetch` finishes as soon as the first bytes arrive. Not recommended. |
| **C** | A **+ a retry when no new data arrives for 20 s** (`pyodide-start.mjs`): read the file itself, restart if it stalls, check the hash itself with `crypto.subtle`; the last try has no timer | Yes | Fixes stalls that clear up on a second try (25 hung packages: ready at 25 s instead of never). Slow downloads untouched (52 s, same as today). Catches half-sent files too. Can never make things worse than today. | ~60 lines in the worker, including our own hash check. Each file is held in memory before Pyodide gets it (Pyodide does this anyway), and the wasm file loses streamed compiling: no visible difference locally, but worth timing on a phone. A wrapper around `fetch` must be re-checked on each stlite/Pyodide upgrade. A retry cannot help if the server keeps failing; then A's message takes over. |
| D | Cache files with a service worker | No | Repeat visits wouldn't depend on the network | Ruled out: no service worker on the shared `lab.shibaprasadb.com` origin (CLAUDE.md, Hosting). |
| E | Download less at start-up (fewer or smaller packages) | No | Fewer chances to stall, faster first load | Separate piece of work; doesn't remove the need for A. |

## Recommendation

**C, which includes A.** Ship A first on its own if a smaller step is wanted; it is safe and small.

Details for whoever builds it:

- `boot.js`: start the 60-s timer before anything else; load stlite with `await import()` inside `try`/`catch`
  so a failed `stlite.js` or manifest shows the failure message; listen for `loadError` on `mount(...)._kernel`;
  clear the timer when the note is removed; pass `disableErrorToasts: true`. Leave the progress messages on, as
  they are the only sign of progress.
- `pyodide-start.mjs`: only same-site `GET` requests; 20 s with no new data, two timed tries, then one try with no
  timer. Also worth retrying once on a network error such as a reset connection (today that leads to the
  "Manage app" box). This last part was **not** prototyped.
- Wording (fixed text only): "This is taking longer than usual. A slow or busy connection can cause this." with a
  spinner and Reload button; "Fundprint could not finish loading. Check your connection and reload the page." with
  a Reload button.
- Tests: static checks in `tests/test_app.py` (timer and messages in `boot.js`, the retry in
  `pyodide-start.mjs`, `disableErrorToasts`, `_kernel` still in the pinned stlite), and a run of
  `scripts/diagnose_startup_stall.py` against the new build (`hang-pkg-pandas`, `hang-many-pkgs`,
  `srv-slow45-pandas`, `404-stlite-js`, `baseline`).
- Optional, owner's call: data-free Umami events such as `load:slow` and `load:failed`, to learn how often this
  happens for real users. Each would have to be added to `ALLOWED_EVENTS` in `feedback.js` and pass
  `fundprintBeforeSend` (CLAUDE.md, Analytics).
- Docs: a new numbered spec, and a line in `ARCHITECTURE.md` on start-up.

The two prototype files are in the shared notes folder (`startup-stall/prototype-boot.js` and
`prototype-pyodide-start.mjs`). They are rough: test-only timings (30 s instead of 60 s), no tests, no spec.

## Not covered

- The live site was not tested again, to avoid adding load or tripping limits. The cause of the live incident
  (throttling, a dropped connection, something else) is unknown.
- Only Chromium was used. Safari/iPhone behaviour, including WebKit's own request time limits, was not checked.
- Timings are from a fast local machine. The 20-s and 60-s values should be sanity-checked on a slow phone
  connection before release.

## Seen along the way (not this issue)

- Streamlit's red error box can show "Ask Google" and "Ask ChatGPT" links that put the error text in the link
  address. Streamlit shows them only on localhost (its `showErrorLinks` setting defaults to "auto"), so the live
  site does not show them, and with `client.showErrorDetails: none` the text is the generic redacted message.
  Turning the setting off explicitly would make that certain; not checked further.
