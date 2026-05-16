"""
BuildemUp — Component 15 — Dimension 7: First-Floor Living
================================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 7 (Lifetime Homes Standard;
accessibility lit).

Four PARTIAL checks at v1:
  P7.1  At least one bedroom on ground floor — RUNNABLE if floor_metadata
  P7.2  At least one toilet on ground floor — RUNNABLE if floor_metadata
  P7.3  Living + kitchen on ground floor — RUNNABLE if floor_metadata
  P7.4  Step-free entry from outside — DEFERRED (envelope detail
        not modeled; B-C15-STEP-FREE-ENTRY-DATA)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from ..contracts import CulturalProfile, FloorInfo
from ..protocol import CheckContext, DEP_FLOOR_METADATA, DEP_ROOM_CATEGORIES
from ..schema import (
    CheckEpistemicKind, CheckSeverity, CheckStatus,
    DeferredCheck, ProblemCheck,
)


BEDROOM_CATS: Final[frozenset[str]] = frozenset({"bedroom", "master_bedroom"})
BATHROOM_CATS: Final[frozenset[str]] = frozenset({"bathroom", "wc", "bathroom_wc"})
LIVING_CATS: Final[frozenset[str]] = frozenset({"living", "drawing", "family"})
KITCHEN_CATS: Final[frozenset[str]] = frozenset({"kitchen", "kitchen_dining"})


def _missing_dep(cid: str, dim: int, dep: str) -> DeferredCheck:
    return DeferredCheck(
        check_id=cid, dimension_id=dim,
        na_reason=f"data dependency {dep!r} not satisfied on this candidate.",
        blocking_backlog_item="",
    )


def _ground_floor(floor_metadata: tuple[FloorInfo, ...]) -> Optional[FloorInfo]:
    for f in floor_metadata:
        if f.is_ground:
            return f
    return None


def _present(cats: dict[str, str], room_ids: tuple[str, ...], cat_set: frozenset[str]) -> list[str]:
    return [rid for rid in room_ids if cats.get(rid, "") in cat_set]


@dataclass(frozen=True)
class _GroundFloorCheckBase:
    """Shared base for P7.1/P7.2/P7.3 — checks-of-shape: 'is some
    category present on the ground floor?'"""
    check_id: str = ""
    dimension_id: int = 7
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (DEP_ROOM_CATEGORIES, DEP_FLOOR_METADATA)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None


# =============================================================================
# P7.1 — At least one bedroom on ground floor
# =============================================================================

@dataclass(frozen=True)
class CheckP71BedroomOnGround(_GroundFloorCheckBase):
    check_id: str = "P7.1"

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        gf = _ground_floor(context.metadata.floor_metadata)
        if gf is None:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No ground floor declared in floor_metadata.",
                blocking_backlog_item="",
            )
        cats = context.metadata.room_categories
        bedrooms_on_gf = _present(cats, gf.room_ids, BEDROOM_CATS)
        if bedrooms_on_gf:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.IMPORTANT,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Lifetime Homes Standard: bedroom on ground floor for aging-in-place.",
                why_it_matters="Ground floor includes at least one bedroom — supports older family members and recovery from injury without stair-climbing.",
                suggested_mitigation=None,
                measurement={"n_bedrooms_on_ground": len(bedrooms_on_gf)},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind, affected_room_ids=(),
            rule_citation="Lifetime Homes Standard: bedroom on ground floor for aging-in-place.",
            why_it_matters="Ground floor has no bedroom — older family members or anyone with mobility limits must climb stairs daily.",
            suggested_mitigation="Convert a ground-floor study/utility to a bedroom, or restructure the floor plan to include one.",
            measurement={"n_bedrooms_on_ground": 0},
        )


# =============================================================================
# P7.2 — At least one toilet on ground floor
# =============================================================================

