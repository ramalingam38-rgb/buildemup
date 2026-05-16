"""
BuildemUp — Component 15 — Unconventional Pattern Detector (v1 LOCK)
========================================================================

Per C15 SPEC v0.2 A7 + LOCK-mandatory B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK.

The 5 v1 patterns (per UNCONVENTIONAL_PATTERN_NAMES) with their
detection feasibility at v1:

| Pattern                            | v1 data avail.   | Detect logic       |
|------------------------------------|------------------|--------------------|
| courtyard_centered                 | YES via C12+C14  | implemented        |
| compact_incremental                | YES via C12      | implemented        |
| split_level_circulation            | NO (no z-offset) | stub: never detect |
| ritual_procession                  | NO (no ritual)   | stub: never detect |
| multigenerational_segregation      | NO (no class)    | stub: never detect |

Honest position per Rule 11 vigorous self-analysis: at v1, the 3
stubbed patterns CANNOT be reliably detected from current upstream
data shape. Pretending otherwise (e.g., guessing "split_level" from
room IDs) would be Pattern A bandage logic. The honest move is to
document each stub with its specific data dependency + B-NNN tracking
item, never emit detected=True for them, and let v2 enable them when
upstream extensions ship.

Filed (or extended) backlog items:
- B-C15-PATTERN-SPLIT-LEVEL-DATA (v2: floor_metadata.z_offset)
- B-C15-PATTERN-RITUAL-PROCESSION-DATA (v2: ritual-category room labels)
- B-C15-PATTERN-MULTIGEN-SEGREGATION-DATA (v2: master-class bedroom
  distinction in room categories)

Per A7 Inv: when ANY pattern is detected, UX reduces confidence on the
flagged check_ids.
"""
from __future__ import annotations

from typing import Iterable

from .schema import UnconventionalPatternHint, UNCONVENTIONAL_PATTERN_NAMES


# =============================================================================
# Helpers — extract data from C12 candidate + C14 report
# =============================================================================

def _placed_rooms(c12_candidate: object) -> tuple:
    """Duck-typed accessor for C12 PlacedCandidate.placed_rooms."""
    return tuple(getattr(c12_candidate, "placed_rooms", ()) or ())


def _category(room: object) -> str:
    """Duck-typed accessor for room category. Returns lowercase
    string; empty string if missing."""
    cat = getattr(room, "category", "")
    return cat.lower() if isinstance(cat, str) else ""


def _area_m2(room: object) -> float:
    """Duck-typed area in m². Tries area_m2 first, then width*depth."""
    a = getattr(room, "area_m2", None)
    if isinstance(a, (int, float)) and a > 0:
        return float(a)
    w = getattr(room, "width_m", None)
    d = getattr(room, "depth_m", None)
    if isinstance(w, (int, float)) and isinstance(d, (int, float)) \
            and w > 0 and d > 0:
        return float(w) * float(d)
    return 0.0


def _adjacency_map(c14_report: object) -> dict[str, frozenset[str]]:
    """Duck-typed accessor for C14 adjacency. Returns
    {room_id: frozenset(adjacent_room_ids)}. Empty if C14 absent or
    lacks adjacency."""
    graph = getattr(c14_report, "adjacency_graph", None)
    if graph is None:
        return {}
    out: dict[str, frozenset[str]] = {}
    for k, vs in graph.items() if hasattr(graph, "items") else ():
        out[str(k)] = frozenset(str(v) for v in vs)
    return out


# =============================================================================
# Pattern 1: courtyard_centered (IMPLEMENTED)
# =============================================================================

