"""POST /api/orchestrate — S56 MVP master orchestrator endpoint.

Accepts a JSON request describing the brief inputs, runs the full
MasterOrchestrator pipeline (C4 → C11a real chain + C11b STUB with
StubEvaluator + C12-C17 STUB), and returns a unified per-phase result
summary.

Request shape (all fields optional except where noted):
  {
    "plot_fixture": "bangalore_40x60" | "chennai_30x40" | ... ,  # required for MVP
    "brief_fixture": "medium_brief" | "small_brief" | "large_brief",  # default: medium_brief
    "config": {
      "vastu_tier": "OFF" | "PARTIAL" | "FULL",  # default PARTIAL
      "max_topology_mutations": int,             # default 4
      "enable_c11b_refinement": bool,            # default true
      "halt_on_first_failure": bool              # default false
    }
  }

MVP CONSTRAINT: the endpoint uses NAMED FIXTURE inputs from the test
suite rather than free-form Plot + FloorRoomBrief construction. This is
deliberate — free-form plot/brief construction requires substantial
input validation work (B-S57-ORCHESTRATE-FREEFORM-INPUTS) tracked in the
S57 follow-ups doc. The fixture-based MVP is sufficient for architect
demonstration (B-238) and for smoke-testing the pipeline.

Response shape:
  {
    "ok": bool,                            # true unless overall_status == ERROR
    "overall_status": "ok|error|stub|skipped",
    "total_elapsed_ms": float,
    "summary": "MasterOrchestrator: ..." str,
    "phases": [
      {
        "phase_id": "c04_plot_analysis",
        "status": "ok|error|stub|skipped",
        "elapsed_ms": float,
        "error_class": "" | "ValueError",
        "error_message": "" | "...",
        "skip_reason": "" | "...",
        "stub_reason": "" | "...",
        "notes": [str, ...]
      },
      ...
    ]
  }

NOTE: Phase payloads (PlotAnalysis dataclass, candidate tuples, etc.)
are NOT serialized to JSON in MVP. The response carries only the
per-phase status + metadata. Payload serialization is its own work
(B-S57-ORCHESTRATE-PAYLOAD-SERIALIZATION) — many of the dataclasses
have nested structures and references that need deliberate JSON shapes.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    PhaseStatus,
)


_LOG = logging.getLogger(__name__)


# Curated fixture registry for MVP. Production callers will use a
# free-form brief input contract (B-S57 follow-up).
_PLOT_FIXTURES = {
    "chennai_30x40", "bangalore_40x60", "delhi_60x90",
    "mumbai_30x40", "pune_30x40", "hyderabad_30x40",
}
_BRIEF_FIXTURES = {"small_brief", "medium_brief", "large_brief"}


def handle_orchestrate(body: bytes) -> Tuple[int, Dict[str, Any]]:
    """POST /api/orchestrate handler.

    Returns (status_code, response_dict) suitable for the stdlib server's
    `_send_json` helper.
    """
    # ─── Parse + validate input ───────────────────────────────────
    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"invalid JSON: {e}"],
        }

    plot_fixture_name = payload.get("plot_fixture", "bangalore_40x60")
    brief_fixture_name = payload.get("brief_fixture", "medium_brief")

    if plot_fixture_name not in _PLOT_FIXTURES:
        return 400, {
            "ok": False,
            "errors": [
                f"unknown plot_fixture {plot_fixture_name!r}; "
                f"allowed: {sorted(_PLOT_FIXTURES)}"
            ],
        }
    if brief_fixture_name not in _BRIEF_FIXTURES:
        return 400, {
            "ok": False,
            "errors": [
                f"unknown brief_fixture {brief_fixture_name!r}; "
                f"allowed: {sorted(_BRIEF_FIXTURES)}"
            ],
        }

    # ─── Build config ─────────────────────────────────────────────
    config_payload = payload.get("config", {})
    try:
        config = MasterOrchestratorConfig(
            vastu_tier=config_payload.get("vastu_tier", "PARTIAL"),
            max_topology_mutations=int(
                config_payload.get("max_topology_mutations", 4)
            ),
            enable_c11b_refinement=bool(
                config_payload.get("enable_c11b_refinement", True)
            ),
            halt_on_first_failure=bool(
                config_payload.get("halt_on_first_failure", False)
            ),
        )
    except (TypeError, ValueError) as e:
        return 400, {
            "ok": False,
            "errors": [f"invalid config: {e}"],
        }

    # ─── Resolve fixtures + run ───────────────────────────────────
    try:
        from buildemup.tests.validation import _c4_fixtures, _c5_fixtures
        plot = getattr(_c4_fixtures, plot_fixture_name)()
        brief_for_c4 = _c4_fixtures.make_brief(plot)
        floor_brief = getattr(_c5_fixtures, brief_fixture_name)()
    except Exception as e:
        _LOG.exception("fixture resolution failed")
        return 500, {
            "ok": False,
            "errors": [f"fixture resolution failed: {type(e).__name__}: {e}"],
        }

    orch = MasterOrchestrator(config)
    try:
        result = orch.run(
            plot=plot,
            brief_for_c4=brief_for_c4,
            floor_brief=floor_brief,
        )
    except Exception as e:
        _LOG.exception("orchestrator raised unexpectedly")
        return 500, {
            "ok": False,
            "errors": [
                f"orchestrator raised unexpectedly: {type(e).__name__}: {e}"
            ],
        }

    # ─── Build response ───────────────────────────────────────────
    response = {
        "ok": result.overall_status != PhaseStatus.ERROR,
        "overall_status": result.overall_status.value,
        "total_elapsed_ms": result.total_elapsed_ms,
        "summary": result.summary(),
        "config": {
            "vastu_tier": config.vastu_tier,
            "max_topology_mutations": config.max_topology_mutations,
            "enable_c11b_refinement": config.enable_c11b_refinement,
            "halt_on_first_failure": config.halt_on_first_failure,
        },
        "phases": [
            {
                "phase_id": p.phase_id,
                "status": p.status.value,
                "elapsed_ms": p.elapsed_ms,
                "error_class": p.error_class,
                "error_message": p.error_message,
                "skip_reason": p.skip_reason,
                "stub_reason": p.stub_reason,
                "notes": list(p.notes),
            }
            for p in result.phases
        ],
    }
    return 200, response
