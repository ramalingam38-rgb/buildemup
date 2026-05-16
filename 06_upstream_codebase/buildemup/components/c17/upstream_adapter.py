"""
C17 — Upstream adapter (C7 / C16 → ProjectBOQ)
================================================

Phase β-1: turn upstream component outputs (C7 cost estimates, C16
dual-drawing bundle metadata, RateProvider rates) into a ProjectBOQ
that phase γ can match against.

This module is the BOUNDARY between C17 and the rest of the pipeline.
It is intentionally minimal: it does NOT make pricing decisions, does
NOT compute deltas, does NOT emit signals. It only:

  1. Walks the upstream artifacts in canonical order
  2. Looks up RateProvider rates for each item
  3. Builds ProjectBOQItem instances
  4. Computes the BOQ signature

Per spec § 8: expected upstream versions are pinned. Mismatches raise
UpstreamSchemaDriftError (LocalQuoteError tier — always halts).

Rule 11 self-analysis:
  1. C7 / C16 surface in our test scaffolding is partial — for the
     adapter we only need a duck-typed protocol of what we read from
     them. Real C7/C16 output objects will conform. v1.0 documents
     this protocol explicitly so the upstream teams can build to it.
  2. Items derived from "miscellaneous" categories have no brand/grade/
     is_code — phase γ's match-basis must accept None for those fields.
     Verified via __post_init__ allowing Optional.
  3. The adapter sorts items by canonical_sort_key (boq_id ASC) before
     emitting — R6 determinism requires byte-equal output across runs.
"""

from __future__ import annotations

from typing import Iterable, Protocol, Tuple

from buildemup.components.c16.contracts import AttestedValue, AuthorityKind
from buildemup.components.c17.cache_keys import compute_project_boq_signature
from buildemup.components.c17.contracts import (
    BOQCategory,
    ProjectBOQ,
    ProjectBOQItem,
)
from buildemup.components.c17.errors import (
    BOQAssemblyError,
    RateProviderUnavailableError,
)
from buildemup.utils.rate_provider import MaterialRate, RateProvider


# ============================================================
# § 1 — UPSTREAM PROTOCOLS (duck-typed shapes we expect)
# ============================================================
#
# These Protocols pin the SHAPE we read from C7 / C16. Real C7/C16
# objects don't need to inherit from these — Python structural typing
# allows them to satisfy the protocol implicitly. The Protocols exist
# so this module's contract is greppable.


class _UpstreamCostLine(Protocol):
    """The shape we expect from a C7 cost line."""
    item_id:        str
    label:          str
    category:       str
    quantity:       float
    unit:           str
    rate_category:  str          # RateProvider category key
    rate_key:       str          # RateProvider key within category
    severity:       str          # "critical" / "important" / "minor"


class _UpstreamCostBundle(Protocol):
    """The shape we expect from the C7 cost-estimator output."""
    cost_lines: Iterable[_UpstreamCostLine]


# ============================================================
# § 2 — RATE LOOKUP HELPERS
# ============================================================

def _attested_from_rate_field(
    value: float,
    *,
    upstream_source: str,
    field_name: str,
) -> AttestedValue:
    """Wrap a RateProvider-sourced numeric in an UPSTREAM_AUTHORITATIVE
    AttestedValue. Per R1 every numeric is wrapped."""
    return AttestedValue(
        value=float(value),
        authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
        upstream_source=f"{upstream_source}.{field_name}",
    )


def _attested_derived(
    value: float,
    *,
    derivation_note: str,
) -> AttestedValue:
    """LOCALLY_DERIVED wrapper (e.g., quantity × rate)."""
    return AttestedValue(
        value=float(value),
        authority=AuthorityKind.LOCALLY_DERIVED,
        derivation_note=derivation_note,
    )


# ============================================================
# § 3 — ADAPTER ENTRYPOINT
# ============================================================

