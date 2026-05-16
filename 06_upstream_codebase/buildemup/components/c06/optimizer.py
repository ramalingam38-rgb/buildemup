"""
BuildemUp† — Component 6 optimizer.

Permutation enumeration, entry-on-road pruning, total-score computation,
5-tier tie-break, hysteresis, margin-clamped confidence. Plus the private
_circulation_score helper (per § 14.20 / Q2).

Per SPEC v0.6 LOCKED §§ 4.3, 4.4, 4.5 + § 14.5–14.7, § 14.9–14.17, § 14.19, § 14.20.

Public-within-package surface (consumed by select.py only):
  - enumerate_permutations(seed_zone_bands, topology_kind, courtyard_bands)
  - prune_by_entry_on_road(perms, plot_facing, secondary_road_direction)
  - compute_function_scores(direction, climate, weights_applied, vastu_tier)
  - score_permutation(perm, function_scores_by_dir, climate_zone)
  - tie_break_key(perm, total, seed_perm, function_scores_by_dir)
  - hamming_distance(perm_a, perm_b)
  - apply_hysteresis(global_score, seed_score)
  - compute_confidence(top_score, second_score)
  - BAND_TO_FUNCTION constant

Private:
  - _circulation_score(direction, climate_zone)

†= placeholder name marker.
"""
from __future__ import annotations

import itertools
from types import MappingProxyType
from typing import Mapping

from buildemup.components.c04.schema import ClimateZone
from buildemup.components.c05.schema import TopologyKind, ZoneBand
from buildemup.components.c06.schema import (
    CARDINAL_FACINGS,
    MAX_PERMUTATION_COUNT,
    MIN_DENOM,
    SWAP_HYSTERESIS_THRESHOLD,
    FunctionRole,
)
from buildemup.components.c06.signals import (
    sun_function_lookup,
    sun_score,
    wind_function_lookup,
    wind_score,
)
from buildemup.components.c06.vastu_kb import vastu_score_4dir
from buildemup.domain.brief import VastuTier
from buildemup.domain.envelope import PlotOrientation


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — band → function mapping (CIRCULATION intentionally absent)
# ─────────────────────────────────────────────────────────────────────────────


BAND_TO_FUNCTION: Mapping[ZoneBand, FunctionRole] = MappingProxyType({
    ZoneBand.PUBLIC:  FunctionRole.LIVING,
    ZoneBand.SERVICE: FunctionRole.KITCHEN,
    ZoneBand.PRIVATE: FunctionRole.BEDROOM,
    # ZoneBand.CIRCULATION → NO mapping; uses _circulation_score private
    # helper instead. Per § 14.10 (light scoring) + § 14.20 (Q2 type fix).
})

FUNCTIONAL_BANDS: frozenset[ZoneBand] = frozenset(BAND_TO_FUNCTION.keys())


# Cardinal cycle order used for lexicographic tie-break (tier 5 of tie_break_key).
# Per SPEC § 4.4 step 4. Standard compass order N → E → S → W.
_CARDINAL_LEX_INDEX: Mapping[PlotOrientation, int] = MappingProxyType({
    PlotOrientation.NORTH: 0,
    PlotOrientation.EAST:  1,
    PlotOrientation.SOUTH: 2,
    PlotOrientation.WEST:  3,
})


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 1 — Permutation enumeration
# ─────────────────────────────────────────────────────────────────────────────


