"""
C16 Phase δ — Permit drawing assembly
========================================

Per v0.5 LOCKED spec § 3 Phase δ.

INPUT:
    - EnvelopeAssembly (Phase α)
    - UpstreamInputBundle (for jurisdiction overlays + plot dimensions)
    - JurisdictionProfile
    - RenderingConfig

PROCESSING:
    1. Build PermitDrawingFloor per FloorGeometry:
       - geometry_ref linking to FloorGeometry.identity.semantic_identity_hash
       - setback_annotations (4 sides)
       - compliance_markers (north arrow, RWH symbol, parking grid, etc.)
    2. Build SitePlan (the plot outline + building footprint + setbacks)
    3. Build KeyPlan (multi-floor reference)
    4. Build Elevations (4 cardinal facades)
    5. Build the 5 permit-critical overlays per TNCDBR:
       - RainWaterHarvestingOverlay (rule 9(a))
       - SewageLayoutOverlay        (rule 9(b))
       - SetbackDimensions (already in compliance attestation)
       - FAR + coverage attestation (Phase ε)
       - ParkingProvision (rule on bays)
    6. Set legal_completeness based on which overlays were emitted

OUTPUT:
    PermitDrawingModel.

R-INVARIANTS:
    R7c — canonical ordering of permit floor plans
    R21 — legal_completeness gating against the 5 permit-critical overlays
    R30 — legal_completeness ⊥ readability_status (this phase only sets
          legal_completeness; readability_status defaults to READABLE
          and is set by Phase ζ from ReadabilityDiagnostics)

Note: this phase does NOT fill ComplianceAttestation values — that's
Phase ε's job. Phase δ produces the *structure* (markers, overlays);
Phase ε produces the *attestation* (with AttestedValue trails).
"""
from __future__ import annotations

from buildemup.components.c16.config import RenderingConfig
from buildemup.components.c16.contracts import (
    ElementKind,
    JurisdictionProfile,
    LegalCompleteness,
    ReadabilityStatus,
)
from buildemup.components.c16.schema import (
    ComplianceMarker,
    Elevation,
    KeyPlan,
    PermitDrawingFloor,
    PermitDrawingModel,
    RainWaterHarvestingOverlay,
    SetbackAnnotation,
    SewageLayoutOverlay,
    ParkingProvision,
    ParkingComplianceReport,
    SectionView,
    SetbackComplianceReport,
    SetbackDimensions,
    SignaturePlaceholder,
    SitePlan,
    compute_element_identity,
)
from buildemup.components.c16.phases.alpha_envelope import EnvelopeAssembly
from buildemup.components.c16.phases.gamma_working import _compute_section_view
from buildemup.components.c16.upstream_adapter import (
    UpstreamInputBundle,
    m_to_mm,
)


# TNCDBR residential setback defaults (rough, jurisdiction-overridable
# at the JurisdictionProfile layer in production).
_TNCDBR_DEFAULT_FRONT_MM = 1500    # 1.5 m
_TNCDBR_DEFAULT_REAR_MM  = 1200    # 1.2 m
_TNCDBR_DEFAULT_SIDE_MM  =  900    # 0.9 m


def _build_setback_annotations(
    site_plan: SitePlan,
) -> tuple[SetbackAnnotation, ...]:
    """One annotation per side from plot edge to building footprint."""
    bx, by, bw, bd = site_plan.building_footprint_xywh
    front_mm = by                              # plot SW → building S edge
    rear_mm  = site_plan.plot_depth_mm - (by + bd)
    left_mm  = bx
    right_mm = site_plan.plot_width_mm - (bx + bw)
    return (
        SetbackAnnotation(
            annotation_id="setback:front",
            side="front",
            value_mm=max(0, front_mm),
            anchor_x_mm=bx + bw // 2,
            anchor_y_mm=by // 2,
        ),
        SetbackAnnotation(
            annotation_id="setback:rear",
            side="rear",
            value_mm=max(0, rear_mm),
            anchor_x_mm=bx + bw // 2,
            anchor_y_mm=site_plan.plot_depth_mm - max(0, rear_mm) // 2,
        ),
        SetbackAnnotation(
            annotation_id="setback:left",
            side="left",
            value_mm=max(0, left_mm),
            anchor_x_mm=left_mm // 2,
            anchor_y_mm=by + bd // 2,
        ),
        SetbackAnnotation(
            annotation_id="setback:right",
            side="right",
            value_mm=max(0, right_mm),
            anchor_x_mm=site_plan.plot_width_mm - max(0, right_mm) // 2,
            anchor_y_mm=by + bd // 2,
        ),
    )


