"""
C3b — Post-Layout Trade-off Negotiation — versioning & thresholds
==================================================================

Spec: C3b v0.4.LOCKED (S50). Build session: S52.

This module pins:
  - Component identity (C3B_VERSION, C3B_SESSION_SCHEMA_VERSION, etc.)
  - Expected upstream versions (per spec § 5)
  - Hard ceilings (per spec § 6)
  - R-invariant thresholds (R-NEW thresholds for severity, regression, etc.)
  - R2 banned-phrase additions specific to C3b (per spec § 7.5)
  - Wire-format constants for canonical hashing (R6 inheritance)

Per spec § 5, schema version bumped 1 → 2 in v0.2 (ADDITIVE, MINOR per
R9 inheritance) to add SubsetRerunRequest.downstream_impact_set,
TopologyInvarianceResult, CompatibilityAssertion, MutationEnvelope.

v0.4 is the LOCK candidate (per spec § 0). Schema unchanged from v0.2.

Rule 11 self-analysis:
  1. EXPECTED_C* versions pin the implementation surface we assume.
     If an upstream component bumps and breaks compatibility, the
     UpstreamSchemaDriftError fires at Phase α — caught early, not
     silently propagated.
  2. ITERATION_CAP_HARD_CEILING > ITERATION_CAP_DEFAULT by 2; that's
     intentional headroom. Users can extend; the hard ceiling is the
     line where Phase ε forces finalization (per spec § 3 Phase ε
     step 4).
  3. MAX_REPRESENT_COUNT=2 is the don't-re-suggest-rejected-tweak
     ceiling. Below 2 is too aggressive (rejecting a tweak in turn 1
     shouldn't bury it forever). Above 2 is nag territory.
  4. PARETO_DIVERSITY_FLOOR_* are the applicability floors. If layouts
     are too similar, C3b refuses to iterate — § 1.4 enforced at
     Phase α.
"""
from __future__ import annotations

from typing import Final


# ============================================================
# § 0 — Component identity
# ============================================================

C3B_VERSION:                Final[str] = "v0.7.LOCKED"
C3B_SESSION_SCHEMA_VERSION: Final[int] = 5
C3B_IDENTITY_GENERATION:    Final[int] = 1

COMPONENT_NAME: Final[str] = "c3b_post_layout_tradeoff_negotiation"


# ============================================================
# § 1 — Expected upstream versions (spec § 5)
# ============================================================
# v0.5 amendment A1: replaces exact-equality pin with semantic
# compatibility (min-version-with-known-incompatibles). EXPECTED_*
# values kept as aliases for backward-compat; runtime check uses MIN_*.

EXPECTED_C15_VERSION: Final[str] = "v1.0.LOCKED"
EXPECTED_C16_VERSION: Final[str] = "v1.2.LOCKED"   # spec v1.2; runtime v0.5
EXPECTED_C7_VERSION:  Final[str] = "v0.8.LOCKED"
EXPECTED_C10_VERSION: Final[str] = "v1.0.LOCKED"
EXPECTED_C12_VERSION: Final[str] = "v1.0.LOCKED"
EXPECTED_C13_VERSION: Final[str] = "v1.0.LOCKED"
EXPECTED_C4_VERSION:  Final[str] = "v1.0.LOCKED"
EXPECTED_C3A_VERSION: Final[str] = "v0.2.1.LOCKED"

# v0.5 A1 — minimum acceptable upstream versions (lex compare via
# _parse_version helper). C3b accepts observed >= min_version.
MIN_C15_VERSION: Final[str] = "v1.0.LOCKED"
MIN_C16_VERSION: Final[str] = "v1.2.LOCKED"
MIN_C7_VERSION:  Final[str] = "v0.8.LOCKED"
MIN_C10_VERSION: Final[str] = "v1.0.LOCKED"
MIN_C12_VERSION: Final[str] = "v1.0.LOCKED"
MIN_C13_VERSION: Final[str] = "v1.0.LOCKED"
MIN_C4_VERSION:  Final[str] = "v1.0.LOCKED"
MIN_C3A_VERSION: Final[str] = "v0.2.1.LOCKED"

# Versions explicitly known to be incompatible despite passing the min
# check. Placeholder tuple for v1.0; populated as upstreams discover
# regressions. Format: tuple of (component_name, version_string) pairs.
KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS: Final[tuple[tuple[str, str], ...]] = ()


