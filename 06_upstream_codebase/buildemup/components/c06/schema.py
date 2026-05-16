"""
BuildemUp† — Component 6 (Orientation Priority) schema.

All enums + dataclasses + named constants for C6. Per SPEC v0.6 LOCKED § 3 + § 13.
Pure types + constants only — no logic, no I/O, no KB data.

Cumulative across spec rounds:
  - v0.1: FunctionRole, SignalBreakdown, DirectionPriorityScore,
          OrientationProvenance, OrientationPriority, OrientedCandidate
  - v0.2: tie-break + hysteresis constants + 8-direction Vastu (initially
          via PlotDirection8 — REMOVED v0.6)
  - v0.3: weighted-avg aggregation; CIRCULATION light scoring formalized
  - v0.4: margin-clamped confidence; weights_raw exposure; permutation cap
  - v0.5: signal_dominance + dominant_signal interpretability
  - v0.6: PlotDirection8 dropped (use PlotOrientation throughout); cardinal-
          only v1 facing (intercardinal raises NotImplementedError, B-107);
          CIRCULATION clarified as private helper (NOT a FunctionRole)

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from buildemup.components.c05.schema import TopologyCandidate, ZoneBand
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# Named constants (per SPEC v0.6 § 13)
# ─────────────────────────────────────────────────────────────────────────────

SIGNAL_DOMINANCE_THRESHOLD: float = 0.45
"""Threshold above which a single signal is declared `dominant_signal`.

Per § 14.18 (v0.5). Equal-weight baseline = 0.33 (with 3 signals); a margin
above that requires meaningful imbalance before declaring dominance.
"""

SWAP_HYSTERESIS_THRESHOLD: float = 0.10
"""Minimum advantage the global optimum must hold over the C5 seed
permutation before C6 swaps. Per § 4.4 step 4 + § 14.13.
"""

MAX_PERMUTATION_COUNT: int = 256
"""Defense-in-depth assertion cap on post-prune permutation count.

Per § 4.4 step 2 + § 14.17. ≤ 24 for non-COURTYARD topologies (4! = 24);
≤ 256 for COURTYARD (4^4 = 256, since COURTYARD allows direction reuse).
"""

MIN_DENOM: float = 0.1
"""Floor on the confidence denominator. Per § 4.5 + § 14.15.

Margin-clamped confidence: `(top - second) / max(top, MIN_DENOM)` clamped
to [0, 1]. MIN_DENOM prevents pathological inflation when top_score is
near zero.
"""


CARDINAL_FACINGS: frozenset[PlotOrientation] = frozenset({
    PlotOrientation.NORTH,
    PlotOrientation.EAST,
    PlotOrientation.SOUTH,
    PlotOrientation.WEST,
})
"""The four cardinal members of `PlotOrientation`. C6 v1 supports only
cardinal `plot.facing` values; intercardinal raises NotImplementedError
(B-107) at the input boundary. Per § 6 + § 14.19.

ARCHITECTURAL INVARIANT (per § 14.21 — v0.7 consolidation):
C6 operates on TWO distinct direction models, intentionally asymmetric:
  - EXTERNAL contract  : 4-direction (cardinal). Input validation
                          rejects intercardinal `plot.facing`; output
                          (direction_priorities, refined_zone_bands) is
                          restricted to cardinals via validator
                          invariants 1 and 9.
  - INTERNAL Vastu     : 8-direction. The PARTIAL Vastu KB is keyed by
                          all 8 PlotOrientation members; cardinal scores
                          are derived via weighted-avg aggregation over
                          each cardinal + its two intercardinal
                          neighbours (§ 4.1.4). Collapsing the table to
                          4-direction would erase the signature Vastu
                          placements (NE/POOJA, SE/KITCHEN, SW/BEDROOM)
                          that live at intercardinal positions in the
                          canonical Mandala.

This asymmetry is by design, not a defect. B-107 will eventually unify
the two by extending the external contract to 8-direction; until then,
the internal-8-dir / external-cardinal split is the documented invariant.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────


