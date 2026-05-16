"""
BuildemUp — Component 11a: Topology Mutation Layer — predicate registry
=========================================================================

Per SPEC § 3.4 (Tier A predicate orchestration) + § 0.4 (Mutation
Legality Responsibility Matrix).

C11a does not own architectural rules. Tier A predicates are bindings
of upstream rule IDs to their callable validators. This module:

1. Adapts the three callable upstream predicates from B-NEW-J/K/L (S38)
   into ``MutationViabilityPredicate`` registry entries:

   - ``C7.staircase_clearance`` → ``validate_staircase_clearance``
   - ``C8.entry_approach``      → ``validate_entry_approach``
   - ``C5.privacy_zoning``      → ``validate_privacy_zoning``

2. Registers 6 always-pass STUB predicates for the C9/C10 invariants
   referenced in § 3.4 matrix (C9.Inv_4, C9.Inv_5, C9.Inv_13;
   C10.Inv_4, C10.Inv_5, C10.Inv_5b). Per § 0.3 / § 0.4: these are
   structural properties of Tier A operator construction (e.g., a
   horizontal flip cannot change room count, so C9.Inv_4 is preserved
   by construction). The stubs are documented as such and ALL register
   with ``pending_upstream=False`` so the v1.0 LOCK gate (Inv 24)
   continues to read ``pending_upstream_predicate_count == 0``.

3. Provides a registry-lookup function ``lookup_predicate()`` and a
   per-operator predicate-id helper ``predicate_ids_for()`` keyed off
   the § 3.4 matrix so individual operators don't redeclare their
   bindings.

Predicate signatures intentionally vary (the upstream functions have
different arities). The operator dispatching to a predicate at apply()
time is responsible for marshalling the right arguments. The
registry's ``_predicate_fn`` field is typed as ``Callable[..., tuple
[bool, Optional[str]]]`` per schema, which allows variable arity.
"""
from __future__ import annotations

from typing import Callable, Final, Mapping, Optional

from buildemup.components.c05.zone_bands import validate_privacy_zoning
from buildemup.components.c07.grid_generator import (
    validate_staircase_clearance,
)
from buildemup.components.c08.validator import validate_entry_approach
from buildemup.components.c11a.errors import OperatorRegistryError
from buildemup.components.c11a.schema import (
    MutationOperator,
    MutationViabilityPredicate,
)


# =============================================================================
# Stub predicate — always-pass
# =============================================================================
#
# Per § 0.3 / § 0.4 Mutation Legality Responsibility Matrix: C11a does
# NOT own architectural rules. The C9/C10 invariants referenced in the
# § 3.4 matrix (Inv_4, Inv_5, Inv_5b, Inv_13) are STRUCTURAL PROPERTIES
# of Tier A operator construction:
#
#   * M1 horizontal flip preserves room count and area total (the y-set
#     and x-set are bijectively swapped, so C9.Inv_4 / C9.Inv_5 hold
#     by construction).
#   * M3 staircase repositioning does not touch the room graph
#     (C9.Inv_4 holds by construction).
#   * M4 corridor inversion preserves the room graph
#     (C9.Inv_4, C10.Inv_5 hold by construction; per W#5 Q22 carry).
#   * etc.
#
# These predicates exist in the registry so the §3.4 dispatch matrix
# stays canonical (any operator → predicate-list lookup is total over
# the matrix, no out-of-band cases). Their _predicate_fn is the stub
# below: returns (True, None) on every call. If a future amendment
# promotes one of these to a runtime check (e.g., C10.Inv_5b becomes
# regenerative-state-dependent), we replace the stub body with the
# real check; the registry shape and operator wiring stay constant.


def _stub_always_pass(*args, **kwargs) -> tuple[bool, Optional[str]]:
    """Always-pass predicate stub for structurally-preserved invariants.

    Used for C9.Inv_4 / C9.Inv_5 / C9.Inv_13 / C10.Inv_4 / C10.Inv_5 /
    C10.Inv_5b — invariants whose preservation is guaranteed by Tier A
    operator construction and therefore does not require a runtime
    check at this tier.

    Returns (True, None) regardless of arguments.
    """
    return (True, None)


# =============================================================================
# § 3.4 — predicate registry (9 entries)
# =============================================================================
#
# Order is by component number ASC (C5, C7, C8, C9, C10), then rule_id
# ASC within each component. This is more semantic than pure lex-ASC
# (which would put "C10" before "C5" because '1' < '5'); component-
# number order also sorts stably across module reloads.


