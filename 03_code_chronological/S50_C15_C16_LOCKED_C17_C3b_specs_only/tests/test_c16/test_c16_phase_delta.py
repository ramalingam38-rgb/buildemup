"""C16 — Phase δ permit drawing assembly tests."""
from buildemup.components.c16 import (
    LegalCompleteness, RenderingConfig, execute_phase_alpha, execute_phase_delta,
)
from tests.test_c16.fixtures import (
    standard_config, standard_jurisdiction, standard_selection,
    standard_upstream_inputs, two_room_floor,
)


def _delta_for(*, floors=None, plot_area=216.0):
    if floors is None:
        floors = (("F0", two_room_floor()),)
    inputs = standard_upstream_inputs(
        per_floor_placements=floors,
        plot_area_sqm=plot_area,
    )
    envelope = execute_phase_alpha(
        selection_result=standard_selection(),
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=standard_config(),
    )
    permit = execute_phase_delta(
        envelope=envelope,
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=standard_config(),
    )
    return permit


class TestSitePlan:
    def test_site_plan_produced(self):
        p = _delta_for()
        assert p.site_plan is not None

    def test_plot_dims_derived_from_area(self):
        # 216 sqm with aspect 1.5 → w=√(216/1.5)=12, d=18
        p = _delta_for(plot_area=216.0)
        assert p.site_plan.plot_width_mm == 12000
        assert p.site_plan.plot_depth_mm == 18000

    def test_building_footprint_in_plot(self):
        p = _delta_for()
        bx, by, bw, bd = p.site_plan.building_footprint_xywh
        assert bx >= 0 and by >= 0
        assert bx + bw <= p.site_plan.plot_width_mm
        assert by + bd <= p.site_plan.plot_depth_mm

    def test_setback_annotations_four_sides(self):
        p = _delta_for()
        sides = {a.side for a in p.floor_plans[0].setback_annotations}
        assert sides == {"front", "rear", "left", "right"}


class TestFloorPlans:
    def test_one_per_floor(self):
        p = _delta_for(floors=(
            ("F0", two_room_floor()),
            ("F1", two_room_floor()),
        ))
        assert len(p.floor_plans) == 2

    def test_north_arrow_marker_present(self):
        p = _delta_for()
        kinds = {m.marker_kind for m in p.floor_plans[0].compliance_markers}
        assert "north_arrow" in kinds


class TestElevations:
    def test_four_cardinal_elevations(self):
        p = _delta_for()
        axes = {e.facade_axis for e in p.elevations}
        assert axes == {"north", "south", "east", "west"}

    def test_height_from_floor_count(self):
        p = _delta_for(floors=(
            ("F0", two_room_floor()),
            ("F1", two_room_floor()),
        ))
        # 2 floors × 3000mm typical = 6000mm total
        assert all(e.height_mm >= 3000 for e in p.elevations)


class TestKeyPlan:
    def test_emitted(self):
        p = _delta_for()
        assert p.key_plan is not None

    def test_floor_count_recorded(self):
        p = _delta_for(floors=(
            ("F0", two_room_floor()),
            ("F1", two_room_floor()),
            ("F2", two_room_floor()),
        ))
        assert p.key_plan.floor_count == 3


class TestPermitCriticalOverlays:
    def test_rwh_emitted_by_default(self):
        p = _delta_for()
        assert p.rwh_overlay is not None
        assert p.rwh_overlay.pit_count >= 1

    def test_sewage_emitted_by_default(self):
        p = _delta_for()
        assert p.sewage_layout is not None
        assert p.sewage_layout.sewage_treatment_capacity_l >= 1000

    def test_parking_emitted_by_default(self):
        p = _delta_for()
        assert p.parking_provision is not None
        assert p.parking_provision.bay_size_mm == (2500, 5000)


class TestLegalCompletenessIncompleteBeforeEpsilon:
    def test_delta_leaves_attestation_for_epsilon(self):
        p = _delta_for()
        # Phase δ alone cannot produce LEGALLY_COMPLETE without Phase ε
        # filling the ComplianceAttestation
        assert p.compliance_attestation is None
        assert p.legal_completeness == LegalCompleteness.LEGALLY_INCOMPLETE
        assert "far_and_coverage_attestation" in p.missing_overlays

    def test_signature_placeholder_present(self):
        p = _delta_for()
        assert p.signature_placeholder is not None
        assert p.requires_professional_signature is True
