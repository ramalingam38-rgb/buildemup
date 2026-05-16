"""Tests for C12 v1.0 pre-algorithm support layer (S44 continuation).

Covers:
- bounds (rectangle_contains, rectangles_overlap, snap_to_grid, axis_overlap_length)
- prng (TieBreakPRNG determinism)
- env_fingerprint (C12EnvironmentFingerprint + capture + cache key)
- input_resolution (schema probes, capability assertion, room category, NBC minima)
- shared_edges (derivation with ε / grid / NBC)
- reachability (BFS Phase 0b)
- vertical_core_reservation (Phase 1b dataclass + helpers)
"""
from __future__ import annotations

import pytest

from buildemup.components.c12 import (
    DEFAULT_EPSILON_M,
    DEFAULT_GRID_SNAP_M,
    MIN_SHARED_EDGE_LENGTH_M,
    NBC_2016_DOORWAY_MIN_BATHROOM_M,
    NBC_2016_DOORWAY_MIN_BEDROOM_M,
    NBC_2016_DOORWAY_MIN_GENERAL_M,
    NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M,
    C12EnvironmentFingerprint,
    CapabilityFlagInconsistencyError,
    PlacedRoom,
    PlacementConfig,
    TieBreakPRNG,
    UpstreamSchemaDriftError,
    VerticalCoreReservation,
    all_rooms_reachable,
    assert_materialized_capability,
    assert_no_internal_conflicts,
    assert_upstream_schema_versions,
    axis_overlap_length,
    canonicalize_reservations,
    capture_c12_environment_fingerprint,
    compute_c12_cache_key,
    derive_shared_edges,
    doorway_minimum_for_pair,
    is_canonical_other_room_category,
    list_unknown_other_rooms,
    normalize_other_room_category,
    rectangle_contains,
    rectangles_overlap,
    reservations_overlap,
    snap_to_grid,
)


# ─────────────────────────────────────────────────────────────────────
# bounds.py
# ─────────────────────────────────────────────────────────────────────


def test_rectangle_contains_strict_interior():
    assert rectangle_contains(0, 0, 10, 10, 1, 1, 5, 5)


def test_rectangle_contains_boundary_within_epsilon():
    # Inner exactly at boundary
    assert rectangle_contains(0, 0, 10, 10, 0, 0, 10, 10)


def test_rectangle_contains_extends_past_edge_rejected():
    assert not rectangle_contains(0, 0, 10, 10, 5, 5, 6, 6)


def test_rectangles_overlap_interior_overlap():
    assert rectangles_overlap(0, 0, 5, 5, 3, 3, 5, 5)


def test_rectangles_overlap_touching_edges_not_overlap():
    """Two rectangles sharing only an edge do NOT overlap in interior."""
    assert not rectangles_overlap(0, 0, 5, 5, 5, 0, 5, 5)


def test_rectangles_overlap_disjoint_not_overlap():
    assert not rectangles_overlap(0, 0, 5, 5, 10, 10, 5, 5)


def test_snap_to_grid_basic():
    assert snap_to_grid(0.50, grid_m=0.05) == 0.5
    assert snap_to_grid(1.234, grid_m=0.05) == 1.25


def test_snap_to_grid_rejects_non_positive_grid():
    with pytest.raises(ValueError, match="grid_m"):
        snap_to_grid(1.0, grid_m=0.0)


def test_snap_to_grid_deterministic_across_calls():
    a = snap_to_grid(1.7234, grid_m=0.05)
    b = snap_to_grid(1.7234, grid_m=0.05)
    assert a == b


def test_axis_overlap_length_basic():
    assert axis_overlap_length(0, 5, 3, 7) == 2.0


def test_axis_overlap_length_no_overlap():
    assert axis_overlap_length(0, 5, 10, 15) == 0.0


def test_axis_overlap_length_touching_at_point():
    """Intervals touching at exactly one point should give 0 overlap."""
    assert axis_overlap_length(0, 5, 5, 10) == 0.0


