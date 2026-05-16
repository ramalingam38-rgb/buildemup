"""
BuildemUp† — Component 10 — Phase 5 (Provenance + Risk Breakdown) module.

Per C10 SPEC v1.0 LOCKED § 3 Phase 5 + § 4 Inv 21 (RemediationHint mutex
DAG validation). Q46 verdict: validate_remediation_graph runs both inside
Phase 5 and defensively in WetZonePlanProvenance.__post_init__.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from buildemup.components.c10.errors import RemediationGraphError


# =============================================================================
# Mutex DAG validation (Inv 21)
# =============================================================================


def validate_remediation_graph(hints: Sequence) -> None:
    """Validate the RemediationHint mutex graph per Inv 21.

    Invariants enforced:
      - mutex relationships form a DAG (no cycles)
      - retry_priority + lex(parameter) form deterministic total ordering
      - mutually_exclusive_with parameter references must exist as another
        hint's parameter (dangling refs are NOT errors at v1 — see F-v8-3 verdict)

    Raises:
        RemediationGraphError if any invariant violated.
    """
    if not hints:
        return

    parameters = {h.parameter for h in hints}
    edges: list[tuple[str, str]] = []
    for h in hints:
        for exc in h.mutually_exclusive_with:
            if exc in parameters:
                edges.append((h.parameter, exc))

    if _has_cycle(parameters, edges):
        raise RemediationGraphError(
            "RemediationHint mutex graph contains cycles; orchestration "
            "undefined. Inv 21 violation."
        )

    # Determinism check: (retry_priority, parameter) form a total ordering.
    # We don't need to enforce uniqueness here (two hints can share a
    # priority); the lex-ASC parameter tie-break gives total ordering.
    keys = [(h.retry_priority, h.parameter) for h in hints]
    if len(set(keys)) != len(keys):
        # Two hints with identical (priority, parameter) pair would be
        # ambiguous in the orchestrator's ordering.
        raise RemediationGraphError(
            "RemediationHint mutex graph contains duplicate "
            "(retry_priority, parameter) keys; ordering ambiguous. "
            "Inv 21 violation."
        )


def _has_cycle(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> bool:
    """DFS-based cycle detection. Lightweight; no networkx dependency
    (per F-v9 rejection)."""
    nodes = set(nodes)
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for u, v in edges:
        if u in adj and v in adj:
            adj[u].append(v)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in nodes}

    def visit(u: str) -> bool:
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                return True                # back-edge -> cycle
            if color[v] == WHITE and visit(v):
                return True
        color[u] = BLACK
        return False

    for n in nodes:
        if color[n] == WHITE and visit(n):
            return True
    return False


# =============================================================================
# Risk-breakdown weighted-severity computation (Phase 5 sub-step)
# =============================================================================


# Weights per spec § 3 Phase 5 (carried from v0.6/v0.7): 0.5/1.0/1.5.
# Tuned via B-219 post-launch.
_RISK_WEIGHT_LOW    = 0.5
_RISK_WEIGHT_MEDIUM = 1.0
_RISK_WEIGHT_HIGH   = 1.5


def compute_risk_level(score: float) -> "PlacementRiskLevel":
    """Map a weighted-severity score to a PlacementRiskLevel.

    Thresholds: score >= 3 -> HIGH, 1-2 -> MEDIUM, 0 -> LOW. (Carried from
    v0.4 § 3 Phase 5; B-219 calibrates post-ship.)
    """
    # Local import to avoid circular import at module load.
    from buildemup.components.c10.schema import PlacementRiskLevel
    if score >= 3.0:
        return PlacementRiskLevel.HIGH
    if score >= 1.0:
        return PlacementRiskLevel.MEDIUM
    return PlacementRiskLevel.LOW


__all__ = [
    "validate_remediation_graph",
    "compute_risk_level",
]
