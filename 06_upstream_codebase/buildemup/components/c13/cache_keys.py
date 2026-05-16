"""
BuildemUp — Component 13 — cache key construction
==================================================

Per C13 SPEC v1.0 LOCKED:
- v0.4 C10 (split geometry / advisory / full cache domains)
- v0.5 D7 (advisory_cache_key contains geometry_cache_key prefix —
  Inv D18)
- v0.2 A10 (cache key includes upstream schema version constants)

Cache key construction pattern:

  geometry_cache_key = sha256(
      C13_VERSION ||
      C13_EDGE_PROTOCOL_VERSION ||
      EXPECTED_C12_VERSION ||
      EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION ||
      EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION ||
      upstream_c12_cache_key ||
      geometry_config_cache_relevant_fields_canonical
  )

  advisory_cache_key = (
      geometry_cache_key ||  # PREFIX per Inv D18
      "::" ||                # canonical separator
      advisory_payload_hash
  )

  where advisory_payload_hash = sha256(
      ADVISORY_SCHEMA_VERSION ||
      advisory_config_cache_relevant_fields_canonical
  )

  full_cache_key = sha256(
      geometry_cache_key || "::" || advisory_payload_hash
  )

Per v0.5 D7: prefix construction makes Inv D18 testable via simple
startswith() check rather than relying on hash-input-inclusion semantics
(which are opaque post-hash). Replay of advisories against mismatched
geometry is structurally impossible — advisory_cache_key changes
whenever geometry_cache_key changes.

This module is the SINGLE PLACE that constructs C13CacheKeys instances.
Constructing C13CacheKeys directly is permitted (the dataclass enforces
D18) but builders here are the canonical path.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .config import DoorPlacementConfig
from .schema import C13CacheKeys
from .versioning import (
    ADVISORY_SCHEMA_VERSION,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
    EXPECTED_C12_VERSION,
    EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION,
    EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION,
)


# =============================================================================
# Internal separator (matches the C13CacheKeys.__post_init__ prefix check)
# =============================================================================

_ADVISORY_CACHE_KEY_SEPARATOR: str = "::"
"""Per v0.5 D7. Separator between geometry_cache_key prefix and the
advisory payload hash. Choice of '::' is canonical at v1.0; bumping
this constant requires ADVISORY_SCHEMA_VERSION MINOR bump (it's part
of the cache-key derivation contract)."""


# =============================================================================
# Cache-domain partitioning of DoorPlacementConfig (per v0.4 C10)
# =============================================================================

_GEOMETRY_CACHE_RELEVANT_FIELDS: tuple[str, ...] = (
    "strict_mode",
    "default_clear_width_m",
    "corner_offset_m",
    "grid_snap_m",
    "max_conflict_resolution_iterations",
    "secondary_door_conflict_budget",
    "bathroom_outswing_area_threshold_m2",
    "master_seed",
)
"""Per v0.4 C10. Config fields whose changes invalidate
geometry_cache_key (and therefore also advisory_cache_key + full_cache_key,
since both depend on geometry_cache_key)."""


_ADVISORY_CACHE_RELEVANT_FIELDS: tuple[str, ...] = (
    "advisory_density_factor",
    "nbc_borderline_fraction",
)
"""Per v0.4 C10. Config fields whose changes invalidate ONLY
advisory_cache_key + full_cache_key, preserving geometry_cache_key.
Allows C14 consumers to request "geometry-only replay" when only
positioning is relevant."""


# Sanity: every DoorPlacementConfig field is classified either as cache-
# relevant in one of the two domains OR is documented as cache-irrelevant.
# Cache-irrelevant fields (telemetry_sink, per_candidate_wallclock_seconds)
# are not included in either tuple.


# =============================================================================
# Canonical config serialization (deterministic for cache stability)
# =============================================================================

def _config_field_canonical(value: Any) -> Any:
    """Canonicalize a config field value for stable serialization.

    Booleans / ints / strings: as-is.
    Floats: formatted with repr() to preserve all precision bits.
    None: literal None.
    """
    if isinstance(value, float):
        # repr() is round-trippable and stable across Python versions.
        return f"f:{value!r}"
    if isinstance(value, bool):
        return f"b:{int(value)}"
    if isinstance(value, int):
        return f"i:{value}"
    if isinstance(value, str):
        return f"s:{value}"
    if value is None:
        return "n:null"
    raise TypeError(
        f"Cache-key serialization: unsupported config field type "
        f"{type(value).__name__} for value {value!r}."
    )


def _canonical_geometry_config_payload(config: DoorPlacementConfig) -> str:
    """Stable JSON serialization of the geometry-cache-relevant subset of
    config. Deterministic across Python sessions and platforms (json
    with sort_keys + canonical float repr)."""
    payload = {
        name: _config_field_canonical(getattr(config, name))
        for name in _GEOMETRY_CACHE_RELEVANT_FIELDS
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _canonical_advisory_config_payload(config: DoorPlacementConfig) -> str:
    """Stable JSON serialization of the advisory-cache-relevant subset."""
    payload = {
        name: _config_field_canonical(getattr(config, name))
        for name in _ADVISORY_CACHE_RELEVANT_FIELDS
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


# =============================================================================
# Hash primitives
# =============================================================================

def _sha256_hex(payload: str) -> str:
    """SHA-256 hex digest of a UTF-8 string. Deterministic, stable
    across Python versions + platforms (sha256 is well-specified)."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =============================================================================
