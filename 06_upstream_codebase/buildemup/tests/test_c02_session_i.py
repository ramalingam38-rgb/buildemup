"""
Component 2 Session I tests.

Coverage:
  - handle_feasibility_run: minimal valid request → 200 + correct shape
  - feasibility_input parsing: all 6 fields accept verified/unverified/unknown
  - Legacy kwargs (electric line, water course)
  - Error handling: bad JSON / missing fields / bad enums / invariant violations
  - Server route wiring: /api/feasibility/run is registered
  - Existing C1 endpoint NOT broken by Session I additions
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import json


# Helper: minimal valid payload
def _minimal_valid_payload(**overrides):
    payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0,
        "plot_facing": "N", "city": "chennai", "road_width_m": 9.0,
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [
            {"floor_number": 0, "floor_use": "residential",
             "rooms": [
                 {"room_type": "living", "count": 1},
                 {"room_type": "kitchen", "count": 1},
             ]},
        ],
        "budget_min_lakhs": 20, "budget_max_lakhs": 30,
    }
    payload.update(overrides)
    return payload


# ─── Happy path ───────────────────────────────────────────────────────

def test_happy_path_returns_200():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    assert response["ok"] is True
    print("PASS minimal valid request → HTTP 200")


def test_happy_path_includes_all_top_level_keys():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    expected_keys = {
        "ok", "trace_id", "feasibility_summary_text",
        "feasibility_full_text", "feasibility_data",
        "brief_summary", "errors",
    }
    assert set(response.keys()) == expected_keys
    print(f"PASS response has all {len(expected_keys)} expected top-level keys")


def test_happy_path_text_outputs_are_strings():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert isinstance(response["feasibility_summary_text"], str)
    assert isinstance(response["feasibility_full_text"], str)
    assert len(response["feasibility_summary_text"]) > 100
    assert len(response["feasibility_full_text"]) > 1000
    print("PASS text outputs are non-empty strings")


def test_happy_path_feasibility_data_is_dict():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    data = response["feasibility_data"]
    assert isinstance(data, dict)
    assert "practical_report" in data
    assert "code_strict_report" in data
    assert "gaps" in data
    assert "cost_delta_lakhs" in data
    print("PASS feasibility_data has DesignGapAnalysis structure")


def test_happy_path_brief_summary_includes_key_fields():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    bs = response["brief_summary"]
    expected_keys = {
        "trace_id", "city", "plot_area_sqm", "plot_facing",
        "floor_count", "budget_min_lakhs", "budget_max_lakhs",
        "risk_level",
    }
    assert set(bs.keys()) == expected_keys
    assert bs["city"] == "chennai"
    assert bs["plot_area_sqm"] == 180.0
    print("PASS brief_summary has expected reference fields")


def test_happy_path_response_is_json_serializable():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    # Round-trip
    serialized = json.dumps(response)
    parsed = json.loads(serialized)
    assert parsed["ok"] is True
    print(f"PASS response round-trips through json.dumps ({len(serialized)} chars)")


# ─── feasibility_input parsing ────────────────────────────────────────

def test_feasibility_input_verified_field():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "user_provided_verified"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    # Verified soil = no soil unknown
    unknowns = response["feasibility_data"]["practical_report"]["unknowns"]
    soil_unknowns = [u for u in unknowns if u["field_name"] == "soil_type"]
    assert len(soil_unknowns) == 0
    print("PASS verified soil_type → no soil unknown in response")


def test_feasibility_input_unverified_field():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "user_provided_unverified"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    print("PASS unverified soil_type accepted")


def test_feasibility_input_doesnt_know():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": None, "source": "user_doesnt_know"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    # USER_DOESNT_KNOW → uses city default → soil_type unknown surfaces
    unknowns = response["feasibility_data"]["practical_report"]["unknowns"]
    soil_unknowns = [u for u in unknowns if u["field_name"] == "soil_type"]
    assert len(soil_unknowns) == 1
    print("PASS user_doesnt_know soil → city default + unknown surfaces")


def test_feasibility_input_water_table_verified():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "water_table_depth_m": {"value": 12.0, "source": "user_provided_verified"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    # Verified WT = WT code-strict passes
    blocking = response["feasibility_data"]["code_strict_report"]["blocking_issues"]
    wt_blocking = [b for b in blocking if "water_table" in b["check_id"]]
    assert len(wt_blocking) == 0
    print("PASS verified water_table → no code-strict WT blocking")


def test_feasibility_input_all_six_fields_can_be_provided():
    """Test that all 6 FeasibilityInput fields can be set in one request."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "user_provided_verified"},
        "water_table_depth_m": {"value": 8.0, "source": "user_provided_verified"},
        "distance_from_electric_line_m": {
            "value": 10.0, "source": "user_provided_verified",
        },
        "electric_line_type": {
            "value": "lt", "source": "user_provided_verified",
        },
        "distance_from_water_course_m": {
            "value": 100.0, "source": "user_provided_verified",
        },
        "has_water_course_within_30m": {
            "value": False, "source": "user_provided_verified",
        },
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    print("PASS all 6 FeasibilityInput fields accepted in one request")


