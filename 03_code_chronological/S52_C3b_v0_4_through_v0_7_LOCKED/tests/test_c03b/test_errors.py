"""Tests for C3b error hierarchy (spec § 4)."""
from __future__ import annotations

import pytest

from buildemup.components.c03b.errors import (
    ApplicabilityBoundaryError,
    C3bConfigurationError,
    C3bError,
    CompatibilityAssertionFailedError,
    ConstraintViolationError,
    DownstreamImpactSetMissingError,
    ImpactComputationError,
    LocalTradeoffError,
    PerTweakError,
    RecommendationFlagAmbiguityError,
    SessionPersistenceError,
    SubsetRerunOrchestrationError,
    TopologyInvarianceProbeError,
    TweakGenerationError,
    UpstreamSchemaDriftError,
)


# ============================================================
# Hierarchy — base classes
# ============================================================

def test_c3b_error_is_root():
    """Every C3b-emitted error descends from C3bError."""
    assert issubclass(LocalTradeoffError, C3bError)
    assert issubclass(PerTweakError, C3bError)


def test_local_and_per_tweak_are_disjoint():
    """The two tiers don't share a more-specific base than C3bError."""
    assert not issubclass(LocalTradeoffError, PerTweakError)
    assert not issubclass(PerTweakError, LocalTradeoffError)


# ============================================================
# LocalTradeoffError subclasses
# ============================================================

def test_upstream_schema_drift_is_local():
    assert issubclass(UpstreamSchemaDriftError, LocalTradeoffError)


def test_upstream_schema_drift_carries_versions():
    err = UpstreamSchemaDriftError(
        "C15 v0.9 received but expected v1.0",
        expected_version="v1.0.LOCKED",
        observed_version="v0.9",
        upstream="c15",
    )
    assert err.expected_version == "v1.0.LOCKED"
    assert err.observed_version == "v0.9"
    assert err.upstream == "c15"
    assert err.phase == "alpha"


def test_c3b_configuration_error_is_local():
    assert issubclass(C3bConfigurationError, LocalTradeoffError)


def test_c3b_configuration_error_carries_field():
    err = C3bConfigurationError(
        "iteration_cap out of range",
        offending_field="iteration_cap",
        offending_value=99,
    )
    assert err.offending_field == "iteration_cap"
    assert err.offending_value == 99


def test_applicability_boundary_is_local():
    assert issubclass(ApplicabilityBoundaryError, LocalTradeoffError)


def test_applicability_boundary_carries_kind():
    err = ApplicabilityBoundaryError(
        "Preview Mode unresolved",
        boundary_kind="preview_mode",
        diagnostic="ResolvedBrief.extreme_case_status='preview_mode'",
    )
    assert err.boundary_kind == "preview_mode"
    assert err.phase == "alpha"


def test_session_persistence_is_local():
    assert issubclass(SessionPersistenceError, LocalTradeoffError)


def test_session_persistence_carries_operation():
    err = SessionPersistenceError("WAL write failed", operation="write")
    assert err.operation == "write"


def test_subset_rerun_orchestration_is_local():
    assert issubclass(SubsetRerunOrchestrationError, LocalTradeoffError)


def test_subset_rerun_orchestration_carries_components():
    err = SubsetRerunOrchestrationError(
        "C12 placement failed",
        failed_components=("c12",),
        rerun_request_id="srr_001",
    )
    assert err.failed_components == ("c12",)
    assert err.rerun_request_id == "srr_001"
    assert err.phase == "epsilon"


def test_topology_invariance_probe_is_local():
    """Spec § 4.1 v0.2 addition. Phase β step 4.2 probe failure."""
    assert issubclass(TopologyInvarianceProbeError, LocalTradeoffError)


def test_topology_invariance_probe_carries_basis():
    err = TopologyInvarianceProbeError(
        "Can't determine prediction_basis",
        tweak_category="kitchen_reorient",
        prediction_basis="heuristic_weak",
    )
    assert err.tweak_category == "kitchen_reorient"
    assert err.prediction_basis == "heuristic_weak"
    assert err.phase == "beta"


# ============================================================
# PerTweakError subclasses
# ============================================================

def test_tweak_generation_is_per_tweak():
    assert issubclass(TweakGenerationError, PerTweakError)


def test_tweak_generation_carries_check_id():
    err = TweakGenerationError(
        "Cross-floor circulation tweak out-of-scope v1.0",
        problem_check_id="check_X",
        tweak_category_attempted="room_swap",
        tweak_id="t1",
        layout_id="L1",
    )
    assert err.problem_check_id == "check_X"
    assert err.tweak_category_attempted == "room_swap"
    assert err.tweak_id == "t1"
    assert err.layout_id == "L1"


def test_impact_computation_is_per_tweak():
    assert issubclass(ImpactComputationError, PerTweakError)


def test_impact_computation_carries_dim():
    err = ImpactComputationError(
        "RateProvider lookup failed",
        impact_dim="cost",
        tweak_id="t1",
    )
    assert err.impact_dim == "cost"


def test_constraint_violation_is_per_tweak():
    assert issubclass(ConstraintViolationError, PerTweakError)


def test_constraint_violation_carries_constraint():
    err = ConstraintViolationError(
        "Resulting bath area below NBC min",
        constraint="nbc_bath_min_area",
        violated_value=18.0,
        tweak_id="t1",
    )
    assert err.constraint == "nbc_bath_min_area"
    assert err.violated_value == 18.0


def test_recommendation_flag_ambiguity_is_per_tweak():
    assert issubclass(RecommendationFlagAmbiguityError, PerTweakError)


def test_downstream_impact_set_missing_is_per_tweak():
    """Spec § 4.2 v0.2 addition. Hard error per § 2.4.1 contract."""
    assert issubclass(DownstreamImpactSetMissingError, PerTweakError)


def test_compatibility_assertion_failed_is_per_tweak():
    """Spec § 4.2 v0.2 addition (R15)."""
    assert issubclass(CompatibilityAssertionFailedError, PerTweakError)


def test_compatibility_assertion_failed_carries_kind():
    err = CompatibilityAssertionFailedError(
        "Spatial overlap with prior tweak",
        conflicting_tweak_id="t_prior",
        assertion_kind="spatial_overlap_check",
        tweak_id="t_new",
    )
    assert err.conflicting_tweak_id == "t_prior"
    assert err.assertion_kind == "spatial_overlap_check"
    assert err.tweak_id == "t_new"


# ============================================================
# Raise + catch behavior
# ============================================================

def test_local_error_caught_as_c3b_error():
    with pytest.raises(C3bError):
        raise ApplicabilityBoundaryError("any reason")


def test_per_tweak_error_caught_as_c3b_error():
    with pytest.raises(C3bError):
        raise ConstraintViolationError("any constraint")


def test_per_tweak_not_caught_as_local():
    """Routing discipline: catching LocalTradeoffError does NOT
    swallow per-tweak errors."""
    with pytest.raises(PerTweakError):
        try:
            raise TweakGenerationError("test")
        except LocalTradeoffError:
            pytest.fail("PerTweakError should not be caught as LocalTradeoffError")
