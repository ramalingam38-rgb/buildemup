"""Tests for C13 v1.0 LOCKED foundational + support layer (S45 Sub-1).

Covers:
- versioning constants (C13_VERSION, protocol + advisory schema
  versions, expected upstream versions, geometric defaults)
- error hierarchy (LocalPlacementError + PerCandidatePlacementError
  subclasses; severity discrimination)
- contracts (C13ConsumesFromC12Edge Protocol; C12V10EdgeAdapter;
  EdgeType enum; structural conformance against real C12 v1.0
  SharedEdge)
- schema (AdvisoryFlag, Door, RoomDoorPreference, CausalContext,
  C13CacheKeys, ConditionalLegalityViolation, FailureRecord,
  SuccessfulDoorPlacement, FailedDoorPlacement,
  DoorPlacementBatchResult; enums)
- config (DoorPlacementConfig validation, cache-domain partitioning)
- cache_keys (Inv D18 prefix construction, geometry/advisory/full
  determinism, builder integration)

Invariants exercised at this layer (the foundational subset):
- Inv D1' (in RoomDoorPreference): min/max door bounds + v1 hard cap
- Inv D6 (in SuccessfulDoorPlacement): exactly-one-main-entry
- Inv D7 (foundational): canonical ordering + frozen-dataclass
  hashability enabling byte-equal replay
- Inv D8 (in SuccessfulDoorPlacement): doors sorted lex-ASC
- Inv D10 (in Door + Config): clear_width_m ≤ 1.5m sanity bound
- Inv D18 (in C13CacheKeys + cache_keys builders): advisory_cache_key
  contains geometry_cache_key prefix
- Inv D19 (in FailureRecord): ConditionalLegalityViolationError
  must carry ConditionalLegalityViolation provenance
- Inv D20 (in AdvisoryFlag): causal_context defaults to None at v1.0
- D14 representation (in Door): GeometricFidelity enum, not numeric
  tier

NOT covered yet (Sub-Session 2+): Phase A-F algorithmic invariants
(D2-D5, D9', D11.1-D11.4, D11.3', D12', D13, D15-D17, D21-D23);
full PBT suite; integration with C12 SharedEdge end-to-end;
adversarial corpus; semantic-conformance PBTs.
"""
from __future__ import annotations

import pytest

from buildemup.components.c13 import (
    ADVISORY_SCHEMA_VERSION,
    AdvisoryCategory,
    AdvisoryFlag,
    C12V10EdgeAdapter,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
    C13CacheKeys,
    C13ConfigurationError,
    C13ConsumesFromC12Edge,
    CausalContext,
    ConditionalLegalityViolation,
    ConditionalLegalityViolationError,
    DEFAULT_CORNER_OFFSET_M,
    DEFAULT_GRID_SNAP_M,
    Door,
    DoorPlacementBatchResult,
    DoorPlacementConfig,
    DoorPlacementError,
    DoorPositionInfeasibleError,
    EXPECTED_C12_VERSION,
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    EdgeType,
    EntryRoomNotFoundError,
    FailedDoorPlacement,
    FailureRecord,
    GeometricFidelity,
    HABITABLE_ROOM_CATEGORIES,
    HabitablePrimaryUnreachabilityError,
    LocalPlacementError,
    MAX_DOORS_PER_ROOM_V1,
    NbcBathroomKitchenAdjacencyError,
    NbcMasterBedroomAdjacencyError,
    NbcThroughBathroomRoutingError,
    PerCandidatePlacementError,
    PostResolutionUnreachabilityError,
    RoomDoorPreference,
    SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1,
    SuccessfulDoorPlacement,
    SwingArcConflictError,
    UpstreamSchemaDriftError,
    build_advisory_cache_key,
    build_c13_cache_keys,
    build_full_cache_key,
    build_geometry_cache_key,
)


# ──────────────────────────────────────────────────────────────────────
# Versioning constants
# ──────────────────────────────────────────────────────────────────────


def test_c13_version_is_v1_0():
    assert C13_VERSION == "v1.0"


def test_c13_edge_protocol_version_is_1():
    # Per v0.4 C3 — locked at v1.0.
    assert C13_EDGE_PROTOCOL_VERSION == 1


def test_advisory_schema_version_is_1():
    # Per v0.4 C8 — locked at v1.0.
    assert ADVISORY_SCHEMA_VERSION == 1


def test_max_doors_per_room_v1_is_2():
    # Per v0.4 C4 — hard cap at v1.0.
    assert MAX_DOORS_PER_ROOM_V1 == 2


