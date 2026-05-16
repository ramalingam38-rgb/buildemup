"""
Component 2 — RWH mandate + Approval complexity checks (Session F).

These are the last 2 of the 18 v0.1 feasibility checks:
  #16 rainwater harvesting mandate (branched)
  #18 statutory approval complexity (advisory, INFO_ONLY)

RWH branching rule:
  PRACTICAL: only flag if city legally mandates it for this plot tier.
    User who isn't legally required is left alone.
  CODE_STRICT: always recommend RWH (NBC Part 9 sustainability + NBC
    sustainable design recommendations apply universally).

Approval complexity:
  Single check (no branching). Always INFO_ONLY severity. Sets user
  expectations for time + paperwork burden. Never blocks.
"""
from __future__ import annotations

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority, Gap, GapSeverity, DecisionSource,
)
from buildemup.components.c02.scoring import compute_score_contribution
from buildemup.utils.kb_rules_loader import load_rules


# ─── Constants ────────────────────────────────────────────────────────

# RWH cost addition estimates (industry typical)
RWH_COST_RANGE_LAKHS = (0.5, 2.0)
"""Range of typical RWH installation cost in lakhs ₹.
Smaller plot ≈ ₹50K (basic recharge pit + downpipe routing).
Larger plot ≈ ₹2L+ (storage tank + filtration + recharge wells).
Above ₹2L only for very large or commercial setups."""

# Floor-to-floor estimate for height calculation
FLOOR_TO_FLOOR_TYPICAL_M = 3.0


# ─── Helper: build CheckResult ────────────────────────────────────────

