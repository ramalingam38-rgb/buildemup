"""
BuildemUp — C11a — operators._base
====================================

Shared machinery for Sub-session 2 Tier A operators:

* ``TierAOperatorContext`` — frozen dataclass bundling the upstream
  state slices that operators read. Built by Sub-4's orchestrator from
  a ``WetZonePlannedCandidate``'s ancestry; tests construct it directly
  with fixture objects.

* ``OperatorPreconditionError`` — module-private exception raised by
  proposal builders when the source candidate doesn't satisfy an
  operator's structural pre-conditions (e.g., M4 applied to a
  has_corridor=False topology). Translated by ``apply_*`` wrappers
  into a ``MutationApplicationResult(valid=False)`` with
  ``rejection_invariant_id=None`` (operator-internal — distinct from
  predicate-driven rejections which carry an owner-prefixed id).

* ``derive_variant_id`` — deterministic SHA256-prefix variant id
  derivation per § 2.3 ("``topology_variant_id`` is a deterministic
  identifier derived from the source candidate's identity + the
  applied operator(s)"). Used for Sub-4 deduplication and Tier B
  cache lookup.

* ``build_valid_result`` / ``build_invalid_result`` — small factories
  that hide ``MutationApplicationResult`` boilerplate. They are
  intentionally NOT magic — every field is supplied explicitly so
  the operator's intent reads cleanly.

* ``dispatch_predicates`` — helper that walks an operator's § 3.4
  predicate matrix and dispatches each one with the right kwargs.
  See per-operator files for the kwarg conventions; the helper just
  iterates and short-circuits on the first failure.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Optional, TYPE_CHECKING

from buildemup.components.c11a.predicate_registry import (
    lookup_predicate,
    predicate_ids_for,
)
from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationLineageDepth,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)

if TYPE_CHECKING:
    # Forward refs — operator code depends on these types but importing
    # at module load time pulls a chunk of the upstream graph. The
    # runtime calls treat them duck-typed; only operator construction
    # requires the concrete classes.
    from buildemup.components.c05.schema import ZoneBand
    from buildemup.components.c07.grid_generator import Grid, Staircase
    from buildemup.components.c08.schema import CorridorPath
    from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# OperatorPreconditionError
# =============================================================================


class OperatorPreconditionError(Exception):
    """Raised by an operator's proposal builder when the source candidate
    cannot supply the inputs the operator needs.

    Examples (per spec § 5):
      * M4 applied to a topology with ``has_corridor=False``
      * M5 applied to zone_bands with no PUBLIC or PRIVATE entry
      * M9 applied to a corridor with no ENTRY endpoints

    The wrapping ``apply_*`` function translates this into a
    ``MutationApplicationError`` (per-candidate severity) by way of an
    invalid ``MutationApplicationResult``. Importantly: this does NOT
    halt the batch — it's a per-candidate scope failure.
    """


# =============================================================================
# TierAOperatorContext
# =============================================================================


@dataclass(frozen=True)
class TierAOperatorContext:
    """Pre-extracted upstream state that Tier A operators read.

    Sub-4's orchestrator constructs this from a
    ``WetZonePlannedCandidate``'s ancestry chain
    (``WetZonePlannedCandidate → RoomSizedCandidate →
    CorridorDesignedCandidate → OrientedCandidate → TopologyCandidate``).
    Sub-2 tests construct it directly.

    Fields are Optional and nullable per operator family:

      * BASE / M0     — uses none
      * FLIP / M1     — C9/C10 stub predicates only; reads no concrete state
      * FLIP / M2     — reads ``zone_bands`` + ``plot_facing`` for C5 predicate
      * STAIRCASE / M3 — reads ``grid`` + ``staircase`` (current footprint)
      * CORRIDOR / M4 — reads ``corridor_path`` (to verify has_corridor)
      * ZONE / M5     — reads ``zone_bands`` + ``plot_facing``
      * ENTRY / M9    — reads ``corridor_path`` + envelope dims + ``plot_facing``

    Each operator's apply() asserts the fields it requires; missing
    fields raise ``OperatorPreconditionError`` (translated to per-
    candidate failure in the result).
    """

    grid: Optional["Grid"] = None
    staircase: Optional["Staircase"] = None
    envelope_width_m: Optional[float] = None
    envelope_depth_m: Optional[float] = None
    plot_facing: Optional["PlotOrientation"] = None
    zone_bands: Optional[Mapping["ZoneBand", "PlotOrientation"]] = None
    corridor_path: Optional["CorridorPath"] = None


# =============================================================================
# Variant id derivation
# =============================================================================


def derive_variant_id(
    operator: MutationOperator,
    source_signature: str,
) -> str:
    """Per § 2.3 — derive the deterministic ``topology_variant_id``.

    Format: ``"{operator.value}@{sha256_prefix}"``. The prefix is the
    first 16 hex chars of SHA256(operator.value + ":" + source_signature)
    — short enough to be readable in logs, long enough that collisions
    across a batch (≤ N_inputs × 16 operators) are negligible.

    The format is stable; downstream caches and dedup logic depend on
    it. Changing it would break Tier B replay determinism.
    """
    h = hashlib.sha256()
    h.update(operator.value.encode("utf-8"))
    h.update(b":")
    h.update(source_signature.encode("utf-8"))
    digest_prefix = h.hexdigest()[:16]
    return f"{operator.value}@{digest_prefix}"


# =============================================================================
# Result factories
# =============================================================================


def build_valid_result(
    *,
    operator: MutationOperator,
    source_signature: str,
    source_family_id: str,
    output_family_id: str,
    family_transition_policy: TopologyFamilyTransitionPolicy,
    output_candidate: Optional[Any] = None,
) -> MutationApplicationResult:
    """Construct a successful ``MutationApplicationResult``.

    Tier A SHALLOW always carries:
      * ``valid=True``
      * ``invalidity_reason=None``
      * ``rejection_invariant_id=None``
      * ``lineage_depth=SHALLOW_TRANSFORM``
      * ``upstream_regeneration_delta=()`` (empty — no upstream re-run)
      * ``output_candidate=None`` unless caller explicitly passes one.

    Per self-review fix at S41 close: ``output_candidate`` is optional
    for Tier A. M0_BASE (identity) passes the source; other Tier A
    predicate-only operators (M1-M5, M9) leave it None until Tier A
    materialization is in scope (future work).

    Caller supplies the operator id, source/output family ids, family
    transition policy, and source signature (used to derive variant_id).
    """
    return MutationApplicationResult(
        operator=operator,
        valid=True,
        invalidity_reason=None,
        topology_variant_id=derive_variant_id(operator, source_signature),
        rejection_invariant_id=None,
        source_family_id=source_family_id,
        output_family_id=output_family_id,
        family_transition_policy=family_transition_policy,
        lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
        upstream_regeneration_delta=(),
        output_candidate=output_candidate,
    )


def build_invalid_result(
    *,
    operator: MutationOperator,
    source_family_id: str,
    family_transition_policy: TopologyFamilyTransitionPolicy,
    invalidity_reason: str,
    rejection_invariant_id: Optional[str],
) -> MutationApplicationResult:
    """Construct a rejected ``MutationApplicationResult``.

    ``rejection_invariant_id`` carries the upstream rule's owner-prefixed
    id (e.g., ``"C7.staircase_clearance"``, ``"C8.entry_approach"``) when
    a registered predicate rejected the proposal. It is ``None`` when
    rejection comes from an operator-internal pre-condition failure
    (e.g., M4 with ``has_corridor=False``) — that case still produces a
    per-candidate invalid result, but no upstream rule fired.

    Tier A invalid results still carry SHALLOW_TRANSFORM lineage_depth
    (the lineage refers to the *attempt depth*, not the validity).
    """
    return MutationApplicationResult(
        operator=operator,
        valid=False,
        invalidity_reason=invalidity_reason,
        topology_variant_id=None,
        rejection_invariant_id=rejection_invariant_id,
        source_family_id=source_family_id,
        output_family_id=None,
        family_transition_policy=family_transition_policy,
        lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
        upstream_regeneration_delta=(),
    )


# =============================================================================
# Predicate dispatch helper
# =============================================================================


def dispatch_predicates(
    operator: MutationOperator,
    predicate_arguments: Mapping[tuple[str, str], tuple[tuple, dict]],
) -> tuple[bool, Optional[str], Optional[str]]:
    """Walk ``operator``'s § 3.4 predicates and short-circuit on the
    first failure.

    Args:
        operator: the operator dispatching its predicates.
        predicate_arguments: a mapping
            ``(rule_owner, rule_id) → (positional_args, keyword_args)``
            — supplied by the caller for each predicate the operator
            registers. Stub predicates (C9/C10) accept any args; the
            caller may pass ``((), {})`` to be explicit.

    Returns:
        ``(True, None, None)`` if all predicates pass.
        ``(False, reason, "<owner>.<id>")`` on the first failure, where
        ``reason`` is the predicate's human-readable failure string and
        the third element is the rejection_invariant_id.

    Predicates run in registry order (per the matrix declaration).
    Order is deterministic — important for replay tests.
    """
    for rule_owner, rule_id in predicate_ids_for(operator):
        predicate = lookup_predicate(rule_owner, rule_id)
        args, kwargs = predicate_arguments.get((rule_owner, rule_id), ((), {}))
        ok, reason = predicate._predicate_fn(*args, **kwargs)
        if not ok:
            return (False, reason, f"{rule_owner}.{rule_id}")
    return (True, None, None)


# =============================================================================
# Pre-condition helper (used by operators that need fields from context)
# =============================================================================


def require_field(
    context: TierAOperatorContext,
    field: str,
    operator_id: str,
) -> Any:
    """Read ``context.<field>`` and raise OperatorPreconditionError if None.

    Used by operators to assert that the fields they need are populated
    in the context. Centralised here so every operator emits a
    consistent message format ("operator <X> requires <field> in
    context; was None").
    """
    value = getattr(context, field, None)
    if value is None:
        raise OperatorPreconditionError(
            f"operator {operator_id} requires context.{field} to be "
            f"set; was None. (Sub-2 operator pre-conditions are "
            f"populated by Sub-4's orchestrator from the source "
            f"candidate's ancestry; tests must construct the context "
            f"explicitly.)"
        )
    return value


__all__ = [
    "OperatorPreconditionError",
    "TierAOperatorContext",
    "derive_variant_id",
    "build_valid_result",
    "build_invalid_result",
    "dispatch_predicates",
    "require_field",
]
