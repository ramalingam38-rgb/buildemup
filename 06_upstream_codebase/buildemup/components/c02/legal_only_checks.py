"""
Component 2 — Legal-only checks (Session B scope).

These 6 checks are governed by hard legal rules with no Practical-vs-CodeStrict
split. A municipal authority will reject the building plan if any HARD_FAILs:

  - far_compliance: total built area / plot area must be ≤ city max FAR
  - ground_coverage_compliance: footprint / plot area must be ≤ city max GC
  - fire_tender_access: road width must support fire tender (NBC Part 4)
  - electric_line_clearance: distance from HT/LT lines (NBC Part 3, 6.4)
  - water_course_clearance: distance from drains/streams (NBC Part 3, 6.5)
  - stilt_mandate_compliance: cities mandate stilt for plot tiers

Three of these (electric line, water course, stilt mandate) need user
input that may not be in the Brief. For Session B we use sensible
defaults — Session E will add the proper 3-state "I don't know" pattern.

For Session B "user might not know" fields, defaults are:
  - distance_from_electric_line_m: assumed > 5m (no overhead lines visible)
  - distance_from_water_course_m: assumed > 30m (no nearby drain/stream)
  - These default to PASS with confidence_reason="user did not specify"
"""
from __future__ import annotations

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    CheckResult, CheckSeverity, CheckCategory, ConfidenceLevel,
    VerificationPriority,
)
from buildemup.components.c02.scoring import compute_score_contribution
from buildemup.utils.kb_rules_loader import load_rules


# ─── Constants ────────────────────────────────────────────────────────
# NBC Part 4 (Fire and Life Safety) values:
NBC_FIRE_TENDER_MIN_ROAD_WIDTH_M = 6.0
"""Minimum road width for fire tender movement, NBC Part 4 + IFC."""

NBC_FIRE_TENDER_MIN_ROAD_FOR_HIGHRISE_M = 12.0
"""For buildings >15m height (G+4+), road must be ≥12m."""

NBC_HIGH_RISE_HEIGHT_THRESHOLD_M = 15.0
"""NBC threshold above which a building is "high-rise" — G+4 typical."""

NBC_FLOOR_TO_FLOOR_TYPICAL_M = 3.0
"""Used to estimate building height from floor count."""

# NBC Part 3 Clause 6.4-6.5 (Plot requirements) — minimum clearances
NBC_MIN_DISTANCE_ELECTRIC_LINE_LT_M = 1.2
"""Minimum horizontal clearance from low-tension overhead line (≤650V).
NBC Part 3 + IS 5613 + Indian Electricity Rules. Voltage-tiered."""

NBC_MIN_DISTANCE_ELECTRIC_LINE_HT_M = 3.7
"""Minimum horizontal clearance from high-tension overhead line.
Used as conservative default — real distance varies by voltage."""

NBC_MIN_DISTANCE_WATER_COURSE_M = 9.0
"""Minimum setback from natural drain/stream/storm channel.
NBC Part 3 Clause 6.5. Cities may add stricter local rules
(NGT orders for specific rivers can require 30m+)."""

# Stilt mandate (Drawback #17) — known cities and thresholds
STILT_MANDATE_BY_CITY: dict[str, dict] = {
    "delhi": {
        "min_plot_sqm": 100,
        "max_plot_sqm": 1000,
        "source": "Delhi notification (separate from UBBL itself)",
    },
    # Other 5 cities don't mandate stilt for residential by plot size
    # alone — depends on floor count + parking norms which vary.
    # Conservative v0.1: only Delhi modelled.
}


# ─── Helper: build CheckResult with auto-computed score ───────────────

def _build_result(
    *,
    check_id: str,
    check_name: str,
    severity: CheckSeverity,
    message: str,
    details: dict,
    category: CheckCategory = CheckCategory.COMPLIANCE,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    confidence_reason: str | None = None,
    assumption_used: str | None = None,
    verification_recommendation: str | None = None,
    verification_priority: VerificationPriority = VerificationPriority.OPTIONAL,
    common_doubts: tuple[str, ...] = (),
) -> CheckResult:
    """Build a CheckResult, computing score_contribution via scoring.py."""
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


