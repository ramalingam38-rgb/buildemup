"""
C11a Sub-session 3 tests — classify_lineage_depth.

Per spec § 2.3 + Inv 21 + Inv 23: classifier reads actual delta vs
operator's expected_delta_schema and emits one of:
  - REGENERATIVE_TRANSFORM (within declared scope)
  - EMERGENT_REGENERATION (delta exceeds declared scope)
  - REJECT (forbidden_keys hit; lineage_depth = None)
"""
from __future__ import annotations

from buildemup.components.c11a import (
    DeltaKey,
    LineageClassification,
    MutationLineageDepth,
    OperatorExpectedDeltaSchema,
    classify_lineage_depth,
)


def _wet_wall_schema() -> OperatorExpectedDeltaSchema:
    """Mirror M6's schema (PLUMB_WET_WALL_ASSIGNMENT expected, etc.)."""
    return OperatorExpectedDeltaSchema(
        expected=frozenset({DeltaKey.PLUMB_WET_WALL_ASSIGNMENT}),
        allowed_secondary=frozenset({
            DeltaKey.PLUMB_TRAP_ARM_DISTANCES,
            DeltaKey.PLUMB_RISER_GROUPS,
        }),
        forbidden=frozenset({
            DeltaKey.GEO_ROOM_AREA,
            DeltaKey.GEO_ROOM_POSITION_X,
        }),
    )


# =============================================================================
# REGENERATIVE_TRANSFORM
# =============================================================================


def test_regenerative_transform_when_actual_subset_of_expected() -> None:
    """Actual delta fully ⊆ expected → REGENERATIVE_TRANSFORM."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.PLUMB_WET_WALL_ASSIGNMENT,),
        schema,
    )
    assert result.lineage_depth == MutationLineageDepth.REGENERATIVE_TRANSFORM
    assert result.rejection_reason is None
    assert result.rejected_by_keys == ()
    assert result.emergent_keys == ()


def test_regenerative_transform_when_actual_subset_of_expected_plus_allowed() -> None:
    """expected ∪ allowed_secondary covers the actual delta →
    still REGENERATIVE_TRANSFORM."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.PLUMB_WET_WALL_ASSIGNMENT, DeltaKey.PLUMB_TRAP_ARM_DISTANCES),
        schema,
    )
    assert result.lineage_depth == MutationLineageDepth.REGENERATIVE_TRANSFORM


def test_regenerative_transform_when_empty_delta() -> None:
    """No upstream change → vacuously REGENERATIVE_TRANSFORM."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth((), schema)
    assert result.lineage_depth == MutationLineageDepth.REGENERATIVE_TRANSFORM


# =============================================================================
# EMERGENT_REGENERATION
# =============================================================================


def test_emergent_when_extra_keys_outside_declared_scope() -> None:
    """Actual delta has keys NOT in expected ∪ allowed_secondary →
    EMERGENT_REGENERATION."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.PLUMB_WET_WALL_ASSIGNMENT, DeltaKey.ZONE_ASSIGNMENTS),
        schema,
    )
    assert result.lineage_depth == MutationLineageDepth.EMERGENT_REGENERATION
    assert DeltaKey.ZONE_ASSIGNMENTS in result.emergent_keys


def test_emergent_only_extra_keys_no_expected() -> None:
    """Even if the operator's expected delta DIDN'T fire, but other
    keys did, the classification is EMERGENT (the upstream regeneration
    drove unexpected effects)."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.ZONE_ASSIGNMENTS,),  # not in expected, not in allowed, not forbidden
        schema,
    )
    assert result.lineage_depth == MutationLineageDepth.EMERGENT_REGENERATION
    assert result.emergent_keys == (DeltaKey.ZONE_ASSIGNMENTS,)


def test_emergent_keys_sorted_lex_asc() -> None:
    """emergent_keys are returned sorted by .value for deterministic
    ordering in provenance/diagnostics."""
    schema = OperatorExpectedDeltaSchema(
        expected=frozenset(),
        allowed_secondary=frozenset(),
        forbidden=frozenset(),
    )
    result = classify_lineage_depth(
        (DeltaKey.ZONE_ASSIGNMENTS, DeltaKey.ADJ_EDGES, DeltaKey.GEO_ROOM_AREA),
        schema,
    )
    values = [k.value for k in result.emergent_keys]
    assert values == sorted(values)


# =============================================================================
# REJECT — forbidden hit
# =============================================================================


def test_reject_on_forbidden_key() -> None:
    """Any forbidden_keys hit → lineage_depth=None + rejection_reason set."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.PLUMB_WET_WALL_ASSIGNMENT, DeltaKey.GEO_ROOM_AREA),
        schema,
    )
    assert result.lineage_depth is None
    assert result.rejection_reason is not None
    assert "forbidden" in result.rejection_reason.lower()
    assert DeltaKey.GEO_ROOM_AREA in result.rejected_by_keys


def test_reject_with_multiple_forbidden_keys() -> None:
    """Multiple forbidden hits → all surfaced in rejected_by_keys."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.GEO_ROOM_AREA, DeltaKey.GEO_ROOM_POSITION_X),
        schema,
    )
    assert result.lineage_depth is None
    assert len(result.rejected_by_keys) == 2


def test_reject_takes_precedence_over_emergent() -> None:
    """If actual has BOTH forbidden hits AND emergent extras, the
    forbidden hit wins (REJECT short-circuits before EMERGENT
    classification)."""
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.GEO_ROOM_AREA, DeltaKey.ZONE_ASSIGNMENTS),
        schema,
    )
    assert result.lineage_depth is None
    # emergent_keys not populated when rejected
    assert result.emergent_keys == ()


# =============================================================================
# Result shape
# =============================================================================


def test_result_is_lineage_classification_instance() -> None:
    schema = _wet_wall_schema()
    result = classify_lineage_depth(
        (DeltaKey.PLUMB_WET_WALL_ASSIGNMENT,), schema,
    )
    assert isinstance(result, LineageClassification)
