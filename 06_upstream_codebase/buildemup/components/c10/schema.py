"""
BuildemUp† — Component 10 (Wet-Zone Stack Planner) — Schema module.

Per C10 SPEC v1.0 LOCKED § 2 (Contract + Schema), § 3 (Behaviour Phase 0-5),
§ 4 (Invariants 1-21).

All dataclasses are frozen (immutable) for replay determinism and to prevent
silent mutation across phase boundaries. Q46 verdict applied:
WetZonePlanProvenance.__post_init__ runs validate_remediation_graph()
defensively against externally-constructed instances.

†= placeholder name marker.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Final, Literal


# =============================================================================
# Module constants
# =============================================================================


# Q43: per-fixture likely-bound factors. Replaces uniform 0.5 from v0.8.
# Lives as Final dict per spec § 3 Phase 4. Q45 deferred KB migration to
# B-246 post-v1.
LIKELY_BOUND_FACTORS_BY_FIXTURE: Final[dict[str, float]] = {
    "water_closet": 0.8,
    "lavatory":     0.5,
    "shower":       0.6,
    "bathtub":      0.6,
    "kitchen_sink": 0.4,
    "utility_sink": 0.4,
    "floor_drain":  0.7,
}

# Float comparison epsilon for internal computations. Per spec § 3
# determinism discipline (Phase 1b ranking, Phase 3 backtracking compares).
EPSILON: Final[float] = 1e-9

# FP precision used for serialisation (rule_trace, replay snapshots).
SERIALIZATION_PRECISION: Final[int] = 6


# =============================================================================
# Enums
# =============================================================================


class EnforcementMode(str, Enum):
    """Mirrors C9.EnforcementMode for cross-component consistency."""
    WARN   = "warn"
    STRICT = "strict"


class PlacementRiskLevel(str, Enum):
    """Re-uses C9 PlacementRiskLevel semantic to keep risk-tier semantics
    aligned across components."""
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class TruncationReason(str, Enum):
    MAX_STATES            = "max_states"
    MAX_ATTEMPTS          = "max_attempts"
    COMPLETED             = "completed"
    INFEASIBLE_TERMINATED = "infeasible_terminated"


# =============================================================================
# Atomic primitive dataclasses
# =============================================================================


@dataclass(frozen=True)
class TrapArmEstimate:
    """Dual-bound trap-arm distance (Q34 + Q43 per-fixture factors)."""
    upper_bound_m: float
    likely_bound_m: float

    def __post_init__(self) -> None:
        if not (isinstance(self.upper_bound_m, (int, float)) and not isinstance(self.upper_bound_m, bool)):
            raise TypeError("TrapArmEstimate.upper_bound_m must be float")
        if not (isinstance(self.likely_bound_m, (int, float)) and not isinstance(self.likely_bound_m, bool)):
            raise TypeError("TrapArmEstimate.likely_bound_m must be float")
        if self.upper_bound_m < 0:
            raise ValueError(
                f"TrapArmEstimate.upper_bound_m must be >= 0; "
                f"got {self.upper_bound_m}"
            )
        if self.likely_bound_m < 0:
            raise ValueError(
                f"TrapArmEstimate.likely_bound_m must be >= 0; "
                f"got {self.likely_bound_m}"
            )
        # Likely never exceeds upper.
        if self.likely_bound_m - self.upper_bound_m > EPSILON:
            raise ValueError(
                f"TrapArmEstimate.likely_bound_m ({self.likely_bound_m}) "
                f"must be <= upper_bound_m ({self.upper_bound_m})"
            )


@dataclass(frozen=True)
class RemediationHint:
    """Structured hint emitted alongside per-candidate errors. Q33 retry
    orchestration fields: retry_priority + mutually_exclusive_with."""
    kind: Literal[
        "relax_config", "increase_limit", "alternative_routing", "manual_review"
    ]
    parameter: str
    current_value: Any
    suggested_value: Any
    severity: Literal["low", "medium", "high"]
    human_readable: str
    retry_priority: int
    mutually_exclusive_with: tuple[str, ...] = ()
    expected_success_probability: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in (
            "relax_config", "increase_limit",
            "alternative_routing", "manual_review",
        ):
            raise ValueError(
                f"RemediationHint.kind invalid: {self.kind!r}"
            )
        if self.severity not in ("low", "medium", "high"):
            raise ValueError(
                f"RemediationHint.severity invalid: {self.severity!r}"
            )
        if not isinstance(self.parameter, str) or not self.parameter:
            raise ValueError(
                f"RemediationHint.parameter must be non-empty string"
            )
        if not isinstance(self.retry_priority, int) or isinstance(self.retry_priority, bool):
            raise TypeError("RemediationHint.retry_priority must be int")
        if not isinstance(self.mutually_exclusive_with, tuple):
            raise TypeError(
                "RemediationHint.mutually_exclusive_with must be tuple[str,...]"
            )
        for mx in self.mutually_exclusive_with:
            if not isinstance(mx, str):
                raise TypeError(
                    "RemediationHint.mutually_exclusive_with entries must be str"
                )
        if self.expected_success_probability is not None:
            if not (
                isinstance(self.expected_success_probability, (int, float))
                and not isinstance(self.expected_success_probability, bool)
            ):
                raise TypeError(
                    "RemediationHint.expected_success_probability must be "
                    "None or float"
                )
            if not (0.0 <= float(self.expected_success_probability) <= 1.0):
                raise ValueError(
                    "RemediationHint.expected_success_probability must be "
                    "in [0.0, 1.0]"
                )


@dataclass(frozen=True)
class ForcedCultureOverride:
    room_id: str
    wall_id: str
    category: str
    rejected_alternatives: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class WallScoreVector:
    """Per-wall, per-category score breakdown. Includes
    scoring_weights_hash for self-contained replay reproducibility."""
    wall_id: str
    category: str
    engineering_score: float
    cultural_score: float
    adjacency_score: float
    scoring_profile_id: str
    scoring_weights_hash: str          # SHA256 hex


@dataclass(frozen=True)
class RiserAnchor:
    wall_id: str
    anchor_position_m: float
    riser_anchor_xy: tuple[float, float]
    column_id: str | None
    snap_distance_m: float | None


@dataclass(frozen=True)
class RiserGroup:
    """v1 invariant: exactly one anchor per RiserGroup. Tuple chosen
    for forward-compat with B-225 multi-anchor."""
    group_id: str
    anchors: tuple[RiserAnchor, ...]
    wet_room_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.anchors) != 1:
            raise ValueError(
                f"RiserGroup {self.group_id}: v1 requires exactly 1 anchor; "
                f"got {len(self.anchors)}. Multi-anchor support pending B-225."
            )
        if len(self.wet_room_ids) == 0:
            raise ValueError(
                f"RiserGroup {self.group_id}: wet_room_ids must be non-empty "
                f"(Inv 13)"
            )


@dataclass(frozen=True)
class WetZoneRiskBreakdown:
    optimization_risk: PlacementRiskLevel
    optimization_score: float
    engineering_risk: PlacementRiskLevel
    engineering_score: float
    cultural_risk: PlacementRiskLevel
    cultural_score: float


@dataclass(frozen=True)
class WetZonePerformanceBudgets:
    max_wall_score_vectors: int = 100
    max_provenance_rule_trace_entries: int = 500
    max_remediation_hints: int = 20


# =============================================================================
# Weights / config dataclasses
# =============================================================================


@dataclass(frozen=True)
class WetZoneCapacityWeights:
    """Q44 extraction from WetZoneScoringWeights: capacity is a feasibility
    concern (Phase 3 Inv 17), not a scoring concern. Default values map to
    rough DFU correspondence per Q38."""
    fixture_capacity_weights: dict[str, float] = field(default_factory=lambda: {
        "water_closet": 2.0, "shower": 1.5, "bathtub": 1.5,
        "lavatory": 1.0, "kitchen_sink": 1.0, "utility_sink": 1.0,
        "floor_drain": 0.5,
    })
    minimum_riser_spacing_m: float = 3.0
    wall_safety_margin_m: float = 0.0    # 0 means "use default" — see usage
    """When 0.0, callers compute safety margin = 2 * minimum_riser_spacing_m
    (per Phase 2.5). Override > 0 to set explicit margin."""


@dataclass(frozen=True)
class WetZoneScoringWeights:
    weight_engineering: float = 1.0
    weight_cultural: float = 1.0
    weight_adjacency: float = 1.0
    column_alignment_bonus: float = 0.2
    wall_length_sufficiency_bonus: float = 0.1
    wall_reuse_penalty: float = -0.5
    bathroom_axis_preferred: float = 1.0
    bathroom_axis_neutral: float = 0.5
    bathroom_axis_discouraged: float = 0.0
    pooja_axis_preferred: float = 1.0
    pooja_axis_neutral: float = 0.5
    pooja_axis_discouraged: float = 0.0


def compute_scoring_weights_hash(w: WetZoneScoringWeights) -> str:
    """SHA256 hex of the canonical-JSON serialisation of the weights.

    Used to populate WallScoreVector.scoring_weights_hash for self-contained
    replay reproducibility.
    """
    payload = {f.name: getattr(w, f.name) for f in fields(w)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class WetZonePlanConfig:
    enforcement_mode: EnforcementMode = EnforcementMode.WARN
    pooja_adjacency_mode: Literal["strict", "soft"] = "strict"
    max_risers: int | None = None
    adjacency_threshold_m: float = 0.0
    require_master_bath_adjacency: bool = True
    # Production default per § 5: True. Test fixtures override to False
    # to tolerate KB-DRAFT during pre-launch.
    require_verified_plumbing: bool = True
    scoring_weights: WetZoneScoringWeights = field(default_factory=WetZoneScoringWeights)
    capacity_weights: WetZoneCapacityWeights = field(default_factory=WetZoneCapacityWeights)
    scoring_profile: Literal["vastu_strict", "vastu_soft", "neutral"] = "neutral"
    max_backtrack_states: int = 100
    max_assignment_attempts: int = 50
    trap_arm_tolerance_m: float = 0.15
    enable_relaxation_pass: bool = True
    """C10 AMENDMENT v1.1 (S59 ext) — when the strict Phase-3 greedy
    fails on small plots (acceptable_walls sets too sparse to satisfy
    every cluster simultaneously), retry over the FULL grid wall set,
    using capacity as the only hard gate and emitting a
    ``ForcedCultureOverride`` per relaxed assignment. Preserves WARN-
    mode UX: the user gets a layout with a flag rather than a
    cascade-error. Set False to keep strict behaviour (e.g. for
    deterministic test fixtures that intentionally exercise the
    failure path).
    """
    performance_budgets: WetZonePerformanceBudgets = field(
        default_factory=WetZonePerformanceBudgets
    )


# =============================================================================
# Plan + Provenance + envelope
# =============================================================================


@dataclass(frozen=True)
class WetZonePlan:
    wet_wall_assignment: dict[str, str]
    riser_groups: tuple[RiserGroup, ...]
    kitchen_riser_group_id: str | None
    fixture_types_per_room: dict[str, tuple[str, ...]]
    trap_arm_distances: dict[tuple[str, str], TrapArmEstimate]
    total_wet_run_length_m: float
    symbolic_bend_estimate: int
    bend_estimation_mode: Literal["symbolic_v1"]
    riser_count: int
    non_wet_room_buffer_zones: tuple[str, ...]
    acceptable_wall_sets: dict[str, tuple[str, ...]]

    @property
    def wall_segments_used(self) -> tuple[str, ...]:
        """Inv 14: every RiserGroup.anchor.wall_id appears in this set."""
        return tuple(sorted({rg.anchors[0].wall_id for rg in self.riser_groups}))

    def __post_init__(self) -> None:
        if self.bend_estimation_mode != "symbolic_v1":
            raise ValueError(
                f"WetZonePlan.bend_estimation_mode (Inv 20) must be "
                f"'symbolic_v1'; got {self.bend_estimation_mode!r}"
            )
        if self.symbolic_bend_estimate < 0:
            raise ValueError(
                f"WetZonePlan.symbolic_bend_estimate must be >= 0; "
                f"got {self.symbolic_bend_estimate}"
            )
        if self.total_wet_run_length_m < 0:
            raise ValueError(
                f"WetZonePlan.total_wet_run_length_m must be >= 0 "
                f"(Inv 10); got {self.total_wet_run_length_m}"
            )
        if self.riser_count < 0:
            raise ValueError(
                f"WetZonePlan.riser_count must be >= 0; got {self.riser_count}"
            )


@dataclass(frozen=True)
class WetZonePlanProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    floor_label: str
    plumbing_kb_version: str
    fixture_profiles_kb_version: str
    enforcement_mode: str
    pooja_adjacency_mode: str
    scoring_profile: str
    scoring_weights_snapshot: WetZoneScoringWeights
    cluster_decisions: tuple[str, ...]
    wall_scoring_breakdown: tuple[WallScoreVector, ...]
    forced_culturally_discouraged: tuple[ForcedCultureOverride, ...]
    unverified_plumbing_rows_used: tuple[str, ...]
    search_truncated: bool
    states_explored: int
    truncation_reason: TruncationReason
    _observational_runtime_ms: int                       # NOT in replay hashes
    risk_breakdown: WetZoneRiskBreakdown
    remediation_hints: tuple[RemediationHint, ...]
    performance_budget_warnings: tuple[str, ...]
    rule_trace: tuple[str, ...]

    def __post_init__(self) -> None:
        # Q46: defensive validation. If the caller constructs a provenance
        # with a cyclic mutex graph, raise immediately.
        # Local import to avoid circular import.
        from buildemup.components.c10.provenance import validate_remediation_graph
        validate_remediation_graph(self.remediation_hints)


@dataclass(frozen=True)
class WetZonePlannedCandidate:
    """C10's per-candidate output. Mirrors C9 RoomSizedCandidate pattern:
    embed the input candidate so callers can correlate output back to input
    position in the partial-batch tuple."""
    room_sized_candidate: Any                # forward-ref RoomSizedCandidate
    wet_zone_plan: WetZonePlan
    provenance: WetZonePlanProvenance


__all__ = [
    # Constants
    "LIKELY_BOUND_FACTORS_BY_FIXTURE",
    "EPSILON",
    "SERIALIZATION_PRECISION",
    # Enums
    "EnforcementMode",
    "PlacementRiskLevel",
    "TruncationReason",
    # Primitive dataclasses
    "TrapArmEstimate",
    "RemediationHint",
    "ForcedCultureOverride",
    "WallScoreVector",
    "RiserAnchor",
    "RiserGroup",
    "WetZoneRiskBreakdown",
    "WetZonePerformanceBudgets",
    # Weights / config
    "WetZoneCapacityWeights",
    "WetZoneScoringWeights",
    "WetZonePlanConfig",
    "compute_scoring_weights_hash",
    # Plan + provenance + envelope
    "WetZonePlan",
    "WetZonePlanProvenance",
    "WetZonePlannedCandidate",
]
