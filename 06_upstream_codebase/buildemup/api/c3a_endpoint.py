"""
Component 3a — API endpoints (S7a SPEC v1.0 LOCKED + S7b SPEC v1.0 LOCKED).

Five POST endpoints over Component 3a (Extreme Case Gate):

  POST /api/extreme-case/check                 (§ 5.1)
  POST /api/extreme-case/resolve               (§ 5.2)
  POST /api/extreme-case/abort                 (§ 5.3)
  POST /api/extreme-case/cba-verified          (§ 5.4)
  POST /api/extreme-case/cba-fallback-continue (§ 5.5)

Every handler signature (S7b § 5.3 wrapper pattern):
  def handle_X(request_body: bytes | str) -> tuple[int, dict]
      ↳ thin instrumentation wrapper around _handle_X_inner.
  def _handle_X_inner(request_body: bytes | str, trace_id: str)
      ↳ all the business logic from S7a, unchanged.

Wrapper responsibilities (S7b § 5.2 + § 5.3 + § 6.2):
  - Mint trace_id per request (§ 5.4 — `secrets.token_hex(8)` → 16 hex
    chars, P34 format-invariant by construction). The single exception
    is `handle_cba_fallback_continue`, which resolves trace_id from the
    inbound `X-Trace-Id` header so the scheduler tick can preserve the
    original pause-time trace across the 24h boundary (P29 + P34).
  - Catch `sqlite3.OperationalError` containing "database is locked"
    and surface as HTTP 503 + body `code: storage_busy` + headers
    `Retry-After: 5` (§ 6.2). The 503 path is the ONLY one that
    returns a 3-tuple (status, body, headers); all other paths stay
    on the 2-tuple contract for backward compat.
  - Emit one `c3a.endpoint` structured-log metric line per handler
    invocation, with bounded cardinality (P30 + § 5.2). Failures in
    the metric emit itself are swallowed (P22).

Pure handlers — they do NOT touch the network. The HTTP layer
(api/server.py) routes URLs to these handlers.

INVARIANTS ENFORCED HERE (S7a SPEC § 2 + § 6.7; S7b additions tagged):
  P1  GateState round-trips losslessly via to_dict / from_dict
  P2  request_id idempotency: duplicate replays cached response
  P3  terminal tokens → HTTP 200 with cached response (NOT 410)
  P4  no-delete on terminal sessions (TTL only; storage layer)
  P7  wire-format is_done: True for all 6 termination reasons; plus
      aborted / paused supplementary flags (NOT mutating S6 semantics)
  P9  1 MB request size cap → HTTP 400
  P10 hook ordering: save state first, then fire hook (best-effort)
  P11 per-token single-flight lock around read→compute→save
  P12 brief→session uniqueness on /check via register_brief_session
  P13 atomic state+cache co-write via save_existing
  P14 deterministic JSON ordering (sort_keys=True at storage layer)
  P15 terminal-replay advisory field session_status="terminal_replay"
  P16 hooks NOT re-fired on idempotency replay (cached response is the
      proof the hook fired — or attempted to — the first time)
  P18 per-field validation runs after JSON parse; 1 MB cap is the
      defense-in-depth outer check
  P22 (S7b) instrumentation never raises; metric emit is best-effort
  P29 (S7b) trace_id propagated to hooks (keyword) and storage rows
  P30 (S7b) metric line cardinality bounded; closed `error_class`
      vocabulary; unmapped codes log a SEPARATE WARNING preserving
      the raw code (no token, email, request_id, free text)
  P34 (S7b) `X-Trace-Id` validated at the cba-fallback-continue trust
      boundary against `^[0-9a-f]{16}$`; otherwise minted fresh +
      WARNING

Hook injection (§ 7.1, § 7.2 + S7b § 7.2 + § 7.3):
  Email + scheduler hooks are bound at module import time to the
  production wiring in api/c3a_email_hook + api/c3a_scheduler_hook.
  Tests can override `_send_cba_checklist` and
  `_schedule_fallback_invitation` module attributes (counter-based
  fakes). Note S7b: scheduler hook signature changed from
  `(draft_token, fallback_at)` to
  `(session_token, fire_at_unix, request_id, *, trace_id=None)` —
  hook-ordering test's fake_scheduler updated accordingly (§ 8.7).

†= placeholder name marker (BuildemUp† to be renamed later).
"""
from __future__ import annotations
import json
import logging
import re
import secrets
import sqlite3
import time
from typing import Any, Mapping, Optional

from buildemup.api.c3a_email_hook import send_cba_checklist as _send_cba_checklist
from buildemup.api.c3a_scheduler_hook import (
    schedule_fallback_invitation as _schedule_fallback_invitation,
)
from buildemup.components.c02 import orchestrator as _c2_orchestrator
from buildemup.components.c02.feasibility_input import FeasibilityInput
from buildemup.components.c03a.gate_state import (
    GateState,
    GateTerminationReason,
    SchemaVersionError,
)
from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.domain.brief import Brief
from buildemup.domain.extreme_case import (
    BriefChangeIntegrityError,
    ExtremeCaseId,
    PreviewModeAcknowledgment,
)
from buildemup.utils.brief_storage import (
    BriefStorage,
    TokenNotFoundError as BriefTokenNotFoundError,
)
from buildemup.utils.gate_state_storage import (
    GateStateStorage,
    MAX_PAYLOAD_BYTES,
    PayloadTooLargeError,
    TokenNotFoundError as GateTokenNotFoundError,
    get_session_lock,
    new_token,
)


logger = logging.getLogger("buildemup.c3a.endpoint")


# ─────────────────────────────────────────────────────────────────────
# S7b § 5.4 — trace_id generation + P34 external-trust validation
# ─────────────────────────────────────────────────────────────────────
# Internal generator: 16 lowercase hex chars. Format-invariant by
# construction — `_TRACE_ID_RE.match(_new_trace_id())` is always true,
# so the P34 boundary check at cba-fallback-continue can never reject
# a trace_id that this module generated. (Distinct from
# `utils.logging.new_trace_id()` which generates 12-char IDs for other
# subsystems and is left untouched per the S7b locked-surface scope.)
def _new_trace_id() -> str:
    return secrets.token_hex(8)


_TRACE_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def _resolve_external_trace_id(header_value: Optional[str]) -> str:
    """P34: accept inbound `X-Trace-Id` only if it matches the format.

    The 24h scheduler tick re-POSTs to /cba-fallback-continue with
    `X-Trace-Id` carrying the original pause-time trace_id (P29).
    Validating the format here defends against polluted log lines or
    accidental injection of caller-controlled strings into trace
    fields downstream.

    Returns the validated header value if it matches; otherwise mints
    a fresh trace_id. Logs a WARNING (not ERROR) when a malformed
    header is rejected — this is recoverable by design.

    KEPT INTACT (S8 § 1.2 (ii) carve-out): existing call paths and
    the P34 unit tests rely on this exact 1-tuple signature. New
    P43 paths use `_resolve_trace_pair` below.
    """
    if header_value and _TRACE_ID_RE.match(header_value):
        return header_value
    if header_value:
        logger.warning(
            "rejected malformed X-Trace-Id: %r", header_value,
        )
    return _new_trace_id()


