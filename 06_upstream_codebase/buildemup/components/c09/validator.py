"""
BuildemUp† — Component 9 (Room Sizer) — Validator + classifier.

Per C9 SPEC v0.7 LOCKED § 4.6 (Infeasibility detection) + § 4.7 (Validator
invariants) + § 4.8 (Order-of-checks) + § 14.35–§ 14.43.

Three responsibilities:

  1. Inv 9 / Inv 17a deterministic-fail-fast checks — raise PerCandidateError
     subclasses BEFORE allocator runs.
  2. Per-room classifier helpers:
       _classify_width_feasibility -> WidthFeasibilityVerdict
       _classify_grid_bay         -> GridBayFeasibility
  3. Full Inv 1-18 sweep after allocation, including:
       - WARN-mode logging to provenance maps
       - STRICT-mode escalations (PackingInfeasibleError, WidthRiskyError,
         GridOversizeError) per § 14.41
       - Severity-weighted placement_risk_level derivation per § 14.36

The validator is pure: it consumes already-materialised RoomSizeRequirement
instances + envelope/grid context, and returns a tuple of computed verdict
maps + the placement_risk_level / score. The orchestrator threads those into
RoomSizingProvenance.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c09.errors import (
    GridOversizeError,
    PackingInfeasibleError,
    RoomSizingInfeasibleError,
    WidthInfeasibleError,
    WidthRiskyError,
)
from buildemup.components.c09.schema import (
    BathroomSubtype,
    EnforcementMode,
    GridBayFeasibility,
    PlacementRiskLevel,
    RoomCategory,
    RoomSizeRequirement,
    WidthFeasibilityVerdict,
)


# Float-equality tolerance (matches allocator).
_EPSILON_M2: float = 1e-6
_EPSILON_M: float = 1e-6


# =============================================================================
# Section 1 — Deterministic fail-fast (run BEFORE allocator)
# =============================================================================


def check_total_area_feasibility(
    *,
    rooms: tuple[RoomSizeRequirement, ...],
    envelope_minus_corridor_m2: float,
    candidate_index: int,
) -> None:
    """Inv 9: ``Σ liveability_min_area_m2 <= envelope_minus_corridor_m2``.

    Per § 4.6 / § 4.7. Raises RoomSizingInfeasibleError (PerCandidateError) on
    failure — total-area infeasibility is deterministic, fail-fast on the
    candidate. The orchestrator catches and aggregates per § 14.40.
    """
    total_min = sum(r.liveability_min_area_m2 for r in rooms)
    if total_min > envelope_minus_corridor_m2 + _EPSILON_M2:
        deficit = total_min - envelope_minus_corridor_m2
        raise RoomSizingInfeasibleError(
            f"C9 Inv 9 failure on candidate {candidate_index}: "
            f"Σ liveability_min_area_m2 ({total_min:.3f} m²) > "
            f"buildable_envelope_minus_corridor_m2 "
            f"({envelope_minus_corridor_m2:.3f} m²); "
            f"deficit = {deficit:.3f} m². Caller must escalate to "
            f"brief renegotiation (B-NNN-A) or plot expansion.",
            candidate_index=candidate_index,
            total_liveability_min_area_m2=total_min,
            envelope_minus_corridor_m2=envelope_minus_corridor_m2,
            deficit_m2=deficit,
        )


def check_width_feasibility_inv_17a(
    *,
    rooms: tuple[RoomSizeRequirement, ...],
    envelope_min_axis_m: float,
    wall_thickness_ratio: float,
    candidate_index: int,
) -> dict[str, WidthFeasibilityVerdict]:
    """Inv 17a (RAISE) + Inv 17b classification.

    Per § 4.6 / § 4.7 / § 14.35. Walks every room, classifies width feasibility,
    and raises WidthInfeasibleError if any room is IMPOSSIBLE (deterministic
    width infeasibility — room cannot fit envelope's smaller axis at all).

    RISKY rooms are returned in the verdict map for downstream WARN/STRICT
    handling in the full invariant sweep.

    Returns:
        {room_id: WidthFeasibilityVerdict} for every room.
    """
    verdicts: dict[str, WidthFeasibilityVerdict] = {}
    for r in rooms:
        verdicts[r.room_id] = _classify_width_feasibility(
            r.liveability_min_width_m,
            envelope_min_axis_m,
            wall_thickness_ratio,
        )

    impossible = tuple(
        rid for rid, v in verdicts.items()
        if v == WidthFeasibilityVerdict.IMPOSSIBLE
    )
    if impossible:
        details = ", ".join(
            f"{rid}: liveability_min_width_m="
            f"{next(r for r in rooms if r.room_id == rid).liveability_min_width_m:.3f}m"
            for rid in impossible
        )
        raise WidthInfeasibleError(
            f"C9 Inv 17a failure on candidate {candidate_index}: "
            f"deterministic width infeasibility on room(s) {impossible} — "
            f"{details}; envelope_min_axis_m={envelope_min_axis_m:.3f}. "
            f"Placement at C11 is mathematically impossible. Caller must "
            f"escalate to brief renegotiation (B-NNN-A) or envelope reshape.",
            candidate_index=candidate_index,
            impossible_room_ids=impossible,
            envelope_min_axis_m=envelope_min_axis_m,
        )
    return verdicts


def _classify_width_feasibility(
    liveability_min_width_m: float,
    envelope_min_axis_m: float,
    wall_thickness_ratio: float,
) -> WidthFeasibilityVerdict:
    """Per § 4.7 (Inv 17a check) + § 14.37.

    risky_threshold = (1.0 - wall_thickness_ratio) * envelope_min_axis_m
    """
    if liveability_min_width_m > envelope_min_axis_m + _EPSILON_M:
        return WidthFeasibilityVerdict.IMPOSSIBLE
    risky_threshold = (1.0 - wall_thickness_ratio) * envelope_min_axis_m
    if liveability_min_width_m > risky_threshold + _EPSILON_M:
        return WidthFeasibilityVerdict.RISKY
    return WidthFeasibilityVerdict.FEASIBLE


def _classify_grid_bay(
    liveability_min_width_m: float,
    bay_max_m: float,
) -> GridBayFeasibility:
    """Per § 14.30."""
    if bay_max_m <= 0.0:
        # Degenerate grid; treat all rooms as OVERSIZED (defensive).
        return GridBayFeasibility.OVERSIZED
    if liveability_min_width_m <= bay_max_m + _EPSILON_M:
        return GridBayFeasibility.SINGLE_BAY
    if liveability_min_width_m <= 2.0 * bay_max_m + _EPSILON_M:
        return GridBayFeasibility.DOUBLE_BAY
    if liveability_min_width_m <= 3.0 * bay_max_m + _EPSILON_M:
        return GridBayFeasibility.TRIPLE_BAY
    return GridBayFeasibility.OVERSIZED


def classify_grid_bay_feasibility(
    *,
    rooms: tuple[RoomSizeRequirement, ...],
    bay_max_m: float,
) -> dict[str, GridBayFeasibility]:
    """Per-room grid-bay classification. Per § 14.30 / Inv 18.

    Pure classifier — does NOT raise. The full invariant sweep handles
    WARN logging and STRICT-mode escalation.
    """
    return {
        r.room_id: _classify_grid_bay(r.liveability_min_width_m, bay_max_m)
        for r in rooms
    }


# =============================================================================
# Section 2 — Full Inv 1-18 sweep (run AFTER allocator)
# =============================================================================


@dataclass(frozen=True)
class ValidationOutcome:
    """Bundles the outputs the orchestrator needs from the post-allocation sweep.

    Per § 4.7 / § 4.8.
    """
    width_feasibility_per_room: dict[str, WidthFeasibilityVerdict]
    grid_bay_feasibility_per_room: dict[str, GridBayFeasibility]
    heuristic_packing_check_warning: bool
    placement_risk_level: PlacementRiskLevel
    placement_risk_score: int


def run_invariants(
    *,
    rooms: tuple[RoomSizeRequirement, ...],
    bedroom_count: int,
    bathroom_count: int,
    has_kitchen: bool,
    has_living: bool,
    has_pooja: bool,
    has_utility: bool,
    other_rooms_count: int,
    width_verdicts: dict[str, WidthFeasibilityVerdict],
    bay_max_m: float,
    envelope_minus_corridor_m2: float,
    packing_efficiency: float,
    enforcement_mode: EnforcementMode,
    candidate_index: int,
    has_master_bedroom: bool = True,
) -> ValidationOutcome:
    """Run Inv 1-18 sweep + STRICT-mode escalations.

    Per § 4.7 / § 14.41. Inv 9 + Inv 17a are checked separately before allocation
    (see check_total_area_feasibility / check_width_feasibility_inv_17a). This
    function handles the remainder + the heuristic warnings + STRICT escalations.

    Per Spec #2 v0.12 LOCKED (C9 Amendment for B-NEW-T3, supersedes v0.11):
    ``has_master_bedroom`` (default True) gates Inv 13 / Inv 14 cardinality.
    When False, the expected master-bedroom / master-bathroom count is 0
    rather than 1; multi-floor non-master floors are now valid C9 outputs.

    Raises:
        ValueError: Inv 1, 2, 11, 12, 13, 14, 15, 16 violations.
        PackingInfeasibleError: Inv 10 + STRICT mode.
        WidthRiskyError:        Inv 17b + STRICT mode.
        GridOversizeError:      Inv 18 + STRICT mode.

    Returns:
        ValidationOutcome.
    """
    # ---- Inv 1: rooms count matches brief ----
    expected_total = (
        bedroom_count
        + bathroom_count
        + (1 if has_kitchen else 0)
        + (1 if has_living else 0)
        + (1 if has_pooja else 0)
        + (1 if has_utility else 0)
        + other_rooms_count
    )
    if len(rooms) != expected_total:
        raise ValueError(
            f"C9 Inv 1 failure on candidate {candidate_index}: "
            f"rooms count ({len(rooms)}) != brief-derived total "
            f"({expected_total}); bedroom={bedroom_count}, bathroom="
            f"{bathroom_count}, kitchen={has_kitchen}, living={has_living}, "
            f"pooja={has_pooja}, utility={has_utility}, other={other_rooms_count}"
        )

    # ---- Inv 2: category counts match brief ----
    counts: dict[RoomCategory, int] = {c: 0 for c in RoomCategory}
    for r in rooms:
        counts[r.category] += 1
    expected_counts = {
        RoomCategory.BEDROOM:  bedroom_count,
        RoomCategory.BATHROOM: bathroom_count,
        RoomCategory.KITCHEN:  1 if has_kitchen else 0,
        RoomCategory.LIVING:   1 if has_living else 0,
        RoomCategory.POOJA:    1 if has_pooja else 0,
        RoomCategory.UTILITY:  1 if has_utility else 0,
        RoomCategory.OTHER:    other_rooms_count,
    }
    for cat, expected in expected_counts.items():
        if counts[cat] != expected:
            raise ValueError(
                f"C9 Inv 2 failure on candidate {candidate_index}: "
                f"category {cat.value} count ({counts[cat]}) != brief "
                f"expected ({expected})"
            )

    # ---- Inv 3,4,5,6,6b,7,8: per-room math (asserted at RoomSizeRequirement
    #      construction; defensive recheck here surfaces any post-construction
    #      tampering) ----
    for r in rooms:
        if r.regulatory_minimum.area_m2 < 0:
            raise ValueError(
                f"C9 Inv 3 failure: room {r.room_id} regulatory area negative"
            )
        if r.liveability_min_area_m2 < r.regulatory_minimum.area_m2 - _EPSILON_M2:
            raise ValueError(
                f"C9 Inv 6 failure: room {r.room_id} liveability_min_area "
                f"< regulatory minimum"
            )
        if r.liveability_min_width_m < r.regulatory_minimum.width_m - _EPSILON_M:
            raise ValueError(
                f"C9 Inv 6b failure: room {r.room_id} liveability_min_width "
                f"< regulatory width"
            )
        if r.target_m2 < r.liveability_min_area_m2 - _EPSILON_M2:
            raise ValueError(
                f"C9 Inv 7 failure: room {r.room_id} target < liveability_min"
            )
        if r.max_m2 < r.target_m2 - _EPSILON_M2:
            raise ValueError(
                f"C9 Inv 8 failure: room {r.room_id} max < target"
            )

    # ---- Inv 11: room_ids unique (asserted at RoomSizeTable; defensive recheck) ----
    ids = [r.room_id for r in rooms]
    if len(set(ids)) != len(ids):
        raise ValueError(
            f"C9 Inv 11 failure on candidate {candidate_index}: "
            f"duplicate room_ids in {ids}"
        )

    # ---- Inv 12: priority covers 1..n contiguously ----
    priorities = sorted(r.priority for r in rooms)
    if priorities != list(range(1, len(rooms) + 1)):
        raise ValueError(
            f"C9 Inv 12 failure on candidate {candidate_index}: "
            f"priority values must cover 1..n contiguously; got {priorities}"
        )

    # ---- Inv 13: master-BEDROOM cardinality (per Spec #2 v0.12 LOCKED) ----
    # When has_master_bedroom=True (default) AND bedroom_count >= 1:
    #     expect exactly 1 master bedroom (legacy single-floor behaviour).
    # When has_master_bedroom=False:
    #     expect 0 master bedrooms (multi-floor non-master floor).
    # When bedroom_count == 0:
    #     always 0 master bedrooms regardless of flag.
    bedroom_masters = [r for r in rooms if r.category == RoomCategory.BEDROOM and r.is_master]
    expected_bedroom_masters = 1 if (bedroom_count >= 1 and has_master_bedroom) else 0
    if len(bedroom_masters) != expected_bedroom_masters:
        raise ValueError(
            f"C9 Inv 13 failure on candidate {candidate_index}: "
            f"expected exactly {expected_bedroom_masters} master BEDROOM "
            f"(bedroom_count={bedroom_count}, "
            f"has_master_bedroom={has_master_bedroom}); "
            f"got {len(bedroom_masters)}"
        )

    # ---- Inv 14: master-BATHROOM cardinality (per Spec #2 v0.12 LOCKED) ----
    # Mirrors Inv 13 with the en-suite coupling per Spec #2 § 3.4:
    # bathroom #1 is master iff has_master_bedroom AND bathroom_count >= 1.
    # When has_master_bedroom=False, expect 0 master bathrooms (was: at most 1).
    bathroom_masters = [r for r in rooms if r.category == RoomCategory.BATHROOM and r.is_master]
    expected_bathroom_masters = 1 if (bathroom_count >= 1 and has_master_bedroom) else 0
    if len(bathroom_masters) != expected_bathroom_masters:
        raise ValueError(
            f"C9 Inv 14 failure on candidate {candidate_index}: "
            f"expected exactly {expected_bathroom_masters} master BATHROOM "
            f"(bathroom_count={bathroom_count}, "
            f"has_master_bedroom={has_master_bedroom}); "
            f"got {len(bathroom_masters)}"
        )

    # ---- Inv 15: bathroom_subtype set iff category == BATHROOM (asserted at
    #      RoomSizeRequirement; defensive recheck) ----
    for r in rooms:
        has_subtype = r.bathroom_subtype is not None
        is_bathroom = r.category == RoomCategory.BATHROOM
        if has_subtype != is_bathroom:
            raise ValueError(
                f"C9 Inv 15 failure on candidate {candidate_index}: "
                f"room {r.room_id} category={r.category.value} but "
                f"bathroom_subtype={r.bathroom_subtype}"
            )

    # Inv 16 is enforced at RoomSizeTable construction (unassigned_area_m2 >= 0).

    # ---- Inv 10: heuristic packing check (WARN by default; STRICT escalates) ----
    total_min = sum(r.liveability_min_area_m2 for r in rooms)
    packing_capacity = envelope_minus_corridor_m2 * packing_efficiency
    packing_warning = total_min > packing_capacity + _EPSILON_M2
    if packing_warning and enforcement_mode == EnforcementMode.STRICT:
        raise PackingInfeasibleError(
            f"C9 Inv 10 + STRICT failure on candidate {candidate_index}: "
            f"Σ liveability_min_area_m2 ({total_min:.3f}) > "
            f"envelope * packing_efficiency ({packing_capacity:.3f}); "
            f"packing_efficiency={packing_efficiency}.",
            candidate_index=candidate_index,
            total_liveability_min_area_m2=total_min,
            packing_capacity_m2=packing_capacity,
            packing_efficiency=packing_efficiency,
        )

    # ---- Inv 17b: width feasibility — WARN on RISKY (escalate in STRICT) ----
    risky = tuple(
        rid for rid, v in width_verdicts.items()
        if v == WidthFeasibilityVerdict.RISKY
    )
    if risky and enforcement_mode == EnforcementMode.STRICT:
        raise WidthRiskyError(
            f"C9 Inv 17b + STRICT failure on candidate {candidate_index}: "
            f"room(s) {risky} have RISKY width verdict (just-barely-fits "
            f"envelope min-axis with wall-thickness margin).",
            candidate_index=candidate_index,
            risky_room_ids=risky,
        )

    # ---- Inv 18: grid-bay feasibility (computed here; WARN on OVERSIZED;
    #      escalate in STRICT) ----
    grid_verdicts: dict[str, GridBayFeasibility] = {
        r.room_id: _classify_grid_bay(r.liveability_min_width_m, bay_max_m)
        for r in rooms
    }
    oversized = tuple(
        rid for rid, v in grid_verdicts.items()
        if v == GridBayFeasibility.OVERSIZED
    )
    if oversized and enforcement_mode == EnforcementMode.STRICT:
        raise GridOversizeError(
            f"C9 Inv 18 + STRICT failure on candidate {candidate_index}: "
            f"room(s) {oversized} have OVERSIZED grid-bay verdict "
            f"(liveability_min_width_m > 3 × bay_max_m={bay_max_m:.3f}). "
            f"Grids are structurally negotiable (transfer beams, alternate "
            f"column patterns) so OVERSIZED is heuristic per § 14.42; STRICT "
            f"mode hard-fails to give callers a clean signal.",
            candidate_index=candidate_index,
            oversized_room_ids=oversized,
            bay_max_m=bay_max_m,
        )

    # ---- placement_risk_level: severity-weighted (§ 14.36) ----
    risk_level, risk_score = _derive_placement_risk_level(
        width_verdicts, grid_verdicts, packing_warning
    )

    return ValidationOutcome(
        width_feasibility_per_room=width_verdicts,
        grid_bay_feasibility_per_room=grid_verdicts,
        heuristic_packing_check_warning=packing_warning,
        placement_risk_level=risk_level,
        placement_risk_score=risk_score,
    )


def _derive_placement_risk_level(
    width_verdicts: dict[str, WidthFeasibilityVerdict],
    grid_verdicts: dict[str, GridBayFeasibility],
    packing_warning: bool,
) -> tuple[PlacementRiskLevel, int]:
    """Severity-weighted aggregation per § 14.36.

    Weights:
      - OVERSIZED grid: 2 (closest-to-deterministic in the WARN tier)
      - packing_warning: 1
      - any RISKY width: 1
      - any TRIPLE_BAY grid: 1

    score -> level:
      - 0:    LOW
      - 1-2:  MEDIUM
      - 3+:   HIGH

    OVERSIZED alone (weight 2) -> MEDIUM. OVERSIZED + any other yellow -> HIGH.
    IMPOSSIBLE width never reaches here (Inv 17a RAISES first).
    """
    score = 0
    if any(v == GridBayFeasibility.OVERSIZED for v in grid_verdicts.values()):
        score += 2
    if packing_warning:
        score += 1
    if any(v == WidthFeasibilityVerdict.RISKY for v in width_verdicts.values()):
        score += 1
    if any(v == GridBayFeasibility.TRIPLE_BAY for v in grid_verdicts.values()):
        score += 1

    if score >= 3:
        return PlacementRiskLevel.HIGH, score
    if score >= 1:
        return PlacementRiskLevel.MEDIUM, score
    return PlacementRiskLevel.LOW, score


__all__ = [
    "ValidationOutcome",
    "check_total_area_feasibility",
    "check_width_feasibility_inv_17a",
    "classify_grid_bay_feasibility",
    "run_invariants",
]
