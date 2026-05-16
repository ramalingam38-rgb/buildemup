"""
BuildemUp† — Component 8 (Corridor Designer) — Schema module.

Per C8 SPEC v0.5 LOCKED § 3 (Output schema).

Defines:
  - Enums: CorridorSegmentKind, CorridorEndpointKind, WidthQuantization,
           WidthPropagation, ConsumptionBand
  - Dataclasses: ZoneBandEnvelope, CorridorEndpoint, CorridorSegment,
                 CorridorPath, CorridorProvenance, CorridorDesignedCandidate,
                 CorridorDesignConfig, GridAlignmentReport
  - Constants: GRID_FRACTION_CANDIDATES, ALLOWED_JUNCTION_ANGLES_DEG,
               DEFAULT_EPSILON_M, DEFAULT_BAND_PRIORITY_ORDER,
               DEFAULT_UNDER_COMFORT_PENALTY_RATIO

All dataclasses are frozen (immutable). Mappings use MappingProxyType wrappers
where appropriate to prevent post-construction mutation.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Final, Mapping

from buildemup.components.c05.schema import (
    ConnectivityType,
    ZoneBand,
)
from buildemup.components.c06.schema import OrientedCandidate
from buildemup.components.c08.tolerances import GEOMETRIC_M
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Constants
# =============================================================================

# Per § 14.2 / § 4.3 — quantization fraction set
GRID_FRACTION_CANDIDATES: tuple[float, ...] = (
    0.25,
    1.0 / 3.0,
    0.5,
    2.0 / 3.0,
    0.75,
)

# Per § 4.6 invariant 13 — junction angle constants
ALLOWED_JUNCTION_ANGLES_DEG: frozenset[float] = frozenset({0.0, 90.0, 180.0, 270.0})

# Per § 3 — coordinate-coincidence tolerance default
DEFAULT_EPSILON_M: float = 0.001  # 1mm; sub-construction-tolerance

# Per § 14.22 — default band priority order (Walk #3 Drawback 7)
# Indian residential vernacular default; configurable via config.band_priority_order
# CIRCULATION intentionally absent (it IS the corridor; § 14.7).
DEFAULT_BAND_PRIORITY_ORDER: tuple[ZoneBand, ...] = (
    ZoneBand.PUBLIC,    # 1st priority — entry-bearing, most foot traffic
    ZoneBand.PRIVATE,   # 2nd — privacy/quietness
    ZoneBand.SERVICE,   # 3rd — most spatially flexible
)

# Per § 14.19 — width-selection penalty default
DEFAULT_UNDER_COMFORT_PENALTY_RATIO: float = 2.0


# =============================================================================
# Enums
# =============================================================================


class CorridorSegmentKind(str, Enum):
    """The role of a corridor segment within a path. Per § 3."""
    PRIMARY = "primary"
    BRANCH = "branch"
    LOOP_ARM = "loop_arm"
    ENTRY_STUB = "entry_stub"


class CorridorEndpointKind(str, Enum):
    """What anchors a corridor endpoint. Per § 3."""
    ENTRY = "entry"
    BAND_ATTACHMENT = "band_attachment"
    JUNCTION = "junction"
    STAIR_ATTACHMENT = "stair_attachment"
    DEAD_END = "dead_end"


class WidthQuantization(str, Enum):
    """How corridor width is chosen relative to grid bay.

    Per § 3 (NEW v0.2 § 14.2). Default: GRID_FRACTIONS.
    """
    GRID_FRACTIONS = "grid_fractions"
    NEAREST_GRID_LINE = "nearest_grid_line"
    NONE_FREE_WIDTH = "none_free_width"


class WidthPropagation(str, Enum):
    """How junction widths propagate across adjacent segments.

    Per § 3 (NEW v0.4 § 14.20). Default: JUNCTION_LOCAL_ONLY.
    """
    JUNCTION_LOCAL_ONLY = "junction_local_only"
    GLOBAL_MAX_INHERITANCE = "global_max"
    INDEPENDENT_WIDTHS = "independent"


class ConsumptionBand(str, Enum):
    """Qualitative classification of corridor area consumption.

    Per § 4.9 (NEW v0.3 § 14.15). Advisory metadata only; C8 takes no action.
    """
    LOW = "low"      # envelope_area_fraction < 0.12
    MEDIUM = "medium"  # 0.12 ≤ fraction < 0.20
    HIGH = "high"    # fraction ≥ 0.20


# =============================================================================
# Data classes — spatial model
# =============================================================================


@dataclass(frozen=True)
class ZoneBandEnvelope:
    """Bounding rectangle for one ZoneBand within the buildable envelope.

    Per § 4.0 (NEW v0.2 § 14.1). C8 derives these internally from
    ``oriented_candidate.refined_zone_bands`` + ``grid.envelope_*``.

    Coordinates: plot-local, origin = SW corner of buildable envelope.

    Invariants (asserted at construction):
      - x_min < x_max, y_min < y_max
      - direction is one of CARDINAL_FACINGS (per C6 invariant)
    """
    band: ZoneBand
    direction: PlotOrientation
    x_min_m: float
    y_min_m: float
    x_max_m: float
    y_max_m: float

    def __post_init__(self) -> None:
        if not isinstance(self.band, ZoneBand):
            raise TypeError(
                f"ZoneBandEnvelope.band must be ZoneBand; "
                f"got {type(self.band).__name__}"
            )
        if not isinstance(self.direction, PlotOrientation):
            raise TypeError(
                f"ZoneBandEnvelope.direction must be PlotOrientation; "
                f"got {type(self.direction).__name__}"
            )
        if self.x_min_m >= self.x_max_m:
            raise ValueError(
                f"ZoneBandEnvelope: x_min_m ({self.x_min_m}) must be < "
                f"x_max_m ({self.x_max_m})"
            )
        if self.y_min_m >= self.y_max_m:
            raise ValueError(
                f"ZoneBandEnvelope: y_min_m ({self.y_min_m}) must be < "
                f"y_max_m ({self.y_max_m})"
            )

    @property
    def centroid_m(self) -> tuple[float, float]:
        """Centroid of the envelope rectangle in plot-local coords."""
        return (
            (self.x_min_m + self.x_max_m) / 2.0,
            (self.y_min_m + self.y_max_m) / 2.0,
        )

    @property
    def width_m(self) -> float:
        return self.x_max_m - self.x_min_m

    @property
    def depth_m(self) -> float:
        return self.y_max_m - self.y_min_m


# =============================================================================
# Data classes — endpoints + segments
# =============================================================================


@dataclass(frozen=True)
class CorridorEndpoint:
    """A single endpoint of a corridor segment. Per § 3 / § 4.4.

    Coordinate-exactness: all endpoints carry exact ``(x, y)`` floats.
    Two endpoints are coincident iff distance < EPSILON_M (§ 4.4).
    """
    kind: CorridorEndpointKind
    point_m: tuple[float, float]
    attached_band: ZoneBand | None = None
    attached_direction: PlotOrientation | None = None
    attached_envelope_id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CorridorEndpointKind):
            raise TypeError(
                f"CorridorEndpoint.kind must be CorridorEndpointKind; "
                f"got {type(self.kind).__name__}"
            )
        if (
            not isinstance(self.point_m, tuple)
            or len(self.point_m) != 2
        ):
            raise TypeError(
                f"CorridorEndpoint.point_m must be a 2-tuple of floats; "
                f"got {self.point_m!r}"
            )
        for c in self.point_m:
            if not isinstance(c, (int, float)):
                raise TypeError(
                    f"CorridorEndpoint.point_m must be a 2-tuple of floats; "
                    f"got element {c!r}"
                )


@dataclass(frozen=True)
class CorridorSegment:
    """A single straight axis-aligned section of the corridor.

    Per § 3 (NEW v0.4 § 14.20).

    All segments are axis-aligned to a cardinal direction in v1
    (diagonal deferred to B-113).

    Each segment has THREE width regions along its ``runs_along`` axis:
      - Taper-start zone:    [start, start + taper_zone_m]; width interpolates
                              linearly from ``start_width_m`` to
                              ``constant_width_m``.
      - Constant middle:     [start + taper_zone_m, end - taper_zone_m];
                              width = ``constant_width_m``.
      - Taper-end zone:      [end - taper_zone_m, end]; width interpolates
                              linearly from ``constant_width_m`` to
                              ``end_width_m``.

    When ``start_width_m == end_width_m == constant_width_m`` (no taper),
    the segment is uniform-width.

    Invariants (asserted at construction):
      - start.point_m and end.point_m differ in exactly one coordinate
        (axis-aligned)
      - length_m == |end - start| in the differing coordinate
      - all three width values > 0
      - 2 × taper_zone_m ≤ length_m (Invariant 16)
      - constant_middle_length ≥ length_m / 2 (Invariant 20)
      - runs_along is the cardinal direction from start to end
    """
    kind: CorridorSegmentKind
    start: CorridorEndpoint
    end: CorridorEndpoint
    constant_width_m: float
    start_width_m: float
    end_width_m: float
    taper_zone_m: float
    length_m: float
    runs_along: PlotOrientation

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CorridorSegmentKind):
            raise TypeError(
                f"CorridorSegment.kind must be CorridorSegmentKind; "
                f"got {type(self.kind).__name__}"
            )
        if not isinstance(self.start, CorridorEndpoint):
            raise TypeError(
                f"CorridorSegment.start must be CorridorEndpoint; "
                f"got {type(self.start).__name__}"
            )
        if not isinstance(self.end, CorridorEndpoint):
            raise TypeError(
                f"CorridorSegment.end must be CorridorEndpoint; "
                f"got {type(self.end).__name__}"
            )
        if not isinstance(self.runs_along, PlotOrientation):
            raise TypeError(
                f"CorridorSegment.runs_along must be PlotOrientation; "
                f"got {type(self.runs_along).__name__}"
            )

        # Width validations
        if self.constant_width_m <= 0:
            raise ValueError(
                f"CorridorSegment.constant_width_m must be > 0; "
                f"got {self.constant_width_m}"
            )
        if self.start_width_m <= 0:
            raise ValueError(
                f"CorridorSegment.start_width_m must be > 0; "
                f"got {self.start_width_m}"
            )
        if self.end_width_m <= 0:
            raise ValueError(
                f"CorridorSegment.end_width_m must be > 0; "
                f"got {self.end_width_m}"
            )
        if self.length_m <= 0:
            raise ValueError(
                f"CorridorSegment.length_m must be > 0; "
                f"got {self.length_m}"
            )
        if self.taper_zone_m < 0:
            raise ValueError(
                f"CorridorSegment.taper_zone_m must be >= 0; "
                f"got {self.taper_zone_m}"
            )

        # Axis-alignment check: exactly one coordinate differs
        sx, sy = self.start.point_m
        ex, ey = self.end.point_m
        dx = abs(ex - sx)
        dy = abs(ey - sy)
        eps = DEFAULT_EPSILON_M
        if dx > eps and dy > eps:
            raise ValueError(
                f"CorridorSegment must be axis-aligned (start and end differ "
                f"in exactly one coordinate); got dx={dx}, dy={dy}"
            )
        if dx <= eps and dy <= eps:
            raise ValueError(
                f"CorridorSegment must have non-zero length; got "
                f"start={self.start.point_m}, end={self.end.point_m}"
            )

        # length_m matches the differing-axis distance
        expected_length = max(dx, dy)
        if abs(self.length_m - expected_length) > eps:
            raise ValueError(
                f"CorridorSegment.length_m ({self.length_m}) must match "
                f"|end - start| in the differing axis ({expected_length})"
            )

        # Count tapers: a taper exists at an end iff the end's width differs
        # from the constant_width. (Per § 14.20: a segment with both ends at
        # constant_width has zero effective tapers; a segment with one
        # junction end has one effective taper; a segment between two
        # junctions may have two.)
        start_has_taper = abs(self.start_width_m - self.constant_width_m) > eps
        end_has_taper = abs(self.end_width_m - self.constant_width_m) > eps
        n_tapers = int(start_has_taper) + int(end_has_taper)

        # Invariant 16: per-side bound — taper_zone_m ≤ length_m / 2.
        # (Spec § 4.3.1 truncation fallback ensures this; validator confirms.)
        if self.taper_zone_m > self.length_m / 2.0 + eps:
            raise ValueError(
                f"CorridorSegment: taper_zone_m ({self.taper_zone_m}) "
                f"must be <= length_m / 2 ({self.length_m / 2.0}) "
                f"(Invariant 16)"
            )

        # Invariant 20: constant_middle_length ≥ length_m / 2
        # (counting only the actual tapers, not 2× always)
        total_taper_length = n_tapers * self.taper_zone_m
        constant_middle = self.length_m - total_taper_length
        if constant_middle < self.length_m / 2.0 - eps:
            raise ValueError(
                f"CorridorSegment: constant_middle_length "
                f"({constant_middle}) must be >= length_m / 2 "
                f"({self.length_m / 2.0}) (Invariant 20). "
                f"n_tapers={n_tapers}, taper_zone_m={self.taper_zone_m}, "
                f"length_m={self.length_m}"
            )

    @property
    def has_taper(self) -> bool:
        """True iff either end's width differs from the constant middle."""
        eps = DEFAULT_EPSILON_M
        return (
            abs(self.start_width_m - self.constant_width_m) > eps
            or abs(self.end_width_m - self.constant_width_m) > eps
        )

    @property
    def constant_middle_length_m(self) -> float:
        """Length of the constant-width middle region. Counts only ends
        that actually have a taper (where width differs from constant)."""
        eps = DEFAULT_EPSILON_M
        start_has_taper = abs(self.start_width_m - self.constant_width_m) > eps
        end_has_taper = abs(self.end_width_m - self.constant_width_m) > eps
        n_tapers = int(start_has_taper) + int(end_has_taper)
        return max(0.0, self.length_m - n_tapers * self.taper_zone_m)


