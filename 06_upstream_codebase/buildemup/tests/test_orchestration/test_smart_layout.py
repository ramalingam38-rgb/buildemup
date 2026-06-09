"""Tests for the S60 smart-layout engine (adjacency-aware arrangement)."""
from __future__ import annotations

import itertools

from buildemup.orchestration.smart_layout import (
    build_smart_layout,
    build_smart_layout_from_preview,
)


def _rooms_3br():
    return [
        {"category": "living", "width_m": 4.3, "depth_m": 4.3, "room_id": "LIVING_1"},
        {"category": "kitchen", "width_m": 3.05, "depth_m": 3.05, "room_id": "KITCHEN_1"},
        {"category": "pooja", "width_m": 1.8, "depth_m": 1.8, "room_id": "POOJA_1"},
        {"category": "bedroom", "width_m": 3.85, "depth_m": 3.85, "room_id": "BEDROOM_1"},
        {"category": "bedroom", "width_m": 3.2, "depth_m": 3.2, "room_id": "BEDROOM_2"},
        {"category": "bedroom", "width_m": 3.2, "depth_m": 3.2, "room_id": "BEDROOM_3"},
        {"category": "bathroom", "width_m": 2.05, "depth_m": 2.05, "room_id": "BATHROOM_1"},
        {"category": "bathroom", "width_m": 1.8, "depth_m": 1.8, "room_id": "BATHROOM_2"},
        {"category": "bathroom", "width_m": 1.8, "depth_m": 1.8, "room_id": "BATHROOM_3"},
    ]


def _overlaps(rooms):
    n = 0
    for a, b in itertools.combinations(rooms, 2):
        if (a["x_m"] < b["x_m"] + b["width_m"] - 0.01
                and b["x_m"] < a["x_m"] + a["width_m"] - 0.01
                and a["y_m"] < b["y_m"] + b["depth_m"] - 0.01
                and b["y_m"] < a["y_m"] + a["depth_m"] - 0.01):
            n += 1
    return n


def test_build_smart_layout_basic_shape():
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288, facing="E")
    assert sl is not None
    assert sl["envelope"] == {"width_m": 12.192, "depth_m": 18.288}
    assert sl["facing"] == "E"
    # 9 program rooms + 1 injected staircase = 10
    assert len(sl["rooms"]) == 10
    assert sl["entrance"]["y_m"] == 0.0


def test_no_overlaps():
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    assert _overlaps(sl["rooms"]) == 0


def test_rooms_stay_within_envelope():
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    for r in sl["rooms"]:
        assert r["x_m"] >= -0.01
        assert r["y_m"] >= -0.01
        assert r["x_m"] + r["width_m"] <= 12.192 + 0.01
        assert r["y_m"] + r["depth_m"] <= 18.288 + 0.01


def test_public_rooms_at_front_bedrooms_at_back():
    """Living/kitchen should sit at the front (low y); bedrooms at the
    back (high y). (v2: pooja moves to a back corner per convention.)"""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    publics = [r for r in sl["rooms"] if r["category"] in ("living", "kitchen")]
    bedrooms = [r for r in sl["rooms"] if r["category"] == "bedroom"]
    max_public_y = max(r["y_m"] + r["depth_m"] for r in publics)
    min_bedroom_y = min(r["y_m"] for r in bedrooms)
    assert min_bedroom_y >= max_public_y - 0.01, "bedrooms should be behind public rooms"


def test_staircase_is_present():
    """v2: a staircase must always be placed (so upper floors are
    reachable) even though the room program omits it."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    stairs = [r for r in sl["rooms"] if r["category"] == "staircase"]
    assert len(stairs) == 1, "exactly one staircase expected"
    assert sl["has_staircase"] is True


def test_entrance_opens_into_living_not_a_bathroom():
    """The entrance is on the front edge; the room spanning the front
    must be the living room, never a bathroom."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    ex = sl["entrance"]["x_m"]
    front = [r for r in sl["rooms"] if r["y_m"] < 0.5
             and r["x_m"] - 0.01 <= ex <= r["x_m"] + r["width_m"] + 0.01]
    assert front, "a room should sit at the entrance"
    assert all(r["category"] != "bathroom" for r in front), "no bathroom at the entrance"
    assert any(r["category"] == "living" for r in front), "entrance should open into living"


