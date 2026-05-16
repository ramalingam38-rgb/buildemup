"""
BuildemUp — Component 11b — top-level orchestrator
=====================================================

Per SPEC v1.1 LOCKED § 0.0d (current surface only digest):

    def run_local_refinement(
        mutated_topology_candidates: tuple[MutatedTopologyCandidate, ...],
        floor_room_brief: FloorRoomBrief,
        grid: Grid,
        plot_analysis: PlotAnalysis,
        evaluator: EvaluatorProtocol,
        *,
        config: LocalRefinementConfig | None = None,
    ) -> tuple[RefinedCandidate, ...]: ...

Phase 0 captures the EnvironmentFingerprint. Phase 1 runs per-topology
NSGA-II via ``refine_one_topology``. Phase 2 assembles the candidate
tuple. Phase 3 builds the provenance record (currently returned via
``run_local_refinement_with_provenance``).

WARN/STRICT escalation (§ 5):
- STRICT: any PerTopologyError halts the batch with
  BatchAllTopologiesFailedError aggregation.
- WARN (default): per-topology errors accumulate; batch returns
  whatever succeeded. Only when EVERY topology fails do we raise
  BatchAllTopologiesFailedError.

The function also accepts an optional ``expected_environment_fingerprint``
for replay-mode strict equality checks (Inv 24 + Inv 29).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from buildemup.components.c11a.provenance import MutatedTopologyCandidate
from buildemup.components.c11b.config import (
    EnforcementMode,
    LocalRefinementConfig,
)
from buildemup.components.c11b.environment_fingerprint import (
    EnvironmentFingerprint,
    capture_environment_fingerprint,
)
from buildemup.components.c11b.errors import (
    BatchAllTopologiesFailedError,
    EnvironmentFingerprintMismatchError,
    MultiFloorRefinementNotSupportedError,
    PerTopologyError,
)
from buildemup.components.c11b.evaluator import EvaluatorProtocol
from buildemup.components.c11b.initialization import RoomSizeRequirement
from buildemup.components.c11b.phase1 import _PerTopologyResult, refine_one_topology
from buildemup.components.c11b.phase2 import assemble_refined_candidates
from buildemup.components.c11b.phase3 import assemble_provenance
from buildemup.components.c11b.provenance import LocalRefinementProvenance
from buildemup.components.c11b.schema import RefinedCandidate
from buildemup.components.c11b.telemetry import PerTopologyTelemetry


@dataclass(frozen=True)
class RefinementBatchResult:
    """Convenience wrapper carrying both the refined candidates and
    the provenance record. ``run_local_refinement`` returns just the
    candidates per the spec signature; tests use this wrapper via
    ``run_local_refinement_with_provenance``.
    """
    refined_candidates: tuple[RefinedCandidate, ...]
    provenance: LocalRefinementProvenance


def _extract_requirements_and_envelope(
    floor_room_brief: Any, grid: Any, plot_analysis: Any
) -> tuple[tuple[RoomSizeRequirement, ...], float, float]:
    """Pull the per-room dimension floors + envelope (w, d) out of the
    upstream artifacts.

    v1 implementation: best-effort extraction. ``FloorRoomBrief`` /
    ``Grid`` / ``PlotAnalysis`` shapes vary across upstream specs; we
    rely on a few well-known attribute names with defensive fallbacks.
    """
    requirements: list[RoomSizeRequirement] = []

    # Try canonical FloorRoomBrief.room_requirements first.
    rooms = (
        getattr(floor_room_brief, "room_requirements", None)
        or getattr(floor_room_brief, "rooms", None)
        or ()
    )
    for r in rooms:
        room_id = (
            getattr(r, "room_id", None)
            or getattr(r, "id", None)
            or getattr(r, "name", None)
        )
        if room_id is None:
            continue
        category = (
            getattr(r, "category", None)
            or getattr(r, "kind", None)
            or "other"
        )
        min_w = (
            getattr(r, "min_width_m", None)
            or getattr(r, "min_w", None)
            or getattr(r, "width_min", None)
        )
        min_d = (
            getattr(r, "min_depth_m", None)
            or getattr(r, "min_d", None)
            or getattr(r, "depth_min", None)
        )
        if min_w is None or min_d is None:
            continue
        requirements.append(
            RoomSizeRequirement(
                room_id=str(room_id),
                category=str(category),
                min_width_m=float(min_w),
                min_depth_m=float(min_d),
            )
        )

    # Envelope: pull from grid first, then plot_analysis.
    envelope_w = (
        getattr(grid, "envelope_width_m", None)
        or getattr(grid, "width_m", None)
        or getattr(plot_analysis, "envelope_width_m", None)
        or getattr(plot_analysis, "width_m", None)
        or 0.0
    )
    envelope_d = (
        getattr(grid, "envelope_depth_m", None)
        or getattr(grid, "depth_m", None)
        or getattr(plot_analysis, "envelope_depth_m", None)
        or getattr(plot_analysis, "depth_m", None)
        or 0.0
    )
    return tuple(requirements), float(envelope_w), float(envelope_d)


def run_local_refinement(
    mutated_topology_candidates: tuple[MutatedTopologyCandidate, ...],
    floor_room_brief: Any,
    grid: Any,
    plot_analysis: Any,
    evaluator: EvaluatorProtocol,
    *,
    config: LocalRefinementConfig | None = None,
    expected_environment_fingerprint: EnvironmentFingerprint | None = None,
) -> tuple[RefinedCandidate, ...]:
    """Top-level C11b entry point. Returns the diversity-ordered Pareto
    slice across all topologies.

    Use ``run_local_refinement_with_provenance`` if you also need the
    provenance record.
    """
    result = run_local_refinement_with_provenance(
        mutated_topology_candidates,
        floor_room_brief,
        grid,
        plot_analysis,
        evaluator,
        config=config,
        expected_environment_fingerprint=expected_environment_fingerprint,
    )
    return result.refined_candidates


def run_local_refinement_with_provenance(
    mutated_topology_candidates: tuple[MutatedTopologyCandidate, ...],
    floor_room_brief: Any,
    grid: Any,
    plot_analysis: Any,
    evaluator: EvaluatorProtocol,
    *,
    config: LocalRefinementConfig | None = None,
    expected_environment_fingerprint: EnvironmentFingerprint | None = None,
) -> RefinementBatchResult:
    """Same as ``run_local_refinement`` but returns the
    ``RefinementBatchResult`` carrying both candidates + provenance."""
    cfg = config or LocalRefinementConfig()

    # Phase 0 — capture environment fingerprint + replay check.
    fp = capture_environment_fingerprint(master_seed=cfg.master_seed)
    if expected_environment_fingerprint is not None:
        if not fp.matches(expected_environment_fingerprint):
            raise EnvironmentFingerprintMismatchError(
                f"C11b: environment fingerprint mismatch on replay. "
                f"Expected hash={expected_environment_fingerprint.fingerprint_hash}; "
                f"got hash={fp.fingerprint_hash}. "
                f"Cache key root has changed."
            )

    requirements, envelope_w, envelope_d = _extract_requirements_and_envelope(
        floor_room_brief, grid, plot_analysis
    )

    per_topology_results: list[_PerTopologyResult] = []
    failure_summaries: list[str] = []
    skipped_multifloor = 0
    timed_out_count = 0
    failed_count = 0

    for topology_index, mtc in enumerate(mutated_topology_candidates):
        try:
            ptr = refine_one_topology(
                mtc=mtc,
                topology_index=topology_index,
                requirements=requirements,
                envelope_w=envelope_w,
                envelope_d=envelope_d,
                evaluator=evaluator,
                config=cfg,
            )
            per_topology_results.append(ptr)
        except MultiFloorRefinementNotSupportedError as exc:
            skipped_multifloor += 1
            failure_summaries.append(
                f"topology_index={topology_index}: skipped (multi-floor)"
            )
            if cfg.enforcement_mode == EnforcementMode.STRICT:
                # STRICT: re-raise immediately; nothing else attempted.
                raise
            # Inject an empty placeholder so provenance length matches.
            per_topology_results.append(
                _PerTopologyResult(
                    refined_candidates=(),
                    telemetry=PerTopologyTelemetry(
                        topology_index=topology_index,
                        completed_generations=0,
                        longest_generation_seconds=0.0,
                        skipped_candidates_total=0,
                    ),
                    resolved_objective_count=0,
                )
            )
            _ = exc
        except PerTopologyError as exc:
            # Bucket timeouts vs other per-topology errors.
            from buildemup.components.c11b.errors import PerTopologyTimeoutError

            if isinstance(exc, PerTopologyTimeoutError):
                timed_out_count += 1
            else:
                failed_count += 1
            failure_summaries.append(
                f"topology_index={topology_index}: {type(exc).__name__}: {exc}"
            )
            if cfg.enforcement_mode == EnforcementMode.STRICT:
                raise
            per_topology_results.append(
                _PerTopologyResult(
                    refined_candidates=(),
                    telemetry=PerTopologyTelemetry(
                        topology_index=topology_index,
                        completed_generations=0,
                        longest_generation_seconds=0.0,
                        skipped_candidates_total=0,
                    ),
                    resolved_objective_count=0,
                )
            )

    refined_candidates = assemble_refined_candidates(tuple(per_topology_results))

    # WARN-mode BatchAllTopologiesFailedError: every topology failed.
    if (
        cfg.enforcement_mode == EnforcementMode.WARN
        and mutated_topology_candidates
        and not refined_candidates
    ):
        raise BatchAllTopologiesFailedError(
            f"C11b: every topology in the batch failed under WARN mode. "
            f"Summary: {'; '.join(failure_summaries) or 'no detail'}"
        )

    provenance = assemble_provenance(
        environment_fingerprint=fp,
        config=cfg,
        evaluator=evaluator,
        batch_size=len(mutated_topology_candidates),
        accepted_count=len(refined_candidates),
        skipped_multifloor_count=skipped_multifloor,
        timed_out_topology_count=timed_out_count,
        failed_topology_count=failed_count,
        per_topology_results=tuple(per_topology_results),
        failure_summaries=tuple(failure_summaries),
    )

    return RefinementBatchResult(
        refined_candidates=refined_candidates, provenance=provenance
    )


__all__ = [
    "RefinementBatchResult",
    "run_local_refinement",
    "run_local_refinement_with_provenance",
]
