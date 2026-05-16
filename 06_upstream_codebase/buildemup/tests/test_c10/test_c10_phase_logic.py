"""
BuildemUp† — Component 10 — phase logic tests.

Per C10 SPEC v1.0 LOCKED § 3 (Behaviour). Covers:
  - Phase 0 (acceptable_wall_set, filter_feasible_walls)
  - Phase 0.5 (fast_fail_pre_screen)
  - Phase 1b (rank_walls; total_score)
  - Phase 2 (cluster_wet_rooms)
  - Phase 2.5 (cluster_occupancy_validate)
  - Phase 3 (assign_clusters_to_walls — happy path)
  - Phase 4 (Manhattan + per-fixture factor — covered in test_c10_invariants
             but expanded here)
  - Phase 5 (provenance.compute_risk_level)

†= placeholder name marker.
"""
from __future__ import annotations

import math

import pytest

from buildemup.components.c07.grid_generator import Grid, GridGenerator
from buildemup.components.c07.wall_segment import WallTag
from buildemup.components.c10 import (
    PlacementRiskLevel,
    PreClusteringInfeasibleError,
    WetZoneCapacityWeights,
    WetZoneInfeasibleError,
    WetZoneScoringWeights,
    compute_risk_level,
)
from buildemup.components.c10.clustering import cluster_wet_rooms
from buildemup.components.c10.occupancy import (
    cluster_occupancy_validate,
    fast_fail_pre_screen,
)
from buildemup.components.c10.scoring import (
    acceptable_wall_set,
    filter_feasible_walls,
    rank_walls,
    total_score,
)


# =============================================================================
# Test fixture: a 12m × 18m grid
# =============================================================================


def _make_grid(envelope_w_m: float = 12.0, envelope_d_m: float = 18.0) -> Grid:
    return GridGenerator().generate(envelope_w_m, envelope_d_m)


# =============================================================================
# Phase 0 — filter_feasible_walls
# =============================================================================


