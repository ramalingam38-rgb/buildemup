"""Tests for C12 v1.0 algorithmic layer (S44 final).

Covers:
- slicing-tree placement (RoomSpec, place_rooms_slicing_tree)
- VAV (verify_vertical_alignment)
- MFRA (absorb_multi_floor_placements)
- Orchestrator (place_and_align end-to-end, STRICT + WARN modes)
"""
from __future__ import annotations

import pytest

from buildemup.components.c12 import (
    AdjacencyConstraintViolationError,
    GeometricInfeasibilityError,
    MultiFloorPlacementInput,
    PlacedCandidate,
    PlacedRoom,
    PlacementConfig,
    RoomSpec,
    SingleFloorPlacementInput,
    VerticalAlignmentError,
    VerticalCoreReservation,
    absorb_multi_floor_placements,
    place_and_align,
    place_rooms_slicing_tree,
    verify_vertical_alignment,
)


# ─────────────────────────────────────────────────────────────────────
# RoomSpec
# ─────────────────────────────────────────────────────────────────────


def test_room_spec_basic():
    rs = RoomSpec(
        room_id="bedroom_1", category="bedroom",
        target_width_m=4.0, target_depth_m=3.5,
    )
    assert rs.area_m2 == pytest.approx(14.0)


def test_room_spec_rejects_empty_id():
    with pytest.raises(ValueError, match="room_id"):
        RoomSpec(room_id="", category="bedroom", target_width_m=1, target_depth_m=1)


def test_room_spec_rejects_non_positive_dims():
    with pytest.raises(ValueError, match="positive"):
        RoomSpec(
            room_id="r", category="bedroom",
            target_width_m=0, target_depth_m=1,
        )


# ─────────────────────────────────────────────────────────────────────
# Slicing-tree placement
# ─────────────────────────────────────────────────────────────────────


def _rs(rid: str, cat: str, w: float, d: float) -> RoomSpec:
    return RoomSpec(room_id=rid, category=cat, target_width_m=w, target_depth_m=d)


def test_slicing_tree_single_room():
    rooms = (_rs("bedroom_1", "bedroom", 4, 4),)
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=10, envelope_depth_m=10,
    )
    assert len(placed) == 1
    assert placed[0].room_id == "bedroom_1"


def test_slicing_tree_4_equal_rooms_in_grid():
    """4 same-size rooms should pack into a 2x2 grid."""
    rooms = tuple(
        _rs(f"r_{i}", "bedroom", 4, 4) for i in range(4)
    )
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=8, envelope_depth_m=8,
    )
    assert len(placed) == 4
    # All rooms placed (no duplicates, no gaps in mapping)
    assert {p.room_id for p in placed} == {f"r_{i}" for i in range(4)}


def test_slicing_tree_canonical_sort_by_id():
    """Output rooms sorted lex-ASC by room_id (PlacedCandidate invariant)."""
    rooms = (
        _rs("zebra", "bedroom", 4, 4),
        _rs("alpha", "bedroom", 4, 4),
        _rs("mango", "bedroom", 4, 4),
    )
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=12, envelope_depth_m=4,
    )
    ids = [p.room_id for p in placed]
    assert ids == sorted(ids)


def test_slicing_tree_deterministic():
    """Same input twice → byte-equal output (Inv 7)."""
    rooms = (
        _rs("bedroom_1", "bedroom", 4, 4),
        _rs("bathroom_1", "bathroom", 2, 3),
        _rs("kitchen_1", "kitchen", 4, 3),
    )
    p1 = place_rooms_slicing_tree(
        rooms, envelope_width_m=8, envelope_depth_m=7,
    )
    p2 = place_rooms_slicing_tree(
        rooms, envelope_width_m=8, envelope_depth_m=7,
    )
    assert p1 == p2


def test_slicing_tree_permutation_invariant():
    """Different input order → identical output (canonical sort, v0.2-A4 rule #1)."""
    rooms_order_1 = (
        _rs("alpha", "bedroom", 4, 4),
        _rs("beta", "bedroom", 4, 4),
        _rs("gamma", "bedroom", 4, 4),
    )
    rooms_order_2 = (rooms_order_1[2], rooms_order_1[0], rooms_order_1[1])
    p1 = place_rooms_slicing_tree(
        rooms_order_1, envelope_width_m=12, envelope_depth_m=4,
    )
    p2 = place_rooms_slicing_tree(
        rooms_order_2, envelope_width_m=12, envelope_depth_m=4,
    )
    assert p1 == p2


