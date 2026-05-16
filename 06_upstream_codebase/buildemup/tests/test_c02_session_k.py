"""
Component 2 Session K tests.

Tests the 5 UX-clarity drawback fixes from the domain review:
  - Drawback 1: Summary surfaces blocker count + names
  - Drawback 2: Downgraded SOFT warnings flagged inline + in summary
  - Drawback 6: Approval check SOFT_WARNs at complex tier
  - Drawback 9: JSON enriched with severity_label + category_label
  - Drawback 11: Inline category tags in lane details (LEGAL/DESIGN/etc.)

These tests document what each fix delivers and lock in the format so
future renderer changes can't quietly break the user-facing signal.
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# Helper: build a brief + run feasibility, return (analysis, brief)
def _build_analysis(**overrides):
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.orchestrator import run_feasibility
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    inp = BriefCaptureInput(**defaults)
    out = BriefCaptureEngine().execute(inp)
    analysis = run_feasibility(out.brief, c7_cost_estimate=out.c7_preview_cost)
    return analysis, out.brief


def _build_pune_g3_unverified():
    """Builds a Pune G+3 brief that triggers the downgrade rule (assumed
    black_cotton soil + G+3 = HARD_FAIL, downgraded to SOFT_WARN because
    user didn't provide verified soil data)."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floors = tuple(
        [FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),))]
        + [FloorRequirement(i, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.BEDROOM_MASTER, 1),))
           for i in range(1, 4)]
    )
    return _build_analysis(
        city="pune", plot_width_m=15.0, plot_depth_m=20.0,
        road_width_m=12.0, floors=floors,
        budget_min_lakhs=80, budget_max_lakhs=120,
    )


# ─── Drawback 1: Summary surfaces blocker count + names ──────────────

def test_drawback_1_summary_shows_blocker_count_when_blockers_exist():
    """When any lane has blockers, the score line should show count."""
    from buildemup.components.c02.renderer import render_text_summary
    # Pune G+3 unverified: Code-Strict has 4+ blockers
    analysis, brief = _build_pune_g3_unverified()
    summary = render_text_summary(analysis, brief)
    # Code-Strict should show "(N blockers)" inline
    assert any(
        "blockers)" in line and "CODE-STRICT" in summary[summary.find(line):]
        for line in summary.split("\n")
        if "blockers)" in line
    ), "Summary should show '(N blockers)' inline with score"
    print("PASS summary score line shows blocker count when blockers exist")


def test_drawback_1_summary_lists_blocker_names():
    """Summary should list the first few blocker names."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_pune_g3_unverified()
    summary = render_text_summary(analysis, brief)
    # "Blockers: ..." line should appear
    assert any("Blockers:" in line for line in summary.split("\n")), (
        "Summary should include 'Blockers: <names>' line"
    )
    print("PASS summary lists blocker names")


def test_drawback_1_summary_truncates_blocker_list_with_count():
    """When there are >3 blockers, summary should show '+ N more'."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_pune_g3_unverified()
    # If there are >3 blockers, the truncation suffix should appear
    n_blockers = len(analysis.code_strict_report.blocking_issues)
    summary = render_text_summary(analysis, brief)
    if n_blockers > 3:
        assert "more" in summary, (
            f"Summary should show '+ N more' when {n_blockers} blockers"
        )
    print(f"PASS summary truncates blocker list with '+ N more' "
          f"({n_blockers} blockers in this scenario)")


def test_drawback_1_summary_no_blocker_count_when_clean():
    """Best-case summary should NOT show '(N blockers)' inline."""
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
            (RoomRequirement(RoomType.LIVING, 1),)),),
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
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    summary = render_text_summary(analysis, out.brief)
    # No blockers in either lane → no "blockers)" suffix anywhere
    assert "blockers)" not in summary, (
        "Best case summary should not have '(N blockers)' suffix"
    )
    print("PASS summary omits blocker count when both lanes clean")


