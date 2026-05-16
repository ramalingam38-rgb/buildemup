"""
BuildemUp† — Confidence Scoring Framework (v0.5)
==================================================

v0.5 RENAMING: The previous HIGH/MEDIUM/LOW names carried false-precision
implications (HIGH read as "highly accurate" by users). The v0.4 review
flagged this as the most subtle but important confidence problem.

New names are descriptive of WHAT the level means, not how "good" it is:

  WELL_CONSTRAINED  = Computed directly from a code rule / hard engineering value.
                       User can rely on the number (±5% variability).
                       Example: IS 456 column size for given floor count.
                       (was: HIGH)

  REGIONAL_TYPICAL  = Computed from typical/modelled values for the region.
                       Variability ±5-15% depending on inputs.
                       Example: Cost from Chennai 2026 average rates.
                       (was: MEDIUM)

  DEPENDS_ON_CHOICE = Depends on contractor choice, supplier, or human decisions.
                       Variability >15%, varies with decisions we can't predict.
                       Example: Final contractor margin, tile choice cost.
                       (was: LOW)

The OLD values (HIGH/MEDIUM/LOW) remain as aliases for backwards-compat
during the v0.5 transition. The DISPLAY uses the new names.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Confidence(str, Enum):
    """Confidence in a numeric output. User sees this directly.

    v0.5: Names changed from HIGH/MEDIUM/LOW to descriptive terms.
    Old names retained as aliases for backwards-compat.
    """
    # New v0.5 descriptive names — display uses these
    WELL_CONSTRAINED = "WELL_CONSTRAINED"
    REGIONAL_TYPICAL = "REGIONAL_TYPICAL"
    DEPENDS_ON_CHOICE = "DEPENDS_ON_CHOICE"

    # Backwards-compat aliases (v0.4 code that imported HIGH/MEDIUM/LOW)
    HIGH = "WELL_CONSTRAINED"
    MEDIUM = "REGIONAL_TYPICAL"
    LOW = "DEPENDS_ON_CHOICE"

    def description(self) -> str:
        """Plain-language explanation for the user."""
        return _DESCRIPTIONS[self.value]

    def display_label(self) -> str:
        """Human-readable label for output (with the descriptive name)."""
        return _DISPLAY_LABELS[self.value]


_DESCRIPTIONS = {
    "WELL_CONSTRAINED": (
        "Computed from Indian codes (IS 456, IS 875) or hard specifications. "
        "Variability typically ±5% or less. Reflects input certainty + "
        "code stability — NOT engineering correctness (still requires "
        "engineer review at detailed design)."
    ),
    "REGIONAL_TYPICAL": (
        "Modelled from typical regional values. Variability ±5-15% "
        "depending on local conditions and market fluctuations."
    ),
    "DEPENDS_ON_CHOICE": (
        "Depends on contractor choice, supplier selection, or other "
        "human decisions. Variability often >15%. Use as indicative only."
    ),
}


_DISPLAY_LABELS = {
    "WELL_CONSTRAINED": "Well-constrained",
    "REGIONAL_TYPICAL": "Regional typical",
    "DEPENDS_ON_CHOICE": "Depends on your choices",
}


def classify(variability_pct: float) -> Confidence:
    """Classify confidence from variability percentage.

    Thresholds:
      ≤ 5%  → WELL_CONSTRAINED  (was HIGH)
      ≤ 15% → REGIONAL_TYPICAL  (was MEDIUM)
      > 15% → DEPENDS_ON_CHOICE (was LOW)
    """
    if variability_pct <= 5.0:
        return Confidence.WELL_CONSTRAINED
    elif variability_pct <= 15.0:
        return Confidence.REGIONAL_TYPICAL
    else:
        return Confidence.DEPENDS_ON_CHOICE


@dataclass(frozen=True)
class ConfidenceEvidence:
    """Records WHY we assigned a particular confidence level.

    Useful for debugging and for showing user evidence chain.
    """
    level: Confidence
    reason: str                    # e.g., "IS 456 cl. 26.5.3.1"
    variability_pct: float = 0.0
    caveats: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"{self.level.display_label()} — {self.reason} (±{self.variability_pct}%)"


# Pre-built evidence objects for common cases (reuse across modules)
WELL_CONSTRAINED_IS456_RULE = ConfidenceEvidence(
    level=Confidence.WELL_CONSTRAINED,
    reason="Direct from IS 456:2000 code rule",
    variability_pct=0.0,
)

WELL_CONSTRAINED_IS875_LOAD = ConfidenceEvidence(
    level=Confidence.WELL_CONSTRAINED,
    reason="Direct from IS 875 load standard",
    variability_pct=0.0,
)

REGIONAL_TYPICAL_RATE = ConfidenceEvidence(
    level=Confidence.REGIONAL_TYPICAL,
    reason="Typical regional material rate for current quarter",
    variability_pct=8.0,
    caveats=("Steel ±8%", "Labour ±10%", "Concrete ±4%"),
)

REGIONAL_TYPICAL_SOIL = ConfidenceEvidence(
    level=Confidence.REGIONAL_TYPICAL,
    reason="City-typical soil profile (not tested)",
    variability_pct=15.0,
    caveats=("Real soil testing recommended",),
)

DEPENDS_ON_CHOICE_MARGIN = ConfidenceEvidence(
    level=Confidence.DEPENDS_ON_CHOICE,
    reason="Contractor margin varies 8-22% by builder",
    variability_pct=20.0,
)

DEPENDS_ON_CHOICE_FINISH = ConfidenceEvidence(
    level=Confidence.DEPENDS_ON_CHOICE,
    reason="Depends on user's finish/fixture choices",
    variability_pct=30.0,
)


# Backwards-compat aliases for old names (v0.4 imports)
HIGH_IS456_RULE = WELL_CONSTRAINED_IS456_RULE
HIGH_IS875_LOAD = WELL_CONSTRAINED_IS875_LOAD
MEDIUM_REGIONAL_RATE = REGIONAL_TYPICAL_RATE
MEDIUM_SOIL_ASSUMPTION = REGIONAL_TYPICAL_SOIL
LOW_CONTRACTOR_MARGIN = DEPENDS_ON_CHOICE_MARGIN
LOW_FINISH_CHOICE = DEPENDS_ON_CHOICE_FINISH
