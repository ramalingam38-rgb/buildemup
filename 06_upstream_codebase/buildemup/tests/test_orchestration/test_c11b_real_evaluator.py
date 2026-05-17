"""Unit tests for the real C11b EvaluatorProtocol (S57 follow-up #3).

Two layers:
  - Direct tests on `MultiObjectiveEvaluator.evaluate(...)` with
    synthetic RefinedCandidates so the objective-surface behavior is
    visible without running NSGA.
  - Smoke test exercising the full orchestrator with
    `use_real_c11b_evaluator=True` to verify whether NSGA converges
    on the real evaluator's objective surface. Whether C11b ends up
    OK or STUB depends on whether NSGA can navigate; the test asserts
    the more important contract: **the orchestrator runs without
    error, the phase is non-ERROR, and the evaluator's signature is
    captured** — even if NSGA can't converge under the smoke fixture's
    MVP config (a different concern, tracked separately).
"""
from __future__ import annotations

import pytest

from buildemup.components.c11b.schema import (
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    PhaseStatus,
)
from buildemup.orchestration.evaluators import (
    MultiObjectiveEvaluator,
    RoomEvaluationContext,
    build_real_evaluator_from_upstream,
)
from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60, make_brief,
)
from buildemup.tests.validation._c5_fixtures import medium_brief


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


def _make_refined(rooms: tuple[tuple[str, float, float], ...]) -> RefinedCandidate:
    sorted_rooms = sorted(rooms, key=lambda r: r[0])
    return RefinedCandidate(
        refined_parameters=RefinedParameters(
            room_dimensions=tuple(
                RoomDimension(room_id=r[0], width_m=r[1], depth_m=r[2])
                for r in sorted_rooms
            ),
        ),
        source_topology_candidate_signature="topo:eval_test",
        geometry_materialized=True,
        placement_safe=True,
        requires_transform_resolution=False,
    )


def _make_evaluator(
    *,
    contexts: tuple[tuple[str, float, float], ...] = (
        ("bedroom_01", 12.0, 2.4),
        ("kitchen_01", 9.0, 2.1),
        ("living_01", 18.0, 3.0),
    ),
    envelope_area: float = 240.0,  # generous envelope
) -> MultiObjectiveEvaluator:
    return MultiObjectiveEvaluator(
        room_contexts_by_id={
            c[0]: RoomEvaluationContext(
                room_id=c[0], target_area_m2=c[1], min_width_m=c[2],
            )
            for c in contexts
        },
        envelope_area_m2=envelope_area,
    )


# ──────────────────────────────────────────────────────────────────────
# Direct evaluator behavior
# ──────────────────────────────────────────────────────────────────────


def test_evaluator_returns_three_objectives():
    """Always exactly three objectives, in canonical order."""
    ev = _make_evaluator()
    refined = _make_refined((
        ("bedroom_01", 3.0, 4.0),
        ("kitchen_01", 3.0, 3.0),
        ("living_01", 4.5, 4.0),
    ))
    vec = ev.evaluate(refined)
    assert len(vec.values) == 3
    names = [name for name, _ in vec.values]
    assert names == ["area_undersizing", "aspect_penalty", "envelope_waste"]
    assert vec.constraint_violations == 0.0