def _get_city_coverage_rules(city: str) -> dict:
    """Load city-specific coverage rules from KB.

    Falls back to "chennai" if city not in KB (defensive — should never
    happen for the 6 launch cities).
    """
    rules = load_rules("coverage_rules")
    # Direct lookup
    if city in rules:
        return rules[city]
    # Lowercase fallback
    if city.lower() in rules:
        return rules[city.lower()]
    # Defensive: use chennai as default
    return rules["chennai"]


def _compute_total_built_area_sqm(brief: Brief) -> float:
    """Compute total built area across all floors INCLUDING circulation.

    Uses Component 1's existing helper estimate_total_built_area_sqm
    (1.30 circulation factor). Stilt parking floors are EXCLUDED from
    FAR (national convention across all 6 cities).
    """
    from buildemup.domain.floor_requirement import FloorUse
    from buildemup.components.c01.room_composer import (
        estimate_total_built_area_sqm,
    )
    # Filter out stilt floors then run estimator on the rest
    non_stilt = tuple(
        f for f in brief.floors if f.floor_use != FloorUse.STILT_PARKING
    )
    if not non_stilt:
        return 0.0
    return estimate_total_built_area_sqm(non_stilt)


def _compute_ground_floor_built_area_sqm(brief: Brief) -> float:
    """Ground footprint = floor 0's built area (rooms × circulation factor)."""
    from buildemup.components.c01.room_composer import (
        estimate_total_built_area_sqm,
    )
    if not brief.floors:
        return 0.0
    # Only floor 0 — pass it as a single-floor tuple to the helper
    return estimate_total_built_area_sqm((brief.floors[0],))


# ─── Check #10: FAR compliance ────────────────────────────────────────

def check_far_compliance(brief: Brief) -> CheckResult:
    """Check whether total built area / plot area ≤ city max FAR.

    HARD_FAIL: actual FAR > city max (rejection by municipality guaranteed).
    SOFT_WARN: actual FAR > 90% of max (very close, may need premium).
    PASS: actual FAR ≤ 90% of max.

    Confidence is HIGH because both numbers are well-known from the brief.
    """
    plot_area = brief.plot.area_sqm
    if plot_area <= 0:
        return _build_result(
            check_id="far_compliance",
            check_name="FAR (Floor Area Ratio) compliance",
            severity=CheckSeverity.NOT_APPLICABLE,
            message="Plot area is zero — FAR check skipped.",
            details={},
        )

    rules = _get_city_coverage_rules(brief.plot.city)
    max_far = rules["base_far"]
    # Delhi small-plot exception
    if "small_plot_far" in rules:
        sp = rules["small_plot_far"]
        if plot_area <= sp["threshold_sqm"]:
            max_far = sp["uniform_far"]

    total_built = _compute_total_built_area_sqm(brief)
    actual_far = total_built / plot_area

    details = {
        "plot_area_sqm": round(plot_area, 1),
        "total_built_area_sqm": round(total_built, 1),
        "actual_far": round(actual_far, 3),
        "city_max_far": max_far,
        "city": brief.plot.city,
        "authority": rules["authority"],
        "regulation": rules["regulation"],
    }

    common_doubts = (
        f"Q: Why does my city allow only FAR {max_far}? "
        f"A: It's set by {rules['authority']} to control density per "
        f"{rules['regulation']}. Some cities allow premium FSI on payment.",
        "Q: Are stilt parking and basement counted? "
        "A: No — all 6 launch cities exclude stilt + basement from FAR. "
        "Mumty (top staircase room) and lift shaft are also typically excluded.",
    )

    if actual_far > max_far:
        excess_pct = ((actual_far - max_far) / max_far) * 100
        return _build_result(
            check_id="far_compliance",
            check_name="FAR (Floor Area Ratio) compliance",
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Total built area {total_built:.0f} sqm ÷ plot {plot_area:.0f} sqm "
                f"= FAR {actual_far:.2f}, exceeding {brief.plot.city.title()}'s "
                f"max FAR {max_far:.2f} by {excess_pct:.0f}%. "
                f"Reduce floors or built area, or apply for premium FSI "
                f"(extra payment, not guaranteed)."
            ),
            details=details,
            verification_priority=VerificationPriority.CRITICAL,
            common_doubts=common_doubts,
        )
    if actual_far > max_far * 0.90:
        return _build_result(
            check_id="far_compliance",
            check_name="FAR (Floor Area Ratio) compliance",
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"FAR {actual_far:.2f} is {(actual_far/max_far)*100:.0f}% of "
                f"city max {max_far:.2f}. Tight margin — any design tweaks "
                f"that add floor area may push you over."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="far_compliance",
        check_name="FAR (Floor Area Ratio) compliance",
        severity=CheckSeverity.PASS,
        message=(
            f"FAR {actual_far:.2f} is well within "
            f"{brief.plot.city.title()}'s max {max_far:.2f}."
        ),
        details=details,
    )


