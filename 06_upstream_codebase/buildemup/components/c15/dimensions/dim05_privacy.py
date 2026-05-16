"""
BuildemUp — Component 15 — Dimension 5: Privacy
=====================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 5 (Altman 1975; Hillier
1984 privacy gradient).

Five checks at v1:
  P5.1  Bedroom not directly adjacent to main_entry — HEURISTIC
  P5.2  Master bedroom step-depth ≥ 3 (Hillier privacy gradient) — HEURISTIC
  P5.3  Bathroom-bedroom direct-adjacency preference — CULTURAL_PREFERENCE
  P5.4  Pooja room visual privacy from non-family circulation — CULTURAL_PREFERENCE
  P5.5  Sleeping vs entertainment zone separation — HEURISTIC
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from ..contracts import CulturalProfile
from ..protocol import (
    CheckContext, DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_MAIN_ENTRY, DEP_ROOM_CATEGORIES,
)
from ..schema import (
    CheckEpistemicKind, CheckSeverity, CheckStatus,
    DeferredCheck, ProblemCheck,
)
from .dim03_logical_flow import INDIAN_PROFILES, POOJA_CATS, _adjacent, _step_depth_map


BEDROOM_CATS: Final[frozenset[str]] = frozenset({"bedroom", "master_bedroom"})
MASTER_BEDROOM_CATS: Final[frozenset[str]] = frozenset({"master_bedroom"})
BATHROOM_CATS: Final[frozenset[str]] = frozenset({"bathroom", "wc", "bathroom_wc"})
ENTERTAINMENT_CATS: Final[frozenset[str]] = frozenset({"living", "drawing", "family", "dining", "media_room"})

P52_MASTER_DEPTH_PASS: Final[int] = 3


def _missing_dep(cid: str, dim: int, dep: str) -> DeferredCheck:
    return DeferredCheck(
        check_id=cid, dimension_id=dim,
        na_reason=f"data dependency {dep!r} not satisfied on this candidate.",
        blocking_backlog_item="",
    )


# =============================================================================
# P5.1 — Bedroom not directly adjacent to main_entry
# =============================================================================

@dataclass(frozen=True)
class CheckP51BedroomAdjacentMainEntry:
    check_id: str = "P5.1"
    dimension_id: int = 5
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES, DEP_MAIN_ENTRY,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        entry = context.metadata.main_entry_room_id
        adj = _adjacent(context.circulation_report)
        adj_to_entry = adj.get(entry, frozenset())
        offenders = sorted(r for r in adj_to_entry if cats.get(r, "") in BEDROOM_CATS)
        if not offenders:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.IMPORTANT,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Standard residential privacy heuristic: bedrooms not directly adjacent to main entry.",
                why_it_matters="When the front door opens, no bedroom is directly visible.",
                suggested_mitigation=None,
                measurement={"n_bedrooms_adjacent_to_entry": 0},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.FAIL, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind, affected_room_ids=tuple(offenders),
            rule_citation="Standard residential privacy heuristic: bedrooms not directly adjacent to main entry.",
            why_it_matters=(
                f"{len(offenders)} bedroom(s) share a wall/door with the "
                f"main entrance. When the front door opens — to delivery "
                f"people, guests, neighbours — the bedroom interior is "
                f"visible or directly audible."
            ),
            suggested_mitigation="Insert a foyer or corridor segment between bedroom and main entry; or re-position the bedroom further from entry.",
            measurement={"n_bedrooms_adjacent_to_entry": len(offenders)},
        )


# =============================================================================
# P5.2 — Master bedroom step-depth ≥ 3
# =============================================================================

@dataclass(frozen=True)
class CheckP52MasterBedroomDepth:
    check_id: str = "P5.2"
    dimension_id: int = 5
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES, DEP_MAIN_ENTRY,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        depths = _step_depth_map(context.circulation_report)
        masters = [rid for rid, c in cats.items() if c in MASTER_BEDROOM_CATS]
        if not masters:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No master_bedroom in placement; check defers (only graded when master labeled).",
                blocking_backlog_item="",
            )
        shallow = [rid for rid in masters if depths.get(rid, 0) < P52_MASTER_DEPTH_PASS]
        if not shallow:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.NICE_TO_HAVE,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Hillier 1984 privacy gradient: master bedroom at step-depth ≥ 3 from entry.",
                why_it_matters="Master bedroom sits deep in the graph, well-shielded from entry-zone traffic.",
                suggested_mitigation=None,
                measurement={"min_master_depth": min(depths.get(rid, 0) for rid in masters)},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind, affected_room_ids=tuple(sorted(shallow)),
            rule_citation="Hillier 1984 privacy gradient: master bedroom at step-depth ≥ 3 from entry.",
            why_it_matters="Master bedroom is shallow in the permeability graph; less private than typical.",
            suggested_mitigation="Route circulation through a buffer room (corridor/lobby) before reaching master.",
            measurement={"min_master_depth": min(depths.get(rid, 0) for rid in masters)},
        )


# =============================================================================
# P5.3 — Bathroom-bedroom direct adjacency (preference)
# =============================================================================

@dataclass(frozen=True)
class CheckP53BathroomBedroomAdjacency:
    """Indian residential POE: many families prefer master bedroom
    has attached/adjacent bathroom; secondary bathrooms common to
    other bedrooms. This is preference, not regulation."""
    check_id: str = "P5.3"
    dimension_id: int = 5
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.CULTURAL_PREFERENCE
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = INDIAN_PROFILES

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        if (
            self.cultural_scope is not None
            and context.metadata.cultural_profile not in self.cultural_scope
        ):
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason=(
                    f"cultural_profile_mismatch: {context.metadata.cultural_profile.value!r} "
                    f"is outside scope; attached-bath preference is culturally-specific."
                ),
                blocking_backlog_item="",
            )
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        adj = _adjacent(context.circulation_report)
        masters = [rid for rid, c in cats.items() if c in MASTER_BEDROOM_CATS]
        baths = {rid for rid, c in cats.items() if c in BATHROOM_CATS}
        if not masters or not baths:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="Need both master_bedroom and bathroom(s); missing.",
                blocking_backlog_item="",
            )
        masters_with_attached = [m for m in masters if adj.get(m, frozenset()) & baths]
        masters_without = [m for m in masters if m not in masters_with_attached]
        if not masters_without:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.NICE_TO_HAVE,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Indian residential POE: master bedroom commonly has attached bath.",
                why_it_matters="Master bedroom has a directly-adjacent bathroom — matches typical Indian residential preference.",
                suggested_mitigation=None,
                measurement={"n_masters": len(masters), "n_with_attached_bath": len(masters_with_attached)},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind, affected_room_ids=tuple(sorted(masters_without)),
            rule_citation="Indian residential POE: master bedroom commonly has attached bath.",
            why_it_matters="Master bedroom does not have a directly-adjacent bathroom — a common Indian residential expectation.",
            suggested_mitigation="Re-position one of the existing bathrooms to share a wall with the master, or accept the trade-off if floor area is constrained.",
            measurement={"n_masters": len(masters), "n_with_attached_bath": len(masters_with_attached)},
        )


# =============================================================================
# P5.4 — Pooja room visual privacy from non-family circulation
# =============================================================================

@dataclass(frozen=True)
class CheckP54PoojaRoomPrivacy:
    """Pooja room should not be directly visible from the main
    entry — visitors shouldn't immediately see the family altar."""
    check_id: str = "P5.4"
    dimension_id: int = 5
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.CULTURAL_PREFERENCE
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES, DEP_MAIN_ENTRY,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = INDIAN_PROFILES

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        if (
            self.cultural_scope is not None
            and context.metadata.cultural_profile not in self.cultural_scope
        ):
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason=f"cultural_profile_mismatch: {context.metadata.cultural_profile.value!r} outside scope.",
                blocking_backlog_item="",
            )
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        entry = context.metadata.main_entry_room_id
        adj = _adjacent(context.circulation_report)
        poojas = [rid for rid, c in cats.items() if c in POOJA_CATS]
        if not poojas:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No pooja room in placement.",
                blocking_backlog_item="",
            )
        offenders = [p for p in poojas if p in adj.get(entry, frozenset())]
        if not offenders:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.NICE_TO_HAVE,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Indian residential POE: pooja room not directly visible from main entry.",
                why_it_matters="Pooja room has visual privacy from arriving visitors.",
                suggested_mitigation=None,
                measurement={"n_poojas_adjacent_to_entry": 0},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind, affected_room_ids=tuple(sorted(offenders)),
            rule_citation="Indian residential POE: pooja room not directly visible from main entry.",
            why_it_matters="Pooja room sits directly off the main entry — first-time visitors see the family altar before being received.",
            suggested_mitigation="Re-position pooja or add an intermediate room between entry and pooja.",
            measurement={"n_poojas_adjacent_to_entry": len(offenders)},
        )


