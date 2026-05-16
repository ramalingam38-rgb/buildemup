"""
BuildemUp — Component 14 — foundational layer tests
=====================================================

Per C14 SPEC v0.2 LOCKED. Sub-session 1 target: ~40 tests covering:

- versioning constants present and well-formed
- errors hierarchy properly structured
- contracts module: RoomMetadata defensive checks + 4 category sets
  + EXTERNAL placeholder re-export from C13
- config: CirculationConfig defaults + __post_init__ validation
- cache_keys: derive_c14_cache_keys + config_signature_for determinism
- schema: every Inv enforced at __post_init__:
  - E2 (nodes lex-ASC + unique)
  - E3' (edges lex-ASC, endpoints in nodes, EXTERNAL exclusion is
        constructor-side, schema verifies sort)
  - E4 (primary_edges ⊆ edges + sorted)
  - E5 (per-room metric tuples cover nodes lex-ASC)
  - E6-analog (exactly one room has step_depth == 0)
  - E10 (mean_depth ≤ max_depth ≤ k-1)
  - E11' (raw_RA ≥ 0)
  - E11'' (real_RA nan for k<4, in [0, ~2] for k≥4)
  - E12' (integration nan for k<4, ≥0 for k≥4)
  - E13' truncation cardinality (at most one TRUNCATION_META per tuple)
  - E16 (provenance triple non-empty / non-negative)
  - E17 (graph_size_category consistent with k)
  - E18 (category_coverage ∈ [0, 1])
- Both StructuralCirculationFlagKind and PreferenceCirculationFlagKind
  exist as distinct enums (per A4) BUT share TRUNCATION_META string value
- Typestate discipline: Successful vs Failed don't overlap; signatures
  must match between wrapper and inner record
- BatchResult: tuples sorted, no signature overlap between succ/failed

Each test is small + named. Aiming for ≥40 to hit the spec target.
"""
from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from typing import get_args

import pytest

from buildemup.components.c14 import (
    # versioning
    C14_METRIC_VERSION,
    C14_VERSION,
    DEFAULT_BETWEENNESS_THRESHOLD,
    DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD,
    DEFAULT_EXCESSIVE_DEPTH_THRESHOLD,
    DEFAULT_FLAG_DENSITY_FACTOR,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    EXPECTED_C13_VERSION,
    GRAPH_SIZE_NORMAL_MIN,
    SMALL_GRAPH_REGIME_SMALL,
    SMALL_GRAPH_REGIME_TINY,
    # errors
    C14ConfigurationError,
    CirculationAnalysisError,
    EntryRoomNotFoundError,
    GraphInconsistencyError,
    LocalCirculationError,
    PerCandidateCirculationError,
    UpstreamSchemaDriftError,
    # contracts
    ALL_RECOGNIZED_CATEGORY_KEYWORDS,
    BEDROOM_CATEGORY_KEYWORDS,
    CIRCULATION_CATEGORY_KEYWORDS,
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    PRIVATE_CATEGORY_KEYWORDS,
    PUBLIC_CATEGORY_KEYWORDS,
    RoomMetadata,
    # config
    CirculationConfig,
    # cache_keys
    C14CacheKeys,
    config_signature_for,
    derive_c14_cache_keys,
    # schema
    CirculationAnalysisBatchResult,
    CirculationFlag,
    CirculationGraphReport,
    FailedCirculationAnalysis,
    FailureRecord,
    PreferenceCirculationFlagKind,
    StructuralCirculationFlagKind,
    SuccessfulCirculationAnalysis,
    TRUNCATION_META_KIND_VALUE,
)


# =============================================================================
# Helpers
# =============================================================================

def _minimal_cache_keys() -> C14CacheKeys:
    """Construct a valid C14CacheKeys triple for schema tests."""
    return derive_c14_cache_keys(
        c13_cache_key="c13:abcdef",
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        config_signature="density=0.750000|betweenness=0.700000|depth=5|cat_cov_low=0.500000",
    )


def _two_node_report(
    sig: str = "cand_001",
) -> CirculationGraphReport:
    """A valid minimal 2-node graph for happy-path tests.

    Tiny regime: k=2 → graph_size_category="tiny", RRA + integration = nan.
    """
    return CirculationGraphReport(
        source_placed_candidate_signature=sig,
        nodes=("entry_01", "living_01"),
        edges=(("entry_01", "living_01"),),
        primary_edges=(("entry_01", "living_01"),),
        step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
        connectivity=(("entry_01", 1), ("living_01", 1)),
        betweenness_rank=(("entry_01", 1), ("living_01", 2)),
        mean_depth=0.5,
        max_depth=1,
        raw_relative_asymmetry=0.0,
        real_relative_asymmetry=float("nan"),
        integration=float("nan"),
        graph_size_category="tiny",
        structural_flags=(),
        preference_flags=(),
        upstream_advisory_flags=(),
        c14_advisory_flags=(),
        category_coverage=1.0,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        cache_keys=_minimal_cache_keys(),
    )


