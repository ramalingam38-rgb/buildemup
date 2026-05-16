"""
BuildemUp† — Component 8 (Corridor Designer) — Junction-width propagation.

Per C8 SPEC v0.5 LOCKED § 4.10 / § 14.20 (NEW v0.4).

Implements three ``WidthPropagation`` modes:

  - JUNCTION_LOCAL_ONLY (default v0.4):
      Each JUNCTION endpoint inherits the MAX of adjoining segments'
      constant_width_m. Each adjoining segment tapers from that junction-max
      back to its own constant_width_m over taper_zone_m. The constant
      middle keeps the segment's requested width — wide-segment inflation
      is contained.

  - GLOBAL_MAX_INHERITANCE (v0.3 back-compat; deprecated):
      Same junction-max inheritance, but instead of tapering, the entire
      adjoining segment inflates to the junction width. Use only for
      regression tests against v0.3 behavior.

  - INDEPENDENT_WIDTHS (v0.2 behavior; rare):
      No propagation. Each segment keeps its constant_width_m at all
      endpoints. Junction has step discontinuity. A diagnostic line is
      added to provenance.rule_trace per junction with mismatch.

Junction matching uses coordinate-coincidence within ``config.epsilon_m``.

†= placeholder name marker.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple

from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.schema import (
    CorridorEndpointKind,
    CorridorSegment,
    CorridorDesignConfig,
    WidthPropagation,
)
from buildemup.components.c08.tolerances import ARITHMETIC_M
from buildemup.components.c08.width_selection import resolve_taper_zone_m


def _coord_key(pt: tuple[float, float], epsilon_m: float) -> tuple[int, int]:
    """Return a quantized integer coordinate key for junction matching.

    Two endpoints are considered coincident if their coordinate keys match
    after quantizing at the EPSILON_M scale.
    """
    # Quantize at half-epsilon to absorb FP jitter
    q = max(epsilon_m / 2.0, ARITHMETIC_M)
    return (
        int(round(pt[0] / q)),
        int(round(pt[1] / q)),
    )


def _build_junction_index(
    segments: List[CorridorSegment],
    epsilon_m: float,
) -> dict[tuple[int, int], list[tuple[int, str]]]:
    """Map each junction coordinate to (segment_index, 'start'|'end') pairs.

    Only endpoints with kind == JUNCTION are included.
    """
    index: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for i, seg in enumerate(segments):
        for which, ep in (("start", seg.start), ("end", seg.end)):
            if ep.kind == CorridorEndpointKind.JUNCTION:
                key = _coord_key(ep.point_m, epsilon_m)
                index.setdefault(key, []).append((i, which))
    return index


def propagate_junction_widths(
    segments: List[CorridorSegment],
    *,
    config: CorridorDesignConfig,
    grid: Grid,
) -> tuple[list[CorridorSegment], list[str]]:
    """Apply junction-width propagation per the configured mode.

    Per § 4.10.

    Args:
        segments: list of CorridorSegments. Caller passes by value; this
                  function returns a new list (segments are frozen).
        config: tunables; supplies ``width_propagation`` and ``epsilon_m``.
        grid: needed by ``resolve_taper_zone_m`` for default taper sizing.

    Returns:
        ``(updated_segments, rule_trace_additions)`` — the updated list of
        segments with junction widths set, plus diagnostic strings appended
        to provenance.rule_trace.
    """
    if not segments:
        return list(segments), []

    mode = config.width_propagation
    rule_trace: list[str] = []

    junction_index = _build_junction_index(segments, config.epsilon_m)

    # Mutable copy: we'll build a new list of (possibly replaced) segments.
    new_segments: list[CorridorSegment] = list(segments)

    if mode == WidthPropagation.INDEPENDENT_WIDTHS:
        # No propagation. Diagnostic: log step discontinuity at each junction
        # where adjoining widths differ.
        for junction_key, members in junction_index.items():
            if len(members) < 2:
                continue
            widths = []
            for (idx, which) in members:
                seg = new_segments[idx]
                w = (
                    seg.start_width_m if which == "start"
                    else seg.end_width_m
                )
                widths.append(w)
            if max(widths) - min(widths) > config.epsilon_m:
                # Step discontinuity logged
                seg_ids = sorted(idx for idx, _ in members)
                rule_trace.append(
                    f"junction_width_step_at_segments_{seg_ids}_widths_{widths}"
                )
        return new_segments, rule_trace

    # For JUNCTION_LOCAL_ONLY and GLOBAL_MAX_INHERITANCE we need the
    # junction-max width per junction.

    # B-131 pre-pass (S33): for each segment, count how many of its ends
    # will *actually* taper (i.e., adjoin a junction whose junction_max
    # exceeds the segment's constant width). This count is threaded into
    # resolve_taper_zone_m() so the per-end taper is bounded by
    # length / (2 × n_tapered_ends), satisfying Inv 20 N-aware
    # (per C8 v0.6 PROPOSED).
    eps_taper = config.epsilon_m
    tapered_ends_per_segment: dict[int, int] = {}
    for junction_key_pre, members_pre in junction_index.items():
        if not members_pre:
            continue
        widths_pre = [
            new_segments[idx].constant_width_m for (idx, _) in members_pre
        ]
        j_max = max(widths_pre)
        for (idx, _which) in members_pre:
            seg_pre = new_segments[idx]
            if abs(seg_pre.constant_width_m - j_max) > eps_taper:
                # This end will taper at this junction.
                tapered_ends_per_segment[idx] = (
                    tapered_ends_per_segment.get(idx, 0) + 1
                )

    for junction_key, members in junction_index.items():
        if not members:
            continue
        widths_at_junction = []
        for (idx, which) in members:
            widths_at_junction.append(new_segments[idx].constant_width_m)
        junction_max = max(widths_at_junction)

        if mode == WidthPropagation.GLOBAL_MAX_INHERITANCE:
            # v0.3 behavior: each adjoining segment inflates entirely to
            # junction_max. Constant middle widens; no taper.
            for (idx, which) in members:
                seg = new_segments[idx]
                if abs(seg.constant_width_m - junction_max) <= config.epsilon_m:
                    continue  # already at junction-max
                new_seg = replace(
                    seg,
                    constant_width_m=junction_max,
                    start_width_m=junction_max,
                    end_width_m=junction_max,
                    taper_zone_m=0.0,
                )
                new_segments[idx] = new_seg
                rule_trace.append(
                    f"global_max_inflated_segment_{idx}_to_{junction_max:.4f}m"
                )
            continue

        # mode == JUNCTION_LOCAL_ONLY (default)
        for (idx, which) in members:
            seg = new_segments[idx]
            n_tapered = tapered_ends_per_segment.get(idx, 0)
            taper_m, truncated = resolve_taper_zone_m(
                config, grid, seg.length_m, n_tapered_ends=n_tapered,
            )

            # If this segment's constant width is already == junction_max,
            # no taper is needed at this end (the segment is the wide one).
            if abs(seg.constant_width_m - junction_max) <= config.epsilon_m:
                # Set the junction-end width explicitly for invariant 18.
                if which == "start":
                    if abs(seg.start_width_m - junction_max) > config.epsilon_m:
                        new_segments[idx] = replace(
                            seg, start_width_m=junction_max,
                        )
                else:
                    if abs(seg.end_width_m - junction_max) > config.epsilon_m:
                        new_segments[idx] = replace(
                            seg, end_width_m=junction_max,
                        )
                continue

            # Taper required: junction-end gets junction_max width,
            # constant middle stays at constant_width_m.
            #
            # B-141 cap (S33): the previous code used
            # ``max(seg.taper_zone_m, taper_m)`` without an upper bound,
            # which could allow cross-junction iterations to inflate
            # taper beyond Inv 20's tolerance. We now cap the taper at the
            # N-aware Inv 20 bound: length / (2 × max(1, n_tapered)).
            n_for_cap = max(1, n_tapered)
            taper_cap = seg.length_m / (2.0 * n_for_cap)
            new_taper = min(max(seg.taper_zone_m, taper_m), taper_cap)
            if which == "start":
                new_segments[idx] = replace(
                    seg,
                    start_width_m=junction_max,
                    taper_zone_m=new_taper,
                )
            else:
                new_segments[idx] = replace(
                    seg,
                    end_width_m=junction_max,
                    taper_zone_m=new_taper,
                )

            rule_trace.append(
                f"local_taper_segment_{idx}_{which}_to_{junction_max:.4f}m"
                f"_taper_{taper_m:.3f}m_n={n_tapered}"
                + ("_truncated" if truncated else "")
                + ("_capped" if new_taper < max(seg.taper_zone_m, taper_m) - eps_taper else "")
            )

    return new_segments, rule_trace


__all__ = [
    "propagate_junction_widths",
]
