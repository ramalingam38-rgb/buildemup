"""Tests for C3b schema dataclasses (spec §§ 2 + 7 R-invariants).

Covers dataclass-level invariant enforcement at __post_init__ time:
  R2  advisory-tone lint
  R3  layout grounding
  R4  severity↔mutation_kind discipline
  R5  recommendation_flag is structural Literal
  R6  lex-ASC sort enforcement
  R8  schema-version pin
  R12 Q3 Level B logging (chosen-in-presented)
  R13 topology invariance
  R14 regression detection consistency
  R15 multi-tweak compatibility
  R16 single-linear-history (iteration_index = position)
"""
from __future__ import annotations

import pytest

from buildemup.components.c03b.advisory_lint import AdvisoryLintError
from buildemup.components.c03b.schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)
from buildemup.components.c03b.versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    MAX_REPRESENT_COUNT,
    TWEAKS_PER_LAYOUT_HARD_CEILING,
    TWEAK_COST_IMPACT_CEILING_INR,
)

from tests.test_c03b.fixtures import (
    make_advisory_flag,
    make_apply_outcome,
    make_apply_specification_finish,
    make_apply_specification_geometry,
    make_apply_specification_subset,
    make_compatibility_assertion,
    make_comfort_impact,
    make_finish_schedule_payload,
    make_geometry_local_payload,
    make_kick_back_payload,
    make_mutation_envelope,
    make_resolved_selection,
    make_session_turn,
    make_space_impact,
    make_subset_rerun_request,
    make_topology_invariance_result,
    make_tradeoff_session,
    make_transparency_triple,
    make_tweak_option_light,
    make_tweak_option_medium,
    make_tweak_option_set,
    make_tweak_provenance,
)


# ============================================================
# TopologyInvarianceResult (§ 2.4.2 / R13)
# ============================================================

def test_topology_invariance_result_happy_path():
    tir = make_topology_invariance_result()
    assert tir.invariance_preserved is True


def test_topology_invariance_preserved_inconsistent_with_topologies():
    """preserved=True but source≠predicted → rejected."""
    with pytest.raises(ValueError, match="invariance_preserved"):
        make_topology_invariance_result(
            source_topology="central_spine",
            predicted_topology="l_shape",
            invariance_preserved=True,
            prediction_basis="structural_grid_invariant",
        )


def test_topology_invariance_not_preserved_requires_advisory():
    """Spec § 2.4.2: advisory_note required when invariance broken."""
    with pytest.raises(ValueError, match="advisory_note"):
        make_topology_invariance_result(
            source_topology="central_spine",
            predicted_topology="l_shape",
            invariance_preserved=False,
            prediction_basis="heuristic_strong",
            advisory_note=None,
        )


def test_topology_invariance_heuristic_weak_must_not_preserve():
    """R13 safety bias: weak prediction must bias to HEAVY
    (invariance_preserved=False)."""
    with pytest.raises(ValueError, match="heuristic_weak"):
        make_topology_invariance_result(
            prediction_basis="heuristic_weak",
            invariance_preserved=True,
        )


def test_topology_invariance_with_lint_violation_in_advisory():
    """R2 lint on advisory text."""
    with pytest.raises(AdvisoryLintError):
        make_topology_invariance_result(
            source_topology="central_spine",
            predicted_topology="l_shape",
            invariance_preserved=False,
            prediction_basis="heuristic_strong",
            advisory_note="You should not do this — it's the wrong choice.",
        )


# ============================================================
# CompatibilityAssertion (§ 2.4.3 / R15)
# ============================================================

def test_compatibility_assertion_happy_path():
    ca = make_compatibility_assertion()
    assert ca.result == "compatible"


def test_compatibility_assertion_empty_against_id_rejected():
    with pytest.raises(ValueError, match="against_applied_tweak_id"):
        make_compatibility_assertion(against_applied_tweak_id="")


def test_compatibility_assertion_conflict_requires_advisory():
    """Spec § 2.4.3: advisory_note required when conflicts."""
    with pytest.raises(ValueError, match="advisory_note"):
        make_compatibility_assertion(
            result="conflicts",
            advisory_note=None,
        )


def test_compatibility_assertion_ambiguous_no_advisory_required():
    """Ambiguous is allowed without an advisory."""
    ca = make_compatibility_assertion(result="ambiguous", advisory_note=None)
    assert ca.result == "ambiguous"


