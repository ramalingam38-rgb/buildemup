"""
v0.1 Session 5 tests — BriefCaptureEngine Orchestrator.

Covers SPEC_v0.2 Section 13:
  G. End-to-end handshake (remaining tests)
  H. ComponentContract enforcement (~4 tests)
  Plus: orchestrator pipeline, explain() rendering, edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _minimal_floors():
    """A minimal valid G+1 floor set."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    return (
        FloorRequirement(
            floor_number=0, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.LIVING, 1),
                   RoomRequirement(RoomType.KITCHEN, 1)),
        ),
        FloorRequirement(
            floor_number=1, floor_use=FloorUse.RESIDENTIAL,
            rooms=(RoomRequirement(RoomType.BEDROOM_MASTER, 1),),
        ),
    )


def _minimal_input(**overrides):
    """Build a minimal BriefCaptureInput with overrideable fields."""
    from buildemup.components.c01_brief_capture import BriefCaptureInput
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0, plot_type="detached",
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=_minimal_floors(),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    return BriefCaptureInput(**defaults)


# ─────────────────────────────────────────────────────────────────────────
# Orchestrator pipeline
# ─────────────────────────────────────────────────────────────────────────

def test_orchestrator_end_to_end_succeeds():
    """BriefCaptureEngine.execute runs the full pipeline without error."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    assert output.brief is not None
    assert output.trace_id
    assert output.compliance_summary is not None
    print(f"PASS end-to-end execute → trace {output.trace_id}")


def test_orchestrator_produces_valid_brief():
    """Output.brief is a valid Brief domain object."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    from buildemup.domain import Brief
    output = BriefCaptureEngine().execute(_minimal_input())
    assert isinstance(output.brief, Brief)
    assert output.brief.plot.city == "chennai"
    assert len(output.brief.floors) == 2
    print("PASS output.brief is a valid Brief domain object")


def test_orchestrator_populates_compliance_summary():
    """Compliance summary reflects setback check outcome."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    # Compliant case
    output_ok = BriefCaptureEngine().execute(_minimal_input())
    assert output_ok.compliance_summary.is_setback_compliant is True
    assert output_ok.compliance_summary.source_authority == "TNCDBR 2019 (CMDA)"

    # Non-compliant case: user setbacks too small
    output_bad = BriefCaptureEngine().execute(_minimal_input(
        user_setback_front_m=0.5,
        user_setback_side_left_m=0.5,
    ))
    assert output_bad.compliance_summary.is_setback_compliant is False
    assert len(output_bad.compliance_summary.setback_violations) > 0
    print(f"PASS compliance_summary reflects setback state")


def test_orchestrator_c7_cost_populated():
    """c7_preview_cost is a valid CostEstimate after execute."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    from buildemup.domain import CostEstimate
    output = BriefCaptureEngine().execute(_minimal_input())
    assert output.c7_preview_cost is not None
    assert isinstance(output.c7_preview_cost, CostEstimate)
    assert output.c7_preview_cost.exact_value > 0
    print(f"PASS c7_preview_cost populated: "
          f"₹{output.c7_preview_cost.exact_value/100_000:.1f}L")


def test_orchestrator_ready_false_on_strong_concerns():
    """ready_for_downstream is False when STRONG_CONCERN present."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    # Bad setbacks → STRONG_CONCERN
    output = BriefCaptureEngine().execute(_minimal_input(
        user_setback_front_m=0.3, user_setback_side_left_m=0.3,
    ))
    assert output.ready_for_downstream is False
    print("PASS ready_for_downstream=False when STRONG_CONCERN present")


def test_orchestrator_ready_true_when_all_info():
    """ready_for_downstream is True when no STRONG_CONCERN messages."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    # Wide plot, generous setbacks, aligned budget — should be clean
    assert output.ready_for_downstream is True
    print("PASS ready_for_downstream=True when no STRONG_CONCERN")


