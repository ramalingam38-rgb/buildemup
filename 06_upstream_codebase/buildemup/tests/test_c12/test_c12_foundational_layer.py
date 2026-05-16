"""Tests for C12 v1.0 LOCKED foundational layer (S44).

Covers:
- versioning constants
- error hierarchy
- core schema dataclasses (PlacedRoom, SharedEdge, PlacedCandidate,
  VerticalAlignmentReport, MultiFloorPlacedCandidate, FailureRecord,
  PlacementBatchResult)
- PlacementConfig

NOT covered yet (S45+): bounds, env_fingerprint, slicing-tree
placement, VAV, MFRA, orchestrator, integration with C8/C9 amendments.
"""
from __future__ import annotations

import pytest

from buildemup.components.c12 import (
    AdjacencyConstraintViolationError,
    C12_VERSION,
    C12ConfigurationError,
    CapabilityFlagInconsistencyError,
    CirculationInfeasibilityError,
    DoorwayFeasibilityError,
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
    FailureRecord,
    GeometricInfeasibilityError,
    LocalPlacementError,
    MultiFloorPlacedCandidate,
    PerCandidatePlacementError,
    PlacedCandidate,
    PlacedRoom,
    PlacementAlgorithmTimeoutError,
    PlacementBatchResult,
    PlacementConfig,
    PlacementError,
    SharedEdge,
    UpstreamSchemaDriftError,
    VerticalAlignmentError,
    VerticalAlignmentReport,
)


# ─────────────────────────────────────────────────────────────────────
# Versioning constants
# ─────────────────────────────────────────────────────────────────────


def test_c12_version_is_v1_0():
    assert C12_VERSION == "v1.0"


def test_expected_c8_schema_version_matches_c8():
    from buildemup.components.c08.schema import CORRIDOR_ZONE_SCHEMA_VERSION
    assert EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION == CORRIDOR_ZONE_SCHEMA_VERSION


def test_expected_c9_schema_version_matches_c9():
    from buildemup.domain.adjacency_hint import ADJACENCY_HINT_SCHEMA_VERSION
    assert EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION == ADJACENCY_HINT_SCHEMA_VERSION


# ─────────────────────────────────────────────────────────────────────
# Error hierarchy
# ─────────────────────────────────────────────────────────────────────


def test_error_base_class():
    assert issubclass(LocalPlacementError, PlacementError)
    assert issubclass(PerCandidatePlacementError, PlacementError)


def test_local_errors_subclass_local():
    assert issubclass(UpstreamSchemaDriftError, LocalPlacementError)
    assert issubclass(C12ConfigurationError, LocalPlacementError)


def test_per_candidate_errors_subclass_per_candidate():
    for cls in (
        GeometricInfeasibilityError,
        CapabilityFlagInconsistencyError,
        PlacementAlgorithmTimeoutError,
        CirculationInfeasibilityError,
        VerticalAlignmentError,
        DoorwayFeasibilityError,
        AdjacencyConstraintViolationError,
    ):
        assert issubclass(cls, PerCandidatePlacementError), cls


def test_error_count_matches_spec():
    """Per § 4: 11 failure types total (2 local + 7 per-candidate +
    2 base = 11 classes in the hierarchy)."""
    from buildemup.components.c12 import errors as e
    classes = [
        getattr(e, n) for n in e.__all__
        if isinstance(getattr(e, n), type) and issubclass(getattr(e, n), Exception)
    ]
    # 3 bases + 2 local + 7 per-candidate = 12 classes total
    # (PlacementError + LocalPlacementError + PerCandidatePlacementError
    # are the 3 bases)
    assert len(classes) == 12


# ─────────────────────────────────────────────────────────────────────
# PlacedRoom
# ─────────────────────────────────────────────────────────────────────


def test_placed_room_construction():
    r = PlacedRoom(
        room_id="bedroom_1",
        category="bedroom",
        x_m=1.0,
        y_m=2.0,
        width_m=3.5,
        depth_m=3.0,
    )
    assert r.room_id == "bedroom_1"
    assert r.category == "bedroom"


