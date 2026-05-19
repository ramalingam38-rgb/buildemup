"""
BuildemUp† — Component 10 — Top-level orchestrator.

Per C10 SPEC v1.0 LOCKED § 2 (Contract). Executes Phases 0 → 5 against
each input candidate; aggregates results under partial-batch semantics
mirroring C9 § 14.40.

Public entry: ``plan_wet_zones(...)``.

†= placeholder name marker.
"""
from __future__ import annotations

import time

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c09.schema import (
    BathroomSubtype,
    PlacementRiskLevel as C9PlacementRiskLevel,
    RoomCategory,
    RoomSizedCandidate,
)
from buildemup.components.c10.assignment import (
    AssignmentResult,
    assign_clusters_to_walls,
)
from buildemup.components.c10.clustering import cluster_wet_rooms
from buildemup.components.c10.errors import (
    BatchWetZoneInfeasibleError,
    KBVersionMismatchError,
    PerCandidateError,
    PlumbingConfidenceTooLow,
    PreClusteringInfeasibleError,
    RemediationGraphError,
    WetZoneInfeasibleError,
    WetZonePlanError,
)
from buildemup.components.c10.kb_validator import (
    get_fixture_types_for,
    load_plumbing_fixture_profiles,
    load_plumbing_minimums,
    validate_plumbing_kbs_compatibility,
)
from buildemup.components.c10.occupancy import (
    cluster_occupancy_validate,
    fast_fail_pre_screen,
)
from buildemup.components.c10.provenance import (
    compute_risk_level,
    validate_remediation_graph,
)
from buildemup.components.c10.schema import (
    EPSILON,
    EnforcementMode,
    PlacementRiskLevel,
    RemediationHint,
    RiserAnchor,
    RiserGroup,
    TrapArmEstimate,
    TruncationReason,
    WallScoreVector,
    WetZoneCapacityWeights,
    WetZonePerformanceBudgets,
    WetZonePlan,
    WetZonePlanConfig,
    WetZonePlanProvenance,
    WetZonePlannedCandidate,
    WetZoneRiskBreakdown,
    WetZoneScoringWeights,
    compute_scoring_weights_hash,
)
from buildemup.components.c10.scoring import (
    acceptable_wall_set,
    filter_feasible_walls,
    rank_walls,
)
from buildemup.components.c10.trap_arm import (
    estimate_trap_arm,
    gate_unverified_rows,
    symbolic_bend_estimate,
    validate_inv_11,
)


# Lazy-init module-level cache for KB validator startup hook.
_KB_VALIDATED = False
_KB_WARNINGS: tuple[str, ...] = ()


def _ensure_kbs_validated() -> tuple[str, ...]:
    """Run validate_plumbing_kbs_compatibility at first call; cache result."""
    global _KB_VALIDATED, _KB_WARNINGS
    if not _KB_VALIDATED:
        _KB_WARNINGS = validate_plumbing_kbs_compatibility()
        _KB_VALIDATED = True
    return _KB_WARNINGS


