# 006: Partial history: warn, don't block

> **Status:** Implemented
> **Notes:** Changes the "statement starts after first investment" error in 003-onboarding into a non-blocking warning. Differences from the text below: the results page has no `#step-2` anchor (Step 2 lives on Home), so "How to do this" is an expander under the warning that shows the Step 2 form table and the CAMS button. Fund names in the warning have every punctuation mark escaped, so a name from the PDF can't turn into a link or image (audit finding FP-01). Code: `fundprint/history.py`, `fundprint/lots.py`.

## Problem
When a statement starts after the user's first purchase in a fund, the app currently shows an error and stops. Results should still appear; the user just needs to know which parts are incomplete. The current check also seems to fire on statements that are complete.

## Goal
1. Detect missing history **reliably, per fund**.
2. **Always show results**, handling the missing part correctly.
3. Show a **clear, specific warning** that names the affected funds and points to the fix.

---

## 1. Detection (per fund)
A fund has **partial history** if its **opening balance is above zero**: casparser's per-scheme `open` field is `> 0.001` units. That means the statement started while units were already held.

- This **replaces** the current guess-based check (first transaction is a sale, units don't add up, etc.). Remove that check.
- Funds whose first transaction is a merger switch-in, a transfer from another folio or a segregated-portfolio entry are **not** partial history as long as `open` is 0. Don't flag them.
- **Keep as a separate safety check:** after processing, if a fund's computed units differ from the statement's closing balance (`close`) by more than 0.01 units, mark the fund as **"doesn't reconcile"**. Use the same warning, worded differently (§3).

---

## 2. How partial-history funds are handled
Treat the opening balance as the **oldest lot**, with an unknown date and cost:
1. **FIFO still applies:** sales use up the opening-balance units first, then the earliest purchases in the statement. This keeps every later purchase's held units correct.
2. **Opening-balance units still held at the end are left out** of the allocation chart, the bucket chart, the table and chart A (funds vs index twin), because their date and cost are unknown.
3. **Purchases inside the statement period are included normally.**
4. **The periodicity chart is unaffected:** it only counts purchases shown in the statement.
5. If **all** of a fund's held units come from the opening balance, the fund simply doesn't appear in the return charts. It's listed in the warning instead.

---

## 3. The warning

### Placement
At the top of the results page (Time in Market), above Section 1. Use `st.warning` styling; it doesn't block anything below it.

### Text (partial history)
> **Some of your history is missing.** Your statement starts after you first invested in these funds:
> - Fund A
> - Fund B
>
> Units bought before the statement's start date aren't included in the results below, because their purchase date and cost aren't in the statement. Everything else is calculated normally.
> For complete results, request your statement again with an earlier start date. [How to do this ↓](#step-2)

- Fund names use the same short form as chart A (plan and option text removed).
- If more than 5 funds are affected, list 5, then "and N more".

### Text (doesn't reconcile)
> **Some funds don't add up.** The units for these funds don't match the statement's closing balance, so their results may be off:
> - Fund C
>
> If this keeps happening, please [send feedback](https://tally.so/r/2EqQGg) (no statement needed).

If both cases apply, show both blocks in one warning box.

### Must not
- No rupee amounts or unit counts in the warning; fund names only.
- Never block or hide the results.

---

## 4. Related changes
- **003-onboarding:** the error-table row "Statement starts after first investment" becomes this warning. Remove it from the error flow.
- **"How this is calculated":** add one line: *"If your statement starts after your first investment in a fund, the units you already held at the start are left out, because their purchase date and cost aren't in the statement."*

---

## 5. Tests (synthetic data only)
- Fund with `open = 0` and a merger switch-in as its first transaction → **no** warning; included normally.
- Fund with `open > 0`, no sales → opening units excluded; in-period purchases included; fund named in the warning.
- Fund with `open > 0` and a sale bigger than the opening balance → the sale uses the opening units first, then the earliest in-period purchase; held lots are correct.
- Fund whose held units are all from the opening balance → absent from the return charts, named in the warning.
- Periodicity chart counts the same purchases with or without the opening balance.
- Fund whose computed units differ from `close` by more than 0.01 → "doesn't reconcile" block.
- Complete statement → no warning at all.
- More than 5 affected funds → 5 listed, then "and N more".
- No-rupee test still passes with the warning visible.

---

## 6. Done when
- [ ] Partial history is detected only via the opening balance; the old guess-based check is removed.
- [ ] Results always render; opening-balance units are excluded as described.
- [ ] The warning names the affected funds and links to Step 2; the "doesn't reconcile" block works.
- [ ] 003-onboarding's error table and "How this is calculated" are updated.
- [ ] All tests above pass; privacy and no-rupee checks still pass.
