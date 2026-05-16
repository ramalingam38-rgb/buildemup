"""
v0.9.1 patch tests — drawback fixes from second post-v0.9 review.

Covers:
  #1+#2 — Cost framing: cited 2.5× breakdown replaces ×1.5-2.0 heuristic
  #3    — Net usable shown as 80-90% range, not 85% point
  #5    — Parking message starts with "[Preliminary check..."
  #6    — KB version + authority surfaced in assumptions
  #8    — risk_drivers explain WHY risk is LOW/MEDIUM/HIGH
  #9    — guidance grouped by category
  #10   — vastu "may conflict" note
  #14   — "Step 1 of 6" roadmap framing
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json


def _minimal_floors():
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


def _api_payload(**overrides):
    base = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0, "plot_facing": "N",
        "city": "chennai", "road_width_m": 9.0,
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [{"floor_number": 0, "floor_use": "residential",
                    "rooms": [{"room_type": "living", "count": 1},
                              {"room_type": "kitchen", "count": 1}]}],
        "budget_min_lakhs": 20, "budget_max_lakhs": 30,
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────
# Drawback #14 — "Step 1 of 6" roadmap framing
# ─────────────────────────────────────────────────────────────────────────

def test_explain_shows_step_1_of_6_banner():
    """Top of explain() positions output as step 1 of 6."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    text = engine.explain(inp, engine.execute(inp))
    assert "STEP 1 OF 6" in text
    assert "Brief Capture" in text
    assert "Feasibility check" in text
    assert "Procurement" in text
    print("PASS explain() shows 'STEP 1 OF 6' roadmap banner")


def test_api_response_includes_roadmap_position():
    """API response includes roadmap_position with all 6 steps."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    assert status == 200
    rp = body["roadmap_position"]
    assert rp["current_step"] == 1
    assert rp["total_steps"] == 6
    assert rp["current_name"] == "Brief Capture"
    # 5 steps ahead
    assert len(rp["steps_ahead"]) == 5
    # Disclaimer present
    assert "directional" in rp["disclaimer"].lower()
    print("PASS API includes roadmap_position with 6-step journey")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #8 — risk_drivers explain WHY
# ─────────────────────────────────────────────────────────────────────────

def test_compute_risk_drivers_low():
    """LOW risk → single 'no concerns' driver."""
    from buildemup.components.c01.soft_guide_engine import (
        compute_risk_drivers,
    )
    drivers = compute_risk_drivers([], "LOW")
    assert len(drivers) == 1
    assert "no critical" in drivers[0].lower() or "no concerns" in drivers[0].lower()
    print("PASS LOW risk gets a 'no concerns' driver")


def test_compute_risk_drivers_high_lists_strong_concerns():
    """HIGH risk → driver list mentions STRONG_CONCERN messages."""
    from buildemup.components.c01.soft_guide_engine import (
        compute_risk_drivers,
    )
    from buildemup.domain.brief import GuidanceMessage, GuidanceSeverity
    msgs = [
        GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text="Front setback 0.3m below DCR minimum 1.5m. Reduce or relocate.",
            context="setback_violation_front",
            action_verb="Reduce",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text="Vastu: main door faces SE which is auspicious.",
            context="vastu_main_door",
            action_verb="Note",
        ),
    ]
    drivers = compute_risk_drivers(msgs, "HIGH")
    # Should include the strong concern, not the info
    joined = " ".join(drivers).lower()
    assert "front setback" in joined
    assert "main door" not in joined  # info skipped
    assert any(d.startswith("Critical:") for d in drivers)
    print(f"PASS HIGH risk drivers list strong concerns "
          f"({len(drivers)} drivers)")


def test_explain_shows_risk_drivers_under_banner():
    """explain() includes 'Why:' followed by drivers under risk banner."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    # Force HIGH risk with bad setbacks
    inp = _minimal_input(user_setback_front_m=0.3)
    text = engine.explain(inp, engine.execute(inp))
    assert "Overall risk level: HIGH" in text
    assert "Why:" in text
    assert "Critical:" in text
    print("PASS explain() shows 'Why:' + drivers under HIGH risk banner")


