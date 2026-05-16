/* S8 § 5.6 — Shared helpers for /c3a/* pages.
 *
 * Exports (attached to window for cross-page use AND to enable
 * the Phase-6 _test_harness.html flow-controller tests):
 *   - traceId()              — resolution per Finding 1 / R3.2
 *   - c3aFetch(url, opts)    — categorized error wrapper around fetch()
 *   - displayError(err, traceId, container)
 *   - handlePageFlow({apiCall, onSuccess, errorContainer, terminalSession})
 *   - handleTerminalRedirect(err, currentSession)
 *   - isTestMode()
 *   - deriveRequestId(briefToken)  (§ 5.2 R3.2)
 *
 * Hand-written; no framework. Every function is small, named,
 * testable. Pages may hand-roll if they have unique flow logic but
 * MUST justify deviation in code comments.
 */
(function (root) {
    "use strict";

    // ─── Constants ──────────────────────────────────────────────────
    var TRACE_RE = /^[0-9a-f]{16}$/;

    // ─── Test mode ──────────────────────────────────────────────────
    function isTestMode() {
        // Server-side injects <meta name="c3a-test-mode" content="1">
        // when C3A_TEST_MODE=1 (per § 5.6.1).
        var m = document.querySelector('meta[name="c3a-test-mode"]');
        return !!(m && m.getAttribute("content") === "1");
    }

    // ─── traceId (Finding 1 / R3.2) ─────────────────────────────────
    var _cachedTraceId = null;
    function traceId() {
        if (_cachedTraceId) return _cachedTraceId;
        // (1) ?trace=... query param
        var url = new URL(window.location.href);
        var fromUrl = url.searchParams.get("trace");
        if (fromUrl && TRACE_RE.test(fromUrl)) {
            _cachedTraceId = fromUrl;
            return _cachedTraceId;
        }
        // (2) mint a fresh 16-hex via crypto.getRandomValues
        _cachedTraceId = _mintTraceId();
        return _cachedTraceId;
    }

    function _mintTraceId() {
        var bytes = new Uint8Array(8);
        (root.crypto || root.msCrypto).getRandomValues(bytes);
        var out = "";
        for (var i = 0; i < bytes.length; i++) {
            var b = bytes[i].toString(16);
            if (b.length < 2) b = "0" + b;
            out += b;
        }
        return out;
    }

    // ─── deriveRequestId (§ 5.2 R3.2) ───────────────────────────────
    // Deterministic: same brief_token → same request_id → P21 cache hit
    // on browser refresh / link-preview-bot / concurrent open-in-new-tab.
    async function deriveRequestId(briefToken) {
        if (!briefToken) return "c3a-init-empty";
        var enc = new TextEncoder();
        var data = enc.encode(briefToken);
        var hash = await root.crypto.subtle.digest("SHA-256", data);
        var arr = new Uint8Array(hash);
        var hex = "";
        for (var i = 0; i < arr.length; i++) {
            var b = arr[i].toString(16);
            if (b.length < 2) b = "0" + b;
            hex += b;
        }
        return "c3a-init-" + hex.slice(0, 16);
    }

    // ─── c3aFetch (§ 5.6 + § 5.6.2 mapping table) ───────────────────
    async function c3aFetch(url, opts) {
        opts = opts || {};
        var method = opts.method || "GET";
        var headers = Object.assign({
            "X-Trace-Id": traceId(),
        }, opts.headers || {});

        var fetchOpts = { method: method, headers: headers };
        if (opts.body !== undefined && opts.body !== null) {
            if (typeof opts.body === "string") {
                fetchOpts.body = opts.body;
            } else {
                headers["Content-Type"] = "application/json";
                fetchOpts.body = JSON.stringify(opts.body);
            }
        }

        var response;
        try {
            response = await fetch(url, fetchOpts);
        } catch (netErr) {
            // Network / CORS error
            throw {
                type: "RETRYABLE",
                source: "network",
                message: "no connection",
                trace_id: traceId(),
            };
        }

        // 503 storage_busy — auto-retry once unless test mode disables
        if (response.status === 503) {
            var retryAfter = parseInt(
                response.headers.get("Retry-After") || "5", 10,
            );
            if (!isTestMode() && !opts._noRetry) {
                await _sleep(retryAfter * 1000);
                return c3aFetch(
                    url,
                    Object.assign({}, opts, { _noRetry: true }),
                );
            }
            var body503 = await _safeJson(response);
            throw {
                type: "RETRYABLE",
                source: "storage",
                retryAfter: retryAfter,
                trace_id: (body503 && body503.trace_id) || traceId(),
                body: body503,
            };
        }

        if (response.status >= 200 && response.status < 300) {
            // Bot-preview HTML path (Content-Type=text/html); pass body
            // back as text rather than JSON for callers that expect HTML.
            var ct = response.headers.get("Content-Type") || "";
            if (ct.indexOf("application/json") < 0) {
                return await response.text();
            }
            return await response.json();
        }

        var body = await _safeJson(response);

        // 404 unknown_token → TERMINAL
        if (response.status === 404) {
            throw {
                type: "TERMINAL",
                source: "unknown_token",
                trace_id: (body && body.trace_id) || traceId(),
                body: body,
            };
        }
        // 410 gone → TERMINAL
        if (response.status === 410) {
            throw {
                type: "TERMINAL",
                source: "gone",
                trace_id: (body && body.trace_id) || traceId(),
                body: body,
            };
        }
        // 4xx other (400, 401, 403, 422) → USER_FIXABLE
        if (response.status >= 400 && response.status < 500) {
            throw {
                type: "USER_FIXABLE",
                source: "validation",
                errors: (body && body.errors) || [],
                trace_id: (body && body.trace_id) || traceId(),
                body: body,
            };
        }
        // 5xx other than 503 → RETRYABLE
        throw {
            type: "RETRYABLE",
            source: "server",
            trace_id: (body && body.trace_id) || traceId(),
            body: body,
        };
    }

    function _safeJson(resp) {
        return resp.json().catch(function () { return null; });
    }
    function _sleep(ms) {
        return new Promise(function (r) { setTimeout(r, ms); });
    }

    // ─── displayError (§ 5.6) ───────────────────────────────────────
    function displayError(err, currentTraceId, container) {
        if (!container) return;
        container.innerHTML = "";
        var div = document.createElement("div");
        div.setAttribute("role", "alert");

        if (err.type === "RETRYABLE") {
            div.className = "c3a-warning";
            div.textContent = (err.source === "network")
                ? "We can't reach the server. Check your connection."
                : (err.source === "storage")
                    ? "The server is busy. Please retry in a moment."
                    : "Something went wrong on our side. Please retry.";
            var retry = document.createElement("button");
            retry.className = "c3a-secondary";
            retry.style.marginTop = "8px";
            retry.textContent = "Retry";
            retry.addEventListener("click", function () {
                window.location.reload();
            });
            div.appendChild(document.createElement("br"));
            div.appendChild(retry);
        } else if (err.type === "USER_FIXABLE") {
            div.className = "c3a-error";
            var head = document.createElement("strong");
            head.textContent = "Please correct and resubmit:";
            div.appendChild(head);
            var ul = document.createElement("ul");
            (err.errors || []).forEach(function (e) {
                var li = document.createElement("li");
                li.textContent = (e.field ? (e.field + ": ") : "")
                    + (e.message || e.code || "validation error");
                ul.appendChild(li);
            });
            div.appendChild(ul);
        } else {
            // TERMINAL fall-through (shouldn't normally hit displayError)
            div.className = "c3a-error";
            div.textContent = "This case is closed.";
        }

        var trace = document.createElement("p");
        trace.className = "c3a-trace";
        trace.textContent = "If you contact support, share this code: "
            + (currentTraceId || err.trace_id || traceId());
        div.appendChild(trace);

        container.appendChild(div);
    }

    // ─── handleTerminalRedirect (§ 5.6 R3.4) ────────────────────────
    function handleTerminalRedirect(err, currentSession) {
        currentSession = currentSession || "";
        if (err.source === "gone") {
            window.location.href = "/c3a/done.html?session="
                + encodeURIComponent(currentSession)
                + "&trace=" + encodeURIComponent(traceId());
        } else if (err.source === "unknown_token") {
            window.location.href = "/brief_form.html";
        } else {
            // Unknown TERMINAL source — fall back to error container
            // (render via displayError if a container is exposed).
            var ec = root.__c3aErrorContainer;
            if (ec) displayError(err, traceId(), ec);
        }
    }

    // ─── handlePageFlow (§ 5.6 controller) ──────────────────────────
    async function handlePageFlow(args) {
        var apiCall = args.apiCall;
        var onSuccess = args.onSuccess;
        var errorContainer = args.errorContainer;
        var currentSession = args.currentSession || "";
        root.__c3aErrorContainer = errorContainer;

        showLoadingUI();
        try {
            var resp = await apiCall();
            var nextUrl = onSuccess(resp);
            window.location.href = nextUrl;
        } catch (err) {
            hideLoadingUI();
            if (err.type === "TERMINAL") {
                handleTerminalRedirect(err, currentSession);
            } else {
                displayError(err, traceId(), errorContainer);
            }
        }
    }

    function showLoadingUI() {
        var el = document.querySelector("[data-c3a-loading]");
        if (el) el.classList.remove("c3a-hidden");
    }
    function hideLoadingUI() {
        var el = document.querySelector("[data-c3a-loading]");
        if (el) el.classList.add("c3a-hidden");
    }

    // ─── Export ─────────────────────────────────────────────────────
    var api = {
        traceId: traceId,
        c3aFetch: c3aFetch,
        displayError: displayError,
        handlePageFlow: handlePageFlow,
        handleTerminalRedirect: handleTerminalRedirect,
        isTestMode: isTestMode,
        deriveRequestId: deriveRequestId,
        _mintTraceId: _mintTraceId,
    };
    Object.keys(api).forEach(function (k) { root[k] = api[k]; });
    root.C3A = api;
})(typeof window !== "undefined" ? window : this);
