"""
Component 3a — Email hook (S7b production wiring per SPEC v1.0 § 7.2).

Per the locked S7b SPEC § 7.4 hook contract:
  - Returns None.
  - Never raises (the hook itself catches and logs).
  - Idempotent across replays (the API-layer P16 short-circuit prevents
    re-invocation on duplicate request_id).
  - Pure side effect — no return value carries information.

Production replacement (S7b): POST to Resend's transactional API
(https://resend.com). Authentication via `RESEND_API_KEY` env var.
FROM address via `RESEND_FROM` (default `noreply@buildemup.com` —
must be domain-verified at Resend before production use).

Reliability model (P20):
  - Single HTTP attempt with 5-second timeout.
  - No retry; no queue; no persistence.
  - Failure → log WARNING; the scheduler 24h fallback (P21 + P33) is
    the user-facing reliability layer.
  - B-048 tracks future retry under a measured failure-rate trigger.

Trace propagation (P29):
  - `trace_id` keyword-only parameter; backward-compatible via default.
  - Logged on every WARNING/INFO line for end-to-end tracing.
  - Forwarded to Resend as `X-Trace-Id` custom header.

S8 § 1.2 (ii) carve-out (Findings 1 + 2):
  - Email body now embeds an absolute `cba-checklist` URL constructed
    from `BUILDEMUP_PUBLIC_URL` env var, the paused session_token, and
    the trace_id. Replaces the v0.x "use draft id X on your dashboard"
    copy that required the user to know where to go.
  - Adds a "do not forward this email" UX hint per § 5a.5 round-3 R3.6
    relabel — explicitly NOT a security mitigation; just sets user
    expectation. Real protection against email forwarding requires
    short-lived view tokens (B-042).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger("buildemup.c3a.email_hook")


# ─── Configuration ───────────────────────────────────────────────────
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_FROM_DEFAULT = "noreply@buildemup.com"
REQUEST_TIMEOUT_SECONDS = 5.0

# S8 § 9.3 + § 1.2 (ii) — public URL for cba-checklist link construction.
# Production deploys MUST set this env var (server.py _validate_config
# enforces presence in BUILDEMUP_ENV=prod). Dev default keeps local
# workflows running without manual env setup.
PUBLIC_URL_DEFAULT = "http://localhost:8000"


def _public_url_base() -> str:
    """Read BUILDEMUP_PUBLIC_URL with the dev default. Trailing slashes
    are stripped so URL composition stays predictable regardless of
    whether the operator wrote `https://x.com` or `https://x.com/`."""
    return os.environ.get(
        "BUILDEMUP_PUBLIC_URL", PUBLIC_URL_DEFAULT,
    ).rstrip("/")


def _build_cba_checklist_url(
    session_token: str, trace_id: Optional[str],
) -> str:
    """Construct the absolute cba-checklist URL for the email link.

    Pattern: `{base}/c3a/checklist.html?token=<urlquoted>&trace=<urlquoted>`.
    Trace is omitted when None. Both values are URL-encoded so any
    operator-chosen token format remains URL-safe.
    """
    base = _public_url_base()
    params = [("token", session_token)]
    if trace_id:
        params.append(("trace", trace_id))
    return f"{base}/c3a/checklist.html?{urllib.parse.urlencode(params)}"


def send_cba_checklist(
    to_email: Optional[str],
    draft_token: str,
    fallback_at: str,
    *,
    trace_id: Optional[str] = None,
) -> None:
    """Send the CBA verification checklist email via Resend.

    Args:
        to_email: user's email (may be None — Brief.user_email is
                  optional). When None, the hook logs INFO and returns
                  without making a network call.
        draft_token: paused session_token, the resume identifier;
                     embedded into the cba-checklist URL.
        fallback_at: ISO 8601 string, 24h after pause (display only).
        trace_id: 16-hex correlation ID propagated end-to-end (P29).
                  Embedded into the URL so support can correlate the
                  user's resume click back to the pause-time logs.

    Returns:
        None. Per § 7.4 contract — never raises.
    """
    if not to_email:
        logger.info(
            "send_cba_checklist: no email address; skipping "
            "(draft_token=%s, trace_id=%s)",
            _mask_token(draft_token), trace_id,
        )
        return None

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.warning(
            "send_cba_checklist: RESEND_API_KEY not set; no email "
            "sent (recipient=%s, draft_token=%s, trace_id=%s)",
            _mask_email(to_email), _mask_token(draft_token), trace_id,
        )
        return None

    checklist_url = _build_cba_checklist_url(draft_token, trace_id)
    body = {
        "from": os.environ.get("RESEND_FROM", RESEND_FROM_DEFAULT),
        "to": [to_email],
        "subject": "Action needed: confirm your plot's CBA classification",
        "html": _render_cba_email_html(
            draft_token, fallback_at, checklist_url,
        ),
    }
    if trace_id:
        body["headers"] = {"X-Trace-Id": trace_id}

    req = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            req, timeout=REQUEST_TIMEOUT_SECONDS,
        ) as resp:
            if 200 <= resp.status < 300:
                logger.info(
                    "send_cba_checklist: ok "
                    "(recipient=%s, status=%d, trace_id=%s)",
                    _mask_email(to_email), resp.status, trace_id,
                )
            else:
                logger.warning(
                    "send_cba_checklist: non-2xx response "
                    "(recipient=%s, status=%d, trace_id=%s)",
                    _mask_email(to_email), resp.status, trace_id,
                )
    except urllib.error.URLError as exc:
        logger.warning(
            "send_cba_checklist: network failure "
            "(recipient=%s, trace_id=%s): %r",
            _mask_email(to_email), trace_id, exc,
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "send_cba_checklist: unexpected error "
            "(recipient=%s, trace_id=%s): %r",
            _mask_email(to_email), trace_id, exc,
        )
    return None


def _render_cba_email_html(
    draft_token: str, fallback_at: str, checklist_url: str,
) -> str:
    return (
        "<!doctype html>\n"
        "<html><body style='font-family:system-ui,sans-serif;"
        "color:#111;max-width:600px;margin:24px auto;line-height:1.5;'>\n"
        "<h2>Confirm your plot's CBA classification</h2>\n"
        "<p>To finish your house plan, we need to confirm whether your "
        "plot falls within a Continuous Building Area (CBA). The "
        "answer affects your setbacks and what's buildable on the "
        "site.</p>\n"
        "<p>Please log in and tell us what your plot's classification "
        "is — you'll find a short checklist on the resume page.</p>\n"
        f"<p><strong><a href=\"{checklist_url}\" style=\"color:#1a4d8a;\">"
        "Open your CBA checklist</a></strong></p>\n"
        f"<p style='color:#666;font-size:0.9em;'>Or copy this link: "
        f"<code style='word-break:break-all;'>{checklist_url}</code></p>\n"
        f"<p>If we don't hear from you by <em>{fallback_at}</em>, "
        "we'll proceed with the conservative default assumption "
        "(plot is NOT in a CBA) and continue your design.</p>\n"
        "<p style='color:#9a4f00;font-size:0.9em;background:#fff8eb;"
        "border:1px solid #f0d6a0;padding:8px 12px;border-radius:4px;"
        "margin-top:16px;'>"
        "<strong>Please do not forward this email.</strong> "
        "The link above is tied to your specific case; "
        "forwarding it gives the recipient access to your "
        "design brief.</p>\n"
        "<p style='color:#666;font-size:0.9em;margin-top:24px;'>"
        "— BuildemUp / BuildEase</p>\n"
        "</body></html>\n"
    )


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _mask_token(token: str) -> str:
    if not token or len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


__all__ = [
    "send_cba_checklist",
    "_build_cba_checklist_url",
    "_public_url_base",
    "PUBLIC_URL_DEFAULT",
]