# ============================================================
# § 2 — Jurisdiction & domain scope (spec § 5)
# ============================================================

SUPPORTED_JURISDICTIONS: Final[frozenset[str]] = frozenset({"tn_cdbr_2019"})
SUPPORTED_DOMAIN_SCOPES: Final[frozenset[str]] = frozenset({"residential_v1"})


# ============================================================
# § 3 — Iteration & tweak ceilings (spec § 5 + § 6)
# ============================================================
# v0.5 amendment A8: ITERATION_CAP_DEFAULT lowered from 5 → 3 to address
# decision-fatigue concerns. Hard ceiling stays 7. Callers wanting more
# headroom must explicitly override via C3bRuntimeConfig.iteration_cap.

ITERATION_CAP_DEFAULT:      Final[int] = 3
ITERATION_CAP_HARD_CEILING: Final[int] = 7
MAX_TWEAKS_PER_LAYOUT:      Final[int] = 6
TWEAKS_PER_LAYOUT_HARD_CEILING: Final[int] = 8
MAX_REPRESENT_COUNT:        Final[int] = 2
SESSION_HISTORY_HARD_CEILING: Final[int] = 50

# v0.5 A2 — periodic full-coherence recheck threshold (MEDIUM tweaks
# applied between full upstream-stack reruns).
FULL_RECOMPUTE_THRESHOLD_DEFAULT: Final[int] = 3

# v0.5 A5 — per-dimension numeric-score regression threshold. A
# dimension degrading by ≥ this pct in post vs pre is flagged.
DIMENSION_DEGRADATION_THRESHOLD_PCT: Final[float] = 15.0

# v0.6 B3 — graded topology divergence thresholds. When
# topology_classification_change=True AND topology_divergence_score
# is populated:
#   score < MEDIUM_CAP  → demote to MEDIUM (low-risk perturbation)
#   score >= HEAVY_FLOOR → stay HEAVY
#   in between          → stay HEAVY (conservative default)
# When score is None, falls back to v0.5 boolean-only behavior.
TOPOLOGY_DIVERGENCE_MEDIUM_CAP: Final[float] = 0.3
TOPOLOGY_DIVERGENCE_HEAVY_FLOOR: Final[float] = 0.7

# Layout count is fixed (Cost Efficient / Everyday Living / Premium Design)
EXPECTED_LAYOUT_COUNT: Final[int] = 3


# ============================================================
# § 4 — Tweak impact magnitude ceilings (spec § 6)
# ============================================================

# A tweak whose cost impact exceeds this is treated as brief-level
# work, not a layout tweak; force MutationEnvelope kick-back to C3a.
TWEAK_COST_IMPACT_CEILING_INR: Final[float] = 20_00_000.0   # ₹20 lakh

# Same rationale for space impact. ±150 sqft is the layout-level boundary.
TWEAK_SPACE_IMPACT_CEILING_SQFT: Final[float] = 150.0


# ============================================================
# § 5 — Pareto-diversity floor for applicability (spec § 6 + § 1.4)
# ============================================================

# Layouts must differ by AT LEAST ONE of these floors to be
# considered iterable by C3b. If all 3 layouts are tighter than every
# floor, C3b refuses (collapse → "abandoned_no_tweaks" with advisory).
PARETO_DIVERSITY_FLOOR_SQFT_PCT:        Final[float] = 10.0
PARETO_DIVERSITY_FLOOR_COST_PCT:        Final[float] = 15.0
PARETO_DIVERSITY_FLOOR_TOPOLOGY_COUNT:  Final[int]   = 3


# ============================================================
# § 6 — Severity computation thresholds (spec § 3 Phase β step 4.2)
# ============================================================

# Phase β step 4.2 — context-aware severity adjustment thresholds.
#
# Per spec, each factor either crosses threshold (promotes severity) or
# does not. Two-or-more factors promote MEDIUM → HEAVY directly.

# Distance from a wall to a column at which we still consider the
# wall "near load-bearing" for severity purposes. Calibrated against
# C7 default grid bay sizes (3-4 m spacing typical).
LOAD_BEARING_PROXIMITY_MM: Final[float] = 300.0

# A subset rerun completing under this is "fast" — eligible for LIGHT
# in marginal cases. Over this is MEDIUM by default.
SUBSET_RERUN_FAST_SECONDS_CEILING: Final[float] = 1.0

