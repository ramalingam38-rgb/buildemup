"""
C16 Phase β — Scheduling
==========================

Per v0.5 LOCKED spec § 3 Phase β.

INPUT:
    - EnvelopeAssembly (from Phase α)

PROCESSING:
    Produces per-floor schedule entries:
      - DoorScheduleEntry per door (numbered, sized for working drawing)
      - WindowScheduleEntry per window (empty in v1 since Phase α
        emits no windows; B-C16-WINDOW-UPSTREAM-CONTRACT)
      - FinishScheduleEntry per room (default finishes per category)

OUTPUT:
    SchedulingResult — schedules indexed by floor_level.

R-INVARIANTS:
    R7c — canonical lex-ASC ordering of every schedule
    R8  — schedule entries carry the upstream element identities
          (passthrough)
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c16.schema import (
    DoorScheduleEntry,
    FinishScheduleEntry,
    FloorGeometry,
    WindowScheduleEntry,
)
from buildemup.components.c16.phases.alpha_envelope import EnvelopeAssembly


# ============================================================
# Per-category default finishes (Indian residential, mid-tier)
# ============================================================
#
# These are NBC-compatible defaults. Per Sub-1 Principle 2 (advisory
# tone), B-C16-FINISH-DEFAULTS-FROM-BRIEF will move these from C16
# defaults to brief-driven choice post-LOCK.
_DEFAULT_FLOOR_FINISH_BY_CATEGORY = {
    "BEDROOM":  "vitrified_tile",
    "LIVING":   "vitrified_tile",
    "KITCHEN":  "ceramic_tile",
    "BATHROOM": "anti_skid_ceramic_tile",
    "BALCONY":  "anti_skid_ceramic_tile",
    "STAIRCASE": "granite",
    "OTHER":    "vitrified_tile",
}
_DEFAULT_WALL_FINISH = "emulsion_paint"
_DEFAULT_CEILING_FINISH = "emulsion_paint"
_DEFAULT_WET_WALL_FINISH = "ceramic_tile"


@dataclass(frozen=True)
class FloorSchedules:
    """Schedules for one floor."""
    floor_level:        int
    door_schedule:      tuple[DoorScheduleEntry, ...]
    window_schedule:    tuple[WindowScheduleEntry, ...]
    finish_schedule:    tuple[FinishScheduleEntry, ...]


@dataclass(frozen=True)
class SchedulingResult:
    """Phase β output: schedules per floor in canonical floor order."""
    per_floor: tuple[FloorSchedules, ...]


# ============================================================
# Phase β
# ============================================================

def execute_phase_beta(
    *,
    envelope: EnvelopeAssembly,
) -> SchedulingResult:
    """Phase β main entry point. Pure function over envelope."""
    per_floor: list[FloorSchedules] = []

    door_counter = 0
    window_counter = 0
    finish_counter = 0

    for fg in envelope.floor_geometries:
        # Door schedule (numbered globally for byte-equal replay)
        door_entries: list[DoorScheduleEntry] = []
        for d in fg.doors:
            door_counter += 1
            door_entries.append(DoorScheduleEntry(
                door_identity=d.identity,
                schedule_id=f"DS:{door_counter:04d}",
                door_number=f"D{door_counter:03d}",
                width_mm=d.clear_width_mm,
                height_mm=2100,
                material="wood",
            ))

        # Window schedule (empty v1)
        window_entries: list[WindowScheduleEntry] = []
        for w in fg.windows:
            window_counter += 1
            window_entries.append(WindowScheduleEntry(
                window_identity=w.identity,
                schedule_id=f"WS:{window_counter:04d}",
                window_number=f"W{window_counter:03d}",
                width_mm=w.width_mm,
                height_mm=w.head_height_mm - w.sill_height_mm,
                material="aluminium",
            ))

        # Finish schedule (per room)
        finish_entries: list[FinishScheduleEntry] = []
        for r in fg.rooms:
            finish_counter += 1
            cat_norm = (r.category or "OTHER").upper()
            floor_finish = _DEFAULT_FLOOR_FINISH_BY_CATEGORY.get(
                cat_norm, _DEFAULT_FLOOR_FINISH_BY_CATEGORY["OTHER"],
            )
            wall_finish = (
                _DEFAULT_WET_WALL_FINISH
                if cat_norm in ("BATHROOM", "KITCHEN")
                else _DEFAULT_WALL_FINISH
            )
            finish_entries.append(FinishScheduleEntry(
                room_identity=r.identity,
                schedule_id=f"FS:{finish_counter:04d}",
                floor_finish=floor_finish,
                wall_finish=wall_finish,
                ceiling_finish=_DEFAULT_CEILING_FINISH,
            ))

        per_floor.append(FloorSchedules(
            floor_level=fg.floor_level,
            door_schedule=tuple(door_entries),
            window_schedule=tuple(window_entries),
            finish_schedule=tuple(finish_entries),
        ))

    return SchedulingResult(per_floor=tuple(per_floor))
