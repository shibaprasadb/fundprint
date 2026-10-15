# Fundprint: Two new insights

> **Status:** Implemented
> **Notes:** Chart B is the periodicity chart; earlier drafts of chart B are described in its intro but no longer apply. Built chart B differs from the text below in small ways: it is labelled 'All funds', the title says 'transactions' not 'investments', and one-off dots are filled neon green, not hollow grey.

An add-on task for the **Time in Market** page at `lab.shibaprasadb.com/fundprint`. Change only what this file describes. All existing rules still apply: **no rupee amounts anywhere**, nothing stored, nothing sent.

Two charts, no more:
- **A. Which funds are ahead of their index twin?** Where the overall result comes from.
- **B. When did you buy?** How the timing of purchases looks against the market.

Both use data the app already has: the user's **held purchase lots** (date, share of money, fund) and the **Nifty 50 benchmark NAV history**. No new data sources.

---

## Page order

The page gets two sections. The existing analysis stays first, because the bucket comparison is the product's main idea. The new charts follow as **overall pictures with a fixed scope**, so they are not affected by the scope toggle.

**Section 1: By time in market** (existing content)
1. Scope toggle (All funds / Equity only), placed at the top of this section under a heading, so it's clear it controls only this section.
2. Allocation chart (existing)
3. Bucket facet chart (existing)
4. Table (existing)

**Section 2: The big picture** (no toggle)
5. **A. Which funds are ahead of their index twin?** (new): always **equity funds only**.
6. **B. When did you buy?** (new): always **all funds**, coloured by asset class.

Each new chart shows its fixed scope as a small label under its title: *"Equity funds only"* / *"All funds, by asset class"*. A short line under the "The big picture" heading says: *"These charts always use your whole portfolio; the toggle above doesn't change them."*

7. "How this is calculated" (existing, at the end of the page, with additions in §C)

Both new charts work with sample data.

---

## A. Which funds are ahead of their index twin?

### What it shows
One horizontal bar per **equity fund**: the gap between the fund's XIRR and the XIRR of its **Nifty 50 twin** (the same purchases, on the same dates, replayed into the Nifty 50 index fund). Measured in percentage points.

### Calculation
- Group held lots **by scheme** (ISIN), combining the same fund across folios.
- For each fund, using only that fund's held lots:
  - `my_xirr` = XIRR of its cash flows (existing method);
  - `twin_xirr` = XIRR of the same purchases replayed into the benchmark (existing replay method);
  - `gap = my_xirr − twin_xirr`, in percentage points.
- `share` = the fund's held cost ÷ total held cost of the funds shown, as a percentage. This is an internal amount used only to make a %; it is never shown.
- **Young money rule:** if a fund's money-weighted average holding age is under 1 year, use the **absolute-return gap** (`my_abs − twin_abs`) instead of XIRR, and fade the bar (same rule and reason as the main chart).
- Lots older than the benchmark history are excluded, as in the main analysis.

### Which funds appear
- **Equity funds only** (asset class = Equity). The chart is not affected by the scope toggle, because comparing debt or gold with the Nifty 50 per fund isn't meaningful. Show a small note under the chart if non-equity funds were left out: *"Debt, gold and other non-equity funds aren't shown here."*
- If there are more than 12 equity funds, show the 12 largest by share, with a note: *"Showing your 12 largest equity funds."*
- If there's only one equity fund, still show it.

### Chart design
- Horizontal bars from a centre line at 0: right = ahead of its twin, left = behind.
- Sorted from most ahead (top) to most behind (bottom).
- **Fund label** (left): a short scheme name. Strip plan and option text such as "- Direct Plan - Growth", "Growth Option", "(Non Demat)". Shown in the user's own browser only, as part of their own results.
- **Value label** at the bar end: `+3.2 pp` / `−1.8 pp`.
- **Share label** in muted grey next to the fund name: `18% of equity money`.
- Faded bars (young money) carry a small marker: `<1Y, absolute return`.
- Style: same palette and fonts as the existing charts. Bars in the accent colour; faded bars at reduced opacity; centre line dark and thin; no gridline clutter.

