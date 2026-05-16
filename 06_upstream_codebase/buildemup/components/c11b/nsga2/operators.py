"""
BuildemUp — Component 11b — NSGA-II genetic operators
========================================================

Standard SBX (Simulated Binary Crossover) and polynomial mutation per
Deb & Agrawal 1995 / Deb 2001. Operate on bare float vectors with
explicit lower/upper bounds; the C11b ``phase1`` orchestrator marshals
``RefinedParameters`` ↔ float vectors around these calls.

Both operators are pure-deterministic given the input + the passed
``numpy.random.Generator``. The Generator is the per-topology PRNG
built via ``_build_per_topology_rng``.
"""
from __future__ import annotations

import numpy as np


def sbx_crossover(
    parent_a: tuple[float, ...],
    parent_b: tuple[float, ...],
    lower: tuple[float, ...],
    upper: tuple[float, ...],
    rng: np.random.Generator,
    *,
    eta_c: float = 20.0,
    crossover_probability: float = 0.9,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Simulated Binary Crossover. Returns (child_a, child_b).

    With probability ``crossover_probability`` per gene, the child genes
    are spread around the parents per the SBX distribution; otherwise
    the genes are copied from the parents.

    Bounds are enforced post-mix via clipping. ``eta_c`` controls the
    distribution sharpness (higher = closer to parents).
    """
    n = len(parent_a)
    assert len(parent_b) == n == len(lower) == len(upper), (
        "SBX requires matched-length parents + bounds."
    )
    child_a = list(parent_a)
    child_b = list(parent_b)
    for i in range(n):
        if rng.random() >= crossover_probability:
            continue
        if abs(parent_a[i] - parent_b[i]) < 1e-14:
            continue
        x1 = min(parent_a[i], parent_b[i])
        x2 = max(parent_a[i], parent_b[i])
        xl, xu = lower[i], upper[i]
        if xu <= xl:
            continue
        rand = rng.random()
        # SBX β derivation.
        beta = 1.0 + (2.0 * (x1 - xl) / (x2 - x1))
        alpha = 2.0 - beta ** -(eta_c + 1.0)
        if rand <= 1.0 / alpha:
            betaq = (rand * alpha) ** (1.0 / (eta_c + 1.0))
        else:
            betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
        c1 = 0.5 * ((x1 + x2) - betaq * (x2 - x1))

        beta = 1.0 + (2.0 * (xu - x2) / (x2 - x1))
        alpha = 2.0 - beta ** -(eta_c + 1.0)
        if rand <= 1.0 / alpha:
            betaq = (rand * alpha) ** (1.0 / (eta_c + 1.0))
        else:
            betaq = (1.0 / (2.0 - rand * alpha)) ** (1.0 / (eta_c + 1.0))
        c2 = 0.5 * ((x1 + x2) + betaq * (x2 - x1))

        c1 = min(max(c1, xl), xu)
        c2 = min(max(c2, xl), xu)
        if rng.random() < 0.5:
            child_a[i], child_b[i] = c2, c1
        else:
            child_a[i], child_b[i] = c1, c2
    return tuple(child_a), tuple(child_b)


def polynomial_mutation(
    parent: tuple[float, ...],
    lower: tuple[float, ...],
    upper: tuple[float, ...],
    rng: np.random.Generator,
    *,
    eta_m: float = 20.0,
    mutation_probability: float | None = None,
) -> tuple[float, ...]:
    """Polynomial mutation. Returns the mutated vector.

    ``mutation_probability`` defaults to ``1/n`` (Deb's standard).
    ``eta_m`` controls perturbation magnitude (higher = closer to
    parent).
    """
    n = len(parent)
    if mutation_probability is None:
        mutation_probability = 1.0 / max(1, n)
    out = list(parent)
    for i in range(n):
        if rng.random() >= mutation_probability:
            continue
        xl, xu = lower[i], upper[i]
        if xu <= xl:
            continue
        y = out[i]
        delta1 = (y - xl) / (xu - xl)
        delta2 = (xu - y) / (xu - xl)
        rand = rng.random()
        mut_pow = 1.0 / (eta_m + 1.0)
        if rand < 0.5:
            xy = 1.0 - delta1
            val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta_m + 1.0))
            deltaq = val**mut_pow - 1.0
        else:
            xy = 1.0 - delta2
            val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta_m + 1.0))
            deltaq = 1.0 - val**mut_pow
        y = y + deltaq * (xu - xl)
        out[i] = min(max(y, xl), xu)
    return tuple(out)


__all__ = [
    "sbx_crossover",
    "polynomial_mutation",
]