# =============================================================================
# Grid alignment + provenance
# =============================================================================


@dataclass(frozen=True)
class GridAlignmentReport:
    """How well the corridor aligns to the C7 grid. Per § 3 / § 14.21."""
    quantization_used: WidthQuantization
    edges_aligned_count: int
    edges_total_count: int
    tapered_edges_count: int
    grid_alignment_score: float
    chosen_width_fraction: float | None = None
    chosen_bay_axis: str | None = None
    envelope_symmetry_score: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.quantization_used, WidthQuantization):
            raise TypeError(
                f"GridAlignmentReport.quantization_used must be "
                f"WidthQuantization; got {type(self.quantization_used).__name__}"
            )
        if self.edges_aligned_count < 0:
            raise ValueError(
                f"GridAlignmentReport.edges_aligned_count must be >= 0; "
                f"got {self.edges_aligned_count}"
            )
        if self.edges_total_count < 0:
            raise ValueError(
                f"GridAlignmentReport.edges_total_count must be >= 0; "
                f"got {self.edges_total_count}"
            )
        if self.tapered_edges_count < 0:
            raise ValueError(
                f"GridAlignmentReport.tapered_edges_count must be >= 0; "
                f"got {self.tapered_edges_count}"
            )
        if not (0.0 <= self.grid_alignment_score <= 1.0 + GEOMETRIC_M):
            raise ValueError(
                f"GridAlignmentReport.grid_alignment_score must be in [0, 1]; "
                f"got {self.grid_alignment_score}"
            )
        if self.chosen_bay_axis is not None and self.chosen_bay_axis not in ("x", "y"):
            raise ValueError(
                f"GridAlignmentReport.chosen_bay_axis must be 'x' or 'y' or None; "
                f"got {self.chosen_bay_axis!r}"
            )


