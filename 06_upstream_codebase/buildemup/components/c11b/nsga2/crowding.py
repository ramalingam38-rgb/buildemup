"""
BuildemUp — Component 11b — NSGA-II crowding distance
=======================================================

Per SPEC v1.1 LOCKED § 0.10 (CDP-scoped — crowding stays hardcoded
at v1; see DominanceSorterProtocol scope clarification).

Crowding distance is the textbook Deb et al. 2002 procedure: for each
objective, sort the front by that objective; extremes get +inf;
intermediate candidates get the normalized neighbour-spread contribution
summed across all objectives.

Mutating the input candidates is not appropriate (they're frozen
dataclasses); instead this function returns a list of (index,
crowding_distance) pairs that the caller applies via dataclass
reconstruction.
"""
from __future__ import annotations

import math

from buildemup.components.c11b.schema import ObjectiveVector, RefinedCandidate


def _objective_values(ov: ObjectiveVector) -> tuple[float, ...]:
    return tuple(v for _, v in ov.values)


def assign_crowding_distance(
    population: tuple[RefinedCandidate, ...],
    front_indices: tuple[int, ...],
) -> dict[int, float]:
    """Compute crowding distance for each index in ``front_indices``.

    Returns a dict mapping index → crowding_distance. Extremes get
    +inf; degenerate fronts (size ≤ 2) get all +inf.
    """
    if not front_indices:
        return {}
    if len(front_indices) <= 2:
        return {idx: math.inf for idx in front_indices}

    distances: dict[int, float] = {idx: 0.0 for idx in front_indices}

    # We need at least one populated objective vector to know how many
    # objectives we have. Defensive: any None gets distance 0.
    first = population[front_indices[0]].objective_vector
    if first is None:
        return {idx: 0.0 for idx in front_indices}
    n_objectives = len(first.values)

    for m in range(n_objectives):
        # Sort front indices by m-th objective.
        sorted_indices = sorted(
            front_indices,
            key=lambda i, m=m: (
                _objective_values(population[i].objective_vector)[m]
                if population[i].objective_vector is not None
                else 0.0
            ),
        )
        # Extremes get +inf.
        distances[sorted_indices[0]] = math.inf
        distances[sorted_indices[-1]] = math.inf

        # Normalization range.
        f_min = _objective_values(population[sorted_indices[0]].objective_vector)[m]
        f_max = _objective_values(population[sorted_indices[-1]].objective_vector)[m]
        f_range = f_max - f_min
        if f_range <= 0.0:
            # Degenerate objective — skip.
            continue

        for k in range(1, len(sorted_indices) - 1):
            prev_idx = sorted_indices[k - 1]
            next_idx = sorted_indices[k + 1]
            cur_idx = sorted_indices[k]
            if math.isinf(distances[cur_idx]):
                continue
            prev_val = _objective_values(
                population[prev_idx].objective_vector
            )[m]
            next_val = _objective_values(
                population[next_idx].objective_vector
            )[m]
            distances[cur_idx] += (next_val - prev_val) / f_range

    return distances


__all__ = [
    "assign_crowding_distance",
]
