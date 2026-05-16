"""C16 Sub-1 — schema.py tests.

Coverage:
    - CanonicalTransform2D + R28d int64 overflow detection
    - ElementIdentity validation + compute_element_identity
    - FloorGeometry + geometry_ref property
    - WorkingDrawingModel / PermitDrawingModel SKETCH construction
    - PermitDrawingModel R21 + R30 legal_completeness gating
    - ComplianceAttestation R15 provenance requirement
    - DualDrawingBundle R20 / R24a / R24b / R24c / R33b enforcement
    - SchemaDescriptor + compute_schema_descriptor_digest
    - PhaseTimings + ReadabilityDiagnostics validation
"""
from __future__ import annotations

import pytest

from buildemup.components.c16 import (
    AdvisoryFlag,
    AttestedValue,
    AuthorityKind,
    C16CacheKeys,
    C16ConfigurationError,
    C16_IDENTITY_GENERATION,
    CanonicalTransform2D,
    CheckProvenance,
    ComplianceAttestation,
    ComplianceProvenanceError,
    DualDrawingBundle,
    ElementIdentity,
    ElementKind,
    FloorGeometry,
    GeometryInconsistencyError,
    GeospatialReference,
    INT64_MAX,
    INT64_MIN,
    LegalCompleteness,
    LocalBuildingFrame,
    ParkingComplianceReport,
    ParkingProvision,
    PermitDrawingFloor,
    PermitDrawingModel,
    PhaseTimings,
    RainWaterHarvestingOverlay,
    ReadabilityDiagnostics,
    ReadabilityStatus,
    RoomGeometry,
    SchemaDescriptor,
    SelectionAuditMetadata,
    SetbackComplianceReport,
    SetbackDimensions,
    SewageLayoutOverlay,
    SitePlan,
    SuppressedAnnotation,
    TransformOverflowError,
    WallSegment,
    WindowGeometry,
    WorkingDrawingFloor,
    WorkingDrawingModel,
    compute_element_identity,
    compute_schema_descriptor_digest,
    sha256_hex,
)


# ============================================================
# Test fixtures
# ============================================================

def make_identity(hash_a: str = "abc12345", hash_b: str = "def67890") -> ElementIdentity:
    return ElementIdentity(
        identity_generation=C16_IDENTITY_GENERATION,
        semantic_identity_hash=hash_a,
        presentation_identity_hash=hash_b,
    )


def make_floor_geometry(level: int = 0, semantic_id: str = "abc12345") -> FloorGeometry:
    return FloorGeometry(
        floor_level=level,
        floor_elevation_mm=level * 3000,
        identity=make_identity(hash_a=semantic_id, hash_b="def67890"),
    )


def make_working_model(refs: tuple[str, ...]) -> WorkingDrawingModel:
    return WorkingDrawingModel(
        floor_plans=tuple(WorkingDrawingFloor(geometry_ref=r) for r in refs),
    )


def make_permit_model(refs: tuple[str, ...]) -> PermitDrawingModel:
    site = SitePlan(
        identity=make_identity("11111111", "22222222"),
        plot_x_mm=0,
        plot_y_mm=0,
        plot_width_mm=12000,
        plot_depth_mm=18000,
        building_footprint_xywh=(2000, 3000, 8000, 12000),
    )
    return PermitDrawingModel(
        site_plan=site,
        floor_plans=tuple(PermitDrawingFloor(geometry_ref=r) for r in refs),
    )


def make_cache_keys() -> C16CacheKeys:
    return C16CacheKeys(
        upstream_cache_key=sha256_hex("u"),
        drawing_cache_key=sha256_hex("d"),
        full_cache_key=sha256_hex("f"),
    )


def make_geospatial() -> GeospatialReference:
    return GeospatialReference(
        local_origin_in_plot_mm=(0, 0),
        rotation_from_plot_north_deg=0.0,
        plot_north_arrow_orientation_deg=0.0,
        orientation_basis="longest_wall",
    )