### Title and subtitle
- **Title, generated:** `"N of M equity funds are ahead of their Nifty 50 twin"`.
- **Subtitle, fixed:**
  > *Each fund compared with a Nifty 50 index fund bought on the same dates, not with its own category. A midcap or small cap fund can trail the Nifty 50 simply because its whole category did.*

### Wording rules
Descriptive only: "ahead of / behind its Nifty 50 twin over this period". Never "underperforming", "bad fund", "switch", "exit" or "consider".

---

## B. When did you buy? (periodicity)

> Earlier drafts of this chart (a "% near 52-week high" headline, then a "timing vs autopilot" number) were dropped because they compared the user's money with the Nifty 50, which they never invested in. This chart shows something purely factual: **how regular the user's investing has been.**

### What it shows
- **The chart:** the Nifty 50 index fund's NAV over the user's investing years, as market context, with a dot on each purchase. Dots are coloured by whether the purchase was **periodic** (part of a regular pattern) or **one-off**.
- **One headline number:** the % of purchases (by count) that were periodic.

### Which transactions count
- **Purchases the user made:** `PURCHASE` and `PURCHASE_SIP`. Include purchases since sold, because this is about investing behaviour, not current holdings.
- **Excluded:** reinvested dividends, switch-ins and STP transfers (internal moves, not new money), reversals and the purchases they cancel, and anything without units.
- **All asset classes,** not affected by the scope toggle.
- Each transaction counts once. SIPs in three funds on the same day are three purchases.

### Periodicity logic
1. **Group by fund** (scheme/ISIN, across folios). *Grouping is a named constant: `PERIODICITY_GROUP = "fund"`, with `"all"` as the alternative.*
   Why per fund: people often run SIPs on different days in different funds (say the 5th in one, the 20th in another). A single mode across everything would wrongly mark the second SIP as one-off.
2. **Usual day:** within each group, take the **mode of the day of the month** across its purchases. If there's a tie, pick the day whose ±5-day window (step 3) contains the most purchases; if still tied, pick the earliest day.
3. **Periodicity zone:** usual day ± **5 days**, measured **around the month end** (circular), so a usual day of the 28th covers the 23rd to the 31st and the 1st and 2nd.
   `distance(d, m) = min(|d − m|, 31 − |d − m|)`; a purchase is in the zone if `distance ≤ 5`.
4. **Minimum pattern:** a group only counts as having a pattern if **at least 3 purchases** fall in its zone. Otherwise all its purchases are one-off. This stops a single lump sum from counting as "periodic" by matching its own date.
5. **Result:** `periodic_% = periodic purchases ÷ all counted purchases × 100`, rounded to a whole number.

Keep the ±5-day window and the 3-purchase minimum as named constants.

**Known gap (accepted for now):** rebalancing and planned top-ups that happen on a regular schedule but on a different day won't be recognised as periodic.

### Headline (generated)
- **Title:** **"72% of your investments followed a regular pattern"**
- **Subtitle:** *"Made within 5 days of your usual investing day for that fund."* Then the usual day(s):
  - one usual day across funds → *"Your usual day: the 5th."*
  - several → *"Your usual days: the 5th, the 20th."* (at most 3, ordered by how many purchases they cover; then "and others").
- If **no fund has a pattern:** title *"Your investments don't follow a regular monthly pattern"*, and no usual-day line.

No other numbers in the headline area.

### Chart design
- **Line:** Nifty 50 index fund NAV, thin, in the dark text colour (`DARK`), from shortly before the first purchase to the latest NAV date. Purely market context.
- **Dots:** one per counted purchase, at (purchase date, benchmark NAV that day).
  - **Periodic:** accent colour (`ACCENT`), semi-transparent so regular SIP dots read as a steady row.
  - **One-off:** hollow grey circle (outline only, `MUTED`).