def test_kitchen_and_dining_grouped():
    """Kitchen and dining should be in the same depth band (grouped)."""
    rooms = _rooms_3br() + [{"category": "dining", "width_m": 3.0, "depth_m": 3.0, "room_id": "DINING_1"}]
    sl = build_smart_layout(rooms=rooms, envelope_w=12.192, envelope_d=18.288)
    kitchen = next(r for r in sl["rooms"] if r["category"] == "kitchen")
    dining = next(r for r in sl["rooms"] if r["category"] == "dining")
    assert abs(kitchen["y_m"] - dining["y_m"]) < 0.5, "kitchen & dining should share a band"


def test_each_bedroom_paired_with_a_bathroom_adjacent():
    """Every bedroom should have a bathroom sharing its column (same x range),
    directly adjacent in y — the attached-bath adjacency."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    bedrooms = [r for r in sl["rooms"] if r["category"] == "bedroom"]
    baths = [r for r in sl["rooms"] if r["category"] == "bathroom"]
    for bed in bedrooms:
        # find a bathroom in the same column (overlapping x) touching in y
        paired = [
            t for t in baths
            if abs(t["x_m"] - bed["x_m"]) < 0.05
            and abs(t["width_m"] - bed["width_m"]) < 0.05
            and abs(t["y_m"] - (bed["y_m"] + bed["depth_m"])) < 0.05
        ]
        assert paired, f"bedroom at x={bed['x_m']} has no adjacent attached bath"


def test_corridor_present_when_both_zones_exist():
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    assert len(sl["corridor"]) == 1
    assert sl["corridor"][0]["width_m"] > 0


def test_doors_present():
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    assert len(sl["doors"]) >= len([r for r in sl["rooms"] if r["category"] == "bedroom"])


def test_good_fill_with_circulation():
    """Rooms + corridor should use most of the plot; rooms alone are
    lower because circulation (corridor) is real space, as in a house."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    env = sl["envelope"]["width_m"] * sl["envelope"]["depth_m"]
    room_area = sum(r["width_m"] * r["depth_m"] for r in sl["rooms"])
    corr_area = sum(c["width_m"] * c["depth_m"] for c in sl["corridor"])
    assert (room_area + corr_area) / env >= 0.80, (
        f"rooms+corridor use only {(room_area + corr_area) / env:.0%}"
    )


def test_empty_rooms_returns_none():
    assert build_smart_layout(rooms=[], envelope_w=10, envelope_d=10) is None


def test_bedrooms_only_floor():
    """An upper floor with only bedrooms + baths should still arrange."""
    rooms = [
        {"category": "bedroom", "width_m": 3.5, "depth_m": 3.5, "room_id": "B1"},
        {"category": "bedroom", "width_m": 3.2, "depth_m": 3.2, "room_id": "B2"},
        {"category": "bathroom", "width_m": 1.8, "depth_m": 1.8, "room_id": "T1"},
    ]
    sl = build_smart_layout(rooms=rooms, envelope_w=12.192, envelope_d=18.288)
    assert sl is not None
    assert _overlaps(sl["rooms"]) == 0


def test_from_preview_wrapper():
    preview = {
        "envelope": {"width_m": 12.0, "depth_m": 18.0},
        "rooms": _rooms_3br(),
    }
    sl = build_smart_layout_from_preview(preview, facing="N")
    assert sl is not None
    assert sl["facing"] == "N"
    assert _overlaps(sl["rooms"]) == 0


def test_from_preview_none_safe():
    assert build_smart_layout_from_preview(None) is None
    assert build_smart_layout_from_preview({"envelope": {}, "rooms": []}) is None
