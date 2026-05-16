"""
BuildemUp — Component 15 — Sub-2 dimension 1 check tests
============================================================

Per C15 SPEC v0.2 LOCKED § 1.4 Dimension 1:

- P1.1 Corridor fraction (RUNNABLE)
- P1.2 Dead-corner detection (DEFERRED)
- P1.3 Aspect-ratio sanity (RUNNABLE)
- P1.4 FAR utilization (DEFERRED)

Each runnable check tested across:
  - happy PASS path (no offenders)
  - WARN path (borderline measurement)
  - FAIL path (clear offender)
  - missing-dependency deferral path

Each deferred check tested for:
  - always returns DeferredCheck with non-empty blocking_backlog_item
"""
from __future__ import annotations

import pytest

from buildemup.components.c15 import (
    CheckEpistemicKind,
    CheckStatus,
    DeferredCheck,
    ProblemCheck,
)
from buildemup.components.c15.dimensions.dim01_no_wasted_space import (
    CIRCULATION_CATEGORIES,
    CheckP11CorridorFraction,
    CheckP12DeadCorner,
    CheckP13AspectRatio,
    CheckP14FarUtilization,
    P11_CORRIDOR_PASS_CEILING,
    P11_CORRIDOR_WARN_CEILING,
    P13_ASPECT_PASS_CEILING,
    P13_ASPECT_WARN_CEILING,
    REGISTERED_CHECKS,
)

from ._fixtures import (
    FakePlacedCandidate,
    FakePlacedRoom,
    build_context,
    build_metadata,
)


# =============================================================================
# REGISTERED_CHECKS tuple
# =============================================================================

def test_dim01_registered_checks_count_is_four():
    assert len(REGISTERED_CHECKS) == 4


def test_dim01_registered_checks_ids_lex_asc():
    ids = [c.check_id for c in REGISTERED_CHECKS]
    assert ids == sorted(ids)
    assert ids == ["P1.1", "P1.2", "P1.3", "P1.4"]


def test_dim01_all_checks_are_dimension_1():
    for c in REGISTERED_CHECKS:
        assert c.dimension_id == 1


def test_dim01_all_checks_are_architectural_heuristic():
    # Per Rule 11 finding: dim 1 has no NBC regulatory backing for
    # its measurement formulas. All four are heuristics.
    for c in REGISTERED_CHECKS:
        assert c.epistemic_kind == CheckEpistemicKind.ARCHITECTURAL_HEURISTIC


# =============================================================================
# CIRCULATION_CATEGORIES — sync with C14 convention
# =============================================================================

def test_circulation_categories_match_c14_convention():
    """C14's CIRCULATION_CATEGORY_KEYWORDS at S47 = {corridor, foyer,
    staircase}. C15's CIRCULATION_CATEGORIES must agree — if they
    diverge, foyer rooms might be counted in dim-1 corridor fraction
    but excluded from C14 graph treatment (or vice versa), breaking
    cross-component consistency."""
    expected = frozenset({"corridor", "foyer", "staircase"})
    assert CIRCULATION_CATEGORIES == expected


# =============================================================================
# P1.1 — Corridor fraction
# =============================================================================

def test_p11_pass_when_corridor_fraction_low():
    # Mostly habitable rooms, tiny corridor.
    rooms = (
        FakePlacedRoom(room_id="r_bed1", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),    # 16 m²
        FakePlacedRoom(room_id="r_bed2", category="bedroom", x_m=4, y_m=0, width_m=4, depth_m=4),    # 16 m²
        FakePlacedRoom(room_id="r_living", category="living", x_m=0, y_m=4, width_m=5, depth_m=4),   # 20 m²
        FakePlacedRoom(room_id="r_kitchen", category="kitchen", x_m=5, y_m=4, width_m=3, depth_m=4), # 12 m²
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=8, y_m=0, width_m=1, depth_m=4),    # 4 m²
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.PASS
    # 4 / 68 ≈ 5.9% — well below 15%.
    assert result.measurement is not None
    assert result.measurement["fraction"] < P11_CORRIDOR_PASS_CEILING


