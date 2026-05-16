"""Tests for ``B-C9-ADJACENCY-HINTS`` v0.1 amendment (S43).

LOCKED via S43 directive ("Let's do the dependencies on c8&c9 and code
that also"). Verifies AdjacencyHint + AdjacencyConstraintKind value
types and the FloorRoomBrief.adjacency_hints field with canonical
ordering + duplicate detection.
"""
from __future__ import annotations

import pytest

from buildemup.domain.adjacency_hint import (
    AdjacencyConstraintKind,
    AdjacencyHint,
)
from buildemup.domain.floor_brief import FloorRoomBrief


# ── AdjacencyConstraintKind enum ───────────────────────────────────────


def test_kind_has_hard_and_soft():
    assert AdjacencyConstraintKind.HARD.value == "hard"
    assert AdjacencyConstraintKind.SOFT.value == "soft"


def test_kind_is_str_enum():
    assert isinstance(AdjacencyConstraintKind.HARD, str)


# ── AdjacencyHint construction ─────────────────────────────────────────


def test_hint_construction_basic():
    h = AdjacencyHint(
        room_a_id="bathroom_1",
        room_b_id="bedroom_1",
        kind=AdjacencyConstraintKind.HARD,
    )
    assert h.room_a_id == "bathroom_1"
    assert h.kind == AdjacencyConstraintKind.HARD
    assert h.weight == 1.0  # default


def test_hint_rejects_empty_room_id():
    with pytest.raises(ValueError, match="non-empty room ids"):
        AdjacencyHint(
            room_a_id="",
            room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        )


def test_hint_rejects_same_room():
    with pytest.raises(ValueError, match="distinct rooms"):
        AdjacencyHint(
            room_a_id="bedroom_1",
            room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.SOFT,
        )


def test_hint_rejects_reverse_lex_order():
    """Canonical: room_a_id < room_b_id lex-ASC."""
    with pytest.raises(ValueError, match="canonical order"):
        AdjacencyHint(
            room_a_id="bedroom_1",
            room_b_id="bathroom_1",  # < bedroom_1 lex-ASC
            kind=AdjacencyConstraintKind.HARD,
        )


def test_hint_rejects_negative_weight():
    with pytest.raises(ValueError, match="weight"):
        AdjacencyHint(
            room_a_id="bathroom_1",
            room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.SOFT,
            weight=-0.5,
        )


def test_hint_accepts_zero_weight():
    """Zero is allowed (SOFT preference with zero priority — effectively informational)."""
    h = AdjacencyHint(
        room_a_id="bathroom_1",
        room_b_id="bedroom_1",
        kind=AdjacencyConstraintKind.SOFT,
        weight=0.0,
    )
    assert h.weight == 0.0


# ── FloorRoomBrief.adjacency_hints default behaviour ───────────────────


def _basic_brief(**kwargs) -> FloorRoomBrief:
    defaults = dict(
        bedroom_count=2,
        bathroom_count=1,
        has_kitchen=True,
        has_living=True,
        has_pooja=False,
        has_utility=False,
    )
    defaults.update(kwargs)
    return FloorRoomBrief(**defaults)


def test_brief_default_adjacency_hints_is_empty_tuple():
    """Backward compat: default empty tuple preserves byte-identical
    behaviour for every existing single-floor caller."""
    brief = _basic_brief()
    assert brief.adjacency_hints == ()
    assert isinstance(brief.adjacency_hints, tuple)


def test_brief_with_no_hints_equals_brief_with_explicit_empty():
    a = _basic_brief()
    b = _basic_brief(adjacency_hints=())
    assert a == b
    assert hash(a) == hash(b)


# ── FloorRoomBrief.adjacency_hints canonical ordering ──────────────────


def test_brief_accepts_sorted_hints():
    hints = (
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        ),
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="kitchen_1",
            kind=AdjacencyConstraintKind.SOFT,
        ),
    )
    brief = _basic_brief(adjacency_hints=hints)
    assert len(brief.adjacency_hints) == 2


def test_brief_rejects_unsorted_hints():
    hints = (
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="kitchen_1",
            kind=AdjacencyConstraintKind.SOFT,
        ),
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        ),
    )
    # b="kitchen_1" > b="bedroom_1" so the tuple is not lex-ASC sorted
    with pytest.raises(ValueError, match="sorted lex-ASC"):
        _basic_brief(adjacency_hints=hints)


def test_brief_rejects_duplicate_pair():
    hints = (
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        ),
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.SOFT,
        ),
    )
    with pytest.raises(ValueError, match="duplicate"):
        _basic_brief(adjacency_hints=hints)


# ── Hash participation ────────────────────────────────────────────────


def test_brief_hash_changes_when_hints_added():
    """Adding adjacency_hints changes the brief's hash. This is the
    cache-key-impact concern flagged in the amendment's § 7."""
    no_hints = _basic_brief()
    with_hints = _basic_brief(adjacency_hints=(
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        ),
    ))
    assert no_hints != with_hints
    assert hash(no_hints) != hash(with_hints)


def test_brief_hash_invariant_under_canonical_order():
    """Two briefs with the same hint SET (after canonicalization)
    hash identically. (Both must be already sorted; we verify
    identical sorted input yields identical hash.)"""
    hint_list = [
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="bedroom_1",
            kind=AdjacencyConstraintKind.HARD,
        ),
        AdjacencyHint(
            room_a_id="bathroom_1", room_b_id="kitchen_1",
            kind=AdjacencyConstraintKind.SOFT,
        ),
    ]
    a = _basic_brief(adjacency_hints=tuple(hint_list))
    b = _basic_brief(adjacency_hints=tuple(hint_list))
    assert a == b
    assert hash(a) == hash(b)
