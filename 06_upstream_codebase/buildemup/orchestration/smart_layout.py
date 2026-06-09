"""Smart layout engine (S60) — adjacency-aware floor-plan arrangement.

THE PROBLEM THIS SOLVES
=======================
The engine's C12 placement (slicing k-d tree) sizes rooms correctly but
arranges them with **zero adjacency awareness** — bedrooms and their
bathrooms land on opposite sides, rooms leave big gaps, and C8's
computed corridors are discarded before placement. The visual result is
"disconnected boxes," not a house. (Documented as B-C12-EDGE-DENSITY;
the adjacency-hint plumbing was never completed — see S57 follow-up #4.)

WHAT THIS MODULE DOES
=====================
Takes the engine's room PROGRAM (categories + NBC sizes from C9/C12) and
arranges it into a coherent, house-like floor plan using explicit
architectural rules:

  - Public zone (living / dining / kitchen / pooja / hall) along the
    FRONT (entrance/facing side).
  - Private zone (bedrooms) along the BACK.
  - Each bedroom is PAIRED with a bathroom placed directly beside it
    (the attached-bath adjacency the user asked for). Leftover bathrooms
    + utility/store go to a service strip.
  - A CORRIDOR spine runs between the public and private zones; every
    room opens onto it (doors), and the main ENTRANCE sits on the
    facing side.
  - Rooms are scaled to tile the buildable area so the plan reads full,
    with shared walls.

This is a heuristic generator (not a constraint solver). It is honest:
room sizes/areas come from the engine; the ARRANGEMENT is rule-based and
clearly labelled illustrative until the C12 adjacency integration ships.

OUTPUT
======
`build_smart_layout(...)` returns a JSON-friendly dict:
  {
    "envelope": {"width_m", "depth_m"},
    "facing": "N|E|S|W",
    "rooms":   [{"category","label","x_m","y_m","width_m","depth_m"}],
    "corridor":[{"x_m","y_m","width_m","depth_m"}],
    "doors":   [{"x_m","y_m"}],          # door centres (room <-> corridor)
    "entrance":{"x_m","y_m"},            # main entry on the facing side
    "note": str,
  }
Coordinates use a frame where y=0 is the FRONT (facing side) and y grows
toward the back; the frontend flips as needed.
"""
from __future__ import annotations

from typing import Any, Optional

_PUBLIC = ("living", "dining", "kitchen", "pooja", "hall", "foyer", "entrance")
_PRIVATE = ("bedroom",)
_BATH = ("bathroom",)
_SERVICE = ("utility", "store", "staircase", "balcony")

_CORRIDOR_W_M = 1.1  # NBC-ish corridor width


def _area(r: dict) -> float:
    return max(0.25, float(r.get("width_m") or 1.0) * float(r.get("depth_m") or 1.0))


