"""
BuildemUp — Component 11a — canonical structural source signature (B-NEW-U)
==============================================================================

Per S39 critique walk F3: the orchestrator's previous
``_derive_source_signature(source, index) = SHA256(repr(source) + index)``
was acknowledged as Sub-4 simplification. F3 made the expansion request
explicit:

    Use canonical deterministic serialization over the ancestry chain:
    - room graph
    - adjacency matrix
    - circulation graph
    - wet-zone anchors
    - staircase metadata
    Then SHA256(canonical_serialization).

This module provides:

  * ``derive_canonical_signature(source)`` — strict walk of the v1.0
    ancestry chain, hashing structural-only fields. Real
    ``WetZonePlannedCandidate`` inputs use this.

  * ``derive_signature(source, index)`` — dispatcher. Real candidates
    → canonical path. Synthetic test fixtures → ``repr+index`` fallback
    (same as Sub-4).

  * Backwards-compatible: existing ``_derive_source_signature`` in
    orchestrator.py becomes a thin wrapper that delegates here.

== What "structural" means ==

Structural fields are those that:
  (a) are deterministic for a given input (no timestamps, no
      provenance, no scoring), AND
  (b) participate in mutation outcomes (room positions, zone bands,
      corridor topology, staircase placement, wet-wall assignment).

The signature deliberately EXCLUDES:
  - Provenance fields (derived_at, trace_id, _kb_version)
  - Score breakdowns (final scoring is in C11b, not in source state)
  - Diagnostic flags (low_confidence, score_margin)
  - Underscore-prefixed fields (per spec § 2.4 _observational_runtime_ms
    convention — excluded from replay hashes)

Two candidates with identical structural state but different scores
or different derivation timestamps produce IDENTICAL signatures —
which is exactly what cache-correctness across upstream evolutions
requires.

== Cache-key consequences ==

Per Sub-3's ``DeepMutationCacheKey`` design, the cache key is
``(operator, source_signature_hash, config_hash)``. With B-NEW-U:

  * Two structurally-identical candidates → same signature → cache hit
  * Same structural state computed at different times → cache hit
  * Repr-equal but structurally-different inputs (rare; from frozen
    dataclass equality semantics) → different signature, not collision
"""
from __future__ import annotations

import hashlib
from dataclasses import fields, is_dataclass
from typing import Any

from buildemup.components.c11a.candidate_context import (
    CandidateContextSchemaError,
    is_real_wet_zone_candidate,
)


# =============================================================================
# Public API
# =============================================================================


def derive_signature(source: Any, source_index: int) -> str:
    """Dispatcher — canonical for real candidates, repr+index for
    synthetic.

    Returns:
        16-hex-char SHA256 prefix of the candidate's structural
        signature. Format matches ``derive_variant_id()`` in
        operators/_base.py for visual consistency.
    """
    if is_real_wet_zone_candidate(source):
        try:
            return derive_canonical_signature(source)
        except CandidateContextSchemaError:
            # Schema drift on a real candidate — fall back to
            # repr+index so the orchestrator can still produce SOME
            # signature (the candidate-context extractor will surface
            # the real schema error per-candidate elsewhere).
            return _derive_repr_index_signature(source, source_index)
    return _derive_repr_index_signature(source, source_index)


