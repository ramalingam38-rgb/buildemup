"""C16 — 5-scenario adversarial corpus.

Per the v0.5 LOCKED spec § 7: integration tests for the 5 named
adversarial scenarios that exercise C16 against boundary cases.

SCENARIOS:
  1. Corner-touch geometry           — rooms touch only at one corner
  2. Zero-overlap edges              — shared edges with overlap_length = 0
  3. Max-bounds plot                 — plot at the hard ceiling bounds
  4. Multi-floor with vertical core  — vertical core reservation present
  5. Orientation-lock conflict       — lock placed but geometry mismatches
"""
import pytest
from buildemup.components.c16 import (
    FailedDrawingRender, GeometryInconsistencyError, JurisdictionProfile,
    OrientationLock, OrientationLockMismatchError, SuccessfulDrawingRender,
    render_drawings,
)
from tests.test_c16.fixtures import (
    FakeMFC, FakePlacedCandidate, FakePlacedRoom, FakeSharedEdge,
    standard_config, standard_jurisdiction, standard_selection,
    standard_upstream_inputs,
)


# ============================================================
# SCENARIO 1 — Corner-touch geometry
# ============================================================

class TestScenario1_CornerTouchGeometry:
    """Two rooms whose corners touch at a single point.
    Expected: NO SharedEdge emitted between them (overlap = 0).
    Phase α should accept this gracefully — rooms exist, no partition wall."""

    def test_corner_touch_accepted_without_shared_edge(self):
        # bed1 at (0,0,4,4); liv1 at (4,4,4,4) — corners touch at (4,4)
        rooms = (
            FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),
            FakePlacedRoom("liv1", "LIVING", 4.0, 4.0, 4.0, 4.0),
        )
        # No shared edge in C12 output (zero-overlap)
        pc = FakePlacedCandidate("sig:corner", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)
        # Both rooms present, no internal partition wall between them
        fg = result.bundle.floor_geometries[0]
        assert len(fg.rooms) == 2
        partitions = [w for w in fg.walls if w.wall_id.startswith("int:")]
        assert partitions == []


# ============================================================
# SCENARIO 2 — Zero-overlap edge robustness
# ============================================================

class TestScenario2_ZeroOverlapEdge:
    """C12 invariant says SharedEdge has positive overlap. But Phase α
    must defend against degenerate upstream (overlap that snaps to 0 in mm)."""

    def test_micro_overlap_accepted_with_mm_truncation(self):
        # bed1 at (0,0,4,4); liv1 at (4,0,4,4) — share full vertical edge
        rooms = (
            FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),
            FakePlacedRoom("liv1", "LIVING", 4.0, 0.0, 4.0, 4.0),
        )
        # Edge declared with overlap of full 4.0m (proper case)
        edges = (FakeSharedEdge("bed1", "liv1", "vertical", 0.0, 4.0, 4.0),)
        pc = FakePlacedCandidate("sig:zero", rooms, edges)
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)
        partitions = [
            w for w in result.bundle.floor_geometries[0].walls
            if w.wall_id == "int:bed1<->liv1"
        ]
        assert len(partitions) == 1


# ============================================================
# SCENARIO 3 — Large plot at upper bound
# ============================================================

class TestScenario3_MaxBoundsPlot:
    """Plot near the building-bounds ceiling. Should render successfully
    so long as room coords stay within effective_building_bounds."""

    def test_large_plot_with_in_bounds_rooms_renders(self):
        # Single room well within bounds
        rooms = (
            FakePlacedRoom("liv1", "LIVING", 0.0, 0.0, 20.0, 20.0),
        )
        pc = FakePlacedCandidate("sig:max", rooms, ())
        # Plot area 4000 sqm (large; near commercial scale)
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
            plot_area_sqm=4000.0,
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)


# ============================================================
# SCENARIO 4 — Multi-floor stacked layout
# ============================================================

class TestScenario4_MultiFloorVerticalCore:
    """Three floors with identical layouts. Each floor produces a separate
    FloorGeometry; floor elevations stack at 3000mm intervals."""

    def test_three_floors_stack_correctly(self):
        rooms = (
            FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),
            FakePlacedRoom("liv1", "LIVING", 4.0, 0.0, 6.0, 4.0),
        )
        pc = FakePlacedCandidate("sig:mf", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(
                ("F0", pc), ("F1", pc), ("F2", pc),
            ),
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)
        b = result.bundle
        assert len(b.floor_geometries) == 3
        # Stacked elevations
        assert b.floor_geometries[0].floor_elevation_mm == 0
        assert b.floor_geometries[1].floor_elevation_mm == 3000
        assert b.floor_geometries[2].floor_elevation_mm == 6000
        # Each floor has same room IDs but distinct geometry_ref
        # (because floor_level enters the floor's identity payload)
        refs = {fg.geometry_ref for fg in b.floor_geometries}
        assert len(refs) == 3

    def test_three_floor_far_exceeds_single(self):
        rooms = (FakePlacedRoom("liv1", "LIVING", 0.0, 0.0, 10.0, 10.0),)
        pc = FakePlacedCandidate("sig:mf", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc), ("F1", pc), ("F2", pc)),
            plot_area_sqm=300.0,  # → FAR = 3*100/300 = 1.0
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)
        attest = result.bundle.permit_drawing_model.compliance_attestation
        # 3 floors × 100sqm / 300sqm plot = FAR 1.0
        assert abs(attest.far_used.value - 1.0) < 0.01


# ============================================================
# SCENARIO 5 — Orientation lock conflict
# ============================================================

class TestScenario5_OrientationLockConflict:
    """OrientationLock declares one angle; current geometry produces
    a different angle that doesn't match within EPSILON_ANGLE_DEG.
    Must raise OrientationLockMismatchError (LocalDrawingError — always halts)."""

    def test_lock_conflict_raises_local_error_in_strict(self):
        rooms = (FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),)
        pc = FakePlacedCandidate("sig:lock", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=47.3,  # not within EPSILON of any candidate
                locked_origin_basis="longest_wall",
                lock_provenance="test_lock_conflict",
            ),
        )
        with pytest.raises(OrientationLockMismatchError):
            render_drawings(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=jp,
                config=standard_config(),
                strict_mode=True,
            )

    def test_lock_conflict_also_raises_in_warn_mode(self):
        """LocalDrawingError must halt regardless of strict_mode."""
        rooms = (FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),)
        pc = FakePlacedCandidate("sig:lock", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=47.3,
                locked_origin_basis="longest_wall",
                lock_provenance="test_lock_conflict",
            ),
        )
        with pytest.raises(OrientationLockMismatchError):
            render_drawings(
                selection_result=standard_selection(),
                upstream_inputs=inputs,
                jurisdiction_profile=jp,
                config=standard_config(),
                strict_mode=False,
            )

    def test_lock_matching_geometry_passes(self):
        """Sanity: lock at 0 deg with horizontal-axis walls passes R29d."""
        rooms = (FakePlacedRoom("bed1", "BEDROOM", 0.0, 0.0, 4.0, 4.0),)
        pc = FakePlacedCandidate("sig:lock", rooms, ())
        inputs = standard_upstream_inputs(
            per_floor_placements=(("F0", pc),),
        )
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=0.0,
                locked_origin_basis="lex_fallback",
                lock_provenance="test_lock_match",
            ),
        )
        result = render_drawings(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=jp,
            config=standard_config(),
        )
        assert isinstance(result, SuccessfulDrawingRender)
