"""
BuildemUp† — Component 9 (Room Sizer) — Public orchestrator.

Per C9 SPEC v0.7 LOCKED § 1, § 2, § 4.6, § 4.8, § 5, § 14.40, § 14.41.

Public entry point: ``size_rooms``.

Pipeline (per § 4.8 Order-of-checks):

  Caller-error layer (one-shot, before per-candidate loop):
    1. Type checks
    2. Plot shape (B-066 NotImplementedError if non-rectangular)
    3. Brief sanity (bedroom_count >= 1)

  Per-candidate layer (looped; per § 14.40 each candidate processed independently;
  PerCandidateError subclasses caught and aggregated):
    4. Dwelling-tier resolution (§ 4.1, with 3-tier accuracy enum per § 14.25)
    5. Grid-bay capture (provenance)
    6. Per-candidate regulatory lookup (with require_verified_nbc gate;
       populates unverified_nbc_rows_used)
    7. Liveability resolution (§ 4.2)
    8. Targets + max sizes (§ 4.3 / § 4.4)
    9. Inv 9 RAISE on total-area infeasibility
   10. Inv 17a RAISE on deterministic IMPOSSIBLE width
   11. Surplus allocation (§ 4.5)
   12. Validator (Inv 1-18 with STRICT-mode escalations applied per-invariant)
   13. placement_risk_level severity-weighted derivation (§ 14.36)
   14. Successful candidate appended; failed candidate caught and recorded

  Batch finalisation:
   15. If zero successes, raise BatchSizingInfeasibleError; else return tuple
       of successes (preserves input-relative order among survivors).

†= placeholder name marker.
"""
from __future__ import annotations

import time
from types import MappingProxyType

from buildemup.components.c04.schema import PlotAnalysis, PlotShape
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.schema import (
    CorridorDesignedCandidate,
    ZoneBandEnvelope,
)
from buildemup.components.c09 import (
    furniture_floor as ff_mod,
    nbc_table as nbc_mod,
    targets_kb as tg_mod,
)
from buildemup.components.c09.allocator import distribute_surplus
from buildemup.components.c09.errors import (
    BatchSizingInfeasibleError,
    NBCConfidenceTooLow,
    PerCandidateError,
)
from buildemup.components.c09.schema import (
    DEFAULT_PACKING_EFFICIENCY,
    DEFAULT_WALL_THICKNESS_RATIO,
    DWELLING_TIER_THRESHOLD_M2,
    BathroomSubtype,
    DwellingSizeTier,
    EnforcementMode,
    NBCSourceConfidence,
    RegulatoryMinimum,
    RoomCategory,
    RoomSizeRequirement,
    RoomSizeTable,
    RoomSizedCandidate,
    RoomSizingConfig,
    RoomSizingProvenance,
    TierResolutionAccuracy,
)
from buildemup.components.c09.validator import (
    check_total_area_feasibility,
    check_width_feasibility_inv_17a,
    run_invariants,
)
from buildemup.domain.floor_brief import FloorRoomBrief


_EPSILON_M2: float = 1e-6


# =============================================================================
# Public entry point
# =============================================================================


