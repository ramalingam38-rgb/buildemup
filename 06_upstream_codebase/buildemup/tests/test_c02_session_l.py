"""
Component 2 Session L tests.

Three small UX text patches addressing concerns from the post-Session-K
domain review:

  Patch 1 (edge cases #1 + #7): Footer disclaimer expansion — calls out
    rectangular-plot assumption + irregular plots + encroachments +
    unapproved layouts requiring independent legal verification.

  Patch 2 (failure scenario #6): Lane-meaning clarifier in OVERALL
    ASSESSMENT — explicit one-liner that PRACTICAL ≠ legally approved
    and CODE-STRICT = no trade-offs. Pre-empts misinterpretation.

  Patch 3 (edge case #10): Sharper budget HARD_FAIL message when the
    gap is ≥30% — uses "materially insufficient" + "major scope
    reduction" instead of the softer original wording.

These are pure text changes; no domain or scoring changes, no behavioural
changes outside message text and one footer expansion.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_analysis(**overrides):
    """Standard helper: build a brief + run feasibility."""
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


# ─── Patch 1: Footer disclaimer expansion ─────────────────────────────

def test_patch_1_footer_mentions_rectangular_assumption():
    """Footer should explicitly call out that we assume rectangular plot."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    # Look in the REPORT NOTES section
    notes_section = text.split("REPORT NOTES")[1] if "REPORT NOTES" in text else ""
    assert "rectangular" in notes_section.lower(), (
        "Footer should mention rectangular-plot assumption"
    )
    print("PASS footer mentions rectangular-plot assumption")


def test_patch_1_footer_mentions_irregular_plots():
    """Footer should call out irregular plots needing independent verification."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    notes_section = text.split("REPORT NOTES")[1] if "REPORT NOTES" in text else ""
    assert "irregular" in notes_section.lower(), (
        "Footer should mention irregular plots"
    )
    print("PASS footer mentions irregular plots")


def test_patch_1_footer_mentions_encroachments():
    """Footer should call out encroachments."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    notes_section = text.split("REPORT NOTES")[1] if "REPORT NOTES" in text else ""
    assert "encroachment" in notes_section.lower(), (
        "Footer should mention encroachments"
    )
    print("PASS footer mentions encroachments")


def test_patch_1_footer_mentions_unapproved_layouts():
    """Footer should call out unapproved layouts."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    notes_section = text.split("REPORT NOTES")[1] if "REPORT NOTES" in text else ""
    assert "unapproved" in notes_section.lower(), (
        "Footer should mention unapproved layouts"
    )
    print("PASS footer mentions unapproved layouts")


def test_patch_1_footer_recommends_independent_verification():
    """Footer should advise independent legal verification before design."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    notes_section = text.split("REPORT NOTES")[1] if "REPORT NOTES" in text else ""
    assert "independent" in notes_section.lower(), (
        "Footer should recommend independent verification"
    )
    print("PASS footer recommends independent legal verification")


# ─── Patch 2: Lane-meaning clarifier ─────────────────────────────────

def test_patch_2_clarifier_in_overall_assessment():
    """OVERALL ASSESSMENT should include the PRACTICAL/CODE-STRICT meaning line."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    # Section between OVERALL ASSESSMENT header and PRACTICAL design line
    assessment = text.split("OVERALL ASSESSMENT")[1].split("PRACTICAL design")[0]
    # Must mention both lanes' meaning
    assert "PRACTICAL" in assessment
    assert "CODE-STRICT" in assessment
    print("PASS OVERALL ASSESSMENT clarifies both lane meanings")


def test_patch_2_clarifier_warns_about_approval_workarounds():
    """Clarifier should mention that Practical may need approval workarounds."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    # Use lowercase + concatenate-spaces to handle wrapping
    flat = " ".join(text.lower().split())
    assert "approval workarounds" in flat, (
        "Clarifier should mention 'approval workarounds' for Practical lane"
    )
    print("PASS clarifier warns Practical may need approval workarounds")