def test_orchestrator_top_guidance_capped_at_3():
    """top_guidance is always ≤ 3 items."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input(
        vastu_preference="full",     # generates ~15 vastu messages
    ))
    assert len(output.top_guidance) <= 3
    print(f"PASS top_guidance ≤ 3 ({len(output.top_guidance)} items)")


def test_orchestrator_kb_versions_include_new_kbs():
    """kb_versions includes setback_rules + room_minimums."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    assert "setback_rules" in output.kb_versions
    assert "room_minimums" in output.kb_versions
    print(f"PASS kb_versions: {output.kb_versions}")


# ─────────────────────────────────────────────────────────────────────────
# End-to-end Component 1 → Component 7 handshake
# ─────────────────────────────────────────────────────────────────────────

def test_brief_feeds_c7_successfully():
    """Output brief can feed Component 7 end-to-end."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    from buildemup.components.c07_structural_grid import StructuralGridEngine
    brief = BriefCaptureEngine().execute(_minimal_input()).brief

    sgi = brief.to_structural_grid_input()
    result = StructuralGridEngine().execute(sgi)
    assert result is not None
    assert result.cost.exact_value > 0
    print(f"PASS Brief → Component 7 end-to-end: "
          f"cost ₹{result.cost.exact_value/100_000:.1f}L")


def test_c7_cost_in_c1_matches_direct_c7_run():
    """C1's c7_preview_cost matches direct C7 run on the same Brief."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    from buildemup.components.c07_structural_grid import StructuralGridEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    direct = StructuralGridEngine().execute(
        output.brief.to_structural_grid_input()
    )
    # Bridge cost must match direct run (allow tiny floating-point jitter)
    assert abs(output.c7_preview_cost.exact_value - direct.cost.exact_value) < 1.0
    print(f"PASS C1 bridge cost == direct C7 "
          f"(₹{output.c7_preview_cost.exact_value:.0f})")


# ─────────────────────────────────────────────────────────────────────────
# H. ComponentContract enforcement
# ─────────────────────────────────────────────────────────────────────────

def test_c01_contract_registered():
    """Component 1 contract is registered with the contract system."""
    from buildemup.utils.component_contract import get_contract
    # Force module import to trigger register_contract()
    import buildemup.components.c01_brief_capture  # noqa
    c = get_contract("C01_brief_capture")
    assert c is not None
    assert c.version == "0.1"
    print(f"PASS C01_brief_capture contract registered (v{c.version})")


def test_c01_contract_produces_brief_domain_object():
    """Contract declares Brief as a produced domain type."""
    from buildemup.utils.component_contract import get_contract
    import buildemup.components.c01_brief_capture  # noqa
    c = get_contract("C01_brief_capture")
    produces_names = [spec.type_name for spec in c.produces]
    assert "Brief" in produces_names
    print("PASS C01 contract produces 'Brief' as domain type")


def test_brief_domain_types_enforced_downstream():
    """v0.7.1 enforcement catches raw dicts for Brief consumers."""
    from buildemup.utils.component_contract import (
        ComponentContract, register_contract, required, validate_input,
    )
    from dataclasses import dataclass

    # Register a test contract that consumes a Brief
    test_contract = ComponentContract(
        component_id="TEST_brief_consumer",
        version="0.1",
        description="Test consumer of a Brief",
        consumes=(
            required("brief", "Brief", "A Brief domain object"),
        ),
        produces=(
            required("result", "str", "Output"),
        ),
    )
    register_contract(test_contract)

    @dataclass
    class BadInput:
        brief: dict
    violations = validate_input(
        "TEST_brief_consumer",
        BadInput(brief={"fake": "brief"}),
    )
    assert len(violations) > 0
    assert "must be a domain object" in violations[0]
    print("PASS downstream dict-as-Brief rejected by v0.7.1 enforcement")


def test_c01_input_has_floors_as_domain_tuple():
    """Contract declares floors as tuple[FloorRequirement, ...] domain type."""
    from buildemup.utils.component_contract import get_contract
    import buildemup.components.c01_brief_capture  # noqa
    c = get_contract("C01_brief_capture")
    floors_spec = next(s for s in c.consumes if s.name == "floors")
    assert "FloorRequirement" in floors_spec.type_name
    print(f"PASS floors declared as: {floors_spec.type_name}")


