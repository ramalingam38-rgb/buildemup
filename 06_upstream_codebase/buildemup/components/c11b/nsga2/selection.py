"""
BuildemUp — Component 11b — NSGA-II survivor selection + tie-break
====================================================================

Per SPEC v1.1 LOCKED § 0.7.1 (deterministic tie-break, REVISED v0.6
W5-12 + v0.7 W6-3) + § 4 Inv 29 (TIER-1 byte-equal under full
conjunction).

Survivor selection picks ``pop_size`` candidates from the union of
parents + offspring:

1. Rank-then-crowding: assign Pareto rank via ``fast_non_dominated_sort``;
   inside each front compute crowding distance; sort by (rank, -crowding).
2. When candidates tie on BOTH (rank, crowding_distance), apply the
   § 0.7.1 lex-ASC tie-break composite key:

       (source_topology_candidate_signature,
        tiebreak_fingerprint,        # W5-12 precomputed at construction
        candidate_index)             # insertion order; layer 3 fallback

Layer 2 uses the precomputed ``RefinedCandidate.tiebreak_fingerprint``
(W6-3 version-anchored). NO per-sort re-hashing — the precompute is the
whole point of the W5-12 optimization.

Layer 3 (``candidate_index``) is single-threaded-safe at v1.
B-NEW-Z (deterministic-parallel-NSGA-II) will replace this with a
candidate UUID / structural hash / ancestry lineage id.
"""
from __future__ import annotations

import math
from dataclasses import replace

from buildemup.components.c11b.nsga2.crowding import assign_crowding_distance
from buildemup.components.c11b.nsga2.dominance import fast_non_dominated_sort
from buildemup.components.c11b.schema import RefinedCandidate


def _tiebreak_key(
    candidate: RefinedCandidate, candidate_index: int
) -> tuple[str, int, int]:
    """Lex-ASC tie-break for NSGA-II survivor selection per Inv 29.

    Composite key:
      1. ``source_topology_candidate_signature`` (deterministic from
         the source artifact via C11a's ``derive_canonical_signature``)
      2. ``tiebreak_fingerprint`` (precomputed 64-bit int per v0.6
         W5-12 + v0.7 W6-3 version-anchored)
      3. ``candidate_index`` (insertion order; single-threaded-safe at v1)
    """
    return (
        candidate.source_topology_candidate_signature,
        candidate.tiebreak_fingerprint,
        candidate_index,
    )


def select_survivors(
    combined_population: tuple[RefinedCandidate, ...],
    pop_size: int,
) -> tuple[RefinedCandidate, ...]:
    """Select ``pop_size`` survivors from the combined parent+offspring
    pool via NSGA-II rank + crowding + deterministic tie-break.

    Returns a tuple of ``RefinedCandidate``s with ``pareto_rank`` and
    ``crowding_distance`` populated (via ``dataclasses.replace``).
    Length is exactly ``min(pop_size, len(combined_population))``.
    """
    if not combined_population:
        return ()

    # 1. Non-dominated sort.
    fronts = fast_non_dominated_sort(combined_population)

    # 2. Crowding within each front + populate pareto_rank.
    ranked_indices: list[tuple[int, int, float]] = []
    # ranked_indices: list of (candidate_index_in_combined, rank, crowding)

    for rank, front in enumerate(fronts):
        if not front:
            continue
        crowding = assign_crowding_distance(combined_population, front)
        for idx in front:
            ranked_indices.append((idx, rank, crowding[idx]))

    # 3. Sort lex-ASC by (rank, -crowding, tiebreak_key).
    #    Note: we want HIGHER crowding to win (more diverse), so we
    #    negate. Inf becomes -inf which sorts before finite values.
    def _sort_key(entry: tuple[int, int, float]) -> tuple:
        idx, rank, crowd = entry
        # neg_crowd handling: inf → -inf (sorts first); other → -crowd.
        if math.isinf(crowd) and crowd > 0:
            neg_crowd = float("-inf")
        else:
            neg_crowd = -crowd
        tb = _tiebreak_key(combined_population[idx], idx)
        return (rank, neg_crowd, *tb)

    ranked_indices.sort(key=_sort_key)

    # 4. Take the first pop_size; reconstruct RefinedCandidates with
    #    rank + crowding populated.
    keep = ranked_indices[:pop_size]
    out: list[RefinedCandidate] = []
    for idx, rank, crowd in keep:
        # crowding_distance is a float; +inf is preserved.
        cand = combined_population[idx]
        out.append(replace(cand, pareto_rank=rank, crowding_distance=crowd))
    return tuple(out)


__all__ = [
    "_tiebreak_key",
    "select_survivors",
]
