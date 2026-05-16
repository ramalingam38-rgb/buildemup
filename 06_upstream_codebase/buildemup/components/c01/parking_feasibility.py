"""
BuildemUp† — Parking Feasibility (Component 1).

Per SPEC_v0.2 Section 4.5 (Drawback 7 fix):
Plot width < 8m + stilt parking = parking won't fit reasonably.

Reasoning:
  - Car parking requires ~2.5m width + circulation (0.5m each side)
  - After side setbacks on a narrow plot, internal width shrinks fast
  - At 8m plot with 1m side setbacks = 6m internal = room for 2 cars tight
  - Below 8m = soft concern; below 6m = strong concern

This is a VERY common real-world failure in Indian urban plots.
Flagging early saves the user rework in the architect phase.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.brief import GuidanceMessage, GuidanceSeverity
from buildemup.domain.floor_requirement import FloorUse


# Minimum plot widths for various parking scenarios
# These are empirical from Indian residential architecture norms.
MIN_PLOT_WIDTH_FOR_STILT_M = 8.0          # below this = soft concern
CRITICAL_PLOT_WIDTH_FOR_STILT_M = 6.0     # below this = strong concern

# Rough car-footprint needs
CAR_WIDTH_M = 2.5
CAR_CIRCULATION_EACH_SIDE_M = 0.5


def check_parking_feasibility(
    plot_width_m: float,
    plot_depth_m: float,
    has_stilt_parking: bool,
    side_left_setback_m: float,
    side_right_setback_m: float,
) -> list[GuidanceMessage]:
    """Return guidance messages about parking feasibility.

    Only fires if the user opted for stilt parking. If they didn't,
    parking is handled differently (surface parking in setbacks, etc.)
    and we don't flag.

    Args:
        plot_width_m: full plot width (street-facing)
        plot_depth_m: full plot depth
        has_stilt_parking: True if any floor in brief is STILT_PARKING
        side_left_setback_m: compliant left side setback
        side_right_setback_m: compliant right side setback

    Returns:
        List of GuidanceMessage (empty if no issues).
    """
    if not has_stilt_parking:
        return []

    # How much width remains after side setbacks?
    internal_width = (
        plot_width_m - side_left_setback_m - side_right_setback_m
    )
    # Rough max cars that fit side-by-side at 2.5m each + 0.5m circulation
    cars_that_fit = int(internal_width // 3.0) if internal_width >= 3.0 else 0

    if plot_width_m < CRITICAL_PLOT_WIDTH_FOR_STILT_M:
        # Very tight — strong concern
        return [GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text=(
                f"[Preliminary check — width-based, layout-dependent. "
                f"Does NOT validate turning radius, column placement, "
                f"or gate alignment.] "
                f"Your plot width of {plot_width_m}m is very tight for stilt "
                f"parking. After side setbacks, internal width is about "
                f"{internal_width:.1f}m — likely fits {cars_that_fit} "
                f"car{'s' if cars_that_fit != 1 else ''} at most, depending "
                f"on final column placement, turning radius, and entry angle. "
                f"Final feasibility depends on layout (Component 4). "
                f"Consider: (a) single-car stilt only, "
                f"(b) surface parking in front setback area, "
                f"(c) skip stilt and use ground floor as habitable space."
            ),
            context="parking_feasibility_critical",
            action_verb="Reconsider",
        )]
    elif plot_width_m < MIN_PLOT_WIDTH_FOR_STILT_M:
        # Marginal — strong concern but with more options
        return [GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text=(
                f"[Preliminary check — width-based, layout-dependent. "
                f"Does NOT validate turning radius, column placement, "
                f"or gate alignment.] "
                f"Your plot width of {plot_width_m}m is likely tight for stilt "
                f"parking — depending on final layout. After side setbacks, "
                f"internal width will be about {internal_width:.1f}m. "
                f"A single car needs 2.5m + circulation, plus allowance "
                f"for column placement, turning radius, and entry angle. "
                f"Final feasibility depends on layout (Component 4). "
                f"Consider: (a) surface parking in front setback, "
                f"(b) single-car stilt only, "
                f"(c) ground-floor parking (loses habitable space)."
            ),
            context="parking_feasibility",
            action_verb="Reconsider",
        )]

    # Plot width OK — no issue
    return []


def estimate_stilt_car_capacity(
    plot_width_m: float,
    side_left_setback_m: float,
    side_right_setback_m: float,
) -> int:
    """Rough estimate of cars that can fit in stilt parking.

    Purely informational — used in guidance messages.
    """
    internal_width = (
        plot_width_m - side_left_setback_m - side_right_setback_m
    )
    if internal_width < 3.0:
        return 0
    return int(internal_width // 3.0)