def make_audit_metadata() -> SelectionAuditMetadata:
    return SelectionAuditMetadata(selection_timestamp_utc="2026-05-15T00:00:00Z")


def make_valid_bundle(
    geometry_ids: tuple[str, ...] = ("11111111",),
) -> DualDrawingBundle:
    return DualDrawingBundle(
        source_selection_signature=sha256_hex("sel"),
        selection_audit_metadata=make_audit_metadata(),
        c16_version="v0.5.LOCKED",
        c16_drawing_schema_version=12,
        jurisdiction_profile_id="tn_cdbr_2019",
        declared_domain_scope="residential_v1",
        floor_geometries=tuple(
            make_floor_geometry(level=i, semantic_id=sid)
            for i, sid in enumerate(geometry_ids)
        ),
        local_building_frame=LocalBuildingFrame(),
        geospatial_reference=make_geospatial(),
        working_drawing_model=make_working_model(geometry_ids),
        permit_drawing_model=make_permit_model(geometry_ids),
        upstream_advisory_flags=(),
        cache_keys=make_cache_keys(),
        canonical_replay_signature=sha256_hex("crs"),
        presentation_signature=sha256_hex("ps"),
        schema_descriptor_digest=sha256_hex("sdd"),
    )


# ============================================================
# § 1 — CanonicalTransform2D + R28d
# ============================================================

class TestCanonicalTransform2D:
    def test_minimal_valid(self):
        t = CanonicalTransform2D(
            a00_micro=1_000_000, a01_micro=0, a02_mm=0,
            a10_micro=0, a11_micro=1_000_000, a12_mm=0,
        )
        assert t.a00_micro == 1_000_000

    def test_int64_max_accepted(self):
        t = CanonicalTransform2D(
            a00_micro=INT64_MAX, a01_micro=0, a02_mm=0,
            a10_micro=0, a11_micro=0, a12_mm=0,
        )
        assert t.a00_micro == INT64_MAX

    def test_int64_min_accepted(self):
        t = CanonicalTransform2D(
            a00_micro=INT64_MIN, a01_micro=0, a02_mm=0,
            a10_micro=0, a11_micro=0, a12_mm=0,
        )
        assert t.a00_micro == INT64_MIN

    def test_overflow_above_int64_max_rejected(self):
        with pytest.raises(TransformOverflowError) as excinfo:
            CanonicalTransform2D(
                a00_micro=INT64_MAX + 1, a01_micro=0, a02_mm=0,
                a10_micro=0, a11_micro=0, a12_mm=0,
            )
        assert excinfo.value.invariant_id == "R28d"

    def test_overflow_below_int64_min_rejected(self):
        with pytest.raises(TransformOverflowError):
            CanonicalTransform2D(
                a00_micro=0, a01_micro=0, a02_mm=0,
                a10_micro=0, a11_micro=0, a12_mm=INT64_MIN - 1,
            )

    def test_float_value_rejected(self):
        with pytest.raises(C16ConfigurationError):
            CanonicalTransform2D(
                a00_micro=1.0,  # type: ignore[arg-type]
                a01_micro=0, a02_mm=0,
                a10_micro=0, a11_micro=0, a12_mm=0,
            )

    def test_bool_value_rejected(self):
        # bool is subclass of int but we explicitly reject it (transforms
        # need actual ints, not 0/1 booleans).
        with pytest.raises(C16ConfigurationError):
            CanonicalTransform2D(
                a00_micro=True,  # type: ignore[arg-type]
                a01_micro=0, a02_mm=0,
                a10_micro=0, a11_micro=0, a12_mm=0,
            )


# ============================================================
# § 2 — ElementIdentity validation
# ============================================================

