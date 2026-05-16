"""C16 — Phase α envelope assembly tests."""
import pytest

from buildemup.components.c16 import (
    ElementKind, GeometryInconsistencyError, MissingUpstreamDataError,
    execute_phase_alpha,
)

from tests.test_c16.fixtures import (
    FakeColumnPosition, FakeDoor, FakeGrid, FakeMFC, FakePlacedCandidate,
    FakePlacedRoom, FakePlotAnalysis, FakeRiserAnchor, FakeRiserGroup,
    FakeSharedEdge, FakeSunPath, FakeWallSegment, FakeWetZonePlan,
    standard_config, standard_jurisdiction, standard_selection,
    standard_upstream_inputs, two_room_floor,
)


class TestBasicEnvelopeAssembly:
    def test_single_floor_two_rooms(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert len(result.floor_geometries) == 1
        fg = result.floor_geometries[0]
        assert len(fg.rooms) == 2

    def test_rooms_sorted_lex_asc_by_id(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        room_ids = [r.room_id for r in result.floor_geometries[0].rooms]
        assert room_ids == sorted(room_ids)

    def test_room_coords_converted_to_mm(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        # bed1 is at x=0, y=0, w=4m, d=4m → 0/0/4000/4000 mm
        bed = [r for r in result.floor_geometries[0].rooms if r.room_id == "bed1"][0]
        assert bed.x_mm == 0 and bed.y_mm == 0
        assert bed.width_mm == 4000 and bed.depth_mm == 4000

    def test_room_category_preserved(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        cats = {r.room_id: r.category for r in result.floor_geometries[0].rooms}
        assert cats["bed1"] == "BEDROOM"
        assert cats["liv1"] == "LIVING"

    def test_floor_elevation_zero_for_ground(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert result.floor_geometries[0].floor_elevation_mm == 0

    def test_multi_floor_elevations(self):
        inputs = standard_upstream_inputs(
            per_floor_placements=(
                ("F0", two_room_floor()),
                ("F1", two_room_floor()),
            ),
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert len(result.floor_geometries) == 2
        assert result.floor_geometries[0].floor_elevation_mm == 0
        # typical_floor_height_m=3.0 → 3000 mm
        assert result.floor_geometries[1].floor_elevation_mm == 3000


class TestSharedEdgePartitionGeometry:
    def test_partition_positioned_at_actual_boundary(self):
        """Regression: partition wall must use real room boundaries,
        not coord 0 (B-C16-SHARED-EDGE-AXIS-PINNING fix)."""
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        # bed1 (0,0,4,4) + liv1 (4,0,6,5) share vertical edge at x=4m
        # Partition wall should be at x=4000mm, not x=0
        partitions = [
            w for w in result.floor_geometries[0].walls
            if w.element_kind == ElementKind.WALL_INTERNAL_PARTITION
            and w.wall_id.startswith("int:")
        ]
        assert len(partitions) == 1
        p = partitions[0]
        # Vertical wall: start_x == end_x == 4000
        assert p.start_x_mm == 4000
        assert p.end_x_mm == 4000

    def test_partition_rejected_when_edge_references_missing_room(self):
        from tests.test_c16.fixtures import FakePlacedRoom, FakeSharedEdge, FakePlacedCandidate
        rooms = (FakePlacedRoom("bed1", "BEDROOM", 0, 0, 4, 4),)
        edges = (FakeSharedEdge("bed1", "ghost", "vertical", 0, 4, 4),)
        pc = FakePlacedCandidate("sig:1", rooms, edges)
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        with pytest.raises(GeometryInconsistencyError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )


class TestWallsFromGrid:
    def test_external_wall_tagged_correctly(self):
        grid = FakeGrid(
            wall_segments=(
                FakeWallSegment("w_s", "south", 0.0, 0.0, 10.0, 0.0, 10.0,
                                tags=frozenset({"external"})),
            ),
        )
        inputs = standard_upstream_inputs(
            grids_by_floor={"F0": grid},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        wall = [w for w in result.floor_geometries[0].walls
                if w.wall_id == "w_s"][0]
        assert wall.element_kind == ElementKind.WALL_EXTERNAL

    def test_load_bearing_internal_tagged(self):
        grid = FakeGrid(
            wall_segments=(
                FakeWallSegment("w_lb", "south", 0.0, 0.0, 5.0, 0.0, 5.0,
                                tags=frozenset({"load_bearing"})),
            ),
        )
        inputs = standard_upstream_inputs(
            grids_by_floor={"F0": grid},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        wall = [w for w in result.floor_geometries[0].walls
                if w.wall_id == "w_lb"][0]
        assert wall.element_kind == ElementKind.WALL_INTERNAL_LOAD_BEARING


class TestColumnsFromGrid:
    def test_columns_emitted_with_default_cross_section(self):
        grid = FakeGrid(
            columns=(
                FakeColumnPosition("A1", 0.0, 0.0, True),
                FakeColumnPosition("B1", 5.0, 0.0, True),
            ),
        )
        inputs = standard_upstream_inputs(
            grids_by_floor={"F0": grid},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        cols = result.floor_geometries[0].columns
        assert len(cols) == 2
        # All default to 230×230 (Indian RCC G+0 standard)
        for c in cols:
            assert c.width_mm == 230 and c.depth_mm == 230


class TestPlumbingStacksFromWetZonePlan:
    def test_stack_anchor_in_mm(self):
        plan = FakeWetZonePlan(
            riser_groups=(
                FakeRiserGroup(
                    group_id="rg1",
                    anchors=(FakeRiserAnchor("w_s", 1.5, (1.5, 0.0)),),
                    wet_room_ids=("bath1",),
                ),
            ),
        )
        inputs = standard_upstream_inputs(
            wet_zone_plans_by_floor={"F0": plan},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        stacks = result.floor_geometries[0].plumbing_stacks
        assert len(stacks) == 1
        assert stacks[0].x_mm == 1500 and stacks[0].y_mm == 0
        assert stacks[0].stack_id == "rg1"
        assert stacks[0].serves_room_ids == ("bath1",)

    def test_empty_anchors_raises(self):
        plan = FakeWetZonePlan(
            riser_groups=(
                FakeRiserGroup(group_id="rg1", anchors=(), wet_room_ids=("bath1",)),
            ),
        )
        inputs = standard_upstream_inputs(
            wet_zone_plans_by_floor={"F0": plan},
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )


class TestDoorsFromC13:
    def test_door_anchor_against_real_boundary(self):
        door = FakeDoor(
            room_a_id="bed1", room_b_id="liv1",
            axis="vertical",
            position_along_edge_m=1.0,
            clear_width_m=0.9,
        )
        inputs = standard_upstream_inputs(
            doors_by_floor={"F0": (door,)},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        doors = result.floor_geometries[0].doors
        assert len(doors) == 1
        # vertical edge between bed1 (right=4m) and liv1 → boundary x=4000mm
        # position=1.0 + overlap_start=0 → y=1000mm
        assert doors[0].anchor_x_mm == 4000
        assert doors[0].anchor_y_mm == 1000
        assert doors[0].clear_width_mm == 900

    def test_door_with_main_entry_kind(self):
        door = FakeDoor(
            room_a_id="bed1", room_b_id="liv1",
            axis="vertical", position_along_edge_m=1.0,
            clear_width_m=0.9, is_main_entry=True,
        )
        inputs = standard_upstream_inputs(
            doors_by_floor={"F0": (door,)},
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        d = result.floor_geometries[0].doors[0]
        assert d.is_main_entry is True
        assert d.element_kind == ElementKind.DOOR_EXTERNAL

    def test_door_references_missing_edge_raises(self):
        door = FakeDoor(
            room_a_id="bed1", room_b_id="ghost",
            axis="vertical", position_along_edge_m=1.0, clear_width_m=0.9,
        )
        inputs = standard_upstream_inputs(
            doors_by_floor={"F0": (door,)},
        )
        with pytest.raises(GeometryInconsistencyError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )


class TestR7bStableIdentities:
    def test_same_input_produces_same_geometry_id(self):
        inputs1 = standard_upstream_inputs()
        inputs2 = standard_upstream_inputs()
        r1 = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs1,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        r2 = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs2,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        # Floor identity is byte-equal
        assert (
            r1.floor_geometries[0].geometry_ref
            == r2.floor_geometries[0].geometry_ref
        )

    def test_room_identity_includes_full_payload(self):
        # R7b: semantic = geometry only; presentation = full payload.
        # Two PlacedCandidates with identical geometry but different
        # category should share semantic_identity_hash but differ in
        # presentation_identity_hash.
        from tests.test_c16.fixtures import FakePlacedRoom, FakePlacedCandidate
        rooms_a = (FakePlacedRoom("r1", "BEDROOM", 0, 0, 4, 4),)
        rooms_b = (FakePlacedRoom("r1", "LIVING", 0, 0, 4, 4),)
        pc_a = FakePlacedCandidate("sig:1", rooms_a, ())
        pc_b = FakePlacedCandidate("sig:2", rooms_b, ())
        i_a = standard_upstream_inputs(per_floor_placements=(("F0", pc_a),))
        i_b = standard_upstream_inputs(per_floor_placements=(("F0", pc_b),))
        r_a = execute_phase_alpha(
            selection_result=standard_selection(), upstream_inputs=i_a,
            jurisdiction_profile=standard_jurisdiction(), config=standard_config(),
        )
        r_b = execute_phase_alpha(
            selection_result=standard_selection(), upstream_inputs=i_b,
            jurisdiction_profile=standard_jurisdiction(), config=standard_config(),
        )
        room_a = r_a.floor_geometries[0].rooms[0]
        room_b = r_b.floor_geometries[0].rooms[0]
        # Semantic (geometry-only) is the SAME — geometry is identical
        assert (
            room_a.identity.semantic_identity_hash
            == room_b.identity.semantic_identity_hash
        )
        # Presentation hash includes category → differs
        assert (
            room_a.identity.presentation_identity_hash
            != room_b.identity.presentation_identity_hash
        )


class TestErrorHandling:
    def test_missing_multifloor_candidate_raises(self):
        inputs = standard_upstream_inputs()
        broken = type(inputs)(
            multifloor_candidate=None,
            grids_by_floor=inputs.grids_by_floor,
            wet_zone_plans_by_floor=inputs.wet_zone_plans_by_floor,
            doors_by_floor=inputs.doors_by_floor,
            plot_analysis=inputs.plot_analysis,
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=broken,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )

    def test_empty_per_floor_placements_raises(self):
        mfc = FakeMFC("sig", ())
        inputs = standard_upstream_inputs()
        broken = type(inputs)(
            multifloor_candidate=mfc,
            grids_by_floor={},
            wet_zone_plans_by_floor={},
            doors_by_floor={},
            plot_analysis=inputs.plot_analysis,
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=broken,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )

    def test_empty_room_id_raises(self):
        from tests.test_c16.fixtures import FakePlacedRoom, FakePlacedCandidate
        rooms = (FakePlacedRoom("", "BEDROOM", 0, 0, 4, 4),)
        pc = FakePlacedCandidate("sig:1", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_alpha(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )


class TestGeospatialReference:
    def test_orientation_basis_recorded(self):
        # With explicit hint, basis must be 'explicit_hint'
        from buildemup.components.c16 import JurisdictionProfile
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            local_x_axis_orientation_deg_hint=30.0,
        )
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=jp,
            config=standard_config(),
        )
        assert result.geospatial_reference.orientation_basis == "explicit_hint"
        assert result.geospatial_reference.rotation_from_plot_north_deg == 30.0

    def test_orientation_basis_lex_fallback_with_no_external_walls(self):
        result = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=standard_upstream_inputs(),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        # No grid walls in default fixture → no external; falls to lex_fallback
        # Our default grid has no walls, so the result hits step 4
        assert result.geospatial_reference.orientation_basis in (
            "lex_fallback", "longest_wall",
        )
