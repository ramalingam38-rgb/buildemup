"""
BuildemUp — Component 12 — schema (output dataclasses)
=======================================================

Per C12 SPEC v1.0 LOCKED § 2.2 — public output types.

Six public dataclasses:
  - PlacedRoom            : one room with realized (x, y, w, d) geometry
  - SharedEdge            : shared-wall segment between two PlacedRooms
  - PlacedCandidate       : single-floor placement output
  - VerticalAlignmentReport : per-MF-candidate alignment outcome
  - MultiFloorPlacedCandidate : multi-floor placement output
  - PlacementBatchResult  : orchestrator batch output (successes + failures)

All dataclasses are frozen for hash-stability + replay determinism
(Inv 7).

Canonical orderings enforced in __post_init__:
  - PlacedCandidate.placed_rooms sorted lex-ASC by room_id
  - PlacedCandidate.shared_edges sorted lex-ASC by
    (room_a_id, room_b_id)
  - MultiFloorPlacedCandidate.per_floor_placements sorted by
    FloorRoomBrief.floor_label
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal


# =============================================================================
# § 2.2.1 — PlacedRoom
# =============================================================================

@dataclass(frozen=True)
class PlacedRoom:
    """One room with its realized axis-aligned (x, y, w, d) geometry
    in envelope coordinates (metres).

    Per C12 SPEC v1.0 § 2.2.1:
      - (x_m, y_m) = bottom-left corner of the room rectangle.
      - width_m / depth_m = extents along x / y axes.
      - room_id = stable lex-ASC ordering key (canonicalization, Inv 7).
      - category = canonical room category string (per v0.4-A2;
        derived from FloorRoomBrief or normalized via alias map for
        other_rooms strings).
      - operator_class_lineage = preserved upstream operator
        class signature for diagnostic provenance (per v0.3-A7).
    """
    room_id: str
    category: str
    x_m: float
    y_m: float
    width_m: float
    depth_m: float
    operator_class_lineage: str = ""

    def __post_init__(self) -> None:
        if not self.room_id:
            raise ValueError("PlacedRoom.room_id must be non-empty.")
        if not self.category:
            raise ValueError("PlacedRoom.category must be non-empty.")
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise ValueError(
                f"PlacedRoom requires positive extents; "
                f"got width={self.width_m}, depth={self.depth_m}."
            )


# =============================================================================
# § 2.2.2 — SharedEdge
# =============================================================================

@dataclass(frozen=True)
class SharedEdge:
    """One shared-wall segment between two PlacedRooms.

    Per C12 SPEC v1.0 § 2.2.2 + v0.2-A7 (ε-aware) + v0.2-A9 (NBC 2016
    doorway minima).

    Fields:
      - room_a_id < room_b_id lex-ASC (canonical ordering, Inv 7).
      - axis = which axis the wall runs along.
      - overlap_start_m, overlap_end_m = snapped to C7-Grid resolution.
      - overlap_length_m = end - start (snapped).
      - min_required_clear_width_m = NBC 2016 doorway minimum for
        the room-category pair (per v0.2-A9 / v0.4-A2).
      - doorway_feasible = (overlap_length_m >= min_required) AND
        (corner-offset check — currently length-only at v1; corner
        offset is B-C12-DOORWAY-CORNER-OFFSET post-v1).

    Consumed by C13 Door Placement per v0.3-A4 handoff contract:
    C13 treats doorway_feasible == False edges as not-door-candidates.
    """
    room_a_id: str
    room_b_id: str
    axis: Literal["vertical", "horizontal"]
    overlap_start_m: float
    overlap_end_m: float
    overlap_length_m: float
    min_required_clear_width_m: float
    doorway_feasible: bool

    def __post_init__(self) -> None:
        if not self.room_a_id or not self.room_b_id:
            raise ValueError("SharedEdge requires non-empty room ids.")
        if self.room_a_id >= self.room_b_id:
            raise ValueError(
                f"SharedEdge requires canonical order "
                f"room_a_id < room_b_id; got "
                f"{self.room_a_id!r} vs {self.room_b_id!r}."
            )
        if self.axis not in ("vertical", "horizontal"):
            raise ValueError(
                f"SharedEdge.axis must be 'vertical' or 'horizontal'; "
                f"got {self.axis!r}."
            )
        if self.overlap_length_m <= 0.0:
            raise ValueError(
                f"SharedEdge.overlap_length_m must be positive; "
                f"got {self.overlap_length_m}."
            )
        if self.min_required_clear_width_m <= 0.0:
            raise ValueError(
                f"SharedEdge.min_required_clear_width_m must be "
                f"positive; got {self.min_required_clear_width_m}."
            )


# =============================================================================
# § 2.2.3 — PlacedCandidate
# =============================================================================

@dataclass(frozen=True)
class PlacedCandidate:
    """Single-floor placement output. The C12 equivalent of C11b's
    RefinedCandidate.

    Per C12 SPEC v1.0 § 2.2.3.

    Fields:
      - source_refined_candidate_signature: provenance back to C11b
        input (canonical string capturing the RefinedCandidate that
        produced this placement).
      - placed_rooms: tuple of PlacedRoom sorted lex-ASC by room_id.
      - shared_edges: tuple of SharedEdge sorted lex-ASC by
        (room_a_id, room_b_id).
      - placement_algorithm: the algorithm string used (v1 = only
        "slicing_kd_tree" per v0.3-A1).
      - envelope_width_m / envelope_depth_m: the envelope inside
        which placement occurred.
    """
    source_refined_candidate_signature: str
    placed_rooms: tuple[PlacedRoom, ...]
    shared_edges: tuple[SharedEdge, ...]
    placement_algorithm: Literal["slicing_kd_tree"]
    envelope_width_m: float
    envelope_depth_m: float

    def __post_init__(self) -> None:
        if not self.source_refined_candidate_signature:
            raise ValueError(
                "PlacedCandidate.source_refined_candidate_signature "
                "must be non-empty."
            )
        # Inv: placed_rooms sorted lex-ASC by room_id.
        ids = [r.room_id for r in self.placed_rooms]
        if ids != sorted(ids):
            raise ValueError(
                f"PlacedCandidate.placed_rooms must be sorted lex-ASC "
                f"by room_id; got order {ids}."
            )
        if len(set(ids)) != len(ids):
            raise ValueError(
                f"PlacedCandidate.placed_rooms contains duplicate "
                f"room_ids; got {ids}."
            )
        # Inv: shared_edges sorted lex-ASC by (room_a_id, room_b_id).
        edge_keys = [(e.room_a_id, e.room_b_id) for e in self.shared_edges]
        if edge_keys != sorted(edge_keys):
            raise ValueError(
                f"PlacedCandidate.shared_edges must be sorted lex-ASC; "
                f"got {edge_keys}."
            )
        if self.envelope_width_m <= 0.0 or self.envelope_depth_m <= 0.0:
            raise ValueError(
                f"PlacedCandidate envelope dims must be positive; "
                f"got w={self.envelope_width_m}, d={self.envelope_depth_m}."
            )


# =============================================================================
# § 2.2.4 — VerticalAlignmentReport
# =============================================================================

@dataclass(frozen=True)
class VerticalAlignmentReport:
    """Per-MF-candidate vertical-alignment outcome.

    Per C12 SPEC v1.0 § 2.2.4 + v0.2-A2 (monotonic-δ convergence).

    Fields:
      - converged: did the retry loop converge within budget?
      - retries_used: number of MFRA retries actually performed.
      - delta_progression: tuple of δ values per retry iteration,
        per v0.2-A2 (preserved for post-hoc convergence debugging).
        Length <= multi_floor_max_realign_iterations + 1 (Inv 13).
      - final_max_misalignment_m: residual max-feature-misalignment
        after the last iteration (whether converged or aborted).
      - misaligned_features: tuple of feature names that remain
        misaligned (empty if converged).
    """
    converged: bool
    retries_used: int
    delta_progression: tuple[float, ...]
    final_max_misalignment_m: float
    misaligned_features: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.retries_used < 0:
            raise ValueError(
                f"VerticalAlignmentReport.retries_used must be >= 0; "
                f"got {self.retries_used}."
            )
        if self.final_max_misalignment_m < 0.0:
            raise ValueError(
                f"VerticalAlignmentReport.final_max_misalignment_m "
                f"must be >= 0; got {self.final_max_misalignment_m}."
            )


# =============================================================================
# § 2.2.5 — MultiFloorPlacedCandidate
# =============================================================================

@dataclass(frozen=True)
class MultiFloorPlacedCandidate:
    """Multi-floor placement output.

    Per C12 SPEC v1.0 § 2.2.5 + v0.2-A2 (alignment report) + v0.2-A10
    (vertical core reservation).

    Fields:
      - source_multifloor_candidate_signature: canonical string
        capturing the upstream C11b MF candidate.
      - per_floor_placements: tuple of (floor_label, PlacedCandidate)
        sorted by floor_label.
      - alignment_report: VerticalAlignmentReport.
      - vertical_cores_reserved: tuple of (label, x_m, y_m, w_m, d_m)
        per v0.2-A10 reservation pre-step.
    """
    source_multifloor_candidate_signature: str
    per_floor_placements: tuple[tuple[str, PlacedCandidate], ...]
    alignment_report: VerticalAlignmentReport
    vertical_cores_reserved: tuple[tuple[str, float, float, float, float], ...]

    def __post_init__(self) -> None:
        if not self.source_multifloor_candidate_signature:
            raise ValueError(
                "MultiFloorPlacedCandidate."
                "source_multifloor_candidate_signature must be non-empty."
            )
        labels = [f for f, _ in self.per_floor_placements]
        if labels != sorted(labels):
            raise ValueError(
                f"MultiFloorPlacedCandidate.per_floor_placements must "
                f"be sorted by floor_label; got {labels}."
            )
        if len(set(labels)) != len(labels):
            raise ValueError(
                f"MultiFloorPlacedCandidate.per_floor_placements "
                f"contains duplicate floor labels; got {labels}."
            )


# =============================================================================
# § 2.2.6 — PlacementBatchResult
# =============================================================================

@dataclass(frozen=True)
class FailureRecord:
    """Per-candidate failure under WARN mode (per v0.2 / v0.3
    structured-failure pattern).

    Per C12 SPEC v1.0 § 2.2.6.
    """
    candidate_signature: str
    error_type: str  # the class name of the PerCandidatePlacementError
    error_message: str
    phase: Literal["phase0", "phase0b", "phase1", "phase1b", "phase2", "phase3"]


@dataclass(frozen=True)
class PlacementBatchResult:
    """Orchestrator batch output: successes + failures.

    Per C12 SPEC v1.0 § 2.2.6.
    """
    placed_candidates: tuple[PlacedCandidate, ...]
    multifloor_placed_candidates: tuple[MultiFloorPlacedCandidate, ...]
    failures: tuple[FailureRecord, ...]
    c12_version: str  # captured from versioning.C12_VERSION
    cache_key: str

    def __post_init__(self) -> None:
        if not self.c12_version:
            raise ValueError(
                "PlacementBatchResult.c12_version must be non-empty."
            )
        if not self.cache_key:
            raise ValueError(
                "PlacementBatchResult.cache_key must be non-empty."
            )


# =============================================================================
# Public exports
# =============================================================================

__all__ = [
    "PlacedRoom",
    "SharedEdge",
    "PlacedCandidate",
    "VerticalAlignmentReport",
    "MultiFloorPlacedCandidate",
    "FailureRecord",
    "PlacementBatchResult",
]
