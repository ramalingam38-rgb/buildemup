/* S8 § 5.4 — done.html controller.
 *
 * Initial GET /status to verify session is actually terminal. Renders
 * terminal_state-specific success message; redirects to /aborted or
 * /case as appropriate.
 */
(async function () {
    "use strict";

    var url = new URL(window.location.href);
    var sessionToken = url.searchParams.get("session")
        || url.searchParams.get("token") || "";
    var doneContainer = document.getElementById("done-container");
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
            // Not actually done — bounce back to case page
            window.location.href = "/c3a/case.html?session="
                + encodeURIComponent(sessionToken);
            return;
        }
        if (status.terminal_state === "USER_ABORTED") {
            window.location.href = "/c3a/aborted.html?session="
                + encodeURIComponent(sessionToken);
            return;
        }

        var label = document.getElementById("terminal-label");
        label.textContent = status.terminal_state || "RESOLVED";
        var successLine = document.getElementById("success-line");
        if (status.terminal_state === "CBA_VERIFICATION_PAUSED"
            || status.terminal_state === "CBA_VERIFIED") {
            successLine.textContent =
                "CBA verification recorded. Your design will continue.";
        } else if (status.terminal_state === "PREVIEW_MODE") {
            successLine.textContent =
                "Preview mode confirmed. You can refine the brief later.";
        } else if (status.terminal_state === "MAX_ITERATIONS_REACHED") {
            successLine.textContent =
                "Limits reached. Please review your brief and resubmit.";
        } else {
            successLine.textContent = "Your case has been resolved.";
        }
        doneContainer.classList.remove("c3a-hidden");
    } catch (err) {
        loadingEl.classList.add("c3a-hidden");
        if (err.type === "TERMINAL" && err.source === "unknown_token") {
            // Show "session not found" without redirecting to brief form
            window.displayError(
                { type: "USER_FIXABLE", source: "validation",
                  errors: [{ code: "unknown_token",
                             message: "session not found" }],
                  trace_id: window.traceId() },
                window.traceId(), errorContainer);
        } else {
            window.displayError(err, window.traceId(), errorContainer);
        }
    }
})();
