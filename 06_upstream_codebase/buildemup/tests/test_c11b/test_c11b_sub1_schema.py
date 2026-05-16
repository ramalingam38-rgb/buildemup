"""Sub-1 tests: schema, version constants, capability flags,
tiebreak_fingerprint precompute, Inv 23 quality-ranked = False."""
from __future__ import annotations

import pytest

from buildemup.components.c11b import (
    C11B_VERSION,
    SEMVER_POLICY_VERSION,
    TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
    InvariantViolationError,
    ObjectiveVector,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.components.c11b.schema import _capability_flags_for_operator_class
from buildemup.components.c11b.tiebreak import _compute_tiebreak_fingerprint


# ── helpers ────────────────────────────────────────────────────────────


def _params(*tuples: tuple[str, float, float]) -> RefinedParameters:
    dims = tuple(
        RoomDimension(room_id=rid, width_m=w, depth_m=d) for rid, w, d in tuples
    )
    return RefinedParameters(room_dimensions=dims)


# ── version constants ──────────────────────────────────────────────────


def test_c11b_version_is_v1_1_string():
    assert C11B_VERSION == "v1.1"
    assert isinstance(C11B_VERSION, str)


def test_tiebreak_fingerprint_schema_version_is_int_1():
    assert TIEBREAK_FINGERPRINT_SCHEMA_VERSION == 1
    assert isinstance(TIEBREAK_FINGERPRINT_SCHEMA_VERSION, int)


def test_semver_policy_version_is_int_1():
    """W6-8: constant exists and is an int, replacing the v0.6
    doc-presence meta-test."""
    assert SEMVER_POLICY_VERSION == 1
    assert isinstance(SEMVER_POLICY_VERSION, int)


# ── capability-flag derivation per § 0.3.1 worked-example table ────────


@pytest.mark.parametrize(
    "operator_class,expected",
    [
        (OperatorClass.TIER_A_SHALLOW, (False, False, True)),
        (OperatorClass.TIER_B_REGENERATIVE, (True, True, False)),
        (OperatorClass.M0_BASE, (True, True, False)),
        (OperatorClass.M8_MULTI_FLOOR, (True, True, False)),
    ],
)
def test_capability_flags_for_operator_class(operator_class, expected):
    assert _capability_flags_for_operator_class(operator_class) == expected


def test_from_operator_class_tier_a_produces_predicate_only():
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.TIER_A_SHALLOW,
        _params(("r0", 3.0, 4.0)),
        "sig_a",
    )
    assert cand.geometry_materialized is False
    assert cand.placement_safe is False
    assert cand.requires_transform_resolution is True
    assert cand.capability_mode == "PREDICATE_ONLY"


def test_from_operator_class_tier_b_produces_materialized():
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.TIER_B_REGENERATIVE,
        _params(("r0", 3.0, 4.0)),
        "sig_b",
    )
    assert cand.geometry_materialized is True
    assert cand.placement_safe is True
    assert cand.requires_transform_resolution is False
    assert cand.capability_mode == "MATERIALIZED"


# ── W6-1 HARD assertion: placement_safe == geometry_materialized ───────


def test_w6_1_hard_assertion_placement_safe_mismatch():
    """W6-1: __post_init__ MUST raise if placement_safe != geometry_materialized."""
    with pytest.raises(InvariantViolationError, match="placement_safe"):
        RefinedCandidate(
            refined_parameters=_params(("r0", 3.0, 4.0)),
            source_topology_candidate_signature="sig",
            geometry_materialized=True,
            placement_safe=False,  # mismatch — must raise
            requires_transform_resolution=False,
        )


def test_w6_1_hard_assertion_transform_resolution_mismatch():
    """W6-1: __post_init__ MUST raise if requires_transform_resolution
    != NOT geometry_materialized."""
    with pytest.raises(InvariantViolationError, match="requires_transform_resolution"):
        RefinedCandidate(
            refined_parameters=_params(("r0", 3.0, 4.0)),
            source_topology_candidate_signature="sig",
            geometry_materialized=True,
            placement_safe=True,
            requires_transform_resolution=True,  # should be False
        )


def test_w6_1_hard_assertion_tier_a_flipped():
    """Tier A flipped flags: gm=False, ps=True is invalid."""
    with pytest.raises(InvariantViolationError):
        RefinedCandidate(
            refined_parameters=_params(("r0", 3.0, 4.0)),
            source_topology_candidate_signature="sig",
            geometry_materialized=False,
            placement_safe=True,
            requires_transform_resolution=True,
        )


# ── Inv 23: output_sequence_is_quality_ranked MUST be False at v1 ──────


def test_inv_23_quality_ranked_must_be_false():
    with pytest.raises(InvariantViolationError, match="Inv 23"):
        RefinedCandidate(
            refined_parameters=_params(("r0", 3.0, 4.0)),
            source_topology_candidate_signature="sig",
            geometry_materialized=True,
            placement_safe=True,
            requires_transform_resolution=False,
            output_sequence_is_quality_ranked=True,
        )


def test_inv_23_default_is_false():
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.M0_BASE,
        _params(("r0", 3.0, 4.0)),
        "sig",
    )
    assert cand.output_sequence_is_quality_ranked is False
    assert cand.output_sequence_strategy == "diversity_order"


