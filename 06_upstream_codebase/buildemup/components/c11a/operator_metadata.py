"""
BuildemUp — Component 11a — operator metadata table
=====================================================

Per spec § 2.2 v0.5 — the canonical ``OPERATOR_METADATA`` dict
mapping every ``MutationOperator`` enum entry to its
``MutationOperatorMetadata`` (tier, family, family-transition policy,
multi-floor / grid-regen flags, expected-delta schema, cache-relevant
config fields).

The per-operator delta schemas use ``DeltaKey`` enum values per
Inv 28 (NEW v0.5). String literals in any expected/allowed/forbidden
set raise ``OperatorRegistryError`` at startup via
``validate_operator_registry()``.

Sub-session 2 ships **all 16 operator metadata entries** (Tier A and
Tier B), even though Tier B operator implementations land at
Sub-session 3. The metadata table is logically separate from the
implementations — Sub-3 will register its dispatch wires; the
metadata is canonical now so registry validation has the full
picture.
"""
from __future__ import annotations

from typing import Final, Mapping

from buildemup.components.c11a.schema import (
    DeltaKey,
    MutationOperator,
    MutationOperatorFamily,
    MutationOperatorMetadata,
    MutationTier,
    OperatorExpectedDeltaSchema,
    TopologyFamilyTransitionPolicy,
)


# =============================================================================
# Per-operator delta schemas (§ 2.2 v0.5 table)
# =============================================================================
#
# Sets are frozenset[DeltaKey] — Inv 28 enforces enum-typing at startup
# in registry.py. Each operator declares:
#   * expected:          deltas the mutation IS expected to drive
#   * allowed_secondary: deltas tolerated as side effects
#   * forbidden:         deltas that, if observed, REJECT the candidate
#                        (cross-operator invariants — META_* keys)
#
# At Tier A SHALLOW (M0-M5, M9), operators do not regenerate upstream
# state, so expected/allowed sets are mostly empty or scoped to direct
# mutations. The schemas matter at Tier B (DeepMutationPipeline) where
# upstream-regeneration deltas are computed and classified.

_M0_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset(),
    allowed_secondary=frozenset(),
    forbidden=frozenset(),
)

_M1_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.GEO_ROOM_POSITION_X}),
    allowed_secondary=frozenset({DeltaKey.ADJ_EDGES_ORIENTATION}),
    forbidden=frozenset({DeltaKey.GEO_ROOM_AREA, DeltaKey.META_FIXTURE_TYPES}),
)

_M2_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.GEO_ROOM_POSITION_Y}),
    allowed_secondary=frozenset({DeltaKey.ADJ_EDGES_ORIENTATION}),
    forbidden=frozenset({DeltaKey.GEO_ROOM_AREA}),
)

_M3_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.GEO_STAIRCASE_POSITION}),
    allowed_secondary=frozenset({DeltaKey.CIRC_CORRIDOR_ROUTING}),
    forbidden=frozenset({DeltaKey.META_ROOM_COUNT, DeltaKey.GEO_ROOM_AREA}),
)

_M4_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.CIRC_CORRIDOR_TOPOLOGY}),
    allowed_secondary=frozenset({DeltaKey.ADJ_EDGES, DeltaKey.ZONE_ASSIGNMENTS}),
    forbidden=frozenset({DeltaKey.META_ROOM_COUNT}),
)

_M5_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.ZONE_ASSIGNMENTS}),
    allowed_secondary=frozenset({DeltaKey.ADJ_EDGES, DeltaKey.ZONE_PRIVACY_PATTERN}),
    forbidden=frozenset({DeltaKey.META_ROOM_COUNT}),
)

_M6_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.PLUMB_WET_WALL_ASSIGNMENT}),
    allowed_secondary=frozenset({
        DeltaKey.PLUMB_TRAP_ARM_DISTANCES,
        DeltaKey.PLUMB_RISER_GROUPS,
    }),
    forbidden=frozenset({
        DeltaKey.GEO_ROOM_AREA,
        DeltaKey.GEO_ROOM_POSITION_X,
    }),
)

