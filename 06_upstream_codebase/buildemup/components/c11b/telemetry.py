"""
BuildemUp — Component 11b — per-topology telemetry
=====================================================

Per SPEC v1.1 LOCKED § 2.1 (W4-3 telemetry addition).

KEPT IN A SEPARATE FILE per Ramalingam's S42 directive: "Starting with
separate telemetry.py (PerTopologyTelemetry) and phase3.py (provenance
assembly) makes that future split [B-C11B-PROVENANCE-SPLIT] a refactor,
not a rewrite."

When B-C11B-PROVENANCE-SPLIT fires (when provenance schema growth blocks
safe version increment), this telemetry block becomes one of the three
split dataclasses: ``OperationalTelemetry``. Today's structure is
designed to make that move trivial.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerTopologyTelemetry:
    """Per-topology diagnostic block carried inside
    ``LocalRefinementProvenance.per_topology_telemetry``.

    Fields per spec § 2.1:
    - ``topology_index``: position in the input batch.
    - ``completed_generations``: how many NSGA-II generations ran
      before exit (timeout, stagnation, or max).
    - ``longest_generation_seconds`` (NEW v0.5 W4-3): wall-clock
      duration of the slowest generation. Surfaces tail-latency
      stragglers approaching but not breaching
      ``per_topology_wallclock_seconds``.
    - ``skipped_candidates_total`` (NEW v0.5): sum of per-generation
      skip counts (Inv 28) for this topology.
    """
    topology_index: int
    completed_generations: int
    longest_generation_seconds: float
    skipped_candidates_total: int


__all__ = [
    "PerTopologyTelemetry",
]