def plan_wet_zones(
    room_sized_candidates: tuple[RoomSizedCandidate, ...],
    floor_room_brief,
    grid: Grid,
    plot_analysis,
    *,
    config: WetZonePlanConfig | None = None,
) -> tuple[WetZonePlannedCandidate, ...]:
    """C10 entry point.

    Per-candidate semantics: each candidate is processed independently;
    failures drop from the output tuple. If ALL candidates fail, raise
    BatchWetZoneInfeasibleError. Systemic errors (PlumbingConfidenceTooLow,
    KBVersionMismatchError, RemediationGraphError) short-circuit the batch.

    Args:
        room_sized_candidates: tuple of RoomSizedCandidate from C9.
        floor_room_brief: FloorRoomBrief for the floor.
        grid: Grid from C7.
        plot_analysis: PlotAnalysis carrying floor metadata.
        config: WetZonePlanConfig; default-constructed if None.

    Returns:
        Tuple of WetZonePlannedCandidate, one per successfully-planned
        candidate. Output tuple may be shorter than input.

    Raises:
        BatchWetZoneInfeasibleError if all candidates failed.
        PlumbingConfidenceTooLow if require_verified_plumbing=True and
            unverified rows used.
        KBVersionMismatchError on KB drift (raised lazily at first call).
    """
    if not isinstance(room_sized_candidates, tuple):
        raise TypeError(
            "room_sized_candidates must be tuple[RoomSizedCandidate, ...]"
        )
    if config is None:
        config = WetZonePlanConfig()

    _ensure_kbs_validated()

    minimums_kb = load_plumbing_minimums()
    profiles_kb = load_plumbing_fixture_profiles()

    successes: list[WetZonePlannedCandidate] = []
    candidate_errors: list[PerCandidateError] = []
    for cand in room_sized_candidates:
        try:
            successes.append(_plan_one_candidate(
                cand, floor_room_brief, grid, plot_analysis,
                config=config,
                plumbing_kb_version=minimums_kb.get("_kb_version", "unknown"),
                profiles_kb_version=profiles_kb.get("_kb_version", "unknown"),
            ))
        except PerCandidateError as e:
            candidate_errors.append(e)
        except (PlumbingConfidenceTooLow, KBVersionMismatchError, RemediationGraphError):
            # Systemic — propagate unchanged.
            raise

    if not successes and candidate_errors:
        raise BatchWetZoneInfeasibleError(
            f"All {len(candidate_errors)} candidate(s) failed; first: "
            f"{candidate_errors[0]!r}",
            candidate_errors=tuple(candidate_errors),
        )
    return tuple(successes)


# ===========================================================================
# Internal — per-candidate pipeline
# ===========================================================================


