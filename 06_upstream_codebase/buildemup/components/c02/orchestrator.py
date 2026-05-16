"""
Component 2 — Feasibility orchestrator (Session G).

The single entry point for running Component 2: takes a Brief (and
optional FeasibilityInput + C7 cost estimate) and returns a complete
DesignGapAnalysis containing both lanes' reports + gaps.

Public API:
  run_feasibility(brief, c7_cost_estimate=None,
                  feasibility_input=None) -> DesignGapAnalysis

Architecture:
  - 10 unbranched checks run ONCE, appear in BOTH lane reports
  - 6 branched checks run TWICE (practical_fn + code_strict_fn)
  - 1 info-only check (approval complexity) runs ONCE, appears in both
  - Total checks per lane: 10 + 6 + 1 = 17 (room minimums deferred)
  - Both lane reports use compute_overall_score() for consistency

Cost delta computation:
  Code-Strict design adds ~₹15K-2.6L depending on which gaps surface:
    Soil test (₹10K)        — if soil_type gap present
    Water table verify (₹5K) — if water_table gap present
    RWH installation (₹100K) — if RWH gap present (city doesn't mandate)
  These are conservative aggregates. v0.2 will refine with builder data.

Unknown aggregation:
  Walks practical-lane check results, collects those with
  assumption_used set, dedupes by field_name, builds Unknown list.

ActionStep generation:
  From practical-lane blocking_issues + soft_warnings, generates
  ActionStep instances with triggering_check_ids. Session H will
  refine the action prose with priority + concrete next steps.
"""
from __future__ import annotations
from typing import Any

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    DesignVariant, DesignGapAnalysis, FeasibilityReport,
    CheckResult, CheckSeverity, ConfidenceLevel,
    Unknown, ActionStep, VerificationPriority, Gap,
)
from buildemup.components.c02.scoring import compute_overall_score
from buildemup.components.c02.feasibility_input import FeasibilityInput

# Imports for the 17 checks
from buildemup.components.c02.hard_physics_checks import (
    check_envelope_sufficiency, check_floor_stack_feasibility,
    check_parking_width, check_budget_feasibility,
)
from buildemup.components.c02.legal_only_checks import (
    check_far_compliance, check_ground_coverage_compliance,
    check_fire_tender_access, check_electric_line_clearance,
    check_water_course_clearance, check_stilt_mandate_compliance,
)
from buildemup.components.c02.branched_checks import (
    check_setback_compliance_practical,
    check_setback_compliance_code_strict,
    check_solar_exposure_practical, check_solar_exposure_code_strict,
    check_cross_ventilation_practical,
    check_cross_ventilation_code_strict,
    compute_setback_gap, compute_solar_gap, compute_ventilation_gap,
)
from buildemup.components.c02.site_input_checks import (
    check_soil_type_practical, check_soil_type_code_strict,
    check_water_table_practical, check_water_table_code_strict,
    compute_soil_type_gap, compute_water_table_gap,
)
from buildemup.components.c02.sustainability_checks import (
    check_rwh_practical, check_rwh_code_strict,
    check_approval_complexity, compute_rwh_gap,
)


# ─── Cost delta constants ─────────────────────────────────────────────
# Conservative aggregate estimates for Code-Strict additions.
# Builders' quotes vary; these are mid-point estimates for the verifications
# + installations Code-Strict would add.

CODE_STRICT_COST_ADDERS_LAKHS: dict[str, float] = {
    "soil_type": 0.10,        # NABL geotech lab test ₹10K
    "water_table": 0.05,      # Hydrogeologist verification ₹5K
    "rwh": 1.0,               # RWH installation if not city-mandated ₹1L
    # Other gaps (setback, solar, ventilation) impose redesign cost,
    # which is too variable to estimate here. Reported qualitatively.
}


# ─── Helper: build the report for one variant ─────────────────────────

