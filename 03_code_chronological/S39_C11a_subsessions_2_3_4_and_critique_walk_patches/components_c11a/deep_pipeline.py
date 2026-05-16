"""
BuildemUp — Component 11a — Tier B DeepMutationPipeline (Sub-session 3)
==========================================================================

Per spec § 3.5: Tier B execution path. For each (source candidate,
Tier B operator) pair the pipeline:

  Step 0: cache lookup (DeepMutationCacheKey)            — § 0.3
  Step 1: build operator's input mutation                — operator-specific
  Step 2-4: call upstream (C7 if M7, then C9, then C10)  — via
           ``UpstreamRegenerator`` protocol (DI for testability;
           Sub-4 wires real C7/C9/C10)
  Step 5: validate upstream invariants on output         — implicit;
           upstream functions raise on violation
  Step 5b: compute actual_delta_keys + classify_lineage  — § 2.3 + Inv 21/23
           (REJECT if forbidden; EMERGENT_REGEN otherwise)
  Step 6: cache result; return                            — § 0.3

Atomicity (Inv 17): each step produces a new immutable object; on
any failure the pipeline raises ``DeepMutationApplicationError``
without leaking partial state. Cache only stores fully-formed results.

Severity-tier catch routing (§ 2.7 + F-v2-7):
  * KBVersionMismatchError, RemediationGraphError,
    PlumbingConfidenceTooLow → propagate UNCAUGHT (systemic)
  * BatchWetZoneInfeasibleError → caught, wrapped, candidate rejected
  * Per-candidate errors (severity_tier="per_candidate") → caught,
    wrapped, candidate rejected

The catch logic uses each error's ``severity_tier`` ClassVar (per
B-NEW-P v1.0 LOCKED, S38) — no hardcoded type lists.

Sub-session 3 ships the pipeline + a ``StubUpstreamRegenerator`` for
unit tests. Sub-session 4 wires the real upstream by implementing
``UpstreamRegenerator`` against actual C7/C9/C10 entry points.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from buildemup.components.c11a.cache import (
    DeepMutationCacheKey,
    derive_cache_key,
)
from buildemup.components.c11a.errors import (
    DeepMutationApplicationError,
    TopologyMutationError,
)
from buildemup.components.c11a.lineage import (
    LineageClassification,
    classify_lineage_depth,
)
from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.schema import (
    DeltaKey,
    MutationLineageDepth,
    MutationOperator,
    MutationTier,
    TopologyMutationConfig,
)


# =============================================================================
# TierBInputMutation — operator-specific input delta
# =============================================================================


@dataclass(frozen=True)
class TierBInputMutation:
    """Operator-specific description of what to change in upstream
    inputs before re-running C7/C9/C10.

    Sub-3 keeps this loose at the schema level — each Tier B operator
    populates the fields it needs and leaves others as None. Sub-4's
    UpstreamRegenerator wiring reads only the fields relevant to the
    operator's family (e.g., M7 reads new_grid_bay_size_m; M6 reads
    new_wet_wall_assignment_direction).

    Carrying it as a single frozen struct (rather than per-family
    subclasses) keeps the pipeline's internal API uniform.
    """

    operator: MutationOperator
    # M6 (wet-wall rotate) — new direction for the wet wall assignment.
    new_wet_wall_assignment_direction: Optional[str] = None
    # M7a/b (grid scale) — new bay dimensions in metres.
    new_grid_bay_x_m: Optional[float] = None
    new_grid_bay_y_m: Optional[float] = None
    # M8 (vertical rearrange) — new master-bedroom floor label.
    new_master_bedroom_floor_label: Optional[str] = None


# =============================================================================
# DeepMutationPipelineResult — pipeline-internal verdict
# =============================================================================


@dataclass(frozen=True)
class DeepMutationPipelineResult:
    """The pipeline's outcome for one (source, operator) attempt.

    Carries everything the wrapping ``apply_<m6/7/8>()`` function needs
    to populate a ``MutationApplicationResult``. The pipeline does NOT
    construct ``MutationApplicationResult`` directly — keeping lineage
    structuring at this level lets the wrapper assemble source/output
    family ids and delegate cache writing.
    """

    valid: bool
    regenerated_candidate: Optional[Any]                    # WetZonePlannedCandidate or None
    lineage_depth: Optional[MutationLineageDepth]
    upstream_regeneration_delta: tuple[DeltaKey, ...]
    invalidity_reason: Optional[str]
    rejection_invariant_id: Optional[str]
    cache_hit: bool = False                                  # True iff served from cache


# =============================================================================
# UpstreamRegenerator Protocol
# =============================================================================


@runtime_checkable
class UpstreamRegenerator(Protocol):
    """Sub-3 dependency-injection surface for Tier B upstream calls.

    Sub-4 wires the real implementation against C7.GridGenerator.generate,
    C9.size_rooms, C10.plan_wet_zones with operator-specific input
    mutation. Sub-3 tests use ``StubUpstreamRegenerator`` to drive the
    pipeline through happy / per-candidate-fail / systemic-fail paths
    without standing up full upstream pipeline state.

    The protocol is INTENTIONALLY narrow:
      * regenerate(source, mutation, operator) → new candidate
      * compute_delta(source, regenerated, operator) → DeltaKey tuple

    Errors are raised; severity-tier classification on the call-site
    routes catch behaviour. The protocol does not own catch logic.
    """

    def regenerate(
        self,
        source: Any,                                # WetZonePlannedCandidate
        mutation: TierBInputMutation,
        operator: MutationOperator,
    ) -> Any:                                       # WetZonePlannedCandidate
        """Re-run upstream components with ``mutation`` applied.

        Raises on failure. The pipeline's catch logic routes via each
        exception's ``severity_tier`` ClassVar:
          * 'systemic' → propagates uncaught
          * 'batch' / 'per_candidate' → caught, wrapped as
            DeepMutationApplicationError, candidate rejected
        """
        ...

    def compute_delta(
        self,
        source: Any,                                # WetZonePlannedCandidate
        regenerated: Any,                           # WetZonePlannedCandidate
        operator: MutationOperator,
    ) -> tuple[DeltaKey, ...]:
        """Walk source vs regenerated state; return the DeltaKey tuple
        of fields that changed. Used by classify_lineage_depth().
        """
        ...


# =============================================================================
# StubUpstreamRegenerator — Sub-3 test double
# =============================================================================


class StubUpstreamRegenerator:
    """Test stub. Tests configure outcomes; pipeline drives through.

    Configure via:
      * ``return_value``: regenerated candidate to emit on regenerate()
      * ``raise_on_regenerate``: exception to raise (severity tested
        via pipeline's catch routing)
      * ``delta_keys``: tuple of DeltaKey values to emit on compute_delta()

    Defaults: regenerate() returns the source unchanged; compute_delta()
    returns the operator's expected_delta keys (regenerative-transform
    happy path).
    """

    def __init__(
        self,
        *,
        return_value: Any = None,
        raise_on_regenerate: Optional[BaseException] = None,
        delta_keys: Optional[tuple[DeltaKey, ...]] = None,
    ) -> None:
        self.return_value = return_value
        self.raise_on_regenerate = raise_on_regenerate
        self.delta_keys = delta_keys
        # Call records — useful for tests asserting cache behaviour.
        self.regenerate_call_count = 0
        self.compute_delta_call_count = 0

    def regenerate(self, source, mutation, operator):
        self.regenerate_call_count += 1
        if self.raise_on_regenerate is not None:
            raise self.raise_on_regenerate
        if self.return_value is not None:
            return self.return_value
        # Default: identity — return source unchanged. Callers wanting
        # operator-driven mutations override return_value.
        return source

    def compute_delta(self, source, regenerated, operator):
        self.compute_delta_call_count += 1
        if self.delta_keys is not None:
            return self.delta_keys
        # Default: emit the operator's expected keys → regenerative-
        # transform happy path.
        md = OPERATOR_METADATA[operator]
        return tuple(sorted(md.expected_delta_schema.expected, key=lambda k: k.value))


# =============================================================================
# DeepMutationPipeline
# =============================================================================


@dataclass
class DeepMutationPipeline:
    """Per-batch Tier B pipeline. Holds the cache map for the duration
    of one ``mutate_topologies()`` invocation.

    Per Inv 30 (single-threaded contract): pipeline instances MUST NOT
    be shared across threads or invocations. Sub-4's orchestrator
    constructs a fresh pipeline per batch; Sub-3 tests construct one
    per test.

    Attributes:
      upstream:    UpstreamRegenerator protocol implementation
      cache:       in-memory map DeepMutationCacheKey → result
      cache_hits:  observational counter (reset per batch)
      cache_misses: observational counter
      cache_enabled: per-batch flag (mirrors config.deep_mutation_cache_enabled)
    """

    upstream: UpstreamRegenerator
    cache: dict[DeepMutationCacheKey, DeepMutationPipelineResult] = field(
        default_factory=dict
    )
    cache_hits: int = 0
    cache_misses: int = 0
    cache_enabled: bool = True

    # =========================================================================
    # Public entry point
    # =========================================================================

    def apply(
        self,
        *,
        source: Any,                                       # WetZonePlannedCandidate
        operator: MutationOperator,
        mutation: TierBInputMutation,
        config: TopologyMutationConfig,
        source_signature: str,
    ) -> DeepMutationPipelineResult:
        """Apply ``operator`` to ``source`` via the Tier B pipeline.

        Args:
            source: source WetZonePlannedCandidate (opaque to the
                pipeline; passed through to the upstream regenerator).
            operator: a Tier B operator (REGENERATIVE tier).
            mutation: operator-specific input mutation built by the
                operator's apply_*() wrapper.
            config: TopologyMutationConfig (read for cache hashing +
                deep_mutation_cache_enabled flag).
            source_signature: deterministic identity hash of source.

        Returns:
            ``DeepMutationPipelineResult``. Caller wraps into a
            ``MutationApplicationResult``.

        Raises:
            ValueError: if ``operator`` is not REGENERATIVE-tier.
            <Systemic upstream errors>: propagated UNCAUGHT per § 2.7.
        """
        # Tier guard.
        op_tier = OPERATOR_METADATA[operator].tier
        if op_tier != MutationTier.REGENERATIVE:
            raise ValueError(
                f"DeepMutationPipeline.apply() requires a REGENERATIVE "
                f"operator; got {operator.value} (tier={op_tier.value})."
            )

        # Step 0 — cache lookup.
        cache_key = derive_cache_key(operator, source_signature, config)

        if self.cache_enabled and cache_key in self.cache:
            cached = self.cache[cache_key]
            self.cache_hits += 1
            # Re-tag as cache_hit=True (immutable; reconstruct).
            return DeepMutationPipelineResult(
                valid=cached.valid,
                regenerated_candidate=cached.regenerated_candidate,
                lineage_depth=cached.lineage_depth,
                upstream_regeneration_delta=cached.upstream_regeneration_delta,
                invalidity_reason=cached.invalidity_reason,
                rejection_invariant_id=cached.rejection_invariant_id,
                cache_hit=True,
            )

        self.cache_misses += 1

        # Step 1-4 — upstream regeneration.
        try:
            regenerated = self.upstream.regenerate(source, mutation, operator)
        except BaseException as exc:
            severity = _severity_of(exc)
            if severity == "systemic":
                # Propagate UNCAUGHT — batch-wide infrastructure failure.
                raise
            # Per-candidate or batch — wrap and reject.
            wrapped = DeepMutationApplicationError(
                f"Tier B regeneration failed for operator {operator.value}: "
                f"{type(exc).__name__}: {exc}",
                wrapped_exception=exc,
                upstream_component=_infer_upstream_component(operator),
            )
            result = DeepMutationPipelineResult(
                valid=False,
                regenerated_candidate=None,
                lineage_depth=None,
                upstream_regeneration_delta=(),
                invalidity_reason=str(wrapped),
                rejection_invariant_id=None,
                cache_hit=False,
            )
            if self.cache_enabled:
                self.cache[cache_key] = result
            return result

        # Step 5b — compute delta + classify lineage.
        try:
            actual_delta = self.upstream.compute_delta(
                source, regenerated, operator,
            )
        except BaseException as exc:
            # Delta computation failure is per-candidate scope.
            severity = _severity_of(exc)
            if severity == "systemic":
                raise
            result = DeepMutationPipelineResult(
                valid=False,
                regenerated_candidate=None,
                lineage_depth=None,
                upstream_regeneration_delta=(),
                invalidity_reason=(
                    f"Tier B delta computation failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
                rejection_invariant_id=None,
                cache_hit=False,
            )
            if self.cache_enabled:
                self.cache[cache_key] = result
            return result

        schema = OPERATOR_METADATA[operator].expected_delta_schema
        classification = classify_lineage_depth(actual_delta, schema)

        # Forbidden hit → REJECT.
        if classification.lineage_depth is None:
            forbidden_keys_str = ",".join(
                k.value for k in classification.rejected_by_keys
            )
            result = DeepMutationPipelineResult(
                valid=False,
                regenerated_candidate=None,
                lineage_depth=None,
                upstream_regeneration_delta=tuple(actual_delta),
                invalidity_reason=classification.rejection_reason,
                rejection_invariant_id=(
                    f"C11a.forbidden_delta_key:{forbidden_keys_str}"
                ),
                cache_hit=False,
            )
            if self.cache_enabled:
                self.cache[cache_key] = result
            return result

        # Step 6 — cache + return.
        result = DeepMutationPipelineResult(
            valid=True,
            regenerated_candidate=regenerated,
            lineage_depth=classification.lineage_depth,
            upstream_regeneration_delta=tuple(actual_delta),
            invalidity_reason=None,
            rejection_invariant_id=None,
            cache_hit=False,
        )
        if self.cache_enabled:
            self.cache[cache_key] = result
        return result


# =============================================================================
# Internal helpers — severity routing
# =============================================================================


def _severity_of(exc: BaseException) -> str:
    """Read ``severity_tier`` ClassVar from ``exc``'s class.

    Per § 2.7 / B-NEW-P (S38): every C7/C9/C10/C11a error carries a
    ``severity_tier`` ClassVar with one of {'per_candidate', 'batch',
    'systemic'}. Missing or unknown → defensive 'systemic' (per
    F-v4-5: fail closed; Phase 0 startup audit catches the missing
    classification at module load time so this fallback is rarely
    exercised in production).
    """
    tier = getattr(type(exc), "severity_tier", None)
    if tier in ("per_candidate", "batch", "systemic"):
        return tier
    return "systemic"


def _infer_upstream_component(operator: MutationOperator) -> str:
    """Best-effort label of which upstream component drove the regen
    failure. M6/M7 → C7+C8+C9+C10; M8 → C9+C10. Used only for the
    DeepMutationApplicationError label."""
    if operator in (MutationOperator.M7A_GRID_3_3, MutationOperator.M7B_GRID_2_7):
        return "C7+C8+C9+C10"
    if operator == MutationOperator.M6_WET_ROTATE:
        return "C10"
    if operator == MutationOperator.M8_VERT_REARR:
        return "C9+C10"
    return "upstream"


__all__ = [
    "TierBInputMutation",
    "DeepMutationPipelineResult",
    "UpstreamRegenerator",
    "StubUpstreamRegenerator",
    "DeepMutationPipeline",
]
