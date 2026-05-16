"""Sub-6 tests: Phase 2 output assembly + Phase 3 provenance assembly.

W5-18: resolved_objective_count is int, not bool."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from buildemup.components.c11b import (
    EnvironmentFingerprint,
    LocalRefinementConfig,
    LocalRefinementProvenance,
    ObjectiveVector,
    OperatorClass,
    PerTopologyTelemetry,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
    StubEvaluator,
    capture_environment_fingerprint,
)
from buildemup.components.c11b.phase1 import _PerTopologyResult
from buildemup.components.c11b.phase2 import assemble_refined_candidates
from buildemup.components.c11b.phase3 import assemble_provenance


def _params(rid="r0"):
    return RefinedParameters(
        room_dimensions=(RoomDimension(room_id=rid, width_m=3.0, depth_m=4.0),)
    )


def _cand(sig: str) -> RefinedCandidate:
    return RefinedCandidate.from_operator_class(
        OperatorClass.M0_BASE,
        _params(),
        sig,
        objective_vector=ObjectiveVector(
            values=(("o0", 1.0), ("o1", 2.0), ("o2", 3.0)),
            constraint_violations=0.0,
        ),
    )


# ── Phase 2 — output assembly ──────────────────────────────────────────


def test_assemble_concatenates_in_topology_order():
    p0 = _PerTopologyResult(
        refined_candidates=(_cand("t0_a"), _cand("t0_b")),
        telemetry=PerTopologyTelemetry(0, 1, 0.0, 0),
        resolved_objective_count=3,
    )
    p1 = _PerTopologyResult(
        refined_candidates=(_cand("t1_a"),),
        telemetry=PerTopologyTelemetry(1, 1, 0.0, 0),
        resolved_objective_count=3,
    )
    out = assemble_refined_candidates((p0, p1))
    sigs = [c.source_topology_candidate_signature for c in out]
    assert sigs == ["t0_a", "t0_b", "t1_a"]


def test_assemble_empty_input_returns_empty():
    assert assemble_refined_candidates(()) == ()


def test_assembled_candidates_carry_inv_23_false():
    p = _PerTopologyResult(
        refined_candidates=(_cand("x"),),
        telemetry=PerTopologyTelemetry(0, 1, 0.0, 0),
        resolved_objective_count=3,
    )
    out = assemble_refined_candidates((p,))
    assert all(not c.output_sequence_is_quality_ranked for c in out)


# ── Phase 3 — provenance assembly ──────────────────────────────────────


def test_assemble_provenance_basic_fields():
    fp = capture_environment_fingerprint(master_seed=42)
    cfg = LocalRefinementConfig(master_seed=42)
    ev = StubEvaluator()
    ptrs = (
        _PerTopologyResult(
            refined_candidates=(_cand("a"),),
            telemetry=PerTopologyTelemetry(0, 5, 0.3, 2),
            resolved_objective_count=3,
        ),
    )
    prov = assemble_provenance(
        environment_fingerprint=fp,
        config=cfg,
        evaluator=ev,
        batch_size=1,
        accepted_count=1,
        skipped_multifloor_count=0,
        timed_out_topology_count=0,
        failed_topology_count=0,
        per_topology_results=ptrs,
        failure_summaries=(),
    )
    assert prov.master_seed == 42
    assert prov.per_topology_wallclock_seconds == cfg.per_topology_wallclock_seconds
    assert prov.evaluator_skip_cap_fraction == cfg.evaluator_skip_cap_fraction
    assert prov.evaluator_signature == ev.signature()
    assert prov.batch_size == 1
    assert prov.accepted_count == 1


def test_w5_18_resolved_objective_count_is_int():
    """W5-18: resolved_objective_count is int (the actual count), not
    bool (the always-True flag from v0.5)."""
    fp = capture_environment_fingerprint(master_seed=0)
    cfg = LocalRefinementConfig()
    ev = StubEvaluator()
    ptrs = (
        _PerTopologyResult(
            refined_candidates=(_cand("a"),),
            telemetry=PerTopologyTelemetry(0, 1, 0.0, 0),
            resolved_objective_count=3,
        ),
    )
    prov = assemble_provenance(
        environment_fingerprint=fp,
        config=cfg,
        evaluator=ev,
        batch_size=1,
        accepted_count=1,
        skipped_multifloor_count=0,
        timed_out_topology_count=0,
        failed_topology_count=0,
        per_topology_results=ptrs,
        failure_summaries=(),
    )
    assert isinstance(prov.resolved_objective_count, int)
    assert not isinstance(prov.resolved_objective_count, bool)
    assert prov.resolved_objective_count == 3


def test_provenance_telemetry_pass_through():
    """v0.5 W4-3: per_topology_telemetry contains
    longest_generation_seconds + skipped_candidates_total."""
    fp = capture_environment_fingerprint(master_seed=0)
    cfg = LocalRefinementConfig()
    ev = StubEvaluator()
    ptrs = (
        _PerTopologyResult(
            refined_candidates=(),
            telemetry=PerTopologyTelemetry(0, 17, 1.42, 5),
            resolved_objective_count=3,
        ),
    )
    prov = assemble_provenance(
        environment_fingerprint=fp,
        config=cfg,
        evaluator=ev,
        batch_size=1,
        accepted_count=0,
        skipped_multifloor_count=0,
        timed_out_topology_count=0,
        failed_topology_count=0,
        per_topology_results=ptrs,
        failure_summaries=(),
    )
    assert len(prov.per_topology_telemetry) == 1
    t = prov.per_topology_telemetry[0]
    assert t.completed_generations == 17
    assert t.longest_generation_seconds == 1.42
    assert t.skipped_candidates_total == 5


def test_skipped_multifloor_count_recorded():
    fp = capture_environment_fingerprint(master_seed=0)
    cfg = LocalRefinementConfig()
    prov = assemble_provenance(
        environment_fingerprint=fp,
        config=cfg,
        evaluator=StubEvaluator(),
        batch_size=3,
        accepted_count=1,
        skipped_multifloor_count=2,
        timed_out_topology_count=0,
        failed_topology_count=0,
        per_topology_results=(),
        failure_summaries=("topology_index=1: skipped (multi-floor)",),
    )
    assert prov.skipped_multifloor_count == 2
    assert prov.failure_summaries == ("topology_index=1: skipped (multi-floor)",)
