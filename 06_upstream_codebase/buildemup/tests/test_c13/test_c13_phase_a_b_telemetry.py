"""Tests for C13 v1.0 LOCKED Phase A + Phase B + telemetry (S45 Sub-2).

Covers:
- Telemetry event types (frozen, hash-stable, sink protocol
  conformance, NullTelemetrySink + InMemoryTelemetrySink behavior)
- Phase A (edge_selection.select_edges):
    - Tier 1 main-entry selection (EXTERNAL_ENVELOPE preference,
      NBC D11.1/D11.4 filtering, lex-ASC tie-break)
    - Tier 2 corridor-adjacent (max overlap_length_m, lex-ASC
      tie-break)
    - Tier 3 lex-ASC fallback (NBC vetoes for master bedroom)
    - Secondary door selection (preference filter, eligible categories
      only, forbid_edges)
    - Determinism (Inv D7): same input → byte-equal output
    - Error paths: EntryRoomNotFoundError, DoorPositionInfeasibleError
    - Result schema invariants (sort, main_entry_room_id presence)
- Phase B (swing_assignment.assign_swings):
    - Main-entry-into-building rule (Rule 1)
    - Bathroom inswing default (Rule 2, area >= threshold)
    - Bathroom outswing compact (Rule 2, area < threshold) +
      EMERGENCY advisory emission
    - Smaller-room inswing (Rule 3)
    - Lex-ASC fallback for equal areas (Rule 4 — Inv D7 determinism)
    - Hinge side default 'start' (v0.2 A3)
    - Result schema canonical sorting

Invariants exercised:
- D7 (byte-equal replay): determinism PBTs in both modules
- D8 (canonical sorting): EdgeSelectionResult + SwingAssignmentResult
  __post_init__
- D9' (bathroom outswing advisory hygiene): emission verified
- D11.1 (no bathroom-kitchen doors): edge filter exercised
- D11.4 (master bedroom no kitchen/bathroom main): edge filter
  exercised
- D14 (geometric fidelity): preserved by Phase B (hinge='start',
  swing decided)
- D16 (advisory density bounded): single-bathroom outswing emits
  exactly one EMERGENCY flag with category-deduplicated key
"""
from __future__ import annotations

import pytest

from buildemup.components.c13 import (
    AdvisoryCategory,
    AdvisoryFlagEmittedEvent,
    C12V10EdgeAdapter,
    DoorPlacementConfig,
    DoorPositionInfeasibleError,
    EdgeAssignment,
    EdgeSelectionEvent,
    EdgeSelectionResult,
    EdgeType,
    EntryRoomNotFoundError,
    InMemoryTelemetrySink,
    NullTelemetrySink,
    PhaseDConvergenceEvent,
    RoomDoorPreference,
    SwingAssignment,
    SwingAssignmentResult,
    SwingDirectionEvent,
    assign_swings,
    select_edges,
)


# ──────────────────────────────────────────────────────────────────────
# Helpers — build minimal SharedEdge fixtures via real C12 v1.0 schema
# ──────────────────────────────────────────────────────────────────────


def _se(
    a: str, b: str,
    *,
    axis: str = "vertical",
    overlap: float = 2.0,
    min_clear: float = 0.9,
    feasible: bool = True,
):
    """Build a C12 v1.0 SharedEdge wrapped in C12V10EdgeAdapter so it
    satisfies the C13ConsumesFromC12Edge Protocol.

    Args 'a' and 'b' are the two room ids; the adapter handles the
    EXTERNAL sentinel for edge_type derivation.
    """
    from buildemup.components.c12 import SharedEdge
    # C12 canonical-order invariant: room_a_id < room_b_id lex-ASC.
    if a >= b:
        raise AssertionError(
            f"Fixture error: rooms must be lex-ASC; got {a!r}, {b!r}."
        )
    raw = SharedEdge(
        room_a_id=a,
        room_b_id=b,
        axis=axis,  # type: ignore[arg-type]
        overlap_start_m=0.0,
        overlap_end_m=overlap,
        overlap_length_m=overlap,
        min_required_clear_width_m=min_clear,
        doorway_feasible=feasible,
    )
    return C12V10EdgeAdapter(raw)


