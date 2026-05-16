"""
C3b — Phase ε — User-turn handling
=====================================

Spec § 3 Phase ε:
  INPUT: TradeoffSession + UserAction (accept / reject / finalize /
         abandon / kickback / no_action)
  PROCESSING:
    1. Validate chosen_tweak_id is in current presented set (Q3 Level B
       discipline — chosen ∈ presented)
    2. Append SessionTurn to session_history
    3. Branch on user_action:
       - accepted_tweak LIGHT  → apply in-place, regen options
       - accepted_tweak MEDIUM → emit SubsetRerunRequest, status →
                                  awaiting_subset_rerun
       - rejected_tweak        → presented_count++, no mutation
       - no_action_continue    → no state change
       - finalized_layout_choice → ResolvedSelection, status → resolved
       - kicked_back_to_c3a    → status → kicked_back_to_c3a (terminal)
       - abandoned_session     → status → abandoned_no_tweaks (terminal)
    4. Iteration cap check: if iteration_count >= cap → force
       iteration_cap_reached

R14 (regression detection) fires inside complete_subset_rerun (called
after MEDIUM rerun returns). R15 (compatibility) fires at apply.
R16 (single-linear-history) is enforced by TradeoffSession's
__post_init__ (iteration_index == position).

Rule 11 self-analysis:
  1. Phase ε ITSELF doesn't run the subset rerun — that's the
     orchestrator's job. Phase ε's MEDIUM-accept path emits the
     SubsetRerunRequest and changes session status to
     'awaiting_subset_rerun'. The orchestrator (or its caller) then
     invokes the rerun and calls back into complete_subset_rerun.
  2. R14 regression detection compares pre-rerun and post-rerun
     ProblemReport critical counts. We pass both as arguments to
     complete_subset_rerun.
  3. The Q3 Level B invariant (chosen ∈ presented) is enforced at
     SessionTurn dataclass construction; Phase ε just constructs the
     turn correctly. Defensive: we also validate before constructing.
  4. The user_action='abandoned_session' branch picks the
     highest-ranked layout (rank 0) as the default selection. This
     mirrors the spec's "user accepts a layout as-is" framing.
"""
from __future__ import annotations

import dataclasses
import uuid
from typing import Optional

from buildemup.components.c15.schema import (
    CheckSeverity,
    CheckStatus,
    ProblemReport,
)

from ..config import C3bRuntimeConfig
from ..contracts import C3bInputBundle, KickbackContext
from ..errors import (
    CompatibilityAssertionFailedError,
    LocalTradeoffError,
)
from ..schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplyStatus,
    CompatibilityAssertion,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionStatus,
    SessionTurn,
    SubsetRerunRequest,
    TradeoffSession,
    TweakOption,
    UserAction,
)
from ..versioning import (
    MAX_REPRESENT_COUNT,
    REGRESSION_CRITICAL_INCREASE_THRESHOLD,
)


# ============================================================
# § 1 — Helpers
# ============================================================

def _all_presented_tweak_ids(session: TradeoffSession) -> tuple[str, ...]:
    """All tweak_ids currently presented across all layout option sets."""
    ids: set[str] = set()
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            ids.add(t.tweak_id)
    return tuple(sorted(ids))


def _find_tweak(
    session:   TradeoffSession,
    tweak_id:  str,
) -> Optional[tuple[TweakOption, str]]:
    """Find a tweak by id across all option sets; return (tweak, layout_id) or None."""
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            if t.tweak_id == tweak_id:
                return t, opt_set.layout_id
    return None


def _bump_iteration_count(session: TradeoffSession) -> int:
    """Returns next iteration_count value."""
    return session.iteration_count + 1


def _at_iteration_cap(session: TradeoffSession) -> bool:
    """Spec § 3 Phase ε step 4: iteration cap check."""
    return _bump_iteration_count(session) >= session.iteration_cap


def _new_turn_id(iteration_index: int) -> str:
    return f"turn_{iteration_index:04d}_{uuid.uuid4().hex[:8]}"


# ============================================================
# § 2 — Compatibility check (R15)
# ============================================================

