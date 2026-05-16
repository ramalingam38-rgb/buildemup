"""
BuildemUp — Component 12 — input resolution (Phase 0 ingress)
==============================================================

Per C12 SPEC v1.0 LOCKED:
- v0.2-A1: HARD-fail-fast on Tier A SHALLOW inputs at ingress
  (capability_mode != MATERIALIZED → CapabilityFlagInconsistencyError)
- v0.4-A1: schema version probes (CORRIDOR_ZONE_SCHEMA_VERSION,
  ADJACENCY_HINT_SCHEMA_VERSION) → UpstreamSchemaDriftError
- v0.4-A2: RoomCategory resolution using existing C9.RoomCategory
  enum + documented alias map for other_rooms strings

This module is pure ingress-validation. It does NOT mutate inputs;
it returns normalized values + raises on violations.
"""
from __future__ import annotations

from typing import Final, Iterable

from .errors import (
    CapabilityFlagInconsistencyError,
    UpstreamSchemaDriftError,
)
from .versioning import (
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
)


# =============================================================================
# v0.4-A1 — Schema-version probes at C12 ingress
# =============================================================================

def assert_upstream_schema_versions() -> None:
    """Phase 0 step 4 (per v0.4-A1): probe upstream schema version
    constants against the values C12 was built against.

    Raises ``UpstreamSchemaDriftError`` on mismatch — catches the
    cross-component contract drift class (academically validated as
    "SemB issues" per Sembid 2022, arxiv 2209.00393).

    NOTE: this catches VERSION drift, not SEMANTIC drift. Semantic
    drift (same version, different behavior) is filed as
    B-C12-CONTRACT-SEMANTIC-VERIFICATION per Walk #5 Item 3.
    """
    # C8 corridor zone schema
    try:
        from buildemup.components.c08.schema import (
            CORRIDOR_ZONE_SCHEMA_VERSION,
        )
    except ImportError as exc:
        raise UpstreamSchemaDriftError(
            "C12 v1 requires CORRIDOR_ZONE_SCHEMA_VERSION constant in "
            "buildemup.components.c08.schema (per B-C8-SCHEMA-VERSION-"
            "CONSTANT amendment). Constant not found."
        ) from exc

    if CORRIDOR_ZONE_SCHEMA_VERSION != EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION:
        raise UpstreamSchemaDriftError(
            f"C12 v1 was built against CORRIDOR_ZONE_SCHEMA_VERSION="
            f"{EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION}, but C8 reports "
            f"version {CORRIDOR_ZONE_SCHEMA_VERSION}. Upstream contract "
            f"drift detected. C12 needs amendment to consume the new "
            f"version."
        )

    # C9 adjacency hint schema
    try:
        from buildemup.domain.adjacency_hint import (
            ADJACENCY_HINT_SCHEMA_VERSION,
        )
    except ImportError as exc:
        raise UpstreamSchemaDriftError(
            "C12 v1 requires ADJACENCY_HINT_SCHEMA_VERSION constant in "
            "buildemup.domain.adjacency_hint (per B-C9-SCHEMA-VERSION-"
            "CONSTANT amendment). Constant not found."
        ) from exc

    if ADJACENCY_HINT_SCHEMA_VERSION != EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION:
        raise UpstreamSchemaDriftError(
            f"C12 v1 was built against ADJACENCY_HINT_SCHEMA_VERSION="
            f"{EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION}, but the domain "
            f"layer reports version {ADJACENCY_HINT_SCHEMA_VERSION}. "
            f"Upstream contract drift detected."
        )


# =============================================================================
# v0.2-A1 — Tier A HARD-fail-fast on capability flag
# =============================================================================