def test_slicing_tree_rejects_infeasible_envelope():
    """Total room area > envelope area → infeasibility."""
    rooms = (_rs("huge", "living", 10, 10),)
    with pytest.raises(GeometricInfeasibilityError, match="area"):
        place_rooms_slicing_tree(
            rooms, envelope_width_m=5, envelope_depth_m=5,
        )


def test_slicing_tree_rejects_room_larger_than_envelope():
    """Single room wider than envelope → infeasibility."""
    rooms = (_rs("wide", "living", 12, 2),)
    with pytest.raises(GeometricInfeasibilityError):
        place_rooms_slicing_tree(
            rooms, envelope_width_m=10, envelope_depth_m=10,
        )


def test_slicing_tree_handles_mixed_dimensions():
    """The case that drove the adaptive-cut-fraction fix."""
    rooms = (
        _rs("bedroom_1", "bedroom", 4, 4),
        _rs("bathroom_1", "bathroom", 2, 3),
        _rs("kitchen_1", "kitchen", 4, 3),
        _rs("living_1", "living", 6, 4),
    )
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=10, envelope_depth_m=7,
    )
    assert len(placed) == 4


def test_slicing_tree_rooms_inside_envelope():
    """Inv 1: every placed room is within envelope bounds."""
    rooms = tuple(
        _rs(f"r_{i}", "bedroom", 3, 3) for i in range(4)
    )
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=6, envelope_depth_m=6,
    )
    for p in placed:
        assert p.x_m >= 0 and p.y_m >= 0
        assert p.x_m + p.width_m <= 6 + 1e-6
        assert p.y_m + p.depth_m <= 6 + 1e-6


def test_slicing_tree_no_overlap():
    """Inv 2: no two placed rooms overlap in interior."""
    rooms = tuple(
        _rs(f"r_{i}", "bedroom", 3, 3) for i in range(4)
    )
    placed = place_rooms_slicing_tree(
        rooms, envelope_width_m=6, envelope_depth_m=6,
    )
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a = placed[i]
            b = placed[j]
            # Strict-less-than: touching edges OK, interior overlap fails.
            x_separated = a.x_m + a.width_m <= b.x_m + 1e-6 or b.x_m + b.width_m <= a.x_m + 1e-6
            y_separated = a.y_m + a.depth_m <= b.y_m + 1e-6 or b.y_m + b.depth_m <= a.y_m + 1e-6
            assert x_separated or y_separated, f"Overlap between {a.room_id} and {b.room_id}"


# ─────────────────────────────────────────────────────────────────────
# VAV
# ─────────────────────────────────────────────────────────────────────


def _pc_with_room(label: str, room: PlacedRoom) -> PlacedCandidate:
    return PlacedCandidate(
        source_refined_candidate_signature=f"rc:{label}",
        placed_rooms=(room,),
        shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10.0, envelope_depth_m=10.0,
    )


def test_vav_converged_identical_features():
    """Same room position on both floors → trivially converged."""
    stair = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    per_floor = (
        ("ground", _pc_with_room("ground", stair)),
        ("first", _pc_with_room("first", stair)),
    )
    # 'first' < 'ground' lex-ASC, so order it correctly
    per_floor_sorted = tuple(sorted(per_floor, key=lambda x: x[0]))
    report = verify_vertical_alignment(
        per_floor_placements=per_floor_sorted,
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        tolerance_m=0.02,
    )
    assert report.converged
    assert report.final_max_misalignment_m == 0.0


def test_vav_diverged_misaligned_features():
    """Staircase at different positions on each floor → not converged."""
    stair_a = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    stair_b = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=5, y_m=5, width_m=2, depth_m=2,
    )
    per_floor = (
        ("first", _pc_with_room("first", stair_b)),
        ("ground", _pc_with_room("ground", stair_a)),
    )
    report = verify_vertical_alignment(
        per_floor_placements=per_floor,
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        tolerance_m=0.02,
    )
    assert not report.converged
    assert "staircase_1" in report.misaligned_features


def test_vav_within_tolerance_converged():
    """Small drift (< tolerance) still converged."""
    stair_a = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    stair_b = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3.01, y_m=3.01, width_m=2, depth_m=2,  # 0.01m drift
    )
    per_floor = (
        ("first", _pc_with_room("first", stair_b)),
        ("ground", _pc_with_room("ground", stair_a)),
    )
    report = verify_vertical_alignment(
        per_floor_placements=per_floor,
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        tolerance_m=0.02,  # 20mm
    )
    assert report.converged


