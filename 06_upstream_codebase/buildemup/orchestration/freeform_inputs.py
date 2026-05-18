"""Free-form Plot + FloorRoomBrief construction (S57 follow-up #11).

Until S59 the `/api/orchestrate` endpoint accepted only named-fixture
inputs (`plot_fixture: "bangalore_40x60"`). Production callers need a
free-form input contract — a JSON shape that maps to the domain Plot
and FloorRoomBrief dataclasses.

This module ships those builders. The JSON shape mirrors what
`/api/brief/capture` already accepts (so the brief-capture form's
output can be replayed into the orchestrator directly).

Validation strategy: every type/range error is raised as
`FreeformInputError` carrying a human-readable message. The endpoint
maps these to 400 responses. We deliberately do NOT echo the offending
value back if it could be huge — message-only.
"""
from __future__ import annotations

from typing import Any, Mapping

from buildemup.domain.envelope import PlotOrientation
from buildemup.domain.floor_brief import FloorRoomBrief
from buildemup.domain.plot import (
    Plot,
    PlotType,
    SharedSide,
    SoilType,
    SUPPORTED_CITIES,
)


class FreeformInputError(ValueError):
    """Raised for any malformed `plot` or `brief` JSON shape."""


# ─────────────────────────────────────────────────────────────────────
# Plot
# ─────────────────────────────────────────────────────────────────────

_FACING_ALIASES = {
    "N": PlotOrientation.NORTH, "NORTH": PlotOrientation.NORTH,
    "NE": PlotOrientation.NORTHEAST, "NORTHEAST": PlotOrientation.NORTHEAST,
    "E": PlotOrientation.EAST, "EAST": PlotOrientation.EAST,
    "SE": PlotOrientation.SOUTHEAST, "SOUTHEAST": PlotOrientation.SOUTHEAST,
    "S": PlotOrientation.SOUTH, "SOUTH": PlotOrientation.SOUTH,
    "SW": PlotOrientation.SOUTHWEST, "SOUTHWEST": PlotOrientation.SOUTHWEST,
    "W": PlotOrientation.WEST, "WEST": PlotOrientation.WEST,
    "NW": PlotOrientation.NORTHWEST, "NORTHWEST": PlotOrientation.NORTHWEST,
}


def build_plot_from_json(data: Mapping[str, Any]) -> Plot:
    """Build a Plot from a JSON-style dict.

    Required fields: width_m, depth_m, facing, city, road_width_m.
    Optional fields: plot_type, corner_plot, second_road_width_m,
    shared_side, soil_type_known.

    For convenience the endpoint also accepts plot dimensions in feet
    via `width_ft` / `depth_ft` / `road_width_ft` — these are converted
    to metres with the spec factor 0.3048.
    """
    if not isinstance(data, Mapping):
        raise FreeformInputError(
            f"plot must be an object; got {type(data).__name__}"
        )

    width_m = _coerce_metres(data, "width_m", "width_ft")
    depth_m = _coerce_metres(data, "depth_m", "depth_ft")
    road_width_m = _coerce_metres(data, "road_width_m", "road_width_ft")

    facing_raw = data.get("facing")
    if facing_raw is None:
        raise FreeformInputError("plot.facing is required")
    facing = _coerce_facing(facing_raw)

    city = data.get("city")
    if not isinstance(city, str) or not city.strip():
        raise FreeformInputError("plot.city is required (non-empty string)")
    city_normalized = city.strip().lower()
    if city_normalized not in SUPPORTED_CITIES:
        raise FreeformInputError(
            f"plot.city={city!r} not supported; "
            f"allowed: {sorted(SUPPORTED_CITIES)}"
        )

    plot_type = _coerce_enum(
        data.get("plot_type", "detached"), PlotType, "plot_type",
    )

    corner_plot = bool(data.get("corner_plot", False))
    second_road_width_m = data.get("second_road_width_m")
    if second_road_width_m is None and data.get("second_road_width_ft") is not None:
        second_road_width_m = float(data["second_road_width_ft"]) * 0.3048
    if corner_plot and second_road_width_m is None:
        raise FreeformInputError(
            "plot.second_road_width_m (or _ft) is required when corner_plot=true"
        )

    shared_side_raw = data.get("shared_side")
    shared_side = (
        _coerce_enum(shared_side_raw, SharedSide, "shared_side")
        if shared_side_raw is not None else None
    )

    soil_raw = data.get("soil_type_known")
    soil = (
        _coerce_enum(soil_raw, SoilType, "soil_type_known")
        if soil_raw is not None else None
    )

    try:
        return Plot(
            width_m=width_m,
            depth_m=depth_m,
            facing=facing,
            city=city_normalized,
            road_width_m=road_width_m,
            plot_type=plot_type,
            corner_plot=corner_plot,
            second_road_width_m=second_road_width_m,
            shared_side=shared_side,
            soil_type_known=soil,
        )
    except (TypeError, ValueError) as e:
        raise FreeformInputError(
            f"Plot rejected by domain validation: {e}"
        ) from e


