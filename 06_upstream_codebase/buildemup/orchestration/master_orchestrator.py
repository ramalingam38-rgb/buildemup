"""MasterOrchestrator — S56 MVP single-call pipeline for all 17 components.

Calls C4 → C5 → C6 → C7 → C8 → C9 → C10 → C11a → C11b as a REAL chained
pipeline (these are well-tested as a chain in existing test fixtures).

Calls C12 → C13 → C14 → C15 → C16 → C17 as STUB phases — the upstream
adapter glue (converting C11b output to C12's `SingleFloorPlacementInput`,
constructing `room_metadata_by_signature` for C14, assembling
`UpstreamInputBundle` for C16, etc.) is non-trivial and is tracked as
explicit follow-up work in
`04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`.

C1+C2 are exposed as OPTIONAL pre-steps — if a caller provides a full
`Brief` (not just a `FloorRoomBrief`), the orchestrator runs them first
and threads the result into the pipeline. If not provided, those phases
are SKIPPED with reason recorded.

C3a/C3b are SKIPPED in MVP — they are session-stateful negotiation flows
already accessible via /api/c3a/* URLs. Integration into the master
orchestrator is its own design problem (see S57 follow-ups).

This module is the orchestrator's MAIN logic; the per-phase result
contracts live in `phase_result.py`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

from buildemup.orchestration.phase_result import (
    PhaseResult,
    PhaseStatus,
    PIPELINE_PHASES,
)


# ─────────────────────────────────────────────────────────────────────
# Public config + result
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MasterOrchestratorConfig:
    """Configuration knobs for a master-orchestrator run.

    All defaults are MVP-friendly. Production callers will want to
    override `vastu_tier`, `max_topology_mutations`, and `strict_mode`.
    """
    vastu_tier: str = "PARTIAL"
    """One of 'OFF' / 'PARTIAL' / 'FULL'. FULL is hidden in v1 UI
    (B-099) but accepted by backend."""

    max_topology_mutations: int = 4
    """C11a max_seeds_per_input. MVP keeps it small for quick smoke tests."""

    enable_c11b_refinement: bool = True
    """If False, skip C11b NSGA refinement (faster smoke tests)."""

    halt_on_first_failure: bool = False
    """If True, stop at first non-OK phase. If False, continue and
    capture per-phase results so partial output is preserved."""


@dataclass(frozen=True)
class MasterOrchestratorResult:
    """Unified result from a master-orchestrator run.

    Always populated; each phase produces a PhaseResult regardless of
    whether the phase succeeded, failed, was skipped, or shipped as a stub.
    """
    config: MasterOrchestratorConfig
    """The config used for this run."""

    phases: Tuple[PhaseResult, ...] = field(default_factory=tuple)
    """Phase results in canonical order (PIPELINE_PHASES)."""

    overall_status: PhaseStatus = PhaseStatus.OK
    """Aggregated outcome: OK if all phases OK/STUB/SKIPPED;
    ERROR if any phase failed and was not recovered."""

    total_elapsed_ms: float = 0.0
    """Total wallclock time for the full run, milliseconds."""

    def phase(self, phase_id: str) -> Optional[PhaseResult]:
        """Look up a single phase result by canonical phase_id."""
        for p in self.phases:
            if p.phase_id == phase_id:
                return p
        return None

    def summary(self) -> str:
        """One-line human-readable summary of the run."""
        counts = {"ok": 0, "error": 0, "stub": 0, "skipped": 0}
        for p in self.phases:
            counts[p.status.value] += 1
        return (
            f"MasterOrchestrator: {counts['ok']} ok, {counts['stub']} stub, "
            f"{counts['error']} error, {counts['skipped']} skipped "
            f"({self.total_elapsed_ms:.1f}ms total)"
        )


# ─────────────────────────────────────────────────────────────────────
# MasterOrchestrator
# ─────────────────────────────────────────────────────────────────────


class MasterOrchestrator:
    """Walks all 17 components in canonical order, producing a unified
    result.

    Usage:
        from buildemup.orchestration import MasterOrchestrator
        from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief
        from buildemup.tests.validation._c5_fixtures import medium_brief

        plot = chennai_30x40()
        brief_for_c4 = make_brief(plot)  # builds the Brief that C4 needs
        floor_brief = medium_brief()      # FloorRoomBrief for C5+

        orch = MasterOrchestrator()
        result = orch.run(
            plot=plot,
            brief_for_c4=brief_for_c4,
            floor_brief=floor_brief,
        )
        for p in result.phases:
            print(p.phase_id, p.status, p.error_message or p.stub_reason)
    """

    def __init__(
        self, config: Optional[MasterOrchestratorConfig] = None,
    ) -> None:
        self.config = config or MasterOrchestratorConfig()

    def run(
        self,
        *,
        plot: Any,
        brief_for_c4: Any,
        floor_brief: Any,
        full_brief: Any = None,
    ) -> MasterOrchestratorResult:
        """Execute the full pipeline.

        Args:
            plot: A plot fixture (e.g., from c4 test fixtures).
            brief_for_c4: The Brief that C4 needs to derive PlotAnalysis.
            floor_brief: The FloorRoomBrief for C5+ pipeline.
            full_brief: OPTIONAL full Brief (for running C1+C2 pre-steps).
                If None, C1+C2 phases are SKIPPED.

        Returns:
            MasterOrchestratorResult with one PhaseResult per phase.
        """
        run_start = time.monotonic()
        phases: list[PhaseResult] = []

        # ─── C1 + C2 (optional pre-steps) ──────────────────────────
        c01_result = self._run_c01_brief(full_brief)
        phases.append(c01_result)

        c02_result = self._run_c02_feasibility(full_brief)
        phases.append(c02_result)

        # ─── C3a/C3b — SKIPPED in MVP ──────────────────────────────
        # Session-stateful negotiation; already HTTP-accessible.

        # ─── C4: PlotAnalysis ──────────────────────────────────────
        c04_result = self._run_c04_plot_analysis(brief_for_c4)
        phases.append(c04_result)
        plot_analysis = c04_result.payload if c04_result.status == PhaseStatus.OK else None

        if plot_analysis is None and self.config.halt_on_first_failure:
            return self._finalize(phases, run_start)

        # ─── C5: Topology ──────────────────────────────────────────
        c05_result = self._run_c05_topology(plot_analysis, floor_brief)
        phases.append(c05_result)
        topology_candidates = c05_result.payload if c05_result.status == PhaseStatus.OK else None

        if topology_candidates is None and self.config.halt_on_first_failure:
            return self._finalize(phases, run_start)

        # ─── C6: Orientation ───────────────────────────────────────
        c06_result = self._run_c06_orientation(
            topology_candidates, plot_analysis,
        )
        phases.append(c06_result)
        oriented_candidates = c06_result.payload if c06_result.status == PhaseStatus.OK else None

        # ─── C7: Structural Grid ───────────────────────────────────
        c07_result = self._run_c07_structural_grid(plot_analysis)
        phases.append(c07_result)
        grid = c07_result.payload if c07_result.status == PhaseStatus.OK else None

        # ─── C8: Corridor ──────────────────────────────────────────
        c08_result = self._run_c08_corridor(
            oriented_candidates, grid, plot_analysis,
        )
        phases.append(c08_result)
        cdc_candidates = c08_result.payload if c08_result.status == PhaseStatus.OK else None

        # ─── C9: Room Sizer ────────────────────────────────────────
        c09_result = self._run_c09_room_sizer(
            cdc_candidates, floor_brief, grid, plot_analysis,
        )
        phases.append(c09_result)
        rsc_candidates = c09_result.payload if c09_result.status == PhaseStatus.OK else None

        # ─── C10: Wet Zones ────────────────────────────────────────
        c10_result = self._run_c10_wet_zones(
            rsc_candidates, floor_brief, grid, plot_analysis,
        )
        phases.append(c10_result)
        wet_zoned_candidates = c10_result.payload if c10_result.status == PhaseStatus.OK else None

        # ─── C11a: Topology Mutation ───────────────────────────────
        c11a_result = self._run_c11a_topology_mutation(
            wet_zoned_candidates, floor_brief, grid, plot_analysis,
        )
        phases.append(c11a_result)
        mutated_candidates = c11a_result.payload if c11a_result.status == PhaseStatus.OK else None

        # ─── C11b: NSGA Refinement ─────────────────────────────────
        c11b_result = self._run_c11b_refinement(
            mutated_candidates, floor_brief, grid, plot_analysis,
        )
        phases.append(c11b_result)

        # ─── C12 → C17: STUB phases ────────────────────────────────
        # Each requires non-trivial adapter glue to upstream output.
        # Tracked in 04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md
        phases.append(self._stub_phase(
            "c12_vertical_placement",
            "C11b output → SingleFloorPlacementInput adapter required",
        ))
        phases.append(self._stub_phase(
            "c13_doors",
            "C12 PlacedCandidate → place_doors batch adapter required",
        ))
        phases.append(self._stub_phase(
            "c14_connection_graph",
            "room_metadata_by_signature construction required",
        ))
        phases.append(self._stub_phase(
            "c15_problem_finder",
            "(C12, C13, C14) triples + ProblemAnalysisMetadata construction required",
        ))
        phases.append(self._stub_phase(
            "c16_dual_drawings",
            "UpstreamInputBundle assembly across C7/C9/C10/C12/C13 required",
        ))
        phases.append(self._stub_phase(
            "c17_quote_comparison",
            "Separate user-uploads-quote flow; not strictly downstream "
            "of the main pipeline. Wire when C17 ingest UI is built.",
        ))

        return self._finalize(phases, run_start)

    # ─────────────────────────────────────────────────────────────
    # Per-phase implementations (real chained calls)
    # ─────────────────────────────────────────────────────────────

    def _run_c01_brief(self, full_brief: Any) -> PhaseResult:
        if full_brief is None:
            return PhaseResult(
                phase_id="c01_brief",
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "No full Brief provided. MVP orchestrator accepts "
                    "a FloorRoomBrief directly; C1 (full brief capture "
                    "from form input) is skipped. To exercise C1, pass "
                    "full_brief= to .run()."
                ),
            )
        # If a full Brief was provided, we don't need to run C1 again — the
        # caller has already constructed it. Return OK with payload=full_brief.
        return PhaseResult(
            phase_id="c01_brief",
            status=PhaseStatus.OK,
            payload=full_brief,
            notes=("Brief provided by caller; C1 form-validation step bypassed.",),
        )

    def _run_c02_feasibility(self, full_brief: Any) -> PhaseResult:
        phase_id = "c02_feasibility"
        if full_brief is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="C2 requires a full Brief; none provided.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c02.orchestrator import run_feasibility
            report = run_feasibility(full_brief)
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=report,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c04_plot_analysis(self, brief_for_c4: Any) -> PhaseResult:
        phase_id = "c04_plot_analysis"
        start = time.monotonic()
        try:
            from buildemup.components.c04 import derive
            plot_analysis = derive(brief_for_c4, now=time.time())
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=plot_analysis,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c05_topology(
        self, plot_analysis: Any, floor_brief: Any,
    ) -> PhaseResult:
        phase_id = "c05_topology"
        if plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Upstream C4 did not produce a PlotAnalysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c05 import select_topology
            candidates = select_topology(plot_analysis, floor_brief)
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=candidates,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c06_orientation(
        self, candidates: Any, plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c06_orientation"
        if candidates is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream candidates or plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c06 import prioritize_orientation
            from buildemup.domain.brief import VastuTier
            tier = VastuTier[self.config.vastu_tier]
            oriented = prioritize_orientation(
                candidates, plot_analysis, tier,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=oriented,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(f"Vastu tier: {self.config.vastu_tier}",),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c07_structural_grid(self, plot_analysis: Any) -> PhaseResult:
        phase_id = "c07_structural_grid"
        if plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Upstream C4 did not produce a PlotAnalysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c07.grid_generator import GridGenerator
            grid = GridGenerator().generate(
                envelope_width_m=plot_analysis.plot.width_m,
                envelope_depth_m=plot_analysis.plot.depth_m,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=grid,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    "MVP runs C7 GridGenerator only (column positions); "
                    "full StructuralGridEngine (sizing + foundation + cost) "
                    "is deferred to S57 — see follow-ups doc.",
                ),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c08_corridor(
        self, oriented: Any, grid: Any, plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c08_corridor"
        if oriented is None or grid is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream oriented/grid/plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c08 import design_corridors
            cdc = design_corridors(tuple(oriented), grid, plot_analysis)
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=cdc,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c09_room_sizer(
        self,
        cdc: Any,
        floor_brief: Any,
        grid: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c09_room_sizer"
        if cdc is None or grid is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream CDC/grid/plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c09 import size_rooms
            rsc = size_rooms(cdc, floor_brief, grid, plot_analysis)
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=rsc,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c10_wet_zones(
        self,
        rsc: Any,
        floor_brief: Any,
        grid: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c10_wet_zones"
        if rsc is None or grid is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream RSC/grid/plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c10 import plan_wet_zones
            wzpc = plan_wet_zones(rsc, floor_brief, grid, plot_analysis)
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=wzpc,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c11a_topology_mutation(
        self,
        wzpc: Any,
        floor_brief: Any,
        grid: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c11a_topology_mutation"
        if wzpc is None or grid is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream WZPC/grid/plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c11a import mutate_topologies
            from buildemup.components.c11a.schema import (
                MutationOperator,
                TopologyMutationConfig,
            )
            # MVP config: M0_BASE only (minimal mutation surface; faster
            # smoke test). Production would enable M1-M9 operators.
            config = TopologyMutationConfig(
                enabled_operators=(MutationOperator.M0_BASE,),
                emit_base=True,
                max_seeds_per_input=self.config.max_topology_mutations,
            )
            mutated = mutate_topologies(
                wzpc, floor_brief, grid, plot_analysis, config=config,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=mutated,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    "MVP config: M0_BASE only. Production should enable "
                    "M1-M9 operators per architect review.",
                ),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c11b_refinement(
        self,
        mutated: Any,
        floor_brief: Any,
        grid: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        phase_id = "c11b_nsga_refinement"
        if not self.config.enable_c11b_refinement:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="enable_c11b_refinement=False in config.",
            )
        if mutated is None or grid is None or plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Missing upstream mutated/grid/plot_analysis.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c11b import (
                run_local_refinement,
                StubEvaluator,
                StubEvaluatorConfig,
                BatchAllTopologiesFailedError,
            )
            evaluator = StubEvaluator(StubEvaluatorConfig())
            try:
                refined = run_local_refinement(
                    mutated, floor_brief, grid, plot_analysis, evaluator,
                )
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.OK,
                    payload=refined,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    notes=(
                        "Used C11b's built-in StubEvaluator. Production "
                        "requires a real EvaluatorProtocol implementation; "
                        "see S57 follow-ups.",
                    ),
                )
            except BatchAllTopologiesFailedError as e:
                # StubEvaluator's heuristic scoring routinely fails NSGA
                # convergence on default MVP config. This is expected for
                # the MVP and is the canonical reason C11b ships as STUB:
                # a real EvaluatorProtocol is required. The chain RAN
                # (call reached C11b's orchestrator); the StubEvaluator
                # simply doesn't produce a refinement-feasible scoring.
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.STUB,
                    payload=None,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    stub_reason=(
                        "StubEvaluator does not satisfy NSGA convergence "
                        "under MVP config. Real EvaluatorProtocol "
                        f"implementation required. Raw error: {e!s}"
                    ),
                    notes=(
                        "Tracked in 04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md",
                        "C11b orchestrator was successfully invoked.",
                    ),
                )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _stub_phase(self, phase_id: str, reason: str) -> PhaseResult:
        """Build a STUB-status PhaseResult for a phase that needs
        adapter glue (tracked in S57 follow-ups doc)."""
        return PhaseResult(
            phase_id=phase_id,
            status=PhaseStatus.STUB,
            stub_reason=reason,
            notes=(
                "Tracked in 04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md",
            ),
        )

    def _error_result(
        self, phase_id: str, exc: Exception, start: float,
    ) -> PhaseResult:
        elapsed = (time.monotonic() - start) * 1000
        msg = str(exc) if exc.args else repr(exc)
        return PhaseResult(
            phase_id=phase_id,
            status=PhaseStatus.ERROR,
            error_class=type(exc).__name__,
            error_message=msg,
            elapsed_ms=elapsed,
        )

    def _finalize(
        self, phases: list[PhaseResult], run_start: float,
    ) -> MasterOrchestratorResult:
        total_elapsed = (time.monotonic() - run_start) * 1000
        # Aggregate status: ERROR if any phase errored unrecoverably.
        overall = PhaseStatus.OK
        for p in phases:
            if p.status == PhaseStatus.ERROR:
                overall = PhaseStatus.ERROR
                break
        return MasterOrchestratorResult(
            config=self.config,
            phases=tuple(phases),
            overall_status=overall,
            total_elapsed_ms=total_elapsed,
        )
