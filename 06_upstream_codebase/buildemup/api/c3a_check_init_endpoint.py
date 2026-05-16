"""S8 § 5b — GET /api/extreme-case/check-init handler.

Per BuildemUp C3a SPEC v1.2 LOCKED § 5b:

  GET /api/extreme-case/check-init?brief=<token>&request_id=<id>
  Headers:
    User-Agent: <browser UA>  (read; bot-filtered per § 5b.5)
    X-Trace-Id: <16-hex>      (optional; correlation hint)

POST-neutralizing GET wrapper around POST /api/extreme-case/check
(round 2 X3). case.html issues this on page load instead of a POST,
eliminating the "Resend form data?" prompt and the accidental
session creation that link-preview bots and prefetchers triggered
when they followed the case URL.

Response (legitimate user agent — § 5b.3):
  Same JSON shape as POST /check:
    { "ok": true, "session_token": "...", "extreme_case": {...},
      "trace_id": "<16-hex>" }
  Cache-Control: no-store, no-cache, must-revalidate (v1.1 Item 7).

Response (bot user agent — v1.2 P-2 § 5b.4):
  200 OK with minimal preview HTML. NO call to handle_check.
  NO session created in storage. Cache-Control: no-store.

Bot-UA detection (§ 5b.5): case-insensitive substring match against
BOT_UA_PATTERNS. Empty/missing UA is treated as suspicious and
served the bot preview as well. Mitigation, not security; see
§ 5a.5 for the threat model and B-042 for the structural fix.

Trace-id behavior follows P43 (§ 2.8): server_trace_id is canonical;
client_trace_id (validated inbound header) surfaces in the response
body's `trace_id` field for the legitimate-UA path.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

# We delegate the legitimate-UA path to the existing POST /check
# pipeline so all S7a invariants (idempotency P12, brief-token
# resolution P10, etc.) are preserved by construction. handle_check
# already mints its own server_trace_id and emits the metric.
from buildemup.api.c3a_endpoint import (
    handle_check,
    _resolve_trace_pair,
)

logger = logging.getLogger(__name__)


# ─── Bot User-Agent filter (§ 5b.5) ─────────────────────────────────
# Maintained in code per spec — new bot patterns can be added without
# a spec amendment (the spec calls this constant out as additive-only).
BOT_UA_PATTERNS: tuple[str, ...] = (
    # Link preview crawlers (web-verified)
    "facebookexternalhit",   # Meta link previews
    "facebot",
    "slackbot",              # Slack link unfurl
    "twitterbot",            # Twitter/X cards
    "linkedinbot",           # LinkedIn previews
    "telegrambot",           # Telegram previews
    "whatsapp",              # WhatsApp previews
    "discordbot",            # Discord embeds
    "blueskypreviewbot",     # Bluesky previews
    # Prefetch / privacy proxies / search crawlers
    "chrome-lighthouse",     # Lighthouse audits
    "googlebot",             # Google crawler
    "bingbot",               # Bing crawler
    "duckduckbot",           # DuckDuckGo
    # AI training / general crawlers
    "anthropic-ai",
    "claudebot",
    "gptbot",
    "ccbot",                 # Common Crawl
    "bytespider",            # ByteDance
    # Generic last-resort patterns
    "bot",
    "crawler",
    "spider",
    "scraper",
)


def _is_bot_ua(ua: Optional[str]) -> bool:
    """Case-insensitive substring match against BOT_UA_PATTERNS.

    Empty/None UA is treated as suspicious (returns True) on the
    rationale that real browsers always send a UA; absence is more
    likely a scripted client than a privacy-careful human.
    """
    if not ua:
        return True
    ua_low = ua.lower()
    return any(pat in ua_low for pat in BOT_UA_PATTERNS)


# ─── Bot preview HTML (§ 5b.4) ──────────────────────────────────────
BOT_PREVIEW_HTML: str = (
    "<!DOCTYPE html>\n"
    "<html>\n"
    "<head>\n"
    "  <meta charset=\"utf-8\">\n"
    "  <title>BuildemUp \u2014 Case Resolution</title>\n"
    "  <meta property=\"og:title\" "
    "content=\"BuildemUp \u2014 Case Resolution\">\n"
    "  <meta property=\"og:description\" "
    "content=\"Resolve your design brief case.\">\n"
    "  <meta name=\"referrer\" content=\"no-referrer\">\n"
    "</head>\n"
    "<body>\n"
    "  <h1>BuildemUp \u2014 Case Resolution</h1>\n"
    "  <p>This page requires a browser to load. "
    "Please open in your browser.</p>\n"
    "</body>\n"
    "</html>\n"
)


_NO_CACHE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
}


def _norm_qs(query_params: dict, key: str) -> Optional[str]:
    """Pull the first value for `key` from a urllib.parse.parse_qs
    result (values are lists). Returns None when missing or empty."""
    val = query_params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    if isinstance(val, str):
        return val
    return None


def handle_check_init(query_params: dict, headers):
    """GET /api/extreme-case/check-init handler.

    Returns 2-tuple `(status, body)` for normal JSON paths and
    3-tuple `(status, body, extra_headers)` whenever Cache-Control
    or other non-JSON headers must accompany the response. The
    server's `_unpack_handler_result` already normalises both shapes.

    Bot-UA path: returns
      (200, {'_html_response': True, 'body': BOT_PREVIEW_HTML,
             'extra_headers': {...}}, no_cache_headers)
    The route handler in server.py inspects `_html_response` to
    serve text/html instead of JSON.

    Legitimate-UA path: constructs the JSON body POST /check expects
    and dispatches via the existing `handle_check` wrapper, then
    rewrites `body['trace_id']` to client_trace_id when the inbound
    X-Trace-Id was a valid 16-hex (P43 § 2.8) and tacks on the
    no-cache headers per § 5b.3.
    """
    ua = _extract_header(headers, "User-Agent") or ""
    server_trace_id, client_trace_id = _resolve_trace_pair(
        _extract_header(headers, "X-Trace-Id"),
    )
    response_trace = client_trace_id or server_trace_id

    if _is_bot_ua(ua):
        # NO session creation. NO call to handle_check. The bot gets
        # a clean preview; legitimate users (case.html script load)
        # fall through to the JSON path below.
        logger.info(
            "c3a.check_init.bot_filtered server_trace_id=%s "
            "ua=%r", server_trace_id, ua[:120],
        )
        return 200, {
            "_html_response": True,
            "body": BOT_PREVIEW_HTML,
            "extra_headers": dict(_NO_CACHE_HEADERS, **{
                "Content-Type": "text/html; charset=utf-8",
            }),
        }

    # Legitimate UA path. Structured request log per P43.
    logger.info(
        "c3a.check_init.request server_trace_id=%s "
        "client_trace_id=%s",
        server_trace_id, client_trace_id or "null",
    )

    brief_token = _norm_qs(query_params, "brief") or ""
    request_id = _norm_qs(query_params, "request_id") or ""

    # Build the JSON body POST /check expects. handle_check will
    # validate the field shapes itself and produce the appropriate
    # 400 / 410 / 503 error if anything is off.
    body_json = json.dumps({
        "brief_token": brief_token,
        "request_id": request_id,
    }).encode("utf-8")

    result = handle_check(body_json)

    # handle_check returns a 2-tuple normally and a 3-tuple on the
    # 503 storage_busy path. Normalize to (status, body, headers).
    if len(result) == 3:
        status, body, extra = result
        merged_headers = dict(extra or {}, **_NO_CACHE_HEADERS)
    else:
        status, body = result
        merged_headers = dict(_NO_CACHE_HEADERS)

    # P43: rewrite response body trace_id to client_trace_id when
    # the inbound X-Trace-Id was valid; else keep handle_check's
    # server_trace_id (we cannot recover it post-call). When client
    # is None, the body keeps handle_check's own trace — which is
    # already a fresh server-minted id, satisfying P43's "never
    # empty" rule.
    if client_trace_id and isinstance(body, dict):
        body = {**body, "trace_id": client_trace_id}

    return status, body, merged_headers


def _extract_header(headers, name: str) -> Optional[str]:
    """Pull a header value from a BaseHTTPRequestHandler.headers
    mapping. Returns None when `headers` is None (used in unit
    tests) or the name is absent."""
    if headers is None:
        return None
    try:
        return headers.get(name)
    except AttributeError:
        return None


__all__ = [
    "handle_check_init",
    "BOT_UA_PATTERNS",
    "BOT_PREVIEW_HTML",
    "_is_bot_ua",
]
