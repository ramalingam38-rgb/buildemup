"""
C11a Sub-session 2 tests — family_slot_allocator.

Per spec § 3 Phase 1: per-family slot allocation must be:
  - deterministic (same inputs → same output)
  - reservation-respecting (each family's reserved_slots is the floor)
  - lex-ASC family-order in the output
  - spillover-distributing surplus when sum_reserved < max_seeds
  - truncating in reverse-lex order when sum_reserved > max_seeds
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a import (
    FamilySlotAllocation,
    FamilySlotAssignment,
    MutationOperator,
    MutationOperatorFamily,
    allocate_family_slots,
)


_ALL_OPERATORS = tuple(MutationOperator)


def _all_families_one_each() -> tuple[FamilySlotAllocation, ...]:
    return tuple(
        FamilySlotAllocation(f, 1) for f in MutationOperatorFamily
    )


# =============================================================================
# Result shape
# =============================================================================


def test_result_is_tuple_of_assignments() -> None:
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),
        max_seeds_per_input=8,
    )
    assert isinstance(result, tuple)
    assert all(isinstance(a, FamilySlotAssignment) for a in result)


def test_result_lex_asc_family_order() -> None:
    """Output is in lex-ASC family-value order regardless of input
    allocation order."""
    # Reverse the input allocations.
    reversed_allocations = tuple(
        FamilySlotAllocation(f, 1) for f in reversed(list(MutationOperatorFamily))
    )
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=reversed_allocations,
        max_seeds_per_input=8,
    )
    family_values = [a.family.value for a in result]
    assert family_values == sorted(family_values)


def test_result_returns_all_9_families() -> None:
    """Even families with 0 reserved or 0 enabled-ops appear in the
    output (with slot_count=0). Caller can iterate uniformly."""
    result = allocate_family_slots(
        enabled_operators=(MutationOperator.M0_BASE,),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
        ),
        max_seeds_per_input=8,
    )
    assert len(result) == 9
    family_set = {a.family for a in result}
    assert family_set == set(MutationOperatorFamily)


# =============================================================================
# Determinism
# =============================================================================


def test_allocator_is_deterministic_across_calls() -> None:
    """Same inputs → byte-equal output (replay determinism)."""
    inputs = dict(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),
        max_seeds_per_input=12,
    )
    a = allocate_family_slots(**inputs)
    b = allocate_family_slots(**inputs)
    assert a == b


def test_allocator_invariant_to_input_allocation_order() -> None:
    """Reordering family_slot_allocations input doesn't change output."""
    forward = _all_families_one_each()
    backward = tuple(reversed(forward))
    a = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=forward,
        max_seeds_per_input=8,
    )
    b = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=backward,
        max_seeds_per_input=8,
    )
    assert a == b


# =============================================================================
# Reservation respecting
# =============================================================================


def test_reserved_slots_at_or_below_max_are_honoured() -> None:
    """Each family's reserved_slots is the FLOOR (achieved when
    enabled-ops cap allows)."""
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.STAIRCASE, 3),
            FamilySlotAllocation(MutationOperatorFamily.ENTRY, 4),
        ),
        max_seeds_per_input=16,
    )
    by_family = {a.family: a.slot_count for a in result}
    assert by_family[MutationOperatorFamily.STAIRCASE] >= 3
    assert by_family[MutationOperatorFamily.ENTRY] >= 4


def test_reserved_slots_capped_at_enabled_ops_count() -> None:
    """If a family has 0 enabled operators, its slots go to 0
    regardless of reserved_slots — slots wasted on a 0-op family
    aren't useful."""
    # Disable all FLIP operators.
    enabled = tuple(
        op for op in MutationOperator
        if op not in {MutationOperator.M1_HORIZ_FLIP, MutationOperator.M2_VERT_FLIP}
    )
    result = allocate_family_slots(
        enabled_operators=enabled,
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.FLIP, 5),  # 5 reserved but 0 enabled
        ),
        max_seeds_per_input=16,
    )
    flip_assignment = next(a for a in result if a.family == MutationOperatorFamily.FLIP)
    assert flip_assignment.slot_count == 0
    assert flip_assignment.enabled_operators_in_family == ()


