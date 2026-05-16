"""C6 schema tests — dataclass __post_init__ invariants, constants, enum.

Per C6 SPEC v0.7 LOCKED § 3 + § 4.6 + § 13. Reconstructed at S33 per B-127.

Coverage:
  - Constants: SIGNAL_DOMINANCE_THRESHOLD, SWAP_HYSTERESIS_THRESHOLD,
    MAX_PERMUTATION_COUNT, MIN_DENOM, CARDINAL_FACINGS.
  - Enum: FunctionRole (6 members; CIRCULATION intentionally absent).
  - SignalBreakdown: range checks, type checks.
  - DirectionPriorityScore: function_scores keyset, range checks.
  - OrientationProvenance: weights keysets, dominant/dominance contract,
    type checks.
  - OrientationPriority: cardinal-only direction_priorities (validator
    invariant 1), refined_zone_bands cardinal-only (validator invariant 9
    NEW v0.6), confidence range, score_margin >= 0.
  - OrientedCandidate: type checks.
"""
from __future__ import annotations

import pytest

from buildemup.components.c06 import (
    CARDINAL_FACINGS,
    DirectionPriorityScore,
    FunctionRole,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    OrientationPriority,
    OrientationProvenance,
    OrientedCandidate,
    SIGNAL_DOMINANCE_THRESHOLD,
    SWAP_HYSTERESIS_THRESHOLD,
    SignalBreakdown,
)
from buildemup.components.c05.schema import ZoneBand
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c6_fixtures import first_candidate


# ─── Constants ────────────────────────────────────────────────────────────


def test_signal_dominance_threshold_value():
    assert SIGNAL_DOMINANCE_THRESHOLD == 0.45


def test_swap_hysteresis_threshold_value():
    assert SWAP_HYSTERESIS_THRESHOLD == 0.10


def test_max_permutation_count_value():
    """Cap = 4^4 = 256 to cover COURTYARD (LOOP) topology."""
    assert MAX_PERMUTATION_COUNT == 256


def test_min_denom_value():
    assert MIN_DENOM == 0.1


def test_cardinal_facings_set():
    """CARDINAL_FACINGS is exactly {N, E, S, W}."""
    expected = {
        PlotOrientation.NORTH, PlotOrientation.EAST,
        PlotOrientation.SOUTH, PlotOrientation.WEST,
    }
    assert set(CARDINAL_FACINGS) == expected


def test_cardinal_facings_is_frozenset():
    """Defensive: CARDINAL_FACINGS is a frozenset (immutable)."""
    assert isinstance(CARDINAL_FACINGS, frozenset)


def test_cardinal_facings_excludes_intercardinals():
    """No NE / SE / SW / NW members."""
    assert PlotOrientation.NORTHEAST not in CARDINAL_FACINGS
    assert PlotOrientation.SOUTHEAST not in CARDINAL_FACINGS
    assert PlotOrientation.SOUTHWEST not in CARDINAL_FACINGS
    assert PlotOrientation.NORTHWEST not in CARDINAL_FACINGS


# ─── FunctionRole enum ────────────────────────────────────────────────────


def test_function_role_has_six_members():
    """Per § 14.20: CIRCULATION is intentionally NOT a FunctionRole."""
    assert len(list(FunctionRole)) == 6


def test_function_role_members():
    expected_values = {
        "living", "bedroom", "kitchen", "pooja", "wet_area", "utility",
    }
    actual_values = {m.value for m in FunctionRole}
    assert actual_values == expected_values


def test_function_role_excludes_circulation():
    """CIRCULATION is a ZoneBand with private scoring; not a FunctionRole."""
    assert "circulation" not in {m.value for m in FunctionRole}


# ─── SignalBreakdown ──────────────────────────────────────────────────────


def test_signal_breakdown_happy_path():
    sb = SignalBreakdown(
        sun_score=0.5, wind_score=0.5, road_score=0.5, vastu_score=0.5,
    )
    assert sb.sun_score == 0.5


def test_signal_breakdown_accepts_zero():
    sb = SignalBreakdown(sun_score=0.0, wind_score=0.0, road_score=0.0, vastu_score=0.0)
    assert sb.vastu_score == 0.0


def test_signal_breakdown_accepts_one():
    sb = SignalBreakdown(sun_score=1.0, wind_score=1.0, road_score=1.0, vastu_score=1.0)
    assert sb.sun_score == 1.0


