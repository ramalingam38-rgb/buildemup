"""Tests for C13 v1.0 LOCKED provenance — place_doors_with_provenance()
+ DoorPlacementProvenance + CandidateProvenanceEntry. S45 Sub-5.

Covers:

CandidateProvenanceEntry:
- Dataclass validation (non-empty signature, valid outcome)
- Inv: failure_record required iff outcome == "failure"
- Inv: failure_record forbidden iff outcome == "success"
- Negative wallclock_seconds rejected
- Frozen / hashable

DoorPlacementProvenance:
- Empty batch → both counts zero, empty candidates tuple
- Inv: candidates sorted lex-ASC by signature
- Inv: success + failure counts agree with candidate breakdown
- Version constants captured + match batch result

place_doors_with_provenance entry point:
- Returns (DoorPlacementBatchResult, DoorPlacementProvenance) tuple
- Batch result identical (modulo wallclock) to place_doors() output
- Provenance carries one entry per candidate
- Success path: outcome="success", phase_reached="phaseF",
  failure_record=None
- Failure path (WARN mode): outcome="failure", phase_reached matches
  failing phase, failure_record cross-references batch.failed
- Strict mode still raises on PerCandidatePlacementError
- LocalPlacementError halts before any provenance is returned
- Determinism: structural fields (excluding wallclock) byte-equal
  across replay runs (Inv D7 caveat respected)
"""
from __future__ import annotations

import pytest

from buildemup.components.c13 import (
    ADVISORY_SCHEMA_VERSION,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
    CandidateProvenanceEntry,
    DoorPlacementBatchResult,
    DoorPlacementConfig,
    DoorPlacementProvenance,
    EntryRoomNotFoundError,
    FailureRecord,
    InMemoryTelemetrySink,
    PhaseDConvergenceEvent,
    UpstreamSchemaDriftError,
    place_doors,
    place_doors_with_provenance,
)


# ──────────────────────────────────────────────────────────────────────
# Helpers — minimal PlacedCandidate fixtures
# ──────────────────────────────────────────────────────────────────────


def _make_placed_candidate(*, signature="cand_1", rooms_spec, edges_spec, envelope=(10.0, 10.0)):
    from buildemup.components.c12 import PlacedCandidate, PlacedRoom, SharedEdge
    placed_rooms = tuple(
        PlacedRoom(
            room_id=rid, category=cat,
            x_m=x, y_m=y, width_m=w, depth_m=d,
        )
        for rid, cat, x, y, w, d in sorted(rooms_spec, key=lambda r: r[0])
    )
    edges = []
    for a, b, axis, overlap, min_clear, feasible in edges_spec:
        edges.append(SharedEdge(
            room_a_id=a, room_b_id=b, axis=axis,
            overlap_start_m=0.0, overlap_end_m=overlap,
            overlap_length_m=overlap,
            min_required_clear_width_m=min_clear,
            doorway_feasible=feasible,
        ))
    edges.sort(key=lambda e: (e.room_a_id, e.room_b_id))
    return PlacedCandidate(
        source_refined_candidate_signature=signature,
        placed_rooms=placed_rooms,
        shared_edges=tuple(edges),
        placement_algorithm="slicing_kd_tree",
        envelope_width_m=envelope[0],
        envelope_depth_m=envelope[1],
    )


def _good_cand(sig="cand_1"):
    """A minimal 2-room candidate that produces a SuccessfulDoorPlacement."""
    return _make_placed_candidate(
        signature=sig,
        rooms_spec=[
            ("AAA_entry", "main_entrance", 0.0, 0.0, 3.0, 3.0),
            ("living_01", "living", 3.0, 0.0, 5.0, 5.0),
        ],
        edges_spec=[
            ("AAA_entry", "living_01", "vertical", 3.0, 0.9, True),
        ],
    )


def _bad_cand(sig="bad_cand"):
    """A candidate with no entry room → EntryRoomNotFoundError."""
    return _make_placed_candidate(
        signature=sig,
        rooms_spec=[
            ("bedroom_01", "bedroom", 0.0, 0.0, 3.0, 3.0),
            ("bedroom_02", "bedroom", 3.0, 0.0, 3.0, 3.0),
        ],
        edges_spec=[
            ("bedroom_01", "bedroom_02", "vertical", 2.0, 0.9, True),
        ],
    )


