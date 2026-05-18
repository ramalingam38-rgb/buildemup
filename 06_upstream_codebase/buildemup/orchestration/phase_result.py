"""PhaseResult — per-phase result captured by MasterOrchestrator.

A pipeline phase produces a PhaseResult regardless of whether the phase
succeeded, failed, was skipped, or shipped as a stub. The orchestrator
captures the outcome of every phase even when a downstream phase fails,
so partial upstream output is preserved for inspection by the architect
review (B-238) and the v1+ roadmap authoring (Option C).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, Tuple


class PhaseStatus(str, Enum):
    """Outcome status for a single pipeline phase."""

    OK = "ok"
    """Phase ran successfully; `payload` carries the real output."""

    ERROR = "error"
    """Phase raised an exception or returned a typestate failure
    (e.g., FailedDoorPlacement). `payload` carries the error details;
    `error_class` and `error_message` carry the exception summary."""

    SKIPPED = "skipped"
    """Phase was intentionally skipped (e.g., MVP-scope deferral).
    `payload` is None; `skip_reason` carries the rationale."""

    STUB = "stub"
    """Phase ran with simplified / partial input adapters; output is
    representative but not production-quality. The follow-ups doc
    tracks what's needed to upgrade STUB → OK."""


@dataclass(frozen=True)
class PhaseResult:
    """Structured result from a single pipeline phase.

    Always populated even on failure — never raises out of the
    orchestrator's per-phase try/except.
    """
    phase_id: str
    """Canonical phase identifier — one of PIPELINE_PHASES."""

    status: PhaseStatus
    """How the phase concluded."""

    payload: Any = None
    """The phase's actual output (dataclass instance, tuple of candidates,
    error details, etc.). May be None for SKIPPED or ERROR phases."""

    error_class: str = ""
    """For ERROR status: the exception class name (e.g., 'ValueError')."""

    error_message: str = ""
    """For ERROR status: the exception message (.args[0] or repr)."""

    skip_reason: str = ""
    """For SKIPPED status: why the phase was skipped."""

    stub_reason: str = ""
    """For STUB status: why the phase used simplified adapters."""

    elapsed_ms: float = 0.0
    """Wallclock time spent in this phase (milliseconds)."""

    notes: Tuple[str, ...] = field(default_factory=tuple)
    """Free-form notes (e.g., 'used StubEvaluator', 'C11a config: M0 only')."""


# ─────────────────────────────────────────────────────────────────────
# Canonical pipeline phase ordering
# ─────────────────────────────────────────────────────────────────────

PIPELINE_PHASES: Final[Tuple[str, ...]] = (
    "c01_brief",
    "c02_feasibility",
    # C3a extreme-case detection ships as an ASYNC-FLAGS phase
    # (S59 follow-up #10): runs detection only, never halts, surfaces
    # detected cases as flags. The full negotiation flow (C3b) stays
    # at /api/extreme-case/* — session-stateful and outside the
    # orchestrator's pure-function contract.
    "c03a_extreme_case_detection",
    "c04_plot_analysis",
    "c05_topology",
    "c06_orientation",
    "c07_structural_grid",
    "c08_corridor",
    "c09_room_sizer",
    "c10_wet_zones",
    "c11a_topology_mutation",
    "c11b_nsga_refinement",
    "c12_vertical_placement",
    "c13_doors",
    "c14_connection_graph",
    "c15_problem_finder",
    "c16_dual_drawings",
    "c17_quote_comparison",
)
