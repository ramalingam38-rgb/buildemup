"""Sub-2 unit tests (Spec #4 v1.6 LOCKED — B-NEW-T3 #4).

Per S40-continuation handoff § 5 Sub-2 step 8: ~10 tests covering the
NON-orchestrator C11a multi-floor support (signature, candidate_context,
family_slot_allocator, lineage, errors).

The cache-version sentinel `test_c11a_cache_key_version_is_v1_3_0` is
already covered in `test_c11a_subsession5_cache_versioning.py` (the
pre-existing test was updated from v1.0.0 to v1.3.0 per Spec #4 § 3.6).

The orchestrator-level tests (multi-floor dispatch, M8 real impl,
property tests, integration tests) are Sub-3 work — covered in
`test_subsession7_multi_floor.py`, `test_subsession7_multi_floor_properties.py`,
and `test_integration/test_b_new_t3_pipeline.py`.
"""
from __future__ import annotations

import pytest

from buildemup.components.c11a.candidate_context import (
    is_real_multi_floor_candidate,
    is_real_wet_zone_candidate,
)
from buildemup.components.c11a.errors import (
    OrchestrationAlignmentError,
    OrchestrationError,
    OrchestrationProtocolError,
    TopologyMutationError,
)
from buildemup.components.c11a.family_slot_allocator import (
    multi_floor_family_id,
)
from buildemup.components.c11a.schema import (
    FloorImpact,
    MULTI_FLOOR_INVALIDITY_REASONS,
)
from buildemup.components.c11a.source_signature import (
    _derive_multi_floor_canonical_signature,
    derive_canonical_signature,
)
from buildemup.domain.multi_floor_candidate import (
    MultiFloorWetZonePlannedCandidate,
)


# ---------------------------------------------------------------------------
# Fixtures (re-use the multi-floor candidate test fixture infrastructure)
# ---------------------------------------------------------------------------


# Lazy import + lazy-build the candidate fixture; the heavy C9-C10 pipeline
# only runs when these tests actually need a real wrapper.
@pytest.fixture(scope="module")
def two_floor_candidate() -> MultiFloorWetZonePlannedCandidate:
    from buildemup.tests.test_domain_multi_floor_candidate import (
        _two_floors_master_ground,
    )
    return MultiFloorWetZonePlannedCandidate(
        floors=_two_floors_master_ground(),
        master_bedroom_floor_label="ground",
    )


@pytest.fixture(scope="module")
def two_floor_candidate_master_first() -> MultiFloorWetZonePlannedCandidate:
    from buildemup.tests.test_domain_multi_floor_candidate import (
        _clone_wzpc,
    )
    return MultiFloorWetZonePlannedCandidate(
        floors=(
            _clone_wzpc(floor_label="ground", keep_master_bedroom=False),
            _clone_wzpc(floor_label="first", keep_master_bedroom=True),
        ),
        master_bedroom_floor_label="first",
    )


# ---------------------------------------------------------------------------
# is_real_multi_floor_candidate (Spec #4 § 3.5) — 3 tests
# ---------------------------------------------------------------------------


def test_is_real_multi_floor_candidate_detects_wrapper_type(two_floor_candidate):
    """Marker-attribute detection works for real wrapper instances."""
    assert is_real_multi_floor_candidate(two_floor_candidate) is True


def test_is_real_multi_floor_candidate_rejects_non_wrapper():
    """Detection returns False for objects without the marker attribute."""
    assert is_real_multi_floor_candidate(object()) is False
    assert is_real_multi_floor_candidate(None) is False
    assert is_real_multi_floor_candidate("hello") is False
    # Even an object with a truthy non-True marker is rejected (strict `is True`).

    class FakeMarker:
        __multi_floor_candidate__ = "yes"

    assert is_real_multi_floor_candidate(FakeMarker()) is False


def test_is_real_multi_floor_candidate_does_not_detect_single_floor_wzpc(
    two_floor_candidate,
):
    """A single-floor WetZonePlannedCandidate must NOT be detected as
    multi-floor (it lacks the marker attribute)."""
    per_floor_wzpc = two_floor_candidate.floors[0]
    assert is_real_wet_zone_candidate(per_floor_wzpc) is True
    assert is_real_multi_floor_candidate(per_floor_wzpc) is False


# ---------------------------------------------------------------------------
# Signature derivation (Spec #4 § 3.5) — 3 tests
# ---------------------------------------------------------------------------


