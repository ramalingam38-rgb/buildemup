"""S55 Batch 3 — C13 v1.x polish closures.

Three items from the S44 v1.x-polish rollup:

  B-C13-INVARIANT-TAXONOMY-GROUPING
      Categorize C13's invariants into structural / soft-quality /
      provenance bands so a critique walker can read "Inv 7 is
      structural, Inv 11 is soft-quality" without re-deriving the
      taxonomy each time. CRITICAL per S44 rollup ("cognitive overload
      flagged 3 walks deep").

  B-C13-ADVERSARIAL-INTEGRATION-CORPUS
      Reserved-set generators for adversarial integration testing —
      narrow-plot/odd-aspect/large-N variants. Walk #6 surfaced the
      gap; this file is the loading point for the future corpus.

  B-C13-WINDOW-AVOIDANCE
      `WindowAvoidanceAdvisory` — door-selection advisory flagging
      candidate door positions that would block a documented window.
      Stays advisory (no rejection) until upstream window data is
      reliable post-LOCK per walk #4 escalation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────
# B-C13-INVARIANT-TAXONOMY-GROUPING (CRITICAL per S44 walk #3)
# ─────────────────────────────────────────────────────────────────────────


class InvariantClass(str, Enum):
    """Classification of a C13 invariant.

    STRUCTURAL: must-hold geometric / topological property (no door
                inside a wet zone perimeter, no two doors on the same
                edge segment, etc.). Failure = bug.
    SOFT_QUALITY: heuristic preference (prefer external envelope for
                  entry, prefer wider edge segments for utility doors).
                  Failure = degraded ranking, not a halt.
    PROVENANCE: book-keeping invariant about output shape / signature /
                tracing. Failure = audit-trail bug.
    UPSTREAM_CONTRACT: invariant about C12 input shape (e.g., shared
                       edges sorted lex-ASC). Failure = upstream bug.
    """
    STRUCTURAL = "structural"
    SOFT_QUALITY = "soft_quality"
    PROVENANCE = "provenance"
    UPSTREAM_CONTRACT = "upstream_contract"


# Canonical map: invariant id → class. Populated for the 13 v1.0
# invariants in C13 SPEC § 12. Future C13 v1.x additions add entries.
C13_INVARIANT_TAXONOMY: dict[str, InvariantClass] = {
    "Inv 1": InvariantClass.STRUCTURAL,         # door inside room rectangle
    "Inv 2": InvariantClass.STRUCTURAL,         # door clear-width ≥ NBC min
    "Inv 3": InvariantClass.STRUCTURAL,         # door on a single edge segment
    "Inv 4": InvariantClass.STRUCTURAL,         # no two doors on same edge
    "Inv 5": InvariantClass.SOFT_QUALITY,       # entry-room preference
    "Inv 6": InvariantClass.SOFT_QUALITY,       # privacy-aware door placement
    "Inv 7": InvariantClass.PROVENANCE,         # canonical lex-ASC ordering
    "Inv 8": InvariantClass.PROVENANCE,         # frozen dataclass / replay
    "Inv 9": InvariantClass.UPSTREAM_CONTRACT,  # C12 SharedEdge sorted lex
    "Inv 10": InvariantClass.UPSTREAM_CONTRACT, # C12 SharedEdge non-empty
    "Inv 11": InvariantClass.SOFT_QUALITY,      # multi-door coordination
    "Inv 12": InvariantClass.STRUCTURAL,        # door swing arc inside room
    "Inv 13": InvariantClass.PROVENANCE,        # trace_id continuity
}


def classify_invariant(invariant_id: str) -> Optional[InvariantClass]:
    """Return the InvariantClass for an id, or None if not registered."""
    return C13_INVARIANT_TAXONOMY.get(invariant_id)


def invariants_by_class(cls: InvariantClass) -> Tuple[str, ...]:
    """Return canonical lex-ASC tuple of invariant ids in the given class."""
    return tuple(
        sorted(k for k, v in C13_INVARIANT_TAXONOMY.items() if v == cls)
    )


# ─────────────────────────────────────────────────────────────────────────
# B-C13-ADVERSARIAL-INTEGRATION-CORPUS (walk #6)
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AdversarialCorpusEntry:
    """One adversarial integration-test fixture.

    Reserved-set entries — walks #6's recommendation was a curated
    set of named adversarial cases (narrow plot, odd aspect, large N,
    cross-component cascade triggers, etc.). Each entry is a self-
    describing recipe the test harness can replay.
    """
    case_id: str
    description: str
    plot_width_m: float
    plot_depth_m: float
    room_count: int
    expected_failure_mode: Optional[str] = None   # None = expected to pass


C13_ADVERSARIAL_CORPUS: Tuple[AdversarialCorpusEntry, ...] = (
    AdversarialCorpusEntry(
        case_id="ADV-001-narrow-plot",
        description="3m × 30m strip plot — corridor tighter than NBC min.",
        plot_width_m=3.0,
        plot_depth_m=30.0,
        room_count=6,
        expected_failure_mode="CorridorTooNarrowError",
    ),
    AdversarialCorpusEntry(
        case_id="ADV-002-odd-aspect",
        description="20m × 4m ribbon plot — most candidates fail VAV.",
        plot_width_m=20.0,
        plot_depth_m=4.0,
        room_count=8,
        expected_failure_mode=None,  # should produce degraded but valid output
    ),
    AdversarialCorpusEntry(
        case_id="ADV-003-large-N",
        description="15m × 25m with 20 rooms — slicing-tree pruning stress.",
        plot_width_m=15.0,
        plot_depth_m=25.0,
        room_count=20,
        expected_failure_mode=None,
    ),
    AdversarialCorpusEntry(
        case_id="ADV-004-zero-shared-edge",
        description="All rooms placed against envelope; no internal edges.",
        plot_width_m=12.0,
        plot_depth_m=12.0,
        room_count=4,
        expected_failure_mode=None,
    ),
    AdversarialCorpusEntry(
        case_id="ADV-005-staircase-island",
        description="Staircase placed mid-envelope forcing corridor loop.",
        plot_width_m=10.0,
        plot_depth_m=15.0,
        room_count=10,
        expected_failure_mode=None,
    ),
)


def adversarial_corpus_case_ids() -> Tuple[str, ...]:
    return tuple(e.case_id for e in C13_ADVERSARIAL_CORPUS)


# ─────────────────────────────────────────────────────────────────────────
# B-C13-WINDOW-AVOIDANCE (walk #4 — escalated to v1.x post-LOCK fast-follow)
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WindowAvoidanceAdvisory:
    """Advisory raised when a chosen door position would obstruct a
    documented window.

    Stays advisory (no rejection) until upstream window data is reliable
    in production. The C13 door-selection layer attaches one of these
    per (door_id, blocked_window_id) pair so the renderer can surface
    a UI hint, and downstream visualizers can highlight the conflict.
    """
    door_id: str
    blocked_window_id: str
    severity: str          # "informational" | "advisory" | "blocking"
    note: str

    def __post_init__(self) -> None:
        if not self.door_id:
            raise ValueError("WindowAvoidanceAdvisory.door_id must be non-empty.")
        if not self.blocked_window_id:
            raise ValueError("WindowAvoidanceAdvisory.blocked_window_id must be non-empty.")
        if self.severity not in ("informational", "advisory", "blocking"):
            raise ValueError(
                f"WindowAvoidanceAdvisory.severity must be one of "
                f"informational|advisory|blocking; got {self.severity!r}."
            )


__all__ = [
    # B-C13-INVARIANT-TAXONOMY-GROUPING
    "InvariantClass",
    "C13_INVARIANT_TAXONOMY",
    "classify_invariant",
    "invariants_by_class",
    # B-C13-ADVERSARIAL-INTEGRATION-CORPUS
    "AdversarialCorpusEntry",
    "C13_ADVERSARIAL_CORPUS",
    "adversarial_corpus_case_ids",
    # B-C13-WINDOW-AVOIDANCE
    "WindowAvoidanceAdvisory",
]
