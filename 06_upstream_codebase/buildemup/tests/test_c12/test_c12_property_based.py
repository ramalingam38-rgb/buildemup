"""
C12 v1.0 LOCKED property-based tests
=====================================

Per C12 SPEC v1.0 LOCKED v0.5-A1 + v0.6-A1 (invariant-grounded
PBT coverage):

  ≥1 PBT per LOCKED invariant (Inv 1-13):             13 minimum
  ≥1 PBT per failure-mode trigger condition:           7 minimum
  ≥1 adversarial-generator PBT for each of:
    - near-unsat layouts (rooms barely fitting)
    - tiny residual spaces
    - high-density adjacency graphs
    - staircase conflicts (vertical core misaligned)
    - input-permutation determinism

Total floor: 25 PBT tests.

Hypothesis is already a project dependency (test_c11a_subsession5_
stress_fuzz.py / test_c4_property_based.py / test_c5_stability.py).
Pattern follows test_c11a_subsession5_stress_fuzz.py.

Coverage map (each test header marks which invariant or trigger
it covers).
"""
from __future__ import annotations

import pytest

try:
    from hypothesis import HealthCheck, assume, given, settings, strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _HYPOTHESIS_AVAILABLE = False

if not _HYPOTHESIS_AVAILABLE:
    pytest.skip("hypothesis not available", allow_module_level=True)

from buildemup.components.c12 import (
    AdjacencyConstraintViolationError,
    CapabilityFlagInconsistencyError,
    C12ConfigurationError,
    GeometricInfeasibilityError,
    PlacedRoom,
    PlacementConfig,
    RoomSpec,
    SingleFloorPlacementInput,
    UpstreamSchemaDriftError,
    VerticalAlignmentError,
    VerticalCoreReservation,
    all_rooms_reachable,
    derive_shared_edges,
    doorway_minimum_for_pair,
    normalize_other_room_category,
    place_and_align,
    place_rooms_slicing_tree,
)
from buildemup.components.c12.shared_edges import MIN_SHARED_EDGE_LENGTH_M


# ─────────────────────────────────────────────────────────────────────
# Hypothesis strategies
# ─────────────────────────────────────────────────────────────────────


@st.composite
def _room_spec_strategy(draw, *, max_dim: float = 6.0):
    """Generate a RoomSpec with reasonable dimensions."""
    rid = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)),
        min_size=2, max_size=10,
    ))
    cat = draw(st.sampled_from([
        "bedroom", "bathroom", "kitchen", "living", "pooja", "utility",
    ]))
    w = draw(st.floats(min_value=1.0, max_value=max_dim))
    d = draw(st.floats(min_value=1.0, max_value=max_dim))
    return RoomSpec(
        room_id=rid, category=cat,
        target_width_m=w, target_depth_m=d,
    )