# ─────────────────────────────────────────────────────────────────────────
# explain() rendering
# ─────────────────────────────────────────────────────────────────────────

def test_explain_contains_all_major_sections():
    """explain() output has all sections per SPEC_v0.2 Section 10.3."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input(vastu_preference="partial")
    output = engine.execute(inp)
    rendered = engine.explain(inp, output)

    required_sections = [
        "YOUR BRIEF",
        "TOP 3 RECOMMENDATIONS",
        "PLOT",
        "SETBACKS",
        "FLOOR COMPOSITION",
        "BUDGET",
        "VASTU GUIDANCE",
        "ASSUMPTIONS USED",
        "NEXT STEPS",
        "LEGAL",
        "REPRODUCIBILITY",
    ]
    for section in required_sections:
        assert section in rendered, f"Section '{section}' missing from explain()"
    print(f"PASS explain() has all {len(required_sections)} required sections")


def test_explain_shows_setback_comparison_table():
    """Setbacks section shows 4-column comparison with diffs."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    assert "Your input" in rendered
    assert "Compliant" in rendered
    assert "Difference" in rendered
    assert "Front:" in rendered
    assert "Rear:" in rendered
    print("PASS explain() shows 4-column setback comparison")


def test_explain_continuous_plot_hides_side_setbacks():
    """For CONTINUOUS plot_type, side setbacks should not appear in table."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input(
        plot_type="continuous",
        user_setback_side_left_m=0.0, user_setback_side_right_m=0.0,
    )
    rendered = engine.explain(inp, engine.execute(inp))
    # Front and Rear shown
    assert "Front:" in rendered
    assert "Rear:" in rendered
    # Sides NOT in the comparison table (they're always 0 for CONTINUOUS)
    # We check the SETBACKS section specifically
    setbacks_start = rendered.find("SETBACKS")
    setbacks_end = rendered.find("FLOOR COMPOSITION")
    setbacks_section = rendered[setbacks_start:setbacks_end]
    assert "Side (L):" not in setbacks_section
    assert "Side (R):" not in setbacks_section
    print("PASS explain() hides side setbacks for CONTINUOUS plot")


def test_explain_budget_section_shows_c7_estimate():
    """Budget section cites Component 7 as the source."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    # Must mention Component 7 source and numeric estimate
    assert "Component 7" in rendered
    assert "₹" in rendered    # cost rendered in rupees
    print("PASS explain() cites Component 7 in budget section")


def test_explain_vastu_section_only_when_opted_in():
    """VASTU GUIDANCE section only appears if vastu != OFF."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    # OFF: no vastu section
    out_off = engine.execute(_minimal_input(vastu_preference="off"))
    rendered_off = engine.explain(_minimal_input(vastu_preference="off"), out_off)
    assert "VASTU GUIDANCE" not in rendered_off

    # PARTIAL: section present
    out_partial = engine.execute(_minimal_input(vastu_preference="partial"))
    rendered_partial = engine.explain(
        _minimal_input(vastu_preference="partial"), out_partial,
    )
    assert "VASTU GUIDANCE (PARTIAL tier)" in rendered_partial
    print("PASS vastu section shown only when opted in")


def test_explain_includes_legal_disclosures():
    """Legal disclosures block always shown (v0.6 mandatory)."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    # Check several legal-block markers
    assert "STRUCTURAL ENGINEER REQUIRED" in rendered
    assert "MUNICIPAL PERMIT" in rendered
    assert "LIMITATION OF LIABILITY" in rendered
    print("PASS explain() includes mandatory legal disclosures")


