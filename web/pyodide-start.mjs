// Starts Python in the browser (Pyodide) with WebAssembly stack switching turned off, and makes
// start-up downloads that stall try again. stlite loads this file inside its worker in place of
// pyodide.mjs.
//
// Pyodide uses stack switching whenever the browser offers it. Safari, and so every browser on an
// iPhone, offers it but cannot run the way Pyodide uses it: the first heavy run (sample data, or
// reading a statement) stops Python with "SuspendError" and the page stays greyed out for good.
// With the feature hidden, Pyodide uses its other path, the same one it uses on Firefox.
import { loadPyodide as startPyodide } from "./vendor/pyodide/pyodide.mjs";

// Stalled downloads (spec 010). A browser never gives up on a download that is connected but gets no
// more data, so one stuck file used to stop start-up for good. Every download from this site made in
// this worker (Python, its packages, the app's wheels) now goes through retryingFetch: if no new data
// arrives for 20 seconds it starts that file again, twice at most, then tries once more with no time
// limit. A slow download that keeps arriving is never cut off.
const SITE = new URL(import.meta.url).origin;
const STALL_MS = 20_000;
const TIMED_TRIES = 2;
const browserFetch = globalThis.fetch.bind(globalThis);

// Pyodide asks for each package with its SHA-256 ("integrity"). With that set, the browser holds the
// whole file back until it has all arrived, so a stall can't be told apart from a slow download.
// So the file is fetched without it and the same check is made here once it has arrived.
async function sameHash(bytes, integrity) {
  const [kind, expected] = integrity.trim().split(/-(.*)/s);
  if (kind !== "sha256") return false;   // Pyodide's lock file only uses sha256
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return btoa(String.fromCharCode(...digest)) === expected;
}

async function fetchOnce(url, init, integrity, timed) {
  const stop = new AbortController();
  let timer;
  const wait = () => {
    clearTimeout(timer);
    if (timed) timer = setTimeout(() => stop.abort(), STALL_MS);
  };
  wait();
  try {
    const res = await browserFetch(url, { ...init, signal: stop.signal });
    if (!res.ok || !res.body) return res;   // a 404 and the like are passed on as they are
    const reader = res.body.getReader();
    const parts = [];
    let size = 0;
    for (;;) {
      wait();
      const { done, value } = await reader.read();
      if (done) break;
      parts.push(value);
      size += value.length;
    }
    const bytes = new Uint8Array(size);
    let at = 0;
    for (const p of parts) { bytes.set(p, at); at += p.length; }
    if (integrity && !(await sameHash(bytes, integrity))) throw new TypeError("checksum mismatch");
    const copy = new Response(bytes, { status: res.status, statusText: res.statusText, headers: res.headers });
    Object.defineProperty(copy, "url", { value: res.url });
    return copy;
  } finally {
    clearTimeout(timer);
  }
}

async function retryingFetch(input, init = {}) {
  const url = typeof input === "string" || input instanceof URL ? new URL(input, SITE) : null;
  const method = (init.method || "GET").toUpperCase();
  if (!url || url.origin !== SITE || method !== "GET" || init.signal) return browserFetch(input, init);
  const { integrity, ...rest } = init;
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetchOnce(url.href, rest, integrity, attempt < TIMED_TRIES);
    } catch (e) {
      if (attempt >= TIMED_TRIES) throw e;   // the untimed last try failed too: let start-up report it
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
}
globalThis.fetch = retryingFetch;

export async function loadPyodide(options) {
  delete WebAssembly.Suspending;
  delete WebAssembly.Suspender;   // the older name for the same feature
  // stlite points Python at this file's folder; its files are in vendor/pyodide/
  return startPyodide({ ...options, indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
}
