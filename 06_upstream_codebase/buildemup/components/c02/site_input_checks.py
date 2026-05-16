"""
Component 2 — Soil + Water Table branched checks (Session E).

These are the first checks to use the FeasibilityInput 3-state pattern
properly. Both fields (soil_type, water_table_depth_m) are commonly
unknown to homeowners, so the "I don't know → city default + LOW conf"
flow is the primary code path.

Critical principle (user-approved): when an ASSUMED city-default value
would HARD_FAIL the check, downgrade severity to SOFT_WARN. When the
value is USER_PROVIDED (verified or unverified), keep HARD_FAIL as is.

Rationale: a homeowner who guessed wrong shouldn't be blocked when the
guess was the system's, not theirs. But a homeowner who provided real
data and that data shows a HARD violation deserves a HARD warning.

NBC anchors:
  - IS 1892, IS 6403: soil bearing capacity for foundation design
  - NBC Part 3 cl. 6.2: damp site / water table considerations
"""
from __future__ import annotations

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority, Gap, GapSeverity, DecisionSource,
)
from buildemup.components.c02.scoring import compute_score_contribution
from buildemup.components.c02.feasibility_input import (
    FeasibilityInput, FieldSource, InputField,
)
from buildemup.utils.kb_rules_loader import load_rules


# ─── Constants ────────────────────────────────────────────────────────

SOIL_HIGH_RISK_TYPES = ("black_cotton", "soft_clay", "loose_fill")
"""Soil types that carry significant settlement / swelling risk for
shallow foundations on G+1+ buildings."""

SOIL_TYPICAL_RISK_TYPES = ("clay", "silty_clay", "alluvial_silty_clay")
"""Soil types where bearing capacity is moderate but settlement
considerations apply."""

SOIL_LOW_RISK_TYPES = (
    "laterite", "weathered_rock", "sandy_alluvial",
    "coastal_alluvial", "mixed", "rock",
)
"""Soil types with adequate bearing for typical residential design."""

# Floor count thresholds for risk escalation
FLOOR_COUNT_FOR_DEEP_FOUNDATION_THRESHOLD = 2
"""G+1 (2 floors) is the typical break-point above which foundation
design becomes critical for high-risk soils."""

# Water table thresholds
WATER_TABLE_VERY_SHALLOW_M = 1.5
"""Below this depth in monsoon, basement construction is very difficult
and damp-proofing is critical for ground floor."""

WATER_TABLE_SHALLOW_M = 3.0
"""Below this depth, special damp-proofing measures recommended for
ground floor; basement construction needs robust waterproofing."""


# ─── Helper: build CheckResult ────────────────────────────────────────