_M7_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.GEO_GRID_BAY_SIZE, DeltaKey.GEO_ROOM_AREA}),
    allowed_secondary=frozenset({
        DeltaKey.PLUMB_WET_WALL_ASSIGNMENT,
        DeltaKey.PLUMB_TRAP_ARM_DISTANCES,
        DeltaKey.GEO_ROOM_POSITION_X,
        DeltaKey.GEO_ROOM_POSITION_Y,
    }),
    forbidden=frozenset({DeltaKey.META_ROOM_COUNT, DeltaKey.META_FIXTURE_TYPES}),
)

_M8_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({
        DeltaKey.MULTI_MASTER_BR_FLOOR,
        DeltaKey.MULTI_FLOOR_ASSIGNMENT,
    }),
    allowed_secondary=frozenset({DeltaKey.ADJ_EDGES}),
    forbidden=frozenset({DeltaKey.META_ROOM_COUNT, DeltaKey.GEO_ROOM_AREA}),
)

_M9_DELTA = OperatorExpectedDeltaSchema(
    expected=frozenset({DeltaKey.GEO_ENTRY_POSITION}),
    allowed_secondary=frozenset({DeltaKey.CIRC_PRIMARY_PATH}),
    forbidden=frozenset({
        DeltaKey.META_ROOM_COUNT,
        DeltaKey.GEO_ROOM_POSITION_X,
        DeltaKey.GEO_ROOM_POSITION_Y,
    }),
)


# =============================================================================
# Cache-relevant config fields per operator (Inv 26)
# =============================================================================
#
# Per § 2.5 — each operator declares which TopologyMutationConfig
# fields, when changed, change the operator's cache key (i.e.,
# require Tier B cache invalidation). Tier A operators read no
# config-driven knobs at v1 beyond the global cache-relevant
# knobs (enabled_operators, max_seeds_per_input, family_slot_*,
# deterministic_order, emit_base, deduplicate_by_signature). Each
# operator's cache_relevant_config_fields lists which of these its
# behaviour depends on. For Sub-2 simplicity, we treat all Tier A
# operators as identical here — they all participate in
# enabled_operators / family_slot_* / deduplicate_by_signature
# controls. The list MUST consist of TopologyMutationConfig field
# names that carry metadata["cache_relevant"]=True (validated at
# startup by validate_operator_registry()).

_TIER_A_CACHE_FIELDS: Final[tuple[str, ...]] = (
    "enabled_operators",
    "family_slot_allocations",
    "deduplicate_by_signature",
    "deterministic_order",
)

_TIER_B_CACHE_FIELDS: Final[tuple[str, ...]] = (
    "enabled_operators",
    "max_seeds_per_input",
    "family_slot_allocations",
    "deduplicate_by_signature",
    "deterministic_order",
    "emit_base",
)


# =============================================================================
# OPERATOR_METADATA (the canonical table)
# =============================================================================


