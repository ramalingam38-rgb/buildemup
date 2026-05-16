"""
BuildemUp — Component 15 — configuration
=========================================

Per C15 SPEC v0.2 LOCKED (v0.1 § 6 perf budget + v0.1 § 5 strict/WARN
dispatch + v0.1 § 8 cache mode).

ProblemFinderConfig carries the tunable behavioral knobs:
- Performance budget (per_candidate_wallclock_seconds,
  per_batch_wallclock_seconds)
- Strict-vs-WARN dispatch mode
- Cache mode

Frozen so config-hash contributes deterministically to cache keys
(Inv P14 cache composability).

Per Inv P0 (v0.2 A1): no field aggregates check outputs or stores
layout-quality scores. Configuration is pure operational tuning.

NOTE on v0.1 § 1.3 thresholds: unlike C14 which has many threshold
fields (betweenness, depth, density), C15's thresholds at v0.2 LOCK
SKETCH live INSIDE the check registry (per § 5.2 + B-C15-CHECK-
MEASUREMENT-FORMULAS-LOCK LOCK-mandatory). Per-check thresholds are
NOT in this config — they're encapsulated in the check definitions
themselves. This avoids the rules-on-rules anti-pattern (Pattern D)
of having config fields that can override per-check semantics
independently of the registry version.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import C15ConfigurationError
from .versioning import (
    DEFAULT_PER_BATCH_WALLCLOCK_SECS,
    DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS,
)


@dataclass(frozen=True)
class ProblemFinderConfig:
    """Per v0.1 § 5 + § 6 + § 8.

    Tunable behavioral knobs for C15. Frozen so the config's identity
    contributes deterministically to cache keys.

    Defaults preserve the v0.2 LOCKED SKETCH semantics.

    Cache-relevant fields: NONE at v0.2.
        At v0.2 LOCK SKETCH, every field here is operational (budget,
        mode, cache-strategy) and does NOT change the output of
        successful candidates (Inv P2 byte-equal replay). Per-check
        thresholds live in the check registry, not here, precisely so
        the config can be tuned at runtime without invalidating caches.

    NON-cache-relevant fields:
    - per_candidate_wallclock_seconds (budget only)
    - per_batch_wallclock_seconds (budget only)
    - strict_mode (mode dispatch — same output across modes for
      successful candidates; only the orchestrator's behavior on failure
      differs)
    - cache_mode (cache invalidation strategy; output-equivalent)
    """
    per_candidate_wallclock_seconds: float = DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS
    """Per v0.1 § 6. Per-candidate wallclock budget.

    Budget only — exceeding it raises a per-candidate timeout, which
    under STRICT halts the batch, under WARN packages a
    FailedProblemAnalysis. Does NOT change the output of successful
    candidates.

    Default 1.5s allows ~40 checks at O(k) each where k = room count.

    Cache-relevant: NO."""

    per_batch_wallclock_seconds: float = DEFAULT_PER_BATCH_WALLCLOCK_SECS
    """Per v0.1 § 6. Per-batch (50 candidates default) wallclock budget.

    At v0.2 LOCK SKETCH: SOFT signal only. The orchestrator reports
    total elapsed time but does NOT abort the batch on overflow.
    v1.0 may upgrade to hard-cap with TRUNCATION_META semantics
    analogous to C14 A6.

    Cache-relevant: NO."""

    strict_mode: bool = True
    """Per v0.1 § 5.

    If True (default), per-candidate errors halt the batch.
    If False (WARN), per-candidate errors are caught and recorded into
    ProblemAnalysisBatchResult.failed.

    LocalProblemError always halts regardless of mode.

    Cache-relevant: NO (failing candidates contribute differently across
    modes, but successful candidates' outputs are byte-equal across
    modes — Inv P2 demands this)."""

    cache_mode: Literal["strict", "lenient"] = "strict"
    """Per v0.1 § 8 + analogous to C13/C14 cache modes.

    "strict": ANY upstream cache-relevant change invalidates C15's
        cache (full chain: C12 → C13 → C14 → C15).
    "lenient": only direct C15 changes (version or registry bump)
        invalidate.

    At v0.2, "strict" is the only validated mode. "lenient" is reserved
    for v1.x when a real use case for divergent invalidation emerges
    (see also B-C14-CACHE-SPLIT-IF-DIVERGENT).

    Cache-relevant: NO at v0.2 (only "strict" is real)."""

    def __post_init__(self) -> None:
        # Defensive validation. Raises C15ConfigurationError at
        # construction time so misconfigurations halt at startup,
        # not at first analyze().

        if not isinstance(self.per_candidate_wallclock_seconds, (int, float)):
            raise C15ConfigurationError(
                f"per_candidate_wallclock_seconds must be a number; "
                f"got {type(self.per_candidate_wallclock_seconds)}"
            )
        if isinstance(self.per_candidate_wallclock_seconds, bool):
            # bool is subclass of int — reject explicitly.
            raise C15ConfigurationError(
                "per_candidate_wallclock_seconds must be a number "
                "(not bool)"
            )
        if self.per_candidate_wallclock_seconds <= 0:
            raise C15ConfigurationError(
                f"per_candidate_wallclock_seconds must be > 0; "
                f"got {self.per_candidate_wallclock_seconds!r}"
            )

        if not isinstance(self.per_batch_wallclock_seconds, (int, float)):
            raise C15ConfigurationError(
                f"per_batch_wallclock_seconds must be a number; "
                f"got {type(self.per_batch_wallclock_seconds)}"
            )
        if isinstance(self.per_batch_wallclock_seconds, bool):
            raise C15ConfigurationError(
                "per_batch_wallclock_seconds must be a number (not bool)"
            )
        if self.per_batch_wallclock_seconds <= 0:
            raise C15ConfigurationError(
                f"per_batch_wallclock_seconds must be > 0; "
                f"got {self.per_batch_wallclock_seconds!r}"
            )

        if not isinstance(self.strict_mode, bool):
            raise C15ConfigurationError(
                f"strict_mode must be bool; got {type(self.strict_mode)}"
            )

        if self.cache_mode not in ("strict", "lenient"):
            raise C15ConfigurationError(
                f"cache_mode must be 'strict' or 'lenient'; "
                f"got {self.cache_mode!r}"
            )


__all__ = ["ProblemFinderConfig"]