# ──────────────────────────────────────────────────────────────────────
# CandidateProvenanceEntry — dataclass validation
# ──────────────────────────────────────────────────────────────────────


def test_candidate_provenance_entry_success_minimal():
    e = CandidateProvenanceEntry(
        candidate_signature="c1",
        outcome="success",
        wallclock_seconds=0.05,
        phase_reached="phaseF",
        n_rooms=2,
        n_doors_placed=1,
        n_advisory_flags=0,
    )
    assert e.failure_record is None
    # Frozen + hashable.
    assert hash(e) == hash(e)
    with pytest.raises(Exception):
        e.outcome = "failure"  # type: ignore[misc]


def test_candidate_provenance_entry_empty_signature_rejected():
    with pytest.raises(ValueError, match="must be non-empty"):
        CandidateProvenanceEntry(
            candidate_signature="",
            outcome="success",
            wallclock_seconds=0.05,
            phase_reached="phaseF",
            n_rooms=2,
            n_doors_placed=1,
            n_advisory_flags=0,
        )


def test_candidate_provenance_entry_invalid_outcome_rejected():
    with pytest.raises(ValueError, match="must be 'success' or 'failure'"):
        CandidateProvenanceEntry(
            candidate_signature="c1",
            outcome="completed",
            wallclock_seconds=0.05,
            phase_reached="phaseF",
            n_rooms=2,
            n_doors_placed=1,
            n_advisory_flags=0,
        )


def test_candidate_provenance_entry_negative_wallclock_rejected():
    with pytest.raises(ValueError, match="must be >= 0"):
        CandidateProvenanceEntry(
            candidate_signature="c1",
            outcome="success",
            wallclock_seconds=-0.001,
            phase_reached="phaseF",
            n_rooms=2,
            n_doors_placed=1,
            n_advisory_flags=0,
        )


def test_candidate_provenance_entry_failure_requires_record():
    """Inv: outcome='failure' requires failure_record present."""
    with pytest.raises(ValueError, match="required when outcome"):
        CandidateProvenanceEntry(
            candidate_signature="c1",
            outcome="failure",
            wallclock_seconds=0.05,
            phase_reached="phaseA",
            n_rooms=2,
            n_doors_placed=0,
            n_advisory_flags=0,
            failure_record=None,
        )


def test_candidate_provenance_entry_success_forbids_record():
    """Inv: outcome='success' forbids failure_record present."""
    rec = FailureRecord(
        candidate_signature="c1",
        error_type="EntryRoomNotFoundError",
        error_message="test",
        phase="phaseA",
    )
    with pytest.raises(ValueError, match="must be None"):
        CandidateProvenanceEntry(
            candidate_signature="c1",
            outcome="success",
            wallclock_seconds=0.05,
            phase_reached="phaseF",
            n_rooms=2,
            n_doors_placed=1,
            n_advisory_flags=0,
            failure_record=rec,
        )


# ──────────────────────────────────────────────────────────────────────
# DoorPlacementProvenance — dataclass validation
# ──────────────────────────────────────────────────────────────────────


def test_door_placement_provenance_empty_minimal():
    p = DoorPlacementProvenance(
        c13_version=C13_VERSION,
        c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
        advisory_schema_version=ADVISORY_SCHEMA_VERSION,
        cache_key="abc",
        total_wallclock_seconds=0.0,
        candidates=(),
        n_successful=0,
        n_failed=0,
    )
    assert p.candidates == ()


def test_door_placement_provenance_empty_version_rejected():
    with pytest.raises(ValueError, match="c13_version"):
        DoorPlacementProvenance(
            c13_version="",
            c13_edge_protocol_version=1,
            advisory_schema_version=1,
            cache_key="abc",
            total_wallclock_seconds=0.0,
            candidates=(),
            n_successful=0,
            n_failed=0,
        )


