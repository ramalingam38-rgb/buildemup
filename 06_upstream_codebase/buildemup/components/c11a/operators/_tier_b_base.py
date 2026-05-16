"""
BuildemUp — C11a — operators._tier_b_base
============================================

Shared machinery for the four Tier B operators (M6/M7a/M7b/M8).

Each Tier B operator's ``apply_*()`` function:

  1. Builds operator-specific ``TierBInputMutation`` (e.g., M7a fixes
     bay sizes to 3.3 m × 3.3 m; M6 chooses a new wet-wall direction).
  2. Delegates to ``DeepMutationPipeline.apply()`` for the cache
     lookup → upstream regen → lineage classify → cache write flow.
  3. Wraps the pipeline's ``DeepMutationPipelineResult`` into a
     ``MutationApplicationResult``.

Like Sub-2 Tier A operators, Sub-3 Tier B operators take an explicit
``source_signature`` + ``source_family_id`` so the orchestrator (Sub-4)
controls identity derivation. The pipeline is also passed in — Sub-4
constructs ONE pipeline per batch and threads it through; Sub-3 tests
construct it inline.

Why a shared base: the four operators differ only in (a) which input
mutation they build and (b) their family-transition policy + family.
Shared apply core eliminates ~150 lines of duplication.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from buildemup.components.c11a.deep_pipeline import (
    DeepMutationPipeline,
    DeepMutationPipelineResult,
    TierBInputMutation,
)
from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.operators._base import (
    derive_variant_id,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationLineageDepth,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
    TopologyMutationConfig,
)


# =============================================================================
# Shared Tier B apply
# =============================================================================


def apply_tier_b_operator(
    *,
    operator: MutationOperator,
    source: Any,
    pipeline: DeepMutationPipeline,
    mutation_builder: Callable[[Any], TierBInputMutation],
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Run the shared Tier B apply path.

    Args:
        operator: which Tier B operator (M6/M7a/M7b/M8).
        source: source WetZonePlannedCandidate (opaque at this layer).
        pipeline: the per-batch DeepMutationPipeline. Sub-4 supplies
            this; Sub-3 tests construct one inline.
        mutation_builder: callable that builds the operator's
            ``TierBInputMutation`` from the source. Caller supplies
            the operator-specific logic (e.g., M7a fixes bay sizes).
        config: TopologyMutationConfig — read for cache hashing.
        source_signature, source_family_id: per-source identity tokens.

    Returns:
        ``MutationApplicationResult`` (per-candidate verdict).
    """
    metadata = OPERATOR_METADATA[operator]

    # Step 1 — build input mutation.
    try:
        mutation = mutation_builder(source)
    except Exception as exc:
        # Operator-internal pre-condition failure (e.g., M8 on a
        # single-floor brief). Per-candidate scope.
        return MutationApplicationResult(
            operator=operator,
            valid=False,
            invalidity_reason=str(exc),
            topology_variant_id=None,
            rejection_invariant_id=None,
            source_family_id=source_family_id,
            output_family_id=None,
            family_transition_policy=metadata.family_transition_policy,
            lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
            upstream_regeneration_delta=(),
        )

    # Step 2 — delegate to pipeline.
    pipe_result: DeepMutationPipelineResult = pipeline.apply(
        source=source,
        operator=operator,
        mutation=mutation,
        config=config,
        source_signature=source_signature,
    )

    # Step 3 — wrap into MutationApplicationResult.
    if not pipe_result.valid:
        # Lineage_depth is None here — the result was rejected. Per
        # spec § 2.3, lineage_depth on the application result still
        # carries a non-None value. Convention: rejected Tier B
        # carries the *attempted* tier label — REGENERATIVE_TRANSFORM
        # since that's what the pipeline tried to perform.
        return MutationApplicationResult(
            operator=operator,
            valid=False,
            invalidity_reason=pipe_result.invalidity_reason,
            topology_variant_id=None,
            rejection_invariant_id=pipe_result.rejection_invariant_id,
            source_family_id=source_family_id,
            output_family_id=None,
            family_transition_policy=metadata.family_transition_policy,
            lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
            upstream_regeneration_delta=pipe_result.upstream_regeneration_delta,
        )

    # Successful regeneration — output_family_id depends on policy.
    output_family_id = _derive_output_family_id(
        operator, source_family_id, metadata.family_transition_policy,
    )

    return MutationApplicationResult(
        operator=operator,
        valid=True,
        invalidity_reason=None,
        topology_variant_id=derive_variant_id(operator, source_signature),
        rejection_invariant_id=None,
        source_family_id=source_family_id,
        output_family_id=output_family_id,
        family_transition_policy=metadata.family_transition_policy,
        lineage_depth=pipe_result.lineage_depth or MutationLineageDepth.REGENERATIVE_TRANSFORM,
        upstream_regeneration_delta=pipe_result.upstream_regeneration_delta,
        # Pattern B fix (self-review at S41 close): the deep pipeline
        # already produced the regenerated WZPC; thread it onto the
        # result so downstream consumers (C11b NSGA-II, scoring) can
        # actually use the Tier B mutation output. Previously the
        # constructed candidate was discarded after pipeline validation.
        output_candidate=pipe_result.regenerated_candidate,
    )


def _derive_output_family_id(
    operator: MutationOperator,
    source_family_id: str,
    policy: TopologyFamilyTransitionPolicy,
) -> str:
    """Map source_family_id → output_family_id per the operator's
    family_transition_policy. Mirrors the Tier A convention from Sub-2.
    """
    if policy == TopologyFamilyTransitionPolicy.PRESERVES_FAMILY:
        return source_family_id
    if policy == TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY:
        return f"transformed_from_{source_family_id}"
    # INVALIDATES_FAMILY — surface as "invalidated" placeholder; Sub-4's
    # emergent classification refines.
    return f"invalidated_from_{source_family_id}"


__all__ = ["apply_tier_b_operator"]
