"""
S54-006 — regression test for budget-generous suppression.

When C1's "your budget is generous for this design" INFO message fires
alongside C2's envelope-insufficient HARD_FAIL, the two messages
contradict each other. The fix: in /api/brief/capture, when C2 reports
envelope_sufficiency HARD_FAIL, replace the misleading budget-generous
line in combined_rendered_explain with an honest "evaluation pending"
message.
"""
from __future__ import annotations

import json
from buildemup.api.brief_endpoint import handle_brief_capture


def _impossible_brief(budget_min: int = 50, budget_max: int = 60) -> bytes:
    """Build a deliberately infeasible brief (20x30 ft, many rooms)."""
    payload = {
        "plot_width_m": 6.096,   # 20 ft
        "plot_depth_m": 9.144,   # 30 ft
        "plot_facing": "N",
        "city": "chennai",
        "road_width_m": 9.144,
        "plot_type": "detached",
        "user_setback_front_m": 1.5,
        "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5,
        "user_setback_side_right_m": 1.5,
        "floors": [
            {
                "floor_number": 0,
                "floor_use": "residential",
                "rooms": [
                    {"room_type": "living", "count": 1},
                    {"room_type": "kitchen", "count": 1},
                    {"room_type": "bedroom_master", "count": 2},
                    {"room_type": "bedroom_regular", "count": 2},
                    {"room_type": "bathroom_attached", "count": 2},
                    {"room_type": "bathroom_common", "count": 1},
                    {"room_type": "pooja", "count": 1},
                ],
            },
        ],
        "budget_min_lakhs": budget_min,
        "budget_max_lakhs": budget_max,
        "vastu_preference": "off",
    }
    return json.dumps(payload).encode("utf-8")


def _feasible_brief(budget_min: int = 50, budget_max: int = 60) -> bytes:
    """A roomy feasible brief — generous budget should remain visible."""
    payload = {
        "plot_width_m": 12.192,  # 40 ft
        "plot_depth_m": 15.24,   # 50 ft
        "plot_facing": "N",
        "city": "chennai",
        "road_width_m": 9.144,
        "plot_type": "detached",
        "user_setback_front_m": 1.5,
        "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5,
        "user_setback_side_right_m": 1.5,
        "floors": [
            {
                "floor_number": 0,
                "floor_use": "residential",
                "rooms": [
                    {"room_type": "living", "count": 1},
                    {"room_type": "kitchen", "count": 1},
                    {"room_type": "bedroom_master", "count": 1},
                ],
            },
        ],
        "budget_min_lakhs": budget_min,
        "budget_max_lakhs": budget_max,
        "vastu_preference": "off",
    }
    return json.dumps(payload).encode("utf-8")


# ─── Infeasible brief: budget message should be SUPPRESSED ─────────────

def test_infeasible_brief_suppresses_budget_generous_in_combined():
    """When envelope is insufficient, combined_rendered_explain must NOT
    contain the misleading 'is generous for this design' phrase.
    """
    body = _impossible_brief(budget_min=50, budget_max=60)
    status, response = handle_brief_capture(body)

    assert status == 200
    assert response["chain_status"]["c2"] == "ok"
    assert response["chain_status"]["budget_generous_suppressed"] is True, (
        f"Expected envelope-insufficient detection. chain_status: "
        f"{response['chain_status']}"
    )

    combined = response["combined_rendered_explain"]
    assert "is generous for this design" not in combined, (
        "S54-006 violation: 'generous for this design' still appears in "
        "combined_rendered_explain despite envelope being insufficient"
    )
    # The honest replacement should be there instead
    assert "Budget vs cost cannot be evaluated" in combined, (
        "Replacement message missing from combined_rendered_explain"
    )


def test_infeasible_brief_preserves_rendered_explain_for_backcompat():
    """The original rendered_explain field stays unchanged (C1-only,
    no awareness of C2 feasibility). Only combined_rendered_explain is
    rewritten. Backwards-compat for clients that read only rendered_explain.
    """
    body = _impossible_brief()
    _, response = handle_brief_capture(body)

    rendered = response["rendered_explain"]
    # rendered_explain still contains the original C1 budget-generous text
    # (unchanged for backcompat). This is intentional — only the new
    # combined view honors the no-silent-override principle.
    assert "is generous for this design" in rendered, (
        "rendered_explain (backwards-compat field) should NOT be modified — "
        "only combined_rendered_explain is rewritten"
    )


# ─── Feasible brief: budget message stays VISIBLE ─────────────────────

def test_feasible_brief_does_NOT_suppress_budget_message():
    """When the brief IS feasible, the budget-generous message is honest
    and should NOT be suppressed.
    """
    body = _feasible_brief(budget_min=50, budget_max=60)
    _, response = handle_brief_capture(body)

    assert response["chain_status"]["budget_generous_suppressed"] is False, (
        "False positive: budget_generous wrongly suppressed on a feasible "
        "brief"
    )

    # Either the brief is generous-enough to fire the original message,
    # or it's aligned/under-budget. Either way the rewrite shouldn't fire.
    combined = response["combined_rendered_explain"]
    assert "Budget vs cost cannot be evaluated" not in combined, (
        "Suppression replacement leaked into a feasible-brief response"
    )


# ─── chain_status records the suppression decision ────────────────────

def test_chain_status_records_budget_suppression_decision():
    """chain_status should always include budget_generous_suppressed (bool),
    so downstream consumers know whether the rewrite happened.
    """
    body = _feasible_brief()
    _, response = handle_brief_capture(body)
    assert "budget_generous_suppressed" in response["chain_status"]
    assert isinstance(response["chain_status"]["budget_generous_suppressed"], bool)