def size_rooms(
    corridor_designed_candidates: tuple[CorridorDesignedCandidate, ...],
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    *,
    config: RoomSizingConfig | None = None,
) -> tuple[RoomSizedCandidate, ...]:
    """Public entry point. Per § 2 / § 5.

    Per-candidate semantics (NEW v0.7 per § 14.40): each input candidate is
    sized independently. PerCandidateError subclasses are caught and aggregated;
    the batch raises BatchSizingInfeasibleError only if ALL candidates fail.

    v1 LIMITATIONS (S34 audit findings):
      - D1: every BATHROOM is sized using BathroomSubtype.COMBINED. The
        FloorRoomBrief.bathroom_count scalar carries no per-bathroom subtype,
        so wc_only and bath_only NBC rows are unreachable through this entry
        point in v1. Filed as B-208.
      - D3: assumes uniform grid (grid.bay_x_m, grid.bay_y_m). C7 v1 produces
        uniform grids; if a future C7 ships non-uniform grids, the bay_max_m
        computation here will silently use only the two scalar bay dimensions
        and may misclassify Inv 18 grid-bay feasibility.

    Args:
        corridor_designed_candidates: tuple of 1-3 from C8.
        floor_room_brief: from C1.
        grid: from C7 (v1: uniform bays only — see D3 above).
        plot_analysis: from C4.
        config: tunables; default OK.

    Returns:
        Tuple of RoomSizedCandidate, ordered as input but skipping failed
        positions. Empty input -> empty output (no raise).

    Raises:
        TypeError, ValueError, NotImplementedError: caller-error / systemic.
        NBCConfidenceTooLow: systemic require_verified_nbc fail.
        BatchSizingInfeasibleError: every candidate failed per-candidate.
    """
    if config is None:
        config = RoomSizingConfig()

    # --- Caller-error layer ----------------------------------------------
    _check_input_types(
        corridor_designed_candidates, floor_room_brief, grid, plot_analysis
    )
    _check_plot_shape(plot_analysis)              # B-066
    _check_brief_sanity(floor_room_brief)

    # Empty input -> empty output (per § 6).
    if len(corridor_designed_candidates) == 0:
        return ()

    # --- Per-candidate layer ---------------------------------------------
    successes: list[RoomSizedCandidate] = []
    failures: list[tuple[int, PerCandidateError]] = []

    for i, candidate in enumerate(corridor_designed_candidates):
        try:
            sized = _size_one_candidate(
                candidate=candidate,
                floor_room_brief=floor_room_brief,
                grid=grid,
                plot_analysis=plot_analysis,
                config=config,
                candidate_index=i,
            )
            successes.append(sized)
        except PerCandidateError as exc:
            failures.append((i, exc))

    if not successes:
        raise BatchSizingInfeasibleError(
            failures, len(corridor_designed_candidates)
        )

    return tuple(successes)


# =============================================================================
# Caller-error checks
# =============================================================================


def _check_input_types(
    corridor_designed_candidates,
    floor_room_brief,
    grid,
    plot_analysis,
) -> None:
    if not isinstance(corridor_designed_candidates, tuple):
        raise TypeError(
            f"size_rooms: corridor_designed_candidates must be a tuple; "
            f"got {type(corridor_designed_candidates).__name__}"
        )
    for i, c in enumerate(corridor_designed_candidates):
        if not isinstance(c, CorridorDesignedCandidate):
            raise TypeError(
                f"size_rooms: corridor_designed_candidates[{i}] must be "
                f"CorridorDesignedCandidate; got {type(c).__name__}"
            )
    if not isinstance(floor_room_brief, FloorRoomBrief):
        raise TypeError(
            f"size_rooms: floor_room_brief must be FloorRoomBrief; "
            f"got {type(floor_room_brief).__name__}"
        )
    if not isinstance(grid, Grid):
        raise TypeError(
            f"size_rooms: grid must be Grid; got {type(grid).__name__}"
        )
    if not isinstance(plot_analysis, PlotAnalysis):
        raise TypeError(
            f"size_rooms: plot_analysis must be PlotAnalysis; "
            f"got {type(plot_analysis).__name__}"
        )


def _check_plot_shape(plot_analysis: PlotAnalysis) -> None:
    if plot_analysis.shape != PlotShape.RECTANGULAR:
        raise NotImplementedError(
            f"C9 v1 supports only RECTANGULAR plots (B-066); "
            f"got {plot_analysis.shape.value}. L_SHAPED / IRREGULAR is C11 "
            f"placement geometry territory (§ 14.28 / § 14.43)."
        )


def _check_brief_sanity(brief: FloorRoomBrief) -> None:
    if brief.bedroom_count < 1:
        raise ValueError(
            f"C9: floor_room_brief.bedroom_count must be >= 1; "
            f"got {brief.bedroom_count}"
        )