def _classify(rooms: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {"public": [], "bedroom": [], "bath": [], "service": []}
    for r in rooms:
        cat = (r.get("category") or "").lower()
        if cat in _PRIVATE:
            buckets["bedroom"].append(r)
        elif cat in _BATH:
            buckets["bath"].append(r)
        elif cat in _PUBLIC:
            buckets["public"].append(r)
        else:
            buckets["service"].append(r)
    return buckets


def build_smart_layout(
    *,
    rooms: list[dict],
    envelope_w: float,
    envelope_d: float,
    facing: str = "N",
) -> Optional[dict]:
    """Arrange the room program into a coherent floor plan.

    Args:
        rooms: list of {category, width_m, depth_m, room_id?} (engine sizes).
        envelope_w / envelope_d: buildable envelope in metres.
        facing: cardinal direction the front faces (display only).
    Returns:
        Layout dict (see module docstring), or None if no rooms.
    """
    if not rooms or envelope_w <= 0 or envelope_d <= 0:
        return None

    W = float(envelope_w)
    D = float(envelope_d)
    buckets = _classify(rooms)

    # ── Pair each bedroom with a bathroom (attached) ──
    baths = list(buckets["bath"])
    bedroom_pairs: list[tuple[dict, Optional[dict]]] = []
    for bed in buckets["bedroom"]:
        bath = baths.pop(0) if baths else None
        bedroom_pairs.append((bed, bath))
    # Leftover baths + service rooms form a service group placed with public.
    service_rooms = list(buckets["service"]) + baths

    public_rooms = list(buckets["public"]) + service_rooms

    # ── Zone depth split (front public vs back private), proportional to area ──
    pub_area = sum(_area(r) for r in public_rooms) or 1.0
    priv_area = sum(_area(b) + (_area(t) if t else 0.0) for b, t in bedroom_pairs) or 1.0

    has_public = len(public_rooms) > 0
    has_private = len(bedroom_pairs) > 0

    usable_d = max(1.0, D - (_CORRIDOR_W_M if (has_public and has_private) else 0.0))
    if has_public and has_private:
        front_d = usable_d * (pub_area / (pub_area + priv_area))
        # keep each zone at least 2m deep so rooms are usable
        front_d = min(max(front_d, 2.0), usable_d - 2.0)
        back_d = usable_d - front_d
        corridor_y = front_d
        back_y = front_d + _CORRIDOR_W_M
    elif has_public:
        front_d, back_d, corridor_y, back_y = usable_d, 0.0, None, None
    else:
        front_d, back_d, corridor_y, back_y = 0.0, usable_d, None, 0.0

    out_rooms: list[dict] = []
    doors: list[dict] = []

    # ── Front zone: public rooms left-to-right, widths ∝ area ──
    if has_public:
        _lay_row(public_rooms, x0=0.0, y0=0.0, row_w=W, row_d=front_d,
                 out_rooms=out_rooms, doors=doors,
                 door_edge="bottom" if has_private else None,
                 corridor_y=corridor_y)

    # ── Back zone: bedroom+bath columns left-to-right, widths ∝ pair area ──
    if has_private:
        total_pair_area = sum(_area(b) + (_area(t) if t else 0.0) for b, t in bedroom_pairs) or 1.0
        x = 0.0
        for bed, bath in bedroom_pairs:
            pair_area = _area(bed) + (_area(bath) if bath else 0.0)
            col_w = W * (pair_area / total_pair_area)
            if bath is not None:
                # Bedroom occupies the upper portion of the column; its
                # bathroom sits directly below it (attached) — adjacency.
                bed_frac = _area(bed) / pair_area
                bed_d = back_d * bed_frac
                bath_d = back_d - bed_d
                out_rooms.append(_rect("bedroom", bed, x, back_y, col_w, bed_d))
                out_rooms.append(_rect("bathroom", bath, x, back_y + bed_d, col_w, bath_d))
                # door: bedroom -> corridor (top edge of bedroom)
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y, 3)})
                # door: bedroom -> its bathroom (shared internal edge)
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y + bed_d, 3)})
            else:
                out_rooms.append(_rect("bedroom", bed, x, back_y, col_w, back_d))
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y, 3)})
            x += col_w

    # ── Corridor spine ──
    corridor: list[dict] = []
    if has_public and has_private:
        corridor.append({
            "x_m": 0.0, "y_m": round(corridor_y, 3),
            "width_m": round(W, 3), "depth_m": round(_CORRIDOR_W_M, 3),
        })

    # ── Entrance on the facing side (front, y=0) ──
    entrance = {"x_m": round(W / 2, 3), "y_m": 0.0}

    return {
        "envelope": {"width_m": round(W, 3), "depth_m": round(D, 3)},
        "facing": facing,
        "rooms": out_rooms,
        "corridor": corridor,
        "doors": doors,
        "entrance": entrance,
        "note": (
            "Smart layout — room sizes are engine-computed (NBC); the "
            "arrangement groups public rooms at the entrance, pairs each "
            "bedroom with its bathroom, and connects everything via a "
            "corridor. Rule-based arrangement (illustrative) until the "
            "C12 adjacency engine ships."
        ),
    }


def _lay_row(
    room_list: list[dict], *, x0: float, y0: float, row_w: float, row_d: float,
    out_rooms: list[dict], doors: list[dict],
    door_edge: Optional[str], corridor_y: Optional[float],
) -> None:
    """Lay rooms left-to-right filling [x0, x0+row_w] × [y0, y0+row_d],
    widths proportional to area."""
    total = sum(_area(r) for r in room_list) or 1.0
    x = x0
    for r in room_list:
        w = row_w * (_area(r) / total)
        out_rooms.append(_rect(r.get("category") or "room", r, x, y0, w, row_d))
        if door_edge == "bottom":
            doors.append({"x_m": round(x + w / 2, 3), "y_m": round(y0 + row_d, 3)})
        x += w


def _rect(category: str, src: dict, x: float, y: float, w: float, d: float) -> dict:
    return {
        "category": category,
        "label": src.get("room_id") or category,
        "x_m": round(x, 3),
        "y_m": round(y, 3),
        "width_m": round(w, 3),
        "depth_m": round(d, 3),
        # carry the engine's true NBC size for the legend / honesty
        "engine_width_m": round(float(src.get("width_m") or 0.0), 3),
        "engine_depth_m": round(float(src.get("depth_m") or 0.0), 3),
    }


def build_smart_layout_from_preview(layout_preview: Any, facing: str = "N") -> Optional[dict]:
    """Convenience wrapper: build a smart layout from a layout_preview dict
    (the shape `orchestration.layout_preview.build_layout_preview` emits)."""
    if not layout_preview:
        return None
    env = layout_preview.get("envelope") or {}
    rooms = layout_preview.get("rooms") or []
    w = env.get("width_m")
    d = env.get("depth_m")
    if not w or not d or not rooms:
        return None
    return build_smart_layout(rooms=rooms, envelope_w=w, envelope_d=d, facing=facing)


__all__ = ["build_smart_layout", "build_smart_layout_from_preview"]
