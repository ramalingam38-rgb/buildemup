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

    enable_full_structural_engine: bool = True
    """If True (default S57+), C7 runs the full StructuralGridEngine
    (grid + sizing + foundation + cost). If False, runs GridGenerator
    only (S56-MVP behaviour). See S57 follow-up #1."""

    enable_full_mutation_operators: bool = False
    """If True, C11a enables M0_BASE + M1-M9 operators. Default False
    keeps the smoke-test surface small. See S57 follow-up #2."""

    use_real_c11b_evaluator: bool = False
    """If True, C11b uses the orchestration MultiObjectiveEvaluator
    (real evaluator with smooth NSGA-friendly objectives). Default
    False keeps the StubEvaluator path active so existing smoke tests
    stay deterministic. See S57 follow-up #3."""

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
        # When the full engine runs (S57 #1), payload is a
        # StructuralGridOutput with .grid; when the MVP GridGenerator
        # path is active, payload IS the Grid. Downstream phases only
        # need the Grid object, so extract uniformly.
        grid = self._extract_grid(c07_result)

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

        # ─── C12: Vertical placement (S57 follow-up #4) ────────────
        # Adapter glue (orchestration/adapters/c11b_to_c12.py) builds
        # SingleFloorPlacementInput tuples from the upstream chain.
        c12_result = self._run_c12_vertical_placement(
            mutated_candidates,
            c11b_result.payload if c11b_result.status == PhaseStatus.OK else None,
            plot_analysis,
        )
        phases.append(c12_result)
        c12_payload = c12_result.payload if c12_result.status == PhaseStatus.OK else None

        # ─── C13: Doors (S57 follow-up #5) ────────────────────────
        c13_result = self._run_c13_doors(c12_payload)
        phases.append(c13_result)
        c13_payload = c13_result.payload if c13_result.status == PhaseStatus.OK else None

        # ─── C14: Connection graph (S57 follow-up #6) ─────────────
        c14_result = self._run_c14_connection_graph(c12_payload, c13_payload)
        phases.append(c14_result)

        # ─── C15 → C17: STUB phases (S57 follow-ups #7/#8/#9) ─────
        # C15 needs (C12, C13, C14) triples + metadata. C16 needs
        # UpstreamInputBundle. C17 is a separate flow.
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
        """C7 — structural grid + (optionally) sizing + foundation + cost.

        When `config.enable_full_structural_engine=True` (default), runs
        the full `StructuralGridEngine().execute(...)` and the payload
        is a `StructuralGridOutput` (carries grid + structure + foundation
        + cost + sensitivity). When False, falls back to the S56-MVP
        `GridGenerator().generate(...)` and the payload is the Grid
        directly (compat path for tests that pin the MVP shape).
        """
        phase_id = "c07_structural_grid"
        if plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Upstream C4 did not produce a PlotAnalysis.",
            )
        start = time.monotonic()
        try:
            if self.config.enable_full_structural_engine:
                from buildemup.components.c07_structural_grid import (
                    StructuralGridEngine,
                    StructuralGridInput,
                )
                from buildemup.kb.building_types import BuildingType
                # City is best-effort: PlotAnalysis carries plot info
                # but not always a city string. Default to "chennai"
                # (which has full rate-provider coverage); the cost
                # estimator falls back gracefully for unsupported
                # cities.
                city = (
                    getattr(plot_analysis, "city", None)
                    or getattr(plot_analysis.plot, "city", None)
                    or "chennai"
                ).lower()
                inp = StructuralGridInput(
                    envelope_width_m=plot_analysis.plot.width_m,
                    envelope_depth_m=plot_analysis.plot.depth_m,
                    floors_above_ground=2,
                    city=city,
                    seismic_zone="II",
                    building_type=BuildingType.RESIDENTIAL_SINGLE_FAMILY,
                )
                output = StructuralGridEngine().execute(inp)
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.OK,
                    payload=output,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    notes=(
                        "Full StructuralGridEngine — grid + sizing + "
                        "foundation + cost. S57 #1 closed.",
                        f"City: {city}; floors_above_ground=2 (orchestrator "
                        "default; see #11 for free-form input).",
                        f"Cost (exact): ₹{output.cost.exact_value:,.0f}; "
                        f"Foundation type: {output.foundation.type}.",
                    ),
                )
            # MVP-compat path: grid only.
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
                    "set enable_full_structural_engine=True for full "
                    "structural sizing + foundation + cost.",
                ),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    @staticmethod
    def _extract_grid(c07_result: PhaseResult) -> Any:
        """Pull the Grid object out of C7's payload (full-engine vs MVP)."""
        if c07_result.status != PhaseStatus.OK or c07_result.payload is None:
            return None
        payload = c07_result.payload
        # Full-engine path: StructuralGridOutput.grid
        grid_attr = getattr(payload, "grid", None)
        if grid_attr is not None:
            return grid_attr
        # MVP path: payload IS the Grid
        return payload

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
            if self.config.enable_full_mutation_operators:
                # S57 #2: full operator suite (M0 + M1-M9). Larger
                # mutation surface; useful for diversity testing or
                # downstream coverage runs.
                enabled = (
                    MutationOperator.M0_BASE,
                    MutationOperator.M1_HORIZ_FLIP,
                    MutationOperator.M2_VERT_FLIP,
                    MutationOperator.M3A_STAIR_EAST,
                    MutationOperator.M3B_STAIR_WEST,
                    MutationOperator.M3C_STAIR_NE,
                    MutationOperator.M4_CORRIDOR_INV,
                    MutationOperator.M5_ZONE_SWAP,
                    MutationOperator.M6_WET_ROTATE,
                    MutationOperator.M7A_GRID_3_3,
                    MutationOperator.M7B_GRID_2_7,
                    MutationOperator.M8_VERT_REARR,
                    MutationOperator.M9A_ENTRY_CTR,
                    MutationOperator.M9B_ENTRY_W,
                    MutationOperator.M9C_ENTRY_E,
                    MutationOperator.M9D_ENTRY_OFF,
                )
            else:
                # MVP config: M0_BASE only (minimal mutation surface;
                # faster smoke test).
                enabled = (MutationOperator.M0_BASE,)
            config = TopologyMutationConfig(
                enabled_operators=enabled,
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
                    f"Operators enabled: {len(enabled)} "
                    f"({'full M0-M9' if self.config.enable_full_mutation_operators else 'M0_BASE only'}).",
                    f"Variants produced: {len(mutated)}.",
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
            brief_for_c11b = floor_brief
            if self.config.use_real_c11b_evaluator:
                from buildemup.orchestration.evaluators import (
                    build_c11b_brief_shim_from_upstream,
                    build_real_evaluator_from_upstream,
                )
                evaluator = build_real_evaluator_from_upstream(
                    c11a_payload=mutated,
                    plot_analysis=plot_analysis,
                )
                # C11b's brief contract expects per-room min dims that
                # the canonical FloorRoomBrief (used by C5/C8/C9)
                # doesn't carry. Build a shim from upstream so C11b's
                # NSGA actually has the constraint surface it needs.
                brief_for_c11b = build_c11b_brief_shim_from_upstream(mutated)
                evaluator_kind = "MultiObjectiveEvaluator"
            else:
                evaluator = StubEvaluator(StubEvaluatorConfig())
                evaluator_kind = "StubEvaluator"
            try:
                refined = run_local_refinement(
                    mutated, brief_for_c11b, grid, plot_analysis, evaluator,
                )
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.OK,
                    payload=refined,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    notes=(
                        f"Evaluator: {evaluator_kind}.",
                        f"Refined candidates: {len(refined)}.",
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

    def _run_c12_vertical_placement(
        self,
        c11a_payload: Any,
        c11b_payload: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        """C12 phase — single-floor placement via place_and_align.

        Builds SingleFloorPlacementInput tuples via the
        orchestration.adapters.c11b_to_c12 module. Uses the documented
        RefinedCandidate path if C11b shipped OK, else falls back to
        the C11a MutatedTopologyCandidate path (per S57 follow-up #4
        STUB-fallback discussion — #3 deferred).
        """
        phase_id = "c12_vertical_placement"
        if plot_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Upstream C4 did not produce a PlotAnalysis.",
            )
        if c11a_payload is None and c11b_payload is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "No upstream candidates available (C11a and C11b "
                    "both produced no payload)."
                ),
            )
        start = time.monotonic()
        try:
            from buildemup.components.c12 import (
                PlacementConfig,
                place_and_align,
            )
            from buildemup.orchestration.adapters import (
                build_single_floor_inputs_from_upstream,
            )
            inputs = build_single_floor_inputs_from_upstream(
                c11a_payload=c11a_payload,
                c11b_payload=c11b_payload,
                plot_analysis=plot_analysis,
            )
            batch = place_and_align(
                single_floor_inputs=inputs,
                config=PlacementConfig(strict_mode=False),
                c11b_env_fingerprint_hash="orch:s57:c12_fallback",
            )
            via_refined = c11b_payload is not None
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=batch,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    (
                        "Adapter path: RefinedCandidate (primary)."
                        if via_refined
                        else "Adapter path: MutatedTopologyCandidate "
                             "(fallback while C11b ships STUB; S57 #3 pending)."
                    ),
                    f"Inputs adapted: {len(inputs)}",
                    f"Placed: {len(batch.placed_candidates)}, "
                    f"Failures: {len(batch.failures)}",
                ),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c13_doors(self, c12_payload: Any) -> PhaseResult:
        """C13 phase — door placement via place_doors (S57 follow-up #5).

        Consumes C12's PlacementBatchResult; pipes successful
        placed_candidates through C13's `place_doors` with WARN-mode
        config so per-candidate failures (e.g., the documented sparse-
        edge problem from the C13 adversarial corpus) don't halt the
        phase.
        """
        phase_id = "c13_doors"
        if c12_payload is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason="Upstream C12 did not produce a placement batch.",
            )
        start = time.monotonic()
        try:
            from buildemup.components.c13 import (
                DoorPlacementConfig,
                place_doors,
            )
            batch = place_doors(
                placed_candidates=c12_payload.placed_candidates,
                config=DoorPlacementConfig(strict_mode=False),
                c12_cache_key=c12_payload.cache_key,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=batch,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    f"C12 inputs: {len(c12_payload.placed_candidates)}",
                    f"Doors placed: {len(batch.successful)}, "
                    f"Failures: {len(batch.failed)}",
                    "Per-candidate failures are normal — C12's slicing-"
                    "tree often produces sparse shared edges (filed "
                    "B-C12-EDGE-DENSITY).",
                ),
            )
        except Exception as e:
            return self._error_result(phase_id, e, start)

    def _run_c14_connection_graph(
        self, c12_payload: Any, c13_payload: Any,
    ) -> PhaseResult:
        """C14 phase — circulation-graph analysis (S57 follow-up #6).

        Builds the room_metadata_by_signature dict from C12 placed
        rooms (for categories) + C13 doors (for main-entry flag) via
        the adapter, then calls C14's batch orchestrator.
        """
        phase_id = "c14_connection_graph"
        if c12_payload is None or c13_payload is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "Upstream C12 and/or C13 did not produce a payload "
                    "(downstream phase cannot run without both)."
                ),
            )
        start = time.monotonic()
        try:
            from buildemup.components.c14 import (
                CirculationConfig,
                analyze_circulation_batch,
            )
            from buildemup.orchestration.adapters import (
                build_room_metadata_by_signature,
            )
            metadata = build_room_metadata_by_signature(
                c12_payload=c12_payload,
                c13_payload=c13_payload,
            )
            batch = analyze_circulation_batch(
                batch=c13_payload,
                room_metadata_by_signature=metadata,
                config=CirculationConfig(),
                strict_mode=False,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=batch,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    f"C13 placements analyzed: {len(c13_payload.successful)}",
                    f"Analyses produced: {len(batch.successful)} OK, "
                    f"{len(batch.failed)} failed",
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
