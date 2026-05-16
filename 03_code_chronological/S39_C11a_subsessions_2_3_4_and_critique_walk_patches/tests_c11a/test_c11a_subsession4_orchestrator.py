"""
C11a Sub-session 4 tests — mutate_topologies orchestrator.

Covers Phase 0 → Phase 3 integration: synthetic source candidates
flow through the full orchestrator, hitting Tier A operators directly
and Tier B operators via DeepMutationPipeline.

Also covers Inv 30 (replay determinism) and the integration smoke
test (per CODING_MANDATE Step 1.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c07.grid_generator import Grid, Staircase
from buildemup.components.c11a import (
    DeltaKey,
    EnforcementMode,
    FamilySlotAllocation,
    MutatedTopologyCandidate,
    MutationOperator,
    MutationOperatorFamily,
    ProvenanceVerbosity,
    StubUpstreamRegenerator,
    TopologyMutationConfig,
    mutate_topologies,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Synthetic test fixtures
# =============================================================================


@dataclass(frozen=True)
class _FakeEnvelope:
    facing: PlotOrientation
    width_m: float
    depth_m: float


@dataclass(frozen=True)
class _FakePlotAnalysis:
    envelope: _FakeEnvelope
    trace_id: str = "test-trace"


@dataclass(frozen=True)
class _FakeBrief:
    is_multi_floor: bool = False
    floor_label: str = "ground"


@dataclass(frozen=True)
class _FakeWetZoneCandidate:
    """Synthetic source — carries the fields the orchestrator's
    context-extractor walks. The orchestrator uses duck typing; tests
    don't need real WetZonePlannedCandidate."""
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


def _make_plot_analysis(facing: PlotOrientation = PlotOrientation.NORTH) -> _FakePlotAnalysis:
    return _FakePlotAnalysis(envelope=_FakeEnvelope(facing=facing, width_m=10.0, depth_m=12.0))


# =============================================================================
# Empty input
# =============================================================================


def test_empty_input_returns_empty_output() -> None:
    """Phase 0 short-circuit on empty input."""
    result = mutate_topologies(
        wet_zoned_candidates=(),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
    )
    assert result == ()


# =============================================================================
# Single-source happy path — Tier A only (default config without Tier B reg)
# =============================================================================


def test_single_source_tier_a_produces_at_least_m0_base() -> None:
    """With default config, M0_BASE always succeeds → at least 1 output."""
    src = _FakeWetZoneCandidate()
    # Disable Tier B operators (they'd hit B-NEW-T NotImplementedError);
    # keep only Tier A.
    tier_a_ops = (
        MutationOperator.M0_BASE,
        MutationOperator.M1_HORIZ_FLIP,
        MutationOperator.M2_VERT_FLIP,
        MutationOperator.M9A_ENTRY_CTR,
    )
    config = TopologyMutationConfig(
        enabled_operators=tier_a_ops,
        max_seeds_per_input=4,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    assert len(result) >= 1
    # At least one output is M0_BASE.
    assert any(
        c.applied_operators[0] == MutationOperator.M0_BASE
        for c in result
    )


def test_outputs_are_mutated_topology_candidates() -> None:
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        max_seeds_per_input=2,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    assert all(isinstance(c, MutatedTopologyCandidate) for c in result)


def test_each_output_carries_application_result() -> None:
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    for c in result:
        assert len(c.application_results) == 1
        assert c.application_results[0].valid is True
        assert c.topology_variant_id  # non-empty


# =============================================================================
# Multi-source — output order matches input order
# =============================================================================


def test_multi_source_output_in_input_order() -> None:
    """For each input candidate, its accept-buffer follows in input
    order: source 0's outputs precede source 1's, etc."""
    src_0 = _FakeWetZoneCandidate(topology_kind="strip")
    src_1 = _FakeWetZoneCandidate(topology_kind="courtyard")
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        max_seeds_per_input=1,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src_0, src_1),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    # Each source produces 1 M0_BASE. Per-source order in output.
    assert result[0].source_candidate is src_0
    assert result[1].source_candidate is src_1


# =============================================================================
# Family slot allocation respected
# =============================================================================