class FunctionRole(str, Enum):
    """The six functional room types C6 scores per direction.

    Per SPEC v0.6 § 3. CIRCULATION is intentionally NOT a FunctionRole —
    it's a ZoneBand with its own private scoring helper inside optimizer.py
    (per § 14.20 / Q2).
    """
    LIVING = "living"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    POOJA = "pooja"
    WET_AREA = "wet_area"
    UTILITY = "utility"


# Note (v0.6): there is no PlotDirection8 enum. The existing
# `domain.envelope.PlotOrientation` already provides 8 directions and is
# used throughout C6 for both internal Vastu computation and the cardinal-
# restricted external output. See § 14.19 (Q1-A) for the rationale.


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SignalBreakdown:
    """Per-direction signal contributions. Per SPEC v0.6 § 3.

    Invariants (asserted at construction):
      - sun_score, wind_score, road_score, vastu_score ∈ [0, 1]
      - road_score is provenance-only (§ 14.14); does NOT feed function_scores
      - vastu_score == 0.0 iff vastu_tier == OFF (enforced at producer site,
        not at construction — this dataclass doesn't see vastu_tier)
    """
    sun_score: float
    wind_score: float
    road_score: float
    vastu_score: float

    def __post_init__(self) -> None:
        for name, value in (
            ("sun_score", self.sun_score),
            ("wind_score", self.wind_score),
            ("road_score", self.road_score),
            ("vastu_score", self.vastu_score),
        ):
            if not isinstance(value, (int, float)):
                raise TypeError(f"SignalBreakdown.{name} must be numeric; got {type(value).__name__}")
            if not (0.0 <= float(value) <= 1.0):
                raise ValueError(f"SignalBreakdown.{name} must be in [0, 1]; got {value}")


@dataclass(frozen=True)
class DirectionPriorityScore:
    """Per-direction functional scoring + signal breakdown. Per SPEC v0.6 § 3.

    `function_scores` is keyed by the 6 FunctionRole members ONLY.
    CIRCULATION is NOT a key here — its scoring is a private helper inside
    optimizer.py (§ 14.20 / Q2).

    Invariants (asserted at construction):
      - function_scores covers exactly all 6 FunctionRole members
      - every function_scores value ∈ [0, 1]
    """
    function_scores: Mapping[FunctionRole, float]
    signal_breakdown: SignalBreakdown

    def __post_init__(self) -> None:
        if not isinstance(self.function_scores, Mapping):
            raise TypeError(
                f"DirectionPriorityScore.function_scores must be a Mapping; "
                f"got {type(self.function_scores).__name__}"
            )
        actual_keys = set(self.function_scores.keys())
        expected_keys = set(FunctionRole)
        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            raise ValueError(
                f"DirectionPriorityScore.function_scores must cover exactly the 6 "
                f"FunctionRole members; missing={sorted(m.value for m in missing)} "
                f"extra={sorted(getattr(e, 'value', repr(e)) for e in extra)}"
            )
        for f, v in self.function_scores.items():
            if not isinstance(v, (int, float)):
                raise TypeError(
                    f"DirectionPriorityScore.function_scores[{f.value}] must be numeric; "
                    f"got {type(v).__name__}"
                )
            if not (0.0 <= float(v) <= 1.0):
                raise ValueError(
                    f"DirectionPriorityScore.function_scores[{f.value}] must be in [0, 1]; "
                    f"got {v}"
                )
        if not isinstance(self.signal_breakdown, SignalBreakdown):
            raise TypeError(
                f"DirectionPriorityScore.signal_breakdown must be SignalBreakdown; "
                f"got {type(self.signal_breakdown).__name__}"
            )


