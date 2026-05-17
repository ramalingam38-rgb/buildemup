"""C9 caller-error / failure-mode tests.

Per C9 SPEC v0.7 LOCKED § 6 (Failure modes) + § 4.8 (Order-of-checks).

Caller-error layer (one-shot, before per-candidate loop):
  - Type checks → TypeError
  - Plot shape (B-066) → NotImplementedError
  - Brief sanity (bedroom_count >= 1) → ValueError

Plus edge cases: empty input, KB integrity defects.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import RoomSizingConfig, size_rooms
from buildemup.components.c09.errors import NBCConfidenceTooLow
from buildemup.tests._c9_fixtures import run_c8_pipeline


# ---------------------------------------------------------------------------
# Type checks
# ---------------------------------------------------------------------------


def test_type_check_corridor_designed_candidates_must_be_tuple():
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    with pytest.raises(TypeError, match="corridor_designed_candidates"):
        size_rooms(list(cdc), brief, grid, plot_analysis)  # type: ignore[arg-type]


def test_type_check_floor_room_brief():
    cdc, _, grid, plot_analysis = run_c8_pipeline()
    with pytest.raises(TypeError, match="floor_room_brief"):
        size_rooms(cdc, "not a brief", grid, plot_analysis)  # type: ignore[arg-type]


def test_type_check_grid():
    cdc, brief, _, plot_analysis = run_c8_pipeline()
    with pytest.raises(TypeError, match="grid"):
        size_rooms(cdc, brief, {"bay_x_m": 3.0}, plot_analysis)  # type: ignore[arg-type]


def test_type_check_plot_analysis():
    cdc, brief, grid, _ = run_c8_pipeline()
    with pytest.raises(TypeError, match="plot_analysis"):
        size_rooms(cdc, brief, grid, "not a plot_analysis")  # type: ignore[arg-type]


def test_type_check_candidate_member_wrong_type():
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    bad = ("not_a_candidate",) + cdc[1:]
    with pytest.raises(TypeError, match="CorridorDesignedCandidate"):
        size_rooms(bad, brief, grid, plot_analysis)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Plot shape (B-066)
# ---------------------------------------------------------------------------


def test_non_rectangular_plot_raises_not_implemented():
    """B-066: v1 supports RECTANGULAR only."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    # Build a fake plot_analysis with non-rectangular shape
    import dataclasses
    from buildemup.components.c04.schema import PlotShape
    bad_pa = dataclasses.replace(plot_analysis, shape=PlotShape.L_SHAPED)
    with pytest.raises(NotImplementedError, match="RECTANGULAR"):
        size_rooms(cdc, brief, grid, bad_pa)


def test_irregular_plot_raises_not_implemented():
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    import dataclasses
    from buildemup.components.c04.schema import PlotShape
    bad_pa = dataclasses.replace(plot_analysis, shape=PlotShape.IRREGULAR)
    with pytest.raises(NotImplementedError, match="RECTANGULAR"):
        size_rooms(cdc, brief, grid, bad_pa)


# ---------------------------------------------------------------------------
# Brief sanity
# ---------------------------------------------------------------------------


def test_brief_with_zero_bedrooms_raises():
    """C9 requires bedroom_count >= 1 (a dwelling without any bedroom is out of scope)."""
    from buildemup.domain.floor_brief import FloorRoomBrief
    cdc, _, grid, plot_analysis = run_c8_pipeline()
    bad_brief = FloorRoomBrief(
        bedroom_count=0, bathroom_count=1,
        has_kitchen=True, has_living=True,
        has_pooja=False, has_utility=False,
    )
    with pytest.raises(ValueError, match="bedroom_count"):
        size_rooms(cdc, bad_brief, grid, plot_analysis)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_no_raise():
    """Per § 6: empty input → empty output."""
    _, brief, grid, plot_analysis = run_c8_pipeline()
    sized = size_rooms((), brief, grid, plot_analysis)
    assert sized == ()


# ---------------------------------------------------------------------------
# Systemic NBCConfidenceTooLow
# ---------------------------------------------------------------------------


def test_require_verified_nbc_systemic_raise():
    """When require_verified_nbc=True and any unverified row used, raise once
    (not per-candidate)."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()  # medium_brief has utility
    with pytest.raises(NBCConfidenceTooLow):
        size_rooms(cdc, brief, grid, plot_analysis,
                   config=RoomSizingConfig(require_verified_nbc=True))


def test_nbc_confidence_too_low_extends_keyerror():
    """Per § 6: NBCConfidenceTooLow extends KeyError for backward compat."""
    err = NBCConfidenceTooLow("test", unverified_room_ids=("r1",))
    assert isinstance(err, KeyError)


def test_nbc_confidence_too_low_carries_unverified_room_ids():
    err = NBCConfidenceTooLow("test", unverified_room_ids=("UTILITY_1",))
    assert err.unverified_room_ids == ("UTILITY_1",)


# ---------------------------------------------------------------------------
# Default config behaviour
# ---------------------------------------------------------------------------


def test_default_config_does_not_raise_on_unverified_rows():
    """require_verified_nbc=False (default) is permissive."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    sized = size_rooms(cdc, brief, grid, plot_analysis)  # no config = defaults
    assert len(sized) == len(cdc)