# =============================================================================
# Per-candidate sizing
# =============================================================================


def _size_one_candidate(
    *,
    candidate: CorridorDesignedCandidate,
    floor_room_brief: FloorRoomBrief,
    grid: Grid,
    plot_analysis: PlotAnalysis,
    config: RoomSizingConfig,
    candidate_index: int,
) -> RoomSizedCandidate:
    """Per § 4.8 steps 4-13 + § 14.40."""

    # Step 4: dwelling-tier resolution (§ 4.1)
    tier, accuracy, assumed_total = _resolve_dwelling_tier(
        candidate, floor_room_brief, config
    )

    # Step 5: grid-bay capture (provenance)
    bay_min_m, bay_max_m = _grid_bays(grid)

    # Envelope geometry. Per spec § 4.1 / § 4.6:
    #   - total buildable area = sum of band envelope rectangles
    #   - corridor area cuts through the bands; subtract for room-placement area
    #   - envelope_min_axis = min(plot.width_m, plot.depth_m) per § 14.43 v1 rectangular
    env_area_m2 = sum(_env_area(e) for e in candidate.corridor_path.envelopes)
    corridor_area_m2 = candidate.corridor_path.total_area_m2
    envelope_minus_corridor_m2 = max(0.0, env_area_m2 - corridor_area_m2)
    env_min_axis_m = min(plot_analysis.plot.width_m, plot_analysis.plot.depth_m)

    # Steps 6 + 7 + 8: materialise rooms (lookups + liveability + targets).
    rooms_list, unverified_nbc_rows, auto_lift_trace = _materialise_rooms(
        floor_room_brief, tier
    )

    # Step 6 systemic gate: require_verified_nbc
    if config.require_verified_nbc and unverified_nbc_rows:
        raise NBCConfidenceTooLow(
            f"C9 require_verified_nbc=True but {len(unverified_nbc_rows)} room(s) "
            f"used unverified NBC rows: {unverified_nbc_rows}. Caller must wait "
            f"for B-150 verification or relax require_verified_nbc.",
            unverified_room_ids=unverified_nbc_rows,
        )

    rooms = tuple(rooms_list)

    # priority_override validation (must reference exactly the rooms we materialised)
    if config.priority_override is not None:
        provided = set(config.priority_override)
        actual = set(r.room_id for r in rooms)
        if provided != actual or len(config.priority_override) != len(rooms):
            raise ValueError(
                f"C9 priority_override mismatch: provided={sorted(provided)}, "
                f"actual={sorted(actual)}; must enumerate every room_id "
                f"exactly once."
            )

    # Step 9: Inv 9 RAISE on total-area infeasibility (per-candidate)
    check_total_area_feasibility(
        rooms=rooms,
        envelope_minus_corridor_m2=envelope_minus_corridor_m2,
        candidate_index=candidate_index,
    )

    # Step 10: Inv 17a RAISE on deterministic IMPOSSIBLE width
    width_verdicts = check_width_feasibility_inv_17a(
        rooms=rooms,
        envelope_min_axis_m=env_min_axis_m,
        wall_thickness_ratio=config.wall_thickness_ratio,
        candidate_index=candidate_index,
    )

    # Step 11: surplus allocation
    alloc = distribute_surplus(
        rooms=rooms,
        envelope_minus_corridor_m2=envelope_minus_corridor_m2,
        strategy=config.allocation_strategy,
        priority_override=config.priority_override,
    )

    # Step 12: full validator sweep + STRICT-mode escalations + Step 13: PRL
    # Per Spec #2 v0.12 LOCKED: thread has_master_bedroom through so Inv 13/14
    # cardinality matches the materializer's gating in _materialise_rooms.
    outcome = run_invariants(
        rooms=rooms,
        bedroom_count=floor_room_brief.bedroom_count,
        bathroom_count=floor_room_brief.bathroom_count,
        has_kitchen=floor_room_brief.has_kitchen,
        has_living=floor_room_brief.has_living,
        has_pooja=floor_room_brief.has_pooja,
        has_utility=floor_room_brief.has_utility,
        other_rooms_count=len(floor_room_brief.other_rooms),
        width_verdicts=width_verdicts,
        bay_max_m=bay_max_m,
        envelope_minus_corridor_m2=envelope_minus_corridor_m2,
        packing_efficiency=config.packing_efficiency,
        enforcement_mode=config.enforcement_mode,
        candidate_index=candidate_index,
        has_master_bedroom=floor_room_brief.has_master_bedroom,
    )

    # Build RoomSizeTable
    total_min = sum(r.liveability_min_area_m2 for r in rooms)
    total_target = sum(r.target_m2 for r in rooms)
    table = RoomSizeTable(
        rooms=rooms,
        buildable_envelope_minus_corridor_m2=round(envelope_minus_corridor_m2, 6),
        dwelling_size_tier=tier,
        total_liveability_min_area_m2=round(total_min, 6),
        total_target_m2=round(total_target, 6),
        surplus_for_distribution_m2=alloc.surplus_for_distribution_m2,
        unassigned_area_m2=alloc.unassigned_area_m2,
        packing_efficiency_used=config.packing_efficiency,
        floor_label=floor_room_brief.floor_label,
    )

    # Build provenance
    provenance = RoomSizingProvenance(
        derived_at=time.time(),
        plot_analysis_trace_id=plot_analysis.trace_id,
        floor_label=floor_room_brief.floor_label,
        nbc_table_version=nbc_mod.KB_VERSION,
        furniture_kb_version=ff_mod.KB_VERSION,
        targets_kb_version=tg_mod.KB_VERSION,
        dwelling_size_tier=tier,
        tier_resolution_accuracy=accuracy,
        assumed_total_dwelling_area_m2=assumed_total,
        grid_bay_min_m=bay_min_m,
        grid_bay_max_m=bay_max_m,
        wall_thickness_ratio_used=config.wall_thickness_ratio,
        enforcement_mode=config.enforcement_mode.value,
        allocation_strategy=config.allocation_strategy.value,
        surplus_distributed_m2=alloc.surplus_distributed_m2,
        rooms_at_min=alloc.rooms_at_min,
        rooms_clamped_at_max=alloc.rooms_clamped_at_max,
        packing_basis=f"heuristic_v1_static_{config.packing_efficiency}",
        heuristic_packing_check_warning=outcome.heuristic_packing_check_warning,
        width_feasibility_per_room=MappingProxyType(
            dict(outcome.width_feasibility_per_room)
        ),
        grid_bay_feasibility_per_room=MappingProxyType(
            dict(outcome.grid_bay_feasibility_per_room)
        ),
        placement_risk_level=outcome.placement_risk_level,
        placement_risk_score=outcome.placement_risk_score,
        unverified_nbc_rows_used=unverified_nbc_rows,
        other_sizing_behavior="pooled_v1" if any(
            r.category == RoomCategory.OTHER for r in rooms
        ) else "n/a",
        rule_trace=tuple(_build_rule_trace(
            tier, accuracy, alloc, outcome, unverified_nbc_rows, auto_lift_trace,
        )),
    )

    return RoomSizedCandidate(
        corridor_designed_candidate=candidate,
        room_size_table=table,
        provenance=provenance,
    )


