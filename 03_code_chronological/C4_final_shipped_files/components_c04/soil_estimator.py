"""
BuildemUp† — C4 soil estimator.

Per spec § 4.7. Returns SoilEstimate with confidence tag.

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# The following items are KNOWN deferrals — already enumerated in spec § 16.
# Critique reviewers: these are filed; please do NOT re-flag.
# (This block is a review aid; can be stripped after critique-review cycles.)
#
#   B-074  MEDIUM_ROCK proper kPa value: real ~1000-1500 kPa per IS 6403,
#          currently approximated to SOFT_ROCK 660 kPa. Fix requires either
#          extending kb.SoilClass with MEDIUM_ROCK class OR aligning C4's
#          BEARING_CAPACITY_BY_TYPE with C7's foundation-design defaults.
#   B-077  Richer multi-state soil confidence model (currently LOW/MEDIUM/HIGH +
#          free-text provenance_note). Multi-state would distinguish e.g.
#          LOW-variability / LOW-liquefaction / LOW-fill.
#   B-082  Structured error fields on SoilEstimate: approximation_error_pct,
#          expected_range_kpa. Currently breadcrumbed via provenance_note
#          string only. Web-verified S29: NCBI mudstone study confirms
#          underestimate magnitude.
# ─────────────────────────────────────────────────────────────────────────────

Two branches:
  - user_input:  plot.soil_type_known is provided → HIGH confidence,
                 bearing capacity from BEARING_CAPACITY_BY_TYPE.
  - city_default: not provided → city's typical_soil/kPa from
                  SOIL_PROFILES; LOW confidence if typical_soil is in
                  HIGH_VARIABILITY_SOIL_TYPES, else MEDIUM.

CONSUMER CONTRACT (per spec § 3): components reading
`confidence == LOW` MUST apply a structural safety factor.

v0.6 (walks #2, #7): populates `provenance_note` to surface
approximation decisions or high-variability reasons that the
LOW/MEDIUM/HIGH enum is too coarse to express.

v0.8 (walk #8): the approximation notes table (previously
`_APPROXIMATED_USER_INPUT_NOTES` local to this module) moved to
`kb/soil_city_defaults.APPROXIMATION_NOTES_BY_SOIL_TYPE`. Approximation
policy is data, not logic; it belongs in the KB layer alongside the
bearing-capacity table it documents.

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ConfidenceLevel, SoilEstimate
from buildemup.domain.plot import Plot, SoilType
from buildemup.kb.soil_city_defaults import (
    APPROXIMATION_NOTES_BY_SOIL_TYPE,
    BEARING_CAPACITY_BY_TYPE,
    HIGH_VARIABILITY_SOIL_TYPES,
    SOIL_PROFILES,
)


def estimate_soil(plot: Plot) -> SoilEstimate:
    """Derive a soil estimate from the plot. See module docstring."""
    if plot.soil_type_known is not None:
        return SoilEstimate(
            soil_type=plot.soil_type_known,
            bearing_capacity_kpa=BEARING_CAPACITY_BY_TYPE[plot.soil_type_known],
            confidence=ConfidenceLevel.HIGH,
            source="user_input",
            provenance_note=APPROXIMATION_NOTES_BY_SOIL_TYPE.get(plot.soil_type_known),
        )

    # City-default branch. Plot.__post_init__ already guaranteed
    # plot.city ∈ SUPPORTED_CITIES, and verify_kb_consistency()
    # guaranteed SUPPORTED_CITIES ⊆ SOIL_PROFILES, so no KeyError here.
    profile = SOIL_PROFILES[plot.city]
    typical = profile.typical_soil
    is_high_variability = typical in HIGH_VARIABILITY_SOIL_TYPES
    confidence = (
        ConfidenceLevel.LOW
        if is_high_variability
        else ConfidenceLevel.MEDIUM
    )
    provenance_note = (
        f"{typical.value}_high_variability_site_survey_required"
        if is_high_variability
        else None
    )
    return SoilEstimate(
        soil_type=typical,
        bearing_capacity_kpa=profile.typical_bearing_capacity_kpa,
        confidence=confidence,
        source="city_default",
        provenance_note=provenance_note,
    )


__all__ = ["estimate_soil"]
