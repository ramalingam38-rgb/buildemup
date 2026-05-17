/* S8 § 5.2 — case.html controller.
 *
 * On load: GET /api/extreme-case/check-init with derived request_id;
 * render case + options. On submit: POST /resolve and redirect.
 */
(async function () {
    "use strict";

    var url = new URL(window.location.href);
    var briefToken = url.searchParams.get("brief") || "";
    var caseContainer = document.getElementById("case-container");
    var errorContainer = document.getElementById("error-container");
    var caseText = document.getElementById("case-text");
    var optionsList = document.getElementById("options-list");
    var sessionInput = document.getElementById("session-token");
    var loadingEl = document.querySelector("[data-c3a-loading]");

    if (!briefToken) {
        loadingEl.classList.add("c3a-hidden");
        window.displayError(
            { type: "USER_FIXABLE", source: "validation",
              errors: [{ field: "brief", code: "missing",
                         message: "brief query param required" }],
              trace_id: window.traceId() },
            window.traceId(),
            errorContainer,
        );
        return;
    }

    // Derive deterministic request_id per § 5.2 R3.2
    var requestId = await window.deriveRequestId(briefToken);

    var checkInitUrl = "/api/extreme-case/check-init?brief="
        + encodeURIComponent(briefToken)
        + "&request_id=" + encodeURIComponent(requestId);

    try {
        var resp = await window.c3aFetch(checkInitUrl);
        loadingEl.classList.add("c3a-hidden");

        if (!resp || !resp.session_token) {
            window.displayError(
                { type: "USER_FIXABLE", source: "validation",
                  errors: [{ code: "unexpected_response",
                             message: "missing session_token" }],
                  trace_id: window.traceId() },
                window.traceId(), errorContainer);
            return;
        }
        sessionInput.value = resp.session_token;

        // Render case + options. Tolerant of nested shapes:
        // resp.extreme_case OR resp.current_case OR top-level fields.
        var ec = resp.extreme_case || resp.current_case || resp;
        caseText.textContent = ec.user_facing_message
            || ec.case_text || ec.framing_line
            || "Please review and choose an option:";

        var options = (ec.options || []);
        if (options.length === 0) {
            // Already terminal (no case to surface)
            window.location.href = "/c3a/done.html?session="
                + encodeURIComponent(resp.session_token)
                + "&trace=" + encodeURIComponent(
                    resp.trace_id || window.traceId());
            return;
        }

        options.forEach(function (opt, i) {
            var label = document.createElement("label");
            label.className = "c3a-option";
            var radio = document.createElement("input");
            radio.type = "radio";
            radio.name = "option_id";
            radio.value = opt.option_id || ("opt-" + i);
            if (i === 0) radio.checked = true;
            label.appendChild(radio);
            label.appendChild(document.createTextNode(
                " " + (opt.description || opt.option_id || "Option")));
            optionsList.appendChild(label);
        });

        // B-057: visible trace_id on success render for support reference
        var caseTrace = document.getElementById("case-trace");
        if (caseTrace) {
            caseTrace.textContent = "Trace ID: "
                + (resp.trace_id || window.traceId());
        }

        caseContainer.classList.remove("c3a-hidden");
    } catch (err) {
        loadingEl.classList.add("c3a-hidden");
        if (err.type === "TERMINAL") {
            window.handleTerminalRedirect(err, "");
        } else {
            window.displayError(err, window.traceId(), errorContainer);
        }
    }

    // ─── Resolve submit ─────────────────────────────────────────────
    document.getElementById("case-form").addEventListener(
        "submit", function (ev) {
            ev.preventDefault();
            var sessionToken = sessionInput.value;
            var selected = document.querySelector(
                'input[name="option_id"]:checked');
            if (!sessionToken || !selected) return;
            var resolveReqId = "c3a-resolve-" + window._mintTraceId();
            window.handlePageFlow({
                apiCall: function () {
                    return window.c3aFetch(
                        "/api/extreme-case/resolve",
                        { method: "POST", body: {
                            session_token: sessionToken,
                            request_id: resolveReqId,
                            chosen_option_id: selected.value,
                        }},
                    );
                },
                onSuccess: function (resp) {
                    var trace = resp.trace_id || window.traceId();
                    if (resp.is_terminal || resp.terminal_state) {
                        return "/c3a/done.html?session="
                            + encodeURIComponent(sessionToken)
                            + "&trace=" + encodeURIComponent(trace);
                    }
                    return "/c3a/checklist.html?session="
                        + encodeURIComponent(sessionToken)
                        + "&trace=" + encodeURIComponent(trace);
                },
                errorContainer: errorContainer,
                currentSession: sessionToken,
            });
        });

    // ─── Abort button ───────────────────────────────────────────────
    document.getElementById("abort-btn").addEventListener(
        "click", function () {
            var sessionToken = sessionInput.value;
            if (!sessionToken) return;
            var abortReqId = "c3a-abort-" + window._mintTraceId();
            window.handlePageFlow({
                apiCall: function () {
                    return window.c3aFetch(
                        "/api/extreme-case/abort",
                        { method: "POST", body: {
                            session_token: sessionToken,
                            request_id: abortReqId,
                        }},
                    );
                },
                onSuccess: function () {
                    return "/c3a/aborted.html?session="
                        + encodeURIComponent(sessionToken)
                        + "&trace=" + encodeURIComponent(window.traceId());
                },
                errorContainer: errorContainer,
                currentSession: sessionToken,
            });
        });
})();