# A subset rerun over this is reclassified HEAVY (per spec § 2.4.1:
# "> 10s requires reclassification").
SUBSET_RERUN_HEAVY_SECONDS_FLOOR: Final[float] = 10.0


# ============================================================
# § 7 — R14 regression detection threshold (spec § 7.2)
# ============================================================

# Minimum increase in critical-tier ProblemReport checks to trigger
# regression_detected. Per backlog item B-C3B-REGRESSION-DETECTION:
# post-launch calibration may move this. v1.0 ships at 1 (any new
# critical issue = regression).
REGRESSION_CRITICAL_INCREASE_THRESHOLD: Final[int] = 1


# ============================================================
# § 8 — R6 / R7 / R8 signature canonicalization constants
# ============================================================

# Canonical hash digest length (sha256 hex)
SIGNATURE_HEX_LENGTH: Final[int] = 64

# Banker's-rounding tolerance for float comparisons in canonical
# hashing (R6 byte-equal replay)
EPSILON_AMOUNT_INR: Final[float] = 0.01

# Number of decimal places we round floats to when canonicalizing for
# signature hashing. Matches C17 convention.
CANONICAL_FLOAT_DECIMALS: Final[int] = 6


# ============================================================
# § 9 — Q3 Level B logging discipline (inherited from C3a v0.2.1)
# ============================================================

# Every SessionTurn must record the full TweakOptionSet the user saw
# (presented_tweaks), not just the chosen one. This constant gates the
# audit trail completeness check.
Q3_LEVEL_B_LOGGING_REQUIRED: Final[bool] = True


# ============================================================
# § 10 — R2 banned-phrase additions (spec § 7.5)
# ============================================================

# Phrases banned in C3b user-facing text BEYOND the C17-inherited list.
# Specific to C3b because tweak/option language has its own failure
# modes ("system decided", "auto-fix", etc.) per critique pt 5
# (MutationEnvelope) and Principle 3.
#
# These are checked by advisory_lint.lint_advisory_text alongside the
# C17 base list.

C3B_BANNED_SUBSTRINGS: Final[tuple[str, ...]] = (
    # Coercion / no-agency phrasings
    "the system decided",
    "system decided",
    "we'll auto-fix",
    "we will auto-fix",
    "auto-fix",
    "you have to",
    "you must",
    "you need to",
    "you should",
    "you ought to",
    # Authoritative ranking ("recommend" structurally OK via flag enum,
    # but as user-facing text it carries verdict weight)
    "perfect tweak",
    "best tweak",
    "best choice",
    "right choice",
    "wrong choice",
    "better option",
    "worse option",
    # Accusatory / failure framing
    "tweak failed",
    "rejected",
    "you rejected",
    # Engine-centric language (Principle 1 enforcement)
    "the engine determined",
    "we calculated that",
    "algorithm decided",
)

# Replacement guidance — surfaced in lint error messages so the
# violator knows what to use instead.
C3B_REPLACEMENT_HINTS: Final[dict[str, str]] = {
    "should":            "could",
    "must":              "may want to",
    "have to":           "could",
    "rejected":          "couldn't be surfaced as a tweak",
    "tweak failed":      "tweak couldn't apply",
    "best":              "an option",
    "perfect":           "well-suited",
    "wrong":             "different from",
}


# ============================================================
# § 9 — Version parsing (v0.5 A1)
# ============================================================

