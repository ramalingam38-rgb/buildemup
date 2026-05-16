"""
v0.9 Session A tests — drawback fixes + circulation + envelope transparency.

Covers the 6 v0.9 changes:
  #2 — Budget range framing in explain()
  #3 — Envelope transparency (gross vs net usable)
  #4 — Parking wording (layout-dependent)
  #5 — Size-aware circulation factor (already covered in Session 2)
  #6 — Vastu cultural-preference label
  #8 — risk_level replaces ready_for_downstream
  #9 — Top-3 cumulative summary line
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


# ─────────────────────────────────────────────────────────────────────────
# Drawback #8 — risk_level replaces ready_for_downstream
# ─────────────────────────────────────────────────────────────────────────

def test_risk_level_low_when_no_concerns():
    """Compliant brief with aligned budget → risk_level=LOW."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    assert output.risk_level == "LOW", f"Expected LOW, got {output.risk_level}"
    print(f"PASS clean brief → risk_level=LOW")


def test_risk_level_high_on_setback_violation():
    """Non-compliant setbacks → STRONG_CONCERN → risk_level=HIGH."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input(
        user_setback_front_m=0.3, user_setback_side_left_m=0.3,
    ))
    assert output.risk_level == "HIGH"
    print(f"PASS bad setbacks → risk_level=HIGH")


def test_proceed_with_warnings_always_true():
    """v0.1: we never block. proceed_with_warnings=True always."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    # Both clean and dirty inputs
    for inp in [_minimal_input(),
                _minimal_input(user_setback_front_m=0.3)]:
        output = BriefCaptureEngine().execute(inp)
        assert output.proceed_with_warnings is True
    print("PASS proceed_with_warnings=True even with STRONG_CONCERN")


def test_ready_for_downstream_backwards_compat_alias():
    """Deprecated property still returns sensible value."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    # Clean case → ready = True
    output_clean = BriefCaptureEngine().execute(_minimal_input())
    assert output_clean.ready_for_downstream is True
    # HIGH risk → ready = False (matches old semantics)
    output_bad = BriefCaptureEngine().execute(_minimal_input(
        user_setback_front_m=0.3,
    ))
    assert output_bad.ready_for_downstream is False
    print("PASS ready_for_downstream alias preserved for back-compat")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #3 — Envelope transparency (gross vs net usable)
# ─────────────────────────────────────────────────────────────────────────

def test_gross_envelope_computed_correctly():
    """Gross envelope = (plot_w - side_setbacks) × (plot_d - front/rear)."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    # 12×15 plot, 1.5m all setbacks → 9×12 = 108 sqm
    output = BriefCaptureEngine().execute(_minimal_input())
    assert abs(output.envelope_width_m - 9.0) < 0.01
    assert abs(output.envelope_depth_m - 12.0) < 0.01
    assert abs(output.gross_envelope_sqm - 108.0) < 0.1
    print(f"PASS gross envelope: 12×15 - 1.5×4 → "
          f"{output.envelope_width_m}×{output.envelope_depth_m} "
          f"= {output.gross_envelope_sqm:.0f} sqm")


def test_net_usable_is_85pct_of_gross():
    """Net usable = 85% of gross envelope per v0.9 efficiency factor."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    expected_net = output.gross_envelope_sqm * 0.85
    assert abs(output.net_usable_sqm - expected_net) < 0.1
    assert output.net_usable_sqm < output.gross_envelope_sqm
    print(f"PASS net usable: {output.gross_envelope_sqm:.0f} × 0.85 "
          f"= {output.net_usable_sqm:.0f} sqm")


def test_explain_shows_gross_and_net_envelope():
    """explain() PLOT section shows both gross and net usable."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    assert "Gross envelope" in rendered
    assert "Net usable" in rendered
    # v0.9.1: was "85%", now shown as "80-90% typical" range
    assert ("85%" in rendered) or ("80-90%" in rendered) or ("80-90" in rendered)
    assert "Component 4" in rendered  # disclosure of refinement
    print("PASS explain() shows gross + net envelope with disclosure")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #5 — Size-aware circulation factor
# ─────────────────────────────────────────────────────────────────────────

