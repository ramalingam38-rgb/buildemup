"""
BuildemUp — Component 15 — versioning constants
================================================

Per C15 SPEC v0.2 LOCKED (composition of v0.1 PROPOSED + v0.2 DELTA).

LOCKED constants this module exposes:

| Constant                              | Value      | Source                          |
|---------------------------------------|------------|---------------------------------|
| C15_VERSION                           | "v0.2"     | v0.2 LOCK at S46                |
| C15_CHECK_REGISTRY_VERSION            | 1          | v0.1 § 0.7 / Inv P15            |
| EXPECTED_C14_VERSION                  | "v0.2"     | C14 LOCKED at S46               |
| EXPECTED_C14_METRIC_VERSION           | 2          | C14 v0.2 A1 (RA → RRA)          |
| EXPECTED_ADVISORY_SCHEMA_VERSION      | 1          | Probed from C14 at ingress      |
| DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS  | 1.5        | v0.1 § 6 (per-candidate budget) |
| DEFAULT_PER_BATCH_WALLCLOCK_SECS      | 15.0       | v0.1 § 6 (batch budget)         |
| MIN_SEVERITY_BASIS_LENGTH             | 20         | v0.2 A4 Inv P18                 |

Bump rules (mirroring C13/C14 versioning modules):
- Removing public type / field / invariant → MAJOR (v1.0 → v2.0)
- Adding invariant / failure type / cache-relevant amendment that affects
  output identity → MINOR (v0.2 → v0.3); paired with bump of
  C15_CHECK_REGISTRY_VERSION when the check semantics change
- Telemetry-only / prose-only changes → PATCH

v0.2 LOCK is SKETCH-level per the C13 v0.6 / C14 v0.2 LOCK-gating
convention reused here. v0.3+ amendments during implementation refine
the SKETCH toward eventual v1.0 LOCK.

Per Inv P0 (v0.2 A1 STRICTER): C15 NEVER computes a single number
representing layout quality, anywhere — not in a public API, not in a
private helper, not in telemetry, not in cache keys. This module
contains constants only; no aggregation logic.
"""
from __future__ import annotations

from typing import Final


# =============================================================================
# C15_VERSION — the canonical component version string
# =============================================================================

C15_VERSION: Final[str] = "v0.2"
"""The LOCKED C15 version string per Ramalingam S46 LOCK directive:
"Lock this and give me the handoff..." — S46.

LOCK level: SKETCH. v0.3+ critique walks during implementation refine
the SKETCH toward eventual v1.0 LOCK (mirroring the C13 v0.6→v1.0 and
C14 v0.2→v1.0 paths).

Captured into ProblemAnalysisBatchResult.c15_version so cache lookups
invalidate cleanly when this string changes.

Bumped when:
- The public API surface changes (per v0.2 A1, A2, A5, A6, A7, A10
  cache-relevance markings)
- A schema-level field is added/removed from any frozen dataclass
  in `schema.py`
- An invariant (P0-P19) is added/removed or strengthened
"""


# =============================================================================
# Check registry version (per v0.1 Inv P15)
# =============================================================================

C15_CHECK_REGISTRY_VERSION: Final[int] = 1
"""Per v0.1 Inv P15. The semantic version of the C15 check registry +
severity-rule table.

Bumped when:
- A new check is added to the registry (governed by § 14.1 gate from
  v0.2 A8 once v1.0 ships; pre-v1.0 walks can amend more freely)
- An existing check's measurement formula or threshold changes
- An existing check's epistemic_kind changes (rare — Inv P15)
- The severity-rule table changes a (check_id, status) → severity
  mapping for any cultural_profile
- The severity_basis citation text changes for any rule (per A4)

NOT bumped when:
- New CulturalProfile sub-variants are added that don't affect existing
  check behavior (but DO bump if they amend severity rules)
- Adding a new ProblemAnalysisMetadata field that no check reads yet
- Adding telemetry events
- Prose-only documentation changes

At v0.2 LOCK SKETCH, the registry is v1 — placeholder. The full check
set + measurement formulas + severity rules will be locked under:
- B-C15-CHECK-REGISTRY-LOCK
- B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
- B-C15-SEVERITY-RULE-TABLE-LOCK
…all LOCK-mandatory for v1.0.
"""


# =============================================================================
# Expected upstream schema versions
# =============================================================================

EXPECTED_C14_VERSION: Final[str] = "v0.2"
"""C15 was built against C14 v0.2 (LOCKED at S46). Phase π ingress
asserts upstream c14_version equals this; mismatch raises
UpstreamSchemaDriftError (LocalProblemError; always halts).

Inv P11: C15 trusts upstream invariants (D11.1, D13, D17, E3', etc.).
Schema-drift detection at ingress is the only check; C15 does NOT
re-verify the invariants themselves."""

EXPECTED_C14_METRIC_VERSION: Final[int] = 2
"""Per C14 v0.2 A1, C14_METRIC_VERSION = 2 (raised from 1 for the
RA → RRA transition). C15 stamps it onto ProblemReport for cache
chain provenance; mismatch at ingress raises UpstreamSchemaDriftError."""

EXPECTED_ADVISORY_SCHEMA_VERSION: Final[int] = 1
"""Per C13 v0.4 / C14 v0.2, ADVISORY_SCHEMA_VERSION = 1 at the LOCKED
upstream chain. C15 passes this through to its output (Inv P16 chain
consistency) — never bumps it. Mismatch at ingress raises
UpstreamSchemaDriftError."""


