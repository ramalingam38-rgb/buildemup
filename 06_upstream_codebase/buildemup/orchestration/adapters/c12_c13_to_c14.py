"""C12 + C13 → C14 metadata builder (S57 follow-up #6).

C14's `analyze_circulation_batch` requires a
``room_metadata_by_signature: dict[str, tuple[RoomMetadata, ...]]``
where each entry maps a C13 SuccessfulDoorPlacement's signature to
the per-room metadata C14 needs (category + main-entry flag).

C14's own contracts module says: "the metadata bundle is NOT encoded
in C13's LOCKED schema; the orchestrator accepts it as a separate
placed_room_metadata parameter (mirroring C13 Phase F's pattern)."
This builder is that orchestrator-side construction step.

Data sources:
  - Room categories: from C12 PlacedRoom.category (mirrors upstream
    C9 RoomSizeRequirement.category via C12's category-passthrough).
  - Main-entry flag: derived from the C13 Door with is_main_entry=True.
    Per C13 Inv D6, every SuccessfulDoorPlacement has exactly one
    such door; the non-EXTERNAL endpoint of that door is the main
    entry room (lex-ASC tiebreak if both endpoints are internal).
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c13.contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
)
from buildemup.components.c14.contracts import RoomMetadata


def _derive_main_entry_room_id(placement: Any) -> str | None:
    """Find the room owning the is_main_entry door.

    Mirrors C14 orchestrator's _derive_main_entry_room_id but kept
    local to the adapter so this module doesn't reach into C14's
    private API. Returns None if no is_main_entry door exists (which
    shouldn't happen for valid SuccessfulDoorPlacements per Inv D6,
    but we handle it defensively).
    """
    main_doors = [d for d in placement.doors if d.is_main_entry]
    if not main_doors:
        return None
    main_door = main_doors[0]
    if main_door.room_a_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        return main_door.room_a_id
    if main_door.room_b_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        return main_door.room_b_id
    return None  # Both endpoints EXTERNAL — impossible per C13 contract


def _placed_candidate_index_by_signature(
    c12_payload: Any,
) -> dict[str, Any]:
    """Index C12's placed candidates by signature for O(1) lookup."""
    return {
        pc.source_refined_candidate_signature: pc
        for pc in c12_payload.placed_candidates
    }


def build_room_metadata_by_signature(
    *,
    c12_payload: Any,
    c13_payload: Any,
) -> dict[str, tuple[RoomMetadata, ...]]:
    """Build the metadata dict C14's batch orchestrator expects.

    For each SuccessfulDoorPlacement in C13's output, look up the
    corresponding PlacedCandidate by signature (C13's
    source_placed_candidate_signature == C12's
    source_refined_candidate_signature; both trace back to the same
    upstream candidate identity per the pipeline naming convention).
    Build a RoomMetadata per placed room, marking is_main_entry_room
    for whichever room owns the main-entry door.

    Returns a dict ready to pass as `room_metadata_by_signature=` to
    `analyze_circulation_batch`. C14 requires the key set to cover
    every SuccessfulDoorPlacement; signatures missing from C12 will
    cause C14 to raise GraphInconsistencyError (under STRICT) or
    surface a FailedCirculationAnalysis (under WARN).
    """
    if c12_payload is None or c13_payload is None:
        return {}

    placed_by_sig = _placed_candidate_index_by_signature(c12_payload)
    metadata: dict[str, tuple[RoomMetadata, ...]] = {}

    for placement in c13_payload.successful:
        sig = placement.source_placed_candidate_signature
        placed_candidate = placed_by_sig.get(sig)
        if placed_candidate is None:
            # No C12 record for this C13 placement — should not happen
            # given the orchestrator's strict downstream wiring. Skip
            # so C14 surfaces the missing key as its own error.
            continue
        main_entry = _derive_main_entry_room_id(placement)
        rooms = tuple(
            RoomMetadata(
                room_id=pr.room_id,
                category=pr.category,
                is_main_entry_room=(pr.room_id == main_entry),
            )
            for pr in placed_candidate.placed_rooms
        )
        metadata[sig] = rooms

    return metadata


__all__ = ["build_room_metadata_by_signature"]
