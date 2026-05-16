"""
BuildemUp — Component 13 — configuration
=========================================

Per C13 SPEC v1.0 LOCKED. DoorPlacementConfig captures all C13-tunable
parameters. Default values reflect:
- v0.2 A2 (corner_offset_m = 0.15)
- v0.2 A4 + v0.3 B3 + v0.4 C4 (max_conflict_resolution_iterations = 5;
  secondary_door_conflict_budget = 3)
- v0.4 C1 (advisory severity calibration + density bound n_rooms × 1.5)
- v0.4 C8 (ADVISORY_SCHEMA_VERSION schema versioning)

Cache-relevant vs cache-irrelevant partitioning (per v0.4 C10):
- Geometry-cache-relevant fields participate in geometry_cache_key
  derivation (door positions, hinges, swings, widths, conflict budgets).
- Advisory-cache-relevant fields participate in advisory_cache_key
  derivation only (severity calibration, density bounds).
- Cache-IRrelevant fields are operational/diagnostic (timeouts,
  telemetry verbosity) and do NOT change output identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import C13ConfigurationError
from .versioning import (
    DEFAULT_CORNER_OFFSET_M,
    DEFAULT_GRID_SNAP_M,
    MAX_DOORS_PER_ROOM_V1,
)


@dataclass(frozen=True)
class DoorPlacementConfig:
    """C13 v1 door-placement configuration.

    All fields documented with cache domain partitioning per v0.4 C10.

    v1 ships STRICT-mode default; WARN mode supported per v0.2 pushback
    item 16 (batch isolation is useful — DOES NOT collapse into STRICT-
    only at v1).
    """
    # ── Mode (geometry-cache-relevant) ──────────────────────────────
    strict_mode: bool = True
    """If True: PerCandidatePlacementError raises immediately, halting
    the batch. If False (WARN mode): per-candidate failures are recorded
    in DoorPlacementBatchResult.failed (typestate FailedDoorPlacement)
    and the batch continues.

    cache_domain: geometry. WARN mode produces different outputs
    (failures vs raise) and must invalidate geometry cache."""

    # ── Phase A defaults (geometry-cache-relevant) ──────────────────
    default_clear_width_m: float = 0.0
    """Per v0.1 § 3.1. The default door clear width when the upstream
    edge's min_required_clear_width_m is exceeded by configuration.
    A value of 0.0 means "use the edge's NBC minimum" (the v1 default
    behavior). A non-zero value RAISES the floor: clear_width_m =
    max(edge.min_required_clear_width_m, default_clear_width_m).

    Inv D10 sanity: must be <= 1.5m.

    cache_domain: geometry."""

    # ── Phase C defaults (geometry-cache-relevant) ──────────────────
    corner_offset_m: float = DEFAULT_CORNER_OFFSET_M
    """Per v0.2 A2. Door position default offset from edge corner
    (150mm = Neufert ergonomic minimum). Replaces v0.1's 0.0 default
    which produced high swing-conflict frequency at corners.

    Must be >= 0.0. Snapped to grid per v0.2 A7.

    cache_domain: geometry."""

    grid_snap_m: float = DEFAULT_GRID_SNAP_M
    """Per v0.2 A7. Grid-snap resolution for door positions. Inherited
    from C12 (50mm). Prevents FP drift from breaking Inv D7 byte-equal
    replay.

    Must be > 0.0.

    cache_domain: geometry."""

    # ── Phase D budget (geometry-cache-relevant) ────────────────────
    max_conflict_resolution_iterations: int = 5
    """Per v0.2 A4 + v0.3 B3 + v0.3 B9. Bounded CSP-lite iteration cap.
    Phase D terminates within this budget; visited-state hashing
    prevents infinite loops (Inv D12').

    cache_domain: geometry."""

    secondary_door_conflict_budget: int = 3
    """Per v0.4 C4. Separate (lower) iteration cap for secondary doors.
    Secondary doors get 3 iterations vs 5 for primary, reflecting
    their lower architectural importance.

    cache_domain: geometry."""

    # ── Phase A iteration order (geometry-cache-relevant) ──────────
    # Per v0.3 B6 (3-tier structural priority): entry > corridor-adjacent
    # > lex-ASC. NOT configurable at v1 (semantic priority table for
    # residential typology was reverted in B6; B-C13-CONFIGURABLE-PRIORITY
    # filed for v1.x). The fact that this is HARDCODED is intentional
    # per the C13/C14 boundary in v0.3 § 0.5 — typology-specific
    # ranking is C14's job, not C13.

    # ── Advisory cache domain (advisory-cache-relevant) ────────────
    advisory_density_factor: float = 1.5
    """Per v0.4 C1 Inv D16. AdvisoryFlag density bound is computed as
    n_rooms × advisory_density_factor. v1 default: 1.5.

    Per v0.4 C1: this factor is hand-picked at v1 (no empirical
    grounding yet). Future calibration is filed as
    B-C13-CATEGORY-SPECIFIC-DENSITY-CAPS (per-category caps replacing
    the global factor) — v1.x.

    Per v0.4 Q11 standing question: configurable vs fixed. v1 ships
    CONFIGURABLE but the field is in the ADVISORY cache domain so
    changes ONLY invalidate advisory_cache_key, preserving
    geometry_cache_key.

    cache_domain: advisory (per v0.4 C10 split)."""

    # ── NBC-borderline threshold (advisory-cache-relevant) ─────────
    nbc_borderline_fraction: float = 0.05
    """Per v0.4 C1 NBC_BORDERLINE category definition. Width within
    this fraction of NBC minimum triggers an NBC_BORDERLINE advisory.

    v1 default: 5% (width <= 1.05 × edge.min_required_clear_width_m).

    cache_domain: advisory."""

    # ── Performance budget (cache_irrelevant — operational) ────────
    per_candidate_wallclock_seconds: float = 10.0
    """Per C12 v0.3-A5 precedent. Single-candidate wallclock budget.
    Phase A-F pipeline is O(n²) worst case for n ≤ 15 rooms; 10s is
    comfortable headroom.

    cache_irrelevant: a timed-out candidate produces a failure record,
    not different geometry — timeouts are operational."""

    # ── Telemetry sink (cache_irrelevant — observability) ──────────
    telemetry_sink: object | None = None
    """Per v0.4 C5 + § 9. Telemetry sink instance; None resolves to
    a null sink at the orchestrator entry. PhaseDConvergenceEvent
    emitted per candidate at Phase D (mandatory at v1 per C5).

    Type stored as object to avoid circular import; the orchestrator
    instantiates / accepts a real TelemetrySink type.

    cache_irrelevant: telemetry is observability, not output-defining."""

    # ── Bathroom outswing area threshold (geometry-cache-relevant) ─
    bathroom_outswing_area_threshold_m2: float = 4.0
    """Per v0.2 A6. Bathrooms with area < 4 m² default to outswing
    (small-bathroom safety + fixture-clearance convention). Bathrooms
    >= 4 m² default to inswing (privacy convention).

    Hand-picked at v1 (no clear NBC cutoff). Documented as v1-
    conservative-best-effort per Rule 11 self-analysis in v0.2.

    cache_domain: geometry."""

    # ── Replay seed (cache_relevant via env fingerprint) ───────────
    master_seed: int = 42
    """Per C12 v0.2-A4 precedent. PRNG used only for tie-break on
    structurally-equivalent door selections. C13 uses canonical
    tie-break ordering (per v0.3 B3 total-order) so the PRNG is
    effectively unused at v1, but reserved for v1.x scenarios.

    cache_relevant via env fingerprint (captured into cache key
    derivation, not directly into config payload)."""

    def __post_init__(self) -> None:
        # Validate geometry domain.
        if self.default_clear_width_m < 0.0:
            raise C13ConfigurationError(
                f"default_clear_width_m must be >= 0.0; "
                f"got {self.default_clear_width_m}."
            )
        if self.default_clear_width_m > 1.5:
            raise C13ConfigurationError(
                f"default_clear_width_m violates Inv D10 sanity bound "
                f"(<= 1.5m at v1); got {self.default_clear_width_m}."
            )
        if self.corner_offset_m < 0.0:
            raise C13ConfigurationError(
                f"corner_offset_m must be >= 0.0; "
                f"got {self.corner_offset_m}."
            )
        if self.grid_snap_m <= 0.0:
            raise C13ConfigurationError(
                f"grid_snap_m must be positive; got {self.grid_snap_m}."
            )
        if self.max_conflict_resolution_iterations < 1:
            raise C13ConfigurationError(
                f"max_conflict_resolution_iterations must be >= 1; "
                f"got {self.max_conflict_resolution_iterations}."
            )
        if self.secondary_door_conflict_budget < 1:
            raise C13ConfigurationError(
                f"secondary_door_conflict_budget must be >= 1; "
                f"got {self.secondary_door_conflict_budget}."
            )
        if self.secondary_door_conflict_budget > self.max_conflict_resolution_iterations:
            raise C13ConfigurationError(
                f"secondary_door_conflict_budget "
                f"({self.secondary_door_conflict_budget}) must be <= "
                f"max_conflict_resolution_iterations "
                f"({self.max_conflict_resolution_iterations}); secondary "
                f"doors are lower priority than primary per v0.4 C4."
            )
        if self.bathroom_outswing_area_threshold_m2 <= 0.0:
            raise C13ConfigurationError(
                f"bathroom_outswing_area_threshold_m2 must be positive; "
                f"got {self.bathroom_outswing_area_threshold_m2}."
            )

        # Validate advisory domain.
        if self.advisory_density_factor <= 0.0:
            raise C13ConfigurationError(
                f"advisory_density_factor must be positive; "
                f"got {self.advisory_density_factor}."
            )
        if self.nbc_borderline_fraction < 0.0:
            raise C13ConfigurationError(
                f"nbc_borderline_fraction must be >= 0.0; "
                f"got {self.nbc_borderline_fraction}."
            )

        # Validate operational.
        if self.per_candidate_wallclock_seconds <= 0.0:
            raise C13ConfigurationError(
                f"per_candidate_wallclock_seconds must be positive; "
                f"got {self.per_candidate_wallclock_seconds}."
            )


__all__ = [
    "DoorPlacementConfig",
]