def test_expected_c12_version_matches_c12():
    # Per v0.1 § 1.3 + v0.4 C3 protocol-version probe.
    from buildemup.components.c12 import C12_VERSION
    assert EXPECTED_C12_VERSION == C12_VERSION


def test_expected_c8_schema_version_matches_c8():
    from buildemup.components.c08.schema import CORRIDOR_ZONE_SCHEMA_VERSION
    assert EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION == CORRIDOR_ZONE_SCHEMA_VERSION


def test_expected_c9_schema_version_matches_c9():
    from buildemup.domain.adjacency_hint import ADJACENCY_HINT_SCHEMA_VERSION
    assert EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION == ADJACENCY_HINT_SCHEMA_VERSION


def test_default_corner_offset_is_150mm():
    # Per v0.2 A2 — Neufert ergonomic minimum.
    assert DEFAULT_CORNER_OFFSET_M == 0.15


def test_default_grid_snap_inherited_from_c12():
    # Per v0.2 A7 — must equal C12's grid resolution.
    from buildemup.components.c12 import DEFAULT_GRID_SNAP_M as C12_GRID
    assert DEFAULT_GRID_SNAP_M == C12_GRID


# ──────────────────────────────────────────────────────────────────────
# Error hierarchy
# ──────────────────────────────────────────────────────────────────────


def test_error_base_class():
    assert issubclass(LocalPlacementError, DoorPlacementError)
    assert issubclass(PerCandidatePlacementError, DoorPlacementError)


def test_local_errors_subclass_local():
    assert issubclass(UpstreamSchemaDriftError, LocalPlacementError)
    assert issubclass(C13ConfigurationError, LocalPlacementError)


def test_per_candidate_errors_subclass_per_candidate():
    for cls in (
        EntryRoomNotFoundError,
        DoorPositionInfeasibleError,
        SwingArcConflictError,
        PostResolutionUnreachabilityError,
        HabitablePrimaryUnreachabilityError,
        NbcBathroomKitchenAdjacencyError,
        NbcThroughBathroomRoutingError,
        NbcMasterBedroomAdjacencyError,
        ConditionalLegalityViolationError,
    ):
        assert issubclass(cls, PerCandidatePlacementError), cls


def test_local_and_per_candidate_are_disjoint():
    # No error class should inherit both branches.
    for cls in (
        UpstreamSchemaDriftError,
        C13ConfigurationError,
    ):
        assert not issubclass(cls, PerCandidatePlacementError)
    for cls in (
        EntryRoomNotFoundError,
        DoorPositionInfeasibleError,
        SwingArcConflictError,
        ConditionalLegalityViolationError,
    ):
        assert not issubclass(cls, LocalPlacementError)


def test_error_can_be_raised_and_caught():
    with pytest.raises(SwingArcConflictError):
        raise SwingArcConflictError("test")
    # Catchable as the per-candidate base.
    try:
        raise NbcBathroomKitchenAdjacencyError("test")
    except PerCandidatePlacementError:
        pass


def test_error_count_matches_spec():
    # 1 root (DoorPlacementError) + 2 tier-2 bases (LocalPlacementError,
    # PerCandidatePlacementError) + 2 local + 9 per-candidate = 14
    # classes. Per spec v0.1 § 5 + v0.4 § 0.0 TL;DR + v0.5 D6 + v0.6 E1.
    import buildemup.components.c13.errors as errors_mod
    error_classes = [
        cls for cls in vars(errors_mod).values()
        if isinstance(cls, type) and issubclass(cls, Exception)
        and cls is not Exception
    ]
    # Filter to C13's own errors (exclude builtins / imports).
    c13_errors = [
        cls for cls in error_classes
        if cls.__module__ == "buildemup.components.c13.errors"
    ]
    assert len(c13_errors) == 14, (
        f"Expected 14 C13 error classes (1 root + 2 tier-2 bases + "
        f"2 local + 9 per-candidate); got {len(c13_errors)}: "
        f"{[c.__name__ for c in c13_errors]}"
    )


# ──────────────────────────────────────────────────────────────────────
# Contracts: Protocol + EdgeType + C12V10EdgeAdapter
# ──────────────────────────────────────────────────────────────────────


def test_edge_type_enum_has_four_values():
    # Per v0.2 A5 + v0.3 B5.
    expected = {"internal", "external_envelope", "service", "balcony"}
    assert {member.value for member in EdgeType} == expected