# ============================================================
# SubsetRerunRequest (§ 2.4.1 / R13)
# ============================================================

def test_subset_rerun_request_happy_path():
    srr = make_subset_rerun_request()
    assert srr.trigger_tweak_id == "tweak_001"


def test_subset_rerun_request_empty_downstream_impact_rejected():
    """v0.2 spec § 2.4.1: downstream_impact_set MANDATORY non-empty."""
    with pytest.raises(ValueError, match="downstream_impact_set"):
        make_subset_rerun_request(downstream_impact_set=())


def test_subset_rerun_request_empty_components_to_rerun_rejected():
    with pytest.raises(ValueError, match="components_to_rerun"):
        make_subset_rerun_request(components_to_rerun=())


def test_subset_rerun_request_components_must_be_lex_asc():
    """R6 sort discipline."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_subset_rerun_request(
            components_to_rerun=("c12", "c10"),  # out of order
        )


def test_subset_rerun_request_downstream_impact_must_be_lex_asc():
    with pytest.raises(ValueError, match="lex-ASC"):
        make_subset_rerun_request(
            downstream_impact_set=("wet_zone_stacks", "cross_ventilation"),
        )


def test_subset_rerun_request_negative_completion_rejected():
    with pytest.raises(ValueError, match="expected_completion_seconds"):
        make_subset_rerun_request(expected_completion_seconds=-1.0)


def test_subset_rerun_request_empty_anchor_rejected():
    with pytest.raises(ValueError, match="rerun_anchor"):
        make_subset_rerun_request(rerun_anchor="")


def test_subset_rerun_request_carries_topology_check():
    """R13: every MEDIUM tweak carries TopologyInvarianceResult."""
    srr = make_subset_rerun_request()
    assert srr.topology_invariance_check is not None


# ============================================================
# KickBackPayload + MutationEnvelope (§ 2.8)
# ============================================================

def test_kickback_payload_happy_path():
    kbp = make_kick_back_payload()
    assert kbp.target_brief_field == "room_program"


def test_kickback_payload_empty_advisory_rejected():
    with pytest.raises(ValueError, match="target_brief_field_advisory"):
        make_kick_back_payload(target_brief_field_advisory="")


def test_kickback_payload_lint_violation():
    with pytest.raises(AdvisoryLintError):
        make_kick_back_payload(
            target_brief_field_advisory="You should accept this change.",
        )


def test_mutation_envelope_happy_path():
    me = make_mutation_envelope()
    assert me.classification == "brief_level_change"
    assert me.kick_back_payload is not None


def test_mutation_envelope_brief_change_requires_kickback():
    """Spec § 2.8: classification=brief_level_change ↔ kick_back_payload set."""
    with pytest.raises(ValueError, match="kick_back_payload"):
        make_mutation_envelope(
            classification="brief_level_change",
            kick_back_payload=None,
        )


def test_mutation_envelope_non_brief_must_omit_kickback():
    with pytest.raises(ValueError, match="kick_back_payload"):
        make_mutation_envelope(
            classification="topology_level_change",
            kick_back_payload=make_kick_back_payload(),
        )


def test_mutation_envelope_lint_violation_in_advisory():
    with pytest.raises(AdvisoryLintError):
        make_mutation_envelope(advisory_note="You must accept this.")


def test_mutation_envelope_lint_violation_in_why_not():
    with pytest.raises(AdvisoryLintError):
        make_mutation_envelope(why_not_a_tweak="You should pick a different tweak.")


# ============================================================
# SpaceImpact (§ 2.7)
# ============================================================

def test_space_impact_happy_path():
    si = make_space_impact()
    assert si.total_sqft_delta == 0.0


def test_space_impact_per_room_must_be_lex_asc():
    """R6: lex-ASC by room_id."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_space_impact(
            per_room_sqft_delta=(("room_002", 5.0), ("room_001", -5.0)),
        )


def test_space_impact_exceeds_tweak_ceiling_rejected():
    """Spec § 6: |total_sqft_delta| ≤ 150 sqft per tweak."""
    with pytest.raises(ValueError, match="ceiling"):
        make_space_impact(total_sqft_delta=200.0)


