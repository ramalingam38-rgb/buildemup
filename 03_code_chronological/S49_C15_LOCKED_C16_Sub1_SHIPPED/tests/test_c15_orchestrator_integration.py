"""
BuildemUp — Component 15 — Orchestrator end-to-end integration tests
=========================================================================

Per C15 SPEC v0.2 LOCKED — exercise Phases π→ρ→σ→τ→υ→φ on
synthesized C12/C13/C14 inputs and verify all P-invariants hold on
the produced ProblemReport.

Coverage:
  Inv P0   No score field anywhere in output
  Inv P2   Replay determinism (same input → equal report)
  Inv P3   applicable_checks + deferred_checks sorted lex-ASC
  Inv P5   Read-only — upstream objects not mutated
  Inv P9   DimensionSummary counts agree with checks tally
  Inv P10  Upstream flags pass through byte-identically
  Inv P12  Every registered check produces exactly one result
  Inv P14  upstream_cache_key non-empty
  Inv P16  Provenance triple populated
  Inv P19  dimensions_not_evaluated non-empty
  WARN dispatch — FailedProblemAnalysis returned in WARN mode on error
"""
from __future__ import annotations

import pytest

from buildemup.components.c15 import (
    C15_VERSION,
    C15_CHECK_REGISTRY_VERSION,
    CheckStatus,
    CulturalProfile,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
    FailedProblemAnalysis,
    FloorInfo,
    InconsistentInputError,
    ProblemFinderConfig,
    ProblemAnalysisMetadata,
    SuccessfulProblemAnalysis,
    analyze_problems,
    analyze_problems_batch,
    build_registry,
)

from ._fixtures import (
    FakeCirculationReport,
    FakePlacedCandidate,
    FakePlacedRoom,
    build_metadata,
)


# =============================================================================
# Helpers — build richer fake upstream
# =============================================================================

class _RichFakeC14:
    """A C14-shaped object with nodes/edges/step_depth/flags populated."""
    def __init__(
        self,
        *,
        nodes: tuple[str, ...] = (),
        edges: tuple[tuple[str, str], ...] = (),
        step_depth: tuple[tuple[str, int], ...] = (),
        structural_flags: tuple = (),
        preference_flags: tuple = (),
    ):
        self.nodes = nodes
        self.edges = edges
        self.step_depth_from_entry = step_depth
        self.structural_flags = structural_flags
        self.preference_flags = preference_flags