# ─── Check #9: Ground coverage compliance ─────────────────────────────

def check_ground_coverage_compliance(brief: Brief) -> CheckResult:
    """Check whether ground footprint / plot area ≤ city max GC%.

    Different from FAR — GC is just the ground floor footprint percentage.
    Most rejections happen here on small plots that try to maximise floor 0.

    HARD_FAIL: actual GC > city max GC.
    SOFT_WARN: actual GC > 95% of max.
    PASS: actual GC ≤ 95% of max.
    """
    plot_area = brief.plot.area_sqm
    if plot_area <= 0:
        return _build_result(
            check_id="ground_coverage_compliance",
            check_name="Ground coverage compliance",
            severity=CheckSeverity.NOT_APPLICABLE,
            message="Plot area is zero — ground coverage check skipped.",
            details={},
        )

    rules = _get_city_coverage_rules(brief.plot.city)
    max_gc = rules["max_ground_coverage_pct"]
    # Delhi small-plot exception
    if "small_plot_far" in rules and plot_area <= rules["small_plot_far"]["threshold_sqm"]:
        max_gc = rules["small_plot_far"]["max_ground_coverage_pct"]

    ground_floor_area = _compute_ground_floor_built_area_sqm(brief)
    actual_gc_pct = (ground_floor_area / plot_area) * 100

    details = {
        "plot_area_sqm": round(plot_area, 1),
        "ground_floor_area_sqm": round(ground_floor_area, 1),
        "actual_gc_pct": round(actual_gc_pct, 1),
        "city_max_gc_pct": max_gc,
        "city": brief.plot.city,
        "regulation": rules["regulation"],
    }

    common_doubts = (
        f"Q: Why does my city limit ground coverage to {max_gc}%? "
        f"A: For light, ventilation, and fire access. The remainder is "
        f"setback area which can't be built on at ground level.",
        "Q: Can I get more ground coverage if I have stilt parking? "
        "A: Stilt is included in ground coverage — only setback area "
        "is open. Some cities count stilt; some don't (varies by DCR).",
    )

    if actual_gc_pct > max_gc:
        return _build_result(
            check_id="ground_coverage_compliance",
            check_name="Ground coverage compliance",
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Ground footprint {ground_floor_area:.0f} sqm "
                f"({actual_gc_pct:.0f}% of plot) exceeds "
                f"{brief.plot.city.title()}'s max {max_gc}%. "
                f"Reduce ground floor footprint or increase setbacks."
            ),
            details=details,
            verification_priority=VerificationPriority.CRITICAL,
            common_doubts=common_doubts,
        )
    if actual_gc_pct > max_gc * 0.95:
        return _build_result(
            check_id="ground_coverage_compliance",
            check_name="Ground coverage compliance",
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Ground coverage {actual_gc_pct:.0f}% is at {actual_gc_pct/max_gc*100:.0f}% "
                f"of city max {max_gc}%. Tight margin on layout."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="ground_coverage_compliance",
        check_name="Ground coverage compliance",
        severity=CheckSeverity.PASS,
        message=(
            f"Ground coverage {actual_gc_pct:.0f}% within "
            f"{brief.plot.city.title()}'s max {max_gc}%."
        ),
        details=details,
    )