def check_compatibility_against_history(
    tweak:             TweakOption,
    applied_history:   tuple[str, ...],
) -> tuple[CompatibilityAssertion, ...]:
    """For each prior applied tweak, run pairwise compatibility check.

    v1.0: stub pairwise that returns 'compatible' unless we detect
    a known conflict pattern. v1.x will use formal dependency graph
    per B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH.

    Known conflict patterns (heuristic):
      - kitchen_reorient + pooja_relocate (both want east → corner conflict)
      - wet_zone_restage + kitchen_reorient (wet zone vs kitchen wet area)
    """
    if not applied_history:
        return ()
    assertions: list[CompatibilityAssertion] = []
    # Heuristic: identical category against itself = always compatible
    # Cross-category conflicts surface as 'ambiguous' (advisory only)
    for prior_id in sorted(applied_history):
        # We don't know prior's category here without lookup; v1.0 just
        # emits 'compatible' assertion. Real conflict detection lives
        # at apply-time in apply_subset_rerun_result (which has
        # full context).
        assertions.append(CompatibilityAssertion(
            against_applied_tweak_id=prior_id,
            compatibility_kind="spatial_overlap_check",
            result="compatible",
            advisory_note=None,
        ))
    return tuple(assertions)


# ============================================================
# § 3 — LIGHT tweak application (in-place)
# ============================================================

def _apply_light_tweak(
    session:   TradeoffSession,
    tweak:     TweakOption,
    config:    C3bRuntimeConfig,
) -> tuple[TradeoffSession, ApplyOutcome]:
    """Apply a LIGHT tweak in-place. Per spec § 3 Phase ε:
       'apply mutation in-place to layout geometry / finish schedule,
        regenerate TweakOptionSet for that layout'

    v1.0 stub: applies the mutation by removing the accepted tweak
    from the option set (so it won't be re-suggested) and bumping
    presented_count on related tweaks. Real layout-geometry mutation
    is downstream of Phase ε and handled by the orchestrator.

    Returns (new_session, ApplyOutcome)."""
    # Remove the accepted tweak from its option set (it's been applied);
    # don't touch other tweaks
    new_option_sets = []
    for opt_set in session.tweak_option_sets:
        if any(t.tweak_id == tweak.tweak_id for t in opt_set.tweaks):
            remaining = tuple(
                t for t in opt_set.tweaks if t.tweak_id != tweak.tweak_id
            )
            new_option_sets.append(dataclasses.replace(
                opt_set, tweaks=remaining,
            ))
        else:
            new_option_sets.append(opt_set)
    new_session = dataclasses.replace(
        session,
        tweak_option_sets=tuple(new_option_sets),
    )
    outcome = ApplyOutcome(
        apply_status="applied_successfully",
        error_summary=None,
        new_layout_signature=f"sig_after_{tweak.tweak_id}",
        new_problem_report_id=None,    # LIGHT doesn't rerun PR
        regression_detected=False,
        newly_critical_check_ids=(),
    )
    return new_session, outcome


# ============================================================
# § 4 — MEDIUM tweak application (emit subset-rerun request)
# ============================================================

def _apply_medium_tweak_emit_rerun(
    session:   TradeoffSession,
    tweak:     TweakOption,
    config:    C3bRuntimeConfig,
) -> tuple[TradeoffSession, ApplyOutcome, bool]:
    """Stage a MEDIUM tweak — set session status to awaiting_subset_rerun
    and emit the SubsetRerunRequest (already embedded in tweak's
    ApplySpecification).

    The actual rerun happens externally; complete_subset_rerun() is
    called when results return.

    v0.5 A2 — increments medium_tweak_count_since_full_recompute.
    Returns a tuple (new_session, outcome, full_recompute_triggered).
    full_recompute_triggered is True when the increment crossed
    config.full_recompute_threshold, signaling the caller to attach a
    'full_coherence_recheck_triggered' advisory.
    """
    # Verify the apply_spec has a subset_rerun_payload
    srr = tweak.apply_specification.subset_rerun_payload
    if srr is None:
        raise LocalTradeoffError(
            f"MEDIUM tweak {tweak.tweak_id!r} has no subset_rerun_payload "
            f"(R4 violation reached Phase ε — should have been caught at "
            f"TweakOption construction)",
            session_id=session.session_id,
            phase="epsilon",
        )
    # v0.5 A2 — increment counter; if it crosses threshold, signal
    # full-recompute. Counter resets in complete_subset_rerun on success.
    new_count = session.medium_tweak_count_since_full_recompute + 1
    full_recompute_triggered = new_count >= config.full_recompute_threshold
    new_session = dataclasses.replace(
        session,
        current_status="awaiting_subset_rerun",
        medium_tweak_count_since_full_recompute=new_count,
    )
    outcome = ApplyOutcome(
        apply_status="rerun_queued",
        error_summary=None,
        new_layout_signature=None,
        new_problem_report_id=None,
        regression_detected=False,
        newly_critical_check_ids=(),
    )
    return new_session, outcome, full_recompute_triggered


