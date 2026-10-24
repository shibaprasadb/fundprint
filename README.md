# Fundprint

*A CASual look at your mutual fund statement.*

**Try it:** [lab.shibaprasadb.com/fundprint](https://lab.shibaprasadb.com/fundprint) · Beta · Free and open source

## Why this exists
One XIRR number hides most of the story. Indian DIY mutual fund investors get a single portfolio XIRR from their fund app. That number blends money invested five years ago with money invested last month, so it can't say what is really driving your returns. It also never says whether a plain index fund would have done better.

Fundprint reads your CAMS/KFintech statement in your browser and shows your returns three ways:
- **By time held.** Returns for each holding period (under 1 year, 1-3, 3-5, 5+), compared with the same purchases replayed into a Nifty 50 index fund.
- **Fund by fund.** Which of your equity funds are ahead of or behind their Nifty 50 twin (the same purchases on the same dates), and how much of your equity money each one holds.
- **How regularly you invest.** What share of your purchases followed a regular monthly pattern, and your usual investing day, shown against the Nifty 50.

No statement yet? Start with a made-up sample portfolio, or follow the four-step guide in the app to request yours. It takes about a minute.

## Your data stays with you
**Nothing is stored. Your file is read and dropped when you close the tab.**

Fundprint runs entirely in your browser. Your statement is never uploaded to any server. See [PRIVACY.md](PRIVACY.md) for the rules and how to check them yourself. Open DevTools → Network, upload a statement, and watch that your file is never sent anywhere. Or load the page, turn on airplane mode, and upload your statement: it still works.

## Analytics
The live page counts visits with [Umami](https://umami.is), to see how many people use it. It sets no cookies, sends only anonymised visit data, and sends nothing from your statement. The only click it counts is on the Feedback link, as a bare event with no details. To check, open the Network tab: the only requests to another site go to `gateway.umami.is`.

The Feedback link opens a form run by [Tally](https://tally.so) in a new tab. Fundprint sends nothing to the form. More in [PRIVACY.md](PRIVACY.md#analytics).

## What it shows
Everything is in percentages. No rupee amounts appear anywhere, so every screen and download is safe to share.

- **Your active XIRR** in one sentence at the top, for the funds you still hold.
- **Where your money sits:** the share of your money in each holding period.
- **You vs the Nifty 50, by holding period:** your XIRR next to the index fund's, plus a table with the share of money, both XIRRs, the gap in percentage points and both absolute returns. Under-1-year results are faded: an XIRR worked out from a few months swings wildly, so read the absolute return there.
- **All funds or equity funds only:** a switch for the section above.
- **The big picture**, for the whole portfolio:
  - each equity fund against its Nifty 50 twin (your 12 largest equity funds)
  - how regularly you've invested, with every purchase shown against the Nifty 50
- **Download PNG** under every chart.

It also handles two common snags:
- **Missing history.** If your statement starts after your first investment in a fund, results still show. A warning names the affected funds and explains how to request a complete statement.
- **Funds it can't classify.** You can set the asset class yourself, and the charts update.

Fundprint works on a phone, and keeps working if your connection drops after the page has loaded.

## How it's calculated
1. Read the Detailed CAS (CAMS/KFintech) with [casparser](https://github.com/codereverie/casparser).
2. Keep only units still held. Sold units come off the oldest purchases first. Bounced SIPs are removed, and reinvested dividends count as free units bought on their own date.
3. If the statement starts after your first investment in a fund, the units you already held at the start are left out, because their purchase date and cost aren't in the statement.
4. Put each held purchase in a bucket by age, and work out XIRR for each bucket.
5. Replay the same amounts on the same dates into UTI Nifty 50 Index Fund (Direct, Growth) and compare. Same cash flows, different fund, so the gap is about the fund and not about timing. Purchases older than the benchmark's price history are left out of both sides.
6. **Index twin per fund:** each equity fund's purchases are replayed into the Nifty 50 index fund and the two XIRRs are compared.
7. **Regular investing:** for each fund, find the day of the month you most often invest on. A purchase counts as regular if it's within 5 days of that day. A fund needs at least 3 such purchases to have a pattern.

The same explanation is in the app under "How this is calculated". The reference notebook is in [notebooks/xirr_analysis.ipynb](notebooks/xirr_analysis.ipynb).

## Run it locally
```bash
pip install -r requirements-dev.txt
streamlit run app/Home.py
```
Use the built-in sample portfolio to try it. The local version has no header bar; only the browser build has one. For tests, the browser build and everything a pull request needs, see [CONTRIBUTING.md](CONTRIBUTING.md).

## How it's deployed
- Fundprint is a set of static files that run in your browser, built with [stlite](https://github.com/whitphx/stlite) (Streamlit made to run client-side). There is no server.
- Public fund prices and fund categories are refreshed automatically every day.
- Everything the build downloads is pinned to an exact version and checked before the site is published.
- The site is published only at `lab.shibaprasadb.com/fundprint`.

How it all fits together, in plain words: [ARCHITECTURE.md](ARCHITECTURE.md).

## Getting your statement
Fundprint needs the **Detailed** Consolidated Account Statement (CAS) from CAMS or KFintech. A Summary statement won't work. On the CAMS statement page:
- **Statement type:** Detailed (includes transaction listing).
- **Period / from date:** a date before your first-ever investment. Earlier is fine. If it starts too late, part of your history is missing.
- **Password:** something simple you'll remember. You'll type it into Fundprint once, and it is never stored.

The PDF usually arrives by email within a few minutes. The Home page walks you through this in four steps, with an annotated screenshot of the form.

## Limitations
- Units already sold aren't counted (active holdings only), so results look slightly kinder than reality.
- Cash paid out by IDCW payout plans isn't counted as a return.
- XIRR reflects timing as well as fund quality; the index replay is there to separate the two.
- Every fund is compared with the Nifty 50, not with its own category.
- The fund-by-fund chart shows equity funds only (no debt or gold), and only the 12 largest.
- Regular rebalancing on dates other than your usual investing day isn't recognised as regular investing yet.
- CAMS/KFintech Detailed CAS only (no NSDL/CDSL). Files up to 20 MB.
- The first load on a phone can take up to a minute.

## Disclaimer
Fundprint is an analytics tool, not investment advice. Past returns don't predict future returns. Fundprint is not affiliated with CAMS, KFintech, AMFI, or any fund house. Benchmark: UTI Nifty 50 Index Fund – Direct Growth, using public NAV data.

## Licence
MIT. Contributions welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue, see [SECURITY.md](SECURITY.md). Design notes and specs are in [docs/specs](docs/specs/).
