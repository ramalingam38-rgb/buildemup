"""
BuildemUp — Component 15 — Dimension 2: Room Sizes Match Function
====================================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 2 (Neufert; Ching).

Five RUNNABLE checks at v1 (all consume C12 geometry + room_categories):
  - P2.1  Habitable room min area (NBC 9.5 m²) — REGULATORY
  - P2.2  Bedroom adequate area (Neufert master ≥ 12 m²) — HEURISTIC
  - P2.3  Kitchen min area (NBC 5.0 m² for separate kitchen) — REGULATORY
  - P2.4  Bathroom min area (NBC 1.8 m² bath / 2.8 m² combined) — REGULATORY
  - P2.5  Living room min area for typical family (≥ 12 m² baseline) — HEURISTIC

Rule 11 verification (S48): All NBC values verified against NBC 2016
Part 3 § 12 secondary citations (multiple sources). Habitable-room
9.5 m² minimum confirmed; kitchen 5.0 m² separate / 7.5 m² kitchen-
cum-dining confirmed; bath 1.8 m² alone / 2.8 m² combined with WC
confirmed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

from ..contracts import CulturalProfile
from ..protocol import (
    CheckContext,
    DEP_C12_PLACEMENT,
    DEP_C12_PLACEMENT_GEOMETRY,
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
# Category sets + thresholds
# =============================================================================

HABITABLE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"bedroom", "master_bedroom", "living", "dining", "study", "office"}
)

BEDROOM_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"bedroom", "master_bedroom"}
)

KITCHEN_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"kitchen", "kitchen_dining"}
)

BATHROOM_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"bathroom", "wc", "bathroom_wc"}
)

LIVING_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"living", "drawing", "family"}
)

# NBC 2016 Part 3 minima (m²)
NBC_HABITABLE_MIN_M2: Final[float] = 9.5
NBC_KITCHEN_SEPARATE_MIN_M2: Final[float] = 5.0
NBC_KITCHEN_DINING_MIN_M2: Final[float] = 7.5
NBC_BATHROOM_ALONE_MIN_M2: Final[float] = 1.8
NBC_BATHROOM_WC_COMBINED_MIN_M2: Final[float] = 2.8
NBC_WC_ALONE_MIN_M2: Final[float] = 1.1

# Neufert + Indian POE heuristics
MASTER_BEDROOM_TARGET_M2: Final[float] = 12.0
STANDARD_BEDROOM_TARGET_M2: Final[float] = 9.0
LIVING_TARGET_M2: Final[float] = 12.0


# =============================================================================
# Shared helper
# =============================================================================

def _missing_dep(check_id: str, dim: int, dep: str) -> DeferredCheck:
    return DeferredCheck(
        check_id=check_id, dimension_id=dim,
        na_reason=f"data dependency {dep!r} not satisfied on this candidate.",
        blocking_backlog_item="",
    )


def _area(room: object) -> float:
    return room.width_m * room.depth_m  # type: ignore[attr-defined]


# =============================================================================
# P2.1 — Habitable room min area (NBC 9.5 m²)
# =============================================================================

@dataclass(frozen=True)
class CheckP21HabitableMinArea:
    """P2.1 — Every habitable room ≥ 9.5 m² per NBC 2016 Part 3.

    REGULATORY. Below NBC floor → FAIL (the layout is not legally
    certifiable as drawn).
    """
    check_id: str = "P2.1"
    dimension_id: int = 2
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]

        offenders: list[tuple[str, float]] = []
        habitable_count = 0
        for r in pr:
            cat = cats.get(r.room_id, "")
            if cat not in HABITABLE_CATEGORIES:
                continue
            habitable_count += 1
            a = _area(r)
            if a < NBC_HABITABLE_MIN_M2:
                offenders.append((r.room_id, a))

        if habitable_count == 0:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No habitable rooms found; NBC habitable-area minima do not apply.",
                blocking_backlog_item="",
            )

        if not offenders:
            status, why, mitigation, affected = (
                CheckStatus.PASS,
                "All habitable rooms meet NBC 2016 Part 3 minimum of 9.5 m².",
                None, (),
            )
        else:
            status = CheckStatus.FAIL
            why = (
                f"{len(offenders)} habitable room(s) below NBC 2016 Part 3 "
                f"minimum of 9.5 m². As drawn, the layout is not legally "
                f"certifiable for the municipal permit set."
            )
            mitigation = (
                "Expand the offending room(s) to at least 9.5 m². "
                "Typical fix: borrow 30-60 cm of width or depth from an "
                "adjacent service area (corridor, storage)."
            )
            affected = tuple(sorted(rid for rid, _ in offenders))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.CRITICAL,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="NBC 2016 Part 3 § 12 — habitable-room minimum area 9.5 m².",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={
                "n_habitable_rooms": habitable_count,
                "n_below_nbc_min": len(offenders),
                "smallest_habitable_m2": round(min((a for _, a in offenders), default=NBC_HABITABLE_MIN_M2), 4),
            },
        )


# =============================================================================
# P2.2 — Bedroom adequate area (Neufert master ≥ 12 m²)
# =============================================================================

@dataclass(frozen=True)
class CheckP22BedroomAdequateArea:
    """P2.2 — Bedrooms meet Neufert/Ching adequacy targets.

    ARCHITECTURAL_HEURISTIC. Master bedroom ≥ 12 m² target; standard
    bedroom ≥ 9 m² target. Below standard = WARN (tight but liveable);
    below 6 m² = FAIL (queen bed + circulation won't fit).
    """
    check_id: str = "P2.2"
    dimension_id: int = 2
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]

        warn_offenders: list[str] = []
        fail_offenders: list[str] = []
        bedroom_count = 0
        for r in pr:
            cat = cats.get(r.room_id, "")
            if cat not in BEDROOM_CATEGORIES:
                continue
            bedroom_count += 1
            a = _area(r)
            target = MASTER_BEDROOM_TARGET_M2 if cat == "master_bedroom" else STANDARD_BEDROOM_TARGET_M2
            if a < 6.0:
                fail_offenders.append(r.room_id)
            elif a < target:
                warn_offenders.append(r.room_id)

        if bedroom_count == 0:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No bedrooms in placement; Neufert bedroom-adequacy targets do not apply.",
                blocking_backlog_item="",
            )

        if fail_offenders:
            status = CheckStatus.FAIL
            why = (
                f"{len(fail_offenders)} bedroom(s) below 6 m² — too small "
                f"for a queen bed + 60 cm circulation around it. The room "
                f"becomes single-bed-only and uncomfortable for adult use."
            )
            mitigation = "Expand offending bedroom(s) to at least 9 m² (standard) or 12 m² (master)."
            affected = tuple(sorted(fail_offenders))
        elif warn_offenders:
            status = CheckStatus.WARN
            why = (
                f"{len(warn_offenders)} bedroom(s) below Neufert target "
                f"(9 m² standard / 12 m² master). Liveable but constrained — "
                f"limits wardrobe + furniture placement options."
            )
            mitigation = "Consider expanding by 0.5-1.0 m in one dimension if envelope allows."
            affected = tuple(sorted(warn_offenders))
        else:
            status, why, mitigation, affected = (
                CheckStatus.PASS,
                "All bedrooms meet Neufert/Ching adequacy targets.",
                None, (),
            )

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="Neufert Architects' Data + Ching: bedroom adequacy targets (master ≥ 12 m², standard ≥ 9 m²).",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={
                "n_bedrooms": bedroom_count,
                "n_below_target": len(warn_offenders) + len(fail_offenders),
                "n_undersized_severely": len(fail_offenders),
            },
        )


# =============================================================================
# P2.3 — Kitchen min area
# =============================================================================

@dataclass(frozen=True)
class CheckP23KitchenMinArea:
    """P2.3 — Kitchen ≥ NBC 2016 Part 3 minimum.

    REGULATORY. Separate kitchen 5.0 m² minimum; kitchen-cum-dining
    7.5 m² minimum.
    """
    check_id: str = "P2.3"
    dimension_id: int = 2
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]

        kitchens = [(r.room_id, _area(r), cats.get(r.room_id, "")) for r in pr if cats.get(r.room_id, "") in KITCHEN_CATEGORIES]
        if not kitchens:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No kitchen in placement; NBC kitchen minima do not apply.",
                blocking_backlog_item="",
            )

        offenders: list[str] = []
        for rid, a, cat in kitchens:
            min_required = NBC_KITCHEN_DINING_MIN_M2 if cat == "kitchen_dining" else NBC_KITCHEN_SEPARATE_MIN_M2
            if a < min_required:
                offenders.append(rid)

        if not offenders:
            status, why, mitigation, affected = (
                CheckStatus.PASS, "Kitchen meets NBC 2016 Part 3 minimum.", None, (),
            )
        else:
            status = CheckStatus.FAIL
            why = (
                "Kitchen below NBC 2016 Part 3 minimum (5.0 m² separate / "
                "7.5 m² kitchen-cum-dining). Layout not legally certifiable."
            )
            mitigation = "Expand kitchen to NBC minimum; usually borrowing 0.5-1.0 m from adjacent corridor or dining works."
            affected = tuple(sorted(offenders))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.CRITICAL,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="NBC 2016 Part 3 § 12.3 — kitchen minimum area.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={
                "n_kitchens": len(kitchens),
                "n_below_nbc_min": len(offenders),
            },
        )


# =============================================================================
# P2.4 — Bathroom min area
# =============================================================================

@dataclass(frozen=True)
class CheckP24BathroomMinArea:
    """P2.4 — Bathroom ≥ NBC 2016 Part 3 minimum.

    REGULATORY. Bath alone 1.8 m², WC alone 1.1 m², combined bath+WC
    2.8 m².
    """
    check_id: str = "P2.4"
    dimension_id: int = 2
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]

        offenders: list[str] = []
        bath_count = 0
        for r in pr:
            cat = cats.get(r.room_id, "")
            if cat not in BATHROOM_CATEGORIES:
                continue
            bath_count += 1
            a = _area(r)
            if cat == "wc":
                min_req = NBC_WC_ALONE_MIN_M2
            elif cat == "bathroom_wc":
                min_req = NBC_BATHROOM_WC_COMBINED_MIN_M2
            else:
                min_req = NBC_BATHROOM_ALONE_MIN_M2
            if a < min_req:
                offenders.append(r.room_id)

        if bath_count == 0:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No bathroom/WC in placement; NBC bathroom minima do not apply.",
                blocking_backlog_item="",
            )

        if not offenders:
            status, why, mitigation, affected = (
                CheckStatus.PASS, "All bathrooms/WCs meet NBC 2016 Part 3 minima.", None, (),
            )
        else:
            status = CheckStatus.FAIL
            why = (
                f"{len(offenders)} bathroom/WC below NBC 2016 Part 3 minimum. "
                f"Layout not legally certifiable for the permit set."
            )
            mitigation = "Expand offending bathroom(s) to NBC minimum (1.8 m² bath, 2.8 m² combined, 1.1 m² WC)."
            affected = tuple(sorted(offenders))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.CRITICAL,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="NBC 2016 Part 3 § 12.4 — bathroom/WC minimum area.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={"n_baths": bath_count, "n_below_nbc_min": len(offenders)},
        )


# =============================================================================
# P2.5 — Living room adequate area
# =============================================================================

@dataclass(frozen=True)
class CheckP25LivingRoomAdequateArea:
    """P2.5 — Living room ≥ 12 m² heuristic target for typical family.

    ARCHITECTURAL_HEURISTIC. Below 9.5 m² FAIL (also NBC violation
    since living is habitable; P2.1 catches that — here we grade on
    function not floor). 9.5-12 m² WARN. ≥ 12 m² PASS.
    """
    check_id: str = "P2.5"
    dimension_id: int = 2
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = (
        DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_ROOM_CATEGORIES,
    )
    cultural_scope: Optional[frozenset[CulturalProfile]] = None

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        for dep in self.data_dependencies:
            if dep not in context.available_dependencies:
                return _missing_dep(self.check_id, self.dimension_id, dep)
        cats = context.metadata.room_categories
        pr = context.placed_candidate.placed_rooms  # type: ignore[attr-defined]

        livings = [(r.room_id, _area(r)) for r in pr if cats.get(r.room_id, "") in LIVING_CATEGORIES]
        if not livings:
            return DeferredCheck(
                check_id=self.check_id, dimension_id=self.dimension_id,
                na_reason="No living/drawing/family room in placement.",
                blocking_backlog_item="",
            )

        max_area = max(a for _, a in livings)

        if max_area >= LIVING_TARGET_M2:
            status, why, mitigation, affected = (
                CheckStatus.PASS, "Living room meets 12 m² family-baseline target.", None, (),
            )
        elif max_area >= NBC_HABITABLE_MIN_M2:
            status = CheckStatus.WARN
            why = (
                f"Living room is {max_area:.1f} m² — meets NBC but below "
                f"12 m² family-baseline. Limits seating arrangement for "
                f"family of 4+."
            )
            mitigation = "Consider expanding to 12 m² if envelope and budget allow."
            affected = tuple(sorted(rid for rid, a in livings if a == max_area))
        else:
            status = CheckStatus.FAIL
            why = (
                f"Living room is {max_area:.1f} m² — below NBC habitable "
                f"floor of 9.5 m². See also P2.1."
            )
            mitigation = "Expand living to ≥ 12 m² for typical family use."
            affected = tuple(sorted(rid for rid, a in livings if a == max_area))

        return ProblemCheck(
            check_id=self.check_id, dimension_id=self.dimension_id,
            status=status, severity=CheckSeverity.IMPORTANT,
            epistemic_kind=self.epistemic_kind,
            affected_room_ids=affected,
            rule_citation="Indian residential POE heuristic: 12 m² living for 3-4 BHK family baseline.",
            why_it_matters=why, suggested_mitigation=mitigation,
            measurement={"n_living_rooms": len(livings), "max_living_area_m2": round(max_area, 4)},
        )


REGISTERED_CHECKS: tuple = (
    CheckP21HabitableMinArea(),
    CheckP22BedroomAdequateArea(),
    CheckP23KitchenMinArea(),
    CheckP24BathroomMinArea(),
    CheckP25LivingRoomAdequateArea(),
)

__all__ = [
    "HABITABLE_CATEGORIES", "BEDROOM_CATEGORIES", "KITCHEN_CATEGORIES",
    "BATHROOM_CATEGORIES", "LIVING_CATEGORIES",
    "NBC_HABITABLE_MIN_M2", "NBC_KITCHEN_SEPARATE_MIN_M2", "NBC_KITCHEN_DINING_MIN_M2",
    "NBC_BATHROOM_ALONE_MIN_M2", "NBC_BATHROOM_WC_COMBINED_MIN_M2", "NBC_WC_ALONE_MIN_M2",
    "MASTER_BEDROOM_TARGET_M2", "STANDARD_BEDROOM_TARGET_M2", "LIVING_TARGET_M2",
    "CheckP21HabitableMinArea", "CheckP22BedroomAdequateArea",
    "CheckP23KitchenMinArea", "CheckP24BathroomMinArea", "CheckP25LivingRoomAdequateArea",
    "REGISTERED_CHECKS",
]
