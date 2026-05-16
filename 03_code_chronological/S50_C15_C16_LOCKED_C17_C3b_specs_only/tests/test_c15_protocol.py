"""
BuildemUp — Component 15 — Sub-2 protocol tests
==================================================

Per C15 SPEC v0.2 LOCKED — protocol layer tests:

- CheckContext defensive checks (metadata type, available_dependencies type)
- Check protocol structural conformance (runtime_checkable)
- Canonical dependency-name constants present and string-typed
- probe_dependencies returns conservative results
- v1-deferred dependency names are never reported by probe
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from buildemup.components.c15 import (
    Check,
    CheckContext,
    CheckEpistemicKind,
    CulturalProfile,
    DEP_C12_PLACEMENT,
    DEP_C12_PLACEMENT_GEOMETRY,
    DEP_C14_FLAGS,
    DEP_C14_GRAPH,
    DEP_ENVELOPE_POLYGON_SUBTRACTION,
    DEP_FLOOR_METADATA,
    DEP_FURNITURE_FIT,
    DEP_MAIN_ENTRY,
    DEP_PLOT_FAR_CEILING,
    DEP_ROOM_CATEGORIES,
    DEP_WINDOW_DATA,
    FloorInfo,
    ProblemAnalysisMetadata,
    probe_dependencies,
)

from ._fixtures import (
    FakeCirculationReport,
    FakePlacedCandidate,
    FakePlacedRoom,
    build_context,
    build_metadata,
)


# =============================================================================
# CheckContext
# =============================================================================

def test_check_context_happy_path():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    ctx = build_context(placed_candidate=placed)
    assert ctx.placed_candidate is placed
    assert isinstance(ctx.metadata, ProblemAnalysisMetadata)
    assert isinstance(ctx.available_dependencies, frozenset)


def test_check_context_is_frozen():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    ctx = build_context(placed_candidate=placed)
    with pytest.raises(FrozenInstanceError):
        ctx.placed_candidate = None  # type: ignore[misc]


def test_check_context_rejects_non_metadata():
    placed = FakePlacedCandidate(placed_rooms=())
    with pytest.raises(TypeError):
        CheckContext(
            placed_candidate=placed,
            circulation_report=FakeCirculationReport(),
            metadata="not metadata",  # type: ignore[arg-type]
            available_dependencies=frozenset(),
        )


def test_check_context_rejects_non_frozenset_dependencies():
    placed = FakePlacedCandidate(placed_rooms=())
    metadata = ProblemAnalysisMetadata(
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    with pytest.raises(TypeError):
        CheckContext(
            placed_candidate=placed,
            circulation_report=FakeCirculationReport(),
            metadata=metadata,
            available_dependencies={"a", "b"},  # type: ignore[arg-type]  # set, not frozenset
        )


# =============================================================================
# Canonical dependency constants
# =============================================================================

def test_dependency_constants_present_and_string():
    for dep in [
        DEP_C12_PLACEMENT,
        DEP_C12_PLACEMENT_GEOMETRY,
        DEP_C14_GRAPH,
        DEP_C14_FLAGS,
        DEP_ROOM_CATEGORIES,
        DEP_FLOOR_METADATA,
        DEP_MAIN_ENTRY,
        DEP_WINDOW_DATA,
        DEP_FURNITURE_FIT,
        DEP_PLOT_FAR_CEILING,
        DEP_ENVELOPE_POLYGON_SUBTRACTION,
    ]:
        assert isinstance(dep, str)
        assert len(dep) > 0


def test_dependency_constants_are_unique():
    deps = [
        DEP_C12_PLACEMENT,
        DEP_C12_PLACEMENT_GEOMETRY,
        DEP_C14_GRAPH,
        DEP_C14_FLAGS,
        DEP_ROOM_CATEGORIES,
        DEP_FLOOR_METADATA,
        DEP_MAIN_ENTRY,
        DEP_WINDOW_DATA,
        DEP_FURNITURE_FIT,
        DEP_PLOT_FAR_CEILING,
        DEP_ENVELOPE_POLYGON_SUBTRACTION,
    ]
    assert len(set(deps)) == len(deps)


# =============================================================================
# probe_dependencies
# =============================================================================

def test_probe_reports_c12_placement_when_rooms_present():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    metadata = build_metadata(
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    available = probe_dependencies(placed, FakeCirculationReport(), metadata)
    assert DEP_C12_PLACEMENT in available
    assert DEP_C12_PLACEMENT_GEOMETRY in available


def test_probe_omits_c12_when_no_rooms():
    placed = FakePlacedCandidate(placed_rooms=())
    metadata = ProblemAnalysisMetadata(
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    available = probe_dependencies(placed, FakeCirculationReport(), metadata)
    assert DEP_C12_PLACEMENT not in available
    assert DEP_C12_PLACEMENT_GEOMETRY not in available


def test_probe_reports_room_categories_only_when_all_covered():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
        FakePlacedRoom(room_id="r2", category="kitchen", x_m=3, y_m=0, width_m=3, depth_m=4),
    ))
    # Metadata covers both rooms.
    metadata_full = ProblemAnalysisMetadata(
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        placed_room_ids=("r1", "r2"),
        room_categories={"r1": "bedroom", "r2": "kitchen"},
        main_entry_room_id="r1",
    )
    available_full = probe_dependencies(placed, FakeCirculationReport(), metadata_full)
    assert DEP_ROOM_CATEGORIES in available_full


def test_probe_reports_main_entry_when_resolvable():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    metadata = build_metadata(
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    available = probe_dependencies(placed, FakeCirculationReport(), metadata)
    assert DEP_MAIN_ENTRY in available


def test_probe_reports_floor_metadata_when_present():
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    floor = FloorInfo(floor_id="GF", is_ground=True, has_entry=True, room_ids=("r1",))
    metadata = build_metadata(
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
        floor_metadata=(floor,),
    )
    available = probe_dependencies(placed, FakeCirculationReport(), metadata)
    assert DEP_FLOOR_METADATA in available


def test_probe_never_reports_v1_deferred_dependencies():
    """Critical: DEP_WINDOW_DATA / DEP_FURNITURE_FIT / DEP_PLOT_FAR_CEILING /
    DEP_ENVELOPE_POLYGON_SUBTRACTION must NEVER be reported as
    available by the probe — these are pipeline gaps at v1 and
    checks depending on them must always defer."""
    placed = FakePlacedCandidate(placed_rooms=(
        FakePlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=3, depth_m=4),
    ))
    metadata = build_metadata(
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    available = probe_dependencies(placed, FakeCirculationReport(), metadata)
    for forbidden in [
        DEP_WINDOW_DATA,
        DEP_FURNITURE_FIT,
        DEP_PLOT_FAR_CEILING,
        DEP_ENVELOPE_POLYGON_SUBTRACTION,
    ]:
        assert forbidden not in available, (
            f"probe_dependencies must NEVER report v1-deferred "
            f"dependency {forbidden!r} as available; that would let "
            f"checks evaluate against absent data."
        )


# =============================================================================
# Check protocol structural conformance
# =============================================================================

def test_check_protocol_is_runtime_checkable():
    # The @runtime_checkable decorator allows isinstance against a Protocol.
    # A class implementing the required attributes + evaluate method should
    # be recognized as a Check.

    @dataclass(frozen=True)
    class TestCheckImpl:
        check_id: str = "P1.99"
        dimension_id: int = 1
        epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
        data_dependencies: tuple[str, ...] = ()
        cultural_scope: frozenset[CulturalProfile] | None = None

        def evaluate(self, context: CheckContext):
            return None

    impl = TestCheckImpl()
    # Note: runtime_checkable for Protocol only checks for attribute
    # presence at runtime, not signatures or types. This is enough
    # for our duck-typing usage.
    assert isinstance(impl, Check)


def test_check_protocol_rejects_missing_attributes():
    # An object without `evaluate` should NOT pass the Protocol check.
    class NotACheck:
        check_id = "P1.99"
        dimension_id = 1

    obj = NotACheck()
    assert not isinstance(obj, Check)
