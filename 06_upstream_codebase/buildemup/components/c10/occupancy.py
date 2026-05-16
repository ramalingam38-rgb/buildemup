"""
BuildemUp† — Component 10 — Phase 0.5 + Phase 2.5 occupancy module.

Per C10 SPEC v1.0 LOCKED § 3 (Q40 / F-v8-6 cluster-occupancy timing fix):

  - Phase 0.5 runs ONLY HARD-edge pairwise pre-screen. Fast-fail on
    clearly-impossible incompatibility.
  - Phase 2.5 runs cluster-occupancy validation AFTER Phase 2 merge
    converges, against final cluster composition.

If you put cluster-occupancy in Phase 0.5 against intermediate state,
you've recreated F-v8-6. The timing split is the bug fix.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Iterable

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c10.errors import (
    PreClusteringInfeasibleError,
    WetZoneInfeasibleError,
)
from buildemup.components.c10.schema import (
    EPSILON,
    RemediationHint,
    WetZoneCapacityWeights,
)


def fast_fail_pre_screen(
    hard_edges: Iterable[tuple[str, str]],
    acceptable_wall_sets: dict[str, tuple[str, ...]],
) -> None:
    """Phase 0.5 — pre-screen for HARD-edge incompatibility.

    For each HARD-edge pair (r1, r2):
      - Compute intersection of acceptable_wall_sets[r1] ∩
        acceptable_wall_sets[r2].
      - If empty: aggregate all infeasible pairs and raise
        PreClusteringInfeasibleError(failure_phase="pre_clustering").

    Memoisation: small N at v1 (3-5 hard edges); we don't bother with
    a memo cache here. The C10 spec § 3 mentions memo for the larger
    Phase 0.5 case; bounded computation makes it optional in practice.

    Args:
        hard_edges: iterable of (room_id_a, room_id_b) tuples.
        acceptable_wall_sets: maps room_id -> tuple of wall_ids.

    Raises:
        PreClusteringInfeasibleError if any HARD-edge pair has empty
            intersection.
    """
    infeasible_pairs: list[tuple[str, str]] = []
    for r1, r2 in hard_edges:
        s1 = set(acceptable_wall_sets.get(r1, ()))
        s2 = set(acceptable_wall_sets.get(r2, ()))
        if not (s1 & s2):
            # Order pairs deterministically.
            a, b = sorted([r1, r2])
            if (a, b) not in infeasible_pairs:
                infeasible_pairs.append((a, b))

    if not infeasible_pairs:
        return
    infeasible_pairs.sort()
    msg = (
        f"Pre-clustering HARD-edge incompatibility for "
        f"{len(infeasible_pairs)} pair(s): {infeasible_pairs}"
    )
    hints = tuple(
        RemediationHint(
            kind="alternative_routing",
            parameter=f"hard_edge_{a}_{b}",
            current_value=f"empty_intersection",
            suggested_value="relax HARD edge or expand acceptable_wall_sets",
            severity="high",
            human_readable=(
                f"No wall is acceptable for both {a!r} and {b!r}; "
                f"HARD-edge cluster cannot share a wall."
            ),
            retry_priority=10 + i,
            mutually_exclusive_with=(),
        )
        for i, (a, b) in enumerate(infeasible_pairs)
    )
    raise PreClusteringInfeasibleError(
        msg, remediation_hints=hints, failure_phase="pre_clustering",
    )


def cluster_occupancy_validate(
    clusters: dict[str, tuple[str, ...]],
    cluster_acceptable_walls: dict[str, set[str]],
    room_min_widths: dict[str, float],
    grid: Grid,
    capacity_weights: WetZoneCapacityWeights,
) -> None:
    """Phase 2.5 — authoritative occupancy validation.

    Per the F-v8-6 fix: this runs AFTER Phase 2 merge, against final
    cluster composition.

    For each cluster C:
        cluster_occupancy_m = Σ(room.liveability_min_width_m for room_id in C)
        wall_safety_margin_m = capacity_weights.wall_safety_margin_m
                               OR (2 * minimum_riser_spacing_m if 0)
    For each candidate wall w in intersection(acceptable_wall_sets of all
    members of C):
        usable = w.length_m - safety_margin
        spatially feasible iff cluster_occupancy_m <= usable

    If no spatially-feasible wall exists for cluster C, raise
    WetZoneInfeasibleError(failure_phase="post_clustering_spatial").

    Args:
        clusters: cluster_id -> tuple of room_ids.
        cluster_acceptable_walls: cluster_id -> set of wall_ids that all
            members share (from Phase 2's overlap-merge result).
        room_min_widths: room_id -> liveability_min_width_m.
        grid: Grid for wall length lookups.
        capacity_weights: WetZoneCapacityWeights.

    Raises:
        WetZoneInfeasibleError(failure_phase="post_clustering_spatial")
        on first spatially-infeasible cluster.
    """
    spacing = capacity_weights.minimum_riser_spacing_m
    margin = (
        capacity_weights.wall_safety_margin_m
        if capacity_weights.wall_safety_margin_m > 0.0
        else 2 * spacing
    )

    walls_by_id = {w.wall_id: w for w in grid.wall_segments_canonical()}

    for cluster_id, room_ids in clusters.items():
        occupancy = sum(
            room_min_widths.get(rid, 0.0) for rid in room_ids
        )
        candidate_walls = cluster_acceptable_walls.get(cluster_id, set())
        feasible_any = False
        for wall_id in candidate_walls:
            wall = walls_by_id.get(wall_id)
            if wall is None:
                continue
            usable = wall.length_m - margin
            if occupancy + EPSILON <= usable:
                feasible_any = True
                break

        if feasible_any:
            continue

        # Build remediation hints.
        hints = (
            RemediationHint(
                kind="manual_review",
                parameter="cluster_size",
                current_value=f"{occupancy:.3f}",
                suggested_value="split cluster or relax HARD edges",
                severity="high",
                human_readable=(
                    f"Cluster {cluster_id} occupies {occupancy:.2f}m which "
                    f"exceeds usable wall length on every candidate wall."
                ),
                retry_priority=20,
                mutually_exclusive_with=(),
            ),
        )
        raise WetZoneInfeasibleError(
            f"Cluster {cluster_id!r} (rooms {list(room_ids)}) has no "
            f"spatially-feasible wall after Phase 2 merge: "
            f"occupancy={occupancy:.2f}m, safety_margin={margin:.2f}m.",
            remediation_hints=hints,
            failure_phase="post_clustering_spatial",
        )


__all__ = [
    "fast_fail_pre_screen",
    "cluster_occupancy_validate",
]
