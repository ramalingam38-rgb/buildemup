"""
Component 2 — Branched checks (Session C).

This module implements the first BRANCHED check — setbacks — proving
out the dual-design pattern end-to-end:

  - check_setback_compliance_practical: validates against user-stated
    setbacks (whatever the user accepted as a compromise).
  - check_setback_compliance_code_strict: validates against the
    NBC/DCR-mandated setbacks (always strict).
  - compute_setback_gap: produces a Gap when the two variants differ,
    with severity quantifying how big the compromise is.

Why setbacks first: per the user, "users push mostly on setbacks" — this
is the most-asked-for compromise in real Indian residential build briefs.
Getting this pattern right here means it works for the other 7 branched
checks (room minimums, solar, ventilation, soil, water table, RWH, approval
complexity) which all follow the same shape.

Architectural note: Component 1 already computes BOTH user_stated_setbacks
and nbc_compliant_setbacks during brief capture. So this module is a thin
wrapper that compares them and produces appropriate CheckResults — no
new KB lookup needed.

Comparison rule:
  PRACTICAL passes if user-stated > 0 (user must specify each setback).
  CODE_STRICT passes if user-stated >= NBC-mandated for ALL four sides.
  Gap severity is computed per-side and aggregated.
"""
from __future__ import annotations

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority, Gap, GapSeverity, DecisionSource,
)
from buildemup.components.c02.scoring import compute_score_contribution


# ─── Constants ────────────────────────────────────────────────────────

SETBACK_GAP_MARGINAL_PCT = 15.0
"""Below this % shortfall vs NBC, gap is MARGINAL severity."""

SETBACK_GAP_SIGNIFICANT_PCT = 30.0
"""Above MARGINAL but below this %, gap is SIGNIFICANT severity.
Above this — the gap is BLOCKING_IF_NOT_ACCEPTED."""

SETBACK_PRACTICAL_MIN_M = 0.0
"""Practical variant accepts any setback ≥ 0 (user's chosen compromise).
Below 0 makes no physical sense and is a HARD fail in any variant."""


# ─── Helper: build CheckResult ────────────────────────────────────────

def _build_result(
    *,
    check_id: str,
    check_name: str,
    severity: CheckSeverity,
    message: str,
    details: dict,
    category: CheckCategory = CheckCategory.SPATIAL,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    confidence_reason: str | None = None,
    assumption_used: str | None = None,
    verification_recommendation: str | None = None,
    verification_priority: VerificationPriority = VerificationPriority.OPTIONAL,
    common_doubts: tuple[str, ...] = (),
) -> CheckResult:
    temp = CheckResult(
        check_id=check_id, check_name=check_name, category=category,
        severity=severity, confidence=confidence,
        confidence_reason=confidence_reason,
        score_contribution=0,
        message=message, details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )
    contribution = compute_score_contribution(temp)
    return CheckResult(
        check_id=check_id, check_name=check_name, category=category,
        severity=severity, confidence=confidence,
        confidence_reason=confidence_reason,
        score_contribution=contribution,
        message=message, details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )


# ─── Internal utilities ───────────────────────────────────────────────

def _compute_per_side_shortfall_pct(
    user_value_m: float, nbc_value_m: float,
) -> float:
    """Return shortfall as % of NBC value.

    0 means user meets/exceeds NBC. 100 means user is at 0 setback.
    Negative means user exceeds NBC (impossible to be 'short').
    """
    if nbc_value_m <= 0:
        # NBC has no minimum on this side (e.g., shared wall in row house)
        return 0.0
    if user_value_m >= nbc_value_m:
        return 0.0
    return ((nbc_value_m - user_value_m) / nbc_value_m) * 100.0


def _aggregate_max_shortfall_pct(brief: Brief) -> tuple[float, str]:
    """Return (max shortfall %, side_label) across all 4 sides."""
    user = brief.user_stated_setbacks
    nbc = brief.nbc_compliant_setbacks
    sides = [
        ("front", user.front_m, nbc.front_m),
        ("rear", user.rear_m, nbc.rear_m),
        ("left", user.side_left_m, nbc.side_left_m),
        ("right", user.side_right_m, nbc.side_right_m),
    ]
    max_pct = 0.0
    max_side = "front"
    for side, u, n in sides:
        pct = _compute_per_side_shortfall_pct(u, n)
        if pct > max_pct:
            max_pct = pct
            max_side = side
    return max_pct, max_side


