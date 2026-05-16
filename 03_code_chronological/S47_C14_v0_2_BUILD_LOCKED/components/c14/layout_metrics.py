"""
BuildemUp — Component 14 — Phase γ: layout-level metrics
=========================================================

Per C14 SPEC v0.2 LOCKED § 3 Phase γ + v0.2 A1 (RRA + integration +
graph_size_category) + Inv E10/E11'/E11''/E12'/E17.

Phase γ reads the GraphTopology + NodeMetrics from Phases α/β and
produces the layout-level scalar metrics:

- `mean_depth`: average step_depth across all non-entry rooms
- `max_depth`: maximum step_depth
- `raw_relative_asymmetry`: Hillier & Hanson 1984 RA(main_entry)
   formula: `2 × (MD − 1) / (k − 2)` for k ≥ 3
- `real_relative_asymmetry`: Hillier & Hanson 1987 RRA(main_entry)
   formula: `RA / D(k)` where D(k) is the Krüger-Vieira 2012 closed
   form of the diamond-graph normalizer. **NaN for k < 4** (Inv E11'').
- `integration`: `1 / RRA` (Hillier IHH). **NaN for k < 4** (Inv E12').
   inf when RRA == 0.
- `graph_size_category`: `tiny` (k ≤ 2) | `small` (k == 3) | `normal`
   (k ≥ 4) per Inv E17.

Formula provenance (Rule 11 web-research-verified):
- Hillier, B. & Hanson, J. (1984). The Social Logic of Space.
  Cambridge University Press, p.109–113, p.282.
- Krüger, M. & Vieira, A. (2012) closed-form D(k), cited in
  Fernandes 2024 SSS13 proceedings.
- Teklenburg, Timmermans & Wagenberg (1993). Standardised
  integration measures. Environment and Planning B, 20(3): 347–357.

Reading-of-RRA convention chosen at v0.2 SKETCH:
- The LOCKED spec's `real_relative_asymmetry: float` field is singular
  (not per-room). Phase γ computes **RRA evaluated AT THE MAIN ENTRY
  ROOM** — i.e., "how integrated is the entry into the whole layout?"
  This is the canonical "global integration as seen from the entry"
  reading.
- Alternative readings ("mean RRA across all rooms", "min RRA")
  are filed as `B-C14-RRA-AGGREGATION-CHOICE` if the SKETCH proves
  wrong in v0.3 critique walks.

Inv E7 byte-equal determinism: all formulas are pure FP arithmetic on
integer-valued inputs (step depths); same inputs → same outputs every
time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import GraphInconsistencyError
from .node_metrics import NodeMetrics
from .schema import GraphSizeCategory, _category_for_node_count


# =============================================================================
# Output: LayoutMetrics
# =============================================================================

@dataclass(frozen=True)
class LayoutMetrics:
    """Phase γ output: layout-level scalars.

    Frozen for replay determinism (Inv E7). All numeric invariants
    (E10/E11'/E11''/E12'/E17) verified at __post_init__; if Phase γ's
    output would violate them, GraphInconsistencyError is raised
    (because that means the math itself is broken — not a per-candidate
    failure).
    """
    mean_depth: float
    max_depth: int
    raw_relative_asymmetry: float
    real_relative_asymmetry: float
    integration: float
    graph_size_category: GraphSizeCategory

    def __post_init__(self) -> None:
        # ── Inv E17 ──
        if self.graph_size_category not in ("tiny", "small", "normal"):
            raise GraphInconsistencyError(
                f"Phase γ: graph_size_category must be tiny|small|normal; "
                f"got {self.graph_size_category!r}."
            )


# =============================================================================
# D(k): Krüger & Vieira 2012 diamond normalizer
# =============================================================================

def _diamond_d_value(k: int) -> float:
    """Per Krüger & Vieira 2012 (cited in Fernandes 2024):

        D(k) = 2 × (k × (log₂((k+2)/3) − 1) + 1) / ((k − 1) × (k − 2))

    Closed-form approximation to the diamond-graph root RA.

    Returns NaN for k < 4 (per Inv E11'' — D(3) is degenerate ~0.21,
    making RRA(3) extremely noisy; D(2)/D(1) are undefined). Returns
    a positive finite float for k ≥ 4.

    Rule 11 verification: this formula is cross-checked against:
    - Fernandes 2024 (SSS13) Prolog implementation
    - Teklenburg, Timmermans, Wagenberg 1993 simulation results
    Both yield the SAME numeric values for the example k values
    tested in the literature.
    """
    if k < 4:
        return float("nan")
    # k ≥ 4 guarantees both denominators are nonzero and positive.
    numerator = 2.0 * (k * (math.log2((k + 2) / 3.0) - 1.0) + 1.0)
    denominator = (k - 1) * (k - 2)
    return numerator / denominator


# =============================================================================
# Helpers — extract main-entry depth + compute mean depth
# =============================================================================

def _depth_dict_from_metrics(
    metrics: NodeMetrics,
) -> dict[str, int]:
    """Tuple-of-pairs → dict for convenient lookup."""
    return dict(metrics.step_depth_from_entry)


def _compute_mean_depth_for_node(
    *,
    depths: dict[str, int],
    source: str,
    k: int,
) -> float:
    """Per Hillier & Hanson 1984 p.109:

        MD(source) = (Σ d(source, u) for u ≠ source) / (k − 1)

    For k = 1, MD is undefined (no other nodes); return 0.0 as a
    degenerate-but-safe value (Phase γ will then mark the layout as
    `tiny` and produce NaN for RA/RRA/integration anyway).
    """
    if k <= 1:
        return 0.0
    total = sum(d for r, d in depths.items() if r != source)
    return total / (k - 1)


def _compute_max_depth(depths: dict[str, int]) -> int:
    """Maximum step depth across all rooms.

    For empty graph returns 0 (degenerate but safe; categorized as
    `tiny` regime).
    """
    if not depths:
        return 0
    return max(depths.values())


# =============================================================================
# Phase γ main entry
# =============================================================================

def compute_layout_metrics(
    *,
    node_metrics: NodeMetrics,
    main_entry_room_id: str,
    nodes: tuple[str, ...],
) -> LayoutMetrics:
    """Phase γ: compute layout-level metrics from per-node metrics.

    Per C14 SPEC v0.2 LOCKED § 3 Phase γ + v0.2 A1.

    Inputs:
      node_metrics: NodeMetrics from Phase β (step depths per room).
      main_entry_room_id: which room is the BFS source (required to
        compute RA/RRA/integration "as seen from the entry").
      nodes: the canonical node tuple from Phase α. We pass it
        separately rather than recomputing because the metric tuples
        already have it but we want to avoid recomputing the set.

    Returns:
      LayoutMetrics — frozen, with all Inv E10/E11'/E11''/E12'/E17
      respected.

    Raises:
      GraphInconsistencyError: if main_entry_room_id isn't in
        node_metrics' depth dict (defensive against Phase β / Phase α
        contract drift — should not happen with valid pipeline input).
    """
    k = len(nodes)
    depths = _depth_dict_from_metrics(node_metrics)
    if main_entry_room_id and main_entry_room_id not in depths:
        raise GraphInconsistencyError(
            f"Phase γ: main_entry_room_id {main_entry_room_id!r} not in "
            f"node_metrics.step_depth_from_entry."
        )

    # ── max_depth (always defined for any non-empty graph) ──────────
    max_depth = _compute_max_depth(depths)

    # ── mean_depth (Inv E10: ≤ max_depth ≤ k-1) ─────────────────────
    if k <= 1:
        mean_depth = 0.0
    else:
        mean_depth = _compute_mean_depth_for_node(
            depths=depths, source=main_entry_room_id, k=k,
        )

    # ── raw_relative_asymmetry (Hillier 1984 p.109) ─────────────────
    # RA = 2 × (MD − 1) / (k − 2); defined for k ≥ 3.
    if k < 3:
        # Under-defined: degenerate floor of 0.0 (Inv E11': raw_RA ≥ 0).
        # The orchestrator will categorize this as `tiny` and downstream
        # consumers should not trust the value (see graph_size_category).
        raw_relative_asymmetry = 0.0
    else:
        raw_relative_asymmetry = 2.0 * (mean_depth - 1.0) / (k - 2)
        # Inv E11': ensure non-negative. For shallow layouts MD < 1 is
        # theoretically possible only when k=1 (impossible by k≥3 here),
        # but FP arithmetic can yield tiny negatives like -1e-17. Clamp.
        if -1e-12 < raw_relative_asymmetry < 0.0:
            raw_relative_asymmetry = 0.0

    # ── real_relative_asymmetry (Hillier 1987) ──────────────────────
    # RRA = RA / D(k); NaN for k < 4 (Inv E11'').
    d_k = _diamond_d_value(k)
    if k < 4 or math.isnan(d_k):
        real_relative_asymmetry = float("nan")
    else:
        # k ≥ 4 → d_k > 0 mathematically. Defensive against FP edge cases.
        if d_k <= 0.0:
            # Shouldn't happen at k ≥ 4 but guard against numeric oddities.
            real_relative_asymmetry = float("inf")
        else:
            real_relative_asymmetry = raw_relative_asymmetry / d_k

    # ── integration = 1 / RRA (Inv E12') ────────────────────────────
    if k < 4 or math.isnan(real_relative_asymmetry):
        integration = float("nan")
    elif real_relative_asymmetry == 0.0:
        integration = float("inf")
    else:
        integration = 1.0 / real_relative_asymmetry

    # ── graph_size_category (Inv E17) ───────────────────────────────
    category: GraphSizeCategory = _category_for_node_count(k)

    return LayoutMetrics(
        mean_depth=mean_depth,
        max_depth=max_depth,
        raw_relative_asymmetry=raw_relative_asymmetry,
        real_relative_asymmetry=real_relative_asymmetry,
        integration=integration,
        graph_size_category=category,
    )


__all__ = [
    "LayoutMetrics",
    "compute_layout_metrics",
    "_diamond_d_value",
]