# Public cache-key builders
# =============================================================================

def build_geometry_cache_key(
    *,
    config: DoorPlacementConfig,
    upstream_c12_cache_key: str,
) -> str:
    """Build the geometry_cache_key per v0.2 A10 + v0.4 C10.

    Components (all enter the sha256):
    - C13_VERSION
    - C13_EDGE_PROTOCOL_VERSION
    - EXPECTED_C12_VERSION
    - EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION
    - EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION
    - upstream_c12_cache_key (PlacementBatchResult.cache_key from C12)
    - canonical serialization of geometry-cache-relevant config fields

    Args:
        config: the DoorPlacementConfig used for this batch.
        upstream_c12_cache_key: the cache_key C12 emitted for the
            upstream PlacementBatchResult. Carrying this forward ties
            C13's cache to the exact C12 geometry it consumed.

    Returns:
        sha256 hex digest as a 64-character lowercase string.

    Raises:
        ValueError: if upstream_c12_cache_key is empty.
    """
    if not upstream_c12_cache_key:
        raise ValueError(
            "build_geometry_cache_key: upstream_c12_cache_key must be "
            "non-empty."
        )
    geometry_payload = "||".join((
        f"c13_version={C13_VERSION}",
        f"c13_edge_protocol_version={C13_EDGE_PROTOCOL_VERSION}",
        f"expected_c12_version={EXPECTED_C12_VERSION}",
        f"expected_c8_schema_version={EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION}",
        f"expected_c9_schema_version={EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION}",
        f"upstream_c12_cache_key={upstream_c12_cache_key}",
        f"geometry_config={_canonical_geometry_config_payload(config)}",
    ))
    return _sha256_hex(geometry_payload)


def build_advisory_cache_key(
    *,
    geometry_cache_key: str,
    config: DoorPlacementConfig,
) -> str:
    """Build the advisory_cache_key per v0.4 C10 + v0.5 D7 (Inv D18).

    Construction (matches C13CacheKeys.__post_init__ check):

        advisory_cache_key =
            geometry_cache_key + "::" + sha256(
                ADVISORY_SCHEMA_VERSION || canonical_advisory_config
            )

    The geometry_cache_key PREFIX makes Inv D18 testable via simple
    startswith() check rather than relying on opaque hash-input
    inclusion.

    Args:
        geometry_cache_key: must be non-empty. Becomes the literal
            prefix of advisory_cache_key per Inv D18.
        config: DoorPlacementConfig (advisory-cache-relevant fields
            participate; geometry-cache-relevant fields do NOT — they
            already flowed into geometry_cache_key).

    Returns:
        f"{geometry_cache_key}::{advisory_payload_hash}" where the hash
        is sha256-hex over advisory-config payload.

    Raises:
        ValueError: if geometry_cache_key is empty.
    """
    if not geometry_cache_key:
        raise ValueError(
            "build_advisory_cache_key: geometry_cache_key must be "
            "non-empty (it becomes the prefix per Inv D18)."
        )
    advisory_payload = "||".join((
        f"advisory_schema_version={ADVISORY_SCHEMA_VERSION}",
        f"advisory_config={_canonical_advisory_config_payload(config)}",
    ))
    advisory_payload_hash = _sha256_hex(advisory_payload)
    return f"{geometry_cache_key}{_ADVISORY_CACHE_KEY_SEPARATOR}{advisory_payload_hash}"