def _build_result(
    *,
    check_id: str,
    check_name: str,
    severity: CheckSeverity,
    message: str,
    details: dict,
    category: CheckCategory = CheckCategory.COST,
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
        confidence_reason=confidence_reason, score_contribution=0,
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


def _is_rwh_legally_mandated(
    city: str, plot_area_sqm: float,
) -> tuple[bool, dict]:
    """Return (mandated, rule_dict) for the given city + plot.

    Falls back to "not mandated" if city missing from KB.
    """
    data = load_rules("rwh_approval_rules")
    rules = data["rwh_mandate_by_city"].get(city.lower())
    if rules is None:
        return False, {
            "_fallback": True,
            "authority": "Unknown (city not in v0.1 KB)",
            "regulation": "v0.1 KB covers 6 cities only",
        }
    if rules["always_mandatory"]:
        return True, rules
    threshold = rules.get("plot_area_threshold_sqm")
    if threshold is not None and plot_area_sqm >= threshold:
        return True, rules
    # Roof-area threshold (Delhi-style)
    # In v0.1 we approximate roof area = ground floor area
    # But we don't have ground floor area at this point easily;
    # use plot_area as proxy for now (conservative — overshoots slightly)
    roof_threshold = rules.get("roof_area_threshold_sqm")
    if roof_threshold is not None and plot_area_sqm >= roof_threshold:
        return True, rules
    return False, rules


# ─── Check #16: RWH mandate (branched) ────────────────────────────────

def check_rwh_practical(brief: Brief) -> CheckResult:
    """Practical RWH check: SOFT_WARN only when legally mandated for this
    plot tier, otherwise PASS (user not blocked when law doesn't require it).

    SOFT_WARN: city mandates RWH for this plot AND brief doesn't include
        RWH planning. Adds INR 50K-2L to budget.
    PASS: not legally mandated for this plot tier.
    NOT_APPLICABLE: city not in v0.1 KB.
    """
    plot_area = brief.plot.area_sqm
    city = brief.plot.city
    mandated, rules = _is_rwh_legally_mandated(city, plot_area)

    details = {
        "city": city,
        "plot_area_sqm": round(plot_area, 1),
        "always_mandatory": rules.get("always_mandatory", False),
        "threshold_sqm": rules.get("plot_area_threshold_sqm"),
        "is_mandated_for_this_plot": mandated,
        "authority": rules.get("authority"),
        "regulation": rules.get("regulation"),
        "estimated_cost_lakhs_range": list(RWH_COST_RANGE_LAKHS),
        "variant": "practical",
    }

    if rules.get("_fallback"):
        return _build_result(
            check_id="rwh_practical",
            check_name="Rainwater harvesting mandate (Practical)",
            severity=CheckSeverity.NOT_APPLICABLE,
            message=(
                f"{city.title()} not in v0.1 RWH KB — verify mandate "
                f"directly with local water board."
            ),
            details=details,
        )

    common_doubts = (
        "Q: Why does my city mandate rainwater harvesting? "
        "A: Groundwater depletion + monsoon water management. Cities "
        "with severe water stress (Chennai, Bengaluru) made it universal; "
        "others tier it by plot size.",
        "Q: What does an RWH system actually cost? "
        f"A: For a residential plot, typical range is ₹{RWH_COST_RANGE_LAKHS[0]}L-"
        f"₹{RWH_COST_RANGE_LAKHS[1]}L. Includes recharge pit, filtration, "
        f"downpipe routing, and optional storage tank.",
        "Q: Can I get water/sewer connection without RWH compliance? "
        "A: In Tamil Nadu — no. In other cities — usually yes, but "
        "you may face penalties or be flagged later.",
    )

    if mandated:
        if rules.get("always_mandatory"):
            mandate_basis = (
                f"{city.title()} mandates RWH for ALL buildings."
            )
        else:
            mandate_basis = (
                f"{city.title()} mandates RWH for plots ≥ "
                f"{rules['plot_area_threshold_sqm']} sqm. "
                f"Your plot is {plot_area:.0f} sqm."
            )
        return _build_result(
            check_id="rwh_practical",
            check_name="Rainwater harvesting mandate (Practical)",
            severity=CheckSeverity.SOFT_WARN,
            confidence=ConfidenceLevel.HIGH,
            verification_priority=VerificationPriority.IMPORTANT,
            verification_recommendation=(
                f"Confirm RWH compliance requirements with "
                f"{rules['authority']}. Water/sewer connection may be "
                f"contingent on RWH installation per "
                f"{rules['regulation']}."
            ),
            message=(
                f"{mandate_basis} Budget approximately "
                f"₹{RWH_COST_RANGE_LAKHS[0]}L-₹{RWH_COST_RANGE_LAKHS[1]}L "
                f"for installation."
            ),
            details=details,
            common_doubts=common_doubts,
        )

    return _build_result(
        check_id="rwh_practical",
        check_name="Rainwater harvesting mandate (Practical)",
        severity=CheckSeverity.PASS,
        message=(
            f"{city.title()} does not legally mandate RWH for "
            f"{plot_area:.0f} sqm plot (threshold "
            f"{rules.get('plot_area_threshold_sqm')} sqm). "
            f"Optional, but recommended for water sustainability."
        ),
        details=details,
        common_doubts=common_doubts,
    )


def check_rwh_code_strict(brief: Brief) -> CheckResult:
    """Code-Strict RWH: NBC sustainable design recommendations apply
    universally — RWH always recommended even when not legally mandated.

    SOFT_WARN: brief doesn't include RWH and city does NOT legally mandate
        (recommended-not-mandated case). Score impact moderate.
    PASS: city does mandate AND brief is implicitly compliant (we don't
        track this directly in brief — but if mandated, Practical handles it).
    """
    plot_area = brief.plot.area_sqm
    city = brief.plot.city
    mandated, rules = _is_rwh_legally_mandated(city, plot_area)

    details = {
        "city": city,
        "plot_area_sqm": round(plot_area, 1),
        "is_mandated_for_this_plot": mandated,
        "nbc_reference": "NBC 2016 Part 9 + sustainable design recommendations",
        "estimated_cost_lakhs_range": list(RWH_COST_RANGE_LAKHS),
        "variant": "code_strict",
    }

    common_doubts = (
        "Q: Code-Strict says I should add RWH even though my city "
        "doesn't require it — why? "
        "A: NBC's sustainable-design recommendations apply universally "
        "for water conservation. Code-Strict surfaces this as a "
        "recommendation; Practical respects whether your city actually "
        "requires it.",
    )

    if mandated:
        return _build_result(
            check_id="rwh_code_strict",
            check_name="Rainwater harvesting (Code-Strict)",
            severity=CheckSeverity.SOFT_WARN,
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                f"{city.title()} mandates RWH for your plot — Code-Strict "
                f"requirement aligns with city law. Budget approximately "
                f"₹{RWH_COST_RANGE_LAKHS[0]}L-₹{RWH_COST_RANGE_LAKHS[1]}L."
            ),
            details=details,
            common_doubts=common_doubts,
        )

    return _build_result(
        check_id="rwh_code_strict",
        check_name="Rainwater harvesting (Code-Strict)",
        severity=CheckSeverity.SOFT_WARN,
        verification_priority=VerificationPriority.OPTIONAL,
        message=(
            f"NBC Part 9 + sustainable design recommendations: install "
            f"RWH even though {city.title()} doesn't legally require it "
            f"for {plot_area:.0f} sqm plots. "
            f"Cost ₹{RWH_COST_RANGE_LAKHS[0]}L-₹{RWH_COST_RANGE_LAKHS[1]}L."
        ),
        details=details,
        common_doubts=common_doubts,
    )