# ──────────────────────────────────────────────────────────────────────
# Telemetry: event types + sinks
# ──────────────────────────────────────────────────────────────────────


def test_edge_selection_event_is_frozen_and_hashable():
    e1 = EdgeSelectionEvent(
        candidate_signature="c1",
        room_id="bedroom_01",
        selected_edge_room_a_id="bedroom_01",
        selected_edge_room_b_id="corridor_01",
        selection_tier="lex_asc",
        feasible_edge_count=1,
        is_secondary=False,
    )
    e2 = EdgeSelectionEvent(
        candidate_signature="c1",
        room_id="bedroom_01",
        selected_edge_room_a_id="bedroom_01",
        selected_edge_room_b_id="corridor_01",
        selection_tier="lex_asc",
        feasible_edge_count=1,
        is_secondary=False,
    )
    assert e1 == e2
    assert hash(e1) == hash(e2)
    with pytest.raises(Exception):  # FrozenInstanceError
        e1.candidate_signature = "c2"  # type: ignore[misc]


def test_phase_d_convergence_event_full_fields():
    e = PhaseDConvergenceEvent(
        candidate_signature="c1",
        iterations_used=2,
        max_iterations=5,
        conflicts_at_start=3,
        conflicts_at_end=0,
        rollbacks_count=1,
        branching_factor=5,
        convergence_quality_proxy=0.075,
        visited_state_hit=False,
    )
    assert e.iterations_used == 2
    assert e.convergence_quality_proxy == 0.075


def test_null_telemetry_sink_emits_silently():
    sink = NullTelemetrySink()
    sink.emit(EdgeSelectionEvent(
        candidate_signature="c1",
        room_id="r1",
        selected_edge_room_a_id="a",
        selected_edge_room_b_id="b",
        selection_tier="entry",
        feasible_edge_count=1,
        is_secondary=False,
    ))
    # No exception, no state.


def test_in_memory_telemetry_sink_retains_events():
    sink = InMemoryTelemetrySink()
    e1 = EdgeSelectionEvent(
        candidate_signature="c1",
        room_id="r1",
        selected_edge_room_a_id="a",
        selected_edge_room_b_id="b",
        selection_tier="entry",
        feasible_edge_count=1,
        is_secondary=False,
    )
    e2 = SwingDirectionEvent(
        candidate_signature="c1",
        room_a_id="a",
        room_b_id="b",
        swing_direction="into_room_a",
        decision_rule="main_entry_into_building",
    )
    sink.emit(e1)
    sink.emit(e2)
    assert sink.events == (e1, e2)
    assert sink.events_of_type(EdgeSelectionEvent) == (e1,)
    assert sink.events_of_type(SwingDirectionEvent) == (e2,)
    sink.clear()
    assert sink.events == ()


# ──────────────────────────────────────────────────────────────────────
# Phase A: EdgeSelectionResult schema invariants
# ──────────────────────────────────────────────────────────────────────


def test_edge_selection_result_sort_order_enforced():
    e1 = _se("aaa", "corridor_01")
    e2 = _se("bbb", "corridor_01")
    a1 = EdgeAssignment(room_id="aaa", edge=e1, is_secondary=False)
    a2 = EdgeAssignment(room_id="bbb", edge=e2, is_secondary=False)
    # Wrong order → rejected.
    with pytest.raises(ValueError, match="must be sorted"):
        EdgeSelectionResult(assignments=(a2, a1), main_entry_room_id="aaa")
    # Correct order works.
    r = EdgeSelectionResult(assignments=(a1, a2), main_entry_room_id="aaa")
    assert r.main_entry_room_id == "aaa"


def test_edge_selection_result_main_entry_must_have_primary():
    e1 = _se("aaa", "corridor_01")
    a1 = EdgeAssignment(room_id="aaa", edge=e1, is_secondary=True)
    # main entry must have a PRIMARY assignment (not just secondary).
    with pytest.raises(ValueError, match="primary assignment"):
        EdgeSelectionResult(assignments=(a1,), main_entry_room_id="aaa")


