"""
BuildemUp† — Component 10 — Phase 4 (Trap-arm distance) module.

Per C10 SPEC v1.0 LOCKED § 3 Phase 4 (Q42 + Q43 + Q34):
  - Manhattan worst-case-corner distance -> upper_bound_m.
  - Per-fixture likely_bound_m factor (LIKELY_BOUND_FACTORS_BY_FIXTURE).
  - Symbolic bend estimate via horizontal-first orthogonal routing
    convention (Q42).
  - Inv 11 dual-bound validation:
      RAISE iff likely_bound_m > MAX + tolerance AND
              upper_bound_m > MAX + tolerance.
      WARN iff only upper_bound_m > MAX + tolerance.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c10.errors import (
    PlumbingConfidenceTooLow,
    TrapArmDistanceExceededError,
)
from buildemup.components.c10.kb_validator import get_plumbing_minimum_for
from buildemup.components.c10.schema import (
    EPSILON,
    LIKELY_BOUND_FACTORS_BY_FIXTURE,
    RemediationHint,
    TrapArmEstimate,
)


def manhattan_worst_case(
    room_bbox: tuple[float, float, float, float],
    anchor_xy: tuple[float, float],
) -> float:
    """Compute Manhattan distance from the room's bbox-corner farthest
    from `anchor_xy` to `anchor_xy`.

    Args:
        room_bbox: (x_min, y_min, x_max, y_max) of the room's bounding box.
        anchor_xy: (x, y) of the riser anchor.

    Returns:
        upper_bound_m — the worst-case-corner Manhattan distance.
    """
    x_min, y_min, x_max, y_max = room_bbox
    ax, ay = anchor_xy
    corners = (
        (x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max),
    )
    return max(abs(cx - ax) + abs(cy - ay) for cx, cy in corners)


def estimate_trap_arm(
    fixture_type: str,
    room_bbox: tuple[float, float, float, float],
    anchor_xy: tuple[float, float],
) -> TrapArmEstimate:
    """Compute (upper_bound_m, likely_bound_m) for a fixture in a room.

    likely_bound_m = LIKELY_BOUND_FACTORS_BY_FIXTURE[fixture_type] *
                     upper_bound_m.

    If fixture_type is not in the factors table, falls back to 0.5
    (midpoint) — defensive only; v1 has all 7 fixture types pre-populated.
    """
    upper = manhattan_worst_case(room_bbox, anchor_xy)
    factor = LIKELY_BOUND_FACTORS_BY_FIXTURE.get(fixture_type, 0.5)
    likely = factor * upper
    return TrapArmEstimate(
        upper_bound_m=round(upper, 6),
        likely_bound_m=round(likely, 6),
    )


def symbolic_bend_estimate(
    fixture_xy: tuple[float, float],
    anchor_xy: tuple[float, float],
) -> int:
    """Q42 horizontal-first orthogonal routing convention.

    From fixture_xy = (fx, fy), route along x-axis first to (anchor_x, fy),
    then along y-axis to (anchor_x, anchor_y).

    Bend count:
      - 0 if fixture lies exactly on the anchor.
      - 0 if collinear-on-route (one of dx, dy is 0).
      - 1 if either dx or dy ends up zero after the horizontal step
        (exactly aligned on one axis).
      - 2 in the general case (both dx and dy non-zero).
    """
    fx, fy = fixture_xy
    ax, ay = anchor_xy
    dx = ax - fx
    dy = ay - fy
    if abs(dx) < EPSILON and abs(dy) < EPSILON:
        return 0
    if abs(dx) < EPSILON or abs(dy) < EPSILON:
        return 1
    return 2


def validate_inv_11(
    estimates: dict[tuple[str, str], TrapArmEstimate],
    *,
    tolerance_m: float,
) -> tuple[tuple[str, ...], list[tuple[tuple[str, str], TrapArmEstimate, str]]]:
    """Inv 11 dual-bound validation.

    Returns:
        (unverified_rows_used, warnings) where:
          - unverified_rows_used: tuple of fixture_type strings whose
            KB row had source_confidence == "secondary_unverified".
          - warnings: list of ((room_id, fixture_type), estimate, reason).
            Reason is "upper_bound_warn" when likely passes but upper
            bound exceeds.

    Raises:
        TrapArmDistanceExceededError if any (room_id, fixture_type) pair
        has BOTH likely and upper bounds beyond MAX + tolerance.
    """
    unverified_rows: list[str] = []
    warnings: list[tuple[tuple[str, str], TrapArmEstimate, str]] = []
    seen_unverified: set[str] = set()
    for (room_id, fixture_type), est in estimates.items():
        row = get_plumbing_minimum_for(fixture_type)
        max_m = row["trap_arm_max_m"]
        threshold = max_m + tolerance_m
        likely_over = est.likely_bound_m > threshold + EPSILON
        upper_over = est.upper_bound_m > threshold + EPSILON
        if likely_over and upper_over:
            hints = (
                RemediationHint(
                    kind="alternative_routing",
                    parameter=f"trap_arm_{room_id}_{fixture_type}",
                    current_value=f"{est.upper_bound_m:.3f}",
                    suggested_value=f"<= {threshold:.3f}",
                    severity="high",
                    human_readable=(
                        f"Trap-arm distance for {fixture_type} in "
                        f"{room_id!r} exceeds maximum "
                        f"({est.upper_bound_m:.2f}m > {threshold:.2f}m) "
                        f"on both likely and worst-case bounds."
                    ),
                    retry_priority=40,
                    mutually_exclusive_with=(),
                ),
            )
            raise TrapArmDistanceExceededError(
                f"Trap-arm distance exceeded for ({room_id!r}, {fixture_type!r}): "
                f"upper={est.upper_bound_m:.3f}m, likely={est.likely_bound_m:.3f}m, "
                f"max+tol={threshold:.3f}m.",
                remediation_hints=hints,
                failure_phase="assignment",
            )
        if upper_over and not likely_over:
            warnings.append(((room_id, fixture_type), est, "upper_bound_warn"))
        if (
            row.get("source_confidence") == "secondary_unverified"
            and fixture_type not in seen_unverified
        ):
            unverified_rows.append(fixture_type)
            seen_unverified.add(fixture_type)
    return tuple(unverified_rows), warnings


def gate_unverified_rows(
    unverified_rows: tuple[str, ...],
    *,
    require_verified: bool,
) -> None:
    """Emit `PlumbingConfidenceTooLow` if `require_verified=True` AND any
    unverified row was used."""
    if require_verified and unverified_rows:
        raise PlumbingConfidenceTooLow(
            f"Plumbing KB used unverified-source rows: {sorted(unverified_rows)}. "
            f"Set config.require_verified_plumbing=False during pre-launch "
            f"or wait for B-222 primary-source verification.",
        )


__all__ = [
    "manhattan_worst_case",
    "estimate_trap_arm",
    "symbolic_bend_estimate",
    "validate_inv_11",
    "gate_unverified_rows",
]
