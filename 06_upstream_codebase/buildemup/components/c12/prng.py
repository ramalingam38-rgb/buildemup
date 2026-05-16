"""
BuildemUp — Component 12 — PRNG for tie-break
==============================================

Per C12 SPEC v1.0 LOCKED v0.2-A4 canonicalization rule #7:

> PRNG: only used for tie-break on equal-score placements; seeded
> from config.master_seed; replay-tested per Inv 7.

The PRNG is INTENTIONALLY a single-purpose tool with a narrow API.
v1 uses Python's ``random.Random`` because:

1. It supports deterministic seed → same output sequence across runs.
2. It's pure-Python and thus immune to NumPy/BLAS FP variation that
   could break Inv 7 byte-equal replay across environments.
3. The use case (tie-break index selection) doesn't need NumPy's
   array-RNG capabilities.

DO NOT USE for:
- Coordinate jitter (would break Inv 7)
- Algorithmic randomization (slicing-tree is deterministic by design)
- Stochastic search (B-C12-CSP-PLACEMENT post-v1 territory)
"""
from __future__ import annotations

import random
from typing import Sequence, TypeVar

T = TypeVar("T")


class TieBreakPRNG:
    """Wraps ``random.Random`` with a narrow tie-break-only API.

    Per v0.2-A4 rule #7. Calling code MUST seed this from
    ``config.master_seed`` for deterministic replay.

    Methods are intentionally limited; expanding the API requires
    spec amendment because adding randomization channels affects
    Inv 7 byte-equal replay testing scope.
    """

    def __init__(self, master_seed: int) -> None:
        self._rng = random.Random(master_seed)
        self._master_seed = master_seed

    @property
    def master_seed(self) -> int:
        """The seed this PRNG was initialized with (for provenance)."""
        return self._master_seed

    def tie_break_choice(self, candidates: Sequence[T]) -> T:
        """Deterministically choose one item from a sequence of
        equally-good candidates.

        Uses an INDEX-based selection (not Random.choice directly)
        because index sampling is determinism-stable across Python
        versions in a way that Random.choice is not (its internal
        implementation has changed in some Python releases).
        """
        if not candidates:
            raise ValueError(
                "TieBreakPRNG.tie_break_choice requires at least one candidate."
            )
        if len(candidates) == 1:
            return candidates[0]
        idx = self._rng.randrange(0, len(candidates))
        return candidates[idx]


__all__ = ["TieBreakPRNG"]