# ──────────────────────────────────────────────────────────────────────
# Phase A: Tier 1 main-entry selection
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_entry_room_not_found_raises():
    edges = (_se("aaa", "corridor_01"),)
    with pytest.raises(EntryRoomNotFoundError):
        select_edges(
            candidate_signature="c1",
            placed_room_ids=("aaa", "corridor_01"),
            room_categories={"aaa": "living", "corridor_01": "corridor"},
            shared_edges=edges,
            entry_room_id="ghost_room",
            room_door_preferences={},
        )


def test_phase_a_entry_picks_external_envelope_when_available():
    # Entry room "AAA_entry" has both an internal edge and an external
    # edge. Should prefer external.
    e_internal = _se("AAA_entry", "corridor_01")
    e_external = _se("AAA_entry", "EXTERNAL")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "corridor_01"),
        room_categories={
            "AAA_entry": "main_entrance", "corridor_01": "corridor",
        },
        shared_edges=(e_external, e_internal),  # lex order: EXTERNAL first
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    entry_assign = [a for a in result.assignments if a.room_id == "AAA_entry"][0]
    assert entry_assign.edge.edge_type == EdgeType.EXTERNAL_ENVELOPE


def test_phase_a_entry_falls_back_when_no_external_edge():
    e_internal = _se("AAA_entry", "corridor_01")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "corridor_01"),
        room_categories={
            "AAA_entry": "main_entrance", "corridor_01": "corridor",
        },
        shared_edges=(e_internal,),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    entry_assign = [a for a in result.assignments if a.room_id == "AAA_entry"][0]
    assert entry_assign.edge.edge_type == EdgeType.INTERNAL


def test_phase_a_emits_entry_tier_telemetry():
    sink = InMemoryTelemetrySink()
    e = _se("AAA_entry", "EXTERNAL")
    select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry",),
        room_categories={"AAA_entry": "main_entrance"},
        shared_edges=(e,),
        entry_room_id="AAA_entry",
        room_door_preferences={},
        telemetry_sink=sink,
    )
    entry_events = sink.events_of_type(EdgeSelectionEvent)
    assert len(entry_events) == 1
    assert entry_events[0].selection_tier == "entry"


# ──────────────────────────────────────────────────────────────────────
# Phase A: Tier 2 corridor-adjacent
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_tier_2_picks_max_overlap_corridor_edge():
    # bedroom_01 has two corridor edges; should pick the longer one.
    e_short = _se("bedroom_01", "corridor_01", overlap=1.5)
    e_long = _se("bedroom_01", "corridor_02", overlap=3.0)
    e_entry = _se("AAA_entry", "EXTERNAL")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "bedroom_01", "corridor_01", "corridor_02"),
        room_categories={
            "AAA_entry": "main_entrance",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
            "corridor_02": "corridor",
        },
        shared_edges=(e_entry, e_short, e_long),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    bedroom_assign = [
        a for a in result.assignments if a.room_id == "bedroom_01"
    ][0]
    # Tier 2 should fire (bedroom is corridor-adjacent) and pick the
    # longer overlap edge (corridor_02).
    assert bedroom_assign.edge.room_b_id == "corridor_02"


def test_phase_a_tier_2_lex_asc_tie_break_on_equal_overlap():
    # Equal overlap → lex-ASC tie-break on (room_a_id, room_b_id).
    e_a = _se("bedroom_01", "corridor_01", overlap=2.0)
    e_b = _se("bedroom_01", "corridor_02", overlap=2.0)
    e_entry = _se("AAA_entry", "EXTERNAL")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "bedroom_01", "corridor_01", "corridor_02"),
        room_categories={
            "AAA_entry": "main_entrance",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
            "corridor_02": "corridor",
        },
        shared_edges=(e_entry, e_a, e_b),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    bedroom_assign = [
        a for a in result.assignments if a.room_id == "bedroom_01"
    ][0]
    # ("bedroom_01", "corridor_01") < ("bedroom_01", "corridor_02").
    assert bedroom_assign.edge.room_b_id == "corridor_01"


