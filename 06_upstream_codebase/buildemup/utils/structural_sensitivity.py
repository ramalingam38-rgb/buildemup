"""
BuildemUp† — Structural Sensitivity Analysis (v0.4)
=====================================================

Narrowly-scoped sensitivity for the two highest-impact structural inputs:
  1. Soil bearing capacity — affects foundation type and size
  2. Column axial load — affects column dimensions and footing size

For each input, computes "what happens if this is 10-20% different from
our assumption?" — does the design change, or stay the same?

This is decision-support: tells the user "if soil test comes back
weaker than expected, your foundation upgrades from raft to pile,
adding ~₹3L." Empowers them to plan for the cost of a soil test
and contingency budget.

Limited to two drivers (not full Monte Carlo) per the v0.3 review:
"sensitivity gives 80% of the value at 5% of the effort."

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """v0.7: An actionable recommendation derived from a sensitivity scenario.

    Per v0.6 review Drawback 5: sensitivity shows cost impact but doesn't
    translate that into 'what should I DO?'. Recommendation closes the loop.
    """
    action_verb: str              # "Keep", "Avoid", "Budget for", "Get"
    action_text: str              # The specific advice
    threshold_basis: str          # Why this threshold (e.g., "beam depth jump at 4m span")
    priority: str                 # "CRITICAL" | "IMPORTANT" | "OPTIONAL"


@dataclass(frozen=True)
class StructuralSensitivityScenario:
    """One what-if scenario for a structural input."""
    driver_name: str             # e.g., "Soil bearing capacity"
    base_value: str              # e.g., "12 T/sqm (assumed)"
    scenario_label: str          # e.g., "If soil tests as 8 T/sqm"
    scenario_change_pct: float   # e.g., -33.3% lower
    structural_impact: str       # What changes structurally
    cost_impact_rupees: float    # Approximate ₹ impact
    user_action: str             # What user can do (v0.4)
    # v0.7: actionable recommendation derived from this scenario
    recommendation: Recommendation | None = None


@dataclass(frozen=True)
class StructuralSensitivityReport:
    """Sensitivity report for the structural design."""
    scenarios: tuple[StructuralSensitivityScenario, ...]

    @property
    def top_recommendations(self) -> list[Recommendation]:
        """v0.7: get all scenarios' recommendations ranked by priority."""
        priority_order = {"CRITICAL": 0, "IMPORTANT": 1, "OPTIONAL": 2}
        recs = [s.recommendation for s in self.scenarios if s.recommendation]
        return sorted(recs, key=lambda r: priority_order.get(r.priority, 9))

    def format_full(self) -> str:
        if not self.scenarios:
            return ""
        lines = ["STRUCTURAL SENSITIVITY (what changes if assumptions are off):"]
        lines.append("")
        for s in self.scenarios:
            lines.append(f"  {s.driver_name} — currently {s.base_value}")
            lines.append(f"    Scenario: {s.scenario_label} ({s.scenario_change_pct:+.0f}%)")
            lines.append(f"    Structural impact: {s.structural_impact}")
            if s.cost_impact_rupees != 0:
                impact_lakhs = s.cost_impact_rupees / 100_000
                sign = "+" if impact_lakhs > 0 else ""
                lines.append(f"    Cost impact: {sign}₹{impact_lakhs:.2f}L")
            lines.append(f"    What you can do: {s.user_action}")
            # v0.7: show recommendation with priority badge
            if s.recommendation:
                badge = f"[{s.recommendation.priority}]"
                lines.append(
                    f"    {badge} {s.recommendation.action_verb}: "
                    f"{s.recommendation.action_text}"
                )
            lines.append("")
        return "\n".join(lines)

    def format_recommendations_only(self) -> str:
        """v0.7: compressed recommendations-only view for decision-makers."""
        recs = self.top_recommendations
        if not recs:
            return ""
        lines = ["TOP RECOMMENDATIONS (ranked by priority):"]
        for r in recs:
            lines.append(f"  [{r.priority}] {r.action_verb}: {r.action_text}")
            lines.append(f"     Why: {r.threshold_basis}")
        return "\n".join(lines)


