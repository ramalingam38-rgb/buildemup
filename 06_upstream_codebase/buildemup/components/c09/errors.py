"""
BuildemUp† — Component 9 (Room Sizer) — Errors module.

Per C9 SPEC v0.7 LOCKED § 6 (Failure modes) and § 14.39 / § 14.40 / § 14.41.

Exception hierarchy:

    RoomSizingError                       (base; never raised directly)
    ├── PerCandidateError                 (per-candidate failures; aggregated by orchestrator)
    │   ├── RoomSizingInfeasibleError     (Inv 9 — total area infeasibility; B-NNN-A)
    │   ├── WidthInfeasibleError          (Inv 17a — deterministic width impossibility; B-NNN-J)
    │   ├── PackingInfeasibleError        (Inv 10 + STRICT mode escalation; v0.7)
    │   ├── WidthRiskyError               (Inv 17b RISKY + STRICT mode escalation; v0.7)
    │   └── GridOversizeError             (Inv 18 OVERSIZED + STRICT mode escalation; B-NNN-K)
    ├── BatchSizingInfeasibleError        (all input candidates failed per-candidate; v0.7)
    └── NBCConfidenceTooLow               (systemic; require_verified_nbc=True with unverified row)

Caller-error / non-C9-typed exceptions raised before per-candidate loop:
    - TypeError (input type mismatches)
    - ValueError (e.g., zero bedrooms)
    - NotImplementedError (B-066: non-rectangular plot)
    - KeyError (KB integrity: missing row for resolved tier)

Walk #6/#7 rationale (§ 14.35, § 14.39, § 14.40, § 14.41): deterministic mathematical
impossibility (room_width > envelope_min_axis; total_liveability_area > envelope) is not a
heuristic — fail-fast at the C9 boundary instead of WARN-and-continue. Heuristic
risks (Inv 10 packing, Inv 17b RISKY, Inv 18 OVERSIZED) WARN by default; STRICT mode
opt-in escalates them per-candidate. Failed candidates drop from the output tuple;
the batch only fails when ALL candidates fail.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal, Optional

if TYPE_CHECKING:
    pass  # avoid circular imports; types referenced only in docstrings


# B-NEW-P (S38) — error severity classification, required by C11a v1.0 § 2.7.
# See C10/errors.py for the same pattern.
_SeverityTier = Literal["per_candidate", "batch", "systemic"]


# =============================================================================
# Base hierarchy
# =============================================================================


class RoomSizingError(Exception):
    """Base for all C9 errors. Per SPEC § 6.

    Callers that don't need to distinguish the failure mode can catch this.
    Raised in two paths:
      - Caller-error / systemic (raised once before the per-candidate loop):
        currently only ``NBCConfidenceTooLow`` extends this directly.
      - Per-candidate (caught and aggregated by the orchestrator): every
        ``PerCandidateError`` subclass raises through this base.
    """

    # B-NEW-P (S38): per-candidate is the conservative default for the base
    # class. Subclasses override to "batch" or "systemic" as appropriate.
    severity_tier: ClassVar[_SeverityTier] = "per_candidate"


# =============================================================================
# Per-candidate failures (§ 14.40)
# =============================================================================


class PerCandidateError(RoomSizingError):
    """Base for per-candidate failures. NEW v0.7 (§ 14.40).

    The orchestrator catches subclasses of this in its per-candidate loop and
    aggregates them into ``BatchSizingInfeasibleError`` only when ALL input
    candidates failed. A successful sibling candidate keeps the batch alive.

    Subclasses MUST set ``candidate_index`` if known so that callers can
    correlate the failure back to the input candidate position.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.candidate_index = candidate_index


class RoomSizingInfeasibleError(PerCandidateError):
    """Inv 9: ``Σ liveability_min_area_m2 > buildable_envelope_minus_corridor_m2``.

    Per § 4.6 / § 4.7 / B-NNN-A. Total-area infeasibility on a single candidate
    — the brief asks for more rooms than the envelope can fit. Caller (eventually
    C2 retry contract per B-NNN-A) must drop a room or expand the plot.

    Carries the deficit so the caller can quantify the gap.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        total_liveability_min_area_m2: float | None = None,
        envelope_minus_corridor_m2: float | None = None,
        deficit_m2: float | None = None,
    ) -> None:
        super().__init__(message, candidate_index=candidate_index)
        self.total_liveability_min_area_m2 = total_liveability_min_area_m2
        self.envelope_minus_corridor_m2 = envelope_minus_corridor_m2
        self.deficit_m2 = deficit_m2


class WidthInfeasibleError(PerCandidateError):
    """Inv 17a: any room's ``liveability_min_width_m > envelope_min_axis``.

    Per § 4.6 / § 4.7 / B-NNN-J. Deterministic placement impossibility —
    the room cannot fit on this envelope regardless of placement (the room is
    wider than the envelope's smaller axis). NEW v0.6 (Walk #6 #1, web-grounded
    fail-fast). Caller must escalate to brief renegotiation or plot expansion.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        impossible_room_ids: tuple[str, ...] = (),
        envelope_min_axis_m: float | None = None,
    ) -> None:
        super().__init__(message, candidate_index=candidate_index)
        self.impossible_room_ids = impossible_room_ids
        self.envelope_min_axis_m = envelope_min_axis_m