def test_external_envelope_placeholder_room_id():
    # Per v0.1 § 3.1 step 2 sentinel + v0.3 B5 adapter logic.
    assert EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID == "EXTERNAL"


def _make_c12_v10_shared_edge_internal():
    """Build a real C12 v1.0 SharedEdge for adapter testing."""
    from buildemup.components.c12 import SharedEdge
    return SharedEdge(
        room_a_id="bedroom_01",
        room_b_id="corridor_01",
        axis="vertical",
        overlap_start_m=0.0,
        overlap_end_m=2.0,
        overlap_length_m=2.0,
        min_required_clear_width_m=0.9,
        doorway_feasible=True,
    )


def _make_c12_v10_shared_edge_external_via_sentinel():
    """Build a SharedEdge with the EXTERNAL placeholder room_id.

    Note: C12 SharedEdge canonical-order invariant requires
    room_a_id < room_b_id lex-ASC. "EXTERNAL" starts with capital E
    (0x45), which is lex-less than lowercase letters; so room_a_id
    must be even-lower in lex order (digit or capital A-D).
    """
    from buildemup.components.c12 import SharedEdge
    return SharedEdge(
        room_a_id="AAA_entry_room",  # lex < "EXTERNAL"
        room_b_id=EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
        axis="horizontal",
        overlap_start_m=0.0,
        overlap_end_m=1.2,
        overlap_length_m=1.2,
        min_required_clear_width_m=1.0,
        doorway_feasible=True,
    )


def test_c12_v10_adapter_wraps_internal_edge():
    edge = _make_c12_v10_shared_edge_internal()
    adapter = C12V10EdgeAdapter(edge)
    assert adapter.room_a_id == "bedroom_01"
    assert adapter.room_b_id == "corridor_01"
    assert adapter.axis == "vertical"
    assert adapter.overlap_length_m == 2.0
    assert adapter.doorway_feasible is True
    # No EXTERNAL placeholder → INTERNAL.
    assert adapter.edge_type == EdgeType.INTERNAL


def test_c12_v10_adapter_recognizes_external_placeholder():
    edge = _make_c12_v10_shared_edge_external_via_sentinel()
    adapter = C12V10EdgeAdapter(edge)
    assert adapter.edge_type == EdgeType.EXTERNAL_ENVELOPE


def test_c12_v10_adapter_rejects_incomplete_object():
    class BadEdge:
        room_a_id = "a"
        # missing room_b_id, axis, etc.
    with pytest.raises(TypeError, match="missing required"):
        C12V10EdgeAdapter(BadEdge())


def test_c12_v10_adapter_satisfies_protocol():
    # The whole point of v0.3 B5: structural typing. The wrapped C12
    # v1.0 SharedEdge alone fails the Protocol (no edge_type); the
    # adapter satisfies it.
    edge = _make_c12_v10_shared_edge_internal()
    adapter = C12V10EdgeAdapter(edge)
    # @runtime_checkable Protocol: isinstance works.
    assert isinstance(adapter, C13ConsumesFromC12Edge)


def test_c12_v10_adapter_equality_via_underlying():
    edge1 = _make_c12_v10_shared_edge_internal()
    edge2 = _make_c12_v10_shared_edge_internal()
    a1 = C12V10EdgeAdapter(edge1)
    a2 = C12V10EdgeAdapter(edge2)
    assert a1 == a2
    assert hash(a1) == hash(a2)


# ──────────────────────────────────────────────────────────────────────
# Schema: AdvisoryFlag
# ──────────────────────────────────────────────────────────────────────


def _make_advisory_flag(**overrides):
    base = dict(
        flag_kind="through_private_routing",
        affected_room_id="bedroom_01",
        category=AdvisoryCategory.CIRCULATION,
        severity="warning",
        explanation_template="Routing traverses bedroom_01 — private space.",
        deduplication_key="bedroom_01::circulation",
    )
    base.update(overrides)
    return AdvisoryFlag(**base)


def test_advisory_flag_minimal_construction():
    flag = _make_advisory_flag()
    assert flag.flag_kind == "through_private_routing"
    assert flag.causal_context is None  # Inv D20: defaults to None at v1.0.


def test_advisory_flag_invalid_kind_rejected():
    with pytest.raises(ValueError, match="flag_kind must be one of"):
        _make_advisory_flag(flag_kind="not_a_real_kind")


def test_advisory_flag_invalid_severity_rejected():
    with pytest.raises(ValueError, match="severity"):
        _make_advisory_flag(severity="totally_unfine")