def assert_materialized_capability(
    *,
    candidate_signature: str,
    capability_mode: str,
    placement_safe: bool,
    geometry_materialized: bool,
) -> None:
    """Phase 0 step 3 (per v0.2-A1): assert the upstream candidate
    is MATERIALIZED, not Tier A SHALLOW (PREDICATE_ONLY).

    v1 ships STRICT-MATERIALIZED-only. Tier A inputs are REJECTED at
    ingress with CapabilityFlagInconsistencyError; future
    B-C12-TIER-A-RESOLVERS will provide per-operator resolvers.

    Three conjunctive checks per v0.2-A1 amendment text:
      - geometry_materialized is True
      - placement_safe is True
      - capability_mode == "MATERIALIZED"
    """
    if not geometry_materialized:
        raise CapabilityFlagInconsistencyError(
            f"Candidate {candidate_signature!r}: geometry_materialized "
            f"is False. C12 v1 STRICT-MATERIALIZED-only (per v0.2-A1). "
            f"Tier A SHALLOW inputs require B-C12-TIER-A-RESOLVERS."
        )
    if not placement_safe:
        raise CapabilityFlagInconsistencyError(
            f"Candidate {candidate_signature!r}: placement_safe is "
            f"False. C12 v1 requires placement-safe candidates from "
            f"C11b. (B-C11B-CAPABILITY-FLAG-DECOMPOSITION post-v1 will "
            f"split this overloaded flag.)"
        )
    if capability_mode != "MATERIALIZED":
        raise CapabilityFlagInconsistencyError(
            f"Candidate {candidate_signature!r}: capability_mode="
            f"{capability_mode!r}. Expected 'MATERIALIZED' per v0.2-A1."
        )


# =============================================================================
# v0.4-A2 — Room category resolution
# =============================================================================

# Documented alias map per v0.4-A2. FROZEN at 6 canonical entries per
# v0.5 § 0.4 + v0.6 governance (expansion requires backlog migration
# plan via B-C12-LAYERED-ALIAS-NORMALIZATION).
#
# Maps RAW string variants → CANONICAL form. Used only for the
# open-ended FloorRoomBrief.other_rooms tuple; the standard room
# categories (bedroom, bathroom, kitchen, living, pooja, utility)
# come directly from the typed brief fields.
_OTHER_ROOMS_ALIAS_MAP: Final[dict[str, str]] = {
    # guest bedroom variants
    "guest_bedroom": "guest_bedroom",
    "guest-bedroom": "guest_bedroom",
    "guest bedroom": "guest_bedroom",
    "guest room": "guest_bedroom",
    "guestbedroom": "guest_bedroom",
    "GuestBedroom": "guest_bedroom",
    # study variants
    "study": "study",
    "study_room": "study",
    "study-room": "study",
    "study room": "study",
    # balcony variants
    "balcony": "balcony",
    "balconies": "balcony",
    # store/storage variants
    "store": "store",
    "storage": "store",
    "storeroom": "store",
    "store_room": "store",
    "store-room": "store",
    # servant variants
    "servant": "servant",
    "servant_quarter": "servant",
    "servant-quarter": "servant",
    "servant quarter": "servant",
    "servant_room": "servant",
}

# The 6 canonical "other_rooms" categories. Per v0.5/v0.6 freeze rule,
# expanding this requires backlog item filing + amendment.
_CANONICAL_OTHER_ROOMS: Final[frozenset[str]] = frozenset({
    "guest_bedroom",
    "study",
    "balcony",
    "store",
    "servant",
    "other",  # generic fallback bucket
})


def normalize_other_room_category(raw: str) -> str:
    """Canonicalize a FloorRoomBrief.other_rooms string via the
    documented alias map.

    Per v0.4-A2 + v0.5 freeze + v0.6 governance.

    Lookup is exact-first (preserves intentional distinctions), then
    falls back to a deterministic normalization rule:
      ``raw.strip().lower().replace(' ', '_').replace('-', '_')``

    If the normalized result is in the canonical set, it's returned.
    Otherwise returns ``"other"`` as the safe fallback bucket (and
    the caller should emit telemetry per B-C12-UNKNOWN-CATEGORY-
    TELEMETRY).
    """
    if raw in _OTHER_ROOMS_ALIAS_MAP:
        return _OTHER_ROOMS_ALIAS_MAP[raw]
    normalized = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in _CANONICAL_OTHER_ROOMS:
        return normalized
    if normalized in _OTHER_ROOMS_ALIAS_MAP:
        return _OTHER_ROOMS_ALIAS_MAP[normalized]
    return "other"


