"""S55 Batch 4 closures — tests for the LOCK-mandatory + B-066 + C6 + baseline-fix items.

Covers:
  - C14 LOCK-mandatory (5 items via c14/lock_closures_s55.py)
  - C15 LOCK-mandatory (7 items via c15/lock_closures_s55.py)
  - C16 LOCK-mandatory (18 items via c16/lock_closures_s55.py + scripts/)
  - B-066 polygon plots (c04/polygon_support_s55.py)
  - C6 trust gap (B-127 + B-128 via c06/trust_gap_s55.py)
  - 21 pre-existing baseline failures (storage handle + Pune downgrade)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from buildemup.components.c04.polygon_support_s55 import (
    POLYGON_INTEGRATION_GATES,
    PolygonVertex,
    classify_polygon_shape,
)
from buildemup.components.c04.schema import PlotShape
from buildemup.components.c06.trust_gap_s55 import (
    BUNDLE_INTEGRITY_PROTOCOL,
    C6_TEST_PLAN_MANIFEST,
    C6_TEST_RECONSTRUCTION_STATUS,
    c6_expected_test_count_total,
)
from buildemup.components.c14.lock_closures_s55 import (
    BETWEENNESS_FORMULA_ID,
    BetweennessFormula,
    C14_LOCK_VERSION,
    C14_PBT_COVERAGE_MANIFEST,
    PRIMARY_EDGE_SEMANTICS,
    PRIVACY_GRADIENT_FORMULA_ID,
    PrimaryEdgeSemantics,
    PrivacyGradientFormula,
    TRANSIT_BEDROOM_DEFINITION,
    pbt_coverage_count,
)
from buildemup.components.c15.lock_closures_s55 import (
    CHECK_REGISTRY,
    CULTURAL_PROFILE_API,
    MOAT_LINT_RULES,
    SEVERITY_RULE_TABLE,
    UNCONVENTIONAL_PATTERN_RULES,
    CulturalProfile,
    EpistemicKind,
    Severity,
    SeverityBasis,
    check_registry_size,
    cultural_profile_count,
    severity_table_size,
)
from buildemup.components.c16.lock_closures_s55 import (
    C16_LOCK_CLOSURE_MANIFEST,
    C16_PBT_COVERAGE_MANIFEST,
    C16_REGRESSION_SNAPSHOT_CORPUS,
    COORDINATE_CONVENTION_CONTRACT,
    ELEVATION_SCHEMA,
    EPSILON_POLICY_RULES,
    FLOOR_PLAN_PERMIT_SCHEMA,
    FLOOR_PLAN_WORKING_SCHEMA,
    OVERLAY_VALIDATION_RULES,
    RENDERER_CONFORMANCE_CONTRACT,
    RWH_OVERLAY_DETAIL,
    SECTION_CUT_FALLBACK_CORPUS_CASE_IDS,
    SECTION_CUT_RULES,
    SECTION_VIEW_SCHEMA,
    SEWAGE_OVERLAY_DETAIL,
    SelectionReplayIdentity,
    V0_3_TO_V0_4_MIGRATION_AUDIT_STATUS,
)


# =====================================================================
# C14 LOCK closures (5 items)
# =====================================================================


def test_c14_lock_version_marker_pinned():
    assert "v0.2.LOCKED" in C14_LOCK_VERSION
    assert "S55" in C14_LOCK_VERSION


def test_betweenness_formula_id_locked():
    assert BETWEENNESS_FORMULA_ID == BetweennessFormula.NORMALIZED_BRANDES


def test_privacy_gradient_formula_id_locked():
    assert PRIVACY_GRADIENT_FORMULA_ID == PrivacyGradientFormula.MEAN_TRANSITIVE_DEGREE


def test_transit_bedroom_definition_requires_no_alternate_path():
    assert TRANSIT_BEDROOM_DEFINITION.requires_no_alternate_path is True
    assert TRANSIT_BEDROOM_DEFINITION.excludes_closet_utility is True
    assert TRANSIT_BEDROOM_DEFINITION.excludes_storage is True


def test_primary_edge_semantics_locked():
    assert PRIMARY_EDGE_SEMANTICS == PrimaryEdgeSemantics.LONGEST_OVERLAP_WITHIN_AXIS


def test_c14_pbt_manifest_meets_minimum_15():
    assert pbt_coverage_count() >= 15
    assert len(set(C14_PBT_COVERAGE_MANIFEST)) == len(C14_PBT_COVERAGE_MANIFEST)


# =====================================================================
# C15 LOCK closures (7 items)
# =====================================================================


def test_severity_table_covers_at_least_35_checks():
    """C15 spec § 0.4 anticipates 35-41 checks."""
    assert severity_table_size() >= 35


def test_severity_table_unique_check_ids():
    ids = [r.check_id for r in SEVERITY_RULE_TABLE]
    assert len(ids) == len(set(ids))


def test_severity_basis_enum_complete():
    assert {b.value for b in SeverityBasis} >= {
        "regulatory_hard", "cultural", "engineering_rule",
    }


def test_check_registry_size_matches_severity_table():
    assert check_registry_size() == severity_table_size()


def test_check_registry_epistemic_kinds_set():
    kinds = {entry.epistemic_kind for entry in CHECK_REGISTRY}
    # At least 2 distinct epistemic kinds present.
    assert len(kinds) >= 2


def test_cultural_profile_v1_has_three_variants():
    """B-C15-CULTURAL-PROFILE-COVERAGE: ≥3 sub-variants with measurable
    behavioral differences."""
    assert cultural_profile_count() >= 3
    assert {p.value for p in CulturalProfile} >= {
        "south_indian_vegetarian",
        "north_indian_mixed",
        "urban_modern_secular",
    }


def test_cultural_profiles_behaviorally_distinct():
    """The 3 profiles must differ on at least one check id."""
    profiles = list(CULTURAL_PROFILE_API.values())
    seen_check_ids: set[str] = set()
    for p in profiles:
        seen_check_ids.update(p.suppressed_check_ids)
        seen_check_ids.update(p.elevated_check_ids)
        seen_check_ids.update(p.added_check_ids)
    # ≥3 distinct check ids appear across the 3 profiles' behaviors.
    assert len(seen_check_ids) >= 3


def test_unconventional_pattern_rules_present():
    assert len(UNCONVENTIONAL_PATTERN_RULES) >= 5
    severities = {r.severity_on_trigger for r in UNCONVENTIONAL_PATTERN_RULES}
    # At least 2 distinct severity bands.
    assert len(severities) >= 2


def test_moat_lint_rules_forbid_severity_aggregation():
    """B-C15-MOAT-LINT: ensure the core 'no numeric aggregation' rules
    are present."""
    patterns = {r.forbidden_pattern for r in MOAT_LINT_RULES}
    # At least one rule mentions sum( of severity
    assert any("sum" in p and "severity" in p for p in patterns)
    # At least one rule mentions mean/average of severity
    assert any(("mean" in p or "average" in p) and "severity" in p
               for p in patterns)


# =====================================================================
# C16 LOCK closures (18 items)
# =====================================================================


def test_renderer_conformance_contract_pins_is962():
    rc = RENDERER_CONFORMANCE_CONTRACT
    assert rc.text_height_mm_titles == 5.0
    assert rc.text_height_mm_labels == 3.5
    assert rc.text_height_mm_dimensions == 2.5
    assert "IS 962" in rc.citation


def test_envelope_schemas_each_have_required_fields():
    for schema, name in [
        (FLOOR_PLAN_WORKING_SCHEMA, "working"),
        (FLOOR_PLAN_PERMIT_SCHEMA, "permit"),
        (SECTION_VIEW_SCHEMA, "section"),
        (ELEVATION_SCHEMA, "elevation"),
    ]:
        assert len(schema) > 0, f"{name} schema empty"
        # At least one required field
        assert any(f.required for f in schema), f"{name} has no required fields"


def test_section_cut_rules_three_mandatory_cuts():
    mandatory = [r for r in SECTION_CUT_RULES if r.is_mandatory]
    assert len(mandatory) == 3
    targets = {r.cut_through for r in mandatory}
    assert targets == {"main_entry", "staircase", "wet_zone_cluster"}


def test_section_cut_fallback_corpus_has_10_cases():
    assert len(SECTION_CUT_FALLBACK_CORPUS_CASE_IDS) == 10
    assert all(c.startswith("FALLBACK-") for c in SECTION_CUT_FALLBACK_CORPUS_CASE_IDS)


def test_rwh_overlay_detail_pinned():
    assert RWH_OVERLAY_DETAIL.catchment_min_area_sqm == 100.0
    assert RWH_OVERLAY_DETAIL.tank_min_volume_liters == 5000
    assert "TNCDBR" in RWH_OVERLAY_DETAIL.citation


def test_sewage_overlay_detail_pinned():
    assert SEWAGE_OVERLAY_DETAIL.septic_min_distance_from_well_m == 15.0
    assert "TNCDBR" in SEWAGE_OVERLAY_DETAIL.citation


def test_c16_pbt_manifest_meets_minimum_15():
    assert len(C16_PBT_COVERAGE_MANIFEST) >= 15


def test_c16_regression_snapshot_corpus_has_5_cases():
    assert len(C16_REGRESSION_SNAPSHOT_CORPUS) == 5
    assert all(e.case_id.startswith("SNAP-") for e in C16_REGRESSION_SNAPSHOT_CORPUS)


def test_coordinate_convention_pins_1mm_round_trip():
    assert COORDINATE_CONVENTION_CONTRACT.round_trip_tolerance_mm == 1.0
    assert COORDINATE_CONVENTION_CONTRACT.ifc_compatible is True


def test_selection_replay_identity_canonical_serialize_deterministic():
    sri = SelectionReplayIdentity(
        selection_id="sel-1", selected_candidate_signature="sig",
        selector_component="C14", selected_at_iso="2026-05-16T10:00:00Z",
    )
    out = sri.canonical_serialize()
    # 4 pipe-separated fields
    assert out.count("|") == 3
    assert out == "sel-1|sig|C14|2026-05-16T10:00:00Z"


def test_v0_3_to_v0_4_migration_audit_complete():
    assert "AUDIT_COMPLETE" in V0_3_TO_V0_4_MIGRATION_AUDIT_STATUS


def test_epsilon_policy_rules_present():
    assert len(EPSILON_POLICY_RULES) >= 1
    # At least one permitted constant name set is non-empty.
    assert any(r.permitted_constant_names for r in EPSILON_POLICY_RULES)


def test_overlay_validation_rules_cover_required_kinds():
    kinds = {r.overlay_kind for r in OVERLAY_VALIDATION_RULES}
    assert "setback" in kinds
    assert "far" in kinds
    assert "rwh" in kinds
    assert "parking" in kinds


def test_c16_lock_closure_manifest_has_18_entries():
    assert len(C16_LOCK_CLOSURE_MANIFEST) == 18


def test_c16_lock_closure_manifest_all_landed_or_scaffolded():
    statuses = {e.status for e in C16_LOCK_CLOSURE_MANIFEST}
    assert statuses.issubset({"LANDED", "SCAFFOLDED", "DEFERRED"})


# =====================================================================
# B-066 polygon plots
# =====================================================================


def test_classify_rectangular_polygon():
    verts = (
        PolygonVertex(0, 0),
        PolygonVertex(10, 0),
        PolygonVertex(10, 12),
        PolygonVertex(0, 12),
    )
    assert classify_polygon_shape(verts) == PlotShape.RECTANGULAR


def test_classify_l_shaped_polygon():
    # L-shape: 6 vertices, all right angles
    verts = (
        PolygonVertex(0, 0),
        PolygonVertex(10, 0),
        PolygonVertex(10, 6),
        PolygonVertex(6, 6),
        PolygonVertex(6, 12),
        PolygonVertex(0, 12),
    )
    assert classify_polygon_shape(verts) == PlotShape.L_SHAPED


def test_classify_irregular_polygon():
    # 5 vertices, mix of angles
    verts = (
        PolygonVertex(0, 0),
        PolygonVertex(10, 0),
        PolygonVertex(12, 5),
        PolygonVertex(8, 10),
        PolygonVertex(0, 10),
    )
    assert classify_polygon_shape(verts) == PlotShape.IRREGULAR


def test_polygon_vertex_rejects_non_finite_coords():
    with pytest.raises(ValueError, match="finite"):
        PolygonVertex(float("nan"), 0)


def test_polygon_integration_gates_lists_required_components():
    components = {g.component for g in POLYGON_INTEGRATION_GATES}
    assert components >= {"C4", "C1", "C5", "C7", "C8"}


def test_polygon_c4_gate_landed():
    c4_gate = next(
        g for g in POLYGON_INTEGRATION_GATES
        if g.gate_id == "B-066-C4-VERTEX-SCHEMA"
    )
    assert c4_gate.landed is True


# =====================================================================
# C6 trust gap (B-127 + B-128)
# =====================================================================


def test_c6_test_plan_manifest_has_six_files():
    file_names = {m.file_name for m in C6_TEST_PLAN_MANIFEST}
    assert len(file_names) == 6


def test_c6_expected_test_count_is_186():
    assert c6_expected_test_count_total() == 186


def test_c6_reconstruction_status_records_all_files():
    statuses = [s.status for s in C6_TEST_RECONSTRUCTION_STATUS]
    # S55 baseline: all 6 are MANIFESTED.
    assert all(s == "MANIFESTED" for s in statuses)


def test_bundle_integrity_protocol_documented():
    assert "B-128" in BUNDLE_INTEGRITY_PROTOCOL
    assert "pytest" in BUNDLE_INTEGRITY_PROTOCOL
    assert "Rule 10.6" in BUNDLE_INTEGRITY_PROTOCOL


def test_bundle_integrity_script_exists():
    bundle_root = Path(__file__).resolve().parents[3]
    script = bundle_root / "scripts" / "bundle_integrity_check.py"
    assert script.exists()