class TestElementIdentity:
    def test_valid_construction(self):
        e = ElementIdentity(
            identity_generation=1,
            semantic_identity_hash="abcd1234",
            presentation_identity_hash="0000ffff",
        )
        assert e.identity_generation == 1

    def test_generation_zero_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ElementIdentity(
                identity_generation=0,
                semantic_identity_hash="abcd1234",
                presentation_identity_hash="0000ffff",
            )

    def test_short_hash_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ElementIdentity(
                identity_generation=1,
                semantic_identity_hash="abc",  # < 8 chars
                presentation_identity_hash="0000ffff",
            )

    def test_uppercase_hash_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ElementIdentity(
                identity_generation=1,
                semantic_identity_hash="ABCD1234",
                presentation_identity_hash="0000ffff",
            )

    def test_non_hex_chars_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ElementIdentity(
                identity_generation=1,
                semantic_identity_hash="ghijklmn",  # 'g'-'n' not hex
                presentation_identity_hash="0000ffff",
            )


class TestComputeElementIdentity:
    def test_returns_element_identity(self):
        e = compute_element_identity(
            element_kind=ElementKind.WALL_EXTERNAL,
            floor_level=0,
            geometry_defining_payload={"start": [0, 0], "end": [5000, 0]},
            full_payload={"start": [0, 0], "end": [5000, 0], "annotations": []},
        )
        assert e.identity_generation == C16_IDENTITY_GENERATION
        assert len(e.semantic_identity_hash) == 8
        assert len(e.presentation_identity_hash) == 8

    def test_same_geometry_same_semantic_hash(self):
        a = compute_element_identity(
            element_kind=ElementKind.WALL_EXTERNAL,
            floor_level=0,
            geometry_defining_payload={"len_mm": 5000},
            full_payload={"len_mm": 5000, "annotations": []},
        )
        b = compute_element_identity(
            element_kind=ElementKind.WALL_EXTERNAL,
            floor_level=0,
            geometry_defining_payload={"len_mm": 5000},
            full_payload={"len_mm": 5000, "annotations": [{"text": "hi"}]},
        )
        # Per v0.3 A3: semantic stable across annotation changes
        assert a.semantic_identity_hash == b.semantic_identity_hash
        # But presentation differs
        assert a.presentation_identity_hash != b.presentation_identity_hash


# ============================================================
# § 3 — FloorGeometry
# ============================================================

class TestFloorGeometry:
    def test_geometry_ref_property(self):
        fg = make_floor_geometry(level=2, semantic_id="aabbccdd")
        assert fg.geometry_ref == "aabbccdd"
        assert fg.floor_level == 2
        assert fg.floor_elevation_mm == 6000


# ============================================================
# § 4 — DualDrawingBundle invariants (R20, R24, R33b)
# ============================================================

class TestBundleR24cUniqueness:
    def test_single_floor_bundle_valid(self):
        b = make_valid_bundle(geometry_ids=("11111111",))
        assert len(b.floor_geometries) == 1

    def test_duplicate_geometry_id_rejected(self):
        # Two FloorGeometry with same semantic hash → R24c violation
        same_id = "abcd1234"
        fg0 = make_floor_geometry(level=0, semantic_id=same_id)
        fg1 = FloorGeometry(
            floor_level=1,
            floor_elevation_mm=3000,
            identity=make_identity(hash_a=same_id, hash_b="00000000"),
        )
        with pytest.raises(GeometryInconsistencyError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg0, fg1),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model((same_id,)),
                permit_drawing_model=make_permit_model((same_id,)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        assert excinfo.value.invariant_id == "R24c"


class TestBundleR24aReferenceResolution:
    def test_unresolved_working_ref_rejected(self):
        fg = make_floor_geometry(level=0, semantic_id="aaaaaaaa")
        with pytest.raises(GeometryInconsistencyError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg,),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("nonexistent",)),
                permit_drawing_model=make_permit_model(("aaaaaaaa",)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        assert excinfo.value.invariant_id == "R24a"

    def test_unresolved_permit_ref_rejected(self):
        fg = make_floor_geometry(level=0, semantic_id="aaaaaaaa")
        with pytest.raises(GeometryInconsistencyError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg,),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("aaaaaaaa",)),
                permit_drawing_model=make_permit_model(("nonexistent",)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        assert excinfo.value.invariant_id == "R24a"


class TestBundleR24bOrphanGeometry:
    def test_orphan_in_working_rejected(self):
        # Two floors but only one referenced in working
        fg0 = make_floor_geometry(level=0, semantic_id="aaaaaaaa")
        fg1 = make_floor_geometry(level=1, semantic_id="bbbbbbbb")
        with pytest.raises(GeometryInconsistencyError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg0, fg1),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("aaaaaaaa",)),  # only floor 0
                permit_drawing_model=make_permit_model(("aaaaaaaa", "bbbbbbbb")),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        # Could fire as R24b (orphan) or R20 (parity); both indicate the bug.
        assert excinfo.value.invariant_id in {"R20", "R24b"}


