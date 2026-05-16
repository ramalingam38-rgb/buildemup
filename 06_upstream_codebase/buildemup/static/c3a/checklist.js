/* S8 § 5.3 — checklist.html controller.
 *
 * On load: GET /status FIRST. If terminal, redirect to /done. Else
 * render checklist. On submit: POST /cba-verified with X-Trace-Id
 * from URL (carried across the 24h gap per Finding 1).
 */
(async function () {
    "use strict";

    var url = new URL(window.location.href);
    var sessionToken = url.searchParams.get("session")
        || url.searchParams.get("token") || "";
    var checklistContainer = document.getElementById("checklist-container");
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

    // GET /status FIRST per § 5.3 + External Item 2
    try {
        var status = await window.c3aFetch(
            "/api/extreme-case/status?session_token="
                + encodeURIComponent(sessionToken));
        if (status.is_terminal) {
            window.location.href = "/c3a/done.html?session="
                + encodeURIComponent(sessionToken)
                + "&trace=" + encodeURIComponent(window.traceId());
            return;
        }
        loadingEl.classList.add("c3a-hidden");
        checklistContainer.classList.remove("c3a-hidden");
    } catch (err) {
        loadingEl.classList.add("c3a-hidden");
        if (err.type === "TERMINAL") {
            window.handleTerminalRedirect(err, sessionToken);
        } else {
            window.displayError(err, window.traceId(), errorContainer);
        }
        return;
    }

    // ─── Confirm submit ─────────────────────────────────────────────
    document.getElementById("cba-form").addEventListener(
        "submit", function (ev) {
            ev.preventDefault();
            var requestId = "c3a-cba-" + window._mintTraceId();
            window.handlePageFlow({
                apiCall: function () {
                    return window.c3aFetch(
                        "/api/extreme-case/cba-verified",
                        { method: "POST", body: {
                            session_token: sessionToken,
                            request_id: requestId,
                            verified: true,
                        }},
                    );
                },
                onSuccess: function () {
                    return "/c3a/done.html?session="
                        + encodeURIComponent(sessionToken)
                        + "&trace=" + encodeURIComponent(window.traceId());
                },
                errorContainer: errorContainer,
                currentSession: sessionToken,
            });
        });
})();