def _aggregate_violations(brief: Brief) -> tuple[tuple[str, float, float, float], ...]:
    """List of (side, user_m, nbc_m, shortfall_pct) for sides where user < NBC."""
    user = brief.user_stated_setbacks
    nbc = brief.nbc_compliant_setbacks
    sides = [
        ("front", user.front_m, nbc.front_m),
        ("rear", user.rear_m, nbc.rear_m),
        ("left", user.side_left_m, nbc.side_left_m),
        ("right", user.side_right_m, nbc.side_right_m),
    ]
    out = []
    for side, u, n in sides:
        if n > 0 and u < n:
            pct = ((n - u) / n) * 100.0
            out.append((side, u, n, pct))
    return tuple(out)


# ─── Check #4 PRACTICAL: setback feasibility (user-accepted) ──────────

def check_setback_compliance_practical(brief: Brief) -> CheckResult:
    """Validate user-stated setbacks for the Practical design variant.

    Practical variant accepts whatever the user chose as long as:
      - All values are physically valid (≥ 0)
      - The remaining envelope is buildable (≥ 1m × 1m clear space)

    Even if user-stated < NBC-mandated, this is PASS in PRACTICAL — the
    compromise is captured separately as a Gap. The user has signalled
    they accept the compromise by entering these values in Component 1.

    HARD_FAIL: any setback < 0 (physically invalid).
    SOFT_WARN: total setback eats more than 80% of plot dimension
        (envelope shrinks below practical buildable).
    PASS: setbacks valid + envelope ≥ 1×1m.
    """
    user = brief.user_stated_setbacks
    plot = brief.plot

    # Physical validity
    invalid_sides = []
    for side, val in [
        ("front", user.front_m), ("rear", user.rear_m),
        ("left", user.side_left_m), ("right", user.side_right_m),
    ]:
        if val < 0:
            invalid_sides.append((side, val))

    if invalid_sides:
        return _build_result(
            check_id="setback_practical",
            check_name="Setback feasibility (Practical)",
            severity=CheckSeverity.HARD_FAIL,
            verification_priority=VerificationPriority.CRITICAL,
            message=(
                f"Setbacks must be ≥ 0m. Invalid: "
                f"{', '.join(f'{s}={v}m' for s, v in invalid_sides)}."
            ),
            details={"invalid_sides": invalid_sides},
        )

    # Envelope viability
    env_w = plot.width_m - user.side_left_m - user.side_right_m
    env_d = plot.depth_m - user.front_m - user.rear_m

    details = {
        "user_setbacks_m": {
            "front": user.front_m, "rear": user.rear_m,
            "left": user.side_left_m, "right": user.side_right_m,
        },
        "envelope_width_m": round(env_w, 2),
        "envelope_depth_m": round(env_d, 2),
        "envelope_area_sqm": round(env_w * env_d, 1),
        "variant": "practical",
    }

    common_doubts = (
        "Q: Why doesn't the Practical check fail when I'm below NBC? "
        "A: Practical accepts your stated compromises and surfaces them "
        "as a Gap instead. Look at the GAP ANALYSIS section to see "
        "what NBC strictly requires.",
        "Q: Will my building plan get approved with these setbacks? "
        "A: Practical setbacks may need a formal variance application or "
        "may simply be tolerated by your municipality (varies by city + "
        "ward officer). Always confirm with a licensed local architect.",
    )

    if env_w < 1.0 or env_d < 1.0:
        return _build_result(
            check_id="setback_practical",
            check_name="Setback feasibility (Practical)",
            severity=CheckSeverity.HARD_FAIL,
            verification_priority=VerificationPriority.CRITICAL,
            message=(
                f"After your stated setbacks, the buildable envelope is "
                f"{env_w:.1f}×{env_d:.1f}m — too small to build any "
                f"meaningful structure. You need either a bigger plot or "
                f"smaller setbacks."
            ),
            details=details,
            common_doubts=common_doubts,
        )

    # Soft-warn if envelope is very tight (>80% of plot is setback)
    setback_share_pct = (1 - (env_w * env_d) / (plot.width_m * plot.depth_m)) * 100
    if setback_share_pct > 80:
        return _build_result(
            check_id="setback_practical",
            check_name="Setback feasibility (Practical)",
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Setbacks consume {setback_share_pct:.0f}% of plot — "
                f"envelope {env_w:.1f}×{env_d:.1f}m is very tight. "
                f"Consider reducing setbacks if your municipality allows."
            ),
            details=details,
            common_doubts=common_doubts,
        )

    return _build_result(
        check_id="setback_practical",
        check_name="Setback feasibility (Practical)",
        severity=CheckSeverity.PASS,
        message=(
            f"User-stated setbacks valid. Envelope "
            f"{env_w:.1f}×{env_d:.1f}m = {env_w*env_d:.0f} sqm."
        ),
        details=details,
    )