def _resolve_trace_pair(
    header_value: Optional[str],
) -> tuple[str, Optional[str]]:
    """P43 (§ 2.8): decouple server-canonical trace from client hint.

    Returns (server_trace_id, client_trace_id):
      - server_trace_id is ALWAYS freshly minted locally. Canonical
        for ops, metrics, server-side error logs, and the
        X-Trace-Id response header.
      - client_trace_id is the inbound header value when it matches
        the 16-hex format; otherwise None. Surfaces in the response
        body's `trace_id` field (correlation hint shown to the user)
        and in structured request log lines alongside the server id.

    Malformed headers are rejected with a WARNING (parity with P34).
    Missing headers are silent (None client_trace_id is the normal
    case for handlers that don't propagate inbound traces).

    Why both: log-injection defense (URL-supplied trace_ids cannot
    pollute the canonical ops trace) AND support workflow
    (user-visible trace stays stable across the pause-time round
    trip the scheduler relies on for /cba-fallback-continue).
    """
    server_trace_id = _new_trace_id()
    if header_value and _TRACE_ID_RE.match(header_value):
        return server_trace_id, header_value
    if header_value:
        logger.warning(
            "rejected malformed X-Trace-Id: %r", header_value,
        )
    return server_trace_id, None


# ─────────────────────────────────────────────────────────────────────
# S7b § 5.2 — instrumentation: error classification + metric emit
# ─────────────────────────────────────────────────────────────────────
# Closed vocabulary for `error_class` per P30. Codes not in this map
# fall back to "internal" AND emit a SEPARATE WARNING line so the
# raw code is preserved for forensics without expanding metric
# cardinality.
_ERROR_CLASS_BY_CODE: dict[str, str] = {
    # Validation
    "request_too_large": "validation",
    "missing_field":     "validation",
    "invalid_field":     "validation",
    "malformed_json":    "validation",
    # Lifecycle / lookup
    "unknown_token":     "unknown_token",
    "not_paused":        "lifecycle_violation",
    "stale_case":        "lifecycle_violation",
    "already_fired":     "lifecycle_violation",
    # Auth
    "unauthorized":      "validation",
    # Storage
    "storage_busy":      "storage_busy",
    "schema_version":    "schema_version",
}


def _classify_error(
    code: Optional[str],
    trace_id: str,
    handler_name: str,
) -> str:
    """Map a body-level `code` field to the closed `error_class` set.

    None → "ok" (handler succeeded with a 2xx). Mapped codes return
    their class. Unmapped codes return "internal" and emit a WARNING
    on a SEPARATE log line (different `msg`) so log routers can
    sample/aggregate metric lines without affecting the rare-event
    WARNING stream.

    NB: c3a structured-error responses use
    `{"errors": [{"field": ..., "code": ..., ...}]}`, where the code
    is nested. The wrapper extracts `body.get("code")` per spec § 5.3
    — so most c3a 4xx classify as "ok" today (no top-level `code`
    field). The new 503 storage_busy and the admin-endpoint
    top-level codes do classify correctly. Unifying error shapes
    project-wide is C3a v0.2 architecture refactor scope (§ 0.3 (f)
    standing pushback); doing it here would be Pattern E scope-creep.
    """
    if not code:
        return "ok"
    cls = _ERROR_CLASS_BY_CODE.get(code)
    if cls is None:
        try:
            logger.warning(json.dumps({
                "msg": "c3a.endpoint.unmapped_code",
                "handler": handler_name,
                "trace_id": trace_id,
                "raw_code": code,
            }, sort_keys=True))
        except Exception:
            pass  # P22.
        return "internal"
    return cls


def _emit_handler_metric(
    handler_name: str,
    status: int,
    duration_ms: int,
    trace_id: str,
    error_class: str,
) -> None:
    """One INFO line per handler call. Best-effort; never raises (P22).

    Field set is fixed per P30: handler, status, duration_ms,
    trace_id, error_class. No session_token, brief_token, request_id,
    email, or user-supplied free text.
    """
    try:
        logger.info(json.dumps({
            "msg": "c3a.endpoint",
            "handler": handler_name,
            "status": status,
            "duration_ms": duration_ms,
            "trace_id": trace_id,
            "error_class": error_class,
        }, sort_keys=True))
    except Exception as exc:
        try:
            logger.warning("metric emit failed: %r", exc)
        except Exception:
            pass  # P22.


# ─────────────────────────────────────────────────────────────────────
# S7b § 6.2 — HTTP 503 storage_busy response builder
# ─────────────────────────────────────────────────────────────────────
def _build_storage_busy_response(
    trace_id: str,
) -> tuple[int, dict, dict]:
    """503 + Retry-After response for SQLite lock-budget exhaustion.

    The third tuple element (response headers) is an additive extension
    to the handler return contract — server.py treats 3-tuples as
    (status, body, headers) when the handler returns one. Only this
    path produces a 3-tuple; all other paths in c3a stay on the
    legacy 2-tuple contract.
    """
    return 503, {
        "ok": False,
        "code": "storage_busy",
        "trace_id": trace_id,
        "retry_after_seconds": 5,
    }, {"Retry-After": "5"}


def _is_sqlite_lock_error(exc: sqlite3.OperationalError) -> bool:
    """Match SQLite's "database is locked" lock-busy message.

    SQLite normalizes this string consistently across versions; we
    match case-insensitively for safety. Any other OperationalError
    (corruption, schema mismatch surfaced as OperationalError, etc.)
    is a genuine internal error and re-raises.
    """
    return "database is locked" in str(exc).lower()


# ─────────────────────────────────────────────────────────────────────
# Request-body cap (P9 / P18)
# ─────────────────────────────────────────────────────────────────────
# Mirrors the storage-layer cap so a request that COULD be parsed
# can also be persisted. Per § 6.1 + § 6.5: outer defense-in-depth.
REQUEST_BODY_LIMIT_BYTES = MAX_PAYLOAD_BYTES   # 1 MB


# ─────────────────────────────────────────────────────────────────────
# Storage + production C2 runner (singletons; tests can override)
# ─────────────────────────────────────────────────────────────────────
# Module-level lazy singletons. Tests inject their own via setter.
_storage: Optional[GateStateStorage] = None
_brief_storage: Optional[BriefStorage] = None


def _get_storage() -> GateStateStorage:
    global _storage
    if _storage is None:
        _storage = GateStateStorage()
    return _storage


def _get_brief_storage() -> BriefStorage:
    global _brief_storage
    if _brief_storage is None:
        _brief_storage = BriefStorage()
    return _brief_storage


def reset_storages_for_tests(
    *,
    gate_storage: Optional[GateStateStorage] = None,
    brief_storage: Optional[BriefStorage] = None,
) -> None:
    """Inject test-time storage instances. Called from tests' setUp."""
    global _storage, _brief_storage
    _storage = gate_storage
    _brief_storage = brief_storage


def _production_c2_runner(brief, feasibility_input):
    """Wrap C2's run_feasibility to match c2_runner protocol.

    Per § 5.1 + § 2.6: runner is injected at handler-construction time.
    """
    return _c2_orchestrator.run_feasibility(
        brief=brief,
        feasibility_input=feasibility_input,
    )


def _make_gate(c2_runner=None) -> ExtremeCaseGate:
    """Build a gate. Tests inject c2_runner; production uses default."""
    return ExtremeCaseGate(c2_runner=c2_runner or _production_c2_runner)


# ─────────────────────────────────────────────────────────────────────
# Body parsing + validation helpers (§ 6.1, § 6.5)
# ─────────────────────────────────────────────────────────────────────

def _decode_body_bytes(request_body: bytes | str) -> bytes:
    """Normalize to bytes for size measurement."""
    if isinstance(request_body, bytes):
        return request_body
    return request_body.encode("utf-8")


def _error_response(
    status: int,
    errors: list[dict],
    trace_id: str,
) -> tuple[int, dict]:
    """Build a structured error response per § 6.5."""
    return status, {
        "ok": False,
        "errors": errors,
        "trace_id": trace_id,
    }


def _make_field_error(field: str, code: str, message: str) -> dict:
    """One entry in the structured errors list."""
    return {"field": field, "code": code, "message": message}