# =============================================================================
# Config (defined here so provenance can hold a snapshot)
# =============================================================================


# =============================================================================
# B-109 — Narrow-plot graceful fallback recommendation
# =============================================================================


@dataclass(frozen=True)
class NarrowPlotRecommendation:
    """Returned by `design_corridors_safe` for a candidate whose plot is
    too narrow for any GRID_FRACTION corridor candidate at the configured
    regulatory minimum.

    Per B-109 (closed S55): the strict `design_corridors` path raises
    `CorridorTooNarrowError` (correct for pipelines that need strict
    feasibility). The new `design_corridors_safe` path substitutes one
    of these objects for that candidate so the caller can keep
    processing siblings AND surface a structured recommendation to the
    user (different topology, override the regulatory minimum, or skip
    the corridor on this candidate).

    Fields:
      candidate_index: position in the input tuple — preserves the
                       position-paired contract from § 14.3.
      message: human-readable diagnostic, suitable for direct UI display.
      bay_min_m / regulatory_min_width_m: numeric context (mirrors the
                       CorridorTooNarrowError attribute names so callers
                       can build either branch with the same code).
      candidate_widths_m: the GRID_FRACTION × bay_min product set the
                       width selector considered, if available.
      suggested_alternative_topologies: tuple of TopologyKind names the
                       caller might retry (e.g., "STRIP" for narrow plots).
      suggested_user_action: short caller-facing guidance — one of
                       "increase_plot_width", "lower_regulatory_min",
                       "drop_corridor_topology", "switch_to_strip".
    """
    candidate_index: int
    message: str
    bay_min_m: float | None = None
    regulatory_min_width_m: float | None = None
    candidate_widths_m: tuple[float, ...] | None = None
    suggested_alternative_topologies: tuple[str, ...] = ()
    suggested_user_action: str = "increase_plot_width"


