"""
C11a Sub-session 1 tests — schema, errors, provenance.

Per CODING_MANDATE Step 2 Sub-session 1: ship schema + errors +
provenance modules with no logic. Tests verify:
  - All enums have the expected entries
  - Frozen dataclass invariants enforced
  - DeltaKey / family / tier surface stable
  - UPSTREAM_PURITY_REGISTRY shape
  - WAIVER_REGISTRY empty at v1.0 LOCK (Inv 24)
  - Error severity_tier ClassVars per § 2.7
  - MutatedTopologyCandidate __post_init__ guards (v1 invariant: 1 op)

Sub-session 2 will add per-operator tests once implementations land.
"""
from __future__ import annotations

from typing import get_args, get_type_hints

import pytest

from buildemup.components.c11a import (
    BatchAllNonBaseFailedError,
    DeepMutationApplicationError,
    DeepMutationPurityContractError,
    DeltaKey,
    EnforcementMode,
    FamilySlotAllocation,
    InvariantViolationError,
    MutatedTopologyCandidate,
    MutationApplicationError,
    MutationApplicationResult,
    MutationDiagnostics,
    MutationLineageDepth,
    MutationOperator,
    MutationOperatorFamily,
    MutationOperatorMetadata,
    MutationTier,
    MutationViabilityPredicate,
    OperatorExpectedDeltaSchema,
    OperatorRegistryError,
    PendingUpstreamPredicateError,
    PerCandidateError,
    ProvenanceVerbosity,
    PurityAttestation,
    QuarantineFingerprint,
    RegistryValidationMode,
    SeverityClassificationAuditError,
    TopologyFamilyTransitionPolicy,
    TopologyInvalidError,
    TopologyMutationConfig,
    TopologyMutationError,
    TopologyMutationProvenance,
    UPSTREAM_PURITY_REGISTRY,
    UpstreamAmendmentWaiver,
    WAIVER_REGISTRY,
    _OPERATOR_FAMILY_POLICY,
)


VALID_TIERS = frozenset({"per_candidate", "batch", "systemic"})


# =============================================================================
# § 2.1 — MutationOperator enum (16 entries)
# =============================================================================


def test_operator_enum_has_16_entries() -> None:
    assert len(list(MutationOperator)) == 16


def test_operator_enum_contains_all_expected_operators() -> None:
    expected = {
        "m0_base",
        "m1_horiz_flip", "m2_vert_flip",
        "m3a_stair_east", "m3b_stair_west", "m3c_stair_ne_corner",
        "m4_corridor_inv",
        "m5_public_private_swap",
        "m6_wet_wall_rotate",
        "m7a_grid_scale_3_3", "m7b_grid_scale_2_7",
        "m8_master_floor_swap",
        "m9a_entry_ne_center", "m9b_entry_ne_corner_w",
        "m9c_entry_ne_corner_e", "m9d_entry_offset_ne",
    }
    actual = {op.value for op in MutationOperator}
    assert actual == expected


def test_operator_enum_inherits_str() -> None:
    """Operator values are str-typed (Enum mixin) so canonical-serialize
    works without custom encoders."""
    assert isinstance(MutationOperator.M0_BASE.value, str)
    assert MutationOperator.M0_BASE == "m0_base"


# =============================================================================
# § 2.1 — MutationTier (2) + MutationOperatorFamily (9)
# =============================================================================


def test_tier_enum_has_two_entries() -> None:
    tiers = {t.value for t in MutationTier}
    assert tiers == {"shallow", "regenerative"}


def test_family_enum_has_nine_entries() -> None:
    families = {f.value for f in MutationOperatorFamily}
    expected = {"base", "flip", "staircase", "corridor", "zone",
                "wet_wall", "grid", "vertical", "entry"}
    assert families == expected


def test_family_transition_policy_has_three_entries() -> None:
    policies = {p.value for p in TopologyFamilyTransitionPolicy}
    assert policies == {"preserves_family", "transforms_family",
                        "invalidates_family"}


# =============================================================================
# § 2.2 — _OPERATOR_FAMILY_POLICY table covers every operator
# =============================================================================


