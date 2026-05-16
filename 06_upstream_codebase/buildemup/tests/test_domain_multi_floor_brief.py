"""MultiFloorDwellingBrief (Spec #1 v0.5 LOCKED) — domain tests.

Per Spec #1 v0.5 LOCKED § 5.1 (Test plan): 45 tests covering construction,
invariants MFDB-1 through MFDB-6, label normalization, read helpers,
mutation helper, frozen + hashability, nested-object-identity sentinel,
and C11a-integration sentinel.
"""
from __future__ import annotations

import dataclasses

import pytest

from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.domain.multi_floor_brief import (
    MultiFloorDwellingBrief,
    _normalize_label,
    _VALID_SELECTORS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ground(*, bedrooms: int = 2, label: str = "ground") -> FloorRoomBrief:
    return FloorRoomBrief(
        bedroom_count=bedrooms,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
        floor_label=label,
    )


def _first(*, bedrooms: int = 2, label: str = "first") -> FloorRoomBrief:
    return FloorRoomBrief(
        bedroom_count=bedrooms,
        bathroom_count=1,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=False,
        floor_label=label,
    )


def _utility_terrace(*, label: str = "terrace") -> FloorRoomBrief:
    return FloorRoomBrief(
        bedroom_count=0,
        bathroom_count=0,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=True,
        floor_label=label,
    )


# ---------------------------------------------------------------------------
# Construction (happy path) — tests 1-5
# ---------------------------------------------------------------------------


def test_two_floor_construction_succeeds():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert len(brief.floors) == 2
    assert brief.master_bedroom_floor_label == "ground"


def test_three_floor_construction_succeeds():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first(), _utility_terrace()),
        master_bedroom_floor_label="ground",
    )
    assert len(brief.floors) == 3


def test_construction_with_master_on_first_floor():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=1), _first(bedrooms=2)),
        master_bedroom_floor_label="first",
    )
    assert brief.master_bedroom_floor_label == "first"
    assert brief.floor_has_master("first") is True
    assert brief.floor_has_master("ground") is False


def test_construction_with_utility_terrace_floor():
    """Non-livable floor (bedroom_count=0) is PERMITTED per § 3.7."""
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first(), _utility_terrace()),
        master_bedroom_floor_label="ground",
    )
    assert len(brief.floors) == 3
    terrace = brief.get_floor("terrace")
    assert terrace.bedroom_count == 0


def test_default_selector_value_is_first_bedroom():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert brief.master_bedroom_selector == "first_bedroom"


# ---------------------------------------------------------------------------
# Invariant violations — tests 6-14
# ---------------------------------------------------------------------------


def test_single_floor_raises():
    """Inv MFDB-1: len(floors) >= 2."""
    with pytest.raises(ValueError, match="len.floors. >= 2"):
        MultiFloorDwellingBrief(
            floors=(_ground(),),
            master_bedroom_floor_label="ground",
        )


def test_empty_floors_raises():
    """Inv MFDB-1: empty floors tuple."""
    with pytest.raises(ValueError, match="len.floors. >= 2"):
        MultiFloorDwellingBrief(
            floors=(),
            master_bedroom_floor_label="ground",
        )


def test_duplicate_floor_labels_raises():
    """Inv MFDB-2: floor_label must be unique."""
    with pytest.raises(ValueError, match="unique"):
        MultiFloorDwellingBrief(
            floors=(_ground(), _first(label="ground")),
            master_bedroom_floor_label="ground",
        )


def test_duplicate_via_normalization_raises():
    """Inv MFDB-2 post-normalization: 'Ground' and 'ground ' both
    normalize to 'ground' and so are duplicates after normalization."""
    with pytest.raises(ValueError, match="unique"):
        MultiFloorDwellingBrief(
            floors=(_ground(label="Ground"), _first(label="ground ")),
            master_bedroom_floor_label="ground",
        )


def test_master_label_not_in_floors_raises():
    """Inv MFDB-3: master_bedroom_floor_label in floor labels."""
    with pytest.raises(ValueError, match="not in floor labels"):
        MultiFloorDwellingBrief(
            floors=(_ground(), _first()),
            master_bedroom_floor_label="second",
        )


def test_master_floor_has_zero_bedrooms_raises():
    """Inv MFDB-4: master floor must have bedroom_count >= 1."""
    no_bedroom_floor = FloorRoomBrief(
        bedroom_count=0,
        bathroom_count=0,
        has_kitchen=False,
        has_living=False,
        has_pooja=False,
        has_utility=True,
        floor_label="utility",
    )
    with pytest.raises(ValueError, match="bedroom_count"):
        MultiFloorDwellingBrief(
            floors=(_ground(), no_bedroom_floor),
            master_bedroom_floor_label="utility",
        )


