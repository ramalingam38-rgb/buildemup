"""
C3a — Extreme Case Gate — UPSTREAM STUB for C3b consumption
============================================================

NOTE: This is a STUB module covering only the surface C3b consumes.
The real C3a (LOCKED at v0.2.1, Session 17 era) lives at
`buildemup_handoff_S50/06_upstream_codebase/buildemup/components/c03a/`
with full gate-state / option-generator / detector / counterfactual
modules. C3b only needs:

  - ResolvedBrief             — what the user committed to after C3a
  - KickbackContext           — payload C3b sends back to C3a for HEAVY tweaks

Both shapes are pinned by C3a v0.2.1 LOCKED spec; this stub reproduces
the minimum field surface C3b consumes (not the full type).

When the real C3a is ported into this working tree, this stub is
replaced by an import re-export; downstream C3b code does not change.

Stability: PINNED to C3a v0.2.1.LOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class ResolvedBrief:
    """The brief after C3a's Extreme Case Gate has resolved any
    detected extremes. C3b consumes this for context — what the user
    originally wanted vs what they got.

    Minimum fields per C3a v0.2.1 LOCKED:
      - brief_id, brief_signature: identity + R6 replay anchor
      - resolved_room_program: the final room-count + size targets
      - resolved_plot: plot id (links to C4 PlotAnalysis)
      - extreme_case_status: was an extreme case detected & resolved?
      - jurisdiction_profile_id: same identifier used downstream
    """
    brief_id:                 str
    brief_signature:          str
    resolved_plot_id:         str
    jurisdiction_profile_id:  str
    resolved_room_program:    tuple[tuple[str, int], ...] = field(default_factory=tuple)
    """(room_function, count) pairs. e.g. (("bedroom", 3), ("bath", 2))."""

    resolved_floor_count:     int = 1
    extreme_case_status:      Literal[
        "no_extreme_detected",
        "extreme_resolved",
        "preview_mode",   # if preview_mode, C3b refuses per § 1.4
    ] = "no_extreme_detected"
    """Per C3a v0.2.1: 'preview_mode' means a HEAVY extreme was detected
    but user chose to proceed under preview discipline. C3b refuses to
    iterate on preview-mode layouts (spec § 1.4)."""

    advisory_note:            str = ""

    def __post_init__(self) -> None:
        if not self.brief_id:
            raise ValueError("ResolvedBrief.brief_id must be non-empty")
        if not self.brief_signature:
            raise ValueError("ResolvedBrief.brief_signature must be non-empty")
        if not self.resolved_plot_id:
            raise ValueError("ResolvedBrief.resolved_plot_id must be non-empty")
        if not self.jurisdiction_profile_id:
            raise ValueError(
                "ResolvedBrief.jurisdiction_profile_id must be non-empty"
            )
        if self.resolved_floor_count < 1:
            raise ValueError(
                f"ResolvedBrief.resolved_floor_count must be >= 1; "
                f"got {self.resolved_floor_count}"
            )


@dataclass(frozen=True)
class KickbackContext:
    """The structured payload C3b sends back to C3a when a HEAVY tweak
    requires brief-level change (Mutation classification ==
    'brief_level_change').

    Per spec § 2.8 MutationEnvelope:
      'When classification == "brief_level_change", kick_back_payload
      is populated. Contains the structured request for C3a (which
      brief field to revisit, what context to surface).'
    """
    source_session_id:        str
    """The C3b session that surfaced the kickback."""

    target_brief_field:       Literal[
        "room_program",        # add/remove a bedroom, etc.
        "floor_count",          # 1F vs 2F
        "plot_orientation",     # rotate orientation (≈ brief change)
        "extreme_case_revisit", # re-open the extreme case
        "other",
    ]
    target_brief_field_advisory: str
    """Plain-English of what to revisit. Per Principle 3."""

    user_requested_change:    str
    """What the user asked for (verbatim quote if available)."""

    proposed_change_summary:  str
    """C3b's structured interpretation."""

    estimated_pipeline_rerun_seconds: float = 60.0
    """Per spec § 2.8 estimated_pathway_effort: 'Stepping back to the
    brief takes 1-2 minutes of your time, plus 60 seconds for the
    system to re-run.'"""

    def __post_init__(self) -> None:
        if not self.source_session_id:
            raise ValueError(
                "KickbackContext.source_session_id must be non-empty"
            )
        if not self.user_requested_change:
            raise ValueError(
                "KickbackContext.user_requested_change must be non-empty"
            )
        if not self.proposed_change_summary:
            raise ValueError(
                "KickbackContext.proposed_change_summary must be non-empty"
            )


# Marker for stub status
C3A_STUB_VERSION = "v0.2.1.LOCKED.stub.S52"

__all__ = ["ResolvedBrief", "KickbackContext", "C3A_STUB_VERSION"]