def test_family_policy_table_covers_every_operator() -> None:
    policy_keys = set(_OPERATOR_FAMILY_POLICY.keys())
    operator_set = set(MutationOperator)
    assert policy_keys == operator_set, (
        f"Missing or extra operators in _OPERATOR_FAMILY_POLICY: "
        f"missing={operator_set - policy_keys}, "
        f"extra={policy_keys - operator_set}"
    )


def test_family_policy_m4_is_transforms_family() -> None:
    """v0.5 W#5 Q22 adjudication — M4 corridor inversion is
    TRANSFORMS_FAMILY, not INVALIDATES_FAMILY."""
    assert (
        _OPERATOR_FAMILY_POLICY[MutationOperator.M4_CORRIDOR_INV]
        is TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY
    )


def test_family_policy_m5_is_transforms_family() -> None:
    assert (
        _OPERATOR_FAMILY_POLICY[MutationOperator.M5_ZONE_SWAP]
        is TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY
    )


def test_family_policy_m0_base_preserves_family() -> None:
    assert (
        _OPERATOR_FAMILY_POLICY[MutationOperator.M0_BASE]
        is TopologyFamilyTransitionPolicy.PRESERVES_FAMILY
    )


# =============================================================================
# § 2.5 — DeltaKey enum (20 entries; namespace prefix for non-meta)
# =============================================================================


def test_delta_key_enum_has_twenty_entries() -> None:
    assert len(list(DeltaKey)) == 20


def test_delta_key_namespaces_well_formed() -> None:
    """Every DeltaKey value is dotted-namespace prefixed. META_* keys
    are namespaced under 'meta.'; all others under their domain
    namespace (geometry / adjacency / circulation / zoning / plumbing /
    multifloor)."""
    valid_namespaces = {
        "geometry.", "adjacency.", "circulation.", "zoning.",
        "plumbing.", "multifloor.", "meta.",
    }
    for key in DeltaKey:
        assert any(key.value.startswith(ns) for ns in valid_namespaces), (
            f"DeltaKey {key.name}={key.value!r} is not namespaced"
        )


def test_delta_key_meta_keys_present() -> None:
    """META_* keys live in the enum so canonical-vocabulary rule
    (Inv 28) catches misuse — they only appear in forbidden_keys
    sets."""
    assert DeltaKey.META_FIXTURE_TYPES.value == "meta.fixture_types"
    assert DeltaKey.META_ROOM_COUNT.value == "meta.room_count"


# =============================================================================
# § 2.5 — OperatorExpectedDeltaSchema is constructible + frozen
# =============================================================================


def test_operator_expected_delta_schema_construction() -> None:
    schema = OperatorExpectedDeltaSchema(
        expected=frozenset({DeltaKey.GEO_ROOM_POSITION_X}),
        allowed_secondary=frozenset({DeltaKey.ADJ_EDGES_ORIENTATION}),
        forbidden=frozenset({DeltaKey.META_ROOM_COUNT,
                             DeltaKey.GEO_ROOM_AREA}),
    )
    assert DeltaKey.GEO_ROOM_POSITION_X in schema.expected
    assert DeltaKey.META_ROOM_COUNT in schema.forbidden


def test_operator_expected_delta_schema_is_frozen() -> None:
    schema = OperatorExpectedDeltaSchema(
        expected=frozenset(),
        allowed_secondary=frozenset(),
        forbidden=frozenset(),
    )
    with pytest.raises(Exception):
        # frozen dataclass — mutation raises FrozenInstanceError
        schema.expected = frozenset({DeltaKey.GEO_ROOM_AREA})  # type: ignore[misc]


# =============================================================================
# § 2.3 — MutationLineageDepth (3 entries)
# =============================================================================


def test_lineage_depth_enum_has_three_entries() -> None:
    depths = {d.value for d in MutationLineageDepth}
    assert depths == {
        "shallow_transform",
        "regenerative_transform",
        "emergent_regeneration",
    }


# =============================================================================
# § 0.1 — UPSTREAM_PURITY_REGISTRY shape
# =============================================================================


def test_upstream_purity_registry_has_three_attestations() -> None:
    """v0.4 ships attestations for C7 (pure), C9 (pure), C10 (lazy_init_once)."""
    assert len(UPSTREAM_PURITY_REGISTRY) == 3