def _build_report_for_variant(
    variant: DesignVariant,
    check_results: tuple[CheckResult, ...],
    cost_estimate: Any,
    unknowns: tuple[Unknown, ...],
    action_steps: tuple[ActionStep, ...],
) -> FeasibilityReport:
    """Build a FeasibilityReport given the check results + supporting data.

    Splits results by severity into the 4 buckets, computes overall score
    + breakdown via compute_overall_score, derives is_feasible properties
    from blocking_issues.
    """
    blocking = tuple(
        r for r in check_results if r.severity == CheckSeverity.HARD_FAIL
    )
    soft = tuple(
        r for r in check_results if r.severity == CheckSeverity.SOFT_WARN
    )
    passed = tuple(
        r for r in check_results if r.severity == CheckSeverity.PASS
    )
    not_applicable = tuple(
        r for r in check_results
        if r.severity == CheckSeverity.NOT_APPLICABLE
    )

    score, breakdown = compute_overall_score(check_results)

    # On first run, all blocking issues are unaccepted by default
    # (Session H+ will populate user acceptances via post-report iteration)
    unaccepted = blocking

    return FeasibilityReport(
        variant=variant,
        overall_score=score,
        score_breakdown=breakdown,
        blocking_issues=blocking,
        unaccepted_blocking_issues=unaccepted,
        soft_warnings=soft,
        passed_checks=passed,
        not_applicable_checks=not_applicable,
        cost_estimate=cost_estimate,
        unknowns=unknowns,
        action_steps=action_steps,
    )


# ─── Helper: extract unknowns from check results ──────────────────────

def _extract_unknowns(
    check_results: tuple[CheckResult, ...],
    feasibility_input: FeasibilityInput,
) -> tuple[Unknown, ...]:
    """Aggregate Unknown records from check results that used assumptions.

    Walks the check results, finds those with assumption_used set,
    pairs them with the FeasibilityInput field that was unknown, and
    builds Unknown records linking them.

    Dedupes by field_name — each unknown field appears once even if
    multiple checks used its assumed value.
    """
    # Map check_id → field_name relationship
    # (Some checks use multiple fields, but for v0.1 each unknown maps
    #  cleanly to one field)
    check_to_field = {
        "soil_type_practical": "soil_type",
        "soil_type_code_strict": "soil_type",
        "water_table_practical": "water_table_depth_m",
        "water_table_code_strict": "water_table_depth_m",
        "electric_line_clearance": "distance_from_electric_line_m",
        "water_course_clearance": "distance_from_water_course_m",
    }

    # Collect which fields were assumed AND which checks they affected
    field_to_assumption: dict[str, str] = {}
    field_to_checks: dict[str, list[str]] = {}
    field_to_recommendation: dict[str, str] = {}
    field_to_priority: dict[str, VerificationPriority] = {}

    for check in check_results:
        if check.assumption_used is None:
            continue
        field_name = check_to_field.get(check.check_id)
        if field_name is None:
            continue
        if field_name not in field_to_assumption:
            field_to_assumption[field_name] = check.assumption_used
            field_to_checks[field_name] = []
            field_to_recommendation[field_name] = (
                check.verification_recommendation or ""
            )
            field_to_priority[field_name] = check.verification_priority
        field_to_checks[field_name].append(check.check_id)
        # Escalate priority if any check rated higher
        if check.verification_priority.value == "critical":
            field_to_priority[field_name] = VerificationPriority.CRITICAL
        elif (check.verification_priority.value == "important" and
              field_to_priority[field_name].value != "critical"):
            field_to_priority[field_name] = VerificationPriority.IMPORTANT

    # Build Unknown records
    unknowns_list = []
    for field_name, assumption in field_to_assumption.items():
        # Try to get user_facing_question from feasibility_input
        user_q = ""
        if hasattr(feasibility_input, field_name):
            input_field = getattr(feasibility_input, field_name)
            user_q = getattr(input_field, "user_facing_question", "")

        unknowns_list.append(Unknown(
            field_name=field_name,
            user_facing_question=user_q,
            assumed_value=assumption,
            affects_check_ids=tuple(field_to_checks[field_name]),
            verification_recommendation=field_to_recommendation[field_name],
            priority=field_to_priority[field_name],
        ))

    return tuple(unknowns_list)


