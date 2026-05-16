"""
BuildemUp - Component 6 (Orientation Priority) - CONSOLIDATED for review

Built per C6 SPEC v0.6 LOCKED (S31 pre-code patch round).
Three changes vs v0.5 LOCKED:
  Q1-A: PlotDirection8 enum dropped (use PlotOrientation throughout)
  Q1-B: Cardinal-only v1 facing; intercardinal raises NotImplementedError(B-107)
  Q2:   CIRCULATION as private _circulation_score helper (NOT a FunctionRole)

Module sequence:
  components/c06/__init__.py      (re-exports)
  components/c06/schema.py        (enums + dataclasses + constants)
  components/c06/vastu_kb.py      (8-dir Vastu table + aggregation)
  components/c06/signals.py       (sun/wind/road + weighting + dominance)
  components/c06/optimizer.py     (perms + prune + score + tie-break +
                                   hysteresis + confidence + _circulation)
  components/c06/select.py        (public prioritize_orientation)

Test suite: 186 tests across 6 test files; all green.
Full project suite: 1725 passed / 1 skipped (vs 1539/1 baseline; ZERO regressions).

NOT a runnable file - module-level imports across boundaries do not work flat.
Read each section as it would be in its own file.
"""


# =============================================================================
# === FILE: components/c06/__init__.py
# =============================================================================

"""
BuildemUp† — Component 6 (Orientation Priority) package init.

Per C6 SPEC v0.6 LOCKED § 5.

Public entry point: ``prioritize_orientation(candidates, plot_analysis, vastu_tier)``.
Re-exports schema names that downstream components (C8+) will consume.

†= placeholder name marker.
"""
from buildemup.components.c06.schema import (
    # Constants
    CARDINAL_FACINGS,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    SIGNAL_DOMINANCE_THRESHOLD,
    SWAP_HYSTERESIS_THRESHOLD,
    # Enums
    FunctionRole,
    # Dataclasses
    DirectionPriorityScore,
    OrientationPriority,
    OrientationProvenance,
    OrientedCandidate,
    SignalBreakdown,
)
from buildemup.components.c06.select import prioritize_orientation

__all__ = [
    "prioritize_orientation",
    # Constants
    "CARDINAL_FACINGS",
    "MAX_PERMUTATION_COUNT",
    "MIN_DENOM",
    "SIGNAL_DOMINANCE_THRESHOLD",
    "SWAP_HYSTERESIS_THRESHOLD",
    # Enums
    "FunctionRole",
    # Dataclasses
    "DirectionPriorityScore",
    "OrientationPriority",
    "OrientationProvenance",
    "OrientedCandidate",
    "SignalBreakdown",
]

# =============================================================================
# === FILE: components/c06/schema.py
# =============================================================================

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

# =============================================================================
# === FILE: components/c06/vastu_kb.py
# =============================================================================

