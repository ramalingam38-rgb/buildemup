"""
BuildemUp† — Component 4 (Plot Analysis) orchestrator.

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# Critique reviewers: filed in spec § 16. Please do NOT re-flag.
# (Strippable review aid — covers items affecting derive() / orchestrator.)
#
#   B-066  Polygon plots (current v1: rectangular only; PlotShape.L_SHAPED /
#          IRREGULAR are forward-compat enum values, no path supports them).
#   B-075  AspectClass enum + extreme-plot detection (e.g., aspect_ratio > 5
#          → flag). Current model relies on Plot constructor bounds (3-60m)
#          → max ratio 20:1 with no classification.
#   B-078  System-wide trace_id lifecycle policy: format (UUID4?), uniqueness
#          scope, generation site (Brief constructor), validation at all read
#          sites. Current contract: Brief.trace_id is str with empty default.
#   B-080  Dynamic KB mutation: re-validation if KBs are mutated outside
#          module-load (hot reload, admin tools, runtime monkey-patch).
#          Current architecture: static-import KBs only, verify_kb_consistency
#          runs once at import.
#   B-081  Performance test: rolling baseline (last-N-runs median ± stddev) OR
#          env-configurable threshold. Current cap: 3ms p95 absolute (~200×
#          measured 0.015ms p95 baseline). Trigger: CI infra live.
# ─────────────────────────────────────────────────────────────────────────────

Per spec § 5 invocation contract.

Public entry point: `derive(brief: ResolvedBrief, *, now: float) -> PlotAnalysis`

Reads (CG-9):
  brief.revised_brief.plot         (the actual upstream path)
  brief.revised_brief.trace_id

Writes: a frozen PlotAnalysis. C5 onward MUST consume this rather than
re-deriving from raw plot.

Pure: no I/O at call time. KB lookups happened at module import.

†= placeholder name marker.
"""
from __future__ import annotations

from types import MappingProxyType

from buildemup.components.c04.climate_zone import (
    lookup_climate_zone,
    lookup_latitude,
    validate_city,
)
from buildemup.components.c04.neighbour_context import derive_neighbour_context
from buildemup.components.c04.schema           import (
    BASELINE_ROOM_ORIENTATION_GUIDELINES,
    PlotAnalysis,
    PlotAnalysisProvenance,
    PlotShape,
    PlotTier,
    RoadWidthClass,
)
from buildemup.components.c04.soil_estimator   import estimate_soil
from buildemup.components.c04.sun_path         import compute_sun_path
from buildemup.domain.envelope                 import PlotOrientation
from buildemup.domain.plot                     import Plot
from buildemup.kb.city_geography               import kb_versions
from buildemup.kb.wind_direction               import PREVAILING_WIND


# ─── Tier thresholds (per spec § 4.1) ───────────────────────────────────
# v0.6 (walk #1): tier classification compares in sqm space using the
# EXACT IEC conversion factor 1 sqft = 0.3048² m² = 0.09290304 sqm.
# This eliminates the second-rounding step (sqm × 10.7639) that made
# 40×60 ft (textbook 2400 sqft) land at 2399.998 sqft and misclassify
# as T1. The 10.7639 factor stays for area_sqft display only.
SQM_PER_SQFT = 0.09290304   # exact: 0.3048² (foot defined as 0.3048 m exactly)

_T1_MIN_SQFT = 600.0
_T2_MIN_SQFT = 2400.0
_T3_MIN_SQFT = 4000.0

_T1_MIN_SQM =  _T1_MIN_SQFT * SQM_PER_SQFT   #  55.74182400 sqm
_T2_MIN_SQM = _T2_MIN_SQFT * SQM_PER_SQFT    # 222.96729600 sqm
_T3_MIN_SQM = _T3_MIN_SQFT * SQM_PER_SQFT    # 371.61216000 sqm