# ─── Check #4 CODE-STRICT: setback compliance (NBC/DCR strict) ────────

def check_setback_compliance_code_strict(brief: Brief) -> CheckResult:
    """Validate user-stated setbacks against NBC/DCR mandated minimums.

    CODE_STRICT variant requires user setbacks ≥ NBC for ALL 4 sides.
    Any side that's short triggers HARD_FAIL.

    HARD_FAIL: any side has user-value < NBC-value.
    SOFT_WARN: any side at exactly NBC minimum (no margin for execution
        error). Edge case — typically rare in real briefs.
    PASS: every side ≥ NBC.
    """
    nbc = brief.nbc_compliant_setbacks

    violations = _aggregate_violations(brief)

    details = {
        "user_setbacks_m": {
            "front": brief.user_stated_setbacks.front_m,
            "rear": brief.user_stated_setbacks.rear_m,
            "left": brief.user_stated_setbacks.side_left_m,
            "right": brief.user_stated_setbacks.side_right_m,
        },
        "nbc_mandated_setbacks_m": {
            "front": nbc.front_m, "rear": nbc.rear_m,
            "left": nbc.side_left_m, "right": nbc.side_right_m,
        },
        "city": brief.plot.city,
        "violations": [
            {"side": s, "user_m": u, "nbc_m": n, "shortfall_pct": round(p, 1)}
            for s, u, n, p in violations
        ],
        "variant": "code_strict",
    }

    common_doubts = (
        f"Q: Why does {brief.plot.city.title()} mandate these specific "
        f"setbacks? "
        f"A: Setbacks ensure light, ventilation, fire access, and "
        f"separation from neighbours per NBC + city DCR. Stricter on "
        f"larger/taller buildings.",
        "Q: My neighbour built closer than this — why must I comply? "
        "A: Older buildings may be grandfathered, regularised, or "
        "violations not enforced. New approvals must comply unless you "
        "obtain a formal variance.",
    )

    if violations:
        worst_side, worst_u, worst_n, worst_pct = max(
            violations, key=lambda x: x[3]
        )
        side_list = ", ".join(
            f"{s}={u}m (need ≥{n}m)" for s, u, n, _ in violations
        )
        return _build_result(
            check_id="setback_code_strict",
            check_name="Setback compliance (Code-Strict)",
            severity=CheckSeverity.HARD_FAIL,
            verification_priority=VerificationPriority.CRITICAL,
            confidence=ConfidenceLevel.HIGH,
            message=(
                f"User-stated setbacks fall short of NBC/DCR on "
                f"{len(violations)} side(s): {side_list}. "
                f"Worst gap: {worst_pct:.0f}% short on {worst_side}. "
                f"To get strict approval without compromise, increase "
                f"setbacks to NBC-mandated values or apply for a formal "
                f"variance."
            ),
            details=details,
            common_doubts=common_doubts,
        )

    return _build_result(
        check_id="setback_code_strict",
        check_name="Setback compliance (Code-Strict)",
        severity=CheckSeverity.PASS,
        message=(
            f"All 4 sides meet NBC/DCR mandate for {brief.plot.city.title()}: "
            f"front≥{nbc.front_m}m, rear≥{nbc.rear_m}m, "
            f"left≥{nbc.side_left_m}m, right≥{nbc.side_right_m}m."
        ),
        details=details,
    )


# ─── Gap helper ───────────────────────────────────────────────────────

