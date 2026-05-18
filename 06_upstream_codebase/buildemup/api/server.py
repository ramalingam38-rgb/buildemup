"""
BuildemUp† — Minimal standalone HTTP server (S7a + S7b).

Uses Python's stdlib http.server. Zero framework dependencies — works
on Railway with just Python 3.10+. Suitable for local dev and initial
deployment. Swap to Flask/FastAPI later if needed.

USAGE:
  python -m buildemup.api.server            # port 8000 by default
  PORT=8080 python -m buildemup.api.server  # or with env var

ROUTES:
  GET  /                                       → redirect to /brief_form.html
  GET  /brief_form.html|js|css                 → static
  GET  /orchestrator_run.html|js               → S59 orchestrator-results UI
  GET  /quote_compare.html|js                  → S59 quote-upload UI
  GET  /api/vastu/partial-items                → 7 partial vastu items
  GET  /api/brief/resume?token=...             → resume saved brief
  GET  /health                                 → S7b § 8.4 health probe
  POST /api/brief/capture                      → C1 capture
  POST /api/brief/save                         → C1 save (returns resume URL)
  POST /api/feasibility/run                    → C2 feasibility
  POST /api/orchestrate                        → S59 master orchestrator (full 18-phase chain)
  POST /api/quote/compare                      → S59 C17 quote-comparison (#9)
  POST /api/setback/preview                    → setback preview
  POST /api/extreme-case/check                 → C3a § 5.1
  POST /api/extreme-case/resolve               → C3a § 5.2
  POST /api/extreme-case/abort                 → C3a § 5.3
  POST /api/extreme-case/cba-verified          → C3a § 5.4
  POST /api/extreme-case/cba-fallback-continue → C3a § 5.5 (P34: passes headers)
  POST /admin/scheduler/tick                   → S7b § 7.4 cron-driven tick
  POST /admin/scheduler/reset                  → S7b § 7.5 stuck-row reset

S7b additions (Phase 8 wiring):
  - GET  /health                                       (handle_health)
  - POST /admin/scheduler/tick                         (handle_scheduler_tick)
  - POST /admin/scheduler/reset                        (handle_scheduler_reset)
  - cba-fallback-continue now passes inbound headers   (P34 X-Trace-Id)
  - 3-tuple response support: handlers can return
    (status, body, extra_headers) for the new 503 storage_busy path
    (§ 6.2). Legacy 2-tuple returns continue to work unchanged.
  - _validate_config() called from run_server() before binding the
    socket; in BUILDEMUP_ENV=prod, validation failures sys.exit(1)
    (§ 9.7 / P32).

†= placeholder name marker.
"""
from __future__ import annotations
import json
import logging
import os
import sqlite3
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from buildemup.api.brief_endpoint import (
    handle_brief_capture, handle_vastu_partial_items,
    handle_brief_save, handle_brief_resume,
)
from buildemup.api.feasibility_endpoint import (
    handle_feasibility_run,
)
from buildemup.api.orchestrate_endpoint import (
    handle_orchestrate,
)
from buildemup.api.quote_endpoint import (
    handle_quote_compare,
)
from buildemup.api.setback_preview_endpoint import (
    handle_setback_preview,
)
from buildemup.api.c3a_endpoint import (
    handle_check as handle_c3a_check,
    handle_resolve as handle_c3a_resolve,
    handle_abort as handle_c3a_abort,
    handle_cba_verified as handle_c3a_cba_verified,
    handle_cba_fallback_continue as handle_c3a_cba_fallback_continue,
)
from buildemup.api.c3a_status_endpoint import (
    handle_status as handle_c3a_status,
)
from buildemup.api.c3a_check_init_endpoint import (
    handle_check_init as handle_c3a_check_init,
)
from buildemup.api.admin_endpoint import (
    handle_scheduler_tick,
    handle_scheduler_reset,
)
from buildemup.api.health_endpoint import handle_health


LOGGER = logging.getLogger(__name__)


STATIC_DIR = Path(__file__).parent.parent / "static"
_STATIC_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
}