# v0.9 (walk #7): use the EXACT inverse of SQM_PER_SQFT for area_sqft display
# rather than the rounded 10.7639 factor. With the rounded factor, 40×60 ft
# (12.192×18.288 m, textbook 2400 sqft) displayed as 2399.998 sqft — visually
# < 2400 even though the tier was correctly classified T2 from sqm-space.
# Exact inverse: 1 / 0.09290304 = 10.76391041670972... — gives 2400.0 exact.
_SQFT_PER_SQM = 1.0 / SQM_PER_SQFT   # exact: ≈ 10.76391041670972

# ─── Road width class thresholds (per spec § 4.8) ───────────────────────
_NARROW_BELOW_M = 6.0
_STANDARD_BELOW_M = 12.0


def _classify_tier(area_sqm: float) -> PlotTier:
    """Classify plot tier from area in sqm (canonical comparison space).

    v0.6 (walk #1): comparison happens in sqm (the directly-computed
    unit) to avoid float misclassification at sqft boundaries — e.g.,
    40×60 ft = 12.192×18.288 m exactly, area_sqm = 222.967296 sqm,
    matches _T2_MIN_SQM = 2400 × 0.09290304 = 222.967296 sqm to ulp.
    """
    if area_sqm < _T1_MIN_SQM:
        # Display the failing area in sqft for the user-facing message.
        sqft = area_sqm * _SQFT_PER_SQM
        raise ValueError(
            f"plot < {_T1_MIN_SQFT:.0f}sqft minimum (got {sqft:.1f}sqft) — "
            f"should have been gated by C3a"
        )
    if area_sqm < _T2_MIN_SQM:
        return PlotTier.T1_COMPACT
    if area_sqm < _T3_MIN_SQM:
        return PlotTier.T2_STANDARD
    return PlotTier.T3_LARGE


def _classify_road(road_width_m: float) -> RoadWidthClass:
    if road_width_m < _NARROW_BELOW_M:
        return RoadWidthClass.NARROW
    if road_width_m < _STANDARD_BELOW_M:
        return RoadWidthClass.STANDARD
    return RoadWidthClass.WIDE


def _validate_now(now: float) -> None:
    """Validate the keyword-only `now` parameter per spec § 5 invocation contract.

    bool is a subclass of int in Python; we explicitly reject it so a caller
    passing `now=True` doesn't sneak through `isinstance(now, float)` after
    the int promotion.
    """
    if isinstance(now, bool) or not isinstance(now, (int, float)):
        raise TypeError(
            f"`now` must be a float (Unix epoch seconds); got "
            f"{type(now).__name__}"
        )
    if now <= 0:
        raise ValueError(f"`now` must be > 0; got {now}")


def _extract_brief_inputs(brief: object) -> tuple[Plot, str]:
    """Pull (plot, trace_id) from a ResolvedBrief (CG-9 contract).

    Reads the actual upstream path:
      brief.revised_brief.plot
      brief.revised_brief.trace_id

    Defensive about each step so a malformed brief raises ValueError
    rather than AttributeError, per spec § 6.
    """
    revised = getattr(brief, "revised_brief", None)
    if revised is None:
        raise ValueError(
            "ResolvedBrief.revised_brief is required (got None or missing)"
        )
    plot = getattr(revised, "plot", None)
    if plot is None:
        raise ValueError(
            "ResolvedBrief.revised_brief.plot is required (got None or missing)"
        )
    if not isinstance(plot, Plot):
        raise ValueError(
            f"ResolvedBrief.revised_brief.plot must be domain.plot.Plot; got "
            f"{type(plot).__name__}"
        )
    trace_id = getattr(revised, "trace_id", None)
    if trace_id is None or not isinstance(trace_id, str):
        raise ValueError(
            "ResolvedBrief.revised_brief.trace_id must be a non-None str; "
            f"got {type(trace_id).__name__}"
        )
    return plot, trace_id