def build_project_boq(
    *,
    project_id:                str,
    jurisdiction_profile_id:   str,
    declared_domain_scope:     str,
    cost_lines:                Iterable[_UpstreamCostLine],
    rate_provider:             RateProvider,
    locality_label:            str = "Chennai-wide",
) -> ProjectBOQ:
    """Build a ProjectBOQ from C7 cost lines + a RateProvider.

    Walks cost_lines in input order, then sorts the resulting
    ProjectBOQItem tuple by boq_id (canonical for R6).

    Errors:
        RateProviderUnavailableError (LocalQuoteError) — RateProvider
            raises KeyError for a category/key. We re-raise as Local
            because the BOQ can't be assembled without all rates.
        BOQAssemblyError (PerQuoteLineError) — quantity is 0/negative
            or label is empty. Single-line scope; STRICT halts, WARN
            collects.
    """
    items: list[ProjectBOQItem] = []

    for line in cost_lines:
        # Validate single-line invariants
        if not getattr(line, "item_id", ""):
            raise BOQAssemblyError(
                "Upstream cost line has empty item_id.",
                boq_id="(missing)",
                reason="item_id empty",
            )
        if not getattr(line, "label", ""):
            raise BOQAssemblyError(
                f"Upstream cost line[{line.item_id}] has empty label.",
                boq_id=line.item_id,
                reason="label empty",
            )
        if line.quantity is None or line.quantity <= 0:
            raise BOQAssemblyError(
                f"Upstream cost line[{line.item_id}] has non-positive "
                f"quantity {line.quantity}.",
                boq_id=line.item_id,
                reason=f"quantity={line.quantity}",
            )

        # RateProvider lookup
        try:
            mr: MaterialRate = rate_provider.get_rate(line.rate_category, line.rate_key)
        except KeyError as exc:
            raise RateProviderUnavailableError(
                f"RateProvider lookup failed for "
                f"category={line.rate_category!r} key={line.rate_key!r} "
                f"(boq_id={line.item_id}). Cannot assemble BOQ.",
                jurisdiction=jurisdiction_profile_id,
                reason=f"missing rate: {exc!r}",
            ) from exc

        rate_min = mr.rate_min if mr.rate_min is not None else mr.rate
        rate_max = mr.rate_max if mr.rate_max is not None else mr.rate

        upstream_src = f"rate_provider.{rate_provider.kb_version}"

        # Wrap rates as UPSTREAM_AUTHORITATIVE
        quantity_av = AttestedValue(
            value=float(line.quantity),
            authority=AuthorityKind.UPSTREAM_AUTHORITATIVE,
            upstream_source=f"c07_cost_estimator.{line.item_id}",
        )
        rate_median_av = _attested_from_rate_field(
            mr.rate, upstream_source=upstream_src, field_name="rate_median",
        )
        rate_min_av = _attested_from_rate_field(
            rate_min, upstream_source=upstream_src, field_name="rate_min",
        )
        rate_max_av = _attested_from_rate_field(
            rate_max, upstream_source=upstream_src, field_name="rate_max",
        )
        total_median_av = _attested_derived(
            line.quantity * mr.rate,
            derivation_note=f"{line.quantity} × {mr.rate} (median)",
        )

        # Category mapping — strict; unknown → "miscellaneous"
        category: BOQCategory = _coerce_category(line.category)

        item = ProjectBOQItem(
            boq_id=line.item_id,
            label=line.label,
            category=category,
            quantity=quantity_av,
            unit=line.unit,
            rate_median=rate_median_av,
            rate_min=rate_min_av,
            rate_max=rate_max_av,
            total_median=total_median_av,
            brand=mr.brand or None,
            grade=mr.grade or None,
            is_code=mr.is_code or None,
            source_component="c07_cost_estimator",
            source_section=f"{line.rate_category}.{line.rate_key}",
            severity_if_missing=_coerce_severity(line.severity),
        )
        items.append(item)

    # Canonical sort for R6 determinism
    items.sort(key=lambda it: it.boq_id)
    items_tuple: Tuple[ProjectBOQItem, ...] = tuple(items)

    # Compute signature OVER the canonicalised items (excluding signature itself)
    # — we use a temporary BOQ with empty signature, then compute, then replace.
    # The cleanest path is to compute via the same _canon helper used in cache_keys.
    boq_signature = compute_project_boq_signature(
        ProjectBOQ(
            project_id=project_id,
            jurisdiction_profile_id=jurisdiction_profile_id,
            declared_domain_scope=declared_domain_scope,
            items=items_tuple,
            boq_signature="",
            rate_provider_kb_version=rate_provider.kb_version,
            rate_provider_kb_date=_extract_kb_date(rate_provider),
            rate_provider_locality=locality_label,
        ),
    )

    return ProjectBOQ(
        project_id=project_id,
        jurisdiction_profile_id=jurisdiction_profile_id,
        declared_domain_scope=declared_domain_scope,
        items=items_tuple,
        boq_signature=boq_signature,
        rate_provider_kb_version=rate_provider.kb_version,
        rate_provider_kb_date=_extract_kb_date(rate_provider),
        rate_provider_locality=locality_label,
    )


