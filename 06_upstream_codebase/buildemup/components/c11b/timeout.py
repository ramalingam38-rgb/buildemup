"""
BuildemUp — Component 11b — per-topology wall-clock budget
=============================================================

Per SPEC v1.1 LOCKED § 0.4 (D-TO-1/2/3) + Inv 27.

The budget check is at GENERATION BOUNDARIES, not inside individual
operations. A single pathological generation can still overrun the
budget, but the topology exits at the next boundary.

Out of scope at v1: per-evaluation timeout, intra-generation
watchdog. Filed as B-C11B-TIMEOUT-V2 + B-C11B-TIMEOUT-COMPLEXITY.
"""
from __future__ import annotations

import time

from buildemup.components.c11b.errors import PerTopologyTimeoutError


class WallclockBudget:
    """Lightweight per-topology budget tracker. Constructed at topology
    start; ``check(gen, max_gen)`` is called at each generation boundary.

    Also exposes ``record_generation_seconds`` for the telemetry
    pipeline's ``longest_generation_seconds`` calculation.
    """

    def __init__(self, budget_seconds: float, topology_index: int) -> None:
        self._budget = budget_seconds
        self._topology_index = topology_index
        self._start = time.perf_counter()
        self._longest_gen_seconds = 0.0
        self._last_gen_start = self._start

    def elapsed(self) -> float:
        return time.perf_counter() - self._start

    def check(self, gen: int, max_gen: int) -> None:
        """Raise ``PerTopologyTimeoutError`` if elapsed > budget."""
        elapsed = self.elapsed()
        if elapsed > self._budget:
            raise PerTopologyTimeoutError(
                f"C11b: topology_index={self._topology_index} exceeded "
                f"wallclock budget {self._budget:.1f}s at generation "
                f"{gen}/{max_gen}; elapsed {elapsed:.2f}s."
            )

    def open_generation(self) -> None:
        """Mark the start of a new generation for the longest-gen
        telemetry."""
        self._last_gen_start = time.perf_counter()

    def close_generation(self) -> None:
        """Mark the end of a generation; updates the longest-gen
        telemetry."""
        gen_seconds = time.perf_counter() - self._last_gen_start
        if gen_seconds > self._longest_gen_seconds:
            self._longest_gen_seconds = gen_seconds

    @property
    def longest_generation_seconds(self) -> float:
        return self._longest_gen_seconds


__all__ = [
    "WallclockBudget",
]