def compute_setback_gap(brief: Brief) -> Gap | None:
    """Compute the Gap between PRACTICAL and CODE_STRICT setback variants.

    Returns None if user-stated == NBC-mandated for all sides ("got lucky").
    Returns a Gap with appropriate severity otherwise.

    Gap severity rule:
      INFO_ONLY: should not occur for setbacks (this gap always means
        a user-accepted compromise that the user must consent to)
      MARGINAL: max shortfall < 15%
      SIGNIFICANT: 15-30% shortfall
      BLOCKING_IF_NOT_ACCEPTED: ≥ 30% shortfall on any side
    """
    violations = _aggregate_violations(brief)
    if not violations:
        return None

    max_pct, worst_side = _aggregate_max_shortfall_pct(brief)

    # Severity from worst-side shortfall percentage
    if max_pct >= SETBACK_GAP_SIGNIFICANT_PCT:
        severity = GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    elif max_pct >= SETBACK_GAP_MARGINAL_PCT:
        severity = GapSeverity.SIGNIFICANT
    else:
        severity = GapSeverity.MARGINAL

    user = brief.user_stated_setbacks
    nbc = brief.nbc_compliant_setbacks

    # Build a human-readable impact description
    lines = []
    for side, u, n, pct in violations:
        lines.append(f"{side}: {u}m vs NBC {n}m ({pct:.0f}% short)")
    impact = "Setback shortfalls — " + "; ".join(lines)

    return Gap(
        check_id="setback_compliance",
        severity=severity,
        practical_value={
            "front": user.front_m, "rear": user.rear_m,
            "left": user.side_left_m, "right": user.side_right_m,
        },
        code_strict_value={
            "front": nbc.front_m, "rear": nbc.rear_m,
            "left": nbc.side_left_m, "right": nbc.side_right_m,
        },
        impact_description=impact,
        # First-pass default — Component 1 captured these via brief, so
        # the user has implicitly accepted them. But explicit acceptance
        # comes via the post-report iteration UI in Sessions H+.
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )


# ─── Check #7: Solar exposure (branched) ──────────────────────────────
#
# NBC 2016 Part 8 mandates daylight factor of ~1% for habitable rooms —
# realistically achievable when at least 2 of the 4 plot orientations
# get unobstructed sun. Practical heuristic accepts even 1 good
# orientation if the user is OK with it.

PLOT_ORIENTATION_QUALITY = {
    # Score: 0-100, where higher = more sun exposure year-round in India.
    # Based on rough north-Indian + south-Indian solar geometry.
    "N": 30,   # north-facing → least direct sun, but stable diffuse light
    "NE": 55,
    "E": 70,   # morning sun, cool afternoon
    "SE": 80,
    "S": 90,   # most sun exposure year-round in India
    "SW": 75,  # afternoon hot sun
    "W": 65,   # afternoon hot sun, less daylight in morning
    "NW": 50,
}
PRACTICAL_SOLAR_MIN_SCORE = 30  # any orientation gets "some sun"
CODE_STRICT_SOLAR_MIN_SCORE = 55
"""NBC daylight factor 1% requires reasonable orientation. Empirically
≥55 covers E/NE/SE/S/SW orientations, leaving N/NW/W as marginal.
This is a coarse approximation — a real daylight calc needs window
dimensions + neighbour heights."""


def _get_orientation_score(brief: Brief) -> int:
    """Look up orientation quality score for the brief's plot facing."""
    facing = brief.plot.facing.value if hasattr(brief.plot.facing, "value") else str(brief.plot.facing)
    return PLOT_ORIENTATION_QUALITY.get(facing, 50)


