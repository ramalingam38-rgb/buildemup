"""
C3b — Phase β lookup tables (spec § 3 Phase β step 4.1 + § 2.4.1)
====================================================================

Three static tables drive Phase β tweak generation:

  TWEAK_CATEGORY_DEFAULT_SEVERITY  — initial severity per category
                                      (before context-aware promotion)
  TWEAK_CATEGORY_IMPACT_TABLE      — static downstream_impact_set per category
                                      (per spec § 2.4.1)
  TWEAK_CATEGORY_COMPONENTS_TO_RERUN — which downstream components must run

Plus:

  PROBLEM_CHECK_TWEAK_PATTERNS     — maps ProblemReport check_id patterns to
                                      candidate tweak categories

Rule 11 self-analysis:
  1. The "static minimum impact set" per spec § 2.4.1 is what Phase β
     declares UPFRONT. Phase ε may widen it at apply-time if the
     specific tweak instance touches more than the minimum — but never
     narrow it. Documented.
  2. LIGHT-default categories (door_relocate, balcony_*, window_*) still
     have entries in IMPACT_TABLE because they can be promoted to
     MEDIUM by context (load-bearing wall, etc.) and need an impact
     set when that happens.
  3. PROBLEM_CHECK_TWEAK_PATTERNS uses substring matching on check_id
     because C15 ProblemCheck IDs are stable strings; concrete IDs
     are LOCKED in C15 v1.0 but their names are not exhaustively known
     here. We match prefixes (e.g., "shower_min_*") which is robust
     to additions.
  4. Categories not present here (e.g., a hypothetical room split) are
     intentionally NOT in v1.0 scope; phase β raises TweakGenerationError
     in STRICT mode when an unknown category appears (defensive).
"""
from __future__ import annotations

from typing import Final

from ..schema import (
    DownstreamComponent,
    DownstreamImpact,
    SeverityTier,
    TweakCategory,
)


# ============================================================
# § 1 — Default severity per tweak category (spec § 3 Phase β 4.1)
# ============================================================

TWEAK_CATEGORY_DEFAULT_SEVERITY: Final[dict[TweakCategory, SeverityTier]] = {
    # LIGHT defaults — no pipeline rerun by default
    "finish_upgrade":          "light",
    "finish_downgrade":        "light",
    "door_relocate":           "light",   # context can promote
    "window_resize":           "light",   # context can promote
    "balcony_add":             "light",   # context can promote
    "balcony_remove":          "light",   # context can promote
    # MEDIUM defaults — partial pipeline rerun
    "storage_add":             "medium",
    "utility_zone_carveout":   "medium",
    "room_swap":               "medium",
    "room_resize":             "medium",  # context can promote to HEAVY
    "pooja_relocate":          "medium",
    "kitchen_reorient":        "medium",
    "wet_zone_restage":        "medium",
}


# ============================================================
# § 2 — Static minimum downstream_impact_set per category (§ 2.4.1)
# ============================================================
# Per spec § 2.4.1: "every tweak category has a static minimum
# impact set declared in TWEAK_CATEGORY_IMPACT_TABLE"

TWEAK_CATEGORY_IMPACT_TABLE: Final[dict[TweakCategory, tuple[DownstreamImpact, ...]]] = {
    # LIGHT defaults — impact sets only used if context-promoted to MEDIUM
    "finish_upgrade":          ("finish_schedule",),
    "finish_downgrade":        ("finish_schedule",),
    "door_relocate":           ("door_placement",),
    "window_resize":           ("natural_light",),
    "balcony_add":             ("cross_ventilation", "natural_light"),
    "balcony_remove":          ("cross_ventilation", "natural_light"),
    # MEDIUM defaults
    "storage_add":             ("circulation_graph", "furniture_fit"),
    "utility_zone_carveout":   ("circulation_graph", "furniture_fit"),
    "room_swap":               (
        "circulation_graph", "furniture_fit",
        "problem_report", "ranking_score",
    ),
    "room_resize":             (
        "circulation_graph", "furniture_fit",
        "problem_report", "ranking_score", "structural_grid",
    ),
    "pooja_relocate":          (
        "circulation_graph", "natural_light", "problem_report",
    ),
    "kitchen_reorient":        (
        "cross_ventilation", "natural_light",
        "problem_report", "wet_zone_stacks",
    ),
    "wet_zone_restage":        (
        "problem_report", "vertical_alignment", "wet_zone_stacks",
    ),
}


