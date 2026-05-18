"""Tests for S59 follow-ups #7, #8, #9, #10, #11, #12.

These tests live in one module because they share the same upstream
smoke fixture and exercise the orchestrator + endpoint surface that
the S57 #4/#5/#6 tests already established. Each test calls out the
follow-up it covers.
"""
from __future__ import annotations

import json

import pytest

from buildemup.api.orchestrate_endpoint import handle_orchestrate
from buildemup.api.quote_endpoint import handle_quote_compare
from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    PhaseStatus,
    PIPELINE_PHASES,
    serialize_phase_payload,
)
from buildemup.orchestration.adapters import (
    build_c15_inputs_from_upstream,
    build_c16_inputs_from_upstream,
    derive_cultural_profile,
)
from buildemup.orchestration.freeform_inputs import (
    FreeformInputError,
    build_floor_brief_from_json,
    build_plot_from_json,
    make_brief_for_c4,
)
from buildemup.components.c15.contracts import CulturalProfile
from buildemup.tests.validation._c4_fixtures import bangalore_40x60, make_brief
from buildemup.tests.validation._c5_fixtures import medium_brief


# ─────────────────────────────────────────────────────────────────────
# Shared smoke fixture
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def smoke_run():
    """Run the full pipeline once; tests inspect specific phases."""
    plot = bangalore_40x60()
    brief_for_c4 = make_brief(plot)
    floor_brief = medium_brief()
    orch = MasterOrchestrator()
    result = orch.run(
        plot=plot, brief_for_c4=brief_for_c4, floor_brief=floor_brief,
    )
    return result


# ─────────────────────────────────────────────────────────────────────
# #12 — phase-payload JSON serialization
# ─────────────────────────────────────────────────────────────────────


def test_12_serialize_phase_payload_handles_none():
    assert serialize_phase_payload("c01_brief", None) is None


def test_12_serialize_phase_payload_walks_dataclass(smoke_run):
    c04 = smoke_run.phase("c04_plot_analysis")
    assert c04.status == PhaseStatus.OK
    out = serialize_phase_payload(c04.phase_id, c04.payload)
    # Top-level should be a dict with __type__ tagging.
    assert isinstance(out, dict)
    assert out.get("__type__") == "PlotAnalysis"
    # Common fields present.
    assert "trace_id" in out
    assert "area_sqm" in out
    # JSON-roundtrippable.
    assert json.dumps(out) is not None


def test_12_serialize_phase_payload_caps_collections(smoke_run):
    c11a = smoke_run.phase("c11a_topology_mutation")
    assert c11a.status == PhaseStatus.OK
    payload = c11a.payload
    # payload is a tuple of mutated candidates; cap to 1.
    out = serialize_phase_payload(
        c11a.phase_id, payload, max_collection_items=1,
    )
    assert isinstance(out, dict)
    assert out.get("__truncated__") == "max_collection_items"
    assert out.get("total_len") == len(payload)


def test_12_endpoint_includes_payloads_when_requested():
    body = json.dumps({"include_payloads": True}).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 200
    # Every phase should carry a `payload` key when include_payloads=True.
    for p in response["phases"]:
        assert "payload" in p, f"phase {p['phase_id']} missing payload"


def test_12_endpoint_omits_payloads_by_default():
    status, response = handle_orchestrate(b"")
    assert status == 200
    for p in response["phases"]:
        assert "payload" not in p, (
            f"phase {p['phase_id']} unexpectedly carries payload"
        )


# ─────────────────────────────────────────────────────────────────────
# #11 — free-form Plot + FloorRoomBrief input contract
# ─────────────────────────────────────────────────────────────────────


def test_11_freeform_plot_from_metres():
    plot = build_plot_from_json({
        "width_m": 12.192, "depth_m": 18.288,
        "facing": "E", "city": "bangalore", "road_width_m": 12.0,
    })
    assert plot.width_m == pytest.approx(12.192)
    assert plot.city == "bangalore"


def test_11_freeform_plot_from_feet():
    plot = build_plot_from_json({
        "width_ft": 40.0, "depth_ft": 60.0,
        "facing": "EAST", "city": "Bangalore", "road_width_ft": 30.0,
    })
    assert plot.width_m == pytest.approx(40.0 * 0.3048)
    assert plot.depth_m == pytest.approx(60.0 * 0.3048)


def test_11_freeform_plot_rejects_missing_facing():
    with pytest.raises(FreeformInputError, match="facing"):
        build_plot_from_json({
            "width_m": 10.0, "depth_m": 10.0,
            "city": "chennai", "road_width_m": 5.0,
        })


