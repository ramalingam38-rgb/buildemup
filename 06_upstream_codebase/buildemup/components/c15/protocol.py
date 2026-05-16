"""
BuildemUp — Component 15 — Check Protocol + Context
=====================================================

Per C15 SPEC v0.2 LOCKED § 1.4 (10 dimensions) + § 3 Phase ρ
(check registry traversal).

A Check is the unit of evaluation. The C15 registry holds Check
instances (one per check_id in the v1 ~41-entry registry); the
orchestrator (Sub-5) iterates them in lex-ASC order and invokes
`evaluate(context)` on each, producing either a ProblemCheck (the
check ran and produced PASS/WARN/FAIL) or a DeferredCheck (the check
could not run because its data dependency was unavailable — Inv P6
A5 routing).

Design notes:

1. **Protocol, not ABC.** Python's runtime structural-subtyping is
   sufficient. Concrete checks are frozen dataclasses (immutable
   identity, eq=False because two instances with same check_id are
   equal-as-registered-checks via registry lookup, not field-equal
   instances).

2. **Stateless.** Checks carry no per-evaluation state — they receive
   a CheckContext and return a result. Replay determinism (Inv P2)
   depends on this.

3. **Severity NOT decided by the Check itself.** Per Inv P8: severity
   is owned by the severity_rule_table. The Check produces a status;
   severity lookup happens in Phase σ (severity assignment). This
   keeps the Check's responsibility narrow.

4. **DimensionId derived from check_id.** A Check declares its
   check_id; the dimension_id is parsed from the check_id pattern
   ("P{dimension}.{index}"). No drift possible (Inv P9 alignment).

5. **Data dependency declared.** Each Check declares its
   data_dependencies — a tuple of stable string names like
   ("c12_placement", "room_categories"). The orchestrator can
   short-circuit: if any required dependency is missing on the
   context, the check is immediately deferred without invoking
   `evaluate`. This makes NA emission cheap and the data envelope
   visible in the registry without running checks.

6. **Cultural scope declared.** A Check declares cultural_scope — a
   frozenset of CulturalProfile values where the check is meaningful,
   OR `None` for "applies regardless of cultural profile" (Inv P13
   routing).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .contracts import CulturalProfile, ProblemAnalysisMetadata
from .schema import (
    CheckEpistemicKind,
    DeferredCheck,
    ProblemCheck,
)


# =============================================================================
# CheckContext — the bundle a Check sees
# =============================================================================

@dataclass(frozen=True)
class CheckContext:
    """The bundle of upstream data a Check evaluates against.

    Per C15 SPEC v0.2 LOCKED § 3 Phase π — assembled at ingress and
    threaded through Phase ρ unchanged.

    Fields:
      placed_candidate: C12 PlacedCandidate (rooms + geometry +
          envelope). Typed as `object` here to avoid a hard import
          dependency on C12's schema (which is in upstream codebase
          per separation of components). The orchestrator (Sub-5)
          ensures the runtime type matches what checks expect.
      circulation_report: C14 CirculationGraphReport (adjacency
          graph + flags + advisory passthrough). Typed as `object`
          for the same reason.
      metadata: ProblemAnalysisMetadata (cultural_profile,
          room_categories, main_entry_room_id, floor_metadata).
      available_dependencies: frozenset[str] — which named
          dependencies the orchestrator confirmed present on this
          context. A Check can also probe explicitly; this is a
          shortcut.

    The context is frozen and never mutated by any Check (Inv P5
    read-only).
    """
    placed_candidate: object
    circulation_report: object
    metadata: ProblemAnalysisMetadata
    available_dependencies: frozenset[str]

    def __post_init__(self) -> None:
        # Defensive: metadata must be a ProblemAnalysisMetadata; we
        # accept `object` for placed_candidate and circulation_report
        # because their concrete types live in C12/C14 modules.
        if not isinstance(self.metadata, ProblemAnalysisMetadata):
            raise TypeError(
                f"CheckContext.metadata must be ProblemAnalysisMetadata; "
                f"got {type(self.metadata)}"
            )
        if not isinstance(self.available_dependencies, frozenset):
            raise TypeError(
                f"CheckContext.available_dependencies must be frozenset; "
                f"got {type(self.available_dependencies)}"
            )


# =============================================================================
# Check protocol
# =============================================================================

@runtime_checkable
class Check(Protocol):
    """A unit of evaluation in C15's registry.

    Implementations are typically frozen dataclasses or simple class
    instances. The orchestrator does not instantiate checks per
    candidate — it iterates a pre-built registry of Check instances,
    sharing each across candidates. This is safe because checks are
    stateless.

    Attributes (all checks declare these):
      check_id: stable lex-ASC ID following pattern "P{dim}.{index}"
          per § 1.5. Once assigned, never changes meaning (§ 1.5
          P-invariant). Used as registry key.
      dimension_id: parsed dimension (1..10). Must match check_id's
          prefix (constructor enforces).
      epistemic_kind: REGULATORY / ARCHITECTURAL_HEURISTIC /
          CULTURAL_PREFERENCE per A2. Surfaces which authority
          backs this check; UX consumers render this differently.
      data_dependencies: tuple of stable named dependency keys.
          The orchestrator pre-checks these against the context's
          available_dependencies; missing → DeferredCheck without
          invoking evaluate.
      cultural_scope: frozenset[CulturalProfile] | None — None means
          the check applies regardless of cultural_profile. A
          non-None set means the check is only meaningful for
          listed profiles; outside that scope it is deferred with
          na_reason="cultural_profile_mismatch" (Inv P13).

    Method:
      evaluate(context) → ProblemCheck | DeferredCheck
        The check sees the full context; runs its measurement;
        returns either a ProblemCheck (status PASS/WARN/FAIL) or a
        DeferredCheck (NOT_APPLICABLE with na_reason).

        Implementations MUST be deterministic (Inv P2). Same context
        → same return. No randomness, no time-dependence, no IO.
    """

    check_id: str
    dimension_id: int
    epistemic_kind: CheckEpistemicKind
    data_dependencies: tuple[str, ...]
    cultural_scope: Optional[frozenset[CulturalProfile]]

    def evaluate(self, context: CheckContext) -> ProblemCheck | DeferredCheck:
        ...


# =============================================================================
# Convenience: shared dependency names
# =============================================================================

# Standard dependency names checks can declare. These are advisory
# constants — checks may use any string, but using these keeps the
# registry's data-dependency surface canonical.

DEP_C12_PLACEMENT: str = "c12_placement"
"""The C12 PlacedCandidate is present and non-empty."""

DEP_C12_PLACEMENT_GEOMETRY: str = "c12_placement_geometry"
"""C12 PlacedCandidate.placed_rooms have non-degenerate width_m/depth_m."""

DEP_C14_GRAPH: str = "c14_graph"
"""The C14 CirculationGraphReport is present with a non-empty graph."""

DEP_C14_FLAGS: str = "c14_flags"
"""The C14 structural/preference flag tuples are present."""

DEP_ROOM_CATEGORIES: str = "room_categories"
"""ProblemAnalysisMetadata.room_categories covers all placed_room_ids."""

DEP_FLOOR_METADATA: str = "floor_metadata"
"""ProblemAnalysisMetadata.floor_metadata declares per-floor room sets."""

DEP_MAIN_ENTRY: str = "main_entry"
"""ProblemAnalysisMetadata.main_entry_room_id resolves to a placed room."""

# v1-deferred dependencies — checks declaring these will always
# emit DeferredCheck at v1 because the data is not in the pipeline.
DEP_WINDOW_DATA: str = "window_data"
"""Per-room window placement (size, orientation). NOT in pipeline at v1.
Blocked by B-C15-WINDOW-DATA backlog item."""

DEP_FURNITURE_FIT: str = "furniture_fit"
"""Per-room furniture-fit analysis. NOT in pipeline at v1.
Blocked by B-C15-FURNITURE-FIT backlog item."""

DEP_PLOT_FAR_CEILING: str = "plot_far_ceiling"
"""Plot-level FAR ceiling from municipal bye-laws. NOT threaded
through ProblemAnalysisMetadata at v1. Blocked by
B-C15-FAR-CEILING-METADATA backlog item."""

DEP_ENVELOPE_POLYGON_SUBTRACTION: str = "envelope_polygon_subtraction"
"""Geometric subtraction of room rectangles from envelope rectangle
to identify L-shaped dead corners. NOT implemented at v1. Blocked
by B-C15-ENVELOPE-POLYGON-SUBTRACTION backlog item."""


# =============================================================================
# Helper: probe context for canonical dependencies
# =============================================================================

def probe_dependencies(
    placed_candidate: object,
    circulation_report: object,
    metadata: ProblemAnalysisMetadata,
) -> frozenset[str]:
    """Probe what dependencies are actually satisfied by the given
    upstream payload. Returned set goes into CheckContext.

    This is conservative — a dependency is "available" only if its
    canonical satisfaction criterion is met. The orchestrator uses
    this to compute the cheap NA-routing pre-pass.

    For dependencies not in this list (e.g., DEP_WINDOW_DATA), the
    probe never reports them as present at v1 — those checks will
    always defer.
    """
    available: set[str] = set()

    # c12_placement: probe for placed_rooms attribute
    pr = getattr(placed_candidate, "placed_rooms", None)
    if pr is not None and len(pr) > 0:
        available.add(DEP_C12_PLACEMENT)
        # geometry: every room has positive width_m and depth_m. C12
        # itself enforces this in PlacedRoom.__post_init__; we
        # defensively re-probe.
        if all(
            getattr(r, "width_m", 0.0) > 0.0 and getattr(r, "depth_m", 0.0) > 0.0
            for r in pr
        ):
            available.add(DEP_C12_PLACEMENT_GEOMETRY)

    # c14_graph: probe for a nodes/adjacency-like surface. We check
    # for the canonical C14 attribute name. Conservative — if C14
    # doesn't expose what we expect, the check defers.
    nodes = getattr(circulation_report, "nodes", None)
    if nodes is None:
        # Try alternative names C14 might use.
        nodes = getattr(circulation_report, "graph_nodes", None)
    if nodes is not None and len(nodes) > 0:
        available.add(DEP_C14_GRAPH)

    # c14_flags: probe for flag tuples
    if (
        getattr(circulation_report, "structural_flags", None) is not None
        or getattr(circulation_report, "preference_flags", None) is not None
    ):
        available.add(DEP_C14_FLAGS)

    # room_categories: must cover all placed_room_ids
    if pr is not None and len(pr) > 0:
        placed_ids = {r.room_id for r in pr}
        cats = metadata.room_categories
        if placed_ids.issubset(cats.keys()):
            available.add(DEP_ROOM_CATEGORIES)

    # floor_metadata: must be non-empty
    if metadata.floor_metadata and len(metadata.floor_metadata) > 0:
        available.add(DEP_FLOOR_METADATA)

    # main_entry: must resolve to a placed room
    if pr is not None and metadata.main_entry_room_id:
        placed_ids = {r.room_id for r in pr}
        if metadata.main_entry_room_id in placed_ids:
            available.add(DEP_MAIN_ENTRY)

    return frozenset(available)


__all__ = [
    "CheckContext",
    "Check",
    # canonical dependency names
    "DEP_C12_PLACEMENT",
    "DEP_C12_PLACEMENT_GEOMETRY",
    "DEP_C14_GRAPH",
    "DEP_C14_FLAGS",
    "DEP_ROOM_CATEGORIES",
    "DEP_FLOOR_METADATA",
    "DEP_MAIN_ENTRY",
    # v1-deferred dependency names
    "DEP_WINDOW_DATA",
    "DEP_FURNITURE_FIT",
    "DEP_PLOT_FAR_CEILING",
    "DEP_ENVELOPE_POLYGON_SUBTRACTION",
    # probe helper
    "probe_dependencies",
]
