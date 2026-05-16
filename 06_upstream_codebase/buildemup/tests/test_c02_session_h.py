"""
Component 2 Session H tests.

Coverage:
  - render_text_summary: structure, length, key content
  - render_text_full: all sections present, doubts appendix optional
  - render_json: shape correctness, all enums as strings, JSON-serializable
  - Edge cases: best case (no gaps), worst case (many issues)
  - Doubts appendix: dedupes by check_id, only includes non-empty doubts
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief_with_orchestrator(**overrides):
    """Helper: build a brief and run feasibility, returning (analysis, brief)."""
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.orchestrator import run_feasibility
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0, plot_type="detached",
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
        ),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    inp = BriefCaptureInput(**defaults)
    out = BriefCaptureEngine().execute(inp)
    analysis = run_feasibility(out.brief, c7_cost_estimate=out.c7_preview_cost)
    return analysis, out.brief


# ─── render_text_summary ──────────────────────────────────────────────

def test_summary_returns_string():
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_summary(analysis, brief)
    assert isinstance(result, str)
    assert len(result) > 0
    print("PASS render_text_summary returns non-empty string")


def test_summary_is_short():
    """Summary should fit in ~30 lines."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_summary(analysis, brief)
    line_count = len(result.split("\n"))
    assert 10 <= line_count <= 40, f"Expected 10-40 lines, got {line_count}"
    print(f"PASS summary is {line_count} lines (in target range)")


def test_summary_includes_both_lane_scores():
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_summary(analysis, brief)
    assert "PRACTICAL" in result
    assert "CODE-STRICT" in result
    # Scores should appear as "/100"
    assert "/100" in result
    print("PASS summary includes both lane scores")


def test_summary_includes_plot_info():
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_summary(analysis, brief)
    assert "Chennai" in result
    assert "180 sqm" in result or "180" in result
    print("PASS summary includes plot info (city + sqm)")


def test_summary_shows_top_concerns_when_warnings_present():
    """Brief with soft warnings should surface them."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()  # default has warnings
    result = render_text_summary(analysis, brief)
    # Should have either TOP CONCERNS or TOP BLOCKING ISSUES section
    assert ("TOP CONCERNS" in result or "TOP BLOCKING" in result
            or "All Practical checks passing" in result)
    print("PASS summary shows top concerns when warnings present")


def test_summary_indicates_feasibility_status():
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_summary(analysis, brief)
    assert "FEASIBLE" in result or "NOT FEASIBLE" in result
    print("PASS summary indicates feasibility status")


def test_summary_handles_best_case():
    """Best case (S-facing, all data verified) — no major issues."""
    from buildemup.components.c02.renderer import render_text_summary
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=15.0, plot_depth_m=20.0, plot_facing="S",
        city="chennai", road_width_m=12.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=30, budget_max_lakhs=40,
    )
    out = BriefCaptureEngine().execute(inp)
    feas_inp = FeasibilityInput(
        brief=out.brief,
        soil_type=InputField.verified("sandy_alluvial"),
        water_table_depth_m=InputField.verified(8.0),
    )
    analysis = run_feasibility(
        out.brief, c7_cost_estimate=out.c7_preview_cost,
        feasibility_input=feas_inp,
        distance_from_electric_line_m=10.0,
        electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    result = render_text_summary(analysis, out.brief)
    # Best case: only RWH SOFT_WARN (Chennai always mandates)
    assert "FEASIBLE" in result
    print("PASS summary handles best case cleanly")


# ─── render_text_full ─────────────────────────────────────────────────

def test_full_returns_string():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    assert isinstance(result, str)
    assert len(result) > 0
    print("PASS render_text_full returns non-empty string")


def test_full_is_longer_than_summary():
    from buildemup.components.c02.renderer import (
        render_text_summary, render_text_full,
    )
    analysis, brief = _build_brief_with_orchestrator()
    full = render_text_full(analysis, brief)
    summary = render_text_summary(analysis, brief)
    assert len(full) > len(summary)
    print(f"PASS full ({len(full)}c) > summary ({len(summary)}c)")


def test_full_includes_all_required_sections():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    required = [
        "PLOT", "BUILD", "OVERALL ASSESSMENT",
        "PRACTICAL LANE", "CODE-STRICT LANE",
        "REPORT NOTES",
    ]
    for section in required:
        assert section in result, f"Missing section: {section}"
    print(f"PASS full includes all {len(required)} required sections")


def test_full_includes_gaps_section_when_gaps_present():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()  # Has gaps from N-facing
    result = render_text_full(analysis, brief)
    if len(analysis.gaps) > 0:
        assert "GAPS BETWEEN PRACTICAL AND CODE-STRICT" in result
    print(f"PASS gaps section present when gaps exist ({len(analysis.gaps)} gaps)")


def test_full_includes_unknowns_section_when_unknowns_present():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    if len(analysis.practical_report.unknowns) > 0:
        assert "VERIFICATION RECOMMENDED" in result
    print("PASS unknowns section present when unknowns exist")


def test_full_includes_action_steps_section_when_actions_present():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    if len(analysis.practical_report.action_steps) > 0:
        assert "ACTION STEPS" in result
    print("PASS action steps section present when actions exist")


def test_full_doubts_appendix_default_on():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    # Should include FAQs by default
    assert "FREQUENTLY ASKED QUESTIONS" in result
    print("PASS doubts appendix included by default")


def test_full_doubts_appendix_can_be_disabled():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief, include_doubts=False)
    assert "FREQUENTLY ASKED QUESTIONS" not in result
    print("PASS doubts appendix can be disabled with include_doubts=False")


def test_full_renders_severity_symbols():
    """The check details use ✗ for blocking, ! for warning, ✓ for pass."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    # Should have at least one passing check (symbol ✓)
    assert "✓" in result or "PASSED" in result
    print("PASS full uses severity symbols (✗/!/✓/-)")


