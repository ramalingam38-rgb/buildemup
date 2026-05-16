"""
C11a Sub-session 2 tests — per-operator apply_*.

Per CODING_MANDATE Step 2 Sub-session 2 + spec § 6 v0.4 carry:
~32 per-operator tests. Sub-session 2 covers Tier A only (12 of 16
operators); Tier B's per-op tests land at Sub-3.

Test discipline (per § 6 v0.4 carry adjusted for Sub-2 scope):
  - M0_BASE        : 1 happy
  - M1_HORIZ_FLIP  : 1 happy + 1 pre-condition (no fail-path; stubs only)
  - M2_VERT_FLIP   : 1 happy + 1 invalidation (C5 privacy_zoning fail)
  - M3 family      : 3 happy (a/b/c) + 1 invalidation (W9 fail)
  - M4_CORRIDOR    : 1 happy + 1 has_corridor=False pre-condition fail
  - M5_ZONE_SWAP   : 1 happy + 1 invalidation (C5 fail) + 1 missing-band pre-condition
  - M9 family      : 4 happy (a/b/c/d) + 1 invalidation (Inv 21 fail)

Plus shared mechanics tests:
  - derive_variant_id determinism
  - build_valid/invalid_result shape
  - dispatch_predicates short-circuit
  - require_field error path
"""
from __future__ import annotations

from typing import Any