@st.composite
def _unique_room_set_strategy(draw, *, n_min: int = 1, n_max: int = 6, max_dim: float = 5.0):
    """Generate a tuple of RoomSpecs with unique room_ids."""
    n = draw(st.integers(min_value=n_min, max_value=n_max))
    rooms: list[RoomSpec] = []
    used_ids: set[str] = set()
    attempts = 0
    while len(rooms) < n and attempts < 50:
        attempts += 1
        rs = draw(_room_spec_strategy(max_dim=max_dim))
        if rs.room_id not in used_ids:
            used_ids.add(rs.room_id)
            rooms.append(rs)
    if not rooms:
        # Fallback: deterministic small set
        rooms.append(RoomSpec(
            room_id="r0", category="bedroom",
            target_width_m=2.0, target_depth_m=2.0,
        ))
    return tuple(rooms)


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-1 — Containment: every placed room is inside the envelope
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=1, n_max=4, max_dim=4.0))
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_inv1_containment(rooms):
    """Inv 1: every placed room is contained within the envelope."""
    envelope_w = 12.0
    envelope_d = 12.0
    total_area = sum(r.area_m2 for r in rooms)
    assume(total_area <= envelope_w * envelope_d * 0.9)  # leave 10% slack

    try:
        placed = place_rooms_slicing_tree(
            rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d,
        )
    except GeometricInfeasibilityError:
        return  # Algorithm validly rejected this case

    for p in placed:
        assert p.x_m >= -1e-6
        assert p.y_m >= -1e-6
        assert p.x_m + p.width_m <= envelope_w + 1e-6
        assert p.y_m + p.depth_m <= envelope_d + 1e-6


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-2 — Non-overlap: no two placed rooms overlap in interior
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=2, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv2_non_overlap(rooms):
    """Inv 2: no two placed rooms overlap in interior."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        placed = place_rooms_slicing_tree(
            rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d,
        )
    except GeometricInfeasibilityError:
        return
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            x_sep = (
                a.x_m + a.width_m <= b.x_m + 1e-6
                or b.x_m + b.width_m <= a.x_m + 1e-6
            )
            y_sep = (
                a.y_m + a.depth_m <= b.y_m + 1e-6
                or b.y_m + b.depth_m <= a.y_m + 1e-6
            )
            assert x_sep or y_sep, f"{a.room_id} overlaps {b.room_id}"


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-3 — All input rooms placed (no drops, no extras)
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=1, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv3_all_rooms_placed(rooms):
    """Inv 3: every input room appears exactly once in the output."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        placed = place_rooms_slicing_tree(
            rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d,
        )
    except GeometricInfeasibilityError:
        return
    placed_ids = sorted(p.room_id for p in placed)
    input_ids = sorted(r.room_id for r in rooms)
    assert placed_ids == input_ids


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-7 — Byte-equal replay determinism
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=2, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv7_deterministic_replay(rooms):
    """Inv 7: same input twice → byte-equal output."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        p1 = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
        p2 = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
    except GeometricInfeasibilityError:
        return
    assert p1 == p2


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-7-PERM — Permutation-invariant determinism (adversarial)
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=3, n_max=5, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv7_permutation_invariant(rooms):
    """Adversarial: same room SET in DIFFERENT input order → byte-equal output."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    rooms_reversed = tuple(reversed(rooms))
    try:
        p1 = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
        p2 = place_rooms_slicing_tree(rooms_reversed, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
    except GeometricInfeasibilityError:
        return
    assert p1 == p2


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-8 — SharedEdge canonical ordering
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=2, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv8_shared_edge_canonical_order(rooms):
    """Inv 8: shared_edges sorted lex-ASC by (room_a_id, room_b_id)."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        placed = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
    except GeometricInfeasibilityError:
        return
    edges = derive_shared_edges(placed)
    keys = [(e.room_a_id, e.room_b_id) for e in edges]
    assert keys == sorted(keys)
    for e in edges:
        assert e.room_a_id < e.room_b_id  # canonical pair ordering


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-9 — SharedEdge ε-tolerance + grid snapping
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=2, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv9_shared_edge_grid_snapped(rooms):
    """Inv 9: SharedEdge coordinates snapped to grid resolution (0.05m)."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        placed = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
    except GeometricInfeasibilityError:
        return
    edges = derive_shared_edges(placed)
    for e in edges:
        # Snapped values are multiples of 0.05 within FP tolerance.
        assert abs(round(e.overlap_start_m / 0.05) * 0.05 - e.overlap_start_m) < 1e-6
        assert abs(round(e.overlap_end_m / 0.05) * 0.05 - e.overlap_end_m) < 1e-6


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-10 — SharedEdge length positive
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=2, n_max=4, max_dim=4.0))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
def test_pbt_inv10_shared_edge_length_positive(rooms):
    """Inv 10: every SharedEdge has overlap_length_m ≥ MIN_SHARED_EDGE_LENGTH_M."""
    envelope_w, envelope_d = 12.0, 12.0
    assume(sum(r.area_m2 for r in rooms) <= envelope_w * envelope_d * 0.9)
    try:
        placed = place_rooms_slicing_tree(rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d)
    except GeometricInfeasibilityError:
        return
    edges = derive_shared_edges(placed)
    for e in edges:
        assert e.overlap_length_m >= MIN_SHARED_EDGE_LENGTH_M - 1e-9


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-11 — Reachability BFS over corridors
# ─────────────────────────────────────────────────────────────────────


