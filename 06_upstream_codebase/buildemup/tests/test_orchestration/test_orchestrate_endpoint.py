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
    assert len(response["phases"]) == 18  # S59: +c03a_extreme_case_detection


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


def test_endpoint_reports_c15_c16_c17_terminal_state():
    """After S59:
       c15 OK (triples adapter), c16 OK|stub (drawings best-effort),
       c17 SKIPPED (separate /api/quote/compare flow).
    """
    status, response = handle_orchestrate(b"")
    by_id = {p["phase_id"]: p for p in response["phases"]}
    assert by_id["c15_problem_finder"]["status"] == "ok"
    assert by_id["c16_dual_drawings"]["status"] in ("ok", "stub")
    assert by_id["c17_quote_comparison"]["status"] == "skipped"
    assert "quote/compare" in by_id["c17_quote_comparison"]["skip_reason"]


def test_endpoint_reports_c12_c13_c14_ok_via_adapters():
    """C12 + C13 + C14 now ship OK via the S57 #4/#5/#6 adapters."""
    status, response = handle_orchestrate(b"")
    by_id = {p["phase_id"]: p for p in response["phases"]}
    assert by_id["c12_vertical_placement"]["status"] == "ok"
    assert by_id["c13_doors"]["status"] == "ok"
    assert by_id["c14_connection_graph"]["status"] == "ok"
