"""
C3b — Phase β — Tweak generation per layout (v0.2 PATCHED)
=============================================================

Spec § 3 Phase β (v0.2 PATCHED — per-instance severity computation):

  INPUT: 3 layouts, 3 ProblemReports, PlotAnalysis
  PROCESSING (per layout):
    1. Read ProblemReport. Find checks with severity ∈ {critical, important}
       AND status == 'fail' that have a known tweak pattern.
    2. Read structural grid. Find under-utilized cells → utility_zone_carveout
       candidates.
    3. Read orientation (PlotAnalysis). Find function/orientation mismatches
       → kitchen_reorient / pooja_relocate candidates.
    4. Apply severity filter (PER-INSTANCE — v0.2 patched):
       4.1 Default severity from category
       4.2 Context-aware adjustment (6 factors)
       4.3 Final severity assignment
       4.4 Bounded selection (max 6 per layout)
    5. Generate plain-English description per Principle 1 + Principle 3
       (advisory tone, R2 banned-phrase lint)

  OUTPUT: 3 TweakOptionSets

This module is the heart of C3b. The static tables in `tables.py` and
the severity logic in `severity.py` drive it.

Rule 11 self-analysis:
  1. HEAVY tweaks are NOT included in TweakOptionSet.tweaks. Instead
     they're buffered as MutationEnvelopes attached to the session for
     later use (per spec § 3 Phase β step 4 final assignment).
  2. STRICT mode raises on per-tweak errors; WARN mode collects. The
     `errors_collected` return value lists per-tweak errors that fired
     in WARN mode.
  3. Bounded selection prioritizes by (a) addresses critical problem,
     (b) LIGHT severity, (c) recommendation_flag='suggested'. Documented.
  4. Tweak description generation uses a TEMPLATE library — every
     category has a deterministic template, parameterized by affected
     room IDs / categories. Template strings are pre-linted to ensure
     they don't contain banned phrases. Tests verify.
  5. `presented_count` always starts at 0 from Phase β; bumped only
     in Phase ε when a tweak is re-surfaced.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from buildemup.components.c15.schema import (
    CheckSeverity,
    CheckStatus,
    ProblemCheck,
    ProblemReport,
)
from buildemup.utils.confidence import Confidence
from buildemup.utils.transparency import DerivationLine, TransparencyTriple

from ..config import C3bRuntimeConfig
from ..contracts import (
    AttestedValue,
    AuthorityKind,
    C3bInputBundle,
    DoorPlacement,
    PlacedRoom,
    RiserGroup,
    StructuralGrid,
)
from ..errors import (
    ConstraintViolationError,
    PerTweakError,
    TweakGenerationError,
)
from ..schema import (
    ApplySpecification,
    ComfortImpact,
    CompatibilityAssertion,
    FinishSchedulePayload,
    GeometryLocalPayload,
    LayoutArchetype,
    MutationEnvelope,
    KickBackPayload,
    MutationClassification,
    RecommendationFlag,
    SeverityTier,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyClassification,
    TopologyInvarianceResult,
    TweakCategory,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)
from ..versioning import MAX_TWEAKS_PER_LAYOUT
from .severity import (
    SeverityContext,
    detect_context_for_tweak,
    predict_topology_invariance,
    promote_severity,
)
from .tables import (
    TWEAK_CATEGORY_COMFORT_PROFILE,
    TWEAK_CATEGORY_COMPONENTS_TO_RERUN,
    TWEAK_CATEGORY_COST_RANGE_INR,
    TWEAK_CATEGORY_DEFAULT_SEVERITY,
    TWEAK_CATEGORY_IMPACT_TABLE,
    TWEAK_CATEGORY_SPACE_DELTA_SQFT,
    lex_asc_components,
    lex_asc_impacts,
    lookup_tweak_categories_for_check,
)


# ============================================================
# § 1 — Tweak description templates (R2 advisory-tone enforced)
# ============================================================
# Per Principle 1 + Principle 3: advisory tone, talks to user not engine.
# Each template is pre-linted (see test_phase_beta.py).

_DESCRIPTION_TEMPLATES: dict[TweakCategory, str] = {
    "finish_upgrade": (
        "You could upgrade the finishes in {rooms} — typically vitrified "
        "tiles or premium flooring. This is a finish-only change with "
        "no structural impact."
    ),
    "finish_downgrade": (
        "You could reduce the finish grade in {rooms} to a more economical "
        "option. This is a finish-only change with no structural impact."
    ),
    "door_relocate": (
        "You could move a door in {rooms} to a different wall, improving "
        "circulation or addressing a clearance concern."
    ),
    "window_resize": (
        "You could resize a window in {rooms} for more natural light "
        "or cross-ventilation."
    ),
    "balcony_add": (
        "You could add a balcony to {rooms} — typically carved from the "
        "interior. This adds outdoor connection and improves ventilation."
    ),
    "balcony_remove": (
        "You could remove the balcony from {rooms} and reclaim the "
        "interior space."
    ),
    "storage_add": (
        "You could add storage (closet or built-in) to {rooms}. This carves "
        "a small amount of room area for storage capacity."
    ),
    "pooja_relocate": (
        "You could relocate the pooja room in {rooms}, typically toward "
        "the east. This aligns with traditional Vastu (opt-in) and gives "
        "morning light."
    ),
    "kitchen_reorient": (
        "You could reorient the kitchen in {rooms} toward the east. This "
        "improves morning light and cross-ventilation in Chennai's warm-"
        "humid climate."
    ),
    "wet_zone_restage": (
        "You could re-stage the wet zones (bath/kitchen) in {rooms} to "
        "align their vertical stacks. This reduces plumbing runs and "
        "long-term leak risk."
    ),
    "utility_zone_carveout": (
        "You could carve a utility zone from underutilized corridor or "
        "lobby space in {rooms}. This adds laundry or storage capacity."
    ),
    "room_swap": (
        "You could swap two rooms' functions in {rooms}. Same geometry, "
        "different functional layout — often improves privacy or flow."
    ),
    "room_resize": (
        "You could resize a room in {rooms}, redistributing area from "
        "or to neighboring spaces. Stays within the existing structural grid."
    ),
}


def _format_room_list(room_ids: tuple[str, ...]) -> str:
    """Friendly join: ('room_001', 'room_002') → 'room_001 and room_002'."""
    if not room_ids:
        return "the layout"
    if len(room_ids) == 1:
        return room_ids[0]
    if len(room_ids) == 2:
        return f"{room_ids[0]} and {room_ids[1]}"
    return f"{', '.join(room_ids[:-1])}, and {room_ids[-1]}"


def render_description(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
) -> str:
    """Render the user-facing description for a tweak category +
    affected rooms. Pre-linted templates."""
    template = _DESCRIPTION_TEMPLATES.get(category)
    if template is None:
        # Fallback that still passes lint
        return (
            f"This is a {category} tweak affecting "
            f"{_format_room_list(affected_room_ids)}."
        )
    return template.format(rooms=_format_room_list(affected_room_ids))


# ============================================================
# § 2 — Heuristic impact builders (Phase γ logic factored here)
# ============================================================

def _build_cost_impact(category: TweakCategory) -> TransparencyTriple:
    low, mid, high, uncertainty = TWEAK_CATEGORY_COST_RANGE_INR.get(
        category, (0.0, 0.0, 0.0, 50.0),
    )
    return TransparencyTriple(
        label=f"Cost impact for {category}",
        exact_value=mid,
        unit="INR",
        uncertainty_pct=uncertainty,
        confidence=Confidence.MEDIUM,
        derivation=[
            DerivationLine(
                label=f"{category} heuristic range",
                amount=mid,
                source="C3b v0.4 TWEAK_CATEGORY_COST_RANGE_INR (Chennai 2026 heuristic)",
            ),
            DerivationLine(
                label=f"Lower bound (-{uncertainty}%)", amount=low,
            ),
            DerivationLine(
                label=f"Upper bound (+{uncertainty}%)", amount=high,
            ),
        ],
        notes=[],
    )


def _build_space_impact(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
    placed_rooms:       tuple[PlacedRoom, ...],
) -> SpaceImpact:
    delta = TWEAK_CATEGORY_SPACE_DELTA_SQFT.get(category, 0.0)
    # Distribute the delta evenly over affected rooms for the per-room view
    per_room: list[tuple[str, float]] = []
    if affected_room_ids:
        share = delta / len(affected_room_ids)
        per_room = [(rid, share) for rid in sorted(affected_room_ids)]

    # Total carpet area after — sum of placed rooms + delta
    base_carpet = sum(r.geometry.area_sqft for r in placed_rooms)
    return SpaceImpact(
        per_room_sqft_delta=tuple(per_room),
        total_sqft_delta=delta,
        total_carpet_area_after=AttestedValue(
            value=base_carpet + delta,
            authority=AuthorityKind.LOCALLY_DERIVED,
            upstream_source=None,
            derivation_note=f"C3b Phase β heuristic for {category}",
        ),
        advisory_note=(
            "Net-zero internal redistribution." if delta == 0.0
            else f"Net area change of {delta:+.0f} sqft."
        ),
    )


def _build_comfort_impact(category: TweakCategory) -> ComfortImpact:
    dims, direction, magnitude = TWEAK_CATEGORY_COMFORT_PROFILE.get(
        category, (("accessibility",), "mixed", "small"),
    )
    # v0.5 A7 — seed emotional heuristics per category. Three coarse
    # 0.0–1.0 scores. Categories that don't meaningfully affect a
    # dimension leave it None. Full architect-reviewed corpus is v1.x;
    # these seed values are deterministic-by-category for R6 replay.
    spaciousness, arrival, gathering = _emotional_heuristic_for_category(category)
    return ComfortImpact(
        dimensions_affected=tuple(sorted(dims)),
        direction=direction,
        magnitude=magnitude,
        advisory_note=f"Typical {magnitude} {direction} for this tweak category.",
        perceived_spaciousness=spaciousness,
        arrival_impression=arrival,
        family_gathering_comfort=gathering,
    )


# v0.5 A7 — emotional heuristic seeds. Map TweakCategory →
# (perceived_spaciousness, arrival_impression, family_gathering_comfort).
# Each Optional[float] in [0.0, 1.0]. None means "not meaningfully
# affected by this category." Full corpus is v1.x backlog.
_EMOTIONAL_HEURISTIC_SEEDS: dict[TweakCategory, tuple] = {
    # finishes — small spaciousness lift (visual lightness)
    "finish_upgrade":         (0.55, 0.60, None),
    "finish_downgrade":       (0.45, 0.40, None),
    # door / window — limited emotional reach
    "door_relocate":          (None, 0.55, None),
    "window_resize":          (0.60, None, None),
    # balcony — strong arrival/spaciousness lift when added
    "balcony_add":            (0.70, 0.70, 0.55),
    "balcony_remove":         (0.40, 0.40, None),
    # storage — neutral on emotion
    "storage_add":            (None, None, None),
    "utility_zone_carveout":  (None, None, None),
    # room moves — strong gathering effect
    "room_swap":              (0.55, 0.55, 0.65),
    "room_resize":            (0.60, 0.50, 0.60),
    # ritual / cultural rooms — arrival impression
    "pooja_relocate":         (None, 0.65, 0.55),
    "kitchen_reorient":       (0.55, None, 0.65),
    "wet_zone_restage":       (None, None, None),
}


def _emotional_heuristic_for_category(category: TweakCategory) -> tuple:
    """Return (perceived_spaciousness, arrival_impression, family_gathering_comfort)
    triple. Each may be None."""
    return _EMOTIONAL_HEURISTIC_SEEDS.get(category, (None, None, None))


# ============================================================
# § 3 — ApplySpecification builders (light vs medium)
# ============================================================

def _build_apply_spec_light(
    category:           TweakCategory,
    affected_room_ids:  tuple[str, ...],
) -> ApplySpecification:
    """LIGHT tweak — apply geometry-local or finish-schedule directly."""
    if category in ("finish_upgrade", "finish_downgrade"):
        grade = "premium_vitrified_800x800" if category == "finish_upgrade" else "standard_ceramic"
        overrides = tuple(sorted([
            (rid, "flooring", grade) for rid in affected_room_ids
        ], key=lambda t: (t[0], t[1])))
        if not overrides:
            # Fallback to a generic finish override
            overrides = (("default_room", "flooring", grade),)
        return ApplySpecification(
            mutation_kind="finish_schedule_only",
            geometry_local_payload=None,
            subset_rerun_payload=None,
            finish_schedule_payload=FinishSchedulePayload(
                room_finish_overrides=overrides,
                advisory_note=f"{category} applied to {len(overrides)} room(s).",
            ),
        )
    # Other LIGHT default categories → geometry_local
    return ApplySpecification(
        mutation_kind="geometry_local",
        geometry_local_payload=GeometryLocalPayload(
            new_room_function_assignments=(),
            new_door_placements_replace=(),
            new_window_assignments=(),
            advisory_note=f"{category} applied in-place.",
        ),
        subset_rerun_payload=None,
        finish_schedule_payload=None,
    )


def _build_apply_spec_medium(
    *,
    tweak_id:               str,
    category:               TweakCategory,
    topology_invariance:    TopologyInvarianceResult,
    compatibility_assertions: tuple[CompatibilityAssertion, ...],
) -> ApplySpecification:
    """MEDIUM tweak — emit SubsetRerunRequest."""
    components = TWEAK_CATEGORY_COMPONENTS_TO_RERUN.get(category, ())
    impacts = TWEAK_CATEGORY_IMPACT_TABLE.get(category, ())
    if not components or not impacts:
        # Shouldn't happen for known MEDIUM categories — defensive
        raise TweakGenerationError(
            f"No rerun mapping for category {category!r}",
            tweak_id=tweak_id,
            tweak_category_attempted=category,
        )
    return ApplySpecification(
        mutation_kind="subset_rerun",
        geometry_local_payload=None,
        finish_schedule_payload=None,
        subset_rerun_payload=SubsetRerunRequest(
            trigger_tweak_id=tweak_id,
            trigger_tweak_category=category,
            components_to_rerun=lex_asc_components(components),
            downstream_impact_set=lex_asc_impacts(impacts),
            topology_invariance_check=topology_invariance,
            expected_completion_seconds=2.5,
            rerun_anchor=f"{category}_anchor",
            compatibility_assertions=compatibility_assertions,
        ),
    )


# ============================================================
# § 4 — Recommendation flag classification
# ============================================================

def classify_recommendation_flag(
    *,
    problem_checks_addressed: tuple[ProblemCheck, ...],
) -> RecommendationFlag:
    """Per R5: STRUCTURAL marker, not authoritative ranking.

    Classification:
      - "suggested"     — at least one critical or important check addressed
      - "optional"      — only nice_to_have checks addressed
      - "alternative"   — no checks addressed (stylistic / preference tweak)
    """
    if not problem_checks_addressed:
        return "alternative"
    severities = [c.severity for c in problem_checks_addressed]
    if any(s == CheckSeverity.CRITICAL for s in severities):
        return "suggested"
    if any(s == CheckSeverity.IMPORTANT for s in severities):
        return "suggested"
    return "optional"


# ============================================================
# § 5 — Single tweak generation
# ============================================================

def _generate_tweak_id(
    layout_id:  str,
    category:   TweakCategory,
    rooms:      tuple[str, ...],
) -> str:
    """Deterministic tweak_id from layout + category + rooms.

    Same inputs → same id (R6 byte-equal replay)."""
    payload = f"{layout_id}|{category}|{','.join(sorted(rooms))}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"tweak_{h}"


def generate_one_tweak(
    *,
    layout_id:           str,
    layout_archetype:    LayoutArchetype,
    category:            TweakCategory,
    affected_room_ids:   tuple[str, ...],
    affected_grid_cells: tuple[str, ...],
    placed_rooms:        tuple[PlacedRoom, ...],
    structural_grid:     StructuralGrid,
    riser_groups:        tuple[RiserGroup, ...],
    door_placements:     tuple[DoorPlacement, ...],
    source_topology:     TopologyClassification,
    motivating_checks:   tuple[ProblemCheck, ...],
    motivation_basis:    str,
    prior_applied_tweak_ids: tuple[str, ...] = (),
) -> Optional[TweakOption] | MutationEnvelope:
    """Generate a single TweakOption for the given category, OR a
    MutationEnvelope when the per-instance severity computation
    classifies it as HEAVY.

    Returns either:
      - TweakOption (LIGHT or MEDIUM)
      - MutationEnvelope (HEAVY classification — surface as alternative pathway)
      - None when grounding can't be established (caller decides STRICT/WARN)
    """
    if not affected_room_ids and not affected_grid_cells:
        return None  # Can't ground

    # § 4.1 — Default severity from category
    default_severity: SeverityTier = TWEAK_CATEGORY_DEFAULT_SEVERITY.get(
        category, "medium",
    )

    # Predict topology invariance (R13 input)
    sorted_rooms = tuple(sorted(affected_room_ids))
    sorted_cells = tuple(sorted(affected_grid_cells))
    topology_invariance = predict_topology_invariance(
        tweak_category=category,
        source_topology=source_topology,
        affected_room_ids=sorted_rooms,
        placed_rooms=placed_rooms,
    )

    # § 4.2 — Context-aware adjustment
    context = detect_context_for_tweak(
        tweak_category=category,
        affected_room_ids=sorted_rooms,
        placed_rooms=placed_rooms,
        structural_grid=structural_grid,
        riser_groups=riser_groups,
        door_placements=door_placements,
        topology_invariance=topology_invariance,
    )

    # § 4.3 — Final severity assignment
    final_severity = promote_severity(
        default_severity=default_severity,
        context=context,
    )

    tweak_id = _generate_tweak_id(layout_id, category, sorted_rooms)

    # HEAVY → emit MutationEnvelope, buffer for session-level surfacing
    if final_severity == "heavy":
        classification: MutationClassification
        if context.topology_classification_change:
            classification = "topology_level_change"
        elif context.load_bearing_wall_involvement and context.structural_bay_boundary_cross:
            classification = "structural_level_change"
        else:
            classification = "structural_level_change"

        triggered = context.factor_names_triggered()
        reason = (
            f"Requested {category} would touch "
            f"{', '.join(triggered) if triggered else 'multiple structural elements'}, "
            f"which makes this a structural change rather than a layout tweak."
        )
        # v0.5 A6 — speculative preview text describes what the
        # restructured layout would look like at a high level, so users
        # can decide whether to step back to brief or pursue the heavy
        # pathway. Pre-linted templates by classification.
        if classification == "topology_level_change":
            preview = (
                f"Going ahead with this change would reshape the overall layout: "
                f"the circulation pattern in {_format_room_list(sorted_rooms)} "
                f"would change, and the corridor / lobby relationships nearby "
                f"would also shift. The system can sketch an alternative layout "
                f"variant if you'd like to see what that looks like."
            )
        else:  # structural_level_change
            preview = (
                f"Going ahead with this change would involve structural work: "
                f"the wall lines around {_format_room_list(sorted_rooms)} would "
                f"shift, and the column grid for the affected bay(s) would "
                f"need to be revised. The system can preview the restructured "
                f"version if you'd like to compare."
            )
        return MutationEnvelope(
            envelope_id="env_" + tweak_id[6:],
            requested_change_summary=(
                f"Tweak request: {category} affecting "
                f"{_format_room_list(sorted_rooms)}."
            ),
            classification=classification,
            why_not_a_tweak=reason,
            suggested_pathway=(
                "explore_alternative_layout"
                if classification == "structural_level_change"
                else "step_back_to_brief"
            ),
            estimated_pathway_effort=(
                "Exploring an alternative layout takes 60-90 seconds for the system."
            ),
            advisory_note=(
                "An alternative layout from the ranked set may achieve this "
                "without structural change."
            ),
            kick_back_payload=None,
            speculative_preview_text=preview,
        )

    # Compatibility assertions for MEDIUM (R15): pairwise against prior tweaks
    # v1.0 ships pairwise "compatible" assertions for simplicity; v1.x via
    # B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH adds N-way reasoning
    compatibility_assertions: tuple[CompatibilityAssertion, ...] = ()
    if final_severity == "medium" and prior_applied_tweak_ids:
        compatibility_assertions = tuple(
            CompatibilityAssertion(
                against_applied_tweak_id=prior_id,
                compatibility_kind="spatial_overlap_check",
                result="compatible",
                advisory_note=None,
            )
            for prior_id in sorted(prior_applied_tweak_ids)
        )

    # Build ApplySpecification
    apply_spec: ApplySpecification
    if final_severity == "light":
        apply_spec = _build_apply_spec_light(category, sorted_rooms)
    else:  # medium
        apply_spec = _build_apply_spec_medium(
            tweak_id=tweak_id,
            category=category,
            topology_invariance=topology_invariance,
            compatibility_assertions=compatibility_assertions,
        )

    # Build impacts
    cost_impact = _build_cost_impact(category)
    space_impact = _build_space_impact(category, sorted_rooms, placed_rooms)
    comfort_impact = _build_comfort_impact(category)

    # Recommendation flag
    rec_flag = classify_recommendation_flag(
        problem_checks_addressed=motivating_checks,
    )

    # Provenance
    motivated_by_check_id = motivating_checks[0].check_id if motivating_checks else None
    motivated_by_grid_cell = sorted_cells[0] if sorted_cells and not motivating_checks else None
    motivated_by_orientation = (
        "orientation_match" if "reorient" in category or "relocate" in category
        else None
    )
    # Ensure at least one motivation
    if not motivated_by_check_id and not motivated_by_grid_cell and not motivated_by_orientation:
        motivated_by_grid_cell = sorted_cells[0] if sorted_cells else None
        if not motivated_by_grid_cell:
            # Last resort — orientation as default motivation
            motivated_by_orientation = "general_layout_review"

    provenance = TweakProvenance(
        motivated_by_check_id=motivated_by_check_id,
        motivated_by_grid_cell_id=motivated_by_grid_cell,
        motivated_by_orientation=motivated_by_orientation,
        generation_basis=motivation_basis,
    )

    description = render_description(category, sorted_rooms)
    problem_links = tuple(sorted(c.check_id for c in motivating_checks))

    return TweakOption(
        tweak_id=tweak_id,
        tweak_category=category,
        severity_tier=final_severity,
        affected_room_ids=sorted_rooms,
        affected_grid_cells=sorted_cells,
        description=description,
        cost_impact=cost_impact,
        space_impact=space_impact,
        comfort_impact=comfort_impact,
        problem_report_links=problem_links,
        recommendation_flag=rec_flag,
        apply_specification=apply_spec,
        provenance=provenance,
        presented_count=0,
    )


# ============================================================
# § 6 — Per-layout candidate enumeration
# ============================================================

def _enumerate_candidates_from_problem_report(
    pr:           ProblemReport,
    placed_rooms: tuple[PlacedRoom, ...],
) -> list[tuple[TweakCategory, tuple[str, ...], ProblemCheck, str]]:
    """For each FAIL check in the ProblemReport with non-trivial severity,
    enumerate (category, room_ids, motivating_check, motivation_basis).

    Returns a list of candidate-triples that Phase β step 4 then turns
    into per-instance severity-classified tweaks."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], ProblemCheck, str]] = []
    valid_room_ids = {r.room_id for r in placed_rooms}

    for check in pr.applicable_checks:
        # Skip pass / warn / not_applicable — only act on fail
        if check.status != CheckStatus.FAIL:
            continue
        # Skip nice_to_have unless the check has affected rooms
        if check.severity == CheckSeverity.NICE_TO_HAVE and not check.affected_room_ids:
            continue
        # Map check_id → tweak categories (uses dimension_id + why_it_matters keywords)
        categories = lookup_tweak_categories_for_check(check)
        if not categories:
            continue
        # Use the check's affected_room_ids, intersected with valid rooms
        rooms = tuple(
            sorted(set(check.affected_room_ids) & valid_room_ids)
        )
        if not rooms:
            # Fall back to first room if no overlap (defensive)
            rooms = tuple(sorted(valid_room_ids))[:1] if valid_room_ids else ()
        for cat in categories:
            candidates.append((
                cat, rooms, check,
                f"ProblemCheck '{check.check_id}' ({check.severity.value}) "
                f"matches tweak category {cat!r}.",
            ))
    return candidates