def test_invalid_selector_value_raises():
    """Inv MFDB-6 runtime: master_bedroom_selector must be in
    _VALID_SELECTORS."""
    with pytest.raises(ValueError, match="not in valid selectors"):
        MultiFloorDwellingBrief(
            floors=(_ground(), _first()),
            master_bedroom_floor_label="ground",
            master_bedroom_selector="banana",  # type: ignore[arg-type]
        )


def test_empty_string_selector_raises():
    """Inv MFDB-6 runtime: empty-string selector rejected."""
    with pytest.raises(ValueError, match="not in valid selectors"):
        MultiFloorDwellingBrief(
            floors=(_ground(), _first()),
            master_bedroom_floor_label="ground",
            master_bedroom_selector="",  # type: ignore[arg-type]
        )


def test_with_master_on_re_validates_selector():
    """Sanity sentinel: with_master_on re-runs __post_init__ so selector
    is re-validated. Original was valid; result is also valid."""
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
    )
    new = brief.with_master_on("first")
    # Re-construction succeeded; selector preserved.
    assert new.master_bedroom_selector == "first_bedroom"


# ---------------------------------------------------------------------------
# Label normalization — tests 15-23
# ---------------------------------------------------------------------------


def test_label_normalization_lowercase():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(label="GROUND"), _first(label="FIRST")),
        master_bedroom_floor_label="GROUND",
    )
    assert brief.master_bedroom_floor_label == "ground"
    assert "ground" in brief.floor_labels
    assert "first" in brief.floor_labels


def test_label_normalization_strip_whitespace():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(label="  ground  "), _first(label="first")),
        master_bedroom_floor_label="ground",
    )
    assert brief.floor_labels[0] == "ground"


def test_label_normalization_collapse_internal_whitespace():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(label="ground floor"), _first(label="first")),
        master_bedroom_floor_label="ground_floor",
    )
    assert brief.floor_labels[0] == "ground_floor"


def test_master_label_normalized_during_construction():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="GROUND",
    )
    assert brief.master_bedroom_floor_label == "ground"


def test_empty_label_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_label("")


def test_whitespace_only_label_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_label("   ")


def test_non_string_label_raises_type_error():
    with pytest.raises(TypeError, match="must be str"):
        _normalize_label(123)  # type: ignore[arg-type]


def test_normalization_does_NOT_unify_semantic_aliases():
    """MAJOR-1 sentinel: 'first' != '1F' != 'first_floor' even after normalization."""
    assert _normalize_label("first") == "first"
    assert _normalize_label("1F") == "1f"
    assert _normalize_label("first_floor") == "first_floor"
    assert _normalize_label("first") != _normalize_label("1F")
    assert _normalize_label("first") != _normalize_label("first_floor")


def test_pathological_labels_are_accepted():
    """MAJOR-4 explicit: '@@@_floor' is a valid normalized label."""
    assert _normalize_label("@@@_floor") == "@@@_floor"
    assert _normalize_label("___") == "___"
    # Building a brief with pathological labels should succeed.
    brief = MultiFloorDwellingBrief(
        floors=(
            _ground(label="@@@_floor"),
            _first(label="___"),
        ),
        master_bedroom_floor_label="@@@_floor",
    )
    assert "@@@_floor" in brief.floor_labels


# ---------------------------------------------------------------------------
# Read helpers — tests 24-33
# ---------------------------------------------------------------------------


def test_is_multi_floor_property_is_true():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert brief.is_multi_floor is True


def test_get_floor_returns_correct_brief():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    ground = brief.get_floor("ground")
    assert ground.bedroom_count == 2
    assert ground.has_kitchen is True


def test_get_floor_normalizes_input():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    # Pass unnormalized; lookup normalizes before comparison.
    found = brief.get_floor("  GROUND  ")
    assert found.floor_label == "ground"


def test_get_floor_unknown_label_raises_key_error():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(KeyError, match="no floor with that label"):
        brief.get_floor("second")


def test_floor_labels_preserves_tuple_order():
    brief = MultiFloorDwellingBrief(
        floors=(_first(), _ground()),  # first BEFORE ground
        master_bedroom_floor_label="ground",
    )
    assert brief.floor_labels == ("first", "ground")


def test_floor_has_master_returns_true_for_master_floor():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert brief.floor_has_master("ground") is True


def test_floor_has_master_returns_false_for_non_master_floor():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert brief.floor_has_master("first") is False


def test_floor_has_master_normalizes_input():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert brief.floor_has_master("GROUND") is True
    assert brief.floor_has_master(" ground ") is True