def build_full_cache_key(
    *,
    geometry_cache_key: str,
    advisory_cache_key: str,
) -> str:
    """Build the full_cache_key per v0.4 C10.

    Construction: sha256 of geometry_cache_key + "::" + advisory hash
    (which is the suffix portion of advisory_cache_key).

    The full_cache_key is for full-result replay (includes both
    positioning AND advisory data). Distinct from advisory_cache_key
    in that the latter is a structured prefix-+-hash string (visible
    geometry prefix) while full_cache_key is an opaque hash.

    Args:
        geometry_cache_key: the geometry domain key.
        advisory_cache_key: the advisory domain key (must satisfy
            Inv D18 startswith).

    Returns:
        sha256 hex digest of geometry + separator + advisory-payload-hash.

    Raises:
        ValueError: if Inv D18 prefix check fails OR either arg empty.
    """
    if not geometry_cache_key:
        raise ValueError(
            "build_full_cache_key: geometry_cache_key must be non-empty."
        )
    if not advisory_cache_key:
        raise ValueError(
            "build_full_cache_key: advisory_cache_key must be non-empty."
        )
    # Sanity check Inv D18 here too (it's also enforced in C13CacheKeys
    # __post_init__; we check at construction time to fail early).
    if not advisory_cache_key.startswith(geometry_cache_key):
        raise ValueError(
            f"build_full_cache_key: advisory_cache_key violates Inv D18 — "
            f"must start with geometry_cache_key. "
            f"advisory_cache_key={advisory_cache_key!r}, "
            f"geometry_cache_key={geometry_cache_key!r}."
        )
    full_payload = "||".join((
        f"geometry={geometry_cache_key}",
        f"advisory={advisory_cache_key}",
    ))
    return _sha256_hex(full_payload)


def build_c13_cache_keys(
    *,
    config: DoorPlacementConfig,
    upstream_c12_cache_key: str,
) -> C13CacheKeys:
    """Canonical builder: derive all three keys + assemble C13CacheKeys.

    This is the primary entry point for cache-key construction in C13.
    Direct construction of C13CacheKeys is permitted (the dataclass
    enforces Inv D18) but this builder centralizes the derivation.

    Args:
        config: the DoorPlacementConfig used for this batch.
        upstream_c12_cache_key: PlacementBatchResult.cache_key from C12.

    Returns:
        C13CacheKeys with all three keys derived and Inv D18 satisfied.
    """
    geometry_cache_key = build_geometry_cache_key(
        config=config,
        upstream_c12_cache_key=upstream_c12_cache_key,
    )
    advisory_cache_key = build_advisory_cache_key(
        geometry_cache_key=geometry_cache_key,
        config=config,
    )
    full_cache_key = build_full_cache_key(
        geometry_cache_key=geometry_cache_key,
        advisory_cache_key=advisory_cache_key,
    )
    return C13CacheKeys(
        geometry_cache_key=geometry_cache_key,
        advisory_cache_key=advisory_cache_key,
        full_cache_key=full_cache_key,
    )


__all__ = [
    "build_geometry_cache_key",
    "build_advisory_cache_key",
    "build_full_cache_key",
    "build_c13_cache_keys",
]