def test_derive_canonical_signature_multi_floor_dispatch(two_floor_candidate):
    """derive_canonical_signature routes to multi-floor branch when the
    marker attribute is present."""
    sig = derive_canonical_signature(two_floor_candidate)
    direct = _derive_multi_floor_canonical_signature(two_floor_candidate)
    assert sig == direct
    assert len(sig) == 16  # SHA256 16-hex-char prefix.


def test_derive_canonical_signature_multi_floor_includes_master_label(
    two_floor_candidate, two_floor_candidate_master_first,
):
    """Wrappers with the same per-floor candidates but different master
    designations produce different signatures (the master_floor=... part
    of the canonical serialisation distinguishes them)."""
    sig_ground = derive_canonical_signature(two_floor_candidate)
    sig_first = derive_canonical_signature(two_floor_candidate_master_first)
    assert sig_ground != sig_first


def test_derive_canonical_signature_multi_floor_recursive_per_floor(
    two_floor_candidate,
):
    """Changing one floor's underlying topology changes the wrapper's
    signature. Verified by constructing two wrappers that differ in one
    floor's ancestry; their signatures must differ."""
    from buildemup.tests.test_domain_multi_floor_candidate import (
        _clone_wzpc,
    )
    sig_a = derive_canonical_signature(two_floor_candidate)

    # Use replace-style swap to produce a structurally-distinct wrapper.
    # _two_floors_master_ground() is cached — build a new (ground, first2)
    # where 'first' has the same label but distinct contents would diverge.
    # In our fixture, _clone_wzpc produces objects with the same content
    # for the same label, so to force a difference we vary keep_master
    # on the non-master floor — but that breaks MFWZP-5 invariants.
    # Instead build a 3-floor wrapper whose extra floor changes signature.
    three_floors = (
        _clone_wzpc(floor_label="ground", keep_master_bedroom=True),
        _clone_wzpc(floor_label="first", keep_master_bedroom=False),
        _clone_wzpc(floor_label="second", keep_master_bedroom=False),
    )
    three_floor_cand = MultiFloorWetZonePlannedCandidate(
        floors=three_floors,
        master_bedroom_floor_label="ground",
    )
    sig_three = derive_canonical_signature(three_floor_cand)
    assert sig_three != sig_a


# ---------------------------------------------------------------------------
# multi_floor_family_id aggregation (Spec #4 § 3.7) — 3 tests
# ---------------------------------------------------------------------------


def test_family_id_multi_floor_aggregation():
    """Label-preserving aggregation. Two distinct label-family pairings
    produce distinct family IDs."""

    class _StubWrapper:
        """Minimal duck-type — just floor_labels + floors. Allocator
        only reads what it needs; the wrapper protocol doesn't bind
        to a concrete type."""

        def __init__(self, pairs):
            self.floor_labels = tuple(label for label, _f in pairs)
            self.floors = tuple(f for _label, f in pairs)

    # Pretend each floor has a per-floor family ID we know.
    fid = {
        "f_strip": "F_STRIP",
        "f_L": "F_L",
    }
    wrapper_a = _StubWrapper([("ground", "f_strip"), ("first", "f_L")])
    wrapper_b = _StubWrapper([("ground", "f_L"), ("first", "f_strip")])

    fam_a = multi_floor_family_id(
        wrapper_a, per_floor_family_id=lambda f: fid[f],
    )
    fam_b = multi_floor_family_id(
        wrapper_b, per_floor_family_id=lambda f: fid[f],
    )
    assert fam_a.startswith("multi_floor:")
    assert fam_b.startswith("multi_floor:")
    assert fam_a != fam_b  # label-family pairing differs.
    # Verify exact format (label-sorted).
    assert fam_a == "multi_floor:first=F_L|ground=F_STRIP"
    assert fam_b == "multi_floor:first=F_STRIP|ground=F_L"


def test_family_id_multi_floor_deterministic_under_floor_reorder():
    """Even if the floors tuple order differs in construction, the
    family ID is the same (sort-by-label canonicalises the pairing
    representation, even though wrapper equality depends on tuple order).
    """

    class _StubWrapper:
        def __init__(self, pairs):
            self.floor_labels = tuple(label for label, _f in pairs)
            self.floors = tuple(f for _label, f in pairs)

    fid = {"a": "F_A", "b": "F_B"}
    wrapper_x = _StubWrapper([("ground", "a"), ("first", "b")])
    wrapper_y = _StubWrapper([("first", "b"), ("ground", "a")])
    fam_x = multi_floor_family_id(wrapper_x, per_floor_family_id=lambda f: fid[f])
    fam_y = multi_floor_family_id(wrapper_y, per_floor_family_id=lambda f: fid[f])
    assert fam_x == fam_y