def _plan_one_candidate(
    cand: RoomSizedCandidate,
    floor_room_brief,
    grid: Grid,
    plot_analysis,
    *,
    config: WetZonePlanConfig,
    plumbing_kb_version: str,
    profiles_kb_version: str,
) -> WetZonePlannedCandidate:
    """Run Phases 0 → 5 against a single candidate."""
    runtime_start = time.monotonic()

    rooms = cand.room_size_table.rooms
    rooms_by_id = {r.room_id: r for r in rooms}

    # ---- Phase 0: filter walls + per-room acceptable_wall_sets ----
    feasible_walls = filter_feasible_walls(grid)
    if not feasible_walls:
        raise WetZoneInfeasibleError(
            "No feasible walls in grid (Phase 1a returned empty).",
            failure_phase="pre_clustering",
            remediation_hints=(),
        )

    acceptable_wall_sets: dict[str, tuple[str, ...]] = {}
    for room in rooms:
        if room.category in (
            RoomCategory.BATHROOM, RoomCategory.KITCHEN,
            RoomCategory.UTILITY, RoomCategory.POOJA,
        ):
            acceptable_wall_sets[room.room_id] = acceptable_wall_set(
                room.liveability_min_width_m, feasible_walls,
            )

    # Inv 15: every wet room has a non-empty acceptable_wall_set, else
    # the candidate is infeasible.
    for rid, walls in acceptable_wall_sets.items():
        if not walls:
            raise WetZoneInfeasibleError(
                f"Room {rid!r} has no acceptable walls (Phase 0).",
                failure_phase="pre_clustering",
                remediation_hints=(
                    RemediationHint(
                        kind="manual_review",
                        parameter="room_min_width",
                        current_value=str(rooms_by_id[rid].liveability_min_width_m),
                        suggested_value="reduce or expand grid envelope",
                        severity="high",
                        human_readable=(
                            f"Room {rid!r} requires "
                            f"{rooms_by_id[rid].liveability_min_width_m:.2f}m "
                            f"width but no eligible wall is long enough."
                        ),
                        retry_priority=5,
                    ),
                ),
            )

    # ---- Phase 0.5: HARD-edge pairwise pre-screen ----
    hard_edges = _derive_hard_edges(rooms_by_id)
    fast_fail_pre_screen(hard_edges, acceptable_wall_sets)

    # ---- Phase 1b: rank walls ----
    score_vectors = rank_walls(
        feasible_walls, grid=grid, weights=config.scoring_weights,
        scoring_profile_id=config.scoring_profile,
    )
    score_vectors_by_key = {
        (v.wall_id, v.category): v for v in score_vectors
    }

    # ---- Phase 2: cluster ----
    wet_rooms = list(acceptable_wall_sets.keys())
    hard_anti_edges = _derive_hard_anti_edges(rooms_by_id)

    # Pre-compute fixture types so the capacity_check closure can use them.
    fixture_types_per_room = _build_fixture_types_per_room(rooms)
    walls_by_id = {w.wall_id: w for w in grid.wall_segments_canonical()}

    def _merge_capacity_ok(
        merged_members: list[str], overlap_walls: set[str],
    ) -> bool:
        """Return True iff at least one wall in `overlap_walls` has
        capacity >= cluster's aggregated fixture-capacity weight.

        Prevents Phase 2 from creating clusters that Phase 3 cannot serve
        on any single wall (Q44 capacity-weight check)."""
        weight = 0.0
        for rid in merged_members:
            for ft in fixture_types_per_room.get(rid, ()):
                weight += config.capacity_weights.fixture_capacity_weights.get(ft, 1.0)
        if weight <= 0.0:
            return True            # POOJA-only cluster, no fixtures
        spacing = config.capacity_weights.minimum_riser_spacing_m
        for wid in overlap_walls:
            wall = walls_by_id.get(wid)
            if wall is None:
                continue
            wc = wall.length_m // spacing
            if weight <= wc + EPSILON:
                return True
        return False

    clusters, cluster_walls = cluster_wet_rooms(
        wet_rooms,
        hard_edges=hard_edges,
        hard_anti_edges=hard_anti_edges,
        acceptable_wall_sets=acceptable_wall_sets,
        capacity_check=_merge_capacity_ok,
    )

    # ---- Phase 2.5: post-merge cluster-occupancy validation ----
    room_min_widths = {
        r.room_id: r.liveability_min_width_m for r in rooms
    }
    cluster_occupancy_validate(
        clusters, cluster_walls, room_min_widths, grid,
        config.capacity_weights,
    )

    # ---- Phase 3: assign clusters to walls ----
    cluster_primary_category = _build_cluster_primary_category(
        clusters, rooms_by_id,
    )
    assignment = assign_clusters_to_walls(
        clusters, cluster_walls, cluster_primary_category,
        fixture_types_per_room,
        grid=grid,
        wall_score_vectors=score_vectors_by_key,
        scoring_weights=config.scoring_weights,
        capacity_weights=config.capacity_weights,
        max_states=config.max_backtrack_states,
        max_attempts=config.max_assignment_attempts,
        enable_relaxation_pass=config.enable_relaxation_pass,
    )

    # Build wet_wall_assignment per-room from cluster assignment.
    wet_wall_assignment: dict[str, str] = {}
    for cid, room_ids in clusters.items():
        wid = assignment.cluster_to_wall.get(cid)
        if wid is None:
            continue
        for rid in room_ids:
            wet_wall_assignment[rid] = wid

    # ---- Phase 4: trap-arm distances ----
    trap_arm_distances: dict[tuple[str, str], TrapArmEstimate] = {}
    bend_total = 0
    total_run = 0.0

    # Proxy depth used for the wet-strip near the wet wall. v1 simplification:
    # fixtures are always placed AT the wet wall, so the proxy depth is small
    # (~0.6m) representing the typical fixture-to-anchor offset. The worst-
    # case corner is (wall midpoint ± room_min_width / 2, _PROXY_DEPTH).
    _PROXY_DEPTH_M = 0.6

    for room in rooms:
        if room.room_id not in wet_wall_assignment:
            continue
        wid = wet_wall_assignment[room.room_id]
        wall = walls_by_id[wid]
        anchor_xy = (
            (wall.start_x_m + wall.end_x_m) / 2.0,
            (wall.start_y_m + wall.end_y_m) / 2.0,
        )
        # Build a wet-strip bbox: along the wall = liveability_min_width_m,
        # perpendicular to the wall = _PROXY_DEPTH_M.
        bbox = _wet_strip_bbox(
            wall, room.liveability_min_width_m, _PROXY_DEPTH_M,
            envelope_w=grid.envelope_width_m, envelope_d=grid.envelope_depth_m,
        )
        room_centre = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        for ft in fixture_types_per_room.get(room.room_id, ()):
            est = estimate_trap_arm(ft, bbox, anchor_xy)
            trap_arm_distances[(room.room_id, ft)] = est
            total_run += est.likely_bound_m
            bend_total += symbolic_bend_estimate(room_centre, anchor_xy)

    unverified, _warnings = validate_inv_11(
        trap_arm_distances, tolerance_m=config.trap_arm_tolerance_m,
    )
    gate_unverified_rows(
        unverified, require_verified=config.require_verified_plumbing,
    )

    # ---- Phase 5: build provenance + plan ----
    riser_groups = _build_riser_groups(
        clusters, assignment, walls_by_id,
    )
    kitchen_riser_group_id = _find_kitchen_riser_group_id(
        riser_groups, rooms_by_id,
    )
    plan = WetZonePlan(
        wet_wall_assignment=dict(wet_wall_assignment),
        riser_groups=riser_groups,
        kitchen_riser_group_id=kitchen_riser_group_id,
        fixture_types_per_room=fixture_types_per_room,
        trap_arm_distances=trap_arm_distances,
        total_wet_run_length_m=round(total_run, 6),
        symbolic_bend_estimate=bend_total,
        bend_estimation_mode="symbolic_v1",
        riser_count=assignment.riser_count,
        non_wet_room_buffer_zones=(),
        acceptable_wall_sets=acceptable_wall_sets,
    )

    risk_breakdown = _compute_risk_breakdown(
        assignment, plan, config,
    )

    rule_trace = (
        f"phase0_feasible_walls={len(feasible_walls)}",
        f"phase2_clusters={len(clusters)}",
        f"phase3_states_explored={assignment.states_explored}",
        f"phase4_total_run_m={round(total_run, 6)}",
    )

    # Performance budget warnings.
    perf_warnings: list[str] = []
    budgets = config.performance_budgets
    if len(score_vectors) > budgets.max_wall_score_vectors:
        perf_warnings.append(
            f"wall_scoring_breakdown count {len(score_vectors)} exceeds "
            f"budget {budgets.max_wall_score_vectors}"
        )
    if len(rule_trace) > budgets.max_provenance_rule_trace_entries:
        perf_warnings.append(
            f"rule_trace count {len(rule_trace)} exceeds budget "
            f"{budgets.max_provenance_rule_trace_entries}"
        )

    runtime_ms = int((time.monotonic() - runtime_start) * 1000)

    provenance = WetZonePlanProvenance(
        derived_at=time.time(),
        plot_analysis_trace_id=getattr(plot_analysis, "trace_id", "unknown"),
        floor_label=getattr(floor_room_brief, "floor_label", "ground"),
        plumbing_kb_version=plumbing_kb_version,
        fixture_profiles_kb_version=profiles_kb_version,
        enforcement_mode=config.enforcement_mode.value,
        pooja_adjacency_mode=config.pooja_adjacency_mode,
        scoring_profile=config.scoring_profile,
        scoring_weights_snapshot=config.scoring_weights,
        cluster_decisions=tuple(
            f"cluster {cid} -> wall {wid}"
            for cid, wid in sorted(assignment.cluster_to_wall.items())
        ),
        wall_scoring_breakdown=score_vectors,
        forced_culturally_discouraged=assignment.forced_culturally_discouraged,
        unverified_plumbing_rows_used=unverified,
        search_truncated=assignment.search_truncated,
        states_explored=assignment.states_explored,
        truncation_reason=assignment.truncation_reason,
        _observational_runtime_ms=runtime_ms,
        risk_breakdown=risk_breakdown,
        remediation_hints=(),
        performance_budget_warnings=tuple(perf_warnings),
        rule_trace=rule_trace,
    )

    return WetZonePlannedCandidate(
        room_sized_candidate=cand,
        wet_zone_plan=plan,
        provenance=provenance,
    )