def test_circulation_factor_reflected_in_output():
    """Output fields circulation_factor_applied + size_label are populated."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    assert output.circulation_factor_applied in (1.30, 1.35, 1.40)
    assert output.circulation_size_label in ("small", "typical", "large")
    print(f"PASS circulation factor output: "
          f"{output.circulation_factor_applied} "
          f"({output.circulation_size_label})")


def test_circulation_factor_appears_in_assumptions():
    """ASSUMPTIONS USED includes the actual factor applied + size band."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    output = BriefCaptureEngine().execute(_minimal_input())
    joined = " ".join(output.assumptions_used)
    # The factor value should appear (e.g., "1.40")
    assert f"{output.circulation_factor_applied:.2f}" in joined
    assert output.circulation_size_label in joined
    assert "IS 3861" in joined  # source citation
    print(f"PASS assumptions include factor "
          f"{output.circulation_factor_applied:.2f} "
          f"({output.circulation_size_label}) + IS 3861 source")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #9 — Top-3 cumulative summary
# ─────────────────────────────────────────────────────────────────────────

def test_top_3_summary_line_shows_cumulative_counts():
    """explain() shows 'Showing top N of TOTAL' line + severity counts."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    # vastu=full generates 15 vastu messages + 3 non-vastu = 18+ total
    inp = _minimal_input(vastu_preference="full")
    rendered = engine.explain(inp, engine.execute(inp))
    # Must contain "Showing top"
    assert "Showing top" in rendered
    assert "total recommendations" in rendered
    # Must contain severity breakdown
    assert "critical" in rendered
    assert "concerns" in rendered
    assert "info items" in rendered
    print("PASS top-3 summary line shows 'Showing top N of TOTAL' + counts")


def test_risk_level_banner_in_top_3_section():
    """Risk level banner appears after top-3."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    assert "Overall risk level:" in rendered
    # Clean brief → LOW
    assert "LOW" in rendered
    print("PASS risk level banner in explain()")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #2 — Budget range framing
# ─────────────────────────────────────────────────────────────────────────

def test_budget_section_leads_with_range():
    """BUDGET section shows range prominently, exact as secondary."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    # Must have range format "Rs X.XL - Rs Y.YL"
    assert "Structural estimate" in rendered
    # Must have DIRECTIONAL framing
    assert "DIRECTIONAL" in rendered or "directional" in rendered.lower()
    # v0.9.1 changed phrasing from "not a quote" to "DO NOT TREAT AS A QUOTE"
    assert ("not a quote" in rendered.lower()
            or "do not treat as a quote" in rendered.lower())
    print("PASS BUDGET leads with range + directional framing")


def test_budget_section_lists_exclusions():
    """Budget section explicitly lists what's NOT included."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    rendered = engine.explain(inp, engine.execute(inp))
    # 4 major exclusions called out
    assert "Finishes" in rendered
    assert "Contractor margin" in rendered
    assert "MEP" in rendered
    assert "Interiors" in rendered
    # All-in estimate heuristic present
    assert "ALL-IN" in rendered
    # "What can change" subsection
    assert "Soil test" in rendered
    print("PASS BUDGET lists 4 exclusions + all-in heuristic + "
          "what-can-change subsection")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #6 — Vastu cultural label
# ─────────────────────────────────────────────────────────────────────────

def test_vastu_section_labelled_cultural():
    """Vastu section explicitly says CULTURAL PREFERENCE."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    inp = _minimal_input(vastu_preference="partial")
    rendered = engine.explain(inp, engine.execute(inp))
    # Must have explicit cultural label
    assert "CULTURAL PREFERENCE" in rendered
    assert "NOT A TECHNICAL REQUIREMENT" in rendered
    # Must say engineering takes precedence
    assert "Engineering and legal compliance take" in rendered \
        or "precedence" in rendered
    print("PASS vastu section labelled CULTURAL PREFERENCE + "
          "engineering precedence note")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #4 — Parking wording (layout-dependent)
# ─────────────────────────────────────────────────────────────────────────

def test_parking_messages_acknowledge_layout_dependency():
    """Parking warnings cite 'layout' and 'Component 4' as arbiters."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    from buildemup.domain import GuidanceSeverity
    # Narrow plot triggering STRONG_CONCERN
    msgs = check_parking_feasibility(
        plot_width_m=7.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.5, side_right_setback_m=1.5,
    )
    assert len(msgs) == 1
    text = msgs[0].text.lower()
    # New wording must include conditional language
    assert "depending on" in text or "likely" in text
    # Must reference Component 4 / final layout
    assert "component 4" in text or "layout" in text
    print(f"PASS parking message acknowledges layout dependency")


