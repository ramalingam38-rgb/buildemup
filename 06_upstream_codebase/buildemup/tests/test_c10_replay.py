"""
BuildemUp† — Component 10 — replay determinism + W8 integration tests.

Per C10 SPEC v1.0 LOCKED:
  - Replay snapshots must be byte-identical for the same inputs.
  - Q42 horizontal-first bend convention is order-stable.

Per C7 amendment v0.8 LOCKED W8: this is the deferred *integration*
shuffle test (the unit-level shuffle test lives in test_c7_wall_segment.py;
the integration test ensures the full C7→C10 pipeline behaves the same
when wall_segments arrive in shuffled order).

†= placeholder name marker.
"""
from __future__ import annotations

import json

import pytest

from buildemup.components.c10 import (
    WetZonePlanConfig,
    plan_wet_zones,
)
from buildemup.tests._c10_fixtures import run_c9_pipeline


# =============================================================================
# C7 amendment W8 integration: shuffle wall_segments storage order; the
# canonical accessor in C10 must produce the same plan.
# =============================================================================


def _serialise_plan_for_replay(planned) -> str:
    """Strip non-deterministic fields and return canonical JSON."""
    wp = planned.wet_zone_plan
    return json.dumps({
        "wet_wall_assignment": wp.wet_wall_assignment,
        "riser_count": wp.riser_count,
        "total_wet_run_length_m": wp.total_wet_run_length_m,
        "symbolic_bend_estimate": wp.symbolic_bend_estimate,
        "wall_segments_used": list(wp.wall_segments_used),
        "trap_arm_distances": {
            f"{k[0]}|{k[1]}": [
                round(v.upper_bound_m, 6),
                round(v.likely_bound_m, 6),
            ]
            for k, v in wp.trap_arm_distances.items()
        },
        "fixture_types_per_room": {
            k: list(v) for k, v in wp.fixture_types_per_room.items()
        },
        "acceptable_wall_sets": {
            k: list(v) for k, v in wp.acceptable_wall_sets.items()
        },
    }, sort_keys=True)


class TestW8IntegrationShuffle:
    """W8: production code must use Grid.wall_segments_canonical(). The
    integration test confirms this end-to-end in C10."""

    def test_pipeline_invariant_to_wall_segments_storage_order(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        config = WetZonePlanConfig(require_verified_plumbing=False)

        # Baseline run with grid as built.
        baseline_out = plan_wet_zones(
            rsc, brief, grid, plot_analysis, config=config,
        )
        assert len(baseline_out) > 0
        baseline_serialisations = [
            _serialise_plan_for_replay(p) for p in baseline_out
        ]

        # Shuffle the wall_segments storage. We use a deterministic
        # permutation (reverse order) since the canonical accessor will
        # re-sort by axis.
        from dataclasses import replace
        shuffled_walls = tuple(reversed(grid.wall_segments))
        shuffled_grid = replace(grid, wall_segments=shuffled_walls)

        shuffled_out = plan_wet_zones(
            rsc, brief, shuffled_grid, plot_analysis, config=config,
        )
        assert len(shuffled_out) == len(baseline_out)
        shuffled_serialisations = [
            _serialise_plan_for_replay(p) for p in shuffled_out
        ]

        for a, b in zip(baseline_serialisations, shuffled_serialisations):
            assert a == b, (
                "C10 plan changed when wall_segments were shuffled — "
                "production code must use grid.wall_segments_canonical() "
                "(W8 invariant)."
            )


# =============================================================================
# Snapshot determinism within a single grid build
# =============================================================================


class TestPlanSerialisationDeterminism:

    def test_two_identical_runs_produce_identical_serialisation(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        config = WetZonePlanConfig(require_verified_plumbing=False)
        out1 = plan_wet_zones(rsc, brief, grid, plot_analysis, config=config)
        out2 = plan_wet_zones(rsc, brief, grid, plot_analysis, config=config)
        for a, b in zip(out1, out2):
            assert _serialise_plan_for_replay(a) == _serialise_plan_for_replay(b)

    def test_riser_groups_sorted_by_group_id(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        out = plan_wet_zones(
            rsc, brief, grid, plot_analysis,
            config=WetZonePlanConfig(require_verified_plumbing=False),
        )
        for planned in out:
            ids = [rg.group_id for rg in planned.wet_zone_plan.riser_groups]
            assert ids == sorted(ids)

    def test_wall_segments_used_sorted_lex(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        out = plan_wet_zones(
            rsc, brief, grid, plot_analysis,
            config=WetZonePlanConfig(require_verified_plumbing=False),
        )
        for planned in out:
            ws = planned.wet_zone_plan.wall_segments_used
            assert list(ws) == sorted(ws)

    def test_wall_scoring_breakdown_lex_sorted(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        out = plan_wet_zones(
            rsc, brief, grid, plot_analysis,
            config=WetZonePlanConfig(require_verified_plumbing=False),
        )
        for planned in out:
            keys = [
                (v.wall_id, v.category)
                for v in planned.provenance.wall_scoring_breakdown
            ]
            assert keys == sorted(keys)


# =============================================================================
# Provenance non-deterministic-fields excluded from determinism checks
# =============================================================================


class TestProvenanceObservationalFields:

    def test_observational_runtime_ms_is_int(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        out = plan_wet_zones(
            rsc, brief, grid, plot_analysis,
            config=WetZonePlanConfig(require_verified_plumbing=False),
        )
        for planned in out:
            ms = planned.provenance._observational_runtime_ms
            assert isinstance(ms, int)
            assert ms >= 0

    def test_derived_at_is_float(self):
        rsc, brief, grid, plot_analysis = run_c9_pipeline()
        out = plan_wet_zones(
            rsc, brief, grid, plot_analysis,
            config=WetZonePlanConfig(require_verified_plumbing=False),
        )
        for planned in out:
            assert isinstance(planned.provenance.derived_at, float)