def test_advisory_flag_empty_room_id_rejected():
    with pytest.raises(ValueError, match="affected_room_id"):
        _make_advisory_flag(affected_room_id="")


def test_advisory_flag_d20_causal_context_default_none():
    # Inv D20: causal_context defaults to None at v1.0.
    flag = _make_advisory_flag()
    assert flag.causal_context is None
    # Setting it to CausalContext() is forward-compat per v0.7 F2.
    flag_with_ctx = _make_advisory_flag(causal_context=CausalContext())
    assert isinstance(flag_with_ctx.causal_context, CausalContext)


def test_causal_context_is_frozen_and_hashable():
    # Per v0.6 E3 + v0.7 F2 semantic intent. Empty sentinel at v1.0.
    ctx = CausalContext()
    assert hash(ctx) == hash(CausalContext())
    with pytest.raises((AttributeError, Exception)):
        ctx.new_attr = "x"  # type: ignore[attr-defined]


def test_advisory_flag_frozen_dataclass():
    flag = _make_advisory_flag()
    with pytest.raises(Exception):  # FrozenInstanceError
        flag.severity = "info"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────
# Schema: Door
# ──────────────────────────────────────────────────────────────────────


def _make_door(**overrides):
    base = dict(
        room_a_id="bedroom_01",
        room_b_id="corridor_01",
        axis="vertical",
        position_along_edge_m=0.15,
        clear_width_m=0.9,
        swing_direction="into_room_a",
        hinge_side="start",
        leaf_thickness_m=0.04,
        is_main_entry=False,
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
    )
    base.update(overrides)
    return Door(**base)


def test_door_minimal_construction():
    door = _make_door()
    assert door.room_a_id == "bedroom_01"
    assert door.geometric_fidelity == GeometricFidelity.APPROXIMATE


def test_door_canonical_room_order_enforced():
    # Inv D8 prerequisite (canonical ordering of room ids).
    with pytest.raises(ValueError, match="canonical order"):
        _make_door(room_a_id="zzz", room_b_id="aaa")


def test_door_inv_d10_clear_width_sanity_bound():
    # Inv D10: clear_width_m ≤ 1.5m at v1.
    with pytest.raises(ValueError, match="Inv D10"):
        _make_door(clear_width_m=1.6)


def test_door_invalid_swing_direction_rejected():
    with pytest.raises(ValueError, match="swing_direction"):
        _make_door(swing_direction="sideways")


def test_door_invalid_hinge_side_rejected():
    with pytest.raises(ValueError, match="hinge_side"):
        _make_door(hinge_side="middle")


def test_door_negative_position_rejected():
    with pytest.raises(ValueError, match="position_along_edge_m"):
        _make_door(position_along_edge_m=-0.01)


def test_door_zero_clear_width_rejected():
    with pytest.raises(ValueError, match="clear_width_m must be positive"):
        _make_door(clear_width_m=0.0)


def test_door_geometric_fidelity_default_approximate_at_v1():
    # Inv D14: geometric_fidelity is the enum; v1.0 default is
    # APPROXIMATE. v0.4 C6 renamed from numeric Tier 1.
    door = _make_door()
    assert door.geometric_fidelity == GeometricFidelity.APPROXIMATE


# ──────────────────────────────────────────────────────────────────────
# Schema: RoomDoorPreference (Inv D1')
# ──────────────────────────────────────────────────────────────────────


def test_room_door_preference_default_min_max_one():
    pref = RoomDoorPreference(room_id="bedroom_01")
    assert pref.min_doors == 1
    assert pref.max_doors == 1
    assert pref.secondary_door_preference == "none"


def test_room_door_preference_max_doors_hard_cap():
    # Inv D1' + v0.4 C4: max_doors ≤ MAX_DOORS_PER_ROOM_V1 = 2.
    with pytest.raises(ValueError, match="hard cap"):
        RoomDoorPreference(room_id="living_01", min_doors=2, max_doors=3)


def test_room_door_preference_min_doors_must_be_at_least_one():
    with pytest.raises(ValueError, match="min_doors"):
        RoomDoorPreference(room_id="bedroom_01", min_doors=0)


def test_room_door_preference_max_must_be_ge_min():
    with pytest.raises(ValueError, match="max_doors"):
        RoomDoorPreference(room_id="bedroom_01", min_doors=2, max_doors=1)


def test_room_door_preference_secondary_kind_validated():
    with pytest.raises(ValueError, match="secondary_door_preference"):
        RoomDoorPreference(
            room_id="kitchen_01",
            max_doors=2,
            secondary_door_preference="banana",  # type: ignore[arg-type]
        )


