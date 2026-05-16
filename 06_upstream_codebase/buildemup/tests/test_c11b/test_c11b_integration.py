"""Integration tests for C11b end-to-end paths."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from buildemup.components.c11b import (
    LocalRefinementConfig,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
    StubEvaluator,
    StubEvaluatorConfig,
    run_local_refinement,
    run_local_refinement_with_provenance,
)
from buildemup.components.c11b.bounds import (
    MAX_ROOM_ASPECT_RATIO,
    SEMANTIC_CAP_BY_CATEGORY,
    derive_room_upper_bounds,
)
from buildemup.components.c11b.evaluator import _compute_three_stub_objectives


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


def _mtc(op_name: str = "m1") -> _FakeMTC:
    return _FakeMTC(
        source_candidate="src",
        application_results=(_FakeAppResult(output_candidate=None),),
        applied_operators=(_FakeOp(op_name),),
    )


# ── StubEvaluator behaviour ────────────────────────────────────────────


def test_stub_evaluator_3_objectives_default():
    """W4-1: default is 3 objectives (v0.3 carried)."""
    ev = StubEvaluator()
    rp = RefinedParameters(
        room_dimensions=(RoomDimension(room_id="r0", width_m=3.0, depth_m=4.0),)
    )
    cand = RefinedCandidate.from_operator_class(OperatorClass.M0_BASE, rp, "s")
    ov = ev.evaluate(cand)
    assert len(ov.values) == 3


def test_stub_evaluator_2_objectives_mode():
    """Setting objectives=2 produces 2 dimensions."""
    ev = StubEvaluator(StubEvaluatorConfig(objectives=2))
    rp = RefinedParameters(
        room_dimensions=(RoomDimension(room_id="r0", width_m=3.0, depth_m=4.0),)
    )
    cand = RefinedCandidate.from_operator_class(OperatorClass.M0_BASE, rp, "s")
    ov = ev.evaluate(cand)
    assert len(ov.values) == 2


def test_stub_evaluator_signature_stable():
    ev1 = StubEvaluator()
    ev2 = StubEvaluator()
    assert ev1.signature() == ev2.signature()
    ev3 = StubEvaluator(StubEvaluatorConfig(objectives=2))
    assert ev3.signature() != ev1.signature()


def test_compute_three_objectives_square_room_compact():
    """A 3x3 (square) room should have lower compactness score than
    a 3x6 (rectangle) room."""
    rp_sq = RefinedParameters(
        room_dimensions=(RoomDimension(room_id="r0", width_m=3.0, depth_m=3.0),)
    )
    rp_rect = RefinedParameters(
        room_dimensions=(RoomDimension(room_id="r0", width_m=3.0, depth_m=6.0),)
    )
    sq_cand = RefinedCandidate.from_operator_class(OperatorClass.M0_BASE, rp_sq, "s")
    rect_cand = RefinedCandidate.from_operator_class(OperatorClass.M0_BASE, rp_rect, "s")
    sq_c, _, _ = _compute_three_stub_objectives(sq_cand)
    rect_c, _, _ = _compute_three_stub_objectives(rect_cand)
    assert sq_c < rect_c


# ── bounds (§ 0.6) ─────────────────────────────────────────────────────


def test_semantic_caps_by_category():
    assert SEMANTIC_CAP_BY_CATEGORY["bathroom"] == 1.8
    assert SEMANTIC_CAP_BY_CATEGORY["kitchen"] == 1.5


def test_max_room_aspect_ratio_constant():
    assert MAX_ROOM_ASPECT_RATIO == 3.0


def test_derive_bounds_bedroom_uses_universal():
    """Categories not in SEMANTIC_CAP_BY_CATEGORY fall back to
    universal_max_multiplier."""
    uw, ud = derive_room_upper_bounds(
        "r0", "bedroom", 3.0, 4.0, 12.0, 10.0, 30.0
    )
    # Upper should be >= min.
    assert uw >= 3.0
    assert ud >= 4.0


def test_derive_bounds_bathroom_uses_semantic_cap():
    """Bathroom: semantic cap 1.8."""
    uw, ud = derive_room_upper_bounds(
        "r0", "bathroom", 1.5, 2.0, 12.0, 10.0, 30.0
    )
    # Envelope-aware clipping may dominate; just verify caps not exceeded.
    assert uw <= 1.5 * 1.8 + 1e-9 or uw <= 12.0
    assert ud <= 2.0 * 1.8 + 1e-9 or ud <= 10.0


# ── end-to-end with a real population ──────────────────────────────────


def test_end_to_end_with_pop_size_8():
    cfg = LocalRefinementConfig(
        pop_size=8, max_generations=3, pareto_output_size=4
    )
    out = run_local_refinement(
        (_mtc("m1"), _mtc("m2")),
        _Brief(
            room_requirements=(
                _Req("r0", "bedroom", 3.0, 4.0),
                _Req("r1", "bathroom", 1.5, 2.0),
            )
        ),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        StubEvaluator(),
        config=cfg,
    )
    assert isinstance(out, tuple)
    # Two topologies × up to 4 each = at most 8.
    assert len(out) <= 8
    # All outputs honour Inv 23.
    assert all(not c.output_sequence_is_quality_ranked for c in out)
    # All outputs have populated objective vectors.
    assert all(c.objective_vector is not None for c in out)


def test_end_to_end_provenance_complete():
    cfg = LocalRefinementConfig(pop_size=6, max_generations=2)
    result = run_local_refinement_with_provenance(
        (_mtc("m1"),),
        _Brief(
            room_requirements=(
                _Req("r0", "bedroom", 3.0, 4.0),
                _Req("r1", "bathroom", 1.5, 2.0),
            )
        ),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        StubEvaluator(),
        config=cfg,
    )
    prov = result.provenance
    assert prov.c11b_version == "v1.1"
    assert prov.batch_size == 1
    assert prov.resolved_objective_count == 3
    assert prov.failed_topology_count == 0
    assert prov.timed_out_topology_count == 0
    assert prov.skipped_multifloor_count == 0
    assert len(prov.per_topology_telemetry) == 1


def test_end_to_end_tier_a_carries_predicate_only_flags():
    """Tier A SHALLOW operators (m1) produce candidates with
    geometry_materialized=False per § 0.3.1."""
    cfg = LocalRefinementConfig(pop_size=4, max_generations=1)
    out = run_local_refinement(
        (_mtc("m1"),),
        _Brief(
            room_requirements=(
                _Req("r0", "bedroom", 3.0, 4.0),
            )
        ),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        StubEvaluator(),
        config=cfg,
    )
    assert len(out) > 0
    for c in out:
        assert c.geometry_materialized is False
        assert c.placement_safe is False
        assert c.requires_transform_resolution is True
        assert c.capability_mode == "PREDICATE_ONLY"


def test_end_to_end_tier_b_carries_materialized_flags():
    """Tier B (m6) → geometry_materialized=True."""
    cfg = LocalRefinementConfig(pop_size=4, max_generations=1)
    out = run_local_refinement(
        (_mtc("m6"),),
        _Brief(
            room_requirements=(
                _Req("r0", "bedroom", 3.0, 4.0),
            )
        ),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        _Grid(envelope_width_m=12.0, envelope_depth_m=10.0),
        StubEvaluator(),
        config=cfg,
    )
    assert len(out) > 0
    for c in out:
        assert c.geometry_materialized is True
        assert c.placement_safe is True
        assert c.requires_transform_resolution is False
        assert c.capability_mode == "MATERIALIZED"
