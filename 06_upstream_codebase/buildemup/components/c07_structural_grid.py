"""
BuildemUp† — Component 7: Structural Grid (Orchestrator)
==========================================================

Thin coordinator for the 4 split responsibilities:
  7a: GridGenerator      → column positions
  7b: StructuralSizer    → column/beam/slab dimensions + load estimation
  7c: FoundationEngine   → foundation type + sizing + water table check
  7d: CostEstimator      → ₹ via RateProvider abstraction

This file is now small and simple. Each sub-module is independently
testable and has a single responsibility.

B-S53-C7-LEGACY-DECISION resolution (S56, 2026-05-16): KEEP.
The S53 backlog filed this as a "951-LOC pre-amendment monolithic file"
and asked whether to delete or deprecate. On audit in S56 the file is
NOT a legacy monolith — it is the canonical top-level Component-7
orchestrator. The modular `c07/` sub-package contains data types
(grid_generator, wall_segment, foundation_engine, cost_estimator, etc.)
that this orchestrator composes; the two are complementary, not
duplicative. 9+ importers across api/, examples/, and tests/ correctly
use this entry point. No action required.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from buildemup.components.c07.grid_generator import GridGenerator, Grid, ColumnPosition
from buildemup.components.c07.structural_sizer import StructuralSizer, SizedStructure
from buildemup.components.c07.foundation_engine import FoundationEngine, FoundationDesign
from buildemup.components.c07.cost_estimator import StructuralCostEstimator
from buildemup.components.c07.frame_sanity import (
    run_frame_sanity_check, FrameSanityReport, FrameSanityResult,
)
from buildemup.components.c07.load_combinations import (
    LoadInputs, find_governing_combination, GoverningResult,
)
from buildemup.components.c07.global_stability import (
    run_global_stability_check, GlobalStabilityReport, DriftCheckResult,
    LoadCase, estimate_base_shear_kn,
)
from buildemup.utils.rate_provider import RateProvider
from buildemup.utils.transparency import TransparencyTriple
from buildemup.utils.confidence import Confidence
from buildemup.utils.sensitivity import compute_sensitivity, SensitivityReport
from buildemup.utils.structural_sensitivity import (
    compute_structural_sensitivity,
    StructuralSensitivityReport,
)
from buildemup.utils.kb_versions import (
    get_versions_for_modules, enforce_freshness_and_get_action,
    should_degrade_confidence,
)
from buildemup.utils.logging import new_trace_id, get_logger
from buildemup.utils.errors import UnsupportedConfigurationError
from buildemup.utils.component_contract import (
    ComponentContract, FieldSpec, register_contract, required, optional,
)
from buildemup.utils.engineering_depth import (
    EngineeringDepth, DepthIndicator, level_2_indicator,
)
from buildemup.utils.legal_disclosures import (
    format_legal_disclosures_block,
)
from buildemup.utils.insights_buffer import (
    get_insights_buffer, build_signature_from_result,
)
from buildemup.kb.material_rates_chennai import ChennaiRateProvider
from buildemup.kb.rcc_design_rules import CITATIONS
from buildemup.kb.load_estimation import SAFETY_FACTORS
from buildemup.kb.building_types import (
    BuildingType, get_spec, is_fully_implemented,
)


# ─── Input contract ─────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StructuralGridInput:
    """Input contract for Component 7."""
    envelope_width_m: float
    envelope_depth_m: float
    floors_above_ground: int
    city: str = "chennai"
    area: str | None = None
    seismic_zone: str = "II"
    has_stilt_parking: bool = False
    has_terrace_access: bool = True
    has_water_tank: bool = True
    plot_facing: str = "NE"
    # v0.3 additions:
    terrain_category: str = "urban"
    re_entrant_corner_x_m: float = 0.0
    re_entrant_corner_y_m: float = 0.0
    is_property_line_edge: bool = False
    # v0.4 addition: building type (defaults to residential single-family
    # for backwards compatibility with v0.3 callers)
    building_type: BuildingType = BuildingType.RESIDENTIAL_SINGLE_FAMILY

    # v0.5/v0.6 addition: user-claimed engineer review for severe-irregularity bypass.
    # v0.6 RENAME: engineer_validated_override → user_claims_engineer_reviewed.
    # We do NOT verify engineer claims. We record them for the user's audit
    # trail and label all output as "user-claimed, unverified". The engineer
    # is the user's own consultant; we are not in the verification chain.
    # See docs/v2_vision.md for the legal positioning.
    user_claims_engineer_reviewed: bool = False
    engineer_name: str = ""             # e.g., "Dr. Ramesh Krishnan" (claimed)
    engineer_license_no: str = ""       # e.g., "TN/SE/2018/4521" (claimed)
    engineer_validation_date: str = ""  # ISO date string (claimed)

    # v0.6 addition: optional consultant-engineer info user records for
    # their own reference. NEVER appears in output. Session-only.
    user_engineer_consultant: str = ""

    # v0.6 backwards-compat alias: callers using the old name still work.
    # Use a class-level setter via __post_init__.
    engineer_validated_override: bool = False  # DEPRECATED, use user_claims_engineer_reviewed

    def __post_init__(self):
        # v0.6 back-compat: if user passed the old name, mirror it to new
        if self.engineer_validated_override and not self.user_claims_engineer_reviewed:
            object.__setattr__(self, "user_claims_engineer_reviewed", True)
        if self.envelope_width_m < 5.0 or self.envelope_depth_m < 5.0:
            raise ValueError(
                f"Envelope too small: {self.envelope_width_m}m × "
                f"{self.envelope_depth_m}m. Minimum 5×5m required for "
                f"structural design."
            )
        if self.floors_above_ground < 0 or self.floors_above_ground > 4:
            raise ValueError(
                f"Floors above ground must be 0-4. Got {self.floors_above_ground}. "
                f"For taller buildings, custom structural design is needed."
            )
        # v0.5: engineer claim requires audit fields
        if self.user_claims_engineer_reviewed:
            missing = []
            if not self.engineer_name.strip():
                missing.append("engineer_name")
            if not self.engineer_license_no.strip():
                missing.append("engineer_license_no")
            if not self.engineer_validation_date.strip():
                missing.append("engineer_validation_date")
            if missing:
                raise ValueError(
                    f"user_claims_engineer_reviewed requires audit fields: "
                    f"{', '.join(missing)}. We do NOT verify engineer claims, "
                    f"but we record name, license, and date for the user's "
                    f"audit trail. The engineer is your own consultant; "
                    f"BuildemUp does not verify or endorse them."
                )


# ─── Output contract ────────────────────────────────────────────────────────
@dataclass
class StructuralGridOutput:
    """Complete output of Component 7."""
    grid: Grid
    structure: SizedStructure
    foundation: FoundationDesign
    cost: TransparencyTriple
    sensitivity: SensitivityReport
    all_warnings: list[str] = field(default_factory=list)
    # v0.4: traceability + reproducibility
    trace_id: str = ""
    kb_versions: dict[str, str] = field(default_factory=dict)
    # v0.4: structural sensitivity (narrow scope: soil + load)
    structural_sensitivity: StructuralSensitivityReport | None = None
    # v0.6: frame sanity check output (LEVEL 2 engineering depth)
    frame_sanity: FrameSanityReport | None = None
    # v0.6: engineering depth indicator
    engineering_depth: DepthIndicator | None = None
    # v0.6: validation status — always PENDING ENGINEER VALIDATION
    # (maybe with user-claim variant)
    validation_status: str = "PENDING ENGINEER VALIDATION"
    # v0.6: freshness enforcement outcome
    freshness_action: str = "OK"  # OK | WARN_DEGRADE_CONFIDENCE | BLOCK_STALE
    freshness_message: str = ""
    # v0.7: global stability (storey-drift) report — per review Drawback 1
    global_stability: GlobalStabilityReport | None = None
    # v0.7.2: proactive guidance from insights buffer (patterns from
    # recent executions in this deployment) — per v0.7.1 review Deferred #3
    proactive_guidance: Any = None  # ProactiveGuidance | None; typed at use


# ─── Orchestrator ───────────────────────────────────────────────────────────
class StructuralGridEngine:
    """Component 7: coordinates grid / sizing / foundation / cost.

    Each step is a separate sub-component with single responsibility.
    """

    def __init__(self, rate_provider: RateProvider | None = None):
        """Initialize with optional custom rate provider.

        Args:
            rate_provider: if None, auto-selects provider based on city.
                          Pass a specific provider to override.
        """
        self.grid_gen = GridGenerator()
        self.sizer = StructuralSizer()
        self.foundation_engine = FoundationEngine()
        # Default provider is Chennai; city-specific selection happens at execute() time
        self.rate_provider = rate_provider
        self._cost_est_cache: dict[str, StructuralCostEstimator] = {}

    def _get_cost_estimator(self, city: str) -> StructuralCostEstimator:
        """Get (cache) the cost estimator for a city.

        If city has no specific rate provider, falls back to Chennai rates
        with a warning that costs are approximate.
        """
        if self.rate_provider is not None:
            key = "custom"
            if key not in self._cost_est_cache:
                self._cost_est_cache[key] = StructuralCostEstimator(self.rate_provider)
            return self._cost_est_cache[key]
        city_key = city.lower().strip()
        if city_key not in self._cost_est_cache:
            from buildemup.kb.material_rates_multicity import (
                get_rate_provider, CITY_COST_MULTIPLIER
            )
            if city_key in CITY_COST_MULTIPLIER:
                provider = get_rate_provider(city_key)
            else:
                # Unsupported city — fall back to Chennai with a flag.
                # The orchestrator will append a warning that rates are
                # approximate (Chennai-baseline, not city-verified).
                from buildemup.kb.material_rates_chennai import ChennaiRateProvider
                provider = ChennaiRateProvider()
            self._cost_est_cache[city_key] = StructuralCostEstimator(provider)
        return self._cost_est_cache[city_key]

    @staticmethod
    def _city_has_rates(city: str) -> bool:
        from buildemup.kb.material_rates_multicity import CITY_COST_MULTIPLIER
        return city.lower().strip() in CITY_COST_MULTIPLIER

    def execute(self, inp: StructuralGridInput) -> StructuralGridOutput:
        """Run all 4 sub-components in order."""
        # v0.4: every run gets a trace_id for debugging + reproducibility
        trace_id = new_trace_id()
        logger = get_logger("component7.orchestrator", trace_id)
        logger.info("execute_start",
                    city=inp.city, zone=inp.seismic_zone,
                    floors=inp.floors_above_ground,
                    building_type=inp.building_type.value)

        # v0.4: building-type gate
        # If user requests a building type that's only stubbed (not fully
        # implemented), refuse with helpful message rather than producing
        # potentially-wrong residential-coded output.
        building_spec = get_spec(inp.building_type)
        if not is_fully_implemented(inp.building_type):
            raise UnsupportedConfigurationError(
                technical_message=(
                    f"Building type '{inp.building_type.value}' is "
                    f"architecturally supported but not fully implemented "
                    f"in v0.4. Status: {building_spec.implementation_status}."
                ),
                user_message=(
                    f"{building_spec.display_name} is on our roadmap but "
                    f"not yet fully supported. Currently we fully support "
                    f"residential single-family homes. {building_spec.user_notes}"
                ),
                suggested_action=(
                    "If you need this building type now, please contact us "
                    "— we can run a manual estimate. Otherwise it will be "
                    "available in a future release."
                ),
            )

        # v0.4: enforce per-type max floors
        if inp.floors_above_ground > building_spec.max_floors_above_ground:
            raise UnsupportedConfigurationError(
                technical_message=(
                    f"Floors {inp.floors_above_ground} > max "
                    f"{building_spec.max_floors_above_ground} "
                    f"for {inp.building_type.value}"
                ),
                user_message=(
                    f"For {building_spec.display_name}, our v1 engine "
                    f"supports up to G+{building_spec.max_floors_above_ground}. "
                    f"You requested G+{inp.floors_above_ground}. "
                    f"Higher buildings need custom design."
                ),
                suggested_action=(
                    "Either reduce floor count, or engage a structural "
                    "engineer for high-rise design (typical fee ₹1-3L)."
                ),
            )

        # 7a: Generate grid
        grid = self.grid_gen.generate(inp.envelope_width_m, inp.envelope_depth_m)

        # 7b: Size structure + calculate loads (v0.4: pass building spec)
        structure = self.sizer.size(
            grid=grid,
            floors_above_ground=inp.floors_above_ground,
            has_stilt_parking=inp.has_stilt_parking,
            has_terrace_access=inp.has_terrace_access,
            has_water_tank=inp.has_water_tank,
            seismic_zone=inp.seismic_zone,
            city=inp.city,
            terrain_category=inp.terrain_category,
            re_entrant_corner_x_m=inp.re_entrant_corner_x_m,
            re_entrant_corner_y_m=inp.re_entrant_corner_y_m,
            building_type_spec=building_spec,
        )

        # v0.4: refuse SEVERELY irregular plans
        # The regularity check ran inside sizing. If it came back severe,
        # we must refuse rather than produce false-precision output.
        # v0.6: user_claims_engineer_reviewed allows bypass with audit trail.
        # NOTE: We do NOT verify the engineer claim. We just record it and
        # produce output labelled "USER-CLAIMED ENGINEER REVIEW (UNVERIFIED)".
        if structure.regularity and structure.regularity.requires_refusal:
            if inp.user_claims_engineer_reviewed:
                # User asserts engineer has reviewed. Log the CLAIM
                # prominently so the audit trail is preserved.
                # We do NOT call this "validation" — it is a claim only.
                logger.warning(
                    "user_claims_engineer_review_severe_irregularity",
                    aspect_ratio=structure.regularity.aspect_ratio,
                    re_entrant_pct=structure.regularity.re_entrant_corner_pct,
                    claimed_engineer_name=inp.engineer_name,
                    claimed_engineer_license=inp.engineer_license_no,
                    claimed_validation_date=inp.engineer_validation_date,
                )
                # Proceed with the design. The CLAIM warning appears
                # prominently in the output so the user always sees that
                # we have NOT verified the engineer.
            else:
                from buildemup.utils.errors import EnvelopeTooIrregularError
                raise EnvelopeTooIrregularError(
                    technical_message=(
                        f"Plan severely irregular: aspect ratio "
                        f"{structure.regularity.aspect_ratio}, re-entrant corner "
                        f"{structure.regularity.re_entrant_corner_pct}%"
                    ),
                    user_message=structure.regularity.recommended_action,
                    suggested_action=(
                        "Engage YOUR OWN structural engineer with dynamic "
                        "analysis capability to review this plan. Once your "
                        "engineer has reviewed it, re-submit with "
                        "user_claims_engineer_reviewed=True (plus engineer_name, "
                        "engineer_license_no, engineer_validation_date for your "
                        "audit trail). We do NOT verify the engineer — that "
                        "stays your responsibility. The engineer's stamped "
                        "drawings always supersede our preliminary estimate. "
                        "Typical engineer fee: ₹60K-1L for dynamic analysis "
                        "of an irregular residential plan."
                    ),
                )

        # 7c: Design foundation
        foundation = self.foundation_engine.design(
            grid=grid,
            structure=structure,
            city=inp.city,
            area=inp.area,
            is_property_line_edge=inp.is_property_line_edge,
        )

        # 7d: Estimate cost (city-specific rate provider auto-selected)
        cost_est = self._get_cost_estimator(inp.city)
        cost = cost_est.estimate(structure, foundation)

        # v0.3: Sensitivity analysis on cost
        sensitivity = compute_sensitivity(cost)

        # v0.4: Structural sensitivity (narrow scope: soil + column load)
        structural_sens = compute_structural_sensitivity(
            actual_soil_sbc_t_sqm=foundation.soil_profile.safe_bearing_capacity_t_sqm,
            actual_foundation_type=foundation.type,
            actual_column_load_kn=structure.max_column_axial_load_kn,
            actual_column_size_mm=structure.column_size_mm,
            actual_total_cost_rupees=cost.exact_value,
        )

        # Consolidate warnings
        all_warnings = structure.warnings + foundation.warnings

        # v0.6: if user CLAIMS engineer review, surface it prominently as
        # an UNVERIFIED claim. We never call this "validated" — that would
        # imply we've checked the engineer, which we haven't.
        if (inp.user_claims_engineer_reviewed and structure.regularity
                and structure.regularity.requires_refusal):
            all_warnings.insert(0, (
                f"⚠ UNVERIFIED USER CLAIM: This plan is severely irregular "
                f"(aspect ratio {structure.regularity.aspect_ratio}, "
                f"re-entrant corner {structure.regularity.re_entrant_corner_pct}%). "
                f"Normally we refuse such plans. The USER STATES that "
                f"{inp.engineer_name} (license claimed: {inp.engineer_license_no}, "
                f"date claimed: {inp.engineer_validation_date}) has reviewed "
                f"this geometry. BuildemUp has NOT verified this claim — we "
                f"do not endorse, contact, or verify any engineer. Our cost "
                f"estimate assumes the engineer's detailing (typically shear "
                f"walls or special framing). Independent validation by your "
                f"engineer is still required before construction. The "
                f"engineer's stamped drawings always supersede our estimate."
            ))

        # Add warning if city falls back to Chennai rates
        if self.rate_provider is None and not self._city_has_rates(inp.city):
            all_warnings.insert(0, (
                f"NOTE: {inp.city.title()} doesn't have city-specific rate "
                f"data yet. Costs shown are based on Chennai rates as a "
                f"baseline approximation. Local rates may differ ±15-25%. "
                f"Get a contractor quote for verification."
            ))

        # v0.4: pin KB versions used in this output for reproducibility
        kb_used = [
            "rcc_design_rules", "soil_foundation_rules", "load_estimation",
            "seismic_detailing", "wind_load",
        ]
        if inp.city.lower() == "chennai":
            kb_used.append("material_rates_chennai")
        else:
            kb_used.append("material_rates_multicity")
        if structure.regularity and not structure.regularity.is_regular:
            pass  # seismic detailing already in list
        # Add pile foundation KB if relevant
        if foundation.type == "pile":
            kb_used.append("pile_foundation")
        kb_versions = get_versions_for_modules(kb_used)

        logger.info("execute_complete",
                    cost=cost.exact_value,
                    foundation_type=foundation.type,
                    column_size=structure.column_size_mm)

        # v0.6: frame sanity check (LEVEL 2 engineering depth)
        # Build a simplified per-column load list from the structure output.
        # Every column gets approximately the same load in our preliminary
        # model — engineer's frame analysis will refine this.
        n_cols = grid.columns_x_count * grid.columns_y_count
        # Approximate per-column load from total factored structural load
        # Simplified: distribute equally; engineer will refine.
        per_col_axial_kn = getattr(structure, 'column_load_kn', 400.0)
        # Small lateral moments for demonstration (real values from wind/seismic)
        col_loads_for_sanity = []
        for i in range(n_cols):
            col_loads_for_sanity.append({
                "column_id": f"C{i+1}",
                "pu_kn": per_col_axial_kn,
                "mux_knm": 15.0,   # Preliminary moment estimate
                "muy_knm": 10.0,
                "column_dim_mm": structure.column_size_mm,
                "fck_mpa": 25.0 if structure.concrete_grade == "M25" else 30.0,
                "steel_pct": 1.0,
                "fy_mpa": 500.0,
            })
        frame_sanity = run_frame_sanity_check(
            col_loads_for_sanity,
            governing_combo="1.5(DL+LL+EQ) preliminary",
        )

        # v0.7: global stability / drift check (per review Drawback 1)
        # Estimate total seismic weight from floor areas + typical loading.
        # Approx: ~10 kN/m² per habitable floor for seismic weight (DL + 25%LL)
        seismic_weight_kn = (
            (inp.floors_above_ground + 1) *
            (inp.envelope_width_m * inp.envelope_depth_m) *
            10.0  # kN/m² combined seismic weight approximation
        )
        base_shear_kn = estimate_base_shear_kn(
            total_seismic_weight_kn=seismic_weight_kn,
            seismic_zone=inp.seismic_zone,
        )
        # Storey count for drift analysis = habitable floors (stilt not counted
        # for drift — it only has columns, no lateral mass above it on stilt
        # level itself). Use max(1, floors) so we never pass 0.
        n_storeys_for_drift = max(1, inp.floors_above_ground + 1)
        global_stability = run_global_stability_check(
            n_storeys=n_storeys_for_drift,
            storey_height_m=3.0,
            n_columns_per_storey=n_cols,
            column_dim_mm=structure.column_size_mm,
            fck_mpa=25.0 if structure.concrete_grade == "M25" else 30.0,
            total_base_shear_kn=base_shear_kn,
            load_case=LoadCase.SEISMIC,
        )
        # Surface WARNING/FAIL into user-facing warnings
        if global_stability.overall_result == DriftCheckResult.FAIL:
            all_warnings.insert(0, (
                f"⚠ GLOBAL STABILITY FAIL: storey drift exceeds IS 1893:2016 "
                f"cl. 7.11.1 limit (0.004h). Worst storey: "
                f"{global_stability.worst_storey} at "
                f"{global_stability.worst_utilization_pct}% of code limit. "
                f"Columns are too flexible — engineer MUST upsize columns OR "
                f"add shear walls OR brace frames before construction."
            ))
        elif global_stability.overall_result == DriftCheckResult.WARNING:
            all_warnings.append(
                f"Global stability warning: storey drift within IS 1893 "
                f"limit but tight ({global_stability.worst_utilization_pct}% "
                f"utilised at storey {global_stability.worst_storey}). "
                f"Engineer should verify with full frame analysis."
            )

        # v0.6: engineering depth indicator
        depth_indicator = level_2_indicator()

        # v0.6: freshness enforcement
        freshness = enforce_freshness_and_get_action()
        if freshness["action"] == "WARN_DEGRADE_CONFIDENCE":
            all_warnings.append(freshness["user_message"])
            # Degrade confidence one level if currently well-constrained
            if cost.confidence == Confidence.WELL_CONSTRAINED:
                cost = TransparencyTriple(
                    label=cost.label,
                    exact_value=cost.exact_value,
                    unit=cost.unit,
                    uncertainty_pct=cost.uncertainty_pct,
                    confidence=Confidence.REGIONAL_TYPICAL,   # degraded
                    derivation=cost.derivation,
                    notes=list(cost.notes) + [
                        "Confidence degraded one level due to stale KB data.",
                    ],
                )
        elif freshness["action"] == "BLOCK_STALE":
            all_warnings.insert(0, freshness["user_message"])

        # v0.6: build validation status string (per Q2 decision)
        if inp.user_claims_engineer_reviewed:
            validation_status = (
                "PENDING ENGINEER VALIDATION "
                "(user claims engineer reviewed — UNVERIFIED)"
            )
        else:
            validation_status = "PENDING ENGINEER VALIDATION"

        # v0.7.2: retrieve proactive guidance from insights buffer
        # BEFORE building the result (we include guidance in the result).
        # Also record this execution to the buffer AFTER so it contributes
        # to future executions' guidance.
        insights = get_insights_buffer()
        proactive_guidance = insights.get_proactive_guidance()

        result = StructuralGridOutput(
            grid=grid,
            structure=structure,
            foundation=foundation,
            cost=cost,
            sensitivity=sensitivity,
            all_warnings=all_warnings,
            trace_id=trace_id,
            kb_versions=kb_versions,
            structural_sensitivity=structural_sens,
            frame_sanity=frame_sanity,
            engineering_depth=depth_indicator,
            validation_status=validation_status,
            freshness_action=freshness["action"],
            freshness_message=freshness["user_message"],
            global_stability=global_stability,
            proactive_guidance=proactive_guidance,
        )

        # v0.7.2: record this execution's signature for future guidance.
        # Errors in recording must never fail the execute call — we
        # swallow exceptions defensively.
        try:
            signature = build_signature_from_result(inp, result, has_refusal=False)
            insights.record(signature)
        except Exception as e:
            logger.warning("insights_recording_failed", error=str(e))

        return result

    def explain(
        self, inp: StructuralGridInput, result: StructuralGridOutput
    ) -> str:
        """User-facing explanation. Principle 1: talks to user, not engine."""
        floors_label = (
            "G only" if inp.floors_above_ground == 0
            else f"G+{inp.floors_above_ground}"
        )
        if inp.has_stilt_parking:
            floors_label = "Stilt + " + floors_label
        if inp.has_terrace_access:
            floors_label += " + accessible terrace"

        # v0.4: PROMINENT preliminary-design banner at the TOP, not buried
        # v0.5: language strengthened — "rule-based heuristic estimate, NOT
        # structural design" addresses the v0.4 review's concern that even
        # with the banner, users could still over-trust the output.
        building_spec = get_spec(inp.building_type)
        lines = [
            "╔" + "═" * 68 + "╗",
            "║" + " ⚠  RULE-BASED HEURISTIC ESTIMATE  ⚠ ".center(68) + "║",
            "║" + " This is NOT structural design. ".center(68) + "║",
            "║" + " It is a preliminary cost & sizing estimate ".center(68) + "║",
            "║" + " produced by applying Indian-code rules ".center(68) + "║",
            "║" + " (IS 456, IS 875, IS 13920) to your inputs. ".center(68) + "║",
            "║" + (" " * 68) + "║",
            "║" + " A LICENSED STRUCTURAL ENGINEER must produce ".center(68) + "║",
            "║" + " final drawings before any construction begins. ".center(68) + "║",
            "║" + " Their analysis (frame analysis, P-M diagrams, ".center(68) + "║",
            "║" + " moment capacity) supersedes our estimate. ".center(68) + "║",
            "╚" + "═" * 68 + "╝",
            "",
            f"Building type: {building_spec.display_name}",
            "",
            "─" * 70,
            "STRUCTURAL GRID — what we designed for your home",
            "─" * 70,
            "",
            f"Your buildable area: {inp.envelope_width_m}m × "
            f"{inp.envelope_depth_m}m ({floors_label})",
            "",
            "We laid out the columns first — before any rooms — because that's",
            "how structural engineers actually work. Walls have to land on or",
            "near columns. If we placed rooms first, many would need expensive",
            "structural workarounds.",
            "",
            f"COLUMN GRID: {result.grid.columns_x_count} × "
            f"{result.grid.columns_y_count} = {result.grid.total_columns} columns",
            f"  Bay sizes: {result.grid.bay_x_m}m × {result.grid.bay_y_m}m",
            "  This is the 'sweet spot' for residential RCC — enough room for",
            "  furniture, but small enough to be cost-efficient.",
            "",
            f"COLUMN SIZE: {result.structure.column_size_mm} × "
            f"{result.structure.column_size_mm} mm",
            f"  Sized per {CITATIONS['IS_456']}.",
            "  This matches a standard 9-inch wall so columns hide in walls.",
            "",
            f"LOADS ON EACH COLUMN:",
            f"  Service load (day-to-day): {result.structure.max_column_load_unfactored_kn:.0f} kN",
            f"  Factored load (with safety factors): "
            f"{result.structure.max_column_axial_load_kn:.0f} kN",
            "",
            f"  Safety factors applied (IS 456 cl. 36.4):",
            f"    • Dead load factor γf = {SAFETY_FACTORS['dead_load']}",
            f"    • Live load factor γf = {SAFETY_FACTORS['live_load']}",
            f"    • Concrete material factor γm = {SAFETY_FACTORS['concrete_material']}",
            f"    • Steel material factor γm = {SAFETY_FACTORS['steel_material']}",
            "",
            f"BEAM DEPTH: {result.structure.beam_depth_mm} mm",
            f"  Calculated as span / 12 ({CITATIONS['DEVDAS_MENON']}).",
            "  Assumption: simply-supported beams (conservative vs continuous).",
            "",
            f"SLAB THICKNESS: {result.structure.slab_thickness_mm} mm",
            f"  Two-way slab, {CITATIONS['IS_456']} cl. 23.2.1.",
            "",
            f"CONCRETE GRADE: {result.structure.concrete_grade}",
            f"  Required for {floors_label} per "
            f"{CITATIONS['IS_456']} cl. 6.1.",
            "",
            f"FOUNDATION: {result.foundation.type.upper()}",
            f"  Soil: {result.foundation.soil_profile.typical_soil} "
            f"(SBC {result.foundation.soil_profile.safe_bearing_capacity_t_sqm} T/sqm)",
            f"  Footing size: {result.foundation.size_m[0]}m × "
            f"{result.foundation.size_m[1]}m per column, "
            f"{result.foundation.depth_m}m deep",
            f"  Water table (monsoon): "
            f"{result.foundation.soil_profile.monsoon_water_table_m}m below "
            f"ground — risk {result.foundation.water_table_risk['level']}",
            "",
            "QUANTITIES (estimated):",
            f"  Total concrete: {result.structure.total_concrete_cum:.1f} cubic metres",
            f"  Total steel:    {result.structure.total_steel_tonnes:.2f} tonnes",
            "",
            "STRUCTURAL COST:",
            f"  {result.cost.format_short()}",
            "",
            "  Click for breakdown:",
        ]

        for d in result.cost.derivation:
            lines.append("  " + d.format_line())

        if result.cost.notes:
            lines.append("")
            lines.append("  Why the range exists:")
            for n in result.cost.notes:
                lines.append(f"    • {n}")

        # v0.5: confidence legend uses descriptive names (renamed from HIGH/MEDIUM/LOW)
        # The old names misled users into reading 'HIGH' as 'highly accurate'.
        lines.append("")
        lines.append(f"  Confidence shown above means:")
        lines.append(
            f"    Well-constrained:        Computed from Indian codes (IS 456, IS 875). "
            f"Variability ±5% or less."
        )
        lines.append(
            f"    Regional typical:        Modelled from typical regional values. "
            f"Variability ±5-15% by local conditions."
        )
        lines.append(
            f"    Depends on your choices: Depends on contractor / supplier / finish "
            f"choice. Variability often >15%."
        )
        lines.append(
            f"  NOTE: Confidence is about INPUT certainty + model stability — "
            f"NOT about engineering correctness. Even 'Well-constrained' values "
            f"need engineer validation at detailed design."
        )

        # v0.3: Sensitivity analysis (cost)
        lines.append("")
        lines.append("WHAT IF RATES CHANGE? (top 3 cost drivers)")
        top_drivers = result.sensitivity.lines[:3]
        for line in top_drivers:
            lines.append(line.format_line())

        # v0.4: Structural sensitivity (soil + load)
        if result.structural_sensitivity:
            lines.append("")
            lines.append(result.structural_sensitivity.format_full().rstrip())

        if result.all_warnings:
            lines.append("")
            lines.append("THINGS TO KNOW:")
            for w in result.all_warnings:
                lines.append(f"  • {w}")

        # v0.4: explicit "WHAT WE CHECK / WHAT WE DON'T CHECK" disclosure
        lines.append("")
        lines.append("─" * 70)
        lines.append("WHAT THIS ESTIMATE COVERS — and what it does NOT")
        lines.append("─" * 70)
        lines.append("")
        lines.append("✓ WE CHECK (rule-based, per Indian codes):")
        lines.append("  • Column dimensions per IS 456 + IS 13920 (Zone III+)")
        lines.append("  • Beam depth heuristic (Devdas Menon span/depth = 12)")
        lines.append("  • Slab thickness per IS 456 cl. 23.2.1")
        lines.append("  • Load estimation per IS 875 (dead, live, water tank)")
        lines.append("  • Foundation type selection (isolated/raft/pile)")
        lines.append("  • Wind load per IS 875 Part 3")
        lines.append("  • Seismic zone factor per IS 1893")
        lines.append("  • SCWB heuristic (dimensional ratio only)")
        lines.append("  • Slenderness ratio (IS 456 cl. 25.1.2)")
        lines.append("  • Plan regularity classification (REGULAR/MODERATE/SEVERE)")
        lines.append("  • Wind vs seismic governing comparison")
        lines.append("  • Cost via city-specific rates with sensitivity analysis")
        lines.append("")
        lines.append("✗ WE DO NOT CHECK (engineer's job at detailed design):")
        lines.append("  • Moment capacity calculation (true SCWB compliance)")
        lines.append("  • P-M interaction diagrams for actual reinforcement")
        lines.append("  • Frame analysis with stiffness matrix")
        lines.append("  • Beam shear reinforcement design")
        lines.append("  • Bending moment + shear envelope for beams")
        lines.append("  • Serviceability: deflection limits, crack width control")
        lines.append("  • Pile skin friction vs end bearing breakdown")
        lines.append("  • Pile group settlement interaction")
        lines.append("  • Differential settlement modelling")
        lines.append("  • Long-term effects: creep, shrinkage")
        lines.append("  • Dynamic earthquake response (we use static method only)")
        # v0.5: explicit disclosure that load combination is simplified
        lines.append("  • Full IS 875 Part 5 load combination matrix "
                     "(we compare wind vs seismic governing case only)")
        lines.append("  • Directional + torsional effects in lateral analysis")
        lines.append("  • Span variation + material strength sensitivity "
                     "(we cover soil + load only)")
        lines.append("")
        lines.append("This is PRELIMINARY DESIGN for cost decision-support.")
        lines.append("Engage a licensed structural engineer for FINAL drawings.")
        lines.append("Typical engineer fee: ₹20-40K for 1200 sqft residential.")
        lines.append("Their drawings supersede our preliminary estimate.")

        # v0.6: VALIDATION STATUS section (prominent)
        lines.append("")
        lines.append("─" * 70)
        lines.append("VALIDATION STATUS")
        lines.append("─" * 70)
        lines.append(f"Status: {result.validation_status}")
        lines.append("")
        lines.append(
            "Every BuildemUp estimate ships with this status. It remains "
            "'pending' until your structural engineer has independently "
            "reviewed and stamped the drawings. BuildemUp itself cannot "
            "transition an estimate out of 'pending' — only your engineer can."
        )
        if inp.user_claims_engineer_reviewed:
            lines.append("")
            lines.append(
                f"  User has claimed that {inp.engineer_name} (license: "
                f"{inp.engineer_license_no}, date: {inp.engineer_validation_date}) "
                f"has reviewed this design. BuildemUp has NOT verified this "
                f"claim — it is recorded for your audit trail only. Independent "
                f"validation is still required before construction."
            )

        # v0.6: ENGINEERING DEPTH section
        if result.engineering_depth is not None:
            lines.append("")
            lines.append("─" * 70)
            lines.append("ENGINEERING DEPTH")
            lines.append("─" * 70)
            lines.append(result.engineering_depth.format_for_user())

        # v0.6: FRAME SANITY CHECK section (LEVEL 2 output)
        if result.frame_sanity is not None:
            lines.append("")
            lines.append("─" * 70)
            lines.append("FRAME SANITY CHECK (preliminary, IS 456 cl. 39.6)")
            lines.append("─" * 70)
            lines.append(result.frame_sanity.user_summary)
            lines.append("")
            # Show the handful of columns with worst ratio if any warnings/fails
            fails = [c for c in result.frame_sanity.columns
                     if c.result.value in ("WARNING", "FAIL")]
            if fails:
                lines.append("Columns flagged (engineer should review first):")
                for c in fails[:3]:  # Show up to 3 worst
                    lines.append(
                        f"  • {c.column_id}: {c.result.value} "
                        f"(Bresler ratio {c.bresler_ratio}, αn={c.alpha_n})"
                    )
            lines.append("")
            lines.append(result.frame_sanity.method_disclosure)

        # v0.7: GLOBAL STABILITY / DRIFT CHECK section (per review Drawback 1)
        if result.global_stability is not None:
            lines.append("")
            lines.append("─" * 70)
            lines.append("GLOBAL STABILITY / DRIFT CHECK (IS 1893 cl. 7.11.1.1)")
            lines.append("─" * 70)
            lines.append(result.global_stability.user_summary)
            # Show any flagged storeys
            flagged = [c for c in result.global_stability.storey_checks
                       if c.result.value in ("WARNING", "FAIL")]
            if flagged:
                lines.append("")
                lines.append("Storeys flagged for engineer review:")
                for c in flagged:
                    lines.append(
                        f"  • Storey {c.storey_number}: {c.result.value} "
                        f"(drift {c.drift_mm}mm, {c.utilization_pct}% of code limit)"
                    )
            lines.append("")
            lines.append(result.global_stability.method_disclosure)

        # v0.7: TOP RECOMMENDATIONS section (per review Drawback 5)
        # Surface the highest-priority actions derived from sensitivity analysis.
        if (result.structural_sensitivity is not None
                and result.structural_sensitivity.top_recommendations):
            lines.append("")
            lines.append("─" * 70)
            lines.append("TOP RECOMMENDATIONS (what you can do about sensitivities)")
            lines.append("─" * 70)
            lines.append(
                result.structural_sensitivity.format_recommendations_only()
            )

        # v0.7.2: PROACTIVE GUIDANCE section (insights from recent executions)
        # Only shown if we have meaningful signal (≥10 executions in buffer).
        if (result.proactive_guidance is not None
                and result.proactive_guidance.has_meaningful_signal):
            lines.append("")
            lines.append("─" * 70)
            lines.append("PROACTIVE GUIDANCE (patterns from recent plans)")
            lines.append("─" * 70)
            lines.append(result.proactive_guidance.user_message)
            lines.append("")
            lines.append(
                f"This guidance is based on {result.proactive_guidance.total_executions_seen} "
                f"recent plans processed in this deployment. Buffer resets on "
                f"redeploy — patterns rebuild automatically."
            )

        # v0.6: FRESHNESS STATUS (only shown if not OK)
        if result.freshness_action != "OK":
            lines.append("")
            lines.append("─" * 70)
            lines.append("DATA FRESHNESS")
            lines.append("─" * 70)
            lines.append(result.freshness_message)

        # v0.6: LEGAL & STATUTORY DISCLOSURES (always shown per Q2 decision)
        # v0.7: supports legal_mode='full' (default) or 'compact'
        lines.append("")
        lines.append(format_legal_disclosures_block(mode="full"))

        # v0.4: Reproducibility footer with KB versions + trace ID
        lines.append("")
        lines.append("─" * 70)
        lines.append("REPRODUCIBILITY")
        lines.append("─" * 70)
        if result.kb_versions:
            lines.append("Knowledge bases used in this estimate:")
            for module, version in sorted(result.kb_versions.items()):
                lines.append(f"  • {module}: {version}")
        if result.trace_id:
            lines.append(f"Trace ID (for support/debugging): {result.trace_id}")
        lines.append(
            "Save these versions if you want to reproduce this estimate later "
            "— rates and codes update over time."
        )
        lines.append("─" * 70)

        return "\n".join(lines)


# ─── Component Contract Registration (v0.5) ──────────────────────────────
# Explicit declaration of what Component 7 consumes and produces.
# Downstream components (Component 1 brief, Component 8 layout, etc.)
# can validate their assumptions against this contract.
_CONTRACT = ComponentContract(
    component_id="C07_structural_grid",
    version="0.6",
    description=(
        "Generates structural grid (columns, beams, slabs, foundation) for "
        "a residential single-family home. Produces preliminary design "
        "estimate with full transparency, sensitivity analysis, and IS-code "
        "citations."
    ),
    consumes=(
        required("envelope_width_m", "float", "Plot buildable width in metres",
                 ">=5.0", "<=50.0"),
        required("envelope_depth_m", "float", "Plot buildable depth in metres",
                 ">=5.0", "<=50.0"),
        required("floors_above_ground", "int", "Number of floors above ground",
                 ">=0", "<=4"),
        optional("city", "str", "City name (defaults to chennai)"),
        optional("seismic_zone", "str", "II, III, or IV (V refused)",
                 "in: II|III|IV"),
        optional("building_type", "BuildingType",
                 "Building type enum (defaults to RESIDENTIAL_SINGLE_FAMILY)"),
        optional("has_stilt_parking", "bool"),
        optional("has_terrace_access", "bool"),
        optional("has_water_tank", "bool"),
        optional("re_entrant_corner_x_m", "float", "L/U corner depth in X"),
        optional("re_entrant_corner_y_m", "float", "L/U corner depth in Y"),
        optional("is_property_line_edge", "bool"),
        optional("user_claims_engineer_reviewed", "bool",
                 "Set True to bypass severe-irregularity refusal (UNVERIFIED claim, audit trail recorded only)"),
        optional("engineer_validated_override", "bool",
                 "DEPRECATED — use user_claims_engineer_reviewed"),
        optional("engineer_name", "str",
                 "User-claimed engineer name (NOT verified by BuildemUp)"),
        optional("engineer_license_no", "str",
                 "User-claimed engineer license (NOT verified by BuildemUp)"),
        optional("engineer_validation_date", "str",
                 "User-claimed validation date ISO format (NOT verified)"),
        optional("user_engineer_consultant", "str",
                 "Optional consultant info for user's records (session-only)"),
    ),
    produces=(
        required("grid", "Grid", "Column grid with positions"),
        required("structure", "SizedStructure",
                 "Sized columns, beams, slabs + IS 13920 detailing"),
        required("foundation", "FoundationDesign",
                 "Foundation type + sizing + warnings"),
        required("cost", "TransparencyTriple",
                 "Cost estimate with low/high/exact + derivation + confidence"),
        required("sensitivity", "SensitivityReport",
                 "Cost sensitivity (top drivers + ±impact)"),
        required("structural_sensitivity", "StructuralSensitivityReport",
                 "Soil + load sensitivity scenarios"),
        required("trace_id", "str", "Unique ID for this run", "not_empty"),
        required("kb_versions", "dict",
                 "Map of KB module → version string used in this output"),
        required("all_warnings", "list",
                 "User-facing warnings (regularity, soil, area-specific)"),
    ),
)
register_contract(_CONTRACT)
