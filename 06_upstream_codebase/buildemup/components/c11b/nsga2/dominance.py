"""
BuildemUp — Component 11b — NSGA-II dominance + non-dominated sort
====================================================================

Per SPEC v1.1 LOCKED § 0.10 (DominanceSorterProtocol scope) +
§ 4 invariants 23-29 + § 0.5 (3-objective regime).

NSGA-II-CDP (Constrained Dominance Principle): a feasible candidate
dominates an infeasible one regardless of objective values; among two
infeasible candidates the lower ``constraint_violations`` dominates.

``fast_non_dominated_sort`` is the textbook Deb et al. 2002 O(M·N²)
algorithm (M = objectives, N = pop). For pop_size=100 this is fast
enough at v1; B-C11B-TIER2-SCALING (Bashir 2025 ND-trees) is the
deferred replacement for N≥1000.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11b.schema import ObjectiveVector, RefinedCandidate


def _objective_values(ov: ObjectiveVector) -> tuple[float, ...]:
    """Extract the bare float tuple from an ObjectiveVector for
    dominance comparison."""
    return tuple(v for _, v in ov.values)


def dominates_cdp(a: RefinedCandidate, b: RefinedCandidate) -> bool:
    """NSGA-II-CDP dominance:

    1. If both feasible (constraint_violations == 0): standard Pareto
       dominance — ``a`` dominates ``b`` iff a is no worse in every
       objective AND strictly better in at least one (lower = better).
    2. If exactly one is feasible: the feasible one dominates.
    3. If both infeasible: the one with lower constraint_violations
       dominates (strict).

    Returns True iff ``a`` dominates ``b``.
    """
    if a.objective_vector is None or b.objective_vector is None:
        # Cannot compare candidates whose evaluator hasn't run.
        return False

    a_cv = a.objective_vector.constraint_violations
    b_cv = b.objective_vector.constraint_violations
    a_feas = a_cv == 0.0
    b_feas = b_cv == 0.0

    if a_feas and not b_feas:
        return True
    if not a_feas and b_feas:
        return False
    if not a_feas and not b_feas:
        # Both infeasible — lower violations dominates.
        return a_cv < b_cv

    # Both feasible — standard Pareto.
    a_vals = _objective_values(a.objective_vector)
    b_vals = _objective_values(b.objective_vector)
    if len(a_vals) != len(b_vals):
        # Mismatched objective counts — neither dominates (defensive).
        return False
    no_worse = all(av <= bv for av, bv in zip(a_vals, b_vals))
    strictly_better = any(av < bv for av, bv in zip(a_vals, b_vals))
    return no_worse and strictly_better


def fast_non_dominated_sort(
    population: tuple[RefinedCandidate, ...],
) -> tuple[tuple[int, ...], ...]:
    """Textbook Deb et al. 2002 fast non-dominated sort. O(M·N²).

    Returns a tuple of fronts; each front is a tuple of indices into
    ``population``. Front 0 is the non-dominated (best) front.
    """
    n = len(population)
    domination_count = [0] * n  # number of solutions dominating i
    dominated_by: list[list[int]] = [[] for _ in range(n)]
    fronts: list[list[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates_cdp(population[p], population[q]):
                dominated_by[p].append(q)
            elif dominates_cdp(population[q], population[p]):
                domination_count[p] += 1
        if domination_count[p] == 0:
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front: list[int] = []
        for p in fronts[i]:
            for q in dominated_by[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    # Drop the trailing empty front.
    while fronts and not fronts[-1]:
        fronts.pop()

    return tuple(tuple(f) for f in fronts)


class StandardDominanceSorter:
    """Default DominanceSorterProtocol implementation — wraps
    ``fast_non_dominated_sort`` with the protocol surface."""

    def sort(
        self, population: tuple[Any, ...]
    ) -> tuple[tuple[int, ...], ...]:
        return fast_non_dominated_sort(tuple(population))


__all__ = [
    "dominates_cdp",
    "fast_non_dominated_sort",
    "StandardDominanceSorter",
]