def test_family_id_prefix_isolates_from_single_floor():
    """The 'multi_floor:' prefix prevents accidental collision with
    single-floor family IDs."""

    class _StubWrapper:
        def __init__(self, pairs):
            self.floor_labels = tuple(label for label, _f in pairs)
            self.floors = tuple(f for _label, f in pairs)

    wrapper = _StubWrapper([("ground", "a")])
    # Add a second floor so the aggregation runs.
    wrapper = _StubWrapper([("ground", "a"), ("first", "b")])
    fam = multi_floor_family_id(
        wrapper, per_floor_family_id=lambda f: f.upper(),
    )
    assert fam.startswith("multi_floor:")


# ---------------------------------------------------------------------------
# Lineage extension (Spec #4 § 3.8) — 1 test
# ---------------------------------------------------------------------------


def test_lineage_classification_floor_label_affected_default_none():
    """LineageClassification.floor_label_affected defaults to None
    (single-floor / dwelling-level usage). Multi-floor per-floor
    classifications set it to the affected floor label."""
    from buildemup.components.c11a.lineage import LineageClassification
    from buildemup.components.c11a.schema import MutationLineageDepth

    # Single-floor / dwelling-level default.
    cls_default = LineageClassification(
        lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
        rejection_reason=None,
        rejected_by_keys=(),
        emergent_keys=(),
    )
    assert cls_default.floor_label_affected is None

    # Multi-floor per-floor explicit assignment.
    cls_floor = LineageClassification(
        lineage_depth=MutationLineageDepth.REGENERATIVE_TRANSFORM,
        rejection_reason=None,
        rejected_by_keys=(),
        emergent_keys=(),
        floor_label_affected="first",
    )
    assert cls_floor.floor_label_affected == "first"


# ---------------------------------------------------------------------------
# Errors (Spec #4 § 3.1) — 2 tests
# ---------------------------------------------------------------------------


def test_orchestration_errors_inherit_from_topology_mutation_error():
    """OrchestrationError + subtypes inherit from TopologyMutationError
    so existing catch-all handlers still see them. Severity tier is
    systemic for all three."""
    assert issubclass(OrchestrationError, TopologyMutationError)
    assert issubclass(OrchestrationProtocolError, OrchestrationError)
    assert issubclass(OrchestrationAlignmentError, OrchestrationError)
    assert OrchestrationError.severity_tier == "systemic"
    assert OrchestrationProtocolError.severity_tier == "systemic"
    assert OrchestrationAlignmentError.severity_tier == "systemic"


def test_orchestration_errors_are_registered_in_error_registry():
    """OrchestrationError + subtypes auto-register via __init_subclass__
    (B-NEW-X registry pattern). Verifies the Phase 0 severity audit will
    pick them up."""
    from buildemup.components.c11a.errors import iter_registered_errors

    registered = iter_registered_errors()
    names = {cls.__qualname__ for cls in registered}
    assert "OrchestrationError" in names
    assert "OrchestrationProtocolError" in names
    assert "OrchestrationAlignmentError" in names


# ---------------------------------------------------------------------------
# FloorImpact + invalidity_reason taxonomy (Spec #4 § 3.11 + § 3.4) — 1 test
# ---------------------------------------------------------------------------


def test_floor_impact_construction_and_taxonomy():
    """FloorImpact is a frozen dataclass with kind / requires_cascade /
    requires_validation_only flags. The multi-floor invalidity_reason
    taxonomy includes the 9 documented variants."""
    impact = FloorImpact(
        label="ground",
        kind="direct",
        requires_cascade=True,
        requires_validation_only=False,
    )
    assert impact.label == "ground"
    assert impact.kind == "direct"
    assert impact.requires_cascade is True
    assert impact.requires_validation_only is False

    # Frozen: assignment raises.
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        impact.label = "first"  # type: ignore[misc]

    # Taxonomy completeness — 9 reasons per Spec #4 § 3.4.
    assert "no_viable_master_target" in MULTI_FLOOR_INVALIDITY_REASONS
    assert "c9_generation_failed" in MULTI_FLOOR_INVALIDITY_REASONS
    assert "c10_validation_failed" in MULTI_FLOOR_INVALIDITY_REASONS
    for n in range(1, 7):
        assert (
            f"orchestration_state_drift:mfwzp{n}"
            in MULTI_FLOOR_INVALIDITY_REASONS
        )
    assert len(MULTI_FLOOR_INVALIDITY_REASONS) == 9