# ──────────────────────────────────────────────────────────────────────
# Schema: C13CacheKeys (Inv D18 prefix rule)
# ──────────────────────────────────────────────────────────────────────


def test_c13_cache_keys_basic_construction():
    keys = C13CacheKeys(
        geometry_cache_key="abc123",
        advisory_cache_key="abc123::def456",
        full_cache_key="ffff",
    )
    assert keys.geometry_cache_key == "abc123"


def test_c13_cache_keys_d18_prefix_enforced():
    # Inv D18: advisory_cache_key.startswith(geometry_cache_key).
    with pytest.raises(ValueError, match="Inv D18"):
        C13CacheKeys(
            geometry_cache_key="abc123",
            advisory_cache_key="xyz999",  # does not start with abc123
            full_cache_key="ffff",
        )


def test_c13_cache_keys_empty_geometry_rejected():
    with pytest.raises(ValueError, match="geometry_cache_key"):
        C13CacheKeys(
            geometry_cache_key="",
            advisory_cache_key="::x",
            full_cache_key="x",
        )


# ──────────────────────────────────────────────────────────────────────
# Schema: ConditionalLegalityViolation (Inv D19 provenance)
# ──────────────────────────────────────────────────────────────────────


def test_conditional_legality_violation_basic():
    v = ConditionalLegalityViolation(
        invariant_id="D11.3",
        violated_path=("bedroom_01", "kitchen_01", "living_01"),
        alternative_path=("bedroom_01", "corridor_01", "living_01"),
        alternative_path_length_grid_units=3,
    )
    assert v.invariant_id == "D11.3"


def test_conditional_legality_violation_paths_require_two_rooms():
    with pytest.raises(ValueError, match="violated_path"):
        ConditionalLegalityViolation(
            invariant_id="D11.3",
            violated_path=("only_one",),
            alternative_path=("a", "b"),
            alternative_path_length_grid_units=1,
        )
    with pytest.raises(ValueError, match="alternative_path"):
        ConditionalLegalityViolation(
            invariant_id="D11.3",
            violated_path=("a", "b"),
            alternative_path=("only_one",),
            alternative_path_length_grid_units=1,
        )


# ──────────────────────────────────────────────────────────────────────
# Schema: FailureRecord (Inv D19 provenance discipline)
# ──────────────────────────────────────────────────────────────────────


def test_failure_record_basic_construction():
    rec = FailureRecord(
        candidate_signature="cand_abc",
        error_type="SwingArcConflictError",
        error_message="conflict at door (a,b)",
        phase="phaseD",
    )
    assert rec.phase == "phaseD"
    assert rec.conditional_legality_violation is None


def test_failure_record_inv_d19_provenance_required_for_conditional():
    # Inv D19: ConditionalLegalityViolationError MUST carry a
    # ConditionalLegalityViolation provenance record.
    with pytest.raises(ValueError, match="Inv D19"):
        FailureRecord(
            candidate_signature="cand_abc",
            error_type="ConditionalLegalityViolationError",
            error_message="through-kitchen routing avoidable",
            phase="phaseF",
            conditional_legality_violation=None,
        )


def test_failure_record_inv_d19_provenance_reserved():
    # Inv D19 inverse: provenance only valid with conditional error.
    prov = ConditionalLegalityViolation(
        invariant_id="D11.3",
        violated_path=("a", "b"),
        alternative_path=("a", "c"),
        alternative_path_length_grid_units=1,
    )
    with pytest.raises(ValueError, match="Inv D19"):
        FailureRecord(
            candidate_signature="cand_abc",
            error_type="SwingArcConflictError",  # NOT conditional
            error_message="...",
            phase="phaseD",
            conditional_legality_violation=prov,
        )


def test_failure_record_conditional_with_provenance_ok():
    prov = ConditionalLegalityViolation(
        invariant_id="D11.3",
        violated_path=("a", "b"),
        alternative_path=("a", "c"),
        alternative_path_length_grid_units=1,
    )
    rec = FailureRecord(
        candidate_signature="cand_abc",
        error_type="ConditionalLegalityViolationError",
        error_message="through-kitchen routing avoidable",
        phase="phaseF",
        conditional_legality_violation=prov,
    )
    assert rec.conditional_legality_violation is prov


# ──────────────────────────────────────────────────────────────────────
# Schema: SuccessfulDoorPlacement (Inv D6 + D8) + FailedDoorPlacement
# ──────────────────────────────────────────────────────────────────────


