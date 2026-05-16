"""
BuildemUp — Component 15 — Dimension 6: No Bottlenecks
============================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 6 (Hillier 1984 betweenness;
circulation engineering).

Four checks at v1:
  P6.1  Single-room betweenness concentration (consumes C14 flag) — HEURISTIC
  P6.2  Corridor width ≥ 0.9 m — DEFERRED (C13 door clear-width
        data not threaded; B-C15-DOOR-WIDTH-DATA)
  P6.3  Doorway clear-width ≥ 0.75 m — DEFERRED (C13 enforces;
        C15 redundancy check would need C13 door data;
        B-C15-DOOR-WIDTH-DATA)
  P6.4  Emergency egress path length — DEFERRED (NBC Part 4 fire-
        safety travel-distance calc requires path geometry;
        B-C15-EGRESS-PATH-LENGTH)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..contracts import CulturalProfile
from ..protocol import (
    CheckContext, DEP_C14_FLAGS, DEP_C14_GRAPH, DEP_C12_PLACEMENT,
)
from ..schema import (
    CheckEpistemicKind, CheckSeverity, CheckStatus,
    DeferredCheck, ProblemCheck,
)


def _missing_dep(cid: str, dim: int, dep: str) -> DeferredCheck:
    return DeferredCheck(
        check_id=cid, dimension_id=dim,
        na_reason=f"data dependency {dep!r} not satisfied on this candidate.",
        blocking_backlog_item="",
    )


# =============================================================================
# P6.1 — Betweenness concentration (consume C14 BOTTLENECK_CONCENTRATION)
# =============================================================================

@dataclass(frozen=True)
class CheckP61BottleneckConcentration:
    """Reads C14's BOTTLENECK_CONCENTRATION structural flag and
    surfaces it as a P1.1 ProblemCheck. C14 has already done the
    heavy lifting (Brandes betweenness + threshold compare); C15
    just routes the flag into the user-facing problem report."""
    check_id: str = "P6.1"
    dimension_id: int = 6
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (DEP_C14_GRAPH, DEP_C14_FLAGS)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)

        # Look for BOTTLENECK_CONCENTRATION flag (C14 structural).
        structural_flags = getattr(context.circulation_report, "structural_flags", ()) or ()
        bottleneck_flags = [
            f for f in structural_flags
            if getattr(getattr(f, "kind", None), "value", "") == "bottleneck_concentration"
            or str(getattr(f, "kind", "")) == "bottleneck_concentration"
        ]
        if not bottleneck_flags:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.IMPORTANT,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Hillier 1984 betweenness; C14 BOTTLENECK_CONCENTRATION flag.",
                why_it_matters="No single room concentrates circulation through it — daily flow is distributed.",
                suggested_mitigation=None,
                measurement={"n_bottleneck_flags": 0},
            )

        affected: list[str] = []
        for f in bottleneck_flags:
            rids = getattr(f, "affected_room_ids", ()) or getattr(f, "rooms", ())
            for rid in rids:
                affected.append(rid)
        affected_sorted = tuple(sorted(set(affected)))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind, affected_room_ids=affected_sorted,
            rule_citation="Hillier 1984 betweenness; C14 BOTTLENECK_CONCENTRATION flag emitted upstream.",
            why_it_matters=(
                f"C14 detected {len(bottleneck_flags)} room(s) with high "
                f"betweenness — daily circulation routes through these "
                f"rooms disproportionately. The room becomes a thoroughfare; "
                f"privacy and usable area inside it suffer."
            ),
            suggested_mitigation="Add a parallel route (corridor segment) bypassing the bottleneck, or relocate the bottleneck room to the periphery.",
            measurement={"n_bottleneck_flags": len(bottleneck_flags), "n_affected_rooms": len(affected_sorted)},
        )


# =============================================================================
# P6.2 — Corridor width ≥ 0.9 m (DEFERRED)
# =============================================================================

@dataclass(frozen=True)
class CheckP62CorridorWidth:
    check_id: str = "P6.2"
    dimension_id: int = 6
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = ("door_clear_width",)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            na_reason=(
                "Corridor width compliance requires C13 door clear-width "
                "data threaded through the CheckContext. Not in v1 "
                "pipeline (C12 SharedEdge has overlap_length_m but C15 "
                "doesn't consume C13 door records directly)."
            ),
            blocking_backlog_item="B-C15-DOOR-WIDTH-DATA",
        )


# =============================================================================
# P6.3 — Doorway clear-width ≥ 0.75 m (DEFERRED)
# =============================================================================

@dataclass(frozen=True)
class CheckP63DoorwayClearWidth:
    check_id: str = "P6.3"
    dimension_id: int = 6
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = ("door_clear_width",)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            na_reason=(
                "Doorway clear-width compliance enforced upstream by C13. "
                "C15 redundancy check would need C13 door records "
                "threaded through CheckContext."
            ),
            blocking_backlog_item="B-C15-DOOR-WIDTH-DATA",
        )


# =============================================================================
# P6.4 — Emergency egress path length (DEFERRED)
# =============================================================================

@dataclass(frozen=True)
class CheckP64EmergencyEgressPath:
    check_id: str = "P6.4"
    dimension_id: int = 6
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = ("egress_path_geometry",)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            na_reason=(
                "NBC Part 4 fire-safety travel-distance check (22 m residential "
                "limit) requires path-length geometry from rooms to exit, "
                "not provided by C12/C13/C14."
            ),
            blocking_backlog_item="B-C15-EGRESS-PATH-LENGTH",
        )


REGISTERED_CHECKS: tuple = (
    CheckP61BottleneckConcentration(),
    CheckP62CorridorWidth(),
    CheckP63DoorwayClearWidth(),
    CheckP64EmergencyEgressPath(),
)

__all__ = [
    "CheckP61BottleneckConcentration", "CheckP62CorridorWidth",
    "CheckP63DoorwayClearWidth", "CheckP64EmergencyEgressPath",
    "REGISTERED_CHECKS",
]
