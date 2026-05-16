"""
C3b — Post-Layout Trade-off Negotiation
========================================

Spec: v0.4.LOCKED (S50). Implementation: S52 full build.

Package surface:
    versioning      — constants, expected upstream versions, ceilings
    config          — runtime C3bRuntimeConfig
    errors          — 2-tier (LocalTradeoffError / PerTweakError) hierarchy
    advisory_lint   — R2 banned-phrase enforcement
    contracts       — upstream input types (re-exports + C3bInputBundle)
    schema          — all output dataclasses (TradeoffSession etc.)
    cache_keys      — R6/R7/R8 canonical signatures
    phases          — Phase α / β / γ / δ / ε / ζ pipeline
    session_storage — SQLite WAL persistence
    orchestrator    — top-level entry points
"""
from .versioning import (  # noqa: F401
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    COMPONENT_NAME,
)
from .config import C3bRuntimeConfig, DEFAULT_CONFIG  # noqa: F401
from .contracts import C3bInputBundle  # noqa: F401
from .orchestrator import (  # noqa: F401
    UserActionRequest,
    apply_user_action_orchestrated,
    complete_subset_rerun_orchestrated,
    finalize_session,
    start_session,
)
from .session_storage import C3bSessionStorage  # noqa: F401

__all__ = [
    "C3B_VERSION",
    "C3B_SESSION_SCHEMA_VERSION",
    "COMPONENT_NAME",
    "C3bRuntimeConfig",
    "DEFAULT_CONFIG",
    "C3bInputBundle",
    "UserActionRequest",
    "C3bSessionStorage",
    "start_session",
    "apply_user_action_orchestrated",
    "complete_subset_rerun_orchestrated",
    "finalize_session",
]
