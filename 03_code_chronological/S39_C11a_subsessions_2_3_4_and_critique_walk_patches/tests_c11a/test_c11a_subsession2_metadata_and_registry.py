"""
C11a Sub-session 2 tests — OPERATOR_METADATA + validate_operator_registry.

Per CODING_MANDATE Step 2 Sub-session 2: the metadata table must
cover all 16 enum operators with type-correct entries; the registry
validator must enforce Inv 26 + Inv 28 at startup.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from buildemup.components.c11a import (
    DeltaKey,
    MutationOperator,
    MutationOperatorFamily,
    MutationOperatorMetadata,
    MutationTier,
    OPERATOR_METADATA,
    OperatorExpectedDeltaSchema,
    OperatorRegistryError,
    TopologyFamilyTransitionPolicy,
    TopologyMutationConfig,
    get_operator_metadata,
    operators_by_family,
    operators_by_tier,
    validate_operator_registry,
)


# =============================================================================
# Coverage — every operator has a metadata entry
# =============================================================================


def test_operator_metadata_covers_all_16_operators() -> None:
    """Every MutationOperator enum member has an entry."""
    enum_members = set(MutationOperator)
    metadata_keys = set(OPERATOR_METADATA.keys())
    assert enum_members == metadata_keys


def test_operator_metadata_has_16_entries() -> None:
    assert len(OPERATOR_METADATA) == 16


def test_get_operator_metadata_returns_metadata_instance() -> None:
    md = get_operator_metadata(MutationOperator.M0_BASE)
    assert isinstance(md, MutationOperatorMetadata)
    assert md.operator == MutationOperator.M0_BASE


# =============================================================================
# Tier coverage
# =============================================================================


def test_operators_by_tier_shallow_count() -> None:
    """Tier A (SHALLOW): M0, M1, M2, M3a/b/c, M4, M5, M9a/b/c/d = 12."""
    shallow = operators_by_tier(MutationTier.SHALLOW)
    assert len(shallow) == 12


def test_operators_by_tier_regenerative_count() -> None:
    """Tier B (REGENERATIVE): M6, M7a, M7b, M8 = 4."""
    regen = operators_by_tier(MutationTier.REGENERATIVE)
    assert len(regen) == 4


def test_tier_partition_is_total() -> None:
    """Every operator is exactly one of SHALLOW/REGENERATIVE."""
    shallow = set(operators_by_tier(MutationTier.SHALLOW))
    regen = set(operators_by_tier(MutationTier.REGENERATIVE))
    assert shallow.isdisjoint(regen)
    assert shallow | regen == set(MutationOperator)


# =============================================================================
# Family coverage
# =============================================================================


def test_operators_by_family_base_singleton() -> None:
    base = operators_by_family(MutationOperatorFamily.BASE)
    assert base == (MutationOperator.M0_BASE,)


def test_operators_by_family_flip_doublet() -> None:
    flip = operators_by_family(MutationOperatorFamily.FLIP)
    assert set(flip) == {MutationOperator.M1_HORIZ_FLIP, MutationOperator.M2_VERT_FLIP}


def test_operators_by_family_staircase_triplet() -> None:
    s = operators_by_family(MutationOperatorFamily.STAIRCASE)
    assert set(s) == {
        MutationOperator.M3A_STAIR_EAST,
        MutationOperator.M3B_STAIR_WEST,
        MutationOperator.M3C_STAIR_NE,
    }


def test_operators_by_family_entry_quartet() -> None:
    e = operators_by_family(MutationOperatorFamily.ENTRY)
    assert set(e) == {
        MutationOperator.M9A_ENTRY_CTR,
        MutationOperator.M9B_ENTRY_W,
        MutationOperator.M9C_ENTRY_E,
        MutationOperator.M9D_ENTRY_OFF,
    }


def test_operators_by_family_grid_doublet() -> None:
    g = operators_by_family(MutationOperatorFamily.GRID)
    assert set(g) == {MutationOperator.M7A_GRID_3_3, MutationOperator.M7B_GRID_2_7}


# =============================================================================
# Per-operator metadata correctness
# =============================================================================


def test_m0_metadata_preserves_family() -> None:
    md = OPERATOR_METADATA[MutationOperator.M0_BASE]
    assert md.tier == MutationTier.SHALLOW
    assert md.family == MutationOperatorFamily.BASE
    assert md.family_transition_policy == TopologyFamilyTransitionPolicy.PRESERVES_FAMILY
    assert md.expected_delta_schema.expected == frozenset()


def test_m4_metadata_transforms_family() -> None:
    """Per W#5 Q22 carry: M4 is TRANSFORMS_FAMILY."""
    md = OPERATOR_METADATA[MutationOperator.M4_CORRIDOR_INV]
    assert md.family_transition_policy == TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY


