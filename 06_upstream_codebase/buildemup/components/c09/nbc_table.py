"""
BuildemUp† — Component 9 (Room Sizer) — NBC table KB lookup.

Per C9 SPEC v0.7 LOCKED § 4.1 (Regulatory minimums) + § 14.4 (KB-managed JSON).

Loads ``kb/nbc_room_minimums.json`` once at module import and exposes
``lookup_nbc_minimum`` for per-room queries keyed by
(tier, category, is_master, bathroom_subtype). Results are cached by key.

Per § 14.4 / § 14.32, the strict-mode gate (require_verified_nbc) is enforced
at the orchestrator boundary — this module surfaces the row's source_confidence
and the orchestrator decides whether to raise NBCConfidenceTooLow.

†= placeholder name marker.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from buildemup.components.c09.schema import (
    BathroomSubtype,
    DwellingSizeTier,
    NBCSourceConfidence,
    RegulatoryMinimum,
    RoomCategory,
)


# =============================================================================
# Module-level KB load (cached)
# =============================================================================

_KB_PATH = Path(__file__).resolve().parent.parent.parent / "kb" / "nbc_room_minimums.json"


def _load_kb() -> dict:
    with _KB_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_KB = _load_kb()


# Build a lookup index: (tier, category_value, is_master, bathroom_subtype_value_or_None)
# -> RegulatoryMinimum
def _build_index() -> dict[tuple[str, str, bool, str | None], RegulatoryMinimum]:
    index: dict[tuple[str, str, bool, str | None], RegulatoryMinimum] = {}
    for row in _KB["rows"]:
        confidence_str = row["source_confidence"]
        confidence = NBCSourceConfidence(confidence_str)
        rm = RegulatoryMinimum(
            area_m2=float(row["area_m2"]),
            width_m=float(row["width_m"]),
            height_m=float(row["height_m"]),
            nbc_clause=row["nbc_clause"],
            source_confidence=confidence,
        )
        key = (
            row["tier"],
            row["category"],
            bool(row["is_master"]),
            row["bathroom_subtype"],  # may be None
        )
        if key in index:
            raise RuntimeError(
                f"NBC KB integrity error: duplicate row for key {key}"
            )
        index[key] = rm
    return index


_INDEX = _build_index()
KB_VERSION: str = _KB["kb_version"]


# =============================================================================
# Public lookup
# =============================================================================


def lookup_nbc_minimum(
    *,
    tier: DwellingSizeTier,
    category: RoomCategory,
    is_master: bool = False,
    bathroom_subtype: BathroomSubtype | None = None,
) -> RegulatoryMinimum:
    """Return the RegulatoryMinimum for the given key.

    Per § 4.1. Raises ``KeyError`` (KB integrity error) if no row matches —
    the orchestrator surfaces this as a systemic failure (the brief asks for
    a category we don't have NBC data for).

    For categories without NBC floors (POOJA), the row carries area_m2=0.0 and
    width_m=0.0; that is intentional and not a missing row.

    OTHER category has no NBC row in v1; callers must supply OTHER's regulatory
    minimum themselves (e.g. zero-minimum default; see room_sizer._materialise_rooms).

    Args:
        tier: SMALL or LARGE.
        category: RoomCategory.
        is_master: True for master bedroom / master bathroom.
        bathroom_subtype: required for BATHROOM category; ignored otherwise.

    Returns:
        Frozen RegulatoryMinimum.

    Raises:
        KeyError: when no row matches the key (KB integrity defect).
        TypeError: bad input types.
    """
    if not isinstance(tier, DwellingSizeTier):
        raise TypeError(
            f"lookup_nbc_minimum.tier must be DwellingSizeTier; "
            f"got {type(tier).__name__}"
        )
    if not isinstance(category, RoomCategory):
        raise TypeError(
            f"lookup_nbc_minimum.category must be RoomCategory; "
            f"got {type(category).__name__}"
        )
    if bathroom_subtype is not None and not isinstance(
        bathroom_subtype, BathroomSubtype
    ):
        raise TypeError(
            f"lookup_nbc_minimum.bathroom_subtype must be BathroomSubtype or None; "
            f"got {type(bathroom_subtype).__name__}"
        )

    if category == RoomCategory.BATHROOM and bathroom_subtype is None:
        raise ValueError(
            "lookup_nbc_minimum: BATHROOM requires a bathroom_subtype"
        )
    if category != RoomCategory.BATHROOM and bathroom_subtype is not None:
        raise ValueError(
            f"lookup_nbc_minimum: non-BATHROOM category {category.value} must "
            f"NOT supply bathroom_subtype; got {bathroom_subtype.value}"
        )

    # OTHER has no NBC row in v1
    if category == RoomCategory.OTHER:
        raise KeyError(
            "lookup_nbc_minimum: OTHER category has no NBC row in v1; caller "
            "must supply zero-minimum regulatory floor explicitly"
        )

    key = (
        tier.value,
        category.value,
        is_master,
        bathroom_subtype.value if bathroom_subtype is not None else None,
    )
    rm = _INDEX.get(key)
    if rm is None:
        raise KeyError(
            f"NBC KB has no row for "
            f"tier={tier.value}, category={category.value}, "
            f"is_master={is_master}, "
            f"bathroom_subtype="
            f"{bathroom_subtype.value if bathroom_subtype else None}"
        )
    return rm


def all_rows() -> tuple[RegulatoryMinimum, ...]:
    """Return all rows for diagnostics / tests."""
    return tuple(_INDEX.values())


__all__ = [
    "KB_VERSION",
    "lookup_nbc_minimum",
    "all_rows",
]
