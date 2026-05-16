"""Tests for severity context computation (Phase β step 4.2).

Spec § 3 Phase β step 4.2 — per-instance severity via 6 context factors.
"""
from __future__ import annotations

import pytest

from buildemup.components.c03b.phases.severity import (
    SeverityContext,
    detect_bay_boundary_crossing,
    detect_circulation_graph_impact,
    detect_external_wall_change,
    detect_load_bearing_proximity,
    detect_wet_zone_interaction,
    predict_topology_invariance,
    promote_severity,
)

from .fixtures import (
    make_door_placement,
    make_placed_room,
    make_riser,
    make_riser_group,
    make_structural_grid,
    make_structural_grid_cell,
    make_room_geometry,
)


# ============================================================
# SeverityContext basics
# ============================================================

def test_severity_context_factor_count_excludes_topology():
    """Topology short-circuits to HEAVY directly — not in factor count."""
    ctx = SeverityContext(
        load_bearing_wall_involvement=True,
        topology_classification_change=True,
    )
    assert ctx.factor_count == 1   # only load_bearing counted; topology short-circuits


def test_severity_context_factor_count_default_zero():
    assert SeverityContext().factor_count == 0


def test_factor_names_triggered():
    ctx = SeverityContext(
        load_bearing_wall_involvement=True,
        wet_zone_stack_interaction=True,
    )
    names = ctx.factor_names_triggered()
    assert "load_bearing_wall_involvement" in names
    assert "wet_zone_stack_interaction" in names


# ============================================================
# promote_severity
# ============================================================

def test_promote_topology_change_always_heavy():
    ctx = SeverityContext(topology_classification_change=True)
    assert promote_severity(default_severity="light", context=ctx) == "heavy"


def test_promote_light_with_zero_factors_stays_light():
    ctx = SeverityContext()
    assert promote_severity(default_severity="light", context=ctx) == "light"


def test_promote_light_with_one_factor_to_medium():
    ctx = SeverityContext(circulation_graph_impact=True)
    assert promote_severity(default_severity="light", context=ctx) == "medium"


def test_promote_medium_with_zero_factors_stays_medium():
    ctx = SeverityContext()
    assert promote_severity(default_severity="medium", context=ctx) == "medium"


def test_promote_medium_with_one_factor_stays_medium():
    ctx = SeverityContext(circulation_graph_impact=True)
    assert promote_severity(default_severity="medium", context=ctx) == "medium"


def test_promote_medium_with_two_factors_becomes_heavy():
    ctx = SeverityContext(
        circulation_graph_impact=True, wet_zone_stack_interaction=True,
    )
    assert promote_severity(default_severity="medium", context=ctx) == "heavy"


def test_promote_heavy_default_stays_heavy():
    ctx = SeverityContext()
    assert promote_severity(default_severity="heavy", context=ctx) == "heavy"


# ============================================================
# Context detection — load-bearing proximity
# ============================================================

def test_load_bearing_returns_false_when_no_load_bearing_cells():
    rooms = (
        make_placed_room("r1", structural_bay_ids=("cell_001",)),
    )
    grid = make_structural_grid(
        cells=(make_structural_grid_cell(cell_id="cell_001", is_load_bearing_perimeter=False),),
    )
    assert detect_load_bearing_proximity(
        affected_room_ids=("r1",),
        placed_rooms=rooms,
        structural_grid=grid,
    ) is False


def test_load_bearing_returns_true_when_room_on_lb_cell():
    rooms = (
        make_placed_room("r1", structural_bay_ids=("cell_001",)),
    )
    grid = make_structural_grid(
        cells=(make_structural_grid_cell(cell_id="cell_001", is_load_bearing_perimeter=True),),
    )
    assert detect_load_bearing_proximity(
        affected_room_ids=("r1",),
        placed_rooms=rooms,
        structural_grid=grid,
    ) is True


def test_load_bearing_returns_false_when_empty_affected():
    grid = make_structural_grid()
    assert detect_load_bearing_proximity(
        affected_room_ids=(),
        placed_rooms=(),
        structural_grid=grid,
    ) is False


# ============================================================
# Context detection — bay boundary crossing
# ============================================================

def test_bay_boundary_crossing_false_single_bay():
    rooms = (
        make_placed_room("r1", structural_bay_ids=("bay_001",)),
    )
    assert detect_bay_boundary_crossing(
        affected_room_ids=("r1",), placed_rooms=rooms,
    ) is False


