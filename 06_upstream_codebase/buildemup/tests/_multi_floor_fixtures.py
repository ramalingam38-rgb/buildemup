"""Multi-floor test fixtures (B-NEW-T3 build session).

Per Spec #4 v1.6 LOCKED § 5.3: builder helpers for multi-floor briefs +
WetZonePlannedCandidate wrappers used across the Sub-3 + integration
test suites.

Strategy: reuse the C5..C10 pipeline to produce a real
WetZonePlannedCandidate, then `dataclasses.replace` to clone the ancestry
with manipulated `floor_label` and per-room `is_master` flags. This
avoids the heavy cost of running the real pipeline N times for N-floor
test fixtures.
"""
from __future__ import annotations

import dataclasses
from functools import lru_cache
from typing import Any

from buildemup.components.c09.schema import RoomCategory
from buildemup.components.c10 import plan_wet_zones
from buildemup.components.c10.schema import WetZonePlannedCandidate
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.domain.multi_floor_brief import MultiFloorDwellingBrief
from buildemup.domain.multi_floor_candidate import (
    MultiFloorWetZonePlannedCandidate,
)
from buildemup.tests._c10_fixtures import run_c9_pipeline


# ---------------------------------------------------------------------------
# Brief builders
# ---------------------------------------------------------------------------


def make_two_floor_brief_with_master_on(label: str = "ground") -> MultiFloorDwellingBrief:
    """Build a 2-floor MultiFloorDwellingBrief with master on the
    given label. Both floors have bedrooms (so either is eligible
    as a master target)."""
    ground = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        floor_label="ground",
    )
    first = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        floor_label="first",
    )
    return MultiFloorDwellingBrief(
        floors=(ground, first),
        master_bedroom_floor_label=label,
    )


def make_three_floor_brief_with_master_on(label: str = "ground") -> MultiFloorDwellingBrief:
    """Build a 3-floor MultiFloorDwellingBrief; all three floors have
    bedrooms (so M8's eligible-target set has size 2)."""
    ground = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        floor_label="ground",
    )
    first = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        floor_label="first",
    )
    second = FloorRoomBrief(
        bedroom_count=1,
        bathroom_count=1,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        floor_label="second",
    )
    return MultiFloorDwellingBrief(
        floors=(ground, first, second),
        master_bedroom_floor_label=label,
    )


# ---------------------------------------------------------------------------
# Per-floor WetZonePlannedCandidate cloning
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _base_wzpc() -> WetZonePlannedCandidate:
    """Cached real WZPC from the C5..C10 pipeline."""
    rsc_tuple, brief, grid, plot_analysis = run_c9_pipeline()
    wzpc_tuple = plan_wet_zones(rsc_tuple, brief, grid, plot_analysis)
    assert len(wzpc_tuple) >= 1
    return wzpc_tuple[0]


def clone_wzpc(
    *,
    floor_label: str,
    keep_master_bedroom: bool,
) -> WetZonePlannedCandidate:
    """Clone the cached base WZPC with manipulated floor_label and
    is_master designation on the rooms. Used to synthesise multi-floor
    fixture wrappers without re-running the full pipeline per floor.
    """
    base = _base_wzpc()
    base_rsc = base.room_sized_candidate
    base_rst = base_rsc.room_size_table
    base_prov = base_rsc.provenance

    new_rooms = []
    seen_first_bedroom = False
    seen_first_bathroom = False
    for r in base_rst.rooms:
        is_master = r.is_master
        if r.category == RoomCategory.BEDROOM:
            if not seen_first_bedroom:
                is_master = keep_master_bedroom
                seen_first_bedroom = True
            else:
                is_master = False
        elif r.category == RoomCategory.BATHROOM:
            if not seen_first_bathroom:
                is_master = keep_master_bedroom
                seen_first_bathroom = True
            else:
                is_master = False
        else:
            is_master = False
        new_rooms.append(dataclasses.replace(r, is_master=is_master))

    new_rst = dataclasses.replace(
        base_rst, rooms=tuple(new_rooms), floor_label=floor_label,
    )
    new_prov = dataclasses.replace(base_prov, floor_label=floor_label)
    new_rsc = dataclasses.replace(
        base_rsc, room_size_table=new_rst, provenance=new_prov,
    )
    return dataclasses.replace(base, room_sized_candidate=new_rsc)


# ---------------------------------------------------------------------------
# Multi-floor wrapper builders
# ---------------------------------------------------------------------------


def make_two_floor_wrapper_master_ground() -> MultiFloorWetZonePlannedCandidate:
    return MultiFloorWetZonePlannedCandidate(
        floors=(
            clone_wzpc(floor_label="ground", keep_master_bedroom=True),
            clone_wzpc(floor_label="first", keep_master_bedroom=False),
        ),
        master_bedroom_floor_label="ground",
    )


def make_two_floor_wrapper_master_first() -> MultiFloorWetZonePlannedCandidate:
    return MultiFloorWetZonePlannedCandidate(
        floors=(
            clone_wzpc(floor_label="ground", keep_master_bedroom=False),
            clone_wzpc(floor_label="first", keep_master_bedroom=True),
        ),
        master_bedroom_floor_label="first",
    )


def make_three_floor_wrapper_master_ground() -> MultiFloorWetZonePlannedCandidate:
    return MultiFloorWetZonePlannedCandidate(
        floors=(
            clone_wzpc(floor_label="ground", keep_master_bedroom=True),
            clone_wzpc(floor_label="first", keep_master_bedroom=False),
            clone_wzpc(floor_label="second", keep_master_bedroom=False),
        ),
        master_bedroom_floor_label="ground",
    )


# ---------------------------------------------------------------------------
# Pipeline runner (multi-floor C9 + C10 cascade) — simulated for tests
# ---------------------------------------------------------------------------


def run_multi_floor_c9_c10_pipeline(
    brief: MultiFloorDwellingBrief,
) -> MultiFloorWetZonePlannedCandidate:
    """Simulate the multi-floor C9 + C10 cascade per the canonical
    construction pseudocode in Spec #3 § 3.1.

    Uses the fixture clone_wzpc helper so the cascade is fast for tests.
    Production wires the real per-floor C9 + C10 calls. The simulated
    version honors the has_master_bedroom flag from
    iter_floors_with_master_flag().
    """
    per_floor_wzpcs = []
    for floor_brief, has_master in brief.iter_floors_with_master_flag():
        wzpc = clone_wzpc(
            floor_label=floor_brief.floor_label,
            keep_master_bedroom=has_master,
        )
        per_floor_wzpcs.append(wzpc)
    return MultiFloorWetZonePlannedCandidate(
        floors=tuple(per_floor_wzpcs),
        master_bedroom_floor_label=brief.master_bedroom_floor_label,
    )


__all__ = [
    "make_two_floor_brief_with_master_on",
    "make_three_floor_brief_with_master_on",
    "clone_wzpc",
    "make_two_floor_wrapper_master_ground",
    "make_two_floor_wrapper_master_first",
    "make_three_floor_wrapper_master_ground",
    "run_multi_floor_c9_c10_pipeline",
]
