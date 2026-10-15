# Fundprint: Feedback link

> **Status:** Implemented
> **Notes:** The `click:feedback` event and its filter are in `web/feedback.js`; the button is in `web/index.html` and the footer link in `app/ui.py`.

Add a link to the beta feedback form on every page. The form is already built and hosted on Tally:

**Form URL:** `https://tally.so/r/2EqQGg`

All existing privacy rules still apply. The app itself never submits anything: the link opens the external form in a new tab, and the tester types there.

---

## 1. Where the link appears

### A. Floating button, top right (always visible)
- A small, fixed-position button in the **top-right corner** of every page, with the text **"Feedback"**.
- Put it in **`index.html`** (the page that mounts stlite) as a plain `<a href="https://tally.so/r/2EqQGg" target="_blank" rel="noopener noreferrer">`, so it sits outside the Streamlit app and stays visible while scrolling.
- Style: small pill shape, the app's accent colour, white text, a soft shadow, high `z-index`. It must not cover Streamlit's own top-right menu: offset it below that menu or to its left.
- On phones it stays in the top right, at a smaller size.

### B. Footer link (every page)
- Add **"Feedback"** to the existing footer line, linking to the same URL in a new tab.

### Link format
- Use the URL exactly as above. Don't add query parameters or anything derived from the statement.

---

## 2. Umami

Add **one** event to the allowlist and to `fundprintBeforeSend`:

| Event | Fired when |
|---|---|
| `click:feedback` | Either feedback link (floating button or footer) clicked |

No event data, as with all other events.

---

## 3. CSP

No change. The form opens in a new tab as a normal link, not an embed, so nothing new is needed in `connect-src` or `frame-src`.

---

## 4. Must not

- No embedded form or iframe, and no in-app submission.
- No prefilled fields with statement data, error text, fund names or results.
- No feedback state stored in the browser.

---

## 5. Done when

- [ ] The "Feedback" button shows in the top-right corner on every page, on desktop and mobile, without covering Streamlit's menu.
- [ ] The footer shows a "Feedback" link.
- [ ] Both open `https://tally.so/r/2EqQGg` in a new tab; Fundprint stays open.
- [ ] Clicking either sends only `click:feedback` to Umami.
- [ ] The network check still passes: after load, requests go only to the app's own domain and the Umami host.
