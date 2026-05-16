"""
BuildemUp — Component 15 — cache keys
======================================

Per C15 SPEC v0.2 LOCKED (v0.1 § 8 + v0.2 cache-relevant amendments
A1, A2, A3, A4, A5, A6, A7, A10).

C15 cache key composes:
- `c14_full_cache_key` (input cache key from C14, passthrough)
- `C15_VERSION` (bumped on schema-affecting amendments)
- `C15_CHECK_REGISTRY_VERSION` (bumped on check semantics or
  severity-rule-table changes)
- `cultural_profile_id` (per v0.2 A3 — profile is part of cache key)

Per Inv P14: any C14 cache change propagates; any C15 registry or
version change bumps the C15 key.

Per Inv P0 (v0.2 A1): cache keys are HASHES of canonical inputs — they
do NOT carry numeric layout-quality scores. The hash is a one-way
fingerprint, not an aggregate of check outputs.

Backlog (post-LOCK): potential split of full_cache_key into
checks/registry/profile keys if a real use case for divergent
invalidation emerges (mirrors B-C14-CACHE-SPLIT-IF-DIVERGENT pattern).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final


# =============================================================================
# Cache-key derivation salt — bumped when the derivation algorithm itself
# changes (NOT when its inputs change). Currently v1.
# =============================================================================

_C15_CACHE_DERIVATION_SALT: Final[str] = "buildemup.c15.cache.v1"


@dataclass(frozen=True)
class C15CacheKeys:
    """Per v0.1 § 8. Frozen for hash-stability across replays.

    Three keys:
    - `c14_full_cache_key`: passthrough from upstream C14 result; if it
       changes, C15 invalidates automatically.
    - `check_registry_cache_key`: hash composing c14_full_cache_key +
       C15_VERSION + C15_CHECK_REGISTRY_VERSION + cultural_profile_id +
       severity_rule_table_hash. Identifies a specific C15-output
       instance for a specific (input, profile, registry).
    - `full_cache_key`: at v0.2, identical to check_registry_cache_key.
       Split deferred to a potential v2.x amendment if divergent-
       invalidation use case emerges.

    All three are stable across replay (Inv P2 byte-equal determinism).

    Per Inv P0 (v0.2 A1): these strings carry NO information about
    individual check outputs or layout quality. They are content
    fingerprints used for cache lookup, not aggregations.
    """
    c14_full_cache_key: str
    check_registry_cache_key: str
    full_cache_key: str

    def __post_init__(self) -> None:
        # Defensive: cache keys must be non-empty strings.
        for field_name in (
            "c14_full_cache_key",
            "check_registry_cache_key",
            "full_cache_key",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(
                    f"C15CacheKeys.{field_name} must be str; "
                    f"got {type(value)}"
                )
            if not value:
                raise ValueError(
                    f"C15CacheKeys.{field_name} must be non-empty"
                )


def derive_c15_cache_keys(
    *,
    c14_full_cache_key: str,
    c15_version: str,
    c15_check_registry_version: int,
    cultural_profile_id: str,
    severity_rule_table_hash: str,
) -> C15CacheKeys:
    """Compose the C15 cache-key triple deterministically.

    Per v0.1 § 8 + v0.2 A3 cache-relevance: the check_registry_cache_key
    is the SHA-256 hex of a canonical-encoded tuple containing all
    cache-relevant inputs:

    - c14_full_cache_key (upstream chain)
    - c15_version (schema)
    - c15_check_registry_version (check semantics + severity rules)
    - cultural_profile_id (per A3 — different profiles → different
      cache buckets)
    - severity_rule_table_hash (per A4 — severity_basis citation
      changes invalidate)

    The salt prefix `buildemup.c15.cache.v1` makes the algorithm
    version explicit; future algorithm changes bump the salt without
    bumping C15_VERSION.

    Per Inv P0: this function returns a hash STRING, not a score. The
    hash is one-way and carries no information about layout quality.
    """
    if not isinstance(c14_full_cache_key, str) or not c14_full_cache_key:
        raise ValueError(
            "derive_c15_cache_keys: c14_full_cache_key must be a "
            "non-empty str"
        )
    if not isinstance(c15_version, str) or not c15_version:
        raise ValueError(
            "derive_c15_cache_keys: c15_version must be a non-empty str"
        )
    if not isinstance(c15_check_registry_version, int):
        raise ValueError(
            "derive_c15_cache_keys: c15_check_registry_version must "
            "be int"
        )
    if isinstance(c15_check_registry_version, bool):
        # bool is int subclass — reject.
        raise ValueError(
            "derive_c15_cache_keys: c15_check_registry_version must "
            "be int (not bool)"
        )
    if c15_check_registry_version < 0:
        raise ValueError(
            "derive_c15_cache_keys: c15_check_registry_version must "
            "be non-negative"
        )
    if not isinstance(cultural_profile_id, str) or not cultural_profile_id:
        raise ValueError(
            "derive_c15_cache_keys: cultural_profile_id must be a "
            "non-empty str"
        )
    if not isinstance(severity_rule_table_hash, str):
        raise ValueError(
            "derive_c15_cache_keys: severity_rule_table_hash must be str"
        )

    payload = "|".join((
        _C15_CACHE_DERIVATION_SALT,
        c14_full_cache_key,
        c15_version,
        str(c15_check_registry_version),
        cultural_profile_id,
        severity_rule_table_hash,
    ))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return C15CacheKeys(
        c14_full_cache_key=c14_full_cache_key,
        check_registry_cache_key=digest,
        full_cache_key=digest,
    )


def config_signature_for() -> str:
    # All cache-relevant config fields would be keyword-only args here.
    # At v0.2 this is empty — see ProblemFinderConfig docstring: NO
    # config fields are cache-relevant at v0.2 LOCK SKETCH. The
    # signature is reserved for future cache-relevant additions.
    """Build a canonical config signature from cache-relevant config fields.

    Per ProblemFinderConfig docstring at v0.2 LOCK SKETCH, NO fields
    are cache-relevant. This function exists as a placeholder for
    future cache-relevant config additions (post-LOCK polish). At
    v0.2 it returns a stable sentinel string.

    Cache-relevant: by definition, but the signature itself is empty.

    Why this function exists at v0.2 even though it's a sentinel:
    keeping the API surface stable across v0.x → v1.0 prevents
    forced caller-code changes when cache-relevant config emerges.
    Callers always include `config_signature_for()` in their cache-key
    pipelines without re-plumbing when v1.x adds real fields.
    """
    return "c15.config.v0.2.no_cache_relevant_fields"


__all__ = [
    "C15CacheKeys",
    "derive_c15_cache_keys",
    "config_signature_for",
]