def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string of the form 'v<major>.<minor>[.<patch>].<status>'
    into a tuple of integers for lex comparison.

    Recognizes:
      v1.0.LOCKED         → (1, 0, 0, _STATUS_LOCKED)
      v1.2.LOCKED         → (1, 2, 0, _STATUS_LOCKED)
      v0.2.1.LOCKED       → (0, 2, 1, _STATUS_LOCKED)
      v1.0.PROPOSED       → (1, 0, 0, _STATUS_PROPOSED)
      v1.0                → (1, 0, 0, _STATUS_UNKNOWN)

    Status ordering: PROPOSED < LOCKED.LOCKED is treated as a higher
    "patch level" than PROPOSED so that v1.0.LOCKED > v1.0.PROPOSED
    even when numeric parts are equal.

    Returns a tuple suitable for direct lex comparison.
    """
    _STATUS_RANK = {"PROPOSED": 0, "LOCKED": 1}
    _STATUS_UNKNOWN = -1

    if not v:
        return ()
    s = v.strip()
    if s.startswith("v") or s.startswith("V"):
        s = s[1:]
    parts = s.split(".")
    if not parts:
        return ()

    # Last component MAY be a status string
    status_token = parts[-1].upper()
    if status_token in _STATUS_RANK:
        numeric_parts = parts[:-1]
        status_rank = _STATUS_RANK[status_token]
    else:
        numeric_parts = parts
        status_rank = _STATUS_UNKNOWN

    nums: list[int] = []
    for p in numeric_parts:
        try:
            nums.append(int(p))
        except ValueError:
            return ()  # malformed
    # Pad to 3 numeric slots so v1.0.LOCKED and v1.0.0.LOCKED compare equal
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums) + (status_rank,)


def version_at_or_above(observed: str, minimum: str) -> bool:
    """Return True iff observed version >= minimum version.

    v0.5 A1 — replaces strict-equality upstream pinning with semantic
    compatibility. Used by Phase α check_upstream_versions.

    Returns False on parse failure (defensive — caller treats malformed
    versions as drift).
    """
    obs_parsed = _parse_version(observed)
    min_parsed = _parse_version(minimum)
    if not obs_parsed or not min_parsed:
        return False
    return obs_parsed >= min_parsed


__all__ = [
    # Identity
    "C3B_VERSION", "C3B_SESSION_SCHEMA_VERSION", "C3B_IDENTITY_GENERATION",
    "COMPONENT_NAME",
    # Expected upstreams (legacy aliases)
    "EXPECTED_C15_VERSION", "EXPECTED_C16_VERSION", "EXPECTED_C7_VERSION",
    "EXPECTED_C10_VERSION", "EXPECTED_C12_VERSION", "EXPECTED_C13_VERSION",
    "EXPECTED_C4_VERSION", "EXPECTED_C3A_VERSION",
    # Minimum versions (v0.5 A1)
    "MIN_C15_VERSION", "MIN_C16_VERSION", "MIN_C7_VERSION", "MIN_C10_VERSION",
    "MIN_C12_VERSION", "MIN_C13_VERSION", "MIN_C4_VERSION", "MIN_C3A_VERSION",
    "KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS",
    "_parse_version", "version_at_or_above",
    # Scope
    "SUPPORTED_JURISDICTIONS", "SUPPORTED_DOMAIN_SCOPES",
    # Ceilings
    "ITERATION_CAP_DEFAULT", "ITERATION_CAP_HARD_CEILING",
    "MAX_TWEAKS_PER_LAYOUT", "TWEAKS_PER_LAYOUT_HARD_CEILING",
    "MAX_REPRESENT_COUNT", "SESSION_HISTORY_HARD_CEILING",
    "EXPECTED_LAYOUT_COUNT",
    "TWEAK_COST_IMPACT_CEILING_INR", "TWEAK_SPACE_IMPACT_CEILING_SQFT",
    # v0.5 new ceilings
    "FULL_RECOMPUTE_THRESHOLD_DEFAULT",
    "DIMENSION_DEGRADATION_THRESHOLD_PCT",
    # v0.6 B3 — graded topology divergence thresholds
    "TOPOLOGY_DIVERGENCE_MEDIUM_CAP",
    "TOPOLOGY_DIVERGENCE_HEAVY_FLOOR",
    # Pareto floors
    "PARETO_DIVERSITY_FLOOR_SQFT_PCT", "PARETO_DIVERSITY_FLOOR_COST_PCT",
    "PARETO_DIVERSITY_FLOOR_TOPOLOGY_COUNT",
    # Severity thresholds
    "LOAD_BEARING_PROXIMITY_MM",
    "SUBSET_RERUN_FAST_SECONDS_CEILING",
    "SUBSET_RERUN_HEAVY_SECONDS_FLOOR",
    # Regression
    "REGRESSION_CRITICAL_INCREASE_THRESHOLD",
    # Signature
    "SIGNATURE_HEX_LENGTH", "EPSILON_AMOUNT_INR", "CANONICAL_FLOAT_DECIMALS",
    # Logging
    "Q3_LEVEL_B_LOGGING_REQUIRED",
    # R2 banned phrases
    "C3B_BANNED_SUBSTRINGS", "C3B_REPLACEMENT_HINTS",
]
