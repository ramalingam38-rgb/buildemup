"""Master-orchestrator adapter glue.

Each component-pair adapter lives in its own module so the surface
stays narrow and unit-testable. Adapters are intentionally pure
functions; the orchestrator pipes data through them without holding
any state.

S57 follow-ups #4/#5/#6 shipped here:
- ``c11b_to_c12``: build C12 SingleFloorPlacementInput from either
  C11b RefinedCandidate (primary path) or C11a MutatedTopologyCandidate
  (fallback used while C11b ships STUB pending #3).
"""
from __future__ import annotations

from buildemup.orchestration.adapters.c11b_to_c12 import (
    adapt_mutated_to_single_floor,
    adapt_refined_to_single_floor,
    build_single_floor_inputs_from_upstream,
)
from buildemup.orchestration.adapters.c12_c13_to_c14 import (
    build_room_metadata_by_signature,
)


__all__ = [
    # C11b/C11a → C12 (follow-up #4)
    "adapt_refined_to_single_floor",
    "adapt_mutated_to_single_floor",
    "build_single_floor_inputs_from_upstream",
    # C12 + C13 → C14 (follow-up #6)
    "build_room_metadata_by_signature",
]