def test_door_placement_provenance_empty_cache_key_rejected():
    with pytest.raises(ValueError, match="cache_key"):
        DoorPlacementProvenance(
            c13_version=C13_VERSION,
            c13_edge_protocol_version=1,
            advisory_schema_version=1,
            cache_key="",
            total_wallclock_seconds=0.0,
            candidates=(),
            n_successful=0,
            n_failed=0,
        )


def test_door_placement_provenance_candidates_must_be_sorted():
    e_a = CandidateProvenanceEntry(
        candidate_signature="cand_a",
        outcome="success", wallclock_seconds=0.0, phase_reached="phaseF",
        n_rooms=2, n_doors_placed=1, n_advisory_flags=0,
    )
    e_b = CandidateProvenanceEntry(
        candidate_signature="cand_b",
        outcome="success", wallclock_seconds=0.0, phase_reached="phaseF",
        n_rooms=2, n_doors_placed=1, n_advisory_flags=0,
    )
    # Correct order.
    DoorPlacementProvenance(
        c13_version=C13_VERSION,
        c13_edge_protocol_version=1,
        advisory_schema_version=1,
        cache_key="abc",
        total_wallclock_seconds=0.0,
        candidates=(e_a, e_b),
        n_successful=2,
        n_failed=0,
    )
    # Reversed.
    with pytest.raises(ValueError, match="must be sorted"):
        DoorPlacementProvenance(
            c13_version=C13_VERSION,
            c13_edge_protocol_version=1,
            advisory_schema_version=1,
            cache_key="abc",
            total_wallclock_seconds=0.0,
            candidates=(e_b, e_a),
            n_successful=2,
            n_failed=0,
        )


def test_door_placement_provenance_counts_must_agree():
    e = CandidateProvenanceEntry(
        candidate_signature="c1",
        outcome="success", wallclock_seconds=0.0, phase_reached="phaseF",
        n_rooms=2, n_doors_placed=1, n_advisory_flags=0,
    )
    # n_successful disagrees with candidate breakdown.
    with pytest.raises(ValueError, match="n_successful"):
        DoorPlacementProvenance(
            c13_version=C13_VERSION,
            c13_edge_protocol_version=1,
            advisory_schema_version=1,
            cache_key="abc",
            total_wallclock_seconds=0.0,
            candidates=(e,),
            n_successful=0,  # wrong
            n_failed=0,
        )


# ──────────────────────────────────────────────────────────────────────
# place_doors_with_provenance — end-to-end behavior
# ──────────────────────────────────────────────────────────────────────


def test_place_doors_with_provenance_returns_tuple():
    cand = _good_cand()
    result, prov = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    assert isinstance(result, DoorPlacementBatchResult)
    assert isinstance(prov, DoorPlacementProvenance)


