"""
BuildemUp† — Component 1: Brief Capture Engine (orchestrator)
==================================================================

This is the top-level Component 1. It takes user form input (or
equivalent programmatic input) and produces a validated Brief
domain object that downstream components (Component 4 layout,
Component 7 structural) consume via the ComponentContract system.

B-S53-C1-CONSOLIDATE resolution (S56, 2026-05-16): KEEP.
The S53 backlog filed this as "fold c01_brief_capture.py into c01/."
On audit in S56 the layout mirrors C7's: this top-level file is the
canonical Component-1 orchestrator; the `c01/` sub-package contains
modular sub-components (budget_bridge, parking_feasibility,
phased_construction, room_composer, setback_calculator,
assumptions_log, vastu_filter, soft_guide_engine) that this
orchestrator composes. The two are complementary, not duplicative.
36+ importers across api/, domain/, examples/, and tests/ correctly
use `buildemup.components.c01_brief_capture` as the entry point.
Same KEEP decision as B-S53-C7-LEGACY-DECISION for the parallel
C7 layout. No action required.

PIPELINE (per SPEC_v0.2 Section 10):
  1. Parse + validate user form input  → domain objects
  2. Compute NBC/DCR-compliant setbacks (plot-type branched)
  3. Check user-stated vs compliant setbacks
  4. Apply default room templates if user didn't specify floors
  5. Enforce auto-staircase (Drawback 8)
  6. Check parking feasibility (Drawback 7)
  7. Generate vastu guidance (OFF/PARTIAL/FULL per user tier)
  8. Call Component 7 via budget bridge (Drawback 4 single source)
  9. Compare budget to estimate; suggest phased construction if needed
  10. Aggregate all guidance; compute top 3 (Drawback 6)
  11. Build assumptions list (Drawback 10)
  12. Assemble + return Brief

FAILURE MODES:
  - Invalid domain input → ValueError (caught at form-validator layer)
  - Component 7 fails → bridge returns None + CONCERN message, we
    continue with a budget-comparison-skipped Brief
  - Vastu guidance never fails (it's read-only lookup)

This orchestrator NEVER refuses to produce a Brief. Even with many
STRONG_CONCERN issues, it returns a valid Brief with
ready_for_downstream=False so the user sees the concerns and can
choose to adjust or override.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from buildemup.domain.plot import Plot, PlotType
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import (
    FloorRequirement, FloorUse, RoomType,
)
from buildemup.domain.brief import (
    Brief, BudgetRange, CostEstimate,
    GuidanceMessage, GuidanceSeverity,
    ComplianceSummary, VastuTier,
)

from buildemup.components.c01.setback_calculator import (
    compute_compliant_setbacks, check_setback_compliance,
)
from buildemup.components.c01.room_composer import (
    ensure_staircase_present, estimate_total_built_area_sqm,
    estimate_total_built_area_sqft,
    get_circulation_factor_label_for_floors,
)
from buildemup.components.c01.parking_feasibility import (
    check_parking_feasibility,
)
from buildemup.components.c01.vastu_filter import (
    generate_vastu_guidance, VASTU_PARTIAL_ITEMS,
)
from buildemup.components.c01.budget_bridge import (
    call_component_7_for_cost, compare_budget_to_estimate,
)
from buildemup.components.c01.phased_construction import (
    suggest_phased_construction_if_needed,
)
from buildemup.components.c01.soft_guide_engine import (
    compute_top_guidance, merge_guidance_sources, has_strong_concerns,
    count_by_severity, compute_risk_level,
    compute_risk_drivers, group_guidance_by_category,
)
from buildemup.components.c01.assumptions_log import build_assumptions_list

from buildemup.utils.component_contract import (
    ComponentContract, register_contract, required, optional,
)
from buildemup.utils.logging import new_trace_id
from buildemup.utils.legal_disclosures import format_legal_disclosures_block


# ─────────────────────────────────────────────────────────────────────────
# Input + Output dataclasses
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class BriefCaptureInput:
    """Input contract for Component 1.

    This is the "form input" shape — primitives matching what a web
    form or JSON API would send. The orchestrator converts this into
    domain objects (Plot, Setbacks, etc.) inside execute().

    Note: per v0.7.1 domain enforcement, we declare primitives here
    NOT domain objects — because this IS the ingestion layer. Domain
    enforcement kicks in for DOWNSTREAM components consuming the Brief.
    """
    # Plot
    plot_width_m: float
    plot_depth_m: float
    plot_facing: str                       # "N", "NE", "E", etc.
    city: str                              # "chennai", "mumbai", etc.
    road_width_m: float
    plot_type: str = "detached"            # "detached"/"semi_detached"/"continuous"
    corner_plot: bool = False
    second_road_width_m: float | None = None
    shared_side: str | None = None         # "left"/"right" if semi_detached

    # Setbacks (user-stated)
    user_setback_front_m: float = 1.5
    user_setback_rear_m: float = 1.5
    user_setback_side_left_m: float = 1.5
    user_setback_side_right_m: float = 1.5

    # Floors — tuple of FloorRequirement (already domain objects, can't
    # practically round-trip tuples of domain through a form — this is
    # where we draw the line on primitives).
    floors: tuple[FloorRequirement, ...] = ()

    # Budget
    budget_min_lakhs: int = 15
    budget_max_lakhs: int = 25

    # Optional
    additional_requirements: tuple[str, ...] = ()
    soil_type_known: str | None = None
    vastu_preference: str = "off"           # "off"/"partial"/"full"
    user_email: str | None = None
    user_phone: str | None = None
    resume_token: str | None = None


@dataclass(frozen=True)
class BriefCaptureOutput:
    """Output contract for Component 1.

    The Brief domain object is the primary payload. Everything else
    is supporting metadata that explain() uses to render the output.

    v0.9 change (Drawback #8 fix):
      - "ready_for_downstream" (bool) replaced with two clearer signals:
        * proceed_with_warnings (bool) — True when downstream can run
          (the handshake with Component 4/7 is valid) but may produce
          warnings. Always True for v0.1 — we never block.
        * risk_level (str) — "LOW" / "MEDIUM" / "HIGH" based on
          severity of guidance messages. This is the honest signal
          about whether the plan looks sound.
    """
    brief: Brief
    soft_guidance: tuple[GuidanceMessage, ...]
    top_guidance: tuple[GuidanceMessage, ...]
    compliance_summary: ComplianceSummary
    assumptions_used: tuple[str, ...]
    c7_preview_cost: CostEstimate | None
    trace_id: str
    kb_versions: dict[str, str]
    proceed_with_warnings: bool            # was: ready_for_downstream
    risk_level: str                        # NEW: LOW / MEDIUM / HIGH
    resume_token: str | None = None

    # Form input echoed for transparency
    total_built_area_sqm: float = 0.0
    total_built_area_sqft: float = 0.0

    # Net usable area after efficiency factor (Drawback #3 fix)
    envelope_width_m: float = 0.0
    envelope_depth_m: float = 0.0
    gross_envelope_sqm: float = 0.0
    net_usable_sqm: float = 0.0

    # v0.9.1 Drawback #3: net usable as RANGE (80-90%) not single number
    net_usable_low_sqm: float = 0.0     # 80% of gross
    net_usable_high_sqm: float = 0.0    # 90% of gross

    # Circulation factor actually applied (Drawback #5 fix)
    circulation_factor_applied: float = 1.35
    circulation_size_label: str = "typical"

    # v0.9.1 Drawback #8: explain WHY risk_level is what it is
    risk_drivers: tuple[str, ...] = ()

    # v0.9.1 Drawback #9: messages grouped by category for UI sectioning
    # Computed lazily — populated in execute() after soft_guidance built
    soft_guidance_by_category: dict[str, tuple] = field(default_factory=dict)

    # --- DEPRECATED ALIAS (will be removed in v1.0) ---
    @property
    def ready_for_downstream(self) -> bool:
        """DEPRECATED: use proceed_with_warnings + risk_level instead.

        Retained as a property for one release cycle so external
        callers don't break immediately. A DeprecationWarning in v1.0
        will precede full removal.
        """
        # Old behaviour: False when STRONG_CONCERN present
        return self.risk_level != "HIGH"


# ─────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────
class BriefCaptureEngine:
    """Top-level Component 1 orchestrator.

    Usage:
        engine = BriefCaptureEngine()
        output = engine.execute(BriefCaptureInput(...))
        rendering = engine.explain(input, output)
    """

    def execute(self, inp: BriefCaptureInput) -> BriefCaptureOutput:
        """Run the full Component 1 pipeline on user input.

        Pipeline:
          1. Parse primitives into domain objects
          2. Compute compliant setbacks
          3. Check compliance (soft-guide messages)
          4. Auto-staircase (Drawback 8)
          5. Parking feasibility (Drawback 7)
          6. Vastu guidance
          7. Call Component 7 for cost (Drawback 4)
          8. Budget comparison + phased construction suggestion
          9. Aggregate + prioritise guidance (Drawback 6)
          10. Build assumptions list (Drawback 10)
          11. Assemble Brief + output
        """
        trace_id = new_trace_id()

        # Step 1 — Parse primitives into domain objects
        plot = self._build_plot(inp)
        user_setbacks = Setbacks(
            front_m=inp.user_setback_front_m,
            rear_m=inp.user_setback_rear_m,
            side_left_m=inp.user_setback_side_left_m,
            side_right_m=inp.user_setback_side_right_m,
        )
        budget = BudgetRange(
            min_lakhs=inp.budget_min_lakhs,
            max_lakhs=inp.budget_max_lakhs,
        )
        vastu_tier = self._parse_vastu_tier(inp.vastu_preference)

        # Step 2 — Compute compliant setbacks
        floor_count = max(1, len(inp.floors))
        building_height_m = 3.0 * floor_count    # 3m per floor standard
        nbc_setbacks, source_authority = compute_compliant_setbacks(
            plot, building_height_m=building_height_m,
        )

        # Whether we used the NBC fallback (for assumptions disclosure)
        used_nbc_fallback = "NBC 2016" in source_authority

        # Step 3 — Check setback compliance
        is_compliant, violations = check_setback_compliance(
            user_setbacks, nbc_setbacks,
        )
        setback_msgs = self._setback_messages(
            is_compliant, violations, source_authority,
        )

        # Step 4 — Auto-staircase (Drawback 8)
        floors_tuple: tuple[FloorRequirement, ...] = inp.floors or ()
        floors_tuple, staircase_msgs = ensure_staircase_present(floors_tuple)
        auto_staircase_was_added = len(staircase_msgs) > 0

        # Step 5 — Parking feasibility (Drawback 7)
        has_stilt = any(
            f.floor_use == FloorUse.STILT_PARKING for f in floors_tuple
        )
        parking_msgs = check_parking_feasibility(
            plot_width_m=plot.width_m,
            plot_depth_m=plot.depth_m,
            has_stilt_parking=has_stilt,
            side_left_setback_m=nbc_setbacks.side_left_m,
            side_right_setback_m=nbc_setbacks.side_right_m,
        )

        # Step 6 — Vastu guidance
        vastu_msgs = generate_vastu_guidance(plot, vastu_tier)

        # Step 7 — Assemble preliminary Brief (pre-C7) so budget bridge
        # can compute cost. We'll re-assemble with final guidance at end.
        preliminary_brief = Brief(
            plot=plot,
            user_stated_setbacks=user_setbacks,
            nbc_compliant_setbacks=nbc_setbacks,
            floors=floors_tuple,
            budget_range=budget,
            additional_requirements=inp.additional_requirements,
            vastu_preference=vastu_tier,
            user_email=inp.user_email,
            user_phone=inp.user_phone,
            resume_token=inp.resume_token,
            trace_id=trace_id,
        )

        # Step 8 — Call Component 7 for cost (Drawback 4)
        c7_cost, bridge_msgs = call_component_7_for_cost(preliminary_brief)

        # Step 9 — Budget comparison + phased construction
        budget_msgs = compare_budget_to_estimate(budget, c7_cost) if c7_cost else []
        phased_msgs = suggest_phased_construction_if_needed(budget, c7_cost)

        # Step 10 — Aggregate + prioritise guidance
        # Order matters: compliance → feasibility → budget → phased →
        # staircase info → vastu → bridge errors (if any)
        all_guidance = merge_guidance_sources(
            setback_msgs,
            parking_msgs,
            budget_msgs,
            phased_msgs,
            staircase_msgs,
            vastu_msgs,
            bridge_msgs,
        )
        top_guidance = compute_top_guidance(all_guidance, n=3)
        risk_level = compute_risk_level(all_guidance)
        # proceed_with_warnings=True always — we never block in v0.1.
        # The meaningful signal is risk_level.
        proceed_with_warnings = True

        # Step 11 — Build assumptions list (Drawback 10)
        # Capture circulation factor used (Drawback #5 v0.9 fix)
        cf_applied, cf_label = get_circulation_factor_label_for_floors(floors_tuple)
        # v0.9.1 Drawback #6: pass KB version + authority for audit trail
        kb_versions = self._collect_kb_versions()
        assumptions = build_assumptions_list(
            plot_type_label=plot.plot_type.value,
            vastu_tier_label=vastu_tier.value,
            city=plot.city,
            used_nbc_fallback=used_nbc_fallback,
            auto_staircase_added=auto_staircase_was_added,
            circulation_factor_applied=cf_applied,
            circulation_size_label=cf_label,
            setback_rules_version=kb_versions.get("setback_rules", "unknown"),
            setback_authority=source_authority,
        )

        # Step 12 — Final Brief assembly (with guidance populated)
        final_brief = Brief(
            plot=plot,
            user_stated_setbacks=user_setbacks,
            nbc_compliant_setbacks=nbc_setbacks,
            floors=floors_tuple,
            budget_range=budget,
            additional_requirements=inp.additional_requirements,
            soft_guidance=all_guidance,
            top_guidance=top_guidance,
            vastu_preference=vastu_tier,
            user_email=inp.user_email,
            user_phone=inp.user_phone,
            resume_token=inp.resume_token,
            assumptions_used=assumptions,
            trace_id=trace_id,
            kb_versions=self._collect_kb_versions(),
        )

        compliance = ComplianceSummary(
            is_setback_compliant=is_compliant,
            setback_violations=violations,
            source_authority=source_authority,
        )

        # Compute envelope + net usable area (Drawback #3 v0.9 fix)
        # Per SPEC Section 10.1: envelope = plot - setbacks, min 5m floor.
        # Efficiency factor 0.85 captures column grid + unusable corners
        # + structural deductions that the gross envelope doesn't.
        # v0.9.1 Drawback #3: also compute 80% / 90% bounds as range.
        gross_env_w = max(5.0, plot.width_m - nbc_setbacks.side_left_m
                          - nbc_setbacks.side_right_m)
        gross_env_d = max(5.0, plot.depth_m - nbc_setbacks.front_m
                          - nbc_setbacks.rear_m)
        gross_env_sqm = gross_env_w * gross_env_d
        net_usable_sqm = gross_env_sqm * 0.85
        net_usable_low_sqm = gross_env_sqm * 0.80
        net_usable_high_sqm = gross_env_sqm * 0.90

        # v0.9.1 Drawback #8: compute risk drivers explaining WHY risk_level
        risk_drivers = compute_risk_drivers(all_guidance, risk_level)

        # v0.9.1 Drawback #9: group guidance by category
        soft_guidance_by_category = group_guidance_by_category(all_guidance)

        return BriefCaptureOutput(
            brief=final_brief,
            soft_guidance=all_guidance,
            top_guidance=top_guidance,
            compliance_summary=compliance,
            assumptions_used=assumptions,
            c7_preview_cost=c7_cost,
            trace_id=trace_id,
            kb_versions=self._collect_kb_versions(),
            proceed_with_warnings=proceed_with_warnings,
            risk_level=risk_level,
            resume_token=inp.resume_token,
            total_built_area_sqm=estimate_total_built_area_sqm(floors_tuple),
            total_built_area_sqft=estimate_total_built_area_sqft(floors_tuple),
            envelope_width_m=gross_env_w,
            envelope_depth_m=gross_env_d,
            gross_envelope_sqm=gross_env_sqm,
            net_usable_sqm=net_usable_sqm,
            net_usable_low_sqm=net_usable_low_sqm,
            net_usable_high_sqm=net_usable_high_sqm,
            circulation_factor_applied=cf_applied,
            circulation_size_label=cf_label,
            risk_drivers=risk_drivers,
            soft_guidance_by_category=soft_guidance_by_category,
        )

    def explain(
        self, inp: BriefCaptureInput, output: BriefCaptureOutput,
    ) -> str:
        """Produce human-readable rendering of a Brief.

        Renders all sections per SPEC_v0.2 Section 10.3:
          - Top 3 Recommendations (NEW per Drawback 6)
          - Plot info + plot type (NEW per Drawback 1)
          - Setbacks comparison
          - Floor composition + total built area
          - Budget vs C7 estimate (NEW per Drawback 4)
          - Vastu guidance (if opted in)
          - Complete soft guidance
          - Assumptions used (NEW per Drawback 10)
          - Next steps
          - Legal disclosures (v0.6 mandatory block)
          - Reproducibility
        """
        brief = output.brief
        plot = brief.plot
        lines: list[str] = []

        _sep = "═" * 70
        _line = "─" * 70

        lines.append(_sep)
        lines.append(f"YOUR BRIEF — captured for {plot.city.title()}")
        lines.append(_sep)

        # v0.9.1 Drawback #14: position this output honestly in the journey
        lines.append("")
        lines.append(
            "  This is STEP 1 OF 6 in your build journey:"
        )
        lines.append(
            "    [1] Brief Capture (this output) →"
        )
        lines.append(
            "    [2] Feasibility check  [3] Layout generation  "
            "[4] Structural design"
        )
        lines.append(
            "    [5] MEP & finishes     [6] Procurement & "
            "contractor selection"
        )
        lines.append(
            "  Treat what follows as DIRECTIONAL planning input — not a "
            "final design or quote."
        )
        # v0.9.2 Drawback #6: explicit next-step CTA so users know what's next
        lines.append(
            "  → Next: Component 2 (Feasibility) will check whether your "
            "plan is actually possible on this plot."
        )
        # v0.9.2 Drawback #13: explicit "does NOT replace" line — users
        # often misread system completeness. Be blunt about scope.
        lines.append("")
        lines.append(
            "  ⚠ This output does NOT replace architect-led layout design, "
            "structural engineering drawings, or municipal plan approval. "
            "It is a planning aid for early-stage decisions only."
        )
        # v0.9.2 Drawback #15: surface the engineering-model dependency
        lines.append(
            "  Structural cost estimate powered by Component 7 — the "
            "BuildemUp engineering model (NBC + IS 456/875/1893 codes, "
            "city-specific material rates)."
        )

        # Top 3 Recommendations with cumulative summary (Drawback #9 v0.9 fix)
        if output.top_guidance:
            total_count = len(output.soft_guidance)
            sev_counts = count_by_severity(output.soft_guidance)
            n_strong = sev_counts.get(GuidanceSeverity.STRONG_CONCERN, 0)
            n_concern = sev_counts.get(GuidanceSeverity.CONCERN, 0)
            n_info = sev_counts.get(GuidanceSeverity.INFO, 0)

            lines.append("")
            lines.append(_line)
            lines.append("TOP 3 RECOMMENDATIONS — please review these first")
            lines.append(_line)
            # Drawback #9 fix: Summary line shows cumulative count so users
            # don't miss that there are more items below the top 3
            lines.append(
                f"  Showing top {len(output.top_guidance)} of {total_count} "
                f"total recommendations "
                f"({n_strong} critical, {n_concern} concerns, "
                f"{n_info} info items)"
            )
            lines.append("")
            for i, m in enumerate(output.top_guidance, start=1):
                lines.append(
                    f"  {i}. [{m.severity.value.upper()}] {m.text}"
                )
            # Risk level banner (Drawback #8 v0.9 fix) + drivers (v0.9.1 fix)
            # v0.9.2 Drawback #3: plain-language tails (LOW alone tested as
            # "safe" by users; explicit qualifier prevents that read).
            lines.append("")
            risk_label = {
                "LOW": "LOW (minor issues, plan looks sound)",
                "MEDIUM": (
                    "MEDIUM (review recommended — concerns worth addressing)"
                ),
                "HIGH": (
                    "HIGH (likely design changes needed before proceeding)"
                ),
            }.get(output.risk_level, output.risk_level)
            lines.append(f"  Overall risk level: {risk_label}")
            # v0.9.1: explain WHY the risk level is what it is
            # v0.9.2 Drawback #4: elevate the FIRST driver as "BIGGEST ISSUE"
            # so users don't miss the most important one in a list of 3-5.
            if output.risk_drivers:
                if output.risk_level in ("MEDIUM", "HIGH") and output.risk_drivers:
                    # Surface the most critical driver prominently
                    lines.append(
                        f"  ★ BIGGEST ISSUE: {output.risk_drivers[0]}"
                    )
                lines.append("  Why:")
                for driver in output.risk_drivers:
                    lines.append(f"    • {driver}")

        # Plot info
        lines.append("")
        lines.append(_line)
        lines.append("PLOT")
        lines.append(_line)
        lines.append(f"  Dimensions: {plot.width_m}m × {plot.depth_m}m "
                     f"({plot.area_sqm:.0f} sqm = {plot.area_sqft:.0f} sqft)")
        lines.append(f"  Facing: {plot.facing.value}")
        lines.append(f"  Plot type: {plot.plot_type.value}")
        lines.append(f"  Road width: {plot.road_width_m}m")
        if plot.corner_plot:
            lines.append(f"  Corner plot — second road: "
                         f"{plot.second_road_width_m}m")
        # Envelope disclosure — Drawback #3 v0.9 fix: show TWO numbers
        # (gross envelope vs net usable), transparent about the 85% factor.
        lines.append("")
        lines.append(f"  Gross envelope (plot − setbacks): "
                     f"{output.envelope_width_m:.1f}m × "
                     f"{output.envelope_depth_m:.1f}m = "
                     f"{output.gross_envelope_sqm:.0f} sqm "
                     f"({output.gross_envelope_sqm * 10.7639:.0f} sqft)")
        lines.append(f"  Net usable (80-90% typical, after columns + "
                     f"stairs + corners):")
        lines.append(
            f"    ~{output.net_usable_low_sqm:.0f}-"
            f"{output.net_usable_high_sqm:.0f} sqm "
            f"(~{output.net_usable_low_sqm * 10.7639:.0f}-"
            f"{output.net_usable_high_sqm * 10.7639:.0f} sqft)"
        )
        lines.append(f"    [Final layout (Component 4) determines actual "
                     f"usability — varies by column grid and design]")
        # v0.9.2 Drawback #8 partial: warn about poor-layout case so users
        # don't anchor on the midpoint as the floor.
        lines.append(
            f"    ⚠ Poor layout choices (excessive corridors, awkward "
            f"column grid, oversized circulation) can push effective "
            f"usability below 80%. The 80-90% range assumes a reasonably "
            f"efficient layout."
        )

        # Setbacks comparison
        lines.append("")
        lines.append(_line)
        lines.append("SETBACKS")
        lines.append(_line)
        lines.append(f"  Source authority: "
                     f"{output.compliance_summary.source_authority}")
        lines.append(f"  Compliance status: "
                     f"{'COMPLIANT ✓' if output.compliance_summary.is_setback_compliant else 'NON-COMPLIANT ✗'}")

        # v0.9 Session C: surface DCR disclosure if present (Mumbai, Delhi)
        # so users see caveats like "defaulted to SUBURBS" or
        # "verify with DDA" inline with the compliance check.
        try:
            from buildemup.utils.kb_rules_loader import (
                get_setback_rules_for_city,
            )
            city_rules = get_setback_rules_for_city(plot.city)
            disclosure = city_rules.get("_disclosure_text", "")
            if disclosure:
                lines.append("")
                lines.append(f"  ⚠ DCR disclosure: {disclosure}")
        except Exception:
            pass
        u = brief.user_stated_setbacks
        c = brief.nbc_compliant_setbacks
        lines.append("")
        lines.append("             Your input    Compliant    Difference")

        # Only show sides that matter for this plot type
        if plot.plot_type == PlotType.CONTINUOUS:
            sides_to_show = ["Front", "Rear"]
        else:
            sides_to_show = ["Front", "Rear", "Side (L)", "Side (R)"]

        def _fmt_row(label: str, u_val: float, c_val: float) -> str:
            diff = u_val - c_val
            diff_str = f"{diff:+.1f}" if diff != 0 else "  0.0"
            return f"    {label:10}  {u_val:>6.1f}m     {c_val:>6.1f}m     {diff_str}m"

        if "Front" in sides_to_show:
            lines.append(_fmt_row("Front:", u.front_m, c.front_m))
        if "Rear" in sides_to_show:
            lines.append(_fmt_row("Rear:", u.rear_m, c.rear_m))
        if "Side (L)" in sides_to_show:
            lines.append(_fmt_row("Side (L):", u.side_left_m, c.side_left_m))
        if "Side (R)" in sides_to_show:
            lines.append(_fmt_row("Side (R):", u.side_right_m, c.side_right_m))

        # Floor composition
        lines.append("")
        lines.append(_line)
        lines.append("FLOOR COMPOSITION")
        lines.append(_line)
        lines.append(f"  Total floors: G+{len(brief.floors) - 1}")
        for f in brief.floors:
            label = "Ground" if f.floor_number == 0 else f"Floor {f.floor_number}"
            if f.floor_number == len(brief.floors) - 1 and f.floor_use.value.startswith("terrace"):
                label = "Terrace"
            lines.append(f"  {label}: {f.floor_use.value.replace('_', ' ').title()}")
            if f.rooms:
                room_summary = ", ".join(
                    f"{r.count}× {r.room_type.value.replace('_', ' ').title()}"
                    for r in f.rooms
                )
                lines.append(f"    Rooms: {room_summary}")
        lines.append("")
        lines.append(f"  Total estimated built-up area: "
                     f"~{output.total_built_area_sqft:.0f} sqft "
                     f"({output.total_built_area_sqm:.1f} sqm)")
        lines.append(f"    [Circulation factor 1.30 applied — walls, "
                     f"passages, stairs included]")

        # Budget (Drawback #4 single source + #2 v0.9 fix: range framing)
        lines.append("")
        lines.append(_line)
        lines.append("BUDGET")
        lines.append(_line)
        lines.append(f"  Your range: {brief.budget_range.describe()}")
        # v0.9.3.1 consolidation fix (post-v0.9.3 review):
        # Combines drawback #3 (multiplier opacity), #4 (Mumbai/Delhi
        # under review), and #7 (data freshness warning) in one line.
        # Rest of v0.9.3 review intentionally not implemented — reviewer
        # said "system is solid, build Component 2 next."
        lines.append(
            "    [City cost adjustment is a market-based estimate "
            "reflecting labour, material, and contractor ecosystem "
            "differences. Mumbai + Delhi under review for next update. "
            "Rates reflect 2026 estimates — actual costs vary by "
            "locality, contractor, and material choice.]"
        )
        if output.c7_preview_cost:
            c7 = output.c7_preview_cost
            # v0.9.1 Drawback #1: lead with RANGE, exact in parens (smaller)
            low_l = c7.range_min / 100_000
            high_l = c7.range_max / 100_000
            exact_l = c7.exact_value / 100_000
            lines.append(
                f"  Structural estimate (Component 7): "
                f"₹{low_l:.1f}L–₹{high_l:.1f}L"
            )
            lines.append(
                f"    (most-likely point: ₹{exact_l:.1f}L | "
                f"confidence: {c7.confidence})"
            )
            lines.append(
                "    DO NOT TREAT AS A QUOTE — directional planning estimate only"
            )
            lines.append("")
            lines.append(
                "  The structural estimate covers foundation, frame, slab, "
                "and walls. It does NOT include:"
            )
            lines.append(
                "    • Finishes (tiles, paint, fittings): "
                "typically +30% to +100%"
            )
            lines.append(
                "    • Contractor margin: typically +8% to +20% by city"
            )
            lines.append(
                "    • MEP (plumbing, electrical, HVAC): "
                "typically +10% to +15%"
            )
            lines.append(
                "    • Interiors + furniture: highly variable, not included"
            )
            lines.append("")
            # v0.9.1 Drawback #2: replace "×1.5-2.0" heuristic with the
            # cited industry breakdown. Per AECORD 2026 + JK Cement +
            # construction industry guides for typical Indian residential:
            #   Structure 40% of total → all-in ≈ 2.5× structural
            #   (Finishing 25%, MEP 15%, Interior 12%, Misc 8%)
            # This corrects v0.9's understated ×1.5-2.0 heuristic.
            all_in_low = low_l * 2.0     # if structure is 50% (lean finishes)
            all_in_high = high_l * 3.0   # if structure is 33% (premium finishes)
            all_in_typical = exact_l * 2.5  # industry-typical 40% structure
            lines.append(
                f"  Typical ALL-IN cost (range observed, not guaranteed):"
            )
            lines.append(
                f"    ~₹{all_in_low:.0f}L–₹{all_in_high:.0f}L "
                f"(typical: ~₹{all_in_typical:.0f}L)"
            )
            lines.append(
                "  Industry breakdown of total residential cost "
                "(source: AECORD 2026, NBC industry guides):"
            )
            lines.append(
                "    Structure 40% (foundation + frame + slabs + walls)"
            )
            lines.append("    Finishing 25% (flooring, paint, doors, windows)")
            lines.append("    MEP 15% (plumbing, electrical, HVAC)")
            lines.append("    Interior 12% (woodwork, kitchen, fixtures)")
            lines.append(
                "    Misc 8% (approvals, soil testing, contingency, overhead)"
            )
            lines.append(
                "  This breakdown is OBSERVED INDUSTRY TYPICAL, not "
                "guaranteed. Premium finishes shift Structure share "
                "toward 30-35%; lean finishes can push it to 50%+."
            )
            lines.append("")
            lines.append("  What can change the structural number:")
            lines.append(
                "    • Soil test result (good soil: -15% | poor soil: +30%)"
            )
            lines.append(
                "    • Material prices during construction (±10%)"
            )
            lines.append(
                "    • Seismic zone (your zone is set per city)"
            )
            lines.append(
                "    • Actual column layout after Component 4 (±5%)"
            )
            # v0.9.2 Drawback #1: explicit overshoot stat from industry data.
            # Citable: 70-year multi-country study (Propeller Aero,
            # Cylinders Inc 2024) shows ~85% of construction projects
            # overshoot, with 15-30% typical. India-specific research
            # (Nature Sci Reports 2025 on Chennai residential cost overrun)
            # confirms the same range. Adding this is meaningful guard
            # against single-number anchoring.
            lines.append("")
            lines.append(
                "  ⚠ Industry reality: 85%+ of construction projects "
                "overshoot their initial estimates by 15-30% on average "
                "(source: 20-country, 70-year construction industry "
                "study; India-specific cost-overrun research confirms "
                "the same range). Plan for this — keep a 20% contingency "
                "above the typical all-in number."
            )
        else:
            lines.append("  Component 7 cost engine did not run for this brief "
                         "— budget comparison skipped.")

        # Vastu (if opted in) — Drawback #6 v0.9 fix: explicit cultural label
        if brief.vastu_preference != VastuTier.OFF:
            vastu_msgs = [
                m for m in brief.soft_guidance
                if m.context.startswith("vastu_")
            ]
            if vastu_msgs:
                lines.append("")
                lines.append(_line)
                lines.append(
                    f"VASTU GUIDANCE ({brief.vastu_preference.value.upper()} tier) "
                    f"— CULTURAL PREFERENCE, NOT A TECHNICAL REQUIREMENT"
                )
                lines.append(_line)
                lines.append(
                    "  These are cultural/traditional preferences. They are "
                    "NEVER building-code requirements and NEVER block your "
                    "design. Engineering and legal compliance take "
                    "precedence over any vastu item below."
                )
                # v0.9.1 Drawback #10: explicit conflict note
                lines.append(
                    "  Note: vastu items may conflict with optimal "
                    "structural and layout choices. When that happens, "
                    "engineering wins."
                )
                lines.append("")
                for m in vastu_msgs:
                    lines.append(f"  • {m.text}")

        # Complete soft guidance — grouped by category (v0.9.1 Drawback #9)
        non_vastu = [
            m for m in brief.soft_guidance
            if not m.context.startswith("vastu_")
        ]
        if non_vastu:
            counts = count_by_severity(non_vastu)
            n_strong = counts.get(GuidanceSeverity.STRONG_CONCERN, 0)
            n_concern = counts.get(GuidanceSeverity.CONCERN, 0)
            n_info = counts.get(GuidanceSeverity.INFO, 0)
            lines.append("")
            lines.append(_line)
            lines.append(
                f"COMPLETE GUIDANCE "
                f"({n_strong} strong concerns, {n_concern} concerns, "
                f"{n_info} info items)"
            )
            lines.append(_line)
            # v0.9.1 fix: group by category instead of flat list
            from buildemup.components.c01.soft_guide_engine import (
                group_guidance_by_category,
            )
            non_vastu_grouped = group_guidance_by_category(non_vastu)
            for category, msgs in non_vastu_grouped.items():
                lines.append("")
                lines.append(f"  ── {category} ({len(msgs)} item(s)) ──")
                for m in msgs:
                    lines.append(
                        f"    [{m.severity.value.upper()}] {m.text}"
                    )

        # ASSUMPTIONS USED (NEW per Drawback 10)
        lines.append("")
        lines.append(_line)
        lines.append("ASSUMPTIONS USED")
        lines.append(_line)
        for a in output.assumptions_used:
            lines.append(f"  • {a}")

        # v0.9.2 Drawback #16: explicit "What should you do now?" section
        # gives users a clear action sequence based on risk level. The old
        # NEXT STEPS section is still there but this is more actionable.
        # Implementation lives in compute_action_steps() so API + explain
        # stay consistent.
        from buildemup.components.c01.soft_guide_engine import (
            compute_action_steps,
        )
        actions = compute_action_steps(brief.soft_guidance, output.risk_level)
        lines.append("")
        lines.append(_line)
        lines.append("WHAT SHOULD YOU DO NOW?")
        lines.append(_line)
        for i, action in enumerate(actions, start=1):
            lines.append(f"  {i}. {action}")

        # Legacy NEXT STEPS (Drawback #8 v0.9 fix: use risk_level language)
        # Kept for back-compat with parsers that look for this header.
        lines.append("")
        lines.append(_line)
        lines.append("NEXT STEPS")
        lines.append(_line)
        if output.risk_level == "LOW":
            lines.append(
                "  Your brief is captured cleanly — no critical concerns. "
                "Next: layout generation (Component 4, coming soon) will "
                "show what's possible on this plot with your composition."
            )
        elif output.risk_level == "MEDIUM":
            lines.append(
                "  Your brief is captured and can proceed. Please review "
                "the CONCERN items above — they won't block your design "
                "but may limit options downstream. Layout generation "
                "(Component 4, coming soon) will proceed either way."
            )
        else:  # HIGH
            lines.append(
                "  Your brief has STRONG_CONCERN items that need review. "
                "You can:"
            )
            lines.append("    - Adjust your inputs and re-submit (recommended)")
            lines.append("    - Accept the concerns and proceed — layout "
                         "generation will still run but will reflect these "
                         "issues in its output")
            lines.append(
                "  NOTE: 'proceed_with_warnings' being True means only that "
                "downstream components will run — not that the system "
                "endorses this plan."
            )

        # Legal disclosures (v0.6 mandatory block)
        lines.append("")
        lines.append(format_legal_disclosures_block(mode="full"))

        # Reproducibility
        lines.append("")
        lines.append(_line)
        lines.append("REPRODUCIBILITY")
        lines.append(_line)
        lines.append(f"  Trace ID: {output.trace_id}")
        lines.append(f"  KB versions: {output.kb_versions}")
        if output.resume_token:
            lines.append(f"  Resume token: {output.resume_token}")
        lines.append(_sep)

        return "\n".join(lines)

    # ─── Internal helpers ────────────────────────────────────────────────

    def _build_plot(self, inp: BriefCaptureInput) -> Plot:
        """Convert primitive form input into a Plot domain object."""
        from buildemup.domain import PlotOrientation
        from buildemup.domain.plot import SharedSide, SoilType

        # Parse enums from strings
        facing_map = {
            "N": PlotOrientation.NORTH, "NE": PlotOrientation.NORTHEAST,
            "E": PlotOrientation.EAST, "SE": PlotOrientation.SOUTHEAST,
            "S": PlotOrientation.SOUTH, "SW": PlotOrientation.SOUTHWEST,
            "W": PlotOrientation.WEST, "NW": PlotOrientation.NORTHWEST,
        }
        facing = facing_map.get(inp.plot_facing.upper())
        if facing is None:
            raise ValueError(
                f"Invalid plot_facing '{inp.plot_facing}'. Must be one of: "
                f"{sorted(facing_map.keys())}"
            )

        pt_map = {
            "detached": PlotType.DETACHED,
            "semi_detached": PlotType.SEMI_DETACHED,
            "continuous": PlotType.CONTINUOUS,
        }
        plot_type = pt_map.get(inp.plot_type.lower())
        if plot_type is None:
            raise ValueError(
                f"Invalid plot_type '{inp.plot_type}'. Must be one of: "
                f"{sorted(pt_map.keys())}"
            )

        shared_side = None
        if inp.shared_side:
            ss_map = {"left": SharedSide.LEFT, "right": SharedSide.RIGHT}
            shared_side = ss_map.get(inp.shared_side.lower())

        soil_type = None
        if inp.soil_type_known:
            try:
                soil_type = SoilType(inp.soil_type_known.lower())
            except ValueError:
                soil_type = None    # Graceful: unknown soil type → None

        return Plot(
            width_m=inp.plot_width_m,
            depth_m=inp.plot_depth_m,
            facing=facing,
            city=inp.city,
            road_width_m=inp.road_width_m,
            plot_type=plot_type,
            corner_plot=inp.corner_plot,
            second_road_width_m=inp.second_road_width_m,
            shared_side=shared_side,
            soil_type_known=soil_type,
        )

    def _parse_vastu_tier(self, value: str) -> VastuTier:
        """Parse vastu tier string, defaulting to OFF for unknown."""
        try:
            return VastuTier(value.lower())
        except ValueError:
            return VastuTier.OFF

    def _setback_messages(
        self, is_compliant: bool, violations: tuple[str, ...],
        source_authority: str,
    ) -> list[GuidanceMessage]:
        """Turn setback violations into GuidanceMessage objects."""
        if is_compliant:
            return [GuidanceMessage(
                severity=GuidanceSeverity.INFO,
                text=(
                    f"Your setbacks meet {source_authority} compliance. "
                    f"Final approval still requires sanction from the "
                    f"municipal corporation."
                ),
                context="setbacks_compliant",
                action_verb="Consider",
            )]
        # Non-compliant — one STRONG_CONCERN per violating side
        msgs = []
        for v in violations:
            msgs.append(GuidanceMessage(
                severity=GuidanceSeverity.STRONG_CONCERN,
                text=(
                    f"{v} This may not get municipal approval per "
                    f"{source_authority}. Consider increasing the "
                    f"setback or reducing built-up area."
                ),
                context="setback_violation",
                action_verb="Adjust",
            ))
        return msgs

    def _collect_kb_versions(self) -> dict[str, str]:
        """Gather KB versions used in this run for reproducibility.

        v0.9.1 Drawback #6 fix: prefer _version (newest convention,
        added in Session C) over kb_version (legacy). Some KBs have
        both keys for historical reasons; we want the latest.
        """
        from buildemup.utils.kb_rules_loader import load_rules
        versions = {}
        for name in ("setback_rules", "room_minimums"):
            try:
                data = load_rules(name)
                meta = data.get("_meta", {})
                # Prefer _version (Session C+ convention),
                # fall back to kb_version (v0.1 convention)
                versions[name] = (
                    meta.get("_version")
                    or meta.get("kb_version")
                    or "unknown"
                )
            except Exception:
                versions[name] = "error"
        return versions


# ─────────────────────────────────────────────────────────────────────────
# Component Contract registration (per v0.7.1)
# ─────────────────────────────────────────────────────────────────────────
_CONTRACT = ComponentContract(
    component_id="C01_brief_capture",
    version="0.1",
    description=(
        "Captures user homebuilding brief from form input, validates "
        "against NBC/DCR setback rules, estimates cost via Component 7 "
        "(single source of truth), applies soft-guide validation without "
        "rejecting input, and produces a validated Brief domain object "
        "for downstream components."
    ),
    consumes=(
        # Plot
        required("plot_width_m", "float", "Plot width in metres",
                 ">=3.0", "<=60.0"),
        required("plot_depth_m", "float", "Plot depth in metres",
                 ">=3.0", "<=60.0"),
        required("plot_facing", "str", "One of N/NE/E/SE/S/SW/W/NW"),
        required("city", "str", "One of 6 supported launch cities"),
        required("road_width_m", "float", "Abutting road width in metres",
                 ">=1.5", "<=30.0"),
        optional("plot_type", "str",
                 "detached/semi_detached/continuous (default: detached)"),
        optional("corner_plot", "bool"),
        optional("second_road_width_m", "float"),
        optional("shared_side", "str", "left/right if plot_type=semi_detached"),
        # Setbacks
        required("user_setback_front_m", "float", ">=0.0", "<=15.0"),
        required("user_setback_rear_m", "float", ">=0.0", "<=15.0"),
        required("user_setback_side_left_m", "float", ">=0.0", "<=15.0"),
        required("user_setback_side_right_m", "float", ">=0.0", "<=15.0"),
        # Floors
        required("floors", "tuple[FloorRequirement, ...]",
                 "Tuple of FloorRequirement domain objects"),
        # Budget
        required("budget_min_lakhs", "int", ">=1", "<=10000"),
        required("budget_max_lakhs", "int", ">=1", "<=10000"),
        # Optional
        optional("additional_requirements", "tuple"),
        optional("soil_type_known", "str"),
        optional("vastu_preference", "str", "off/partial/full (default: off)"),
        optional("user_email", "str", "Optional — session-only in v0.1"),
        optional("user_phone", "str", "Optional — session-only in v0.1"),
        optional("resume_token", "str",
                 "Optional — for save/resume via browser localStorage"),
    ),
    produces=(
        required("brief", "Brief",
                 "Validated brief domain object (feeds Component 7 via "
                 "brief.to_structural_grid_input())"),
        required("soft_guidance", "tuple",
                 "All GuidanceMessage items generated during capture"),
        required("top_guidance", "tuple",
                 "Top 3 guidance messages prioritised by severity"),
        required("compliance_summary", "ComplianceSummary",
                 "Setback compliance status + violations"),
        required("assumptions_used", "tuple",
                 "Explicit list of assumptions for transparency"),
        optional("c7_preview_cost", "CostEstimate",
                 "Cost from Component 7, or None if bridge failed"),
        required("trace_id", "str"),
        required("kb_versions", "dict"),
        required("proceed_with_warnings", "bool",
                 "Always True in v0.1 — downstream can always run. "
                 "Use risk_level for meaningful risk signal."),
        required("risk_level", "str",
                 "LOW / MEDIUM / HIGH — overall risk of plan based on "
                 "severity of guidance messages."),
        optional("resume_token", "str"),
    ),
)

register_contract(_CONTRACT)
