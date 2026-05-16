"""
v0.9.2 patch tests — drawback fixes from third post-v0.9.1 review.

Covers 6 of 16 drawbacks shipped + 3 partials:
  #1 partial — overshoot stat ("85%+ projects overshoot 15-30%")
  #3        — risk labels with plain-language tails
  #4        — BIGGEST ISSUE elevation
  #6        — next-step CTA (Component 2)
  #7 partial — parking msg extended (turning radius / columns / gates)
  #8 partial — net usable poor-layout warning
  #13       — scope caveat (does NOT replace layout/structural drawings)
  #15       — powered-by surface (Component 7 engineering model)
  #16       — WHAT SHOULD YOU DO NOW? section + action_steps API field
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
# Drawback #3 — risk labels with plain-language tails
# ─────────────────────────────────────────────────────────────────────────

def test_explain_risk_label_has_plain_language_tail():
    """LOW/MEDIUM/HIGH labels include parenthetical context."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    # LOW
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "LOW (minor issues" in text
    # HIGH (force with bad setback)
    bad = _minimal_input(user_setback_front_m=0.3)
    text = engine.explain(bad, engine.execute(bad))
    assert "HIGH (likely design changes needed" in text
    print("PASS risk labels have plain-language tails (LOW (minor issues...) / HIGH (likely design changes...))")


def test_api_risk_label_with_context_field():
    """API exposes risk_label_with_context as a separate field."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    assert status == 200
    label = body["risk_label_with_context"]
    assert "LOW" in label
    assert "(" in label and ")" in label  # has parenthetical
    # Bare risk_level still present (back-compat)
    assert body["risk_level"] == "LOW"
    print(f"PASS API risk_label_with_context: {label!r}")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #4 — BIGGEST ISSUE elevation
# ─────────────────────────────────────────────────────────────────────────

def test_explain_shows_biggest_issue_for_high_risk():
    """HIGH risk explain output has 'BIGGEST ISSUE:' line above 'Why:'."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    bad = _minimal_input(user_setback_front_m=0.3)
    text = engine.explain(bad, engine.execute(bad))
    assert "BIGGEST ISSUE" in text
    # Must come before the "Why:" list
    biggest_pos = text.find("BIGGEST ISSUE")
    why_pos = text.find("Why:")
    assert biggest_pos < why_pos
    print("PASS HIGH risk shows BIGGEST ISSUE elevation above Why:")


def test_explain_no_biggest_issue_for_low_risk():
    """LOW risk doesn't surface BIGGEST ISSUE (would be misleading)."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "BIGGEST ISSUE" not in text
    print("PASS LOW risk does NOT show BIGGEST ISSUE elevation")


def test_api_biggest_issue_field():
    """API biggest_issue: string for MEDIUM/HIGH, None for LOW."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    # LOW
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    assert body["biggest_issue"] is None
    # HIGH
    status, body = handle_brief_capture(json.dumps(_api_payload(
        user_setback_front_m=0.3,
    )))
    assert body["biggest_issue"] is not None
    assert isinstance(body["biggest_issue"], str)
    assert body["biggest_issue"].startswith("Critical:")
    print("PASS API biggest_issue: None for LOW, populated for HIGH")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #6 — next-step CTA
# ─────────────────────────────────────────────────────────────────────────

def test_explain_shows_next_step_cta():
    """explain() includes 'Next: Component 2 (Feasibility)' line."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "Component 2" in text
    assert "Feasibility" in text
    assert "actually possible" in text
    print("PASS explain() shows 'Next: Component 2 (Feasibility)' CTA")


def test_api_roadmap_position_includes_next_step_cta():
    """API roadmap_position now includes next_step_cta."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    cta = body["roadmap_position"]["next_step_cta"]
    assert "Component 2" in cta
    assert "Feasibility" in cta
    print(f"PASS API roadmap_position.next_step_cta populated")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #13 — scope caveat (does NOT replace)
# ─────────────────────────────────────────────────────────────────────────

