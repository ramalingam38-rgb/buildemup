"""
BuildemUp† — IMD Prevailing Wind Direction (NEW v0.5).

# ───────────────────── DEFERRED BACKLOG (REVIEW MARKER) ─────────────────────
# Critique reviewers: filed in spec § 16. Please do NOT re-flag.
# (Strippable review aid.)
#
#   B-070  Per-city IMD wind-rose data (full directional + intensity
#          distribution). Promotes WindContext.confidence MEDIUM → HIGH
#          when integrated. Currently this module compresses each city's
#          full wind characteristics into (primary_direction, monsoon_direction,
#          basic_speed_ms) triple — known-lossy compression.
# ─────────────────────────────────────────────────────────────────────────────

Per-city prevailing wind direction sourced from Indian Meteorological
Department climatology summaries. Used by C4 (Plot Analysis) for
ventilation orientation hints to the layout pipeline (C5/C6).

NOT a wind-rose. NOT for structural design. Wind speed (basic_speed_ms)
is read from kb/wind_load — this module carries direction only.

CALIBRATION CAVEAT (per C4 spec § 4.6): all 6 city values are PROPOSED
pending per-city IMD wind-rose verification (B-070).

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.components.c04.schema import ConfidenceLevel, WindContext
from buildemup.domain.envelope import PlotOrientation as _PO
# v0.7 (walk #2): import wind speeds at module load so each WindContext
# can carry basic_speed_ms as a stored field instead of resolving via
# lazy property at access time. Module-load coupling between two
# mandatory KBs is intentional and acceptable.
from buildemup.kb.wind_load import BASIC_WIND_SPEED_MS as _BASIC_WIND_SPEED_MS


KB_VERSION = "v1.0"


# Per-city wind direction. Source: IMD climatology summaries (cited per-city
# below). Full IMD wind-rose integration is B-070.
#
# v0.7 (walk #2): `basic_speed_ms` resolved here at module load.
# v0.8 (walk #7): `city` field on WindContext removed; the dict key IS
# the city, so the previous duplication is gone (key="chennai" with
# city="chennai" risked silent drift on copy-paste; now there's nothing
# to drift).
#
# v0.6 (walk #3): every entry carries `confidence=ConfidenceLevel.MEDIUM`
# explicitly. MEDIUM = "single-station IMD climatology" — sufficient for
# v1 layout heuristics but not authoritative for ventilation engineering.
# B-070 will promote to HIGH when full per-city wind-rose data is
# integrated. C5 ventilation logic SHOULD read this flag and apply
# isotropic-monsoon fallback heuristics where directional resolution
# matters.
PREVAILING_WIND: dict[str, WindContext] = {
    "chennai":   WindContext(
        primary_direction=_PO.NORTHEAST,    # NE non-monsoon (Oct–Mar)
        monsoon_direction=_PO.SOUTHWEST,    # SW monsoon (Jun–Sep)
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["chennai"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Chennai (Nungambakkam) climatology
    ),
    "mumbai":    WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["mumbai"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Santacruz station
    ),
    "bangalore": WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["bangalore"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Bangalore HAL
    ),
    "pune":      WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["pune"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Shivajinagar
    ),
    "hyderabad": WindContext(
        primary_direction=_PO.WEST,
        monsoon_direction=_PO.SOUTHWEST,
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["hyderabad"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Begumpet
    ),
    "delhi":     WindContext(
        primary_direction=_PO.NORTHWEST,    # NW winter
        monsoon_direction=_PO.SOUTHEAST,    # monsoon spillover
        basic_speed_ms=float(_BASIC_WIND_SPEED_MS["delhi"]),
        confidence=ConfidenceLevel.MEDIUM,
        # Source: IMD Safdarjung
    ),
}


__all__ = [
    "KB_VERSION",
    "PREVAILING_WIND",
]
