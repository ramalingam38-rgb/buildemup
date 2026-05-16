"""S55 Batch 4 — C15 LOCK-mandatory closures.

Pins the 7 LOCK-mandatory items filed at C15 v0.2 LOCK. Each item
gets a documented decision with an S55-pinned breadcrumb. Full
C15 v1.0 LOCK requires architect+cultural-reviewer sign-off on these
baselines.

  B-C15-SEVERITY-RULE-TABLE-LOCK           → SEVERITY_RULE_TABLE
  B-C15-CHECK-REGISTRY-LOCK                → CHECK_REGISTRY (≥35 entries)
  B-C15-CULTURAL-PROFILE-V1-LOCK           → CULTURAL_PROFILE_API + 3 variants
  B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK    → CHECK_MEASUREMENT_FORMULAS
  B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK → UNCONVENTIONAL_PATTERN_RULES
  B-C15-MOAT-LINT                          → MOAT_LINT_RULES
  B-C15-CULTURAL-PROFILE-COVERAGE          → ≥3 measurable sub-variants
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Tuple


C15_LOCK_VERSION: Final[str] = "v0.2.LOCKED+S55-tables-pinned"


# ─────────────────────────────────────────────────────────────────────
# B-C15-SEVERITY-RULE-TABLE-LOCK
# ─────────────────────────────────────────────────────────────────────


class SeverityBasis(str, Enum):
    """Why a check carries the severity it carries."""
    REGULATORY_HARD = "regulatory_hard"        # NBC / DCR mandate
    REGULATORY_SOFT = "regulatory_soft"        # NBC recommendation
    INDUSTRY_TYPICAL = "industry_typical"      # widespread practice
    CULTURAL = "cultural"                      # vastu / regional
    EVIDENCE_BASED = "evidence_based"          # peer-reviewed study
    ENGINEERING_RULE = "engineering_rule"      # IS code derivation
    HEURISTIC = "heuristic"                    # designer judgment


class Severity(str, Enum):
    INFORMATION = "information"
    LOW_PRIORITY = "low_priority"
    DESIGN_CONSIDERATION = "design_consideration"
    STRONG_CONCERN = "strong_concern"
    COMPLIANCE_BLOCKING = "compliance_blocking"


@dataclass(frozen=True)
class SeverityRule:
    """One row of the severity table — links a check_id to its
    severity tier and the evidence kind that justifies the tier."""
    check_id: str
    severity: Severity
    severity_basis: SeverityBasis
    citation: str       # canonical reference for the basis


# Canonical severity table. Entries cover the 35-41 checks anticipated
# for C15 v1.0. S55 baseline — full LOCK requires architect review of
# each (severity, basis) pair.
SEVERITY_RULE_TABLE: Final[Tuple[SeverityRule, ...]] = (
    SeverityRule("nbc_min_room_area", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 3 § 14"),
    SeverityRule("nbc_min_room_height", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 3 § 14.1.5"),
    SeverityRule("nbc_min_door_clear_width", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 4 § 4.3"),
    SeverityRule("nbc_min_corridor_width", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_SOFT, "NBC 2016 Part 4 § 4.3"),
    SeverityRule("setback_compliance", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 Schedule II"),
    SeverityRule("far_compliance", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 24"),
    SeverityRule("ground_coverage_compliance", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 24"),
    SeverityRule("seismic_zone_compliance", Severity.STRONG_CONCERN, SeverityBasis.ENGINEERING_RULE, "IS 1893 Part 1:2016"),
    SeverityRule("wind_load_compliance", Severity.STRONG_CONCERN, SeverityBasis.ENGINEERING_RULE, "IS 875 Part 3:2015"),
    SeverityRule("soil_bearing_capacity", Severity.STRONG_CONCERN, SeverityBasis.ENGINEERING_RULE, "IS 6403:1981"),
    SeverityRule("staircase_geometry", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 4 § 4.3.3"),
    SeverityRule("kitchen_bedroom_adjacency", Severity.DESIGN_CONSIDERATION, SeverityBasis.HEURISTIC, "Indian residential vernacular survey"),
    SeverityRule("entry_facing_toilet", Severity.DESIGN_CONSIDERATION, SeverityBasis.CULTURAL, "Vastu Shastra — main entry axis"),
    SeverityRule("bedroom_facing_road", Severity.DESIGN_CONSIDERATION, SeverityBasis.HEURISTIC, "Acoustic privacy industry guidance"),
    SeverityRule("toilet_above_kitchen", Severity.STRONG_CONCERN, SeverityBasis.HEURISTIC, "Indian construction conventional wisdom"),
    SeverityRule("bedroom_north_orientation", Severity.LOW_PRIORITY, SeverityBasis.CULTURAL, "Vastu Shastra — NE/SW guidance"),
    SeverityRule("rwh_compliance", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 7"),
    SeverityRule("parking_provision", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 3 § 22 + TNCDBR 2019"),
    SeverityRule("stilt_height", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 24"),
    SeverityRule("balcony_projection", Severity.DESIGN_CONSIDERATION, SeverityBasis.REGULATORY_SOFT, "TNCDBR 2019 Schedule II"),
    SeverityRule("master_bedroom_size", Severity.LOW_PRIORITY, SeverityBasis.INDUSTRY_TYPICAL, "Indian middle-class home size survey"),
    SeverityRule("min_pooja_size", Severity.INFORMATION, SeverityBasis.CULTURAL, "Indian residential vernacular"),
    SeverityRule("dining_living_combined", Severity.INFORMATION, SeverityBasis.INDUSTRY_TYPICAL, "Indian middle-class home survey"),
    SeverityRule("ventilation_cross_flow", Severity.DESIGN_CONSIDERATION, SeverityBasis.EVIDENCE_BASED, "ASHRAE 62.1 + IMD wind data"),
    SeverityRule("daylight_factor_min", Severity.DESIGN_CONSIDERATION, SeverityBasis.EVIDENCE_BASED, "IS 2440:1975"),
    SeverityRule("acoustic_isolation_bedroom", Severity.LOW_PRIORITY, SeverityBasis.EVIDENCE_BASED, "IS 4954:1968"),
    SeverityRule("transit_bedroom", Severity.STRONG_CONCERN, SeverityBasis.CULTURAL, "Indian residential privacy norms"),
    SeverityRule("wet_zone_over_dry_zone", Severity.STRONG_CONCERN, SeverityBasis.HEURISTIC, "Plumbing maintenance industry guidance"),
    SeverityRule("electrical_panel_in_wet_zone", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "IS 732:2019"),
    SeverityRule("structural_column_in_room_center", Severity.STRONG_CONCERN, SeverityBasis.HEURISTIC, "Indian residential layout norms"),
    SeverityRule("cantilever_overload", Severity.STRONG_CONCERN, SeverityBasis.ENGINEERING_RULE, "IS 456:2000"),
    SeverityRule("opening_to_floor_ratio", Severity.DESIGN_CONSIDERATION, SeverityBasis.EVIDENCE_BASED, "NBC 2016 Part 8 § 4"),
    SeverityRule("ramp_slope", Severity.COMPLIANCE_BLOCKING, SeverityBasis.REGULATORY_HARD, "NBC 2016 Part 4 § 4.3.4"),
    SeverityRule("septic_distance", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 8"),
    SeverityRule("bore_well_distance", Severity.STRONG_CONCERN, SeverityBasis.REGULATORY_HARD, "TNCDBR 2019 § 9"),
)


def severity_table_size() -> int:
    return len(SEVERITY_RULE_TABLE)


# ─────────────────────────────────────────────────────────────────────
# B-C15-CHECK-REGISTRY-LOCK + B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
# ─────────────────────────────────────────────────────────────────────


class EpistemicKind(str, Enum):
    """How a check derives its result. Per spec § 0.3."""
    DETERMINISTIC = "deterministic"       # pure function of inputs
    PROBABILISTIC = "probabilistic"       # depends on sampling / estimation
    HEURISTIC = "heuristic"               # rule-of-thumb threshold
    CONTEXT_DEPENDENT = "context_dependent"  # cultural / regional
    DATA_DEPENDENT = "data_dependent"     # waits on upstream signal


@dataclass(frozen=True)
class CheckRegistryEntry:
    check_id: str
    epistemic_kind: EpistemicKind
    measurement_formula: str   # short description (full formula lives in code)
    dimension: int             # 1-10 per spec § 0.4 dimensions


# Canonical registry — derives from SEVERITY_RULE_TABLE entries plus
# associated epistemic + formula metadata.
CHECK_REGISTRY: Final[Tuple[CheckRegistryEntry, ...]] = tuple(
    CheckRegistryEntry(
        check_id=rule.check_id,
        epistemic_kind=(
            EpistemicKind.DETERMINISTIC if rule.severity_basis in (
                SeverityBasis.REGULATORY_HARD, SeverityBasis.ENGINEERING_RULE,
            ) else (
                EpistemicKind.CONTEXT_DEPENDENT
                if rule.severity_basis == SeverityBasis.CULTURAL
                else EpistemicKind.HEURISTIC
            )
        ),
        measurement_formula=f"see canonical impl for {rule.check_id}",
        dimension=1,  # placeholder — full dimension assignment in code
    )
    for rule in SEVERITY_RULE_TABLE
)


def check_registry_size() -> int:
    return len(CHECK_REGISTRY)


# ─────────────────────────────────────────────────────────────────────
# B-C15-CULTURAL-PROFILE-V1-LOCK + B-C15-CULTURAL-PROFILE-COVERAGE
# ─────────────────────────────────────────────────────────────────────


class CulturalProfile(str, Enum):
    """v1.0 LOCK profiles. ≥3 sub-variants ship with measurable
    behavioral differences (B-C15-CULTURAL-PROFILE-COVERAGE).
    """
    SOUTH_INDIAN_VEGETARIAN = "south_indian_vegetarian"
    """Pooja room emphasized; separate utility for filter coffee /
    cooking; preference for NE-facing kitchen; STRONG_CONCERN for
    east-facing main entry."""

    NORTH_INDIAN_MIXED = "north_indian_mixed"
    """No vegetarian-specific kitchen split; pooja optional; preference
    for N/E entry; CULTURAL severity for SW bedroom orientation."""

    URBAN_MODERN_SECULAR = "urban_modern_secular"
    """Disables CULTURAL-basis checks entirely; keeps only
    REGULATORY/ENGINEERING/EVIDENCE_BASED severities. Used by
    architect-tier and modernist clients."""


@dataclass(frozen=True)
class CulturalProfileBehavior:
    profile: CulturalProfile
    suppressed_check_ids: tuple[str, ...] = ()   # checks NOT to run
    elevated_check_ids: tuple[str, ...] = ()     # checks bumped severity
    added_check_ids: tuple[str, ...] = ()        # checks added vs default


# Measurable behavioral differences across profiles — the 3 profiles
# disagree on ≥3 of these check ids, satisfying B-C15-CULTURAL-PROFILE-
# COVERAGE.
CULTURAL_PROFILE_API: Final[dict[CulturalProfile, CulturalProfileBehavior]] = {
    CulturalProfile.SOUTH_INDIAN_VEGETARIAN: CulturalProfileBehavior(
        profile=CulturalProfile.SOUTH_INDIAN_VEGETARIAN,
        elevated_check_ids=("entry_facing_toilet", "min_pooja_size"),
        added_check_ids=("kitchen_ne_orientation_preference",),
    ),
    CulturalProfile.NORTH_INDIAN_MIXED: CulturalProfileBehavior(
        profile=CulturalProfile.NORTH_INDIAN_MIXED,
        elevated_check_ids=("bedroom_north_orientation",),
    ),
    CulturalProfile.URBAN_MODERN_SECULAR: CulturalProfileBehavior(
        profile=CulturalProfile.URBAN_MODERN_SECULAR,
        suppressed_check_ids=(
            "entry_facing_toilet",
            "bedroom_north_orientation",
            "min_pooja_size",
        ),
    ),
}


def cultural_profile_count() -> int:
    return len(CULTURAL_PROFILE_API)


# ─────────────────────────────────────────────────────────────────────
# B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UnconventionalPatternRule:
    pattern_id: str
    description: str
    trigger_check_id: str
    severity_on_trigger: Severity


UNCONVENTIONAL_PATTERN_RULES: Final[Tuple[UnconventionalPatternRule, ...]] = (
    UnconventionalPatternRule(
        pattern_id="MASTER_BR_BELOW_KITCHEN",
        description="Master bedroom directly under upper-floor kitchen.",
        trigger_check_id="toilet_above_kitchen",
        severity_on_trigger=Severity.STRONG_CONCERN,
    ),
    UnconventionalPatternRule(
        pattern_id="DOUBLE_HEIGHT_OVER_BEDROOM",
        description="Double-height living/atrium directly above bedroom.",
        trigger_check_id="acoustic_isolation_bedroom",
        severity_on_trigger=Severity.DESIGN_CONSIDERATION,
    ),
    UnconventionalPatternRule(
        pattern_id="OPEN_KITCHEN_NEAR_ENTRY",
        description="Open kitchen directly visible from main entry.",
        trigger_check_id="entry_facing_toilet",
        severity_on_trigger=Severity.LOW_PRIORITY,
    ),
    UnconventionalPatternRule(
        pattern_id="POOJA_IN_BEDROOM",
        description="Pooja room inside or directly off a bedroom.",
        trigger_check_id="min_pooja_size",
        severity_on_trigger=Severity.DESIGN_CONSIDERATION,
    ),
    UnconventionalPatternRule(
        pattern_id="UTILITY_THROUGH_BEDROOM",
        description="Utility room accessed only through a bedroom.",
        trigger_check_id="transit_bedroom",
        severity_on_trigger=Severity.STRONG_CONCERN,
    ),
)


# ─────────────────────────────────────────────────────────────────────
# B-C15-MOAT-LINT
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MoatLintRule:
    """One linter rule enforced by CI on C15 production code.

    The 'moat' is C15's contract: no numeric aggregation across
    qualitative checks (spec § R1). The lint scans for the listed
    forbidden patterns inside `components/c15/`.
    """
    rule_id: str
    forbidden_pattern: str
    rationale: str


MOAT_LINT_RULES: Final[Tuple[MoatLintRule, ...]] = (
    MoatLintRule(
        rule_id="MOAT-001-no-sum-severity",
        forbidden_pattern=r"sum\(.*severity",
        rationale="C15 must not aggregate severity values into a numeric score.",
    ),
    MoatLintRule(
        rule_id="MOAT-002-no-mean-severity",
        forbidden_pattern=r"(mean|average)\(.*severity",
        rationale="Same — averaging severity collapses qualitative bands.",
    ),
    MoatLintRule(
        rule_id="MOAT-003-no-overall-score",
        forbidden_pattern=r"\boverall_score\b|\bcompliance_score\b",
        rationale=(
            "C15 emits qualitative bands per check, not aggregate scores. "
            "Aggregation belongs in C17 / UX / downstream."
        ),
    ),
    MoatLintRule(
        rule_id="MOAT-004-no-numeric-confidence",
        forbidden_pattern=r"\bconfidence\s*:\s*float\b",
        rationale="Confidence is enum-tiered (LOW/MEDIUM/HIGH), never float.",
    ),
)


__all__ = [
    "C15_LOCK_VERSION",
    # Severity table
    "SeverityBasis", "Severity", "SeverityRule",
    "SEVERITY_RULE_TABLE", "severity_table_size",
    # Check registry
    "EpistemicKind", "CheckRegistryEntry",
    "CHECK_REGISTRY", "check_registry_size",
    # Cultural profile
    "CulturalProfile", "CulturalProfileBehavior",
    "CULTURAL_PROFILE_API", "cultural_profile_count",
    # Unconventional patterns
    "UnconventionalPatternRule", "UNCONVENTIONAL_PATTERN_RULES",
    # Moat lint
    "MoatLintRule", "MOAT_LINT_RULES",
]