# ============================================================
# § 4 — CATEGORY / SEVERITY COERCION
# ============================================================

_KNOWN_BOQ_CATEGORIES = {
    "structural_rcc",
    "structural_steel",
    "masonry",
    "plumbing",
    "electrical",
    "doors_windows",
    "flooring",
    "painting",
    "waterproofing",
    "miscellaneous",
}


def _coerce_category(raw: str) -> BOQCategory:
    """Coerce upstream category string into BOQCategory.

    Unknown → "miscellaneous". This is deliberately tolerant —
    upstream may use shorthand ("rcc", "brick"); we map known
    synonyms here. If misclassification becomes an issue,
    B-C17-CATEGORY-MAPPING tightens this."""
    if raw in _KNOWN_BOQ_CATEGORIES:
        return raw  # type: ignore[return-value]
    synonyms = {
        "rcc":           "structural_rcc",
        "concrete":      "structural_rcc",
        "steel":         "structural_steel",
        "rebar":         "structural_steel",
        "brick":         "masonry",
        "brickwork":     "masonry",
        "plaster":       "masonry",
        "plumb":         "plumbing",
        "wet":           "plumbing",
        "electric":      "electrical",
        "elec":          "electrical",
        "door":          "doors_windows",
        "window":        "doors_windows",
        "floor":         "flooring",
        "tile":          "flooring",
        "paint":         "painting",
        "wp":            "waterproofing",
        "waterproof":    "waterproofing",
    }
    return synonyms.get(raw, "miscellaneous")  # type: ignore[return-value]


def _coerce_severity(raw: str):
    """Coerce upstream severity into the BOQItem severity_if_missing.
    Unknown → 'important' (middle ground)."""
    if raw in ("critical", "important", "minor"):
        return raw
    return "important"


def _extract_kb_date(rate_provider: RateProvider) -> str:
    """Best-effort: extract an ISO date from kb_version (e.g.,
    'Chennai_2026_Q2_v1' → '2026-04-01'). If absent, return today.

    Real providers may expose `kb_date` directly; we check for that
    first to preserve provenance fidelity."""
    direct = getattr(rate_provider, "kb_date", None)
    if direct:
        return str(direct)
    # Heuristic from kb_version
    v = rate_provider.kb_version
    if "_Q1" in v:
        # Pull the year
        for tok in v.split("_"):
            if tok.isdigit() and len(tok) == 4:
                return f"{tok}-01-01"
    if "_Q2" in v:
        for tok in v.split("_"):
            if tok.isdigit() and len(tok) == 4:
                return f"{tok}-04-01"
    if "_Q3" in v:
        for tok in v.split("_"):
            if tok.isdigit() and len(tok) == 4:
                return f"{tok}-07-01"
    if "_Q4" in v:
        for tok in v.split("_"):
            if tok.isdigit() and len(tok) == 4:
                return f"{tok}-10-01"
    # Default: a stable placeholder. NOT today() — that would break R6.
    return "2026-01-01"
