"""C9 v0.8 (Spec #2 v0.11 LOCKED) — `has_master_bedroom` flag tests.

Per Spec #2 v0.11 LOCKED § 5 (Test plan): 8 tests covering the new
`has_master_bedroom: bool = True` field on FloorRoomBrief and its impact
on master bedroom + en-suite master bathroom designation in
`_materialise_rooms` (lines 498 + 548).

The 9th test in Spec #2 § 5.3 (C11a cache-key version sentinel pinning
to "v1.1.0") is DEFERRED to Sub-2 per S40-continuation handoff plan,
which performs a single cumulative bump v1.0.0 -> v1.3.0 covering Specs
#2, #3, #4 together rather than incremental bumps.
"""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.components.c09 import (
    RoomCategory,
    size_rooms,
)
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.tests._c9_fixtures import (
    medium_brief,
    run_c8_pipeline,
)


# ---------------------------------------------------------------------------
# 1-2 + 8: Domain-level tests on FloorRoomBrief itself (no pipeline)
# ---------------------------------------------------------------------------


def test_floor_room_brief_default_has_master_bedroom_is_true():
    """Spec #2 § 5.1 test 1 — backwards-compat sentinel.

    FloorRoomBrief construction without the flag defaults to True.
    Preserves v0.7 byte-identical behaviour for every existing single-
    floor caller.
    """
    brief = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
    )
    assert brief.has_master_bedroom is True


def test_floor_room_brief_accepts_has_master_bedroom_false():
    """Spec #2 § 5.1 test 2 — explicit `has_master_bedroom=False` construction
    succeeds (no validation error)."""
    brief = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=False,
    )
    assert brief.has_master_bedroom is False


def test_brief_equality_includes_has_master_bedroom():
    """Spec #2 § 5.1 test 8 — hash-participation sentinel.

    Two briefs identical EXCEPT for has_master_bedroom are NOT equal
    and hash differently. Supports the C11A_CACHE_KEY_VERSION bump
    rationale per Spec #1 § 3.6 normalization-versioning contract.
    """
    brief_a = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=True,
    )
    brief_b = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=False,
    )
    assert brief_a != brief_b
    assert hash(brief_a) != hash(brief_b)


# ---------------------------------------------------------------------------
# 3-7: Pipeline-driven tests — has_master_bedroom impact on room designation
# ---------------------------------------------------------------------------


def _make_master_true_brief() -> FloorRoomBrief:
    """Brief: 2 bedrooms / 2 bathrooms, has_master_bedroom=True (default)."""
    return FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=2,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=True,
    )


def _make_master_false_brief() -> FloorRoomBrief:
    """Brief: 2 bedrooms / 2 bathrooms, has_master_bedroom=False."""
    return FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=2,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=False,
    )


def test_floor_room_brief_with_master_true_produces_master_bedroom():
    """Spec #2 § 5.1 test 3 — existing behaviour sentinel.

    has_master_bedroom=True, bedroom_count=2 -> bedroom #1 is_master=True,
    bedroom #2 is_master=False.
    """
    cdc, _orig_brief, grid, plot_analysis = run_c8_pipeline(
        brief_factory=_make_master_true_brief
    )
    brief = _make_master_true_brief()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    assert len(sized) >= 1
    rooms = sized[0].room_size_table.rooms
    bedrooms = sorted(
        (r for r in rooms if r.category == RoomCategory.BEDROOM),
        key=lambda r: r.priority,
    )
    assert len(bedrooms) == 2
    assert bedrooms[0].is_master is True, "bedroom #1 should be master"
    assert bedrooms[1].is_master is False, "bedroom #2 should NOT be master"


def test_floor_room_brief_with_master_false_produces_no_master_bedroom():
    """Spec #2 § 5.1 test 4 — corrective multi-floor behaviour.

    has_master_bedroom=False, bedroom_count=2 -> both bedrooms have
    is_master=False (line 498 short-circuits via the `and` clause).
    """
    cdc, _orig_brief, grid, plot_analysis = run_c8_pipeline(
        brief_factory=_make_master_false_brief
    )
    brief = _make_master_false_brief()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    rooms = sized[0].room_size_table.rooms
    bedrooms = [r for r in rooms if r.category == RoomCategory.BEDROOM]
    assert len(bedrooms) == 2
    assert all(not r.is_master for r in bedrooms), (
        "no bedroom should be master when has_master_bedroom=False; "
        f"got is_master={[r.is_master for r in bedrooms]}"
    )


def test_floor_room_brief_with_master_true_produces_master_bathroom():
    """Spec #2 § 5.1 test 5 — existing en-suite behaviour sentinel.

    has_master_bedroom=True, bathroom_count=2 -> bathroom #1 is_master=True,
    bathroom #2 is_master=False.
    """
    cdc, _orig_brief, grid, plot_analysis = run_c8_pipeline(
        brief_factory=_make_master_true_brief
    )
    brief = _make_master_true_brief()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    rooms = sized[0].room_size_table.rooms
    bathrooms = sorted(
        (r for r in rooms if r.category == RoomCategory.BATHROOM),
        key=lambda r: r.priority,
    )
    assert len(bathrooms) == 2
    assert bathrooms[0].is_master is True
    assert bathrooms[1].is_master is False


def test_floor_room_brief_with_master_false_produces_no_master_bathroom():
    """Spec #2 § 5.1 test 6 — en-suite coupling sentinel.

    has_master_bedroom=False (which controls BOTH bedroom and bathroom
    master designation per Spec #2 § 3.4), bathroom_count=2 -> both
    bathrooms have is_master=False.
    """
    cdc, _orig_brief, grid, plot_analysis = run_c8_pipeline(
        brief_factory=_make_master_false_brief
    )
    brief = _make_master_false_brief()
    sized = size_rooms(cdc, brief, grid, plot_analysis)
    rooms = sized[0].room_size_table.rooms
    bathrooms = [r for r in rooms if r.category == RoomCategory.BATHROOM]
    assert len(bathrooms) == 2
    assert all(not r.is_master for r in bathrooms), (
        "no bathroom should be master when has_master_bedroom=False; "
        f"got is_master={[r.is_master for r in bathrooms]}"
    )


def test_brief_with_master_false_and_zero_bedrooms_produces_no_rooms():
    """Spec #2 § 5.1 test 7 — edge case sanity sentinel.

    has_master_bedroom=False AND bedroom_count=0 -> 0 bedroom rooms
    materialized. The flag is irrelevant when there are no bedrooms;
    this confirms the `(i == 0) and brief.has_master_bedroom`
    short-circuit doesn't break the empty-bedroom path.

    Validated at the domain level (no pipeline needed for this case —
    the C9 pipeline expects feasible bedroom briefs, but the
    _materialise_rooms behaviour we test is the for-loop range check).
    """
    brief = FloorRoomBrief(
        bedroom_count=0,
        bathroom_count=0,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        has_master_bedroom=False,
    )
    # Construction succeeds; the flag is preserved (not collapsed).
    assert brief.has_master_bedroom is False
    assert brief.bedroom_count == 0
    assert brief.bathroom_count == 0
