"""
BuildemUp — Component 12 — versioning constants
================================================

Per C12 SPEC v1.0 LOCKED § 0.7.1 W6-3 pattern (inherited from C11b).
Centralizes all C12 version constants so future amendments are
auditable at a glance.

Bump rules (mirroring C11b spec § 0.3.4):
- Removing a public type / field / invariant → MAJOR
- Adding invariant / failure type / cache_relevant flip / changed
  default that affects output identity → MINOR
- Telemetry-only / new enum value on non-cache field / prose-only
  wording → PATCH

Per C12 SPEC v0.3-A6 (Q-10 resolution): C12 owns its own cache key
built as sha256(c11b_env_fingerprint || c12_config_cache_relevant_fields).
Owning the C12-side key with the env fingerprint as a prefix keeps the
dependency explicit instead of piggybacking C11b's cache.
"""
from __future__ import annotations

from typing import Final


# =============================================================================
# C12_VERSION — the canonical component version string
# =============================================================================

C12_VERSION: Final[str] = "v1.0"
"""The LOCKED C12 version string per S43 Ramalingam directive
("Lock it and start coding").

Captured into EnvironmentFingerprint.c12_version so cache lookups
invalidate cleanly when this string changes. A pre-v1.0 cache entry
deserialize-misses under v1.0 (no in-place migration)."""


# =============================================================================
# Expected upstream schema versions (per v0.4-A1 schema-version probes)
# =============================================================================

EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION: Final[int] = 1
"""C12 was built against C8's CORRIDOR_ZONE_SCHEMA_VERSION = 1.
Phase 0 step 4 asserts upstream constant matches this value; mismatch
raises UpstreamSchemaDriftError."""

EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION: Final[int] = 1
"""C12 was built against C9's ADJACENCY_HINT_SCHEMA_VERSION = 1.
Phase 0 step 4 asserts upstream constant matches this value; mismatch
raises UpstreamSchemaDriftError."""


__all__ = [
    "C12_VERSION",
    "EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION",
    "EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION",
]
