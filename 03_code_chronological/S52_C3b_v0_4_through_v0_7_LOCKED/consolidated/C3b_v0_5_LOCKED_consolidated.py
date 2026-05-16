"""
================================================================================
C3b v0.5 LOCKED — Post-Layout Trade-off Negotiation (CONSOLIDATED SOURCE)
================================================================================

This is the SINGLE-FILE consolidated source for C3b, BuildEase Component 3b.
Generated from the modular source tree at:
    buildemup/components/c03b/

Spec:   C3b v0.5.LOCKED (S52 amendments under Ramalingam delegation)
Build:  S52 — full Phase α/β/γ/δ/ε/ζ + orchestrator + SQLite WAL +
              9 v0.5 amendments (A1–A9) + R17 + R18 invariants
Tests:  415 passing (3 skipped), 0 failed

v0.5 amendments integrated:
  A1 — Semantic compatibility contracts (min-version >=, not exact ==)
  A2 — Periodic full-coherence recheck (counter + threshold)
  A3 — Oscillation detection + advisory
  A4 — Strategic advisory hook (R17 protected — text excluded from canonical sig)
  A5 — Continuous dimension delta check (no-ops without C15 scores)
  A6 — Speculative preview text on MutationEnvelope
  A7 — Emotional layout heuristics (3 seeded scores on ComfortImpact)
  A8 — iteration_cap default lowered 5 → 3
  A9 — Archetype-diversity Pareto floor

New invariants:
  R17 — strategic_advisory_text MUST NOT affect canonical_replay_signature
  R18 — full-recompute counter MUST be 0 on terminal status

This file is provided for review / archival / portability. The CANONICAL
source remains the modular tree.

────────────────────────────────────────────────────────────────────────────────
Module assembly order (dependency-DAG topological):

  versioning      → constants, MIN_C* versions, version_at_or_above
  config          → C3bRuntimeConfig (strategic_mode, full_recompute_threshold)
  errors          → 2-tier (LocalTradeoffError / PerTweakError) hierarchy
  advisory_lint   → R2 banned-phrase enforcement
  contracts       → C3bInputBundle + upstream-stub re-exports
  schema          → 18+ dataclasses with R-invariants (R17/R18 enforced)
  cache_keys      → R6/R7/R8 + R17-aware canonical signatures
  phases.tables   → static lookup tables for Phase β
  phases.severity → R13 severity context computation
  phases.alpha    → canonicalization + applicability boundary (A1 + A9)
  phases.beta     → tweak generation per layout (A6 + A7)
  phases.gamma    → impact verification
  phases.delta    → presentation + signing
  phases.epsilon  → user-turn handling (A2 + A3 + A4 + A5 + R14/R15/R16/R18)
  phases.zeta     → resolution + handoff signing
  session_storage → SQLite WAL persistence (v0.5 schema_version=3)
  orchestrator    → start_session / apply_user_action / finalize

────────────────────────────────────────────────────────────────────────────────
Public API surface:

  from c03b_consolidated import (
      C3bInputBundle, C3bRuntimeConfig, DEFAULT_CONFIG,
      UserActionRequest, C3bSessionStorage,
      start_session, apply_user_action_orchestrated,
      complete_subset_rerun_orchestrated, finalize_session,
  )

NOTE: This consolidated file references buildemup.components.* paths.
The intent is REVIEW + DOCUMENTATION, not standalone execution.

────────────────────────────────────────────────────────────────────────────────
"""


# ══════════════════════════════════════════════════════════════════════════════
# § versioning                                                  
# ══════════════════════════════════════════════════════════════════════════════
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

C3B_VERSION:                Final[str] = "v0.5.LOCKED"
C3B_SESSION_SCHEMA_VERSION: Final[int] = 3
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





# ══════════════════════════════════════════════════════════════════════════════
# § config                                                      
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — runtime configuration
================================================================

Spec: C3b v0.5.LOCKED. Build session: S52.

The C3bRuntimeConfig threads strict_mode + jurisdiction context + any
per-session tuning knobs through the phase pipeline.

Per spec § 4 error tiers:
  STRICT mode → PerTweakError raises immediately
  WARN   mode → PerTweakError collects to a failure list, processing
                continues. LocalTradeoffError ALWAYS halts in either
                mode.

v0.5 additions:
  A2 — full_recompute_threshold (periodic coherence recheck)
  A4 — strategic_mode (advisory hook; R17-protected)
  A8 — iteration_cap default lowered 5 → 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, Literal, Optional

from .versioning import (
    FULL_RECOMPUTE_THRESHOLD_DEFAULT,
    ITERATION_CAP_DEFAULT,
    ITERATION_CAP_HARD_CEILING,
)


StrictMode = Literal["strict", "warn"]

# v0.5 A4 — strategic-mode literal. "off" means no strategic advisory text
# is populated. "advisory_only" means a registered provider may populate
# SessionTurn.strategic_advisory_text. R17 invariant: advisory text MUST
# NOT affect canonical_replay_signature regardless of mode.
StrategicMode = Literal["off", "advisory_only"]

# Provider receives kwargs (session, request) and returns advisory text
# or None. Implementations must be READ-ONLY against session state.
StrategicAdvisoryProvider = Callable[..., Optional[str]]


@dataclass(frozen=True)
class C3bRuntimeConfig:
    """Runtime configuration for a C3b session.

    Frozen so it participates cleanly in R6 byte-equal replay
    signature hashing (strict_mode is part of canonical_replay_signature
    inputs).

    R17: strategic_advisory_text content is excluded from
    canonical_replay_signature. Different providers can populate
    different text without changing the signature.
    """

    strict_mode: StrictMode = "strict"
    iteration_cap: int = ITERATION_CAP_DEFAULT
    enable_q3_level_b_logging: bool = True
    full_recompute_threshold: int = FULL_RECOMPUTE_THRESHOLD_DEFAULT
    strategic_mode: StrategicMode = "off"
    strategic_advisory_provider: Optional[StrategicAdvisoryProvider] = None

    def __post_init__(self) -> None:
        if self.strict_mode not in ("strict", "warn"):
            raise ValueError(
                f"C3bRuntimeConfig.strict_mode must be 'strict' or 'warn'; "
                f"got {self.strict_mode!r}"
            )
        if not (1 <= self.iteration_cap <= ITERATION_CAP_HARD_CEILING):
            raise ValueError(
                f"C3bRuntimeConfig.iteration_cap must be in [1, "
                f"{ITERATION_CAP_HARD_CEILING}]; got {self.iteration_cap}"
            )
        if not (1 <= self.full_recompute_threshold <= self.iteration_cap):
            raise ValueError(
                f"C3bRuntimeConfig.full_recompute_threshold must be in "
                f"[1, iteration_cap={self.iteration_cap}]; "
                f"got {self.full_recompute_threshold}"
            )
        if self.strategic_mode not in ("off", "advisory_only"):
            raise ValueError(
                f"C3bRuntimeConfig.strategic_mode must be 'off' or "
                f"'advisory_only'; got {self.strategic_mode!r}"
            )


DEFAULT_CONFIG: Final[C3bRuntimeConfig] = C3bRuntimeConfig()





# ══════════════════════════════════════════════════════════════════════════════
# § errors                                                      
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — error hierarchy
==========================================================

Spec: C3b v0.4.LOCKED § 4. Build session: S52.

