"""
BuildemUp — Component 14 — configuration
=========================================

Per C14 SPEC v0.2 LOCKED (v0.1 § 6 perf budget + v0.1 § 1.3 thresholds
+ v0.2 A6/A8 cap + coverage threshold + v0.2 A10 default-severity-info).

CirculationConfig carries the tunable behavioral knobs:
- Performance budget (per_candidate_wallclock_seconds)
- Flag-density cap factor (Inv E13')
- Threshold values for flag emission (betweenness, depth)
- Category-coverage warning threshold (Inv E18 from A8)
- Strict-vs-WARN dispatch mode

Frozen so config-hash contributes deterministically to cache keys
(Inv E16 / E18 / cache compose).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import C14ConfigurationError
from .versioning import (
    DEFAULT_BETWEENNESS_THRESHOLD,
    DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD,
    DEFAULT_EXCESSIVE_DEPTH_THRESHOLD,
    DEFAULT_FLAG_DENSITY_FACTOR,
)


@dataclass(frozen=True)
class CirculationConfig:
    """Per v0.1 § 6 + § 1.3 + v0.2 A6 + A8 + A10.

    Tunable behavioral knobs for C14. Frozen so the config's identity
    contributes deterministically to the metric cache key.

    Defaults preserve the v0.2 LOCKED SKETCH semantics.

    Cache-relevant fields:
    - flag_density_factor (controls truncation per A6 Inv E13')
    - betweenness_threshold (controls BOTTLENECK_CONCENTRATION emission)
    - excessive_depth_threshold (controls EXCESSIVE_DEPTH emission)
    - category_coverage_low_threshold (controls category_coverage_low emission per A8)

    NON-cache-relevant fields:
    - per_candidate_wallclock_seconds (budget only — does not change output)
    - strict_mode (mode dispatch — same output across strict/warn for
      successful candidates; only the orchestrator's behavior on failure differs)
    """
    per_candidate_wallclock_seconds: float = 0.5
    """Per v0.1 § 6. Per-candidate wallclock budget.

    Budget only — exceeding it raises a per-candidate timeout, which
    under STRICT halts the batch, under WARN packages a
    FailedCirculationAnalysis. Does NOT change the output of successful
    candidates.

    Cache-relevant: NO."""

    flag_density_factor: float = DEFAULT_FLAG_DENSITY_FACTOR
    """Per v0.2 A6 Inv E13'.

    Cap on total flags: len(structural_flags) + len(preference_flags)
    ≤ len(nodes) × flag_density_factor. When the cap is exceeded, a
    single TRUNCATION_META meta-flag replaces the last slot of the
    over-cap tuple.

    Cache-relevant: YES."""

    betweenness_threshold: float = DEFAULT_BETWEENNESS_THRESHOLD
    """Per v0.1 § 1.3 BOTTLENECK_CONCENTRATION.

    Normalized betweenness above this threshold for a non-corridor
    room emits a BOTTLENECK_CONCENTRATION structural flag.

    Cache-relevant: YES."""

    excessive_depth_threshold: int = DEFAULT_EXCESSIVE_DEPTH_THRESHOLD
    """Per v0.1 § 1.3 EXCESSIVE_DEPTH.

    step_depth above this threshold emits an EXCESSIVE_DEPTH preference
    flag. Default severity is `info` per v0.2 A10.

    Cache-relevant: YES."""

    category_coverage_low_threshold: float = DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD
    """Per v0.2 A8 Inv E18.

    If `category_coverage < this threshold`, emit a category_coverage_low
    STRUCTURAL flag indicating downstream consumers SHOULD verify
    upstream categorization quality.

    Cache-relevant: YES."""

    strict_mode: bool = True
    """Per v0.1 § 5.

    If True, per-candidate errors halt the batch.
    If False (WARN), per-candidate errors are caught and recorded into
    CirculationAnalysisBatchResult.failed.

    LocalCirculationError always halts regardless of mode.

    Cache-relevant: NO (failing candidates contribute differently across
    modes, but successful candidates' outputs are byte-equal across
    modes — Inv E7 demands this)."""

    cache_mode: Literal["strict", "lenient"] = "strict"
    """Per v0.1 § 8 + analogous to C13's cache modes.

    "strict": ANY upstream cache-relevant change invalidates C14's cache.
    "lenient": only direct C14 changes invalidate.

    At v0.2, "strict" is the only validated mode. "lenient" is reserved
    for v1.x. Cache-relevant: NO at v0.2 (only "strict" is real)."""

    def __post_init__(self) -> None:
        # Defensive validation. Raises C14ConfigurationError at construction
        # time so misconfigurations halt at startup, not at first analyze().

        if self.per_candidate_wallclock_seconds <= 0:
            raise C14ConfigurationError(
                f"per_candidate_wallclock_seconds must be > 0; "
                f"got {self.per_candidate_wallclock_seconds!r}"
            )

        if not (0.0 < self.flag_density_factor <= 10.0):
            # Upper bound 10.0 is generous — defends against typos like
            # 75 instead of 0.75. Per v0.1 Inv E13 default is 0.75; values
            # > 1 mean "more flags than nodes" which is permitted but
            # unusual.
            raise C14ConfigurationError(
                f"flag_density_factor must be in (0, 10]; "
                f"got {self.flag_density_factor!r}"
            )

        if not (0.0 <= self.betweenness_threshold <= 1.0):
            raise C14ConfigurationError(
                f"betweenness_threshold must be in [0, 1]; "
                f"got {self.betweenness_threshold!r}"
            )

        if self.excessive_depth_threshold < 0:
            raise C14ConfigurationError(
                f"excessive_depth_threshold must be >= 0; "
                f"got {self.excessive_depth_threshold!r}"
            )

        if not (0.0 <= self.category_coverage_low_threshold <= 1.0):
            raise C14ConfigurationError(
                f"category_coverage_low_threshold must be in [0, 1]; "
                f"got {self.category_coverage_low_threshold!r}"
            )

        if self.cache_mode not in ("strict", "lenient"):
            raise C14ConfigurationError(
                f"cache_mode must be 'strict' or 'lenient'; "
                f"got {self.cache_mode!r}"
            )


__all__ = ["CirculationConfig"]
