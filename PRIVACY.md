# Privacy

**Nothing is stored. Your file is read and dropped when you close the tab.**

Fundprint runs entirely in your browser. Your statement is never uploaded to any server.

## The rules the code follows
- All reading and analysis happens in the browser. There is no backend.
- The file is handled in memory only. It is never written to disk.
- No caching of anything from your statement (caching is used only for public benchmark data).
- No `localStorage`, `sessionStorage`, IndexedDB or cookies holding statement data.
- No analytics, trackers, third-party fonts or external scripts.
- A Content-Security-Policy tag stops the page from sending data anywhere else.
- No network calls while you use the app, other than loading its own files.
- Error messages never show statement data.
- Your PDF password is used once to open the file, then dropped.
- No real statements in this repository; tests use made-up data only.

## Check it yourself
1. Open DevTools → Network, upload a statement, and watch: no requests go out after the app has loaded.
2. Read the Content-Security-Policy tag in the page source.
3. Read the code. There is no server code to hide anything in.

## What the browser build enforces
`web/index.html` carries a Content-Security-Policy tag with `connect-src 'self' blob: data:`. The browser blocks any request to another site, including from the Python worker. During testing the policy caught a CDN request we had missed, which is why Python, its packages and the wheels are now served from this site.

One note you may see in the console: the charts ask for an image at `stlite.invalid` first. That name can never resolve, and the policy blocks it; the chart is then drawn from an in-page `blob:` URL. Nothing is sent anywhere.