# ─────────────────────────────────────────────────────────────────────
# prng.py
# ─────────────────────────────────────────────────────────────────────


def test_prng_deterministic_same_seed():
    p1 = TieBreakPRNG(42)
    p2 = TieBreakPRNG(42)
    cands = [1, 2, 3, 4, 5]
    seq1 = [p1.tie_break_choice(cands) for _ in range(20)]
    seq2 = [p2.tie_break_choice(cands) for _ in range(20)]
    assert seq1 == seq2


def test_prng_different_seeds_give_different_sequences():
    p1 = TieBreakPRNG(1)
    p2 = TieBreakPRNG(2)
    cands = [1, 2, 3, 4, 5]
    seq1 = [p1.tie_break_choice(cands) for _ in range(20)]
    seq2 = [p2.tie_break_choice(cands) for _ in range(20)]
    assert seq1 != seq2


def test_prng_single_candidate_returns_it_directly():
    p = TieBreakPRNG(42)
    assert p.tie_break_choice(["only"]) == "only"


def test_prng_empty_candidates_raises():
    p = TieBreakPRNG(42)
    with pytest.raises(ValueError, match="at least one"):
        p.tie_break_choice([])


def test_prng_master_seed_property():
    p = TieBreakPRNG(123)
    assert p.master_seed == 123


# ─────────────────────────────────────────────────────────────────────
# env_fingerprint.py
# ─────────────────────────────────────────────────────────────────────


def test_env_fingerprint_capture_basic():
    cfg = PlacementConfig()
    fp = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="upstream_hash_abc",
        config=cfg,
    )
    assert fp.c12_version == "v1.0"
    assert fp.c11b_env_fingerprint_hash == "upstream_hash_abc"
    assert len(fp.fingerprint_hash) == 64  # SHA256 hex


def test_env_fingerprint_same_inputs_same_hash():
    cfg = PlacementConfig()
    fp1 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="upstream_hash_abc", config=cfg,
    )
    fp2 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="upstream_hash_abc", config=cfg,
    )
    assert fp1.fingerprint_hash == fp2.fingerprint_hash
    assert fp1.matches(fp2)


def test_env_fingerprint_differs_on_different_upstream():
    cfg = PlacementConfig()
    fp1 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="upstream_hash_aaa", config=cfg,
    )
    fp2 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="upstream_hash_bbb", config=cfg,
    )
    assert fp1.fingerprint_hash != fp2.fingerprint_hash


def test_env_fingerprint_differs_on_different_cache_relevant_config():
    """Changing a cache_relevant field changes the fingerprint."""
    fp1 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up", config=PlacementConfig(),
    )
    fp2 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up",
        config=PlacementConfig(vertical_alignment_tolerance_m=0.05),
    )
    assert fp1.fingerprint_hash != fp2.fingerprint_hash


def test_env_fingerprint_invariant_to_non_cache_relevant_config():
    """Changing a NON-cache_relevant field (wallclock) does NOT
    change the fingerprint, per v0.3-A6."""
    fp1 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up",
        config=PlacementConfig(per_candidate_wallclock_seconds=10.0),
    )
    fp2 = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up",
        config=PlacementConfig(per_candidate_wallclock_seconds=30.0),
    )
    assert fp1.fingerprint_hash == fp2.fingerprint_hash


def test_env_fingerprint_rejects_empty_upstream_hash():
    with pytest.raises(ValueError, match="c11b_env_fingerprint_hash"):
        capture_c12_environment_fingerprint(
            c11b_env_fingerprint_hash="", config=PlacementConfig(),
        )


def test_compute_c12_cache_key_matches_fingerprint_hash():
    cfg = PlacementConfig()
    fp = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up", config=cfg,
    )
    assert compute_c12_cache_key(fp) == fp.fingerprint_hash


# ─────────────────────────────────────────────────────────────────────
# input_resolution.py — schema probes
# ─────────────────────────────────────────────────────────────────────


def test_schema_version_probes_pass_at_v1_baseline():
    """Both upstream constants are at v1, so the probe must succeed."""
    assert_upstream_schema_versions()  # no exception


