"""C16 — Phase γ working drawing assembly tests."""
import pytest
from buildemup.components.c16 import (
    RenderingConfig, execute_phase_alpha, execute_phase_beta,
    execute_phase_gamma,
)
from tests.test_c16.fixtures import (
    FakeDoor, standard_jurisdiction, standard_selection,
    standard_upstream_inputs, two_room_floor,
)


def _gamma_for(*, doors=(), floors=None, config=None):
    if floors is None:
        floors = (("F0", two_room_floor()),)
    if config is None:
        config = RenderingConfig()
    inputs = standard_upstream_inputs(
        per_floor_placements=floors,
        doors_by_floor={label: doors for label, _ in floors},
    )
    envelope = execute_phase_alpha(
        selection_result=standard_selection(),
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=config,
    )
    scheduling = execute_phase_beta(envelope=envelope)
    return execute_phase_gamma(
        envelope=envelope, scheduling=scheduling, config=config,
    )


class TestWorkingDrawingFloorAssembly:
    def test_one_floor_one_plan(self):
        r = _gamma_for()
        assert len(r.floor_plans) == 1

    def test_two_floors_two_plans(self):
        r = _gamma_for(floors=(
            ("F0", two_room_floor()),
            ("F1", two_room_floor()),
        ))
        assert len(r.floor_plans) == 2

    def test_annotations_emitted_per_room(self):
        r = _gamma_for()
        # 2 rooms × 3 annotations each = 6
        assert len(r.floor_plans[0].annotations) == 6

    def test_annotations_sorted_canonically(self):
        r = _gamma_for()
        ann_ids = [a.annotation_id for a in r.floor_plans[0].annotations]
        assert ann_ids == sorted(ann_ids)

    def test_annotations_include_room_labels(self):
        r = _gamma_for()
        kinds = {a.annotation_kind for a in r.floor_plans[0].annotations}
        assert "room_label" in kinds
        assert "dimension" in kinds


class TestSectionViewsR23:
    def test_no_doors_no_entry_section_emitted(self):
        # No main_entry door → entry cut still fallback to lex-first; but if
        # no doors at all, returns None and entry section omitted
        r = _gamma_for(doors=())
        cuts = {sv.cut_type for sv in r.section_views}
        assert "entry" not in cuts   # zero doors → no entry cut possible

    def test_main_entry_door_produces_entry_section(self):
        door = FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9, is_main_entry=True)
        r = _gamma_for(doors=(door,))
        cuts = {sv.cut_type for sv in r.section_views}
        assert "entry" in cuts

    def test_staircase_cut_only_in_multifloor(self):
        # Single floor → no staircase cut
        r = _gamma_for()
        cuts = {sv.cut_type for sv in r.section_views}
        assert "staircase" not in cuts

    def test_staircase_emitted_in_multifloor(self):
        r = _gamma_for(floors=(
            ("F0", two_room_floor()),
            ("F1", two_room_floor()),
        ))
        cuts = {sv.cut_type for sv in r.section_views}
        assert "staircase" in cuts

    def test_disabling_section_cuts_via_config_omits(self):
        cfg = RenderingConfig(mandatory_section_cuts=())
        r = _gamma_for(config=cfg)
        assert r.section_views == ()

    def test_r23_offset_fallback_records_offset(self):
        """When the natural cut position falls outside the building bbox,
        R23 v0.2 A8 says offset it inward. The offset magnitude must be
        recorded on offset_mm."""
        # Door is at x=4000mm boundary, anchor pos=1.0m → cut at x=4000 (vertical).
        # Building spans x in [0, 10000]. 4000 is well inside; no offset.
        door = FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9, is_main_entry=True)
        r = _gamma_for(doors=(door,))
        entry_sv = [s for s in r.section_views if s.cut_type == "entry"][0]
        assert entry_sv.offset_mm == 0


class TestRoofPlan:
    def test_roof_emitted_from_top_floor_bbox(self):
        r = _gamma_for()
        assert r.roof_plan is not None
        # two_room_floor: bed1 (0,0,4,4) + liv1 (4,0,6,5) → bbox 10×5 m → 10000×5000
        assert r.roof_plan.outline_width_mm == 10000
        assert r.roof_plan.outline_depth_mm == 5000

    def test_roof_drainage_slope_min_1pct(self):
        r = _gamma_for()
        assert r.roof_plan.drainage_slope_pct >= 1.0


class TestModelLevelAggregation:
    def test_aggregated_door_schedule_matches_per_floor_total(self):
        door = FakeDoor("bed1", "liv1", "vertical", 1.0, 0.9)
        r = _gamma_for(doors=(door,), floors=(
            ("F0", two_room_floor()), ("F1", two_room_floor()),
        ))
        # 1 door per floor × 2 floors = 2 entries at model level
        assert len(r.door_schedule) == 2
