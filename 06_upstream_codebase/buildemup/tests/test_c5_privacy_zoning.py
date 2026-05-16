"""
Tests for B-NEW-J (S38): C5 privacy zoning predicate.

Verifies ``validate_privacy_zoning(zone_bands, plot_facing)`` per the
predicate contract:

  - Cardinal facings (N/S/E/W) forbid PRIVATE on the matching cardinal.
  - Intercardinal facings (NE/NW/SE/SW) forbid PRIVATE on the
    intercardinal itself plus its two adjacent cardinals.
  - PRIVATE on a non-forbidden direction passes.
  - Vacuous-pass when zone_bands has no PRIVATE entry.

Per C5 SPEC v0.9 LOCKED + B-NEW-J v0.1 PROPOSED.
"""
from __future__ import annotations

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c05.zone_bands import validate_privacy_zoning
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Cardinal — PRIVATE on forbidden direction → fail
# =============================================================================


def test_priv_north_facing_private_north_fails() -> None:
    """plot.facing=NORTH forbids PRIVATE at NORTH."""
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
    }
    ok, reason = validate_privacy_zoning(zone_bands, PlotOrientation.NORTH)
    assert ok is False
    assert reason is not None
    assert "privacy_zoning" in reason
    assert "PRIVATE" in reason


def test_priv_south_facing_private_south_fails() -> None:
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
    }
    ok, reason = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTH)
    assert ok is False
    assert "privacy_zoning" in (reason or "")


def test_priv_east_facing_private_east_fails() -> None:
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.EAST,
        ZoneBand.PUBLIC: PlotOrientation.WEST,
    }
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.EAST)
    assert ok is False


def test_priv_west_facing_private_west_fails() -> None:
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.WEST,
        ZoneBand.PUBLIC: PlotOrientation.EAST,
    }
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.WEST)
    assert ok is False


# =============================================================================
# Cardinal — PRIVATE on safe direction → pass
# =============================================================================


def test_priv_north_facing_private_south_passes() -> None:
    """plot.facing=NORTH allows PRIVATE at SOUTH (rear of plot)."""
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
    }
    ok, reason = validate_privacy_zoning(zone_bands, PlotOrientation.NORTH)
    assert ok is True
    assert reason is None


def test_priv_south_facing_private_north_passes() -> None:
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
    }
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTH)
    assert ok is True


def test_priv_east_facing_private_west_passes() -> None:
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.WEST,
        ZoneBand.PUBLIC: PlotOrientation.EAST,
    }
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.EAST)
    assert ok is True


def test_priv_north_facing_private_east_passes() -> None:
    """Cardinal facings only forbid the single matching cardinal — adjacent
    cardinals are safe."""
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.EAST,
        ZoneBand.PUBLIC: PlotOrientation.WEST,
    }
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTH)
    assert ok is True


# =============================================================================
# Intercardinal — PRIVATE on each of the three forbidden directions → fail
# =============================================================================


def test_priv_ne_facing_private_ne_fails() -> None:
    """plot.facing=NE forbids PRIVATE at NE."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.NORTHEAST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHEAST)
    assert ok is False


def test_priv_ne_facing_private_north_fails() -> None:
    """plot.facing=NE also forbids PRIVATE at NORTH (adjacent cardinal)."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.NORTH}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHEAST)
    assert ok is False


def test_priv_ne_facing_private_east_fails() -> None:
    """plot.facing=NE also forbids PRIVATE at EAST (adjacent cardinal)."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.EAST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHEAST)
    assert ok is False


def test_priv_sw_facing_private_sw_fails() -> None:
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.SOUTHWEST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTHWEST)
    assert ok is False


def test_priv_sw_facing_private_south_fails() -> None:
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.SOUTH}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTHWEST)
    assert ok is False


def test_priv_sw_facing_private_west_fails() -> None:
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.WEST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTHWEST)
    assert ok is False


# =============================================================================
# Intercardinal — PRIVATE on safe direction → pass
# =============================================================================


def test_priv_ne_facing_private_sw_passes() -> None:
    """plot.facing=NE — PRIVATE at SW (opposite corner) passes."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.SOUTHWEST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHEAST)
    assert ok is True


def test_priv_nw_facing_private_se_passes() -> None:
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.SOUTHEAST}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHWEST)
    assert ok is True


def test_priv_se_facing_private_north_passes() -> None:
    """plot.facing=SE forbids {SE, S, E}; PRIVATE at NORTH is safe."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.NORTH}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTHEAST)
    assert ok is True


def test_priv_sw_facing_private_north_passes() -> None:
    """plot.facing=SW forbids {SW, S, W}; PRIVATE at NORTH is safe."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.NORTH}
    ok, _ = validate_privacy_zoning(zone_bands, PlotOrientation.SOUTHWEST)
    assert ok is True


# =============================================================================
# Vacuous-pass + purity
# =============================================================================


def test_priv_no_private_band_passes() -> None:
    """Vacuous-pass: zone_bands lacking PRIVATE entry returns (True, None)."""
    zone_bands = {
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
        ZoneBand.SERVICE: PlotOrientation.SOUTH,
    }
    ok, reason = validate_privacy_zoning(zone_bands, PlotOrientation.NORTH)
    assert ok is True
    assert reason is None


def test_priv_predicate_does_not_mutate_input() -> None:
    """Predicate is pure — input dict is unchanged after the call."""
    zone_bands = {
        ZoneBand.PRIVATE: PlotOrientation.SOUTH,
        ZoneBand.PUBLIC: PlotOrientation.NORTH,
    }
    snapshot = dict(zone_bands)
    validate_privacy_zoning(zone_bands, PlotOrientation.NORTH)
    assert zone_bands == snapshot


# =============================================================================
# Reasoning text
# =============================================================================


def test_priv_failure_reason_names_directions() -> None:
    """Failure reason includes the offending PRIVATE direction and the
    forbidden set so callers can debug C11a's rejection messages."""
    zone_bands = {ZoneBand.PRIVATE: PlotOrientation.NORTH}
    ok, reason = validate_privacy_zoning(zone_bands, PlotOrientation.NORTHEAST)
    assert ok is False
    assert reason is not None
    # PRIVATE direction labeled
    assert "PRIVATE band at N" in reason or "PRIVATE band at NORTH" in reason or "N" in reason
    # plot_facing labeled
    assert "NE" in reason or "NORTHEAST" in reason


# =============================================================================
# Smoke test against a real default_zone_bands output
# =============================================================================


def test_priv_default_zone_bands_for_strip_topology_north_facing_passes() -> None:
    """The default zone_bands produced by C5 for a NORTH-facing STRIP plot
    should pass privacy_zoning. (Smoke test that the rule is consistent
    with C5's own defaults — if this fails for the default outputs,
    the rule contradicts C5's design intent.)"""
    from buildemup.components.c05.schema import TopologyKind
    from buildemup.components.c05.zone_bands import default_zone_bands

    for kind in TopologyKind:
        for facing in PlotOrientation:
            zb = default_zone_bands(kind, facing)
            ok, reason = validate_privacy_zoning(zb, facing)
            # C5's own defaults should respect privacy_zoning by design.
            # If any default fails, that's a finding worth surfacing
            # (filed as B-NEW-J-defaults if found).
            assert ok is True, (
                f"C5 default_zone_bands({kind.value}, {facing.value}) "
                f"violates privacy_zoning: {reason}"
            )
