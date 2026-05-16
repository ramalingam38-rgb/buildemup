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
        # NEW v0.6 (Q1-B / § 14.19). Per § 14.21 (v0.7 consolidation):
        # cardinal-only is an EXTERNAL CONTRACT constraint, NOT a scoring
        # limitation. The internal Vastu KB still consumes all 8 directions
        # via weighted-avg aggregation (vastu_kb.vastu_score_4dir). When
        # B-107 lands, this guard loosens; the internal 8-dir machinery
        # stays as-is.
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