def test_space_impact_negative_below_ceiling_allowed():
    """The ceiling is on |delta|, not on sign."""
    si = make_space_impact(total_sqft_delta=-100.0)
    assert si.total_sqft_delta == -100.0


def test_space_impact_lint_violation_in_advisory():
    """R2 wiring at construction."""
    with pytest.raises(AdvisoryLintError):
        make_space_impact(advisory_note="You should accept this rebalancing.")


# ============================================================
# ComfortImpact (§ 2.7)
# ============================================================

def test_comfort_impact_happy_path():
    ci = make_comfort_impact()
    assert ci.direction == "improves"


def test_comfort_impact_dimensions_must_be_non_empty():
    with pytest.raises(ValueError, match="dimensions_affected"):
        make_comfort_impact(dimensions_affected=())


def test_comfort_impact_dimensions_must_be_sorted():
    """R6 sort."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_comfort_impact(
            dimensions_affected=("natural_light", "cross_ventilation"),  # wrong order
        )


def test_comfort_impact_lint_violation_in_advisory():
    """R2 wiring."""
    with pytest.raises(AdvisoryLintError):
        make_comfort_impact(advisory_note="Best choice for this room.")


# ============================================================
# Payload types (§ 2.4)
# ============================================================

def test_geometry_local_payload_happy_path():
    glp = make_geometry_local_payload()
    assert len(glp.new_room_function_assignments) == 1


def test_geometry_local_payload_lint_violation_in_advisory():
    """R2 wiring."""
    with pytest.raises(AdvisoryLintError):
        make_geometry_local_payload(advisory_note="You should approve this.")


def test_finish_schedule_payload_empty_overrides_rejected():
    with pytest.raises(ValueError, match="room_finish_overrides"):
        make_finish_schedule_payload(room_finish_overrides=())


def test_finish_schedule_payload_lint_violation_in_advisory():
    """R2 wiring."""
    with pytest.raises(AdvisoryLintError):
        make_finish_schedule_payload(
            advisory_note="Best tweak for the master bedroom.",
        )


def test_finish_schedule_payload_must_be_sorted():
    with pytest.raises(ValueError, match="lex-ASC"):
        make_finish_schedule_payload(
            room_finish_overrides=(
                ("room_002", "flooring", "x"),
                ("room_001", "flooring", "y"),
            ),
        )


# ============================================================
# ApplySpecification (§ 2.4 / R4)
# ============================================================

def test_apply_spec_geometry_happy_path():
    asp = make_apply_specification_geometry()
    assert asp.mutation_kind == "geometry_local"


def test_apply_spec_must_have_exactly_one_payload():
    """R4: exactly one payload field set."""
    with pytest.raises(ValueError, match="exactly one"):
        ApplySpecification(
            mutation_kind="geometry_local",
            geometry_local_payload=None,
            subset_rerun_payload=None,
            finish_schedule_payload=None,
        )


def test_apply_spec_two_payloads_set_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        ApplySpecification(
            mutation_kind="geometry_local",
            geometry_local_payload=make_geometry_local_payload(),
            subset_rerun_payload=make_subset_rerun_request(),
            finish_schedule_payload=None,
        )


def test_apply_spec_kind_must_match_payload():
    """mutation_kind='subset_rerun' but only geometry payload set."""
    with pytest.raises(ValueError, match="payload field is None"):
        ApplySpecification(
            mutation_kind="subset_rerun",
            geometry_local_payload=make_geometry_local_payload(),
            subset_rerun_payload=None,
            finish_schedule_payload=None,
        )


# ============================================================
# TweakProvenance (§ 2.2)
# ============================================================

def test_tweak_provenance_happy_path():
    tp = make_tweak_provenance()
    assert tp.motivated_by_check_id == "check_001"


def test_tweak_provenance_requires_at_least_one_motivation():
    """Spec § 2.2: every tweak traces back to a check / cell / orientation."""
    with pytest.raises(ValueError, match="motivation source"):
        TweakProvenance(
            motivated_by_check_id=None,
            motivated_by_grid_cell_id=None,
            motivated_by_orientation=None,
            generation_basis="orphan",
        )


def test_tweak_provenance_requires_generation_basis():
    with pytest.raises(ValueError, match="generation_basis"):
        TweakProvenance(
            motivated_by_check_id="check_001",
            generation_basis="",
        )


# ============================================================
# TweakOption (§ 2.3 / R3 + R4 + R9)
# ============================================================

def test_tweak_option_light_happy_path():
    to = make_tweak_option_light()
    assert to.severity_tier == "light"


def test_tweak_option_medium_happy_path():
    to = make_tweak_option_medium()
    assert to.severity_tier == "medium"


def test_tweak_option_heavy_severity_rejected():
    """R4: HEAVY tweaks are never surfaced as TweakOptions."""
    with pytest.raises(ValueError, match="heavy"):
        make_tweak_option_light(severity_tier="heavy")


def test_tweak_option_no_layout_grounding_rejected():
    """R3 + R9: at least one of room_ids / grid_cells must be non-empty."""
    with pytest.raises(ValueError, match="layout grounding"):
        make_tweak_option_light(
            affected_room_ids=(),
            affected_grid_cells=(),
        )


def test_tweak_option_either_grounding_alone_is_ok():
    """Grid cells alone is enough."""
    to = make_tweak_option_light(
        affected_room_ids=(),
        affected_grid_cells=("cell_001",),
    )
    assert to.affected_grid_cells == ("cell_001",)


def test_tweak_option_affected_rooms_must_be_sorted():
    with pytest.raises(ValueError, match="lex-ASC"):
        make_tweak_option_light(affected_room_ids=("room_b", "room_a"))


def test_tweak_option_light_cannot_use_subset_rerun():
    """R4: LIGHT severity NEVER uses subset_rerun mutation_kind."""
    with pytest.raises(ValueError, match="subset_rerun"):
        make_tweak_option_light(
            apply_specification=make_apply_specification_subset(),
        )


def test_tweak_option_medium_must_use_subset_rerun():
    """R4: MEDIUM severity MUST use subset_rerun mutation_kind."""
    with pytest.raises(ValueError, match="subset_rerun"):
        make_tweak_option_medium(
            apply_specification=make_apply_specification_geometry(),
        )


def test_tweak_option_medium_with_broken_invariance_rejected():
    """R13: MEDIUM with invariance_preserved=False would be auto-HEAVY."""
    broken_tir = make_topology_invariance_result(
        source_topology="central_spine",
        predicted_topology="l_shape",
        invariance_preserved=False,
        prediction_basis="heuristic_strong",
        advisory_note="Topology would change; routing to HEAVY.",
    )
    broken_srr = make_subset_rerun_request(topology_invariance_check=broken_tir)
    broken_asp = make_apply_specification_subset(subset_rerun_payload=broken_srr)
    with pytest.raises(ValueError, match="R13"):
        make_tweak_option_medium(apply_specification=broken_asp)


def test_tweak_option_present_count_exceeds_max():
    """MAX_REPRESENT_COUNT discipline."""
    with pytest.raises(ValueError, match="MAX_REPRESENT_COUNT"):
        make_tweak_option_light(presented_count=MAX_REPRESENT_COUNT + 1)


def test_tweak_option_negative_present_count_rejected():
    with pytest.raises(ValueError, match="presented_count"):
        make_tweak_option_light(presented_count=-1)


def test_tweak_option_cost_impact_ceiling():
    """Spec § 6: cost impact > ₹20 lakh → not a tweak, brief-level."""
    too_expensive = make_transparency_triple(
        exact_value=TWEAK_COST_IMPACT_CEILING_INR + 1.0,
    )
    with pytest.raises(ValueError, match="ceiling"):
        make_tweak_option_light(cost_impact=too_expensive)


def test_tweak_option_empty_description_rejected():
    with pytest.raises(ValueError, match="description"):
        make_tweak_option_light(description="")


def test_tweak_option_lint_violation_in_description():
    """R2 in description."""
    with pytest.raises(AdvisoryLintError):
        make_tweak_option_light(
            description="You should move the kitchen east.",
        )


# ============================================================
# TweakOptionSet (§ 2.2)
# ============================================================

def test_tweak_option_set_happy_path():
    tos = make_tweak_option_set()
    assert tos.layout_archetype == "cost_efficient"
    assert len(tos.tweaks) == 2


def test_tweak_option_set_too_many_tweaks_rejected():
    """Hard ceiling: 8 tweaks/layout (TWEAKS_PER_LAYOUT_HARD_CEILING)."""
    too_many = tuple(
        make_tweak_option_light(tweak_id=f"tweak_{i:03d}")
        for i in range(TWEAKS_PER_LAYOUT_HARD_CEILING + 1)
    )
    with pytest.raises(ValueError, match="hard ceiling"):
        make_tweak_option_set(tweaks=too_many)


def test_tweak_option_set_tweaks_must_be_sorted():
    """R6: lex-ASC by tweak_id."""
    out_of_order = (
        make_tweak_option_light(tweak_id="tweak_z"),
        make_tweak_option_light(tweak_id="tweak_a"),
    )
    with pytest.raises(ValueError, match="lex-ASC"):
        make_tweak_option_set(tweaks=out_of_order)


def test_tweak_option_set_duplicate_ids_rejected():
    dupes = (
        make_tweak_option_light(tweak_id="tweak_same"),
        make_tweak_option_light(tweak_id="tweak_same"),
    )
    with pytest.raises(ValueError, match="duplicate"):
        make_tweak_option_set(tweaks=dupes)


def test_tweak_option_set_lint_violation_in_advisory():
    with pytest.raises(AdvisoryLintError):
        make_tweak_option_set(
            overall_advisory_note="You should accept these tweaks.",
        )


# ============================================================
# ApplyOutcome (§ 2.7 / R14)
# ============================================================

def test_apply_outcome_happy_path():
    ao = make_apply_outcome()
    assert ao.apply_status == "applied_successfully"


def test_apply_outcome_regression_with_no_critical_ids_rejected():
    """R14 consistency: regression_detected=True ↔ non-empty list."""
    with pytest.raises(ValueError, match="regression_detected"):
        make_apply_outcome(
            regression_detected=True,
            newly_critical_check_ids=(),
        )


def test_apply_outcome_no_regression_with_critical_ids_rejected():
    with pytest.raises(ValueError, match="newly_critical"):
        make_apply_outcome(
            regression_detected=False,
            newly_critical_check_ids=("check_x",),
        )


def test_apply_outcome_critical_ids_must_be_sorted():
    """R6."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_apply_outcome(
            regression_detected=True,
            newly_critical_check_ids=("check_z", "check_a"),
        )