def test_feasibility_input_partial_population():
    """Setting just 1 field should work; others default to NOT_ASKED."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "user_provided_verified"},
        # Other 5 not specified
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    print("PASS partial feasibility_input population works")


# ─── Legacy kwargs ───────────────────────────────────────────────────

def test_legacy_electric_line_kwargs():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(
        distance_from_electric_line_m=10.0,
        electric_line_type="lt",
    )
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    print("PASS legacy distance_from_electric_line_m + electric_line_type accepted")


def test_legacy_water_course_kwargs():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(
        has_water_course_within_30m=False,
    )
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 200
    print("PASS legacy has_water_course_within_30m accepted")


# ─── Error handling ──────────────────────────────────────────────────

def test_bad_json_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    status, response = handle_feasibility_run(b"not json at all")
    assert status == 400
    assert "Invalid JSON" in response["errors"][0]
    print("PASS bad JSON → 400 with clear error")


def test_non_object_json_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    status, response = handle_feasibility_run(b'["not", "an", "object"]')
    assert status == 400
    print("PASS non-object JSON (e.g. array) → 400")


def test_missing_required_field_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload()
    del payload["plot_width_m"]
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    print("PASS missing required field → 400")


def test_unsupported_city_returns_400_not_500():
    """User input errors (e.g., unsupported city) should be 400, not 500."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(city="kolkata")
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400, f"Expected 400 for unsupported city, got {status}"
    assert "Input validation failed" in response["errors"][0]
    print("PASS unsupported city returns 400 (not 500)")


def test_bad_floor_structure_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(floors=[
        {"floor_number": 0, "floor_use": "INVALID", "rooms": []},
    ])
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    assert "Invalid floor structure" in response["errors"][0]
    print("PASS bad floor structure → 400")


def test_bad_field_source_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "bogus"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    assert "FieldSource" in response["errors"][0]
    print("PASS bad source enum → 400 with clear FieldSource error")


def test_verified_with_null_value_returns_400():
    """Source/value invariant: VERIFIED requires non-null value."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": None, "source": "user_provided_verified"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    print("PASS VERIFIED + null value → 400 (invariant violation)")


def test_doesnt_know_with_value_returns_400():
    """Source/value invariant: DOESNT_KNOW requires null value."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "soil_type": {"value": "laterite", "source": "user_doesnt_know"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    print("PASS DOESNT_KNOW + value → 400 (invariant violation)")


def test_bad_legacy_kwarg_type_returns_400():
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(
        distance_from_electric_line_m="not a number",
    )
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    print("PASS bad legacy kwarg type → 400")


def test_bad_feasibility_input_field_value_type_returns_400():
    """If value cannot be coerced to expected type, return 400."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    payload = _minimal_valid_payload(feasibility_input={
        "water_table_depth_m": {"value": "not a float",
                                "source": "user_provided_verified"},
    })
    status, response = handle_feasibility_run(json.dumps(payload).encode())
    assert status == 400
    print("PASS bad value type for feasibility field → 400")


# ─── Server routing wiring ───────────────────────────────────────────

def test_server_module_imports_handle_feasibility_run():
    """Verify the server module imports the new handler."""
    from buildemup.api import server
    assert hasattr(server, "handle_feasibility_run")
    print("PASS server module imports handle_feasibility_run")


def test_server_route_registered_in_do_post():
    """Verify /api/feasibility/run path is in server's do_POST source."""
    import inspect
    from buildemup.api import server
    source = inspect.getsource(server.BriefCaptureHandler.do_POST)
    assert "/api/feasibility/run" in source
    print("PASS /api/feasibility/run route is registered")


# ─── C1 endpoint NOT broken by Session I ─────────────────────────────

