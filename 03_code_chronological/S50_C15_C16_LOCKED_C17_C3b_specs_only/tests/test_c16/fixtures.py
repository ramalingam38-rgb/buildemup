"""Shared duck-typed upstream stand-ins for C16 phase tests.

Production passes real C7/C9/C10/C12/C13/C14/C4 instances; these
fixtures mirror the exact attribute names Phase α reads via getattr.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from buildemup.components.c16 import (
    JurisdictionProfile, RenderingConfig, SelectionAuditMetadata,
    SelectionReason, SelectionReplayIdentity, SelectionResult,
    UpstreamInputBundle,
)


# ────────────── C12 stand-ins ──────────────
@dataclass(frozen=True)
class FakePlacedRoom:
    room_id: str
    category: str
    x_m: float
    y_m: float
    width_m: float
    depth_m: float


@dataclass(frozen=True)
class FakeSharedEdge:
    room_a_id: str
    room_b_id: str
    axis: str
    overlap_start_m: float
    overlap_end_m: float
    overlap_length_m: float
    min_required_clear_width_m: float = 0.9
    doorway_feasible: bool = True


@dataclass(frozen=True)
class FakePlacedCandidate:
    source_refined_candidate_signature: str
    placed_rooms: tuple
    shared_edges: tuple
    placement_algorithm: str = "slicing_kd_tree"
    envelope_width_m: float = 10.0
    envelope_depth_m: float = 12.0


@dataclass(frozen=True)
class FakeMFC:
    source_multifloor_candidate_signature: str
    per_floor_placements: tuple
    alignment_report: object = None
    vertical_cores_reserved: tuple = ()


# ────────────── C7 stand-ins ──────────────
@dataclass(frozen=True)
class FakeColumnPosition:
    grid_label: str
    x_m: float
    y_m: float
    on_perimeter: bool


@dataclass(frozen=True)
class FakeWallSegment:
    """Duck-typed C7.WallSegment. Production uses WallAxis enum + WallTag
    frozenset; we accept string-equivalent tags ('external', 'internal',
    'load_bearing') which Phase α's tag_strs frozenset construction
    handles transparently."""
    wall_id: str
    axis: object   # WallAxis or str
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    length_m: float
    tags: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class FakeGrid:
    columns: tuple = ()
    wall_segments: tuple = ()
    envelope_width_m: float = 10.0
    envelope_depth_m: float = 12.0


# ────────────── C10 stand-ins ──────────────
@dataclass(frozen=True)
class FakeRiserAnchor:
    wall_id: str
    anchor_position_m: float
    riser_anchor_xy: tuple
    column_id: object = None
    snap_distance_m: object = None


@dataclass(frozen=True)
class FakeRiserGroup:
    group_id: str
    anchors: tuple
    wet_room_ids: tuple


@dataclass(frozen=True)
class FakeWetZonePlan:
    riser_groups: tuple = ()
    total_wet_run_length_m: float = 0.0


# ────────────── C13 stand-in ──────────────
@dataclass(frozen=True)
class FakeDoor:
    room_a_id: str
    room_b_id: str
    axis: str
    position_along_edge_m: float
    clear_width_m: float
    swing_direction: str = "into_room_a"
    hinge_side: str = "start"
    leaf_thickness_m: float = 0.045
    is_main_entry: bool = False


# ────────────── C4 stand-ins ──────────────
@dataclass(frozen=True)
class FakeSunPath:
    true_north_deg: float = 0.0


@dataclass(frozen=True)
class FakePlotAnalysis:
    trace_id: str = "test"
    area_sqm: float = 216.0
    aspect_ratio: float = 1.5
    sun_path: object = None


# ────────────── Convenience builders ──────────────
def two_room_floor() -> FakePlacedCandidate:
    """Simple 2-room floor: bedroom (4x4) adjacent to living (6x5),
    sharing a vertical edge at x=4."""
    rooms = (
        FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),
        FakePlacedRoom("liv1", "LIVING", 4.0, 0.0, 6.0, 5.0),
    )
    edges = (FakeSharedEdge("bed1", "liv1", "vertical", 0.0, 4.0, 4.0),)
    return FakePlacedCandidate("sig:1", rooms, edges)


def standard_jurisdiction() -> JurisdictionProfile:
    return JurisdictionProfile(
        jurisdiction_id="tn_cdbr_2019",
        declared_domain_scope="residential_v1",
    )


def standard_config() -> RenderingConfig:
    return RenderingConfig()


def standard_selection() -> SelectionResult:
    return SelectionResult(
        replay_identity=SelectionReplayIdentity(
            selected_layout_signature="lay:1",
            selector_version="v1.0",
            selection_reason=SelectionReason.RANKER_TOP,
            candidate_ranking_snapshot=(),
            upstream_problem_reports=(),
        ),
        audit_metadata=SelectionAuditMetadata(
            selection_timestamp_utc="2026-05-15T00:00:00Z",
            human_override=None,
            selector_instance_id=None,
            selection_machine_fingerprint=None,
        ),
    )


def standard_upstream_inputs(
    *,
    per_floor_placements: tuple = None,
    grids_by_floor: dict = None,
    wet_zone_plans_by_floor: dict = None,
    doors_by_floor: dict = None,
    plot_area_sqm: float = 216.0,
) -> UpstreamInputBundle:
    if per_floor_placements is None:
        per_floor_placements = (("F0", two_room_floor()),)
    if grids_by_floor is None:
        grids_by_floor = {label: FakeGrid() for label, _ in per_floor_placements}
    if wet_zone_plans_by_floor is None:
        wet_zone_plans_by_floor = {}
    if doors_by_floor is None:
        doors_by_floor = {label: () for label, _ in per_floor_placements}
    mfc = FakeMFC("mfsig:1", per_floor_placements)
    return UpstreamInputBundle(
        multifloor_candidate=mfc,
        grids_by_floor=grids_by_floor,
        wet_zone_plans_by_floor=wet_zone_plans_by_floor,
        doors_by_floor=doors_by_floor,
        plot_analysis=FakePlotAnalysis(
            area_sqm=plot_area_sqm,
            sun_path=FakeSunPath(),
        ),
        upstream_cache_key="a" * 64,
    )
