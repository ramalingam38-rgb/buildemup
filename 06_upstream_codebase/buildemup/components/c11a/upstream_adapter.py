"""
BuildemUp — Component 11a — real UpstreamRegenerator adapter (Sub-session 4)
==============================================================================

Per spec § 3.5: Tier B operators drive ``DeepMutationPipeline`` which
calls a UpstreamRegenerator implementation. Sub-3 ships the protocol +
``StubUpstreamRegenerator`` for unit tests; this module ships the
**real adapter** wired against C7.GridGenerator + C9.size_rooms +
C10.plan_wet_zones.

== Sub-4 scope decision (filed as B-NEW-T) ==

Each Tier B operator (M6/M7a/M7b/M8) needs operator-specific
**upstream-input-rebuild** logic to translate its ``TierBInputMutation``
into concrete ``Brief / Grid / RoomSizingConfig / WetZoneConfig`` deltas
the upstream functions accept. That logic is non-trivial and operator-
specific:

  * M6 (wet-wall rotate): synthesize new ``WetWallRotationHint`` config
    parameter or rebuild the C10 input with the rotated assignment.
  * M7a/b (grid scale): construct a new Grid via C7.GridGenerator with
    the target bay size, then re-run C8 corridor design + C9 sizing +
    C10 wet-zone plan against it.
  * M8 (master-floor swap): rebuild the multi-floor brief with the
    swapped master floor, then re-run C9 + C10.

Per Pattern E (scope creep mid-build), Sub-4 ships:

  1. The adapter scaffold (``RealUpstreamRegenerator`` class shape)
  2. Per-operator method stubs that raise ``NotImplementedError``
     with operator-specific implementation hints
  3. A working ``compute_delta()`` over the candidate's ancestry hash

The unimplemented operator-specific upstream calls are filed as
**B-NEW-T** (Sub-4 backlog item). The orchestrator's Tier A path is
fully wired and end-to-end testable; Tier B requires opting in via
``upstream_regenerator=...`` on ``mutate_topologies()`` until B-NEW-T
lands.

This is the honest scope: Sub-4 ships the orchestrator, the Phase 0
validators, replay determinism, the integration smoke test for Tier A.
Tier-B-on-real-upstream is one carefully-scoped follow-up session.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c11a.deep_pipeline import (
    TierBInputMutation,
    UpstreamRegenerator,
)
from buildemup.components.c11a.errors import DeepMutationApplicationError
from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.schema import DeltaKey, MutationOperator


# =============================================================================
# RealUpstreamRegenerator
# =============================================================================


class RealUpstreamRegenerator:
    """Production ``UpstreamRegenerator`` wired against C7/C9/C10.

    Per Sub-4 scope decision: the Tier B real-upstream wiring is
    deferred to B-NEW-T. This class provides:

      * The ``UpstreamRegenerator`` Protocol shape (so the orchestrator
        can hold one and pass it to ``DeepMutationPipeline``).
      * A working ``compute_delta()`` against an ancestry-hash signal
        (Sub-4 simplification — Sub-5 / B-NEW-T expands to true
        per-DeltaKey diffing on fully-regenerated candidates).
      * ``regenerate()`` that raises ``NotImplementedError`` per
        operator with concrete implementation hints.

    For test purposes (and for callers that need only Tier A behaviour
    out of ``mutate_topologies()``), the orchestrator can be invoked
    without a Tier B regenerator at all — the orchestrator's
    ``enabled_operators`` filter excludes Tier B if no regenerator is
    configured.
    """

    def __init__(
        self,
        *,
        floor_room_brief: Any = None,
        grid: Any = None,
        plot_analysis: Any = None,
    ) -> None:
        """Sub-4 holds upstream context for B-NEW-T wiring.

        Args:
            floor_room_brief: from ``mutate_topologies()`` parameter
            grid: from ``mutate_topologies()`` parameter
            plot_analysis: from ``mutate_topologies()`` parameter
        """
        self._floor_room_brief = floor_room_brief
        self._grid = grid
        self._plot_analysis = plot_analysis

    # -------------------------------------------------------------------------
    # UpstreamRegenerator protocol — regenerate
    # -------------------------------------------------------------------------

    def regenerate(
        self,
        source: Any,
        mutation: TierBInputMutation,
        operator: MutationOperator,
    ) -> Any:
        """Re-run upstream with the operator's input mutation applied.

        At Sub-4: ``NotImplementedError`` for M7/M8 (B-NEW-T2/T3 deferred).
        At Sub-5: M6 wired via the post-process rotation vertical slice
        (B-NEW-T1).
        """
        if operator == MutationOperator.M6_WET_ROTATE:
            # B-NEW-T1: M6 vertical slice via post-process rotation.
            # Imports lazily to avoid c10 dependency at module load.
            from buildemup.components.c10.schema import WetZonePlannedCandidate
            from buildemup.components.c11a.m6_wet_rotate_real import (
                M6NotViableError,
                rotate_wet_zone_planned_candidate,
            )
            if not isinstance(source, WetZonePlannedCandidate):
                # Fall through to NotImplementedError — Sub-4
                # synthetic-source path. Real candidates only.
                raise NotImplementedError(
                    "RealUpstreamRegenerator.regenerate(M6_WET_ROTATE): "
                    "B-NEW-T1 requires a real WetZonePlannedCandidate "
                    f"source; got {type(source).__name__}. Tests with "
                    "synthetic sources should inject a "
                    "StubUpstreamRegenerator."
                )
            try:
                return rotate_wet_zone_planned_candidate(source, self._grid)
            except M6NotViableError:
                # Re-raise — pipeline catches per_candidate severity
                # and surfaces as invalid result.
                raise

        if operator in (
            MutationOperator.M7A_GRID_3_3,
            MutationOperator.M7B_GRID_2_7,
        ):
            raise NotImplementedError(
                f"RealUpstreamRegenerator.regenerate({operator.value}): "
                f"Sub-4 scope deferred to B-NEW-T2. Implementation: "
                f"call C7.GridGenerator().generate(envelope, "
                f"target_bay_x=mutation.new_grid_bay_x_m, "
                f"target_bay_y=mutation.new_grid_bay_y_m); cascade "
                f"through C8 / C9 / C10."
            )
        if operator == MutationOperator.M8_VERT_REARR:
            raise NotImplementedError(
                "RealUpstreamRegenerator.regenerate(M8_VERT_REARR): "
                "Sub-4 scope deferred to B-NEW-T3. Implementation: "
                "rebuild floor_room_brief with master-floor swapped; "
                "re-run C9.size_rooms + C10.plan_wet_zones per floor."
            )

        # Tier A operator passed to a Tier B regenerator — programming bug.
        raise DeepMutationApplicationError(
            f"RealUpstreamRegenerator.regenerate(): operator "
            f"{operator.value} is not REGENERATIVE-tier. The "
            f"DeepMutationPipeline guards against this; this message "
            f"indicates the guard was bypassed."
        )

    # -------------------------------------------------------------------------
    # UpstreamRegenerator protocol — compute_delta
    # -------------------------------------------------------------------------

    def compute_delta(
        self,
        source: Any,
        regenerated: Any,
        operator: MutationOperator,
    ) -> tuple[DeltaKey, ...]:
        """Compute the DeltaKey tuple between source and regenerated.

        Per B-NEW-T1: real per-DeltaKey diff for M6 (compares
        wet_wall_assignment + riser_groups + trap_arm_distances).
        Other operators fall back to the conservative-default
        (return operator's expected_delta keys).

        B-NEW-T2/T3 expand to grid + multi-floor diffs.
        """
        if operator == MutationOperator.M6_WET_ROTATE:
            return _diff_m6_wet_rotate(source, regenerated)

        # Conservative default for unwired operators.
        metadata = OPERATOR_METADATA[operator]
        return tuple(
            sorted(
                metadata.expected_delta_schema.expected,
                key=lambda k: k.value,
            )
        )


# =============================================================================
# Protocol assertion
# =============================================================================
#
# Confirms RealUpstreamRegenerator satisfies the UpstreamRegenerator
# Protocol structurally. This is a self-check; runtime_checkable on
# UpstreamRegenerator means isinstance() works, so Sub-4's tests verify
# this directly.

assert hasattr(RealUpstreamRegenerator, "regenerate")
assert hasattr(RealUpstreamRegenerator, "compute_delta")


# =============================================================================
# M6 wet-rotate diff helper (B-NEW-T1)
# =============================================================================


def _diff_m6_wet_rotate(source: Any, regenerated: Any) -> tuple[DeltaKey, ...]:
    """Real per-DeltaKey diff for M6 wet-rotate.

    Compares ``WetZonePlannedCandidate.wet_zone_plan`` fields between
    source and regenerated. Returns the delta keys per § 2.5 v0.5
    DeltaKey vocabulary:

      * PLUMB_WET_WALL_ASSIGNMENT — wet_wall_assignment dict differs
      * PLUMB_RISER_GROUPS — riser_groups tuple differs (after rotation,
        cluster→wall mapping changes; group_ids change)
      * PLUMB_TRAP_ARM_DISTANCES — trap_arm_distances dict differs
        (recomputed under new wall positions)

    Returns sorted by DeltaKey.value for replay determinism.
    """
    delta_keys: set[DeltaKey] = set()

    src_plan = getattr(source, "wet_zone_plan", None)
    regen_plan = getattr(regenerated, "wet_zone_plan", None)
    if src_plan is None or regen_plan is None:
        # Defensive — without plans we can't diff, return empty.
        return ()

    if src_plan.wet_wall_assignment != regen_plan.wet_wall_assignment:
        delta_keys.add(DeltaKey.PLUMB_WET_WALL_ASSIGNMENT)

    if src_plan.riser_groups != regen_plan.riser_groups:
        delta_keys.add(DeltaKey.PLUMB_RISER_GROUPS)

    if src_plan.trap_arm_distances != regen_plan.trap_arm_distances:
        delta_keys.add(DeltaKey.PLUMB_TRAP_ARM_DISTANCES)

    return tuple(sorted(delta_keys, key=lambda k: k.value))


__all__ = ["RealUpstreamRegenerator"]
