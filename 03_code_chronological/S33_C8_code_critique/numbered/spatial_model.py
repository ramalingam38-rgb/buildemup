"""
BuildemUp† — Component 8 (Corridor Designer) — Spatial model module.

Per C8 SPEC v0.5 LOCKED § 4.0 / § 14.1.

C8 owns the ZoneBandEnvelope spatial model. This module derives the per-band
bounding rectangles ("strips") from the C6 candidate's ``refined_zone_bands``
mapping plus the C7 grid envelope dimensions.

The directional-strip model:
  - Each (band, direction) → a rectangular strip of width ``envelope_dim/N``
    placed on the cardinal edge facing ``direction``, where N = count of
    distinct cardinal bands in the candidate.
  - Corner overlaps (where two adjacent strips meet at a corner) are
    deterministically resolved by band-priority order (§ 14.10):
    PUBLIC > PRIVATE > SERVICE by default; configurable via
    ``CorridorDesignConfig.band_priority_order``.
  - CIRCULATION band intentionally has NO envelope (it IS the corridor;
    § 14.7 / Invariant 7).

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Mapping

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c06.schema import OrientedCandidate
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c08.schema import (
    CorridorDesignConfig,
    ZoneBandEnvelope,
)
from buildemup.components.c08.tolerances import (
    ARITHMETIC_M,
    GEOMETRIC_M,
    STRUCTURAL_M,
)
from buildemup.domain.envelope import PlotOrientation


# Cardinal directions (mirrors C6.CARDINAL_FACINGS but kept local to avoid
# the cross-component import cost):
_CARDINAL_FACINGS = frozenset({
    PlotOrientation.NORTH,
    PlotOrientation.EAST,
    PlotOrientation.SOUTH,
    PlotOrientation.WEST,
})


def derive_zone_band_envelopes(
    oriented_candidate: OrientedCandidate,
    grid: Grid,
    *,
    config: CorridorDesignConfig,
) -> tuple[ZoneBandEnvelope, ...]:
    """Derive ZoneBandEnvelope rectangles for the given oriented candidate.

    Per § 4.0 directional-strip algorithm with corner-overlap resolution
    (§ 14.10).

    Args:
        oriented_candidate: from C6, carries ``refined_zone_bands``.
        grid: from C7, carries ``envelope_width_m / envelope_depth_m``.
        config: tunables; uses ``band_priority_order`` for corner resolution.

    Returns:
        Tuple of ZoneBandEnvelope, one per non-CIRCULATION band in
        ``refined_zone_bands``. Order is the iteration order of the input
        mapping (deterministic when input is a deterministic mapping).
    """
    refined = oriented_candidate.orientation.refined_zone_bands

    # Filter out CIRCULATION (it has no envelope per § 14.7)
    band_dir_pairs: list[tuple[ZoneBand, PlotOrientation]] = []
    for band, direction in refined.items():
        if band == ZoneBand.CIRCULATION:
            continue
        if direction not in _CARDINAL_FACINGS:
            # Defensive: C6 invariant 9 already enforces this; assert here.
            raise ValueError(
                f"derive_zone_band_envelopes: refined_zone_bands[{band.value}] "
                f"direction must be cardinal; got {direction.value}"
            )
        band_dir_pairs.append((band, direction))

    n_strips = len(band_dir_pairs)
    if n_strips == 0:
        return ()

    # Strip thickness: envelope dim along strip's direction / N
    # (Per § 4.0 step 1.) For uniform strips in v1, we use the envelope's
    # smaller dimension as thickness divisor for simplicity — but the spec
    # says "envelope_dim_along_direction / N" where direction is each strip's
    # own. For 4 distinct cardinal bands the strips can have different
    # thicknesses if the envelope is non-square. The spec's "~25% of envelope
    # along its axis" is interpreted per-direction.
    #
    # Build the raw strips first (without corner-overlap resolution):
    raw_strips = []
    for band, direction in band_dir_pairs:
        if direction in (PlotOrientation.NORTH, PlotOrientation.SOUTH):
            t = grid.envelope_depth_m / n_strips
            if direction == PlotOrientation.NORTH:
                x_min, y_min = 0.0, grid.envelope_depth_m - t
                x_max, y_max = grid.envelope_width_m, grid.envelope_depth_m
            else:  # SOUTH
                x_min, y_min = 0.0, 0.0
                x_max, y_max = grid.envelope_width_m, t
        else:  # EAST or WEST
            t = grid.envelope_width_m / n_strips
            if direction == PlotOrientation.EAST:
                x_min, y_min = grid.envelope_width_m - t, 0.0
                x_max, y_max = grid.envelope_width_m, grid.envelope_depth_m
            else:  # WEST
                x_min, y_min = 0.0, 0.0
                x_max, y_max = t, grid.envelope_depth_m
        raw_strips.append((band, direction, x_min, y_min, x_max, y_max))

    # Resolve corner overlaps deterministically per § 14.10 / § 4.0.
    # Band priority: PUBLIC > PRIVATE > SERVICE by default.
    priority_order = config.effective_band_priority_order()
    band_priority: dict[ZoneBand, int] = {
        b: i for i, b in enumerate(priority_order)
    }

    def priority_key(band: ZoneBand) -> int:
        # Lower index = higher priority. Bands not in the priority order
        # (defensive) get a worse-than-everyone priority.
        return band_priority.get(band, 10**6)

    resolved = list(raw_strips)
    # Pairwise overlap resolution: for each (i, j) where strips overlap,
    # the lower-priority strip is clipped at the overlap boundary.
    for i in range(len(resolved)):
        for j in range(len(resolved)):
            if i == j:
                continue
            (b_i, d_i, xi0, yi0, xi1, yi1) = resolved[i]
            (b_j, d_j, xj0, yj0, xj1, yj1) = resolved[j]

            # Compute overlap rectangle (axis-aligned)
            ox0 = max(xi0, xj0)
            oy0 = max(yi0, yj0)
            ox1 = min(xi1, xj1)
            oy1 = min(yi1, yj1)
            if ox0 >= ox1 - ARITHMETIC_M or oy0 >= oy1 - ARITHMETIC_M:
                continue  # no overlap

            # Decide loser: the lower-priority band is clipped.
            pi = priority_key(b_i)
            pj = priority_key(b_j)
            if pi < pj:
                loser_idx = j
            elif pj < pi:
                loser_idx = i
            else:
                # Tie: lexicographic on band name (per § 4.0 "if both have
                # the same priority class").
                if b_i.value < b_j.value:
                    loser_idx = j
                else:
                    loser_idx = i

            (b_l, d_l, xl0, yl0, xl1, yl1) = resolved[loser_idx]
            # Clip the loser strip out of the overlap region. We choose the
            # clip axis based on the loser's strip orientation:
            #   - N/S strips: clip along x-axis (preserve vertical extent)
            #   - E/W strips: clip along y-axis (preserve horizontal extent)
            if d_l in (PlotOrientation.NORTH, PlotOrientation.SOUTH):
                # N/S strip: full envelope width by default. Clip x.
                # If overlap aligned to one x-edge, shrink to the opposite.
                if abs(xl0 - ox0) < ARITHMETIC_M:
                    new_x0 = ox1
                    new_x1 = xl1
                elif abs(xl1 - ox1) < ARITHMETIC_M:
                    new_x0 = xl0
                    new_x1 = ox0
                else:
                    # Overlap is interior — should not happen with
                    # cardinal strips; fall back to clipping x to whichever
                    # side has more remaining envelope.
                    left_remaining = ox0 - xl0
                    right_remaining = xl1 - ox1
                    if left_remaining >= right_remaining:
                        new_x0, new_x1 = xl0, ox0
                    else:
                        new_x0, new_x1 = ox1, xl1
                if new_x1 - new_x0 < ARITHMETIC_M:
                    # Loser strip fully consumed — degenerate to a thin
                    # sliver. Skip this update (loser remains; will be
                    # filtered out below if degenerate).
                    resolved[loser_idx] = (b_l, d_l, new_x0, yl0, new_x1, yl1)
                else:
                    resolved[loser_idx] = (b_l, d_l, new_x0, yl0, new_x1, yl1)
            else:
                # E/W strip: full envelope depth. Clip y.
                if abs(yl0 - oy0) < ARITHMETIC_M:
                    new_y0 = oy1
                    new_y1 = yl1
                elif abs(yl1 - oy1) < ARITHMETIC_M:
                    new_y0 = yl0
                    new_y1 = oy0
                else:
                    bottom_remaining = oy0 - yl0
                    top_remaining = yl1 - oy1
                    if bottom_remaining >= top_remaining:
                        new_y0, new_y1 = yl0, oy0
                    else:
                        new_y0, new_y1 = oy1, yl1
                resolved[loser_idx] = (b_l, d_l, xl0, new_y0, xl1, new_y1)

    # Build envelopes; skip degenerate (zero-area) strips.
    envelopes: list[ZoneBandEnvelope] = []
    for (band, direction, x0, y0, x1, y1) in resolved:
        if x1 - x0 < GEOMETRIC_M or y1 - y0 < GEOMETRIC_M:
            # Degenerate after clipping; band has no envelope this candidate.
            # Per § 4.0 this is rare but possible; downstream code that
            # depends on per-band envelopes must check via lookup.
            continue
        envelopes.append(
            ZoneBandEnvelope(
                band=band,
                direction=direction,
                x_min_m=x0,
                y_min_m=y0,
                x_max_m=x1,
                y_max_m=y1,
            )
        )

    return tuple(envelopes)


def find_envelope_for_band(
    envelopes: tuple[ZoneBandEnvelope, ...],
    band: ZoneBand,
) -> ZoneBandEnvelope | None:
    """Return the first envelope for the given band, or None if absent."""
    for e in envelopes:
        if e.band == band:
            return e
    return None


__all__ = [
    "derive_zone_band_envelopes",
    "find_envelope_for_band",
]