def test_place_doors_with_provenance_batch_matches_place_doors():
    """Without provenance: place_doors() returns the same batch result
    (modulo wallclock-driven differences which aren't output-defining).

    Inv: cache_key, doors, advisory_flags all byte-equal.
    """
    cand = _good_cand()
    plain = place_doors(
        placed_candidates=(cand,),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    result, _prov = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    assert plain.cache_key == result.cache_key
    assert plain.successful == result.successful
    assert plain.failed == result.failed


def test_place_doors_with_provenance_empty_batch():
    result, prov = place_doors_with_provenance(
        placed_candidates=(),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    assert result.successful == ()
    assert result.failed == ()
    assert prov.candidates == ()
    assert prov.n_successful == 0
    assert prov.n_failed == 0


def test_place_doors_with_provenance_success_entry():
    cand = _good_cand("cand_AAA")
    result, prov = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    assert prov.n_successful == 1
    assert prov.n_failed == 0
    assert len(prov.candidates) == 1
    e = prov.candidates[0]
    assert e.candidate_signature == "cand_AAA"
    assert e.outcome == "success"
    assert e.phase_reached == "phaseF"
    assert e.failure_record is None
    assert e.n_rooms == 2
    assert e.n_doors_placed == 1
    assert e.wallclock_seconds >= 0.0


def test_place_doors_with_provenance_warn_mode_failure_entry():
    cand = _bad_cand("cand_BAD")
    config = DoorPlacementConfig(strict_mode=False)
    result, prov = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=config,
        c12_cache_key="c12_test_key",
    )
    assert prov.n_successful == 0
    assert prov.n_failed == 1
    e = prov.candidates[0]
    assert e.outcome == "failure"
    assert e.phase_reached == "phaseA"  # EntryRoomNotFoundError is phaseA
    assert e.failure_record is not None
    assert e.failure_record.error_type == "EntryRoomNotFoundError"
    # Cross-reference into result.failed.
    assert (
        result.failed[0].failure_record == e.failure_record
    )


def test_place_doors_with_provenance_strict_mode_raises():
    cand = _bad_cand()
    config = DoorPlacementConfig(strict_mode=True)
    with pytest.raises(EntryRoomNotFoundError):
        place_doors_with_provenance(
            placed_candidates=(cand,),
            config=config,
            c12_cache_key="c12_test_key",
        )


def test_place_doors_with_provenance_local_error_halts():
    """LocalPlacementError halts regardless of strict_mode — no
    provenance returned."""
    class BadCandidate:
        placed_rooms = ()
        shared_edges = ()
        # Missing source_refined_candidate_signature.
    config = DoorPlacementConfig(strict_mode=False)
    with pytest.raises(UpstreamSchemaDriftError):
        place_doors_with_provenance(
            placed_candidates=(BadCandidate(),),
            config=config,
            c12_cache_key="c12_test_key",
        )


def test_place_doors_with_provenance_candidates_sorted_lex_asc():
    cand_b = _good_cand("cand_BBB")
    cand_a = _good_cand("cand_AAA")
    # Pass in reverse.
    _result, prov = place_doors_with_provenance(
        placed_candidates=(cand_b, cand_a),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    sigs = [e.candidate_signature for e in prov.candidates]
    assert sigs == sorted(sigs)


def test_place_doors_with_provenance_replay_structural_fields_byte_equal():
    """Inv D7 caveat: cache_key, candidates' structural fields
    (excluding wallclock) match across runs. wallclock_seconds may
    vary."""
    cand = _good_cand("cand_X")
    config = DoorPlacementConfig()
    _r1, p1 = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=config,
        c12_cache_key="c12_test_key",
    )
    _r2, p2 = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=config,
        c12_cache_key="c12_test_key",
    )
    # Cache key + counts + version are byte-equal.
    assert p1.cache_key == p2.cache_key
    assert p1.c13_version == p2.c13_version
    assert p1.n_successful == p2.n_successful
    assert p1.n_failed == p2.n_failed
    # Per-candidate structural fields match.
    assert len(p1.candidates) == len(p2.candidates)
    for c1, c2 in zip(p1.candidates, p2.candidates):
        assert c1.candidate_signature == c2.candidate_signature
        assert c1.outcome == c2.outcome
        assert c1.phase_reached == c2.phase_reached
        assert c1.n_rooms == c2.n_rooms
        assert c1.n_doors_placed == c2.n_doors_placed
        assert c1.n_advisory_flags == c2.n_advisory_flags
        assert c1.failure_record == c2.failure_record


def test_place_doors_with_provenance_telemetry_still_works():
    """Provenance API does not interfere with telemetry sink."""
    sink = InMemoryTelemetrySink()
    cand = _good_cand()
    config = DoorPlacementConfig(telemetry_sink=sink)
    place_doors_with_provenance(
        placed_candidates=(cand,),
        config=config,
        c12_cache_key="c12_test_key",
    )
    # Per v0.4 C5: PhaseDConvergenceEvent emitted mandatorily.
    assert len(sink.events_of_type(PhaseDConvergenceEvent)) == 1


def test_place_doors_with_provenance_version_constants_match_batch():
    cand = _good_cand()
    result, prov = place_doors_with_provenance(
        placed_candidates=(cand,),
        config=DoorPlacementConfig(),
        c12_cache_key="c12_test_key",
    )
    assert prov.c13_version == result.c13_version
    assert prov.c13_edge_protocol_version == result.c13_edge_protocol_version
    assert prov.advisory_schema_version == result.advisory_schema_version
    assert prov.cache_key == result.cache_key
