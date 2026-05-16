"""S55 Batch 4 — B-066 polygon-plot support scaffolding.

User-decision: B-066 was promoted from v2-deferred to product-blocker
(S54 triage) because L-shaped + irregular plots account for 5-10% of
real Indian residential plots — hard-fails on those are a user-trust
failure.

Full B-066 implementation is multi-session work touching C1 (entry UI),
C4 (shape detection), C5 (L-shape topology), C7 (rotated grid), C8
(corridor support). This module ships the foundational vertex schema
+ shape-classification heuristic + integration breadcrumbs so the
downstream component work can land incrementally.

Status:
  LANDED in S55:
    - PolygonVertex schema
    - classify_polygon_shape() heuristic from vertex count + angles
    - Plot.shape forward-compat enum already had L_SHAPED + IRREGULAR
    - Tests verify the heuristic + integration breadcrumbs

  DEFERRED to follow-up build sessions:
    - C1 polygon entry UI (B-066-C1-UI)
    - C5 L-shape topology operators (B-066-C5-TOPOLOGY)
    - C7 rotated structural grid (B-111 — already filed)
    - C8 diagonal corridor segments (B-113 — already filed)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Tuple

from buildemup.components.c04.schema import PlotShape


@dataclass(frozen=True)
class PolygonVertex:
    """One vertex of a non-rectangular plot polygon.

    Coordinates in plot-local metres. The polygon is closed implicitly
    by treating the last vertex's successor as the first vertex.
    """
    x_m: float
    y_m: float

    def __post_init__(self) -> None:
        # Coordinates may be negative for plots whose origin sits
        # outside the polygon (e.g. an L-shape with origin in the
        # cutout corner). No validation beyond finiteness.
        if not math.isfinite(self.x_m) or not math.isfinite(self.y_m):
            raise ValueError(
                f"PolygonVertex coordinates must be finite; "
                f"got x={self.x_m}, y={self.y_m}"
            )


def _interior_angle_count_near_90(
    vertices: Tuple[PolygonVertex, ...], tolerance_deg: float = 15.0,
) -> int:
    """Count vertices whose interior angle is within tolerance of 90°."""
    n = len(vertices)
    if n < 3:
        return 0
    count = 0
    for i in range(n):
        prev = vertices[(i - 1) % n]
        curr = vertices[i]
        nxt = vertices[(i + 1) % n]
        ax, ay = prev.x_m - curr.x_m, prev.y_m - curr.y_m
        bx, by = nxt.x_m - curr.x_m, nxt.y_m - curr.y_m
        dot = ax * bx + ay * by
        cross = ax * by - ay * bx
        angle = math.degrees(math.atan2(abs(cross), dot))
        if abs(angle - 90.0) <= tolerance_deg:
            count += 1
    return count


def classify_polygon_shape(
    vertices: Tuple[PolygonVertex, ...],
) -> PlotShape:
    """Classify a polygon by vertex count + right-angle count.

    Heuristic:
      - 4 vertices, all ~90° → RECTANGULAR
      - 6 vertices, 5-6 ~90° → L_SHAPED
      - otherwise → IRREGULAR

    Sufficient for v1's 5-10% of Indian residential plots (mostly
    L-shapes); IRREGULAR plots still get the hard-fail today but at
    least the classification is correct.
    """
    n = len(vertices)
    right_angles = _interior_angle_count_near_90(vertices)
    if n == 4 and right_angles == 4:
        return PlotShape.RECTANGULAR
    if n == 6 and right_angles >= 5:
        return PlotShape.L_SHAPED
    return PlotShape.IRREGULAR


# ─────────────────────────────────────────────────────────────────────
# Integration manifest — what downstream components still need
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PolygonIntegrationGate:
    component: str
    gate_id: str
    description: str
    landed: bool


POLYGON_INTEGRATION_GATES: Final[Tuple[PolygonIntegrationGate, ...]] = (
    PolygonIntegrationGate(
        component="C4",
        gate_id="B-066-C4-VERTEX-SCHEMA",
        description="PolygonVertex schema + classify_polygon_shape()",
        landed=True,
    ),
    PolygonIntegrationGate(
        component="C1",
        gate_id="B-066-C1-UI",
        description="Brief form UI for polygon vertex entry",
        landed=False,
    ),
    PolygonIntegrationGate(
        component="C5",
        gate_id="B-066-C5-TOPOLOGY",
        description="L-shape topology operators",
        landed=False,
    ),
    PolygonIntegrationGate(
        component="C7",
        gate_id="B-111",
        description="Rotated structural grid (already filed as B-111)",
        landed=False,
    ),
    PolygonIntegrationGate(
        component="C8",
        gate_id="B-113",
        description="Diagonal corridor segments (already filed as B-113)",
        landed=False,
    ),
)


__all__ = [
    "PolygonVertex",
    "classify_polygon_shape",
    "PolygonIntegrationGate",
    "POLYGON_INTEGRATION_GATES",
]
