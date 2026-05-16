"""
BuildemUp — Component 12 — vertical core reservation (Phase 1b)
================================================================

Per C12 SPEC v1.0 LOCKED v0.2-A10:

> Phase 1b — Vertical core reservation (MF inputs only)
>
> For multi-floor inputs, BEFORE per-floor SFP runs, C12 identifies
> the alignment-relevant "vertical cores":
> 1. Staircase rectangle (from FloorRoomBrief.stair_zone)
> 2. Wet-zone column centroid(s)
> 3. Structural column grid (from C7 Grid; columns aligned across
>    floors by definition)
>
> Each vertical core is reserved at the SAME (x, y) position on every
> floor before any per-floor SFP runs. This prevents the iteration
> oscillation pattern: per-floor SFP placing a staircase at different
> (x, y) on each floor, then VAV failing, then retry trying to "pull"
> the misaligned floor — wasted work that could have been prevented.

This module ships the data structures + reservation derivation
helpers. The actual integration into Phase 1 placement (where the
reserved rectangles become occupancy constraints) is S45 work in
the slicing-tree subpackage.

Full coupled multi-floor placement (joint optimization across all
floors) remains B-C12-COUPLED-MF-PLACEMENT post-v1. The reservation
pre-step is the v1-tractable middle ground.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


VerticalCoreKind = Literal[
    "staircase",
    "wet_zone_column",
    "structural_column",
]


@dataclass(frozen=True)
class VerticalCoreReservation:
    """One alignment-relevant rectangle reserved at the same (x, y)
    on every floor before per-floor SFP runs.

    Fields:
      - label: stable identifier for the core (e.g., "staircase_1",
        "wet_stack_kitchen_bath_master"). Used for VAV alignment
        report misaligned_features tuple when applicable.
      - kind: which type of vertical structure this represents.
      - x_m, y_m, width_m, depth_m: the reserved rectangle in
        envelope coordinates.

    Equal-by-value for hashability + replay determinism.
    """
    label: str
    kind: VerticalCoreKind
    x_m: float
    y_m: float
    width_m: float
    depth_m: float

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("VerticalCoreReservation.label must be non-empty.")
        if self.kind not in (
            "staircase", "wet_zone_column", "structural_column",
        ):
            raise ValueError(
                f"VerticalCoreReservation.kind must be a known "
                f"VerticalCoreKind; got {self.kind!r}."
            )
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise ValueError(
                f"VerticalCoreReservation requires positive extents; "
                f"got width={self.width_m}, depth={self.depth_m}."
            )

    def to_tuple(self) -> tuple[str, float, float, float, float]:
        """For embedding into MultiFloorPlacedCandidate.vertical_cores_reserved
        per the schema (label, x, y, w, d) tuple form."""
        return (self.label, self.x_m, self.y_m, self.width_m, self.depth_m)


def canonicalize_reservations(
    reservations: tuple[VerticalCoreReservation, ...],
) -> tuple[VerticalCoreReservation, ...]:
    """Sort reservations into canonical lex-ASC order by label, per
    v0.2-A4 canonicalization rule #5 (no unordered collections).

    Also enforces: no two reservations may share a label."""
    labels = [r.label for r in reservations]
    if len(set(labels)) != len(labels):
        raise ValueError(
            f"VerticalCoreReservation set contains duplicate labels; "
            f"got {labels}."
        )
    return tuple(sorted(reservations, key=lambda r: r.label))


def reservations_overlap(
    a: VerticalCoreReservation,
    b: VerticalCoreReservation,
    *,
    epsilon_m: float = 0.001,
) -> bool:
    """Two reservations overlap in interior. Used by the orchestrator
    to validate that user-provided cores don't conflict."""
    return (
        a.x_m + a.width_m > b.x_m + epsilon_m
        and b.x_m + b.width_m > a.x_m + epsilon_m
        and a.y_m + a.depth_m > b.y_m + epsilon_m
        and b.y_m + b.depth_m > a.y_m + epsilon_m
    )


def assert_no_internal_conflicts(
    reservations: tuple[VerticalCoreReservation, ...],
    *,
    epsilon_m: float = 0.001,
) -> None:
    """Raise ValueError if any two reservations in the set overlap
    in interior (touching edges is fine — adjacent cores like
    staircase + wet stack are common)."""
    for i in range(len(reservations)):
        for j in range(i + 1, len(reservations)):
            if reservations_overlap(
                reservations[i], reservations[j], epsilon_m=epsilon_m,
            ):
                raise ValueError(
                    f"VerticalCoreReservations overlap: "
                    f"{reservations[i].label!r} vs {reservations[j].label!r}."
                )


__all__ = [
    "VerticalCoreKind",
    "VerticalCoreReservation",
    "canonicalize_reservations",
    "reservations_overlap",
    "assert_no_internal_conflicts",
]