def derive_canonical_signature(source: Any) -> str:
    """Per B-NEW-U: structural-only canonical signature.

    Walks the v1.0 ancestry chain extracting structural-only fields
    and hashing the canonical-serialised result. The walk is bounded
    by an EXPLICIT_PATH list — adding a new structural field to one
    of the upstream schemas requires updating this list (intentional
    review gate per F-v4-2 source-constant policy).

    Per Spec #4 v1.6 § 3.5: multi-floor dispatch added. If source is
    a real ``MultiFloorWetZonePlannedCandidate`` (detected via the
    ``__multi_floor_candidate__`` marker attribute), delegate to
    ``_derive_multi_floor_canonical_signature`` which aggregates per-
    floor signatures with the wrapper-level schema prefix.

    Args:
        source: a real ``WetZonePlannedCandidate`` or
            ``MultiFloorWetZonePlannedCandidate``.

    Returns:
        16-hex-char SHA256 prefix.

    Raises:
        ``CandidateContextSchemaError`` if the v1.0 ancestry chain is
        broken (delegates to walk helpers).
    """
    # Spec #4 v1.6 § 3.5: multi-floor dispatch via marker-attribute.
    # Import here to avoid module-load circular dependency with c11a's
    # candidate_context (which imports source_signature in some paths).
    from buildemup.components.c11a.candidate_context import (
        is_real_multi_floor_candidate,
    )
    if is_real_multi_floor_candidate(source):
        return _derive_multi_floor_canonical_signature(source)

    parts: list[str] = []

    # 1. Topology kind (from oriented → topology candidate)
    parts.append(f"topology_kind={_get_path(source, _PATH_TOPOLOGY_KIND_VALUE)}")

    # 2. Zone bands — Mapping[ZoneBand, PlotOrientation]; canonical-
    #    serialise as sorted (band_value, direction_value) pairs.
    zone_bands = _get_path(source, _PATH_ZONE_BANDS, allow_missing=True)
    if zone_bands is not None:
        zb_serial = ",".join(
            sorted(
                f"{getattr(b, 'value', str(b))}:{getattr(d, 'value', str(d))}"
                for b, d in zone_bands.items()
            )
        )
        parts.append(f"zone_bands=[{zb_serial}]")

    # 3. Corridor topology — segments + endpoints.
    corridor_path = _get_path(source, _PATH_CORRIDOR_PATH, allow_missing=True)
    if corridor_path is not None:
        parts.append(f"corridor={_serialise_corridor_path(corridor_path)}")

    # 4. Room size table — sorted (room_id, area_m2) pairs.
    room_size_table = _get_path(source, _PATH_ROOM_SIZE_TABLE, allow_missing=True)
    if room_size_table is not None:
        parts.append(f"rooms={_serialise_room_size_table(room_size_table)}")

    # 5. Wet-zone plan — sorted assignments + anchors.
    wet_zone_plan = _get_path(source, _PATH_WET_ZONE_PLAN, allow_missing=True)
    if wet_zone_plan is not None:
        parts.append(f"wet_zone={_serialise_wet_zone_plan(wet_zone_plan)}")

    # 6. Plot orientation — from oriented_candidate (different from
    #    plot.facing — this is C6's refined orientation).
    orientation = _get_path(source, _PATH_ORIENTATION, allow_missing=True)
    if orientation is not None:
        parts.append(f"orientation={getattr(orientation, 'value', str(orientation))}")

    h = hashlib.sha256()
    h.update("\x1f".join(parts).encode("utf-8"))
    return h.hexdigest()[:16]


def _derive_multi_floor_canonical_signature(source: Any) -> str:
    """Multi-floor canonical signature per Spec #4 v1.6 § 3.5.

    Aggregates per-floor canonical signatures with:
      - ``multi_floor_sig_schema=v1`` prefix (item 5 from v1.1 critique
        walk) — decouples wrapper-level signature versioning from
        per-floor signature versioning.
      - ``multi_floor=true`` marker.
      - ``master_floor=<label>`` — distinguishes M8-mutated wrappers
        from non-M8 wrappers even when per-floor signatures coincide.
      - per-floor signatures derived recursively, ordered by tuple
        index (Spec #1 + Spec #3 § 3.5 tuple-order-is-structural).

    Returns: 16-hex-char SHA256 prefix.
    """
    parts: list[str] = []
    parts.append("multi_floor_sig_schema=v1")
    parts.append("multi_floor=true")
    parts.append(f"master_floor={source.master_bedroom_floor_label}")
    for floor_label, per_floor_wzpc in zip(source.floor_labels, source.floors):
        per_floor_sig = derive_canonical_signature(per_floor_wzpc)
        parts.append(f"floor[{floor_label}]={per_floor_sig}")
    serialised = "|".join(parts)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# Path constants — v1.0 LOCKED ancestry chain
# =============================================================================


_PATH_TOPOLOGY_KIND_VALUE = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "oriented_candidate",
    "topology_candidate",
    "kind",
)

_PATH_ZONE_BANDS = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "oriented_candidate",
    "topology_candidate",
    "zone_bands",
)

_PATH_CORRIDOR_PATH = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "corridor_path",
)

_PATH_ROOM_SIZE_TABLE = (
    "room_sized_candidate",
    "room_size_table",
)