@dataclass(frozen=True)
class CorridorDesignConfig:
    """Tunables for C8. All have safe defaults; callers can omit. Per § 3.

    B-108 (partial closure S55): `regulatory_min_width_m` default of
    0.9m is sourced from NBC 2016 Part 3 § 14 interior-residential
    corridor minimum (single-dwelling unit, < 30m corridor length).
    NBC 2016 Part 4 § 4.3 fire-egress paths can require 1.0m+ for
    longer corridors or multi-unit dwellings — those callers should
    pass a higher override. Full PDF verification (with architect
    sign-off) is queued under B-150 / B-238; see
    `05_integrity_check/B108_PARTIAL_NBC_VERIFICATION_S55.md`.
    """
    regulatory_min_width_m: float = 0.9
    comfort_target_width_m: float = 1.2
    entry_stub_width_m: float = 1.0
    width_quantization: WidthQuantization = WidthQuantization.GRID_FRACTIONS
    fallback_snap_tolerance_m: float = 0.15
    junction_angle_tolerance_deg: float = 0.0
    epsilon_m: float = DEFAULT_EPSILON_M
    courtyard_loop_inner_clear_m: float = 1.0
    consumption_band_thresholds: tuple[float, float] = (0.12, 0.20)

    # NEW v0.4 fields
    width_propagation: WidthPropagation = WidthPropagation.JUNCTION_LOCAL_ONLY
    taper_zone_m_default: float | None = None
    under_comfort_penalty_ratio: float = DEFAULT_UNDER_COMFORT_PENALTY_RATIO
    envelope_symmetry_weight: float = 0.3
    band_priority_order: tuple[ZoneBand, ...] | None = None

    def __post_init__(self) -> None:
        if self.regulatory_min_width_m <= 0:
            raise ValueError(
                f"CorridorDesignConfig.regulatory_min_width_m must be > 0; "
                f"got {self.regulatory_min_width_m}"
            )
        if self.comfort_target_width_m < self.regulatory_min_width_m:
            raise ValueError(
                f"CorridorDesignConfig.comfort_target_width_m "
                f"({self.comfort_target_width_m}) must be >= "
                f"regulatory_min_width_m ({self.regulatory_min_width_m})"
            )
        if self.entry_stub_width_m <= 0:
            raise ValueError(
                f"CorridorDesignConfig.entry_stub_width_m must be > 0; "
                f"got {self.entry_stub_width_m}"
            )
        if not isinstance(self.width_quantization, WidthQuantization):
            raise TypeError(
                f"CorridorDesignConfig.width_quantization must be "
                f"WidthQuantization; got {type(self.width_quantization).__name__}"
            )
        if not isinstance(self.width_propagation, WidthPropagation):
            raise TypeError(
                f"CorridorDesignConfig.width_propagation must be "
                f"WidthPropagation; got {type(self.width_propagation).__name__}"
            )
        if self.epsilon_m <= 0:
            raise ValueError(
                f"CorridorDesignConfig.epsilon_m must be > 0; "
                f"got {self.epsilon_m}"
            )
        if not (0.0 <= self.junction_angle_tolerance_deg <= 90.0):
            raise ValueError(
                f"CorridorDesignConfig.junction_angle_tolerance_deg must be "
                f"in [0, 90]; got {self.junction_angle_tolerance_deg}"
            )
        if not (0.0 <= self.under_comfort_penalty_ratio):
            raise ValueError(
                f"CorridorDesignConfig.under_comfort_penalty_ratio must be "
                f">= 0; got {self.under_comfort_penalty_ratio}"
            )
        if not (0.0 <= self.envelope_symmetry_weight):
            raise ValueError(
                f"CorridorDesignConfig.envelope_symmetry_weight must be "
                f">= 0; got {self.envelope_symmetry_weight}"
            )
        if self.taper_zone_m_default is not None and self.taper_zone_m_default < 0:
            raise ValueError(
                f"CorridorDesignConfig.taper_zone_m_default must be None or >= 0; "
                f"got {self.taper_zone_m_default}"
            )
        # consumption band thresholds: (low_high_boundary, medium_high_boundary)
        thr = self.consumption_band_thresholds
        if (
            not isinstance(thr, tuple)
            or len(thr) != 2
            or not all(isinstance(x, (int, float)) for x in thr)
        ):
            raise TypeError(
                f"CorridorDesignConfig.consumption_band_thresholds must be a "
                f"2-tuple of floats; got {thr!r}"
            )
        if not (0.0 <= thr[0] <= thr[1] <= 1.0):
            raise ValueError(
                f"CorridorDesignConfig.consumption_band_thresholds must be a "
                f"sorted 2-tuple in [0, 1]; got {thr}"
            )

    def effective_band_priority_order(self) -> tuple[ZoneBand, ...]:
        """Return the configured priority order or the default."""
        if self.band_priority_order is not None:
            return tuple(self.band_priority_order)
        return DEFAULT_BAND_PRIORITY_ORDER


