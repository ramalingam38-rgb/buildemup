"""
BuildemUp† — Component 10 — Phase 3 (Wall assignment) module.

Per C10 SPEC v1.0 LOCKED § 3 Phase 3:
  - Greedy + bounded backtracking with `max_backtrack_states`.
  - Q36 interim DFU-aware capacity weighting via
    capacity_weights.fixture_capacity_weights.
  - wall_reuse_penalty applied when a wall is already used by another
    cluster.
  - forced_culturally_discouraged emitted when a cluster's primary
    category is forced onto a discouraged axis.

Capacity check (Inv 17, REVISED v0.9 per Q44):
    cluster_capacity_weight = Σ(fixture_capacity_weights[ft]
                              for ft in fixtures of cluster's rooms)
    wall_capacity = floor(wall.length_m / minimum_riser_spacing_m)
    fits iff cluster_capacity_weight <= wall_capacity

†= placeholder name marker.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c10.errors import WetZoneInfeasibleError
from buildemup.components.c10.schema import (
    EPSILON,
    ForcedCultureOverride,
    RemediationHint,
    TruncationReason,
    WallScoreVector,
    WetZoneCapacityWeights,
    WetZoneScoringWeights,
)
from buildemup.components.c10.scoring import total_score


@dataclass(frozen=True)
class AssignmentResult:
    """Output of Phase 3 assignment."""
    cluster_to_wall: dict[str, str]                       # cluster_id -> wall_id
    riser_count: int
    forced_culturally_discouraged: tuple[ForcedCultureOverride, ...]
    states_explored: int
    truncation_reason: TruncationReason
    search_truncated: bool


def assign_clusters_to_walls(
    clusters: dict[str, tuple[str, ...]],
    cluster_acceptable_walls: dict[str, set[str]],
    cluster_primary_category: dict[str, str],
    fixture_types_per_room: dict[str, tuple[str, ...]],
    *,
    grid: Grid,
    wall_score_vectors: dict[tuple[str, str], WallScoreVector],
    scoring_weights: WetZoneScoringWeights,
    capacity_weights: WetZoneCapacityWeights,
    max_states: int = 100,
    max_attempts: int = 50,
    enable_relaxation_pass: bool = True,
) -> AssignmentResult:
    """Greedy + bounded backtracking assignment.

    Per C10 SPEC v1.0 LOCKED § 3 Phase 3 + C10 AMENDMENT v1.1 (S59 ext):
    if the strict pass exhausts the search bound, optionally fall back
    to a RELAXATION PASS over the full grid-wall set, emitting one
    ``ForcedCultureOverride`` per relaxed assignment. The relaxation
    keeps capacity as a hard gate but drops the
    ``cluster_acceptable_walls`` filter — useful on small plots where
    the per-cluster acceptable-wall sets are too sparse to satisfy
    every cluster simultaneously.

    Args:
        clusters: cluster_id -> tuple of room_ids (lex-ASC).
        cluster_acceptable_walls: cluster_id -> set of wall_ids common to
            all members.
        cluster_primary_category: cluster_id -> primary category string
            ("bathroom", "kitchen", "utility", "pooja").
        fixture_types_per_room: room_id -> tuple of fixture_type strings.
        grid: Grid for wall length lookups.
        wall_score_vectors: (wall_id, category) -> WallScoreVector.
        scoring_weights: scoring weights with reuse penalty.
        capacity_weights: per-fixture capacity weighting.
        max_states: bound for backtracking.
        max_attempts: bound for greedy retry.
        enable_relaxation_pass: per C10 AMENDMENT v1.1, when True (the
            new default) retry over the full wall set on strict
            exhaustion. False keeps the v1.0 strict-only semantics.

    Raises:
        WetZoneInfeasibleError(failure_phase="assignment") if neither
            the strict pass nor (when enabled) the relaxation pass
            finds a feasible assignment within bounds.
    """
    walls_by_id = {w.wall_id: w for w in grid.wall_segments_canonical()}

    # Precompute cluster capacity weight (per spec Phase 3).
    cluster_cap_weight: dict[str, float] = {}
    for cid, rids in clusters.items():
        weight = 0.0
        for rid in rids:
            for ft in fixture_types_per_room.get(rid, ()):
                weight += capacity_weights.fixture_capacity_weights.get(ft, 1.0)
        cluster_cap_weight[cid] = weight

    # Process clusters in seed order (lex-ASC of cluster_id).
    cluster_ids = sorted(clusters.keys())
    used_walls: dict[str, str] = {}     # cluster_id -> wall_id
    riser_count = 0
    states_explored = 0
    forced: list[ForcedCultureOverride] = []

    def _wall_score(
        cluster_id: str, wall_id: str, currently_used: dict[str, str],
    ) -> float:
        cat = cluster_primary_category.get(cluster_id, "bathroom")
        vec = wall_score_vectors.get((wall_id, cat))
        if vec is None:
            return float("-inf")
        score = total_score(vec, scoring_weights)
        # Reuse penalty if some other cluster already uses this wall.
        if wall_id in currently_used.values():
            score += scoring_weights.wall_reuse_penalty
        return score

    def _wall_capacity_ok(
        cluster_id: str, wall_id: str,
    ) -> bool:
        wall = walls_by_id.get(wall_id)
        if wall is None:
            return False
        wc = math.floor(wall.length_m / capacity_weights.minimum_riser_spacing_m)
        return cluster_cap_weight[cluster_id] <= wc + EPSILON

    # Greedy assignment with simple backtracking.
    def _try_assign(idx: int, current: dict[str, str]) -> bool:
        nonlocal states_explored
        if idx >= len(cluster_ids):
            return True
        cid = cluster_ids[idx]
        candidates = sorted(
            cluster_acceptable_walls.get(cid, set()),
            key=lambda w: (-_wall_score(cid, w, current), w),
        )
        for wall_id in candidates:
            states_explored += 1
            if states_explored > max_states:
                return False
            if not _wall_capacity_ok(cid, wall_id):
                continue
            current[cid] = wall_id
            if _try_assign(idx + 1, current):
                return True
            del current[cid]
        return False

    success = _try_assign(0, used_walls)
    relaxation_used = False
    truncation: TruncationReason
    if not success and enable_relaxation_pass:
        # C10 AMENDMENT v1.1 — strict greedy exhausted; retry over the
        # full wall set with capacity as the only hard gate. Every
        # assignment made by this pass is recorded as a
        # ForcedCultureOverride so downstream consumers can surface the
        # relaxation honestly to the user.
        used_walls.clear()
        all_wall_ids = set(walls_by_id.keys())
        relaxed_states = 0

        def _try_assign_relaxed(idx: int, current: dict[str, str]) -> bool:
            nonlocal relaxed_states
            if idx >= len(cluster_ids):
                return True
            cid = cluster_ids[idx]
            # Sort the full wall set by score (descending) so the best
            # available wall is tried first even outside the strict
            # acceptable set.
            wall_candidates = sorted(
                all_wall_ids,
                key=lambda w: (-_wall_score(cid, w, current), w),
            )
            for wall_id in wall_candidates:
                relaxed_states += 1
                if relaxed_states > max_states * 4:
                    # Generous bound — relaxation tries 4× the strict
                    # budget because the search space is much wider.
                    return False
                if not _wall_capacity_ok(cid, wall_id):
                    continue
                current[cid] = wall_id
                if _try_assign_relaxed(idx + 1, current):
                    return True
                del current[cid]
            return False

        success = _try_assign_relaxed(0, used_walls)
        if success:
            relaxation_used = True
            # Combine state counts so callers see the full work done.
            states_explored += relaxed_states
            # Record one ForcedCultureOverride per cluster whose
            # assigned wall fell OUTSIDE its strict acceptable set.
            for cid, wid in used_walls.items():
                strict_set = cluster_acceptable_walls.get(cid, set())
                if wid in strict_set:
                    continue  # acceptable assignment; nothing to flag
                cat = cluster_primary_category.get(cid, "bathroom")
                # Rejected alternatives = the cluster's strict
                # acceptable-set members it didn't get.
                rejected = tuple(
                    (w, "strict_acceptable_set_infeasible")
                    for w in sorted(strict_set)
                    if w in walls_by_id
                )
                forced.append(ForcedCultureOverride(
                    room_id=clusters[cid][0],
                    wall_id=wid,
                    category=cat,
                    rejected_alternatives=rejected,
                ))

    if not success:
        # Build informative remediation hints.
        hints = (
            RemediationHint(
                kind="increase_limit",
                parameter="max_risers",
                current_value="(implicit cluster cap)",
                suggested_value="raise wall_capacity ceiling or split cluster",
                severity="medium",
                human_readable="Cluster capacity weights exceed wall ceilings.",
                retry_priority=30,
                mutually_exclusive_with=("cluster_size",),
            ),
            RemediationHint(
                kind="manual_review",
                parameter="cluster_size",
                current_value=f"{sum(len(v) for v in clusters.values())}",
                suggested_value="reduce member rooms per cluster",
                severity="high",
                human_readable="Reduce per-cluster room count to lower capacity weight.",
                retry_priority=99,
                mutually_exclusive_with=("max_risers",),
            ),
        )
        truncation = (
            TruncationReason.MAX_STATES if states_explored > max_states
            else TruncationReason.INFEASIBLE_TERMINATED
        )
        relax_note = (
            " (relaxation pass also failed)" if enable_relaxation_pass
            else " (strict-only mode — set enable_relaxation_pass=True "
                 "for AMENDMENT v1.1 fallback)"
        )
        raise WetZoneInfeasibleError(
            f"Phase 3 wall assignment exhausted: states_explored="
            f"{states_explored}, clusters={list(cluster_ids)}{relax_note}",
            remediation_hints=hints,
            failure_phase="assignment",
        )
    _ = relaxation_used  # observability hook; future amendment may surface

    # Detect forced culturally-discouraged: when the assigned wall has
    # discouraged classification for the cluster's primary category.
    for cid, wid in used_walls.items():
        cat = cluster_primary_category.get(cid, "bathroom")
        vec = wall_score_vectors.get((wid, cat))
        if vec is None:
            continue
        # If cultural_score is the discouraged value (i.e., 0.0 for
        # neutral/discouraged profile), and there exists another wall in
        # the cluster's acceptable set with strictly higher cultural score,
        # this is a forced override.
        candidates = cluster_acceptable_walls.get(cid, set())
        better = [
            wall_score_vectors[(w, cat)]
            for w in candidates
            if (w, cat) in wall_score_vectors
            and wall_score_vectors[(w, cat)].cultural_score > vec.cultural_score + EPSILON
        ]
        if better:
            rejected = tuple(
                (b.wall_id, "capacity_or_search_bound")
                for b in sorted(better, key=lambda v: v.wall_id)
            )
            forced.append(ForcedCultureOverride(
                room_id=clusters[cid][0],     # representative
                wall_id=wid,
                category=cat,
                rejected_alternatives=rejected,
            ))

    riser_count = len(used_walls)
    truncation = (
        TruncationReason.MAX_STATES if states_explored > max_states
        else TruncationReason.COMPLETED
    )
    return AssignmentResult(
        cluster_to_wall=dict(used_walls),
        riser_count=riser_count,
        forced_culturally_discouraged=tuple(forced),
        states_explored=states_explored,
        truncation_reason=truncation,
        search_truncated=(truncation == TruncationReason.MAX_STATES),
    )


__all__ = ["AssignmentResult", "assign_clusters_to_walls"]