def _parse_and_size_check(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[Optional[dict], Optional[tuple[int, dict]]]:
    """Run § 6.1 outer-layer checks: size cap then JSON parse.

    Returns (parsed_dict, None) on success, OR (None, error_response).
    """
    body_bytes = _decode_body_bytes(request_body)
    if len(body_bytes) > REQUEST_BODY_LIMIT_BYTES:
        return None, _error_response(
            400,
            [_make_field_error(
                "body", "too_large",
                f"body exceeds {REQUEST_BODY_LIMIT_BYTES}-byte limit (P9)",
            )],
            trace_id,
        )
    if len(body_bytes) == 0:
        return None, _error_response(
            400,
            [_make_field_error(
                "body", "empty", "request body required",
            )],
            trace_id,
        )
    try:
        body_str = body_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, _error_response(
            400,
            [_make_field_error(
                "body", "encoding",
                f"body not valid UTF-8: {str(e)[:120]}",
            )],
            trace_id,
        )
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError as e:
        return None, _error_response(
            400,
            [_make_field_error(
                "body", "json",
                f"invalid JSON: {str(e)[:120]}",
            )],
            trace_id,
        )
    if not isinstance(payload, dict):
        return None, _error_response(
            400,
            [_make_field_error(
                "body", "shape",
                "request body must be a JSON object at the top level",
            )],
            trace_id,
        )
    return payload, None


def _require_str(
    payload: dict, field: str, errors: list[dict],
) -> Optional[str]:
    """Pull a required non-empty string field; append to errors on miss."""
    value = payload.get(field)
    if value is None:
        errors.append(_make_field_error(
            field, "missing", f"{field} is required",
        ))
        return None
    if not isinstance(value, str):
        errors.append(_make_field_error(
            field, "type", f"{field} must be a string",
        ))
        return None
    if not value:
        errors.append(_make_field_error(
            field, "empty", f"{field} must be non-empty",
        ))
        return None
    return value


def _validate_iso8601(
    payload: dict, field: str, errors: list[dict],
) -> Optional[str]:
    """Pull a required ISO 8601 timestamp field; validate strictly.

    Added in D-067 round 3 (post-Session 24 code review item #4):
    timestamps are caller-supplied per spec § 2.5, so they are
    untrusted input subject to P18 (per-field validation). Reject
    malformed ISO 8601 with a structured 400 error rather than
    accepting silently and propagating the bad value into stored
    state + downstream computations like _add_24h_iso.

    Accepts: 'YYYY-MM-DDTHH:MM:SSZ' or 'YYYY-MM-DDTHH:MM:SS+HH:MM'
    or 'YYYY-MM-DDTHH:MM:SS.ffffffZ' (fromisoformat-compatible).
    Trailing 'Z' is normalized to '+00:00' for parsing per Python
    3.11+ semantics (which now accept Z natively, but we normalize
    for consistency across Python versions).

    Returns the original string on success (callers who need a
    datetime object should re-parse — keeping this function
    string-typed avoids accidental timezone bugs).
    """
    value = _require_str(payload, field, errors)
    if value is None:
        return None
    from datetime import datetime
    try:
        normalized = value.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
    except (ValueError, TypeError) as e:
        errors.append(_make_field_error(
            field, "format",
            f"{field} must be a valid ISO 8601 timestamp "
            f"(e.g. '2026-05-01T12:00:00Z'); got {value!r}: "
            f"{str(e)[:120]}",
        ))
        return None
    return value


# ─────────────────────────────────────────────────────────────────────
# P15: terminal-replay advisory field
# ─────────────────────────────────────────────────────────────────────

def _add_terminal_replay_advisory(cached_response: dict) -> dict:
    """Per § 6.6 P15: when a terminal token is hit AGAIN, the cached
    response is returned with `session_status="terminal_replay"` added
    at response-build time. The advisory is NOT stored — it's appended
    on each replay so client telemetry can detect lifecycle bugs.
    """
    out = dict(cached_response)
    out["session_status"] = "terminal_replay"
    return out


# ─────────────────────────────────────────────────────────────────────
# P7: wire-format is_done normalization
# ─────────────────────────────────────────────────────────────────────

_ABORT_REASONS = frozenset({
    GateTerminationReason.USER_ABORTED,
    GateTerminationReason.MAX_ITERATIONS_REACHED,
    GateTerminationReason.PER_CASE_LIMIT_REACHED,
})


def _wire_aborted(state: GateState) -> bool:
    """P7: aborted=true for USER_ABORTED, MAX_ITERATIONS, PER_CASE_LIMIT."""
    return (
        state.is_done
        and state.termination_reason in _ABORT_REASONS
    )


def _wire_paused(state: GateState) -> bool:
    """P7: paused=true for CBA_VERIFICATION_PAUSED."""
    return (
        state.is_done
        and state.termination_reason
        == GateTerminationReason.CBA_VERIFICATION_PAUSED
    )


# ─────────────────────────────────────────────────────────────────────
# Response builders (§ 5.1 — § 5.5 response shapes)
# ─────────────────────────────────────────────────────────────────────

def _build_check_response(
    state: GateState,
    request_id: str,
    trace_id: str,
) -> dict:
    """Build the /check response per § 5.1."""
    if state.is_done:
        # No-blockers terminal SUCCESS path
        return _build_terminal_success_response_for_check(
            state, request_id, trace_id,
        )
    # Has-blockers continuing path
    head = state.remaining_cases[0]
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "has_blockers": True,
        "is_done": False,
        "current_iteration": state.iteration_count,
        "current_case": head.to_dict(),
        "remaining_blocker_count": len(state.remaining_cases),
        "preflight": (
            state.preflight.to_dict()
            if state.preflight is not None else None
        ),
        "meta_banner": (
            state.meta_banner.to_dict()
            if state.meta_banner is not None else None
        ),
        "next_step": "USER_DECIDE",
        "trace_id": trace_id,
    }


def _build_terminal_success_response_for_check(
    state: GateState, request_id: str, trace_id: str,
) -> dict:
    """No-blockers SUCCESS at /check entry per § 5.1 first response shape."""
    assert state.final_resolved_brief is not None
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "has_blockers": False,
        "is_done": True,
        "aborted": False,
        "paused": False,
        "termination_reason": GateTerminationReason.SUCCESS.value,
        "mode": state.final_resolved_brief.mode.value,
        "resolved_brief": state.final_resolved_brief.to_dict(),
        "next_step": "PROCEED_TO_LAYOUT",
        "trace_id": trace_id,
    }


def _build_continuing_resolve_response(
    state: GateState,
    request_id: str,
    applied_brief_changes: tuple,
    trace_id: str,
) -> dict:
    """/resolve mid-flow continuation per § 5.2."""
    head = state.remaining_cases[0]
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": False,
        "current_iteration": state.iteration_count,
        "current_case": head.to_dict(),
        "remaining_blocker_count": len(state.remaining_cases),
        "transition_banner": (
            state.transition_banner.to_dict()
            if state.transition_banner is not None else None
        ),
        "meta_banner": (
            state.meta_banner.to_dict()
            if state.meta_banner is not None else None
        ),
        "applied_changes": [bc.to_dict() for bc in applied_brief_changes],
        "revised_brief_summary": _summarize_brief(state.current_brief),
        "next_step": "USER_DECIDE",
        "trace_id": trace_id,
    }


def _build_branch_c_error_response(
    state: GateState,
    request_id: str,
    trace_id: str,
) -> dict:
    """Branch C — BriefChangeIntegrityError surfaced as HTTP 200 per § 6.2.

    The user-experience error path is structured into the response;
    NOT a 4xx (4xx is only for malformed requests / lifecycle violations).
    """
    head = state.remaining_cases[0]
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": False,
        "current_iteration": state.iteration_count,
        "current_case": head.to_dict(),
        "remaining_blocker_count": len(state.remaining_cases),
        "last_error_message": state.last_error_message,
        "last_error_option_id": state.last_error_option_id,
        "failed_option_ids_for_current_case": sorted(
            state.failed_option_ids_for_current_case
        ),
        "next_step": "USER_DECIDE_AGAIN",
        "trace_id": trace_id,
    }