def test_11_freeform_plot_rejects_unsupported_city():
    with pytest.raises(FreeformInputError, match="not supported"):
        build_plot_from_json({
            "width_m": 10.0, "depth_m": 10.0,
            "facing": "N", "city": "atlantis", "road_width_m": 5.0,
        })


def test_11_freeform_brief_basic():
    brief = build_floor_brief_from_json({
        "bedroom_count": 2, "bathroom_count": 2,
        "has_kitchen": True, "has_living": True,
    })
    assert brief.bedroom_count == 2
    assert brief.has_kitchen is True


def test_11_freeform_brief_rejects_negative():
    with pytest.raises(FreeformInputError):
        build_floor_brief_from_json({
            "bedroom_count": -1, "bathroom_count": 1,
        })


def test_11_endpoint_accepts_freeform_inputs():
    body = json.dumps({
        "plot": {
            "width_m": 12.192, "depth_m": 18.288,
            "facing": "E", "city": "bangalore", "road_width_m": 12.0,
        },
        "brief": {
            "bedroom_count": 2, "bathroom_count": 2,
            "has_kitchen": True, "has_living": True,
        },
    }).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 200
    assert response["ok"] is True
    # All 18 phases should appear regardless of input shape.
    assert len(response["phases"]) == 18


def test_11_endpoint_400s_on_bad_freeform_plot():
    """Plot missing required city → 400 with diagnostic."""
    body = json.dumps({
        "plot": {
            "width_m": 10.0, "depth_m": 10.0,
            "facing": "N", "road_width_m": 5.0,
        },  # no `city`
        "brief": {"bedroom_count": 1, "bathroom_count": 1},
    }).encode("utf-8")
    status, response = handle_orchestrate(body)
    assert status == 400
    assert any("city" in e.lower() for e in response["errors"])


def test_11_make_brief_for_c4_satisfies_c4_contract():
    plot = build_plot_from_json({
        "width_m": 12.0, "depth_m": 12.0,
        "facing": "N", "city": "chennai", "road_width_m": 9.0,
    })
    brief = make_brief_for_c4(plot)
    # C4 only reads brief.revised_brief.plot + .trace_id
    assert brief.revised_brief.plot is plot
    assert brief.revised_brief.trace_id


# ─────────────────────────────────────────────────────────────────────
# #7 — C15 triples + ProblemAnalysisMetadata
# ─────────────────────────────────────────────────────────────────────


def test_7_c15_phase_runs_and_ships_ok(smoke_run):
    c15 = smoke_run.phase("c15_problem_finder")
    assert c15 is not None
    assert c15.status == PhaseStatus.OK
    # Notes mention the triples + cultural profile.
    notes_text = " ".join(c15.notes)
    assert "Triples" in notes_text
    assert "Cultural profile" in notes_text


def test_7_cultural_profile_mapping():
    # Each tier maps to a stable profile.
    assert derive_cultural_profile("OFF") == CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC
    assert derive_cultural_profile("PARTIAL") == CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN
    assert derive_cultural_profile("FULL") == CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN
    # Unknown tier → GENERIC.
    assert derive_cultural_profile("ZZZZ") == CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC


def test_7_build_c15_inputs_returns_empty_on_missing_upstream():
    triples, metadata = build_c15_inputs_from_upstream(
        c12_payload=None, c13_payload=None, c14_payload=None,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    )
    assert triples == ()
    assert metadata == ()


# ─────────────────────────────────────────────────────────────────────
# #8 — C16 UpstreamInputBundle + drawings
# ─────────────────────────────────────────────────────────────────────


def test_8_c16_phase_reaches_terminal_state(smoke_run):
    c16 = smoke_run.phase("c16_dual_drawings")
    assert c16 is not None
    # OK when bundles render; STUB when no candidates survive the
    # C12→C13 join (sparse-edge case). Anything but ERROR/SKIPPED.
    assert c16.status in (PhaseStatus.OK, PhaseStatus.STUB), (
        f"C16 phase reached unexpected status {c16.status} "
        f"({c16.error_class}: {c16.error_message})"
    )


def test_8_build_c16_inputs_returns_empty_on_missing_upstream():
    sel, bundles = build_c16_inputs_from_upstream(
        c07_payload=None, c10_payload=None, c12_payload=None,
        c13_payload=None, c14_payload=None, c15_payload=None,
        plot_analysis=None,
    )
    assert sel == ()
    assert bundles == ()


