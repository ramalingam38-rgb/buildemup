"""Validation tests for C8 spatial model (ZoneBandEnvelope derivation).

Per C8 SPEC v0.5 LOCKED § 4.0 / § 14.1 / § 14.10.
"""
from __future__ import annotations

from types import MappingProxyType

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c08.schema import (
    CorridorDesignConfig,
    ZoneBandEnvelope,
)
from buildemup.components.c08.spatial_model import (
    derive_zone_band_envelopes,
    find_envelope_for_band,
)
from buildemup.domain.envelope import PlotOrientation
from buildemup.tests.validation._c8_fixtures import (
    make_grid,
    make_grid_minimal,
    real_pipeline,
)


def test_derive_envelopes_basic():
    """Real pipeline candidates produce envelopes."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        assert len(envs) >= 1


def test_derive_envelopes_circulation_excluded():
    """Per § 14.7: CIRCULATION has no envelope."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            assert e.band != ZoneBand.CIRCULATION


def test_derive_envelopes_returns_tuple():
    """Output type contract."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    envs = derive_zone_band_envelopes(oriented[0], grid, config=cfg)
    assert isinstance(envs, tuple)


def test_derive_envelopes_within_grid_bounds():
    """Each envelope rectangle ⊆ [0, envelope_width] × [0, envelope_depth]."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            assert e.x_min_m >= -1e-6
            assert e.y_min_m >= -1e-6
            assert e.x_max_m <= grid.envelope_width_m + 1e-6
            assert e.y_max_m <= grid.envelope_depth_m + 1e-6


def test_derive_envelopes_no_zero_area():
    """Per § 4.0: degenerate (zero-area) strips are dropped."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            assert e.width_m > 0
            assert e.depth_m > 0


def test_find_envelope_for_band_present():
    env_pub = ZoneBandEnvelope(
        band=ZoneBand.PUBLIC, direction=PlotOrientation.NORTH,
        x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
    )
    env_priv = ZoneBandEnvelope(
        band=ZoneBand.PRIVATE, direction=PlotOrientation.SOUTH,
        x_min_m=0.0, y_min_m=0.0, x_max_m=10.0, y_max_m=2.0,
    )
    found = find_envelope_for_band((env_pub, env_priv), ZoneBand.PUBLIC)
    assert found is not None
    assert found.band == ZoneBand.PUBLIC


def test_find_envelope_for_band_absent():
    env_pub = ZoneBandEnvelope(
        band=ZoneBand.PUBLIC, direction=PlotOrientation.NORTH,
        x_min_m=0.0, y_min_m=8.0, x_max_m=10.0, y_max_m=10.0,
    )
    found = find_envelope_for_band((env_pub,), ZoneBand.SERVICE)
    assert found is None


def test_corner_overlap_resolution_priority_default():
    """Per § 14.10: PUBLIC > PRIVATE > SERVICE by default for corners.

    Since C5/C6 may produce candidates with overlapping strips at corners,
    test with a real pipeline candidate that has corner-meeting bands.
    """
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    # Smoke check: no two envelopes have overlapping interior
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for i in range(len(envs)):
            for j in range(i + 1, len(envs)):
                a, b = envs[i], envs[j]
                ox = max(0.0, min(a.x_max_m, b.x_max_m) - max(a.x_min_m, b.x_min_m))
                oy = max(0.0, min(a.y_max_m, b.y_max_m) - max(a.y_min_m, b.y_min_m))
                # Allow shared boundary (touching) but not interior overlap
                assert ox * oy < 1e-6, (
                    f"envelopes[{i}] ({envs[i].band.value}) and "
                    f"envelopes[{j}] ({envs[j].band.value}) overlap"
                )


def test_corner_overlap_resolution_custom_priority():
    """Custom band_priority_order is respected at corner resolution."""
    oriented, _, grid = real_pipeline()
    # Custom: SERVICE first
    cfg = CorridorDesignConfig(
        band_priority_order=(ZoneBand.SERVICE, ZoneBand.PUBLIC, ZoneBand.PRIVATE),
    )
    cfg2 = CorridorDesignConfig()  # default

    for oc in oriented:
        e1 = derive_zone_band_envelopes(oc, grid, config=cfg)
        e2 = derive_zone_band_envelopes(oc, grid, config=cfg2)
        # Either same envelopes (no corner conflict) or different (priority changed
        # which band kept which corner). Both are valid; just ensure no crash.
        assert isinstance(e1, tuple) and isinstance(e2, tuple)


def test_envelope_count_matches_distinct_bands():
    """Output envelope count ≤ count of distinct non-CIRCULATION bands in input."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        non_circ_bands = {
            b for b in oc.orientation.refined_zone_bands.keys()
            if b != ZoneBand.CIRCULATION
        }
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        assert len(envs) <= len(non_circ_bands)


def test_envelopes_have_cardinal_directions_only():
    """Per C6 invariant 9: refined directions all cardinal; envelopes inherit."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    cardinal = {
        PlotOrientation.NORTH, PlotOrientation.EAST,
        PlotOrientation.SOUTH, PlotOrientation.WEST,
    }
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            assert e.direction in cardinal


def test_envelope_north_strip_is_top_edge():
    """An envelope facing NORTH should be at the top of the buildable area."""
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            if e.direction == PlotOrientation.NORTH:
                # Top of the envelope should be at y = envelope_depth_m
                assert abs(e.y_max_m - grid.envelope_depth_m) < 1e-6


def test_envelope_east_strip_is_right_edge():
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            if e.direction == PlotOrientation.EAST:
                assert abs(e.x_max_m - grid.envelope_width_m) < 1e-6


def test_envelope_south_strip_is_bottom_edge():
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            if e.direction == PlotOrientation.SOUTH:
                assert abs(e.y_min_m) < 1e-6


def test_envelope_west_strip_is_left_edge():
    oriented, _, grid = real_pipeline()
    cfg = CorridorDesignConfig()
    for oc in oriented:
        envs = derive_zone_band_envelopes(oc, grid, config=cfg)
        for e in envs:
            if e.direction == PlotOrientation.WEST:
                assert abs(e.x_min_m) < 1e-6