# ============================================================
# § 3 — Components-to-rerun per category
# ============================================================
# Strictly lex-ASC sorted at runtime (we sort here in source for
# legibility but the spec § 2.4.1 mandates lex-ASC on the actual
# SubsetRerunRequest emit).

TWEAK_CATEGORY_COMPONENTS_TO_RERUN: Final[dict[TweakCategory, tuple[DownstreamComponent, ...]]] = {
    # LIGHT defaults — empty rerun set (no subset rerun for LIGHT)
    "finish_upgrade":          (),
    "finish_downgrade":        (),
    # context-promotable LIGHTs (when promoted to MEDIUM, these fire):
    "door_relocate":           ("c13",),
    "window_resize":           ("c13",),
    "balcony_add":             ("c12", "c13"),
    "balcony_remove":          ("c12", "c13"),
    # MEDIUM
    "storage_add":             ("c12", "c9"),    # will be sorted lex-ASC at emit
    "utility_zone_carveout":   ("c12", "c9"),
    "room_swap":               ("c12", "c13", "c14"),
    "room_resize":             ("c12", "c13", "c14", "c9"),
    "pooja_relocate":          ("c12", "c13"),
    "kitchen_reorient":        ("c10", "c12", "c13"),
    "wet_zone_restage":        ("c10", "c12"),
}


# ============================================================
# § 4 — ProblemCheck → tweak-category mapping (spec § 3 Phase β step 1)
# ============================================================
# C15 ProblemCheck check_ids are opaque (P{dim}.{idx}); semantic
# routing happens via TWO signals:
#
#   1. DIMENSION_TWEAK_MAP: coarse — dimension_id (1..10) → candidates
#   2. WHY_IT_MATTERS_KEYWORDS: fine — substring in why_it_matters
#      narrows to specific categories
#
# A check matches if its dimension_id is in DIMENSION_TWEAK_MAP and any
# keyword in WHY_IT_MATTERS_KEYWORDS matches its why_it_matters text.
# If no keyword matches but dimension matches, use dimension's default.

# Dimension semantic mapping (per C15 v0.3 § 1.4):
#   D1 setbacks       → no tweaks (regulatory; out of C3b scope)
#   D2 plot geometry  → no tweaks
#   D3 area           → room_resize
#   D4 BHK            → no tweaks (room_swap if function mismatch)
#   D5 vastu          → pooja_relocate, kitchen_reorient
#   D6 kitchen        → kitchen_reorient, room_resize
#   D7 bathroom       → room_resize, wet_zone_restage
#   D8 storage        → storage_add, utility_zone_carveout
#   D9 corridor       → utility_zone_carveout, door_relocate
#   D10 ventilation   → window_resize, balcony_add, kitchen_reorient

DIMENSION_TWEAK_MAP: Final[dict[int, tuple[TweakCategory, ...]]] = {
    1: (),                                              # setbacks — no tweaks
    2: (),                                              # plot geometry — no tweaks
    3: ("room_resize",),                                # area
    4: ("room_swap",),                                  # BHK
    5: ("pooja_relocate", "kitchen_reorient"),          # vastu
    6: ("kitchen_reorient", "room_resize"),             # kitchen
    7: ("room_resize", "wet_zone_restage", "door_relocate"),  # bathroom
    8: ("storage_add", "utility_zone_carveout"),        # storage
    9: ("utility_zone_carveout", "door_relocate"),      # corridor
    10: ("window_resize", "balcony_add", "kitchen_reorient"),  # ventilation
}

# Why-it-matters keyword refinement (substring match, case-insensitive).
# Maps phrases that commonly appear in why_it_matters to categories.
WHY_IT_MATTERS_KEYWORDS: Final[tuple[tuple[str, tuple[TweakCategory, ...]], ...]] = (
    # Bathroom / wet-zone
    ("shower",                  ("room_resize", "door_relocate")),
    ("bath",                    ("room_resize", "wet_zone_restage")),
    ("wet zone",                ("wet_zone_restage",)),
    ("wet-zone",                ("wet_zone_restage",)),
    ("stack",                   ("wet_zone_restage",)),
    # Kitchen
    ("kitchen orientation",     ("kitchen_reorient",)),
    ("kitchen ventilation",     ("kitchen_reorient", "window_resize")),
    ("kitchen morning light",   ("kitchen_reorient",)),
    ("kitchen min",             ("room_resize",)),
    # Pooja
    ("pooja",                   ("pooja_relocate",)),
    ("vastu",                   ("pooja_relocate", "kitchen_reorient")),
    # Storage
    ("storage",                 ("storage_add",)),
    ("utility zone",            ("utility_zone_carveout",)),
    # Circulation
    ("corridor",                ("utility_zone_carveout", "door_relocate")),
    ("dead end",                ("door_relocate",)),
    ("dead-end",                ("door_relocate",)),
    ("circulation",             ("door_relocate",)),
    # Outdoor / windows
    ("balcony",                 ("balcony_add", "balcony_remove")),
    ("window",                  ("window_resize",)),
    ("natural light",           ("window_resize", "balcony_add")),
    ("daylight",                ("window_resize", "balcony_add")),
    # Door
    ("door swing",              ("door_relocate",)),
    ("door blocks",             ("door_relocate",)),
)

