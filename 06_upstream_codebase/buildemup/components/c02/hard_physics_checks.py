"""
Component 2 — Hard-physics checks (Session A scope).

These 4 checks have NO Practical-vs-CodeStrict split because they're
governed by physics or money, not by adjustable code interpretation:

  - envelope_sufficiency: rooms physically fit in buildable area?
  - floor_stack: total area sane after staircase deduction?
  - parking_width: car physically fits given setbacks?
  - budget: user's budget vs C7 cost range?

These run identically for both DesignVariant.PRACTICAL and CODE_STRICT,
so the orchestrator can call them once and reuse the result for both.

Each check returns a CheckResult with:
  - severity (HARD_FAIL / SOFT_WARN / PASS / NOT_APPLICABLE)
  - confidence (HIGH for these — physics is verified by the user's plot data)
  - score_contribution computed via scoring.compute_score_contribution
  - common_doubts surfaced when severity != PASS

Future Sessions: 14 more checks across Sessions B-F.
"""
from __future__ import annotations

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority,
)
from buildemup.components.c02.scoring import compute_score_contribution


# ─── Constants ────────────────────────────────────────────────────────
# Sources cited inline for traceability (per v0.9.1 KB-version pattern).

CIRCULATION_FACTOR = 1.35
"""Walls + horizontal + vertical circulation overhead per IS 3861-2002.
Same factor used by Component 1's room_composer for consistency."""

STAIRCASE_AREA_PER_FLOOR_SQM = 4.0
"""Typical 1.0m × 4.0m staircase footprint per IS 3861-2002 + NBC Part 3.
Conservative; an actual layout may be 3-5 sqm depending on design."""

PARKING_CAR_WIDTH_M = 2.5
"""Standard car bay width per NBC + IS 11268. Excludes circulation."""

PARKING_CIRCULATION_M = 0.5
"""Door-opening + walking allowance on each side of car."""

PARKING_MIN_INTERNAL_WIDTH_M = (
    PARKING_CAR_WIDTH_M + 2 * PARKING_CIRCULATION_M
)  # = 3.5m absolute physical minimum for one car


# ─── Helper: build standard CheckResult ───────────────────────────────

def _build_result(
    *,
    check_id: str,
    check_name: str,
    severity: CheckSeverity,
    message: str,
    details: dict,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    confidence_reason: str | None = None,
    assumption_used: str | None = None,
    verification_recommendation: str | None = None,
    verification_priority: VerificationPriority = VerificationPriority.OPTIONAL,
    common_doubts: tuple[str, ...] = (),
    category: CheckCategory = CheckCategory.SPATIAL,
) -> CheckResult:
    """Build a CheckResult with the score_contribution auto-filled.

    score_contribution depends on severity + confidence per scoring.py.
    Building a temporary CheckResult to compute contribution then
    rebuilding the final one with the right value (since dataclass is
    frozen, we can't mutate).
    """
    # Build a temp result with placeholder score=0 so we can call
    # compute_score_contribution; then build the real one.
    temp = CheckResult(
        check_id=check_id,
        check_name=check_name,
        category=category,
        severity=severity,
        confidence=confidence,
        confidence_reason=confidence_reason,
        score_contribution=0,  # placeholder
        message=message,
        details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )
    contribution = compute_score_contribution(temp)
    # Rebuild with the correct contribution (frozen dataclass — must
    # build new instance)
    return CheckResult(
        check_id=check_id,
        check_name=check_name,
        category=category,
        severity=severity,
        confidence=confidence,
        confidence_reason=confidence_reason,
        score_contribution=contribution,
        message=message,
        details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )


# ─── Check #1: Envelope sufficiency ───────────────────────────────────