def test_explain_includes_scope_caveat():
    """explain() banner has 'does NOT replace architect-led' line."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    # The exact phrasing
    assert "NOT replace" in text
    assert "architect-led layout" in text
    assert "structural engineering" in text
    assert "municipal plan approval" in text
    print("PASS explain() shows scope caveat (does NOT replace...)")


def test_api_scope_caveat_field():
    """API top-level scope_caveat field present."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    caveat = body["scope_caveat"]
    assert "NOT replace" in caveat
    assert "architect" in caveat
    print(f"PASS API scope_caveat field populated")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #15 — powered-by surface
# ─────────────────────────────────────────────────────────────────────────

def test_explain_includes_powered_by():
    """explain() banner names Component 7 + IS codes."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "Component 7" in text
    assert "engineering model" in text
    # IS code refs (any of)
    assert "IS 456" in text or "IS 875" in text or "IS 1893" in text
    print("PASS explain() surfaces 'powered by Component 7' with IS codes")


def test_api_powered_by_field():
    """API top-level powered_by dict present."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    pb = body["powered_by"]
    assert "structural_cost_engine" in pb
    assert "Component 7" in pb["structural_cost_engine"]
    assert "city_rates_source" in pb
    print(f"PASS API powered_by populated")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #16 — WHAT SHOULD YOU DO NOW? + action_steps
# ─────────────────────────────────────────────────────────────────────────

def test_compute_action_steps_low():
    """LOW risk → 3 actions, all positive next-step framed."""
    from buildemup.components.c01.soft_guide_engine import compute_action_steps
    actions = compute_action_steps([], "LOW")
    assert len(actions) == 3
    # First action is "proceed to Component 2"
    assert "Component 2" in actions[0]
    # Mentions contingency
    assert any("contingency" in a or "overshoot" in a for a in actions)
    # Mentions architect
    assert any("architect" in a for a in actions)
    print(f"PASS LOW risk → {len(actions)} action steps")


def test_compute_action_steps_high_with_compliance_issue():
    """HIGH risk with setback violation → 'fix compliance' is action 1."""
    from buildemup.components.c01.soft_guide_engine import compute_action_steps
    from buildemup.domain.brief import GuidanceMessage, GuidanceSeverity
    msgs = [
        GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text="Front setback 0.3m below DCR minimum 1.5m.",
            context="setback_violation_front",
            action_verb="Reduce",
        ),
    ]
    actions = compute_action_steps(msgs, "HIGH")
    # First action must be "fix compliance"
    assert actions[0].lower().startswith("fix compliance")
    # Must mention re-running
    assert any("re-run" in a.lower() for a in actions)
    # Must mention architect sanity check
    assert any("architect" in a.lower() for a in actions)
    print(f"PASS HIGH+compliance → {len(actions)} actions, "
          f"#1 = fix compliance")


def test_explain_what_should_you_do_now_section():
    """explain() includes 'WHAT SHOULD YOU DO NOW?' section header."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "WHAT SHOULD YOU DO NOW?" in text
    # Numbered list (at least "  1.")
    assert "  1." in text
    print("PASS explain() shows WHAT SHOULD YOU DO NOW? section")


def test_api_action_steps_field():
    """API top-level action_steps list, length 3-5."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    actions = body["action_steps"]
    assert isinstance(actions, list)
    assert 3 <= len(actions) <= 5
    # All strings
    assert all(isinstance(a, str) for a in actions)
    print(f"PASS API action_steps: {len(actions)} items")