# ─── Check #11: Fire tender access ────────────────────────────────────

def check_fire_tender_access(brief: Brief) -> CheckResult:
    """Check whether plot's road width supports fire tender access.

    NBC Part 4: minimum 6m for any building. Buildings >15m (G+4+) need
    minimum 12m road. User-provided road_width is verified physical fact
    so HARD fails are honest HARDs (not soft-warnable).

    HARD_FAIL:
      - Building height >15m and road <12m
      - Building height ≤15m and road <6m
    SOFT_WARN: Road width ≥6m but <8m (tight for tender turning radius).
    PASS: Road width ≥8m.
    """
    road_width = brief.plot.road_width_m
    floor_count = len(brief.floors)
    estimated_height = floor_count * NBC_FLOOR_TO_FLOOR_TYPICAL_M
    is_high_rise = estimated_height > NBC_HIGH_RISE_HEIGHT_THRESHOLD_M

    details = {
        "road_width_m": road_width,
        "floor_count": floor_count,
        "estimated_height_m": estimated_height,
        "is_high_rise": is_high_rise,
        "nbc_min_for_low_rise_m": NBC_FIRE_TENDER_MIN_ROAD_WIDTH_M,
        "nbc_min_for_high_rise_m": NBC_FIRE_TENDER_MIN_ROAD_FOR_HIGHRISE_M,
    }

    required_min = (
        NBC_FIRE_TENDER_MIN_ROAD_FOR_HIGHRISE_M if is_high_rise
        else NBC_FIRE_TENDER_MIN_ROAD_WIDTH_M
    )

    common_doubts = (
        "Q: My road is narrow but ambulances reach my house — why does "
        "fire access matter? "
        "A: Fire tenders are 22 tonnes (low-rise) or 45 tonnes (high-rise) "
        "and need clearance for turning + outrigger deployment. NBC is "
        "stricter than ambulance access.",
        f"Q: Can I get an exception with a narrower road? "
        f"A: Some cities allow undertakings for narrow lanes with "
        f"alternate access. Check with {brief.plot.city.title()} fire "
        f"services NOC office before assuming.",
    )

    if road_width < required_min:
        return _build_result(
            check_id="fire_tender_access",
            check_name="Fire tender access",
            category=CheckCategory.SAFETY,
            severity=CheckSeverity.HARD_FAIL,
            message=(
                f"Road width {road_width}m is below NBC minimum {required_min}m "
                f"for {'high-rise' if is_high_rise else 'low-rise'} "
                f"({floor_count} floors, ~{estimated_height:.0f}m height). "
                f"Fire tender cannot reach the building. "
                f"Either reduce floor count to ≤4 (G+3) "
                f"{'(brings height under 15m threshold)' if is_high_rise else ''} "
                f"or get a wider access road dedicated to your plot."
            ),
            details=details,
            verification_priority=VerificationPriority.CRITICAL,
            common_doubts=common_doubts,
        )
    if road_width < 8.0 and not is_high_rise:
        return _build_result(
            check_id="fire_tender_access",
            check_name="Fire tender access",
            category=CheckCategory.SAFETY,
            severity=CheckSeverity.SOFT_WARN,
            message=(
                f"Road width {road_width}m meets NBC minimum {required_min}m "
                f"but is tight for fire tender turning radius. "
                f"Recommended ≥8m for comfortable access."
            ),
            details=details,
            common_doubts=common_doubts,
        )
    return _build_result(
        check_id="fire_tender_access",
        check_name="Fire tender access",
        category=CheckCategory.SAFETY,
        severity=CheckSeverity.PASS,
        message=(
            f"Road width {road_width}m supports fire tender access "
            f"({'high-rise' if is_high_rise else 'low-rise'} required ≥{required_min}m)."
        ),
        details=details,
    )