def test_api_includes_risk_drivers():
    """API response top-level has risk_drivers list."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    # HIGH risk
    status, body = handle_brief_capture(json.dumps(_api_payload(
        user_setback_front_m=0.3,
    )))
    assert status == 200
    assert body["risk_level"] == "HIGH"
    assert isinstance(body["risk_drivers"], list)
    assert len(body["risk_drivers"]) >= 1
    # All drivers for HIGH should start with "Critical:"
    assert all(d.startswith("Critical:") for d in body["risk_drivers"])
    print(f"PASS API risk_drivers populated for HIGH risk: "
          f"{len(body['risk_drivers'])} drivers")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #9 — guidance grouped by category
# ─────────────────────────────────────────────────────────────────────────

def test_group_guidance_by_category():
    """group_guidance_by_category buckets messages by context prefix."""
    from buildemup.components.c01.soft_guide_engine import (
        group_guidance_by_category,
    )
    from buildemup.domain.brief import GuidanceMessage, GuidanceSeverity
    msgs = [
        GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN, text="x",
            context="setback_violation_front", action_verb="Fix",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO, text="y",
            context="parking_feasibility", action_verb="Note",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO, text="z",
            context="vastu_main_door", action_verb="Note",
        ),
        GuidanceMessage(
            severity=GuidanceSeverity.INFO, text="w",
            context="budget_aligned", action_verb="Note",
        ),
    ]
    grouped = group_guidance_by_category(msgs)
    assert "Compliance" in grouped
    assert "Parking" in grouped
    assert "Vastu (cultural)" in grouped
    assert "Budget" in grouped
    assert len(grouped["Compliance"]) == 1
    print(f"PASS guidance grouped into {len(grouped)} categories")


def test_api_includes_guidance_by_category():
    """API response has soft_guidance_by_category dict."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload(
        vastu_preference="partial",
    )))
    assert status == 200
    grouped = body["soft_guidance_by_category"]
    assert isinstance(grouped, dict)
    # With vastu=partial, must have at least Vastu category
    assert "Vastu (cultural)" in grouped
    # Each category is a list of message dicts with proper shape
    for category, msgs in grouped.items():
        assert isinstance(msgs, list)
        if msgs:
            assert "severity" in msgs[0]
            assert "text" in msgs[0]
            assert "context" in msgs[0]
    print(f"PASS API soft_guidance_by_category has "
          f"{len(grouped)} categories")


def test_explain_shows_grouped_guidance_section():
    """explain() COMPLETE GUIDANCE section uses category headers."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input(vastu_preference="partial")
    text = engine.explain(inp, engine.execute(inp))
    # Look for the category-header pattern "── Category (N item(s)) ──"
    # at least one category should appear
    import re
    headers = re.findall(r"── (.+?) \(\d+ item", text)
    assert len(headers) >= 1
    print(f"PASS explain() shows grouped guidance "
          f"({len(headers)} category headers found)")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #1 + #2 — cost framing rewritten
# ─────────────────────────────────────────────────────────────────────────

def test_explain_cost_section_shows_aecord_breakdown():
    """BUDGET section shows 40/25/15/12/8 industry breakdown."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    text = engine.explain(inp, engine.execute(inp))
    # AECORD-cited breakdown numbers
    assert "Structure 40%" in text
    assert "Finishing 25%" in text
    assert "MEP 15%" in text
    assert "Interior 12%" in text
    assert "Misc 8%" in text
    # Source citation
    assert "AECORD" in text or "industry guides" in text
    # Old wrong heuristic (×1.5-2.0) should be gone
    assert "× 1.5-2.0" not in text
    assert "× 1.5 to 2.0" not in text
    print("PASS BUDGET section shows AECORD 40/25/15/12/8 breakdown")