def test_placed_room_rejects_empty_room_id():
    with pytest.raises(ValueError, match="room_id"):
        PlacedRoom(room_id="", category="bedroom", x_m=0, y_m=0, width_m=1, depth_m=1)


def test_placed_room_rejects_empty_category():
    with pytest.raises(ValueError, match="category"):
        PlacedRoom(room_id="r1", category="", x_m=0, y_m=0, width_m=1, depth_m=1)


def test_placed_room_rejects_non_positive_extents():
    with pytest.raises(ValueError, match="positive extents"):
        PlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=0, depth_m=1)
    with pytest.raises(ValueError, match="positive extents"):
        PlacedRoom(room_id="r1", category="bedroom", x_m=0, y_m=0, width_m=1, depth_m=-1)


# ─────────────────────────────────────────────────────────────────────
# SharedEdge
# ─────────────────────────────────────────────────────────────────────


def test_shared_edge_construction():
    e = SharedEdge(
        room_a_id="bathroom_1",
        room_b_id="bedroom_1",
        axis="vertical",
        overlap_start_m=2.0,
        overlap_end_m=3.5,
        overlap_length_m=1.5,
        min_required_clear_width_m=0.9,
        doorway_feasible=True,
    )
    assert e.doorway_feasible is True


def test_shared_edge_rejects_reverse_lex_order():
    with pytest.raises(ValueError, match="canonical order"):
        SharedEdge(
            room_a_id="bedroom_1",
            room_b_id="bathroom_1",  # lex < bedroom_1
            axis="vertical",
            overlap_start_m=0,
            overlap_end_m=1,
            overlap_length_m=1,
            min_required_clear_width_m=0.9,
            doorway_feasible=True,
        )


def test_shared_edge_rejects_same_room():
    with pytest.raises(ValueError, match="canonical order"):
        SharedEdge(
            room_a_id="r1",
            room_b_id="r1",
            axis="vertical",
            overlap_start_m=0,
            overlap_end_m=1,
            overlap_length_m=1,
            min_required_clear_width_m=0.9,
            doorway_feasible=True,
        )


def test_shared_edge_rejects_bad_axis():
    with pytest.raises(ValueError, match="axis"):
        SharedEdge(
            room_a_id="a", room_b_id="b", axis="diagonal",
            overlap_start_m=0, overlap_end_m=1, overlap_length_m=1,
            min_required_clear_width_m=0.9, doorway_feasible=True,
        )


def test_shared_edge_rejects_non_positive_overlap():
    with pytest.raises(ValueError, match="overlap_length_m"):
        SharedEdge(
            room_a_id="a", room_b_id="b", axis="vertical",
            overlap_start_m=0, overlap_end_m=0, overlap_length_m=0,
            min_required_clear_width_m=0.9, doorway_feasible=False,
        )


def test_shared_edge_rejects_non_positive_min_width():
    with pytest.raises(ValueError, match="min_required_clear_width_m"):
        SharedEdge(
            room_a_id="a", room_b_id="b", axis="vertical",
            overlap_start_m=0, overlap_end_m=1, overlap_length_m=1,
            min_required_clear_width_m=0.0, doorway_feasible=False,
        )


# ─────────────────────────────────────────────────────────────────────
# PlacedCandidate
# ─────────────────────────────────────────────────────────────────────


def _r(room_id: str, x: float = 0.0, y: float = 0.0) -> PlacedRoom:
    return PlacedRoom(
        room_id=room_id, category="bedroom",
        x_m=x, y_m=y, width_m=3.0, depth_m=3.0,
    )


def test_placed_candidate_construction():
    pc = PlacedCandidate(
        source_refined_candidate_signature="rc:abc123",
        placed_rooms=(_r("bedroom_1"), _r("bedroom_2", x=4)),
        shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10.0,
        envelope_depth_m=10.0,
    )
    assert len(pc.placed_rooms) == 2