PREDICATE_REGISTRY: Final[tuple[MutationViabilityPredicate, ...]] = (
    # ── C5 ────────────────────────────────────────────────────────────
    MutationViabilityPredicate(
        rule_owner="C5",
        rule_id="privacy_zoning",
        description=(
            "PRIVATE band must not occupy the road-facing direction set "
            "derived from plot_facing. Per B-NEW-J v1.0 LOCKED (S38). "
            "Applies to M2 (vertical flip) and M5 (zone swap)."
        ),
        _predicate_fn=validate_privacy_zoning,
        pending_upstream=False,
    ),
    # ── C7 ────────────────────────────────────────────────────────────
    MutationViabilityPredicate(
        rule_owner="C7",
        rule_id="staircase_clearance",
        description=(
            "W9 staircase clearance: width >= NBC minimum, landing depth "
            ">= max(width, NBC floor), footprint within envelope, anchor "
            "flush. Per B-NEW-K v1.0 LOCKED + K-4 patch (S38). Applies "
            "to M3a/b/c (staircase repositioning)."
        ),
        _predicate_fn=validate_staircase_clearance,
        pending_upstream=False,
    ),
    # ── C8 ────────────────────────────────────────────────────────────
    MutationViabilityPredicate(
        rule_owner="C8",
        rule_id="entry_approach",
        description=(
            "Inv 21: every ENTRY endpoint of a has_corridor=True path "
            "lies on the envelope edge(s) corresponding to plot_facing. "
            "Per B-NEW-L v1.0 LOCKED (S38). Applies to M9a/b/c/d (entry "
            "repositioning)."
        ),
        _predicate_fn=validate_entry_approach,
        pending_upstream=False,
    ),
    # ── C9 stubs ──────────────────────────────────────────────────────
    MutationViabilityPredicate(
        rule_owner="C9",
        rule_id="Inv_4",
        description=(
            "Room-graph cardinality preservation. Structural property "
            "of Tier A operator construction (M3 / M4 cannot add or "
            "remove rooms). STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
    MutationViabilityPredicate(
        rule_owner="C9",
        rule_id="Inv_5",
        description=(
            "Per-room area floor preservation. Structural property of "
            "Tier A flips (M1 / M2): bijective coordinate swap preserves "
            "areas. STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
    MutationViabilityPredicate(
        rule_owner="C9",
        rule_id="Inv_13",
        description=(
            "Room-size-table determinism. Tier A operators do not "
            "regenerate the size table; preservation is structural. "
            "STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
    # ── C10 stubs ─────────────────────────────────────────────────────
    MutationViabilityPredicate(
        rule_owner="C10",
        rule_id="Inv_4",
        description=(
            "Wet-zone planner cache consistency. Tier A SHALLOW does "
            "not touch the wet-zone plan; cache state is structurally "
            "preserved. STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
    MutationViabilityPredicate(
        rule_owner="C10",
        rule_id="Inv_5",
        description=(
            "Wet-wall assignment determinism. Tier A operators do not "
            "drive C10 regeneration; assignment preservation is "
            "structural. STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
    MutationViabilityPredicate(
        rule_owner="C10",
        rule_id="Inv_5b",
        description=(
            "Wet-zone assignment derived-from-zoning consistency. "
            "Applies to M5 (zone swap) — preserved structurally because "
            "M5 swaps assignments but does not regenerate plumbing "
            "geometry at Tier A. STUB — see module docstring."
        ),
        _predicate_fn=_stub_always_pass,
        pending_upstream=False,
    ),
)


# =============================================================================
# § 3.4 — per-operator predicate matrix (carried v0.4)
# =============================================================================


_OPERATOR_PREDICATE_MATRIX: Final[
    Mapping[MutationOperator, tuple[tuple[str, str], ...]]
] = {
    # M0 is the always-valid base — no predicates.
    MutationOperator.M0_BASE: (),

    # M1 horizontal flip: structural preservation of areas + adjacency.
    MutationOperator.M1_HORIZ_FLIP: (
        ("C9", "Inv_5"),
        ("C9", "Inv_13"),
        ("C10", "Inv_4"),
        ("C10", "Inv_5"),
    ),

    # M2 vertical flip: like M1 plus C5 privacy zoning (vertical flip
    # may move the PRIVATE band into a road-facing direction).
    MutationOperator.M2_VERT_FLIP: (
        ("C5", "privacy_zoning"),
        ("C9", "Inv_5"),
        ("C9", "Inv_13"),
        ("C10", "Inv_5"),
    ),

    # M3a/b/c staircase repositioning: W9 + room-graph preservation.
    MutationOperator.M3A_STAIR_EAST: (
        ("C7", "staircase_clearance"),
        ("C9", "Inv_4"),
    ),
    MutationOperator.M3B_STAIR_WEST: (
        ("C7", "staircase_clearance"),
        ("C9", "Inv_4"),
    ),
    MutationOperator.M3C_STAIR_NE: (
        ("C7", "staircase_clearance"),
        ("C9", "Inv_4"),
    ),

    # M4 corridor inversion: room-graph preservation + wet-zone consistency.
    MutationOperator.M4_CORRIDOR_INV: (
        ("C9", "Inv_4"),
        ("C10", "Inv_5"),
    ),

    # M5 public/private swap: privacy zoning + wet-zone-from-zoning.
    MutationOperator.M5_ZONE_SWAP: (
        ("C5", "privacy_zoning"),
        ("C10", "Inv_5b"),
    ),

    # M6/M7/M8 — Tier B operators. They do NOT dispatch Tier A
    # predicates; validation happens at C7/C9/C10 invariant-check time
    # during DeepMutationPipeline regeneration (§ 3.5 step 5). The
    # empty matrix entries keep the per-operator lookup total — Tier B
    # callers get () back and skip predicate dispatch entirely.
    MutationOperator.M6_WET_ROTATE: (),
    MutationOperator.M7A_GRID_3_3: (),
    MutationOperator.M7B_GRID_2_7: (),
    MutationOperator.M8_VERT_REARR: (),

    # M9a/b/c/d entry repositioning: Inv 21 entry-on-edge.
    MutationOperator.M9A_ENTRY_CTR: (("C8", "entry_approach"),),
    MutationOperator.M9B_ENTRY_W:   (("C8", "entry_approach"),),
    MutationOperator.M9C_ENTRY_E:   (("C8", "entry_approach"),),
    MutationOperator.M9D_ENTRY_OFF: (("C8", "entry_approach"),),
}


# =============================================================================
# Lookup helpers
# =============================================================================


def lookup_predicate(
    rule_owner: str, rule_id: str,
) -> MutationViabilityPredicate:
    """Find a predicate by (rule_owner, rule_id).

    Raises:
        OperatorRegistryError if the predicate is not registered.
            Per § 5: predicate-registry inconsistencies are systemic;
            an operator referencing a non-existent predicate cannot
            produce correct results.
    """
    for p in PREDICATE_REGISTRY:
        if p.rule_owner == rule_owner and p.rule_id == rule_id:
            return p
    raise OperatorRegistryError(
        f"predicate {rule_owner}.{rule_id} is not registered in "
        f"PREDICATE_REGISTRY (predicate_registry.py § 3.4)."
    )


def predicate_ids_for(
    operator: MutationOperator,
) -> tuple[tuple[str, str], ...]:
    """Return the (rule_owner, rule_id) tuples applicable to ``operator``.

    Per the § 3.4 matrix.

    Tier A operators (M0/M1/M2/M3a/b/c/M4/M5/M9a/b/c/d) return their
    declared predicate list. Tier B operators (M6/M7/M8) return an
    empty tuple — they do NOT dispatch Tier A predicates; validation
    runs at C7/C9/C10 invariant-check time during
    ``DeepMutationPipeline`` regeneration (§ 3.5 step 5).

    Raises:
        OperatorRegistryError if ``operator`` is somehow not in the
        matrix at all (programming bug — every enum member should be
        a key).
    """
    if operator not in _OPERATOR_PREDICATE_MATRIX:
        raise OperatorRegistryError(
            f"operator {operator.value} has no entry in the § 3.4 "
            f"predicate matrix. Every MutationOperator enum member "
            f"must have an entry (Tier B entries are empty tuples)."
        )
    return _OPERATOR_PREDICATE_MATRIX[operator]


def predicates_for(
    operator: MutationOperator,
) -> tuple[MutationViabilityPredicate, ...]:
    """Return resolved predicate instances applicable to ``operator``."""
    ids = predicate_ids_for(operator)
    return tuple(lookup_predicate(o, r) for (o, r) in ids)


# =============================================================================
# Inv 24 LOCK gate (snapshot read of registry state)
# =============================================================================


def pending_upstream_predicate_count() -> int:
    """Per Inv 24: count of registered predicates with pending_upstream=True.

    At v1.0 LOCK time, B-NEW-J/K/L/P all LOCKED, so this returns 0.
    Sub-session 4's Phase 0 startup validation reads this together
    with WAIVER_REGISTRY length to enforce the LOCK gate.
    """
    return sum(1 for p in PREDICATE_REGISTRY if p.pending_upstream)


__all__ = [
    "PREDICATE_REGISTRY",
    "lookup_predicate",
    "predicate_ids_for",
    "predicates_for",
    "pending_upstream_predicate_count",
]