def _four_node_normal_report(
    sig: str = "cand_004",
) -> CirculationGraphReport:
    """A valid 4-node hub-and-spoke layout (normal regime).

    Living is the hub; entry / kitchen / bedroom connect only through it.
    """
    return CirculationGraphReport(
        source_placed_candidate_signature=sig,
        nodes=("bedroom_01", "entry_01", "kitchen_01", "living_01"),
        edges=(
            ("bedroom_01", "living_01"),
            ("entry_01", "living_01"),
            ("kitchen_01", "living_01"),
        ),
        primary_edges=(
            ("bedroom_01", "living_01"),
            ("entry_01", "living_01"),
            ("kitchen_01", "living_01"),
        ),
        step_depth_from_entry=(
            ("bedroom_01", 2),
            ("entry_01", 0),
            ("kitchen_01", 2),
            ("living_01", 1),
        ),
        connectivity=(
            ("bedroom_01", 1),
            ("entry_01", 1),
            ("kitchen_01", 1),
            ("living_01", 3),
        ),
        betweenness_rank=(
            ("bedroom_01", 2),
            ("entry_01", 3),
            ("kitchen_01", 4),
            ("living_01", 1),
        ),
        mean_depth=1.25,
        max_depth=2,
        raw_relative_asymmetry=0.25,
        real_relative_asymmetry=0.25,
        integration=4.0,
        graph_size_category="normal",
        structural_flags=(),
        preference_flags=(),
        upstream_advisory_flags=(),
        c14_advisory_flags=(),
        category_coverage=1.0,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        cache_keys=_minimal_cache_keys(),
    )


# =============================================================================
# 1. Versioning constants
# =============================================================================

def test_versioning_c14_version_is_v0_2():
    """C14_VERSION is LOCKED at v0.2 per S46 Ramalingam directive."""
    assert C14_VERSION == "v0.2"


def test_versioning_metric_version_is_2():
    """C14_METRIC_VERSION = 2 (bumped from 1 by v0.2 A1 RA→RRA)."""
    assert C14_METRIC_VERSION == 2


def test_versioning_expected_upstream_c13_v1_0():
    """C14 was built against C13 v1.0 LOCKED at S45."""
    assert EXPECTED_C13_VERSION == "v1.0"
    assert EXPECTED_ADVISORY_SCHEMA_VERSION == 1


def test_versioning_default_thresholds_match_spec():
    """Defaults match v0.1 § 1.3 / v0.2 A6 / v0.2 A8."""
    assert DEFAULT_FLAG_DENSITY_FACTOR == 0.75
    assert DEFAULT_BETWEENNESS_THRESHOLD == 0.7
    assert DEFAULT_EXCESSIVE_DEPTH_THRESHOLD == 5
    assert DEFAULT_CATEGORY_COVERAGE_LOW_THRESHOLD == 0.5


def test_versioning_graph_size_regime_partition_is_disjoint_and_complete():
    """Per Inv E17, regimes partition the positive integers cleanly.

    {1,2} ∪ {3} ∪ {4,5,6,...} = ℕ⁺ with no overlap.
    """
    assert SMALL_GRAPH_REGIME_TINY == frozenset({1, 2})
    assert SMALL_GRAPH_REGIME_SMALL == frozenset({3})
    assert GRAPH_SIZE_NORMAL_MIN == 4
    # No overlap
    assert SMALL_GRAPH_REGIME_TINY.isdisjoint(SMALL_GRAPH_REGIME_SMALL)


# =============================================================================
# 2. Error hierarchy
# =============================================================================

def test_errors_base_class_is_exception():
    """CirculationAnalysisError descends from Exception."""
    assert issubclass(CirculationAnalysisError, Exception)


def test_errors_local_and_per_candidate_tiers():
    """Two-tier hierarchy mirrors C13."""
    assert issubclass(LocalCirculationError, CirculationAnalysisError)
    assert issubclass(PerCandidateCirculationError, CirculationAnalysisError)
    # Local and per-candidate do NOT inherit from each other.
    assert not issubclass(LocalCirculationError, PerCandidateCirculationError)
    assert not issubclass(PerCandidateCirculationError, LocalCirculationError)


def test_errors_local_subtypes():
    """UpstreamSchemaDriftError + C14ConfigurationError are LocalCirculationError."""
    assert issubclass(UpstreamSchemaDriftError, LocalCirculationError)
    assert issubclass(C14ConfigurationError, LocalCirculationError)