def test_vav_single_floor_trivially_converged():
    """Feature on only 1 floor → trivially aligned (nothing to align WITH)."""
    stair = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    per_floor = (("ground", _pc_with_room("ground", stair)),)
    report = verify_vertical_alignment(
        per_floor_placements=per_floor,
        feature_room_ids_by_floor={"ground": {"staircase_1"}},
        tolerance_m=0.02,
    )
    assert report.converged


# ─────────────────────────────────────────────────────────────────────
# MFRA
# ─────────────────────────────────────────────────────────────────────


def test_mfra_converges_on_aligned_input():
    stair = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    per_floor = (
        ("first", _pc_with_room("first", stair)),
        ("ground", _pc_with_room("ground", stair)),
    )
    mfc = absorb_multi_floor_placements(
        source_multifloor_signature="mf:test",
        per_floor_placements=per_floor,
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        vertical_cores_reserved=(),
        tolerance_m=0.02, max_realign_iterations=3,
        strict_mode=True,
    )
    assert mfc.alignment_report.converged
    assert mfc.alignment_report.retries_used == 0


def test_mfra_raises_on_misalignment_strict():
    stair_a = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    stair_b = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=5, y_m=5, width_m=2, depth_m=2,
    )
    per_floor = (
        ("first", _pc_with_room("first", stair_b)),
        ("ground", _pc_with_room("ground", stair_a)),
    )
    with pytest.raises(VerticalAlignmentError, match="MFRA failed"):
        absorb_multi_floor_placements(
            source_multifloor_signature="mf:test",
            per_floor_placements=per_floor,
            feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
            vertical_cores_reserved=(),
            tolerance_m=0.02, max_realign_iterations=3,
            strict_mode=True,
        )


def test_mfra_warn_mode_returns_unconverged():
    stair_a = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=3, y_m=3, width_m=2, depth_m=2,
    )
    stair_b = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=5, y_m=5, width_m=2, depth_m=2,
    )
    per_floor = (
        ("first", _pc_with_room("first", stair_b)),
        ("ground", _pc_with_room("ground", stair_a)),
    )
    mfc = absorb_multi_floor_placements(
        source_multifloor_signature="mf:test",
        per_floor_placements=per_floor,
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        vertical_cores_reserved=(),
        tolerance_m=0.02, max_realign_iterations=3,
        strict_mode=False,
    )
    assert not mfc.alignment_report.converged
    assert "staircase_1" in mfc.alignment_report.misaligned_features


# ─────────────────────────────────────────────────────────────────────
# Orchestrator — end-to-end
# ─────────────────────────────────────────────────────────────────────


def _basic_sf(sig: str = "rc:test") -> SingleFloorPlacementInput:
    return SingleFloorPlacementInput(
        candidate_signature=sig,
        capability_mode="MATERIALIZED",
        placement_safe=True,
        geometry_materialized=True,
        rooms=(
            _rs("bedroom_1", "bedroom", 4, 4),
            _rs("kitchen_1", "kitchen", 4, 4),
        ),
        envelope_width_m=8, envelope_depth_m=4,
        adjacency_hints=(),
    )


def test_orchestrator_single_floor_success():
    cfg = PlacementConfig()
    result = place_and_align(
        single_floor_inputs=(_basic_sf(),),
        multi_floor_inputs=(),
        config=cfg,
        c11b_env_fingerprint_hash="upstream_abc",
    )
    assert len(result.placed_candidates) == 1
    assert result.failures == ()
    assert result.c12_version == "v1.0"
    assert len(result.cache_key) == 64  # SHA256 hex


