"""
BuildemUp† — Component 3a Session 4: BriefChange application.

Per locked S4 SPEC v0.1 (`buildemup_S4_SPEC_v0_1_LOCKED.md`).

Public API:
    apply_brief_change(brief, change)   -> Brief
    apply_brief_changes(brief, changes) -> Brief

Both are pure: never mutate the input Brief. They construct a new
Brief via dataclasses.replace and let Brief.__post_init__ run
(implicit validation). On validation failure, they raise
BriefChangeIntegrityError with classification + context dict
suitable for the reason-aware error formatter (parent C3a spec
Section 4.8).

Design references:
  - parent C3a spec § 3.3 (integrity invariant)
  - parent C3a spec § 4.1 step [8] (apply step in main flow)
  - parent C3a spec § 4.8 (reason-aware errors → formatter)
  - locked S4 spec § 4 (field_path vocabulary)
  - locked S4 spec § 5 (dispatch table + error wrapping)
  - locked S4 spec § 6 (edge cases + invariants)
  - locked S4 spec § 7 (the 6 error classifications)
  - resolved Q1-Q10 in `02_S4_RESOLVED_QUESTIONS.md`

†= placeholder name marker.
"""
from __future__ import annotations
import dataclasses
from typing import Callable, Optional

from buildemup.domain.brief import Brief, BudgetRange
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import (
    FloorRequirement, RoomRequirement, RoomType, FloorUse,
    NBC_MINIMUM_ROOM_SIZES_SQM,
)
from buildemup.domain.extreme_case import (
    BriefChange,
    BriefChangeIntegrityError,
)


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────

# Classifications (must match BriefChangeIntegrityError.classify() docstring)
CLS_BEDROOM = "BEDROOM_COUNT_BELOW_MIN"
CLS_BUDGET = "BUDGET_BELOW_THRESHOLD"
CLS_FAR = "FAR_EXCEEDED_BY_CHANGE"            # reserved; not produced in v0.1
CLS_ROOM_AREA = "ROOM_AREA_BELOW_NBC_MIN"
CLS_FLOOR_COUNT = "FLOOR_COUNT_BELOW_MIN"
CLS_SETBACK_INVALID = "SETBACK_INVALID"       # B-014 (S54 fix)
CLS_UNKNOWN = "UNKNOWN"

# Per parent spec, brief enforces ≥1 floor in __post_init__
_MIN_FLOORS = 1
# We don't model min-bedrooms in Brief.__post_init__ as of S4 v0.1
# (Q5 in resolved questions). Reserved for future use.
_MIN_BEDROOMS = 1

# Bedroom room types — used by classifier to recognize bedroom paths
_BEDROOM_TYPES = (RoomType.BEDROOM_MASTER, RoomType.BEDROOM_REGULAR)


# ─────────────────────────────────────────────────────────────────────
# Per-handler implementations
# Each handler returns a NEW Brief. None of them mutate the input.
# ─────────────────────────────────────────────────────────────────────