def _inject_test_mode_meta(html_bytes: bytes) -> bytes:
    """S8 § 5.6.1 — Inject ``<meta name="c3a-test-mode" content="1">``
    into HTML responses for /c3a/* requests when ``C3A_TEST_MODE=1``.

    The meta tag surfaces the env var to the static JS layer, where
    ``_shared.js isTestMode()`` reads it (browsers can't read env
    vars directly). When the flag is true, ``c3aFetch`` disables its
    503 auto-retry — necessary for tests to deterministically observe
    the 503 path (per External Item 3 / P36).

    Idempotent: if the meta tag is already present (e.g.,
    ``_test_harness.html`` has it hardcoded), no duplicate is added.

    Defensive: if the document has no ``<head>`` tag (shouldn't happen
    for our pages), return content unchanged rather than corrupt it.
    """
    if b'name="c3a-test-mode"' in html_bytes:
        return html_bytes
    needle = b"<head>"
    pos = html_bytes.find(needle)
    if pos == -1:
        return html_bytes
    inject_at = pos + len(needle)
    meta = b'\n    <meta name="c3a-test-mode" content="1">'
    return html_bytes[:inject_at] + meta + html_bytes[inject_at:]


# ─────────────────────────────────────────────────────────────────────
# B-064 — static asset hardening (CSP + Cache-Control + nosniff)
# ─────────────────────────────────────────────────────────────────────

# Conservative CSP for our static UI surface. The C1 brief form and
# C3a case/done/resume pages all run their own JS + own CSS only; no
# third-party scripts, no inline event handlers, no remote XHR.
#
# We allow 'unsafe-inline' for styles because some pages emit small
# inline <style> blocks for severity badges / banner colors. Inline
# scripts are NOT permitted — anything that needs to run must live in
# a .js file under /static/.
_STATIC_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self' data:; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

# Cache-Control policy per content type. HTML revalidates every
# request (so deploys are picked up immediately); JS/CSS get a short
# revalidation window (5 min) so a CDN layer can later slot in cleanly
# without serving stale code through a deploy. Anything else gets a
# conservative no-store.
_STATIC_CACHE_CONTROL = {
    ".html": "no-cache, must-revalidate",
    ".js":   "public, max-age=300, must-revalidate",
    ".css":  "public, max-age=300, must-revalidate",
}


def _static_security_headers(ext: str) -> dict[str, str]:
    """B-064 — return the security/cache headers for a static asset.

    Kept module-level for testability: tests can assert exact header
    values without spinning up an HTTPServer.
    """
    return {
        "Content-Security-Policy": _STATIC_CSP,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": _STATIC_CACHE_CONTROL.get(ext, "no-store"),
    }


# ─────────────────────────────────────────────────────────────────────
# § 9.7 / P32 — Startup config validation
# ─────────────────────────────────────────────────────────────────────
_PROD_REQUIRED = (
    "RESEND_API_KEY",
    "BUILDEMUP_DATABASE_PATH",
    "BUILDEMUP_ADMIN_TOKEN",
    # S8 § 9.3 / round 2 X9 — required for c3a_email_hook to construct
    # absolute cba-checklist URLs that survive the 24h pause-time gap.
    # Forgetting this var = deploy failure (sys.exit(1)), NOT silently
    # broken email links. Defaults to http://localhost:8000 in dev.
    "BUILDEMUP_PUBLIC_URL",
)

_MIN_LENGTHS = {
    "RESEND_API_KEY": 10,
    "BUILDEMUP_ADMIN_TOKEN": 16,
}

_MIN_SQLITE = (3, 35, 0)


