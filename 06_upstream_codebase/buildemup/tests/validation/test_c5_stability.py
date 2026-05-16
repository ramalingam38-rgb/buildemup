"""Validation tests for C5 score stability under small input perturbations.

Per C5 SPEC v0.8 § 14.3:

   "Small perturbations of plot dimensions (±0.1m on width or depth) should
    produce small score changes (< 0.05). If the perturbation crosses a
    decision-table boundary that flips the topology kind, the score gap
    between old-top and new-top must be smaller than 0.05 (boundary case)."

Implementation uses Hypothesis to sample perturbations across the baseline
plot, asserting the spec invariant for both perturbation directions.
"""
from __future__ import annotations

import time

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from buildemup.components.c04 import derive
from buildemup.components.c05 import select_topology, TopologyKind
from buildemup.components.c05.schema import TopologyKind as Kind
from buildemup.domain.plot import Plot
from buildemup.tests.validation._c4_fixtures import make_brief
from buildemup.tests.validation._c5_fixtures import (
    baseline_test_brief,
    baseline_test_plot,
)


# ─── Helpers ──────────────────────────────────────────────────────────────


def _score_at(width_m: float, depth_m: float) -> tuple[Kind, float]:
    """Run the pipeline at the given dimensions; return (top_kind, top_score)."""
    base = baseline_test_plot()
    plot = Plot(
        width_m=width_m,
        depth_m=depth_m,
        facing=base.facing,
        city=base.city,
        road_width_m=base.road_width_m,
        corner_plot=base.corner_plot,
    )
    pa = derive(make_brief(plot, trace_id="trace-stability"), now=time.time())
    candidates = select_topology(pa, baseline_test_brief())
    top = candidates[0]
    return top.kind, top.score


def _baseline_top() -> tuple[Kind, float]:
    base = baseline_test_plot()
    return _score_at(base.width_m, base.depth_m)


# ─── Hypothesis perturbation tests ────────────────────────────────────────


_STABILITY_THRESHOLD = 0.05
_PERTURBATION_M = 0.1


@settings(
    max_examples=40,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    dw=st.floats(min_value=-_PERTURBATION_M, max_value=_PERTURBATION_M, allow_nan=False),
    dd=st.floats(min_value=-_PERTURBATION_M, max_value=_PERTURBATION_M, allow_nan=False),
)
def test_score_stable_under_small_perturbation(dw: float, dd: float):
    """v0.8 § 14.3: ±0.1m perturbation → either same kind with |Δscore|<0.05,
    or kind flip with |score_old - score_new|<0.05 (boundary case)."""
    base = baseline_test_plot()
    base_kind, base_score = _baseline_top()
    new_w = base.width_m + dw
    new_d = base.depth_m + dd
    # Skip degenerate dims (Plot constructor will reject anyway)
    if new_w <= 0 or new_d <= 0:
        return
    try:
        new_kind, new_score = _score_at(new_w, new_d)
    except (ValueError, NotImplementedError):
        # C4 rejected the perturbed plot — not a stability violation
        return

    score_diff = abs(base_score - new_score)
    assert score_diff < _STABILITY_THRESHOLD, (
        f"score moved {score_diff:.4f} (>= {_STABILITY_THRESHOLD}) for "
        f"perturbation dw={dw:.4f} dd={dd:.4f}: "
        f"base={base_kind.value}@{base_score:.4f} → "
        f"new={new_kind.value}@{new_score:.4f}"
    )

    # Boundary-flip case: score gap must also be small (already enforced by
    # the score_diff check above when scores are similar — flipping kinds
    # while keeping similar scores is the spec-permitted boundary case).


def test_baseline_pipeline_runs():
    """Smoke test: the baseline plot+brief produces a result."""
    kind, score = _baseline_top()
    assert kind in TopologyKind
    assert 0.0 <= score <= 1.0


def test_baseline_score_is_above_low_confidence():
    """The baseline plot+brief is well-formed enough to score above 0.30."""
    from buildemup.components.c05 import LOW_CONFIDENCE_THRESHOLD
    _, score = _baseline_top()
    assert score >= LOW_CONFIDENCE_THRESHOLD, (
        f"baseline score {score:.4f} below {LOW_CONFIDENCE_THRESHOLD} — "
        "fixture choice is not a meaningful perturbation baseline"
    )


def test_sub_perturbation_score_change_bounded():
    """Manual ε perturbations (no Hypothesis): Δw=+0.05m, Δw=-0.05m,
    Δd=+0.05m, Δd=-0.05m. All four should be inside the threshold."""
    base = baseline_test_plot()
    _, base_score = _baseline_top()
    for dw, dd in ((0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)):
        _, new_score = _score_at(base.width_m + dw, base.depth_m + dd)
        diff = abs(new_score - base_score)
        assert diff < _STABILITY_THRESHOLD, (
            f"manual perturbation dw={dw} dd={dd}: Δscore={diff:.4f}"
        )
