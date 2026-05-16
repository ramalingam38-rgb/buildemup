"""
C3b — Phase δ — User-facing presentation rendering
====================================================

Spec § 3 Phase δ:
  INPUT: full TradeoffSession with populated tweaks
  PROCESSING:
    1. Lex-ASC sort within each TweakOptionSet.tweaks by tweak_id (R6)
    2. Set TradeoffSession.current_status = "open_for_user_input"
    3. Compute canonical_replay_signature (R6), presentation_signature (R7),
       schema_descriptor_digest (R8)
    4. Persist session to SQLite WAL

  OUTPUT: TradeoffSession ready for downstream UI consumption

Per Rule 11 self-analysis:
  1. Sorting is enforced at dataclass construction (TweakOptionSet
     __post_init__ rejects unsorted tweaks). Phase δ's sort step is
     defensive — re-sort if any phase had unsorted output, but raise
     if dataclasses already accepted unsorted input. So in practice
     this is a no-op verification.
  2. Persistence is delegated to session_storage.py (called from
     orchestrator, not directly from Phase δ). Phase δ's job is signing.
"""
from __future__ import annotations

from ..config import C3bRuntimeConfig
from ..schema import TradeoffSession


def run_phase_delta(
    session:  TradeoffSession,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Render presentation: set status to open_for_user_input,
    re-sign session, return."""
    from .alpha import _resign_session
    import dataclasses

    # Verify lex-ASC sort (defensive — dataclasses already enforce)
    for opt_set in session.tweak_option_sets:
        tweak_ids = [t.tweak_id for t in opt_set.tweaks]
        assert tweak_ids == sorted(tweak_ids), (
            f"TweakOptionSet {opt_set.layout_id!r} tweaks unsorted at Phase δ "
            f"(would have failed dataclass invariant)"
        )

    # Ensure status reflects readiness for user input
    if session.current_status != "open_for_user_input":
        # Only change if it's a non-terminal status
        if session.current_status in (
            "open_for_user_input", "awaiting_subset_rerun",
            "iteration_cap_reached",
        ):
            new_session = dataclasses.replace(
                session, current_status="open_for_user_input",
            )
            return _resign_session(new_session, config)

    # Re-sign at presentation time
    return _resign_session(session, config)


__all__ = ["run_phase_delta"]
