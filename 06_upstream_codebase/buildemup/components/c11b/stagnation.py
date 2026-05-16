"""
BuildemUp — Component 11b — stagnation detection
==================================================

Per SPEC v1.1 LOCKED § 0.8 (REVISED v0.3; carried v0.4-v0.7).

Inv 25: stagnation cost bounded. Full O(N²) check max once per
``full_signature_every_n_gens`` (default 5); per-gen check is O(N)
centroid variance. Worst case for pop=100 / max_gen=100:
~200,000 ops total.

Convergence triggers iff composite hash repeats for
``convergence_stable_gens`` consecutive FULL-signature gens.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from buildemup.components.c11b.config import StagnationConfig
from buildemup.components.c11b.schema import RefinedCandidate


@dataclass(frozen=True)
class StagnationSignature:
    """Composite signature returned by stagnation checks.

    ``composite_hash`` is a stable string; consecutive equal values
    across full-signature gens indicate stagnation.
    """
    composite_hash: str
    metric_used: Literal["pairwise_distance", "centroid_variance"]
    gen_index: int


def _flatten_dims(c: RefinedCandidate) -> tuple[float, ...]:
    out: list[float] = []
    for rd in c.refined_parameters.room_dimensions:
        out.append(rd.width_m)
        out.append(rd.depth_m)
    return tuple(out)


def _centroid_variance_hash(
    population: tuple[RefinedCandidate, ...], gen_index: int
) -> str:
    """O(N · R · 2) centroid-variance hash."""
    if not population:
        return "empty"
    n = len(population)
    flat = [_flatten_dims(c) for c in population]
    dims = len(flat[0]) if flat else 0
    if dims == 0:
        return hashlib.sha256(f"{gen_index}|empty-dims".encode()).hexdigest()[:16]
    centroid = [sum(fv[i] for fv in flat) / n for i in range(dims)]
    variance = sum(
        sum((fv[i] - centroid[i]) ** 2 for fv in flat) / n for i in range(dims)
    )
    # Round to 6 dp for stability (matches CANONICAL_FP_PRECISION).
    payload = f"{gen_index}|cv|{round(variance, 6)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _pairwise_distance_hash(
    population: tuple[RefinedCandidate, ...], gen_index: int
) -> str:
    """O(N² · R · 2) pairwise-distance hash. Full check."""
    if not population:
        return "empty"
    flat = [_flatten_dims(c) for c in population]
    n = len(flat)
    dims = len(flat[0]) if flat else 0
    total = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(dims):
                total += (flat[i][k] - flat[j][k]) ** 2
    payload = f"{gen_index}|pw|{round(total, 6)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def compute_stagnation_signature_lite(
    population: tuple[RefinedCandidate, ...],
    gen_index: int,
    config: StagnationConfig,
) -> StagnationSignature:
    """Adaptive cadence per § 0.8: cheap centroid-variance every gen;
    full pairwise every Nth gen.
    """
    if (
        config.full_signature_every_n_gens > 0
        and gen_index % config.full_signature_every_n_gens == 0
    ):
        return StagnationSignature(
            composite_hash=_pairwise_distance_hash(population, gen_index),
            metric_used="pairwise_distance",
            gen_index=gen_index,
        )
    if not config.centroid_variance_per_gen:
        # Skip cheap check; return a unique non-matching hash so
        # no false stagnation can trigger.
        return StagnationSignature(
            composite_hash=f"skip-{gen_index}",
            metric_used="centroid_variance",
            gen_index=gen_index,
        )
    return StagnationSignature(
        composite_hash=_centroid_variance_hash(population, gen_index),
        metric_used="centroid_variance",
        gen_index=gen_index,
    )


__all__ = [
    "StagnationSignature",
    "compute_stagnation_signature_lite",
]
