"""C16 — orchestrator tests covering STRICT/WARN routing + batch + LocalDrawingError."""
import pytest
from buildemup.components.c16 import (
    FailedDrawingRender, MissingUpstreamDataError, OrientationLock,
    OrientationLockMismatchError, RenderingConfig, SuccessfulDrawingRender,
    JurisdictionProfile, UpstreamInputBundle,
    render_drawings, render_drawings_batch,
)
from tests.test_c16.fixtures import (
    FakeMFC, standard_config, standard_jurisdiction, standard_selection,
    standard_upstream_inputs, two_room_floor,
)


def _strict_render(*, inputs=None, jp=None, cfg=None, strict=True):
    if inputs is None:
        inputs = standard_upstream_inputs()
    if jp is None:
        jp = standard_jurisdiction()
    if cfg is None:
        cfg = standard_config()
    return render_drawings(
        selection_result=standard_selection(),
        upstream_inputs=inputs,
        jurisdiction_profile=jp,
        config=cfg,
        strict_mode=strict,
    )


class TestSuccessfulRender:
    def test_happy_path_returns_successful(self):
        r = _strict_render()
        assert isinstance(r, SuccessfulDrawingRender)

    def test_bundle_well_formed(self):
        r = _strict_render()
        b = r.bundle
        assert b.canonical_replay_signature
        assert b.presentation_signature
        assert len(b.floor_geometries) == 1


class TestStrictMode:
    def test_strict_raises_on_per_layout_error(self):
        # Empty MFC → MissingUpstreamDataError (per-layout)
        inputs = standard_upstream_inputs()
        broken = UpstreamInputBundle(
            multifloor_candidate=FakeMFC("sig", ()),
            grids_by_floor={}, wet_zone_plans_by_floor={},
            doors_by_floor={}, plot_analysis=inputs.plot_analysis,
        )
        with pytest.raises(MissingUpstreamDataError):
            _strict_render(inputs=broken, strict=True)

    def test_warn_collects_failure(self):
        inputs = standard_upstream_inputs()
        broken = UpstreamInputBundle(
            multifloor_candidate=FakeMFC("sig", ()),
            grids_by_floor={}, wet_zone_plans_by_floor={},
            doors_by_floor={}, plot_analysis=inputs.plot_analysis,
        )
        r = _strict_render(inputs=broken, strict=False)
        assert isinstance(r, FailedDrawingRender)
        assert r.failure_record.phase == "alpha"
        assert "per_floor_placements" in r.failure_record.error_message


class TestLocalDrawingErrorAlwaysHalts:
    def test_orientation_lock_mismatch_raises_in_strict(self):
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=73.0,  # nowhere near any candidate
                locked_origin_basis="longest_wall",
                lock_provenance="test",
            ),
        )
        with pytest.raises(OrientationLockMismatchError):
            _strict_render(jp=jp, strict=True)

    def test_orientation_lock_mismatch_also_raises_in_warn(self):
        """LocalDrawingError must halt REGARDLESS of strict_mode."""
        jp = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
            orientation_lock=OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=73.0,
                locked_origin_basis="longest_wall",
                lock_provenance="test",
            ),
        )
        # Even with strict=False, this still raises
        with pytest.raises(OrientationLockMismatchError):
            _strict_render(jp=jp, strict=False)


class TestBatchRender:
    def test_batch_with_two_success(self):
        sr = standard_selection()
        ub = standard_upstream_inputs()
        result = render_drawings_batch(
            selection_results=(sr, sr),
            upstream_inputs_per=(ub, ub),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
            strict_mode=False,
        )
        assert len(result.successes) == 2
        assert len(result.failures) == 0

    def test_batch_mismatched_inputs_raises(self):
        sr = standard_selection()
        ub = standard_upstream_inputs()
        with pytest.raises(ValueError):
            render_drawings_batch(
                selection_results=(sr, sr),
                upstream_inputs_per=(ub,),  # length mismatch
                jurisdiction_profile=standard_jurisdiction(),
                config=standard_config(),
            )

    def test_batch_with_one_failure_warn_mode(self):
        sr = standard_selection()
        ub_ok = standard_upstream_inputs()
        ub_bad = UpstreamInputBundle(
            multifloor_candidate=FakeMFC("sig", ()),
            grids_by_floor={}, wet_zone_plans_by_floor={},
            doors_by_floor={}, plot_analysis=ub_ok.plot_analysis,
        )
        result = render_drawings_batch(
            selection_results=(sr, sr),
            upstream_inputs_per=(ub_ok, ub_bad),
            jurisdiction_profile=standard_jurisdiction(),
            config=standard_config(),
            strict_mode=False,
        )
        assert len(result.successes) == 1
        assert len(result.failures) == 1


class TestTimingsAndDiagnosticsCapture:
    def test_default_no_capture(self):
        r = _strict_render()
        assert isinstance(r, SuccessfulDrawingRender)
        # By default, capture_phase_timings=False → no timings on bundle
        assert r.bundle.phase_timings is None

    def test_capture_timings_enabled(self):
        cfg = RenderingConfig(capture_phase_timings=True)
        r = _strict_render(cfg=cfg)
        assert r.bundle.phase_timings is not None
        # alpha + beta + gamma + delta + epsilon at least add up
        assert r.bundle.phase_timings.total_ms >= 0

    def test_capture_readability_enabled(self):
        cfg = RenderingConfig(capture_readability_diagnostics=True)
        r = _strict_render(cfg=cfg)
        assert r.bundle.readability_diagnostics is not None


class TestSignatureStability:
    def test_two_renders_produce_byte_equal_canonical(self):
        r1 = _strict_render()
        r2 = _strict_render()
        assert r1.bundle.canonical_replay_signature == r2.bundle.canonical_replay_signature

    def test_timings_do_not_affect_canonical_signature(self):
        cfg_no = RenderingConfig(capture_phase_timings=False)
        cfg_yes = RenderingConfig(capture_phase_timings=True)
        r_no = _strict_render(cfg=cfg_no)
        r_yes = _strict_render(cfg=cfg_yes)
        # Canonical must be identical (R7d — time excluded)
        assert r_no.bundle.canonical_replay_signature == r_yes.bundle.canonical_replay_signature