# ─── Helper: generate action steps from check results ─────────────────

def _generate_action_steps(
    check_results: tuple[CheckResult, ...],
) -> tuple[ActionStep, ...]:
    """Generate ActionStep records from blocking + soft-warn check results.

    Each ActionStep links to the triggering check_ids. Session H will
    refine the prose with priority + concrete next-step text.

    Priority assignment (1 = highest):
      1 — HARD_FAIL with HIGH confidence (true blockers)
      2 — HARD_FAIL with MEDIUM/LOW (assumed-blocker cases)
      3 — SOFT_WARN with HIGH (real concerns)
      4 — SOFT_WARN with MEDIUM/LOW (advisory)
    """
    actions = []
    for check in check_results:
        if check.severity == CheckSeverity.HARD_FAIL:
            priority = 1 if check.confidence == ConfidenceLevel.HIGH else 2
            step_text = f"[BLOCKING] {check.check_name}: {check.message}"
            actions.append(ActionStep(
                step_text=step_text,
                triggering_check_ids=(check.check_id,),
                priority=priority,
            ))
        elif check.severity == CheckSeverity.SOFT_WARN:
            priority = 3 if check.confidence == ConfidenceLevel.HIGH else 4
            step_text = f"[ATTENTION] {check.check_name}: {check.message}"
            actions.append(ActionStep(
                step_text=step_text,
                triggering_check_ids=(check.check_id,),
                priority=priority,
            ))
    return tuple(actions)


# ─── Helper: compute cost delta ───────────────────────────────────────

def _compute_cost_delta_lakhs(gaps: tuple[Gap, ...]) -> float:
    """Compute the additional cost (lakhs ₹) of choosing Code-Strict
    over Practical, based on which gaps are present.

    Returns sum of CODE_STRICT_COST_ADDERS_LAKHS for each gap whose
    check_id maps to a known cost adder. Other gaps add qualitative
    redesign cost not estimated here.
    """
    total = 0.0
    for gap in gaps:
        adder = CODE_STRICT_COST_ADDERS_LAKHS.get(gap.check_id)
        if adder is not None:
            total += adder
    return round(total, 2)


# ─── Helper: build user-decisions list ────────────────────────────────

def _build_user_decisions_required(gaps: tuple[Gap, ...]) -> tuple[str, ...]:
    """Build human-readable list of decisions the user needs to make.

    For each non-INFO gap, generates a yes/no question for the user to
    answer in the post-report iteration UI.
    """
    decisions = []
    for gap in gaps:
        if gap.severity.value == "info_only":
            continue  # INFO doesn't need a decision
        decisions.append(
            f"For '{gap.check_id}': accept {gap.severity.value} compromise "
            f"({gap.impact_description[:80]}...)?"
        )
    return tuple(decisions)


# ─── Public API ───────────────────────────────────────────────────────