_PATH_WET_ZONE_PLAN = (
    "wet_zone_plan",
)

_PATH_ORIENTATION = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "oriented_candidate",
    "orientation",
)


# =============================================================================
# Walk helpers
# =============================================================================


def _get_path(
    root: Any, path: tuple[str, ...], *, allow_missing: bool = False,
) -> Any:
    """Walk dotted ``path`` from ``root``. Raises if required and missing."""
    cur = root
    for i, segment in enumerate(path):
        if not hasattr(cur, segment):
            if allow_missing:
                return None
            raise CandidateContextSchemaError(
                f"Canonical signature path '{'.'.join(path)}' broken at "
                f"segment '{segment}' (consumed: '{'.'.join(path[:i])}')."
            )
        cur = getattr(cur, segment)
        if cur is None:
            if allow_missing:
                return None
            raise CandidateContextSchemaError(
                f"Canonical signature path '{'.'.join(path[:i+1])}' "
                f"resolved to None."
            )
    return cur


# =============================================================================
# Serialisers — structural fields only
# =============================================================================


def _serialise_corridor_path(corridor_path: Any) -> str:
    """Serialise CorridorPath structurally: has_corridor + segment list."""
    has_corridor = getattr(corridor_path, "has_corridor", None)
    segments = getattr(corridor_path, "segments", ())
    seg_parts = []
    for seg in segments:
        kind = getattr(getattr(seg, "kind", None), "value", "?")
        runs = getattr(getattr(seg, "runs_along", None), "value", "?")
        length = getattr(seg, "length_m", 0.0)
        seg_parts.append(f"{kind}@{runs}:{length:.4f}")
    return f"has={has_corridor};segs=[{','.join(seg_parts)}]"


def _serialise_room_size_table(room_size_table: Any) -> str:
    """Best-effort structural serialise of room_size_table.

    Real RoomSizeTable carries a sequence of room entries with id +
    area. The signature uses these structurally; if the type's shape
    changes in a future C9 amendment, B-NEW-U becomes the source-edit
    review gate per F-v4-2.
    """
    # Tries common shapes; falls back to repr.
    if hasattr(room_size_table, "rooms"):
        rooms = room_size_table.rooms
        try:
            entries = sorted(
                f"{getattr(r, 'room_id', '?')}:{getattr(r, 'area_m2', 0.0):.4f}"
                for r in rooms
            )
            return f"rooms={','.join(entries)}"
        except Exception:
            return f"rooms={repr(room_size_table)}"
    return f"rst={repr(room_size_table)}"


def _serialise_wet_zone_plan(wet_zone_plan: Any) -> str:
    """Structural serialise of WetZonePlan — wet-wall assignments
    + riser anchors."""
    parts = []
    # Wet-wall assignments
    assignments = getattr(wet_zone_plan, "wet_wall_assignments", None)
    if assignments is not None:
        try:
            assignment_strs = sorted(
                f"{getattr(a, 'fixture_id', '?')}->{getattr(a, 'wall_id', '?')}"
                for a in assignments
            )
            parts.append(f"assigns=[{','.join(assignment_strs)}]")
        except Exception:
            parts.append(f"assigns={repr(assignments)}")

    # Riser groups / anchors
    risers = getattr(wet_zone_plan, "riser_groups", None)
    if risers is not None:
        try:
            riser_strs = sorted(
                f"{getattr(r, 'group_id', '?')}@({getattr(r, 'x_m', 0.0):.4f},{getattr(r, 'y_m', 0.0):.4f})"
                for r in risers
            )
            parts.append(f"risers=[{','.join(riser_strs)}]")
        except Exception:
            parts.append(f"risers={repr(risers)}")

    return ";".join(parts) or repr(wet_zone_plan)


# =============================================================================
# Repr+index fallback (synthetic / schema-drift safety)
# =============================================================================


def _derive_repr_index_signature(source: Any, source_index: int) -> str:
    """Sub-4 fallback. SHA256-prefix of repr(source) + index."""
    h = hashlib.sha256()
    h.update(repr(source).encode("utf-8"))
    h.update(b"\x1f")
    h.update(str(source_index).encode("utf-8"))
    return h.hexdigest()[:16]


__all__ = [
    "derive_signature",
    "derive_canonical_signature",
]