"""
BuildemUp† — Component 6 Vastu KB.

8-direction × 6-function PARTIAL-tier Vastu table + the weighted-average
aggregation rule that maps 8-dir Vastu values to 4-dir cardinal scores.

Per SPEC v0.6 LOCKED § 4.1.4 + § 14.4 + § 14.9 + § 14.19.

Tier handling (§ 6 + § 14.8):
  - OFF      → callers should not invoke this module (vastu_score = 0.0)
  - PARTIAL  → reads from VASTU_TABLE_PARTIAL (this file)
  - FULL     → NotImplementedError; requires populated vastu_engine KB (B-099)

Why this is its own module (Q3 / S31):
  - Tabular KB data, not algorithm — keeps signals.py focused on logic
  - B-099 (FULL tier KB authoring) becomes a self-contained edit
  - Vastu has cultural significance; isolating the table makes future edits
    by domain experts easier to review

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c06.schema import CARDINAL_FACINGS, FunctionRole
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# 8-direction × 6-function Vastu table (PARTIAL tier baseline)
# Per SPEC v0.6 § 4.1.4
# ─────────────────────────────────────────────────────────────────────────────


def _frozen(d: dict[FunctionRole, float]) -> Mapping[FunctionRole, float]:
    """Wrap a per-function dict in MappingProxyType for true immutability."""
    return MappingProxyType(dict(d))


_RAW_VASTU_TABLE: dict[PlotOrientation, dict[FunctionRole, float]] = {
    PlotOrientation.NORTH: {
        FunctionRole.LIVING:   0.85,
        FunctionRole.BEDROOM:  0.6,
        FunctionRole.KITCHEN:  0.3,
        FunctionRole.POOJA:    0.7,
        FunctionRole.WET_AREA: 0.4,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.NORTHEAST: {
        FunctionRole.LIVING:   0.9,
        FunctionRole.BEDROOM:  0.5,
        FunctionRole.KITCHEN:  0.1,
        FunctionRole.POOJA:    1.0,   # signature NE/pooja per § 4.1.4
        FunctionRole.WET_AREA: 0.0,   # signature NE/wet_area = 0.0 per § 4.1.4
        FunctionRole.UTILITY:  0.3,
    },
    PlotOrientation.EAST: {
        FunctionRole.LIVING:   0.85,
        FunctionRole.BEDROOM:  0.7,
        FunctionRole.KITCHEN:  0.5,
        FunctionRole.POOJA:    0.85,
        FunctionRole.WET_AREA: 0.3,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.SOUTHEAST: {
        FunctionRole.LIVING:   0.55,
        FunctionRole.BEDROOM:  0.4,
        FunctionRole.KITCHEN:  1.0,   # signature SE/kitchen per § 4.1.4
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.4,
        FunctionRole.UTILITY:  0.5,
    },
    PlotOrientation.SOUTH: {
        FunctionRole.LIVING:   0.5,
        FunctionRole.BEDROOM:  0.4,
        FunctionRole.KITCHEN:  0.7,
        FunctionRole.POOJA:    0.2,
        FunctionRole.WET_AREA: 0.5,
        FunctionRole.UTILITY:  0.6,
    },
    PlotOrientation.SOUTHWEST: {
        FunctionRole.LIVING:   0.4,
        FunctionRole.BEDROOM:  1.0,   # signature SW/bedroom per § 4.1.4
        FunctionRole.KITCHEN:  0.4,
        FunctionRole.POOJA:    0.2,
        FunctionRole.WET_AREA: 0.5,
        FunctionRole.UTILITY:  0.7,
    },
    PlotOrientation.WEST: {
        FunctionRole.LIVING:   0.5,
        FunctionRole.BEDROOM:  0.7,
        FunctionRole.KITCHEN:  0.6,
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.7,
        FunctionRole.UTILITY:  0.85,
    },
    PlotOrientation.NORTHWEST: {
        FunctionRole.LIVING:   0.55,
        FunctionRole.BEDROOM:  0.6,
        FunctionRole.KITCHEN:  0.7,
        FunctionRole.POOJA:    0.3,
        FunctionRole.WET_AREA: 0.7,
        FunctionRole.UTILITY:  0.9,
    },
}


# Public, immutable view: outer Mapping keyed by all 8 PlotOrientation members,
# inner Mappings keyed by all 6 FunctionRole members.
VASTU_TABLE_PARTIAL: Mapping[PlotOrientation, Mapping[FunctionRole, float]] = (
    MappingProxyType({d: _frozen(table) for d, table in _RAW_VASTU_TABLE.items()})
)


# ─────────────────────────────────────────────────────────────────────────────
# Adjacency (per SPEC v0.6 § 4.1.4)
# ─────────────────────────────────────────────────────────────────────────────


# CCW intercardinal neighbour for each cardinal (compass with N at top,
# rotation = counter-clockwise as viewed from above).
_CCW_ADJACENT: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    PlotOrientation.NORTH: PlotOrientation.NORTHWEST,
    PlotOrientation.EAST:  PlotOrientation.NORTHEAST,
    PlotOrientation.SOUTH: PlotOrientation.SOUTHEAST,
    PlotOrientation.WEST:  PlotOrientation.SOUTHWEST,
})

# CW intercardinal neighbour for each cardinal (clockwise as viewed from above).
_CW_ADJACENT: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    PlotOrientation.NORTH: PlotOrientation.NORTHEAST,
    PlotOrientation.EAST:  PlotOrientation.SOUTHEAST,
    PlotOrientation.SOUTH: PlotOrientation.SOUTHWEST,
    PlotOrientation.WEST:  PlotOrientation.NORTHWEST,
})


def adjacent_intercardinals(cardinal: PlotOrientation) -> tuple[PlotOrientation, PlotOrientation]:
    """Return the two intercardinal neighbours of a cardinal direction.

    Order: (CCW, CW). Per SPEC v0.6 § 4.1.4.

    Raises ValueError if `cardinal` is not in CARDINAL_FACINGS.
    """
    if cardinal not in CARDINAL_FACINGS:
        raise ValueError(
            f"adjacent_intercardinals expects a cardinal PlotOrientation; "
            f"got {cardinal.value} (cardinals: NORTH, EAST, SOUTH, WEST)"
        )
    return (_CCW_ADJACENT[cardinal], _CW_ADJACENT[cardinal])


# ─────────────────────────────────────────────────────────────────────────────
# Vastu score lookup (tier-aware) + 4-dir aggregation
# ─────────────────────────────────────────────────────────────────────────────


def vastu_score_4dir(
    cardinal: PlotOrientation,
    function: FunctionRole,
    tier: VastuTier,
) -> float:
    """Return the Vastu score for (cardinal direction, function) at the given tier.

    Per SPEC v0.6 § 4.1.4 (weighted-average aggregation 8-dir → 4-dir):

        result = (1.0 × VASTU_TABLE[c][f]
                + 0.5 × VASTU_TABLE[ccw_adj(c)][f]
                + 0.5 × VASTU_TABLE[cw_adj(c)][f]) / 2.0

    Tier semantics (§ 6 + § 14.8):
      - OFF     : returns 0.0 (callers should not even invoke us, but defensive)
      - PARTIAL : reads VASTU_TABLE_PARTIAL
      - FULL    : raises NotImplementedError (B-099)

    Raises:
      NotImplementedError if tier == FULL (B-099 — requires vastu_engine KB).
      ValueError if cardinal is not in CARDINAL_FACINGS.
      TypeError if tier is not a VastuTier instance.
    """
    if not isinstance(tier, VastuTier):
        raise TypeError(
            f"vastu_score_4dir: tier must be VastuTier; got {type(tier).__name__}"
        )
    if tier == VastuTier.OFF:
        return 0.0
    if tier == VastuTier.FULL:
        raise NotImplementedError(
            "FULL tier requires vastu_engine KB; B-099. Use PARTIAL."
        )
    # PARTIAL
    if cardinal not in CARDINAL_FACINGS:
        raise ValueError(
            f"vastu_score_4dir expects a cardinal PlotOrientation; "
            f"got {cardinal.value}"
        )
    ccw, cw = adjacent_intercardinals(cardinal)
    return (
        1.0 * VASTU_TABLE_PARTIAL[cardinal][function]
        + 0.5 * VASTU_TABLE_PARTIAL[ccw][function]
        + 0.5 * VASTU_TABLE_PARTIAL[cw][function]
    ) / 2.0


__all__ = [
    "VASTU_TABLE_PARTIAL",
    "adjacent_intercardinals",
    "vastu_score_4dir",
]

# =============================================================================
# === FILE: components/c06/signals.py
# =============================================================================

"""
BuildemUp† — Component 6 signals.

Sun, wind, and road score tables. Signal weighting (per climate + Vastu tier).
Signal dominance derivation. Per-function multipliers.

Per SPEC v0.6 LOCKED §§ 4.1.1–4.1.3, 4.2, 4.3.

Public surface:
  - sun_score(direction)                                   — cardinal direction → [0, 1]
  - wind_score(direction, climate_zone)                    — cardinal direction → [0, 1]
  - road_score(direction, plot_facing, secondary_road_dir) — cardinal direction → [0, 1]
  - sun_function_lookup(function)                          — per-function multiplier
  - wind_function_lookup(function)                         — per-function multiplier
  - compute_weights(climate_zone, vastu_tier)              — returns (weights_raw, weights_applied)
  - compute_signal_dominance(weights_raw)                  — returns (dominance, dominant_signal)

What's NOT here:
  - Vastu table + 4-dir aggregation → vastu_kb.py
  - Permutation enumeration / scoring / tie-break → optimizer.py
  - Public API → select.py

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c06.schema import (
    CARDINAL_FACINGS,
    SIGNAL_DOMINANCE_THRESHOLD,
    FunctionRole,
)
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.1 — Sun-score table (cardinal, climate-independent)
# ─────────────────────────────────────────────────────────────────────────────


