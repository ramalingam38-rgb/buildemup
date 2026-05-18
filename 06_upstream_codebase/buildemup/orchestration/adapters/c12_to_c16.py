"""C7 + C10 + C12 + C13 + C14 (+ C15) → C16 bundle builder (S57 follow-up #8).

C16's `render_drawings_batch` requires:
  - `selection_results: tuple[SelectionResult, ...]` — one per drawable
    candidate, carrying replay_identity + audit_metadata.
  - `upstream_inputs_per: tuple[UpstreamInputBundle, ...]` — parallel
    tuple of upstream bundles. Each bundle aggregates one floor's worth
    of grid + wet zones + doors + circulation reports plus the project-
    level plot analysis.

This module assembles both, sourcing:
  - placed rooms + shared edges from C12.PlacedCandidate
  - grid columns + perimeter walls from C7 (Grid extracted from the
    full StructuralGridOutput or MVP-compat raw Grid)
  - wet-zone plans + risers from C10 (best-effort 1:1 join — see note)
  - doors from C13.SuccessfulDoorPlacement
  - circulation flags from C14 (best-effort)
  - per-candidate ProblemReport from C15 (when available)

Per-candidate wet-zone-plan correctness note: C10 runs BEFORE C11a's
mutations, so its per-candidate plans were produced from un-mutated
topologies. v1 uses the first available C10 plan for every drawable
candidate — adequate to produce visually-readable drawings on the
smoke fixture while we wait for the proper per-candidate re-planning
in v1+ (tracked under B-NEW post-B-238 architect feedback).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Optional

from buildemup.components.c16 import (
    CandidateRanking,
    JurisdictionProfile,
    SelectionAuditMetadata,
    SelectionReason,
    SelectionReplayIdentity,
    SelectionResult,
    UpstreamInputBundle,
)


# ─────────────────────────────────────────────────────────────────────
# Multi-floor candidate wrapper
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_FLOOR_LABEL = "F0"


@dataclass(frozen=True)
class _SingleFloorMulti:
    """Duck-typed shim that satisfies C16's `multifloor_candidate`
    attribute expectations on top of a single-floor PlacedCandidate.

    The bundle docstring says it needs `per_floor_placements` as a
    tuple of (floor_label, PlacedCandidate). v1 only supports single-
    floor briefs end-to-end; wrapping the lone PlacedCandidate as
    a 1-tuple here is the minimal valid value.
    """
    per_floor_placements: tuple[tuple[str, Any], ...]
    source_multifloor_candidate_signature: str


def _wrap_as_multifloor(
    placed_candidate: Any, floor_label: str = _DEFAULT_FLOOR_LABEL,
) -> _SingleFloorMulti:
    sig = placed_candidate.source_refined_candidate_signature
    return _SingleFloorMulti(
        per_floor_placements=((floor_label, placed_candidate),),
        source_multifloor_candidate_signature=f"mf-shim:{sig}",
    )


# ─────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────


def _extract_grid(c07_payload: Any) -> Any | None:
    """Pull the Grid object out of C7's payload (full-engine vs MVP).

    Mirrors `MasterOrchestrator._extract_grid` so the adapter is
    self-contained.
    """
    if c07_payload is None:
        return None
    grid_attr = getattr(c07_payload, "grid", None)
    if grid_attr is not None:
        return grid_attr
    return c07_payload  # MVP-compat path: payload IS the Grid.


def _first_wet_zone_plan(c10_payload: Any) -> Any | None:
    """Return the first WetZonePlan from a C10 candidate tuple.

    C10's output is a tuple of WetZonePlannedCandidate; each has a
    `.wet_zone_plan` attribute (the C16-friendly shape). Returns None
    on empty input.
    """
    if not c10_payload:
        return None
    first = c10_payload[0]
    return getattr(first, "wet_zone_plan", None)


def _index_c13_by_signature(c13_payload: Any) -> dict[str, Any]:
    if c13_payload is None:
        return {}
    out: dict[str, Any] = {}
    for placement in getattr(c13_payload, "successful", ()):
        sig = getattr(placement, "source_placed_candidate_signature", None)
        if sig:
            out[sig] = placement
    return out


def _index_c14_by_signature(c14_payload: Any) -> dict[str, Any]:
    if c14_payload is None:
        return {}
    out: dict[str, Any] = {}
    for report in getattr(c14_payload, "successful", ()):
        sig = (
            getattr(report, "source_placed_candidate_signature", None)
            or getattr(report, "source_refined_candidate_signature", None)
        )
        if sig:
            out[sig] = report
    return out


def _index_c15_by_signature(c15_payload: Any) -> dict[str, Any]:
    """C15 reports come back wrapped in SuccessfulProblemAnalysis."""
    if c15_payload is None:
        return {}
    out: dict[str, Any] = {}
    for entry in getattr(c15_payload, "successful", ()):
        sig = getattr(entry, "source_placed_candidate_signature", None)
        report = getattr(entry, "report", None)
        if sig and report is not None:
            out[sig] = report
    return out


# ─────────────────────────────────────────────────────────────────────
# Selection-result construction
# ─────────────────────────────────────────────────────────────────────


def _build_selection_result(
    *,
    layout_signature: str,
    rank_position: int,
    upstream_problem_report: Any | None,
    timestamp_utc: str,
) -> SelectionResult:
    """Build a single-ranking SelectionResult tagged with the orchestrator
    as the selector (DEFAULT_FIRST reason — the orchestrator surfaces
    every candidate that survived the chain, not a ranker-driven
    selection)."""
    ranking = (
        CandidateRanking(
            layout_signature=layout_signature,
            rank_position=rank_position,
            score=0.0,
            selection_marker=True,
        ),
    )
    upstream_reports = (
        (upstream_problem_report,) if upstream_problem_report is not None else ()
    )
    replay_identity = SelectionReplayIdentity(
        selected_layout_signature=layout_signature,
        selector_version="orch-s59-1.0",
        selection_reason=SelectionReason.DEFAULT_FIRST,
        candidate_ranking_snapshot=ranking,
        upstream_problem_reports=upstream_reports,
    )
    audit_metadata = SelectionAuditMetadata(
        selection_timestamp_utc=timestamp_utc,
    )
    return SelectionResult(
        replay_identity=replay_identity,
        audit_metadata=audit_metadata,
    )


# ─────────────────────────────────────────────────────────────────────
# Bundle construction
# ─────────────────────────────────────────────────────────────────────


def _build_bundle(
    *,
    placed_candidate: Any,
    grid: Any,
    wet_zone_plan: Any | None,
    doors: tuple,
    circulation_report: Any | None,
    plot_analysis: Any,
    floor_label: str = _DEFAULT_FLOOR_LABEL,
) -> UpstreamInputBundle:
    """Assemble one UpstreamInputBundle from upstream payloads."""
    multifloor = _wrap_as_multifloor(placed_candidate, floor_label)

    grids_by_floor = {floor_label: grid}
    wet_zone_plans_by_floor = (
        {floor_label: wet_zone_plan} if wet_zone_plan is not None else {}
    )
    doors_by_floor = {floor_label: tuple(doors)}
    circulation_reports_by_floor = (
        {floor_label: circulation_report}
        if circulation_report is not None else {}
    )

    return UpstreamInputBundle(
        multifloor_candidate=multifloor,
        grids_by_floor=grids_by_floor,
        wet_zone_plans_by_floor=wet_zone_plans_by_floor,
        doors_by_floor=doors_by_floor,
        plot_analysis=plot_analysis,
        circulation_reports_by_floor=circulation_reports_by_floor,
        upstream_cache_key=f"orch-s59:{placed_candidate.source_refined_candidate_signature}",
    )


# ─────────────────────────────────────────────────────────────────────
# Public entry
# ─────────────────────────────────────────────────────────────────────


def build_c16_inputs_from_upstream(
    *,
    c07_payload: Any,
    c10_payload: Any,
    c12_payload: Any,
    c13_payload: Any,
    c14_payload: Any,
    c15_payload: Any,
    plot_analysis: Any,
) -> tuple[tuple[SelectionResult, ...], tuple[UpstreamInputBundle, ...]]:
    """Assemble parallel tuples for `render_drawings_batch`.

    A candidate makes the cut only if it has a matching C13
    SuccessfulDoorPlacement — without doors there's nothing to render
    on. C14 + C15 reports are optional pass-throughs.
    """
    if c12_payload is None or c13_payload is None:
        return ((), ())

    grid = _extract_grid(c07_payload)
    if grid is None or plot_analysis is None:
        return ((), ())

    wet_zone_plan = _first_wet_zone_plan(c10_payload)
    c13_by_sig = _index_c13_by_signature(c13_payload)
    c14_by_sig = _index_c14_by_signature(c14_payload)
    c15_by_sig = _index_c15_by_signature(c15_payload)

    timestamp_utc = (
        datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    selection_results: list[SelectionResult] = []
    bundles: list[UpstreamInputBundle] = []

    for rank, placed in enumerate(
        getattr(c12_payload, "placed_candidates", ()), start=1,
    ):
        sig = placed.source_refined_candidate_signature
        c13_placement = c13_by_sig.get(sig)
        if c13_placement is None:
            continue  # Without doors C16 can't render anything.
        doors = getattr(c13_placement, "doors", ())
        circulation_report = c14_by_sig.get(sig)
        problem_report = c15_by_sig.get(sig)

        try:
            bundle = _build_bundle(
                placed_candidate=placed,
                grid=grid,
                wet_zone_plan=wet_zone_plan,
                doors=doors,
                circulation_report=circulation_report,
                plot_analysis=plot_analysis,
            )
            sel = _build_selection_result(
                layout_signature=sig,
                rank_position=rank,
                upstream_problem_report=problem_report,
                timestamp_utc=timestamp_utc,
            )
        except Exception:
            # Per-candidate construction failure → drop this candidate
            # from the batch but keep processing the rest. The orchestrator
            # surfaces total counts in its notes line.
            continue

        bundles.append(bundle)
        selection_results.append(sel)

    return tuple(selection_results), tuple(bundles)


__all__ = ["build_c16_inputs_from_upstream"]