def check_envelope_sufficiency(brief: Brief) -> CheckResult:
    """Check whether room areas (× circulation factor) fit in buildable envelope.

    Buildable envelope = (plot area) - (setbacks). For a multi-floor
    brief, the per-floor envelope is the same; we check whether each
    floor's room sum fits.

    HARD_FAIL: any floor's required area > envelope area.
    SOFT_WARN: utilisation > 95% (very tight; layout will be cramped).
    PASS: utilisation ≤ 95%.
    """
    plot = brief.plot
    setbacks = brief.user_stated_setbacks

    # Compute buildable envelope footprint (same on every floor)
    env_w = max(0.0, plot.width_m - setbacks.side_left_m
                - setbacks.side_right_m)
    env_d = max(0.0, plot.depth_m - setbacks.front_m
                - setbacks.rear_m)
    env_area_sqm = env_w * env_d

    # Find the floor with highest required room area
    worst_floor_num = 0
    worst_required_sqm = 0.0
    for fr in brief.floors:
        # Sum of room areas × circulation factor = required floor area
        # FloorRequirement.total_room_area_sqm() sums rooms with count
        rooms_sum = fr.total_room_area_sqm()
        required = rooms_sum * CIRCULATION_FACTOR
        if required > worst_required_sqm:
            worst_required_sqm = required
            worst_floor_num = fr.floor_number

    # Edge case: no rooms at all (e.g., stilt-only floor)
    if worst_required_sqm == 0:
        return _build_result(
            check_id="envelope_sufficiency",
            check_name="Envelope sufficiency",
            severity=CheckSeverity.NOT_APPLICABLE,
            message=(
                "No habitable rooms specified — envelope check skipped. "
                "(This is normal for stilt-only or storage-only floors.)"
            ),
            details={"envelope_sqm": round(env_area_sqm, 1)},
        )

    utilisation_pct = (worst_required_sqm / env_area_sqm) * 100 if env_area_sqm > 0 else float("inf")

    details = {
        "envelope_width_m": round(env_w, 2),
        "envelope_depth_m": round(env_d, 2),
        "envelope_area_sqm": round(env_area_sqm, 1),
        "worst_floor": worst_floor_num,
        "required_area_sqm": round(worst_required_sqm, 1),
        "utilisation_pct": round(utilisation_pct, 1),
        "circulation_factor": CIRCULATION_FACTOR,
    }

    if utilisation_pct > 100:
        shortfall = worst_required_sqm - env_area_sqm
        return _build_result(
            check_id="envelope_sufficiency",
            check_name="Envelope sufficiency",
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Floor {worst_floor_num} requires {worst_required_sqm:.0f} "
                f"sqm (rooms × {CIRCULATION_FACTOR} circulation) but the "
                f"buildable envelope is only {env_area_sqm:.0f} sqm. "
                f"Shortfall: {shortfall:.0f} sqm. The rooms physically "
                f"cannot fit on this floor without reducing room count, "
                f"reducing room sizes, or relaxing setbacks."
            ),
            details=details,
            common_doubts=(
                "Q: Can I reduce setbacks to fit? "
                "A: Possibly — check the SETBACK FEASIBILITY section. "
                "Some cities allow up to 0.3m relaxation on small plots "
                "with municipal variance application.",
                "Q: Does the circulation factor of 1.35 always apply? "
                "A: It's an industry typical (IS 3861-2002). A clever "
                "layout can sometimes hit 1.30; complex layouts need 1.40.",
            ),
        )
    if utilisation_pct > 95:
        return _build_result(
            check_id="envelope_sufficiency",
            check_name="Envelope sufficiency",
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Floor {worst_floor_num} uses {utilisation_pct:.0f}% of "
                f"envelope ({worst_required_sqm:.0f}/{env_area_sqm:.0f} sqm). "
                f"This is very tight — corridors will be narrow and the "
                f"layout has minimal flexibility. Consider slightly larger "
                f"setbacks or smaller rooms."
            ),
            details=details,
            common_doubts=(
                "Q: 'Tight' means what exactly? "
                "A: 95%+ utilisation typically means corridor widths "
                "drop to absolute NBC minimum and column placement "
                "becomes restrictive.",
            ),
        )
    return _build_result(
        check_id="envelope_sufficiency",
        check_name="Envelope sufficiency",
        severity=CheckSeverity.PASS,
        message=(
            f"Rooms fit comfortably ({utilisation_pct:.0f}% envelope "
            f"utilisation, {worst_required_sqm:.0f}/{env_area_sqm:.0f} "
            f"sqm on floor {worst_floor_num})."
        ),
        details=details,
    )