@dataclass(frozen=True)
class CheckP72ToiletOnGround(_GroundFloorCheckBase):
    check_id: str = "P7.2"

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        gf = _ground_floor(context.metadata.floor_metadata)
        if gf is None:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No ground floor declared in floor_metadata.",
                blocking_backlog_item="",
            )
        cats = context.metadata.room_categories
        toilets_on_gf = _present(cats, gf.room_ids, BATHROOM_CATS)
        if toilets_on_gf:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.IMPORTANT,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Lifetime Homes Standard: toilet on ground floor.",
                why_it_matters="Ground floor includes at least one toilet — guests and elderly do not climb stairs for basic facilities.",
                suggested_mitigation=None,
                measurement={"n_toilets_on_ground": len(toilets_on_gf)},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.FAIL, severity=CheckSeverity.CRITICAL,
            epistemic_kind=self.epistemic_kind, affected_room_ids=(),
            rule_citation="Lifetime Homes Standard: toilet on ground floor.",
            why_it_matters="Ground floor has NO toilet — guests, elderly visitors, and anyone in a hurry must climb stairs.",
            suggested_mitigation="Add a powder room (~1.1 m² WC) on the ground floor; almost always possible under staircase or in spare corner.",
            measurement={"n_toilets_on_ground": 0},
        )


# =============================================================================
# P7.3 — Living + kitchen on ground floor
# =============================================================================

@dataclass(frozen=True)
class CheckP73LivingKitchenOnGround(_GroundFloorCheckBase):
    check_id: str = "P7.3"

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        gf = _ground_floor(context.metadata.floor_metadata)
        if gf is None:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No ground floor declared in floor_metadata.",
                blocking_backlog_item="",
            )
        cats = context.metadata.room_categories
        has_living = bool(_present(cats, gf.room_ids, LIVING_CATS))
        has_kitchen = bool(_present(cats, gf.room_ids, KITCHEN_CATS))
        if has_living and has_kitchen:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.IMPORTANT,
                epistemic_kind=self.epistemic_kind, affected_room_ids=(),
                rule_citation="Standard residential: primary daytime zones on ground floor.",
                why_it_matters="Living and kitchen both on ground floor — daily routines do not require stairs.",
                suggested_mitigation=None,
                measurement={"has_living_on_ground": 1, "has_kitchen_on_ground": 1},
            )
        missing = []
        if not has_living:
            missing.append("living")
        if not has_kitchen:
            missing.append("kitchen")
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.FAIL, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind, affected_room_ids=(),
            rule_citation="Standard residential: primary daytime zones on ground floor.",
            why_it_matters=(
                f"Ground floor is missing: {', '.join(missing)}. Family "
                f"members climb stairs many times per day for routine tasks."
            ),
            suggested_mitigation="Re-allocate ground floor space to include both living and kitchen on entry level.",
            measurement={
                "has_living_on_ground": 1 if has_living else 0,
                "has_kitchen_on_ground": 1 if has_kitchen else 0,
            },
        )


# =============================================================================
# P7.4 — Step-free entry (DEFERRED)
# =============================================================================

@dataclass(frozen=True)
class CheckP74StepFreeEntry:
    check_id: str = "P7.4"
    dimension_id: int = 7
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = ("step_free_entry_data",)
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            na_reason=(
                "Step-free entry check requires envelope-detail data "
                "(plinth height, ramp presence, threshold rise) not in "
                "the v1 pipeline."
            ),
            blocking_backlog_item="B-C15-STEP-FREE-ENTRY-DATA",
        )


REGISTERED_CHECKS: tuple = (
    CheckP71BedroomOnGround(),
    CheckP72ToiletOnGround(),
    CheckP73LivingKitchenOnGround(),
    CheckP74StepFreeEntry(),
)

__all__ = [
    "CheckP71BedroomOnGround", "CheckP72ToiletOnGround",
    "CheckP73LivingKitchenOnGround", "CheckP74StepFreeEntry",
    "REGISTERED_CHECKS",
]