# ──────────────────────────────────────────────────────────────────────
# Phase A: Tier 3 lex-ASC fallback
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_tier_3_lex_asc_when_no_corridor_adjacency():
    # bedroom_02 has no corridor edge; must fall to Tier 3.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_inter = _se("bedroom_01", "bedroom_02", overlap=2.0)
    e_corr = _se("bedroom_01", "corridor_01", overlap=2.0)
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "bedroom_01", "bedroom_02", "corridor_01"),
        room_categories={
            "AAA_entry": "main_entrance",
            "bedroom_01": "bedroom",
            "bedroom_02": "bedroom",
            "corridor_01": "corridor",
        },
        shared_edges=(e_entry, e_inter, e_corr),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    bedroom_02_assign = [
        a for a in result.assignments if a.room_id == "bedroom_02"
    ][0]
    # bedroom_02 has only one feasible edge (to bedroom_01). The
    # corr edge is forbid'd by being bedroom_01's primary (Tier 2 fired
    # first); so Tier 3 picks bedroom_01-bedroom_02.
    assert bedroom_02_assign.edge.room_a_id == "bedroom_01"
    assert bedroom_02_assign.edge.room_b_id == "bedroom_02"


def test_phase_a_raises_when_room_has_no_feasible_edge():
    # bedroom_02 has only an infeasible edge.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_inf = _se("bedroom_01", "bedroom_02", feasible=False)
    with pytest.raises(DoorPositionInfeasibleError):
        select_edges(
            candidate_signature="c1",
            placed_room_ids=("AAA_entry", "bedroom_01", "bedroom_02"),
            room_categories={
                "AAA_entry": "main_entrance",
                "bedroom_01": "bedroom",
                "bedroom_02": "bedroom",
            },
            shared_edges=(e_entry, e_inf),
            entry_room_id="AAA_entry",
            room_door_preferences={},
        )


# ──────────────────────────────────────────────────────────────────────
# Phase A: NBC vetoes D11.1 (bathroom-kitchen) + D11.4 (master bedroom)
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_d11_1_filters_bathroom_kitchen_edge():
    # bathroom_01 has only one edge — directly to kitchen_01. Phase A
    # filters it, leaving no feasible edge → DoorPositionInfeasibleError.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bath_kitchen = _se("bathroom_01", "kitchen_01")
    e_kitchen_entry = _se("AAA_entry", "kitchen_01")
    with pytest.raises(DoorPositionInfeasibleError):
        select_edges(
            candidate_signature="c1",
            placed_room_ids=("AAA_entry", "bathroom_01", "kitchen_01"),
            room_categories={
                "AAA_entry": "main_entrance",
                "bathroom_01": "bathroom",
                "kitchen_01": "kitchen",
            },
            shared_edges=(e_entry, e_bath_kitchen, e_kitchen_entry),
            entry_room_id="AAA_entry",
            room_door_preferences={},
        )


def test_phase_a_d11_1_allows_bathroom_when_alternate_exists():
    # bathroom_01 has two edges: one to kitchen (filtered by D11.1)
    # and one to corridor (kept). Phase A picks the corridor edge.
    # kitchen also has an edge to corridor so it isn't isolated by
    # the D11.1 filter.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_entry_corr = _se("AAA_entry", "corridor_01")
    e_bath_kitchen = _se("bathroom_01", "kitchen_01")  # D11.1 → filtered
    e_bath_corr = _se("bathroom_01", "corridor_01")
    e_kit_corr = _se("corridor_01", "kitchen_01")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "bathroom_01", "corridor_01", "kitchen_01"),
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "corridor_01": "corridor",
            "kitchen_01": "kitchen",
        },
        shared_edges=(
            e_entry, e_entry_corr, e_bath_kitchen, e_bath_corr, e_kit_corr,
        ),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    # Find the assignment that is "for" bathroom_01 (the assignment
    # carrying bathroom_01 as its responsible-room).
    bath_chosen_edges = [
        (a.edge.room_a_id, a.edge.room_b_id)
        for a in result.assignments
        if a.room_id == "bathroom_01"
    ]
    # D11.1 filtered the bathroom-kitchen edge; the bathroom-corridor
    # edge is picked instead.
    assert bath_chosen_edges == [("bathroom_01", "corridor_01")]
    # Crucially, NO assignment uses the bathroom-kitchen edge (D11.1).
    all_chosen = {
        (a.edge.room_a_id, a.edge.room_b_id) for a in result.assignments
    }
    assert ("bathroom_01", "kitchen_01") not in all_chosen


