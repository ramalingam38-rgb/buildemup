"""B-NEW-J-override (S55 Batch 3) — layout-override consultation hook.

When C11a's predicate registry runs a B-NEW-J-style rule (e.g.,
road-facing PRIVATE band penalty), it MUST consult the Brief's
`layout_overrides` before applying the penalty. Without this, view-
typology homes (sea-facing master bedroom, valley-facing private wing)
get systematically rejected by the search even when the user explicitly
asked for that arrangement.

Public API:
  should_skip_predicate(brief, rule_id) → bool

The function is keyed off documented rule ids so a future B-NEW-J
production shipping (and any additional overrides we add) doesn't need
to re-thread plumbing.

Per backlog: "When implemented, MUST follow B-meta-rule-taxonomy
framework (no one-off override mechanism)." This file IS that framework
for C11a — the single consultation point.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buildemup.domain.brief import Brief, LayoutOverrides


# ─────────────────────────────────────────────────────────────────────────
# Rule-id → LayoutOverrides field map
# ─────────────────────────────────────────────────────────────────────────
# Each entry: predicate rule id → attribute name on LayoutOverrides whose
# True value bypasses the predicate. Adding a new override here means
# adding a new field on LayoutOverrides AND registering its consultation
# entry below.

_OVERRIDE_BY_RULE_ID: dict[str, str] = {
    # B-NEW-J road-facing PRIVATE band rule
    "C5.road_facing_private_band": "accept_road_facing_private_band",
    # Future B-NEW-J-acoustic kitchen↔bedroom adjacency (placeholder mapping;
    # the predicate itself ships post-launch per B-NEW-J-acoustic backlog).
    "C9.kitchen_bedroom_adjacency": "accept_kitchen_adjacent_to_bedroom",
    # Vastu FULL tier override (B-099 deferred to v1.1; mapping wired now)
    "C5.vastu_full_orientation": "accept_vastu_violation_for_view",
}


def should_skip_predicate(brief: "Brief", rule_id: str) -> bool:
    """Return True iff the Brief's layout_overrides authorise skipping
    the named predicate.

    Unknown rule ids return False (we don't grant blanket bypasses for
    unrecognised rules — the override must be explicitly mapped).
    """
    field_name = _OVERRIDE_BY_RULE_ID.get(rule_id)
    if field_name is None:
        return False
    overrides = brief.layout_overrides
    return bool(getattr(overrides, field_name, False))


def registered_rule_ids() -> tuple[str, ...]:
    """Canonical lex-ASC tuple of rule ids with override mappings.

    Used by tests + provenance to enumerate the audit surface.
    """
    return tuple(sorted(_OVERRIDE_BY_RULE_ID.keys()))


__all__ = [
    "should_skip_predicate",
    "registered_rule_ids",
]