def _build_site_plan(
    *,
    envelope:        EnvelopeAssembly,
    upstream_inputs: UpstreamInputBundle,
) -> SitePlan:
    """Site plan: plot outline + building footprint from ground floor."""
    plot_analysis = upstream_inputs.plot_analysis
    # Default plot dims if upstream not present
    plot_w_mm = 12_000
    plot_d_mm = 18_000
    if plot_analysis is not None:
        # PlotAnalysis carries area_sqm + aspect_ratio; we derive dims.
        area_sqm = float(getattr(plot_analysis, "area_sqm", 216.0))
        aspect = float(getattr(plot_analysis, "aspect_ratio", 1.5))
        # depth/width = aspect; w*d = area*1e6 mm² (converted from sqm)
        # → w² * aspect = area*1e6 → w = sqrt(area*1e6 / aspect)
        import math
        w_m = math.sqrt(area_sqm / aspect) if aspect > 0 else math.sqrt(area_sqm)
        d_m = w_m * aspect
        plot_w_mm = m_to_mm(w_m)
        plot_d_mm = m_to_mm(d_m)

    # Building footprint = ground floor bbox
    if envelope.floor_geometries:
        ground = envelope.floor_geometries[0]
        if ground.rooms:
            min_x = min(r.x_mm for r in ground.rooms)
            min_y = min(r.y_mm for r in ground.rooms)
            max_x = max(r.x_mm + r.width_mm for r in ground.rooms)
            max_y = max(r.y_mm + r.depth_mm for r in ground.rooms)
            bw = max_x - min_x
            bd = max_y - min_y
        else:
            bw = bd = 0
    else:
        bw = bd = 0
    # Place building per default front/rear/side setbacks
    bx = _TNCDBR_DEFAULT_SIDE_MM
    by = _TNCDBR_DEFAULT_FRONT_MM
    geometry_payload = {
        "plot_x_mm":   0,
        "plot_y_mm":   0,
        "plot_width_mm": plot_w_mm,
        "plot_depth_mm": plot_d_mm,
        "building_footprint_xywh": [bx, by, bw, bd],
    }
    identity = compute_element_identity(
        element_kind=ElementKind.SLAB_FLOOR,
        floor_level=-1,    # site plan is "below" floor 0
        geometry_defining_payload=geometry_payload,
        full_payload=geometry_payload,
    )
    return SitePlan(
        identity=identity,
        plot_x_mm=0,
        plot_y_mm=0,
        plot_width_mm=plot_w_mm,
        plot_depth_mm=plot_d_mm,
        building_footprint_xywh=(bx, by, bw, bd),
    )


def _build_elevations(
    envelope: EnvelopeAssembly,
) -> tuple[Elevation, ...]:
    """4 cardinal elevations (N/S/E/W) from envelope bbox."""
    if not envelope.floor_geometries:
        return ()
    # Total height
    floors = envelope.floor_geometries
    top_y = max(fg.floor_elevation_mm for fg in floors)
    typical_floor_height_mm = 3000
    total_height_mm = top_y + typical_floor_height_mm
    # Width and depth from ground bbox
    g = floors[0]
    if not g.rooms:
        return ()
    bw = max(r.x_mm + r.width_mm for r in g.rooms) - min(r.x_mm for r in g.rooms)
    bd = max(r.y_mm + r.depth_mm for r in g.rooms) - min(r.y_mm for r in g.rooms)

    elevs: list[Elevation] = []
    for facade in ("north", "south", "east", "west"):
        width_mm = bw if facade in ("north", "south") else bd
        geometry_payload = {
            "facade_axis": facade,
            "width_mm":    width_mm,
            "height_mm":   total_height_mm,
        }
        identity = compute_element_identity(
            element_kind=ElementKind.WALL_EXTERNAL,
            floor_level=0,
            geometry_defining_payload=geometry_payload,
            full_payload=geometry_payload,
        )
        elevs.append(Elevation(
            identity=identity,
            elevation_id=f"elev:{facade}",
            facade_axis=facade,
            width_mm=width_mm,
            height_mm=total_height_mm,
        ))
    return tuple(elevs)