def test_area_undersizing_is_zero_at_target():
    """Rooms exactly at C9 target → undersizing = 0."""
    ev = _make_evaluator()
    refined = _make_refined((
        ("bedroom_01", 3.0, 4.0),  # area = 12 (target)
        ("kitchen_01", 3.0, 3.0),  # area = 9 (target)
        ("living_01", 4.5, 4.0),   # area = 18 (target)
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["area_undersizing"] == 0.0


def test_area_undersizing_grows_quadratically_with_deficit():
    """Halving a room's area should yield deficit²-style penalty."""
    ev = _make_evaluator()
    refined = _make_refined((
        ("bedroom_01", 2.0, 3.0),  # area = 6 (target 12 → deficit 6 → 36)
        ("kitchen_01", 3.0, 3.0),  # at target
        ("living_01", 4.5, 4.0),   # at target
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["area_undersizing"] == pytest.approx(36.0)


def test_oversized_room_does_not_contribute_to_undersizing():
    """Areas above C9 target are fine — C12 handles envelope fit."""
    ev = _make_evaluator()
    refined = _make_refined((
        ("bedroom_01", 5.0, 5.0),  # area = 25 (target 12, oversized)
        ("kitchen_01", 3.0, 3.0),
        ("living_01", 4.5, 4.0),
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["area_undersizing"] == 0.0


def test_aspect_penalty_zero_for_squares():
    """Perfect-square rooms minimize aspect penalty."""
    ev = _make_evaluator()
    refined = _make_refined((
        ("bedroom_01", 3.0, 3.0),
        ("kitchen_01", 3.0, 3.0),
        ("living_01", 4.0, 4.0),
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["aspect_penalty"] == 0.0


def test_aspect_penalty_grows_for_elongated_rooms():
    """Long-thin rooms accumulate penalty."""
    ev = _make_evaluator()
    refined = _make_refined((
        # 2:1 aspect → (2-1)² = 1 per room
        ("bedroom_01", 2.0, 4.0),
        ("kitchen_01", 2.0, 4.0),
        ("living_01", 2.0, 4.0),
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["aspect_penalty"] == pytest.approx(3.0)


def test_envelope_waste_zero_when_full_utilization():
    """Total room area >= envelope → waste = 0."""
    ev = _make_evaluator(envelope_area=30.0)
    refined = _make_refined((
        ("bedroom_01", 5.0, 5.0),
        ("kitchen_01", 5.0, 5.0),
        ("living_01", 5.0, 5.0),
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    assert by_name["envelope_waste"] == 0.0


def test_envelope_waste_positive_when_under_utilized():
    """Small rooms in a large envelope → waste > 0."""
    ev = _make_evaluator(envelope_area=100.0)
    refined = _make_refined((
        ("bedroom_01", 2.0, 3.0),  # 6
        ("kitchen_01", 3.0, 3.0),  # 9
        ("living_01", 4.0, 4.0),   # 16
    ))
    vec = ev.evaluate(refined)
    by_name = dict(vec.values)
    # Total = 31; waste = 100 - 31 = 69
    assert by_name["envelope_waste"] == pytest.approx(69.0)


# ──────────────────────────────────────────────────────────────────────
# signature() — stable across identical contexts
# ──────────────────────────────────────────────────────────────────────


def test_signature_stable_across_identical_evaluators():
    ev1 = _make_evaluator()
    ev2 = _make_evaluator()
    assert ev1.signature() == ev2.signature()


def test_signature_differs_when_envelope_differs():
    ev_small = _make_evaluator(envelope_area=100.0)
    ev_large = _make_evaluator(envelope_area=300.0)
    assert ev_small.signature() != ev_large.signature()


def test_signature_unaffected_by_dict_ordering():
    """RoomEvaluationContext dict iteration order should NOT change
    the signature (sorted internally by room_id)."""
    contexts_a = {
        "alpha_room": RoomEvaluationContext("alpha_room", 12.0, 2.4),
        "beta_room": RoomEvaluationContext("beta_room", 9.0, 2.1),
    }
    contexts_b = {
        "beta_room": RoomEvaluationContext("beta_room", 9.0, 2.1),
        "alpha_room": RoomEvaluationContext("alpha_room", 12.0, 2.4),
    }
    ev_a = MultiObjectiveEvaluator(
        room_contexts_by_id=contexts_a, envelope_area_m2=200.0,
    )
    ev_b = MultiObjectiveEvaluator(
        room_contexts_by_id=contexts_b, envelope_area_m2=200.0,
    )
    assert ev_a.signature() == ev_b.signature()


# ──────────────────────────────────────────────────────────────────────
# build_real_evaluator_from_upstream
# ──────────────────────────────────────────────────────────────────────


def test_build_real_evaluator_raises_on_empty_payload():
    """Empty C11a output → caller should not call the builder."""
    with pytest.raises(ValueError, match="empty payload"):
        build_real_evaluator_from_upstream(
            c11a_payload=(),
            plot_analysis=object(),
        )


# ──────────────────────────────────────────────────────────────────────
# Construction guards
# ──────────────────────────────────────────────────────────────────────


def test_evaluator_rejects_nonpositive_envelope_area():
    with pytest.raises(ValueError, match="envelope_area_m2 must be positive"):
        MultiObjectiveEvaluator(
            room_contexts_by_id={
                "r": RoomEvaluationContext("r", 10.0, 2.0),
            },
            envelope_area_m2=0.0,
        )


# ──────────────────────────────────────────────────────────────────────
# Integration smoke — does the orchestrator actually wire it through?
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def smoke_inputs():
    plot = bangalore_40x60()
    return plot, make_brief(plot), medium_brief()


def test_orchestrator_flips_c11b_to_ok_with_real_evaluator(smoke_inputs):
    """With use_real_c11b_evaluator=True, the orchestrator:

    1. Builds the MultiObjectiveEvaluator from upstream context.
    2. Builds the C11b brief shim (so C11b's NSGA sees the per-room
       constraints it needs — canonical FloorRoomBrief doesn't carry
       these).
    3. Threads both into run_local_refinement.

    Result: C11b NSGA converges and emits real RefinedCandidates →
    phase flips from STUB (S56 default) to OK.
    """
    plot, brief_for_c4, floor_brief = smoke_inputs
    config = MasterOrchestratorConfig(use_real_c11b_evaluator=True)
    orch = MasterOrchestrator(config)
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c11b = result.phase("c11b_nsga_refinement")
    assert c11b is not None
    assert c11b.status == PhaseStatus.OK, (
        f"C11b expected OK with real evaluator; got {c11b.status} "
        f"({c11b.error_class}: {c11b.error_message})"
    )
    assert c11b.payload is not None
    assert len(c11b.payload) > 0, "Expected at least one RefinedCandidate"
    notes_text = " ".join(c11b.notes)
    assert "MultiObjectiveEvaluator" in notes_text


def test_c12_primary_adapter_path_activates_when_c11b_ships_ok(smoke_inputs):
    """Sanity: once C11b ships OK with the real evaluator, the C12
    dispatcher should pick the documented PRIMARY adapter path
    (`RefinedCandidate` → `SingleFloorPlacementInput`) instead of the
    C11a fallback. C12 stays OK; its notes line records which path
    ran."""
    plot, brief_for_c4, floor_brief = smoke_inputs
    config = MasterOrchestratorConfig(use_real_c11b_evaluator=True)
    orch = MasterOrchestrator(config)
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    c11b = result.phase("c11b_nsga_refinement")
    if c11b.status != PhaseStatus.OK:
        pytest.skip(
            "C11b did not ship OK on this fixture; primary-path "
            "assertion only meaningful when C11b is OK."
        )
    c12 = result.phase("c12_vertical_placement")
    assert c12.status == PhaseStatus.OK
    notes_text = " ".join(c12.notes)
    # Primary path uses RefinedCandidate; the orchestrator's notes
    # distinguish "RefinedCandidate (primary)" vs "MutatedTopologyCandidate
    # (fallback)".
    assert "RefinedCandidate" in notes_text
    assert "fallback" not in notes_text.lower()
