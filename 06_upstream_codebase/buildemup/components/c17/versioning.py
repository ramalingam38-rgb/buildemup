"""
C17 — Quote Comparison Engine — versioning constants
======================================================

Per C17 v0.3 LOCKED spec (S50 close, May 15 2026), composed of:
    spec_C17_v0_1_PROPOSED.md     (foundational v0.1 — S49 close)
    spec_C17_v0_2_PROPOSED.md     (12 SPEC-AMENDMENTs — walk #1)
    spec_C17_v0_3_LOCKED.md       (4 SPEC-AMENDMENTs — walk #2: R15 narrow,
                                   § 1.4 applicability, § 26 bundle scope,
                                   § 27.5 explainability)

These constants are the IMMUTABLE knobs every C17 module reads from.

Pinned at v0.3 LOCK:
    C17_VERSION                     : str   = "v0.3.LOCKED"
    C17_REPORT_SCHEMA_VERSION       : int   = 2
    C17_IDENTITY_GENERATION         : int   = 1
"""

from __future__ import annotations

from typing import Final, FrozenSet


# ============================================================
# § 1 — VERSION TRIPLE (R6, R8, R11)
# ============================================================

C17_VERSION: Final[str] = "v0.3.LOCKED"
"""Component version. Updated at every LOCK milestone.

Cache-relevant. Any v0.x → v0.y bump invalidates all C17 caches."""

C17_REPORT_SCHEMA_VERSION: Final[int] = 2
"""Report-schema version. Cumulative bumps across amendments:

    v0.1 baseline                                              :  1
    v0.2 RateStalenessDisclosure + DecompositionAcknowledgment
         + ReportConfidence + PriceSignal rename               :  2
    v0.3 R15 narrowing / § 1.4 / § 26 / § 27.5  (DOCUMENTATION
         only — no schema-field additions; per v0.3 spec § 5)   :  2 (unchanged)

R8/R12: adding fields → MINOR bump; removing/renaming → MAJOR bump.
"""

C17_IDENTITY_GENERATION: Final[int] = 1
"""Identity-generation scope (parallel to C16's R33).

Bumps ONLY on signature-algorithm changes or canonicalization-rule
changes that would render previously-emitted reports non-reproducible.
Does NOT bump on schema MINOR additions."""


# ============================================================
# § 2 — EXPECTED UPSTREAM VERSIONS (spec § 8)
# ============================================================

EXPECTED_C7_VERSION:  Final[str] = "v0.8"
"""C7 Structural Grid Engine — provides RateProvider, MaterialRate,
TransparencyTriple via project utils, and cost-derived BOQ items."""

EXPECTED_C16_VERSION: Final[str] = "v0.5"
"""C16 Dual-Drawing Renderer — provides AttestedValue, AuthorityKind,
CheckProvenance, AdvisoryFlag. Re-used (not duplicated) by C17."""


# ============================================================
# § 3 — JURISDICTION + DOMAIN SCOPE (spec § 5)
# ============================================================

SUPPORTED_JURISDICTIONS: Final[FrozenSet[str]] = frozenset({"tn_cdbr_2019"})
"""v1.0 jurisdictions. Chennai-only at LOCK.
B-C17-MICRO-MARKET-CALIBRATION expands post-launch."""

SUPPORTED_DOMAIN_SCOPES: Final[FrozenSet[str]] = frozenset({
    "residential_v1",
})
"""v1.0 scope per spec § 1.4 applicability boundary.
Informal/mason-led/family-network builds explicitly out-of-scope —
heuristic detection still operates, surfacing as
human_review_recommended (R17) with explicit advisory note."""


# ============================================================
# § 4 — HARD CEILINGS (spec § 6)
# ============================================================

HARD_CEILING_PARSED_QUOTE_LINE_COUNT: Final[int] = 500
"""ParsedQuote.line_items length. Beyond this, the quote is structurally
too complex for reliable per-line comparison; require human review."""

HARD_CEILING_QUOTE_TOTAL_INR: Final[float] = 50_00_00_000.0
"""₹50 crore. Above residential v1.0 scope per § 1.4."""

HARD_CEILING_LINE_AMOUNT_INR: Final[float] = 1_00_00_000.0
"""₹1 crore per single line — anything larger is almost certainly a
bundle masquerading as a line item; route via DecompositionAcknowledgment."""

HARD_CEILING_MATERIAL_RATE_PER_UNIT_INR: Final[float] = 1_00_000.0
"""₹1 lakh per unit. Above this, MaterialRate is almost certainly
mis-categorized (rate vs. lump-sum confusion)."""


# ============================================================
# § 5 — FUZZY-MATCH + CONFIDENCE THRESHOLDS (spec § 6)
# ============================================================
#
# These are TIER BOUNDARIES, not user-facing publishable numbers.
# Per spec § 27.1 — internal heuristic, NOT in user-facing docs.
# Per spec § 27.2 — rotates ±20% per quarter under
# B-C17-HEURISTIC-ROTATION-DISCIPLINE. v1.0 ships with these defaults.

LEVENSHTEIN_HARD_CEILING: Final[float] = 0.4
"""Levenshtein-similarity floor; below this, no match candidate is
returned at all (line goes to unmatched_quote_lines)."""

MATCH_TIER_HIGH_THRESHOLD: Final[float] = 0.85
"""Confidence ≥ 0.85 + IS-code or brand+grade exact → tier='high'."""

