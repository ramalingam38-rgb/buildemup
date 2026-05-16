"""
BuildemUp — Component 11b — evaluator protocol + stub evaluator
================================================================

Per SPEC v1.1 LOCKED:
- § 0.5 NSGA-II 3-objective Pareto pathology (D-NSGA-1):
  ``StubEvaluatorConfig.objectives: Literal[2, 3] = 3`` (default 3
  carries v0.3 LOCKED behaviour; 2-objective mode stays inside NSGA-II's
  proven regime per Doerr et al. 2022).
- § 0.6 evaluator failure isolation (D-EV-1, D-EV-2): per-candidate
  ``EvaluatorContractError`` is skip-and-continue up to Inv 28 cap;
  non-contract exception → systemic wrap.

EvaluatorProtocol is a structural-typing contract — anything with a
matching ``evaluate(candidate) -> ObjectiveVector`` and a
``signature() -> str`` method satisfies it.

StubEvaluator's three objectives at v1 (all "lower is better"):

1. ``synthetic_compactness`` — sum of (perimeter / sqrt(area)) across
   rooms. Pure square rooms minimize this (≈4); long thin rooms blow
   it up.
2. ``synthetic_aspect_variance`` — variance of per-room aspect ratios
   ``max(w,d)/min(w,d)``. Lower = more uniform proportions across the
   plan.
3. ``synthetic_envelope_efficiency`` — proxy: ``-total_room_area``
   (negated so "lower is better" still favours bigger usable rooms).

These three signals are correlated by construction, which is exactly
what makes them acceptable for NSGA-II 3-obj at v1 per § 0.5
rationale: practical Pareto front is well-approximated even where the
theoretical front is unreachable.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from buildemup.components.c11b.errors import EvaluatorContractError
from buildemup.components.c11b.schema import ObjectiveVector, RefinedCandidate


# =============================================================================
# § 0.4 — EvaluatorProtocol (carried v1.0)
# =============================================================================


@runtime_checkable
class EvaluatorProtocol(Protocol):
    """Structural protocol for any evaluator C11b's NSGA-II can call.

    The evaluator is PURE: same ``RefinedCandidate`` in, same
    ``ObjectiveVector`` out across calls (purity verified by
    ``EvaluatorPurityContractError`` checks at the orchestration
    layer).

    ``signature()`` returns a stable string identifying the evaluator's
    behaviour — captured into ``LocalRefinementProvenance`` for replay
    discipline. Two evaluators with the same signature are required to
    produce identical outputs for identical inputs."""

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector: ...
    def signature(self) -> str: ...


# =============================================================================
# § 0.5 — StubEvaluatorConfig (NEW v0.4, REVISED v0.5 W4-1 default = 3)
# =============================================================================


@dataclass(frozen=True)
class StubEvaluatorConfig:
    """Config knob for the stub-only objective count.

    Default is 3 (v0.3 carried behaviour; v0.5 W4-1 corrected stale
    "default 2" drift in v0.4 draft).

    Setting to 2 stays inside NSGA-II's mathematically proven regime
    (no 3-objective Pareto-front pathology per Doerr et al. 2022),
    useful when isolating algorithm correctness from objective-count
    effects.
    """
    objectives: Literal[2, 3] = 3


# =============================================================================
# § 0.5 — StubEvaluator (3 / 2 synthetic objectives)
# =============================================================================


def _compute_three_stub_objectives(
    candidate: RefinedCandidate,
) -> tuple[float, float, float]:
    """Compute (compactness, aspect_variance, neg_total_area) for the
    candidate. All three are "lower is better" by NSGA-II convention.
    """
    dims = candidate.refined_parameters.room_dimensions
    if not dims:
        # Degenerate input — return zeros. Should not happen via the
        # normal init path; tests may exercise it.
        return (0.0, 0.0, 0.0)

    # 1. Compactness: sum over rooms of perimeter / sqrt(area).
    #    Square room → 4 / sqrt(1) = 4 per unit-area; deviation grows
    #    with aspect mismatch.
    compactness = 0.0
    aspects: list[float] = []
    total_area = 0.0
    for rd in dims:
        w, d = rd.width_m, rd.depth_m
        area = w * d
        perim = 2.0 * (w + d)
        compactness += perim / math.sqrt(area)
        aspects.append(max(w, d) / min(w, d))
        total_area += area

    # 2. Aspect variance (sample variance; 0 if n<=1).
    if len(aspects) >= 2:
        mean_a = sum(aspects) / len(aspects)
        aspect_variance = sum((a - mean_a) ** 2 for a in aspects) / len(aspects)
    else:
        aspect_variance = 0.0

    # 3. Envelope efficiency proxy: -total_area (more area = better,
    #    so negate so "lower is better" still ranks correctly).
    neg_total_area = -total_area

    return (compactness, aspect_variance, neg_total_area)


class StubEvaluator:
    """v0.4 (W4-1 corrected to default 3): objectives count configurable.

    Returns 3 objectives by default (v0.3 LOCKED behaviour preserved);
    set ``StubEvaluatorConfig(objectives=2)`` to use 2-objective mode
    (drops the aspect-variance middle term to stay inside NSGA-II's
    proven regime).
    """

    def __init__(self, config: StubEvaluatorConfig | None = None) -> None:
        self._config = config or StubEvaluatorConfig()

    def evaluate(self, candidate: RefinedCandidate) -> ObjectiveVector:
        compactness, variance, neg_area = _compute_three_stub_objectives(candidate)
        if self._config.objectives == 2:
            return ObjectiveVector(
                values=(
                    ("synthetic_compactness", round(compactness, 6)),
                    ("synthetic_envelope_efficiency", round(neg_area, 6)),
                ),
                constraint_violations=0.0,
            )
        # Default: 3-objective mode (v0.3 carried).
        return ObjectiveVector(
            values=(
                ("synthetic_compactness", round(compactness, 6)),
                ("synthetic_aspect_variance", round(variance, 6)),
                ("synthetic_envelope_efficiency", round(neg_area, 6)),
            ),
            constraint_violations=0.0,
        )

    def signature(self) -> str:
        """Stable identifier capturing the evaluator's configuration.
        Two stub evaluators with the same objective count have the
        same signature."""
        payload = f"StubEvaluator:objectives={self._config.objectives}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "EvaluatorProtocol",
    "StubEvaluatorConfig",
    "StubEvaluator",
    "_compute_three_stub_objectives",
    "EvaluatorContractError",  # re-export for convenience
]
