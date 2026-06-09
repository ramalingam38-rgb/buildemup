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
    assert len(sl["rooms"]) == 9
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
    """Public rooms (living/kitchen/pooja) should sit at the front (low y);
    bedrooms at the back (high y)."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    publics = [r for r in sl["rooms"] if r["category"] in ("living", "kitchen", "pooja")]
    bedrooms = [r for r in sl["rooms"] if r["category"] == "bedroom"]
    max_public_y = max(r["y_m"] + r["depth_m"] for r in publics)
    min_bedroom_y = min(r["y_m"] for r in bedrooms)
    assert min_bedroom_y >= max_public_y - 0.01, "bedrooms should be behind public rooms"


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


def test_high_fill():
    """The arrangement should fill most of the buildable area (no big gaps)."""
    sl = build_smart_layout(rooms=_rooms_3br(), envelope_w=12.192, envelope_d=18.288)
    area = sum(r["width_m"] * r["depth_m"] for r in sl["rooms"])
    env = sl["envelope"]["width_m"] * sl["envelope"]["depth_m"]
    assert area / env >= 0.75, f"fill only {area / env:.0%}"


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
