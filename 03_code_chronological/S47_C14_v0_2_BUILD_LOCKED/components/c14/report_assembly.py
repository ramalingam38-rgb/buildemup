"""
BuildemUp — Component 14 — Phase ζ: report assembly
====================================================

Per C14 SPEC v0.2 LOCKED § 3 Phase ζ + v0.2 A8 (Inv E18 category_coverage)
+ Inv E16 (provenance triple).

Phase ζ is the FINAL phase. It assembles all prior outputs into the
canonical CirculationGraphReport:

Inputs (one set per candidate):
- source_placed_candidate_signature
- GraphTopology (from Phase α)
- NodeMetrics (from Phase β)
- LayoutMetrics (from Phase γ)
- EmittedFlags (from Phase δ — structural + preference, already capped)
- AdvisoryBundle (from Phase ε — upstream + c14 advisories)
- RoomMetadata tuple (used here for category_coverage)
- CirculationConfig (for category_coverage_low threshold)
- C14CacheKeys (composed prior)
- Version triple (C14_VERSION, C14_METRIC_VERSION, advisory_schema_version)

Output: CirculationGraphReport (frozen, canonical-sorted, all
invariants enforced by its __post_init__).

Phase ζ's own logic:
1. Compute category_coverage (per A8 Inv E18) — fraction of nodes
   whose category is in ALL_RECOGNIZED_CATEGORY_KEYWORDS. This was
   passed INTO flag emission as a precondition; we compute it here
   and the orchestrator wires the same value through both phases.
2. Stamp provenance triple (Inv E16).
3. Construct CirculationGraphReport — its __post_init__ verifies
   all numeric + canonical-sort invariants.
"""
from __future__ import annotations

from .advisory_passthrough import AdvisoryBundle
from .cache_keys import C14CacheKeys
from .contracts import ALL_RECOGNIZED_CATEGORY_KEYWORDS, RoomMetadata
from .flag_emission import EmittedFlags
from .graph_construction import GraphTopology
from .layout_metrics import LayoutMetrics
from .node_metrics import NodeMetrics
from .schema import CirculationGraphReport


# =============================================================================
# Category coverage (per A8 Inv E18)
# =============================================================================

def compute_category_coverage(
    *,
    nodes: tuple[str, ...],
    metadata: tuple[RoomMetadata, ...],
) -> float:
    """Per v0.2 A8 Inv E18.

    Returns the fraction of `nodes` whose corresponding RoomMetadata
    category appears in `ALL_RECOGNIZED_CATEGORY_KEYWORDS`.

    Edge cases:
    - Empty nodes: returns 1.0 (degenerate-but-safe; trivially "all
      covered" since the set of unrecognized is empty).
    - Node has no metadata entry: counted as UNRECOGNIZED (lowers
      coverage).
    - Node's metadata category is the empty string: counted as
      UNRECOGNIZED.

    The coverage value flows back into flag emission so the
    `category_coverage_low` STRUCTURAL flag can fire if too many
    nodes lack recognized categorization.
    """
    if not nodes:
        return 1.0
    metadata_lookup = {rm.room_id: rm.category for rm in metadata}
    recognized = 0
    for room_id in nodes:
        category = metadata_lookup.get(room_id, "")
        if category and category in ALL_RECOGNIZED_CATEGORY_KEYWORDS:
            recognized += 1
    return recognized / len(nodes)


# =============================================================================
# Phase ζ main entry
# =============================================================================

def assemble_report(
    *,
    source_placed_candidate_signature: str,
    topology: GraphTopology,
    node_metrics: NodeMetrics,
    layout_metrics: LayoutMetrics,
    emitted_flags: EmittedFlags,
    advisory_bundle: AdvisoryBundle,
    category_coverage: float,
    c14_version: str,
    c14_metric_version: int,
    advisory_schema_version: int,
    cache_keys: C14CacheKeys,
) -> CirculationGraphReport:
    """Phase ζ: build the CirculationGraphReport.

    Per v0.1 § 3 Phase ζ + Inv E2/E3'/E4/E5/E10/E11'/E11''/E12'/E13'/
    E16/E17/E18.

    The report's __post_init__ verifies all numeric + canonical-sort
    invariants. If Phase α/β/γ/δ produced any output violating those
    invariants, the construction will raise ValueError — that's a
    real bug in the upstream phases, NOT a per-candidate failure.

    Inputs are unchanged; this function just assembles + stamps.
    """
    return CirculationGraphReport(
        source_placed_candidate_signature=source_placed_candidate_signature,
        # Phase α
        nodes=topology.nodes,
        edges=topology.edges,
        primary_edges=topology.primary_edges,
        # Phase β
        step_depth_from_entry=node_metrics.step_depth_from_entry,
        connectivity=node_metrics.connectivity,
        betweenness_rank=node_metrics.betweenness_rank,
        # Phase γ
        mean_depth=layout_metrics.mean_depth,
        max_depth=layout_metrics.max_depth,
        raw_relative_asymmetry=layout_metrics.raw_relative_asymmetry,
        real_relative_asymmetry=layout_metrics.real_relative_asymmetry,
        integration=layout_metrics.integration,
        graph_size_category=layout_metrics.graph_size_category,
        # Phase δ
        structural_flags=emitted_flags.structural_flags,
        preference_flags=emitted_flags.preference_flags,
        # Phase ε
        upstream_advisory_flags=advisory_bundle.upstream_advisory_flags,
        c14_advisory_flags=advisory_bundle.c14_advisory_flags,
        # Phase ζ
        category_coverage=category_coverage,
        # Inv E16 provenance
        c14_version=c14_version,
        c14_metric_version=c14_metric_version,
        advisory_schema_version=advisory_schema_version,
        # Cache keys
        cache_keys=cache_keys,
    )


__all__ = [
    "compute_category_coverage",
    "assemble_report",
]
