// Starts Streamlit inside the browser (stlite). Every file comes from this site.
// Log anything the security policy blocks, so a blocked outside request is visible in the console.
document.addEventListener("securitypolicyviolation", (e) =>
  console.warn("Blocked by security policy:", e.violatedDirective, e.blockedURI));

// Start-up has no time limit of its own: if one download stops arriving, the note would spin for good.
// So after a minute the note says so and offers a Reload button, and if start-up fails it says that
// plainly (spec 010). Messages are fixed text: nothing from an error, a file or the page goes in them.
const SLOW_AFTER_MS = 60_000;
const SLOW_TEXT = "This is taking longer than usual. A slow or busy connection can cause this.";
const FAILED_TEXT = "Fundprint could not finish loading. Check your connection and reload the page.";

function showNote(text, { spinner }) {
  const note = document.getElementById("loading-note");
  if (!note) return;
  note.replaceChildren();
  if (spinner) {
    const s = document.createElement("span");
    s.className = "spinner";
    note.append(s);
  }
  const words = document.createElement("span");
  words.textContent = text;
  const reload = document.createElement("button");
  reload.type = "button";
  reload.textContent = "Reload";
  reload.addEventListener("click", () => location.reload());   // the security policy blocks click handlers written in the HTML
  note.append(words, reload);
}

const slowTimer = setTimeout(() => showNote(SLOW_TEXT, { spinner: true }), SLOW_AFTER_MS);
let failed = false;
function fail() {
  if (failed) return;
  failed = true;
  clearTimeout(slowTimer);
  showNote(FAILED_TEXT, { spinner: false });
}

const here = (rel) => new URL(rel, location.href).href;

// Take the "first time load" note away once the app has drawn its first real element.
// While Python is still starting, the page only holds an empty box or grey placeholder bars.
const root = document.getElementById("root");
const isReal = (el) => el.childElementCount > 0 && !el.querySelector('[data-testid="stAppSkeleton"]');
const drawn = new MutationObserver(() => {
  if (failed) return;
  if ([...root.querySelectorAll('[data-testid="stMain"] [data-testid="stElementContainer"]')].some(isReal)) {
    document.getElementById("loading-note")?.remove();
    clearTimeout(slowTimer);
    drawn.disconnect();
  }
});
drawn.observe(root, { childList: true, subtree: true });

try {
  // Loaded here rather than with a top-level import, so a failed download reaches the catch below.
  const { mount } = await import("./vendor/stlite/stlite.js");
  const manifest = await (await fetch("./app-manifest.json")).json();
  const files = Object.fromEntries(
    manifest.files.map((p) => [p, { url: new URL(`./app/${p}`, location.href).href }]),
  );

  const app = mount(
    {
      entrypoint: "Home.py",
      files,
      // Python itself and its big packages come from our own site, not a CDN
      pyodideUrl: here("./pyodide-start.mjs"),   // works around an iPhone crash and retries stalled downloads
      // Everything is installed by name from ./vendor/pyodide/pyodide-lock.json, which also lists our
      // own pure-Python wheels. casparser lists no rapidfuzz there (it has no browser build);
      // rapidfuzz/ in the app is a small stand-in.
      requirements: ["casparser", "pydantic", "python-dateutil", "matplotlib", "sqlite3", "click",
                     "colorama", "rich", "cryptography", "charset-normalizer", "protobuf", "itsdangerous",
                     "python-multipart"],
      // stlite's own start-up error box shows the raw error, which for Python is a traceback (rule 8).
      // Our plain message below replaces it.
      disableErrorToasts: true,
      // Light theme with a white background by default, even when the device is set to dark mode
      streamlitConfig: { "client.showErrorDetails": "none", "client.toolbarMode": "minimal",
                         "theme.base": "light", "theme.backgroundColor": "#FFFFFF" },
    },
    root,
  );
  // _kernel is stlite's internal object; tests/test_app.py checks it is still there after an upgrade.
  app._kernel?.addEventListener("loadError", fail);
} catch {
  fail();
}
