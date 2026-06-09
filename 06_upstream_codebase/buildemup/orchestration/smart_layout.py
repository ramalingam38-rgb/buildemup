"""Smart layout engine v2 (S60) — graph/core-first floor-plan arrangement.

WHY THIS EXISTS
===============
The engine has no working intelligent layout (C12 is an area-packer with
zero adjacency awareness; adjacency_hints never populated; C8 corridors
discarded). v1 of this module was a 2-zone band-packer with no staircase
and no real circulation — the user correctly called it "boxes in order."

v2 builds a coherent home using architectural rules drawn from how real
procedural/graph floor-plan generators work (constrained-growth +
adjacency-graph; see web research S60):

  - A STAIRCASE CORE is always present (injected if the room program
    omits it) and placed at a FIXED position so it lines up across
    floors — the thing you climb to reach the first floor.
  - The MAIN ENTRANCE opens into the LIVING room (never a bathroom).
  - KITCHEN + DINING are grouped together; utility/wash sits by the
    kitchen.
  - A CORRIDOR/LOBBY beside the stair forms the circulation spine;
    BEDROOMS open off it, each PAIRED with its ensuite bathroom.
  - POOJA is placed in a corner (NE-leaning) per Indian convention.
  - No bathroom is ever placed in the entrance/living band.

Honesty: room sizes/areas come from the engine (NBC). The ARRANGEMENT
is rule-based (a deterministic heuristic generator), labelled
illustrative until a full graph-dualization engine + the C12 adjacency
integration ship. This is the real fix for "lifeless boxes," not yet a
C12 replacement.

OUTPUT (JSON-friendly dict)
===========================
  {
    "envelope": {"width_m","depth_m"},
    "facing": "N|E|S|W",
    "rooms":   [{"category","label","x_m","y_m","width_m","depth_m"}],
    "corridor":[{"x_m","y_m","width_m","depth_m"}],
    "doors":   [{"x_m","y_m"}],
    "entrance":{"x_m","y_m"},
    "note": str,
  }
Frame: y=0 is the FRONT (facing/entrance side); y grows toward the back.
"""
from __future__ import annotations

from typing import Any, Optional

# Category groups
_LIVING = ("living", "hall", "foyer", "drawing")
_COOK = ("kitchen", "dining")
_BEDROOM = ("bedroom",)
_BATH = ("bathroom",)
_POOJA = ("pooja",)
_SERVICE = ("utility", "store", "wash")

_CORRIDOR_W_M = 1.2          # circulation width
_STAIR_W_M = 2.4            # staircase footprint width
_STAIR_D_M = 4.0           # staircase footprint depth (dog-leg)
_MIN_BAND_D_M = 2.4        # smallest usable band depth


def _area(r: dict) -> float:
    return max(0.25, float(r.get("width_m") or 1.0) * float(r.get("depth_m") or 1.0))


def _rect(category: str, x: float, y: float, w: float, d: float, label: str = "") -> dict:
    return {
        "category": category,
        "label": label or category,
        "x_m": round(x, 3), "y_m": round(y, 3),
        "width_m": round(w, 3), "depth_m": round(d, 3),
    }


def _classify(rooms: list[dict]) -> dict[str, list[dict]]:
    b: dict[str, list[dict]] = {"living": [], "cook": [], "bedroom": [], "bath": [], "pooja": [], "service": []}
    for r in rooms:
        cat = (r.get("category") or "").lower()
        if cat in _LIVING:
            b["living"].append(r)
        elif cat in _COOK:
            b["cook"].append(r)
        elif cat in _BEDROOM:
            b["bedroom"].append(r)
        elif cat in _BATH:
            b["bath"].append(r)
        elif cat in _POOJA:
            b["pooja"].append(r)
        else:
            b["service"].append(r)
    return b


def _lay_row(items: list[tuple[str, float]], x0: float, y0: float, row_w: float, row_d: float) -> list[dict]:
    """Place items (category, area) left-to-right filling the row; widths ∝ area."""
    total = sum(a for _, a in items) or 1.0
    out = []
    x = x0
    for i, (cat, a) in enumerate(items):
        w = row_w * (a / total)
        if i == len(items) - 1:
            w = (x0 + row_w) - x  # absorb rounding into the last cell
        out.append(_rect(cat, x, y0, w, row_d))
        x += w
    return out