# ─── Check #2: Floor stack feasibility ────────────────────────────────

def check_floor_stack_feasibility(brief: Brief) -> CheckResult:
    """Check whether staircase area is accounted for across all floors.

    A G+1 brief needs ~4 sqm on EACH floor (ground + first) for stairs,
    or it's actually a 4-sqm-smaller-than-stated build per floor.

    HARD_FAIL: floor count > 1 AND any floor's residual area after
        deducting staircase + room area is < 0.
    SOFT_WARN: residual is < 5 sqm (tight margin).
    PASS: residual ≥ 5 sqm.
    NOT_APPLICABLE: single floor (no staircase needed).
    """
    if len(brief.floors) <= 1:
        return _build_result(
            check_id="floor_stack_feasibility",
            check_name="Floor stack feasibility",
            severity=CheckSeverity.NOT_APPLICABLE,
            message="Single-floor brief — no staircase area required.",
            details={"floor_count": len(brief.floors)},
        )

    plot = brief.plot
    setbacks = brief.user_stated_setbacks
    env_w = max(0.0, plot.width_m - setbacks.side_left_m
                - setbacks.side_right_m)
    env_d = max(0.0, plot.depth_m - setbacks.front_m
                - setbacks.rear_m)
    env_area_sqm = env_w * env_d

    # Per-floor required = rooms × circulation + staircase
    worst_floor_num = 0
    worst_residual = float("inf")
    for fr in brief.floors:
        rooms_sum = fr.total_room_area_sqm()
        # Top floor doesn't need a staircase going up
        is_top_floor = fr.floor_number == len(brief.floors) - 1
        staircase_area = 0.0 if is_top_floor else STAIRCASE_AREA_PER_FLOOR_SQM
        required = rooms_sum * CIRCULATION_FACTOR + staircase_area
        residual = env_area_sqm - required
        if residual < worst_residual:
            worst_residual = residual
            worst_floor_num = fr.floor_number

    details = {
        "envelope_sqm": round(env_area_sqm, 1),
        "floor_count": len(brief.floors),
        "staircase_per_floor_sqm": STAIRCASE_AREA_PER_FLOOR_SQM,
        "worst_floor": worst_floor_num,
        "worst_residual_sqm": round(worst_residual, 1),
    }

    if worst_residual < 0:
        return _build_result(
            check_id="floor_stack_feasibility",
            check_name="Floor stack feasibility",
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Floor {worst_floor_num} cannot fit rooms + staircase "
                f"({STAIRCASE_AREA_PER_FLOOR_SQM} sqm staircase needed). "
                f"Shortfall: {-worst_residual:.0f} sqm. Either reduce "
                f"rooms on this floor, reduce floor count, or accept a "
                f"more compact staircase (3 sqm absolute minimum, NBC "
                f"Part 3)."
            ),
            details=details,
            common_doubts=(
                "Q: Can I skip the staircase by using an external one? "
                "A: NBC requires internal staircase as primary access in "
                "residential buildings; external is supplementary only.",
            ),
        )
    if worst_residual < 5:
        return _build_result(
            check_id="floor_stack_feasibility",
            check_name="Floor stack feasibility",
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Floor {worst_floor_num} has only {worst_residual:.0f} sqm "
                f"of residual space after rooms + staircase. This is tight "
                f"— may not fit a comfortable staircase landing or "
                f"corridor."
            ),
            details=details,
        )
    return _build_result(
        check_id="floor_stack_feasibility",
        check_name="Floor stack feasibility",
        severity=CheckSeverity.PASS,
        message=(
            f"Staircase area accounted for on all {len(brief.floors)} "
            f"floors. Worst-case residual: {worst_residual:.0f} sqm "
            f"(floor {worst_floor_num})."
        ),
        details=details,
    )


# ─── Check #6: Parking width feasibility ──────────────────────────────

