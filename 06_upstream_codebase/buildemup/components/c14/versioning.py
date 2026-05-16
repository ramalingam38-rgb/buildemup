"""
BuildemUp — Component 14 — versioning constants
================================================

Per C14 SPEC v0.2 LOCKED (composition of v0.1 PROPOSED + v0.2 DELTA).

LOCKED constants this module exposes:

| Constant                          | Value      | Source                          |
|-----------------------------------|------------|---------------------------------|
| C14_VERSION                       | "v0.2"     | v0.1 § 0.5; v0.2 LOCK at S46    |
| C14_METRIC_VERSION                | 2          | v0.2 A1 (RA → RRA) bumped from 1 |
| ADVISORY_SCHEMA_VERSION_EXPECTED  | 1          | Probed from C13 at ingress       |
| EXPECTED_C13_VERSION              | "v1.0"     | C13 LOCKED at S45                |
| DEFAULT_FLAG_DENSITY_FACTOR       | 0.75       | v0.1 Inv E13 / v0.2 A6 Inv E13'  |
| DEFAULT_BETWEENNESS_THRESHOLD     | 0.7        | v0.1 § 1.3 BOTTLENECK_CONCENTRATION |
| DEFAULT_EXCESSIVE_DEPTH_THRESHOLD | 5          | v0.1 § 1.3 EXCESSIVE_DEPTH       |
| DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD | 0.5  | v0.2 A8 category_coverage_low    |

Bump rules (mirroring C13 versioning module):
- Removing public type / field / invariant → MAJOR
- Adding invariant / failure type / cache_relevant flip / changed default
  that affects output identity → MINOR
- Telemetry-only / non-cache field changes / prose-only wording → PATCH

v0.2 LOCK is SKETCH-level per the C13 v0.6 LOCK-gating convention reused
here. v0.3+ amendments during implementation refine the SKETCH toward
eventual v1.0 LOCK. Fast-revision-window patches (90 days post v1.0
LOCK) may ship without MINOR bumps if they preserve LOCKED contracts.
"""
from __future__ import annotations

from typing import Final


# =============================================================================
# C14_VERSION — the canonical component version string
# =============================================================================

C14_VERSION: Final[str] = "v0.2"
"""The LOCKED C14 version string per Ramalingam S46 LOCK directive:
"Lock this and let's move on to c15 spec doc" — S46.

LOCK level: SKETCH. v0.3+ critique walks during implementation refine
the SKETCH toward eventual v1.0 LOCK (mirroring the C13 v0.6→v1.0 path).

Captured into CirculationAnalysisBatchResult.c14_version so cache
lookups invalidate cleanly when this string changes."""


# =============================================================================
# Metric version (per v0.2 A1)
# =============================================================================

C14_METRIC_VERSION: Final[int] = 2
"""Per v0.2 A1. The semantic version of the C14 metric formulas.

v0.2 bumped from 1 to 2 because A1 replaced raw RA (Hillier 1984) with
RRA (Hillier 1987). Same metric NAMES, different semantic formulas.
Composed cache keys must carry this constant so v0.1-era cached
results don't silently feed v0.2-era consumers.

Bump rules (per A1 / A4 / A5 / A6 / A8 / A10 cache-relevance markings):
- ANY semantic formula change for an existing metric → bump
- Adding a new metric → bump
- Changing default severity (A10) → bump
- Schema field addition (A4 structural/preference split, A6 truncation
  meta, A8 category_coverage) → bump C14_VERSION as well

NOT bumped on:
- Telemetry-only emission changes
- Prose-only documentation
"""


# =============================================================================
# Expected upstream schema versions
# =============================================================================

EXPECTED_C13_VERSION: Final[str] = "v1.0"
"""C14 was built against C13 v1.0 (LOCKED at S45). Phase 0 ingress
asserts upstream C13_VERSION equals this; mismatch raises
UpstreamSchemaDriftError."""

EXPECTED_ADVISORY_SCHEMA_VERSION: Final[int] = 1
"""Per C13 v0.4 C8, ADVISORY_SCHEMA_VERSION = 1 at C13 v1.0 LOCK.

C14 passes this through to its output (Inv E9 / E16) — never bumps it.
Mismatch at ingress raises UpstreamSchemaDriftError."""


# =============================================================================
# Default thresholds (per v0.1 § 1.3 + v0.2 A6 / A8)
# =============================================================================

DEFAULT_FLAG_DENSITY_FACTOR: Final[float] = 0.75
"""Per v0.1 Inv E13 / v0.2 A6 Inv E13'.

Cap on total emitted flags: len(structural_flags) + len(preference_flags)
≤ len(nodes) × DEFAULT_FLAG_DENSITY_FACTOR. When more flags would be
emitted, a single TRUNCATION_META meta-flag replaces the last slot of
the over-cap tuple (per A6).

Cache-relevant: yes (changes which flags surface).
"""

DEFAULT_BETWEENNESS_THRESHOLD: Final[float] = 0.7
"""Per v0.1 § 1.3 BOTTLENECK_CONCENTRATION.

Normalized betweenness above this threshold for a non-corridor room
emits a BOTTLENECK_CONCENTRATION structural flag (per A4 split).

v1.0 LOCK-mandatory: B-C14-BETWEENNESS-FORMULA-LOCK will pin the exact
betweenness formula. This threshold may co-evolve.

Cache-relevant: yes."""

DEFAULT_EXCESSIVE_DEPTH_THRESHOLD: Final[int] = 5
"""Per v0.1 § 1.3 EXCESSIVE_DEPTH.

step_depth_from_entry[room] above this threshold emits an EXCESSIVE_DEPTH
preference flag (per A4 split). At v0.2 default severity is `info`
(per A10 interpretation-neutrality).

Cache-relevant: yes."""

DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD: Final[float] = 0.5
"""Per v0.2 A8 Inv E18.

If `category_coverage < this threshold`, emit a category_coverage_low
STRUCTURAL flag indicating downstream consumers SHOULD verify upstream
categorization quality.

Cache-relevant: yes (changes which flags surface)."""


# =============================================================================
# Small-graph regime markers (per v0.2 A1 Inv E17)
# =============================================================================

SMALL_GRAPH_REGIME_TINY: Final[frozenset[int]] = frozenset({1, 2})
"""Per v0.2 A1 Inv E17. Node counts where most metrics are N/A."""

SMALL_GRAPH_REGIME_SMALL: Final[frozenset[int]] = frozenset({3})
"""Per v0.2 A1 Inv E17. Node count where RRA is defined but high-noise."""

GRAPH_SIZE_NORMAL_MIN: Final[int] = 4
"""Per v0.2 A1 Inv E11'' / E17. RRA is bounded and reliable for k ≥ 4."""


__all__ = [
    "C14_VERSION",
    "C14_METRIC_VERSION",
    "EXPECTED_C13_VERSION",
    "EXPECTED_ADVISORY_SCHEMA_VERSION",
    "DEFAULT_FLAG_DENSITY_FACTOR",
    "DEFAULT_BETWEENNESS_THRESHOLD",
    "DEFAULT_EXCESSIVE_DEPTH_THRESHOLD",
    "DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD",
    "SMALL_GRAPH_REGIME_TINY",
    "SMALL_GRAPH_REGIME_SMALL",
    "GRAPH_SIZE_NORMAL_MIN",
]