def _build_terminal_resolve_response(
    state: GateState,
    request_id: str,
    trace_id: str,
    *,
    email_sent_to: Optional[str] = None,
    fallback_at: Optional[str] = None,
) -> dict:
    """Terminal /resolve response per § 5.2 — branches by termination_reason."""
    reason = state.termination_reason
    base = {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": True,                                   # P7
        "aborted": _wire_aborted(state),                   # P7
        "paused": _wire_paused(state),                     # P7
        "termination_reason": reason.value,
        "trace_id": trace_id,
    }

    if reason == GateTerminationReason.SUCCESS:
        rb = state.final_resolved_brief
        assert rb is not None
        base.update({
            "mode": rb.mode.value,
            "resolved_brief": rb.to_dict(),
            "decision_log": rb.decision_log.to_dict(),
            "counterfactuals": [c.to_dict() for c in rb.counterfactuals],
            "next_step": "PROCEED_TO_LAYOUT",
        })
        return base

    if reason == GateTerminationReason.PREVIEW_MODE:
        rb = state.final_resolved_brief
        assert rb is not None
        base.update({
            "mode": rb.mode.value,
            "resolved_brief": rb.to_dict(),
            "decision_log": rb.decision_log.to_dict(),
            "counterfactuals": [c.to_dict() for c in rb.counterfactuals],
            "unresolved_blockers": [
                b.to_dict() for b in rb.unresolved_blockers
            ],
            "relaxed_constraints": list(rb.relaxed_constraints),
            "warning_message": (
                "This brief has unresolved blockers. The layout you'll "
                "see is for preview only and cannot be built without "
                "first resolving these."
            ),
            "next_step": "PROCEED_TO_PREVIEW_LAYOUT",
        })
        return base

    if reason in (
        GateTerminationReason.MAX_ITERATIONS_REACHED,
        GateTerminationReason.PER_CASE_LIMIT_REACHED,
    ):
        # rb is built by the orchestrator on these abort paths too;
        # but the response shape per § 5.2 surfaces decision_log + a
        # user_message + remaining_blockers (for UI display).
        rb = state.final_resolved_brief
        decision_log = (
            rb.decision_log.to_dict() if rb is not None else None
        )
        base.update({
            "decision_log": decision_log,
            "remaining_blockers": [
                c.to_dict() for c in state.remaining_cases
            ],
            "user_message": _abort_user_message(reason, state),
            "next_step": "RETURN_TO_BRIEF",
        })
        return base

    if reason == GateTerminationReason.CBA_VERIFICATION_PAUSED:
        base.update({
            "pause_reason": "AWAITING_CBA_VERIFICATION",
            "email_sent_to": email_sent_to,
            "fallback_at": fallback_at,
            "user_message": (
                "We've sent you a CBA verification checklist. "
                "Reply within 24 hours, or we'll resume assuming your "
                "plot is not a Continuous Building Area."
            ),
            "next_step": "WAIT_FOR_USER_RETURN",
        })
        return base

    # USER_ABORTED — per § 5.3 (abort endpoint), not § 5.2, but if this
    # ever lands here defensively we return a safe shape.
    if reason == GateTerminationReason.USER_ABORTED:
        rb = state.final_resolved_brief
        decision_log = (
            rb.decision_log.to_dict() if rb is not None else None
        )
        base.update({
            "saved_as_draft": True,
            "decision_log": decision_log,
            "next_step": "USER_ABORTED",
        })
        return base

    raise RuntimeError(
        f"unhandled termination_reason: {reason!r}"
    )


def _build_abort_response(
    state: GateState, request_id: str, trace_id: str,
) -> dict:
    """/abort terminal response per § 5.3."""
    rb = state.final_resolved_brief
    decision_log = (
        rb.decision_log.to_dict() if rb is not None else None
    )
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": True,                                   # P7
        "aborted": True,                                   # P7
        "paused": False,                                   # P7
        "saved_as_draft": True,
        "termination_reason": GateTerminationReason.USER_ABORTED.value,
        "decision_log": decision_log,
        "trace_id": trace_id,
    }


def _build_cba_verified_response(
    state: GateState,
    request_id: str,
    verification_result: str,
    trace_id: str,
) -> dict:
    """/cba-verified response per § 5.4."""
    next_step_map = {
        "CBA_CONFIRMED": "RESTART_BRIEF_WITH_PLOT_TYPE_CONTINUOUS",
        "NOT_CBA": "PROCEED_WITH_ORIGINAL_BRIEF",
        "STILL_UNSURE": "MANUAL_FOLLOWUP",
    }
    rb = state.final_resolved_brief
    decision_log = (
        rb.decision_log.to_dict() if rb is not None else None
    )
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": True,                                   # P7
        "aborted": False,
        "paused": False,
        "brief_restarting": verification_result == "CBA_CONFIRMED",
        "next_step": next_step_map[verification_result],
        "decision_log": decision_log,
        "trace_id": trace_id,
    }


def _build_cba_fallback_response(
    state: GateState, request_id: str, trace_id: str,
) -> dict:
    """/cba-fallback-continue response per § 5.5."""
    return {
        "ok": True,
        "session_token": state.session_id,
        "request_id": request_id,
        "is_done": True,                                   # P7
        "aborted": False,
        "paused": False,
        "brief_resuming": True,
        "assumed_plot_type": "DETACHED",
        "next_step": "RESUME_AT_LAST_CASE_WITH_NOT_CBA_ASSUMPTION",
        "user_message": (
            "Continuing assuming your plot is NOT a Continuous Building "
            "Area. You can correct this later if needed."
        ),
        "trace_id": trace_id,
    }


def _abort_user_message(
    reason: GateTerminationReason, state: GateState,
) -> str:
    if reason == GateTerminationReason.MAX_ITERATIONS_REACHED:
        return (
            f"After {state.iteration_count} attempts, we still can't "
            "reconcile your brief with the plot. You may want to revisit "
            "the brief or consider a different plot."
        )
    if reason == GateTerminationReason.PER_CASE_LIMIT_REACHED:
        return (
            "The same constraint keeps re-firing after several attempts. "
            "We've stopped to avoid an unproductive loop. Please revisit "
            "the brief or consider a different plot."
        )
    return ""


def _summarize_brief(brief: Brief) -> str:
    """One-line summary for revised_brief_summary in /resolve responses.

    Cheap to compute; informational only.
    """
    return (
        f"{brief.plot.width_m:g}×{brief.plot.depth_m:g}m, "
        f"{len(brief.floors)} floor(s), "
        f"budget {brief.budget_range.min_lakhs:g}-"
        f"{brief.budget_range.max_lakhs:g}L"
    )


# ─────────────────────────────────────────────────────────────────────
# Hook firing helpers (§ 7.3 P10 + P16 enforced at handler scope)
# ─────────────────────────────────────────────────────────────────────

def _fire_email_hook_safely(
    to_email: Optional[str],
    draft_token: str,
    fallback_at: str,
    *,
    trace_id: Optional[str] = None,
) -> None:
    """Best-effort fire (P10). Never propagates exceptions.

    S7b: trace_id added as keyword-only with default None for backward
    compat with any existing test fakes that haven't been updated.
    """
    try:
        _send_cba_checklist(
            to_email, draft_token, fallback_at, trace_id=trace_id,
        )
    except Exception as e:
        # Per § 7.4, hook MUST NOT raise. Defensive: log and swallow.
        logger.error(
            "c3a email hook raised: %s (state already saved per P10)", e,
        )


