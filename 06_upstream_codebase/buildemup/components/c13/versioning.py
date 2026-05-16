"""
BuildemUp — Component 13 — versioning constants
================================================

Per C13 SPEC v1.0 LOCKED.

LOCKED constants this module exposes:

| Constant                                          | Value     | Source            |
|---------------------------------------------------|-----------|-------------------|
| C13_VERSION                                       | "v1.0"    | v0.1 § 1.3        |
| C13_EDGE_PROTOCOL_VERSION                         | 1         | v0.4 C3           |
| ADVISORY_SCHEMA_VERSION                           | 1         | v0.4 C8           |
| MAX_DOORS_PER_ROOM_V1                             | 2         | v0.4 C4           |
| EXPECTED_C12_VERSION                              | "v1.0"    | v0.1 § 1.3        |
| EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION          | 1         | v0.2 A10          |
| EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION         | 1         | v0.2 A10          |
| DEFAULT_CORNER_OFFSET_M                           | 0.15      | v0.2 A2 / v0.4 C1 |
| DEFAULT_GRID_SNAP_M                               | 0.05      | v0.2 A7 (from C12)|

Bump rules (mirroring C12 versioning module + C11b precedent):
- Removing public type / field / invariant → MAJOR
- Adding invariant / failure type / cache_relevant flip / changed
  default that affects output identity → MINOR
- Telemetry-only / new enum value on non-cache field / prose-only
  wording → PATCH

Per C13 SPEC v0.7 F3 (fast-revision stabilization-only constraint):
fast-revision-window patches that preserve v1.0 LOCKED contracts may
ship without MINOR bumps within the 90-day window. Patches that break
contracts require v1.1.
"""
from __future__ import annotations

from typing import Final


# =============================================================================
# C13_VERSION — the canonical component version string
# =============================================================================

C13_VERSION: Final[str] = "v1.0"
"""The LOCKED C13 version string per Ramalingam S44 path (c) LOCK
directive: "Lock it and give me the handoff."

Captured into DoorPlacementBatchResult.c13_version so cache lookups
invalidate cleanly when this string changes. A pre-v1.0 cache entry
deserialize-misses under v1.0 (no in-place migration)."""


# =============================================================================
# Protocol + advisory schema versions (per C13 spec v0.4 C3 + C8)
# =============================================================================

C13_EDGE_PROTOCOL_VERSION: Final[int] = 1
"""Per C13 v0.4 C3. The semantic version of the C13ConsumesFromC12Edge
Protocol contract.

Bump rules (per v0.4 C3):
- Changing the SEMANTIC meaning of a field C13 reads from upstream
  (even if the field name is unchanged) → bump
- Adding a new field that C13 begins to depend on → bump
- Removing a field from the Protocol → bump

NOT bumped on:
- C12 SharedEdge schema changes that don't touch C13-read fields
- Internal C12 implementation changes that preserve Protocol semantics

Examples that would require a bump:
- overlap_length_m switches from "edge-line length" to "projected-to-grid length"
- doorway_feasible adds occupancy-dependent semantics"""

ADVISORY_SCHEMA_VERSION: Final[int] = 1
"""Per C13 v0.4 C8. The semantic version of the AdvisoryFlag schema +
flag_kind vocabulary.

Bump rules (per v0.4 C8):
- Adding new flag_kind values → MINOR (additive)
- Renaming / removing flag_kind values → MAJOR (breaking)
- Changing semantic meaning of an existing flag_kind → MAJOR

NOT bumped on:
- Internal severity recalibration (info → warning) — operational
- Density bound adjustments
- causal_context field population at v1.x (per v0.6 E3 reserved field;
  v1.0 ships with causal_context=None always, v1.x may populate without
  schema bump)
"""


# =============================================================================
# v1 hard scope bounds (per C13 spec v0.4 C4)
# =============================================================================

MAX_DOORS_PER_ROOM_V1: Final[int] = 2
"""Per C13 v0.4 C4. Hard cap on doors per room at v1.0 LOCK.

Bedrooms with multiple doors require an upstream override flag (filed
as B-C13-MULTI-DOOR-BEDROOM-OVERRIDE for luxury master suites with
attached dressing rooms — v1.x).

Multi-door rooms beyond this cap require v1.1 spec amendment per
v0.7 F3 (fast-revision-window patches are stabilization-only)."""


# =============================================================================
# Expected upstream schema versions
# =============================================================================
# Per C13 v0.1 § 1.3 + v0.2 A10 — C13 probes upstream version constants at
# ingress; mismatch raises UpstreamSchemaDriftError.

EXPECTED_C12_VERSION: Final[str] = "v1.0"
"""C13 was built against C12 v1.0. Phase 0 ingress asserts
upstream C12_VERSION equals this; mismatch raises
UpstreamSchemaDriftError."""

EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION: Final[int] = 1
"""C13 was built against C8's CORRIDOR_ZONE_SCHEMA_VERSION = 1.
Per v0.2 A10 cache-key derivation includes this constant."""

EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION: Final[int] = 1
"""C13 was built against C9's ADJACENCY_HINT_SCHEMA_VERSION = 1.
Per v0.2 A10 cache-key derivation includes this constant."""


# =============================================================================
# Geometric defaults (per C13 spec v0.2 A2 / A7 / v0.4 C1)
# =============================================================================

DEFAULT_CORNER_OFFSET_M: Final[float] = 0.15
"""Per C13 v0.2 A2 (150mm — Neufert ergonomic minimum). Replaces v0.1's
unrealistic 0.0 default which produced high swing-conflict frequency at
corners (columns, chases, switches, wardrobes live there).

Configurable per batch via DoorPlacementConfig.corner_offset_m.
Cache-relevant: yes (changes door geometry)."""

DEFAULT_GRID_SNAP_M: Final[float] = 0.05
"""Per C13 v0.2 A7. Inherited from C12.bounds.DEFAULT_GRID_SNAP_M (50mm).

Used to snap door position_along_edge_m to the deterministic grid
resolution, preventing FP drift from breaking Inv D7 byte-equal
replay. Same mechanism as C12 v0.2-A4 rule #4.

Re-exported here (instead of imported from C12) per v0.2 A7's
"Re-export from C13 to avoid direct C12-internal dependency"
direction."""

DEFAULT_LEAF_THICKNESS_M: Final[float] = 0.04
"""Per C13 v0.2 A3 — 40mm Indian standard residential door leaf thickness.

The Door schema makes this a required field for v1 to keep
constructions explicit, but the canonical default value lives here so
Phase E assembly can populate it consistently. Configurable per batch
via DoorPlacementConfig in v1.x if production data demands it
(B-C13-LEAF-THICKNESS-CONFIGURABLE — not v1-LOCK-blocking).

Cache-relevant: yes (changes swept-volume geometry)."""


__all__ = [
    "C13_VERSION",
    "C13_EDGE_PROTOCOL_VERSION",
    "ADVISORY_SCHEMA_VERSION",
    "MAX_DOORS_PER_ROOM_V1",
    "EXPECTED_C12_VERSION",
    "EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION",
    "EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION",
    "DEFAULT_CORNER_OFFSET_M",
    "DEFAULT_GRID_SNAP_M",
    "DEFAULT_LEAF_THICKNESS_M",
]