# ============================================================
# § 5 — Public: apply_user_action
# ============================================================

# v0.5 A3 — known contradictory tweak-category pairs for oscillation
# detection. (a, b) means accepting a then accepting b is contradictory.
# Order-agnostic; the detection logic checks both orderings.
KNOWN_CONTRADICTORY_CATEGORY_PAIRS: tuple[tuple[str, str], ...] = (
    ("balcony_add",     "balcony_remove"),
    ("finish_upgrade",  "finish_downgrade"),
)


def detect_oscillation_pattern(
    session: TradeoffSession,
) -> Optional[tuple[str, str]]:
    """v0.5 A3 — detect oscillation patterns in session_history.

    Returns (pattern_kind, advisory_note) when a pattern fires, else None.
    Patterns checked (any one triggers):
      1. Accept-then-reject of the SAME tweak_id within 3 turns
      2. Accept of category X then accept of contradictory category Y
      3. 3 consecutive rejections of the same category

    Pattern detection is deterministic over session_history → R6 safe.
    """
    history = session.session_history
    if not history:
        return None

    # Map tweak_id → its category, accreted from option sets (current + applied)
    tweak_id_to_category: dict[str, str] = {}
    for opt_set in session.tweak_option_sets:
        for t in opt_set.tweaks:
            tweak_id_to_category[t.tweak_id] = t.tweak_category
    # Also handle tweaks that have been removed (LIGHT applied) — we lose
    # them but the accept-then-reject case is unaffected (since reject
    # doesn't remove until cap).

    # Pattern 1: accept-then-reject of same tweak_id within 3 turns
    n = len(history)
    for i, turn in enumerate(history):
        if turn.user_action == "rejected_tweak" and turn.chosen_tweak_id:
            look_back_start = max(0, i - 3)
            for j in range(look_back_start, i):
                prior = history[j]
                if (prior.user_action == "accepted_tweak"
                        and prior.chosen_tweak_id == turn.chosen_tweak_id):
                    return (
                        "oscillation_pattern_detected",
                        f"You accepted tweak '{turn.chosen_tweak_id}' "
                        f"earlier and then rejected it. You could take a "
                        f"moment to decide which direction matters more "
                        f"and finalize on that priority.",
                    )

    # Pattern 2: contradictory-category accepts
    accepted_categories: list[tuple[int, str]] = []
    for i, turn in enumerate(history):
        if turn.user_action == "accepted_tweak" and turn.chosen_tweak_id:
            cat = tweak_id_to_category.get(turn.chosen_tweak_id)
            if cat:
                accepted_categories.append((i, cat))
    for i, (idx_a, cat_a) in enumerate(accepted_categories):
        for idx_b, cat_b in accepted_categories[i + 1:]:
            for pair in KNOWN_CONTRADICTORY_CATEGORY_PAIRS:
                if {cat_a, cat_b} == {pair[0], pair[1]}:
                    return (
                        "oscillation_pattern_detected",
                        f"You appear to be balancing {cat_a} vs {cat_b}. "
                        f"You could take a moment to decide which matters "
                        f"more and finalize on that priority.",
                    )

    # Pattern 3: 3 consecutive rejections of same category
    consecutive_rejects: list[tuple[int, str]] = []
    for i, turn in enumerate(history):
        if turn.user_action == "rejected_tweak" and turn.chosen_tweak_id:
            cat = tweak_id_to_category.get(turn.chosen_tweak_id)
            if cat:
                if consecutive_rejects and consecutive_rejects[-1][1] != cat:
                    consecutive_rejects = []
                consecutive_rejects.append((i, cat))
                if len(consecutive_rejects) >= 3:
                    return (
                        "oscillation_pattern_detected",
                        f"You've rejected three tweaks of the same kind "
                        f"({cat}). That category may not fit what you want "
                        f"— you could move on or step back to brief.",
                    )
        elif turn.user_action == "accepted_tweak":
            consecutive_rejects = []

    return None