def test_upstream_purity_registry_components() -> None:
    components = {a.component_id for a in UPSTREAM_PURITY_REGISTRY}
    assert components == {"C7", "C9", "C10"}


def test_upstream_purity_registry_c10_is_lazy_init_once() -> None:
    """C10's _KB_VALIDATED qualifies as lazy_init_once per v0.4 § 0.1."""
    c10_attestation = next(
        a for a in UPSTREAM_PURITY_REGISTRY if a.component_id == "C10"
    )
    assert c10_attestation.purity_class == "lazy_init_once"
    assert c10_attestation.entry_point == "plan_wet_zones"


def test_upstream_purity_registry_c7_c9_are_pure() -> None:
    for component_id in ("C7", "C9"):
        attestation = next(
            a for a in UPSTREAM_PURITY_REGISTRY if a.component_id == component_id
        )
        assert attestation.purity_class == "pure"


def test_purity_attestation_purity_classes_well_formed() -> None:
    """Each attestation declares one of the three documented purity classes."""
    valid = {"pure", "read_only_cache", "lazy_init_once"}
    for a in UPSTREAM_PURITY_REGISTRY:
        assert a.purity_class in valid


# =============================================================================
# § 0.2 — WAIVER_REGISTRY at v1.0 LOCK (Inv 24)
# =============================================================================


def test_waiver_registry_empty_at_v1_lock() -> None:
    """Per S38 Path α + Inv 24 LOCK gate: at v1.0 LOCK time,
    pending_upstream_count - len(active_waivers) == 0 AND
    len(active_waivers) <= 3. With B-NEW-J/K/L/P all LOCKED, no
    pending upstream amendments require waivers, so the registry is
    empty."""
    assert len(WAIVER_REGISTRY) == 0


def test_waiver_registry_below_three_cap() -> None:
    """Inv 24 v0.5: len(active_waivers) <= 3 at LOCK time."""
    assert len(WAIVER_REGISTRY) <= 3


def test_upstream_amendment_waiver_is_constructible_and_frozen() -> None:
    """The dataclass is usable for future grace-window waivers; v1 just
    has none."""
    waiver = UpstreamAmendmentWaiver(
        rule_owner="C5",
        rule_id="example_pending_rule",
        waiver_reason="upstream amendment landing in v1.0.1",
        granted_by="Ramalingam",
        granted_at_iso="2026-05-09T10:00:00Z",
        grace_window_expires_at_version="1.0.2",
        inline_check_implementation="returns (True, None) — vacuous-pass stub",
    )
    assert waiver.rule_owner == "C5"
    with pytest.raises(Exception):
        waiver.rule_owner = "C7"  # type: ignore[misc]


# =============================================================================
# § 0.4 / § 2.7 — MutationViabilityPredicate
# =============================================================================


def test_predicate_pending_upstream_default_false() -> None:
    pred = MutationViabilityPredicate(
        rule_owner="C5",
        rule_id="privacy_zoning",
        description="example",
        _predicate_fn=lambda *args, **kwargs: (True, None),
    )
    assert pred.pending_upstream is False
    assert pred.expires_at_version is None


# =============================================================================
# § 2.9 — QuarantineFingerprint
# =============================================================================


def test_quarantine_fingerprint_constructible_with_empty_quarantine() -> None:
    """Default state at v1.0: no operators quarantined; fingerprint
    captures the empty set + a hash of the canonical-serialized empty
    state. (Hash function lives in orchestrator; we just verify the
    schema is usable.)"""
    fp = QuarantineFingerprint(
        quarantined_operators=(),
        quarantine_reasons=(),
        fingerprint_hash="0" * 64,  # placeholder SHA256 hex digest
    )
    assert fp.quarantined_operators == ()


# =============================================================================
# § 2.6 — Config + enums
# =============================================================================


def test_topology_mutation_config_defaults() -> None:
    """Default config enables every operator, max 8 seeds, dedupe on,
    enforcement WARN, registry STRICT."""
    cfg = TopologyMutationConfig()
    assert len(cfg.enabled_operators) == 16
    assert cfg.max_seeds_per_input == 8
    assert cfg.deduplicate_by_signature is True
    assert cfg.enforcement_mode is EnforcementMode.WARN
    assert cfg.registry_validation_mode is RegistryValidationMode.STRICT