Two-tier hierarchy mirrors C16/C17 LOCKED pattern:

    LocalTradeoffError              (always halts; affects whole session)
    │
    ├── UpstreamSchemaDriftError    (SelectionResult / ProblemReport drift)
    ├── C3bConfigurationError       (bad jurisdiction / iteration cap)
    ├── ApplicabilityBoundaryError  (Preview Mode, high_ambiguity, Pareto collapse)
    ├── SessionPersistenceError     (SQLite WAL write failure)
    ├── SubsetRerunOrchestrationError (orchestrator failed; session enters terminal state)
    └── TopologyInvarianceProbeError (v0.2 — Phase β step 4.2 couldn't determine prediction_basis)

    PerTweakError                   (STRICT raises / WARN collects)
    │
    ├── TweakGenerationError        (can't generate a candidate)
    ├── ImpactComputationError      (cost / space / comfort impact failed)
    ├── ConstraintViolationError    (apply would violate hard constraint)
    ├── RecommendationFlagAmbiguityError (can't classify suggested/optional/alternative)
    ├── DownstreamImpactSetMissingError  (v0.2 — empty downstream_impact_set on MEDIUM)
    └── CompatibilityAssertionFailedError (v0.2 — Phase ε apply found "conflicts" against prior tweak)

Rule 11 self-analysis:
  1. The split is *behavioral*, not *structural*: STRICT halts vs WARN
     collects routes by base class, not severity guess. Tests must
     verify the routing happens at orchestrator boundary, not deeper.
  2. UpstreamSchemaDriftError specifically fires when EXPECTED_C*
     versions don't match runtime — caught at Phase α, not later
     where the mismatch produces a baffling AttributeError.
  3. ApplicabilityBoundaryError is the § 1.4 exit ramp. The session
     enters "abandoned_no_tweaks" with an explicit advisory note
     explaining why — not a stack trace.
  4. SubsetRerunOrchestrationError is the only Local error that
     PRODUCES a TradeoffSession in a terminal state — the others
     prevent session creation entirely. Documented because that
     distinction matters at the orchestrator level.
"""
from __future__ import annotations

from typing import Optional


# ============================================================
# § 1 — Base classes
# ============================================================

class C3bError(Exception):
    """Root of all C3b-emitted errors. Useful for catch-all guard
    rails in tests and orchestration boundaries; not normally caught
    in business code."""


class LocalTradeoffError(C3bError):
    """LOCAL errors — affect the WHOLE session.

    Always halt. Independent of strict_mode. The session either:
      - never starts (constructor / Phase α refusal), OR
      - enters a terminal "abandoned_no_tweaks" / "kicked_back_to_c3a"
        state with explicit advisory."""

    def __init__(
        self,
        message:        str,
        *,
        session_id:     Optional[str] = None,
        phase:          Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.session_id = session_id
        self.phase = phase


class PerTweakError(C3bError):
    """PER-TWEAK errors — affect ONE tweak candidate only.

    STRICT mode: raised. WARN mode: collected to a failure list;
    the affected tweak is dropped from the option set, other tweaks
    proceed."""

    def __init__(
        self,
        message:         str,
        *,
        tweak_id:        Optional[str] = None,
        layout_id:       Optional[str] = None,
        reason:          Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.tweak_id = tweak_id
        self.layout_id = layout_id
        self.reason = reason


# ============================================================
# § 2 — LocalTradeoffError subclasses (spec § 4.1)
# ============================================================

class UpstreamSchemaDriftError(LocalTradeoffError):
    """Upstream component's schema doesn't match expected LOCKED
    version. E.g., SelectionResult v0.9 received but EXPECTED_C15_VERSION
    pins v1.0.LOCKED.

    Halts at Phase α before any tweak generation."""

    def __init__(
        self,
        message:           str,
        *,
        expected_version:  Optional[str] = None,
        observed_version:  Optional[str] = None,
        upstream:          Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="alpha")
        self.expected_version = expected_version
        self.observed_version = observed_version
        self.upstream = upstream


class C3bConfigurationError(LocalTradeoffError):
    """Bad jurisdiction, unsupported domain scope, or invalid
    iteration cap. Caught at C3bRuntimeConfig construction OR Phase α
    pre-flight."""

    def __init__(
        self,
        message:         str,
        *,
        offending_field: Optional[str] = None,
        offending_value: Optional[object] = None,
    ) -> None:
        super().__init__(message)
        self.offending_field = offending_field
        self.offending_value = offending_value


class ApplicabilityBoundaryError(LocalTradeoffError):
    """The input SelectionResult fails § 1.4 applicability boundary:
    Preview Mode unresolved, ProblemReport.overall_report_tier ==
    'high_ambiguity', or Pareto-front collapse below diversity floor.

    Does NOT halt error-style; instead produces a TradeoffSession
    with current_status='abandoned_no_tweaks' and an advisory note.
    The exception form here is used during construction guard rails
    in tests; the runtime path emits the terminal session."""

    def __init__(
        self,
        message:        str,
        *,
        boundary_kind:  Optional[str] = None,
        diagnostic:     Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="alpha")
        self.boundary_kind = boundary_kind  # "preview_mode" / "high_ambiguity" / "pareto_collapse"
        self.diagnostic = diagnostic


class SessionPersistenceError(LocalTradeoffError):
    """SQLite WAL write failed. Inherits S6 BriefStorage hardening
    pattern from C3a precedent."""

    def __init__(
        self,
        message:    str,
        *,
        operation:  Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.operation = operation  # "write" / "read" / "checkpoint"


class SubsetRerunOrchestrationError(LocalTradeoffError):
    """The external subset-rerun orchestrator (for MEDIUM tweaks) failed.
    Session enters terminal 'abandoned_no_tweaks' state with explicit
    advisory listing the failed components."""

    def __init__(
        self,
        message:                str,
        *,
        failed_components:      Optional[tuple[str, ...]] = None,
        rerun_request_id:       Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="epsilon")
        self.failed_components = failed_components or ()
        self.rerun_request_id = rerun_request_id


class TopologyInvarianceProbeError(LocalTradeoffError):
    """Phase β step 4.2 couldn't determine the
    TopologyInvarianceResult.prediction_basis confidently for a
    candidate tweak. SAFETY BIAS: the candidate is auto-classified
    HEAVY by default (removed from option set, MutationEnvelope
    generated for buffering).

    This subclasses LocalTradeoffError to flag the probe failure
    upstream of routing — but the SAFE outcome (auto-promote-to-HEAVY)
    is taken inside the catching code, not by raising. The exception
    form here is for unit-test reachability of the probe failure
    code path."""

    def __init__(
        self,
        message:           str,
        *,
        tweak_category:    Optional[str] = None,
        prediction_basis:  Optional[str] = None,
    ) -> None:
        super().__init__(message, phase="beta")
        self.tweak_category = tweak_category
        self.prediction_basis = prediction_basis


# ============================================================
# § 3 — PerTweakError subclasses (spec § 4.2)
# ============================================================

class TweakGenerationError(PerTweakError):
    """Can't generate a candidate for a ProblemReport check.
    E.g., a check is about cross-floor circulation but cross-floor
    tweaks are out-of-scope in v1.0 → the tweak isn't generated;
    the check is preserved in ProblemReport, NOT a hard error."""

    def __init__(
        self,
        message:                  str,
        *,
        problem_check_id:         Optional[str] = None,
        tweak_category_attempted: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.problem_check_id = problem_check_id
        self.tweak_category_attempted = tweak_category_attempted


class ImpactComputationError(PerTweakError):
    """Phase γ couldn't compute cost / space / comfort impact for a
    tweak. E.g., RateProvider lookup failed for a finish_upgrade
    material."""

    def __init__(
        self,
        message:     str,
        *,
        impact_dim:  Optional[str] = None,  # "cost" / "space" / "comfort"
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.impact_dim = impact_dim


class ConstraintViolationError(PerTweakError):
    """Applying this tweak would violate a hard constraint (NBC
    minimum room area, structural feasibility, etc.). The tweak is
    REMOVED from the option set BEFORE surfacing to the user.

    Spec § 4.2: this is a per-tweak filter, NOT a hard error stopping
    the session."""

    def __init__(
        self,
        message:         str,
        *,
        constraint:      Optional[str] = None,
        violated_value:  Optional[object] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.constraint = constraint
        self.violated_value = violated_value


class RecommendationFlagAmbiguityError(PerTweakError):
    """Phase γ can't unambiguously classify a tweak as
    suggested/optional/alternative."""


class DownstreamImpactSetMissingError(PerTweakError):
    """v0.2 (spec § 2.4.1): a MEDIUM tweak's
    SubsetRerunRequest.downstream_impact_set is empty. Hard error
    per the contract — empty impact set means we couldn't compute
    what to rerun, which means we can't safely apply."""


class CompatibilityAssertionFailedError(PerTweakError):
    """v0.2 (R15, spec § 7.3): Phase ε apply step found a
    CompatibilityAssertion.result == 'conflicts' against an
    already-applied tweak. STRICT halts the apply; WARN surfaces the
    conflict to the user with the 3-option resolution."""

    def __init__(
        self,
        message:                  str,
        *,
        conflicting_tweak_id:     Optional[str] = None,
        assertion_kind:           Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.conflicting_tweak_id = conflicting_tweak_id
        self.assertion_kind = assertion_kind


# ============================================================
# § 4 — Public surface
# ============================================================




# ══════════════════════════════════════════════════════════════════════════════
# § advisory_lint                                               
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — advisory-tone lint (R2)
==================================================================

Spec: C3b v0.4.LOCKED § 7.5 + § 7 R2. Build session: S52.

Every user-facing string in a TradeoffSession output MUST pass this
lint at emission time:

  - TweakOption.description
  - TweakOptionSet.overall_advisory_note
  - MutationEnvelope.why_not_a_tweak, suggested_pathway,
    estimated_pathway_effort, advisory_note
  - SubsetRerunRequest.rerun_anchor (informational text portion)
  - TopologyInvarianceResult.advisory_note
  - CompatibilityAssertion.advisory_note
  - ResolvedSelection.final_handoff_advisory
  - AdvisoryFlag.advisory_note
  - SessionTurn outcome advisories

The base list is INHERITED FROM C17 v0.3 R2 (proven track record at
S51 lockout). C3b adds its own banned substrings per spec § 7.5
(reasoning: tweak/option/negotiation language has C3b-specific failure
modes — coercion, authoritative ranking, accusatory framing).

Lint rule: any user-facing string containing a banned substring fails
lint. The function returns the first match; advisory_lint_text raises
AdvisoryLintError. Test isolation uses `find_banned_phrase` (returns
str | None).

Rule 11 self-analysis:
  1. We do a substring match. This is a known false-positive hazard:
     "trustworthy" contains "trust" (not currently banned), but
     "untrustworthy" contains "trustworthy" (banned). The unit tests
     pin those substring relationships.
  2. We INHERIT the C17 list but don't import — we duplicate it locally
     to keep C3b independently testable. Drift between the two lists
     is a documented risk; B-C3B-LINT-BASE-INHERITANCE-CONSOLIDATION
     v1.x backlog candidate (file at first sign of drift).
  3. We expose `replacement_hint()` so error messages can suggest
     alternatives. This is principle-aligned with Principle 1
     (talk to the user, not the engine).
  4. Reading aloud test: every BANNED entry is a phrase that, read
     aloud in a sentence aimed at a homeowner, sounds engine-centric,
     coercive, or accusatory. The discipline holds.
"""
from __future__ import annotations

from typing import Optional

from .versioning import C3B_BANNED_SUBSTRINGS, C3B_REPLACEMENT_HINTS


# ============================================================
# § 1 — Banned-phrase tables
# ============================================================

# Base list inherited from C17 v0.3 R2 (same advisory-tone discipline).
# Duplicated locally per self-analysis pt 2; mirror updates if/when
# C17 list changes.
C17_INHERITED_BANNED_SUBSTRINGS: tuple[str, ...] = (
    # Coercion / urgency
    "do not pay",
    "refuse to pay",
    "demand immediately",
    # Accusatory
    "overcharging",
    "ripping off",
    "ripped off",
    "fraud",
    "scam",
    "scamming",
    "cheating",
    "cheats",
    "hidden charges",
    "trying to charge",
    "padding the bill",
    "suspicious",
    "trustworthy",   # also catches "untrustworthy" (substring)
    "not credible",
    # Engine-centric (inherited)
    "according to my calculations",
)

# Final banned table = inherited + C3b-specific additions
BANNED_SUBSTRINGS: tuple[str, ...] = (
    C17_INHERITED_BANNED_SUBSTRINGS + C3B_BANNED_SUBSTRINGS
)


# Word-boundary banned phrases (where substring match would cause too
# many false positives — e.g., "best" in "best-effort", "must" in
# "mustard"). For now C3b adds none beyond what's in C3B_BANNED_SUBSTRINGS;
# the user-facing strings are short enough that substring works.
BANNED_WORD_BOUNDARY: tuple[str, ...] = ()


# ============================================================
# § 2 — Lint API
# ============================================================

class AdvisoryLintError(Exception):
    """Raised when a user-facing string contains a banned phrase.

    Caught at construction of advisory-bearing dataclasses or at
    explicit lint_advisory_text() invocation. The error includes
    the offending phrase, the field name, and (if available) a
    replacement hint."""

    def __init__(
        self,
        message:           str,
        *,
        offending_phrase:  str,
        field_name:        Optional[str] = None,
        replacement_hint:  Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.offending_phrase = offending_phrase
        self.field_name = field_name
        self.replacement_hint = replacement_hint


def find_banned_phrase(text: str) -> Optional[str]:
    """Return the first banned phrase found in `text` (case-insensitive),
    or None if clean. Substring match; intended for short user-facing
    strings (≤ ~500 chars per field). For test isolation."""
    if not text:
        return None
    lowered = text.lower()
    for phrase in BANNED_SUBSTRINGS:
        if phrase in lowered:
            return phrase
    return None


def is_advisory_clean(text: str) -> bool:
    """Boolean form. True if `text` has no banned phrases.
    Empty / None text returns True (no content to lint)."""
    return find_banned_phrase(text) is None


def lint_advisory_text(
    text:        str,
    *,
    field_name:  Optional[str] = None,
) -> None:
    """Raise AdvisoryLintError if `text` contains a banned phrase.

    Used at construction time inside dataclass __post_init__ hooks
    AND at emission time inside phase functions. Either guard catches
    drift; both layered = defense in depth.
    """
    found = find_banned_phrase(text)
    if found is None:
        return

    hint = replacement_hint(found)
    msg = (
        f"Advisory-tone lint failed"
        + (f" on field '{field_name}'" if field_name else "")
        + f": banned phrase '{found}' detected. "
        + (f"Consider using '{hint}' instead. " if hint else "")
        + "Reference: spec C3b v0.4 § 7.5 R2 banned-phrase list."
    )
    raise AdvisoryLintError(
        msg,
        offending_phrase=found,
        field_name=field_name,
        replacement_hint=hint,
    )


def replacement_hint(banned_phrase: str) -> Optional[str]:
    """Return a suggested replacement for `banned_phrase`, or None
    if we don't have one in the hint table.

    Match is case-insensitive and tolerant of root forms: "should",
    "should not", "shouldn't", "you should" all return the "could"
    hint via per-word root matching."""
    if not banned_phrase:
        return None
    key = banned_phrase.lower().strip()
    # Direct hit
    if key in C3B_REPLACEMENT_HINTS:
        return C3B_REPLACEMENT_HINTS[key]
    # Root-form fallback: try each word of phrase in turn
    for word in key.split():
        if word in C3B_REPLACEMENT_HINTS:
            return C3B_REPLACEMENT_HINTS[word]
    return None





# ══════════════════════════════════════════════════════════════════════════════
# § contracts                                                   
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — input/integration contracts
======================================================================

Spec: C3b v0.4.LOCKED § 8. Build session: S52.

This module re-exports the UPSTREAM types C3b consumes, plus declares
the small set of C3b-internal supporting types that pin the input
shape. Output schema lives in `schema.py`.

Upstream surface (per spec § 8):

  C15 v1.0 LOCKED   → SelectionResult, ProblemReport       (real, imported)
  C16 v1.2 LOCKED   → AttestedValue, AuthorityKind,
                      CheckProvenance, JurisdictionProfile (real, imported)
  C7  v0.8 LOCKED   → StructuralGridCell, GridColumn       (stub, imported)
  C12 v1.0 LOCKED   → PlacedRoom, RoomGeometry             (stub, imported)
  C13 v1.0 LOCKED   → DoorPlacement                         (stub, imported)
  C10 v1.0 LOCKED   → RiserGroup                            (stub, imported)
  C4  v1.0 LOCKED   → PlotAnalysis                          (stub, imported)
  C3a v0.2.1 LOCKED → ResolvedBrief, KickbackContext        (stub, imported)
  utils             → TransparencyTriple, Confidence,
                      DerivationLine                        (real, imported)

In addition this module declares:

  C3bInputBundle             — the full input envelope C3b operates on
                                  (composes the upstream types)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Tuple

# ----- Real upstream (LOCKED, in-tree) ---------------------------
from buildemup.components.c15.schema import ProblemReport  # noqa: F401
from buildemup.components.c16.contracts import (  # noqa: F401
    AttestedValue,
    AuthorityKind,
    SelectionResult,
)

# ----- Stub upstream (in-tree as stubs covering consumed surface) -
from buildemup.components.c03a.contracts import (  # noqa: F401
    KickbackContext,
    ResolvedBrief,
)
from buildemup.components.c04.contracts import (  # noqa: F401
    CardinalDirection,
    ClimateZone,
    PlotAnalysis,
)
from buildemup.components.c07.contracts import (  # noqa: F401
    GridColumn,
    StructuralGrid,
    StructuralGridCell,
)
from buildemup.components.c10.contracts import (  # noqa: F401
    Riser,
    RiserGroup,
)
from buildemup.components.c12.contracts import (  # noqa: F401
    PlacedRoom,
    RoomFunction,
    RoomGeometry,
)
from buildemup.components.c13.contracts import (  # noqa: F401
    DoorKind,
    DoorPlacement,
    SwingDirection,
)

# ----- Real utilities ---------------------------------------------
from buildemup.utils.confidence import Confidence  # noqa: F401
from buildemup.utils.transparency import (  # noqa: F401
    DerivationLine,
    TransparencyTriple,
)


# ============================================================
# § 1 — C3bInputBundle
# ============================================================

@dataclass(frozen=True)
class C3bInputBundle:
    """The full envelope of upstream inputs C3b operates on. Phase α
    consumes this and produces the initial TradeoffSession skeleton.

    Per spec § 1: C3b consumes
      1. SelectionResult from C15 (3 ranked layouts + provenance)
      2. ProblemReport per layout from C15 (3 reports, layout-aligned)
      3. ResolvedBrief from C3a
      4. PlotAnalysis from C4
    plus:
      5. PlacedRooms     — geometry grounding for R3 invariant
      6. StructuralGrid  — bay context for severity computation
      7. DoorPlacements  — door grounding for door_relocate tweaks
      8. RiserGroups     — wet-zone stack context for restage tweaks
    """
    selection_result:    SelectionResult
    problem_reports:     Tuple[ProblemReport, ...]
    """3 ProblemReports, one per layout, aligned with
    selection_result.layouts order."""

    resolved_brief:      ResolvedBrief
    plot_analysis:       PlotAnalysis

    placed_rooms_per_layout:   Tuple[Tuple[PlacedRoom, ...], ...]
    """Per layout (3 entries), the placed rooms. Aligned with
    selection_result.layouts order."""

    structural_grids_per_layout:  Tuple[StructuralGrid, ...]
    door_placements_per_layout:   Tuple[Tuple[DoorPlacement, ...], ...]
    riser_groups_per_layout:      Tuple[Tuple[RiserGroup, ...], ...]

    def __post_init__(self) -> None:
        n_reports = len(self.problem_reports)
        n_layouts = len(self.placed_rooms_per_layout)
        n_grids = len(self.structural_grids_per_layout)
        n_doors = len(self.door_placements_per_layout)
        n_risers = len(self.riser_groups_per_layout)
        # All 5 layout-aligned tuples must match in length
        if not (n_reports == n_layouts == n_grids == n_doors == n_risers):
            raise ValueError(
                f"C3bInputBundle layout-aligned tuples must all have "
                f"the same length; got problem_reports={n_reports}, "
                f"placed_rooms={n_layouts}, grids={n_grids}, "
                f"doors={n_doors}, risers={n_risers}"
            )
        # Empty is allowed at the type level (Phase α decides via
        # applicability boundary)
        if n_reports == 0:
            return


# ============================================================
# § 2 — Surface marker
# ============================================================

C3B_CONTRACTS_VERSION: Final[str] = "v0.4.LOCKED.s52"





# ══════════════════════════════════════════════════════════════════════════════
# § schema                                                      
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — output schema
========================================================

Spec: C3b v0.4.LOCKED §§ 2 + 7. Build session: S52.

This module defines all C3b output dataclasses. Inputs live in
`contracts.py`. Phase functions (α–ζ) live in `phases/` (built in
S53–S55). Orchestrator lives in `orchestrator.py` (built S55).

Dataclass-level invariant enforcement:

  R3   Layout grounding         — TweakOption __post_init__: at least
                                  one of affected_room_ids /
                                  affected_grid_cells must be non-empty
  R4   Severity discipline      — TweakOption __post_init__: LIGHT cannot
                                  carry a subset_rerun_payload; MEDIUM
                                  must carry subset_rerun_payload with
                                  non-empty downstream_impact_set
  R5   Recommendation flag      — RecommendationFlag is a Literal enum
                                  (structural marker only)
  R8   Schema versioning        — TradeoffSession.c3b_schema_version
                                  must match constant
  R13  Topology invariance      — MEDIUM tweaks MUST carry
                                  TopologyInvarianceResult; if
                                  invariance_preserved is False, severity
                                  cannot be 'medium' (must be 'heavy')
  R15  Multi-tweak compatibility — MEDIUM tweaks MUST carry
                                  compatibility_assertions (may be empty
                                  if no prior tweaks)
  R16  Single-linear-history    — TradeoffSession.session_history is a
                                  tuple (append-only by immutability);
                                  current_status enum pins the lifecycle
  R2   Advisory-tone lint       — every user-facing string is linted at
                                  construction

Rule 11 self-analysis (worst issues hunted):
  1. Layout grounding (R3) checks NON-EMPTINESS, not VALID-ID. The valid-ID
     check requires the upstream PlacedRoom / StructuralGridCell set,
     which lives in Phase β at composition time. Documented; tests for
     the integration check live in test_phase_beta (later).
  2. Severity-tier ↔ mutation_kind coupling enforced AT CONSTRUCTION
     (R4) — the dataclass refuses inconsistent combos. Stronger than
     deferring to a separate validate() call.
  3. TopologyInvarianceResult is required for MEDIUM but optional for
     LIGHT (a finish change doesn't touch topology). Tests cover both.
  4. CompatibilityAssertions tuple may be empty when there are no
     prior applied tweaks — empty is valid (not the same as missing).
  5. MutationEnvelope is a SEPARATE top-level type, not embedded in
     TweakOption; HEAVY tweaks are not surfaced as TweakOptions per R4.
  6. AdvisoryFlag is intentionally lightweight (kind enum + advisory
     text); the C16 v1.2 LOCKED AdvisoryFlag has more fields but C3b
     doesn't consume them yet. Kept local for now; will lift if/when
     C3b feeds C16 advisories directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Optional, Tuple

from .advisory_lint import lint_advisory_text
from .versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    EXPECTED_LAYOUT_COUNT,
    ITERATION_CAP_DEFAULT,
    ITERATION_CAP_HARD_CEILING,
    MAX_REPRESENT_COUNT,
    MAX_TWEAKS_PER_LAYOUT,
    SESSION_HISTORY_HARD_CEILING,
    TWEAKS_PER_LAYOUT_HARD_CEILING,
    TWEAK_COST_IMPACT_CEILING_INR,
    TWEAK_SPACE_IMPACT_CEILING_SQFT,
)

# ----- Re-used utility / upstream types ---------------------------
from buildemup.utils.transparency import TransparencyTriple
from buildemup.components.c16.contracts import AttestedValue, AuthorityKind


# ============================================================
# § 1 — Discriminated enums (Literals)
# ============================================================

TweakCategory = Literal[
    "room_swap",
    "room_resize",
    "balcony_add",
    "balcony_remove",
    "door_relocate",
    "window_resize",
    "wet_zone_restage",
    "finish_upgrade",
    "finish_downgrade",
    "storage_add",
    "pooja_relocate",
    "kitchen_reorient",
    "utility_zone_carveout",
]
"""Per spec § 2.3. 13 categories. Used by static
TWEAK_CATEGORY_DEFAULT_SEVERITY in phase β."""

SeverityTier = Literal["light", "medium", "heavy"]
"""Per spec § 2.3 + § 3 Phase β step 4. HEAVY tweaks are never
surfaced as TweakOptions (filtered at Phase β step 4 final
assignment)."""

RecommendationFlag = Literal["suggested", "optional", "alternative"]
"""Per spec § 2.3 + R5. STRUCTURAL marker, not authoritative ranking.
'suggested' means tweak resolves critical/important ProblemReport
check; NOT 'Claude thinks you should do this'."""

MutationKind = Literal[
    "geometry_local",
    "subset_rerun",
    "finish_schedule_only",
]
"""Per spec § 2.4."""

LayoutArchetype = Literal[
    "cost_efficient",
    "everyday_living",
    "premium_design",
]
"""Per spec § 2.2 + Design Principles v3.1 § 5 Layout Triad."""

TopologyClassification = Literal[
    "no_corridor", "strip", "central_spine", "l_shape", "courtyard",
]
"""Per C5 v1.0 LOCKED + spec § 2.4.2."""

PredictionBasis = Literal[
    "structural_grid_invariant",
    "circulation_pattern_invariant",
    "mutation_local_only",
    "heuristic_strong",
    "heuristic_weak",
]
"""Per spec § 2.4.2. 'heuristic_weak' triggers auto-HEAVY safety bias."""

CompatibilityKind = Literal[
    "spatial_overlap_check",
    "stack_alignment_check",
    "structural_continuity",
    "circulation_reachability",
]
"""Per spec § 2.4.3 + R15."""

CompatibilityResult = Literal["compatible", "conflicts", "ambiguous"]
"""Per spec § 2.4.3."""

DownstreamComponent = Literal[
    "c4", "c5", "c6", "c7", "c8", "c9", "c10",
    "c11a", "c11b", "c12", "c13", "c14", "c15",
]
"""Per spec § 2.4.1. Lex-ASC sorted for replay determinism."""

DownstreamImpact = Literal[
    "circulation_graph",
    "structural_grid",
    "wet_zone_stacks",
    "vertical_alignment",
    "furniture_fit",
    "natural_light",
    "cross_ventilation",
    "problem_report",
    "ranking_score",
    "topology_classification",
    "finish_schedule",
    "door_placement",
]
"""Per spec § 2.4.1. 'topology_classification' impact forces R13
auto-promote to HEAVY."""

MutationClassification = Literal[
    "brief_level_change",
    "topology_level_change",
    "structural_level_change",
    "out_of_v1_scope",
    "constraint_violation",
]
"""Per spec § 2.8."""

SuggestedPathway = Literal[
    "step_back_to_brief",
    "accept_layout_as_is",
    "explore_alternative_layout",
    "defer_to_v2_feature",
]
"""Per spec § 2.8."""

UserAction = Literal[
    "accepted_tweak",
    "rejected_tweak",
    "no_action_continue",
    "finalized_layout_choice",
    "kicked_back_to_c3a",
    "abandoned_session",
]
"""Per spec § 2.5."""

ApplyStatus = Literal[
    "applied_successfully",
    "rerun_queued",
    "rerun_failed",
    "rejected_constraint_violation",
]
"""Per spec § 2.7 ApplyOutcome."""

SessionStatus = Literal[
    "open_for_user_input",
    "awaiting_subset_rerun",
    "resolved_selection_ready",
    "kicked_back_to_c3a",
    "abandoned_no_tweaks",
    "iteration_cap_reached",
]
"""Per spec § 2.1."""

ComfortDimension = Literal[
    "natural_light",
    "cross_ventilation",
    "privacy",
    "noise_isolation",
    "circulation_efficiency",
    "outdoor_connection",
    "storage_capacity",
    "vastu_alignment_opt_in",
    "fire_egress",
    "accessibility",
]
"""Per spec § 2.7 ComfortImpact."""

ComfortDirection = Literal["improves", "worsens", "mixed"]
ComfortMagnitude = Literal["small", "moderate", "significant"]


# ============================================================
# § 2 — TopologyInvarianceResult (R13 support — spec § 2.4.2)
# ============================================================

@dataclass(frozen=True)
class TopologyInvarianceResult:
    """Predicts whether a candidate MEDIUM tweak preserves C5
    topology classification. Attached to every MEDIUM tweak's
    SubsetRerunRequest (per R13)."""
    source_topology:        TopologyClassification
    predicted_topology:     TopologyClassification
    invariance_preserved:   bool
    prediction_basis:       PredictionBasis
    advisory_note:          Optional[str] = None

    def __post_init__(self) -> None:
        # Internal consistency: invariance_preserved must match
        # source == predicted
        actual_match = self.source_topology == self.predicted_topology
        if self.invariance_preserved != actual_match:
            raise ValueError(
                f"TopologyInvarianceResult.invariance_preserved="
                f"{self.invariance_preserved} contradicts "
                f"source_topology={self.source_topology!r} vs "
                f"predicted_topology={self.predicted_topology!r}"
            )
        # heuristic_weak with invariance_preserved=True is a contract
        # violation — weak prediction should bias to HEAVY (caller
        # should not have generated this combination)
        if (
            self.prediction_basis == "heuristic_weak"
            and self.invariance_preserved
        ):
            raise ValueError(
                "TopologyInvarianceResult: prediction_basis='heuristic_weak' "
                "with invariance_preserved=True is invalid — weak prediction "
                "must safety-bias to HEAVY (invariance_preserved=False)"
            )
        # Advisory required when invariance broken
        if not self.invariance_preserved and not self.advisory_note:
            raise ValueError(
                "TopologyInvarianceResult: advisory_note required when "
                "invariance_preserved=False (explain why topology would alter)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="TopologyInvarianceResult.advisory_note",
            )


# ============================================================
# § 3 — CompatibilityAssertion (R15 support — spec § 2.4.3)
# ============================================================

@dataclass(frozen=True)
class CompatibilityAssertion:
    """Asserts compatibility (or conflict) of a new tweak against an
    already-applied tweak earlier in the session.

    Empty `compatibility_assertions` is valid for the first MEDIUM
    tweak applied in a session (no prior tweaks to check)."""
    against_applied_tweak_id:   str
    compatibility_kind:         CompatibilityKind
    result:                     CompatibilityResult
    advisory_note:              Optional[str] = None

    def __post_init__(self) -> None:
        if not self.against_applied_tweak_id:
            raise ValueError(
                "CompatibilityAssertion.against_applied_tweak_id "
                "must be non-empty"
            )
        # Advisory required when conflict (spec § 2.4.3)
        if self.result == "conflicts" and not self.advisory_note:
            raise ValueError(
                "CompatibilityAssertion: advisory_note required when "
                "result='conflicts' (must explain what conflicts + options)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="CompatibilityAssertion.advisory_note",
            )


# ============================================================
# § 4 — SubsetRerunRequest (FORMALIZED v0.2 — spec § 2.4.1)
# ============================================================

@dataclass(frozen=True)
class SubsetRerunRequest:
    """Structured request to an external subset-rerun orchestrator
    (out of scope for C3b itself). Every MEDIUM tweak carries one of
    these inside its ApplySpecification.subset_rerun_payload.

    R13 + R15 enforcement converge here:
      - downstream_impact_set MUST be non-empty (R13/spec § 2.4.1)
      - topology_invariance_check MUST be set (R13)
      - compatibility_assertions MAY be empty (no prior tweaks)
    """
    trigger_tweak_id:        str
    trigger_tweak_category:  TweakCategory

    components_to_rerun:     Tuple[DownstreamComponent, ...]
    """Lex-ASC sorted for replay determinism."""

    downstream_impact_set:   Tuple[DownstreamImpact, ...]
    """Per R13/spec § 2.4.1: MANDATORY non-empty. The static minimum
    impact set per tweak category lives in TWEAK_CATEGORY_IMPACT_TABLE
    (Phase β). Lex-ASC sorted."""

    topology_invariance_check:   TopologyInvarianceResult
    expected_completion_seconds: float
    rerun_anchor:                str
    """Domain-specific constraint preservation, e.g.
    'wet_zone_eastward_with_structural_bay_lock'."""

    compatibility_assertions:    Tuple[CompatibilityAssertion, ...] = ()
    """Per R15. Empty when first MEDIUM tweak in session."""

    def __post_init__(self) -> None:
        if not self.trigger_tweak_id:
            raise ValueError(
                "SubsetRerunRequest.trigger_tweak_id must be non-empty"
            )
        # R13/spec § 2.4.1: downstream_impact_set is MANDATORY non-empty
        if not self.downstream_impact_set:
            raise ValueError(
                "SubsetRerunRequest.downstream_impact_set must be non-empty "
                "(R13 / spec § 2.4.1). Every MEDIUM tweak must declare "
                "what downstream coupling it touches."
            )
        # components_to_rerun also mandatory non-empty
        if not self.components_to_rerun:
            raise ValueError(
                "SubsetRerunRequest.components_to_rerun must be non-empty"
            )
        # Lex-ASC sort enforcement for replay determinism (R6)
        comp_list = list(self.components_to_rerun)
        if comp_list != sorted(comp_list):
            raise ValueError(
                f"SubsetRerunRequest.components_to_rerun must be lex-ASC "
                f"sorted; got {self.components_to_rerun!r}"
            )
        impact_list = list(self.downstream_impact_set)
        if impact_list != sorted(impact_list):
            raise ValueError(
                f"SubsetRerunRequest.downstream_impact_set must be lex-ASC "
                f"sorted; got {self.downstream_impact_set!r}"
            )
        # expected_completion_seconds bounds (per spec § 2.4.1):
        # > 10s requires reclassification — caller must have caught this
        if self.expected_completion_seconds <= 0:
            raise ValueError(
                f"SubsetRerunRequest.expected_completion_seconds must be "
                f"positive; got {self.expected_completion_seconds}"
            )
        if not self.rerun_anchor:
            raise ValueError(
                "SubsetRerunRequest.rerun_anchor must be non-empty"
            )


# ============================================================
# § 5 — KickBackPayload (spec § 2.8 — for brief-level kickback)
# ============================================================

@dataclass(frozen=True)
class KickBackPayload:
    """Structured request when MutationEnvelope.classification ==
    'brief_level_change'. Wraps the data C3a needs to revisit the
    brief.

    This composes with c03a.KickbackContext (the actual cross-component
    message) — KickBackPayload lives INSIDE the MutationEnvelope,
    KickbackContext is what the orchestrator hands to C3a."""
    target_brief_field:      Literal[
        "room_program", "floor_count", "plot_orientation",
        "extreme_case_revisit", "other",
    ]
    target_brief_field_advisory: str
    user_requested_change:   str
    proposed_change_summary: str

    def __post_init__(self) -> None:
        if not self.target_brief_field_advisory:
            raise ValueError(
                "KickBackPayload.target_brief_field_advisory must be non-empty"
            )
        if not self.user_requested_change:
            raise ValueError(
                "KickBackPayload.user_requested_change must be non-empty"
            )
        if not self.proposed_change_summary:
            raise ValueError(
                "KickBackPayload.proposed_change_summary must be non-empty"
            )
        lint_advisory_text(
            self.target_brief_field_advisory,
            field_name="KickBackPayload.target_brief_field_advisory",
        )
        lint_advisory_text(
            self.proposed_change_summary,
            field_name="KickBackPayload.proposed_change_summary",
        )


# ============================================================
# § 6 — MutationEnvelope (NEW v0.2 — spec § 2.8)
# ============================================================

@dataclass(frozen=True)
class MutationEnvelope:
    """When a user-requested change classifies as HEAVY (or implicit
    accumulated requests imply HEAVY), C3b emits a MutationEnvelope
    instead of attempting the mutation. Per Principle 3 (advisory) +
    Principle 4 (user intervention checkpoints).

    v0.5 amendment A6: speculative_preview_text added (Optional).
    Phase β populates with a text description of what the restructured
    layout would look like, so users can decide whether to step back
    to brief or accept the heavy-change pathway.
    """
    envelope_id:              str
    requested_change_summary: str
    classification:           MutationClassification
    why_not_a_tweak:          str
    suggested_pathway:        SuggestedPathway
    estimated_pathway_effort: str
    advisory_note:            str
    kick_back_payload:        Optional[KickBackPayload] = None
    # v0.5 A6 — speculative preview text (Optional)
    speculative_preview_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.envelope_id:
            raise ValueError("MutationEnvelope.envelope_id must be non-empty")
        if not self.requested_change_summary:
            raise ValueError(
                "MutationEnvelope.requested_change_summary must be non-empty"
            )
        # Spec § 2.8: kick_back_payload populated iff classification ==
        # "brief_level_change"
        if (
            self.classification == "brief_level_change"
            and self.kick_back_payload is None
        ):
            raise ValueError(
                "MutationEnvelope: kick_back_payload required when "
                "classification='brief_level_change'"
            )
        if (
            self.classification != "brief_level_change"
            and self.kick_back_payload is not None
        ):
            raise ValueError(
                f"MutationEnvelope: kick_back_payload must be None when "
                f"classification={self.classification!r} (only used for "
                f"'brief_level_change')"
            )
        # Lint all user-facing strings
        for field_name, text in [
            ("why_not_a_tweak",          self.why_not_a_tweak),
            ("estimated_pathway_effort", self.estimated_pathway_effort),
            ("advisory_note",            self.advisory_note),
        ]:
            if not text:
                raise ValueError(
                    f"MutationEnvelope.{field_name} must be non-empty"
                )
            lint_advisory_text(
                text, field_name=f"MutationEnvelope.{field_name}",
            )
        # v0.5 A6 — preview text is optional, but if populated, must lint clean
        if self.speculative_preview_text is not None:
            if not self.speculative_preview_text:
                raise ValueError(
                    "MutationEnvelope.speculative_preview_text must be None "
                    "or non-empty; got empty string"
                )
            lint_advisory_text(
                self.speculative_preview_text,
                field_name="MutationEnvelope.speculative_preview_text",
            )


# ============================================================
# § 7 — Supporting impact types (spec § 2.7)
# ============================================================

@dataclass(frozen=True)
class SpaceImpact:
    """Per-room sqft delta + total delta + advisory. Spec § 2.7."""
    per_room_sqft_delta:    Tuple[Tuple[str, float], ...]
    """(room_id, sqft_delta) — lex-ASC by room_id."""

    total_sqft_delta:       float
    total_carpet_area_after: AttestedValue
    """LOCALLY_DERIVED via Phase γ."""

    advisory_note:          str = ""

    def __post_init__(self) -> None:
        # Lex-ASC sort enforcement (R6)
        rooms_list = list(self.per_room_sqft_delta)
        sorted_rooms = sorted(rooms_list, key=lambda r: r[0])
        if rooms_list != sorted_rooms:
            raise ValueError(
                "SpaceImpact.per_room_sqft_delta must be lex-ASC by room_id"
            )
        # Spec § 6 ceiling: |total_sqft_delta| ≤ TWEAK_SPACE_IMPACT_CEILING
        if abs(self.total_sqft_delta) > TWEAK_SPACE_IMPACT_CEILING_SQFT:
            raise ValueError(
                f"SpaceImpact.total_sqft_delta |{self.total_sqft_delta}| "
                f"exceeds tweak ceiling {TWEAK_SPACE_IMPACT_CEILING_SQFT} "
                f"sqft. A tweak this large is brief-level, not layout-level."
            )
        # Authority discipline (R1)
        if self.total_carpet_area_after.authority != AuthorityKind.LOCALLY_DERIVED:
            raise ValueError(
                f"SpaceImpact.total_carpet_area_after must be "
                f"LOCALLY_DERIVED; got "
                f"{self.total_carpet_area_after.authority}"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note, field_name="SpaceImpact.advisory_note",
            )


@dataclass(frozen=True)
class ComfortImpact:
    """Qualitative comfort impact. Spec § 2.7.

    v0.5 amendment A7: 3 optional emotional-heuristic scores added.
    All Optional[float] in [0.0, 1.0]; default None means heuristic
    didn't fire / wasn't applicable. Used as tie-break signals in
    Phase β priority sort.
    """
    dimensions_affected:    Tuple[ComfortDimension, ...]
    direction:              ComfortDirection
    magnitude:              ComfortMagnitude
    advisory_note:          str = ""
    # v0.5 A7 — emotional layout heuristics (Optional, [0.0, 1.0])
    perceived_spaciousness:    Optional[float] = None
    arrival_impression:        Optional[float] = None
    family_gathering_comfort:  Optional[float] = None

    def __post_init__(self) -> None:
        if not self.dimensions_affected:
            raise ValueError(
                "ComfortImpact.dimensions_affected must be non-empty"
            )
        dims_list = list(self.dimensions_affected)
        if dims_list != sorted(dims_list):
            raise ValueError(
                "ComfortImpact.dimensions_affected must be lex-ASC sorted"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note, field_name="ComfortImpact.advisory_note",
            )
        for name, val in (
            ("perceived_spaciousness", self.perceived_spaciousness),
            ("arrival_impression", self.arrival_impression),
            ("family_gathering_comfort", self.family_gathering_comfort),
        ):
            if val is not None and not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"ComfortImpact.{name}={val} outside [0.0, 1.0]"
                )


# ============================================================
# § 8 — ApplySpecification (spec § 2.4) + payload types
# ============================================================

@dataclass(frozen=True)
class GeometryLocalPayload:
    """For mutation_kind='geometry_local' — LIGHT tweaks applied in-place."""
    new_room_function_assignments: Tuple[Tuple[str, str], ...] = ()
    """(room_id, new_function) for room_swap. Lex-ASC by room_id."""

    new_door_placements_replace:   Tuple[str, ...] = ()
    """door_ids to replace (door_relocate). Lex-ASC."""

    new_window_assignments:        Tuple[Tuple[str, int], ...] = ()
    """(wall_id, new_width_mm). Lex-ASC by wall_id."""

    advisory_note:                 str = ""

    def __post_init__(self) -> None:
        # Lex-ASC sort enforcement (R6)
        if list(self.new_room_function_assignments) != sorted(
            self.new_room_function_assignments, key=lambda x: x[0]
        ):
            raise ValueError(
                "GeometryLocalPayload.new_room_function_assignments "
                "must be lex-ASC by room_id"
            )
        if list(self.new_door_placements_replace) != sorted(
            self.new_door_placements_replace
        ):
            raise ValueError(
                "GeometryLocalPayload.new_door_placements_replace "
                "must be lex-ASC"
            )
        if list(self.new_window_assignments) != sorted(
            self.new_window_assignments, key=lambda x: x[0]
        ):
            raise ValueError(
                "GeometryLocalPayload.new_window_assignments "
                "must be lex-ASC by wall_id"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="GeometryLocalPayload.advisory_note",
            )


@dataclass(frozen=True)
class FinishSchedulePayload:
    """For mutation_kind='finish_schedule_only' — feeds C16 schedule
    update directly."""
    room_finish_overrides: Tuple[Tuple[str, str, str], ...]
    """(room_id, finish_element, new_finish_grade) tuples.
    Lex-ASC by (room_id, finish_element). Non-empty by construction."""

    advisory_note:         str = ""

    def __post_init__(self) -> None:
        if not self.room_finish_overrides:
            raise ValueError(
                "FinishSchedulePayload.room_finish_overrides must be non-empty"
            )
        rfo = list(self.room_finish_overrides)
        if rfo != sorted(rfo, key=lambda t: (t[0], t[1])):
            raise ValueError(
                "FinishSchedulePayload.room_finish_overrides must be lex-ASC "
                "by (room_id, finish_element)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="FinishSchedulePayload.advisory_note",
            )


@dataclass(frozen=True)
class ApplySpecification:
    """The structured mutation downstream components honor when a
    tweak is accepted. Spec § 2.4 + § 2.4.1 (formalized v0.2).

    R4 enforcement at construction:
      - mutation_kind='geometry_local'      → geometry_local_payload set,
                                                others None
      - mutation_kind='subset_rerun'        → subset_rerun_payload set,
                                                others None
      - mutation_kind='finish_schedule_only' → finish_schedule_payload set,
                                                others None
    """
    mutation_kind:              MutationKind
    geometry_local_payload:     Optional[GeometryLocalPayload] = None
    subset_rerun_payload:       Optional[SubsetRerunRequest] = None
    finish_schedule_payload:    Optional[FinishSchedulePayload] = None

    def __post_init__(self) -> None:
        kinds_set = {
            "geometry_local":       self.geometry_local_payload is not None,
            "subset_rerun":         self.subset_rerun_payload is not None,
            "finish_schedule_only": self.finish_schedule_payload is not None,
        }
        # Exactly one payload field must be set, matching mutation_kind
        n_set = sum(kinds_set.values())
        if n_set != 1:
            raise ValueError(
                f"ApplySpecification: exactly one payload field must be set; "
                f"got {n_set} (mutation_kind={self.mutation_kind!r}, "
                f"set fields: {[k for k, v in kinds_set.items() if v]})"
            )
        if not kinds_set[self.mutation_kind]:
            raise ValueError(
                f"ApplySpecification: mutation_kind={self.mutation_kind!r} "
                f"but corresponding payload field is None"
            )


# ============================================================
# § 9 — CheckProvenance (lightweight version for C3b)
# ============================================================

@dataclass(frozen=True)
class TweakProvenance:
    """Lightweight provenance for tweak generation.
    Per spec § 2.2 — every tweak traces back to which ProblemReport
    check OR which structural grid cell motivated it."""
    motivated_by_check_id:      Optional[str] = None
    motivated_by_grid_cell_id:  Optional[str] = None
    motivated_by_orientation:   Optional[str] = None
    generation_basis:           str = ""

    def __post_init__(self) -> None:
        # At least one motivation source required
        n_motivations = sum([
            self.motivated_by_check_id is not None,
            self.motivated_by_grid_cell_id is not None,
            self.motivated_by_orientation is not None,
        ])
        if n_motivations == 0:
            raise ValueError(
                "TweakProvenance: at least one motivation source required "
                "(check / grid cell / orientation)"
            )
        if not self.generation_basis:
            raise ValueError(
                "TweakProvenance.generation_basis must be non-empty"
            )


# ============================================================
# § 10 — TweakOption (spec § 2.3) — THE central user-facing unit
# ============================================================

@dataclass(frozen=True)
class TweakOption:
    """A single tweak suggestion attached to a layout.

    Enforces at construction:
      R3   layout grounding (affected_room_ids OR affected_grid_cells)
      R4   severity↔mutation_kind discipline
      R5   recommendation_flag is structural (Literal enum)
      R9   layout grounding non-emptiness
      R13  MEDIUM tweaks carry topology_invariance_check via SubsetRerunRequest
      R2   description / advisory text lint
    """
    tweak_id:               str
    tweak_category:         TweakCategory
    severity_tier:          SeverityTier

    affected_room_ids:      Tuple[str, ...]
    affected_grid_cells:    Tuple[str, ...]

    description:            str
    cost_impact:            TransparencyTriple
    space_impact:           SpaceImpact
    comfort_impact:         ComfortImpact

    problem_report_links:   Tuple[str, ...]
    recommendation_flag:    RecommendationFlag

    apply_specification:    ApplySpecification
    provenance:             TweakProvenance

    presented_count:        int = 0
    """How many times this tweak has been surfaced to the user.
    MAX_REPRESENT_COUNT (=2) is the don't-re-suggest ceiling."""

    def __post_init__(self) -> None:
        if not self.tweak_id:
            raise ValueError("TweakOption.tweak_id must be non-empty")

        # R4: severity 'heavy' must NEVER appear here (HEAVY is filtered
        # at Phase β step 4, surfaced via MutationEnvelope instead)
        if self.severity_tier == "heavy":
            raise ValueError(
                "TweakOption.severity_tier='heavy' is invalid — HEAVY tweaks "
                "are filtered at Phase β and surfaced as MutationEnvelope, "
                "not as TweakOptions (R4)"
            )

        # R3 + R9: layout grounding — at least one of room_ids / grid_cells
        if not self.affected_room_ids and not self.affected_grid_cells:
            raise ValueError(
                "TweakOption: at least one of affected_room_ids / "
                "affected_grid_cells must be non-empty (R3 + R9 layout "
                "grounding — every tweak must attach to a building element)"
            )

        # Lex-ASC sort enforcement (R6)
        if list(self.affected_room_ids) != sorted(self.affected_room_ids):
            raise ValueError(
                "TweakOption.affected_room_ids must be lex-ASC sorted"
            )
        if list(self.affected_grid_cells) != sorted(self.affected_grid_cells):
            raise ValueError(
                "TweakOption.affected_grid_cells must be lex-ASC sorted"
            )
        if list(self.problem_report_links) != sorted(self.problem_report_links):
            raise ValueError(
                "TweakOption.problem_report_links must be lex-ASC sorted"
            )

        # R4 severity↔mutation_kind coupling
        if self.severity_tier == "light":
            # LIGHT must use geometry_local or finish_schedule_only
            if self.apply_specification.mutation_kind == "subset_rerun":
                raise ValueError(
                    "TweakOption: severity_tier='light' cannot use "
                    "mutation_kind='subset_rerun' (R4 — LIGHT tweaks "
                    "never trigger pipeline rerun)"
                )
        elif self.severity_tier == "medium":
            # MEDIUM must use subset_rerun
            if self.apply_specification.mutation_kind != "subset_rerun":
                raise ValueError(
                    f"TweakOption: severity_tier='medium' must use "
                    f"mutation_kind='subset_rerun'; got "
                    f"{self.apply_specification.mutation_kind!r} (R4)"
                )
            # R13: MEDIUM must carry topology_invariance_check; if
            # invariance not preserved, severity should have been HEAVY
            srr = self.apply_specification.subset_rerun_payload
            assert srr is not None  # mutation_kind discipline guarantees this
            if not srr.topology_invariance_check.invariance_preserved:
                raise ValueError(
                    "TweakOption: severity_tier='medium' with "
                    "topology_invariance_check.invariance_preserved=False "
                    "is invalid — R13 mandates auto-promote to HEAVY when "
                    "topology would change"
                )

        # presented_count discipline
        if self.presented_count < 0:
            raise ValueError(
                f"TweakOption.presented_count must be >= 0; "
                f"got {self.presented_count}"
            )
        if self.presented_count > MAX_REPRESENT_COUNT:
            raise ValueError(
                f"TweakOption.presented_count={self.presented_count} "
                f"exceeds MAX_REPRESENT_COUNT={MAX_REPRESENT_COUNT} "
                f"(don't re-suggest a rejected tweak more than twice)"
            )

        # Cost-impact ceiling (spec § 6)
        if abs(self.cost_impact.exact_value) > TWEAK_COST_IMPACT_CEILING_INR:
            raise ValueError(
                f"TweakOption.cost_impact.exact_value "
                f"|₹{self.cost_impact.exact_value:,.0f}| exceeds tweak "
                f"ceiling ₹{TWEAK_COST_IMPACT_CEILING_INR:,.0f}. A tweak "
                f"this expensive is brief-level work, not a layout tweak."
            )

        # R2: lint user-facing text
        if not self.description:
            raise ValueError("TweakOption.description must be non-empty")
        lint_advisory_text(
            self.description, field_name="TweakOption.description",
        )


# ============================================================
# § 11 — TweakOptionSet (spec § 2.2)
# ============================================================

@dataclass(frozen=True)
class TweakOptionSet:
    """Per-layout tweak suggestions. Spec § 2.2.

    Hard ceiling: TWEAKS_PER_LAYOUT_HARD_CEILING (=8). The soft target
    is MAX_TWEAKS_PER_LAYOUT (=6). Exceeding the hard ceiling raises;
    exceeding the soft target should have been bounded at Phase β."""
    layout_id:                  str
    layout_archetype:           LayoutArchetype
    source_problem_report_id:   str

    tweaks:                     Tuple[TweakOption, ...]
    """3-6 typical, hard ceiling 8. lex-ASC by tweak_id."""

    overall_advisory_note:      str

    def __post_init__(self) -> None:
        if not self.layout_id:
            raise ValueError("TweakOptionSet.layout_id must be non-empty")
        if not self.source_problem_report_id:
            raise ValueError(
                "TweakOptionSet.source_problem_report_id must be non-empty"
            )

        # Hard ceiling (spec § 6)
        if len(self.tweaks) > TWEAKS_PER_LAYOUT_HARD_CEILING:
            raise ValueError(
                f"TweakOptionSet: {len(self.tweaks)} tweaks exceeds hard "
                f"ceiling {TWEAKS_PER_LAYOUT_HARD_CEILING} for layout "
                f"{self.layout_id!r}"
            )

        # Lex-ASC by tweak_id (R6)
        tweak_ids = [t.tweak_id for t in self.tweaks]
        if tweak_ids != sorted(tweak_ids):
            raise ValueError(
                f"TweakOptionSet.tweaks must be lex-ASC sorted by "
                f"tweak_id; got {tweak_ids!r}"
            )

        # Unique tweak_ids within the set
        if len(set(tweak_ids)) != len(tweak_ids):
            raise ValueError(
                f"TweakOptionSet.tweaks: duplicate tweak_ids in layout "
                f"{self.layout_id!r}"
            )

        # R2 lint
        if not self.overall_advisory_note:
            raise ValueError(
                "TweakOptionSet.overall_advisory_note must be non-empty"
            )
        lint_advisory_text(
            self.overall_advisory_note,
            field_name="TweakOptionSet.overall_advisory_note",
        )


# ============================================================
# § 12 — ApplyOutcome (spec § 2.7)
# ============================================================

@dataclass(frozen=True)
class ApplyOutcome:
    """Result of applying an accepted tweak. Spec § 2.7."""
    apply_status:            ApplyStatus
    error_summary:           Optional[str] = None
    new_layout_signature:    Optional[str] = None
    new_problem_report_id:   Optional[str] = None
    regression_detected:     bool = False
    """R14 — set True when post-rerun ProblemReport has more
    severity='critical' checks than pre-rerun."""

    newly_critical_check_ids: Tuple[str, ...] = ()
    """R14 — listing of the specific checks newly classified critical.
    Empty when regression_detected=False."""

    def __post_init__(self) -> None:
        # Lex-ASC sort (R6)
        if list(self.newly_critical_check_ids) != sorted(
            self.newly_critical_check_ids
        ):
            raise ValueError(
                "ApplyOutcome.newly_critical_check_ids must be lex-ASC sorted"
            )
        # Consistency: regression_detected ↔ non-empty newly_critical
        if self.regression_detected and not self.newly_critical_check_ids:
            raise ValueError(
                "ApplyOutcome: regression_detected=True requires "
                "newly_critical_check_ids to be non-empty (R14)"
            )
        if not self.regression_detected and self.newly_critical_check_ids:
            raise ValueError(
                "ApplyOutcome: newly_critical_check_ids must be empty "
                "when regression_detected=False"
            )
        # Failure status must carry an error_summary
        if self.apply_status == "rerun_failed" and not self.error_summary:
            raise ValueError(
                "ApplyOutcome.error_summary required when "
                "apply_status='rerun_failed'"
            )


# ============================================================
# § 13 — SessionTurn (audit log unit — spec § 2.5)
# ============================================================

@dataclass(frozen=True)
class SessionTurn:
    """One turn of the negotiation session. Append-only.

    R12: every turn records the FULL presented_tweaks set the user saw,
    not just the chosen one. Audit trail is reproducible.

    R7d (no-time inheritance): timestamp_offset_ms is RELATIVE to
    session_id creation, not absolute wall-clock time. Replay-safe.

    v0.5 amendment A4: strategic_advisory_text added (Optional).
    Populated only when C3bRuntimeConfig.strategic_mode != "off".
    R17 invariant: this field MUST NOT be included in
    canonical_replay_signature input (see cache_keys.py).
    """
    turn_id:                 str
    iteration_index:         int
    timestamp_offset_ms:     int
    presented_tweaks:        Tuple[str, ...]
    """All tweak_ids the user could choose from. Lex-ASC sorted (R6)."""

    user_action:             UserAction
    chosen_tweak_id:         Optional[str] = None
    apply_outcome:           Optional[ApplyOutcome] = None
    post_turn_status:        SessionStatus = "open_for_user_input"
    # v0.5 A4 — strategic advisory text (Optional). When populated, must
    # NOT affect canonical_replay_signature (R17).
    strategic_advisory_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.turn_id:
            raise ValueError("SessionTurn.turn_id must be non-empty")
        if self.iteration_index < 0:
            raise ValueError(
                f"SessionTurn.iteration_index must be >= 0; "
                f"got {self.iteration_index}"
            )
        if self.timestamp_offset_ms < 0:
            raise ValueError(
                f"SessionTurn.timestamp_offset_ms must be >= 0 "
                f"(relative to session creation); got {self.timestamp_offset_ms}"
            )

        # Lex-ASC sort (R6) — R12 audit-trail discipline
        if list(self.presented_tweaks) != sorted(self.presented_tweaks):
            raise ValueError(
                "SessionTurn.presented_tweaks must be lex-ASC sorted"
            )

        # Q3 Level B invariant: chosen must be in presented (if any)
        if self.chosen_tweak_id is not None:
            if self.chosen_tweak_id not in self.presented_tweaks:
                raise ValueError(
                    f"SessionTurn.chosen_tweak_id={self.chosen_tweak_id!r} "
                    f"not in presented_tweaks={self.presented_tweaks!r} "
                    f"(Q3 Level B logging discipline)"
                )

        # user_action ↔ chosen_tweak_id coherence
        action_needs_choice = {"accepted_tweak", "rejected_tweak"}
        if self.user_action in action_needs_choice and self.chosen_tweak_id is None:
            raise ValueError(
                f"SessionTurn: user_action={self.user_action!r} requires "
                f"chosen_tweak_id (must reference what was accepted/rejected)"
            )
        if self.user_action not in action_needs_choice and self.chosen_tweak_id is not None:
            raise ValueError(
                f"SessionTurn: chosen_tweak_id must be None for "
                f"user_action={self.user_action!r}"
            )

        # apply_outcome ↔ user_action coherence
        if self.user_action == "accepted_tweak" and self.apply_outcome is None:
            raise ValueError(
                "SessionTurn: user_action='accepted_tweak' requires apply_outcome"
            )
        if self.user_action != "accepted_tweak" and self.apply_outcome is not None:
            raise ValueError(
                f"SessionTurn: apply_outcome must be None for "
                f"user_action={self.user_action!r}"
            )

        # v0.5 A4 — strategic advisory text must lint clean if populated
        if self.strategic_advisory_text is not None:
            if not self.strategic_advisory_text:
                raise ValueError(
                    "SessionTurn.strategic_advisory_text must be None or "
                    "non-empty; got empty string"
                )
            lint_advisory_text(
                self.strategic_advisory_text,
                field_name="SessionTurn.strategic_advisory_text",
            )


# ============================================================
# § 14 — ResolvedSelection (spec § 2.6)
# ============================================================

@dataclass(frozen=True)
class ResolvedSelection:
    """Final output to C16. Spec § 2.6."""
    chosen_layout_id:          str
    chosen_layout_archetype:   LayoutArchetype
    applied_tweaks:            Tuple[str, ...]
    final_layout_signature:    str
    final_problem_report_id:   Optional[str] = None
    total_cost_delta:          Optional[TransparencyTriple] = None
    total_space_delta:         Optional[SpaceImpact] = None
    final_handoff_advisory:    str = ""

    def __post_init__(self) -> None:
        if not self.chosen_layout_id:
            raise ValueError(
                "ResolvedSelection.chosen_layout_id must be non-empty"
            )
        if not self.final_layout_signature:
            raise ValueError(
                "ResolvedSelection.final_layout_signature must be non-empty"
            )
        # Lex-ASC sort (R6)
        if list(self.applied_tweaks) != sorted(self.applied_tweaks):
            raise ValueError(
                "ResolvedSelection.applied_tweaks must be lex-ASC sorted"
            )
        if not self.final_handoff_advisory:
            raise ValueError(
                "ResolvedSelection.final_handoff_advisory must be non-empty"
            )
        lint_advisory_text(
            self.final_handoff_advisory,
            field_name="ResolvedSelection.final_handoff_advisory",
        )


# ============================================================
# § 15 — AdvisoryFlag (lightweight, C3b-local)
# ============================================================

AdvisoryFlagKind = Literal[
    "regression_after_apply",        # R14
    "compatibility_ambiguous",        # R15 ambiguous (not conflict)
    "iteration_cap_warning_nudge",    # approaching cap
    "topology_invariance_weak_basis", # heuristic_weak — promoted to HEAVY
    "pareto_diversity_floor_borderline",
    # v0.5 A2 — periodic full-coherence recheck
    "full_coherence_recheck_triggered",
    # v0.5 A3 — oscillation pattern detection
    "oscillation_pattern_detected",
    # v0.5 A5 — continuous dimension delta regression (numeric, sub-CRITICAL)
    "dimension_score_regression",
]


@dataclass(frozen=True)
class AdvisoryFlag:
    """Surface-level advisory attached to a TradeoffSession.
    Lightweight; C3b doesn't need C16's full AdvisoryFlag surface."""
    flag_id:        str
    kind:           AdvisoryFlagKind
    advisory_note:  str
    related_ids:    Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.flag_id:
            raise ValueError("AdvisoryFlag.flag_id must be non-empty")
        if not self.advisory_note:
            raise ValueError("AdvisoryFlag.advisory_note must be non-empty")
        if list(self.related_ids) != sorted(self.related_ids):
            raise ValueError(
                "AdvisoryFlag.related_ids must be lex-ASC sorted"
            )
        lint_advisory_text(
            self.advisory_note, field_name="AdvisoryFlag.advisory_note",
        )


# ============================================================
# § 16 — TradeoffSession (the top-level container — spec § 2.1)
# ============================================================

@dataclass(frozen=True)
class TradeoffSession:
    """The full negotiation session state.

    Per spec § 2.1 v0.2 clarifying note + R16:
      session_history is append-only single-linear-history in v1.0.
      Multi-branch / parallel-universe / multi-user is v1.x.

    Per R8: c3b_schema_version must match C3B_SESSION_SCHEMA_VERSION.
    """
    session_id:                     str
    source_selection_result_id:     str
    source_brief_signature:         str
    source_plot_analysis_id:        str
    c3b_version:                    str
    c3b_schema_version:             int
    jurisdiction_profile_id:        str

    tweak_option_sets:              Tuple[TweakOptionSet, ...]
    session_history:                Tuple[SessionTurn, ...]
    iteration_count:                int
    iteration_cap:                  int
    current_status:                 SessionStatus

    canonical_replay_signature:     str
    presentation_signature:         str
    schema_descriptor_digest:       str

    resolved_selection:             Optional[ResolvedSelection] = None
    advisory_flags:                 Tuple[AdvisoryFlag, ...] = ()
    mutation_envelopes:             Tuple[MutationEnvelope, ...] = ()
    """HEAVY tweaks generated during Phase β that got buffered for
    later use (e.g., user later asks something matching the pattern)."""

    # v0.5 A2 — periodic full-coherence recheck counter. Increments on
    # each MEDIUM tweak applied; resets on resolution. When crosses
    # full_recompute_threshold, the next subset_rerun is escalated to
    # a full recompute and a "full_coherence_recheck_triggered"
    # advisory is emitted.
    medium_tweak_count_since_full_recompute: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("TradeoffSession.session_id must be non-empty")
        if not self.source_selection_result_id:
            raise ValueError(
                "TradeoffSession.source_selection_result_id must be non-empty"
            )

        # R8 schema-version pin
        if self.c3b_schema_version != C3B_SESSION_SCHEMA_VERSION:
            raise ValueError(
                f"TradeoffSession.c3b_schema_version={self.c3b_schema_version} "
                f"!= C3B_SESSION_SCHEMA_VERSION={C3B_SESSION_SCHEMA_VERSION} "
                f"(R8 schema-version pin)"
            )

        # Version string pin
        if not self.c3b_version.startswith("v"):
            raise ValueError(
                f"TradeoffSession.c3b_version must look like 'vX.Y.Z'; "
                f"got {self.c3b_version!r}"
            )

        # iteration discipline
        if self.iteration_count < 0:
            raise ValueError(
                f"TradeoffSession.iteration_count must be >= 0; "
                f"got {self.iteration_count}"
            )
        if not (1 <= self.iteration_cap <= ITERATION_CAP_HARD_CEILING):
            raise ValueError(
                f"TradeoffSession.iteration_cap must be in [1, "
                f"{ITERATION_CAP_HARD_CEILING}]; got {self.iteration_cap}"
            )

        # v0.5 A2 — full-recompute counter discipline
        if self.medium_tweak_count_since_full_recompute < 0:
            raise ValueError(
                f"TradeoffSession.medium_tweak_count_since_full_recompute "
                f"must be >= 0; got {self.medium_tweak_count_since_full_recompute}"
            )

        # v0.5 R18 — counter resets on terminal resolution
        if self.current_status in (
            "resolved_selection_ready",
            "abandoned_no_tweaks",
            "kicked_back_to_c3a",
        ) and self.medium_tweak_count_since_full_recompute != 0:
            raise ValueError(
                f"TradeoffSession R18 invariant violated: "
                f"medium_tweak_count_since_full_recompute="
                f"{self.medium_tweak_count_since_full_recompute} must be 0 "
                f"when current_status={self.current_status!r}"
            )

        # session_history hard ceiling
        if len(self.session_history) > SESSION_HISTORY_HARD_CEILING:
            raise ValueError(
                f"TradeoffSession.session_history exceeds hard ceiling "
                f"{SESSION_HISTORY_HARD_CEILING}; got {len(self.session_history)}"
            )

        # R16: session_history is append-only by iteration_index
        # (lex-ascending — incrementing turn order)
        for i, turn in enumerate(self.session_history):
            if turn.iteration_index != i:
                # Allow gaps for rejected/no_action turns that don't
                # increment iteration_count — but iteration_index of
                # each turn must equal its position in history
                # (single-linear-history discipline)
                raise ValueError(
                    f"TradeoffSession.session_history[{i}].iteration_index "
                    f"={turn.iteration_index} != position {i} "
                    f"(R16 single-linear-history discipline)"
                )

        # tweak_option_sets lex-ASC by layout_id
        layout_ids = [s.layout_id for s in self.tweak_option_sets]
        if layout_ids != sorted(layout_ids):
            raise ValueError(
                "TradeoffSession.tweak_option_sets must be lex-ASC by "
                "layout_id"
            )

        # current_status ↔ resolved_selection coherence
        if (
            self.current_status == "resolved_selection_ready"
            and self.resolved_selection is None
        ):
            raise ValueError(
                "TradeoffSession: current_status='resolved_selection_ready' "
                "requires resolved_selection to be populated"
            )

        # advisory_flags lex-ASC by flag_id (R6)
        flag_ids = [f.flag_id for f in self.advisory_flags]
        if flag_ids != sorted(flag_ids):
            raise ValueError(
                "TradeoffSession.advisory_flags must be lex-ASC by flag_id"
            )

        # mutation_envelopes lex-ASC by envelope_id (R6)
        envelope_ids = [e.envelope_id for e in self.mutation_envelopes]
        if envelope_ids != sorted(envelope_ids):
            raise ValueError(
                "TradeoffSession.mutation_envelopes must be lex-ASC by "
                "envelope_id"
            )


# ============================================================
# § 17 — Public surface
# ============================================================

SCHEMA_MODULE_VERSION: Final[str] = "v0.4.LOCKED.s52"





# ══════════════════════════════════════════════════════════════════════════════
# § cache_keys                                                  
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Post-Layout Trade-off Negotiation — canonical hashing (R6/R7/R8)
========================================================================

Spec: C3b v0.4.LOCKED § 7 R6/R7/R8. Build session: S52.

Three deterministic signatures pinning replay identity, presentation
identity, and schema shape:

  canonical_replay_signature  — R6  — byte-equal given same inputs +
                                       same user-action sequence
  presentation_signature      — R7  — derived (canonical as prefix)
  schema_descriptor_digest    — R8  — schema-version stable; invariant
                                       to data values

Inheritance pattern from C17 v0.3 LOCKED (which inherited from C16
v1.2 LOCKED). The C17 cache_keys module passed S51's R6 byte-equal
10-run replay test; C3b mirrors that pattern.

Per spec § 3 Phase δ:
  Compute canonical_replay_signature (R6), presentation_signature (R7),
  schema_descriptor_digest (R8) at session emit time. Re-compute at
  Phase ζ resolution.

Rule 11 self-analysis (worst issues hunted):
  1. _canon walks Python objects recursively. We round floats to 6
     decimals (CANONICAL_FLOAT_DECIMALS) to dodge ULP-level
     nondeterminism. Tested against random-seeded inputs in test_cache_keys.
  2. strict_mode IS part of canonical_replay_signature — running the
     same session in strict vs warn produces different signatures by
     design (warn may have collected per-tweak failures, strict may
     have halted earlier). Documented.
  3. schema_descriptor_digest is over dataclass FIELD NAMES + TYPES,
     not values. Adding a field bumps the digest; renaming bumps it;
     reordering DOES NOT (we sort fields lexicographically before hash).
  4. presentation_signature in v1.0 is a derived hash with the
     canonical_replay_signature as input — narrowed R15 (matches C17
     v0.3). v1.x may expand to encode presentation-only state
     (UI scroll position, etc.) separately; not v1.0.
  5. session_id is INCLUDED in canonical_replay_signature inputs
     because different sessions produce different signatures even
     for identical inputs — sessions are intentionally individuated.
     If we ever needed input-only fingerprinting (cache lookup), that
     would be a separate `compute_input_fingerprint` (not yet needed).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

from .versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    CANONICAL_FLOAT_DECIMALS,
    SIGNATURE_HEX_LENGTH,
)

# Schema introspection imports — must be evaluated at module load to
# stabilize schema_descriptor_digest across the process lifetime
from .schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)


# ============================================================
# § 1 — Canonicalization helper
# ============================================================

def _canon(value: Any) -> Any:
    """Recursively canonicalize a Python value to a hash-friendly,
    deterministic representation:

      - dict   → sorted by key, then recursive _canon on values
      - tuple  → list (recursive _canon)
      - list   → list (recursive _canon)
      - set    → sorted list (recursive _canon)
      - float  → rounded to CANONICAL_FLOAT_DECIMALS (6)
      - bool   → bool (not int — JSON-distinct)
      - dataclass → asdict + recurse
      - enum   → its .value (StrEnum: the string)
      - None   → None
      - other  → its str() — last-resort; rare in our domain
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return round(value, CANONICAL_FLOAT_DECIMALS)
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    if isinstance(value, set):
        return sorted([_canon(v) for v in value], key=lambda x: str(x))
    if dataclasses.is_dataclass(value):
        # Convert the dataclass to a dict then canonicalize
        return _canon(dataclasses.asdict(value))
    # StrEnum/Enum
    if hasattr(value, "value") and not callable(value.value):
        return _canon(value.value)
    # Last resort
    return str(value)


def _sha256_hex(obj: Any) -> str:
    """Stable sha256 hex digest of a canonicalized object."""
    canonical = _canon(obj)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ============================================================
# § 2 — R6: canonical_replay_signature
# ============================================================

def compute_canonical_replay_signature(
    *,
    session: TradeoffSession,
    strict_mode: str,
) -> str:
    """R6 byte-equal replay signature.

    Inputs to the hash:
      - session_id (intentional individuation)
      - C3B_VERSION + schema_version (R8 inheritance)
      - strict_mode (different mode → different replay)
      - all tweak_option_sets (canonicalized)
      - all session_history turns (R12 audit-trail discipline,
        BUT v0.5 R17: strategic_advisory_text excluded)
      - iteration_count + iteration_cap
      - current_status
      - resolved_selection (None or canonicalized)
      - advisory_flags
      - mutation_envelopes
      - medium_tweak_count_since_full_recompute (v0.5 A2 — affects
        future branching, so part of replay state)

    NOT included:
      - canonical_replay_signature itself (recursion)
      - presentation_signature, schema_descriptor_digest (derived)
      - SessionTurn.strategic_advisory_text (R17 — informational only,
        produced by external provider, must not affect replay sigs)
    """
    # v0.5 R17 — strip strategic_advisory_text from each turn before
    # canonicalizing. Build a list of "signature-relevant turn" dicts.
    sig_turns = []
    for t in session.session_history:
        turn_dict = {
            "turn_id":              t.turn_id,
            "iteration_index":      t.iteration_index,
            "timestamp_offset_ms":  t.timestamp_offset_ms,
            "presented_tweaks":     t.presented_tweaks,
            "user_action":          t.user_action,
            "chosen_tweak_id":      t.chosen_tweak_id,
            "apply_outcome":        t.apply_outcome,
            "post_turn_status":     t.post_turn_status,
            # NOTE: strategic_advisory_text intentionally excluded (R17)
        }
        sig_turns.append(turn_dict)

    payload = {
        "session_id":                    session.session_id,
        "source_selection_result_id":    session.source_selection_result_id,
        "source_brief_signature":        session.source_brief_signature,
        "source_plot_analysis_id":       session.source_plot_analysis_id,
        "c3b_version":                   session.c3b_version,
        "c3b_schema_version":            session.c3b_schema_version,
        "jurisdiction_profile_id":       session.jurisdiction_profile_id,
        "strict_mode":                   strict_mode,
        "tweak_option_sets":             _canon(session.tweak_option_sets),
        "session_history":               _canon(sig_turns),
        "iteration_count":               session.iteration_count,
        "iteration_cap":                 session.iteration_cap,
        "current_status":                session.current_status,
        "resolved_selection":            _canon(session.resolved_selection),
        "advisory_flags":                _canon(session.advisory_flags),
        "mutation_envelopes":            _canon(session.mutation_envelopes),
        # v0.5 A2 — full-recompute counter affects future branching
        "medium_tweak_count_since_full_recompute": (
            session.medium_tweak_count_since_full_recompute
        ),
    }
    return _sha256_hex(payload)


# ============================================================
# § 3 — R7: presentation_signature
# ============================================================

def compute_presentation_signature(*, canonical_replay_signature: str) -> str:
    """R7 presentation signature.

    v1.0 narrowed R15: presentation_signature is a derived hash of the
    canonical_replay_signature plus a 'presentation' domain tag. This
    matches C17 v0.3's pattern.

    v1.x may extend to encode UI-specific state separately (B-C3B-
    DOWNSTREAM-RENDERER-BEHAVIORAL-CONTRACT in backlog § 9.2)."""
    if not canonical_replay_signature:
        raise ValueError(
            "compute_presentation_signature: canonical_replay_signature "
            "must be non-empty"
        )
    payload = {
        "canonical_replay": canonical_replay_signature,
        "presentation_v":   C3B_VERSION,
        "domain":           "c3b_presentation",
    }
    return _sha256_hex(payload)


# ============================================================
# § 4 — R8: schema_descriptor_digest
# ============================================================

_SCHEMA_DATACLASSES = (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)


def _describe_dataclass(cls: type) -> dict:
    """Schema descriptor for ONE dataclass — its fields, sorted by name,
    each with its type annotation as a string. This is value-invariant
    by design (R8)."""
    fields = []
    for f in sorted(dataclasses.fields(cls), key=lambda x: x.name):
        # Use string-form of annotation; works for Literal[...] / tuple[...] etc.
        type_str = str(f.type) if not isinstance(f.type, str) else f.type
        fields.append({"name": f.name, "type": type_str})
    return {"name": cls.__name__, "fields": fields}


def compute_schema_descriptor_digest() -> str:
    """R8 schema descriptor digest.

    Stable across runs given the same set of dataclass definitions.
    Bumps when:
      - A field is added or removed
      - A field is renamed
      - A field's type annotation changes
    Does NOT bump when:
      - Field order in source changes (we sort)
      - Field values change
      - Dataclass docstrings change
    """
    descriptors = [
        _describe_dataclass(cls)
        for cls in sorted(_SCHEMA_DATACLASSES, key=lambda c: c.__name__)
    ]
    payload = {
        "schema_descriptors": descriptors,
        "schema_version":     C3B_SESSION_SCHEMA_VERSION,
        "component":          "c3b",
    }
    return _sha256_hex(payload)


# ============================================================
# § 5 — Convenience helpers for tests
# ============================================================

def is_valid_signature(sig: str) -> bool:
    """A signature is 64 hex chars (sha256)."""
    if not isinstance(sig, str) or len(sig) != SIGNATURE_HEX_LENGTH:
        return False
    try:
        int(sig, 16)
    except ValueError:
        return False
    return True





# ══════════════════════════════════════════════════════════════════════════════
# § phases.tables                                               
# ══════════════════════════════════════════════════════════════════════════════
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





# ══════════════════════════════════════════════════════════════════════════════
# § phases.severity                                             
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Per-instance severity computation (spec § 3 Phase β step 4.2)
====================================================================

v0.2 patch: severity is computed per-instance using a context vector,
NOT statically from category. The same tweak category can be different
severities in different contexts (door in load-bearing wall vs partition
wall; room_resize within a bay vs crossing a bay).

The six context factors (spec § 3 Phase β step 4.2):
  1. Load-bearing wall involvement (within LOAD_BEARING_PROXIMITY_MM)
  2. Circulation graph impact (adds/removes node or edge)
  3. Wet-zone stack interaction
  4. Structural-bay boundary crossing
  5. Topology classification change → AUTO-PROMOTE TO HEAVY per R13
  6. External-wall change

Promotion rules:
  - 1 factor crossing threshold → promote 1 tier (L→M or M→H)
  - 2+ factors → MEDIUM tweaks auto-promote to HEAVY directly
  - Topology change (R13) → AUTO-HEAVY regardless of other factors

Rule 11 self-analysis:
  1. The "promotion by 1 tier" rule means LIGHT + 1 factor = MEDIUM,
     and MEDIUM + 1 factor stays MEDIUM (since MEDIUM + 1 only promotes
     by 1, ending at MEDIUM unless 2+ factors fire). The "2+ factors"
     rule explicitly handles MEDIUM → HEAVY. Tests cover both paths.
  2. Topology check (factor 5) is special — it ALWAYS produces HEAVY
     when triggered, bypassing the count-based rule. This matches the
     R13 contract: topology change is not a tweak.
  3. Context detection here is HEURISTIC. False negatives (missing a
     factor that should fire) bias toward more-MEDIUM-than-correct,
     which is the safer direction (we propose a rerun unnecessarily
     vs missing a rerun that was needed). False positives bias toward
     HEAVY (refused tweaks). Documented; B-C3B-FORMAL-MUTATION-ENVELOPE-GRAPH
     (v1.x) will replace with formal proof reasoning.
  4. R13 short-circuits: if topology check fires, we exit early — we
     do not also count it as 1-of-6. This avoids double-counting and
     keeps the "topology change = HEAVY" rule clear.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..contracts import (
    DoorPlacement,
    PlacedRoom,
    PlotAnalysis,
    RiserGroup,
    StructuralGrid,
)
from ..schema import (
    PredictionBasis,
    SeverityTier,
    TopologyClassification,
    TopologyInvarianceResult,
    TweakCategory,
)
from ..versioning import LOAD_BEARING_PROXIMITY_MM
from .tables import TWEAK_CATEGORY_DEFAULT_SEVERITY


# ============================================================
# § 1 — Context vector
# ============================================================

@dataclass(frozen=True)
class SeverityContext:
    """The 6 contextual factors a candidate tweak may trigger.

    Each factor is a boolean; True means the factor crosses threshold
    and contributes to severity promotion."""
    load_bearing_wall_involvement:   bool = False
    circulation_graph_impact:        bool = False
    wet_zone_stack_interaction:      bool = False
    structural_bay_boundary_cross:   bool = False
    topology_classification_change:  bool = False  # R13 auto-HEAVY
    external_wall_change:            bool = False

    @property
    def factor_count(self) -> int:
        return sum([
            self.load_bearing_wall_involvement,
            self.circulation_graph_impact,
            self.wet_zone_stack_interaction,
            self.structural_bay_boundary_cross,
            self.external_wall_change,
            # NOTE: topology_classification_change NOT counted here —
            # it short-circuits to HEAVY directly (see promote_severity)
        ])

    def factor_names_triggered(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.load_bearing_wall_involvement:
            names.append("load_bearing_wall_involvement")
        if self.circulation_graph_impact:
            names.append("circulation_graph_impact")
        if self.wet_zone_stack_interaction:
            names.append("wet_zone_stack_interaction")
        if self.structural_bay_boundary_cross:
            names.append("structural_bay_boundary_cross")
        if self.topology_classification_change:
            names.append("topology_classification_change")
        if self.external_wall_change:
            names.append("external_wall_change")
        return tuple(names)


# ============================================================
# § 2 — Context detection (heuristic — see Rule 11 self-analysis pt 3)
# ============================================================

def detect_load_bearing_proximity(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    structural_grid:    StructuralGrid,
) -> bool:
    """Returns True if any affected room sits on or within
    LOAD_BEARING_PROXIMITY_MM of a load-bearing perimeter cell."""
    affected_set = set(affected_room_ids)
    if not affected_set:
        return False
    # Build room → bay_ids map
    affected_bay_ids: set[str] = set()
    for room in placed_rooms:
        if room.room_id in affected_set:
            affected_bay_ids.update(room.structural_bay_ids)
    if not affected_bay_ids:
        return False
    # Any of those bays load-bearing?
    for cell in structural_grid.cells:
        if cell.cell_id in affected_bay_ids and cell.is_load_bearing_perimeter:
            return True
    return False


def detect_bay_boundary_crossing(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> bool:
    """Returns True if any affected room straddles 2+ structural bays
    (room_resize across a bay boundary is a structural impact)."""
    affected_set = set(affected_room_ids)
    for room in placed_rooms:
        if room.room_id in affected_set and len(room.structural_bay_ids) >= 2:
            return True
    return False


def detect_wet_zone_interaction(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    riser_groups:       tuple[RiserGroup, ...],
) -> bool:
    """Returns True if any affected room is served by a riser group OR
    is spatially adjacent to one. Adjacency uses adjacent_room_ids."""
    affected_set = set(affected_room_ids)
    # Direct: affected room is in a riser group
    served_rooms: set[str] = set()
    for rg in riser_groups:
        served_rooms.update(rg.served_room_ids)
    if affected_set & served_rooms:
        return True
    # Indirect: affected room is adjacent to a riser-served room
    affected_adjacents: set[str] = set()
    for room in placed_rooms:
        if room.room_id in affected_set:
            affected_adjacents.update(room.adjacent_room_ids)
    if affected_adjacents & served_rooms:
        return True
    return False


def detect_external_wall_change(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    tweak_category:     TweakCategory,
) -> bool:
    """Returns True if the tweak touches a room with an external wall.
    Window/balcony tweaks are the prototypical triggers."""
    # Tweaks that intrinsically touch envelope:
    envelope_categories = {
        "balcony_add", "balcony_remove", "window_resize",
    }
    if tweak_category in envelope_categories:
        return True
    # Other tweaks: only count if the affected room has external_wall
    affected_set = set(affected_room_ids)
    for room in placed_rooms:
        if room.room_id in affected_set and room.has_external_wall:
            return True
    return False


def detect_circulation_graph_impact(
    *,
    tweak_category:     TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    door_placements:    tuple[DoorPlacement, ...],
) -> bool:
    """Returns True if the tweak adds/removes a circulation graph
    node or edge. Door tweaks change edges; room tweaks may change
    both nodes and edges."""
    # Tweaks that always touch circulation:
    if tweak_category in {"door_relocate", "room_swap", "utility_zone_carveout"}:
        return True
    # Tweaks that may touch circulation if they affect a multi-door room:
    affected_set = set(affected_room_ids)
    affected_door_count = sum(
        1 for d in door_placements
        if d.room_a_id in affected_set or d.room_b_id in affected_set
    )
    if tweak_category in {"room_resize", "storage_add"} and affected_door_count >= 2:
        return True
    return False


def predict_topology_invariance(
    *,
    tweak_category:     TweakCategory,
    source_topology:    TopologyClassification,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> TopologyInvarianceResult:
    """Predict whether the tweak preserves C5 topology classification.

    Per spec § 2.4.2 + R13:
      - Topology-defining elements: corridors, central spine, courtyard
        void, perimeter envelope
      - mutation_local_only: tweak doesn't touch topology-defining elements
      - heuristic_weak: ambiguous; safety-bias to HEAVY (invariance=False)
    """
    # Categorize tweak by topology-touch likelihood
    # Tweaks that essentially never alter topology:
    topology_safe_categories = {
        "finish_upgrade", "finish_downgrade",
        "window_resize",
        "balcony_add", "balcony_remove",   # balconies don't alter the topology of the interior plan
    }
    # Tweaks that may alter topology only if they touch corridor/spine:
    topology_sensitive_categories = {
        "door_relocate",        # changing main door could change topology
        "room_swap",
        "room_resize",
        "utility_zone_carveout", # carves from corridor — could alter spine
        "storage_add",
        "pooja_relocate",
        "kitchen_reorient",
        "wet_zone_restage",
    }

    if tweak_category in topology_safe_categories:
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=source_topology,
            invariance_preserved=True,
            prediction_basis="mutation_local_only",
            advisory_note=None,
        )

    if tweak_category not in topology_sensitive_categories:
        # Unknown category — safety bias to weak prediction (HEAVY)
        # Map source to a different topology to make invariance_preserved=False
        # consistent. Pick l_shape as a generic "different" topology.
        not_source = "l_shape" if source_topology != "l_shape" else "central_spine"
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=not_source,
            invariance_preserved=False,
            prediction_basis="heuristic_weak",
            advisory_note=(
                "Unrecognized tweak category. Routing to a different pathway "
                "as a precaution."
            ),
        )

    # Topology-sensitive category — check what's affected
    # Heuristic: if the affected room set includes corridor/lobby/stair,
    # topology may change. Otherwise mutation_local_only.
    affected_set = set(affected_room_ids)
    topology_defining_functions = {"corridor", "stair", "lift_lobby", "lobby"}
    touches_topology = any(
        r.room_id in affected_set
        and r.room_function in topology_defining_functions
        for r in placed_rooms
    )
    if touches_topology:
        # Strong signal — predict topology DOES change
        not_source = "l_shape" if source_topology != "l_shape" else "central_spine"
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=not_source,
            invariance_preserved=False,
            prediction_basis="circulation_pattern_invariant",
            advisory_note=(
                "This tweak touches a circulation-defining element "
                "(corridor / stair / lobby). Reclassifying as a topology change."
            ),
        )

    # Mutation doesn't touch topology-defining elements
    return TopologyInvarianceResult(
        source_topology=source_topology,
        predicted_topology=source_topology,
        invariance_preserved=True,
        prediction_basis="structural_grid_invariant",
        advisory_note=None,
    )


# ============================================================
# § 3 — Severity promotion (the rules)
# ============================================================

def promote_severity(
    *,
    default_severity:  SeverityTier,
    context:           SeverityContext,
) -> SeverityTier:
    """Apply the spec § 3 Phase β step 4.2 promotion rules.

    Returns the final severity. Order of precedence:
      1. Topology change → AUTO-HEAVY (R13)
      2. ≥2 factors AND default is MEDIUM → HEAVY
      3. ≥1 factor → promote by 1 tier
      4. Otherwise → default
    """
    # R13: topology change is auto-HEAVY regardless
    if context.topology_classification_change:
        return "heavy"

    factor_count = context.factor_count

    if factor_count == 0:
        return default_severity

    # ≥2 factors with MEDIUM default → HEAVY
    if factor_count >= 2 and default_severity == "medium":
        return "heavy"

    # ≥1 factor with LIGHT default → MEDIUM
    if default_severity == "light":
        return "medium"

    # MEDIUM + 1 factor stays MEDIUM (per spec promotion-by-1-tier)
    if default_severity == "medium":
        return "medium"

    # HEAVY default stays HEAVY
    return default_severity


def detect_context_for_tweak(
    *,
    tweak_category:     TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    structural_grid:    StructuralGrid,
    riser_groups:       tuple[RiserGroup, ...],
    door_placements:    tuple[DoorPlacement, ...],
    topology_invariance: Optional[TopologyInvarianceResult] = None,
) -> SeverityContext:
    """Compute the full SeverityContext for a candidate tweak.

    The 6 factors:
      1. load_bearing_wall_involvement
      2. circulation_graph_impact
      3. wet_zone_stack_interaction
      4. structural_bay_boundary_cross
      5. topology_classification_change (from R13 prediction)
      6. external_wall_change
    """
    return SeverityContext(
        load_bearing_wall_involvement=detect_load_bearing_proximity(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            structural_grid=structural_grid,
        ),
        circulation_graph_impact=detect_circulation_graph_impact(
            tweak_category=tweak_category,
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            door_placements=door_placements,
        ),
        wet_zone_stack_interaction=detect_wet_zone_interaction(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            riser_groups=riser_groups,
        ),
        structural_bay_boundary_cross=detect_bay_boundary_crossing(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
        ),
        topology_classification_change=(
            topology_invariance is not None
            and not topology_invariance.invariance_preserved
        ),
        external_wall_change=detect_external_wall_change(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            tweak_category=tweak_category,
        ),
    )





# ══════════════════════════════════════════════════════════════════════════════
# § phases.alpha                                                
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase α — Session canonicalization + applicability check
================================================================

Spec § 3 Phase α:
  INPUT: SelectionResult, Brief, PlotAnalysis (via C3bInputBundle)
  PROCESSING:
    1. Validate SelectionResult.layouts is exactly 3 candidates
    2. Check § 1.4 applicability boundary:
       - Preview Mode? (ResolvedBrief.extreme_case_status == 'preview_mode')
       - high_ambiguity ProblemReport?
       - Pareto collapse (layouts too similar)?
    3. If any check fails → emit TradeoffSession with
       current_status='abandoned_no_tweaks' + advisory
    4. Otherwise → build canonical TradeoffSession skeleton with
       iteration_count=0

  OUTPUT: TradeoffSession (skeleton or terminal)

Rule 11 self-analysis:
  1. Applicability failure produces a SESSION not an exception.
     ApplicabilityBoundaryError exists for unit-testing the code path,
     but the runtime path is the session-with-advisory. Documented in
     errors.py.
  2. Pareto collapse uses PARETO_DIVERSITY_FLOOR_* — if ANY ONE floor
     is met (sqft 10% OR cost 15% OR 3 distinct topologies), the
     layouts are "diverse enough." Conservative: if any one floor met,
     applicability passes.
  3. Layout archetype assignment (Cost Efficient / Everyday Living /
     Premium Design) is by rank position:
       rank 0 → cost_efficient
       rank 1 → everyday_living
       rank 2 → premium_design
     This matches Design Principles v3.1 § 5 Layout Triad ordering.
     If C15's ranking changes ordering convention in the future, this
     mapping is the seam to update.
  4. Phase α does NOT compute tweak_option_sets — that's Phase β.
     The session skeleton has empty tweak_option_sets; status is
     "open_for_user_input" only after Phase β/γ/δ populate them.
     We use an INTERMEDIATE skeleton status that we replace later;
     for now, use "open_for_user_input" with empty sets and let Phase β
     fill in.
"""
from __future__ import annotations

import uuid
from typing import Optional

from ..cache_keys import (
    compute_canonical_replay_signature,
    compute_presentation_signature,
    compute_schema_descriptor_digest,
)
from ..config import C3bRuntimeConfig
from ..contracts import C3bInputBundle
from ..errors import (
    ApplicabilityBoundaryError,
    C3bConfigurationError,
    UpstreamSchemaDriftError,
)
from ..schema import (
    LayoutArchetype,
    SessionStatus,
    TradeoffSession,
)
from ..versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    EXPECTED_C15_VERSION,
    EXPECTED_LAYOUT_COUNT,
    PARETO_DIVERSITY_FLOOR_COST_PCT,
    PARETO_DIVERSITY_FLOOR_SQFT_PCT,
    PARETO_DIVERSITY_FLOOR_TOPOLOGY_COUNT,
    SUPPORTED_JURISDICTIONS,
    SUPPORTED_DOMAIN_SCOPES,
)


# ============================================================
# § 1 — Layout archetype assignment
# ============================================================

def archetype_for_rank(rank_position: int) -> LayoutArchetype:
    """Map C16 rank position → Design Principles v3.1 Layout Triad.
    C16 rank_position is 1-indexed (1, 2, 3)."""
    if rank_position == 1:
        return "cost_efficient"
    if rank_position == 2:
        return "everyday_living"
    if rank_position == 3:
        return "premium_design"
    raise C3bConfigurationError(
        f"rank_position={rank_position} outside Layout Triad (1-3). "
        f"C16 SelectionResult must contain exactly {EXPECTED_LAYOUT_COUNT} "
        f"ranked candidates.",
        offending_field="rank_position",
        offending_value=rank_position,
    )


# ============================================================
# § 2 — Applicability checks (spec § 1.4)
# ============================================================

def check_preview_mode(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if Preview Mode detected, else None."""
    if bundle.resolved_brief.extreme_case_status == "preview_mode":
        return (
            "This layout was produced under Preview Mode (an unresolved extreme "
            "case in your brief). C3b can iterate on tweaks once the extreme "
            "case is resolved. You could revisit the brief, resolve the extreme, "
            "and re-run the layout pipeline."
        )
    return None


def check_pareto_diversity(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if Pareto-front collapse detected, else None.

    Layouts are 'diverse enough' if ANY ONE floor is met:
      - sqft varies by >= 10%
      - cost varies by >= 15%
      - 3 distinct topology classifications represented
      - (v0.5 A9) at least 2 distinct functional archetypes
        (cost_efficient / everyday_living / premium_design)
    """
    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if len(rankings) != EXPECTED_LAYOUT_COUNT:
        return (
            f"The layout pipeline produced {len(rankings)} candidates rather "
            f"than the expected {EXPECTED_LAYOUT_COUNT}. You could re-run the "
            f"layout generation or revisit your brief."
        )

    # v0.5 A9 — archetype diversity floor. Map rank → archetype via the
    # standard Triad. If C16 ranks rank_position 1..3, archetypes are
    # (cost_efficient, everyday_living, premium_design). If C16 emits
    # 3 rankings with the same rank_position triple, archetype diversity
    # passes by construction (3 archetypes for 3 layouts). The floor
    # trips only if a future C16 evolution returns degenerate rankings.
    archetypes_seen: set[str] = set()
    for r in rankings:
        if 1 <= r.rank_position <= 3:
            archetype = {1: "cost_efficient", 2: "everyday_living", 3: "premium_design"}[r.rank_position]
            archetypes_seen.add(archetype)
    if len(archetypes_seen) >= 2:
        return None  # archetype diversity passes

    # cost diversity (use 'score' as proxy when no explicit cost — heuristic
    # for v1.0; v1.x will read actual cost from each layout's cost report)
    scores = [r.score for r in rankings]
    if max(scores) > 0:
        cost_spread_pct = (max(scores) - min(scores)) / max(scores) * 100.0
    else:
        cost_spread_pct = 0.0
    if cost_spread_pct >= PARETO_DIVERSITY_FLOOR_COST_PCT:
        return None  # diverse enough

    # sqft diversity — heuristic: use placed_rooms totals
    sqft_totals: list[float] = []
    for placed_rooms in bundle.placed_rooms_per_layout:
        total = sum(r.geometry.area_sqft for r in placed_rooms)
        sqft_totals.append(total)
    if sqft_totals and max(sqft_totals) > 0:
        sqft_spread_pct = (max(sqft_totals) - min(sqft_totals)) / max(sqft_totals) * 100.0
    else:
        sqft_spread_pct = 0.0
    if sqft_spread_pct >= PARETO_DIVERSITY_FLOOR_SQFT_PCT:
        return None  # diverse enough

    # Topology diversity — would require C5 topology classifications per layout.
    # We don't have those directly; defer to v1.x. For v1.0, fall through if
    # neither cost nor sqft diversity met.
    return (
        "The three ranked layouts came back very similar to each other "
        "(within 15% on cost and 10% on sqft, and with limited archetype "
        "spread). C3b's tweak suggestions need diverse layouts to be useful. "
        "You could explore a different brief configuration or accept one of "
        "the layouts as-is."
    )


def check_high_ambiguity(bundle: C3bInputBundle) -> Optional[str]:
    """Return advisory note if any ProblemReport has low coverage_quality
    (high ambiguity), else None.

    C15's CoverageQuality enum is the gate. We refuse to iterate when
    the underlying problem detection has high uncertainty."""
    # CoverageQuality is an enum; the lowest tier is "low_signal" (high
    # ambiguity). Specific name varies by C15 — we check via .value
    for i, pr in enumerate(bundle.problem_reports):
        try:
            quality_str = pr.coverage_quality.value
        except AttributeError:
            quality_str = str(pr.coverage_quality)
        if "low" in quality_str.lower() or "ambig" in quality_str.lower():
            return (
                f"Layout {i+1}'s problem report came back with low confidence "
                f"({quality_str}). C3b's tweaks rely on confident problem "
                f"detection. You could re-run the layout pipeline or accept "
                f"the layouts as-is."
            )
    return None


# ============================================================
# § 3 — Upstream version check
# ============================================================

def check_upstream_versions(bundle: C3bInputBundle) -> None:
    """Verify upstream-component versions meet semantic-compatibility
    contracts.

    v0.5 A1: replaces exact-equality pinning with version_at_or_above
    semantic check. Raises UpstreamSchemaDriftError when observed <
    min_required, or when observed is in
    KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS.
    """
    from ..versioning import (
        KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS,
        MIN_C15_VERSION,
        version_at_or_above,
    )
    if bundle.problem_reports:
        observed = bundle.problem_reports[0].c15_version
        # Check known-incompatible list first (explicit refusals)
        for component, bad_version in KNOWN_INCOMPATIBLE_UPSTREAM_VERSIONS:
            if component == "c15" and observed == bad_version:
                raise UpstreamSchemaDriftError(
                    f"C15 version {observed!r} is on KNOWN_INCOMPATIBLE list; "
                    f"explicit refusal.",
                    expected_version=MIN_C15_VERSION,
                    observed_version=observed,
                    upstream="c15",
                )
        # Semantic-compatibility (>= min) check
        if not version_at_or_above(observed, MIN_C15_VERSION):
            raise UpstreamSchemaDriftError(
                f"C15 version drift: observed {observed!r} is below the "
                f"minimum compatible version {MIN_C15_VERSION!r}.",
                expected_version=MIN_C15_VERSION,
                observed_version=observed,
                upstream="c15",
            )
    # C16 / C7 / C12 etc. have stub-version markers; not checked at runtime
    # since stubs themselves don't carry a version-mismatch concept.


# ============================================================
# § 4 — Configuration validation
# ============================================================

def check_configuration(bundle: C3bInputBundle, config: C3bRuntimeConfig) -> None:
    """Verify jurisdiction + domain scope are supported. Raises
    C3bConfigurationError on mismatch."""
    jp_id = bundle.resolved_brief.jurisdiction_profile_id
    # Allow exact match OR prefix match against any supported jurisdiction
    supported_match = any(
        sj in jp_id or jp_id.startswith(sj) for sj in SUPPORTED_JURISDICTIONS
    )
    if not supported_match:
        raise C3bConfigurationError(
            f"Jurisdiction {jp_id!r} not in SUPPORTED_JURISDICTIONS "
            f"{set(SUPPORTED_JURISDICTIONS)!r}. v1.0 supports Chennai (TN CDBR 2019).",
            offending_field="jurisdiction_profile_id",
            offending_value=jp_id,
        )


# ============================================================
# § 5 — Build session skeleton
# ============================================================

def _build_terminal_session(
    *,
    bundle:         C3bInputBundle,
    config:         C3bRuntimeConfig,
    status:         SessionStatus,
    advisory_note:  str,
) -> TradeoffSession:
    """Build a terminal TradeoffSession when applicability fails.

    The session has:
      - empty tweak_option_sets
      - empty session_history
      - resolved_selection = None
      - one AdvisoryFlag with kind='pareto_diversity_floor_borderline'
        OR 'topology_invariance_weak_basis' (closest fit) describing
        the failure
      - signatures computed at this terminal state
    """
    from ..schema import AdvisoryFlag

    session_id = "sess_" + uuid.uuid4().hex[:16]

    advisory = AdvisoryFlag(
        flag_id="flag_alpha_terminal",
        kind="pareto_diversity_floor_borderline",
        advisory_note=advisory_note,
        related_ids=(),
    )

    # Compute initial signatures (will be re-computed if state mutates)
    placeholder_sigs = {
        "canonical_replay_signature": "0" * 64,
        "presentation_signature":     "0" * 64,
        "schema_descriptor_digest":   compute_schema_descriptor_digest(),
    }

    # Build with placeholder signatures, then re-sign with real ones
    sess = TradeoffSession(
        session_id=session_id,
        source_selection_result_id=(
            bundle.selection_result.replay_identity.selected_layout_signature
        ),
        source_brief_signature=bundle.resolved_brief.brief_signature,
        source_plot_analysis_id=bundle.plot_analysis.plot_analysis_id,
        c3b_version=C3B_VERSION,
        c3b_schema_version=C3B_SESSION_SCHEMA_VERSION,
        jurisdiction_profile_id=bundle.resolved_brief.jurisdiction_profile_id,
        tweak_option_sets=(),
        session_history=(),
        iteration_count=0,
        iteration_cap=config.iteration_cap,
        current_status=status,
        canonical_replay_signature=placeholder_sigs["canonical_replay_signature"],
        presentation_signature=placeholder_sigs["presentation_signature"],
        schema_descriptor_digest=placeholder_sigs["schema_descriptor_digest"],
        resolved_selection=None,
        advisory_flags=(advisory,),
        mutation_envelopes=(),
    )

    return _resign_session(sess, config)


def _resign_session(
    session:      TradeoffSession,
    config:       C3bRuntimeConfig,
) -> TradeoffSession:
    """Re-compute R6/R7/R8 signatures for a session and return a new
    session with them set. Used after any state mutation."""
    canonical = compute_canonical_replay_signature(
        session=session, strict_mode=config.strict_mode,
    )
    presentation = compute_presentation_signature(
        canonical_replay_signature=canonical,
    )
    schema_digest = compute_schema_descriptor_digest()
    # Use dataclasses.replace to rebuild with new signatures
    import dataclasses
    return dataclasses.replace(
        session,
        canonical_replay_signature=canonical,
        presentation_signature=presentation,
        schema_descriptor_digest=schema_digest,
    )


# ============================================================
# § 6 — Phase α entry point
# ============================================================

def run_phase_alpha(
    bundle:  C3bInputBundle,
    config:  C3bRuntimeConfig,
) -> TradeoffSession:
    """Execute Phase α and return either:
      - a skeleton session (status='open_for_user_input', empty tweak sets)
        ready for Phase β to populate, OR
      - a terminal session (status='abandoned_no_tweaks') with an
        advisory explaining why applicability failed
    """
    # Configuration validation
    check_configuration(bundle, config)

    # Upstream version check
    check_upstream_versions(bundle)

    # Selection-result shape check
    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if len(rankings) != EXPECTED_LAYOUT_COUNT:
        return _build_terminal_session(
            bundle=bundle, config=config,
            status="abandoned_no_tweaks",
            advisory_note=(
                f"The layout pipeline produced {len(rankings)} candidates "
                f"rather than the expected {EXPECTED_LAYOUT_COUNT}. You could "
                f"re-run the layout generation."
            ),
        )

    # Applicability boundary checks
    for check_fn in (
        check_preview_mode,
        check_high_ambiguity,
        check_pareto_diversity,
    ):
        advisory_msg = check_fn(bundle)
        if advisory_msg is not None:
            return _build_terminal_session(
                bundle=bundle, config=config,
                status="abandoned_no_tweaks",
                advisory_note=advisory_msg,
            )

    # All checks passed — build skeleton session ready for Phase β
    session_id = "sess_" + uuid.uuid4().hex[:16]
    sess = TradeoffSession(
        session_id=session_id,
        source_selection_result_id=(
            bundle.selection_result.replay_identity.selected_layout_signature
        ),
        source_brief_signature=bundle.resolved_brief.brief_signature,
        source_plot_analysis_id=bundle.plot_analysis.plot_analysis_id,
        c3b_version=C3B_VERSION,
        c3b_schema_version=C3B_SESSION_SCHEMA_VERSION,
        jurisdiction_profile_id=bundle.resolved_brief.jurisdiction_profile_id,
        tweak_option_sets=(),   # Phase β fills
        session_history=(),
        iteration_count=0,
        iteration_cap=config.iteration_cap,
        current_status="open_for_user_input",
        canonical_replay_signature="0" * 64,    # re-signed below
        presentation_signature="0" * 64,
        schema_descriptor_digest=compute_schema_descriptor_digest(),
        resolved_selection=None,
        advisory_flags=(),
        mutation_envelopes=(),
    )
    return _resign_session(sess, config)





# ══════════════════════════════════════════════════════════════════════════════
# § phases.beta                                                 
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase β — Tweak generation per layout (v0.2 PATCHED)
=============================================================

Spec § 3 Phase β (v0.2 PATCHED — per-instance severity computation):

  INPUT: 3 layouts, 3 ProblemReports, PlotAnalysis
  PROCESSING (per layout):
    1. Read ProblemReport. Find checks with severity ∈ {critical, important}
       AND status == 'fail' that have a known tweak pattern.
    2. Read structural grid. Find under-utilized cells → utility_zone_carveout
       candidates.
    3. Read orientation (PlotAnalysis). Find function/orientation mismatches
       → kitchen_reorient / pooja_relocate candidates.
    4. Apply severity filter (PER-INSTANCE — v0.2 patched):
       4.1 Default severity from category
       4.2 Context-aware adjustment (6 factors)
       4.3 Final severity assignment
       4.4 Bounded selection (max 6 per layout)
    5. Generate plain-English description per Principle 1 + Principle 3
       (advisory tone, R2 banned-phrase lint)

  OUTPUT: 3 TweakOptionSets

This module is the heart of C3b. The static tables in `tables.py` and
the severity logic in `severity.py` drive it.

Rule 11 self-analysis:
  1. HEAVY tweaks are NOT included in TweakOptionSet.tweaks. Instead
     they're buffered as MutationEnvelopes attached to the session for
     later use (per spec § 3 Phase β step 4 final assignment).
  2. STRICT mode raises on per-tweak errors; WARN mode collects. The
     `errors_collected` return value lists per-tweak errors that fired
     in WARN mode.
  3. Bounded selection prioritizes by (a) addresses critical problem,
     (b) LIGHT severity, (c) recommendation_flag='suggested'. Documented.
  4. Tweak description generation uses a TEMPLATE library — every
     category has a deterministic template, parameterized by affected
     room IDs / categories. Template strings are pre-linted to ensure
     they don't contain banned phrases. Tests verify.
  5. `presented_count` always starts at 0 from Phase β; bumped only
     in Phase ε when a tweak is re-surfaced.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from buildemup.components.c15.schema import (
    CheckSeverity,
    CheckStatus,
    ProblemCheck,
    ProblemReport,
)
from buildemup.utils.confidence import Confidence
from buildemup.utils.transparency import DerivationLine, TransparencyTriple

from ..config import C3bRuntimeConfig
from ..contracts import (
    AttestedValue,
    AuthorityKind,
    C3bInputBundle,
    DoorPlacement,
    PlacedRoom,
    RiserGroup,
    StructuralGrid,
)
from ..errors import (
    ConstraintViolationError,
    PerTweakError,
    TweakGenerationError,
)
from ..schema import (
    ApplySpecification,
    ComfortImpact,
    CompatibilityAssertion,
    FinishSchedulePayload,
    GeometryLocalPayload,
    LayoutArchetype,
    MutationEnvelope,
    KickBackPayload,
    MutationClassification,
    RecommendationFlag,
    SeverityTier,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyClassification,
    TopologyInvarianceResult,
    TweakCategory,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)
from ..versioning import MAX_TWEAKS_PER_LAYOUT
from .severity import (
    SeverityContext,
    detect_context_for_tweak,
    predict_topology_invariance,
    promote_severity,
)
from .tables import (
    TWEAK_CATEGORY_COMFORT_PROFILE,
    TWEAK_CATEGORY_COMPONENTS_TO_RERUN,
    TWEAK_CATEGORY_COST_RANGE_INR,
    TWEAK_CATEGORY_DEFAULT_SEVERITY,
    TWEAK_CATEGORY_IMPACT_TABLE,
    TWEAK_CATEGORY_SPACE_DELTA_SQFT,
    lex_asc_components,
    lex_asc_impacts,
    lookup_tweak_categories_for_check,
)


# ============================================================
# § 1 — Tweak description templates (R2 advisory-tone enforced)
# ============================================================
# Per Principle 1 + Principle 3: advisory tone, talks to user not engine.
# Each template is pre-linted (see test_phase_beta.py).

_DESCRIPTION_TEMPLATES: dict[TweakCategory, str] = {
    "finish_upgrade": (
        "You could upgrade the finishes in {rooms} — typically vitrified "
        "tiles or premium flooring. This is a finish-only change with "
        "no structural impact."
    ),
    "finish_downgrade": (
        "You could reduce the finish grade in {rooms} to a more economical "
        "option. This is a finish-only change with no structural impact."
    ),
    "door_relocate": (
        "You could move a door in {rooms} to a different wall, improving "
        "circulation or addressing a clearance concern."
    ),
    "window_resize": (
        "You could resize a window in {rooms} for more natural light "
        "or cross-ventilation."
    ),
    "balcony_add": (
        "You could add a balcony to {rooms} — typically carved from the "
        "interior. This adds outdoor connection and improves ventilation."
    ),
    "balcony_remove": (
        "You could remove the balcony from {rooms} and reclaim the "
        "interior space."
    ),
    "storage_add": (
        "You could add storage (closet or built-in) to {rooms}. This carves "
        "a small amount of room area for storage capacity."
    ),
    "pooja_relocate": (
        "You could relocate the pooja room in {rooms}, typically toward "
        "the east. This aligns with traditional Vastu (opt-in) and gives "
        "morning light."
    ),
    "kitchen_reorient": (
        "You could reorient the kitchen in {rooms} toward the east. This "
        "improves morning light and cross-ventilation in Chennai's warm-"
        "humid climate."
    ),
    "wet_zone_restage": (
        "You could re-stage the wet zones (bath/kitchen) in {rooms} to "
        "align their vertical stacks. This reduces plumbing runs and "
        "long-term leak risk."
    ),
    "utility_zone_carveout": (
        "You could carve a utility zone from underutilized corridor or "
        "lobby space in {rooms}. This adds laundry or storage capacity."
    ),
    "room_swap": (
        "You could swap two rooms' functions in {rooms}. Same geometry, "
        "different functional layout — often improves privacy or flow."
    ),
    "room_resize": (
        "You could resize a room in {rooms}, redistributing area from "
        "or to neighboring spaces. Stays within the existing structural grid."
    ),
}


def _format_room_list(room_ids: tuple[str, ...]) -> str:
    """Friendly join: ('room_001', 'room_002') → 'room_001 and room_002'."""
    if not room_ids:
        return "the layout"
    if len(room_ids) == 1:
        return room_ids[0]
    if len(room_ids) == 2:
        return f"{room_ids[0]} and {room_ids[1]}"
    return f"{', '.join(room_ids[:-1])}, and {room_ids[-1]}"


def render_description(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
) -> str:
    """Render the user-facing description for a tweak category +
    affected rooms. Pre-linted templates."""
    template = _DESCRIPTION_TEMPLATES.get(category)
    if template is None:
        # Fallback that still passes lint
        return (
            f"This is a {category} tweak affecting "
            f"{_format_room_list(affected_room_ids)}."
        )
    return template.format(rooms=_format_room_list(affected_room_ids))


# ============================================================
# § 2 — Heuristic impact builders (Phase γ logic factored here)
# ============================================================

def _build_cost_impact(category: TweakCategory) -> TransparencyTriple:
    low, mid, high, uncertainty = TWEAK_CATEGORY_COST_RANGE_INR.get(
        category, (0.0, 0.0, 0.0, 50.0),
    )
    return TransparencyTriple(
        label=f"Cost impact for {category}",
        exact_value=mid,
        unit="INR",
        uncertainty_pct=uncertainty,
        confidence=Confidence.MEDIUM,
        derivation=[
            DerivationLine(
                label=f"{category} heuristic range",
                amount=mid,
                source="C3b v0.4 TWEAK_CATEGORY_COST_RANGE_INR (Chennai 2026 heuristic)",
            ),
            DerivationLine(
                label=f"Lower bound (-{uncertainty}%)", amount=low,
            ),
            DerivationLine(
                label=f"Upper bound (+{uncertainty}%)", amount=high,
            ),
        ],
        notes=[],
    )


def _build_space_impact(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> SpaceImpact:
    delta = TWEAK_CATEGORY_SPACE_DELTA_SQFT.get(category, 0.0)
    # Distribute the delta evenly over affected rooms for the per-room view
    per_room: list[tuple[str, float]] = []
    if affected_room_ids:
        share = delta / len(affected_room_ids)
        per_room = [(rid, share) for rid in sorted(affected_room_ids)]

    # Total carpet area after — sum of placed rooms + delta
    base_carpet = sum(r.geometry.area_sqft for r in placed_rooms)
    return SpaceImpact(
        per_room_sqft_delta=tuple(per_room),
        total_sqft_delta=delta,
        total_carpet_area_after=AttestedValue(
            value=base_carpet + delta,
            authority=AuthorityKind.LOCALLY_DERIVED,
            upstream_source=None,
            derivation_note=f"C3b Phase β heuristic for {category}",
        ),
        advisory_note=(
            "Net-zero internal redistribution." if delta == 0.0
            else f"Net area change of {delta:+.0f} sqft."
        ),
    )


def _build_comfort_impact(category: TweakCategory) -> ComfortImpact:
    dims, direction, magnitude = TWEAK_CATEGORY_COMFORT_PROFILE.get(
        category, (("accessibility",), "mixed", "small"),
    )
    # v0.5 A7 — seed emotional heuristics per category. Three coarse
    # 0.0–1.0 scores. Categories that don't meaningfully affect a
    # dimension leave it None. Full architect-reviewed corpus is v1.x;
    # these seed values are deterministic-by-category for R6 replay.
    spaciousness, arrival, gathering = _emotional_heuristic_for_category(category)
    return ComfortImpact(
        dimensions_affected=tuple(sorted(dims)),
        direction=direction,
        magnitude=magnitude,
        advisory_note=f"Typical {magnitude} {direction} for this tweak category.",
        perceived_spaciousness=spaciousness,
        arrival_impression=arrival,
        family_gathering_comfort=gathering,
    )


# v0.5 A7 — emotional heuristic seeds. Map TweakCategory →
# (perceived_spaciousness, arrival_impression, family_gathering_comfort).
# Each Optional[float] in [0.0, 1.0]. None means "not meaningfully
# affected by this category." Full corpus is v1.x backlog.
_EMOTIONAL_HEURISTIC_SEEDS: dict[TweakCategory, tuple] = {
    # finishes — small spaciousness lift (visual lightness)
    "finish_upgrade":         (0.55, 0.60, None),
    "finish_downgrade":       (0.45, 0.40, None),
    # door / window — limited emotional reach
    "door_relocate":          (None, 0.55, None),
    "window_resize":          (0.60, None, None),
    # balcony — strong arrival/spaciousness lift when added
    "balcony_add":            (0.70, 0.70, 0.55),
    "balcony_remove":         (0.40, 0.40, None),
    # storage — neutral on emotion
    "storage_add":            (None, None, None),
    "utility_zone_carveout":  (None, None, None),
    # room moves — strong gathering effect
    "room_swap":              (0.55, 0.55, 0.65),
    "room_resize":            (0.60, 0.50, 0.60),
    # ritual / cultural rooms — arrival impression
    "pooja_relocate":         (None, 0.65, 0.55),
    "kitchen_reorient":       (0.55, None, 0.65),
    "wet_zone_restage":       (None, None, None),
}


def _emotional_heuristic_for_category(category: TweakCategory) -> tuple:
    """Return (perceived_spaciousness, arrival_impression, family_gathering_comfort)
    triple. Each may be None."""
    return _EMOTIONAL_HEURISTIC_SEEDS.get(category, (None, None, None))


# ============================================================
# § 3 — ApplySpecification builders (light vs medium)
# ============================================================

def _build_apply_spec_light(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
) -> ApplySpecification:
    """LIGHT tweak — apply geometry-local or finish-schedule directly."""
    if category in ("finish_upgrade", "finish_downgrade"):
        grade = "premium_vitrified_800x800" if category == "finish_upgrade" else "standard_ceramic"
        overrides = tuple(sorted([
            (rid, "flooring", grade) for rid in affected_room_ids
        ], key=lambda t: (t[0], t[1])))
        if not overrides:
            # Fallback to a generic finish override
            overrides = (("default_room", "flooring", grade),)
        return ApplySpecification(
            mutation_kind="finish_schedule_only",
            geometry_local_payload=None,
            subset_rerun_payload=None,
            finish_schedule_payload=FinishSchedulePayload(
                room_finish_overrides=overrides,
                advisory_note=f"{category} applied to {len(overrides)} room(s).",
            ),
        )
    # Other LIGHT default categories → geometry_local
    return ApplySpecification(
        mutation_kind="geometry_local",
        geometry_local_payload=GeometryLocalPayload(
            new_room_function_assignments=(),
            new_door_placements_replace=(),
            new_window_assignments=(),
            advisory_note=f"{category} applied in-place.",
        ),
        subset_rerun_payload=None,
        finish_schedule_payload=None,
    )


def _build_apply_spec_medium(
    *,
    tweak_id:               str,
    category:               TweakCategory,
    topology_invariance:    TopologyInvarianceResult,
    compatibility_assertions: tuple[CompatibilityAssertion, ...],
) -> ApplySpecification:
    """MEDIUM tweak — emit SubsetRerunRequest."""
    components = TWEAK_CATEGORY_COMPONENTS_TO_RERUN.get(category, ())
    impacts = TWEAK_CATEGORY_IMPACT_TABLE.get(category, ())
    if not components or not impacts:
        # Shouldn't happen for known MEDIUM categories — defensive
        raise TweakGenerationError(
            f"No rerun mapping for category {category!r}",
            tweak_id=tweak_id,
            tweak_category_attempted=category,
        )
    return ApplySpecification(
        mutation_kind="subset_rerun",
        geometry_local_payload=None,
        finish_schedule_payload=None,
        subset_rerun_payload=SubsetRerunRequest(
            trigger_tweak_id=tweak_id,
            trigger_tweak_category=category,
            components_to_rerun=lex_asc_components(components),
            downstream_impact_set=lex_asc_impacts(impacts),
            topology_invariance_check=topology_invariance,
            expected_completion_seconds=2.5,
            rerun_anchor=f"{category}_anchor",
            compatibility_assertions=compatibility_assertions,
        ),
    )


# ============================================================
# § 4 — Recommendation flag classification
# ============================================================

def classify_recommendation_flag(
    *,
    problem_checks_addressed: tuple[ProblemCheck, ...],
) -> RecommendationFlag:
    """Per R5: STRUCTURAL marker, not authoritative ranking.

    Classification:
      - "suggested"     — at least one critical or important check addressed
      - "optional"      — only nice_to_have checks addressed
      - "alternative"   — no checks addressed (stylistic / preference tweak)
    """
    if not problem_checks_addressed:
        return "alternative"
    severities = [c.severity for c in problem_checks_addressed]
    if any(s == CheckSeverity.CRITICAL for s in severities):
        return "suggested"
    if any(s == CheckSeverity.IMPORTANT for s in severities):
        return "suggested"
    return "optional"


# ============================================================
# § 5 — Single tweak generation
# ============================================================

def _generate_tweak_id(
    layout_id:  str,
    category:   TweakCategory,
    rooms:      tuple[str, ...],
) -> str:
    """Deterministic tweak_id from layout + category + rooms.

    Same inputs → same id (R6 byte-equal replay)."""
    payload = f"{layout_id}|{category}|{','.join(sorted(rooms))}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"tweak_{h}"


def generate_one_tweak(
    *,
    layout_id:           str,
    layout_archetype:    LayoutArchetype,
    category:            TweakCategory,
    affected_room_ids:   tuple[str, ...],
    affected_grid_cells: tuple[str, ...],
    placed_rooms:        tuple[PlacedRoom, ...],
    structural_grid:     StructuralGrid,
    riser_groups:        tuple[RiserGroup, ...],
    door_placements:     tuple[DoorPlacement, ...],
    source_topology:     TopologyClassification,
    motivating_checks:   tuple[ProblemCheck, ...],
    motivation_basis:    str,
    prior_applied_tweak_ids: tuple[str, ...] = (),
) -> Optional[TweakOption] | MutationEnvelope:
    """Generate a single TweakOption for the given category, OR a
    MutationEnvelope when the per-instance severity computation
    classifies it as HEAVY.

    Returns either:
      - TweakOption (LIGHT or MEDIUM)
      - MutationEnvelope (HEAVY classification — surface as alternative pathway)
      - None when grounding can't be established (caller decides STRICT/WARN)
    """
    if not affected_room_ids and not affected_grid_cells:
        return None  # Can't ground

    # § 4.1 — Default severity from category
    default_severity: SeverityTier = TWEAK_CATEGORY_DEFAULT_SEVERITY.get(
        category, "medium",
    )

    # Predict topology invariance (R13 input)
    sorted_rooms = tuple(sorted(affected_room_ids))
    sorted_cells = tuple(sorted(affected_grid_cells))
    topology_invariance = predict_topology_invariance(
        tweak_category=category,
        source_topology=source_topology,
        affected_room_ids=sorted_rooms,
        placed_rooms=placed_rooms,
    )

    # § 4.2 — Context-aware adjustment
    context = detect_context_for_tweak(
        tweak_category=category,
        affected_room_ids=sorted_rooms,
        placed_rooms=placed_rooms,
        structural_grid=structural_grid,
        riser_groups=riser_groups,
        door_placements=door_placements,
        topology_invariance=topology_invariance,
    )

    # § 4.3 — Final severity assignment
    final_severity = promote_severity(
        default_severity=default_severity,
        context=context,
    )

    tweak_id = _generate_tweak_id(layout_id, category, sorted_rooms)

    # HEAVY → emit MutationEnvelope, buffer for session-level surfacing
    if final_severity == "heavy":
        classification: MutationClassification
        if context.topology_classification_change:
            classification = "topology_level_change"
        elif context.load_bearing_wall_involvement and context.structural_bay_boundary_cross:
            classification = "structural_level_change"
        else:
            classification = "structural_level_change"

        triggered = context.factor_names_triggered()
        reason = (
            f"Requested {category} would touch "
            f"{', '.join(triggered) if triggered else 'multiple structural elements'}, "
            f"which makes this a structural change rather than a layout tweak."
        )
        # v0.5 A6 — speculative preview text describes what the
        # restructured layout would look like at a high level, so users
        # can decide whether to step back to brief or pursue the heavy
        # pathway. Pre-linted templates by classification.
        if classification == "topology_level_change":
            preview = (
                f"Going ahead with this change would reshape the overall layout: "
                f"the circulation pattern in {_format_room_list(sorted_rooms)} "
                f"would change, and the corridor / lobby relationships nearby "
                f"would also shift. The system can sketch an alternative layout "
                f"variant if you'd like to see what that looks like."
            )
        else:  # structural_level_change
            preview = (
                f"Going ahead with this change would involve structural work: "
                f"the wall lines around {_format_room_list(sorted_rooms)} would "
                f"shift, and the column grid for the affected bay(s) would "
                f"need to be revised. The system can preview the restructured "
                f"version if you'd like to compare."
            )
        return MutationEnvelope(
            envelope_id="env_" + tweak_id[6:],
            requested_change_summary=(
                f"Tweak request: {category} affecting "
                f"{_format_room_list(sorted_rooms)}."
            ),
            classification=classification,
            why_not_a_tweak=reason,
            suggested_pathway=(
                "explore_alternative_layout"
                if classification == "structural_level_change"
                else "step_back_to_brief"
            ),
            estimated_pathway_effort=(
                "Exploring an alternative layout takes 60-90 seconds for the system."
            ),
            advisory_note=(
                "An alternative layout from the ranked set may achieve this "
                "without structural change."
            ),
            kick_back_payload=None,
            speculative_preview_text=preview,
        )

    # Compatibility assertions for MEDIUM (R15): pairwise against prior tweaks
    # v1.0 ships pairwise "compatible" assertions for simplicity; v1.x via
    # B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH adds N-way reasoning
    compatibility_assertions: tuple[CompatibilityAssertion, ...] = ()
    if final_severity == "medium" and prior_applied_tweak_ids:
        compatibility_assertions = tuple(
            CompatibilityAssertion(
                against_applied_tweak_id=prior_id,
                compatibility_kind="spatial_overlap_check",
                result="compatible",
                advisory_note=None,
            )
            for prior_id in sorted(prior_applied_tweak_ids)
        )

    # Build ApplySpecification
    apply_spec: ApplySpecification
    if final_severity == "light":
        apply_spec = _build_apply_spec_light(category, sorted_rooms)
    else:  # medium
        apply_spec = _build_apply_spec_medium(
            tweak_id=tweak_id,
            category=category,
            topology_invariance=topology_invariance,
            compatibility_assertions=compatibility_assertions,
        )

    # Build impacts
    cost_impact = _build_cost_impact(category)
    space_impact = _build_space_impact(category, sorted_rooms, placed_rooms)
    comfort_impact = _build_comfort_impact(category)

    # Recommendation flag
    rec_flag = classify_recommendation_flag(
        problem_checks_addressed=motivating_checks,
    )

    # Provenance
    motivated_by_check_id = motivating_checks[0].check_id if motivating_checks else None
    motivated_by_grid_cell = sorted_cells[0] if sorted_cells and not motivating_checks else None
    motivated_by_orientation = (
        "orientation_match" if "reorient" in category or "relocate" in category
        else None
    )
    # Ensure at least one motivation
    if not motivated_by_check_id and not motivated_by_grid_cell and not motivated_by_orientation:
        motivated_by_grid_cell = sorted_cells[0] if sorted_cells else None
        if not motivated_by_grid_cell:
            # Last resort — orientation as default motivation
            motivated_by_orientation = "general_layout_review"

    provenance = TweakProvenance(
        motivated_by_check_id=motivated_by_check_id,
        motivated_by_grid_cell_id=motivated_by_grid_cell,
        motivated_by_orientation=motivated_by_orientation,
        generation_basis=motivation_basis,
    )

    description = render_description(category, sorted_rooms)
    problem_links = tuple(sorted(c.check_id for c in motivating_checks))

    return TweakOption(
        tweak_id=tweak_id,
        tweak_category=category,
        severity_tier=final_severity,
        affected_room_ids=sorted_rooms,
        affected_grid_cells=sorted_cells,
        description=description,
        cost_impact=cost_impact,
        space_impact=space_impact,
        comfort_impact=comfort_impact,
        problem_report_links=problem_links,
        recommendation_flag=rec_flag,
        apply_specification=apply_spec,
        provenance=provenance,
        presented_count=0,
    )


# ============================================================
# § 6 — Per-layout candidate enumeration
# ============================================================

def _enumerate_candidates_from_problem_report(
    pr:           ProblemReport,
    placed_rooms: tuple[PlacedRoom, ...],
) -> list[tuple[TweakCategory, tuple[str, ...], ProblemCheck, str]]:
    """For each FAIL check in the ProblemReport with non-trivial severity,
    enumerate (category, room_ids, motivating_check, motivation_basis).

    Returns a list of candidate-triples that Phase β step 4 then turns
    into per-instance severity-classified tweaks."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], ProblemCheck, str]] = []
    valid_room_ids = {r.room_id for r in placed_rooms}

    for check in pr.applicable_checks:
        # Skip pass / warn / not_applicable — only act on fail
        if check.status != CheckStatus.FAIL:
            continue
        # Skip nice_to_have unless the check has affected rooms
        if check.severity == CheckSeverity.NICE_TO_HAVE and not check.affected_room_ids:
            continue
        # Map check_id → tweak categories (uses dimension_id + why_it_matters keywords)
        categories = lookup_tweak_categories_for_check(check)
        if not categories:
            continue
        # Use the check's affected_room_ids, intersected with valid rooms
        rooms = tuple(
            sorted(set(check.affected_room_ids) & valid_room_ids)
        )
        if not rooms:
            # Fall back to first room if no overlap (defensive)
            rooms = tuple(sorted(valid_room_ids))[:1] if valid_room_ids else ()
        for cat in categories:
            candidates.append((
                cat, rooms, check,
                f"ProblemCheck '{check.check_id}' ({check.severity.value}) "
                f"matches tweak category {cat!r}.",
            ))
    return candidates


def _enumerate_orientation_candidates(
    placed_rooms:   tuple[PlacedRoom, ...],
    plot_analysis,  # PlotAnalysis
) -> list[tuple[TweakCategory, tuple[str, ...], None, str]]:
    """Orientation-mismatch candidates per spec § 3 Phase β step 3."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], None, str]] = []
    for room in placed_rooms:
        # Kitchen facing N or W in warm-humid (Chennai) is suboptimal
        if room.room_function in ("kitchen", "kitchen_utility"):
            if room.cardinal_orientation in ("N", "W") and plot_analysis.climate_zone == "warm_humid":
                candidates.append((
                    "kitchen_reorient",
                    (room.room_id,),
                    None,
                    f"Kitchen at {room.cardinal_orientation} wall in warm-humid climate "
                    f"misaligns with morning light + ventilation principles.",
                ))
        # Pooja facing W is suboptimal per Vastu (opt-in)
        if room.room_function == "pooja":
            if room.cardinal_orientation == "W":
                candidates.append((
                    "pooja_relocate",
                    (room.room_id,),
                    None,
                    "Pooja at W wall misaligns with traditional E orientation "
                    "(opt-in via brief).",
                ))
    return candidates


def _enumerate_underutilized_cells(
    structural_grid: StructuralGrid,
    placed_rooms:    tuple[PlacedRoom, ...],
) -> list[tuple[TweakCategory, tuple[str, ...], None, str]]:
    """Structural-cell candidates per spec § 3 Phase β step 2."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], None, str]] = []
    # Rooms whose function is "corridor" with large area → utility_zone_carveout candidate
    for room in placed_rooms:
        if room.room_function == "corridor" and room.geometry.area_sqft > 80.0:
            candidates.append((
                "utility_zone_carveout",
                (room.room_id,),
                None,
                f"Corridor at {room.geometry.area_sqft:.0f} sqft is oversized; "
                f"could host a utility carveout.",
            ))
    return candidates


# ============================================================
# § 7 — Bounded selection (spec § 3 Phase β step 5)
# ============================================================

def _priority_key(tweak: TweakOption) -> tuple[int, int, int, str]:
    """Sort key for bounded selection. Lower = higher priority.

    Per spec:
      (a) addresses critical problem    — recommendation_flag='suggested' first
      (b) is LIGHT severity              — LIGHT before MEDIUM
      (c) recommendation_flag='suggested' (already used in a)

    We use:
      key = (flag_rank, severity_rank, problem_link_count_descending, tweak_id)
    """
    flag_rank = {"suggested": 0, "optional": 1, "alternative": 2}[tweak.recommendation_flag]
    severity_rank = {"light": 0, "medium": 1, "heavy": 2}[tweak.severity_tier]
    # More problem links = higher priority (use negative for sort)
    link_count = -len(tweak.problem_report_links)
    return (flag_rank, severity_rank, link_count, tweak.tweak_id)


def _bounded_selection(
    tweaks: list[TweakOption],
    cap:    int = MAX_TWEAKS_PER_LAYOUT,
) -> list[TweakOption]:
    """Keep up to `cap` tweaks, prioritized per spec § 3 Phase β step 5."""
    if len(tweaks) <= cap:
        return tweaks
    sorted_tweaks = sorted(tweaks, key=_priority_key)
    return sorted_tweaks[:cap]


# ============================================================
# § 8 — Per-layout tweak set generation
# ============================================================

def _topology_for_layout(layout_index: int) -> TopologyClassification:
    """Heuristic: lookup table for v1.0. Phase β receives the
    StructuralGrid + PlacedRooms but not the C5 topology classification
    directly. v1.x will receive it explicitly.

    For v1.0 stub: use a deterministic mapping by index.
    """
    mapping: tuple[TopologyClassification, ...] = (
        "central_spine", "strip", "l_shape",
    )
    return mapping[layout_index % len(mapping)]


def generate_tweak_option_set_for_layout(
    *,
    layout_index:      int,
    bundle:            C3bInputBundle,
    config:            C3bRuntimeConfig,
    prior_applied:     tuple[str, ...] = (),
) -> tuple[TweakOptionSet, tuple[MutationEnvelope, ...], tuple[PerTweakError, ...]]:
    """Generate a TweakOptionSet for the layout at `layout_index`.

    Returns:
      - the TweakOptionSet
      - any MutationEnvelopes buffered for HEAVY rejections
      - any per-tweak errors collected (WARN mode)
    """
    from .alpha import archetype_for_rank

    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if layout_index >= len(rankings):
        raise IndexError(f"layout_index {layout_index} out of range")

    ranking = rankings[layout_index]
    pr = bundle.problem_reports[layout_index]
    placed_rooms = bundle.placed_rooms_per_layout[layout_index]
    structural_grid = bundle.structural_grids_per_layout[layout_index]
    door_placements = bundle.door_placements_per_layout[layout_index]
    riser_groups = bundle.riser_groups_per_layout[layout_index]
    source_topology = _topology_for_layout(layout_index)

    layout_id = ranking.layout_signature
    archetype = archetype_for_rank(ranking.rank_position)

    # Enumerate candidates from 3 sources (spec § 3 Phase β 1-3)
    candidates_pr = _enumerate_candidates_from_problem_report(pr, placed_rooms)
    candidates_or = _enumerate_orientation_candidates(placed_rooms, bundle.plot_analysis)
    candidates_cell = _enumerate_underutilized_cells(structural_grid, placed_rooms)

    all_candidates = candidates_pr + candidates_or + candidates_cell

    tweaks: list[TweakOption] = []
    envelopes: list[MutationEnvelope] = []
    errors_collected: list[PerTweakError] = []

    seen_ids: set[str] = set()

    for cat, rooms, check, basis in all_candidates:
        motivating_checks = (check,) if check is not None else ()
        # Determine affected_grid_cells from rooms
        affected_cells = tuple(sorted({
            bay_id
            for room in placed_rooms
            if room.room_id in rooms
            for bay_id in room.structural_bay_ids
        }))
        try:
            result = generate_one_tweak(
                layout_id=layout_id,
                layout_archetype=archetype,
                category=cat,
                affected_room_ids=rooms,
                affected_grid_cells=affected_cells,
                placed_rooms=placed_rooms,
                structural_grid=structural_grid,
                riser_groups=riser_groups,
                door_placements=door_placements,
                source_topology=source_topology,
                motivating_checks=motivating_checks,
                motivation_basis=basis,
                prior_applied_tweak_ids=prior_applied,
            )
        except PerTweakError as e:
            if config.strict_mode == "strict":
                raise
            errors_collected.append(e)
            continue
        except ValueError as e:
            # Schema-level validation rejection during construction
            err = TweakGenerationError(
                f"Generated tweak rejected by schema validation: {e}",
                problem_check_id=(check.check_id if check else None),
                tweak_category_attempted=cat,
            )
            if config.strict_mode == "strict":
                raise err from e
            errors_collected.append(err)
            continue

        if result is None:
            continue
        if isinstance(result, MutationEnvelope):
            # Avoid duplicate envelope IDs
            if result.envelope_id not in {e.envelope_id for e in envelopes}:
                envelopes.append(result)
            continue
        # TweakOption
        if result.tweak_id in seen_ids:
            continue
        seen_ids.add(result.tweak_id)
        tweaks.append(result)

    # § 4.4 — Bounded selection
    selected = _bounded_selection(tweaks, cap=MAX_TWEAKS_PER_LAYOUT)
    selected_sorted = tuple(sorted(selected, key=lambda t: t.tweak_id))

    # Build the option-set advisory note
    if not selected_sorted:
        advisory = (
            "No specific tweaks surfaced for this layout. You could accept "
            "it as-is or explore the other ranked options."
        )
    else:
        n = len(selected_sorted)
        advisory = (
            f"{n} tweak option{'s' if n != 1 else ''} surfaced for this layout. "
            f"None are required — review each and accept what fits your priorities."
        )

    option_set = TweakOptionSet(
        layout_id=layout_id,
        layout_archetype=archetype,
        source_problem_report_id=pr.upstream_cache_key,
        tweaks=selected_sorted,
        overall_advisory_note=advisory,
    )

    return option_set, tuple(envelopes), tuple(errors_collected)


# ============================================================
# § 9 — Phase β entry point
# ============================================================

def run_phase_beta(
    session:    "TradeoffSession",  # from schema; quotes to avoid import cycle
    bundle:     C3bInputBundle,
    config:     C3bRuntimeConfig,
    prior_applied_tweak_ids: tuple[str, ...] = (),
) -> "TradeoffSession":
    """Execute Phase β: populate session.tweak_option_sets + envelopes.

    Input session must come from Phase α (status='open_for_user_input',
    empty tweak_option_sets). Returns a new session with tweak_option_sets
    + mutation_envelopes filled, re-signed.
    """
    from ..schema import TradeoffSession  # noqa: F401 — runtime import
    from .alpha import _resign_session

    if session.tweak_option_sets:
        # Phase β idempotent — if already populated, no-op
        return session

    all_option_sets: list[TweakOptionSet] = []
    all_envelopes: list[MutationEnvelope] = []

    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    for layout_idx in range(len(rankings)):
        opt_set, envs, _errs = generate_tweak_option_set_for_layout(
            layout_index=layout_idx,
            bundle=bundle,
            config=config,
            prior_applied=prior_applied_tweak_ids,
        )
        all_option_sets.append(opt_set)
        all_envelopes.extend(envs)

    # Lex-ASC sort by layout_id (R6)
    sorted_option_sets = tuple(sorted(all_option_sets, key=lambda s: s.layout_id))
    # De-dup envelopes by envelope_id; lex-ASC
    seen_env: set[str] = set()
    unique_envelopes: list[MutationEnvelope] = []
    for env in sorted(all_envelopes, key=lambda e: e.envelope_id):
        if env.envelope_id in seen_env:
            continue
        seen_env.add(env.envelope_id)
        unique_envelopes.append(env)

    import dataclasses
    new_session = dataclasses.replace(
        session,
        tweak_option_sets=sorted_option_sets,
        mutation_envelopes=tuple(unique_envelopes),
    )
    return _resign_session(new_session, config)





# ══════════════════════════════════════════════════════════════════════════════
# § phases.gamma                                                
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase γ — Cost + space + comfort impact computation
============================================================

Spec § 3 Phase γ:
  INPUT: tweaks from Phase β, RateProvider, layout geometry
  PROCESSING (per tweak):
    1. Cost impact via C7 cost estimator + RateProvider
    2. Space impact via ApplySpecification geometry payload
    3. Comfort impact via ProblemReport check mapping
    4. Recommendation flag classification
  OUTPUT: TweakOptionSets with full impact data

For v1.0 we INLINE the impact computation into Phase β (since each
TweakOption needs its cost/space/comfort impacts at construction
time per R3/R4 schema enforcement). Phase γ here is a thin wrapper
that VALIDATES every emitted tweak has well-formed impacts. v1.x will
swap heuristic ranges for live RateProvider calibration (see
B-C3B-COST-CALIBRATION implicit in v1.0 LOCK-mandatory backlog).

Rule 11 self-analysis:
  1. Why is Phase γ thin in v1.0? Because the dataclass invariants
     enforce well-formed impacts at construction time — Phase β can't
     emit a tweak with malformed impacts without raising. So Phase γ's
     job is reduced to: (a) verify integrity, (b) compute summary
     statistics (range / mid / derivation are already populated).
  2. The summary computation (total session cost delta when multiple
     tweaks accepted) happens in Phase ζ, not γ. γ is per-tweak; ζ is
     per-session.
  3. This is a real Phase, not a no-op — the verification step catches
     drift if heuristic tables and dataclass schema diverge.
"""
from __future__ import annotations

from typing import Optional

from ..config import C3bRuntimeConfig
from ..errors import ImpactComputationError, PerTweakError
from ..schema import TradeoffSession, TweakOption


def verify_tweak_impacts(tweak: TweakOption) -> Optional[ImpactComputationError]:
    """Verify a tweak's impacts are well-formed. Returns None on success
    or an ImpactComputationError describing the problem."""
    # cost_impact non-None (dataclass enforces this)
    if tweak.cost_impact is None:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} cost_impact missing",
            impact_dim="cost",
            tweak_id=tweak.tweak_id,
        )
    if not tweak.cost_impact.derivation:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} cost_impact has empty derivation",
            impact_dim="cost",
            tweak_id=tweak.tweak_id,
        )
    # space_impact non-None
    if tweak.space_impact is None:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} space_impact missing",
            impact_dim="space",
            tweak_id=tweak.tweak_id,
        )
    # comfort_impact non-None and has dimensions
    if not tweak.comfort_impact.dimensions_affected:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} comfort_impact has no dimensions",
            impact_dim="comfort",
            tweak_id=tweak.tweak_id,
        )
    return None


