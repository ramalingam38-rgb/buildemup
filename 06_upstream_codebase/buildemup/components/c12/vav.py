"""
BuildemUp — Component 12 — vertical alignment verification (VAV)
=================================================================

Per C12 SPEC v1.0 LOCKED § 3 Phase 2 step 3 (VAV).

VAV checks that alignment-relevant features (staircase, wet-zone
stacks, structural columns) are aligned across all floors of a
multi-floor candidate within the configured tolerance.

v1 SCOPE (per v0.5-A2 guarantee boundary):
- Point-based alignment: feature centroid (x, y) consistency.
- Volume-based alignment (full 3D trajectory + shaft continuity)
  is B-C12-VOLUMETRIC-ALIGNMENT post-v1.

Algorithm:
1. For each tracked feature (e.g., "staircase_1", "wet_stack_a"):
   a. Compute its centroid (x, y) on each floor that contains it.
   b. Compute consensus position = element-wise mean across floors.
   c. Compute per-floor delta = max(|x_floor - x_consensus|,
      |y_floor - y_consensus|).
   d. Feature is aligned iff max_floor_delta ≤ tolerance.
2. Compute overall max-misalignment = max(max_floor_delta) across
   features.
3. Build VerticalAlignmentReport.
"""
from __future__ import annotations

from .schema import PlacedCandidate, PlacedRoom, VerticalAlignmentReport


def _feature_centroids_per_floor(
    *,
    per_floor_placements: tuple[tuple[str, PlacedCandidate], ...],
    feature_room_ids_by_floor: dict[str, set[str]],
) -> dict[str, dict[str, tuple[float, float]]]:
    """For each feature room_id, build a dict of
    floor_label → (centroid_x, centroid_y).

    Returns a NEW dict per call (no mutation of inputs).
    """
    out: dict[str, dict[str, tuple[float, float]]] = {}
    for floor_label, pc in per_floor_placements:
        feature_ids = feature_room_ids_by_floor.get(floor_label, set())
        for room in pc.placed_rooms:
            if room.room_id not in feature_ids:
                continue
            cx = room.x_m + room.width_m / 2.0
            cy = room.y_m + room.depth_m / 2.0
            out.setdefault(room.room_id, {})[floor_label] = (cx, cy)
    return out


def _max_misalignment_for_feature(
    floor_centroids: dict[str, tuple[float, float]],
) -> float:
    """For one feature appearing on multiple floors, compute the
    maximum distance from the consensus (mean) centroid to any
    floor's centroid.

    Uses Chebyshev distance (max of |dx|, |dy|) so the tolerance
    is interpretable as "feature drifts by ≤ tolerance on either
    axis."

    Returns 0.0 if the feature is on ≤ 1 floor (trivially aligned).
    """
    if len(floor_centroids) <= 1:
        return 0.0
    xs = [c[0] for c in floor_centroids.values()]
    ys = [c[1] for c in floor_centroids.values()]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    max_delta = 0.0
    for cx, cy in floor_centroids.values():
        delta = max(abs(cx - mean_x), abs(cy - mean_y))
        if delta > max_delta:
            max_delta = delta
    return max_delta


def verify_vertical_alignment(
    *,
    per_floor_placements: tuple[tuple[str, PlacedCandidate], ...],
    feature_room_ids_by_floor: dict[str, set[str]],
    tolerance_m: float,
    current_retry_index: int = 0,
    delta_history: tuple[float, ...] = (),
) -> VerticalAlignmentReport:
    """Run VAV over a multi-floor placement.

    Args:
      per_floor_placements: the placed per-floor candidates.
      feature_room_ids_by_floor: which room_ids are alignment-relevant
        on each floor (typically derived from FloorRoomBrief +
        operator class lineage for "staircase" / "wet_zone_column").
      tolerance_m: max acceptable Chebyshev distance from consensus
        centroid (default 0.02m per v0.2-A8).
      current_retry_index: which MFRA retry this VAV is for
        (0 = initial, 1+ = post-retry).
      delta_history: tuple of prior δ values from earlier retry
        iterations (passed in by MFRA for monotonic-δ tracking).

    Returns: VerticalAlignmentReport.
    """
    feature_centroids = _feature_centroids_per_floor(
        per_floor_placements=per_floor_placements,
        feature_room_ids_by_floor=feature_room_ids_by_floor,
    )

    misaligned: list[str] = []
    max_misalignment = 0.0
    for feature_id, floor_centroids in feature_centroids.items():
        delta = _max_misalignment_for_feature(floor_centroids)
        if delta > tolerance_m:
            misaligned.append(feature_id)
        if delta > max_misalignment:
            max_misalignment = delta

    converged = len(misaligned) == 0

    return VerticalAlignmentReport(
        converged=converged,
        retries_used=current_retry_index,
        delta_progression=delta_history + (max_misalignment,),
        final_max_misalignment_m=max_misalignment,
        misaligned_features=tuple(sorted(misaligned)),
    )


__all__ = ["verify_vertical_alignment"]
