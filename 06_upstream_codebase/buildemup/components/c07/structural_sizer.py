"""
BuildemUp† — Component 7b: Structural Sizer (v0.3)
====================================================

Upgraded structural sizer. Adds over v0.2:
  - Zone IV support (was refused; now supported with IS 13920)
  - Strong-column-weak-beam check (IS 13920 cl. 7.2.1)
  - Minimum column dim for seismic (IS 13920 cl. 7.1.2)
  - Stirrup spacing rules (IS 13920 cl. 7.4.3)
  - Slenderness ratio check (IS 456 cl. 25.1.2)
  - Wind load calculation (IS 875 Part 3)
  - Seismic reliability indicator (LOW/MEDIUM/HIGH)
  - Plan regularity check integration

Zone support:
  - Zone II:  basic IS 456 + optional checks
  - Zone III: IS 13920 enforced, SCWB check, stirrup spacing rules
  - Zone IV:  IS 13920 enforced, larger columns, higher steel %
  - Zone V:   still refused — requires detailed expert design

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from buildemup.kb.rcc_design_rules import (
    select_column_spec,
    calculate_beam_depth_mm,
    calculate_slab_thickness_mm,
    select_concrete_grade,
    estimate_concrete_volume_cum,
    estimate_steel_tonnes,
    ColumnSpec,
)
from buildemup.kb.load_estimation import (
    FloorType,
    calculate_column_axial_load_kn,
    SAFETY_FACTORS,
)
from buildemup.kb.seismic_detailing import (
    is13920_required,
    check_scwb_heuristic,
    check_slenderness,
    column_stirrup_spacing,
    beam_stirrup_spacing,
    check_plan_regularity,
    SEISMIC_MIN_COLUMN_DIM_MM,
    RECOMMENDED_COLUMN_STEEL_PCT,
    IrregularityCheck,
    StirrupSpacing,
    REGULARITY_REGULAR,
    REGULARITY_MODERATE,
    REGULARITY_SEVERE,
)
from buildemup.kb.wind_load import (
    calculate_wind_load,
    WindLoadResult,
    estimate_base_shear_coefficient,
    compare_lateral_loads,
)
from buildemup.components.c07.grid_generator import Grid
from buildemup.utils.errors import SeismicZoneUnsupportedError


@dataclass(frozen=True)
class SizedStructure:
    """Output of structural sizing — all structural dimensions set."""
    column_size_mm: int
    column_steel_pct: float
    column_spec: ColumnSpec
    beam_depth_mm: int
    beam_width_mm: int
    slab_thickness_mm: int
    concrete_grade: str
    max_column_axial_load_kn: float
    max_column_load_unfactored_kn: float
    column_load_breakdown: dict
    total_concrete_cum: float
    total_steel_tonnes: float
    seismic_zone: str
    needs_is13920_detailing: bool

    # v0.4 additions / renames
    scwb_heuristic: dict     # was 'scwb_check' in v0.3 — renamed to flag heuristic nature
    slenderness_check: dict
    column_stirrups: StirrupSpacing | None
    beam_stirrups: dict | None
    wind_load: WindLoadResult | None
    regularity: IrregularityCheck | None
    seismic_reliability: str
    recommended_steel_pct: float
    lateral_load_comparison: dict | None  # v0.4: wind vs seismic governing

    warnings: list[str] = field(default_factory=list)


class StructuralSizer:
    """Sizes structural elements given grid + load stack."""

    SUPPORTED_ZONES = {"II", "III", "IV"}
    REFUSED_ZONES = {"V"}

    def size(
        self,
        grid: Grid,
        floors_above_ground: int,
        has_stilt_parking: bool = False,
        has_terrace_access: bool = True,
        has_water_tank: bool = True,
        seismic_zone: str = "II",
        city: str = "chennai",
        terrain_category: str = "urban",
        re_entrant_corner_x_m: float = 0.0,
        re_entrant_corner_y_m: float = 0.0,
        building_type_spec=None,    # v0.4: Optional BuildingTypeSpec
    ) -> SizedStructure:
        """Size the structure with IS 456 + IS 13920 + IS 875 Part 3 rules.

        v0.4: building_type_spec carries importance factor and typical live
        load per IS 1893 / IS 875 Part 2. If None, defaults to residential.
        """
        # v0.4: derive importance factor + live load from building spec
        # Default for backwards compat: residential (importance 1.0)
        if building_type_spec is not None:
            importance_factor = building_type_spec.importance_factor
            building_typical_ll = building_type_spec.typical_live_load_knsqm
            building_forces_is13920 = building_type_spec.is13920_mandatory_all_zones
        else:
            importance_factor = 1.0
            building_typical_ll = None  # use load_estimation defaults
            building_forces_is13920 = False
        # Gate: refuse Zone V
        if seismic_zone in self.REFUSED_ZONES:
            raise SeismicZoneUnsupportedError(
                technical_message=f"Seismic Zone {seismic_zone}",
                user_message=(
                    f"Seismic Zone {seismic_zone} regions (e.g., Bhuj, NE "
                    f"India) require detailed expert structural design. "
                    f"BuildemUp v1 supports Zones II, III, and IV."
                ),
                suggested_action=(
                    "Contact a licensed structural engineer in your region. "
                    "Typical cost for Zone V design: ₹60-100K for residential."
                ),
            )
        if seismic_zone not in self.SUPPORTED_ZONES:
            raise SeismicZoneUnsupportedError(
                technical_message=f"Unknown seismic zone: {seismic_zone}",
                user_message=f"Zone '{seismic_zone}' not recognised.",
            )

        # Build floor stack
        floor_stack = self._build_floor_stack(
            floors_above_ground, has_stilt_parking, has_terrace_access
        )
        effective_floors = floors_above_ground + (1 if has_stilt_parking else 0)
        col_floor_count = min(effective_floors, 4)

        # Base column sizing per IS 456
        col_spec = select_column_spec(col_floor_count, seismic_zone)

        # v0.4: building type can force IS 13920 even in low zones (educational,
        # healthcare are 'important buildings' per IS 1893)
        effective_is13920 = is13920_required(seismic_zone) or building_forces_is13920

        # IS 13920 minimum override for Zone III+ OR important buildings
        if effective_is13920:
            if col_spec.typical_dim_mm < SEISMIC_MIN_COLUMN_DIM_MM:
                col_spec = ColumnSpec(
                    floors_above_ground=col_spec.floors_above_ground,
                    min_dim_mm=SEISMIC_MIN_COLUMN_DIM_MM,
                    typical_dim_mm=SEISMIC_MIN_COLUMN_DIM_MM,
                    typical_steel_pct=RECOMMENDED_COLUMN_STEEL_PCT.get(
                        seismic_zone, col_spec.typical_steel_pct
                    ),
                    note=f"{col_spec.note} (upgraded to IS 13920 min)",
                    source=f"{col_spec.source} + IS 13920 cl. 7.1.2",
                )

        # Tributary load
        tributary_area = grid.bay_x_m * grid.bay_y_m
        load_result = calculate_column_axial_load_kn(
            tributary_area_sqm=tributary_area,
            floor_stack=floor_stack,
            slab_thickness_mm=125,
            has_water_tank_above=has_water_tank,
            is_water_tank_column=False,
        )

        # Beam, slab
        beam_depth = calculate_beam_depth_mm(grid.max_span_m)
        beam_width = col_spec.typical_dim_mm
        slab_thickness = calculate_slab_thickness_mm(grid.max_span_m, is_two_way=True)
        concrete_grade = select_concrete_grade(col_floor_count, seismic_zone)

        # IS 13920 checks
        scwb = check_scwb_heuristic(
            col_spec.typical_dim_mm, beam_depth, seismic_zone
        )
        floor_height_mm = 3000
        effective_length_mm = int(floor_height_mm * 0.75)
        slender = check_slenderness(effective_length_mm, col_spec.typical_dim_mm)
        col_stirrups = column_stirrup_spacing(
            col_spec.typical_dim_mm, floor_height_mm, seismic_zone
        )
        beam_stirrup = beam_stirrup_spacing(beam_depth, seismic_zone)

        # Regularity + wind
        regularity = check_plan_regularity(
            plan_width_m=grid.envelope_width_m,
            plan_depth_m=grid.envelope_depth_m,
            re_entrant_corner_x_m=re_entrant_corner_x_m,
            re_entrant_corner_y_m=re_entrant_corner_y_m,
            seismic_zone=seismic_zone,
        )
        building_height = (effective_floors + 1) * 3.0
        wind = calculate_wind_load(
            city=city,
            building_height_m=building_height,
            terrain_category=terrain_category,
        )

        # v0.4: explicit wind vs seismic comparison.
        # Building face area for wind = wider_dimension × height.
        # Building weight ~ floor_area × floors × 12 kN/sqm avg.
        building_face_area = max(grid.envelope_width_m, grid.envelope_depth_m) * building_height
        building_weight_kn = (
            grid.envelope_width_m * grid.envelope_depth_m
            * (effective_floors + 1) * 12.0
        )
        base_shear_coef = estimate_base_shear_coefficient(
            seismic_zone, has_is13920=is13920_required(seismic_zone)
        )
        lateral_comparison = compare_lateral_loads(
            wind_pressure_knsqm=wind.design_pressure_knsqm,
            building_face_area_sqm=building_face_area,
            seismic_base_shear_coefficient=base_shear_coef,
            building_weight_kn=building_weight_kn,
        )

        # Quantities (with seismic steel uplift)
        floor_area_sqm = grid.envelope_width_m * grid.envelope_depth_m
        total_concrete = estimate_concrete_volume_cum(floor_area_sqm, col_floor_count)
        total_steel = estimate_steel_tonnes(total_concrete)

        if is13920_required(seismic_zone):
            recommended_steel_pct = RECOMMENDED_COLUMN_STEEL_PCT.get(
                seismic_zone, col_spec.typical_steel_pct
            )
            steel_uplift = {"III": 1.10, "IV": 1.20}.get(seismic_zone, 1.0)
            total_steel = total_steel * steel_uplift
        else:
            recommended_steel_pct = col_spec.typical_steel_pct

        # Reliability
        reliability = self._compute_reliability(
            seismic_zone, scwb, slender, regularity
        )

        # Warnings
        warnings = self._generate_warnings(
            seismic_zone, is13920_required(seismic_zone),
            scwb, slender, col_stirrups, beam_stirrup,
            regularity, wind, has_water_tank, reliability,
        )

        return SizedStructure(
            column_size_mm=col_spec.typical_dim_mm,
            column_steel_pct=recommended_steel_pct,
            column_spec=col_spec,
            beam_depth_mm=beam_depth,
            beam_width_mm=beam_width,
            slab_thickness_mm=slab_thickness,
            concrete_grade=concrete_grade,
            max_column_axial_load_kn=load_result["total_factored_kn"],
            max_column_load_unfactored_kn=load_result["total_unfactored_kn"],
            column_load_breakdown=load_result,
            total_concrete_cum=total_concrete,
            total_steel_tonnes=total_steel,
            seismic_zone=seismic_zone,
            needs_is13920_detailing=is13920_required(seismic_zone),
            scwb_heuristic=scwb,
            slenderness_check=slender,
            column_stirrups=col_stirrups,
            beam_stirrups=beam_stirrup,
            wind_load=wind,
            regularity=regularity,
            seismic_reliability=reliability,
            recommended_steel_pct=recommended_steel_pct,
            lateral_load_comparison=lateral_comparison,
            warnings=warnings,
        )

    @staticmethod
    def _build_floor_stack(
        floors_above_ground: int,
        has_stilt_parking: bool,
        has_terrace_access: bool,
    ) -> list[FloorType]:
        stack = []
        if has_terrace_access:
            stack.append(FloorType.TERRACE_ACCESSIBLE)
        else:
            stack.append(FloorType.TERRACE_INACCESSIBLE)
        for _ in range(floors_above_ground):
            stack.append(FloorType.RESIDENTIAL)
        stack.append(FloorType.RESIDENTIAL)  # GF slab
        if has_stilt_parking:
            stack.append(FloorType.STILT_PARKING)
        return stack

    @staticmethod
    def _compute_reliability(
        seismic_zone: str, scwb: dict, slender: dict,
        regularity: IrregularityCheck,
    ) -> str:
        if seismic_zone == "II":
            return "HIGH" if regularity.is_regular else "MEDIUM"
        # Zone III+
        if not regularity.is_regular:
            return "LOW"
        if scwb.get("applicable") and not scwb.get("check_passed"):
            return "LOW"
        if not slender.get("is_short_column"):
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _generate_warnings(
        seismic_zone: str, needs_is13920: bool,
        scwb: dict, slender: dict,
        col_stirrups, beam_stirrup,
        regularity: IrregularityCheck, wind: WindLoadResult,
        has_water_tank: bool, reliability: str,
    ) -> list[str]:
        warnings: list[str] = []
        if needs_is13920:
            warnings.append(
                f"Zone {seismic_zone}: IS 13920 ductile detailing ENFORCED. "
                f"Column min 300mm, stirrup spacing per code, "
                f"strong-column-weak-beam check applied."
            )
        if scwb.get("applicable") and not scwb.get("check_passed"):
            warnings.append(
                f"SCWB heuristic failed: {scwb['message']} "
                f"NOTE: This is a dimensional heuristic only. Real SCWB "
                f"compliance requires moment capacity calculation by your "
                f"structural engineer."
            )
        if not slender.get("is_short_column"):
            warnings.append(
                f"Column slenderness {slender['slenderness_ratio']} > 12. "
                f"Slender column needs detailed buckling analysis."
            )
        if col_stirrups:
            warnings.append(col_stirrups.notes)
        if beam_stirrup:
            warnings.append(beam_stirrup["notes"])
        for w in regularity.warnings:
            warnings.append(w)
        if regularity.requires_detailed_analysis:
            warnings.append(regularity.recommended_action)
        if wind.basic_wind_speed_ms >= 44:
            for w in wind.warnings:
                warnings.append(w)
        if has_water_tank:
            warnings.append(
                "Terrace water tank (~50 kN) included in load calculation."
            )
        warnings.append(
            "Construction tolerance: columns shift ±20mm during pour. "
            "Ensure walls stay at least 30mm from column edges."
        )
        if reliability == "LOW":
            warnings.append(
                "⚠ SEISMIC RELIABILITY: LOW. Detailed dynamic analysis "
                "STRONGLY recommended before construction."
            )
        elif reliability == "MEDIUM":
            warnings.append(
                "Seismic reliability: MEDIUM. Engineer review advised."
            )
        warnings.append(
            "Preliminary structural sizing using Indian codes. Final "
            "construction drawings require licensed structural engineer "
            "(typical cost ₹20-40K for 1200 sqft)."
        )
        return warnings
