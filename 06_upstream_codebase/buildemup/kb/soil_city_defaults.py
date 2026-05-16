"""
BuildemUp† — typed soil projection adapter for C4 (NEW v0.5).

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# Critique reviewers: these are filed in spec § 16 / § 12; please do NOT re-flag.
# (Strippable review aid.)
#
#   B-072  C7 foundation-design retrofit to consume PlotAnalysis.soil_estimate
#          rather than re-deriving from raw plot. Out of v1 scope.
#   B-079  System-wide KB_VERSION format policy. Codebase has 6+ co-existing
#          format styles ('v1.0', 'Wind_IS875_2026_v1', 'SoilSBC_IS1904_v1_2026',
#          etc.). Cross-component sweep, not a C4-only fix.
#   B-083  Sub-city soil zoning. Single-profile-per-city (this module) is lossy
#          where intra-city variation is large (e.g., Mumbai reclaimed vs basalt;
#          Navi Mumbai shows 5-7× spread within metro area per geotech report).
#          Web-verified S29.
# ─────────────────────────────────────────────────────────────────────────────

WHY THIS MODULE EXISTS
======================
C4 SPEC v0.5 § 4.7.1. Three upstream-facing problems caught by code-grep
round 2 (CG-6, CG-7, CG-8) at the start of Session 29:

  1. CG-6: kb/soil_foundation_rules.py exposes CITY_SOIL_DEFAULTS keyed
     by city — not "SOIL_PROFILES" as v0.4 spec assumed. C4 needs a
     city-keyed dict with a stable name.

  2. CG-7: kb/soil_foundation_rules.SoilProfile.typical_soil is an
     informal string (e.g. "rock_or_hard_clay", "silt_clay"), NOT
     convertible to domain.plot.SoilType. Its bearing field is in
     tonnes/sqm (`safe_bearing_capacity_t_sqm`), not kPa.

  3. CG-8: v0.4 spec referenced BEARING_CAPACITY_BY_TYPE without
     defining it. C4 needs a SoilType → kPa map for the user-input
     branch of estimate_soil().

This module is a typed projection adapter: it sources its values from
the two existing soil KBs and exposes the C4-shaped contract. Pattern
E safe — zero edits to shipped code.

  - Per-city kPa values: derived from
    kb/soil_foundation_rules.CITY_SOIL_DEFAULTS.safe_bearing_capacity_t_sqm
    via t/sqm × 9.81 m/s² ≈ kPa.

  - Per-SoilType kPa values: derived from
    kb/soil_classification.SOIL_PROFILES[SoilClass].sbc_typical_knm2
    via a SoilType (domain) → SoilClass (KB) mapping. As of v1.1 (B-074
    closure), MEDIUM_ROCK is a first-class kb.SoilClass — no more
    approximation downcast.

  - typical_soil per city: closest matching SoilType enum value,
    chosen conservatively (e.g., Mumbai's "rock_or_filled_up" → FILLED_UP,
    triggering LOW confidence in line with the existing CITY_SOIL_DEFAULTS
    note "MANDATORY soil testing").

CONSUMER CONTRACT (per C4 spec § 3 SoilEstimate):
  bearing_capacity_kpa with confidence == LOW means downstream
  components MUST apply a structural safety factor.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.domain.plot import SoilType


KB_VERSION = "v1.1"


# ─────────────────────────────────────────────────────────────────────────────
# Per-city soil profile (typed projection of CITY_SOIL_DEFAULTS)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SoilCityProfile:
    """Typed soil default for a city. Used by C4's city-default branch."""
    typical_soil: SoilType
    typical_bearing_capacity_kpa: float


# 1 t/sqm ≈ 9.81 kPa (g = 9.81 m/s²). City kPa values below derived from
# kb/soil_foundation_rules.CITY_SOIL_DEFAULTS:
#
#   chennai     12.0 t/sqm × 9.81 = 117.7 kPa  (clay)
#   bangalore   20.0 t/sqm × 9.81 = 196.2 kPa  (rock_or_hard_clay)
#   mumbai      15.0 t/sqm × 9.81 = 147.1 kPa  (rock_or_filled_up — VARIABLE)
#   delhi       15.0 t/sqm × 9.81 = 147.1 kPa  (silt_clay)
#   hyderabad   20.0 t/sqm × 9.81 = 196.2 kPa  (rock_or_murrum)
#   pune        18.0 t/sqm × 9.81 = 176.6 kPa  (murrum)
#
# typical_soil mappings (informal city label → SoilType, conservative):
#   chennai     "clay"               → MEDIUM_CLAY
#   bangalore   "rock_or_hard_clay"  → MEDIUM_ROCK   (rocky-typical)
#   mumbai      "rock_or_filled_up"  → FILLED_UP     (CONSERVATIVE: triggers
#                                                      LOW confidence; matches
#                                                      Mumbai docs' "MANDATORY
#                                                      soil testing" note)
#   delhi       "silt_clay"          → MEDIUM_CLAY
#   hyderabad   "rock_or_murrum"     → MEDIUM_ROCK
#   pune        "murrum"             → STIFF_CLAY    (proxy for firm murrum)
SOIL_PROFILES: dict[str, SoilCityProfile] = {
    "chennai":   SoilCityProfile(SoilType.MEDIUM_CLAY, 117.7),
    "bangalore": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),
    "mumbai":    SoilCityProfile(SoilType.FILLED_UP,   147.1),
    "delhi":     SoilCityProfile(SoilType.MEDIUM_CLAY, 147.1),
    "hyderabad": SoilCityProfile(SoilType.MEDIUM_ROCK, 196.2),
    "pune":      SoilCityProfile(SoilType.STIFF_CLAY,  176.6),
}


