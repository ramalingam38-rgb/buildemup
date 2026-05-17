"""Unit tests for the C11b → C12 adapter glue (S57 follow-up #4).

The orchestrator's C12 phase uses ``adapters.c11b_to_c12`` to build
``SingleFloorPlacementInput`` tuples from upstream output. Two paths:

  1. RefinedCandidate (primary) — for when C11b ships OK after S57 #3
     lands. Exercised here with a synthetic RefinedCandidate.
  2. MutatedTopologyCandidate (fallback) — used while C11b is STUB.
     Exercised here with real C11a output via the smoke-test fixture
     chain (C4 → C5 → ... → C11a).

Plus the orchestrator-facing dispatcher
``build_single_floor_inputs_from_upstream`` is tested for routing
behavior (refined preferred, mutated fallback, empty payload).
"""
from __future__ import annotations

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c05 import select_topology
from buildemup.components.c06 import prioritize_orientation
from buildemup.components.c07.grid_generator import GridGenerator
from buildemup.components.c08 import design_corridors
from buildemup.components.c09 import size_rooms
from buildemup.components.c10 import plan_wet_zones
from buildemup.components.c11a import mutate_topologies
from buildemup.components.c11a.schema import (
    MutationOperator,
    TopologyMutationConfig,
)
from buildemup.components.c11b.schema import (
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.components.c12 import (
    RoomSpec,
    SingleFloorPlacementInput,
)
from buildemup.domain.brief import VastuTier
from buildemup.orchestration.adapters import (
    adapt_mutated_to_single_floor,
    adapt_refined_to_single_floor,
    build_single_floor_inputs_from_upstream,
)
from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60, make_brief,
)
from buildemup.tests.validation._c5_fixtures import medium_brief


# ──────────────────────────────────────────────────────────────────────
# Fixtures — run the C4-C11a chain once to get real upstream output.
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def upstream_chain():
    """Run C4 → C5 → ... → C11a on the smoke-test fixture so adapter
    tests have realistic upstream output to consume."""
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()

    plot_analysis = derive(brief_for_c4, now=1700000000.0)
    topology_candidates = select_topology(plot_analysis, floor_brief)
    oriented = prioritize_orientation(
        topology_candidates, plot_analysis, VastuTier.PARTIAL,
    )
    grid = GridGenerator().generate(
        envelope_width_m=plot_analysis.plot.width_m,
        envelope_depth_m=plot_analysis.plot.depth_m,
    )
    cdc = design_corridors(tuple(oriented), grid, plot_analysis)
    rsc = size_rooms(cdc, floor_brief, grid, plot_analysis)
    wzpc = plan_wet_zones(rsc, floor_brief, grid, plot_analysis)
    mutated = mutate_topologies(
        wzpc, floor_brief, grid, plot_analysis,
        config=TopologyMutationConfig(
            enabled_operators=(MutationOperator.M0_BASE,),
            emit_base=True, max_seeds_per_input=4,
        ),
    )
    return plot_analysis, mutated


# ──────────────────────────────────────────────────────────────────────
# Fallback path — MutatedTopologyCandidate adapter
# ──────────────────────────────────────────────────────────────────────


def test_fallback_adapter_produces_single_floor_input(upstream_chain):
    """The fallback adapter materializes a valid SingleFloorPlacementInput
    from a real C11a MutatedTopologyCandidate."""
    plot_analysis, mutated = upstream_chain
    assert len(mutated) >= 1, (
        "C11a smoke chain must produce at least one mutated candidate"
    )
    first = mutated[0]
    sf_input = adapt_mutated_to_single_floor(first, plot_analysis)

    assert isinstance(sf_input, SingleFloorPlacementInput)
    assert sf_input.candidate_signature == first.topology_variant_id
    # M0_BASE is materialized per C11b § 0.3.1 worked example.
    assert sf_input.capability_mode == "MATERIALIZED"
    assert sf_input.placement_safe is True
    assert sf_input.geometry_materialized is True
    # Envelope dimensions threaded from plot_analysis.
    assert sf_input.envelope_width_m == plot_analysis.plot.width_m
    assert sf_input.envelope_depth_m == plot_analysis.plot.depth_m
    # Room set is non-empty and well-formed.
    assert len(sf_input.rooms) >= 1
    for r in sf_input.rooms:
        assert isinstance(r, RoomSpec)
        assert r.room_id  # non-empty
        assert r.category  # non-empty
        assert r.target_width_m > 0
        assert r.target_depth_m > 0


def test_fallback_adapter_preserves_room_ids(upstream_chain):
    """The adapter doesn't reorder or rename rooms from upstream."""
    plot_analysis, mutated = upstream_chain
    first = mutated[0]
    sf_input = adapt_mutated_to_single_floor(first, plot_analysis)

    upstream_ids = {
        r.room_id
        for r in first.source_candidate.room_sized_candidate.room_size_table.rooms
    }
    adapter_ids = {r.room_id for r in sf_input.rooms}
    assert adapter_ids == upstream_ids


