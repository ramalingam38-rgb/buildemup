"""Tier-1 unit tests for C4 (Plot Analysis) — main behavioural surface.

Per SPEC v0.5 LOCKED § 7.
"""
from __future__ import annotations

import time

import pytest

from buildemup.components.c04 import derive
from buildemup.components.c04.schema import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    ClimateZone,
    ConfidenceLevel,
    PlotShape,
    PlotTier,
    RoadWidthClass,
    compute_plot_facing_sides,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, PlotType, SharedSide, SoilType

from buildemup.tests.validation._c4_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    hyderabad_30x40,
    make_brief,
    mumbai_30x40,
    pune_30x40,
)


# ─── Tier classification ─────────────────────────────────────────────────

def test_tier_t1_compact_chennai_30x40():
    """30×40ft (≈1200 sqft) is T1_COMPACT."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.tier == PlotTier.T1_COMPACT
    assert 1190.0 < pa.area_sqft < 1210.0


def test_tier_t2_standard_bangalore_40x60():
    """Textbook 40×60 ft (exactly 2400 sqft via sqm-space comparison) is T2_STANDARD."""
    pa = derive(make_brief(bangalore_40x60()), now=1.0)
    assert pa.tier == PlotTier.T2_STANDARD
    # Display sqft will read ~2399.998 (from 10.7639 conversion); tier is correct.
    assert 2399.0 < pa.area_sqft < 2401.0


def test_tier_boundary_at_2400_sqft_lands_in_t2():
    """v0.6 (walk #1): 40×60 ft = 12.192×18.288 m exactly maps to 2400 sqft.

    Sqm-space comparison must classify this as T2, not T1. v0.5 sqft-space
    comparison misclassified due to the 10.7639 rounding factor.
    """
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.tier == PlotTier.T2_STANDARD, (
        f"40×60 ft (textbook 2400 sqft) must be T2; got {pa.tier}. "
        f"area_sqm={pa.area_sqm}, area_sqft_display={pa.area_sqft}"
    )


def test_area_sqft_display_matches_textbook_at_40x60ft_boundary():
    """v0.9 (walk #7): area_sqft display must equal the textbook 2400.0 at the
    boundary, not 2399.998. Achieved by using the EXACT inverse of SQM_PER_SQFT
    (1 / 0.09290304 = 10.76391041670972...) rather than the rounded 10.7639.

    v1.0 (walk D1): tolerance comparison instead of exact equality. Per
    web-research (Bruce Dawson "Floating-Point Determinism", IEEE 754 cross-
    platform behavior), float exact-equality is fragile across compiler
    optimization paths and library variants even when IEEE 754 strictness
    holds. 1e-9 tolerance is ~10 orders of magnitude tighter than any
    plausible drift on a 64-bit double while remaining platform-robust.
    """
    plot = Plot(
        width_m=12.192, depth_m=18.288, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert abs(pa.area_sqft - 2400.0) < 1e-9, (
        f"area_sqft display drifted from textbook 2400.0 (got {pa.area_sqft}) "
        f"— v0.9 walk #7 fix requires use of exact 1/SQM_PER_SQFT inverse."
    )


def test_tier_t3_large_delhi_60x90():
    """60×90ft (≈5400 sqft) is T3_LARGE."""
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    assert pa.tier == PlotTier.T3_LARGE
    assert 5390.0 < pa.area_sqft < 5410.0


# ─── Climate zones (5 covered, 2 unmapped in v1) ─────────────────────────

def test_climate_zone_chennai_is_warm_humid():
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.WARM_HUMID


def test_climate_zone_bangalore_is_temperate():
    pa = derive(make_brief(bangalore_40x60()), now=1.0)
    assert pa.climate_zone == ClimateZone.TEMPERATE


def test_climate_zone_pune_is_temperate():
    pa = derive(make_brief(pune_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.TEMPERATE


def test_climate_zone_delhi_is_composite():
    pa = derive(make_brief(delhi_60x90()), now=1.0)
    assert pa.climate_zone == ClimateZone.COMPOSITE


def test_climate_zone_hyderabad_is_composite():
    pa = derive(make_brief(hyderabad_30x40()), now=1.0)
    assert pa.climate_zone == ClimateZone.COMPOSITE


def test_climate_zone_no_v1_city_is_cold_or_hot_dry():
    """No v1 city should map to HOT_DRY or COLD (per spec § 4.4.1)."""
    from buildemup.kb.city_geography import CITY_GEOGRAPHY
    forbidden = {ClimateZone.HOT_DRY, ClimateZone.COLD}
    for city, geo in CITY_GEOGRAPHY.items():
        assert geo.climate_zone not in forbidden, (
            f"{city} maps to {geo.climate_zone} — no v1 city should be HOT_DRY/COLD"
        )


def test_baseline_orientations_cover_all_5_zones():
    """All 5 climate zones must have a guidelines entry (incl. reserved)."""
    assert set(BASELINE_ROOM_ORIENTATION_GUIDELINES.keys()) == set(ClimateZone)
    for zone, rooms in BASELINE_ROOM_ORIENTATION_GUIDELINES.items():
        assert {"living", "kitchen", "bedroom", "bathroom"} <= set(rooms.keys())
        for room, orientations in rooms.items():
            assert len(orientations) >= 1, f"{zone}.{room} has no orientations"
            for o in orientations:
                assert isinstance(o, PlotOrientation)


# ─── Neighbour context (DETACHED / SEMI_DETACHED / CONTINUOUS / corner) ──

def test_neighbour_context_detached_4_facades():
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.EAST,
        city="chennai", road_width_m=9.0, plot_type=PlotType.DETACHED,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.raw_facade_count == 4
    assert len(pa.neighbour_context.shared_sides) == 0
    assert len(pa.neighbour_context.open_sides) == 4


def test_neighbour_context_semidetached_left_facing_north_translates_to_west():
    """N-facing plot, shared_side=LEFT translates to compass WEST."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.SEMI_DETACHED, shared_side=SharedSide.LEFT,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.shared_sides == (PlotOrientation.WEST,)
    assert pa.neighbour_context.raw_facade_count == 3
    # The 3 open sides are front (N), back (S), right (E)
    assert set(pa.neighbour_context.open_sides) == {
        PlotOrientation.NORTH, PlotOrientation.SOUTH, PlotOrientation.EAST
    }


def test_neighbour_context_continuous_2_facades():
    """CONTINUOUS plots share both side walls — only front + back open."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0, plot_type=PlotType.CONTINUOUS,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.raw_facade_count == 2
    assert set(pa.neighbour_context.open_sides) == {
        PlotOrientation.NORTH, PlotOrientation.SOUTH
    }
    assert set(pa.neighbour_context.shared_sides) == {
        PlotOrientation.WEST, PlotOrientation.EAST
    }


def test_neighbour_context_corner_plot_extra_open_side():
    """Corner CONTINUOUS plot: one shared side gets promoted to open."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    # 3 open sides (1 promoted from shared), 1 shared side remaining
    assert pa.neighbour_context.raw_facade_count == 3
    assert len(pa.neighbour_context.shared_sides) == 1


def test_compute_plot_facing_sides_for_all_8_orientations():
    """compute_plot_facing_sides returns front/back/left/right for all 8 facings."""
    expected = {
        PlotOrientation.NORTH: ("N", "S", "W", "E"),
        PlotOrientation.SOUTH: ("S", "N", "E", "W"),
        PlotOrientation.EAST:  ("E", "W", "N", "S"),
        PlotOrientation.WEST:  ("W", "E", "S", "N"),
        PlotOrientation.NORTHEAST: ("NE", "SW", "NW", "SE"),
        PlotOrientation.SOUTHEAST: ("SE", "NW", "NE", "SW"),
        PlotOrientation.SOUTHWEST: ("SW", "NE", "SE", "NW"),
        PlotOrientation.NORTHWEST: ("NW", "SE", "SW", "NE"),
    }
    for facing, (f, b, l, r) in expected.items():
        sides = compute_plot_facing_sides(facing)
        assert sides["front"].value == f, f"{facing}.front"
        assert sides["back"].value  == b, f"{facing}.back"
        assert sides["left"].value  == l, f"{facing}.left"
        assert sides["right"].value == r, f"{facing}.right"


# ─── Soil estimate ───────────────────────────────────────────────────────

def test_soil_estimate_uses_user_input_with_confidence_high():
    """If plot.soil_type_known is set, use it with HIGH confidence."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.HARD_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.HARD_ROCK
    assert pa.soil_estimate.confidence == ConfidenceLevel.HIGH
    assert pa.soil_estimate.source == "user_input"
    assert pa.soil_estimate.bearing_capacity_kpa == 1620.0


def test_soil_estimate_falls_back_to_city_default_with_confidence_medium():
    """Chennai default → MEDIUM_CLAY, MEDIUM confidence (not high-variability)."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.MEDIUM_CLAY
    assert pa.soil_estimate.confidence == ConfidenceLevel.MEDIUM
    assert pa.soil_estimate.source == "city_default"
    assert pa.soil_estimate.bearing_capacity_kpa == pytest.approx(117.7)


def test_soil_estimate_mumbai_city_default_returns_confidence_low():
    """Mumbai default → FILLED_UP (high-variability) → LOW confidence (CG-7)."""
    pa = derive(make_brief(mumbai_30x40()), now=1.0)
    assert pa.soil_estimate.soil_type == SoilType.FILLED_UP
    assert pa.soil_estimate.confidence == ConfidenceLevel.LOW
    assert pa.soil_estimate.source == "city_default"


# ─── Road width classification (universal 6/12m, per Path B) ─────────────

def test_road_width_classification_uses_universal_thresholds():
    cases = [
        (1.5, RoadWidthClass.NARROW),
        (5.99, RoadWidthClass.NARROW),
        (6.0, RoadWidthClass.STANDARD),
        (9.0, RoadWidthClass.STANDARD),
        (11.99, RoadWidthClass.STANDARD),
        (12.0, RoadWidthClass.WIDE),
        (24.0, RoadWidthClass.WIDE),
    ]
    for road_m, expected in cases:
        plot = Plot(
            width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
            city="chennai", road_width_m=road_m,
        )
        pa = derive(make_brief(plot), now=1.0)
        assert pa.road_width_classification == expected, (
            f"road {road_m}m → {pa.road_width_classification}, expected {expected}"
        )


# ─── City normalization ──────────────────────────────────────────────────

def test_city_normalization_handles_uppercase_and_whitespace():
    """Plot.__post_init__ does the normalization; C4 still tolerates it."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="  Chennai  ", road_width_m=9.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.plot.city == "chennai"
    assert pa.climate_zone == ClimateZone.WARM_HUMID


# ─── Failure modes ───────────────────────────────────────────────────────

def test_below_600_sqft_raises_value_error():
    """A 3×3m plot is ~97 sqft — should fail tier classification."""
    # Plot constructor enforces ≥ 3.0m bounds, so 3×3m is the smallest.
    plot = Plot(
        width_m=3.0, depth_m=3.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=3.0,
    )
    with pytest.raises(ValueError, match="600sqft"):
        derive(make_brief(plot), now=1.0)


def test_invalid_latitude_raises_value_error():
    """sun_path computation rejects implausible lat (defense in depth)."""
    from buildemup.components.c04.sun_path import compute_sun_path
    with pytest.raises(ValueError, match="latitude"):
        compute_sun_path(60.0)
    with pytest.raises(ValueError, match="latitude"):
        compute_sun_path(-50.0)


def test_now_zero_or_negative_raises_value_error():
    plot = chennai_30x40()
    with pytest.raises(ValueError, match=r"now"):
        derive(make_brief(plot), now=0.0)
    with pytest.raises(ValueError, match=r"now"):
        derive(make_brief(plot), now=-5.0)


def test_now_non_float_raises_type_error():
    plot = chennai_30x40()
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now="not-a-float")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now=None)           # type: ignore[arg-type]
    # bool is a numeric subclass in Python; we explicitly reject it.
    with pytest.raises(TypeError, match=r"now"):
        derive(make_brief(plot), now=True)           # type: ignore[arg-type]


def test_shape_consumer_guard_raises_for_non_rectangular():
    """Per spec § 4.2: any consumer of shape_metadata that sees a non-RECTANGULAR
    shape MUST raise NotImplementedError. v1 always returns RECTANGULAR; this
    test simulates the future consumer guard."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.shape == PlotShape.RECTANGULAR

    # Simulate a future consumer pattern that would touch shape_metadata
    # only for non-rectangular shapes — guard must raise.
    def consumer(shape: PlotShape) -> None:
        if shape != PlotShape.RECTANGULAR:
            raise NotImplementedError("v1 supports rectangular only; B-066")
    with pytest.raises(NotImplementedError, match="B-066"):
        consumer(PlotShape.L_SHAPED)
    with pytest.raises(NotImplementedError, match="B-066"):
        consumer(PlotShape.IRREGULAR)


# ─── ResolvedBrief input contract (CG-9) ─────────────────────────────────

def test_derive_reads_plot_from_revised_brief():
    """C4 reads brief.revised_brief.plot, NOT brief.plot."""
    plot = chennai_30x40()
    brief = make_brief(plot, trace_id="trace-A")
    pa = derive(brief, now=1.0)
    # Round-trip: the same Plot object must come back on the output.
    assert pa.plot is plot

    # And a malformed brief (missing revised_brief) must raise ValueError,
    # not AttributeError.
    class _NoRevised:
        pass
    with pytest.raises(ValueError, match="revised_brief"):
        derive(_NoRevised(), now=1.0)


def test_derive_reads_trace_id_from_revised_brief():
    """C4 reads brief.revised_brief.trace_id and surfaces it on PlotAnalysis."""
    plot = chennai_30x40()
    brief = make_brief(plot, trace_id="trace-XYZ-123")
    pa = derive(brief, now=1.0)
    assert pa.trace_id == "trace-XYZ-123"

    # Missing trace_id raises ValueError, not AttributeError.
    from types import SimpleNamespace
    no_trace = SimpleNamespace(plot=plot)        # no trace_id attribute
    wrap = SimpleNamespace(revised_brief=no_trace)
    with pytest.raises(ValueError, match="trace_id"):
        derive(wrap, now=1.0)


# ─── v0.6 SPEC-AMENDMENT tests ─────────────────────────────────────────────

# § 14.2 Soil provenance_note (walks #2, #7)
def test_soil_estimate_chennai_default_has_no_provenance_note():
    """Stable city defaults carry no provenance_note (None)."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.soil_estimate.provenance_note is None


def test_soil_estimate_mumbai_carries_high_variability_note():
    """Mumbai default → FILLED_UP → provenance_note breadcrumbs the variability."""
    pa = derive(make_brief(mumbai_30x40()), now=1.0)
    note = pa.soil_estimate.provenance_note
    assert note is not None
    assert "filled_up" in note
    assert "high_variability" in note
    assert "site_survey_required" in note


def test_soil_estimate_user_input_medium_rock_uses_is6403_value():
    """B-074 closed S55: MEDIUM_ROCK is a first-class kb.SoilClass with 1250 kPa
    (IS 6403 typical of 1000-1500). No approximation breadcrumb anymore."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.MEDIUM_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.confidence == ConfidenceLevel.HIGH
    assert pa.soil_estimate.bearing_capacity_kpa == 1250.0
    assert pa.soil_estimate.provenance_note is None


def test_soil_estimate_user_input_hard_rock_has_no_provenance_note():
    """Cleanly-mapped user inputs (no approximation) carry no note."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        soil_type_known=SoilType.HARD_ROCK,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.soil_estimate.provenance_note is None


# § 14.3 Wind confidence (walk #3)
def test_all_prevailing_wind_entries_carry_medium_confidence_until_b070():
    """Every per-city WindContext currently carries MEDIUM (single-station IMD)."""
    from buildemup.kb.wind_direction import PREVAILING_WIND
    for city, wc in PREVAILING_WIND.items():
        assert wc.confidence == ConfidenceLevel.MEDIUM, (
            f"{city} wind confidence is {wc.confidence}; v0.6 spec requires "
            f"MEDIUM until B-070 promotes per-city wind-rose to HIGH"
        )


def test_plot_analysis_surfaces_wind_confidence():
    """PlotAnalysis.prevailing_wind exposes the .confidence field."""
    pa = derive(make_brief(chennai_30x40()), now=1.0)
    assert pa.prevailing_wind.confidence == ConfidenceLevel.MEDIUM


# § 14.5 Corner assumption surfacing (walk #5)
def test_non_corner_carries_no_assumption():
    """Non-corner plots have corner_assumption = None."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=False,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.corner_assumption is None


def test_corner_continuous_carries_b076_assumption_breadcrumb():
    """CONTINUOUS+corner uses the v1 LEFT default → assumption surfaced."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.CONTINUOUS,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    note = pa.neighbour_context.corner_assumption
    assert note is not None
    assert "second_street" in note
    assert "LEFT" in note
    assert "b076" in note


def test_corner_semidetached_carries_no_assumption():
    """SEMI_DETACHED+corner is deterministic from shared_side → no assumption."""
    plot = Plot(
        width_m=9.0, depth_m=12.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.SEMI_DETACHED, shared_side=SharedSide.LEFT,
        corner_plot=True, second_road_width_m=6.0,
    )
    pa = derive(make_brief(plot), now=1.0)
    assert pa.neighbour_context.corner_assumption is None


# ─── v0.7 SPEC-AMENDMENT tests ──────────────────────────────────────────────

# § 14.1: centralized normalize_city + validate_city (walks #1, #4)
def test_normalize_city_handles_uppercase_and_whitespace():
    """normalize_city is the canonical lowercase/strip helper."""
    from buildemup.components.c04.climate_zone import normalize_city
    assert normalize_city("  Chennai  ") == "chennai"
    assert normalize_city("DELHI") == "delhi"
    assert normalize_city("bangalore") == "bangalore"


def test_normalize_city_rejects_non_str():
    """Type contract: city must be str."""
    from buildemup.components.c04.climate_zone import normalize_city
    with pytest.raises(TypeError, match="city must be str"):
        normalize_city(123)              # type: ignore[arg-type]
    with pytest.raises(TypeError, match="city must be str"):
        normalize_city(None)             # type: ignore[arg-type]


def test_validate_city_returns_normalized_name_for_supported():
    """validate_city normalizes and verifies membership."""
    from buildemup.components.c04.climate_zone import validate_city
    assert validate_city("Chennai") == "chennai"
    assert validate_city("  DELHI  ") == "delhi"


def test_validate_city_raises_for_unsupported():
    """Unsupported city raises ValueError with helpful message."""
    from buildemup.components.c04.climate_zone import validate_city
    with pytest.raises(ValueError, match=r"missing from CITY_GEOGRAPHY"):
        validate_city("kolkata")
    with pytest.raises(ValueError, match=r"missing from CITY_GEOGRAPHY"):
        validate_city("not-a-city")


# § 14.2: WindContext.basic_speed_ms is now a stored field (walk #2)
def test_wind_context_basic_speed_ms_is_stored_field_not_property():
    """v0.7: basic_speed_ms is a dataclass field, not a @property descriptor."""
    import inspect
    from buildemup.components.c04.schema import WindContext
    # Property descriptor would show up via getattr_static on the CLASS.
    descriptor = inspect.getattr_static(WindContext, "basic_speed_ms", None)
    assert not isinstance(descriptor, property), (
        "basic_speed_ms should be a stored dataclass field per v0.7 §14.2, "
        "not a @property descriptor."
    )
    # And it must show up in __dataclass_fields__.
    assert "basic_speed_ms" in WindContext.__dataclass_fields__


def test_wind_context_basic_speed_ms_value_matches_wind_load_kb():
    """Eager-resolved basic_speed_ms equals kb.wind_load value at module load."""
    from buildemup.kb.wind_direction import PREVAILING_WIND
    from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS
    for city, wc in PREVAILING_WIND.items():
        assert wc.basic_speed_ms == float(BASIC_WIND_SPEED_MS[city]), (
            f"{city}: basic_speed_ms ({wc.basic_speed_ms}) != "
            f"wind_load value ({BASIC_WIND_SPEED_MS[city]})"
        )


# ─── v0.8 SPEC-AMENDMENT tests ──────────────────────────────────────────────

# § 14.2: WindContext.city field removed (walk #7)
def test_wind_context_does_not_carry_city_field():
    """v0.8: city field removed; PREVAILING_WIND dict key IS the city."""
    from buildemup.components.c04.schema import WindContext
    assert "city" not in WindContext.__dataclass_fields__, (
        "WindContext.city field was removed in v0.8 walk #7 (dead metadata "
        "after v0.7 made basic_speed_ms a stored field). PREVAILING_WIND "
        "dict key IS the city."
    )


def test_prevailing_wind_keys_match_supported_cities_post_v08():
    """Post-removal: dict keys still cover every supported city."""
    from buildemup.domain.plot import SUPPORTED_CITIES
    from buildemup.kb.wind_direction import PREVAILING_WIND
    assert set(PREVAILING_WIND.keys()) == set(SUPPORTED_CITIES)


# § 14.3: Approximation notes moved from logic to KB layer (walk #8).
# v1.1 (B-074 closed S55): MEDIUM_ROCK is no longer approximated. The
# table export survives as an empty dict so the v0.8 contract still holds.
def test_approximation_notes_table_lives_in_kb_layer():
    """v0.8: APPROXIMATION_NOTES_BY_SOIL_TYPE is exported from kb/soil_city_defaults."""
    from buildemup.kb import soil_city_defaults
    assert hasattr(soil_city_defaults, "APPROXIMATION_NOTES_BY_SOIL_TYPE")
    table = soil_city_defaults.APPROXIMATION_NOTES_BY_SOIL_TYPE
    assert isinstance(table, dict)
    # B-074 removed MEDIUM_ROCK from the table; no soil types are
    # approximated as of v1.1.
    assert SoilType.MEDIUM_ROCK not in table


def test_soil_estimator_no_longer_carries_local_approximation_table():
    """v0.8: soil_estimator must NOT define a local _APPROXIMATED_USER_INPUT_NOTES
    (the table moved to the KB layer; carrying both invites drift)."""
    from buildemup.components.c04 import soil_estimator
    assert not hasattr(soil_estimator, "_APPROXIMATED_USER_INPUT_NOTES"), (
        "Local _APPROXIMATED_USER_INPUT_NOTES table should have moved to "
        "kb/soil_city_defaults.py in v0.8 walk #8. Found in soil_estimator.py."
    )
