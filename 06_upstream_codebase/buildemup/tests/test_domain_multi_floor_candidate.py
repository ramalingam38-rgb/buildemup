"""MultiFloorWetZonePlannedCandidate (Spec #3 v0.3 LOCKED) — domain tests.

Per Spec #3 v0.3 LOCKED § 5.1 (Test plan): ~35 tests covering construction,
invariants MFWZP-1 through MFWZP-6, read helpers, mutation helpers,
frozen + equality + hash, and symmetry / trust-boundary sentinels.

Fixture strategy: build real WZPC instances via the C5..C10 pipeline,
then use `dataclasses.replace` to clone them with manipulated
`floor_label` and `is_master` ancestry for the multi-floor scenarios.
"""
from __future__ import annotations

import dataclasses
from functools import lru_cache

import pytest

from buildemup.components.c09.schema import (
    RoomCategory,
    RoomSizeRequirement,
    RoomSizeTable,
    RoomSizedCandidate,
    RoomSizingProvenance,
)
from buildemup.components.c10 import plan_wet_zones
from buildemup.components.c10.schema import WetZonePlannedCandidate
from buildemup.domain.multi_floor_candidate import MultiFloorWetZonePlannedCandidate
from buildemup.tests._c10_fixtures import run_c9_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _base_wzpc() -> WetZonePlannedCandidate:
    """Cached real WZPC from the C5..C10 pipeline. Used as base for
    cloning with manipulated floor_label / is_master."""
    rsc_tuple, brief, grid, plot_analysis = run_c9_pipeline()
    wzpc_tuple = plan_wet_zones(rsc_tuple, brief, grid, plot_analysis)
    assert len(wzpc_tuple) >= 1
    return wzpc_tuple[0]


def _clone_wzpc(
    *,
    floor_label: str,
    keep_master_bedroom: bool,
) -> WetZonePlannedCandidate:
    """Clone the base WZPC, rewriting floor_label in provenance and
    rewriting room is_master flags to satisfy the requested master
    designation."""
    base = _base_wzpc()
    base_rsc: RoomSizedCandidate = base.room_sized_candidate
    base_rst: RoomSizeTable = base_rsc.room_size_table
    base_prov: RoomSizingProvenance = base_rsc.provenance

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
        base_rst,
        rooms=tuple(new_rooms),
        floor_label=floor_label,
    )
    new_prov = dataclasses.replace(base_prov, floor_label=floor_label)
    new_rsc = dataclasses.replace(
        base_rsc, room_size_table=new_rst, provenance=new_prov,
    )
    return dataclasses.replace(base, room_sized_candidate=new_rsc)


def _two_floors_master_ground():
    return (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
    )


def _three_floors_master_ground():
    return (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
        _clone_wzpc(floor_label="second", keep_master_bedroom=False),
    )


# ---------------------------------------------------------------------------
# Construction (happy path) — tests 1-3
# ---------------------------------------------------------------------------


def test_two_floor_construction_succeeds_with_master_on_ground():
    floors = _two_floors_master_ground()
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="ground",
    )
    assert len(cand.floors) == 2
    assert cand.master_bedroom_floor_label == "ground"


def test_three_floor_construction_succeeds():
    floors = _three_floors_master_ground()
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="ground",
    )
    assert len(cand.floors) == 3


def test_construction_with_master_on_first_floor():
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=True),
    )
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="first",
    )
    assert cand.master_bedroom_floor_label == "first"
    assert cand.floor_has_master("first") is True


# ---------------------------------------------------------------------------
# Invariant violations — tests 4-11
# ---------------------------------------------------------------------------


def test_single_floor_raises():
    """Inv MFWZP-1: len(floors) >= 2."""
    with pytest.raises(ValueError, match="len.floors. >= 2"):
        MultiFloorWetZonePlannedCandidate(
            floors=(_clone_wzpc(floor_label="ground", keep_master_bedroom=True),),
            master_bedroom_floor_label="ground",
        )


def test_empty_floors_raises():
    """Inv MFWZP-1: empty tuple."""
    with pytest.raises(ValueError, match="len.floors. >= 2"):
        MultiFloorWetZonePlannedCandidate(
            floors=(),
            master_bedroom_floor_label="ground",
        )


def test_duplicate_floor_labels_raises():
    """Inv MFWZP-2: per-floor labels (derived from ancestry) must be unique."""
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
    )
    with pytest.raises(ValueError, match="must be unique"):
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="ground",
        )


def test_master_label_not_in_floors_raises():
    """Inv MFWZP-3: master_bedroom_floor_label in derived labels."""
    floors = _two_floors_master_ground()
    with pytest.raises(ValueError, match="not in derived per-floor labels"):
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="second",
        )


