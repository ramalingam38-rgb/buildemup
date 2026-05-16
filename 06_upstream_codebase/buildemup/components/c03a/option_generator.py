"""
BuildemUp† — Component 3a Option Generation logic (Session 3).

Per SPEC v0.2.1a Section 2.2 — generates the real ResolutionOption set
for each detected ExtremeCase. Replaces the placeholder pair S2's
detector produces.

Per-EC dispatch (option counts incl. Preview Mode last):
  EC-001 → 6 options
  EC-002 → 4 options
  EC-003 → 4 options
  EC-004 → 4 options (no proceed-anyway — legal)
  EC-005 → 4 options (no proceed-anyway — legal)
  EC-006 → 5 options (no proceed-anyway — legal)
  EC-007 → 3 options (no proceed-anyway — legal)
  EC-008 → 6 options
  EC-009 → 4 options
  EC-010 → 4 options for HIGH/MEDIUM, 3 options for LOW (no proceed-anyway)

S6 orchestrator (later session) wires detector → generator → applier.
This module trusts the input ExtremeCase per Q10 (does NOT re-detect).

†= placeholder name marker.
"""
from __future__ import annotations

import math
from typing import Optional

from buildemup.domain.brief import Brief
from buildemup.domain.feasibility import (
    DesignGapAnalysis, CheckResult,
)
from buildemup.domain.floor_requirement import (
    NBC_MINIMUM_ROOM_SIZES_SQM, RoomType,
)
from buildemup.domain.extreme_case import (
    ExtremeCase, ExtremeCaseId, ResolutionOption,
    ResolutionProbability, BriefChange,
    CostImpact, CostConfidence,
)


# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

SQM_TO_SQFT = 10.7639
M_TO_FT = 3.28084

# Cut priority per D-006 (locked Era 1). Lowest priority first → cut first.
# STAIRCASE and BATHROOM_* are intentionally excluded (never cut).
ROOM_CUT_PRIORITY = (
    RoomType.BALCONY,
    RoomType.STORE,
    RoomType.UTILITY,
    RoomType.POOJA,
    RoomType.DINING,
    RoomType.LIVING,
    RoomType.KITCHEN,
    RoomType.BEDROOM_REGULAR,
    RoomType.BEDROOM_MASTER,
)

# Metro split for EC-003 parking recommendation logic
METRO_CITIES = frozenset({"mumbai", "delhi", "bangalore"})

# EC-001 recommendation thresholds (sqft)
EC_001_DROP_ROOM_THRESHOLD = 200    # < this → option A RECOMMENDED
EC_001_REDUCE_COUNT_THRESHOLD = 500  # 200..500 → option B RECOMMENDED

# EC-004 recommendation threshold
EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT = 100  # < this → option B RECOMMENDED

# EC-005 default permitted coverage (used as fallback)
EC_005_DEFAULT_PERMITTED_COVERAGE_PCT = 60.0

# EC-008 recommendation thresholds (gap %)
EC_008_PHASE_GAP_LOW = 50
EC_008_PHASE_GAP_HIGH = 65

# EC-009 default pile cost if soil CheckResult details missing it (₹5L)
EC_009_DEFAULT_PILE_COST_INR = 500_000

# Domain minima used by precondition guards. A residential brief must
# retain at least one bedroom and at least one floor; BriefChanges that
# would drop below these are not emitted as actionable.
MIN_BEDROOMS = 1
MIN_FLOORS = 1


# ──────────────────────────────────────────────────────────────────────
# Helpers — shared across EC builders
# ──────────────────────────────────────────────────────────────────────

def _bhk_count_from_brief(brief: Brief) -> int:
    """Total bedrooms (master + regular) across all floors. Mirrors
    detector logic.
    """
    count = 0
    for floor in brief.floors:
        for room_req in floor.rooms:
            if room_req.room_type in (RoomType.BEDROOM_MASTER,
                                      RoomType.BEDROOM_REGULAR):
                count += room_req.count
    return count


def _pick_lowest_priority_room(brief: Brief) -> Optional[RoomType]:
    """Find the lowest-priority room type currently present in the brief.

    Returns the cut-first candidate per ROOM_CUT_PRIORITY, or None if
    the brief contains no cuttable room types (very edge case — would
    only happen for a brief with only bathrooms/staircases).
    """
    present = {r.room_type for f in brief.floors for r in f.rooms}
    for room_type in ROOM_CUT_PRIORITY:
        if room_type in present:
            return room_type
    return None


def _far_has_headroom(gap_analysis: DesignGapAnalysis) -> bool:
    """True if FAR check is in passed_checks (headroom exists for adding
    a floor). False if FAR is missing, in blocking_issues, or in soft.
    """
    for cr in gap_analysis.practical_report.passed_checks:
        if cr.check_id == "far_compliance":
            return True
    return False


def _compute_shortfall_sqft(
    brief: Brief, gap_analysis: DesignGapAnalysis
) -> float:
    """Mirror of detector's EC-001 shortfall computation. Re-imports
    detector's package-internal helpers; legitimate intra-package use.
    """
    from buildemup.components.c03a.detector import (
        _compute_min_buildable_per_floor_sqm,
        _compute_envelope_area_sqm,
    )
    if not brief.floors:
        return 0.0
    min_buildable_per_floor = _compute_min_buildable_per_floor_sqm(brief)
    envelope_per_floor = _compute_envelope_area_sqm(
        brief, use_nbc_setbacks=True
    )
    floors = len(brief.floors)
    return (min_buildable_per_floor - envelope_per_floor) * floors * SQM_TO_SQFT


def _budget_gap_pct(
    brief: Brief, gap_analysis: DesignGapAnalysis
) -> Optional[float]:
    """Compute (estimate - budget) / budget * 100 for EC-008 logic.
    Returns None if cost_estimate or budget unavailable.
    """
    cost_estimate = gap_analysis.practical_report.cost_estimate
    if cost_estimate is None:
        return None
    estimate_inr = getattr(cost_estimate, "exact_value", None)
    if estimate_inr is None:
        return None
    budget_inr = brief.budget_range.max_rupees
    if budget_inr <= 0:
        return None
    return (estimate_inr - budget_inr) / budget_inr * 100


def _room_size_sqft(room_type: RoomType) -> float:
    """NBC-minimum size for a room type, expressed in sqft."""
    return NBC_MINIMUM_ROOM_SIZES_SQM[room_type] * SQM_TO_SQFT


def _typical_floor_area_sqft(brief: Brief) -> float:
    """Approximate per-floor envelope area in sqft. Used for the
    'add a floor' option's space_impact estimate.
    """
    from buildemup.components.c03a.detector import _compute_envelope_area_sqm
    if not brief.floors:
        return 0.0
    env_per_floor = _compute_envelope_area_sqm(brief, use_nbc_setbacks=True)
    return env_per_floor * SQM_TO_SQFT


