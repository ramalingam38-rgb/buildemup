"""B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (S55, HIGH priority).

C12 v1.1: SharedEdge gains an `edge_type: EdgeType` field defaulting
to `EdgeType.INTERNAL`. C13 v0.3 B5 Protocol decoupled C13 from raw
C12 schema via C13ConsumesFromC12Edge; with this amendment, real C12
SharedEdge instances now satisfy the Protocol natively — C12V10EdgeAdapter
remains supported for older callers but is no longer required.

EdgeType is now sourced from c12.schema; c13.contracts re-exports it
for backwards compat.
"""
from __future__ import annotations

import pytest

from buildemup.components.c12.schema import EdgeType as C12EdgeType
from buildemup.components.c12.schema import SharedEdge
from buildemup.components.c13.contracts import (
    C13ConsumesFromC12Edge,
    EdgeType as C13EdgeType,
)


# ─────────────────────────────────────────────────────────────────────
# EdgeType is canonical in c12.schema and re-exported from c13.contracts
# ─────────────────────────────────────────────────────────────────────

def test_c12_and_c13_edge_type_are_the_same_class():
    """Source of truth is c12.schema; c13.contracts re-exports."""
    assert C12EdgeType is C13EdgeType


def test_edge_type_enum_has_four_values():
    assert {e.value for e in C12EdgeType} == {
        "internal", "external_envelope", "service", "balcony",
    }


# ─────────────────────────────────────────────────────────────────────
# SharedEdge.edge_type — defaults + explicit values
# ─────────────────────────────────────────────────────────────────────

def _make_edge(**overrides) -> SharedEdge:
    base = dict(
        room_a_id="aaa",
        room_b_id="bbb",
        axis="vertical",
        overlap_start_m=0.0,
        overlap_end_m=2.0,
        overlap_length_m=2.0,
        min_required_clear_width_m=0.9,
        doorway_feasible=True,
    )
    base.update(overrides)
    return SharedEdge(**base)


def test_shared_edge_defaults_to_internal_when_edge_type_omitted():
    """Backwards-compat: every v1.0 keyword-arg construction must
    keep working and produce edge_type=INTERNAL."""
    e = _make_edge()
    assert e.edge_type == C12EdgeType.INTERNAL


def test_shared_edge_accepts_external_envelope():
    e = _make_edge(edge_type=C12EdgeType.EXTERNAL_ENVELOPE)
    assert e.edge_type == C12EdgeType.EXTERNAL_ENVELOPE


def test_shared_edge_accepts_service():
    e = _make_edge(edge_type=C12EdgeType.SERVICE)
    assert e.edge_type == C12EdgeType.SERVICE


def test_shared_edge_accepts_balcony():
    e = _make_edge(edge_type=C12EdgeType.BALCONY)
    assert e.edge_type == C12EdgeType.BALCONY


def test_shared_edge_rejects_non_edge_type_value():
    """Type-validation guard — passing a string or other type fails."""
    with pytest.raises(ValueError, match="edge_type must be EdgeType"):
        _make_edge(edge_type="external_envelope")  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# Protocol conformance — v1.1 SharedEdge satisfies C13ConsumesFromC12Edge
# natively (no adapter needed)
# ─────────────────────────────────────────────────────────────────────

def test_shared_edge_satisfies_c13_protocol_natively():
    """v1.1 closure: a real C12 SharedEdge is now C13ConsumesFromC12Edge.
    Before this amendment, C13 needed C12V10EdgeAdapter to supply
    edge_type."""
    e = _make_edge(edge_type=C12EdgeType.EXTERNAL_ENVELOPE)
    assert isinstance(e, C13ConsumesFromC12Edge)


def test_protocol_accessors_match_field_values():
    e = _make_edge(edge_type=C12EdgeType.SERVICE)
    # The Protocol fields are direct attribute reads — verify each.
    assert e.room_a_id == "aaa"
    assert e.room_b_id == "bbb"
    assert e.axis == "vertical"
    assert e.overlap_start_m == 0.0
    assert e.overlap_end_m == 2.0
    assert e.overlap_length_m == 2.0
    assert e.min_required_clear_width_m == 0.9
    assert e.doorway_feasible is True
    assert e.edge_type == C12EdgeType.SERVICE


# ─────────────────────────────────────────────────────────────────────
# Frozen invariant survives the new field
# ─────────────────────────────────────────────────────────────────────

def test_shared_edge_remains_frozen_after_amendment():
    e = _make_edge()
    with pytest.raises((AttributeError, Exception)):
        e.edge_type = C12EdgeType.EXTERNAL_ENVELOPE  # type: ignore[misc]
