"""
BuildemUp — Component 15 — Check Registry
============================================

Per C15 SPEC v0.2 LOCKED § 3 Phase ρ + Inv P4 (every emitted
check_id belongs to the registered set) + Inv P12 (every registered
check produces exactly one outcome).

The registry is an ordered, immutable collection of Check instances
keyed by check_id. It enforces:

- check_id uniqueness within the registry (Inv P4 enabler — if a
  check_id were duplicated, the orchestrator couldn't decide which
  Check to dispatch on).
- check_id sort order is lex-ASC (Inv P2 + P3 — replay determinism
  depends on deterministic iteration).
- Registration is exhaustive at module load; the registry is
  closed after `build_registry` returns. Subsequent attempts to
  mutate raise CheckRegistryError.

The registry is built by a top-level `build_registry()` function
that imports every dimension module and registers its checks. At
each sub-session we extend the building call to include the new
dimension. Pre-LOCK the registry is mutable across versions (governed
by `C15_CHECK_REGISTRY_VERSION` bumps); at LOCK the registry
contents are frozen.

Sub-2 ships the registry mechanism + 4 dim-1 checks. Dimensions
2, 3, 5, 6 land in Sub-3+.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from .errors import CheckRegistryError
from .protocol import Check


# =============================================================================
# CheckRegistry — immutable ordered container
# =============================================================================

@dataclass(frozen=True)
class CheckRegistry:
    """An immutable, lex-ASC-sorted collection of Check instances.

    Per Inv P2/P3/P4/P12. Constructed via `build_registry()`; cannot
    be mutated after construction (frozen dataclass + tuple field).

    Fields:
      checks: tuple of Check, lex-ASC by check_id. Iteration order
          is the canonical Phase ρ traversal order.
      _check_id_set: derived frozenset for O(1) membership probes.
          Underscored because callers should use `contains()` /
          `iter()` rather than poking the underlying set.

    Methods:
      iter() → Iterator[Check]
      contains(check_id) → bool
      get(check_id) → Check     (raises CheckRegistryError if missing)
      ids() → tuple[str, ...]   (canonical lex-ASC tuple)
      __len__()

    Why frozenset for _check_id_set instead of recomputing from
    checks: lookup is O(1) instead of O(N), and the orchestrator
    will probe membership in inner loops (per-candidate × per-check).
    """
    checks: tuple[Check, ...]
    _check_id_set: frozenset[str] = field(repr=False)

    def __post_init__(self) -> None:
        # checks must be a tuple (frozen-dataclass already prevents
        # mutation of the field itself, but we defend against the
        # caller passing a list which would defeat hashability).
        if not isinstance(self.checks, tuple):
            raise TypeError(
                f"CheckRegistry.checks must be a tuple; "
                f"got {type(self.checks)}"
            )

        ids = [c.check_id for c in self.checks]

        # Sort discipline: lex-ASC.
        if ids != sorted(ids):
            raise CheckRegistryError(
                f"CheckRegistry.checks must be sorted lex-ASC by "
                f"check_id (Inv P2/P3 replay determinism); got order "
                f"{ids}"
            )

        # Uniqueness discipline.
        if len(set(ids)) != len(ids):
            duplicates = [cid for cid in ids if ids.count(cid) > 1]
            raise CheckRegistryError(
                f"CheckRegistry.checks contains duplicate check_id(s) "
                f"{set(duplicates)}; check_id is the registry key "
                f"and must be unique (Inv P4 enabler)."
            )

        # _check_id_set must agree with checks.
        if self._check_id_set != frozenset(ids):
            raise CheckRegistryError(
                f"CheckRegistry._check_id_set mismatch with checks; "
                f"_check_id_set={self._check_id_set} vs derived={frozenset(ids)}"
            )

    def __iter__(self) -> Iterator[Check]:
        return iter(self.checks)

    def __len__(self) -> int:
        return len(self.checks)

    def contains(self, check_id: str) -> bool:
        """True iff check_id is registered."""
        return check_id in self._check_id_set

    def get(self, check_id: str) -> Check:
        """Return the registered Check with this check_id. Raises
        CheckRegistryError if not registered (Inv P4)."""
        for c in self.checks:
            if c.check_id == check_id:
                return c
        raise CheckRegistryError(
            f"check_id {check_id!r} is not registered; per Inv P4, "
            f"only registered check_ids may be emitted. Registered: "
            f"{sorted(self._check_id_set)}"
        )

    def ids(self) -> tuple[str, ...]:
        """Return registered check_ids as a canonical lex-ASC tuple."""
        return tuple(c.check_id for c in self.checks)


# =============================================================================
# Registry construction
# =============================================================================

def make_registry(checks: Iterable[Check]) -> CheckRegistry:
    """Build a CheckRegistry from an iterable of Check instances.

    Sorts lex-ASC by check_id (caller order is irrelevant). Validates
    via CheckRegistry.__post_init__.

    Each Check must declare a non-empty check_id (string), a valid
    dimension_id (1..10), an epistemic_kind, data_dependencies, and
    cultural_scope. The Check protocol does not enforce these at
    runtime (Protocol is structural); CheckRegistry verifies the
    invariants that affect dispatch.

    Returns: CheckRegistry. Raises: CheckRegistryError on duplicate
    check_ids or unsortable input.
    """
    check_list = list(checks)
    # Defensive: every check must declare these attributes. Protocol
    # is structural; mistakes at the dataclass-definition level would
    # show up here.
    for c in check_list:
        if not hasattr(c, "check_id") or not isinstance(c.check_id, str):
            raise CheckRegistryError(
                f"Registry entry missing check_id or check_id not str: "
                f"{c!r}"
            )
        if not c.check_id:
            raise CheckRegistryError(
                f"Registry entry has empty check_id: {c!r}"
            )
        if not hasattr(c, "dimension_id") or not isinstance(c.dimension_id, int):
            raise CheckRegistryError(
                f"Registry entry missing dimension_id or not int: "
                f"check_id={c.check_id!r}"
            )

    sorted_checks = sorted(check_list, key=lambda c: c.check_id)
    return CheckRegistry(
        checks=tuple(sorted_checks),
        _check_id_set=frozenset(c.check_id for c in sorted_checks),
    )


def build_registry() -> CheckRegistry:
    """Build the canonical C15 registry — all 10 dimensions.

    Sub-2 shipped dim 1 only. The full build (post-completion) covers
    all 10 dimensions = 41 checks total. The data envelope:
      - Dim 1: 2 RUNNABLE + 2 DEFERRED (4)
      - Dim 2: 5 RUNNABLE (5)
      - Dim 3: 4 RUNNABLE (4)
      - Dim 4: 4 DEFERRED  (4)
      - Dim 5: 5 RUNNABLE (5)
      - Dim 6: 1 RUNNABLE + 3 DEFERRED (4)
      - Dim 7: 3 RUNNABLE (partial — need floor_metadata) + 1 DEFERRED (4)
      - Dim 8: 4 DEFERRED (4)
      - Dim 9: 4 DEFERRED (4)
      - Dim 10: 3 DEFERRED (3)
    Total: 41 checks; ~20 RUNNABLE, ~21 DEFERRED.
    """
    from .dimensions.dim01_no_wasted_space import REGISTERED_CHECKS as DIM01
    from .dimensions.dim02_room_sizes import REGISTERED_CHECKS as DIM02
    from .dimensions.dim03_logical_flow import REGISTERED_CHECKS as DIM03
    from .dimensions.dim05_privacy import REGISTERED_CHECKS as DIM05
    from .dimensions.dim06_no_bottlenecks import REGISTERED_CHECKS as DIM06
    from .dimensions.dim07_first_floor_living import REGISTERED_CHECKS as DIM07
    from .dimensions.dim_deferred import (
        DIM04_REGISTERED_CHECKS as DIM04,
        DIM08_REGISTERED_CHECKS as DIM08,
        DIM09_REGISTERED_CHECKS as DIM09,
        DIM10_REGISTERED_CHECKS as DIM10,
    )

    all_checks: list[Check] = []
    all_checks.extend(DIM01)
    all_checks.extend(DIM02)
    all_checks.extend(DIM03)
    all_checks.extend(DIM04)
    all_checks.extend(DIM05)
    all_checks.extend(DIM06)
    all_checks.extend(DIM07)
    all_checks.extend(DIM08)
    all_checks.extend(DIM09)
    all_checks.extend(DIM10)

    return make_registry(all_checks)


__all__ = [
    "CheckRegistry",
    "make_registry",
    "build_registry",
]