def _detect_courtyard_centered(
    c12_candidate: object, c14_report: object,
) -> bool:
    """Heuristic per UNCONVENTIONAL_PATTERN_NAMES docstring:
    > 3 habitable rooms with primary adjacency to a single
    non-habitable central room (the courtyard).

    v1 implementation:
      - Identify candidate "courtyard" rooms: category contains
        "courtyard" OR "open_to_sky" OR category == "verandah_inner".
      - For each candidate, count habitable rooms (bedroom/living/
        dining/kitchen) adjacent to it.
      - Detect if any single courtyard candidate has ≥ 4 adjacent
        habitable rooms.

    Failure mode honesty: if room category lacks an explicit
    "courtyard" label, the pattern is undetectable (returns False).
    Future v2 extension could analyze geometric topology to infer
    courtyard-shape void without explicit label.
    """
    rooms = _placed_rooms(c12_candidate)
    if len(rooms) < 5:  # ≥ 4 habitable + 1 courtyard
        return False

    adj = _adjacency_map(c14_report)
    if not adj:
        return False

    HABITABLE = {
        "bedroom", "master_bedroom", "living", "living_room",
        "dining", "dining_room", "kitchen", "study", "office",
        "guest_bedroom", "pooja_room", "pooja",
    }
    COURTYARD_CATS = {"courtyard", "open_to_sky", "verandah_inner",
                      "inner_courtyard", "atrium"}

    courtyard_ids = tuple(
        getattr(r, "room_id", "") for r in rooms
        if _category(r) in COURTYARD_CATS
    )
    if not courtyard_ids:
        return False

    habitable_ids = frozenset(
        getattr(r, "room_id", "") for r in rooms
        if _category(r) in HABITABLE
    )

    for cyd in courtyard_ids:
        neighbors = adj.get(cyd, frozenset())
        habitable_neighbors = neighbors & habitable_ids
        if len(habitable_neighbors) >= 4:
            return True
    return False


# =============================================================================
# Pattern 2: compact_incremental (IMPLEMENTED)
# =============================================================================

# Threshold constants pinned for B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
# audit traceability.
COMPACT_INCREMENTAL_AREA_THRESHOLD_M2: float = 55.74
"""Per UNCONVENTIONAL_PATTERN_NAMES docstring: 600 sqft ≈ 55.74 m².
LOCK-pinned for v1 (B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK)."""

COMPACT_INCREMENTAL_ROOM_COUNT_MIN: int = 4
"""Per UNCONVENTIONAL_PATTERN_NAMES docstring: room count ≥ 4."""


def _detect_compact_incremental(
    c12_candidate: object, c14_report: object,
) -> bool:
    """Per UNCONVENTIONAL_PATTERN_NAMES docstring:
    total carpet area < 600 sqft AND room count ≥ 4.

    Detects households that build incrementally on tight plots —
    walls of standard checks like "rooms below Neufert size targets"
    may over-trigger here because the family knowingly trades room
    size for room count under hard plot constraints.
    """
    rooms = _placed_rooms(c12_candidate)
    if len(rooms) < COMPACT_INCREMENTAL_ROOM_COUNT_MIN:
        return False
    total_area = sum(_area_m2(r) for r in rooms)
    return total_area > 0 and total_area < COMPACT_INCREMENTAL_AREA_THRESHOLD_M2


# =============================================================================
# Pattern 3: split_level_circulation (STUB — data-blocked at v1)
# =============================================================================

def _detect_split_level_circulation(
    c12_candidate: object, c14_report: object,
) -> bool:
    """STUB — data-blocked at v1.

    Detection requires per-room z-offset metadata. C12's PlacedRoom
    schema at v1 does NOT include z_offset (only width_m, depth_m,
    x_origin, y_origin). The v2 ProblemMetadata.floor_metadata field
    would need to extend with split-level room mapping for this to
    detect.

    Backlog: B-C15-PATTERN-SPLIT-LEVEL-DATA (v2 upstream extension
    required). Returns False at v1.

    Per Rule 11 vigorous self-analysis: a Pattern A bandage here would
    be to guess split-level from room-ID prefixes (e.g., "BR2_mezz")
    or comments. That would produce false positives on conventional
    layouts whose IDs happen to follow that convention. Honest
    behavior: return False; document the data dependency.
    """
    return False


# =============================================================================
# Pattern 4: ritual_procession (STUB — data-blocked at v1)
# =============================================================================

def _detect_ritual_procession(
    c12_candidate: object, c14_report: object,
) -> bool:
    """STUB — data-blocked at v1.

    Detection requires explicit ritual-category room labels (not just
    pooja_room, but ritual sequence markers like
    "ritual_entry_threshold", "ritual_transit_room",
    "inner_sanctum") + C14 graph-path analysis with semantic ritual
    flow.

    v1 C12 categorization recognizes pooja_room but not ritual
    sequence positions. Detection at v1 would either over-trigger on
    any-house-with-pooja or require Vastu-style heuristics that
    BuildemUp explicitly excludes per project decision.

    Backlog: B-C15-PATTERN-RITUAL-PROCESSION-DATA (v2 upstream
    extension required). Returns False at v1.
    """
    return False