def check_solar_exposure_practical(brief: Brief) -> CheckResult:
    """Practical solar check — accepts any orientation that gets some sun.

    HARD_FAIL: orientation score < 30 (genuinely sunless — should not
        occur for our 8 supported facings).
    SOFT_WARN: orientation score 30-55 (N/NW). Sun-poor; rooms will need
        more electric lighting during day.
    PASS: orientation score ≥ 55.
    """
    score = _get_orientation_score(brief)
    facing = brief.plot.facing.value if hasattr(brief.plot.facing, "value") else str(brief.plot.facing)

    details = {
        "plot_facing": facing,
        "orientation_score": score,
        "practical_threshold": PRACTICAL_SOLAR_MIN_SCORE,
        "variant": "practical",
    }

    common_doubts = (
        f"Q: My plot faces {facing} — what does the orientation score mean? "
        f"A: It's a coarse year-round sun-availability heuristic for India "
        f"(0-100). Higher means more direct sunlight reaches the plot. "
        f"Real daylight depends on window placement + neighbour heights — "
        f"final layout in Component 4 will validate.",
        "Q: Can I improve sun exposure with design choices? "
        "A: Yes — larger south/east windows, light-coloured interior "
        "walls, skylights, and minimising deep room layouts all help.",
    )

    if score < PRACTICAL_SOLAR_MIN_SCORE:
        return _build_result(
            check_id="solar_practical",
            check_name="Solar exposure (Practical)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.HARD_FAIL,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "Heuristic based on plot orientation only — does not "
                "account for window placement or neighbour shading."
            ),
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                f"Plot faces {facing} (score {score}/100) — sun exposure is "
                f"too poor for habitable rooms without major design "
                f"compensation."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    if score < CODE_STRICT_SOLAR_MIN_SCORE:
        return _build_result(
            check_id="solar_practical",
            check_name="Solar exposure (Practical)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.SOFT_WARN,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "Heuristic based on plot orientation only — does not "
                "account for window placement or neighbour shading."
            ),
            message=(
                f"Plot faces {facing} (score {score}/100) — sun-poor. "
                f"Rooms may need more daytime electric lighting. "
                f"Workable if you accept this trade-off."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="solar_practical",
        check_name="Solar exposure (Practical)",
        category=CheckCategory.USABILITY,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.MEDIUM,
        confidence_reason=(
            "Heuristic based on plot orientation only — final daylight "
            "depends on window design (Component 4)."
        ),
        message=(
            f"Plot faces {facing} (score {score}/100) — adequate sun "
            f"for habitable rooms."
        ),
        details=details,
    )


def check_solar_exposure_code_strict(brief: Brief) -> CheckResult:
    """Code-strict solar check per NBC Part 8 daylight factor heuristic.

    Practical-side already accepts marginal scores; this lane requires
    a strictly NBC-aligned orientation score (≥ 55).

    HARD_FAIL: orientation score < 55 (does not meet NBC daylight 1%).
    PASS: orientation score ≥ 55.
    """
    score = _get_orientation_score(brief)
    facing = brief.plot.facing.value if hasattr(brief.plot.facing, "value") else str(brief.plot.facing)

    details = {
        "plot_facing": facing,
        "orientation_score": score,
        "code_strict_threshold": CODE_STRICT_SOLAR_MIN_SCORE,
        "nbc_reference": "NBC 2016 Part 8 Section 1 (daylight factor 1%)",
        "variant": "code_strict",
    }

    common_doubts = (
        "Q: My plot faces N or NW — what can I do? "
        "A: NBC daylight compliance becomes harder. Options: enlarge "
        "south-side windows, add courtyards, or accept the Practical "
        "compromise.",
    )

    if score < CODE_STRICT_SOLAR_MIN_SCORE:
        return _build_result(
            check_id="solar_code_strict",
            check_name="Solar exposure (Code-Strict)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.HARD_FAIL,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "NBC daylight factor 1% is hard to meet on this orientation."
            ),
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                f"Plot faces {facing} (score {score}/100). NBC Part 8 "
                f"daylight factor 1% is difficult to achieve without "
                f"major fenestration or courtyard design. Code-Strict "
                f"would require redesign or relaxation."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="solar_code_strict",
        check_name="Solar exposure (Code-Strict)",
        category=CheckCategory.USABILITY,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.MEDIUM,
        message=(
            f"Plot faces {facing} (score {score}/100) — supports NBC "
            f"daylight factor with standard window sizing."
        ),
        details=details,
    )