# =============================================================================
# Provenance
# =============================================================================


@dataclass(frozen=True)
class CorridorProvenance:
    """Per § 10. Snapshot of the rule trace + diagnostics."""
    derived_at: float
    oriented_candidate_trace_id: str
    grid_trace_id: str
    config_snapshot: CorridorDesignConfig
    rule_trace: tuple[str, ...]
    fallback_used: bool
    envelope_area_consumed_m2: float
    envelope_area_fraction: float
    additive_sum_m2: float
    overlap_area_m2: float

    def __post_init__(self) -> None:
        if not isinstance(self.config_snapshot, CorridorDesignConfig):
            raise TypeError(
                f"CorridorProvenance.config_snapshot must be "
                f"CorridorDesignConfig; got {type(self.config_snapshot).__name__}"
            )
        if not isinstance(self.rule_trace, tuple):
            raise TypeError(
                f"CorridorProvenance.rule_trace must be a tuple; "
                f"got {type(self.rule_trace).__name__}"
            )
        if self.envelope_area_consumed_m2 < 0:
            raise ValueError(
                f"CorridorProvenance.envelope_area_consumed_m2 must be >= 0; "
                f"got {self.envelope_area_consumed_m2}"
            )
        if not (0.0 <= self.envelope_area_fraction <= 1.0 + GEOMETRIC_M):
            raise ValueError(
                f"CorridorProvenance.envelope_area_fraction must be in [0, 1]; "
                f"got {self.envelope_area_fraction}"
            )