def compute_structural_sensitivity(
    actual_soil_sbc_t_sqm: float,
    actual_foundation_type: str,
    actual_column_load_kn: float,
    actual_column_size_mm: int,
    actual_total_cost_rupees: float,
    actual_longest_span_m: float = 4.0,       # v0.6: span sensitivity
    actual_concrete_grade: str = "M25",       # v0.6: material sensitivity
    actual_steel_grade: str = "Fe500",        # v0.6: material sensitivity
) -> StructuralSensitivityReport:
    """Compute structural sensitivity scenarios.

    For each driver, generate a "what-if-this-were-different" scenario
    showing how the design and cost would change.

    v0.6: Extended from 2 drivers (soil, load) to 4 drivers by adding
    span + material grade per the v0.5 review recommendation.
    """
    scenarios: list[StructuralSensitivityScenario] = []

    # ─── Driver 1: soil bearing capacity ────────────────────────────────
    # Most common surprise: actual soil tests weaker than typical assumption.
    weak_soil_sbc = actual_soil_sbc_t_sqm * 0.7  # 30% weaker
    scenarios.append(_soil_sensitivity_scenario(
        actual_soil_sbc_t_sqm, weak_soil_sbc,
        actual_foundation_type, actual_total_cost_rupees,
    ))

    # ─── Driver 2: column load ──────────────────────────────────────────
    # Common variation: heavier finishes, water tank moved to edge column,
    # neighbor adds upper floor that increases tributary load.
    heavier_load = actual_column_load_kn * 1.20  # 20% heavier
    scenarios.append(_load_sensitivity_scenario(
        actual_column_load_kn, heavier_load,
        actual_column_size_mm, actual_total_cost_rupees,
    ))

    # ─── Driver 3 (v0.6): span variation ────────────────────────────────
    # If user wants column-free hall / larger rooms, span grows.
    scenarios.append(_span_sensitivity_scenario(
        actual_longest_span_m, actual_longest_span_m * 1.20,
        actual_column_size_mm, actual_total_cost_rupees,
    ))

    # ─── Driver 4 (v0.6): material grade ────────────────────────────────
    # Upgrading concrete and steel grade changes column section + cost.
    scenarios.append(_material_grade_sensitivity_scenario(
        actual_concrete_grade, actual_steel_grade,
        actual_column_size_mm, actual_total_cost_rupees,
    ))

    return StructuralSensitivityReport(scenarios=tuple(scenarios))


def _soil_sensitivity_scenario(
    actual_sbc: float, weaker_sbc: float,
    current_foundation: str, current_total_cost: float,
) -> StructuralSensitivityScenario:
    """If soil tests weaker than assumed, what changes?"""
    # If weak enough, foundation upgrades
    if weaker_sbc < 6.0:
        # Would trigger pile if not already
        if current_foundation != "pile":
            impact = "Foundation upgrades to PILE (was {}).".format(current_foundation)
            cost_impact = current_total_cost * 0.20  # ~20% increase
        else:
            impact = "Already pile foundation; pile size may increase."
            cost_impact = current_total_cost * 0.05
    elif weaker_sbc < 8.0:
        if current_foundation == "isolated":
            impact = "Foundation upgrades from ISOLATED to RAFT (footings get too large)."
            cost_impact = current_total_cost * 0.10
        elif current_foundation == "combined":
            impact = "Foundation upgrades from COMBINED to RAFT."
            cost_impact = current_total_cost * 0.06
        else:
            impact = f"Foundation type stays {current_foundation}; footings get larger."
            cost_impact = current_total_cost * 0.03
    else:
        impact = f"Foundation type stays {current_foundation}; minor footing increase."
        cost_impact = current_total_cost * 0.02

    # v0.7: action-layer recommendation
    cost_threshold_lakhs = cost_impact / 100_000
    if weaker_sbc < 6.0:
        rec = Recommendation(
            action_verb="Get soil test BEFORE finalising design",
            action_text=(
                f"Pile foundation may add ₹{cost_threshold_lakhs:.1f}L — "
                f"a ₹20K soil test now prevents a surprise 20× bigger."
            ),
            threshold_basis="SBC < 6 T/sqm triggers pile upgrade",
            priority="CRITICAL",
        )
    elif weaker_sbc < 8.0:
        rec = Recommendation(
            action_verb="Budget for contingency",
            action_text=(
                f"Keep ₹{cost_threshold_lakhs:.1f}L in foundation contingency. "
                f"Get soil test before excavation to confirm."
            ),
            threshold_basis="SBC 6-8 T/sqm triggers foundation upgrade",
            priority="IMPORTANT",
        )
    else:
        rec = Recommendation(
            action_verb="Get soil test (standard practice)",
            action_text=(
                "Soil test (~₹15-25K) confirms assumptions. "
                "Minor footing size adjustment may be needed."
            ),
            threshold_basis="SBC > 8 T/sqm = adequate; minor adjustment only",
            priority="OPTIONAL",
        )

    return StructuralSensitivityScenario(
        driver_name="Soil bearing capacity",
        base_value=f"{actual_sbc:.0f} T/sqm (city-typical assumed)",
        scenario_label=f"If soil tests as {weaker_sbc:.0f} T/sqm",
        scenario_change_pct=-30.0,
        structural_impact=impact,
        cost_impact_rupees=cost_impact,
        user_action=(
            "Get a soil test (~₹15-25K) before construction. If results "
            "match our assumption, no change. If weaker, plan for above "
            "cost increase in your contingency budget."
        ),
        recommendation=rec,
    )