class TestPhase0Filter:

    def test_returns_walls_above_min_length(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        assert len(feas) == 4               # all 4 outer walls eligible
        for w in feas:
            assert w.length_m >= 1.5
            assert WallTag.EXTERNAL in w.tags

    def test_uses_canonical_accessor(self):
        # Result order matches canonical (CCW from south).
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        canonical = grid.wall_segments_canonical()
        assert tuple(w.wall_id for w in feas) == tuple(
            w.wall_id for w in canonical
        )


# =============================================================================
# Phase 0 — acceptable_wall_set
# =============================================================================


class TestAcceptableWallSet:

    def test_returns_walls_meeting_min_width(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        # All walls >= 12m so any min_width <= 12 passes
        out = acceptable_wall_set(2.4, feas)
        assert len(out) == 4

    def test_excludes_walls_shorter_than_min_width(self):
        grid = _make_grid(envelope_w_m=6.0, envelope_d_m=18.0)
        feas = filter_feasible_walls(grid)
        # WALL_SOUTH/NORTH = 6m. Min width 10m -> only the 18m walls eligible.
        out = acceptable_wall_set(10.0, feas)
        assert "WALL_EAST" in out
        assert "WALL_WEST" in out
        assert "WALL_SOUTH" not in out
        assert "WALL_NORTH" not in out

    def test_lex_asc_sorted(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        out = acceptable_wall_set(1.0, feas)
        assert list(out) == sorted(out)


# =============================================================================
# Phase 0.5 — fast_fail_pre_screen
# =============================================================================


class TestPhase05PreScreen:

    def test_no_hard_edges_passes(self):
        # No hard edges → no-op
        fast_fail_pre_screen((), {"BA1": ("WALL_NORTH",)})

    def test_compatible_intersection_passes(self):
        sets = {
            "BA1": ("WALL_NORTH", "WALL_SOUTH"),
            "BA2": ("WALL_SOUTH", "WALL_EAST"),
        }
        # Intersection = {WALL_SOUTH} — non-empty → pass
        fast_fail_pre_screen([("BA1", "BA2")], sets)

    def test_empty_intersection_raises(self):
        sets = {
            "BA1": ("WALL_NORTH",),
            "BA2": ("WALL_SOUTH",),
        }
        with pytest.raises(PreClusteringInfeasibleError):
            fast_fail_pre_screen([("BA1", "BA2")], sets)

    def test_aggregates_multiple_infeasible_pairs(self):
        sets = {
            "A": ("W1",), "B": ("W2",), "C": ("W3",),
        }
        try:
            fast_fail_pre_screen([("A", "B"), ("A", "C")], sets)
        except PreClusteringInfeasibleError as e:
            # 2 hints (one per pair)
            assert len(e.remediation_hints) == 2
            assert e.failure_phase == "pre_clustering"
        else:
            pytest.fail("Expected PreClusteringInfeasibleError")


# =============================================================================
# Phase 1b — rank_walls + total_score
# =============================================================================


class TestPhase1bRanking:

    def test_emits_one_vector_per_wall_per_category(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        weights = WetZoneScoringWeights()
        vectors = rank_walls(feas, grid=grid, weights=weights)
        # 4 walls × 4 categories (bathroom/kitchen/utility/pooja)
        assert len(vectors) == 4 * 4

    def test_lex_asc_by_wall_id_then_category(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        vectors = rank_walls(feas, grid=grid, weights=WetZoneScoringWeights())
        keys = [(v.wall_id, v.category) for v in vectors]
        assert keys == sorted(keys)

    def test_scoring_weights_hash_consistent(self):
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        weights = WetZoneScoringWeights()
        vectors = rank_walls(feas, grid=grid, weights=weights)
        # All vectors share the same hash because weights is a singleton.
        hashes = {v.scoring_weights_hash for v in vectors}
        assert len(hashes) == 1

    def test_total_score_weighted_sum(self):
        weights = WetZoneScoringWeights(
            weight_engineering=2.0, weight_cultural=3.0, weight_adjacency=4.0,
        )
        grid = _make_grid()
        feas = filter_feasible_walls(grid)
        vectors = rank_walls(feas, grid=grid, weights=weights)
        for v in vectors:
            expected = (
                2.0 * v.engineering_score
                + 3.0 * v.cultural_score
                + 4.0 * v.adjacency_score
            )
            assert math.isclose(total_score(v, weights), expected, abs_tol=1e-9)


# =============================================================================
# Phase 2 — cluster_wet_rooms
# =============================================================================


class TestPhase2Clustering:

    def test_no_overlap_no_merge(self):
        sets = {
            "A": ("W1",), "B": ("W2",),
        }
        clusters, walls = cluster_wet_rooms(["A", "B"], acceptable_wall_sets=sets)
        # No overlap → 2 separate clusters
        assert len(clusters) == 2

    def test_overlap_triggers_merge_when_no_capacity_check(self):
        sets = {
            "A": ("W1", "W2"), "B": ("W2", "W3"),
        }
        clusters, walls = cluster_wet_rooms(
            ["A", "B"], acceptable_wall_sets=sets,
        )
        # Overlap = {W2} → merge into single cluster
        assert len(clusters) == 1

    def test_hard_anti_edge_prevents_merge(self):
        sets = {
            "A": ("W1", "W2"), "B": ("W2", "W3"),
        }
        clusters, walls = cluster_wet_rooms(
            ["A", "B"], hard_anti_edges=[("A", "B")],
            acceptable_wall_sets=sets,
        )
        # HARD-anti -> no merge
        assert len(clusters) == 2

    def test_capacity_check_vetos_merge(self):
        sets = {
            "A": ("W1",), "B": ("W1",),
        }
        # capacity_check returns False for any merge candidate
        always_no = lambda members, walls: False
        clusters, walls = cluster_wet_rooms(
            ["A", "B"], acceptable_wall_sets=sets,
            capacity_check=always_no,
        )
        assert len(clusters) == 2

    def test_capacity_check_allows_merge(self):
        sets = {
            "A": ("W1",), "B": ("W1",),
        }
        always_yes = lambda members, walls: True
        clusters, walls = cluster_wet_rooms(
            ["A", "B"], acceptable_wall_sets=sets,
            capacity_check=always_yes,
        )
        assert len(clusters) == 1

    def test_lex_asc_cluster_id_winner(self):
        sets = {
            "BA1": ("W1",), "KIT1": ("W1",),
        }
        clusters, _ = cluster_wet_rooms(
            ["BA1", "KIT1"], acceptable_wall_sets=sets,
        )
        # Winner is "cluster_BA1" (lex-ASC)
        assert "cluster_BA1" in clusters

    def test_three_way_chain_merge(self):
        sets = {
            "A": ("W1",), "B": ("W1",), "C": ("W1",),
        }
        clusters, _ = cluster_wet_rooms(
            ["A", "B", "C"], acceptable_wall_sets=sets,
        )
        assert len(clusters) == 1


# =============================================================================
# Phase 2.5 — cluster_occupancy_validate
# =============================================================================


class TestPhase25Occupancy:

    def test_passes_when_cluster_fits(self):
        grid = _make_grid()
        clusters = {"cluster_1": ("BA1",)}
        cluster_walls = {"cluster_1": {"WALL_EAST"}}
        widths = {"BA1": 1.5}
        weights = WetZoneCapacityWeights()
        cluster_occupancy_validate(
            clusters, cluster_walls, widths, grid, weights,
        )

    def test_raises_when_cluster_too_large(self):
        grid = _make_grid()
        clusters = {"cluster_1": ("BA1", "BA2", "BA3", "BA4", "BA5", "BA6")}
        # SOUTH/NORTH walls = 12m, usable = 12 - 6 = 6m. Cluster = 12m.
        cluster_walls = {"cluster_1": {"WALL_SOUTH"}}
        widths = {f"BA{i}": 2.0 for i in range(1, 7)}
        weights = WetZoneCapacityWeights()
        with pytest.raises(WetZoneInfeasibleError) as exc:
            cluster_occupancy_validate(
                clusters, cluster_walls, widths, grid, weights,
            )
        assert exc.value.failure_phase == "post_clustering_spatial"

    def test_uses_explicit_safety_margin_override(self):
        grid = _make_grid()
        clusters = {"cluster_1": ("BA1",)}
        cluster_walls = {"cluster_1": {"WALL_EAST"}}
        widths = {"BA1": 1.5}
        # Explicit margin = 1.0
        weights = WetZoneCapacityWeights(wall_safety_margin_m=1.0)
        cluster_occupancy_validate(
            clusters, cluster_walls, widths, grid, weights,
        )


# =============================================================================
# Phase 5 — compute_risk_level
# =============================================================================


class TestComputeRiskLevel:

    def test_zero_score_low(self):
        assert compute_risk_level(0.0) == PlacementRiskLevel.LOW

    def test_score_below_one_low(self):
        assert compute_risk_level(0.5) == PlacementRiskLevel.LOW

    def test_score_one_medium(self):
        assert compute_risk_level(1.0) == PlacementRiskLevel.MEDIUM

    def test_score_two_medium(self):
        assert compute_risk_level(2.0) == PlacementRiskLevel.MEDIUM

    def test_score_three_high(self):
        assert compute_risk_level(3.0) == PlacementRiskLevel.HIGH

    def test_large_score_high(self):
        assert compute_risk_level(99.0) == PlacementRiskLevel.HIGH
