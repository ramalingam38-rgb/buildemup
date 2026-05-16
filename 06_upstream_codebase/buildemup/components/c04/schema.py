"""
BuildemUp† — Component 4 (Plot Analysis) schema.

All dataclasses + enums for C4. Per SPEC v0.5 LOCKED § 3.

Pure types only — no logic, no I/O. Importable independently of the
rest of c04 to break circular import risk between
`kb/city_geography.py` and `components/c04/__init__.py`.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.plot import Plot, SoilType


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class PlotTier(str, Enum):
    """Plot-size tier — drives layout topology bias in C5."""
    T1_COMPACT = "T1"     # 600 ≤ sqft < 2400
    T2_STANDARD = "T2"    # 2400 ≤ sqft < 4000
    T3_LARGE = "T3"       # sqft ≥ 4000


class PlotShape(str, Enum):
    """Plot shape. v1 always RECTANGULAR; L_SHAPED / IRREGULAR = B-066."""
    RECTANGULAR = "rectangular"
    L_SHAPED = "l_shaped"
    IRREGULAR = "irregular"


class ClimateZone(str, Enum):
    """5 climate zones per NBC 2016 Part 8 Section 1, §§ 2.2.21–2.2.24 + 3.2.2.

    No v1 city maps to HOT_DRY (Jodhpur not in supported set) or COLD
    (Srinagar not in supported set). Reserved for future expansion.
    """
    HOT_DRY = "hot_dry"
    WARM_HUMID = "warm_humid"
    TEMPERATE = "temperate"
    COMPOSITE = "composite"
    COLD = "cold"


class ConfidenceLevel(str, Enum):
    """Confidence tag on derived properties (currently soil_estimate).

    Consumer contract: components reading `confidence == LOW` MUST apply
    a structural safety factor to bearing_capacity_kpa. C7 currently
    uses its own conservative defaults (B-072 retrofit will align this).
    """
    LOW = "low"        # high-variability soil region; downstream MUST apply safety factor
    MEDIUM = "medium"  # city-default for stable-soil region
    HIGH = "high"      # user-supplied site survey


class RoadWidthClass(str, Enum):
    """Coarse classifier for layout heuristics. FSI-aware logic lives in C2."""
    NARROW = "narrow"        # < 6m
    STANDARD = "standard"    # 6–12m
    WIDE = "wide"            # ≥ 12m


# ─────────────────────────────────────────────────────────────────────────────
# Geometry / climate / wind / soil dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SunPath:
    """Solar geometry at solstices. Closed-form Cooper 1969.

    Per-month declination = B-067.
    """
    latitude_deg: float
    summer_solstice_noon_alt: float
    winter_solstice_noon_alt: float
    sunrise_arc_summer: tuple[float, float]
    sunrise_arc_winter: tuple[float, float]


@dataclass(frozen=True)
class WindContext:
    """City wind characterisation.

    `basic_speed_ms` is the IS-875 Part 3 basic wind speed for the city,
    in m/s.

    v0.5 (CG-5): `primary_direction` and `monsoon_direction` use
    full PlotOrientation member names (NORTH, NORTHEAST, ...), not
    short value-string aliases.

    v0.6 (walk #3): `confidence` field exposes the data-quality status
    of the per-city direction values. All v1 cities are MEDIUM (single-
    station IMD climatology). HIGH requires per-city wind-rose
    verification (B-070).

    v0.7 (walk #2): `basic_speed_ms` is a STORED field, not a lazy
    property. The IS-875 wind speed is resolved once at PREVAILING_WIND
    construction (module load) and frozen on the dataclass, eliminating
    the runtime hidden import. Single-source-of-truth for wind speeds is
    preserved (kb.wind_load is still the canonical KB; consulted at
    module load instead of at every property access).

    v0.8 (walk #7): `city` field REMOVED. It was introduced in v0.5 as
    the lookup key for the `basic_speed_ms` lazy property. v0.7 made
    `basic_speed_ms` a stored field, leaving `city` as dead metadata.
    Code-grep confirmed no consumer read it. Removing eliminates the
    key/field consistency risk (PREVAILING_WIND["chennai"] could have
    had city="delhi" without anyone noticing). The dict key in
    PREVAILING_WIND IS the city.

    CONSUMER CONTRACT: components reading `confidence == MEDIUM` MAY
    apply fallback heuristics (e.g., assume isotropic monsoon dominance)
    when ventilation logic depends on tight directional resolution.
    """
    primary_direction: PlotOrientation     # dominant non-monsoon
    monsoon_direction: PlotOrientation     # SW or NE monsoon arrival
    basic_speed_ms: float                  # v0.7: stored field
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass(frozen=True)
class SoilEstimate:
    """Soil + bearing capacity estimate with confidence tag.

    Consumer contract: confidence == LOW → downstream MUST apply
    safety factor on bearing_capacity_kpa.

    v0.6 (walks #2, #7): `provenance_note` surfaces approximation
    decisions or high-variability reasons that the LOW/MEDIUM/HIGH
    confidence enum is too coarse to express. Examples:
      - None for clean user_input or stable city defaults.
      - "filled_up_high_variability_site_survey_required" for Mumbai
        city default (matches CITY_SOIL_DEFAULTS' "MANDATORY soil
        testing" guidance).

    v1.1 (B-074 closed): MEDIUM_ROCK is now a first-class kb.SoilClass
    with IS 6403-aligned kPa (1000-1500 typ 1250). The previous
    `_b074` breadcrumb is no longer emitted; the breadcrumb hook in
    APPROXIMATION_NOTES_BY_SOIL_TYPE survives as an empty-dict export
    for forward compatibility.
    """
    soil_type: SoilType
    bearing_capacity_kpa: float | None
    confidence: ConfidenceLevel
    source: str                              # "user_input" | "city_default"
    provenance_note: str | None = None       # NEW v0.6 (walks #2, #7)


@dataclass(frozen=True)
class NeighbourContext:
    """Raw plot openness — does NOT account for setbacks.

    `effective_open_sides` (post-setback) = B-068.

    v0.6 (walk #5): `corner_assumption` surfaces the v1 convention used
    when the input contract underspecifies which side the second street
    is on (currently only CONTINUOUS+corner without an explicit
    `Plot.corner_orientation`). Populated as
    `"second_street_assumed_LEFT_b076"` for that case; None otherwise.

    CONSUMER CONTRACT: components reading `corner_assumption is not None`
    SHOULD treat downstream layout decisions affected by the second-
    street side as TENTATIVE pending B-076.
    """
    open_sides: tuple[PlotOrientation, ...]
    shared_sides: tuple[PlotOrientation, ...]
    raw_facade_count: int                    # = len(open_sides)
    corner_assumption: str | None = None     # NEW v0.6 (walk #5)


@dataclass(frozen=True)
class PlotAnalysisProvenance:
    """Tracking metadata: when this analysis was derived + KB versions.

    `derived_at` is caller-injected (Unix epoch seconds, > 0). KB
    versions auto-populated from KB_VERSION constants at construction.
    """
    derived_at: float                    # Unix epoch seconds (> 0)
    source_versions: Mapping[str, str]   # MappingProxyType


# ─────────────────────────────────────────────────────────────────────────────
# Top-level output: PlotAnalysis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlotAnalysis:
    """C4's output. Single source of truth for plot-derived properties.

    C5 onward MUST consume this rather than re-deriving from raw `plot`.
    C7 currently re-derives soil — see B-072 for the deferred retrofit.

    v0.5 (CG-9): `trace_id` (was `brief_token` in v0.1–v0.4) — renamed
    to mirror upstream Brief.trace_id.
    """
    # ── Identity ──
    trace_id: str
    plot: Plot                                            # frozen passthrough

    # ── Computed properties ──
    area_sqft: float
    area_sqm: float
    tier: PlotTier
    shape: PlotShape                                      # ALWAYS RECTANGULAR in v1
    shape_metadata: Mapping[str, object]                  # MappingProxyType
    aspect_ratio: float                                   # depth / width

    # ── Solar geometry ──
    sun_path: SunPath

    # ── Climate (top-level — climate-derived, not solar-geometry-derived) ──
    climate_zone: ClimateZone
    baseline_room_orientation_guidelines: Mapping[
        ClimateZone, Mapping[str, tuple[PlotOrientation, ...]]
    ]                                                      # MappingProxyType (outer + inner)

    # ── Wind ──
    prevailing_wind: WindContext

    # ── Geotechnical ──
    soil_estimate: SoilEstimate

    # ── Site context ──
    road_width_classification: RoadWidthClass
    neighbour_context: NeighbourContext

    # ── Provenance ──
    provenance: PlotAnalysisProvenance


# ─────────────────────────────────────────────────────────────────────────────
# Constants (climate-keyed baselines + facing translation)
# ─────────────────────────────────────────────────────────────────────────────

# Baseline room orientation guidelines per climate zone (v0.5 CG-5: full
# PlotOrientation member names). MappingProxyType wraps both outer + inner
# dicts so consumers cannot mutate (SC-1).
#
# These are CLIMATE-derived heuristics. C5/C6 produce dynamic recommendations
# integrating baselines + plot facing + aspect ratio + neighbour openness +
# Vastu + brief preferences.
#
# Values for HOT_DRY and COLD are reserved (no v1 city maps to them); the
# tables are populated for forward-compat but no v1 test path exercises them
# beyond presence checks.
_PO = PlotOrientation  # local alias to keep the table compact

BASELINE_ROOM_ORIENTATION_GUIDELINES: Mapping[
    ClimateZone, Mapping[str, tuple[PlotOrientation, ...]]
] = MappingProxyType({
    ClimateZone.WARM_HUMID: MappingProxyType({   # Mumbai, Chennai
        "living":   (_PO.NORTH, _PO.NORTHEAST),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST, _PO.NORTHWEST),
    }),
    ClimateZone.TEMPERATE: MappingProxyType({    # Bangalore, Pune
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST, _PO.SOUTH),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST),
    }),
    ClimateZone.COMPOSITE: MappingProxyType({    # Delhi, Hyderabad
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "kitchen":  (_PO.EAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST, _PO.SOUTHEAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST, _PO.NORTHWEST),
    }),
    ClimateZone.HOT_DRY: MappingProxyType({       # Reserved (no v1 city)
        "living":   (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "kitchen":  (_PO.EAST, _PO.NORTHEAST),
        "bedroom":  (_PO.NORTH, _PO.NORTHEAST, _PO.EAST),
        "bathroom": (_PO.WEST, _PO.SOUTHWEST),
    }),
    ClimateZone.COLD: MappingProxyType({          # Reserved (no v1 city)
        "living":   (_PO.SOUTH, _PO.SOUTHEAST, _PO.SOUTHWEST),
        "kitchen":  (_PO.EAST, _PO.SOUTHEAST),
        "bedroom":  (_PO.SOUTH, _PO.SOUTHEAST),
        "bathroom": (_PO.NORTH, _PO.NORTHWEST),
    }),
})


# Facing → which compass direction is "left" / "right" from a viewer
# standing on the street facing the plot. Used by neighbour_context for
# SharedSide (LEFT/RIGHT) → PlotOrientation translation.
#
# Convention: "left" = 90° counter-clockwise from front; "right" = 90°
# clockwise. Compound facings (NORTHEAST, SOUTHEAST, SOUTHWEST, NORTHWEST)
# get perpendicular diagonals.
LEFT_RIGHT_BY_FACING: Mapping[
    PlotOrientation, Mapping[str, PlotOrientation]
] = MappingProxyType({
    _PO.NORTH:     MappingProxyType({"left": _PO.WEST,      "right": _PO.EAST}),
    _PO.SOUTH:     MappingProxyType({"left": _PO.EAST,      "right": _PO.WEST}),
    _PO.EAST:      MappingProxyType({"left": _PO.NORTH,     "right": _PO.SOUTH}),
    _PO.WEST:      MappingProxyType({"left": _PO.SOUTH,     "right": _PO.NORTH}),
    _PO.NORTHEAST: MappingProxyType({"left": _PO.NORTHWEST, "right": _PO.SOUTHEAST}),
    _PO.SOUTHEAST: MappingProxyType({"left": _PO.NORTHEAST, "right": _PO.SOUTHWEST}),
    _PO.SOUTHWEST: MappingProxyType({"left": _PO.SOUTHEAST, "right": _PO.NORTHWEST}),
    _PO.NORTHWEST: MappingProxyType({"left": _PO.SOUTHWEST, "right": _PO.NORTHEAST}),
})


# Facing → opposite (used for back-of-plot computation).
_OPPOSITE_FACING: Mapping[PlotOrientation, PlotOrientation] = MappingProxyType({
    _PO.NORTH:     _PO.SOUTH,
    _PO.SOUTH:     _PO.NORTH,
    _PO.EAST:      _PO.WEST,
    _PO.WEST:      _PO.EAST,
    _PO.NORTHEAST: _PO.SOUTHWEST,
    _PO.SOUTHWEST: _PO.NORTHEAST,
    _PO.SOUTHEAST: _PO.NORTHWEST,
    _PO.NORTHWEST: _PO.SOUTHEAST,
})


def compute_plot_facing_sides(
    facing: PlotOrientation,
) -> Mapping[str, PlotOrientation]:
    """Map plot.facing to the four cardinal "sides" of the plot.

    Returns a frozen mapping with keys "front", "back", "left", "right".

    "front" = facing direction (street side)
    "back"  = opposite of front
    "left"  = 90° counter-clockwise from front (viewer on street facing plot)
    "right" = 90° clockwise from front

    Tested for all 8 PlotOrientation values.
    """
    if not isinstance(facing, PlotOrientation):
        raise ValueError(
            f"compute_plot_facing_sides requires PlotOrientation; got "
            f"{type(facing).__name__}"
        )
    lr = LEFT_RIGHT_BY_FACING[facing]
    return MappingProxyType({
        "front": facing,
        "back":  _OPPOSITE_FACING[facing],
        "left":  lr["left"],
        "right": lr["right"],
    })


__all__ = [
    "PlotTier",
    "PlotShape",
    "ClimateZone",
    "ConfidenceLevel",
    "RoadWidthClass",
    "SunPath",
    "WindContext",
    "SoilEstimate",
    "NeighbourContext",
    "PlotAnalysisProvenance",
    "PlotAnalysis",
    "BASELINE_ROOM_ORIENTATION_GUIDELINES",
    "LEFT_RIGHT_BY_FACING",
    "compute_plot_facing_sides",
]
