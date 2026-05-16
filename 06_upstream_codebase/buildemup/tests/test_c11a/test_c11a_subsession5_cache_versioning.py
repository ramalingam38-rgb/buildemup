"""
C11a Sub-session 5 — B-NEW-W partial: cache versioning hooks tests.

Per S39 critique walk F7. The full B-NEW-W (cross-batch invalidation
epochs) is gated on B-NEW-E2 process-lifetime cache. The partial
shipped here adds:
  - C11A_CACHE_KEY_VERSION constant folded into config hash
  - UpstreamVersionInfo struct + optional fold into config hash

Verifies:
  - Hash changes when C11A_CACHE_KEY_VERSION would change.
  - Hash changes when UpstreamVersionInfo fields change.
  - Hash unchanged when upstream_versions=None vs absent (default
    behaviour preserved).
  - Sub-3 hashes remain comparable internally — the version fold is
    deterministic, not random per-call.
"""
from __future__ import annotations

from buildemup.components.c11a import (
    DeepMutationCacheKey,
    MutationOperator,
    TopologyMutationConfig,
    derive_cache_config_hash,
    derive_cache_key,
)
from buildemup.components.c11a.cache import (
    C11A_CACHE_KEY_VERSION,
    UpstreamVersionInfo,
)


# =============================================================================
# C11A_CACHE_KEY_VERSION constant
# =============================================================================


def test_c11a_cache_key_version_is_v1_at_lock() -> None:
    """At Spec #4 v1.6 LOCKED (B-NEW-T3 build), the constant bumps
    from v1.0.0 to v1.3.0 in a single cumulative step covering
    Spec #2 (v1.1.0), Spec #3 (v1.2.0), and Spec #4 (v1.3.0) per
    Spec #4 § 3.6.
    """
    assert C11A_CACHE_KEY_VERSION == "v1.3.0"


def test_cache_hash_includes_c11a_version() -> None:
    """The hash MUST fold in the C11a impl version. Verified
    indirectly: pre-B-NEW-W and post-B-NEW-W hash bytes differ
    (the constant insertion changed the hash). We can't compare
    against the legacy hash directly, but we can verify version
    is part of the input by toggling it.
    """
    # Construct two derive_cache_config_hash calls with same config
    # but different C11A_CACHE_KEY_VERSION via monkeypatch.
    import buildemup.components.c11a.cache as cache_mod
    original = cache_mod.C11A_CACHE_KEY_VERSION
    config = TopologyMutationConfig()

    cache_mod.C11A_CACHE_KEY_VERSION = "vX.Y.Z"
    try:
        h_alt = derive_cache_config_hash(config)
    finally:
        cache_mod.C11A_CACHE_KEY_VERSION = original

    h_orig = derive_cache_config_hash(config)
    assert h_alt != h_orig


# =============================================================================
# UpstreamVersionInfo fold
# =============================================================================


def test_upstream_versions_none_matches_omitted() -> None:
    """Passing upstream_versions=None should produce the same hash as
    omitting the kwarg — backwards-compat with Sub-3 callers."""
    config = TopologyMutationConfig()
    h_omit = derive_cache_config_hash(config)
    h_none = derive_cache_config_hash(config, upstream_versions=None)
    assert h_omit == h_none


def test_upstream_versions_changes_hash() -> None:
    """Different UpstreamVersionInfo → different hash."""
    config = TopologyMutationConfig()
    v_a = UpstreamVersionInfo(c7_kb_version="v0.7.3")
    v_b = UpstreamVersionInfo(c7_kb_version="v0.8.0")
    h_a = derive_cache_config_hash(config, upstream_versions=v_a)
    h_b = derive_cache_config_hash(config, upstream_versions=v_b)
    assert h_a != h_b


def test_upstream_versions_field_distinction() -> None:
    """Different KB fields produce different hashes — verifies each
    field participates."""
    config = TopologyMutationConfig()
    base = UpstreamVersionInfo()
    h_base = derive_cache_config_hash(config, upstream_versions=base)

    for field in (
        "c7_kb_version",
        "c9_furniture_kb_version",
        "c9_targets_kb_version",
        "c10_plumbing_kb_version",
        "c10_fixture_profiles_kb_version",
    ):
        kwargs = {field: "v_modified"}
        modified = UpstreamVersionInfo(**kwargs)
        h_modified = derive_cache_config_hash(
            config, upstream_versions=modified,
        )
        assert h_modified != h_base, (
            f"Field {field} doesn't participate in hash"
        )


def test_upstream_versions_deterministic() -> None:
    config = TopologyMutationConfig()
    v = UpstreamVersionInfo(c7_kb_version="v0.7.3", c10_plumbing_kb_version="v1.0")
    h_a = derive_cache_config_hash(config, upstream_versions=v)
    h_b = derive_cache_config_hash(config, upstream_versions=v)
    assert h_a == h_b


# =============================================================================
# derive_cache_key passthrough
# =============================================================================


def test_derive_cache_key_with_upstream_versions() -> None:
    """derive_cache_key passes upstream_versions through to config hash."""
    config = TopologyMutationConfig()
    v = UpstreamVersionInfo(c10_plumbing_kb_version="v2.0")
    k_with = derive_cache_key(
        MutationOperator.M6_WET_ROTATE, "src", config, upstream_versions=v,
    )
    k_without = derive_cache_key(
        MutationOperator.M6_WET_ROTATE, "src", config,
    )
    assert k_with.config_hash != k_without.config_hash


def test_derive_cache_key_returns_deep_mutation_cache_key() -> None:
    config = TopologyMutationConfig()
    k = derive_cache_key(MutationOperator.M7A_GRID_3_3, "src", config)
    assert isinstance(k, DeepMutationCacheKey)


# =============================================================================
# UpstreamVersionInfo shape
# =============================================================================


def test_upstream_version_info_default_empty_strings() -> None:
    """Defaults are empty strings (not None / not 'unknown') — so a
    partial-fill instance still hashes deterministically."""
    v = UpstreamVersionInfo()
    assert v.c7_kb_version == ""
    assert v.c10_plumbing_kb_version == ""


def test_upstream_version_info_to_serialised_parts_sorted() -> None:
    v = UpstreamVersionInfo(c7_kb_version="x", c10_plumbing_kb_version="y")
    parts = v.to_serialised_parts()
    # Sorted alphabetically.
    assert list(parts) == sorted(parts)


def test_upstream_version_info_frozen() -> None:
    """UpstreamVersionInfo is frozen — field values can't change post-
    construction (cache-key stability)."""
    import pytest
    v = UpstreamVersionInfo()
    with pytest.raises(Exception):
        v.c7_kb_version = "x"  # type: ignore[misc]
