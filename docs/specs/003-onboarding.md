# Fundprint: Simpler onboarding

> **Status:** Implemented
> **Notes:** Small differences: the sample banner has no emoji, and its link goes to the top of Home rather than to the 'Use your own statement' section.

An add-on task for the live app at `lab.shibaprasadb.com/fundprint`. Change only what this file describes. All existing privacy rules still apply; in particular, nothing here may store anything in the browser or send anything anywhere.

**Problem:** most visitors will leave at the step where they have to request their Consolidated Account Statement (CAS) from CAMS. The form is unfamiliar, the PDF arrives by email, and people don't come back.

**Goal:** fewer people give up at that step. Three changes:
1. **Show the payoff first**: sample data is the first thing people see.
2. **A 60-second checklist** for requesting the CAS, with an annotated screenshot.
3. **Make coming back easy**: clear "request now, return later" guidance, and re-entry is just upload + password.

Out of scope for now: drag-and-drop upload, other statement formats (Groww, Kuvera, etc.), and email or Account Aggregator integrations.

---

## 1. Show the payoff first

### Home page order (top to bottom)
1. Title + tagline: **Fundprint**: *a CASual look at your mutual fund statement.*
2. The privacy promise block, unchanged and word for word:
   > **Nothing is stored. Your file is read and dropped when you close the tab.**
3. **Primary button: "See it with sample data"**: large, first, impossible to miss.
   Under it, one line: *"A made-up portfolio, so you can see what Fundprint shows before using your own."*
4. **"Use your own statement"** section (§2 and §3).

### Sample data behaviour
- Loads the synthetic sample portfolio and goes straight to the analysis page.
- The analysis page shows a clear banner while sample data is in use:
  > 🧪 **You're looking at a sample portfolio (made-up data).** [Use your own statement →]
  The link goes back to the Home page's "Use your own statement" section.
- The sample must be fully synthetic and look realistic: a mix of SIPs and lump sums across 5+ years, a couple of equity funds and one debt fund, a few redemptions, so every chart and bucket has something to show.
- Percentages only, as everywhere else in the app.

---

## 2. The CAS checklist

Shown under **"Use your own statement"**, below the upload box (§3), as a short numbered checklist. Open by default.

### Header
> **Don't have your statement yet? It takes about a minute to request.**

### Steps

**Step 1. Open the CAMS statement page**
- A button: **"Open CAMS statement page ↗"** linking to `https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement`.
- It must open in a **new tab** (`st.link_button`, or an `<a target="_blank" rel="noopener noreferrer">`), so Fundprint stays open in this tab.
- Line under it: *"Fundprint stays open in this tab."*

**Step 2. Fill in the form like this**

| Field | Choose | Note |
|---|---|---|
| Statement type | **Detailed** (includes transaction listing) | **Required.** A Summary statement won't work. |
| Period / from date | **A date before your first-ever investment** | Earlier is fine. Missing history makes results wrong. |
| To date | Today | |
| Folio listing | Any option | All work. |
| Email + PAN | Yours | The PDF is emailed to you. |
| Password | **Something simple you'll remember** | You'll type it here once. Fundprint never stores it. |

Then the **annotated screenshot** (see Assets).

**Step 3. Check your email**
> The statement usually arrives from CAMS within a few minutes as a PDF attachment. If you can't see it, check Spam or Promotions.

**Step 4. Come back and upload it**
> Upload the PDF above and type the password you just set.

Small footnote: *"Already have a CAS from KFintech or CAMS? That works too, as long as it's the Detailed one."*

### Assets
- `app/assets/cams_form_annotated.png`: a screenshot of the CAMS form with **Detailed** selected and the date fields visible, annotated with simple arrows or numbered markers matching the table above (① Detailed, ② From date, ③ Password).
  - **The maintainer provides the screenshot.** It must contain **no personal details**: no email, PAN or name typed in.
  - Annotations: thin lines and small numbered circles in the app's accent colour; no clutter.
  - Shown at a readable width on desktop; full width on mobile.
  - Alt text: *"CAMS statement form with Detailed selected, the from-date set early, and a password field."*
- Until the screenshot is supplied, show the table alone; don't block the release on it.

### Copy tone
Short, friendly, no jargon. Say "statement", not "CAS", in step text (keep "CAS" only in headings and the footnote).

---

## 3. Make coming back easy

### "Request now, come back later" note
Directly above the checklist:
> 💡 **Request it now and come back when the email arrives.** Bookmark this page, or copy its link:

Then show the page URL in a code block (`st.code("https://lab.shibaprasadb.com/fundprint", language=None)`) so people get Streamlit's built-in copy button. Don't use custom clipboard JavaScript.

### Re-entry is just upload + password
- The **upload box sits above the checklist**, always visible, under a heading: **"Already have your statement?"**
- A returning visitor should only need to: choose the file → type the password → see results. No other clicks.
- Show the **password field once a file is chosen**, with the hint: *"The password you set on the CAMS form."* Run the analysis automatically when the password is entered (Enter key, or a single **"Show my results"** button).
- Keep the existing file-picker upload. **No drag-and-drop work in this task.**

### Clear error messages (no technical details, no statement data)
| Situation | Message |
|---|---|
| Wrong password | "That password didn't open the file. It's the one you set on the CAMS form." |
| Summary CAS | "This is a Summary statement. Please request the **Detailed** one (Step 2 below)." |
| Not a CAS / unreadable | "Couldn't read this file. Is it a CAMS or KFintech statement PDF?" |
| Partial history detected (first transaction is a redemption or units don't add up) | "Your statement seems to start after your first investment. Request it again with an earlier from-date for accurate results." |

Each error message links or scrolls to the relevant checklist step.

### Must not
- **No remembering progress.** Don't save anything to localStorage, cookies or session storage to "resume" later. Returning visitors simply upload again.
- No email capture, reminders or notifications.

---

## 4. Mobile

Many visitors will arrive from a phone, and the CAS email often arrives on the phone too.
- All buttons full width on small screens.
- The CAMS button opens a new tab on mobile too.
- Uploading from the phone's file picker (Downloads / Files app) must work; test on Android Chrome and iOS Safari.
- The annotated screenshot shouldn't need horizontal scrolling.

---

## 5. Done when

- [ ] "See it with sample data" is the first and most prominent action on Home.
- [ ] The sample-data banner shows on the analysis page, with a working link back to "Use your own statement".
- [ ] The checklist shows all four steps; the CAMS button opens in a new tab and Fundprint stays open.
- [ ] Field table and copy match this spec; the screenshot slot shows the image when the asset exists and is skipped cleanly when it doesn't.
- [ ] The "come back later" note shows the copyable page link.
- [ ] Returning flow works with no extra clicks: choose file → password → results.
- [ ] Each error case shows its message and points to the right step.
- [ ] Nothing is stored in the browser; the existing network/privacy checks still pass.
- [ ] Works on a phone (Android Chrome, iOS Safari).