def test_errors_per_candidate_subtypes():
    """EntryRoomNotFoundError + GraphInconsistencyError are PerCandidate."""
    assert issubclass(EntryRoomNotFoundError, PerCandidateCirculationError)
    assert issubclass(GraphInconsistencyError, PerCandidateCirculationError)


# =============================================================================
# 3. Contracts: EXTERNAL re-export + category keyword sets
# =============================================================================

def test_external_envelope_placeholder_value():
    """Per v0.2 A2: EXTERNAL placeholder is the string "EXTERNAL"."""
    assert EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID == "EXTERNAL"


def test_external_envelope_placeholder_is_re_exported_from_c13():
    """A2 requires that C14's EXTERNAL exclusion use the SAME constant
    as C13 (no string-literal duplication)."""
    from buildemup.components.c13 import (
        EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID as C13_EXT,
    )
    assert EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID is C13_EXT or EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID == C13_EXT


def test_category_keywords_bedroom_set():
    """Per v0.2 A8 — bedroom keyword set."""
    expected = {"bedroom", "master_bedroom", "guest_bedroom", "kids_bedroom"}
    assert BEDROOM_CATEGORY_KEYWORDS == expected


def test_category_keywords_public_set():
    """Per v0.2 A8 — public keyword set."""
    expected = {"living", "dining", "family", "lounge", "kitchen"}
    assert PUBLIC_CATEGORY_KEYWORDS == expected


def test_category_keywords_private_includes_bedrooms():
    """Per v0.2 A8 — private keyword set is a SUPERSET of bedroom keywords
    + bathroom/study/pooja."""
    assert BEDROOM_CATEGORY_KEYWORDS <= PRIVATE_CATEGORY_KEYWORDS
    assert "bathroom" in PRIVATE_CATEGORY_KEYWORDS
    assert "study" in PRIVATE_CATEGORY_KEYWORDS
    assert "pooja" in PRIVATE_CATEGORY_KEYWORDS


def test_category_keywords_circulation_set():
    """Per v0.2 A8 — circulation keyword set."""
    expected = {"corridor", "foyer", "staircase"}
    assert CIRCULATION_CATEGORY_KEYWORDS == expected


def test_category_keywords_all_includes_main_entrance():
    """ALL_RECOGNIZED includes main_entrance (the C13 main-entry category)."""
    assert "main_entrance" in ALL_RECOGNIZED_CATEGORY_KEYWORDS
    # All five sets contribute.
    assert BEDROOM_CATEGORY_KEYWORDS <= ALL_RECOGNIZED_CATEGORY_KEYWORDS
    assert PUBLIC_CATEGORY_KEYWORDS <= ALL_RECOGNIZED_CATEGORY_KEYWORDS
    assert PRIVATE_CATEGORY_KEYWORDS <= ALL_RECOGNIZED_CATEGORY_KEYWORDS
    assert CIRCULATION_CATEGORY_KEYWORDS <= ALL_RECOGNIZED_CATEGORY_KEYWORDS


def test_category_keyword_sets_are_frozen():
    """All four sets are frozensets (immutable)."""
    for s in (
        BEDROOM_CATEGORY_KEYWORDS,
        PUBLIC_CATEGORY_KEYWORDS,
        PRIVATE_CATEGORY_KEYWORDS,
        CIRCULATION_CATEGORY_KEYWORDS,
        ALL_RECOGNIZED_CATEGORY_KEYWORDS,
    ):
        assert isinstance(s, frozenset)


# =============================================================================
# 4. RoomMetadata
# =============================================================================

def test_room_metadata_happy_path():
    rm = RoomMetadata(
        room_id="bedroom_01",
        category="bedroom",
        is_main_entry_room=False,
    )
    assert rm.room_id == "bedroom_01"
    assert rm.category == "bedroom"
    assert rm.is_main_entry_room is False
    assert rm.is_secondary_door_owner is False  # default


def test_room_metadata_is_frozen():
    rm = RoomMetadata(room_id="x", category="bedroom", is_main_entry_room=False)
    with pytest.raises(FrozenInstanceError):
        rm.category = "kitchen"  # type: ignore[misc]


def test_room_metadata_rejects_empty_room_id():
    with pytest.raises(ValueError, match="non-empty"):
        RoomMetadata(room_id="", category="bedroom", is_main_entry_room=False)


def test_room_metadata_rejects_non_string_category():
    with pytest.raises(TypeError, match="str"):
        RoomMetadata(
            room_id="x", category=42, is_main_entry_room=False  # type: ignore[arg-type]
        )


# =============================================================================
# 5. CirculationConfig
# =============================================================================