def test_parking_critical_message_mentions_component_4():
    """Critical case (<6m) also cites Component 4."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    msgs = check_parking_feasibility(
        plot_width_m=5.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.0, side_right_setback_m=1.0,
    )
    assert len(msgs) == 1
    assert "Component 4" in msgs[0].text or "layout" in msgs[0].text.lower()
    print("PASS critical parking message mentions Component 4")


# ─────────────────────────────────────────────────────────────────────────
# API layer — new fields in response
# ─────────────────────────────────────────────────────────────────────────

def test_api_response_includes_risk_level():
    """API response has risk_level + proceed_with_warnings."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0, "plot_facing": "N",
        "city": "chennai", "road_width_m": 9.0,
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [{
            "floor_number": 0, "floor_use": "residential",
            "rooms": [{"room_type": "living", "count": 1}],
        }],
        "budget_min_lakhs": 15, "budget_max_lakhs": 25,
    }
    status, body = handle_brief_capture(json.dumps(payload))
    assert status == 200
    assert "risk_level" in body
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert body["proceed_with_warnings"] is True
    # Deprecated alias still present
    assert "ready_for_downstream" in body
    print(f"PASS API response has risk_level={body['risk_level']} + "
          f"proceed_with_warnings")


def test_api_response_includes_envelope_and_counts():
    """API response has envelope + guidance counts."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0, "plot_facing": "N",
        "city": "chennai", "road_width_m": 9.0,
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [{
            "floor_number": 0, "floor_use": "residential",
            "rooms": [{"room_type": "living", "count": 1}],
        }],
        "budget_min_lakhs": 15, "budget_max_lakhs": 25,
    }
    status, body = handle_brief_capture(json.dumps(payload))
    summary = body["brief_summary"]
    # Envelope fields
    assert "gross_envelope_sqm" in summary
    assert "net_usable_sqm" in summary
    assert summary["net_usable_sqm"] < summary["gross_envelope_sqm"]
    # Circulation factor
    assert "circulation_factor_applied" in summary
    assert summary["circulation_factor_applied"] in (1.30, 1.35, 1.40)
    # Counts by severity (top-level)
    assert "guidance_counts_by_severity" in body
    counts = body["guidance_counts_by_severity"]
    assert set(counts.keys()) == {"strong_concern", "concern", "info"}
    print(f"PASS API response has envelope + circulation + "
          f"severity counts")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9 — Session A Tests: drawback fixes")
    print("=" * 70)
    print()
    print("--- Drawback #8 — risk_level ---")
    test_risk_level_low_when_no_concerns()
    test_risk_level_high_on_setback_violation()
    test_proceed_with_warnings_always_true()
    test_ready_for_downstream_backwards_compat_alias()
    print()
    print("--- Drawback #3 — envelope transparency ---")
    test_gross_envelope_computed_correctly()
    test_net_usable_is_85pct_of_gross()
    test_explain_shows_gross_and_net_envelope()
    print()
    print("--- Drawback #5 — size-aware circulation ---")
    test_circulation_factor_reflected_in_output()
    test_circulation_factor_appears_in_assumptions()
    print()
    print("--- Drawback #9 — top-3 cumulative summary ---")
    test_top_3_summary_line_shows_cumulative_counts()
    test_risk_level_banner_in_top_3_section()
    print()
    print("--- Drawback #2 — budget range framing ---")
    test_budget_section_leads_with_range()
    test_budget_section_lists_exclusions()
    print()
    print("--- Drawback #6 — vastu cultural label ---")
    test_vastu_section_labelled_cultural()
    print()
    print("--- Drawback #4 — parking layout-dependent wording ---")
    test_parking_messages_acknowledge_layout_dependency()
    test_parking_critical_message_mentions_component_4()
    print()
    print("--- API layer ---")
    test_api_response_includes_risk_level()
    test_api_response_includes_envelope_and_counts()
    print()
    print("=" * 70)
    print("ALL V0.9 SESSION A TESTS PASSED")
    print("=" * 70)
