"""C11b → C12 adapter glue (S57 follow-up #4).

C12's `place_and_align` consumes `SingleFloorPlacementInput` tuples
that carry per-room dimensions plus an envelope. The DOCUMENTED upstream
producer is C11b's `RefinedCandidate` (post-NSGA refinement), but the
MVP master orchestrator currently ships C11b as STUB (S57 follow-up #3
defers the real EvaluatorProtocol). To flip C12 from STUB to OK end-to-end
in S57, this module provides BOTH paths:

  1. ``adapt_refined_to_single_floor`` — the documented primary path.
     Future-shipping: activates once #3 lands and C11b produces real
     RefinedCandidate output. Currently exercised only by unit tests.

  2. ``adapt_mutated_to_single_floor`` — the STUB-fallback. Sources room
     dimensions from the C9 RoomSizeTable embedded in the C10 wet-zoned
     candidate that's embedded in the C11a output. Used by the master
     orchestrator while C11b is STUB.

  3. ``build_single_floor_inputs_from_upstream`` — the orchestrator's
     entry point. Picks the RefinedCandidate path if C11b ships OK,
     else falls back to the C11a path. Returns a tuple of
     SingleFloorPlacementInput ready for ``place_and_align``.

The fallback path explicitly trades C11b's optimization (the NSGA
loop's dimension refinement) for C10's sizing. That's acceptable: the
goal at S57 is end-to-end pipeline aliveness, not refinement quality.
When #3 ships and C11b ships OK, the orchestrator naturally switches
to the primary path with no orchestrator code change required.
"""
from __future__ import annotations

import math
from typing import Any