class TestBundleR20GeometryParity:
    def test_working_permit_ref_mismatch_rejected(self):
        # working refs ≠ permit refs (different set)
        fg0 = make_floor_geometry(level=0, semantic_id="aaaaaaaa")
        fg1 = make_floor_geometry(level=1, semantic_id="bbbbbbbb")
        with pytest.raises(GeometryInconsistencyError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg0, fg1),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("aaaaaaaa",)),
                permit_drawing_model=make_permit_model(("bbbbbbbb",)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        # The mismatch can surface as R24b (orphan) or R20 (parity).
        assert excinfo.value.invariant_id in {"R20", "R24b"}


class TestBundleR33bMixedGeneration:
    def test_mixed_generation_rejected(self):
        # If two FloorGeometry have different identity_generation, reject
        fg0 = make_floor_geometry(level=0, semantic_id="aaaaaaaa")
        # Build a FloorGeometry with a different generation
        fg1 = FloorGeometry(
            floor_level=1,
            floor_elevation_mm=3000,
            identity=ElementIdentity(
                identity_generation=2,   # different!
                semantic_identity_hash="bbbbbbbb",
                presentation_identity_hash="ccccdddd",
            ),
        )
        with pytest.raises(C16ConfigurationError) as excinfo:
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(fg0, fg1),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("aaaaaaaa", "bbbbbbbb")),
                permit_drawing_model=make_permit_model(("aaaaaaaa", "bbbbbbbb")),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )
        assert "R33b" in str(excinfo.value)


class TestBundleValidConstruction:
    def test_valid_single_floor_constructs(self):
        b = make_valid_bundle()
        assert b.c16_drawing_schema_version == 12
        assert b.declared_domain_scope == "residential_v1"

    def test_valid_two_floor_constructs(self):
        b = make_valid_bundle(geometry_ids=("11111111", "22222222"))
        assert len(b.floor_geometries) == 2

    def test_short_canonical_signature_rejected(self):
        with pytest.raises(C16ConfigurationError):
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=12,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(make_floor_geometry(),),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("abc12345",)),
                permit_drawing_model=make_permit_model(("abc12345",)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature="short_sig",   # bad
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )

    def test_zero_schema_version_rejected(self):
        with pytest.raises(C16ConfigurationError):
            DualDrawingBundle(
                source_selection_signature=sha256_hex("s"),
                selection_audit_metadata=make_audit_metadata(),
                c16_version="v0.5",
                c16_drawing_schema_version=0,
                jurisdiction_profile_id="tn_cdbr_2019",
                declared_domain_scope="residential_v1",
                floor_geometries=(make_floor_geometry(),),
                local_building_frame=LocalBuildingFrame(),
                geospatial_reference=make_geospatial(),
                working_drawing_model=make_working_model(("abc12345",)),
                permit_drawing_model=make_permit_model(("abc12345",)),
                upstream_advisory_flags=(),
                cache_keys=make_cache_keys(),
                canonical_replay_signature=sha256_hex("c"),
                presentation_signature=sha256_hex("p"),
                schema_descriptor_digest=sha256_hex("s"),
            )