def check_parking_width(brief: Brief) -> CheckResult:
    """Check whether stilt parking is physically possible given setbacks.

    Reuses logic from Component 1's parking_feasibility. Wraps it as
    a feasibility CheckResult.

    NOT_APPLICABLE: brief has no stilt parking floor.
    HARD_FAIL: internal width after setbacks < 3.5m (not even one car).
    SOFT_WARN: width < 6m (single car only, no turning room).
    PASS: width ≥ 6m.
    """
    from buildemup.domain.floor_requirement import FloorUse

    has_stilt = any(
        f.floor_use == FloorUse.STILT_PARKING for f in brief.floors
    )
    if not has_stilt:
        return _build_result(
            check_id="parking_width_feasibility",
            check_name="Parking width feasibility",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.NOT_APPLICABLE,
            message=(
                "Brief has no stilt parking floor — parking width check "
                "skipped."
            ),
            details={},
        )

    plot = brief.plot
    setbacks = brief.user_stated_setbacks
    internal_width_m = max(
        0.0,
        plot.width_m - setbacks.side_left_m - setbacks.side_right_m,
    )

    details = {
        "plot_width_m": plot.width_m,
        "internal_width_m": round(internal_width_m, 2),
        "side_setback_total_m": (setbacks.side_left_m
                                 + setbacks.side_right_m),
        "min_for_one_car_m": PARKING_MIN_INTERNAL_WIDTH_M,
    }

    if internal_width_m < PARKING_MIN_INTERNAL_WIDTH_M:
        return _build_result(
            check_id="parking_width_feasibility",
            check_name="Parking width feasibility",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Internal width after side setbacks is only "
                f"{internal_width_m:.1f}m. NBC + IS 11268 minimum for "
                f"a single car bay is 2.5m + 0.5m circulation each side "
                f"= {PARKING_MIN_INTERNAL_WIDTH_M:.1f}m absolute physical "
                f"minimum. Parking is not feasible on this plot with "
                f"current setbacks."
            ),
            details=details,
            verification_recommendation=(
                "Component 4 (layout) will validate with actual column "
                "placement. Width check is necessary but not sufficient."
            ),
            common_doubts=(
                "Q: Can I park outside in the front setback instead? "
                "A: Some cities permit it (Chennai, Bangalore for small "
                "plots); some prohibit it (Mumbai). Check your DCR.",
                "Q: What if I skip stilt and use ground floor as parking? "
                "A: That loses ground-floor habitable space but is a "
                "common compromise on tight plots.",
            ),
        )
    if internal_width_m < 6.0:
        return _build_result(
            check_id="parking_width_feasibility",
            check_name="Parking width feasibility",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Internal width {internal_width_m:.1f}m fits one car "
                f"but with no turning margin and tight column placement. "
                f"Final feasibility depends on layout (Component 4) — "
                f"turning radius, gate alignment, and column positions "
                f"can still make this fail."
            ),
            details=details,
            verification_priority=VerificationPriority.IMPORTANT,
            verification_recommendation=(
                "Component 4 layout will determine whether the column "
                "grid actually allows a car to enter and park."
            ),
        )
    return _build_result(
        check_id="parking_width_feasibility",
        check_name="Parking width feasibility",
        category=CheckCategory.USABILITY,
        severity=CheckSeverity.PASS,
        message=(
            f"Internal width {internal_width_m:.1f}m comfortably fits "
            f"a single car with turning margin."
        ),
        details=details,
    )


# ─── Check #5: Budget feasibility ─────────────────────────────────────

