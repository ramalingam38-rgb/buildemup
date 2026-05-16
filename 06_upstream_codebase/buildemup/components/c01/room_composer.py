"""
BuildemUp† — Room Composer (Component 1).

Handles room composition logic per SPEC_v0.2 Sections 4.3 + 4.4:

1. Default templates (typical Indian residential patterns) so users
   don't start with a blank form.

2. Circulation factor (1.30) applied to total_room_area_sqm to get
   estimated total_floor_area_sqm — per Drawback 5 fix.

3. Auto-staircase enforcement for floors ≥ 2 — per Drawback 8 fix.
   If user didn't explicitly add STAIRCASE on any floor in a multi-floor
   design, we add one to the ground floor with an INFO guidance message.

All operations are PURE: they take a brief (or floor list) and return
a new version + guidance messages. No mutation of input.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import replace

from buildemup.domain.brief import (
    GuidanceMessage, GuidanceSeverity,
)
from buildemup.domain.floor_requirement import (
    FloorRequirement, RoomRequirement, FloorUse, RoomType,
    NBC_MINIMUM_ROOM_SIZES_SQM,
)
from buildemup.utils.kb_rules_loader import (
    get_circulation_factor, get_circulation_factor_for_size,
)


# ─────────────────────────────────────────────────────────────────────────
# Floor area estimation (Drawback 5)
# ─────────────────────────────────────────────────────────────────────────

def estimate_floor_area_sqm(floor: FloorRequirement) -> float:
    """Estimate total floor area including circulation.

    Per SPEC_v0.2 Section 4.3 (Drawback 5 fix):
    total_floor_area = sum(room areas) × circulation_factor (1.30)

    The factor accounts for walls, passages, internal circulation,
    stairs — the 25-35% of a floor that isn't "room area" but is
    still part of built-up area.

    For STILT_PARKING floors, we estimate roughly 3 sqm per car space,
    since user wouldn't typically itemize parking rooms.

    For TERRACE_INACCESSIBLE floors, we return 0 for built-up (the
    terrace is above, not a usable floor).

    For TERRACE_ACCESSIBLE, we use the sum of any rooms (water tank
    space, etc.) × circulation factor.
    """
    if floor.floor_use == FloorUse.STILT_PARKING:
        # Rough heuristic: a stilt parking floor takes most of the
        # envelope area — we return 0 here since it's "unbuilt" for
        # built-up-area purposes. Component 7 handles structural load
        # via its own FloorType mapping.
        # For budget estimation, stilt is structure only (no finishes)
        # which Component 7 captures.
        return 0.0

    if floor.floor_use == FloorUse.TERRACE_INACCESSIBLE:
        return 0.0

    room_area = floor.total_room_area_sqm()
    # Size-aware circulation factor per IS 3861-2002 research:
    # small homes (< 30 sqm/floor) = 1.40, large (> 100) = 1.30, typical = 1.35
    factor, _ = get_circulation_factor_for_size(room_area)
    return room_area * factor


def get_circulation_factor_label_for_floors(
    floors: tuple[FloorRequirement, ...],
) -> tuple[float, str]:
    """Return the dominant circulation factor and size label for a brief.

    Used by assumptions_log to disclose the actual factor applied.
    Averages across residential floors only (stilt/terrace don't count).
    """
    residential_areas = [
        f.total_room_area_sqm() for f in floors
        if f.floor_use == FloorUse.RESIDENTIAL and f.total_room_area_sqm() > 0
    ]
    if not residential_areas:
        return get_circulation_factor(), "typical"
    # Use average per-floor room area to pick the factor
    avg_area = sum(residential_areas) / len(residential_areas)
    return get_circulation_factor_for_size(avg_area)


def estimate_total_built_area_sqm(
    floors: tuple[FloorRequirement, ...],
) -> float:
    """Sum of estimated floor areas across all floors."""
    return sum(estimate_floor_area_sqm(f) for f in floors)


def estimate_total_built_area_sqft(
    floors: tuple[FloorRequirement, ...],
) -> float:
    """Same, in square feet (user-facing display)."""
    return estimate_total_built_area_sqm(floors) * 10.7639


# ─────────────────────────────────────────────────────────────────────────
# Default floor templates
# ─────────────────────────────────────────────────────────────────────────

def default_ground_floor_template() -> FloorRequirement:
    """Typical Indian ground-floor defaults.

    1 Living, 1 Kitchen, 1 Common Bathroom, 1 Pooja.
    User edits as desired — this just gives them a starting point.
    """
    return FloorRequirement(
        floor_number=0,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(RoomType.LIVING, count=1),
            RoomRequirement(RoomType.KITCHEN, count=1),
            RoomRequirement(RoomType.BATHROOM_COMMON, count=1),
            RoomRequirement(RoomType.POOJA, count=1),
        ),
    )


def default_upper_floor_template(floor_number: int) -> FloorRequirement:
    """Typical upper-floor defaults: 1 master + 1 regular bedroom + baths."""
    return FloorRequirement(
        floor_number=floor_number,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(
            RoomRequirement(RoomType.BEDROOM_MASTER, count=1),
            RoomRequirement(RoomType.BATHROOM_ATTACHED, count=1),
            RoomRequirement(RoomType.BEDROOM_REGULAR, count=1),
            RoomRequirement(RoomType.BATHROOM_COMMON, count=1),
        ),
    )


def default_terrace_template(floor_number: int) -> FloorRequirement:
    """Terrace defaults: accessible with water tank space (utility)."""
    return FloorRequirement(
        floor_number=floor_number,
        floor_use=FloorUse.TERRACE_ACCESSIBLE,
        rooms=(
            RoomRequirement(RoomType.UTILITY, count=1),
        ),
    )


def default_floors_for_storeys(total_storeys: int) -> tuple[FloorRequirement, ...]:
    """Build a default floor set for N storeys.

    G only: 1 floor (ground).
    G+1: 2 floors (ground + first).
    G+2: 3 floors (ground + first + second).
    G+3: 4 floors (ground + first + second + terrace).
    """
    if total_storeys < 1 or total_storeys > 4:
        raise ValueError(
            f"total_storeys must be 1..4 (G to G+3). Got {total_storeys}."
        )

    floors = [default_ground_floor_template()]

    for i in range(1, total_storeys):
        if i == total_storeys - 1 and total_storeys >= 3:
            # Top floor of G+2 or G+3 can be terrace
            floors.append(default_terrace_template(i))
        else:
            floors.append(default_upper_floor_template(i))

    return tuple(floors)


# ─────────────────────────────────────────────────────────────────────────
# Auto-staircase (Drawback 8)
# ─────────────────────────────────────────────────────────────────────────

def ensure_staircase_present(
    floors: tuple[FloorRequirement, ...],
) -> tuple[tuple[FloorRequirement, ...], list[GuidanceMessage]]:
    """If multi-floor design lacks a staircase, auto-add to ground floor.

    Per SPEC_v0.2 Section 4.4 (Drawback 8 fix):
    When total_storeys ≥ 2 and no floor has a STAIRCASE room, we add
    NBC-minimum staircase (5.5 sqm) to the ground floor and emit an
    INFO message telling the user we did this.

    Returns:
      (updated_floors, guidance_messages)
    """
    # Only one floor = no staircase needed (single-storey home)
    if len(floors) < 2:
        return floors, []

    # Does any floor already have a staircase?
    has_staircase_anywhere = any(f.has_staircase for f in floors)
    if has_staircase_anywhere:
        return floors, []

    # Find ground floor (floor_number == 0)
    ground_idx = None
    for i, f in enumerate(floors):
        if f.floor_number == 0:
            ground_idx = i
            break

    if ground_idx is None:
        # Shouldn't happen given Brief validation, but defensive
        return floors, []

    ground = floors[ground_idx]
    # Stilt parking can't have rooms, so if ground is stilt, add to floor 1 instead
    if ground.floor_use == FloorUse.STILT_PARKING:
        target_idx = ground_idx + 1
        target_label = "first floor"
        # Safety check — should always have at least floor 1 if stilt is ground
        if target_idx >= len(floors):
            return floors, []
    else:
        target_idx = ground_idx
        target_label = "ground floor"

    # Add STAIRCASE to target floor's rooms tuple
    target = floors[target_idx]
    new_rooms = target.rooms + (
        RoomRequirement(RoomType.STAIRCASE, count=1),
    )
    updated_target = replace(target, rooms=new_rooms)

    updated_floors = (
        floors[:target_idx] + (updated_target,) + floors[target_idx + 1:]
    )

    message = GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            f"Staircase was not specified on any floor. "
            f"We've added one to the {target_label} using the NBC minimum "
            f"(5.5 sqm including landing). You can override the size "
            f"or location in the editor."
        ),
        context="auto_staircase",
        action_verb="Adjust",
    )
    return updated_floors, [message]