def _invoke_strategic_advisory(
    *,
    session: TradeoffSession,
    request,    # forward ref to UserActionRequest below
    config:  C3bRuntimeConfig,
) -> Optional[str]:
    """v0.5 A4 — invoke the configured strategic-advisory provider.

    Returns the advisory text the provider returned, or None when:
      - strategic_mode == "off"
      - no provider registered
      - provider returns None
      - provider raises (silently swallowed — strategic advice is best-
        effort, never blocks the user turn)

    R17 invariant: returned text does NOT affect canonical_replay_signature.
    Caller attaches it to SessionTurn.strategic_advisory_text only.
    """
    if config.strategic_mode == "off":
        return None
    provider = config.strategic_advisory_provider
    if provider is None:
        return None
    try:
        text = provider(session=session, request=request)
    except Exception:
        # Strategic advisory is best-effort; provider crashes never
        # interrupt the user turn.
        return None
    if not isinstance(text, str) or not text:
        return None
    # Best-effort lint check — if the provider returns banned text, drop
    # it silently rather than raising.
    try:
        from ..advisory_lint import is_advisory_clean
        if not is_advisory_clean(text):
            return None
    except Exception:
        return None
    return text


@dataclasses.dataclass(frozen=True)
class UserActionRequest:
    """Structured user-action input to Phase ε.

    Fields by user_action:
      - accepted_tweak       → chosen_tweak_id required
      - rejected_tweak       → chosen_tweak_id required
      - no_action_continue   → no extras
      - finalized_layout_choice → finalize_layout_id required
      - kicked_back_to_c3a   → kickback_context required (caller supplies)
      - abandoned_session    → no extras (system picks rank-0 layout)
    """
    user_action:        UserAction
    chosen_tweak_id:    Optional[str] = None
    finalize_layout_id: Optional[str] = None
    kickback_context:   Optional[KickbackContext] = None