# =============================================================================
# Pattern 5: multigenerational_segregation (STUB — data-blocked at v1)
# =============================================================================

def _detect_multigenerational_segregation(
    c12_candidate: object, c14_report: object,
) -> bool:
    """STUB — data-blocked at v1.

    Detection requires master-class vs. regular bedroom distinction in
    room categories. v1 C12 has "bedroom" and "master_bedroom"
    categories — only TWO master bedrooms in a layout would satisfy
    "≥ 2 master-class bedrooms separated by step-depth ≥ 3" but
    "master_bedroom × 2" is rare; multigen typically has
    "elders_suite" + "couples_suite" or similar that v1 doesn't model.

    Backlog: B-C15-PATTERN-MULTIGEN-SEGREGATION-DATA (v2 category
    refinement required). Returns False at v1.

    Per Rule 11: alternative implementation using ≥ 2 "master_bedroom"
    + step-depth ≥ 3 would generate false-positives on conventional
    NRI-style layouts that happen to label two suites as master.
    Honest behavior: return False; document the dependency.
    """
    return False


# =============================================================================
# Public detector entry point
# =============================================================================

def detect_unconventional_patterns(
    c12_candidate: object,
    c14_report: object,
) -> UnconventionalPatternHint:
    """Run all 5 v1 pattern detectors on the given candidate +
    upstream report. Returns an UnconventionalPatternHint.

    Per A7 Inv: detected=True iff at least one pattern fired.
    suspected_patterns sorted lex-ASC.

    Replay determinism: pure function of inputs; no clock/randomness.

    Caveat string: when patterns fire, names the data dependencies
    behind any stubbed-not-detected patterns so consumers know
    coverage is partial. Constructed at module level; identical
    across calls.
    """
    suspected: list[str] = []
    if _detect_courtyard_centered(c12_candidate, c14_report):
        suspected.append("courtyard_centered")
    if _detect_compact_incremental(c12_candidate, c14_report):
        suspected.append("compact_incremental")
    if _detect_split_level_circulation(c12_candidate, c14_report):
        suspected.append("split_level_circulation")
    if _detect_ritual_procession(c12_candidate, c14_report):
        suspected.append("ritual_procession")
    if _detect_multigenerational_segregation(c12_candidate, c14_report):
        suspected.append("multigenerational_segregation")

    # Inv: all suspected_patterns are valid names.
    for s in suspected:
        assert s in UNCONVENTIONAL_PATTERN_NAMES, (
            f"detector emitted invalid pattern name {s!r}"
        )

    suspected_sorted = tuple(sorted(suspected))
    detected = bool(suspected_sorted)

    if detected:
        caveat = (
            "One or more unconventional patterns detected. Standard "
            "checks may incorrectly flag this layout because the "
            "spatial program intentionally diverges from typical "
            "Indian residential patterns. UX should render affected "
            "checks with reduced confidence. Note: at v1, only "
            "'courtyard_centered' and 'compact_incremental' are "
            "actively detected; 'split_level_circulation', "
            "'ritual_procession', and 'multigenerational_segregation' "
            "are documented as data-blocked stubs per v2 upstream "
            "extension backlog."
        )
    else:
        caveat = ""

    # affected_check_ids at v1: empty for stubbed patterns; for
    # implemented patterns we conservatively flag none because the
    # specific UX policy of which checks reduce confidence per
    # pattern is itself a v2 question (B-C15-PATTERN-CHECK-INTERACTION).
    # For v1 LOCK we surface the pattern detection only.
    affected: tuple[str, ...] = ()

    return UnconventionalPatternHint(
        detected=detected,
        suspected_patterns=suspected_sorted,
        confidence_caveat=caveat,
        affected_check_ids=affected,
    )


__all__ = [
    "detect_unconventional_patterns",
    "COMPACT_INCREMENTAL_AREA_THRESHOLD_M2",
    "COMPACT_INCREMENTAL_ROOM_COUNT_MIN",
]
