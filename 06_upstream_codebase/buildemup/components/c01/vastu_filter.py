"""
BuildemUp† — Vastu Filter (Component 1).

Per SPEC_v0.2 Section 7 + Q5 (user preference):
Three-tier vastu opt-in (OFF / PARTIAL / FULL), all tiers INFO-level only.

OFF:
  No vastu guidance. Default.

PARTIAL (the 7 user-approved items, per SPEC_v0.2 Section 2.1):
  1. Main door direction (most important)
  2. Kitchen direction (southeast preferred)
  3. Master bedroom direction (southwest preferred)
  4. Pooja room direction (northeast preferred)
  5. Toilet/bathroom location (avoid northeast)
  6. Staircase direction (avoid northeast)
  7. Water tank location (underground northeast / overhead southwest)

FULL:
  All 7 PARTIAL items + additional items (plot shape, brahmasthan,
  window directions, furniture placement, etc.) sourced from the
  existing Component 7 vastu_engine KB.

IMPORTANT:
  All vastu messages are INFO severity. Never STRONG_CONCERN. Vastu
  is cultural preference, not building code — we never block on it.

Reuses Component 7's kb/vastu_engine rules where applicable (no
duplication). For PARTIAL, we extend with 2 additional items
(staircase, water tank) not in the vastu_engine core 5.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.brief import (
    GuidanceMessage, GuidanceSeverity, VastuTier, VASTU_PARTIAL_ITEMS,
)
from buildemup.domain.plot import Plot
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────
# PARTIAL vastu messages — the 7 items user can see on the form
# ─────────────────────────────────────────────────────────────────────────

def _main_door_message(plot_facing: PlotOrientation) -> GuidanceMessage:
    """Vastu preference for main door / entrance direction."""
    preferred = {PlotOrientation.NORTH, PlotOrientation.EAST,
                 PlotOrientation.NORTHEAST}
    avoid = {PlotOrientation.SOUTH, PlotOrientation.SOUTHWEST}

    if plot_facing in preferred:
        text = (
            f"Main door on a {plot_facing.value}-facing plot is auspicious "
            f"per Vastu (receives morning sun, sacred direction)."
        )
    elif plot_facing in avoid:
        text = (
            f"Main door on a {plot_facing.value}-facing plot is traditionally "
            f"avoided per Vastu. Consider placing the entrance on the "
            f"East or North side of the plot if possible, even if the "
            f"plot itself is {plot_facing.value}-facing."
        )
    else:
        text = (
            f"Main door on a {plot_facing.value}-facing plot is acceptable "
            f"per Vastu. North and East are most preferred; avoid South "
            f"and Southwest."
        )
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=text,
        context="vastu_main_door",
        action_verb="Consider",
    )


def _kitchen_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Kitchen is traditionally placed in the Southeast (SE) corner "
            "per Vastu (Agni — fire element). Northwest is an acceptable "
            "secondary. Avoid Northeast (sacred direction, fire-water "
            "conflict) and Southwest (Pitru zone)."
        ),
        context="vastu_kitchen",
        action_verb="Consider",
    )


def _master_bedroom_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Master bedroom is traditionally placed in the Southwest (SW) "
            "corner per Vastu (earth-element grounding, stability). "
            "Avoid Northeast — sacred direction considered inauspicious "
            "for personal spaces."
        ),
        context="vastu_master_bedroom",
        action_verb="Consider",
    )


def _pooja_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Pooja room is traditionally placed in the Northeast (NE) "
            "corner per Vastu — the Ishanya (sacred) direction. East is "
            "acceptable secondary. Avoid South and Southwest."
        ),
        context="vastu_pooja",
        action_verb="Consider",
    )


def _toilet_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Toilets/bathrooms are traditionally placed in Northwest or "
            "West per Vastu. Avoid Northeast (defiles sacred direction), "
            "Southeast (conflicts with kitchen fire element), and South."
        ),
        context="vastu_toilet",
        action_verb="Consider",
    )


def _staircase_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Staircase is traditionally placed in Southwest, South, or "
            "West per Vastu. Avoid Northeast (defiles the sacred direction) "
            "and the center (Brahmasthan — should stay clear)."
        ),
        context="vastu_staircase",
        action_verb="Consider",
    )


def _water_tank_message() -> GuidanceMessage:
    return GuidanceMessage(
        severity=GuidanceSeverity.INFO,
        text=(
            "Water storage per Vastu: underground tank in Northeast "
            "(flowing water, auspicious); overhead water tank in Southwest "
            "(weight adds earth-element stability). Avoid overhead tank in "
            "Northeast or center."
        ),
        context="vastu_water_tank",
        action_verb="Consider",
    )


# ─────────────────────────────────────────────────────────────────────────
# FULL vastu — additional items beyond PARTIAL
# ─────────────────────────────────────────────────────────────────────────

def _full_additional_messages() -> list[GuidanceMessage]:
    """Items included in FULL but not PARTIAL."""
    return [
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Brahmasthan (center of the house) should remain open and "
                "clear of heavy structures per Vastu. Avoid placing load-"
                "bearing walls, toilets, or kitchens at the center."
            ),
            context="vastu_brahmasthan",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Dining area: east or west is preferred per Vastu. Avoid "
                "south-facing dining tables (head pointing south while "
                "eating is traditionally avoided)."
            ),
            context="vastu_dining",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Windows: larger openings preferred on North and East walls "
                "(morning sun, cooler afternoon shade). Avoid large West-"
                "facing windows (afternoon heat)."
            ),
            context="vastu_windows",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Plot shape: regular rectangles or squares are preferred. "
                "Irregular shapes (triangular, L-shaped, cut corners) are "
                "considered less auspicious — extensions in NE are "
                "acceptable, cut corners in NE are traditionally avoided."
            ),
            context="vastu_plot_shape",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Sleeping direction: head pointing South or East while "
                "sleeping is preferred per Vastu. Avoid head pointing "
                "North (per traditional belief)."
            ),
            context="vastu_sleeping_direction",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Pooja altar: deities should face East or West (so the "
                "person praying faces the opposite direction). Never place "
                "deities facing South per traditional Vastu."
            ),
            context="vastu_pooja_altar",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Mirror placement: avoid mirrors in the bedroom facing the "
                "bed per Vastu. North and East walls are preferred "
                "locations for mirrors elsewhere."
            ),
            context="vastu_mirrors",
            action_verb="Consider",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=(
                "Slope and drainage: plot should ideally slope from "
                "Southwest (higher) to Northeast (lower) per Vastu. "
                "Drainage should flow toward the Northeast corner."
            ),
            context="vastu_slope",
            action_verb="Consider",
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

def generate_vastu_guidance(
    plot: Plot, tier: VastuTier,
) -> list[GuidanceMessage]:
    """Generate INFO-only vastu messages based on user's tier preference.

    Per SPEC_v0.2 Section 7 + Q5:
    - OFF (default): returns empty list
    - PARTIAL: returns 7 messages (the 7 VASTU_PARTIAL_ITEMS)
    - FULL: returns 7 PARTIAL + additional ~8 items

    ALL messages are GuidanceSeverity.INFO. We never produce
    STRONG_CONCERN or CONCERN for vastu — it's cultural preference.
    """
    if tier == VastuTier.OFF:
        return []

    messages: list[GuidanceMessage] = [
        _main_door_message(plot.facing),
        _kitchen_message(),
        _master_bedroom_message(),
        _pooja_message(),
        _toilet_message(),
        _staircase_message(),
        _water_tank_message(),
    ]

    if tier == VastuTier.FULL:
        messages.extend(_full_additional_messages())

    return messages


def list_partial_items_for_form_display() -> tuple[str, ...]:
    """Return the 7 PARTIAL items as displayed on the form.

    Used by the UI layer to show the user exactly what they're opting
    into when they pick PARTIAL. Re-exported from domain/brief.py to
    keep the form's data source colocated with vastu logic.
    """
    return VASTU_PARTIAL_ITEMS
