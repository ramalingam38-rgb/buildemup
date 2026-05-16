"""Tests for B-C8-SCHEMA-VERSION-CONSTANT + B-C9-SCHEMA-VERSION-CONSTANT
v0.1 amendments LOCKED via S43 directive "Lock it and start coding"
(combined LOCK + code authorization).

Consumed by C12 v0.4-A1 schema-version probe at Phase 0 step 4.
"""
from __future__ import annotations


def test_c8_corridor_zone_schema_version_present_and_v1():
    """C12 v0.4-A1 expects CORRIDOR_ZONE_SCHEMA_VERSION == 1."""
    from buildemup.components.c08.schema import CORRIDOR_ZONE_SCHEMA_VERSION
    assert CORRIDOR_ZONE_SCHEMA_VERSION == 1
    assert isinstance(CORRIDOR_ZONE_SCHEMA_VERSION, int)


def test_c8_corridor_zone_schema_version_in_all_exports():
    """The constant must be a public export for C12 to consume cleanly."""
    from buildemup.components.c08 import schema
    assert "CORRIDOR_ZONE_SCHEMA_VERSION" in schema.__all__


def test_c9_adjacency_hint_schema_version_present_and_v1():
    """C12 v0.4-A1 expects ADJACENCY_HINT_SCHEMA_VERSION == 1."""
    from buildemup.domain.adjacency_hint import ADJACENCY_HINT_SCHEMA_VERSION
    assert ADJACENCY_HINT_SCHEMA_VERSION == 1
    assert isinstance(ADJACENCY_HINT_SCHEMA_VERSION, int)


def test_c9_adjacency_hint_schema_version_in_all_exports():
    """The constant must be a public export for C12 to consume cleanly."""
    from buildemup.domain import adjacency_hint
    assert "ADJACENCY_HINT_SCHEMA_VERSION" in adjacency_hint.__all__
