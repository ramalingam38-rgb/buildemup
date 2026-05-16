"""
BuildemUp — C11a — operator M0_BASE
====================================

Per spec § 2.1 / § 3 Phase 1: M0_BASE is the **identity** operator —
the always-valid baseline emitted for every input candidate when
``config.emit_base=True``. It applies no transformation and runs no
predicates.

Family: BASE (only member). Tier: SHALLOW. Family-transition policy:
PRESERVES_FAMILY (the output is structurally the source).

M0 exists as an explicit operator (rather than implicit behaviour) so
the per-batch ``BatchAllNonBaseFailedError`` can be reasoned about: a
batch with at least one M0_BASE accepted candidate has at least one
output, even if every non-base operator failed.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11a.operators._base import (
    TierAOperatorContext,
    build_valid_result,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)


def apply_m0_base(
    source: Any,
    context: TierAOperatorContext,
    *,
    source_signature: str,
    source_family_id: str,
) -> MutationApplicationResult:
    """Apply M0_BASE to ``source``.

    Always returns ``valid=True``. The output_family_id equals the
    source_family_id (M0 preserves family by definition). No predicates
    are checked (the § 3.4 matrix entry for M0 is empty).

    Args:
        source: the source ``WetZonePlannedCandidate`` (treated as
            opaque at Sub-2 — operators do not deeply inspect it).
        context: pre-extracted upstream state (unused by M0).
        source_signature: deterministic signature derived by Sub-4
            from the source candidate's identity. Sub-2 tests pass
            an explicit string.
        source_family_id: topology family id of the source. Sub-4
            extracts; Sub-2 tests pass explicitly.

    Returns:
        A valid ``MutationApplicationResult`` with
        ``family_transition_policy=PRESERVES_FAMILY`` and
        ``output_family_id == source_family_id``.
    """
    # No predicates, no proposal — M0 is identity. Carry the source as
    # output_candidate so consumers can read ALL valid results uniformly
    # via result.output_candidate (post-S41 self-review fix follow-up:
    # without this, downstream code must special-case "if op==M0: use
    # source else: use output_candidate").
    return build_valid_result(
        operator=MutationOperator.M0_BASE,
        source_signature=source_signature,
        source_family_id=source_family_id,
        output_family_id=source_family_id,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        output_candidate=source,
    )


__all__ = ["apply_m0_base"]
