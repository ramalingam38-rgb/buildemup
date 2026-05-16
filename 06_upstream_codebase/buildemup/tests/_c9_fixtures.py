"""C9 test fixtures — pipeline runners + minimal-candidate synthesis.

C9 input is a CorridorDesignedCandidate from C8. Synthesising one by hand is
heavy (OrientedCandidate alone requires direction_priorities mapping), so
fixtures lean on the real C4 -> C5 -> C6 -> C8 pipeline.

Module-coverage / unit tests that only need RoomSizeRequirement / RegulatoryMinimum /
RoomSizeTable build them directly via the schema.
"""
from __future__ import annotations

from buildemup.components.c05 import select_topology
from buildemup.components.c06 import prioritize_orientation
from buildemup.components.c07.grid_generator import GridGenerator
from buildemup.components.c08 import design_corridors
from buildemup.components.c09.schema import (
    BathroomSubtype,
    NBCSourceConfidence,
    PlacementRiskLevel,
    RegulatoryMinimum,
    RoomCategory,
    RoomSizeRequirement,
    RoomSizingProvenance,
    TierResolutionAccuracy,
    DwellingSizeTier,
    WidthFeasibilityVerdict,
    GridBayFeasibility,
)
from buildemup.domain.brief import VastuTier
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    make_plot_analysis,
    medium_brief,
    small_brief,
    large_brief,
)
from buildemup.tests.validation._c4_fixtures import (
    mumbai_30x40,
    pune_30x40,
    hyderabad_30x40,
)


__all__ = [
    "run_c8_pipeline",
    "make_regulatory",
    "make_room",
    "make_provenance_stub",
    # Re-exported plot/brief fixtures
    "bangalore_40x60", "chennai_30x40", "delhi_60x90",
    "mumbai_30x40", "pune_30x40", "hyderabad_30x40",
    "medium_brief", "small_brief", "large_brief",
    "make_plot_analysis",
]


# ---------------------------------------------------------------------------
# Real-pipeline runner
# ---------------------------------------------------------------------------


def run_c8_pipeline(*, plot_factory=bangalore_40x60, brief_factory=medium_brief):
    """Run C4 -> C5 -> C6 -> C7 -> C8. Returns (cdc_tuple, brief, grid, plot_analysis)."""
    plot = plot_factory()
    plot_analysis = make_plot_analysis(plot)
    brief = brief_factory()
    candidates = select_topology(plot_analysis, brief)
    oriented = prioritize_orientation(candidates, plot_analysis, VastuTier.PARTIAL)
    grid = GridGenerator().generate(
        envelope_width_m=plot_analysis.plot.width_m,
        envelope_depth_m=plot_analysis.plot.depth_m,
    )
    cdc = design_corridors(tuple(oriented), grid, plot_analysis)
    return cdc, brief, grid, plot_analysis


# ---------------------------------------------------------------------------
# Direct schema constructors for unit tests
# ---------------------------------------------------------------------------


def make_regulatory(
    *,
    area_m2: float = 9.5,
    width_m: float = 2.4,
    height_m: float = 2.75,
    nbc_clause: str = "NBC 2016 Part 3 Clause 12.1.1",
    source_confidence: NBCSourceConfidence = NBCSourceConfidence.SECONDARY_CONSENSUS,
) -> RegulatoryMinimum:
    return RegulatoryMinimum(
        area_m2=area_m2, width_m=width_m, height_m=height_m,
        nbc_clause=nbc_clause, source_confidence=source_confidence,
    )


def make_room(
    *,
    room_id: str = "BEDROOM_1",
    category: RoomCategory = RoomCategory.BEDROOM,
    is_master: bool = True,
    priority: int = 1,
    regulatory: RegulatoryMinimum | None = None,
    liveability_min_area_m2: float = 13.0,
    liveability_min_width_m: float = 3.3,
    target_m2: float = 14.9,
    max_m2: float = 23.8,
    bathroom_subtype: BathroomSubtype | None = None,
    other_subtype: str = "",
) -> RoomSizeRequirement:
    """Build a RoomSizeRequirement with sensible defaults (master bedroom).

    Caller can override any field. Defaults align with kb/room_targets.json's
    BEDROOM is_master=True row.
    """
    if regulatory is None:
        regulatory = make_regulatory()
    return RoomSizeRequirement(
        room_id=room_id,
        category=category,
        regulatory_minimum=regulatory,
        liveability_min_area_m2=liveability_min_area_m2,
        liveability_min_width_m=liveability_min_width_m,
        target_m2=target_m2,
        max_m2=max_m2,
        priority=priority,
        is_master=is_master,
        bathroom_subtype=bathroom_subtype,
        other_subtype=other_subtype,
    )


def make_provenance_stub(
    *,
    width_feasibility_per_room=None,
    grid_bay_feasibility_per_room=None,
    placement_risk_level=PlacementRiskLevel.LOW,
    placement_risk_score=0,
    unverified_nbc_rows_used=(),
) -> RoomSizingProvenance:
    """Stub provenance for tests that only need a single field."""
    if width_feasibility_per_room is None:
        width_feasibility_per_room = {}
    if grid_bay_feasibility_per_room is None:
        grid_bay_feasibility_per_room = {}
    return RoomSizingProvenance(
        derived_at=1.0,
        plot_analysis_trace_id="trace-test",
        floor_label="ground",
        nbc_table_version="NBC_test",
        furniture_kb_version="Furniture_test",
        targets_kb_version="Targets_test",
        dwelling_size_tier=DwellingSizeTier.LARGE,
        tier_resolution_accuracy=TierResolutionAccuracy.EXACT,
        assumed_total_dwelling_area_m2=None,
        grid_bay_min_m=3.0,
        grid_bay_max_m=4.0,
        wall_thickness_ratio_used=0.10,
        enforcement_mode="WARN",
        allocation_strategy="priority_greedy",
        surplus_distributed_m2=0.0,
        rooms_at_min=(),
        rooms_clamped_at_max=(),
        packing_basis="heuristic_v1_static_0.75",
        heuristic_packing_check_warning=False,
        width_feasibility_per_room=width_feasibility_per_room,
        grid_bay_feasibility_per_room=grid_bay_feasibility_per_room,
        placement_risk_level=placement_risk_level,
        placement_risk_score=placement_risk_score,
        unverified_nbc_rows_used=unverified_nbc_rows_used,
        other_sizing_behavior="n/a",
        rule_trace=(),
    )