# ── RefinedParameters invariants ───────────────────────────────────────


def test_refined_parameters_sorted_by_room_id():
    """RefinedParameters MUST be sorted lex-ASC by room_id."""
    with pytest.raises(InvariantViolationError, match="sorted"):
        RefinedParameters(
            room_dimensions=(
                RoomDimension(room_id="r2", width_m=3.0, depth_m=4.0),
                RoomDimension(room_id="r1", width_m=3.0, depth_m=4.0),
            )
        )


def test_refined_parameters_no_duplicate_room_ids():
    with pytest.raises(InvariantViolationError, match="duplicate"):
        RefinedParameters(
            room_dimensions=(
                RoomDimension(room_id="r1", width_m=3.0, depth_m=4.0),
                RoomDimension(room_id="r1", width_m=3.5, depth_m=4.5),
            )
        )


def test_room_dimension_rejects_nonpositive():
    with pytest.raises(InvariantViolationError):
        RoomDimension(room_id="r0", width_m=0.0, depth_m=3.0)
    with pytest.raises(InvariantViolationError):
        RoomDimension(room_id="r0", width_m=3.0, depth_m=-1.0)


# ── ObjectiveVector invariants ─────────────────────────────────────────


def test_objective_vector_rejects_negative_violations():
    with pytest.raises(InvariantViolationError):
        ObjectiveVector(values=(("a", 0.0),), constraint_violations=-0.1)


def test_objective_vector_zero_violations_is_feasible_marker():
    ov = ObjectiveVector(values=(("a", 0.0),), constraint_violations=0.0)
    assert ov.constraint_violations == 0.0


# ── tiebreak_fingerprint precompute (W5-12) ────────────────────────────


def test_tiebreak_fingerprint_set_after_post_init():
    """W5-12: tiebreak_fingerprint precomputed at __post_init__."""
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.M0_BASE, _params(("r0", 3.0, 4.0)), "sig"
    )
    assert cand.tiebreak_fingerprint != 0
    assert isinstance(cand.tiebreak_fingerprint, int)
    # 64-bit big-endian: fits in 8 bytes.
    assert 0 <= cand.tiebreak_fingerprint < 2**64


def test_tiebreak_fingerprint_deterministic_same_params():
    """Same RefinedParameters → same fingerprint, regardless of how
    they're wrapped in a candidate."""
    rp = _params(("r0", 3.0, 4.0), ("r1", 2.5, 3.0))
    fp1 = _compute_tiebreak_fingerprint(rp)
    fp2 = _compute_tiebreak_fingerprint(rp)
    assert fp1 == fp2


def test_tiebreak_fingerprint_differs_for_different_params():
    fp1 = _compute_tiebreak_fingerprint(_params(("r0", 3.0, 4.0)))
    fp2 = _compute_tiebreak_fingerprint(_params(("r0", 3.0, 4.1)))
    assert fp1 != fp2


def test_w6_3_version_anchor_changes_fingerprint():
    """W6-3: changing TIEBREAK_FINGERPRINT_SCHEMA_VERSION must produce a
    different fingerprint for the same parameters. We monkeypatch the
    constant to simulate a future bump."""
    import buildemup.components.c11b.tiebreak as tb_mod

    rp = _params(("r0", 3.0, 4.0))
    fp_v1 = _compute_tiebreak_fingerprint(rp)

    # Monkeypatch the module-level reference to simulate version bump.
    original = tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION
    try:
        tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = 2
        fp_v2 = _compute_tiebreak_fingerprint(rp)
        assert fp_v1 != fp_v2, (
            "W6-3 version anchor must change the fingerprint when "
            "TIEBREAK_FINGERPRINT_SCHEMA_VERSION changes."
        )
    finally:
        tb_mod.TIEBREAK_FINGERPRINT_SCHEMA_VERSION = original


def test_tiebreak_fingerprint_user_override_is_recomputed():
    """If the caller passes a stale tiebreak_fingerprint at construction,
    __post_init__ silently recomputes it (F-v6-3)."""
    rp = _params(("r0", 3.0, 4.0))
    expected = _compute_tiebreak_fingerprint(rp)
    cand = RefinedCandidate(
        refined_parameters=rp,
        source_topology_candidate_signature="sig",
        geometry_materialized=True,
        placement_safe=True,
        requires_transform_resolution=False,
        tiebreak_fingerprint=999999,  # stale; will be overwritten
    )
    assert cand.tiebreak_fingerprint == expected


# ── capability_mode derived property ───────────────────────────────────


def test_capability_mode_predicate_only_when_not_materialized():
    cand = RefinedCandidate.from_operator_class(
        OperatorClass.TIER_A_SHALLOW, _params(("r0", 3.0, 4.0)), "sig"
    )
    assert cand.capability_mode == "PREDICATE_ONLY"


def test_capability_mode_materialized_when_geometry_materialized():
    for oc in (OperatorClass.TIER_B_REGENERATIVE, OperatorClass.M0_BASE):
        cand = RefinedCandidate.from_operator_class(
            oc, _params(("r0", 3.0, 4.0)), "sig"
        )
        assert cand.capability_mode == "MATERIALIZED"