def test_topology_mutation_config_family_slot_allocations_default() -> None:
    """Default config reserves 1 slot per family — 9 families * 1 slot = 9
    slots, comfortably within max_seeds_per_input=8 plus base."""
    cfg = TopologyMutationConfig()
    assert len(cfg.family_slot_allocations) == 9
    families = {a.family for a in cfg.family_slot_allocations}
    assert families == set(MutationOperatorFamily)
    for a in cfg.family_slot_allocations:
        assert a.reserved_slots == 1


def test_topology_mutation_config_is_frozen() -> None:
    cfg = TopologyMutationConfig()
    with pytest.raises(Exception):
        cfg.max_seeds_per_input = 99  # type: ignore[misc]


def test_config_field_metadata_cache_relevant_present_per_inv_26() -> None:
    """Inv 26 (NEW v0.4): every TopologyMutationConfig field carries
    metadata['cache_relevant']: bool. Missing markers raise
    OperatorRegistryError at startup. Sub-session 1 just checks the
    schema-side metadata is in place — the runtime Phase 0 check
    lands at Sub-session 4."""
    import dataclasses
    cfg_fields = dataclasses.fields(TopologyMutationConfig)
    for f in cfg_fields:
        assert "cache_relevant" in f.metadata, (
            f"TopologyMutationConfig.{f.name} missing "
            f"metadata['cache_relevant'] (Inv 26)"
        )
        assert isinstance(f.metadata["cache_relevant"], bool)


def test_config_cache_relevant_partition_six_six() -> None:
    """Per § 2.6 + Spec #4 v1.6 § 3.4: 6 cache-relevant fields
    (enabled_operators, max_seeds_per_input, family_slot_allocations,
    deterministic_order, emit_base, deduplicate_by_signature) and 6
    cache-irrelevant (enforcement_mode, provenance_verbosity,
    deep_mutation_cache_enabled, skip_pending_upstream_predicates,
    registry_validation_mode, generation — Spec #4 v1.6 addition;
    cache_relevant=False because generation participates in Tier 2/3
    dispatch only, NOT in cache identity per the determinism
    tier-table)."""
    import dataclasses
    cfg_fields = dataclasses.fields(TopologyMutationConfig)
    cache_rel = [f for f in cfg_fields if f.metadata.get("cache_relevant")]
    cache_irr = [f for f in cfg_fields if not f.metadata.get("cache_relevant")]
    assert len(cache_rel) == 6
    assert len(cache_irr) == 6


def test_enforcement_mode_two_entries() -> None:
    assert {m.value for m in EnforcementMode} == {"strict", "warn"}


def test_provenance_verbosity_three_entries() -> None:
    assert {m.value for m in ProvenanceVerbosity} == {
        "summary", "per_op", "full",
    }


def test_registry_validation_mode_two_entries() -> None:
    assert {m.value for m in RegistryValidationMode} == {"strict", "warn"}


# =============================================================================
# § 2.4 — MutationDiagnostics
# =============================================================================


def test_diagnostics_constructible_with_empty_yields() -> None:
    """Smoke test the dataclass shape; defaults for novelty fidelity
    are 'low' per v0.3."""
    diag = MutationDiagnostics(
        per_operator_yield={},
        per_family_yield={},
        family_spread_entropy=0.0,
        duplicate_ratio=0.0,
        novelty_deficit_estimator=0.0,
    )
    assert diag.novelty_estimator_fidelity == "low"
    assert diag.deep_mutation_runtime_ms == 0


# =============================================================================
# § 2.3 — MutationApplicationResult
# =============================================================================


def test_application_result_constructible() -> None:
    result = MutationApplicationResult(
        operator=MutationOperator.M0_BASE,
        valid=True,
        invalidity_reason=None,
        topology_variant_id="t-base-001",
        rejection_invariant_id=None,
        source_family_id="fam-source-001",
        output_family_id="fam-source-001",
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
    )
    assert result.upstream_regeneration_delta == ()


