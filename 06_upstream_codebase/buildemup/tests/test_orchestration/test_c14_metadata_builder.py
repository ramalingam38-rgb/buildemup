"""Unit tests for the C12 + C13 → C14 metadata builder (S57 #6).

Most behavior is exercised end-to-end via the smoke tests
(`test_c14_phase_flips_to_ok_via_circulation_batch`). These unit tests
cover the edge cases the orchestrator may hit but the smoke fixture
doesn't always exercise:

  - Empty payloads (None on either side).
  - Main-entry resolution when both endpoints are non-EXTERNAL.
  - Missing signatures in C12 (defensive — should not happen but
    builder handles it gracefully).
"""
from __future__ import annotations

import pytest

from buildemup.components.c13.contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
)
from buildemup.components.c14.contracts import RoomMetadata
from buildemup.orchestration.adapters.c12_c13_to_c14 import (
    _derive_main_entry_room_id,
    build_room_metadata_by_signature,
)


# ──────────────────────────────────────────────────────────────────────
# Synthetic fixture stand-ins — keep tests independent of full chain.
# ──────────────────────────────────────────────────────────────────────


class _FakeDoor:
    def __init__(self, room_a_id: str, room_b_id: str,
                 is_main_entry: bool = False):
        self.room_a_id = room_a_id
        self.room_b_id = room_b_id
        self.is_main_entry = is_main_entry


class _FakeRoom:
    def __init__(self, room_id: str, category: str):
        self.room_id = room_id
        self.category = category


class _FakePlacement:
    def __init__(self, signature: str, doors):
        self.source_placed_candidate_signature = signature
        self.doors = doors


class _FakeC13Batch:
    def __init__(self, successful):
        self.successful = successful


class _FakeC12Candidate:
    def __init__(self, signature: str, placed_rooms):
        self.source_refined_candidate_signature = signature
        self.placed_rooms = placed_rooms


class _FakeC12Batch:
    def __init__(self, placed_candidates):
        self.placed_candidates = placed_candidates


# ──────────────────────────────────────────────────────────────────────
# _derive_main_entry_room_id
# ──────────────────────────────────────────────────────────────────────


def test_main_entry_external_to_room_picks_internal_endpoint():
    """Standard main-entry door: EXTERNAL ↔ entry_room. Internal
    endpoint is the main entry room."""
    placement = _FakePlacement(
        signature="sig:standard",
        doors=[
            _FakeDoor(
                EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
                "entry_01",
                is_main_entry=True,
            ),
            _FakeDoor("entry_01", "living_01"),
        ],
    )
    # room_a is EXTERNAL; non-EXTERNAL endpoint is room_b
    assert _derive_main_entry_room_id(placement) == "entry_01"


def test_main_entry_room_a_external_resolves_to_room_b():
    """When room_a is EXTERNAL, room_b is the entry room."""
    placement = _FakePlacement(
        signature="sig:room_a_external",
        doors=[
            _FakeDoor(
                EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
                "lobby_01",
                is_main_entry=True,
            ),
        ],
    )
    assert _derive_main_entry_room_id(placement) == "lobby_01"


def test_main_entry_internal_to_internal_picks_room_a():
    """Degenerate case: both endpoints non-EXTERNAL. Per C14 Inv E7
    deterministic tiebreak, room_a wins (it's already lex-ASC-smaller
    by C13's canonical ordering)."""
    placement = _FakePlacement(
        signature="sig:degenerate",
        doors=[
            _FakeDoor("foyer_01", "living_01", is_main_entry=True),
        ],
    )
    assert _derive_main_entry_room_id(placement) == "foyer_01"


def test_main_entry_none_when_no_main_entry_door_present():
    """Defensive: if a placement somehow lacks an is_main_entry door,
    return None rather than raising."""
    placement = _FakePlacement(
        signature="sig:no_main",
        doors=[_FakeDoor("a", "b", is_main_entry=False)],
    )
    assert _derive_main_entry_room_id(placement) is None


# ──────────────────────────────────────────────────────────────────────
# build_room_metadata_by_signature
# ──────────────────────────────────────────────────────────────────────


def test_builder_returns_empty_when_either_payload_missing():
    """Either side missing → empty dict; orchestrator handles upstream."""
    assert build_room_metadata_by_signature(
        c12_payload=None, c13_payload=object(),
    ) == {}
    assert build_room_metadata_by_signature(
        c12_payload=object(), c13_payload=None,
    ) == {}


def test_builder_pairs_c13_placement_with_c12_rooms():
    """Happy path: one C12 candidate + one C13 placement → metadata."""
    c12 = _FakeC12Batch(placed_candidates=[
        _FakeC12Candidate(
            signature="sig:01",
            placed_rooms=[
                _FakeRoom("entry_01", "main_entrance"),
                _FakeRoom("bedroom_01", "bedroom"),
            ],
        ),
    ])
    c13 = _FakeC13Batch(successful=[
        _FakePlacement(
            signature="sig:01",
            doors=[
                _FakeDoor(
                    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
                    "entry_01",
                    is_main_entry=True,
                ),
                _FakeDoor("entry_01", "bedroom_01"),
            ],
        ),
    ])
    metadata = build_room_metadata_by_signature(c12_payload=c12, c13_payload=c13)
    assert "sig:01" in metadata
    by_id = {m.room_id: m for m in metadata["sig:01"]}
    assert by_id["entry_01"].is_main_entry_room is True
    assert by_id["entry_01"].category == "main_entrance"
    assert by_id["bedroom_01"].is_main_entry_room is False
    assert by_id["bedroom_01"].category == "bedroom"
    for m in metadata["sig:01"]:
        assert isinstance(m, RoomMetadata)


def test_builder_skips_signatures_missing_from_c12():
    """If C13 has a placement signature C12 doesn't know about, the
    builder skips it (C14's batch will then surface this signature as
    GraphInconsistencyError when its metadata key is missing — which
    is the correct error surface, not silent success)."""
    c12 = _FakeC12Batch(placed_candidates=[
        _FakeC12Candidate(
            signature="sig:present",
            placed_rooms=[_FakeRoom("entry_01", "main_entrance")],
        ),
    ])
    c13 = _FakeC13Batch(successful=[
        _FakePlacement(
            signature="sig:present",
            doors=[_FakeDoor(EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
                             "entry_01", is_main_entry=True)],
        ),
        _FakePlacement(
            signature="sig:orphan_from_c12",
            doors=[_FakeDoor(EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
                             "entry_02", is_main_entry=True)],
        ),
    ])
    metadata = build_room_metadata_by_signature(c12_payload=c12, c13_payload=c13)
    assert "sig:present" in metadata
    assert "sig:orphan_from_c12" not in metadata
