"""S8 § 5a — GET /api/extreme-case/status read-only handler.

Per BuildemUp C3a SPEC v1.2 LOCKED § 5a:

  GET /api/extreme-case/status?session_token=<token>
  Headers:
    X-Trace-Id: <16-hex>  (optional; correlation hint)

Response shapes (§ 5a.3):

  Success (200) for non-terminal session:
    {
      "ok": true,
      "session_token": "<token>",
      "current_state": "IN_PROGRESS",
      "terminal_state": null,
      "is_terminal": false,
      "last_updated_at": <unix>,
      "trace_id": "<16-hex>"
    }

  Success (200) for terminal session:
    current_state == terminal_state == GateTerminationReason.value
    is_terminal == true

  Errors:
    400 validation       — missing session_token query param
    404 unknown_token    — token not in gate_states (purged or never existed)

Used by done.html / aborted.html for state reconciliation
(External Item 2). Pure read; no side effects.

Authentication: none — relies on 122-bit session_token entropy
(threat model § 5a.5). Rate limiting / view-token rotation deferred
to B-042.

Read consistency: SQLite WAL provides snapshot isolation for the
read transaction; partial-state reads are impossible at row
granularity (round 2 X6).

Trace-id behavior follows P43 (§ 2.8 — NEW round 2):
  - server_trace_id is always minted fresh (canonical for ops).
  - X-Trace-Id header (if valid 16-hex) is captured as
    client_trace_id correlation hint.
  - Response body `trace_id` field carries client_trace_id when
    valid, else echoes server_trace_id (so the user-facing UX
    surface is never empty).
  - Both fields are written into structured request log lines.
"""

from __future__ import annotations

import logging
from typing import Optional

# Import the canonical trace-id helpers from c3a_endpoint so /status
# uses the same 16-hex format as every other C3a handler (P34).
from buildemup.api.c3a_endpoint import (
    _new_trace_id,
    _resolve_trace_pair,
)
from buildemup.api.c3a_endpoint import _get_storage as _gate_state_storage

logger = logging.getLogger(__name__)


def handle_status(
    query_params: dict,
    headers: Optional[object] = None,
) -> tuple[int, dict]:
    """GET /api/extreme-case/status handler.

    `query_params` is a parsed query-string dict
    (urllib.parse.parse_qs → values are lists, take [0]).
    `headers` is the BaseHTTPRequestHandler.headers mapping; pass
    None in pure-unit tests.

    Per P43 (§ 2.8): mint a fresh server_trace_id; if X-Trace-Id is
    a valid 16-hex, capture it as client_trace_id correlation hint.
    Both go into structured logs; the response body field uses
    client_trace_id (or server_trace_id when no client trace).
    """
    # Normalize parse_qs lists → first value
    if isinstance(query_params, dict):
        token_val = query_params.get("session_token")
        token = (
            token_val[0] if isinstance(token_val, list) and token_val
            else (token_val if isinstance(token_val, str) else None)
        )
    else:  # already a flat dict
        token = None

    server_trace_id, client_trace_id = _resolve_trace_pair(
        _extract_trace_header(headers),
    )
    response_trace = client_trace_id or server_trace_id

    logger.info(
        "c3a.status.request server_trace_id=%s client_trace_id=%s "
        "session_token_present=%s",
        server_trace_id,
        client_trace_id or "null",
        bool(token),
    )

    if not token:
        return 400, {
            "ok": False,
            "errors": [{
                "code": "validation",
                "message": "session_token required",
            }],
            "trace_id": response_trace,
        }

    snapshot = _gate_state_storage().load_status_row(token)
    if snapshot is None:
        return 404, {
            "ok": False,
            "errors": [{
                "code": "unknown_token",
                "message": "session not found",
            }],
            "trace_id": response_trace,
        }

    termination_reason, is_terminal, saved_at = snapshot
    terminal_state = termination_reason if is_terminal else None
    current_state = terminal_state if is_terminal else "IN_PROGRESS"

    return 200, {
        "ok": True,
        "session_token": token,
        "current_state": current_state,
        "terminal_state": terminal_state,
        "is_terminal": is_terminal,
        "last_updated_at": int(saved_at),
        "trace_id": response_trace,
    }


def _extract_trace_header(headers) -> Optional[str]:
    """Pull X-Trace-Id from a headers mapping. Returns None if absent
    or if `headers` is None (e.g., pure-unit-test invocations)."""
    if headers is None:
        return None
    try:
        return headers.get("X-Trace-Id")
    except AttributeError:
        return None


__all__ = ["handle_status"]