def _make_minimal_cache_keys():
    return C13CacheKeys(
        geometry_cache_key="GEO",
        advisory_cache_key="GEO::ADV",
        full_cache_key="FULL",
    )


def test_successful_door_placement_minimal():
    door = _make_door(is_main_entry=True)
    s = SuccessfulDoorPlacement(
        source_placed_candidate_signature="cand_abc",
        doors=(door,),
        advisory_flags=(),
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
        cache_keys=_make_minimal_cache_keys(),
    )
    assert len(s.doors) == 1
    assert s.doors[0].is_main_entry


def test_successful_door_placement_inv_d6_exactly_one_main_entry():
    # Inv D6: exactly one door has is_main_entry=True per candidate.
    d1 = _make_door(
        room_a_id="bedroom_01", room_b_id="corridor_01", is_main_entry=False,
    )
    d2 = _make_door(
        room_a_id="entry_01",
        room_b_id="zzz_external",
        is_main_entry=False,
    )
    with pytest.raises(ValueError, match="Inv D6"):
        SuccessfulDoorPlacement(
            source_placed_candidate_signature="cand_abc",
            doors=(d1, d2),  # zero main entries
            advisory_flags=(),
            geometric_fidelity=GeometricFidelity.APPROXIMATE,
            cache_keys=_make_minimal_cache_keys(),
        )
    d1b = _make_door(
        room_a_id="bedroom_01", room_b_id="corridor_01", is_main_entry=True,
    )
    d2b = _make_door(
        room_a_id="entry_01", room_b_id="zzz_external", is_main_entry=True,
    )
    with pytest.raises(ValueError, match="Inv D6"):
        SuccessfulDoorPlacement(
            source_placed_candidate_signature="cand_abc",
            doors=(d1b, d2b),  # two main entries
            advisory_flags=(),
            geometric_fidelity=GeometricFidelity.APPROXIMATE,
            cache_keys=_make_minimal_cache_keys(),
        )


def test_successful_door_placement_inv_d8_sort_order():
    # Inv D8: doors sorted lex-ASC by (room_a_id, room_b_id).
    d1 = _make_door(
        room_a_id="bedroom_01", room_b_id="corridor_01", is_main_entry=True,
    )
    d2 = _make_door(
        room_a_id="aardvark_01",
        room_b_id="bedroom_02",
        is_main_entry=False,
    )
    # Pass them in wrong order; should be rejected.
    with pytest.raises(ValueError, match="Inv D8"):
        SuccessfulDoorPlacement(
            source_placed_candidate_signature="cand_abc",
            doors=(d1, d2),
            advisory_flags=(),
            geometric_fidelity=GeometricFidelity.APPROXIMATE,
            cache_keys=_make_minimal_cache_keys(),
        )
    # Correct order works.
    s = SuccessfulDoorPlacement(
        source_placed_candidate_signature="cand_abc",
        doors=(d2, d1),
        advisory_flags=(),
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
        cache_keys=_make_minimal_cache_keys(),
    )
    assert s.doors[0].room_a_id == "aardvark_01"


def test_failed_door_placement_minimal():
    rec = FailureRecord(
        candidate_signature="cand_abc",
        error_type="SwingArcConflictError",
        error_message="exhausted",
        phase="phaseD",
    )
    f = FailedDoorPlacement(
        source_placed_candidate_signature="cand_abc",
        failure_record=rec,
    )
    assert f.partial_doors == ()
    assert f.partial_advisory_flags == ()


# ──────────────────────────────────────────────────────────────────────
# Schema: DoorPlacementBatchResult
# ──────────────────────────────────────────────────────────────────────


def test_door_placement_batch_result_minimal():
    r = DoorPlacementBatchResult(
        successful=(),
        failed=(),
        c13_version=C13_VERSION,
        c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
        advisory_schema_version=ADVISORY_SCHEMA_VERSION,
        cache_key="batch_xyz",
    )
    assert r.c13_version == "v1.0"


def test_door_placement_batch_result_sort_order_enforced():
    door = _make_door(is_main_entry=True)
    s1 = SuccessfulDoorPlacement(
        source_placed_candidate_signature="z_cand",
        doors=(door,),
        advisory_flags=(),
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
        cache_keys=_make_minimal_cache_keys(),
    )
    s2 = SuccessfulDoorPlacement(
        source_placed_candidate_signature="a_cand",
        doors=(door,),
        advisory_flags=(),
        geometric_fidelity=GeometricFidelity.APPROXIMATE,
        cache_keys=_make_minimal_cache_keys(),
    )
    with pytest.raises(ValueError, match="must be sorted lex-ASC"):
        DoorPlacementBatchResult(
            successful=(s1, s2),  # z before a — wrong
            failed=(),
            c13_version=C13_VERSION,
            c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
            advisory_schema_version=ADVISORY_SCHEMA_VERSION,
            cache_key="batch_xyz",
        )


