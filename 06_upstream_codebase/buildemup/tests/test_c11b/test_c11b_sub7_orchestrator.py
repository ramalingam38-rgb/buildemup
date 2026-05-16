"""Sub-7 tests: orchestrator — STRICT/WARN escalation,
BatchAllTopologiesFailedError, EnvironmentFingerprintMismatchError."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from buildemup.components.c11b import (
    BatchAllTopologiesFailedError,
    EnforcementMode,
    EnvironmentFingerprint,
    EnvironmentFingerprintMismatchError,
    LocalRefinementConfig,
    MultiFloorRefinementNotSupportedError,
    StubEvaluator,
    capture_environment_fingerprint,
    run_local_refinement,
    run_local_refinement_with_provenance,
)


# ── upstream-shape doubles ─────────────────────────────────────────────


class _FakeOp:
    def __init__(self, value: str) -> None:
        self.value = value


@dataclass
class _FakeAppResult:
    output_candidate: Any = None


@dataclass
class _FakeMTC:
    source_candidate: Any = "src"
    application_results: tuple = ()
    applied_operators: tuple = ()


@dataclass
class _Brief:
    room_requirements: tuple


@dataclass
class _Req:
    room_id: str
    category: str
    min_width_m: float
    min_depth_m: float


@dataclass
class _Grid:
    envelope_width_m: float
    envelope_depth_m: float


@dataclass
class _Plot:
    envelope_width_m: float = 0.0
    envelope_depth_m: float = 0.0


class _MFArt:
    __multi_floor_candidate__ = True


def _make_brief():
    return _Brief(
        room_requirements=(
            _Req("r0", "bedroom", 3.0, 4.0),
            _Req("r1", "bathroom", 1.5, 2.0),
        )
    )


def _mtc_single_floor() -> _FakeMTC:
    return _FakeMTC(
        source_candidate="src_artifact",
        application_results=(_FakeAppResult(output_candidate=None),),
        applied_operators=(_FakeOp("m1"),),
    )


def _mtc_multi_floor() -> _FakeMTC:
    return _FakeMTC(
        source_candidate=_MFArt(),
        application_results=(_FakeAppResult(output_candidate=None),),
        applied_operators=(_FakeOp("m0_base"),),
    )


# ── STRICT mode: any per-topology error halts immediately ──────────────


def test_strict_mode_halts_on_multi_floor():
    cfg = LocalRefinementConfig(
        enforcement_mode=EnforcementMode.STRICT, pop_size=4, max_generations=2
    )
    with pytest.raises(MultiFloorRefinementNotSupportedError):
        run_local_refinement(
            (_mtc_multi_floor(),),
            _make_brief(),
            _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
            _Plot(),
            StubEvaluator(),
            config=cfg,
        )


# ── WARN mode: per-topology error accumulates ──────────────────────────


def test_warn_mode_skips_multi_floor_and_returns_others():
    cfg = LocalRefinementConfig(
        enforcement_mode=EnforcementMode.WARN, pop_size=4, max_generations=2
    )
    result = run_local_refinement_with_provenance(
        (_mtc_multi_floor(), _mtc_single_floor()),
        _make_brief(),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Plot(),
        StubEvaluator(),
        config=cfg,
    )
    # The single-floor topology contributed candidates.
    assert len(result.refined_candidates) >= 1
    assert result.provenance.skipped_multifloor_count == 1
    assert result.provenance.batch_size == 2


def test_warn_mode_all_failing_raises_batch_all_failed():
    """When EVERY topology fails under WARN, we raise
    BatchAllTopologiesFailedError."""
    cfg = LocalRefinementConfig(
        enforcement_mode=EnforcementMode.WARN, pop_size=4, max_generations=2
    )
    with pytest.raises(BatchAllTopologiesFailedError):
        run_local_refinement(
            (_mtc_multi_floor(), _mtc_multi_floor()),
            _make_brief(),
            _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
            _Plot(),
            StubEvaluator(),
            config=cfg,
        )


def test_warn_mode_empty_batch_returns_empty():
    """An empty input batch is not a failure — just produces no
    candidates."""
    cfg = LocalRefinementConfig(enforcement_mode=EnforcementMode.WARN)
    out = run_local_refinement(
        (),
        _make_brief(),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Plot(),
        StubEvaluator(),
        config=cfg,
    )
    assert out == ()


# ── EnvironmentFingerprint replay check (Inv 24 + Inv 29) ──────────────


def test_replay_with_matching_fingerprint_succeeds():
    cfg = LocalRefinementConfig(pop_size=4, max_generations=2, master_seed=42)
    expected = capture_environment_fingerprint(master_seed=42)
    # Should not raise.
    run_local_refinement(
        (_mtc_single_floor(),),
        _make_brief(),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Plot(),
        StubEvaluator(),
        config=cfg,
        expected_environment_fingerprint=expected,
    )


def test_replay_with_mismatched_fingerprint_raises():
    """Different master_seed → fingerprint mismatch → raise."""
    cfg = LocalRefinementConfig(pop_size=4, max_generations=2, master_seed=42)
    wrong = capture_environment_fingerprint(master_seed=999)
    with pytest.raises(EnvironmentFingerprintMismatchError, match="mismatch"):
        run_local_refinement(
            (_mtc_single_floor(),),
            _make_brief(),
            _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
            _Plot(),
            StubEvaluator(),
            config=cfg,
            expected_environment_fingerprint=wrong,
        )


# ── basic end-to-end smoke ────────────────────────────────────────────


def test_basic_run_returns_provenance_with_telemetry():
    cfg = LocalRefinementConfig(pop_size=6, max_generations=3)
    result = run_local_refinement_with_provenance(
        (_mtc_single_floor(),),
        _make_brief(),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Plot(),
        StubEvaluator(),
        config=cfg,
    )
    assert result.provenance.batch_size == 1
    assert len(result.provenance.per_topology_telemetry) == 1
    assert result.provenance.resolved_objective_count == 3


def test_basic_run_produces_pareto_output_size_or_less():
    cfg = LocalRefinementConfig(
        pop_size=10, max_generations=2, pareto_output_size=5
    )
    result = run_local_refinement(
        (_mtc_single_floor(),),
        _make_brief(),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Plot(),
        StubEvaluator(),
        config=cfg,
    )
    assert len(result) <= 5
