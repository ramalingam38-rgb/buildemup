"""
C16 — LocalBuildingFrame orientation computation
==================================================

Per v0.4 A4 + R29:

    +X axis orientation, chosen by first applicable rule:
    1. EXPLICIT HINT from JurisdictionProfile.local_x_axis_orientation_deg_hint
    2. PRIMARY ENTRANCE WALL axis (door with is_main_entry=True)
    3. LONGEST EXTERNAL WALL (with semantic_identity_hash lex-ASC tiebreak)
    4. LEX-ASC fallback (first wall's start→end direction)

Per R29b: the hierarchy step that fired is recorded in
GeospatialReference.orientation_basis.

Per R29c: tiebreaks use semantic_identity_hash (stable per R27).

Per R29d (v0.5 A5): when OrientationLock is present, validate the lock
is within EPSILON_ANGLE_DEG of one of the four candidates; raise
OrientationLockMismatchError if implausible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from buildemup.components.c16.contracts import (
    JurisdictionProfile,
    OrientationLock,
)
from buildemup.components.c16.errors import OrientationLockMismatchError
from buildemup.components.c16.versioning import EPSILON_ANGLE_DEG


@dataclass(frozen=True)
class WallCandidate:
    """One external-wall candidate considered by the orientation
    hierarchy. start/end are in LocalBuildingFrame coordinates (mm)."""
    wall_id:                str
    start_x_mm:             int
    start_y_mm:             int
    end_x_mm:               int
    end_y_mm:               int
    length_mm:              int
    semantic_identity_hash: str   # 8-hex stable ID (Inv R29c tiebreak)
    is_external:            bool
    has_main_entry:         bool


@dataclass(frozen=True)
class OrientationDecision:
    """Result of the R29 hierarchy walk."""
    orientation_deg: float       # CCW from plot-East (+X axis direction)
    basis:           Literal[
        "explicit_hint", "primary_entrance", "longest_wall", "lex_fallback",
    ]
    chosen_wall_id:  Optional[str] = None


def _wall_axis_angle_deg(w: WallCandidate) -> float:
    """Angle of the wall direction (start → end) measured CCW from +X
    in degrees, normalized to [0, 360).

    Two walls along the same line return the SAME angle regardless of
    direction; we wrap to [0, 360) and additionally mod-180 the axis
    into [0, 180) since a wall's "+X axis" is direction-agnostic.
    """
    dx = w.end_x_mm - w.start_x_mm
    dy = w.end_y_mm - w.start_y_mm
    if dx == 0 and dy == 0:
        return 0.0
    angle = math.degrees(math.atan2(dy, dx))
    # Wrap to [0, 360)
    while angle < 0.0:
        angle += 360.0
    while angle >= 360.0:
        angle -= 360.0
    # Axis-agnostic: same line forward or backward → same orientation
    return angle % 180.0


def compute_orientation(
    *,
    walls:                 tuple[WallCandidate, ...],
    jurisdiction_profile:  JurisdictionProfile,
) -> OrientationDecision:
    """Per R29 hierarchy. First applicable step wins.

    Inputs:
      walls: every wall the floor carries (the external+entry+longest
             logic filters internally).
      jurisdiction_profile: carries optional explicit hint.

    Returns:
      OrientationDecision with the angle + basis + (optional) chosen
      wall_id for audit trail.
    """
    # Step 1 — explicit hint
    if jurisdiction_profile.local_x_axis_orientation_deg_hint is not None:
        return OrientationDecision(
            orientation_deg=float(
                jurisdiction_profile.local_x_axis_orientation_deg_hint
            ),
            basis="explicit_hint",
        )

    # Step 2 — primary entrance wall
    entry_walls = tuple(w for w in walls if w.has_main_entry)
    if entry_walls:
        # If multiple walls flagged with main entry (multi-entry buildings),
        # tiebreak with semantic_identity_hash lex-ASC per R29c
        chosen = min(entry_walls, key=lambda w: w.semantic_identity_hash)
        return OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="primary_entrance",
            chosen_wall_id=chosen.wall_id,
        )

    # Step 3 — longest external wall
    external = tuple(w for w in walls if w.is_external)
    if external:
        max_len = max(w.length_mm for w in external)
        # All walls within 1 mm of max length are tied (R7a precision)
        tied = tuple(w for w in external if abs(w.length_mm - max_len) <= 1)
        # R29c tiebreak: lex-ASC of semantic_identity_hash
        chosen = min(tied, key=lambda w: w.semantic_identity_hash)
        return OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="longest_wall",
            chosen_wall_id=chosen.wall_id,
        )

    # Step 4 — degenerate fallback: lex-ASC first wall
    if walls:
        chosen = min(walls, key=lambda w: w.semantic_identity_hash)
        return OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="lex_fallback",
            chosen_wall_id=chosen.wall_id,
        )

    # Truly degenerate: no walls at all. Use 0° (plot-East).
    return OrientationDecision(
        orientation_deg=0.0,
        basis="lex_fallback",
        chosen_wall_id=None,
    )


def validate_orientation_lock(
    *,
    lock:                 OrientationLock,
    candidate_decisions:  tuple[OrientationDecision, ...],
) -> None:
    """Per R29d: lock's orientation MUST be within EPSILON_ANGLE_DEG
    of at least one candidate computed from CURRENT geometry.

    A mismatch indicates the geometry has changed so much that the lock
    no longer makes sense → halt with OrientationLockMismatchError
    (LocalDrawingError — always halts regardless of strict_mode).
    """
    locked = lock.locked_x_axis_orientation_deg
    candidates_deg = tuple(d.orientation_deg for d in candidate_decisions)
    for c in candidates_deg:
        # Compare modulo 180 since orientation is axis-agnostic
        diff = abs(locked - c)
        diff = min(diff, 180.0 - diff, abs(diff - 180.0))
        if diff <= EPSILON_ANGLE_DEG:
            return  # plausible — honor the lock
    # No candidate within tolerance → implausible
    raise OrientationLockMismatchError(
        f"OrientationLock {locked}° not within {EPSILON_ANGLE_DEG}° of "
        f"any R29 hierarchy candidate {candidates_deg!r}. "
        f"Geometry may have changed since the lock was set; manual "
        f"review required.",
        locked_orientation_deg=locked,
        candidate_orientations_deg=candidates_deg,
        epsilon_deg=EPSILON_ANGLE_DEG,
    )


def all_hierarchy_candidates(
    *,
    walls:                tuple[WallCandidate, ...],
    jurisdiction_profile: JurisdictionProfile,
) -> tuple[OrientationDecision, ...]:
    """Compute all four hierarchy candidates that would have applied,
    for R29d plausibility validation.

    Unlike compute_orientation(), which short-circuits at the first
    applicable rule, this returns the full candidate set so the lock
    can be compared against any of them."""
    results: list[OrientationDecision] = []

    # Step 1 candidate (always synthesize if hint present)
    if jurisdiction_profile.local_x_axis_orientation_deg_hint is not None:
        results.append(OrientationDecision(
            orientation_deg=float(
                jurisdiction_profile.local_x_axis_orientation_deg_hint
            ),
            basis="explicit_hint",
        ))

    # Step 2 — main entrance walls
    entry_walls = tuple(w for w in walls if w.has_main_entry)
    if entry_walls:
        chosen = min(entry_walls, key=lambda w: w.semantic_identity_hash)
        results.append(OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="primary_entrance",
            chosen_wall_id=chosen.wall_id,
        ))

    # Step 3 — longest external
    external = tuple(w for w in walls if w.is_external)
    if external:
        max_len = max(w.length_mm for w in external)
        tied = tuple(w for w in external if abs(w.length_mm - max_len) <= 1)
        chosen = min(tied, key=lambda w: w.semantic_identity_hash)
        results.append(OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="longest_wall",
            chosen_wall_id=chosen.wall_id,
        ))

    # Step 4 — fallback
    if walls:
        chosen = min(walls, key=lambda w: w.semantic_identity_hash)
        results.append(OrientationDecision(
            orientation_deg=_wall_axis_angle_deg(chosen),
            basis="lex_fallback",
            chosen_wall_id=chosen.wall_id,
        ))
    else:
        # Degenerate: no walls. compute_orientation() returns 0° as the
        # lex_fallback default; mirror that here so R29d plausibility
        # accepts locks at 0° in this degenerate case.
        results.append(OrientationDecision(
            orientation_deg=0.0,
            basis="lex_fallback",
            chosen_wall_id=None,
        ))

    return tuple(results)
