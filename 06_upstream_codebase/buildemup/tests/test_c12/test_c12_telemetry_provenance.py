"""
C12 v1.0 telemetry + provenance test suite (S44 continuation).

Covers:
- TelemetrySink interface contract (Null + List implementations)
- Event type immutability + field correctness
- Orchestrator emission paths (single-floor + multi-floor)
- Adjacency coverage counting
- MFRA convergence event abort_reason classification
- place_and_align_with_provenance contract
- PlacementProvenance field invariants
- STRICT-mode raise still emits performance event (telemetry-first contract)
- Default config = zero-overhead NullTelemetrySink
"""
from __future__ import annotations

import pytest

from buildemup.components.c12 import (
    AdjacencyCoverageEvent,
    CandidateProvenanceEntry,
    GeometricInfeasibilityError,
    IrregularEnvelopeRejectionEvent,
    ListTelemetrySink,
    MfraConvergenceEvent,
    MultiFloorPlacementInput,
    NullTelemetrySink,
    PerformanceEvent,
    PlacedCandidate,
    PlacedRoom,
    PlacementConfig,
    PlacementDiversityEvent,
    PlacementProvenance,
    RoomSpec,
    SingleFloorPlacementInput,
    TelemetrySink,
    UnknownCategoryEvent,
    capture_c12_environment_fingerprint,
    place_and_align,
    place_and_align_with_provenance,
)


# ─────────────────────────────────────────────────────────────────────
# Event type immutability + construction
# ─────────────────────────────────────────────────────────────────────


def test_placement_diversity_event_frozen():
    e = PlacementDiversityEvent(
        candidate_signature="rc:a", n_rooms=4,
        vertical_cuts_used=2, horizontal_cuts_used=1, max_recursion_depth=3,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        e.n_rooms = 99  # type: ignore[misc]


def test_mfra_convergence_event_construction():
    e = MfraConvergenceEvent(
        source_multifloor_signature="mf:test", n_floors=2,
        converged=True, retries_used=0,
        delta_progression=(0.0,),
        final_max_misalignment_m=0.0,
        abort_reason="converged",
    )
    assert e.converged
    assert e.delta_progression == (0.0,)


def test_adjacency_coverage_event_construction():
    e = AdjacencyCoverageEvent(
        candidate_signature="rc:a",
        hard_hints_total=3, hard_hints_satisfied=2,
        soft_hints_total=1, soft_hints_satisfied=1,
    )
    assert e.hard_hints_total == 3
    assert e.hard_hints_satisfied == 2


def test_performance_event_construction():
    e = PerformanceEvent(
        candidate_signature="rc:a", n_rooms=4,
        wallclock_seconds=0.123, phase="single_floor",
    )
    assert e.wallclock_seconds == pytest.approx(0.123)


def test_unknown_category_event_construction():
    e = UnknownCategoryEvent(raw_category="library", normalized_to="other")
    assert e.raw_category == "library"


def test_irregular_envelope_rejection_event_construction():
    e = IrregularEnvelopeRejectionEvent(
        envelope_signature="env:abc", rejection_reason="non-rectangular",
    )
    assert e.envelope_signature == "env:abc"


# ─────────────────────────────────────────────────────────────────────
# Sink interface contracts
# ─────────────────────────────────────────────────────────────────────


def test_null_sink_drops_everything_silently():
    sink = NullTelemetrySink()
    # Calls don't raise; no observable side effect.
    sink.record_diversity(PlacementDiversityEvent("a", 1, 0, 0, 0))
    sink.record_mfra_convergence(MfraConvergenceEvent(
        "a", 1, True, 0, (0.0,), 0.0, "converged",
    ))
    sink.record_adjacency_coverage(AdjacencyCoverageEvent("a", 0, 0, 0, 0))
    sink.record_performance(PerformanceEvent("a", 1, 0.0, "single_floor"))
    sink.record_unknown_category(UnknownCategoryEvent("x", "other"))
    sink.record_irregular_envelope_rejection(
        IrregularEnvelopeRejectionEvent("env", "reason"),
    )


def test_list_sink_collects_each_event_type_independently():
    sink = ListTelemetrySink()
    sink.record_diversity(PlacementDiversityEvent("a", 1, 0, 0, 0))
    sink.record_diversity(PlacementDiversityEvent("b", 2, 1, 1, 1))
    sink.record_performance(PerformanceEvent("a", 1, 0.0, "single_floor"))
    assert len(sink.diversity_events) == 2
    assert len(sink.performance_events) == 1
    assert sink.mfra_events == []
    assert sink.total_events() == 3


def test_telemetry_sink_is_abstract():
    """Can't instantiate TelemetrySink directly — it's abstract."""
    with pytest.raises(TypeError):
        TelemetrySink()  # type: ignore[abstract]


# ─────────────────────────────────────────────────────────────────────
# Config telemetry_sink validation
# ─────────────────────────────────────────────────────────────────────


def test_config_default_telemetry_sink_is_none():
    cfg = PlacementConfig()
    assert cfg.telemetry_sink is None


def test_config_accepts_list_sink():
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    assert cfg.telemetry_sink is sink


def test_orchestrator_rejects_non_sink_object():
    """Invalid telemetry_sink type → TypeError at orchestrator boundary."""
    sf = SingleFloorPlacementInput(
        candidate_signature="rc:x",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(room_id="r", category="bedroom",
                        target_width_m=2, target_depth_m=2),),
        envelope_width_m=4, envelope_depth_m=4,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(telemetry_sink="not a sink")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="TelemetrySink"):
        place_and_align(
            single_floor_inputs=(sf,), multi_floor_inputs=(),
            config=cfg, c11b_env_fingerprint_hash="upstream",
        )


