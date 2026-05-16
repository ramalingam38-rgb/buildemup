"""
BuildemUp† — Engineering Depth Axis (v0.6)
=============================================

Per the v0.5 review's most important architectural insight:
  CONFIDENCE is about input certainty + model stability.
  It is NOT about engineering rigor.

Users misread "Confidence: Well-constrained" as "engineering validated."
That conflation is dangerous.

The fix (v0.5 style rename) partly addressed this. v0.6 adds a SECOND
orthogonal axis that explicitly describes engineering rigor:

  LEVEL 1 — Rule-based only
    Values computed by applying IS code rules to inputs. No frame
    analysis, no moment check. Our v0.4/v0.5 baseline.

  LEVEL 2 — Frame-checked
    Rule-based values + Hardy Cross frame sanity + IS 456 cl. 39.6
    Bresler interaction check. Our v0.6 addition. Catches obvious
    problems but is NOT a design.

  LEVEL 3 — Engineer-designed
    A licensed structural engineer has produced stamped drawings.
    BuildemUp does NOT produce LEVEL 3 — that is explicitly out of
    scope. LEVEL 3 is what must happen AFTER BuildemUp.

Why the separation matters:
  A WELL_CONSTRAINED value at LEVEL 1 means: our rules gave a clean
  answer, but we haven't checked whether the column can actually
  resist the moments the frame would deliver.

  A WELL_CONSTRAINED value at LEVEL 2 means: same data certainty,
  PLUS a frame sanity check said the column is likely OK.

  Neither is LEVEL 3. Both still need engineer validation.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class EngineeringDepth(str, Enum):
    """How deeply engineered is this output?

    This is orthogonal to Confidence. Both axes should be shown together.
    """
    LEVEL_1_RULE_BASED = "LEVEL_1_RULE_BASED"
    LEVEL_2_FRAME_CHECKED = "LEVEL_2_FRAME_CHECKED"
    LEVEL_3_ENGINEER_DESIGNED = "LEVEL_3_ENGINEER_DESIGNED"

    def display_label(self) -> str:
        return _DISPLAY[self.value]

    def user_description(self) -> str:
        return _DESCRIPTIONS[self.value]


_DISPLAY = {
    "LEVEL_1_RULE_BASED":        "Level 1 — Rule-based",
    "LEVEL_2_FRAME_CHECKED":     "Level 2 — Frame-checked",
    "LEVEL_3_ENGINEER_DESIGNED": "Level 3 — Engineer-designed",
}

_DESCRIPTIONS = {
    "LEVEL_1_RULE_BASED": (
        "Values computed by applying IS code rules to your inputs. "
        "No frame analysis. No moment capacity check. No P-delta. "
        "Catches typical residential cases. Does NOT catch unusual "
        "load paths or moment concentrations."
    ),
    "LEVEL_2_FRAME_CHECKED": (
        "Rule-based values PLUS a Hardy Cross frame sanity check with "
        "IS 456 cl. 39.6 Bresler interaction ratio. This adds a "
        "preliminary moment-capacity check that catches obvious "
        "problems. Still NOT a full frame analysis. Still NOT an "
        "engineer design."
    ),
    "LEVEL_3_ENGINEER_DESIGNED": (
        "A licensed structural engineer has produced stamped drawings. "
        "BuildemUp does NOT produce Level 3 output. Every BuildemUp "
        "estimate must be taken to your engineer for Level 3 validation "
        "before construction begins."
    ),
}


# Labels used in banner / legal text
LEVEL_1_DISCLAIMER = (
    "This is a LEVEL 1 rule-based estimate. It applies IS code rules "
    "to your inputs but does NOT include frame analysis. Your engineer "
    "must independently verify moment capacity before construction."
)

LEVEL_2_DISCLAIMER = (
    "This is a LEVEL 2 frame-checked estimate. It applies IS code rules "
    "AND a preliminary IS 456 cl. 39.6 Bresler interaction check. This "
    "is a sanity check, NOT a design. Your engineer must independently "
    "verify with SP-16 charts and full frame analysis before construction."
)


@dataclass(frozen=True)
class DepthIndicator:
    """The engineering depth stamp on an output."""
    level: EngineeringDepth
    what_we_did: tuple[str, ...]         # Methods actually applied
    what_we_did_not_do: tuple[str, ...]  # Honest about scope

    def format_for_user(self) -> str:
        lines = [
            f"Engineering Depth: {self.level.display_label()}",
            f"  {self.level.user_description()}",
            "",
            "  Methods applied:",
        ]
        for method in self.what_we_did:
            lines.append(f"    ✓ {method}")
        lines.append("")
        lines.append("  Methods NOT applied (engineer's job):")
        for method in self.what_we_did_not_do:
            lines.append(f"    ✗ {method}")
        return "\n".join(lines)


def level_1_indicator() -> DepthIndicator:
    """Level 1 indicator for pure rule-based output (pre-v0.6 style)."""
    return DepthIndicator(
        level=EngineeringDepth.LEVEL_1_RULE_BASED,
        what_we_did=(
            "IS 456 column sizing (section + steel %)",
            "IS 875 load estimation (dead + live)",
            "IS 1893 seismic zone factors",
            "IS 13920 ductile detailing (for Zone III+)",
            "Plan regularity classification",
        ),
        what_we_did_not_do=(
            "Frame analysis (moment distribution or stiffness matrix)",
            "P-M interaction check (IS 456 cl. 39.6)",
            "Beam moment + shear envelope",
            "Serviceability checks (deflection, crack width)",
        ),
    )


def level_2_indicator() -> DepthIndicator:
    """Level 2 indicator when frame sanity check is applied."""
    return DepthIndicator(
        level=EngineeringDepth.LEVEL_2_FRAME_CHECKED,
        what_we_did=(
            "IS 456 column sizing (section + steel %)",
            "IS 875 load estimation (dead + live + lateral)",
            "IS 1893 seismic zone factors",
            "IS 13920 ductile detailing (for Zone III+)",
            "Plan regularity classification",
            "Hardy Cross moment distribution (preliminary)",
            "IS 456 cl. 39.6 Bresler interaction ratio (with real αn)",
            "5-combo governing load case selection",
        ),
        what_we_did_not_do=(
            "Full frame analysis with stiffness matrix",
            "P-delta / second-order effects",
            "Moment-curvature analysis",
            "Beam moment + shear envelope (approx only)",
            "Serviceability checks (deflection, crack width)",
            "Dynamic response / time-history analysis",
        ),
    )
