"""
BuildemUp† — Component 9 (Room Sizer) — Surplus allocator.

Per C9 SPEC v0.7 LOCKED § 4.5 (Surplus allocation).

Distributes the envelope's free area (envelope_minus_corridor minus the sum of
all liveability_min_area_m2) across the rooms. The allocation does NOT mutate
RoomSizeRequirement instances; it produces metrics consumed by RoomSizeTable
and RoomSizingProvenance:

  - surplus_for_distribution_m2 (= envelope - Σ liveability_min)
  - surplus_distributed_m2      (allocated to rooms; never exceeds available)
  - unassigned_area_m2          (= surplus_for_distribution - surplus_distributed)
  - rooms_at_min                (room_ids that never grew above liveability_min)
  - rooms_clamped_at_max        (room_ids that hit max_m2 in growth stage 2)

Algorithms:
  - PRIORITY_GREEDY (default): two-stage water-filling.
      Stage 1: each room (in priority order) grows from liveability_min to target.
      Stage 2: leftover surplus, again in priority order, grows rooms from target
               to max. Surplus exhausted at any point stops the loop.
  - PROPORTIONAL: single pro-rata pass weighted by (target - liveability_min),
    clamped at (max - liveability_min). Leftover from clipping is redistributed
    once across un-clipped rooms; further leftover becomes unassigned.

Priority resolution:
  - Default: rooms sorted by ``room.priority`` ascending (1 = highest).
  - Override (config.priority_override): tuple[str, ...] of room_ids in priority
    order. The orchestrator validates this against rooms it materialised.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c09.schema import (
    AllocationStrategy,
    RoomSizeRequirement,
)


# Float-equality tolerance for "is this room at min / clamped at max?" decisions.
# Matches the ~1e-6 m^2 fuzz allowed elsewhere in the codebase.
_EPSILON_M2: float = 1e-6


@dataclass(frozen=True)
class AllocationResult:
    """Outcome of one allocation pass. Fields feed into RoomSizeTable +
    RoomSizingProvenance.

    `assigned_per_room` is a dict{room_id: assigned_size_m2}; the assigned
    size is between liveability_min_area_m2 and max_m2. The orchestrator
    captures it in provenance for debugging but does NOT mutate
    RoomSizeRequirement (the requirement carries the boundaries; downstream
    components (C11/C14) make the final placement-time sizing decision).
    """
    assigned_per_room: dict[str, float]
    surplus_for_distribution_m2: float
    surplus_distributed_m2: float
    unassigned_area_m2: float
    rooms_at_min: tuple[str, ...]
    rooms_clamped_at_max: tuple[str, ...]


def _resolve_order(
    rooms: tuple[RoomSizeRequirement, ...],
    priority_override: tuple[str, ...] | None,
) -> tuple[RoomSizeRequirement, ...]:
    """Resolve priority order. Per § 4.5 / § 14.19.

    If override is supplied:
      - Must contain every room_id in `rooms` exactly once (caller validated by
        orchestrator; here we trust the caller).
    Otherwise:
      - Sort by room.priority ascending (1 = highest).
    """
    if priority_override is None:
        return tuple(sorted(rooms, key=lambda r: r.priority))
    by_id = {r.room_id: r for r in rooms}
    return tuple(by_id[rid] for rid in priority_override)


def distribute_surplus(
    *,
    rooms: tuple[RoomSizeRequirement, ...],
    envelope_minus_corridor_m2: float,
    strategy: AllocationStrategy,
    priority_override: tuple[str, ...] | None = None,
) -> AllocationResult:
    """Distribute surplus area across rooms. Per § 4.5.

    Args:
        rooms: tuple of materialised RoomSizeRequirement (already passed Inv 6/7/8).
        envelope_minus_corridor_m2: from C8's CorridorPath envelopes minus
            corridor area; must be > 0 and >= Σ liveability_min (Inv 9, checked
            upstream by validator).
        strategy: PRIORITY_GREEDY or PROPORTIONAL.
        priority_override: tuple of room_ids in priority order, or None for
            default (sort by room.priority ascending).

    Returns:
        AllocationResult with assigned sizes + surplus metrics.

    Raises:
        ValueError: surplus_for_distribution_m2 < 0 (caller should have raised
            RoomSizingInfeasibleError before reaching here; this is a defensive
            guard).
    """
    if not rooms:
        return AllocationResult(
            assigned_per_room={},
            surplus_for_distribution_m2=envelope_minus_corridor_m2,
            surplus_distributed_m2=0.0,
            unassigned_area_m2=envelope_minus_corridor_m2,
            rooms_at_min=(),
            rooms_clamped_at_max=(),
        )

    total_min = sum(r.liveability_min_area_m2 for r in rooms)
    surplus = envelope_minus_corridor_m2 - total_min
    if surplus < -_EPSILON_M2:
        raise ValueError(
            f"distribute_surplus: surplus_for_distribution_m2 < 0 "
            f"({surplus:.6f}); orchestrator should have raised "
            f"RoomSizingInfeasibleError. envelope={envelope_minus_corridor_m2}, "
            f"Σ liveability_min={total_min}"
        )
    surplus = max(0.0, surplus)  # tolerate tiny float fuzz

    ordered = _resolve_order(rooms, priority_override)
    assigned = {r.room_id: r.liveability_min_area_m2 for r in rooms}

    if strategy == AllocationStrategy.PRIORITY_GREEDY:
        remaining = _priority_greedy(assigned, ordered, surplus)
    elif strategy == AllocationStrategy.PROPORTIONAL:
        remaining = _proportional(assigned, ordered, surplus)
    else:
        raise ValueError(
            f"distribute_surplus: unknown strategy {strategy!r}"
        )

    surplus_distributed = surplus - remaining

    rooms_at_min: list[str] = []
    rooms_clamped_at_max: list[str] = []
    by_id = {r.room_id: r for r in rooms}
    for room_id, size in assigned.items():
        req = by_id[room_id]
        if abs(size - req.liveability_min_area_m2) <= _EPSILON_M2:
            rooms_at_min.append(room_id)
        if abs(size - req.max_m2) <= _EPSILON_M2:
            rooms_clamped_at_max.append(room_id)

    return AllocationResult(
        assigned_per_room=assigned,
        surplus_for_distribution_m2=round(surplus, 6),
        surplus_distributed_m2=round(surplus_distributed, 6),
        unassigned_area_m2=round(remaining, 6),
        rooms_at_min=tuple(rooms_at_min),
        rooms_clamped_at_max=tuple(rooms_clamped_at_max),
    )


def _priority_greedy(
    assigned: dict[str, float],
    ordered: tuple[RoomSizeRequirement, ...],
    surplus: float,
) -> float:
    """Two-stage water-filling. Returns leftover surplus (unassigned)."""
    remaining = surplus

    # Stage 1: grow rooms from liveability_min to target, in priority order.
    for r in ordered:
        if remaining <= _EPSILON_M2:
            break
        room_target_grow = r.target_m2 - assigned[r.room_id]
        if room_target_grow <= _EPSILON_M2:
            continue
        give = min(room_target_grow, remaining)
        assigned[r.room_id] += give
        remaining -= give

    # Stage 2: grow rooms from target to max, in priority order.
    for r in ordered:
        if remaining <= _EPSILON_M2:
            break
        room_max_grow = r.max_m2 - assigned[r.room_id]
        if room_max_grow <= _EPSILON_M2:
            continue
        give = min(room_max_grow, remaining)
        assigned[r.room_id] += give
        remaining -= give

    return max(0.0, remaining)


def _proportional(
    assigned: dict[str, float],
    ordered: tuple[RoomSizeRequirement, ...],
    surplus: float,
) -> float:
    """Single pro-rata pass weighted by (target - liveability_min).

    Clamped at (max - liveability_min). One redistribution pass for clipped
    rooms; further leftover becomes unassigned.
    """
    if surplus <= _EPSILON_M2:
        return max(0.0, surplus)

    weights = {
        r.room_id: max(0.0, r.target_m2 - r.liveability_min_area_m2)
        for r in ordered
    }
    total_weight = sum(weights.values())
    if total_weight <= _EPSILON_M2:
        return surplus  # no room wants to grow

    by_id = {r.room_id: r for r in ordered}
    remaining = surplus
    # Iterate up to len(rooms)+1 redistributions; each iteration clips at most one room.
    for _ in range(len(ordered) + 1):
        if remaining <= _EPSILON_M2 or total_weight <= _EPSILON_M2:
            break
        clipped_this_pass = False
        for room_id, w in list(weights.items()):
            if w <= _EPSILON_M2:
                continue
            share = remaining * (w / total_weight)
            req = by_id[room_id]
            cap = req.max_m2 - assigned[room_id]
            if share >= cap:
                # Clip
                give = max(0.0, cap)
                assigned[room_id] += give
                remaining -= give
                weights[room_id] = 0.0
                total_weight -= w
                clipped_this_pass = True
                break  # restart redistribution
            else:
                # provisional give; will be finalised once nobody clips
                pass
        if not clipped_this_pass:
            # Distribute according to weights; nobody clips
            for room_id, w in weights.items():
                if w <= _EPSILON_M2:
                    continue
                share = remaining * (w / total_weight)
                assigned[room_id] += share
            remaining = 0.0
            break

    return max(0.0, remaining)


__all__ = [
    "AllocationResult",
    "distribute_surplus",
]
