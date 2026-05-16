"""
BuildemUp† — Component 7c: Foundation Engine (v0.3)
=====================================================

Foundation types supported:
  - isolated:  single footing per column
  - combined:  two columns on one footing
  - strap:     edge column with strap beam to interior column
  - raft:      continuous slab
  - pile:      deep foundation (Mumbai reclaimed, Kolkata)

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from buildemup.kb.soil_foundation_rules import (
    SoilProfile,
    get_soil_profile,
    get_area_warning,
    check_water_table_risk,
    calculate_isolated_footing_size,
    estimate_footing_quantities,
)
from buildemup.kb.pile_foundation import (
    select_pile_spec,
    pile_group_size,
    pile_cap_size_m,
    pile_cap_concrete_cum,
    pile_foundation_warnings,
    PileSpec,
)
from buildemup.components.c07.grid_generator import Grid
from buildemup.components.c07.structural_sizer import SizedStructure


@dataclass(frozen=True)
class FoundationDesign:
    type: str
    size_m: tuple[float, float]
    depth_m: float
    concrete_cum_per_footing: float
    steel_kg_per_footing: float
    total_concrete_cum: float
    total_steel_kg: float
    footing_count: int
    soil_profile: SoilProfile
    water_table_risk: dict
    adjacent_footing_risk: bool
    area_specific_warning: str | None
    pile_spec: PileSpec | None = None
    piles_per_column: int = 0
    total_piles: int = 0
    has_edge_columns: bool = False
    strap_beams_count: int = 0
    warnings: list[str] = field(default_factory=list)


class FoundationEngine:
    """Foundation designer with pile + strap support."""

    def design(
        self,
        grid: Grid,
        structure: SizedStructure,
        city: str,
        area: str | None = None,
        is_property_line_edge: bool = False,
    ) -> FoundationDesign:
        soil = get_soil_profile(city, area=area)
        column_load_kn = structure.max_column_axial_load_kn
        max_span_m = grid.max_span_m

        foundation_type = self._select_type(
            column_load_kn, soil, max_span_m, is_property_line_edge
        )

        if foundation_type == "pile":
            return self._design_pile(
                grid, structure, soil, column_load_kn, city, area,
                is_property_line_edge,
            )
        elif foundation_type == "strap":
            return self._design_strap(
                grid, structure, soil, column_load_kn, city, area,
            )
        else:
            return self._design_shallow(
                grid, structure, soil, column_load_kn, city, area,
                foundation_type, is_property_line_edge,
            )

    @staticmethod
    def _select_type(
        column_load_kn: float, soil: SoilProfile,
        column_spacing_m: float, is_property_line_edge: bool,
    ) -> str:
        # Very weak soil (SBC < 6) → pile always
        if soil.safe_bearing_capacity_t_sqm < 6.0:
            return "pile"
        # Weak alluvial (typical Kolkata 5-10 T/sqm) + any G+1+ → pile
        # IS 2911 practice: SBC ≤ 10 T/sqm + >2-floor structure = pile
        if soil.typical_soil == "alluvial_clay" and column_load_kn > 300:
            return "pile"
        # Reclaimed or mixed-fill with high load → pile
        if soil.typical_soil in ("filled_up", "rock_or_filled_up") and column_load_kn > 500:
            return "pile"
        # High load + weak-ish soil → pile
        if column_load_kn > 800 and soil.safe_bearing_capacity_t_sqm < 12.0:
            return "pile"
        # Standard isolated footing size check
        fw, _ = calculate_isolated_footing_size(
            column_load_kn, soil.safe_bearing_capacity_t_sqm
        )
        # Edge-of-property + large footing → strap
        if is_property_line_edge and fw > 1.5:
            return "strap"
        # Very close footings → raft
        if fw > column_spacing_m * 0.6:
            return "raft"
        # Close footings → combined
        if fw > column_spacing_m * 0.45:
            return "combined"
        return "isolated"

    def _design_pile(
        self, grid, structure, soil, column_load_kn,
        city, area, is_property_line_edge,
    ) -> FoundationDesign:
        pile_spec = select_pile_spec(column_load_kn)
        piles_per_col = pile_group_size(column_load_kn, pile_spec.safe_working_load_kn)
        col_count = len(grid.columns)
        total_piles = piles_per_col * col_count

        cap_size = pile_cap_size_m(piles_per_col, pile_spec.diameter_mm)
        cap_concrete = pile_cap_concrete_cum(cap_size, 0.6)
        cap_steel = cap_concrete * 80

        concrete_per_col = pile_spec.concrete_cum_per_pile * piles_per_col + cap_concrete
        steel_per_col = pile_spec.steel_kg_per_pile * piles_per_col + cap_steel

        total_concrete = concrete_per_col * col_count
        total_steel = steel_per_col * col_count

        wt_risk = check_water_table_risk(soil, pile_spec.typical_length_m)
        area_warning = get_area_warning(city, area)

        warnings = [
            f"PILE FOUNDATION: {piles_per_col} pile(s) of {pile_spec.diameter_mm}mm "
            f"diameter × {pile_spec.typical_length_m}m deep per column. "
            f"Total: {total_piles} piles across the building.",
        ]
        warnings.extend(pile_foundation_warnings(city))
        if area_warning:
            warnings.append(f"Location-specific: {area_warning}")
        warnings.append(soil.confidence_note)

        return FoundationDesign(
            type="pile",
            size_m=cap_size,
            depth_m=pile_spec.typical_length_m,
            concrete_cum_per_footing=concrete_per_col,
            steel_kg_per_footing=steel_per_col,
            total_concrete_cum=total_concrete,
            total_steel_kg=total_steel,
            footing_count=col_count,
            soil_profile=soil,
            water_table_risk=wt_risk,
            adjacent_footing_risk=False,
            area_specific_warning=area_warning,
            pile_spec=pile_spec,
            piles_per_column=piles_per_col,
            total_piles=total_piles,
            has_edge_columns=is_property_line_edge,
            warnings=warnings,
        )

    def _design_strap(
        self, grid, structure, soil, column_load_kn, city, area,
    ) -> FoundationDesign:
        fw, fl = calculate_isolated_footing_size(
            column_load_kn, soil.safe_bearing_capacity_t_sqm
        )
        edge_count = sum(1 for c in grid.columns if c.on_perimeter)
        strap_count = max(edge_count // 2, 1)

        concrete_per_footing, steel_per_footing = estimate_footing_quantities(
            (fw, fl), depth_m=0.35
        )
        strap_concrete = 0.3 * 0.6 * grid.max_span_m
        strap_steel = strap_concrete * 150

        total_footings = len(grid.columns)
        total_concrete = (
            concrete_per_footing * total_footings + strap_concrete * strap_count
        )
        total_steel = (
            steel_per_footing * total_footings + strap_steel * strap_count
        )

        wt_risk = check_water_table_risk(soil, 0.35)
        area_warning = get_area_warning(city, area)

        warnings = [
            f"STRAP FOOTING: used at property-line edges to avoid neighbor "
            f"encroachment. Adds {strap_count} strap beam(s) connecting "
            f"edge footings to interior.",
            "Adds ~10-15% cost vs pure isolated footings.",
        ]
        if area_warning:
            warnings.append(f"Location-specific: {area_warning}")
        if wt_risk["warning"]:
            warnings.append(f"Water table: {wt_risk['warning']}")
        warnings.append(soil.confidence_note)

        return FoundationDesign(
            type="strap",
            size_m=(fw, fl),
            depth_m=0.35,
            concrete_cum_per_footing=concrete_per_footing,
            steel_kg_per_footing=steel_per_footing,
            total_concrete_cum=total_concrete,
            total_steel_kg=total_steel,
            footing_count=total_footings,
            soil_profile=soil,
            water_table_risk=wt_risk,
            adjacent_footing_risk=False,
            area_specific_warning=area_warning,
            has_edge_columns=True,
            strap_beams_count=strap_count,
            warnings=warnings,
        )

    def _design_shallow(
        self, grid, structure, soil, column_load_kn,
        city, area, foundation_type, is_property_line_edge,
    ) -> FoundationDesign:
        if foundation_type in ("isolated", "combined"):
            footing_size = calculate_isolated_footing_size(
                column_load_kn, soil.safe_bearing_capacity_t_sqm
            )
        else:
            footing_size = (grid.envelope_width_m, grid.envelope_depth_m)

        footing_depth = 0.35 if foundation_type != "raft" else 0.45

        concrete_per_footing, steel_per_footing = estimate_footing_quantities(
            footing_size, depth_m=footing_depth
        )

        footing_count = 1 if foundation_type == "raft" else len(grid.columns)
        total_concrete = concrete_per_footing * footing_count
        total_steel = steel_per_footing * footing_count

        wt_risk = check_water_table_risk(soil, footing_depth)
        adjacent_risk = footing_size[0] > grid.max_span_m * 0.4
        area_warning = get_area_warning(city, area)

        warnings = []
        if wt_risk["warning"]:
            warnings.append(f"Water table: {wt_risk['warning']}")
        if adjacent_risk:
            warnings.append(
                f"Footing width {footing_size[0]}m close to column spacing "
                f"{grid.max_span_m}m — consider combined footings."
            )
        if area_warning:
            warnings.append(f"Location-specific: {area_warning}")
        if foundation_type == "raft":
            warnings.append(
                "RAFT FOUNDATION recommended. More expensive than isolated "
                "but necessary given loads and soil. Adds ~₹80K-1.5L."
            )
        warnings.append(soil.confidence_note)

        return FoundationDesign(
            type=foundation_type,
            size_m=footing_size,
            depth_m=footing_depth,
            concrete_cum_per_footing=concrete_per_footing,
            steel_kg_per_footing=steel_per_footing,
            total_concrete_cum=total_concrete,
            total_steel_kg=total_steel,
            footing_count=footing_count,
            soil_profile=soil,
            water_table_risk=wt_risk,
            adjacent_footing_risk=adjacent_risk,
            area_specific_warning=area_warning,
            has_edge_columns=is_property_line_edge,
            warnings=warnings,
        )
