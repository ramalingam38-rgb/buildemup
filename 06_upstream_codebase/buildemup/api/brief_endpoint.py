"""
BuildemUp† — Brief Capture API endpoint (Component 1 v0.1 / v0.9).

Exposes BriefCaptureEngine over HTTP. Accepts JSON POST matching the
BriefCaptureInput shape (with floors as list-of-dict that we translate
to FloorRequirement tuples), runs the engine, and returns:

  {
    "ok": bool,
    "trace_id": str,
    "rendered_explain": str,              # human-readable
    "brief_summary": { ... structured ... },
    "top_guidance": [ {severity, text, context, action_verb}, ... ],
    "risk_level": "LOW" / "MEDIUM" / "HIGH",
    "proceed_with_warnings": bool,
    "c7_preview_cost_lakhs": float | null,
    "errors": [str, ...] | null
  }

Plus (v0.9 Session B) two save/resume endpoints:

  POST /api/brief/save     - persist in-progress form, return resume token
  GET  /api/brief/resume   - fetch saved form by token

On validation errors (bad input), returns HTTP 400 with an errors list.
On engine errors (e.g., Component 7 unexpected failure), still returns
200 with a graceful output — this matches SPEC_v0.2 behaviour: Component 1
never refuses to produce a Brief.

DEPLOYMENT:
  Works with Python's built-in http.server. For Railway, a simple
  entrypoint (api/server.py) wires this to the HTTP handler.

†= placeholder name marker.
"""
from __future__ import annotations
import json
from typing import Any

from buildemup.components.c01_brief_capture import (
    BriefCaptureEngine, BriefCaptureInput,
)
from buildemup.components.c01.soft_guide_engine import (
    compute_action_steps,
)
from buildemup.domain import (
    FloorRequirement, RoomRequirement, FloorUse, RoomType,
)
from buildemup.utils.brief_storage import (
    BriefStorage, TokenNotFoundError, PayloadTooLargeError,
)


# ─────────────────────────────────────────────────────────────────────────
# Floor / room parsing from JSON
# ─────────────────────────────────────────────────────────────────────────
_FLOOR_USE_STRINGS = {fu.value: fu for fu in FloorUse}
_ROOM_TYPE_STRINGS = {rt.value: rt for rt in RoomType}


def _parse_room_requirement(payload: dict) -> RoomRequirement:
    """JSON → RoomRequirement domain object.

    Expected shape:
      { "room_type": "bedroom_master", "count": 1,
        "min_size_sqm": null, "preferred_size_sqm": 12.0 }
    """
    room_type_str = str(payload.get("room_type", "")).lower()
    if room_type_str not in _ROOM_TYPE_STRINGS:
        raise ValueError(
            f"Unknown room_type '{payload.get('room_type')}'. "
            f"Must be one of: {sorted(_ROOM_TYPE_STRINGS.keys())}"
        )
    return RoomRequirement(
        room_type=_ROOM_TYPE_STRINGS[room_type_str],
        count=int(payload.get("count", 1)),
        min_size_sqm=payload.get("min_size_sqm"),
        preferred_size_sqm=payload.get("preferred_size_sqm"),
    )