def compute_rwh_gap(brief: Brief) -> Gap | None:
    """Gap when city does NOT mandate RWH (Practical PASS) but Code-Strict
    recommends it (SOFT_WARN). When city DOES mandate, both lanes converge
    to flagging it — no real gap.

    Returns None when the city mandates RWH (no divergence).
    Returns INFO_ONLY Gap when not mandated (Practical accepts skipping).
    """
    plot_area = brief.plot.area_sqm
    mandated, rules = _is_rwh_legally_mandated(brief.plot.city, plot_area)

    if mandated:
        return None  # No divergence

    if rules.get("_fallback"):
        return None  # Not in KB → no clear divergence

    return Gap(
        check_id="rwh",
        severity=GapSeverity.INFO_ONLY,
        practical_value={
            "rwh_required": False,
            "reason": "Not legally mandated",
            "city": brief.plot.city,
            "plot_area_sqm": round(plot_area, 1),
            "threshold_sqm": rules.get("plot_area_threshold_sqm"),
        },
        code_strict_value={
            "rwh_required": True,
            "reason": "NBC sustainable design recommendation",
            "estimated_cost_lakhs_range": list(RWH_COST_RANGE_LAKHS),
        },
        impact_description=(
            f"Practical accepts skipping RWH for {brief.plot.city.title()} "
            f"plots below mandate threshold; Code-Strict recommends RWH "
            f"per NBC sustainability. Cost adder if you choose Code-Strict: "
            f"₹{RWH_COST_RANGE_LAKHS[0]}L-₹{RWH_COST_RANGE_LAKHS[1]}L."
        ),
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )


# ─── Check #18: Approval complexity (info-only) ───────────────────────

def _classify_approval_complexity(brief: Brief) -> str:
    """Return 'simple' / 'medium' / 'complex' tier name."""
    plot_area = brief.plot.area_sqm
    floor_count = len(brief.floors)
    estimated_height_m = floor_count * FLOOR_TO_FLOOR_TYPICAL_M

    # Complex tier — large plot, very tall, or special concerns
    if plot_area > 1000 or floor_count > 7 or estimated_height_m > 18:
        return "complex"
    # Medium tier — mid-range plot or moderately tall
    if plot_area > 300 or floor_count >= 5 or estimated_height_m > 12.5:
        return "medium"
    # Simple tier — small low-rise residential
    return "simple"


def check_approval_complexity(brief: Brief) -> CheckResult:
    """Statutory approval complexity check.

    INFO-only severity (never blocks). Tells user what approval path,
    timeline, and burden to expect. The check has no Practical/Code-Strict
    branch — both lanes need the same information.

    Severity is always classified as PASS (we don't fail on this); the
    payload is in the message + details.
    """
    plot_area = brief.plot.area_sqm
    floor_count = len(brief.floors)
    estimated_height_m = floor_count * FLOOR_TO_FLOOR_TYPICAL_M
    tier = _classify_approval_complexity(brief)

    data = load_rules("rwh_approval_rules")
    tier_rules = data["approval_complexity_tiers"][tier]

    details = {
        "plot_area_sqm": round(plot_area, 1),
        "floor_count": floor_count,
        "estimated_height_m": estimated_height_m,
        "complexity_tier": tier,
        "typical_timeline_weeks": tier_rules["typical_timeline_weeks"],
        "typical_authority_path": tier_rules["typical_authority_path"],
        "typical_nocs_required": tier_rules.get("typical_nocs_required", []),
        "user_burden_summary": tier_rules["user_burden_summary"],
        "city": brief.plot.city,
    }

    common_doubts = (
        "Q: Are these timelines realistic? "
        "A: They're typical when documents are complete and the city's "
        "online portal is functional. Real timelines often slip by 50-100% "
        "due to revisions, NOC delays, or inspection scheduling.",
        "Q: Can I do this myself or do I need an architect? "
        "A: Most cities REQUIRE a licensed architect/engineer to sign "
        "the plans for any building beyond the smallest. Self-cert (where "
        "available) still needs architect-prepared drawings.",
        "Q: What's the difference between approval tiers? "
        "A: Simple = small low-rise (online portal, fast). Medium = full "
        "DA review (multiple NOCs). Complex = state + central agencies, "
        "possibly EIA. Cost + time scale up with complexity.",
    )

    # Drawback 6 fix (Session K): SOFT_WARN when tier="complex" — these
    # builds carry real time/cost/feasibility friction (16-40 weeks,
    # multiple state/central NOCs, possible EIA). PASS for simple/medium.
    severity = (
        CheckSeverity.SOFT_WARN if tier == "complex"
        else CheckSeverity.PASS
    )
    if tier == "complex":
        message = (
            f"Approval tier: COMPLEX — expect "
            f"{tier_rules['typical_timeline_weeks']} weeks via "
            f"{tier_rules['typical_authority_path']}. "
            f"{tier_rules['user_burden_summary']} Plan budget + timeline "
            f"with this overhead in mind."
        )
    else:
        message = (
            f"Approval tier: {tier.upper()} — typical timeline "
            f"{tier_rules['typical_timeline_weeks']} weeks via "
            f"{tier_rules['typical_authority_path']}. "
            f"{tier_rules['user_burden_summary']}"
        )

    return _build_result(
        check_id="approval_complexity",
        check_name="Statutory approval complexity",
        category=CheckCategory.COMPLIANCE,
        severity=severity,
        confidence=ConfidenceLevel.HIGH,
        message=message,
        details=details,
        common_doubts=common_doubts,
    )