def test_signal_breakdown_rejects_negative_sun():
    with pytest.raises(ValueError, match=r"sun_score.*\[0, 1\]"):
        SignalBreakdown(sun_score=-0.1, wind_score=0.0, road_score=0.0, vastu_score=0.0)


def test_signal_breakdown_rejects_above_one_wind():
    with pytest.raises(ValueError, match=r"wind_score.*\[0, 1\]"):
        SignalBreakdown(sun_score=0.0, wind_score=1.1, road_score=0.0, vastu_score=0.0)


def test_signal_breakdown_rejects_non_numeric():
    with pytest.raises(TypeError, match=r"road_score must be numeric"):
        SignalBreakdown(
            sun_score=0.0, wind_score=0.0, road_score="bad", vastu_score=0.0,  # type: ignore
        )


# ─── DirectionPriorityScore ───────────────────────────────────────────────


def _full_function_scores(value: float = 0.5) -> dict:
    """Helper: a dict covering all 6 FunctionRole members."""
    return {f: value for f in FunctionRole}


def _signal_breakdown_default() -> SignalBreakdown:
    return SignalBreakdown(sun_score=0.5, wind_score=0.5, road_score=0.5, vastu_score=0.5)


def test_dps_happy_path():
    dps = DirectionPriorityScore(
        function_scores=_full_function_scores(),
        signal_breakdown=_signal_breakdown_default(),
    )
    assert dps.function_scores[FunctionRole.LIVING] == 0.5


def test_dps_rejects_missing_function_role():
    incomplete = {f: 0.5 for f in FunctionRole if f != FunctionRole.LIVING}
    with pytest.raises(ValueError, match=r"function_scores must cover.*living"):
        DirectionPriorityScore(
            function_scores=incomplete,
            signal_breakdown=_signal_breakdown_default(),
        )


def test_dps_rejects_extra_key():
    extra = _full_function_scores()
    extra["unknown_role"] = 0.3  # type: ignore
    with pytest.raises(ValueError, match=r"function_scores must cover.*"):
        DirectionPriorityScore(
            function_scores=extra,
            signal_breakdown=_signal_breakdown_default(),
        )


def test_dps_rejects_out_of_range_value():
    bad = _full_function_scores()
    bad[FunctionRole.LIVING] = 1.5
    with pytest.raises(ValueError, match=r"function_scores"):
        DirectionPriorityScore(
            function_scores=bad,
            signal_breakdown=_signal_breakdown_default(),
        )


def test_dps_rejects_non_mapping():
    with pytest.raises(TypeError, match=r"function_scores must be a Mapping"):
        DirectionPriorityScore(
            function_scores=[(f, 0.5) for f in FunctionRole],  # type: ignore
            signal_breakdown=_signal_breakdown_default(),
        )


def test_dps_rejects_non_numeric_value():
    bad = _full_function_scores()
    bad[FunctionRole.KITCHEN] = "bad"  # type: ignore
    with pytest.raises(TypeError, match=r"kitchen.*numeric"):
        DirectionPriorityScore(
            function_scores=bad,
            signal_breakdown=_signal_breakdown_default(),
        )


# ─── OrientationProvenance ────────────────────────────────────────────────


def _provenance_kwargs(**overrides) -> dict:
    base = dict(
        derived_at=1234.0,
        plot_analysis_trace_id="trace-test",
        vastu_tier=VastuTier.OFF,
        weights_applied={"sun": 0.6, "wind": 0.4, "vastu": 0.0},
        weights_raw={"sun": 1.0, "wind": 0.6, "vastu": 0.0},
        signal_dominance=0.625,  # >= 0.45 → must have non-None dominant_signal
        dominant_signal="sun",
        climate_profile="composite",
        rule_trace=("test",),
        permutation_search_size=5,
        chosen_over_seed=False,
        seed_distance=0,
    )
    base.update(overrides)
    return base


def test_provenance_happy_path():
    p = OrientationProvenance(**_provenance_kwargs())
    assert p.dominant_signal == "sun"


def test_provenance_dominance_below_threshold_requires_none():
    """Validator invariant 8: dominant_signal == None iff dominance < threshold."""
    with pytest.raises(ValueError, match=r"dominant_signal must be None iff"):
        OrientationProvenance(**_provenance_kwargs(
            signal_dominance=0.30,           # below 0.45
            dominant_signal="sun",           # but says non-None — invariant violation
        ))