- **Dot size:** **all dots the same size.** The headline is a count of purchases, so every purchase gets equal weight on the chart too. No per-dot labels or percentages.
- **Legend:** two entries only: **Periodic** / **One-off**.
- Asset-class colouring is dropped from this chart; colour now means periodic vs one-off.
- Y-axis label: *"Nifty 50 index fund NAV"* (public values, not user amounts). X-axis: years.

### Caption (fixed, small text under the chart)
> *Every purchase you've made, including ones since sold, shown against the Nifty 50 for context. "Periodic" means within 5 days of your usual investing day for that fund. Regular rebalancing on other dates isn't recognised yet.*

---

## C. Additions to "How this is calculated"

Add two short paragraphs in plain English:
- **Index twin per fund:** each fund's purchases are replayed into a Nifty 50 index fund on the same dates, and the two XIRRs are compared. It's the Nifty 50 for every fund, not each fund's own category.
- **Regular investing:** for each fund, Fundprint finds the day of the month you most often invest on, and counts a purchase as periodic if it's within 5 days of that day (counting across the month end). A fund needs at least 3 such purchases to have a pattern. Switches, reinvested dividends and reversed payments aren't counted.

---

## D. Other details

- **Downloads:** each new chart gets a PNG download button. The existing `click:download-chart` Umami event covers them; no new events.
- **Sample data:** the synthetic sample must produce a meaningful result for both charts: at least 3 equity funds with different gaps; SIPs on two different usual days (e.g. the 5th and the 20th, one near a month end to exercise wrap-around); and a few lump sums so some dots are one-off.
- **Mobile:** fund labels wrap or truncate cleanly; the dot chart stays readable at phone width.
- **No rupee amounts:** shares, gaps and NAV values only. The existing no-rupee test must cover both new charts.

---

## E. Tests (synthetic data only)

- A fund whose NAV moves exactly with the benchmark → gap ≈ 0.0 pp.
- A fund that grows 15%/yr against a benchmark growing 10%/yr → positive gap of about 5 pp.
- Same scheme in two folios → one bar, combined.
- Young-money fund (all purchases under 1 year old) → uses the absolute-return gap and is faded.
- Non-equity funds never appear in chart A; the note shows when any were left out.
- One fund with a monthly SIP on the 5th for 12 months → 100% periodic, usual day "the 5th".
- Two funds, SIPs on the 5th and the 20th → both recognised as periodic (per-fund grouping); with `PERIODICITY_GROUP = "all"` the 20th ones become one-off.
- Usual day 28th, purchases on the 30th and the 2nd → inside the zone (wrap-around); a purchase on the 4th → outside.
- A fund with only 2 purchases on the same day → both one-off (below the 3-purchase minimum).
- A single lump sum → one-off.
- Reinvested dividends, switch-ins, STPs and reversed purchases are not counted.
- Ties in the mode resolve by window coverage, then the earliest day.
- No patterns at all → the "don't follow a regular monthly pattern" title, and no usual-day line.
- The no-rupee test passes with both charts rendered.

---

## F. Done when

- [ ] Section 1 ("By time in market") comes first, with the scope toggle at its top controlling only the allocation chart, bucket chart and table.
- [ ] Section 2 ("The big picture") follows, with both new charts and their fixed-scope labels; changing the toggle does not change them.
- [ ] Chart A shows equity funds only, sorted, with gap, share and young-money labels, and the fixed subtitle.
- [ ] Chart B shows the NAV line, purchase dots coloured periodic / one-off and sized by share, the compact legend, the periodicity headline with usual day(s), and the caption. The old timing number is gone.
- [ ] Both follow the existing style and work on mobile.
- [ ] "How this is calculated" includes the two new paragraphs.
- [ ] All tests in §E pass; privacy and no-rupee checks still pass.
