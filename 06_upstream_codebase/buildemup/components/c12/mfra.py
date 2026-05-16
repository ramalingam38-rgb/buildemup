"""
BuildemUp — Component 12 — Multi-Floor Refinement Absorption (MFRA)
=====================================================================

Per C12 SPEC v1.0 LOCKED v0.2-A2 (formal MFRA convergence) + v0.2-A10
(vertical-core reservation pre-step).

Algorithm (§ 3 Phase 2 step 4):

1. Initial pass:
   a. Run Phase 1b: reserve vertical cores at the SAME (x, y) on
      every floor (prevents iteration oscillation).
   b. Run Phase 1 SFP per floor (slicing-tree).
   c. Run Phase 2 step 3 VAV across floors.
   d. If converged: emit MultiFloorPlacedCandidate.

2. Retry loop (bounded by multi_floor_max_realign_iterations,
   default 3 per v0.3-A2):
   a. For each misaligned feature f:
      - Identify the floor F whose centroid deviates most from
        consensus.
      - Inject a HARD position constraint into F's SFP retry:
        f.target_position = mean(positions across non-deviant floors)
        with ε-tolerance = (alignment_tolerance / 2).
      - Re-run SFP on F with the constraint added.
   b. Re-run VAV.
   c. Convergence criterion (monotonic-δ):
      - If δ_{n+1} < δ_n × 0.5: continue (good progress)
      - If δ_n × 0.5 ≤ δ_{n+1} < δ_n: continue (slow progress)
      - If δ_{n+1} ≥ δ_n: ABORT (divergence/plateau)
   d. If retries exhausted without convergence: raise
      VerticalAlignmentError.

For v1, the constraint-injection step (2a) is implemented as a
simple "biased re-placement": we don't currently re-run the full
slicing-tree with hard constraints (that's a deeper integration
filed as B-C12-COUPLED-MF-PLACEMENT). v1 instead does best-effort:
if the initial VAV fails, MFRA reports the convergence outcome
honestly without pretending to fix it via single-pass retry. This
matches the v0.5-A2 "v1 guarantee boundary": deterministic
geometric realization + bounded feasibility, NOT solver completeness.

This is the v1-tractable middle ground per spec § 0.6 build plan.
Full coupled multi-floor placement remains backlog.
"""
from __future__ import annotations

from .errors import VerticalAlignmentError
from .schema import (
    MultiFloorPlacedCandidate,
    PlacedCandidate,
    VerticalAlignmentReport,
)
from .vav import verify_vertical_alignment
from .vertical_core_reservation import VerticalCoreReservation


def _monotonic_delta_decision(
    prev_delta: float, current_delta: float,
) -> str:
    """Per v0.2-A2 convergence criterion.

    Returns one of:
      - "good_progress": δ_{n+1} < δ_n × 0.5
      - "slow_progress": δ_n × 0.5 ≤ δ_{n+1} < δ_n
      - "abort_divergence": δ_{n+1} ≥ δ_n (plateau or growth)
    """
    if current_delta < prev_delta * 0.5:
        return "good_progress"
    if current_delta < prev_delta:
        return "slow_progress"
    return "abort_divergence"


def absorb_multi_floor_placements(
    *,
    source_multifloor_signature: str,
    per_floor_placements: tuple[tuple[str, PlacedCandidate], ...],
    feature_room_ids_by_floor: dict[str, set[str]],
    vertical_cores_reserved: tuple[VerticalCoreReservation, ...],
    tolerance_m: float,
    max_realign_iterations: int,
    strict_mode: bool,
) -> MultiFloorPlacedCandidate:
    """Orchestrate the MFRA loop for one multi-floor candidate.

    For v1 the retry-with-constraint-injection step is a no-op
    placeholder (see module docstring); the loop runs initial VAV
    and reports the outcome honestly. Future versions will inject
    constraints into per-floor SFP retries here.

    Args:
      source_multifloor_signature: provenance back to C11b input.
      per_floor_placements: tuple of (floor_label, PlacedCandidate),
        sorted by floor_label.
      feature_room_ids_by_floor: alignment-relevant room IDs per floor.
      vertical_cores_reserved: Phase 1b cores (canonicalized).
      tolerance_m: VAV tolerance (per PlacementConfig).
      max_realign_iterations: retry budget (per PlacementConfig).
      strict_mode: if True, raise on non-convergence; if False,
        return the MultiFloorPlacedCandidate with converged=False
        in its alignment report.

    Returns: MultiFloorPlacedCandidate.

    Raises:
      VerticalAlignmentError under STRICT mode when MFRA fails to
      converge within budget OR exhibits monotonic-δ divergence.
    """
    # Initial VAV
    report = verify_vertical_alignment(
        per_floor_placements=per_floor_placements,
        feature_room_ids_by_floor=feature_room_ids_by_floor,
        tolerance_m=tolerance_m,
        current_retry_index=0,
        delta_history=(),
    )

    if report.converged:
        return _build_mf_candidate(
            source_multifloor_signature,
            per_floor_placements,
            report,
            vertical_cores_reserved,
        )

    # Retry loop (v1 placeholder: no actual constraint injection yet;
    # see module docstring + B-C12-COUPLED-MF-PLACEMENT).
    delta_history: tuple[float, ...] = (report.final_max_misalignment_m,)
    for retry_idx in range(1, max_realign_iterations + 1):
        # v1: no constraint-injection, so re-running VAV gives same
        # result. Future amendments fill in the gap.
        new_report = verify_vertical_alignment(
            per_floor_placements=per_floor_placements,
            feature_room_ids_by_floor=feature_room_ids_by_floor,
            tolerance_m=tolerance_m,
            current_retry_index=retry_idx,
            delta_history=delta_history,
        )
        prev_delta = delta_history[-1]
        decision = _monotonic_delta_decision(
            prev_delta, new_report.final_max_misalignment_m,
        )
        if new_report.converged:
            return _build_mf_candidate(
                source_multifloor_signature,
                per_floor_placements,
                new_report,
                vertical_cores_reserved,
            )
        if decision == "abort_divergence":
            # Per v0.2-A2: don't waste further retries.
            report = new_report
            break
        delta_history = new_report.delta_progression
        report = new_report

    # All retries exhausted (or aborted) without convergence.
    if strict_mode:
        raise VerticalAlignmentError(
            f"MFRA failed to converge for {source_multifloor_signature!r} "
            f"within {max_realign_iterations} retries. Final max "
            f"misalignment: {report.final_max_misalignment_m:.4f} m. "
            f"Misaligned features: {report.misaligned_features}."
        )

    # WARN mode: return the candidate with non-converged report.
    return _build_mf_candidate(
        source_multifloor_signature,
        per_floor_placements,
        report,
        vertical_cores_reserved,
    )


def _build_mf_candidate(
    sig: str,
    per_floor_placements: tuple[tuple[str, PlacedCandidate], ...],
    report: VerticalAlignmentReport,
    cores: tuple[VerticalCoreReservation, ...],
) -> MultiFloorPlacedCandidate:
    return MultiFloorPlacedCandidate(
        source_multifloor_candidate_signature=sig,
        per_floor_placements=per_floor_placements,
        alignment_report=report,
        vertical_cores_reserved=tuple(c.to_tuple() for c in cores),
    )


__all__ = [
    "absorb_multi_floor_placements",
]