def check_budget_feasibility(
    brief: Brief, c7_cost_estimate
) -> CheckResult:
    """Check whether the user's stated budget meets C7's structural cost range.

    HARD_FAIL: user budget MAX < C7 range_min (cannot afford even the
        minimum estimate).
    SOFT_WARN: user budget MAX < C7 exact (within range but below
        most-likely point).
    PASS: user budget MAX >= C7 exact.

    Notes:
      - C7 cost is structural-only (~40% of all-in). Budget check
        compares against structural, then warns about all-in separately.
      - Confidence is HIGH because both numbers are well-known.
    """
    if c7_cost_estimate is None:
        return _build_result(
            check_id="budget_feasibility",
            check_name="Budget feasibility",
            category=CheckCategory.COST,
            severity=CheckSeverity.NOT_APPLICABLE,
            message=(
                "Component 7 did not provide a cost estimate for this "
                "brief — budget check skipped."
            ),
            details={},
        )

    user_budget_max_inr = brief.budget_range.max_rupees
    structural_min_inr = c7_cost_estimate.range_min
    structural_exact_inr = c7_cost_estimate.exact_value
    structural_max_inr = c7_cost_estimate.range_max

    # Estimate all-in cost using v0.9.1 cited 2.5× factor
    all_in_typical_inr = structural_exact_inr * 2.5

    details = {
        "user_budget_max_lakhs": round(user_budget_max_inr / 100_000, 2),
        "structural_range_min_lakhs": round(structural_min_inr / 100_000, 2),
        "structural_exact_lakhs": round(structural_exact_inr / 100_000, 2),
        "structural_range_max_lakhs": round(structural_max_inr / 100_000, 2),
        "all_in_typical_lakhs": round(all_in_typical_inr / 100_000, 2),
    }

    if user_budget_max_inr < structural_min_inr:
        # Session L patch (edge case #10 fix): how badly is budget short?
        # If the gap is large (≥30% short), use sharper language so users
        # don't read "insufficient" as "needs minor adjustment".
        gap_inr = structural_min_inr - user_budget_max_inr
        gap_pct = (gap_inr / structural_min_inr) * 100
        if gap_pct >= 30:
            sharp_lead = (
                f"Budget materially insufficient — your ₹{user_budget_max_inr/100_000:.1f}L "
                f"ceiling is {gap_pct:.0f}% below the structural minimum "
                f"₹{structural_min_inr/100_000:.1f}L. This is not a minor "
                f"adjustment; it requires major scope reduction (fewer floors, "
                f"smaller footprint, or significantly larger budget)."
            )
        else:
            sharp_lead = (
                f"Budget ceiling ₹{user_budget_max_inr/100_000:.1f}L is "
                f"below structural minimum ₹{structural_min_inr/100_000:.1f}L "
                f"({gap_pct:.0f}% short). The structure alone cannot be "
                f"built within budget."
            )
        return _build_result(
            check_id="budget_feasibility",
            check_name="Budget feasibility",
            category=CheckCategory.COST,
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"{sharp_lead} All-in cost (typical 2.5× structural ≈ "
                f"₹{all_in_typical_inr/100_000:.0f}L) will be even higher."
            ),
            details=details,
            common_doubts=(
                "Q: Can I reduce cost by using cheaper materials? "
                "A: Some yes — but structural materials (cement, steel) "
                "have minimum quality grades by NBC. Real savings come "
                "from smaller footprint or fewer floors.",
                "Q: Is the structural-only number realistic? "
                "A: It includes foundation, frame, slab, walls. "
                "Excludes finishes (~25% extra), MEP (~15%), interior "
                "(~12%), and contingency. See BUDGET section for breakdown.",
            ),
        )
    if user_budget_max_inr < structural_exact_inr:
        return _build_result(
            check_id="budget_feasibility",
            check_name="Budget feasibility",
            category=CheckCategory.COST,
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Budget ceiling ₹{user_budget_max_inr/100_000:.1f}L is "
                f"within C7's range but below the most-likely point "
                f"₹{structural_exact_inr/100_000:.1f}L. Tight margin — "
                f"if costs trend toward the upper range, budget may "
                f"overrun. Industry data: 85%+ of projects overshoot "
                f"15-30% (see BUDGET section)."
            ),
            details=details,
        )
    return _build_result(
        check_id="budget_feasibility",
        check_name="Budget feasibility",
        category=CheckCategory.COST,
        severity=CheckSeverity.PASS,
        message=(
            f"Budget ceiling ₹{user_budget_max_inr/100_000:.1f}L covers "
            f"C7's structural estimate (most-likely "
            f"₹{structural_exact_inr/100_000:.1f}L). Note: all-in cost is "
            f"typically 2.5× structural ≈ ₹{all_in_typical_inr/100_000:.0f}L "
            f"— ensure this fits your overall budget."
        ),
        details=details,
    )