def test_schema_version_probes_can_detect_drift(monkeypatch):
    """Simulate upstream schema-version bump by monkey-patching."""
    import buildemup.components.c08.schema as c8_schema
    monkeypatch.setattr(c8_schema, "CORRIDOR_ZONE_SCHEMA_VERSION", 99)
    with pytest.raises(UpstreamSchemaDriftError, match="CORRIDOR_ZONE_SCHEMA_VERSION"):
        assert_upstream_schema_versions()


# ─────────────────────────────────────────────────────────────────────
# input_resolution.py — capability flag assertion
# ─────────────────────────────────────────────────────────────────────


def test_capability_assertion_passes_on_materialized():
    """Happy path: all three flags consistent."""
    assert_materialized_capability(
        candidate_signature="rc:abc",
        capability_mode="MATERIALIZED",
        placement_safe=True,
        geometry_materialized=True,
    )


def test_capability_assertion_rejects_unmaterialized_geometry():
    with pytest.raises(CapabilityFlagInconsistencyError, match="geometry_materialized"):
        assert_materialized_capability(
            candidate_signature="rc:abc",
            capability_mode="MATERIALIZED",
            placement_safe=True,
            geometry_materialized=False,
        )


def test_capability_assertion_rejects_unsafe_placement():
    with pytest.raises(CapabilityFlagInconsistencyError, match="placement_safe"):
        assert_materialized_capability(
            candidate_signature="rc:abc",
            capability_mode="MATERIALIZED",
            placement_safe=False,
            geometry_materialized=True,
        )


def test_capability_assertion_rejects_predicate_only_mode():
    with pytest.raises(CapabilityFlagInconsistencyError, match="capability_mode"):
        assert_materialized_capability(
            candidate_signature="rc:abc",
            capability_mode="PREDICATE_ONLY",
            placement_safe=True,
            geometry_materialized=True,
        )


# ─────────────────────────────────────────────────────────────────────
# input_resolution.py — room category resolution
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [
    # Exact-canonical
    ("guest_bedroom", "guest_bedroom"),
    ("study", "study"),
    ("balcony", "balcony"),
    ("store", "store"),
    ("servant", "servant"),
    # Hyphen variants
    ("guest-bedroom", "guest_bedroom"),
    ("study-room", "study"),
    # Camel-case variants
    ("GuestBedroom", "guest_bedroom"),
    # Spaced variants
    ("guest room", "guest_bedroom"),
    ("study room", "study"),
    # Aliased "storage"
    ("storage", "store"),
    # Servant variants
    ("servant_quarter", "servant"),
    ("servant quarter", "servant"),
])
def test_normalize_other_room_category_known_variants(raw, expected):
    assert normalize_other_room_category(raw) == expected


def test_normalize_other_room_category_unknown_falls_to_other():
    assert normalize_other_room_category("FooBar") == "other"
    assert normalize_other_room_category("library") == "other"


def test_is_canonical_other_room_category():
    assert is_canonical_other_room_category("guest_bedroom")
    assert is_canonical_other_room_category("other")
    assert not is_canonical_other_room_category("library")


def test_list_unknown_other_rooms():
    raw = ("guest_bedroom", "study", "library", "media_room", "balcony")
    unknown = list_unknown_other_rooms(raw)
    assert "library" in unknown
    assert "media_room" in unknown
    assert "guest_bedroom" not in unknown


# ─────────────────────────────────────────────────────────────────────
# input_resolution.py — NBC 2016 doorway minima
# ─────────────────────────────────────────────────────────────────────


def test_nbc_constants_match_spec():
    """Per NBC 2016 Part 3 (web-verified at v0.2 walk)."""
    assert NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M == 1.00
    assert NBC_2016_DOORWAY_MIN_BEDROOM_M == 0.90
    assert NBC_2016_DOORWAY_MIN_BATHROOM_M == 0.75
    assert NBC_2016_DOORWAY_MIN_GENERAL_M == 0.75