def test_application_result_delta_can_carry_delta_keys() -> None:
    """v0.5 type-tightening: upstream_regeneration_delta is
    tuple[DeltaKey, ...], not tuple[str, ...]."""
    result = MutationApplicationResult(
        operator=MutationOperator.M7A_GRID_3_3,
        valid=True,
        invalidity_reason=None,
        topology_variant_id="t-m7a-001",
        rejection_invariant_id=None,
        source_family_id="fam-source-001",
        output_family_id="fam-source-001",
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
        upstream_regeneration_delta=(
            DeltaKey.GEO_GRID_BAY_SIZE,
            DeltaKey.PLUMB_WET_WALL_ASSIGNMENT,
        ),
    )
    assert DeltaKey.GEO_GRID_BAY_SIZE in result.upstream_regeneration_delta


# =============================================================================
# § 2.3 — MutatedTopologyCandidate __post_init__ guards
# =============================================================================


def _make_app_result(op: MutationOperator) -> MutationApplicationResult:
    return MutationApplicationResult(
        operator=op,
        valid=True,
        invalidity_reason=None,
        topology_variant_id=f"t-{op.value}",
        rejection_invariant_id=None,
        source_family_id="fam-source",
        output_family_id="fam-source",
        family_transition_policy=TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
        lineage_depth=MutationLineageDepth.SHALLOW_TRANSFORM,
    )


def _make_provenance() -> TopologyMutationProvenance:
    diag = MutationDiagnostics(
        per_operator_yield={}, per_family_yield={},
        family_spread_entropy=0.0, duplicate_ratio=0.0,
        novelty_deficit_estimator=0.0,
    )
    fp = QuarantineFingerprint(
        quarantined_operators=(),
        quarantine_reasons=(),
        fingerprint_hash="0" * 64,
    )
    return TopologyMutationProvenance(
        derived_at=0.0,
        plot_analysis_trace_id="trace-001",
        floor_label="ground",
        enabled_operators_snapshot=(),
        operator_application_log=(),
        accepted_count=0, rejected_count=0, deduplicated_count=0,
        truncated_at_max_seeds=False,
        diagnostics=diag,
        rule_trace=(),
        quarantine_fingerprint=fp,
    )


def test_mutated_candidate_v1_invariant_one_operator() -> None:
    """v1 invariant: exactly one operator + one application_result."""
    op = MutationOperator.M0_BASE
    cand = MutatedTopologyCandidate(
        source_candidate=None,  # type: ignore[arg-type]  # Sub-session 1: schema-only
        applied_operators=(op,),
        topology_variant_id="t-001",
        application_results=(_make_app_result(op),),
        provenance=_make_provenance(),
    )
    assert len(cand.applied_operators) == 1


def test_mutated_candidate_rejects_multi_operator() -> None:
    op1 = MutationOperator.M0_BASE
    op2 = MutationOperator.M1_HORIZ_FLIP
    with pytest.raises(ValueError, match="v1 requires exactly 1 operator"):
        MutatedTopologyCandidate(
            source_candidate=None,  # type: ignore[arg-type]
            applied_operators=(op1, op2),
            topology_variant_id="t-001",
            application_results=(
                _make_app_result(op1), _make_app_result(op2),
            ),
            provenance=_make_provenance(),
        )


def test_mutated_candidate_rejects_zero_operators() -> None:
    with pytest.raises(ValueError, match="v1 requires exactly 1 operator"):
        MutatedTopologyCandidate(
            source_candidate=None,  # type: ignore[arg-type]
            applied_operators=(),
            topology_variant_id="t-001",
            application_results=(),
            provenance=_make_provenance(),
        )


def test_mutated_candidate_rejects_inconsistent_op_and_result() -> None:
    """applied_operators[0] must equal application_results[0].operator."""
    op_a = MutationOperator.M0_BASE
    op_b = MutationOperator.M1_HORIZ_FLIP
    with pytest.raises(ValueError, match="Inconsistent MutatedTopologyCandidate"):
        MutatedTopologyCandidate(
            source_candidate=None,  # type: ignore[arg-type]
            applied_operators=(op_a,),
            topology_variant_id="t-001",
            application_results=(_make_app_result(op_b),),
            provenance=_make_provenance(),
        )


# =============================================================================
# § 5 / § 2.7 — Error severity_tier ClassVar coverage
# =============================================================================


