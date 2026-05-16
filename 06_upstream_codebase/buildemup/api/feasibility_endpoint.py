"""
BuildemUp — Feasibility API endpoint (Component 2 v0.1).

Exposes the C2 feasibility orchestrator over HTTP. Accepts the same JSON
payload as /api/brief/capture, plus optional FeasibilityInput fields, and
returns a complete DesignGapAnalysis as JSON + rendered text.

Endpoint:
  POST /api/feasibility/run

Request payload:
  {
    ...all C1 BriefCaptureInput fields (plot_width_m, plot_depth_m, etc.)...,
    "feasibility_input": {
      "soil_type": {"value": "laterite", "source": "user_provided_verified"},
      "water_table_depth_m": {"value": 8.0, "source": "user_provided_unverified"},
      ...etc, all 6 optional FeasibilityInput fields...
    },
    // Legacy positional kwargs (Session B placeholders):
    "distance_from_electric_line_m": 5.0,
    "electric_line_type": "lt",
    "distance_from_water_course_m": 50.0,
    "has_water_course_within_30m": false
  }

Response (HTTP 200):
  {
    "ok": true,
    "trace_id": "<C1 trace id>",
    "feasibility_summary_text": "...20-line CLI summary...",
    "feasibility_full_text": "...full 100+ line report...",
    "feasibility_data": { ...full DesignGapAnalysis JSON... },
    "brief_summary": { ... C1 brief summary for reference ... },
    "errors": null
  }

On bad JSON / bad input:
  HTTP 400, {"ok": false, "errors": ["Invalid JSON: ..."]}

On unexpected orchestrator error:
  HTTP 500, {"ok": false, "errors": [...], "technical_detail": "..."}

DEPLOYMENT:
  Wired into api/server.py via add of the new POST route.
  Works with stdlib http.server — no Flask/FastAPI dependency.
"""
from __future__ import annotations
import json
from typing import Any

from buildemup.components.c01_brief_capture import (
    BriefCaptureEngine, BriefCaptureInput,
)
from buildemup.components.c02.feasibility_input import (
    FeasibilityInput, InputField, FieldSource,
)
from buildemup.components.c02.orchestrator import run_feasibility
from buildemup.components.c02.renderer import (
    render_text_summary, render_text_full, render_json,
)

# Reuse C1's floor/room parsers (already module-level + tested)
from buildemup.api.brief_endpoint import (
    _parse_floor_requirement,
)


# ─── FeasibilityInput field parsing ───────────────────────────────────

def _parse_input_field(field_payload: Any, field_name: str,
                       expected_type: type) -> InputField:
    """Parse a single FeasibilityInput field from JSON.

    Accepts shape: {"value": <typed>, "source": "<source-string>"}
    or shape: null / missing → defaults to NOT_ASKED InputField.

    Raises ValueError for malformed input.
    """
    if field_payload is None:
        return InputField.not_asked(field_name=field_name)

    if not isinstance(field_payload, dict):
        raise ValueError(
            f"feasibility_input.{field_name} must be an object with "
            f"'value' and 'source' keys, got {type(field_payload).__name__}"
        )

    source_str = field_payload.get("source", "")
    try:
        source = FieldSource(source_str)
    except ValueError:
        raise ValueError(
            f"feasibility_input.{field_name}.source: '{source_str}' is "
            f"not a valid FieldSource. Must be one of: "
            f"{[s.value for s in FieldSource]}"
        )

    value = field_payload.get("value")

    # Source/value invariants — match InputField __post_init__
    if source in (FieldSource.USER_PROVIDED_VERIFIED,
                  FieldSource.USER_PROVIDED_UNVERIFIED):
        if value is None:
            raise ValueError(
                f"feasibility_input.{field_name}: source={source.value} "
                f"requires a non-None value."
            )
        # Coerce to expected type
        try:
            value = expected_type(value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"feasibility_input.{field_name}.value: cannot coerce "
                f"{value!r} to {expected_type.__name__}: {e}"
            )
    elif source in (FieldSource.USER_DOESNT_KNOW, FieldSource.NOT_ASKED):
        if value is not None:
            raise ValueError(
                f"feasibility_input.{field_name}: source={source.value} "
                f"requires value=null, got {value!r}"
            )

    return InputField(
        value=value,
        source=source,
        field_name=field_name,
    )