@pytest.mark.parametrize("a,b,expected", [
    ("main_entrance", "living", 1.00),
    ("foyer", "living", 1.00),
    ("bedroom", "bathroom", 0.90),
    ("master_bedroom", "master_bathroom", 0.90),  # bedroom priority > bathroom
    ("bathroom", "kitchen", 0.75),
    ("wc", "kitchen", 0.75),
    ("kitchen", "living", 0.75),  # general fallback
])
def test_doorway_minimum_priority_order(a, b, expected):
    assert doorway_minimum_for_pair(a, b) == expected


def test_doorway_minimum_order_invariant():
    """Same pair in either order gives the same minimum."""
    assert doorway_minimum_for_pair("bedroom", "bathroom") == doorway_minimum_for_pair("bathroom", "bedroom")


# ─────────────────────────────────────────────────────────────────────
# shared_edges.py
# ─────────────────────────────────────────────────────────────────────


def _r(rid: str, cat: str, x: float, y: float, w: float, d: float) -> PlacedRoom:
    return PlacedRoom(
        room_id=rid, category=cat, x_m=x, y_m=y, width_m=w, depth_m=d,
    )


def test_shared_edge_vertical_wall_full_overlap():
    """Two 4x4 rooms side-by-side, sharing a 4m vertical wall."""
    r1 = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    r2 = _r("bedroom_2", "bedroom", 4, 0, 4, 4)
    edges = derive_shared_edges((r1, r2))
    assert len(edges) == 1
    e = edges[0]
    assert e.axis == "vertical"
    assert e.overlap_length_m == 4.0
    assert e.room_a_id == "bedroom_1"  # canonical lex-ASC
    assert e.room_b_id == "bedroom_2"
    assert e.doorway_feasible  # 4m > 0.9m bedroom minimum


def test_shared_edge_horizontal_wall():
    """Two rooms stacked, sharing a horizontal wall."""
    r1 = _r("living_1", "living", 0, 0, 5, 3)
    r2 = _r("kitchen_1", "kitchen", 0, 3, 5, 3)
    edges = derive_shared_edges((r1, r2))
    assert len(edges) == 1
    assert edges[0].axis == "horizontal"
    assert edges[0].overlap_length_m == 5.0


def test_shared_edge_canonical_id_ordering():
    """The returned room_a_id < room_b_id regardless of input order."""
    # Pass in "z" first, "a" second — canonical output is (a, z).
    rz = _r("z_room", "bedroom", 4, 0, 4, 4)
    ra = _r("a_room", "bedroom", 0, 0, 4, 4)
    edges = derive_shared_edges((rz, ra))
    assert len(edges) == 1
    assert edges[0].room_a_id == "a_room"
    assert edges[0].room_b_id == "z_room"


def test_shared_edge_partial_overlap():
    """Rooms sharing only part of a wall."""
    r1 = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    r2 = _r("bedroom_2", "bedroom", 4, 2, 4, 4)  # offset by 2m in y
    edges = derive_shared_edges((r1, r2))
    assert len(edges) == 1
    assert edges[0].overlap_length_m == 2.0  # y in [2,4]


def test_shared_edge_no_overlap_disjoint():
    """Rooms not touching → no shared edge."""
    r1 = _r("bedroom_1", "bedroom", 0, 0, 3, 3)
    r2 = _r("bedroom_2", "bedroom", 5, 5, 3, 3)
    edges = derive_shared_edges((r1, r2))
    assert edges == ()


def test_shared_edge_sliver_rejected():
    """An overlap < 0.75m (general NBC min) is rejected outright."""
    r1 = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    # r2 offset so only 0.5m overlaps on y
    r2 = _r("bedroom_2", "bedroom", 4, 3.5, 4, 4)
    edges = derive_shared_edges((r1, r2))
    assert edges == ()  # too short for any door


