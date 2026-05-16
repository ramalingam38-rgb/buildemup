"""Sub-2 tests: LocalRefinementConfig cache-relevant partition sentinel
(v0.5 W4-4/W4-5), PRNG determinism, EnvironmentFingerprint with v0.7
W6-3 + v0.4 master_seed fields."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from buildemup.components.c11b import (
    EnvironmentFingerprint,
    LocalRefinementConfig,
    StagnationConfig,
    cache_irrelevant_field_names,
    cache_relevant_field_names,
    capture_environment_fingerprint,
)
from buildemup.components.c11b.prng import (
    _build_per_topology_rng,
    derive_per_topology_seed,
)


# ── partition sentinel ─────────────────────────────────────────────────


def test_config_has_15_cache_relevant_fields():
    """v0.5 baseline: 12 v1.0-carried + 3 v0.4/v0.5 (master_seed,
    per_topology_wallclock_seconds, evaluator_skip_cap_fraction) = 15."""
    cr = cache_relevant_field_names(LocalRefinementConfig)
    assert len(cr) == 15, f"Expected 15 cache_relevant fields; got {len(cr)}: {cr}"


def test_config_has_5_cache_irrelevant_fields():
    """evaluator_cache_max_memory_mb, enforcement_mode,
    provenance_verbosity, evaluator_cache_enabled,
    dominance_sorter_factory."""
    ci = cache_irrelevant_field_names(LocalRefinementConfig)
    assert len(ci) == 5, f"Expected 5 cache_irrelevant fields; got {len(ci)}: {ci}"


def test_partition_is_disjoint_and_complete():
    """No field is in both buckets; every field is in exactly one."""
    cr = set(cache_relevant_field_names(LocalRefinementConfig))
    ci = set(cache_irrelevant_field_names(LocalRefinementConfig))
    assert cr.isdisjoint(ci)
    all_fields = {f.name for f in dataclasses.fields(LocalRefinementConfig)}
    assert cr | ci == all_fields


def test_w4_5_per_topology_wallclock_is_cache_relevant():
    """v0.5 W4-5 PATCH-NOW: per_topology_wallclock_seconds.cache_relevant
    flipped False → True."""
    f = next(
        f
        for f in dataclasses.fields(LocalRefinementConfig)
        if f.name == "per_topology_wallclock_seconds"
    )
    assert f.metadata["cache_relevant"] is True


def test_w4_4_evaluator_skip_cap_fraction_is_cache_relevant():
    """v0.5 W4-4 PATCH-NOW: evaluator_skip_cap_fraction.cache_relevant
    flipped False → True."""
    f = next(
        f
        for f in dataclasses.fields(LocalRefinementConfig)
        if f.name == "evaluator_skip_cap_fraction"
    )
    assert f.metadata["cache_relevant"] is True


def test_master_seed_is_cache_relevant():
    """v0.4 D-PR-1: master_seed must participate in the cache-key root."""
    f = next(
        f
        for f in dataclasses.fields(LocalRefinementConfig)
        if f.name == "master_seed"
    )
    assert f.metadata["cache_relevant"] is True


# ── defaults ───────────────────────────────────────────────────────────


def test_config_defaults():
    cfg = LocalRefinementConfig()
    assert cfg.pop_size == 100
    assert cfg.max_generations == 100
    assert cfg.permutations_per_candidate == 3
    assert cfg.per_topology_wallclock_seconds == 30.0
    assert cfg.evaluator_skip_cap_fraction == 0.25
    assert isinstance(cfg.stagnation_config, StagnationConfig)


# ── PRNG determinism ───────────────────────────────────────────────────


def test_derive_per_topology_seed_pure_deterministic():
    seed_a = derive_per_topology_seed(42, 0, "sig_abc")
    seed_b = derive_per_topology_seed(42, 0, "sig_abc")
    assert seed_a == seed_b
    assert 0 <= seed_a < 2**32


def test_derive_per_topology_seed_varies_with_master():
    s0 = derive_per_topology_seed(0, 0, "sig")
    s1 = derive_per_topology_seed(1, 0, "sig")
    assert s0 != s1


def test_derive_per_topology_seed_varies_with_topology_index():
    s0 = derive_per_topology_seed(42, 0, "sig")
    s1 = derive_per_topology_seed(42, 1, "sig")
    assert s0 != s1


def test_derive_per_topology_seed_varies_with_signature():
    s0 = derive_per_topology_seed(42, 0, "sig_a")
    s1 = derive_per_topology_seed(42, 0, "sig_b")
    assert s0 != s1


def test_build_per_topology_rng_is_byte_equal():
    """TIER-1: same (master_seed, topology_index, signature) yields
    byte-equal RNG streams."""
    r1 = _build_per_topology_rng(42, 7, "topology_sig")
    r2 = _build_per_topology_rng(42, 7, "topology_sig")
    a = r1.random(1000)
    b = r2.random(1000)
    assert np.array_equal(a, b)


def test_build_per_topology_rng_differs_on_seed_change():
    r1 = _build_per_topology_rng(42, 0, "sig")
    r2 = _build_per_topology_rng(43, 0, "sig")
    assert not np.array_equal(r1.random(100), r2.random(100))


# ── EnvironmentFingerprint ─────────────────────────────────────────────


def test_environment_fingerprint_captures_master_seed():
    fp = capture_environment_fingerprint(master_seed=12345)
    assert fp.master_seed == 12345


def test_environment_fingerprint_captures_w6_3_schema_version():
    """W6-3: EnvironmentFingerprint must capture
    tiebreak_fingerprint_schema_version so cache keys invalidate when
    it bumps."""
    fp = capture_environment_fingerprint(master_seed=0)
    assert fp.tiebreak_fingerprint_schema_version == 1


def test_environment_fingerprint_is_deterministic():
    fp1 = capture_environment_fingerprint(master_seed=0)
    fp2 = capture_environment_fingerprint(master_seed=0)
    assert fp1.fingerprint_hash == fp2.fingerprint_hash
    assert fp1.matches(fp2)


def test_environment_fingerprint_master_seed_changes_hash():
    fp1 = capture_environment_fingerprint(master_seed=0)
    fp2 = capture_environment_fingerprint(master_seed=1)
    assert fp1.fingerprint_hash != fp2.fingerprint_hash
    assert not fp1.matches(fp2)


def test_environment_fingerprint_carries_c11b_version():
    from buildemup.components.c11b import C11B_VERSION

    fp = capture_environment_fingerprint(master_seed=0)
    assert fp.c11b_version == C11B_VERSION