# =============================================================================
# Helpers
# =============================================================================


def _resolve_dwelling_tier(
    candidate: CorridorDesignedCandidate,
    brief: FloorRoomBrief,
    config: RoomSizingConfig,
) -> tuple[DwellingSizeTier, TierResolutionAccuracy, float | None]:
    """Per § 4.1 / § 14.25 / § 14.33."""
    if config.dwelling_tier_override is not None:
        return (
            config.dwelling_tier_override,
            TierResolutionAccuracy.OVERRIDE_SUPPLIED,
            None,
        )
    if config.assumed_total_dwelling_area_m2 is not None:
        a = config.assumed_total_dwelling_area_m2
        tier = (
            DwellingSizeTier.SMALL
            if a <= DWELLING_TIER_THRESHOLD_M2
            else DwellingSizeTier.LARGE
        )
        return tier, TierResolutionAccuracy.OVERRIDE_SUPPLIED, a
    # D2 (S34 audit): normalise whitespace and separators so labels like
    # "Ground Floor", "ground-floor", "GF ", "Ground_Floor" all resolve to the
    # ground-floor branch. Previously a literal lower()-only check missed
    # "ground floor" (with space) and silently routed it to multi-floor
    # APPROXIMATE_DEFENSIVE_LARGE.
    label_normalised = (
        brief.floor_label.lower().strip().replace("-", "_").replace(" ", "_")
    )
    is_multi_floor = label_normalised not in (
        "ground", "ground_floor", "gf",
    )
    if is_multi_floor:
        return (
            DwellingSizeTier.LARGE,
            TierResolutionAccuracy.APPROXIMATE_DEFENSIVE_LARGE,
            None,
        )
    envelope_areas = sum(_env_area(e) for e in candidate.corridor_path.envelopes)
    tier = (
        DwellingSizeTier.SMALL
        if envelope_areas <= DWELLING_TIER_THRESHOLD_M2
        else DwellingSizeTier.LARGE
    )
    return tier, TierResolutionAccuracy.EXACT, envelope_areas


