"""
C3b — Phase γ — Cost + space + comfort impact computation
============================================================

Spec § 3 Phase γ:
  INPUT: tweaks from Phase β, RateProvider, layout geometry
  PROCESSING (per tweak):
    1. Cost impact via C7 cost estimator + RateProvider
    2. Space impact via ApplySpecification geometry payload
    3. Comfort impact via ProblemReport check mapping
    4. Recommendation flag classification
  OUTPUT: TweakOptionSets with full impact data

For v1.0 we INLINE the impact computation into Phase β (since each
TweakOption needs its cost/space/comfort impacts at construction
time per R3/R4 schema enforcement). Phase γ here is a thin wrapper
that VALIDATES every emitted tweak has well-formed impacts. v1.x will
swap heuristic ranges for live RateProvider calibration (see
B-C3B-COST-CALIBRATION implicit in v1.0 LOCK-mandatory backlog).

Rule 11 self-analysis:
  1. Why is Phase γ thin in v1.0? Because the dataclass invariants
     enforce well-formed impacts at construction time — Phase β can't
     emit a tweak with malformed impacts without raising. So Phase γ's
     job is reduced to: (a) verify integrity, (b) compute summary
     statistics (range / mid / derivation are already populated).
  2. The summary computation (total session cost delta when multiple
     tweaks accepted) happens in Phase ζ, not γ. γ is per-tweak; ζ is
     per-session.
  3. This is a real Phase, not a no-op — the verification step catches
     drift if heuristic tables and dataclass schema diverge.
"""
from __future__ import annotations

from typing import Optional

from ..config import C3bRuntimeConfig
from ..errors import ImpactComputationError, PerTweakError
from ..schema import TradeoffSession, TweakOption


def verify_tweak_impacts(tweak: TweakOption) -> Optional[ImpactComputationError]:
    """Verify a tweak's impacts are well-formed. Returns None on success
    or an ImpactComputationError describing the problem."""
    # cost_impact non-None (dataclass enforces this)
    if tweak.cost_impact is None:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} cost_impact missing",
            impact_dim="cost",
            tweak_id=tweak.tweak_id,
        )
    if not tweak.cost_impact.derivation:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} cost_impact has empty derivation",
            impact_dim="cost",
            tweak_id=tweak.tweak_id,
        )
    # space_impact non-None
    if tweak.space_impact is None:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} space_impact missing",
            impact_dim="space",
            tweak_id=tweak.tweak_id,
        )
    # comfort_impact non-None and has dimensions
    if not tweak.comfort_impact.dimensions_affected:
        return ImpactComputationError(
            f"Tweak {tweak.tweak_id!r} comfort_impact has no dimensions",
            impact_dim="comfort",
            tweak_id=tweak.tweak_id,
        )
    return None


def run_phase_gamma(
    session:  TradeoffSession,
    config:   C3bRuntimeConfig,
) -> TradeoffSession:
    """Verify every tweak in the session has well-formed impacts.

    Raises ImpactComputationError in STRICT mode; collects + drops the
    offending tweaks in WARN mode. Returns the (possibly modified) session."""
    errors_collected: list[PerTweakError] = []
    new_option_sets = []
    for opt_set in session.tweak_option_sets:
        verified_tweaks = []
        for tweak in opt_set.tweaks:
            err = verify_tweak_impacts(tweak)
            if err is None:
                verified_tweaks.append(tweak)
                continue
            if config.strict_mode == "strict":
                raise err
            errors_collected.append(err)
        # Rebuild option set with verified-only tweaks
        if len(verified_tweaks) == len(opt_set.tweaks):
            new_option_sets.append(opt_set)
        else:
            import dataclasses
            new_option_sets.append(dataclasses.replace(
                opt_set,
                tweaks=tuple(verified_tweaks),
            ))
    if not errors_collected:
        return session

    from .alpha import _resign_session
    import dataclasses
    return _resign_session(
        dataclasses.replace(session, tweak_option_sets=tuple(new_option_sets)),
        config,
    )


__all__ = ["verify_tweak_impacts", "run_phase_gamma"]
