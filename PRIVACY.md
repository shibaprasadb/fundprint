# Privacy

**Nothing is stored. Your file is read and dropped when you close the tab.**

Fundprint runs entirely in your browser. Your statement is never uploaded to any server.

## The rules the code follows
- All reading and analysis happens in the browser. There is no backend.
- The file is handled in memory only. It is never written to disk.
- No caching of anything from your statement (caching is used only for public benchmark data).
- No `localStorage`, `sessionStorage`, IndexedDB or cookies holding statement data.
- No scripts, fonts or trackers are loaded from other sites. Anonymous visit counts are sent to Umami by a small script served from this site (see Analytics below).
- A Content-Security-Policy tag stops the page from sending data anywhere except this site and Umami.
- No network calls while you use the app, other than loading its own files and those anonymous counts.
- Error messages never show statement data.
- Your PDF password is used once to open the file, then dropped.
- No real statements in this repository; tests use made-up data only.

## Check it yourself
1. Open DevTools → Network, upload a statement, and watch: after the app has loaded, the only requests that leave this site are small ones to `gateway.umami.is`. Click one to see what it holds: the page address, never your file.
2. Read the Content-Security-Policy tag in the page source.
3. Read the code. There is no server code to hide anything in.

## What the browser build enforces
`web/index.html` carries a Content-Security-Policy tag with `connect-src 'self' blob: data: https://gateway.umami.is`. The browser blocks any request to any other site, including from the Python worker. During testing the policy caught a CDN request we had missed, which is why Python, its packages and the wheels are now served from this site.

One note you may see in the console: the charts ask for an image at `stlite.invalid` first. That name can never resolve, and the policy blocks it; the chart is then drawn from an in-page `blob:` URL. Nothing is sent anywhere.

## Analytics
Fundprint uses [Umami](https://umami.is), a privacy-friendly visit counter, to see how many people visit. It sets no cookies and collects no personal data.

What is sent: a page view when you open a page (the page address and title, plus Umami's standard fields: screen size, browser language and the page you came from). Button clicks are not tracked.

What is never sent: anything from your statement. The counter is a small script kept in this repository (`web/umami.js`) and served from this site, so it cannot change unless this code changes. Like any script on the page it runs alongside the upload box, which is why we keep a fixed copy that anyone can read, and do not load it from another site.

To check: in DevTools → Network, the only requests to another site are the small page-view requests to `gateway.umami.is`.