@given(
    n_rooms=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_inv11_reachability_single_corridor(n_rooms):
    """Inv 11: with a corridor touching every room, all rooms are reachable."""
    # Lay out rooms in a horizontal strip with a corridor along the
    # bottom touching all of them.
    rooms = tuple(
        PlacedRoom(
            room_id=f"r_{i}", category="bedroom",
            x_m=i * 3.0, y_m=2.0, width_m=3.0, depth_m=3.0,
        )
        for i in range(n_rooms)
    )
    corridor = (0.0, 0.0, n_rooms * 3.0, 2.0)
    ok, unreachable = all_rooms_reachable(
        placed_rooms=rooms,
        corridor_zones=(corridor,),
        entry_zone_indices=(0,),
    )
    assert ok
    assert unreachable == ()


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-12 — Doorway feasibility per NBC 2016
# ─────────────────────────────────────────────────────────────────────


@given(
    cat_a=st.sampled_from(["bedroom", "bathroom", "kitchen", "living", "main_entrance"]),
    cat_b=st.sampled_from(["bedroom", "bathroom", "kitchen", "living", "main_entrance"]),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_inv12_doorway_minimum_priority(cat_a, cat_b):
    """Inv 12: doorway minimum follows the priority order
    main_entrance > bedroom > bathroom > general."""
    minimum = doorway_minimum_for_pair(cat_a, cat_b)
    if "main_entrance" in (cat_a, cat_b):
        assert minimum == 1.00
    elif "bedroom" in (cat_a, cat_b):
        assert minimum == 0.90
    elif "bathroom" in (cat_a, cat_b):
        assert minimum == 0.75
    else:
        assert minimum == 0.75


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-12-COMMUTATIVE — Doorway minimum order-invariant
# ─────────────────────────────────────────────────────────────────────


@given(
    cat_a=st.sampled_from(["bedroom", "bathroom", "kitchen", "living", "main_entrance"]),
    cat_b=st.sampled_from(["bedroom", "bathroom", "kitchen", "living", "main_entrance"]),
)
@settings(max_examples=50)
def test_pbt_inv12_doorway_minimum_commutative(cat_a, cat_b):
    """Doorway minimum is order-invariant (commutative)."""
    assert doorway_minimum_for_pair(cat_a, cat_b) == doorway_minimum_for_pair(cat_b, cat_a)


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-13 — MFRA delta_progression length bounded
# ─────────────────────────────────────────────────────────────────────


def test_pbt_inv13_mfra_delta_progression_bounded():
    """Inv 13: delta_progression length ≤ max_realign_iterations + 1.

    PBT-style with varying max_realign_iterations values."""
    from buildemup.components.c12 import absorb_multi_floor_placements

    for max_iter in (0, 1, 2, 3, 5):
        # Build mismatched stair positions to force retries.
        stair_a = PlacedRoom(
            room_id="staircase_1", category="staircase",
            x_m=2, y_m=2, width_m=2, depth_m=2,
        )
        stair_b = PlacedRoom(
            room_id="staircase_1", category="staircase",
            x_m=6, y_m=6, width_m=2, depth_m=2,
        )
        from buildemup.components.c12 import PlacedCandidate
        pc_ground = PlacedCandidate(
            source_refined_candidate_signature="rc:g",
            placed_rooms=(stair_a,), shared_edges=(),
            placement_algorithm="slicing_kd_tree",
            envelope_width_m=10, envelope_depth_m=10,
        )
        pc_first = PlacedCandidate(
            source_refined_candidate_signature="rc:f",
            placed_rooms=(stair_b,), shared_edges=(),
            placement_algorithm="slicing_kd_tree",
            envelope_width_m=10, envelope_depth_m=10,
        )
        try:
            mfc = absorb_multi_floor_placements(
                source_multifloor_signature="mf:test",
                per_floor_placements=(("first", pc_first), ("ground", pc_ground)),
                feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
                vertical_cores_reserved=(),
                tolerance_m=0.02, max_realign_iterations=max_iter,
                strict_mode=False,
            )
            assert len(mfc.alignment_report.delta_progression) <= max_iter + 1
        except VerticalAlignmentError:
            pass  # STRICT-mode raise is also valid


# ─────────────────────────────────────────────────────────────────────
# PBT-Failure — UpstreamSchemaDriftError trigger
# ─────────────────────────────────────────────────────────────────────


@given(bad_version=st.integers(min_value=2, max_value=100))
@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_pbt_failure_schema_drift_detected(bad_version, monkeypatch):
    """Failure trigger: any non-1 upstream version raises UpstreamSchemaDriftError."""
    from buildemup.components.c12.input_resolution import assert_upstream_schema_versions
    import buildemup.components.c08.schema as c8_schema
    monkeypatch.setattr(c8_schema, "CORRIDOR_ZONE_SCHEMA_VERSION", bad_version)
    with pytest.raises(UpstreamSchemaDriftError):
        assert_upstream_schema_versions()


# ─────────────────────────────────────────────────────────────────────
# PBT-Failure — CapabilityFlagInconsistencyError trigger
# ─────────────────────────────────────────────────────────────────────


@given(
    cap_mode=st.sampled_from(["PREDICATE_ONLY", "UNKNOWN", "TIER_A_SHALLOW", ""]),
)
@settings(max_examples=20)
def test_pbt_failure_capability_flag_inconsistency(cap_mode):
    """Failure trigger: any non-MATERIALIZED capability_mode rejects."""
    from buildemup.components.c12 import assert_materialized_capability
    with pytest.raises(CapabilityFlagInconsistencyError):
        assert_materialized_capability(
            candidate_signature="rc:test",
            capability_mode=cap_mode,
            placement_safe=True,
            geometry_materialized=True,
        )


# ─────────────────────────────────────────────────────────────────────
# PBT-Failure — GeometricInfeasibilityError trigger
# ─────────────────────────────────────────────────────────────────────


@given(
    envelope_w=st.floats(min_value=1.0, max_value=3.0),
    envelope_d=st.floats(min_value=1.0, max_value=3.0),
    room_w=st.floats(min_value=5.0, max_value=10.0),
)
@settings(max_examples=20)
def test_pbt_failure_geometric_infeasibility_oversized_room(envelope_w, envelope_d, room_w):
    """Failure trigger: room larger than envelope → GeometricInfeasibilityError."""
    rooms = (RoomSpec(
        room_id="huge", category="living",
        target_width_m=room_w, target_depth_m=2.0,
    ),)
    with pytest.raises(GeometricInfeasibilityError):
        place_rooms_slicing_tree(
            rooms, envelope_width_m=envelope_w, envelope_depth_m=envelope_d,
        )


# ─────────────────────────────────────────────────────────────────────
# PBT-Failure — VerticalAlignmentError trigger
# ─────────────────────────────────────────────────────────────────────


def test_pbt_failure_vertical_alignment_error_strict():
    """Failure trigger: misaligned MF features in STRICT mode raise."""
    from buildemup.components.c12 import absorb_multi_floor_placements, PlacedCandidate
    stair_a = PlacedRoom(room_id="s", category="staircase", x_m=1, y_m=1, width_m=2, depth_m=2)
    stair_b = PlacedRoom(room_id="s", category="staircase", x_m=5, y_m=5, width_m=2, depth_m=2)
    pc_g = PlacedCandidate(
        source_refined_candidate_signature="rc:g",
        placed_rooms=(stair_a,), shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10, envelope_depth_m=10,
    )
    pc_f = PlacedCandidate(
        source_refined_candidate_signature="rc:f",
        placed_rooms=(stair_b,), shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10, envelope_depth_m=10,
    )
    with pytest.raises(VerticalAlignmentError):
        absorb_multi_floor_placements(
            source_multifloor_signature="mf",
            per_floor_placements=(("first", pc_f), ("ground", pc_g)),
            feature_room_ids_by_floor={"ground": {"s"}, "first": {"s"}},
            vertical_cores_reserved=(),
            tolerance_m=0.02, max_realign_iterations=3,
            strict_mode=True,
        )


# ─────────────────────────────────────────────────────────────────────
# PBT-Failure — C12ConfigurationError trigger
# ─────────────────────────────────────────────────────────────────────


@given(
    bad_tolerance=st.floats(min_value=-1.0, max_value=-0.001),
)
@settings(max_examples=20)
def test_pbt_failure_config_negative_tolerance(bad_tolerance):
    """Failure trigger: negative alignment tolerance → C12ConfigurationError."""
    with pytest.raises(C12ConfigurationError):
        PlacementConfig(vertical_alignment_tolerance_m=bad_tolerance)


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — Near-unsat layouts (room just fits)
# ─────────────────────────────────────────────────────────────────────


@given(
    room_dim=st.floats(min_value=2.0, max_value=5.0),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_adversarial_room_exactly_fills_envelope(room_dim):
    """Adversarial: single room exactly filling envelope is feasible."""
    rooms = (RoomSpec(
        room_id="exact_fit", category="living",
        target_width_m=room_dim, target_depth_m=room_dim,
    ),)
    placed = place_rooms_slicing_tree(
        rooms,
        envelope_width_m=room_dim, envelope_depth_m=room_dim,
    )
    assert len(placed) == 1


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — Tiny residual spaces handled gracefully
# ─────────────────────────────────────────────────────────────────────


@given(slack=st.floats(min_value=0.0, max_value=0.5))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_adversarial_tiny_residual_space(slack):
    """Adversarial: envelope with very little slack — either succeeds or
    raises GeometricInfeasibilityError cleanly, never crashes."""
    rooms = (
        RoomSpec(room_id="a", category="bedroom", target_width_m=4, target_depth_m=4),
        RoomSpec(room_id="b", category="bedroom", target_width_m=4, target_depth_m=4),
    )
    # Total area = 32. Envelope barely fits.
    env_w = 8 + slack
    env_d = 4 + slack * 0.5
    try:
        placed = place_rooms_slicing_tree(
            rooms, envelope_width_m=env_w, envelope_depth_m=env_d,
        )
        assert len(placed) == 2
    except GeometricInfeasibilityError:
        pass  # Algorithm honestly reports infeasibility


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — Alias-map normalization stability
# ─────────────────────────────────────────────────────────────────────


@given(
    raw=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu"), whitelist_characters=" -_"),
        min_size=1, max_size=20,
    ),
)
@settings(max_examples=50)
def test_pbt_adversarial_alias_normalization_never_crashes(raw):
    """Adversarial: any string input to normalize_other_room_category
    returns a known canonical or "other" — never crashes."""
    out = normalize_other_room_category(raw)
    assert isinstance(out, str)
    assert len(out) > 0


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — End-to-end orchestrator never crashes on
# pathological input
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=1, n_max=4, max_dim=3.0))
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_adversarial_orchestrator_never_crashes(rooms):
    """Adversarial: any valid SingleFloorPlacementInput either succeeds
    or raises a known PlacementError subclass. Never crashes with
    AssertionError / ZeroDivisionError / unexpected exception."""
    from buildemup.components.c12 import PlacementError

    sf = SingleFloorPlacementInput(
        candidate_signature="rc:fuzz",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=rooms,
        envelope_width_m=10.0, envelope_depth_m=10.0,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(strict_mode=False)  # WARN mode: collect failures
    try:
        result = place_and_align(
            single_floor_inputs=(sf,), multi_floor_inputs=(),
            config=cfg, c11b_env_fingerprint_hash="upstream_fuzz",
        )
        # Either succeeded or recorded a failure — both are valid.
        assert len(result.placed_candidates) + len(result.failures) == 1
    except PlacementError:
        pass  # LocalPlacementError can still propagate in WARN mode


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — High-density adjacency graphs
# ─────────────────────────────────────────────────────────────────────


@given(n=st.integers(min_value=2, max_value=4))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_adversarial_high_density_adjacency_hints(n):
    """Adversarial: adjacency hints for every pair of rooms.

    The orchestrator should not crash; either succeeds with all hints
    satisfied (because every pair shares a wall in a packed grid) or
    raises AdjacencyConstraintViolationError cleanly."""
    rooms = tuple(
        RoomSpec(
            room_id=f"r_{i:02d}", category="bedroom",
            target_width_m=2.0, target_depth_m=2.0,
        )
        for i in range(n)
    )
    # All-pairs HARD adjacency hints (canonical-order each pair)
    hints = []
    for i in range(n):
        for j in range(i + 1, n):
            hints.append((f"r_{i:02d}", f"r_{j:02d}", "hard"))

    sf = SingleFloorPlacementInput(
        candidate_signature="rc:dense",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=rooms,
        envelope_width_m=4.0,  # 2x2 grid → 4 rooms fit
        envelope_depth_m=4.0,
        adjacency_hints=tuple(hints),
    )
    cfg = PlacementConfig(strict_mode=False)
    result = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream_dense",
    )
    # Result is well-formed in either case
    assert len(result.placed_candidates) + len(result.failures) == 1


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — Staircase conflict (vertical core misalignment)
# ─────────────────────────────────────────────────────────────────────