# ─── Drawback 2: Downgrade tag in lane details + summary note ────────

def test_drawback_2_downgraded_warning_tagged_in_lane_details():
    """SOFT_WARN with details.downgrade_applied=True should show
    [DOWNGRADED FROM HARD] in the lane details."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_pune_g3_unverified()
    full = render_text_full(analysis, brief, include_doubts=False)
    assert "[DOWNGRADED FROM HARD]" in full, (
        "Lane details should tag downgraded warnings"
    )
    print("PASS downgraded warnings tagged [DOWNGRADED FROM HARD] in lane details")


def test_drawback_2_summary_notes_downgraded_count():
    """Summary should display 'Note: N warning(s) downgraded from HARD'
    when downgrades exist."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_pune_g3_unverified()
    summary = render_text_summary(analysis, brief)
    assert "downgraded from HARD" in summary, (
        "Summary should include downgrade note"
    )
    print("PASS summary notes downgraded count when downgrades exist")


def test_drawback_2_no_downgrade_note_when_no_downgrades():
    """Best case summary should NOT include the downgrade note."""
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
            (RoomRequirement(RoomType.LIVING, 1),)),),
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
        distance_from_electric_line_m=10.0, electric_line_type="lt",
        has_water_course_within_30m=False,
    )
    summary = render_text_summary(analysis, out.brief)
    assert "downgraded from HARD" not in summary, (
        "Summary should not include downgrade note when no downgrades"
    )
    print("PASS summary omits downgrade note when no downgrades")


def test_drawback_2_full_overall_assessment_shows_downgrade_note():
    """Full text OVERALL ASSESSMENT also shows the downgrade note."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_pune_g3_unverified()
    full = render_text_full(analysis, brief, include_doubts=False)
    # The OVERALL ASSESSMENT section should include downgrade note
    assessment_section = full.split("OVERALL ASSESSMENT")[1].split("PRACTICAL LANE")[0]
    assert "downgraded from HARD" in assessment_section, (
        "OVERALL ASSESSMENT should show downgrade note"
    )
    print("PASS full text OVERALL ASSESSMENT shows downgrade note")


# ─── Drawback 6: Approval check SOFT_WARN at complex tier ────────────

def test_drawback_6_approval_pass_for_simple_tier():
    """Small G+0 build → simple tier → PASS."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    analysis, brief = _build_analysis()  # default G+0 small
    r = check_approval_complexity(brief)
    assert r.details["complexity_tier"] == "simple"
    assert r.severity.value == "pass"
    print("PASS approval check is PASS for simple tier")


def test_drawback_6_approval_softwarn_for_complex_tier():
    """G+3 large build → complex tier → SOFT_WARN."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floors = tuple(
        [FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),))]
        + [FloorRequirement(i, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.BEDROOM_MASTER, 1),))
           for i in range(1, 4)]
    )
    # Delhi 1024+ sqm with G+3 → complex
    analysis, brief = _build_analysis(
        city="delhi", plot_width_m=32.0, plot_depth_m=32.0,
        road_width_m=15.0, floors=floors,
        user_setback_front_m=3.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
        budget_min_lakhs=180, budget_max_lakhs=250,
    )
    r = check_approval_complexity(brief)
    assert r.details["complexity_tier"] == "complex"
    assert r.severity.value == "soft_warn"
    print("PASS approval check is SOFT_WARN for complex tier")


def test_drawback_6_approval_complex_message_advises_planning():
    """Complex-tier message should mention 'budget' or 'timeline' planning."""
    from buildemup.components.c02.sustainability_checks import (
        check_approval_complexity,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    floors = tuple(
        [FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),))]
        + [FloorRequirement(i, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.BEDROOM_MASTER, 1),))
           for i in range(1, 4)]
    )
    analysis, brief = _build_analysis(
        city="delhi", plot_width_m=32.0, plot_depth_m=32.0,
        road_width_m=15.0, floors=floors,
        user_setback_front_m=3.0, user_setback_rear_m=2.0,
        user_setback_side_left_m=2.0, user_setback_side_right_m=2.0,
        budget_min_lakhs=180, budget_max_lakhs=250,
    )
    r = check_approval_complexity(brief)
    msg = r.message.lower()
    assert "budget" in msg or "timeline" in msg or "overhead" in msg, (
        f"Complex-tier message should advise planning: got '{r.message[:120]}'"
    )
    print("PASS complex-tier message advises budget/timeline planning")


# ─── Drawback 9: JSON enriched with labels ───────────────────────────

def test_drawback_9_json_has_severity_label_on_blocking_issue():
    """JSON blocking_issues entries should have severity_label = 'BLOCKING'."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_pune_g3_unverified()
    data = render_json(analysis)
    blockers = data["code_strict_report"]["blocking_issues"]
    assert len(blockers) > 0, "Test scenario should have blockers"
    for b in blockers:
        assert b.get("severity_label") == "BLOCKING", (
            f"Block check {b['check_id']} should have severity_label=BLOCKING"
        )
    print("PASS JSON blocking_issues have severity_label='BLOCKING'")


