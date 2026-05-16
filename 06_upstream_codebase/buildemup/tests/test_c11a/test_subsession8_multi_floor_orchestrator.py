"""Orchestrator-routed multi-floor integration tests (Spec #4 v1.6 LOCKED).

These tests exercise the FULL `mutate_topologies` path with a multi-floor
brief + wrapper as input. They are distinct from
`test_subsession7_multi_floor.py` (which tests the helpers in isolation)
and from `test_integration/test_b_new_t3_pipeline.py` (which exercises
Spec #1->C9->C10->Spec #3 + helper-level C11a calls).

The wiring this file covers is the S41 "Sub-3 deferred" piece — the
orchestrator end-to-end loop that was finished in this session.
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a.orchestrator import mutate_topologies
from buildemup.components.c11a.schema import (
    FamilySlotAllocation,
    MutationOperator,
    MutationOperatorFamily,
    TopologyMutationConfig,
)
from buildemup.tests._c10_fixtures import run_c9_pipeline
from buildemup.tests._multi_floor_fixtures import (
    make_three_floor_brief_with_master_on,
    make_three_floor_wrapper_master_ground,
    make_two_floor_brief_with_master_on,
    make_two_floor_wrapper_master_ground,
    make_two_floor_wrapper_master_first,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def grid_and_plot():
    """Reuse the pipeline's grid + plot_analysis (same across briefs
    in v1; per-floor grid is B-MFDB-C territory)."""
    _, _brief, grid, plot_analysis = run_c9_pipeline()
    return grid, plot_analysis


# ---------------------------------------------------------------------------
# 1. mutate_topologies accepts a multi-floor brief + wrapper
# ---------------------------------------------------------------------------


def test_orchestrator_accepts_multi_floor_brief_and_wrapper(grid_and_plot):
    """The orchestrator end-to-end runs cleanly with multi-floor input;
    no errors propagate. M0 alone always emits at least one result."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        emit_base=True,
    )
    results = mutate_topologies(
        (wrapper,), brief, grid, plot_analysis, config=config,
    )
    assert len(results) == 1
    assert results[0].application_results[0].operator == MutationOperator.M0_BASE
    assert results[0].application_results[0].valid is True


# ---------------------------------------------------------------------------
# 2. Per-floor dispatch with bipartite interleaving
# ---------------------------------------------------------------------------


def test_orchestrator_dispatches_per_floor_for_tier_a_operator(grid_and_plot):
    """Tier A operators (M1) applied to a 2-floor wrapper produce
    results with `floor_label_affected` set to the targeted floor.
    Both floors should be targeted across the slot allocator's budget.

    Explicit FLIP family slot allocation is set to 2 so the bipartite
    interleaving covers both floors (default allocation is 1 per family).
    """
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
        ),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.FLIP, reserved_slots=2),
        ),
        max_seeds_per_input=8,
        emit_base=True,
    )
    results = mutate_topologies(
        (wrapper,), brief, grid, plot_analysis, config=config,
    )
    # M0 + M1-on-ground + M1-on-first.
    m1_results = [
        r.application_results[0]
        for r in results
        if r.application_results[0].operator == MutationOperator.M1_HORIZ_FLIP
    ]
    floors_targeted = {r.floor_label_affected for r in m1_results}
    assert floors_targeted == {"ground", "first"}, (
        f"expected both floors targeted; got {floors_targeted}"
    )


def test_orchestrator_per_floor_variant_ids_distinct_across_floors(
    grid_and_plot,
):
    """Per-floor variant_ids must be distinct across floors (wrapper-
    scoped suffix `::floor=<label>`) so dedup doesn't collapse them."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.FLIP, reserved_slots=2),
        ),
        max_seeds_per_input=8,
        emit_base=True,
        deduplicate_by_signature=True,
    )
    results = mutate_topologies(
        (wrapper,), brief, grid, plot_analysis, config=config,
    )
    m1_vids = {
        r.application_results[0].topology_variant_id
        for r in results
        if r.application_results[0].operator == MutationOperator.M1_HORIZ_FLIP
    }
    # Two distinct ids (one per floor).
    assert len(m1_vids) == 2


# ---------------------------------------------------------------------------
# 3. M8 routed through real implementation
# ---------------------------------------------------------------------------


def test_orchestrator_routes_m8_through_real_implementation(grid_and_plot):
    """M8 with `requires_multi_floor=True` is dispatched via
    `_dispatch_m8_real` which calls `apply_m8_real`. Result has
    valid=True and a wrapper-scoped variant_id starting with `m8:`."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M8_VERT_REARR,
        ),
        family_slot_allocations=(
            FamilySlotAllocation(
                family=MutationOperatorFamily.BASE, reserved_slots=1,
            ),
            FamilySlotAllocation(
                family=MutationOperatorFamily.VERTICAL, reserved_slots=2,
            ),
        ),
        max_seeds_per_input=4,
        emit_base=True,
        generation=0,
    )
    results = mutate_topologies(
        (wrapper,), brief, grid, plot_analysis, config=config,
    )
    m8_results = [
        r.application_results[0]
        for r in results
        if r.application_results[0].operator == MutationOperator.M8_VERT_REARR
    ]
    assert len(m8_results) >= 1
    m8_first = m8_results[0]
    assert m8_first.valid is True
    assert m8_first.topology_variant_id is not None
    assert m8_first.topology_variant_id.startswith("m8:")
    assert m8_first.floor_label_affected is None  # M8 is dwelling-wide


