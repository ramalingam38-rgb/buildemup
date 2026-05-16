"""
C11a Sub-session 3 tests — DeepMutationPipeline.

Per spec § 3.5 + Inv 17 (atomicity) + § 2.7 severity routing + § 0.3
caching. Tests use ``StubUpstreamRegenerator`` to drive the pipeline
through happy / per-candidate-fail / systemic-fail paths without
standing up real C7/C9/C10.
"""
from __future__ import annotations

from typing import ClassVar

import pytest

from buildemup.components.c11a import (
    DeepMutationApplicationError,
    DeepMutationPipeline,
    DeepMutationPipelineResult,
    DeltaKey,
    MutationLineageDepth,
    MutationOperator,
    StubUpstreamRegenerator,
    TierBInputMutation,
    TopologyMutationConfig,
)


# =============================================================================
# Test helpers — synthetic exceptions with declared severity tiers
# =============================================================================


class _SystemicError(Exception):
    """Mimics KBVersionMismatchError / RemediationGraphError shape."""
    severity_tier: ClassVar[str] = "systemic"


class _BatchError(Exception):
    severity_tier: ClassVar[str] = "batch"


class _PerCandidateError(Exception):
    severity_tier: ClassVar[str] = "per_candidate"


class _UnclassifiedError(Exception):
    """No severity_tier ClassVar — defaults to systemic per defensive
    fallback in _severity_of."""


def _make_pipeline(stub: StubUpstreamRegenerator | None = None) -> DeepMutationPipeline:
    return DeepMutationPipeline(upstream=stub or StubUpstreamRegenerator())


def _make_mutation(operator: MutationOperator) -> TierBInputMutation:
    return TierBInputMutation(operator=operator)


# =============================================================================
# Happy path — REGENERATIVE_TRANSFORM
# =============================================================================


def test_happy_path_regenerative_transform_m6() -> None:
    """Stub returns expected delta → REGENERATIVE_TRANSFORM."""
    stub = StubUpstreamRegenerator(return_value="regenerated")
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src",
        operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(),
        source_signature="sig",
    )
    assert result.valid is True
    assert result.lineage_depth == MutationLineageDepth.REGENERATIVE_TRANSFORM
    assert result.regenerated_candidate == "regenerated"
    assert result.cache_hit is False


def test_happy_path_emergent_regeneration() -> None:
    """Stub returns delta with keys outside declared scope → EMERGENT."""
    stub = StubUpstreamRegenerator(
        return_value="regen",
        delta_keys=(DeltaKey.PLUMB_WET_WALL_ASSIGNMENT, DeltaKey.ZONE_ASSIGNMENTS),
    )
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src",
        operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(),
        source_signature="sig",
    )
    assert result.valid is True
    assert result.lineage_depth == MutationLineageDepth.EMERGENT_REGENERATION


# =============================================================================
# REJECT — forbidden delta key
# =============================================================================


def test_reject_on_forbidden_delta() -> None:
    """Stub returns delta with a forbidden key → pipeline rejects."""
    stub = StubUpstreamRegenerator(
        return_value="regen",
        delta_keys=(DeltaKey.GEO_ROOM_AREA,),  # forbidden for M6
    )
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src",
        operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(),
        source_signature="sig",
    )
    assert result.valid is False
    assert result.lineage_depth is None
    assert result.regenerated_candidate is None
    assert result.rejection_invariant_id is not None
    assert "forbidden_delta_key" in result.rejection_invariant_id


# =============================================================================
# Severity routing — per-candidate / batch / systemic
# =============================================================================


def test_per_candidate_error_caught_and_wrapped() -> None:
    """Per-candidate severity errors → caught, candidate rejected."""
    stub = StubUpstreamRegenerator(
        raise_on_regenerate=_PerCandidateError("upstream rejected"),
    )
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src",
        operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(),
        source_signature="sig",
    )
    assert result.valid is False
    assert result.regenerated_candidate is None
    assert "Tier B regeneration failed" in (result.invalidity_reason or "")


def test_batch_error_also_caught_per_severity_routing() -> None:
    """Batch severity errors are also caught (treated as per-candidate
    Tier B failure per § 2.7 / DeepMutationApplicationError docstring).
    """
    stub = StubUpstreamRegenerator(
        raise_on_regenerate=_BatchError("batch level"),
    )
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src",
        operator=MutationOperator.M7A_GRID_3_3,
        mutation=_make_mutation(MutationOperator.M7A_GRID_3_3),
        config=TopologyMutationConfig(),
        source_signature="sig",
    )
    assert result.valid is False