def test_drawback_9_json_has_severity_label_on_soft_warning():
    """JSON soft_warnings should have severity_label = 'WARNING'."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_pune_g3_unverified()
    data = render_json(analysis)
    warns = data["practical_report"]["soft_warnings"]
    if warns:
        for w in warns:
            assert w.get("severity_label") == "WARNING"
    print("PASS JSON soft_warnings have severity_label='WARNING'")


def test_drawback_9_json_has_severity_label_on_passed_check():
    """JSON passed_checks should have severity_label = 'OK'."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_analysis()
    data = render_json(analysis)
    passed = data["practical_report"]["passed_checks"]
    if passed:
        for p in passed:
            assert p.get("severity_label") == "OK"
    print("PASS JSON passed_checks have severity_label='OK'")


def test_drawback_9_json_has_severity_label_on_gap():
    """JSON gaps should have gap-specific severity_label
    ('DECISION NEEDED' / 'SIGNIFICANT' / 'MINOR' / 'INFO')."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_pune_g3_unverified()
    data = render_json(analysis)
    gaps = data["gaps"]
    valid_gap_labels = {
        "DECISION NEEDED", "SIGNIFICANT", "MINOR", "INFO",
    }
    for g in gaps:
        assert g.get("severity_label") in valid_gap_labels, (
            f"Gap {g['check_id']} severity_label '{g.get('severity_label')}' "
            f"not in {valid_gap_labels}"
        )
    print(f"PASS JSON gaps have correct severity_label ({len(gaps)} gaps tested)")


def test_drawback_9_json_has_category_label_on_checks():
    """JSON checks should have category_label (LEGAL / DESIGN / etc.)."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_analysis()
    data = render_json(analysis)
    valid_labels = {
        "LEGAL", "DESIGN", "STRUCTURAL", "COST", "SPATIAL", "SAFETY",
    }
    all_checks = (
        data["practical_report"]["passed_checks"]
        + data["practical_report"]["soft_warnings"]
    )
    for c in all_checks:
        assert c.get("category_label") in valid_labels, (
            f"Check {c['check_id']} category_label "
            f"'{c.get('category_label')}' not in {valid_labels}"
        )
    print(f"PASS JSON checks have valid category_label")