# ─── Check #14: Electric line clearance ───────────────────────────────

def check_electric_line_clearance(
    brief: Brief,
    distance_from_electric_line_m: float | None = None,
    line_type: str = "unknown",  # "lt" | "ht" | "unknown"
) -> CheckResult:
    """Check NBC Part 3 Clause 6.4 electric line clearance.

    User-provided distance overrides default. If user said "I don't know",
    pass distance_from_electric_line_m=None and we assume no nearby lines.

    HARD_FAIL: user-provided distance < required clearance.
    SOFT_WARN: user said "unknown" AND lines might be present (we can't tell).
    PASS: user-provided distance ≥ required, OR user said "no nearby lines".
    """
    if distance_from_electric_line_m is None:
        # User did not specify — Session E will have proper "unknown" handling.
        # For Session B, assume no overhead lines present (PASS with caveat).
        return _build_result(
            check_id="electric_line_clearance",
            check_name="Electric line clearance",
            category=CheckCategory.SAFETY,
            severity=CheckSeverity.PASS,
            confidence=ConfidenceLevel.LOW,
            confidence_reason=(
                "User did not specify distance from electric lines. "
                "Assumed no overhead HT/LT lines within 5m of plot."
            ),
            assumption_used="No overhead electric lines within 5m of plot",
            verification_recommendation=(
                "Walk plot perimeter, look up for visible HT/LT lines. "
                "If lines present, contact local DISCOM (TANGEDCO/BESCOM/"
                "TSSPDCL/MSEDCL/MSPGCL/BSES) for line-type and required "
                "clearance. NBC mandates 1.2m for LT, 3.7m+ for HT."
            ),
            verification_priority=VerificationPriority.IMPORTANT,
            message=(
                "No electric line distance provided — assumed no overhead "
                "lines within 5m. Verify by visual inspection of plot."
            ),
            details={"line_type": line_type, "user_provided": False},
        )

    required_clearance = (
        NBC_MIN_DISTANCE_ELECTRIC_LINE_HT_M if line_type == "ht"
        else NBC_MIN_DISTANCE_ELECTRIC_LINE_LT_M
    )

    details = {
        "distance_from_electric_line_m": distance_from_electric_line_m,
        "line_type": line_type,
        "required_clearance_m": required_clearance,
        "user_provided": True,
    }

    if distance_from_electric_line_m < required_clearance:
        return _build_result(
            check_id="electric_line_clearance",
            check_name="Electric line clearance",
            category=CheckCategory.SAFETY,
            severity=CheckSeverity.HARD_FAIL,
            confidence=ConfidenceLevel.HIGH,
            verification_priority=VerificationPriority.CRITICAL,
            message=(
                f"Building is {distance_from_electric_line_m}m from "
                f"{line_type.upper()} electric line, below NBC minimum "
                f"{required_clearance}m clearance. "
                f"This is a safety + legal violation. Either relocate the "
                f"building footprint, request DISCOM to relocate the line, "
                f"or convert to underground cable."
            ),
            details=details,
            common_doubts=(
                "Q: Can I just install protective sheathing on the wall "
                "instead of moving the building? "
                "A: No — NBC clearance is non-negotiable for human safety "
                "and electrical induction concerns. Cable relocation is "
                "the standard solution.",
            ),
        )
    return _build_result(
        check_id="electric_line_clearance",
        check_name="Electric line clearance",
        category=CheckCategory.SAFETY,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.HIGH,
        message=(
            f"Distance {distance_from_electric_line_m}m from "
            f"{line_type.upper()} line meets NBC minimum {required_clearance}m."
        ),
        details=details,
    )