_SUN_SCORE: Mapping[PlotOrientation, float] = MappingProxyType({
    PlotOrientation.NORTH: 0.95,
    PlotOrientation.EAST:  0.85,
    PlotOrientation.SOUTH: 0.55,
    PlotOrientation.WEST:  0.20,
})


def sun_score(direction: PlotOrientation) -> float:
    """Per-direction sun score. Per SPEC v0.6 § 4.1.1.

    Cardinal direction only. Intercardinal raises ValueError (caller bug
    if reached — input boundary should have caught it via § 6 row 5).
    """
    if direction not in CARDINAL_FACINGS:
        raise ValueError(
            f"sun_score: cardinal direction required (C6 v1); got {direction.value}. "
            f"Intercardinal facing should have been rejected at input boundary (B-107)."
        )
    return _SUN_SCORE[direction]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.2 — Wind-score table (cardinal × 3 supported climates)
# ─────────────────────────────────────────────────────────────────────────────


_WIND_SCORE: Mapping[ClimateZone, Mapping[PlotOrientation, float]] = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({
        PlotOrientation.NORTH: 0.6,
        PlotOrientation.EAST:  0.7,
        PlotOrientation.SOUTH: 0.9,
        PlotOrientation.WEST:  0.85,
    }),
    ClimateZone.COMPOSITE: MappingProxyType({
        PlotOrientation.NORTH: 0.7,
        PlotOrientation.EAST:  0.6,
        PlotOrientation.SOUTH: 0.5,
        PlotOrientation.WEST:  0.5,
    }),
    ClimateZone.TEMPERATE: MappingProxyType({
        PlotOrientation.NORTH: 0.7,
        PlotOrientation.EAST:  0.7,
        PlotOrientation.SOUTH: 0.7,
        PlotOrientation.WEST:  0.7,
    }),
})


def wind_score(direction: PlotOrientation, climate_zone: ClimateZone) -> float:
    """Per-direction wind score for a supported climate. Per SPEC v0.6 § 4.1.2.

    Raises ValueError if direction is not cardinal.
    Raises NotImplementedError (B-098) if climate is HOT_DRY or COLD.
    """
    if direction not in CARDINAL_FACINGS:
        raise ValueError(
            f"wind_score: cardinal direction required; got {direction.value}"
        )
    if climate_zone not in _WIND_SCORE:
        raise NotImplementedError(
            f"wind_score: climate {climate_zone.value} not supported in v1; B-098. "
            f"Supported: {sorted(c.value for c in _WIND_SCORE)}."
        )
    return _WIND_SCORE[climate_zone][direction]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.1.3 — Road score (provenance-only; does NOT feed function_scores)
# ─────────────────────────────────────────────────────────────────────────────


def road_score(
    direction: PlotOrientation,
    plot_facing: PlotOrientation,
    secondary_road_direction: PlotOrientation | None = None,
) -> float:
    """Per-direction road score. Per SPEC v0.6 § 4.1.3 + § 14.14.

    Returns 1.0 if direction == plot_facing (primary road),
            0.5 if direction == secondary_road_direction (corner plot only),
            0.0 otherwise.

    NOTE: This is provenance-only. road_score does NOT contribute to
    function_scores — entry-on-road is enforced as a hard-constraint
    pruner at § 4.4 step 2 instead. See § 14.14 (v0.3 walk #2 amendment).
    """
    if direction == plot_facing:
        return 1.0
    if secondary_road_direction is not None and direction == secondary_road_direction:
        return 0.5
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# § 4.3 — Per-function lookup multipliers
# ─────────────────────────────────────────────────────────────────────────────


_SUN_FUNCTION_LOOKUP: Mapping[FunctionRole, float] = MappingProxyType({
    FunctionRole.LIVING:   1.0,
    FunctionRole.BEDROOM:  0.7,
    FunctionRole.KITCHEN:  0.6,
    FunctionRole.POOJA:    0.8,
    FunctionRole.WET_AREA: 0.3,
    FunctionRole.UTILITY:  0.3,
})


_WIND_FUNCTION_LOOKUP: Mapping[FunctionRole, float] = MappingProxyType({
    FunctionRole.LIVING:   0.9,
    FunctionRole.BEDROOM:  1.0,
    FunctionRole.KITCHEN:  0.6,
    FunctionRole.POOJA:    0.5,
    FunctionRole.WET_AREA: 0.4,
    FunctionRole.UTILITY:  0.3,
})


def sun_function_lookup(function: FunctionRole) -> float:
    """Per-function sun-affinity multiplier. Per SPEC v0.6 § 4.3."""
    return _SUN_FUNCTION_LOOKUP[function]


def wind_function_lookup(function: FunctionRole) -> float:
    """Per-function wind-affinity multiplier. Per SPEC v0.6 § 4.3 + § 14.11."""
    return _WIND_FUNCTION_LOOKUP[function]


# ─────────────────────────────────────────────────────────────────────────────
# § 4.2 — Signal weighting (per climate + Vastu tier)
# ─────────────────────────────────────────────────────────────────────────────


_VASTU_WEIGHT_BY_TIER: Mapping[VastuTier, float] = MappingProxyType({
    VastuTier.OFF:     0.0,
    VastuTier.PARTIAL: 0.4,
    VastuTier.FULL:    0.7,
})