def test_placed_candidate_rejects_unsorted_rooms():
    with pytest.raises(ValueError, match="sorted lex-ASC by room_id"):
        PlacedCandidate(
            source_refined_candidate_signature="rc:abc",
            placed_rooms=(_r("bedroom_2"), _r("bedroom_1", x=4)),  # reversed
            shared_edges=(),
            placement_algorithm="slicing_kd_tree",
            envelope_width_m=10.0,
            envelope_depth_m=10.0,
        )


def test_placed_candidate_rejects_duplicate_room_ids():
    with pytest.raises(ValueError, match="duplicate"):
        PlacedCandidate(
            source_refined_candidate_signature="rc:abc",
            placed_rooms=(_r("bedroom_1"), _r("bedroom_1", x=4)),
            shared_edges=(),
            placement_algorithm="slicing_kd_tree",
            envelope_width_m=10.0,
            envelope_depth_m=10.0,
        )


def test_placed_candidate_rejects_unsorted_edges():
    e1 = SharedEdge(
        room_a_id="a", room_b_id="z", axis="vertical",
        overlap_start_m=0, overlap_end_m=1, overlap_length_m=1,
        min_required_clear_width_m=0.9, doorway_feasible=True,
    )
    e2 = SharedEdge(
        room_a_id="a", room_b_id="b", axis="vertical",
        overlap_start_m=0, overlap_end_m=1, overlap_length_m=1,
        min_required_clear_width_m=0.9, doorway_feasible=True,
    )
    # (a, z) > (a, b) lex-ASC, so the tuple in that order is unsorted
    with pytest.raises(ValueError, match="sorted lex-ASC"):
        PlacedCandidate(
            source_refined_candidate_signature="rc:abc",
            placed_rooms=(_r("a"), _r("b", x=4), _r("z", x=8)),
            shared_edges=(e1, e2),  # unsorted
            placement_algorithm="slicing_kd_tree",
            envelope_width_m=20.0, envelope_depth_m=10.0,
        )


# ─────────────────────────────────────────────────────────────────────
# VerticalAlignmentReport
# ─────────────────────────────────────────────────────────────────────


def test_vertical_alignment_report_converged():
    r = VerticalAlignmentReport(
        converged=True,
        retries_used=1,
        delta_progression=(0.05, 0.01),
        final_max_misalignment_m=0.01,
        misaligned_features=(),
    )
    assert r.converged
    assert r.retries_used == 1


def test_vertical_alignment_report_rejects_negative_retries():
    with pytest.raises(ValueError, match="retries_used"):
        VerticalAlignmentReport(
            converged=False, retries_used=-1,
            delta_progression=(), final_max_misalignment_m=0.0,
            misaligned_features=(),
        )


def test_vertical_alignment_report_rejects_negative_misalignment():
    with pytest.raises(ValueError, match="final_max_misalignment_m"):
        VerticalAlignmentReport(
            converged=False, retries_used=0,
            delta_progression=(), final_max_misalignment_m=-0.1,
            misaligned_features=(),
        )


# ─────────────────────────────────────────────────────────────────────
# MultiFloorPlacedCandidate
# ─────────────────────────────────────────────────────────────────────


def _pc(sig: str) -> PlacedCandidate:
    return PlacedCandidate(
        source_refined_candidate_signature=sig,
        placed_rooms=(_r("bedroom_1"),),
        shared_edges=(),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=10.0, envelope_depth_m=10.0,
    )


def test_multifloor_placed_candidate_construction():
    mf = MultiFloorPlacedCandidate(
        source_multifloor_candidate_signature="mf:abc",
        per_floor_placements=(
            ("first", _pc("rc:1")),
            ("ground", _pc("rc:0")),
        ),  # sorted by label
        alignment_report=VerticalAlignmentReport(
            converged=True, retries_used=0,
            delta_progression=(0.0,), final_max_misalignment_m=0.0,
            misaligned_features=(),
        ),
        vertical_cores_reserved=(),
    )
    assert len(mf.per_floor_placements) == 2