def test_m5_metadata_transforms_family() -> None:
    md = OPERATOR_METADATA[MutationOperator.M5_ZONE_SWAP]
    assert md.family_transition_policy == TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY


def test_m7_requires_grid_regen() -> None:
    """M7 changes the grid bay size — requires_grid_regen=True."""
    for op in (MutationOperator.M7A_GRID_3_3, MutationOperator.M7B_GRID_2_7):
        assert OPERATOR_METADATA[op].requires_grid_regen is True


def test_m8_requires_multi_floor() -> None:
    md = OPERATOR_METADATA[MutationOperator.M8_VERT_REARR]
    assert md.requires_multi_floor is True


def test_only_m8_requires_multi_floor() -> None:
    """Per § 2.2: only M8 carries requires_multi_floor=True."""
    multi_floor_ops = [
        op for op in MutationOperator
        if OPERATOR_METADATA[op].requires_multi_floor
    ]
    assert multi_floor_ops == [MutationOperator.M8_VERT_REARR]


def test_m1_expected_delta_room_position_x() -> None:
    """Per § 2.2 v0.5 table: M1 expects GEO_ROOM_POSITION_X."""
    md = OPERATOR_METADATA[MutationOperator.M1_HORIZ_FLIP]
    assert md.expected_delta_schema.expected == frozenset(
        {DeltaKey.GEO_ROOM_POSITION_X}
    )
    assert DeltaKey.GEO_ROOM_AREA in md.expected_delta_schema.forbidden


def test_m1_forbids_meta_fixture_types() -> None:
    """Cross-operator invariant: no operator changes fixture-type set.
    META_* keys appear only in forbidden sets per § 2.5 / F-v5-2.
    """
    md = OPERATOR_METADATA[MutationOperator.M1_HORIZ_FLIP]
    assert DeltaKey.META_FIXTURE_TYPES in md.expected_delta_schema.forbidden


def test_m9_expected_delta_entry_position() -> None:
    md = OPERATOR_METADATA[MutationOperator.M9A_ENTRY_CTR]
    assert md.expected_delta_schema.expected == frozenset(
        {DeltaKey.GEO_ENTRY_POSITION}
    )


# =============================================================================
# Tier B operators have plumbing/grid/multifloor delta keys
# =============================================================================


def test_m6_expected_delta_includes_wet_wall_assignment() -> None:
    md = OPERATOR_METADATA[MutationOperator.M6_WET_ROTATE]
    assert DeltaKey.PLUMB_WET_WALL_ASSIGNMENT in md.expected_delta_schema.expected


def test_m7_expected_delta_includes_grid_bay_size() -> None:
    for op in (MutationOperator.M7A_GRID_3_3, MutationOperator.M7B_GRID_2_7):
        md = OPERATOR_METADATA[op]
        assert DeltaKey.GEO_GRID_BAY_SIZE in md.expected_delta_schema.expected


def test_m8_expected_delta_includes_master_br_floor() -> None:
    md = OPERATOR_METADATA[MutationOperator.M8_VERT_REARR]
    assert DeltaKey.MULTI_MASTER_BR_FLOOR in md.expected_delta_schema.expected


