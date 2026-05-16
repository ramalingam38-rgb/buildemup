"""
C11a Sub-session 3 tests — Tier B operators.

Per § 6 v0.4 carry: Tier B operators (M6, M7a/b family, M8) — each
gets ~2 tests (1 happy + 1 invalidation/forbidden-delta). Plus shared
mechanics (apply_tier_b_operator wrapping, output_family_id derivation,
variant_id determinism on cache replays).
"""
from __future__ import annotations

from typing import ClassVar

from buildemup.components.c11a import (
    DeepMutationPipeline,
    DeltaKey,
    MutationLineageDepth,
    MutationOperator,
    StubUpstreamRegenerator,
    TopologyFamilyTransitionPolicy,
    TopologyMutationConfig,
    apply_m6_wet_rotate,
    apply_m7a_grid_3_3,
    apply_m7b_grid_2_7,
    apply_m8_vert_rearr,
)


_TEST_SOURCE = "test-source"
_TEST_SIG = "test-signature"
_TEST_FAMILY = "central_spine"


def _pipeline_with_outcome(
    *,
    return_value="regen",
    delta_keys=None,
    raise_exc=None,
) -> DeepMutationPipeline:
    stub = StubUpstreamRegenerator(
        return_value=return_value,
        delta_keys=delta_keys,
        raise_on_regenerate=raise_exc,
    )
    return DeepMutationPipeline(upstream=stub)


# =============================================================================
# M6 — wet-wall rotate
# =============================================================================


def test_m6_happy_path() -> None:
    pipeline = _pipeline_with_outcome()
    result = apply_m6_wet_rotate(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M6_WET_ROTATE
    assert result.lineage_depth == MutationLineageDepth.REGENERATIVE_TRANSFORM
    assert result.family_transition_policy == TopologyFamilyTransitionPolicy.PRESERVES_FAMILY
    assert result.output_family_id == _TEST_FAMILY


def test_m6_invalidation_forbidden_delta() -> None:
    """Stub returns delta with GEO_ROOM_AREA — forbidden for M6 (room
    areas must not change during wet-wall rotation)."""
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.GEO_ROOM_AREA,),
    )
    result = apply_m6_wet_rotate(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is not None
    assert "forbidden_delta_key" in result.rejection_invariant_id


# =============================================================================
# M7a / M7b — grid scale
# =============================================================================


def test_m7a_happy_path() -> None:
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.GEO_GRID_BAY_SIZE, DeltaKey.GEO_ROOM_AREA),
    )
    result = apply_m7a_grid_3_3(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M7A_GRID_3_3


def test_m7b_happy_path() -> None:
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.GEO_GRID_BAY_SIZE, DeltaKey.GEO_ROOM_AREA),
    )
    result = apply_m7b_grid_2_7(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M7B_GRID_2_7


def test_m7_invalidation_changes_room_count() -> None:
    """M7 forbids META_ROOM_COUNT — if regeneration changes room count
    (e.g., re-tiled grid couldn't fit one of the rooms), reject."""
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.GEO_GRID_BAY_SIZE, DeltaKey.META_ROOM_COUNT),
    )
    result = apply_m7a_grid_3_3(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is False


# =============================================================================
# M8 — multi-floor vertical rearrange
# =============================================================================


def test_m8_happy_path() -> None:
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.MULTI_MASTER_BR_FLOOR, DeltaKey.MULTI_FLOOR_ASSIGNMENT),
    )
    result = apply_m8_vert_rearr(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M8_VERT_REARR


def test_m8_invalidation_changes_room_area() -> None:
    """M8 forbids GEO_ROOM_AREA — vertical rearrangement shouldn't
    cascade into room sizing changes at this tier."""
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.MULTI_MASTER_BR_FLOOR, DeltaKey.GEO_ROOM_AREA),
    )
    result = apply_m8_vert_rearr(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is False


# =============================================================================
# Per-candidate upstream error → invalid result
# =============================================================================


class _SyntheticPerCandidate(Exception):
    severity_tier: ClassVar[str] = "per_candidate"


def test_tier_b_per_candidate_upstream_error_yields_invalid() -> None:
    """Per-candidate severity error from upstream → invalid result with
    no upstream_regeneration_delta."""
    pipeline = _pipeline_with_outcome(
        raise_exc=_SyntheticPerCandidate("upstream rejected the regen"),
    )
    result = apply_m6_wet_rotate(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    assert result.valid is False
    assert result.upstream_regeneration_delta == ()


# =============================================================================
# Cache replay
# =============================================================================


def test_tier_b_cache_replay_on_second_call() -> None:
    """Two apply_m6 calls with same identity hit the cache; the second
    result is structurally identical to the first."""
    pipeline = _pipeline_with_outcome()
    args = dict(
        source=_TEST_SOURCE, pipeline=pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id=_TEST_FAMILY,
    )
    first = apply_m6_wet_rotate(**args)
    second = apply_m6_wet_rotate(**args)
    # Both valid, same lineage, same delta — atomicity guarantees
    # byte-equal pipeline result; the wrapper-derived variant_id is
    # deterministic too.
    assert first.valid is True and second.valid is True
    assert first.topology_variant_id == second.topology_variant_id
    assert first.lineage_depth == second.lineage_depth


# =============================================================================
# Output family policies
# =============================================================================


def test_m6_preserves_family() -> None:
    pipeline = _pipeline_with_outcome()
    result = apply_m6_wet_rotate(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id="strip",
    )
    assert result.output_family_id == "strip"  # PRESERVES_FAMILY


def test_m7_preserves_family() -> None:
    pipeline = _pipeline_with_outcome(
        delta_keys=(DeltaKey.GEO_GRID_BAY_SIZE, DeltaKey.GEO_ROOM_AREA),
    )
    result = apply_m7a_grid_3_3(
        _TEST_SOURCE, pipeline,
        config=TopologyMutationConfig(),
        source_signature=_TEST_SIG, source_family_id="courtyard",
    )
    assert result.output_family_id == "courtyard"