def _load_sensitivity_scenario(
    actual_load: float, heavier_load: float,
    current_column_size_mm: int, current_total_cost: float,
) -> StructuralSensitivityScenario:
    """If column load is heavier than estimated, what changes?"""
    # 20% heavier load typically means column size goes up by one tier (50mm)
    # and footings grow proportionally
    next_column_size = current_column_size_mm + 50
    impact = (
        f"Columns may need to grow from {current_column_size_mm}mm to "
        f"{next_column_size}mm. Footings grow ~10%. Concrete/steel "
        f"quantities increase ~12%."
    )
    cost_impact = current_total_cost * 0.05  # ~5% structural cost increase

    # v0.7: action-layer recommendation
    rec = Recommendation(
        action_verb=f"Keep finishes under {actual_load*1.1:.0f} kN/column equivalent",
        action_text=(
            f"If adding heavy finishes (Italian marble, false ceiling, "
            f"water tank relocation), +20% load triggers a column size "
            f"tier jump (+50mm), adding ₹{cost_impact/100_000:.1f}L. "
            f"Confirm final finishes now, not after casting."
        ),
        threshold_basis=f"Column size tier boundary at ~{actual_load*1.2:.0f} kN",
        priority="IMPORTANT",
    )

    return StructuralSensitivityScenario(
        driver_name="Column axial load",
        base_value=f"{actual_load:.0f} kN factored (estimated)",
        scenario_label=f"If actual load is 20% heavier ({heavier_load:.0f} kN)",
        scenario_change_pct=+20.0,
        structural_impact=impact,
        cost_impact_rupees=cost_impact,
        user_action=(
            "Common reasons for heavier-than-estimated load: heavier "
            "finishes (Italian marble vs vitrified), additional floor in "
            "future, water tank relocation. Plan structure for heaviest "
            "likely scenario, not just current brief."
        ),
        recommendation=rec,
    )


def _span_sensitivity_scenario(
    actual_span_m: float, larger_span_m: float,
    current_column_size_mm: int, current_total_cost: float,
) -> StructuralSensitivityScenario:
    """v0.6: If user wants larger spans (column-free hall, bigger rooms).

    Span increase cascades through design:
      +10% span → beam depth up ~10% (beam moment scales with L²)
      +20% span → beam depth jumps one size (350mm → 450mm typical)
      Slabs: span:depth ratio ~ 30 for residential → thicker slab
      Columns: tributary area grows, column size up 50mm typical
    """
    span_increase_pct = ((larger_span_m - actual_span_m) / actual_span_m) * 100

    if span_increase_pct >= 20:
        impact = (
            f"Beam depth likely jumps from 350mm to 450mm. "
            f"Slab thickness +25-30mm. Columns may grow 50mm. "
            f"Concrete +12%, steel +15%."
        )
        cost_impact = current_total_cost * 0.08
    elif span_increase_pct >= 10:
        impact = (
            f"Beam depth grows ~10%. Slab marginally thicker. "
            f"Columns may stay same. Concrete +5-7%, steel +6-8%."
        )
        cost_impact = current_total_cost * 0.04
    else:
        impact = (
            f"Minor impact — beam/slab/column sizes likely unchanged. "
            f"Slight increase in reinforcement."
        )
        cost_impact = current_total_cost * 0.01

    # v0.7: action-layer recommendation — threshold-based
    # Beam depth typically jumps at ~4m span for residential UDL.
    # Cost jump is significant (+8% total) at 20% span increase.
    comfort_span_m = 4.0  # Industry rule-of-thumb for residential RC
    if actual_span_m < comfort_span_m and larger_span_m >= comfort_span_m:
        rec = Recommendation(
            action_verb=f"Keep longest span under {comfort_span_m:.1f}m",
            action_text=(
                f"Span increase from {actual_span_m:.1f}m to {larger_span_m:.1f}m "
                f"crosses the residential beam-depth tier boundary. "
                f"Cost jump ~₹{cost_impact/100_000:.1f}L. If you need a "
                f"column-free hall, accept this cost now — retrofitting later "
                f"is 5-10× more expensive."
            ),
            threshold_basis=(
                f"Beam depth jumps at span ≈ {comfort_span_m:.1f}m for "
                f"residential UDL — tier boundary in sizing rules"
            ),
            priority="IMPORTANT",
        )
    elif span_increase_pct >= 20:
        rec = Recommendation(
            action_verb="Lock span early",
            action_text=(
                f"Large span changes drive beam depth + slab thickness + "
                f"column size. Finalise layout before concrete — late "
                f"changes add ~₹{cost_impact/100_000:.1f}L."
            ),
            threshold_basis="20%+ span increase triggers cascading size changes",
            priority="IMPORTANT",
        )
    else:
        rec = Recommendation(
            action_verb="Minor span flexibility available",
            action_text=(
                f"Span changes under 10% have negligible structural "
                f"impact (~₹{cost_impact/100_000:.2f}L). Layout can be "
                f"adjusted during design without significant cost."
            ),
            threshold_basis="<10% span change = within member capacity margins",
            priority="OPTIONAL",
        )

    return StructuralSensitivityScenario(
        driver_name="Longest span",
        base_value=f"{actual_span_m:.1f}m (current layout)",
        scenario_label=f"If longest span increases to {larger_span_m:.1f}m",
        scenario_change_pct=round(span_increase_pct, 0),
        structural_impact=impact,
        cost_impact_rupees=cost_impact,
        user_action=(
            "If you want a larger column-free hall or bigger living room, "
            "tell the engineer BEFORE final design — adding span after "
            "columns are cast is very expensive. Typical residential "
            "max span comfortable for cost is 4-4.5m."
        ),
        recommendation=rec,
    )