@given(
    offset_x=st.floats(min_value=0.5, max_value=5.0),
    offset_y=st.floats(min_value=0.5, max_value=5.0),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_adversarial_staircase_conflict(offset_x, offset_y):
    """Adversarial: staircase at different positions across floors
    triggers VAV non-convergence cleanly in WARN mode."""
    from buildemup.components.c12 import absorb_multi_floor_placements, PlacedCandidate
    stair_g = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=1.0, y_m=1.0, width_m=2.0, depth_m=2.0,
    )
    stair_f = PlacedRoom(
        room_id="staircase_1", category="staircase",
        x_m=1.0 + offset_x, y_m=1.0 + offset_y,
        width_m=2.0, depth_m=2.0,
    )
    pc_g = PlacedCandidate(
        source_refined_candidate_signature="rc:g",
        placed_rooms=(stair_g,), shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10, envelope_depth_m=10,
    )
    pc_f = PlacedCandidate(
        source_refined_candidate_signature="rc:f",
        placed_rooms=(stair_f,), shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10, envelope_depth_m=10,
    )
    mfc = absorb_multi_floor_placements(
        source_multifloor_signature="mf:conflict",
        per_floor_placements=(("first", pc_f), ("ground", pc_g)),
        feature_room_ids_by_floor={"ground": {"staircase_1"}, "first": {"staircase_1"}},
        vertical_cores_reserved=(),
        tolerance_m=0.02, max_realign_iterations=3,
        strict_mode=False,
    )
    # The misalignment is large; VAV should report non-converged.
    assert not mfc.alignment_report.converged
    assert "staircase_1" in mfc.alignment_report.misaligned_features