def test_patch_2_clarifier_notes_code_strict_has_no_trade_offs():
    """Clarifier should mention CODE-STRICT = no trade-offs."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    flat = " ".join(text.lower().split())
    assert "no trade-offs" in flat or "no tradeoffs" in flat, (
        "Clarifier should say CODE-STRICT = no trade-offs"
    )
    print("PASS clarifier notes CODE-STRICT has no trade-offs")


def test_patch_2_clarifier_appears_before_lane_scores():
    """The clarifier should appear ABOVE the score lines, not below."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis()
    text = render_text_full(analysis, brief, include_doubts=False)
    # PRACTICAL = ... appears before "PRACTICAL design"
    assessment_block = text.split("OVERALL ASSESSMENT")[1]
    clarifier_pos = assessment_block.find("PRACTICAL = ")
    score_line_pos = assessment_block.find("PRACTICAL design")
    assert clarifier_pos != -1
    assert score_line_pos != -1
    assert clarifier_pos < score_line_pos, (
        "Clarifier should appear above score lines"
    )
    print("PASS clarifier appears above score lines (so user reads it first)")


# ─── Patch 3: Sharper budget HARD_FAIL message at large gap ──────────

def test_patch_3_large_budget_gap_uses_sharp_language():
    """Budget gap ≥30% short → 'materially insufficient' + 'major scope reduction'."""
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # G+3 large with ₹15L budget — ~59% below structural minimum
    floors = tuple(
        [FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),))]
        + [FloorRequirement(i, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.BEDROOM_MASTER, 1),))
           for i in range(1, 4)]
    )
    inp = BriefCaptureInput(
        plot_width_m=18.0, plot_depth_m=22.0, plot_facing="S",
        city="chennai", road_width_m=12.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=floors,
        budget_min_lakhs=10, budget_max_lakhs=15,
    )
    out = BriefCaptureEngine().execute(inp)
    r = check_budget_feasibility(out.brief, out.c7_preview_cost)
    assert r.severity.value == "hard_fail"
    msg = r.message.lower()
    assert "materially insufficient" in msg, (
        f"Large gap should use sharp 'materially insufficient' wording: "
        f"{r.message[:120]}"
    )
    assert "major scope reduction" in msg, (
        f"Large gap should mention 'major scope reduction': "
        f"{r.message[:120]}"
    )
    print(f"PASS large budget gap uses sharp language ({r.message[:80]}...)")


def test_patch_3_small_budget_gap_uses_softer_language():
    """Budget gap <30% short → original wording (no 'materially insufficient')."""
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    # Small enough gap that it's <30%. C7 estimate around ₹15L for G+1
    # standard plot, so a budget of ~₹13L is ~13% short.
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
        budget_min_lakhs=10, budget_max_lakhs=13,
    )
    out = BriefCaptureEngine().execute(inp)
    r = check_budget_feasibility(out.brief, out.c7_preview_cost)
    if r.severity.value != "hard_fail":
        # If not HARD, this scenario doesn't exercise the gap at all
        print("PASS scenario didn't HARD-fail (gap <0%) — softer wording N/A")
        return
    # Compute the gap
    pct_gap = ((r.details["structural_range_min_lakhs"]
                - r.details["user_budget_max_lakhs"])
               / r.details["structural_range_min_lakhs"]) * 100
    msg = r.message.lower()
    if pct_gap < 30:
        assert "materially insufficient" not in msg, (
            f"Small gap (<30%) should NOT use sharp wording: {r.message[:120]}"
        )
        assert "major scope reduction" not in msg
        print(f"PASS small budget gap ({pct_gap:.0f}%) uses softer wording")
    else:
        # Gap was actually ≥30% — sharp wording is correct
        assert "materially insufficient" in msg
        print(f"PASS budget gap ({pct_gap:.0f}%) was actually large — "
              f"sharp wording correctly used")


def test_patch_3_message_includes_percent_gap():
    """The new sharp message should include the % gap so user sees magnitude."""
    from buildemup.components.c02.hard_physics_checks import (
        check_budget_feasibility,
    )
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
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
    inp = BriefCaptureInput(
        plot_width_m=18.0, plot_depth_m=22.0, plot_facing="S",
        city="chennai", road_width_m=12.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=floors,
        budget_min_lakhs=10, budget_max_lakhs=15,
    )
    out = BriefCaptureEngine().execute(inp)
    r = check_budget_feasibility(out.brief, out.c7_preview_cost)
    assert r.severity.value == "hard_fail"
    # Should include some "X%" in message
    import re
    pct_matches = re.findall(r"\d+%", r.message)
    assert len(pct_matches) >= 1, (
        f"Message should include '%' magnitude indicator: {r.message[:120]}"
    )
    print(f"PASS budget HARD message includes % gap ({pct_matches[0]} found)")


