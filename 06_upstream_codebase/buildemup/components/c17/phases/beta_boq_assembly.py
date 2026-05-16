"""
C17 — Phase β — BOQ assembly
==============================

Input:  C7 cost_lines + RateProvider + project metadata
Output: ProjectBOQ

Phase β does the C7/C16/RateProvider → ProjectBOQ conversion. The
heavy lifting is in upstream_adapter.py; this module is the orchestrator
seam that wraps it with phase-β-specific provenance and per-line
WARN-mode tolerance.

Per spec § 3: phase β runs AFTER phase α (so we know the quote's
decomposition style) but BEFORE phase γ matching. Why after α?
Because if the decomposition is 'turnkey_bundles', phase β can
collapse some BOQ items into bundle aggregates for coarser matching.

v1.0 doesn't yet implement bundle-collapse in phase β — it produces
a full line-item BOQ regardless of decomposition style, and phase γ
adapts at match time. Bundle-collapse is documented as a future
optimisation (B-C17-BUNDLE-AWARE-BOQ-ASSEMBLY).

Rule 11 self-analysis:
  1. The upstream_adapter does the actual work. This file is a thin
     orchestrator wrapper — easy to mistake as fluff, but the seam
     exists because (a) phase β may evolve to do bundle-collapse,
     (b) STRICT vs WARN routing happens here, not in the adapter.
  2. WARN mode: BOQAssemblyError on a single cost_line skips that
     line and continues. The BOQ ends up missing that item; phase γ
     will see no candidate; phase δ skips; phase ζ surfaces it as
     an advisory_flag. End-to-end recoverable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from buildemup.components.c17.config import C17RuntimeConfig
from buildemup.components.c17.contracts import ProjectBOQ, ProjectBOQItem
from buildemup.components.c17.errors import BOQAssemblyError
from buildemup.components.c17.phases.alpha_canonicalize import PhaseAlphaOutput
from buildemup.components.c17.schema import FailedComparisonRecord
from buildemup.components.c17.upstream_adapter import build_project_boq
from buildemup.utils.rate_provider import RateProvider


@dataclass(frozen=True)
class PhaseBetaOutput:
    """Bundled output of phase β."""
    project_boq:       ProjectBOQ
    failures:          Tuple[FailedComparisonRecord, ...]


def run_phase_beta(
    alpha_output: PhaseAlphaOutput,
    *,
    project_id:                str,
    jurisdiction_profile_id:   str,
    declared_domain_scope:     str,
    cost_lines:                Iterable,
    rate_provider:             RateProvider,
    locality_label:            str,
    config:                    C17RuntimeConfig,
) -> PhaseBetaOutput:
    """Phase β entry point.

    `alpha_output` is accepted for forward-compat (future bundle-aware
    BOQ assembly). v1.0 doesn't consume it but the seam exists."""
    # In STRICT mode: any BOQAssemblyError halts the whole report.
    # In WARN mode: collect into failures, continue with reduced BOQ.

    if config.strict_mode == "strict":
        # Easy path — adapter raises on any failure.
        boq = build_project_boq(
            project_id=project_id,
            jurisdiction_profile_id=jurisdiction_profile_id,
            declared_domain_scope=declared_domain_scope,
            cost_lines=cost_lines,
            rate_provider=rate_provider,
            locality_label=locality_label,
        )
        return PhaseBetaOutput(project_boq=boq, failures=())

    # WARN mode — filter offending lines, collect failures.
    surviving_lines: List = []
    failures: List[FailedComparisonRecord] = []
    for line in cost_lines:
        try:
            # Probe by calling adapter with a single-line iterable.
            # This is wasteful in the worst case; if it becomes a
            # bottleneck we drop in a more efficient per-line API.
            build_project_boq(
                project_id="__probe__",
                jurisdiction_profile_id=jurisdiction_profile_id,
                declared_domain_scope=declared_domain_scope,
                cost_lines=[line],
                rate_provider=rate_provider,
                locality_label=locality_label,
            )
            surviving_lines.append(line)
        except BOQAssemblyError as exc:
            failures.append(FailedComparisonRecord(
                line_id=exc.boq_id,
                failure_phase="beta",
                error_class="BOQAssemblyError",
                error_message=str(exc),
                error_metadata=f"reason={exc.reason!r}",
            ))

    boq = build_project_boq(
        project_id=project_id,
        jurisdiction_profile_id=jurisdiction_profile_id,
        declared_domain_scope=declared_domain_scope,
        cost_lines=surviving_lines,
        rate_provider=rate_provider,
        locality_label=locality_label,
    )

    return PhaseBetaOutput(
        project_boq=boq,
        failures=tuple(failures),
    )