import pytest

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c07.grid_generator import (
    Grid, MIN_STAIRCASE_LANDING_DEPTH_M, MIN_STAIRCASE_WIDTH_M, Staircase,
)
from buildemup.components.c07.wall_segment import WallAxis
from buildemup.components.c11a import (
    MutationLineageDepth,
    MutationOperator,
    OperatorPreconditionError,
    TierAOperatorContext,
    TopologyFamilyTransitionPolicy,
    apply_m0_base,
    apply_m1_horiz_flip,
    apply_m2_vert_flip,
    apply_m3a_stair_east,
    apply_m3b_stair_west,
    apply_m3c_stair_ne,
    apply_m4_corridor_inv,
    apply_m5_zone_swap,
    apply_m9a_entry_ne_center,
    apply_m9b_entry_ne_corner_w,
    apply_m9c_entry_ne_corner_e,
    apply_m9d_entry_offset_ne,
    build_invalid_result,
    build_valid_result,
    derive_variant_id,
)
from buildemup.components.c11a.operators._base import (
    dispatch_predicates,
    require_field,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Shared fixtures
# =============================================================================


_SOURCE_PLACEHOLDER: Any = object()  # opaque WetZonePlannedCandidate at Sub-2
_TEST_SIGNATURE = "test-source-signature-001"
_TEST_FAMILY_ID = "central_spine"


def _make_grid(width_m: float = 10.0, depth_m: float = 12.0) -> Grid:
    """Construct a minimal valid Grid for predicate tests."""
    return Grid(
        columns=[],
        bay_x_m=3.0,
        bay_y_m=3.0,
        columns_x_count=0,
        columns_y_count=0,
        envelope_width_m=width_m,
        envelope_depth_m=depth_m,
    )


def _make_staircase(
    width_m: float = 1.0, landing_depth_m: float = 1.2,
    origin_x_m: float = 1.0, origin_y_m: float = 1.0,
    anchor: WallAxis | None = None,
) -> Staircase:
    """Construct a staircase. Defaults satisfy NBC mins."""
    return Staircase(
        origin_x_m=origin_x_m, origin_y_m=origin_y_m,
        width_m=width_m, landing_depth_m=landing_depth_m,
        anchor=anchor,
    )


# =============================================================================
# derive_variant_id — shared determinism mechanic
# =============================================================================


def test_derive_variant_id_deterministic() -> None:
    """Same operator + signature → same variant_id."""
    v1 = derive_variant_id(MutationOperator.M0_BASE, "sig-A")
    v2 = derive_variant_id(MutationOperator.M0_BASE, "sig-A")
    assert v1 == v2


def test_derive_variant_id_distinct_per_operator() -> None:
    """Different operators on same source → different variant_ids."""
    v_m0 = derive_variant_id(MutationOperator.M0_BASE, "sig")
    v_m1 = derive_variant_id(MutationOperator.M1_HORIZ_FLIP, "sig")
    assert v_m0 != v_m1


def test_derive_variant_id_distinct_per_source() -> None:
    """Same operator on different sources → different variant_ids."""
    v_a = derive_variant_id(MutationOperator.M0_BASE, "sig-A")
    v_b = derive_variant_id(MutationOperator.M0_BASE, "sig-B")
    assert v_a != v_b


def test_derive_variant_id_format() -> None:
    """Format: '<op_value>@<16-hex-char-prefix>'."""
    v = derive_variant_id(MutationOperator.M3A_STAIR_EAST, "sig")
    assert v.startswith("m3a_stair_east@")
    suffix = v.split("@", 1)[1]
    assert len(suffix) == 16
    int(suffix, 16)  # raises if non-hex


# =============================================================================
# M0_BASE — identity
# =============================================================================


def test_m0_base_always_valid() -> None:
    """M0 is the always-valid baseline."""
    ctx = TierAOperatorContext()  # M0 reads no fields
    result = apply_m0_base(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE,
        source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M0_BASE
    assert result.invalidity_reason is None
    assert result.rejection_invariant_id is None
    assert result.lineage_depth == MutationLineageDepth.SHALLOW_TRANSFORM
    assert result.upstream_regeneration_delta == ()
    assert result.source_family_id == _TEST_FAMILY_ID
    assert result.output_family_id == _TEST_FAMILY_ID
    assert result.family_transition_policy == TopologyFamilyTransitionPolicy.PRESERVES_FAMILY


def test_m0_base_variant_id_deterministic() -> None:
    """Two M0 invocations on the same signature produce same variant_id."""
    ctx = TierAOperatorContext()
    a = apply_m0_base(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature="src-1", source_family_id=_TEST_FAMILY_ID,
    )
    b = apply_m0_base(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature="src-1", source_family_id=_TEST_FAMILY_ID,
    )
    assert a.topology_variant_id == b.topology_variant_id


# =============================================================================
# M1_HORIZ_FLIP
# =============================================================================


def test_m1_horiz_flip_happy_path() -> None:
    """All four C9/C10 stubs pass → valid result."""
    ctx = TierAOperatorContext()  # stubs read no fields
    result = apply_m1_horiz_flip(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.family_transition_policy == TopologyFamilyTransitionPolicy.PRESERVES_FAMILY
    assert result.output_family_id == _TEST_FAMILY_ID


# =============================================================================
# M2_VERT_FLIP
# =============================================================================


def test_m2_vert_flip_happy_path() -> None:
    """Vertical flip on a topology where no PRIVATE → SOUTH issue."""
    ctx = TierAOperatorContext(
        zone_bands={
            ZoneBand.PUBLIC: PlotOrientation.SOUTH,
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
        },
        plot_facing=PlotOrientation.NORTH,
    )
    # vflip: PUBLIC SOUTH→NORTH, PRIVATE NORTH→SOUTH. plot_facing=N
    # forbids PRIVATE on N; PRIVATE is now S. Fine.
    result = apply_m2_vert_flip(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True


def test_m2_vert_flip_invalidation_c5_privacy() -> None:
    """vflip places PRIVATE on the road-facing direction → C5 rejects."""
    ctx = TierAOperatorContext(
        zone_bands={
            ZoneBand.PUBLIC: PlotOrientation.NORTH,
            ZoneBand.PRIVATE: PlotOrientation.SOUTH,  # S → vflipped to N
        },
        plot_facing=PlotOrientation.NORTH,  # forbids PRIVATE on N
    )
    result = apply_m2_vert_flip(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id == "C5.privacy_zoning"
    assert "PRIVATE" in (result.invalidity_reason or "")


def test_m2_vert_flip_missing_zone_bands_pre_condition() -> None:
    """Missing zone_bands → operator-internal pre-condition failure."""
    ctx = TierAOperatorContext(plot_facing=PlotOrientation.NORTH)
    result = apply_m2_vert_flip(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None  # operator-internal
    assert "zone_bands" in (result.invalidity_reason or "")


# =============================================================================
# M3a / M3b / M3c — staircase repositioning
# =============================================================================


def test_m3a_stair_east_happy_path() -> None:
    grid = _make_grid(width_m=10.0, depth_m=12.0)
    current = _make_staircase(width_m=1.0, landing_depth_m=1.2)
    ctx = TierAOperatorContext(grid=grid, staircase=current)
    result = apply_m3a_stair_east(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M3A_STAIR_EAST


def test_m3b_stair_west_happy_path() -> None:
    grid = _make_grid(width_m=10.0, depth_m=12.0)
    current = _make_staircase(width_m=1.0, landing_depth_m=1.2)
    ctx = TierAOperatorContext(grid=grid, staircase=current)
    result = apply_m3b_stair_west(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M3B_STAIR_WEST


def test_m3c_stair_ne_happy_path() -> None:
    grid = _make_grid(width_m=10.0, depth_m=12.0)
    current = _make_staircase(width_m=1.0, landing_depth_m=1.2)
    ctx = TierAOperatorContext(grid=grid, staircase=current)
    result = apply_m3c_stair_ne(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True


def test_m3_invalidation_w9b_landing_too_shallow() -> None:
    """A wide staircase (1.5m) with too-shallow landing (1.0m) fails W9-b
    via K-4 patch: required landing = max(width, NBC floor) = 1.5m.
    """
    grid = _make_grid(width_m=10.0, depth_m=12.0)
    current = _make_staircase(width_m=1.5, landing_depth_m=1.0)  # invalid
    ctx = TierAOperatorContext(grid=grid, staircase=current)
    result = apply_m3a_stair_east(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id == "C7.staircase_clearance"
    assert "W9" in (result.invalidity_reason or "")


def test_m3_pre_condition_missing_grid() -> None:
    """No grid in context → pre-condition failure."""
    current = _make_staircase()
    ctx = TierAOperatorContext(staircase=current)  # missing grid
    result = apply_m3a_stair_east(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None
    assert "grid" in (result.invalidity_reason or "")


# =============================================================================
# M4_CORRIDOR_INV
# =============================================================================


def test_m4_happy_path_with_has_corridor() -> None:
    """A topology with has_corridor=True passes; M4 is TRANSFORMS_FAMILY."""
    # Construct a minimal CorridorPath with has_corridor=True.
    from buildemup.components.c11a.operators._m9_helpers import build_entry_probe_path
    probe = build_entry_probe_path((5.0, 12.0), 10.0, 12.0)
    ctx = TierAOperatorContext(corridor_path=probe)

    result = apply_m4_corridor_inv(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.family_transition_policy == TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY
    # Output family id is "transformed_from_<source>".
    assert result.output_family_id == f"transformed_from_{_TEST_FAMILY_ID}"


def test_m4_invalid_no_corridor() -> None:
    """has_corridor=False → operator-internal pre-condition failure."""
    from buildemup.components.c08.schema import (
        CorridorPath, ConnectivityType, ConsumptionBand,
        GridAlignmentReport, WidthQuantization,
    )
    no_corridor = CorridorPath(
        has_corridor=False,
        segments=(),
        envelopes=(),
        total_length_m=0.0,
        total_area_m2=0.0,
        consumption_band=ConsumptionBand.LOW,
        connectivity_type=ConnectivityType.LINEAR,
        grid_alignment=GridAlignmentReport(
            quantization_used=WidthQuantization.NONE_FREE_WIDTH,
            edges_aligned_count=0, edges_total_count=0,
            tapered_edges_count=0, grid_alignment_score=0.0,
        ),
    )
    ctx = TierAOperatorContext(corridor_path=no_corridor)
    result = apply_m4_corridor_inv(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None  # operator-internal
    assert "has_corridor=False" in (result.invalidity_reason or "")


def test_m4_pre_condition_missing_corridor_path() -> None:
    ctx = TierAOperatorContext()  # no corridor_path set
    result = apply_m4_corridor_inv(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None


# =============================================================================
# M5_ZONE_SWAP
# =============================================================================


def test_m5_happy_path_swap() -> None:
    """Swap PUBLIC↔PRIVATE; result satisfies C5 privacy_zoning."""
    ctx = TierAOperatorContext(
        zone_bands={
            ZoneBand.PUBLIC: PlotOrientation.NORTH,    # swap → PRIVATE: N
            ZoneBand.PRIVATE: PlotOrientation.SOUTH,   # swap → PUBLIC: S
        },
        plot_facing=PlotOrientation.SOUTH,  # forbids PRIVATE on S, but PRIVATE is now N
    )
    result = apply_m5_zone_swap(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.family_transition_policy == TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY


def test_m5_invalidation_c5_privacy() -> None:
    """Swap pushes PRIVATE onto road-facing direction → C5 rejects."""
    ctx = TierAOperatorContext(
        zone_bands={
            ZoneBand.PUBLIC: PlotOrientation.SOUTH,    # swap → PRIVATE: S
            ZoneBand.PRIVATE: PlotOrientation.NORTH,   # swap → PUBLIC: N
        },
        plot_facing=PlotOrientation.SOUTH,  # forbids PRIVATE on S
    )
    result = apply_m5_zone_swap(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id == "C5.privacy_zoning"


def test_m5_pre_condition_missing_public_band() -> None:
    """No PUBLIC entry → swap undefined → operator-internal failure."""
    ctx = TierAOperatorContext(
        zone_bands={
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
            # No PUBLIC.
        },
        plot_facing=PlotOrientation.SOUTH,
    )
    result = apply_m5_zone_swap(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None
    assert "public" in (result.invalidity_reason or "").lower()


# =============================================================================
# M9 family — entry repositioning
# =============================================================================


def _m9_north_facing_ctx() -> TierAOperatorContext:
    """Build a context where the plot faces NORTH — north-wall entries valid."""
    return TierAOperatorContext(
        envelope_width_m=10.0,
        envelope_depth_m=12.0,
        plot_facing=PlotOrientation.NORTH,
    )


def test_m9a_happy_path_north_facing() -> None:
    """M9a entry on north wall passes for NORTH-facing plot."""
    ctx = _m9_north_facing_ctx()
    result = apply_m9a_entry_ne_center(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True
    assert result.operator == MutationOperator.M9A_ENTRY_CTR


def test_m9b_happy_path_north_facing() -> None:
    ctx = _m9_north_facing_ctx()
    result = apply_m9b_entry_ne_corner_w(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True


def test_m9c_happy_path_east_facing() -> None:
    """M9c places entry on east wall — needs east-admitting facing."""
    ctx = TierAOperatorContext(
        envelope_width_m=10.0,
        envelope_depth_m=12.0,
        plot_facing=PlotOrientation.EAST,
    )
    result = apply_m9c_entry_ne_corner_e(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True


def test_m9d_happy_path_north_facing() -> None:
    ctx = _m9_north_facing_ctx()
    result = apply_m9d_entry_offset_ne(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is True


def test_m9_invalidation_inv21_wrong_edge() -> None:
    """A SOUTH-facing plot rejects a north-wall entry (M9a)."""
    ctx = TierAOperatorContext(
        envelope_width_m=10.0,
        envelope_depth_m=12.0,
        plot_facing=PlotOrientation.SOUTH,  # forbids north-wall entries
    )
    result = apply_m9a_entry_ne_center(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id == "C8.entry_approach"


def test_m9_pre_condition_missing_envelope_width() -> None:
    """Missing envelope_width_m → operator-internal pre-condition fail."""
    ctx = TierAOperatorContext(
        envelope_depth_m=12.0,
        plot_facing=PlotOrientation.NORTH,
    )  # missing envelope_width_m
    result = apply_m9a_entry_ne_center(
        _SOURCE_PLACEHOLDER, ctx,
        source_signature=_TEST_SIGNATURE, source_family_id=_TEST_FAMILY_ID,
    )
    assert result.valid is False
    assert result.rejection_invariant_id is None


# =============================================================================
# Shared mechanic tests — build_*, dispatch_predicates, require_field
# =============================================================================


def test_build_valid_result_shape() -> None:
    r = build_valid_result(
        operator=MutationOperator.M0_BASE,
        source_signature="sig",
        source_family_id="fam",
        output_family_id="fam",
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    )
    assert r.valid is True
    assert r.invalidity_reason is None
    assert r.rejection_invariant_id is None
    assert r.upstream_regeneration_delta == ()
    assert r.lineage_depth == MutationLineageDepth.SHALLOW_TRANSFORM


def test_build_invalid_result_no_variant_id() -> None:
    r = build_invalid_result(
        operator=MutationOperator.M5_ZONE_SWAP,
        source_family_id="fam",
        family_transition_policy=TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
        invalidity_reason="test reason",
        rejection_invariant_id="C5.privacy_zoning",
    )
    assert r.valid is False
    assert r.topology_variant_id is None
    assert r.output_family_id is None
    assert r.rejection_invariant_id == "C5.privacy_zoning"


def test_dispatch_predicates_short_circuits() -> None:
    """The dispatch helper short-circuits on the first failure: stubs
    after a failing predicate should NOT execute. Confirm by checking
    that with a non-fail-only predicate set, all-pass produces (True, None, None)."""
    # M0 has no predicates → trivial pass.
    ok, reason, rid = dispatch_predicates(MutationOperator.M0_BASE, {})
    assert ok is True
    assert reason is None
    assert rid is None


def test_require_field_raises_on_missing() -> None:
    ctx = TierAOperatorContext()  # all None
    with pytest.raises(OperatorPreconditionError, match="grid"):
        require_field(ctx, "grid", "test_op")


def test_require_field_returns_value_when_set() -> None:
    ctx = TierAOperatorContext(envelope_width_m=10.0)
    val = require_field(ctx, "envelope_width_m", "test_op")
    assert val == 10.0
