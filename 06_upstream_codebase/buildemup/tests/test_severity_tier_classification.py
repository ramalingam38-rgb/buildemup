"""
Tests for B-NEW-P (S38): error severity classification.

Verifies that every custom error class in C8, C9, and C10 declares a
``severity_tier`` ClassVar with a value in
``{"per_candidate", "batch", "systemic"}`` per C11a v1.0 SPEC § 2.7.

This is the upstream amendment that C11a's ``DeepMutationPipeline``
relies on to route exceptions via inversion-of-control rather than
hardcoded type lists. Per C11a § 2.7:

    severity = getattr(type(e), "severity_tier", "unknown")
    if severity == "systemic":
        raise                                # propagate uncaught
    if severity == "batch":
        raise DeepMutationApplicationError(e)  # wrap; reject mutation
    if severity == "per_candidate":
        raise DeepMutationApplicationError(e)  # wrap; reject mutation
    # severity == "unknown": defensive — treat as systemic
    raise

C7 raises only stdlib exceptions (KeyError/ValueError) and so falls
through to the "unknown" → systemic-default branch by design; that
behaviour is verified at the C11a level, not here.
"""
from __future__ import annotations

from typing import get_args, get_type_hints

import pytest

from buildemup.components.c08 import errors as c8_errors
from buildemup.components.c09 import errors as c9_errors
from buildemup.components.c10 import errors as c10_errors

VALID_TIERS = frozenset({"per_candidate", "batch", "systemic"})


# =============================================================================
# Test corpus: (component_label, error_class, expected_tier)
# =============================================================================

_C9_CASES = [
    ("C9", c9_errors.RoomSizingError, "per_candidate"),  # base default
    ("C9", c9_errors.PerCandidateError, "per_candidate"),
    ("C9", c9_errors.RoomSizingInfeasibleError, "per_candidate"),
    ("C9", c9_errors.WidthInfeasibleError, "per_candidate"),
    ("C9", c9_errors.PackingInfeasibleError, "per_candidate"),
    ("C9", c9_errors.WidthRiskyError, "per_candidate"),
    ("C9", c9_errors.GridOversizeError, "per_candidate"),
    ("C9", c9_errors.BatchSizingInfeasibleError, "batch"),
    ("C9", c9_errors.NBCConfidenceTooLow, "systemic"),
]

_C10_CASES = [
    ("C10", c10_errors.WetZonePlanError, "per_candidate"),  # base default
    ("C10", c10_errors.PerCandidateError, "per_candidate"),
    ("C10", c10_errors.WetZoneInfeasibleError, "per_candidate"),
    ("C10", c10_errors.PreClusteringInfeasibleError, "per_candidate"),
    ("C10", c10_errors.PoojaAdjacencyError, "per_candidate"),
    ("C10", c10_errors.RiserCountExceededError, "per_candidate"),
    ("C10", c10_errors.TrapArmDistanceExceededError, "per_candidate"),
    ("C10", c10_errors.WallCapacityExceededError, "per_candidate"),
    ("C10", c10_errors.ClusterIntegrityError, "per_candidate"),
    ("C10", c10_errors.BatchWetZoneInfeasibleError, "batch"),
    ("C10", c10_errors.PlumbingConfidenceTooLow, "systemic"),
    ("C10", c10_errors.KBVersionMismatchError, "systemic"),
    ("C10", c10_errors.RemediationGraphError, "systemic"),
]

_C8_CASES = [
    ("C8", c8_errors.CorridorTooNarrowError, "per_candidate"),
    ("C8", c8_errors.CorridorSelfIntersectionError, "systemic"),
    ("C8", c8_errors.CorridorDispatchError, "per_candidate"),
]

_ALL_CASES = _C8_CASES + _C9_CASES + _C10_CASES


# =============================================================================
# severity_tier presence + value tests
# =============================================================================


@pytest.mark.parametrize(
    "component, error_class, expected_tier",
    _ALL_CASES,
    ids=[f"{lbl}.{cls.__name__}" for lbl, cls, _ in _ALL_CASES],
)
def test_severity_tier_declared_and_correct(
    component: str, error_class: type, expected_tier: str
) -> None:
    """Each error class has severity_tier == expected_tier."""
    assert hasattr(error_class, "severity_tier"), (
        f"{component}.{error_class.__name__} missing severity_tier ClassVar"
    )
    assert error_class.severity_tier == expected_tier, (
        f"{component}.{error_class.__name__} severity_tier="
        f"{error_class.severity_tier!r} expected {expected_tier!r}"
    )


@pytest.mark.parametrize(
    "component, error_class, expected_tier",
    _ALL_CASES,
    ids=[f"{lbl}.{cls.__name__}" for lbl, cls, _ in _ALL_CASES],
)
def test_severity_tier_in_valid_set(
    component: str, error_class: type, expected_tier: str
) -> None:
    """severity_tier is one of the three accepted Literal values."""
    assert error_class.severity_tier in VALID_TIERS, (
        f"{component}.{error_class.__name__} has invalid severity_tier"
        f"={error_class.severity_tier!r}; must be one of {VALID_TIERS}"
    )


