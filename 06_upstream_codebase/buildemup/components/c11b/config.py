"""
BuildemUp — Component 11b — LocalRefinementConfig + supporting enums
=====================================================================

Per SPEC v1.1 LOCKED § 2.2 (REVISED v0.4 + v0.5):

- v1.0 carried fields (pop_size, max_generations, crossover/mutation
  rates, SBX/polynomial etas, output size, convergence gens,
  multiplier, init retries, permutations_per_candidate,
  stagnation_config, evaluator_cache_max_memory_mb, enforcement_mode,
  provenance_verbosity, evaluator_cache_enabled,
  dominance_sorter_factory)
- v0.4 additions: ``per_topology_wallclock_seconds``, ``master_seed``,
  ``evaluator_skip_cap_fraction``
- v0.5 cache_relevant FLIPS (W4-4, W4-5):
  - ``per_topology_wallclock_seconds.cache_relevant``: False → True
  - ``evaluator_skip_cap_fraction.cache_relevant``: False → True

PARTITION SENTINEL (v0.5 baseline):
- Carried v1.0 cache_relevant: pop_size, max_generations, crossover_rate,
  mutation_rate, sbx_eta_c, polynomial_eta_m, pareto_output_size,
  convergence_stable_gens, universal_max_multiplier, init_max_retries,
  permutations_per_candidate, stagnation_config → 12 fields
- v0.4 + v0.5 additions (all cache_relevant=True):
  per_topology_wallclock_seconds, master_seed,
  evaluator_skip_cap_fraction → 3 fields
- TOTAL cache_relevant: 15
- cache_irrelevant: evaluator_cache_max_memory_mb, enforcement_mode,
  provenance_verbosity, evaluator_cache_enabled, dominance_sorter_factory
  → 5
- Total fields: 20
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol


# =============================================================================
# EnforcementMode + ProvenanceVerbosity (carried v1.0)
# =============================================================================


class EnforcementMode(str, enum.Enum):
    """Per § 0.4 + § 5 — controls how PerTopologyError propagates.

    - STRICT: any per-topology failure halts the batch via
      ``BatchAllTopologiesFailedError`` aggregation.
    - WARN (default): per-topology failures aggregate; batch returns
      whatever succeeded; only halts if EVERY topology failed.
    """
    STRICT = "strict"
    WARN = "warn"


class ProvenanceVerbosity(str, enum.Enum):
    """Per F-v5-6 PATCH-NOW: only ``SUMMARY``, ``PER_OP``, ``PER_GEN``,
    ``FULL`` exist — v0.5 draft initially said PER_TOPOLOGY which is
    not a v1.0 enum member."""
    SUMMARY = "summary"
    PER_OP = "per_op"
    PER_GEN = "per_gen"
    FULL = "full"


# =============================================================================
# § 0.10 — DominanceSorterProtocol (v0.3 scope-clarified; carried)
# =============================================================================


class DominanceSorterProtocol(Protocol):
    """v0.3 scope clarification:

    Abstracts NON-DOMINATED SORTING ONLY. Does NOT abstract:
      - Diversity semantics (crowding distance hardcoded at v1)
      - Survivor selection (NSGA-II rank+crowding hardcoded at v1)
      - Tie-breaking (lex-ASC composite key hardcoded at v1)

    Replacing the sorter (e.g., Jensen fast sort) is safe. Replacing
    the *algorithm family* (e.g., MOEA/D, NSGA-III) requires
    additional protocol abstractions (B-NEW-V5 if needed post-launch).
    """

    def sort(self, population: tuple[Any, ...]) -> tuple[tuple[int, ...], ...]:
        """Return Pareto fronts as a tuple of tuples-of-indices into
        ``population``. Front 0 is the best (non-dominated front)."""
        ...


# =============================================================================
# § 0.8 — StagnationConfig (NEW v0.3, carried)
# =============================================================================


@dataclass(frozen=True)
class StagnationConfig:
    """NEW v0.3 — explicit cost knobs for stagnation detection."""
    full_signature_every_n_gens: int = 5
    centroid_variance_per_gen: bool = True
    diversity_metric: Literal["pairwise_distance", "centroid_variance"] = (
        "centroid_variance"
    )


# =============================================================================
# § 2.2 — LocalRefinementConfig (REVISED v0.4 + v0.5)
# =============================================================================


# Lazy import for the default factory below (avoid circular import on
# nsga2/dominance at module load).
def _default_dominance_sorter_factory() -> DominanceSorterProtocol:
    from buildemup.components.c11b.nsga2.dominance import StandardDominanceSorter

    return StandardDominanceSorter()


@dataclass(frozen=True)
class LocalRefinementConfig:
    """The C11b runtime config.

    All cache_relevant=True fields participate in the cache key root
    (paired with ``EnvironmentFingerprint``). cache_relevant=False
    fields are operational toggles that do NOT affect output identity.

    v0.5 W4-4 + W4-5 corrected the cache_relevant flags on
    ``per_topology_wallclock_seconds`` (timeout-truncated outputs differ
    from completed runs) and ``evaluator_skip_cap_fraction`` (different
    caps → different surviving populations → different Pareto fronts).
    """
    # ── v1.0 carried cache_relevant fields ────────────────────────────
    pop_size: int = field(default=100, metadata={"cache_relevant": True})
    max_generations: int = field(default=100, metadata={"cache_relevant": True})
    crossover_rate: float = field(default=0.9, metadata={"cache_relevant": True})
    mutation_rate: float = field(default=0.1, metadata={"cache_relevant": True})
    sbx_eta_c: float = field(default=20.0, metadata={"cache_relevant": True})
    polynomial_eta_m: float = field(default=20.0, metadata={"cache_relevant": True})
    pareto_output_size: int = field(default=20, metadata={"cache_relevant": True})
    convergence_stable_gens: int = field(default=5, metadata={"cache_relevant": True})
    universal_max_multiplier: float = field(
        default=2.5, metadata={"cache_relevant": True}
    )
    init_max_retries: int = field(default=100, metadata={"cache_relevant": True})
    permutations_per_candidate: int = field(
        default=3, metadata={"cache_relevant": True}
    )
    stagnation_config: StagnationConfig = field(
        default_factory=StagnationConfig, metadata={"cache_relevant": True}
    )

    # ── NEW v0.4 + v0.5 cache_relevant fields ────────────────────────
    per_topology_wallclock_seconds: float = field(
        default=30.0,
        metadata={"cache_relevant": True},  # v0.5 W4-5 PATCH-NOW
    )
    master_seed: int = field(
        default=0xC11B5EED,
        metadata={"cache_relevant": True},  # NEW v0.4 D-PR-1
    )
    evaluator_skip_cap_fraction: float = field(
        default=0.25,
        metadata={"cache_relevant": True},  # v0.5 W4-4 PATCH-NOW
    )

    # ── cache_irrelevant operational toggles ─────────────────────────
    evaluator_cache_max_memory_mb: int = field(
        default=512, metadata={"cache_relevant": False}
    )
    enforcement_mode: EnforcementMode = field(
        default=EnforcementMode.WARN, metadata={"cache_relevant": False}
    )
    provenance_verbosity: ProvenanceVerbosity = field(
        default=ProvenanceVerbosity.PER_GEN, metadata={"cache_relevant": False}
    )
    evaluator_cache_enabled: bool = field(
        default=True, metadata={"cache_relevant": False}
    )
    dominance_sorter_factory: Callable[[], DominanceSorterProtocol] = field(
        default=_default_dominance_sorter_factory,
        metadata={"cache_relevant": False},
    )


def cache_relevant_field_names(config_cls: type) -> tuple[str, ...]:
    """Return the names of fields with ``metadata['cache_relevant'] is
    True`` in declaration order. Used by the partition sentinel test
    + cache-key derivation."""
    import dataclasses

    return tuple(
        f.name
        for f in dataclasses.fields(config_cls)
        if f.metadata.get("cache_relevant") is True
    )


def cache_irrelevant_field_names(config_cls: type) -> tuple[str, ...]:
    """Mirror of ``cache_relevant_field_names`` for cache_relevant=False."""
    import dataclasses

    return tuple(
        f.name
        for f in dataclasses.fields(config_cls)
        if f.metadata.get("cache_relevant") is False
    )


__all__ = [
    "EnforcementMode",
    "ProvenanceVerbosity",
    "DominanceSorterProtocol",
    "StagnationConfig",
    "LocalRefinementConfig",
    "cache_relevant_field_names",
    "cache_irrelevant_field_names",
]
