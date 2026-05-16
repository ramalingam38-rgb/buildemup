"""
BuildemUp — Component 15 — Sub-2 test fixtures
==================================================

Test doubles for upstream C12 PlacedCandidate / C14
CirculationGraphReport — duck-typed to match what C15 checks probe
for (placed_rooms, room_id, category, width_m, depth_m, etc.) without
importing the actual C12/C14 schemas.

This keeps tests self-contained and prevents test failures from
unrelated upstream changes propagating into C15 tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from buildemup.components.c15 import (
    CulturalProfile,
    FloorInfo,
    ProblemAnalysisMetadata,
    CheckContext,
    probe_dependencies,
)


@dataclass(frozen=True)
class FakePlacedRoom:
    """Duck-typed analog of C12 PlacedRoom."""
    room_id: str
    category: str
    x_m: float
    y_m: float
    width_m: float
    depth_m: float


@dataclass(frozen=True)
class FakePlacedCandidate:
    """Duck-typed analog of C12 PlacedCandidate."""
    placed_rooms: tuple[FakePlacedRoom, ...]
    envelope_width_m: float = 10.0
    envelope_depth_m: float = 12.0


@dataclass(frozen=True)
class FakeCirculationReport:
    """Duck-typed analog of C14 CirculationGraphReport. Sub-2 dim 1
    checks don't consume this, but the CheckContext requires
    something."""
    nodes: tuple[str, ...] = ()
    structural_flags: tuple = ()
    preference_flags: tuple = ()


def build_metadata(
    *,
    cultural_profile: CulturalProfile = CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    placed_room_ids: tuple[str, ...] = ("r_bed1", "r_corridor", "r_kitchen", "r_living"),
    room_categories: dict[str, str] | None = None,
    main_entry_room_id: str = "r_living",
    floor_metadata: tuple[FloorInfo, ...] = (),
) -> ProblemAnalysisMetadata:
    if room_categories is None:
        room_categories = {
            "r_living": "living",
            "r_bed1": "bedroom",
            "r_kitchen": "kitchen",
            "r_corridor": "corridor",
        }
    # Inv P2 replay determinism: placed_room_ids must be lex-ASC. The
    # fixture sorts unconditionally so individual tests can list
    # rooms in any order without worrying about it.
    sorted_ids = tuple(sorted(placed_room_ids))
    return ProblemAnalysisMetadata(
        cultural_profile=cultural_profile,
        placed_room_ids=sorted_ids,
        room_categories=room_categories,
        main_entry_room_id=main_entry_room_id,
        floor_metadata=floor_metadata,
    )


def build_context(
    *,
    placed_candidate: FakePlacedCandidate,
    circulation_report: FakeCirculationReport | None = None,
    metadata: ProblemAnalysisMetadata | None = None,
    extra_deferred_deps: frozenset[str] = frozenset(),
) -> CheckContext:
    """Build a CheckContext with available_dependencies probed from
    the placed_candidate / circulation_report / metadata, plus an
    optional set of additional dependencies to mark as available
    (test-only escape hatch — DEP_PLOT_FAR_CEILING etc. are normally
    never available)."""
    if circulation_report is None:
        circulation_report = FakeCirculationReport()
    if metadata is None:
        metadata = build_metadata()
    available = probe_dependencies(placed_candidate, circulation_report, metadata) | extra_deferred_deps
    return CheckContext(
        placed_candidate=placed_candidate,
        circulation_report=circulation_report,
        metadata=metadata,
        available_dependencies=available,
    )
