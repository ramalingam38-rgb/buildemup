"""C16 Sub-1 — contracts.py tests.

Coverage focus:
    - Frozen dataclass discipline (immutability + hashability)
    - SelectionResult / replay-identity / audit-metadata construction
    - AttestedValue R22 authority discipline (all 3 authority kinds × valid + invalid combos)
    - JurisdictionProfile R31b enforcement
    - GeospatialReference range checks
    - OrientationLock construction-time validation (geometry-plausibility deferred)
    - Enum completeness
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from buildemup.components.c16 import (
    AttestedValue,
    AuthorityKind,
    C16ConfigurationError,
    CandidateRanking,
    CheckProvenance,
    ComplianceProvenanceError,
    ElementKind,
    GeospatialReference,
    HumanOverrideRecord,
    JurisdictionNotSupportedError,
    JurisdictionProfile,
    LegalCompleteness,
    LocalBuildingFrame,
    OrientationLock,
    ReadabilityStatus,
    SelectionAuditMetadata,
    SelectionReason,
    SelectionReplayIdentity,
    SelectionResult,
)


# ============================================================
# § 1 — SelectionReason enum
# ============================================================

class TestSelectionReasonEnum:
    @pytest.mark.parametrize("name", [
        "HUMAN_CHOICE", "RANKER_TOP", "TIEBREAK_DETERMINISTIC",
        "DEFAULT_FIRST", "UNKNOWN_LEGACY",
    ])
    def test_all_documented_reasons_present(self, name):
        assert hasattr(SelectionReason, name)

    def test_no_extra_reasons(self):
        # Tight enum — bumping requires schema bump
        assert len(list(SelectionReason)) == 5


# ============================================================
# § 2 — CandidateRanking
# ============================================================

class TestCandidateRanking:
    def test_valid_construction(self):
        c = CandidateRanking(
            layout_signature="sig_abc",
            rank_position=1,
            score=0.9,
            selection_marker=True,
        )
        assert c.layout_signature == "sig_abc"
        assert c.rank_position == 1
        assert c.score == 0.9
        assert c.selection_marker is True

    def test_zero_or_negative_rank_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CandidateRanking(
                layout_signature="x", rank_position=0,
                score=0.0, selection_marker=False,
            )
        with pytest.raises(C16ConfigurationError):
            CandidateRanking(
                layout_signature="x", rank_position=-1,
                score=0.0, selection_marker=False,
            )

    def test_empty_signature_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CandidateRanking(
                layout_signature="", rank_position=1,
                score=0.0, selection_marker=False,
            )

    def test_frozen(self):
        c = CandidateRanking("sig", 1, 0.5, True)
        with pytest.raises(FrozenInstanceError):
            c.score = 1.0  # type: ignore[misc]


# ============================================================
# § 3 — HumanOverrideRecord
# ============================================================

class TestHumanOverrideRecord:
    def test_valid_override(self):
        h = HumanOverrideRecord(
            chosen_layout_signature="sig_human",
            overridden_layout_signature="sig_ranker_top",
            override_reason="family preferred courtyard layout",
            overrider_actor_id="user_42",
        )
        assert h.chosen_layout_signature == "sig_human"

    def test_chosen_equals_overridden_rejected(self):
        # If chosen == overridden, that's not an override
        with pytest.raises(C16ConfigurationError):
            HumanOverrideRecord(
                chosen_layout_signature="sig_x",
                overridden_layout_signature="sig_x",
                override_reason="oops",
            )

    def test_optional_actor_id_defaults_to_none(self):
        h = HumanOverrideRecord(
            chosen_layout_signature="a",
            overridden_layout_signature="b",
            override_reason="reason",
        )
        assert h.overrider_actor_id is None


# ============================================================
# § 4 — SelectionReplayIdentity (v0.3 A1)
# ============================================================

def _good_ranking(signature: str = "sel_sig") -> tuple[CandidateRanking, ...]:
    return (
        CandidateRanking(signature, 1, 0.9, True),
        CandidateRanking("other_sig", 2, 0.7, False),
    )


class TestSelectionReplayIdentity:
    def test_minimal_valid(self):
        r = SelectionReplayIdentity(
            selected_layout_signature="sel_sig",
            selector_version="auto_v0.1",
            selection_reason=SelectionReason.RANKER_TOP,
            candidate_ranking_snapshot=_good_ranking(),
            upstream_problem_reports=(),
        )
        assert r.selected_layout_signature == "sel_sig"
        assert r.selection_reason == SelectionReason.RANKER_TOP

    def test_empty_signature_rejected(self):
        with pytest.raises(C16ConfigurationError):
            SelectionReplayIdentity(
                selected_layout_signature="",
                selector_version="auto_v0.1",
                selection_reason=SelectionReason.RANKER_TOP,
                candidate_ranking_snapshot=_good_ranking("sel_sig"),
                upstream_problem_reports=(),
            )

    def test_empty_selector_version_rejected(self):
        with pytest.raises(C16ConfigurationError):
            SelectionReplayIdentity(
                selected_layout_signature="sel_sig",
                selector_version="",
                selection_reason=SelectionReason.RANKER_TOP,
                candidate_ranking_snapshot=_good_ranking(),
                upstream_problem_reports=(),
            )

    def test_zero_marked_candidates_rejected(self):
        ranking = (
            CandidateRanking("a", 1, 1.0, False),
            CandidateRanking("b", 2, 0.5, False),
        )
        with pytest.raises(C16ConfigurationError):
            SelectionReplayIdentity(
                selected_layout_signature="a",
                selector_version="auto",
                selection_reason=SelectionReason.RANKER_TOP,
                candidate_ranking_snapshot=ranking,
                upstream_problem_reports=(),
            )

    def test_multiple_marked_candidates_rejected(self):
        ranking = (
            CandidateRanking("a", 1, 1.0, True),
            CandidateRanking("b", 2, 0.5, True),
        )
        with pytest.raises(C16ConfigurationError):
            SelectionReplayIdentity(
                selected_layout_signature="a",
                selector_version="auto",
                selection_reason=SelectionReason.RANKER_TOP,
                candidate_ranking_snapshot=ranking,
                upstream_problem_reports=(),
            )

    def test_selected_signature_must_match_marked_candidate(self):
        # Selected is "a" but marker is on "b" — inconsistent
        ranking = (
            CandidateRanking("a", 1, 1.0, False),
            CandidateRanking("b", 2, 0.5, True),
        )
        with pytest.raises(C16ConfigurationError):
            SelectionReplayIdentity(
                selected_layout_signature="a",
                selector_version="auto",
                selection_reason=SelectionReason.RANKER_TOP,
                candidate_ranking_snapshot=ranking,
                upstream_problem_reports=(),
            )

    def test_empty_ranking_is_allowed(self):
        # An empty ranking is permitted (e.g. default_first fallback);
        # the marker-consistency check only fires if there's a snapshot.
        r = SelectionReplayIdentity(
            selected_layout_signature="lone_sig",
            selector_version="default",
            selection_reason=SelectionReason.DEFAULT_FIRST,
            candidate_ranking_snapshot=(),
            upstream_problem_reports=(),
        )
        assert r.candidate_ranking_snapshot == ()


# ============================================================
# § 5 — SelectionAuditMetadata
# ============================================================

class TestSelectionAuditMetadata:
    def test_minimal_valid(self):
        m = SelectionAuditMetadata(selection_timestamp_utc="2026-05-15T00:00:00Z")
        assert m.selection_timestamp_utc == "2026-05-15T00:00:00Z"
        assert m.human_override is None
        assert m.selector_instance_id is None
        assert m.selection_machine_fingerprint is None

    def test_empty_timestamp_rejected(self):
        with pytest.raises(C16ConfigurationError):
            SelectionAuditMetadata(selection_timestamp_utc="")


# ============================================================
# § 6 — SelectionResult
# ============================================================

class TestSelectionResult:
    def test_compose_replay_and_audit(self):
        replay = SelectionReplayIdentity(
            selected_layout_signature="sel_sig",
            selector_version="auto",
            selection_reason=SelectionReason.RANKER_TOP,
            candidate_ranking_snapshot=_good_ranking(),
            upstream_problem_reports=(),
        )
        audit = SelectionAuditMetadata(
            selection_timestamp_utc="2026-05-15T01:00:00Z",
        )
        s = SelectionResult(replay_identity=replay, audit_metadata=audit)
        assert s.replay_identity is replay
        assert s.audit_metadata is audit


# ============================================================
# § 7 — AttestedValue R22 authority discipline
# ============================================================

class TestAttestedValueAuthorityDiscipline:
    # --- UPSTREAM_AUTHORITATIVE ---

    def test_upstream_authoritative_valid(self):
        a = AttestedValue(
            value=1500.0,
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source="c4_plot_analysis:plot_area_sqm",
        )
        assert a.value == 1500.0
        assert a.derivation_note is None

    def test_upstream_authoritative_missing_source_rejected(self):
        with pytest.raises(ComplianceProvenanceError) as excinfo:
            AttestedValue(
                value=1500.0,
                authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                upstream_source=None,
            )
        assert excinfo.value.invariant_id == "R22"

    def test_upstream_authoritative_with_derivation_note_rejected(self):
        # Upstream values should not have derivation notes
        with pytest.raises(ComplianceProvenanceError) as excinfo:
            AttestedValue(
                value=1500.0,
                authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                upstream_source="c4:area",
                derivation_note="something",
            )
        assert excinfo.value.invariant_id == "R22"

    # --- LOCALLY_DERIVED ---

    def test_locally_derived_valid(self):
        a = AttestedValue(
            value=25.5,
            authority=AuthorityKind.LOCALLY_DERIVED,
            derivation_note="built_up_area / plot_area * 100",
        )
        assert a.value == 25.5
        assert a.upstream_source is None

    def test_locally_derived_missing_note_rejected(self):
        with pytest.raises(ComplianceProvenanceError) as excinfo:
            AttestedValue(
                value=25.5,
                authority=AuthorityKind.LOCALLY_DERIVED,
            )
        assert excinfo.value.invariant_id == "R22"

    def test_locally_derived_with_upstream_source_rejected(self):
        # If it's locally derived, it didn't come from upstream
        with pytest.raises(ComplianceProvenanceError):
            AttestedValue(
                value=25.5,
                authority=AuthorityKind.LOCALLY_DERIVED,
                upstream_source="c2:something",
                derivation_note="ratio",
            )

    # --- CROSS_CHECK_VERIFICATION ---

    def test_cross_check_verification_valid(self):
        a = AttestedValue(
            value=0.85,
            authority=AuthorityKind.CROSS_CHECK_VERIFICATION,
            upstream_source="c2_feasibility:far_used",
            derivation_note="built_up_area / plot_area (cross-checked vs C2 FAR)",
        )
        assert a.upstream_source.startswith("c2")
        assert "cross-checked" in a.derivation_note

    def test_cross_check_missing_source_rejected(self):
        with pytest.raises(ComplianceProvenanceError):
            AttestedValue(
                value=0.85,
                authority=AuthorityKind.CROSS_CHECK_VERIFICATION,
                derivation_note="local ratio",
            )

    def test_cross_check_missing_note_rejected(self):
        with pytest.raises(ComplianceProvenanceError):
            AttestedValue(
                value=0.85,
                authority=AuthorityKind.CROSS_CHECK_VERIFICATION,
                upstream_source="c2:far",
            )

    # --- value type guard ---

    @pytest.mark.parametrize("value", [1.5, 3, True, False, 0])
    def test_accepted_value_types(self, value):
        AttestedValue(
            value=value,
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source="c_x:y",
        )

    @pytest.mark.parametrize("value", ["string", None, [], {}, (1, 2)])
    def test_rejected_value_types(self, value):
        with pytest.raises(C16ConfigurationError):
            AttestedValue(
                value=value,  # type: ignore[arg-type]
                authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                upstream_source="c_x:y",
            )


# ============================================================
# § 8 — Coordinate frames (LocalBuildingFrame + GeospatialReference)
# ============================================================

class TestLocalBuildingFrame:
    def test_marker_type_constructs_without_args(self):
        # No fields — pure marker
        lbf = LocalBuildingFrame()
        assert lbf is not None

    def test_marker_type_instances_compare_equal(self):
        # No-field frozen dataclasses are equal by definition
        assert LocalBuildingFrame() == LocalBuildingFrame()


class TestGeospatialReference:
    def _good(self, **kwargs):
        defaults = dict(
            local_origin_in_plot_mm=(0, 0),
            rotation_from_plot_north_deg=0.0,
            plot_north_arrow_orientation_deg=0.0,
            orientation_basis="longest_wall",
        )
        defaults.update(kwargs)
        return GeospatialReference(**defaults)

    def test_minimal_valid(self):
        g = self._good()
        assert g.rotation_from_plot_north_deg == 0.0
        assert g.orientation_basis == "longest_wall"

    def test_rotation_at_360_rejected(self):
        # Range is [0, 360)
        with pytest.raises(C16ConfigurationError):
            self._good(rotation_from_plot_north_deg=360.0)

    def test_rotation_negative_rejected(self):
        with pytest.raises(C16ConfigurationError):
            self._good(rotation_from_plot_north_deg=-1.0)

    def test_plot_north_at_360_rejected(self):
        with pytest.raises(C16ConfigurationError):
            self._good(plot_north_arrow_orientation_deg=360.0)

    def test_lat_out_of_range_rejected(self):
        with pytest.raises(C16ConfigurationError):
            self._good(geospatial_latitude=91.0)

    def test_lng_out_of_range_rejected(self):
        with pytest.raises(C16ConfigurationError):
            self._good(geospatial_longitude=181.0)

    def test_optional_geospatial_omittable(self):
        g = self._good()
        assert g.geospatial_latitude is None
        assert g.geospatial_longitude is None
        assert g.geospatial_elevation_m is None

    def test_valid_chennai_coords(self):
        # Chennai ~13.08 N, 80.27 E
        g = self._good(
            geospatial_latitude=13.0827,
            geospatial_longitude=80.2707,
            geospatial_elevation_m=6.7,
        )
        assert g.geospatial_latitude == 13.0827


# ============================================================
# § 9 — OrientationLock (v0.5 A5)
# ============================================================

class TestOrientationLock:
    def test_minimal_valid(self):
        o = OrientationLock(
            locked_at_first_publish=True,
            locked_x_axis_orientation_deg=45.0,
            locked_origin_basis="primary_entrance",
            lock_provenance="first_published_2026_03_15",
        )
        assert o.locked_at_first_publish is True
        assert o.locked_x_axis_orientation_deg == 45.0

    def test_orientation_at_360_rejected(self):
        with pytest.raises(C16ConfigurationError):
            OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=360.0,
                locked_origin_basis="longest_wall",
                lock_provenance="x",
            )

    def test_orientation_negative_rejected(self):
        with pytest.raises(C16ConfigurationError):
            OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=-0.1,
                locked_origin_basis="longest_wall",
                lock_provenance="x",
            )

    def test_empty_provenance_rejected(self):
        with pytest.raises(C16ConfigurationError):
            OrientationLock(
                locked_at_first_publish=True,
                locked_x_axis_orientation_deg=0.0,
                locked_origin_basis="longest_wall",
                lock_provenance="",
            )

    def test_frozen(self):
        o = OrientationLock(True, 0.0, "longest_wall", "p")
        with pytest.raises(FrozenInstanceError):
            o.lock_provenance = "other"  # type: ignore[misc]


# ============================================================
# § 10 — JurisdictionProfile (R31b enforcement)
# ============================================================

class TestJurisdictionProfile:
    def test_minimal_valid_tncdbr(self):
        j = JurisdictionProfile(jurisdiction_id="tn_cdbr_2019")
        assert j.jurisdiction_id == "tn_cdbr_2019"
        assert j.declared_domain_scope == "residential_v1"
        assert j.orientation_lock is None

    @pytest.mark.parametrize("scope", [
        "residential_v1", "small_commercial_v1", "mixed_use_v1",
    ])
    def test_all_v1_scopes_accepted(self, scope):
        j = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope=scope,
        )
        assert j.declared_domain_scope == scope

    @pytest.mark.parametrize("scope", [
        "industrial_v1", "township_v1", "infrastructure_v1", "campus_v1",
    ])
    def test_out_of_scope_domain_rejected(self, scope):
        with pytest.raises(C16ConfigurationError) as excinfo:
            JurisdictionProfile(
                jurisdiction_id="tn_cdbr_2019",
                declared_domain_scope=scope,  # type: ignore[arg-type]
            )
        # Spec references R31b
        assert "R31b" in str(excinfo.value)

    def test_unsupported_jurisdiction_rejected(self):
        with pytest.raises(JurisdictionNotSupportedError) as excinfo:
            JurisdictionProfile(jurisdiction_id="ka_bbmp_2020")
        assert excinfo.value.requested_jurisdiction == "ka_bbmp_2020"

    def test_orientation_hint_in_range_accepted(self):
        j = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            local_x_axis_orientation_deg_hint=45.0,
        )
        assert j.local_x_axis_orientation_deg_hint == 45.0

    def test_orientation_hint_at_360_rejected(self):
        with pytest.raises(C16ConfigurationError):
            JurisdictionProfile(
                jurisdiction_id="tn_cdbr_2019",
                local_x_axis_orientation_deg_hint=360.0,
            )

    def test_with_orientation_lock(self):
        lock = OrientationLock(
            locked_at_first_publish=True,
            locked_x_axis_orientation_deg=0.0,
            locked_origin_basis="longest_wall",
            lock_provenance="p",
        )
        j = JurisdictionProfile(
            jurisdiction_id="tn_cdbr_2019",
            orientation_lock=lock,
        )
        assert j.orientation_lock is lock


# ============================================================
# § 11 — LegalCompleteness / ReadabilityStatus enums
# ============================================================

class TestStatusEnumsOrthogonality:
    def test_legal_completeness_values(self):
        assert {e.value for e in LegalCompleteness} == {
            "legally_complete",
            "legally_incomplete",
            "unsafe_for_submission",
        }

    def test_readability_status_values(self):
        assert {e.value for e in ReadabilityStatus} == {
            "readable",
            "review_recommended",
            "readability_degraded",
        }

    def test_enums_are_disjoint_types(self):
        # Per R30: orthogonal types — instances are never equal across enums
        for lc in LegalCompleteness:
            for rs in ReadabilityStatus:
                assert lc != rs


# ============================================================
# § 12 — ElementKind taxonomy
# ============================================================

class TestElementKindTaxonomy:
    def test_wall_kinds_present(self):
        assert ElementKind.WALL_EXTERNAL.value == "wall_external"
        assert ElementKind.WALL_INTERNAL_LOAD_BEARING.value
        assert ElementKind.WALL_INTERNAL_PARTITION.value
        assert ElementKind.WALL_PARAPET.value

    def test_opening_kinds_present(self):
        assert ElementKind.DOOR_EXTERNAL
        assert ElementKind.DOOR_INTERNAL
        assert ElementKind.WINDOW_EXTERNAL
        assert ElementKind.WINDOW_VENTILATOR

    def test_structural_kinds_present(self):
        for name in ["COLUMN", "BEAM", "SLAB_FLOOR", "SLAB_ROOF"]:
            assert hasattr(ElementKind, name)

    def test_plumbing_stack_kinds_present(self):
        assert ElementKind.PLUMBING_STACK_FRESH_WATER
        assert ElementKind.PLUMBING_STACK_WASTE
        assert ElementKind.PLUMBING_STACK_RAIN_WATER

    def test_compliance_overlay_kinds_present(self):
        for name in [
            "SETBACK_MARKER", "FAR_ANNOTATION", "PARKING_BAY",
            "RWH_FACILITY", "SEWAGE_FACILITY",
        ]:
            assert hasattr(ElementKind, name)

    def test_total_kind_count_pinned(self):
        # 4 wall + 4 opening + 4 structural + 3 plumbing + 5 compliance = 20
        # Adding kinds is MINOR; this test pins the v0.5 LOCK baseline.
        assert len(list(ElementKind)) == 20


# ============================================================
# § 13 — CheckProvenance
# ============================================================

class TestCheckProvenance:
    def test_minimal_valid(self):
        c = CheckProvenance(
            upstream_component="c2_feasibility",
            check_id="parking_width_feasibility",
            upstream_version="v1.0",
            attested_field_name="parking_compliance",
        )
        assert c.upstream_component == "c2_feasibility"

    @pytest.mark.parametrize("missing_field", [
        "upstream_component", "check_id",
        "upstream_version", "attested_field_name",
    ])
    def test_every_field_required_non_empty(self, missing_field):
        good_kwargs = dict(
            upstream_component="c2",
            check_id="cid",
            upstream_version="v1.0",
            attested_field_name="field",
        )
        good_kwargs[missing_field] = ""
        with pytest.raises(C16ConfigurationError):
            CheckProvenance(**good_kwargs)
