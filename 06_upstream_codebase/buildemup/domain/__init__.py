"""
BuildemUp† — Domain Layer (v0.7.2 / Component 1 v0.1)
=========================================================

Shared domain objects that multiple components read/write.

WHY THIS EXISTS:
  Before v0.6, each component defined its own shape for Building, Grid,
  Column. That's assumption drift. The /domain/ layer puts shared
  concepts in ONE place.

PRINCIPLE — "Lightweight domain, fat components":
  Domain objects are DUMB: dataclasses with validation. They don't know
  about IS codes, material rates, or foundations. Components import
  domain types and add behaviour on top.

v0.7.2 scope:
  - Building, BuildingMeta, Floor, FloorType   (Component 7)
  - Column, ColumnLocation                      (Component 7)
  - Grid (DomainGrid)                           (Component 7)
  - Envelope, PlotOrientation                   (Component 7)

Component 1 v0.1 adds:
  - Plot, PlotType, SharedSide, SoilType        (buyer's plot of land)
  - Setbacks                                    (4-side setback values)
  - FloorRequirement, RoomRequirement           (what user wants per floor)
  - FloorUse, RoomType                          (enums)
  - Brief, BudgetRange, CostEstimate            (top-level Brief)
  - VastuTier, VASTU_PARTIAL_ITEMS              (Q5 vastu opt-in)
  - GuidanceSeverity, GuidanceMessage           (soft-guide messages)
  - ComplianceSummary                           (compliance overview)

†= placeholder name marker.
"""
# Existing (Component 7 era)
from buildemup.domain.building import Building, BuildingMeta
from buildemup.domain.floor import Floor, FloorType
from buildemup.domain.column import Column, ColumnLocation
from buildemup.domain.envelope import Envelope, PlotOrientation
from buildemup.domain.grid import DomainGrid

# Component 1 v0.1 additions
from buildemup.domain.plot import (
    Plot, PlotType, SharedSide, SoilType, SUPPORTED_CITIES,
)
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import (
    FloorRequirement, RoomRequirement, FloorUse, RoomType,
    NBC_MINIMUM_ROOM_SIZES_SQM,
)
from buildemup.domain.brief import (
    Brief, BudgetRange, CostEstimate,
    VastuTier, VASTU_PARTIAL_ITEMS,
    GuidanceSeverity, GuidanceMessage,
    ComplianceSummary,
)

__all__ = [
    # Existing
    "Building",
    "BuildingMeta",
    "Floor",
    "FloorType",
    "Column",
    "ColumnLocation",
    "Envelope",
    "PlotOrientation",
    "DomainGrid",
    # Component 1 additions
    "Plot",
    "PlotType",
    "SharedSide",
    "SoilType",
    "SUPPORTED_CITIES",
    "Setbacks",
    "FloorRequirement",
    "RoomRequirement",
    "FloorUse",
    "RoomType",
    "NBC_MINIMUM_ROOM_SIZES_SQM",
    "Brief",
    "BudgetRange",
    "CostEstimate",
    "VastuTier",
    "VASTU_PARTIAL_ITEMS",
    "GuidanceSeverity",
    "GuidanceMessage",
    "ComplianceSummary",
]