# ============================================================
# § 5 — PermitDrawingModel R21 / R30 legal_completeness
# ============================================================

class TestPermitDrawingModelLegalCompleteness:
    def _site(self) -> SitePlan:
        return SitePlan(
            identity=make_identity("11111111", "22222222"),
            plot_x_mm=0,
            plot_y_mm=0,
            plot_width_mm=12000,
            plot_depth_mm=18000,
            building_footprint_xywh=(2000, 3000, 8000, 12000),
        )

    def test_default_is_unsafe_for_submission(self):
        # Per v0.4 A5 — default legal_completeness is UNSAFE_FOR_SUBMISSION
        # when constructed minimally (no overlays)
        m = PermitDrawingModel(
            site_plan=self._site(),
            floor_plans=(PermitDrawingFloor(geometry_ref="aaaaaaaa"),),
        )
        assert m.legal_completeness == LegalCompleteness.UNSAFE_FOR_SUBMISSION
        assert m.requires_professional_signature is True

    def test_legally_complete_without_all_overlays_rejected(self):
        # R21 — claiming LEGALLY_COMPLETE without all 5 permit-critical overlays
        with pytest.raises(C16ConfigurationError) as excinfo:
            PermitDrawingModel(
                site_plan=self._site(),
                floor_plans=(PermitDrawingFloor(geometry_ref="aaaaaaaa"),),
                legal_completeness=LegalCompleteness.LEGALLY_COMPLETE,
            )
        assert "R21" in str(excinfo.value)

    def test_legally_incomplete_requires_missing_overlay_list(self):
        with pytest.raises(C16ConfigurationError) as excinfo:
            PermitDrawingModel(
                site_plan=self._site(),
                floor_plans=(PermitDrawingFloor(geometry_ref="aaaaaaaa"),),
                legal_completeness=LegalCompleteness.LEGALLY_INCOMPLETE,
                missing_overlays=(),  # but says incomplete
            )
        assert "R21" in str(excinfo.value)

    def test_legally_incomplete_with_missing_overlays_accepted(self):
        m = PermitDrawingModel(
            site_plan=self._site(),
            floor_plans=(PermitDrawingFloor(geometry_ref="aaaaaaaa"),),
            legal_completeness=LegalCompleteness.LEGALLY_INCOMPLETE,
            missing_overlays=("rain_water_harvesting", "sewage_layout"),
        )
        assert m.legal_completeness == LegalCompleteness.LEGALLY_INCOMPLETE

    def test_north_arrow_out_of_range_rejected(self):
        with pytest.raises(C16ConfigurationError):
            PermitDrawingModel(
                site_plan=self._site(),
                floor_plans=(PermitDrawingFloor(geometry_ref="aaaaaaaa"),),
                north_arrow_orientation_deg=360.0,
            )


# ============================================================
# § 6 — ComplianceAttestation R15 provenance
# ============================================================

class TestComplianceAttestationProvenance:
    def _good_attest(self, **overrides) -> AttestedValue:
        return AttestedValue(
            value=1500.0,
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source="c4_plot_analysis:plot_area_sqm",
        )

    def test_empty_provenance_rejected(self):
        with pytest.raises(ComplianceProvenanceError) as excinfo:
            ComplianceAttestation(
                plot_area_sqm=self._good_attest(),
                built_up_area_sqm=self._good_attest(),
                plot_coverage_pct=AttestedValue(
                    value=15.0,
                    authority=AuthorityKind.LOCALLY_DERIVED,
                    derivation_note="ratio",
                ),
                far_used=self._good_attest(),
                far_permitted=self._good_attest(),
                building_height_m=self._good_attest(),
                height_limit_m=self._good_attest(),
                floors_count=AttestedValue(
                    value=2, authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                    upstream_source="c12:floors",
                ),
                setback_compliance=SetbackComplianceReport(
                    setback_dimensions=SetbackDimensions(),
                    all_compliant=True,
                ),
                parking_compliance=ParkingComplianceReport(compliant=True),
                rwh_present=AttestedValue(
                    value=True, authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                    upstream_source="c2:rwh_present",
                ),
                sewage_treatment_present=AttestedValue(
                    value=True, authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
                    upstream_source="c2:sewage",
                ),
                upstream_check_provenance=(),   # EMPTY — should be rejected
            )
        assert excinfo.value.invariant_id == "R15"