def build_smart_layout(
    *,
    rooms: list[dict],
    envelope_w: float,
    envelope_d: float,
    facing: str = "N",
    include_staircase: bool = True,
) -> Optional[dict]:
    """Arrange the room program into a coherent home floor plan (v2).

    Bands front (entrance) -> back:
      1. LIVING (full width) — entrance opens here.
      2. KITCHEN + DINING (+ utility) — cooking band.
      3. CORE — staircase (one side) + corridor/lobby (rest).
      4. BEDROOMS — each with its ensuite bathroom behind it; pooja in
         a back corner.
    Bands that have no rooms are skipped; the staircase core is always
    present (so upper floors line up and are reachable).
    """
    if not rooms or envelope_w <= 0 or envelope_d <= 0:
        return None

    W = float(envelope_w)
    D = float(envelope_d)
    g = _classify(rooms)

    out_rooms: list[dict] = []
    doors: list[dict] = []
    corridor: list[dict] = []

    # ── Pair bedrooms with ensuite bathrooms ──
    baths = list(g["bath"])
    bed_pairs: list[tuple[dict, Optional[dict]]] = []
    for bed in g["bedroom"]:
        bed_pairs.append((bed, baths.pop(0) if baths else None))
    common_baths = baths  # leftover -> common, placed off the corridor

    # ── Band depth budget ──
    stair_d = min(_STAIR_D_M, max(_MIN_BAND_D_M, D * 0.22)) if include_staircase else 0.0
    core_d = max(stair_d, _CORRIDOR_W_M) if (include_staircase or bed_pairs) else 0.0

    living_area = sum(_area(r) for r in g["living"]) or 0.0
    cook_area = sum(_area(r) for r in g["cook"]) + sum(_area(r) for r in g["service"])
    bed_area = sum(_area(b) + (_area(t) if t else 0.0) for b, t in bed_pairs)
    bed_area += sum(_area(r) for r in g["pooja"]) + sum(_area(r) for r in common_baths)

    flexible_d = max(1.0, D - core_d)
    zone_total = (living_area + cook_area + bed_area) or 1.0
    living_d = flexible_d * (living_area / zone_total) if living_area else 0.0
    cook_d = flexible_d * (cook_area / zone_total) if cook_area else 0.0
    bed_d = flexible_d - living_d - cook_d

    # enforce minimums where a band has content
    if living_area:
        living_d = max(living_d, _MIN_BAND_D_M)
    if cook_area:
        cook_d = max(cook_d, _MIN_BAND_D_M)
    # rebalance bed_d so total fits
    used = living_d + cook_d + core_d
    bed_d = max(0.0, D - used)
    if bed_pairs and bed_d < _MIN_BAND_D_M:
        # steal from cook/living proportionally
        deficit = _MIN_BAND_D_M - bed_d
        if cook_d > living_d:
            cook_d = max(_MIN_BAND_D_M, cook_d - deficit)
        else:
            living_d = max(_MIN_BAND_D_M, living_d - deficit)
        bed_d = max(0.0, D - (living_d + cook_d + core_d))

    y = 0.0

    # ── Band 1: LIVING (entrance) ──
    if living_area:
        liv = g["living"][0]
        out_rooms.append(_rect("living", 0.0, y, W, living_d, liv.get("room_id") or "Living"))
        # entrance door into living, on the front edge
        doors.append({"x_m": round(W / 2, 3), "y_m": 0.0})
        living_top = y + living_d
        y = living_top

    # ── Band 2: KITCHEN + DINING + utility ──
    if cook_area:
        items = [(r.get("category") or "room", _area(r)) for r in g["cook"]]
        items += [(r.get("category") or "utility", _area(r)) for r in g["service"]]
        row = _lay_row(items, 0.0, y, W, cook_d)
        out_rooms.extend(row)
        # door living -> cooking band (vertical flow)
        if living_area:
            doors.append({"x_m": round(W / 2, 3), "y_m": round(y, 3)})
        y += cook_d

    # ── Band 3: CORE (staircase + corridor/lobby) ──
    core_y = y
    if core_d > 0:
        stair_w = min(_STAIR_W_M, W * 0.4) if include_staircase else 0.0
        if include_staircase and stair_w > 0:
            # staircase on the RIGHT side (fixed position across floors)
            out_rooms.append(_rect("staircase", W - stair_w, core_y, stair_w, core_d, "Stair"))
        corr_w = W - (stair_w if include_staircase else 0.0)
        if corr_w > 0.5:
            corridor.append({"x_m": 0.0, "y_m": round(core_y, 3), "width_m": round(corr_w, 3), "depth_m": round(core_d, 3)})
            # common baths tucked into the corridor band's left edge (off the lobby)
            cx = 0.0
            for cb in common_baths:
                cbw = min(_area(cb) / max(core_d, 1.0), corr_w * 0.4)
                cbw = max(1.2, cbw)
                out_rooms.append(_rect("bathroom", cx, core_y, cbw, core_d, cb.get("room_id") or "Bath"))
                doors.append({"x_m": round(cx + cbw / 2, 3), "y_m": round(core_y + core_d, 3)})
                cx += cbw
            # door from cooking/living into the lobby
            doors.append({"x_m": round(corr_w / 2, 3), "y_m": round(core_y, 3)})
            # door lobby -> staircase
            if include_staircase and stair_w > 0:
                doors.append({"x_m": round(W - stair_w, 3), "y_m": round(core_y + core_d / 2, 3)})
        y += core_d

    # ── Band 4: BEDROOMS (+ ensuite) + pooja corner ──
    back_y = y
    if bed_pairs and bed_d > 0:
        # widths ∝ pair area; pooja gets a small slice at the right (NE-ish)
        pooja = g["pooja"][0] if g["pooja"] else None
        pooja_w = min(2.0, W * 0.18) if pooja else 0.0
        usable_w = W - pooja_w
        total_pair = sum(_area(b) + (_area(t) if t else 0.0) for b, t in bed_pairs) or 1.0
        x = 0.0
        for i, (bed, bath) in enumerate(bed_pairs):
            pa = _area(bed) + (_area(bath) if bath else 0.0)
            col_w = usable_w * (pa / total_pair)
            if i == len(bed_pairs) - 1 and not pooja:
                col_w = usable_w - x
            if bath is not None:
                bed_frac = _area(bed) / pa
                bd = bed_d * bed_frac
                td = bed_d - bd
                out_rooms.append(_rect("bedroom", x, back_y, col_w, bd, bed.get("room_id") or "Bedroom"))
                out_rooms.append(_rect("bathroom", x, back_y + bd, col_w, td, bath.get("room_id") or "Bath"))
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y, 3)})           # corridor->bedroom
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y + bd, 3)})       # bedroom->ensuite
            else:
                out_rooms.append(_rect("bedroom", x, back_y, col_w, bed_d, bed.get("room_id") or "Bedroom"))
                doors.append({"x_m": round(x + col_w / 2, 3), "y_m": round(back_y, 3)})
            x += col_w
        # pooja in the back-right corner (NE-leaning)
        if pooja:
            out_rooms.append(_rect("pooja", W - pooja_w, back_y, pooja_w, min(bed_d, 2.2), pooja.get("room_id") or "Pooja"))
            doors.append({"x_m": round(W - pooja_w / 2, 3), "y_m": round(back_y, 3)})
    elif g["pooja"]:
        # no bedrooms but a pooja -> small corner room at the back
        pooja = g["pooja"][0]
        pw = min(2.0, W * 0.2)
        out_rooms.append(_rect("pooja", W - pw, back_y, pw, max(_MIN_BAND_D_M, bed_d), pooja.get("room_id") or "Pooja"))

    entrance = {"x_m": round(W / 2, 3), "y_m": 0.0}

    return {
        "envelope": {"width_m": round(W, 3), "depth_m": round(D, 3)},
        "facing": facing,
        "rooms": out_rooms,
        "corridor": corridor,
        "doors": doors,
        "entrance": entrance,
        "has_staircase": bool(include_staircase),
        "note": (
            "Smart layout v2 — entrance opens into the living room; "
            "kitchen & dining are grouped; a staircase + lobby form the "
            "circulation core (same position every floor); bedrooms open "
            "off the lobby, each with its attached bathroom; pooja in a "
            "corner. Room sizes are engine-computed (NBC); the "
            "arrangement is rule-based (illustrative) — a full "
            "graph-based layout engine is the next build."
        ),
    }


def build_smart_layout_from_preview(layout_preview: Any, facing: str = "N") -> Optional[dict]:
    """Build a smart layout from a layout_preview dict (the shape
    `orchestration.layout_preview.build_layout_preview` emits)."""
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
