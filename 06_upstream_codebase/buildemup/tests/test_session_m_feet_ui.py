"""
v0.10.1 Session M tests — Feet/metres dual-unit UI.

Tests three layers:
  1. The new /api/setback/preview endpoint (returns NBC setback in both units)
  2. The brief_form.html surface (feet field names, NBC hint placeholder)
  3. The brief_form.js surface (unit conversion helpers, refreshNbcSetbackHint)
  4. The C2 renderer (dual-unit display in plot section)

The engine itself is untouched — still computes in metres internally.
This is purely a presentation/UX layer change.
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─── /api/setback/preview endpoint ───────────────────────────────────

def test_setback_preview_chennai_30x40():
    """Chennai 30x40 ft (~9.14 × 12.19 m) detached should return TNCDBR setbacks."""
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    payload = {
        "city": "chennai",
        "plot_width_m": 9.14, "plot_depth_m": 12.19,
        "plot_facing": "N",
        "plot_type": "detached",
        "road_width_m": 9.14,
        "corner_plot": False,
    }
    status, resp = handle_setback_preview(json.dumps(payload).encode())
    assert status == 200
    assert resp["ok"] is True
    # Should have all 4 sides in both units
    for side in ["front", "rear", "side_left", "side_right"]:
        assert f"{side}_m" in resp
        assert f"{side}_ft" in resp
    # TNCDBR small-plot tier: front=0.9m, rear=0.7m, side_left=0.7m, side_right=0
    assert resp["front_m"] == 0.9
    assert "TNCDBR" in resp["source_authority"]
    print(f"PASS Chennai 30x40 returns TNCDBR setbacks "
          f"(front {resp['front_ft']}ft / {resp['front_m']}m)")


def test_setback_preview_returns_metres_AND_feet():
    """Both unit systems are present in the response."""
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    payload = {
        "city": "bangalore", "plot_width_m": 12.0, "plot_depth_m": 15.0,
        "plot_facing": "S", "plot_type": "detached", "road_width_m": 9.0,
    }
    status, resp = handle_setback_preview(json.dumps(payload).encode())
    assert status == 200
    # Feet values should equal metre values × 3.28084 (rounded to 2 places)
    for side in ["front", "rear", "side_left", "side_right"]:
        m_val = resp[f"{side}_m"]
        ft_val = resp[f"{side}_ft"]
        expected_ft = round(m_val * 3.28084, 2)
        assert abs(ft_val - expected_ft) < 0.01, (
            f"{side}: {ft_val} ft != {expected_ft} ft (from {m_val} m)"
        )
    print("PASS endpoint returns mathematically consistent metres + feet")


def test_setback_preview_handles_corner_plot():
    """Corner plot uses wider road for front setback."""
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    payload = {
        "city": "chennai", "plot_width_m": 12.0, "plot_depth_m": 15.0,
        "plot_facing": "N", "plot_type": "detached", "road_width_m": 6.0,
        "corner_plot": True, "second_road_width_m": 12.0,
    }
    status, resp = handle_setback_preview(json.dumps(payload).encode())
    assert status == 200
    assert "front_m" in resp
    print("PASS endpoint handles corner_plot input")


def test_setback_preview_all_6_cities():
    """All 6 launch cities work through the endpoint."""
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    cities = ["chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi"]
    for city in cities:
        payload = {
            "city": city, "plot_width_m": 12.0, "plot_depth_m": 15.0,
            "plot_facing": "N", "plot_type": "detached", "road_width_m": 9.0,
        }
        status, resp = handle_setback_preview(json.dumps(payload).encode())
        assert status == 200, f"Failed for {city}: {resp.get('errors')}"
        assert resp["source_authority"], f"{city} missing source_authority"
    print(f"PASS endpoint works for all {len(cities)} cities")


def test_setback_preview_unsupported_city_returns_400():
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    payload = {
        "city": "kolkata", "plot_width_m": 12.0, "plot_depth_m": 15.0,
        "plot_facing": "N", "plot_type": "detached", "road_width_m": 9.0,
    }
    status, resp = handle_setback_preview(json.dumps(payload).encode())
    assert status == 400
    assert "kolkata" in str(resp["errors"]).lower() or "supported" in str(resp["errors"]).lower()
    print("PASS unsupported city returns 400 (not 500)")


def test_setback_preview_bad_json_returns_400():
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    status, resp = handle_setback_preview(b"not json")
    assert status == 400
    print("PASS bad JSON returns 400")


def test_setback_preview_missing_field_returns_400():
    from buildemup.api.setback_preview_endpoint import handle_setback_preview
    # Missing plot_width_m
    payload = {"city": "chennai", "plot_depth_m": 15.0,
               "plot_facing": "N", "plot_type": "detached", "road_width_m": 9.0}
    status, resp = handle_setback_preview(json.dumps(payload).encode())
    assert status == 400
    print("PASS missing required field returns 400")


def test_setback_preview_route_registered():
    """Verify the new route is wired into the server."""
    import inspect
    from buildemup.api import server
    source = inspect.getsource(server.BriefCaptureHandler.do_POST)
    assert "/api/setback/preview" in source
    print("PASS /api/setback/preview route is registered")


# ─── HTML form surface (feet field names) ────────────────────────────

def test_form_html_uses_feet_field_names():
    """The form should declare feet inputs, not metre inputs."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    # Read with explicit utf-8 to handle Windows cp1252 default
    html = html_path.read_text(encoding="utf-8")
    feet_fields = [
        "plot_width_ft", "plot_depth_ft", "road_width_ft",
        "user_setback_front_ft", "user_setback_rear_ft",
        "user_setback_side_left_ft", "user_setback_side_right_ft",
    ]
    for f in feet_fields:
        assert f'name="{f}"' in html, f"Missing feet field: {f}"
    print(f"PASS form HTML declares all {len(feet_fields)} feet fields")