# =============================================================================
# Default performance budgets (per v0.1 § 6)
# =============================================================================

DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS: Final[float] = 1.5
"""Per v0.1 § 6. Per-candidate wallclock budget.

Budget allows ~40 checks at O(k) each where k = room count. Exceeding
it raises a per-candidate timeout, which under STRICT halts the batch,
under WARN packages a FailedProblemAnalysis.

Cache-relevant: NO. Performance budget does NOT change the output of
successful candidates (Inv P2 byte-equal replay).

Configurable via ProblemFinderConfig.per_candidate_wallclock_seconds."""

DEFAULT_PER_BATCH_WALLCLOCK_SECS: Final[float] = 15.0
"""Per v0.1 § 6. Per-batch wallclock budget (50 candidates default).

Soft signal at v0.2 — the orchestrator reports total elapsed time but
does NOT abort the batch on overflow at v0.2. v1.0 may upgrade to a
hard cap with TRUNCATION_META semantics analogous to C14 A6.

Cache-relevant: NO."""


# =============================================================================
# Severity-basis minimum length (per v0.2 A4 Inv P18)
# =============================================================================

MIN_SEVERITY_BASIS_LENGTH: Final[int] = 20
"""Per v0.2 A4 Inv P18.

Every severity rule MUST carry a `severity_basis` citation string of
at least this many characters. Empty strings or strings shorter than
20 characters fail registration at module load (CheckRegistryError,
which is a LocalProblemError → always halts).

The threshold of 20 is chosen as the minimum that allows a meaningful
citation (e.g., "NBC India 2016 §6.2.1" = 21 chars). Below this, the
citation is effectively missing.

Cache-relevant: YES (the threshold is part of the registry contract;
changing it would invalidate every severity rule that previously passed
but now fails — bump C15_CHECK_REGISTRY_VERSION)."""


# =============================================================================
# Dimensions surface — 10 dimensions per v0.1 § 1.4
# =============================================================================

TOTAL_DIMENSIONS: Final[int] = 10
"""Per v0.1 § 1.4. The 10 dimensions of residential lived quality:

1. No wasted space (Neufert / FAR)
2. Room sizes match function (Neufert / Ching)
3. Logical flow (Hillier 1984/1987 / van Hoogdalem 1985)
4. Natural light (Reinhart 2014 / LEED IEQc8) — PARTIAL at v1
5. Privacy (Altman 1975 / Hillier 1984)
6. No bottlenecks (Hillier 1984 betweenness)
7. First-floor living (Lifetime Homes UK) — PARTIAL at v1
8. Outdoor connection (Kellert 2008 biophilic) — PARTIAL at v1
9. Storage (Neufert / Indian residential POE) — NOT-RUNNABLE at v1
10. Multi-functional (Brand 1994) — NOT-RUNNABLE at v1

Dimension IDs are 1-indexed and STABLE across versions (Inv P15
analog at dimension level)."""


MIN_DIMENSION_ID: Final[int] = 1
"""Lowest legal dimension_id. See TOTAL_DIMENSIONS for upper bound."""

MAX_DIMENSION_ID: Final[int] = 10
"""Highest legal dimension_id. See TOTAL_DIMENSIONS for upper bound."""


# =============================================================================
# Dimensions-not-evaluated baseline (per v0.2 A6 Inv P19)
# =============================================================================

DIMENSIONS_NOT_EVALUATED_V1: Final[tuple[str, ...]] = (
    "acoustic_experience_inside_rooms",
    "aesthetic_taste_traditional_vs_modern",
    "emotional_comfort_and_memory_of_place",
    "future_adaptability_unanticipated_changes",
    "long_term_family_habit_evolution",
    "olfactory_experience",
    "ritual_and_ceremonial_use_specifics",
    "social_relationships_supported_by_layout",
    "sunlight_mood_throughout_day_and_year",
    "tactile_material_quality",
)
"""Per v0.2 A6 + Inv P19.

The baseline 10 categories of habitation that C15 explicitly DOES NOT
evaluate. ProblemReport carries this (or an extension thereof) as
`dimensions_not_evaluated`, making the incompleteness visible at the
artifact level rather than buried in spec prose.

Inv P19: `ProblemReport.dimensions_not_evaluated` is non-empty at
every report. Empty = bug, fails report construction.

Ordering: lex-ASC for Inv P2 replay determinism. UX consumers MUST
present this in display order chosen at render time (e.g., grouped
by severity-of-omission), NOT raw lex-ASC.

UX consumers MUST render this in a "what we don't check" section.

Future cultural profiles or future-extension orchestrators MAY append
to this tuple (e.g., for region-specific exclusions), but the v1
baseline 10 entries are always present.

Cache-relevant: YES (changes here change the report content;
bump C15_VERSION)."""


__all__ = [
    "C15_VERSION",
    "C15_CHECK_REGISTRY_VERSION",
    "EXPECTED_C14_VERSION",
    "EXPECTED_C14_METRIC_VERSION",
    "EXPECTED_ADVISORY_SCHEMA_VERSION",
    "DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS",
    "DEFAULT_PER_BATCH_WALLCLOCK_SECS",
    "MIN_SEVERITY_BASIS_LENGTH",
    "TOTAL_DIMENSIONS",
    "MIN_DIMENSION_ID",
    "MAX_DIMENSION_ID",
    "DIMENSIONS_NOT_EVALUATED_V1",
]