def test_explain_cost_de_emphasizes_exact_value():
    """Range shown first, exact in parens with disclaimer."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    text = engine.explain(inp, engine.execute(inp))
    # Both range and exact present, but disclaimer prominent
    assert "Structural estimate" in text
    assert "most-likely point" in text
    assert "DO NOT TREAT AS A QUOTE" in text
    print("PASS cost section de-emphasizes exact, leads with range "
          "+ DO NOT TREAT AS A QUOTE")


def test_api_includes_aecord_cost_breakdown():
    """API response has all_in_cost_estimate_lakhs with breakdown_pct."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    assert status == 200
    estimate = body["all_in_cost_estimate_lakhs"]
    assert estimate is not None
    # Cited breakdown
    bp = estimate["breakdown_pct"]
    assert bp["structure"] == 40
    assert bp["finishing"] == 25
    assert bp["mep"] == 15
    assert bp["interior"] == 12
    assert bp["miscellaneous"] == 8
    # Sum = 100
    assert sum(bp.values()) == 100
    # Source citation
    assert "AECORD" in estimate["source"]
    # Disclaimer
    assert "quote" in estimate["disclaimer"].lower()
    # Typical = 2.5× exact (within rounding)
    typical = estimate["typical"]
    exact = body["c7_preview_cost_lakhs"]
    ratio = typical / exact
    assert 2.45 < ratio < 2.55, f"Expected ~2.5×, got {ratio:.2f}"
    print(f"PASS API all-in cost: typical={typical}L "
          f"(2.5× structural {exact}L) + 40/25/15/12/8 breakdown")


def test_api_cost_estimate_low_high_uses_2_to_3_multiplier():
    """all_in low = 2.0× range_min, high = 3.0× range_max."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    estimate = body["all_in_cost_estimate_lakhs"]
    range_lakhs = body["c7_preview_cost_range_lakhs"]
    # Low = 2.0× range_min (lean finishes scenario)
    expected_low = round(range_lakhs[0] * 2.0, 1)
    assert estimate["low"] == expected_low
    # High = 3.0× range_max (premium finishes scenario)
    expected_high = round(range_lakhs[1] * 3.0, 1)
    assert estimate["high"] == expected_high
    print(f"PASS all-in low/high uses 2.0× / 3.0× brackets")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #3 — net usable as range
# ─────────────────────────────────────────────────────────────────────────

def test_output_has_net_usable_low_and_high():
    """BriefCaptureOutput has 80% and 90% bounds."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    # 80% < 85% < 90%
    assert output.net_usable_low_sqm < output.net_usable_sqm
    assert output.net_usable_sqm < output.net_usable_high_sqm
    # Math check: low = gross * 0.80
    assert abs(output.net_usable_low_sqm - output.gross_envelope_sqm * 0.80) < 0.01
    assert abs(output.net_usable_high_sqm - output.gross_envelope_sqm * 0.90) < 0.01
    print(f"PASS net usable range: {output.net_usable_low_sqm:.0f}-"
          f"{output.net_usable_high_sqm:.0f} sqm "
          f"(midpoint {output.net_usable_sqm:.0f})")


def test_explain_shows_net_usable_as_range():
    """explain() PLOT section shows '80-90%' range, not '85%'."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "80-90%" in text
    assert "Final layout" in text  # Component 4 disclaimer
    print("PASS explain() shows net usable as 80-90% range")


def test_api_includes_net_usable_range():
    """API response has both low and high bounds."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    summary = body["brief_summary"]
    assert "net_usable_low_sqm" in summary
    assert "net_usable_high_sqm" in summary
    assert summary["net_usable_low_sqm"] < summary["net_usable_high_sqm"]
    print(f"PASS API net usable range: "
          f"{summary['net_usable_low_sqm']}-"
          f"{summary['net_usable_high_sqm']} sqm")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #5 — parking wording
# ─────────────────────────────────────────────────────────────────────────

def test_parking_message_starts_with_preliminary_check():
    """Critical + marginal parking msgs both lead with [Preliminary check..."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    # Critical case (<6m)
    msgs_critical = check_parking_feasibility(
        plot_width_m=5.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.0, side_right_setback_m=1.0,
    )
    assert len(msgs_critical) == 1
    assert msgs_critical[0].text.startswith("[Preliminary check")
    assert "layout-dependent" in msgs_critical[0].text

    # Marginal case (6-8m)
    msgs_marginal = check_parking_feasibility(
        plot_width_m=7.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.5, side_right_setback_m=1.5,
    )
    assert len(msgs_marginal) == 1
    assert msgs_marginal[0].text.startswith("[Preliminary check")
    print("PASS both parking messages prefixed with [Preliminary check]")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #6 — KB version + authority in assumptions
# ─────────────────────────────────────────────────────────────────────────

def test_assumptions_include_kb_version():
    """Assumptions list includes 'KB version: <ver>' line."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input(city="mumbai",
        user_setback_front_m=4.5))  # mumbai requires 4.5m front
    joined = " ".join(output.assumptions_used)
    assert "KB version:" in joined
    # Mumbai DCPR 2034 should appear in the authority line
    assert "DCPR 2034" in joined or "MCGM" in joined
    print(f"PASS assumptions disclose KB version + authority")


