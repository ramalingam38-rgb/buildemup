"""
BuildemUp — Component 11b — Phase 2 output assembly
=====================================================

Per SPEC v1.1 LOCKED § 3 Phase 2 (REVISED v0.4 + v0.5 + v0.6):

Each ``RefinedCandidate`` carries the three capability flags
``(geometry_materialized, placement_safe, requires_transform_resolution)``
derived from C11a operator metadata per the worked-example table in
§ 0.3.1. Output ordering is diversity-order per Inv 23
(``output_sequence_is_quality_ranked == False`` at v1).

Phase 2 is a thin assembly step at v1 — the heavy lifting (rank +
crowding + tie-break) happens in Phase 1's NSGA-II loop via
``select_survivors``. This module exists to mark the architectural
seam for future expansion (B-NEW-V3 alternative ordering strategies,
B-C11B-DOERR-TIEBREAK frequency-based tie-break).
"""
from __future__ import annotations

from buildemup.components.c11b.phase1 import _PerTopologyResult
from buildemup.components.c11b.schema import RefinedCandidate


def assemble_refined_candidates(
    per_topology_results: tuple[_PerTopologyResult, ...],
) -> tuple[RefinedCandidate, ...]:
    """Concatenate per-topology Pareto-ordered slices into the batch
    output. Order across topologies is the input topology order; within
    each topology the order is NSGA-II diversity (rank+crowding+tiebreak).

    Inv 23 (carried v1.0 § 0.9): every emitted candidate has
    ``output_sequence_is_quality_ranked == False`` (enforced in
    ``RefinedCandidate.__post_init__``).
    """
    out: list[RefinedCandidate] = []
    for ptr in per_topology_results:
        out.extend(ptr.refined_candidates)
    return tuple(out)


__all__ = [
    "assemble_refined_candidates",
]
