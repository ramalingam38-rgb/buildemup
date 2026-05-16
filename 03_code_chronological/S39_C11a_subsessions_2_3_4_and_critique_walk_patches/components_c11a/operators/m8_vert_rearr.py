"""
BuildemUp — C11a — operator M8_VERT_REARR (Tier B)
======================================================

Per spec § 2.1 / § 2.2 + W#5 Q12: M8 swaps the master bedroom's floor
assignment in a multi-floor brief (e.g., master from first floor →
ground floor). Drives C9 room sizing + C10 wet-zone re-planning per
floor.

Per W#5 Q12: M8 is BUILDING-WIDE — the multi-floor scope makes this
a Tier B regenerative mutation. Single-floor briefs cannot dispatch
M8 (operator-internal pre-condition); the metadata table's
``requires_multi_floor=True`` flag surfaces this to Sub-4's orchestrator
which filters M8 out of single-floor batches.

Family: VERTICAL. Tier: REGENERATIVE. Requires multi-floor.
Family-transition policy: PRESERVES_FAMILY (the topology family is
per-floor; rearranging floors doesn't change a floor's family).
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


_OPERATOR_ID = MutationOperator.M8_VERT_REARR


def _build_m8_mutation(source: Any) -> TierBInputMutation:
    """Build M8's input mutation. Symbolic at Sub-3 ('swap_master_floor');
    Sub-4's wiring reads the source's current master-floor placement and
    proposes the swap.
    """
    return TierBInputMutation(
        operator=_OPERATOR_ID,
        new_master_bedroom_floor_label="swap_master_floor",
    )


def apply_m8_vert_rearr(
    source: Any,
    pipeline: DeepMutationPipeline,
    *,
    config: TopologyMutationConfig,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M8_VERT_REARR via the Tier B pipeline."""
    return apply_tier_b_operator(
        operator=_OPERATOR_ID,
        source=source,
        pipeline=pipeline,
        mutation_builder=_build_m8_mutation,
        config=config,
        source_signature=source_signature,
        source_family_id=source_family_id,
    )


__all__ = ["apply_m8_vert_rearr"]
