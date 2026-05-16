"""
BuildemUp — Component 12 — configuration
========================================

Per C12 SPEC v1.0 LOCKED § 2.3.

PlacementConfig captures all C12-tunable parameters. Default values
reflect v0.2-A8 (alignment tolerance 0.02m) + v0.3-A5 (performance
budgets) + v0.3-A1 (slicing_kd_tree only) + v0.3-A3 (STRICT-only repair).

Cache-relevant vs cache-irrelevant partitioning:
- cache_relevant=True fields participate in cache key derivation;
  changing them invalidates cached PlacementBatchResults.
- cache_relevant=False fields are operational/diagnostic only
  (timeouts, telemetry verbosity) and do NOT change output identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .errors import C12ConfigurationError


@dataclass(frozen=True)
class PlacementConfig:
    """C12 v1 placement configuration.

    All fields documented with cache_relevant flag per v0.3-A6.

    v1 ships STRICT-only (no LENIENT_SHRINK per v0.2-A3). The
    single-algorithm choice (slicing_kd_tree) per v0.3-A1 means
    placement_algorithm is a Literal, not an enum.
    """
    # ── Mode (cache_relevant=True) ─────────────────────────────────
    strict_mode: bool = True
    """If True: PerCandidatePlacementError raises immediately.
    If False (WARN mode): per-candidate failures are recorded in
    PlacementBatchResult.failures and the batch continues.

    cache_relevant=True: WARN mode produces different outputs
    (failures vs raise)."""

    # ── Placement algorithm (cache_relevant=True) ──────────────────
    placement_algorithm: Literal["slicing_kd_tree"] = "slicing_kd_tree"
    """Per v0.3-A1: v1 ships ONLY the slicing-tree algorithm.
    CSP-backtrack fallback removed from v1 scope; filed as
    B-C12-CSP-PLACEMENT post-v1.

    cache_relevant=True."""

    # ── Alignment tolerance (cache_relevant=True) ──────────────────
    vertical_alignment_tolerance_m: float = 0.02
    """Per v0.2-A8 (Q-2 resolution): default 0.02 m = 20mm = 2× IS 456
    slab construction tolerance. Replaced v0.1's unrealistic 0.0
    default.

    Configurable per batch for tighter / looser alignment requirements.

    cache_relevant=True."""

    # ── Multi-floor retry budget (cache_relevant=True) ─────────────
    multi_floor_max_realign_iterations: int = 3
    """Per v0.3-A2: flat constant at v1 (no scaling with floor count;
    that's B-C12-ADAPTIVE-RETRY-BUDGET post-v1). Combined with v0.2-A2
    monotonic-δ convergence + divergence abort, worst-case work is
    bounded by 3× SFP + 3× VAV.

    cache_relevant=True."""

    # ── Performance budgets (cache_relevant=False — operational) ───
    per_candidate_wallclock_seconds: float = 10.0
    """Per v0.3-A5: single-floor wallclock budget. Slicing-tree is
    O(n log n) typical for n ≤ 15, so 10s is comfortable headroom.
    PlacementAlgorithmTimeoutError raised on exceed.

    cache_relevant=False: timeouts are operational, not output-defining
    (a timed-out batch produces failures, not different geometry)."""

    multi_floor_wallclock_seconds: float | None = None
    """Per v0.3-A5: when None, derived as
    per_candidate * num_floors + max_realign_iterations * 5.0.
    For typical 3-floor with 3 retries: 30 + 15 = 45 s.

    cache_relevant=False (same rationale as
    per_candidate_wallclock_seconds)."""

    # ── PRNG seed (cache_relevant=True via env fingerprint) ────────
    master_seed: int = 42
    """Per v0.2-A4: PRNG used only for tie-break on equal-score
    placements. Replay-tested per Inv 7.

    cache_relevant=True (captured into env fingerprint, not directly
    into cache key)."""

    # ── Telemetry sink (cache_relevant=False — observability only) ─
    # Type stored as Any to avoid circular import; the orchestrator
    # imports + instantiates the real TelemetrySink type. Default
    # ``None`` resolves to NullTelemetrySink at the orchestrator
    # entry, preserving zero-overhead default.
    telemetry_sink: object | None = None
    """Per B-C12-*-TELEMETRY backlog items: a TelemetrySink instance
    that receives structured events. Default None resolves to
    NullTelemetrySink (drops everything).

    cache_relevant=False: telemetry output never changes placement
    geometry, so it does NOT participate in cache key derivation."""

    def __post_init__(self) -> None:
        if self.vertical_alignment_tolerance_m < 0.0:
            raise C12ConfigurationError(
                f"vertical_alignment_tolerance_m must be >= 0; "
                f"got {self.vertical_alignment_tolerance_m}."
            )
        if self.multi_floor_max_realign_iterations < 0:
            raise C12ConfigurationError(
                f"multi_floor_max_realign_iterations must be >= 0; "
                f"got {self.multi_floor_max_realign_iterations}."
            )
        if self.per_candidate_wallclock_seconds <= 0.0:
            raise C12ConfigurationError(
                f"per_candidate_wallclock_seconds must be > 0; "
                f"got {self.per_candidate_wallclock_seconds}."
            )
        if (
            self.multi_floor_wallclock_seconds is not None
            and self.multi_floor_wallclock_seconds <= 0.0
        ):
            raise C12ConfigurationError(
                f"multi_floor_wallclock_seconds must be > 0 when set; "
                f"got {self.multi_floor_wallclock_seconds}."
            )

    def effective_multi_floor_wallclock_seconds(self, num_floors: int) -> float:
        """Per v0.3-A5 derivation formula."""
        if self.multi_floor_wallclock_seconds is not None:
            return self.multi_floor_wallclock_seconds
        return (
            self.per_candidate_wallclock_seconds * num_floors
            + self.multi_floor_max_realign_iterations * 5.0
        )


__all__ = ["PlacementConfig"]