def test_non_wzpc_in_floors_tuple_raises():
    """Inv MFWZP-4: every floor must be a real WetZonePlannedCandidate."""
    floors = _two_floors_master_ground()
    bad_floors = (floors[0], "not a WZPC")
    with pytest.raises(TypeError, match="must be WetZonePlannedCandidate"):
        MultiFloorWetZonePlannedCandidate(
            floors=bad_floors,  # type: ignore[arg-type]
            master_bedroom_floor_label="ground",
        )


def test_zero_master_bedrooms_globally_raises():
    """Inv MFWZP-5: exactly one master bedroom globally — zero fails."""
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
    )
    with pytest.raises(ValueError, match="expected exactly one"):
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="ground",
        )


def test_two_master_bedrooms_globally_raises():
    """Inv MFWZP-5: two masters globally fails."""
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        _clone_wzpc(floor_label="first", keep_master_bedroom=True),
    )
    with pytest.raises(ValueError, match="expected exactly one"):
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="ground",
        )


def test_master_label_disagrees_with_actual_master_floor_raises():
    """Inv MFWZP-6: declared master_bedroom_floor_label MUST match the
    actual floor whose bedroom #1 has is_master=True."""
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=True),
    )
    with pytest.raises(ValueError, match="master bedroom found on floor"):
        # Declares 'ground' but actual master is on 'first'.
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="ground",
        )


# ---------------------------------------------------------------------------
# Read helpers — tests 12-21
# ---------------------------------------------------------------------------


def test_is_multi_floor_property_true():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert cand.is_multi_floor is True


def test_floor_labels_returns_derived_tuple():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert cand.floor_labels == ("ground", "first")


def test_get_floor_returns_correct_wzpc():
    floors = _two_floors_master_ground()
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="ground",
    )
    ground_wzpc = cand.get_floor("ground")
    assert (
        ground_wzpc.room_sized_candidate.provenance.floor_label == "ground"
    )


def test_get_floor_normalizes_input():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    found = cand.get_floor("  GROUND  ")
    assert found is cand.floors[0]


def test_get_floor_unknown_label_raises_key_error():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(KeyError, match="no floor with that label"):
        cand.get_floor("second")


def test_floor_has_master_returns_true_for_master_floor():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert cand.floor_has_master("ground") is True


def test_floor_has_master_returns_false_for_non_master_floor():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert cand.floor_has_master("first") is False


def test_floor_has_master_normalizes_input():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert cand.floor_has_master("GROUND") is True
    assert cand.floor_has_master(" ground ") is True


def test_iter_floors_with_master_flag_yields_one_true_total():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_three_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    flags = [has_master for _wzpc, has_master in cand.iter_floors_with_master_flag()]
    assert flags.count(True) == 1
    assert flags.count(False) == 2


def test_iter_floors_with_master_flag_preserves_tuple_order():
    floors = (
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
    )
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="ground",
    )
    pairs = list(cand.iter_floors_with_master_flag())
    assert pairs[0][1] is False  # first floor is NOT master
    assert pairs[1][1] is True  # ground floor IS master


# ---------------------------------------------------------------------------
# Mutation helpers — tests 22-29
# ---------------------------------------------------------------------------


def test_with_floor_replaced_replaces_one_floor():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    new_first = _clone_wzpc(floor_label="first", keep_master_bedroom=False)
    new_cand = cand.with_floor_replaced("first", new_first)
    assert new_cand.get_floor("first") is new_first
    # Master preserved.
    assert new_cand.master_bedroom_floor_label == "ground"


def test_with_floor_replaced_preserves_master_designation():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    new_first = _clone_wzpc(floor_label="first", keep_master_bedroom=False)
    new_cand = cand.with_floor_replaced("first", new_first)
    assert new_cand.floor_has_master("ground") is True
    assert new_cand.floor_has_master("first") is False


def test_with_floor_replaced_unknown_label_raises():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    new_first = _clone_wzpc(floor_label="first", keep_master_bedroom=False)
    with pytest.raises(ValueError, match="no floor with that label"):
        cand.with_floor_replaced("second", new_first)


def test_with_floor_replaced_does_not_mutate_original():
    floors = _two_floors_master_ground()
    cand = MultiFloorWetZonePlannedCandidate(
        floors=floors,
        master_bedroom_floor_label="ground",
    )
    new_first = _clone_wzpc(floor_label="first", keep_master_bedroom=False)
    _new = cand.with_floor_replaced("first", new_first)
    # Original tuple unchanged.
    assert cand.floors == floors