# ──────────────────────────────────────────────────────────────────────
# Phase A: secondary doors (per v0.3 B8 + v0.4 C4)
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_secondary_door_for_eligible_category():
    """Per v0.4 C4 secondary door support.

    Door-centric model note (clarified in Sub-2 self-analysis): a
    SharedEdge admits at most one door, which serves BOTH rooms on
    that edge. So a room may end up with N "doors" total because N
    edges touch it — counting doors-per-room means counting touching
    edges across the chosen-edge set, NOT counting EdgeAssignments
    whose `room_id` (= responsible-room provenance) equals the target.

    This test exercises the secondary-preference path: kitchen
    requests max_doors=2 with 'utility' preference. The first
    kitchen-touching edge is picked as kitchen's primary (corridor
    edge per Tier 2 rule). The utility-kitchen edge must then be
    added as a NEW chosen edge (kitchen's secondary) because no
    other room reaches it (utility's own primary is
    utility-corridor, available via a separate utility-corridor
    edge).
    """
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_entry_corr = _se("AAA_entry", "corridor_01")
    e_kit_corr = _se("corridor_01", "kitchen_01")
    e_kit_util = _se("kitchen_01", "utility_01")
    e_util_corr = _se("corridor_01", "utility_01")  # gives utility its own primary
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=(
            "AAA_entry", "corridor_01", "kitchen_01", "utility_01",
        ),
        room_categories={
            "AAA_entry": "main_entrance",
            "corridor_01": "corridor",
            "kitchen_01": "kitchen",
            "utility_01": "utility",
        },
        shared_edges=(e_entry, e_entry_corr, e_kit_corr, e_kit_util, e_util_corr),
        entry_room_id="AAA_entry",
        room_door_preferences={
            "kitchen_01": RoomDoorPreference(
                room_id="kitchen_01",
                min_doors=2,
                max_doors=2,
                secondary_door_preference="utility",
            ),
        },
    )
    # All chosen edges:
    chosen = {
        (a.edge.room_a_id, a.edge.room_b_id) for a in result.assignments
    }
    # Kitchen should be touched by two chosen edges: corridor-kitchen
    # (primary, picked as kitchen's first responsibility) AND
    # kitchen-utility (secondary, picked via preference filter).
    kitchen_touching = {
        e for e in chosen if "kitchen_01" in e
    }
    assert len(kitchen_touching) == 2
    assert ("corridor_01", "kitchen_01") in chosen  # kitchen's primary
    assert ("kitchen_01", "utility_01") in chosen  # kitchen's secondary
    # The kitchen-utility edge MUST be tagged is_secondary=True under
    # kitchen's responsibility (the secondary-door selection loop).
    kitchen_secondary = [
        a for a in result.assignments
        if a.room_id == "kitchen_01" and a.is_secondary
    ]
    assert len(kitchen_secondary) == 1
    assert kitchen_secondary[0].edge.room_a_id == "kitchen_01"
    assert kitchen_secondary[0].edge.room_b_id == "utility_01"


def test_phase_a_secondary_door_skipped_for_ineligible_category():
    # Bedroom requests 2 doors but bedrooms are NOT eligible
    # (per SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1). Should skip secondary.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bed_corr = _se("bedroom_01", "corridor_01")
    e_bed_bath = _se("bathroom_01", "bedroom_01")
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=(
            "AAA_entry", "bathroom_01", "bedroom_01", "corridor_01",
        ),
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
        },
        shared_edges=(e_entry, e_bed_corr, e_bed_bath),
        entry_room_id="AAA_entry",
        room_door_preferences={
            "bedroom_01": RoomDoorPreference(
                room_id="bedroom_01", max_doors=2,
            ),
        },
    )
    bedroom_assignments = [
        a for a in result.assignments if a.room_id == "bedroom_01"
    ]
    # Only primary; no secondary even though preference requested 2.
    assert len(bedroom_assignments) == 1
    assert not bedroom_assignments[0].is_secondary


