"""
BuildemUp — Component 11a — operator registry validation
==========================================================

Per spec § 2.8 — ``validate_operator_registry()`` runs at C11a Phase 0
startup (Sub-session 4 wires it into the orchestrator). Sub-session 2
ships the validator + its sub-checks; Sub-session 4 calls it.

Invariants enforced (Sub-session 2 scope):

  * **Inv 28** (NEW v0.5): every key in any ``OperatorExpectedDeltaSchema``
    set MUST be a ``DeltaKey`` enum value. String literals raise
    ``OperatorRegistryError`` at startup.

  * **Inv 26** (NEW v0.4): every ``TopologyMutationConfig`` field carries
    ``metadata["cache_relevant"]`` boolean. Missing markers raise
    ``OperatorRegistryError`` at startup.

  * **Coverage**: every ``MutationOperator`` enum member has a metadata
    entry in ``OPERATOR_METADATA``; missing entries raise.

  * **Tier consistency**: every metadata entry's tier ∈ {SHALLOW,
    REGENERATIVE}; family ∈ valid enum values; family_transition_policy
    ∈ valid enum values. (Type-checked by enum-typed dataclass fields,
    but the validator surfaces violations explicitly with file context.)

  * **Cache-relevant field coverage**: every entry in
    ``cache_relevant_config_fields`` MUST be a TopologyMutationConfig
    field with metadata["cache_relevant"]=True.

Sub-session 4 will extend this with:

  * **Inv 27 / F-v4-5**: ``validate_severity_classification_audit()``
    walks the upstream-error dependency graph and verifies every
    referenced exception type carries ``severity_tier`` ClassVar.

  * **Pending-predicate sunset scan + Inv 24 LOCK gate**: reads the
    predicate registry, counts pending_upstream entries, checks
    against WAIVER_REGISTRY length per the LOCK gate formula.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Final

from buildemup.components.c11a.errors import OperatorRegistryError
from buildemup.components.c11a.operator_metadata import OPERATOR_METADATA
from buildemup.components.c11a.schema import (
    DeltaKey,
    MutationOperator,
    MutationOperatorFamily,
    MutationOperatorMetadata,
    MutationTier,
    TopologyFamilyTransitionPolicy,
    TopologyMutationConfig,
)


# =============================================================================
# Inv 26 — every TopologyMutationConfig field carries cache_relevant
# =============================================================================


def _validate_inv_26_cache_metadata() -> None:
    """Walk TopologyMutationConfig fields; every one MUST carry
    metadata["cache_relevant"] as a boolean.

    Per Inv 26 (v0.4): missing markers indicate a config-evolution
    drift — a field added without explicit cache-relevance declaration.
    Such fields would silently misbehave in DeepMutationCacheKey
    derivation, so we hard-fail at startup.
    """
    for f in dataclasses.fields(TopologyMutationConfig):
        if "cache_relevant" not in f.metadata:
            raise OperatorRegistryError(
                f"Inv 26 violation: TopologyMutationConfig field "
                f"'{f.name}' is missing metadata['cache_relevant']. "
                f"Every config field MUST declare cache-relevance "
                f"explicitly per § 2.5."
            )
        value = f.metadata["cache_relevant"]
        if not isinstance(value, bool):
            raise OperatorRegistryError(
                f"Inv 26 violation: TopologyMutationConfig field "
                f"'{f.name}' has metadata['cache_relevant']={value!r} "
                f"(expected bool)."
            )


# =============================================================================
# Inv 28 — DeltaKey enum vocabulary
# =============================================================================


def _validate_inv_28_delta_key_enum(
    operator: MutationOperator, metadata: MutationOperatorMetadata,
) -> None:
    """Walk the operator's expected_delta_schema; every key in
    expected, allowed_secondary, forbidden MUST be a DeltaKey enum
    value.

    Per Inv 28 (v0.5): string literals not in the enum raise here.
    The schema's frozenset[DeltaKey] type *should* prevent this at
    construction time, but a runtime audit catches dynamically-
    constructed schemas (e.g., loaded from JSON KB or test
    fixtures with type erasure).
    """
    schema = metadata.expected_delta_schema
    for set_name, key_set in (
        ("expected", schema.expected),
        ("allowed_secondary", schema.allowed_secondary),
        ("forbidden", schema.forbidden),
    ):
        for key in key_set:
            if not isinstance(key, DeltaKey):
                raise OperatorRegistryError(
                    f"Inv 28 violation: operator {operator.value}'s "
                    f"expected_delta_schema.{set_name} contains "
                    f"{key!r} which is not a DeltaKey enum member. "
                    f"Per § 2.5 v0.5 all delta keys MUST come from "
                    f"the canonical DeltaKey enum."
                )


# =============================================================================
# Cache-relevant field coverage
# =============================================================================


def _validate_cache_field_coverage(
    operator: MutationOperator, metadata: MutationOperatorMetadata,
    cache_relevant_field_names: frozenset[str],
) -> None:
    """Every entry in metadata.cache_relevant_config_fields MUST be a
    TopologyMutationConfig field marked cache_relevant=True.

    Implements the cross-check that operator metadata cannot reference
    cache-irrelevant or non-existent config fields — it would mislead
    DeepMutationCacheKey derivation.
    """
    for fname in metadata.cache_relevant_config_fields:
        if fname not in cache_relevant_field_names:
            raise OperatorRegistryError(
                f"operator {operator.value}: "
                f"cache_relevant_config_fields contains {fname!r} "
                f"which is not a cache_relevant=True field of "
                f"TopologyMutationConfig. Either fix the field name "
                f"or update the config's metadata['cache_relevant']."
            )


# =============================================================================
# Operator coverage
# =============================================================================


def _validate_operator_coverage() -> None:
    """Every MutationOperator enum member MUST have an OPERATOR_METADATA
    entry. Missing entries raise.
    """
    enum_members = set(MutationOperator)
    metadata_keys = set(OPERATOR_METADATA.keys())
    missing = enum_members - metadata_keys
    if missing:
        raise OperatorRegistryError(
            f"OPERATOR_METADATA is missing entries for: "
            f"{sorted(o.value for o in missing)}. Per § 2.8 every "
            f"MutationOperator enum member MUST have a metadata entry."
        )
    extra = metadata_keys - enum_members
    if extra:
        raise OperatorRegistryError(
            f"OPERATOR_METADATA contains entries for non-enum operators: "
            f"{sorted(o.value if hasattr(o, 'value') else str(o) for o in extra)}. "
            f"This is a programming bug."
        )


# =============================================================================
# Per-entry well-formedness
# =============================================================================


def _validate_metadata_entry(
    operator: MutationOperator, metadata: MutationOperatorMetadata,
) -> None:
    """Audit a single OPERATOR_METADATA entry for type-correctness."""
    if metadata.operator != operator:
        raise OperatorRegistryError(
            f"OPERATOR_METADATA[{operator.value}].operator does not "
            f"match its dict key (got {metadata.operator.value!r})."
        )
    if not isinstance(metadata.tier, MutationTier):
        raise OperatorRegistryError(
            f"OPERATOR_METADATA[{operator.value}].tier is "
            f"{metadata.tier!r} (expected MutationTier)."
        )
    if not isinstance(metadata.family, MutationOperatorFamily):
        raise OperatorRegistryError(
            f"OPERATOR_METADATA[{operator.value}].family is "
            f"{metadata.family!r} (expected MutationOperatorFamily)."
        )
    if not isinstance(
        metadata.family_transition_policy, TopologyFamilyTransitionPolicy,
    ):
        raise OperatorRegistryError(
            f"OPERATOR_METADATA[{operator.value}]."
            f"family_transition_policy is "
            f"{metadata.family_transition_policy!r} "
            f"(expected TopologyFamilyTransitionPolicy)."
        )


# =============================================================================
# validate_operator_registry — public entry point
# =============================================================================


def validate_operator_registry() -> None:
    """Per § 2.8 — startup validator.

    Order of checks (each runs to completion or raises on first
    violation):

      1. Operator coverage (every enum member has metadata)
      2. Inv 26 (TopologyMutationConfig cache_relevant markers)
      3. Per-entry: type well-formedness, Inv 28 DeltaKey purity,
         cache-relevant field coverage

    Sub-session 4 will extend with Inv 24 LOCK gate + severity audit.
    """
    # Step 1 — coverage.
    _validate_operator_coverage()

    # Step 2 — Inv 26.
    _validate_inv_26_cache_metadata()

    # Pre-compute the set of cache-relevant TopologyMutationConfig
    # field names for the per-entry check.
    cache_relevant_field_names = frozenset(
        f.name
        for f in dataclasses.fields(TopologyMutationConfig)
        if f.metadata.get("cache_relevant") is True
    )

    # Step 3 — per-entry checks.
    for operator, metadata in OPERATOR_METADATA.items():
        _validate_metadata_entry(operator, metadata)
        _validate_inv_28_delta_key_enum(operator, metadata)
        _validate_cache_field_coverage(
            operator, metadata, cache_relevant_field_names,
        )


__all__ = [
    "validate_operator_registry",
]