# =============================================================================
# validate_operator_registry — happy path
# =============================================================================


def test_validate_operator_registry_passes_at_v1_lock() -> None:
    """At v1.0 LOCK time, the registry is valid by construction."""
    # Should not raise.
    validate_operator_registry()


def test_validate_operator_registry_idempotent() -> None:
    """Calling twice doesn't change state."""
    validate_operator_registry()
    validate_operator_registry()


# =============================================================================
# validate_operator_registry — Inv 28 enforcement
# =============================================================================


def test_inv_28_string_literal_in_expected_raises(monkeypatch: Any) -> None:
    """Inject a malformed metadata entry with a string literal in the
    expected set; the validator must raise OperatorRegistryError.
    """
    bad_schema = OperatorExpectedDeltaSchema(
        expected=frozenset({"not_a_delta_key"}),  # type: ignore[arg-type]
        allowed_secondary=frozenset(),
        forbidden=frozenset(),
    )
    bad_md = MutationOperatorMetadata(
        operator=MutationOperator.M0_BASE,
        tier=MutationTier.SHALLOW,
        family=MutationOperatorFamily.BASE,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        requires_multi_floor=False,
        requires_grid_regen=False,
        expected_delta_schema=bad_schema,
        cache_relevant_config_fields=("enabled_operators",),
    )

    # Patch OPERATOR_METADATA's M0 entry with the bad one.
    from buildemup.components.c11a import operator_metadata as m
    monkeypatch.setattr(
        m, "OPERATOR_METADATA",
        {**m.OPERATOR_METADATA, MutationOperator.M0_BASE: bad_md},
    )
    # Also patch the registry module's view of OPERATOR_METADATA.
    from buildemup.components.c11a import registry as r
    monkeypatch.setattr(
        r, "OPERATOR_METADATA",
        {**OPERATOR_METADATA, MutationOperator.M0_BASE: bad_md},
    )

    with pytest.raises(OperatorRegistryError, match="Inv 28"):
        validate_operator_registry()


# =============================================================================
# validate_operator_registry — coverage enforcement
# =============================================================================


def test_missing_operator_raises(monkeypatch: Any) -> None:
    """If OPERATOR_METADATA is missing an operator, validator raises."""
    from buildemup.components.c11a import registry as r
    incomplete = {
        op: md for op, md in OPERATOR_METADATA.items()
        if op != MutationOperator.M0_BASE
    }
    monkeypatch.setattr(r, "OPERATOR_METADATA", incomplete)

    with pytest.raises(OperatorRegistryError, match="missing entries"):
        validate_operator_registry()


def test_cache_field_unknown_raises(monkeypatch: Any) -> None:
    """If metadata references an unknown TopologyMutationConfig field,
    validator raises."""
    bad_md = dataclasses.replace(
        OPERATOR_METADATA[MutationOperator.M0_BASE],
        cache_relevant_config_fields=("nonexistent_config_field",),
    )
    from buildemup.components.c11a import registry as r
    monkeypatch.setattr(
        r, "OPERATOR_METADATA",
        {**OPERATOR_METADATA, MutationOperator.M0_BASE: bad_md},
    )
    with pytest.raises(OperatorRegistryError, match="cache_relevant_config_fields"):
        validate_operator_registry()


# =============================================================================
# Inv 26 — TopologyMutationConfig field cache_relevant metadata
# =============================================================================


def test_inv_26_all_config_fields_carry_cache_relevant_marker() -> None:
    """Per Inv 26: every TopologyMutationConfig field MUST carry
    metadata['cache_relevant'] as a bool."""
    for f in dataclasses.fields(TopologyMutationConfig):
        assert "cache_relevant" in f.metadata, (
            f"field '{f.name}' missing metadata['cache_relevant']"
        )
        assert isinstance(f.metadata["cache_relevant"], bool)