# ──────────────────────────────────────────────────────────────────────
# Phase A: Determinism (Inv D7)
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_is_deterministic():
    # Inv D7: same inputs → byte-equal result.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bed_corr = _se("bedroom_01", "corridor_01")
    e_bath_corr = _se("bathroom_01", "corridor_01")
    args = dict(
        candidate_signature="c1",
        placed_room_ids=(
            "AAA_entry", "bathroom_01", "bedroom_01", "corridor_01",
        ),
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
        },
        shared_edges=(e_entry, e_bath_corr, e_bed_corr),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    r1 = select_edges(**args)
    r2 = select_edges(**args)
    # Same assignments + same main entry.
    assert r1.main_entry_room_id == r2.main_entry_room_id
    keys_1 = [(a.room_id, a.edge.room_a_id, a.edge.room_b_id) for a in r1.assignments]
    keys_2 = [(a.room_id, a.edge.room_a_id, a.edge.room_b_id) for a in r2.assignments]
    assert keys_1 == keys_2


# ──────────────────────────────────────────────────────────────────────
# Phase B: SwingAssignmentResult schema invariants
# ──────────────────────────────────────────────────────────────────────


def test_swing_assignment_result_sort_order_enforced():
    s1 = SwingAssignment(
        room_a_id="aaa", room_b_id="corridor_01",
        swing_direction="into_room_a", hinge_side="start",
        is_secondary=False, decision_rule="smaller_room_inswing",
    )
    s2 = SwingAssignment(
        room_a_id="bbb", room_b_id="corridor_01",
        swing_direction="into_room_a", hinge_side="start",
        is_secondary=False, decision_rule="smaller_room_inswing",
    )
    with pytest.raises(ValueError, match="must be sorted"):
        SwingAssignmentResult(assignments=(s2, s1), advisory_flags=())


# ──────────────────────────────────────────────────────────────────────
# Phase B: Rule 1 — main entry into building
# ──────────────────────────────────────────────────────────────────────


def test_phase_b_main_entry_swings_into_building():
    # Main entry edge has EXTERNAL as room_b_id (the adapter sentinel
    # convention). Door should swing into room_a (the building side).
    e_entry = _se("AAA_entry", "EXTERNAL")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(
                room_id="AAA_entry", edge=e_entry, is_secondary=False,
            ),
        ),
        main_entry_room_id="AAA_entry",
    )
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={"AAA_entry": "main_entrance"},
        room_areas={"AAA_entry": 8.0},
        bathroom_outswing_area_threshold_m2=4.0,
    )
    s = swing_result.assignments[0]
    assert s.decision_rule == "main_entry_into_building"
    assert s.swing_direction == "into_room_a"
    assert s.hinge_side == "start"
    assert swing_result.advisory_flags == ()


# ──────────────────────────────────────────────────────────────────────
# Phase B: Rule 2 — bathroom inswing default (area >= threshold)
# ──────────────────────────────────────────────────────────────────────


def test_phase_b_bathroom_inswing_when_area_above_threshold():
    # Bathroom area 5 m² >= 4 m² threshold → inswing.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bath = _se("bathroom_01", "corridor_01")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(room_id="AAA_entry", edge=e_entry, is_secondary=False),
            EdgeAssignment(room_id="bathroom_01", edge=e_bath, is_secondary=False),
        ),
        main_entry_room_id="AAA_entry",
    )
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "corridor_01": "corridor",
        },
        room_areas={"bathroom_01": 5.0, "corridor_01": 6.0},
        bathroom_outswing_area_threshold_m2=4.0,
    )
    bath_swing = [
        s for s in swing_result.assignments
        if s.room_a_id == "bathroom_01"
    ][0]
    assert bath_swing.decision_rule == "bathroom_inswing_default"
    # bathroom_01 is room_a → swing into_room_a.
    assert bath_swing.swing_direction == "into_room_a"
    # No advisory for inswing.
    assert all(
        f.flag_kind != "bathroom_outswing_emergency_clearance"
        for f in swing_result.advisory_flags
    )