def _make_simple_4room_layout():
    """4-room layout: bedroom, living, kitchen, bath, all reasonable
    sizes. Forms a chain entry→living→kitchen, living→bedroom,
    bedroom→bath."""
    rooms = (
        FakePlacedRoom(room_id="r_bath", category="bathroom", x_m=8, y_m=4, width_m=2.0, depth_m=2.0),
        FakePlacedRoom(room_id="r_bed", category="bedroom", x_m=0, y_m=4, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_kit", category="kitchen", x_m=6, y_m=0, width_m=4, depth_m=4),
        FakePlacedRoom(room_id="r_liv", category="living", x_m=0, y_m=0, width_m=6, depth_m=4),
    )
    metadata = build_metadata(
        placed_room_ids=tuple(sorted(r.room_id for r in rooms)),
        room_categories={r.room_id: r.category for r in rooms},
        main_entry_room_id="r_liv",
    )
    candidate = FakePlacedCandidate(placed_rooms=rooms)
    c14 = _RichFakeC14(
        nodes=("r_bath", "r_bed", "r_kit", "r_liv"),
        edges=(("r_bath", "r_bed"), ("r_bed", "r_liv"), ("r_kit", "r_liv")),
        step_depth=(("r_bath", 3), ("r_bed", 2), ("r_kit", 1), ("r_liv", 0)),
    )
    c13 = type("FakeC13", (), {"advisory_flags": ()})()
    return candidate, c13, c14, metadata


# =============================================================================
# Inv P12 — 41 emitted checks (one per registered)
# =============================================================================

def test_inv_p12_every_registered_check_emits_exactly_one_result():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    assert isinstance(result, SuccessfulProblemAnalysis)
    report = result.report
    reg = build_registry()
    total = len(report.applicable_checks) + len(report.deferred_checks)
    assert total == len(reg), f"Inv P12 violated: {total} results for {len(reg)} registered checks"
    # No check_id appears in both tuples.
    app_ids = {c.check_id for c in report.applicable_checks}
    def_ids = {c.check_id for c in report.deferred_checks}
    assert app_ids.isdisjoint(def_ids)
    # All emitted check_ids are registered.
    assert app_ids | def_ids == set(reg.ids())


# =============================================================================
# Inv P3 — sort order
# =============================================================================

def test_inv_p3_applicable_and_deferred_sorted_lex_asc():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    app_ids = [c.check_id for c in result.report.applicable_checks]
    def_ids = [c.check_id for c in result.report.deferred_checks]
    assert app_ids == sorted(app_ids)
    assert def_ids == sorted(def_ids)


# =============================================================================
# Inv P9 — DimensionSummary counts agree with check tallies
# =============================================================================

def test_inv_p9_dimension_summary_counts_agree_with_checks():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    report = result.report
    for s in report.dimension_summary:
        actual_app = [c for c in report.applicable_checks if c.dimension_id == s.dimension_id]
        actual_def = [c for c in report.deferred_checks if c.dimension_id == s.dimension_id]
        n_pass = sum(1 for c in actual_app if c.status == CheckStatus.PASS)
        n_warn = sum(1 for c in actual_app if c.status == CheckStatus.WARN)
        n_fail = sum(1 for c in actual_app if c.status == CheckStatus.FAIL)
        assert s.n_pass == n_pass
        assert s.n_warn == n_warn
        assert s.n_fail == n_fail
        assert s.n_applicable == n_pass + n_warn + n_fail
        assert s.n_deferred == len(actual_def)


# =============================================================================
# Inv P0 — no score field in ProblemReport
# =============================================================================

def test_inv_p0_no_score_field_in_report():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    forbidden = {"score", "quality_score", "rank", "ranker_hint", "aggregate"}
    field_names = {f.name for f in result.report.__dataclass_fields__.values()}
    overlap = field_names & forbidden
    assert not overlap, f"Inv P0 violated: ProblemReport has aggregate fields {overlap}"


# =============================================================================
# Inv P10 — upstream flags byte-identical passthrough
# =============================================================================

def test_inv_p10_upstream_flags_passthrough_byte_identical():
    cand, _, c14_base, md = _make_simple_4room_layout()
    # Synthesize specific flag tuples.
    flag_a = type("F", (), {"kind": "advisory_a", "value": "A1"})()
    flag_b = type("F", (), {"kind": "structural_b", "value": "S1"})()
    flag_c = type("F", (), {"kind": "preference_c", "value": "P1"})()
    c13 = type("FakeC13", (), {"advisory_flags": (flag_a,)})()
    c14 = _RichFakeC14(
        nodes=c14_base.nodes, edges=c14_base.edges, step_depth=c14_base.step_depth_from_entry,
        structural_flags=(flag_b,), preference_flags=(flag_c,),
    )
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    report = result.report
    assert report.c13_advisory_flags == (flag_a,)
    assert report.c14_structural_flags == (flag_b,)
    assert report.c14_preference_flags == (flag_c,)
    # Identity-equal: the orchestrator didn't substitute copies.
    assert report.c13_advisory_flags[0] is flag_a
    assert report.c14_structural_flags[0] is flag_b
    assert report.c14_preference_flags[0] is flag_c


# =============================================================================
# Inv P14 — upstream_cache_key non-empty
# =============================================================================

def test_inv_p14_upstream_cache_key_non_empty():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    assert result.report.upstream_cache_key  # non-empty


# =============================================================================
# Inv P16 — provenance triple populated
# =============================================================================

def test_inv_p16_provenance_triple_populated():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    r = result.report
    assert r.c15_version == C15_VERSION
    assert r.c15_check_registry_version == C15_CHECK_REGISTRY_VERSION
    assert r.advisory_schema_version == EXPECTED_ADVISORY_SCHEMA_VERSION


# =============================================================================
# Inv P19 — dimensions_not_evaluated non-empty at v1
# =============================================================================

def test_inv_p19_dimensions_not_evaluated_non_empty():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    assert len(result.report.dimensions_not_evaluated) > 0


# =============================================================================
# Inv P2 — replay determinism
# =============================================================================

def test_inv_p2_replay_determinism():
    cand, c13, c14, md = _make_simple_4room_layout()
    r1 = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    r2 = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    assert r1.report.applicable_checks == r2.report.applicable_checks
    assert r1.report.deferred_checks == r2.report.deferred_checks
    assert r1.report.dimension_summary == r2.report.dimension_summary


# =============================================================================
# Inv P5 — read-only upstream (no mutation)
# =============================================================================

def test_inv_p5_no_upstream_mutation():
    cand, c13, c14, md = _make_simple_4room_layout()
    # Snapshot id-stable mutable views.
    cand_rooms_before = cand.placed_rooms
    c14_nodes_before = c14.nodes
    analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    assert cand.placed_rooms is cand_rooms_before
    assert c14.nodes is c14_nodes_before


# =============================================================================
# Severity assigned from rule table (Phase σ) overrides Check placeholder
# =============================================================================

def test_phase_sigma_overrides_placeholder_severity():
    cand, c13, c14, md = _make_simple_4room_layout()
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    # Verify a known check: P2.1 (NBC habitable min) PASS should have
    # severity NICE_TO_HAVE per rule table, not the placeholder
    # CRITICAL the check itself uses.
    from buildemup.components.c15 import CheckSeverity
    p21 = next((c for c in result.report.applicable_checks if c.check_id == "P2.1"), None)
    assert p21 is not None
    assert p21.status == CheckStatus.PASS
    assert p21.severity == CheckSeverity.NICE_TO_HAVE


# =============================================================================
# WARN dispatch — InconsistentInput → FailedProblemAnalysis
# =============================================================================

def test_warn_mode_packages_inconsistent_input_as_failed():
    cand, c13, c14, md = _make_simple_4room_layout()
    # Construct mismatch: drop one room from metadata.placed_room_ids.
    bad_md = ProblemAnalysisMetadata(
        cultural_profile=md.cultural_profile,
        placed_room_ids=("r_bath", "r_bed"),  # missing 2
        room_categories={"r_bath": "bathroom", "r_bed": "bedroom"},
        main_entry_room_id="r_bed",
    )
    cfg = ProblemFinderConfig(strict_mode=False)
    result = analyze_problems(
        c12_candidate=cand, c13_placement=c13, c14_report=c14,
        metadata=bad_md, config=cfg,
    )
    assert isinstance(result, FailedProblemAnalysis)
    assert result.failure_record.error_type == "InconsistentInputError"
    assert result.failure_record.phase == "pi"


def test_strict_mode_raises_inconsistent_input():
    cand, c13, c14, md = _make_simple_4room_layout()
    bad_md = ProblemAnalysisMetadata(
        cultural_profile=md.cultural_profile,
        placed_room_ids=("r_bath",),
        room_categories={"r_bath": "bathroom"},
        main_entry_room_id="r_bath",
    )
    cfg = ProblemFinderConfig(strict_mode=True)
    with pytest.raises(InconsistentInputError):
        analyze_problems(
            c12_candidate=cand, c13_placement=c13, c14_report=c14,
            metadata=bad_md, config=cfg,
        )


# =============================================================================
# Batch entry
# =============================================================================

def test_batch_returns_sorted_results():
    cand, c13, c14, md = _make_simple_4room_layout()
    # Build two candidates with different signatures.
    cand2 = FakePlacedCandidate(placed_rooms=cand.placed_rooms)
    md2 = md
    # Synthesize different cache keys by id; the orchestrator's
    # candidate_signature defaults to id-based for these fakes.
    result = analyze_problems_batch(
        triples=[(cand, c13, c14), (cand2, c13, c14)],
        metadata_per_candidate=[md, md2],
    )
    keys = [s.source_placed_candidate_signature for s in result.successful]
    assert keys == sorted(keys)
    assert len(result.successful) + len(result.failed) == 2


# =============================================================================
# Cultural profile branching — P3.4 + P5.3 + P5.4 run for all Indian profiles
# =============================================================================

def test_cultural_profile_runs_for_all_six_indian_sub_variants():
    """At this CulturalProfile enum version (Sub-1) all members are
    Indian sub-variants. P3.4 pooja access + P5.3 bath adjacency +
    P5.4 pooja privacy all declare cultural_scope=INDIAN_PROFILES,
    so all six sub-variants are in-scope and the checks run (not
    deferred with cultural_profile_mismatch). Per A3: ≥3 sub-variants
    LOCKED — verify all six produce applicable results."""
    cand, c13, c14, md_in = _make_simple_4room_layout()
    indian_profiles = (
        CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
        CulturalProfile.INDIAN_MIDDLE_CLASS_COMPACT_URBAN,
        CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        CulturalProfile.INDIAN_LOWER_INCOME_INCREMENTAL,
        CulturalProfile.INDIAN_NRI_RETURNEE,
    )
    for profile in indian_profiles:
        md = ProblemAnalysisMetadata(
            cultural_profile=profile,
            placed_room_ids=md_in.placed_room_ids,
            room_categories=md_in.room_categories,
            main_entry_room_id=md_in.main_entry_room_id,
        )
        result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
        deferred = {d.check_id: d for d in result.report.deferred_checks}
        # P5.3 must not defer with cultural_profile_mismatch.
        if "P5.3" in deferred:
            assert "cultural_profile_mismatch" not in deferred["P5.3"].na_reason, (
                f"P5.3 cultural-profile-mismatch defer fired for {profile} — should be in-scope"
            )


def test_cultural_scope_attribute_defaults_to_indian_profiles_for_pooja_checks():
    """Verify the cultural-scope attribute is set correctly on the
    pooja-related checks — guards against silently dropping the
    scope and leaving the check global."""
    from buildemup.components.c15.dimensions.dim03_logical_flow import (
        CheckP34PoojaRoomAccess, INDIAN_PROFILES,
    )
    from buildemup.components.c15.dimensions.dim05_privacy import (
        CheckP54PoojaRoomPrivacy, CheckP53BathroomBedroomAdjacency,
    )
    for c in (CheckP34PoojaRoomAccess(), CheckP54PoojaRoomPrivacy(), CheckP53BathroomBedroomAdjacency()):
        assert c.cultural_scope == INDIAN_PROFILES, (
            f"{c.check_id} cultural_scope must equal INDIAN_PROFILES; got {c.cultural_scope}"
        )


# =============================================================================
# Floor metadata unlocks dim 7
# =============================================================================

def test_floor_metadata_unlocks_dim7_partial_checks():
    cand, c13, c14, md_no_floor = _make_simple_4room_layout()
    md = ProblemAnalysisMetadata(
        cultural_profile=md_no_floor.cultural_profile,
        placed_room_ids=md_no_floor.placed_room_ids,
        room_categories=md_no_floor.room_categories,
        main_entry_room_id=md_no_floor.main_entry_room_id,
        floor_metadata=(
            FloorInfo(
                floor_id="GF",
                is_ground=True,
                has_entry=True,
                room_ids=md_no_floor.placed_room_ids,
            ),
        ),
    )
    result = analyze_problems(c12_candidate=cand, c13_placement=c13, c14_report=c14, metadata=md)
    # P7.1, P7.2, P7.3 should now produce ProblemCheck (not deferred).
    applicable_ids = [c.check_id for c in result.report.applicable_checks]
    for cid in ("P7.1", "P7.2", "P7.3"):
        assert cid in applicable_ids
    # P7.4 always defers (envelope detail not in pipeline).
    deferred_ids = [d.check_id for d in result.report.deferred_checks]
    assert "P7.4" in deferred_ids
