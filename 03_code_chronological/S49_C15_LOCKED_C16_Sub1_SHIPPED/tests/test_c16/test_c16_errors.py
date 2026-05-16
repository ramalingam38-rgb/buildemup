"""C16 Sub-1 — error hierarchy tests."""
from __future__ import annotations

import pytest

from buildemup.components.c16 import errors as e


# ============================================================
# Hierarchy structure (two-tier)
# ============================================================

class TestErrorHierarchyShape:
    def test_root_is_exception(self):
        assert issubclass(e.DrawingRenderError, Exception)

    def test_local_tier_descends_from_root(self):
        assert issubclass(e.LocalDrawingError, e.DrawingRenderError)

    def test_perlayout_tier_descends_from_root(self):
        assert issubclass(e.PerLayoutDrawingError, e.DrawingRenderError)

    def test_two_tiers_are_disjoint(self):
        # Critical contract: orchestrator dispatches on tier; mixing
        # the two would break STRICT vs WARN routing.
        assert not issubclass(e.LocalDrawingError, e.PerLayoutDrawingError)
        assert not issubclass(e.PerLayoutDrawingError, e.LocalDrawingError)


# ============================================================
# Local tier subtypes
# ============================================================

class TestLocalDrawingErrorSubtypes:
    @pytest.mark.parametrize("cls", [
        e.UpstreamSchemaDriftError,
        e.C16ConfigurationError,
        e.JurisdictionNotSupportedError,
        e.OrientationLockMismatchError,
    ])
    def test_subtype_descends_from_local(self, cls):
        assert issubclass(cls, e.LocalDrawingError)

    def test_upstream_schema_drift_records_versions(self):
        err = e.UpstreamSchemaDriftError(
            "C13 schema drift",
            upstream_component="c13_door_placement",
            expected_version="v1.0",
            observed_version="v0.9",
        )
        assert err.upstream_component == "c13_door_placement"
        assert err.expected_version == "v1.0"
        assert err.observed_version == "v0.9"

    def test_configuration_error_records_field(self):
        err = e.C16ConfigurationError(
            "bad bound",
            offending_field="plot_x_max_mm",
            offending_value=10_000_000_000,
        )
        assert err.offending_field == "plot_x_max_mm"
        assert err.offending_value == 10_000_000_000

    def test_jurisdiction_not_supported_records_requested_and_supported(self):
        err = e.JurisdictionNotSupportedError(
            "nope",
            requested_jurisdiction="ka_bbmp_2020",
            supported=frozenset({"tn_cdbr_2019"}),
        )
        assert err.requested_jurisdiction == "ka_bbmp_2020"
        assert err.supported == frozenset({"tn_cdbr_2019"})

    def test_orientation_lock_mismatch_carries_candidates(self):
        err = e.OrientationLockMismatchError(
            "mismatch",
            locked_orientation_deg=90.0,
            candidate_orientations_deg=(45.0, 135.0, 225.0, 315.0),
            epsilon_deg=1e-6,
        )
        assert err.locked_orientation_deg == 90.0
        assert len(err.candidate_orientations_deg) == 4
        assert err.epsilon_deg == 1e-6


# ============================================================
# Per-layout tier subtypes
# ============================================================

class TestPerLayoutDrawingErrorSubtypes:
    @pytest.mark.parametrize("cls", [
        e.MissingUpstreamDataError,
        e.GeometryInconsistencyError,
        e.ComplianceProvenanceError,
    ])
    def test_subtype_descends_from_perlayout(self, cls):
        assert issubclass(cls, e.PerLayoutDrawingError)

    def test_missing_upstream_data_records_field(self):
        err = e.MissingUpstreamDataError(
            "no doors",
            missing_field="doors",
            upstream_component="c13_door_placement",
        )
        assert err.missing_field == "doors"
        assert err.upstream_component == "c13_door_placement"

    def test_geometry_inconsistency_records_invariant(self):
        err = e.GeometryInconsistencyError(
            "orphan geometry",
            invariant_id="R24b",
            offending_ids=("g_abc12345",),
        )
        assert err.invariant_id == "R24b"
        assert err.offending_ids == ("g_abc12345",)

    def test_compliance_provenance_records_invariant_and_field(self):
        err = e.ComplianceProvenanceError(
            "wrong authority",
            invariant_id="R22",
            attested_field="plot_coverage_pct",
            authority_observed="locally_derived",
        )
        assert err.invariant_id == "R22"
        assert err.attested_field == "plot_coverage_pct"
        assert err.authority_observed == "locally_derived"


# ============================================================
# Catching by tier (orchestrator routing contract)
# ============================================================

class TestTierRouting:
    def test_local_errors_caught_at_local_tier(self):
        with pytest.raises(e.LocalDrawingError):
            raise e.JurisdictionNotSupportedError(
                "nope",
                requested_jurisdiction="x",
                supported=frozenset({"tn_cdbr_2019"}),
            )

    def test_perlayout_errors_caught_at_perlayout_tier(self):
        with pytest.raises(e.PerLayoutDrawingError):
            raise e.MissingUpstreamDataError("x", missing_field="y")

    def test_local_not_caught_as_perlayout(self):
        with pytest.raises(e.LocalDrawingError):
            try:
                raise e.C16ConfigurationError("local error")
            except e.PerLayoutDrawingError:
                pytest.fail("LocalDrawingError must NOT match PerLayoutDrawingError")
            # If we got here without re-raising, fail
            raise e.C16ConfigurationError("local error")  # propagate up

    def test_all_caught_at_root(self):
        for err in [
            e.C16ConfigurationError("a"),
            e.MissingUpstreamDataError("b", missing_field="c"),
        ]:
            with pytest.raises(e.DrawingRenderError):
                raise err


# ============================================================
# Message threading (str() returns the message)
# ============================================================

class TestMessageThreading:
    def test_configuration_error_message_threads_through(self):
        err = e.C16ConfigurationError("bad config X")
        assert "bad config X" in str(err)

    def test_geometry_inconsistency_message_threads_through(self):
        err = e.GeometryInconsistencyError("R24a violation", invariant_id="R24a")
        assert "R24a" in str(err)