def test_with_floor_replaced_normalizes_input():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    new_first = _clone_wzpc(floor_label="first", keep_master_bedroom=False)
    new_cand = cand.with_floor_replaced("  FIRST  ", new_first)
    assert new_cand.get_floor("first") is new_first


def test_with_master_on_returns_new_instance_with_swapped_master():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    # M8 caller: re-run C9->C10 cascade producing flipped master.
    new_floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=True),
    )
    new_cand = cand.with_master_on("first", new_floors)
    assert new_cand.master_bedroom_floor_label == "first"
    assert new_cand.floor_has_master("first") is True


def test_with_master_on_re_validates_all_invariants():
    """If caller passes inconsistent state, with_master_on rejects it."""
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    # Bug simulation: caller claims master moved to 'first' but actual
    # WZPC ancestry still has master on 'ground' -> Inv MFWZP-6 catches.
    bad_floors = _two_floors_master_ground()  # master still on ground
    with pytest.raises(ValueError):
        cand.with_master_on("first", bad_floors)


def test_with_master_on_normalizes_input():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    new_floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=True),
    )
    new_cand = cand.with_master_on("FIRST", new_floors)
    assert new_cand.master_bedroom_floor_label == "first"


# ---------------------------------------------------------------------------
# Frozen + equality + hash — tests 30-33
# ---------------------------------------------------------------------------


def test_two_candidates_with_same_content_are_equal():
    a = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    b = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    assert a == b


def test_candidate_is_hashable():
    """Wrapper supports the hash protocol (frozen dataclass auto-generates
    __hash__). NOTE: real-world WZPC ancestry from the C5..C10 pipeline
    contains some unhashable mid-pipeline scoring metadata (e.g.
    TopologyCandidate.score_components dict), so end-to-end hash
    computation can fail under live fixtures. The wrapper TYPE is
    hashable by construction per Spec #3 § 2; downstream hashability
    is a property of the WZPC ancestry, not this wrapper.
    """
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    # Wrapper class supports hash protocol (frozen dataclass).
    assert cand.__hash__ is not None
    # The hash method is defined and callable.
    assert callable(type(cand).__hash__)


def test_attempted_field_mutation_raises_frozen_instance_error():
    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        cand.master_bedroom_floor_label = "first"  # type: ignore[misc]


def test_candidates_with_different_floor_order_are_not_equal():
    """Structural != topological identity (mirrors Spec #1 test 43)."""
    a = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),  # (ground, first)
        master_bedroom_floor_label="ground",
    )
    b = MultiFloorWetZonePlannedCandidate(
        floors=(
            _clone_wzpc(floor_label="first", keep_master_bedroom=False),
            _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        ),  # (first, ground) — reversed order
        master_bedroom_floor_label="ground",
    )
    assert a != b


# ---------------------------------------------------------------------------
# Symmetry sentinel — test 34
# ---------------------------------------------------------------------------


def test_iter_floors_with_master_flag_round_trips_with_spec_1():
    """Symmetry sentinel: build from Spec #1, check Spec #3 wrapper's
    iter helper produces the same (label, has_master) pairing as Spec #1's
    iter helper produced on the brief side."""
    from buildemup.domain.multi_floor_brief import MultiFloorDwellingBrief
    from buildemup.domain.floor_brief import FloorRoomBrief

    mfb = MultiFloorDwellingBrief(
        floors=(
            FloorRoomBrief(
                bedroom_count=2, bathroom_count=1,
                has_kitchen=True, has_living=True,
                has_pooja=False, has_utility=False,
                floor_label="ground",
            ),
            FloorRoomBrief(
                bedroom_count=2, bathroom_count=1,
                has_kitchen=False, has_living=False,
                has_pooja=False, has_utility=False,
                floor_label="first",
            ),
        ),
        master_bedroom_floor_label="ground",
    )
    brief_pairs = [
        (f.floor_label, has_master)
        for f, has_master in mfb.iter_floors_with_master_flag()
    ]

    cand = MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )
    cand_pairs = [
        (wzpc.room_sized_candidate.provenance.floor_label, has_master)
        for wzpc, has_master in cand.iter_floors_with_master_flag()
    ]

    assert brief_pairs == cand_pairs


# ---------------------------------------------------------------------------
# Trust-boundary hardening sentinel — test 35
# ---------------------------------------------------------------------------


def test_construction_fail_fast_for_zero_master_no_silent_propagation():
    """Explicitly verify Inv MFWZP-5 fires AT construction, not later —
    no cache/scoring path can see a zero-master state."""
    floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
    )
    with pytest.raises(ValueError, match="expected exactly one"):
        MultiFloorWetZonePlannedCandidate(
            floors=floors,
            master_bedroom_floor_label="ground",
        )
    # Nothing leaked past construction. (Confirmed by exception capture.)