def run_phase_gamma(
    session:  TradeoffSession,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Verify every tweak in the session has well-formed impacts.

    Raises ImpactComputationError in STRICT mode; collects + drops the
    offending tweaks in WARN mode. Returns the (possibly modified) session."""
    errors_collected: list[PerTweakError] = []
    new_option_sets = []
    for opt_set in session.tweak_option_sets:
        verified_tweaks = []
        for tweak in opt_set.tweaks:
            err = verify_tweak_impacts(tweak)
            if err is None:
                verified_tweaks.append(tweak)
                continue
            if config.strict_mode == "strict":
                raise err
            errors_collected.append(err)
        # Rebuild option set with verified-only tweaks
        if len(verified_tweaks) == len(opt_set.tweaks):
            new_option_sets.append(opt_set)
        else:
            import dataclasses
            new_option_sets.append(dataclasses.replace(
                opt_set,
                tweaks=tuple(verified_tweaks),
            ))
    if not errors_collected:
        return session

    from .alpha import _resign_session
    import dataclasses
    return _resign_session(
        dataclasses.replace(session, tweak_option_sets=tuple(new_option_sets)),
        config,
    )





# ══════════════════════════════════════════════════════════════════════════════
# § phases.delta                                                
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase δ — User-facing presentation rendering
====================================================

Spec § 3 Phase δ:
  INPUT: full TradeoffSession with populated tweaks
  PROCESSING:
    1. Lex-ASC sort within each TweakOptionSet.tweaks by tweak_id (R6)
    2. Set TradeoffSession.current_status = "open_for_user_input"
    3. Compute canonical_replay_signature (R6), presentation_signature (R7),
       schema_descriptor_digest (R8)
    4. Persist session to SQLite WAL

  OUTPUT: TradeoffSession ready for downstream UI consumption

Per Rule 11 self-analysis:
  1. Sorting is enforced at dataclass construction (TweakOptionSet
     __post_init__ rejects unsorted tweaks). Phase δ's sort step is
     defensive — re-sort if any phase had unsorted output, but raise
     if dataclasses already accepted unsorted input. So in practice
     this is a no-op verification.
  2. Persistence is delegated to session_storage.py (called from
     orchestrator, not directly from Phase δ). Phase δ's job is signing.
"""
from __future__ import annotations

from ..config import C3bRuntimeConfig
from ..schema import TradeoffSession


def run_phase_delta(
    session:  TradeoffSession,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Render presentation: set status to open_for_user_input,
    re-sign session, return."""
    from .alpha import _resign_session
    import dataclasses

    # Verify lex-ASC sort (defensive — dataclasses already enforce)
    for opt_set in session.tweak_option_sets:
        tweak_ids = [t.tweak_id for t in opt_set.tweaks]
        assert tweak_ids == sorted(tweak_ids), (
            f"TweakOptionSet {opt_set.layout_id!r} tweaks unsorted at Phase δ "
            f"(would have failed dataclass invariant)"
        )

    # Ensure status reflects readiness for user input
    if session.current_status != "open_for_user_input":
        # Only change if it's a non-terminal status
        if session.current_status in (
            "open_for_user_input", "awaiting_subset_rerun",
            "iteration_cap_reached",
        ):
            new_session = dataclasses.replace(
                session, current_status="open_for_user_input",
            )
            return _resign_session(new_session, config)

    # Re-sign at presentation time
    return _resign_session(session, config)





# ══════════════════════════════════════════════════════════════════════════════
# § phases.epsilon                                              
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase ε — User-turn handling
=====================================

Spec § 3 Phase ε:
  INPUT: TradeoffSession + UserAction (accept / reject / finalize /
         abandon / kickback / no_action)
  PROCESSING:
    1. Validate chosen_tweak_id is in current presented set (Q3 Level B
       discipline — chosen ∈ presented)
    2. Append SessionTurn to session_history
    3. Branch on user_action:
       - accepted_tweak LIGHT  → apply in-place, regen options
       - accepted_tweak MEDIUM → emit SubsetRerunRequest, status →
                                  awaiting_subset_rerun
       - rejected_tweak        → presented_count++, no mutation
       - no_action_continue    → no state change
       - finalized_layout_choice → ResolvedSelection, status → resolved
       - kicked_back_to_c3a    → status → kicked_back_to_c3a (terminal)
       - abandoned_session     → status → abandoned_no_tweaks (terminal)
    4. Iteration cap check: if iteration_count >= cap → force
       iteration_cap_reached

R14 (regression detection) fires inside complete_subset_rerun (called
after MEDIUM rerun returns). R15 (compatibility) fires at apply.
R16 (single-linear-history) is enforced by TradeoffSession's
__post_init__ (iteration_index == position).

Rule 11 self-analysis:
  1. Phase ε ITSELF doesn't run the subset rerun — that's the
     orchestrator's job. Phase ε's MEDIUM-accept path emits the
     SubsetRerunRequest and changes session status to
     'awaiting_subset_rerun'. The orchestrator (or its caller) then
     invokes the rerun and calls back into complete_subset_rerun.
  2. R14 regression detection compares pre-rerun and post-rerun
     ProblemReport critical counts. We pass both as arguments to
     complete_subset_rerun.
  3. The Q3 Level B invariant (chosen ∈ presented) is enforced at
     SessionTurn dataclass construction; Phase ε just constructs the
     turn correctly. Defensive: we also validate before constructing.
  4. The user_action='abandoned_session' branch picks the
     highest-ranked layout (rank 0) as the default selection. This
     mirrors the spec's "user accepts a layout as-is" framing.
"""
from __future__ import annotations

import dataclasses
import uuid
from typing import Optional

from buildemup.components.c15.schema import (
    CheckSeverity,
    CheckStatus,
    ProblemReport,
)

from ..config import C3bRuntimeConfig
from ..contracts import C3bInputBundle, KickbackContext
from ..errors import (
    CompatibilityAssertionFailedError,
    LocalTradeoffError,
)
from ..schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplyStatus,
    CompatibilityAssertion,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionStatus,
    SessionTurn,
    SubsetRerunRequest,
    TradeoffSession,
    TweakOption,
    UserAction,
)
from ..versioning import (
    MAX_REPRESENT_COUNT,
    REGRESSION_CRITICAL_INCREASE_THRESHOLD,
)


# ============================================================
# § 1 — Helpers
# ============================================================

def _all_presented_tweak_ids(session: TradeoffSession) -> tuple[str, ...]:
    """All tweak_ids currently presented across all layout option sets."""
    ids: set[str] = set()
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            ids.add(t.tweak_id)
    return tuple(sorted(ids))


def _find_tweak(
    session:   TradeoffSession,
    tweak_id:  str,
) -> Optional[tuple[TweakOption, str]]:
    """Find a tweak by id across all option sets; return (tweak, layout_id) or None."""
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.tweak_id == tweak_id:
                return t, opt_set.layout_id
    return None


def _bump_iteration_count(session: TradeoffSession) -> int:
    """Returns next iteration_count value."""
    return session.iteration_count + 1


def _at_iteration_cap(session: TradeoffSession) -> bool:
    """Spec § 3 Phase ε step 4: iteration cap check."""
    return _bump_iteration_count(session) >= session.iteration_cap


def _new_turn_id(iteration_index: int) -> str:
    return f"turn_{iteration_index:04d}_{uuid.uuid4().hex[:8]}"


# ============================================================
# § 2 — Compatibility check (R15)
# ============================================================

def check_compatibility_against_history(
    tweak:             TweakOption,
    applied_history:   tuple[str, ...],
) -> tuple[CompatibilityAssertion, ...]:
    """For each prior applied tweak, run pairwise compatibility check.

    v1.0: stub pairwise that returns 'compatible' unless we detect
    a known conflict pattern. v1.x will use formal dependency graph
    per B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH.

    Known conflict patterns (heuristic):
      - kitchen_reorient + pooja_relocate (both want east → corner conflict)
      - wet_zone_restage + kitchen_reorient (wet zone vs kitchen wet area)
    """
    if not applied_history:
        return ()
    assertions: list[CompatibilityAssertion] = []
    # Heuristic: identical category against itself = always compatible
    # Cross-category conflicts surface as 'ambiguous' (advisory only)
    for prior_id in sorted(applied_history):
        # We don't know prior's category here without lookup; v1.0 just
        # emits 'compatible' assertion. Real conflict detection lives
        # at apply-time in apply_subset_rerun_result (which has
        # full context).
        assertions.append(CompatibilityAssertion(
            against_applied_tweak_id=prior_id,
            compatibility_kind="spatial_overlap_check",
            result="compatible",
            advisory_note=None,
        ))
    return tuple(assertions)


# ============================================================
# § 3 — LIGHT tweak application (in-place)
# ============================================================

def _apply_light_tweak(
    session:   TradeoffSession,
    tweak:     TweakOption,
    config:    C3bRuntimeConfig,
) -> tuple[TradeoffSession, ApplyOutcome]:
    """Apply a LIGHT tweak in-place. Per spec § 3 Phase ε:
       'apply mutation in-place to layout geometry / finish schedule,
        regenerate TweakOptionSet for that layout'

    v1.0 stub: applies the mutation by removing the accepted tweak
    from the option set (so it won't be re-suggested) and bumping
    presented_count on related tweaks. Real layout-geometry mutation
    is downstream of Phase ε and handled by the orchestrator.

    Returns (new_session, ApplyOutcome)."""
    # Remove the accepted tweak from its option set (it's been applied);
    # don't touch other tweaks
    new_option_sets = []
    for opt_set in session.tweak_option_sets:
        if any(t.tweak_id == tweak.tweak_id for t in opt_set.tweaks):
            remaining = tuple(
                t for t in opt_set.tweaks if t.tweak_id != tweak.tweak_id
            )
            new_option_sets.append(dataclasses.replace(
                opt_set, tweaks=remaining,
            ))
        else:
            new_option_sets.append(opt_set)
    new_session = dataclasses.replace(
        session,
        tweak_option_sets=tuple(new_option_sets),
    )
    outcome = ApplyOutcome(
        apply_status="applied_successfully",
        error_summary=None,
        new_layout_signature=f"sig_after_{tweak.tweak_id}",
        new_problem_report_id=None,    # LIGHT doesn't rerun PR
        regression_detected=False,
        newly_critical_check_ids=(),
    )
    return new_session, outcome


# ============================================================
# § 4 — MEDIUM tweak application (emit subset-rerun request)
# ============================================================

def _apply_medium_tweak_emit_rerun(
    session:   TradeoffSession,
    tweak:     TweakOption,
    config:    C3bRuntimeConfig,
) -> tuple[TradeoffSession, ApplyOutcome, bool]:
    """Stage a MEDIUM tweak — set session status to awaiting_subset_rerun
    and emit the SubsetRerunRequest (already embedded in tweak's
    ApplySpecification).

    The actual rerun happens externally; complete_subset_rerun() is
    called when results return.

    v0.5 A2 — increments medium_tweak_count_since_full_recompute.
    Returns a tuple (new_session, outcome, full_recompute_triggered).
    full_recompute_triggered is True when the increment crossed
    config.full_recompute_threshold, signaling the caller to attach a
    'full_coherence_recheck_triggered' advisory.
    """
    # Verify the apply_spec has a subset_rerun_payload
    srr = tweak.apply_specification.subset_rerun_payload
    if srr is None:
        raise LocalTradeoffError(
            f"MEDIUM tweak {tweak.tweak_id!r} has no subset_rerun_payload "
            f"(R4 violation reached Phase ε — should have been caught at "
            f"TweakOption construction)",
            session_id=session.session_id,
            phase="epsilon",
        )
    # v0.5 A2 — increment counter; if it crosses threshold, signal
    # full-recompute. Counter resets in complete_subset_rerun on success.
    new_count = session.medium_tweak_count_since_full_recompute + 1
    full_recompute_triggered = new_count >= config.full_recompute_threshold
    new_session = dataclasses.replace(
        session,
        current_status="awaiting_subset_rerun",
        medium_tweak_count_since_full_recompute=new_count,
    )
    outcome = ApplyOutcome(
        apply_status="rerun_queued",
        error_summary=None,
        new_layout_signature=None,
        new_problem_report_id=None,
        regression_detected=False,
        newly_critical_check_ids=(),
    )
    return new_session, outcome, full_recompute_triggered


# ============================================================
# § 5 — Public: apply_user_action
# ============================================================

# v0.5 A3 — known contradictory tweak-category pairs for oscillation
# detection. (a, b) means accepting a then accepting b is contradictory.
# Order-agnostic; the detection logic checks both orderings.
KNOWN_CONTRADICTORY_CATEGORY_PAIRS: tuple[tuple[str, str], ...] = (
    ("balcony_add",     "balcony_remove"),
    ("finish_upgrade",  "finish_downgrade"),
)


def detect_oscillation_pattern(
    session: TradeoffSession,
) -> Optional[tuple[str, str]]:
    """v0.5 A3 — detect oscillation patterns in session_history.

    Returns (pattern_kind, advisory_note) when a pattern fires, else None.
    Patterns checked (any one triggers):
      1. Accept-then-reject of the SAME tweak_id within 3 turns
      2. Accept of category X then accept of contradictory category Y
      3. 3 consecutive rejections of the same category

    Pattern detection is deterministic over session_history → R6 safe.
    """
    history = session.session_history
    if not history:
        return None

    # Map tweak_id → its category, accreted from option sets (current + applied)
    tweak_id_to_category: dict[str, str] = {}
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            tweak_id_to_category[t.tweak_id] = t.tweak_category
    # Also handle tweaks that have been removed (LIGHT applied) — we lose
    # them but the accept-then-reject case is unaffected (since reject
    # doesn't remove until cap).

    # Pattern 1: accept-then-reject of same tweak_id within 3 turns
    n = len(history)
    for i, turn in enumerate(history):
        if turn.user_action == "rejected_tweak" and turn.chosen_tweak_id:
            look_back_start = max(0, i - 3)
            for j in range(look_back_start, i):
                prior = history[j]
                if (prior.user_action == "accepted_tweak"
                        and prior.chosen_tweak_id == turn.chosen_tweak_id):
                    return (
                        "oscillation_pattern_detected",
                        f"You accepted tweak '{turn.chosen_tweak_id}' "
                        f"earlier and then rejected it. You could take a "
                        f"moment to decide which direction matters more "
                        f"and finalize on that priority.",
                    )

    # Pattern 2: contradictory-category accepts
    accepted_categories: list[tuple[int, str]] = []
    for i, turn in enumerate(history):
        if turn.user_action == "accepted_tweak" and turn.chosen_tweak_id:
            cat = tweak_id_to_category.get(turn.chosen_tweak_id)
            if cat:
                accepted_categories.append((i, cat))
    for i, (idx_a, cat_a) in enumerate(accepted_categories):
        for idx_b, cat_b in accepted_categories[i + 1:]:
            for pair in KNOWN_CONTRADICTORY_CATEGORY_PAIRS:
                if {cat_a, cat_b} == {pair[0], pair[1]}:
                    return (
                        "oscillation_pattern_detected",
                        f"You appear to be balancing {cat_a} vs {cat_b}. "
                        f"You could take a moment to decide which matters "
                        f"more and finalize on that priority.",
                    )

    # Pattern 3: 3 consecutive rejections of same category
    consecutive_rejects: list[tuple[int, str]] = []
    for i, turn in enumerate(history):
        if turn.user_action == "rejected_tweak" and turn.chosen_tweak_id:
            cat = tweak_id_to_category.get(turn.chosen_tweak_id)
            if cat:
                if consecutive_rejects and consecutive_rejects[-1][1] != cat:
                    consecutive_rejects = []
                consecutive_rejects.append((i, cat))
                if len(consecutive_rejects) >= 3:
                    return (
                        "oscillation_pattern_detected",
                        f"You've rejected three tweaks of the same kind "
                        f"({cat}). That category may not fit what you want "
                        f"— you could move on or step back to brief.",
                    )
        elif turn.user_action == "accepted_tweak":
            consecutive_rejects = []

    return None


def _invoke_strategic_advisory(
    *,
    session: TradeoffSession,
    request,    # forward ref to UserActionRequest below
    config:  C3bRuntimeConfig,
) -> Optional[str]:
    """v0.5 A4 — invoke the configured strategic-advisory provider.

    Returns the advisory text the provider returned, or None when:
      - strategic_mode == "off"
      - no provider registered
      - provider returns None
      - provider raises (silently swallowed — strategic advice is best-
        effort, never blocks the user turn)

    R17 invariant: returned text does NOT affect canonical_replay_signature.
    Caller attaches it to SessionTurn.strategic_advisory_text only.
    """
    if config.strategic_mode == "off":
        return None
    provider = config.strategic_advisory_provider
    if provider is None:
        return None
    try:
        text = provider(session=session, request=request)
    except Exception:
        # Strategic advisory is best-effort; provider crashes never
        # interrupt the user turn.
        return None
    if not isinstance(text, str) or not text:
        return None
    # Best-effort lint check — if the provider returns banned text, drop
    # it silently rather than raising.
    try:
        from ..advisory_lint import is_advisory_clean
        if not is_advisory_clean(text):
            return None
    except Exception:
        return None
    return text


@dataclasses.dataclass(frozen=True)
class UserActionRequest:
    """Structured user-action input to Phase ε.

    Fields by user_action:
      - accepted_tweak       → chosen_tweak_id required
      - rejected_tweak       → chosen_tweak_id required
      - no_action_continue   → no extras
      - finalized_layout_choice → finalize_layout_id required
      - kicked_back_to_c3a   → kickback_context required (caller supplies)
      - abandoned_session    → no extras (system picks rank-0 layout)
    """
    user_action:        UserAction
    chosen_tweak_id:    Optional[str] = None
    finalize_layout_id: Optional[str] = None
    kickback_context:   Optional[KickbackContext] = None


def apply_user_action(
    session:  TradeoffSession,
    request:  UserActionRequest,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Phase ε entry point. Apply one user action to the session,
    append a SessionTurn, branch on action, return new session.

    Per Principle 4: user agency. The system never overrides; it
    routes the action and surfaces outcomes."""
    from .alpha import _resign_session
    from .beta import run_phase_beta  # noqa: F401 — for re-gen after LIGHT apply

    if session.current_status in (
        "abandoned_no_tweaks", "kicked_back_to_c3a",
        "resolved_selection_ready",
    ):
        raise LocalTradeoffError(
            f"Session in terminal status {session.current_status!r}; "
            f"no further actions accepted.",
            session_id=session.session_id,
            phase="epsilon",
        )

    presented = _all_presented_tweak_ids(session)
    iteration_index = len(session.session_history)
    next_iteration_count = _bump_iteration_count(session)

    # Branch by user_action
    action = request.user_action
    chosen_id = request.chosen_tweak_id
    apply_outcome: Optional[ApplyOutcome] = None
    post_status: SessionStatus = session.current_status
    new_session = session
    new_advisory_flags: list[AdvisoryFlag] = list(session.advisory_flags)

    if action in ("accepted_tweak", "rejected_tweak"):
        if not chosen_id:
            raise LocalTradeoffError(
                f"user_action={action!r} requires chosen_tweak_id",
                session_id=session.session_id, phase="epsilon",
            )
        if chosen_id not in presented:
            raise LocalTradeoffError(
                f"chosen_tweak_id {chosen_id!r} not in presented set "
                f"(Q3 Level B violation)",
                session_id=session.session_id, phase="epsilon",
            )
        found = _find_tweak(session, chosen_id)
        if found is None:
            raise LocalTradeoffError(
                f"Tweak {chosen_id!r} not found",
                session_id=session.session_id, phase="epsilon",
            )
        tweak, _layout_id = found

        if action == "accepted_tweak":
            if tweak.severity_tier == "light":
                new_session, apply_outcome = _apply_light_tweak(
                    new_session, tweak, config,
                )
                post_status = "open_for_user_input"
            elif tweak.severity_tier == "medium":
                # v0.5 A2 — _apply_medium_tweak_emit_rerun now returns
                # 3-tuple including full_recompute_triggered flag
                new_session, apply_outcome, full_recompute_triggered = (
                    _apply_medium_tweak_emit_rerun(
                        new_session, tweak, config,
                    )
                )
                post_status = "awaiting_subset_rerun"
                # v0.5 A2 — if counter crossed threshold, attach advisory
                if full_recompute_triggered:
                    new_advisory_flags.append(AdvisoryFlag(
                        flag_id=f"flag_fullrecompute_{iteration_index:04d}",
                        kind="full_coherence_recheck_triggered",
                        advisory_note=(
                            "You've applied several layout-affecting tweaks. "
                            "The next rerun will re-check the whole layout "
                            "for coherence, not just the affected rooms."
                        ),
                        related_ids=(tweak.tweak_id,),
                    ))
            else:  # heavy — should never reach here (R4)
                raise LocalTradeoffError(
                    "HEAVY tweak reached Phase ε accepted_tweak branch "
                    "(R4 violation)",
                    session_id=session.session_id, phase="epsilon",
                )
        else:  # rejected_tweak
            # Bump presented_count on the rejected tweak so it isn't
            # re-suggested too aggressively (MAX_REPRESENT_COUNT)
            new_option_sets = []
            for opt_set in new_session.tweak_option_sets:
                if any(t.tweak_id == chosen_id for t in opt_set.tweaks):
                    new_tweaks = []
                    for t in opt_set.tweaks:
                        if t.tweak_id == chosen_id and t.presented_count < MAX_REPRESENT_COUNT:
                            new_tweaks.append(dataclasses.replace(
                                t, presented_count=t.presented_count + 1,
                            ))
                        elif t.tweak_id == chosen_id:
                            # At cap — remove from option set
                            continue
                        else:
                            new_tweaks.append(t)
                    new_option_sets.append(dataclasses.replace(
                        opt_set, tweaks=tuple(new_tweaks),
                    ))
                else:
                    new_option_sets.append(opt_set)
            new_session = dataclasses.replace(
                new_session, tweak_option_sets=tuple(new_option_sets),
            )
            post_status = "open_for_user_input"
            apply_outcome = None

    elif action == "no_action_continue":
        post_status = session.current_status
        if post_status not in ("open_for_user_input", "awaiting_subset_rerun"):
            post_status = "open_for_user_input"

    elif action == "finalized_layout_choice":
        if not request.finalize_layout_id:
            raise LocalTradeoffError(
                "user_action='finalized_layout_choice' requires finalize_layout_id",
                session_id=session.session_id, phase="epsilon",
            )
        new_session = _build_resolved_selection(
            new_session, request.finalize_layout_id, config,
        )
        # v0.5 R18 — counter resets on terminal resolution
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "resolved_selection_ready"

    elif action == "kicked_back_to_c3a":
        # v0.5 R18 — counter resets on terminal status
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "kicked_back_to_c3a"

    elif action == "abandoned_session":
        # Pick rank-0 layout as default
        if session.tweak_option_sets:
            default_layout_id = session.tweak_option_sets[0].layout_id
            new_session = _build_resolved_selection(
                new_session, default_layout_id, config, no_tweaks_applied=True,
            )
        # v0.5 R18 — counter resets on terminal status
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "abandoned_no_tweaks"

    else:
        raise LocalTradeoffError(
            f"Unknown user_action {action!r}",
            session_id=session.session_id, phase="epsilon",
        )

    # Iteration-cap check (after action, before commit) — only for non-terminal
    if post_status in ("open_for_user_input", "awaiting_subset_rerun"):
        if next_iteration_count >= session.iteration_cap:
            post_status = "iteration_cap_reached"
            new_advisory_flags.append(AdvisoryFlag(
                flag_id=f"flag_itercap_{iteration_index:04d}",
                kind="iteration_cap_warning_nudge",
                advisory_note=(
                    "You've made good progress — you could finalize a layout "
                    "now or step back to brief if your scope is changing."
                ),
                related_ids=(),
            ))

    # v0.5 A3 — oscillation pattern detection (after applying this turn
    # but before committing the SessionTurn). We feed the still-being-
    # built session-with-history-so-far to the detector.
    # Build the in-flight turn first (without strategic advisory) so the
    # detector can examine the would-be history.
    in_flight_turn = SessionTurn(
        turn_id=_new_turn_id(iteration_index),
        iteration_index=iteration_index,
        timestamp_offset_ms=iteration_index * 1000,    # R7d: relative, deterministic
        presented_tweaks=presented,
        user_action=action,
        chosen_tweak_id=(
            chosen_id if action in ("accepted_tweak", "rejected_tweak") else None
        ),
        apply_outcome=apply_outcome,
        post_turn_status=post_status,
        strategic_advisory_text=None,    # filled below if provider present
    )

    # Run oscillation detection on the would-be-committed history.
    # Detection only fires on patterns spanning multiple turns.
    history_for_detection = session.session_history + (in_flight_turn,)
    probe_session = dataclasses.replace(
        new_session,
        session_history=history_for_detection,
        current_status=post_status,
        # R18 invariant: keep counter coherent with post_status. The
        # probe session is for detection only; never returned.
    )
    osc_result = detect_oscillation_pattern(probe_session)
    if osc_result is not None:
        kind, note = osc_result
        # Use turn-position-keyed flag_id for stability
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_osc_{iteration_index:04d}",
            kind=kind,
            advisory_note=note,
            related_ids=(),
        ))

    # v0.5 A4 — invoke strategic advisory provider (R17: text excluded
    # from canonical_replay_signature; this is purely informational)
    strategic_text = _invoke_strategic_advisory(
        session=new_session, request=request, config=config,
    )

    # Commit the actual turn (with strategic text attached if produced)
    turn = dataclasses.replace(in_flight_turn, strategic_advisory_text=strategic_text)

    # Update iteration_count for non-terminal actions; cap at hard ceiling
    new_iter_count = next_iteration_count if action not in (
        "no_action_continue", "kicked_back_to_c3a", "abandoned_session",
    ) else session.iteration_count

    new_advisory_flags_sorted = tuple(
        sorted(new_advisory_flags, key=lambda f: f.flag_id)
    )

    final_session = dataclasses.replace(
        new_session,
        session_history=session.session_history + (turn,),
        iteration_count=new_iter_count,
        current_status=post_status,
        advisory_flags=new_advisory_flags_sorted,
    )
    return _resign_session(final_session, config)


# ============================================================
# § 6 — ResolvedSelection assembly (called from finalize/abandon paths)
# ============================================================

def _build_resolved_selection(
    session:    TradeoffSession,
    layout_id:  str,
    config:     C3bRuntimeConfig,
    no_tweaks_applied: bool = False,
) -> TradeoffSession:
    """Construct a ResolvedSelection and attach to session.

    Sums cost / space deltas across applied tweaks (history)."""
    # Find the option set for this layout (for archetype)
    target_set = None
    for opt_set in session.tweak_option_sets:
        if opt_set.layout_id == layout_id:
            target_set = opt_set
            break
    if target_set is None and session.tweak_option_sets:
        target_set = session.tweak_option_sets[0]
        layout_id = target_set.layout_id

    archetype = target_set.layout_archetype if target_set else "cost_efficient"

    # Find applied tweaks from history
    applied_tweak_ids: list[str] = []
    if not no_tweaks_applied:
        for turn in session.session_history:
            if (turn.user_action == "accepted_tweak"
                    and turn.chosen_tweak_id is not None
                    and turn.apply_outcome
                    and turn.apply_outcome.apply_status in (
                        "applied_successfully", "rerun_queued",
                    )):
                applied_tweak_ids.append(turn.chosen_tweak_id)
    applied_sorted = tuple(sorted(applied_tweak_ids))

    final_handoff = _build_handoff_advisory(
        archetype=archetype,
        applied_count=len(applied_sorted),
        no_tweaks_applied=no_tweaks_applied,
    )

    final_layout_signature = f"final_{layout_id}_{len(applied_sorted)}tweaks"
    rs = ResolvedSelection(
        chosen_layout_id=layout_id,
        chosen_layout_archetype=archetype,
        applied_tweaks=applied_sorted,
        final_layout_signature=final_layout_signature,
        final_problem_report_id=None,    # Phase ζ may fill this
        total_cost_delta=None,            # Phase ζ may fill this
        total_space_delta=None,
        final_handoff_advisory=final_handoff,
    )
    return dataclasses.replace(session, resolved_selection=rs)


def _build_handoff_advisory(
    *,
    archetype:         str,
    applied_count:     int,
    no_tweaks_applied: bool,
) -> str:
    """Plain-English handoff summary. R2 lint-clean by construction."""
    archetype_display = {
        "cost_efficient":   "Cost Efficient",
        "everyday_living":  "Everyday Living",
        "premium_design":   "Premium Design",
    }.get(archetype, archetype)

    if no_tweaks_applied:
        return (
            f"You accepted the {archetype_display} layout as-is. "
            f"We'll generate the working and regulatory drawings next."
        )
    n = applied_count
    return (
        f"You finalized the {archetype_display} layout with "
        f"{n} tweak{'s' if n != 1 else ''} applied. "
        f"We'll generate the working and regulatory drawings next."
    )


# ============================================================
# § 7 — R14: Regression detection on subset-rerun completion
# ============================================================

def _count_critical_checks(pr: ProblemReport) -> int:
    """Count fail-tier critical checks in a ProblemReport."""
    return sum(
        1 for c in pr.applicable_checks
        if c.status == CheckStatus.FAIL
        and c.severity == CheckSeverity.CRITICAL
    )


def _diff_critical_check_ids(
    pre:   ProblemReport,
    post:  ProblemReport,
) -> tuple[str, ...]:
    """Return check_ids that are newly CRITICAL in `post` vs `pre`."""
    pre_critical = {
        c.check_id for c in pre.applicable_checks
        if c.status == CheckStatus.FAIL and c.severity == CheckSeverity.CRITICAL
    }
    post_critical = {
        c.check_id for c in post.applicable_checks
        if c.status == CheckStatus.FAIL and c.severity == CheckSeverity.CRITICAL
    }
    return tuple(sorted(post_critical - pre_critical))


def _detect_dimension_score_regression(
    pre_rerun_pr:   ProblemReport,
    post_rerun_pr:  ProblemReport,
) -> tuple[tuple[str, float], ...]:
    """v0.5 A5 — detect numeric per-dimension regression beyond
    DIMENSION_DEGRADATION_THRESHOLD_PCT.

    Returns a tuple of (dimension_name, degradation_pct) pairs for
    dimensions that degraded by >= threshold. Empty tuple if C15
    doesn't emit per-dimension scores (defensive fall-through).
    """
    from ..versioning import DIMENSION_DEGRADATION_THRESHOLD_PCT
    pre_scores = getattr(pre_rerun_pr, "dimension_score_snapshot", None)
    post_scores = getattr(post_rerun_pr, "dimension_score_snapshot", None)
    if not pre_scores or not post_scores:
        return ()    # graceful no-op when C15 doesn't supply
    if not hasattr(pre_scores, "items"):
        return ()
    regressions: list[tuple[str, float]] = []
    for dim_name, pre_score in pre_scores.items():
        post_score = post_scores.get(dim_name)
        if post_score is None or pre_score <= 0:
            continue
        delta_pct = (pre_score - post_score) / pre_score * 100.0
        if delta_pct >= DIMENSION_DEGRADATION_THRESHOLD_PCT:
            regressions.append((dim_name, delta_pct))
    # lex-ASC by dimension name for replay determinism
    regressions.sort(key=lambda t: t[0])
    return tuple(regressions)


def complete_subset_rerun(
    session:        TradeoffSession,
    applied_tweak_id: str,
    pre_rerun_pr:   ProblemReport,
    post_rerun_pr:  ProblemReport,
    config:         C3bRuntimeConfig,
) -> TradeoffSession:
    """Called when an external subset-rerun orchestrator returns
    results. Performs R14 regression detection, surfaces advisory,
    and re-opens session for next user input.

    Per spec § 7.2 R14:
      'When the new C15 ProblemReport has MORE critical checks than
      the original, mark regression_detected, add AdvisoryFlag, and
      surface an automatic "undo this tweak" option.'

    v0.5 amendments:
      A2 — resets medium_tweak_count_since_full_recompute to 0 when
           the rerun was a full recompute (counter had crossed
           full_recompute_threshold before this rerun fired)
      A5 — dimension-score regression check (numeric, sub-CRITICAL).
           Augments R14's severity-tier-transition check with a
           per-dimension delta check. No-ops gracefully when C15
           does not emit per-dimension scores.

    v1.0 stops short of synthesizing the undo tweak option — that's
    the orchestrator's job after this returns. We mark the flag and
    update the last apply_outcome.
    """
    from .alpha import _resign_session

    pre_count = _count_critical_checks(pre_rerun_pr)
    post_count = _count_critical_checks(post_rerun_pr)
    regression = (
        post_count - pre_count >= REGRESSION_CRITICAL_INCREASE_THRESHOLD
    )
    newly_critical_ids = _diff_critical_check_ids(pre_rerun_pr, post_rerun_pr)

    # v0.5 A5 — numeric dimension regression (independent of severity-tier
    # transitions; catches gradual sub-CRITICAL degradation)
    dim_regressions = _detect_dimension_score_regression(
        pre_rerun_pr, post_rerun_pr,
    )

    # Update the last SessionTurn's apply_outcome with results
    if not session.session_history:
        raise LocalTradeoffError(
            "complete_subset_rerun called on session with empty history",
            session_id=session.session_id, phase="epsilon",
        )
    last_turn = session.session_history[-1]
    if last_turn.user_action != "accepted_tweak":
        raise LocalTradeoffError(
            f"complete_subset_rerun expected last turn to be accepted_tweak; "
            f"got {last_turn.user_action!r}",
            session_id=session.session_id, phase="epsilon",
        )
    new_outcome = ApplyOutcome(
        apply_status="applied_successfully",
        error_summary=None,
        new_layout_signature=f"sig_after_{applied_tweak_id}",
        new_problem_report_id=post_rerun_pr.upstream_cache_key,
        regression_detected=regression,
        newly_critical_check_ids=newly_critical_ids if regression else (),
    )
    new_last_turn = dataclasses.replace(last_turn, apply_outcome=new_outcome)
    new_history = session.session_history[:-1] + (new_last_turn,)

    new_advisory_flags = list(session.advisory_flags)
    if regression:
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_regression_{applied_tweak_id[:12]}",
            kind="regression_after_apply",
            advisory_note=(
                f"After this tweak, {len(newly_critical_ids)} new critical "
                f"issue{'s' if len(newly_critical_ids) != 1 else ''} appeared. "
                f"You could undo this tweak and try a different approach."
            ),
            related_ids=newly_critical_ids,
        ))

    # v0.5 A5 — dimension-score regression advisory
    if dim_regressions:
        dim_names = ", ".join(name for name, _ in dim_regressions)
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_dimregression_{applied_tweak_id[:12]}",
            kind="dimension_score_regression",
            advisory_note=(
                f"After this tweak, {dim_names} dropped noticeably "
                f"(more than the typical tolerance). The change didn't "
                f"trip a critical issue, but you could undo it if those "
                f"dimensions matter to you."
            ),
            related_ids=tuple(name for name, _ in dim_regressions),
        ))

    new_advisory_flags_sorted = tuple(
        sorted(new_advisory_flags, key=lambda f: f.flag_id)
    )

    # v0.5 A2 — when the rerun was a full recompute (counter had crossed
    # threshold before this rerun fired), reset the counter to 0.
    new_counter = session.medium_tweak_count_since_full_recompute
    if new_counter >= config.full_recompute_threshold:
        new_counter = 0

    new_session = dataclasses.replace(
        session,
        session_history=new_history,
        advisory_flags=new_advisory_flags_sorted,
        current_status="open_for_user_input",
        medium_tweak_count_since_full_recompute=new_counter,
    )
    return _resign_session(new_session, config)





# ══════════════════════════════════════════════════════════════════════════════
# § phases.zeta                                                 
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Phase ζ — Resolution + handoff signing
==============================================

Spec § 3 Phase ζ:
  INPUT: TradeoffSession in 'resolved_selection_ready' state
  PROCESSING:
    1. Compute final_layout_signature (post-tweak hash)
    2. If MEDIUM tweaks applied, fetch re-run ProblemReport's ID
       into final_problem_report_id
    3. Sum cost_impacts across applied tweaks → total_cost_delta
    4. Sum space_impacts → total_space_delta
    5. Generate final_handoff_advisory (plain-English summary)
    6. Compute final canonical_replay_signature (R6),
       presentation_signature (R7), schema_descriptor_digest (R8)
  OUTPUT: TradeoffSession.resolved_selection fully populated; session
          ready for C16 to consume.

Rule 11 self-analysis:
  1. Phase ζ ONLY runs when current_status == 'resolved_selection_ready'.
     Other terminal statuses (abandoned, kicked_back) have their own
     resolved_selection paths in Phase ε.
  2. Cost / space delta sums are computed from the SESSION HISTORY,
     not from current option sets (applied tweaks may have been
     removed from option sets already). The session_history is the
     source of truth per R16.
  3. We attach a wrap-up AdvisoryFlag if the session had regressions
     (R14) so downstream renderers can show them prominently.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from buildemup.utils.confidence import Confidence
from buildemup.utils.transparency import DerivationLine, TransparencyTriple

from ..config import C3bRuntimeConfig
from ..contracts import AttestedValue, AuthorityKind
from ..errors import LocalTradeoffError
from ..schema import (
    ResolvedSelection,
    SpaceImpact,
    TradeoffSession,
    TweakOption,
)


def _find_applied_tweaks(session: TradeoffSession) -> tuple[TweakOption, ...]:
    """Pull TweakOptions for tweak_ids in session.resolved_selection.applied_tweaks
    from session history's apply-outcomes. v1.0 uses tweak_option_sets as
    the lookup source — but applied tweaks may have been removed from
    option sets. We use a heuristic: look in both."""
    if session.resolved_selection is None:
        return ()
    target_ids = set(session.resolved_selection.applied_tweaks)
    found: list[TweakOption] = []
    seen: set[str] = set()
    # Search option sets first
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.tweak_id in target_ids and t.tweak_id not in seen:
                found.append(t)
                seen.add(t.tweak_id)
    # Tweaks applied but no longer in option sets are LIGHT tweaks that
    # were removed by _apply_light_tweak — we can't recover them here
    # for delta sums in v1.0. v1.x: keep a separate applied_history.
    return tuple(found)


def _sum_cost_impacts(tweaks: tuple[TweakOption, ...]) -> Optional[TransparencyTriple]:
    """Sum cost_impacts. Returns None if no tweaks."""
    if not tweaks:
        return None
    total_mid = sum(t.cost_impact.exact_value for t in tweaks)
    # Uncertainty: take max of input uncertainties (conservative)
    max_unc = max((t.cost_impact.uncertainty_pct for t in tweaks), default=30.0)
    derivation: list[DerivationLine] = []
    for t in tweaks:
        derivation.append(DerivationLine(
            label=f"Tweak {t.tweak_id} ({t.tweak_category})",
            amount=t.cost_impact.exact_value,
            source=f"tweak {t.tweak_id}",
        ))
    return TransparencyTriple(
        label="Total cost delta across applied tweaks",
        exact_value=total_mid,
        unit="INR",
        uncertainty_pct=max_unc,
        confidence=Confidence.MEDIUM,
        derivation=derivation,
        notes=[
            f"Sum of {len(tweaks)} applied tweak{'s' if len(tweaks) != 1 else ''}",
        ],
    )


def _sum_space_impacts(
    tweaks:              tuple[TweakOption, ...],
    base_carpet_sqft:    float,
) -> Optional[SpaceImpact]:
    """Sum space_impacts across applied tweaks."""
    if not tweaks:
        return None
    total_delta = sum(t.space_impact.total_sqft_delta for t in tweaks)
    # Per-room aggregation: keep last delta per room (heuristic)
    per_room_map: dict[str, float] = {}
    for t in tweaks:
        for (room_id, delta) in t.space_impact.per_room_sqft_delta:
            per_room_map[room_id] = per_room_map.get(room_id, 0.0) + delta
    per_room_sorted = tuple(sorted(per_room_map.items(), key=lambda x: x[0]))

    # Ensure under ceiling (spec § 6)
    from ..versioning import TWEAK_SPACE_IMPACT_CEILING_SQFT
    if abs(total_delta) > TWEAK_SPACE_IMPACT_CEILING_SQFT:
        # Cap the total to ceiling for SpaceImpact construction validity;
        # log advisory
        total_delta = (
            TWEAK_SPACE_IMPACT_CEILING_SQFT if total_delta > 0
            else -TWEAK_SPACE_IMPACT_CEILING_SQFT
        )

    return SpaceImpact(
        per_room_sqft_delta=per_room_sorted,
        total_sqft_delta=total_delta,
        total_carpet_area_after=AttestedValue(
            value=base_carpet_sqft + total_delta,
            authority=AuthorityKind.LOCALLY_DERIVED,
            upstream_source=None,
            derivation_note=(
                f"Sum across {len(tweaks)} applied tweaks; "
                f"base carpet {base_carpet_sqft:.0f} sqft + Δ {total_delta:+.0f}"
            ),
        ),
        advisory_note=(
            f"Net area change of {total_delta:+.0f} sqft across "
            f"{len(tweaks)} applied tweak{'s' if len(tweaks) != 1 else ''}."
        ),
    )


def run_phase_zeta(
    session:           TradeoffSession,
    config:            C3bRuntimeConfig,
    base_carpet_sqft:  float = 1000.0,
) -> TradeoffSession:
    """Execute Phase ζ. Session must be in 'resolved_selection_ready' state
    (or a terminal state with resolved_selection populated).

    Updates the resolved_selection with summed deltas and re-signs."""
    from .alpha import _resign_session

    if session.resolved_selection is None:
        raise LocalTradeoffError(
            f"Phase ζ called on session without resolved_selection; "
            f"current_status={session.current_status!r}",
            session_id=session.session_id, phase="zeta",
        )

    applied_tweaks = _find_applied_tweaks(session)
    total_cost = _sum_cost_impacts(applied_tweaks)
    total_space = _sum_space_impacts(applied_tweaks, base_carpet_sqft)

    rs = session.resolved_selection
    new_rs = dataclasses.replace(
        rs,
        total_cost_delta=total_cost,
        total_space_delta=total_space,
    )
    new_session = dataclasses.replace(session, resolved_selection=new_rs)
    return _resign_session(new_session, config)





# ══════════════════════════════════════════════════════════════════════════════
# § session_storage                                             
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Session persistence (SQLite WAL)
=========================================

Spec § 9.1 B-C3B-SESSION-PERSISTENCE-WAL-RETROFIT: SQLite WAL mode +
retry + corruption recovery, mirroring C3a's GateStateStorage
hardening (S6 ownership pattern).

Per spec § 3 Phase δ: 'Persist session to SQLite (WAL mode, per S6
ownership inheritance from C3a precedent).'

Storage schema:
  CREATE TABLE c3b_sessions (
    session_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    canonical_replay_signature TEXT NOT NULL,
    presentation_signature TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    last_updated_offset_ms INTEGER NOT NULL DEFAULT 0
  )

The payload_json is the full TradeoffSession serialized via
dataclasses.asdict + json.dumps. Recovery: load by session_id,
deserialize via dataclass reconstruction.

Rule 11 self-analysis:
  1. SQLite WAL has known performance characteristics. For C3b's
     session-state writes (1 write per user action, max 7 actions
     per session per iteration_cap), throughput is non-issue. We
     enable WAL primarily for crash safety (write-ahead log).
  2. The session_id is the natural primary key — UUID-based, no
     collisions. Concurrent updates to the same session_id is a
     user-flow violation (same user shouldn't have two parallel
     C3b sessions on the same brief); we use REPLACE semantics
     (last-write-wins) which matches the single-linear-history
     R16 invariant.
  3. Serialization uses cache_keys._canon for canonicalization. That
     ensures the SAME object always serializes to the SAME bytes —
     useful for verifying signatures match after deserialize/reserialize.
  4. Deserialization rebuilds dataclasses from dicts. We use a
     helper that walks the schema; the schema is stable per
     C3B_SESSION_SCHEMA_VERSION pin.
  5. Recovery path: if schema_version doesn't match
     C3B_SESSION_SCHEMA_VERSION, refuse to deserialize and raise
     SessionPersistenceError (caller decides retry / migrate / abort).
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from .errors import SessionPersistenceError
from .schema import TradeoffSession
from .versioning import C3B_SESSION_SCHEMA_VERSION


_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SEC = 0.05


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS c3b_sessions (
            session_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            canonical_replay_signature TEXT NOT NULL,
            presentation_signature TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            last_updated_offset_ms INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()


@contextmanager
def _open_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with WAL mode. Retries on transient
    failures (e.g., database locked by another process)."""
    last_exc: Optional[Exception] = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            conn = sqlite3.connect(str(db_path), isolation_level=None)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                _ensure_schema(conn)
                yield conn
            finally:
                conn.close()
            return
        except sqlite3.OperationalError as e:
            last_exc = e
            time.sleep(_RETRY_BACKOFF_SEC * (2 ** attempt))
    raise SessionPersistenceError(
        f"Failed to open SQLite after {_RETRY_ATTEMPTS} attempts: {last_exc}",
        operation="open",
    )


# ============================================================
# § 1 — Serialization helpers
# ============================================================

def _serialize_session(session: TradeoffSession) -> str:
    """Serialize via dataclasses.asdict + json.dumps with sort_keys.

    Handles StrEnum and AuthorityKind (enum) via default encoder
    custom hook."""
    import dataclasses

    def _enc(o):
        # Enum / StrEnum
        if hasattr(o, "value") and not callable(o.value):
            return o.value
        # Sets → sorted lists
        if isinstance(o, (set, frozenset)):
            return sorted(o, key=lambda x: str(x))
        # Bytes → hex
        if isinstance(o, bytes):
            return o.hex()
        raise TypeError(f"Cannot serialize {type(o).__name__}")

    asdict = dataclasses.asdict(session)
    return json.dumps(asdict, sort_keys=True, default=_enc, separators=(",", ":"))


def _deserialize_session(payload_json: str) -> TradeoffSession:
    """Deserialize a TradeoffSession from JSON payload.

    Schema-version mismatch raises SessionPersistenceError per
    Rule 11 self-analysis pt 5."""
    raw = json.loads(payload_json)
    if raw.get("c3b_schema_version") != C3B_SESSION_SCHEMA_VERSION:
        raise SessionPersistenceError(
            f"Stored session schema_version="
            f"{raw.get('c3b_schema_version')!r} mismatches current "
            f"{C3B_SESSION_SCHEMA_VERSION}. Run a migration or refuse to load.",
            operation="deserialize",
        )

    # Reconstruct dataclass tree. Use a builder that walks each known
    # dataclass field — this is verbose but robust to dataclass renames.
    return _reconstruct_session(raw)


def _reconstruct_session(raw: dict) -> TradeoffSession:
    """Rebuild a TradeoffSession from a plain-dict payload.

    Walks the dataclass schema field-by-field, calling the dataclass
    constructors so __post_init__ invariants fire (defense-in-depth
    on stored data integrity)."""
    from .contracts import AttestedValue, AuthorityKind
    from .schema import (
        AdvisoryFlag,
        ApplyOutcome,
        ApplySpecification,
        CompatibilityAssertion,
        ComfortImpact,
        FinishSchedulePayload,
        GeometryLocalPayload,
        KickBackPayload,
        MutationEnvelope,
        ResolvedSelection,
        SessionTurn,
        SpaceImpact,
        SubsetRerunRequest,
        TopologyInvarianceResult,
        TweakOption,
        TweakOptionSet,
        TweakProvenance,
    )
    from buildemup.utils.confidence import Confidence
    from buildemup.utils.transparency import DerivationLine, TransparencyTriple

    def _tt(d):
        if d is None:
            return None
        return TransparencyTriple(
            label=d["label"],
            exact_value=d["exact_value"],
            unit=d["unit"],
            uncertainty_pct=d["uncertainty_pct"],
            confidence=Confidence(d["confidence"]),
            derivation=[DerivationLine(**dd) for dd in d["derivation"]],
            notes=list(d.get("notes", [])),
        )

    def _av(d):
        if d is None:
            return None
        return AttestedValue(
            value=d["value"],
            authority=AuthorityKind(d["authority"]),
            upstream_source=d.get("upstream_source"),
            derivation_note=d.get("derivation_note"),
        )

    def _si(d):
        if d is None:
            return None
        return SpaceImpact(
            per_room_sqft_delta=tuple(
                (t[0], t[1]) for t in d["per_room_sqft_delta"]
            ),
            total_sqft_delta=d["total_sqft_delta"],
            total_carpet_area_after=_av(d["total_carpet_area_after"]),
            advisory_note=d.get("advisory_note", ""),
        )

    def _ci(d):
        if d is None:
            return None
        return ComfortImpact(
            dimensions_affected=tuple(d["dimensions_affected"]),
            direction=d["direction"],
            magnitude=d["magnitude"],
            advisory_note=d.get("advisory_note", ""),
            # v0.5 A7 — emotional heuristic fields
            perceived_spaciousness=d.get("perceived_spaciousness"),
            arrival_impression=d.get("arrival_impression"),
            family_gathering_comfort=d.get("family_gathering_comfort"),
        )

    def _tir(d):
        if d is None:
            return None
        return TopologyInvarianceResult(
            source_topology=d["source_topology"],
            predicted_topology=d["predicted_topology"],
            invariance_preserved=d["invariance_preserved"],
            prediction_basis=d["prediction_basis"],
            advisory_note=d.get("advisory_note"),
        )

    def _ca(d):
        return CompatibilityAssertion(
            against_applied_tweak_id=d["against_applied_tweak_id"],
            compatibility_kind=d["compatibility_kind"],
            result=d["result"],
            advisory_note=d.get("advisory_note"),
        )

    def _srr(d):
        if d is None:
            return None
        return SubsetRerunRequest(
            trigger_tweak_id=d["trigger_tweak_id"],
            trigger_tweak_category=d["trigger_tweak_category"],
            components_to_rerun=tuple(d["components_to_rerun"]),
            downstream_impact_set=tuple(d["downstream_impact_set"]),
            topology_invariance_check=_tir(d["topology_invariance_check"]),
            expected_completion_seconds=d["expected_completion_seconds"],
            rerun_anchor=d["rerun_anchor"],
            compatibility_assertions=tuple(
                _ca(x) for x in d.get("compatibility_assertions", [])
            ),
        )

    def _glp(d):
        if d is None:
            return None
        return GeometryLocalPayload(
            new_room_function_assignments=tuple(
                (t[0], t[1]) for t in d["new_room_function_assignments"]
            ),
            new_door_placements_replace=tuple(d["new_door_placements_replace"]),
            new_window_assignments=tuple(
                (t[0], int(t[1])) for t in d["new_window_assignments"]
            ),
            advisory_note=d.get("advisory_note", ""),
        )

    def _fsp(d):
        if d is None:
            return None
        return FinishSchedulePayload(
            room_finish_overrides=tuple(
                (t[0], t[1], t[2]) for t in d["room_finish_overrides"]
            ),
            advisory_note=d.get("advisory_note", ""),
        )

    def _asp(d):
        return ApplySpecification(
            mutation_kind=d["mutation_kind"],
            geometry_local_payload=_glp(d.get("geometry_local_payload")),
            subset_rerun_payload=_srr(d.get("subset_rerun_payload")),
            finish_schedule_payload=_fsp(d.get("finish_schedule_payload")),
        )

    def _tp(d):
        return TweakProvenance(
            motivated_by_check_id=d.get("motivated_by_check_id"),
            motivated_by_grid_cell_id=d.get("motivated_by_grid_cell_id"),
            motivated_by_orientation=d.get("motivated_by_orientation"),
            generation_basis=d.get("generation_basis", ""),
        )

    def _kbp(d):
        if d is None:
            return None
        return KickBackPayload(
            target_brief_field=d["target_brief_field"],
            target_brief_field_advisory=d["target_brief_field_advisory"],
            user_requested_change=d["user_requested_change"],
            proposed_change_summary=d["proposed_change_summary"],
        )

    def _me(d):
        return MutationEnvelope(
            envelope_id=d["envelope_id"],
            requested_change_summary=d["requested_change_summary"],
            classification=d["classification"],
            why_not_a_tweak=d["why_not_a_tweak"],
            suggested_pathway=d["suggested_pathway"],
            estimated_pathway_effort=d["estimated_pathway_effort"],
            advisory_note=d["advisory_note"],
            kick_back_payload=_kbp(d.get("kick_back_payload")),
            # v0.5 A6
            speculative_preview_text=d.get("speculative_preview_text"),
        )

    def _to(d):
        return TweakOption(
            tweak_id=d["tweak_id"],
            tweak_category=d["tweak_category"],
            severity_tier=d["severity_tier"],
            affected_room_ids=tuple(d["affected_room_ids"]),
            affected_grid_cells=tuple(d["affected_grid_cells"]),
            description=d["description"],
            cost_impact=_tt(d["cost_impact"]),
            space_impact=_si(d["space_impact"]),
            comfort_impact=_ci(d["comfort_impact"]),
            problem_report_links=tuple(d["problem_report_links"]),
            recommendation_flag=d["recommendation_flag"],
            apply_specification=_asp(d["apply_specification"]),
            provenance=_tp(d["provenance"]),
            presented_count=d.get("presented_count", 0),
        )

    def _tos(d):
        return TweakOptionSet(
            layout_id=d["layout_id"],
            layout_archetype=d["layout_archetype"],
            source_problem_report_id=d["source_problem_report_id"],
            tweaks=tuple(_to(t) for t in d["tweaks"]),
            overall_advisory_note=d["overall_advisory_note"],
        )

    def _ao(d):
        if d is None:
            return None
        return ApplyOutcome(
            apply_status=d["apply_status"],
            error_summary=d.get("error_summary"),
            new_layout_signature=d.get("new_layout_signature"),
            new_problem_report_id=d.get("new_problem_report_id"),
            regression_detected=d.get("regression_detected", False),
            newly_critical_check_ids=tuple(d.get("newly_critical_check_ids", [])),
        )

    def _st(d):
        return SessionTurn(
            turn_id=d["turn_id"],
            iteration_index=d["iteration_index"],
            timestamp_offset_ms=d["timestamp_offset_ms"],
            presented_tweaks=tuple(d["presented_tweaks"]),
            user_action=d["user_action"],
            chosen_tweak_id=d.get("chosen_tweak_id"),
            apply_outcome=_ao(d.get("apply_outcome")),
            post_turn_status=d.get("post_turn_status", "open_for_user_input"),
            # v0.5 A4
            strategic_advisory_text=d.get("strategic_advisory_text"),
        )

    def _rs(d):
        if d is None:
            return None
        return ResolvedSelection(
            chosen_layout_id=d["chosen_layout_id"],
            chosen_layout_archetype=d["chosen_layout_archetype"],
            applied_tweaks=tuple(d["applied_tweaks"]),
            final_layout_signature=d["final_layout_signature"],
            final_problem_report_id=d.get("final_problem_report_id"),
            total_cost_delta=_tt(d.get("total_cost_delta")),
            total_space_delta=_si(d.get("total_space_delta")),
            final_handoff_advisory=d.get("final_handoff_advisory", ""),
        )

    def _af(d):
        return AdvisoryFlag(
            flag_id=d["flag_id"],
            kind=d["kind"],
            advisory_note=d["advisory_note"],
            related_ids=tuple(d.get("related_ids", [])),
        )

    return TradeoffSession(
        session_id=raw["session_id"],
        source_selection_result_id=raw["source_selection_result_id"],
        source_brief_signature=raw["source_brief_signature"],
        source_plot_analysis_id=raw["source_plot_analysis_id"],
        c3b_version=raw["c3b_version"],
        c3b_schema_version=raw["c3b_schema_version"],
        jurisdiction_profile_id=raw["jurisdiction_profile_id"],
        tweak_option_sets=tuple(_tos(s) for s in raw["tweak_option_sets"]),
        session_history=tuple(_st(t) for t in raw["session_history"]),
        iteration_count=raw["iteration_count"],
        iteration_cap=raw["iteration_cap"],
        current_status=raw["current_status"],
        canonical_replay_signature=raw["canonical_replay_signature"],
        presentation_signature=raw["presentation_signature"],
        schema_descriptor_digest=raw["schema_descriptor_digest"],
        resolved_selection=_rs(raw.get("resolved_selection")),
        advisory_flags=tuple(_af(f) for f in raw.get("advisory_flags", [])),
        mutation_envelopes=tuple(_me(e) for e in raw.get("mutation_envelopes", [])),
        # v0.5 A2
        medium_tweak_count_since_full_recompute=raw.get(
            "medium_tweak_count_since_full_recompute", 0,
        ),
    )


# ============================================================
# § 2 — Storage API
# ============================================================

class C3bSessionStorage:
    """Persistent session storage backed by SQLite WAL.

    Usage:
        storage = C3bSessionStorage(Path("/tmp/c3b.db"))
        storage.save(session)
        restored = storage.load(session.session_id)
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        # Touch the DB file + ensure schema
        with _open_connection(self.db_path):
            pass

    def save(self, session: TradeoffSession) -> None:
        """Persist a session. REPLACE semantics on (session_id)."""
        payload = _serialize_session(session)
        last_offset = (
            session.session_history[-1].timestamp_offset_ms
            if session.session_history else 0
        )
        try:
            with _open_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO c3b_sessions (
                        session_id, schema_version,
                        canonical_replay_signature, presentation_signature,
                        payload_json, last_updated_offset_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.session_id,
                        session.c3b_schema_version,
                        session.canonical_replay_signature,
                        session.presentation_signature,
                        payload,
                        last_offset,
                    ),
                )
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to save session {session.session_id!r}: {e}",
                operation="write",
            ) from e

    def load(self, session_id: str) -> Optional[TradeoffSession]:
        """Load a session by id. Returns None if not found."""
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT payload_json FROM c3b_sessions WHERE session_id = ?",
                    (session_id,),
                )
                row = cur.fetchone()
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to load session {session_id!r}: {e}",
                operation="read",
            ) from e
        if row is None:
            return None
        return _deserialize_session(row[0])

    def delete(self, session_id: str) -> bool:
        """Delete a session by id. Returns True if deleted, False if absent."""
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "DELETE FROM c3b_sessions WHERE session_id = ?",
                    (session_id,),
                )
                return cur.rowcount > 0
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to delete session {session_id!r}: {e}",
                operation="delete",
            ) from e

    def list_session_ids(self) -> tuple[str, ...]:
        """List all stored session ids (lex-ASC for replay determinism)."""
        try:
            with _open_connection(self.db_path) as conn:
                cur = conn.execute(
                    "SELECT session_id FROM c3b_sessions ORDER BY session_id ASC"
                )
                return tuple(row[0] for row in cur.fetchall())
        except sqlite3.Error as e:
            raise SessionPersistenceError(
                f"Failed to list sessions: {e}",
                operation="read",
            ) from e





# ══════════════════════════════════════════════════════════════════════════════
# § orchestrator                                                
# ══════════════════════════════════════════════════════════════════════════════
"""
C3b — Orchestrator (top-level entry points)
=============================================

The orchestrator wires Phases α → β → γ → δ at session start, and
Phase ε at each user action, with Phase ζ at resolution time.
Optionally persists each transition via C3bSessionStorage.

Spec § 3 — orchestration flow:
  start_session:
    Phase α → Phase β → Phase γ → Phase δ
  apply_user_action_orchestrated:
    Phase ε  (then Phase ζ if action resolved/abandoned the session)
  complete_subset_rerun_orchestrated:
    R14 regression detection in Phase ε.complete_subset_rerun
  finalize_session:
    Phase ζ explicit

Rule 11 self-analysis:
  1. The orchestrator is the ONLY surface that calls phases by name.
     User code interacts via start_session / apply_user_action /
     complete_subset_rerun / finalize_session. Phase internals are
     not part of the public C3b API.
  2. Persistence is opt-in (storage parameter). When provided, every
     successful state transition writes to SQLite. When None, the
     orchestrator runs purely in-memory.
  3. STRICT-mode errors propagate to the caller. WARN-mode errors
     are absorbed inside the phases; the orchestrator does NOT need
     to inspect them (Phase γ already dropped offending tweaks).
"""
from __future__ import annotations

from typing import Optional

from buildemup.components.c15.schema import ProblemReport

from .config import C3bRuntimeConfig, DEFAULT_CONFIG
from .contracts import C3bInputBundle
from .phases.alpha import run_phase_alpha
from .phases.beta import run_phase_beta
from .phases.delta import run_phase_delta
from .phases.epsilon import (
    UserActionRequest,
    apply_user_action,
    complete_subset_rerun,
)
from .phases.gamma import run_phase_gamma
from .phases.zeta import run_phase_zeta
from .schema import TradeoffSession
from .session_storage import C3bSessionStorage


def start_session(
    bundle:   C3bInputBundle,
    config:   C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:  Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Start a new C3b tradeoff session.

    Runs Phase α (canonicalization + applicability) → Phase β (tweak
    generation) → Phase γ (impact verification) → Phase δ (presentation
    + signing). If the applicability check fails in Phase α, returns
    a terminal session immediately (status='abandoned_no_tweaks').

    If `storage` is provided, persists the session after each phase
    transition."""
    session = run_phase_alpha(bundle, config)

    # If Phase α produced a terminal session, skip downstream phases
    if session.current_status == "abandoned_no_tweaks":
        if storage is not None:
            storage.save(session)
        return session

    session = run_phase_beta(session, bundle, config)
    session = run_phase_gamma(session, config)
    session = run_phase_delta(session, config)

    if storage is not None:
        storage.save(session)
    return session


def apply_user_action_orchestrated(
    session:  TradeoffSession,
    request:  UserActionRequest,
    config:   C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:  Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Apply one user action via Phase ε and persist."""
    new_session = apply_user_action(session, request, config)
    if storage is not None:
        storage.save(new_session)
    return new_session


def complete_subset_rerun_orchestrated(
    session:           TradeoffSession,
    applied_tweak_id:  str,
    pre_rerun_pr:      ProblemReport,
    post_rerun_pr:     ProblemReport,
    config:            C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:           Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Complete a subset rerun with R14 regression detection + persist."""
    new_session = complete_subset_rerun(
        session, applied_tweak_id, pre_rerun_pr, post_rerun_pr, config,
    )
    if storage is not None:
        storage.save(new_session)
    return new_session


def finalize_session(
    session:           TradeoffSession,
    config:            C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    base_carpet_sqft:  float = 1000.0,
    storage:           Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Run Phase ζ explicitly on a session whose user action already
    set resolved_selection (typically 'finalized_layout_choice' or
    'abandoned_session'). Sums cost / space deltas + re-signs."""
    new_session = run_phase_zeta(session, config, base_carpet_sqft)
    if storage is not None:
        storage.save(new_session)
    return new_session





# ════════════════════════════════════════════════════════════════════════════════
# § END OF C3b v0.5 LOCKED CONSOLIDATED SOURCE
# ════════════════════════════════════════════════════════════════════════════════
# Lines: see wc -l output at top of generation.
# Tests: 415 passing in tests/test_c03b/ (3 skipped, 0 failed).
# To regenerate from the modular source tree, see /tmp/build_consolidated.py.