def test_p11_warn_when_corridor_fraction_borderline():
    # Big corridor: 18% of total.
    # Total target = 50 m²; corridor = 9 m².
    rooms = (
        FakePlacedRoom(room_id="r_bed1", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),  # 16
        FakePlacedRoom(room_id="r_kit", category="kitchen", x_m=0, y_m=4, width_m=5, depth_m=5),   # 25
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=5, y_m=0, width_m=1, depth_m=9),  # 9 m²
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_bed1",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.WARN
    assert P11_CORRIDOR_PASS_CEILING < result.measurement["fraction"] <= P11_CORRIDOR_WARN_CEILING


def test_p11_fail_when_corridor_fraction_too_high():
    # 30% corridor → FAIL.
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=5),    # 20
        FakePlacedRoom(room_id="r_kit", category="kitchen", x_m=4, y_m=0, width_m=3, depth_m=5),    # 15
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=7, y_m=0, width_m=3, depth_m=5),   # 15 m²
        # Total = 50 m²; corridor = 15/50 = 30%.
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.FAIL
    assert result.measurement["fraction"] > P11_CORRIDOR_WARN_CEILING
    # Affected_room_ids must include the corridor room.
    assert "r_cor" in result.affected_room_ids


def test_p11_includes_foyer_in_corridor_fraction():
    """Foyer is in CIRCULATION_CATEGORIES — its area should count
    toward the corridor fraction."""
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),   # 16
        FakePlacedRoom(room_id="r_living", category="living", x_m=4, y_m=0, width_m=5, depth_m=5),  # 25
        FakePlacedRoom(room_id="r_foy", category="foyer", x_m=0, y_m=4, width_m=4, depth_m=5),     # 20
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    # 20 / 61 ≈ 32.8% — FAIL (foyer included).
    assert result.status == CheckStatus.FAIL


def test_p11_pass_when_no_circulation_rooms_present():
    # A truly corridor-free layout (e.g., no-corridor topology on
    # narrow plot). corridor_area = 0, fraction = 0, status = PASS.
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_kit", category="kitchen", x_m=4, y_m=0, width_m=4, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.PASS
    assert result.measurement["fraction"] == 0.0
    assert result.affected_room_ids == ()


def test_p11_defers_when_room_categories_dependency_absent():
    # Metadata constructor enforces full room_categories coverage,
    # so we can't construct incomplete metadata. Instead build the
    # CheckContext directly with available_dependencies that
    # excludes DEP_ROOM_CATEGORIES — simulating an orchestrator that
    # detected stale categories upstream and dropped the dep.
    from buildemup.components.c15 import (
        CheckContext,
        DEP_C12_PLACEMENT,
        DEP_C12_PLACEMENT_GEOMETRY,
        DEP_MAIN_ENTRY,
    )
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_extra", category="bedroom", x_m=4, y_m=0, width_m=4, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed", "r_extra"),
        room_categories={"r_bed": "bedroom", "r_extra": "bedroom"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    # Manually construct context WITHOUT DEP_ROOM_CATEGORIES.
    ctx = CheckContext(
        placed_candidate=placed,
        circulation_report=None,  # type: ignore[arg-type]  # not consumed by P1.1
        metadata=metadata,
        available_dependencies=frozenset({DEP_C12_PLACEMENT, DEP_C12_PLACEMENT_GEOMETRY, DEP_MAIN_ENTRY}),
    )
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, DeferredCheck)
    assert result.check_id == "P1.1"
    assert "room_categories" in result.na_reason


def test_p11_measurement_is_serializable_dict():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=4, y_m=0, width_m=1, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed", "r_cor"),
        room_categories={"r_bed": "bedroom", "r_cor": "corridor"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP11CorridorFraction().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert "corridor_area_m2" in result.measurement
    assert "total_area_m2" in result.measurement
    assert "fraction" in result.measurement


# =============================================================================
# P1.2 — Dead-corner detection (always deferred at v1)
# =============================================================================

def test_p12_always_emits_deferred_at_v1():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed",),
        room_categories={"r_bed": "bedroom"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP12DeadCorner().evaluate(ctx)
    assert isinstance(result, DeferredCheck)
    assert result.check_id == "P1.2"
    assert result.blocking_backlog_item == "B-C15-ENVELOPE-POLYGON-SUBTRACTION"
    assert "polygon subtraction" in result.na_reason.lower()


# =============================================================================
# P1.3 — Aspect-ratio sanity
# =============================================================================

def test_p13_pass_when_all_habitable_rooms_under_25():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),   # 1:1
        FakePlacedRoom(room_id="r_living", category="living", x_m=4, y_m=0, width_m=6, depth_m=4), # 1.5:1
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.PASS
    assert result.affected_room_ids == ()


def test_p13_warn_when_a_room_aspect_between_25_and_30():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=8, depth_m=3),   # 8/3 ≈ 2.67
        FakePlacedRoom(room_id="r_living", category="living", x_m=0, y_m=3, width_m=5, depth_m=5), # 1:1
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.WARN
    assert "r_bed" in result.affected_room_ids