def _env_area(env: ZoneBandEnvelope) -> float:
    """Compute area from rectangle bounds (the spec uses 'e.area_m2'
    pseudo-attribute; ZoneBandEnvelope only exposes width_m / depth_m)."""
    return env.width_m * env.depth_m


def _grid_bays(grid: Grid) -> tuple[float, float]:
    """Return (bay_min_m, bay_max_m) for the grid.

    D3 (S34 audit): C9 v1 ASSUMES the grid is uniform — i.e. every bay along the
    x-axis has size grid.bay_x_m and every bay along y-axis has size grid.bay_y_m.
    C7 v1 produces such grids. If a future C7 ships non-uniform bay layouts
    (e.g. variable bay sizes for transfer-beam regions), the (bay_x_m, bay_y_m)
    scalars would no longer represent the full grid and Inv 18 grid-bay
    feasibility classification would silently use wrong inputs.

    The defensive check below prefers explicit failure over silent wrong-answer.
    If C7 introduces per-bay sizing in a future version, C9 should be updated to
    consume the per-bay tuple instead of the (x, y) scalars; until then this
    sanity-check guards against a contract drift.
    """
    if not (grid.bay_x_m > 0 and grid.bay_y_m > 0):
        raise ValueError(
            f"C9 _grid_bays: grid.bay_x_m and grid.bay_y_m must both be > 0; "
            f"got bay_x_m={grid.bay_x_m}, bay_y_m={grid.bay_y_m}. "
            f"C9 v1 assumes uniform-bay grids per C7 v1 contract."
        )
    bays = (grid.bay_x_m, grid.bay_y_m)
    return min(bays), max(bays)


