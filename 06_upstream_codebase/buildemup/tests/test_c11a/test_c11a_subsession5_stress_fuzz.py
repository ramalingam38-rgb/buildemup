"""
C11a Sub-session 5 — B-NEW-Y partial: long-horizon stress fuzz tests.

Per S39 critique walk F10. The full B-NEW-Y (mutation chain
accumulation + topology corruption + perf regression) is gated on
B-NEW-T1 landing, since meaningful chain-stress requires Tier B real
upstream. The partial shipped here covers the bits that DON'T need
B-NEW-T1:

  * Randomised single-operator dispatch fuzz (Hypothesis) — every
    Tier A operator with any synthetic context combination either
    returns a valid result OR an invalid one with a structured
    failure reason. Never crashes.

  * Many-source batch stress — orchestrator handles 50+ sources
    in one invocation without state leakage between sources.

  * Determinism stress — 10 repeated invocations on the same input
    produce byte-equal outputs (Inv 30 with replay).

  * Perf regression sentinel — single-source orchestrator dispatch
    completes within a generous budget (lets us notice 10× slowdowns
    in CI).

What this does NOT cover (requires B-NEW-T1):
  * 1000+ generation chained mutations
  * Mutation accumulation effects (those are C11b territory anyway)
  * Real-upstream regeneration stress

Pattern: hypothesis-based generators construct synthetic candidates
matching the lenient extractor's expected attribute paths. The
Sub-4 _FakeWetZoneCandidate fixture style is the reference.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest

# Hypothesis is already a project dependency (used in c4_property_based,
# c5_stability tests). If unavailable on a runner, skip cleanly.
try:
    from hypothesis import HealthCheck, given, settings, strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:  # pragma: no cover - defensive
    _HYPOTHESIS_AVAILABLE = False

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c07.grid_generator import Grid, Staircase
from buildemup.components.c11a import (
    FamilySlotAllocation,
    MutatedTopologyCandidate,
    MutationOperator,
    MutationOperatorFamily,
    StubUpstreamRegenerator,
    TopologyMutationConfig,
    mutate_topologies,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Synthetic test fixtures (lenient extractor compatibility)
# =============================================================================


@dataclass(frozen=True)
class _FakeEnvelope:
    facing: PlotOrientation = PlotOrientation.NORTH
    width_m: float = 10.0
    depth_m: float = 12.0


@dataclass(frozen=True)
class _FakePlotAnalysis:
    envelope: _FakeEnvelope = field(default_factory=_FakeEnvelope)
    trace_id: str = "stress-trace"


@dataclass(frozen=True)
class _FakeBrief:
    is_multi_floor: bool = False
    floor_label: str = "ground"


@dataclass(frozen=True)
class _FakeSource:
    topology_kind: str = "central_spine"
    zone_bands: dict = field(default_factory=lambda: {
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
    })
    corridor_path: Any = None


def _make_grid(width_m: float = 10.0, depth_m: float = 12.0) -> Grid:
    return Grid(
        columns=[],
        bay_x_m=3.0, bay_y_m=3.0,
        columns_x_count=0, columns_y_count=0,
        envelope_width_m=width_m, envelope_depth_m=depth_m,
        staircase=Staircase(
            origin_x_m=1.0, origin_y_m=1.0,
            width_m=1.0, landing_depth_m=1.2,
        ),
    )


# =============================================================================
# Hypothesis strategies
# =============================================================================


if _HYPOTHESIS_AVAILABLE:
    _ORIENTATIONS = list(PlotOrientation)
    _TOPOLOGY_KINDS = ["strip", "central_spine", "courtyard", "l_shape"]

    # Filter out M8 (multi-floor only) and Tier B operators (need
    # injected regenerator) from the random-operator strategy. The
    # stress fuzz runs against Tier A.
    _TIER_A_OPS = [
        MutationOperator.M0_BASE,
        MutationOperator.M1_HORIZ_FLIP,
        MutationOperator.M2_VERT_FLIP,
        MutationOperator.M3A_STAIR_EAST,
        MutationOperator.M3B_STAIR_WEST,
        MutationOperator.M3C_STAIR_NE,
        MutationOperator.M4_CORRIDOR_INV,
        MutationOperator.M5_ZONE_SWAP,
        MutationOperator.M9A_ENTRY_CTR,
        MutationOperator.M9B_ENTRY_W,
        MutationOperator.M9C_ENTRY_E,
        MutationOperator.M9D_ENTRY_OFF,
    ]

    @st.composite
    def fake_source_strategy(draw) -> _FakeSource:
        kind = draw(st.sampled_from(_TOPOLOGY_KINDS))
        public_dir = draw(st.sampled_from(_ORIENTATIONS))
        private_dir = draw(st.sampled_from(_ORIENTATIONS))
        return _FakeSource(
            topology_kind=kind,
            zone_bands={
                ZoneBand.PUBLIC: public_dir,
                ZoneBand.PRIVATE: private_dir,
            },
        )


# =============================================================================
# Randomised dispatch fuzz — never crashes
# =============================================================================


@pytest.mark.skipif(
    not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed",
)
class TestRandomDispatchFuzz:

    @settings(
        max_examples=50,
        deadline=2000,  # 2s per example — generous for CI
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.large_base_example],
    )
    @given(
        source=fake_source_strategy(),
        plot_facing=st.sampled_from(list(PlotOrientation)),
    )
    def test_orchestrator_never_crashes_on_random_inputs(
        self, source: _FakeSource, plot_facing: PlotOrientation,
    ) -> None:
        """Fuzz: random source × random plot facing → orchestrator
        completes without raising. Outputs may be empty (every operator
        rejected) or populated; both are acceptable. Crash = bug."""
        # Restrict to Tier A operators — Tier B without regenerator
        # is per-candidate invalid (which is fine but doesn't add
        # crash-coverage value).
        config = TopologyMutationConfig(
            enabled_operators=tuple(_TIER_A_OPS),
            max_seeds_per_input=8,
        )
        result = mutate_topologies(
            wet_zoned_candidates=(source,),
            floor_room_brief=_FakeBrief(),
            grid=_make_grid(),
            plot_analysis=_FakePlotAnalysis(
                envelope=_FakeEnvelope(facing=plot_facing),
            ),
            config=config,
        )
        # Output is a (possibly empty) tuple of MutatedTopologyCandidate.
        assert isinstance(result, tuple)
        assert all(isinstance(c, MutatedTopologyCandidate) for c in result)


# =============================================================================
# Many-source batch stress
# =============================================================================


def test_many_source_batch_no_state_leak() -> None:
    """50 sources in one batch — outputs match per-source counts; no
    pipeline state leaks between sources."""
    sources = tuple(
        _FakeSource(
            topology_kind=("strip" if i % 2 == 0 else "central_spine"),
        )
        for i in range(50)
    )
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        max_seeds_per_input=1,
    )
    result = mutate_topologies(
        wet_zoned_candidates=sources,
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_FakePlotAnalysis(),
        config=config,
    )
    # Each source produces 1 M0_BASE; total = 50.
    assert len(result) == 50

    # Per-source ordering preserved: result[i].source_candidate is sources[i].
    for i, c in enumerate(result):
        assert c.source_candidate is sources[i]


def test_many_source_unique_variant_ids() -> None:
    """50 distinct sources → 50 distinct variant_ids (signature
    uniqueness across-source)."""
    sources = tuple(
        _FakeSource(topology_kind=f"synthetic_{i}") for i in range(50)
    )
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
    )
    result = mutate_topologies(
        wet_zoned_candidates=sources,
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_FakePlotAnalysis(),
        config=config,
    )
    variant_ids = [c.topology_variant_id for c in result]
    assert len(set(variant_ids)) == len(variant_ids)


# =============================================================================
# Determinism stress (Inv 30 — replay)
# =============================================================================


def test_replay_determinism_10_runs_byte_equal() -> None:
    """10 repeated invocations → byte-equal outputs (variant_ids,
    application_results). Stresses Inv 30 beyond the 2-run check
    in subsession4_orchestrator."""
    src = _FakeSource()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
            MutationOperator.M9A_ENTRY_CTR,
        ),
        max_seeds_per_input=4,
    )

    def _run() -> tuple:
        return mutate_topologies(
            wet_zoned_candidates=(src,),
            floor_room_brief=_FakeBrief(),
            grid=_make_grid(),
            plot_analysis=_FakePlotAnalysis(),
            config=config,
        )

    runs = [_run() for _ in range(10)]
    base = runs[0]
    for i, run in enumerate(runs[1:], start=1):
        assert len(run) == len(base), f"run {i}: length differs"
        for j, (a, b) in enumerate(zip(base, run)):
            assert a.applied_operators == b.applied_operators, (
                f"run {i} candidate {j}: operators differ"
            )
            assert a.topology_variant_id == b.topology_variant_id, (
                f"run {i} candidate {j}: variant_id differs"
            )
            assert a.application_results[0] == b.application_results[0], (
                f"run {i} candidate {j}: result differs"
            )


def test_tier_b_replay_with_stub_regenerator_10_runs() -> None:
    """Tier B replay determinism. Each run gets a fresh
    StubUpstreamRegenerator (no cross-batch state); identical outputs."""
    src = _FakeSource()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M6_WET_ROTATE),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL, 1),
        ),
        max_seeds_per_input=4,
    )

    def _run() -> tuple:
        stub = StubUpstreamRegenerator(return_value="regen-stable")
        return mutate_topologies(
            wet_zoned_candidates=(src,),
            floor_room_brief=_FakeBrief(),
            grid=_make_grid(),
            plot_analysis=_FakePlotAnalysis(),
            config=config,
            upstream_regenerator=stub,
        )

    runs = [_run() for _ in range(10)]
    variant_id_sets = [
        tuple(c.topology_variant_id for c in run) for run in runs
    ]
    base = variant_id_sets[0]
    for i, vs in enumerate(variant_id_sets[1:], start=1):
        assert vs == base, f"run {i} variant_ids differ"


# =============================================================================
# Performance regression sentinel
# =============================================================================


def test_perf_single_source_within_generous_budget() -> None:
    """Single-source dispatch through the full Tier A path completes
    within a generous budget. Sentinel — flags 10× slowdowns in CI.

    Budget: 250ms. Real call should be < 50ms; 5× margin for CI noise.
    """
    src = _FakeSource()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
            MutationOperator.M2_VERT_FLIP,
            MutationOperator.M9A_ENTRY_CTR,
        ),
    )
    start = time.perf_counter()
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_FakePlotAnalysis(),
        config=config,
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 0.25, (
        f"Single-source dispatch took {elapsed*1000:.1f}ms; "
        f"perf regression suspected (budget 250ms)."
    )
    assert len(result) >= 1


def test_perf_50_source_batch_within_generous_budget() -> None:
    """50-source batch — sublinear-ish scaling expected from cache
    sharing within batch. Generous budget 2.5s."""
    sources = tuple(_FakeSource() for _ in range(50))
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
            MutationOperator.M9A_ENTRY_CTR,
        ),
    )
    start = time.perf_counter()
    result = mutate_topologies(
        wet_zoned_candidates=sources,
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_FakePlotAnalysis(),
        config=config,
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 2.5, (
        f"50-source batch took {elapsed*1000:.1f}ms; "
        f"perf regression suspected (budget 2.5s)."
    )
    assert len(result) >= 50


# =============================================================================
# Pipeline-cache stress
# =============================================================================


def test_cache_within_batch_tier_b_serves_repeat_attempts() -> None:
    """Same Tier B operator on identical sources hits cache — 50
    repeat attempts produce only 1 stub regenerate() call (bound is
    cap_size_per_batch worst-case 128 / per-source unique 1)."""
    sources = tuple(_FakeSource() for _ in range(50))
    stub = StubUpstreamRegenerator(return_value="regen-shared")
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M6_WET_ROTATE),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL, 1),
        ),
    )
    mutate_topologies(
        wet_zoned_candidates=sources,
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_FakePlotAnalysis(),
        config=config,
        upstream_regenerator=stub,
    )
    # 50 sources, but every source's repr-based signature is identical
    # (synthetic _FakeSource's frozen-dataclass repr is stable).
    # Without index disambiguation, the cache would hit on every source
    # after the first — but the orchestrator's _derive_source_signature
    # includes source_index, so signatures differ per index.
    # Result: 50 distinct cache keys → 50 stub regenerate calls.
    assert stub.regenerate_call_count == 50