# ─── Check #15: Water course clearance ────────────────────────────────

def check_water_course_clearance(
    brief: Brief,
    distance_from_water_course_m: float | None = None,
    has_water_course_within_30m: bool | None = None,
) -> CheckResult:
    """Check NBC Part 3 Clause 6.5 water course clearance.

    'Water course' = natural drain, stream, storm channel, riverbank.
    NBC mandates 9m minimum setback. Local rules (NGT orders, river-
    specific buffers) can be stricter.

    HARD_FAIL: user-confirmed water course < 9m from plot edge.
    SOFT_WARN: user said "unknown" and city has known water course risk
        (e.g. Chennai monsoon flooding zones).
    PASS: user said "no water course nearby" OR distance ≥ 9m.
    """
    # Branch 1: user provided exact distance
    if distance_from_water_course_m is not None:
        details = {
            "distance_from_water_course_m": distance_from_water_course_m,
            "nbc_min_clearance_m": NBC_MIN_DISTANCE_WATER_COURSE_M,
            "user_provided": True,
        }
        if distance_from_water_course_m < NBC_MIN_DISTANCE_WATER_COURSE_M:
            return _build_result(
                check_id="water_course_clearance",
                check_name="Water course clearance",
                category=CheckCategory.COMPLIANCE,
                severity=CheckSeverity.HARD_FAIL,
                confidence=ConfidenceLevel.HIGH,
                verification_priority=VerificationPriority.CRITICAL,
                message=(
                    f"Distance {distance_from_water_course_m}m from "
                    f"water course is below NBC minimum "
                    f"{NBC_MIN_DISTANCE_WATER_COURSE_M}m. "
                    f"Local NGT orders for specific rivers may add "
                    f"further restrictions (some require 30m+)."
                ),
                details=details,
                common_doubts=(
                    "Q: It's just a stormwater drain — does that count? "
                    "A: Yes — NBC + city DCRs treat stormwater drains as "
                    "water courses. The risk is monsoon overflow + "
                    "structural damage from saturated soil.",
                ),
            )
        return _build_result(
            check_id="water_course_clearance",
            check_name="Water course clearance",
            category=CheckCategory.COMPLIANCE,
            severity=CheckSeverity.PASS,
            confidence=ConfidenceLevel.HIGH,
            message=(
                f"Distance {distance_from_water_course_m}m meets NBC "
                f"minimum {NBC_MIN_DISTANCE_WATER_COURSE_M}m clearance."
            ),
            details=details,
        )

    # Branch 2: user said "no water course nearby"
    if has_water_course_within_30m is False:
        return _build_result(
            check_id="water_course_clearance",
            check_name="Water course clearance",
            category=CheckCategory.COMPLIANCE,
            severity=CheckSeverity.PASS,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_reason=(
                "User confirmed no water course within 30m of plot, "
                "but distance not measured precisely."
            ),
            message=(
                "User confirmed no water course (drain/stream/river) "
                "within 30m of plot. Check passes."
            ),
            details={"user_provided": True,
                     "has_water_course_within_30m": False},
        )

    # Branch 3: user did not specify — Session E will properly handle this
    return _build_result(
        check_id="water_course_clearance",
        check_name="Water course clearance",
        category=CheckCategory.COMPLIANCE,
        severity=CheckSeverity.PASS,
        confidence=ConfidenceLevel.LOW,
        confidence_reason=(
            "User did not specify presence of water course near plot. "
            "Assumed no water course within 30m."
        ),
        assumption_used="No water course (drain/stream/river) within 30m",
        verification_recommendation=(
            "Walk plot perimeter and check for visible drains, streams, "
            "or river channels. Reference Survey of India topographic "
            "map for your district. If a water course exists, NBC "
            "requires 9m minimum setback (more if NGT orders apply)."
        ),
        verification_priority=VerificationPriority.IMPORTANT,
        message=(
            "Water course presence not specified — assumed no nearby "
            "drain/stream. Verify by walking plot perimeter."
        ),
        details={"user_provided": False},
    )