def test_form_html_does_not_use_old_metre_field_names():
    """Old metre field names should be gone from the form."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    html = html_path.read_text(encoding="utf-8")
    old_metre_fields = [
        "plot_width_m", "plot_depth_m", "road_width_m",
        "user_setback_front_m", "user_setback_rear_m",
        "user_setback_side_left_m", "user_setback_side_right_m",
    ]
    for f in old_metre_fields:
        assert f'name="{f}"' not in html, (
            f"Old metre field still present: {f}"
        )
    print("PASS old metre field names removed from HTML")


def test_form_html_has_nbc_hint_placeholder():
    """The NBC setback hint container should be present."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    html = html_path.read_text(encoding="utf-8")
    assert 'id="nbc-setback-hint"' in html
    assert 'id="nbc-setback-hint-text"' in html
    print("PASS HTML has nbc-setback-hint placeholder")


def test_form_html_setback_step_labels_say_feet():
    """The setbacks section should mention feet."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    html = html_path.read_text(encoding="utf-8")
    assert "in feet" in html.lower() or "(ft)" in html
    print("PASS setback section labels mention feet")


# ─── JS surface (unit conversion + helpers) ──────────────────────────

def test_form_js_has_conversion_constants():
    """The JS file should have the conversion constants we expect."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    js = js_path.read_text(encoding="utf-8")
    assert "FT_PER_M" in js
    assert "M_PER_FT" in js
    assert "SQFT_PER_SQM" in js
    print("PASS JS has FT_PER_M, M_PER_FT, SQFT_PER_SQM constants")