def _parse_floor_requirement(payload: dict) -> FloorRequirement:
    """JSON → FloorRequirement domain object.

    Expected shape:
      { "floor_number": 0, "floor_use": "residential",
        "rooms": [ {room_requirement}, ... ], "notes": "" }
    """
    floor_use_str = str(payload.get("floor_use", "residential")).lower()
    if floor_use_str not in _FLOOR_USE_STRINGS:
        raise ValueError(
            f"Unknown floor_use '{payload.get('floor_use')}'. "
            f"Must be one of: {sorted(_FLOOR_USE_STRINGS.keys())}"
        )
    rooms_payload = payload.get("rooms") or []
    rooms = tuple(_parse_room_requirement(r) for r in rooms_payload)
    return FloorRequirement(
        floor_number=int(payload["floor_number"]),
        floor_use=_FLOOR_USE_STRINGS[floor_use_str],
        rooms=rooms,
        notes=str(payload.get("notes", "")),
    )


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
def _get_city_disclosure(city: str) -> str:
    """Return the city DCR disclosure text or empty string.

    Surfaces v0.9 Session C disclosures (Mumbai SUBURBS default,
    Delhi Clause 4.4.3 verification advice). For cities still using
    NBC fallback, returns the fallback's disclosure (or empty if none).
    Returns "" on any error so callers don't crash on bad data.
    """
    try:
        from buildemup.utils.kb_rules_loader import (
            get_setback_rules_for_city,
        )
        rules = get_setback_rules_for_city(city)
        return rules.get("_disclosure_text", "") or ""
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────
# Main handler
# ─────────────────────────────────────────────────────────────────────────
def handle_brief_capture(request_body: bytes | str) -> tuple[int, dict]:
    """Handle POST /api/brief/capture.

    Args:
        request_body: raw request body as bytes or JSON string.

    Returns:
        (status_code, response_dict):
          - 400 on input validation error (bad JSON, bad enum, etc.)
          - 200 on success (or partial-success — engine failed gracefully)
          - 500 on unexpected orchestrator error (shouldn't happen)
    """
    # Parse JSON
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

    # Extract floors list → tuple of FloorRequirement
    floors_payload = payload.get("floors") or []
    try:
        floors = tuple(_parse_floor_requirement(f) for f in floors_payload)
    except (ValueError, KeyError, TypeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid floor structure: {str(e)[:120]}"],
        }

    # Additional requirements (strings)
    additional = tuple(payload.get("additional_requirements") or [])

    # Build BriefCaptureInput
    try:
        inp = BriefCaptureInput(
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
    except (KeyError, ValueError, TypeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Input validation failed: {str(e)[:150]}"],
        }

    # Execute engine
    try:
        engine = BriefCaptureEngine()
        output = engine.execute(inp)
    except Exception as e:
        # This shouldn't happen — Component 1 is designed to never refuse.
        # If it does, return 500 but tell the user enough to file a bug.
        return 500, {
            "ok": False,
            "errors": [
                f"Unexpected orchestrator error: {type(e).__name__}. "
                f"Please report with trace context."
            ],
            "technical_detail": str(e)[:300],
        }

    # Render explain() as text (client will display in a <pre> block)
    try:
        rendered = engine.explain(inp, output)
    except Exception as e:
        rendered = f"(explain() rendering failed: {type(e).__name__})"

    # ─────────────────────────────────────────────────────────────────────
    # S54-001 + S54-002 (May 2026) — Chain C1 → C2 → C3a-detect
    #
    # Per Architecture v1 §2.4 ("no silent override is the forbidden mode"),
    # the brief endpoint must NOT return only C1's optimistic view when
    # C2 would flag infeasibility or C3a would detect an extreme case.
    # We always run C2 + C3a-detect after C1, and surface their findings
    # in the response. If either fails, we degrade gracefully — the
    # original C1 surface stays intact and chain_status reports the gap.
    # ─────────────────────────────────────────────────────────────────────
    from buildemup.components.c02.orchestrator import run_feasibility
    from buildemup.components.c02.renderer import (
        render_text_summary as _render_feasibility_summary,
        render_json as _render_feasibility_json,
    )
    from buildemup.components.c03a.detector import ExtremeCaseDetector

    feasibility_analysis = None
    feasibility_summary_text: str | None = None
    feasibility_json: dict | None = None
    extreme_cases_dicts: list[dict] = []
    chain_status = {"c1": "ok", "c2": "not_run", "c3a_detect": "not_run"}

    try:
        feasibility_analysis = run_feasibility(
            output.brief,
            c7_cost_estimate=output.c7_preview_cost,
            feasibility_input=None,  # NOT_ASKED defaults
        )
        chain_status["c2"] = "ok"
    except Exception as e:
        chain_status["c2"] = f"error:{type(e).__name__}"

    if feasibility_analysis is not None:
        try:
            feasibility_summary_text = _render_feasibility_summary(
                feasibility_analysis, output.brief,
            )
            feasibility_json = _render_feasibility_json(
                feasibility_analysis
            )
        except Exception as e:
            chain_status["c2"] = f"render_error:{type(e).__name__}"
            feasibility_summary_text = None
            feasibility_json = None

        try:
            extreme_cases = ExtremeCaseDetector.detect(
                feasibility_analysis, output.brief,
            )
            extreme_cases_dicts = [ec.to_dict() for ec in extreme_cases]
            chain_status["c3a_detect"] = (
                "ok" if extreme_cases_dicts else "ok_no_cases"
            )
        except Exception as e:
            chain_status["c3a_detect"] = f"error:{type(e).__name__}"
            extreme_cases_dicts = []

    # Combined human-readable text: C1 explain + C2 summary + C3a section.
    # Frontend renders this in a <pre> block instead of C1's rendered_explain.
    combined_parts: list[str] = [rendered]
    if feasibility_summary_text:
        combined_parts.append("")
        combined_parts.append("=" * 70)
        combined_parts.append(
            "FEASIBILITY CHECK — Component 2 (auto-run after Brief Capture)"
        )
        combined_parts.append("=" * 70)
        combined_parts.append(feasibility_summary_text)
    if extreme_cases_dicts:
        combined_parts.append("")
        combined_parts.append("=" * 70)
        combined_parts.append(
            f"⚠ EXTREME CASE(S) DETECTED — {len(extreme_cases_dicts)} item(s)"
        )
        combined_parts.append("=" * 70)
        combined_parts.append(
            "Component 3a flagged the following blocker(s). Visit the "
            "extreme-case negotiation flow to resolve them before "
            "proceeding to layout generation:"
        )
        for ec in extreme_cases_dicts:
            combined_parts.append("")
            combined_parts.append(
                f"[{ec['case_id']}] ({ec['category']})"
            )
            combined_parts.append(f"  {ec['framing_line']}")
            combined_parts.append(f"  {ec['user_facing_message']}")
    combined_rendered_explain = "\n".join(combined_parts)

    # Build structured response
    response = {
        "ok": True,
        "trace_id": output.trace_id,
        "rendered_explain": rendered,
        # S54-001+002: combined honest view (C1 + C2 + C3a)
        "combined_rendered_explain": combined_rendered_explain,
        "feasibility_summary_text": feasibility_summary_text,
        "feasibility_data": feasibility_json,
        "extreme_cases": extreme_cases_dicts,
        "chain_status": chain_status,
        "proceed_with_warnings": output.proceed_with_warnings,
        "risk_level": output.risk_level,
        # v0.9.2 Drawback #3: plain-language label tail so clients don't
        # render "LOW" alone (tested as "safe" by users)
        "risk_label_with_context": {
            "LOW": "LOW (minor issues, plan looks sound)",
            "MEDIUM": "MEDIUM (review recommended — concerns worth addressing)",
            "HIGH": "HIGH (likely design changes needed before proceeding)",
        }.get(output.risk_level, output.risk_level),
        # v0.9.2 Drawback #4: surface the most critical driver as a single
        # field so clients can render it prominently. None for LOW risk.
        "biggest_issue": (
            output.risk_drivers[0]
            if output.risk_level in ("MEDIUM", "HIGH")
            and output.risk_drivers
            else None
        ),
        # v0.9.1 Drawback #8: explain WHY risk_level is what it is
        "risk_drivers": list(output.risk_drivers),
        # v0.9.1 Drawback #14: position this output in the build journey
        "roadmap_position": {
            "current_step": 1,
            "current_name": "Brief Capture",
            "total_steps": 6,
            "steps_ahead": [
                {"n": 2, "name": "Feasibility check"},
                {"n": 3, "name": "Layout generation"},
                {"n": 4, "name": "Structural design"},
                {"n": 5, "name": "MEP & finishes"},
                {"n": 6, "name": "Procurement & contractor selection"},
            ],
            # v0.9.2 Drawback #6: explicit next-step CTA
            "next_step_cta": (
                "Next: Component 2 (Feasibility) will check whether your "
                "plan is actually possible on this plot."
            ),
            "disclaimer": (
                "This is step 1 of 6 — directional planning input only, "
                "not a final design or quote."
            ),
        },
        # v0.9.2 Drawback #13: explicit scope caveat — system does NOT
        # replace architect-led layout, structural drawings, or municipal
        # plan approval.
        "scope_caveat": (
            "This output does NOT replace architect-led layout design, "
            "structural engineering drawings, or municipal plan approval. "
            "It is a planning aid for early-stage decisions only."
        ),
        # v0.9.2 Drawback #15: surface the engineering-model dependency
        "powered_by": {
            "structural_cost_engine": "Component 7 (NBC + IS 456/875/1893)",
            "city_rates_source": "City-specific material rates (v0.9 Sessions C+D)",
        },
        # v0.9.2 Drawback #16: action steps for "what should you do now?"
        # Mirrors the explain() WHAT SHOULD YOU DO NOW? section so clients
        # can render the same numbered list in their own UI.
        "action_steps": list(compute_action_steps(
            output.brief.soft_guidance, output.risk_level
        )),
        # v0.9.2 Drawback #16: numbered action sequence for "what to do now"
        "action_steps": list(compute_action_steps(
            output.brief.soft_guidance, output.risk_level
        )),
        # Deprecated alias retained for one release — clients should
        # migrate to risk_level which is the meaningful signal.
        "ready_for_downstream": output.risk_level != "HIGH",
        "top_guidance": [
            {
                "severity": m.severity.value,
                "text": m.text,
                "context": m.context,
                "action_verb": m.action_verb,
            }
            for m in output.top_guidance
        ],
        "guidance_counts_by_severity": {
            "strong_concern": sum(
                1 for m in output.soft_guidance
                if m.severity.value == "strong_concern"
            ),
            "concern": sum(
                1 for m in output.soft_guidance
                if m.severity.value == "concern"
            ),
            "info": sum(
                1 for m in output.soft_guidance
                if m.severity.value == "info"
            ),
        },
        # v0.9.1 Drawback #9: messages grouped by category for UI sectioning
        "soft_guidance_by_category": {
            category: [
                {
                    "severity": m.severity.value,
                    "text": m.text,
                    "context": m.context,
                    "action_verb": m.action_verb,
                }
                for m in msgs
            ]
            for category, msgs in output.soft_guidance_by_category.items()
        },
        "brief_summary": {
            "city": output.brief.plot.city,
            "plot_width_m": output.brief.plot.width_m,
            "plot_depth_m": output.brief.plot.depth_m,
            "plot_type": output.brief.plot.plot_type.value,
            "plot_facing": output.brief.plot.facing.value,
            "plot_area_sqm": output.brief.plot.area_sqm,
            "plot_area_sqft": output.brief.plot.area_sqft,
            "floor_count": len(output.brief.floors),
            "floors_above_ground": output.brief.total_floors_above_ground,
            "has_stilt_parking": output.brief.has_stilt_parking,
            "total_built_area_sqft": output.total_built_area_sqft,
            # Envelope + net usable (Drawback #3 v0.9)
            "gross_envelope_sqm": round(output.gross_envelope_sqm, 1),
            "net_usable_sqm": round(output.net_usable_sqm, 1),
            # v0.9.1 Drawback #3: net usable as range, not single point
            "net_usable_low_sqm": round(output.net_usable_low_sqm, 1),
            "net_usable_high_sqm": round(output.net_usable_high_sqm, 1),
            "envelope_width_m": output.envelope_width_m,
            "envelope_depth_m": output.envelope_depth_m,
            # Circulation factor applied (Drawback #5 v0.9)
            "circulation_factor_applied": output.circulation_factor_applied,
            "circulation_size_label": output.circulation_size_label,
            "budget_min_lakhs": output.brief.budget_range.min_lakhs,
            "budget_max_lakhs": output.brief.budget_range.max_lakhs,
            "vastu_preference": output.brief.vastu_preference.value,
            "compliance": {
                "is_setback_compliant": output.compliance_summary.is_setback_compliant,
                "source_authority": output.compliance_summary.source_authority,
                "violations": list(output.compliance_summary.setback_violations),
                "dcr_disclosure": _get_city_disclosure(output.brief.plot.city),
            },
            "soft_guidance_count": len(output.soft_guidance),
            "assumptions_count": len(output.assumptions_used),
        },
        "c7_preview_cost_lakhs": (
            round(output.c7_preview_cost.exact_value / 100_000, 2)
            if output.c7_preview_cost else None
        ),
        "c7_preview_cost_range_lakhs": (
            [
                round(output.c7_preview_cost.range_min / 100_000, 2),
                round(output.c7_preview_cost.range_max / 100_000, 2),
            ]
            if output.c7_preview_cost else None
        ),
        # v0.9.1 Drawback #2: cited industry breakdown replaces ×1.5-2.0
        "all_in_cost_estimate_lakhs": (
            {
                "low": round(output.c7_preview_cost.range_min / 100_000 * 2.0, 1),
                "typical": round(output.c7_preview_cost.exact_value / 100_000 * 2.5, 1),
                "high": round(output.c7_preview_cost.range_max / 100_000 * 3.0, 1),
                "structural_share_typical": 0.40,
                "breakdown_pct": {
                    "structure": 40,
                    "finishing": 25,
                    "mep": 15,
                    "interior": 12,
                    "miscellaneous": 8,
                },
                "source": (
                    "Industry typical breakdown (AECORD 2026 + NBC industry "
                    "guides). Premium finishes shift structure share toward "
                    "30-35%; lean finishes can push to 50%+. Range observed, "
                    "not guaranteed."
                ),
                "disclaimer": (
                    "Do not treat as a quote — directional planning estimate."
                ),
            }
            if output.c7_preview_cost else None
        ),
        "kb_versions": output.kb_versions,
        "resume_token": output.resume_token,
    }

    return 200, response


# ─────────────────────────────────────────────────────────────────────────
# Vastu items endpoint (GET /api/vastu/partial-items)
# ─────────────────────────────────────────────────────────────────────────
def handle_vastu_partial_items() -> tuple[int, dict]:
    """Return the 7 VASTU_PARTIAL_ITEMS for form display.

    Per SPEC_v0.2 Section 7.2: the user must see exactly what PARTIAL
    vastu includes. This endpoint returns the canonical list so the
    frontend shows the same 7 items as the backend applies.
    """
    from buildemup.domain import VASTU_PARTIAL_ITEMS
    return 200, {
        "ok": True,
        "partial_items": list(VASTU_PARTIAL_ITEMS),
        "count": len(VASTU_PARTIAL_ITEMS),
    }


# ─────────────────────────────────────────────────────────────────────────
# v0.9 Session B — Server-side save/resume via SQLite
# ─────────────────────────────────────────────────────────────────────────
_STORAGE_SINGLETON: BriefStorage | None = None


def _get_storage() -> BriefStorage:
    """Lazy-initialize a process-wide BriefStorage singleton.

    Connections are opened per-operation, so the singleton is cheap to
    hold. We use a singleton mainly so tests can substitute a custom
    path via the env var before the first call.
    """
    global _STORAGE_SINGLETON
    if _STORAGE_SINGLETON is None:
        _STORAGE_SINGLETON = BriefStorage()
    return _STORAGE_SINGLETON


def _reset_storage_singleton() -> None:
    """Test helper — forces a re-init on next _get_storage() call."""
    global _STORAGE_SINGLETON
    _STORAGE_SINGLETON = None


def handle_brief_save(
    request_body: bytes | str, host_base_url: str = "",
) -> tuple[int, dict]:
    """Handle POST /api/brief/save.

    Body: arbitrary JSON dict (the in-progress form state).
    Optionally: {"existing_token": "..."} alongside the payload to update
    in place (so repeat-saves share the same resume URL).

    Args:
        request_body: raw JSON body
        host_base_url: e.g., "https://build-ease-ai.up.railway.app" —
            used to construct the resume URL. If empty, returns just
            the query-string fragment.

    Returns:
        (status, body)
        - 400 if body is bad JSON or payload too large
        - 200 on success, returns {token, resume_url, expires_at_utc,
          ephemeral_storage_warning}
    """
    try:
        if isinstance(request_body, bytes):
            body_str = request_body.decode("utf-8")
        else:
            body_str = request_body
        outer = json.loads(body_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return 400, {
            "ok": False,
            "errors": [f"Invalid JSON: {str(e)[:120]}"],
        }

    if not isinstance(outer, dict):
        return 400, {
            "ok": False,
            "errors": ["Body must be a JSON object"],
        }

    # Extract optional existing_token; everything else is the payload
    existing_token = outer.pop("existing_token", None)
    payload = outer

    try:
        token, expires_at = _get_storage().save(
            payload, existing_token=existing_token,
        )
    except PayloadTooLargeError as e:
        return 400, {"ok": False, "errors": [str(e)]}
    except Exception as e:
        return 500, {
            "ok": False,
            "errors": [f"Storage error: {type(e).__name__}"],
        }

    import datetime as _dt
    expires_iso = _dt.datetime.utcfromtimestamp(expires_at).isoformat() + "Z"

    if host_base_url:
        resume_url = f"{host_base_url.rstrip('/')}/?resume={token}"
    else:
        resume_url = f"/?resume={token}"

    return 200, {
        "ok": True,
        "token": token,
        "resume_url": resume_url,
        "expires_at_utc": expires_iso,
        "ephemeral_storage_warning": (
            "On hobby/free tiers the server filesystem is ephemeral. "
            "Your brief may be lost if the service restarts. For "
            "production, use a persistent-volume tier or external DB."
        ),
    }


def handle_brief_resume(token: str) -> tuple[int, dict]:
    """Handle GET /api/brief/resume?token=X.

    Returns:
        (status, body)
        - 404 if token missing/invalid/expired
        - 200 {ok: True, payload: <original dict>, saved_at_utc, ...}
    """
    if not token:
        return 400, {
            "ok": False,
            "errors": ["Missing 'token' query parameter"],
        }

    try:
        payload = _get_storage().resume(token)
    except TokenNotFoundError as e:
        return 404, {"ok": False, "errors": [str(e)]}
    except Exception as e:
        return 500, {
            "ok": False,
            "errors": [f"Storage error: {type(e).__name__}"],
        }

    return 200, {
        "ok": True,
        "token": token,
        "payload": payload,
    }