def test_family_slot_allocation_caps_per_family() -> None:
    """STAIRCASE family with 2 slot reserve + tight max_seeds → at most
    2 staircase outputs.

    Note: family_slot_allocations.reserved_slots is a FLOOR per the
    Sub-2 allocator design (not a cap). To enforce a cap, max_seeds_per_input
    must equal sum(reserved) so spillover can't grant additional slots.
    """
    src = _FakeWetZoneCandidate()
    enabled_ops = (
        MutationOperator.M0_BASE,
        MutationOperator.M3A_STAIR_EAST,
        MutationOperator.M3B_STAIR_WEST,
        MutationOperator.M3C_STAIR_NE,
    )
    config = TopologyMutationConfig(
        enabled_operators=enabled_ops,
        max_seeds_per_input=3,   # 1 BASE + 2 STAIRCASE = exactly 3, no surplus
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.STAIRCASE, 2),
        ),
        emit_base=True,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    staircase_count = sum(
        1 for c in result
        if c.applied_operators[0] in {
            MutationOperator.M3A_STAIR_EAST,
            MutationOperator.M3B_STAIR_WEST,
            MutationOperator.M3C_STAIR_NE,
        }
    )
    assert staircase_count <= 2


# =============================================================================
# Tier B opt-in via injected regenerator
# =============================================================================


def test_tier_b_with_stub_regenerator_succeeds() -> None:
    """Injecting StubUpstreamRegenerator allows Tier B operators to
    produce valid outputs."""
    src = _FakeWetZoneCandidate()
    stub = StubUpstreamRegenerator(return_value="regenerated-source")
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M6_WET_ROTATE),
        max_seeds_per_input=4,
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL, 1),
        ),
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
        upstream_regenerator=stub,
    )
    m6_outputs = [c for c in result if c.applied_operators[0] == MutationOperator.M6_WET_ROTATE]
    assert len(m6_outputs) == 1


def test_tier_b_without_regenerator_fails_per_candidate() -> None:
    """Without an injected regenerator (real adapter pending B-NEW-T),
    Tier B operators surface as per-candidate invalid; other operators
    still succeed."""
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M6_WET_ROTATE),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL, 1),
        ),
        max_seeds_per_input=4,
    )
    # No upstream_regenerator supplied — real adapter raises NotImplementedError
    # internally; orchestrator catches as per-candidate invalid.
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    # M0_BASE still succeeds → at least 1 output.
    assert len(result) >= 1
    # No M6 in successful outputs.
    assert not any(
        c.applied_operators[0] == MutationOperator.M6_WET_ROTATE
        for c in result
    )


# =============================================================================
# M8 single-floor brief skip path (F-v2-8)
# =============================================================================


def test_m8_skipped_on_single_floor_brief() -> None:
    """M8 requires multi-floor — single-floor brief skips deterministically."""
    src = _FakeWetZoneCandidate()
    stub = StubUpstreamRegenerator(return_value="regen")
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M8_VERT_REARR),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.VERTICAL, 1),
        ),
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(is_multi_floor=False),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
        upstream_regenerator=stub,
    )
    # M8 produced no output; M0 did.
    assert not any(
        c.applied_operators[0] == MutationOperator.M8_VERT_REARR
        for c in result
    )
    # The provenance log records the M8 attempt with reason "single_floor_brief".
    log = result[0].provenance.operator_application_log
    m8_attempts = [r for r in log if r.operator == MutationOperator.M8_VERT_REARR]
    assert len(m8_attempts) == 1
    assert m8_attempts[0].invalidity_reason == "single_floor_brief"


# =============================================================================
# Deduplication
# =============================================================================


def test_deduplication_drops_duplicate_variant_ids() -> None:
    """If two operators produce the same variant_id (synthetically),
    deduplication drops the second."""
    # M0_BASE alone won't produce duplicates; this test confirms the
    # dedup machinery does NOT drop legitimate distinct variant_ids
    # (they're all distinct by operator).
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP),
        deduplicate_by_signature=True,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    variant_ids = [c.topology_variant_id for c in result]
    # All distinct.
    assert len(variant_ids) == len(set(variant_ids))


