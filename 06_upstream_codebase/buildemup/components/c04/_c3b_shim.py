"""
C4 — Plot Analysis — UPSTREAM STUB for C3b consumption
=======================================================

NOTE: This is a STUB module covering only the surface C3b consumes.
The real C4 (LOCKED) provides full plot analysis including soil,
neighboring buildings, FAR, setbacks per jurisdiction. C3b only needs:

  - PlotAnalysis             — orientation + climate + plot dimensions

C3b uses PlotAnalysis for tweak generation context:
  - kitchen_reorient: aligns kitchen with cardinal direction
  - pooja_relocate:   aligns pooja with east (Vastu opt-in via brief)
  - balcony_add:      ventilation direction
  - window_resize:    daylight direction

Stability: PINNED to C4 v1.0.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Tuple


CardinalDirection = Literal["N", "S", "E", "W", "NE", "NW", "SE", "SW"]

ClimateZone = Literal[
    "warm_humid",    # Chennai, Mumbai coast
    "hot_dry",       # Rajasthan, interior plains
    "moderate",      # Bangalore, Pune
    "composite",     # Delhi, Lucknow
    "cold",          # Himalayan
]


@dataclass(frozen=True)
class PlotEdge:
    """One edge of the plot polygon, with its cardinal-direction
    orientation. Used by C3b for orientation-aware tweaks."""
    edge_id:        str
    direction:      CardinalDirection
    length_m:       float
    is_road_facing: bool = False

    def __post_init__(self) -> None:
        if not self.edge_id:
            raise ValueError("PlotEdge.edge_id must be non-empty")
        if self.length_m <= 0:
            raise ValueError(
                f"PlotEdge.length_m must be positive; got {self.length_m}"
            )


@dataclass(frozen=True)
class PlotAnalysis:
    """Geometric + climatic + regulatory analysis of the plot.

    Minimum fields per C4 v1.0 LOCKED for C3b consumption:
      - plot_analysis_id, plot_signature: identity
      - locality_label: micro-market identifier (e.g. "Chennai-OMR")
      - climate_zone: drives ventilation/orientation tweaks
      - plot_edges: per-edge orientation
      - dominant_road_direction: where the entrance comes from
    """
    plot_analysis_id:         str
    plot_signature:           str
    jurisdiction_profile_id:  str
    locality_label:           str
    climate_zone:             ClimateZone

    plot_area_sqft:           float
    plot_dimensions_m:        Tuple[float, float]
    """(width, depth) in meters."""

    plot_edges:               Tuple[PlotEdge, ...] = field(default_factory=tuple)
    dominant_road_direction:  CardinalDirection = "N"
    primary_ventilation_axis: Literal["N_S", "E_W"] = "N_S"
    """C6 Orientation Priority output — preferred long-axis for
    cross-ventilation. Chennai default: N_S (per spec § 6 inheritance
    from NZEB India)."""

    def __post_init__(self) -> None:
        if not self.plot_analysis_id:
            raise ValueError("PlotAnalysis.plot_analysis_id must be non-empty")
        if not self.plot_signature:
            raise ValueError("PlotAnalysis.plot_signature must be non-empty")
        if not self.locality_label:
            raise ValueError("PlotAnalysis.locality_label must be non-empty")
        if self.plot_area_sqft <= 0:
            raise ValueError(
                f"PlotAnalysis.plot_area_sqft must be positive; "
                f"got {self.plot_area_sqft}"
            )
        w, d = self.plot_dimensions_m
        if w <= 0 or d <= 0:
            raise ValueError(
                f"PlotAnalysis.plot_dimensions_m must both be positive; "
                f"got {self.plot_dimensions_m!r}"
            )


C4_STUB_VERSION: Final[str] = "v1.0.LOCKED.stub.S52"

__all__ = [
    "CardinalDirection", "ClimateZone",
    "PlotEdge", "PlotAnalysis",
    "C4_STUB_VERSION",
]
