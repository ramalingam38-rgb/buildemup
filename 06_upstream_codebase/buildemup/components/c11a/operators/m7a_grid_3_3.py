"""
BuildemUp — C11a — operator M7A_GRID_SCALE_3_3 (Tier B)
==========================================================

Per spec § 2.1 / § 2.2: M7a sets the structural grid bay to 3.3 m ×
3.3 m. The operator drives C7 grid regeneration → cascading C8 corridor
re-design → C9 room sizing → C10 wet-zone re-plan.

Per W#5 Q11 (carried v1.0): the M7 grid scales are FIXED at v1
(2.7 / 3.0 / 3.3 m). A KB-driven set is post-v1 work (B-NEW-A).

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


_OPERATOR_ID = MutationOperator.M7A_GRID_3_3
_TARGET_BAY_M = 3.3


def _build_m7a_mutation(source: Any) -> TierBInputMutation:
    return TierBInputMutation(
        operator=_OPERATOR_ID,
        new_grid_bay_x_m=_TARGET_BAY_M,
        new_grid_bay_y_m=_TARGET_BAY_M,
    )


def apply_m7a_grid_3_3(
    source: Any,
    pipeline: DeepMutationPipeline,
    *,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M7A_GRID_3_3 via the Tier B pipeline."""
    return apply_tier_b_operator(
        operator=_OPERATOR_ID,
        source=source,
        pipeline=pipeline,
        mutation_builder=_build_m7a_mutation,
        config=config,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m7a_grid_3_3"]
