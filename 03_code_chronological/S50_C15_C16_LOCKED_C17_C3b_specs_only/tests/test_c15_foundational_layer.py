"""
BuildemUp — Component 15 — foundational layer tests
======================================================

Per C15 SPEC v0.2 LOCKED (S46). Sub-1 (S48) target: ≥50 tests covering:

- versioning constants present and well-formed
- errors hierarchy properly structured (Local always halts, PerCandidate
  strict-halts / warn-collects)
- contracts:
  - CulturalProfile enum with ≥3 sub-variants (Inv P17)
  - VALID_CULTURAL_PROFILE_VALUES frozenset re-exported
  - FloorInfo defensive checks
  - ProblemAnalysisMetadata REQUIRED cultural_profile (Inv P17)
- config: ProblemFinderConfig defaults + __post_init__ validation
- cache_keys: derive_c15_cache_keys determinism + sensitivity to inputs
  + config_signature_for sentinel
- schema: every Inv P0..P19 enforced at __post_init__:
  - P0 STRICTER (no module-level aggregator returning numeric quality)
  - P3 (applicable_checks + deferred_checks sorted lex-ASC by check_id)
  - P6 (na_reason populated on DeferredCheck)
  - P7 (affected_room_ids sorted + unique)
  - P9 (dimension_summary counts match actual checks per dimension)
  - P12 (no check_id in both applicable + deferred)
  - P16 (provenance non-empty / non-negative)
  - P17 (cultural_profile REQUIRED on metadata + report)
  - P18 (severity_basis ≥20 chars on SeverityRule)
  - P19 (dimensions_not_evaluated non-empty + sorted-or-stable)
- ProblemCheck rejects NOT_APPLICABLE status (routes to DeferredCheck per A5)
- ProblemCheck.dimension_id must match parsed dimension from check_id
- ProblemCheck.measurement rejects bool values
- UnconventionalPatternHint cross-field consistency
- SeverityRule cultural_profile may be None (applies to all)
- Typestate discipline (Successful vs Failed don't overlap; signatures match)
- BatchResult: tuples sorted, no signature overlap
- Moat-lint surface: c15 public API exposes no float-returning aggregator
  over check tuples

Each test is small + named. Aiming for ≥50 to hit the spec target.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from buildemup.components.c15 import (
    # versioning
    C15_VERSION,
    C15_CHECK_REGISTRY_VERSION,
    EXPECTED_C14_VERSION,
    EXPECTED_C14_METRIC_VERSION,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS,
    DEFAULT_PER_BATCH_WALLCLOCK_SECS,
    MIN_SEVERITY_BASIS_LENGTH,
    TOTAL_DIMENSIONS,
    MIN_DIMENSION_ID,
    MAX_DIMENSION_ID,
    DIMENSIONS_NOT_EVALUATED_V1,
    # errors
    ProblemAnalysisError,
    LocalProblemError,
    PerCandidateProblemError,
    UpstreamSchemaDriftError,
    C15ConfigurationError,
    CheckRegistryError,
    MissingMetadataError,
    InconsistentInputError,
    # contracts
    CulturalProfile,
    VALID_CULTURAL_PROFILE_VALUES,
    FloorInfo,
    ProblemAnalysisMetadata,
    # config
    ProblemFinderConfig,
    # cache_keys
    C15CacheKeys,
    derive_c15_cache_keys,
    config_signature_for,
    # schema
    CheckStatus,
    CheckSeverity,
    CheckEpistemicKind,
    SeverityRule,
    ProblemCheck,
    DeferredCheck,
    UNCONVENTIONAL_PATTERN_NAMES,
    UnconventionalPatternHint,
    DimensionSummary,
    ProblemReport,
    FailureRecord,
    SuccessfulProblemAnalysis,
    FailedProblemAnalysis,
    ProblemAnalysisBatchResult,
)
from buildemup.components.c15.schema import (
    # v0.3 A12 — surfaced via deep import; not yet in c15 __init__ public surface
    CoverageQuality,
    DimensionMaturity,
)


# =============================================================================
# Helpers (minimal valid baselines)
# =============================================================================

def _valid_severity_basis() -> str:
    # Illustrative test stand-in only. Real severity_basis citations
    # come from the locked check registry built in Sub-2 (per
    # B-C15-SEVERITY-RULE-TABLE-LOCK). Sub-1 tests only verify that
    # SeverityRule enforces the ≥20-char floor (Inv P18); they do not
    # verify clause accuracy.
    return "NBC 2016 Part 3 habitable-room minimum-area provisions (illustrative stand-in)"


def _make_check(
    check_id: str = "P1.1",
    dimension_id: int = 1,
    status: CheckStatus = CheckStatus.PASS,
    severity: CheckSeverity = CheckSeverity.IMPORTANT,
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.REGULATORY,
    affected_room_ids: tuple[str, ...] = ("r1",),
    rule_citation: str = "NBC 2016 §6.2.1",
    why_it_matters: str = "Habitable rooms below 9.5 m² fail NBC and are not legally certifiable.",
    suggested_mitigation: str | None = "Increase room area to ≥9.5 m².",
    measurement: dict | None = None,
) -> ProblemCheck:
    return ProblemCheck(
        check_id=check_id,
        dimension_id=dimension_id,
        status=status,
        severity=severity,
        epistemic_kind=epistemic_kind,
        affected_room_ids=affected_room_ids,
        rule_citation=rule_citation,
        why_it_matters=why_it_matters,
        suggested_mitigation=suggested_mitigation,
        measurement=measurement,
    )


def _make_deferred(
    check_id: str = "P9.1",
    dimension_id: int = 9,
    na_reason: str = "Storage-volume measurement not yet implemented for v1.",
    blocking_backlog_item: str = "B-C15-STORAGE-DIMENSION",
) -> DeferredCheck:
    return DeferredCheck(
        check_id=check_id,
        dimension_id=dimension_id,
        na_reason=na_reason,
        blocking_backlog_item=blocking_backlog_item,
    )


def _make_dim_summary(
    dimension_id: int,
    dimension_name: str,
    n_applicable: int,
    n_deferred: int,
    n_pass: int,
    n_warn: int,
    n_fail: int,
) -> DimensionSummary:
    # v0.3 A12: derive maturity from counts so all test fixtures stay
    # honest by construction.
    from buildemup.components.c15.schema import _derive_dim_maturity
    return DimensionSummary(
        dimension_id=dimension_id,
        dimension_name=dimension_name,
        n_applicable=n_applicable,
        n_deferred=n_deferred,
        n_pass=n_pass,
        n_warn=n_warn,
        n_fail=n_fail,
        maturity=_derive_dim_maturity(n_applicable, n_deferred),
    )


def _empty_hint() -> UnconventionalPatternHint:
    return UnconventionalPatternHint(
        detected=False,
        suspected_patterns=(),
        confidence_caveat="",
        affected_check_ids=(),
    )


def _full_dimension_summary_for(checks: tuple[ProblemCheck, ...], deferred: tuple[DeferredCheck, ...]) -> tuple[DimensionSummary, ...]:
    """Build a complete tuple of DimensionSummary entries covering all 10 dimensions, consistent with the given checks/deferred.

    Required by Inv P9 — summary entries must cover every dimension
    1..10 and counts must match.
    """
    summaries: list[DimensionSummary] = []
    names = {
        1: "no_wasted_space",
        2: "room_sizes_match_function",
        3: "logical_flow",
        4: "natural_light",
        5: "privacy",
        6: "no_bottlenecks",
        7: "first_floor_living",
        8: "outdoor_connection",
        9: "storage",
        10: "multi_functional",
    }
    for dim in range(1, 11):
        dim_checks = tuple(c for c in checks if c.dimension_id == dim)
        dim_deferred = tuple(d for d in deferred if d.dimension_id == dim)
        n_pass = sum(1 for c in dim_checks if c.status == CheckStatus.PASS)
        n_warn = sum(1 for c in dim_checks if c.status == CheckStatus.WARN)
        n_fail = sum(1 for c in dim_checks if c.status == CheckStatus.FAIL)
        summaries.append(_make_dim_summary(
            dimension_id=dim,
            dimension_name=names[dim],
            n_applicable=len(dim_checks),
            n_deferred=len(dim_deferred),
            n_pass=n_pass,
            n_warn=n_warn,
            n_fail=n_fail,
        ))
    return tuple(summaries)


def _make_report(
    *,
    candidate_sig: str = "cand-001",
    checks: tuple[ProblemCheck, ...] = (),
    deferred: tuple[DeferredCheck, ...] = (),
    hint: UnconventionalPatternHint | None = None,
    cultural_profile: CulturalProfile = CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
) -> ProblemReport:
    if hint is None:
        hint = _empty_hint()
    summary = _full_dimension_summary_for(checks, deferred)
    # v0.3 A12: derive coverage_quality from dimension_summary.
    from buildemup.components.c15.schema import _derive_coverage_quality
    coverage_quality, ratio_applicable = _derive_coverage_quality(summary)
    return ProblemReport(
        source_placed_candidate_signature=candidate_sig,
        applicable_checks=checks,
        deferred_checks=deferred,
        dimension_summary=summary,
        dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
        unconventional_pattern_hint=hint,
        cultural_profile_active=cultural_profile,
        c13_advisory_flags=(),
        c14_structural_flags=(),
        c14_preference_flags=(),
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        upstream_cache_key="c14-key-abc",
        coverage_quality=coverage_quality,
        ratio_applicable=ratio_applicable,
    )


# =============================================================================
# Versioning
# =============================================================================

def test_versioning_c15_version_is_v0_2():
    assert C15_VERSION == "v0.2"


def test_versioning_check_registry_version_is_1():
    assert C15_CHECK_REGISTRY_VERSION == 1


def test_versioning_expected_upstream_c14_v0_2():
    assert EXPECTED_C14_VERSION == "v0.2"


def test_versioning_expected_c14_metric_version_is_2():
    assert EXPECTED_C14_METRIC_VERSION == 2


def test_versioning_expected_advisory_schema_version_is_1():
    assert EXPECTED_ADVISORY_SCHEMA_VERSION == 1


def test_versioning_default_per_candidate_wallclock():
    assert DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS == 1.5


def test_versioning_default_per_batch_wallclock():
    assert DEFAULT_PER_BATCH_WALLCLOCK_SECS == 15.0


def test_versioning_min_severity_basis_length_is_20():
    # Inv P18 floor — A4.
    assert MIN_SEVERITY_BASIS_LENGTH == 20


def test_versioning_total_dimensions_and_bounds():
    assert TOTAL_DIMENSIONS == 10
    assert MIN_DIMENSION_ID == 1
    assert MAX_DIMENSION_ID == 10


def test_versioning_dimensions_not_evaluated_v1_non_empty():
    # Inv P19 baseline.
    assert len(DIMENSIONS_NOT_EVALUATED_V1) > 0


def test_versioning_dimensions_not_evaluated_v1_all_non_empty_strings():
    assert all(isinstance(d, str) and len(d) > 0 for d in DIMENSIONS_NOT_EVALUATED_V1)


def test_versioning_dimensions_not_evaluated_v1_no_duplicates():
    assert len(set(DIMENSIONS_NOT_EVALUATED_V1)) == len(DIMENSIONS_NOT_EVALUATED_V1)


# =============================================================================
# Errors hierarchy
# =============================================================================

def test_errors_base_class_is_exception():
    assert issubclass(ProblemAnalysisError, Exception)


def test_errors_local_and_per_candidate_tiers():
    # Two tiers required by spec § 0.6 (analog of C14 spec).
    assert issubclass(LocalProblemError, ProblemAnalysisError)
    assert issubclass(PerCandidateProblemError, ProblemAnalysisError)
    # The tiers are distinct.
    assert not issubclass(LocalProblemError, PerCandidateProblemError)
    assert not issubclass(PerCandidateProblemError, LocalProblemError)


def test_errors_local_subtypes_inherit_correctly():
    for cls in (UpstreamSchemaDriftError, C15ConfigurationError, CheckRegistryError):
        assert issubclass(cls, LocalProblemError)


def test_errors_per_candidate_subtypes_inherit_correctly():
    for cls in (MissingMetadataError, InconsistentInputError):
        assert issubclass(cls, PerCandidateProblemError)


def test_errors_can_be_raised_and_caught():
    with pytest.raises(LocalProblemError):
        raise UpstreamSchemaDriftError("test")
    with pytest.raises(PerCandidateProblemError):
        raise MissingMetadataError("test")


# =============================================================================
# Contracts — CulturalProfile
# =============================================================================

def test_cultural_profile_has_minimum_three_sub_variants():
    # Inv P17 — A3 LOCK-mandatory: ≥3 sub-variants at v1.0 LOCK.
    # v0.2 ships 6 to leave headroom; LOCK requires ≥3.
    assert len(list(CulturalProfile)) >= 3


def test_cultural_profile_ships_six_at_v0_2():
    assert len(list(CulturalProfile)) == 6


def test_cultural_profile_values_are_canonical():
    values = {m.value for m in CulturalProfile}
    assert "in_mc_tamil_multigen" in values
    assert "in_mc_kerala_courtyard" in values
    assert "in_mc_compact_urban" in values
    assert "in_mc_generic" in values
    assert "in_li_incremental" in values
    assert "in_nri_returnee" in values


def test_cultural_profile_string_enum_indexable():
    # StrEnum: values can be compared and serialized as strings.
    assert CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC.value == "in_mc_generic"
    assert isinstance(CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC.value, str)


def test_valid_cultural_profile_values_matches_enum():
    enum_values = {m.value for m in CulturalProfile}
    assert VALID_CULTURAL_PROFILE_VALUES == frozenset(enum_values)


# =============================================================================
# Contracts — FloorInfo
# =============================================================================

def test_floor_info_happy_path():
    f = FloorInfo(floor_id="GF", is_ground=True, has_entry=True, room_ids=("r1", "r2"))
    assert f.floor_id == "GF"
    assert f.is_ground is True


def test_floor_info_is_frozen():
    f = FloorInfo(floor_id="GF", is_ground=True, has_entry=True, room_ids=("r1",))
    with pytest.raises(FrozenInstanceError):
        f.floor_id = "FF"  # type: ignore[misc]


def test_floor_info_rejects_empty_floor_id():
    with pytest.raises((ValueError, TypeError)):
        FloorInfo(floor_id="", is_ground=True, has_entry=True, room_ids=("r1",))


def test_floor_info_rejects_non_tuple_rooms():
    with pytest.raises(TypeError):
        FloorInfo(floor_id="GF", is_ground=True, has_entry=True, room_ids=["r1"])  # type: ignore[arg-type]


# =============================================================================
# Contracts — ProblemAnalysisMetadata
# =============================================================================

def test_metadata_happy_path():
    m = ProblemAnalysisMetadata(
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        placed_room_ids=("r1", "r2"),
        room_categories={"r1": "bedroom", "r2": "kitchen"},
        main_entry_room_id="r1",
    )
    assert m.cultural_profile == CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC


def test_metadata_is_frozen():
    m = ProblemAnalysisMetadata(
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        placed_room_ids=("r1",),
        room_categories={"r1": "bedroom"},
        main_entry_room_id="r1",
    )
    with pytest.raises(FrozenInstanceError):
        m.main_entry_room_id = "r2"  # type: ignore[misc]


def test_metadata_rejects_none_cultural_profile():
    # Inv P17 — A3 LOCKED: cultural_profile REQUIRED, no default.
    with pytest.raises((TypeError, ValueError)):
        ProblemAnalysisMetadata(
            cultural_profile=None,  # type: ignore[arg-type]
            placed_room_ids=("r1",),
            room_categories={"r1": "bedroom"},
            main_entry_room_id="r1",
        )


def test_metadata_rejects_str_for_cultural_profile():
    # Must be the enum, not a raw string. Forces caller awareness.
    with pytest.raises((TypeError, ValueError)):
        ProblemAnalysisMetadata(
            cultural_profile="in_mc_generic",  # type: ignore[arg-type]
            placed_room_ids=("r1",),
            room_categories={"r1": "bedroom"},
            main_entry_room_id="r1",
        )


def test_metadata_rejects_main_entry_not_in_rooms():
    with pytest.raises(ValueError):
        ProblemAnalysisMetadata(
            cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            placed_room_ids=("r1", "r2"),
            room_categories={"r1": "bedroom", "r2": "kitchen"},
            main_entry_room_id="r99",
        )


def test_metadata_rejects_room_categories_missing_keys():
    with pytest.raises(ValueError):
        ProblemAnalysisMetadata(
            cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            placed_room_ids=("r1", "r2"),
            room_categories={"r1": "bedroom"},  # r2 missing
            main_entry_room_id="r1",
        )


# =============================================================================
# Config
# =============================================================================

def test_config_defaults_match_spec():
    c = ProblemFinderConfig()
    assert c.per_candidate_wallclock_seconds == DEFAULT_PER_CANDIDATE_WALLCLOCK_SECS
    assert c.per_batch_wallclock_seconds == DEFAULT_PER_BATCH_WALLCLOCK_SECS
    assert c.strict_mode is True  # default-on per spec
    assert c.cache_mode == "strict"


def test_config_is_frozen():
    c = ProblemFinderConfig()
    with pytest.raises(FrozenInstanceError):
        c.strict_mode = False  # type: ignore[misc]


def test_config_rejects_negative_wallclock():
    with pytest.raises((ValueError, TypeError, C15ConfigurationError)):
        ProblemFinderConfig(per_candidate_wallclock_seconds=-1.0)


def test_config_rejects_zero_wallclock():
    with pytest.raises((ValueError, TypeError, C15ConfigurationError)):
        ProblemFinderConfig(per_candidate_wallclock_seconds=0.0)


def test_config_rejects_invalid_cache_mode():
    with pytest.raises((ValueError, TypeError, C15ConfigurationError)):
        ProblemFinderConfig(cache_mode="bogus")  # type: ignore[arg-type]


def test_config_rejects_non_bool_strict_mode():
    with pytest.raises((TypeError, ValueError, C15ConfigurationError)):
        ProblemFinderConfig(strict_mode="yes")  # type: ignore[arg-type]


def test_config_accepts_lenient_cache_mode():
    c = ProblemFinderConfig(cache_mode="lenient")
    assert c.cache_mode == "lenient"


# =============================================================================
# Cache keys
# =============================================================================

def test_cache_keys_deterministic_across_calls():
    k1 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-hash-001",
    )
    k2 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-hash-001",
    )
    assert k1.full_cache_key == k2.full_cache_key


def test_cache_keys_differ_when_c14_key_changes():
    k1 = derive_c15_cache_keys(
        c14_full_cache_key="c14-A",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-hash-001",
    )
    k2 = derive_c15_cache_keys(
        c14_full_cache_key="c14-B",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-hash-001",
    )
    assert k1.full_cache_key != k2.full_cache_key


def test_cache_keys_differ_when_cultural_profile_changes():
    k1 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-hash-001",
    )
    k2 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_tamil_multigen",
        severity_rule_table_hash="srt-hash-001",
    )
    assert k1.full_cache_key != k2.full_cache_key


def test_cache_keys_differ_when_severity_rule_table_changes():
    k1 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-001",
    )
    k2 = derive_c15_cache_keys(
        c14_full_cache_key="c14-abc",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-002",
    )
    assert k1.full_cache_key != k2.full_cache_key


def test_cache_keys_reject_empty_c14_key():
    with pytest.raises((ValueError, TypeError)):
        derive_c15_cache_keys(
            c14_full_cache_key="",
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            cultural_profile_id="in_mc_generic",
            severity_rule_table_hash="srt-001",
        )


def test_cache_keys_c14_key_passes_through_unchanged():
    keys = derive_c15_cache_keys(
        c14_full_cache_key="c14-XYZ",
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        cultural_profile_id="in_mc_generic",
        severity_rule_table_hash="srt-001",
    )
    assert keys.c14_full_cache_key == "c14-XYZ"


def test_c15_cache_keys_dataclass_rejects_empty_fields():
    with pytest.raises((ValueError, TypeError)):
        C15CacheKeys(c14_full_cache_key="", check_registry_cache_key="x", full_cache_key="y")


def test_config_signature_for_is_deterministic():
    s1 = config_signature_for()
    s2 = config_signature_for()
    assert s1 == s2
    assert isinstance(s1, str)
    assert len(s1) > 0


# =============================================================================
# Schema enums
# =============================================================================

def test_check_status_enum_values():
    values = {m.value for m in CheckStatus}
    assert values == {"pass", "warn", "fail", "not_applicable"}


def test_check_severity_enum_values():
    values = {m.value for m in CheckSeverity}
    assert values == {"critical", "important", "nice_to_have"}


def test_check_epistemic_kind_enum_values_per_a2():
    # A2 LOCKED.
    values = {m.value for m in CheckEpistemicKind}
    assert values == {"regulatory", "architectural_heuristic", "cultural_preference"}


# =============================================================================
# SeverityRule (Inv P18)
# =============================================================================

def test_severity_rule_happy_path():
    rule = SeverityRule(
        check_id="P2.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.CRITICAL,
        severity_basis=_valid_severity_basis(),
    )
    assert rule.severity == CheckSeverity.CRITICAL


def test_severity_rule_is_frozen():
    rule = SeverityRule(
        check_id="P2.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.CRITICAL,
        severity_basis=_valid_severity_basis(),
    )
    with pytest.raises(FrozenInstanceError):
        rule.severity = CheckSeverity.IMPORTANT  # type: ignore[misc]


def test_severity_rule_rejects_short_basis_per_inv_p18():
    # Inv P18 — A4: severity_basis ≥ MIN_SEVERITY_BASIS_LENGTH chars.
    with pytest.raises(CheckRegistryError):
        SeverityRule(
            check_id="P2.1",
            status=CheckStatus.FAIL,
            cultural_profile=None,
            severity=CheckSeverity.CRITICAL,
            severity_basis="short",
        )


def test_severity_rule_rejects_basis_exactly_one_short():
    short = "x" * (MIN_SEVERITY_BASIS_LENGTH - 1)
    with pytest.raises(CheckRegistryError):
        SeverityRule(
            check_id="P2.1",
            status=CheckStatus.FAIL,
            cultural_profile=None,
            severity=CheckSeverity.CRITICAL,
            severity_basis=short,
        )


def test_severity_rule_accepts_basis_at_minimum_length():
    ok = "x" * MIN_SEVERITY_BASIS_LENGTH
    rule = SeverityRule(
        check_id="P2.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.CRITICAL,
        severity_basis=ok,
    )
    assert rule.severity_basis == ok


def test_severity_rule_cultural_profile_may_be_none():
    # cultural_profile=None means "applies regardless of cultural profile."
    rule = SeverityRule(
        check_id="P2.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.CRITICAL,
        severity_basis=_valid_severity_basis(),
    )
    assert rule.cultural_profile is None


def test_severity_rule_cultural_profile_may_be_specific():
    rule = SeverityRule(
        check_id="P5.3",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.IMPORTANT,
        severity_basis=_valid_severity_basis(),
    )
    assert rule.cultural_profile == CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN


def test_severity_rule_rejects_not_applicable_status():
    # NOT_APPLICABLE goes to DeferredCheck, not severity-graded.
    with pytest.raises(CheckRegistryError):
        SeverityRule(
            check_id="P2.1",
            status=CheckStatus.NOT_APPLICABLE,
            cultural_profile=None,
            severity=CheckSeverity.CRITICAL,
            severity_basis=_valid_severity_basis(),
        )


# =============================================================================
# ProblemCheck
# =============================================================================

def test_problem_check_happy_path():
    c = _make_check()
    assert c.check_id == "P1.1"
    assert c.dimension_id == 1


def test_problem_check_is_frozen():
    c = _make_check()
    with pytest.raises(FrozenInstanceError):
        c.status = CheckStatus.FAIL  # type: ignore[misc]


def test_problem_check_id_pattern_valid():
    # P{1..10}.{1..n}
    for cid, dim in [("P1.1", 1), ("P10.5", 10), ("P3.25", 3)]:
        c = _make_check(check_id=cid, dimension_id=dim)
        assert c.check_id == cid


def test_problem_check_id_pattern_rejects_bad_form():
    for bad in ["1.1", "P0.1", "P11.1", "P1.0", "p1.1", "P1.", ".1", "P1", "P1.a"]:
        with pytest.raises((ValueError, CheckRegistryError)):
            _make_check(check_id=bad)


def test_problem_check_dimension_id_must_match_parsed_check_id():
    # check_id "P1.1" implies dimension_id=1; passing dimension_id=2 is rejected.
    with pytest.raises((ValueError, CheckRegistryError)):
        _make_check(check_id="P1.1", dimension_id=2)


def test_problem_check_rejects_not_applicable_status_per_a5():
    # A5: NOT_APPLICABLE checks route to DeferredCheck, not ProblemCheck.
    with pytest.raises((ValueError, CheckRegistryError)):
        _make_check(status=CheckStatus.NOT_APPLICABLE)


def test_problem_check_affected_rooms_sorted_per_inv_p7():
    # Inv P7: affected_room_ids sorted lex-ASC, unique.
    with pytest.raises(ValueError):
        _make_check(affected_room_ids=("r2", "r1"))


def test_problem_check_affected_rooms_unique_per_inv_p7():
    with pytest.raises(ValueError):
        _make_check(affected_room_ids=("r1", "r1"))


def test_problem_check_rejects_empty_rule_citation():
    with pytest.raises(ValueError):
        _make_check(rule_citation="")


def test_problem_check_rejects_empty_why_it_matters():
    with pytest.raises(ValueError):
        _make_check(why_it_matters="")


def test_problem_check_measurement_accepts_numeric_dict():
    c = _make_check(measurement={"actual_sqft": 85.5, "min_sqft": 102})
    assert c.measurement is not None
    assert c.measurement["actual_sqft"] == 85.5


def test_problem_check_measurement_rejects_bool_values():
    # bool is a subclass of int but semantically a flag; rejecting it
    # forces callers to use explicit numeric measurements.
    with pytest.raises((TypeError, ValueError)):
        _make_check(measurement={"some_flag": True})


def test_problem_check_measurement_may_be_none():
    c = _make_check(measurement=None)
    assert c.measurement is None


def test_problem_check_epistemic_kind_three_variants():
    for kind in (CheckEpistemicKind.REGULATORY, CheckEpistemicKind.ARCHITECTURAL_HEURISTIC, CheckEpistemicKind.CULTURAL_PREFERENCE):
        c = _make_check(epistemic_kind=kind)
        assert c.epistemic_kind == kind


# =============================================================================
# DeferredCheck (per A5)
# =============================================================================

def test_deferred_check_happy_path():
    d = _make_deferred()
    assert d.na_reason.startswith("Storage-volume")


def test_deferred_check_is_frozen():
    d = _make_deferred()
    with pytest.raises(FrozenInstanceError):
        d.na_reason = "different"  # type: ignore[misc]


def test_deferred_check_rejects_empty_na_reason_per_inv_p6():
    # Inv P6: na_reason populated on every deferred check.
    with pytest.raises(ValueError):
        _make_deferred(na_reason="")


def test_deferred_check_id_pattern_enforced():
    with pytest.raises((ValueError, CheckRegistryError)):
        _make_deferred(check_id="bogus")


def test_deferred_check_dimension_must_match_check_id():
    with pytest.raises((ValueError, CheckRegistryError)):
        _make_deferred(check_id="P9.1", dimension_id=2)


# =============================================================================
# UnconventionalPatternHint (per A7)
# =============================================================================

def test_unconventional_pattern_names_count_is_five():
    # A7: v1 ships 5 recognized patterns.
    assert len(UNCONVENTIONAL_PATTERN_NAMES) == 5


def test_unconventional_pattern_names_membership():
    expected = {
        "courtyard_centered",
        "split_level_circulation",
        "ritual_procession",
        "compact_incremental",
        "multigenerational_segregation",
    }
    assert set(UNCONVENTIONAL_PATTERN_NAMES) == expected


def test_unconventional_pattern_hint_empty_form_valid():
    h = _empty_hint()
    assert h.detected is False
    assert h.suspected_patterns == ()


def test_unconventional_pattern_hint_detected_requires_patterns():
    # Cross-field consistency: detected=True requires non-empty patterns.
    with pytest.raises(ValueError):
        UnconventionalPatternHint(
            detected=True,
            suspected_patterns=(),
            confidence_caveat="caveat",
            affected_check_ids=("P5.1",),
        )


def test_unconventional_pattern_hint_patterns_require_detected():
    # Reverse: patterns supplied but detected=False is inconsistent.
    with pytest.raises(ValueError):
        UnconventionalPatternHint(
            detected=False,
            suspected_patterns=("courtyard_centered",),
            confidence_caveat="caveat",
            affected_check_ids=(),
        )


def test_unconventional_pattern_hint_rejects_unknown_pattern():
    with pytest.raises(ValueError):
        UnconventionalPatternHint(
            detected=True,
            suspected_patterns=("bogus_pattern",),
            confidence_caveat="caveat present",
            affected_check_ids=("P5.1",),
        )


def test_unconventional_pattern_hint_detected_requires_caveat():
    with pytest.raises(ValueError):
        UnconventionalPatternHint(
            detected=True,
            suspected_patterns=("courtyard_centered",),
            confidence_caveat="",
            affected_check_ids=("P5.1",),
        )


# =============================================================================
# DimensionSummary (per A10)
# =============================================================================

def test_dimension_summary_happy_path():
    ds = _make_dim_summary(1, "no_wasted_space", 5, 0, 3, 1, 1)
    assert ds.dimension_id == 1


def test_dimension_summary_arithmetic_per_a10():
    # A10 LOCKED: n_pass + n_warn + n_fail == n_applicable.
    # Critical structural invariant of DimensionSummary.
    with pytest.raises(ValueError):
        _make_dim_summary(1, "x", n_applicable=5, n_deferred=0, n_pass=2, n_warn=1, n_fail=1)


def test_dimension_summary_rejects_negative_counts():
    with pytest.raises(ValueError):
        _make_dim_summary(1, "x", n_applicable=-1, n_deferred=0, n_pass=0, n_warn=0, n_fail=0)


def test_dimension_summary_rejects_dimension_out_of_range():
    with pytest.raises(ValueError):
        _make_dim_summary(0, "x", 0, 0, 0, 0, 0)
    with pytest.raises(ValueError):
        _make_dim_summary(11, "x", 0, 0, 0, 0, 0)


def test_dimension_summary_rejects_empty_name():
    with pytest.raises(ValueError):
        _make_dim_summary(1, "", 0, 0, 0, 0, 0)


# =============================================================================
# ProblemReport — assembly + invariants
# =============================================================================

def test_report_happy_path_empty_checks():
    r = _make_report()
    assert r.source_placed_candidate_signature == "cand-001"
    assert r.applicable_checks == ()
    assert r.cultural_profile_active == CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC


def test_report_is_frozen():
    r = _make_report()
    with pytest.raises(FrozenInstanceError):
        r.upstream_cache_key = "different"  # type: ignore[misc]


def test_report_applicable_checks_sorted_lex_asc_per_inv_p3():
    # Inv P3.
    c_p2 = _make_check(check_id="P2.1", dimension_id=2)
    c_p1 = _make_check(check_id="P1.1", dimension_id=1)
    with pytest.raises(ValueError):
        _make_report(checks=(c_p2, c_p1))


def test_report_deferred_checks_sorted_lex_asc_per_inv_p3():
    d_p9 = _make_deferred(check_id="P9.1", dimension_id=9)
    d_p4 = _make_deferred(check_id="P4.1", dimension_id=4)
    with pytest.raises(ValueError):
        _make_report(deferred=(d_p9, d_p4))


def test_report_inv_p12_no_overlap_applicable_and_deferred():
    # Inv P12: a check_id cannot appear in both applicable and deferred.
    c = _make_check(check_id="P1.1", dimension_id=1)
    d = _make_deferred(check_id="P1.1", dimension_id=1)
    with pytest.raises(ValueError):
        _make_report(checks=(c,), deferred=(d,))


def test_report_inv_p9_dimension_summary_counts_match():
    # Inv P9 — A10: dimension_summary counts must match actual checks
    # per dimension. _make_report's helper computes them, so directly
    # mutating to an inconsistent summary should fail at the constructor.
    c = _make_check(check_id="P1.1", dimension_id=1, status=CheckStatus.PASS)
    bad_summary = list(_full_dimension_summary_for((c,), ()))
    # Force a mismatch on dimension 1.
    bad_summary[0] = _make_dim_summary(1, "no_wasted_space", 99, 0, 99, 0, 0)
    with pytest.raises(ValueError):
        ProblemReport(
            source_placed_candidate_signature="cand-001",
            applicable_checks=(c,),
            deferred_checks=(),
            dimension_summary=tuple(bad_summary),
            dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
            unconventional_pattern_hint=_empty_hint(),
            cultural_profile_active=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            c13_advisory_flags=(),
            c14_structural_flags=(),
            c14_preference_flags=(),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            upstream_cache_key="c14-key-abc",
            coverage_quality=CoverageQuality.LOW,
            ratio_applicable=0.0,
        )


def test_report_inv_p19_dimensions_not_evaluated_must_be_non_empty():
    # Inv P19 — A6.
    with pytest.raises(ValueError):
        ProblemReport(
            source_placed_candidate_signature="cand-001",
            applicable_checks=(),
            deferred_checks=(),
            dimension_summary=_full_dimension_summary_for((), ()),
            dimensions_not_evaluated=(),
            unconventional_pattern_hint=_empty_hint(),
            cultural_profile_active=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            c13_advisory_flags=(),
            c14_structural_flags=(),
            c14_preference_flags=(),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            upstream_cache_key="c14-key-abc",
            coverage_quality=CoverageQuality.LOW,
            ratio_applicable=0.0,
        )


def test_report_inv_p17_cultural_profile_active_required_via_type():
    # Inv P17 — A3 LOCKED. None is not a CulturalProfile; constructor rejects.
    with pytest.raises((TypeError, ValueError)):
        ProblemReport(
            source_placed_candidate_signature="cand-001",
            applicable_checks=(),
            deferred_checks=(),
            dimension_summary=_full_dimension_summary_for((), ()),
            dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
            unconventional_pattern_hint=_empty_hint(),
            cultural_profile_active=None,  # type: ignore[arg-type]
            c13_advisory_flags=(),
            c14_structural_flags=(),
            c14_preference_flags=(),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            upstream_cache_key="c14-key-abc",
            coverage_quality=CoverageQuality.LOW,
            ratio_applicable=0.0,
        )


def test_report_inv_p16_provenance_non_empty():
    # Inv P16: c15_version, check_registry_version, advisory_schema_version,
    # upstream_cache_key all provenance fields must be non-empty / valid.
    with pytest.raises((ValueError, TypeError)):
        ProblemReport(
            source_placed_candidate_signature="cand-001",
            applicable_checks=(),
            deferred_checks=(),
            dimension_summary=_full_dimension_summary_for((), ()),
            dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
            unconventional_pattern_hint=_empty_hint(),
            cultural_profile_active=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            c13_advisory_flags=(),
            c14_structural_flags=(),
            c14_preference_flags=(),
            c15_version="",
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            upstream_cache_key="c14-key-abc",
            coverage_quality=CoverageQuality.LOW,
            ratio_applicable=0.0,
        )


def test_report_inv_p16_check_registry_version_must_be_positive():
    with pytest.raises((ValueError, TypeError)):
        ProblemReport(
            source_placed_candidate_signature="cand-001",
            applicable_checks=(),
            deferred_checks=(),
            dimension_summary=_full_dimension_summary_for((), ()),
            dimensions_not_evaluated=DIMENSIONS_NOT_EVALUATED_V1,
            unconventional_pattern_hint=_empty_hint(),
            cultural_profile_active=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
            c13_advisory_flags=(),
            c14_structural_flags=(),
            c14_preference_flags=(),
            c15_version=C15_VERSION,
            c15_check_registry_version=-1,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
            upstream_cache_key="c14-key-abc",
            coverage_quality=CoverageQuality.LOW,
            ratio_applicable=0.0,
        )


def test_report_dimension_summary_consistent_with_checks():
    # Spec does NOT mandate that dimension_summary enumerate ALL 10
    # dimensions; only that counts per included dimension be
    # consistent with checks (Inv P9 + A10 split). Verify the helper
    # produces a consistent summary that matches Inv P9.
    c1 = _make_check(check_id="P1.1", dimension_id=1, status=CheckStatus.PASS)
    r = _make_report(checks=(c1,))
    dim1 = next(d for d in r.dimension_summary if d.dimension_id == 1)
    assert dim1.n_pass == 1
    assert dim1.n_warn == 0
    assert dim1.n_fail == 0
    assert dim1.n_applicable == 1
    # Inv P9 cross-check: pass+warn+fail == applicable.
    assert dim1.n_pass + dim1.n_warn + dim1.n_fail == dim1.n_applicable


def test_report_with_pass_warn_fail_checks_assembles():
    c1 = _make_check(check_id="P1.1", dimension_id=1, status=CheckStatus.PASS)
    c2 = _make_check(check_id="P1.2", dimension_id=1, status=CheckStatus.WARN)
    c3 = _make_check(check_id="P1.3", dimension_id=1, status=CheckStatus.FAIL)
    r = _make_report(checks=(c1, c2, c3))
    assert len(r.applicable_checks) == 3
    dim1 = next(d for d in r.dimension_summary if d.dimension_id == 1)
    assert dim1.n_pass == 1
    assert dim1.n_warn == 1
    assert dim1.n_fail == 1
    assert dim1.n_applicable == 3


# =============================================================================
# FailureRecord + Typestate
# =============================================================================

def test_failure_record_happy_path():
    f = FailureRecord(
        candidate_signature="cand-001",
        error_type="MissingMetadataError",
        error_message="cultural_profile is required",
        phase="pi",
    )
    assert f.phase == "pi"


def test_failure_record_is_frozen():
    f = FailureRecord(
        candidate_signature="cand-001",
        error_type="MissingMetadataError",
        error_message="cultural_profile is required",
        phase="pi",
    )
    with pytest.raises(FrozenInstanceError):
        f.phase = "rho"  # type: ignore[misc]


def test_failure_record_rejects_invalid_phase():
    with pytest.raises((ValueError, TypeError)):
        FailureRecord(
            candidate_signature="cand-001",
            error_type="MissingMetadataError",
            error_message="cultural_profile is required",
            phase="omega",  # type: ignore[arg-type]
        )


def test_failure_record_rejects_empty_candidate_signature():
    with pytest.raises(ValueError):
        FailureRecord(
            candidate_signature="",
            error_type="MissingMetadataError",
            error_message="x",
            phase="pi",
        )


def test_successful_problem_analysis_signature_consistency():
    r = _make_report(candidate_sig="cand-001")
    succ = SuccessfulProblemAnalysis(
        source_placed_candidate_signature="cand-001",
        report=r,
    )
    assert succ.report is r


def test_successful_problem_analysis_rejects_signature_mismatch():
    r = _make_report(candidate_sig="cand-001")
    with pytest.raises(ValueError):
        SuccessfulProblemAnalysis(
            source_placed_candidate_signature="cand-DIFFERENT",
            report=r,
        )


def test_failed_problem_analysis_happy_path():
    fr = FailureRecord(
        candidate_signature="cand-001",
        error_type="MissingMetadataError",
        error_message="x",
        phase="pi",
    )
    fail = FailedProblemAnalysis(
        source_placed_candidate_signature="cand-001",
        failure_record=fr,
    )
    assert fail.partial_report is None


def test_failed_problem_analysis_signature_consistency():
    fr = FailureRecord(
        candidate_signature="cand-001",
        error_type="MissingMetadataError",
        error_message="x",
        phase="pi",
    )
    with pytest.raises(ValueError):
        FailedProblemAnalysis(
            source_placed_candidate_signature="cand-DIFFERENT",
            failure_record=fr,
        )


# =============================================================================
# ProblemAnalysisBatchResult
# =============================================================================

def test_batch_result_empty_valid():
    b = ProblemAnalysisBatchResult(
        successful=(),
        failed=(),
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
    )
    assert b.successful == ()
    assert b.failed == ()


def test_batch_result_is_frozen():
    b = ProblemAnalysisBatchResult(
        successful=(),
        failed=(),
        c15_version=C15_VERSION,
        c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
        advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
    )
    with pytest.raises(FrozenInstanceError):
        b.c15_version = "v0.3"  # type: ignore[misc]


def test_batch_result_successful_sorted_lex_asc():
    r_b = _make_report(candidate_sig="cand-B")
    r_a = _make_report(candidate_sig="cand-A")
    succ_b = SuccessfulProblemAnalysis(source_placed_candidate_signature="cand-B", report=r_b)
    succ_a = SuccessfulProblemAnalysis(source_placed_candidate_signature="cand-A", report=r_a)
    with pytest.raises(ValueError):
        ProblemAnalysisBatchResult(
            successful=(succ_b, succ_a),
            failed=(),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_failed_sorted_lex_asc():
    fr_b = FailureRecord(candidate_signature="cand-B", error_type="X", error_message="x", phase="pi")
    fr_a = FailureRecord(candidate_signature="cand-A", error_type="X", error_message="x", phase="pi")
    failed_b = FailedProblemAnalysis(source_placed_candidate_signature="cand-B", failure_record=fr_b)
    failed_a = FailedProblemAnalysis(source_placed_candidate_signature="cand-A", failure_record=fr_a)
    with pytest.raises(ValueError):
        ProblemAnalysisBatchResult(
            successful=(),
            failed=(failed_b, failed_a),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_no_signature_overlap_between_succ_and_failed():
    r = _make_report(candidate_sig="cand-001")
    succ = SuccessfulProblemAnalysis(source_placed_candidate_signature="cand-001", report=r)
    fr = FailureRecord(candidate_signature="cand-001", error_type="X", error_message="x", phase="pi")
    fail = FailedProblemAnalysis(source_placed_candidate_signature="cand-001", failure_record=fr)
    with pytest.raises(ValueError):
        ProblemAnalysisBatchResult(
            successful=(succ,),
            failed=(fail,),
            c15_version=C15_VERSION,
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


def test_batch_result_provenance_must_be_well_formed():
    with pytest.raises((ValueError, TypeError)):
        ProblemAnalysisBatchResult(
            successful=(),
            failed=(),
            c15_version="",
            c15_check_registry_version=C15_CHECK_REGISTRY_VERSION,
            advisory_schema_version=EXPECTED_ADVISORY_SCHEMA_VERSION,
        )


# =============================================================================
# Inv P0 STRICTER — moat-lint surface check
# =============================================================================

def test_inv_p0_no_module_level_aggregator_in_public_api():
    """Inv P0 (v0.2 A1 STRICTER): C15 NEVER computes a single number
    representing layout quality, anywhere — not in public API, not in
    helpers, not in telemetry, not in cache keys.

    This test scans the public surface (`buildemup.components.c15.__all__`)
    looking for any callable whose name matches a quality-aggregation
    pattern. If one appears, this fails (forcing intentional review).

    Cache-key digest functions return strings, not floats; they are
    excluded from this scan by name allow-list.
    """
    import buildemup.components.c15 as c15_pkg

    forbidden_substrings = ("score", "quality_index", "aggregate", "overall", "summary_metric")
    allowlist_callable_names = {"derive_c15_cache_keys", "config_signature_for"}

    for name in c15_pkg.__all__:
        obj = getattr(c15_pkg, name)
        if not callable(obj):
            continue
        if name in allowlist_callable_names:
            continue
        lower = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lower, (
                f"Inv P0 violation: public callable '{name}' contains "
                f"forbidden quality-aggregation substring '{forbidden}'. "
                f"C15 MUST NOT expose layout-quality aggregators."
            )


def test_inv_p0_no_module_level_constant_named_like_quality_score():
    """Companion to the test above: also verify no public constant
    name suggests a quality score."""
    import buildemup.components.c15 as c15_pkg

    forbidden_substrings = ("quality_score", "overall_score", "layout_score")
    for name in c15_pkg.__all__:
        lower = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lower, (
                f"Inv P0 violation: public name '{name}' suggests "
                f"a layout quality score. C15 has none."
            )