# ─── Check #17: Stilt mandate compliance ──────────────────────────────

def check_stilt_mandate_compliance(brief: Brief) -> CheckResult:
    """Check whether city mandates stilt parking for this plot tier.

    Currently only Delhi has a clear plot-tier stilt mandate (100-1000 sqm).
    Other cities mandate based on parking norms, which depend on number
    of dwelling units — out of v0.1 scope.

    HARD_FAIL: city mandates stilt for this plot tier AND brief has no stilt.
    PASS: stilt mandated AND brief has stilt; OR stilt not mandated.
    """
    from buildemup.domain.floor_requirement import FloorUse
    city = brief.plot.city.lower()
    plot_area = brief.plot.area_sqm
    has_stilt = any(f.floor_use == FloorUse.STILT_PARKING for f in brief.floors)

    if city not in STILT_MANDATE_BY_CITY:
        return _build_result(
            check_id="stilt_mandate_compliance",
            check_name="Stilt mandate compliance",
            severity=CheckSeverity.NOT_APPLICABLE,
            message=(
                f"{city.title()} does not have a clear plot-tier stilt "
                f"mandate in v0.1 KB. Stilt requirement may still apply "
                f"based on parking norms — verify with local building "
                f"plan office."
            ),
            details={"city": city, "kb_has_stilt_mandate": False},
        )

    mandate = STILT_MANDATE_BY_CITY[city]
    in_mandate_range = (
        mandate["min_plot_sqm"] <= plot_area <= mandate["max_plot_sqm"]
    )

    details = {
        "city": city,
        "plot_area_sqm": plot_area,
        "mandate_min_sqm": mandate["min_plot_sqm"],
        "mandate_max_sqm": mandate["max_plot_sqm"],
        "in_mandate_range": in_mandate_range,
        "has_stilt": has_stilt,
        "mandate_source": mandate["source"],
    }

    if in_mandate_range and not has_stilt:
        return _build_result(
            check_id="stilt_mandate_compliance",
            check_name="Stilt mandate compliance",
            severity=CheckSeverity.HARD_FAIL,
            verification_priority=VerificationPriority.CRITICAL,
            message=(
                f"{city.title()} mandates stilt parking for plots between "
                f"{mandate['min_plot_sqm']}-{mandate['max_plot_sqm']} sqm. "
                f"Your plot is {plot_area:.0f} sqm but brief has no stilt "
                f"floor. Either add stilt parking OR reduce plot tier "
                f"(below {mandate['min_plot_sqm']} sqm). "
                f"Source: {mandate['source']}."
            ),
            details=details,
            common_doubts=(
                "Q: Is the stilt requirement in the UBBL itself? "
                "A: For Delhi, no — it's a separate notification, easy "
                "to miss. This is a known gotcha in Delhi plan submissions.",
                "Q: Can I have surface parking instead? "
                "A: Surface parking in setback area is allowed but doesn't "
                "satisfy the stilt mandate where it applies.",
            ),
        )
    if in_mandate_range and has_stilt:
        return _build_result(
            check_id="stilt_mandate_compliance",
            check_name="Stilt mandate compliance",
            severity=CheckSeverity.PASS,
            message=(
                f"{city.title()} mandates stilt for {plot_area:.0f} sqm "
                f"plots; brief includes stilt floor. Compliant."
            ),
            details=details,
        )
    return _build_result(
        check_id="stilt_mandate_compliance",
        check_name="Stilt mandate compliance",
        severity=CheckSeverity.NOT_APPLICABLE,
        message=(
            f"Plot {plot_area:.0f} sqm is outside {city.title()}'s stilt "
            f"mandate range ({mandate['min_plot_sqm']}-"
            f"{mandate['max_plot_sqm']} sqm). Stilt is optional."
        ),
        details=details,
    )
