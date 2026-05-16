"""
C11a Sub-session 3 tests — DeepMutationCacheKey + derive_cache_*.

Per spec § 0.3 + § 2.6: cache key determinism, cache-relevant field
flip changes hash, cache-irrelevant field flip preserves hash.
"""
from __future__ import annotations

import dataclasses

from buildemup.components.c11a import (
    DeepMutationCacheKey,
    EnforcementMode,
    MutationOperator,
    ProvenanceVerbosity,
    RegistryValidationMode,
    TopologyMutationConfig,
    derive_cache_config_hash,
    derive_cache_key,
)


# =============================================================================
# DeepMutationCacheKey shape
# =============================================================================


def test_cache_key_is_frozen_dataclass() -> None:
    k = DeepMutationCacheKey(
        operator=MutationOperator.M6_WET_ROTATE,
        source_topology_signature_hash="src",
        config_hash="cfg",
    )
    assert dataclasses.is_dataclass(k)
    # frozen → cannot reassign
    import pytest
    with pytest.raises(Exception):
        k.config_hash = "x"  # type: ignore[misc]


def test_cache_key_equality_by_value() -> None:
    """Two keys with same fields are equal (frozen dataclass)."""
    a = DeepMutationCacheKey(
        operator=MutationOperator.M7A_GRID_3_3,
        source_topology_signature_hash="s", config_hash="c",
    )
    b = DeepMutationCacheKey(
        operator=MutationOperator.M7A_GRID_3_3,
        source_topology_signature_hash="s", config_hash="c",
    )
    assert a == b
    assert hash(a) == hash(b)


# =============================================================================
# derive_cache_config_hash — determinism + scope
# =============================================================================


def test_config_hash_deterministic() -> None:
    """Same config → same hash across calls."""
    c = TopologyMutationConfig()
    assert derive_cache_config_hash(c) == derive_cache_config_hash(c)


def test_config_hash_format_16_hex_chars() -> None:
    h = derive_cache_config_hash(TopologyMutationConfig())
    assert len(h) == 16
    int(h, 16)  # raises if non-hex


def test_config_hash_changes_when_cache_relevant_field_changes() -> None:
    """max_seeds_per_input is cache_relevant=True; flipping it must
    change the hash."""
    c1 = TopologyMutationConfig(max_seeds_per_input=8)
    c2 = TopologyMutationConfig(max_seeds_per_input=16)
    assert derive_cache_config_hash(c1) != derive_cache_config_hash(c2)


def test_config_hash_changes_when_enabled_operators_changes() -> None:
    """enabled_operators is cache_relevant=True."""
    c1 = TopologyMutationConfig()
    c2 = TopologyMutationConfig(
        enabled_operators=(MutationOperator.M0_BASE, MutationOperator.M1_HORIZ_FLIP),
    )
    assert derive_cache_config_hash(c1) != derive_cache_config_hash(c2)


def test_config_hash_changes_when_deduplicate_flag_changes() -> None:
    c1 = TopologyMutationConfig(deduplicate_by_signature=True)
    c2 = TopologyMutationConfig(deduplicate_by_signature=False)
    assert derive_cache_config_hash(c1) != derive_cache_config_hash(c2)


def test_config_hash_unchanged_when_provenance_verbosity_changes() -> None:
    """provenance_verbosity is cache_relevant=False — flipping must
    NOT change the hash. This is the cache-bypass-irrelevant-fields
    invariant per § 2.6."""
    c1 = TopologyMutationConfig(provenance_verbosity=ProvenanceVerbosity.PER_OP)
    c2 = TopologyMutationConfig(provenance_verbosity=ProvenanceVerbosity.FULL)
    assert derive_cache_config_hash(c1) == derive_cache_config_hash(c2)


def test_config_hash_unchanged_when_enforcement_mode_changes() -> None:
    """enforcement_mode is cache_relevant=False."""
    c1 = TopologyMutationConfig(enforcement_mode=EnforcementMode.WARN)
    c2 = TopologyMutationConfig(enforcement_mode=EnforcementMode.STRICT)
    assert derive_cache_config_hash(c1) == derive_cache_config_hash(c2)


def test_config_hash_unchanged_when_registry_validation_mode_changes() -> None:
    """registry_validation_mode is cache_relevant=False."""
    c1 = TopologyMutationConfig(registry_validation_mode=RegistryValidationMode.STRICT)
    c2 = TopologyMutationConfig(registry_validation_mode=RegistryValidationMode.WARN)
    assert derive_cache_config_hash(c1) == derive_cache_config_hash(c2)


# =============================================================================
# derive_cache_key — composes operator + signature + config
# =============================================================================


def test_cache_key_components_distinct_per_operator() -> None:
    c = TopologyMutationConfig()
    k1 = derive_cache_key(MutationOperator.M6_WET_ROTATE, "src", c)
    k2 = derive_cache_key(MutationOperator.M7A_GRID_3_3, "src", c)
    assert k1 != k2
    assert k1.operator != k2.operator


def test_cache_key_distinct_per_source_signature() -> None:
    c = TopologyMutationConfig()
    k1 = derive_cache_key(MutationOperator.M6_WET_ROTATE, "src-A", c)
    k2 = derive_cache_key(MutationOperator.M6_WET_ROTATE, "src-B", c)
    assert k1.source_topology_signature_hash != k2.source_topology_signature_hash
    assert k1 != k2


def test_cache_key_carries_operator_enum_value() -> None:
    """The key carries the enum, not the .value string — so two keys
    with the same .value but different enum types (a defensive check)
    would compare unequal."""
    k = derive_cache_key(
        MutationOperator.M8_VERT_REARR, "src", TopologyMutationConfig(),
    )
    assert k.operator is MutationOperator.M8_VERT_REARR
