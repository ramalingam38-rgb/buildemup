"""
C16 Phase γ — Working drawing assembly
=========================================

Per v0.5 LOCKED spec § 3 Phase γ.

INPUT:
    - EnvelopeAssembly (Phase α)
    - SchedulingResult (Phase β)
    - RenderingConfig

PROCESSING:
    1. Build WorkingDrawingFloor per FloorGeometry:
       - geometry_ref = FloorGeometry.identity.semantic_identity_hash
       - working annotations: dimension lines, room labels, finish callouts
       - per-floor door/window/finish schedules from Phase β
    2. Generate SectionView per RenderingConfig.mandatory_section_cuts
       (R23):
       - "entry"     — cut through main entrance, perpendicular to entry wall
       - "staircase" — cut through staircase (multi-floor only, else skipped)
       - "wet_zone"  — cut through highest-stack-count plumbing column
       - Fallback (v0.2 A8): offset to stay inside building, snapped to
         structural grid; lex-ASC tiebreak per R7c.
    3. Build RoofPlan (top floor only) from upper FloorGeometry bbox.

OUTPUT:
    WorkingDrawingModel.

R-INVARIANTS:
    R7c — canonical sort of annotations + schedules
    R8  — schedules carry upstream identities (passthrough)
    R23 — section cut set matches config.mandatory_section_cuts
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from buildemup.components.c16.config import RenderingConfig
from buildemup.components.c16.errors import GeometryInconsistencyError
from buildemup.components.c16.schema import (
    ElementIdentity,
    FloorGeometry,
    RoofPlan,
    SectionView,
    WorkingAnnotation,
    WorkingDrawingFloor,
    WorkingDrawingModel,
    compute_element_identity,
)
from buildemup.components.c16.contracts import ElementKind
from buildemup.components.c16.phases.alpha_envelope import EnvelopeAssembly
from buildemup.components.c16.phases.beta_scheduling import SchedulingResult


def _emit_annotations_for_floor(fg: FloorGeometry) -> tuple[WorkingAnnotation, ...]:
    """Per-room labels + dimension callouts. Deterministic ordering."""
    out: list[WorkingAnnotation] = []
    counter = 0
    for r in fg.rooms:
        counter += 1
        out.append(WorkingAnnotation(
            annotation_id=f"label:{r.room_id}",
            text=f"{r.room_id} ({r.category})",
            anchor_x_mm=r.x_mm + r.width_mm // 2,
            anchor_y_mm=r.y_mm + r.depth_mm // 2,
            annotation_kind="room_label",
        ))
        counter += 1
        out.append(WorkingAnnotation(
            annotation_id=f"dim:{r.room_id}:w",
            text=f"{r.width_mm} mm",
            anchor_x_mm=r.x_mm + r.width_mm // 2,
            anchor_y_mm=r.y_mm,
            annotation_kind="dimension",
        ))
        counter += 1
        out.append(WorkingAnnotation(
            annotation_id=f"dim:{r.room_id}:d",
            text=f"{r.depth_mm} mm",
            anchor_x_mm=r.x_mm,
            anchor_y_mm=r.y_mm + r.depth_mm // 2,
            annotation_kind="dimension",
        ))
    return tuple(sorted(out, key=lambda a: a.annotation_id))


def _compute_section_view(
    *,
    cut_type:         Literal["entry", "staircase", "wet_zone"],
    floor_geometries: tuple[FloorGeometry, ...],
) -> SectionView | None:
    """R23 section cut generation.

    Returns None if the cut isn't applicable (e.g. staircase cut on a
    single-floor building).

    R7c determinism: when multiple anchors are valid, lex-ASC tiebreak
    on semantic_identity_hash.
    """
    if not floor_geometries:
        return None

    # Floors traversed = all floors that have any geometry
    floors_traversed = tuple(fg.floor_level for fg in floor_geometries)
    is_multifloor = len(floor_geometries) > 1

    section_id = f"section:{cut_type}"
    cut_position_mm = 0
    axis: Literal["vertical", "horizontal"] = "horizontal"

    if cut_type == "entry":
        # Find main-entry door on ground floor (level 0).
        ground = floor_geometries[0]
        entry_doors = tuple(d for d in ground.doors if d.is_main_entry)
        if not entry_doors:
            # No main entry on ground floor — degenerate. R23 allows
            # fallback to lex-ASC first door.
            if not ground.doors:
                return None
            chosen = min(
                ground.doors, key=lambda d: d.identity.semantic_identity_hash,
            )
        else:
            chosen = min(
                entry_doors,
                key=lambda d: d.identity.semantic_identity_hash,
            )
        # Cut perpendicular to the door wall:
        # horizontal door (wall is horizontal) → vertical cut through door
        if chosen.axis == "horizontal":
            axis = "vertical"
            cut_position_mm = chosen.anchor_x_mm
        else:
            axis = "horizontal"
            cut_position_mm = chosen.anchor_y_mm

    elif cut_type == "staircase":
        if not is_multifloor:
            return None
        # We don't carry an explicit staircase in this build; use the
        # geometric midpoint of the top floor (where the staircase
        # typically sits in residential layouts). Documented as
        # B-C16-STAIRCASE-CUT-FROM-C7-STAIRCASE (LOCK-mandatory).
        top = floor_geometries[-1]
        if not top.rooms:
            return None
        midroom = min(top.rooms, key=lambda r: r.identity.semantic_identity_hash)
        axis = "horizontal"
        cut_position_mm = midroom.y_mm + midroom.depth_mm // 2

    elif cut_type == "wet_zone":
        # Highest-stack-count plumbing column across floors
        all_stacks = []
        for fg in floor_geometries:
            for s in fg.plumbing_stacks:
                all_stacks.append((s, fg.floor_level))
        if not all_stacks:
            return None
        # Group by (x_mm, y_mm) — same column across floors
        from collections import Counter
        positions = Counter((s.x_mm, s.y_mm) for s, _ in all_stacks)
        # Highest count, lex-ASC tiebreak
        (best_x, best_y), _ = max(
            positions.items(),
            key=lambda kv: (kv[1], -kv[0][0], -kv[0][1]),
        )
        # Cut horizontally through that column
        axis = "horizontal"
        cut_position_mm = best_y

    else:
        return None

    # R23 v0.2 A8 fallback: if cut_position falls outside the building
    # bbox along its perpendicular axis, offset it inward to the
    # nearest valid coord and record offset_mm. This prevents section
    # views that don't actually cross the building.
    offset_mm = 0
    if floor_geometries and floor_geometries[0].rooms:
        ground = floor_geometries[0]
        min_x = min(r.x_mm for r in ground.rooms)
        max_x = max(r.x_mm + r.width_mm for r in ground.rooms)
        min_y = min(r.y_mm for r in ground.rooms)
        max_y = max(r.y_mm + r.depth_mm for r in ground.rooms)
        margin = 50  # 50 mm inward snap
        if axis == "vertical":
            target = max(min_x + margin, min(cut_position_mm, max_x - margin))
            offset_mm = abs(target - cut_position_mm)
            cut_position_mm = target
        else:
            target = max(min_y + margin, min(cut_position_mm, max_y - margin))
            offset_mm = abs(target - cut_position_mm)
            cut_position_mm = target

    geometry_payload = {
        "cut_type":         cut_type,
        "axis":             axis,
        "cut_position_mm":  cut_position_mm,
        "floors_traversed": list(floors_traversed),
    }
    full_payload = {**geometry_payload, "section_id": section_id}
    identity = compute_element_identity(
        element_kind=ElementKind.SLAB_FLOOR,  # closest match in taxonomy
        floor_level=0,
        geometry_defining_payload=geometry_payload,
        full_payload=full_payload,
    )
    return SectionView(
        identity=identity,
        section_id=section_id,
        cut_type=cut_type,
        floors_traversed=floors_traversed,
        axis=axis,
        cut_position_mm=cut_position_mm,
        offset_mm=offset_mm,
    )


def _build_roof_plan(
    floor_geometries: tuple[FloorGeometry, ...],
) -> RoofPlan | None:
    """RoofPlan based on top-floor bbox."""
    if not floor_geometries:
        return None
    top = floor_geometries[-1]
    if not top.rooms:
        return None
    min_x = min(r.x_mm for r in top.rooms)
    min_y = min(r.y_mm for r in top.rooms)
    max_x = max(r.x_mm + r.width_mm for r in top.rooms)
    max_y = max(r.y_mm + r.depth_mm for r in top.rooms)
    geometry_payload = {
        "outline_x_mm":       min_x,
        "outline_y_mm":       min_y,
        "outline_width_mm":   max_x - min_x,
        "outline_depth_mm":   max_y - min_y,
    }
    full_payload = {**geometry_payload, "drainage_slope_pct": 1.0}
    identity = compute_element_identity(
        element_kind=ElementKind.SLAB_ROOF,
        floor_level=top.floor_level + 1,
        geometry_defining_payload=geometry_payload,
        full_payload=full_payload,
    )
    return RoofPlan(
        identity=identity,
        outline_x_mm=min_x,
        outline_y_mm=min_y,
        outline_width_mm=max_x - min_x,
        outline_depth_mm=max_y - min_y,
        drainage_slope_pct=1.0,
    )


def execute_phase_gamma(
    *,
    envelope:    EnvelopeAssembly,
    scheduling:  SchedulingResult,
    config:      RenderingConfig,
) -> WorkingDrawingModel:
    """Phase γ main entry point."""
    # Build WorkingDrawingFloor per FloorGeometry
    schedules_by_level = {fs.floor_level: fs for fs in scheduling.per_floor}
    floor_plans: list[WorkingDrawingFloor] = []
    for fg in envelope.floor_geometries:
        schedules = schedules_by_level.get(fg.floor_level)
        if schedules is None:
            raise GeometryInconsistencyError(
                f"Phase γ: floor_level {fg.floor_level} has no Phase β "
                f"schedules — phase ordering bug.",
                invariant_id="R20",
                offending_ids=(str(fg.floor_level),),
            )
        floor_plans.append(WorkingDrawingFloor(
            geometry_ref=fg.geometry_ref,
            annotations=_emit_annotations_for_floor(fg),
            door_schedule=schedules.door_schedule,
            window_schedule=schedules.window_schedule,
            finish_schedule=schedules.finish_schedule,
        ))

    # R23 — generate mandatory section cuts in canonical enum order
    section_views: list[SectionView] = []
    for cut_type in ("entry", "staircase", "wet_zone"):
        if cut_type not in config.mandatory_section_cuts:
            continue
        sv = _compute_section_view(
            cut_type=cut_type,
            floor_geometries=envelope.floor_geometries,
        )
        if sv is not None:
            section_views.append(sv)

    # Aggregate all schedules across floors (for the WorkingDrawingModel
    # top-level — used by drafting software that wants a flat schedule).
    all_doors:  list = []
    all_wins:   list = []
    all_finish: list = []
    for fs in scheduling.per_floor:
        all_doors.extend(fs.door_schedule)
        all_wins.extend(fs.window_schedule)
        all_finish.extend(fs.finish_schedule)

    return WorkingDrawingModel(
        floor_plans=tuple(floor_plans),
        section_views=tuple(section_views),
        roof_plan=_build_roof_plan(envelope.floor_geometries),
        door_schedule=tuple(all_doors),
        window_schedule=tuple(all_wins),
        finish_schedule=tuple(all_finish),
        recommended_scale=config.working_drawing_scale,
    )