def test_explain_and_api_action_steps_match():
    """Same actions in explain() and API — single source of truth."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    from buildemup.api.brief_endpoint import handle_brief_capture
    engine = BriefCaptureEngine()
    inp = _minimal_input()
    text = engine.explain(inp, engine.execute(inp))
    status, body = handle_brief_capture(json.dumps(_api_payload()))
    api_actions = body["action_steps"]
    # Each API action should appear (substring) in the rendered text
    for action in api_actions:
        # Check first 40 chars (enough to disambiguate, avoids width-wrap issues)
        snippet = action[:40]
        assert snippet in text, f"API action not in explain: {snippet!r}"
    print(f"PASS explain() and API action_steps are consistent "
          f"({len(api_actions)} actions)")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #1 partial — overshoot stat in BUDGET section
# ─────────────────────────────────────────────────────────────────────────

def test_explain_budget_section_has_overshoot_stat():
    """BUDGET section ends with industry-overshoot warning."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "85%" in text   # industry stat
    assert "15-30%" in text  # overshoot range
    assert "contingency" in text  # actionable advice
    print("PASS BUDGET section has 85%+/15-30% overshoot warning")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #7 partial — parking caveat extended
# ─────────────────────────────────────────────────────────────────────────

def test_parking_message_warns_about_turning_radius_and_columns():
    """Both critical and marginal parking msgs say what is NOT validated."""
    from buildemup.components.c01.parking_feasibility import (
        check_parking_feasibility,
    )
    msgs = check_parking_feasibility(
        plot_width_m=5.0, plot_depth_m=12.0,
        has_stilt_parking=True,
        side_left_setback_m=1.0, side_right_setback_m=1.0,
    )
    assert len(msgs) == 1
    assert "NOT validate" in msgs[0].text
    assert "turning radius" in msgs[0].text
    assert "column placement" in msgs[0].text
    assert "gate alignment" in msgs[0].text
    print("PASS parking msg lists what is NOT validated "
          "(turning/columns/gates)")


# ─────────────────────────────────────────────────────────────────────────
# Drawback #8 partial — net usable poor-layout warning
# ─────────────────────────────────────────────────────────────────────────

def test_explain_net_usable_warns_about_poor_layouts():
    """Net usable section warns about layouts dropping below 80%."""
    from buildemup.components.c01_brief_capture import BriefCaptureEngine
    engine = BriefCaptureEngine()
    text = engine.explain(_minimal_input(), engine.execute(_minimal_input()))
    assert "below 80%" in text or "below 80 %" in text
    assert "Poor layout" in text or "poor layout" in text
    assert "corridors" in text
    print("PASS net usable section warns about poor layouts dropping <80%")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.9.2 — Patch Tests (post-v0.9.1 review)")
    print("=" * 70)
    print()
    print("--- Drawback #3: plain-language risk tails ---")
    test_explain_risk_label_has_plain_language_tail()
    test_api_risk_label_with_context_field()
    print()
    print("--- Drawback #4: BIGGEST ISSUE elevation ---")
    test_explain_shows_biggest_issue_for_high_risk()
    test_explain_no_biggest_issue_for_low_risk()
    test_api_biggest_issue_field()
    print()
    print("--- Drawback #6: next-step CTA ---")
    test_explain_shows_next_step_cta()
    test_api_roadmap_position_includes_next_step_cta()
    print()
    print("--- Drawback #13: scope caveat ---")
    test_explain_includes_scope_caveat()
    test_api_scope_caveat_field()
    print()
    print("--- Drawback #15: powered-by surface ---")
    test_explain_includes_powered_by()
    test_api_powered_by_field()
    print()
    print("--- Drawback #16: WHAT SHOULD YOU DO NOW? + action_steps ---")
    test_compute_action_steps_low()
    test_compute_action_steps_high_with_compliance_issue()
    test_explain_what_should_you_do_now_section()
    test_api_action_steps_field()
    test_explain_and_api_action_steps_match()
    print()
    print("--- Drawback #1 partial: overshoot stat ---")
    test_explain_budget_section_has_overshoot_stat()
    print()
    print("--- Drawback #7 partial: parking turning radius caveat ---")
    test_parking_message_warns_about_turning_radius_and_columns()
    print()
    print("--- Drawback #8 partial: net usable poor-layout warning ---")
    test_explain_net_usable_warns_about_poor_layouts()
    print()
    print("=" * 70)
    print("ALL V0.9.2 PATCH TESTS PASSED")
    print("=" * 70)
