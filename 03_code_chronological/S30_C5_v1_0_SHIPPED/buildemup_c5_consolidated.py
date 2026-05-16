# ══════════════════════════════════════════════════════════════════════════════
# BuildemUp C5 (Topology Selector) — CONSOLIDATED REVIEW BUNDLE
# Session 30 (S30) build per C5 SPEC v0.9 LOCKED
#
# Q1: per-topology natural-capacity bedroom-fit table — adopted as proposed
# Q2: runs_along on COURTYARD = plot.facing convention (Option C w/ tweak)
# Q3: _c5_fixtures.py wraps c04.derive(), reuses C4 plot fixtures — adopted
#
# Test status: 120 new C5 tests passing; full suite 1539 passed / 1 skipped
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/domain/floor_brief.py
# DOMAIN: FloorRoomBrief
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — FloorRoomBrief domain dataclass.

Per C5 SPEC v0.9 LOCKED § 2 (input contract). DRAFT-Q 1 adjudicated to
domain placement (vs contracts/) because multiple components consume it:
C5 (topology), C8 (corridor), C9 (placement).

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FloorRoomBrief:
    """Per-floor room requirements. Multi-floor briefs construct one per floor.

    Domain concept (lives in domain/, not contracts/) — multiple components
    consume it. v1 covers the typical Indian residential floor: bedrooms,
    bathrooms, optional kitchen / living / pooja / utility, plus an open-ended
    `other_rooms` tuple for less-common rooms (study, guest, balcony).

    Per C5 SPEC v0.2 PROPOSED § 2:
      - bedroom_count >= 0 (validated in __post_init__)
      - bathroom_count >= 0 (validated in __post_init__)
      - other_rooms is a tuple to keep the dataclass hashable / frozen-friendly
    """
    bedroom_count: int
    bathroom_count: int
    has_kitchen: bool
    has_living: bool
    has_pooja: bool
    has_utility: bool
    other_rooms: tuple[str, ...] = ()
    floor_label: str = "ground"

    def __post_init__(self) -> None:
        if self.bedroom_count < 0:
            raise ValueError(
                f"bedroom_count must be >= 0; got {self.bedroom_count}"
            )
        if self.bathroom_count < 0:
            raise ValueError(
                f"bathroom_count must be >= 0; got {self.bathroom_count}"
            )


__all__ = ["FloorRoomBrief"]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/schema.py
# C5: schema (enums + dataclasses)
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) schema.

All dataclasses + enums for C5. Per SPEC v0.9 LOCKED § 3 + § 14.
Pure types only — no logic, no I/O.

Cumulative across spec rounds:
  - v0.2: TopologyKind, ZoneBand, CorridorPosition, CorridorSketch,
          TopologyProvenance, TopologyCandidate
  - v0.3: ConnectivityType + CorridorSketch fields (approx_length_m,
          connectivity_type)
  - v0.4: low_confidence: bool field on TopologyCandidate
  - v0.5: ScoreBreakdownEntry (raw, weight, contribution)
  - v0.6: prior entry in score_breakdown; branch_label form changed
  - v0.7: top_contributors tuple, branch_weights mapping in provenance
  - v0.8: base_score, prior_value fields on TopologyCandidate
  - v0.9: confidence_gap, score_margin fields; ScoreBreakdownEntry split
          into contribution_raw / contribution_final; raw_branch_total
          in provenance

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

# NOTE: the Plot dataclass is intentionally NOT imported in any C5 module;
# C5 reads plot fields via plot_analysis.plot.* per the guardrail test in
# tests/validation/test_c5_consumes_plot_analysis.py (which forbids C5
# from importing the Plot type via either of the two import-statement
# spellings the test checks for).  PlotOrientation lives in domain.envelope
# (a separate module), which IS importable.
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────


class TopologyKind(str, Enum):
    """The four v1 topology kinds. Per C5 SPEC v0.2 § 3.

    More kinds (Hall-centric, U-shape, T-shape) are B-086 — added when a real
    plot fails to fit any of these four.
    """
    STRIP = "strip"
    CENTRAL_SPINE = "central_spine"
    L_SHAPE = "l_shape"
    COURTYARD = "courtyard"


class ZoneBand(str, Enum):
    """Functional bands within a floor. Per C5 SPEC v0.2 § 3.

    Climate-variant zone-band assignment is B-091.
    """
    PUBLIC = "public"            # living, dining, foyer
    SERVICE = "service"          # kitchen, utility, pooja
    CIRCULATION = "circulation"
    PRIVATE = "private"          # bedrooms, attached baths


class CorridorPosition(str, Enum):
    """Where the corridor sits relative to the building shell.

    Per C5 SPEC v0.2 § 3.
    """
    NONE = "none"                # Strip topologies on small T1 plots
    CENTRAL = "central"          # Down the middle (Central Spine)
    PERIMETER = "perimeter"      # Wraps inside the shell (Courtyard)
    L_BENT = "l_bent"            # L-shape only


class ConnectivityType(str, Enum):
    """Corridor topology shape. Added in v0.3 § 14.6 (D8).

    Used by the consistency validator (v0.5 § 14.7) to assert the
    sketch shape matches the topology kind.
    """
    LINEAR = "linear"            # Strip, Central Spine
    BRANCHED = "branched"        # L-shape (two arms meeting at a junction)
    LOOP = "loop"                # Courtyard (corridor wraps the open core)


# ─────────────────────────────────────────────────────────────────────────────
# Sub-dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CorridorSketch:
    """Nominal corridor footprint. C8 (Corridor Designer) refines geometry.

    Per C5 SPEC v0.2 § 3 + v0.3 § 14.6 (approx_length_m, connectivity_type).

    runs_along semantics (Q2 design decision, S30):
      For LINEAR (STRIP, CENTRAL_SPINE) and BRANCHED (L_SHAPE) topologies,
      runs_along is the corridor's primary direction. For COURTYARD (LOOP),
      the corridor has no primary direction; runs_along is then a CONVENTION
      carrying plot.facing — the plot's front-of-plot reference. C8 produces
      the actual loop geometry.
    """
    position: CorridorPosition
    nominal_width_m: float
    runs_along: PlotOrientation
    approx_length_m: float                          # v0.3 § 14.6 (D8)
    connectivity_type: ConnectivityType             # v0.3 § 14.6 (D8)


@dataclass(frozen=True)
class ScoreBreakdownEntry:
    """Per-criterion score detail, exposed for debugging + tuning.

    Per C5 SPEC v0.5 § 14.4 + v0.9 § 14.3.

    contribution_raw   = raw × weight                (intrinsic — sums to base_score
                                                      across criteria; for the
                                                      synthetic "prior" entry it
                                                      is the prior's raw value)
    contribution_final = raw × weight × 0.85         (final-blended; sums to
                                                      0.85 × base_score across
                                                      criteria; for the "prior"
                                                      entry it is 0.15 × prior)

    Across all entries (criteria + prior),
    sum(contribution_final) == score (the candidate's final score).
    """
    raw: float
    weight: float
    contribution_raw: float                         # v0.9 § 14.3 (#4)
    contribution_final: float                       # v0.9 § 14.3 (#4)


@dataclass(frozen=True)
class TopologyProvenance:
    """Tracking metadata: when this analysis was derived + branch trace.

    Per C5 SPEC v0.2 § 3 + v0.7 § 14.4 (branch_weights) + v0.9 § 14.4
    (raw_branch_total).

    derived_at: pulled from plot_analysis.provenance.derived_at (Q8 — single
                pipeline clock; C5 does not mint its own timestamp).
    candidate_decision_table_match: human-readable dominant-branch label
                in the v0.6 form `blend_<dominant>@<weight>` (e.g.,
                "blend_wide_few_bedrooms@0.80").
    branch_weights: full normalized branch-weight breakdown summing to 1.0.
                    Keys: "corner", "wide_few_bedrooms", "narrow_many_bedrooms",
                    "large", "default".
    raw_branch_total: sum of the FOUR branch weights BEFORE normalization
                      (excludes default). Distinguishes scenarios that collapse
                      to the same normalized priors but had different raw signal
                      strength.
    """
    derived_at: float
    plot_analysis_trace_id: str
    candidate_decision_table_match: str
    branch_weights: Mapping[str, float]             # v0.7 § 14.4 (#10)
    raw_branch_total: float                         # v0.9 § 14.4 (#5)


