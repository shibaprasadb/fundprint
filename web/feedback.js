// Feedback link counting, the Umami filter, and starting Umami.
// Clicking a link to the feedback form counts one anonymous event: no extra details.
// Umami calls fundprintBeforeSend before every send; only the events listed here may leave the page.
// This file is the only thing that loads umami.js, and only after the filter exists. If this file
// fails to load, Umami never starts, so nothing can be sent without the filter.
(function () {
  "use strict";
  var FORM_URL = "https://tally.so/r/2EqQGg";
  var ALLOWED_EVENTS = ["click:feedback"];

  // Page views (no event name) pass. Named events pass only if listed above, and never carry data.
  // Anything else (identify, performance and so on) is dropped.
  window.fundprintBeforeSend = function (type, payload) {
    if (type !== "event" || !payload) return null;
    if (!payload.name) return payload;
    if (ALLOWED_EVENTS.indexOf(payload.name) === -1) return null;
    delete payload.data;
    return payload;
  };

  // One listener covers the floating button and the footer link (the footer is drawn later by the app).
  document.addEventListener("click", function (e) {
    var link = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!link || link.getAttribute("href") !== FORM_URL) return;
    if (window.umami && typeof window.umami.track === "function") window.umami.track("click:feedback");
  }, true);

  // Start Umami now that the filter is in place. umami.js sits next to this file.
  var umami = document.createElement("script");
  umami.src = new URL("umami.js", document.currentScript.src).href;
  umami.setAttribute("data-website-id", "2e67cd5c-f499-4fba-a139-481c5adb30c4");
  umami.setAttribute("data-domains", "lab.shibaprasadb.com");
  umami.setAttribute("data-before-send", "fundprintBeforeSend");
  document.head.appendChild(umami);
})();