def test_c1_endpoint_still_works():
    """The existing /api/brief/capture endpoint should still work."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _minimal_valid_payload()
    status, response = handle_brief_capture(json.dumps(payload).encode())
    assert status == 200
    assert response["ok"] is True
    # C1 has its own response shape — make sure it didn't change
    assert "trace_id" in response
    assert "rendered_explain" in response
    print("PASS existing C1 /api/brief/capture endpoint still works")


def test_c1_endpoint_response_shape_unchanged():
    """C1's response shape should not be touched by Session I."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _minimal_valid_payload()
    status, response = handle_brief_capture(json.dumps(payload).encode())
    expected_c1_keys = {
        "ok", "trace_id", "rendered_explain", "proceed_with_warnings",
    }
    # C1 may add other keys but these MUST be present
    assert expected_c1_keys.issubset(set(response.keys()))
    print("PASS C1 response shape preserves required keys")


# ─── End-to-end realism ──────────────────────────────────────────────

def test_endpoint_reflects_orchestrator_for_normal_brief():
    """The endpoint output should match what running orchestrator directly produces."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )

    # Build the same brief two ways: once via API, once directly
    payload = _minimal_valid_payload()

    # API path
    status, api_resp = handle_feasibility_run(json.dumps(payload).encode())

    # Direct path
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
    direct = run_feasibility(out.brief, c7_cost_estimate=out.c7_preview_cost)

    # Scores should match exactly
    api_p = api_resp["feasibility_data"]["practical_report"]["overall_score"]
    api_c = api_resp["feasibility_data"]["code_strict_report"]["overall_score"]
    assert api_p == direct.practical_report.overall_score
    assert api_c == direct.code_strict_report.overall_score
    print(f"PASS API output matches direct orchestrator (P={api_p}, C={api_c})")


def test_endpoint_handles_all_6_cities():
    """Verify the endpoint works for each launch city."""
    from buildemup.api.feasibility_endpoint import handle_feasibility_run
    cities = ["chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi"]
    for city in cities:
        payload = _minimal_valid_payload(city=city)
        status, response = handle_feasibility_run(json.dumps(payload).encode())
        assert status == 200, f"Failed for {city}: {response.get('errors')}"
    print(f"PASS endpoint works for all 6 cities")


# ─── Baseline ─────────────────────────────────────────────────────────

def test_v0_9_3_baseline_unaffected_by_session_i():
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
    print("PASS v0.9.3 baseline unaffected by Session I")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session I (API endpoint + C1+C2 chained)")
    print("=" * 70)
    print()

    print("--- Happy path ---")
    test_happy_path_returns_200()
    test_happy_path_includes_all_top_level_keys()
    test_happy_path_text_outputs_are_strings()
    test_happy_path_feasibility_data_is_dict()
    test_happy_path_brief_summary_includes_key_fields()
    test_happy_path_response_is_json_serializable()
    print()

    print("--- feasibility_input parsing ---")
    test_feasibility_input_verified_field()
    test_feasibility_input_unverified_field()
    test_feasibility_input_doesnt_know()
    test_feasibility_input_water_table_verified()
    test_feasibility_input_all_six_fields_can_be_provided()
    test_feasibility_input_partial_population()
    print()

    print("--- Legacy kwargs ---")
    test_legacy_electric_line_kwargs()
    test_legacy_water_course_kwargs()
    print()

    print("--- Error handling ---")
    test_bad_json_returns_400()
    test_non_object_json_returns_400()
    test_missing_required_field_returns_400()
    test_unsupported_city_returns_400_not_500()
    test_bad_floor_structure_returns_400()
    test_bad_field_source_returns_400()
    test_verified_with_null_value_returns_400()
    test_doesnt_know_with_value_returns_400()
    test_bad_legacy_kwarg_type_returns_400()
    test_bad_feasibility_input_field_value_type_returns_400()
    print()

    print("--- Server routing wiring ---")
    test_server_module_imports_handle_feasibility_run()
    test_server_route_registered_in_do_post()
    print()

    print("--- C1 endpoint preserved ---")
    test_c1_endpoint_still_works()
    test_c1_endpoint_response_shape_unchanged()
    print()

    print("--- End-to-end realism ---")
    test_endpoint_reflects_orchestrator_for_normal_brief()
    test_endpoint_handles_all_6_cities()
    print()

    print("--- Baseline ---")
    test_v0_9_3_baseline_unaffected_by_session_i()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION I TESTS PASSED")
    print("=" * 70)