def test_shared_edge_bedroom_bathroom_doorway_feasible():
    """A 2m wall between bedroom and bathroom: feasible (≥0.9m)."""
    r_bed = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    r_bath = _r("bathroom_1", "bathroom", 4, 0, 2, 2)
    edges = derive_shared_edges((r_bed, r_bath))
    assert len(edges) == 1
    assert edges[0].min_required_clear_width_m == 0.9
    assert edges[0].doorway_feasible


def test_shared_edge_canonical_sort_multiple_edges():
    """Edges in output tuple are sorted lex-ASC by (room_a_id, room_b_id)."""
    # Three rooms in a row: r_a — r_b — r_c
    r_a = _r("a_room", "bedroom", 0, 0, 4, 4)
    r_b = _r("b_room", "bedroom", 4, 0, 4, 4)
    r_c = _r("c_room", "bedroom", 8, 0, 4, 4)
    edges = derive_shared_edges((r_a, r_b, r_c))
    assert len(edges) == 2
    # canonical: (a_room, b_room) then (b_room, c_room)
    assert edges[0].room_a_id == "a_room" and edges[0].room_b_id == "b_room"
    assert edges[1].room_a_id == "b_room" and edges[1].room_b_id == "c_room"


def test_shared_edge_deterministic_under_input_permutation():
    """Per Inv 7 / v0.2-A4 rule #1: same room set in different orders
    gives byte-identical SharedEdge output."""
    rooms_order_1 = (
        _r("alpha", "bedroom", 0, 0, 4, 4),
        _r("beta", "bedroom", 4, 0, 4, 4),
        _r("gamma", "bedroom", 8, 0, 4, 4),
    )
    rooms_order_2 = (rooms_order_1[2], rooms_order_1[0], rooms_order_1[1])
    e1 = derive_shared_edges(rooms_order_1)
    e2 = derive_shared_edges(rooms_order_2)
    assert e1 == e2


# ─────────────────────────────────────────────────────────────────────
# reachability.py
# ─────────────────────────────────────────────────────────────────────


def test_reachability_single_room_no_corridors():
    """A single room is trivially reachable (it IS the building)."""
    r = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    ok, unreachable = all_rooms_reachable(
        placed_rooms=(r,),
        corridor_zones=(),
        entry_zone_indices=(),
    )
    assert ok
    assert unreachable == ()


def test_reachability_two_rooms_no_corridors_infeasible():
    r1 = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    r2 = _r("bedroom_2", "bedroom", 5, 5, 4, 4)
    ok, unreachable = all_rooms_reachable(
        placed_rooms=(r1, r2),
        corridor_zones=(),
        entry_zone_indices=(),
    )
    assert not ok
    assert "bedroom_2" in unreachable


def test_reachability_with_corridor_and_entry():
    """Two rooms connected by a corridor; corridor touches envelope edge → entry."""
    r1 = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    r2 = _r("bedroom_2", "bedroom", 5, 0, 4, 4)
    # Corridor in the gap between them
    corridor = (4.0, 0.0, 1.0, 4.0)  # x=4, y=0, w=1, d=4
    ok, unreachable = all_rooms_reachable(
        placed_rooms=(r1, r2),
        corridor_zones=(corridor,),
        entry_zone_indices=(0,),
    )
    assert ok
    assert unreachable == ()


def test_reachability_no_entry_points_infeasible():
    """Corridors exist but no entry → unreachable."""
    r = _r("bedroom_1", "bedroom", 0, 0, 4, 4)
    corridor = (4.0, 0.0, 1.0, 4.0)
    ok, unreachable = all_rooms_reachable(
        placed_rooms=(r,),
        corridor_zones=(corridor,),
        entry_zone_indices=(),
    )
    assert not ok
    assert "bedroom_1" in unreachable


def test_reachability_isolated_room_unreachable():
    """Room not touching any corridor → unreachable even if corridor exists."""
    r_connected = _r("connected", "bedroom", 0, 0, 4, 4)
    r_isolated = _r("isolated", "bedroom", 10, 10, 4, 4)  # far away
    corridor = (4.0, 0.0, 1.0, 4.0)
    ok, unreachable = all_rooms_reachable(
        placed_rooms=(r_connected, r_isolated),
        corridor_zones=(corridor,),
        entry_zone_indices=(0,),
    )
    assert not ok
    assert "isolated" in unreachable
    assert "connected" not in unreachable


