"""
C17 — Canonical signatures (R6 / R7 / R8)
==========================================

Implements deterministic SHA-256 signatures over QuoteComparisonReport
and intermediate artifacts. Three signatures are emitted per report:

  canonical_replay_signature  (R6) — sha256 over the report's
      canonical-state tuple. Two reports with byte-equal canonical
      form produce identical signatures. Includes strict_mode (R6).

  presentation_signature      (R7) — sha256 over canonical_replay
      signature + presentation-only fields (e.g., display ordering
      hints). MUST have canonical_replay_signature as prefix
      (R7 inheritance from C16). v1.0: same as canonical because
      R15 narrowed — no presentation-implying fields on C17 output.

  schema_descriptor_digest    (R8) — sha256 over the *shape* of the
      QuoteComparisonReport (field names + types + invariant version
      table). Changes when C17_REPORT_SCHEMA_VERSION bumps. Allows
      downstream consumers to fail fast on schema drift.

Plus:
  source_quote_signature      — sha256 over canonicalised ParsedQuote
  source_boq_signature        — sha256 over canonicalised ProjectBOQ

Rule 11 self-analysis:
  1. JSON dumping a dataclass with Enums needs explicit conversion.
     We define _canon() to walk a dataclass into a JSON-stable
     primitive tree.
  2. Floats are notorious for non-determinism in JSON. We round to
     6 decimals before serialising; matches RateProvider precision
     and EPSILON_RATE_DELTA_PCT/EPSILON_AMOUNT_INR.
  3. Tuples become lists in JSON. That's fine — sha256 only cares
     about bytes, and tuple↔list round-trip is stable.
  4. dict key ordering: we use sort_keys=True everywhere.
  5. TransparencyTriple has a `derivation: list[DerivationLine]`
     field — DerivationLine is not frozen. We rely on its dataclass
     vars being deterministic. If they're not, signatures drift.
     Documented; if drift observed, B-C17-DERIVATION-CANONICALIZATION.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from buildemup.components.c17.contracts import ParsedQuote, ProjectBOQ
from buildemup.components.c17.versioning import (
    C17_IDENTITY_GENERATION,
    C17_REPORT_SCHEMA_VERSION,
    C17_VERSION,
)


# ============================================================
# § 1 — CANONICAL JSON SERIALISATION
# ============================================================

_FLOAT_ROUND_DECIMALS = 6


def _canon(obj: Any) -> Any:
    """Walk an object into a JSON-stable primitive tree.

    Rules:
      - dataclass: dict {fieldname: _canon(value)}
      - Enum:      .value (string or int)
      - tuple/list: list of _canon(...)
      - dict:       sorted-key dict of _canon(...)
      - float:      rounded to _FLOAT_ROUND_DECIMALS
      - str/int/bool/None: passthrough
      - other:     repr() (best-effort; surfaces in tests if needed)
    """
    if obj is None or isinstance(obj, (str, bool, int)):
        # NB: bool before int — bool is a subclass of int.
        return obj
    if isinstance(obj, float):
        return round(obj, _FLOAT_ROUND_DECIMALS)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (tuple, list)):
        return [_canon(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _canon(v) for k, v in sorted(obj.items(), key=lambda kv: kv[0])}
    if is_dataclass(obj):
        out: dict[str, Any] = {}
        for f in fields(obj):
            # Skip private / underscore fields (e.g. R13's class-constant
            # `R13_MANDATORY_CLAUSE_SUBSTRING` that is init=False).
            if f.name.startswith("_"):
                continue
            if not f.init and f.name.startswith("R13_"):
                # R13_MANDATORY_CLAUSE_SUBSTRING — class constant, not data
                continue
            out[f.name] = _canon(getattr(obj, f.name))
        return out
    # Defensive fallback
    return repr(obj)


def _sha256_hex(payload: Any) -> str:
    """Deterministic sha256 hex of any object via _canon + sort_keys JSON."""
    canonical = _canon(payload)
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ============================================================
# § 2 — SOURCE SIGNATURES
# ============================================================

def compute_parsed_quote_signature(pq: ParsedQuote) -> str:
    """sha256 over the entire ParsedQuote (excluding its own
    `parsed_quote_signature` field — that's the value being computed).

    Used by phase α to verify the parser-supplied signature matches
    what we'd compute ourselves. Drift → UpstreamSchemaDriftError."""
    payload = {
        "parsed_quote_id":   pq.parsed_quote_id,
        "contractor_label":  pq.contractor_label,
        "quote_date_iso":    pq.quote_date_iso,
        "quote_total_inr":   pq.quote_total_inr,
        "line_items":        [_canon(li) for li in pq.line_items],
        "parser_hint_decomposition_style": pq.parser_hint_decomposition_style,
    }
    return _sha256_hex(payload)


def compute_project_boq_signature(boq: ProjectBOQ) -> str:
    """sha256 over the ProjectBOQ (excluding its own boq_signature)."""
    payload = {
        "project_id":              boq.project_id,
        "jurisdiction_profile_id": boq.jurisdiction_profile_id,
        "declared_domain_scope":   boq.declared_domain_scope,
        "rate_provider_kb_version": boq.rate_provider_kb_version,
        "rate_provider_kb_date":   boq.rate_provider_kb_date,
        "rate_provider_locality":  boq.rate_provider_locality,
        "items":                   [_canon(it) for it in boq.items],
    }
    return _sha256_hex(payload)


# ============================================================
# § 3 — REPORT-LEVEL SIGNATURES (R6 / R7 / R8)
# ============================================================

def compute_canonical_replay_signature(
    *,
    source_quote_signature:  str,
    source_boq_signature:    str,
    strict_mode:             str,
    matched_lines:           tuple,
    missing_from_quote:      tuple,
    unmatched_quote_lines:   tuple,
    lump_sum_indicators:     tuple,
    decomposition_acknowledgment: Any,
    total_comparison:        Any,
    discussion_baseline:     Any,
    itemization_indicators:  Any,
    report_confidence:       Any,
    rate_staleness_disclosure: Any,
    jurisdiction_profile_id: str,
    declared_domain_scope:   str,
) -> str:
    """R6: byte-equal on replay given identical inputs.

    Includes strict_mode per spec § 4 — STRICT and WARN produce
    different reports (WARN may have FailedComparisonRecords),
    so they must have distinct signatures."""
    payload = {
        "c17_version":             C17_VERSION,
        "c17_schema_version":      C17_REPORT_SCHEMA_VERSION,
        "c17_identity_generation": C17_IDENTITY_GENERATION,
        "strict_mode":             strict_mode,
        "source_quote_signature":  source_quote_signature,
        "source_boq_signature":    source_boq_signature,
        "jurisdiction_profile_id": jurisdiction_profile_id,
        "declared_domain_scope":   declared_domain_scope,
        "rate_staleness":          _canon(rate_staleness_disclosure),
        "matched_lines":           [_canon(m) for m in matched_lines],
        "missing_from_quote":      [_canon(g) for g in missing_from_quote],
        "unmatched_quote_lines":   [_canon(u) for u in unmatched_quote_lines],
        "lump_sum_indicators":     [_canon(l) for l in lump_sum_indicators],
        "decomposition":           _canon(decomposition_acknowledgment),
        "total_comparison":        _canon(total_comparison),
        "discussion_baseline":     _canon(discussion_baseline),
        "itemization_indicators":  _canon(itemization_indicators),
        "report_confidence":       _canon(report_confidence),
    }
    return _sha256_hex(payload)


def compute_presentation_signature(
    *,
    canonical_replay_signature: str,
) -> str:
    """R7: MUST have canonical_replay_signature as conceptual prefix.

    Per spec § 7 R15 (narrowed v0.3): C17 has NO presentation-only
    fields (no headline, no prominence, no top_concern). Therefore
    the presentation signature equals the canonical signature for
    v1.0. If presentation-affecting fields are added in a future
    schema bump, this function changes; the R7-prefix invariant
    remains."""
    # R7 conceptual prefix is satisfied by structural equality at v1.0.
    # The hash function is the identity on the canonical value, ensuring
    # the prefix property holds in any future where additive
    # presentation salt is appended.
    return canonical_replay_signature


def compute_schema_descriptor_digest() -> str:
    """R8: sha256 over the SHAPE of QuoteComparisonReport — field
    names, types, invariant version table. Changes only when
    C17_REPORT_SCHEMA_VERSION bumps.

    Used by downstream consumers to fail fast on schema drift
    (read this digest, cache it; if it changes without an expected
    schema-version bump, raise UpstreamSchemaDriftError on YOUR side)."""
    # Lazy import to avoid circular: schema.py imports cache_keys? No.
    # cache_keys imports schema only here.
    from buildemup.components.c17.schema import (
        DecompositionAcknowledgment,
        DiscussionBaseline,
        GapIndicator,
        ItemizationIndicators,
        LumpSumIndicator,
        MatchedLine,
        QuoteComparisonReport,
        RateStalenessDisclosure,
        ReportConfidence,
        TotalComparison,
        UnmatchedQuoteLine,
    )

    def _shape(cls: type) -> dict[str, str]:
        out: dict[str, str] = {}
        for f in fields(cls):
            if f.name.startswith("_") or (not f.init and f.name.startswith("R13_")):
                continue
            out[f.name] = repr(f.type)
        return out

    descriptor = {
        "c17_version":             C17_VERSION,
        "c17_schema_version":      C17_REPORT_SCHEMA_VERSION,
        "c17_identity_generation": C17_IDENTITY_GENERATION,
        "shapes": {
            "QuoteComparisonReport":       _shape(QuoteComparisonReport),
            "RateStalenessDisclosure":     _shape(RateStalenessDisclosure),
            "MatchedLine":                 _shape(MatchedLine),
            "GapIndicator":                _shape(GapIndicator),
            "UnmatchedQuoteLine":          _shape(UnmatchedQuoteLine),
            "LumpSumIndicator":            _shape(LumpSumIndicator),
            "DecompositionAcknowledgment": _shape(DecompositionAcknowledgment),
            "TotalComparison":             _shape(TotalComparison),
            "DiscussionBaseline":          _shape(DiscussionBaseline),
            "ItemizationIndicators":       _shape(ItemizationIndicators),
            "ReportConfidence":            _shape(ReportConfidence),
        },
    }
    return _sha256_hex(descriptor)
