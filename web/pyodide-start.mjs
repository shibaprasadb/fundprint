// Starts Python in the browser (Pyodide) with WebAssembly stack switching turned off.
// stlite loads this file inside its worker in place of pyodide.mjs.
//
// Pyodide uses stack switching whenever the browser offers it. Safari, and so every browser on an
// iPhone, offers it but cannot run the way Pyodide uses it: the first heavy run (sample data, or
// reading a statement) stops Python with "SuspendError" and the page stays greyed out for good.
// With the feature hidden, Pyodide uses its other path, the same one it uses on Firefox.
import { loadPyodide as startPyodide } from "./vendor/pyodide/pyodide.mjs";

export async function loadPyodide(options) {
  delete WebAssembly.Suspending;
  delete WebAssembly.Suspender;   // the older name for the same feature
  // stlite points Python at this file's folder; its files are in vendor/pyodide/
  return startPyodide({ ...options, indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
}
