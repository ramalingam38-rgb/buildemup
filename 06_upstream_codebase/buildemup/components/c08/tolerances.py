"""
BuildemUp† — Component 8 — Centralized tolerance policy (B-142).

Per S33 walk #1 review (Ramalingam Finding #10) — replaces scattered
``1e-9`` / ``1e-12`` / ``1e-6`` magic numbers with named tolerance tiers.

Three tiers, each with a documented purpose and scale rationale:

  STRUCTURAL_M     = 1e-3 (1mm)
    Coordinate-coincidence at the construction-tolerance scale.
    This is the primary EPSILON_M used for endpoint matching, junction
    coincidence, and any check whose meaning is tied to physical buildability.
    Equal to ``DEFAULT_EPSILON_M`` for backwards-compat.

  GEOMETRIC_M      = 1e-6 (1 micrometre)
    Geometric degeneracy / ratio-fraction tolerance. Used when comparing
    ratios, normalized scores, or testing whether a derived geometric
    quantity is "effectively zero" (degenerate strip after clipping,
    normalized score within [0, 1+eps], etc.). Three orders below
    construction tolerance — won't fire on legitimate construction noise.

  ARITHMETIC_M     = 1e-12 (1 picometre)
    Floating-point round-off tolerance. Used only for FP arithmetic
    sanity checks (e.g. "is this overlap rectangle non-empty after
    arithmetic"). Effectively the IEEE-754-double round-off scale.
    Should never carry physical or geometric meaning — only catches
    arithmetic-induced false positives/negatives.

Usage convention:
  - Coordinate equality, junction matching, point-in-segment           → STRUCTURAL_M
  - Score in [0, 1] tolerance, ratio degeneracy, "near-zero ratio"     → GEOMETRIC_M
  - Pure FP round-off (overlap area > 0?, rect non-empty after clip?)  → ARITHMETIC_M

Components must NOT introduce new bare ``1e-N`` literals; if a new
tolerance tier is needed, add it here with a docstring rationale.

†= placeholder name marker.
"""
from __future__ import annotations


# Tier 1 — physical/structural tolerance (1mm, sub-construction)
STRUCTURAL_M: float = 1.0e-3
"""Coordinate-coincidence tolerance at the construction-tolerance scale.
Two endpoints are coincident iff |dx|, |dy| < STRUCTURAL_M.
Same numeric value as ``DEFAULT_EPSILON_M`` (preserved for backward-compat).
"""

# Tier 2 — geometric/ratio tolerance (1 micrometre)
GEOMETRIC_M: float = 1.0e-6
"""Geometric degeneracy / ratio-fraction tolerance. Used for normalized
scores in [0, 1], testing whether derived geometry is effectively zero,
and ratio-based checks that should be insensitive to construction-scale
variation but should still catch FP-amplified errors at the ratio scale.
"""

# Tier 3 — arithmetic/round-off tolerance (1 picometre)
ARITHMETIC_M: float = 1.0e-12
"""Floating-point round-off tolerance. Catches FP-arithmetic-induced
false positives (e.g., "is this overlap rectangle non-empty after
intersection arithmetic?"). Carries no physical or geometric meaning.
"""


def epsilon_m_for(stage: str) -> float:
    """Return the tolerance for a named stage.

    Per S33 B-142 centralization. Use this when the caller doesn't
    have access to ``CorridorDesignConfig.epsilon_m`` (e.g., schema
    __post_init__ which runs without config) and needs a stage-tagged
    tolerance.

    Stages:
      - "structural" / "coordinate" / "junction" / "construction" → STRUCTURAL_M
      - "geometric" / "ratio" / "score"                            → GEOMETRIC_M
      - "arithmetic" / "round_off" / "fp"                          → ARITHMETIC_M

    Raises ValueError on unknown stage (forces explicit callsite tagging).
    """
    s = stage.lower()
    if s in ("structural", "coordinate", "junction", "construction"):
        return STRUCTURAL_M
    if s in ("geometric", "ratio", "score"):
        return GEOMETRIC_M
    if s in ("arithmetic", "round_off", "fp"):
        return ARITHMETIC_M
    raise ValueError(
        f"epsilon_m_for: unknown tolerance stage {stage!r}; "
        f"expected one of structural/coordinate/junction/construction, "
        f"geometric/ratio/score, arithmetic/round_off/fp."
    )


__all__ = [
    "STRUCTURAL_M",
    "GEOMETRIC_M",
    "ARITHMETIC_M",
    "epsilon_m_for",
]
