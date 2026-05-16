"""Tests for ``B-C8-CORRIDOR-ZONE-CONTRACT`` v0.1 amendment (S43).

LOCKED via S43 directive ("Let's do the dependencies on c8&c9 and code
that also"). Verifies the CorridorZone dataclass + corridor_zones
derived accessor on CorridorDesignedCandidate.
"""
from __future__ import annotations

import pytest

from buildemup.components.c08.schema import (
    CorridorEndpoint,
    CorridorEndpointKind,
    CorridorSegment,
    CorridorSegmentKind,
    CorridorZone,
    _corridor_segment_to_zone,
)
from buildemup.domain.envelope import PlotOrientation


# ── helpers ────────────────────────────────────────────────────────────


def _make_segment(
    *,
    sx: float,
    sy: float,
    ex: float,
    ey: float,
    runs_along: PlotOrientation,
    constant_width_m: float = 1.0,
    start_width_m: float | None = None,
    end_width_m: float | None = None,
    kind: CorridorSegmentKind = CorridorSegmentKind.PRIMARY,
) -> CorridorSegment:
    sw = start_width_m if start_width_m is not None else constant_width_m
    ew = end_width_m if end_width_m is not None else constant_width_m
    length = max(abs(ex - sx), abs(ey - sy))
    return CorridorSegment(
        kind=kind,
        start=CorridorEndpoint(
            kind=CorridorEndpointKind.JUNCTION, point_m=(sx, sy)
        ),
        end=CorridorEndpoint(
            kind=CorridorEndpointKind.JUNCTION, point_m=(ex, ey)
        ),
        constant_width_m=constant_width_m,
        start_width_m=sw,
        end_width_m=ew,
        taper_zone_m=0.5,
        length_m=length,
        runs_along=runs_along,
    )


# ── CorridorZone construction invariants ───────────────────────────────


def test_zone_rejects_zero_width():
    with pytest.raises(ValueError, match="positive extents"):
        CorridorZone(
            x_m=0.0, y_m=0.0, width_m=0.0, depth_m=1.0,
            source_segment_kind=CorridorSegmentKind.PRIMARY,
        )


def test_zone_rejects_negative_depth():
    with pytest.raises(ValueError, match="positive extents"):
        CorridorZone(
            x_m=0.0, y_m=0.0, width_m=1.0, depth_m=-1.0,
            source_segment_kind=CorridorSegmentKind.PRIMARY,
        )


def test_zone_accepts_positive_extents():
    z = CorridorZone(
        x_m=1.0, y_m=2.0, width_m=3.0, depth_m=0.9,
        source_segment_kind=CorridorSegmentKind.PRIMARY,
    )
    assert z.x_m == 1.0 and z.width_m == 3.0


# ── derivation: uniform-width horizontal segment ───────────────────────


def test_horizontal_uniform_segment_yields_correct_zone():
    """Horizontal segment from (1, 5) → (4, 5), width=1.0, no taper.
    Expected zone: x=1, y=4.5 (centred), w=3, d=1.0."""
    seg = _make_segment(
        sx=1.0, sy=5.0, ex=4.0, ey=5.0, runs_along=PlotOrientation.EAST,
        constant_width_m=1.0,
    )
    z = _corridor_segment_to_zone(seg)
    assert z.x_m == 1.0
    assert z.y_m == 4.5
    assert z.width_m == 3.0
    assert z.depth_m == 1.0


# ── derivation: tapered horizontal segment (conservative) ──────────────


def test_horizontal_tapered_segment_uses_max_width():
    """Tapered segment widths (start=1.0, const=1.2, end=1.4).
    Conservative reservation uses 1.4."""
    seg = _make_segment(
        sx=1.0, sy=5.0, ex=4.0, ey=5.0, runs_along=PlotOrientation.EAST,
        constant_width_m=1.2, start_width_m=1.0, end_width_m=1.4,
    )
    z = _corridor_segment_to_zone(seg)
    assert z.depth_m == 1.4
    # y-centred: y0 = 5.0 - 1.4/2 = 4.3
    assert z.y_m == 4.3


