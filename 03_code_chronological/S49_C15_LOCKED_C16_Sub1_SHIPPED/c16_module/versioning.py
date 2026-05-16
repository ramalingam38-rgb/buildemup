"""
C16 — Dual-Drawing Renderer — versioning constants
=====================================================

Per C16 v0.5 LOCKED spec (S47), composed of:
    spec_C16_v0_1_PROPOSED.md     (foundational v0.1)
    spec_C16_v0_2_PROPOSED_DELTA  (10 amendments — walk #1)
    spec_C16_v0_3_PROPOSED_DELTA  (8 amendments — walk #2)
    spec_C16_v0_4_PROPOSED_DELTA  (12 amendments — walk #3 + Item 13 META)
    spec_C16_v0_5_PROPOSED_DELTA  (6 amendments — walk #4)

These constants are the IMMUTABLE knobs that every downstream module
(contracts, schema, cache_keys, orchestrator, phases) reads from.
Changes here are governance-gated by the C13/C14/C15 LOCK convention.

Pinned at Sub-1 (S49):
    C16_VERSION                     : str   = "v0.5.LOCKED"
    C16_DRAWING_SCHEMA_VERSION      : int   = 12
    C16_IDENTITY_GENERATION         : int   = 1
    SEVERITY_TABLE_VERSION (n/a)            — C16 has no severity table

Hard ceilings: per v0.5 A4 (R31a) — module-level, NOT overridable.
Epsilon policy:  per v0.4 A11 + v0.5 A3 (R34, R34e) — canonical tolerances.
"""

from __future__ import annotations

from typing import Final, FrozenSet

# ============================================================
# § 1 — VERSION TRIPLE (Inv R16)
# ============================================================

C16_VERSION: Final[str] = "v0.5.LOCKED"
"""Component version. Updated at every LOCK milestone.

Cache-relevant. Any v0.5 → v0.6 → v1.0 bump invalidates all C16 caches.
"""

C16_DRAWING_SCHEMA_VERSION: Final[int] = 12
"""Drawing-schema version. Cumulative bumps across amendments:

    v0.1 baseline                                              :  1
    v0.2 A3 (shared FloorGeometry)                             :  2
    v0.2 A4 (SubmissionReadiness — superseded by v0.4 A5)      :  3
    v0.2 A5 (AuthorityKind + AttestedValue)                    :  3 (same bump)
    v0.2 A6 (RenderingConfig fleshed out)                      :  3 (same bump)
    v0.2 A7 (Stable IDs + ElementKind taxonomy)                :  4
    v0.3 A3 (ElementIdentity two-tier)                         :  5
    v0.3 A4 (LocalBuildingFrame + GeospatialReference)         :  6
    v0.4 A5 (LegalCompleteness ⊥ ReadabilityStatus split)      :  7
    v0.4 A9 (presentation_signature)                           :  8
    v0.4 A10 (identity_generation field)                       :  9
    v0.5 A2 (schema_descriptor_digest)                         : 10
    v0.5 A4 (declared_domain_scope on JurisdictionProfile)     : 11
    v0.5 A5 (OrientationLock optional metadata)                : 12

Inv R9: adding fields → MINOR bump; removing/renaming → MAJOR bump.
"""

C16_IDENTITY_GENERATION: Final[int] = 1
"""Identity-generation scope per v0.4 A10 (Inv R33).

Bumps ONLY on coordinate-system migrations, geometry normalization
fixes, or element-kind taxonomy MAJOR changes. Does NOT bump on
schema MINOR additions.

v0.5 LOCK starts at generation 1. R33a: any future bump requires
MAJOR C16_DRAWING_SCHEMA_VERSION bump + release-note "breaking change".
"""

# ============================================================
# § 2 — EXPECTED UPSTREAM VERSIONS
# ============================================================

EXPECTED_C7_VERSION:  Final[str] = "v0.8"   # structural grid
EXPECTED_C9_VERSION:  Final[str] = "v1.0"   # room sizer
EXPECTED_C10_VERSION: Final[str] = "v1.0"   # wet-zone stack alignment
EXPECTED_C12_VERSION: Final[str] = "v1.0"   # vertical alignment engine
EXPECTED_C13_VERSION: Final[str] = "v1.0"   # door placement
EXPECTED_C14_VERSION: Final[str] = "v1.0"   # connection-graph quality
EXPECTED_C15_VERSION: Final[str] = "v1.0"   # layout problem finder (LOCKED at S49)

# ============================================================
# § 3 — JURISDICTION + DOMAIN SCOPE (v0.5 A4 — R31b)
# ============================================================

SUPPORTED_JURISDICTIONS: Final[FrozenSet[str]] = frozenset({"tn_cdbr_2019"})
"""v1 jurisdictions. B-C16-MULTI-JURISDICTION-PROFILES expands post-LOCK."""

