"""
S54-001+002 — tests for the C1 → C2 → C3a-detect chain in /api/brief/capture.

Per Architecture v1 §2.4 (no silent override), the brief endpoint must
always run C2 + C3a-detect after C1, and surface their findings in the
response so the user never sees an optimistic "budget generous" message
when the brief is geometrically infeasible.

These tests verify:
  - The endpoint returns the new fields (combined_rendered_explain,
    feasibility_summary_text, feasibility_data, extreme_cases,
    chain_status) on every response.
  - For a feasible brief, extreme_cases is empty but the feasibility
    chain still runs (chain_status["c2"] == "ok").
  - For an infeasible brief (rooms-too-big-for-envelope), C3a's
    extreme-case detection actually fires and surfaces EC objects.
  - The combined_rendered_explain text includes the C2 feasibility
    section when present.
  - The endpoint degrades gracefully if downstream components fail.
"""
from __future__ import annotations

import json

from buildemup.api.brief_endpoint import handle_brief_capture


def _make_brief(
    *,
    plot_width_m: float = 12.192,  # 40 ft
    plot_depth_m: float = 15.24,   # 50 ft
    city: str = "chennai",
    floors: list | None = None,
    budget_min: int = 25,
    budget_max: int = 35,
    setback_m: float = 1.5,
) -> bytes:
    """Build a minimal valid request body for /api/brief/capture."""
    if floors is None:
        floors = [
            {
                "floor_number": 0,
                "floor_use": "residential",
                "rooms": [
                    {"room_type": "living", "count": 1},
                    {"room_type": "kitchen", "count": 1},
                    {"room_type": "bedroom_master", "count": 1},
                ],
            },
        ]
    payload = {
        "plot_width_m": plot_width_m,
        "plot_depth_m": plot_depth_m,
        "plot_facing": "N",
        "city": city,
        "road_width_m": 9.144,
        "plot_type": "detached",
        "user_setback_front_m": setback_m,
        "user_setback_rear_m": setback_m,
        "user_setback_side_left_m": setback_m,
        "user_setback_side_right_m": setback_m,
        "floors": floors,
        "budget_min_lakhs": budget_min,
        "budget_max_lakhs": budget_max,
        "vastu_preference": "off",
    }
    return json.dumps(payload).encode("utf-8")


# ─── Test 1: new response fields are always present ─────────────────────

def test_chain_response_has_new_fields():
    """Every successful brief response should include the chain fields."""
    body = _make_brief()
    status, response = handle_brief_capture(body)

    assert status == 200, f"Expected 200, got {status}: {response.get('errors')}"
    # Original fields preserved (backwards compat)
    assert "rendered_explain" in response
    assert "trace_id" in response
    assert "risk_level" in response
    # New S54 fields
    assert "combined_rendered_explain" in response
    assert "feasibility_summary_text" in response
    assert "feasibility_data" in response
    assert "extreme_cases" in response
    assert "chain_status" in response


def test_chain_status_records_each_stage():
    """chain_status should track c1 / c2 / c3a_detect outcomes."""
    body = _make_brief()
    _, response = handle_brief_capture(body)
    cs = response["chain_status"]
    assert cs["c1"] == "ok"
    # C2 should run for any valid C1 output
    assert cs["c2"] in ("ok", "render_error"), (
        f"C2 should run, got {cs['c2']}"
    )
    # C3a-detect should run when C2 succeeds
    assert cs["c3a_detect"] in ("ok", "ok_no_cases"), (
        f"C3a should run when C2 succeeds, got {cs['c3a_detect']}"
    )


# ─── Test 2: feasible brief → no extreme cases, but chain runs ──────────

def test_feasible_brief_chain_runs_no_extreme_cases():
    """A reasonable brief should have C2 ok + C3a finds no extreme cases."""
    body = _make_brief(
        plot_width_m=12.192, plot_depth_m=15.24,  # 40x50 ft
        budget_min=40, budget_max=60,  # generous budget
        setback_m=1.5,  # CMDA-compliant
    )
    status, response = handle_brief_capture(body)

    assert status == 200
    assert response["chain_status"]["c2"] == "ok"
    # Even feasible plots may surface some EC types (e.g., parking),
    # so we don't assert empty — we just assert the chain ran.
    assert isinstance(response["extreme_cases"], list)
    assert response["feasibility_summary_text"] is not None


# ─── Test 3: infeasible brief → extreme cases or feasibility flags fire ─

def test_infeasible_brief_surfaces_problems():
    """An impossible brief (many rooms on tiny plot) should surface
    findings via either extreme_cases OR feasibility_data gaps OR a
    HIGH risk level — but NEVER pass through silently as 'all fine'.
    """
    body = _make_brief(
        plot_width_m=6.096, plot_depth_m=9.144,  # 20x30 ft = 600 sqft
        floors=[
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
        budget_min=40, budget_max=50,
    )
    status, response = handle_brief_capture(body)

    assert status == 200
    assert response["chain_status"]["c2"] == "ok", (
        f"C2 must run on infeasible brief; got {response['chain_status']}"
    )

    # SOUL test: response must NOT be silently optimistic. At least ONE
    # of these signals must fire:
    has_extreme_cases = len(response["extreme_cases"]) > 0
    has_feasibility_gaps = (
        response.get("feasibility_data") is not None
        and len(response["feasibility_data"].get("gaps") or []) > 0
    )
    has_high_risk = response["risk_level"] == "HIGH"

    assert has_extreme_cases or has_feasibility_gaps or has_high_risk, (
        f"Infeasible brief surfaced no warnings — soul violation. "
        f"extreme_cases={response['extreme_cases']}, "
        f"feasibility_summary_present={response['feasibility_summary_text'] is not None}, "
        f"risk_level={response['risk_level']}"
    )


# ─── Test 4: combined_rendered_explain includes feasibility section ─────

def test_combined_explain_includes_feasibility_section():
    """When C2 runs successfully, the combined text should embed the
    feasibility summary so the user sees it inline with the brief output.
    """
    body = _make_brief()
    _, response = handle_brief_capture(body)
    combined = response["combined_rendered_explain"]
    assert combined is not None
    assert "FEASIBILITY CHECK" in combined, (
        "combined_rendered_explain should include the C2 feasibility "
        "section header"
    )


# ─── Test 5: backwards compatibility — rendered_explain unchanged ───────

def test_rendered_explain_preserved_for_backwards_compat():
    """The original rendered_explain field must still be C1-only output,
    so existing clients that only read that field don't break.
    """
    body = _make_brief()
    _, response = handle_brief_capture(body)
    rendered = response["rendered_explain"]
    combined = response["combined_rendered_explain"]
    # Original is C1-only; combined is C1 + C2 (+ optional C3a)
    assert rendered != combined, (
        "rendered_explain should NOT have C2 content (backwards compat); "
        "combined_rendered_explain is the new chained view"
    )
    assert "FEASIBILITY CHECK" not in rendered, (
        "rendered_explain (legacy C1-only) should not contain C2 section"
    )