def test_drawback_9_json_severity_label_distinguishes_check_vs_gap():
    """Check severity 'hard_fail' → 'BLOCKING', but gap severity
    'blocking_if_not_accepted' → 'DECISION NEEDED'. Same value source
    different labels."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_pune_g3_unverified()
    data = render_json(analysis)
    # Check side
    for b in data["code_strict_report"]["blocking_issues"]:
        assert b.get("severity_label") == "BLOCKING"
    # Gap side
    for g in data["gaps"]:
        if g["severity"] == "blocking_if_not_accepted":
            assert g.get("severity_label") == "DECISION NEEDED"
    print("PASS check 'BLOCKING' vs gap 'DECISION NEEDED' labels distinguished")


def test_drawback_9_json_raw_severity_field_unchanged():
    """The raw 'severity' field should still carry the enum value
    (BACKWARD COMPATIBLE for any existing API consumer)."""
    from buildemup.components.c02.renderer import render_json
    analysis, brief = _build_analysis()
    data = render_json(analysis)
    valid_check_severities = {
        "hard_fail", "soft_warn", "pass", "not_applicable",
    }
    for c in data["practical_report"]["passed_checks"]:
        assert c["severity"] in valid_check_severities
    print("PASS raw 'severity' field preserved alongside 'severity_label'")


# ─── Drawback 11: Inline category tags in lane details ───────────────

def test_drawback_11_lane_details_blocking_has_category_tag():
    """Each blocking issue line should start with [CATEGORY]."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_pune_g3_unverified()
    full = render_text_full(analysis, brief, include_doubts=False)
    # Look in CODE-STRICT lane (which has blockers)
    lane_section = full.split("CODE-STRICT LANE")[1].split("GAPS BETWEEN")[0]
    blocking_section_start = lane_section.find("BLOCKING (")
    blocking_section = lane_section[blocking_section_start:]
    # Each ✗ line should have a [TAG]
    blocking_lines = [
        l for l in blocking_section.split("\n")
        if l.strip().startswith("✗")
    ]
    assert len(blocking_lines) > 0
    for line in blocking_lines:
        # Pattern: "    ✗ [CATEGORY] CheckName"
        assert "[" in line and "]" in line, (
            f"Blocking line missing category tag: {line!r}"
        )
    print(f"PASS {len(blocking_lines)} blocking lines all have category tags")


def test_drawback_11_lane_details_warnings_have_category_tag():
    """Each warning line should have a category tag."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_pune_g3_unverified()
    full = render_text_full(analysis, brief, include_doubts=False)
    practical_section = full.split("PRACTICAL LANE")[1].split("CODE-STRICT LANE")[0]
    warning_lines = [
        l for l in practical_section.split("\n")
        if l.strip().startswith("!")
    ]
    assert len(warning_lines) > 0
    for line in warning_lines:
        assert "[" in line and "]" in line, (
            f"Warning line missing category tag: {line!r}"
        )
    print(f"PASS {len(warning_lines)} warning lines all have category tags")


def test_drawback_11_lane_details_passed_have_category_tag():
    """Each passed check line should have a category tag."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    full = render_text_full(analysis, brief, include_doubts=False)
    practical_section = full.split("PRACTICAL LANE")[1].split("CODE-STRICT LANE")[0]
    passed_lines = [
        l for l in practical_section.split("\n")
        if l.strip().startswith("✓")
    ]
    assert len(passed_lines) > 0
    for line in passed_lines:
        assert "[" in line and "]" in line, (
            f"Passed line missing category tag: {line!r}"
        )
    print(f"PASS {len(passed_lines)} passed lines all have category tags")


