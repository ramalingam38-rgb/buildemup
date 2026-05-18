"""C12 + C13 + C14 → C15 triple + metadata builder (S57 follow-up #7).

C15's `analyze_problems_batch` requires:
  - `triples: Sequence[tuple[c12_candidate, c13_placement, c14_report]]`
    — one per candidate, each carrying the C12 placement, the C13
    door placement, and the C14 circulation report.
  - `metadata_per_candidate: Sequence[ProblemAnalysisMetadata]`
    — orchestrator-supplied per-room context (cultural_profile,
    room_categories, main_entry_room_id, …) that C14's LOCKED schema
    does NOT encode (per B-PROJECT-PIPELINE-METADATA-CONTRACT).

This builder is the orchestrator-side construction step.

Signature-keyed join: all three upstream payloads carry a common
``source_(refined_|placed_)?candidate_signature`` that traces back to
the same upstream identity. We index C13 successes and C14 successes
by that signature so a candidate that failed at any tier is naturally
excluded from the C15 triples.
"""
from __future__ import annotations

from typing import Any, Sequence

from buildemup.components.c13.contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
)
from buildemup.components.c15.contracts import (
    CulturalProfile,
    ProblemAnalysisMetadata,
)


def _signature_of_c14(report: Any) -> str:
    """Pull the canonical signature off a C14 report (best-effort)."""
    return (
        getattr(report, "source_placed_candidate_signature", None)
        or getattr(report, "source_refined_candidate_signature", None)
        or getattr(report, "candidate_signature", None)
        or ""
    )


def _signature_of_c13(placement: Any) -> str:
    return (
        getattr(placement, "source_placed_candidate_signature", None)
        or getattr(placement, "source_refined_candidate_signature", None)
        or getattr(placement, "candidate_signature", None)
        or ""
    )


def _main_entry_room_id(placement: Any) -> str | None:
    """Return the placed_room that owns the is_main_entry door.

    Mirrors the C12+C13→C14 metadata builder (S57 #6). Returns None if
    no is_main_entry door exists (degenerate case — C13 Inv D6 says
    every SuccessfulDoorPlacement has exactly one).
    """
    doors = getattr(placement, "doors", ())
    main = [d for d in doors if getattr(d, "is_main_entry", False)]
    if not main:
        return None
    main_door = main[0]
    if main_door.room_a_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        return main_door.room_a_id
    if main_door.room_b_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        return main_door.room_b_id
    return None


# Mapping from the orchestrator's `vastu_tier` config knob to a
# best-fit CulturalProfile. v1 doesn't surface CulturalProfile in the
# orchestrator config separately — it derives from the existing vastu
# tier signal (PARTIAL → Tamil multigen as the most common Indian
# residential default; OFF / FULL fall back to the GENERIC profile).
# Production callers will likely want explicit profile control; that's
# tracked separately under the v1+ roadmap (post-B-238).
_VASTU_TO_CULTURAL_PROFILE = {
    "OFF":     CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    "PARTIAL": CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
    "FULL":    CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
}


def derive_cultural_profile(vastu_tier: str) -> CulturalProfile:
    """Map MasterOrchestratorConfig.vastu_tier → CulturalProfile.

    Defaults to INDIAN_MIDDLE_CLASS_GENERIC for unrecognized tiers so
    C15's strict metadata validation never fails on a tier bump.
    """
    return _VASTU_TO_CULTURAL_PROFILE.get(
        vastu_tier.upper() if isinstance(vastu_tier, str) else "",
        CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    )


def _build_metadata(
    placed_candidate: Any,
    placement: Any,
    *,
    cultural_profile: CulturalProfile,
) -> ProblemAnalysisMetadata | None:
    """Build ProblemAnalysisMetadata for one placed candidate.

    Returns None when the candidate carries no placed rooms (degenerate
    case — C15's metadata validator requires non-empty placed_room_ids).
    """
    placed_rooms = getattr(placed_candidate, "placed_rooms", ())
    if not placed_rooms:
        return None

    room_ids = tuple(sorted(r.room_id for r in placed_rooms))
    room_categories = {r.room_id: r.category for r in placed_rooms}

    main_entry = _main_entry_room_id(placement)
    if main_entry is None or main_entry not in room_categories:
        # Per Inv P17 main_entry_room_id is required + must be in
        # placed_room_ids. Pick the lex-ASC first room as a deterministic
        # fallback (C13 sparse-edge case where no main door exists).
        main_entry = room_ids[0]

    try:
        return ProblemAnalysisMetadata(
            cultural_profile=cultural_profile,
            placed_room_ids=room_ids,
            room_categories=room_categories,
            main_entry_room_id=main_entry,
        )
    except (TypeError, ValueError):
        # Defensive: any field that fails domain validation drops the
        # candidate from the C15 batch entirely. The orchestrator
        # surfaces this via its phase's notes count, not as a fatal.
        return None


def build_c15_inputs_from_upstream(
    *,
    c12_payload: Any,
    c13_payload: Any,
    c14_payload: Any,
    cultural_profile: CulturalProfile,
) -> tuple[
    tuple[tuple[Any, Any, Any], ...],
    tuple[ProblemAnalysisMetadata, ...],
]:
    """Build the (triples, metadata) pair for `analyze_problems_batch`.

    Returns parallel tuples — one entry per candidate that has a
    matching C12 placement, C13 door placement, and C14 report. Drops
    candidates that fail any of these joins (or that produce invalid
    metadata).
    """
    if c12_payload is None or c13_payload is None or c14_payload is None:
        return ((), ())

    # Index C12 + C14 by signature for O(1) joins.
    placed_by_sig: dict[str, Any] = {
        pc.source_refined_candidate_signature: pc
        for pc in getattr(c12_payload, "placed_candidates", ())
    }
    c14_by_sig: dict[str, Any] = {}
    for report in getattr(c14_payload, "successful", ()):
        sig = _signature_of_c14(report)
        if sig:
            c14_by_sig[sig] = report

    triples: list[tuple[Any, Any, Any]] = []
    metadata: list[ProblemAnalysisMetadata] = []

    for placement in getattr(c13_payload, "successful", ()):
        sig = _signature_of_c13(placement)
        placed = placed_by_sig.get(sig)
        report = c14_by_sig.get(sig)
        if placed is None or report is None:
            continue
        md = _build_metadata(
            placed, placement,
            cultural_profile=cultural_profile,
        )
        if md is None:
            continue
        triples.append((placed, placement, report))
        metadata.append(md)

    return tuple(triples), tuple(metadata)


__all__ = [
    "build_c15_inputs_from_upstream",
    "derive_cultural_profile",
]