# ─────────────────────────────────────────────────────────────────────
# vertical_core_reservation.py
# ─────────────────────────────────────────────────────────────────────


def test_vertical_core_reservation_construction():
    v = VerticalCoreReservation(
        label="staircase_1",
        kind="staircase",
        x_m=3.0, y_m=2.0, width_m=1.5, depth_m=3.0,
    )
    assert v.kind == "staircase"
    assert v.to_tuple() == ("staircase_1", 3.0, 2.0, 1.5, 3.0)


def test_vertical_core_rejects_empty_label():
    with pytest.raises(ValueError, match="label"):
        VerticalCoreReservation(
            label="", kind="staircase",
            x_m=0, y_m=0, width_m=1, depth_m=1,
        )


def test_vertical_core_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        VerticalCoreReservation(
            label="x", kind="elevator",  # type: ignore
            x_m=0, y_m=0, width_m=1, depth_m=1,
        )


def test_vertical_core_rejects_non_positive_extents():
    with pytest.raises(ValueError, match="positive extents"):
        VerticalCoreReservation(
            label="x", kind="staircase",
            x_m=0, y_m=0, width_m=0, depth_m=1,
        )


def test_canonicalize_reservations_sorts():
    a = VerticalCoreReservation(
        label="z_core", kind="staircase",
        x_m=0, y_m=0, width_m=1, depth_m=1,
    )
    b = VerticalCoreReservation(
        label="a_core", kind="wet_zone_column",
        x_m=5, y_m=5, width_m=1, depth_m=1,
    )
    out = canonicalize_reservations((a, b))
    assert out[0].label == "a_core"
    assert out[1].label == "z_core"


def test_canonicalize_reservations_rejects_duplicate_labels():
    a = VerticalCoreReservation(
        label="x", kind="staircase",
        x_m=0, y_m=0, width_m=1, depth_m=1,
    )
    b = VerticalCoreReservation(
        label="x", kind="wet_zone_column",
        x_m=5, y_m=5, width_m=1, depth_m=1,
    )
    with pytest.raises(ValueError, match="duplicate"):
        canonicalize_reservations((a, b))


def test_reservations_overlap_interior():
    a = VerticalCoreReservation(
        label="a", kind="staircase",
        x_m=0, y_m=0, width_m=3, depth_m=3,
    )
    b = VerticalCoreReservation(
        label="b", kind="staircase",
        x_m=1, y_m=1, width_m=3, depth_m=3,
    )
    assert reservations_overlap(a, b)


def test_reservations_touching_not_overlap():
    a = VerticalCoreReservation(
        label="a", kind="staircase",
        x_m=0, y_m=0, width_m=3, depth_m=3,
    )
    b = VerticalCoreReservation(
        label="b", kind="wet_zone_column",
        x_m=3, y_m=0, width_m=3, depth_m=3,
    )
    assert not reservations_overlap(a, b)


def test_assert_no_internal_conflicts_passes_for_disjoint():
    a = VerticalCoreReservation(
        label="a", kind="staircase",
        x_m=0, y_m=0, width_m=2, depth_m=2,
    )
    b = VerticalCoreReservation(
        label="b", kind="wet_zone_column",
        x_m=5, y_m=5, width_m=2, depth_m=2,
    )
    assert_no_internal_conflicts((a, b))


def test_assert_no_internal_conflicts_raises_on_overlap():
    a = VerticalCoreReservation(
        label="a", kind="staircase",
        x_m=0, y_m=0, width_m=3, depth_m=3,
    )
    b = VerticalCoreReservation(
        label="b", kind="staircase",
        x_m=1, y_m=1, width_m=3, depth_m=3,
    )
    with pytest.raises(ValueError, match="overlap"):
        assert_no_internal_conflicts((a, b))