def test_orchestrator_replay_determinism():
    """Same inputs + same env hash + same config → identical output."""
    cfg = PlacementConfig()
    r1 = place_and_align(
        single_floor_inputs=(_basic_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_abc",
    )
    r2 = place_and_align(
        single_floor_inputs=(_basic_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_abc",
    )
    assert r1 == r2


def test_orchestrator_strict_mode_raises_on_infeasible():
    bad_sf = SingleFloorPlacementInput(
        candidate_signature="rc:bad",
        capability_mode="MATERIALIZED", placement_safe=True, geometry_materialized=True,
        rooms=(_rs("huge", "living", 100, 100),),  # too big
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(strict_mode=True)
    with pytest.raises(GeometricInfeasibilityError):
        place_and_align(
            single_floor_inputs=(bad_sf,), multi_floor_inputs=(),
            config=cfg, c11b_env_fingerprint_hash="upstream_abc",
        )


def test_orchestrator_warn_mode_records_failures():
    """Per § 0 STRICT/WARN dispatch: WARN mode captures failures."""
    bad_sf = SingleFloorPlacementInput(
        candidate_signature="rc:bad",
        capability_mode="MATERIALIZED", placement_safe=True, geometry_materialized=True,
        rooms=(_rs("huge", "living", 100, 100),),
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(strict_mode=False)
    result = place_and_align(
        single_floor_inputs=(bad_sf, _basic_sf("rc:good")),
        multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_abc",
    )
    # Failure recorded; the other candidate still succeeded.
    assert len(result.failures) == 1
    assert result.failures[0].error_type == "GeometricInfeasibilityError"
    assert len(result.placed_candidates) == 1
    assert result.placed_candidates[0].source_refined_candidate_signature == "rc:good"


def test_orchestrator_hard_adjacency_enforced():
    """HARD adjacency that's not realized → AdjacencyConstraintViolationError."""
    sf = SingleFloorPlacementInput(
        candidate_signature="rc:test",
        capability_mode="MATERIALIZED", placement_safe=True, geometry_materialized=True,
        rooms=(
            _rs("bedroom_1", "bedroom", 4, 4),
            _rs("kitchen_1", "kitchen", 4, 4),
        ),
        envelope_width_m=8, envelope_depth_m=4,
        # HARD adjacency between two rooms that DO share a wall — should pass
        adjacency_hints=(("bedroom_1", "kitchen_1", "hard"),),
    )
    cfg = PlacementConfig(strict_mode=True)
    result = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_abc",
    )
    # Rooms ARE adjacent (4x4 each in 8x4 envelope) → HARD satisfied.
    assert len(result.placed_candidates) == 1


def test_orchestrator_capability_flag_rejected():
    """Tier A SHALLOW input → CapabilityFlagInconsistencyError per v0.2-A1."""
    from buildemup.components.c12 import CapabilityFlagInconsistencyError
    sf = SingleFloorPlacementInput(
        candidate_signature="rc:tier_a",
        capability_mode="PREDICATE_ONLY",  # ← Tier A
        placement_safe=True, geometry_materialized=True,
        rooms=(_rs("bedroom_1", "bedroom", 4, 4),),
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(strict_mode=True)
    with pytest.raises(CapabilityFlagInconsistencyError, match="capability_mode"):
        place_and_align(
            single_floor_inputs=(sf,), multi_floor_inputs=(),
            config=cfg, c11b_env_fingerprint_hash="upstream_abc",
        )


def test_orchestrator_multi_floor_success():
    """Two-floor scenario with identical placements → VAV converges."""
    def _floor(sig: str) -> SingleFloorPlacementInput:
        return SingleFloorPlacementInput(
            candidate_signature=sig,
            capability_mode="MATERIALIZED",
            placement_safe=True, geometry_materialized=True,
            rooms=(
                _rs("bedroom_1", "bedroom", 4, 4),
                _rs("staircase_1", "staircase", 2, 4),
                _rs("bathroom_1", "bathroom", 2, 4),
            ),
            envelope_width_m=8, envelope_depth_m=4,
            adjacency_hints=(),
        )
    mf = MultiFloorPlacementInput(
        source_signature="mf:test",
        floors=(("first", _floor("rc:F1")), ("ground", _floor("rc:G0"))),
        feature_room_ids_by_floor={"first": {"staircase_1"}, "ground": {"staircase_1"}},
        vertical_cores=(),
    )
    cfg = PlacementConfig()
    result = place_and_align(
        single_floor_inputs=(), multi_floor_inputs=(mf,),
        config=cfg, c11b_env_fingerprint_hash="upstream_abc",
    )
    assert len(result.multifloor_placed_candidates) == 1
    mfc = result.multifloor_placed_candidates[0]
    assert mfc.alignment_report.converged


def test_orchestrator_env_fingerprint_changes_invalidate_cache():
    """Different upstream env → different cache key."""
    cfg = PlacementConfig()
    r1 = place_and_align(
        single_floor_inputs=(_basic_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_aaa",
    )
    r2 = place_and_align(
        single_floor_inputs=(_basic_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_bbb",
    )
    assert r1.cache_key != r2.cache_key
