"""
BuildemUp — Setback preview endpoint (added v0.10.1 for feet-UI hint).

Tiny utility endpoint that takes a plot description and returns the
NBC/DCR-required setbacks. Used by the front-end to show a hint on the
setback step (Step 3) so users can see what the law requires before
they enter their own values.

This is a UI helper, not a feasibility check — it does NOT validate
anything, just exposes the same `compute_compliant_setbacks` logic that
C1 already uses internally.

Endpoint:
  POST /api/setback/preview

Request payload:
  {
    "city": "chennai",
    "plot_width_m": 9.14,
    "plot_depth_m": 12.19,
    "plot_type": "detached",
    "road_width_m": 9.14,
    "corner_plot": false,
    "second_road_width_m": null,
    "shared_side": null,
    "building_height_m": 9.0   // optional, default 9.0
  }

Response (200):
  {
    "ok": true,
    "front_m": 1.5, "rear_m": 1.5,
    "side_left_m": 1.5, "side_right_m": 1.5,
    "front_ft": 4.92, "rear_ft": 4.92,
    "side_left_ft": 4.92, "side_right_ft": 4.92,
    "source_authority": "TNCDBR 2019 (CMDA)",
    "tier_label": "small_medium_plot_100_to_300sqm"
  }

On bad input: 400 with {"ok": false, "errors": [...]}.
"""
from __future__ import annotations
import json
from typing import Any

from buildemup.domain.plot import Plot, PlotType
from buildemup.components.c01.setback_calculator import (
    compute_compliant_setbacks,
)


_FT_PER_M = 3.28084


def _m_to_ft(m: float) -> float:
    """Convert metres to feet, rounded to 2 decimal places."""
    return round(m * _FT_PER_M, 2)


def handle_setback_preview(request_body: bytes | str) -> tuple[int, dict]:
    """Handle POST /api/setback/preview.

    Returns:
        (status_code, response_dict).
    """
    # ── Parse JSON ────────────────────────────────────────────────────
    try:
        body_str = (request_body.decode("utf-8")
                    if isinstance(request_body, bytes) else request_body)
        payload: dict[str, Any] = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid JSON: {str(e)[:120]}"],
        }
    if not isinstance(payload, dict):
        return 400, {
            "ok": False,
            "errors": ["Request body must be a JSON object"],
        }

    # ── Build Plot domain object (Plot's __post_init__ handles
    # most input validation for us) ───────────────────────────────────
    try:
        plot_type_str = str(payload.get("plot_type", "detached")).lower()
        plot_type = PlotType(plot_type_str)
    except (ValueError, TypeError):
        return 400, {
            "ok": False,
            "errors": [
                f"Invalid plot_type: {payload.get('plot_type')!r}. "
                f"Must be one of: {[p.value for p in PlotType]}"
            ],
        }

    try:
        plot = Plot(
            width_m=float(payload["plot_width_m"]),
            depth_m=float(payload["plot_depth_m"]),
            facing=payload.get("plot_facing", "N"),
            city=str(payload["city"]),
            road_width_m=float(payload["road_width_m"]),
            plot_type=plot_type,
            corner_plot=bool(payload.get("corner_plot", False)),
            second_road_width_m=(
                float(payload["second_road_width_m"])
                if payload.get("second_road_width_m") is not None
                else None
            ),
            shared_side=payload.get("shared_side"),
        )
    except (KeyError, ValueError, TypeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid plot input: {str(e)[:200]}"],
        }

    # ── Compute setbacks ──────────────────────────────────────────────
    try:
        building_height_m = float(payload.get("building_height_m", 9.0))
        compliant, source_authority = compute_compliant_setbacks(
            plot, building_height_m=building_height_m,
        )
    except Exception as e:  # pragma: no cover — defensive
        return 500, {
            "ok": False,
            "errors": [
                f"Setback computation failed: {type(e).__name__}"
            ],
            "technical_detail": str(e)[:300],
        }

    # ── Build dual-unit response ──────────────────────────────────────
    return 200, {
        "ok": True,
        "front_m":      compliant.front_m,
        "rear_m":       compliant.rear_m,
        "side_left_m":  compliant.side_left_m,
        "side_right_m": compliant.side_right_m,
        "front_ft":      _m_to_ft(compliant.front_m),
        "rear_ft":       _m_to_ft(compliant.rear_m),
        "side_left_ft":  _m_to_ft(compliant.side_left_m),
        "side_right_ft": _m_to_ft(compliant.side_right_m),
        "source_authority": source_authority,
    }
