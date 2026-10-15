# Fundprint: Add Umami analytics

> **Status:** Partly implemented
> **Notes:** Only the visit counter (page views) and one event, `click:feedback`, are live. The 11-event click allowlist, the `data-tag` and clean-URL settings, and the footer line are not built. The counter is a fixed copy in `web/umami.js` (not loaded from the Umami host), and the filter lives in `web/feedback.js`, not `index.html`. `feedback.js` also loads `umami.js` itself, after the filter is set up, so the counter never runs without the filter (§2's script tag is not used).

A small add-on task for the live app at `lab.shibaprasadb.com/fundprint`. The rest of the app is already built; change only what this file describes.

**Goal:** see which pages and buttons people use. Nothing more.

**Ground rule:** analytics must never carry anything from a user's statement. The privacy promise stays exactly as it is:

> **Nothing is stored. Your file is read and dropped when you close the tab.**

---

## 1. Umami setup (manual, done by the maintainer)

- Reuse the **existing Umami website** already used for shibaprasadb.com (the free plan allows only one website). Use its **website ID** and **Umami host URL** as `<website-id>` and `<umami-host>` below.
- Lab traffic is kept apart from the main site in two ways:
  - every lab event is tagged `lab` via `data-tag="lab"`, so the dashboard can be filtered to lab only;
  - all lab pages and events sit under the `lab.shibaprasadb.com` hostname, which Umami can also filter on.
- Do **not** change anything in the main site's Umami setup.

---

## 2. Load the tracker in `index.html`, not in Python

stlite runs Python in a **web worker**, which has no access to `window` or `window.umami`. So all tracking must be plain JavaScript on the main HTML page that mounts the app.

Add this to the `<head>` of the page that mounts stlite. The `fundprintBeforeSend` function must be defined **before** the Umami script tag (see §4):

```html
<script defer
  src="<umami-host>/script.js"
  data-website-id="<website-id>"
  data-domains="lab.shibaprasadb.com"
  data-tag="lab"
  data-exclude-search="true"
  data-exclude-hash="true"
  data-before-send="fundprintBeforeSend"></script>
```

| Attribute | Why |
|---|---|
| `data-domains` | Only tracks on the live site, not on localhost or preview builds. |
| `data-tag` | Marks every lab event as `lab`, so lab traffic can be separated from the main site in the shared dashboard. |
| `data-exclude-search`, `data-exclude-hash` | Keeps URLs clean; nothing extra rides along in the address. |
| `data-before-send` | Safety filter (§4). |

---

## 3. What gets tracked

### Page views
- Umami tracks the first page view automatically.
- If switching pages inside the app **does not change the URL** (check this in the live app), send a page event when a sidebar page link is clicked instead, e.g. `umami.track('page:time-in-market')`.

### Clicks: one listener, fixed allowlist
Add a single click listener on `document`. On each click:
1. Find the nearest clicked `button`, `a`, `summary`, or element with `role="button"` / `role="tab"`.
2. Read its **visible label** (trimmed `innerText`).
3. If the label matches an entry in the allowlist below, send the mapped event name with `umami.track(name)`. **Otherwise, do nothing.**

Never send the label itself. Only send the fixed event name from the table.

### Event allowlist (v1)

Adjust the "label" column to match the exact text in the live app.

| Event name | Label it matches | Fired when |
|---|---|---|
| `page:home` | Home page link | Home page viewed |
| `page:time-in-market` | Analysis page link | Analysis page viewed |
| `click:try-sample` | "Try with sample data" | Sample data used |
| `click:upload` | Upload button / "Browse files" | Upload box used |
| `click:how-to-get-cas` | CAS instructions expander | Instructions opened |
| `click:how-calculated` | "How this is calculated" expander | Method opened |
| `click:scope-equity` | "Equity only" | Scope switched to equity |
| `click:scope-all` | "All funds" | Scope switched to all |
| `click:download-chart` | Chart download button(s) | A chart downloaded |
| `click:repo-link` | Footer repo link | GitHub link clicked |
| `click:shibaprasadb` | Footer "shibaprasadb.com" link | Site link clicked |

Keep the allowlist as **one constant** in the JS (a simple object of `label → event name`), so adding an event later is a one-line change.

---

## 4. Hard rules

1. **No event data.** Only ever call `umami.track(name)`. Never `umami.track(name, {...})`.
2. **Nothing derived from the statement**, ever. No file name, size or type, no fund names, no number of funds, no percentages or XIRR values, no success/failure of parsing, no error text.
3. **Safety filter.** Define this before the Umami script loads:
   ```js
   // Drops any event that isn't on the allowlist, and strips any extra data.
   // This protects the privacy promise even if someone later adds a careless event.
   window.fundprintBeforeSend = function (type, payload) {
     const allowed = new Set(Object.values(FUNDPRINT_EVENTS)); // same constant as §3
     if (type === 'event') {
       if (!payload.name || !allowed.has(payload.name)) return false;
       delete payload.data;
     }
     return payload;
   };
   ```
   (Plain page views have no `name` and pass through. Check the payload shape against the Umami version in use and adjust if needed.)
4. **No visitor IDs.** Never use `data-distinct-id` or `umami.identify()`.
5. **No heatmaps, session replay, scroll tracking or performance tracking.**
6. **No other trackers.** Umami is the only external service the page may talk to.

---

## 5. Changes to existing parts of the app

### Content-Security-Policy
Update the existing CSP `<meta>` tag to allow the Umami host, and nothing else new:
- `script-src 'self' <umami-host>`
- `connect-src 'self' <umami-host>`

Keep everything else as it is.

### Privacy text in the app
Keep the promise line word for word. Update the sentence under it so it stays true:

> Fundprint runs entirely in your browser. Your statement is never uploaded to any server.
> Don't take our word for it: the [code is open source](<repo link>), and you can open your browser's Network tab to check that your file is never sent anywhere.
> This page counts anonymous visits and button clicks with [Umami](https://umami.is) (no cookies, no personal data). That's the only thing it sends, and it never includes anything from your statement.

Also add a short line to the footer: *"Anonymous usage counts via Umami. No cookies."*

### PRIVACY.md and README
Add a short "Analytics" section saying:
- what Umami is and why it's used (to see which features people use);
- the exact event list from §3;
- that no statement data, file details or results are ever sent;
- how to verify: Network tab shows only small requests to `<umami-host>`.

### Release checklist / tests
Replace "zero network requests after load" with:
- After the app loads, **every** network request goes either to the app's own domain or to `<umami-host>`.
- Every Umami request contains only an allowlisted event name (or a plain page view) and Umami's standard fields.
- If a Playwright test exists for the network check, update it to assert the above instead of "no requests".

---

## 6. Done when

- [ ] Lab events appear in the existing Umami dashboard, and filtering by tag `lab` (or hostname `lab.shibaprasadb.com`) shows only lab traffic.
- [ ] No tracking fires on localhost.
- [ ] Clicking each allowlisted button sends exactly its event name; clicking anything else sends nothing.
- [ ] Uploading a synthetic CAS and running every page sends no event containing statement-related information.
- [ ] The CSP allows only `'self'` and `<umami-host>`.
- [ ] Privacy text, footer, PRIVACY.md and README updated.
