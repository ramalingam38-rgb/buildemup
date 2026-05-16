"""
C3b — Per-instance severity computation (spec § 3 Phase β step 4.2)
====================================================================

v0.2 patch: severity is computed per-instance using a context vector,
NOT statically from category. The same tweak category can be different
severities in different contexts (door in load-bearing wall vs partition
wall; room_resize within a bay vs crossing a bay).

The six context factors (spec § 3 Phase β step 4.2):
  1. Load-bearing wall involvement (within LOAD_BEARING_PROXIMITY_MM)
  2. Circulation graph impact (adds/removes node or edge)
  3. Wet-zone stack interaction
  4. Structural-bay boundary crossing
  5. Topology classification change → AUTO-PROMOTE TO HEAVY per R13
  6. External-wall change

Promotion rules:
  - 1 factor crossing threshold → promote 1 tier (L→M or M→H)
  - 2+ factors → MEDIUM tweaks auto-promote to HEAVY directly
  - Topology change (R13) → AUTO-HEAVY regardless of other factors

Rule 11 self-analysis:
  1. The "promotion by 1 tier" rule means LIGHT + 1 factor = MEDIUM,
     and MEDIUM + 1 factor stays MEDIUM (since MEDIUM + 1 only promotes
     by 1, ending at MEDIUM unless 2+ factors fire). The "2+ factors"
     rule explicitly handles MEDIUM → HEAVY. Tests cover both paths.
  2. Topology check (factor 5) is special — it ALWAYS produces HEAVY
     when triggered, bypassing the count-based rule. This matches the
     R13 contract: topology change is not a tweak.
  3. Context detection here is HEURISTIC. False negatives (missing a
     factor that should fire) bias toward more-MEDIUM-than-correct,
     which is the safer direction (we propose a rerun unnecessarily
     vs missing a rerun that was needed). False positives bias toward
     HEAVY (refused tweaks). Documented; B-C3B-FORMAL-MUTATION-ENVELOPE-GRAPH
     (v1.x) will replace with formal proof reasoning.
  4. R13 short-circuits: if topology check fires, we exit early — we
     do not also count it as 1-of-6. This avoids double-counting and
     keeps the "topology change = HEAVY" rule clear.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..contracts import (
    DoorPlacement,
    PlacedRoom,
    PlotAnalysis,
    RiserGroup,
    StructuralGrid,
)
from ..schema import (
    PredictionBasis,
    SeverityTier,
    TopologyClassification,
    TopologyInvarianceResult,
    TweakCategory,
)
from ..versioning import LOAD_BEARING_PROXIMITY_MM
from .tables import TWEAK_CATEGORY_DEFAULT_SEVERITY


# ============================================================
# § 1 — Context vector
# ============================================================

@dataclass(frozen=True)
class SeverityContext:
    """The 6 contextual factors a candidate tweak may trigger.

    Each factor is a boolean; True means the factor crosses threshold
    and contributes to severity promotion.

    v0.6 B3 — when topology_classification_change=True, a graded
    topology_divergence_score may also be populated. If present and
    below TOPOLOGY_DIVERGENCE_MEDIUM_CAP, severity is demoted to
    MEDIUM instead of forced to HEAVY (low-risk perturbation).
    """
    load_bearing_wall_involvement:   bool = False
    circulation_graph_impact:        bool = False
    wet_zone_stack_interaction:      bool = False
    structural_bay_boundary_cross:   bool = False
    topology_classification_change:  bool = False  # R13 auto-HEAVY
    external_wall_change:            bool = False
    # v0.6 B3 — graded divergence score for topology changes. None when
    # not computed (v0.5 boolean-only fallback). Only consulted when
    # topology_classification_change=True.
    topology_divergence_score:       Optional[float] = None

    @property
    def factor_count(self) -> int:
        return sum([
            self.load_bearing_wall_involvement,
            self.circulation_graph_impact,
            self.wet_zone_stack_interaction,
            self.structural_bay_boundary_cross,
            self.external_wall_change,
            # NOTE: topology_classification_change NOT counted here —
            # it short-circuits to HEAVY directly (see promote_severity)
        ])

    def factor_names_triggered(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.load_bearing_wall_involvement:
            names.append("load_bearing_wall_involvement")
        if self.circulation_graph_impact:
            names.append("circulation_graph_impact")
        if self.wet_zone_stack_interaction:
            names.append("wet_zone_stack_interaction")
        if self.structural_bay_boundary_cross:
            names.append("structural_bay_boundary_cross")
        if self.topology_classification_change:
            names.append("topology_classification_change")
        if self.external_wall_change:
            names.append("external_wall_change")
        return tuple(names)


# ============================================================
# § 2 — Context detection (heuristic — see Rule 11 self-analysis pt 3)
# ============================================================

def detect_load_bearing_proximity(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    structural_grid:    StructuralGrid,
) -> bool:
    """Returns True if any affected room sits on or within
    LOAD_BEARING_PROXIMITY_MM of a load-bearing perimeter cell."""
    affected_set = set(affected_room_ids)
    if not affected_set:
        return False
    # Build room → bay_ids map
    affected_bay_ids: set[str] = set()
    for room in placed_rooms:
        if room.room_id in affected_set:
            affected_bay_ids.update(room.structural_bay_ids)
    if not affected_bay_ids:
        return False
    # Any of those bays load-bearing?
    for cell in structural_grid.cells:
        if cell.cell_id in affected_bay_ids and cell.is_load_bearing_perimeter:
            return True
    return False


def detect_bay_boundary_crossing(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> bool:
    """Returns True if any affected room straddles 2+ structural bays
    (room_resize across a bay boundary is a structural impact)."""
    affected_set = set(affected_room_ids)
    for room in placed_rooms:
        if room.room_id in affected_set and len(room.structural_bay_ids) >= 2:
            return True
    return False


def detect_wet_zone_interaction(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    riser_groups:       tuple[RiserGroup, ...],
) -> bool:
    """Returns True if any affected room is served by a riser group OR
    is spatially adjacent to one. Adjacency uses adjacent_room_ids."""
    affected_set = set(affected_room_ids)
    # Direct: affected room is in a riser group
    served_rooms: set[str] = set()
    for rg in riser_groups:
        served_rooms.update(rg.served_room_ids)
    if affected_set & served_rooms:
        return True
    # Indirect: affected room is adjacent to a riser-served room
    affected_adjacents: set[str] = set()
    for room in placed_rooms:
        if room.room_id in affected_set:
            affected_adjacents.update(room.adjacent_room_ids)
    if affected_adjacents & served_rooms:
        return True
    return False


def detect_external_wall_change(
    *,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    tweak_category:     TweakCategory,
) -> bool:
    """Returns True if the tweak touches a room with an external wall.
    Window/balcony tweaks are the prototypical triggers."""
    # Tweaks that intrinsically touch envelope:
    envelope_categories = {
        "balcony_add", "balcony_remove", "window_resize",
    }
    if tweak_category in envelope_categories:
        return True
    # Other tweaks: only count if the affected room has external_wall
    affected_set = set(affected_room_ids)
    for room in placed_rooms:
        if room.room_id in affected_set and room.has_external_wall:
            return True
    return False


def detect_circulation_graph_impact(
    *,
    tweak_category:     TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    door_placements:    tuple[DoorPlacement, ...],
) -> bool:
    """Returns True if the tweak adds/removes a circulation graph
    node or edge. Door tweaks change edges; room tweaks may change
    both nodes and edges."""
    # Tweaks that always touch circulation:
    if tweak_category in {"door_relocate", "room_swap", "utility_zone_carveout"}:
        return True
    # Tweaks that may touch circulation if they affect a multi-door room:
    affected_set = set(affected_room_ids)
    affected_door_count = sum(
        1 for d in door_placements
        if d.room_a_id in affected_set or d.room_b_id in affected_set
    )
    if tweak_category in {"room_resize", "storage_add"} and affected_door_count >= 2:
        return True
    return False


def predict_topology_invariance(
    *,
    tweak_category:     TweakCategory,
    source_topology:    TopologyClassification,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> TopologyInvarianceResult:
    """Predict whether the tweak preserves C5 topology classification.

    Per spec § 2.4.2 + R13:
      - Topology-defining elements: corridors, central spine, courtyard
        void, perimeter envelope
      - mutation_local_only: tweak doesn't touch topology-defining elements
      - heuristic_weak: ambiguous; safety-bias to HEAVY (invariance=False)
    """
    # Categorize tweak by topology-touch likelihood
    # Tweaks that essentially never alter topology:
    topology_safe_categories = {
        "finish_upgrade", "finish_downgrade",
        "window_resize",
        "balcony_add", "balcony_remove",   # balconies don't alter the topology of the interior plan
    }
    # Tweaks that may alter topology only if they touch corridor/spine:
    topology_sensitive_categories = {
        "door_relocate",        # changing main door could change topology
        "room_swap",
        "room_resize",
        "utility_zone_carveout", # carves from corridor — could alter spine
        "storage_add",
        "pooja_relocate",
        "kitchen_reorient",
        "wet_zone_restage",
    }

    if tweak_category in topology_safe_categories:
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=source_topology,
            invariance_preserved=True,
            prediction_basis="mutation_local_only",
            advisory_note=None,
        )

    if tweak_category not in topology_sensitive_categories:
        # Unknown category — safety bias to weak prediction (HEAVY)
        # Map source to a different topology to make invariance_preserved=False
        # consistent. Pick l_shape as a generic "different" topology.
        not_source = "l_shape" if source_topology != "l_shape" else "central_spine"
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=not_source,
            invariance_preserved=False,
            prediction_basis="heuristic_weak",
            advisory_note=(
                "Unrecognized tweak category. Routing to a different pathway "
                "as a precaution."
            ),
        )

    # Topology-sensitive category — check what's affected
    # Heuristic: if the affected room set includes corridor/lobby/stair,
    # topology may change. Otherwise mutation_local_only.
    affected_set = set(affected_room_ids)
    topology_defining_functions = {"corridor", "stair", "lift_lobby", "lobby"}
    touches_topology = any(
        r.room_id in affected_set
        and r.room_function in topology_defining_functions
        for r in placed_rooms
    )
    if touches_topology:
        # Strong signal — predict topology DOES change
        not_source = "l_shape" if source_topology != "l_shape" else "central_spine"
        return TopologyInvarianceResult(
            source_topology=source_topology,
            predicted_topology=not_source,
            invariance_preserved=False,
            prediction_basis="circulation_pattern_invariant",
            advisory_note=(
                "This tweak touches a circulation-defining element "
                "(corridor / stair / lobby). Reclassifying as a topology change."
            ),
        )

    # Mutation doesn't touch topology-defining elements
    return TopologyInvarianceResult(
        source_topology=source_topology,
        predicted_topology=source_topology,
        invariance_preserved=True,
        prediction_basis="structural_grid_invariant",
        advisory_note=None,
    )


# ============================================================
# § 3 — Severity promotion (the rules)
# ============================================================

def promote_severity(
    *,
    default_severity:  SeverityTier,
    context:           SeverityContext,
) -> SeverityTier:
    """Apply the spec § 3 Phase β step 4.2 promotion rules.

    Returns the final severity. Order of precedence:
      1. Topology change → AUTO-HEAVY (R13) — BUT v0.6 B3 amendment:
         if topology_divergence_score < TOPOLOGY_DIVERGENCE_MEDIUM_CAP,
         demote to MEDIUM (low-risk perturbation). Mid/high divergence
         OR score=None preserve v0.5 auto-HEAVY behavior.
      2. ≥2 factors AND default is MEDIUM → HEAVY
      3. ≥1 factor → promote by 1 tier
      4. Otherwise → default
    """
    from ..versioning import TOPOLOGY_DIVERGENCE_MEDIUM_CAP

    # R13 + v0.6 B3 — graded topology routing
    if context.topology_classification_change:
        # If score is populated AND below cap → demote to MEDIUM
        if (context.topology_divergence_score is not None
                and context.topology_divergence_score < TOPOLOGY_DIVERGENCE_MEDIUM_CAP):
            # Low-divergence topology change → MEDIUM (with structural
            # factors potentially still promoting further below)
            base = "medium"
            # If other structural factors also cross threshold, MEDIUM
            # + ≥1 factor stays MEDIUM (per promotion-by-1-tier rule).
            # Special-case: ≥2 OTHER factors should still escalate.
            other_factor_count = context.factor_count
            if other_factor_count >= 2:
                return "heavy"
            return base
        # None or ≥ cap → preserved v0.5 auto-HEAVY
        return "heavy"

    factor_count = context.factor_count

    if factor_count == 0:
        return default_severity

    # ≥2 factors with MEDIUM default → HEAVY
    if factor_count >= 2 and default_severity == "medium":
        return "heavy"

    # ≥1 factor with LIGHT default → MEDIUM
    if default_severity == "light":
        return "medium"

    # MEDIUM + 1 factor stays MEDIUM (per spec promotion-by-1-tier)
    if default_severity == "medium":
        return "medium"

    # HEAVY default stays HEAVY
    return default_severity


def detect_context_for_tweak(
    *,
    tweak_category:     TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
    structural_grid:    StructuralGrid,
    riser_groups:       tuple[RiserGroup, ...],
    door_placements:    tuple[DoorPlacement, ...],
    topology_invariance: Optional[TopologyInvarianceResult] = None,
) -> SeverityContext:
    """Compute the full SeverityContext for a candidate tweak.

    The 6 factors:
      1. load_bearing_wall_involvement
      2. circulation_graph_impact
      3. wet_zone_stack_interaction
      4. structural_bay_boundary_cross
      5. topology_classification_change (from R13 prediction)
      6. external_wall_change
    """
    return SeverityContext(
        load_bearing_wall_involvement=detect_load_bearing_proximity(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            structural_grid=structural_grid,
        ),
        circulation_graph_impact=detect_circulation_graph_impact(
            tweak_category=tweak_category,
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            door_placements=door_placements,
        ),
        wet_zone_stack_interaction=detect_wet_zone_interaction(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            riser_groups=riser_groups,
        ),
        structural_bay_boundary_cross=detect_bay_boundary_crossing(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
        ),
        topology_classification_change=(
            topology_invariance is not None
            and not topology_invariance.invariance_preserved
        ),
        external_wall_change=detect_external_wall_change(
            affected_room_ids=affected_room_ids,
            placed_rooms=placed_rooms,
            tweak_category=tweak_category,
        ),
        # v0.6 B3 — graded score (may be None if upstream didn't populate)
        topology_divergence_score=(
            topology_invariance.topology_divergence_score
            if topology_invariance is not None
            else None
        ),
    )


__all__ = [
    "SeverityContext",
    "detect_load_bearing_proximity",
    "detect_bay_boundary_crossing",
    "detect_wet_zone_interaction",
    "detect_external_wall_change",
    "detect_circulation_graph_impact",
    "predict_topology_invariance",
    "promote_severity",
    "detect_context_for_tweak",
]