SUPPORTED_DOMAIN_SCOPES: Final[FrozenSet[str]] = frozenset({
    "residential_v1",
    "small_commercial_v1",
    "mixed_use_v1",
})
"""v0.5 A4 — `declared_domain_scope` enum values. Larger-scope domains
(township, campus, infrastructure) require a different C16 variant
(e.g. C16-CAMPUS), NOT a ceiling override."""

# ============================================================
# § 4 — HARD CEILINGS (v0.5 A4 — R31a)
# ============================================================
#
# SCOPE: BuildemUp residential and small-commercial v1.
# Plot ≤ 1 km × 1 km; building ≤ 500 m × 500 m × 500 m height.
#
# These are module-level constants. NOT overridable via RenderingConfig
# (v0.4 A7 was relaxed → v0.5 A4 re-tightened).
#
# For larger domains:
#   (a) Use a DIFFERENT jurisdiction profile that declares its scope,
#   (b) Bump C16_VERSION to a domain-specific variant,
#   (c) DO NOT attempt to override these ceilings.

HARD_CEILING_PLOT_X_MM:        Final[int] = 1_000_000   # 1 km — township scale
HARD_CEILING_PLOT_Y_MM:        Final[int] = 1_000_000
HARD_CEILING_BUILDING_X_MM:    Final[int] =   500_000   # 500 m — largest commercial complex
HARD_CEILING_BUILDING_Y_MM:    Final[int] =   500_000
HARD_CEILING_BUILDING_Z_MAX_MM: Final[int] =  500_000   # 500 m — above skyscraper limit
HARD_CEILING_BUILDING_Z_MIN_MM: Final[int] =  -50_000   # 50 m basement depth

# LocalBuildingFrame bounds per v0.3 A4 (typical residential building dims)
HARD_CEILING_LOCAL_FRAME_X_MAX_MM: Final[int] =  50_000
HARD_CEILING_LOCAL_FRAME_X_MIN_MM: Final[int] = -50_000
HARD_CEILING_LOCAL_FRAME_Y_MAX_MM: Final[int] =  50_000
HARD_CEILING_LOCAL_FRAME_Y_MIN_MM: Final[int] = -50_000

# ============================================================
# § 5 — EPSILON POLICY (v0.4 A11 + v0.5 A3 — R34, R34e)
# ============================================================

EPSILON_COORD_MM: Final[int] = 1
"""Coordinate snapping tolerance. v0.2 A2 set 1 mm. R7a banker's
rounding to integer mm; sub-mm precision NEVER appears in output."""

EPSILON_RATIO: Final[float] = 1e-4
"""Ratio tolerance — e.g. plot_coverage_pct cross-check vs C2 FAR."""

EPSILON_ANGLE_DEG: Final[float] = 1e-6
"""Angle comparison tolerance — used by R29d (OrientationLock
plausibility) and rotation-from-plot-north cross-checks.

Tight enough to catch real disagreements; loose enough to absorb
banker's-rounding artifacts from upstream geometry computations."""

# ============================================================
# § 6 — COORDINATE FRAME CONVENTIONS (v0.2 A2 + v0.3 A4)
# ============================================================
#
# These are documented in the spec § 1.0; pinned here as constants so
# downstream renderers can read them programmatically.

PLOT_FRAME_ORIGIN_DESCRIPTION: Final[str] = (
    "South-West corner of site bounding box; "
    "+X = East, +Y = North, +Z = Up (right-handed)."
)

LOCAL_BUILDING_FRAME_ORIGIN_DESCRIPTION: Final[str] = (
    "South-West corner of BUILDING footprint; "
    "+X chosen by deterministic orientation hierarchy (v0.4 A4 — R29); "
    "+Y by right-hand rule from +X; +Z = Up."
)

# ============================================================
# § 7 — ORIENTATION HIERARCHY (v0.4 A4 — R29b)
# ============================================================

ORIENTATION_BASIS_VALUES: Final[FrozenSet[str]] = frozenset({
    "explicit_hint",       # JurisdictionProfile or C4 hint
    "primary_entrance",    # main entry wall (C13 is_main_entry=True)
    "longest_wall",        # longest WALL_EXTERNAL, lex-ASC tiebreak
    "lex_fallback",        # degenerate fallback (defensive)
})
"""Valid values for GeospatialReference.orientation_basis per R29b.
Recorded in the bundle so consumers know WHICH hierarchy step fired."""

# ============================================================
# § 8 — REPR
# ============================================================

def version_triple() -> tuple[str, int, int]:
    """The (Inv R16) provenance triple, programmatically accessible."""
    return (C16_VERSION, C16_DRAWING_SCHEMA_VERSION, C16_IDENTITY_GENERATION)


def version_summary() -> str:
    """Human-readable summary for logging and provenance records."""
    return (
        f"C16 {C16_VERSION} "
        f"(drawing_schema={C16_DRAWING_SCHEMA_VERSION}, "
        f"identity_gen={C16_IDENTITY_GENERATION})"
    )
