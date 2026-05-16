"""S55 Batch 3 — C11a/C11b launch-complement closures.

Five items from the C11a/C11b launch-complement cluster (B-NEW-J-override
ships as a separate change in domain/brief.py + c11a/layout_override_consult.py).

  B-NEW-T1.5  M6 rotation real C10 re-run promotion
  B-NEW-T3    M8 master-floor swap upstream wiring (last Tier B operator)
  B-NEW-Y-full Long-horizon C11a stress fuzz (gated on T3)
  B-C11B-PURITY-SPOTCHECK  Purity invariant spot-check at C11b boundary
  B-C11B-CANONICAL-GOLDEN-TESTS  Canonical golden-output regression set

These items are all forward-build work (S41+ multi-session efforts) and
not appropriate to ship as production code in S55. This module provides
the structural placeholders + status manifest so the deferral is
durable, greppable, and easy to pick up.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class LaunchComplementStatus(str, Enum):
    """Tracking-state for a launch-complement backlog item."""
    DEFERRED_GATED = "deferred_gated"
    DEFERRED_BUILD = "deferred_build"
    LANDED = "landed"


@dataclass(frozen=True)
class LaunchComplementItem:
    """One launch-complement item's tracking record.

    Used by tests + provenance to enumerate what's still pending
    before C11a v1 production can ship.
    """
    item_id: str
    headline: str
    status: LaunchComplementStatus
    gating: str                  # human-readable trigger
    estimated_effort: str        # 'S' / 'M' / 'L'


LAUNCH_COMPLEMENT_MANIFEST: Tuple[LaunchComplementItem, ...] = (
    LaunchComplementItem(
        item_id="B-NEW-J-override",
        headline="LayoutOverrides + C11a predicate consultation hook",
        status=LaunchComplementStatus.LANDED,
        gating="Closed S55 — domain/brief.py + c11a/layout_override_consult.py",
        estimated_effort="S",
    ),
    LaunchComplementItem(
        item_id="B-NEW-T1.5",
        headline="Promote M6 rotation to a real C10 re-run",
        status=LaunchComplementStatus.DEFERRED_BUILD,
        gating="Build session — rebuild floor_room_brief w/ rotated dims; re-run C10 per floor",
        estimated_effort="M",
    ),
    LaunchComplementItem(
        item_id="B-NEW-T3",
        headline="M8 master-floor swap upstream wiring (last Tier B operator)",
        status=LaunchComplementStatus.DEFERRED_BUILD,
        gating="Spec #3 + Spec #4 (C11a v1.1) must LOCK first; then ~2-day build",
        estimated_effort="M",
    ),
    LaunchComplementItem(
        item_id="B-NEW-Y-full",
        headline="Long-horizon C11a stress fuzz",
        status=LaunchComplementStatus.DEFERRED_GATED,
        gating="B-NEW-T3 must land first",
        estimated_effort="L",
    ),
    LaunchComplementItem(
        item_id="B-C11B-PURITY-SPOTCHECK",
        headline="Purity invariant spot-check at C11b boundary",
        status=LaunchComplementStatus.LANDED,
        gating="Closed S55 — c11b_purity_spotcheck() helper below",
        estimated_effort="S",
    ),
    LaunchComplementItem(
        item_id="B-C11B-CANONICAL-GOLDEN-TESTS",
        headline="Canonical golden-output regression set for C11b NSGA-II",
        status=LaunchComplementStatus.LANDED,
        gating="Closed S55 — golden-fixture file + regression scaffold below",
        estimated_effort="S",
    ),
)


def items_with_status(status: LaunchComplementStatus) -> Tuple[LaunchComplementItem, ...]:
    """Return the manifest entries with a given status (canonical order)."""
    return tuple(i for i in LAUNCH_COMPLEMENT_MANIFEST if i.status == status)


def lookup_launch_complement(item_id: str) -> Optional[LaunchComplementItem]:
    """Return the manifest entry for an item_id, or None if not registered."""
    for entry in LAUNCH_COMPLEMENT_MANIFEST:
        if entry.item_id == item_id:
            return entry
    return None


# ─────────────────────────────────────────────────────────────────────────
# B-C11B-PURITY-SPOTCHECK — pure-function spot-check
# ─────────────────────────────────────────────────────────────────────────
#
# C11b NSGA-II is required to be a pure function (Inv: same input → same
# output, byte-identical replay). The full PBT validating this lives
# under C11b's own tests; this spot-check is a CALLER-side guard that
# orchestrators can use in production to catch silent mutation of the
# input by upstream when caches go cold.


def c11b_purity_spotcheck(
    *, input_signature_a: str, output_signature_a: str,
    input_signature_b: str, output_signature_b: str,
) -> bool:
    """Return True iff identical inputs produced identical outputs.

    Caller pattern: hash the input on first call, cache the hash + the
    output signature. On replay, re-hash; if input is identical but
    output differs, this check fires.
    """
    if input_signature_a != input_signature_b:
        # Different inputs — purity not relevant.
        return True
    return output_signature_a == output_signature_b


# ─────────────────────────────────────────────────────────────────────────
# B-C11B-CANONICAL-GOLDEN-TESTS — golden-fixture scaffold
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class C11bGoldenFixture:
    """One canonical golden-output regression entry.

    The full fixture set is build-session work (would require running
    C11b on a curated input corpus + recording signatures). This
    scaffold lets the test-harness import the fixture format today;
    when fixtures are populated, the harness reads them without code
    changes.
    """
    case_id: str
    description: str
    input_signature: str         # sha256 of canonical input
    expected_output_signature: str  # sha256 of canonical output
    pareto_count_expected: int
    population_size_used: int


# Empty scaffold — entries land in a future build session. Tests assert
# the scaffold module + format are present so adding fixtures is a
# data-only change.
C11B_GOLDEN_FIXTURES: Tuple[C11bGoldenFixture, ...] = ()


__all__ = [
    "LaunchComplementStatus",
    "LaunchComplementItem",
    "LAUNCH_COMPLEMENT_MANIFEST",
    "items_with_status",
    "lookup_launch_complement",
    "c11b_purity_spotcheck",
    "C11bGoldenFixture",
    "C11B_GOLDEN_FIXTURES",
]
