"""Sub-5 tests: Phase 1 — W5-9 ordering, Inv 28 skip cap, Inv 27
per-topology timeout, aspect-ratio HARD constraint."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from buildemup.components.c11b import (
    LocalRefinementConfig,
    MultiFloorRefinementNotSupportedError,
    ObjectiveVector,
    OperatorClass,
    PerTopologyTimeoutError,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
    StubEvaluator,
)
from buildemup.components.c11b.bounds import compute_aspect_constraint_violation
from buildemup.components.c11b.errors import EvaluatorContractError
from buildemup.components.c11b.initialization import RoomSizeRequirement
from buildemup.components.c11b.phase1 import (
    _classify_operator,
    _evaluate_population,
    refine_one_topology,
)
from buildemup.components.c11b.timeout import WallclockBudget


# ── operator-class classification ──────────────────────────────────────


class _FakeOp:
    def __init__(self, value: str) -> None:
        self.value = value


@dataclass
class _FakeMTC:
    source_candidate: Any = "src"
    application_results: tuple = ()
    applied_operators: tuple = ()


@dataclass
class _FakeAppResult:
    output_candidate: Any = None


def _mtc(op_name: str, output_candidate: Any = None) -> _FakeMTC:
    return _FakeMTC(
        source_candidate="src_artifact",
        application_results=(_FakeAppResult(output_candidate=output_candidate),),
        applied_operators=(_FakeOp(op_name),),
    )


def test_classify_m0_base():
    assert _classify_operator(_mtc("m0_base")) == OperatorClass.M0_BASE


def test_classify_tier_a_operators():
    for n in ("m1", "m2", "m3a", "m4", "m5", "m9a"):
        assert _classify_operator(_mtc(n)) == OperatorClass.TIER_A_SHALLOW


def test_classify_tier_b_operators():
    for n in ("m6", "m7"):
        assert _classify_operator(_mtc(n)) == OperatorClass.TIER_B_REGENERATIVE


def test_classify_m8_multi_floor():
    assert _classify_operator(_mtc("m8_floor_swap_real")) == OperatorClass.M8_MULTI_FLOOR


# ── aspect-ratio HARD constraint (Inv 22) ──────────────────────────────


def test_aspect_violation_zero_for_square():
    assert compute_aspect_constraint_violation(3.0, 3.0) == 0.0


def test_aspect_violation_zero_at_threshold():
    # 3:1 → ratio 3.0, exactly at threshold → 0 violation.
    assert compute_aspect_constraint_violation(6.0, 2.0) == 0.0


def test_aspect_violation_positive_beyond_threshold():
    # 4:1 → ratio 4.0, violation 1.0
    v = compute_aspect_constraint_violation(8.0, 2.0)
    assert v == pytest.approx(1.0, abs=1e-9)


def test_aspect_violation_negative_dims_inf():
    assert compute_aspect_constraint_violation(0.0, 3.0) == float("inf")


# ── _evaluate_population: per-candidate skip cap (Inv 28) ──────────────


class _FailingEvaluator:
    """Raises EvaluatorContractError on the first ``n_fail`` candidates,
    then succeeds. Used to test the skip cap."""

    def __init__(self, n_fail: int) -> None:
        self._n_fail = n_fail
        self._call = 0

    def evaluate(self, c: RefinedCandidate) -> ObjectiveVector:
        self._call += 1
        if self._call <= self._n_fail:
            raise EvaluatorContractError("test-injection")
        return ObjectiveVector(values=(("o0", 1.0),), constraint_violations=0.0)

    def signature(self) -> str:
        return "failing-test-stub"


def _make_population(n: int) -> tuple[RefinedCandidate, ...]:
    rp = RefinedParameters(
        room_dimensions=(RoomDimension(room_id="r0", width_m=3.0, depth_m=4.0),)
    )
    return tuple(
        RefinedCandidate.from_operator_class(
            OperatorClass.M0_BASE, rp, f"sig_{i}"
        )
        for i in range(n)
    )


def test_inv_28_within_skip_cap_passes():
    """Skip count ≤ cap → continue at reduced population."""
    pop = _make_population(10)
    cfg = LocalRefinementConfig(pop_size=10, evaluator_skip_cap_fraction=0.5)
    # cap = max(1, int(10 * 0.5)) = 5
    evaluator = _FailingEvaluator(n_fail=3)  # 3 ≤ 5 (cap)
    out, skipped = _evaluate_population(pop, evaluator, cfg)
    assert skipped == 3
    assert len(out) == 7


def test_inv_28_exceeds_skip_cap_raises():
    """Skip count > cap → systemic EvaluatorContractError."""
    pop = _make_population(10)
    cfg = LocalRefinementConfig(pop_size=10, evaluator_skip_cap_fraction=0.2)
    # cap = max(1, int(10 * 0.2)) = 2
    evaluator = _FailingEvaluator(n_fail=5)  # 5 > 2 (cap)
    with pytest.raises(EvaluatorContractError, match="cap exceeded"):
        _evaluate_population(pop, evaluator, cfg)


def test_inv_28_skip_cap_minimum_one():
    """Inv 28: ``max(1, int(pop_size * fraction))`` — fraction 0.01 on
    pop_size 5 still allows at least 1 skip."""
    pop = _make_population(5)
    cfg = LocalRefinementConfig(pop_size=5, evaluator_skip_cap_fraction=0.01)
    # cap = max(1, int(5 * 0.01)) = max(1, 0) = 1
    evaluator = _FailingEvaluator(n_fail=1)
    out, skipped = _evaluate_population(pop, evaluator, cfg)
    assert skipped == 1
    assert len(out) == 4


# ── per-topology timeout (Inv 27) ──────────────────────────────────────


def test_wallclock_budget_raises_when_exceeded():
    """Inv 27: budget breach at a generation boundary raises."""
    budget = WallclockBudget(budget_seconds=0.05, topology_index=0)
    time.sleep(0.08)
    with pytest.raises(PerTopologyTimeoutError, match="topology_index=0"):
        budget.check(gen=1, max_gen=10)


def test_wallclock_budget_passes_within_budget():
    budget = WallclockBudget(budget_seconds=60.0, topology_index=0)
    budget.check(gen=1, max_gen=10)  # no raise


def test_wallclock_budget_tracks_longest_generation():
    budget = WallclockBudget(budget_seconds=60.0, topology_index=0)
    budget.open_generation()
    time.sleep(0.02)
    budget.close_generation()
    budget.open_generation()
    time.sleep(0.05)
    budget.close_generation()
    assert budget.longest_generation_seconds >= 0.05


# ── W5-9 ordering: MF rejection BEFORE signature derivation ────────────


def test_w5_9_mf_rejection_before_signature():
    """When the resolved artifact is multi-floor, refine_one_topology
    raises MultiFloorRefinementNotSupportedError WITHOUT having called
    derive_canonical_signature. We verify this by monkeypatching the
    signature derivation to record calls."""
    import buildemup.components.c11b.phase1 as phase1_mod

    calls = []

    def _spy(art):
        calls.append(art)
        return "fake_sig"

    original = phase1_mod.derive_canonical_signature
    phase1_mod.derive_canonical_signature = _spy
    try:
        from buildemup.components.c11b.input_resolution import (
            _is_multi_floor_artifact,
        )

        # Build a fake multi-floor artifact via the C11a marker attribute.
        class MFArt:
            __multi_floor_candidate__ = True

        mtc = _mtc("m0_base", output_candidate=MFArt())
        assert _is_multi_floor_artifact(MFArt())
        cfg = LocalRefinementConfig(pop_size=2, max_generations=1)
        evaluator = StubEvaluator()
        with pytest.raises(MultiFloorRefinementNotSupportedError):
            refine_one_topology(
                mtc=mtc,
                topology_index=0,
                requirements=(),
                envelope_w=10.0,
                envelope_d=10.0,
                evaluator=evaluator,
                config=cfg,
            )
        # The signature derivation must NOT have been called.
        assert calls == [], (
            f"W5-9 violation: derive_canonical_signature was called "
            f"before MF rejection. Calls: {calls}"
        )
    finally:
        phase1_mod.derive_canonical_signature = original