# =============================================================================
# Inheritance behaviour
# =============================================================================


def test_c10_per_candidate_subclasses_inherit_tier() -> None:
    """Per-candidate subclasses of WetZonePlanError inherit "per_candidate"
    without explicit override (inheritance carries the ClassVar)."""
    # PoojaAdjacencyError doesn't have an explicit severity_tier line but
    # must report "per_candidate" via inheritance from the base.
    assert c10_errors.PoojaAdjacencyError.severity_tier == "per_candidate"


def test_c9_per_candidate_subclasses_inherit_tier() -> None:
    """Same for C9."""
    assert c9_errors.PackingInfeasibleError.severity_tier == "per_candidate"


def test_c10_systemic_overrides_base() -> None:
    """A systemic subclass overrides the per_candidate base default."""
    assert c10_errors.WetZonePlanError.severity_tier == "per_candidate"
    assert c10_errors.KBVersionMismatchError.severity_tier == "systemic"


def test_c9_batch_overrides_base() -> None:
    """A batch subclass overrides the per_candidate base default."""
    assert c9_errors.RoomSizingError.severity_tier == "per_candidate"
    assert c9_errors.BatchSizingInfeasibleError.severity_tier == "batch"


# =============================================================================
# Instance access (subclasses pick up the ClassVar via type(instance))
# =============================================================================


def test_severity_tier_accessible_via_type_of_instance() -> None:
    """C11a's catch logic uses ``getattr(type(e), 'severity_tier', 'unknown')``;
    verify the lookup pattern works on an actual instance."""
    err = c10_errors.PoojaAdjacencyError("test")
    assert getattr(type(err), "severity_tier", "unknown") == "per_candidate"

    err2 = c10_errors.KBVersionMismatchError("test")
    assert getattr(type(err2), "severity_tier", "unknown") == "systemic"

    err3 = c9_errors.NBCConfidenceTooLow("test")
    assert getattr(type(err3), "severity_tier", "unknown") == "systemic"


def test_stdlib_exception_returns_unknown_default() -> None:
    """C7 raises stdlib KeyError/ValueError. Per C11a § 2.7 these fall
    through to the defensive "unknown" → systemic branch. Verify the
    getattr default applies to bare stdlib exceptions."""
    err = ValueError("not a buildemup error")
    assert getattr(type(err), "severity_tier", "unknown") == "unknown"

    err2 = KeyError("not a buildemup error")
    assert getattr(type(err2), "severity_tier", "unknown") == "unknown"


# =============================================================================
# C11a § 2.7 dispatch pattern reference test
# =============================================================================


def _classify(exc: BaseException) -> str:
    """Mirror of C11a § 2.7 dispatch logic, used here only to confirm the
    severity_tier ClassVar resolves to the expected branch for each
    upstream error class. The real DeepMutationPipeline implementation
    will live under C11a; this is a contract-level smoke test."""
    return getattr(type(exc), "severity_tier", "unknown")


@pytest.mark.parametrize(
    "error_class, expected",
    [
        (c10_errors.PoojaAdjacencyError, "per_candidate"),
        (c10_errors.BatchWetZoneInfeasibleError, "batch"),
        (c10_errors.KBVersionMismatchError, "systemic"),
        (c9_errors.RoomSizingInfeasibleError, "per_candidate"),
        (c9_errors.BatchSizingInfeasibleError, "batch"),
        (c9_errors.NBCConfidenceTooLow, "systemic"),
        (c8_errors.CorridorTooNarrowError, "per_candidate"),
        (c8_errors.CorridorSelfIntersectionError, "systemic"),
    ],
)
def test_classify_dispatch(error_class: type, expected: str) -> None:
    """Each error class instance routes to the expected branch in the
    C11a § 2.7 catch pattern."""
    # BatchWetZoneInfeasibleError + BatchSizingInfeasibleError have richer
    # constructors; build them with minimal args.
    if error_class is c10_errors.BatchWetZoneInfeasibleError:
        instance = error_class("batch failed", candidate_errors=())
    elif error_class is c9_errors.BatchSizingInfeasibleError:
        instance = error_class(failures=[], input_count=0)
    else:
        instance = error_class("smoke test")
    assert _classify(instance) == expected


# =============================================================================
# Defensive: ClassVar ordering is consistent (no shadowing surprises)
# =============================================================================


def test_no_instance_attribute_shadows_classvar() -> None:
    """severity_tier must remain a class attribute; no constructor sets it
    at instance level (which would be a B-NEW-P amendment violation)."""
    err = c10_errors.PoojaAdjacencyError("test")
    # __dict__ at the instance level should not contain severity_tier
    assert "severity_tier" not in err.__dict__
    # but the class attribute is still reachable
    assert err.severity_tier == "per_candidate"
