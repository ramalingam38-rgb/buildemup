"""Phase-payload JSON serializer (S57 follow-up #12).

The MasterOrchestrator captures rich phase outputs (PlotAnalysis,
candidate tuples, PlacementBatchResult, DualDrawingBundle, etc.) as
`PhaseResult.payload`. The HTTP endpoint historically returned only
per-phase status + metadata — leaving the actual outputs invisible to
callers who can't import the Python dataclasses directly.

This module ships `serialize_phase_payload(phase_id, payload)` —
a recursive dataclass-aware to-JSON converter that:
  - Walks frozen dataclasses via `dataclasses.fields()` and emits a
    `__type__` tag so consumers can disambiguate.
  - Converts Enums (incl. StrEnum) to their `.value`.
  - Converts tuples and sets to lists (deterministic order for sets).
  - Treats dict keys as strings.
  - Caps recursion depth so accidentally-cyclic graphs return a
    truncation marker instead of stack-overflowing.
  - Falls back to a truncated `repr()` for anything else (numpy
    arrays, shapely geometries, etc.) — UI consumers see *something*
    even when the type isn't trivially JSON-able.

Per-phase shaping: callers can opt in to slim payloads (drop large
candidate tuples) by passing `max_collection_items`. Default is None
(no truncation), keeping the response fully traceable for the UI
follow-up #14.
"""
from __future__ import annotations

import dataclasses
import math
from enum import Enum
from typing import Any, Optional


# Conservative defaults — UI rendering doesn't need every dataclass
# field 12 levels deep; debugging does. Bumpable per-call.
_DEFAULT_MAX_DEPTH: int = 8
_DEFAULT_REPR_CAP: int = 400


def serialize_phase_payload(
    phase_id: str,
    payload: Any,
    *,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_collection_items: Optional[int] = None,
) -> Any:
    """Convert a phase payload to a JSON-safe value.

    Args:
        phase_id: The phase identifier; unused at the conversion level
            but reserved for future per-phase shaping rules.
        payload: The PhaseResult.payload object. May be None (SKIPPED /
            STUB phases) — in that case None is returned.
        max_depth: Hard cap on recursion depth. Exceeding this returns
            a truncation marker. Default 8 (plenty for our nests).
        max_collection_items: If set, lists/tuples beyond this length
            are truncated with a marker indicating the dropped count.
            None means no truncation.

    Returns:
        A value json.dumps() can serialize: None, bool, int, float,
        str, list, or dict.
    """
    _ = phase_id  # reserved for future per-phase shaping
    if payload is None:
        return None
    return _to_jsonable(
        payload,
        depth=0,
        max_depth=max_depth,
        max_collection_items=max_collection_items,
    )


def _to_jsonable(
    obj: Any,
    *,
    depth: int,
    max_depth: int,
    max_collection_items: Optional[int],
) -> Any:
    """Recursive worker. Returns a JSON-safe representation of `obj`."""
    if depth > max_depth:
        return {
            "__truncated__": "max_depth",
            "type": type(obj).__name__,
        }

    # ─── Primitives ──────────────────────────────────────────────
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        # NaN / Inf aren't valid JSON; surface them as strings so the
        # UI can still display "NaN" rather than crash json.dumps.
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj
    if isinstance(obj, str):
        return obj

    # ─── Enums (including StrEnum) ───────────────────────────────
    if isinstance(obj, Enum):
        # StrEnum members already compare/serialize as their value,
        # but explicit .value makes intent obvious for consumers.
        return obj.value

    # ─── Bytes ───────────────────────────────────────────────────
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return {"__bytes_len__": len(obj)}

    # ─── Frozen / regular dataclass instances ────────────────────
    # Order matters — must come before generic "object" fallback.
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {"__type__": type(obj).__name__}
        for field in dataclasses.fields(obj):
            try:
                value = getattr(obj, field.name)
            except Exception as exc:  # noqa: BLE001
                result[field.name] = {
                    "__unreadable__": f"{type(exc).__name__}: {exc}",
                }
                continue
            result[field.name] = _to_jsonable(
                value,
                depth=depth + 1,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
            )
        return result

    # ─── Collections ─────────────────────────────────────────────
    if isinstance(obj, (list, tuple)):
        return _serialize_sequence(
            obj,
            depth=depth + 1,
            max_depth=max_depth,
            max_collection_items=max_collection_items,
            kind="sequence",
        )
    if isinstance(obj, (set, frozenset)):
        # Deterministic order — sort by string repr for stability.
        ordered = sorted(obj, key=lambda v: repr(v))
        return _serialize_sequence(
            ordered,
            depth=depth + 1,
            max_depth=max_depth,
            max_collection_items=max_collection_items,
            kind="set",
        )
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key = k if isinstance(k, str) else _stringify_dict_key(k)
            out[key] = _to_jsonable(
                v,
                depth=depth + 1,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
            )
        return out

    # ─── Fallback: truncated repr ────────────────────────────────
    text = repr(obj)
    if len(text) > _DEFAULT_REPR_CAP:
        text = text[: _DEFAULT_REPR_CAP - 3] + "..."
    return {"__repr__": text, "type": type(obj).__name__}


def _serialize_sequence(
    seq,
    *,
    depth: int,
    max_depth: int,
    max_collection_items: Optional[int],
    kind: str,
) -> Any:
    """Serialize a list/tuple/sorted set; optionally cap length."""
    full_len = len(seq)
    if max_collection_items is not None and full_len > max_collection_items:
        kept = list(seq)[:max_collection_items]
        return {
            "__truncated__": "max_collection_items",
            "kind": kind,
            "total_len": full_len,
            "kept": [
                _to_jsonable(
                    item,
                    depth=depth,
                    max_depth=max_depth,
                    max_collection_items=max_collection_items,
                )
                for item in kept
            ],
        }
    return [
        _to_jsonable(
            item,
            depth=depth,
            max_depth=max_depth,
            max_collection_items=max_collection_items,
        )
        for item in seq
    ]


def _stringify_dict_key(key: Any) -> str:
    """Convert non-string dict keys to a stable string form."""
    if isinstance(key, Enum):
        return key.value
    if isinstance(key, (int, float, bool)):
        return str(key)
    if isinstance(key, tuple):
        # Common in coordinate-keyed dicts.
        return "(" + ",".join(_stringify_dict_key(k) for k in key) + ")"
    return repr(key)


__all__ = ["serialize_phase_payload"]