def _handle_rooms_count(brief: Brief, change: BriefChange) -> Brief:
    """rooms.{room_type}.count INCREMENT delta.

    For every floor's RoomRequirement of the named type, add delta to
    its count. Rooms whose resulting count ≤ 0 are dropped from that
    floor's `rooms` tuple entirely (per S4 spec §4 row 1, Q5).

    Defensive: delta=0 is a no-op. S3 should never emit this, but we
    return the input Brief unchanged rather than producing a useless
    rebuild.
    """
    parts = change.field_path.split(".")
    if len(parts) != 3:
        raise BriefChangeIntegrityError(
            f"rooms.{{X}}.count requires 3 segments; got {change.field_path!r}",
            classification=CLS_UNKNOWN,
            context={"field_path": change.field_path},
        )
    target_room_type_str = parts[1]
    try:
        target_room_type = RoomType(target_room_type_str)
    except ValueError:
        raise BriefChangeIntegrityError(
            f"Unknown room type {target_room_type_str!r}",
            classification=CLS_UNKNOWN,
            context={"field_path": change.field_path},
        )

    try:
        delta = int(change.new_value)
    except (TypeError, ValueError):
        raise BriefChangeIntegrityError(
            f"rooms.{{X}}.count INCREMENT requires integer delta; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )

    if delta == 0:
        return brief

    new_floors = []
    for f in brief.floors:
        new_rooms = []
        for r in f.rooms:
            if r.room_type == target_room_type:
                new_count = r.count + delta
                if new_count > 0:
                    new_rooms.append(dataclasses.replace(r, count=new_count))
                # else: drop entirely
            else:
                new_rooms.append(r)
        new_floors.append(dataclasses.replace(f, rooms=tuple(new_rooms)))

    return dataclasses.replace(brief, floors=tuple(new_floors))


def _handle_rooms_all_size(brief: Brief, change: BriefChange) -> Brief:
    """rooms.all.size SET 'nbc_min'.

    For every RoomRequirement on every floor, drop preferred_size_sqm
    and min_size_sqm (set to None) so effective_size_sqm falls back
    to NBC_MINIMUM_ROOM_SIZES_SQM (per S4 spec §4 row 2, Q6).
    """
    if change.new_value != "nbc_min":
        raise BriefChangeIntegrityError(
            f"rooms.all.size SET only supports 'nbc_min'; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )

    new_floors = []
    for f in brief.floors:
        new_rooms = tuple(
            dataclasses.replace(r, min_size_sqm=None, preferred_size_sqm=None)
            for r in f.rooms
        )
        new_floors.append(dataclasses.replace(f, rooms=new_rooms))
    return dataclasses.replace(brief, floors=tuple(new_floors))


def _handle_floors_add(brief: Brief, change: BriefChange) -> Brief:
    """floors.add INCREMENT 1.

    Append a RESIDENTIAL FloorRequirement at floor_number = max_existing
    + 1 (or 0 if no floors). Empty rooms tuple. (Per S4 spec §4 row 3,
    Q2.)
    """
    try:
        delta = int(change.new_value)
    except (TypeError, ValueError):
        raise BriefChangeIntegrityError(
            f"floors.add INCREMENT requires integer delta; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )
    if delta <= 0:
        # Spec §6.4: floors.add is positive-only.
        raise BriefChangeIntegrityError(
            f"floors.add INCREMENT only supports positive delta; "
            f"got {delta}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": delta,
            },
        )
    if delta != 1:
        # S3 only ever emits delta=1 for floors.add. Anything else is
        # a programmer error.
        raise BriefChangeIntegrityError(
            f"floors.add INCREMENT only supports new_value=1; got {delta}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": delta,
            },
        )

    if not brief.floors:
        new_floor_number = 0
    else:
        new_floor_number = max(f.floor_number for f in brief.floors) + 1

    new_floor = FloorRequirement(
        floor_number=new_floor_number,
        floor_use=FloorUse.RESIDENTIAL,
        rooms=(),
        notes="",
    )
    return dataclasses.replace(brief, floors=brief.floors + (new_floor,))


def _handle_floors_index_delete(
    brief: Brief, change: BriefChange,
) -> Brief:
    """floors.{N} DELETE None.

    Remove the FloorRequirement whose floor_number == N. Renumber
    higher floors down by 1 to keep numbering contiguous.
    (Per S4 spec §4 row 4, §6.5, Q4.)
    """
    parts = change.field_path.split(".")
    if len(parts) != 2:
        raise BriefChangeIntegrityError(
            f"floors.{{N}} requires 2 segments; got {change.field_path!r}",
            classification=CLS_UNKNOWN,
            context={"field_path": change.field_path},
        )
    try:
        target_index = int(parts[1])
    except ValueError:
        raise BriefChangeIntegrityError(
            f"floors.{{N}} requires integer index; "
            f"got {change.field_path!r}",
            classification=CLS_UNKNOWN,
            context={"field_path": change.field_path},
        )

    if not any(f.floor_number == target_index for f in brief.floors):
        raise BriefChangeIntegrityError(
            f"floors.{target_index} not present in brief",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "target_index": target_index,
            },
        )

    new_floors = []
    for f in brief.floors:
        if f.floor_number == target_index:
            continue  # drop
        if f.floor_number > target_index:
            new_floors.append(
                dataclasses.replace(f, floor_number=f.floor_number - 1)
            )
        else:
            new_floors.append(f)
    return dataclasses.replace(brief, floors=tuple(new_floors))


