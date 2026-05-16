"""
BuildemUp† — Component 10 — KB cross-validator.

Per C10 SPEC v1.0 LOCKED § 3 (KB cross-validation startup hook). Validates
that plumbing_minimums.json and plumbing_fixture_profiles.json are
mutually compatible:

  1. version pinning: profiles._compatible_with_minimums_kb_version
     equals minimums._kb_version
  2. orphan-reference check: every fixture_type referenced in profiles
     must exist in minimums
  3. semantic integrity: plausible-range checks per row
  4. orphan-minimum warnings: fixtures in minimums NOT referenced in
     profiles (forward-staged; warn-only)

†= placeholder name marker.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buildemup.components.c10.errors import KBVersionMismatchError


_KB_DIR = Path(__file__).resolve().parent.parent.parent / "kb"


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def load_plumbing_minimums() -> dict[str, Any]:
    return _load_json(_KB_DIR / "plumbing_minimums.json")


def load_plumbing_fixture_profiles() -> dict[str, Any]:
    return _load_json(_KB_DIR / "plumbing_fixture_profiles.json")


def validate_plumbing_kbs_compatibility(
    profiles_kb: dict[str, Any] | None = None,
    minimums_kb: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Validate the two plumbing KBs are mutually compatible.

    Args:
        profiles_kb: optionally pre-loaded profiles KB dict; if None, loads
            from disk.
        minimums_kb: optionally pre-loaded minimums KB dict; if None, loads
            from disk.

    Returns:
        Tuple of warning strings (orphan-minimum entries; advisory only).

    Raises:
        KBVersionMismatchError on any of:
          - version drift between profiles._compatible_with_minimums_kb_version
            and minimums._kb_version
          - orphan fixture types referenced in profiles but absent from minimums
          - semantic-integrity violation in any minimums row
    """
    if profiles_kb is None:
        profiles_kb = load_plumbing_fixture_profiles()
    if minimums_kb is None:
        minimums_kb = load_plumbing_minimums()

    # 1. Version pinning.
    declared = profiles_kb.get("_compatible_with_minimums_kb_version")
    actual = minimums_kb.get("_kb_version")
    if declared != actual:
        raise KBVersionMismatchError(
            f"Plumbing KB version drift: profiles declares compatibility "
            f"with minimums version {declared!r} but minimums actual "
            f"version is {actual!r}."
        )

    # 2. Orphan reference check.
    referenced = {
        ft for row in profiles_kb.get("rows", [])
        for ft in row.get("fixture_types", ())
    }
    available = {
        row["fixture_type"]
        for row in minimums_kb.get("rows", ())
    }
    orphans = referenced - available
    if orphans:
        raise KBVersionMismatchError(
            f"Plumbing fixture profiles reference orphan fixture types "
            f"absent from minimums KB: {sorted(orphans)}"
        )

    # 3. Semantic integrity.
    for row in minimums_kb.get("rows", ()):
        ft = row["fixture_type"]
        diam = row.get("min_pipe_diameter_mm")
        if not (isinstance(diam, (int, float)) and 25 <= diam <= 200):
            raise KBVersionMismatchError(
                f"{ft}: min_pipe_diameter_mm={diam} outside plausible "
                f"range [25, 200]"
            )
        seal = row.get("trap_seal_min_mm")
        if not (isinstance(seal, (int, float)) and 38 <= seal <= 100):
            raise KBVersionMismatchError(
                f"{ft}: trap_seal_min_mm={seal} outside plausible "
                f"range [38, 100]"
            )
        tam = row.get("trap_arm_max_m")
        if not (isinstance(tam, (int, float)) and tam > 0):
            raise KBVersionMismatchError(
                f"{ft}: trap_arm_max_m={tam} must be > 0"
            )

    # 4. Orphan-minimum warnings (forward-staged fixtures).
    orphan_minimums = available - referenced
    return tuple(
        f"orphan minimums entry: fixture_type {ft!r} present in minimums "
        f"but not referenced by any profiles row"
        for ft in sorted(orphan_minimums)
    )


def get_plumbing_minimum_for(fixture_type: str) -> dict[str, Any]:
    """Return the minimums-KB row for the given fixture_type.

    Raises:
        KeyError if fixture_type not in KB.
    """
    minimums = load_plumbing_minimums()
    for row in minimums.get("rows", ()):
        if row["fixture_type"] == fixture_type:
            return row
    raise KeyError(
        f"No plumbing-minimums row for fixture_type {fixture_type!r}"
    )


def get_fixture_types_for(
    room_category: str, bathroom_subtype: str | None,
) -> tuple[str, ...]:
    """Return the fixture_types tuple for (room_category, bathroom_subtype)
    from the profiles KB.

    Raises:
        KeyError if no matching row exists.
    """
    profiles = load_plumbing_fixture_profiles()
    for row in profiles.get("rows", ()):
        if (
            row["room_category"] == room_category
            and row.get("bathroom_subtype") == bathroom_subtype
        ):
            return tuple(row["fixture_types"])
    raise KeyError(
        f"No fixture-profile row for "
        f"(room_category={room_category!r}, bathroom_subtype={bathroom_subtype!r})"
    )


__all__ = [
    "load_plumbing_minimums",
    "load_plumbing_fixture_profiles",
    "validate_plumbing_kbs_compatibility",
    "get_plumbing_minimum_for",
    "get_fixture_types_for",
]
