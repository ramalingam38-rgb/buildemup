"""
C17 — Quote Comparison Engine — runtime config
================================================

All R5/R17/R18 thresholds and ceilings live in versioning.py as
module-level Final constants (spec § 6 / § 27 — internal heuristics,
NOT user-tunable per § 27.1). This module holds only RUNTIME knobs
that may vary per orchestrator invocation:

    - strict_mode (STRICT vs WARN per spec § 4)
    - debug introspection toggles

Per spec § 27.1: this file does NOT expose threshold values via
public API. They are imported FROM versioning.py and used internally
only. Adversarial contractors must not be able to read thresholds
out of this module's `__all__`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class C17RuntimeConfig:
    """Per-invocation runtime config. Determinism-safe:

      - strict_mode is part of the canonical_replay_signature (R6)
      - Other fields (verbose, dry_run) are NOT — they don't change
        the report shape, only logging/diagnostics. R6 preserved.
    """
    strict_mode: Literal["strict", "warn"] = "strict"
    """STRICT mode raises PerQuoteLineError immediately. WARN mode
    collects failures into FailedComparisonRecord and continues.
    Default: 'strict' (caller must opt into WARN for batch tolerance)."""

    verbose:    bool = False
    """If True, advisory_flags include per-phase progress markers.
    NOT signature-relevant."""

    dry_run:    bool = False
    """If True, phases run but the orchestrator skips final signing.
    Used by tests; NOT signature-relevant."""

    def signature_relevant_tuple(self) -> tuple:
        """Subset of fields included in canonical_replay_signature (R6).

        ONLY strict_mode currently. Other fields are diagnostics."""
        return (self.strict_mode,)