def compute_weights(
    climate_zone: ClimateZone,
    vastu_tier: VastuTier,
) -> tuple[Mapping[str, float], Mapping[str, float]]:
    """Compute raw + applied (renormalized) signal weights. Per SPEC v0.6 § 4.2.

    Returns:
      (weights_raw, weights_applied) — both Mappings keyed by
      "sun" | "wind" | "vastu", both immutable.

      weights_raw   : per-signal weight pre-normalization (exposed for
                      interpretability / signal_dominance derivation).
      weights_applied: weights_raw renormalized to sum = 1.0 (used in
                      function_scores blending). If raw_total == 0.0,
                      applied is all zeros (defensive; should not happen
                      with valid v1 inputs).

    Raises:
      NotImplementedError (B-098) if climate_zone is not v1-supported.
      TypeError if vastu_tier is not a VastuTier instance.
    """
    if not isinstance(vastu_tier, VastuTier):
        raise TypeError(
            f"compute_weights: vastu_tier must be VastuTier; "
            f"got {type(vastu_tier).__name__}"
        )
    if climate_zone not in _WIND_SCORE:  # same supported set as wind table
        raise NotImplementedError(
            f"compute_weights: climate {climate_zone.value} not supported in v1; "
            f"B-098. Supported: {sorted(c.value for c in _WIND_SCORE)}."
        )

    sun_w = 1.0 if climate_zone in (ClimateZone.COMPOSITE, ClimateZone.TEMPERATE) else 0.7
    wind_w = 1.0 if climate_zone == ClimateZone.WARM_HUMID else 0.6
    vastu_w = _VASTU_WEIGHT_BY_TIER[vastu_tier]

    weights_raw = MappingProxyType({"sun": sun_w, "wind": wind_w, "vastu": vastu_w})
    raw_total = sum(weights_raw.values())
    if raw_total > 0:
        weights_applied = MappingProxyType({
            k: v / raw_total for k, v in weights_raw.items()
        })
    else:
        # Edge case: never happens in v1 valid inputs (sun + wind always > 0)
        weights_applied = MappingProxyType({"sun": 0.0, "wind": 0.0, "vastu": 0.0})

    return (weights_raw, weights_applied)


# ─────────────────────────────────────────────────────────────────────────────
# § 4.2 (v0.5) — Signal dominance derivation
# ─────────────────────────────────────────────────────────────────────────────


def compute_signal_dominance(
    weights_raw: Mapping[str, float],
) -> tuple[float, str | None]:
    """Compute (signal_dominance, dominant_signal) from raw weights.

    Per SPEC v0.6 § 4.2 + § 14.18.

    Returns:
      signal_dominance ∈ [0, 1] = max(weights_raw) / sum(weights_raw).
      dominant_signal: argmax key when dominance >= SIGNAL_DOMINANCE_THRESHOLD,
                       else None.

    Edge case: if all raw weights are zero, returns (0.0, None) defensively.
    """
    raw_total = sum(weights_raw.values())
    if raw_total <= 0.0:
        return (0.0, None)
    max_weight = max(weights_raw.values())
    dominance = max_weight / raw_total
    if dominance >= SIGNAL_DOMINANCE_THRESHOLD:
        # argmax — break ties by the canonical sun → wind → vastu order
        # (deterministic; matches insertion order of the Mapping)
        for k, v in weights_raw.items():
            if v == max_weight:
                return (dominance, k)
    return (dominance, None)


__all__ = [
    "sun_score",
    "wind_score",
    "road_score",
    "sun_function_lookup",
    "wind_function_lookup",
    "compute_weights",
    "compute_signal_dominance",
]

# =============================================================================
# === FILE: components/c06/optimizer.py
# =============================================================================

"""
BuildemUp† — Component 6 optimizer.

Permutation enumeration, entry-on-road pruning, total-score computation,
5-tier tie-break, hysteresis, margin-clamped confidence. Plus the private
_circulation_score helper (per § 14.20 / Q2).

Per SPEC v0.6 LOCKED §§ 4.3, 4.4, 4.5 + § 14.5–14.7, § 14.9–14.17, § 14.19, § 14.20.

Public-within-package surface (consumed by select.py only):
  - enumerate_permutations(seed_zone_bands, topology_kind, courtyard_bands)
  - prune_by_entry_on_road(perms, plot_facing, secondary_road_direction)
  - compute_function_scores(direction, climate, weights_applied, vastu_tier)
  - score_permutation(perm, function_scores_by_dir, climate_zone)
  - tie_break_key(perm, total, seed_perm, function_scores_by_dir)
  - hamming_distance(perm_a, perm_b)
  - apply_hysteresis(global_score, seed_score)
  - compute_confidence(top_score, second_score)
  - BAND_TO_FUNCTION constant

Private:
  - _circulation_score(direction, climate_zone)

†= placeholder name marker.
"""
from __future__ import annotations

import itertools
from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c05.schema import TopologyKind, ZoneBand
from buildemup.components.c06.schema import (
    CARDINAL_FACINGS,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    SWAP_HYSTERESIS_THRESHOLD,
    FunctionRole,
)
from buildemup.components.c06.signals import (
    sun_function_lookup,
    sun_score,
    wind_function_lookup,
    wind_score,
)
from buildemup.components.c06.vastu_kb import vastu_score_4dir
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — band → function mapping (CIRCULATION intentionally absent)
# ─────────────────────────────────────────────────────────────────────────────


BAND_TO_FUNCTION: Mapping[ZoneBand, FunctionRole] = MappingProxyType({
    ZoneBand.PUBLIC:  FunctionRole.LIVING,
    ZoneBand.SERVICE: FunctionRole.KITCHEN,
    ZoneBand.PRIVATE: FunctionRole.BEDROOM,
    # ZoneBand.CIRCULATION → NO mapping; uses _circulation_score private
    # helper instead. Per § 14.10 (light scoring) + § 14.20 (Q2 type fix).
})

FUNCTIONAL_BANDS: frozenset[ZoneBand] = frozenset(BAND_TO_FUNCTION.keys())


# Cardinal cycle order used for lexicographic tie-break (tier 5 of tie_break_key).
# Per SPEC § 4.4 step 4. Standard compass order N → E → S → W.
_CARDINAL_LEX_INDEX: Mapping[PlotOrientation, int] = MappingProxyType({
    PlotOrientation.NORTH: 0,
    PlotOrientation.EAST:  1,
    PlotOrientation.SOUTH: 2,
    PlotOrientation.WEST:  3,
})


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 1 — Permutation enumeration
# ─────────────────────────────────────────────────────────────────────────────