def test_kb_versions_use_modern_version_field():
    """v0.9.1 fix: kb_versions reads _version (not legacy kb_version).

    S54-004 (May 2026): version bumped from v3 → v4. Test relaxed to
    accept any non-legacy version — the real intent is to confirm the
    engine reads `_version` (not the legacy `kb_version` field which
    stayed pinned at v1).
    """
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    # Setback rules KB _version was bumped v1 → v2 → v3 → v4 across sessions.
    # Bug to catch: pre-v0.9.1 read the legacy kb_version which stayed at _v1.
    setback_ver = output.kb_versions["setback_rules"]
    assert "_v1" not in setback_ver, (
        f"Expected modern _version field (v2+), got {setback_ver} (bug: "
        f"reading legacy kb_version instead of _version)"
    )
    # Must match Setbacks_India_2026_v<N> shape with N >= 2
    import re
    match = re.search(r"_v(\d+)$", setback_ver)
    assert match is not None, (
        f"Setback version doesn't match expected shape: {setback_ver}"
    )
    assert int(match.group(1)) >= 2, (
        f"Expected version v2 or newer, got {setback_ver}"
    )
    print(f"PASS kb_versions reads _version correctly: {setback_ver}")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #10 — vastu "may conflict" note
# ─────────────────────────────────────────────────────────────────────────

def test_vastu_section_includes_conflict_note():
    """Vastu section warns 'may conflict with optimal structural/layout'."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input(vastu_preference="partial")
    text = engine.explain(inp, engine.execute(inp))
    # Find vastu section
    assert "VASTU GUIDANCE" in text
    assert "may conflict" in text
    assert "engineering wins" in text.lower()
    print("PASS vastu section warns about conflicts + 'engineering wins'")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9.1 — Patch Tests (post-v0.9 review)")
    print("=" * 70)
    print()
    print("--- Drawback #14: Step 1 of 6 framing ---")
    test_explain_shows_step_1_of_6_banner()
    test_api_response_includes_roadmap_position()
    print()
    print("--- Drawback #8: risk_drivers ---")
    test_compute_risk_drivers_low()
    test_compute_risk_drivers_high_lists_strong_concerns()
    test_explain_shows_risk_drivers_under_banner()
    test_api_includes_risk_drivers()
    print()
    print("--- Drawback #9: guidance grouped by category ---")
    test_group_guidance_by_category()
    test_api_includes_guidance_by_category()
    test_explain_shows_grouped_guidance_section()
    print()
    print("--- Drawback #1+#2: cost framing rewritten ---")
    test_explain_cost_section_shows_aecord_breakdown()
    test_explain_cost_de_emphasizes_exact_value()
    test_api_includes_aecord_cost_breakdown()
    test_api_cost_estimate_low_high_uses_2_to_3_multiplier()
    print()
    print("--- Drawback #3: net usable range ---")
    test_output_has_net_usable_low_and_high()
    test_explain_shows_net_usable_as_range()
    test_api_includes_net_usable_range()
    print()
    print("--- Drawback #5: parking wording ---")
    test_parking_message_starts_with_preliminary_check()
    print()
    print("--- Drawback #6: KB version traceability ---")
    test_assumptions_include_kb_version()
    test_kb_versions_use_modern_version_field()
    print()
    print("--- Drawback #10: vastu conflict note ---")
    test_vastu_section_includes_conflict_note()
    print()
    print("=" * 70)
    print("ALL V0.9.1 PATCH TESTS PASSED")
    print("=" * 70)