def _build_result(
    *,
    check_id: str,
    check_name: str,
    severity: CheckSeverity,
    message: str,
    details: dict,
    category: CheckCategory = CheckCategory.STRUCTURAL,
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


def _get_city_defaults(city: str) -> dict:
    """Look up city defaults; falls back to chennai if city missing."""
    data = load_rules("city_feasibility_defaults")
    return data.get(city.lower(), data["chennai"])


def _resolve_soil_type(
    soil_field: InputField, brief: Brief,
) -> tuple[str, ConfidenceLevel, str | None]:
    """Get effective soil type + confidence + assumption description.

    Returns:
        (soil_type, confidence, assumption_used)
        assumption_used is None if user provided value, else description.
    """
    if soil_field.is_user_data_present:
        return soil_field.value, soil_field.confidence_level, None
    # Use city default
    defaults = _get_city_defaults(brief.plot.city)
    return (
        defaults["soil_type"],
        ConfidenceLevel.LOW,
        f"Assumed {defaults['soil_type']} (typical for "
        f"{brief.plot.city.title()})",
    )


def _resolve_water_table(
    wt_field: InputField, brief: Brief,
) -> tuple[float, ConfidenceLevel, str | None]:
    """Get effective water table depth + confidence + assumption.

    For city default, uses post-monsoon (wettest case = most
    conservative for foundation design).
    """
    if wt_field.is_user_data_present:
        return wt_field.value, wt_field.confidence_level, None
    defaults = _get_city_defaults(brief.plot.city)
    wt_m = defaults["water_table_depth_m_postmonsoon"]
    return (
        wt_m,
        ConfidenceLevel.LOW,
        f"Assumed {wt_m}m post-monsoon water table (typical for "
        f"{brief.plot.city.title()} per CGWB)",
    )


def _maybe_downgrade_severity(
    severity: CheckSeverity, source: FieldSource,
) -> tuple[CheckSeverity, str | None]:
    """Apply user-approved 'don't HARD-fail on a guess' rule.

    Returns (new_severity, downgrade_note).

    If severity == HARD_FAIL AND source is DOESNT_KNOW or NOT_ASKED,
    downgrade to SOFT_WARN with an explanatory note.
    Otherwise, no change.
    """
    if severity == CheckSeverity.HARD_FAIL and source in (
        FieldSource.USER_DOESNT_KNOW, FieldSource.NOT_ASKED,
    ):
        return CheckSeverity.SOFT_WARN, (
            "Severity downgraded from HARD_FAIL to SOFT_WARN because "
            "the value used was a city-default assumption, not user-"
            "verified data. Get site-specific verification to confirm."
        )
    return severity, None


# ─── Check #12: Soil type risk (branched) ─────────────────────────────

def _classify_soil_risk(soil_type: str, floor_count: int) -> tuple[
    CheckSeverity, str
]:
    """Return (severity, reason) for soil-type + floor-count combination."""
    soil_lower = soil_type.lower()

    if soil_lower in SOIL_HIGH_RISK_TYPES:
        if floor_count > FLOOR_COUNT_FOR_DEEP_FOUNDATION_THRESHOLD:
            return CheckSeverity.HARD_FAIL, (
                f"Soil '{soil_type}' is high-risk for shallow foundations. "
                f"With {floor_count} floors, deep/pile foundation is "
                f"essential — proceeding with shallow footings would risk "
                f"differential settlement, cracking, and structural failure."
            )
        return CheckSeverity.SOFT_WARN, (
            f"Soil '{soil_type}' has known settlement / swelling risks. "
            f"For {floor_count}-floor build, consider raft or under-reamed "
            f"piles, or budget for soil replacement."
        )
    if soil_lower in SOIL_TYPICAL_RISK_TYPES:
        if floor_count > FLOOR_COUNT_FOR_DEEP_FOUNDATION_THRESHOLD:
            return CheckSeverity.SOFT_WARN, (
                f"Soil '{soil_type}' has moderate bearing capacity. With "
                f"{floor_count} floors, soil test before final foundation "
                f"design strongly recommended."
            )
        return CheckSeverity.PASS, (
            f"Soil '{soil_type}' has adequate bearing for {floor_count}-"
            f"floor build with standard strip footings."
        )
    return CheckSeverity.PASS, (
        f"Soil '{soil_type}' has good bearing capacity — standard "
        f"foundation design adequate for {floor_count}-floor build."
    )


def check_soil_type_practical(
    inp: FeasibilityInput,
) -> CheckResult:
    """Practical soil check: same soil-risk classification but downgrade
    HARD_FAIL to SOFT_WARN when soil type is assumed (not user-verified).

    User who provided a verified soil type → strict outcome.
    User who said 'don't know' → city-default with confidence-aware
    severity (HARD risks become SOFT to avoid blocking on a guess).
    """
    soil_type, confidence, assumption_used = _resolve_soil_type(
        inp.soil_type, inp.brief,
    )
    floor_count = len(inp.brief.floors)

    raw_severity, base_message = _classify_soil_risk(soil_type, floor_count)
    final_severity, downgrade_note = _maybe_downgrade_severity(
        raw_severity, inp.soil_type.source,
    )

    # If we downgraded, append note to message
    message = base_message
    if downgrade_note:
        message = base_message + " " + downgrade_note

    confidence_reason = None
    verification_recommendation = None
    verification_priority = VerificationPriority.OPTIONAL

    if assumption_used is not None:
        # Used city default
        confidence_reason = (
            f"User did not provide soil type — used city-default "
            f"({inp.brief.plot.city.title()}) educated guess."
        )
        verification_recommendation = (
            "Get a site-specific soil test from a NABL-accredited "
            "geotechnical lab. Cost: ₹5,000-₹15,000. Timeline: 3-5 "
            "days. Look for: bearing capacity, soil type, water table, "
            "chemical composition. Trusted labs in your city: search "
            "'NABL accredited geotech lab + " + inp.brief.plot.city + "'."
        )
        verification_priority = (
            VerificationPriority.CRITICAL
            if raw_severity == CheckSeverity.HARD_FAIL
            else VerificationPriority.IMPORTANT
        )
    elif inp.soil_type.source == FieldSource.USER_PROVIDED_UNVERIFIED:
        confidence_reason = (
            "User-provided value but not verified by lab test."
        )
        verification_recommendation = (
            "Confirm soil type with a NABL-accredited geotechnical lab "
            "test before final foundation design (₹5K-₹15K, 3-5 days)."
        )
        verification_priority = VerificationPriority.IMPORTANT

    common_doubts = (
        "Q: How do I know what soil I have without a test? "
        "A: You can do a coarse visual check — black soil that cracks "
        "in summer = black cotton (high risk). Reddish iron-rich soil "
        "= laterite (good). Dig a 1m pit; if water seeps in fast, you "
        "have sandy soil. But any G+1+ build needs a lab test.",
        "Q: Why does my city's typical soil affect my plot? "
        "A: It's a starting estimate. Real plots vary plot-by-plot, "
        "even within the same neighbourhood. The city default tells "
        "us what's likely; the soil test tells us what's actually there.",
    )

    details = {
        "soil_type_used": soil_type,
        "floor_count": floor_count,
        "raw_severity": raw_severity.value,
        "final_severity": final_severity.value,
        "data_source": inp.soil_type.source.value,
        "downgrade_applied": downgrade_note is not None,
        "city": inp.brief.plot.city,
        "variant": "practical",
    }

    return _build_result(
        check_id="soil_type_practical",
        check_name="Soil type risk (Practical)",
        severity=final_severity,
        confidence=confidence,
        confidence_reason=confidence_reason,
        message=message,
        details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )


def check_soil_type_code_strict(
    inp: FeasibilityInput,
) -> CheckResult:
    """Code-Strict soil check: NBC + IS 1892 mandate soil testing for
    any RCC structure G+1+. Without verified soil data, a strict-NBC
    project cannot proceed.

    HARD_FAIL: floor_count > 1 AND soil data NOT verified.
    PASS: soil data verified OR single-floor build.
    """
    floor_count = len(inp.brief.floors)
    is_verified = inp.soil_type.source == FieldSource.USER_PROVIDED_VERIFIED

    details = {
        "floor_count": floor_count,
        "soil_data_source": inp.soil_type.source.value,
        "is_verified": is_verified,
        "nbc_reference": "IS 1892, IS 6403 (soil testing requirements)",
        "variant": "code_strict",
    }

    if floor_count <= 1:
        return _build_result(
            check_id="soil_type_code_strict",
            check_name="Soil type compliance (Code-Strict)",
            severity=CheckSeverity.PASS,
            message=(
                "Single-floor build — soil testing is recommended but "
                "not strictly mandated by NBC."
            ),
            details=details,
        )

    if is_verified:
        # Verified soil type — code-strict still passes
        return _build_result(
            check_id="soil_type_code_strict",
            check_name="Soil type compliance (Code-Strict)",
            severity=CheckSeverity.PASS,
            message=(
                f"Soil data verified ({inp.soil_type.value}) — meets "
                f"NBC + IS 1892 soil-testing requirement for "
                f"{floor_count}-floor RCC structure."
            ),
            details=details,
        )

    return _build_result(
        check_id="soil_type_code_strict",
        check_name="Soil type compliance (Code-Strict)",
        severity=CheckSeverity.HARD_FAIL,
        confidence=ConfidenceLevel.HIGH,
        verification_priority=VerificationPriority.CRITICAL,
        verification_recommendation=(
            "NBC + IS 1892 mandate soil bearing capacity testing for "
            "any RCC structure beyond G+0. Get a NABL-accredited "
            "geotech lab report (₹5K-₹15K, 3-5 days) before proceeding."
        ),
        message=(
            f"Code-Strict requires verified soil data for "
            f"{floor_count}-floor RCC structure (NBC + IS 1892). "
            f"User has not provided lab-verified soil test."
        ),
        details=details,
    )


def compute_soil_type_gap(inp: FeasibilityInput) -> Gap | None:
    """Gap when Practical accepts soil-risk-on-a-guess that CodeStrict refuses.

    Returns None when both lanes pass (single floor, OR soil verified).
    """
    floor_count = len(inp.brief.floors)
    if floor_count <= 1:
        return None  # Both pass for single-floor

    is_verified = inp.soil_type.source == FieldSource.USER_PROVIDED_VERIFIED
    if is_verified:
        return None  # Both pass when verified

    # Code-Strict fails (no verified soil data) but Practical might pass
    # or soft-warn. Either way → BLOCKING_IF_NOT_ACCEPTED gap.
    soil_type_used, _, assumption_used = _resolve_soil_type(
        inp.soil_type, inp.brief,
    )
    return Gap(
        check_id="soil_type",
        severity=GapSeverity.BLOCKING_IF_NOT_ACCEPTED,
        practical_value={
            "soil_type": soil_type_used,
            "data_source": inp.soil_type.source.value,
            "assumption_used": assumption_used,
        },
        code_strict_value={
            "requires_verified_soil_test": True,
            "reference": "NBC + IS 1892",
        },
        impact_description=(
            f"Practical accepts unverified/assumed soil data for "
            f"{floor_count}-floor build; Code-Strict requires "
            f"NBC + IS 1892 lab-verified soil test."
        ),
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )


# ─── Check #13: Water table risk (branched) ───────────────────────────

def _classify_water_table_risk(
    wt_depth_m: float, brief: Brief,
) -> tuple[CheckSeverity, str]:
    """Return (severity, reason) for water table depth + brief features."""
    from buildemup.domain.floor_requirement import FloorUse

    has_basement = any(
        getattr(f.floor_use, "value", str(f.floor_use)) == "basement"
        for f in brief.floors
    )

    if wt_depth_m < WATER_TABLE_VERY_SHALLOW_M:
        if has_basement:
            return CheckSeverity.HARD_FAIL, (
                f"Water table at {wt_depth_m:.1f}m is too shallow for "
                f"basement construction. Persistent water ingress + "
                f"flotation risk."
            )
        return CheckSeverity.SOFT_WARN, (
            f"Water table at {wt_depth_m:.1f}m is very shallow. "
            f"Strong damp-proofing required for ground floor (DPC + "
            f"plinth waterproofing). Budget for waterproofing measures."
        )
    if wt_depth_m < WATER_TABLE_SHALLOW_M:
        if has_basement:
            return CheckSeverity.SOFT_WARN, (
                f"Water table at {wt_depth_m:.1f}m requires robust "
                f"basement waterproofing (membrane + drainage)."
            )
        return CheckSeverity.SOFT_WARN, (
            f"Water table at {wt_depth_m:.1f}m is moderately shallow. "
            f"Standard damp-proofing course (DPC) recommended at plinth."
        )
    return CheckSeverity.PASS, (
        f"Water table at {wt_depth_m:.1f}m is deep enough for standard "
        f"foundation + damp-proofing."
    )


def check_water_table_practical(
    inp: FeasibilityInput,
) -> CheckResult:
    """Practical water table check: downgrades HARD to SOFT for assumptions."""
    wt_m, confidence, assumption_used = _resolve_water_table(
        inp.water_table_depth_m, inp.brief,
    )

    raw_severity, base_message = _classify_water_table_risk(wt_m, inp.brief)
    final_severity, downgrade_note = _maybe_downgrade_severity(
        raw_severity, inp.water_table_depth_m.source,
    )

    message = base_message
    if downgrade_note:
        message = base_message + " " + downgrade_note

    confidence_reason = None
    verification_recommendation = None
    verification_priority = VerificationPriority.OPTIONAL

    if assumption_used is not None:
        confidence_reason = (
            f"User did not provide water table depth — used CGWB "
            f"city-typical post-monsoon depth for "
            f"{inp.brief.plot.city.title()}."
        )
        verification_recommendation = (
            "Check CGWB district report for your area "
            "(https://cgwb.gov.in — free). Or commission a borewell "
            "survey from a local hydrogeologist (₹2K-₹8K) for the "
            "wettest-month depth at your specific plot."
        )
        verification_priority = (
            VerificationPriority.CRITICAL
            if raw_severity == CheckSeverity.HARD_FAIL
            else VerificationPriority.IMPORTANT
        )

    common_doubts = (
        "Q: Why does the water table matter for my house? "
        "A: A shallow water table affects foundation design, basement "
        "feasibility, damp-proofing requirements, and concrete "
        "durability (saline groundwater corrodes rebar). Wettest-month "
        "depth matters most — that's when waterproofing is tested.",
        "Q: How accurate is the city default? "
        "A: It's an average; your plot may be much deeper or shallower "
        "depending on local geology, distance from water bodies, and "
        "elevation. Always verify before basement construction.",
    )

    details = {
        "water_table_depth_m": wt_m,
        "raw_severity": raw_severity.value,
        "final_severity": final_severity.value,
        "data_source": inp.water_table_depth_m.source.value,
        "downgrade_applied": downgrade_note is not None,
        "city": inp.brief.plot.city,
        "variant": "practical",
    }

    return _build_result(
        check_id="water_table_practical",
        check_name="Water table risk (Practical)",
        severity=final_severity,
        confidence=confidence,
        confidence_reason=confidence_reason,
        message=message,
        details=details,
        assumption_used=assumption_used,
        verification_recommendation=verification_recommendation,
        verification_priority=verification_priority,
        common_doubts=common_doubts,
    )


def check_water_table_code_strict(
    inp: FeasibilityInput,
) -> CheckResult:
    """Code-Strict water table check: NBC Part 3 cl. 6.2 mandates damp-
    site verification before any habitable construction.

    HARD_FAIL: water table data not user-verified AND brief has habitable
        ground floor or basement.
    PASS: data verified, OR brief is upper-floor-only.
    """
    is_verified = inp.water_table_depth_m.source == FieldSource.USER_PROVIDED_VERIFIED
    from buildemup.domain.floor_requirement import FloorUse

    has_habitable_ground = any(
        getattr(f.floor_use, "value", str(f.floor_use)) == "residential"
        and f.floor_number == 0
        for f in inp.brief.floors
    )

    details = {
        "is_verified": is_verified,
        "data_source": inp.water_table_depth_m.source.value,
        "has_habitable_ground": has_habitable_ground,
        "nbc_reference": "NBC 2016 Part 3 cl. 6.2 (damp site requirements)",
        "variant": "code_strict",
    }

    if not has_habitable_ground:
        return _build_result(
            check_id="water_table_code_strict",
            check_name="Water table compliance (Code-Strict)",
            severity=CheckSeverity.PASS,
            message=(
                "Brief has no habitable ground floor — NBC damp-site "
                "verification not strictly required."
            ),
            details=details,
        )

    if is_verified:
        return _build_result(
            check_id="water_table_code_strict",
            check_name="Water table compliance (Code-Strict)",
            severity=CheckSeverity.PASS,
            message=(
                f"Water table verified at {inp.water_table_depth_m.value}m "
                f"— meets NBC damp-site verification requirement."
            ),
            details=details,
        )

    return _build_result(
        check_id="water_table_code_strict",
        check_name="Water table compliance (Code-Strict)",
        severity=CheckSeverity.HARD_FAIL,
        confidence=ConfidenceLevel.HIGH,
        verification_priority=VerificationPriority.CRITICAL,
        verification_recommendation=(
            "NBC Part 3 cl. 6.2 requires verified damp-site assessment "
            "before habitable construction. Get CGWB district report or "
            "site-specific borewell survey."
        ),
        message=(
            "Code-Strict requires verified water table data for habitable "
            "ground-floor construction (NBC Part 3 cl. 6.2). User has "
            "not provided verified data."
        ),
        details=details,
    )


def compute_water_table_gap(inp: FeasibilityInput) -> Gap | None:
    """Gap between Practical (assumed-OK) and Code-Strict (verified-required)."""
    is_verified = inp.water_table_depth_m.source == FieldSource.USER_PROVIDED_VERIFIED
    if is_verified:
        return None
    from buildemup.domain.floor_requirement import FloorUse
    has_habitable_ground = any(
        getattr(f.floor_use, "value", str(f.floor_use)) == "residential"
        and f.floor_number == 0
        for f in inp.brief.floors
    )
    if not has_habitable_ground:
        return None  # Both lanes pass

    wt_used, _, assumption_used = _resolve_water_table(
        inp.water_table_depth_m, inp.brief,
    )
    return Gap(
        check_id="water_table",
        severity=GapSeverity.BLOCKING_IF_NOT_ACCEPTED,
        practical_value={
            "water_table_depth_m": wt_used,
            "data_source": inp.water_table_depth_m.source.value,
            "assumption_used": assumption_used,
        },
        code_strict_value={
            "requires_verified_water_table": True,
            "reference": "NBC Part 3 cl. 6.2",
        },
        impact_description=(
            f"Practical accepts assumed/unverified water table "
            f"({wt_used:.1f}m) for habitable ground-floor; Code-Strict "
            f"requires NBC-verified damp-site assessment."
        ),
        user_acceptable=None,
        decision_source=DecisionSource.SYSTEM_DEFAULT,
    )