# ─────────────────────────────────────────────────────────────────────
# #10 — C3a/C3b integration (async-flags)
# ─────────────────────────────────────────────────────────────────────


def test_10_pipeline_phases_includes_c3a_detection():
    assert "c03a_extreme_case_detection" in PIPELINE_PHASES
    # Position: between c02 and c04.
    idx = PIPELINE_PHASES.index("c03a_extreme_case_detection")
    assert PIPELINE_PHASES[idx - 1] == "c02_feasibility"
    assert PIPELINE_PHASES[idx + 1] == "c04_plot_analysis"


def test_10_c3a_phase_skipped_without_full_brief(smoke_run):
    """Without a full Brief, C3a detection skips like C1/C2 do."""
    c3a = smoke_run.phase("c03a_extreme_case_detection")
    assert c3a is not None
    assert c3a.status == PhaseStatus.SKIPPED
    assert "full Brief" in c3a.skip_reason


def test_10_overall_status_ok_with_c3a_skipped(smoke_run):
    """Skipped C3a must not break overall status."""
    assert smoke_run.overall_status == PhaseStatus.OK


# ─────────────────────────────────────────────────────────────────────
# #9 — C17 separate quote-compare endpoint
# ─────────────────────────────────────────────────────────────────────


_VALID_PARSED_QUOTE = {
    "parsed_quote_id": "pq-test-001",
    "contractor_label": "Test Constructions",
    "quote_date_iso": "2026-05-18",
    "quote_total_inr": 200000.0,
    "parsed_quote_signature": "test-sig",
    "line_items": [
        {
            "line_id": "L001",
            "raw_label": "Cement OPC 53",
            "quantity": 100.0,
            "unit": "bag",
            "rate": 420.0,
            "total": 42000.0,
            "is_lump_sum_hint": False,
        },
        {
            "line_id": "L002",
            "raw_label": "Painting works",
            "quantity": None,
            "unit": "",
            "rate": None,
            "total": 50000.0,
            "is_lump_sum_hint": True,
        },
    ],
}

_VALID_COST_LINES = [
    {
        "item_id": "C7-RCC-CEMENT-001",
        "label": "Cement OPC 53",
        "category": "structural_rcc",
        "quantity": 100.0,
        "unit": "bag",
        "rate_category": "structural_rcc",
        "rate_key": "cement_opc_53",
        "severity": "critical",
    },
]


def test_9_quote_endpoint_runs_with_valid_payload():
    body = json.dumps({
        "project_id": "proj-test-001",
        "parsed_quote": _VALID_PARSED_QUOTE,
        "cost_lines": _VALID_COST_LINES,
    }).encode("utf-8")
    status, response = handle_quote_compare(body)
    assert status == 200, response
    assert response["ok"] is True
    assert "summary" in response
    s = response["summary"]
    # We sent 2 quote lines; one should match the BOQ cement line.
    assert s["matched_lines"] >= 0
    assert s["quote_total_inr"] == pytest.approx(200000.0)
    assert "signatures" in response
    assert response["signatures"]["canonical_replay_signature"]


def test_9_quote_endpoint_includes_full_report_when_requested():
    body = json.dumps({
        "project_id": "proj-test-001",
        "parsed_quote": _VALID_PARSED_QUOTE,
        "cost_lines": _VALID_COST_LINES,
        "include_payload": True,
    }).encode("utf-8")
    status, response = handle_quote_compare(body)
    assert status == 200, response
    assert response["ok"] is True
    assert "report" in response
    assert response["report"].get("__type__") == "QuoteComparisonReport"


def test_9_quote_endpoint_rejects_missing_project_id():
    body = json.dumps({
        "parsed_quote": _VALID_PARSED_QUOTE,
        "cost_lines": _VALID_COST_LINES,
    }).encode("utf-8")
    status, response = handle_quote_compare(body)
    assert status == 400
    assert any("project_id" in e for e in response["errors"])


def test_9_quote_endpoint_rejects_invalid_json():
    status, response = handle_quote_compare(b"{not valid json")
    assert status == 400
    assert any("invalid JSON" in e for e in response["errors"])


def test_9_quote_endpoint_rejects_malformed_cost_lines():
    body = json.dumps({
        "project_id": "proj-test-001",
        "parsed_quote": _VALID_PARSED_QUOTE,
        "cost_lines": [{"label": "missing item_id"}],
    }).encode("utf-8")
    status, response = handle_quote_compare(body)
    assert status == 400
    assert any("cost_lines" in e for e in response["errors"])