def enumerate_permutations(
    seed_zone_bands: Mapping[ZoneBand, PlotOrientation],
    topology_kind: TopologyKind,
) -> tuple[Mapping[ZoneBand, PlotOrientation], ...]:
    """Enumerate all band → cardinal-direction permutations.

    Per SPEC v0.6 § 4.4 step 1.

    For non-COURTYARD topologies (STRIP, CENTRAL_SPINE, L_SHAPE), bands map
    to DISTINCT cardinal directions: at most 4! = 24 permutations (or fewer
    if the band set is < 4).

    For COURTYARD (LOOP), bands wrap around a central open core and may
    share cardinal directions: at most 4^|bands| = 256 permutations
    (with |bands| = 4: PUBLIC, SERVICE, PRIVATE, CIRCULATION).

    Returns:
      Tuple of immutable (MappingProxyType) Mappings, each keyed by
      seed_zone_bands.keys() with cardinal PlotOrientation values.

    Defensive: if a non-COURTYARD seed has fewer bands than 4, the keyset
    is preserved (band set comes from the seed, not hardcoded).
    """
    bands = tuple(seed_zone_bands.keys())
    cardinals = tuple(sorted(CARDINAL_FACINGS, key=lambda d: _CARDINAL_LEX_INDEX[d]))

    if topology_kind == TopologyKind.COURTYARD:
        # Directions can repeat: itertools.product
        raw_iter = itertools.product(cardinals, repeat=len(bands))
    else:
        # Distinct directions: itertools.permutations (exhausts when |bands|>4)
        raw_iter = itertools.permutations(cardinals, len(bands))

    return tuple(
        MappingProxyType(dict(zip(bands, dir_tuple)))
        for dir_tuple in raw_iter
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 2 — Entry-on-road pruning + cap assertion
# ─────────────────────────────────────────────────────────────────────────────


def prune_by_entry_on_road(
    perms: tuple[Mapping[ZoneBand, PlotOrientation], ...],
    plot_facing: PlotOrientation,
    secondary_road_direction: PlotOrientation | None,
) -> tuple[Mapping[ZoneBand, PlotOrientation], ...]:
    """Keep only permutations whose PUBLIC band faces a road direction.

    Per SPEC v0.6 § 4.4 step 2 + § 14.6.

    A permutation survives if `perm[PUBLIC] == plot_facing` OR (on corner
    plots) `perm[PUBLIC] == secondary_road_direction`.

    Asserts `len(survivors) <= MAX_PERMUTATION_COUNT (= 256)` per § 14.17
    defense-in-depth.

    Note: PUBLIC must be present in the seed bandset; if absent (shouldn't
    happen with valid C5 candidates), no perm survives.
    """
    allowed: set[PlotOrientation] = {plot_facing}
    if secondary_road_direction is not None:
        allowed.add(secondary_road_direction)

    survivors = tuple(
        p for p in perms
        if ZoneBand.PUBLIC in p and p[ZoneBand.PUBLIC] in allowed
    )
    assert len(survivors) <= MAX_PERMUTATION_COUNT, (
        f"prune_by_entry_on_road: post-prune permutation count "
        f"{len(survivors)} exceeds MAX_PERMUTATION_COUNT={MAX_PERMUTATION_COUNT} "
        f"(§ 14.17 defense-in-depth assertion)"
    )
    return survivors


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — Per-direction function scores + CIRCULATION helper
# ─────────────────────────────────────────────────────────────────────────────


def compute_function_scores(
    direction: PlotOrientation,
    climate_zone: ClimateZone,
    weights_applied: Mapping[str, float],
    vastu_tier: VastuTier,
) -> Mapping[FunctionRole, float]:
    """Compute per-function scores for one cardinal direction.

    Per SPEC v0.6 § 4.3. Returns an immutable Mapping keyed by all 6
    FunctionRole members. Values are weighted blends:

        function_scores[f] = (
            sun_score(direction)        * sun_function_lookup(f)  * w_sun
          + wind_score(direction, clim) * wind_function_lookup(f) * w_wind
          + vastu_score_4dir(direction, f, tier)                  * w_vastu
        )

    Vastu term contribution is 0.0 when tier == OFF (since vastu_score is
    0.0 there); raises NotImplementedError(B-099) if tier == FULL.

    Returned scores are clamped to [0, 1] defensively. With weights_applied
    summing to 1.0 and individual sun/wind/vastu factors all in [0, 1],
    the sum is naturally in [0, 1] without clamping; the clamp is belt-and-
    suspenders against floating-point edge cases.
    """
    sun_v = sun_score(direction)
    wind_v = wind_score(direction, climate_zone)
    w_sun = weights_applied["sun"]
    w_wind = weights_applied["wind"]
    w_vastu = weights_applied["vastu"]

    out: dict[FunctionRole, float] = {}
    for f in FunctionRole:
        vastu_v = vastu_score_4dir(direction, f, vastu_tier)
        score = (
            sun_v * sun_function_lookup(f) * w_sun
            + wind_v * wind_function_lookup(f) * w_wind
            + vastu_v * w_vastu
        )
        # Defensive clamp against fp drift; should be in-range natively.
        out[f] = max(0.0, min(1.0, score))
    return MappingProxyType(out)


def _circulation_score(
    direction: PlotOrientation,
    climate_zone: ClimateZone,
) -> float:
    """Light circulation scoring. Private helper. Per SPEC v0.6 § 14.10 + § 14.20.

    NOT a key in DirectionPriorityScore.function_scores. Used only inside
    score_permutation() to weight the CIRCULATION band's contribution.

    Formula (per § 4.4 step 3):

        _circulation_score = 0.3 * sun_score(direction)
                           + 0.2 * wind_score(direction, climate_zone)
                           + 0.5

    Uses RAW direction-baseline sun/wind scores (§ 4.1.1 / § 4.1.2),
    not the weighted blended function_scores. The 0.5 baseline reflects
    that circulation tolerates any direction reasonably well; the
    sun/wind terms add modest bias toward bright/breezy faces.
    """
    return (
        0.3 * sun_score(direction)
        + 0.2 * wind_score(direction, climate_zone)
        + 0.5
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — Total score per permutation
# ─────────────────────────────────────────────────────────────────────────────


def score_permutation(
    perm: Mapping[ZoneBand, PlotOrientation],
    function_scores_by_dir: Mapping[PlotOrientation, Mapping[FunctionRole, float]],
    climate_zone: ClimateZone,
) -> float:
    """Compute the total score for one band → direction permutation.

    Per SPEC v0.6 § 4.4 step 3:

        total_score(perm) = (
            Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
          + 0.5 × _circulation_score(perm[CIRCULATION])
        )

    The CIRCULATION term is multiplied by 0.5 in addition to its internal
    weighting (per § 14.10 light scoring) — together this damps the
    influence of corridor placement vs. functional band placement.

    If a band in `perm` is not in BAND_TO_FUNCTION and not CIRCULATION,
    it's silently skipped (defensive — should not happen with valid bandsets).

    If perm has no CIRCULATION band, the circulation term is 0.0 (defensive
    — STRIP topologies on small T1 plots may legitimately omit circulation).
    """
    total = 0.0
    for band, direction in perm.items():
        if band in BAND_TO_FUNCTION:
            f = BAND_TO_FUNCTION[band]
            total += function_scores_by_dir[direction][f]
        elif band == ZoneBand.CIRCULATION:
            total += 0.5 * _circulation_score(direction, climate_zone)
        # else: unknown band — skip defensively
    return total


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 4 — Hamming distance + 5-tier tie-break key
# ─────────────────────────────────────────────────────────────────────────────


def hamming_distance(
    perm_a: Mapping[ZoneBand, PlotOrientation],
    perm_b: Mapping[ZoneBand, PlotOrientation],
) -> int:
    """Count of (band, direction) pairs that differ between two permutations.

    Per SPEC v0.6 § 13. Range [0, |bands|]. Bands present in only one
    perm count as differing (defensive — should not happen with validated
    permutations from the same enumeration).
    """
    all_bands = set(perm_a.keys()) | set(perm_b.keys())
    return sum(1 for b in all_bands if perm_a.get(b) != perm_b.get(b))


def tie_break_key(
    perm: Mapping[ZoneBand, PlotOrientation],
    total_score: float,
    seed_perm: Mapping[ZoneBand, PlotOrientation],
    function_scores_by_dir: Mapping[PlotOrientation, Mapping[FunctionRole, float]],
) -> tuple[float, int, float, float, tuple[int, ...]]:
    """5-tier deterministic sort key. Per SPEC v0.6 § 4.4 step 4 + § 14.13.

    Sort ascending by this key → best permutation comes first.

    Tiers (all ties broken in order):
      1. -total_score                        — primary (higher score better)
      2. hamming_distance(perm, seed_perm)   — prefer minimal change from seed
      3. -function_scores[perm[PUBLIC]][LIVING]
                                             — prefer best LIVING placement
      4. -function_scores[perm[PRIVATE]][BEDROOM]
                                             — prefer best BEDROOM placement
      5. lex_band_direction(perm)            — final lexicographic determinism

    Defensive: if PUBLIC or PRIVATE is missing from perm, use 0.0 for the
    tier-3/tier-4 component (extreme degenerate case).
    """
    public_dir = perm.get(ZoneBand.PUBLIC)
    private_dir = perm.get(ZoneBand.PRIVATE)
    living_score = (
        function_scores_by_dir[public_dir][FunctionRole.LIVING]
        if public_dir is not None else 0.0
    )
    bedroom_score = (
        function_scores_by_dir[private_dir][FunctionRole.BEDROOM]
        if private_dir is not None else 0.0
    )
    # Lex tier: tuple of (band-sorted direction lex indices). Bands sorted
    # by their enum value for determinism across permutations.
    lex_tuple = tuple(
        _CARDINAL_LEX_INDEX[perm[b]]
        for b in sorted(perm.keys(), key=lambda x: x.value)
    )
    return (
        -total_score,
        hamming_distance(perm, seed_perm),
        -living_score,
        -bedroom_score,
        lex_tuple,
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 4 — Hysteresis vs C5 seed
# ─────────────────────────────────────────────────────────────────────────────


def apply_hysteresis(
    global_top_score: float,
    seed_score: float,
) -> bool:
    """Should C6 swap from the seed to the global top? Per SPEC v0.6 § 4.4 step 4.

    Returns True iff `global_top_score - seed_score >= SWAP_HYSTERESIS_THRESHOLD`.
    Otherwise False — stick with the seed (avoids low-confidence churn).

    Per § 14.13 + § 14.5: when the global optimum and seed are tied on
    primary score (they often will be, since the seed is itself a valid
    candidate considered in the search), the diff is 0.0 — no swap.
    """
    return (global_top_score - seed_score) >= SWAP_HYSTERESIS_THRESHOLD


# ─────────────────────────────────────────────────────────────────────────────
# § 4.5 — Margin-clamped confidence
# ─────────────────────────────────────────────────────────────────────────────


def compute_confidence(top_score: float, second_score: float | None) -> float:
    """Margin-clamped confidence. Per SPEC v0.6 § 4.5 + § 14.15.

        priority_confidence = clamp(
            (top - second) / max(top, MIN_DENOM),
            0.0, 1.0
        )

    If `second_score` is None (only one survivor after pruning), returns
    1.0 (nothing to compare against; max possible confidence).
    """
    if second_score is None:
        return 1.0
    margin = top_score - second_score
    denom = max(top_score, MIN_DENOM)
    return max(0.0, min(1.0, margin / denom))


__all__ = [
    "BAND_TO_FUNCTION",
    "FUNCTIONAL_BANDS",
    "enumerate_permutations",
    "prune_by_entry_on_road",
    "compute_function_scores",
    "score_permutation",
    "hamming_distance",
    "tie_break_key",
    "apply_hysteresis",
    "compute_confidence",
]

# =============================================================================
# === FILE: components/c06/select.py
# =============================================================================

"""
BuildemUp† — Component 6 select (public orchestrator).

Public entry point: ``prioritize_orientation(candidates, plot_analysis, vastu_tier)``.

Per SPEC v0.6 LOCKED §§ 2, 5, 6, 4.6.

Sequence per candidate:
  1. Validate inputs (failure modes per § 6) at session boundary, then
     per-candidate (cheap rechecks).
  2. Derive secondary_road_direction from plot.corner_plot (reuse C4's
     derive_second_street_side function — convention preservation, B-076).
  3. Compute weights (raw, applied) + signal_dominance.
  4. Compute function_scores per cardinal direction.
  5. Enumerate band → direction permutations.
  6. Prune by entry-on-road.
  7. Score every survivor.
  8. Sort by 5-tier tie-break key.
  9. Locate seed score; apply hysteresis (global vs seed).
 10. Build OrientationProvenance + OrientationPriority + OrientedCandidate.
 11. Return position-paired tuple.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.neighbour_context import derive_second_street_side
from buildemup.components.c04.schema import ClimateZone, PlotAnalysis, PlotShape
from buildemup.components.c05.schema import TopologyCandidate, ZoneBand
from buildemup.components.c06.optimizer import (
    apply_hysteresis,
    compute_confidence,
    compute_function_scores,
    enumerate_permutations,
    hamming_distance,
    prune_by_entry_on_road,
    score_permutation,
    tie_break_key,
)
from buildemup.components.c06.schema import (
    CARDINAL_FACINGS,
    DirectionPriorityScore,
    FunctionRole,
    OrientationPriority,
    OrientationProvenance,
    OrientedCandidate,
    SignalBreakdown,
)
from buildemup.components.c06.signals import (
    compute_signal_dominance,
    compute_weights,
    road_score,
)
from buildemup.components.c06.vastu_kb import vastu_score_4dir
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# Climates supported in v1 (per § 6 + B-098).
_SUPPORTED_CLIMATES: frozenset[ClimateZone] = frozenset({
    ClimateZone.WARM_HUMID,
    ClimateZone.COMPOSITE,
    ClimateZone.TEMPERATE,
})


def _validate_session(
    candidates: tuple[TopologyCandidate, ...],
    plot_analysis: PlotAnalysis,
    vastu_tier: VastuTier,
) -> None:
    """Session-level input validation per § 6.

    Order matters: cheapest type checks first, then shape, then facing,
    then climate. Vastu_tier is checked early because it's the most
    common configuration knob.

    Raises:
      TypeError on type mismatches.
      NotImplementedError(B-066) on non-RECTANGULAR shape.
      NotImplementedError(B-107) on intercardinal facing — NEW v0.6.
      NotImplementedError(B-098) on unsupported climate.

    NOTE: FULL Vastu tier is allowed at this gate; the deferred check
    happens inside vastu_score_4dir on first lookup (B-099 hard-fail).
    """
    if not isinstance(candidates, tuple):
        raise TypeError(
            f"prioritize_orientation: candidates must be a tuple; "
            f"got {type(candidates).__name__}"
        )
    if not isinstance(vastu_tier, VastuTier):
        raise TypeError(
            f"prioritize_orientation: vastu_tier must be VastuTier; "
            f"got {type(vastu_tier).__name__}"
        )
    if not isinstance(plot_analysis, PlotAnalysis):
        raise TypeError(
            f"prioritize_orientation: plot_analysis must be PlotAnalysis; "
            f"got {type(plot_analysis).__name__}"
        )
    if plot_analysis.shape != PlotShape.RECTANGULAR:
        raise NotImplementedError(
            f"plot shape {plot_analysis.shape.value} not supported in v1; B-066. "
            f"v1 supports RECTANGULAR only."
        )
    facing = plot_analysis.plot.facing
    if facing not in CARDINAL_FACINGS:
        # NEW v0.6 (Q1-B / § 14.19)
        raise NotImplementedError(
            f"intercardinal facing reserved; B-107. v1 supports cardinal "
            f"facing only. Got {facing.value}."
        )
    if plot_analysis.climate_zone not in _SUPPORTED_CLIMATES:
        raise NotImplementedError(
            f"climate {plot_analysis.climate_zone.value} not supported in v1; "
            f"B-098. v1 supports: "
            f"{sorted(c.value for c in _SUPPORTED_CLIMATES)}."
        )


def _orient_one(
    candidate: TopologyCandidate,
    plot_analysis: PlotAnalysis,
    vastu_tier: VastuTier,
    weights_raw: Mapping[str, float],
    weights_applied: Mapping[str, float],
    signal_dominance: float,
    dominant_signal: str | None,
    fs_by_dir: Mapping[PlotOrientation, Mapping[FunctionRole, float]],
    secondary_road_dir: PlotOrientation | None,
) -> OrientedCandidate:
    """Run the orientation pipeline for one C5 candidate."""
    plot_facing = plot_analysis.plot.facing
    climate = plot_analysis.climate_zone
    seed = candidate.zone_bands

    # § 4.4 step 1
    all_perms = enumerate_permutations(seed, candidate.kind)

    # § 4.4 step 2
    survivors = prune_by_entry_on_road(all_perms, plot_facing, secondary_road_dir)

    # § 6 fallback: all permutations pruned → use C5 seed as-is.
    # Defensive only — the seed itself satisfies entry-on-road for valid
    # C5 output, so survivors should never be empty in practice.
    rule_trace: list[str] = []
    if not survivors:
        rule_trace.append("all_perms_pruned_fallback_to_seed")
        chosen_perm = seed
        chosen_score = score_permutation(seed, fs_by_dir, climate)
        second_score: float | None = None
        chosen_over_seed = False
        seed_dist = 0
        permutation_search_size = 0
    else:
        # § 4.4 step 3: score every survivor
        scored = [(p, score_permutation(p, fs_by_dir, climate)) for p in survivors]

        # § 4.4 step 4: sort by 5-tier tie-break key.
        scored.sort(key=lambda ps: tie_break_key(ps[0], ps[1], seed, fs_by_dir))

        global_perm, global_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else None

        # Locate seed score among survivors (seed satisfies entry-on-road by C5
        # construction; should always be in `survivors` for valid input).
        seed_score: float | None = None
        for p, sc in scored:
            if dict(p) == dict(seed):  # value-equal Mapping comparison
                seed_score = sc
                break
        if seed_score is None:
            # Defensive: seed not among survivors (shouldn't happen for valid
            # C5 output). Fall back to global top with chosen_over_seed=True.
            rule_trace.append("seed_absent_from_survivors_using_global")
            chosen_perm = global_perm
            chosen_score = global_score
            chosen_over_seed = True
        else:
            # § 4.4 step 4: hysteresis check
            if apply_hysteresis(global_score, seed_score):
                chosen_perm = global_perm
                chosen_score = global_score
                chosen_over_seed = True
                rule_trace.append("global_chosen_via_hysteresis")
            else:
                chosen_perm = seed
                chosen_score = seed_score
                chosen_over_seed = False
                rule_trace.append("seed_held_via_hysteresis")

        seed_dist = hamming_distance(chosen_perm, seed)
        permutation_search_size = len(survivors)

    # § 4.5 — confidence
    priority_confidence = compute_confidence(chosen_score, second_score)

    # § 4.4 step 5 — score margin (best - second). Defensive: 0.0 if no second.
    score_margin = (chosen_score - second_score) if second_score is not None else 0.0
    score_margin = max(0.0, score_margin)  # OrientationPriority requires >= 0

    # Build per-direction priorities (DirectionPriorityScore for each cardinal)
    direction_priorities: dict[PlotOrientation, DirectionPriorityScore] = {}
    for d in CARDINAL_FACINGS:
        # Compute road_score for provenance in SignalBreakdown (§ 4.1.3)
        rs = road_score(d, plot_facing, secondary_road_dir)
        # Sun, wind, vastu raw direction scores (per § 3 SignalBreakdown
        # contract — raw direction baselines, not blended)
        from buildemup.components.c06.signals import sun_score, wind_score
        ss = sun_score(d)
        ws = wind_score(d, climate)
        # Vastu summary score for this direction: average across functions
        # (provenance only — not consumed downstream of OrientationPriority).
        # Per § 3 SignalBreakdown.vastu_score: == 0.0 iff vastu_tier == OFF.
        if vastu_tier == VastuTier.OFF:
            vs = 0.0
        else:
            vs_per_f = [vastu_score_4dir(d, f, vastu_tier) for f in FunctionRole]
            vs = sum(vs_per_f) / len(vs_per_f)
            # vs is in [0, 1.5] potentially (since aggregation can exceed 1.0
            # for cells with strong cardinal+intercardinal alignment); clamp.
            vs = max(0.0, min(1.0, vs))

        direction_priorities[d] = DirectionPriorityScore(
            function_scores=fs_by_dir[d],
            signal_breakdown=SignalBreakdown(
                sun_score=ss, wind_score=ws,
                road_score=rs, vastu_score=vs,
            ),
        )

    # Provenance
    provenance = OrientationProvenance(
        derived_at=plot_analysis.provenance.derived_at,
        plot_analysis_trace_id=plot_analysis.trace_id,
        vastu_tier=vastu_tier,
        weights_applied=weights_applied,
        weights_raw=weights_raw,
        signal_dominance=signal_dominance,
        dominant_signal=dominant_signal,
        climate_profile=climate.value,
        rule_trace=tuple(rule_trace),
        permutation_search_size=permutation_search_size,
        chosen_over_seed=chosen_over_seed,
        seed_distance=seed_dist,
    )

    # Final OrientationPriority — validators run in __post_init__
    orientation = OrientationPriority(
        direction_priorities=MappingProxyType(direction_priorities),
        refined_zone_bands=MappingProxyType(dict(chosen_perm)),
        priority_confidence=priority_confidence,
        score_margin=score_margin,
        provenance=provenance,
    )
    return OrientedCandidate(
        topology_candidate=candidate,
        orientation=orientation,
    )


def prioritize_orientation(
    candidates: tuple[TopologyCandidate, ...],
    plot_analysis: PlotAnalysis,
    vastu_tier: VastuTier = VastuTier.OFF,
) -> tuple[OrientedCandidate, ...]:
    """Refine orientation for each C5 candidate. Per SPEC v0.6 LOCKED §§ 2, 5.

    Cardinality preserved: 1-3 C5 candidates → 1-3 OrientedCandidates,
    position-paired in the output tuple.

    Args:
      candidates: tuple of TopologyCandidate from C5 (length 1-3, but
        empty input is also valid → returns empty output).
      plot_analysis: from C4. Must be PlotAnalysis with RECTANGULAR shape,
        cardinal facing, and v1-supported climate (WARM_HUMID, COMPOSITE,
        or TEMPERATE).
      vastu_tier: from C1.brief. OFF (default), PARTIAL, or FULL.

    Returns:
      Tuple of OrientedCandidate, position-paired with input candidates.

    Raises:
      TypeError on type mismatches.
      NotImplementedError(B-066) on non-RECTANGULAR plot shape.
      NotImplementedError(B-107) on intercardinal plot.facing — NEW v0.6.
      NotImplementedError(B-098) on HOT_DRY or COLD climate.
      NotImplementedError(B-099) on FULL Vastu tier (deferred — raised on
        first vastu_score_4dir call inside compute_function_scores).
    """
    # Empty input is valid per § 6: returns empty tuple immediately.
    if isinstance(candidates, tuple) and len(candidates) == 0:
        # Still validate other args so downstream gets early failure on bad inputs.
        if not isinstance(vastu_tier, VastuTier):
            raise TypeError(
                f"prioritize_orientation: vastu_tier must be VastuTier; "
                f"got {type(vastu_tier).__name__}"
            )
        if not isinstance(plot_analysis, PlotAnalysis):
            raise TypeError(
                f"prioritize_orientation: plot_analysis must be PlotAnalysis; "
                f"got {type(plot_analysis).__name__}"
            )
        return ()

    _validate_session(candidates, plot_analysis, vastu_tier)

    # Session-level computations (shared across all candidates).
    weights_raw, weights_applied = compute_weights(
        plot_analysis.climate_zone, vastu_tier,
    )
    signal_dominance, dominant_signal = compute_signal_dominance(weights_raw)

    # Per-cardinal function_scores. Triggers B-099 hard-fail here for FULL
    # tier (compute_function_scores → vastu_score_4dir → NotImplementedError).
    fs_by_dir: dict[PlotOrientation, Mapping[FunctionRole, float]] = {
        d: compute_function_scores(d, plot_analysis.climate_zone, weights_applied, vastu_tier)
        for d in CARDINAL_FACINGS
    }

    # Secondary-road direction (only for corner plots; v1 LEFT convention
    # via C4's derive_second_street_side; eventually B-076 will let users
    # specify explicitly).
    secondary_road_dir: PlotOrientation | None = (
        derive_second_street_side(plot_analysis.plot)
        if plot_analysis.plot.corner_plot else None
    )

    return tuple(
        _orient_one(
            candidate=c,
            plot_analysis=plot_analysis,
            vastu_tier=vastu_tier,
            weights_raw=weights_raw,
            weights_applied=weights_applied,
            signal_dominance=signal_dominance,
            dominant_signal=dominant_signal,
            fs_by_dir=fs_by_dir,
            secondary_road_dir=secondary_road_dir,
        )
        for c in candidates
    )


__all__ = ["prioritize_orientation"]