def test_config_defaults_match_spec():
    c = CirculationConfig()
    assert c.per_candidate_wallclock_seconds == 0.5
    assert c.flag_density_factor == 0.75
    assert c.betweenness_threshold == 0.7
    assert c.excessive_depth_threshold == 5
    assert c.category_coverage_low_threshold == 0.5
    assert c.strict_mode is True
    assert c.cache_mode == "strict"


def test_config_is_frozen():
    c = CirculationConfig()
    with pytest.raises(FrozenInstanceError):
        c.strict_mode = False  # type: ignore[misc]


def test_config_rejects_negative_wallclock():
    with pytest.raises(C14ConfigurationError, match="wallclock"):
        CirculationConfig(per_candidate_wallclock_seconds=-1.0)


def test_config_rejects_zero_wallclock():
    with pytest.raises(C14ConfigurationError, match="wallclock"):
        CirculationConfig(per_candidate_wallclock_seconds=0.0)


def test_config_rejects_negative_flag_density():
    with pytest.raises(C14ConfigurationError, match="density"):
        CirculationConfig(flag_density_factor=-0.1)


def test_config_rejects_betweenness_out_of_range():
    with pytest.raises(C14ConfigurationError, match="betweenness"):
        CirculationConfig(betweenness_threshold=1.5)
    with pytest.raises(C14ConfigurationError, match="betweenness"):
        CirculationConfig(betweenness_threshold=-0.1)


def test_config_rejects_negative_depth_threshold():
    with pytest.raises(C14ConfigurationError, match="depth"):
        CirculationConfig(excessive_depth_threshold=-1)


def test_config_rejects_invalid_cache_mode():
    with pytest.raises(C14ConfigurationError, match="cache_mode"):
        CirculationConfig(cache_mode="aggressive")  # type: ignore[arg-type]


# =============================================================================
# 6. Cache keys
# =============================================================================

def test_cache_keys_deterministic_across_calls():
    """Same inputs → same digest. Replay determinism (Inv E7)."""
    a = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version="v0.2",
        c14_metric_version=2,
        config_signature="density=0.75",
    )
    b = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version="v0.2",
        c14_metric_version=2,
        config_signature="density=0.75",
    )
    assert a == b
    assert a.metric_cache_key == b.metric_cache_key


def test_cache_keys_differ_when_c13_key_changes():
    a = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version="v0.2",
        c14_metric_version=2,
        config_signature="density=0.75",
    )
    b = derive_c14_cache_keys(
        c13_cache_key="c13:y",
        c14_version="v0.2",
        c14_metric_version=2,
        config_signature="density=0.75",
    )
    assert a.metric_cache_key != b.metric_cache_key


def test_cache_keys_differ_when_metric_version_changes():
    """v0.2 A1 rationale: metric_version bump must invalidate caches."""
    a = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version="v0.2",
        c14_metric_version=1,
        config_signature="s",
    )
    b = derive_c14_cache_keys(
        c13_cache_key="c13:x",
        c14_version="v0.2",
        c14_metric_version=2,
        config_signature="s",
    )
    assert a.metric_cache_key != b.metric_cache_key


def test_cache_keys_reject_empty_c13_key():
    with pytest.raises(ValueError):
        derive_c14_cache_keys(
            c13_cache_key="",
            c14_version="v0.2",
            c14_metric_version=2,
            config_signature="s",
        )


def test_cache_keys_dataclass_rejects_empty_fields():
    with pytest.raises(ValueError):
        C14CacheKeys(c13_cache_key="", metric_cache_key="m", full_cache_key="f")


def test_config_signature_for_is_deterministic():
    s1 = config_signature_for(
        flag_density_factor=0.75,
        betweenness_threshold=0.7,
        excessive_depth_threshold=5,
        category_coverage_low_threshold=0.5,
    )
    s2 = config_signature_for(
        flag_density_factor=0.75,
        betweenness_threshold=0.7,
        excessive_depth_threshold=5,
        category_coverage_low_threshold=0.5,
    )
    assert s1 == s2


# =============================================================================
# 7. Flag-kind enums (per A4 + A6)
# =============================================================================

def test_structural_enum_values_per_a4_and_a8_and_a6():
    """Per A4, A8, A6 — all four structural flag kinds present."""
    values = {fk.value for fk in StructuralCirculationFlagKind}
    assert values == {
        "bottleneck_concentration",
        "dead_end_isolation",
        "category_coverage_low",
        "truncation_meta",
    }


def test_preference_enum_values_per_a4_and_a6():
    """Per A4 + A6 — all four preference flag kinds present."""
    values = {fk.value for fk in PreferenceCirculationFlagKind}
    assert values == {
        "transit_through_bedroom",
        "privacy_gradient_violation",
        "excessive_depth",
        "truncation_meta",
    }


