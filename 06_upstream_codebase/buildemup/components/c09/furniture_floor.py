"""
BuildemUp† — Component 9 (Room Sizer) — Furniture floor KB lookup.

Per C9 SPEC v0.7 LOCKED § 4.2 (Liveability minimums).

Loads ``kb/furniture_floor.json`` once at module import. Lookup keyed by
(category, is_master, bathroom_subtype) returning the (area_m2, min_width_m,
ref_config) furniture floor used in liveability resolution:

    liveability_min_area_m2  = max(regulatory.area_m2,  furniture.area_m2)
    liveability_min_width_m  = max(regulatory.width_m,  furniture.min_width_m)

†= placeholder name marker.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from buildemup.components.c09.schema import (
    BathroomSubtype,
    RoomCategory,
)


# =============================================================================
# Public dataclass
# =============================================================================


@dataclass(frozen=True)
class FurnitureFloor:
    """Furniture-fit floor for one (category, is_master, bathroom_subtype) row."""
    area_m2: float
    min_width_m: float
    ref_config: str


# =============================================================================
# Module-level KB load
# =============================================================================

_KB_PATH = Path(__file__).resolve().parent.parent.parent / "kb" / "furniture_floor.json"


def _load_kb() -> dict:
    with _KB_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_KB = _load_kb()


def _build_index() -> dict[tuple[str, bool, str | None], FurnitureFloor]:
    index: dict[tuple[str, bool, str | None], FurnitureFloor] = {}
    for row in _KB["rows"]:
        ff = FurnitureFloor(
            area_m2=float(row["area_m2"]),
            min_width_m=float(row["min_width_m"]),
            ref_config=row["ref_config"],
        )
        key = (
            row["category"],
            bool(row["is_master"]),
            row["bathroom_subtype"],
        )
        if key in index:
            raise RuntimeError(
                f"Furniture KB integrity error: duplicate row for key {key}"
            )
        index[key] = ff
    return index


_INDEX = _build_index()
KB_VERSION: str = _KB["kb_version"]


# Default furniture floor for OTHER (per § 14.34 — pooled v1 behaviour); zero
# minimums let the regulatory minimum dominate (which is also zero for OTHER).
_OTHER_DEFAULT = FurnitureFloor(
    area_m2=4.0,                  # nominal floor for unspecified OTHER rooms
    min_width_m=1.5,
    ref_config="OTHER pooled v1 — generic 4.0 m^2 / 1.5 m floor; B-151 will refine",
)


# =============================================================================
# Public lookup
# =============================================================================


def lookup_furniture_floor(
    *,
    category: RoomCategory,
    is_master: bool = False,
    bathroom_subtype: BathroomSubtype | None = None,
) -> FurnitureFloor:
    """Return the FurnitureFloor for the given (category, is_master, subtype) key.

    Per § 4.2 / § 14.34. OTHER category falls through to the pooled default
    (B-151 deferred for subtype-driven differentiation).

    Args:
        category: RoomCategory.
        is_master: True for master variants.
        bathroom_subtype: required for BATHROOM; None otherwise.

    Returns:
        Frozen FurnitureFloor.

    Raises:
        KeyError: when no row matches and category is not OTHER (KB defect).
        TypeError / ValueError: bad input types or missing/extraneous bathroom_subtype.
    """
    if not isinstance(category, RoomCategory):
        raise TypeError(
            f"lookup_furniture_floor.category must be RoomCategory; "
            f"got {type(category).__name__}"
        )
    if bathroom_subtype is not None and not isinstance(
        bathroom_subtype, BathroomSubtype
    ):
        raise TypeError(
            "lookup_furniture_floor.bathroom_subtype must be BathroomSubtype "
            f"or None; got {type(bathroom_subtype).__name__}"
        )
    if category == RoomCategory.BATHROOM and bathroom_subtype is None:
        raise ValueError(
            "lookup_furniture_floor: BATHROOM requires a bathroom_subtype"
        )
    if category != RoomCategory.BATHROOM and bathroom_subtype is not None:
        raise ValueError(
            f"lookup_furniture_floor: non-BATHROOM category {category.value} "
            f"must NOT supply bathroom_subtype; got {bathroom_subtype.value}"
        )

    if category == RoomCategory.OTHER:
        return _OTHER_DEFAULT

    key = (
        category.value,
        is_master,
        bathroom_subtype.value if bathroom_subtype is not None else None,
    )
    ff = _INDEX.get(key)
    if ff is None:
        raise KeyError(
            f"Furniture KB has no row for "
            f"category={category.value}, is_master={is_master}, "
            f"bathroom_subtype="
            f"{bathroom_subtype.value if bathroom_subtype else None}"
        )
    return ff


__all__ = [
    "FurnitureFloor",
    "KB_VERSION",
    "lookup_furniture_floor",
]