def test_apply_outcome_rerun_failed_requires_error_summary():
    with pytest.raises(ValueError, match="error_summary"):
        make_apply_outcome(apply_status="rerun_failed", error_summary=None)


# ============================================================
# SessionTurn (§ 2.5 / R7d / R12 / Q3 Level B)
# ============================================================

def test_session_turn_happy_path():
    st = make_session_turn()
    assert st.user_action == "accepted_tweak"


def test_session_turn_presented_must_be_sorted():
    """R6."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_session_turn(presented_tweaks=("tweak_z", "tweak_a"))


def test_session_turn_chosen_must_be_in_presented():
    """Q3 Level B: chosen_tweak_id ∈ presented_tweaks."""
    with pytest.raises(ValueError, match="Q3 Level B"):
        make_session_turn(
            presented_tweaks=("tweak_001", "tweak_002"),
            chosen_tweak_id="tweak_xxx",  # not in presented!
        )


def test_session_turn_accepted_requires_chosen():
    """user_action=accepted_tweak → chosen_tweak_id non-None."""
    with pytest.raises(ValueError, match="chosen_tweak_id"):
        make_session_turn(
            user_action="accepted_tweak",
            chosen_tweak_id=None,
            apply_outcome=None,
        )


def test_session_turn_finalized_must_have_no_chosen():
    """user_action=finalized_layout_choice → chosen_tweak_id None."""
    with pytest.raises(ValueError, match="chosen_tweak_id"):
        make_session_turn(
            user_action="finalized_layout_choice",
            chosen_tweak_id="tweak_001",
            apply_outcome=None,
        )


def test_session_turn_accepted_requires_apply_outcome():
    with pytest.raises(ValueError, match="apply_outcome"):
        make_session_turn(
            user_action="accepted_tweak",
            chosen_tweak_id="tweak_001",
            apply_outcome=None,
        )


def test_session_turn_negative_timestamp_rejected():
    """R7d: timestamp_offset_ms is relative (≥0)."""
    with pytest.raises(ValueError, match="timestamp_offset_ms"):
        make_session_turn(timestamp_offset_ms=-1)


# ============================================================
# ResolvedSelection (§ 2.6)
# ============================================================

def test_resolved_selection_happy_path():
    rs = make_resolved_selection()
    assert rs.chosen_layout_archetype == "everyday_living"


def test_resolved_selection_applied_tweaks_must_be_sorted():
    """R6."""
    with pytest.raises(ValueError, match="lex-ASC"):
        make_resolved_selection(applied_tweaks=("tweak_z", "tweak_a"))


def test_resolved_selection_empty_advisory_rejected():
    with pytest.raises(ValueError, match="final_handoff_advisory"):
        make_resolved_selection(final_handoff_advisory="")


def test_resolved_selection_lint_violation_in_advisory():
    with pytest.raises(AdvisoryLintError):
        make_resolved_selection(
            final_handoff_advisory="You should accept this layout.",
        )


# ============================================================
# AdvisoryFlag
# ============================================================

def test_advisory_flag_happy_path():
    af = make_advisory_flag()
    assert af.kind == "compatibility_ambiguous"


def test_advisory_flag_lint_violation():
    with pytest.raises(AdvisoryLintError):
        make_advisory_flag(advisory_note="The system decided this for you.")


def test_advisory_flag_related_ids_must_be_sorted():
    with pytest.raises(ValueError, match="lex-ASC"):
        make_advisory_flag(related_ids=("tweak_z", "tweak_a"))


# ============================================================
# TradeoffSession (§ 2.1 / R8 / R16)
# ============================================================

def test_tradeoff_session_happy_path():
    ts = make_tradeoff_session()
    assert ts.current_status == "open_for_user_input"


def test_tradeoff_session_wrong_schema_version_rejected():
    """R8: c3b_schema_version must match constant."""
    with pytest.raises(ValueError, match="R8 schema-version"):
        make_tradeoff_session(c3b_schema_version=C3B_SESSION_SCHEMA_VERSION + 99)


def test_tradeoff_session_iteration_cap_too_high_rejected():
    with pytest.raises(ValueError, match="iteration_cap"):
        make_tradeoff_session(iteration_cap=999)


def test_tradeoff_session_resolved_status_requires_resolved_selection():
    with pytest.raises(ValueError, match="resolved_selection"):
        make_tradeoff_session(
            current_status="resolved_selection_ready",
            resolved_selection=None,
        )


def test_tradeoff_session_history_iteration_index_must_match_position():
    """R16 single-linear-history: turn[i].iteration_index == i."""
    # Wrong iteration_index for position 0
    bad_turn = make_session_turn(iteration_index=5)
    with pytest.raises(ValueError, match="R16"):
        make_tradeoff_session(session_history=(bad_turn,))


def test_tradeoff_session_tweak_sets_must_be_sorted():
    """R6 lex-ASC by layout_id."""
    set_a = make_tweak_option_set(layout_id="layout_z")
    set_b = make_tweak_option_set(
        layout_id="layout_a",
        tweaks=(make_tweak_option_light("tweak_003"),),
    )
    with pytest.raises(ValueError, match="lex-ASC"):
        make_tradeoff_session(tweak_option_sets=(set_a, set_b))


def test_tradeoff_session_advisory_flags_must_be_sorted():
    flag_a = make_advisory_flag(flag_id="flag_z")
    flag_b = make_advisory_flag(flag_id="flag_a")
    with pytest.raises(ValueError, match="lex-ASC"):
        make_tradeoff_session(advisory_flags=(flag_a, flag_b))


def test_tradeoff_session_mutation_envelopes_must_be_sorted():
    e1 = make_mutation_envelope(envelope_id="env_z")
    e2 = make_mutation_envelope(envelope_id="env_a")
    with pytest.raises(ValueError, match="lex-ASC"):
        make_tradeoff_session(mutation_envelopes=(e1, e2))


def test_tradeoff_session_with_proper_history_ok():
    """Happy path: turns aligned with position."""
    t0 = make_session_turn(iteration_index=0, turn_id="turn_000")
    t1 = make_session_turn(iteration_index=1, turn_id="turn_001")
    ts = make_tradeoff_session(session_history=(t0, t1))
    assert len(ts.session_history) == 2