def _parse_feasibility_input(brief, payload: dict | None) -> FeasibilityInput:
    """Parse the optional 'feasibility_input' section of the request payload.

    If the section is missing or empty, returns FeasibilityInput with all
    fields defaulted to NOT_ASKED.
    """
    if not payload:
        return FeasibilityInput(brief=brief)

    if not isinstance(payload, dict):
        raise ValueError(
            f"feasibility_input must be an object, got "
            f"{type(payload).__name__}"
        )

    return FeasibilityInput(
        brief=brief,
        soil_type=_parse_input_field(
            payload.get("soil_type"), "soil_type", str,
        ),
        water_table_depth_m=_parse_input_field(
            payload.get("water_table_depth_m"), "water_table_depth_m", float,
        ),
        distance_from_electric_line_m=_parse_input_field(
            payload.get("distance_from_electric_line_m"),
            "distance_from_electric_line_m", float,
        ),
        electric_line_type=_parse_input_field(
            payload.get("electric_line_type"), "electric_line_type", str,
        ),
        distance_from_water_course_m=_parse_input_field(
            payload.get("distance_from_water_course_m"),
            "distance_from_water_course_m", float,
        ),
        has_water_course_within_30m=_parse_input_field(
            payload.get("has_water_course_within_30m"),
            "has_water_course_within_30m", bool,
        ),
    )


# ─── BriefCaptureInput construction (replicated from brief_endpoint) ──
# Duplicated rather than refactored to avoid any risk of breaking the
# 220+ existing C1 tests. If both endpoints diverge, refactor later.

def _build_capture_input(payload: dict, floors) -> BriefCaptureInput:
    """Construct BriefCaptureInput from request payload + parsed floors.

    Raises KeyError/ValueError/TypeError on bad input — caller maps to
    HTTP 400.
    """
    additional = tuple(payload.get("additional_requirements") or [])
    return BriefCaptureInput(
        plot_width_m=float(payload["plot_width_m"]),
        plot_depth_m=float(payload["plot_depth_m"]),
        plot_facing=str(payload["plot_facing"]),
        city=str(payload["city"]),
        road_width_m=float(payload["road_width_m"]),
        plot_type=str(payload.get("plot_type", "detached")),
        corner_plot=bool(payload.get("corner_plot", False)),
        second_road_width_m=(
            float(payload["second_road_width_m"])
            if payload.get("second_road_width_m") is not None
            else None
        ),
        shared_side=payload.get("shared_side"),
        user_setback_front_m=float(payload.get("user_setback_front_m", 1.5)),
        user_setback_rear_m=float(payload.get("user_setback_rear_m", 1.5)),
        user_setback_side_left_m=float(payload.get("user_setback_side_left_m", 1.5)),
        user_setback_side_right_m=float(payload.get("user_setback_side_right_m", 1.5)),
        floors=floors,
        budget_min_lakhs=int(payload.get("budget_min_lakhs", 15)),
        budget_max_lakhs=int(payload.get("budget_max_lakhs", 25)),
        additional_requirements=additional,
        soil_type_known=payload.get("soil_type_known"),
        vastu_preference=str(payload.get("vastu_preference", "off")),
        user_email=payload.get("user_email"),
        user_phone=payload.get("user_phone"),
        resume_token=payload.get("resume_token"),
    )


# ─── Main handler ─────────────────────────────────────────────────────