# ─────────────────────────────────────────────────────────────────────────────
# Per-SoilType bearing capacity (used by user-input branch of estimate_soil)
# ─────────────────────────────────────────────────────────────────────────────

# Sourced from kb.soil_classification.SOIL_PROFILES[SoilClass].sbc_typical_knm2
# via the SoilType (domain) → SoilClass (KB) mapping below. kN/m² == kPa.
#
#   domain.SoilType    → kb.SoilClass        sbc_typical_knm2
#     HARD_ROCK          HARD_ROCK             1620.0
#     MEDIUM_ROCK        MEDIUM_ROCK           1250.0   (v1.1 — B-074 closed)
#     DENSE_SAND         DENSE_SAND             350.0
#     MEDIUM_SAND        MEDIUM_SAND            200.0
#     LOOSE_SAND         LOOSE_SAND             125.0
#     STIFF_CLAY         STIFF_CLAY             250.0
#     MEDIUM_CLAY        MEDIUM_CLAY            125.0
#     SOFT_CLAY          SOFT_CLAY               90.0
#     FILLED_UP          RECLAIMED_FILL          50.0
#
# The mapping is intentionally one-way (no reverse needed): C4 reads
# SoilType from the user; SoilClass is internal to soil_classification.
BEARING_CAPACITY_BY_TYPE: dict[SoilType, float] = {
    SoilType.HARD_ROCK:    1620.0,
    SoilType.MEDIUM_ROCK:  1250.0,   # IS 6403 typical (1000-1500); B-074 v1.1
    SoilType.DENSE_SAND:    350.0,
    SoilType.MEDIUM_SAND:   200.0,
    SoilType.LOOSE_SAND:    125.0,
    SoilType.STIFF_CLAY:    250.0,
    SoilType.MEDIUM_CLAY:   125.0,
    SoilType.SOFT_CLAY:      90.0,
    SoilType.FILLED_UP:      50.0,   # mapped to kb.SoilClass.RECLAIMED_FILL
}


# ─────────────────────────────────────────────────────────────────────────────
# High-variability marker (drives LOW confidence in city-default branch)
# ─────────────────────────────────────────────────────────────────────────────

# When a city's typical_soil falls in this set, estimate_soil() returns
# ConfidenceLevel.LOW for the city-default branch. Per spec § 4.7.
HIGH_VARIABILITY_SOIL_TYPES: frozenset[SoilType] = frozenset({
    SoilType.SOFT_CLAY,    # highly variable; site survey strongly recommended
    SoilType.LOOSE_SAND,   # liquefaction risk; varies with water table
    SoilType.FILLED_UP,    # made-up ground — always low-confidence
})


# ─────────────────────────────────────────────────────────────────────────────
# Approximation notes (v0.8 walk #8 — moved from logic layer to KB layer)
# ─────────────────────────────────────────────────────────────────────────────

# v0.8 (walk #8) contract: SoilType values that the underlying
# kb.soil_classification does NOT carry as a first-class class get a
# breadcrumb note here so downstream consumers see provenance instead
# of silently inheriting an approximated kPa value.
#
# v1.1 (B-074 closed): the previous MEDIUM_ROCK entry was removed when
# kb.SoilClass gained a first-class MEDIUM_ROCK entry (1000-1500 kPa
# typ 1250 per IS 6403). The export hook is preserved as an empty dict
# so the v0.8 surface contract (consumers may probe for breadcrumbs)
# stays stable.
APPROXIMATION_NOTES_BY_SOIL_TYPE: dict[SoilType, str] = {}


# Coverage invariants checked by tests:
#   - Every domain.plot.SoilType value is a key in BEARING_CAPACITY_BY_TYPE.
#   - SOIL_PROFILES covers every city in domain.plot.SUPPORTED_CITIES.
# The KB-drift check (verify_kb_consistency in kb.city_geography) handles
# the latter as part of the cross-KB invariant.

__all__ = [
    "KB_VERSION",
    "SoilCityProfile",
    "SOIL_PROFILES",
    "BEARING_CAPACITY_BY_TYPE",
    "HIGH_VARIABILITY_SOIL_TYPES",
    "APPROXIMATION_NOTES_BY_SOIL_TYPE",
]