def test_provenance_dominance_above_threshold_requires_named():
    """If dominance >= threshold, must name a signal."""
    with pytest.raises(ValueError, match=r"dominant_signal must be None iff"):
        OrientationProvenance(**_provenance_kwargs(
            signal_dominance=0.70,
            dominant_signal=None,           # invariant violation
        ))


def test_provenance_balanced_at_threshold():
    """Boundary: dominance exactly at threshold — must have dominant_signal."""
    p = OrientationProvenance(**_provenance_kwargs(
        signal_dominance=0.45,
        dominant_signal="sun",
    ))
    assert p.signal_dominance == 0.45


def test_provenance_rejects_non_vastu_tier():
    with pytest.raises(TypeError, match=r"vastu_tier must be VastuTier"):
        OrientationProvenance(**_provenance_kwargs(vastu_tier="off"))  # type: ignore


def test_provenance_rejects_bad_weights_keyset():
    with pytest.raises(ValueError, match=r"weights_applied keys must be exactly"):
        OrientationProvenance(**_provenance_kwargs(
            weights_applied={"sun": 1.0, "wind": 0.0},   # missing 'vastu'
        ))


def test_provenance_rejects_dominance_out_of_range():
    with pytest.raises(ValueError, match=r"signal_dominance.*\[0, 1\]"):
        OrientationProvenance(**_provenance_kwargs(
            signal_dominance=1.5,
            dominant_signal="sun",
        ))


def test_provenance_rejects_unknown_dominant_signal():
    with pytest.raises(ValueError, match=r"dominant_signal must be in"):
        OrientationProvenance(**_provenance_kwargs(
            signal_dominance=0.70,
            dominant_signal="unknown",
        ))


def test_provenance_rejects_non_tuple_rule_trace():
    with pytest.raises(TypeError, match=r"rule_trace must be a tuple"):
        OrientationProvenance(**_provenance_kwargs(rule_trace=["x"]))  # type: ignore


def test_provenance_rejects_negative_permutation_size():
    with pytest.raises(ValueError, match=r"permutation_search_size must be >= 0"):
        OrientationProvenance(**_provenance_kwargs(permutation_search_size=-1))


def test_provenance_rejects_negative_seed_distance():
    with pytest.raises(ValueError, match=r"seed_distance must be >= 0"):
        OrientationProvenance(**_provenance_kwargs(seed_distance=-1))


# ─── OrientationPriority ──────────────────────────────────────────────────


def _make_dps_for_dir() -> DirectionPriorityScore:
    return DirectionPriorityScore(
        function_scores=_full_function_scores(),
        signal_breakdown=_signal_breakdown_default(),
    )


def _full_direction_priorities() -> dict:
    """Helper: a dict covering all 4 cardinals."""
    return {d: _make_dps_for_dir() for d in CARDINAL_FACINGS}


def _refined_zone_bands_default() -> dict:
    return {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.WEST,
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.CIRCULATION: PlotOrientation.EAST,
    }


def _provenance_default() -> OrientationProvenance:
    return OrientationProvenance(**_provenance_kwargs())


def test_orientation_priority_happy_path():
    op = OrientationPriority(
        direction_priorities=_full_direction_priorities(),
        refined_zone_bands=_refined_zone_bands_default(),
        priority_confidence=0.7,
        score_margin=0.2,
        provenance=_provenance_default(),
    )
    assert op.priority_confidence == 0.7


