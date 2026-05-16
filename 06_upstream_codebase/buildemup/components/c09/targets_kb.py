"""
BuildemUp† — Component 9 (Room Sizer) — Room targets KB lookup.

Per C9 SPEC v0.7 LOCKED § 4.3 (Target sizes) + § 4.4 (Max sizes).

Loads ``kb/room_targets.json`` once at module import. Lookup by
(category, is_master) returning ``target_m2``. Max sizes computed as
``target_m2 * PER_CATEGORY_MAX_MULTIPLIER[category]`` (per § 4.4).

Q14 (open spec question): max_m2 multipliers may eventually move into the
JSON. v1 keeps them in code (PER_CATEGORY_MAX_MULTIPLIER lives in schema.py)
per the strict v0.7 LOCKED reading.

†= placeholder name marker.
"""
from __future__ import annotations

import json
from pathlib import Path

from buildemup.components.c09.schema import (
    PER_CATEGORY_MAX_MULTIPLIER,
    RoomCategory,
)


# =============================================================================
# Module-level KB load
# =============================================================================

_KB_PATH = Path(__file__).resolve().parent.parent.parent / "kb" / "room_targets.json"


def _load_kb() -> dict:
    with _KB_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_KB = _load_kb()


def _build_index() -> dict[tuple[str, bool], float]:
    index: dict[tuple[str, bool], float] = {}
    for row in _KB["rows"]:
        key = (row["category"], bool(row["is_master"]))
        if key in index:
            raise RuntimeError(
                f"Targets KB integrity error: duplicate row for key {key}"
            )
        index[key] = float(row["target_m2"])
    return index


_INDEX = _build_index()
KB_VERSION: str = _KB["kb_version"]


# OTHER falls through to pooled default per § 14.34. Use a modest target
# matching the OTHER furniture floor to keep Inv 7 (target >= liveability) safe.
_OTHER_DEFAULT_TARGET_M2: float = 5.0


# =============================================================================
# Public lookup
# =============================================================================


def lookup_target_m2(
    *,
    category: RoomCategory,
    is_master: bool = False,
) -> float:
    """Return the comfortable-target area for (category, is_master).

    Per § 4.3. OTHER falls through to the pooled v1 default.

    Args:
        category: RoomCategory.
        is_master: True for master bedroom / master bathroom.

    Returns:
        Target area in square meters.

    Raises:
        KeyError: when no row matches and category is not OTHER.
        TypeError: bad input types.
    """
    if not isinstance(category, RoomCategory):
        raise TypeError(
            f"lookup_target_m2.category must be RoomCategory; "
            f"got {type(category).__name__}"
        )

    if category == RoomCategory.OTHER:
        return _OTHER_DEFAULT_TARGET_M2

    key = (category.value, is_master)
    target = _INDEX.get(key)
    if target is None:
        # Fall back to is_master=False if the master variant isn't present
        # (e.g., asking for is_master=True on LIVING; LIVING is never master).
        fallback = _INDEX.get((category.value, False))
        if fallback is None:
            raise KeyError(
                f"Targets KB has no row for "
                f"category={category.value}, is_master={is_master}"
            )
        return fallback
    return target


def lookup_max_m2(
    *,
    category: RoomCategory,
    is_master: bool = False,
) -> float:
    """Return the max (waste-threshold) area for (category, is_master).

    Per § 4.4: ``max_m2 = target_m2 * PER_CATEGORY_MAX_MULTIPLIER[category]``.
    Q14 in spec § 15 may relocate the multiplier source; v1 keeps it in
    schema.py constants.

    Args:
        category: RoomCategory.
        is_master: True for master bedroom / master bathroom.

    Returns:
        Max area in square meters.
    """
    if not isinstance(category, RoomCategory):
        raise TypeError(
            f"lookup_max_m2.category must be RoomCategory; "
            f"got {type(category).__name__}"
        )
    target = lookup_target_m2(category=category, is_master=is_master)
    multiplier = PER_CATEGORY_MAX_MULTIPLIER[category]
    return round(target * multiplier, 6)  # float-fuzz guard


__all__ = [
    "KB_VERSION",
    "lookup_target_m2",
    "lookup_max_m2",
]