def test_form_js_has_unit_helpers():
    """JS should expose feet↔metre helpers."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    js = js_path.read_text(encoding="utf-8")
    for fn in ["feetToMetres", "metresToFeet", "sqmToSqft", "fmtFeet", "fmtArea"]:
        assert f"function {fn}" in js, f"Missing JS helper: {fn}()"
    print("PASS JS has all 5 unit-conversion helpers")


def test_form_js_collects_feet_fields_and_sends_metres():
    """collectFormData should call feetToMetres on plot dimensions."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    js = js_path.read_text(encoding="utf-8")
    # Look for feetToMetres being applied to plot_width_ft etc
    assert "feetToMetres(Number(form.plot_width_ft.value))" in js
    assert "feetToMetres(Number(form.plot_depth_ft.value))" in js
    assert "feetToMetres(Number(form.road_width_ft.value))" in js
    assert "feetToMetres(Number(form.user_setback_front_ft.value))" in js
    print("PASS collectFormData converts feet→metres before sending to API")


def test_form_js_has_nbc_hint_function():
    """JS should have refreshNbcSetbackHint function."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    js = js_path.read_text(encoding="utf-8")
    assert "refreshNbcSetbackHint" in js
    assert "/api/setback/preview" in js
    print("PASS JS has refreshNbcSetbackHint() and calls /api/setback/preview")


# ─── C2 renderer dual-unit display ───────────────────────────────────

def _build_analysis_for_renderer():
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.orchestrator import run_feasibility
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),
             RoomRequirement(RoomType.KITCHEN, 1))),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    out = BriefCaptureEngine().execute(inp)
    analysis = run_feasibility(out.brief, c7_cost_estimate=out.c7_preview_cost)
    return analysis, out.brief


def test_renderer_summary_shows_feet_and_metres():
    """Summary should show plot dimensions in 'X.X ft (Y.YY m)' format."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_analysis_for_renderer()
    summary = render_text_summary(analysis, brief)
    # 12 m → 39.4 ft, 15 m → 49.2 ft
    assert "ft" in summary, "Summary should mention feet"
    assert "m" in summary, "Summary should mention metres"
    # Specifically expect "39.4 ft" and "(12.00 m)" pattern
    assert "39.4 ft" in summary, f"Expected '39.4 ft' in summary, got: {summary[:200]}"
    assert "(12.00 m)" in summary
    print("PASS summary plot line shows 'X.X ft (Y.YY m)'")


def test_renderer_summary_shows_sqft_and_sqm():
    """Summary should show area in 'X sqft (Y sqm)' format."""
    from buildemup.components.c02.renderer import render_text_summary
    analysis, brief = _build_analysis_for_renderer()
    summary = render_text_summary(analysis, brief)
    # 180 sqm → 1937 sqft
    assert "sqft" in summary
    assert "sqm" in summary
    assert "1937 sqft" in summary or "1938 sqft" in summary  # rounding tolerance
    print("PASS summary shows area as 'X sqft (Y sqm)'")


def test_renderer_full_dimensions_show_both_units():
    """Full report PLOT section should show dimensions in both units."""
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis_for_renderer()
    full = render_text_full(analysis, brief, include_doubts=False)
    # Look for the PLOT section
    plot_section = full.split("PLOT")[1].split("BUILD")[0]
    assert "ft" in plot_section
    assert "m)" in plot_section  # closing paren of "(X.XX m)" pattern
    assert "sqft" in plot_section
    assert "sqm)" in plot_section
    print("PASS full report PLOT section shows dimensions + area in both units")


def test_renderer_full_road_width_shows_both_units():
    from buildemup.components.c02.renderer import render_text_full
    analysis, brief = _build_analysis_for_renderer()
    full = render_text_full(analysis, brief, include_doubts=False)
    plot_section = full.split("PLOT")[1].split("BUILD")[0]
    # Find "Road width:" line
    assert "Road width:" in plot_section
    # Should have something like "29.5 ft (9.00 m)"
    road_lines = [l for l in plot_section.split("\n") if "Road width" in l]
    assert any("ft" in l and "m" in l for l in road_lines), (
        f"Road width line should show both units: {road_lines}"
    )
    print("PASS road width shows both ft + m in full report")