# =============================================================================
# Path + designed candidate
# =============================================================================


@dataclass(frozen=True)
class CorridorPath:
    """The complete corridor design for one candidate. Per § 3.

    NEW v0.2: ``has_corridor`` flag. Invariants split into ALL-PATHS
    (apply unconditionally) and HAS-CORRIDOR-ONLY (apply only when
    ``has_corridor == True``) per § 4.6.

    NEW v0.3: ``consumption_band`` advisory metadata.
    """
    has_corridor: bool
    segments: tuple[CorridorSegment, ...]
    envelopes: tuple[ZoneBandEnvelope, ...]
    total_length_m: float
    total_area_m2: float
    consumption_band: ConsumptionBand
    connectivity_type: ConnectivityType
    grid_alignment: GridAlignmentReport

    def __post_init__(self) -> None:
        if not isinstance(self.segments, tuple):
            raise TypeError(
                f"CorridorPath.segments must be a tuple; "
                f"got {type(self.segments).__name__}"
            )
        if not isinstance(self.envelopes, tuple):
            raise TypeError(
                f"CorridorPath.envelopes must be a tuple; "
                f"got {type(self.envelopes).__name__}"
            )
        for i, s in enumerate(self.segments):
            if not isinstance(s, CorridorSegment):
                raise TypeError(
                    f"CorridorPath.segments[{i}] must be CorridorSegment; "
                    f"got {type(s).__name__}"
                )
        for i, e in enumerate(self.envelopes):
            if not isinstance(e, ZoneBandEnvelope):
                raise TypeError(
                    f"CorridorPath.envelopes[{i}] must be ZoneBandEnvelope; "
                    f"got {type(e).__name__}"
                )
        if not isinstance(self.consumption_band, ConsumptionBand):
            raise TypeError(
                f"CorridorPath.consumption_band must be ConsumptionBand; "
                f"got {type(self.consumption_band).__name__}"
            )
        if not isinstance(self.connectivity_type, ConnectivityType):
            raise TypeError(
                f"CorridorPath.connectivity_type must be ConnectivityType; "
                f"got {type(self.connectivity_type).__name__}"
            )
        if not isinstance(self.grid_alignment, GridAlignmentReport):
            raise TypeError(
                f"CorridorPath.grid_alignment must be GridAlignmentReport; "
                f"got {type(self.grid_alignment).__name__}"
            )
        if self.total_length_m < 0:
            raise ValueError(
                f"CorridorPath.total_length_m must be >= 0; "
                f"got {self.total_length_m}"
            )
        if self.total_area_m2 < 0:
            raise ValueError(
                f"CorridorPath.total_area_m2 must be >= 0; "
                f"got {self.total_area_m2}"
            )
        if not self.has_corridor and len(self.segments) != 0:
            raise ValueError(
                f"CorridorPath: has_corridor=False but segments is non-empty "
                f"(len={len(self.segments)})"
            )