MATCH_TIER_MEDIUM_THRESHOLD: Final[float] = 0.65
"""Confidence in [0.65, 0.85) → tier='medium'."""

MATCH_TIER_LOW_THRESHOLD: Final[float] = 0.5
"""Confidence in [0.5, 0.65) → tier='low'."""

MATCH_TIER_HUMAN_REVIEW_THRESHOLD: Final[float] = 0.3
"""Confidence in [0.3, 0.5) → tier='human_verification_recommended'.
Below 0.3 → no candidate emitted."""


# ============================================================
# § 6 — PRICE SIGNAL THRESHOLDS (spec § 2.3)
# ============================================================
#
# Per spec § 27.1: these are INTERNAL.
# Per spec § 27.5: NOT published to end users; user-facing report
# describes CATEGORIES only.

PRICE_SIGNAL_ABOVE_REFERENCE_PCT: Final[float] = 20.0
"""rate_delta_pct > +20% (with high/medium match) → ABOVE_REFERENCE_RANGE."""

PRICE_SIGNAL_ABOVE_TYPICAL_PCT: Final[float] = 5.0
"""rate_delta_pct in (+5%, +20%] → ABOVE_TYPICAL."""

PRICE_SIGNAL_WITHIN_TYPICAL_PCT: Final[float] = 5.0
"""rate_delta_pct in [-5%, +5%] → WITHIN_TYPICAL."""

PRICE_SIGNAL_BELOW_TYPICAL_PCT: Final[float] = -5.0
"""rate_delta_pct in [-20%, -5%) → BELOW_TYPICAL (note: not a public enum;
collapses into WITHIN_TYPICAL because mild under-quote is not a quality risk)."""

PRICE_SIGNAL_BELOW_QUALITY_RISK_PCT: Final[float] = -20.0
"""rate_delta_pct < -20% → BELOW_TYPICAL_QUALITY_RISK
(advisory only — never accusatory; R2 + R5)."""


# ============================================================
# § 7 — BUNDLE-LEVEL COMPARISON (spec § 26.2)
# ============================================================

BUNDLE_THRESHOLD_INFLATION_FACTOR: Final[float] = 3.0
"""When DecompositionAcknowledgment.detected_decomposition_style is NOT
'line_itemized', threshold tolerances are inflated by 3.0× and the
PriceSignal is downgraded one tier (R18 + spec § 26.2)."""

BUNDLE_PCT_DOMINANCE_THRESHOLD: Final[float] = 50.0
"""If ≥ 50% of quote ₹-value comes from bundle lines, ReportConfidence
caps at 'moderate_signal' regardless of other indicators (spec § 26.2)."""


# ============================================================
# § 8 — REPORT-CONFIDENCE TIER THRESHOLDS (spec § 2.10, R17)
# ============================================================

REPORT_TIER_HIGH_SIGNAL_PCT: Final[float] = 75.0
"""≥ 75% high+medium matches → overall_report_tier='high_signal'."""

REPORT_TIER_MODERATE_SIGNAL_PCT: Final[float] = 50.0
"""50–75% → 'moderate_signal'; <50% → 'high_ambiguity'."""

REPORT_TIER_HUMAN_REVIEW_PCT: Final[float] = 25.0
"""≥ 25% human_verification_recommended → 'human_review_recommended'
regardless of other tier counts (R17)."""


# ============================================================
# § 9 — INFORMAL-CONSTRUCTION HEURISTICS (spec § 1.4)
# ============================================================
#
# These detect quotes from labor-exchange / mason-led / family-network
# arrangements where C17's comparative model misframes the relationship.
# When ANY 2 of these fire, set overall_report_tier='human_review_recommended'
# with the explicit advisory note from spec § 1.4.

INFORMAL_HEURISTIC_BRAND_SPEC_MIN_PCT: Final[float] = 10.0
"""If <10% of line items have brand/grade specifications → signal."""

INFORMAL_HEURISTIC_UNIT_RATE_MIN_PCT: Final[float] = 30.0
"""If <30% of lines have unit rates → signal."""

INFORMAL_HEURISTIC_LUMP_SUM_MAX_PCT: Final[float] = 60.0
"""If >60% of ₹-value is lump-sum lines → signal."""

INFORMAL_HEURISTIC_LINE_COUNT_MIN: Final[int] = 5
"""If <5 line items for a residential project → signal (scope-as-prose)."""


# ============================================================
# § 10 — EPSILON POLICY (spec § 5)
# ============================================================

EPSILON_RATE_DELTA_PCT: Final[float] = 0.5
"""rate_delta_pct comparisons: any |Δ| < 0.5% treated as zero for
PriceSignal binning. Below the precision RateProvider rates carry."""

EPSILON_AMOUNT_INR: Final[float] = 100.0
"""₹100 tolerance on total_delta arithmetic — banker's rounding artifacts.
Real comparison thresholds run in tens-of-thousands or lakhs."""


# ============================================================
# § 11 — REPR
# ============================================================

def version_triple() -> tuple[str, int, int]:
    """The (R6) provenance triple, programmatically accessible."""
    return (C17_VERSION, C17_REPORT_SCHEMA_VERSION, C17_IDENTITY_GENERATION)


def version_summary() -> str:
    """Human-readable summary for logging and provenance records."""
    return (
        f"C17 {C17_VERSION} "
        f"(report_schema={C17_REPORT_SCHEMA_VERSION}, "
        f"identity_gen={C17_IDENTITY_GENERATION})"
    )