def is_canonical_other_room_category(category: str) -> bool:
    """True iff the category is in the frozen v1 canonical set."""
    return category in _CANONICAL_OTHER_ROOMS


def list_unknown_other_rooms(
    raw_categories: Iterable[str],
) -> tuple[str, ...]:
    """Return raw category strings that don't map to a known canonical
    form (i.e., would fall through to the ``"other"`` bucket).

    Used by the orchestrator to emit B-C12-UNKNOWN-CATEGORY-TELEMETRY
    on each batch.
    """
    unknown: list[str] = []
    for raw in raw_categories:
        if raw in _OTHER_ROOMS_ALIAS_MAP:
            continue
        normalized = raw.strip().lower().replace(" ", "_").replace("-", "_")
        if normalized in _CANONICAL_OTHER_ROOMS:
            continue
        if normalized in _OTHER_ROOMS_ALIAS_MAP:
            continue
        unknown.append(raw)
    return tuple(unknown)


# =============================================================================
# NBC 2016 doorway minima — v0.2-A9 + v0.4-A2
# =============================================================================

# Per NBC 2016 Part 3 (verified via web search at S43 v0.2 walk):
#   - Main entrance:        1.00 m minimum
#   - Bedroom door:         0.90 m minimum
#   - Bathroom door:        0.75 m minimum
#   - General fallback:     0.75 m minimum
#
# These are CLEAR widths (the unobstructed opening width), not nominal
# door-leaf widths.
NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M: Final[float] = 1.00
NBC_2016_DOORWAY_MIN_BEDROOM_M: Final[float] = 0.90
NBC_2016_DOORWAY_MIN_BATHROOM_M: Final[float] = 0.75
NBC_2016_DOORWAY_MIN_GENERAL_M: Final[float] = 0.75


def doorway_minimum_for_pair(category_a: str, category_b: str) -> float:
    """Per v0.2-A9 + v0.4-A2: derive the NBC 2016 doorway minimum
    clear width for a shared edge between two rooms by category.

    Priority order (a higher-priority category in either slot
    determines the minimum):
      1. Main entrance / entry → 1.00 m
      2. Bedroom (any subtype, incl. master) → 0.90 m
      3. Bathroom / wc / toilet → 0.75 m
      4. Else → 0.75 m (general fallback)
    """
    # Normalize for case-insensitive matching.
    a = category_a.lower()
    b = category_b.lower()

    # Priority 1: main entrance / entry adjacency
    entrance_keywords = {"main_entrance", "entrance", "entry", "foyer"}
    if a in entrance_keywords or b in entrance_keywords:
        return NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M

    # Priority 2: bedroom adjacency
    bedroom_keywords = {"bedroom", "master_bedroom", "guest_bedroom"}
    if a in bedroom_keywords or b in bedroom_keywords:
        return NBC_2016_DOORWAY_MIN_BEDROOM_M

    # Priority 3: bathroom / wc / toilet adjacency
    bathroom_keywords = {"bathroom", "master_bathroom", "wc", "toilet"}
    if a in bathroom_keywords or b in bathroom_keywords:
        return NBC_2016_DOORWAY_MIN_BATHROOM_M

    # Fallback: general
    return NBC_2016_DOORWAY_MIN_GENERAL_M


__all__ = [
    # Phase 0 ingress checks
    "assert_upstream_schema_versions",
    "assert_materialized_capability",
    # Room category resolution
    "normalize_other_room_category",
    "is_canonical_other_room_category",
    "list_unknown_other_rooms",
    # NBC 2016 doorway constants
    "NBC_2016_DOORWAY_MIN_MAIN_ENTRANCE_M",
    "NBC_2016_DOORWAY_MIN_BEDROOM_M",
    "NBC_2016_DOORWAY_MIN_BATHROOM_M",
    "NBC_2016_DOORWAY_MIN_GENERAL_M",
    "doorway_minimum_for_pair",
]