def _handle_floors_add_stilt(brief: Brief, change: BriefChange) -> Brief:
    """floors.add_stilt SET True.

    Insert a STILT_PARKING floor at floor_number=0; renumber existing
    floors upward by 1. Idempotent if a stilt floor already exists.
    (Per S4 spec §4 row 5, §6.1, Q3.)
    """
    if change.new_value is not True:
        raise BriefChangeIntegrityError(
            f"floors.add_stilt SET only supports True; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )
    # Idempotent: if any floor already has STILT_PARKING use, no-op
    if any(f.floor_use == FloorUse.STILT_PARKING for f in brief.floors):
        return brief

    new_stilt = FloorRequirement(
        floor_number=0,
        floor_use=FloorUse.STILT_PARKING,
        rooms=(),
        notes="",
    )
    renumbered = tuple(
        dataclasses.replace(f, floor_number=f.floor_number + 1)
        for f in brief.floors
    )
    return dataclasses.replace(brief, floors=(new_stilt,) + renumbered)


def _handle_floors_count(brief: Brief, change: BriefChange) -> Brief:
    """floors.count INCREMENT delta (negative-only).

    Drop the topmost |delta| floors. Equivalent to repeated
    floors.{N} DELETE on the highest indices. (Per S4 spec §4 row 6,
    §6.4, §6.6.)
    """
    try:
        delta = int(change.new_value)
    except (TypeError, ValueError):
        raise BriefChangeIntegrityError(
            f"floors.count INCREMENT requires integer delta; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )

    if delta >= 0:
        # Spec §6.4: floors.count is negative-only (drop floors).
        raise BriefChangeIntegrityError(
            f"floors.count INCREMENT only supports negative delta; "
            f"got {delta}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": delta,
            },
        )

    drops_remaining = -delta
    floors = list(brief.floors)
    while drops_remaining > 0:
        if not floors:
            break
        # Find the floor with maximum floor_number (the topmost) and
        # drop it. No renumbering needed since we always remove the
        # top.
        topmost_index = max(
            range(len(floors)),
            key=lambda i: floors[i].floor_number,
        )
        floors.pop(topmost_index)
        drops_remaining -= 1
    return dataclasses.replace(brief, floors=tuple(floors))


# ─── setback handlers (one per side) ────────────────────────────────

def _setback_increment_handler(sb_field: str):
    """Factory: build a setback INCREMENT handler for one side."""
    def handler(brief: Brief, change: BriefChange) -> Brief:
        try:
            delta = float(change.new_value)
        except (TypeError, ValueError):
            raise BriefChangeIntegrityError(
                f"setbacks.{sb_field} INCREMENT requires numeric delta; "
                f"got {change.new_value!r}",
                classification=CLS_UNKNOWN,
                context={
                    "field_path": change.field_path,
                    "new_value": change.new_value,
                },
            )
        current = brief.user_stated_setbacks
        # B-014 (S54 fix): Compute the would-be value per side, catch
        # Setbacks.__post_init__ validation errors, and translate to a
        # SETBACK_INVALID-classified BriefChangeIntegrityError with the
        # side + resulting value in context. Pre-fix, the raw ValueError
        # bubbled out and the formatter fell back to UNKNOWN ("try a
        # different option"), giving the user no actionable signal.
        result_m = (
            (current.front_m if sb_field == "front_m" else current.front_m),
            (current.rear_m if sb_field == "rear_m" else current.rear_m),
            (current.side_left_m if sb_field == "side_left_m" else current.side_left_m),
            (current.side_right_m if sb_field == "side_right_m" else current.side_right_m),
        )
        # Apply the delta to the targeted side
        new_front = current.front_m + (delta if sb_field == "front_m" else 0)
        new_rear = current.rear_m + (delta if sb_field == "rear_m" else 0)
        new_left = current.side_left_m + (delta if sb_field == "side_left_m" else 0)
        new_right = current.side_right_m + (delta if sb_field == "side_right_m" else 0)
        target_result = {
            "front_m": new_front, "rear_m": new_rear,
            "side_left_m": new_left, "side_right_m": new_right,
        }[sb_field]
        try:
            new_setbacks = Setbacks(
                front_m=new_front, rear_m=new_rear,
                side_left_m=new_left, side_right_m=new_right,
            )
        except (ValueError, TypeError) as ve:
            raise BriefChangeIntegrityError(
                f"setbacks.{sb_field} would become {target_result:.2f}m, "
                f"which is outside the allowed 0–15m range "
                f"(detail: {ve})",
                classification=CLS_SETBACK_INVALID,
                context={
                    "field_path": change.field_path,
                    "side": sb_field,
                    "delta_m": delta,
                    "result_m": round(target_result, 2),
                    "current_m": round(getattr(current, sb_field), 2),
                },
            )
        return dataclasses.replace(brief, user_stated_setbacks=new_setbacks)
    handler.__name__ = f"_handle_setbacks_{sb_field}"
    return handler


_handle_setbacks_front = _setback_increment_handler("front_m")
_handle_setbacks_rear = _setback_increment_handler("rear_m")
_handle_setbacks_side_left = _setback_increment_handler("side_left_m")
_handle_setbacks_side_right = _setback_increment_handler("side_right_m")


# ─── budget ─────────────────────────────────────────────────────────

def _handle_budget_max_lakhs(brief: Brief, change: BriefChange) -> Brief:
    """budget.max_lakhs SET <int>.

    Replace brief.budget_range with BudgetRange(min=min(min, new),
    max=new). Keeping min ≤ max is automatic via min().
    (Per S4 spec §4 row 11.)
    """
    try:
        new_max = int(change.new_value)
    except (TypeError, ValueError):
        raise BriefChangeIntegrityError(
            f"budget.max_lakhs SET requires integer; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )
    current = brief.budget_range
    new_min = min(current.min_lakhs, new_max)
    new_budget = BudgetRange(
        min_lakhs=new_min,
        max_lakhs=new_max,
        currency=current.currency,
    )
    return dataclasses.replace(brief, budget_range=new_budget)


# ─── parking / coverage acceptance (interim audit-trail tags) ───────
# Per S4 spec §6.2 and Q10. The Brief schema as of S1 has no parking
# / coverage structured fields. These handlers append a tag string to
# brief.additional_requirements — backlog item B-011 tracks the
# eventual move to structured fields.

_PARKING_OPEN_TAG = "parking_open_accepted_by_user"


def _handle_parking_acceptance(brief: Brief, change: BriefChange) -> Brief:
    """parking.has_covered SET False — record acceptance tag."""
    if change.new_value is not False:
        raise BriefChangeIntegrityError(
            f"parking.has_covered SET only supports False; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )
    if _PARKING_OPEN_TAG in brief.additional_requirements:
        return brief  # idempotent
    return dataclasses.replace(
        brief,
        additional_requirements=(
            brief.additional_requirements + (_PARKING_OPEN_TAG,)
        ),
    )


def _handle_coverage_acceptance(brief: Brief, change: BriefChange) -> Brief:
    """coverage.reduce_footprint SET <pct> — record acceptance tag."""
    try:
        pct = float(change.new_value)
    except (TypeError, ValueError):
        raise BriefChangeIntegrityError(
            f"coverage.reduce_footprint SET requires numeric pct; "
            f"got {change.new_value!r}",
            classification=CLS_UNKNOWN,
            context={
                "field_path": change.field_path,
                "new_value": change.new_value,
            },
        )
    tag = f"coverage_reduced_to_{pct:.0f}_pct"
    if tag in brief.additional_requirements:
        return brief
    return dataclasses.replace(
        brief,
        additional_requirements=brief.additional_requirements + (tag,),
    )


# ─────────────────────────────────────────────────────────────────────
# Dispatch table (S4 spec §5.2, Q1)
# ─────────────────────────────────────────────────────────────────────

_DISPATCH_TABLE: dict[
    tuple[str, ...], Callable[[Brief, BriefChange], Brief]
] = {
    # Tuple-keyed; "*" matches any segment (wildcard fallback only)
    ("rooms", "*", "count"):           _handle_rooms_count,
    ("rooms", "all", "size"):          _handle_rooms_all_size,
    ("floors", "add"):                 _handle_floors_add,
    ("floors", "*"):                   _handle_floors_index_delete,
    ("floors", "add_stilt"):           _handle_floors_add_stilt,
    ("floors", "count"):               _handle_floors_count,
    ("setbacks", "front_m"):           _handle_setbacks_front,
    ("setbacks", "rear_m"):            _handle_setbacks_rear,
    ("setbacks", "side_left_m"):       _handle_setbacks_side_left,
    ("setbacks", "side_right_m"):      _handle_setbacks_side_right,
    ("budget", "max_lakhs"):           _handle_budget_max_lakhs,
    ("parking", "has_covered"):        _handle_parking_acceptance,
    ("coverage", "reduce_footprint"):  _handle_coverage_acceptance,
}


def _resolve_handler(
    field_path: str,
) -> Optional[Callable[[Brief, BriefChange], Brief]]:
    """Return the handler for a parsed field_path, or None.

    Tries exact tuple match first, then a single-position wildcard
    fallback (one segment replaced with "*"). Per Q1.
    """
    parts = tuple(field_path.split("."))
    if parts in _DISPATCH_TABLE:
        return _DISPATCH_TABLE[parts]
    for n in range(len(parts)):
        wildcard_key = parts[:n] + ("*",) + parts[n + 1:]
        if wildcard_key in _DISPATCH_TABLE:
            return _DISPATCH_TABLE[wildcard_key]
    return None


# ─────────────────────────────────────────────────────────────────────
# Classification — map ValueError messages to one of 6 known classes
# (S4 spec §7)
# ─────────────────────────────────────────────────────────────────────

def _is_drop_floor(change: BriefChange) -> bool:
    """True iff this change semantically reduces the floor count."""
    fp = change.field_path
    if fp.startswith("floors.") and change.operation == "DELETE":
        return True
    if fp == "floors.count" and change.operation == "INCREMENT":
        try:
            return int(change.new_value) < 0
        except (TypeError, ValueError):
            return False
    return False


def _room_type_str_from_path(field_path: str) -> Optional[str]:
    """Extract the RoomType string from a `rooms.{type}.count` path."""
    parts = field_path.split(".")
    if len(parts) >= 2 and parts[0] == "rooms":
        return parts[1]
    return None


def _is_bedroom_path(field_path: str) -> bool:
    rt = _room_type_str_from_path(field_path)
    if rt is None:
        return False
    try:
        return RoomType(rt) in _BEDROOM_TYPES
    except ValueError:
        return False


def _resulting_bedroom_count(brief: Brief, change: BriefChange) -> int:
    """Estimate post-apply bedroom count for a bedroom change.

    For a `rooms.{bedroom_type}.count INCREMENT delta` change, walk
    the brief and apply the delta hypothetically. Used for context
    fields when classification fires.
    """
    rt = _room_type_str_from_path(change.field_path)
    if rt is None:
        return 0
    try:
        target = RoomType(rt)
    except ValueError:
        return 0
    try:
        delta = int(change.new_value)
    except (TypeError, ValueError):
        delta = 0
    current = sum(
        r.count
        for f in brief.floors
        for r in f.rooms
        if r.room_type == target
    )
    return max(0, current + delta)


def _classify_error(
    err: Exception, brief: Brief, change: BriefChange,
) -> tuple[str, dict]:
    """Map a caught ValueError/TypeError to (classification, context).

    Substring-matches `Brief.__post_init__` / `RoomRequirement` /
    `BudgetRange` / `Setbacks` / `FloorRequirement` error wording.
    Backlog item B-013 tracks moving to typed exception classes for
    robustness.
    """
    msg = str(err).lower()

    # ─── ROOM_AREA_BELOW_NBC_MIN ──────────────────────────────────
    if "below nbc minimum" in msg:
        room_type_str = _room_type_str_from_path(change.field_path)
        nbc_min_sqm = 0.0
        requested = 0.0
        if room_type_str is not None:
            try:
                rt_enum = RoomType(room_type_str)
                nbc_min_sqm = float(
                    NBC_MINIMUM_ROOM_SIZES_SQM.get(rt_enum, 0.0)
                )
            except ValueError:
                pass
        # Try to extract the requested value from the new_value field
        try:
            requested = float(change.new_value)
        except (TypeError, ValueError):
            requested = 0.0
        return CLS_ROOM_AREA, {
            "room_type": room_type_str or "",
            "requested_size_sqm": requested,
            "nbc_min_sqm": nbc_min_sqm,
            "raw_message": str(err),
            "field_path": change.field_path,
        }

    # ─── BEDROOM_COUNT_BELOW_MIN ─────────────────────────────────
    # Trigger 1: room count cannot be negative AND it's a bedroom
    # Trigger 2: future-proofing — explicit bedroom-min check
    if (
        ("count cannot be negative" in msg
         and _is_bedroom_path(change.field_path))
        or "bedroom" in msg and "below" in msg and "minimum" in msg
    ):
        return CLS_BEDROOM, {
            "resulting_count": _resulting_bedroom_count(brief, change),
            "stated_min": _MIN_BEDROOMS,
            "room_type": (
                _room_type_str_from_path(change.field_path) or ""
            ),
            "raw_message": str(err),
            "field_path": change.field_path,
        }

    # ─── BUDGET_BELOW_THRESHOLD ──────────────────────────────────
    # Brief budget validation messages always start with the word
    # "budget" (lowered): "budget min_lakhs={X} is implausibly low",
    # "budget max_lakhs ({X}) < min_lakhs ({Y})".
    if "budget" in msg and (
        "implausibly low" in msg or "max_lakhs" in msg
        or "min_lakhs" in msg
    ):
        # We don't have a cost estimate at apply time. Use 0 as
        # placeholder; S6 / formatter caller can fold in c2 estimate
        # if it has one.
        try:
            new_max = int(change.new_value) if change.field_path == \
                "budget.max_lakhs" else brief.budget_range.max_lakhs
        except (TypeError, ValueError):
            new_max = brief.budget_range.max_lakhs
        delta_l = brief.budget_range.max_lakhs - new_max
        return CLS_BUDGET, {
            "delta_l": int(delta_l),
            "est_l": 0,  # placeholder; not known at apply time (B-012)
            "budget_l": int(new_max),
            "raw_message": str(err),
            "field_path": change.field_path,
        }

    # ─── FLOOR_COUNT_BELOW_MIN ───────────────────────────────────
    # Brief: "Brief requires at least one floor (ground floor)."
    # Also catch the "floor_number ... exceeds" case but only if the
    # change semantically reduces floors.
    if "at least one floor" in msg or (
        "floor_number" in msg and "exceeds" in msg
        and _is_drop_floor(change)
    ):
        return CLS_FLOOR_COUNT, {
            "resulting_count": 0,
            "stated_min": _MIN_FLOORS,
            "raw_message": str(err),
            "field_path": change.field_path,
        }

    # ─── UNKNOWN ─────────────────────────────────────────────────
    return CLS_UNKNOWN, {
        "raw_message": str(err),
        "field_path": change.field_path,
    }


# ─────────────────────────────────────────────────────────────────────
# Public API (S4 spec §3)
# ─────────────────────────────────────────────────────────────────────

def apply_brief_change(brief: Brief, change: BriefChange) -> Brief:
    """Apply a single BriefChange to a Brief and return a new validated Brief.

    Pure function — does not mutate `brief`.

    Per parent C3a spec § 3.3 integrity invariant:
        result MUST pass Brief.__post_init__ validation;
        if validation fails, raises BriefChangeIntegrityError with
        classification + context dict.

    Raises:
        BriefChangeIntegrityError — with classification (one of the 6
            per S1's BriefChangeIntegrityError.classify()) and a
            context dict (numeric/textual fields the formatter needs).
    """
    handler = _resolve_handler(change.field_path)
    if handler is None:
        raise BriefChangeIntegrityError(
            f"Unknown field_path: {change.field_path!r}",
            classification=CLS_UNKNOWN,
            context={"field_path": change.field_path},
        )
    try:
        return handler(brief, change)
    except BriefChangeIntegrityError:
        # Already classified by the handler — propagate untouched.
        raise
    except (ValueError, TypeError) as e:
        classification, context = _classify_error(e, brief, change)
        raise BriefChangeIntegrityError(
            f"BriefChange '{change.description}' produced invalid Brief: {e}",
            classification=classification,
            context=context,
        ) from e


def apply_brief_changes(
    brief: Brief, changes: tuple[BriefChange, ...],
) -> Brief:
    """Apply a tuple of BriefChanges sequentially.

    Each change is applied to the running Brief, so later changes
    see the results of earlier ones.

    Empty tuple is a valid no-op (returns the input Brief unchanged) —
    Preview Mode and several advisory options carry empty tuples.

    On the FIRST change that raises BriefChangeIntegrityError, the
    error is re-raised with .context["change_index"] set to the index
    in the tuple where it failed. Earlier successful applications are
    NOT rolled back into the input — the caller's input Brief remains
    untouched because every step is constructed via dataclasses.replace.

    Returns:
        A new validated Brief representing the cumulative effect.

    Raises:
        BriefChangeIntegrityError — re-raised with .context["change_index"]
            populated.
    """
    if not changes:
        return brief
    current = brief
    for index, change in enumerate(changes):
        try:
            current = apply_brief_change(current, change)
        except BriefChangeIntegrityError as e:
            e.context["change_index"] = index
            raise
    return current
