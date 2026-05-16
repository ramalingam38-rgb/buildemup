"""
BuildemUp — Component 15 — Dimensions Package
================================================

Per C15 SPEC v0.2 LOCKED § 1.4 — the 10 dimensions of residential
lived quality. Each dimension lives in its own module, registering
its checks via a module-level `REGISTERED_CHECKS` tuple that
`registry.build_registry()` imports.

Sub-2 ships dim 1 only. Sub-3 adds dim 2, 3, 5, 6 (other fully-
runnable dimensions). Sub-4 adds dim 4, 7, 8 (partial) + 9, 10
(all-NA). Sub-5 ships the orchestrator that walks the registry.

This package's __init__ deliberately does NOT re-export per-
dimension checks at the package level — callers wanting checks
should use `registry.build_registry()` rather than poking
sub-modules directly. This keeps the data envelope visible only
through the registry.
"""
from __future__ import annotations

__all__: list[str] = []
