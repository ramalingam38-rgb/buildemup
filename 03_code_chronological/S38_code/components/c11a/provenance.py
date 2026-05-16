"""
BuildemUp — Component 11a: Topology Mutation Layer — provenance + result
=========================================================================

Per SPEC § 2.3 (MutatedTopologyCandidate), § 2.4 (provenance),
§ 2.9 (QuarantineFingerprint integration).

This module defines the OUTPUT data types of `mutate_topologies()`:
- `TopologyMutationProvenance`: per-batch metadata + diagnostic trail
- `MutatedTopologyCandidate`: the unit returned from C11a per accepted
  mutation candidate (one operator application per candidate at v1)

Sub-session 1 scope: schema only. The runtime function that constructs
these (`mutate_topologies()`) lands at Sub-session 2+.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationDiagnostics,
    MutationOperator,
    QuarantineFingerprint,
)

if TYPE_CHECKING:
    # Avoid circular import at runtime; only used for type hints.
    from buildemup.components.c10.schema import WetZonePlannedCandidate


# =============================================================================
# § 2.4 / § 2.9 — TopologyMutationProvenance
# =============================================================================


@dataclass(frozen=True)
class TopologyMutationProvenance:
    """SPEC § 2.4 — per-batch provenance + diagnostics.

    Every batch invocation of `mutate_topologies()` produces ONE
    provenance record shared across all accepted MutatedTopologyCandidates
    in that batch. (Per-candidate operator-specific data lives on
    MutatedTopologyCandidate.application_results.)

    `_observational_runtime_ms` is intentionally underscore-prefixed
    to mark it excluded from canonical-serialize replay hashes —
    runtime varies between machines / cold cache / process load and
    cannot participate in deterministic replay.

    `quarantine_fingerprint` (NEW v0.5 § 2.9): captures which operators
    were quarantined at startup. Inv 29 — replays with mismatching
    fingerprints are REJECTED.

    Note: type hints in this module are forward-ref strings for
    `WetZonePlannedCandidate` to avoid C10 → C11a circular import at
    module load. C10 imports nothing from C11a.
    """
    derived_at: float                                              # POSIX timestamp; informational
    plot_analysis_trace_id: str                                    # carried from upstream brief
    floor_label: str                                               # "ground" | "first" | etc
    enabled_operators_snapshot: tuple[str, ...]                    # MutationOperator.value strings
    operator_application_log: tuple[MutationApplicationResult, ...]
    accepted_count: int
    rejected_count: int
    deduplicated_count: int
    truncated_at_max_seeds: bool
    diagnostics: MutationDiagnostics
    rule_trace: tuple[str, ...]                                    # ordered audit-trail entries
    quarantine_fingerprint: QuarantineFingerprint                  # NEW v0.5 § 2.9
    _observational_runtime_ms: int = 0                             # excluded from replay hashes


# =============================================================================
# § 2.3 — MutatedTopologyCandidate (output unit)
# =============================================================================


@dataclass(frozen=True)
class MutatedTopologyCandidate:
    """SPEC § 2.3 — output unit of `mutate_topologies()`.

    REVISED v0.2 with composition-future-proof tuples:
    `applied_operators` is a tuple even though v1 invariant is len==1
    (single operator per output). Multi-operator composition is
    deferred to B-NEW-B post-launch. The dataclass shape is forward-
    compatible.

    `topology_variant_id` is a deterministic identifier derived from
    the source candidate's identity + the applied operator(s). Used
    for deduplication (per `config.deduplicate_by_signature`) and
    cache lookup (Tier B).

    Fields:
      - source_candidate: the input WetZonePlannedCandidate this
        mutation was applied to
      - applied_operators: tuple of MutationOperator entries; len==1 at v1
      - topology_variant_id: deterministic id (hash of source +
        operator + cache-relevant config)
      - application_results: per-operator outcome records; len==1 at v1
      - provenance: SHARED across the batch — every output candidate
        from one mutate_topologies() call carries the same provenance
        instance (frozen dataclasses are hashable; sharing is safe)
    """
    source_candidate: "WetZonePlannedCandidate"
    applied_operators: tuple[MutationOperator, ...]    # v1 invariant: len==1
    topology_variant_id: str
    application_results: tuple[MutationApplicationResult, ...]    # v1: len==1
    provenance: TopologyMutationProvenance

    def __post_init__(self) -> None:
        # v1 invariant — multi-operator composition deferred to B-NEW-B.
        # Carrying the check at the schema layer means callers cannot
        # accidentally produce composition-shaped outputs at v1.
        if len(self.applied_operators) != 1:
            raise ValueError(
                f"v1 requires exactly 1 operator per output; "
                f"got {len(self.applied_operators)}. Multi-operator "
                f"composition deferred to B-NEW-B."
            )
        if len(self.application_results) != 1:
            raise ValueError(
                f"v1 requires exactly 1 application_result per output; "
                f"got {len(self.application_results)}. Multi-operator "
                f"composition deferred to B-NEW-B."
            )
        # The single applied_operator MUST match the result's operator.
        op = self.applied_operators[0]
        result_op = self.application_results[0].operator
        if op != result_op:
            raise ValueError(
                f"Inconsistent MutatedTopologyCandidate: applied_operators[0]="
                f"{op.value} but application_results[0].operator="
                f"{result_op.value}"
            )


__all__ = [
    "TopologyMutationProvenance",
    "MutatedTopologyCandidate",
]