def _validate_config() -> None:
    """Validate runtime config at startup. Spec § 9.7 + P32.

    In BUILDEMUP_ENV=prod, any failure logs ERROR and sys.exit(1) —
    Railway marks the deploy failed and routes no traffic. In any
    other env (dev / test / unset), failures log WARNING and the
    server continues — local development should not require a Resend
    key or production-strength admin token.

    Checks:
      1. Presence of required env vars.
      2. Min-length of values that are secrets/tokens.
      3. Writability of the DB path's parent directory (try-write +
         delete a sentinel file).
      4. SQLite version >= 3.35.0 (UPDATE...RETURNING is required by
         the scheduler atomic claim, P28).
      5. B-062 cross-check: BUILDEMUP_ENV=prod + C3A_TEST_MODE=1 is
         a forbidden combination. The test-mode flag exposes
         /c3a/_test_harness.html and bypasses the c3aFetch 503
         auto-retry — both unacceptable for real traffic.
    """
    env = os.environ.get("BUILDEMUP_ENV", "dev").lower()
    is_prod = (env == "prod")
    failures: list[str] = []

    # 1 + 2: presence + length
    for name in _PROD_REQUIRED:
        value = os.environ.get(name) or ""
        if not value:
            failures.append(f"{name} missing")
            continue
        min_len = _MIN_LENGTHS.get(name)
        if min_len and len(value) < min_len:
            failures.append(
                f"{name} length {len(value)} < minimum {min_len}"
            )

    # 3: DB path parent writable
    db_path = os.environ.get("BUILDEMUP_DATABASE_PATH")
    if db_path:
        try:
            parent = os.path.dirname(os.path.abspath(db_path)) or "."
            sentinel = os.path.join(
                parent, ".buildemup_health_sentinel",
            )
            with open(sentinel, "w") as fh:
                fh.write("ok")
            os.unlink(sentinel)
        except OSError as exc:
            failures.append(
                f"BUILDEMUP_DATABASE_PATH parent not writable: {exc}"
            )

    # 4: SQLite version
    ver = sqlite3.sqlite_version_info[:3]
    if ver < _MIN_SQLITE:
        failures.append(
            f"SQLite {ver} < required {_MIN_SQLITE} "
            f"(UPDATE...RETURNING needed)"
        )

    # 5: B-062 — prod + test-mode is a forbidden combination.
    # Test mode exposes /c3a/_test_harness.html AND disables the
    # c3aFetch 503 auto-retry. Either alone is acceptable in dev;
    # both in prod means real users land on a harness that won't
    # retry transient SQLite locks.
    if is_prod and os.environ.get("C3A_TEST_MODE") == "1":
        failures.append(
            "C3A_TEST_MODE=1 is forbidden when BUILDEMUP_ENV=prod "
            "(exposes /c3a/_test_harness.html and disables the "
            "c3aFetch 503 auto-retry path)"
        )

    if not failures:
        LOGGER.info(
            "config validation ok (env=%s, sqlite=%s)", env, ver,
        )
        return

    if is_prod:
        for f in failures:
            LOGGER.error("config validation failed: %s", f)
        sys.exit(1)
    else:
        for f in failures:
            LOGGER.warning(
                "config validation (env=%s, non-fatal): %s", env, f,
            )


# ─────────────────────────────────────────────────────────────────────
# Handler-result unpacking — supports the S7b 3-tuple 503 path
# ─────────────────────────────────────────────────────────────────────
def _unpack_handler_result(result):
    """Normalize handler returns to (status, body, extra_headers).

    Legacy contract: (status, body) — 2-tuple. extra_headers is None.
    S7b § 6.2 storage_busy: (status, body, headers) — 3-tuple.
    """
    if len(result) == 3:
        status, body, extra_headers = result
        return status, body, extra_headers
    status, body = result
    return status, body, None