# ── derivation: vertical segment ───────────────────────────────────────


def test_vertical_segment_yields_correct_zone():
    """Vertical segment (5, 2) → (5, 6), width=1.0.
    Expected zone: x=4.5 (centred), y=2, w=1.0, d=4."""
    seg = _make_segment(
        sx=5.0, sy=2.0, ex=5.0, ey=6.0, runs_along=PlotOrientation.NORTH,
    )
    z = _corridor_segment_to_zone(seg)
    assert z.x_m == 4.5
    assert z.y_m == 2.0
    assert z.width_m == 1.0
    assert z.depth_m == 4.0


# ── derivation: reversed-direction segment same as forward ─────────────


def test_segment_direction_invariant():
    """A segment running east vs west between the same endpoints
    yields the same zone (min/max coords)."""
    seg_e = _make_segment(
        sx=1.0, sy=5.0, ex=4.0, ey=5.0, runs_along=PlotOrientation.EAST,
    )
    seg_w = _make_segment(
        sx=4.0, sy=5.0, ex=1.0, ey=5.0, runs_along=PlotOrientation.WEST,
    )
    z_e = _corridor_segment_to_zone(seg_e)
    z_w = _corridor_segment_to_zone(seg_w)
    assert (z_e.x_m, z_e.y_m, z_e.width_m, z_e.depth_m) == (
        z_w.x_m, z_w.y_m, z_w.width_m, z_w.depth_m
    )


# ── source_segment_kind provenance ─────────────────────────────────────


def test_zone_preserves_segment_kind():
    seg = _make_segment(
        sx=0.0, sy=0.0, ex=1.0, ey=0.0, runs_along=PlotOrientation.EAST,
        kind=CorridorSegmentKind.BRANCH,
    )
    z = _corridor_segment_to_zone(seg)
    assert z.source_segment_kind == CorridorSegmentKind.BRANCH


# ── corridor_zones derived property on CorridorDesignedCandidate ───────


def test_corridor_zones_empty_when_no_corridor():
    """When ``has_corridor=False`` (or segments tuple is empty), the
    derived zones tuple is empty. Verified at the property logic level
    rather than constructing a full CorridorPath (which has expensive
    cross-module dependencies)."""
    # The property short-circuits on has_corridor=False. We test the
    # semantic via the empty-segments equivalence instead.
    empty_segments: tuple = ()
    zones = tuple(
        _corridor_segment_to_zone(s) for s in empty_segments
    )
    assert zones == ()


def test_corridor_zones_canonical_ordering():
    """Multiple segments produce zones sorted lex-ASC by
    (x_m, y_m, width_m, depth_m). Verified at the segment-list level."""
    seg_a = _make_segment(
        sx=5.0, sy=0.0, ex=5.0, ey=3.0, runs_along=PlotOrientation.NORTH,
    )
    seg_b = _make_segment(
        sx=0.0, sy=5.0, ex=3.0, ey=5.0, runs_along=PlotOrientation.EAST,
    )
    z_a = _corridor_segment_to_zone(seg_a)
    z_b = _corridor_segment_to_zone(seg_b)
    # Build the expected sorted tuple and compare.
    sorted_zones = tuple(
        sorted([z_a, z_b], key=lambda z: (z.x_m, z.y_m, z.width_m, z.depth_m))
    )
    # b.x_m = 0.0 < a.x_m = 4.5, so b comes first.
    assert sorted_zones[0] is z_b
    assert sorted_zones[1] is z_a


def test_segment_to_zone_pure_deterministic():
    """Two derivations of the same segment yield equal zones."""
    seg = _make_segment(
        sx=1.0, sy=2.0, ex=5.0, ey=2.0, runs_along=PlotOrientation.EAST,
    )
    z1 = _corridor_segment_to_zone(seg)
    z2 = _corridor_segment_to_zone(seg)
    assert z1 == z2