def _coerce_metres(
    data: Mapping[str, Any], key_m: str, key_ft: str,
) -> float:
    """Pull a metre value; fall back to feet × 0.3048."""
    if key_m in data and data[key_m] is not None:
        try:
            return float(data[key_m])
        except (TypeError, ValueError) as e:
            raise FreeformInputError(
                f"plot.{key_m} must be numeric; got {data[key_m]!r}"
            ) from e
    if key_ft in data and data[key_ft] is not None:
        try:
            return float(data[key_ft]) * 0.3048
        except (TypeError, ValueError) as e:
            raise FreeformInputError(
                f"plot.{key_ft} must be numeric; got {data[key_ft]!r}"
            ) from e
    raise FreeformInputError(
        f"plot.{key_m} (or .{key_ft}) is required"
    )


def _coerce_facing(raw: Any) -> PlotOrientation:
    if isinstance(raw, PlotOrientation):
        return raw
    if not isinstance(raw, str):
        raise FreeformInputError(
            f"plot.facing must be a string; got {type(raw).__name__}"
        )
    key = raw.strip().upper()
    if key not in _FACING_ALIASES:
        raise FreeformInputError(
            f"plot.facing={raw!r} not recognized; "
            f"allowed: {sorted(set(o.value for o in PlotOrientation))}"
        )
    return _FACING_ALIASES[key]


def _coerce_enum(raw: Any, enum_cls, field_name: str):
    """Coerce a string to the named enum; accept enum value or enum name."""
    if isinstance(raw, enum_cls):
        return raw
    if not isinstance(raw, str):
        raise FreeformInputError(
            f"plot.{field_name} must be a string; got {type(raw).__name__}"
        )
    key = raw.strip().lower()
    for member in enum_cls:
        if member.value.lower() == key or member.name.lower() == key:
            return member
    allowed = sorted(m.value for m in enum_cls)
    raise FreeformInputError(
        f"plot.{field_name}={raw!r} not recognized; allowed: {allowed}"
    )


# ─────────────────────────────────────────────────────────────────────
# FloorRoomBrief
# ─────────────────────────────────────────────────────────────────────


def build_floor_brief_from_json(data: Mapping[str, Any]) -> FloorRoomBrief:
    """Build a FloorRoomBrief from a JSON-style dict.

    Required: bedroom_count, bathroom_count.
    Optional booleans: has_kitchen, has_living, has_pooja, has_utility,
    has_master_bedroom. Optional collection: other_rooms (list of str).
    Optional string: floor_label.
    """
    if not isinstance(data, Mapping):
        raise FreeformInputError(
            f"brief must be an object; got {type(data).__name__}"
        )

    def _int(name: str, *, default: int | None = None) -> int:
        raw = data.get(name, default)
        if raw is None:
            raise FreeformInputError(f"brief.{name} is required")
        try:
            value = int(raw)
        except (TypeError, ValueError) as e:
            raise FreeformInputError(
                f"brief.{name} must be int; got {raw!r}"
            ) from e
        if value < 0:
            raise FreeformInputError(
                f"brief.{name} must be ≥ 0; got {value}"
            )
        return value

    def _bool(name: str, default: bool) -> bool:
        if name in data:
            return bool(data[name])
        return default

    other_rooms_raw = data.get("other_rooms", ())
    if isinstance(other_rooms_raw, str):
        raise FreeformInputError(
            "brief.other_rooms must be a list of strings, not a string"
        )
    try:
        other_rooms = tuple(str(r) for r in other_rooms_raw)
    except TypeError as e:
        raise FreeformInputError(
            f"brief.other_rooms must be iterable of strings; got "
            f"{type(other_rooms_raw).__name__}"
        ) from e

    floor_label = str(data.get("floor_label", "ground"))

    try:
        return FloorRoomBrief(
            bedroom_count=_int("bedroom_count"),
            bathroom_count=_int("bathroom_count"),
            has_kitchen=_bool("has_kitchen", True),
            has_living=_bool("has_living", True),
            has_pooja=_bool("has_pooja", False),
            has_utility=_bool("has_utility", False),
            other_rooms=other_rooms,
            floor_label=floor_label,
            has_master_bedroom=_bool("has_master_bedroom", True),
        )
    except (TypeError, ValueError) as e:
        raise FreeformInputError(
            f"FloorRoomBrief rejected by domain validation: {e}"
        ) from e


# ─────────────────────────────────────────────────────────────────────
# Brief-for-C4 wrapper
# ─────────────────────────────────────────────────────────────────────


def make_brief_for_c4(plot: Plot, *, trace_id: str = "trace-orch-free-001"):
    """Wrap a Plot into the minimal ResolvedBrief-shape C4 consumes.

    Mirrors `tests/validation/_c4_fixtures.make_brief` so we share the
    contract without depending on test fixtures in production code.
    """
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _RevisedStub:
        plot: Plot
        trace_id: str

    @dataclass(frozen=True)
    class _BriefStub:
        revised_brief: _RevisedStub

    return _BriefStub(revised_brief=_RevisedStub(plot=plot, trace_id=trace_id))


__all__ = [
    "FreeformInputError",
    "build_plot_from_json",
    "build_floor_brief_from_json",
    "make_brief_for_c4",
]