def _topmost_floor_index(brief: Brief) -> int:
    """Highest floor_number in the brief. Used for EC-004 option A
    (drop a floor) — drops the topmost floor.
    """
    if not brief.floors:
        return 0
    return max(f.floor_number for f in brief.floors)


def _find_check(
    gap_analysis: DesignGapAnalysis, check_id: str
) -> Optional[CheckResult]:
    """Find a CheckResult by check_id across blocking + soft + passed.
    Returns None if not found.
    """
    pr = gap_analysis.practical_report
    for cr in pr.blocking_issues + pr.soft_warnings + pr.passed_checks:
        if cr.check_id == check_id:
            return cr
    return None


def _ec004_excess_sqft(
    brief: Brief, gap_analysis: DesignGapAnalysis
) -> float:
    """Compute FAR excess in sqft for EC-004 option B recommendation logic.
    Reads from far_compliance CheckResult details if present; falls back
    to a value above the threshold (so option B is NOT recommended) if
    we can't determine.
    """
    cr = _find_check(gap_analysis, "far_compliance")
    if cr is None:
        return float(EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT + 1)
    excess = cr.details.get("excess_sqft")
    if excess is None:
        return float(EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT + 1)
    try:
        return float(excess)
    except (TypeError, ValueError):
        return float(EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT + 1)


def _ec005_permitted_coverage_pct(
    gap_analysis: DesignGapAnalysis,
) -> float:
    """Read permitted coverage % from ground_coverage_compliance CheckResult
    details if present. Falls back to a sensible default (60%, typical
    Chennai DCR) — flagged as v0.2-backlog when default is used.
    """
    cr = _find_check(gap_analysis, "ground_coverage_compliance")
    if cr is None:
        return EC_005_DEFAULT_PERMITTED_COVERAGE_PCT
    permitted = cr.details.get("permitted_coverage_pct")
    if permitted is None:
        return EC_005_DEFAULT_PERMITTED_COVERAGE_PCT
    try:
        return float(permitted)
    except (TypeError, ValueError):
        return EC_005_DEFAULT_PERMITTED_COVERAGE_PCT


def _ec009_pile_cost_inr(gap_analysis: DesignGapAnalysis) -> int:
    """Read pile_cost_inr from soil CheckResult details if present;
    fall back to ₹5L default. Mirrors detector's EC-009 default.
    """
    pr = gap_analysis.practical_report
    for cr in pr.blocking_issues + pr.soft_warnings:
        if cr.check_id in ("soil_type", "soil_type_practical"):
            cost = cr.details.get("pile_cost_inr")
            if cost is not None:
                try:
                    return int(cost)
                except (TypeError, ValueError):
                    pass
            return EC_009_DEFAULT_PILE_COST_INR
    return EC_009_DEFAULT_PILE_COST_INR


def _can_reduce_bedrooms(brief: Brief) -> bool:
    """True iff dropping one bedroom keeps the brief at >= MIN_BEDROOMS.

    Used to guard EC-001 op B, EC-002 op A, and EC-008 op B (the
    bedroom-decrement portion of the chain) against producing a
    BriefChange that would trigger BEDROOM_COUNT_BELOW_MIN downstream.
    """
    return _bhk_count_from_brief(brief) > MIN_BEDROOMS


def _can_reduce_floors(brief: Brief) -> bool:
    """True iff dropping one floor keeps the brief at >= MIN_FLOORS.

    Used to guard EC-007 op B against producing a BriefChange that
    would trigger FLOOR_COUNT_BELOW_MIN downstream.
    """
    return len(brief.floors) > MIN_FLOORS


def _make_preview_option(case_id: ExtremeCaseId) -> ResolutionOption:
    """Build the Preview Mode option for any EC. Always last in tuple.

    Two invariants enforced by S1's __post_init__ and ExtremeCase post_init:
      - is_preview_mode=True ⇒ requires_brief_change=()
      - Preview Mode option must be at index len(options)-1
    """
    return ResolutionOption(
        option_id=f"{case_id.value}_OPT_PREVIEW_MODE",
        description=(
            "See what your full brief looks like as a layout — "
            "watermarked, not buildable"
        ),
        impact_summary=(
            "Reduced output: 1 layout, dimension ranges only, "
            "watermarks inside rooms, no construction details. "
            "Cannot be used by a contractor."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "This is a non-buildable preview only. Sharing this with a "
            "contractor as a buildable plan is not appropriate."
        ),
        is_preview_mode=True,
    )


def _build_different_plot_option(
    *,
    option_id: str,
    description: str,
    impact_summary: str,
    cost_impact: Optional[CostImpact] = None,
    recommended: bool = False,
    recommendation_reason: Optional[str] = None,
    risk_advisory: Optional[str] = None,
) -> ResolutionOption:
    """Centralized constructor for "look for a different plot" options.

    ALL different-plot options across S3 MUST be constructed via this
    helper (B-027 P2). Direct construction with is_different_plot_option=True
    is also structurally guarded by ResolutionOption.__post_init__ (B-027 P1
    + P6), but using this helper is the disciplined path.

    HARD-CODED FIELDS + RATIONALE (B-027 P8):

    space_impact_sqft=0 — represents NOT-APPLICABLE for plot-switch
        decisions, NOT "zero impact." Different-plot doesn't shrink or
        expand the brief; it abandons the entire current brief in favor
        of finding a different plot. The numeric zero is a placeholder;
        downstream consumers (S5 counterfactual ranking) should
        understand that distance-based ranking is semantically
        meaningless for these options because they're recommended for
        structural plot-fit reasons, not spatial trade-offs. S6's
        promotion logic doesn't use space_impact for these options.

    requires_brief_change=() — different-plot does NOT modify the current
        brief. The user navigates back to plot search; no BriefChange is
        applied. (Also enforced by S1 __post_init__ P6.)

    requires_action=None — there is no in-app action to trigger (no
        email, no scheduled task). The user simply navigates elsewhere.
        (Also enforced by S1 __post_init__ P6.)

    is_preview_mode=False — different-plot is not Preview Mode (mutually
        exclusive — enforced by S1 __post_init__ P1).

    is_different_plot_option=True — the entire purpose of this helper.

    Args:
        option_id: stable identifier (caller-supplied)
        description: user-facing label
        impact_summary: counterfactual phrasing material
        cost_impact: optional cost estimate (usually None for different-
            plot — no cost to walking away)
        recommended: whether THIS specific case wants the option
            recommended at emission time. NOTE: S6's runtime promotion
            logic mutates this to True when promotion conditions fire,
            so most callers should leave this False; set True only when
            the case unconditionally recommends different-plot.
        recommendation_reason: required iff recommended=True
        risk_advisory: optional cautionary note
    """
    return ResolutionOption(
        option_id=option_id,
        description=description,
        impact_summary=impact_summary,
        cost_impact=cost_impact,
        space_impact_sqft=0,
        recommended=recommended,
        recommendation_reason=recommendation_reason,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=risk_advisory,
        is_preview_mode=False,
        is_different_plot_option=True,
    )


