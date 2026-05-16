"""
BuildemUp — Component 11a — Tier A operators (Sub-session 2)
=============================================================

Per CODING_MANDATE Step 2 Sub-session 2.

Sub-session 2 ships **SHALLOW** (Tier A) operators only:

  * M0_BASE       — identity (always-valid base)
  * M1_HORIZ_FLIP — horizontal flip
  * M2_VERT_FLIP  — vertical flip
  * M3a/b/c       — staircase repositioning (E / W / NE corner)
  * M4_CORRIDOR   — corridor inversion (TRANSFORMS_FAMILY)
  * M5_ZONE_SWAP  — public/private zone swap (TRANSFORMS_FAMILY)
  * M9a/b/c/d     — entry repositioning (NE region variants)

Tier B operators (M6/M7/M8) ship at Sub-session 3.

Per Q2 (S39 open): operators return ``MutationApplicationResult``
**only**. The deeply-mutated downstream candidate is constructed by
the orchestrator (Sub-session 4). At Sub-2 the operator's job is to:

  1. Construct the proposed change (a small in-memory delta — e.g.,
     a new Staircase footprint for M3, new zone_bands for M5).
  2. Dispatch its applicable § 3.4 predicates against the proposal.
  3. Return a valid ``MutationApplicationResult`` if all pass, or an
     invalid one (carrying ``rejection_invariant_id``) if any fails.

This keeps Sub-2 testable in isolation: tests can construct ad-hoc
``TierAOperatorContext`` fixtures with the exact upstream slice each
operator reads, without wiring full upstream pipeline state.
"""
from __future__ import annotations

# Re-export the operator entry points for convenient import from
# ``buildemup.components.c11a.operators``.

from buildemup.components.c11a.operators._base import (
    OperatorPreconditionError,
    TierAOperatorContext,
    build_invalid_result,
    build_valid_result,
    derive_variant_id,
    dispatch_predicates,
)
from buildemup.components.c11a.operators._tier_b_base import (
    apply_tier_b_operator,
)
from buildemup.components.c11a.operators.m0_base import apply_m0_base
from buildemup.components.c11a.operators.m1_horiz_flip import apply_m1_horiz_flip
from buildemup.components.c11a.operators.m2_vert_flip import apply_m2_vert_flip
from buildemup.components.c11a.operators.m3a_stair_east import apply_m3a_stair_east
from buildemup.components.c11a.operators.m3b_stair_west import apply_m3b_stair_west
from buildemup.components.c11a.operators.m3c_stair_ne import apply_m3c_stair_ne
from buildemup.components.c11a.operators.m4_corridor_inv import apply_m4_corridor_inv
from buildemup.components.c11a.operators.m5_zone_swap import apply_m5_zone_swap
from buildemup.components.c11a.operators.m6_wet_rotate import apply_m6_wet_rotate
from buildemup.components.c11a.operators.m7a_grid_3_3 import apply_m7a_grid_3_3
from buildemup.components.c11a.operators.m7b_grid_2_7 import apply_m7b_grid_2_7
from buildemup.components.c11a.operators.m8_vert_rearr import apply_m8_vert_rearr
from buildemup.components.c11a.operators.m9a_entry_ne_center import apply_m9a_entry_ne_center
from buildemup.components.c11a.operators.m9b_entry_ne_corner_w import apply_m9b_entry_ne_corner_w
from buildemup.components.c11a.operators.m9c_entry_ne_corner_e import apply_m9c_entry_ne_corner_e
from buildemup.components.c11a.operators.m9d_entry_offset_ne import apply_m9d_entry_offset_ne


# Dispatch table — operator → apply function. Sub-4's orchestrator
# reads this; tests use it for parametric coverage.
TIER_A_DISPATCH = {
    # The keys reference MutationOperator enum members; importing the
    # enum here would create a thicker module API; see
    # ``operator_metadata.OPERATOR_METADATA`` for the canonical
    # operator → metadata table. The dispatch table below is keyed by
    # the .value strings to keep this module's surface lean.
}


__all__ = [
    # base
    "OperatorPreconditionError",
    "TierAOperatorContext",
    "build_invalid_result",
    "build_valid_result",
    "derive_variant_id",
    "dispatch_predicates",
    "apply_tier_b_operator",
    # operator entry points
    "apply_m0_base",
    "apply_m1_horiz_flip",
    "apply_m2_vert_flip",
    "apply_m3a_stair_east",
    "apply_m3b_stair_west",
    "apply_m3c_stair_ne",
    "apply_m4_corridor_inv",
    "apply_m5_zone_swap",
    "apply_m6_wet_rotate",
    "apply_m7a_grid_3_3",
    "apply_m7b_grid_2_7",
    "apply_m8_vert_rearr",
    "apply_m9a_entry_ne_center",
    "apply_m9b_entry_ne_corner_w",
    "apply_m9c_entry_ne_corner_e",
    "apply_m9d_entry_offset_ne",
]