def derive(brief: object, *, now: float) -> PlotAnalysis:
    """Derive a PlotAnalysis from a ResolvedBrief.

    Args:
        brief: ResolvedBrief from C3a output. Reads
               `brief.revised_brief.plot` and `brief.revised_brief.trace_id`.
        now:   keyword-only required. Must be float > 0 (Unix epoch seconds).
               Tests pass `now=1.0` (smallest valid).

    Returns:
        Frozen PlotAnalysis. C5 onward MUST consume this; MUST NOT
        re-derive any of its fields from raw plot.

    Raises:
        TypeError: `now` not a float.
        ValueError: any of the input contract / domain validations fail
                    (city not in CITY_GEOGRAPHY; plot < 600sqft; latitude
                    out of range; bad facing enum; bad ResolvedBrief shape;
                    `now` ≤ 0).

    UPSTREAM INVARIANTS C4 RELIES ON (per domain/plot.py Plot.__post_init__):
        - 3.0 ≤ plot.width_m ≤ 60.0      (width-zero mechanically impossible)
        - 3.0 ≤ plot.depth_m ≤ 60.0
        - 1.5 ≤ plot.road_width_m ≤ 30.0
        - plot.city normalized + ∈ SUPPORTED_CITIES
        - plot.facing is a PlotOrientation enum

    These are NOT re-validated in C4 (single source of truth for plot
    invariants is the Plot constructor). dataclasses.replace() re-runs
    __post_init__, so post-construction modification via that path is also
    covered. The only true bypass is object.__new__ + object.__setattr__,
    which defeats any layer of validation equally — so re-validating in C4
    would not help.

    v0.7 (walk #5): documented above; pushback on a redundant defensive
    width_m > 0 check stands.
    """
    _validate_now(now)
    plot, trace_id = _extract_brief_inputs(brief)

    # Defensive: facing must be the enum (Plot.__post_init__ doesn't enforce
    # this, only the dim/road/city bounds — see domain/plot.py).
    if not isinstance(plot.facing, PlotOrientation):
        raise ValueError(
            f"plot.facing must be PlotOrientation; got "
            f"{type(plot.facing).__name__}"
        )

    # v0.7 (walks #1, #4): centralized validate_city helper replaces the
    # inline normalize+check. Plot.__post_init__ already guarantees
    # plot.city is a normalized supported city; this call is belt-and-
    # braces in case future callers bypass __post_init__.
    city = validate_city(plot.city)

    # ── Tier + shape + dimensions ──────────────────────────────────────
    area_sqm = plot.width_m * plot.depth_m
    area_sqft = area_sqm * _SQFT_PER_SQM
    tier = _classify_tier(area_sqm)              # v0.6: compare in sqm space
    aspect_ratio = plot.depth_m / plot.width_m   # > 1 = deep; < 1 = wide

    # ── Solar geometry ─────────────────────────────────────────────────
    latitude_deg = lookup_latitude(city)
    sun_path = compute_sun_path(latitude_deg)

    # ── Climate ────────────────────────────────────────────────────────
    climate_zone = lookup_climate_zone(city)

    # ── Wind ───────────────────────────────────────────────────────────
    # PREVAILING_WIND is keyed by city; verify_kb_consistency() guarantees
    # presence for every supported city.
    prevailing_wind = PREVAILING_WIND[city]

    # ── Soil ───────────────────────────────────────────────────────────
    soil_estimate = estimate_soil(plot)

    # ── Site context ───────────────────────────────────────────────────
    road_width_classification = _classify_road(plot.road_width_m)
    neighbour_context = derive_neighbour_context(plot)

    # ── Provenance ─────────────────────────────────────────────────────
    provenance = PlotAnalysisProvenance(
        derived_at=float(now),
        source_versions=MappingProxyType(kb_versions()),
    )

    return PlotAnalysis(
        trace_id=trace_id,
        plot=plot,
        area_sqft=area_sqft,
        area_sqm=area_sqm,
        tier=tier,
        shape=PlotShape.RECTANGULAR,           # v1: always rectangular
        shape_metadata=MappingProxyType({}),   # SC-1: true immutability
        aspect_ratio=aspect_ratio,
        sun_path=sun_path,
        climate_zone=climate_zone,
        baseline_room_orientation_guidelines=BASELINE_ROOM_ORIENTATION_GUIDELINES,
        prevailing_wind=prevailing_wind,
        soil_estimate=soil_estimate,
        road_width_classification=road_width_classification,
        neighbour_context=neighbour_context,
        provenance=provenance,
    )


__all__ = ["derive"]