def test_orientation_priority_invariant_1_rejects_intercardinal_in_priorities():
    """Validator invariant 1: direction_priorities covers exactly cardinals."""
    bad = {d: _make_dps_for_dir() for d in CARDINAL_FACINGS}
    bad[PlotOrientation.NORTHEAST] = _make_dps_for_dir()  # extra intercardinal
    with pytest.raises(ValueError, match=r"direction_priorities must cover exactly"):
        OrientationPriority(
            direction_priorities=bad,
            refined_zone_bands=_refined_zone_bands_default(),
            priority_confidence=0.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


def test_orientation_priority_invariant_1_rejects_missing_cardinal():
    bad = {d: _make_dps_for_dir() for d in CARDINAL_FACINGS if d != PlotOrientation.WEST}
    with pytest.raises(ValueError, match=r"direction_priorities must cover exactly"):
        OrientationPriority(
            direction_priorities=bad,
            refined_zone_bands=_refined_zone_bands_default(),
            priority_confidence=0.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


def test_orientation_priority_invariant_9_rejects_intercardinal_in_refined_bands():
    """Validator invariant 9 (NEW v0.6): refined_zone_bands values all cardinal."""
    bad_bands = dict(_refined_zone_bands_default())
    bad_bands[ZoneBand.PUBLIC] = PlotOrientation.NORTHEAST
    with pytest.raises(ValueError, match=r"refined_zone_bands.*cardinal PlotOrientation"):
        OrientationPriority(
            direction_priorities=_full_direction_priorities(),
            refined_zone_bands=bad_bands,
            priority_confidence=0.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


def test_orientation_priority_rejects_negative_score_margin():
    with pytest.raises(ValueError, match=r"score_margin must be >= 0"):
        OrientationPriority(
            direction_priorities=_full_direction_priorities(),
            refined_zone_bands=_refined_zone_bands_default(),
            priority_confidence=0.5,
            score_margin=-0.01,
            provenance=_provenance_default(),
        )


def test_orientation_priority_rejects_confidence_out_of_range():
    with pytest.raises(ValueError, match=r"priority_confidence.*\[0, 1\]"):
        OrientationPriority(
            direction_priorities=_full_direction_priorities(),
            refined_zone_bands=_refined_zone_bands_default(),
            priority_confidence=1.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


def test_orientation_priority_rejects_non_dps_value():
    bad = {d: "not_a_dps" for d in CARDINAL_FACINGS}
    with pytest.raises(TypeError, match=r"direction_priorities.*DirectionPriorityScore"):
        OrientationPriority(
            direction_priorities=bad,  # type: ignore
            refined_zone_bands=_refined_zone_bands_default(),
            priority_confidence=0.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


def test_orientation_priority_rejects_non_zone_band_key_in_refined_bands():
    bad_bands = {"public": PlotOrientation.NORTH}
    with pytest.raises(TypeError, match=r"refined_zone_bands key must be ZoneBand"):
        OrientationPriority(
            direction_priorities=_full_direction_priorities(),
            refined_zone_bands=bad_bands,  # type: ignore
            priority_confidence=0.5,
            score_margin=0.1,
            provenance=_provenance_default(),
        )


# ─── OrientedCandidate ────────────────────────────────────────────────────


def test_oriented_candidate_happy_path():
    """Build via the real C5 → C6 pipeline; just verify type-paired construction."""
    from buildemup.components.c06 import prioritize_orientation
    from buildemup.tests.validation._c6_fixtures import (
        bangalore_40x60, make_plot_analysis, medium_brief,
    )
    from buildemup.components.c05 import select_topology

    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    assert isinstance(out[0], OrientedCandidate)


def test_oriented_candidate_rejects_non_topology_candidate():
    """Schema-level validation."""
    op = OrientationPriority(
        direction_priorities=_full_direction_priorities(),
        refined_zone_bands=_refined_zone_bands_default(),
        priority_confidence=0.5,
        score_margin=0.1,
        provenance=_provenance_default(),
    )
    with pytest.raises(TypeError, match=r"topology_candidate must be TopologyCandidate"):
        OrientedCandidate(topology_candidate="not_a_candidate", orientation=op)  # type: ignore


def test_oriented_candidate_rejects_non_orientation_priority():
    cand = first_candidate()
    with pytest.raises(TypeError, match=r"orientation must be OrientationPriority"):
        OrientedCandidate(topology_candidate=cand, orientation="bad")  # type: ignore


def test_oriented_candidate_is_frozen():
    """Dataclass is frozen — assignment raises."""
    from buildemup.components.c06 import prioritize_orientation
    from buildemup.tests.validation._c6_fixtures import (
        bangalore_40x60, make_plot_analysis, medium_brief,
    )
    from buildemup.components.c05 import select_topology

    plot = bangalore_40x60()
    pa = make_plot_analysis(plot)
    cands = select_topology(pa, medium_brief())
    out = prioritize_orientation(cands, pa, VastuTier.OFF)
    with pytest.raises(Exception):  # FrozenInstanceError or similar
        out[0].topology_candidate = cands[0]  # type: ignore
