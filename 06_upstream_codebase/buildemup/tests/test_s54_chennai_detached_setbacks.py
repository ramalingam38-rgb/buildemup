"""
S54-004 — regression test for Chennai detached tier_50_to_150sqm setbacks.

Bug: `kb_rules/setback_rules.json` Chennai detached tier_50_to_150sqm had
side_right_m: 0.0 — semi-detached/CBA behaviour incorrectly leaking into
the detached rules. A user on a 20×30 ft (~56 sqm) plot saw output:
  "Side (R): 0.6m | required 0.0m | +0.6m"
which is nonsensical for a detached plot.

Fix (S54-004): side_right_m corrected to 0.7m, symmetric with side_left_m,
per TNCDBR 2019 Schedule II. KB version bumped to v4.
"""
from __future__ import annotations

import pytest

from buildemup.domain import Plot, PlotType, PlotOrientation
from buildemup.components.c01.setback_calculator import (
    compute_compliant_setbacks,
)


# ─── Plots in the affected tier (50–150 sqm) ──────────────────────────────

@pytest.mark.parametrize("width_m,depth_m,plot_name", [
    (6.096, 9.144, "20x30 ft (56 sqm)"),   # the user's original case
    (7.0, 10.0, "23x33 ft (70 sqm)"),
    (8.5, 12.0, "28x39 ft (102 sqm)"),
    (10.0, 14.0, "33x46 ft (140 sqm)"),    # near upper bound
])
def test_chennai_detached_50_150sqm_has_symmetric_side_setbacks(
    width_m, depth_m, plot_name,
):
    """For a Chennai detached plot in the 50-150 sqm tier, left and right
    side setbacks must be equal (and BOTH non-zero) — a detached plot
    cannot have 0m on any side by definition.
    """
    p = Plot(
        width_m=width_m, depth_m=depth_m,
        facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.DETACHED,
    )
    s, authority = compute_compliant_setbacks(p)

    assert "TNCDBR" in authority

    # Soul rule: detached plot must have non-zero setbacks on ALL sides.
    assert s.side_left_m > 0.0, (
        f"{plot_name}: detached plot has 0m on LEFT side — impossible"
    )
    assert s.side_right_m > 0.0, (
        f"{plot_name}: detached plot has 0m on RIGHT side — S54-004 bug"
    )

    # Symmetric rule: left and right setbacks should match for detached
    assert s.side_left_m == s.side_right_m, (
        f"{plot_name}: asymmetric side setbacks "
        f"(L={s.side_left_m}, R={s.side_right_m}) — bug or genuine "
        f"city-specific rule? Investigate."
    )

    # Tier-specific rule: TNCDBR Schedule II says 0.7m for 50-150 sqm
    assert s.side_right_m == 0.7, (
        f"{plot_name}: expected 0.7m side setback (TNCDBR Sched II), "
        f"got {s.side_right_m}m"
    )
    assert s.side_left_m == 0.7


# ─── Plots NOT in the affected tier — these should NOT change ────────────

def test_chennai_detached_over_150sqm_unchanged():
    """Plots > 150 sqm use a different tier with 1.5m all sides; fix
    must not affect them.
    """
    p = Plot(
        width_m=12.0, depth_m=15.0,  # 180 sqm — over 150
        facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
        plot_type=PlotType.DETACHED,
    )
    s, _ = compute_compliant_setbacks(p)
    assert s.side_left_m == 1.5
    assert s.side_right_m == 1.5


def test_chennai_continuous_still_zero_sides():
    """CONTINUOUS plots correctly have 0 sides — fix must not break this."""
    p = Plot(
        width_m=6.0, depth_m=15.0,
        facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=6.0,
        plot_type=PlotType.CONTINUOUS,
    )
    s, _ = compute_compliant_setbacks(p)
    assert s.side_left_m == 0.0
    assert s.side_right_m == 0.0


# ─── KB version bumped ────────────────────────────────────────────────────

def test_kb_version_bumped_to_v4():
    """The KB version field should reflect the S54-004 fix."""
    import json
    from pathlib import Path
    kb_path = (
        Path(__file__).parent.parent / "kb_rules" / "setback_rules.json"
    )
    data = json.loads(kb_path.read_text(encoding="utf-8"))
    version = data["_meta"]["_version"]
    assert "v4" in version, (
        f"Expected KB version v4 after S54-004 fix, got {version}"
    )