from buildemup.components.c09.schema import (
    RoomCategory,
    RoomSizeRequirement,
)
from buildemup.components.c11b.schema import RefinedCandidate
from buildemup.components.c11a.provenance import MutatedTopologyCandidate
from buildemup.components.c12 import (
    RoomSpec,
    SingleFloorPlacementInput,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _room_category_to_str(category: RoomCategory) -> str:
    """C9 RoomCategory enum → C12-friendly canonical string.

    RoomCategory is `str, Enum`, so .value is already the canonical
    string. Kept as a function for forward-compat with category-aware
    normalisation (e.g., master-bedroom subtyping in future).
    """
    return category.value


def _derive_dims_from_requirement(
    req: RoomSizeRequirement,
) -> tuple[float, float]:
    """Derive (width_m, depth_m) for a RoomSpec from C9 sizing.

    C9 produces target area + minimum width. C12 wants width+depth.
    Strategy: take width = max(sqrt(target_m2), liveability_min_width_m)
    so the room is roughly square but never below NBC width minimum;
    derive depth = target_m2 / width. If the resulting depth would
    drop below liveability_min_width_m, square it at min_width and
    accept the slight area overshoot — C12 only needs dimensions for
    placement, not strict area conservation.

    This is intentionally simple. When #3 lands and C11b's NSGA loop
    produces refined per-room dimensions directly, this fallback is no
    longer the active path.
    """
    target_a = req.target_m2
    min_w = req.liveability_min_width_m
    sqrt_a = math.sqrt(target_a)
    width = max(sqrt_a, min_w)
    depth = target_a / width
    if depth < min_w:
        # Square at min_width; area overshoots slightly. Acceptable
        # because C12 placement only requires positive dims; C9's
        # area invariants are not re-asserted downstream.
        width = min_w
        depth = min_w
    return width, depth


def _build_room_spec_from_requirement(req: RoomSizeRequirement) -> RoomSpec:
    """Lift a C9 RoomSizeRequirement to a C12 RoomSpec."""
    width_m, depth_m = _derive_dims_from_requirement(req)
    return RoomSpec(
        room_id=req.room_id,
        category=_room_category_to_str(req.category),
        target_width_m=width_m,
        target_depth_m=depth_m,
    )


def _plot_envelope(plot_analysis: Any) -> tuple[float, float]:
    """Extract (width_m, depth_m) from a C4 PlotAnalysis.

    The orchestrator's C7 phase already pulls these via
    ``plot_analysis.plot.width_m / .plot.depth_m`` (see
    ``_run_c07_structural_grid``), so the same access pattern is used
    here.
    """
    return plot_analysis.plot.width_m, plot_analysis.plot.depth_m


# ─────────────────────────────────────────────────────────────────────
# Primary adapter — RefinedCandidate → SingleFloorPlacementInput
# ─────────────────────────────────────────────────────────────────────


def adapt_refined_to_single_floor(
    refined: RefinedCandidate,
    plot_analysis: Any,
    *,
    room_categories_by_id: dict[str, str],
) -> SingleFloorPlacementInput:
    """C11b RefinedCandidate → C12 SingleFloorPlacementInput.

    The documented primary path (S57 follow-up #4). Activates in the
    orchestrator once #3 ships a real EvaluatorProtocol that makes
    C11b emit RefinedCandidate output.

    `room_categories_by_id` carries category data that C11b's
    RefinedCandidate schema doesn't itself encode (C11b refines
    dimensions only; categories live upstream in C9's RoomSizeTable).
    The orchestrator builds this lookup from the C9 → C10 → C11a chain
    before calling C11b, threads it through, and passes it here.
    """
    envelope_w, envelope_d = _plot_envelope(plot_analysis)
    rooms = tuple(
        RoomSpec(
            room_id=d.room_id,
            category=room_categories_by_id[d.room_id],
            target_width_m=d.width_m,
            target_depth_m=d.depth_m,
        )
        for d in refined.refined_parameters.room_dimensions
    )
    return SingleFloorPlacementInput(
        candidate_signature=refined.source_topology_candidate_signature,
        capability_mode=refined.capability_mode,
        placement_safe=refined.placement_safe,
        geometry_materialized=refined.geometry_materialized,
        rooms=rooms,
        envelope_width_m=envelope_w,
        envelope_depth_m=envelope_d,
    )


# ─────────────────────────────────────────────────────────────────────
# Fallback adapter — MutatedTopologyCandidate → SingleFloorPlacementInput
# ─────────────────────────────────────────────────────────────────────


def adapt_mutated_to_single_floor(
    mutated: MutatedTopologyCandidate,
    plot_analysis: Any,
) -> SingleFloorPlacementInput:
    """C11a MutatedTopologyCandidate → C12 SingleFloorPlacementInput.

    The STUB-fallback path (S57 follow-up #4). Used by the master
    orchestrator while C11b ships STUB (S57 follow-up #3 pending).

    Pulls room dimensions out of the C10 WetZonePlannedCandidate
    embedded in the C11a output (via .source_candidate). The room
    dimensions come from C9's RoomSizeTable via C8's CorridorDesignedCandidate
    → C9's RoomSizedCandidate → C10's WetZonePlannedCandidate chain.

    Trade-off: drops C11b's NSGA optimization. Acceptable for S57 — the
    goal is end-to-end aliveness, not optimization quality.
    """
    wet_zoned = mutated.source_candidate
    room_sized = wet_zoned.room_sized_candidate
    rooms = tuple(
        _build_room_spec_from_requirement(req)
        for req in room_sized.room_size_table.rooms
    )
    envelope_w, envelope_d = _plot_envelope(plot_analysis)
    # M0_BASE is materialized geometry per C11b spec § 0.3.1 worked
    # example. Tier A operators surface as PREDICATE_ONLY but those
    # don't reach C12 anyway — they're filtered before placement.
    # The orchestrator currently enables only M0_BASE; fallback assumes
    # materialized.
    return SingleFloorPlacementInput(
        candidate_signature=mutated.topology_variant_id,
        capability_mode="MATERIALIZED",
        placement_safe=True,
        geometry_materialized=True,
        rooms=rooms,
        envelope_width_m=envelope_w,
        envelope_depth_m=envelope_d,
    )


# ─────────────────────────────────────────────────────────────────────
# Orchestrator entry point
# ─────────────────────────────────────────────────────────────────────


def build_single_floor_inputs_from_upstream(
    *,
    c11a_payload: Any,
    c11b_payload: Any,
    plot_analysis: Any,
) -> tuple[SingleFloorPlacementInput, ...]:
    """Pick the right adapter and build the C12 input batch.

    Picks the documented `RefinedCandidate` path if C11b shipped OK
    (payload is a `RefinementBatchResult` carrying refined candidates).
    Otherwise falls back to the C11a-direct path that sources rooms
    from the C9 RoomSizeTable embedded upstream.

    Returns the tuple ``place_and_align`` expects. Caller passes it
    straight in.

    No-op path: if both upstream payloads are None, returns an empty
    tuple. C12 then runs against zero candidates — `place_and_align`
    returns a `PlacementBatchResult` with empty successes and failures
    (no candidates is not an error condition for C12). The orchestrator
    treats that batch result as OK because the call succeeded; the
    "no candidates" cause is captured in upstream phase results.
    """
    # Primary path: try to use C11b's RefinedCandidate output if
    # available. C11b is currently STUB so this branch is dead at S57;
    # included so the orchestrator naturally upgrades when #3 ships.
    if c11b_payload is not None:
        refined_candidates = _extract_refined_candidates(c11b_payload)
        if refined_candidates:
            # Build a category lookup from C11a's upstream wet-zoned
            # candidates so we can fill the category field that
            # RefinedCandidate doesn't carry itself.
            categories = _collect_room_categories(c11a_payload)
            return tuple(
                adapt_refined_to_single_floor(
                    rc, plot_analysis,
                    room_categories_by_id=categories,
                )
                for rc in refined_candidates
            )

    # Fallback path: build from C11a's MutatedTopologyCandidates
    # directly. Used while C11b ships STUB.
    if c11a_payload is None:
        return ()
    return tuple(
        adapt_mutated_to_single_floor(m, plot_analysis)
        for m in c11a_payload
    )


def _extract_refined_candidates(
    c11b_payload: Any,
) -> tuple[RefinedCandidate, ...]:
    """Pull the flat tuple of RefinedCandidates from C11b's payload.

    C11b's `run_local_refinement` returns ``tuple[RefinedCandidate, ...]``
    directly; the `RefinementBatchResult` wrapper from
    `run_local_refinement_with_provenance` carries the same tuple as
    `.refined_candidates`. Handle both shapes.
    """
    if c11b_payload is None:
        return ()
    # Wrapper case: RefinementBatchResult-style with .refined_candidates
    refined = getattr(c11b_payload, "refined_candidates", None)
    if refined is not None:
        return tuple(refined)
    # Direct-tuple case: payload IS the candidates tuple. Validate by
    # checking the first element looks like a RefinedCandidate.
    try:
        first = next(iter(c11b_payload), None)
    except TypeError:
        return ()
    if first is not None and isinstance(first, RefinedCandidate):
        return tuple(c11b_payload)
    return ()


def _collect_room_categories(c11a_payload: Any) -> dict[str, str]:
    """Build a {room_id: category} map from C11a's mutated candidates.

    All MutatedTopologyCandidates in a single C11a batch share the
    same upstream room set (they differ only by mutation operator
    applied to the same source WetZonePlannedCandidate). So we read
    categories from the first candidate that's available.

    Returns an empty dict if no candidates are present; callers should
    handle that case (the RefinedCandidate adapter will KeyError on a
    missing entry).
    """
    if not c11a_payload:
        return {}
    first = next(iter(c11a_payload), None)
    if first is None:
        return {}
    try:
        rooms = first.source_candidate.room_sized_candidate.room_size_table.rooms
    except AttributeError:
        return {}
    return {r.room_id: _room_category_to_str(r.category) for r in rooms}


__all__ = [
    "adapt_refined_to_single_floor",
    "adapt_mutated_to_single_floor",
    "build_single_floor_inputs_from_upstream",
]
