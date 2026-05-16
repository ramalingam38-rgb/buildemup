"""
BuildemUp — C11a — operator M6_WET_ROTATE (Tier B)
====================================================

Per spec § 2.1 / § 2.2: M6 rotates the wet-wall assignment direction.
The operator drives C10 wet-zone re-planning with the rotated wall
target; downstream the new wet-wall produces new trap-arm distances
and (potentially) regrouped risers.

Family: WET_WALL. Tier: REGENERATIVE. Family-transition policy:
PRESERVES_FAMILY (the topology family is a circulation/zoning
property, not a plumbing one — rotating the wet wall doesn't
reclassify Strip/CentralSpine/etc.).

Per § 3.4 matrix: M6 is Tier B → no Tier A predicates. Validation
happens at C10 invariant-check time (§ 3.5 step 5) plus lineage
classification on the actual delta.

Sub-3 simplification: the input mutation carries
``new_wet_wall_assignment_direction='rotate_90_clockwise'`` — a
symbolic instruction. Sub-4's UpstreamRegenerator translates this
into the concrete C10 input rebuild.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11a.deep_pipeline import (
    DeepMutationPipeline,
    TierBInputMutation,
)
from buildemup.components.c11a.operators._tier_b_base import (
    apply_tier_b_operator,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationOperator,
    TopologyMutationConfig,
)


_OPERATOR_ID = MutationOperator.M6_WET_ROTATE


def _build_m6_mutation(source: Any) -> TierBInputMutation:
    """Build M6's input mutation. Symbolic at Sub-3; Sub-4's wiring
    translates 'rotate_90_clockwise' to the concrete wet-wall config.
    """
    return TierBInputMutation(
        operator=_OPERATOR_ID,
        new_wet_wall_assignment_direction="rotate_90_clockwise",
    )


def apply_m6_wet_rotate(
    source: Any,
    pipeline: DeepMutationPipeline,
    *,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M6_WET_ROTATE via the Tier B pipeline.

    Sub-3 testing: tests construct a ``StubUpstreamRegenerator``,
    instantiate the pipeline, and pass it in. Sub-4 wires the real
    upstream and constructs ONE pipeline per batch.
    """
    return apply_tier_b_operator(
        operator=_OPERATOR_ID,
        source=source,
        pipeline=pipeline,
        mutation_builder=_build_m6_mutation,
        config=config,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m6_wet_rotate"]