_ERROR_TIER_CASES = [
    (TopologyMutationError, "per_candidate"),     # base default
    (PerCandidateError, "per_candidate"),
    (TopologyInvalidError, "per_candidate"),
    (MutationApplicationError, "per_candidate"),
    (DeepMutationApplicationError, "per_candidate"),
    (BatchAllNonBaseFailedError, "batch"),
    (OperatorRegistryError, "systemic"),
    (DeepMutationPurityContractError, "systemic"),
    (PendingUpstreamPredicateError, "systemic"),
    (SeverityClassificationAuditError, "systemic"),
    (InvariantViolationError, "systemic"),
]


@pytest.mark.parametrize(
    "error_class, expected_tier",
    _ERROR_TIER_CASES,
    ids=[c.__name__ for c, _ in _ERROR_TIER_CASES],
)
def test_c11a_error_severity_tier_correct(
    error_class: type, expected_tier: str,
) -> None:
    """Every C11a error declares severity_tier per § 2.7."""
    assert hasattr(error_class, "severity_tier")
    assert error_class.severity_tier == expected_tier
    assert error_class.severity_tier in VALID_TIERS


def test_c11a_error_dispatch_pattern_routes_correctly() -> None:
    """Mirror of § 2.7 catch logic: routes by getattr lookup."""
    err = TopologyInvalidError("test", rejection_invariant_id="C5_privacy_zoning")
    assert getattr(type(err), "severity_tier", "unknown") == "per_candidate"

    err2 = OperatorRegistryError("registry inconsistency")
    assert getattr(type(err2), "severity_tier", "unknown") == "systemic"


def test_topology_invalid_error_carries_rejection_invariant_id() -> None:
    err = TopologyInvalidError(
        "M9c entry mismatch",
        rejection_invariant_id="C8_Inv_21",
    )
    assert err.rejection_invariant_id == "C8_Inv_21"


def test_deep_mutation_application_error_wraps_upstream() -> None:
    upstream_exc = ValueError("upstream failure")
    err = DeepMutationApplicationError(
        "Tier B regeneration rejected",
        wrapped_exception=upstream_exc,
        upstream_component="C10",
    )
    assert err.wrapped_exception is upstream_exc
    assert err.upstream_component == "C10"


def test_batch_all_non_base_failed_carries_failures() -> None:
    err = BatchAllNonBaseFailedError(
        "all non-base operators rejected for all candidates",
        per_candidate_failures=[(0, ValueError("a")), (1, ValueError("b"))],
        input_count=2,
    )
    assert err.input_count == 2
    assert len(err.per_candidate_failures) == 2


# =============================================================================
# § 2.4 — TopologyMutationProvenance
# =============================================================================


def test_provenance_constructible_with_empty_log() -> None:
    prov = _make_provenance()
    assert prov.accepted_count == 0
    assert prov.quarantine_fingerprint.fingerprint_hash == "0" * 64


def test_provenance_observational_runtime_underscore_marker() -> None:
    """Per § 2.4: _observational_runtime_ms is excluded from replay
    hashes by underscore convention. Verify the field name is
    explicit (lint discipline)."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(TopologyMutationProvenance)}
    assert "_observational_runtime_ms" in field_names


# =============================================================================
# § 2.6 — FamilySlotAllocation
# =============================================================================


def test_family_slot_allocation_default_one() -> None:
    a = FamilySlotAllocation(family=MutationOperatorFamily.BASE)
    assert a.reserved_slots == 1


def test_family_slot_allocation_is_frozen() -> None:
    a = FamilySlotAllocation(family=MutationOperatorFamily.FLIP)
    with pytest.raises(Exception):
        a.reserved_slots = 99  # type: ignore[misc]


# =============================================================================
# Cross-shape sanity: counts adjudicated by spec
# =============================================================================


def test_spec_counts_self_consistent() -> None:
    """Quick assertion of the adjudicated counts at v1.0 LOCK so any
    accidental enum/dataclass change shows up immediately."""
    assert len(list(MutationOperator)) == 16
    assert len(list(MutationOperatorFamily)) == 9
    assert len(list(MutationTier)) == 2
    assert len(list(DeltaKey)) == 20
    assert len(UPSTREAM_PURITY_REGISTRY) == 3
    assert len(WAIVER_REGISTRY) == 0  # Inv 24 LOCK gate
    assert len(_OPERATOR_FAMILY_POLICY) == 16