# ──────────────────────────────────────────────────────────────────────
# Category sets
# ──────────────────────────────────────────────────────────────────────


def test_habitable_room_categories_per_v0_5_d6():
    # Per v0.5 D6: Inv D17 — primary-reachability for habitable rooms.
    expected = {
        "bedroom", "master_bedroom", "guest_bedroom",
        "living", "dining", "kitchen", "pooja", "study",
    }
    assert HABITABLE_ROOM_CATEGORIES == expected


def test_secondary_door_eligible_categories_per_v0_4_c4():
    # Per v0.4 C4: only living/kitchen/utility/main_entrance eligible
    # for secondary doors at v1. Bedrooms/bathrooms/pooja excluded
    # (privacy).
    expected = {"living", "kitchen", "utility", "main_entrance"}
    assert SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1 == expected
    # Verify bedrooms/bathrooms/pooja are NOT eligible.
    for excluded in ("bedroom", "master_bedroom", "bathroom", "pooja"):
        assert excluded not in SECONDARY_DOOR_ELIGIBLE_CATEGORIES_V1


# ──────────────────────────────────────────────────────────────────────
# Config: DoorPlacementConfig
# ──────────────────────────────────────────────────────────────────────


def test_door_placement_config_defaults():
    c = DoorPlacementConfig()
    assert c.strict_mode is True
    assert c.corner_offset_m == DEFAULT_CORNER_OFFSET_M
    assert c.grid_snap_m == DEFAULT_GRID_SNAP_M
    assert c.max_conflict_resolution_iterations == 5
    assert c.secondary_door_conflict_budget == 3
    assert c.advisory_density_factor == 1.5
    assert c.bathroom_outswing_area_threshold_m2 == 4.0


def test_door_placement_config_negative_corner_offset_rejected():
    with pytest.raises(C13ConfigurationError, match="corner_offset_m"):
        DoorPlacementConfig(corner_offset_m=-0.01)


def test_door_placement_config_inv_d10_default_clear_width_rejected():
    with pytest.raises(C13ConfigurationError, match="Inv D10"):
        DoorPlacementConfig(default_clear_width_m=1.6)


def test_door_placement_config_zero_grid_snap_rejected():
    with pytest.raises(C13ConfigurationError, match="grid_snap_m"):
        DoorPlacementConfig(grid_snap_m=0.0)


def test_door_placement_config_secondary_budget_must_be_le_max():
    # Per v0.4 C4: secondary budget ≤ primary budget.
    with pytest.raises(C13ConfigurationError, match="secondary_door_conflict_budget"):
        DoorPlacementConfig(
            max_conflict_resolution_iterations=3,
            secondary_door_conflict_budget=5,
        )


def test_door_placement_config_zero_max_iterations_rejected():
    with pytest.raises(C13ConfigurationError, match="max_conflict_resolution_iterations"):
        DoorPlacementConfig(max_conflict_resolution_iterations=0)


def test_door_placement_config_negative_advisory_density_rejected():
    with pytest.raises(C13ConfigurationError, match="advisory_density_factor"):
        DoorPlacementConfig(advisory_density_factor=-0.1)


def test_door_placement_config_is_frozen():
    c = DoorPlacementConfig()
    with pytest.raises(Exception):  # FrozenInstanceError
        c.strict_mode = False  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────
# Cache keys: builders + determinism + Inv D18
# ──────────────────────────────────────────────────────────────────────


def test_build_geometry_cache_key_is_deterministic():
    config = DoorPlacementConfig()
    upstream = "c12_cache_abc"
    k1 = build_geometry_cache_key(
        config=config, upstream_c12_cache_key=upstream,
    )
    k2 = build_geometry_cache_key(
        config=config, upstream_c12_cache_key=upstream,
    )
    assert k1 == k2
    # sha256 hex digest is 64 chars.
    assert len(k1) == 64


def test_build_geometry_cache_key_changes_on_geometry_config_change():
    config_a = DoorPlacementConfig(corner_offset_m=0.15)
    config_b = DoorPlacementConfig(corner_offset_m=0.20)
    k_a = build_geometry_cache_key(
        config=config_a, upstream_c12_cache_key="c12",
    )
    k_b = build_geometry_cache_key(
        config=config_b, upstream_c12_cache_key="c12",
    )
    assert k_a != k_b