@dataclass(frozen=True)
class TopologyCandidate:
    """One ranked topology candidate. Frozen, fully-described.

    Cumulative spec lineage:
      v0.2: kind, score, score_breakdown, zone_bands, corridor_sketch,
            justification, provenance
      v0.4: + low_confidence
      v0.5: score_breakdown promoted to Mapping[str, ScoreBreakdownEntry]
      v0.7: + top_contributors
      v0.8: + base_score, prior_value
      v0.9: + confidence_gap, score_margin

    Invariants (asserted at construction in select.py):
      score == 0.85 × base_score + 0.15 × prior_value           (v0.8)
      confidence_gap == abs(base_score - score)                 (v0.9 § 14.2)
                     == 0.15 × abs(base_score - prior_value)
      sum(e.contribution_final for e in score_breakdown.values()) == score
                                                                (v0.9 § 14.3)
      sum(e.contribution_raw  for c, e in score_breakdown.items()
          if c != "prior") == base_score                        (v0.9 § 14.3)
      score_margin >= 0.0                                       (v0.9 § 14.5)
      score, base_score, prior_value, confidence_gap, score_margin ∈ [0, 1]
      low_confidence == (score < LOW_CONFIDENCE_THRESHOLD = 0.30) (v0.6 § 14.6 + v0.9 § 14.1)
    """
    kind: TopologyKind
    score: float                                    # final = 0.85 × base + 0.15 × prior
    base_score: float                               # v0.8 § 14.1 (#4)
    prior_value: float                              # v0.8 § 14.1 (#4)
    confidence_gap: float                           # v0.9 § 14.2 (#3)
    score_margin: float                             # v0.9 § 14.5 (#10)
    score_breakdown: Mapping[str, ScoreBreakdownEntry]
    top_contributors: tuple[str, ...]               # v0.7 § 14.3 (#5) + v0.8 § 14.2 dyn threshold
    zone_bands: Mapping[ZoneBand, PlotOrientation]
    corridor_sketch: CorridorSketch
    low_confidence: bool                            # v0.4 § 14.3 (#6)
    justification: str                              # ≤ 200 chars
    provenance: TopologyProvenance


# ─────────────────────────────────────────────────────────────────────────────
# TopologyPriors — internal-to-C5 dataclass for the decision table
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TopologyPriors:
    """Soft prior multipliers per topology kind. Internal-to-C5.

    Per C5 SPEC v0.3 § 14.1 + v0.4 § 14.2 (tightened spread to {1.0, 0.85, 0.7})
    + v0.5 § 14.2 (smooth ramps + interpolation) + v0.6 § 14.1 (multi-branch
    blending) + v0.7 § 14.1 (proper normalization fix for math defect).

    Each value in [0, 1]. Combined with base_score via
        final_score = 0.85 × base_score + 0.15 × prior_value
    per v0.5 § 14.1 (#1) additive blend.
    """
    strip: float
    central_spine: float
    l_shape: float
    courtyard: float

    def for_kind(self, kind: TopologyKind) -> float:
        """Lookup the prior for a given topology kind."""
        if kind == TopologyKind.STRIP:
            return self.strip
        if kind == TopologyKind.CENTRAL_SPINE:
            return self.central_spine
        if kind == TopologyKind.L_SHAPE:
            return self.l_shape
        if kind == TopologyKind.COURTYARD:
            return self.courtyard
        raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


__all__ = [
    "TopologyKind",
    "ZoneBand",
    "CorridorPosition",
    "ConnectivityType",
    "CorridorSketch",
    "ScoreBreakdownEntry",
    "TopologyProvenance",
    "TopologyCandidate",
    "TopologyPriors",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/decision_table.py
# C5: decision_table (assign_priors)
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) decision table.

Per C5 SPEC v0.9 LOCKED § 14 (cumulative through v0.2-v0.9).

Implements the multi-branch prior-blending decision table that smoothly maps
(plot, room_brief) to a TopologyPriors quadruple plus provenance metadata.

