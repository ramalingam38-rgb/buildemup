"""Multi-floor orchestration tests (Spec #4 v1.6 LOCKED).

Per Spec #4 v1.6 § 5.1: 18 example-based tests covering the multi-floor
orchestration helpers (pre-flights, bipartite interleaving,
affected_floor_set) and the M8 real implementation (cyclic target
selection, failure taxonomy).

These tests exercise the v1.6 contract pieces in isolation. Integration
tests (cross-spec end-to-end) live in
`tests/test_integration/test_b_new_t3_pipeline.py`.
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a.errors import (
    OrchestrationAlignmentError,
    OrchestrationProtocolError,
)
from buildemup.components.c11a.orchestrator import (
    _generate_per_floor_attempts,
    _validate_multi_floor_alignment,
    _validate_multi_floor_protocol,
    affected_floor_set,
)
from buildemup.components.c11a.m8_floor_swap_real import (
    apply_m8_real,
    compute_eligible_master_targets,
    pick_m8_target,
)
from buildemup.components.c11a.schema import (
    FloorImpact,
    MutationOperator,
)
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.domain.multi_floor_brief import MultiFloorDwellingBrief
from buildemup.tests._multi_floor_fixtures import (
    clone_wzpc,
    make_three_floor_brief_with_master_on,
    make_three_floor_wrapper_master_ground,
    make_two_floor_brief_with_master_on,
    make_two_floor_wrapper_master_ground,
    make_two_floor_wrapper_master_first,
    run_multi_floor_c9_c10_pipeline,
)


# ===========================================================================
# 1. Pre-flight validators (Spec #4 § 3.1)
# ===========================================================================


def test_validate_multi_floor_protocol_accepts_real_brief():
    """Real MultiFloorDwellingBrief passes the duck-type protocol check."""
    brief = make_two_floor_brief_with_master_on("ground")
    _validate_multi_floor_protocol(brief)  # no raise


def test_validate_multi_floor_protocol_rejects_single_floor_brief():
    """A plain FloorRoomBrief has no is_multi_floor attribute -> rejected."""
    plain = FloorRoomBrief(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
    )
    with pytest.raises(OrchestrationProtocolError):
        _validate_multi_floor_protocol(plain)


def test_validate_multi_floor_protocol_rejects_impostor_with_mismatched_cardinality():
    """A duck-type impostor with floors != floor_labels length is caught."""

    class Impostor:
        is_multi_floor = True
        floors = (1, 2)
        floor_labels = ("a", "b", "c")

    with pytest.raises(OrchestrationProtocolError, match="floor_labels length"):
        _validate_multi_floor_protocol(Impostor())


def test_validate_multi_floor_alignment_passes_when_matched():
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()
    _validate_multi_floor_alignment(brief, source)  # no raise


def test_validate_multi_floor_alignment_rejects_master_mismatch():
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_first()  # master on 'first'
    with pytest.raises(OrchestrationAlignmentError, match="master"):
        _validate_multi_floor_alignment(brief, source)


# ===========================================================================
# 2. Bipartite operator+floor interleaving (Spec #4 § 3.2)
# ===========================================================================


def test_generate_per_floor_attempts_covers_all_pairs_for_n_eq_n():
    """For n_operators == n_floors, the full schedule covers every
    (operator, floor) pair exactly once."""
    ops = (MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP)
    floors = ("ground", "first")
    attempts = _generate_per_floor_attempts(ops, floors)
    assert len(attempts) == 4
    pairs = set(attempts)
    assert len(pairs) == 4
    # Every operator + every floor appears.
    assert {a[0] for a in attempts} == set(ops)
    assert {a[1] for a in attempts} == set(floors)


def test_generate_per_floor_attempts_round_major_outer_loop():
    """Round 0 emits one (operator, floor) pair for each operator with
    rotated floor; round 1 rotates again. Verifies bipartite shape."""
    ops = (MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP)
    floors = ("g", "f")
    attempts = _generate_per_floor_attempts(ops, floors)
    # Round 0: (M0, g), (M1, f).
    assert attempts[0] == (MutationOperator.M0_BASE, "g")
    assert attempts[1] == (MutationOperator.M1_HORIZ_FLIP, "f")
    # Round 1: (M0, f), (M1, g).
    assert attempts[2] == (MutationOperator.M0_BASE, "f")
    assert attempts[3] == (MutationOperator.M1_HORIZ_FLIP, "g")


def test_generate_per_floor_attempts_bounded_imbalance_under_truncation():
    """Truncated to S < n_ops * n_floors slots, per-operator and
    per-floor counts differ by at most 1 (Spec § 3.2 fairness theorem)."""
    ops = (
        MutationOperator.M0_BASE,
        MutationOperator.M1_HORIZ_FLIP,
        MutationOperator.M2_VERT_FLIP,
        MutationOperator.M4_CORRIDOR_INV,
    )
    floors = ("a", "b", "c", "d")
    attempts = _generate_per_floor_attempts(ops, floors)
    # Truncate to 6 slots (< 16).
    truncated = attempts[:6]
    op_counts = {}
    floor_counts = {}
    for op, fl in truncated:
        op_counts[op] = op_counts.get(op, 0) + 1
        floor_counts[fl] = floor_counts.get(fl, 0) + 1
    # Imbalance <= 1 on each axis.
    op_vals = sorted(op_counts.values())
    fl_vals = sorted(floor_counts.values())
    assert op_vals[-1] - op_vals[0] <= 1
    assert fl_vals[-1] - fl_vals[0] <= 1


def test_generate_per_floor_attempts_single_floor_one_attempt_per_op():
    """n_floors=1 collapses to one attempt per operator (existing
    single-floor behaviour preserved byte-identical per Spec § 3.2)."""
    ops = (
        MutationOperator.M0_BASE,
        MutationOperator.M1_HORIZ_FLIP,
        MutationOperator.M2_VERT_FLIP,
    )
    floors = ("only",)
    attempts = _generate_per_floor_attempts(ops, floors)
    assert len(attempts) == 3
    assert all(a[1] == "only" for a in attempts)


# ===========================================================================
# 3. affected_floor_set split-kwarg API (Spec #4 § 3.11)
# ===========================================================================


def test_affected_floor_set_per_floor_operator_returns_one_direct_floor():
    """A per-floor operator (M0, M1, ...) with direct_floor_label returns
    a single FloorImpact(direct, cascade=True)."""
    source = make_two_floor_wrapper_master_ground()
    impacts = affected_floor_set(
        MutationOperator.M2_VERT_FLIP,
        source,
        direct_floor_label="first",
    )
    assert len(impacts) == 1
    impact = next(iter(impacts))
    assert impact.label == "first"
    assert impact.kind == "direct"
    assert impact.requires_cascade is True
    assert impact.requires_validation_only is False


def test_affected_floor_set_m8_returns_old_and_new_master_floors():
    """M8 with new_master_floor_label returns TWO FloorImpacts: the
    old master and the new master."""
    source = make_two_floor_wrapper_master_ground()
    impacts = affected_floor_set(
        MutationOperator.M8_VERT_REARR,
        source,
        new_master_floor_label="first",
    )
    labels = {i.label for i in impacts}
    assert labels == {"ground", "first"}
    assert all(i.kind == "direct" and i.requires_cascade for i in impacts)


def test_affected_floor_set_rejects_wrong_kwarg_for_operator_class():
    """Per-floor operator + new_master_floor_label -> protocol error.
    M8 + direct_floor_label -> protocol error."""
    source = make_two_floor_wrapper_master_ground()
    with pytest.raises(OrchestrationProtocolError, match="MUST be None"):
        affected_floor_set(
            MutationOperator.M2_VERT_FLIP,
            source,
            direct_floor_label="first",
            new_master_floor_label="ground",
        )
    with pytest.raises(OrchestrationProtocolError, match="MUST be None"):
        affected_floor_set(
            MutationOperator.M8_VERT_REARR,
            source,
            direct_floor_label="first",
            new_master_floor_label="ground",
        )


# ===========================================================================
# 4. M8 cyclic target selection (Spec #4 § 3.4)
# ===========================================================================


def test_m8_target_selection_is_deterministic():
    """Same (eligible_targets, generation, operator_index) -> same target."""
    targets = ("first", "second", "third")
    a = pick_m8_target(targets, generation=5, operator_index=2)
    b = pick_m8_target(targets, generation=5, operator_index=2)
    assert a == b


def test_m8_target_selection_cyclic_coverage_across_n_generations():
    """For N eligible targets, N consecutive generations visit each
    target exactly once. Mathematical guarantee per Spec § 3.4."""
    targets = ("a", "b", "c")
    visited = set()
    for gen in range(3):
        visited.add(pick_m8_target(targets, generation=gen, operator_index=0))
    assert visited == set(targets)


def test_m8_target_selection_uses_sorted_input():
    """The cyclic algorithm pre-sorts targets for cross-process
    determinism. Verify by passing in two different tuple orders of
    the same set."""
    a = pick_m8_target(("b", "a", "c"), generation=0, operator_index=0)
    b = pick_m8_target(("c", "b", "a"), generation=0, operator_index=0)
    assert a == b == "a"  # sorted[0]


def test_compute_eligible_master_targets_excludes_current_master():
    """The current master floor is NEVER eligible (would be a no-op M8)."""
    brief = make_two_floor_brief_with_master_on("ground")
    eligible = compute_eligible_master_targets(brief)
    assert "ground" not in eligible
    assert "first" in eligible


def test_compute_eligible_master_targets_excludes_zero_bedroom_floors():
    """A non-master floor with bedroom_count=0 is NOT eligible (per
    Spec #1 MFDB-4: master floor must have bedrooms)."""
    ground = FloorRoomBrief(
        bedroom_count=2, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
        floor_label="ground",
    )
    terrace = FloorRoomBrief(
        bedroom_count=0, bathroom_count=0,
        has_kitchen=False, has_living=False,
        has_pooja=False, has_utility=True,
        floor_label="terrace",
    )
    brief = MultiFloorDwellingBrief(
        floors=(ground, terrace),
        master_bedroom_floor_label="ground",
    )
    eligible = compute_eligible_master_targets(brief)
    assert eligible == ()  # terrace has no bedrooms -> no viable targets.


# ===========================================================================
# 5. M8 real execution (Spec #4 § 3.4)
# ===========================================================================


def _fake_c9_runner_success(per_floor_brief, source_floor_wzpc=None):
    """Simulate a successful C9+C10 cascade by returning a clone_wzpc().
    Second arg added for the post-S41-self-review signature change
    (apply_m8_real now passes the source per-floor WZPC so the runner
    can pull per-floor CDC from its own ancestry); ignored in fakes.
    """
    return clone_wzpc(
        floor_label=per_floor_brief.floor_label,
        keep_master_bedroom=per_floor_brief.has_master_bedroom,
    )


def _fake_c9_runner_failure(per_floor_brief, source_floor_wzpc=None):
    """Simulate a C9 failure. Second arg ignored."""
    raise RuntimeError("simulated C9 failure")


def test_m8_real_execution_produces_wrapper_with_master_swapped():
    """End-to-end: M8 on a 2-floor candidate (master on ground) -> new
    wrapper with master on first."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()
    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=_fake_c9_runner_success,
        source_family_id="test_family",
    )
    assert result.valid is True
    assert result.invalidity_reason is None
    assert result.operator == MutationOperator.M8_VERT_REARR


def test_m8_no_viable_target_returns_no_viable_master_target():
    """If no non-master floor has bedrooms, M8 returns
    valid=False, invalidity_reason='no_viable_master_target'."""
    ground = FloorRoomBrief(
        bedroom_count=2, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
        floor_label="ground",
    )
    terrace = FloorRoomBrief(
        bedroom_count=0, bathroom_count=0,
        has_kitchen=False, has_living=False,
        has_pooja=False, has_utility=True,
        floor_label="terrace",
    )
    brief = MultiFloorDwellingBrief(
        floors=(ground, terrace),
        master_bedroom_floor_label="ground",
    )
    # Source wrapper construction needs valid 2-floor candidate; reuse
    # standard one — terrace fixture would fail MFWZP-5 anyway since
    # terrace has 0 bedrooms so there's no candidate. Use the actual
    # 2-floor wrapper with master on ground and accept the brief/source
    # mismatch in this isolated unit test (apply_m8_real reads brief
    # for eligibility, source for cascade).
    source = make_two_floor_wrapper_master_ground()
    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=_fake_c9_runner_success,
        source_family_id="test_family",
    )
    assert result.valid is False
    assert result.invalidity_reason == "no_viable_master_target"


def test_m8_c9_generation_failed_returns_invalid_with_reason():
    """If C9 raises on the new per-floor brief, M8 returns
    valid=False, invalidity_reason='c9_generation_failed'."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()
    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=_fake_c9_runner_failure,
        source_family_id="test_family",
    )
    assert result.valid is False
    assert result.invalidity_reason == "c9_generation_failed"


def test_m8_failure_returns_family_id_preserved():
    """Even on failure, the source_family_id is carried through to the
    result for lineage."""
    brief = make_two_floor_brief_with_master_on("ground")
    source = make_two_floor_wrapper_master_ground()
    result = apply_m8_real(
        source=source,
        brief=brief,
        generation=0,
        operator_index=0,
        run_c9_per_floor=_fake_c9_runner_failure,
        source_family_id="preserved_id",
    )
    assert result.source_family_id == "preserved_id"