# ──────────────────────────────────────────────────────────────────────
# EC-001 — TOTAL_AREA_EXCEEDS_ENVELOPE (SPATIAL)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_001(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """6 options. EC-001 is non-legal so proceed-anyway is allowed."""
    shortfall_sqft = _compute_shortfall_sqft(brief, gap_analysis)
    far_headroom = _far_has_headroom(gap_analysis)
    lowest_priority_room = _pick_lowest_priority_room(brief)

    options: list[ResolutionOption] = []

    # Option A — Drop the lowest-priority room
    if lowest_priority_room is not None:
        opt_a_recommended = shortfall_sqft < EC_001_DROP_ROOM_THRESHOLD
        room_label = lowest_priority_room.value.replace("_", " ")
        room_size = _room_size_sqft(lowest_priority_room)
        options.append(ResolutionOption(
            option_id="EC_001_OPT_A_DROP_LOWEST_PRIORITY_ROOM",
            description=f"Drop the {room_label}",
            impact_summary=(
                f"Removes ~{room_size:.0f} sqft from the brief. Affects "
                f"only the lowest-priority room — bedrooms and kitchen "
                f"are preserved."
            ),
            cost_impact=None,
            space_impact_sqft=-int(round(room_size)),
            recommended=opt_a_recommended,
            recommendation_reason=(
                f"Best fit when shortfall < {EC_001_DROP_ROOM_THRESHOLD} "
                f"sqft (yours is ~{shortfall_sqft:.0f})"
                if opt_a_recommended else None
            ),
            requires_brief_change=(
                BriefChange(
                    field_path=f"rooms.{lowest_priority_room.value}.count",
                    operation="INCREMENT",
                    new_value=-1,
                    description=f"Remove one {room_label}",
                ),
            ),
            requires_action=None,
            risk_advisory=None,
            is_preview_mode=False,
        ))

    # Option B — Reduce room count by 1 (drop a bedroom equivalent)
    can_drop_bedroom = _can_reduce_bedrooms(brief)
    opt_b_recommended = (
        can_drop_bedroom
        and EC_001_DROP_ROOM_THRESHOLD <= shortfall_sqft
        <= EC_001_REDUCE_COUNT_THRESHOLD
    )
    options.append(ResolutionOption(
        option_id="EC_001_OPT_B_REDUCE_ROOM_COUNT",
        description="Reduce room count by 1 (drop a bedroom)",
        impact_summary=(
            "Removes ~120 sqft from the brief. Visible reduction in BHK; "
            "bigger trade-off than dropping ancillary rooms."
        ),
        cost_impact=None,
        space_impact_sqft=-120 if can_drop_bedroom else 0,
        recommended=opt_b_recommended,
        recommendation_reason=(
            f"Best fit when shortfall is "
            f"{EC_001_DROP_ROOM_THRESHOLD}-{EC_001_REDUCE_COUNT_THRESHOLD} "
            f"sqft (yours is ~{shortfall_sqft:.0f})"
            if opt_b_recommended else None
        ),
        requires_brief_change=(
            (BriefChange(
                field_path=f"rooms.{RoomType.BEDROOM_REGULAR.value}.count",
                operation="INCREMENT",
                new_value=-1,
                description="Remove one regular bedroom",
            ),) if can_drop_bedroom else ()
        ),
        requires_action=None,
        risk_advisory=(
            None if can_drop_bedroom
            else (
                f"Brief is already at {MIN_BEDROOMS}BHK; this option is "
                f"informational only — there's nothing to drop."
            )
        ),
        is_preview_mode=False,
    ))

    # Option C — Add a floor (only sensible if FAR has headroom)
    floor_area_sqft = _typical_floor_area_sqft(brief)
    options.append(ResolutionOption(
        option_id="EC_001_OPT_C_ADD_FLOOR",
        description="Add another floor to fit the brief",
        impact_summary=(
            f"Adds ~{floor_area_sqft:.0f} sqft of buildable area. "
            f"Adds ~₹15-25 L to construction cost."
        ),
        cost_impact=CostImpact.build(
            low=1_500_000, mid=2_000_000, high=2_500_000,
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Per-floor incremental cost from C7 cost engine averages "
                "for Indian residential construction."
            ),
        ),
        space_impact_sqft=int(round(floor_area_sqft)),
        recommended=far_headroom,
        recommendation_reason=(
            "FAR has headroom; adding a floor is structurally and legally "
            "clean."
            if far_headroom else None
        ),
        requires_brief_change=(
            BriefChange(
                field_path="floors.add",
                operation="INCREMENT",
                new_value=1,
                description="Add one residential floor",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            None if far_headroom
            else "FAR check is currently failing; adding a floor may not "
                 "be approvable without a variance."
        ),
        is_preview_mode=False,
    ))

    # Option D — Accept smaller room sizes (NBC minimums)
    options.append(ResolutionOption(
        option_id="EC_001_OPT_D_ACCEPT_NBC_MINIMUMS",
        description="Accept smaller room sizes (NBC minimums)",
        impact_summary=(
            "Each room shrinks to NBC minimum. Saves ~80-150 sqft total "
            "but rooms feel cramped (no king bed, narrow wardrobes)."
        ),
        cost_impact=None,
        space_impact_sqft=-100,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="rooms.all.size",
                operation="SET",
                new_value="nbc_min",
                description="Reduce all room sizes to NBC minimums",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            "Resulting rooms may feel cramped; furniture choices "
            "constrained."
        ),
        is_preview_mode=False,
    ))

    # Option E — Proceed anyway (logged risk acceptance; EC-001 non-legal)
    options.append(ResolutionOption(
        option_id="EC_001_OPT_E_PROCEED_ANYWAY",
        description="Proceed with current brief, accepting tight fit",
        impact_summary=(
            "Layout will be generated with current brief. Some rooms may "
            "be NBC-minimum or rendered as compact variants."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Layout output will reflect the trade-offs; quality may be "
            "lower than briefs that fit comfortably."
        ),
        is_preview_mode=False,
    ))

    # Option F — Preview Mode (always last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-002 — PLOT_WIDTH_INSUFFICIENT (SITE)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_002(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """4 options. 'Different plot' co-fire-promoted with EC-006.

    Heuristic: option A (Reduce BHK) is RECOMMENDED only when bhk >= 3
    (per Q8 / B-007 — Brief lacks an explicit bhk_flexibility signal).
    """
    bhk = _bhk_count_from_brief(brief)
    co_fire_with_006 = (
        ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE
        in co_fired_case_ids
    )

    options: list[ResolutionOption] = []

    # Option A — Reduce BHK count
    can_drop_bedroom = _can_reduce_bedrooms(brief)
    opt_a_recommended = can_drop_bedroom and bhk >= 3
    target_bhk = max(MIN_BEDROOMS, bhk - 1)
    if can_drop_bedroom:
        opt_a_description = f"Reduce BHK count from {bhk}BHK to {target_bhk}BHK"
        opt_a_impact = (
            "Drops one bedroom from the brief. Layout becomes "
            "comfortable instead of compromised."
        )
        opt_a_advisory: Optional[str] = None
    else:
        opt_a_description = (
            f"Reduce BHK count (informational — already at {MIN_BEDROOMS}BHK)"
        )
        opt_a_impact = (
            f"Brief is already at {MIN_BEDROOMS}BHK; cannot reduce further. "
            f"Other options below remain available."
        )
        opt_a_advisory = (
            f"Brief is already at {MIN_BEDROOMS}BHK; this option is "
            f"informational only — there's nothing to drop."
        )
    options.append(ResolutionOption(
        option_id="EC_002_OPT_A_REDUCE_BHK",
        description=opt_a_description,
        impact_summary=opt_a_impact,
        cost_impact=None,
        space_impact_sqft=-120 if can_drop_bedroom else 0,
        recommended=opt_a_recommended,
        recommendation_reason=(
            "Reducing from 3+BHK is a meaningful trade-off when plot "
            "width is severe."
            if opt_a_recommended else None
        ),
        requires_brief_change=(
            (BriefChange(
                field_path=f"rooms.{RoomType.BEDROOM_REGULAR.value}.count",
                operation="INCREMENT",
                new_value=-1,
                description="Remove one regular bedroom",
            ),) if can_drop_bedroom else ()
        ),
        requires_action=None,
        risk_advisory=opt_a_advisory,
        is_preview_mode=False,
    ))

    # Option B — Accept layout compromises (effective proceed-anyway)
    options.append(ResolutionOption(
        option_id="EC_002_OPT_B_ACCEPT_COMPROMISES",
        description="Accept the layout compromises and proceed",
        impact_summary=(
            "Bedrooms will be narrow; furniture choices constrained "
            "(no king beds, shallower wardrobes, single-loaded corridor "
            "only)."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Resulting layout will feel tight; furniture sizing "
            "constrained."
        ),
        is_preview_mode=False,
    ))

    # Option C — Look for a different plot (RECOMMENDED if EC-006 co-fires)
    options.append(_build_different_plot_option(
        option_id="EC_002_OPT_C_DIFFERENT_PLOT",
        description="Look for a different plot",
        impact_summary=(
            "Pause this brief and search for a wider plot that allows "
            "comfortable BHK layouts."
        ),
        recommended=co_fire_with_006,
        recommendation_reason=(
            "When EC-006 also fires (envelope below buildable), plot "
            "search becomes the realistic path."
            if co_fire_with_006 else None
        ),
    ))

    # Option D — Preview Mode (always last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-003 — NO_PARKING_POSITION (SITE)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_003(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """4 options. Recommendation flips on metro vs tier-2/3."""
    is_metro = brief.plot.city.lower() in METRO_CITIES

    options: list[ResolutionOption] = []

    # Option A — Drop covered parking; accept open street parking
    options.append(ResolutionOption(
        option_id="EC_003_OPT_A_DROP_COVERED_PARKING",
        description="Drop covered parking; accept open street parking",
        impact_summary=(
            "Frees up plot footprint; no covered car bay. "
            "Owner parks on street."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=not is_metro,
        recommendation_reason=(
            "Open street parking is normal in tier-2/3 cities; covered "
            "parking is not strictly necessary."
            if not is_metro else None
        ),
        requires_brief_change=(
            BriefChange(
                field_path="parking.has_covered",
                operation="SET",
                new_value=False,
                description="Remove covered parking from brief",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            "In metros, open parking creates security and weather "
            "concerns."
            if is_metro else None
        ),
        is_preview_mode=False,
    ))

    # Option B — Convert ground floor to stilt parking
    options.append(ResolutionOption(
        option_id="EC_003_OPT_B_STILT_PARKING",
        description="Convert ground floor to stilt parking",
        impact_summary=(
            "Adds one effective floor of usable space above; ~₹2.5L extra "
            "construction cost. Removes the ground-floor footprint "
            "constraint for parking."
        ),
        cost_impact=CostImpact.build(
            low=200_000, mid=250_000, high=400_000,
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Stilt parking incremental cost — Indian residential "
                "averages."
            ),
        ),
        space_impact_sqft=0,
        recommended=is_metro,
        recommendation_reason=(
            "Standard pattern in metros; secures parking and adds usable "
            "floor area above."
            if is_metro else None
        ),
        requires_brief_change=(
            BriefChange(
                field_path="floors.add_stilt",
                operation="SET",
                new_value=True,
                description="Add stilt parking as ground floor",
            ),
        ),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option C — Look for a different plot (last resort, never recommended)
    options.append(_build_different_plot_option(
        option_id="EC_003_OPT_C_DIFFERENT_PLOT",
        description="Look for a different plot with parking access",
        impact_summary=(
            "Pause this brief and search for a plot with workable parking "
            "geometry."
        ),
    ))

    # Option D — Preview Mode (always last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-004 — FAR_EXCEEDED (LEGAL — no proceed-anyway)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_004(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """4 options — no proceed-anyway because FAR is regulatory.

    Option A (drop floor): RECOMMENDED if floors > 1 (otherwise can't
    drop without making it 0-floor).
    Option B (reduce per-floor area): RECOMMENDED if excess < 100 sqft.
    """
    floors_count = len(brief.floors)
    excess_sqft = _ec004_excess_sqft(brief, gap_analysis)
    topmost = _topmost_floor_index(brief)

    options: list[ResolutionOption] = []

    # Option A — Drop a floor (G+2 → G+1)
    opt_a_recommended = floors_count > 1
    options.append(ResolutionOption(
        option_id="EC_004_OPT_A_DROP_FLOOR",
        description="Drop a floor to fit FAR",
        impact_summary=(
            f"Removes the topmost floor (~{_typical_floor_area_sqft(brief):.0f} "
            f"sqft of buildable area). Brings FAR within permitted "
            f"limits cleanly."
        ),
        cost_impact=None,
        space_impact_sqft=-int(round(_typical_floor_area_sqft(brief))),
        recommended=opt_a_recommended,
        recommendation_reason=(
            "Cleanest path to FAR compliance when more than one floor "
            "is planned."
            if opt_a_recommended else None
        ),
        requires_brief_change=(
            BriefChange(
                field_path=f"floors.{topmost}",
                operation="DELETE",
                new_value=None,
                description=f"Remove floor {topmost} from brief",
            ),
        ) if opt_a_recommended else (),
        requires_action=None,
        risk_advisory=(
            None if opt_a_recommended
            else "Brief has only one floor; this option is informational "
                 "only — there's nothing to drop."
        ),
        is_preview_mode=False,
    ))

    # Option B — Reduce per-floor area (shrink rooms to NBC mins)
    opt_b_recommended = excess_sqft < EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT
    options.append(ResolutionOption(
        option_id="EC_004_OPT_B_REDUCE_PER_FLOOR_AREA",
        description="Reduce per-floor area (shrink rooms to NBC minimums)",
        impact_summary=(
            f"Each room shrinks to NBC minimum, recovering ~80-150 sqft "
            f"total. Suitable when the FAR excess is small "
            f"(yours is ~{excess_sqft:.0f} sqft)."
        ),
        cost_impact=None,
        space_impact_sqft=-100,
        recommended=opt_b_recommended,
        recommendation_reason=(
            f"Best fit when excess < "
            f"{EC_004_REDUCE_AREA_EXCESS_THRESHOLD_SQFT} sqft."
            if opt_b_recommended else None
        ),
        requires_brief_change=(
            BriefChange(
                field_path="rooms.all.size",
                operation="SET",
                new_value="nbc_min",
                description="Reduce all room sizes to NBC minimums",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            "Resulting rooms may feel cramped; furniture choices "
            "constrained."
        ),
        is_preview_mode=False,
    ))

    # Option C — Apply for FAR variance (advisory only)
    options.append(ResolutionOption(
        option_id="EC_004_OPT_C_FAR_VARIANCE_APPLICATION",
        description="Apply for FAR variance",
        impact_summary=(
            "3-6 month process; ₹50K-2L typical cost; ~30% success "
            "rate. Variance is discretionary — outcome depends on city "
            "planning authority."
        ),
        cost_impact=CostImpact.build(
            low=50_000, mid=125_000, high=200_000,
            confidence=CostConfidence.LOW,
            derivation=(
                "Variance application costs from city DCR research "
                "(filing + drafting + consultant fees)."
            ),
        ),
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Variance is discretionary; success not guaranteed. Plan "
            "for the possibility of refusal."
        ),
        is_preview_mode=False,
    ))

    # Option D — Preview Mode (always last; no proceed-anyway — legal)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-005 — GROUND_COVERAGE_EXCEEDED (LEGAL — no proceed-anyway)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_005(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """4 options — no proceed-anyway (legal).

    Option A (increase setbacks) is always RECOMMENDED — cheapest path.
    """
    permitted_pct = _ec005_permitted_coverage_pct(gap_analysis)

    options: list[ResolutionOption] = []

    # Option A — Increase setbacks (RECOMMENDED, lowest cost)
    options.append(ResolutionOption(
        option_id="EC_005_OPT_A_INCREASE_SETBACKS",
        description="Increase setbacks to reduce footprint",
        impact_summary=(
            "Increases front and rear setbacks by 0.3 m each, reducing "
            "the ground-floor footprint to within permitted coverage. "
            "Lowest-cost path to compliance."
        ),
        cost_impact=None,
        space_impact_sqft=-50,
        recommended=True,
        recommendation_reason=(
            "Lowest-cost path: no construction change needed beyond "
            "envelope adjustment."
        ),
        requires_brief_change=(
            BriefChange(
                field_path="setbacks.front_m",
                operation="INCREMENT",
                new_value=0.3,
                description="Increase front setback by 0.3 m",
            ),
            BriefChange(
                field_path="setbacks.rear_m",
                operation="INCREMENT",
                new_value=0.3,
                description="Increase rear setback by 0.3 m",
            ),
        ),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option B — Reduce ground-floor footprint
    options.append(ResolutionOption(
        option_id="EC_005_OPT_B_REDUCE_GROUND_FLOOR_FOOTPRINT",
        description="Reduce ground-floor footprint (e.g. partial-cover stilt)",
        impact_summary=(
            f"Shrinks ground-floor coverage to the permitted "
            f"{permitted_pct:.0f}%. Upper floors keep their footprint "
            f"(NBC allows upper floors to overhang the reduced ground)."
        ),
        cost_impact=None,
        space_impact_sqft=-80,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="coverage.reduce_footprint",
                operation="SET",
                new_value=permitted_pct,
                description=(
                    f"Reduce ground-floor coverage to "
                    f"{permitted_pct:.0f}%"
                ),
            ),
        ),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option C — Apply for variance (advisory only)
    options.append(ResolutionOption(
        option_id="EC_005_OPT_C_COVERAGE_VARIANCE_APPLICATION",
        description="Apply for ground-coverage variance",
        impact_summary=(
            "3-6 month process; ₹50K-2L typical cost; success rate is "
            "city-dependent. Coverage variances are harder to obtain "
            "than FAR variances."
        ),
        cost_impact=CostImpact.build(
            low=50_000, mid=125_000, high=200_000,
            confidence=CostConfidence.LOW,
            derivation=(
                "Variance application costs from city DCR research; "
                "coverage variances trend toward the upper range."
            ),
        ),
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Variance is discretionary; coverage variances are "
            "particularly hard to secure. Plan for the possibility "
            "of refusal."
        ),
        is_preview_mode=False,
    ))

    # Option D — Preview Mode (always last; no proceed-anyway — legal)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-006 — PRACTICAL_ENVELOPE_BELOW_BUILDABLE (LEGAL — no proceed-anyway)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_006(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """5 options — no proceed-anyway (legal).

    Option D (different plot) co-fire-promoted with EC-002.
    Option C (verify CBA) is the only place EMAIL_CBA_CHECKLIST appears.
    """
    co_fire_with_002 = (
        ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT in co_fired_case_ids
    )
    lowest_priority_room = _pick_lowest_priority_room(brief)

    options: list[ResolutionOption] = []

    # Option A — Reduce brief scope (RECOMMENDED)
    if lowest_priority_room is not None:
        room_label = lowest_priority_room.value.replace("_", " ")
        scope_brief_change: tuple[BriefChange, ...] = (
            BriefChange(
                field_path=f"rooms.{lowest_priority_room.value}.count",
                operation="INCREMENT",
                new_value=-1,
                description=f"Remove one {room_label} from brief",
            ),
        )
        scope_summary = (
            f"Drops the lowest-priority room ({room_label}) so the brief "
            f"fits within your stated setbacks."
        )
    else:
        scope_brief_change = ()
        scope_summary = (
            "Reduces overall scope so the brief fits within your stated "
            "setbacks."
        )

    options.append(ResolutionOption(
        option_id="EC_006_OPT_A_REDUCE_BRIEF_SCOPE",
        description="Reduce brief scope to fit your stated setbacks",
        impact_summary=scope_summary,
        cost_impact=None,
        space_impact_sqft=(
            -int(round(_room_size_sqft(lowest_priority_room)))
            if lowest_priority_room is not None else 0
        ),
        recommended=True,
        recommendation_reason=(
            "Fastest path: keeps your setback preferences intact while "
            "shrinking the brief to fit."
        ),
        requires_brief_change=scope_brief_change,
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option B — Reduce stated setbacks further (advisory)
    options.append(ResolutionOption(
        option_id="EC_006_OPT_B_REDUCE_SETBACKS_FURTHER",
        description="Reduce stated setbacks below NBC further",
        impact_summary=(
            "Tightens setbacks beyond what you originally stated. "
            "Recovers buildable envelope but creates approval and "
            "structural challenges."
        ),
        cost_impact=None,
        space_impact_sqft=40,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="setbacks.front_m",
                operation="INCREMENT",
                new_value=-0.3,
                description="Reduce front setback by 0.3 m further",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            "Setbacks below 1 ft create approval and structural "
            "challenges; expect plan-sanction friction."
        ),
        is_preview_mode=False,
    ))

    # Option C — Verify CBA (special action, no brief change)
    options.append(ResolutionOption(
        option_id="EC_006_OPT_C_VERIFY_CBA",
        description="Verify if your plot is in a Continuous Building Area",
        impact_summary=(
            "If your plot is in a CMDA-designated Continuous Building "
            "Area (CBA), zero side-setbacks are allowed — which may "
            "fully resolve this issue. We'll email a verification "
            "checklist to your registered email."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action="EMAIL_CBA_CHECKLIST",
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option D — Look for a different plot (RECOMMENDED if EC-002 co-fires)
    options.append(_build_different_plot_option(
        option_id="EC_006_OPT_D_DIFFERENT_PLOT",
        description="Look for a different plot",
        impact_summary=(
            "Pause this brief and search for a plot whose buildable "
            "envelope supports the brief without sub-NBC compromises."
        ),
        recommended=co_fire_with_002,
        recommendation_reason=(
            "When EC-002 also fires (plot width insufficient), the "
            "realistic path is a different plot."
            if co_fire_with_002 else None
        ),
    ))

    # Option E — Preview Mode (always last; no proceed-anyway — legal)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-007 — STILT_MANDATE_VIOLATED (LEGAL — no proceed-anyway)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_007(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """3 options — no proceed-anyway (legal).

    Option A (add stilt) is RECOMMENDED — keeps brief scope intact.
    """
    options: list[ResolutionOption] = []

    # Option A — Add stilt parking (RECOMMENDED)
    options.append(ResolutionOption(
        option_id="EC_007_OPT_A_ADD_STILT_PARKING",
        description="Add stilt parking to comply with the mandate",
        impact_summary=(
            "Adds an effective floor of stilt parking; brief scope is "
            "preserved. Adds ~₹2.5-4 L to construction cost."
        ),
        cost_impact=CostImpact.build(
            low=250_000, mid=325_000, high=400_000,
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Stilt parking incremental cost — Indian residential "
                "averages."
            ),
        ),
        space_impact_sqft=0,
        recommended=True,
        recommendation_reason=(
            "Preserves the full brief; cleanest path to mandate "
            "compliance."
        ),
        requires_brief_change=(
            BriefChange(
                field_path="floors.add_stilt",
                operation="SET",
                new_value=True,
                description="Add stilt parking as ground floor",
            ),
        ),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option B — Reduce floor count to drop below threshold
    can_drop_floor = _can_reduce_floors(brief)
    options.append(ResolutionOption(
        option_id="EC_007_OPT_B_REDUCE_FLOOR_COUNT",
        description="Reduce floor count to drop below the stilt threshold",
        impact_summary=(
            "Removes a floor so building height drops below the city's "
            "stilt-mandate threshold. Reduces overall buildable area."
        ),
        cost_impact=None,
        space_impact_sqft=(
            -int(round(_typical_floor_area_sqft(brief)))
            if can_drop_floor else 0
        ),
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            (BriefChange(
                field_path="floors.count",
                operation="INCREMENT",
                new_value=-1,
                description="Remove one floor from brief",
            ),) if can_drop_floor else ()
        ),
        requires_action=None,
        risk_advisory=(
            None if can_drop_floor
            else (
                f"Brief has only {MIN_FLOORS} floor; this option is "
                f"informational only — there's nothing to drop."
            )
        ),
        is_preview_mode=False,
    ))

    # Option C — Preview Mode (always last; no proceed-anyway — legal)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-008 — BUDGET_CATASTROPHICALLY_LOW (BUDGET — proceed-anyway allowed)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_008(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """6 options. BUDGET is non-legal so proceed-anyway is allowed.

    Option C (phase construction) RECOMMENDED if gap_pct ∈ [50, 65].
    """
    cost_estimate = gap_analysis.practical_report.cost_estimate
    estimate_inr = (
        getattr(cost_estimate, "exact_value", None)
        if cost_estimate is not None else None
    )
    range_min = (
        getattr(cost_estimate, "range_min", None)
        if cost_estimate is not None else None
    )
    range_max = (
        getattr(cost_estimate, "range_max", None)
        if cost_estimate is not None else None
    )
    gap_pct = _budget_gap_pct(brief, gap_analysis)

    # Compute target budget for option A (rounded up to next lakh)
    if estimate_inr is not None:
        target_lakhs = int(math.ceil(estimate_inr / 100_000))
    else:
        # Defensive fallback — shouldn't happen since EC-008 detection
        # requires cost_estimate present.
        target_lakhs = int(math.ceil(brief.budget_range.max_rupees * 1.6
                                     / 100_000))

    options: list[ResolutionOption] = []

    # Option A — Increase budget to cover the estimate
    if (estimate_inr is not None and range_min is not None
            and range_max is not None):
        budget_cost_impact = CostImpact.build(
            low=int(range_min), mid=int(estimate_inr), high=int(range_max),
            confidence=CostConfidence.HIGH,
            derivation=(
                "Cost estimate from Component 7 (C7) cost engine output, "
                "applied directly."
            ),
        )
    else:
        # Fallback when cost_estimate is incomplete
        synthetic = brief.budget_range.max_rupees * 1.6
        budget_cost_impact = CostImpact.build(
            low=int(synthetic * 0.85), mid=int(synthetic),
            high=int(synthetic * 1.15),
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Synthetic estimate from budget × industry-typical "
                "overrun factor (cost engine output unavailable)."
            ),
        )
    options.append(ResolutionOption(
        option_id="EC_008_OPT_A_INCREASE_BUDGET",
        description=f"Increase budget to ₹{target_lakhs} L to cover the estimate",
        impact_summary=(
            f"Raises max budget to ₹{target_lakhs} L. May require "
            f"phased financing or a top-up loan; loan eligibility "
            f"depends on income and LTV."
        ),
        cost_impact=budget_cost_impact,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="budget.max_lakhs",
                operation="SET",
                new_value=target_lakhs,
                description=f"Increase budget ceiling to ₹{target_lakhs} L",
            ),
        ),
        requires_action=None,
        risk_advisory=(
            "Loan eligibility is income-dependent; verify with your "
            "bank before committing."
        ),
        is_preview_mode=False,
    ))

    # Option B — Reduce scope dramatically (chain of BriefChanges)
    present_room_types = {r.room_type for f in brief.floors for r in f.rooms}
    scope_changes: list[BriefChange] = []
    can_drop_bedroom_for_scope = _can_reduce_bedrooms(brief)
    if (RoomType.BEDROOM_REGULAR in present_room_types
            and can_drop_bedroom_for_scope):
        scope_changes.append(BriefChange(
            field_path=f"rooms.{RoomType.BEDROOM_REGULAR.value}.count",
            operation="INCREMENT",
            new_value=-1,
            description="Remove one regular bedroom",
        ))
    if RoomType.BALCONY in present_room_types:
        scope_changes.append(BriefChange(
            field_path=f"rooms.{RoomType.BALCONY.value}.count",
            operation="INCREMENT",
            new_value=-1,
            description="Remove one balcony",
        ))
    if not scope_changes:
        # Fallback: no cuttable rooms (or already at MIN_BEDROOMS with no
        # balcony) — emit a generic NBC-min reduction so the option still
        # produces some change.
        scope_changes.append(BriefChange(
            field_path="rooms.all.size",
            operation="SET",
            new_value="nbc_min",
            description="Reduce all room sizes to NBC minimums",
        ))
    # Description / advisory adapt to whether bedroom decrement is in scope
    if can_drop_bedroom_for_scope:
        opt_b_description = "Reduce scope dramatically (drop bedroom + balcony)"
        opt_b_advisory: Optional[str] = None
    else:
        opt_b_description = (
            "Reduce scope dramatically (drop balcony, shrink rooms; "
            f"already at {MIN_BEDROOMS}BHK so no further bedroom cut)"
        )
        opt_b_advisory = (
            f"Brief is at {MIN_BEDROOMS}BHK; bedroom cut is unavailable. "
            f"Scope reduction will rely on balcony/room-size changes only."
        )
    options.append(ResolutionOption(
        option_id="EC_008_OPT_B_REDUCE_SCOPE_DRAMATICALLY",
        description=opt_b_description,
        impact_summary=(
            "Substantially shrinks the brief: drops one bedroom and one "
            "balcony where present, plus implies lower-tier finishes. "
            "Brings cost down meaningfully, but the home is materially "
            "smaller."
        ),
        cost_impact=None,
        space_impact_sqft=-200,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=tuple(scope_changes),
        requires_action=None,
        risk_advisory=opt_b_advisory,
        is_preview_mode=False,
    ))

    # Option C — Phase the construction (advisory, no brief change)
    opt_c_recommended = (
        gap_pct is not None
        and EC_008_PHASE_GAP_LOW <= gap_pct <= EC_008_PHASE_GAP_HIGH
    )
    options.append(ResolutionOption(
        option_id="EC_008_OPT_C_PHASE_CONSTRUCTION",
        description="Phase the construction (build core now, finish later)",
        impact_summary=(
            "Build the shell and core (structure, plumbing, kitchen, one "
            "bedroom) now within budget; finish remaining bedrooms and "
            "interior in phase 2 over 1-3 years. Brief unchanged; you "
            "manage the build in stages."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=opt_c_recommended,
        recommendation_reason=(
            f"Best fit when gap is {EC_008_PHASE_GAP_LOW}-"
            f"{EC_008_PHASE_GAP_HIGH}% (yours is ~{gap_pct:.0f}%); "
            f"phasing absorbs gaps in this range without scope cuts."
            if opt_c_recommended else None
        ),
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Phase 2 cost will be higher than today's quote due to "
            "inflation; budget a 6-10%/year escalation."
        ),
        is_preview_mode=False,
    ))

    # Option D — Pause the project (last resort, not framed as failure)
    options.append(ResolutionOption(
        option_id="EC_008_OPT_D_PAUSE_PROJECT",
        description="Pause the project to revisit later",
        impact_summary=(
            "Saves the brief as a draft. You can return when budget, "
            "scope, or financing changes. Not framed as failure — many "
            "homes wait the right moment."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action="PAUSE_FOR_USER_VERIFICATION",
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option E — Proceed anyway (BUDGET non-legal so allowed)
    options.append(ResolutionOption(
        option_id="EC_008_OPT_E_PROCEED_ANYWAY",
        description="Proceed with current brief, accepting the funding gap",
        impact_summary=(
            "Layout will be generated with the full brief. You take "
            "responsibility for bridging the gap (top-up loan, family "
            "contribution, or scope changes during construction)."
        ),
        cost_impact=None,
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Mid-construction scope cuts are expensive and stressful. "
            "Most contractors recommend resolving budget gaps before "
            "starting."
        ),
        is_preview_mode=False,
    ))

    # Option F — Preview Mode (always last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-009 — SOIL_REQUIRES_PILE_BUDGET_LOW (SITE+BUDGET intersect)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_009(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """4 options. Defer-via-soil-test is RECOMMENDED (low-cost, high-info).
    No proceed-anyway in this set per build plan.
    """
    pile_cost_inr = _ec009_pile_cost_inr(gap_analysis)
    pile_lakhs = int(math.ceil(pile_cost_inr / 100_000))
    current_max_lakhs = brief.budget_range.max_lakhs
    target_lakhs = current_max_lakhs + pile_lakhs

    options: list[ResolutionOption] = []

    # Option A — Increase budget to cover the pile foundation
    options.append(ResolutionOption(
        option_id="EC_009_OPT_A_INCREASE_BUDGET_FOR_PILE",
        description=(
            f"Increase budget by ~₹{pile_lakhs} L to cover pile foundation"
        ),
        impact_summary=(
            f"Raises max budget to ₹{target_lakhs} L. Covers the pile "
            f"foundation cost (~₹{pile_lakhs} L) on top of the build "
            f"estimate."
        ),
        cost_impact=CostImpact.build(
            low=int(pile_cost_inr * 0.85),
            mid=int(pile_cost_inr),
            high=int(pile_cost_inr * 1.15),
            confidence=CostConfidence.HIGH,
            derivation=(
                "Pile foundation cost from soil CheckResult details "
                "(C2 / C7 derivation), with ±15% range."
            ),
        ),
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(
            BriefChange(
                field_path="budget.max_lakhs",
                operation="SET",
                new_value=target_lakhs,
                description=(
                    f"Increase budget ceiling to ₹{target_lakhs} L"
                ),
            ),
        ),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option B — Defer via verified soil test (RECOMMENDED)
    options.append(ResolutionOption(
        option_id="EC_009_OPT_B_DEFER_VIA_SOIL_TEST",
        description=(
            "Get a verified geotechnical soil test before deciding"
        ),
        impact_summary=(
            "A real soil test (₹3K-8K) may reveal shallower good soil "
            "layers, in which case pile foundation may not be needed at "
            "all. Low-cost, high-information path before committing to "
            "pile cost."
        ),
        cost_impact=CostImpact.build(
            low=3_000, mid=5_000, high=8_000,
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Geotechnical soil test typical cost — Indian "
                "residential market."
            ),
        ),
        space_impact_sqft=0,
        recommended=True,
        recommendation_reason=(
            "Lowest-cost path: a verified test may eliminate the need "
            "for pile foundation entirely. High information value."
        ),
        requires_brief_change=(),
        requires_action="PAUSE_FOR_USER_VERIFICATION",
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option C — Look for a different plot (last resort)
    options.append(_build_different_plot_option(
        option_id="EC_009_OPT_C_DIFFERENT_PLOT",
        description="Look for a different plot with better soil",
        impact_summary=(
            "Pause this brief and search for a plot whose soil supports "
            "shallow foundation (no pile required)."
        ),
    ))

    # Option D — Preview Mode (always last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# EC-010 — APPROVAL_BLOCKER (varies by resolution_probability)
# ──────────────────────────────────────────────────────────────────────

def _options_for_ec_010(
    case: ExtremeCase, brief: Brief,
    gap_analysis: DesignGapAnalysis,
    co_fired_case_ids: tuple[ExtremeCaseId, ...],
) -> tuple[ResolutionOption, ...]:
    """LOW: 3 options (different plot RECOMMENDED, variance, preview).
    MEDIUM/HIGH: 4 options (variance, consultant, different plot, preview).
    No proceed-anyway in any subtype — regulatory by definition.
    """
    options: list[ResolutionOption] = []

    if case.resolution_probability == ResolutionProbability.LOW:
        # Option A — Look for a different plot (RECOMMENDED)
        options.append(_build_different_plot_option(
            option_id="EC_010_OPT_A_DIFFERENT_PLOT",
            description="Look for a different plot",
            impact_summary=(
                "Pause this brief and search for a plot without this "
                "approval blocker. For LOW-probability blockers (HT "
                "lines, watercourse, heritage overlays) this is "
                "typically the realistic path."
            ),
            recommended=True,
            recommendation_reason=(
                "LOW-probability blockers are rarely resolvable on the "
                "current plot; a different plot is the realistic path."
            ),
        ))

        # Option B — Apply for variance (10% success — long shot)
        options.append(ResolutionOption(
            option_id="EC_010_OPT_B_VARIANCE_APPLICATION",
            description="Apply for a planning variance",
            impact_summary=(
                "3-6 month process; ₹50K-2L typical cost; ~10% success "
                "rate for LOW-probability blockers. Long shot."
            ),
            cost_impact=CostImpact.build(
                low=50_000, mid=125_000, high=200_000,
                confidence=CostConfidence.LOW,
                derivation=(
                    "Variance application cost research; success rate "
                    "for LOW-probability blockers from city planning "
                    "department records."
                ),
            ),
            space_impact_sqft=0,
            recommended=False,
            recommendation_reason=None,
            requires_brief_change=(),
            requires_action=None,
            risk_advisory=(
                "Variance success rate is ~10% for this blocker class; "
                "budget time and cost as likely-sunk."
            ),
            is_preview_mode=False,
        ))

        # Option C — Preview Mode (last)
        options.append(_make_preview_option(case.case_id))
        return tuple(options)

    # MEDIUM (or HIGH) — 4 options
    # Option A — Apply for planning variance (50% success)
    options.append(ResolutionOption(
        option_id="EC_010_OPT_A_VARIANCE_APPLICATION",
        description="Apply for a planning variance",
        impact_summary=(
            "3-6 month process; ₹50K-2L typical cost; ~50% success "
            "rate for MEDIUM-probability blockers (fire access, LT "
            "lines)."
        ),
        cost_impact=CostImpact.build(
            low=50_000, mid=125_000, high=200_000,
            confidence=CostConfidence.LOW,
            derivation=(
                "Variance application cost research; ~50% success for "
                "this blocker class per city planning records."
            ),
        ),
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=(
            "Variance is discretionary; plan for the possibility of "
            "refusal."
        ),
        is_preview_mode=False,
    ))

    # Option B — Engage local planning consultant
    options.append(ResolutionOption(
        option_id="EC_010_OPT_B_LOCAL_CONSULTANT",
        description="Engage a local planning consultant",
        impact_summary=(
            "₹15K-30K consultant fee. Local consultants often know "
            "shortcuts (which department, which forms, which engineer "
            "to talk to). Effective for resolvable blockers."
        ),
        cost_impact=CostImpact.build(
            low=15_000, mid=22_500, high=30_000,
            confidence=CostConfidence.MEDIUM,
            derivation=(
                "Local planning consultant fee — typical Indian "
                "metropolitan range."
            ),
        ),
        space_impact_sqft=0,
        recommended=False,
        recommendation_reason=None,
        requires_brief_change=(),
        requires_action=None,
        risk_advisory=None,
        is_preview_mode=False,
    ))

    # Option C — Look for a different plot
    options.append(_build_different_plot_option(
        option_id="EC_010_OPT_C_DIFFERENT_PLOT",
        description="Look for a different plot",
        impact_summary=(
            "Pause this brief and search for a plot without this "
            "approval blocker."
        ),
    ))

    # Option D — Preview Mode (last)
    options.append(_make_preview_option(case.case_id))

    return tuple(options)


# ──────────────────────────────────────────────────────────────────────
# Public API: OptionGenerator
# ──────────────────────────────────────────────────────────────────────

class OptionGenerator:
    """Generates real ResolutionOption sets for detected ExtremeCases.

    Public API:
        generate_options(case, brief, gap_analysis, co_fired_case_ids)
            -> tuple[ResolutionOption, ...]

    Replaces the placeholder option pair S2's detector produces.
    Per-EC dispatch via case.case_id. S6 orchestrator (later session)
    wires this in after detection.

    co_fired_case_ids carries the set of OTHER ECs detected in this run,
    used for cross-EC promotion logic (EC-002↔EC-006 mutual "different
    plot" promotion). Default empty for direct unit testing; S6
    computes and passes the real set.
    """

    @staticmethod
    def generate_options(
        case: ExtremeCase,
        brief: Brief,
        gap_analysis: DesignGapAnalysis,
        co_fired_case_ids: tuple[ExtremeCaseId, ...] = (),
    ) -> tuple[ResolutionOption, ...]:
        dispatch = {
            ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE:
                _options_for_ec_001,
            ExtremeCaseId.EC_002_PLOT_WIDTH_INSUFFICIENT:
                _options_for_ec_002,
            ExtremeCaseId.EC_003_NO_PARKING_POSITION:
                _options_for_ec_003,
            ExtremeCaseId.EC_004_FAR_EXCEEDED:
                _options_for_ec_004,
            ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED:
                _options_for_ec_005,
            ExtremeCaseId.EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE:
                _options_for_ec_006,
            ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED:
                _options_for_ec_007,
            ExtremeCaseId.EC_008_BUDGET_CATASTROPHICALLY_LOW:
                _options_for_ec_008,
            ExtremeCaseId.EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW:
                _options_for_ec_009,
            ExtremeCaseId.EC_010_APPROVAL_BLOCKER:
                _options_for_ec_010,
        }
        builder = dispatch.get(case.case_id)
        if builder is None:
            raise ValueError(
                f"OptionGenerator: no builder registered for "
                f"{case.case_id!r}"
            )
        return builder(case, brief, gap_analysis, co_fired_case_ids)