def test_truncation_meta_string_is_shared_per_a6():
    """Per A6: same string value in both enums."""
    assert (
        StructuralCirculationFlagKind.TRUNCATION_META.value
        == PreferenceCirculationFlagKind.TRUNCATION_META.value
        == TRUNCATION_META_KIND_VALUE
        == "truncation_meta"
    )


def test_structural_and_preference_enums_are_distinct_types():
    """Per A4: split prevents downstream from collapsing the categories."""
    assert StructuralCirculationFlagKind is not PreferenceCirculationFlagKind
    # And their non-truncation values don't overlap.
    s_non_trunc = {
        fk.value
        for fk in StructuralCirculationFlagKind
        if fk.value != TRUNCATION_META_KIND_VALUE
    }
    p_non_trunc = {
        fk.value
        for fk in PreferenceCirculationFlagKind
        if fk.value != TRUNCATION_META_KIND_VALUE
    }
    assert s_non_trunc.isdisjoint(p_non_trunc)


# =============================================================================
# 8. CirculationFlag construction + defensive checks
# =============================================================================

def test_circulation_flag_happy_path_structural():
    f = CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.BOTTLENECK_CONCENTRATION,
        affected_room_id="living_01",
        severity="warning",
        explanation_template="Room {room} has high betweenness.",
        deduplication_key="bottleneck:living_01",
    )
    assert f.flag_kind == StructuralCirculationFlagKind.BOTTLENECK_CONCENTRATION


def test_circulation_flag_happy_path_preference_default_info():
    """Per A10: preference flags default to severity=info.

    (The dataclass requires explicit severity, but emission code uses
    info by default — this test confirms info is a VALID severity.)
    """
    f = CirculationFlag(
        flag_kind=PreferenceCirculationFlagKind.EXCESSIVE_DEPTH,
        affected_room_id="bedroom_03",
        severity="info",
        explanation_template="Room {room} depth exceeds threshold.",
        deduplication_key="excessive_depth:bedroom_03",
    )
    assert f.severity == "info"


def test_circulation_flag_truncation_meta_allows_empty_affected_room():
    """Per A6: TRUNCATION_META is a meta-flag, not tied to one room."""
    f = CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.TRUNCATION_META,
        affected_room_id="",  # OK for meta-flag
        severity="info",
        explanation_template="3 flags suppressed (BOTTLENECK_CONCENTRATION, ...).",
        deduplication_key="truncation_meta:structural",
    )
    assert f.affected_room_id == ""


def test_circulation_flag_rejects_empty_affected_room_for_non_meta():
    with pytest.raises(ValueError, match="empty ONLY for"):
        CirculationFlag(
            flag_kind=StructuralCirculationFlagKind.BOTTLENECK_CONCENTRATION,
            affected_room_id="",
            severity="warning",
            explanation_template="x",
            deduplication_key="x",
        )


def test_circulation_flag_rejects_bad_severity():
    with pytest.raises(ValueError, match="severity"):
        CirculationFlag(
            flag_kind=StructuralCirculationFlagKind.DEAD_END_ISOLATION,
            affected_room_id="bedroom_02",
            severity="catastrophic",  # type: ignore[arg-type]
            explanation_template="x",
            deduplication_key="x",
        )


def test_circulation_flag_rejects_empty_explanation():
    with pytest.raises(ValueError, match="explanation_template"):
        CirculationFlag(
            flag_kind=PreferenceCirculationFlagKind.TRANSIT_THROUGH_BEDROOM,
            affected_room_id="bedroom_01",
            severity="info",
            explanation_template="",
            deduplication_key="x",
        )


def test_circulation_flag_rejects_empty_dedup_key():
    with pytest.raises(ValueError, match="deduplication_key"):
        CirculationFlag(
            flag_kind=PreferenceCirculationFlagKind.PRIVACY_GRADIENT_VIOLATION,
            affected_room_id="bedroom_01",
            severity="info",
            explanation_template="x",
            deduplication_key="",
        )


def test_circulation_flag_rejects_non_enum_kind():
    with pytest.raises(TypeError, match="flag_kind"):
        CirculationFlag(
            flag_kind="bottleneck_concentration",  # type: ignore[arg-type]
            affected_room_id="x",
            severity="info",
            explanation_template="x",
            deduplication_key="x",
        )


def test_circulation_flag_is_frozen():
    f = CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.BOTTLENECK_CONCENTRATION,
        affected_room_id="living_01",
        severity="warning",
        explanation_template="x",
        deduplication_key="x",
    )
    with pytest.raises(FrozenInstanceError):
        f.severity = "concern"  # type: ignore[misc]


# =============================================================================
# 9. CirculationGraphReport happy paths
# =============================================================================

