# Fundprint: Editorial page style

> **Status:** Partly implemented. Everything except the chart restyle (spec section 3 and the transaction-timeline colours in 6.7), which was left out on purpose.

The page chrome now reads like a data page in a newspaper: serif headings, paper background, navy for type and controls, brick red only for "your money" in data. The source is the design brief `FP-UI-SPEC.md` (24 Oct 2026). No change to calculations, parsing, privacy or analytics.

## What changed

- **Theme** (`.streamlit/config.toml`, `web/boot.js`): paper `#FAF8F3`, ink `#1B2333`, navy `#002147` (the navy already in the code), small corners, serif headings. The four newer keys (`headingFont`, `baseRadius`, `borderColor`, `showWidgetBorder`) are valid in the Streamlit that stlite bundles (1.65) but not in the one used on a computer, so they are set only in `boot.js`. One CSS block in `app/ui.py` does the rest.
- **Loading screen** (`web/index.html`, `web/boot.js`): one static screen with the wordmark and one line of text, plus a thin moving line. stlite's progress messages are off (`disableProgressToasts`). Its error messages stay off too (`disableErrorToasts`), because the raw error can be a traceback (rule 8).
- **Header** (`web/index.html`): one slim navy bar with Home, Time in market, How it works, Source and Feedback. Below 600px the links sit behind a "Menu" text toggle (CSS only). Home and Time in market switch pages through the app's own page list, which is hidden but still there. The sidebar, toolbar and the floating Feedback button are gone. The header is part of the browser build; `streamlit run` on a computer shows no header.
- **Footer** (`ui.footer`): plain text under a hairline rule; the "runs in your browser" line moved here from the sidebar.
- **Home**: kicker, one H1, standfirst, a neutral privacy panel with the promise word for word, an outline "Try it with a sample portfolio" button, a plain "Use your own statement" heading, and the CAMS link as a text link. Upload limit is 20 MB.
- **Results page**: one H1 and the active-XIRR sentence as the standfirst (filled in after the filter is read); the radio is labelled "Show"; "Download PNG" is a small grey link under each chart; the scope sentences sit directly above the charts they describe; the table is plain HTML with a signed Gap (pts) column (brick when ahead, grey when behind, true minus sign); "How this is calculated" is a plain disclosure.
- **Copy**: first person singular, sentence case, no emoji, true minus signs.
- **Tab title and favicon**: "Fundprint: a CASual look at your mutual fund statement" on Home, "Time in market · Fundprint" on the results page; navy square with a serif "F" (`web/favicon.svg`, 32px PNG for the page icon).

## Left out, and where it differs from the brief

- **Chart restyle not done.** No `fundprint/style.py`, no Source Serif 4 font for charts, no source lines, facet changes or alt text. The charts still use their own colours (including the steel blue for the Nifty 50 and the green one-off dots) and a slightly different background (`#FAFAF7`), so they show as faint boxes on the paper page. The acceptance items about chart fonts, chart backgrounds and steel blue / green are open until that part is done. The chart sub-lines the brief asked for are plain captions above the chart instead.
- **Step-2 table keeps the ①②③ markers.** The brief said to replace them with "Required", but the numbers match the numbered badges on the CAMS form screenshot. "Required" is added to the Period row as well.
- **The `Feedback` link in the header and footer** use the existing form address, so the existing `click:feedback` event still counts both. No new events.
- The layout is `centered` as the brief says, so charts are narrower than before.

## Checks

- [x] Test suite passes (Home, results page, history warning, privacy, build).
- [x] Checked in a browser at desktop and 375px width: loading screen, header and Menu toggle, page switching from the header, Home, results table, footer. No sideways page scroll at 375px.
- [ ] Not checked: iPhone Safari, a cold first load on a slow connection, before/after screenshots for a PR.