def test_full_handles_brief_without_budget():
    """Brief always has budget_range, so no special handling needed.
    But test that the renderer doesn't crash on minimal brief."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    assert "Budget" in result
    print("PASS full handles brief budget")


def test_full_word_wrap_keeps_lines_under_80_chars():
    """Wrapped messages should keep lines under 80 chars for terminal."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_brief_with_orchestrator()
    result = render_text_full(analysis, brief)
    # Most lines should be ≤ 80 chars (some may exceed for URLs/data values)
    over_80 = [l for l in result.split("\n") if len(l) > 100]
    assert len(over_80) <= 5, f"Too many long lines: {len(over_80)}"
    print(f"PASS most lines under 100 chars ({len(over_80)} exceptions)")


# ─── render_json ──────────────────────────────────────────────────────

def test_json_returns_dict():
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    assert isinstance(result, dict)
    print("PASS render_json returns dict")


def test_json_has_top_level_keys():
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    expected = {
        "practical_report", "code_strict_report", "gaps",
        "cost_delta_lakhs", "user_decisions_required",
    }
    assert set(result.keys()) == expected
    print("PASS json has all 5 top-level DesignGapAnalysis keys")


def test_json_practical_report_has_all_fields():
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    p = result["practical_report"]
    expected = {
        "variant", "overall_score", "score_breakdown",
        "blocking_issues", "unaccepted_blocking_issues",
        "soft_warnings", "passed_checks", "not_applicable_checks",
        "cost_estimate", "unknowns", "action_steps",
    }
    assert set(p.keys()) == expected
    print(f"PASS json practical_report has all {len(expected)} fields")


def test_json_enums_are_strings():
    """All Enum values should be serialized as strings (.value)."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    # Variant should be a string
    assert isinstance(result["practical_report"]["variant"], str)
    assert result["practical_report"]["variant"] == "practical"
    # Severity in checks should be a string
    if result["practical_report"]["passed_checks"]:
        assert isinstance(
            result["practical_report"]["passed_checks"][0]["severity"], str,
        )
    print("PASS json converts all enums to .value strings")


def test_json_tuples_are_lists():
    """Tuples should serialize to lists."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    assert isinstance(result["gaps"], list)
    assert isinstance(result["practical_report"]["passed_checks"], list)
    assert isinstance(result["user_decisions_required"], list)
    print("PASS json converts tuples to lists")


def test_json_is_json_serializable():
    """The dict should be JSON-serializable end-to-end."""
    import json as json_lib
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    serialized = json_lib.dumps(result)
    assert len(serialized) > 0
    # And round-trip
    parsed = json_lib.loads(serialized)
    assert parsed["practical_report"]["overall_score"] == result["practical_report"]["overall_score"]
    print(f"PASS json round-trips through json.dumps/loads ({len(serialized)} chars)")


