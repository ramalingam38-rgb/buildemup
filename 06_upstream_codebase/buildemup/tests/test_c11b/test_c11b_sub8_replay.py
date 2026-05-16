"""Sub-8 tests: replay determinism per Inv 29.

TIER-1 (byte-equal) requires the full conjunction: same env fingerprint
+ same config + same upstream inputs.

W6-3: schema-version bump invalidates fingerprint."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from buildemup.components.c11b import (
    LocalRefinementConfig,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
    StubEvaluator,
    capture_environment_fingerprint,
    run_local_refinement,
)
from buildemup.components.c11b.tiebreak import _compute_tiebreak_fingerprint


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


def _mtc():
    return _FakeMTC(
        source_candidate="src_artifact",
        application_results=(_FakeAppResult(output_candidate=None),),
        applied_operators=(_FakeOp("m1"),),
    )


def _brief():
    return _Brief(
        room_requirements=(
            _Req("r0", "bedroom", 3.0, 4.0),
            _Req("r1", "kitchen", 2.5, 3.0),
        )
    )


# ── TIER-1 byte-equal replay (Inv 29) ──────────────────────────────────


def test_tier_1_byte_equal_replay_same_config_same_seed():
    cfg = LocalRefinementConfig(
        pop_size=8, max_generations=3, master_seed=42
    )
    grid = _Grid(envelope_width_m=12.0, envelope_depth_m=10.0)
    eval1 = StubEvaluator()
    eval2 = StubEvaluator()

    out1 = run_local_refinement(
        (_mtc(),), _brief(), grid, grid, eval1, config=cfg
    )
    out2 = run_local_refinement(
        (_mtc(),), _brief(), grid, grid, eval2, config=cfg
    )

    sigs1 = [c.source_topology_candidate_signature for c in out1]
    sigs2 = [c.source_topology_candidate_signature for c in out2]
    assert sigs1 == sigs2

    # All RefinedParameters must match byte-for-byte (via tiebreak_fingerprint).
    fps1 = [c.tiebreak_fingerprint for c in out1]
    fps2 = [c.tiebreak_fingerprint for c in out2]
    assert fps1 == fps2


def test_replay_different_seed_diverges():
    grid = _Grid(envelope_width_m=12.0, envelope_depth_m=10.0)
    cfg_a = LocalRefinementConfig(pop_size=8, max_generations=3, master_seed=42)
    cfg_b = LocalRefinementConfig(pop_size=8, max_generations=3, master_seed=43)
    out_a = run_local_refinement(
        (_mtc(),), _brief(), grid, grid, StubEvaluator(), config=cfg_a
    )
    out_b = run_local_refinement(
        (_mtc(),), _brief(), grid, grid, StubEvaluator(), config=cfg_b
    )
    # Almost certainly different fingerprints (PRNG-driven init).
    fps_a = [c.tiebreak_fingerprint for c in out_a]
    fps_b = [c.tiebreak_fingerprint for c in out_b]
    assert fps_a != fps_b


# ── W6-3 schema version invalidation ───────────────────────────────────


def test_w6_3_version_bump_invalidates_fingerprint():
    """Bumping TIEBREAK_FINGERPRINT_SCHEMA_VERSION causes the same
    RefinedParameters to hash to a different fingerprint — the whole
    point of the W6-3 fix."""
    import buildemup.components.c11b.tiebreak as tb_mod

    rp = RefinedParameters(
        room_dimensions=(
            RoomDimension(room_id="r0", width_m=3.0, depth_m=4.0),
        )
    )
    fp_v1 = _compute_tiebreak_fingerprint(rp)
    original = tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION
    try:
        tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = 2
        fp_v2 = _compute_tiebreak_fingerprint(rp)
        assert fp_v1 != fp_v2
    finally:
        tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = original


def test_w6_3_env_fingerprint_captures_schema_version():
    """The captured EnvironmentFingerprint must include the
    schema version so cache lookups invalidate correctly when it
    bumps."""
    import buildemup.components.c11b.environment_fingerprint as efp_mod

    fp_v1 = capture_environment_fingerprint(master_seed=0)
    original = efp_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION
    try:
        efp_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = 2
        fp_v2 = capture_environment_fingerprint(master_seed=0)
        assert fp_v1.tiebreak_fingerprint_schema_version == 1
        assert fp_v2.tiebreak_fingerprint_schema_version == 2
        assert fp_v1.fingerprint_hash != fp_v2.fingerprint_hash
        assert not fp_v1.matches(fp_v2)
    finally:
        efp_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = original


# ── SEMVER_POLICY_VERSION (W6-8) ───────────────────────────────────────


def test_semver_policy_version_constant_exists():
    """W6-8: replaces v0.6 doc-presence meta-test with a
    constant-presence test. The constant being importable and being
    an int IS the contract."""
    from buildemup.components.c11b import SEMVER_POLICY_VERSION

    assert SEMVER_POLICY_VERSION == 1
    assert isinstance(SEMVER_POLICY_VERSION, int)


# ── PRNG independence across runs ──────────────────────────────────────


def test_prng_stream_byte_equal_across_runs():
    """Reinforce that the per-topology PRNG path is byte-equal."""
    from buildemup.components.c11b.prng import _build_per_topology_rng

    r1 = _build_per_topology_rng(42, 0, "sig")
    r2 = _build_per_topology_rng(42, 0, "sig")
    assert np.array_equal(r1.random(500), r2.random(500))
