"""Smoke tests for the /api/orchestrate HTTP endpoint."""
from __future__ import annotations

import json

import pytest

from buildemup.api.orchestrate_endpoint import handle_orchestrate


# ──────────────────────────────────────────────────────────────────────
# Happy-path tests
# ──────────────────────────────────────────────────────────────────────


def test_orchestrate_endpoint_runs_with_default_inputs():
    """Empty body should use bangalore_40x60 + medium_brief defaults."""
    status, response = handle_orchestrate(b"")
    assert status == 200
    assert response["ok"] is True
    assert response["overall_status"] in {"ok", "stub"}
    assert response["total_elapsed_ms"] > 0
    assert len(response["phases"]) == 17


def test_orchestrate_endpoint_returns_all_phases_in_order():
    """Phases should appear in canonical pipeline order."""
    status, response = handle_orchestrate(b"")
    assert status == 200
    expected_first_phase = "c01_brief"
    expected_last_phase = "c17_quote_comparison"
    phases = response["phases"]
    assert phases[0]["phase_id"] == expected_first_phase
    assert phases[-1]["phase_id"] == expected_last_phase


def test_orchestrate_endpoint_accepts_custom_plot_and_brief():
    """Custom fixture names should be honored."""
    body = json.dumps({
        "plot_fixture": "chennai_30x40",
        "brief_fixture": "small_brief",
    }).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 200


def test_orchestrate_endpoint_accepts_config():
    """Config knobs should be honored."""
    body = json.dumps({
        "plot_fixture": "bangalore_40x60",
        "brief_fixture": "medium_brief",
        "config": {
            "vastu_tier": "OFF",
            "enable_c11b_refinement": False,
        },
    }).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 200
    assert response["config"]["vastu_tier"] == "OFF"
    assert response["config"]["enable_c11b_refinement"] is False
    # C11b should be SKIPPED
    c11b = next(p for p in response["phases"]
                if p["phase_id"] == "c11b_nsga_refinement")
    assert c11b["status"] == "skipped"


# ──────────────────────────────────────────────────────────────────────
# Validation error tests
# ──────────────────────────────────────────────────────────────────────


def test_orchestrate_endpoint_rejects_invalid_json():
    status, response = handle_orchestrate(b"{not valid json")
    assert status == 400
    assert response["ok"] is False
    assert any("invalid JSON" in e for e in response["errors"])


def test_orchestrate_endpoint_rejects_unknown_plot_fixture():
    body = json.dumps({"plot_fixture": "atlantis_42x42"}).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 400
    assert any("unknown plot_fixture" in e for e in response["errors"])


def test_orchestrate_endpoint_rejects_unknown_brief_fixture():
    body = json.dumps({"brief_fixture": "mansion_brief"}).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 400
    assert any("unknown brief_fixture" in e for e in response["errors"])


# ──────────────────────────────────────────────────────────────────────
# Phase reporting
# ──────────────────────────────────────────────────────────────────────


def test_endpoint_reports_stub_phases_with_reason():
    """C12-C17 should report status=stub with non-empty stub_reason."""
    status, response = handle_orchestrate(b"")
    stub_ids = {
        "c12_vertical_placement", "c13_doors", "c14_connection_graph",
        "c15_problem_finder", "c16_dual_drawings", "c17_quote_comparison",
    }
    for p in response["phases"]:
        if p["phase_id"] in stub_ids:
            assert p["status"] == "stub"
            assert p["stub_reason"], f"empty stub_reason for {p['phase_id']}"