def _fire_scheduler_hook_safely(
    session_token: str,
    fire_at_unix: int,
    request_id: str,
    *,
    trace_id: Optional[str] = None,
) -> None:
    """Best-effort fire (P10). Never propagates exceptions.

    S7b § 7.4 + § 1.1 (1): signature is non-backward-compatible vs
    S7a. Old `(draft_token, fallback_at)` is gone — server-time
    UNIX `fire_at_unix` is the source of truth (P31), `request_id` is
    forwarded for P21 idempotency, `trace_id` for P29 propagation.
    """
    try:
        _schedule_fallback_invitation(
            session_token, fire_at_unix, request_id,
            trace_id=trace_id,
        )
    except Exception as e:
        logger.error(
            "c3a scheduler hook raised: %s (state already saved per P10)",
            e,
        )


# ─────────────────────────────────────────────────────────────────────
# § 5.1 — POST /api/extreme-case/check
# ─────────────────────────────────────────────────────────────────────

def _handle_check_inner(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST /api/extreme-case/check — initial entry from C2.

    Per § 5.1: caller has a Brief saved (brief_token) and asks whether
    extreme-case blockers exist. Returns either:
      - terminal SUCCESS (no blockers) — ResolvedBrief in response
      - in-progress state with first ExtremeCase to surface to user

    Idempotency for /check (P12): keyed on (brief_token, request_id).
    Same pair → same session_token. Different request_id with same
    brief_token: a new session is created (caller's choice).

    S7b § 5.3 wrapper: trace_id is now passed in by `handle_check`
    rather than generated locally. All return paths emit through the
    wrapper for instrumentation (P22 + P30).
    """
    # ─── P9 / § 6.1: outer body checks ──────────────────────────────
    payload, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    # ─── § 6.5: per-field validation ────────────────────────────────
    field_errors: list[dict] = []
    brief_token = _require_str(payload, "brief_token", field_errors)
    request_id = _require_str(payload, "request_id", field_errors)
    fi_payload = payload.get("feasibility_input")
    if fi_payload is not None and not isinstance(fi_payload, dict):
        field_errors.append(_make_field_error(
            "feasibility_input", "type",
            "feasibility_input must be a JSON object or null",
        ))
    if field_errors:
        return _error_response(400, field_errors, trace_id)

    storage = _get_storage()

    # ─── P12: brief→session uniqueness check ────────────────────────
    existing_session = storage.lookup_brief_session(
        brief_token=brief_token, request_id=request_id,
    )
    if existing_session is not None:
        # Same (brief_token, request_id) seen before — replay the cached
        # response. If terminal, also tag with session_status advisory.
        try:
            state, _last_req_id, last_response = storage.resume(
                existing_session,
            )
        except GateTokenNotFoundError:
            # Edge case: registration row exists but session row was
            # pruned (TTL on session expired separately). Treat as
            # missing — caller should retry with a fresh request_id.
            return _error_response(
                410,
                [_make_field_error(
                    "brief_token", "expired",
                    "session for (brief_token, request_id) has expired",
                )],
                trace_id,
            )
        if last_response is None:
            # Should not happen — /check always saves with cache. Defensive.
            return _error_response(
                500,
                [_make_field_error(
                    "internal", "missing_cache",
                    "session row exists but no cached response",
                )],
                trace_id,
            )
        if state.is_done:
            return 200, _add_terminal_replay_advisory(last_response)
        return 200, last_response

    # ─── Resolve brief_token → Brief ────────────────────────────────
    brief_storage = _get_brief_storage()
    try:
        brief_payload = brief_storage.resume(brief_token)
    except BriefTokenNotFoundError as e:
        return _error_response(
            410,
            [_make_field_error(
                "brief_token", "unknown_or_expired", str(e)[:200],
            )],
            trace_id,
        )
    try:
        brief = Brief.from_dict(brief_payload)
    except (KeyError, TypeError, ValueError) as e:
        return _error_response(
            400,
            [_make_field_error(
                "brief_token", "shape",
                f"stored brief is not a valid Brief: {str(e)[:160]}",
            )],
            trace_id,
        )

    # ─── Build optional FeasibilityInput ────────────────────────────
    feasibility_input: Optional[FeasibilityInput] = None
    if fi_payload is not None:
        try:
            feasibility_input = FeasibilityInput.from_dict(fi_payload)
        except (KeyError, TypeError, ValueError) as e:
            return _error_response(
                400,
                [_make_field_error(
                    "feasibility_input", "shape",
                    f"feasibility_input not parseable: {str(e)[:160]}",
                )],
                trace_id,
            )

    # ─── Generate fresh session_token + run gate.start ─────────────
    session_token = new_token()
    gate = _make_gate()
    initial_state = gate.start(
        session_id=session_token,
        brief=brief,
        feasibility_input=feasibility_input,
    )

    # ─── Build response ─────────────────────────────────────────────
    response = _build_check_response(initial_state, request_id, trace_id)

    # ─── P11: take per-token lock around save. (No prior state, but
    # ─── lock is cheap and protects against the rare two-concurrent-
    # ─── /check-with-same-fresh-token race — which shouldn't happen
    # ─── since session_token is freshly minted, but defense in depth.)
    with get_session_lock(session_token):
        try:
            storage.save(
                initial_state, request_id=request_id, response=response,
            )
        except PayloadTooLargeError as e:
            return _error_response(
                400,
                [_make_field_error(
                    "internal", "state_too_large",
                    f"serialized state exceeds size cap: {str(e)[:160]}",
                )],
                trace_id,
            )
        # P12: register the (brief_token, request_id) → session_token
        # mapping. If race lost (another /check with same pair beat
        # us), look up the winner and replay its response.
        registered = storage.register_brief_session(
            brief_token=brief_token,
            request_id=request_id,
            session_token=session_token,
        )
    if not registered:
        # Race lost — return the winner's response.
        winner_token = storage.lookup_brief_session(
            brief_token=brief_token, request_id=request_id,
        )
        if winner_token is None:
            # Pathological — registration claimed dup but lookup missed.
            return _error_response(
                500,
                [_make_field_error(
                    "internal", "race_inconsistent",
                    "register said collision but lookup empty",
                )],
                trace_id,
            )
        try:
            _state, _last_req_id, last_response = storage.resume(winner_token)
        except GateTokenNotFoundError:
            return _error_response(
                410,
                [_make_field_error(
                    "brief_token", "expired", "winner session expired",
                )],
                trace_id,
            )
        if last_response is not None:
            return 200, last_response
        # No cached response — shouldn't happen for /check; defensive
        return 200, response

    return 200, response


# ─────────────────────────────────────────────────────────────────────
# § 5.2 — POST /api/extreme-case/resolve  (most complex)
# ─────────────────────────────────────────────────────────────────────

def _handle_resolve_inner(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST /api/extreme-case/resolve — user picked an option.

    Per § 5.2: applies user's choice via ExtremeCaseGate, re-runs C2,
    returns next state. Six terminal paths + continuing path + Branch
    C error path.

    Implements P2 (idempotency replay), P3 (terminal → 200 + cached),
    P10 (save before hook), P11 (per-token lock), P13 (atomic co-write),
    P15 (terminal-replay advisory), P16 (no hook re-fire on replay).

    S7b § 5.3 wrapper: trace_id is now passed in by `handle_resolve`.
    """
    payload, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    field_errors: list[dict] = []
    session_token = _require_str(payload, "session_token", field_errors)
    request_id = _require_str(payload, "request_id", field_errors)
    case_id_str = _require_str(payload, "case_id", field_errors)
    chosen_option_id = _require_str(payload, "chosen_option_id", field_errors)
    user_acknowledged_at = _validate_iso8601(
        payload, "user_acknowledged_at", field_errors,
    )
    pma_payload = payload.get("preview_mode_acknowledgment")
    if pma_payload is not None and not isinstance(pma_payload, dict):
        field_errors.append(_make_field_error(
            "preview_mode_acknowledgment", "type",
            "preview_mode_acknowledgment must be a JSON object or null",
        ))
    if field_errors:
        return _error_response(400, field_errors, trace_id)

    # Validate case_id is a known ExtremeCaseId
    try:
        case_id = ExtremeCaseId(case_id_str)
    except ValueError:
        return _error_response(
            400,
            [_make_field_error(
                "case_id", "unknown_enum",
                f"unknown case_id: {case_id_str!r}",
            )],
            trace_id,
        )

    # Optional PreviewModeAcknowledgment
    preview_ack: Optional[PreviewModeAcknowledgment] = None
    if pma_payload is not None:
        try:
            preview_ack = PreviewModeAcknowledgment.from_dict(pma_payload)
        except (KeyError, TypeError, ValueError) as e:
            return _error_response(
                400,
                [_make_field_error(
                    "preview_mode_acknowledgment", "shape",
                    f"not parseable: {str(e)[:160]}",
                )],
                trace_id,
            )

    storage = _get_storage()

    # ─── P11: serialize read→compute→save under per-token lock ─────
    with get_session_lock(session_token):
        try:
            state, last_request_id, last_response = storage.resume(
                session_token,
            )
        except GateTokenNotFoundError as e:
            return _error_response(
                410,
                [_make_field_error(
                    "session_token", "unknown_or_expired", str(e)[:200],
                )],
                trace_id,
            )
        except SchemaVersionError as e:
            return _error_response(
                500,
                [_make_field_error(
                    "internal", "schema_version", str(e)[:200],
                )],
                trace_id,
            )

        # ─── P2: idempotency replay (BEFORE P3 terminal check, per
        # ─── § 5.2 ordering: idempotency cache checked first) ─────
        if last_request_id == request_id and last_response is not None:
            # Verbatim cached response. Hooks NOT re-fired (P16).
            return 200, last_response

        # ─── P3 + P15: terminal token → cached response with
        # ─── session_status="terminal_replay" advisory ────────────
        if state.is_done:
            if last_response is None:
                # Should not happen for terminated sessions; defensive
                return _error_response(
                    500,
                    [_make_field_error(
                        "internal", "missing_terminal_cache",
                        "terminal session has no cached response",
                    )],
                    trace_id,
                )
            return 200, _add_terminal_replay_advisory(last_response)

        # ─── Compute new state via S6 orchestrator ────────────────
        gate = _make_gate()
        previous_brief = state.current_brief
        try:
            new_state = gate.apply_user_decision(
                state=state,
                case_id=case_id,
                chosen_option_id=chosen_option_id,
                user_acknowledged_at=user_acknowledged_at,
                preview_mode_acknowledgment=preview_ack,
            )
        except ValueError as e:
            # § 5.2 step 6: bad case_id / option_id / empty timestamp /
            # missing PreviewMode ack → 400 with structured errors.
            return _error_response(
                400,
                [_make_field_error(
                    "request", "invalid",
                    f"orchestrator rejected: {str(e)[:200]}",
                )],
                trace_id,
            )

        # ─── Compute applied_changes for response shape ───────────
        applied_changes = _compute_applied_changes(
            previous_brief=previous_brief,
            new_state=new_state,
        )

        # ─── Build response ────────────────────────────────────────
        response = _build_resolve_response(
            new_state=new_state,
            request_id=request_id,
            trace_id=trace_id,
            applied_changes=applied_changes,
        )

        # ─── P10 + P13: save state+cache atomically FIRST ─────────
        try:
            storage.save_existing(
                session_token, new_state,
                request_id=request_id, response=response,
            )
        except PayloadTooLargeError as e:
            return _error_response(
                400,
                [_make_field_error(
                    "internal", "state_too_large",
                    f"serialized state exceeds cap: {str(e)[:160]}",
                )],
                trace_id,
            )

        # ─── P10: NOW fire hooks (best-effort, post-save). Only on the
        # ─── CBA_VERIFICATION_PAUSED branch per § 5.2 + § 7.3.
        if (
            new_state.is_done
            and new_state.termination_reason
            == GateTerminationReason.CBA_VERIFICATION_PAUSED
        ):
            _fire_email_hook_safely(
                to_email=new_state.current_brief.user_email,
                draft_token=session_token,
                fallback_at=response.get("fallback_at") or "",
                trace_id=trace_id,
            )
            # S7b § 7.4 + P31: server-time UNIX is the authoritative
            # firing time; the user-display `fallback_at` ISO string
            # in the response body stays caller-relative for UI use.
            _fire_scheduler_hook_safely(
                session_token=session_token,
                fire_at_unix=int(time.time()) + 86400,
                request_id=request_id,
                trace_id=trace_id,
            )

    return 200, response


def _compute_applied_changes(
    previous_brief: Brief, new_state: GateState,
) -> tuple:
    """Approximate the user-facing applied_changes list.

    The orchestrator already applied them; we report the most recent
    decision's brief_changes via the chosen option that won the round.
    """
    # The most recent decision is the last element of decisions_so_far
    # (§ S6: pure functional orchestrator appends one ExtremeDecision
    # per /resolve call on Branches A/B/D).
    if not new_state.decisions_so_far:
        return ()
    last_decision = new_state.decisions_so_far[-1]
    chosen = next(
        (
            opt for opt in last_decision.presented_options
            if opt.option_id == last_decision.chosen_option_id
        ),
        None,
    )
    if chosen is None:
        return ()
    return chosen.requires_brief_change


def _build_resolve_response(
    new_state: GateState,
    request_id: str,
    trace_id: str,
    applied_changes: tuple,
) -> dict:
    """Pick the right /resolve response shape per termination state."""
    if new_state.is_done:
        # Determine fallback_at if CBA pause; spec § 5.2 uses it as the
        # 24h-from-pause marker. The user_acknowledged_at is the most
        # recent decision's timestamp; fallback = +24h. Caller-supplied
        # timestamps (§ 2.5) — we don't compute fresh ones here.
        fallback_at = ""
        if (
            new_state.termination_reason
            == GateTerminationReason.CBA_VERIFICATION_PAUSED
            and new_state.decisions_so_far
        ):
            # Best-effort: take the last decision timestamp + 24h.
            # Without dateutil we do simple ISO-string addition by
            # delegating to an internal helper.
            fallback_at = _add_24h_iso(
                new_state.decisions_so_far[-1].user_acknowledged_at,
            )
        return _build_terminal_resolve_response(
            new_state, request_id, trace_id,
            email_sent_to=new_state.current_brief.user_email,
            fallback_at=fallback_at or None,
        )
    # Non-terminal: continuing OR Branch C error
    if new_state.last_error_message is not None:
        return _build_branch_c_error_response(
            new_state, request_id, trace_id,
        )
    return _build_continuing_resolve_response(
        new_state, request_id, applied_changes, trace_id,
    )


def _add_24h_iso(iso_ts: str) -> str:
    """Add 24 hours to a strictly-validated ISO 8601 timestamp.

    Strictness contract (D-067 round 3, code review item #4): the
    caller has already validated `iso_ts` via `_validate_iso8601` at
    the API trust boundary (P18). This function therefore RAISES on
    any parse failure rather than silently returning the input —
    silent recovery here would mask data-corruption bugs (e.g. a
    GateState row deserialized from a future schema version slipping
    through P8 checks). Exceptions are caught at the handler scope
    by the surrounding try/except patterns; if they ever propagate,
    they correctly surface as 500 (truly internal) rather than as a
    valid-looking but wrong fallback_at field in the response.
    """
    from datetime import datetime, timedelta, timezone
    # Normalize trailing Z for fromisoformat (consistent across
    # Python versions; 3.11+ accept Z natively).
    normalized = iso_ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    plus24 = dt + timedelta(hours=24)
    return plus24.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ─────────────────────────────────────────────────────────────────────
# § 5.3 — POST /api/extreme-case/abort
# ─────────────────────────────────────────────────────────────────────

def _handle_abort_inner(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST /api/extreme-case/abort — user clicked "Save and exit".

    Per § 5.3: terminal USER_ABORTED state. Idempotent across replays
    via P2/P3.

    S7b § 5.3 wrapper: trace_id is now passed in by `handle_abort`.
    """
    payload, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    field_errors: list[dict] = []
    session_token = _require_str(payload, "session_token", field_errors)
    request_id = _require_str(payload, "request_id", field_errors)
    if field_errors:
        return _error_response(400, field_errors, trace_id)
    # `reason` is optional free-form; ignored by S6, logged here.
    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        return _error_response(
            400,
            [_make_field_error(
                "reason", "type", "reason must be a string or absent",
            )],
            trace_id,
        )

    storage = _get_storage()

    with get_session_lock(session_token):
        try:
            state, last_request_id, last_response = storage.resume(
                session_token,
            )
        except GateTokenNotFoundError as e:
            return _error_response(
                410,
                [_make_field_error(
                    "session_token", "unknown_or_expired", str(e)[:200],
                )],
                trace_id,
            )

        # P2 idempotency
        if last_request_id == request_id and last_response is not None:
            return 200, last_response

        # P3 terminal token → cached + advisory
        if state.is_done:
            if last_response is None:
                return _error_response(
                    500,
                    [_make_field_error(
                        "internal", "missing_terminal_cache",
                        "terminal session has no cached response",
                    )],
                    trace_id,
                )
            return 200, _add_terminal_replay_advisory(last_response)

        gate = _make_gate()
        try:
            new_state = gate.apply_user_abort(state)
        except ValueError as e:
            return _error_response(
                400,
                [_make_field_error(
                    "request", "invalid",
                    f"orchestrator rejected: {str(e)[:200]}",
                )],
                trace_id,
            )

        if reason:
            logger.info(
                "c3a abort reason logged: session=%s reason=%s",
                session_token, reason[:200],
            )

        response = _build_abort_response(new_state, request_id, trace_id)

        try:
            storage.save_existing(
                session_token, new_state,
                request_id=request_id, response=response,
            )
        except PayloadTooLargeError as e:
            return _error_response(
                400,
                [_make_field_error(
                    "internal", "state_too_large",
                    f"serialized state exceeds cap: {str(e)[:160]}",
                )],
                trace_id,
            )

    return 200, response


# ─────────────────────────────────────────────────────────────────────
# § 5.4 — POST /api/extreme-case/cba-verified
# ─────────────────────────────────────────────────────────────────────

_VALID_CBA_RESULTS = frozenset({"CBA_CONFIRMED", "NOT_CBA", "STILL_UNSURE"})


def _handle_cba_verified_inner(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST /api/extreme-case/cba-verified — user answered the checklist.

    Per § 5.4: state must be in CBA_VERIFICATION_PAUSED. Maps the
    verification_result to a next-step instruction. C3a does NOT
    auto-restart C1; it returns the instruction.

    S7b § 5.3 wrapper: trace_id is now passed in by `handle_cba_verified`.
    """
    payload, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    field_errors: list[dict] = []
    session_token = _require_str(payload, "session_token", field_errors)
    request_id = _require_str(payload, "request_id", field_errors)
    verification_result = _require_str(
        payload, "verification_result", field_errors,
    )
    if field_errors:
        return _error_response(400, field_errors, trace_id)

    if verification_result not in _VALID_CBA_RESULTS:
        return _error_response(
            400,
            [_make_field_error(
                "verification_result", "unknown_enum",
                f"verification_result must be one of "
                f"{sorted(_VALID_CBA_RESULTS)}; got "
                f"{verification_result!r}",
            )],
            trace_id,
        )

    storage = _get_storage()

    with get_session_lock(session_token):
        try:
            state, last_request_id, last_response = storage.resume(
                session_token,
            )
        except GateTokenNotFoundError as e:
            return _error_response(
                410,
                [_make_field_error(
                    "session_token", "unknown_or_expired", str(e)[:200],
                )],
                trace_id,
            )

        # P2 idempotency
        if last_request_id == request_id and last_response is not None:
            return 200, last_response

        # § 5.4 step 2: state-precondition checks
        if state.is_done:
            # If the existing terminal reason is CBA_VERIFICATION_PAUSED
            # this is the "still paused but nothing new to do" replay
            # path → 200 with cached + advisory. Other terminals also
            # 200 (idempotent — different terminal already happened).
            if last_response is None:
                return _error_response(
                    500,
                    [_make_field_error(
                        "internal", "missing_terminal_cache",
                        "terminal session has no cached response",
                    )],
                    trace_id,
                )
            # Special case: CBA_VERIFICATION_PAUSED is the EXPECTED
            # terminal state at /cba-verified entry. We want to advance
            # it (build a verified-result response) IF this is a fresh
            # request_id. The state-machine allows /cba-verified to
            # transition out of CBA_VERIFICATION_PAUSED at the C3a
            # level even though state.is_done is True at S6.
            if (
                state.termination_reason
                == GateTerminationReason.CBA_VERIFICATION_PAUSED
            ):
                # Build the response per § 5.4 (treats CBA pause as the
                # required precondition state). Save updates the cache
                # so subsequent calls with a different request_id will
                # see the most-recent verified response, and same-
                # request_id calls replay verbatim per P2.
                response = _build_cba_verified_response(
                    state, request_id, verification_result, trace_id,
                )
                try:
                    storage.save_existing(
                        session_token, state,
                        request_id=request_id, response=response,
                    )
                except PayloadTooLargeError as e:
                    return _error_response(
                        400,
                        [_make_field_error(
                            "internal", "state_too_large",
                            f"serialized state exceeds cap: "
                            f"{str(e)[:160]}",
                        )],
                        trace_id,
                    )
                return 200, response
            # Other terminal — return cached with advisory (idempotent
            # at session level; nothing to do).
            return 200, _add_terminal_replay_advisory(last_response)

        # § 5.4: non-terminal mid-flow → 409 CONFLICT (lifecycle violation)
        return _error_response(
            409,
            [_make_field_error(
                "session_token", "lifecycle",
                "session is not in CBA_VERIFICATION_PAUSED; "
                "cba-verified can only be called on a paused session",
            )],
            trace_id,
        )


# ─────────────────────────────────────────────────────────────────────
# § 5.5 — POST /api/extreme-case/cba-fallback-continue
# ─────────────────────────────────────────────────────────────────────

def _handle_cba_fallback_continue_inner(
    request_body: bytes | str,
    trace_id: str,
) -> tuple[int, dict]:
    """POST /api/extreme-case/cba-fallback-continue.

    Per § 5.5: 24h-after-pause fallback. Conservative default — assumes
    plot is NOT a Continuous Building Area (DETACHED). Returns the
    instruction; C1 layer is responsible for restarting.

    S7b § 5.3 wrapper: trace_id is now passed in by
    `handle_cba_fallback_continue`, which sources it from the inbound
    `X-Trace-Id` header (after P34 validation) so the original
    pause-time trace is preserved across the 24h boundary.
    """
    payload, err = _parse_and_size_check(request_body, trace_id)
    if err is not None:
        return err

    field_errors: list[dict] = []
    session_token = _require_str(payload, "session_token", field_errors)
    request_id = _require_str(payload, "request_id", field_errors)
    if field_errors:
        return _error_response(400, field_errors, trace_id)

    storage = _get_storage()

    with get_session_lock(session_token):
        try:
            state, last_request_id, last_response = storage.resume(
                session_token,
            )
        except GateTokenNotFoundError as e:
            return _error_response(
                410,
                [_make_field_error(
                    "session_token", "unknown_or_expired", str(e)[:200],
                )],
                trace_id,
            )

        # P2 idempotency
        if last_request_id == request_id and last_response is not None:
            return 200, last_response

        if state.is_done:
            if last_response is None:
                return _error_response(
                    500,
                    [_make_field_error(
                        "internal", "missing_terminal_cache",
                        "terminal session has no cached response",
                    )],
                    trace_id,
                )
            if (
                state.termination_reason
                == GateTerminationReason.CBA_VERIFICATION_PAUSED
            ):
                # Build fallback-continue response and cache it.
                response = _build_cba_fallback_response(
                    state, request_id, trace_id,
                )
                try:
                    storage.save_existing(
                        session_token, state,
                        request_id=request_id, response=response,
                    )
                except PayloadTooLargeError as e:
                    return _error_response(
                        400,
                        [_make_field_error(
                            "internal", "state_too_large",
                            f"serialized state exceeds cap: "
                            f"{str(e)[:160]}",
                        )],
                        trace_id,
                    )
                return 200, response
            # Other terminal — idempotent no-op
            return 200, _add_terminal_replay_advisory(last_response)

        # Non-terminal mid-flow → 409 CONFLICT (same as § 5.4)
        return _error_response(
            409,
            [_make_field_error(
                "session_token", "lifecycle",
                "session is not in CBA_VERIFICATION_PAUSED; "
                "cba-fallback-continue can only be called on a paused "
                "session",
            )],
            trace_id,
        )


# ─────────────────────────────────────────────────────────────────────
# S7b § 5.3 — Public handler wrappers
# ─────────────────────────────────────────────────────────────────────
# Five thin wrappers around the `_handle_X_inner` business logic.
# Each wrapper:
#   1. Mints a trace_id (cba-fallback-continue resolves from header).
#   2. Calls the inner with try/except for sqlite3.OperationalError
#      to translate SQLite "database is locked" into HTTP 503 +
#      Retry-After (§ 6.2). All other exceptions propagate.
#   3. Emits the c3a.endpoint structured-log metric in `finally`,
#      regardless of how the inner returned (success / 4xx / 5xx /
#      503 / propagated exception).
#
# Backward-compat: the wrappers preserve the legacy 2-tuple return
# contract on every path EXCEPT the storage_busy 503, which returns
# a 3-tuple (status, body, headers). server.py is updated in Phase 8
# to honour the third element.


def handle_check(request_body: bytes | str):
    """POST /api/extreme-case/check (§ 5.1)."""
    t0 = time.monotonic()
    trace_id = _new_trace_id()
    status = 0
    error_code = None
    try:
        try:
            status, body = _handle_check_inner(request_body, trace_id)
            error_code = (
                body.get("code") if isinstance(body, dict) else None
            )
            return status, body
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc):
                status = 503
                error_code = "storage_busy"
                return _build_storage_busy_response(trace_id)
            raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _emit_handler_metric(
            "check", status, duration_ms, trace_id,
            _classify_error(error_code, trace_id, "check"),
        )


def handle_resolve(request_body: bytes | str):
    """POST /api/extreme-case/resolve (§ 5.2)."""
    t0 = time.monotonic()
    trace_id = _new_trace_id()
    status = 0
    error_code = None
    try:
        try:
            status, body = _handle_resolve_inner(request_body, trace_id)
            error_code = (
                body.get("code") if isinstance(body, dict) else None
            )
            return status, body
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc):
                status = 503
                error_code = "storage_busy"
                return _build_storage_busy_response(trace_id)
            raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _emit_handler_metric(
            "resolve", status, duration_ms, trace_id,
            _classify_error(error_code, trace_id, "resolve"),
        )


def handle_abort(request_body: bytes | str):
    """POST /api/extreme-case/abort (§ 5.3)."""
    t0 = time.monotonic()
    trace_id = _new_trace_id()
    status = 0
    error_code = None
    try:
        try:
            status, body = _handle_abort_inner(request_body, trace_id)
            error_code = (
                body.get("code") if isinstance(body, dict) else None
            )
            return status, body
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc):
                status = 503
                error_code = "storage_busy"
                return _build_storage_busy_response(trace_id)
            raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _emit_handler_metric(
            "abort", status, duration_ms, trace_id,
            _classify_error(error_code, trace_id, "abort"),
        )


