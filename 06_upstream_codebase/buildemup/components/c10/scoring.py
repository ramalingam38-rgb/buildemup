"""
BuildemUp† — Component 10 — Phase 1a (feasibility filter) + Phase 1b
(per-wall ranking) module.

Per C10 SPEC v1.0 LOCKED § 3:
  - Phase 1a: eligibility = length_m >= 1.5m AND WallTag.EXTERNAL in tags.
  - Phase 1b: emit WallScoreVector(engineering_score, cultural_score,
    adjacency_score) with scoring_weights_hash for self-contained replay.

Production code uses Grid.wall_segments_canonical() (W8 invariant).

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c07.wall_segment import WallAxis, WallSegment, WallTag
from buildemup.components.c10.schema import (
    EPSILON,
    WallScoreVector,
    WetZoneScoringWeights,
    compute_scoring_weights_hash,
)


# Min wall length to be considered eligible. Per spec § 3 Phase 1a.
# B-215 refinement pending (KB-driven per-category minimum).
_MIN_WALL_LENGTH_M = 1.5


def filter_feasible_walls(grid: Grid) -> tuple[WallSegment, ...]:
    """Phase 1a: filter walls by `length_m >= 1.5m AND EXTERNAL`.

    Uses canonical accessor (W8 enforcement).
    """
    return tuple(
        w for w in grid.wall_segments_canonical()
        if w.length_m + EPSILON >= _MIN_WALL_LENGTH_M
        and WallTag.EXTERNAL in w.tags
    )


def _axis_class(
    axis: WallAxis,
    category: str,
    *,
    cultural_axis_preferences: Mapping[str, set[WallAxis]] | None = None,
) -> str:
    """Return PREFERRED / NEUTRAL / DISCOURAGED classification for the
    given (wall axis, category) pair.

    v1 baseline: in absence of orientation/Vastu inputs, return NEUTRAL.
    Real C6 OrientedCandidate integration is a B-217-class extension;
    here we honour the contract without prescribing axis values.
    """
    if cultural_axis_preferences is None:
        return "neutral"
    if axis in cultural_axis_preferences.get(f"{category}_preferred", set()):
        return "preferred"
    if axis in cultural_axis_preferences.get(f"{category}_discouraged", set()):
        return "discouraged"
    return "neutral"


def _cultural_score(
    weights: WetZoneScoringWeights, category: str, axis_class: str,
) -> float:
    if category == "bathroom":
        if axis_class == "preferred":
            return weights.bathroom_axis_preferred
        if axis_class == "discouraged":
            return weights.bathroom_axis_discouraged
        return weights.bathroom_axis_neutral
    if category == "pooja":
        if axis_class == "preferred":
            return weights.pooja_axis_preferred
        if axis_class == "discouraged":
            return weights.pooja_axis_discouraged
        return weights.pooja_axis_neutral
    # Default for kitchen, utility: neutral middle.
    return 0.5


def rank_walls(
    feasible_walls: Iterable[WallSegment],
    *,
    grid: Grid,
    weights: WetZoneScoringWeights,
    categories: tuple[str, ...] = ("bathroom", "kitchen", "utility", "pooja"),
    cultural_axis_preferences: Mapping[str, set[WallAxis]] | None = None,
    scoring_profile_id: str = "neutral",
) -> tuple[WallScoreVector, ...]:
    """Phase 1b: emit one WallScoreVector per (wall, category) pair.

    engineering_score = column_alignment_bonus (if a column lies on the wall)
                      + wall_length_sufficiency_bonus.
    cultural_score    = weights.{cat}_axis_{class}.
    adjacency_score   = 0.0 at v1 baseline; populated when caller passes
                      adjacency-aware weights via the cultural_axis_preferences
                      hook (post-v1 expansion).

    Result tuple sorted lex-ASC by (wall_id, category) for deterministic
    serialisation.
    """
    weights_hash = compute_scoring_weights_hash(weights)
    feasible_walls = list(feasible_walls)
    cols_on_wall = {
        w.wall_id: _wall_has_column(w, grid) for w in feasible_walls
    }
    out: list[WallScoreVector] = []
    for wall in feasible_walls:
        for cat in categories:
            eng = (
                (weights.column_alignment_bonus if cols_on_wall[wall.wall_id] else 0.0)
                + weights.wall_length_sufficiency_bonus
            )
            cult_class = _axis_class(
                wall.axis, cat,
                cultural_axis_preferences=cultural_axis_preferences,
            )
            cult = _cultural_score(weights, cat, cult_class)
            adj = 0.0
            out.append(WallScoreVector(
                wall_id=wall.wall_id,
                category=cat,
                engineering_score=round(eng, 6),
                cultural_score=round(cult, 6),
                adjacency_score=round(adj, 6),
                scoring_profile_id=scoring_profile_id,
                scoring_weights_hash=weights_hash,
            ))
    out.sort(key=lambda v: (v.wall_id, v.category))
    return tuple(out)


def total_score(
    vec: WallScoreVector, weights: WetZoneScoringWeights,
) -> float:
    """Weighted sum used by Phase 3 greedy assignment (and by tests)."""
    return (
        weights.weight_engineering * vec.engineering_score
        + weights.weight_cultural   * vec.cultural_score
        + weights.weight_adjacency  * vec.adjacency_score
    )


def _wall_has_column(wall: WallSegment, grid: Grid) -> bool:
    """True iff at least one column position coincides with wall endpoints
    or the wall midline. Approximation suitable for v1; B-NNN refinement
    can use exact-overlap geometry."""
    for col in grid.columns:
        # Wall is axis-aligned. Column on the wall iff its (x,y) lies
        # within the wall's start->end segment +/- tolerance.
        if abs(wall.end_x_m - wall.start_x_m) < 1e-6:    # vertical wall
            same_x = abs(col.x_m - wall.start_x_m) < 1e-3
            in_y = (
                min(wall.start_y_m, wall.end_y_m) - 1e-3
                <= col.y_m
                <= max(wall.start_y_m, wall.end_y_m) + 1e-3
            )
            if same_x and in_y:
                return True
        else:                                            # horizontal wall
            same_y = abs(col.y_m - wall.start_y_m) < 1e-3
            in_x = (
                min(wall.start_x_m, wall.end_x_m) - 1e-3
                <= col.x_m
                <= max(wall.start_x_m, wall.end_x_m) + 1e-3
            )
            if same_y and in_x:
                return True
    return False


def acceptable_wall_set(
    room_min_width_m: float,
    feasible_walls: Iterable[WallSegment],
) -> tuple[str, ...]:
    """Phase 0 per-room acceptable-wall set: walls whose length is at
    least the room's liveability_min_width_m.

    Determinism: result sorted lex-ASC by wall_id.
    """
    out = sorted(
        w.wall_id for w in feasible_walls
        if w.length_m + EPSILON >= room_min_width_m
    )
    return tuple(out)


__all__ = [
    "filter_feasible_walls",
    "rank_walls",
    "total_score",
    "acceptable_wall_set",
]
