"""
BuildemUp — Component 15 — Dimension 1: No Wasted Space
==========================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 1 (per validation report
LOCK Decision #1 — Neufert; FAR analysis literature).

Four checks at v1:
  - P1.1  Corridor area as fraction of total carpet area
            (RUNNABLE — needs c12_placement + room_categories)
  - P1.2  Dead-corner detection (L-corners < 1.5 m² with no
          functional assignment)
            (DEFERRED — needs envelope polygon subtraction, blocked
            by B-C15-ENVELOPE-POLYGON-SUBTRACTION)
  - P1.3  Aspect-ratio sanity (rooms with extreme width:depth > 3:1)
            (RUNNABLE — needs c12_placement_geometry)
  - P1.4  Built-up-to-FAR utilization
            (DEFERRED — needs plot FAR ceiling not threaded through
            ProblemAnalysisMetadata at v1, blocked by
            B-C15-FAR-CEILING-METADATA)

Epistemic kind for all four: ARCHITECTURAL_HEURISTIC. None of these
maps to a hard NBC clause (NBC mandates corridor MINIMUM width 0.9 m
but no MAXIMUM area fraction; per Rule 11 web search S48).

Per Rule 11 web research finding S48: The "≤12%" corridor fraction
in v0.1 § 1.4 sample was illustrative and not NBC-backed. Realistic
architectural-heuristic thresholds for Indian residential POE:
  - PASS:  corridor fraction ≤ 15%
  - WARN:  15% < corridor fraction ≤ 20%
  - FAIL:  corridor fraction > 20%
This is heuristic; B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK will fix
the authoritative threshold at v1.0 LOCK.

For aspect ratio (P1.3), Neufert/Ching guidance: ratios > 3:1 make
habitable rooms functionally cramped (furniture placement
constrained, awkward circulation within room). Thresholds:
  - PASS:  max ratio across habitable rooms ≤ 2.5
  - WARN:  2.5 < max ratio ≤ 3.0
  - FAIL:  max ratio > 3.0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Optional

from ..contracts import CulturalProfile
from ..protocol import (
    CheckContext,
    DEP_C12_PLACEMENT,
    DEP_C12_PLACEMENT_GEOMETRY,
    DEP_ENVELOPE_POLYGON_SUBTRACTION,
    DEP_PLOT_FAR_CEILING,
    DEP_ROOM_CATEGORIES,
)
from ..schema import (
    CheckEpistemicKind,
    CheckSeverity,
    CheckStatus,
    DeferredCheck,
    ProblemCheck,
)


# =============================================================================
# Shared constants
# =============================================================================

# Categories C15 treats as circulation (matches C14
# CIRCULATION_CATEGORY_KEYWORDS — kept synchronized; if C14 expands
# its set, this set should too. NOT a string-equality re-export
# because both live in different components and breaking sync should
# be caught by tests, not silently propagated.)
CIRCULATION_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"corridor", "foyer", "staircase"}
)

# Categories that are NOT habitable rooms (aspect-ratio check P1.3
# excludes these — odd-shaped baths/utilities/storage are fine).
NON_HABITABLE_FOR_ASPECT_RATIO: Final[frozenset[str]] = frozenset(
    {
        "corridor",
        "foyer",
        "staircase",
        "bathroom",
        "wc",
        "utility",
        "storage",
        "balcony",
        "main_entrance",
    }
)

# Thresholds. Architectural heuristic — pending
# B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK.
P11_CORRIDOR_PASS_CEILING: Final[float] = 0.15  # 15%
P11_CORRIDOR_WARN_CEILING: Final[float] = 0.20  # 20%

P13_ASPECT_PASS_CEILING: Final[float] = 2.5
P13_ASPECT_WARN_CEILING: Final[float] = 3.0


# =============================================================================
# P1.1 — Corridor area fraction
# =============================================================================

@dataclass(frozen=True)
class CheckP11CorridorFraction:
    """P1.1 — Corridor area as fraction of total carpet area.

    Architectural heuristic. NBC has no maximum corridor fraction;
    industry POE convention treats > 20% as inefficient.

    Measurement:
      corridor_area = sum of room areas where category in
                      CIRCULATION_CATEGORIES
      total_area    = sum of all room areas (carpet area proxy)
      fraction      = corridor_area / total_area

    Status:
      PASS if fraction ≤ 0.15
      WARN if 0.15 < fraction ≤ 0.20
      FAIL if fraction > 0.20

    Edge cases:
      - total_area = 0 (no placed rooms): impossible by C12's
        invariants but defensive — would defer if it happened.
      - no rooms in CIRCULATION_CATEGORIES: corridor_area = 0,
        fraction = 0, status = PASS. (A truly corridor-free layout
        is fine.)
    """
    check_id: str = "P1.1"
    dimension_id: int = 1
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT,
        DEP_C12_PLACEMENT_GEOMETRY,
        DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        # Pre-check dependencies (Inv P6 routing).
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return DeferredCheck(
                    check_id=self.check_id,
                    dimension_id=self.dimension_id,
                    na_reason=(
                        f"data dependency {dep!r} not satisfied on this "
                        f"candidate; P1.1 requires placed-rooms geometry "
                        f"plus room_categories covering every placed room."
                    ),
                    blocking_backlog_item="",
                )

        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]
        cats = context.metadata.room_categories

        total_area = 0.0
        corridor_area = 0.0
        corridor_rooms: list[str] = []
        for room in pr:
            area = room.width_m * room.depth_m
            total_area += area
            cat = cats.get(room.room_id, "")
            if cat in CIRCULATION_CATEGORIES:
                corridor_area += area
                corridor_rooms.append(room.room_id)

        if total_area <= 0.0:
            return DeferredCheck(
                check_id=self.check_id,
                dimension_id=self.dimension_id,
                na_reason=(
                    "total carpet area computed as zero; cannot compute "
                    "corridor fraction (defensive guard — should not "
                    "happen given C12 invariants)."
                ),
                blocking_backlog_item="",
            )

        fraction = corridor_area / total_area

        if fraction <= P11_CORRIDOR_PASS_CEILING:
            status = CheckStatus.PASS
            why = (
                f"Circulation area is {fraction:.1%} of carpet area, "
                f"within the architectural-heuristic comfortable range "
                f"(≤ 15%)."
            )
            mitigation: Optional[str] = None
            affected: tuple[str, ...] = ()
        elif fraction <= P11_CORRIDOR_WARN_CEILING:
            status = CheckStatus.WARN
            why = (
                f"Circulation area is {fraction:.1%} of carpet area. "
                f"Above 15% is borderline — often justified by "
                f"topology (single-loaded corridor on narrow plots) "
                f"but reduces room area you could otherwise have."
            )
            mitigation = (
                "Consider reducing corridor length by relocating rooms "
                "to share walls more efficiently, or accept the trade-"
                "off if your plot shape forces this topology."
            )
            affected = tuple(sorted(corridor_rooms))
        else:
            status = CheckStatus.FAIL
            why = (
                f"Circulation area is {fraction:.1%} of carpet area. "
                f"Above 20% is inefficient by Indian residential POE "
                f"convention — that's habitable-room area you're "
                f"paying construction cost on but not using as living "
                f"space."
            )
            mitigation = (
                "Re-examine corridor routing. Common fixes: switch to "
                "double-loaded corridor (rooms on both sides), eliminate "
                "redundant foyer area, or reduce corridor width to NBC "
                "minimum (0.9 m) where you've allocated more."
            )
            affected = tuple(sorted(corridor_rooms))

        # Rule citation surfaced separately from severity_basis
        # because rule_citation is the user-facing pointer ("why
        # this rule exists") while severity_basis is the
        # registry-internal grading authority. They can differ.
        rule_citation = (
            "Architectural heuristic — Indian residential POE: "
            "circulation fraction ≤ 15% target, > 20% considered "
            "wasteful. Not an NBC clause."
        )

        return ProblemCheck(
            check_id=self.check_id,
            dimension_id=self.dimension_id,
            status=status,
            severity=CheckSeverity.IMPORTANT,  # placeholder; orchestrator overrides via severity rule table in Phase σ
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation=rule_citation,
            why_it_matters=why,
            suggested_mitigation=mitigation,
            measurement={
                "corridor_area_m2": round(corridor_area, 4),
                "total_area_m2": round(total_area, 4),
                "fraction": round(fraction, 4),
            },
        )


# =============================================================================
# P1.2 — Dead-corner detection (DEFERRED at v1)
# =============================================================================

@dataclass(frozen=True)
class CheckP12DeadCorner:
    """P1.2 — Dead-corner detection (L-corners < 1.5 m² with no
    functional assignment).

    DEFERRED at v1. Requires axis-aligned polygon subtraction
    (envelope minus union of room rectangles) to identify the
    geometry of unallocated areas, plus a min-area threshold to
    flag small "dead" pockets.

    Blocked by B-C15-ENVELOPE-POLYGON-SUBTRACTION. Always emits
    DeferredCheck at this registry version.
    """
    check_id: str = "P1.2"
    dimension_id: int = 1
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (DEP_ENVELOPE_POLYGON_SUBTRACTION,)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        # Always deferred at v1 — DEP_ENVELOPE_POLYGON_SUBTRACTION
        # is never satisfied by the v1 probe (per protocol.py
        # design: dependencies in the "deferred dependencies" group
        # are never reported as available).
        return DeferredCheck(
            check_id=self.check_id,
            dimension_id=self.dimension_id,
            na_reason=(
                "Dead-corner detection requires axis-aligned polygon "
                "subtraction (envelope geometry minus union of room "
                "rectangles) to identify unallocated L-pockets. Not "
                "implemented at v1; the C15 pipeline at this version "
                "does not compute the unoccupied envelope region."
            ),
            blocking_backlog_item="B-C15-ENVELOPE-POLYGON-SUBTRACTION",
        )


# =============================================================================
# P1.3 — Aspect-ratio sanity
# =============================================================================

@dataclass(frozen=True)
class CheckP13AspectRatio:
    """P1.3 — Aspect-ratio sanity for habitable rooms (width:depth).

    Architectural heuristic per Neufert + Ching. Rooms with max:min
    aspect > 3:1 are functionally compromised — furniture layout
    constrained, awkward circulation within the room.

    Measurement:
      For each room NOT in NON_HABITABLE_FOR_ASPECT_RATIO:
        ratio = max(width_m, depth_m) / min(width_m, depth_m)
      report = max ratio across habitable rooms

    Status:
      PASS if max ratio ≤ 2.5
      WARN if 2.5 < max ratio ≤ 3.0
      FAIL if max ratio > 3.0

    affected_room_ids on WARN/FAIL: only rooms whose own ratio
    exceeds the relevant threshold (so the user sees which rooms
    to act on, not just the max-offender).
    """
    check_id: str = "P1.3"
    dimension_id: int = 1
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT,
        DEP_C12_PLACEMENT_GEOMETRY,
        DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return DeferredCheck(
                    check_id=self.check_id,
                    dimension_id=self.dimension_id,
                    na_reason=(
                        f"data dependency {dep!r} not satisfied; P1.3 "
                        f"requires placed-room geometry + room_categories "
                        f"to identify habitable rooms."
                    ),
                    blocking_backlog_item="",
                )

        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]
        cats = context.metadata.room_categories

        # Compute per-room ratios for HABITABLE rooms only.
        per_room: list[tuple[str, float]] = []
        for room in pr:
            cat = cats.get(room.room_id, "")
            if cat in NON_HABITABLE_FOR_ASPECT_RATIO:
                continue
            w = room.width_m
            d = room.depth_m
            ratio = max(w, d) / min(w, d)
            per_room.append((room.room_id, ratio))

        if not per_room:
            # No habitable rooms — defer (an envelope with only
            # bathrooms + corridors is structurally unusual).
            return DeferredCheck(
                check_id=self.check_id,
                dimension_id=self.dimension_id,
                na_reason=(
                    "No habitable rooms (bedrooms, living, dining, "
                    "kitchen, study) found among placed rooms; aspect-"
                    "ratio sanity is not meaningful for circulation/"
                    "service-only layouts."
                ),
                blocking_backlog_item="",
            )

        max_ratio = max(r for _, r in per_room)

        if max_ratio <= P13_ASPECT_PASS_CEILING:
            status = CheckStatus.PASS
            why = (
                f"All habitable rooms have aspect ratio ≤ 2.5:1, well "
                f"within Neufert/Ching guidance for comfortable "
                f"furniture layout."
            )
            mitigation: Optional[str] = None
            affected: tuple[str, ...] = ()
        elif max_ratio <= P13_ASPECT_WARN_CEILING:
            status = CheckStatus.WARN
            why = (
                f"Some habitable rooms have aspect ratio between 2.5:1 "
                f"and 3:1 (max: {max_ratio:.2f}:1). Borderline — "
                f"furniture layout becomes constrained; some bed/sofa "
                f"orientations may not fit."
            )
            mitigation = (
                "Consider widening narrow rooms by 0.3-0.6 m if "
                "envelope allows, or accept the trade-off if you've "
                "verified furniture fits in the planned arrangement."
            )
            affected = tuple(sorted(
                rid for rid, r in per_room if r > P13_ASPECT_PASS_CEILING
            ))
        else:
            status = CheckStatus.FAIL
            why = (
                f"Some habitable rooms have aspect ratio above 3:1 "
                f"(max: {max_ratio:.2f}:1). Per Neufert/Ching, this "
                f"makes the room functionally compromised — corridor-"
                f"like proportions reduce flexibility of furniture "
                f"placement and feel cramped."
            )
            mitigation = (
                "Re-shape the offending room(s) closer to a 2:1 ratio. "
                "This usually requires re-slicing adjacent rooms to "
                "redistribute width/depth. Consider whether the "
                "topology choice (e.g., single-loaded corridor on a "
                "narrow plot) is forcing this geometry."
            )
            affected = tuple(sorted(
                rid for rid, r in per_room if r > P13_ASPECT_WARN_CEILING
            ))

        rule_citation = (
            "Architectural heuristic — Neufert Architects' Data + "
            "Ching 'Architecture: Form, Space, Order': habitable room "
            "aspect ratio > 3:1 is functionally compromised. Not an "
            "NBC clause."
        )

        return ProblemCheck(
            check_id=self.check_id,
            dimension_id=self.dimension_id,
            status=status,
            severity=CheckSeverity.IMPORTANT,  # orchestrator overrides via severity rule table
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation=rule_citation,
            why_it_matters=why,
            suggested_mitigation=mitigation,
            measurement={
                "max_aspect_ratio": round(max_ratio, 4),
                "n_habitable_rooms": len(per_room),
                "n_rooms_over_pass_ceiling": sum(
                    1 for _, r in per_room if r > P13_ASPECT_PASS_CEILING
                ),
                "n_rooms_over_warn_ceiling": sum(
                    1 for _, r in per_room if r > P13_ASPECT_WARN_CEILING
                ),
            },
        )


# =============================================================================
# P1.4 — Built-up-to-FAR utilization (DEFERRED at v1)
# =============================================================================

@dataclass(frozen=True)
class CheckP14FarUtilization:
    """P1.4 — Built-up-to-FAR utilization (over- or under-utilization
    of allowed FAR).

    DEFERRED at v1. Requires plot-level FAR ceiling (municipal
    bye-law value) threaded through ProblemAnalysisMetadata. The
    current metadata schema does not carry plot regulatory data.

    Blocked by B-C15-FAR-CEILING-METADATA. Always emits
    DeferredCheck at this registry version.
    """
    check_id: str = "P1.4"
    dimension_id: int = 1
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (DEP_PLOT_FAR_CEILING,)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id,
            dimension_id=self.dimension_id,
            na_reason=(
                "FAR utilization requires the plot's regulatory FAR "
                "ceiling (from municipal bye-laws — TNCDBR / CMDA / "
                "DTCP equivalents) threaded through "
                "ProblemAnalysisMetadata. Not in the v1 metadata "
                "contract; check defers until plot regulatory data "
                "is plumbed through."
            ),
            blocking_backlog_item="B-C15-FAR-CEILING-METADATA",
        )


# =============================================================================
# Registry exports
# =============================================================================

REGISTERED_CHECKS: tuple = (
    CheckP11CorridorFraction(),
    CheckP12DeadCorner(),
    CheckP13AspectRatio(),
    CheckP14FarUtilization(),
)
"""Per-dimension check tuple. Imported by registry.build_registry().

Lex-ASC by check_id (P1.1, P1.2, P1.3, P1.4).
"""


__all__ = [
    # constants
    "CIRCULATION_CATEGORIES",
    "NON_HABITABLE_FOR_ASPECT_RATIO",
    "P11_CORRIDOR_PASS_CEILING",
    "P11_CORRIDOR_WARN_CEILING",
    "P13_ASPECT_PASS_CEILING",
    "P13_ASPECT_WARN_CEILING",
    # check classes
    "CheckP11CorridorFraction",
    "CheckP12DeadCorner",
    "CheckP13AspectRatio",
    "CheckP14FarUtilization",
    # registry tuple
    "REGISTERED_CHECKS",
]
