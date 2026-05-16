"""
BuildemUp — Component 11a — lineage classification (Sub-session 3)
====================================================================

Per spec § 2.3 + Inv 21 / Inv 23 + § 3.5 Step 5b: after Tier B
regeneration, ``classify_lineage_depth()`` reads the actual delta keys
(fields that changed during upstream re-run) and classifies the result
against the operator's ``OperatorExpectedDeltaSchema``:

  * **REGENERATIVE_TRANSFORM** — actual_delta ⊆ (expected ∪ allowed_secondary).
    The mutation drove ONLY the changes the operator metadata declared.
  * **EMERGENT_REGENERATION** — actual_delta exceeds the declared scope
    (some keys appeared that aren't in expected ∪ allowed_secondary).
    The upstream re-run produced effects beyond operator intent.
  * **REJECT** (sentinel) — actual_delta intersects ``forbidden`` keys.
    The mutation violated a cross-operator invariant (e.g., changed
    room count when the operator forbids that). The pipeline rejects
    the candidate.

This classification IS the lineage_depth carried on
``MutationApplicationResult``. EMERGENT_REGENERATION outputs are
preserved (the mutation succeeded) but LABELED so downstream consumers
(C11b, diagnostics, replay) can distinguish operator-driven mutations
from emergent-regeneration outputs.

Tier A always carries SHALLOW_TRANSFORM (no upstream re-run); Sub-2
operators use that directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from buildemup.components.c11a.schema import (
    DeltaKey,
    MutationLineageDepth,
    OperatorExpectedDeltaSchema,
)


# =============================================================================
# REJECT sentinel
# =============================================================================
#
# We don't add a REJECT enum value — REJECT is a control-flow outcome,
# not a stable lineage state to carry on a successful candidate. The
# classifier returns Optional[MutationLineageDepth]: None means
# "rejected — forbidden_keys hit". Pipeline callers check for None.


@dataclass(frozen=True)
class LineageClassification:
    """Outcome of ``classify_lineage_depth``.

    Two-state on the success path:
      * lineage_depth ∈ {REGENERATIVE_TRANSFORM, EMERGENT_REGENERATION}
        with rejection_reason=None and rejected_by_keys=()

    On the rejection path:
      * lineage_depth = None
      * rejected_by_keys = the forbidden keys that were hit
      * rejection_reason = human-readable explanation

    Per Spec #4 v1.6 § 3.8 (B-NEW-T3 #4):
      * floor_label_affected: the per-floor label this lineage entry
        scopes to, OR None for dwelling-level operators.
          - Per-floor operators (M0-M7, M9 — single-floor and per-floor
            multi-floor dispatch): label = the directly-mutated floor.
          - M8 (dwelling-level): label = None.
          - Single-floor briefs: label = None (no multi-floor concept).
        Lightweight per-floor causality signal for downstream NSGA-II
        explainability and debugging. Full ancestry-chain extension
        filed as B-C11A-8.
    """

    lineage_depth: Optional[MutationLineageDepth]
    rejection_reason: Optional[str]
    rejected_by_keys: tuple[DeltaKey, ...]
    emergent_keys: tuple[DeltaKey, ...]    # delta keys outside expected ∪ allowed (informational)
    floor_label_affected: Optional[str] = None    # Spec #4 v1.6 § 3.8


# =============================================================================
# classify_lineage_depth
# =============================================================================


def classify_lineage_depth(
    actual_delta_keys: tuple[DeltaKey, ...],
    schema: OperatorExpectedDeltaSchema,
) -> LineageClassification:
    """Per § 2.3 / Inv 21 / Inv 23 — classify a Tier B regeneration's
    output by the delta it produced.

    Args:
        actual_delta_keys: the DeltaKey values that changed during
            upstream regeneration. Computed by the pipeline from
            (source_state, regenerated_state).
        schema: the operator's declared
            ``OperatorExpectedDeltaSchema``.

    Returns:
        ``LineageClassification`` with lineage_depth set per the rules
        above (or None for rejection).

    Resolution order:
      1. If any actual key ∈ schema.forbidden → REJECT.
      2. If actual ⊆ (expected ∪ allowed_secondary) → REGENERATIVE_TRANSFORM.
      3. Otherwise → EMERGENT_REGENERATION.

    Empty actual_delta is REGENERATIVE_TRANSFORM (vacuously) — the
    upstream re-run produced no observable change. Strange but valid;
    the operator's declared expected was a hope, not a guarantee.
    """
    actual_set = frozenset(actual_delta_keys)

    # Step 1 — forbidden hit?
    forbidden_hits = actual_set & schema.forbidden
    if forbidden_hits:
        # Stable lex-ASC ordering for the rejection reason.
        sorted_forbidden = tuple(sorted(forbidden_hits, key=lambda k: k.value))
        return LineageClassification(
            lineage_depth=None,
            rejection_reason=(
                f"Tier B regeneration produced forbidden delta key(s): "
                f"{[k.value for k in sorted_forbidden]}. "
                f"Operator's expected_delta_schema explicitly forbids "
                f"these (cross-operator invariant)."
            ),
            rejected_by_keys=sorted_forbidden,
            emergent_keys=(),
        )

    # Step 2 — within declared scope?
    declared_scope = schema.expected | schema.allowed_secondary
    emergent = actual_set - declared_scope

    if not emergent:
        # All actual keys ∈ declared scope.
        return LineageClassification(
            lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
            rejection_reason=None,
            rejected_by_keys=(),
            emergent_keys=(),
        )

    # Step 3 — emergent regeneration.
    sorted_emergent = tuple(sorted(emergent, key=lambda k: k.value))
    return LineageClassification(
        lineage_depth=MutationLineageDepth.EMERGENT_REGENERATION,
        rejection_reason=None,
        rejected_by_keys=(),
        emergent_keys=sorted_emergent,
    )


__all__ = [
    "LineageClassification",
    "classify_lineage_depth",
]