def _enumerate_orientation_candidates(
    placed_rooms:   tuple[PlacedRoom, ...],
    plot_analysis,  # PlotAnalysis
) -> list[tuple[TweakCategory, tuple[str, ...], None, str]]:
    """Orientation-mismatch candidates per spec § 3 Phase β step 3."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], None, str]] = []
    for room in placed_rooms:
        # Kitchen facing N or W in warm-humid (Chennai) is suboptimal
        if room.room_function in ("kitchen", "kitchen_utility"):
            if room.cardinal_orientation in ("N", "W") and plot_analysis.climate_zone == "warm_humid":
                candidates.append((
                    "kitchen_reorient",
                    (room.room_id,),
                    None,
                    f"Kitchen at {room.cardinal_orientation} wall in warm-humid climate "
                    f"misaligns with morning light + ventilation principles.",
                ))
        # Pooja facing W is suboptimal per Vastu (opt-in)
        if room.room_function == "pooja":
            if room.cardinal_orientation == "W":
                candidates.append((
                    "pooja_relocate",
                    (room.room_id,),
                    None,
                    "Pooja at W wall misaligns with traditional E orientation "
                    "(opt-in via brief).",
                ))
    return candidates


def _enumerate_underutilized_cells(
    structural_grid: StructuralGrid,
    placed_rooms:    tuple[PlacedRoom, ...],
) -> list[tuple[TweakCategory, tuple[str, ...], None, str]]:
    """Structural-cell candidates per spec § 3 Phase β step 2."""
    candidates: list[tuple[TweakCategory, tuple[str, ...], None, str]] = []
    # Rooms whose function is "corridor" with large area → utility_zone_carveout candidate
    for room in placed_rooms:
        if room.room_function == "corridor" and room.geometry.area_sqft > 80.0:
            candidates.append((
                "utility_zone_carveout",
                (room.room_id,),
                None,
                f"Corridor at {room.geometry.area_sqft:.0f} sqft is oversized; "
                f"could host a utility carveout.",
            ))
    return candidates


# ============================================================
# § 7 — Bounded selection (spec § 3 Phase β step 5)
# ============================================================

def _priority_key(tweak: TweakOption) -> tuple[int, int, int, str]:
    """Sort key for bounded selection. Lower = higher priority.

    Per spec:
      (a) addresses critical problem    — recommendation_flag='suggested' first
      (b) is LIGHT severity              — LIGHT before MEDIUM
      (c) recommendation_flag='suggested' (already used in a)

    We use:
      key = (flag_rank, severity_rank, problem_link_count_descending, tweak_id)
    """
    flag_rank = {"suggested": 0, "optional": 1, "alternative": 2}[tweak.recommendation_flag]
    severity_rank = {"light": 0, "medium": 1, "heavy": 2}[tweak.severity_tier]
    # More problem links = higher priority (use negative for sort)
    link_count = -len(tweak.problem_report_links)
    return (flag_rank, severity_rank, link_count, tweak.tweak_id)


def _bounded_selection(
    tweaks: list[TweakOption],
    cap:    int = MAX_TWEAKS_PER_LAYOUT,
) -> list[TweakOption]:
    """Keep up to `cap` tweaks, prioritized per spec § 3 Phase β step 5."""
    if len(tweaks) <= cap:
        return tweaks
    sorted_tweaks = sorted(tweaks, key=_priority_key)
    return sorted_tweaks[:cap]


# ============================================================
# § 8 — Per-layout tweak set generation
# ============================================================

def _topology_for_layout(layout_index: int) -> TopologyClassification:
    """Heuristic: lookup table for v1.0. Phase β receives the
    StructuralGrid + PlacedRooms but not the C5 topology classification
    directly. v1.x will receive it explicitly.

    For v1.0 stub: use a deterministic mapping by index.
    """
    mapping: tuple[TopologyClassification, ...] = (
        "central_spine", "strip", "l_shape",
    )
    return mapping[layout_index % len(mapping)]


def generate_tweak_option_set_for_layout(
    *,
    layout_index:      int,
    bundle:            C3bInputBundle,
    config:            C3bRuntimeConfig,
    prior_applied:     tuple[str, ...] = (),
) -> tuple[TweakOptionSet, tuple[MutationEnvelope, ...], tuple[PerTweakError, ...]]:
    """Generate a TweakOptionSet for the layout at `layout_index`.

    Returns:
      - the TweakOptionSet
      - any MutationEnvelopes buffered for HEAVY rejections
      - any per-tweak errors collected (WARN mode)
    """
    from .alpha import archetype_for_rank

    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    if layout_index >= len(rankings):
        raise IndexError(f"layout_index {layout_index} out of range")

    ranking = rankings[layout_index]
    pr = bundle.problem_reports[layout_index]
    placed_rooms = bundle.placed_rooms_per_layout[layout_index]
    structural_grid = bundle.structural_grids_per_layout[layout_index]
    door_placements = bundle.door_placements_per_layout[layout_index]
    riser_groups = bundle.riser_groups_per_layout[layout_index]
    source_topology = _topology_for_layout(layout_index)

    layout_id = ranking.layout_signature
    archetype = archetype_for_rank(ranking.rank_position)

    # Enumerate candidates from 3 sources (spec § 3 Phase β 1-3)
    candidates_pr = _enumerate_candidates_from_problem_report(pr, placed_rooms)
    candidates_or = _enumerate_orientation_candidates(placed_rooms, bundle.plot_analysis)
    candidates_cell = _enumerate_underutilized_cells(structural_grid, placed_rooms)

    all_candidates = candidates_pr + candidates_or + candidates_cell

    tweaks: list[TweakOption] = []
    envelopes: list[MutationEnvelope] = []
    errors_collected: list[PerTweakError] = []

    seen_ids: set[str] = set()

    for cat, rooms, check, basis in all_candidates:
        motivating_checks = (check,) if check is not None else ()
        # Determine affected_grid_cells from rooms
        affected_cells = tuple(sorted({
            bay_id
            for room in placed_rooms
            if room.room_id in rooms
            for bay_id in room.structural_bay_ids
        }))
        try:
            result = generate_one_tweak(
                layout_id=layout_id,
                layout_archetype=archetype,
                category=cat,
                affected_room_ids=rooms,
                affected_grid_cells=affected_cells,
                placed_rooms=placed_rooms,
                structural_grid=structural_grid,
                riser_groups=riser_groups,
                door_placements=door_placements,
                source_topology=source_topology,
                motivating_checks=motivating_checks,
                motivation_basis=basis,
                prior_applied_tweak_ids=prior_applied,
            )
        except PerTweakError as e:
            if config.strict_mode == "strict":
                raise
            errors_collected.append(e)
            continue
        except ValueError as e:
            # Schema-level validation rejection during construction
            err = TweakGenerationError(
                f"Generated tweak rejected by schema validation: {e}",
                problem_check_id=(check.check_id if check else None),
                tweak_category_attempted=cat,
            )
            if config.strict_mode == "strict":
                raise err from e
            errors_collected.append(err)
            continue

        if result is None:
            continue
        if isinstance(result, MutationEnvelope):
            # Avoid duplicate envelope IDs
            if result.envelope_id not in {e.envelope_id for e in envelopes}:
                envelopes.append(result)
            continue
        # TweakOption
        if result.tweak_id in seen_ids:
            continue
        seen_ids.add(result.tweak_id)
        tweaks.append(result)

    # § 4.4 — Bounded selection
    selected = _bounded_selection(tweaks, cap=MAX_TWEAKS_PER_LAYOUT)
    selected_sorted = tuple(sorted(selected, key=lambda t: t.tweak_id))

    # Build the option-set advisory note
    if not selected_sorted:
        advisory = (
            "No specific tweaks surfaced for this layout. You could accept "
            "it as-is or explore the other ranked options."
        )
    else:
        n = len(selected_sorted)
        advisory = (
            f"{n} tweak option{'s' if n != 1 else ''} surfaced for this layout. "
            f"None are required — review each and accept what fits your priorities."
        )

    option_set = TweakOptionSet(
        layout_id=layout_id,
        layout_archetype=archetype,
        source_problem_report_id=pr.upstream_cache_key,
        tweaks=selected_sorted,
        overall_advisory_note=advisory,
    )

    return option_set, tuple(envelopes), tuple(errors_collected)


# ============================================================
# § 9 — Phase β entry point
# ============================================================

def run_phase_beta(
    session:    "TradeoffSession",  # from schema; quotes to avoid import cycle
    bundle:     C3bInputBundle,
    config:     C3bRuntimeConfig,
    prior_applied_tweak_ids: tuple[str, ...] = (),
) -> "TradeoffSession":
    """Execute Phase β: populate session.tweak_option_sets + envelopes.

    Input session must come from Phase α (status='open_for_user_input',
    empty tweak_option_sets). Returns a new session with tweak_option_sets
    + mutation_envelopes filled, re-signed.
    """
    from ..schema import TradeoffSession  # noqa: F401 — runtime import
    from .alpha import _resign_session

    if session.tweak_option_sets:
        # Phase β idempotent — if already populated, no-op
        return session

    all_option_sets: list[TweakOptionSet] = []
    all_envelopes: list[MutationEnvelope] = []

    rankings = bundle.selection_result.replay_identity.candidate_ranking_snapshot
    for layout_idx in range(len(rankings)):
        opt_set, envs, _errs = generate_tweak_option_set_for_layout(
            layout_index=layout_idx,
            bundle=bundle,
            config=config,
            prior_applied=prior_applied_tweak_ids,
        )
        all_option_sets.append(opt_set)
        all_envelopes.extend(envs)

    # Lex-ASC sort by layout_id (R6)
    sorted_option_sets = tuple(sorted(all_option_sets, key=lambda s: s.layout_id))
    # De-dup envelopes by envelope_id; lex-ASC
    seen_env: set[str] = set()
    unique_envelopes: list[MutationEnvelope] = []
    for env in sorted(all_envelopes, key=lambda e: e.envelope_id):
        if env.envelope_id in seen_env:
            continue
        seen_env.add(env.envelope_id)
        unique_envelopes.append(env)

    import dataclasses
    new_session = dataclasses.replace(
        session,
        tweak_option_sets=sorted_option_sets,
        mutation_envelopes=tuple(unique_envelopes),
    )
    return _resign_session(new_session, config)


__all__ = [
    "render_description",
    "classify_recommendation_flag",
    "generate_one_tweak",
    "generate_tweak_option_set_for_layout",
    "run_phase_beta",
    "_DESCRIPTION_TEMPLATES",
]