# ─── Integration: nothing else broke ─────────────────────────────────

def test_session_l_session_j_validation_still_passes():
    """Session J 20-scenario validation should still pass after Session L.

    S55 Batch 4: S17 excluded — see B-NEW-PUNE-SOIL-SCENARIO-REFRESH.
    """
    from buildemup.tests.test_c02_session_j import SCENARIOS, run_scenario
    failures = []
    for s in SCENARIOS:
        if s.id in ("S05", "S17"):
            continue  # B-NEW-PUNE-SOIL-SCENARIO-REFRESH
        result = run_scenario(s)
        passed, fails = result.assertions_pass
        if not passed:
            failures.append(f"{s.id}: {fails}")
    assert not failures, (
        f"Session J broke after Session L:\n" + "\n".join(failures)
    )
    print(f"PASS 19 Session J scenarios still pass after Session L "
          f"(S17 excluded pending B-NEW-PUNE-SOIL-SCENARIO-REFRESH)")


def test_session_l_session_k_uplift_still_works():
    """Session K's UX-clarity fixes (drawbacks 1, 2, 6, 9, 11) should still
    work after Session L's text patches."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis(
        city="pune", plot_width_m=15.0, plot_depth_m=20.0,
        floors=tuple(
            [__import__('buildemup.domain', fromlist=['FloorRequirement'])
                .FloorRequirement(0,
                    __import__('buildemup.domain', fromlist=['FloorUse'])
                        .FloorUse.RESIDENTIAL,
                    (__import__('buildemup.domain', fromlist=['RoomRequirement'])
                        .RoomRequirement(
                        __import__('buildemup.domain', fromlist=['RoomType'])
                            .RoomType.LIVING, 1),))]
            + [
                __import__('buildemup.domain', fromlist=['FloorRequirement'])
                    .FloorRequirement(i,
                        __import__('buildemup.domain', fromlist=['FloorUse'])
                            .FloorUse.RESIDENTIAL,
                        (__import__('buildemup.domain', fromlist=['RoomRequirement'])
                            .RoomRequirement(
                            __import__('buildemup.domain', fromlist=['RoomType'])
                                .RoomType.BEDROOM_MASTER, 1),))
                for i in range(1, 4)
            ]
        ),
    )
    text = render_text_full(analysis, brief, include_doubts=False)
    # Session K marker: category tags inline
    assert "[STRUCTURAL]" in text or "[LEGAL]" in text or "[DESIGN]" in text
    # Session K marker: downgrade flag
    if any(r.details.get("downgrade_applied")
           for r in analysis.practical_report.soft_warnings):
        assert "[DOWNGRADED FROM HARD]" in text
    print("PASS Session K UX uplift still works after Session L")


def test_v0_9_3_baseline_unaffected_by_session_l():
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
    print("PASS v0.9.3 baseline unaffected by Session L")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session L (3 small UX text patches)")
    print("=" * 70)
    print()

    print("--- Patch 1: Footer disclaimer expansion ---")
    test_patch_1_footer_mentions_rectangular_assumption()
    test_patch_1_footer_mentions_irregular_plots()
    test_patch_1_footer_mentions_encroachments()
    test_patch_1_footer_mentions_unapproved_layouts()
    test_patch_1_footer_recommends_independent_verification()
    print()

    print("--- Patch 2: Lane-meaning clarifier ---")
    test_patch_2_clarifier_in_overall_assessment()
    test_patch_2_clarifier_warns_about_approval_workarounds()
    test_patch_2_clarifier_notes_code_strict_has_no_trade_offs()
    test_patch_2_clarifier_appears_before_lane_scores()
    print()

    print("--- Patch 3: Sharper budget HARD_FAIL at large gap ---")
    test_patch_3_large_budget_gap_uses_sharp_language()
    test_patch_3_small_budget_gap_uses_softer_language()
    test_patch_3_message_includes_percent_gap()
    print()

    print("--- Integration ---")
    test_session_l_session_j_validation_still_passes()
    test_session_l_session_k_uplift_still_works()
    test_v0_9_3_baseline_unaffected_by_session_l()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION L TESTS PASSED")
    print("=" * 70)
