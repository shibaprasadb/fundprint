// Feedback link counting and the Umami filter.
// Clicking a link to the feedback form counts one anonymous event: no extra details.
// Umami calls fundprintBeforeSend before every send; only the events listed here may leave the page.
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
})();
