"""
BuildemUp — Component 11b — LocalRefinementProvenance
========================================================

Per SPEC v1.1 LOCKED § 2.1 (carried v1.0 + v0.4/v0.5/v0.6/v0.7 fields).

v0.4 adds: ``master_seed``, ``per_topology_wallclock_seconds``,
``evaluator_skip_cap_fraction``, ``environment_fingerprint`` carried.

v0.5 adds: ``skipped_multifloor_count``, ``per_topology_telemetry``.

v0.6 W5-18 supersedes v0.5: ``resolved_objective_count: int`` (was
``nsga2_objective_count_warning: bool`` which was always True at v1
default — alert fatigue).

KEPT IN A SEPARATE FILE per Ramalingam's S42 directive: future
B-C11B-PROVENANCE-SPLIT (HIGH priority) will split this into
``ReplayProvenance`` + ``OperationalTelemetry`` + ``DiagnosticWarnings``;
isolating provenance assembly into ``phase3.py`` + carrying telemetry
in its own module makes that future split a refactor, not a rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from buildemup.components.c11b.environment_fingerprint import EnvironmentFingerprint
from buildemup.components.c11b.telemetry import PerTopologyTelemetry


@dataclass(frozen=True)
class LocalRefinementProvenance:
    """Per-batch provenance for ``run_local_refinement``.

    Captures the env tuple + config knobs that determined output
    identity (TIER-1 byte-equal replay requires same fingerprint +
    same config). Also carries v0.5+ telemetry / diagnostic counters.
    """
    # Replay-critical fields (TIER-1 surface per § 0.0c).
    environment_fingerprint: EnvironmentFingerprint
    master_seed: int  # v0.4 D-PR-1
    c11b_version: str  # captured for downstream readers
    per_topology_wallclock_seconds: float  # v0.4 D-TO-1 (cache_relevant per v0.5)
    evaluator_skip_cap_fraction: float  # v0.4 D-EV-3 (cache_relevant per v0.5)

    # Evaluator + counters.
    evaluator_signature: str
    batch_size: int
    accepted_count: int
    skipped_multifloor_count: int  # v0.5 W4-1-tel (Item 1)
    timed_out_topology_count: int  # v0.4 D-TO-3
    failed_topology_count: int

    # v0.6 W5-18: int actual count, NOT bool always-True flag.
    resolved_objective_count: int

    # v0.5 W4-3-tel: per-topology telemetry block.
    per_topology_telemetry: tuple[PerTopologyTelemetry, ...] = field(
        default_factory=tuple
    )

    # Per-topology failure summaries (operator-facing diagnostics).
    failure_summaries: tuple[str, ...] = field(default_factory=tuple)


__all__ = [
    "LocalRefinementProvenance",
]
