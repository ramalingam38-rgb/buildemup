"""
BuildemUp† — Setback Calculator (Component 1).

Computes NBC/DCR-compliant setbacks for a plot per SPEC_v0.2 Section 3.

Branching logic (Drawback 1 fix):
  - CONTINUOUS → front + rear only, sides = 0
  - SEMI_DETACHED → 3 sides (shared side = 0)
  - DETACHED → 4 sides via tier table lookup

City resolution:
  - Chennai → full TNCDBR 2019 implementation
  - Other 5 cities → NBC fallback (explicitly disclosed)

Returns:
  (compliant_setbacks, source_authority_disclosure)

†= placeholder name marker.
"""
from __future__ import annotations

from buildemup.domain.plot import Plot, PlotType, SharedSide
from buildemup.domain.setbacks import Setbacks
from buildemup.utils.kb_rules_loader import (
    get_setback_rules_for_city, get_setback_authority_for_city,
)


def compute_compliant_setbacks(
    plot: Plot, building_height_m: float = 9.0,
) -> tuple[Setbacks, str]:
    """Compute the NBC/DCR-compliant setbacks for this plot.

    Args:
        plot: The Plot domain object.
        building_height_m: Estimated total building height. Default 9m
            (= G+2 at 3m per floor). Tier lookup may use this.

    Returns:
        (compliant_setbacks, source_authority):
          - compliant_setbacks: Setbacks instance with required minimums
          - source_authority: string like "TNCDBR 2019" or "NBC 2016 general"
    """
    if plot.plot_type == PlotType.CONTINUOUS:
        return _continuous_setbacks(plot)
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        return _semi_detached_setbacks(plot, building_height_m)
    else:
        return _detached_setbacks(plot, building_height_m)


def _detached_setbacks(
    plot: Plot, building_height_m: float,
) -> tuple[Setbacks, str]:
    """4-side setbacks for DETACHED plots, tier-based on plot area."""
    city_rules = get_setback_rules_for_city(plot.city)
    tiers = city_rules["detached"]["tiers"]
    plot_area = plot.area_sqm

    # Find the first tier whose plot_area_max_sqm >= plot_area.
    # If a tier has height_max_m, also check height.
    chosen_tier = None
    for tier in tiers:
        if plot_area > tier["plot_area_max_sqm"]:
            continue
        # Height filter (optional, not all tiers have it)
        height_max = tier.get("height_max_m")
        if height_max is not None and building_height_m > height_max:
            continue
        chosen_tier = tier
        break

    # Fallback: use the last (largest) tier if nothing matched
    if chosen_tier is None:
        chosen_tier = tiers[-1]

    setbacks = Setbacks(
        front_m=float(chosen_tier["front_m"]),
        rear_m=float(chosen_tier["rear_m"]),
        side_left_m=float(chosen_tier["side_left_m"]),
        side_right_m=float(chosen_tier["side_right_m"]),
    )
    authority = get_setback_authority_for_city(plot.city)
    return setbacks, authority


def _semi_detached_setbacks(
    plot: Plot, building_height_m: float,
) -> tuple[Setbacks, str]:
    """3-side setbacks: use DETACHED tier, zero out shared side."""
    base_setbacks, authority = _detached_setbacks(plot, building_height_m)

    # Zero the shared side
    if plot.shared_side == SharedSide.LEFT:
        setbacks = Setbacks(
            front_m=base_setbacks.front_m,
            rear_m=base_setbacks.rear_m,
            side_left_m=0.0,
            side_right_m=base_setbacks.side_right_m,
        )
    else:  # SharedSide.RIGHT (enforced by Plot.__post_init__)
        setbacks = Setbacks(
            front_m=base_setbacks.front_m,
            rear_m=base_setbacks.rear_m,
            side_left_m=base_setbacks.side_left_m,
            side_right_m=0.0,
        )
    return setbacks, authority


def _continuous_setbacks(plot: Plot) -> tuple[Setbacks, str]:
    """Row-house / CBA: front + rear only, both sides = 0.

    Front setback depends on road width bucket.
    """
    city_rules = get_setback_rules_for_city(plot.city)
    cont = city_rules["continuous"]

    # Resolve front by road width
    road_width = plot.wider_road_width_m
    front_m = _lookup_front_by_road_width(
        cont["front_m_by_road_width"], road_width,
    )

    setbacks = Setbacks(
        front_m=front_m,
        rear_m=float(cont["rear_m"]),
        side_left_m=float(cont.get("side_left_m", 0.0)),
        side_right_m=float(cont.get("side_right_m", 0.0)),
    )
    authority = get_setback_authority_for_city(plot.city)
    return setbacks, authority


def _lookup_front_by_road_width(
    bucket_table: dict[str, float], road_width_m: float,
) -> float:
    """Resolve front setback from road-width bucket table.

    Bucket keys look like '3.0_to_7.0' (inclusive lower, exclusive upper)
    or '12.0_and_above'.

    Returns the largest-bucket value if road_width exceeds all buckets.
    """
    # Sort buckets by lower bound
    parsed_buckets = []
    for key, value in bucket_table.items():
        if key.startswith("_"):
            continue  # skip metadata keys
        if key.endswith("_and_above"):
            lower = float(key.replace("_and_above", ""))
            upper = float("inf")
        else:
            parts = key.split("_to_")
            lower = float(parts[0])
            upper = float(parts[1])
        parsed_buckets.append((lower, upper, float(value)))

    parsed_buckets.sort(key=lambda x: x[0])

    for lower, upper, value in parsed_buckets:
        if lower <= road_width_m < upper:
            return value

    # Fallback: use the largest bucket
    return parsed_buckets[-1][2]


def check_setback_compliance(
    user_stated: Setbacks, nbc_compliant: Setbacks,
) -> tuple[bool, tuple[str, ...]]:
    """Compare user-stated vs compliant setbacks.

    Returns:
        (is_compliant, violation_messages):
          - is_compliant: True if all four sides meet compliance
          - violation_messages: empty tuple if compliant, else messages
    """
    violations: list[str] = []
    diff = user_stated.difference_from(nbc_compliant)

    if diff["front_m"] < 0:
        violations.append(
            f"Front setback {user_stated.front_m}m is {abs(diff['front_m']):.1f}m "
            f"below the required {nbc_compliant.front_m}m."
        )
    if diff["rear_m"] < 0:
        violations.append(
            f"Rear setback {user_stated.rear_m}m is {abs(diff['rear_m']):.1f}m "
            f"below the required {nbc_compliant.rear_m}m."
        )
    if diff["side_left_m"] < 0:
        violations.append(
            f"Left side setback {user_stated.side_left_m}m is "
            f"{abs(diff['side_left_m']):.1f}m below the required "
            f"{nbc_compliant.side_left_m}m."
        )
    if diff["side_right_m"] < 0:
        violations.append(
            f"Right side setback {user_stated.side_right_m}m is "
            f"{abs(diff['side_right_m']):.1f}m below the required "
            f"{nbc_compliant.side_right_m}m."
        )

    return len(violations) == 0, tuple(violations)