def _build_key_plan(
    *,
    envelope:  EnvelopeAssembly,
    site_plan: SitePlan,
) -> KeyPlan:
    geometry_payload = {
        "floor_count":     len(envelope.floor_geometries),
        "site_outline_mm": [
            site_plan.plot_x_mm,
            site_plan.plot_y_mm,
            site_plan.plot_width_mm,
            site_plan.plot_depth_mm,
        ],
    }
    identity = compute_element_identity(
        element_kind=ElementKind.SLAB_FLOOR,
        floor_level=-1,
        geometry_defining_payload=geometry_payload,
        full_payload=geometry_payload,
    )
    return KeyPlan(
        identity=identity,
        floor_count=len(envelope.floor_geometries),
        site_outline_mm=(
            site_plan.plot_x_mm,
            site_plan.plot_y_mm,
            site_plan.plot_width_mm,
            site_plan.plot_depth_mm,
        ),
    )


def execute_phase_delta(
    *,
    envelope:             EnvelopeAssembly,
    upstream_inputs:      UpstreamInputBundle,
    jurisdiction_profile: JurisdictionProfile,
    config:               RenderingConfig,
) -> PermitDrawingModel:
    """Phase δ main entry point."""

    site_plan = _build_site_plan(
        envelope=envelope,
        upstream_inputs=upstream_inputs,
    )
    setback_annotations = _build_setback_annotations(site_plan)

    # Per-floor permit floor plans
    floor_plans = tuple(
        PermitDrawingFloor(
            geometry_ref=fg.geometry_ref,
            setback_annotations=setback_annotations,
            compliance_markers=(
                ComplianceMarker(
                    marker_id=f"north_arrow:{fg.floor_level}",
                    marker_kind="north_arrow",
                    anchor_x_mm=site_plan.plot_width_mm - 1000,
                    anchor_y_mm=site_plan.plot_depth_mm - 1000,
                ),
            ),
        )
        for fg in envelope.floor_geometries
    )

    # Elevations + key plan
    elevations = _build_elevations(envelope)
    key_plan = _build_key_plan(envelope=envelope, site_plan=site_plan)

    # Permit section views — same R23 set as working but separately
    # generated so each model is self-contained.
    section_views: list[SectionView] = []
    for cut_type in ("entry", "staircase", "wet_zone"):
        if cut_type not in config.mandatory_section_cuts:
            continue
        sv = _compute_section_view(
            cut_type=cut_type,
            floor_geometries=envelope.floor_geometries,
        )
        if sv is not None:
            section_views.append(sv)

    # 5 permit-critical overlays (all 5 emitted by default; jurisdiction
    # may opt out via brief at production time).
    rwh = RainWaterHarvestingOverlay(
        overlay_id="rwh:default",
        pit_count=1,
        pit_location_xy_mm=(
            site_plan.plot_width_mm - 1500,
            site_plan.plot_depth_mm - 1500,
        ),
    )
    sewage = SewageLayoutOverlay(
        overlay_id="sewage:default",
        septic_tank_location_xy_mm=(
            site_plan.plot_width_mm - 2500,
            1000,
        ),
        sewage_treatment_capacity_l=1500,
    )
    parking = ParkingProvision(
        provided_count=1,    # default 1 bay; production reads from brief
        required_count=1,
        bay_size_mm=(2500, 5000),
    )

    # north_arrow_orientation_deg from envelope's geospatial_reference
    north_arrow = envelope.geospatial_reference.plot_north_arrow_orientation_deg

    # Per R30a: legal_completeness derives ONLY from
    # UPSTREAM_AUTHORITATIVE overlay presence. Phase δ produces the
    # structural overlays; the AUTHORITATIVENESS gating happens in
    # Phase ε. Here we provisionally mark LEGALLY_INCOMPLETE; Phase ε
    # may upgrade to LEGALLY_COMPLETE once the attestation is packaged.
    # (Note: PermitDrawingModel's __post_init__ requires
    # missing_overlays non-empty when LEGALLY_INCOMPLETE; we name the
    # missing pieces as compliance_attestation, which Phase ε fills.)

    return PermitDrawingModel(
        site_plan=site_plan,
        floor_plans=floor_plans,
        elevations=elevations,
        section_views=tuple(section_views),
        key_plan=key_plan,
        compliance_attestation=None,    # Phase ε fills this
        rwh_overlay=rwh,
        sewage_layout=sewage,
        parking_provision=parking,
        north_arrow_orientation_deg=(
            north_arrow if 0.0 <= north_arrow < 360.0 else 0.0
        ),
        recommended_scale=config.permit_drawing_scale,
        legal_completeness=LegalCompleteness.LEGALLY_INCOMPLETE,
        readability_status=ReadabilityStatus.READABLE,
        requires_professional_signature=True,
        missing_overlays=("far_and_coverage_attestation",),
        signature_placeholder=SignaturePlaceholder(
            placeholder_id="architect_signature_block",
        ),
    )
