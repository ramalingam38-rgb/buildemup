"""
BuildemUp — Component 11a — Tier B cache (Sub-session 3)
==========================================================

Per spec § 0.3 + § 3.5 Step 0: ``DeepMutationCacheKey`` is a
signature-keyed memoisation token for ``DeepMutationPipeline``.

Cache scope:
  * Single batch — one ``mutate_topologies()`` invocation. Discarded
    at function return (§ 0.3 / Inv 30 single-threaded contract).
  * Bounded: at most ``len(enabled_operators) × len(input_candidates)``
    entries per batch — at v1 worst-case 16 × 8 = 128.

The cache key is the canonical-serialised triple
``(operator, source_topology_signature_hash, config_hash)``. Per § 2.6,
``config_hash`` is the SHA256 of the cache-relevant fields of
``TopologyMutationConfig`` only — cache-irrelevant fields (provenance
verbosity, registry validation mode, etc.) MUST NOT participate so
re-running with different presentation flags hits the cache.

Sub-session 4 will wire ``deep_mutation_cache_enabled`` into the
pipeline — when the flag is False, the cache is bypassed (used at
debugging time when comparing two configs that differ only in
cache-irrelevant fields).

== B-NEW-W partial (S39 critique walk F7) ==

The cache key now folds in C11a's own implementation version
(``C11A_CACHE_KEY_VERSION``) and an optional ``UpstreamVersionInfo``
struct describing the upstream KBs. Sub-3's single-batch cache scope
makes the version fold safe (the cache is discarded at batch end), but
adding it now sets the design up cleanly for B-NEW-E2 (process-
lifetime cache). With versions in the key, a process-lifetime cache
correctly invalidates entries across upstream KB updates / C11a
version bumps.

Full B-NEW-W (cross-batch invalidation epochs, runtime KB-version
drift detection) is gated on B-NEW-E2 landing. This partial is the
v1 floor.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from buildemup.components.c11a.schema import (
    MutationOperator,
    TopologyMutationConfig,
)


# =============================================================================
# C11a implementation version (B-NEW-W partial)
# =============================================================================
#
# Bump on any change that alters what cache hits SHOULD or SHOULDN'T
# return — i.e., changes to:
#   - operator implementations (Tier A or B)
#   - predicate registry contents or order
#   - lineage classification semantics
#   - delta-key vocabulary
#
# Source-edit gate: any of the above changes should land in the same
# PR that bumps this constant.

C11A_CACHE_KEY_VERSION: str = "v1.3.0"


# =============================================================================
# UpstreamVersionInfo (B-NEW-W partial)
# =============================================================================


@dataclass(frozen=True)
class UpstreamVersionInfo:
    """Records upstream KB versions at batch start.

    The orchestrator passes this to ``derive_cache_config_hash`` /
    ``derive_cache_key`` so cache hits are scoped to (a fixed
    upstream KB version × C11a implementation version × config-relevant
    fields).

    Sub-3/Sub-4 constructors accept ``None`` (pre-B-NEW-W behaviour
    preserved); when None, the version-fold is omitted from the hash
    and the cache key matches the legacy format. Real wiring lands
    with B-NEW-E2.

    Field defaults are empty strings (not "unknown") so a partial-fill
    instance still hashes deterministically.
    """

    c7_kb_version: str = ""
    c9_furniture_kb_version: str = ""
    c9_targets_kb_version: str = ""
    c10_plumbing_kb_version: str = ""
    c10_fixture_profiles_kb_version: str = ""

    def to_serialised_parts(self) -> tuple[str, ...]:
        """Stable string serialisation for inclusion in the config hash.

        Sorted alphabetically by component-and-field for byte-identical
        output across module reloads.
        """
        return tuple(
            sorted(
                f"{f.name}={getattr(self, f.name)}"
                for f in dataclasses.fields(self)
            )
        )


# =============================================================================
# DeepMutationCacheKey
# =============================================================================


@dataclass(frozen=True)
class DeepMutationCacheKey:
    """Per § 0.3 — signature-keyed memoisation token.

    Two cache-key triples are equal iff the operator + source signature
    + cache-relevant config bytes are byte-identical. This is the
    sufficient condition for Tier B replay determinism: two pipelines
    invoked with equal keys MUST produce equal regenerated candidates
    (per Inv 17 atomicity + Inv 25 upstream purity).
    """

    operator: MutationOperator
    source_topology_signature_hash: str    # 16-hex SHA256 prefix
    config_hash: str                        # 16-hex SHA256 prefix


# =============================================================================
# Config hash derivation
# =============================================================================


def _serialise_config_value(value: Any) -> str:
    """Stable string serialisation of a config field's value for hashing.

    Tuples / lists serialise element-wise (for stable iteration order).
    Sets are sorted before serialisation. Enums use ``.value``. Frozen
    dataclasses use ``dataclasses.fields`` walk. Other primitives use
    ``repr``.
    """
    # Enum (str-based)
    if hasattr(value, "value") and isinstance(value, MutationOperator):
        return value.value
    if hasattr(value, "value") and hasattr(type(value), "__members__"):
        return f"{type(value).__name__}.{value.value}"
    # Tuple / list
    if isinstance(value, (tuple, list)):
        return "[" + ",".join(_serialise_config_value(v) for v in value) + "]"
    # Frozenset / set — sorted for determinism
    if isinstance(value, (frozenset, set)):
        return "{" + ",".join(
            sorted(_serialise_config_value(v) for v in value)
        ) + "}"
    # Frozen dataclass
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        parts = []
        for f in dataclasses.fields(value):
            parts.append(
                f"{f.name}={_serialise_config_value(getattr(value, f.name))}"
            )
        return f"{type(value).__name__}({','.join(parts)})"
    # Bool, int, float, str, None
    return repr(value)


def derive_cache_config_hash(
    config: TopologyMutationConfig,
    *,
    upstream_versions: Optional[UpstreamVersionInfo] = None,
) -> str:
    """Per § 2.6 — return SHA256-prefix hash of the cache-relevant
    fields of ``config``, plus C11a implementation version, plus
    optional upstream KB versions.

    Cache-irrelevant fields (those whose
    ``metadata['cache_relevant']`` is False) are EXCLUDED. Two configs
    that differ only in cache-irrelevant fields produce the same hash
    — so the same source candidate + operator hits the cache regardless
    of presentation/diagnostic flag changes.

    Per B-NEW-W partial: ``C11A_CACHE_KEY_VERSION`` is always folded
    in; ``upstream_versions`` is folded in when provided. Both are
    stable for a given runtime, so single-batch cache scope is
    unaffected. Pre-B-NEW-W callers (omitting ``upstream_versions``)
    get hashes that include only the C11a version + config — the same
    values are reproduced regardless of whether the caller provides
    versions.

    Returns the first 16 hex chars of SHA256 — matches the
    ``derive_variant_id`` format from Sub-2 for visual consistency.
    """
    parts: list[str] = []
    for f in dataclasses.fields(config):
        if not f.metadata.get("cache_relevant", False):
            continue
        value = getattr(config, f.name)
        parts.append(f"{f.name}={_serialise_config_value(value)}")

    # Sort for stability across field-declaration-order changes — though
    # dataclass fields() preserves declaration order, sorting is a safety
    # net for replay across module reloads.
    parts.sort()

    # B-NEW-W partial: prepend the C11a implementation version.
    parts.insert(0, f"__c11a_version__={C11A_CACHE_KEY_VERSION}")

    # B-NEW-W partial: fold upstream KB versions when supplied.
    if upstream_versions is not None:
        parts.extend(
            f"__upstream__.{p}"
            for p in upstream_versions.to_serialised_parts()
        )

    h = hashlib.sha256()
    h.update("\x1f".join(parts).encode("utf-8"))   # \x1f = unit separator
    return h.hexdigest()[:16]


# =============================================================================
# Cache key derivation
# =============================================================================


def derive_cache_key(
    operator: MutationOperator,
    source_topology_signature_hash: str,
    config: TopologyMutationConfig,
    *,
    upstream_versions: Optional[UpstreamVersionInfo] = None,
) -> DeepMutationCacheKey:
    """Build a ``DeepMutationCacheKey`` for the (operator, source, config)
    triple. ``source_topology_signature_hash`` is the source candidate's
    deterministic identity hash — Sub-4's orchestrator computes this
    from the candidate's ancestry; Sub-3 tests pass an explicit string.

    Per B-NEW-W partial: pass ``upstream_versions`` to fold KB-version
    strings into the config hash. Sub-3 tests omit; Sub-4 orchestrator
    omits at v1 (stays single-batch); B-NEW-E2 process-lifetime cache
    will pass real values.
    """
    config_hash = derive_cache_config_hash(
        config, upstream_versions=upstream_versions,
    )
    return DeepMutationCacheKey(
        operator=operator,
        source_topology_signature_hash=source_topology_signature_hash,
        config_hash=config_hash,
    )


__all__ = [
    "C11A_CACHE_KEY_VERSION",
    "DeepMutationCacheKey",
    "UpstreamVersionInfo",
    "derive_cache_config_hash",
    "derive_cache_key",
]
