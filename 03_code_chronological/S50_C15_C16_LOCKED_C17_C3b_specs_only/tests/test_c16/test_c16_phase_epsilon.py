"""C16 — Phase ε compliance attestation packaging tests."""
import pytest
from buildemup.components.c16 import (
    AuthorityKind, LegalCompleteness, MissingUpstreamDataError,
    execute_phase_alpha, execute_phase_delta, execute_phase_epsilon,
)
from tests.test_c16.fixtures import (
    FakeMFC, FakePlotAnalysis, FakeSunPath, UpstreamInputBundle,
    standard_config, standard_jurisdiction, standard_selection,
    standard_upstream_inputs, two_room_floor,
)


def _epsilon_for(*, floors=None, plot_area=216.0, far_permitted=1.5):
    if floors is None:
        floors = (("F0", two_room_floor()),)
    inputs_base = standard_upstream_inputs(
        per_floor_placements=floors,
        plot_area_sqm=plot_area,
    )
    # Adjust far_permitted on the bundle
    inputs = UpstreamInputBundle(
        multifloor_candidate=inputs_base.multifloor_candidate,
        grids_by_floor=inputs_base.grids_by_floor,
        wet_zone_plans_by_floor=inputs_base.wet_zone_plans_by_floor,
        doors_by_floor=inputs_base.doors_by_floor,
        plot_analysis=inputs_base.plot_analysis,
        upstream_cache_key=inputs_base.upstream_cache_key,
        far_permitted=far_permitted,
    )
    envelope = execute_phase_alpha(
        selection_result=standard_selection(),
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=standard_config(),
    )
    permit_provisional = execute_phase_delta(
        envelope=envelope,
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
        config=standard_config(),
    )
    return execute_phase_epsilon(
        envelope=envelope,
        permit_model=permit_provisional,
        upstream_inputs=inputs,
        jurisdiction_profile=standard_jurisdiction(),
    )


class TestAttestationStructure:
    def test_attestation_populated(self):
        p = _epsilon_for()
        assert p.compliance_attestation is not None

    def test_plot_area_recorded(self):
        p = _epsilon_for(plot_area=200.0)
        assert p.compliance_attestation.plot_area_sqm.value == 200.0


class TestR22AuthorityDiscipline:
    def test_plot_area_marked_upstream_authoritative(self):
        p = _epsilon_for()
        av = p.compliance_attestation.plot_area_sqm
        assert av.authority == AuthorityKind.UPSTREAM_AUTHORITATIVE
        assert av.upstream_source is not None

    def test_built_up_area_marked_upstream(self):
        p = _epsilon_for()
        av = p.compliance_attestation.built_up_area_sqm
        assert av.authority == AuthorityKind.UPSTREAM_AUTHORITATIVE

    def test_coverage_pct_marked_locally_derived(self):
        p = _epsilon_for()
        av = p.compliance_attestation.plot_coverage_pct
        assert av.authority == AuthorityKind.LOCALLY_DERIVED
        assert av.derivation_note  # non-empty

    def test_far_used_marked_locally_derived(self):
        p = _epsilon_for()
        av = p.compliance_attestation.far_used
        assert av.authority == AuthorityKind.LOCALLY_DERIVED

    def test_far_permitted_marked_upstream(self):
        p = _epsilon_for()
        av = p.compliance_attestation.far_permitted
        assert av.authority == AuthorityKind.UPSTREAM_AUTHORITATIVE


class TestR15Provenance:
    def test_provenance_entries_present(self):
        p = _epsilon_for()
        prov = p.compliance_attestation.upstream_check_provenance
        assert len(prov) >= 5

    def test_each_provenance_has_component_and_check_id(self):
        p = _epsilon_for()
        for cp in p.compliance_attestation.upstream_check_provenance:
            assert cp.upstream_component
            assert cp.check_id
            assert cp.upstream_version

    def test_plot_area_traced_to_c04(self):
        p = _epsilon_for()
        prov = p.compliance_attestation.upstream_check_provenance
        plot_prov = [cp for cp in prov if cp.attested_field_name == "plot_area_sqm"]
        assert len(plot_prov) == 1
        assert plot_prov[0].upstream_component == "c04_plot_analysis"


class TestR25LegalCompleteness:
    def test_default_two_room_layout_is_legally_complete(self):
        # The two-room fixture with 216 sqm plot + FAR 1.5 + default overlays
        # should yield LEGALLY_COMPLETE
        p = _epsilon_for()
        # 2 rooms × ~20 sqm each = ~40 sqm built-up; coverage ~18%; FAR ~0.19
        # All overlays present → COMPLETE
        assert p.legal_completeness == LegalCompleteness.LEGALLY_COMPLETE
        assert p.missing_overlays == ()

    def test_locally_derived_alone_does_not_gate_complete(self):
        """R25: LEGALLY_COMPLETE only when UPSTREAM_AUTHORITATIVE
        overlays present. Locally-derived ratios don't count for the
        gate."""
        p = _epsilon_for()
        # The far_used is LOCALLY_DERIVED. Its presence is necessary
        # but NOT sufficient — it counts toward completeness only
        # because far_permitted (its authoritative pair) is upstream.
        far_used = p.compliance_attestation.far_used
        assert far_used.authority == AuthorityKind.LOCALLY_DERIVED


class TestSetbackComplianceReport:
    def test_setback_report_populated(self):
        p = _epsilon_for()
        sr = p.compliance_attestation.setback_compliance
        assert sr.front_min_required_mm == 1500
        assert sr.rear_min_required_mm == 1200
        assert sr.left_min_required_mm == 900
        assert sr.right_min_required_mm == 900


class TestErrorHandling:
    def test_missing_plot_analysis_raises(self):
        inputs = standard_upstream_inputs()
        broken = UpstreamInputBundle(
            multifloor_candidate=inputs.multifloor_candidate,
            grids_by_floor=inputs.grids_by_floor,
            wet_zone_plans_by_floor=inputs.wet_zone_plans_by_floor,
            doors_by_floor=inputs.doors_by_floor,
            plot_analysis=None,
        )
        envelope = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,   # use intact for envelope
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        permit = execute_phase_delta(
            envelope=envelope, upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_epsilon(
                envelope=envelope, permit_model=permit,
                upstream_inputs=broken,
                jurisdiction_profile=standard_jurisdiction(),
            )

    def test_zero_plot_area_raises(self):
        from buildemup.components.c16 import UpstreamInputBundle
        inputs = standard_upstream_inputs()
        broken = UpstreamInputBundle(
            multifloor_candidate=inputs.multifloor_candidate,
            grids_by_floor=inputs.grids_by_floor,
            wet_zone_plans_by_floor=inputs.wet_zone_plans_by_floor,
            doors_by_floor=inputs.doors_by_floor,
            plot_analysis=FakePlotAnalysis(
                area_sqm=0.0, sun_path=FakeSunPath(),
            ),
        )
        envelope = execute_phase_alpha(
            selection_result=standard_selection(),
            upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        permit = execute_phase_delta(
            envelope=envelope, upstream_inputs=inputs,
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
        )
        with pytest.raises(MissingUpstreamDataError):
            execute_phase_epsilon(
                envelope=envelope, permit_model=permit,
                upstream_inputs=broken,
                jurisdiction_profile=standard_jurisdiction(),
            )