# =============================================================================
# Total ≤ max_seeds
# =============================================================================


def test_total_slots_never_exceeds_max_seeds() -> None:
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=tuple(
            FamilySlotAllocation(f, 5) for f in MutationOperatorFamily
        ),
        max_seeds_per_input=8,
    )
    total = sum(a.slot_count for a in result)
    assert total <= 8


def test_zero_max_seeds_yields_all_zero() -> None:
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),
        max_seeds_per_input=0,
    )
    assert all(a.slot_count == 0 for a in result)


# =============================================================================
# Spillover
# =============================================================================


def test_surplus_spills_to_families_with_unused_capacity() -> None:
    """If sum_reserved < max_seeds, surplus distributes to families
    whose enabled-ops count > current allocation."""
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),  # sum = 9
        max_seeds_per_input=16,
    )
    total = sum(a.slot_count for a in result)
    # All 16 slots allocated (1 per op for 16 enabled ops).
    assert total == 16


def test_surplus_caps_at_total_enabled_operators() -> None:
    """Spillover can't exceed total enabled-ops across all families."""
    # Only M0 + M1 + M2 enabled (3 ops total).
    enabled = (
        MutationOperator.M0_BASE,
        MutationOperator.M1_HORIZ_FLIP,
        MutationOperator.M2_VERT_FLIP,
    )
    result = allocate_family_slots(
        enabled_operators=enabled,
        family_slot_allocations=_all_families_one_each(),
        max_seeds_per_input=100,  # impossible to fill
    )
    total = sum(a.slot_count for a in result)
    assert total == 3  # 1 BASE + 2 FLIP


# =============================================================================
# Truncation
# =============================================================================


def test_truncation_when_sum_reserved_exceeds_max() -> None:
    """sum_reserved=9, max_seeds=5 → truncate 4 slots from reverse-lex
    families. Lex-first families (BASE, etc.) preserved."""
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),  # sum = 9
        max_seeds_per_input=5,
    )
    total = sum(a.slot_count for a in result)
    assert total == 5
    # The lex-first families should have their reservation preserved.
    by_family = {a.family: a.slot_count for a in result}
    # base, corridor, entry, flip, grid, staircase, vertical, wet_wall, zone
    # reverse-lex order: zone, wet_wall, vertical, staircase, ...
    # Truncate 4: zone, wet_wall, vertical, staircase → 0
    # Keep: base, corridor, entry, flip, grid → 1 each = 5 total.
    assert by_family[MutationOperatorFamily.BASE] == 1
    assert by_family[MutationOperatorFamily.CORRIDOR] == 1


# =============================================================================
# Negative inputs
# =============================================================================


def test_negative_max_seeds_raises() -> None:
    with pytest.raises(ValueError, match="max_seeds_per_input"):
        allocate_family_slots(
            enabled_operators=_ALL_OPERATORS,
            family_slot_allocations=_all_families_one_each(),
            max_seeds_per_input=-1,
        )


def test_negative_reserved_slots_raises() -> None:
    with pytest.raises(ValueError, match="reserved_slots"):
        allocate_family_slots(
            enabled_operators=_ALL_OPERATORS,
            family_slot_allocations=(
                FamilySlotAllocation(MutationOperatorFamily.BASE, -2),
            ),
            max_seeds_per_input=8,
        )


# =============================================================================
# Enabled operators per family
# =============================================================================


def test_enabled_operators_in_family_populated() -> None:
    result = allocate_family_slots(
        enabled_operators=_ALL_OPERATORS,
        family_slot_allocations=_all_families_one_each(),
        max_seeds_per_input=16,
    )
    by_family = {a.family: a.enabled_operators_in_family for a in result}
    # Staircase family has 3 ops.
    assert len(by_family[MutationOperatorFamily.STAIRCASE]) == 3
    # Entry family has 4 ops.
    assert len(by_family[MutationOperatorFamily.ENTRY]) == 4
    # Base family has 1 op.
    assert by_family[MutationOperatorFamily.BASE] == (MutationOperator.M0_BASE,)