def test_report_two_node_happy_path():
    r = _two_node_report()
    assert r.graph_size_category == "tiny"
    assert math.isnan(r.real_relative_asymmetry)
    assert math.isnan(r.integration)
    assert r.category_coverage == 1.0


def test_report_four_node_normal_happy_path():
    r = _four_node_normal_report()
    assert r.graph_size_category == "normal"
    assert not math.isnan(r.real_relative_asymmetry)
    assert r.integration == 4.0


def test_report_is_frozen():
    r = _two_node_report()
    with pytest.raises(FrozenInstanceError):
        r.mean_depth = 999.0  # type: ignore[misc]


def test_report_is_hashable_no_nan_fields():
    """Frozen dataclasses with hashable, non-NaN fields produce stable hashes.

    Tests Inv E7 byte-equal replay determinism: two identical reports
    constructed from identical inputs must compare equal AND hash equal.

    Note: reports containing float('nan') (e.g. tiny/small regime k<4)
    will NOT compare equal because NaN != NaN by IEEE 754. This is a
    Python-level quirk, not a spec violation — Inv E7 is about byte-equal
    OUTPUT determinism, which orchestrator-level tests verify separately
    via serialization. See test_report_with_nan_is_still_hashable below.
    """
    r1 = _four_node_normal_report()
    r2 = _four_node_normal_report()
    assert r1 == r2
    assert hash(r1) == hash(r2)


def test_report_with_nan_is_still_hashable():
    """Reports with NaN-valued metric fields (k<4 regime) are still
    hashable individually — `hash()` must succeed even when `==`
    won't due to NaN semantics."""
    r = _two_node_report()
    h = hash(r)  # must not raise
    assert isinstance(h, int)


# =============================================================================
# 10. Schema invariants — E2 (nodes sort)
# =============================================================================

def test_report_rejects_unsorted_nodes_inv_e2():
    with pytest.raises(ValueError, match="E2"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("living_01", "entry_01"),  # NOT sorted
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_rejects_duplicate_nodes_inv_e2():
    with pytest.raises(ValueError, match="E2"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "entry_01"),  # duplicate
            edges=(),
            primary_edges=(),
            step_depth_from_entry=(("entry_01", 0), ("entry_01", 1)),
            connectivity=(("entry_01", 0), ("entry_01", 0)),
            betweenness_rank=(("entry_01", 1), ("entry_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 11. Schema invariants — E3' (edges sort + endpoints in nodes + a<=b)
# =============================================================================

def test_report_rejects_unsorted_edges_inv_e3_prime():
    """Sorted nodes, two edges in reverse-sorted order — E3' should fire."""
    with pytest.raises(ValueError, match="E3'"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("bedroom_01", "entry_01", "living_01"),
            # edges sorted-by-tuple would be:
            #   ("bedroom_01","living_01"), ("entry_01","living_01")
            # We pass them reversed to trigger E3' (NOT E2 — nodes are sorted).
            edges=(
                ("entry_01", "living_01"),
                ("bedroom_01", "living_01"),
            ),
            primary_edges=(),
            step_depth_from_entry=(
                ("bedroom_01", 2),
                ("entry_01", 0),
                ("living_01", 1),
            ),
            connectivity=(
                ("bedroom_01", 1),
                ("entry_01", 1),
                ("living_01", 2),
            ),
            betweenness_rank=(
                ("bedroom_01", 2),
                ("entry_01", 3),
                ("living_01", 1),
            ),
            mean_depth=1.0,
            max_depth=2,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),  # k=3 → nan
            integration=float("nan"),
            graph_size_category="small",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_rejects_edge_with_unknown_endpoint():
    """Inv E3': edge endpoints must be in nodes."""
    with pytest.raises(ValueError, match="unknown room_id"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "ghost_room"),),  # endpoint not in nodes
            primary_edges=(),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_rejects_edge_with_a_greater_than_b():
    """Inv E3': each edge must satisfy room_a <= room_b lex-ASC."""
    with pytest.raises(ValueError, match="room_a <= room_b"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("living_01", "entry_01"),),  # reversed
            primary_edges=(),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 12. Schema invariants — E4 (primary_edges ⊆ edges)
# =============================================================================

def test_report_rejects_primary_edge_not_in_edges():
    with pytest.raises(ValueError, match="E4"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "kitchen_99"),),  # not in edges
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 13. Schema invariants — E5 (metric tuples cover nodes lex-ASC)
# =============================================================================

def test_report_rejects_metric_tuple_missing_a_node():
    with pytest.raises(ValueError, match="E5"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0),),  # missing living
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 14. Schema invariants — E6 analog (exactly one room has depth 0)
# =============================================================================