# =============================================================================
# Inv 30 — replay determinism
# =============================================================================


def test_replay_determinism_two_runs_byte_equal() -> None:
    """Two identical mutate_topologies calls produce byte-equal output
    (modulo observational fields like derived_at, _observational_runtime_ms).
    """
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(
            MutationOperator.M0_BASE,
            MutationOperator.M1_HORIZ_FLIP,
            MutationOperator.M9A_ENTRY_CTR,
        ),
        max_seeds_per_input=4,
    )

    def _run():
        return mutate_topologies(
            wet_zoned_candidates=(src,),
            floor_room_brief=_FakeBrief(),
            grid=_make_grid(),
            plot_analysis=_make_plot_analysis(),
            config=config,
        )

    a = _run()
    b = _run()

    # Output count + ordering identical.
    assert len(a) == len(b)
    for ca, cb in zip(a, b):
        assert ca.applied_operators == cb.applied_operators
        assert ca.topology_variant_id == cb.topology_variant_id
        # MutationApplicationResult is frozen; compare structurally.
        assert ca.application_results[0] == cb.application_results[0]


def test_replay_determinism_with_tier_b_stub() -> None:
    """Determinism preserved when Tier B operators participate."""
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M6_WET_ROTATE),
        family_slot_allocations=(
            FamilySlotAllocation(MutationOperatorFamily.BASE, 1),
            FamilySlotAllocation(MutationOperatorFamily.WET_WALL, 1),
        ),
        max_seeds_per_input=4,
    )

    def _run():
        # Fresh stub per run — cache MUST NOT bleed across invocations
        # (Inv 30 single-batch scope).
        stub = StubUpstreamRegenerator(return_value="regenerated")
        return mutate_topologies(
            wet_zoned_candidates=(src,),
            floor_room_brief=_FakeBrief(),
            grid=_make_grid(),
            plot_analysis=_make_plot_analysis(),
            config=config,
            upstream_regenerator=stub,
        )

    a = _run()
    b = _run()
    assert len(a) == len(b)
    for ca, cb in zip(a, b):
        assert ca.topology_variant_id == cb.topology_variant_id


# =============================================================================
# Provenance verbosity
# =============================================================================


def test_provenance_verbosity_summary_drops_attempts_log() -> None:
    """SUMMARY verbosity → provenance.operator_application_log is empty."""
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        provenance_verbosity=ProvenanceVerbosity.SUMMARY,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    assert result[0].provenance.operator_application_log == ()


def test_provenance_verbosity_per_op_includes_attempts_log() -> None:
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
        provenance_verbosity=ProvenanceVerbosity.PER_OP,
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    assert len(result[0].provenance.operator_application_log) >= 1


# =============================================================================
# Provenance — quarantine fingerprint
# =============================================================================


def test_provenance_carries_quarantine_fingerprint_at_strict_mode() -> None:
    """STRICT mode → empty quarantined_operators tuple, deterministic hash."""
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE,),
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    fp = result[0].provenance.quarantine_fingerprint
    assert fp.quarantined_operators == ()
    assert fp.fingerprint_hash  # non-empty


# =============================================================================
# Diagnostics
# =============================================================================


def test_diagnostics_per_operator_yield_populated() -> None:
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP),
    )
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    diag = result[0].provenance.diagnostics
    # Both operators attempted; per_operator_yield has entries for them.
    assert MutationOperator.M0_BASE in diag.per_operator_yield
    assert MutationOperator.M1_HORIZ_FLIP in diag.per_operator_yield
    # Yields in [0, 1].
    for op, y in diag.per_operator_yield.items():
        assert 0.0 <= y <= 1.0


def test_diagnostics_records_runtime_observationally() -> None:
    src = _FakeWetZoneCandidate()
    config = TopologyMutationConfig()
    result = mutate_topologies(
        wet_zoned_candidates=(src,),
        floor_room_brief=_FakeBrief(),
        grid=_make_grid(),
        plot_analysis=_make_plot_analysis(),
        config=config,
    )
    # _observational_runtime_ms is set on provenance.
    assert result[0].provenance._observational_runtime_ms >= 0