@dataclass(frozen=True)
class CorridorZone:
    """An axis-aligned rectangle reserving a region of the envelope for
    corridor occupancy. Derived from CorridorSegment geometry for
    downstream C12 consumption.

    Per ``B-C8-CORRIDOR-ZONE-CONTRACT`` (C12 v0.2 Amendment A6,
    LOCKED via S43 directive — "Let's do the dependencies on c8&c9
    and code that also"):

    C12 marks each CorridorZone rectangle as occupied (cannot be
    placed-into) before per-floor SFP runs, and verifies room
    reachability via a BFS over the placed rooms + zones graph.

    Fields use SAME conventions as C12.PlacedRoom:
      - ``(x_m, y_m)`` = bottom-left corner in envelope coordinates (m)
      - ``width_m`` / ``depth_m`` = extents along x / y axes

    For tapered corridor segments, the zone uses
    ``max(start_width, constant_width, end_width)`` so reservation is
    conservative (over-reserve rather than under-reserve). Accurate
    taper modelling is filed as ``B-C8-TAPER-ACCURATE-ZONES`` post-v1.
    """
    x_m: float
    y_m: float
    width_m: float
    depth_m: float
    source_segment_kind: "CorridorSegmentKind"

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise ValueError(
                f"CorridorZone requires positive extents; "
                f"got width={self.width_m}, depth={self.depth_m}."
            )


def _corridor_segment_to_zone(segment: "CorridorSegment") -> "CorridorZone":
    """Derive a CorridorZone (axis-aligned rectangle) from a single
    CorridorSegment. Conservative on tapered segments.

    A segment running ALONG axis A has length on A and width on the
    perpendicular axis. The zone reserves
    ``max(start_width, constant_width, end_width)`` on the perpendicular
    axis centred on the segment's centreline.
    """
    sx, sy = segment.start.point_m
    ex, ey = segment.end.point_m
    max_w = max(
        segment.start_width_m,
        segment.constant_width_m,
        segment.end_width_m,
    )
    # Axis-aligned by invariant: segments differ in exactly one coord.
    if abs(ex - sx) > abs(ey - sy):
        # Runs along x; width is on y axis.
        x_min = min(sx, ex)
        x_max = max(sx, ex)
        y_centre = sy  # sy == ey by axis-alignment
        zone_w = x_max - x_min
        zone_d = max_w
        x0 = x_min
        y0 = y_centre - max_w / 2.0
    else:
        # Runs along y; width is on x axis.
        y_min = min(sy, ey)
        y_max = max(sy, ey)
        x_centre = sx  # sx == ex by axis-alignment
        zone_w = max_w
        zone_d = y_max - y_min
        x0 = x_centre - max_w / 2.0
        y0 = y_min
    return CorridorZone(
        x_m=x0,
        y_m=y0,
        width_m=zone_w,
        depth_m=zone_d,
        source_segment_kind=segment.kind,
    )


