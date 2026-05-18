"""POST /api/orchestrate — master orchestrator endpoint.

Accepts a JSON request describing the brief inputs, runs the full
MasterOrchestrator pipeline (S57: C4 → C14 as a real chain, with
opt-in real C11b evaluator; S59: C15 + C16 + C17 now also OK via
adapter glue), and returns a unified per-phase result summary.

Request shape (all fields optional unless noted):
  {
    "plot_fixture": "bangalore_40x60" | ... ,    # one of the named fixtures
    "brief_fixture": "medium_brief" | ... ,      # default: medium_brief
    "plot": { ... },                             # S59 #11 — free-form plot
    "brief": { ... },                            # S59 #11 — free-form floor brief
    "include_payloads": bool,                    # S59 #12 — serialize phase
                                                 #          payloads in response
    "max_collection_items": int,                 # S59 #12 — cap large tuples
    "config": {
      "vastu_tier": "OFF" | "PARTIAL" | "FULL",  # default PARTIAL
      "max_topology_mutations": int,             # default 4
      "enable_c11b_refinement": bool,            # default true
      "enable_full_structural_engine": bool,     # default true
      "enable_full_mutation_operators": bool,    # default false
      "use_real_c11b_evaluator": bool,           # default false
      "halt_on_first_failure": bool              # default false
    }
  }

Provide EITHER `plot_fixture` + `brief_fixture` (named fixture inputs)
OR `plot` + `brief` (free-form JSON). When both shapes are present the
free-form shape wins. If neither is present, defaults
(bangalore_40x60 + medium_brief) are used.

Response shape (status + metadata always; payload when requested):
  {
    "ok": bool,
    "overall_status": "ok|error|stub|skipped",
    "total_elapsed_ms": float,
    "summary": "MasterOrchestrator: ..." str,
    "config": { ... },
    "phases": [
      {
        "phase_id": "c04_plot_analysis",
        "status": "ok|error|stub|skipped",
        "elapsed_ms": float,
        "error_class": "" | "ValueError",
        "error_message": "" | "...",
        "skip_reason": "" | "...",
        "stub_reason": "" | "...",
        "notes": [str, ...],
        "payload": { ... }   # PRESENT iff include_payloads=true
      },
      ...
    ]
  }
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

from buildemup.orchestration import (
    MasterOrchestrator,
    MasterOrchestratorConfig,
    PhaseStatus,
    serialize_phase_payload,
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

    # ─── Resolve inputs: prefer free-form, fall back to fixtures ─────
    # S59 #11: free-form `plot` + `brief` JSON shapes take precedence
    # over `plot_fixture` + `brief_fixture` named fixtures when present.
    freeform_plot = payload.get("plot")
    freeform_brief = payload.get("brief")

    try:
        if freeform_plot is not None or freeform_brief is not None:
            from buildemup.orchestration.freeform_inputs import (
                build_plot_from_json,
                build_floor_brief_from_json,
                FreeformInputError,
                make_brief_for_c4,
            )
            try:
                plot = build_plot_from_json(freeform_plot or {})
                floor_brief = build_floor_brief_from_json(freeform_brief or {})
            except FreeformInputError as e:
                return 400, {"ok": False, "errors": [str(e)]}
            brief_for_c4 = make_brief_for_c4(plot)
        else:
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
            from buildemup.tests.validation import _c4_fixtures, _c5_fixtures
            plot = getattr(_c4_fixtures, plot_fixture_name)()
            brief_for_c4 = _c4_fixtures.make_brief(plot)
            floor_brief = getattr(_c5_fixtures, brief_fixture_name)()
    except Exception as e:  # noqa: BLE001
        _LOG.exception("input resolution failed")
        return 500, {
            "ok": False,
            "errors": [f"input resolution failed: {type(e).__name__}: {e}"],
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
            enable_full_structural_engine=bool(
                config_payload.get("enable_full_structural_engine", True)
            ),
            enable_full_mutation_operators=bool(
                config_payload.get("enable_full_mutation_operators", False)
            ),
            use_real_c11b_evaluator=bool(
                config_payload.get("use_real_c11b_evaluator", False)
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

    include_payloads = bool(payload.get("include_payloads", False))
    max_collection_items_raw = payload.get("max_collection_items")
    max_collection_items: int | None
    if max_collection_items_raw is None:
        max_collection_items = None
    else:
        try:
            max_collection_items = int(max_collection_items_raw)
        except (TypeError, ValueError):
            return 400, {
                "ok": False,
                "errors": [
                    "max_collection_items must be int when provided; "
                    f"got {max_collection_items_raw!r}"
                ],
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
            "enable_full_structural_engine": config.enable_full_structural_engine,
            "enable_full_mutation_operators": config.enable_full_mutation_operators,
            "use_real_c11b_evaluator": config.use_real_c11b_evaluator,
            "halt_on_first_failure": config.halt_on_first_failure,
        },
        "phases": [
            _serialize_phase(p, include_payloads, max_collection_items)
            for p in result.phases
        ],
    }
    return 200, response


def _serialize_phase(
    phase,
    include_payloads: bool,
    max_collection_items: int | None,
) -> Dict[str, Any]:
    """Convert one PhaseResult to its endpoint JSON shape (S59 #12)."""
    out: Dict[str, Any] = {
        "phase_id": phase.phase_id,
        "status": phase.status.value,
        "elapsed_ms": phase.elapsed_ms,
        "error_class": phase.error_class,
        "error_message": phase.error_message,
        "skip_reason": phase.skip_reason,
        "stub_reason": phase.stub_reason,
        "notes": list(phase.notes),
    }
    if include_payloads:
        try:
            out["payload"] = serialize_phase_payload(
                phase.phase_id,
                phase.payload,
                max_collection_items=max_collection_items,
            )
        except Exception as exc:  # noqa: BLE001
            # Serialization mustn't break the response — surface the
            # error inline and continue.
            _LOG.exception(
                "phase-payload serialization failed for %s", phase.phase_id,
            )
            out["payload"] = {
                "__serialization_error__": f"{type(exc).__name__}: {exc}",
            }
    return out