def test_phase_b_bathroom_outswing_when_area_below_threshold():
    # Bathroom area 3 m² < 4 m² → outswing + EMERGENCY advisory.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bath = _se("bathroom_01", "corridor_01")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(room_id="AAA_entry", edge=e_entry, is_secondary=False),
            EdgeAssignment(room_id="bathroom_01", edge=e_bath, is_secondary=False),
        ),
        main_entry_room_id="AAA_entry",
    )
    sink = InMemoryTelemetrySink()
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "corridor_01": "corridor",
        },
        room_areas={"bathroom_01": 3.0, "corridor_01": 6.0},
        bathroom_outswing_area_threshold_m2=4.0,
        telemetry_sink=sink,
    )
    bath_swing = [
        s for s in swing_result.assignments
        if s.room_a_id == "bathroom_01"
    ][0]
    assert bath_swing.decision_rule == "bathroom_outswing_compact"
    # bathroom_01 is room_a → outswing → into_room_b.
    assert bath_swing.swing_direction == "into_room_b"
    # Advisory emitted.
    emergency_flags = [
        f for f in swing_result.advisory_flags
        if f.flag_kind == "bathroom_outswing_emergency_clearance"
    ]
    assert len(emergency_flags) == 1
    assert emergency_flags[0].category == AdvisoryCategory.EMERGENCY
    assert emergency_flags[0].severity == "concern"
    assert emergency_flags[0].affected_room_id == "bathroom_01"
    # Telemetry sink saw the advisory event.
    advisory_events = sink.events_of_type(AdvisoryFlagEmittedEvent)
    assert len(advisory_events) == 1
    assert advisory_events[0].flag_kind == "bathroom_outswing_emergency_clearance"


# ──────────────────────────────────────────────────────────────────────
# Phase B: Rule 3/4 — smaller-room inswing + lex tie-break
# ──────────────────────────────────────────────────────────────────────


def test_phase_b_smaller_room_inswing():
    # bedroom_01 (10 m²) - bedroom_02 (8 m²). Door swings into bedroom_02
    # (smaller). bedroom_02 is room_b → swing_direction = into_room_b.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_inter = _se("bedroom_01", "bedroom_02")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(room_id="AAA_entry", edge=e_entry, is_secondary=False),
            EdgeAssignment(room_id="bedroom_02", edge=e_inter, is_secondary=False),
        ),
        main_entry_room_id="AAA_entry",
    )
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bedroom_01": "bedroom",
            "bedroom_02": "bedroom",
        },
        room_areas={"bedroom_01": 10.0, "bedroom_02": 8.0},
        bathroom_outswing_area_threshold_m2=4.0,
    )
    inter_swing = [
        s for s in swing_result.assignments
        if s.room_a_id == "bedroom_01" and s.room_b_id == "bedroom_02"
    ][0]
    assert inter_swing.decision_rule == "smaller_room_inswing"
    assert inter_swing.swing_direction == "into_room_b"


def test_phase_b_lex_tie_break_when_areas_equal():
    # bedroom_01 (10 m²) = bedroom_02 (10 m²). Tie-break: lex-ASC
    # room_a wins INSWING → into_room_a.
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_inter = _se("bedroom_01", "bedroom_02")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(room_id="AAA_entry", edge=e_entry, is_secondary=False),
            EdgeAssignment(room_id="bedroom_02", edge=e_inter, is_secondary=False),
        ),
        main_entry_room_id="AAA_entry",
    )
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bedroom_01": "bedroom",
            "bedroom_02": "bedroom",
        },
        room_areas={"bedroom_01": 10.0, "bedroom_02": 10.0},
        bathroom_outswing_area_threshold_m2=4.0,
    )
    inter_swing = [
        s for s in swing_result.assignments
        if s.room_a_id == "bedroom_01" and s.room_b_id == "bedroom_02"
    ][0]
    assert inter_swing.decision_rule == "fallback_lex_asc"
    assert inter_swing.swing_direction == "into_room_a"


# ──────────────────────────────────────────────────────────────────────
# Phase B: determinism (Inv D7)
# ──────────────────────────────────────────────────────────────────────