def test_explain_reproducibility_block():
    """Reproducibility section has trace_id and kb_versions."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    output = engine.execute(inp)
    rendered = engine.explain(inp, output)
    assert "Trace ID:" in rendered
    assert output.trace_id in rendered
    assert "KB versions:" in rendered
    print("PASS explain() reproducibility block shows trace + versions")


# ─────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────

def test_orchestrator_handles_different_cities():
    """Each supported city produces a valid Brief."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    for city in ["chennai", "bangalore", "hyderabad",
                 "mumbai", "pune", "delhi"]:
        output = BriefCaptureEngine().execute(_minimal_input(city=city))
        assert output.brief.plot.city == city
        # Chennai gets TNCDBR; others get NBC fallback
        authority = output.compliance_summary.source_authority
        assert authority
    print("PASS all 6 cities produce valid Briefs")


def test_orchestrator_handles_all_plot_types():
    """DETACHED / SEMI_DETACHED / CONTINUOUS all succeed."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()

    # DETACHED
    out_d = engine.execute(_minimal_input(plot_type="detached"))
    assert out_d.brief is not None

    # SEMI_DETACHED
    out_s = engine.execute(_minimal_input(
        plot_type="semi_detached", shared_side="left",
    ))
    assert out_s.brief is not None

    # CONTINUOUS
    out_c = engine.execute(_minimal_input(
        plot_type="continuous",
        user_setback_side_left_m=0.0, user_setback_side_right_m=0.0,
    ))
    assert out_c.brief is not None
    print("PASS all 3 plot types produce valid Briefs")


def test_orchestrator_vastu_integrated_in_guidance():
    """Vastu messages appear in soft_guidance (not just separate list)."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input(
        vastu_preference="partial",
    ))
    vastu_msgs = [
        m for m in output.soft_guidance
        if m.context.startswith("vastu_")
    ]
    # PARTIAL = 7 vastu messages
    assert len(vastu_msgs) == 7
    # All INFO
    from buildemup.domain import GuidanceSeverity
    assert all(m.severity == GuidanceSeverity.INFO for m in vastu_msgs)
    print("PASS vastu messages integrated into soft_guidance (7, all INFO)")


def test_orchestrator_trace_id_is_unique_per_run():
    """Every execute() gets a fresh trace_id."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    o1 = engine.execute(_minimal_input())
    o2 = engine.execute(_minimal_input())
    assert o1.trace_id != o2.trace_id
    print(f"PASS trace_ids unique: {o1.trace_id[:8]}.. vs {o2.trace_id[:8]}..")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 5 Tests: BriefCaptureEngine")
    print("=" * 70)
    print()
    print("--- Orchestrator pipeline ---")
    test_orchestrator_end_to_end_succeeds()
    test_orchestrator_produces_valid_brief()
    test_orchestrator_populates_compliance_summary()
    test_orchestrator_c7_cost_populated()
    test_orchestrator_ready_false_on_strong_concerns()
    test_orchestrator_ready_true_when_all_info()
    test_orchestrator_top_guidance_capped_at_3()
    test_orchestrator_kb_versions_include_new_kbs()
    print()
    print("--- Brief → Component 7 end-to-end ---")
    test_brief_feeds_c7_successfully()
    test_c7_cost_in_c1_matches_direct_c7_run()
    print()
    print("--- H. ComponentContract enforcement ---")
    test_c01_contract_registered()
    test_c01_contract_produces_brief_domain_object()
    test_brief_domain_types_enforced_downstream()
    test_c01_input_has_floors_as_domain_tuple()
    print()
    print("--- explain() rendering ---")
    test_explain_contains_all_major_sections()
    test_explain_shows_setback_comparison_table()
    test_explain_continuous_plot_hides_side_setbacks()
    test_explain_budget_section_shows_c7_estimate()
    test_explain_vastu_section_only_when_opted_in()
    test_explain_includes_legal_disclosures()
    test_explain_reproducibility_block()
    print()
    print("--- Edge cases ---")
    test_orchestrator_handles_different_cities()
    test_orchestrator_handles_all_plot_types()
    test_orchestrator_vastu_integrated_in_guidance()
    test_orchestrator_trace_id_is_unique_per_run()
    print()
    print("=" * 70)
    print("ALL SESSION 5 TESTS PASSED")
    print("=" * 70)
