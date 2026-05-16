"""
BuildemUp — Component 13 — Phase B (swing direction assignment)
================================================================

Per C13 SPEC v1.0 LOCKED:
- v0.1 § 3.2 (base swing rules)
- v0.2 A6 (bathroom-preferred-inward, NOT mandatory; outswing for
  compact bathrooms < area threshold)

Phase B responsibility:
  - For each EdgeAssignment from Phase A, decide swing_direction
    (into_room_a vs into_room_b) and hinge_side (start/end).
  - Apply decision rules in priority order; record decision rule
    for telemetry.

Decision rules (priority DESC; first match wins):
  Rule 1 — main entry always swings INTO the building (away from
           external space). The "building side" is the non-EXTERNAL
           room of the main entry edge.
  Rule 2 — bathroom INSWING if bathroom area >= threshold (default
           4.0 m²). Bathroom OUTSWING if area < threshold (per v0.2
           A6 (a) — safety + fixture clearance for compact
           bathrooms).
  Rule 3 — Smaller-area room INSWING (default per v0.1 § 3.2 step 1
           — door arc doesn't block circulation in larger room).
  Rule 4 — Tie-break (equal areas): lex-ASC room_a wins INSWING
           (deterministic per Inv D7).

Hinge side defaults to "start" (per v0.2 A3 / Inv D7 canonical
default). Phase D may flip hinge during conflict resolution; Phase B
sets the canonical initial value.

Per Inv D9' (v0.2 A6): bathroom outswing doors must not conflict
with adjacent traversal. The conflict check itself is Phase D
territory; Phase B only chooses outswing for compact bathrooms and
emits an AdvisoryFlag ("bathroom_outswing_emergency_clearance") if
the outward arc may impede traversal — Phase D / F validate.

This module ALSO emits AdvisoryFlag candidates for Phase E to
consume: when a bathroom under threshold is forced outward, an
"bathroom_outswing_emergency_clearance" advisory with
severity='concern' and category=EMERGENCY is recorded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .contracts import C13ConsumesFromC12Edge, EdgeType
from .edge_selection import EdgeAssignment, EdgeSelectionResult
from .schema import (
    AdvisoryCategory,
    AdvisoryFlag,
    AdvisoryFlagKind,
    AdvisorySeverity,
)
from .telemetry import (
    AdvisoryFlagEmittedEvent,
    C13TelemetrySink,
    NullTelemetrySink,
    SwingDirectionEvent,
)


# Bathroom category set — must mirror edge_selection.py.
# (Kept private here to avoid cross-module coupling, but the
# membership must agree.)
_BATHROOM_CATEGORIES = frozenset({"bathroom", "wc", "powder_room", "toilet"})


SwingDecisionRule = Literal[
    "main_entry_into_building",
    "bathroom_inswing_default",
    "bathroom_outswing_compact",
    "smaller_room_inswing",
    "fallback_lex_asc",
]


@dataclass(frozen=True)
class SwingAssignment:
    """One door's swing decision. Output of Phase B per edge
    assignment.

    Per v0.2 A3 hinge_side default: 'start'.
    """
    room_a_id: str
    room_b_id: str
    swing_direction: Literal["into_room_a", "into_room_b"]
    hinge_side: Literal["start", "end"]
    is_secondary: bool
    decision_rule: SwingDecisionRule


@dataclass(frozen=True)
class SwingAssignmentResult:
    """Output of Phase B: one SwingAssignment per Phase A assignment,
    plus a collection of AdvisoryFlag candidates to be merged at
    Phase E."""
    assignments: tuple[SwingAssignment, ...]
    advisory_flags: tuple[AdvisoryFlag, ...]

    def __post_init__(self) -> None:
        # Canonical ordering: (room_a_id, room_b_id, is_secondary).
        keys = [
            (a.room_a_id, a.room_b_id, a.is_secondary)
            for a in self.assignments
        ]
        if keys != sorted(keys):
            raise ValueError(
                f"SwingAssignmentResult.assignments must be sorted by "
                f"(room_a_id, room_b_id, is_secondary); got {keys}."
            )


# =============================================================================
# Helpers
# =============================================================================

def _is_bathroom(category: str) -> bool:
    return category in _BATHROOM_CATEGORIES


def _room_area(room_id: str, room_areas: dict[str, float]) -> float:
    """Lookup room area in m². Missing → 0.0 (treated as smallest;
    means the room's category was likely 'unknown' or external)."""
    return room_areas.get(room_id, 0.0)


def _swing_into(
    target_room_id: str,
    edge: C13ConsumesFromC12Edge,
) -> Literal["into_room_a", "into_room_b"]:
    """Map a target room id to the corresponding swing_direction
    literal."""
    if target_room_id == edge.room_a_id:
        return "into_room_a"
    if target_room_id == edge.room_b_id:
        return "into_room_b"
    raise ValueError(
        f"_swing_into: target {target_room_id!r} is not on edge "
        f"({edge.room_a_id}, {edge.room_b_id})."
    )


# =============================================================================
# Per-edge swing decision
# =============================================================================

def _decide_swing_for_main_entry(
    edge: C13ConsumesFromC12Edge,
) -> tuple[Literal["into_room_a", "into_room_b"], SwingDecisionRule]:
    """Per v0.1 § 3.2 step 3: main entry ALWAYS swings INTO the
    building (away from external).

    The "building side" is the non-EXTERNAL room. If both sides are
    internal (no EXTERNAL marker), fall through to a default — but
    a main-entry door without an EXTERNAL side is a Phase A choice
    we should respect: pick into_room_a as canonical fallback
    (deterministic).
    """
    if edge.edge_type == EdgeType.EXTERNAL_ENVELOPE:
        # The room on the building-internal side is the non-"EXTERNAL"
        # room. Per the C12V10EdgeAdapter convention, room_b_id ==
        # "EXTERNAL" (sentinel); room_a_id is the internal room.
        # (For native C12 v1.1 native edge_type, the convention may
        # differ; for v1.0 LOCKED we ship the sentinel-aware path.)
        from .contracts import EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
        if edge.room_b_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
            return "into_room_a", "main_entry_into_building"
        if edge.room_a_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
            # Per C12 canonical-order invariant, room_a < room_b
            # lex-ASC, so EXTERNAL (capital E) typically ends up
            # as room_a — handle both layouts.
            return "into_room_b", "main_entry_into_building"
    # No EXTERNAL sentinel present — fall back to canonical default
    # (into_room_a). Deterministic.
    return "into_room_a", "main_entry_into_building"


def _decide_swing_for_bathroom(
    bathroom_room_id: str,
    edge: C13ConsumesFromC12Edge,
    bathroom_area_m2: float,
    bathroom_outswing_area_threshold_m2: float,
) -> tuple[
    Literal["into_room_a", "into_room_b"],
    SwingDecisionRule,
    bool,  # is_outswing (for advisory emission)
]:
    """Per v0.2 A6.

    Rule: bathroom INSWING (into the bathroom) by default, BUT
    bathroom OUTSWING when area < threshold (compact bathroom; safety
    + fixture clearance).

    Returns (swing_direction, decision_rule, is_outswing).
    is_outswing=True means the door swings AWAY from the bathroom,
    which triggers an "bathroom_outswing_emergency_clearance" advisory.
    """
    if bathroom_area_m2 >= bathroom_outswing_area_threshold_m2:
        # Inswing (into the bathroom).
        return (
            _swing_into(bathroom_room_id, edge),
            "bathroom_inswing_default",
            False,
        )
    # Outswing — swing INTO the OTHER room.
    other = (
        edge.room_a_id if edge.room_b_id == bathroom_room_id
        else edge.room_b_id
    )
    return (
        _swing_into(other, edge),
        "bathroom_outswing_compact",
        True,
    )


def _decide_swing_for_general(
    edge: C13ConsumesFromC12Edge,
    room_areas: dict[str, float],
) -> tuple[Literal["into_room_a", "into_room_b"], SwingDecisionRule]:
    """Per v0.1 § 3.2 step 1: swing INTO the smaller-area room.

    Tie-break (equal areas): lex-ASC room_a → into_room_a (per Inv
    D7 canonical determinism). Both sides need an area lookup;
    missing area defaults to 0.0 (treated as smallest).
    """
    area_a = _room_area(edge.room_a_id, room_areas)
    area_b = _room_area(edge.room_b_id, room_areas)
    if area_a < area_b:
        return "into_room_a", "smaller_room_inswing"
    if area_b < area_a:
        return "into_room_b", "smaller_room_inswing"
    # Equal areas — lex-ASC tie-break.
    return "into_room_a", "fallback_lex_asc"


# =============================================================================
# Phase B entry point
# =============================================================================

def assign_swings(
    *,
    candidate_signature: str,
    edge_result: EdgeSelectionResult,
    room_categories: dict[str, str],
    room_areas: dict[str, float],
    bathroom_outswing_area_threshold_m2: float,
    telemetry_sink: Optional[C13TelemetrySink] = None,
) -> SwingAssignmentResult:
    """Phase B entry point.

    For each EdgeAssignment from Phase A, decide swing_direction +
    hinge_side. Emit one SwingDirectionEvent per decision; emit one
    AdvisoryFlag (bathroom_outswing_emergency_clearance, category
    EMERGENCY, severity 'concern') per bathroom that is forced
    outward.

    Args:
      candidate_signature: provenance.
      edge_result: Phase A output.
      room_categories: room_id → category map.
      room_areas: room_id → area_m2 map (consumed by smaller-room
          rule).
      bathroom_outswing_area_threshold_m2: per
          DoorPlacementConfig.bathroom_outswing_area_threshold_m2.
          v1 default 4.0 m² (per v0.2 A6 hand-picked threshold).
      telemetry_sink: optional sink. None → NullTelemetrySink.

    Returns:
      SwingAssignmentResult with assignments + collected advisories.
    """
    sink: C13TelemetrySink = telemetry_sink or NullTelemetrySink()

    swings: list[SwingAssignment] = []
    advisories: list[AdvisoryFlag] = []

    for a in edge_result.assignments:
        edge = a.edge
        # Decision dispatch — rules in priority DESC.

        # Rule 1: main entry into building (primary edge of entry room).
        is_main_entry_door = (
            a.room_id == edge_result.main_entry_room_id
            and not a.is_secondary
        )
        if is_main_entry_door:
            swing_dir, rule = _decide_swing_for_main_entry(edge)
        else:
            # Rule 2: bathroom (one side is a bathroom).
            cat_a = room_categories.get(edge.room_a_id, "")
            cat_b = room_categories.get(edge.room_b_id, "")
            a_is_bath = _is_bathroom(cat_a)
            b_is_bath = _is_bathroom(cat_b)
            # If both sides bathroom (unusual but legal in
            # contiguous-toilet layouts), pick room_a's perspective
            # canonically.
            if a_is_bath or b_is_bath:
                bath_room = edge.room_a_id if a_is_bath else edge.room_b_id
                bath_area = _room_area(bath_room, room_areas)
                swing_dir, rule, is_outswing = _decide_swing_for_bathroom(
                    bath_room, edge, bath_area,
                    bathroom_outswing_area_threshold_m2,
                )
                # Emit advisory for compact outswing.
                if is_outswing:
                    flag = AdvisoryFlag(
                        flag_kind="bathroom_outswing_emergency_clearance",
                        affected_room_id=bath_room,
                        category=AdvisoryCategory.EMERGENCY,
                        severity="concern",
                        explanation_template=(
                            f"Bathroom {bath_room} (area "
                            f"{bath_area:.2f}m²) is below the outswing "
                            f"threshold "
                            f"({bathroom_outswing_area_threshold_m2:.2f}m²)"
                            f"; door swings outward — verify adjacent "
                            f"traversal clearance (Inv D9')."
                        ),
                        deduplication_key=f"{bath_room}::emergency",
                    )
                    advisories.append(flag)
                    sink.emit(AdvisoryFlagEmittedEvent(
                        candidate_signature=candidate_signature,
                        flag_kind=flag.flag_kind,
                        affected_room_id=flag.affected_room_id,
                        category=flag.category,
                        severity=flag.severity,
                    ))
            else:
                # Rule 3 / Rule 4: general smaller-area swing.
                swing_dir, rule = _decide_swing_for_general(edge, room_areas)

        # Hinge side: v0.2 A3 canonical default "start". Phase D may
        # flip during conflict resolution.
        hinge: Literal["start", "end"] = "start"

        swings.append(SwingAssignment(
            room_a_id=edge.room_a_id,
            room_b_id=edge.room_b_id,
            swing_direction=swing_dir,
            hinge_side=hinge,
            is_secondary=a.is_secondary,
            decision_rule=rule,
        ))
        sink.emit(SwingDirectionEvent(
            candidate_signature=candidate_signature,
            room_a_id=edge.room_a_id,
            room_b_id=edge.room_b_id,
            swing_direction=swing_dir,
            decision_rule=rule,
        ))

    # Canonical sort enforced by SwingAssignmentResult.__post_init__.
    swings.sort(key=lambda s: (s.room_a_id, s.room_b_id, s.is_secondary))
    return SwingAssignmentResult(
        assignments=tuple(swings),
        advisory_flags=tuple(advisories),
    )


__all__ = [
    "SwingDecisionRule",
    "SwingAssignment",
    "SwingAssignmentResult",
    "assign_swings",
]