def test_p13_fail_when_a_room_aspect_over_30():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=10, depth_m=3),  # 10/3 ≈ 3.33
        FakePlacedRoom(room_id="r_living", category="living", x_m=0, y_m=3, width_m=5, depth_m=5),
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.FAIL
    assert "r_bed" in result.affected_room_ids


def test_p13_ignores_non_habitable_rooms_for_aspect_ratio():
    """A long thin bathroom or corridor should NOT trigger P1.3."""
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_bath", category="bathroom", x_m=4, y_m=0, width_m=10, depth_m=2),  # 5:1
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=0, y_m=4, width_m=15, depth_m=1),   # 15:1
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    # Only r_bed is habitable; it's 1:1 → PASS.
    assert result.status == CheckStatus.PASS


def test_p13_defers_when_no_habitable_rooms_present():
    """A purely-service layout shouldn't fail aspect-ratio sanity —
    aspect ratio is not meaningful for bath-only/corridor-only
    configurations."""
    rooms = (
        FakePlacedRoom(room_id="r_bath", category="bathroom", x_m=0, y_m=0, width_m=2, depth_m=2),
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=2, y_m=0, width_m=1, depth_m=2),
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_cor",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, DeferredCheck)
    assert "habitable" in result.na_reason.lower()


def test_p13_affected_rooms_only_offenders():
    """P1.3 affected_room_ids should list only the rooms whose own
    ratio exceeds the relevant threshold, not the room with the max."""
    rooms = (
        FakePlacedRoom(room_id="r_bed1", category="bedroom", x_m=0, y_m=0, width_m=10, depth_m=3),  # 3.33:1 (FAIL)
        FakePlacedRoom(room_id="r_bed2", category="bedroom", x_m=0, y_m=3, width_m=11, depth_m=3),  # 3.67:1 (FAIL)
        FakePlacedRoom(room_id="r_living", category="living", x_m=0, y_m=6, width_m=5, depth_m=4),  # 1.25:1 (OK)
    )
    metadata = build_metadata(
        placed_room_ids=tuple(r.room_id for r in rooms),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_living",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP13AspectRatio().evaluate(ctx)
    assert isinstance(result, ProblemCheck)
    assert result.status == CheckStatus.FAIL
    assert set(result.affected_room_ids) == {"r_bed1", "r_bed2"}
    assert "r_living" not in result.affected_room_ids


# =============================================================================
# P1.4 — FAR utilization (always deferred at v1)
# =============================================================================

def test_p14_always_emits_deferred_at_v1():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed",),
        room_categories={"r_bed": "bedroom"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    result = CheckP14FarUtilization().evaluate(ctx)
    assert isinstance(result, DeferredCheck)
    assert result.check_id == "P1.4"
    assert result.blocking_backlog_item == "B-C15-FAR-CEILING-METADATA"
    assert "FAR" in result.na_reason


# =============================================================================
# Replay determinism (Inv P2) — same input → same output
# =============================================================================

def test_p11_replay_determinism():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_cor", category="corridor", x_m=4, y_m=0, width_m=1, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed", "r_cor"),
        room_categories={"r_bed": "bedroom", "r_cor": "corridor"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    r1 = CheckP11CorridorFraction().evaluate(ctx)
    r2 = CheckP11CorridorFraction().evaluate(ctx)
    assert r1 == r2  # frozen dataclass __eq__


def test_p13_replay_determinism():
    rooms = (
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=0, width_m=8, depth_m=3),
    )
    metadata = build_metadata(
        placed_room_ids=("r_bed",),
        room_categories={"r_bed": "bedroom"},
        main_entry_room_id="r_bed",
    )
    placed = FakePlacedCandidate(placed_rooms=rooms)
    ctx = build_context(placed_candidate=placed, metadata=metadata)
    r1 = CheckP13AspectRatio().evaluate(ctx)
    r2 = CheckP13AspectRatio().evaluate(ctx)
    assert r1 == r2
