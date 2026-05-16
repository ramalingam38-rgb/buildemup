"""
C3b — Post-Layout Trade-off Negotiation — runtime configuration
================================================================

Spec: C3b v0.5.LOCKED. Build session: S52.

The C3bRuntimeConfig threads strict_mode + jurisdiction context + any
per-session tuning knobs through the phase pipeline.

Per spec § 4 error tiers:
  STRICT mode → PerTweakError raises immediately
  WARN   mode → PerTweakError collects to a failure list, processing
                continues. LocalTradeoffError ALWAYS halts in either
                mode.

v0.5 additions:
  A2 — full_recompute_threshold (periodic coherence recheck)
  A4 — strategic_mode (advisory hook; R17-protected)
  A8 — iteration_cap default lowered 5 → 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, Literal, Optional

from .versioning import (
    FULL_RECOMPUTE_THRESHOLD_DEFAULT,
    ITERATION_CAP_DEFAULT,
    ITERATION_CAP_HARD_CEILING,
)


StrictMode = Literal["strict", "warn"]

# v0.5 A4 — strategic-mode literal. "off" means no strategic advisory text
# is populated. "advisory_only" means a registered provider may populate
# SessionTurn.strategic_advisory_text. R17 invariant: advisory text MUST
# NOT affect canonical_replay_signature regardless of mode.
StrategicMode = Literal["off", "advisory_only"]

# Provider receives kwargs (session, request) and returns advisory text
# or None. Implementations must be READ-ONLY against session state.
StrategicAdvisoryProvider = Callable[..., Optional[str]]


@dataclass(frozen=True)
class C3bRuntimeConfig:
    """Runtime configuration for a C3b session.

    Frozen so it participates cleanly in R6 byte-equal replay
    signature hashing (strict_mode is part of canonical_replay_signature
    inputs).

    R17: strategic_advisory_text content is excluded from
    canonical_replay_signature. Different providers can populate
    different text without changing the signature.
    """

    strict_mode: StrictMode = "strict"
    iteration_cap: int = ITERATION_CAP_DEFAULT
    enable_q3_level_b_logging: bool = True
    full_recompute_threshold: int = FULL_RECOMPUTE_THRESHOLD_DEFAULT
    strategic_mode: StrategicMode = "off"
    strategic_advisory_provider: Optional[StrategicAdvisoryProvider] = None

    def __post_init__(self) -> None:
        if self.strict_mode not in ("strict", "warn"):
            raise ValueError(
                f"C3bRuntimeConfig.strict_mode must be 'strict' or 'warn'; "
                f"got {self.strict_mode!r}"
            )
        if not (1 <= self.iteration_cap <= ITERATION_CAP_HARD_CEILING):
            raise ValueError(
                f"C3bRuntimeConfig.iteration_cap must be in [1, "
                f"{ITERATION_CAP_HARD_CEILING}]; got {self.iteration_cap}"
            )
        if not (1 <= self.full_recompute_threshold <= self.iteration_cap):
            raise ValueError(
                f"C3bRuntimeConfig.full_recompute_threshold must be in "
                f"[1, iteration_cap={self.iteration_cap}]; "
                f"got {self.full_recompute_threshold}"
            )
        if self.strategic_mode not in ("off", "advisory_only"):
            raise ValueError(
                f"C3bRuntimeConfig.strategic_mode must be 'off' or "
                f"'advisory_only'; got {self.strategic_mode!r}"
            )


DEFAULT_CONFIG: Final[C3bRuntimeConfig] = C3bRuntimeConfig()


__all__ = [
    "C3bRuntimeConfig", "StrictMode", "StrategicMode",
    "StrategicAdvisoryProvider", "DEFAULT_CONFIG",
]
