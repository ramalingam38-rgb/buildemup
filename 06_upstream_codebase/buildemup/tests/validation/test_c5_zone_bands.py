"""Validation tests for C5 zone_bands + corridor_sketch builders.

Per C5 SPEC v0.9 LOCKED § 4.3 + § 14.6.
"""
from __future__ import annotations

import pytest

from buildemup.components.c05.schema import (
    ConnectivityType,
    CorridorPosition,
    TopologyKind,
    ZoneBand,
)
from buildemup.components.c05.zone_bands import (
    build_corridor_sketch,
    default_zone_bands,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    delhi_60x90,
    make_plot_analysis,
)


# ─── default_zone_bands per topology ──────────────────────────────────────


def test_strip_required_bands_present():
    bands = default_zone_bands(TopologyKind.STRIP, PlotOrientation.NORTH)
    assert set(bands.keys()) >= {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                  ZoneBand.CIRCULATION, ZoneBand.PRIVATE}


def test_central_spine_required_bands_present():
    bands = default_zone_bands(TopologyKind.CENTRAL_SPINE, PlotOrientation.EAST)
    assert set(bands.keys()) >= {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                  ZoneBand.CIRCULATION, ZoneBand.PRIVATE}


def test_l_shape_required_bands_present():
    """v0.6 § 14.5: L_SHAPE requires {PUBLIC, PRIVATE, CIRCULATION}."""
    bands = default_zone_bands(TopologyKind.L_SHAPE, PlotOrientation.NORTH)
    assert set(bands.keys()) >= {ZoneBand.PUBLIC, ZoneBand.PRIVATE,
                                  ZoneBand.CIRCULATION}


def test_courtyard_required_bands_present():
    bands = default_zone_bands(TopologyKind.COURTYARD, PlotOrientation.SOUTH)
    assert set(bands.keys()) >= {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                  ZoneBand.PRIVATE, ZoneBand.CIRCULATION}


def test_strip_distinct_compass_directions():
    """Non-COURTYARD: distinct compass directions per v0.6 § 14.5."""
    bands = default_zone_bands(TopologyKind.STRIP, PlotOrientation.NORTH)
    directions = list(bands.values())
    assert len(directions) == len(set(directions))


def test_central_spine_distinct_compass_directions():
    bands = default_zone_bands(TopologyKind.CENTRAL_SPINE, PlotOrientation.EAST)
    directions = list(bands.values())
    assert len(directions) == len(set(directions))


def test_l_shape_distinct_compass_directions():
    bands = default_zone_bands(TopologyKind.L_SHAPE, PlotOrientation.NORTH)
    directions = list(bands.values())
    assert len(directions) == len(set(directions))


def test_zone_bands_rotate_with_facing():
    """Per v0.2 § 4.3: zone-band positions are RELATIVE to plot.facing."""
    bands_n = default_zone_bands(TopologyKind.STRIP, PlotOrientation.NORTH)
    bands_e = default_zone_bands(TopologyKind.STRIP, PlotOrientation.EAST)
    # PUBLIC is always at "front" — rotates with facing
    assert bands_n[ZoneBand.PUBLIC] == PlotOrientation.NORTH
    assert bands_e[ZoneBand.PUBLIC] == PlotOrientation.EAST


# ─── CorridorSketch builder per topology ──────────────────────────────────


def test_strip_corridor_position():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.STRIP, pa)
    # STRIP allows NONE or CENTRAL per validator
    assert sketch.position in (CorridorPosition.NONE, CorridorPosition.CENTRAL)


def test_central_spine_corridor_central():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.CENTRAL_SPINE, pa)
    assert sketch.position == CorridorPosition.CENTRAL


def test_l_shape_corridor_l_bent():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.L_SHAPE, pa)
    assert sketch.position == CorridorPosition.L_BENT


def test_courtyard_corridor_perimeter():
    pa = make_plot_analysis(delhi_60x90())
    sketch = build_corridor_sketch(TopologyKind.COURTYARD, pa)
    assert sketch.position == CorridorPosition.PERIMETER


# ─── ConnectivityType per topology (v0.3 § 14.6 D8) ───────────────────────


def test_strip_connectivity_linear():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.STRIP, pa)
    assert sketch.connectivity_type == ConnectivityType.LINEAR


def test_central_spine_connectivity_linear():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.CENTRAL_SPINE, pa)
    assert sketch.connectivity_type == ConnectivityType.LINEAR


def test_l_shape_connectivity_branched():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.L_SHAPE, pa)
    assert sketch.connectivity_type == ConnectivityType.BRANCHED


def test_courtyard_connectivity_loop():
    pa = make_plot_analysis(delhi_60x90())
    sketch = build_corridor_sketch(TopologyKind.COURTYARD, pa)
    assert sketch.connectivity_type == ConnectivityType.LOOP


# ─── approx_length_m formulas (v0.3 § 14.6 D8) ────────────────────────────


def test_strip_approx_length_formula():
    """STRIP: depth_m × 0.85."""
    pa = make_plot_analysis(bangalore_40x60())     # depth = 18.288
    sketch = build_corridor_sketch(TopologyKind.STRIP, pa)
    assert sketch.approx_length_m == pytest.approx(18.288 * 0.85, abs=1e-6)


def test_central_spine_approx_length_formula():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.CENTRAL_SPINE, pa)
    assert sketch.approx_length_m == pytest.approx(18.288 * 0.85, abs=1e-6)


def test_l_shape_approx_length_formula():
    """L_SHAPE: (width + depth) × 0.5."""
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.L_SHAPE, pa)
    assert sketch.approx_length_m == pytest.approx(
        (12.192 + 18.288) * 0.5, abs=1e-6
    )


def test_courtyard_approx_length_formula():
    """COURTYARD: 2 × (width + depth) × 0.4."""
    pa = make_plot_analysis(delhi_60x90())         # 18.288 × 27.432
    sketch = build_corridor_sketch(TopologyKind.COURTYARD, pa)
    expected = 2.0 * (18.288 + 27.432) * 0.4
    assert sketch.approx_length_m == pytest.approx(expected, abs=1e-6)


# ─── runs_along (Q2 design) ───────────────────────────────────────────────


def test_runs_along_strip_is_plot_facing():
    pa = make_plot_analysis(bangalore_40x60())     # facing EAST
    sketch = build_corridor_sketch(TopologyKind.STRIP, pa)
    assert sketch.runs_along == pa.plot.facing


def test_runs_along_courtyard_is_plot_facing_nominal():
    """Q2 design (S30): COURTYARD has LOOP connectivity; runs_along is the
    NOMINAL front-axis reference per Option C wording."""
    pa = make_plot_analysis(delhi_60x90())         # facing SOUTH
    sketch = build_corridor_sketch(TopologyKind.COURTYARD, pa)
    assert sketch.connectivity_type == ConnectivityType.LOOP
    assert sketch.runs_along == pa.plot.facing


# ─── nominal_width_m ─────────────────────────────────────────────────────


def test_nominal_corridor_width_set():
    pa = make_plot_analysis(bangalore_40x60())
    sketch = build_corridor_sketch(TopologyKind.STRIP, pa)
    # NBC residential corridor minimum ~1.2m (refined by C8)
    assert 0.9 <= sketch.nominal_width_m <= 1.5