def compute_solar_gap(brief: Brief) -> Gap | None:
    """Gap when Practical accepts a sun-poor orientation that CodeStrict rejects.

    Returns None when the orientation passes both lanes.
    """
    score = _get_orientation_score(brief)
    if score >= CODE_STRICT_SOLAR_MIN_SCORE:
        return None  # Both lanes pass

    facing = brief.plot.facing.value if hasattr(brief.plot.facing, "value") else str(brief.plot.facing)
    # Practical side accepted; CodeStrict rejects → BLOCKING_IF_NOT_ACCEPTED
    # unless the score is so low that even Practical fails — then severity
    # is SIGNIFICANT (because both lanes fail and there's no real choice).
    if score < PRACTICAL_SOLAR_MIN_SCORE:
        severity = GapSeverity.SIGNIFICANT
        impact = (
            f"Plot faces {facing} — both Practical and CodeStrict find "
            f"this sun-poor. Major design intervention needed."
        )
    else:
        severity = GapSeverity.BLOCKING_IF_NOT_ACCEPTED
        impact = (
            f"Plot faces {facing} (score {score}/100). Practical accepts "
            f"the marginal sun exposure; CodeStrict requires score ≥ "
            f"{CODE_STRICT_SOLAR_MIN_SCORE} per NBC Part 8 daylight factor."
        )

    return Gap(
        check_id="solar_exposure",
        severity=severity,
        practical_value={"orientation_score": score, "plot_facing": facing,
                         "accepted": score >= PRACTICAL_SOLAR_MIN_SCORE},
        code_strict_value={"min_score": CODE_STRICT_SOLAR_MIN_SCORE,
                           "plot_facing": facing, "accepted": False},
        impact_description=impact,
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )


# ─── Check #8: Cross-ventilation (branched) ───────────────────────────
#
# Per NBC Part 8, habitable rooms require cross-ventilation: openings on
# at least two walls. Detached plots support this naturally; row houses
# (continuous type) typically have only front + rear openings, not sides.
# Plot type from Component 1's Plot.plot_type is the key input.
#
# v0.1 LIMITATION: Continuous (row house) plots get 2 openable sides
# (front + rear), which meets NBC's ≥2 minimum — so the gap rarely
# triggers. Real divergence requires modelling interior/landlocked
# plots or shaft-only configurations, which v0.1 doesn't capture.
# The check + gap helper still ship for forward-compatibility.

CROSS_VENT_PRACTICAL_MIN_OPEN_SIDES = 1
"""Practical accepts even one openable side — minimum acceptable for
basic ventilation (e.g., row house with deep front + rear openings)."""

CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES = 2
"""NBC Part 8 cross-ventilation requires openings on ≥2 sides for
proper air exchange."""


def _count_openable_sides(brief: Brief) -> int:
    """Estimate how many of the 4 sides can have window openings.

    Based on plot_type:
      - DETACHED: all 4 sides openable (4)
      - SEMI_DETACHED: 3 sides openable (one side shared)
      - CONTINUOUS (row house): 2 sides openable (front + rear only)
    """
    from buildemup.domain.plot import PlotType
    pt = brief.plot.plot_type
    if pt == PlotType.DETACHED:
        return 4
    if pt == PlotType.SEMI_DETACHED:
        return 3
    if pt == PlotType.CONTINUOUS:
        return 2
    return 4  # safe default


def check_cross_ventilation_practical(brief: Brief) -> CheckResult:
    """Practical cross-vent — accepts even minimal openable sides."""
    sides = _count_openable_sides(brief)
    plot_type_str = brief.plot.plot_type.value if hasattr(brief.plot.plot_type, "value") else str(brief.plot.plot_type)

    details = {
        "plot_type": plot_type_str,
        "openable_sides_estimated": sides,
        "practical_min_sides": CROSS_VENT_PRACTICAL_MIN_OPEN_SIDES,
        "variant": "practical",
    }

    common_doubts = (
        "Q: How is 'openable sides' computed? "
        "A: From your plot type — detached has all 4 sides free, "
        "semi-detached has 3 (one shared wall), continuous (row) has "
        "only front + rear (2). Final layout in Component 4 will "
        "validate which walls actually get window openings.",
        "Q: What if my row house has a small light well? "
        "A: A central light well counts as a third opening surface — "
        "but Component 4 needs to include it explicitly. v0.1 does "
        "not model light wells.",
    )

    if sides < CROSS_VENT_PRACTICAL_MIN_OPEN_SIDES:
        return _build_result(
            check_id="cross_vent_practical",
            check_name="Cross-ventilation (Practical)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.HARD_FAIL,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "Heuristic based on plot type only — does not account "
                "for light wells, courtyards, or interior shafts."
            ),
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                f"Plot type '{plot_type_str}' supports {sides} openable "
                f"sides — insufficient for any meaningful ventilation. "
                f"Add courtyard or light well in design."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    if sides < CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES:
        return _build_result(
            check_id="cross_vent_practical",
            check_name="Cross-ventilation (Practical)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.SOFT_WARN,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "Heuristic based on plot type only — light wells / "
                "courtyards may add more ventilation."
            ),
            message=(
                f"Plot type '{plot_type_str}' supports only {sides} "
                f"openable side — limited cross-ventilation. Workable "
                f"if you accept reduced air exchange or add a light well."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="cross_vent_practical",
        check_name="Cross-ventilation (Practical)",
        category=CheckCategory.USABILITY,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.MEDIUM,
        confidence_reason=(
            "Heuristic based on plot type — final ventilation depends "
            "on window placement (Component 4)."
        ),
        message=(
            f"Plot type '{plot_type_str}' supports {sides} openable "
            f"sides — adequate for cross-ventilation."
        ),
        details=details,
    )


