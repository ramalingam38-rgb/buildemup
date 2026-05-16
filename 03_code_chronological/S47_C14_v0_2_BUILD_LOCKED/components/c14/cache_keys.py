"""
BuildemUp — Component 14 — cache keys
======================================

Per C14 SPEC v0.2 LOCKED (v0.1 § 8 + v0.2 cache-relevant amendments).

C14 cache key composes:
- `c13_cache_key` (input cache key from C13, passthrough — full key,
   not split, per v0.1 § 8 + § 0.5)
- `C14_VERSION` (bumped on any schema-affecting amendment)
- `C14_METRIC_VERSION` (bumped on any metric semantic change — v0.2 A1
   raised it from 1 to 2 for the RA→RRA transition)
- Config-relevant fields (per CirculationConfig docs)

Inv (D18-analog): geometry-cache invalidation in C13 propagates to C14
via `c13_cache_key` change. Advisory-cache change in C13 ALSO propagates
(because at v0.2 C14 bundles geometry + advisory under `full_cache_key`).

Backlog: B-C14-CACHE-SPLIT-IF-DIVERGENT (post-LOCK, M) — split into
geometry / advisory only if a real use case for divergent invalidation
emerges.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final


# =============================================================================
# Cache-key derivation salt — bumped when the derivation algorithm itself
# changes (NOT when its inputs change). Currently v1.
# =============================================================================

_C14_CACHE_DERIVATION_SALT: Final[str] = "buildemup.c14.cache.v1"


@dataclass(frozen=True)
class C14CacheKeys:
    """Per v0.1 § 8. Frozen for hash-stability across replays.

    Three keys:
    - `c13_cache_key`: passthrough from upstream C13 result; if it
       changes, C14 invalidates automatically.
    - `metric_cache_key`: hash composing c13_cache_key + C14_VERSION +
       C14_METRIC_VERSION + cache-relevant config fields. Identifies a
       specific C14-output instance.
    - `full_cache_key`: at v0.2, identical to metric_cache_key. Split
       deferred to v2.0+ per B-C14-CACHE-SPLIT-IF-DIVERGENT.

    All three are stable across replay (Inv E7 byte-equal determinism).
    """
    c13_cache_key: str
    metric_cache_key: str
    full_cache_key: str

    def __post_init__(self) -> None:
        # Defensive: cache keys must be non-empty strings.
        for field_name in ("c13_cache_key", "metric_cache_key", "full_cache_key"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(
                    f"C14CacheKeys.{field_name} must be str; got {type(value)}"
                )
            if not value:
                raise ValueError(
                    f"C14CacheKeys.{field_name} must be non-empty"
                )


def derive_c14_cache_keys(
    *,
    c13_cache_key: str,
    c14_version: str,
    c14_metric_version: int,
    config_signature: str,
) -> C14CacheKeys:
    """Compose the C14 cache-key triple deterministically.

    Per v0.1 § 8, the metric_cache_key is the SHA-256 hex of a
    canonical-encoded tuple containing all cache-relevant inputs.
    """
    if not isinstance(c13_cache_key, str) or not c13_cache_key:
        raise ValueError(
            "derive_c14_cache_keys: c13_cache_key must be a non-empty str"
        )
    if not isinstance(c14_version, str) or not c14_version:
        raise ValueError(
            "derive_c14_cache_keys: c14_version must be a non-empty str"
        )
    if not isinstance(c14_metric_version, int) or c14_metric_version < 0:
        raise ValueError(
            "derive_c14_cache_keys: c14_metric_version must be a non-negative int"
        )
    if not isinstance(config_signature, str):
        raise ValueError(
            "derive_c14_cache_keys: config_signature must be a str"
        )

    payload = "|".join((
        _C14_CACHE_DERIVATION_SALT,
        c13_cache_key,
        c14_version,
        str(c14_metric_version),
        config_signature,
    ))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return C14CacheKeys(
        c13_cache_key=c13_cache_key,
        metric_cache_key=digest,
        full_cache_key=digest,
    )


def config_signature_for(
    *,
    flag_density_factor: float,
    betweenness_threshold: float,
    excessive_depth_threshold: int,
    category_coverage_low_threshold: float,
) -> str:
    """Build a canonical config signature from cache-relevant config fields.

    Per CirculationConfig docstring, these four fields are the only
    cache-relevant ones at v0.2. per_candidate_wallclock_seconds,
    strict_mode, and cache_mode are NOT cache-relevant (see config.py).
    """
    return "|".join((
        f"density={flag_density_factor:.6f}",
        f"betweenness={betweenness_threshold:.6f}",
        f"depth={excessive_depth_threshold}",
        f"cat_cov_low={category_coverage_low_threshold:.6f}",
    ))


__all__ = [
    "C14CacheKeys",
    "derive_c14_cache_keys",
    "config_signature_for",
]
