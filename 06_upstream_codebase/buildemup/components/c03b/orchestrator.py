"""
C3b — Orchestrator (top-level entry points)
=============================================

The orchestrator wires Phases α → β → γ → δ at session start, and
Phase ε at each user action, with Phase ζ at resolution time.
Optionally persists each transition via C3bSessionStorage.

Spec § 3 — orchestration flow:
  start_session:
    Phase α → Phase β → Phase γ → Phase δ
  apply_user_action_orchestrated:
    Phase ε  (then Phase ζ if action resolved/abandoned the session)
  complete_subset_rerun_orchestrated:
    R14 regression detection in Phase ε.complete_subset_rerun
  finalize_session:
    Phase ζ explicit

Rule 11 self-analysis:
  1. The orchestrator is the ONLY surface that calls phases by name.
     User code interacts via start_session / apply_user_action /
     complete_subset_rerun / finalize_session. Phase internals are
     not part of the public C3b API.
  2. Persistence is opt-in (storage parameter). When provided, every
     successful state transition writes to SQLite. When None, the
     orchestrator runs purely in-memory.
  3. STRICT-mode errors propagate to the caller. WARN-mode errors
     are absorbed inside the phases; the orchestrator does NOT need
     to inspect them (Phase γ already dropped offending tweaks).
"""
from __future__ import annotations

from typing import Optional

from buildemup.components.c15.schema import ProblemReport

from .config import C3bRuntimeConfig, DEFAULT_CONFIG
from .contracts import C3bInputBundle
from .phases.alpha import run_phase_alpha
from .phases.beta import run_phase_beta
from .phases.delta import run_phase_delta
from .phases.epsilon import (
    UserActionRequest,
    apply_user_action,
    complete_subset_rerun,
)
from .phases.gamma import run_phase_gamma
from .phases.zeta import run_phase_zeta
from .schema import TradeoffSession
from .session_storage import C3bSessionStorage


def start_session(
    bundle:   C3bInputBundle,
    config:   C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:  Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Start a new C3b tradeoff session.

    Runs Phase α (canonicalization + applicability) → Phase β (tweak
    generation) → Phase γ (impact verification) → Phase δ (presentation
    + signing). If the applicability check fails in Phase α, returns
    a terminal session immediately (status='abandoned_no_tweaks').

    If `storage` is provided, persists the session after each phase
    transition."""
    session = run_phase_alpha(bundle, config)

    # If Phase α produced a terminal session, skip downstream phases
    if session.current_status == "abandoned_no_tweaks":
        if storage is not None:
            storage.save(session)
        return session

    session = run_phase_beta(session, bundle, config)
    session = run_phase_gamma(session, config)
    session = run_phase_delta(session, config)

    if storage is not None:
        storage.save(session)
    return session


def apply_user_action_orchestrated(
    session:  TradeoffSession,
    request:  UserActionRequest,
    config:   C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:  Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Apply one user action via Phase ε and persist."""
    new_session = apply_user_action(session, request, config)
    if storage is not None:
        storage.save(new_session)
    return new_session


def complete_subset_rerun_orchestrated(
    session:           TradeoffSession,
    applied_tweak_id:  str,
    pre_rerun_pr:      ProblemReport,
    post_rerun_pr:     ProblemReport,
    config:            C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    storage:           Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Complete a subset rerun with R14 regression detection + persist."""
    new_session = complete_subset_rerun(
        session, applied_tweak_id, pre_rerun_pr, post_rerun_pr, config,
    )
    if storage is not None:
        storage.save(new_session)
    return new_session


def finalize_session(
    session:           TradeoffSession,
    config:            C3bRuntimeConfig = DEFAULT_CONFIG,
    *,
    base_carpet_sqft:  float = 1000.0,
    storage:           Optional[C3bSessionStorage] = None,
) -> TradeoffSession:
    """Run Phase ζ explicitly on a session whose user action already
    set resolved_selection (typically 'finalized_layout_choice' or
    'abandoned_session'). Sums cost / space deltas + re-signs."""
    new_session = run_phase_zeta(session, config, base_carpet_sqft)
    if storage is not None:
        storage.save(new_session)
    return new_session


__all__ = [
    "start_session",
    "apply_user_action_orchestrated",
    "complete_subset_rerun_orchestrated",
    "finalize_session",
    "UserActionRequest",
]