# ─────────────────────────────────────────────────────────────────────
# PBT-Adversarial — Replay across multiple environment hashes
# ─────────────────────────────────────────────────────────────────────


@given(
    upstream_hash=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=8, max_size=64,
    ),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_adversarial_env_hash_changes_cache_key(upstream_hash):
    """Adversarial: any unique upstream hash produces a unique cache key
    (no collisions / no degenerate output)."""
    sf = SingleFloorPlacementInput(
        candidate_signature="rc:test",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(
            room_id="r0", category="bedroom",
            target_width_m=2.0, target_depth_m=2.0,
        ),),
        envelope_width_m=4.0, envelope_depth_m=4.0,
        adjacency_hints=(),
    )
    result = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=PlacementConfig(),
        c11b_env_fingerprint_hash=upstream_hash,
    )
    assert len(result.cache_key) == 64
    # Cache key is sensitive to upstream hash
    result2 = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=PlacementConfig(),
        c11b_env_fingerprint_hash=upstream_hash + "_modified",
    )
    assert result.cache_key != result2.cache_key


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-5 — Source signature provenance preservation
# ─────────────────────────────────────────────────────────────────────


@given(
    sig=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=":_"),
        min_size=3, max_size=30,
    ),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_pbt_inv5_source_signature_preserved(sig):
    """Inv 5: PlacedCandidate.source_refined_candidate_signature
    matches the input SingleFloorPlacementInput.candidate_signature."""
    sf = SingleFloorPlacementInput(
        candidate_signature=sig,
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(
            room_id="r0", category="bedroom",
            target_width_m=2.0, target_depth_m=2.0,
        ),),
        envelope_width_m=4.0, envelope_depth_m=4.0,
        adjacency_hints=(),
    )
    result = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=PlacementConfig(),
        c11b_env_fingerprint_hash="upstream_test",
    )
    assert len(result.placed_candidates) == 1
    assert result.placed_candidates[0].source_refined_candidate_signature == sig


# ─────────────────────────────────────────────────────────────────────
# PBT-Inv-6 — Placement algorithm matches config
# ─────────────────────────────────────────────────────────────────────


@given(rooms=_unique_room_set_strategy(n_min=1, n_max=3, max_dim=3.0))
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pbt_inv6_placement_algorithm_recorded(rooms):
    """Inv 6: PlacedCandidate.placement_algorithm == config's choice.
    v1 ships slicing_kd_tree only (per v0.3-A1)."""
    sf = SingleFloorPlacementInput(
        candidate_signature="rc:test",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=rooms,
        envelope_width_m=10.0, envelope_depth_m=10.0,
        adjacency_hints=(),
    )
    try:
        result = place_and_align(
            single_floor_inputs=(sf,), multi_floor_inputs=(),
            config=PlacementConfig(),
            c11b_env_fingerprint_hash="upstream_test",
        )
    except GeometricInfeasibilityError:
        return
    for pc in result.placed_candidates:
        assert pc.placement_algorithm == "slicing_kd_tree"
