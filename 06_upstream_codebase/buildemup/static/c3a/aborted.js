/* S8 § 5.4 — aborted.html controller (symmetric to done.js).
 *
 * Initial GET /status to verify the session was actually aborted.
 * If terminal_state is something other than USER_ABORTED, redirects
 * to /done. If not terminal, redirects back to /case.
 */
(async function () {
    "use strict";

    var url = new URL(window.location.href);
    var sessionToken = url.searchParams.get("session")
        || url.searchParams.get("token") || "";
    var abortedContainer = document.getElementById("aborted-container");
    var errorContainer = document.getElementById("error-container");
    var loadingEl = document.querySelector("[data-c3a-loading]");

    if (!sessionToken) {
        loadingEl.classList.add("c3a-hidden");
        window.displayError(
            { type: "USER_FIXABLE", source: "validation",
              errors: [{ field: "session", code: "missing",
                         message: "session query param required" }],
              trace_id: window.traceId() },
            window.traceId(), errorContainer);
        return;
    }

    try {
        var status = await window.c3aFetch(
            "/api/extreme-case/status?session_token="
                + encodeURIComponent(sessionToken));
        loadingEl.classList.add("c3a-hidden");

        if (!status.is_terminal) {
            window.location.href = "/c3a/case.html?session="
                + encodeURIComponent(sessionToken);
            return;
        }
        if (status.terminal_state !== "USER_ABORTED") {
            // Different terminal — show on done page instead
            window.location.href = "/c3a/done.html?session="
                + encodeURIComponent(sessionToken);
            return;
        }
        abortedContainer.classList.remove("c3a-hidden");
    } catch (err) {
        loadingEl.classList.add("c3a-hidden");
        window.displayError(err, window.traceId(), errorContainer);
    }
})();