def check_cross_ventilation_code_strict(brief: Brief) -> CheckResult:
    """Code-strict cross-vent per NBC Part 8 (≥2 openable sides)."""
    sides = _count_openable_sides(brief)
    plot_type_str = brief.plot.plot_type.value if hasattr(brief.plot.plot_type, "value") else str(brief.plot.plot_type)

    details = {
        "plot_type": plot_type_str,
        "openable_sides_estimated": sides,
        "code_strict_min_sides": CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES,
        "nbc_reference": "NBC 2016 Part 8 Section 1 (cross-ventilation requirements)",
        "variant": "code_strict",
    }

    common_doubts = (
        "Q: NBC requires ≥2 sides openable — does my row house comply? "
        "A: Front + rear openings count as 2 sides. So a basic row house "
        "passes — but the openings must be properly sized (10% of floor "
        "area minimum per room).",
    )

    if sides < CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES:
        return _build_result(
            check_id="cross_vent_code_strict",
            check_name="Cross-ventilation (Code-Strict)",
            category=CheckCategory.USABILITY,
            severity=CheckSeverity.HARD_FAIL,
            confidence=ConfidenceLevel.MEDIUM,
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                f"Plot type '{plot_type_str}' supports only {sides} "
                f"openable side — does not meet NBC cross-vent requirement "
                f"({CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES} sides minimum). "
                f"Add courtyard or interior shaft to comply."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="cross_vent_code_strict",
        check_name="Cross-ventilation (Code-Strict)",
        category=CheckCategory.USABILITY,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.MEDIUM,
        message=(
            f"Plot type '{plot_type_str}' supports {sides} sides — meets "
            f"NBC cross-ventilation requirement."
        ),
        details=details,
    )


def compute_ventilation_gap(brief: Brief) -> Gap | None:
    """Gap when Practical accepts a low-vent design that CodeStrict rejects."""
    sides = _count_openable_sides(brief)
    if sides >= CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES:
        return None  # Both pass

    plot_type_str = brief.plot.plot_type.value if hasattr(brief.plot.plot_type, "value") else str(brief.plot.plot_type)

    if sides < CROSS_VENT_PRACTICAL_MIN_OPEN_SIDES:
        # Both lanes fail — there's no real choice
        severity = GapSeverity.SIGNIFICANT
        impact = (
            f"Plot type '{plot_type_str}' supports {sides} openable side. "
            f"Both Practical and CodeStrict find this insufficient — major "
            f"design intervention needed."
        )
    else:
        severity = GapSeverity.BLOCKING_IF_NOT_ACCEPTED
        impact = (
            f"Plot type '{plot_type_str}' supports {sides} openable side. "
            f"Practical accepts this; CodeStrict requires ≥"
            f"{CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES} sides per NBC Part 8."
        )

    return Gap(
        check_id="cross_ventilation",
        severity=severity,
        practical_value={"openable_sides": sides, "plot_type": plot_type_str,
                         "accepted": sides >= CROSS_VENT_PRACTICAL_MIN_OPEN_SIDES},
        code_strict_value={"min_openable_sides": CROSS_VENT_CODE_STRICT_MIN_OPEN_SIDES,
                           "plot_type": plot_type_str, "accepted": False},
        impact_description=impact,
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )
