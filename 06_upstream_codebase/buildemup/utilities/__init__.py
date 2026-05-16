"""
BuildemUp† — Utilities (cross-component infrastructure).

Per C7 amendment v0.8 LOCKED § 1 (B-240 IMPLEMENTED-IN-SPEC).

Houses cross-component helpers that must NOT live inside any single Track-3
component (else dependency-direction cycles). Both C7 (test helper) and C10
(replay snapshots) consume `canonical_serialize`; each component's tests
import from this module.

**Architectural rule**: production code in C7 (and other Track-3 components)
MUST NOT import from `buildemup.utilities`; only test paths and
re-export shims may do so. This preserves clean upward-only dependency
direction. Future contributors who add such an import erode the
architecture silently — see B-241 (CI lint rule, post v1).

†= placeholder name marker.
"""
from buildemup.utilities.canonical import (
    canonical_serialize,
    assert_wall_segment_order_independent,
)

__all__ = [
    "canonical_serialize",
    "assert_wall_segment_order_independent",
]
