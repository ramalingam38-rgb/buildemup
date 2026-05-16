"""
BuildemUp — Component 15 — Dimensions 4, 8, 9, 10 (DEFERRED at v1)
======================================================================

Per C15 SPEC v0.2 LOCKED § 1.4 — these dimensions need upstream data
not present in the v1 C12 / C13 / C14 / metadata pipeline:

  Dim 4  Natural light — needs window placement (size, orientation)
  Dim 8  Outdoor connection — needs window placement + envelope orientation
  Dim 9  Storage — needs furniture-fit data
  Dim 10 Multi-functional — needs furniture-fit data

All 15 checks below ALWAYS emit DeferredCheck at v1. This is the
honest data envelope (A5 + A6): we name the gaps as artifact-level
rather than burying them in spec prose. Future upstream extensions
(window placement engine, furniture-fit engine) unlock these
dimensions without changing C15's schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..contracts import CulturalProfile
from ..protocol import CheckContext, DEP_FURNITURE_FIT, DEP_WINDOW_DATA
from ..schema import CheckEpistemicKind, DeferredCheck, ProblemCheck


@dataclass(frozen=True)
class _AlwaysDeferred:
    """Shared base for the all-deferred check classes. Subclasses
    override class-level attributes."""
    check_id: str = ""
    dimension_id: int = 0
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = ()
    cultural_scope: Optional[frozenset[CulturalProfile]] = None
    _na_reason: str = ""
    _blocking_item: str = ""

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        return DeferredCheck(
            check_id=self.check_id,
            dimension_id=self.dimension_id,
            na_reason=self._na_reason,
            blocking_backlog_item=self._blocking_item,
        )


# =============================================================================
# Dim 4 — Natural light
# =============================================================================

_WINDOW_REASON = (
    "Natural-light evaluation requires per-room window placement "
    "(size, orientation, sill height) — not in v1 C13 output. "
    "Future window-placement engine unlocks this dimension."
)

@dataclass(frozen=True)
class CheckP41WindowPerHabitable(_AlwaysDeferred):
    check_id: str = "P4.1"; dimension_id: int = 4
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY
    data_dependencies: tuple[str, ...] = (DEP_WINDOW_DATA,)
    _na_reason: str = _WINDOW_REASON
    _blocking_item: str = "B-C15-WINDOW-DATA"


@dataclass(frozen=True)
class CheckP42WindowFloorRatio(_AlwaysDeferred):
    check_id: str = "P4.2"; dimension_id: int = 4
    data_dependencies: tuple[str, ...] = (DEP_WINDOW_DATA,)
    _na_reason: str = _WINDOW_REASON
    _blocking_item: str = "B-C15-WINDOW-DATA"


@dataclass(frozen=True)
class CheckP43CrossVentilation(_AlwaysDeferred):
    check_id: str = "P4.3"; dimension_id: int = 4
    data_dependencies: tuple[str, ...] = (DEP_WINDOW_DATA,)
    _na_reason: str = _WINDOW_REASON
    _blocking_item: str = "B-C15-WINDOW-DATA"


@dataclass(frozen=True)
class CheckP44NorthFacingWindowHotClimate(_AlwaysDeferred):
    check_id: str = "P4.4"; dimension_id: int = 4
    data_dependencies: tuple[str, ...] = (DEP_WINDOW_DATA, "envelope_orientation")
    _na_reason: str = _WINDOW_REASON + " Also needs envelope cardinal orientation."
    _blocking_item: str = "B-C15-WINDOW-DATA"


# =============================================================================
# Dim 8 — Outdoor connection
# =============================================================================

_OUTDOOR_REASON = (
    "Outdoor-connection evaluation requires window placement + envelope "
    "orientation + balcony/garden/terrace metadata — not in v1 pipeline."
)

@dataclass(frozen=True)
class CheckP81HabitableOutdoorView(_AlwaysDeferred):
    check_id: str = "P8.1"; dimension_id: int = 8
    data_dependencies: tuple[str, ...] = (DEP_WINDOW_DATA,)
    _na_reason: str = _OUTDOOR_REASON
    _blocking_item: str = "B-C15-WINDOW-DATA"


@dataclass(frozen=True)
class CheckP82BalconyAdjacentLiving(_AlwaysDeferred):
    check_id: str = "P8.2"; dimension_id: int = 8
    data_dependencies: tuple[str, ...] = ("balcony_metadata",)
    _na_reason: str = "Requires balcony placement metadata not in v1 pipeline."
    _blocking_item: str = "B-C15-OUTDOOR-METADATA"


@dataclass(frozen=True)
class CheckP83GardenVisibilityPublic(_AlwaysDeferred):
    check_id: str = "P8.3"; dimension_id: int = 8
    data_dependencies: tuple[str, ...] = ("garden_metadata", DEP_WINDOW_DATA)
    _na_reason: str = "Requires garden + window orientation data not in v1 pipeline."
    _blocking_item: str = "B-C15-OUTDOOR-METADATA"


@dataclass(frozen=True)
class CheckP84OutdoorDryingSpace(_AlwaysDeferred):
    check_id: str = "P8.4"; dimension_id: int = 8
    data_dependencies: tuple[str, ...] = ("utility_terrace_metadata",)
    _na_reason: str = "Requires utility-terrace/drying-space data not in v1 pipeline. Indian residential POE expectation."
    _blocking_item: str = "B-C15-OUTDOOR-METADATA"


# =============================================================================
# Dim 9 — Storage
# =============================================================================

_STORAGE_REASON = (
    "Storage evaluation requires per-room furniture-fit analysis "
    "(wardrobe placement, cabinet sizing) — not in v1 pipeline."
)

@dataclass(frozen=True)
class CheckP91WardrobePerBedroom(_AlwaysDeferred):
    check_id: str = "P9.1"; dimension_id: int = 9
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _STORAGE_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


@dataclass(frozen=True)
class CheckP92KitchenStorageVolume(_AlwaysDeferred):
    check_id: str = "P9.2"; dimension_id: int = 9
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _STORAGE_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


@dataclass(frozen=True)
class CheckP93CommonAreaStorage(_AlwaysDeferred):
    check_id: str = "P9.3"; dimension_id: int = 9
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _STORAGE_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


@dataclass(frozen=True)
class CheckP94UtilityStorage(_AlwaysDeferred):
    check_id: str = "P9.4"; dimension_id: int = 9
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _STORAGE_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


# =============================================================================
# Dim 10 — Multi-functional
# =============================================================================

_MULTIFUNC_REASON = (
    "Multi-functional / adaptive-housing evaluation requires furniture-"
    "fit analysis (footprint of alternative arrangements) — not in v1 "
    "pipeline (Brand 1994 'How Buildings Learn' style metric)."
)

@dataclass(frozen=True)
class CheckP101LivingFlexibility(_AlwaysDeferred):
    check_id: str = "P10.1"; dimension_id: int = 10
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _MULTIFUNC_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


@dataclass(frozen=True)
class CheckP102BedroomDualUse(_AlwaysDeferred):
    check_id: str = "P10.2"; dimension_id: int = 10
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _MULTIFUNC_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


@dataclass(frozen=True)
class CheckP103ConvertibleSpaces(_AlwaysDeferred):
    check_id: str = "P10.3"; dimension_id: int = 10
    data_dependencies: tuple[str, ...] = (DEP_FURNITURE_FIT,)
    _na_reason: str = _MULTIFUNC_REASON
    _blocking_item: str = "B-C15-FURNITURE-FIT"


# =============================================================================
# Registry exports per dimension
# =============================================================================

DIM04_REGISTERED_CHECKS: tuple = (
    CheckP41WindowPerHabitable(), CheckP42WindowFloorRatio(),
    CheckP43CrossVentilation(), CheckP44NorthFacingWindowHotClimate(),
)
DIM08_REGISTERED_CHECKS: tuple = (
    CheckP81HabitableOutdoorView(), CheckP82BalconyAdjacentLiving(),
    CheckP83GardenVisibilityPublic(), CheckP84OutdoorDryingSpace(),
)
DIM09_REGISTERED_CHECKS: tuple = (
    CheckP91WardrobePerBedroom(), CheckP92KitchenStorageVolume(),
    CheckP93CommonAreaStorage(), CheckP94UtilityStorage(),
)
DIM10_REGISTERED_CHECKS: tuple = (
    CheckP101LivingFlexibility(), CheckP102BedroomDualUse(),
    CheckP103ConvertibleSpaces(),
)


__all__ = [
    # Dim 4
    "CheckP41WindowPerHabitable", "CheckP42WindowFloorRatio",
    "CheckP43CrossVentilation", "CheckP44NorthFacingWindowHotClimate",
    # Dim 8
    "CheckP81HabitableOutdoorView", "CheckP82BalconyAdjacentLiving",
    "CheckP83GardenVisibilityPublic", "CheckP84OutdoorDryingSpace",
    # Dim 9
    "CheckP91WardrobePerBedroom", "CheckP92KitchenStorageVolume",
    "CheckP93CommonAreaStorage", "CheckP94UtilityStorage",
    # Dim 10
    "CheckP101LivingFlexibility", "CheckP102BedroomDualUse", "CheckP103ConvertibleSpaces",
    # Registries
    "DIM04_REGISTERED_CHECKS", "DIM08_REGISTERED_CHECKS",
    "DIM09_REGISTERED_CHECKS", "DIM10_REGISTERED_CHECKS",
]