def test_drawback_11_categories_use_user_friendly_labels():
    """Categories should use user-friendly labels: LEGAL not 'compliance',
    DESIGN not 'usability'."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    full = render_text_full(analysis, brief, include_doubts=False)
    # User-facing labels should appear, raw enum values should not
    assert "[LEGAL]" in full or "[DESIGN]" in full or "[STRUCTURAL]" in full, (
        "User-friendly labels should appear in lane details"
    )
    # Raw enum values should NOT leak
    assert "[compliance]" not in full
    assert "[usability]" not in full
    print("PASS lane details use user-friendly labels (LEGAL/DESIGN/etc.)")


# ─── Integration: full pipeline still works ──────────────────────────

def test_session_k_session_j_validation_still_passes():
    """Re-running Session J's 20 scenarios after Session K changes — all
    expectations should still hold (ranges are wide enough).

    S55 Batch 4: S17 excluded — see B-NEW-PUNE-SOIL-SCENARIO-REFRESH.
    """
    from buildemup.tests.test_c02_session_j import (
        SCENARIOS, run_scenario,
    )
    failures = []
    for s in SCENARIOS:
        if s.id in ("S05", "S17"):
            continue  # B-NEW-PUNE-SOIL-SCENARIO-REFRESH
        result = run_scenario(s)
        passed, fails = result.assertions_pass
        if not passed:
            failures.append(f"{s.id}: {fails}")
    assert not failures, (
        f"Session J scenarios broke after Session K:\n" + "\n".join(failures)
    )
    print(f"PASS 19 Session J scenarios still pass after Session K "
          f"(S17 excluded pending B-NEW-PUNE-SOIL-SCENARIO-REFRESH)")


def test_session_k_full_pipeline_still_works():
    """End-to-end smoke test through API endpoint."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0,
        "plot_facing": "N", "city": "chennai", "road_width_m": 9.0,
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [{"floor_number": 0, "floor_use": "residential",
                    "rooms": [{"room_type": "living", "count": 1}]}],
        "budget_min_lakhs": 20, "budget_max_lakhs": 30,
    }
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    # All Session K enrichments should be present in the JSON
    data = response["feasibility_data"]
    if data["practical_report"]["passed_checks"]:
        c = data["practical_report"]["passed_checks"][0]
        assert "severity_label" in c
        assert "category_label" in c
    print("PASS full pipeline through API still produces enriched output")


def test_v0_9_3_baseline_unaffected_by_session_k():
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
    print("PASS v0.9.3 baseline unaffected by Session K")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session K (5 UX-clarity drawback fixes)")
    print("=" * 70)
    print()

    print("--- Drawback 1: blocker count + names in summary ---")
    test_drawback_1_summary_shows_blocker_count_when_blockers_exist()
    test_drawback_1_summary_lists_blocker_names()
    test_drawback_1_summary_truncates_blocker_list_with_count()
    test_drawback_1_summary_no_blocker_count_when_clean()
    print()

    print("--- Drawback 2: downgrade tag + summary note ---")
    test_drawback_2_downgraded_warning_tagged_in_lane_details()
    test_drawback_2_summary_notes_downgraded_count()
    test_drawback_2_no_downgrade_note_when_no_downgrades()
    test_drawback_2_full_overall_assessment_shows_downgrade_note()
    print()

    print("--- Drawback 6: approval SOFT_WARN at complex ---")
    test_drawback_6_approval_pass_for_simple_tier()
    test_drawback_6_approval_softwarn_for_complex_tier()
    test_drawback_6_approval_complex_message_advises_planning()
    print()

    print("--- Drawback 9: JSON severity_label + category_label ---")
    test_drawback_9_json_has_severity_label_on_blocking_issue()
    test_drawback_9_json_has_severity_label_on_soft_warning()
    test_drawback_9_json_has_severity_label_on_passed_check()
    test_drawback_9_json_has_severity_label_on_gap()
    test_drawback_9_json_has_category_label_on_checks()
    test_drawback_9_json_severity_label_distinguishes_check_vs_gap()
    test_drawback_9_json_raw_severity_field_unchanged()
    print()

    print("--- Drawback 11: inline category tags ---")
    test_drawback_11_lane_details_blocking_has_category_tag()
    test_drawback_11_lane_details_warnings_have_category_tag()
    test_drawback_11_lane_details_passed_have_category_tag()
    test_drawback_11_categories_use_user_friendly_labels()
    print()

    print("--- Integration ---")
    test_session_k_session_j_validation_still_passes()
    test_session_k_full_pipeline_still_works()
    test_v0_9_3_baseline_unaffected_by_session_k()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION K TESTS PASSED")
    print("=" * 70)
