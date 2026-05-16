"""
BuildemUp — Component 11b — feasibility-aware initialization
==============================================================

Per SPEC v1.1 LOCKED § 0.7 (REVISED v0.3, carried v0.4-v0.7).

v0.3 ``permutations_per_candidate=3``: for each candidate slot, sample
3 random room orderings; run sequential allocation with each; pick the
most area-balanced result (lowest variance of room_area / room_min_area).
Reduces allocation-order bias.

Determinism: fully reproducible via the per-topology ``rng``.

KB-driven Dirichlet allocation (literature-preferred, Zhang et al. 2024)
is filed as B-NEW-V4 post-launch.

The init produces ``RefinedParameters`` (parameter vectors only). The
``RefinedCandidate`` wrappers are assembled in ``phase1.py`` after
operator-class derivation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from buildemup.components.c11b.bounds import derive_room_upper_bounds
from buildemup.components.c11b.errors import AreaInfeasiblePopulationError
from buildemup.components.c11b.schema import RefinedParameters, RoomDimension


@dataclass(frozen=True)
class RoomSizeRequirement:
    """Per-room dimension floor + category (for SEMANTIC_CAP lookup).

    Built from upstream brief data (FloorRoomBrief + WetZonePlannedCandidate
    room_size_table). Stored sorted by room_id at construction.
    """
    room_id: str
    category: str
    min_width_m: float
    min_depth_m: float

    def __post_init__(self) -> None:
        if self.min_width_m <= 0 or self.min_depth_m <= 0:
            raise ValueError(
                f"RoomSizeRequirement {self.room_id} needs positive mins"
            )


def _sequential_allocate(
    requirements: tuple[RoomSizeRequirement, ...],
    envelope_w: float,
    envelope_d: float,
    rng: np.random.Generator,
    *,
    universal_max_multiplier: float = 2.5,
) -> RefinedParameters | None:
    """One pass of sequential allocation: visit rooms in given order,
    pick a width/depth within bounds via uniform sampling, return
    ``RefinedParameters`` if feasible (sum of areas ≤ envelope), else
    None.
    """
    total_min_area = sum(r.min_width_m * r.min_depth_m for r in requirements)
    envelope_area = envelope_w * envelope_d
    if total_min_area > envelope_area:
        return None  # Infeasible at the floor.

    assigned: list[RoomDimension] = []
    other_mins = list(total_min_area for _ in requirements)
    for i, r in enumerate(requirements):
        # Other rooms' min area = total_min_area - this room's own min.
        own_min = r.min_width_m * r.min_depth_m
        others_min = total_min_area - own_min
        upper_w, upper_d = derive_room_upper_bounds(
            r.room_id,
            r.category,
            r.min_width_m,
            r.min_depth_m,
            envelope_w,
            envelope_d,
            others_min,
            universal_max_multiplier=universal_max_multiplier,
        )
        # Uniform sample within [min, upper].
        w = rng.uniform(r.min_width_m, max(r.min_width_m, upper_w))
        d = rng.uniform(r.min_depth_m, max(r.min_depth_m, upper_d))
        assigned.append(RoomDimension(room_id=r.room_id, width_m=w, depth_m=d))
        _ = other_mins  # unused; kept for future Dirichlet path

    # Sort by room_id for canonical ordering.
    assigned.sort(key=lambda rd: rd.room_id)
    rp = RefinedParameters(room_dimensions=tuple(assigned))

    # Final area feasibility check.
    total = sum(rd.width_m * rd.depth_m for rd in assigned)
    if total > envelope_area:
        return None
    return rp


def _balance_score(rp: RefinedParameters, requirements: tuple[RoomSizeRequirement, ...]) -> float:
    """Variance of room_area / room_min_area across the plan; lower is
    more balanced."""
    req_by_id = {r.room_id: r for r in requirements}
    ratios = []
    for rd in rp.room_dimensions:
        req = req_by_id.get(rd.room_id)
        if req is None:
            continue
        min_area = req.min_width_m * req.min_depth_m
        if min_area <= 0:
            continue
        ratios.append((rd.width_m * rd.depth_m) / min_area)
    if not ratios:
        return float("inf")
    mean_r = sum(ratios) / len(ratios)
    return sum((r - mean_r) ** 2 for r in ratios) / len(ratios)


def feasibility_aware_init(
    requirements: tuple[RoomSizeRequirement, ...],
    envelope_w: float,
    envelope_d: float,
    rng: np.random.Generator,
    *,
    pop_size: int,
    permutations_per_candidate: int = 3,
    init_max_retries: int = 100,
    universal_max_multiplier: float = 2.5,
) -> tuple[RefinedParameters, ...]:
    """v0.3: multiple permutations per candidate.

    For each slot, sample up to ``init_max_retries`` * ``permutations``
    candidate orderings, run sequential allocation, pick the most
    area-balanced result. If we cannot fill ``pop_size``, raise
    ``AreaInfeasiblePopulationError``.
    """
    if not requirements:
        return ()

    population: list[RefinedParameters] = []
    for slot in range(pop_size):
        best: RefinedParameters | None = None
        best_score = float("inf")
        for attempt in range(init_max_retries):
            # For each candidate, try ``permutations_per_candidate`` orderings.
            for _ in range(permutations_per_candidate):
                permuted = list(requirements)
                rng.shuffle(permuted)
                cand = _sequential_allocate(
                    tuple(permuted),
                    envelope_w,
                    envelope_d,
                    rng,
                    universal_max_multiplier=universal_max_multiplier,
                )
                if cand is None:
                    continue
                score = _balance_score(cand, requirements)
                if score < best_score:
                    best, best_score = cand, score
            if best is not None:
                break
        if best is None:
            raise AreaInfeasiblePopulationError(
                f"C11b init: slot {slot}/{pop_size} could not produce a "
                f"feasible candidate within {init_max_retries} retries × "
                f"{permutations_per_candidate} permutations. Envelope "
                f"{envelope_w}×{envelope_d} m²; total room min area = "
                f"{sum(r.min_width_m * r.min_depth_m for r in requirements):.2f} m²."
            )
        population.append(best)
    return tuple(population)


__all__ = [
    "RoomSizeRequirement",
    "feasibility_aware_init",
]