@dataclass(frozen=True)
class OrientationProvenance:
    """Why C6 picked this orientation. Per SPEC v0.6 § 3 + § 10.

    Two interpretability fields added in v0.5:
      - signal_dominance ∈ [0, 1] = max(weights_raw) / sum(weights_raw)
      - dominant_signal: "sun" | "wind" | "vastu" | None
        (None when signal_dominance < SIGNAL_DOMINANCE_THRESHOLD)

    Invariants (asserted at construction):
      - vastu_tier is a VastuTier instance
      - weights_applied + weights_raw cover {"sun", "wind", "vastu"}
      - signal_dominance ∈ [0.0, 1.0]
      - dominant_signal in {"sun", "wind", "vastu", None}
      - dominant_signal == None iff signal_dominance < SIGNAL_DOMINANCE_THRESHOLD
        (validator invariant 8 — § 4.6)
      - permutation_search_size >= 0
      - seed_distance >= 0
    """
    derived_at: float
    plot_analysis_trace_id: str
    vastu_tier: VastuTier
    weights_applied: Mapping[str, float]
    weights_raw: Mapping[str, float]
    signal_dominance: float
    dominant_signal: str | None
    climate_profile: str
    rule_trace: tuple[str, ...]
    permutation_search_size: int
    chosen_over_seed: bool
    seed_distance: int

    def __post_init__(self) -> None:
        if not isinstance(self.vastu_tier, VastuTier):
            raise TypeError(
                f"OrientationProvenance.vastu_tier must be VastuTier; "
                f"got {type(self.vastu_tier).__name__}"
            )
        for name, m in (("weights_applied", self.weights_applied),
                         ("weights_raw", self.weights_raw)):
            if not isinstance(m, Mapping):
                raise TypeError(
                    f"OrientationProvenance.{name} must be a Mapping; "
                    f"got {type(m).__name__}"
                )
            if set(m.keys()) != {"sun", "wind", "vastu"}:
                raise ValueError(
                    f"OrientationProvenance.{name} keys must be exactly "
                    f"{{'sun', 'wind', 'vastu'}}; got {sorted(m.keys())}"
                )
        if not (0.0 <= float(self.signal_dominance) <= 1.0):
            raise ValueError(
                f"OrientationProvenance.signal_dominance must be in [0, 1]; "
                f"got {self.signal_dominance}"
            )
        if self.dominant_signal not in (None, "sun", "wind", "vastu"):
            raise ValueError(
                f"OrientationProvenance.dominant_signal must be in "
                f"{{'sun', 'wind', 'vastu', None}}; got {self.dominant_signal!r}"
            )
        # Validator invariant 8 (§ 4.6): dominant_signal == None iff
        # signal_dominance < SIGNAL_DOMINANCE_THRESHOLD
        below = self.signal_dominance < SIGNAL_DOMINANCE_THRESHOLD
        if (self.dominant_signal is None) != below:
            raise ValueError(
                f"OrientationProvenance: dominant_signal must be None iff "
                f"signal_dominance < {SIGNAL_DOMINANCE_THRESHOLD}; "
                f"got dominance={self.signal_dominance}, dominant={self.dominant_signal!r}"
            )
        if not isinstance(self.rule_trace, tuple):
            raise TypeError(
                f"OrientationProvenance.rule_trace must be a tuple; "
                f"got {type(self.rule_trace).__name__}"
            )
        if self.permutation_search_size < 0:
            raise ValueError(
                f"OrientationProvenance.permutation_search_size must be >= 0; "
                f"got {self.permutation_search_size}"
            )
        if self.seed_distance < 0:
            raise ValueError(
                f"OrientationProvenance.seed_distance must be >= 0; "
                f"got {self.seed_distance}"
            )


