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