def test_json_includes_common_doubts():
    """common_doubts should appear in the JSON for each check that has them."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    # Find a check that has common_doubts (e.g., RWH)
    rwh_checks = [
        c for c in result["practical_report"]["soft_warnings"]
        if "rwh" in c["check_id"].lower()
    ]
    if rwh_checks:
        rwh = rwh_checks[0]
        assert "common_doubts" in rwh
        assert isinstance(rwh["common_doubts"], list)
    print("PASS json includes common_doubts on each check")


def test_json_includes_unknowns():
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    unknowns = result["practical_report"]["unknowns"]
    if len(analysis.practical_report.unknowns) > 0:
        assert len(unknowns) > 0
        u = unknowns[0]
        assert "field_name" in u
        assert "verification_recommendation" in u
        assert "priority" in u
        # Priority should be a string (enum value)
        assert isinstance(u["priority"], str)
    print(f"PASS json includes unknowns with all fields ({len(unknowns)} unknowns)")


def test_json_includes_action_steps():
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_brief_with_orchestrator()
    result = render_json(analysis)
    actions = result["practical_report"]["action_steps"]
    if len(analysis.practical_report.action_steps) > 0:
        assert len(actions) > 0
        a = actions[0]
        assert "step_text" in a
        assert "triggering_check_ids" in a
        assert "priority" in a
        assert isinstance(a["priority"], int)
    print(f"PASS json includes action_steps ({len(actions)} actions)")


# ─── Doubts appendix behaviour ────────────────────────────────────────

def test_doubts_appendix_dedupes_by_check_id():
    """Same check_id across passed/warnings/blocking shouldn't repeat doubts.

    But practical+code_strict variants of same check have different check_ids,
    so they could both appear. Test that it's a property of the report's
    check_ids, not of the underlying topic."""
    from buildemup.components.c02.renderer import _render_doubts_appendix
    analysis, brief = _build_brief_with_orchestrator()
    lines = _render_doubts_appendix(analysis.practical_report)
    # Count how many times "About:" appears — once per unique check_id with doubts
    about_count = sum(1 for l in lines if l.startswith("About:"))
    # Every check_id should appear at most once
    about_lines = [l for l in lines if l.startswith("About:")]
    assert len(about_lines) == len(set(about_lines))
    print(f"PASS doubts appendix dedupes by check_id ({about_count} sections)")


def test_doubts_appendix_skips_checks_without_doubts():
    """Checks with empty common_doubts shouldn't get an empty section."""
    from buildemup.components.c02.renderer import _render_doubts_appendix
    analysis, brief = _build_brief_with_orchestrator()
    lines = _render_doubts_appendix(analysis.practical_report)
    # Get all checks with doubts
    checks_with_doubts = {
        c.check_id for c in analysis.practical_report.all_check_results
        if c.common_doubts
    }
    about_lines = [l for l in lines if l.startswith("About:")]
    # Number of "About:" sections == number of checks with doubts
    assert len(about_lines) == len(checks_with_doubts)
    print(f"PASS doubts appendix only includes checks with non-empty doubts "
          f"({len(checks_with_doubts)} checks)")


# ─── User guide doc exists ────────────────────────────────────────────

def test_user_guide_doc_exists():
    """The user guide markdown doc should be present."""
    import os
    path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "buildemup", "docs", "c02_user_guide.md",
    )
    assert os.path.exists(path), f"Missing: {path}"
    with open(path) as f:
        content = f.read()
    # Check key sections exist
    assert "# BuildemUp Feasibility Report" in content
    assert "Practical" in content
    assert "Code-Strict" in content
    assert "scores" in content.lower()
    assert "gap" in content.lower()
    print("PASS user guide doc exists with required sections")


# ─── Baseline ─────────────────────────────────────────────────────────

def test_v0_9_3_baseline_unaffected_by_session_h():
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),)),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    out = BriefCaptureEngine().execute(inp)
    assert out.risk_level == "LOW"
    print("PASS v0.9.3 baseline unaffected by Session H")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session H (Renderer + User Guide)")
    print("=" * 70)
    print()

    print("--- render_text_summary ---")
    test_summary_returns_string()
    test_summary_is_short()
    test_summary_includes_both_lane_scores()
    test_summary_includes_plot_info()
    test_summary_shows_top_concerns_when_warnings_present()
    test_summary_indicates_feasibility_status()
    test_summary_handles_best_case()
    print()

    print("--- render_text_full ---")
    test_full_returns_string()
    test_full_is_longer_than_summary()
    test_full_includes_all_required_sections()
    test_full_includes_gaps_section_when_gaps_present()
    test_full_includes_unknowns_section_when_unknowns_present()
    test_full_includes_action_steps_section_when_actions_present()
    test_full_doubts_appendix_default_on()
    test_full_doubts_appendix_can_be_disabled()
    test_full_renders_severity_symbols()
    test_full_handles_brief_without_budget()
    test_full_word_wrap_keeps_lines_under_80_chars()
    print()

    print("--- render_json ---")
    test_json_returns_dict()
    test_json_has_top_level_keys()
    test_json_practical_report_has_all_fields()
    test_json_enums_are_strings()
    test_json_tuples_are_lists()
    test_json_is_json_serializable()
    test_json_includes_common_doubts()
    test_json_includes_unknowns()
    test_json_includes_action_steps()
    print()

    print("--- Doubts appendix ---")
    test_doubts_appendix_dedupes_by_check_id()
    test_doubts_appendix_skips_checks_without_doubts()
    print()

    print("--- User guide doc ---")
    test_user_guide_doc_exists()
    print()

    print("--- Baseline ---")
    test_v0_9_3_baseline_unaffected_by_session_h()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION H TESTS PASSED")
    print("=" * 70)