@dataclass(frozen=True)
class CorridorDesignedCandidate:
    """One C6 OrientedCandidate paired with its C8 corridor design. Per § 3."""
    oriented_candidate: OrientedCandidate
    corridor_path: CorridorPath
    provenance: CorridorProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.oriented_candidate, OrientedCandidate):
            raise TypeError(
                f"CorridorDesignedCandidate.oriented_candidate must be "
                f"OrientedCandidate; got {type(self.oriented_candidate).__name__}"
            )
        if not isinstance(self.corridor_path, CorridorPath):
            raise TypeError(
                f"CorridorDesignedCandidate.corridor_path must be CorridorPath; "
                f"got {type(self.corridor_path).__name__}"
            )
        if not isinstance(self.provenance, CorridorProvenance):
            raise TypeError(
                f"CorridorDesignedCandidate.provenance must be "
                f"CorridorProvenance; got {type(self.provenance).__name__}"
            )

    @property
    def corridor_zones(self) -> tuple["CorridorZone", ...]:
        """Derived view: each CorridorSegment converted to a
        CorridorZone axis-aligned rectangle.

        Per ``B-C8-CORRIDOR-ZONE-CONTRACT`` (LOCKED via S43 directive).

        Canonical ordering: sorted lex-ASC by
        ``(x_m, y_m, width_m, depth_m)`` so the C12 reservation
        order is deterministic.

        Returns an empty tuple when ``has_corridor`` is False.
        """
        if not self.corridor_path.has_corridor:
            return ()
        zones = tuple(
            _corridor_segment_to_zone(s) for s in self.corridor_path.segments
        )
        # Canonical lex-ASC ordering for deterministic C12 consumption.
        return tuple(
            sorted(zones, key=lambda z: (z.x_m, z.y_m, z.width_m, z.depth_m))
        )


__all__ = [
    # Constants
    "GRID_FRACTION_CANDIDATES",
    "ALLOWED_JUNCTION_ANGLES_DEG",
    "DEFAULT_EPSILON_M",
    "DEFAULT_BAND_PRIORITY_ORDER",
    "DEFAULT_UNDER_COMFORT_PENALTY_RATIO",
    "CORRIDOR_ZONE_SCHEMA_VERSION",  # NEW v0.1 B-C8-SCHEMA-VERSION-CONSTANT
    # Enums
    "CorridorSegmentKind",
    "CorridorEndpointKind",
    "WidthQuantization",
    "WidthPropagation",
    "ConsumptionBand",
    # Dataclasses
    "ZoneBandEnvelope",
    "CorridorEndpoint",
    "CorridorSegment",
    "GridAlignmentReport",
    "CorridorDesignConfig",
    "CorridorProvenance",
    "CorridorPath",
    "CorridorDesignedCandidate",
    "CorridorZone",  # NEW v0.1 B-C8-CORRIDOR-ZONE-CONTRACT
]


# B-C8-SCHEMA-VERSION-CONSTANT v0.1 LOCKED via S43 directive
# ("Lock it and start coding" — interpreted as combined LOCK + code
# authorization following the same pattern as the routed C8/C9
# amendments earlier in S43).
#
# Consumed by C12 v0.4-A1 schema-version probe at ingress:
# C12 asserts CORRIDOR_ZONE_SCHEMA_VERSION == 1 at Phase 0 step 4
# to catch semantic-incompatible upstream evolution.
CORRIDOR_ZONE_SCHEMA_VERSION: Final[int] = 1
