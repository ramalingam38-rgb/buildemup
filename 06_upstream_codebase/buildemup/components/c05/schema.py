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