def test_report_rejects_zero_rooms_at_depth_zero():
    """Inv E6 analog — at least one entry-room must have depth 0."""
    with pytest.raises(ValueError, match="E6"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 1), ("living_01", 2)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=1.5,
            max_depth=2,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_rejects_two_rooms_at_depth_zero():
    """Inv E6 analog — exactly one room at depth 0 (uniqueness)."""
    with pytest.raises(ValueError, match="E6"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 0)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.0,
            max_depth=0,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 15. Schema invariants — E11''/E12' (small-graph nan)
# =============================================================================

def test_report_rejects_non_nan_real_ra_at_k_lt_4():
    """Inv E11'': real_RA must be nan for k < 4."""
    with pytest.raises(ValueError, match="E11''"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=0.5,  # NOT nan — bug
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_rejects_nan_real_ra_at_k_ge_4():
    """Inv E11'': real_RA must NOT be nan for k ≥ 4."""
    r = _four_node_normal_report()
    with pytest.raises(ValueError, match="E11''"):
        CirculationGraphReport(
            source_placed_candidate_signature=r.source_placed_candidate_signature,
            nodes=r.nodes,
            edges=r.edges,
            primary_edges=r.primary_edges,
            step_depth_from_entry=r.step_depth_from_entry,
            connectivity=r.connectivity,
            betweenness_rank=r.betweenness_rank,
            mean_depth=r.mean_depth,
            max_depth=r.max_depth,
            raw_relative_asymmetry=r.raw_relative_asymmetry,
            real_relative_asymmetry=float("nan"),  # bug at k=4
            integration=r.integration,
            graph_size_category=r.graph_size_category,
            structural_flags=r.structural_flags,
            preference_flags=r.preference_flags,
            upstream_advisory_flags=r.upstream_advisory_flags,
            c14_advisory_flags=r.c14_advisory_flags,
            category_coverage=r.category_coverage,
            c14_version=r.c14_version,
            c14_metric_version=r.c14_metric_version,
            advisory_schema_version=r.advisory_schema_version,
            cache_keys=r.cache_keys,
        )


# =============================================================================
# 16. Schema invariants — E17 (graph_size_category consistent with k)
# =============================================================================

def test_report_rejects_wrong_category_normal_for_tiny_k():
    """Inv E17: k=2 → 'tiny', not 'normal'."""
    with pytest.raises(ValueError, match="E17"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="normal",  # bug at k=2
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


def test_report_three_node_uses_small_category():
    """Inv E17: k=3 → 'small'."""
    r = CirculationGraphReport(
        source_placed_candidate_signature="cand_003",
        nodes=("entry_01", "kitchen_01", "living_01"),
        edges=(
            ("entry_01", "living_01"),
            ("kitchen_01", "living_01"),
        ),
        primary_edges=(
            ("entry_01", "living_01"),
            ("kitchen_01", "living_01"),
        ),
        step_depth_from_entry=(
            ("entry_01", 0),
            ("kitchen_01", 2),
            ("living_01", 1),
        ),
        connectivity=(
            ("entry_01", 1),
            ("kitchen_01", 1),
            ("living_01", 2),
        ),
        betweenness_rank=(
            ("entry_01", 2),
            ("kitchen_01", 3),
            ("living_01", 1),
        ),
        mean_depth=1.5,
        max_depth=2,
        raw_relative_asymmetry=1.0,
        real_relative_asymmetry=float("nan"),  # k=3 → nan
        integration=float("nan"),
        graph_size_category="small",
        structural_flags=(),
        preference_flags=(),
        upstream_advisory_flags=(),
        c14_advisory_flags=(),
        category_coverage=1.0,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        cache_keys=_minimal_cache_keys(),
    )
    assert r.graph_size_category == "small"


# =============================================================================
# 17. Schema invariants — E18 (category_coverage in [0, 1])
# =============================================================================

def test_report_rejects_category_coverage_out_of_range():
    """Inv E18."""
    with pytest.raises(ValueError, match="E18"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.2,  # out of [0,1]
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 18. Schema invariants — E13' truncation-meta cardinality
# =============================================================================

def test_report_rejects_two_truncation_meta_in_one_tuple():
    """Per A6: at most ONE TRUNCATION_META per tuple."""
    f1 = CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.TRUNCATION_META,
        affected_room_id="",
        severity="info",
        explanation_template="3 flags suppressed.",
        deduplication_key="trunc:1",
    )
    f2 = CirculationFlag(
        flag_kind=StructuralCirculationFlagKind.TRUNCATION_META,
        affected_room_id="",
        severity="info",
        explanation_template="2 flags suppressed.",
        deduplication_key="trunc:2",
    )
    with pytest.raises(ValueError, match="TRUNCATION_META"):
        CirculationGraphReport(
            source_placed_candidate_signature="x",
            nodes=("entry_01", "living_01"),
            edges=(("entry_01", "living_01"),),
            primary_edges=(("entry_01", "living_01"),),
            step_depth_from_entry=(("entry_01", 0), ("living_01", 1)),
            connectivity=(("entry_01", 1), ("living_01", 1)),
            betweenness_rank=(("entry_01", 1), ("living_01", 2)),
            mean_depth=0.5,
            max_depth=1,
            raw_relative_asymmetry=0.0,
            real_relative_asymmetry=float("nan"),
            integration=float("nan"),
            graph_size_category="tiny",
            structural_flags=(f1, f2),
            preference_flags=(),
            upstream_advisory_flags=(),
            c14_advisory_flags=(),
            category_coverage=1.0,
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            cache_keys=_minimal_cache_keys(),
        )


# =============================================================================
# 19. Typestate variants
# =============================================================================

def test_successful_analysis_happy_path():
    r = _two_node_report(sig="cand_007")
    s = SuccessfulCirculationAnalysis(
        source_placed_candidate_signature="cand_007",
        report=r,
    )
    assert s.report is r


def test_successful_analysis_signature_mismatch_rejected():
    r = _two_node_report(sig="cand_007")
    with pytest.raises(ValueError, match="does not match"):
        SuccessfulCirculationAnalysis(
            source_placed_candidate_signature="cand_DIFFERENT",
            report=r,
        )


def test_failed_analysis_happy_path():
    fr = FailureRecord(
        candidate_signature="cand_x",
        error_type="EntryRoomNotFoundError",
        error_message="main_entry not in placed_room_ids",
        phase="alpha",
    )
    fa = FailedCirculationAnalysis(
        source_placed_candidate_signature="cand_x",
        failure_record=fr,
    )
    assert fa.partial_report is None


def test_failed_analysis_signature_mismatch_rejected():
    fr = FailureRecord(
        candidate_signature="cand_x",
        error_type="EntryRoomNotFoundError",
        error_message="m",
        phase="alpha",
    )
    with pytest.raises(ValueError, match="does not match"):
        FailedCirculationAnalysis(
            source_placed_candidate_signature="cand_OTHER",
            failure_record=fr,
        )


def test_failure_record_rejects_bad_phase():
    with pytest.raises(ValueError, match="phase"):
        FailureRecord(
            candidate_signature="x",
            error_type="GraphInconsistencyError",
            error_message="m",
            phase="phase_xyzzy",  # type: ignore[arg-type]
        )


# =============================================================================
# 20. BatchResult
# =============================================================================

def test_batch_result_happy_path():
    r = _two_node_report(sig="cand_a")
    s = SuccessfulCirculationAnalysis(
        source_placed_candidate_signature="cand_a", report=r
    )
    batch = CirculationAnalysisBatchResult(
        successful=(s,),
        failed=(),
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
    )
    assert batch.successful == (s,)
    assert batch.failed == ()


def test_batch_result_rejects_unsorted_successful():
    r1 = _two_node_report(sig="cand_z")
    r2 = _two_node_report(sig="cand_a")
    s1 = SuccessfulCirculationAnalysis(
        source_placed_candidate_signature="cand_z", report=r1
    )
    s2 = SuccessfulCirculationAnalysis(
        source_placed_candidate_signature="cand_a", report=r2
    )
    with pytest.raises(ValueError, match="sorted"):
        CirculationAnalysisBatchResult(
            successful=(s1, s2),  # NOT sorted
            failed=(),
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_rejects_signature_overlap_between_succ_and_failed():
    r = _two_node_report(sig="cand_dup")
    s = SuccessfulCirculationAnalysis(
        source_placed_candidate_signature="cand_dup", report=r
    )
    fr = FailureRecord(
        candidate_signature="cand_dup",
        error_type="GraphInconsistencyError",
        error_message="m",
        phase="alpha",
    )
    f = FailedCirculationAnalysis(
        source_placed_candidate_signature="cand_dup",
        failure_record=fr,
    )
    with pytest.raises(ValueError, match="BOTH"):
        CirculationAnalysisBatchResult(
            successful=(s,),
            failed=(f,),
            c14_version=C14_VERSION,
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_rejects_empty_version():
    with pytest.raises(ValueError, match="c14_version"):
        CirculationAnalysisBatchResult(
            successful=(),
            failed=(),
            c14_version="",
            c14_metric_version=C14_METRIC_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_is_frozen_and_hashable():
    batch = CirculationAnalysisBatchResult(
        successful=(),
        failed=(),
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
    )
    with pytest.raises(FrozenInstanceError):
        batch.c14_version = "v9.9"  # type: ignore[misc]
    assert hash(batch) == hash(batch)