# =============================================================================
# P5.5 — Sleeping vs entertainment zone separation
# =============================================================================

@dataclass(frozen=True)
class CheckP55SleepingEntertainmentSeparation:
    """Bedrooms should not be directly adjacent to entertainment
    rooms (living/dining/media) — TV noise and conversation carry
    into bedroom through shared wall."""
    check_id: str = "P5.5"
    dimension_id: int = 5
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        adj = _adjacent(context.circulation_report)
        bedrooms = {rid for rid, c in cats.items() if c in BEDROOM_CATS}
        entertainment = {rid for rid, c in cats.items() if c in ENTERTAINMENT_CATS}
        if not bedrooms or not entertainment:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="Need both bedrooms and entertainment rooms; one or both missing.",
                blocking_backlog_item="",
            )
        offenders = sorted(b for b in bedrooms if adj.get(b, frozenset()) & entertainment)
        if not offenders:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.NICE_TO_HAVE,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Acoustic-privacy heuristic: bedrooms and entertainment rooms separated by ≥1 buffer room.",
                why_it_matters="No bedroom shares a wall with living/dining/media — acoustic privacy preserved.",
                suggested_mitigation=None,
                measurement={"n_bedrooms_touching_entertainment": 0},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind, affected_room_ids=tuple(offenders),
            rule_citation="Acoustic-privacy heuristic: bedrooms and entertainment rooms separated by ≥1 buffer room.",
            why_it_matters=(
                f"{len(offenders)} bedroom(s) share a wall with the living/"
                f"dining/media room. TV audio and conversation pass through "
                f"into bedroom — disturbs early sleepers + multigen schedules."
            ),
            suggested_mitigation="Insert a buffer room (storage, corridor, study) between bedroom and entertainment room; or use acoustic-rated party wall.",
            measurement={"n_bedrooms_touching_entertainment": len(offenders)},
        )


REGISTERED_CHECKS: tuple = (
    CheckP51BedroomAdjacentMainEntry(),
    CheckP52MasterBedroomDepth(),
    CheckP53BathroomBedroomAdjacency(),
    CheckP54PoojaRoomPrivacy(),
    CheckP55SleepingEntertainmentSeparation(),
)

__all__ = [
    "CheckP51BedroomAdjacentMainEntry", "CheckP52MasterBedroomDepth",
    "CheckP53BathroomBedroomAdjacency", "CheckP54PoojaRoomPrivacy",
    "CheckP55SleepingEntertainmentSeparation", "REGISTERED_CHECKS",
]
