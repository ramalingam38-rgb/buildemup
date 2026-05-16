"""
BuildemUp† — Component 7a: Grid Generator
===========================================

Single responsibility: decide WHERE columns go given an envelope.

No structural sizing. No foundation. No cost. Just the geometry of
the grid. Downstream components take this grid and layer their
concerns on top.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Final, Optional

from buildemup.kb.rcc_design_rules import (
    PREFERRED_BAY_SIZES_M,
    MIN_RESIDENTIAL_SPAN_M,
    MAX_RESIDENTIAL_SPAN_M,
)
from buildemup.components.c07.wall_segment import (
    WALL_AXIS_CANONICAL_ORDER,
    WALL_ORDER_CONVENTION,
    WallAxis,
    WallSegment,
    WallTag,
    serialize_tags_sorted,
)


# =============================================================================
# B-NEW-K (S38) — staircase clearance constants + Staircase dataclass + W9.
# =============================================================================
#
# NBC 2016 Part 4 Table 3.1.4-G — residential staircase minimums.
# Values await primary-source verification per pre-launch hard gate
# B-150-equiv. v1 ships with these values flagged as needs-verification;
# they should be re-confirmed against the published NBC text before
# pre-launch.
MIN_STAIRCASE_WIDTH_M: Final[float] = 0.9
MIN_STAIRCASE_LANDING_DEPTH_M: Final[float] = 0.9
# Tolerance for anchor-flush check (W9-d). Re-uses C7's general 1e-6 m
# float tolerance convention.
_STAIRCASE_ANCHOR_TOLERANCE_M: Final[float] = 1e-6


@dataclass(frozen=True)
class Staircase:
    """A staircase footprint positioned within the envelope.

    Per B-NEW-K (S38). v1 represents the staircase as an axis-aligned
    rectangular footprint anchored at (origin_x_m, origin_y_m) — the
    bottom-left corner in envelope-local coordinates.

    Fields:
        origin_x_m, origin_y_m: footprint bottom-left in envelope coords
            (envelope origin is (0, 0), x grows east, y grows north —
            consistent with WallSegment convention)
        width_m: dimension along x (perpendicular to climb direction)
        landing_depth_m: dimension along y
        anchor: optional WallAxis the landing footprint is flush with.
            None for centre placements. Encodes the M3a/b/c position
            semantics: EAST=M3a-equivalent, WEST=M3b-equivalent;
            NORTH/SOUTH for completeness; corner positions expressed
            via origin_x/y placement combined with anchor.

    Per-field validation in __post_init__ guards against malformed
    inputs (negative dimensions, non-WallAxis anchor, etc.). The W9
    invariant (clearance against the envelope) is enforced separately
    on Grid construction since it requires the envelope dimensions.
    """
    origin_x_m: float
    origin_y_m: float
    width_m: float
    landing_depth_m: float
    anchor: Optional[WallAxis] = None

    def __post_init__(self) -> None:
        for fname in ("origin_x_m", "origin_y_m", "width_m", "landing_depth_m"):
            v = getattr(self, fname)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(
                    f"Staircase.{fname} must be float; got {type(v).__name__}"
                )
        if self.width_m <= 0.0:
            raise ValueError(
                f"Staircase.width_m must be > 0; got {self.width_m}"
            )
        if self.landing_depth_m <= 0.0:
            raise ValueError(
                f"Staircase.landing_depth_m must be > 0; got {self.landing_depth_m}"
            )
        if self.origin_x_m < 0.0 or self.origin_y_m < 0.0:
            raise ValueError(
                f"Staircase origin must be non-negative; got "
                f"({self.origin_x_m}, {self.origin_y_m})"
            )
        if self.anchor is not None and not isinstance(self.anchor, WallAxis):
            raise ValueError(
                f"Staircase.anchor must be WallAxis or None; "
                f"got {type(self.anchor).__name__}"
            )


def validate_staircase_clearance(
    grid: "Grid", staircase: Staircase,
) -> tuple[bool, Optional[str]]:
    """W9 predicate. Validate a candidate Staircase against a Grid envelope.

    Per B-NEW-K (S38). C11a Tier A registers this as
    `C7.staircase_clearance` for M3a/b/c operators. Pure function —
    does NOT mutate the input Grid.

    Sub-conditions checked (W9 a/b/c/d):
        a) width_m >= MIN_STAIRCASE_WIDTH_M
        b) landing_depth_m >= max(width_m, MIN_STAIRCASE_LANDING_DEPTH_M)
           — per NBC 2016 Part 4 / common Indian practice, landing
           depth must be at least the staircase width (B-NEW-K v0.2,
           S38 K-4 patch).
        c) footprint within envelope (no overflow)
        d) if anchor is set, footprint flush with the corresponding edge

    Returns:
        (True, None) on pass.
        (False, reason) on fail. Reason is a human-readable string
        identifying the failed sub-condition.
    """
    # (a) width minimum
    if staircase.width_m < MIN_STAIRCASE_WIDTH_M:
        return (
            False,
            f"W9-a: staircase width {staircase.width_m}m < "
            f"NBC minimum {MIN_STAIRCASE_WIDTH_M}m",
        )

    # (b) landing depth scales with width (B-NEW-K v0.2, K-4 patch).
    # NBC 2016: landing depth must be at least the staircase width AND
    # at least the absolute floor MIN_STAIRCASE_LANDING_DEPTH_M.
    required_landing = max(staircase.width_m, MIN_STAIRCASE_LANDING_DEPTH_M)
    if staircase.landing_depth_m < required_landing:
        return (
            False,
            f"W9-b: landing depth {staircase.landing_depth_m}m < "
            f"required {required_landing}m "
            f"(max of width_m={staircase.width_m}m and NBC floor "
            f"{MIN_STAIRCASE_LANDING_DEPTH_M}m)",
        )

    # (c) footprint within envelope
    far_x = staircase.origin_x_m + staircase.width_m
    far_y = staircase.origin_y_m + staircase.landing_depth_m
    if far_x > grid.envelope_width_m + _STAIRCASE_ANCHOR_TOLERANCE_M:
        return (
            False,
            f"W9-c: staircase east edge {far_x:.6f}m exceeds envelope "
            f"width {grid.envelope_width_m:.6f}m",
        )
    if far_y > grid.envelope_depth_m + _STAIRCASE_ANCHOR_TOLERANCE_M:
        return (
            False,
            f"W9-c: staircase north edge {far_y:.6f}m exceeds envelope "
            f"depth {grid.envelope_depth_m:.6f}m",
        )

    # (d) anchor flush check
    if staircase.anchor is not None:
        ok, reason = _check_anchor_flush(grid, staircase)
        if not ok:
            return (False, reason)

    return (True, None)


def _check_anchor_flush(
    grid: "Grid", staircase: Staircase,
) -> tuple[bool, Optional[str]]:
    """W9-d helper. Verify the staircase footprint is flush with the
    envelope edge corresponding to the declared anchor."""
    tol = _STAIRCASE_ANCHOR_TOLERANCE_M
    if staircase.anchor is WallAxis.SOUTH:
        if abs(staircase.origin_y_m - 0.0) > tol:
            return (
                False,
                f"W9-d: anchor=SOUTH requires origin_y_m=0; "
                f"got {staircase.origin_y_m}",
            )
    elif staircase.anchor is WallAxis.NORTH:
        far_y = staircase.origin_y_m + staircase.landing_depth_m
        if abs(far_y - grid.envelope_depth_m) > tol:
            return (
                False,
                f"W9-d: anchor=NORTH requires origin_y+depth="
                f"envelope_depth; got far_y={far_y:.6f}, "
                f"envelope_depth={grid.envelope_depth_m:.6f}",
            )
    elif staircase.anchor is WallAxis.WEST:
        if abs(staircase.origin_x_m - 0.0) > tol:
            return (
                False,
                f"W9-d: anchor=WEST requires origin_x_m=0; "
                f"got {staircase.origin_x_m}",
            )
    elif staircase.anchor is WallAxis.EAST:
        far_x = staircase.origin_x_m + staircase.width_m
        if abs(far_x - grid.envelope_width_m) > tol:
            return (
                False,
                f"W9-d: anchor=EAST requires origin_x+width="
                f"envelope_width; got far_x={far_x:.6f}, "
                f"envelope_width={grid.envelope_width_m:.6f}",
            )
    return (True, None)


@dataclass(frozen=True)
class ColumnPosition:
    """Position of one column in the grid."""
    grid_label: str           # e.g., "A1", "B2"
    x_m: float
    y_m: float
    on_perimeter: bool


@dataclass(frozen=True)
class Grid:
    """The output of the grid generator — geometry only.

    Per C7 amendment v0.8 LOCKED, Grid additionally carries
    `wall_segments` describing the four perimeter walls. The default
    empty tuple preserves backwards-compat with all existing C7/C8/C9
    test fixtures and call sites that construct Grid directly.

    Per B-NEW-K (S38), Grid additionally carries an optional
    `staircase` describing the staircase footprint. Default None
    preserves backwards-compat. When set, W9 invariant is enforced in
    __post_init__.

    Production code consuming wall data MUST use
    `wall_segments_canonical()` instead of iterating over
    `wall_segments` directly (W8 invariant).
    """
    columns: list[ColumnPosition]
    bay_x_m: float
    bay_y_m: float
    columns_x_count: int
    columns_y_count: int
    envelope_width_m: float
    envelope_depth_m: float
    wall_segments: tuple[WallSegment, ...] = ()    # backwards-compat default
    staircase: Optional[Staircase] = None           # NEW B-NEW-K (S38)

    def __post_init__(self) -> None:
        # B-NEW-K (S38): W9 enforcement — only fires when staircase set.
        if self.staircase is not None:
            ok, reason = validate_staircase_clearance(self, self.staircase)
            if not ok:
                raise ValueError(
                    f"Grid (W9): staircase fails clearance check: {reason}"
                )

    @property
    def total_columns(self) -> int:
        return len(self.columns)

    @property
    def max_span_m(self) -> float:
        """Max span to be supported by beams."""
        return max(self.bay_x_m, self.bay_y_m)

    def wall_segments_canonical(self) -> tuple[WallSegment, ...]:
        """Return wall_segments in canonical WallAxis order.

        Production code paths MUST use this method instead of iterating
        over `wall_segments` directly. Guarantees byte-identical
        iteration regardless of the underlying tuple's storage order.

        Direct iteration over `wall_segments` is reserved for canonical-
        serialisation snapshots that explicitly want raw storage order
        for debugging/audit purposes.

        Returns walls present in the Grid; missing axes are silently
        omitted (forward-compat with non-rectangular envelopes post
        B-066). For v1 rectangular envelopes, exactly four segments are
        returned in (SOUTH, EAST, NORTH, WEST) order.
        """
        by_axis: dict[WallAxis, WallSegment] = {
            w.axis: w for w in self.wall_segments
        }
        return tuple(by_axis[a] for a in WALL_AXIS_CANONICAL_ORDER if a in by_axis)

    def wall_segment_by_id(self, wall_id: str) -> WallSegment:
        """Look up a WallSegment by its `wall_id`.

        O(N) linear scan; v1 N <= 4 so trivially fast. Polygonal
        envelopes (post B-066) may justify precomputed dict — tracked
        as B-231.

        Raises:
            KeyError if no segment has the given wall_id.
        """
        for w in self.wall_segments:
            if w.wall_id == wall_id:
                return w
        raise KeyError(
            f"Grid has no wall_segment with wall_id={wall_id!r}"
        )


class GridGenerator:
    """Generates a structural column grid for a given envelope.

    No knowledge of loads, soil, or cost. Pure geometry.
    """

    def generate(self, envelope_width_m: float, envelope_depth_m: float) -> Grid:
        """Generate a column grid for the given envelope.

        Args:
            envelope_width_m: buildable width after setbacks
            envelope_depth_m: buildable depth after setbacks

        Returns:
            Grid with column positions, bay sizes, counts.

        Raises:
            ValueError if envelope is smaller than 5m × 5m.
        """
        if envelope_width_m < 5.0 or envelope_depth_m < 5.0:
            raise ValueError(
                f"Envelope too small: {envelope_width_m}m × "
                f"{envelope_depth_m}m. Minimum 5×5m required for "
                f"structural design."
            )

        # Step 1: select bay sizes
        bay_x = self._select_bay_size(envelope_width_m)
        bay_y = self._select_bay_size(envelope_depth_m)

        # Step 2: distribute columns along each axis
        x_positions = self._distribute_columns(envelope_width_m, bay_x)
        y_positions = self._distribute_columns(envelope_depth_m, bay_y)

        # Step 3: build column objects with grid labels
        columns = self._build_columns(
            x_positions, y_positions,
            envelope_width_m, envelope_depth_m,
        )

        # Step 4: build wall segments (C7 amendment v0.8 LOCKED)
        wall_segments = self._build_wall_segments(
            envelope_width_m, envelope_depth_m,
        )

        return Grid(
            columns=columns,
            bay_x_m=bay_x,
            bay_y_m=bay_y,
            columns_x_count=len(x_positions),
            columns_y_count=len(y_positions),
            envelope_width_m=envelope_width_m,
            envelope_depth_m=envelope_depth_m,
            wall_segments=wall_segments,
        )

    @staticmethod
    def _build_wall_segments(
        envelope_w_m: float, envelope_d_m: float,
    ) -> tuple[WallSegment, ...]:
        """Build the four perimeter WallSegments in WALL_ORDER_CONVENTION
        (CCW from SOUTH).

        v1 rectangular envelope only:
            SOUTH:  (0, 0) -> (W, 0)   length W
            EAST:   (W, 0) -> (W, D)   length D
            NORTH:  (W, D) -> (0, D)   length W
            WEST:   (0, D) -> (0, 0)   length D

        All four tagged {EXTERNAL, LOAD_BEARING}. Polygonal envelopes
        (B-066) lift this restriction.

        Enforces W4-W7 invariants by construction:
            W4 — exactly 4 wall_segments
            W5 — each WallAxis appears exactly once
            W6 — wall_ids unique
            W7 — total wall length == perimeter (2W + 2D)
        """
        external_load = frozenset({WallTag.EXTERNAL, WallTag.LOAD_BEARING})
        # Build in CCW-from-SOUTH order matching WALL_ORDER_CONVENTION.
        segments = (
            WallSegment(
                wall_id="WALL_SOUTH",
                axis=WallAxis.SOUTH,
                start_x_m=0.0, start_y_m=0.0,
                end_x_m=envelope_w_m, end_y_m=0.0,
                length_m=envelope_w_m,
                tags=external_load,
            ),
            WallSegment(
                wall_id="WALL_EAST",
                axis=WallAxis.EAST,
                start_x_m=envelope_w_m, start_y_m=0.0,
                end_x_m=envelope_w_m, end_y_m=envelope_d_m,
                length_m=envelope_d_m,
                tags=external_load,
            ),
            WallSegment(
                wall_id="WALL_NORTH",
                axis=WallAxis.NORTH,
                start_x_m=envelope_w_m, start_y_m=envelope_d_m,
                end_x_m=0.0, end_y_m=envelope_d_m,
                length_m=envelope_w_m,
                tags=external_load,
            ),
            WallSegment(
                wall_id="WALL_WEST",
                axis=WallAxis.WEST,
                start_x_m=0.0, start_y_m=envelope_d_m,
                end_x_m=0.0, end_y_m=0.0,
                length_m=envelope_d_m,
                tags=external_load,
            ),
        )
        return segments

    @staticmethod
    def _select_bay_size(envelope_dim_m: float) -> float:
        """Pick the bay size closest to the 'sweet spot' of 3.0-3.6m."""
        SWEET_SPOT = 3.3

        candidates = []
        for bay_count in (2, 3, 4, 5):
            raw_bay = envelope_dim_m / bay_count
            if raw_bay < MIN_RESIDENTIAL_SPAN_M or raw_bay > MAX_RESIDENTIAL_SPAN_M:
                continue
            snapped = min(PREFERRED_BAY_SIZES_M, key=lambda b: abs(b - raw_bay))
            distance_from_sweet = abs(snapped - SWEET_SPOT)
            candidates.append((distance_from_sweet, snapped, bay_count))

        if not candidates:
            # Extreme fallback: envelope that doesn't fit any preferred bay
            # Pick the largest preferred bay that's <= envelope_dim
            viable = [b for b in PREFERRED_BAY_SIZES_M if b <= envelope_dim_m]
            if viable:
                return viable[-1]
            return PREFERRED_BAY_SIZES_M[0]

        candidates.sort()
        return candidates[0][1]

    @staticmethod
    def _distribute_columns(envelope_dim_m: float, bay_size_m: float) -> list[float]:
        """Distribute column positions along one axis.

        Handles sliver bays: if remainder after n bays is <50% of bay_size,
        absorb into the last bay instead of creating a tiny awkward bay.
        """
        n_full_bays = int(envelope_dim_m // bay_size_m)
        remainder = envelope_dim_m - (n_full_bays * bay_size_m)

        if n_full_bays == 0:
            return [0.0, round(envelope_dim_m, 2)]

        if remainder < bay_size_m * 0.5:
            # Absorb sliver
            positions = [round(i * bay_size_m, 2) for i in range(n_full_bays)]
            positions.append(round(envelope_dim_m, 2))
        else:
            # Add another column for the substantial remainder
            positions = [round(i * bay_size_m, 2) for i in range(n_full_bays + 1)]
            positions.append(round(envelope_dim_m, 2))

        return positions

    @staticmethod
    def _build_columns(
        x_positions: list[float], y_positions: list[float],
        envelope_w_m: float, envelope_d_m: float,
    ) -> list[ColumnPosition]:
        """Convert x/y positions into labeled ColumnPosition objects."""
        columns = []
        for col_idx, x in enumerate(x_positions):
            for row_idx, y in enumerate(y_positions):
                col_letter = chr(65 + col_idx)  # A, B, C...
                row_number = row_idx + 1
                label = f"{col_letter}{row_number}"

                on_perim = (
                    x == 0.0 or
                    abs(x - envelope_w_m) < 0.01 or
                    y == 0.0 or
                    abs(y - envelope_d_m) < 0.01
                )

                columns.append(ColumnPosition(
                    grid_label=label,
                    x_m=x,
                    y_m=y,
                    on_perimeter=on_perim,
                ))
        return columns
