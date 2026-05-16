"""
BuildemUp — Component 11b — Phase 3 provenance assembly
=========================================================

Per SPEC v1.1 LOCKED § 3 Phase 3 + § 2.1 schema additions
v0.4 + v0.5 + v0.6 W5-18.

Populates:
- ``environment_fingerprint`` (v1.0 carried, v0.4 + v0.7 fields)
- ``master_seed`` (v0.4 D-PR-1)
- ``per_topology_wallclock_seconds`` (v0.4 D-TO-1, cache_relevant per v0.5)
- ``evaluator_skip_cap_fraction`` (v0.4 D-EV-3, cache_relevant per v0.5)
- ``skipped_multifloor_count`` (v0.5 W4-1-tel)
- ``resolved_objective_count`` (v0.6 W5-18; replaces v0.5 always-True bool)
- ``per_topology_telemetry`` (v0.5 W4-3-tel)

This module is INTENTIONALLY KEPT SEPARATE from ``phase2.py`` per
Ramalingam's S42 directive: B-C11B-PROVENANCE-SPLIT (HIGH priority)
will split this assembly into three independently-versioned
dataclasses; isolating provenance work here makes that future split
a refactor, not a rewrite.
"""
from __future__ import annotations

from buildemup.components.c11b.config import LocalRefinementConfig
from buildemup.components.c11b.environment_fingerprint import (
    EnvironmentFingerprint,
)
from buildemup.components.c11b.evaluator import EvaluatorProtocol
from buildemup.components.c11b.phase1 import _PerTopologyResult
from buildemup.components.c11b.provenance import LocalRefinementProvenance
from buildemup.components.c11b.versioning import C11B_VERSION


def assemble_provenance(
    *,
    environment_fingerprint: EnvironmentFingerprint,
    config: LocalRefinementConfig,
    evaluator: EvaluatorProtocol,
    batch_size: int,
    accepted_count: int,
    skipped_multifloor_count: int,
    timed_out_topology_count: int,
    failed_topology_count: int,
    per_topology_results: tuple[_PerTopologyResult, ...],
    failure_summaries: tuple[str, ...],
) -> LocalRefinementProvenance:
    """Build the provenance record at batch close."""
    # Resolve objective count: take the first non-zero count from the
    # per-topology results. (v0.6 W5-18: int actual count, not bool.)
    resolved_objective_count = 0
    for ptr in per_topology_results:
        if ptr.resolved_objective_count > 0:
            resolved_objective_count = ptr.resolved_objective_count
            break

    telemetry = tuple(ptr.telemetry for ptr in per_topology_results)

    return LocalRefinementProvenance(
        environment_fingerprint=environment_fingerprint,
        master_seed=config.master_seed,
        c11b_version=C11B_VERSION,
        per_topology_wallclock_seconds=config.per_topology_wallclock_seconds,
        evaluator_skip_cap_fraction=config.evaluator_skip_cap_fraction,
        evaluator_signature=evaluator.signature(),
        batch_size=batch_size,
        accepted_count=accepted_count,
        skipped_multifloor_count=skipped_multifloor_count,
        timed_out_topology_count=timed_out_topology_count,
        failed_topology_count=failed_topology_count,
        resolved_objective_count=resolved_objective_count,
        per_topology_telemetry=telemetry,
        failure_summaries=failure_summaries,
    )


__all__ = [
    "assemble_provenance",
]
