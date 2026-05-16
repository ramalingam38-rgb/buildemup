"""
BuildemUp — C11a — Multi-floor C9->C10 adapter for M8 (Spec #4 v1.6 § 3.4)
==========================================================================

Per Spec #4 v1.6 LOCKED § 3.4 step 5: M8's cascade re-runs C9 (room
sizing) + C10 (wet-zone planning) for each floor whose
`has_master_bedroom` flag flipped. This module provides a factory
producing the per-floor runner that `apply_m8_real` takes as a
dependency.

Separation of concerns: `m8_floor_swap_real.apply_m8_real` is the
algorithmic core (cyclic target selection, eligibility, wrapper
assembly, invariant routing) and accepts the runner as injected
behaviour. This adapter wires the algorithmic core to the real
upstream pipeline (C7's grid, C4's plot_analysis, C9 + C10 entry
points). Tests substitute their own runner; production wires this one.

Per-attempt cost (Spec #4 § 3.3 + § 3.4): one regenerative cascade
per affected floor. M8 affects exactly two floors today (old master +
new master); future cross-floor cascades (B-C11A-7) will broaden the
affected set via `affected_floor_set`.

This module is intentionally thin — its only job is to construct a
callable that takes a per-floor `FloorRoomBrief` and returns a
`WetZonePlannedCandidate`. All routing decisions live in
`apply_m8_real`; this adapter just executes the underlying C9+C10
pipeline.
"""
from __future__ import annotations

from typing import Any, Callable

from buildemup.components.c09 import size_rooms
from buildemup.components.c09.schema import RoomSizedCandidate
from buildemup.components.c10 import plan_wet_zones
from buildemup.components.c10.schema import WetZonePlannedCandidate
from buildemup.domain.floor_brief import FloorRoomBrief


# =============================================================================
# Adapter factory
# =============================================================================


def make_per_floor_c9_runner(
    *,
    grid: Any,
    plot_analysis: Any,
) -> Callable[[FloorRoomBrief, Any], WetZonePlannedCandidate]:
    """Build a per-floor C9 + C10 runner for M8's cascade.

    Per Spec #4 v1.6 § 3.4 step 5: returns a callable
    ``(per_floor_brief, source_floor_wzpc) -> WetZonePlannedCandidate``
    that runs C9 + C10 against the per-floor brief, using the source
    floor WZPC's OWN ancestry to retrieve the right corridor-designed
    candidate (CDC) for that floor.

    Self-review fix at S41 close: earlier shape took
    ``corridor_designed_candidates`` as factory configuration, baked
    from ``source.floors[0]`` at dispatch time. That assumed all floors
    share a single C8 ancestor — which is true for fixture-built
    wrappers but is NOT a Spec #3 invariant. Future heterogeneous
    multi-floor wrappers (e.g., floors that came from different C8
    runs) would silently use the wrong CDC. The new shape pulls CDC
    from each floor's own ancestry.

    Args:
        grid: C7 Grid carrying envelope dimensions (shared across floors
            in v1; per-floor grid is B-MFDB-C future work).
        plot_analysis: C4 PlotAnalysis providing plot_facing (shared
            across floors).

    Returns:
        Callable ``(per_floor_brief, source_floor_wzpc) -> WZPC``. The
        runner exposes c9/c10 failure distinction via the `.c11a_stage`
        attribute on raised exceptions ("c9" or "c10"); callers use
        this to populate ``invalidity_reason`` correctly.

    Raises (when called):
        C9 exceptions surface with `.c11a_stage="c9"` attached;
        C10 exceptions surface with `.c11a_stage="c10"` attached.
        `apply_m8_real` catches both and routes appropriately.
    """

    def runner(
        per_floor_brief: FloorRoomBrief,
        source_floor_wzpc: Any,
    ) -> WetZonePlannedCandidate:
        """Run C9 then C10 for the given per-floor brief, using THIS
        floor's own ancestry CDC.

        The brief's `has_master_bedroom` flag drives C9's master
        designation per Spec #2 v0.12 LOCKED (materializer + validator
        both gate on this flag).
        """
        # Extract THIS floor's CDC from its own ancestry chain. Every
        # WZPC has wzpc.room_sized_candidate.corridor_designed_candidate
        # enforced by C9's __post_init__.
        try:
            cdc = (
                source_floor_wzpc.room_sized_candidate
                .corridor_designed_candidate
            )
        except AttributeError as e:
            err = RuntimeError(
                f"make_per_floor_c9_runner: source floor WZPC ancestry "
                f"broken; cannot extract CDC: {e}"
            )
            err.c11a_stage = "c9"
            raise err from e

        # C9: room sizing against the per-floor brief and the floor's
        # own CDC.
        try:
            rsc_tuple = size_rooms(
                (cdc,),
                per_floor_brief,
                grid,
                plot_analysis,
            )
        except Exception as e:
            # Mark stage explicitly so the caller can classify.
            if not hasattr(e, "c11a_stage"):
                e.c11a_stage = "c9"
            raise

        if not rsc_tuple:
            err = RuntimeError(
                "make_per_floor_c9_runner: C9 produced no "
                "RoomSizedCandidate output."
            )
            err.c11a_stage = "c9"
            raise err

        # C10: wet-zone planning against the C9 output.
        try:
            wzpc_tuple = plan_wet_zones(
                rsc_tuple,
                per_floor_brief,
                grid,
                plot_analysis,
            )
        except Exception as e:
            if not hasattr(e, "c11a_stage"):
                e.c11a_stage = "c10"
            raise

        if not wzpc_tuple:
            err = RuntimeError(
                "make_per_floor_c9_runner: C10 produced no "
                "WetZonePlannedCandidate output."
            )
            err.c11a_stage = "c10"
            raise err

        # Return the first WZPC — M8's cascade requires one candidate
        # per affected floor. Multi-candidate fan-out at this layer
        # is unsupported in v1 (filed as future work; B-NEW-T3 ships
        # single-cascade-per-floor).
        return wzpc_tuple[0]

    return runner


__all__ = ["make_per_floor_c9_runner"]
