"""
C11a Sub-session 2 tests — predicate registry.

Per CODING_MANDATE Step 2 Sub-session 2: predicate registry binds
upstream callable predicates (B-NEW-J/K/L) and registers C9/C10
structural-property stubs. Tests verify:
  - 9 entries exact (3 callable + 6 stubs)
  - All v1.0 predicates pending_upstream=False (Inv 24 LOCK gate at 0)
  - lookup_predicate lookup correctness + error path
  - predicate_ids_for matches § 3.4 matrix
  - § 3.4 dispatch coverage for every Tier A operator
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a import (
    MutationOperator,
    MutationViabilityPredicate,
    OperatorRegistryError,
    PREDICATE_REGISTRY,
    lookup_predicate,
    pending_upstream_predicate_count,
    predicate_ids_for,
    predicates_for,
)


# =============================================================================
# Registry shape
# =============================================================================


def test_predicate_registry_has_9_entries() -> None:
    """3 callable (C5/C7/C8) + 6 stubs (C9.Inv_4/5/13, C10.Inv_4/5/5b)."""
    assert len(PREDICATE_REGISTRY) == 9


def test_predicate_registry_entries_are_predicate_instances() -> None:
    for p in PREDICATE_REGISTRY:
        assert isinstance(p, MutationViabilityPredicate)


def test_predicate_registry_stable_order() -> None:
    """The registry order is fixed at v1.0 LOCK and pinned by this
    test: C5 → C7 → C8 → C9 (Inv_4, 5, 13 in numerical-id order) →
    C10 (Inv_4, 5, 5b in numerical-id then lex). Order MUST be stable
    across module reloads — replay/cache hashes depend on it.
    """
    keys = [(p.rule_owner, p.rule_id) for p in PREDICATE_REGISTRY]
    expected = [
        ("C5",  "privacy_zoning"),
        ("C7",  "staircase_clearance"),
        ("C8",  "entry_approach"),
        ("C9",  "Inv_4"),
        ("C9",  "Inv_5"),
        ("C9",  "Inv_13"),
        ("C10", "Inv_4"),
        ("C10", "Inv_5"),
        ("C10", "Inv_5b"),
    ]
    assert keys == expected


def test_predicate_registry_contains_3_callable_predicates() -> None:
    """C5.privacy_zoning, C7.staircase_clearance, C8.entry_approach
    are real callables imported from the upstream components."""
    expected_callable = {
        ("C5", "privacy_zoning"),
        ("C7", "staircase_clearance"),
        ("C8", "entry_approach"),
    }
    actual = {(p.rule_owner, p.rule_id) for p in PREDICATE_REGISTRY}
    # Just check the callables are present (also stubs).
    assert expected_callable <= actual


def test_predicate_registry_contains_6_c9_c10_stubs() -> None:
    expected_stubs = {
        ("C9", "Inv_4"),
        ("C9", "Inv_5"),
        ("C9", "Inv_13"),
        ("C10", "Inv_4"),
        ("C10", "Inv_5"),
        ("C10", "Inv_5b"),
    }
    actual = {(p.rule_owner, p.rule_id) for p in PREDICATE_REGISTRY}
    assert expected_stubs <= actual


# =============================================================================
# Inv 24 LOCK gate
# =============================================================================


def test_all_predicates_pending_upstream_false() -> None:
    """At v1.0 LOCK, B-NEW-J/K/L/P all LOCKED, so every predicate has
    pending_upstream=False. Stubs likewise (they encode structurally-
    preserved invariants, not pending-upstream amendments).
    """
    for p in PREDICATE_REGISTRY:
        assert p.pending_upstream is False, (
            f"{p.rule_owner}.{p.rule_id} pending_upstream should be False"
        )


def test_pending_upstream_predicate_count_is_zero() -> None:
    """Inv 24 LOCK gate clause 1: pending_upstream_count == 0 at LOCK."""
    assert pending_upstream_predicate_count() == 0


def test_predicate_descriptions_non_empty() -> None:
    """Every predicate carries a non-empty description (audit trail)."""
    for p in PREDICATE_REGISTRY:
        assert p.description.strip(), (
            f"{p.rule_owner}.{p.rule_id} has empty description"
        )


# =============================================================================
# lookup_predicate
# =============================================================================


def test_lookup_predicate_finds_callable_entry() -> None:
    p = lookup_predicate("C7", "staircase_clearance")
    assert p.rule_owner == "C7"
    assert p.rule_id == "staircase_clearance"
    # Confirm it's not the stub.
    assert callable(p._predicate_fn)


def test_lookup_predicate_finds_stub_entry() -> None:
    p = lookup_predicate("C9", "Inv_4")
    assert p.rule_owner == "C9"
    assert p.rule_id == "Inv_4"
    # The stub returns (True, None) for any args.
    assert p._predicate_fn() == (True, None)
    assert p._predicate_fn("anything") == (True, None)
    assert p._predicate_fn(1, 2, foo="bar") == (True, None)


def test_lookup_predicate_unknown_raises() -> None:
    with pytest.raises(OperatorRegistryError, match="not registered"):
        lookup_predicate("C99", "nonexistent_rule")


# =============================================================================
# § 3.4 matrix coverage — predicate_ids_for
# =============================================================================


def test_predicate_ids_for_m0_empty() -> None:
    """M0_BASE has no predicates per § 3.4."""
    assert predicate_ids_for(MutationOperator.M0_BASE) == ()


def test_predicate_ids_for_m1_matches_spec() -> None:
    expected = (
        ("C9", "Inv_5"),
        ("C9", "Inv_13"),
        ("C10", "Inv_4"),
        ("C10", "Inv_5"),
    )
    assert predicate_ids_for(MutationOperator.M1_HORIZ_FLIP) == expected


def test_predicate_ids_for_m2_includes_c5_privacy() -> None:
    """M2 vertical flip dispatches C5.privacy_zoning unlike M1."""
    ids = predicate_ids_for(MutationOperator.M2_VERT_FLIP)
    assert ("C5", "privacy_zoning") in ids


def test_predicate_ids_for_m3_family_uses_c7_w9() -> None:
    """All three M3 variants dispatch C7.staircase_clearance + C9.Inv_4."""
    expected = (("C7", "staircase_clearance"), ("C9", "Inv_4"))
    assert predicate_ids_for(MutationOperator.M3A_STAIR_EAST) == expected
    assert predicate_ids_for(MutationOperator.M3B_STAIR_WEST) == expected
    assert predicate_ids_for(MutationOperator.M3C_STAIR_NE) == expected


def test_predicate_ids_for_m4_uses_c9_c10_stubs() -> None:
    """M4 corridor inversion uses C9.Inv_4 + C10.Inv_5 (per § 3.4 W#5 Q22)."""
    expected = (("C9", "Inv_4"), ("C10", "Inv_5"))
    assert predicate_ids_for(MutationOperator.M4_CORRIDOR_INV) == expected


def test_predicate_ids_for_m5_uses_c5_and_c10_5b() -> None:
    """M5 zone swap → C5.privacy_zoning + C10.Inv_5b stub."""
    expected = (("C5", "privacy_zoning"), ("C10", "Inv_5b"))
    assert predicate_ids_for(MutationOperator.M5_ZONE_SWAP) == expected


def test_predicate_ids_for_m9_family_uses_c8_entry() -> None:
    """All four M9 variants dispatch C8.entry_approach only."""
    expected = (("C8", "entry_approach"),)
    assert predicate_ids_for(MutationOperator.M9A_ENTRY_CTR) == expected
    assert predicate_ids_for(MutationOperator.M9B_ENTRY_W) == expected
    assert predicate_ids_for(MutationOperator.M9C_ENTRY_E) == expected
    assert predicate_ids_for(MutationOperator.M9D_ENTRY_OFF) == expected


def test_predicate_ids_for_tier_b_returns_empty() -> None:
    """Tier B operators (M6/M7/M8) return () — they do not dispatch
    Tier A predicates; validation runs at C7/C9/C10 invariant-check
    time during DeepMutationPipeline regeneration."""
    assert predicate_ids_for(MutationOperator.M6_WET_ROTATE) == ()
    assert predicate_ids_for(MutationOperator.M7A_GRID_3_3) == ()
    assert predicate_ids_for(MutationOperator.M7B_GRID_2_7) == ()
    assert predicate_ids_for(MutationOperator.M8_VERT_REARR) == ()


def test_predicates_for_resolves_instances() -> None:
    """predicates_for() resolves the (owner, id) tuples to actual
    MutationViabilityPredicate instances."""
    preds = predicates_for(MutationOperator.M3A_STAIR_EAST)
    assert len(preds) == 2
    assert all(isinstance(p, MutationViabilityPredicate) for p in preds)
    assert preds[0].rule_owner == "C7"
    assert preds[1].rule_owner == "C9"