def test_multifloor_rejects_unsorted_floors():
    """'first' < 'ground' lex-ASC ('f' < 'g'), so ('ground', 'first') is unsorted."""
    with pytest.raises(ValueError, match="sorted by floor_label"):
        MultiFloorPlacedCandidate(
            source_multifloor_candidate_signature="mf:abc",
            per_floor_placements=(
                ("ground", _pc("rc:0")),
                ("first", _pc("rc:1")),
            ),  # 'g' > 'f' so ground first is unsorted
            alignment_report=VerticalAlignmentReport(
                converged=True, retries_used=0, delta_progression=(0.0,),
                final_max_misalignment_m=0.0, misaligned_features=(),
            ),
            vertical_cores_reserved=(),
        )


# ─────────────────────────────────────────────────────────────────────
# PlacementBatchResult
# ─────────────────────────────────────────────────────────────────────


def test_placement_batch_result_construction():
    r = PlacementBatchResult(
        placed_candidates=(),
        multifloor_placed_candidates=(),
        failures=(),
        c12_version=C12_VERSION,
        cache_key="abc123",
    )
    assert r.c12_version == "v1.0"


def test_placement_batch_result_rejects_empty_cache_key():
    with pytest.raises(ValueError, match="cache_key"):
        PlacementBatchResult(
            placed_candidates=(),
            multifloor_placed_candidates=(),
            failures=(),
            c12_version=C12_VERSION,
            cache_key="",
        )


# ─────────────────────────────────────────────────────────────────────
# FailureRecord
# ─────────────────────────────────────────────────────────────────────


def test_failure_record_construction():
    f = FailureRecord(
        candidate_signature="rc:abc",
        error_type="GeometricInfeasibilityError",
        error_message="cannot fit 20 rooms in 5x5m envelope",
        phase="phase1",
    )
    assert f.phase == "phase1"


# ─────────────────────────────────────────────────────────────────────
# PlacementConfig
# ─────────────────────────────────────────────────────────────────────


def test_placement_config_defaults():
    cfg = PlacementConfig()
    assert cfg.strict_mode is True
    assert cfg.placement_algorithm == "slicing_kd_tree"
    assert cfg.vertical_alignment_tolerance_m == 0.02  # v0.2-A8
    assert cfg.multi_floor_max_realign_iterations == 3  # v0.3-A2
    assert cfg.per_candidate_wallclock_seconds == 10.0  # v0.3-A5
    assert cfg.master_seed == 42


def test_placement_config_rejects_negative_tolerance():
    with pytest.raises(C12ConfigurationError, match="tolerance"):
        PlacementConfig(vertical_alignment_tolerance_m=-0.01)


def test_placement_config_rejects_negative_retries():
    with pytest.raises(C12ConfigurationError, match="realign_iterations"):
        PlacementConfig(multi_floor_max_realign_iterations=-1)


def test_placement_config_rejects_zero_wallclock():
    with pytest.raises(C12ConfigurationError, match="per_candidate_wallclock"):
        PlacementConfig(per_candidate_wallclock_seconds=0.0)


def test_placement_config_multifloor_wallclock_derivation():
    """Per v0.3-A5 formula:
    multi_floor_wallclock = per_candidate * num_floors + retries * 5.0
    For 3 floors @ 10s + 3 retries @ 5s = 30 + 15 = 45s."""
    cfg = PlacementConfig()
    assert cfg.effective_multi_floor_wallclock_seconds(3) == 45.0


def test_placement_config_multifloor_wallclock_override():
    cfg = PlacementConfig(multi_floor_wallclock_seconds=120.0)
    assert cfg.effective_multi_floor_wallclock_seconds(3) == 120.0


def test_placement_config_is_frozen():
    cfg = PlacementConfig()
    with pytest.raises((AttributeError, Exception)):
        cfg.strict_mode = False  # type: ignore
