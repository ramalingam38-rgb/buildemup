"""Layout preview builder (S60 — drawings fallback).

The formal C16 drawing bundle requires a fully wall-adjacent layout
with doors (C13) and a circulation graph (C14). On the current named
fixtures, C12's slicing-tree produces rooms at non-adjacent anchors
(the documented `B-C12-EDGE-DENSITY` issue), so C13 can't place doors
and C16 lands STUB — meaning the UI shows no floorplan.

But C12 DOES produce a complete set of placed rooms with real
coordinates (x, y, width, depth, category). That's a drawable floor
plan in its own right — it just lacks the wall-adjacency that doors
need. This module extracts that placement (plus the C7 grid envelope
+ columns) into a small JSON-friendly `layout_preview` dict the
frontend can render directly as an SVG floorplan.

This is an HONEST preview: it shows exactly what the engine places
today. The rooms are positioned and sized by the real C9 sizing + C12
placement; only the inter-room wall sharing (needed for door routing)
is still being refined. The UI labels it as a "placement preview" so
nobody mistakes it for the final dimensioned permit drawing C16 will
eventually emit.
"""
from __future__ import annotations

from typing import Any, Optional

from buildemup.orchestration.phase_result import PhaseStatus


def _extract_grid(c07_payload: Any) -> Any | None:
    """Pull the Grid out of C7's payload (full-engine vs MVP-compat)."""
    if c07_payload is None:
        return None
    grid_attr = getattr(c07_payload, "grid", None)
    if grid_attr is not None:
        return grid_attr
    return c07_payload


def _round(value: Any, ndigits: int = 3) -> Optional[float]:
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def build_layout_preview(result: Any) -> Optional[dict]:
    """Build a draw-friendly layout dict from a MasterOrchestratorResult.

    Returns None when there's no C12 placement to draw (e.g. an
    upstream phase STUB-degraded before C12). Otherwise returns:

        {
          "envelope": {"width_m": float, "depth_m": float},
          "source": "c12_placement",
          "candidate_signature": str,
          "rooms": [
            {"room_id", "category", "x_m", "y_m", "width_m", "depth_m"},
            ...
          ],
          "columns": [{"grid_label", "x_m", "y_m"}, ...],
          "note": str,
        }

    The frontend renders `rooms` as colour-coded rects and `columns`
    as small squares, scaled to the envelope.
    """
    c12 = result.phase("c12_vertical_placement")
    if c12 is None or c12.status != PhaseStatus.OK or c12.payload is None:
        return None

    placed_candidates = getattr(c12.payload, "placed_candidates", ())
    if not placed_candidates:
        return None

    # Draw the first placed candidate (the orchestrator surfaces the
    # full ranked set; candidate 0 is representative for a preview).
    candidate = placed_candidates[0]
    placed_rooms = getattr(candidate, "placed_rooms", ())
    if not placed_rooms:
        return None

    rooms = [
        {
            "room_id": getattr(r, "room_id", ""),
            "category": getattr(r, "category", "other"),
            "x_m": _round(getattr(r, "x_m", 0.0)),
            "y_m": _round(getattr(r, "y_m", 0.0)),
            "width_m": _round(getattr(r, "width_m", 0.0)),
            "depth_m": _round(getattr(r, "depth_m", 0.0)),
        }
        for r in placed_rooms
    ]

    # Envelope + columns from the C7 grid.
    c07 = result.phase("c07_structural_grid")
    grid = _extract_grid(c07.payload) if c07 is not None else None
    envelope = {"width_m": None, "depth_m": None}
    columns: list[dict] = []
    if grid is not None:
        envelope = {
            "width_m": _round(getattr(grid, "envelope_width_m", None)),
            "depth_m": _round(getattr(grid, "envelope_depth_m", None)),
        }
        for c in getattr(grid, "columns", ()) or ():
            columns.append({
                "grid_label": getattr(c, "grid_label", ""),
                "x_m": _round(getattr(c, "x_m", 0.0)),
                "y_m": _round(getattr(c, "y_m", 0.0)),
            })

    # If the grid didn't give an envelope, derive a bounding box from
    # the rooms so the frontend can still scale the drawing.
    if envelope["width_m"] is None or envelope["depth_m"] is None:
        max_x = max((rm["x_m"] + rm["width_m"]) for rm in rooms)
        max_y = max((rm["y_m"] + rm["depth_m"]) for rm in rooms)
        envelope = {"width_m": _round(max_x), "depth_m": _round(max_y)}

    return {
        "source": "c12_placement",
        "candidate_signature": getattr(
            candidate, "source_refined_candidate_signature", "",
        ),
        "envelope": envelope,
        "rooms": rooms,
        "columns": columns,
        "note": (
            "Placement preview — room positions and sizes from the live "
            "C9 sizing + C12 placement engine. Inter-room wall sharing "
            "(needed for door routing and the formal C16 permit drawing) "
            "is still being refined (B-C12-EDGE-DENSITY). This shows what "
            "the engine places today, not the final dimensioned drawing."
        ),
    }


__all__ = ["build_layout_preview"]
