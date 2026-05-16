"""
BuildemUp† — Plot domain object (Component 1).

The buyer's plot of land. Captures physical dimensions, street
orientation, abutting road width, plot type (detached/semi/continuous),
and optional soil type if user knows it.

DIFFERENCE vs Envelope:
  - Plot is the RAW land (before setbacks)
  - Envelope is the buildable footprint (after setbacks)
  - Component 1 produces Plot from user input
  - setback_calculator converts Plot → Envelope

DOMAIN ENFORCEMENT (from v0.7.1):
  Plot is a first-class domain type. Downstream components consuming
  a Plot must use the actual object, not a raw dict.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from buildemup.domain.envelope import PlotOrientation


class PlotType(str, Enum):
    """Physical relationship to neighbouring plots.

    Drives setback calculation per SPEC_v0.2 Section 3.2:
      - DETACHED: 4-side setbacks required
      - SEMI_DETACHED: 3 sides (shared side = 0)
      - CONTINUOUS: front + rear only (both sides = 0, e.g., row houses
                    or Chennai's Continuous Building Area per TNCDBR 2019)

    Default: DETACHED (safest, most common for standalone homes).
    """
    DETACHED = "detached"
    SEMI_DETACHED = "semi_detached"
    CONTINUOUS = "continuous"


class SharedSide(str, Enum):
    """Which side is shared with a neighbour (only for SEMI_DETACHED).

    Left/right is relative to someone standing on the street facing the plot.
    """
    LEFT = "left"
    RIGHT = "right"


class SoilType(str, Enum):
    """Soil types that users might know from a soil test.

    If user doesn't know, they leave this as None and Component 7
    defaults to a conservative assumption.
    """
    HARD_ROCK = "hard_rock"
    MEDIUM_ROCK = "medium_rock"
    DENSE_SAND = "dense_sand"
    MEDIUM_SAND = "medium_sand"
    LOOSE_SAND = "loose_sand"
    STIFF_CLAY = "stiff_clay"
    MEDIUM_CLAY = "medium_clay"
    SOFT_CLAY = "soft_clay"
    FILLED_UP = "filled_up"     # Made-up ground, weakest


# Six supported launch cities (matches Component 7 scope)
SUPPORTED_CITIES = frozenset({
    "chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi",
})


@dataclass(frozen=True)
class Plot:
    """Physical plot of land where the building will go.

    All measurements in metres. This represents the buyer's plot
    BEFORE setbacks are applied — the total legal land boundary.

    Validation (in __post_init__):
      - width / depth within 3.0..60.0
      - road_width within 1.5..30.0
      - city in SUPPORTED_CITIES
      - If corner_plot, second_road_width_m required
      - If plot_type=SEMI_DETACHED, shared_side required
      - plot_type=CONTINUOUS implies no shared_side needed (both sides shared)
    """
    width_m: float                          # Street-facing dimension
    depth_m: float                          # Perpendicular to street
    facing: PlotOrientation                 # Compass direction
    city: str                               # Must be in SUPPORTED_CITIES
    road_width_m: float                     # Abutting road width
    plot_type: PlotType = PlotType.DETACHED
    corner_plot: bool = False
    second_road_width_m: float | None = None
    shared_side: SharedSide | None = None   # Only if SEMI_DETACHED
    soil_type_known: SoilType | None = None

    def __post_init__(self) -> None:
        # Dimension bounds
        if not 3.0 <= self.width_m <= 60.0:
            raise ValueError(
                f"Plot width {self.width_m}m out of range [3.0, 60.0]. "
                f"Below 3m is unworkable; above 60m refer to architect."
            )
        if not 3.0 <= self.depth_m <= 60.0:
            raise ValueError(
                f"Plot depth {self.depth_m}m out of range [3.0, 60.0]."
            )

        # Road width bounds
        if not 1.5 <= self.road_width_m <= 30.0:
            raise ValueError(
                f"Road width {self.road_width_m}m out of range [1.5, 30.0]. "
                f"Below 1.5m is a footpath; above 30m is arterial/highway."
            )

        # City must be supported
        normalized_city = self.city.lower().strip()
        if normalized_city not in SUPPORTED_CITIES:
            raise ValueError(
                f"City '{self.city}' not supported. Must be one of: "
                f"{sorted(SUPPORTED_CITIES)}."
            )
        # Normalize city name in place (frozen dataclass workaround)
        object.__setattr__(self, "city", normalized_city)

        # Corner plot requires second road width
        if self.corner_plot:
            if self.second_road_width_m is None:
                raise ValueError(
                    "corner_plot=True requires second_road_width_m to be set."
                )
            if not 1.5 <= self.second_road_width_m <= 30.0:
                raise ValueError(
                    f"second_road_width_m {self.second_road_width_m}m out of range."
                )
        elif self.second_road_width_m is not None:
            raise ValueError(
                "second_road_width_m given but corner_plot=False."
            )

        # Semi-detached requires shared_side
        if self.plot_type == PlotType.SEMI_DETACHED:
            if self.shared_side is None:
                raise ValueError(
                    "plot_type=SEMI_DETACHED requires shared_side "
                    "(LEFT or RIGHT)."
                )
        elif self.shared_side is not None:
            raise ValueError(
                f"shared_side given but plot_type={self.plot_type.value}. "
                f"shared_side only meaningful for SEMI_DETACHED."
            )

    @property
    def area_sqm(self) -> float:
        """Raw plot area before setbacks."""
        return self.width_m * self.depth_m

    @property
    def area_sqft(self) -> float:
        """Plot area in square feet (for user-facing display)."""
        return self.area_sqm * 10.7639

    @property
    def wider_road_width_m(self) -> float:
        """For corner plots, returns the wider of the two roads.

        Per TNCDBR 2019: front setback of a corner plot is determined
        by the wider road.
        """
        if not self.corner_plot:
            return self.road_width_m
        return max(self.road_width_m, self.second_road_width_m or 0)

    def describe(self) -> str:
        """Human-readable one-liner for logs and explain() output."""
        base = (
            f"{self.width_m}m × {self.depth_m}m ({self.area_sqm:.0f} sqm) "
            f"{self.facing.value}-facing in {self.city}, "
            f"{self.road_width_m}m road, "
            f"type={self.plot_type.value}"
        )
        if self.corner_plot:
            base += f" corner (+ {self.second_road_width_m}m road)"
        return base

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "width_m": self.width_m,
            "depth_m": self.depth_m,
            "facing": self.facing.value,
            "city": self.city,
            "road_width_m": self.road_width_m,
            "plot_type": self.plot_type.value,
            "corner_plot": self.corner_plot,
            "second_road_width_m": self.second_road_width_m,
            "shared_side": (
                self.shared_side.value if self.shared_side else None
            ),
            "soil_type_known": (
                self.soil_type_known.value if self.soil_type_known else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Plot":
        return cls(
            width_m=payload["width_m"],
            depth_m=payload["depth_m"],
            facing=PlotOrientation(payload["facing"]),
            city=payload["city"],
            road_width_m=payload["road_width_m"],
            plot_type=PlotType(payload.get("plot_type", "DETACHED")),
            corner_plot=payload.get("corner_plot", False),
            second_road_width_m=payload.get("second_road_width_m"),
            shared_side=(
                SharedSide(payload["shared_side"])
                if payload.get("shared_side") else None
            ),
            soil_type_known=(
                SoilType(payload["soil_type_known"])
                if payload.get("soil_type_known") else None
            ),
        )
