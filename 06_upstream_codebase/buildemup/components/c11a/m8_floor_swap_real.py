"""
BuildemUp — C11a — M8 real floor-swap implementation (Spec #4 v1.6 § 3.4)
=========================================================================

Per Spec #4 v1.6 LOCKED § 3.4 (B-NEW-T3 enabler #4 of 4). M8 is the only
Tier B operator that operates dwelling-wide. It swaps which floor hosts
the master bedroom.

Algorithm:

1. Read `source` (a MultiFloorWetZonePlannedCandidate).
2. Compute eligible target floors: every floor EXCEPT the current master
   that has bedroom_count >= 1 (per Spec #1 Inv MFDB-4 — the target
   floor must host the master).
3. Choose ONE target via **deterministic cyclic exploration**:
        index = (generation + operator_index) % len(sorted_targets)
   Mathematical guarantee: across N consecutive distinct generations,
   all N eligible targets are visited exactly once.
4. Construct the post-mutation MultiFloorDwellingBrief via Spec #1's
   `with_master_on(new_floor_label)` — re-validates Inv MFDB-4.
5. For each floor whose `has_master_bedroom` flag flipped (exactly two
   floors today; see B-C11A-7 for future cross-floor cascades), re-run
   the C9->C10 cascade against the new per-floor brief.
6. Assemble the new MultiFloorWetZonePlannedCandidate via Spec #3's
   `with_master_on(new_floor_label, new_per_floor_candidates)`. Spec #3's
   `__post_init__` re-validates MFWZP-1 through MFWZP-6.
7. Return MutationApplicationResult with the new wrapper, or a failed
   result with one of:
     - "no_viable_master_target": empty target set.
     - "c9_generation_failed": C9 raised on the new per-floor brief.
     - "c10_validation_failed": C9 succeeded; C10 rejected.
     - "orchestration_state_drift:mfwzpN": wrapper construction failed
       at Spec #3 Inv MFWZP-N (N in 1..6).

Determinism contract (Spec #4 § 3.4.1 tier-table):
  - Tier 1 (structural identity): generation-independent — same source
    content -> same canonical signature.
  - Tier 2 (operator scheduling): generation-dependent but stable for
    fixed generation. Same (source, generation, operator_index) ->
    same M8 target.
  - Tier 3 (evolutionary trajectory): different generations on same
    source intentionally produce different outputs (different target
    floors).

NOTE on cascade architecture: today exactly TWO floors are affected by
M8 (old master + new master). Future cross-floor constraint amendments
(B-C11A-7) may broaden this; the `affected_floor_set(M8, source,
new_master_floor_label=L)` abstraction in orchestrator.py is the
extension point. M8's per-attempt cost remains O(2 floor cascades);
the wrapper rebuild is O(num_floors).

This module exposes the algorithm as standalone callable functions so
they are unit-testable independently of the larger orchestrator wiring.
The existing stub `m8_vert_rearr.py` continues to provide the symbolic
TierBInputMutation form for legacy code paths until the orchestrator's
multi-floor dispatch loop wires this real implementation end-to-end.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from buildemup.components.c11a.schema import (
    MutationApplicationResult,
    MutationLineageDepth,
    MutationOperator,
    TopologyFamilyTransitionPolicy,
)


# =============================================================================
# Target selection
# =============================================================================


def pick_m8_target(
    eligible_targets: tuple[str, ...],
    *,
    generation: int,
    operator_index: int,
) -> str:
    """Cyclic deterministic target selection per Spec #4 v1.6 § 3.4.

    Replaces v1.2's hash-modulo (which lacked coverage guarantee).
    Mathematical property: for N eligible targets and any K consecutive
    distinct generation values, the visited target set has size
    min(K, N). At K = N, all eligible targets are visited exactly once.

    Args:
        eligible_targets: pre-filtered tuple of floor labels eligible
            to become the new master floor (i.e., NOT the current
            master, AND bedroom_count >= 1).
        generation: orchestrator's generation counter.
        operator_index: M8's index in its family's operator list.

    Returns:
        The selected floor label.

    Raises:
        ValueError if eligible_targets is empty (caller should check
        first and produce a "no_viable_master_target" result).
    """
    if not eligible_targets:
        raise ValueError(
            "pick_m8_target: eligible_targets is empty; caller must "
            "check beforehand and emit 'no_viable_master_target'."
        )
    sorted_targets = tuple(sorted(eligible_targets))
    index = (generation + operator_index) % len(sorted_targets)
    return sorted_targets[index]


# =============================================================================
# Eligibility computation
# =============================================================================


def compute_eligible_master_targets(brief: Any) -> tuple[str, ...]:
    """Return the tuple of floor labels eligible to host the master
    bedroom after an M8 swap.

    Per Spec #4 v1.6 § 3.4 step 2: every floor in
    ``brief.floor_labels`` EXCEPT the current master that has
    ``bedroom_count >= 1`` (per Spec #1 Inv MFDB-4).

    Args:
        brief: a MultiFloorDwellingBrief.

    Returns:
        Tuple of eligible floor labels in input tuple order.
    """
    current_master = brief.master_bedroom_floor_label
    eligible: list[str] = []
    for floor in brief.floors:
        if floor.floor_label == current_master:
            continue
        if floor.bedroom_count < 1:
            continue
        eligible.append(floor.floor_label)
    return tuple(eligible)


# =============================================================================
# Full M8 execution — orchestrated cascade with dependency injection
# =============================================================================


def apply_m8_real(
    *,
    source: Any,                                       # MultiFloorWetZonePlannedCandidate
    brief: Any,                                        # MultiFloorDwellingBrief
    generation: int,
    operator_index: int,
    run_c9_per_floor: Callable[[Any, Any], Any],       # (FloorRoomBrief, source_floor_wzpc) -> WZPC
    source_family_id: str,
) -> MutationApplicationResult:
    """Execute M8 end-to-end and produce a MutationApplicationResult.

    Per Spec #4 v1.6 § 3.4. Dependency injection on the C9->C10 cascade
    keeps this function unit-testable: production wires
    ``run_c9_per_floor`` against the real C9+C10 pipeline; tests
    substitute a fake that returns canned WZPCs.

    Args:
        source: the current MultiFloorWetZonePlannedCandidate (Spec #3).
        brief: the MultiFloorDwellingBrief (Spec #1) the source came from.
        generation: orchestrator generation counter (drives cyclic
            target selection).
        operator_index: M8's index in its family's operator list.
        run_c9_per_floor: callable signature
            ``(per_floor_brief: FloorRoomBrief, source_floor_wzpc: WetZonePlannedCandidate) -> WetZonePlannedCandidate``.
            The runner gets BOTH the new per-floor brief AND the
            source floor's WZPC ancestry, so it can pull the
            corresponding corridor-designed candidate from that floor's
            own ancestry chain (fix for self-review issue 3 at S41 close
            — earlier shape used only floors[0]'s CDC for all floors,
            which silently breaks under per-floor heterogeneity).
            Should raise on failure; apply_m8_real catches and routes
            to invalidity reasons.
        source_family_id: the wrapper's source family ID (carried
            through to the result for lineage).

    Returns:
        MutationApplicationResult — valid=True with the new wrapper, or
        valid=False with one of:
          - "no_viable_master_target"
          - "c9_generation_failed"
          - "c10_validation_failed"   (currently subsumed under c9_generation_failed
                                       at this layer; distinguishing requires the
                                       per-floor runner to surface C10 separately)
          - "orchestration_state_drift:mfwzpN" for N in 1..6
    """
    # Step 1-2: eligibility.
    eligible = compute_eligible_master_targets(brief)
    if not eligible:
        return _failed_result(
            invalidity_reason="no_viable_master_target",
            source_family_id=source_family_id,
        )

    # Step 3: cyclic target selection.
    new_master_label = pick_m8_target(
        eligible, generation=generation, operator_index=operator_index,
    )

    # Step 4: post-mutation brief via Spec #1.
    try:
        new_brief = brief.with_master_on(new_master_label)
    except ValueError as e:
        # Should be unreachable if compute_eligible_master_targets is
        # correct; surfaces as orchestration state drift if it isn't.
        return _failed_result(
            invalidity_reason=f"orchestration_state_drift:mfwzp4",
            source_family_id=source_family_id,
            extra_msg=str(e),
        )

    # Step 5: re-run C9->C10 cascade on each floor whose
    # has_master_bedroom flipped. Per Spec #4 § 3.4 today exactly two
    # floors flip: the old master (True -> False) and the new master
    # (False -> True). All other floors carry through unchanged.
    #
    # Critical (fix for self-review issue 3): the per-floor runner now
    # receives BOTH the new per-floor brief AND the source per-floor
    # WZPC so the runner can extract THAT floor's own CDC from its
    # ancestry. Earlier shape used floors[0]'s CDC for every cascade,
    # which silently degrades correctness when floors come from
    # different C8 ancestors (a configuration Spec #3 does not forbid).
    old_master_label = brief.master_bedroom_floor_label
    new_per_floor_candidates: list[Any] = []
    for new_floor_brief, has_master in new_brief.iter_floors_with_master_flag():
        label = new_floor_brief.floor_label
        if label == old_master_label or label == new_master_label:
            # Flipped: re-run cascade against THIS floor's own ancestry.
            import dataclasses

            per_floor_brief = dataclasses.replace(
                new_floor_brief, has_master_bedroom=has_master,
            )
            # Fetch the source per-floor WZPC for ancestry continuity.
            source_floor_wzpc = source.get_floor(label)
            try:
                new_wzpc = run_c9_per_floor(per_floor_brief, source_floor_wzpc)
            except Exception as e:
                # Classify C9 vs C10 failures distinctly (fix for self-
                # review issue 4): the per-floor runner attaches a
                # `.c11a_stage` attribute on exceptions it intercepts
                # to distinguish C9 failures from C10 failures. Bare
                # exceptions default to c9_generation_failed.
                stage = getattr(e, "c11a_stage", "c9")
                reason = (
                    "c10_validation_failed" if stage == "c10"
                    else "c9_generation_failed"
                )
                return _failed_result(
                    invalidity_reason=reason,
                    source_family_id=source_family_id,
                    extra_msg=f"floor={label}: {e}",
                )
            new_per_floor_candidates.append(new_wzpc)
        else:
            # Unchanged floor: reuse existing WZPC via Spec #3's lookup.
            new_per_floor_candidates.append(source.get_floor(label))

    # Step 6: assemble new wrapper. Spec #3's __post_init__ re-validates
    # MFWZP-1 through MFWZP-6; any failure becomes
    # orchestration_state_drift:mfwzpN.
    try:
        new_wrapper = source.with_master_on(
            new_master_label, tuple(new_per_floor_candidates),
        )
    except ValueError as e:
        mfwzp_n = _diagnose_mfwzp_invariant(str(e))
        return _failed_result(
            invalidity_reason=f"orchestration_state_drift:mfwzp{mfwzp_n}",
            source_family_id=source_family_id,
            extra_msg=str(e),
        )
    except TypeError as e:
        # MFWZP-4 (non-WZPC element) routes through TypeError.
        return _failed_result(
            invalidity_reason="orchestration_state_drift:mfwzp4",
            source_family_id=source_family_id,
            extra_msg=str(e),
        )

    # Step 7: success. Carry the constructed wrapper on output_candidate
    # so downstream consumers (orchestrator's MutatedTopologyCandidate
    # decoration, C11b NSGA-II, scoring) can actually USE the mutation.
    # Fix for the Pattern B self-review issue caught at end-of-S41:
    # earlier shape built new_wrapper, validated it, then returned a
    # result that mentioned valid=True but discarded the artifact.
    return MutationApplicationResult(
        operator=MutationOperator.M8_VERT_REARR,
        valid=True,
        invalidity_reason=None,
        topology_variant_id=None,        # set by orchestrator post-processing
        rejection_invariant_id=None,
        source_family_id=source_family_id,
        output_family_id=None,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
        upstream_regeneration_delta=(),
        output_candidate=new_wrapper,
    )


# =============================================================================
# Helpers
# =============================================================================


def _failed_result(
    *,
    invalidity_reason: str,
    source_family_id: str,
    extra_msg: Optional[str] = None,
) -> MutationApplicationResult:
    """Construct a failed MutationApplicationResult with the documented
    invalidity_reason. extra_msg is logged but not currently carried on
    the result (no such field on MutationApplicationResult; filed for
    future telemetry work)."""
    return MutationApplicationResult(
        operator=MutationOperator.M8_VERT_REARR,
        valid=False,
        invalidity_reason=invalidity_reason,
        topology_variant_id=None,
        rejection_invariant_id=None,
        source_family_id=source_family_id,
        output_family_id=None,
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
        upstream_regeneration_delta=(),
    )


def _diagnose_mfwzp_invariant(error_message: str) -> int:
    """Parse an MFWZP ValueError message and return the invariant
    number N (1..6) that fired.

    Per Spec #3 v0.3 LOCKED's error messages:
      - MFWZP-1: "len(floors) >= 2" / "Single-floor outputs should use"
      - MFWZP-2: "per-floor labels must be unique" / "derived"
      - MFWZP-3: "not in derived per-floor labels"
      - MFWZP-4: TypeError "must be WetZonePlannedCandidate" (handled
        separately in caller via except TypeError clause)
      - MFWZP-5: "expected exactly one"
      - MFWZP-6: "master bedroom found on floor"

    Returns 5 (most likely cascade drift) if no match — conservative
    classification, the message + reason combo gives operators
    enough signal even on the fallback.
    """
    m = error_message.lower()
    if "expected exactly one" in m:
        return 5
    if "master bedroom found on floor" in m:
        return 6
    if "not in derived per-floor labels" in m:
        return 3
    if "per-floor labels must be unique" in m or "must be unique" in m:
        return 2
    if "len(floors) >= 2" in m or "single-floor outputs" in m:
        return 1
    # Fallback: most likely the master-cascade drift case.
    return 5


__all__ = [
    "pick_m8_target",
    "compute_eligible_master_targets",
    "apply_m8_real",
]
