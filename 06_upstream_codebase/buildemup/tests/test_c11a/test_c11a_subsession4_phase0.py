"""
C11a Sub-session 4 tests — Phase 0 startup validation.

Per spec § 3 Phase 0 + Inv 24/25/27 + F-v4-5: validate_upstream_purity_contract,
enforce_pending_predicate_sunset, validate_severity_classification_audit.
"""
from __future__ import annotations

from typing import ClassVar

import pytest

from buildemup.components.c11a import (
    DeepMutationPurityContractError,
    PendingUpstreamPredicateError,
    SeverityClassificationAuditError,
    enforce_pending_predicate_sunset,
    run_phase_0_startup_validation,
    validate_severity_classification_audit,
    validate_upstream_purity_contract,
)


# =============================================================================
# Combined entry point — happy path at v1.0 LOCK
# =============================================================================


def test_run_phase_0_startup_validation_passes_at_v1_lock() -> None:
    """At v1.0 LOCK time, all four sub-validators pass."""
    run_phase_0_startup_validation()


def test_run_phase_0_startup_validation_idempotent() -> None:
    """Calling twice is safe."""
    run_phase_0_startup_validation()
    run_phase_0_startup_validation()


# =============================================================================
# validate_upstream_purity_contract (Inv 25)
# =============================================================================


def test_purity_contract_passes_at_v1_lock() -> None:
    """Every UPSTREAM_PURITY_REGISTRY entry resolves at runtime."""
    validate_upstream_purity_contract()


def test_purity_contract_raises_on_missing_component(monkeypatch) -> None:
    """If registry references an unknown component_id, raise."""
    from buildemup.components.c11a import schema as s
    from buildemup.components.c11a.schema import PurityAttestation

    bogus_registry = (
        PurityAttestation(
            component_id="C99",   # invalid
            entry_point="foo",
            purity_class="pure",
            attested_by="C99",
            attested_at_kb_version="v0",
        ),
    )
    monkeypatch.setattr(s, "UPSTREAM_PURITY_REGISTRY", bogus_registry)
    # Also patch the imported reference inside phase0.
    from buildemup.components.c11a import phase0 as p
    monkeypatch.setattr(p, "UPSTREAM_PURITY_REGISTRY", bogus_registry)

    with pytest.raises(DeepMutationPurityContractError, match="unknown"):
        validate_upstream_purity_contract()


def test_purity_contract_raises_on_unresolvable_entry_point(monkeypatch) -> None:
    from buildemup.components.c11a import phase0 as p
    from buildemup.components.c11a.schema import PurityAttestation

    bogus = (
        PurityAttestation(
            component_id="C7",
            entry_point="DefinitelyNotARealClass.method",
            purity_class="pure",
            attested_by="C7",
            attested_at_kb_version="v0",
        ),
    )
    monkeypatch.setattr(p, "UPSTREAM_PURITY_REGISTRY", bogus)
    with pytest.raises(DeepMutationPurityContractError, match="not resolvable"):
        validate_upstream_purity_contract()


# =============================================================================
# enforce_pending_predicate_sunset (Inv 24 LOCK gate)
# =============================================================================


def test_sunset_passes_at_v1_lock() -> None:
    """At v1.0 LOCK: pending_count=0, waiver_count=0 → both clauses pass."""
    enforce_pending_predicate_sunset()


def test_sunset_raises_on_pending_with_no_waivers(monkeypatch) -> None:
    """A pending predicate with no waiver → LOCK gate violation."""
    from buildemup.components.c11a import phase0 as p
    monkeypatch.setattr(p, "pending_upstream_predicate_count", lambda: 1)
    monkeypatch.setattr(p, "WAIVER_REGISTRY", ())
    with pytest.raises(PendingUpstreamPredicateError, match="pending_upstream"):
        enforce_pending_predicate_sunset()


def test_sunset_passes_when_waivers_match_pending(monkeypatch) -> None:
    """1 pending + 1 waiver → clause 1 passes."""
    from buildemup.components.c11a import phase0 as p
    monkeypatch.setattr(p, "pending_upstream_predicate_count", lambda: 1)
    # Synthetic waiver tuple — only length matters per Inv 24 clause.
    monkeypatch.setattr(p, "WAIVER_REGISTRY", ("w1",))
    enforce_pending_predicate_sunset()


def test_sunset_raises_on_too_many_waivers(monkeypatch) -> None:
    """4 waivers exceeds the v1.0 cap of 3."""
    from buildemup.components.c11a import phase0 as p
    monkeypatch.setattr(p, "pending_upstream_predicate_count", lambda: 4)
    monkeypatch.setattr(p, "WAIVER_REGISTRY", ("w1", "w2", "w3", "w4"))
    with pytest.raises(PendingUpstreamPredicateError, match="exceeds the v1.0 cap"):
        enforce_pending_predicate_sunset()


# =============================================================================
# validate_severity_classification_audit (Inv 27 / F-v4-5)
# =============================================================================


def test_severity_audit_passes_for_c11a_errors() -> None:
    """Every C11a error class carries a valid severity_tier ClassVar."""
    validate_severity_classification_audit()


def test_severity_audit_raises_on_missing_tier() -> None:
    """Inject a synthetic TopologyMutationError subclass without
    severity_tier — audit should detect it via the registry.

    Per B-NEW-X: the synthetic subclass auto-registers via
    __init_subclass__ at class-definition time (inside this function).
    Once the test function returns the class becomes unreachable;
    the WeakSet drops the entry on next GC pass. Subsequent tests of
    the happy-path validator pass without explicit cleanup — this is
    the WeakSet correctness fix from B-NEW-X.
    """
    import gc
    from buildemup.components.c11a.errors import TopologyMutationError

    class _NoSeverityTier(TopologyMutationError):
        pass

    _NoSeverityTier.severity_tier = None  # type: ignore[assignment]
    with pytest.raises(SeverityClassificationAuditError):
        validate_severity_classification_audit()

    # Drop the local ref + force GC so the WeakSet drops it before the
    # next test's happy-path audit runs.
    del _NoSeverityTier
    gc.collect()


def test_severity_audit_raises_on_invalid_tier_value() -> None:
    """Inject a subclass with severity_tier='unknown' — invalid value.

    Same WeakSet GC-cleanup pattern as above.
    """
    import gc
    from buildemup.components.c11a.errors import TopologyMutationError

    class _BadTierError(TopologyMutationError):
        severity_tier: ClassVar[str] = "definitely_not_valid"

    with pytest.raises(SeverityClassificationAuditError, match="invalid"):
        validate_severity_classification_audit()

    del _BadTierError
    gc.collect()
