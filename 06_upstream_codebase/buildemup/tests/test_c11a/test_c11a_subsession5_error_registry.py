"""
C11a Sub-session 5 — B-NEW-X: WeakSet error registry tests.

Per S39 critique walk F8 — the previous severity-classification audit
walked `cls.__subclasses__()` recursively, which (a) accumulated state
for the process lifetime and (b) returned subclasses in non-deterministic
order. B-NEW-X replaces this with a WeakSet auto-populated via
`__init_subclass__`. These tests verify:

  - Every concrete error class is registered at module load.
  - `iter_registered_errors()` returns deterministic (sorted) order.
  - Dynamically-created subclasses register on definition.
  - Dynamically-created subclasses drop out after GC when their last
    strong reference is released (the property that fixes the test-
    leak issue).
"""
from __future__ import annotations

import gc
from typing import ClassVar

from buildemup.components.c11a.errors import (
    BatchAllNonBaseFailedError,
    DeepMutationApplicationError,
    DeepMutationPurityContractError,
    InvariantViolationError,
    MutationApplicationError,
    OperatorRegistryError,
    PendingUpstreamPredicateError,
    PerCandidateError,
    SeverityClassificationAuditError,
    TopologyInvalidError,
    TopologyMutationError,
    iter_registered_errors,
)


# =============================================================================
# Module-load registration
# =============================================================================


def test_registry_includes_topology_mutation_error_base() -> None:
    """The base class itself is registered."""
    registry = iter_registered_errors()
    assert TopologyMutationError in registry


def test_registry_includes_all_v1_subclasses() -> None:
    """Every v1.0 LOCKED concrete error subclass is registered at
    module load."""
    registry = set(iter_registered_errors())
    for cls in (
        PerCandidateError,
        TopologyInvalidError,
        MutationApplicationError,
        DeepMutationApplicationError,
        BatchAllNonBaseFailedError,
        OperatorRegistryError,
        DeepMutationPurityContractError,
        PendingUpstreamPredicateError,
        SeverityClassificationAuditError,
        InvariantViolationError,
    ):
        assert cls in registry, f"{cls.__qualname__} missing from registry"


# =============================================================================
# Deterministic ordering
# =============================================================================


def test_iter_registered_errors_returns_sorted() -> None:
    """Output is sorted by `module.qualname` for replay determinism.

    WeakSet iteration order is intrinsically non-deterministic; the
    explicit sort in `iter_registered_errors()` makes audit output
    reproducible across runs."""
    registry = iter_registered_errors()
    qualnames = [f"{c.__module__}.{c.__qualname__}" for c in registry]
    assert qualnames == sorted(qualnames)


def test_iter_registered_errors_returns_tuple() -> None:
    """Tuple return — callers can index, len(), and iterate without
    surprise mutation semantics."""
    registry = iter_registered_errors()
    assert isinstance(registry, tuple)


# =============================================================================
# Dynamic subclass registration + GC drop-out
# =============================================================================


def test_dynamic_subclass_registers_on_definition() -> None:
    """A subclass defined at runtime appears in the registry as soon
    as its class statement executes — via `__init_subclass__`."""
    before = set(iter_registered_errors())

    class _DynamicErr(TopologyMutationError):
        severity_tier: ClassVar[str] = "per_candidate"

    after = set(iter_registered_errors())
    assert _DynamicErr in after
    assert _DynamicErr not in before


def test_dynamic_subclass_dropped_after_gc() -> None:
    """When the last strong reference to a subclass is released, the
    WeakSet drops it on next GC pass.

    This is the property B-NEW-X exists for: the previous
    `__subclasses__()` walk would retain the dropped class for the
    process lifetime, accumulating audit state across test runs.
    """
    class _Ephemeral(TopologyMutationError):
        severity_tier: ClassVar[str] = "per_candidate"

    assert _Ephemeral in iter_registered_errors()

    # Drop the local ref + force GC.
    qualname = f"{_Ephemeral.__module__}.{_Ephemeral.__qualname__}"
    del _Ephemeral
    gc.collect()

    # The class should no longer be in the registry.
    remaining_qualnames = {
        f"{c.__module__}.{c.__qualname__}"
        for c in iter_registered_errors()
    }
    assert qualname not in remaining_qualnames


def test_grandchild_subclass_registers() -> None:
    """Subclasses-of-subclasses also register (every class in the
    chain triggers __init_subclass__)."""
    class _Mid(TopologyMutationError):
        severity_tier: ClassVar[str] = "per_candidate"

    class _Leaf(_Mid):
        severity_tier: ClassVar[str] = "per_candidate"

    registry = set(iter_registered_errors())
    assert _Mid in registry
    assert _Leaf in registry

    del _Leaf, _Mid
    gc.collect()


# =============================================================================
# Severity audit reads the registry — confirm wiring
# =============================================================================


def test_severity_audit_uses_registry() -> None:
    """The severity classification audit pulls from
    iter_registered_errors() — verified by happy-path pass with the
    full v1.0 registry."""
    from buildemup.components.c11a.phase0 import (
        validate_severity_classification_audit,
    )
    validate_severity_classification_audit()
