// Starts Streamlit inside the browser (stlite). Every file comes from this site.
// Log anything the security policy blocks, so a blocked outside request is visible in the console.
document.addEventListener("securitypolicyviolation", (e) =>
  console.warn("Blocked by security policy:", e.violatedDirective, e.blockedURI));

import { mount } from "./vendor/stlite/stlite.js";

const manifest = await (await fetch("./app-manifest.json")).json();
const files = Object.fromEntries(
  manifest.files.map((p) => [p, { url: new URL(`./app/${p}`, location.href).href }]),
);

const here = (rel) => new URL(rel, location.href).href;

mount(
  {
    entrypoint: "Home.py",
    files,
    // Python itself and its big packages come from our own site, not a CDN
    pyodideUrl: here("./vendor/pyodide/pyodide.mjs"),
    // Everything is installed by name from ./vendor/pyodide/pyodide-lock.json, which also lists our
    // own pure-Python wheels. casparser lists no rapidfuzz there (it has no browser build);
    // rapidfuzz/ in the app is a small stand-in.
    requirements: ["casparser", "pydantic", "python-dateutil", "scipy", "matplotlib", "sqlite3", "click",
                   "colorama", "rich", "cryptography", "charset-normalizer", "protobuf", "itsdangerous",
                   "python-multipart"],
    streamlitConfig: { "client.showErrorDetails": "none", "client.toolbarMode": "minimal" },
  },
  document.getElementById("root"),
);