def test_phase_b_is_deterministic():
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_bath = _se("bathroom_01", "corridor_01")
    e_inter = _se("bedroom_01", "bedroom_02")
    edge_result = EdgeSelectionResult(
        assignments=(
            EdgeAssignment(room_id="AAA_entry", edge=e_entry, is_secondary=False),
            EdgeAssignment(room_id="bathroom_01", edge=e_bath, is_secondary=False),
            EdgeAssignment(room_id="bedroom_02", edge=e_inter, is_secondary=False),
        ),
        main_entry_room_id="AAA_entry",
    )
    kwargs = dict(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "bedroom_01": "bedroom",
            "bedroom_02": "bedroom",
            "corridor_01": "corridor",
        },
        room_areas={
            "bathroom_01": 3.0, "bedroom_01": 10.0, "bedroom_02": 8.0,
            "corridor_01": 6.0,
        },
        bathroom_outswing_area_threshold_m2=4.0,
    )
    r1 = assign_swings(**kwargs)
    r2 = assign_swings(**kwargs)
    assert r1 == r2
    assert hash(r1) == hash(r2)


# ──────────────────────────────────────────────────────────────────────
# Phase B + Phase A integration smoke
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_then_phase_b_smoke():
    """Smoke test: real pipeline through Phase A then Phase B for a
    small synthetic layout. Verifies the modules wire together
    correctly (Pattern B counter: building-with-wiring)."""
    e_entry = _se("AAA_entry", "EXTERNAL")
    e_entry_corr = _se("AAA_entry", "corridor_01")
    e_bath = _se("bathroom_01", "corridor_01")
    e_bed = _se("bedroom_01", "corridor_01")
    edge_result = select_edges(
        candidate_signature="c1",
        placed_room_ids=(
            "AAA_entry", "bathroom_01", "bedroom_01", "corridor_01",
        ),
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
        },
        shared_edges=(e_entry, e_entry_corr, e_bath, e_bed),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    swing_result = assign_swings(
        candidate_signature="c1",
        edge_result=edge_result,
        room_categories={
            "AAA_entry": "main_entrance",
            "bathroom_01": "bathroom",
            "bedroom_01": "bedroom",
            "corridor_01": "corridor",
        },
        room_areas={
            "AAA_entry": 4.0, "bathroom_01": 3.0,
            "bedroom_01": 10.0, "corridor_01": 6.0,
        },
        bathroom_outswing_area_threshold_m2=4.0,
    )
    # Each Phase A assignment gets a Phase B assignment.
    assert len(swing_result.assignments) == len(edge_result.assignments)
    # Bathroom outswing advisory emitted.
    assert len(swing_result.advisory_flags) == 1
    assert (
        swing_result.advisory_flags[0].flag_kind
        == "bathroom_outswing_emergency_clearance"
    )
    # Decision rule diversity proves the dispatch worked.
    rules = {s.decision_rule for s in swing_result.assignments}
    assert "main_entry_into_building" in rules
    assert "bathroom_outswing_compact" in rules


# ──────────────────────────────────────────────────────────────────────
# Adapter equality with native Protocol-conforming object (mock)
# ──────────────────────────────────────────────────────────────────────


def test_phase_a_accepts_protocol_conforming_object():
    """Per v0.3 B5: C13 binds against the Protocol, not the raw C12
    dataclass. Verify a non-adapter, non-C12 object that exposes all
    Protocol fields works."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class FakeEdge:
        room_a_id: str
        room_b_id: str
        axis: str
        overlap_start_m: float
        overlap_end_m: float
        overlap_length_m: float
        min_required_clear_width_m: float
        doorway_feasible: bool
        edge_type: EdgeType

    fake = FakeEdge(
        room_a_id="AAA_entry",
        room_b_id="corridor_01",
        axis="vertical",
        overlap_start_m=0.0,
        overlap_end_m=2.0,
        overlap_length_m=2.0,
        min_required_clear_width_m=0.9,
        doorway_feasible=True,
        edge_type=EdgeType.INTERNAL,
    )
    result = select_edges(
        candidate_signature="c1",
        placed_room_ids=("AAA_entry", "corridor_01"),
        room_categories={
            "AAA_entry": "main_entrance", "corridor_01": "corridor",
        },
        shared_edges=(fake,),
        entry_room_id="AAA_entry",
        room_door_preferences={},
    )
    assert result.main_entry_room_id == "AAA_entry"