# ──────────────────────────────────────────────────────────────────────
# Primary path — RefinedCandidate adapter (synthetic input)
# ──────────────────────────────────────────────────────────────────────


def _make_refined_candidate(
    *,
    source_sig: str = "topo:test",
    rooms: tuple[tuple[str, float, float], ...] = (
        ("bedroom_01", 3.5, 4.0),
        ("kitchen_01", 3.0, 3.0),
        ("living_01", 4.5, 4.0),
    ),
) -> RefinedCandidate:
    """Build a synthetic RefinedCandidate for primary-path testing.

    The room_dimensions must be lex-ASC by room_id (C11b
    RefinedParameters invariant).
    """
    sorted_rooms = sorted(rooms, key=lambda x: x[0])
    return RefinedCandidate(
        refined_parameters=RefinedParameters(
            room_dimensions=tuple(
                RoomDimension(room_id=r[0], width_m=r[1], depth_m=r[2])
                for r in sorted_rooms
            ),
        ),
        source_topology_candidate_signature=source_sig,
        geometry_materialized=True,
        placement_safe=True,
        requires_transform_resolution=False,
    )


def test_primary_adapter_consumes_refined_candidate(upstream_chain):
    """adapt_refined_to_single_floor builds a valid SingleFloorPlacementInput
    from a synthetic RefinedCandidate + category lookup."""
    plot_analysis, _ = upstream_chain
    refined = _make_refined_candidate(source_sig="topo:primary_path")
    categories = {
        "bedroom_01": "bedroom",
        "kitchen_01": "kitchen",
        "living_01": "living",
    }

    sf_input = adapt_refined_to_single_floor(
        refined, plot_analysis, room_categories_by_id=categories,
    )

    assert isinstance(sf_input, SingleFloorPlacementInput)
    assert sf_input.candidate_signature == "topo:primary_path"
    assert sf_input.capability_mode == "MATERIALIZED"
    assert sf_input.placement_safe is True
    assert sf_input.envelope_width_m == plot_analysis.plot.width_m
    assert len(sf_input.rooms) == 3
    # Room IDs preserved; categories filled from lookup.
    room_map = {r.room_id: r for r in sf_input.rooms}
    assert room_map["bedroom_01"].category == "bedroom"
    assert room_map["bedroom_01"].target_width_m == 3.5
    assert room_map["bedroom_01"].target_depth_m == 4.0
    assert room_map["kitchen_01"].category == "kitchen"


def test_primary_adapter_raises_on_missing_category(upstream_chain):
    """If the category lookup is missing a room_id, KeyError surfaces.

    The orchestrator builds the lookup from C11a upstream, so missing
    entries indicate a contract bug — fail loudly rather than silently
    using a default.
    """
    plot_analysis, _ = upstream_chain
    refined = _make_refined_candidate()
    incomplete_categories = {"bedroom_01": "bedroom"}  # missing others

    with pytest.raises(KeyError):
        adapt_refined_to_single_floor(
            refined, plot_analysis,
            room_categories_by_id=incomplete_categories,
        )


# ──────────────────────────────────────────────────────────────────────
# Dispatcher — build_single_floor_inputs_from_upstream
# ──────────────────────────────────────────────────────────────────────


def test_dispatcher_uses_fallback_when_c11b_payload_is_none(upstream_chain):
    """When C11b ships STUB (payload=None), dispatcher uses the
    MutatedTopologyCandidate path."""
    plot_analysis, mutated = upstream_chain
    inputs = build_single_floor_inputs_from_upstream(
        c11a_payload=mutated,
        c11b_payload=None,
        plot_analysis=plot_analysis,
    )
    assert len(inputs) == len(mutated)
    # Each input's signature traces back to a mutated candidate.
    sigs = {i.candidate_signature for i in inputs}
    expected = {m.topology_variant_id for m in mutated}
    assert sigs == expected


def test_dispatcher_returns_empty_when_both_payloads_missing():
    """No upstream data → empty input tuple (orchestrator surfaces this
    as a SKIPPED phase upstream; the adapter itself stays pure)."""
    inputs = build_single_floor_inputs_from_upstream(
        c11a_payload=None,
        c11b_payload=None,
        plot_analysis=None,
    )
    assert inputs == ()


def test_dispatcher_falls_back_when_c11b_payload_has_no_refined(upstream_chain):
    """If C11b's payload exists but exposes no refined_candidates
    (e.g., empty RefinementBatchResult), dispatcher still falls back
    to C11a rather than panicking."""
    plot_analysis, mutated = upstream_chain

    class EmptyRefinement:
        refined_candidates: tuple = ()

    inputs = build_single_floor_inputs_from_upstream(
        c11a_payload=mutated,
        c11b_payload=EmptyRefinement(),
        plot_analysis=plot_analysis,
    )
    # Refined path returned nothing → fallback to mutated path.
    assert len(inputs) == len(mutated)
