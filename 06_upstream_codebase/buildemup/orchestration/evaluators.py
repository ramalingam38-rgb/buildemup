"""Real C11b EvaluatorProtocol implementations (S57 follow-up #3).

C11b's NSGA-II refinement needs an `EvaluatorProtocol` — anything with
`evaluate(candidate) -> ObjectiveVector` + `signature() -> str`.

The shipped `StubEvaluator` (in C11b's evaluator.py) returns three
synthetic objectives derived purely from a candidate's room
dimensions. The orchestrator's MVP uses it and converts
`BatchAllTopologiesFailedError` to STUB status because the stub's
objective surface plus the orchestrator's default NSGA config doesn't
satisfy convergence on the smoke fixture.

This module ships the **real** evaluator: ``MultiObjectiveEvaluator``.
Its objectives use upstream context (target areas + minimum widths
from C9 sizing, envelope area from C4) plus the candidate's refined
dimensions to compute objectives that NSGA-II can climb:

  1. ``area_undersizing`` — sum of max(0, target_m2 - actual_m2)²
     across rooms. Smooth, zero when every room hits its C9 target,
     grows quadratically with undersizing.
  2. ``aspect_penalty`` — sum of (aspect_ratio - 1)² across rooms,
     where aspect_ratio = max(w,d) / min(w,d). Smooth, zero for
     perfect squares, grows for elongated rooms.
  3. ``envelope_waste`` — (envelope_area - total_room_area) when
     positive, else 0. Penalizes layouts that under-use the plot.
     Smooth (clamped at zero on the over-use side; that's a different
     failure mode, handled by C12 not C11b).

All three are "lower is better" per NSGA-II convention. They are
co-correlated by construction (just like StubEvaluator's three) so the
3-objective NSGA regime stays inside its proven mathematical zone
(per § 0.5 D-NSGA-1 in the C11b spec).

Pulling the upstream context the evaluator needs is the
``build_real_evaluator_from_upstream`` helper. It walks the C11a
output, extracts the C9 RoomSizeRequirement set (target_m2 +
liveability_min_width_m + category), and bundles that with the C4
PlotAnalysis envelope. The result is a constructed evaluator the
orchestrator can pass straight to ``run_local_refinement``.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from buildemup.components.c11b.evaluator import EvaluatorProtocol
from buildemup.components.c11b.schema import (
    ObjectiveVector,
    RefinedCandidate,
)


# ─────────────────────────────────────────────────────────────────────
# Public dataclass — per-room upstream context for the evaluator
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RoomEvaluationContext:
    """Per-room data the evaluator needs that RefinedCandidate doesn't
    itself carry (C11b refines dimensions only — categories + target
    areas live upstream).
    """
    room_id: str
    target_area_m2: float
    min_width_m: float


# ─────────────────────────────────────────────────────────────────────
# Real evaluator
# ─────────────────────────────────────────────────────────────────────


class MultiObjectiveEvaluator:
    """Real C11b EvaluatorProtocol implementation (S57 #3).

    Stores upstream context at construction time so `evaluate()` can
    compute objectives without re-walking the C9 / C4 chain on each
    call.

    Conforms to `buildemup.components.c11b.evaluator.EvaluatorProtocol`
    structurally; `isinstance(evaluator, EvaluatorProtocol)` returns
    True via the @runtime_checkable Protocol on EvaluatorProtocol.
    """

    def __init__(
        self,
        *,
        room_contexts_by_id: Mapping[str, RoomEvaluationContext],
        envelope_area_m2: float,
    ) -> None:
        if envelope_area_m2 <= 0.0:
            raise ValueError(
                f"envelope_area_m2 must be positive; got "
                f"{envelope_area_m2}."
            )
        # Freeze inputs (dict copy + tuple of items) for purity.
        self._contexts = dict(room_contexts_by_id)
        self._envelope_area_m2 = float(envelope_area_m2)
        # Precompute signature so it's stable across calls.
        self._sig = self._compute_signature()

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        dims = candidate.refined_parameters.room_dimensions
        if not dims:
            # Degenerate; return all-zero objectives with no
            # constraint violations. NSGA never sees this in practice.
            return ObjectiveVector(
                values=(
                    ("area_undersizing", 0.0),
                    ("aspect_penalty", 0.0),
                    ("envelope_waste", 0.0),
                ),
                constraint_violations=0.0,
            )

        undersizing = 0.0
        aspect_penalty = 0.0
        total_area = 0.0

        for rd in dims:
            w, d = rd.width_m, rd.depth_m
            area = w * d
            total_area += area

            ctx = self._contexts.get(rd.room_id)
            if ctx is not None:
                # Quadratic penalty on undersizing only (oversize is
                # fine for C11b's optimization surface — C12 handles
                # envelope fit).
                deficit = ctx.target_area_m2 - area
                if deficit > 0.0:
                    undersizing += deficit * deficit

            # Aspect penalty: (max/min - 1)² → 0 for squares, grows
            # for elongated rooms. Bounded enough that NSGA can
            # navigate.
            if min(w, d) > 0.0:
                aspect = max(w, d) / min(w, d)
                aspect_penalty += (aspect - 1.0) ** 2

        envelope_waste = max(0.0, self._envelope_area_m2 - total_area)

        return ObjectiveVector(
            values=(
                ("area_undersizing", round(undersizing, 6)),
                ("aspect_penalty", round(aspect_penalty, 6)),
                ("envelope_waste", round(envelope_waste, 6)),
            ),
            constraint_violations=0.0,
        )

    def signature(self) -> str:
        return self._sig

    def _compute_signature(self) -> str:
        """Stable identifier capturing the evaluator's bound context.

        Two evaluators with identical room context + envelope produce
        identical signatures. Used by C11b to validate replay
        determinism (LocalRefinementProvenance carries this).
        """
        # Sort by room_id so dict ordering doesn't perturb the hash.
        items = sorted(
            (
                (
                    ctx.room_id,
                    round(ctx.target_area_m2, 6),
                    round(ctx.min_width_m, 6),
                )
                for ctx in self._contexts.values()
            ),
            key=lambda t: t[0],
        )
        payload_parts = [
            "MultiObjectiveEvaluator",
            f"envelope={self._envelope_area_m2:.6f}",
            *(
                f"{rid}:{ta:.6f}:{mw:.6f}"
                for rid, ta, mw in items
            ),
        ]
        payload = "|".join(payload_parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────
# Helper — build an evaluator from upstream orchestrator state
# ─────────────────────────────────────────────────────────────────────


def build_real_evaluator_from_upstream(
    *,
    c11a_payload: Any,
    plot_analysis: Any,
) -> MultiObjectiveEvaluator:
    """Construct a `MultiObjectiveEvaluator` from C11a + C4 output.

    Walks the embedded C9 RoomSizeTable (via
    c11a_payload[0].source_candidate.room_sized_candidate.room_size_table)
    to pull per-room target areas + min widths. Pulls envelope area
    from `plot_analysis.plot.width_m * .depth_m`.

    Raises ValueError if the C11a payload is empty (caller should
    short-circuit before reaching the evaluator builder in that case).
    """
    if not c11a_payload:
        raise ValueError(
            "build_real_evaluator_from_upstream requires at least one "
            "C11a MutatedTopologyCandidate; got empty payload."
        )
    first = next(iter(c11a_payload))
    rooms = first.source_candidate.room_sized_candidate.room_size_table.rooms
    contexts = {
        r.room_id: RoomEvaluationContext(
            room_id=r.room_id,
            target_area_m2=float(r.target_m2),
            min_width_m=float(r.liveability_min_width_m),
        )
        for r in rooms
    }
    envelope_area = (
        float(plot_analysis.plot.width_m)
        * float(plot_analysis.plot.depth_m)
    )
    return MultiObjectiveEvaluator(
        room_contexts_by_id=contexts,
        envelope_area_m2=envelope_area,
    )


# ─────────────────────────────────────────────────────────────────────
# C11b input-shim — bridges FloorRoomBrief shape mismatch
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _C11bRoomRequirement:
    """One row of the shim brief C11b's `_extract_requirements_and_envelope`
    expects. Carries per-room min dims that the canonical FloorRoomBrief
    (used by C5/C8/C9) doesn't itself encode."""
    room_id: str
    category: str
    min_width_m: float
    min_depth_m: float


@dataclass(frozen=True)
class C11bBriefShim:
    """Minimal shim that satisfies C11b's brief contract.

    Required by `_extract_requirements_and_envelope` in C11b's
    orchestrator, which looks for a `room_requirements` attribute
    carrying per-room `min_width_m` + `min_depth_m`. The canonical
    `FloorRoomBrief` (used by C5/C8/C9) only carries high-level counts
    (bedroom_count, has_kitchen, etc.) — the per-room dimension data
    arrives at C11b only via the C9 RoomSizeTable nested deep in
    C11a's output.

    The orchestrator builds one of these from C11a's upstream chain
    and passes it to `run_local_refinement` IN PLACE OF the canonical
    FloorRoomBrief. C11b's contract is "structural" (duck-typed via
    getattr fallbacks); only the shim's room_requirements field is
    consumed.
    """
    room_requirements: tuple[_C11bRoomRequirement, ...]


def build_c11b_brief_shim_from_upstream(
    c11a_payload: Any,
) -> "C11bBriefShim":
    """Walk C11a output to extract per-room sizing and build the shim.

    Raises ValueError if the payload is empty.
    """
    if not c11a_payload:
        raise ValueError(
            "build_c11b_brief_shim_from_upstream requires a non-empty "
            "C11a payload."
        )
    first = next(iter(c11a_payload))
    rs_rooms = (
        first.source_candidate.room_sized_candidate.room_size_table.rooms
    )
    return C11bBriefShim(
        room_requirements=tuple(
            _C11bRoomRequirement(
                room_id=r.room_id,
                category=r.category.value,
                # C9 exposes `liveability_min_width_m` only; reuse it
                # for the depth floor too (both axes get the same NBC
                # minimum, which is the conservative-correct choice).
                min_width_m=float(r.liveability_min_width_m),
                min_depth_m=float(r.liveability_min_width_m),
            )
            for r in rs_rooms
        )
    )


__all__ = [
    "RoomEvaluationContext",
    "MultiObjectiveEvaluator",
    "build_real_evaluator_from_upstream",
    "C11bBriefShim",
    "build_c11b_brief_shim_from_upstream",
]