def enumerate_permutations(
    seed_zone_bands: Mapping[ZoneBand, PlotOrientation],
    topology_kind: TopologyKind,
) -> tuple[Mapping[ZoneBand, PlotOrientation], ...]:
    """Enumerate all band → cardinal-direction permutations.

    Per SPEC v0.6 § 4.4 step 1.

    For non-COURTYARD topologies (STRIP, CENTRAL_SPINE, L_SHAPE), bands map
    to DISTINCT cardinal directions: at most 4! = 24 permutations (or fewer
    if the band set is < 4).

    For COURTYARD (LOOP), bands wrap around a central open core and may
    share cardinal directions: at most 4^|bands| = 256 permutations
    (with |bands| = 4: PUBLIC, SERVICE, PRIVATE, CIRCULATION).

    Returns:
      Tuple of immutable (MappingProxyType) Mappings, each keyed by
      seed_zone_bands.keys() with cardinal PlotOrientation values.

    Defensive: if a non-COURTYARD seed has fewer bands than 4, the keyset
    is preserved (band set comes from the seed, not hardcoded).
    """
    bands = tuple(seed_zone_bands.keys())
    cardinals = tuple(sorted(CARDINAL_FACINGS, key=lambda d: _CARDINAL_LEX_INDEX[d]))

    if topology_kind == TopologyKind.COURTYARD:
        # Directions can repeat: itertools.product
        raw_iter = itertools.product(cardinals, repeat=len(bands))
    else:
        # Distinct directions: itertools.permutations (exhausts when |bands|>4)
        raw_iter = itertools.permutations(cardinals, len(bands))

    return tuple(
        MappingProxyType(dict(zip(bands, dir_tuple)))
        for dir_tuple in raw_iter
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 2 — Entry-on-road pruning + cap assertion
# ─────────────────────────────────────────────────────────────────────────────


def prune_by_entry_on_road(
    perms: tuple[Mapping[ZoneBand, PlotOrientation], ...],
    plot_facing: PlotOrientation,
    secondary_road_direction: PlotOrientation | None,
) -> tuple[Mapping[ZoneBand, PlotOrientation], ...]:
    """Keep only permutations whose PUBLIC band faces a road direction.

    Per SPEC v0.6 § 4.4 step 2 + § 14.6.

    A permutation survives if `perm[PUBLIC] == plot_facing` OR (on corner
    plots) `perm[PUBLIC] == secondary_road_direction`.

    Asserts `len(survivors) <= MAX_PERMUTATION_COUNT (= 256)` per § 14.17
    defense-in-depth.

    Note: PUBLIC must be present in the seed bandset; if absent (shouldn't
    happen with valid C5 candidates), no perm survives.
    """
    allowed: set[PlotOrientation] = {plot_facing}
    if secondary_road_direction is not None:
        allowed.add(secondary_road_direction)

    survivors = tuple(
        p for p in perms
        if ZoneBand.PUBLIC in p and p[ZoneBand.PUBLIC] in allowed
    )
    assert len(survivors) <= MAX_PERMUTATION_COUNT, (
        f"prune_by_entry_on_road: post-prune permutation count "
        f"{len(survivors)} exceeds MAX_PERMUTATION_COUNT={MAX_PERMUTATION_COUNT} "
        f"(§ 14.17 defense-in-depth assertion)"
    )
    return survivors


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — Per-direction function scores + CIRCULATION helper
# ─────────────────────────────────────────────────────────────────────────────


def compute_function_scores(
    direction: PlotOrientation,
    climate_zone: ClimateZone,
    weights_applied: Mapping[str, float],
    vastu_tier: VastuTier,
) -> Mapping[FunctionRole, float]:
    """Compute per-function scores for one cardinal direction.

    Per SPEC v0.6 § 4.3. Returns an immutable Mapping keyed by all 6
    FunctionRole members. Values are weighted blends:

        function_scores[f] = (
            sun_score(direction)        * sun_function_lookup(f)  * w_sun
          + wind_score(direction, clim) * wind_function_lookup(f) * w_wind
          + vastu_score_4dir(direction, f, tier)                  * w_vastu
        )

    Vastu term contribution is 0.0 when tier == OFF (since vastu_score is
    0.0 there); raises NotImplementedError(B-099) if tier == FULL.

    Returned scores are clamped to [0, 1] defensively. With weights_applied
    summing to 1.0 and individual sun/wind/vastu factors all in [0, 1],
    the sum is naturally in [0, 1] without clamping; the clamp is belt-and-
    suspenders against floating-point edge cases.
    """
    sun_v = sun_score(direction)
    wind_v = wind_score(direction, climate_zone)
    w_sun = weights_applied["sun"]
    w_wind = weights_applied["wind"]
    w_vastu = weights_applied["vastu"]

    out: dict[FunctionRole, float] = {}
    for f in FunctionRole:
        vastu_v = vastu_score_4dir(direction, f, vastu_tier)
        score = (
            sun_v * sun_function_lookup(f) * w_sun
            + wind_v * wind_function_lookup(f) * w_wind
            + vastu_v * w_vastu
        )
        # Defensive clamp against fp drift; should be in-range natively.
        out[f] = max(0.0, min(1.0, score))
    return MappingProxyType(out)


def _circulation_score(
    direction: PlotOrientation,
    climate_zone: ClimateZone,
) -> float:
    """Light circulation scoring. Private helper. Per SPEC v0.6 § 14.10 + § 14.20.

    NOT a key in DirectionPriorityScore.function_scores. Used only inside
    score_permutation() to weight the CIRCULATION band's contribution.

    Formula (per § 4.4 step 3):

        _circulation_score = 0.3 * sun_score(direction)
                           + 0.2 * wind_score(direction, climate_zone)
                           + 0.5

    Uses RAW direction-baseline sun/wind scores (§ 4.1.1 / § 4.1.2),
    not the weighted blended function_scores. The 0.5 baseline reflects
    that circulation tolerates any direction reasonably well; the
    sun/wind terms add modest bias toward bright/breezy faces.
    """
    return (
        0.3 * sun_score(direction)
        + 0.2 * wind_score(direction, climate_zone)
        + 0.5
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 3 — Total score per permutation
# ─────────────────────────────────────────────────────────────────────────────


def score_permutation(
    perm: Mapping[ZoneBand, PlotOrientation],
    function_scores_by_dir: Mapping[PlotOrientation, Mapping[FunctionRole, float]],
    climate_zone: ClimateZone,
) -> float:
    """Compute the total score for one band → direction permutation.

    Per SPEC v0.6 § 4.4 step 3:

        total_score(perm) = (
            Σ_(b ∈ functional_bands) function_scores[band_to_function[b]][perm[b]]
          + 0.5 × _circulation_score(perm[CIRCULATION])
        )

    The CIRCULATION term is multiplied by 0.5 in addition to its internal
    weighting (per § 14.10 light scoring) — together this damps the
    influence of corridor placement vs. functional band placement.

    If a band in `perm` is not in BAND_TO_FUNCTION and not CIRCULATION,
    it's silently skipped (defensive — should not happen with valid bandsets).

    If perm has no CIRCULATION band, the circulation term is 0.0 (defensive
    — STRIP topologies on small T1 plots may legitimately omit circulation).
    """
    total = 0.0
    for band, direction in perm.items():
        if band in BAND_TO_FUNCTION:
            f = BAND_TO_FUNCTION[band]
            total += function_scores_by_dir[direction][f]
        elif band == ZoneBand.CIRCULATION:
            total += 0.5 * _circulation_score(direction, climate_zone)
        # else: unknown band — skip defensively
    return total


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 4 — Hamming distance + 5-tier tie-break key
# ─────────────────────────────────────────────────────────────────────────────


def hamming_distance(
    perm_a: Mapping[ZoneBand, PlotOrientation],
    perm_b: Mapping[ZoneBand, PlotOrientation],
) -> int:
    """Count of (band, direction) pairs that differ between two permutations.

    Per SPEC v0.6 § 13. Range [0, |bands|]. Bands present in only one
    perm count as differing (defensive — should not happen with validated
    permutations from the same enumeration).
    """
    all_bands = set(perm_a.keys()) | set(perm_b.keys())
    return sum(1 for b in all_bands if perm_a.get(b) != perm_b.get(b))


def tie_break_key(
    perm: Mapping[ZoneBand, PlotOrientation],
    total_score: float,
    seed_perm: Mapping[ZoneBand, PlotOrientation],
    function_scores_by_dir: Mapping[PlotOrientation, Mapping[FunctionRole, float]],
) -> tuple[float, int, float, float, tuple[int, ...]]:
    """5-tier deterministic sort key. Per SPEC v0.6 § 4.4 step 4 + § 14.13.

    Sort ascending by this key → best permutation comes first.

    Tiers (all ties broken in order):
      1. -total_score                        — primary (higher score better)
      2. hamming_distance(perm, seed_perm)   — prefer minimal change from seed
      3. -function_scores[perm[PUBLIC]][LIVING]
                                             — prefer best LIVING placement
      4. -function_scores[perm[PRIVATE]][BEDROOM]
                                             — prefer best BEDROOM placement
      5. lex_band_direction(perm)            — final lexicographic determinism

    Defensive: if PUBLIC or PRIVATE is missing from perm, use 0.0 for the
    tier-3/tier-4 component (extreme degenerate case).
    """
    public_dir = perm.get(ZoneBand.PUBLIC)
    private_dir = perm.get(ZoneBand.PRIVATE)
    living_score = (
        function_scores_by_dir[public_dir][FunctionRole.LIVING]
        if public_dir is not None else 0.0
    )
    bedroom_score = (
        function_scores_by_dir[private_dir][FunctionRole.BEDROOM]
        if private_dir is not None else 0.0
    )
    # Lex tier: tuple of (band-sorted direction lex indices). Bands sorted
    # by their enum value for determinism across permutations.
    lex_tuple = tuple(
        _CARDINAL_LEX_INDEX[perm[b]]
        for b in sorted(perm.keys(), key=lambda x: x.value)
    )
    return (
        -total_score,
        hamming_distance(perm, seed_perm),
        -living_score,
        -bedroom_score,
        lex_tuple,
    )


# ─────────────────────────────────────────────────────────────────────────────
# § 4.4 step 4 — Hysteresis vs C5 seed
# ─────────────────────────────────────────────────────────────────────────────


def apply_hysteresis(
    global_top_score: float,
    seed_score: float,
) -> bool:
    """Should C6 swap from the seed to the global top? Per SPEC v0.6 § 4.4 step 4.

    Returns True iff `global_top_score - seed_score >= SWAP_HYSTERESIS_THRESHOLD`.
    Otherwise False — stick with the seed (avoids low-confidence churn).

    Per § 14.13 + § 14.5: when the global optimum and seed are tied on
    primary score (they often will be, since the seed is itself a valid
    candidate considered in the search), the diff is 0.0 — no swap.
    """
    return (global_top_score - seed_score) >= SWAP_HYSTERESIS_THRESHOLD


# ─────────────────────────────────────────────────────────────────────────────
# § 4.5 — Margin-clamped confidence
# ─────────────────────────────────────────────────────────────────────────────


def compute_confidence(top_score: float, second_score: float | None) -> float:
    """Margin-clamped confidence. Per SPEC v0.6 § 4.5 + § 14.15.

        priority_confidence = clamp(
            (top - second) / max(top, MIN_DENOM),
            0.0, 1.0
        )

    If `second_score` is None (only one survivor after pruning), returns
    1.0 (nothing to compare against; max possible confidence).
    """
    if second_score is None:
        return 1.0
    margin = top_score - second_score
    denom = max(top_score, MIN_DENOM)
    return max(0.0, min(1.0, margin / denom))


__all__ = [
    "BAND_TO_FUNCTION",
    "FUNCTIONAL_BANDS",
    "enumerate_permutations",
    "prune_by_entry_on_road",
    "compute_function_scores",
    "score_permutation",
    "hamming_distance",
    "tie_break_key",
    "apply_hysteresis",
    "compute_confidence",
]

