"""
BuildemUp — Component 15 — Pattern Detector Tests (v1 LOCK)
================================================================

Per LOCK-mandatory B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK.

Verifies:
- compact_incremental detects on small-area multi-room layouts
- compact_incremental does NOT detect on standard-size layouts
- courtyard_centered detects when a courtyard room has ≥4 habitable
  neighbors
- courtyard_centered does NOT detect when no courtyard category exists
- split_level_circulation always returns False at v1 (data-blocked stub)
- ritual_procession always returns False at v1 (data-blocked stub)
- multigenerational_segregation always returns False at v1
  (data-blocked stub)
- UnconventionalPatternHint output is well-formed
- caveat populated when patterns fire; empty when none

Rule 11 self-analysis: detection logic depends on duck-typed room
shape, which is brittle. Test fixtures replicate the exact shape from
test_c15/_fixtures.py so the test catches drift.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c15.pattern_detector import (
    COMPACT_INCREMENTAL_AREA_THRESHOLD_M2,
    COMPACT_INCREMENTAL_ROOM_COUNT_MIN,
    detect_unconventional_patterns,
    _detect_compact_incremental,
    _detect_courtyard_centered,
    _detect_split_level_circulation,
    _detect_ritual_procession,
    _detect_multigenerational_segregation,
)
from buildemup.components.c15.schema import (
    UNCONVENTIONAL_PATTERN_NAMES, UnconventionalPatternHint,
)


# =============================================================================
# Test doubles
# =============================================================================

@dataclass(frozen=True)
class FakeRoom:
    room_id: str
    category: str
    width_m: float = 3.0
    depth_m: float = 3.0


@dataclass(frozen=True)
class FakeCandidate:
    placed_rooms: tuple


@dataclass(frozen=True)
class FakeC14Report:
    adjacency_graph: dict[str, frozenset[str]]


def _empty_c14() -> FakeC14Report:
    return FakeC14Report(adjacency_graph={})


# =============================================================================
# compact_incremental — IMPLEMENTED
# =============================================================================

class TestCompactIncremental:
    def test_detects_when_4_rooms_under_55_74_m2(self):
        # 4 rooms × 3×3=9 m² each = 36 m². Under 55.74 m² threshold.
        rooms = tuple(
            FakeRoom(f"r{i}", "bedroom") for i in range(4)
        )
        cand = FakeCandidate(placed_rooms=rooms)
        assert _detect_compact_incremental(cand, _empty_c14()) is True

    def test_does_not_detect_with_3_rooms(self):
        # Room count under min (≥4 required).
        rooms = tuple(FakeRoom(f"r{i}", "bedroom") for i in range(3))
        cand = FakeCandidate(placed_rooms=rooms)
        assert _detect_compact_incremental(cand, _empty_c14()) is False

    def test_does_not_detect_when_above_area_threshold(self):
        # 4 rooms × 16 m² each = 64 m², above 55.74 threshold.
        rooms = tuple(
            FakeRoom(f"r{i}", "bedroom", width_m=4.0, depth_m=4.0)
            for i in range(4)
        )
        cand = FakeCandidate(placed_rooms=rooms)
        assert _detect_compact_incremental(cand, _empty_c14()) is False

    def test_threshold_constants_match_spec(self):
        # Per UNCONVENTIONAL_PATTERN_NAMES docstring: 600 sqft ~= 55.74 m²
        # Locked for B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK audit.
        assert COMPACT_INCREMENTAL_AREA_THRESHOLD_M2 == 55.74
        assert COMPACT_INCREMENTAL_ROOM_COUNT_MIN == 4


# =============================================================================
# courtyard_centered — IMPLEMENTED
# =============================================================================

class TestCourtyardCentered:
    def test_detects_courtyard_with_4_habitable_neighbors(self):
        rooms = (
            FakeRoom("cy1", "courtyard"),
            FakeRoom("br1", "bedroom"),
            FakeRoom("br2", "bedroom"),
            FakeRoom("liv", "living"),
            FakeRoom("din", "dining"),
            FakeRoom("kit", "kitchen"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = FakeC14Report(adjacency_graph={
            "cy1": frozenset({"br1", "br2", "liv", "din", "kit"}),
            "br1": frozenset({"cy1"}),
            "br2": frozenset({"cy1"}),
            "liv": frozenset({"cy1", "din"}),
            "din": frozenset({"cy1", "liv", "kit"}),
            "kit": frozenset({"cy1", "din"}),
        })
        assert _detect_courtyard_centered(cand, c14) is True

    def test_does_not_detect_without_courtyard_category(self):
        # No room labeled courtyard.
        rooms = (
            FakeRoom("hall", "hallway"),
            FakeRoom("br1", "bedroom"),
            FakeRoom("br2", "bedroom"),
            FakeRoom("liv", "living"),
            FakeRoom("din", "dining"),
            FakeRoom("kit", "kitchen"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = FakeC14Report(adjacency_graph={
            "hall": frozenset({"br1", "br2", "liv", "din", "kit"}),
            "br1": frozenset({"hall"}),
        })
        assert _detect_courtyard_centered(cand, c14) is False

    def test_does_not_detect_with_only_3_habitable_neighbors(self):
        rooms = (
            FakeRoom("cy1", "courtyard"),
            FakeRoom("br1", "bedroom"),
            FakeRoom("liv", "living"),
            FakeRoom("din", "dining"),
            FakeRoom("util", "utility"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = FakeC14Report(adjacency_graph={
            "cy1": frozenset({"br1", "liv", "din", "util"}),
        })
        # Only 3 habitable (br1, liv, din); util is not habitable
        # per detector's HABITABLE set.
        assert _detect_courtyard_centered(cand, c14) is False

    def test_does_not_detect_when_no_adjacency_data(self):
        rooms = (
            FakeRoom("cy1", "courtyard"),
            FakeRoom("br1", "bedroom"),
            FakeRoom("br2", "bedroom"),
            FakeRoom("liv", "living"),
            FakeRoom("din", "dining"),
            FakeRoom("kit", "kitchen"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = _empty_c14()
        assert _detect_courtyard_centered(cand, c14) is False


# =============================================================================
# Data-blocked stubs — ALWAYS return False
# =============================================================================

class TestDataBlockedStubs:
    """Per B-C15-PATTERN-{...}-DATA backlog items, these 3 patterns
    require upstream extensions not in v1. Honest behavior: always
    return False; never emit detected=True for these names at v1."""

    def test_split_level_circulation_always_false(self):
        rooms = (FakeRoom(f"r{i}", "bedroom") for i in range(20))
        cand = FakeCandidate(placed_rooms=tuple(rooms))
        c14 = _empty_c14()
        assert _detect_split_level_circulation(cand, c14) is False

    def test_ritual_procession_always_false(self):
        rooms = (
            FakeRoom("entry", "entry"),
            FakeRoom("liv", "living"),
            FakeRoom("pooja", "pooja_room"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = FakeC14Report(adjacency_graph={
            "entry": frozenset({"liv"}),
            "liv": frozenset({"entry", "pooja"}),
        })
        assert _detect_ritual_procession(cand, c14) is False

    def test_multigenerational_segregation_always_false(self):
        rooms = (
            FakeRoom("m1", "master_bedroom"),
            FakeRoom("m2", "master_bedroom"),
            FakeRoom("br1", "bedroom"),
            FakeRoom("br2", "bedroom"),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = _empty_c14()
        assert _detect_multigenerational_segregation(cand, c14) is False


# =============================================================================
# Public detect_unconventional_patterns integration
# =============================================================================

class TestPublicDetector:
    def test_no_pattern_returns_well_formed_empty_hint(self):
        rooms = (
            FakeRoom("liv", "living"),
            FakeRoom("kit", "kitchen", width_m=4.0, depth_m=4.0),
        )
        cand = FakeCandidate(placed_rooms=rooms)
        hint = detect_unconventional_patterns(cand, _empty_c14())
        assert isinstance(hint, UnconventionalPatternHint)
        assert hint.detected is False
        assert hint.suspected_patterns == ()
        assert hint.confidence_caveat == ""

    def test_compact_incremental_detection_caveat_populated(self):
        rooms = tuple(FakeRoom(f"r{i}", "bedroom") for i in range(4))
        cand = FakeCandidate(placed_rooms=rooms)
        hint = detect_unconventional_patterns(cand, _empty_c14())
        assert hint.detected is True
        assert "compact_incremental" in hint.suspected_patterns
        assert hint.confidence_caveat != ""
        assert "compact_incremental" in hint.confidence_caveat

    def test_suspected_patterns_sorted_lex_asc(self):
        # Layout that triggers BOTH courtyard_centered AND
        # compact_incremental (small area + courtyard).
        rooms = (
            FakeRoom("cy", "courtyard", width_m=2.0, depth_m=2.0),
            FakeRoom("br1", "bedroom", width_m=2.5, depth_m=2.5),
            FakeRoom("br2", "bedroom", width_m=2.5, depth_m=2.5),
            FakeRoom("liv", "living", width_m=3.0, depth_m=2.5),
            FakeRoom("kit", "kitchen", width_m=2.0, depth_m=2.0),
            FakeRoom("din", "dining", width_m=2.0, depth_m=2.0),
        )
        # Total ≈ 4 + 6.25 + 6.25 + 7.5 + 4 + 4 = 32 m² < 55.74
        # Room count = 6 ≥ 4 (compact_incremental fires)
        cand = FakeCandidate(placed_rooms=rooms)
        c14 = FakeC14Report(adjacency_graph={
            "cy": frozenset({"br1", "br2", "liv", "kit", "din"}),
        })
        hint = detect_unconventional_patterns(cand, c14)
        # Both fire; suspected_patterns sorted lex-ASC.
        assert hint.detected is True
        assert hint.suspected_patterns == ("compact_incremental",
                                            "courtyard_centered")
        assert hint.suspected_patterns == tuple(
            sorted(hint.suspected_patterns)
        )

    def test_all_suspected_names_in_pattern_name_set(self):
        rooms = tuple(FakeRoom(f"r{i}", "bedroom") for i in range(4))
        cand = FakeCandidate(placed_rooms=rooms)
        hint = detect_unconventional_patterns(cand, _empty_c14())
        for name in hint.suspected_patterns:
            assert name in UNCONVENTIONAL_PATTERN_NAMES


# =============================================================================
# Replay determinism (Inv P2)
# =============================================================================

class TestReplayDeterminism:
    def test_identical_inputs_produce_identical_hints(self):
        rooms = tuple(FakeRoom(f"r{i}", "bedroom") for i in range(4))
        cand = FakeCandidate(placed_rooms=rooms)
        h1 = detect_unconventional_patterns(cand, _empty_c14())
        h2 = detect_unconventional_patterns(cand, _empty_c14())
        assert h1 == h2
        # Tuple identity (suspected_patterns) must be equal.
        assert h1.suspected_patterns == h2.suspected_patterns
        assert h1.confidence_caveat == h2.confidence_caveat