# ============================================================
# § 7 — Observability (excluded from cache by design)
# ============================================================

class TestPhaseTimings:
    def test_minimal_valid(self):
        t = PhaseTimings(
            alpha_envelope_assembly_ms=10,
            beta_scheduling_ms=20,
            gamma_working_assembly_ms=30,
            delta_permit_assembly_ms=40,
            epsilon_attestation_packaging_ms=15,
            zeta_bundle_assembly_ms=5,
            total_ms=120,
        )
        assert t.total_ms == 120

    def test_negative_timing_rejected(self):
        with pytest.raises(C16ConfigurationError):
            PhaseTimings(
                alpha_envelope_assembly_ms=-1,
                beta_scheduling_ms=0,
                gamma_working_assembly_ms=0,
                delta_permit_assembly_ms=0,
                epsilon_attestation_packaging_ms=0,
                zeta_bundle_assembly_ms=0,
                total_ms=0,
            )


class TestReadabilityDiagnostics:
    def test_minimal_valid(self):
        d = ReadabilityDiagnostics(
            collision_count=0,
            suppressed_annotations=(),
            viewport_congestion_score=0.0,
            readability_degraded=False,
        )
        assert d.collision_count == 0

    def test_with_suppressed_annotations(self):
        sa = SuppressedAnnotation(
            annotation_id="a1",
            conflicting_annotation_id="a2",
            precedence_rule_fired="decorative_suppressed_first",
        )
        d = ReadabilityDiagnostics(
            collision_count=1,
            suppressed_annotations=(sa,),
            viewport_congestion_score=0.3,
            readability_degraded=False,
        )
        assert len(d.suppressed_annotations) == 1

    def test_congestion_score_out_of_range_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ReadabilityDiagnostics(
                collision_count=0,
                suppressed_annotations=(),
                viewport_congestion_score=1.5,  # > 1.0
                readability_degraded=False,
            )

    def test_negative_collision_count_rejected(self):
        with pytest.raises(C16ConfigurationError):
            ReadabilityDiagnostics(
                collision_count=-1,
                suppressed_annotations=(),
                viewport_congestion_score=0.0,
                readability_degraded=False,
            )


# ============================================================
# § 8 — SchemaDescriptor + digest (v0.5 A2 / R26b)
# ============================================================

class TestSchemaDescriptor:
    def test_construction(self):
        d = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        assert d.c16_drawing_schema_version == 12

    def test_digest_is_64_hex(self):
        d = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        digest = compute_schema_descriptor_digest(d)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_digest_deterministic(self):
        d1 = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        d2 = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        assert compute_schema_descriptor_digest(d1) == compute_schema_descriptor_digest(d2)

    def test_different_descriptor_different_digest(self):
        d1 = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="residential_v1",
        )
        d2 = SchemaDescriptor(
            c16_version="v0.5.LOCKED",
            c16_drawing_schema_version=12,
            c16_identity_generation=1,
            jurisdiction_id="tn_cdbr_2019",
            declared_domain_scope="small_commercial_v1",  # different
        )
        assert compute_schema_descriptor_digest(d1) != compute_schema_descriptor_digest(d2)


# ============================================================
# § 9 — AdvisoryFlag passthrough surface
# ============================================================

class TestAdvisoryFlag:
    def test_construction(self):
        f = AdvisoryFlag(
            source_component="c14_circulation",
            flag_id="ELBOW_NARROWING",
            message="Corridor narrows abruptly at staircase exit.",
        )
        assert f.source_component == "c14_circulation"