def test_bay_boundary_crossing_true_two_bays():
    rooms = (
        make_placed_room("r1", structural_bay_ids=("bay_001", "bay_002")),
    )
    assert detect_bay_boundary_crossing(
        affected_room_ids=("r1",), placed_rooms=rooms,
    ) is True


# ============================================================
# Context detection — wet-zone interaction
# ============================================================

def test_wet_zone_interaction_direct_room_in_riser_group():
    rooms = (make_placed_room("bath_001"),)
    rg = (make_riser_group(served_room_ids=("bath_001",)),)
    assert detect_wet_zone_interaction(
        affected_room_ids=("bath_001",), placed_rooms=rooms, riser_groups=rg,
    ) is True


def test_wet_zone_interaction_indirect_via_adjacency():
    rooms = (
        make_placed_room("bedroom_001", adjacent_room_ids=("bath_001",)),
        make_placed_room("bath_001"),
    )
    rg = (make_riser_group(served_room_ids=("bath_001",)),)
    assert detect_wet_zone_interaction(
        affected_room_ids=("bedroom_001",), placed_rooms=rooms, riser_groups=rg,
    ) is True


def test_wet_zone_interaction_unrelated_room_false():
    rooms = (make_placed_room("living_001"),)
    rg = (make_riser_group(served_room_ids=("bath_001",)),)
    assert detect_wet_zone_interaction(
        affected_room_ids=("living_001",), placed_rooms=rooms, riser_groups=rg,
    ) is False


# ============================================================
# Context detection — external wall change
# ============================================================

def test_external_wall_change_balcony_add_always_true():
    """balcony_add intrinsically touches envelope."""
    assert detect_external_wall_change(
        affected_room_ids=("r1",),
        placed_rooms=(make_placed_room("r1", has_external_wall=False),),
        tweak_category="balcony_add",
    ) is True


def test_external_wall_change_window_resize_always_true():
    assert detect_external_wall_change(
        affected_room_ids=(),
        placed_rooms=(),
        tweak_category="window_resize",
    ) is True


def test_external_wall_change_other_categories_depend_on_room():
    """Non-envelope categories: true only if affected room has external wall."""
    rooms_ext = (make_placed_room("r1", has_external_wall=True),)
    rooms_int = (make_placed_room("r1", has_external_wall=False),)
    assert detect_external_wall_change(
        affected_room_ids=("r1",), placed_rooms=rooms_ext,
        tweak_category="room_swap",
    ) is True
    assert detect_external_wall_change(
        affected_room_ids=("r1",), placed_rooms=rooms_int,
        tweak_category="room_swap",
    ) is False


# ============================================================
# Context detection — circulation graph
# ============================================================

def test_circulation_door_relocate_always_true():
    assert detect_circulation_graph_impact(
        tweak_category="door_relocate", affected_room_ids=(),
        placed_rooms=(), door_placements=(),
    ) is True


def test_circulation_room_swap_always_true():
    assert detect_circulation_graph_impact(
        tweak_category="room_swap", affected_room_ids=(),
        placed_rooms=(), door_placements=(),
    ) is True


def test_circulation_finish_upgrade_false():
    assert detect_circulation_graph_impact(
        tweak_category="finish_upgrade", affected_room_ids=("r1",),
        placed_rooms=(), door_placements=(),
    ) is False


# ============================================================
# Topology invariance prediction (R13)
# ============================================================

def test_topology_invariance_safe_for_finish_tweaks():
    res = predict_topology_invariance(
        tweak_category="finish_upgrade",
        source_topology="central_spine",
        affected_room_ids=(),
        placed_rooms=(),
    )
    assert res.invariance_preserved is True
    assert res.prediction_basis == "mutation_local_only"


def test_topology_invariance_safe_for_window_resize():
    res = predict_topology_invariance(
        tweak_category="window_resize",
        source_topology="strip",
        affected_room_ids=("r1",),
        placed_rooms=(make_placed_room("r1"),),
    )
    assert res.invariance_preserved is True


def test_topology_invariance_flags_corridor_touch_as_heavy():
    """Touching a corridor → topology may change → invariance False."""
    rooms = (
        make_placed_room("corridor_001", room_function="corridor"),
    )
    res = predict_topology_invariance(
        tweak_category="utility_zone_carveout",
        source_topology="central_spine",
        affected_room_ids=("corridor_001",),
        placed_rooms=rooms,
    )
    assert res.invariance_preserved is False
