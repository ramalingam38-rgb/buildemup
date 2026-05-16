"""
BuildemUp — C11a — operator M7B_GRID_SCALE_2_7 (Tier B)
==========================================================

Per spec § 2.1 / § 2.2: M7b sets the structural grid bay to 2.7 m ×
2.7 m. Companion to M7a (3.3 m); together they sample the small +
large ends of the v1 grid scale set. 3.0 m is the default mid-scale
that the source candidate typically already uses.

Family: GRID. Tier: REGENERATIVE. requires_grid_regen=True.
Family-transition policy: PRESERVES_FAMILY.
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


_OPERATOR_ID = MutationOperator.M7B_GRID_2_7
_TARGET_BAY_M = 2.7


def _build_m7b_mutation(source: Any) -> TierBInputMutation:
    return TierBInputMutation(
        operator=_OPERATOR_ID,
        new_grid_bay_x_m=_TARGET_BAY_M,
        new_grid_bay_y_m=_TARGET_BAY_M,
    )


def apply_m7b_grid_2_7(
    source: Any,
    pipeline: DeepMutationPipeline,
    *,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M7B_GRID_2_7 via the Tier B pipeline."""
    return apply_tier_b_operator(
        operator=_OPERATOR_ID,
        source=source,
        pipeline=pipeline,
        mutation_builder=_build_m7b_mutation,
        config=config,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m7b_grid_2_7"]