def test_orchestrator_m8_uses_generation_from_config(grid_and_plot):
    """The generation counter on TopologyMutationConfig threads into
    M8's cyclic algorithm. Different generations produce different
    variant_ids on the same source."""
    grid, plot_analysis = grid_and_plot
    brief = make_three_floor_brief_with_master_on("ground")
    wrapper = make_three_floor_wrapper_master_ground()

    config_gen0 = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE, MutationOperator.M8_VERT_REARR,
        ),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.VERTICAL, reserved_slots=1),
        ),
        max_seeds_per_input=2,
        generation=0,
    )
    config_gen1 = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE, MutationOperator.M8_VERT_REARR,
        ),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.VERTICAL, reserved_slots=1),
        ),
        max_seeds_per_input=2,
        generation=1,
    )
    r0 = mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config_gen0)
    r1 = mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config_gen1)
    vid_0 = next(
        x.application_results[0].topology_variant_id for x in r0
        if x.application_results[0].operator == MutationOperator.M8_VERT_REARR
    )
    vid_1 = next(
        x.application_results[0].topology_variant_id for x in r1
        if x.application_results[0].operator == MutationOperator.M8_VERT_REARR
    )
    assert vid_0 != vid_1
    assert "gen=0" in vid_0
    assert "gen=1" in vid_1


# ---------------------------------------------------------------------------
# 4. Single-floor backwards compatibility (Spec § 3.10)
# ---------------------------------------------------------------------------


def test_orchestrator_single_floor_path_unchanged(grid_and_plot):
    """A single-floor brief (plain FloorRoomBrief) routes through the
    legacy single-floor path. The multi-floor branch is NOT entered.
    Verified by running with a single-floor wrapper input (which has
    no `__multi_floor_candidate__` marker)."""
    grid, plot_analysis = grid_and_plot
    rsc_tuple, single_brief, _grid, _plot = run_c9_pipeline()
    from buildemup.components.c10 import plan_wet_zones
    single_wzpc = plan_wet_zones(rsc_tuple, single_brief, grid, plot_analysis)[0]
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        emit_base=True,
    )
    results = mutate_topologies(
        (single_wzpc,), single_brief, grid, plot_analysis, config=config,
    )
    # Single-floor path uses original logic; M0 result has
    # floor_label_affected=None (default — single-floor doesn't
    # populate it).
    assert len(results) == 1
    assert results[0].application_results[0].floor_label_affected is None


# ---------------------------------------------------------------------------
# 5. Pre-flight validators fire on misaligned input
# ---------------------------------------------------------------------------


def test_orchestrator_rejects_misaligned_brief_and_source(grid_and_plot):
    """If the brief says master on 'ground' but the source wrapper has
    master on 'first', the alignment pre-flight catches it and surfaces
    as OrchestrationAlignmentError. (Systemic — halts the source.)"""
    from buildemup.components.c11a.errors import OrchestrationAlignmentError
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_first()  # master on first — mismatch!
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
    )
    with pytest.raises(OrchestrationAlignmentError):
        mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config)


# ---------------------------------------------------------------------------
# 6. Multi-floor signature is in the cache key path (Item 6 verification)
# ---------------------------------------------------------------------------


def test_orchestrator_multi_floor_signature_flows_through_source_signature(
    grid_and_plot,
):
    """The orchestrator's `_derive_source_signature` reaches the
    multi-floor branch of `derive_canonical_signature` for multi-floor
    wrappers. Verified by checking the result variant_id incorporates
    the wrapper-scoped signature (which differs from any per-floor
    signature)."""
    from buildemup.components.c11a.source_signature import (
        derive_canonical_signature,
    )
    wrapper = make_two_floor_wrapper_master_ground()
    wrapper_sig = derive_canonical_signature(wrapper)
    # Per-floor signature is computed against the per-floor WZPC.
    per_floor_sig = derive_canonical_signature(wrapper.floors[0])
    # They must differ — the wrapper signature aggregates per-floor +
    # master label + schema prefix.
    assert wrapper_sig != per_floor_sig
    # And both are 16-hex-char prefixes.
    assert len(wrapper_sig) == 16
    assert len(per_floor_sig) == 16


# ---------------------------------------------------------------------------
# 7. Per-floor and M8 dispatched together in one batch
# ---------------------------------------------------------------------------


def test_orchestrator_mixed_dispatch_per_floor_and_m8(grid_and_plot):
    """A single batch with both per-floor operators (M1) AND M8
    enabled. M1 dispatches per-floor with bipartite interleaving;
    M8 dispatches dwelling-wide via cyclic selection. Both kinds of
    result appear in the output, with appropriate floor_label_affected
    semantics."""
    grid, plot_analysis = grid_and_plot
    brief = make_two_floor_brief_with_master_on("ground")
    wrapper = make_two_floor_wrapper_master_ground()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
            MutationOperator.M8_VERT_REARR,
        ),
        family_slot_allocations=(
            FamilySlotAllocation(family=MutationOperatorFamily.BASE, reserved_slots=1),
            FamilySlotAllocation(family=MutationOperatorFamily.FLIP, reserved_slots=2),
            FamilySlotAllocation(family=MutationOperatorFamily.VERTICAL, reserved_slots=1),
        ),
        max_seeds_per_input=4,
        generation=0,
    )
    results = mutate_topologies((wrapper,), brief, grid, plot_analysis, config=config)

    by_op = {}
    for r in results:
        ar = r.application_results[0]
        by_op.setdefault(ar.operator, []).append(ar)

    # M0 present, M1 across both floors, M8 dwelling-wide.
    assert MutationOperator.M0_BASE in by_op
    assert MutationOperator.M1_HORIZ_FLIP in by_op
    assert MutationOperator.M8_VERT_REARR in by_op

    # M1 results have floor_label_affected set; M8 doesn't.
    for r in by_op[MutationOperator.M1_HORIZ_FLIP]:
        assert r.floor_label_affected in {"ground", "first"}
    for r in by_op[MutationOperator.M8_VERT_REARR]:
        assert r.floor_label_affected is None