def handle_cba_verified(request_body: bytes | str):
    """POST /api/extreme-case/cba-verified (§ 5.4)."""
    t0 = time.monotonic()
    trace_id = _new_trace_id()
    status = 0
    error_code = None
    try:
        try:
            status, body = _handle_cba_verified_inner(
                request_body, trace_id,
            )
            error_code = (
                body.get("code") if isinstance(body, dict) else None
            )
            return status, body
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc):
                status = 503
                error_code = "storage_busy"
                return _build_storage_busy_response(trace_id)
            raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _emit_handler_metric(
            "cba_verified", status, duration_ms, trace_id,
            _classify_error(error_code, trace_id, "cba_verified"),
        )


def handle_cba_fallback_continue(
    request_body: bytes | str,
    headers: Optional[Mapping[str, str]] = None,
):
    """POST /api/extreme-case/cba-fallback-continue (§ 5.5).

    UNIQUE WRAPPER — accepts inbound `X-Trace-Id` (P34 validated).

    The `headers` param defaults to None for backward compat with
    callers that don't yet pass headers (existing tests + Phase-8
    server wiring). When None or empty, trace_id is minted fresh.

    S8 P43 (§ 2.8): trace_id is decoupled into server_trace_id
    (canonical, freshly minted on every call) and client_trace_id
    (correlation hint, validated from the inbound header when
    present). Per the § 2.8 mapping table:
      - server_trace_id → metric `c3a.endpoint` line, server-side
        error logs, internal handler trace_id arg.
      - client_trace_id → response body `trace_id` field
        (preserves existing scheduler-tick round-trip semantics)
        and UI error display.
      - structured request log line includes BOTH (separate fields).
    When client_trace_id is None (no/invalid header), the response
    body falls back to server_trace_id so the user-facing surface
    is never empty.
    """
    t0 = time.monotonic()
    server_trace_id, client_trace_id = _resolve_trace_pair(
        headers.get("X-Trace-Id") if headers else None,
    )
    response_trace = client_trace_id or server_trace_id

    # Structured request log — both fields per P43 mapping table.
    logger.info(
        "c3a.fallback_continue.request "
        "server_trace_id=%s client_trace_id=%s",
        server_trace_id,
        client_trace_id or "null",
    )

    status = 0
    error_code = None
    try:
        try:
            # Inner handler operates on server_trace_id (canonical).
            status, body = _handle_cba_fallback_continue_inner(
                request_body, server_trace_id,
            )
            error_code = (
                body.get("code") if isinstance(body, dict) else None
            )
            # P43: rewrite response body trace_id to the client-facing
            # value (correlation hint). Inner produced server_trace_id
            # in the body; we swap to client_or_server here so the
            # user-visible "share this code with support" UX matches
            # the URL-supplied trace when valid.
            if isinstance(body, dict):
                body = {**body, "trace_id": response_trace}
            return status, body
        except sqlite3.OperationalError as exc:
            if _is_sqlite_lock_error(exc):
                status = 503
                error_code = "storage_busy"
                s_status, s_body, s_headers = (
                    _build_storage_busy_response(server_trace_id)
                )
                if isinstance(s_body, dict):
                    s_body = {**s_body, "trace_id": response_trace}
                return s_status, s_body, s_headers
            raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        # Metric line uses server_trace_id (canonical for ops).
        _emit_handler_metric(
            "cba_fallback_continue",
            status, duration_ms, server_trace_id,
            _classify_error(
                error_code, server_trace_id, "cba_fallback_continue",
            ),
        )


__all__ = [
    "handle_check",
    "handle_resolve",
    "handle_abort",
    "handle_cba_verified",
    "handle_cba_fallback_continue",
    "reset_storages_for_tests",
    "REQUEST_BODY_LIMIT_BYTES",
]