# ─────────────────────────────────────────────────────────────────────
# Orchestrator emission paths
# ─────────────────────────────────────────────────────────────────────


def _sf(sig: str = "rc:test", hints=()) -> SingleFloorPlacementInput:
    return SingleFloorPlacementInput(
        candidate_signature=sig,
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(
            RoomSpec(room_id="bedroom_1", category="bedroom",
                     target_width_m=4, target_depth_m=4),
            RoomSpec(room_id="kitchen_1", category="kitchen",
                     target_width_m=4, target_depth_m=4),
        ),
        envelope_width_m=8, envelope_depth_m=4,
        adjacency_hints=hints,
    )


def test_orchestrator_emits_adjacency_event_per_success():
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    place_and_align(
        single_floor_inputs=(_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(sink.adjacency_events) == 1
    e = sink.adjacency_events[0]
    assert e.candidate_signature == "rc:test"


def test_orchestrator_emits_performance_event_per_candidate():
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    place_and_align(
        single_floor_inputs=(_sf("rc:a"), _sf("rc:b")),
        multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(sink.performance_events) == 2
    sigs = sorted(e.candidate_signature for e in sink.performance_events)
    assert sigs == ["rc:a", "rc:b"]


def test_orchestrator_adjacency_satisfaction_counted_correctly():
    """Hard hints satisfied/total counts match shared-edge realization."""
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    # Two-room scenario: HARD hint between adjacent rooms → satisfied.
    sf = _sf(hints=(("bedroom_1", "kitchen_1", "hard"),))
    place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    e = sink.adjacency_events[0]
    assert e.hard_hints_total == 1
    assert e.hard_hints_satisfied == 1


def test_orchestrator_soft_hint_counted_separately():
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    sf = _sf(hints=(("bedroom_1", "kitchen_1", "soft"),))
    place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    e = sink.adjacency_events[0]
    assert e.soft_hints_total == 1
    assert e.soft_hints_satisfied == 1
    assert e.hard_hints_total == 0


def test_orchestrator_emits_mfra_event_per_multifloor_candidate():
    """One MfraConvergenceEvent per multi-floor candidate."""
    def _floor(sig):
        return SingleFloorPlacementInput(
            candidate_signature=sig,
            capability_mode="MATERIALIZED",
            placement_safe=True, geometry_materialized=True,
            rooms=(
                RoomSpec(room_id="staircase_1", category="staircase",
                         target_width_m=2, target_depth_m=4),
                RoomSpec(room_id="bedroom_1", category="bedroom",
                         target_width_m=4, target_depth_m=4),
            ),
            envelope_width_m=6, envelope_depth_m=4,
            adjacency_hints=(),
        )
    mf = MultiFloorPlacementInput(
        source_signature="mf:test",
        floors=(("first", _floor("rc:F1")), ("ground", _floor("rc:G0"))),
        feature_room_ids_by_floor={"first": {"staircase_1"}, "ground": {"staircase_1"}},
        vertical_cores=(),
    )
    sink = ListTelemetrySink()
    cfg = PlacementConfig(telemetry_sink=sink)
    place_and_align(
        single_floor_inputs=(), multi_floor_inputs=(mf,),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(sink.mfra_events) == 1
    e = sink.mfra_events[0]
    assert e.source_multifloor_signature == "mf:test"
    assert e.n_floors == 2
    assert e.converged
    assert e.abort_reason == "converged"


def test_orchestrator_performance_event_emitted_even_on_strict_raise():
    """Per telemetry-first contract: STRICT mode raise still emits a
    PerformanceEvent before re-raising."""
    bad_sf = SingleFloorPlacementInput(
        candidate_signature="rc:bad",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(
            room_id="huge", category="living",
            target_width_m=100, target_depth_m=100,
        ),),
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    sink = ListTelemetrySink()
    cfg = PlacementConfig(strict_mode=True, telemetry_sink=sink)
    with pytest.raises(GeometricInfeasibilityError):
        place_and_align(
            single_floor_inputs=(bad_sf,), multi_floor_inputs=(),
            config=cfg, c11b_env_fingerprint_hash="upstream",
        )
    # PerformanceEvent emitted before raise
    assert len(sink.performance_events) == 1
    assert sink.performance_events[0].candidate_signature == "rc:bad"


def test_orchestrator_warn_mode_still_emits_performance():
    bad_sf = SingleFloorPlacementInput(
        candidate_signature="rc:bad",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(
            room_id="huge", category="living",
            target_width_m=100, target_depth_m=100,
        ),),
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    sink = ListTelemetrySink()
    cfg = PlacementConfig(strict_mode=False, telemetry_sink=sink)
    place_and_align(
        single_floor_inputs=(bad_sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(sink.performance_events) == 1


# ─────────────────────────────────────────────────────────────────────
# place_and_align_with_provenance contract
# ─────────────────────────────────────────────────────────────────────


def test_with_provenance_returns_tuple():
    cfg = PlacementConfig()
    result, prov = place_and_align_with_provenance(
        single_floor_inputs=(_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    from buildemup.components.c12 import PlacementBatchResult
    assert isinstance(result, PlacementBatchResult)
    assert isinstance(prov, PlacementProvenance)


def test_provenance_contains_candidate_entries():
    cfg = PlacementConfig()
    result, prov = place_and_align_with_provenance(
        single_floor_inputs=(_sf("rc:a"), _sf("rc:b")),
        multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(prov.candidates) == 2
    sigs = sorted(c.candidate_signature for c in prov.candidates)
    assert sigs == ["rc:a", "rc:b"]
    for c in prov.candidates:
        assert c.outcome == "success"
        assert c.wallclock_seconds >= 0
        assert c.phase_reached == "phase3"
        assert c.n_rooms == 2
        assert c.failure_record is None


def test_provenance_captures_failure_in_warn_mode():
    bad_sf = SingleFloorPlacementInput(
        candidate_signature="rc:bad",
        capability_mode="MATERIALIZED",
        placement_safe=True, geometry_materialized=True,
        rooms=(RoomSpec(
            room_id="huge", category="living",
            target_width_m=100, target_depth_m=100,
        ),),
        envelope_width_m=10, envelope_depth_m=10,
        adjacency_hints=(),
    )
    cfg = PlacementConfig(strict_mode=False)
    result, prov = place_and_align_with_provenance(
        single_floor_inputs=(bad_sf,), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(prov.candidates) == 1
    c = prov.candidates[0]
    assert c.outcome == "failure"
    assert c.failure_record is not None
    assert c.failure_record.error_type == "GeometricInfeasibilityError"


def test_provenance_total_wallclock_positive():
    cfg = PlacementConfig()
    _, prov = place_and_align_with_provenance(
        single_floor_inputs=(_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert prov.total_wallclock_seconds > 0


def test_provenance_env_fingerprint_matches_result_cache_key():
    cfg = PlacementConfig()
    result, prov = place_and_align_with_provenance(
        single_floor_inputs=(_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert prov.cache_key == result.cache_key
    assert prov.c12_version == result.c12_version


def test_provenance_construction_validates_fields():
    """PlacementProvenance.__post_init__ rejects invalid inputs."""
    env_fp = capture_c12_environment_fingerprint(
        c11b_env_fingerprint_hash="up", config=PlacementConfig(),
    )
    # Empty version → ValueError
    with pytest.raises(ValueError, match="c12_version"):
        PlacementProvenance(
            c12_version="",
            env_fingerprint=env_fp,
            cache_key="abc",
            total_wallclock_seconds=0.1,
            candidates=(),
            failures=(),
        )
    # Negative wallclock → ValueError
    with pytest.raises(ValueError, match="wallclock"):
        PlacementProvenance(
            c12_version="v1.0",
            env_fingerprint=env_fp,
            cache_key="abc",
            total_wallclock_seconds=-1.0,
            candidates=(),
            failures=(),
        )


# ─────────────────────────────────────────────────────────────────────
# Default config = zero-overhead
# ─────────────────────────────────────────────────────────────────────


def test_default_config_no_telemetry_required():
    """Default PlacementConfig (telemetry_sink=None) works without
    importing telemetry types — zero-overhead default contract."""
    cfg = PlacementConfig()
    assert cfg.telemetry_sink is None
    # And place_and_align works fine
    result = place_and_align(
        single_floor_inputs=(_sf(),), multi_floor_inputs=(),
        config=cfg, c11b_env_fingerprint_hash="upstream",
    )
    assert len(result.placed_candidates) == 1


def test_replay_determinism_unaffected_by_telemetry():
    """Per v0.3-A6: cache_relevant=False means telemetry_sink does
    NOT affect cache key. Same input + different sinks → same hash."""
    sf = _sf()
    cfg_null = PlacementConfig(telemetry_sink=None)
    cfg_list = PlacementConfig(telemetry_sink=ListTelemetrySink())
    r1 = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg_null, c11b_env_fingerprint_hash="upstream",
    )
    r2 = place_and_align(
        single_floor_inputs=(sf,), multi_floor_inputs=(),
        config=cfg_list, c11b_env_fingerprint_hash="upstream",
    )
    assert r1.cache_key == r2.cache_key
    assert r1.placed_candidates == r2.placed_candidates


# ─────────────────────────────────────────────────────────────────────
# CandidateProvenanceEntry
# ─────────────────────────────────────────────────────────────────────


def test_candidate_provenance_entry_frozen():
    e = CandidateProvenanceEntry(
        candidate_signature="rc:a",
        outcome="success",
        wallclock_seconds=0.1,
        phase_reached="phase3",
        n_rooms=4,
    )
    with pytest.raises(Exception):
        e.outcome = "failure"  # type: ignore[misc]


def test_candidate_provenance_default_failure_record_none():
    e = CandidateProvenanceEntry(
        candidate_signature="rc:a",
        outcome="success",
        wallclock_seconds=0.1,
        phase_reached="phase3",
        n_rooms=4,
    )
    assert e.failure_record is None
