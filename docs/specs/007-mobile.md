# Fundprint: Mobile first tap

> **Status:** Implemented

On a phone the page looked ready, then froze when someone tapped **See it with sample data** or uploaded a statement.

Python in the browser runs on one thread. It cannot redraw, and it cannot take the next tap, while it is busy. The slow work was the first use of Matplotlib (its font cache), then drawing the charts, and, for a real file, reading the PDF. The loading note was removed as soon as the first widget appeared, so those taps happened while that work was still ahead. Doing the import at the bottom of Home made it worse: the buttons were already on screen.

## What the app does

1. **Before the first widget on Home**, load the chart code and draw one tiny figure. That builds the font cache while the loading note is still up. A later call does almost nothing. This touches no user data.
2. **The loading note** says the first load can take up to a minute on a phone, and to wait until the note is gone.
3. **Charts** are drawn under a spinner. A short pause at the start lets the spinner appear, and a short pause after each chart lets that chart appear before the next one is drawn. Chart downloads use 120 dpi.
4. **Reading a statement** uses the same short pause inside its spinner, before the PDF is opened.
5. **No SciPy in the browser.** The XIRR fallback is a small bracket search in `fundprint/xirr.py`. SciPy was only used there, and it is a large module on a phone. Tests still compare with pyxirr.

6. **Python starts without stack switching.** Pyodide uses WebAssembly stack switching whenever the browser offers it. Safari, and so every browser on an iPhone (Brave and Firefox included), offers it but fails the way Pyodide uses it: the first heavy run stopped Python with `SuspendError` and the page stayed greyed out. `boot.js` now starts Python through `web/pyodide-start.mjs`, which hides the feature first. Pyodide then takes its other path, the one it uses on Firefox. Checked in WebKit with iPhone emulation and in Chromium, for sample data and for a synthetic locked PDF.
7. **Quiet logs.** The browser build sets logging to DEBUG and sends every line to the page. `ui.quiet_logs()` keeps warnings and errors only, so Matplotlib and Pillow no longer send hundreds of lines per chart.

## Checks

- [ ] On a phone, wait until the loading note is gone, then tap **See it with sample data**. A spinner shows, then the charts appear. The page accepts another tap afterwards.
- [ ] Tap the upload box after the note is gone. The phone's file picker opens. After a password and **Show my results**, the "Reading your statement…" spinner shows before the charts.
- [ ] Desktop sample data and the XIRR tests still pass.