# Legacy substring-match table (kept for backward-compat in case spec calls
# for a direct check_id pattern down the line; current code uses the
# (DIMENSION_TWEAK_MAP, WHY_IT_MATTERS_KEYWORDS) pair).
PROBLEM_CHECK_TWEAK_PATTERNS: Final[tuple[tuple[str, tuple[TweakCategory, ...]], ...]] = (
    # Retained for documentation; lookup_tweak_categories_for_check uses the
    # dimension+keyword approach below.
)


# ============================================================
# § 5 — Cost-impact heuristic ranges per category (Phase γ)
# ============================================================
# Per spec § 3 Phase γ — cost impact computation. v1.0 uses HEURISTIC
# ranges grounded in Chennai 2026 rates from C17's RateProvider
# pattern. Range = (low_INR, mid_INR, high_INR, uncertainty_pct).
# Negative midpoints mean SAVINGS. v1.x will swap heuristic for live
# RateProvider per B-C3B-COST-CALIBRATION (filed implicitly via
# the v1.0 LOCK-mandatory backlog).

TWEAK_CATEGORY_COST_RANGE_INR: Final[dict[TweakCategory, tuple[float, float, float, float]]] = {
    # (low, mid, high, uncertainty_pct)
    "finish_upgrade":          (15_000.0,    40_000.0,    80_000.0,   30.0),
    "finish_downgrade":        (-50_000.0,  -25_000.0,   -10_000.0,   30.0),
    "door_relocate":           (5_000.0,     12_000.0,    25_000.0,   25.0),
    "window_resize":           (8_000.0,     18_000.0,    35_000.0,   25.0),
    "balcony_add":             (60_000.0,   120_000.0,   250_000.0,   30.0),
    "balcony_remove":          (-30_000.0,  -15_000.0,   -5_000.0,    35.0),
    "storage_add":             (15_000.0,    35_000.0,    70_000.0,   30.0),
    "utility_zone_carveout":   (20_000.0,    50_000.0,   100_000.0,   30.0),
    "room_swap":               (5_000.0,     20_000.0,    50_000.0,   40.0),
    "room_resize":             (25_000.0,    75_000.0,   200_000.0,   35.0),
    "pooja_relocate":          (15_000.0,    35_000.0,    75_000.0,   30.0),
    "kitchen_reorient":        (80_000.0,   175_000.0,   400_000.0,   30.0),
    "wet_zone_restage":        (120_000.0,  280_000.0,   600_000.0,   35.0),
}


# ============================================================
# § 6 — Space-impact heuristic ranges per category (sqft)
# ============================================================
# total_sqft_delta absolute value per spec § 6: ≤ 150 sqft per tweak.

TWEAK_CATEGORY_SPACE_DELTA_SQFT: Final[dict[TweakCategory, float]] = {
    "finish_upgrade":          0.0,
    "finish_downgrade":        0.0,
    "door_relocate":           0.0,
    "window_resize":           0.0,
    "balcony_add":             -30.0,    # interior shrinks (carved from inside)
    "balcony_remove":          30.0,      # interior gains back
    "storage_add":             -20.0,    # carves from a room
    "utility_zone_carveout":   -25.0,    # carves from corridor
    "room_swap":               0.0,       # net zero
    "room_resize":             0.0,       # default neutral (specific instance may differ)
    "pooja_relocate":          0.0,
    "kitchen_reorient":        0.0,
    "wet_zone_restage":        0.0,
}


# ============================================================
# § 7 — Comfort-impact heuristic mapping per category
# ============================================================

from ..schema import ComfortDimension, ComfortDirection, ComfortMagnitude

# (dimensions_affected_tuple, direction, magnitude)
# Direction is the typical/expected direction; specific instances
# may invert (e.g., balcony_remove on a hot west wall improves
# noise_isolation but worsens outdoor_connection — picked here as
# the dominant effect).