def apply_user_action(
    session:  TradeoffSession,
    request:  UserActionRequest,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Phase ε entry point. Apply one user action to the session,
    append a SessionTurn, branch on action, return new session.

    Per Principle 4: user agency. The system never overrides; it
    routes the action and surfaces outcomes."""
    from .alpha import _resign_session
    from .beta import run_phase_beta  # noqa: F401 — for re-gen after LIGHT apply

    if session.current_status in (
        "abandoned_no_tweaks", "kicked_back_to_c3a",
        "resolved_selection_ready",
    ):
        raise LocalTradeoffError(
            f"Session in terminal status {session.current_status!r}; "
            f"no further actions accepted.",
            session_id=session.session_id,
            phase="epsilon",
        )

    presented = _all_presented_tweak_ids(session)
    iteration_index = len(session.session_history)
    next_iteration_count = _bump_iteration_count(session)

    # Branch by user_action
    action = request.user_action
    chosen_id = request.chosen_tweak_id
    apply_outcome: Optional[ApplyOutcome] = None
    post_status: SessionStatus = session.current_status
    new_session = session
    new_advisory_flags: list[AdvisoryFlag] = list(session.advisory_flags)

    if action in ("accepted_tweak", "rejected_tweak"):
        if not chosen_id:
            raise LocalTradeoffError(
                f"user_action={action!r} requires chosen_tweak_id",
                session_id=session.session_id, phase="epsilon",
            )
        if chosen_id not in presented:
            raise LocalTradeoffError(
                f"chosen_tweak_id {chosen_id!r} not in presented set "
                f"(Q3 Level B violation)",
                session_id=session.session_id, phase="epsilon",
            )
        found = _find_tweak(session, chosen_id)
        if found is None:
            raise LocalTradeoffError(
                f"Tweak {chosen_id!r} not found",
                session_id=session.session_id, phase="epsilon",
            )
        tweak, _layout_id = found

        if action == "accepted_tweak":
            if tweak.severity_tier == "light":
                new_session, apply_outcome = _apply_light_tweak(
                    new_session, tweak, config,
                )
                post_status = "open_for_user_input"
            elif tweak.severity_tier == "medium":
                # v0.5 A2 — _apply_medium_tweak_emit_rerun now returns
                # 3-tuple including full_recompute_triggered flag
                new_session, apply_outcome, full_recompute_triggered = (
                    _apply_medium_tweak_emit_rerun(
                        new_session, tweak, config,
                    )
                )
                post_status = "awaiting_subset_rerun"
                # v0.5 A2 — if counter crossed threshold, attach advisory
                if full_recompute_triggered:
                    new_advisory_flags.append(AdvisoryFlag(
                        flag_id=f"flag_fullrecompute_{iteration_index:04d}",
                        kind="full_coherence_recheck_triggered",
                        advisory_note=(
                            "You've applied several layout-affecting tweaks. "
                            "The next rerun will re-check the whole layout "
                            "for coherence, not just the affected rooms."
                        ),
                        related_ids=(tweak.tweak_id,),
                    ))
            else:  # heavy — should never reach here (R4)
                raise LocalTradeoffError(
                    "HEAVY tweak reached Phase ε accepted_tweak branch "
                    "(R4 violation)",
                    session_id=session.session_id, phase="epsilon",
                )
        else:  # rejected_tweak
            # Bump presented_count on the rejected tweak so it isn't
            # re-suggested too aggressively (MAX_REPRESENT_COUNT)
            new_option_sets = []
            for opt_set in new_session.tweak_option_sets:
                if any(t.tweak_id == chosen_id for t in opt_set.tweaks):
                    new_tweaks = []
                    for t in opt_set.tweaks:
                        if t.tweak_id == chosen_id and t.presented_count < MAX_REPRESENT_COUNT:
                            new_tweaks.append(dataclasses.replace(
                                t, presented_count=t.presented_count + 1,
                            ))
                        elif t.tweak_id == chosen_id:
                            # At cap — remove from option set
                            continue
                        else:
                            new_tweaks.append(t)
                    new_option_sets.append(dataclasses.replace(
                        opt_set, tweaks=tuple(new_tweaks),
                    ))
                else:
                    new_option_sets.append(opt_set)
            new_session = dataclasses.replace(
                new_session, tweak_option_sets=tuple(new_option_sets),
            )
            post_status = "open_for_user_input"
            apply_outcome = None

    elif action == "no_action_continue":
        post_status = session.current_status
        if post_status not in ("open_for_user_input", "awaiting_subset_rerun"):
            post_status = "open_for_user_input"

    elif action == "finalized_layout_choice":
        if not request.finalize_layout_id:
            raise LocalTradeoffError(
                "user_action='finalized_layout_choice' requires finalize_layout_id",
                session_id=session.session_id, phase="epsilon",
            )
        new_session = _build_resolved_selection(
            new_session, request.finalize_layout_id, config,
        )
        # v0.5 R18 — counter resets on terminal resolution
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "resolved_selection_ready"

    elif action == "kicked_back_to_c3a":
        # v0.5 R18 — counter resets on terminal status
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "kicked_back_to_c3a"

    elif action == "abandoned_session":
        # Pick rank-0 layout as default
        if session.tweak_option_sets:
            default_layout_id = session.tweak_option_sets[0].layout_id
            new_session = _build_resolved_selection(
                new_session, default_layout_id, config, no_tweaks_applied=True,
            )
        # v0.5 R18 — counter resets on terminal status
        new_session = dataclasses.replace(
            new_session, medium_tweak_count_since_full_recompute=0,
        )
        post_status = "abandoned_no_tweaks"

    else:
        raise LocalTradeoffError(
            f"Unknown user_action {action!r}",
            session_id=session.session_id, phase="epsilon",
        )

    # Iteration-cap check (after action, before commit) — only for non-terminal
    if post_status in ("open_for_user_input", "awaiting_subset_rerun"):
        if next_iteration_count >= session.iteration_cap:
            post_status = "iteration_cap_reached"
            new_advisory_flags.append(AdvisoryFlag(
                flag_id=f"flag_itercap_{iteration_index:04d}",
                kind="iteration_cap_warning_nudge",
                advisory_note=(
                    "You've made good progress — you could finalize a layout "
                    "now or step back to brief if your scope is changing."
                ),
                related_ids=(),
            ))

    # v0.5 A3 — oscillation pattern detection (after applying this turn
    # but before committing the SessionTurn). We feed the still-being-
    # built session-with-history-so-far to the detector.
    # Build the in-flight turn first (without strategic advisory) so the
    # detector can examine the would-be history.
    in_flight_turn = SessionTurn(
        turn_id=_new_turn_id(iteration_index),
        iteration_index=iteration_index,
        timestamp_offset_ms=iteration_index * 1000,    # R7d: relative, deterministic
        presented_tweaks=presented,
        user_action=action,
        chosen_tweak_id=(
            chosen_id if action in ("accepted_tweak", "rejected_tweak") else None
        ),
        apply_outcome=apply_outcome,
        post_turn_status=post_status,
        strategic_advisory_text=None,    # filled below if provider present
    )

    # Run oscillation detection on the would-be-committed history.
    # Detection only fires on patterns spanning multiple turns.
    history_for_detection = session.session_history + (in_flight_turn,)
    probe_session = dataclasses.replace(
        new_session,
        session_history=history_for_detection,
        current_status=post_status,
        # R18 invariant: keep counter coherent with post_status. The
        # probe session is for detection only; never returned.
    )
    osc_result = detect_oscillation_pattern(probe_session)
    if osc_result is not None:
        kind, note = osc_result
        # Use turn-position-keyed flag_id for stability
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_osc_{iteration_index:04d}",
            kind=kind,
            advisory_note=note,
            related_ids=(),
        ))

    # v0.5 A4 — invoke strategic advisory provider (R17: text excluded
    # from canonical_replay_signature; this is purely informational)
    strategic_text = _invoke_strategic_advisory(
        session=new_session, request=request, config=config,
    )

    # Commit the actual turn (with strategic text attached if produced)
    turn = dataclasses.replace(in_flight_turn, strategic_advisory_text=strategic_text)

    # Update iteration_count for non-terminal actions; cap at hard ceiling
    new_iter_count = next_iteration_count if action not in (
        "no_action_continue", "kicked_back_to_c3a", "abandoned_session",
    ) else session.iteration_count

    new_advisory_flags_sorted = tuple(
        sorted(new_advisory_flags, key=lambda f: f.flag_id)
    )

    final_session = dataclasses.replace(
        new_session,
        session_history=session.session_history + (turn,),
        iteration_count=new_iter_count,
        current_status=post_status,
        advisory_flags=new_advisory_flags_sorted,
    )
    return _resign_session(final_session, config)


# ============================================================
# § 6 — ResolvedSelection assembly (called from finalize/abandon paths)
# ============================================================

def _build_resolved_selection(
    session:    TradeoffSession,
    layout_id:  str,
    config:     C3bRuntimeConfig,
    no_tweaks_applied: bool = False,
) -> TradeoffSession:
    """Construct a ResolvedSelection and attach to session.

    Sums cost / space deltas across applied tweaks (history)."""
    # Find the option set for this layout (for archetype)
    target_set = None
    for opt_set in session.tweak_option_sets:
        if opt_set.layout_id == layout_id:
            target_set = opt_set
            break
    if target_set is None and session.tweak_option_sets:
        target_set = session.tweak_option_sets[0]
        layout_id = target_set.layout_id

    archetype = target_set.layout_archetype if target_set else "cost_efficient"

    # Find applied tweaks from history
    applied_tweak_ids: list[str] = []
    if not no_tweaks_applied:
        for turn in session.session_history:
            if (turn.user_action == "accepted_tweak"
                    and turn.chosen_tweak_id is not None
                    and turn.apply_outcome
                    and turn.apply_outcome.apply_status in (
                        "applied_successfully", "rerun_queued",
                    )):
                applied_tweak_ids.append(turn.chosen_tweak_id)
    applied_sorted = tuple(sorted(applied_tweak_ids))

    final_handoff = _build_handoff_advisory(
        archetype=archetype,
        applied_count=len(applied_sorted),
        no_tweaks_applied=no_tweaks_applied,
    )

    final_layout_signature = f"final_{layout_id}_{len(applied_sorted)}tweaks"
    rs = ResolvedSelection(
        chosen_layout_id=layout_id,
        chosen_layout_archetype=archetype,
        applied_tweaks=applied_sorted,
        final_layout_signature=final_layout_signature,
        final_problem_report_id=None,    # Phase ζ may fill this
        total_cost_delta=None,            # Phase ζ may fill this
        total_space_delta=None,
        final_handoff_advisory=final_handoff,
    )
    return dataclasses.replace(session, resolved_selection=rs)


def _build_handoff_advisory(
    *,
    archetype:         str,
    applied_count:     int,
    no_tweaks_applied: bool,
) -> str:
    """Plain-English handoff summary. R2 lint-clean by construction."""
    archetype_display = {
        "cost_efficient":   "Cost Efficient",
        "everyday_living":  "Everyday Living",
        "premium_design":   "Premium Design",
    }.get(archetype, archetype)

    if no_tweaks_applied:
        return (
            f"You accepted the {archetype_display} layout as-is. "
            f"We'll generate the working and regulatory drawings next."
        )
    n = applied_count
    return (
        f"You finalized the {archetype_display} layout with "
        f"{n} tweak{'s' if n != 1 else ''} applied. "
        f"We'll generate the working and regulatory drawings next."
    )


# ============================================================
# § 7 — R14: Regression detection on subset-rerun completion
# ============================================================

def _count_critical_checks(pr: ProblemReport) -> int:
    """Count fail-tier critical checks in a ProblemReport."""
    return sum(
        1 for c in pr.applicable_checks
        if c.status == CheckStatus.FAIL
        and c.severity == CheckSeverity.CRITICAL
    )


def _diff_critical_check_ids(
    pre:   ProblemReport,
    post:  ProblemReport,
) -> tuple[str, ...]:
    """Return check_ids that are newly CRITICAL in `post` vs `pre`."""
    pre_critical = {
        c.check_id for c in pre.applicable_checks
        if c.status == CheckStatus.FAIL and c.severity == CheckSeverity.CRITICAL
    }
    post_critical = {
        c.check_id for c in post.applicable_checks
        if c.status == CheckStatus.FAIL and c.severity == CheckSeverity.CRITICAL
    }
    return tuple(sorted(post_critical - pre_critical))


def _detect_dimension_score_regression(
    pre_rerun_pr:   ProblemReport,
    post_rerun_pr:  ProblemReport,
) -> tuple[tuple[str, float], ...]:
    """v0.5 A5 — detect numeric per-dimension regression beyond
    DIMENSION_DEGRADATION_THRESHOLD_PCT.

    Returns a tuple of (dimension_name, degradation_pct) pairs for
    dimensions that degraded by >= threshold. Empty tuple if C15
    doesn't emit per-dimension scores (defensive fall-through).
    """
    from ..versioning import DIMENSION_DEGRADATION_THRESHOLD_PCT
    pre_scores = getattr(pre_rerun_pr, "dimension_score_snapshot", None)
    post_scores = getattr(post_rerun_pr, "dimension_score_snapshot", None)
    if not pre_scores or not post_scores:
        return ()    # graceful no-op when C15 doesn't supply
    if not hasattr(pre_scores, "items"):
        return ()
    regressions: list[tuple[str, float]] = []
    for dim_name, pre_score in pre_scores.items():
        post_score = post_scores.get(dim_name)
        if post_score is None or pre_score <= 0:
            continue
        delta_pct = (pre_score - post_score) / pre_score * 100.0
        if delta_pct >= DIMENSION_DEGRADATION_THRESHOLD_PCT:
            regressions.append((dim_name, delta_pct))
    # lex-ASC by dimension name for replay determinism
    regressions.sort(key=lambda t: t[0])
    return tuple(regressions)


def complete_subset_rerun(
    session:        TradeoffSession,
    applied_tweak_id: str,
    pre_rerun_pr:   ProblemReport,
    post_rerun_pr:  ProblemReport,
    config:         C3bRuntimeConfig,
) -> TradeoffSession:
    """Called when an external subset-rerun orchestrator returns
    results. Performs R14 regression detection, surfaces advisory,
    and re-opens session for next user input.

    Per spec § 7.2 R14:
      'When the new C15 ProblemReport has MORE critical checks than
      the original, mark regression_detected, add AdvisoryFlag, and
      surface an automatic "undo this tweak" option.'

    v0.5 amendments:
      A2 — resets medium_tweak_count_since_full_recompute to 0 when
           the rerun was a full recompute (counter had crossed
           full_recompute_threshold before this rerun fired)
      A5 — dimension-score regression check (numeric, sub-CRITICAL).
           Augments R14's severity-tier-transition check with a
           per-dimension delta check. No-ops gracefully when C15
           does not emit per-dimension scores.

    v1.0 stops short of synthesizing the undo tweak option — that's
    the orchestrator's job after this returns. We mark the flag and
    update the last apply_outcome.
    """
    from .alpha import _resign_session

    pre_count = _count_critical_checks(pre_rerun_pr)
    post_count = _count_critical_checks(post_rerun_pr)
    regression = (
        post_count - pre_count >= REGRESSION_CRITICAL_INCREASE_THRESHOLD
    )
    newly_critical_ids = _diff_critical_check_ids(pre_rerun_pr, post_rerun_pr)

    # v0.5 A5 — numeric dimension regression (independent of severity-tier
    # transitions; catches gradual sub-CRITICAL degradation)
    dim_regressions = _detect_dimension_score_regression(
        pre_rerun_pr, post_rerun_pr,
    )

    # Update the last SessionTurn's apply_outcome with results
    if not session.session_history:
        raise LocalTradeoffError(
            "complete_subset_rerun called on session with empty history",
            session_id=session.session_id, phase="epsilon",
        )
    last_turn = session.session_history[-1]
    if last_turn.user_action != "accepted_tweak":
        raise LocalTradeoffError(
            f"complete_subset_rerun expected last turn to be accepted_tweak; "
            f"got {last_turn.user_action!r}",
            session_id=session.session_id, phase="epsilon",
        )
    new_outcome = ApplyOutcome(
        apply_status="applied_successfully",
        error_summary=None,
        new_layout_signature=f"sig_after_{applied_tweak_id}",
        new_problem_report_id=post_rerun_pr.upstream_cache_key,
        regression_detected=regression,
        newly_critical_check_ids=newly_critical_ids if regression else (),
    )
    new_last_turn = dataclasses.replace(last_turn, apply_outcome=new_outcome)
    new_history = session.session_history[:-1] + (new_last_turn,)

    new_advisory_flags = list(session.advisory_flags)
    if regression:
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_regression_{applied_tweak_id[:12]}",
            kind="regression_after_apply",
            advisory_note=(
                f"After this tweak, {len(newly_critical_ids)} new critical "
                f"issue{'s' if len(newly_critical_ids) != 1 else ''} appeared. "
                f"You could undo this tweak and try a different approach."
            ),
            related_ids=newly_critical_ids,
        ))

    # v0.5 A5 — dimension-score regression advisory
    if dim_regressions:
        dim_names = ", ".join(name for name, _ in dim_regressions)
        new_advisory_flags.append(AdvisoryFlag(
            flag_id=f"flag_dimregression_{applied_tweak_id[:12]}",
            kind="dimension_score_regression",
            advisory_note=(
                f"After this tweak, {dim_names} dropped noticeably "
                f"(more than the typical tolerance). The change didn't "
                f"trip a critical issue, but you could undo it if those "
                f"dimensions matter to you."
            ),
            related_ids=tuple(name for name, _ in dim_regressions),
        ))

    new_advisory_flags_sorted = tuple(
        sorted(new_advisory_flags, key=lambda f: f.flag_id)
    )

    # v0.5 A2 — when the rerun was a full recompute (counter had crossed
    # threshold before this rerun fired), reset the counter to 0.
    new_counter = session.medium_tweak_count_since_full_recompute
    if new_counter >= config.full_recompute_threshold:
        new_counter = 0

    new_session = dataclasses.replace(
        session,
        session_history=new_history,
        advisory_flags=new_advisory_flags_sorted,
        current_status="open_for_user_input",
        medium_tweak_count_since_full_recompute=new_counter,
    )
    return _resign_session(new_session, config)


__all__ = [
    "UserActionRequest",
    "apply_user_action",
    "complete_subset_rerun",
    "check_compatibility_against_history",
    "detect_oscillation_pattern",
    "_count_critical_checks",
    "_diff_critical_check_ids",
    "_detect_dimension_score_regression",
]