# ===========================================================================
# Helpers
# ===========================================================================


def _derive_hard_edges(
    rooms_by_id: dict,
) -> tuple[tuple[str, str], ...]:
    """Derive HARD edges among WET rooms (those that get acceptable_wall_sets
    in Phase 0).

    v1: there are no HARD edges between wet rooms. Master_BR ↔ master_BA
    is an *adjacency* constraint enforced via Inv 5 (master BA's wall must
    lie in the master BR's acceptable side), not a cluster-sharing
    constraint. Phase 0.5 fast-fail therefore receives an empty tuple at
    v1; future versions may add wet-stack-share rules.
    """
    return ()


def _derive_hard_anti_edges(
    rooms_by_id: dict,
) -> tuple[tuple[str, str], ...]:
    """POOJA must not share a cluster with any wet room."""
    poojas = [
        r.room_id for r in rooms_by_id.values()
        if r.category == RoomCategory.POOJA
    ]
    wets = [
        r.room_id for r in rooms_by_id.values()
        if r.category in (
            RoomCategory.BATHROOM, RoomCategory.KITCHEN, RoomCategory.UTILITY,
        )
    ]
    edges: list[tuple[str, str]] = []
    for p in poojas:
        for w in wets:
            edges.append((p, w))
    return tuple(edges)