def _materialise_rooms(
    brief: FloorRoomBrief,
    tier: DwellingSizeTier,
) -> tuple[list[RoomSizeRequirement], tuple[str, ...], tuple[str, ...]]:
    """Build the RoomSizeRequirement list for the brief.

    Default v1 priority order (per § 4.5):
      1. master BEDROOM
      2. typical BEDROOMs
      3. KITCHEN
      4. LIVING
      5. master BATHROOM (if any)
      6. typical BATHROOMs
      7. POOJA
      8. UTILITY
      9. OTHER

    Returns:
        (rooms_list,
         tuple_of_room_ids_using_unverified_nbc_rows,
         tuple_of_auto_lift_trace_entries)  # D4 (S34 audit)
    """
    rooms: list[RoomSizeRequirement] = []
    unverified: list[str] = []
    auto_lift: list[str] = []
    next_priority = 1

    # ---- BEDROOMs ----
    # Per Spec #2 v0.11 LOCKED (C9 Amendment for B-NEW-T3):
    # is_master is gated by brief.has_master_bedroom so multi-floor
    # orchestration (Spec #4) can suppress master designation on
    # non-master floors. Default has_master_bedroom=True preserves
    # v0.7 byte-identical behaviour for single-floor callers.
    for i in range(brief.bedroom_count):
        is_master = (i == 0) and brief.has_master_bedroom
        room_id = f"BEDROOM_{i + 1}"
        rooms.append(_make_room(
            room_id=room_id,
            category=RoomCategory.BEDROOM,
            tier=tier,
            is_master=is_master,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- KITCHEN ----
    if brief.has_kitchen:
        rooms.append(_make_room(
            room_id="KITCHEN_1",
            category=RoomCategory.KITCHEN,
            tier=tier,
            is_master=False,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- LIVING ----
    if brief.has_living:
        rooms.append(_make_room(
            room_id="LIVING_1",
            category=RoomCategory.LIVING,
            tier=tier,
            is_master=False,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- BATHROOMs (master first, then typical) ----
    #
    # v1 LIMITATION (D1): every BATHROOM is hard-coded to BathroomSubtype.COMBINED.
    # FloorRoomBrief.bathroom_count is a scalar with no per-bathroom subtype info,
    # so the orchestrator cannot distinguish wc_only / bath_only briefs in v1.
    # Consequence: nbc_table SMALL+wc_only and SMALL+bath_only / LARGE+bath_only
    # rows are unreachable through size_rooms() in v1; they are usable only via
    # direct nbc_table.lookup_nbc_minimum() calls. Filed as B-208 (extend
    # FloorRoomBrief schema with per-bathroom subtype tuple). Until then, every
    # bathroom uses the COMBINED row for its tier.
    for i in range(brief.bathroom_count):
        # Per Spec #2 v0.11 LOCKED (C9 Amendment for B-NEW-T3):
        # bathroom #1 master is gated by brief.has_master_bedroom to keep
        # the en-suite coupling (Spec #2 § 3.4) consistent — if the floor
        # doesn't host the master bedroom, it doesn't host the en-suite
        # master bathroom either.
        is_master = (i == 0) and brief.has_master_bedroom
        room_id = f"BATHROOM_{i + 1}"
        rooms.append(_make_room(
            room_id=room_id,
            category=RoomCategory.BATHROOM,
            tier=tier,
            is_master=is_master,
            priority=next_priority,
            bathroom_subtype=BathroomSubtype.COMBINED,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- POOJA ----
    if brief.has_pooja:
        rooms.append(_make_room(
            room_id="POOJA_1",
            category=RoomCategory.POOJA,
            tier=tier,
            is_master=False,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- UTILITY ----
    if brief.has_utility:
        rooms.append(_make_room(
            room_id="UTILITY_1",
            category=RoomCategory.UTILITY,
            tier=tier,
            is_master=False,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
        ))
        next_priority += 1

    # ---- OTHER (pooled per § 14.34) ----
    for i, label in enumerate(brief.other_rooms):
        room_id = f"OTHER_{i + 1}"
        rooms.append(_make_room(
            room_id=room_id,
            category=RoomCategory.OTHER,
            tier=tier,
            is_master=False,
            priority=next_priority,
            unverified_acc=unverified,
            auto_lift_acc=auto_lift,
            other_subtype=label,
        ))
        next_priority += 1

    return rooms, tuple(unverified), tuple(auto_lift)


def _make_room(
    *,
    room_id: str,
    category: RoomCategory,
    tier: DwellingSizeTier,
    is_master: bool,
    priority: int,
    unverified_acc: list[str],
    auto_lift_acc: list[str],
    bathroom_subtype: BathroomSubtype | None = None,
    other_subtype: str = "",
) -> RoomSizeRequirement:
    """Build one RoomSizeRequirement. Records unverified-NBC use AND auto-lift
    events (D4 — S34 audit) so they surface in provenance.rule_trace.
    """

    # Resolve regulatory minimum
    if category == RoomCategory.OTHER:
        # OTHER has no NBC row in v1 — defaults to zero-minimum regulatory.
        regulatory = RegulatoryMinimum(
            area_m2=0.0,
            width_m=0.0,
            height_m=2.1,
            nbc_clause="(no NBC row in v1; OTHER pooled)",
            source_confidence=NBCSourceConfidence.SECONDARY_CONSENSUS,
        )
    else:
        regulatory = nbc_mod.lookup_nbc_minimum(
            tier=tier,
            category=category,
            is_master=is_master,
            bathroom_subtype=bathroom_subtype,
        )
    if regulatory.source_confidence == NBCSourceConfidence.SECONDARY_UNVERIFIED:
        unverified_acc.append(room_id)

    # Furniture-fit floor
    ff = ff_mod.lookup_furniture_floor(
        category=category,
        is_master=is_master,
        bathroom_subtype=bathroom_subtype,
    )

    liveability_min_area_m2 = max(regulatory.area_m2, ff.area_m2)
    liveability_min_width_m = max(regulatory.width_m, ff.min_width_m)

    # Targets / max
    target_m2 = tg_mod.lookup_target_m2(category=category, is_master=is_master)
    max_m2 = tg_mod.lookup_max_m2(category=category, is_master=is_master)

    # Inv 7 / Inv 8 sanity nudge: target / max must be >= liveability_min.
    # If furniture floor is generous and pushes liveability above the KB target,
    # lift target / max accordingly. This preserves the dataclass invariants
    # without the orchestrator hand-rolling exception cases.
    #
    # D4 (S34 audit): emit a rule_trace entry when this fires so callers see it
    # in provenance. Previously silent — could mask KB inconsistencies (e.g. a
    # furniture floor that always exceeds the KB target would be invisible
    # noise).
    if target_m2 < liveability_min_area_m2:
        original_target = target_m2
        target_m2 = liveability_min_area_m2
        auto_lift_acc.append(
            f"target_lifted[{room_id}]: kb_target={original_target} -> "
            f"liveability_min={liveability_min_area_m2} (furniture floor exceeds KB target)"
        )
    if max_m2 < target_m2:
        original_max = max_m2
        max_m2 = target_m2
        auto_lift_acc.append(
            f"max_lifted[{room_id}]: kb_max={original_max} -> target={target_m2} "
            f"(post-target-lift; ensures Inv 8)"
        )

    return RoomSizeRequirement(
        room_id=room_id,
        category=category,
        regulatory_minimum=regulatory,
        liveability_min_area_m2=liveability_min_area_m2,
        liveability_min_width_m=liveability_min_width_m,
        target_m2=target_m2,
        max_m2=max_m2,
        priority=priority,
        is_master=is_master,
        bathroom_subtype=bathroom_subtype,
        other_subtype=other_subtype,
    )


def _build_rule_trace(
    tier,
    accuracy,
    alloc,
    outcome,
    unverified_nbc_rows,
    auto_lift_trace,
) -> list[str]:
    trace = [
        f"tier={tier.value}",
        f"tier_resolution={accuracy.value}",
        f"surplus_for_distribution_m2={alloc.surplus_for_distribution_m2}",
        f"surplus_distributed_m2={alloc.surplus_distributed_m2}",
        f"unassigned_area_m2={alloc.unassigned_area_m2}",
        f"placement_risk_level={outcome.placement_risk_level.value}",
        f"placement_risk_score={outcome.placement_risk_score}",
    ]
    if outcome.heuristic_packing_check_warning:
        trace.append("heuristic_packing_check_warning=True")
    if unverified_nbc_rows:
        trace.append(f"unverified_nbc_rows_used={list(unverified_nbc_rows)}")
    # D4 (S34 audit): surface auto-lift events so KB inconsistencies are visible.
    trace.extend(auto_lift_trace)
    return trace


__all__ = [
    "size_rooms",
]