OPERATOR_METADATA: Final[Mapping[
    MutationOperator, MutationOperatorMetadata,
]] = {
    # ── M0 BASE ────────────────────────────────────────────────────────
    MutationOperator.M0_BASE: MutationOperatorMetadata(
        operator=MutationOperator.M0_BASE,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.BASE,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M0_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),

    # ── M1 / M2 FLIP ───────────────────────────────────────────────────
    MutationOperator.M1_HORIZ_FLIP: MutationOperatorMetadata(
        operator=MutationOperator.M1_HORIZ_FLIP,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.FLIP,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M1_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M2_VERT_FLIP: MutationOperatorMetadata(
        operator=MutationOperator.M2_VERT_FLIP,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.FLIP,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M2_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),

    # ── M3 STAIRCASE ───────────────────────────────────────────────────
    MutationOperator.M3A_STAIR_EAST: MutationOperatorMetadata(
        operator=MutationOperator.M3A_STAIR_EAST,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.STAIRCASE,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M3_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M3B_STAIR_WEST: MutationOperatorMetadata(
        operator=MutationOperator.M3B_STAIR_WEST,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.STAIRCASE,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M3_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M3C_STAIR_NE: MutationOperatorMetadata(
        operator=MutationOperator.M3C_STAIR_NE,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.STAIRCASE,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M3_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),

    # ── M4 CORRIDOR ────────────────────────────────────────────────────
    MutationOperator.M4_CORRIDOR_INV: MutationOperatorMetadata(
        operator=MutationOperator.M4_CORRIDOR_INV,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.CORRIDOR,
        family_transition_policy=TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M4_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),

    # ── M5 ZONE SWAP ───────────────────────────────────────────────────
    MutationOperator.M5_ZONE_SWAP: MutationOperatorMetadata(
        operator=MutationOperator.M5_ZONE_SWAP,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.ZONE,
        family_transition_policy=TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M5_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),

    # ── M6 WET-WALL (Tier B — implementation lands at Sub-3) ───────────
    MutationOperator.M6_WET_ROTATE: MutationOperatorMetadata(
        operator=MutationOperator.M6_WET_ROTATE,
        tier=MutationTier.REGENERATIVE,
        family=MutationOperatorFamily.WET_WALL,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M6_DELTA,
        cache_relevant_config_fields=_TIER_B_CACHE_FIELDS,
    ),

    # ── M7 GRID (Tier B — implementation lands at Sub-3) ───────────────
    MutationOperator.M7A_GRID_3_3: MutationOperatorMetadata(
        operator=MutationOperator.M7A_GRID_3_3,
        tier=MutationTier.REGENERATIVE,
        family=MutationOperatorFamily.GRID,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=True,
        expected_delta_schema=_M7_DELTA,
        cache_relevant_config_fields=_TIER_B_CACHE_FIELDS,
    ),
    MutationOperator.M7B_GRID_2_7: MutationOperatorMetadata(
        operator=MutationOperator.M7B_GRID_2_7,
        tier=MutationTier.REGENERATIVE,
        family=MutationOperatorFamily.GRID,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=True,
        expected_delta_schema=_M7_DELTA,
        cache_relevant_config_fields=_TIER_B_CACHE_FIELDS,
    ),

    # ── M8 VERTICAL REARRANGE (Tier B; multi-floor required) ───────────
    MutationOperator.M8_VERT_REARR: MutationOperatorMetadata(
        operator=MutationOperator.M8_VERT_REARR,
        tier=MutationTier.REGENERATIVE,
        family=MutationOperatorFamily.VERTICAL,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=True,
        requires_grid_regen=False,
        expected_delta_schema=_M8_DELTA,
        cache_relevant_config_fields=_TIER_B_CACHE_FIELDS,
    ),

    # ── M9 ENTRY ───────────────────────────────────────────────────────
    MutationOperator.M9A_ENTRY_CTR: MutationOperatorMetadata(
        operator=MutationOperator.M9A_ENTRY_CTR,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.ENTRY,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M9_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M9B_ENTRY_W: MutationOperatorMetadata(
        operator=MutationOperator.M9B_ENTRY_W,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.ENTRY,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M9_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M9C_ENTRY_E: MutationOperatorMetadata(
        operator=MutationOperator.M9C_ENTRY_E,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.ENTRY,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M9_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
    MutationOperator.M9D_ENTRY_OFF: MutationOperatorMetadata(
        operator=MutationOperator.M9D_ENTRY_OFF,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.ENTRY,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=_M9_DELTA,
        cache_relevant_config_fields=_TIER_A_CACHE_FIELDS,
    ),
}


# =============================================================================
# Helpers
# =============================================================================


def get_operator_metadata(
    operator: MutationOperator,
) -> MutationOperatorMetadata:
    """Look up metadata for ``operator``.

    All 16 enum members have entries — KeyError indicates a programming
    bug, not a runtime condition.
    """
    return OPERATOR_METADATA[operator]


def operators_by_tier(tier: MutationTier) -> tuple[MutationOperator, ...]:
    """Return all operators of a given tier in MutationOperator enum order."""
    return tuple(
        op for op in MutationOperator
        if OPERATOR_METADATA[op].tier == tier
    )


def operators_by_family(
    family: MutationOperatorFamily,
) -> tuple[MutationOperator, ...]:
    """Return all operators of a given family in MutationOperator enum order."""
    return tuple(
        op for op in MutationOperator
        if OPERATOR_METADATA[op].family == family
    )


__all__ = [
    "OPERATOR_METADATA",
    "get_operator_metadata",
    "operators_by_tier",
    "operators_by_family",
]