def test_build_geometry_cache_key_changes_on_upstream_change():
    config = DoorPlacementConfig()
    k_a = build_geometry_cache_key(
        config=config, upstream_c12_cache_key="c12_v1",
    )
    k_b = build_geometry_cache_key(
        config=config, upstream_c12_cache_key="c12_v2",
    )
    assert k_a != k_b


def test_build_geometry_cache_key_rejects_empty_upstream():
    config = DoorPlacementConfig()
    with pytest.raises(ValueError, match="upstream_c12_cache_key"):
        build_geometry_cache_key(
            config=config, upstream_c12_cache_key="",
        )


def test_build_advisory_cache_key_d18_prefix_holds():
    # Per Inv D18: advisory_cache_key starts with geometry_cache_key.
    config = DoorPlacementConfig()
    geometry = build_geometry_cache_key(
        config=config, upstream_c12_cache_key="c12",
    )
    advisory = build_advisory_cache_key(
        geometry_cache_key=geometry, config=config,
    )
    assert advisory.startswith(geometry)


def test_build_advisory_cache_key_changes_on_advisory_config_only():
    # Changing only advisory-cache-relevant config should change the
    # advisory_cache_key but leave geometry_cache_key intact.
    config_a = DoorPlacementConfig(advisory_density_factor=1.5)
    config_b = DoorPlacementConfig(advisory_density_factor=2.0)
    geometry_a = build_geometry_cache_key(
        config=config_a, upstream_c12_cache_key="c12",
    )
    geometry_b = build_geometry_cache_key(
        config=config_b, upstream_c12_cache_key="c12",
    )
    assert geometry_a == geometry_b  # geometry domain unchanged
    advisory_a = build_advisory_cache_key(
        geometry_cache_key=geometry_a, config=config_a,
    )
    advisory_b = build_advisory_cache_key(
        geometry_cache_key=geometry_b, config=config_b,
    )
    assert advisory_a != advisory_b  # advisory domain changed


def test_build_full_cache_key_rejects_d18_violation():
    # build_full_cache_key sanity-checks Inv D18 even if both args were
    # constructed independently.
    with pytest.raises(ValueError, match="Inv D18"):
        build_full_cache_key(
            geometry_cache_key="ABC",
            advisory_cache_key="XYZ::not_starting_with_abc",
        )


def test_build_c13_cache_keys_full_pipeline():
    config = DoorPlacementConfig()
    keys = build_c13_cache_keys(
        config=config, upstream_c12_cache_key="c12_xyz",
    )
    # Inv D18 enforced by both builder and dataclass __post_init__.
    assert keys.advisory_cache_key.startswith(keys.geometry_cache_key)
    # All three keys non-empty.
    assert keys.geometry_cache_key
    assert keys.advisory_cache_key
    assert keys.full_cache_key
    # full_cache_key is opaque (sha256 hex, 64 chars).
    assert len(keys.full_cache_key) == 64


def test_build_c13_cache_keys_byte_equal_replay():
    # Inv D7 foundational: same inputs → byte-equal cache keys.
    config = DoorPlacementConfig()
    upstream = "c12_xyz"
    keys_1 = build_c13_cache_keys(
        config=config, upstream_c12_cache_key=upstream,
    )
    keys_2 = build_c13_cache_keys(
        config=config, upstream_c12_cache_key=upstream,
    )
    assert keys_1 == keys_2
    assert hash(keys_1) == hash(keys_2)


# ──────────────────────────────────────────────────────────────────────
# Public API surface sanity
# ──────────────────────────────────────────────────────────────────────


def test_public_exports_present():
    # All v1.0 LOCKED contracts should be accessible from the package
    # root. Sample the critical types.
    import buildemup.components.c13 as c13
    for name in (
        "C13_VERSION",
        "C13_EDGE_PROTOCOL_VERSION",
        "ADVISORY_SCHEMA_VERSION",
        "MAX_DOORS_PER_ROOM_V1",
        "Door",
        "AdvisoryFlag",
        "CausalContext",
        "C13CacheKeys",
        "ConditionalLegalityViolation",
        "SuccessfulDoorPlacement",
        "FailedDoorPlacement",
        "DoorPlacementBatchResult",
        "C13ConsumesFromC12Edge",
        "EdgeType",
        "build_c13_cache_keys",
    ):
        assert hasattr(c13, name), f"Missing public export: {name}"
