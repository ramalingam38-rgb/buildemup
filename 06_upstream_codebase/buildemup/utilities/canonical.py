"""
BuildemUp† — utilities/canonical.py

Per C7 amendment v0.8 LOCKED § 1 (and C10 v1.0 LOCKED § 3 Phase 5).

Module-level helpers for byte-identical replay snapshots. Centralised
here per Walk #8 reviewer #8 architectural direction (B-240). Both C7
(test helper) and C10 (replay snapshots) import from this module;
neither imports the other for canonical serialisation. Avoids
C7→C10 test-helper dependency inversion; preserves clean layering.

Public API:
    canonical_serialize(obj) -> str
    assert_wall_segment_order_independent(grid_factory, fn) -> None

†= placeholder name marker.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, fields, is_dataclass
from enum import Enum
from typing import Any, Callable

# Floating-point precision used by canonical serialisation. Matches C10 spec
# v1.0 LOCKED § 3 (rule_trace, replay snapshot rounding).
CANONICAL_FP_PRECISION = 6


def _canonicalize(obj: Any) -> Any:
    """Recursively convert obj to JSON-canonical form.

    - dict keys sorted lex-ASC (handled by json.dumps sort_keys=True)
    - dataclasses converted via field-by-field walk
    - frozenset / set converted to sorted list of canonicalised elements
    - tuple / list canonicalised element-wise (preserve source order)
    - Enum converted to .value
    - float rounded to CANONICAL_FP_PRECISION decimals
    - other primitives passed through
    """
    if obj is None or isinstance(obj, (bool, str, int)):
        return obj
    if isinstance(obj, float):
        return round(obj, CANONICAL_FP_PRECISION)
    if isinstance(obj, Enum):
        # Enum.value may be string or int; both serialise fine.
        return _canonicalize(obj.value)
    if isinstance(obj, (frozenset, set)):
        return sorted(_canonicalize(e) for e in obj)
    if isinstance(obj, dict):
        # Stringify keys for JSON; recursively canonicalise values.
        # json.dumps sort_keys=True will sort the outer dict; nested
        # dicts produced by _canonicalize are also dicts so they sort.
        return {str(k): _canonicalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(e) for e in obj]
    if is_dataclass(obj):
        # Use field iteration (not asdict) so we control nested behaviour
        # — asdict would deep-recurse and lose Enum/frozenset semantics.
        out: dict[str, Any] = {}
        for f in fields(obj):
            out[f.name] = _canonicalize(getattr(obj, f.name))
        return out
    # Fallback: rely on str representation. Documented as acceptable for
    # types not anticipated by v1; tests should fail if a critical replay
    # field hits this path.
    return str(obj)


def canonical_serialize(obj: Any) -> str:
    """Produce a byte-identical JSON representation of `obj`.

    Determinism guarantees:
    - dict keys sorted lex-ASC
    - tuple/list elements emitted in source order (caller responsibility)
    - float values rounded to 6 decimal places
    - frozenset/set converted to sorted list (lex-ASC over canonicalised
      elements)
    - Enum values converted via `.value` attribute
    - dataclasses field-by-field, recursive

    Used by C10 Phase 5 replay snapshots and C7 test helper to verify
    order-independence properties (W8 invariant).

    Args:
        obj: any structure of dataclasses, dicts, sequences, enums, primitives.

    Returns:
        JSON string with deterministic key/element ordering.
    """
    return json.dumps(
        _canonicalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def assert_wall_segment_order_independent(
    grid_factory: Callable[[tuple], Any],
    fn: Callable[[Any], Any],
    *,
    seed: int = 12345,
) -> None:
    """Verify that `fn` produces identical output when fed two Grids with
    the same wall_segments stored in different tuple orders.

    Used to catch W8 invariant violations: any production code path that
    iterates `grid.wall_segments` directly (rather than calling
    `grid.wall_segments_canonical()`) will produce different results
    across the two calls and fail this assertion.

    Args:
        grid_factory: callable taking a tuple of WallSegment and returning
            a Grid (or Grid-like object with `wall_segments` attribute).
            Allows the helper to build two Grids that differ ONLY in the
            internal storage order of `wall_segments`.
        fn: function under test — takes a Grid, returns any structure that
            `canonical_serialize()` can handle.
        seed: random seed for the shuffle (default 12345 for reproducibility).

    Raises:
        AssertionError if `canonical_serialize(fn(default_grid)) !=
                          canonical_serialize(fn(shuffled_grid))`.
    """
    # Build the canonical (default) Grid first to capture the segment
    # storage order produced by GridGenerator.
    canonical_grid = grid_factory(())
    default_segments = tuple(canonical_grid.wall_segments)
    if len(default_segments) <= 1:
        # Nothing meaningful to shuffle.
        return

    # Build a Grid with shuffled storage order.
    rng = random.Random(seed)
    shuffled = list(default_segments)
    while True:
        rng.shuffle(shuffled)
        if tuple(shuffled) != default_segments:
            break
    grid_default = grid_factory(default_segments)
    grid_shuffled = grid_factory(tuple(shuffled))

    out_default = fn(grid_default)
    out_shuffled = fn(grid_shuffled)
    canon_default = canonical_serialize(out_default)
    canon_shuffled = canonical_serialize(out_shuffled)
    if canon_default != canon_shuffled:
        raise AssertionError(
            "Function is wall_segment-order dependent (W8 violation):\n"
            f"  default order  -> {canon_default[:200]}...\n"
            f"  shuffled order -> {canon_shuffled[:200]}..."
        )