def _build_fixture_types_per_room(rooms) -> dict[str, tuple[str, ...]]:
    """Per-room fixture_type tuple from the profiles KB.

    **Strict mode (S37 patch — addresses S36 critique #7):** missing
    profile rows for any wet category surface as KBVersionMismatchError
    rather than silently falling back to defaults. The fallback was
    masking Inv 16 violations under KB regression.

    Profile rows for the 3 bathroom subtypes + kitchen + utility are
    expected to exist; if they don't, the KB has drifted and that should
    be caught at the orchestrator boundary, not papered over.
    """
    out: dict[str, tuple[str, ...]] = {}
    for r in rooms:
        if r.category == RoomCategory.BATHROOM:
            subtype = (
                r.bathroom_subtype.value if r.bathroom_subtype is not None
                else "combined"
            )
            try:
                out[r.room_id] = get_fixture_types_for("bathroom", subtype)
            except KeyError as e:
                raise KBVersionMismatchError(
                    f"plumbing_fixture_profiles KB missing row for "
                    f"(room_category='bathroom', bathroom_subtype="
                    f"{subtype!r}); needed by room {r.room_id!r}. "
                    f"Inv 16 cannot be satisfied. Original lookup error: {e}"
                ) from e
        elif r.category == RoomCategory.KITCHEN:
            try:
                out[r.room_id] = get_fixture_types_for("kitchen", None)
            except KeyError as e:
                raise KBVersionMismatchError(
                    f"plumbing_fixture_profiles KB missing row for "
                    f"room_category='kitchen'; needed by room "
                    f"{r.room_id!r}. Original lookup error: {e}"
                ) from e
        elif r.category == RoomCategory.UTILITY:
            try:
                out[r.room_id] = get_fixture_types_for("utility", None)
            except KeyError as e:
                raise KBVersionMismatchError(
                    f"plumbing_fixture_profiles KB missing row for "
                    f"room_category='utility'; needed by room "
                    f"{r.room_id!r}. Original lookup error: {e}"
                ) from e
        # POOJA, BEDROOM, LIVING, OTHER: not wet — no fixture types.
    return out


def _build_cluster_primary_category(
    clusters: dict[str, tuple[str, ...]],
    rooms_by_id: dict,
) -> dict[str, str]:
    """Primary category per cluster: bathroom > kitchen > utility > pooja."""
    priority = {
        RoomCategory.BATHROOM: 1,
        RoomCategory.KITCHEN:  2,
        RoomCategory.UTILITY:  3,
        RoomCategory.POOJA:    4,
    }
    out: dict[str, str] = {}
    for cid, room_ids in clusters.items():
        cats = [
            rooms_by_id[r].category for r in room_ids
            if r in rooms_by_id and rooms_by_id[r].category in priority
        ]
        if not cats:
            out[cid] = "bathroom"
            continue
        cats.sort(key=lambda c: priority[c])
        out[cid] = cats[0].value
    return out