def _material_grade_sensitivity_scenario(
    current_concrete_grade: str, current_steel_grade: str,
    current_column_size_mm: int, current_total_cost: float,
) -> StructuralSensitivityScenario:
    """v0.6: Material grade upgrade sensitivity.

    Upgrading M25→M30 concrete + Fe500→Fe550 steel:
      - Allows smaller column sections (~25mm less)
      - OR allows higher floors with same section
      - Concrete rate +10%, steel rate +5%
      - Net cost: roughly flat for G+1, marginally up for G+2+
    """
    # Upgrade path: M25 → M30, Fe500 → Fe550
    target_concrete = "M30" if current_concrete_grade == "M25" else current_concrete_grade
    target_steel = "Fe550" if current_steel_grade == "Fe500" else current_steel_grade

    if target_concrete == current_concrete_grade and target_steel == current_steel_grade:
        # Already at highest grades in our KB — can't upgrade further
        impact = (
            f"Already using high-grade materials ({current_concrete_grade}, "
            f"{current_steel_grade}). Further upgrade not supported in our "
            f"KB — consult engineer for high-strength options."
        )
        cost_impact = 0.0
        scenario_label = f"Material grade at max ({current_concrete_grade}/{current_steel_grade})"
        pct = 0.0
    else:
        impact = (
            f"Upgrade to {target_concrete} concrete + {target_steel} steel: "
            f"column section could reduce ~25mm, freeing up internal space. "
            f"Material cost +8%, but smaller columns partially offset."
        )
        cost_impact = current_total_cost * 0.03   # Net ~3% increase
        scenario_label = f"Upgrade to {target_concrete} + {target_steel}"
        pct = 10.0

    # v0.7: action-layer recommendation for material grade
    if target_concrete == current_concrete_grade:
        rec = Recommendation(
            action_verb="No action needed",
            action_text=(
                "Already at M30/Fe550 — further upgrades have diminishing "
                "returns for residential. Focus on workmanship + curing."
            ),
            threshold_basis="Already at top-tier grades in our KB",
            priority="OPTIONAL",
        )
    else:
        rec = Recommendation(
            action_verb="Discuss grade upgrade with engineer",
            action_text=(
                f"Upgrading to {target_concrete}/{target_steel} costs "
                f"~₹{cost_impact/100_000:.2f}L but frees ~25mm column width "
                f"(more room space). Worth it if: planning future floors, "
                f"coastal/severe-climate site, or tight internal dimensions."
            ),
            threshold_basis=(
                "M30+Fe550 trade-off: +8% material cost, -25mm column width"
            ),
            priority="OPTIONAL",
        )

    return StructuralSensitivityScenario(
        driver_name="Material grade",
        base_value=f"{current_concrete_grade} concrete, {current_steel_grade} steel",
        scenario_label=scenario_label,
        scenario_change_pct=pct,
        structural_impact=impact,
        cost_impact_rupees=cost_impact,
        user_action=(
            "Higher-grade materials are typically worth the cost if you "
            "want more internal space, plan to add floors later, or are "
            "building in severe climate/seismic zones. Engineer decides "
            "final grade based on structural demand + long-term durability."
        ),
        recommendation=rec,
    )
