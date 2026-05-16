"""
BuildemUp — Component 15 — Dimension 3: Logical Flow
=========================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 3 (Hillier 1984/1987;
van Hoogdalem 1985).

Four checks at v1 — all consume C14 CirculationGraphReport:
  P3.1  Step-depth main_entry → bedrooms ≤ 3 — HEURISTIC
  P3.2  Public-to-private depth monotonicity — HEURISTIC
  P3.3  Kitchen-to-dining adjacency — HEURISTIC
  P3.4  Pooja room accessible from public zone — CULTURAL_PREFERENCE
        (only meaningful for Indian profiles)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from ..contracts import CulturalProfile
from ..protocol import (
    CheckContext, DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_MAIN_ENTRY,
    DEP_ROOM_CATEGORIES,
)
from ..schema import (
    CheckEpistemicKind, CheckSeverity, CheckStatus,
    DeferredCheck, ProblemCheck,
)


BEDROOM_CATS: Final[frozenset[str]] = frozenset({"bedroom", "master_bedroom"})
PUBLIC_CATS: Final[frozenset[str]] = frozenset({"living", "drawing", "family", "dining"})
KITCHEN_CATS: Final[frozenset[str]] = frozenset({"kitchen", "kitchen_dining"})
DINING_CATS: Final[frozenset[str]] = frozenset({"dining", "kitchen_dining"})
POOJA_CATS: Final[frozenset[str]] = frozenset({"pooja", "puja", "prayer"})

INDIAN_PROFILES: Final[frozenset[CulturalProfile]] = frozenset({
    CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
    CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
    CulturalProfile.INDIAN_MIDDLE_CLASS_COMPACT_URBAN,
    CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    CulturalProfile.INDIAN_LOWER_INCOME_INCREMENTAL,
    CulturalProfile.INDIAN_NRI_RETURNEE,
})

P31_STEP_DEPTH_PASS: Final[int] = 3
P31_STEP_DEPTH_WARN: Final[int] = 4


def _missing_dep(cid: str, dim: int, dep: str) -> DeferredCheck:
    return DeferredCheck(
        check_id=cid, dimension_id=dim,
        na_reason=f"data dependency {dep!r} not satisfied on this candidate.",
        blocking_backlog_item="",
    )


def _step_depth_map(c14_report: object) -> dict[str, int]:
    """Extract step_depth_from_entry as a dict."""
    raw = getattr(c14_report, "step_depth_from_entry", ())
    return dict(raw)


def _adjacent(c14_report: object) -> dict[str, frozenset[str]]:
    """Build a room_id → adjacent_room_ids map from C14 edges."""
    adj: dict[str, set[str]] = {}
    edges = getattr(c14_report, "edges", ())
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return {k: frozenset(v) for k, v in adj.items()}


# =============================================================================
# P3.1 — Step-depth main_entry → bedrooms ≤ 3
# =============================================================================

@dataclass(frozen=True)
class CheckP31BedroomDepthFromEntry:
    check_id: str = "P3.1"
    dimension_id: int = 3
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
        bedrooms = [rid for rid, cat in cats.items() if cat in BEDROOM_CATS]
        if not bedrooms:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No bedrooms in placement; depth-from-entry to bedrooms does not apply.",
                blocking_backlog_item="",
            )

        offenders_warn: list[str] = []
        offenders_fail: list[str] = []
        for rid in bedrooms:
            d = depths.get(rid, -1)
            if d < 0:
                continue
            if d > P31_STEP_DEPTH_WARN:
                offenders_fail.append(rid)
            elif d > P31_STEP_DEPTH_PASS:
                offenders_warn.append(rid)

        if offenders_fail:
            status = CheckStatus.FAIL
            why = (
                f"{len(offenders_fail)} bedroom(s) are at step depth > 4 from "
                f"the main entrance. Walking to your bedroom passes through "
                f"too many intermediate rooms — fatiguing and bad privacy."
            )
            mitigation = "Restructure circulation so bedrooms sit no more than 3 steps from entry."
            affected = tuple(sorted(offenders_fail + offenders_warn))
        elif offenders_warn:
            status = CheckStatus.WARN
            why = (
                f"{len(offenders_warn)} bedroom(s) at step depth 4 from "
                f"entry. Acceptable for second-floor private cluster; "
                f"problematic if ground floor."
            )
            mitigation = "Consider re-routing if the deep bedroom is on the ground floor."
            affected = tuple(sorted(offenders_warn))
        else:
            status, why, mitigation, affected = (
                CheckStatus.PASS, "All bedrooms within 3 steps of main entrance.", None, (),
            )

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="Hillier 1984 — space syntax: residential bedrooms should sit within 3 graph-steps of entry for daily-life ergonomics.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={
                "n_bedrooms": len(bedrooms),
                "max_bedroom_depth": max((depths.get(rid, -1) for rid in bedrooms), default=-1),
                "n_over_pass_threshold": len(offenders_warn) + len(offenders_fail),
            },
        )


# =============================================================================
# P3.2 — Public-to-private depth monotonicity
# =============================================================================

@dataclass(frozen=True)
class CheckP32PublicPrivateMonotonicity:
    """Public rooms (living/dining) should sit at shallower depths
    than private rooms (bedrooms). Failure: private at depth < some
    public room → privacy gradient inverted."""
    check_id: str = "P3.2"
    dimension_id: int = 3
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
        public_depths = [depths.get(rid, -1) for rid, c in cats.items() if c in PUBLIC_CATS and depths.get(rid, -1) >= 0]
        bedroom_depths = [(rid, depths.get(rid, -1)) for rid, c in cats.items() if c in BEDROOM_CATS and depths.get(rid, -1) >= 0]
        if not public_depths or not bedroom_depths:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="Need both public rooms and bedrooms with depth data; missing.",
                blocking_backlog_item="",
            )
        max_public = max(public_depths)
        offenders = [rid for rid, d in bedroom_depths if d < max_public]

        if not offenders:
            status, why, mitigation, affected = (
                CheckStatus.PASS,
                "Privacy gradient holds: all bedrooms sit at depths ≥ max public-room depth.",
                None, (),
            )
        else:
            status = CheckStatus.WARN
            why = (
                f"{len(offenders)} bedroom(s) sit shallower than the deepest "
                f"public room — privacy gradient inverted. Family/guests "
                f"in the deep public space have to pass closer to the "
                f"bedroom than the entry path does."
            )
            mitigation = "Swap bedroom and public-room positions on the floor plan, or restructure circulation."
            affected = tuple(sorted(offenders))
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="Hillier 1984/1987 — public-to-private depth monotonicity is a basic permeability-graph privacy heuristic.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={
                "max_public_depth": max_public,
                "n_bedrooms_shallower_than_max_public": len(offenders),
            },
        )


# =============================================================================
# P3.3 — Kitchen-to-dining adjacency
# =============================================================================

@dataclass(frozen=True)
class CheckP33KitchenDiningAdjacency:
    check_id: str = "P3.3"
    dimension_id: int = 3
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
        kitchens = [rid for rid, c in cats.items() if c in KITCHEN_CATS]
        dinings = [rid for rid, c in cats.items() if c in DINING_CATS]

        # Combined kitchen_dining counts as adjacent-to-itself trivially.
        if not kitchens:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No kitchen in placement.",
                blocking_backlog_item="",
            )
        if not dinings:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No dining/kitchen_dining in placement.",
                blocking_backlog_item="",
            )

        # If there's a kitchen_dining, the check is trivially satisfied.
        combined = any(cats.get(rid) == "kitchen_dining" for rid in kitchens)
        adjacent_ok = False
        if combined:
            adjacent_ok = True
        else:
            for k in kitchens:
                if any(d in adj.get(k, frozenset()) for d in dinings):
                    adjacent_ok = True
                    break

        if adjacent_ok:
            return ProblemCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                status=CheckStatus.PASS, severity=CheckSeverity.NICE_TO_HAVE,
                epistemic_kind=self.epistemic_kind,
                affected_room_ids=(),
                rule_citation="Standard residential adjacency: kitchen-dining share a wall or door.",
                why_it_matters="Carrying food + dishes between kitchen and dining is a daily walk; sharing a wall keeps it short.",
                suggested_mitigation=None,
                measurement={"adjacent": 1, "combined_room": 1 if combined else 0},
            )
        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=CheckStatus.WARN, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=tuple(sorted(kitchens + dinings)),
            rule_citation="Standard residential adjacency: kitchen-dining should share a wall or door.",
            why_it_matters="Kitchen is not adjacent to any dining room; food/dish carry path crosses other rooms each meal.",
            suggested_mitigation="Re-place kitchen and dining to share a wall, or use a kitchen_dining combined room.",
            measurement={"adjacent": 0, "combined_room": 0},
        )


# =============================================================================
# P3.4 — Pooja room access (cultural preference)
# =============================================================================

@dataclass(frozen=True)
class CheckP34PoojaRoomAccess:
    """Pooja room reachable from public zone within 2 steps, for
    Indian cultural profiles only. For non-Indian profiles → defer
    with cultural_profile_mismatch reason (Inv P13)."""
    check_id: str = "P3.4"
    dimension_id: int = 3
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.CULTURAL_PREFERENCE
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C14_GRAPH, DEP_ROOM_CATEGORIES, DEP_MAIN_ENTRY,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = INDIAN_PROFILES

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        # Inv P13: cultural_profile not in scope → defer with structured reason.
        if (
            self.cultural_scope is not None
            and context.metadata.cultural_profile not in self.cultural_scope
        ):
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason=(
                    f"cultural_profile_mismatch: {context.metadata.cultural_profile.value!r} "
                    f"is outside this check's declared cultural_scope; pooja-room "
                    f"access is a culturally-specific consideration."
                ),
                blocking_backlog_item="",
            )

        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)

        cats = context.metadata.room_categories
        depths = _step_depth_map(context.circulation_report)
        poojas = [rid for rid, c in cats.items() if c in POOJA_CATS]
        if not poojas:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No pooja room in placement; nothing to evaluate.",
                blocking_backlog_item="",
            )

        # Pooja room reachable from public means: its step depth from
        # entry is no greater than the deepest public room + 1.
        public_depths = [depths.get(rid, -1) for rid, c in cats.items() if c in PUBLIC_CATS and depths.get(rid, -1) >= 0]
        if not public_depths:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No public rooms with depth data; reference for pooja-access depth unavailable.",
                blocking_backlog_item="",
            )
        max_public = max(public_depths)
        max_allowed = max_public + 1

        offenders = [rid for rid in poojas if depths.get(rid, -1) > max_allowed]
        if not offenders:
            status, why, mitigation, affected = (
                CheckStatus.PASS,
                "Pooja room is within one step of the public zone — appropriately accessible.",
                None, (),
            )
        else:
            status = CheckStatus.WARN
            why = (
                "Pooja room is buried deeper than the public zone. In "
                "Indian residential POE, the pooja room is typically "
                "reachable from the living/dining area without passing "
                "through bedrooms."
            )
            mitigation = "Re-position pooja near living or dedicated alcove off public circulation."
            affected = tuple(sorted(offenders))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.NICE_TO_HAVE,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="Indian residential POE: pooja room accessible from public zone, not via bedrooms.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={"max_public_depth": max_public, "n_buried_pooja": len(offenders)},
        )


REGISTERED_CHECKS: tuple = (
    CheckP31BedroomDepthFromEntry(),
    CheckP32PublicPrivateMonotonicity(),
    CheckP33KitchenDiningAdjacency(),
    CheckP34PoojaRoomAccess(),
)

__all__ = [
    "INDIAN_PROFILES",
    "CheckP31BedroomDepthFromEntry", "CheckP32PublicPrivateMonotonicity",
    "CheckP33KitchenDiningAdjacency", "CheckP34PoojaRoomAccess",
    "REGISTERED_CHECKS",
]