def test_iter_floors_with_master_flag_yields_exactly_one_true():
    """Inv MFDB-5 sentinel: exactly one floor canonically designated master."""
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first(), _utility_terrace()),
        master_bedroom_floor_label="ground",
    )
    flags = [has_master for _f, has_master in brief.iter_floors_with_master_flag()]
    assert flags.count(True) == 1
    assert flags.count(False) == 2


def test_iter_floors_with_master_flag_preserves_tuple_order():
    brief = MultiFloorDwellingBrief(
        floors=(_first(), _ground()),  # first BEFORE ground
        master_bedroom_floor_label="ground",
    )
    pairs = list(brief.iter_floors_with_master_flag())
    assert pairs[0][0].floor_label == "first"
    assert pairs[1][0].floor_label == "ground"
    assert pairs[0][1] is False  # first floor is NOT master
    assert pairs[1][1] is True   # ground floor IS master


# ---------------------------------------------------------------------------
# Mutation helper — tests 34-39
# ---------------------------------------------------------------------------


def test_with_master_on_returns_new_instance_with_swapped_master():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
    )
    new = brief.with_master_on("first")
    assert new.master_bedroom_floor_label == "first"
    assert brief.master_bedroom_floor_label == "ground"  # original unchanged


def test_with_master_on_normalizes_input():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
    )
    new = brief.with_master_on("FIRST")
    assert new.master_bedroom_floor_label == "first"


def test_with_master_on_unknown_floor_raises():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(ValueError, match="not a floor label"):
        brief.with_master_on("second")


def test_with_master_on_target_with_zero_bedrooms_raises():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _utility_terrace()),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(ValueError, match="bedroom_count"):
        brief.with_master_on("terrace")


def test_with_master_on_does_not_mutate_original():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
    )
    _new = brief.with_master_on("first")
    assert brief.master_bedroom_floor_label == "ground"


def test_with_master_on_preserves_selector_value():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(bedrooms=2), _first(bedrooms=2)),
        master_bedroom_floor_label="ground",
        master_bedroom_selector="first_bedroom",
    )
    new = brief.with_master_on("first")
    assert new.master_bedroom_selector == "first_bedroom"


# ---------------------------------------------------------------------------
# Frozen + equality + hashability — tests 40-43
# ---------------------------------------------------------------------------


def test_two_briefs_with_same_content_are_equal():
    a = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    b = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert a == b
    assert hash(a) == hash(b)


def test_brief_is_hashable_for_dict_and_set_use():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    s = {brief}
    assert brief in s
    d = {brief: "value"}
    assert d[brief] == "value"


def test_attempted_field_mutation_raises_frozen_instance_error():
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        brief.master_bedroom_floor_label = "first"  # type: ignore[misc]


def test_briefs_with_different_floor_order_are_not_equal():
    """MAJOR-2 sentinel: structural identity != topological identity.
    (ground, first) and (first, ground) are NOT equal even though they
    are topologically equivalent."""
    a = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    b = MultiFloorDwellingBrief(
        floors=(_first(), _ground()),
        master_bedroom_floor_label="ground",
    )
    assert a != b
    assert hash(a) != hash(b)


# ---------------------------------------------------------------------------
# Nested-object-identity sentinel — test 44
# ---------------------------------------------------------------------------


def test_nested_floor_brief_is_rewritten_not_preserved():
    """CRITICAL-1 sentinel: original FloorRoomBrief is NOT preserved at
    brief.floors[i]; construction rewrites via dataclasses.replace.
    """
    ground = _ground(label="GROUND")
    first = _first(label="FIRST")
    brief = MultiFloorDwellingBrief(
        floors=(ground, first),
        master_bedroom_floor_label="GROUND",
    )
    # The stored floors are NOT the same Python objects (rewritten for
    # normalization).
    assert id(brief.floors[0]) != id(ground)
    assert id(brief.floors[1]) != id(first)
    # But the structural content (modulo normalization) matches.
    assert brief.floors[0].bedroom_count == ground.bedroom_count
    assert brief.floors[0].floor_label == "ground"  # normalized
    # And they hash differently because the floor_label string changed.
    assert hash(brief.floors[0]) != hash(ground)


# ---------------------------------------------------------------------------
# C11a integration sentinel — test 45
# ---------------------------------------------------------------------------


def test_c11a_is_multi_floor_returns_true_for_this_type():
    """C11a's `_is_multi_floor()` helper duck-types for `is_multi_floor`
    attribute. Confirming this type satisfies that duck-type contract.
    """
    brief = MultiFloorDwellingBrief(
        floors=(_ground(), _first()),
        master_bedroom_floor_label="ground",
    )
    assert getattr(brief, "is_multi_floor", False) is True