def test_systemic_error_propagates_uncaught() -> None:
    """Systemic-severity errors propagate UNCAUGHT — pipeline must not
    swallow them. Per F-v2-7."""
    stub = StubUpstreamRegenerator(
        raise_on_regenerate=_SystemicError("KB mismatch"),
    )
    pipeline = _make_pipeline(stub)
    with pytest.raises(_SystemicError, match="KB mismatch"):
        pipeline.apply(
            source="src",
            operator=MutationOperator.M6_WET_ROTATE,
            mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
            config=TopologyMutationConfig(),
            source_signature="sig",
        )


def test_unclassified_error_treated_as_systemic_defensively() -> None:
    """Errors without severity_tier ClassVar default to systemic per
    F-v4-5 fail-closed policy."""
    stub = StubUpstreamRegenerator(
        raise_on_regenerate=_UnclassifiedError("no tier declared"),
    )
    pipeline = _make_pipeline(stub)
    with pytest.raises(_UnclassifiedError):
        pipeline.apply(
            source="src",
            operator=MutationOperator.M6_WET_ROTATE,
            mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
            config=TopologyMutationConfig(),
            source_signature="sig",
        )


# =============================================================================
# Cache behaviour
# =============================================================================


def test_cache_hit_on_second_call_with_same_inputs() -> None:
    """Second call with identical (source, operator, config) hits
    the cache; upstream NOT re-invoked."""
    stub = StubUpstreamRegenerator(return_value="regen")
    pipeline = _make_pipeline(stub)
    args = dict(
        source="src", operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(), source_signature="sig",
    )
    first = pipeline.apply(**args)
    second = pipeline.apply(**args)
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert stub.regenerate_call_count == 1
    assert pipeline.cache_hits == 1
    assert pipeline.cache_misses == 1


def test_cache_miss_on_different_source_signature() -> None:
    stub = StubUpstreamRegenerator(return_value="regen")
    pipeline = _make_pipeline(stub)
    base = dict(
        source="src", operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(),
    )
    pipeline.apply(**base, source_signature="sig-A")
    pipeline.apply(**base, source_signature="sig-B")
    assert stub.regenerate_call_count == 2
    assert pipeline.cache_hits == 0
    assert pipeline.cache_misses == 2


def test_cache_disabled_bypasses() -> None:
    """When cache_enabled=False, every call invokes upstream."""
    stub = StubUpstreamRegenerator(return_value="regen")
    pipeline = _make_pipeline(stub)
    pipeline.cache_enabled = False
    args = dict(
        source="src", operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(), source_signature="sig",
    )
    pipeline.apply(**args)
    pipeline.apply(**args)
    assert stub.regenerate_call_count == 2


def test_cache_stores_failures_too() -> None:
    """Per-candidate failures cache (so the same source+operator+config
    re-attempt doesn't re-invoke upstream pointlessly)."""
    stub = StubUpstreamRegenerator(
        raise_on_regenerate=_PerCandidateError("rejected"),
    )
    pipeline = _make_pipeline(stub)
    args = dict(
        source="src", operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(), source_signature="sig",
    )
    first = pipeline.apply(**args)
    second = pipeline.apply(**args)
    assert first.valid is False and second.valid is False
    assert second.cache_hit is True
    assert stub.regenerate_call_count == 1


# =============================================================================
# Tier-guard
# =============================================================================


def test_pipeline_rejects_tier_a_operator() -> None:
    """The pipeline is REGENERATIVE-only; passing a Tier A operator
    raises ValueError."""
    pipeline = _make_pipeline()
    with pytest.raises(ValueError, match="REGENERATIVE"):
        pipeline.apply(
            source="src",
            operator=MutationOperator.M0_BASE,   # SHALLOW
            mutation=_make_mutation(MutationOperator.M0_BASE),
            config=TopologyMutationConfig(),
            source_signature="sig",
        )


# =============================================================================
# DeepMutationPipelineResult shape
# =============================================================================


def test_pipeline_result_is_frozen_dataclass() -> None:
    stub = StubUpstreamRegenerator(return_value="regen")
    pipeline = _make_pipeline(stub)
    result = pipeline.apply(
        source="src", operator=MutationOperator.M6_WET_ROTATE,
        mutation=_make_mutation(MutationOperator.M6_WET_ROTATE),
        config=TopologyMutationConfig(), source_signature="sig",
    )
    assert isinstance(result, DeepMutationPipelineResult)
    with pytest.raises(Exception):
        result.valid = False  # type: ignore[misc]