class PackingInfeasibleError(PerCandidateError):
    """Inv 10 + STRICT mode escalation. NEW v0.7 (§ 14.41).

    Raised only when ``config.enforcement_mode == "STRICT"`` and the heuristic
    packing check fails (``Σ liveability_min_area > envelope * packing_efficiency``).
    Default WARN mode logs to provenance only.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        total_liveability_min_area_m2: float | None = None,
        packing_capacity_m2: float | None = None,
        packing_efficiency: float | None = None,
    ) -> None:
        super().__init__(message, candidate_index=candidate_index)
        self.total_liveability_min_area_m2 = total_liveability_min_area_m2
        self.packing_capacity_m2 = packing_capacity_m2
        self.packing_efficiency = packing_efficiency


class WidthRiskyError(PerCandidateError):
    """Inv 17b RISKY + STRICT mode escalation. NEW v0.7 (§ 14.41).

    Raised only when ``config.enforcement_mode == "STRICT"`` and one or more
    rooms have ``WidthFeasibilityVerdict.RISKY``. Default WARN mode logs to
    provenance and lets the candidate through.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        risky_room_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, candidate_index=candidate_index)
        self.risky_room_ids = risky_room_ids


class GridOversizeError(PerCandidateError):
    """Inv 18 OVERSIZED + STRICT mode escalation. NEW v0.7 (§ 14.41 / § 14.42).

    B-NNN-K. Raised only when ``config.enforcement_mode == "STRICT"`` and one or
    more rooms have ``GridBayFeasibility.OVERSIZED`` (room width >
    3 x grid.bay_max_m). Default WARN mode logs and lets the candidate through.

    § 14.42 documents why this is heuristic (grids are structurally negotiable
    via transfer beams / alternate column patterns), unlike Inv 17a width which
    is geometric impossibility on a fixed envelope.
    """

    def __init__(
        self,
        message: str,
        *,
        candidate_index: int | None = None,
        oversized_room_ids: tuple[str, ...] = (),
        bay_max_m: float | None = None,
    ) -> None:
        super().__init__(message, candidate_index=candidate_index)
        self.oversized_room_ids = oversized_room_ids
        self.bay_max_m = bay_max_m


# =============================================================================
# Batch-level failure (§ 14.40)
# =============================================================================


class BatchSizingInfeasibleError(RoomSizingError):
    """All input candidates failed per-candidate. NEW v0.7 (§ 14.40).

    Raised by the orchestrator when the per-candidate loop produces zero
    successes. Wraps the list of ``(input_index, PerCandidateError)`` pairs and
    the input cardinality so the caller can inspect every failure.

    Per-candidate exceptions caught here include any ``PerCandidateError``
    subclass, including the v0.7 STRICT-mode escalations.
    """

    severity_tier: ClassVar[_SeverityTier] = "batch"  # B-NEW-P (S38)

    def __init__(
        self,
        failures: list[tuple[int, PerCandidateError]],
        input_count: int,
    ) -> None:
        names = ", ".join(
            f"#{idx}={type(exc).__name__}" for idx, exc in failures
        )
        super().__init__(
            f"All {input_count} input candidates failed C9 sizing "
            f"per-candidate: {names}"
        )
        self.failures = tuple(failures)
        self.input_count = input_count


# =============================================================================
# Systemic failure (§ 4.6)
# =============================================================================


class NBCConfidenceTooLow(RoomSizingError, KeyError):
    """``config.require_verified_nbc=True`` AND a needed NBC row uses
    a ``source_confidence != VERIFIED`` value.

    Per § 4.6 / § 14.32. Systemic — not per-candidate (the NBC table is shared
    across all candidates). Raised once before the per-candidate loop. Extends
    ``KeyError`` for backward compatibility with callers that handle "row
    unavailable" via KeyError catches.

    Q18 (open in spec § 15): may become per-candidate in a future revision when
    multi-floor dwelling-tier resolution per-candidate matters. v0.7 ships
    systemic for simplicity.
    """

    severity_tier: ClassVar[_SeverityTier] = "systemic"  # B-NEW-P (S38)

    def __init__(
        self,
        message: str,
        *,
        unverified_room_ids: tuple[str, ...] = (),
        unverified_clauses: tuple[str, ...] = (),
    ) -> None:
        # KeyError's first positional arg becomes ``args[0]``; we want the message
        # string, not a synthesized repr. Initialize via Exception path.
        Exception.__init__(self, message)
        self.unverified_room_ids = unverified_room_ids
        self.unverified_clauses = unverified_clauses


__all__ = [
    "RoomSizingError",
    "PerCandidateError",
    "RoomSizingInfeasibleError",
    "WidthInfeasibleError",
    "PackingInfeasibleError",
    "WidthRiskyError",
    "GridOversizeError",
    "BatchSizingInfeasibleError",
    "NBCConfidenceTooLow",
]