def _build_riser_groups(
    clusters: dict[str, tuple[str, ...]],
    assignment: AssignmentResult,
    walls_by_id: dict,
) -> tuple[RiserGroup, ...]:
    """Build one RiserGroup per cluster (v1 invariant: 1 anchor each)."""
    groups: list[RiserGroup] = []
    for cid in sorted(assignment.cluster_to_wall.keys()):
        wid = assignment.cluster_to_wall[cid]
        wall = walls_by_id[wid]
        anchor_position = wall.length_m / 2.0
        anchor_xy = (
            round((wall.start_x_m + wall.end_x_m) / 2.0, 6),
            round((wall.start_y_m + wall.end_y_m) / 2.0, 6),
        )
        anchor = RiserAnchor(
            wall_id=wid,
            anchor_position_m=round(anchor_position, 6),
            riser_anchor_xy=anchor_xy,
            column_id=None,
            snap_distance_m=None,
        )
        groups.append(RiserGroup(
            group_id=f"rg_{cid}",
            anchors=(anchor,),
            wet_room_ids=tuple(sorted(clusters[cid])),
        ))
    return tuple(groups)


def _find_kitchen_riser_group_id(
    riser_groups: tuple[RiserGroup, ...], rooms_by_id: dict,
) -> str | None:
    for rg in riser_groups:
        for rid in rg.wet_room_ids:
            r = rooms_by_id.get(rid)
            if r is not None and r.category == RoomCategory.KITCHEN:
                return rg.group_id
    return None


def _wet_strip_bbox(
    wall, room_min_width_m: float, proxy_depth_m: float,
    *, envelope_w: float, envelope_d: float,
) -> tuple[float, float, float, float]:
    """Compute a bbox proxy representing the wet strip adjacent to ``wall``.

    The fixture is assumed AT the wet wall; the bbox runs along the wall
    for ``room_min_width_m`` (centred at the wall midpoint) and extends
    inward by ``proxy_depth_m``.

    Args:
        wall: WallSegment.
        room_min_width_m: liveability_min_width_m of the room.
        proxy_depth_m: small inward depth (typically 0.6m).
        envelope_w: grid envelope width.
        envelope_d: grid envelope depth.

    Returns:
        (x_min, y_min, x_max, y_max).
    """
    # Local import to avoid circular import.
    from buildemup.components.c07.wall_segment import WallAxis
    half_w = room_min_width_m / 2.0
    mid_x = (wall.start_x_m + wall.end_x_m) / 2.0
    mid_y = (wall.start_y_m + wall.end_y_m) / 2.0
    if wall.axis == WallAxis.SOUTH:
        # Wall along bottom (y = 0). Strip goes inward (positive y).
        return (mid_x - half_w, 0.0, mid_x + half_w, proxy_depth_m)
    if wall.axis == WallAxis.NORTH:
        # Wall along top (y = envelope_d). Strip goes inward (negative y).
        return (
            mid_x - half_w, envelope_d - proxy_depth_m,
            mid_x + half_w, envelope_d,
        )
    if wall.axis == WallAxis.WEST:
        # Wall along left (x = 0). Strip goes inward (positive x).
        return (0.0, mid_y - half_w, proxy_depth_m, mid_y + half_w)
    # WallAxis.EAST: wall along right.
    return (
        envelope_w - proxy_depth_m, mid_y - half_w,
        envelope_w, mid_y + half_w,
    )


def _compute_risk_breakdown(
    assignment: AssignmentResult,
    plan: WetZonePlan,
    config: WetZonePlanConfig,
) -> WetZoneRiskBreakdown:
    """Phase 5 weighted-severity. Carried v0.6/v0.7 0.5/1.0/1.5 weights;
    tuned via B-219."""
    opt_score = 0.0
    if assignment.search_truncated:
        opt_score += 1.0
    if config.max_risers is not None and assignment.riser_count >= config.max_risers:
        opt_score += 1.0

    eng_score = 0.0
    if assignment.forced_culturally_discouraged:
        eng_score += 1.0

    cult_score = 0.0
    if config.pooja_adjacency_mode == "soft":
        cult_score += 0.5

    return WetZoneRiskBreakdown(
        optimization_risk=compute_risk_level(opt_score),
        optimization_score=opt_score,
        engineering_risk=compute_risk_level(eng_score),
        engineering_score=eng_score,
        cultural_risk=compute_risk_level(cult_score),
        cultural_score=cult_score,
    )


__all__ = ["plan_wet_zones"]