class BriefCaptureHandler(BaseHTTPRequestHandler):
    """Serve Component 1 form + API."""

    # Silence noisy log lines — keep stdout clean for deployments
    def log_message(self, format, *args):  # noqa
        if os.environ.get("BUILDEMUP_HTTP_VERBOSE"):
            super().log_message(format, *args)

    def do_GET(self):  # noqa — stdlib naming
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Root → redirect to form
        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/brief_form.html")
            self.end_headers()
            return

        # API: vastu partial items
        if path == "/api/vastu/partial-items":
            status, body = handle_vastu_partial_items()
            self._send_json(status, body)
            return

        # API: resume saved brief
        if path == "/api/brief/resume":
            token = (qs.get("token") or [""])[0]
            status, body = handle_brief_resume(token)
            self._send_json(status, body)
            return

        # ─── S7b § 8.4 — health probe ───────────────────────────────
        if path == "/health":
            status, body = handle_health()
            self._send_json(status, body)
            return

        # ─── S8 § 5a — read-only /status ────────────────────────────
        if path == "/api/extreme-case/status":
            status, body = handle_c3a_status(qs, self.headers)
            self._send_json(status, body)
            return

        # ─── S8 § 5b — POST-neutralizing GET wrapper /check-init ────
        # Bot-UA path returns an HTML preview; legitimate UA path
        # returns the same JSON shape as POST /check, with no-cache
        # headers (v1.1 Item 7) and trace_id rewritten per P43.
        if path == "/api/extreme-case/check-init":
            result = handle_c3a_check_init(qs, self.headers)
            status, body, extra_headers = _unpack_handler_result(result)
            if isinstance(body, dict) and body.get("_html_response"):
                self._send_html(
                    status, body["body"],
                    extra_headers=body.get("extra_headers"),
                )
            else:
                self._send_json(
                    status, body, extra_headers=extra_headers,
                )
            return

        # ─── S8 § 5 — Static C3a UI assets ──────────────────────────
        # Five user-facing pages + shared assets (CSS/JS) + one test
        # harness, all served from static/c3a/. Any GET under /c3a/
        # is delegated to _serve_static, which already enforces the
        # STATIC_DIR containment check (no path traversal). Routes
        # paired with files (Pattern B avoidance — routes shipped in
        # the same phase as the HTML/JS/CSS they serve, NOT 2 sessions
        # ahead per Ramalingam's Phase 1 override).
        #
        # § 4.11 — _test_harness.html exists ONLY to enable Phase 6
        # e2e tests of handlePageFlow / displayError. Production
        # deploys MUST NOT expose it (it bypasses test-mode gating
        # of the c3aFetch wrapper, breaking real-user 503 handling).
        # Gate behind C3A_TEST_MODE=1 env var; otherwise return 404
        # so the harness looks like an ordinary missing file.
        if path.startswith("/c3a/"):
            if (
                path == "/c3a/_test_harness.html"
                and os.environ.get("C3A_TEST_MODE") != "1"
            ):
                self._send_json(
                    404,
                    {"ok": False, "errors": [f"Not found: {path}"]},
                )
                return
            self._serve_static(path)
            return

        # Static files
        if path in (
            "/brief_form.html", "/brief_form.js", "/brief_form.css",
            # S59 orchestrator-results + quote-upload UIs
            "/orchestrator_run.html", "/orchestrator_run.js",
            "/orchestrator_run.css",
            "/quote_compare.html", "/quote_compare.js",
        ):
            self._serve_static(path)
            return

        # 404
        self._send_json(404, {"ok": False, "errors": [f"Not found: {path}"]})

    def do_POST(self):  # noqa
        path = self.path.split("?", 1)[0]

        if path == "/api/brief/capture":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_brief_capture(body)
            self._send_json(status, response)
            return

        if path == "/api/brief/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            # Construct host base URL from the request Host header so
            # resume URLs point to the right domain
            host = self.headers.get("Host", "")
            # Respect X-Forwarded-Proto for Railway / behind proxy
            proto = self.headers.get("X-Forwarded-Proto", "http")
            host_base = f"{proto}://{host}" if host else ""
            status, response = handle_brief_save(body, host_base_url=host_base)
            self._send_json(status, response)
            return

        if path == "/api/feasibility/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_feasibility_run(body)
            self._send_json(status, response)
            return

        if path == "/api/orchestrate":
            # S59 — runs the full 18-phase master orchestrator pipeline
            # (C1-C17 plus c03a_extreme_case_detection).
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_orchestrate(body)
            self._send_json(status, response)
            return

        if path == "/api/quote/compare":
            # S59 follow-up #9 — C17 quote-comparison flow. The
            # master orchestrator does NOT invoke C17 because it has
            # no contractor quote to compare; this endpoint is the
            # entry point for the upload-quote-and-compare flow.
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_quote_compare(body)
            self._send_json(status, response)
            return

        if path == "/api/setback/preview":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_setback_preview(body)
            self._send_json(status, response)
            return

        # ─── Component 3a — Extreme Case Gate (S7a + S7b) ─────────────
        # All five c3a handlers return a 2-tuple (status, body) on
        # legacy paths and a 3-tuple (status, body, headers) on the
        # new 503 storage_busy path (§ 6.2). _unpack_handler_result
        # normalizes both shapes.
        if path == "/api/extreme-case/check":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            result = handle_c3a_check(body)
            status, response, extra = _unpack_handler_result(result)
            self._send_json(status, response, extra_headers=extra)
            return

        if path == "/api/extreme-case/resolve":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            result = handle_c3a_resolve(body)
            status, response, extra = _unpack_handler_result(result)
            self._send_json(status, response, extra_headers=extra)
            return

        if path == "/api/extreme-case/abort":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            result = handle_c3a_abort(body)
            status, response, extra = _unpack_handler_result(result)
            self._send_json(status, response, extra_headers=extra)
            return

        if path == "/api/extreme-case/cba-verified":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            result = handle_c3a_cba_verified(body)
            status, response, extra = _unpack_handler_result(result)
            self._send_json(status, response, extra_headers=extra)
            return

        if path == "/api/extreme-case/cba-fallback-continue":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            # P34: pass inbound headers so the wrapper can resolve
            # X-Trace-Id from the scheduler-tick caller. self.headers
            # is an HTTPMessage, which supports .get() (Mapping-ish).
            result = handle_c3a_cba_fallback_continue(body, self.headers)
            status, response, extra = _unpack_handler_result(result)
            self._send_json(status, response, extra_headers=extra)
            return

        # ─── S7b admin endpoints ──────────────────────────────────────
        if path == "/admin/scheduler/tick":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_scheduler_tick(body, self.headers)
            self._send_json(status, response)
            return

        if path == "/admin/scheduler/reset":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            status, response = handle_scheduler_reset(body, self.headers)
            self._send_json(status, response)
            return

        self._send_json(404, {"ok": False, "errors": [f"Not found: {path}"]})

    def _send_json(
        self, status: int, body: dict, *, extra_headers=None,
    ) -> None:
        """Serialize and send a JSON response.

        S7b: optional `extra_headers` mapping (e.g. {"Retry-After": "5"}
        on 503 storage_busy) is added BEFORE end_headers. The S7a
        2-arg call signature is preserved for non-c3a routes.
        """
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        # CORS: allow local dev from file:// or other origins
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, str(value))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(
        self, status: int, body: str, *, extra_headers=None,
    ) -> None:
        """Serialize and send an HTML response.

        S8 § 5b — bot-preview path of /api/extreme-case/check-init.
        Mirrors `_send_json` structure but writes text/html and
        respects caller-supplied Content-Type / Cache-Control via
        `extra_headers`.
        """
        payload = body.encode("utf-8")
        self.send_response(status)
        # Default Content-Type for HTML; caller may override via
        # extra_headers (the bot path supplies its own to be explicit).
        ct = None
        if extra_headers:
            ct = extra_headers.get("Content-Type")
        self.send_header(
            "Content-Type", ct or "text/html; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for name, value in extra_headers.items():
                if name.lower() == "content-type":
                    continue  # already sent
                self.send_header(name, str(value))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_static(self, path: str) -> None:
        filename = path.lstrip("/")
        filepath = STATIC_DIR / filename
        # Security: make sure we don't serve anything outside STATIC_DIR
        try:
            filepath.resolve().relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_json(403, {"ok": False, "errors": ["Forbidden"]})
            return

        if not filepath.exists() or not filepath.is_file():
            self._send_json(404, {"ok": False, "errors": [f"Not found: {path}"]})
            return

        ext = filepath.suffix.lower()
        mime = _STATIC_MIME.get(ext, "application/octet-stream")
        content = filepath.read_bytes()

        # § 5.6.1 — meta-tag injection for C3a HTML when test mode active.
        # Only runs for /c3a/*.html paths (other static surfaces left
        # untouched), and only when C3A_TEST_MODE=1. The helper is
        # idempotent so _test_harness.html (which has the tag hardcoded)
        # stays single-tag.
        if (
            ext == ".html"
            and path.startswith("/c3a/")
            and os.environ.get("C3A_TEST_MODE") == "1"
        ):
            content = _inject_test_mode_meta(content)

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        # B-064 — static asset hardening: CSP + Cache-Control + nosniff.
        for header_name, header_value in _static_security_headers(ext).items():
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(content)


def run_server(host: str = "0.0.0.0", port: int | None = None) -> None:
    # § 9.7 / P32 — validate config BEFORE binding the socket. In
    # prod, failure here sys.exit(1)'s; the HTTP server never starts.
    _validate_config()

    if port is None:
        port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer((host, port), BriefCaptureHandler)
    print(f"BuildemUp Component 1 + 2 + 3a listening on http://{host}:{port}")
    print(f"  Form:                http://{host}:{port}/brief_form.html")
    print(f"  C1 brief (POST):     http://{host}:{port}/api/brief/capture")
    print(f"  C2 feasibility (POST): http://{host}:{port}/api/feasibility/run")
    print(f"  Health (GET):        http://{host}:{port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    run_server()