TWEAK_CATEGORY_COMFORT_PROFILE: Final[
    dict[TweakCategory,
         tuple[tuple[ComfortDimension, ...], ComfortDirection, ComfortMagnitude]]
] = {
    "finish_upgrade":          (("storage_capacity",), "improves", "small"),
    "finish_downgrade":        (("storage_capacity",), "mixed", "small"),
    "door_relocate":           (("circulation_efficiency",), "improves", "small"),
    "window_resize":           (("natural_light",), "improves", "moderate"),
    "balcony_add":             (("cross_ventilation", "natural_light", "outdoor_connection"), "improves", "moderate"),
    "balcony_remove":          (("noise_isolation",), "improves", "small"),
    "storage_add":             (("storage_capacity",), "improves", "moderate"),
    "utility_zone_carveout":   (("storage_capacity",), "improves", "small"),
    "room_swap":               (("circulation_efficiency", "privacy"), "improves", "moderate"),
    "room_resize":             (("accessibility",), "mixed", "moderate"),
    "pooja_relocate":          (("vastu_alignment_opt_in",), "improves", "moderate"),
    "kitchen_reorient":        (("cross_ventilation", "natural_light"), "improves", "significant"),
    "wet_zone_restage":        (("noise_isolation", "privacy"), "improves", "moderate"),
}


# ============================================================
# § 8 — Helpers
# ============================================================

def lookup_tweak_categories_for_check(check_or_id) -> tuple[TweakCategory, ...]:
    """Given a ProblemCheck (preferred) or check_id string, return
    candidate tweak categories.

    Resolution order:
      1. If a ProblemCheck is passed, use dimension_id → DIMENSION_TWEAK_MAP.
         Then refine using why_it_matters keywords (WHY_IT_MATTERS_KEYWORDS).
         Returns the INTERSECTION (dimension candidates AND keyword
         candidates) when both fire; falls back to dimension's defaults
         when no keyword matches.
      2. If only a string is passed, treat as legacy substring matching
         against PROBLEM_CHECK_TWEAK_PATTERNS (legacy; returns empty
         for new-style P{dim}.{idx} ids).

    Returns empty tuple if no match.
    """
    # Path 1: ProblemCheck object
    if hasattr(check_or_id, "dimension_id") and hasattr(check_or_id, "why_it_matters"):
        check = check_or_id
        dim_candidates = DIMENSION_TWEAK_MAP.get(check.dimension_id, ())
        if not dim_candidates:
            return ()
        # Keyword refinement
        wim_lower = (check.why_it_matters or "").lower()
        keyword_candidates: set[TweakCategory] = set()
        for keyword, cats in WHY_IT_MATTERS_KEYWORDS:
            if keyword in wim_lower:
                keyword_candidates.update(cats)
        # Intersection
        if keyword_candidates:
            refined = tuple(
                c for c in dim_candidates if c in keyword_candidates
            )
            if refined:
                return refined
            # Keywords matched a different category than dimension
            # suggested; trust dimension (most specific)
        return dim_candidates

    # Path 2: legacy string-based matching (unused in v1.0; kept for tests)
    check_id = check_or_id
    if not check_id:
        return ()
    lowered = check_id.lower()
    matches: list[TweakCategory] = []
    for prefix, categories in PROBLEM_CHECK_TWEAK_PATTERNS:
        if prefix in lowered:
            for cat in categories:
                if cat not in matches:
                    matches.append(cat)
    return tuple(matches)


def lex_asc_components(components: tuple[DownstreamComponent, ...]) -> tuple[DownstreamComponent, ...]:
    """Return lex-ASC sorted copy of components for SubsetRerunRequest emit (R6)."""
    return tuple(sorted(components))


def lex_asc_impacts(impacts: tuple[DownstreamImpact, ...]) -> tuple[DownstreamImpact, ...]:
    """Return lex-ASC sorted copy of impacts for SubsetRerunRequest emit (R6)."""
    return tuple(sorted(impacts))


__all__ = [
    "TWEAK_CATEGORY_DEFAULT_SEVERITY",
    "TWEAK_CATEGORY_IMPACT_TABLE",
    "TWEAK_CATEGORY_COMPONENTS_TO_RERUN",
    "TWEAK_CATEGORY_COST_RANGE_INR",
    "TWEAK_CATEGORY_SPACE_DELTA_SQFT",
    "TWEAK_CATEGORY_COMFORT_PROFILE",
    "PROBLEM_CHECK_TWEAK_PATTERNS",
    "lookup_tweak_categories_for_check",
    "lex_asc_components",
    "lex_asc_impacts",
]
