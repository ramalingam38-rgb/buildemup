"""
BuildemUp — Component 11b — NSGA-II subpackage
================================================

Per SPEC v1.1 LOCKED:
- § 0.10 ``DominanceSorterProtocol`` scope clarification
- § 0.7.1 deterministic tie-break (W5-12 precomputed + W6-3 versioned)
- § 0.5 NSGA-II 3-objective regime + future NSGA-III migration trigger
  (B-NEW-V5)

Per Ramalingam's S42 directive: the tie-break / selection / fingerprint
trio is split across versioning.py / tiebreak.py / selection.py so the
W6-3 fix stays auditable at a glance — never collapse them into a
single nsga2_core.py.
"""
from __future__ import annotations

from buildemup.components.c11b.nsga2.crowding import (
    assign_crowding_distance,
)
from buildemup.components.c11b.nsga2.dominance import (
    StandardDominanceSorter,
    dominates_cdp,
    fast_non_dominated_sort,
)
from buildemup.components.c11b.nsga2.operators import (
    polynomial_mutation,
    sbx_crossover,
)
from buildemup.components.c11b.nsga2.selection import (
    _tiebreak_key,
    select_survivors,
)


__all__ = [
    "StandardDominanceSorter",
    "dominates_cdp",
    "fast_non_dominated_sort",
    "assign_crowding_distance",
    "_tiebreak_key",
    "select_survivors",
    "sbx_crossover",
    "polynomial_mutation",
]