Cumulative architectural lineage:
  v0.2 § 4.1: hard-filter decision table (4 branches + default)
  v0.3 § 14.1: replace hard filter with soft TopologyPriors (D1)
  v0.3 § 14.2: wide-but-shallow guard (D2 — small in-table fix)
  v0.4 § 14.2: tighten prior spread to {1.0, 0.85, 0.7} (#2)
  v0.4 § 14.4: smooth ramp on shallow plot (#8)
  v0.5 § 14.2: generalize smooth ramps to ALL four thresholds (#4)
  v0.6 § 14.1: multi-branch weighted blending (#2 — no dispatch discontinuity)
  v0.7 § 14.1: PROPER normalization fix (math defect — when raw_total > 1,
               scale all branch weights so they sum to 1; w_default = 0)
  v0.9 § 14.4: capture raw_branch_total in provenance (diagnostic)

Web research (Rule 7): no external standards invoked at this layer; thresholds
trace to the project's architecture doc (Apr 17 session). Empirical recalibration
against Indian-market data is B-090.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c05.schema import TopologyPriors
from buildemup.domain.floor_brief import FloorRoomBrief


# ─── Architecture-doc thresholds in metric (1 ft = 0.3048 m exact) ──────────
# Q3 adjudication: metric internal; comments may cite ft for traceability.

WIDE_THRESHOLD_M:    float = 26.0 * 0.3048    #  7.9248 m
NARROW_THRESHOLD_M:  float = 22.0 * 0.3048    #  6.7056 m
LARGE_W_THRESHOLD_M: float = 40.0 * 0.3048    # 12.1920 m
LARGE_D_THRESHOLD_M: float = 60.0 * 0.3048    # 18.2880 m

# ─── Smooth-ramp half-widths per v0.5 § 14.2 / NEXT_CLAUDE_HANDOFF #3 ───────
# wide:   ±0.5m around 7.9248m → low=7.4248, high=8.4248
# narrow: ±0.5m around 6.7056m → low=6.2056, high=7.2056
# large_w:±1.0m around 12.192m → low=11.192, high=13.192
# large_d:±1.0m around 18.288m → low=17.288, high=19.288
# shallow: ratio low=0.5, high=0.8

_WIDE_RAMP_LOW    = WIDE_THRESHOLD_M    - 0.5
_WIDE_RAMP_HIGH   = WIDE_THRESHOLD_M    + 0.5
_NARROW_RAMP_LOW  = NARROW_THRESHOLD_M  - 0.5
_NARROW_RAMP_HIGH = NARROW_THRESHOLD_M  + 0.5
_LARGE_W_RAMP_LOW   = LARGE_W_THRESHOLD_M - 1.0
_LARGE_W_RAMP_HIGH  = LARGE_W_THRESHOLD_M + 1.0
_LARGE_D_RAMP_LOW   = LARGE_D_THRESHOLD_M - 1.0
_LARGE_D_RAMP_HIGH  = LARGE_D_THRESHOLD_M + 1.0
_SHALLOW_RAMP_LOW   = 0.5
_SHALLOW_RAMP_HIGH  = 0.8


# ─── Per-branch preferred priors (v0.4 § 14.2 tighter spread {1.0, 0.85, 0.7})

_P_DEFAULT = TopologyPriors(strip=1.0,  central_spine=1.0,  l_shape=0.7, courtyard=0.7)
_P_CORNER  = TopologyPriors(strip=0.85, central_spine=0.7,  l_shape=1.0, courtyard=0.7)
_P_WIDE    = TopologyPriors(strip=1.0,  central_spine=0.85, l_shape=0.7, courtyard=0.7)
_P_NARROW  = TopologyPriors(strip=0.7,  central_spine=1.0,  l_shape=0.7, courtyard=0.7)
_P_LARGE   = TopologyPriors(strip=0.85, central_spine=0.7,  l_shape=0.7, courtyard=1.0)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _smooth_ramp(value: float, low: float, high: float) -> float:
    """Linear ramp: 0.0 when value ≤ low, 1.0 when value ≥ high, linear between.

    Per v0.5 § 14.2 utility (used at every decision-table threshold).
    """
    if high <= low:                                  # defensive (high should always > low)
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


# ─── Public entry ──────────────────────────────────────────────────────────


def assign_priors(
    plot_analysis: object,
    room_brief: FloorRoomBrief,
) -> tuple[TopologyPriors, str, Mapping[str, float], float]:
    """Compute the soft prior multipliers for the four topology kinds.

    Per C5 SPEC v0.6 § 14.1 + v0.7 § 14.1 (math fix) + v0.9 § 14.4 (raw total).

    Reads ``plot_analysis.plot.width_m``, ``plot_analysis.plot.depth_m``,
    ``plot_analysis.plot.corner_plot``. The Plot dataclass itself is NOT
    imported here — C5 must consume PlotAnalysis (placeholder guardrail
    test enforces).

    Returns:
        A 4-tuple ``(priors, branch_label, branch_weights, raw_branch_total)``:

          - ``priors``: blended TopologyPriors (each value in [0, 1]).
          - ``branch_label``: human-readable form ``"blend_<dominant>@<weight>"``.
          - ``branch_weights``: frozen mapping with the five normalized weights
            (corner, wide_few_bedrooms, narrow_many_bedrooms, large, default)
            summing to 1.0. For the candidate_decision_table_match field
            and downstream provenance.
          - ``raw_branch_total``: sum of FOUR branch weights BEFORE
            normalization (excludes default). Diagnostic field surfaced in
            TopologyProvenance per v0.9 § 14.4 (#5) — distinguishes scenarios
            that collapse to the same normalized priors.

    Raises:
        AttributeError: if ``plot_analysis.plot`` does not have the expected
        Plot fields. Defensive — C4 contract guarantees these exist.
    """
    plot = plot_analysis.plot
    width_m = plot.width_m
    depth_m = plot.depth_m
    is_corner = bool(plot.corner_plot)

    # ── Smooth-ramp membership factors (v0.5 § 14.2) ─────────────────────
    wide_f       = _smooth_ramp(width_m, _WIDE_RAMP_LOW, _WIDE_RAMP_HIGH)
    narrow_f     = 1.0 - _smooth_ramp(width_m, _NARROW_RAMP_LOW, _NARROW_RAMP_HIGH)
    large_w_f    = _smooth_ramp(width_m, _LARGE_W_RAMP_LOW, _LARGE_W_RAMP_HIGH)
    large_d_f    = _smooth_ramp(depth_m, _LARGE_D_RAMP_LOW, _LARGE_D_RAMP_HIGH)
    # shallow factor: 1.0 = no demotion (depth/width >= 0.8); 0.0 = full demotion (≤ 0.5)
    if width_m > 1e-6:
        ratio_dw = depth_m / width_m
    else:
        ratio_dw = 0.0                               # defensive (Plot validates > 0)
    shallow_f    = _smooth_ramp(ratio_dw, _SHALLOW_RAMP_LOW, _SHALLOW_RAMP_HIGH)

    # ── Brief gating (v0.6 § 14.1) ───────────────────────────────────────
    few_beds  = room_brief.bedroom_count <= 2
    many_beds = room_brief.bedroom_count >= 2

    # ── Per-branch raw weights ───────────────────────────────────────────
    # corner is binary in the input contract (plot.corner_plot is bool); no ramp
    w_corner   = 1.0 if is_corner else 0.0
    w_wide     = wide_f                if (few_beds  and not is_corner) else 0.0
    w_narrow   = narrow_f              if (many_beds and not is_corner) else 0.0
    w_large    = min(large_w_f, large_d_f) if not is_corner else 0.0

    # Apply shallow-plot factor to the wide branch (v0.5 § 14.4 #8 carry-over)
    w_wide *= shallow_f

    # ── v0.9 § 14.4 (#5): capture raw branch total BEFORE normalization ──
    raw_branch_total = w_corner + w_wide + w_narrow + w_large

    # ── v0.7 § 14.1 (#2) MATH DEFECT FIX: proper normalization ───────────
    # When raw sum > 1.0 we MUST scale branch weights down (so they sum to 1)
    # and zero out w_default. Otherwise the blend uses raw weights summing
    # to > 1, producing priors > 1 (the v0.6 bug).
    if raw_branch_total > 1.0:
        scale = 1.0 / raw_branch_total
        w_corner *= scale
        w_wide   *= scale
        w_narrow *= scale
        w_large  *= scale
        w_default = 0.0
    else:
        w_default = 1.0 - raw_branch_total

    # Post-normalization: w_corner + w_wide + w_narrow + w_large + w_default == 1.0

    # ── Convex-combination blend ─────────────────────────────────────────
    blended = TopologyPriors(
        strip = (
            w_corner * _P_CORNER.strip
            + w_wide   * _P_WIDE.strip
            + w_narrow * _P_NARROW.strip
            + w_large  * _P_LARGE.strip
            + w_default* _P_DEFAULT.strip
        ),
        central_spine = (
            w_corner * _P_CORNER.central_spine
            + w_wide   * _P_WIDE.central_spine
            + w_narrow * _P_NARROW.central_spine
            + w_large  * _P_LARGE.central_spine
            + w_default* _P_DEFAULT.central_spine
        ),
        l_shape = (
            w_corner * _P_CORNER.l_shape
            + w_wide   * _P_WIDE.l_shape
            + w_narrow * _P_NARROW.l_shape
            + w_large  * _P_LARGE.l_shape
            + w_default* _P_DEFAULT.l_shape
        ),
        courtyard = (
            w_corner * _P_CORNER.courtyard
            + w_wide   * _P_WIDE.courtyard
            + w_narrow * _P_NARROW.courtyard
            + w_large  * _P_LARGE.courtyard
            + w_default* _P_DEFAULT.courtyard
        ),
    )

    # ── Branch label: dominant by weight (v0.6 § 14.1) ───────────────────
    branches = (
        ("corner",                w_corner),
        ("wide_few_bedrooms",     w_wide),
        ("narrow_many_bedrooms",  w_narrow),
        ("large",                 w_large),
        ("default_strip_or_central", w_default),
    )
    dominant_name, dominant_weight = max(branches, key=lambda kv: kv[1])
    branch_label = f"blend_{dominant_name}@{dominant_weight:.2f}"

    branch_weights = MappingProxyType({
        "corner":                w_corner,
        "wide_few_bedrooms":     w_wide,
        "narrow_many_bedrooms":  w_narrow,
        "large":                 w_large,
        "default":               w_default,
    })

    return blended, branch_label, branch_weights, raw_branch_total


__all__ = [
    "assign_priors",
    "WIDE_THRESHOLD_M",
    "NARROW_THRESHOLD_M",
    "LARGE_W_THRESHOLD_M",
    "LARGE_D_THRESHOLD_M",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/scorers.py
# C5: scorers (7 criteria + weights)
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) per-criterion scorers.

Per C5 SPEC v0.9 LOCKED § 14 (cumulative through v0.2-v0.9).

Implements:
  - The 7 base criterion scorers, each returning a value in [0, 1]
  - Context-aware weight multipliers (v0.3 § 14.3) with renormalization
  - Per-topology min-bedroom factor (v0.7 § 14.2)
  - Q1 design (S30): _topology_base_bedroom_fit per-topology natural-capacity
    table

Cumulative architectural lineage:
  v0.2 § 4.2: 7 criteria + base weights summing to 1.0
  v0.3 § 14.3: context multipliers (corner / T1 / T3) + renormalization
  v0.5 § 14.5: COURTYARD bedroom-count penalty (#8)
  v0.6 § 14.2: smooth bedroom penalty (#4) — replaced step function
  v0.7 § 14.2: per-topology min-bedrooms (extends penalty to all 4 topologies)

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone, PlotTier
from buildemup.components.c05.schema import TopologyKind
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.floor_brief import FloorRoomBrief


# ─── Base weights (v0.2 § 4.2 + Q4 adjudication: starting values) ───────────
BASE_WEIGHTS: Mapping[str, float] = MappingProxyType({
    "width_fit":         0.25,
    "bedroom_fit":       0.20,
    "open_side_count":   0.15,
    "climate_fit":       0.15,
    "corner_fit":        0.10,
    "aspect_ratio_fit":  0.10,
    "corridor_overhead": 0.05,
})
# Invariant: sum(BASE_WEIGHTS.values()) == 1.0 exactly.
# Locked by tests/validation/test_c5_scorers.py::test_base_weights_sum_to_one.


# ─── Per-topology min bedrooms (v0.7 § 14.2 #8) ─────────────────────────────
TOPOLOGY_MIN_BEDROOMS: Mapping[TopologyKind, int] = MappingProxyType({
    TopologyKind.STRIP:         1,
    TopologyKind.CENTRAL_SPINE: 2,
    TopologyKind.L_SHAPE:       2,
    TopologyKind.COURTYARD:     3,
})


# ─── Context multipliers (v0.3 § 14.3) ──────────────────────────────────────


def _context_weight_multipliers(
    plot_analysis: object,
) -> Mapping[str, float]:
    """Per-context multipliers BEFORE renormalization to sum=1.

    Per C5 SPEC v0.3 § 14.3.

    Reads plot_analysis.plot.corner_plot and plot_analysis.tier.
    """
    plot = plot_analysis.plot
    tier = plot_analysis.tier
    is_corner = bool(plot.corner_plot)

    m: dict[str, float] = {k: 1.0 for k in BASE_WEIGHTS}
    if is_corner:
        m["corner_fit"] = 2.0     # boost: must be decisive on corner plots
        m["width_fit"]  = 0.6     # reduce: width matters less when L-shape is in play
    if tier == PlotTier.T3_LARGE:
        m["width_fit"]         = 0.5    # reduce: large plots fit any topology width-wise
        m["corridor_overhead"] = 2.0    # boost: corridor cost matters on big plots
        m["climate_fit"]       = 1.5    # boost: courtyard becomes a real option
    if tier == PlotTier.T1_COMPACT:
        m["bedroom_fit"] = 1.5    # boost: tight plots → bedroom packing dominates
    return MappingProxyType(m)


def effective_weights(plot_analysis: object) -> Mapping[str, float]:
    """Context-multiplied weights renormalized to sum exactly to 1.0.

    Per C5 SPEC v0.3 § 14.3 + v0.4 § 14.5 (max-weight ≤ 0.35 invariant).
    """
    mults = _context_weight_multipliers(plot_analysis)
    raw = {k: BASE_WEIGHTS[k] * mults[k] for k in BASE_WEIGHTS}
    total = sum(raw.values())
    return MappingProxyType({k: v / total for k, v in raw.items()})


# ─── Per-criterion scorers (each returns [0, 1]) ────────────────────────────


def score_width_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """How well plot width accommodates this topology's bands.

    STRIP needs ≥ ~7.9m comfortably; CENTRAL_SPINE prefers ≤ ~6.7m;
    L_SHAPE / COURTYARD are flexible.
    """
    width = plot_analysis.plot.width_m
    if topology == TopologyKind.STRIP:
        # Best fit at 8m+; degrades below 7m and above 12m (gets unwieldy)
        if width >= 8.0 and width <= 12.0:
            return 1.0
        if width < 8.0:
            # Linear from 0 at 5m to 1 at 8m
            return max(0.0, min(1.0, (width - 5.0) / 3.0))
        # width > 12m
        return max(0.4, 1.0 - (width - 12.0) / 8.0)
    if topology == TopologyKind.CENTRAL_SPINE:
        # Best fit at 6-9m; tolerates wider
        if 6.0 <= width <= 9.0:
            return 1.0
        if width < 6.0:
            return max(0.0, min(1.0, (width - 4.0) / 2.0))
        # width > 9m
        return max(0.5, 1.0 - (width - 9.0) / 6.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape needs at least ~6m width to bend meaningfully
        if width >= 7.0:
            return 1.0
        return max(0.0, min(1.0, (width - 5.0) / 2.0))
    if topology == TopologyKind.COURTYARD:
        # Courtyard needs serious width (≥ 11m) to fit a real open core
        if width >= 11.0:
            return 1.0
        # Linear from 0 at 8m to 1 at 11m
        return max(0.0, min(1.0, (width - 8.0) / 3.0))
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def _topology_base_bedroom_fit(topology: TopologyKind, bedroom_count: int) -> float:
    """Per-topology natural-capacity score (Q1 design, S30).

    Step function over integer bedroom_count — bedroom_count is fundamentally
    an integer (humans don't have 2.5 bedrooms in a brief), so smoothing here
    would be artificial. The smoothing program (v0.4 § 14.4 / v0.5 § 14.2)
    targets continuous variables (width_m, depth_m, depth/width ratio).

    Sweet spots:
      STRIP:         1-2 (single-row layout)
      CENTRAL_SPINE: 2-4 (dual-flank corridor amortizes well)
      L_SHAPE:       2-3 (two arms, ~1-2 bedrooms per arm)
      COURTYARD:     3-5 (perimeter wraps need ≥3 to surround the open core)
    """
    if topology == TopologyKind.STRIP:
        if bedroom_count in (1, 2):
            return 1.0
        if bedroom_count == 3:
            return 0.7
        return 0.4   # >= 4
    if topology == TopologyKind.CENTRAL_SPINE:
        if bedroom_count in (2, 3, 4):
            return 1.0
        if bedroom_count in (1, 5):
            return 0.7
        return 0.4   # 0 or >= 6
    if topology == TopologyKind.L_SHAPE:
        if bedroom_count in (2, 3):
            return 1.0
        if bedroom_count in (1, 4):
            return 0.7
        return 0.4   # 0 or >= 5
    if topology == TopologyKind.COURTYARD:
        if bedroom_count in (3, 4, 5):
            return 1.0
        if bedroom_count in (2, 6):
            return 0.7
        return 0.4   # 0, 1, or >= 7
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_bedroom_fit(topology: TopologyKind, room_brief: FloorRoomBrief) -> float:
    """Bedroom-fit scorer per C5 SPEC v0.7 § 14.2 #8.

    Combines Q1 base table with the per-topology min-bedrooms factor
    ``min(1, bedroom_count / min_bedrooms[topology])``.

    Effect of factor (illustrative, multiplied with the base table):
      STRIP min=1:    factor=1.0 for any bedroom_count >= 1
      CENTRAL_SPINE min=2:  factor=0.5 at 1 bed, 1.0 at 2+
      L_SHAPE min=2:        factor=0.5 at 1 bed, 1.0 at 2+
      COURTYARD min=3:      factor=0.333 at 1, 0.667 at 2, 1.0 at 3+
    """
    base = _topology_base_bedroom_fit(topology, room_brief.bedroom_count)
    min_beds = TOPOLOGY_MIN_BEDROOMS[topology]
    if room_brief.bedroom_count <= 0:
        # bedroom_count==0 should give factor=0 (no bedrooms → topology vacuous)
        factor = 0.0
    else:
        factor = min(1.0, room_brief.bedroom_count / float(min_beds))
    return base * factor


def score_open_side_count(topology: TopologyKind, plot_analysis: object) -> float:
    """More open sides → courtyard's main ventilation benefit weakens → favours
    Strip / CENTRAL_SPINE / L_SHAPE on detached plots.

    Reads plot_analysis.neighbour_context.open_sides (tuple[PlotOrientation, ...]).
    """
    n_open = len(plot_analysis.neighbour_context.open_sides)
    # 0 to 4 open sides; map to per-topology preference
    if topology == TopologyKind.STRIP:
        # Strip benefits from open sides (cross-ventilation along front-back axis)
        return min(1.0, n_open / 3.0)              # 0→0, 3→1, 4→1
    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine benefits from open flanks (cross-ventilation perpendicular to spine)
        return min(1.0, n_open / 3.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape works on a corner (2 open sides typical); neutral overall
        return 0.6 + 0.1 * min(1.0, n_open / 4.0)  # 0.6 to 0.7 as opens increase
    if topology == TopologyKind.COURTYARD:
        # Courtyard's main job is ventilation when sides are SHARED.
        # Many open sides → courtyard less needed → score declines.
        # 0 open: 1.0; 1 open: 0.85; 2 open: 0.7; 3 open: 0.5; 4 open: 0.3
        if n_open == 0: return 1.0
        if n_open == 1: return 0.85
        if n_open == 2: return 0.7
        if n_open == 3: return 0.5
        return 0.3
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_climate_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """Climate suitability per topology.

    Warm-humid (Chennai, Mumbai) favours cross-ventilation → CENTRAL_SPINE,
    COURTYARD. Composite (Delhi) favours STRIP / CENTRAL_SPINE (less courtyard
    benefit due to dust, hot summers). Temperate (Bangalore, Pune, Hyderabad)
    is forgiving — all topologies workable.

    HOT_DRY and COLD are reserved (no v1 city maps to them).
    """
    cz = plot_analysis.climate_zone
    if cz == ClimateZone.WARM_HUMID:
        if topology == TopologyKind.CENTRAL_SPINE: return 1.0
        if topology == TopologyKind.COURTYARD:    return 0.9
        if topology == TopologyKind.STRIP:        return 0.7
        if topology == TopologyKind.L_SHAPE:      return 0.6
    if cz == ClimateZone.COMPOSITE:
        if topology == TopologyKind.STRIP:         return 0.9
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.7
        if topology == TopologyKind.COURTYARD:     return 0.5
    if cz == ClimateZone.TEMPERATE:
        if topology == TopologyKind.STRIP:         return 0.85
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.75
        if topology == TopologyKind.COURTYARD:     return 0.7
    if cz == ClimateZone.HOT_DRY:                  # Reserved — no v1 city
        if topology == TopologyKind.COURTYARD:     return 1.0
        if topology == TopologyKind.CENTRAL_SPINE: return 0.7
        if topology == TopologyKind.STRIP:         return 0.5
        if topology == TopologyKind.L_SHAPE:       return 0.5
    if cz == ClimateZone.COLD:                     # Reserved — no v1 city
        if topology == TopologyKind.STRIP:         return 0.85
        if topology == TopologyKind.CENTRAL_SPINE: return 0.85
        if topology == TopologyKind.L_SHAPE:       return 0.7
        if topology == TopologyKind.COURTYARD:     return 0.4
    return 0.6                                     # pragma: no cover (defensive)


def score_corner_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """corner_plot=True heavily favours L_SHAPE; 0 for non-corner.

    Per C5 SPEC v0.2 § 4.2.
    """
    is_corner = bool(plot_analysis.plot.corner_plot)
    if not is_corner:
        # Non-corner: L_SHAPE gets 0; others moderate (corner-fit irrelevant)
        if topology == TopologyKind.L_SHAPE:
            return 0.0
        return 0.7
    # Corner plot
    if topology == TopologyKind.L_SHAPE:    return 1.0
    if topology == TopologyKind.STRIP:      return 0.7
    if topology == TopologyKind.CENTRAL_SPINE: return 0.5
    if topology == TopologyKind.COURTYARD:  return 0.5
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_aspect_ratio_fit(topology: TopologyKind, plot_analysis: object) -> float:
    """Aspect ratio (depth/width) suitability.

    aspect_ratio > 1.5 (deep plot) penalizes STRIP (front-to-back layout
    becomes a long corridor problem).
    """
    ar = plot_analysis.aspect_ratio
    if topology == TopologyKind.STRIP:
        if ar <= 1.5:                      return 1.0
        if ar <= 2.0:                      return 0.7
        return max(0.3, 1.0 - (ar - 1.5) / 2.0)
    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine actually benefits from deeper plots
        if 1.2 <= ar <= 2.5:               return 1.0
        if ar < 1.2:                       return 0.7
        return max(0.5, 1.0 - (ar - 2.5) / 2.0)
    if topology == TopologyKind.L_SHAPE:
        # L-shape works at moderate ratios
        if 0.8 <= ar <= 1.8:               return 1.0
        return 0.7
    if topology == TopologyKind.COURTYARD:
        # Courtyard prefers near-square plots
        if 0.9 <= ar <= 1.4:               return 1.0
        if 0.7 <= ar <= 1.7:               return 0.7
        return 0.4
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


def score_corridor_overhead(topology: TopologyKind, plot_analysis: object) -> float:
    """Corridor cost — HIGHER raw means LESS overhead (this is fitness).

    Per C5 SPEC v0.2 § 4.2 + v0.6 § 14.4 (tie-break uses raw value:
    higher raw = less overhead = wins ties).

    plot_analysis is accepted for symmetry with other scorers (allows future
    plot-size-dependent overhead). v1 uses topology-only, but signature is
    stable.
    """
    _ = plot_analysis                                # currently unused; signature stable
    # STRIP has the lowest overhead; COURTYARD the highest.
    if topology == TopologyKind.STRIP:         return 1.0
    if topology == TopologyKind.CENTRAL_SPINE: return 0.8
    if topology == TopologyKind.L_SHAPE:       return 0.6
    if topology == TopologyKind.COURTYARD:     return 0.4
    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


# ─── Aggregate scorer (returns Mapping[str, float] for select.py) ──────────


def compute_raw_scores(
    topology: TopologyKind,
    plot_analysis: object,
    room_brief: FloorRoomBrief,
) -> Mapping[str, float]:
    """Return all 7 criterion raw scores for a single topology, frozen.

    Per C5 SPEC v0.2 § 4.2 + v0.5 § 14.4 (ScoreBreakdownEntry construction
    happens in select.py using these raw scores).
    """
    return MappingProxyType({
        "width_fit":         score_width_fit(topology, plot_analysis),
        "bedroom_fit":       score_bedroom_fit(topology, room_brief),
        "open_side_count":   score_open_side_count(topology, plot_analysis),
        "climate_fit":       score_climate_fit(topology, plot_analysis),
        "corner_fit":        score_corner_fit(topology, plot_analysis),
        "aspect_ratio_fit":  score_aspect_ratio_fit(topology, plot_analysis),
        "corridor_overhead": score_corridor_overhead(topology, plot_analysis),
    })


__all__ = [
    "BASE_WEIGHTS",
    "TOPOLOGY_MIN_BEDROOMS",
    "effective_weights",
    "compute_raw_scores",
    "score_width_fit",
    "score_bedroom_fit",
    "score_open_side_count",
    "score_climate_fit",
    "score_corner_fit",
    "score_aspect_ratio_fit",
    "score_corridor_overhead",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/zone_bands.py
# C5: zone_bands + corridor sketch
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) zone-band assignments.

Per C5 SPEC v0.9 LOCKED § 4.3 (cumulative through v0.2).

Implements the default zone-band → compass-direction mapping for each
topology (rotated relative to plot.facing) plus the CorridorSketch builder
for each topology.

Q5 adjudication: one default per topology + B-091 (climate-variant overrides
deferred). Pattern E avoidance — climate-aware zone bands when those become
empirically needed, not pre-empirically.

Q2 design (S30): runs_along on COURTYARD (LOOP) is a CONVENTION carrying
plot.facing — the plot's front-of-plot reference. C8 produces the actual
loop geometry.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import compute_plot_facing_sides
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    CorridorSketch,
    TopologyKind,
    ZoneBand,
)
from buildemup.domain.envelope import PlotOrientation


# ─── Zone-band assignment ──────────────────────────────────────────────────


def default_zone_bands(
    topology: TopologyKind,
    facing: PlotOrientation,
) -> Mapping[ZoneBand, PlotOrientation]:
    """Default zone-band → compass direction mapping per topology.

    Per C5 SPEC v0.2 § 4.3 (one default per topology; B-091 for climate
    variants).

    The defaults are expressed relative to plot.facing; the helper
    compute_plot_facing_sides() (from c04.schema) translates them to absolute
    compass directions.

    | Topology      | Default assignment                                          |
    |---------------|-------------------------------------------------------------|
    | STRIP         | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |
    | CENTRAL_SPINE | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |
    | L_SHAPE       | front=PUBLIC, back=PRIVATE, left=CIRCULATION                 |
    | COURTYARD     | front=PUBLIC, back=PRIVATE, left=SERVICE, right=CIRCULATION |

    Note on duplicates (validator-relevant):
      - All topologies except L_SHAPE assign 4 distinct directions.
      - L_SHAPE assigns 3 (PUBLIC, PRIVATE, CIRCULATION) — junction acts as
        circulation; SERVICE band sits within the public arm at this resolution.
      - The validator (consistency check, v0.5 § 14.7 + v0.6 § 14.5) requires
        the per-topology required-bands set to be present and distinct
        directions for non-COURTYARD topologies.
    """
    sides = compute_plot_facing_sides(facing)        # {"front", "back", "left", "right"}

    if topology == TopologyKind.STRIP:
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.CIRCULATION: sides["right"],
            ZoneBand.PRIVATE:     sides["back"],
        })

    if topology == TopologyKind.CENTRAL_SPINE:
        # Central spine: public + service flank one direction; private flanks
        # the opposite; circulation runs front-to-back through the middle.
        # Default v0.2 § 4.3: one_flank=(PUBLIC+SERVICE), other_flank=PRIVATE.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.CIRCULATION: sides["right"],
            ZoneBand.PRIVATE:     sides["back"],
        })

    if topology == TopologyKind.L_SHAPE:
        # L-shape: front_arm=PUBLIC, side_arm=PRIVATE, junction=CIRCULATION.
        # Required bands per v0.6 § 14.5: {PUBLIC, PRIVATE, CIRCULATION}.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.PRIVATE:     sides["back"],
            ZoneBand.CIRCULATION: sides["left"],
        })

    if topology == TopologyKind.COURTYARD:
        # Courtyard: front=PUBLIC, sides=SERVICE+PRIVATE, courtyard=CIRCULATION.
        # Per v0.6 § 14.5: COURTYARD is exempted from the distinct-directions
        # rule because the courtyard CIRCULATION band shares space with
        # other bands at this sketch resolution.
        return MappingProxyType({
            ZoneBand.PUBLIC:      sides["front"],
            ZoneBand.SERVICE:     sides["left"],
            ZoneBand.PRIVATE:     sides["right"],
            ZoneBand.CIRCULATION: sides["back"],
        })

    raise ValueError(f"unknown TopologyKind: {topology!r}")  # pragma: no cover


# ─── CorridorSketch builder ────────────────────────────────────────────────


def _connectivity_for(kind: TopologyKind) -> ConnectivityType:
    """Connectivity is fully determined by topology kind (v0.3 § 14.6).

    STRIP / CENTRAL_SPINE = LINEAR; L_SHAPE = BRANCHED; COURTYARD = LOOP.
    """
    if kind in (TopologyKind.STRIP, TopologyKind.CENTRAL_SPINE):
        return ConnectivityType.LINEAR
    if kind == TopologyKind.L_SHAPE:
        return ConnectivityType.BRANCHED
    if kind == TopologyKind.COURTYARD:
        return ConnectivityType.LOOP
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def _corridor_position_for(kind: TopologyKind) -> CorridorPosition:
    """Per the consistency validator (v0.5 § 14.7) required positions.

    STRIP -> NONE (small T1) or CENTRAL — v1 default uses CENTRAL because
    sketches at C5 still represent a nominal corridor; corridor erasure on
    small T1 plots is a C8 decision.
    CENTRAL_SPINE -> CENTRAL.
    L_SHAPE -> L_BENT.
    COURTYARD -> PERIMETER.
    """
    if kind == TopologyKind.STRIP:
        return CorridorPosition.CENTRAL
    if kind == TopologyKind.CENTRAL_SPINE:
        return CorridorPosition.CENTRAL
    if kind == TopologyKind.L_SHAPE:
        return CorridorPosition.L_BENT
    if kind == TopologyKind.COURTYARD:
        return CorridorPosition.PERIMETER
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def _approx_length_m_for(kind: TopologyKind, width_m: float, depth_m: float) -> float:
    """Per C5 SPEC v0.3 § 14.6 (D8) approx_length_m formulas.

    The 0.85 / 0.5 / 0.4 multipliers approximate the post-setback usable run.
    Refined by C8.
    """
    if kind == TopologyKind.STRIP:
        return depth_m * 0.85
    if kind == TopologyKind.CENTRAL_SPINE:
        return depth_m * 0.85
    if kind == TopologyKind.L_SHAPE:
        return (width_m + depth_m) * 0.5
    if kind == TopologyKind.COURTYARD:
        return 2.0 * (width_m + depth_m) * 0.4
    raise ValueError(f"unknown TopologyKind: {kind!r}")  # pragma: no cover


def build_corridor_sketch(
    topology: TopologyKind,
    plot_analysis: object,
) -> CorridorSketch:
    """Build the CorridorSketch for a given topology + plot.

    Per C5 SPEC v0.2 § 3 + v0.3 § 14.6 + Q2 design (S30) for COURTYARD.
    """
    plot = plot_analysis.plot
    width_m = plot.width_m
    depth_m = plot.depth_m
    facing = plot.facing

    # runs_along (Q2 — Option C with micro tweak):
    #   For LINEAR (STRIP, CENTRAL_SPINE) and BRANCHED (L_SHAPE) topologies,
    #   runs_along is the corridor's primary direction. For COURTYARD (LOOP),
    #   the corridor has no primary direction; runs_along is then a CONVENTION
    #   carrying plot.facing — the plot's front-of-plot reference. C8 produces
    #   the actual loop geometry.
    runs_along = facing

    # nominal_width_m: 1.2m default (NBC-aligned residential corridor minimum)
    # — refined by C8.
    nominal_width_m = 1.2

    return CorridorSketch(
        position=_corridor_position_for(topology),
        nominal_width_m=nominal_width_m,
        runs_along=runs_along,
        approx_length_m=_approx_length_m_for(topology, width_m, depth_m),
        connectivity_type=_connectivity_for(topology),
    )


__all__ = [
    "default_zone_bands",
    "build_corridor_sketch",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/select.py
# C5: select (orchestrator)
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) orchestrator.

Per C5 SPEC v0.9 LOCKED § 5 (invocation contract).

Public entry point: select_topology(plot_analysis, room_brief)
                   -> tuple[TopologyCandidate, ...]

Cumulative architectural lineage (per spec versions):
  v0.2: 7-criterion weighted-sum scoring; tuple of 1-3 candidates returned
  v0.3 § 14.4: Q7 reversal — RuntimeError on all-fail removed; top is always
               returned with low_confidence flag when score < threshold
  v0.4 § 14.3: structured low_confidence: bool field (uniform per candidate)
  v0.5 § 14.1: additive blend final = 0.85 × base + 0.15 × prior
  v0.5 § 14.4: ScoreBreakdownEntry with raw / weight / contribution
  v0.5 § 14.7: consistency validator (kind ↔ corridor ↔ zone bands)
  v0.6 § 14.3: prior entry added to score_breakdown
  v0.6 § 14.4: tie-break by corridor_overhead.raw (higher raw = less overhead)
  v0.6 § 14.5: stronger consistency validator (zone-band shape)
  v0.6 § 14.6: low_confidence is uniform per candidate (doc clarification)
  v0.7 § 14.3: top_contributors derived field
  v0.8 § 14.1: base_score, prior_value fields with invariant
  v0.8 § 14.2: dynamic top_contributors threshold (max_n=3, threshold_pct=0.10)
  v0.9 § 14.1: NAMED constants LOW_CONFIDENCE_THRESHOLD,
               MIN_CANDIDATE_ADMISSION_THRESHOLD (#7)
  v0.9 § 14.2: confidence_gap derived field (#3)
  v0.9 § 14.3: ScoreBreakdownEntry split into contribution_raw / contribution_final (#4)
  v0.9 § 14.4: raw_branch_total in TopologyProvenance (#5)
  v0.9 § 14.5: score_margin field (gap to next candidate) (#10)

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import PlotShape
from buildemup.components.c05.decision_table import assign_priors
from buildemup.components.c05.scorers import (
    BASE_WEIGHTS,
    compute_raw_scores,
    effective_weights,
)
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    ScoreBreakdownEntry,
    TopologyCandidate,
    TopologyKind,
    TopologyPriors,
    TopologyProvenance,
    ZoneBand,
)
from buildemup.components.c05.zone_bands import (
    build_corridor_sketch,
    default_zone_bands,
)
from buildemup.domain.floor_brief import FloorRoomBrief


# ─── v0.9 § 14.1 (#7) — NAMED THRESHOLD CONSTANTS ──────────────────────────
# Promoted from inline literal 0.30 to named module-level constants.
# Naming them clarifies semantic intent and makes future tuning (e.g.,
# empirical recalibration via B-090) a single-site change rather than a
# code-archaeology grep.

LOW_CONFIDENCE_THRESHOLD: float = 0.30
"""Top candidate's score below this threshold sets low_confidence=True.
Named separately from MIN_CANDIDATE_ADMISSION_THRESHOLD because they serve
distinct semantic roles (confidence flag vs admission filter) even when
numerically equal at v0.9 LOCK time."""

MIN_CANDIDATE_ADMISSION_THRESHOLD: float = 0.30
"""Secondary candidates (2nd, 3rd) must score >= this to be returned in the
candidate tuple. Top candidate is always returned regardless (per v0.3 § 14.4
Q7 reversal)."""

# v0.5 § 14.1 additive blend constants
_BASE_BLEND_WEIGHT:  float = 0.85
_PRIOR_BLEND_WEIGHT: float = 0.15

# v0.4 § 14.5 max-weight invariant (codified in test_c5_scorers.py)
_MAX_NORMALIZED_WEIGHT: float = 0.35

# Top-contributors threshold (v0.8 § 14.2)
_TOP_CONTRIB_MAX_N: int          = 3
_TOP_CONTRIB_THRESHOLD_PCT: float = 0.10

# Tie-break thresholds (relative; v0.3 § 14.4-14.5)
_TIE_RELATIVE_DELTA_2ND: float = 0.10
_TIE_RELATIVE_DELTA_3RD: float = 0.15

# Justification max length (v0.2 § 3)
_JUSTIFICATION_MAX_LEN: int = 200


# ─── Internal scored-candidate dataclass (mutable during scoring) ──────────


class _ScoredCandidate:
    """Internal-only mutable scratch data for one candidate during scoring.

    Frozen TopologyCandidate is constructed at the end. This intermediate
    form carries everything we need for sorting, tie-break, and final
    construction.
    """
    __slots__ = (
        "kind", "raw_scores", "weights", "base_score", "prior_value",
        "score", "score_breakdown",
    )

    def __init__(
        self,
        kind: TopologyKind,
        raw_scores: Mapping[str, float],
        weights: Mapping[str, float],
        base_score: float,
        prior_value: float,
        score: float,
        score_breakdown: Mapping[str, ScoreBreakdownEntry],
    ) -> None:
        self.kind = kind
        self.raw_scores = raw_scores
        self.weights = weights
        self.base_score = base_score
        self.prior_value = prior_value
        self.score = score
        self.score_breakdown = score_breakdown


# ─── Helpers ────────────────────────────────────────────────────────────────


def _build_score_breakdown(
    raw_scores: Mapping[str, float],
    weights: Mapping[str, float],
    prior: float,
) -> Mapping[str, ScoreBreakdownEntry]:
    """Build ScoreBreakdownEntry mapping per v0.9 § 14.3 (#4).

    Splits contribution into intrinsic (raw × weight) and final-blended
    (raw × weight × 0.85). Adds the synthetic "prior" entry.

    Invariants (asserted by tests):
      sum(e.contribution_raw   for c, e in entries.items() if c != "prior") == base_score
      sum(e.contribution_final for e in entries.values())                   == score
      entries["prior"].contribution_raw   == prior
      entries["prior"].contribution_final == 0.15 * prior
    """
    entries: dict[str, ScoreBreakdownEntry] = {}
    for criterion, raw in raw_scores.items():
        w = weights[criterion]
        entries[criterion] = ScoreBreakdownEntry(
            raw=raw,
            weight=w,
            contribution_raw=raw * w,                          # intrinsic
            contribution_final=raw * w * _BASE_BLEND_WEIGHT,   # final-blended (× 0.85)
        )
    entries["prior"] = ScoreBreakdownEntry(
        raw=prior,
        weight=_PRIOR_BLEND_WEIGHT,
        contribution_raw=prior,                                 # intrinsic prior
        contribution_final=_PRIOR_BLEND_WEIGHT * prior,         # 0.15 × prior
    )
    return MappingProxyType(entries)


def _compute_top_contributors(
    score_breakdown: Mapping[str, ScoreBreakdownEntry],
    *,
    max_n: int = _TOP_CONTRIB_MAX_N,
    threshold_pct: float = _TOP_CONTRIB_THRESHOLD_PCT,
) -> tuple[str, ...]:
    """Dynamic threshold-based top contributors per v0.8 § 14.2 (#5).

    Sort by contribution_final descending; include all entries within
    threshold_pct of the top contribution. Cap at max_n. Ties on contribution
    broken alphabetically by criterion name (deterministic).
    """
    if not score_breakdown:
        return ()
    sorted_entries = sorted(
        score_breakdown.items(),
        key=lambda kv: (-kv[1].contribution_final, kv[0]),
    )
    top_contrib = sorted_entries[0][1].contribution_final
    if top_contrib <= 0:
        return (sorted_entries[0][0],)
    cutoff = top_contrib * (1.0 - threshold_pct)
    selected: list[str] = []
    for name, entry in sorted_entries:
        if entry.contribution_final < cutoff:
            break
        selected.append(name)
        if len(selected) >= max_n:
            break
    return tuple(selected)


def _build_justification(
    kind: TopologyKind,
    score: float,
    top_contributors: tuple[str, ...],
    branch_label: str,
    low_confidence: bool,
) -> str:
    """Human-readable why-this-rank string. Max 200 chars per v0.2 § 3."""
    parts = [
        f"{kind.value} (score {score:.2f})",
        f"top: {', '.join(top_contributors[:2]) if top_contributors else 'none'}",
        f"branch: {branch_label}",
    ]
    if low_confidence:
        parts.append("LOW-CONFIDENCE")
    text = " | ".join(parts)
    if len(text) > _JUSTIFICATION_MAX_LEN:
        text = text[: _JUSTIFICATION_MAX_LEN - 1] + "…"
    return text


def _validate_candidate_consistency(c: TopologyCandidate) -> None:
    """Internal-consistency invariants per v0.5 § 14.7 + v0.6 § 14.5.

    Catches bugs introduced by future refactors where topology kind, corridor
    sketch, and zone-band assignment fall out of sync.
    """
    expected_position = {
        TopologyKind.STRIP:         (CorridorPosition.NONE, CorridorPosition.CENTRAL),
        TopologyKind.CENTRAL_SPINE: (CorridorPosition.CENTRAL,),
        TopologyKind.L_SHAPE:       (CorridorPosition.L_BENT,),
        TopologyKind.COURTYARD:     (CorridorPosition.PERIMETER,),
    }
    if c.corridor_sketch.position not in expected_position[c.kind]:
        raise RuntimeError(
            f"candidate consistency violation: {c.kind.value} topology has "
            f"corridor position {c.corridor_sketch.position.value}, expected "
            f"one of {[p.value for p in expected_position[c.kind]]}"
        )

    expected_connectivity = {
        TopologyKind.STRIP:         ConnectivityType.LINEAR,
        TopologyKind.CENTRAL_SPINE: ConnectivityType.LINEAR,
        TopologyKind.L_SHAPE:       ConnectivityType.BRANCHED,
        TopologyKind.COURTYARD:     ConnectivityType.LOOP,
    }
    if c.corridor_sketch.connectivity_type != expected_connectivity[c.kind]:
        raise RuntimeError(
            f"candidate consistency violation: {c.kind.value} topology has "
            f"connectivity {c.corridor_sketch.connectivity_type.value}, expected "
            f"{expected_connectivity[c.kind].value}"
        )

    if not c.zone_bands:
        raise RuntimeError(f"{c.kind.value} candidate has empty zone_bands")

    # v0.6 § 14.5 (#7): per-topology required-bands set
    required_bands = {
        TopologyKind.STRIP:         {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.CIRCULATION, ZoneBand.PRIVATE},
        TopologyKind.CENTRAL_SPINE: {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.CIRCULATION, ZoneBand.PRIVATE},
        TopologyKind.L_SHAPE:       {ZoneBand.PUBLIC, ZoneBand.PRIVATE,
                                     ZoneBand.CIRCULATION},
        TopologyKind.COURTYARD:     {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.PRIVATE, ZoneBand.CIRCULATION},
    }
    have = set(c.zone_bands.keys())
    missing = required_bands[c.kind] - have
    if missing:
        raise RuntimeError(
            f"{c.kind.value} candidate missing required zone bands: "
            f"{sorted(b.value for b in missing)}"
        )

    # No-duplicate-direction check (relaxed for COURTYARD per v0.6 § 14.5)
    if c.kind != TopologyKind.COURTYARD:
        used_directions = list(c.zone_bands.values())
        if len(used_directions) != len(set(used_directions)):
            raise RuntimeError(
                f"{c.kind.value} has duplicate compass directions in zone_bands: "
                f"{used_directions}"
            )


def _make_candidate(
    sc: _ScoredCandidate,
    plot_analysis: object,
    branch_label: str,
    branch_weights: Mapping[str, float],
    raw_branch_total: float,
    low_confidence: bool,
    score_margin: float,
) -> TopologyCandidate:
    """Construct a frozen TopologyCandidate from a _ScoredCandidate.

    Computes derived fields (confidence_gap, top_contributors, justification),
    builds the corridor sketch and zone bands, asserts the v0.8 invariant,
    and runs the consistency validator.
    """
    # v0.9 § 14.2 (#3): confidence_gap = abs(base_score - score)
    confidence_gap = abs(sc.base_score - sc.score)

    top_contributors = _compute_top_contributors(sc.score_breakdown)

    justification = _build_justification(
        kind=sc.kind,
        score=sc.score,
        top_contributors=top_contributors,
        branch_label=branch_label,
        low_confidence=low_confidence,
    )

    zone_bands  = default_zone_bands(sc.kind, plot_analysis.plot.facing)
    corridor    = build_corridor_sketch(sc.kind, plot_analysis)

    provenance = TopologyProvenance(
        derived_at=plot_analysis.provenance.derived_at,
        plot_analysis_trace_id=plot_analysis.trace_id,
        candidate_decision_table_match=branch_label,
        branch_weights=branch_weights,
        raw_branch_total=raw_branch_total,
    )

    candidate = TopologyCandidate(
        kind=sc.kind,
        score=sc.score,
        base_score=sc.base_score,
        prior_value=sc.prior_value,
        confidence_gap=confidence_gap,
        score_margin=score_margin,
        score_breakdown=sc.score_breakdown,
        top_contributors=top_contributors,
        zone_bands=zone_bands,
        corridor_sketch=corridor,
        low_confidence=low_confidence,
        justification=justification,
        provenance=provenance,
    )

    # v0.5 § 14.7 + v0.6 § 14.5 — consistency validator
    _validate_candidate_consistency(candidate)

    # v0.8 § 14.1 invariant — score == 0.85 × base + 0.15 × prior
    expected_score = (
        _BASE_BLEND_WEIGHT * sc.base_score + _PRIOR_BLEND_WEIGHT * sc.prior_value
    )
    if abs(candidate.score - expected_score) > 1e-9:
        raise RuntimeError(
            f"v0.8 § 14.1 invariant violation for {sc.kind.value}: "
            f"score={candidate.score:.6f} but 0.85×base+0.15×prior="
            f"{expected_score:.6f}"
        )

    return candidate


# ─── Input validation ──────────────────────────────────────────────────────


def _validate_inputs(plot_analysis: object, room_brief: FloorRoomBrief) -> None:
    """Per spec § 6 failure modes."""
    if not isinstance(room_brief, FloorRoomBrief):
        raise TypeError(
            f"room_brief must be FloorRoomBrief; got {type(room_brief).__name__}"
        )
    # plot_analysis is a duck-typed object; we read fields rather than
    # isinstance-check (no Plot/PlotAnalysis import in this module is
    # required for the runtime path, but PlotShape comes from c04 schema
    # which IS importable).
    shape = getattr(plot_analysis, "shape", None)
    if shape is not None and shape != PlotShape.RECTANGULAR:
        raise NotImplementedError(
            f"v1 supports rectangular plots only (got {shape.value}); B-066"
        )


# ─── Public entry point ────────────────────────────────────────────────────


def select_topology(
    plot_analysis: object,
    room_brief: FloorRoomBrief,
) -> tuple[TopologyCandidate, ...]:
    """Select 1-3 ranked topology candidates.

    Per C5 SPEC v0.9 LOCKED § 5.

    Args:
        plot_analysis: Frozen PlotAnalysis from C4 (typed as ``object`` here
            to keep this module decoupled from c04's structural type and to
            satisfy the placeholder guardrail test which forbids importing
            Plot in C5).
        room_brief: FloorRoomBrief — per-floor room requirements.

    Returns:
        Tuple of 1-3 TopologyCandidate, score-ordered descending. Top
        candidate always returned (Q7 reversal — never RuntimeError on all-fail);
        secondary candidates require score >= MIN_CANDIDATE_ADMISSION_THRESHOLD
        AND relative score gap within tie-break thresholds.

    Raises:
        TypeError: room_brief is not a FloorRoomBrief.
        NotImplementedError: plot_analysis.shape != RECTANGULAR (B-066).
    """
    _validate_inputs(plot_analysis, room_brief)

    # ── Decision table: priors + provenance metadata ─────────────────────
    priors, branch_label, branch_weights, raw_branch_total = assign_priors(
        plot_analysis, room_brief
    )

    # ── Per-context effective weights ────────────────────────────────────
    weights = effective_weights(plot_analysis)

    # ── Score every topology kind (v0.3 § 14.1: all 4 always enter) ──────
    scored: list[_ScoredCandidate] = []
    for kind in TopologyKind:
        raw_scores = compute_raw_scores(kind, plot_analysis, room_brief)
        # base_score = weighted sum of raw scores using effective weights
        base_score = sum(raw_scores[c] * weights[c] for c in raw_scores)
        # Defensive clamp; weights sum to 1.0 and raw in [0,1] ⇒ base in [0,1]
        # mathematically. Test invariant (v0.3 § 14.7) protects this.
        base_score = max(0.0, min(1.0, base_score))

        prior_value = priors.for_kind(kind)
        # v0.5 § 14.1 additive blend — final = 0.85 × base + 0.15 × prior
        score = _BASE_BLEND_WEIGHT * base_score + _PRIOR_BLEND_WEIGHT * prior_value
        score = max(0.0, min(1.0, score))

        score_breakdown = _build_score_breakdown(raw_scores, weights, prior_value)

        scored.append(_ScoredCandidate(
            kind=kind,
            raw_scores=raw_scores,
            weights=weights,
            base_score=base_score,
            prior_value=prior_value,
            score=score,
            score_breakdown=score_breakdown,
        ))

    # ── v0.6 § 14.4 (#8): sort by (-score, -corridor_overhead.raw) ──────
    # Higher corridor_overhead raw = LESS overhead (it's a fitness score)
    # → simpler topology wins ties.
    scored.sort(
        key=lambda c: (
            -c.score,
            -c.score_breakdown["corridor_overhead"].raw,
        )
    )

    # ── Selection (v0.3 § 14.4 Q7 reversal) ──────────────────────────────
    if not scored:                                   # pragma: no cover (4 always scored)
        raise RuntimeError("no candidates produced — decision-table bug")

    top = scored[0]

    # v0.6 § 14.6 — uniform per candidate; top can be low-confidence
    top_low_confidence = top.score < LOW_CONFIDENCE_THRESHOLD

    # v0.9 § 14.5 (#10) — score_margin: per-candidate gap to NEXT-RANKED.
    # Computed AFTER sort, so each candidate's margin uses its own +1 neighbour.
    # Last candidate's margin is its score (margin to 0.0).
    # Compute margins for every position; we'll only use selected ones.
    def _margin(idx: int) -> float:
        if idx + 1 < len(scored):
            return max(0.0, scored[idx].score - scored[idx + 1].score)
        return scored[idx].score

    selected: list[TopologyCandidate] = []
    selected.append(_make_candidate(
        sc=top,
        plot_analysis=plot_analysis,
        branch_label=branch_label,
        branch_weights=branch_weights,
        raw_branch_total=raw_branch_total,
        low_confidence=top_low_confidence,
        score_margin=_margin(0),
    ))

    # 2nd candidate: relative-delta + admission threshold
    if (
        len(scored) >= 2
        and scored[1].score >= MIN_CANDIDATE_ADMISSION_THRESHOLD
        and top.score > 0
        and (top.score - scored[1].score) / top.score <= _TIE_RELATIVE_DELTA_2ND
    ):
        selected.append(_make_candidate(
            sc=scored[1],
            plot_analysis=plot_analysis,
            branch_label=branch_label,
            branch_weights=branch_weights,
            raw_branch_total=raw_branch_total,
            low_confidence=False,
            score_margin=_margin(1),
        ))
        # 3rd: only if 2nd was admitted
        if (
            len(scored) >= 3
            and scored[2].score >= MIN_CANDIDATE_ADMISSION_THRESHOLD
            and (top.score - scored[2].score) / top.score <= _TIE_RELATIVE_DELTA_3RD
        ):
            selected.append(_make_candidate(
                sc=scored[2],
                plot_analysis=plot_analysis,
                branch_label=branch_label,
                branch_weights=branch_weights,
                raw_branch_total=raw_branch_total,
                low_confidence=False,
                score_margin=_margin(2),
            ))

    return tuple(selected)


__all__ = [
    "select_topology",
    "LOW_CONFIDENCE_THRESHOLD",
    "MIN_CANDIDATE_ADMISSION_THRESHOLD",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/components/c05/__init__.py
# C5: package re-exports
# ══════════════════════════════════════════════════════════════════════════════

"""
BuildemUp† — Component 5 (Topology Selector) package init.

Per C5 SPEC v0.9 LOCKED § 5.

Public entry point: ``select_topology(plot_analysis, room_brief)``.
Re-exports schema names that downstream components (C6+) will consume.

No KB consistency check (no KB at C5).

†= placeholder name marker.
"""
from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    CorridorSketch,
    ScoreBreakdownEntry,
    TopologyCandidate,
    TopologyKind,
    TopologyPriors,
    TopologyProvenance,
    ZoneBand,
)
from buildemup.components.c05.select import (
    LOW_CONFIDENCE_THRESHOLD,
    MIN_CANDIDATE_ADMISSION_THRESHOLD,
    select_topology,
)


__all__ = [
    "select_topology",
    "LOW_CONFIDENCE_THRESHOLD",
    "MIN_CANDIDATE_ADMISSION_THRESHOLD",
    "TopologyKind",
    "ZoneBand",
    "CorridorPosition",
    "ConnectivityType",
    "CorridorSketch",
    "ScoreBreakdownEntry",
    "TopologyProvenance",
    "TopologyCandidate",
    "TopologyPriors",
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE: buildemup/tests/validation/_c5_fixtures.py
# TEST FIXTURES: _c5_fixtures
# ══════════════════════════════════════════════════════════════════════════════

"""C5 test helpers — FloorRoomBrief builders + PlotAnalysis wrapper.

Per Q3 design (S30 — adopted as proposed).

C5 tests need:
  - A FloorRoomBrief (NEW domain dataclass per C5 SPEC § 2)
  - A PlotAnalysis (output of c04.derive)

This file builds both. Plot fixtures themselves are RE-EXPORTED from
_c4_fixtures.py — no duplication.
"""
from __future__ import annotations

import time

from buildemup.components.c04 import derive
from buildemup.components.c04.schema import PlotAnalysis
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    make_brief,
    mumbai_30x40,
    pune_30x40,
)


__all__ = [
    # Plot fixtures (re-exported from C4)
    "chennai_30x40", "bangalore_40x60", "delhi_60x90",
    "mumbai_30x40", "pune_30x40", "hyderabad_30x40",
    # PlotAnalysis builder
    "make_plot_analysis",
    # FloorRoomBrief builders
    "small_brief", "medium_brief", "large_brief", "make_floor_brief",
    # Stability test baselines
    "baseline_test_plot", "baseline_test_brief",
]


# ─── PlotAnalysis builder ────────────────────────────────────────────────


def make_plot_analysis(
    plot, *, trace_id: str = "trace-c5-test", now: float | None = None
) -> PlotAnalysis:
    """Build a PlotAnalysis by calling c04.derive() on a plot fixture.

    Used by C5 tests instead of constructing PlotAnalysis directly — keeps
    C5 tests downstream of the actual C4 contract.
    """
    if now is None:
        now = time.time()
    brief_stub = make_brief(plot, trace_id=trace_id)
    return derive(brief_stub, now=now)


# ─── FloorRoomBrief builders ─────────────────────────────────────────────


def small_brief() -> FloorRoomBrief:
    """1-bedroom ground-floor brief. Pairs with chennai_30x40 / mumbai_30x40."""
    return FloorRoomBrief(
        bedroom_count=1, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )


def medium_brief() -> FloorRoomBrief:
    """3-bedroom ground-floor brief. Pairs with bangalore_40x60."""
    return FloorRoomBrief(
        bedroom_count=3, bathroom_count=2,
        has_kitchen=True, has_living=True,
        has_pooja=True, has_utility=True,
    )


def large_brief() -> FloorRoomBrief:
    """4-bedroom ground-floor brief. Pairs with delhi_60x90 (T3)."""
    return FloorRoomBrief(
        bedroom_count=4, bathroom_count=3,
        has_kitchen=True, has_living=True,
        has_pooja=True, has_utility=True,
        other_rooms=("study",),
    )


def make_floor_brief(
    *,
    bedroom_count: int = 2,
    bathroom_count: int = 2,
    has_kitchen: bool = True,
    has_living: bool = True,
    has_pooja: bool = False,
    has_utility: bool = False,
    other_rooms: tuple[str, ...] = (),
    floor_label: str = "ground",
) -> FloorRoomBrief:
    """Generic FloorRoomBrief builder for parametrized tests."""
    return FloorRoomBrief(
        bedroom_count=bedroom_count, bathroom_count=bathroom_count,
        has_kitchen=has_kitchen, has_living=has_living,
        has_pooja=has_pooja, has_utility=has_utility,
        other_rooms=other_rooms, floor_label=floor_label,
    )


# ─── Stability test baselines (v0.8 § 14.3) ──────────────────────────────


def baseline_test_plot():
    """The fixed plot used by test_c5_stability.py perturbation tests.

    9.0 × 12.0 m, NORTH-facing, chennai. NOT exactly any of the C4 fixtures
    so perturbation ±0.1m doesn't accidentally hit a fixture boundary.

    The Plot import here is permitted: this file lives in
    buildemup.tests.validation, NOT buildemup.components.c05; the
    forbidden-import test (test_c5_consumes_plot_analysis.py) scans
    only the c05 package via pkgutil.walk_packages.
    """
    from buildemup.domain.envelope import PlotOrientation
    from buildemup.domain.plot import Plot
    return Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )


def baseline_test_brief() -> FloorRoomBrief:
    """The fixed brief used by test_c5_stability.py perturbation tests.

    3-bedroom is in the sweet spot for STRIP, CENTRAL_SPINE, AND L_SHAPE,
    so the topology choice is decided by plot dims + scoring, not by the
    bedroom-fit factor alone.
    """
    return FloorRoomBrief(
        bedroom_count=3, bathroom_count=2,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )

