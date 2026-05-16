"""
v0.1 Session 6 tests — API endpoint + HTTP server.

Covers the API layer:
  - handle_brief_capture with valid payload, missing fields, bad JSON
  - handle_vastu_partial_items
  - End-to-end HTTP server (boot server, POST form JSON, parse response)
  - Static file serving (GET /brief_form.html, .js, .css)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json


def _valid_payload(**overrides):
    """Build a valid JSON payload for POST /api/brief/capture."""
    payload = {
        "plot_width_m": 12.0, "plot_depth_m": 15.0, "plot_facing": "N",
        "city": "chennai", "road_width_m": 9.0, "plot_type": "detached",
        "user_setback_front_m": 1.5, "user_setback_rear_m": 1.5,
        "user_setback_side_left_m": 1.5, "user_setback_side_right_m": 1.5,
        "floors": [
            {
                "floor_number": 0, "floor_use": "residential",
                "rooms": [
                    {"room_type": "living", "count": 1},
                    {"room_type": "kitchen", "count": 1},
                    {"room_type": "bathroom_common", "count": 1},
                ],
            },
            {
                "floor_number": 1, "floor_use": "residential",
                "rooms": [
                    {"room_type": "bedroom_master", "count": 1},
                    {"room_type": "bathroom_attached", "count": 1},
                ],
            },
        ],
        "budget_min_lakhs": 20, "budget_max_lakhs": 30,
        "vastu_preference": "partial",
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────
# API endpoint unit tests
# ─────────────────────────────────────────────────────────────────────────

def test_vastu_partial_items_endpoint():
    """GET /api/vastu/partial-items returns exactly 7 items."""
    from buildemup.api.brief_endpoint import handle_vastu_partial_items
    status, body = handle_vastu_partial_items()
    assert status == 200
    assert body["ok"] is True
    assert body["count"] == 7
    assert len(body["partial_items"]) == 7
    # Check spot sample: main door item present
    assert any("main door" in item.lower() for item in body["partial_items"])
    print(f"PASS vastu/partial-items returns 7 items")


def test_brief_capture_valid_payload():
    """POST valid payload → 200 with full response."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_valid_payload()))
    assert status == 200
    assert body["ok"] is True
    assert body["trace_id"]
    assert body["ready_for_downstream"] is True
    assert body["c7_preview_cost_lakhs"] is not None
    assert body["c7_preview_cost_lakhs"] > 0
    assert body["brief_summary"]["city"] == "chennai"
    assert body["brief_summary"]["plot_width_m"] == 12.0
    assert len(body["top_guidance"]) <= 3
    assert len(body["rendered_explain"]) > 1000    # non-trivial rendering
    print(f"PASS valid payload → 200, "
          f"₹{body['c7_preview_cost_lakhs']}L from C7")


def test_brief_capture_invalid_json():
    """Bad JSON → 400 with error."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture("{not valid json}")
    assert status == 400
    assert body["ok"] is False
    assert "Invalid JSON" in body["errors"][0]
    print("PASS invalid JSON → 400")


def test_brief_capture_missing_required_field():
    """Missing plot_width_m → 400."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _valid_payload()
    del payload["plot_width_m"]
    status, body = handle_brief_capture(json.dumps(payload))
    assert status == 400
    assert body["ok"] is False
    assert "plot_width_m" in body["errors"][0]
    print("PASS missing required field → 400 with field name")


def test_brief_capture_unknown_room_type():
    """Unknown room_type → 400 listing valid options."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _valid_payload()
    payload["floors"] = [{
        "floor_number": 0, "floor_use": "residential",
        "rooms": [{"room_type": "swimming_pool", "count": 1}],
    }]
    status, body = handle_brief_capture(json.dumps(payload))
    assert status == 400
    assert "Unknown room_type" in body["errors"][0]
    print("PASS unknown room_type → 400 with suggestion list")


def test_brief_capture_unknown_floor_use():
    """Unknown floor_use → 400."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _valid_payload()
    payload["floors"] = [{
        "floor_number": 0, "floor_use": "basement",
        "rooms": [],
    }]
    status, body = handle_brief_capture(json.dumps(payload))
    assert status == 400
    assert "Unknown floor_use" in body["errors"][0]
    print("PASS unknown floor_use → 400")


def test_brief_capture_non_compliant_setbacks():
    """Non-compliant setbacks → 200 with ready=False + STRONG_CONCERN."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _valid_payload(
        user_setback_front_m=0.3,    # way below compliance
        user_setback_side_left_m=0.3,
    )
    status, body = handle_brief_capture(json.dumps(payload))
    assert status == 200        # still 200 — we never refuse
    assert body["ok"] is True
    assert body["ready_for_downstream"] is False
    assert body["brief_summary"]["compliance"]["is_setback_compliant"] is False
    # Top 3 should include STRONG_CONCERN
    severities = [m["severity"] for m in body["top_guidance"]]
    assert "strong_concern" in severities
    print("PASS non-compliant setbacks → 200 with ready=False "
          "+ STRONG_CONCERN in top 3")


def test_brief_capture_returns_compliance_details():
    """Response includes compliance details + violations list."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    payload = _valid_payload(
        user_setback_front_m=0.5,     # violating
    )
    status, body = handle_brief_capture(json.dumps(payload))
    compliance = body["brief_summary"]["compliance"]
    assert compliance["is_setback_compliant"] is False
    assert len(compliance["violations"]) > 0
    assert "source_authority" in compliance
    print(f"PASS compliance details included: "
          f"{len(compliance['violations'])} violations, "
          f"source={compliance['source_authority']}")


def test_brief_capture_all_6_cities():
    """Each of 6 cities produces a valid response."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    for city in ["chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi"]:
        status, body = handle_brief_capture(json.dumps(_valid_payload(city=city)))
        assert status == 200
        assert body["ok"] is True
        assert body["brief_summary"]["city"] == city
    print("PASS all 6 cities process through the API successfully")


def test_brief_capture_rendered_explain_contains_sections():
    """Rendered explain in response has all major sections."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    status, body = handle_brief_capture(json.dumps(_valid_payload()))
    r = body["rendered_explain"]
    for section in ["YOUR BRIEF", "TOP 3 RECOMMENDATIONS", "PLOT",
                    "SETBACKS", "BUDGET", "ASSUMPTIONS USED",
                    "REPRODUCIBILITY"]:
        assert section in r, f"Section '{section}' missing"
    print("PASS rendered_explain includes all major sections")


def test_brief_capture_with_all_plot_types():
    """All 3 plot types process through the API."""
    from buildemup.api.brief_endpoint import handle_brief_capture
    # DETACHED (default)
    status, body = handle_brief_capture(json.dumps(_valid_payload()))
    assert status == 200 and body["ok"]

    # SEMI_DETACHED
    status, body = handle_brief_capture(json.dumps(_valid_payload(
        plot_type="semi_detached", shared_side="left",
    )))
    assert status == 200 and body["ok"]
    assert body["brief_summary"]["plot_type"] == "semi_detached"

    # CONTINUOUS
    status, body = handle_brief_capture(json.dumps(_valid_payload(
        plot_type="continuous",
        user_setback_side_left_m=0.0,
        user_setback_side_right_m=0.0,
    )))
    assert status == 200 and body["ok"]
    assert body["brief_summary"]["plot_type"] == "continuous"
    print("PASS all 3 plot types process through the API")


# ─────────────────────────────────────────────────────────────────────────
# HTTP server integration test
# ─────────────────────────────────────────────────────────────────────────

def test_http_server_end_to_end():
    """Boot server, POST payload, verify response."""
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer
    from buildemup.api.server import BriefCaptureHandler

    # Use ephemeral port
    server = HTTPServer(("127.0.0.1", 0), BriefCaptureHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{port}"

        # 1. GET /api/vastu/partial-items
        with urllib.request.urlopen(f"{base_url}/api/vastu/partial-items", timeout=5) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            assert body["ok"] is True
            assert body["count"] == 7

        # 2. POST /api/brief/capture
        req = urllib.request.Request(
            f"{base_url}/api/brief/capture",
            data=json.dumps(_valid_payload()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            assert body["ok"] is True
            assert body["c7_preview_cost_lakhs"] > 0

        # 3. GET /brief_form.html (static)
        with urllib.request.urlopen(f"{base_url}/brief_form.html", timeout=5) as resp:
            assert resp.status == 200
            html = resp.read().decode()
            assert "BuildemUp" in html
            # As of v0.10.1: plot dims are in feet on the form (engine still in metres)
            assert "plot_width_ft" in html

        # 4. GET /brief_form.js (static)
        with urllib.request.urlopen(f"{base_url}/brief_form.js", timeout=5) as resp:
            assert resp.status == 200
            js = resp.read().decode()
            assert "BuildemUp Brief Form" in js

        # 5. GET /brief_form.css (static)
        with urllib.request.urlopen(f"{base_url}/brief_form.css", timeout=5) as resp:
            assert resp.status == 200
            css = resp.read().decode()
            assert "BuildemUp" in css

        # 6. GET / redirects to form
        try:
            resp = urllib.request.urlopen(
                f"{base_url}/", timeout=5,
            )
            # urllib follows redirects by default — we'll end up on the form
            assert resp.status == 200
            assert "BuildemUp" in resp.read().decode()
        except urllib.error.HTTPError as e:
            # Manual redirect check — should not 404
            assert e.code != 404

        # 7. 404 for unknown path
        try:
            urllib.request.urlopen(f"{base_url}/does-not-exist", timeout=5)
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 404

        print("PASS HTTP server end-to-end: "
              "vastu-items, brief-capture, static form/js/css, "
              "redirect, 404 all working")
    finally:
        server.shutdown()
        server.server_close()


def test_http_server_handles_bad_post():
    """Server returns 400 (not 500) for bad JSON via HTTP."""
    import threading
    import urllib.request
    import urllib.error
    from http.server import HTTPServer
    from buildemup.api.server import BriefCaptureHandler

    server = HTTPServer(("127.0.0.1", 0), BriefCaptureHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/brief/capture",
            data=b"{malformed",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            body = json.loads(e.read().decode())
            assert body["ok"] is False
    finally:
        server.shutdown()
        server.server_close()
    print("PASS server returns 400 for malformed POST (not 500)")


def test_http_server_cors_header():
    """Responses include CORS header for cross-origin usage."""
    import threading
    import urllib.request
    from http.server import HTTPServer
    from buildemup.api.server import BriefCaptureHandler

    server = HTTPServer(("127.0.0.1", 0), BriefCaptureHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/vastu/partial-items",
            timeout=5,
        ) as resp:
            cors = resp.headers.get("Access-Control-Allow-Origin")
            assert cors == "*"
    finally:
        server.shutdown()
        server.server_close()
    print("PASS CORS header present (Access-Control-Allow-Origin: *)")


# ─────────────────────────────────────────────────────────────────────────
# Static asset validation
# ─────────────────────────────────────────────────────────────────────────

def test_static_form_html_structure():
    """Form HTML has the expected structure (step panels + fields)."""
    from pathlib import Path
    html_path = Path(__file__).parent.parent / "static" / "brief_form.html"
    assert html_path.exists(), f"Form HTML missing at {html_path}"
    # S54-005: explicit utf-8 — on Windows the default is cp1252 which
    # chokes on any non-ASCII byte in the file (e.g., emoji in headers).
    html = html_path.read_text(encoding="utf-8")

    # Must have 4 step panels
    import re
    step_panels = re.findall(r'data-step="(\d+)"', html)
    # Each step appears in indicator + panel — expect at least 4 unique
    assert "1" in step_panels
    assert "4" in step_panels

    # Must have key fields (renamed to feet in v0.10.1)
    required_fields = [
        "plot_width_ft", "plot_depth_ft", "plot_facing", "city",
        "road_width_ft", "plot_type", "user_setback_front_ft",
        "budget_min_lakhs", "budget_max_lakhs", "vastu_preference",
    ]
    for f in required_fields:
        assert f'name="{f}"' in html, f"Field '{f}' missing in HTML"

    # All 6 cities in the dropdown
    for city in ["chennai", "bangalore", "hyderabad",
                 "mumbai", "pune", "delhi"]:
        assert f'value="{city}"' in html
    print(f"PASS brief_form.html has 4 steps + "
          f"{len(required_fields)} fields + 6 cities")


def test_static_form_js_loads_vastu():
    """Form JS has API endpoints and save/resume logic."""
    from pathlib import Path
    js_path = Path(__file__).parent.parent / "static" / "brief_form.js"
    assert js_path.exists()
    js = js_path.read_text()
    # Must call the right endpoints
    assert "/api/brief/capture" in js
    assert "/api/vastu/partial-items" in js
    # Save/resume logic (localStorage, generateResumeToken)
    assert "localStorage" in js
    assert "generateResumeToken" in js or "resume_token" in js.lower()
    print("PASS brief_form.js has API endpoints + save/resume")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 1 v0.1 — Session 6 Tests: API + HTTP Server")
    print("=" * 70)
    print()
    print("--- API endpoint unit tests ---")
    test_vastu_partial_items_endpoint()
    test_brief_capture_valid_payload()
    test_brief_capture_invalid_json()
    test_brief_capture_missing_required_field()
    test_brief_capture_unknown_room_type()
    test_brief_capture_unknown_floor_use()
    test_brief_capture_non_compliant_setbacks()
    test_brief_capture_returns_compliance_details()
    test_brief_capture_all_6_cities()
    test_brief_capture_rendered_explain_contains_sections()
    test_brief_capture_with_all_plot_types()
    print()
    print("--- HTTP server integration ---")
    test_http_server_end_to_end()
    test_http_server_handles_bad_post()
    test_http_server_cors_header()
    print()
    print("--- Static asset validation ---")
    test_static_form_html_structure()
    test_static_form_js_loads_vastu()
    print()
    print("=" * 70)
    print("ALL SESSION 6 TESTS PASSED")
    print("=" * 70)