def test_renderer_unit_helpers_math_correct():
    """Direct test of the renderer's _fmt_ft and _fmt_area functions."""
    from buildemup.components.c02.renderer import _fmt_ft, _fmt_area
    # 1.5 m → 4.92 ft (rounded to 4.9 in display)
    out = _fmt_ft(1.5)
    assert "4.9 ft" in out
    assert "1.50 m" in out
    # 180 sqm × 10.7639 = 1937.5 sqft → rounds to 1938
    out = _fmt_area(180.0)
    assert "1938 sqft" in out
    assert "180 sqm" in out
    print("PASS renderer's _fmt_ft + _fmt_area do correct math")


# ─── Integration: form-to-API roundtrip with feet inputs ─────────────

def test_full_pipeline_accepts_metres_from_feet_conversion():
    """When the front-end converts 30 ft → 9.144 m and POSTs, the
    feasibility endpoint should still produce sensible output."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    # Simulate JS doing feetToMetres(40) = 12.192 etc.
    payload = {
        "plot_width_m": 12.192,  # was 40 ft
        "plot_depth_m": 15.24,   # was 50 ft
        "plot_facing": "N",
        "city": "chennai",
        "road_width_m": 9.144,   # was 30 ft
        "user_setback_front_m": 1.524,  # was 5 ft
        "user_setback_rear_m": 1.524,
        "user_setback_side_left_m": 1.524,
        "user_setback_side_right_m": 1.524,
        "floors": [{"floor_number": 0, "floor_use": "residential",
                    "rooms": [{"room_type": "living", "count": 1},
                              {"room_type": "kitchen", "count": 1}]}],
        "budget_min_lakhs": 20, "budget_max_lakhs": 30,
    }
    status, resp = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    assert resp["ok"] is True
    # The response should still have sensible scores
    p_score = resp["feasibility_data"]["practical_report"]["overall_score"]
    assert 0 <= p_score <= 100
    # Summary text should now show feet
    assert "ft" in resp["feasibility_summary_text"]
    print(f"PASS feet→metres-converted payload works end-to-end "
          f"(P-score={p_score})")


# ─── Baseline preserved ──────────────────────────────────────────────

def test_v0_9_3_baseline_unaffected_by_session_m():
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
    print("PASS v0.9.3 baseline unaffected by Session M feet UI changes")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.10.1 Session M — Feet/metres dual-unit UI")
    print("=" * 70)
    print()

    print("--- /api/setback/preview endpoint ---")
    test_setback_preview_chennai_30x40()
    test_setback_preview_returns_metres_AND_feet()
    test_setback_preview_handles_corner_plot()
    test_setback_preview_all_6_cities()
    test_setback_preview_unsupported_city_returns_400()
    test_setback_preview_bad_json_returns_400()
    test_setback_preview_missing_field_returns_400()
    test_setback_preview_route_registered()
    print()

    print("--- HTML form surface ---")
    test_form_html_uses_feet_field_names()
    test_form_html_does_not_use_old_metre_field_names()
    test_form_html_has_nbc_hint_placeholder()
    test_form_html_setback_step_labels_say_feet()
    print()

    print("--- JS surface ---")
    test_form_js_has_conversion_constants()
    test_form_js_has_unit_helpers()
    test_form_js_collects_feet_fields_and_sends_metres()
    test_form_js_has_nbc_hint_function()
    print()

    print("--- C2 renderer dual-unit display ---")
    test_renderer_summary_shows_feet_and_metres()
    test_renderer_summary_shows_sqft_and_sqm()
    test_renderer_full_dimensions_show_both_units()
    test_renderer_full_road_width_shows_both_units()
    test_renderer_unit_helpers_math_correct()
    print()

    print("--- Integration ---")
    test_full_pipeline_accepts_metres_from_feet_conversion()
    print()

    print("--- Baseline ---")
    test_v0_9_3_baseline_unaffected_by_session_m()
    print()

    print("=" * 70)
    print("ALL SESSION M TESTS PASSED")
    print("=" * 70)