def run_feasibility(
    brief: Brief,
    c7_cost_estimate: Any = None,
    feasibility_input: FeasibilityInput | None = None,
    distance_from_electric_line_m: float | None = None,
    electric_line_type: str = "unknown",
    distance_from_water_course_m: float | None = None,
    has_water_course_within_30m: bool | None = None,
) -> DesignGapAnalysis:
    """Run all 17 v0.1 feasibility checks and return DesignGapAnalysis.

    Args:
        brief: The captured Brief from Component 1.
        c7_cost_estimate: Optional TransparencyTriple from C7 (cost engine).
        feasibility_input: Optional FeasibilityInput for soil + water table
            data. If None, defaults are constructed (all NOT_ASKED).
        distance_from_electric_line_m, electric_line_type,
        distance_from_water_course_m, has_water_course_within_30m:
            Optional overrides for legal-only checks that haven't been
            converted to FeasibilityInput pattern yet (Session B
            placeholders — to be unified in v0.2).

    Returns:
        DesignGapAnalysis containing:
          - practical_report (with all 17 checks under Practical lens)
          - code_strict_report (with all 17 checks under CodeStrict lens)
          - gaps (Gap instances for the 6 branched checks where divergent)
          - cost_delta_lakhs (estimated additional cost of Code-Strict)
          - user_decisions_required (questions for post-report iteration)
    """
    # Default feasibility_input if not provided
    if feasibility_input is None:
        feasibility_input = FeasibilityInput(brief=brief)

    # ── Run unbranched checks ONCE (appear in both reports) ───────────
    envelope = check_envelope_sufficiency(brief)
    floor_stack = check_floor_stack_feasibility(brief)
    parking = check_parking_width(brief)
    budget = check_budget_feasibility(brief, c7_cost_estimate)
    far = check_far_compliance(brief)
    gc = check_ground_coverage_compliance(brief)
    fire = check_fire_tender_access(brief)
    elec = check_electric_line_clearance(
        brief,
        distance_from_electric_line_m=distance_from_electric_line_m,
        line_type=electric_line_type,
    )
    water_course = check_water_course_clearance(
        brief,
        distance_from_water_course_m=distance_from_water_course_m,
        has_water_course_within_30m=has_water_course_within_30m,
    )
    stilt = check_stilt_mandate_compliance(brief)
    approval = check_approval_complexity(brief)

    unbranched_results = (
        envelope, floor_stack, parking, budget,
        far, gc, fire, elec, water_course, stilt,
        approval,
    )

    # ── Run branched checks for both lanes ────────────────────────────
    # Practical lane
    setback_p = check_setback_compliance_practical(brief)
    solar_p = check_solar_exposure_practical(brief)
    vent_p = check_cross_ventilation_practical(brief)
    soil_p = check_soil_type_practical(feasibility_input)
    wt_p = check_water_table_practical(feasibility_input)
    rwh_p = check_rwh_practical(brief)

    # Code-Strict lane
    setback_c = check_setback_compliance_code_strict(brief)
    solar_c = check_solar_exposure_code_strict(brief)
    vent_c = check_cross_ventilation_code_strict(brief)
    soil_c = check_soil_type_code_strict(feasibility_input)
    wt_c = check_water_table_code_strict(feasibility_input)
    rwh_c = check_rwh_code_strict(brief)

    practical_results = unbranched_results + (
        setback_p, solar_p, vent_p, soil_p, wt_p, rwh_p,
    )
    code_strict_results = unbranched_results + (
        setback_c, solar_c, vent_c, soil_c, wt_c, rwh_c,
    )

    # ── Compute gaps (only for branched checks) ───────────────────────
    raw_gaps = (
        compute_setback_gap(brief),
        compute_solar_gap(brief),
        compute_ventilation_gap(brief),
        compute_soil_type_gap(feasibility_input),
        compute_water_table_gap(feasibility_input),
        compute_rwh_gap(brief),
    )
    gaps = tuple(g for g in raw_gaps if g is not None)

    # ── Aggregate unknowns + action steps (from practical lane) ───────
    unknowns = _extract_unknowns(practical_results, feasibility_input)
    practical_actions = _generate_action_steps(practical_results)
    code_strict_actions = _generate_action_steps(code_strict_results)

    # ── Build the two reports ─────────────────────────────────────────
    practical_report = _build_report_for_variant(
        DesignVariant.PRACTICAL,
        practical_results,
        c7_cost_estimate,
        unknowns,
        practical_actions,
    )
    code_strict_report = _build_report_for_variant(
        DesignVariant.CODE_STRICT,
        code_strict_results,
        c7_cost_estimate,
        unknowns,        # Same unknowns appear in both reports
        code_strict_actions,
    )

    # ── Compute cost delta + decisions ────────────────────────────────
    cost_delta = _compute_cost_delta_lakhs(gaps)
    decisions = _build_user_decisions_required(gaps)

    return DesignGapAnalysis(
        practical_report=practical_report,
        code_strict_report=code_strict_report,
        gaps=gaps,
        cost_delta_lakhs=cost_delta,
        user_decisions_required=decisions,
    )
