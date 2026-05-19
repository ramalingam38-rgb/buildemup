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

        # ─── C3a: extreme-case detection (S59 follow-up #10) ──────
        # Async-flags mode: detection-only, never halts the pipeline.
        # The full negotiation flow (C3b) stays at /api/extreme-case/*.
        c03a_result = self._run_c3a_detection(
            full_brief,
            c02_result.payload if c02_result.status == PhaseStatus.OK else None,
        )
        phases.append(c03a_result)

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
        c14_payload = c14_result.payload if c14_result.status == PhaseStatus.OK else None

        # ─── C15: Problem finder (S59 follow-up #7) ───────────────
        c15_result = self._run_c15_problem_finder(
            c12_payload, c13_payload, c14_payload,
        )
        phases.append(c15_result)
        c15_payload = c15_result.payload if c15_result.status == PhaseStatus.OK else None

        # ─── C16: Dual drawings (S59 follow-up #8) ────────────────
        c16_result = self._run_c16_dual_drawings(
            c07_result.payload if c07_result.status == PhaseStatus.OK else None,
            c10_result.payload if c10_result.status == PhaseStatus.OK else None,
            c12_payload, c13_payload, c14_payload, c15_payload,
            plot_analysis,
        )
        phases.append(c16_result)

        # ─── C17: Quote comparison ─────────────────────────────────
        # Always SKIPPED inside the master pipeline — C17 is the
        # user-uploaded-quote flow accessed separately via
        # /api/quote/compare (S59 follow-up #9). The master
        # orchestrator skips it deliberately so a no-quote run still
        # produces a complete 17-phase result.
        phases.append(PhaseResult(
            phase_id="c17_quote_comparison",
            status=PhaseStatus.SKIPPED,
            skip_reason=(
                "C17 runs as a separate user-uploaded-quote flow via "
                "POST /api/quote/compare. The master pipeline does not "
                "invoke C17 because it has no contractor quote to "
                "compare. Wire a quote upload to that endpoint instead."
            ),
            notes=(
                "S59 follow-up #9: see api/quote_endpoint.py.",
            ),
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

    def _run_c3a_detection(
        self, full_brief: Any, gap_analysis: Any,
    ) -> PhaseResult:
        """C3a extreme-case detection (S59 follow-up #10) — async-flags.

        Runs only the detector step; does NOT enter the multi-turn
        negotiation flow (that's C3b at /api/extreme-case/*). Detected
        cases surface as a list in PhaseResult.payload + notes. Phase
        always ships OK unless a hard exception fires — detection
        finding cases is information, not failure.
        """
        phase_id = "c03a_extreme_case_detection"
        if full_brief is None or gap_analysis is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "C3a detection requires a full Brief + C2 "
                    "DesignGapAnalysis. Pass full_brief= to .run() to "
                    "enable; otherwise the pipeline continues without "
                    "extreme-case flags."
                ),
            )
        start = time.monotonic()
        try:
            from buildemup.components.c03a.detector import (
                ExtremeCaseDetector,
            )
            cases = ExtremeCaseDetector.detect(gap_analysis, full_brief)
            case_summary = tuple(
                {
                    "case_id": c.case_id.value if hasattr(c.case_id, "value") else str(c.case_id),
                    "category": (
                        c.category.value if hasattr(c.category, "value")
                        else str(c.category)
                    ),
                }
                for c in cases
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload={"cases_detected": case_summary},
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    f"Extreme cases detected: {len(cases)}",
                    "Async-flags mode: pipeline continues regardless.",
                    "For interactive negotiation, route to "
                    "POST /api/extreme-case/check (C3b flow).",
                ),
            )
        except Exception as e:  # noqa: BLE001
            return self._error_result(phase_id, e, start)

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
            try:
                oriented = prioritize_orientation(
                    candidates, plot_analysis, tier,
                )
            except NotImplementedError as e:
                # S59 ext: B-107 — C6 explicitly rejects intercardinal
                # facing (NE/SE/SW/NW). Downgrade to STUB so downstream
                # phases SKIP cleanly instead of every cascade-erroring.
                msg = str(e)
                if "intercardinal facing reserved" in msg or "B-107" in msg:
                    return PhaseResult(
                        phase_id=phase_id,
                        status=PhaseStatus.STUB,
                        elapsed_ms=(time.monotonic() - start) * 1000,
                        stub_reason=(
                            "C6 does not yet support intercardinal "
                            "facing (NE/SE/SW/NW) — tracked under B-107. "
                            "v1 supports cardinal facing only. Rotate "
                            "the plot to a cardinal facing or wait for "
                            "B-107 to extend orientation logic."
                        ),
                        notes=(f"Underlying: {msg[:160]}",),
                    )
                raise
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
            from buildemup.components.c08.errors import (
                CorridorSelfIntersectionError,
            )
            try:
                cdc = design_corridors(tuple(oriented), grid, plot_analysis)
            except CorridorSelfIntersectionError as e:
                # S59 ext: C8 topology dispatch occasionally produces
                # overlapping corridor segments on large plots with
                # complex briefs (delhi_60x90 + 4BR+study). Downgrade
                # to STUB rather than cascade-error the pipeline.
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.STUB,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    stub_reason=(
                        "C8 corridor self-intersection (Inv 11) — the "
                        "topology dispatch produced overlapping segments. "
                        "Common on large plots with high room counts. "
                        "Tracked under B-C8-LARGE-PLOT-COVERAGE."
                    ),
                    notes=(
                        f"Underlying: CorridorSelfIntersectionError",
                        f"Detail: {str(e)[:200]}",
                    ),
                )
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
            from buildemup.components.c09.errors import (
                BatchSizingInfeasibleError,
                RoomSizingInfeasibleError,
            )
            try:
                rsc = size_rooms(cdc, floor_brief, grid, plot_analysis)
            except BatchSizingInfeasibleError as e:
                # S59 ext / B-C9 amendment: every input candidate failed
                # C9 sizing. The common cause on tight plots is **Inv 9
                # mathematical infeasibility**: Σ liveability_min_area
                # exceeds the buildable envelope minus corridor — i.e.
                # the brief asks for more area than the plot can hold.
                # This is NOT a search-budget problem; no amount of
                # additional iteration would find a feasible packing.
                # The amendment surfaces the worst-case deficit so the
                # UI can show "your brief is ~X m² over capacity" rather
                # than a generic exhaustion message.
                worst_deficit = 0.0
                worst_envelope = 0.0
                worst_min_area = 0.0
                deterministic_infeasible = False
                for _idx, exc in e.failures:
                    if isinstance(exc, RoomSizingInfeasibleError):
                        deterministic_infeasible = True
                        if exc.deficit_m2 > worst_deficit:
                            worst_deficit = exc.deficit_m2
                            worst_envelope = exc.envelope_minus_corridor_m2
                            worst_min_area = exc.total_liveability_min_area_m2
                if deterministic_infeasible:
                    stub_reason = (
                        f"Brief exceeds plot capacity by "
                        f"~{worst_deficit:.1f} m² (NBC-minimum room "
                        f"areas sum to {worst_min_area:.1f} m² but the "
                        f"buildable envelope minus corridor is only "
                        f"{worst_envelope:.1f} m²). Inv 9 — mathematical "
                        f"infeasibility, not a search budget issue. "
                        f"Remediation: drop a room (try removing pooja "
                        f"or utility for the tightest reduction) or "
                        f"enlarge the plot."
                    )
                else:
                    stub_reason = (
                        "All input candidates failed C9 sizing for a "
                        "non-area reason (likely width-infeasibility, "
                        "Inv 17a). Try a wider/squarer plot, smaller "
                        "rooms, or check the brief for unusual room "
                        "min-width hints."
                    )
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.STUB,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    stub_reason=stub_reason,
                    notes=(
                        f"Underlying: {type(e).__name__}",
                        f"Per-candidate failures: {len(e.failures)} of "
                        f"{e.input_count}",
                        f"Detail: {str(e)[:240]}",
                    ),
                )
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
            from buildemup.components.c10.errors import (
                BatchWetZoneInfeasibleError,
            )
            try:
                wzpc = plan_wet_zones(rsc, floor_brief, grid, plot_analysis)
            except BatchWetZoneInfeasibleError as e:
                # S59 ext: small plots (e.g. mumbai/hyderabad 30×40 +
                # small brief) sometimes can't fit a feasible wet-zone
                # plan — every candidate exhausts wall capacity for
                # bathroom+kitchen clusters. Downgrade to STUB so the
                # pipeline doesn't fail-cascade everything downstream.
                # The user-facing UI surfaces this honestly via the
                # phase's stub_reason. C11a/C11b/C12/C13/C14/C15/C16
                # then SKIP cleanly (their guards already handle the
                # `wet_zoned_candidates is None` case).
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.STUB,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    stub_reason=(
                        "All candidates failed wet-zone planning. "
                        "Common cause: small plots where wall capacity "
                        "can't accommodate bathroom + kitchen riser "
                        "clusters. Suggested remediation: enlarge the "
                        "plot, reduce wet-room count, or split clusters."
                    ),
                    notes=(
                        f"Underlying: {type(e).__name__}",
                        f"Detail: {str(e)[:240]}",
                    ),
                )
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
            refinement_config = None
            if self.config.use_real_c11b_evaluator:
                from buildemup.components.c11b.config import (
                    LocalRefinementConfig,
                )
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
                # S59 ext: generous per-topology budget + larger init
                # retry budget. Two issues observed when use_real_c11b
                # _evaluator=True ran in isolated subset (vs full sweep):
                # (a) 30s default wallclock was sometimes hit → STUB;
                # (b) init_max_retries=100 was sometimes insufficient
                # for the per-topology PRNG to find a feasible seed
                # population (BatchAllTopologiesFailedError with no
                # error attached). Bumping wallclock to 120s and
                # init_max_retries 100→500 makes convergence
                # deterministic across run orders without changing
                # cache-key semantics for default-config callers.
                refinement_config = LocalRefinementConfig(
                    per_topology_wallclock_seconds=120.0,
                    init_max_retries=500,
                )
            else:
                evaluator = StubEvaluator(StubEvaluatorConfig())
                evaluator_kind = "StubEvaluator"
            try:
                if refinement_config is not None:
                    refined = run_local_refinement(
                        mutated, brief_for_c11b, grid, plot_analysis,
                        evaluator, config=refinement_config,
                    )
                else:
                    refined = run_local_refinement(
                        mutated, brief_for_c11b, grid, plot_analysis,
                        evaluator,
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

    def _run_c15_problem_finder(
        self,
        c12_payload: Any,
        c13_payload: Any,
        c14_payload: Any,
    ) -> PhaseResult:
        """C15 phase — problem analysis (S59 follow-up #7).

        Builds (C12, C13, C14) triples via the
        orchestration.adapters.c12_c13_c14_to_c15 module, derives
        per-candidate ProblemAnalysisMetadata, then calls C15's
        `analyze_problems_batch`. Skips when any upstream dependency
        is missing; emits OK with an empty batch when no triples can
        be assembled (e.g. C12 sparse-edge case → 0 C13 successes →
        0 triples).
        """
        phase_id = "c15_problem_finder"
        if c12_payload is None or c13_payload is None or c14_payload is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "Upstream C12 / C13 / C14 did not all produce a "
                    "payload (problem analysis requires the full triple)."
                ),
            )
        start = time.monotonic()
        try:
            from buildemup.components.c15 import (
                ProblemFinderConfig,
                analyze_problems_batch,
            )
            from buildemup.orchestration.adapters import (
                build_c15_inputs_from_upstream,
                derive_cultural_profile,
            )
            cultural_profile = derive_cultural_profile(self.config.vastu_tier)
            triples, metadata = build_c15_inputs_from_upstream(
                c12_payload=c12_payload,
                c13_payload=c13_payload,
                c14_payload=c14_payload,
                cultural_profile=cultural_profile,
            )
            batch = analyze_problems_batch(
                triples=triples,
                metadata_per_candidate=metadata,
                config=ProblemFinderConfig(strict_mode=False),
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=batch,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    f"Triples assembled: {len(triples)}",
                    f"Cultural profile: {cultural_profile.value}",
                    f"Analyses: {len(batch.successful)} OK, "
                    f"{len(batch.failed)} failed",
                    "Empty triples are normal when upstream C12/C13 "
                    "produce sparse edges; phase still ships OK.",
                ),
            )
        except Exception as e:  # noqa: BLE001
            return self._error_result(phase_id, e, start)

    def _run_c16_dual_drawings(
        self,
        c07_payload: Any,
        c10_payload: Any,
        c12_payload: Any,
        c13_payload: Any,
        c14_payload: Any,
        c15_payload: Any,
        plot_analysis: Any,
    ) -> PhaseResult:
        """C16 phase — dual drawings (S59 follow-up #8).

        Assembles UpstreamInputBundle + SelectionResult per surviving
        candidate via the orchestration.adapters.c12_to_c16 module,
        then calls C16's `render_drawings_batch` in WARN mode.

        STUB-degraded path: if the bundle builder finds no candidates
        with the full {C12 + C13 + C14 + per-floor grid + per-floor wet
        zones} cross-section, the phase ships STUB with reason rather
        than failing — the chain runs end-to-end on this fixture but
        renders nothing.
        """
        phase_id = "c16_dual_drawings"
        if c12_payload is None or c13_payload is None:
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.SKIPPED,
                skip_reason=(
                    "Upstream C12 / C13 did not produce a payload "
                    "(drawings require both at minimum)."
                ),
            )
        start = time.monotonic()
        try:
            from buildemup.components.c16 import (
                JurisdictionProfile,
                RenderingConfig,
                render_drawings_batch,
            )
            from buildemup.orchestration.adapters.c12_to_c16 import (
                build_c16_inputs_from_upstream,
            )
            selection_results, bundles = build_c16_inputs_from_upstream(
                c07_payload=c07_payload,
                c10_payload=c10_payload,
                c12_payload=c12_payload,
                c13_payload=c13_payload,
                c14_payload=c14_payload,
                c15_payload=c15_payload,
                plot_analysis=plot_analysis,
            )
            if not selection_results:
                return PhaseResult(
                    phase_id=phase_id,
                    status=PhaseStatus.STUB,
                    payload=None,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    stub_reason=(
                        "No drawable candidates after upstream join: "
                        "every C12 PlacedCandidate either failed C13 "
                        "door placement or C14 circulation analysis. "
                        "(C12 sparse-edge density problem — filed as "
                        "B-C12-EDGE-DENSITY; working as designed.)"
                    ),
                    notes=(
                        "C16 orchestrator was not invoked — no inputs.",
                        "Tracked in 04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md",
                    ),
                )
            jurisdiction = JurisdictionProfile(
                jurisdiction_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
            )
            rendering_config = RenderingConfig()
            batch = render_drawings_batch(
                selection_results=selection_results,
                upstream_inputs_per=bundles,
                jurisdiction_profile=jurisdiction,
                config=rendering_config,
                strict_mode=False,
            )
            return PhaseResult(
                phase_id=phase_id,
                status=PhaseStatus.OK,
                payload=batch,
                elapsed_ms=(time.monotonic() - start) * 1000,
                notes=(
                    f"Bundles assembled: {len(bundles)}",
                    f"Drawings rendered: {len(batch.successes)} OK, "
                    f"{len(batch.failures)} failed",
                    f"Jurisdiction: {jurisdiction.jurisdiction_id}",
                    "Per-candidate failures are normal when upstream "
                    "data is sparse — surfaced via batch.failures.",
                ),
            )
        except Exception as e:  # noqa: BLE001
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
