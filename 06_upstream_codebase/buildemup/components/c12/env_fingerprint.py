"""
BuildemUp — Component 12 — environment fingerprint
====================================================

Per C12 SPEC v1.0 LOCKED v0.3-A6 (Q-10 resolution): C12 builds its
own cache key as ``sha256(c11b_env_fingerprint || c12_config_cache_relevant_fields)``.
Owning the C12-side key with the C11b env fingerprint as a prefix
keeps the dependency explicit instead of silently piggybacking
C11b's cache.

Captures the run-time tuple that determines TIER-1 byte-equal replay
equivalence (Inv 7 + Inv 13):

- ``c12_version``: changes invalidate cache cleanly
- ``c11b_env_fingerprint_hash``: inherits the upstream env tuple
  identity (NumPy / Python / platform / BLAS / master_seed)
- ``c12_config_hash``: SHA256 over the canonical-serialized
  cache_relevant PlacementConfig fields

``fingerprint_hash`` is a SHA256 over the canonical-serialized tuple
used as the cache key root.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from buildemup.utilities.canonical import canonical_serialize

from .config import PlacementConfig
from .versioning import C12_VERSION


@dataclass(frozen=True)
class C12EnvironmentFingerprint:
    """Carries the C12 env tuple used for TIER-1 replay equivalence
    plus cache-key derivation."""
    c12_version: str
    c11b_env_fingerprint_hash: str
    c12_config_hash: str
    fingerprint_hash: str

    def matches(self, other: "C12EnvironmentFingerprint") -> bool:
        return (
            self.c12_version == other.c12_version
            and self.c11b_env_fingerprint_hash
            == other.c11b_env_fingerprint_hash
            and self.c12_config_hash == other.c12_config_hash
        )


def _config_cache_relevant_payload(config: PlacementConfig) -> dict:
    """Build the cache-relevant payload for hashing.

    Per v0.3-A6: only fields with cache_relevant=True semantics
    participate. The non-cache-relevant fields (timeouts) do NOT
    change output identity and are excluded from the hash.

    Fields included per § 2.3 cache_relevant flags:
      - strict_mode (cache_relevant=True)
      - placement_algorithm (cache_relevant=True)
      - vertical_alignment_tolerance_m (cache_relevant=True)
      - multi_floor_max_realign_iterations (cache_relevant=True)
      - master_seed (cache_relevant=True via env tuple)

    Fields excluded per § 2.3 cache_relevant flags:
      - per_candidate_wallclock_seconds (cache_relevant=False)
      - multi_floor_wallclock_seconds (cache_relevant=False)
    """
    return {
        "strict_mode": config.strict_mode,
        "placement_algorithm": config.placement_algorithm,
        "vertical_alignment_tolerance_m": config.vertical_alignment_tolerance_m,
        "multi_floor_max_realign_iterations": config.multi_floor_max_realign_iterations,
        "master_seed": config.master_seed,
    }


def capture_c12_environment_fingerprint(
    *,
    c11b_env_fingerprint_hash: str,
    config: PlacementConfig,
) -> C12EnvironmentFingerprint:
    """Phase 0 helper — captures the C12 env tuple at batch start.

    ``c11b_env_fingerprint_hash`` is the SHA256 hex digest from the
    upstream C11b ``EnvironmentFingerprint.fingerprint_hash``. This
    is what makes the C12 cache key inherit C11b's env identity
    without re-hashing the full C11b tuple (which would couple our
    cache to C11b's internal representation).
    """
    if not c11b_env_fingerprint_hash:
        raise ValueError(
            "capture_c12_environment_fingerprint requires non-empty "
            "c11b_env_fingerprint_hash."
        )

    config_payload = _config_cache_relevant_payload(config)
    config_canon = canonical_serialize(config_payload)
    config_hash = hashlib.sha256(config_canon.encode("utf-8")).hexdigest()

    payload = {
        "c12_version": C12_VERSION,
        "c11b_env_fingerprint_hash": c11b_env_fingerprint_hash,
        "c12_config_hash": config_hash,
    }
    canon = canonical_serialize(payload)
    fph = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    return C12EnvironmentFingerprint(
        c12_version=C12_VERSION,
        c11b_env_fingerprint_hash=c11b_env_fingerprint_hash,
        c12_config_hash=config_hash,
        fingerprint_hash=fph,
    )


def compute_c12_cache_key(env: C12EnvironmentFingerprint) -> str:
    """Per v0.3-A6: cache key = the env fingerprint hash itself.

    Kept as a separate function so future C12 versions can add
    additional cache-key dimensions (e.g., per-batch input hash)
    without breaking the v1.0 contract.
    """
    return env.fingerprint_hash


__all__ = [
    "C12EnvironmentFingerprint",
    "capture_c12_environment_fingerprint",
    "compute_c12_cache_key",
]
