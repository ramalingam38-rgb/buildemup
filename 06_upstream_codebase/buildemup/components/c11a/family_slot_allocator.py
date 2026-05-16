"""
BuildemUp — Component 11a — family slot allocator
====================================================

Per spec § 3 Phase 1: per-family slot allocation distributes
``max_seeds_per_input`` across the 9 ``MutationOperatorFamily``
values according to ``config.family_slot_allocations``, with three
properties:

  * **Deterministic**: same inputs → same allocation. The allocator
    operates over the lex-ASC enum-value sort of family names so
    set-iteration order doesn't leak into the result.

  * **Reservation-respecting**: each family's ``reserved_slots`` is
    the floor — actual allocations are ≥ reserved_slots if total
    reserved ≤ max_seeds.

  * **Spillover to surplus families**: if the sum of reserved_slots
    is less than max_seeds, the surplus is distributed round-robin
    across all families in lex-ASC order, biased to families with
    more enabled operators (so the spillover slots get used).

  * **Truncation**: if the sum of reserved_slots exceeds max_seeds,
    families are truncated in *reverse* lex-ASC order until the sum
    fits. (Reverse so the lex-first families — BASE, FLIP — keep
    their reservations preferentially.)

Sub-session 4 will call ``allocate_family_slots`` from the
``mutate_topologies`` orchestrator. Sub-2 ships the function +
tests so the algorithm is locked-down before orchestrator wires it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.schema import (
    FamilySlotAllocation,
    MutationOperator,
    MutationOperatorFamily,
)


# =============================================================================
# Result type
# =============================================================================


@dataclass(frozen=True)
class FamilySlotAssignment:
    """The allocator's per-family verdict — how many seeds this family
    should produce on a given source candidate.

    Per § 3 Phase 1: the orchestrator iterates families lex-ASC and
    requests up to ``slot_count`` seeds from each family's enabled
    operators. Families with zero enabled operators or zero
    slot_count contribute nothing.
    """
    family: MutationOperatorFamily
    slot_count: int
    enabled_operators_in_family: tuple[MutationOperator, ...]


# =============================================================================
# Helpers
# =============================================================================


def _enabled_operators_per_family(
    enabled_operators: tuple[MutationOperator, ...],
) -> Mapping[MutationOperatorFamily, tuple[MutationOperator, ...]]:
    """Group ``enabled_operators`` by their declared family.

    Iteration order is MutationOperator enum order (which is lex-ASC
    by historical convention; the schema sub-session 1 tests pin the
    enum order so this is stable).
    """
    grouped: dict[MutationOperatorFamily, list[MutationOperator]] = {
        family: [] for family in MutationOperatorFamily
    }
    enabled_set = set(enabled_operators)
    for op in MutationOperator:
        if op not in enabled_set:
            continue
        family = OPERATOR_METADATA[op].family
        grouped[family].append(op)
    return {f: tuple(ops) for f, ops in grouped.items()}


def _family_lex_order() -> tuple[MutationOperatorFamily, ...]:
    """Return MutationOperatorFamily values in lex-ASC of their .value
    strings. Stable across runs.
    """
    return tuple(sorted(MutationOperatorFamily, key=lambda f: f.value))


# =============================================================================
# Allocator
# =============================================================================


def allocate_family_slots(
    *,
    enabled_operators: tuple[MutationOperator, ...],
    family_slot_allocations: tuple[FamilySlotAllocation, ...],
    max_seeds_per_input: int,
    floor_count_for_cap: int = 1,
) -> tuple[FamilySlotAssignment, ...]:
    """Compute per-family slot assignments for one source candidate.

    Args:
        enabled_operators: from ``TopologyMutationConfig.enabled_operators``.
            Operators NOT in this tuple are excluded from their family's
            ``enabled_operators_in_family`` list (and contribute zero
            even if their family has reserved slots).
        family_slot_allocations: from
            ``TopologyMutationConfig.family_slot_allocations``. Per-family
            ``reserved_slots`` floors. Families absent from this tuple
            default to 0 reserved slots.
        max_seeds_per_input: total slot budget per source candidate.
            The sum of all returned ``slot_count``s is exactly
            ``min(sum_reserved, max_seeds)`` plus any surplus spillover
            up to ``max_seeds``.
        floor_count_for_cap: per Spec #4 v1.6 § 3.2 (B-NEW-T3 #4) — the
            number of floors the multi-floor bipartite expansion will
            target. Default 1 (single-floor; byte-identical original
            behaviour). For multi-floor inputs, the orchestrator passes
            ``len(wrapper.floor_labels)`` so the per-family cap allows
            ``len(enabled_ops) * num_floors`` candidate attempts before
            truncation. Without this hint, a family with 1 enabled
            operator + multiple floors would be capped at 1 slot, which
            collapses multi-floor coverage to single-floor coverage.

    Returns:
        Tuple of ``FamilySlotAssignment`` in lex-ASC family order.
        Total ``slot_count`` across the tuple ≤ max_seeds_per_input.

    Raises:
        ValueError: if ``max_seeds_per_input`` is negative or if any
            ``reserved_slots`` is negative.
    """
    if max_seeds_per_input < 0:
        raise ValueError(
            f"max_seeds_per_input must be >= 0; got {max_seeds_per_input}"
        )
    if floor_count_for_cap < 1:
        raise ValueError(
            f"floor_count_for_cap must be >= 1; got {floor_count_for_cap}"
        )
    for fsa in family_slot_allocations:
        if fsa.reserved_slots < 0:
            raise ValueError(
                f"FamilySlotAllocation({fsa.family.value}).reserved_slots "
                f"must be >= 0; got {fsa.reserved_slots}"
            )

    # 1. Build the canonical per-family reserved-slot map.
    reserved: dict[MutationOperatorFamily, int] = {
        f: 0 for f in MutationOperatorFamily
    }
    for fsa in family_slot_allocations:
        # Last entry wins on duplicates (rare; surfaces in tests).
        reserved[fsa.family] = fsa.reserved_slots

    # 2. Build per-family enabled-operators map.
    enabled_per_family = _enabled_operators_per_family(enabled_operators)

    # 3. Initial allocation: each family gets min(reserved, families'
    #    enabled-ops cap × floor_count_for_cap). Capping at
    #    `enabled × floor_count` is the multi-floor extension: with
    #    floor_count_for_cap=1 it's byte-identical to the original
    #    single-floor cap (`enabled` only); with floor_count_for_cap=N
    #    a family with K enabled ops can hold up to K*N slots, allowing
    #    the bipartite operator+floor interleaving (Spec #4 § 3.2) to
    #    cover (op × floor) pairs.
    families_lex = _family_lex_order()
    initial: dict[MutationOperatorFamily, int] = {}
    for family in families_lex:
        enabled_count = len(enabled_per_family[family])
        cap = max(0, enabled_count) * floor_count_for_cap
        initial[family] = min(reserved[family], cap)

    # 4. Truncate if total > max_seeds, in REVERSE lex-ASC order
    #    (preferentially preserve lex-first families' reservations).
    total_initial = sum(initial.values())
    if total_initial > max_seeds_per_input:
        overflow = total_initial - max_seeds_per_input
        for family in reversed(families_lex):
            if overflow <= 0:
                break
            take = min(initial[family], overflow)
            initial[family] -= take
            overflow -= take

    # 5. Spillover: if total < max_seeds, distribute surplus
    #    round-robin across families with enabled operators.
    total_now = sum(initial.values())
    surplus = max_seeds_per_input - total_now

    if surplus > 0:
        # Build round-robin list of families with at least one enabled
        # operator AND room above their current allocation. Cap is
        # `enabled_count * floor_count_for_cap` per the multi-floor
        # extension (Spec #4 v1.6 § 3.2).
        def _family_cap(f: MutationOperatorFamily) -> int:
            return len(enabled_per_family[f]) * floor_count_for_cap

        eligible = [
            f for f in families_lex
            if _family_cap(f) > initial[f]
        ]
        idx = 0
        while surplus > 0 and eligible:
            f = eligible[idx % len(eligible)]
            if initial[f] < _family_cap(f):
                initial[f] += 1
                surplus -= 1
            # If we just hit the cap, drop f from eligible.
            if initial[f] >= _family_cap(f):
                eligible.remove(f)
                # Don't increment idx — the next family takes its slot.
                if eligible and idx >= len(eligible):
                    idx = 0
            else:
                idx += 1
                if idx >= len(eligible):
                    idx = 0

    # 6. Materialise the result tuple in lex-ASC order.
    return tuple(
        FamilySlotAssignment(
            family=family,
            slot_count=initial[family],
            enabled_operators_in_family=enabled_per_family[family],
        )
        for family in families_lex
    )


# =============================================================================
# Spec #4 v1.6 § 3.7 — Multi-floor family ID aggregation (B-NEW-T3 #4)
# =============================================================================


def multi_floor_family_id(
    wrapper: Any,
    *,
    per_floor_family_id: "Callable[[Any], str] | None" = None,
) -> str:
    """Label-preserving family-ID aggregation for multi-floor wrappers.

    Per Spec #4 v1.6 § 3.7: aggregates per-floor family IDs into a
    multi-floor family ID that encodes WHICH FAMILY is on WHICH FLOOR,
    not just the multiset of families.

    Format: ``multi_floor:<label1>=<family_id1>|<label2>=<family_id2>|...``

    Sort key is the floor LABEL (not the family) for cross-process
    determinism while preserving label-family pairing. v1.1's
    sorted-by-family aggregation would have collapsed
    architecturally-distinct configurations like ``[ground=A, first=B]``
    and ``[ground=B, first=A]`` into the same family ID. v1.2+'s
    label-preserving aggregation prevents that.

    Lexical-sort caveat (v1.3 from v1.2 critique walk item 3): may not
    reflect elevation order, but is the available-determinism choice
    until Spec #1 B-MFDB-A lands per-floor elevation metadata.

    Args:
        wrapper: a real ``MultiFloorWetZonePlannedCandidate`` (Spec #3).
        per_floor_family_id: optional callable returning the
            per-floor wrapper's family ID. Defaulted to a structural
            family-extraction stub via candidate_context when omitted;
            override for testing.

    Returns:
        Family ID string, prefixed ``multi_floor:`` so it cannot
        collide with single-floor family IDs.
    """
    # Default per-floor family extractor: derive from topology kind
    # (the same signal single-floor candidates use for family ID).
    # Per Spec #4 § 3.7 the per-floor family ID is whatever the
    # single-floor family allocator considers a candidate's family;
    # for the v1 build that's the topology kind string from the
    # ancestry chain.
    if per_floor_family_id is None:
        from buildemup.components.c11a.candidate_context import (
            extract_topology_kind,
        )

        def per_floor_family_id(f: Any) -> str:  # type: ignore[no-redef]
            return str(extract_topology_kind(f))

    pairs = sorted(
        (label, per_floor_family_id(f))
        for label, f in zip(wrapper.floor_labels, wrapper.floors)
    )
    payload = "|".join(f"{label}={family_id}" for label, family_id in pairs)
    return f"multi_floor:{payload}"


__all__ = [
    "FamilySlotAssignment",
    "allocate_family_slots",
    # Spec #4 v1.6 § 3.7: multi-floor family aggregation
    "multi_floor_family_id",
]
