"""
Contractor marketplace export contract.

When the contractor marketplace launches (Phase 1, month 5-6 per vision doc),
it needs to ingest our project outputs to:
  1. Match the project to contractors who do this scope/budget/location
  2. Send the project's bill-of-materials to contractors for quoting
  3. Track which contractors quoted, won, completed

This file defines the data shape — not the marketplace itself.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ContractorBriefExport:
    """What goes to the contractor marketplace per project.

    Stable interface — once a marketplace integration is live, breaking
    changes here cost real partner re-integration work. Add fields, don't
    remove or rename.
    """
    # Project identity
    project_id: str                          # e.g., "BE-2026-04-12345"
    user_city: str
    user_area: str | None
    plot_size_sqft: int

    # Scope
    building_type: str                       # building_types.BuildingType.value
    floors_above_ground: int
    has_stilt_parking: bool
    total_built_up_sqft: int

    # Budget signal (range, not exact — we don't share user's pocket)
    estimated_cost_range_lakhs: tuple[float, float]
    estimated_timeline_months: tuple[int, int]

    # Materials at high level (BOM details available separately)
    requires_pile_foundation: bool
    requires_is13920_detailing: bool
    seismic_zone: str

    # User preferences for matching
    preferred_finish_quality: str = "standard"   # economy/standard/premium/luxury
    has_vastu_priority: bool = False
    needs_design_changes_post_quote: bool = True

    # Privacy
    user_name: str = ""                      # Empty = anonymous match first
    user_phone_masked: str = ""              # Last 4 digits only

    # Metadata
    generated_at: str = ""                   # ISO timestamp
    source_trace_id: str = ""                # Component 7 trace_id


class ContractorMarketplaceAdapter(Protocol):
    """Interface that marketplace integration must implement.

    v0.4 ships this Protocol only. Real implementations come when the
    contractor marketplace partner is signed.
    """

    def submit_project_brief(self, brief: ContractorBriefExport) -> str:
        """Submit project for contractor matching. Returns marketplace project ID."""
        ...

    def get_matched_contractors(
        self, marketplace_project_id: str
    ) -> list[dict]:
        """Get contractors who matched this project + their quotes."""
        ...

    def notify_user_of_quotes(self, marketplace_project_id: str) -> None:
        """Trigger user notification when quotes arrive."""
        ...
