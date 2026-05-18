"""POST /api/quote/compare — C17 quote-comparison endpoint (S59 follow-up #9).

C17 (`run_c17`) takes a parsed contractor quote + a project BOQ + a
rate provider and produces a QuoteComparisonReport. The original
master orchestrator does NOT invoke C17 because it has no quote to
compare; the homeowner uploads a quote separately, and this endpoint
handles that flow.

Request shape (JSON):
  {
    "project_id": "proj-abc",                  # caller-supplied identifier
    "jurisdiction_profile_id": "tn_cdbr_2019", # default tn_cdbr_2019
    "declared_domain_scope": "residential_v1",  # default residential_v1
    "locality_label": "Chennai-wide",           # default Chennai-wide
    "parsed_quote": {
        "parsed_quote_id": "uuid",
        "contractor_label": "Anand Constructions",
        "quote_date_iso": "2026-05-18",
        "quote_total_inr": 3200000.0,
        "parsed_quote_signature": "sha256...",
        "line_items": [
          {"line_id": "L001", "raw_label": "Cement OPC 53 (50kg bag)",
           "quantity": 200.0, "unit": "bag", "rate": 410.0,
           "total": 82000.0, "is_lump_sum_hint": false}
        ]
    },
    "cost_lines": [
        {"item_id": "C7-RCC-CEMENT-001", "label": "Cement OPC 53",
         "category": "structural_rcc", "quantity": 200.0, "unit": "bag",
         "rate_category": "structural_rcc", "rate_key": "cement_opc_53",
         "severity": "critical"}
    ],
    "include_payload": false
  }

Response shape:
  {
    "ok": true,
    "report": { ... QuoteComparisonReport serialized ... | summary only ... },
    "summary": {
        "matched_lines": int, "gaps": int, "unmatched_lines": int,
        "lump_sums": int, "quote_total_inr": float, "delta_pct": float,
        "report_confidence_tier": "..."
    }
  }

On request errors → 400; on RateProvider / C17 exceptions → 500 with
error class + message.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any, Dict, Iterable, Tuple


_LOG = logging.getLogger(__name__)


# Duck-typed cost-line shim — C17's upstream_adapter reads attributes
# off this with getattr(); we don't need to subclass the Protocol.
@dataclasses.dataclass(frozen=True)
class _CostLineShim:
    item_id:        str
    label:          str
    category:       str
    quantity:       float
    unit:           str
    rate_category:  str
    rate_key:       str
    severity:       str


def _coerce_cost_lines(raw: Any) -> tuple[_CostLineShim, ...]:
    if not isinstance(raw, list):
        raise ValueError(
            f"cost_lines must be a list; got {type(raw).__name__}"
        )
    out: list[_CostLineShim] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(
                f"cost_lines[{i}] must be an object; got "
                f"{type(item).__name__}"
            )
        try:
            out.append(_CostLineShim(
                item_id=str(item["item_id"]),
                label=str(item["label"]),
                category=str(item.get("category", "miscellaneous")),
                quantity=float(item["quantity"]),
                unit=str(item.get("unit", "")),
                rate_category=str(item["rate_category"]),
                rate_key=str(item["rate_key"]),
                severity=str(item.get("severity", "important")),
            ))
        except KeyError as e:
            raise ValueError(
                f"cost_lines[{i}] missing required field: {e}"
            ) from e
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"cost_lines[{i}] field coercion failed: {e}"
            ) from e
    return tuple(out)


def _build_parsed_quote(raw: Any):
    """Build a ParsedQuote from a JSON-style dict."""
    from buildemup.components.c17.contracts import (
        ParsedQuote,
        ParsedQuoteLine,
    )
    if not isinstance(raw, dict):
        raise ValueError(
            f"parsed_quote must be an object; got {type(raw).__name__}"
        )

    line_items_raw = raw.get("line_items", [])
    if not isinstance(line_items_raw, list):
        raise ValueError(
            f"parsed_quote.line_items must be a list; got "
            f"{type(line_items_raw).__name__}"
        )

    line_items = []
    for i, li in enumerate(line_items_raw):
        if not isinstance(li, dict):
            raise ValueError(
                f"parsed_quote.line_items[{i}] must be an object."
            )
        try:
            line_items.append(ParsedQuoteLine(
                line_id=str(li["line_id"]),
                raw_label=str(li["raw_label"]),
                quantity=(
                    float(li["quantity"]) if li.get("quantity") is not None
                    else None
                ),
                unit=str(li.get("unit", "")),
                rate=(
                    float(li["rate"]) if li.get("rate") is not None else None
                ),
                total=float(li["total"]),
                is_lump_sum_hint=bool(li.get("is_lump_sum_hint", False)),
                raw_notes=str(li.get("raw_notes", "")),
            ))
        except KeyError as e:
            raise ValueError(
                f"parsed_quote.line_items[{i}] missing required field: {e}"
            ) from e

    try:
        # We auto-compute the signature so callers don't have to
        # implement C17's canonicalization themselves. The signature
        # field is required by the dataclass; we pass empty string
        # initially, then re-build with the computed value.
        provisional = ParsedQuote(
            parsed_quote_id=str(raw["parsed_quote_id"]),
            contractor_label=str(raw["contractor_label"]),
            quote_date_iso=str(raw["quote_date_iso"]),
            quote_total_inr=float(raw["quote_total_inr"]),
            line_items=tuple(line_items),
            parsed_quote_signature="",
            parser_hint_decomposition_style=raw.get(
                "parser_hint_decomposition_style"
            ),
        )
    except KeyError as e:
        raise ValueError(
            f"parsed_quote missing required field: {e}"
        ) from e

    from buildemup.components.c17.cache_keys import (
        compute_parsed_quote_signature,
    )
    sig = compute_parsed_quote_signature(provisional)
    return ParsedQuote(
        parsed_quote_id=provisional.parsed_quote_id,
        contractor_label=provisional.contractor_label,
        quote_date_iso=provisional.quote_date_iso,
        quote_total_inr=provisional.quote_total_inr,
        line_items=provisional.line_items,
        parsed_quote_signature=sig,
        parser_hint_decomposition_style=provisional.parser_hint_decomposition_style,
    )


def handle_quote_compare(body: bytes) -> Tuple[int, Dict[str, Any]]:
    """POST /api/quote/compare handler.

    Returns (status_code, response_dict) for the stdlib server's
    _send_json helper.
    """
    # ─── Parse + validate input ───────────────────────────────────
    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return 400, {"ok": False, "errors": [f"invalid JSON: {e}"]}

    if not isinstance(payload, dict):
        return 400, {"ok": False, "errors": ["request body must be an object"]}

    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id.strip():
        return 400, {
            "ok": False,
            "errors": ["project_id is required (non-empty string)"],
        }

    jurisdiction = payload.get("jurisdiction_profile_id", "tn_cdbr_2019")
    domain_scope = payload.get("declared_domain_scope", "residential_v1")
    locality_label = payload.get("locality_label", "Chennai-wide")

    try:
        parsed_quote = _build_parsed_quote(payload.get("parsed_quote"))
        cost_lines = _coerce_cost_lines(payload.get("cost_lines", []))
    except ValueError as e:
        return 400, {"ok": False, "errors": [str(e)]}

    include_payload = bool(payload.get("include_payload", False))

    # ─── Run C17 ──────────────────────────────────────────────────
    try:
        from buildemup.components.c17.orchestrator import run_c17
        from buildemup.components.c17.rates.chennai_rate_provider import (
            ChennaiRateProvider,
        )
        rate_provider = ChennaiRateProvider()
        report = run_c17(
            parsed_quote=parsed_quote,
            cost_lines=cost_lines,
            rate_provider=rate_provider,
            project_id=project_id,
            jurisdiction_profile_id=jurisdiction,
            declared_domain_scope=domain_scope,
            locality_label=locality_label,
        )
    except Exception as e:  # noqa: BLE001
        _LOG.exception("C17 quote-compare failed")
        return 500, {
            "ok": False,
            "errors": [
                f"C17 quote-compare failed: {type(e).__name__}: {e}"
            ],
        }

    # ─── Build response ───────────────────────────────────────────
    response: Dict[str, Any] = {
        "ok": True,
        "summary": {
            "matched_lines": len(report.matched_lines),
            "gaps_in_quote": len(report.missing_from_quote),
            "unmatched_quote_lines": len(report.unmatched_quote_lines),
            "lump_sum_indicators": len(report.lump_sum_indicators),
            "quote_total_inr": float(report.total_comparison.quote_total.value),
            "delta_pct": float(report.total_comparison.delta_pct.value),
            "report_confidence_tier": report.report_confidence.overall_report_tier,
            "decomposition_style":
                report.decomposition_acknowledgment.detected_decomposition_style,
            "advisory_flags": len(report.advisory_flags),
        },
        "signatures": {
            "canonical_replay_signature": report.canonical_replay_signature,
            "presentation_signature": report.presentation_signature,
            "schema_descriptor_digest": report.schema_descriptor_digest,
        },
    }

    if include_payload:
        from buildemup.orchestration.phase_payloads import (
            serialize_phase_payload,
        )
        response["report"] = serialize_phase_payload(
            "c17_quote_comparison", report,
        )

    return 200, response


__all__ = ["handle_quote_compare"]
