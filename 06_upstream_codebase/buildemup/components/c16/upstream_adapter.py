"""
C16 — upstream adapter
========================

Bridges concrete upstream contracts → C16 internal forms.

Per the v0.5 LOCKED spec, C16 consumes:
    - SelectionResult (from contracts.py)
    - MultiFloorPlacedCandidate (C12 — per-floor placements)
    - PlacedCandidate.placed_rooms (C12.PlacedRoom, metres)
    - PlacedCandidate.shared_edges (C12.SharedEdge, metres)
    - Per-floor Grid (C7 — columns + perimeter walls)
    - Per-floor WetZonePlan (C10 — plumbing risers)
    - Per-floor Door tuple (C13 — doors with position_along_edge)
    - CirculationGraphReport (C14 — advisory flags via R8 passthrough)
    - PlotAnalysis (C4 — plot area, climate, soil)
    - ProblemReport (C15 — per-candidate problem analysis)

All upstream types are READ-ONLY. C16 NEVER mutates them.

This module provides the input bundle type C16 consumes, plus the
unit-conversion + canonical ordering helpers Phase α needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


# We define UpstreamInputBundle with typed fields. Upstream concrete types
# are imported lazily (since the upstream codebase is reference-only here,
# and the runtime tests construct minimal duck-typed substitutes).
# At production time, downstream callers pass real instances of these.

@dataclass(frozen=True)
class UpstreamInputBundle:
    """The full upstream input C16 needs to render one DualDrawingBundle.

    Per the LOCKED spec, each rendering call consumes one
    MultiFloorPlacedCandidate plus the per-floor context produced by
    C7/C9/C10/C13/C14, plus the project-level PlotAnalysis (C4).

    Fields are typed as `Any` to keep this module decoupled from the
    upstream codebase (which lives under buildemup.components.c01–c15
    in the production tree, not in C16's local working tree). Phase α
    reads these duck-typed via the documented attribute names.

    DUCK-TYPED ATTRIBUTE EXPECTATIONS:
      multifloor_candidate.per_floor_placements →
            tuple[(floor_label: str, PlacedCandidate), ...]
      PlacedCandidate.placed_rooms → tuple of objects with
            (room_id, category, x_m, y_m, width_m, depth_m)
      PlacedCandidate.shared_edges → tuple of objects with
            (room_a_id, room_b_id, axis, overlap_start_m, overlap_end_m,
             overlap_length_m)
      PlacedCandidate.envelope_width_m, .envelope_depth_m

      grids_by_floor[label].columns → list of objects with
            (grid_label, x_m, y_m, on_perimeter)
      grids_by_floor[label].wall_segments → tuple of objects with
            (wall_id, axis, start_x_m, start_y_m, end_x_m, end_y_m,
             length_m, tags)
      grids_by_floor[label].envelope_width_m
      grids_by_floor[label].envelope_depth_m

      wet_zone_plans_by_floor[label].riser_groups → tuple of objects with
            (group_id, anchors, wet_room_ids)
      RiserGroup.anchors[0] → object with (wall_id, riser_anchor_xy,
                                            anchor_position_m)

      doors_by_floor[label] → tuple of Door objects with
            (room_a_id, room_b_id, axis, position_along_edge_m,
             clear_width_m, swing_direction, hinge_side,
             leaf_thickness_m, is_main_entry)

      circulation_reports_by_floor[label] → optional, list of
            objects with (flag_kind, affected_room_id, severity,
            explanation_template, deduplication_key)

      plot_analysis.area_sqm → float
      plot_analysis.trace_id → str

      far_permitted → float (from jurisdiction config, NOT C4)
      height_limit_m → float (from jurisdiction config)
      typical_floor_height_m → float (default 3.0 — used to compute
            building_height_m when C12 didn't carry explicit heights)
    """
    multifloor_candidate:           Any
    grids_by_floor:                 Mapping[str, Any]
    wet_zone_plans_by_floor:        Mapping[str, Any]
    doors_by_floor:                 Mapping[str, tuple[Any, ...]]
    plot_analysis:                  Any
    circulation_reports_by_floor:   Mapping[str, Any] = ()
    upstream_cache_key:             str = ""
    far_permitted:                  float = 1.5      # default TNCDBR residential
    height_limit_m:                 float = 11.5
    typical_floor_height_m:         float = 3.0


# ============================================================
# Unit conversion + canonical ordering helpers
# ============================================================

def m_to_mm(value_m: float) -> int:
    """Convert metres → integer millimetres with banker's rounding
    (R7a). Sub-mm precision NEVER reaches output."""
    return int(round(value_m * 1000.0))


def sorted_by_floor_label(per_floor: tuple) -> tuple:
    """Return per_floor placements sorted by floor_label lex-ASC.
    Per C12 invariant + Inv R7 byte-equal replay, the upstream is
    already sorted; this function defensively re-sorts to make C16
    self-contained against upstream-tuple-reordering bugs."""
    return tuple(sorted(per_floor, key=lambda x: x[0]))


def floor_label_to_level(label: str) -> int:
    """Map upstream floor_label → integer floor_level for C16.

    C12 conventions observed:
        "F0", "F1", "F2"   → 0, 1, 2
        "G", "FF", "SF"    → 0, 1, 2  (ground / first / second)
        "0", "1", "2"      → 0, 1, 2

    Anything that doesn't parse as a recognized label → use the
    lex-ASC position. Documented as B-C16-FLOOR-LABEL-NORMALIZATION
    (post-LOCK item — Sub-2 normalizer is heuristic; production
    contract pins canonical labels)."""
    label = label.strip().upper()
    # Try pure digits first
    if label.isdigit():
        return int(label)
    # F-prefixed digits (F0, F1, F2)
    if label.startswith("F") and label[1:].isdigit():
        return int(label[1:])
    # Named: G/FF/SF/TF
    named = {"G": 0, "GF": 0, "FF": 1, "SF": 2, "TF": 3, "FOURTH": 4}
    if label in named:
        return named[label]
    # Last resort: hash to a stable integer (but we want monotone, so
    # this is a fallback that caller must avoid by using F-prefix or digit).
    return -1  # signals caller: "use list position instead"