def handle_feasibility_run(request_body: bytes | str) -> tuple[int, dict]:
    """Handle POST /api/feasibility/run.

    Args:
        request_body: raw request body as bytes or JSON string.

    Returns:
        (status_code, response_dict) — see module docstring for shape.
    """
    # ── Parse JSON ────────────────────────────────────────────────────
    try:
        if isinstance(request_body, bytes):
            body_str = request_body.decode("utf-8")
        else:
            body_str = request_body
        payload: dict[str, Any] = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid JSON: {str(e)[:120]}"],
        }
    if not isinstance(payload, dict):
        return 400, {
            "ok": False,
            "errors": [
                f"Request body must be a JSON object, got "
                f"{type(payload).__name__}"
            ],
        }

    # ── Parse floors ──────────────────────────────────────────────────
    floors_payload = payload.get("floors") or []
    try:
        floors = tuple(_parse_floor_requirement(f) for f in floors_payload)
    except (ValueError, KeyError, TypeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid floor structure: {str(e)[:120]}"],
        }

    # ── Build BriefCaptureInput ───────────────────────────────────────
    try:
        capture_input = _build_capture_input(payload, floors)
    except (KeyError, ValueError, TypeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Input validation failed: {str(e)[:150]}"],
        }

    # ── Run C1 ─────────────────────────────────────────────────────────
    try:
        engine = BriefCaptureEngine()
        c1_output = engine.execute(capture_input)
    except ValueError as e:
        # ValueError from C1 = user input validation (e.g., unsupported city,
        # invalid plot dimensions). Return 400 with the message visible.
        return 400, {
            "ok": False,
            "errors": [f"Input validation failed: {str(e)[:200]}"],
        }
    except Exception as e:
        # Other exceptions = unexpected code path. 500 with technical detail.
        return 500, {
            "ok": False,
            "errors": [
                f"C1 brief capture failed: {type(e).__name__}. "
                f"Please report with trace context."
            ],
            "technical_detail": str(e)[:300],
        }

    brief = c1_output.brief

    # ── Parse FeasibilityInput section + legacy kwargs ────────────────
    try:
        feasibility_input = _parse_feasibility_input(
            brief, payload.get("feasibility_input"),
        )
    except ValueError as e:
        return 400, {
            "ok": False,
            "errors": [f"feasibility_input parsing failed: {str(e)[:200]}"],
        }

    # Legacy kwargs from Session B (electric line + water course)
    # Will be unified into FeasibilityInput in v0.2
    legacy_kwargs = {}
    for legacy_field, expected in [
        ("distance_from_electric_line_m", float),
        ("electric_line_type", str),
        ("distance_from_water_course_m", float),
        ("has_water_course_within_30m", bool),
    ]:
        if legacy_field in payload and payload[legacy_field] is not None:
            try:
                legacy_kwargs[legacy_field] = expected(payload[legacy_field])
            except (ValueError, TypeError) as e:
                return 400, {
                    "ok": False,
                    "errors": [
                        f"Invalid {legacy_field}: cannot coerce to "
                        f"{expected.__name__}"
                    ],
                }

    # ── Run C2 ─────────────────────────────────────────────────────────
    try:
        analysis = run_feasibility(
            brief,
            c7_cost_estimate=c1_output.c7_preview_cost,
            feasibility_input=feasibility_input,
            **legacy_kwargs,
        )
    except Exception as e:
        return 500, {
            "ok": False,
            "errors": [
                f"C2 feasibility orchestrator failed: "
                f"{type(e).__name__}."
            ],
            "technical_detail": str(e)[:300],
        }

    # ── Render outputs ────────────────────────────────────────────────
    try:
        summary_text = render_text_summary(analysis, brief)
        full_text = render_text_full(analysis, brief)
        json_data = render_json(analysis)
    except Exception as e:
        return 500, {
            "ok": False,
            "errors": [
                f"Renderer failed: {type(e).__name__}. "
                f"This indicates a bug — please report."
            ],
            "technical_detail": str(e)[:300],
        }

    # ── Build brief summary for reference ─────────────────────────────
    brief_summary = {
        "trace_id": c1_output.trace_id,
        "city": brief.plot.city,
        "plot_area_sqm": round(brief.plot.area_sqm, 1),
        "plot_facing": brief.plot.facing.value,
        "floor_count": len(brief.floors),
        "budget_min_lakhs": brief.budget_range.min_lakhs,
        "budget_max_lakhs": brief.budget_range.max_lakhs,
        "risk_level": c1_output.risk_level,
    }

    return 200, {
        "ok": True,
        "trace_id": c1_output.trace_id,
        "feasibility_summary_text": summary_text,
        "feasibility_full_text": full_text,
        "feasibility_data": json_data,
        "brief_summary": brief_summary,
        "errors": None,
    }