@dataclass(frozen=True)
class OrientationPriority:
    """C6's orientation refinement for one C5 candidate. Per SPEC v0.6 § 3.

    Invariants (asserted at construction):
      - direction_priorities covers exactly the 4 cardinal PlotOrientation
        members (validator invariant 1, § 4.6)
      - refined_zone_bands values are all in CARDINAL_FACINGS
        (validator invariant 9, § 4.6 — NEW v0.6)
      - priority_confidence ∈ [0, 1]
      - score_margin >= 0
    """
    direction_priorities: Mapping[PlotOrientation, DirectionPriorityScore]
    refined_zone_bands: Mapping[ZoneBand, PlotOrientation]
    priority_confidence: float
    score_margin: float
    provenance: OrientationProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.direction_priorities, Mapping):
            raise TypeError(
                f"OrientationPriority.direction_priorities must be a Mapping; "
                f"got {type(self.direction_priorities).__name__}"
            )
        actual = set(self.direction_priorities.keys())
        if actual != CARDINAL_FACINGS:
            missing = CARDINAL_FACINGS - actual
            extra = actual - CARDINAL_FACINGS
            raise ValueError(
                f"OrientationPriority.direction_priorities must cover exactly "
                f"{{NORTH, EAST, SOUTH, WEST}} (validator invariant 1); "
                f"missing={sorted(d.value for d in missing)} "
                f"extra={sorted(getattr(d, 'value', repr(d)) for d in extra)}"
            )
        for d, s in self.direction_priorities.items():
            if not isinstance(s, DirectionPriorityScore):
                raise TypeError(
                    f"OrientationPriority.direction_priorities[{d.value}] must "
                    f"be DirectionPriorityScore; got {type(s).__name__}"
                )
        if not isinstance(self.refined_zone_bands, Mapping):
            raise TypeError(
                f"OrientationPriority.refined_zone_bands must be a Mapping; "
                f"got {type(self.refined_zone_bands).__name__}"
            )
        # Validator invariant 9 (NEW v0.6): refined_zone_bands values all cardinal
        for b, dir_ in self.refined_zone_bands.items():
            if not isinstance(b, ZoneBand):
                raise TypeError(
                    f"OrientationPriority.refined_zone_bands key must be ZoneBand; "
                    f"got {type(b).__name__}"
                )
            if dir_ not in CARDINAL_FACINGS:
                raise ValueError(
                    f"OrientationPriority.refined_zone_bands[{b.value}] must be "
                    f"a cardinal PlotOrientation (validator invariant 9, § 4.6 "
                    f"NEW v0.6); got {dir_.value}"
                )
        if not (0.0 <= float(self.priority_confidence) <= 1.0):
            raise ValueError(
                f"OrientationPriority.priority_confidence must be in [0, 1]; "
                f"got {self.priority_confidence}"
            )
        if self.score_margin < 0.0:
            raise ValueError(
                f"OrientationPriority.score_margin must be >= 0; "
                f"got {self.score_margin}"
            )
        if not isinstance(self.provenance, OrientationProvenance):
            raise TypeError(
                f"OrientationPriority.provenance must be OrientationProvenance; "
                f"got {type(self.provenance).__name__}"
            )


@dataclass(frozen=True)
class OrientedCandidate:
    """C5 candidate paired with C6's orientation refinement. Per SPEC v0.6 § 3.

    Cardinality preservation: one OrientedCandidate per input TopologyCandidate.
    Position-paired in the output tuple (per § 14.3 / Q3).
    """
    topology_candidate: TopologyCandidate
    orientation: OrientationPriority

    def __post_init__(self) -> None:
        if not isinstance(self.topology_candidate, TopologyCandidate):
            raise TypeError(
                f"OrientedCandidate.topology_candidate must be TopologyCandidate; "
                f"got {type(self.topology_candidate).__name__}"
            )
        if not isinstance(self.orientation, OrientationPriority):
            raise TypeError(
                f"OrientedCandidate.orientation must be OrientationPriority; "
                f"got {type(self.orientation).__name__}"
            )


__all__ = [
    # Constants
    "SIGNAL_DOMINANCE_THRESHOLD",
    "SWAP_HYSTERESIS_THRESHOLD",
    "MAX_PERMUTATION_COUNT",
    "MIN_DENOM",
    "CARDINAL_FACINGS",
    # Enums
    "FunctionRole",
    # Dataclasses
    "SignalBreakdown",
    "DirectionPriorityScore",
    "OrientationProvenance",
    "OrientationPriority",
    "OrientedCandidate",
]

