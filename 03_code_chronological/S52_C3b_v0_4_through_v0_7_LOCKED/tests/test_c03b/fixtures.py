"""Fixtures for C3b tests.

Builders that return valid instances of upstream + C3b types. Each
builder accepts kwargs to override defaults so tests can mutate one
field while keeping the rest valid.

Convention: every builder is `make_<TypeName>(**overrides)`. Keep
defaults SIMPLE — they exist to fill required fields, not to
exercise interesting branches. Tests should pass explicit kwargs
for any field they care about.
"""
from __future__ import annotations

from typing import Any

from buildemup.components.c03a.contracts import KickbackContext, ResolvedBrief
from buildemup.components.c04.contracts import PlotAnalysis, PlotEdge
from buildemup.components.c07.contracts import (
    GridColumn,
    StructuralGrid,
    StructuralGridCell,
)
from buildemup.components.c10.contracts import Riser, RiserGroup
from buildemup.components.c12.contracts import PlacedRoom, RoomGeometry
from buildemup.components.c13.contracts import DoorPlacement
from buildemup.components.c16.contracts import (
    AttestedValue,
    AuthorityKind,
)
from buildemup.components.c03b.schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)
from buildemup.components.c03b.versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
)
from buildemup.utils.confidence import Confidence
from buildemup.utils.transparency import DerivationLine, TransparencyTriple


# ============================================================
# Upstream stub builders
# ============================================================

def make_resolved_brief(**ov: Any) -> ResolvedBrief:
    defaults: dict[str, Any] = {
        "brief_id":                "brief_001",
        "brief_signature":         "sig_brief_001",
        "resolved_plot_id":        "plot_001",
        "jurisdiction_profile_id": "tn_cdbr_2019_chennai",
        "resolved_room_program":   (("living", 1), ("kitchen", 1), ("bedroom_master", 1), ("bath_full", 1)),
        "resolved_floor_count":    1,
        "extreme_case_status":     "no_extreme_detected",
        "advisory_note":           "Standard brief, no extremes.",
    }
    defaults.update(ov)
    return ResolvedBrief(**defaults)


def make_kickback_context(**ov: Any) -> KickbackContext:
    defaults: dict[str, Any] = {
        "source_session_id":             "sess_001",
        "target_brief_field":            "room_program",
        "target_brief_field_advisory":   "You could revisit the room program to add another bedroom.",
        "user_requested_change":         "Add another bedroom to the first floor",
        "proposed_change_summary":       "Add 1 bedroom to room_program; rerun layout pipeline.",
        "estimated_pipeline_rerun_seconds": 60.0,
    }
    defaults.update(ov)
    return KickbackContext(**defaults)


def make_plot_edge(edge_id: str = "edge_n", **ov: Any) -> PlotEdge:
    defaults: dict[str, Any] = {
        "edge_id":         edge_id,
        "direction":       "N",
        "length_m":        12.0,
        "is_road_facing":  False,
    }
    defaults.update(ov)
    return PlotEdge(**defaults)


def make_plot_analysis(**ov: Any) -> PlotAnalysis:
    defaults: dict[str, Any] = {
        "plot_analysis_id":         "plot_an_001",
        "plot_signature":           "sig_plot_001",
        "jurisdiction_profile_id":  "tn_cdbr_2019_chennai",
        "locality_label":           "Chennai-OMR",
        "climate_zone":             "warm_humid",
        "plot_area_sqft":           1500.0,
        "plot_dimensions_m":        (12.0, 12.0),
        "plot_edges":               (
            make_plot_edge("edge_n", direction="N"),
            make_plot_edge("edge_e", direction="E"),
            make_plot_edge("edge_s", direction="S", is_road_facing=True),
            make_plot_edge("edge_w", direction="W"),
        ),
        "dominant_road_direction":  "S",
        "primary_ventilation_axis": "N_S",
    }
    defaults.update(ov)
    return PlotAnalysis(**defaults)


def make_grid_column(column_id: str = "col_001", **ov: Any) -> GridColumn:
    defaults: dict[str, Any] = {
        "column_id":  column_id,
        "x_mm":       0.0,
        "y_mm":       0.0,
        "floor":      0,
        "size_mm":    (230, 230),
    }
    defaults.update(ov)
    return GridColumn(**defaults)


def make_structural_grid_cell(cell_id: str = "cell_001", **ov: Any) -> StructuralGridCell:
    defaults: dict[str, Any] = {
        "cell_id":                    cell_id,
        "floor":                      0,
        "corner_column_ids":          ("col_001", "col_002", "col_003", "col_004"),
        "bay_dimensions_m":           (3.0, 3.0),
        "is_load_bearing_perimeter":  True,
        "contains_riser_chase":       False,
    }
    defaults.update(ov)
    return StructuralGridCell(**defaults)


def make_structural_grid(**ov: Any) -> StructuralGrid:
    defaults: dict[str, Any] = {
        "grid_id":      "grid_001",
        "floor_count":  1,
        "columns":      (make_grid_column("col_001"),),
        "cells":        (make_structural_grid_cell("cell_001"),),
    }
    defaults.update(ov)
    return StructuralGrid(**defaults)


def make_riser(riser_id: str = "riser_001", **ov: Any) -> Riser:
    defaults: dict[str, Any] = {
        "riser_id":       riser_id,
        "riser_kind":     "combined",
        "x_mm":           500.0,
        "y_mm":           500.0,
        "served_floors":  (0,),
    }
    defaults.update(ov)
    return Riser(**defaults)


def make_riser_group(**ov: Any) -> RiserGroup:
    defaults: dict[str, Any] = {
        "riser_group_id":   "rg_001",
        "risers":           (make_riser("riser_001"),),
        "served_room_ids":  ("room_kitchen", "room_bath_full"),
        "chase_width_mm":   600.0,
    }
    defaults.update(ov)
    return RiserGroup(**defaults)


def make_room_geometry(**ov: Any) -> RoomGeometry:
    defaults: dict[str, Any] = {
        "x_mm":     0.0,
        "y_mm":     0.0,
        "width_mm": 3000.0,
        "depth_mm": 3000.0,
    }
    defaults.update(ov)
    return RoomGeometry(**defaults)


def make_placed_room(room_id: str = "room_001", **ov: Any) -> PlacedRoom:
    defaults: dict[str, Any] = {
        "room_id":              room_id,
        "room_function":        "bedroom_master",
        "floor":                0,
        "geometry":             make_room_geometry(),
        "structural_bay_ids":   ("cell_001",),
        "adjacent_room_ids":    (),
        "has_external_wall":    True,
        "cardinal_orientation": "S",
    }
    defaults.update(ov)
    return PlacedRoom(**defaults)


def make_door_placement(door_id: str = "door_001", **ov: Any) -> DoorPlacement:
    defaults: dict[str, Any] = {
        "door_id":    door_id,
        "door_kind":  "interior_room",
        "room_a_id":  "room_001",
        "room_b_id":  "room_002",
        "wall_id":    "wall_001",
        "width_mm":   900,
        "height_mm":  2100,
        "swing":      "into_room_a",
    }
    defaults.update(ov)
    return DoorPlacement(**defaults)


# ============================================================
# C3b output builders
# ============================================================

def make_attested_value(value: float = 100.0, **ov: Any) -> AttestedValue:
    defaults: dict[str, Any] = {
        "value":           value,
        "authority":       AuthorityKind.LOCALLY_DERIVED,
        "upstream_source": None,
        "derivation_note": "test fixture",
    }
    defaults.update(ov)
    return AttestedValue(**defaults)


def make_transparency_triple(**ov: Any) -> TransparencyTriple:
    defaults: dict[str, Any] = {
        "label":           "Test cost",
        "exact_value":     10000.0,
        "unit":            "INR",
        "uncertainty_pct": 10.0,
        "confidence":      Confidence.MEDIUM,
        "derivation":      [DerivationLine(label="Test cost line", amount=10000.0)],
        "notes":           [],
    }
    defaults.update(ov)
    return TransparencyTriple(**defaults)


def make_topology_invariance_result(**ov: Any) -> TopologyInvarianceResult:
    defaults: dict[str, Any] = {
        "source_topology":      "central_spine",
        "predicted_topology":   "central_spine",
        "invariance_preserved": True,
        "prediction_basis":     "structural_grid_invariant",
        "advisory_note":        None,
    }
    defaults.update(ov)
    return TopologyInvarianceResult(**defaults)


def make_subset_rerun_request(**ov: Any) -> SubsetRerunRequest:
    defaults: dict[str, Any] = {
        "trigger_tweak_id":             "tweak_001",
        "trigger_tweak_category":       "kitchen_reorient",
        "components_to_rerun":          ("c10", "c12", "c13"),
        "downstream_impact_set":        ("cross_ventilation", "natural_light", "wet_zone_stacks"),
        "topology_invariance_check":    make_topology_invariance_result(),
        "expected_completion_seconds":  2.5,
        "rerun_anchor":                 "kitchen_east_aligned",
        "compatibility_assertions":     (),
    }
    defaults.update(ov)
    return SubsetRerunRequest(**defaults)


def make_compatibility_assertion(**ov: Any) -> CompatibilityAssertion:
    defaults: dict[str, Any] = {
        "against_applied_tweak_id":  "tweak_prior_001",
        "compatibility_kind":        "spatial_overlap_check",
        "result":                    "compatible",
        "advisory_note":             None,
    }
    defaults.update(ov)
    return CompatibilityAssertion(**defaults)


def make_kick_back_payload(**ov: Any) -> KickBackPayload:
    defaults: dict[str, Any] = {
        "target_brief_field":              "room_program",
        "target_brief_field_advisory":     "You could step back to revisit the room program.",
        "user_requested_change":           "Add another bedroom",
        "proposed_change_summary":         "Re-open room_program field; add 1 bedroom.",
    }
    defaults.update(ov)
    return KickBackPayload(**defaults)


def make_mutation_envelope(**ov: Any) -> MutationEnvelope:
    defaults: dict[str, Any] = {
        "envelope_id":              "env_001",
        "requested_change_summary": "Add another bedroom to the first floor",
        "classification":           "brief_level_change",
        "why_not_a_tweak":          "Adding a bedroom changes the room count, which is configured at the brief stage.",
        "suggested_pathway":        "step_back_to_brief",
        "estimated_pathway_effort": "Stepping back takes 1-2 minutes plus a 60-second rerun.",
        "advisory_note":            "We can revisit the brief and re-run the layout pipeline.",
        "kick_back_payload":        make_kick_back_payload(),
    }
    defaults.update(ov)
    return MutationEnvelope(**defaults)


def make_space_impact(**ov: Any) -> SpaceImpact:
    defaults: dict[str, Any] = {
        "per_room_sqft_delta":     (("room_001", -5.0), ("room_002", 5.0)),
        "total_sqft_delta":        0.0,
        "total_carpet_area_after": make_attested_value(value=950.0),
        "advisory_note":           "Net zero space; rooms re-balanced.",
    }
    defaults.update(ov)
    return SpaceImpact(**defaults)


def make_comfort_impact(**ov: Any) -> ComfortImpact:
    defaults: dict[str, Any] = {
        "dimensions_affected":  ("cross_ventilation", "natural_light"),
        "direction":            "improves",
        "magnitude":            "moderate",
        "advisory_note":        "Improved east-facing exposure.",
    }
    defaults.update(ov)
    return ComfortImpact(**defaults)


def make_geometry_local_payload(**ov: Any) -> GeometryLocalPayload:
    defaults: dict[str, Any] = {
        "new_room_function_assignments": (("room_001", "study"),),
        "new_door_placements_replace":   (),
        "new_window_assignments":        (),
        "advisory_note":                 "Room repurposed.",
    }
    defaults.update(ov)
    return GeometryLocalPayload(**defaults)


def make_finish_schedule_payload(**ov: Any) -> FinishSchedulePayload:
    defaults: dict[str, Any] = {
        "room_finish_overrides": (
            ("room_001", "flooring", "premium_vitrified_800x800"),
        ),
        "advisory_note":         "Premium vitrified tiles in master bedroom.",
    }
    defaults.update(ov)
    return FinishSchedulePayload(**defaults)


def make_apply_specification_geometry(**ov: Any) -> ApplySpecification:
    defaults: dict[str, Any] = {
        "mutation_kind":           "geometry_local",
        "geometry_local_payload":  make_geometry_local_payload(),
        "subset_rerun_payload":    None,
        "finish_schedule_payload": None,
    }
    defaults.update(ov)
    return ApplySpecification(**defaults)


def make_apply_specification_subset(**ov: Any) -> ApplySpecification:
    defaults: dict[str, Any] = {
        "mutation_kind":           "subset_rerun",
        "geometry_local_payload":  None,
        "subset_rerun_payload":    make_subset_rerun_request(),
        "finish_schedule_payload": None,
    }
    defaults.update(ov)
    return ApplySpecification(**defaults)


def make_apply_specification_finish(**ov: Any) -> ApplySpecification:
    defaults: dict[str, Any] = {
        "mutation_kind":           "finish_schedule_only",
        "geometry_local_payload":  None,
        "subset_rerun_payload":    None,
        "finish_schedule_payload": make_finish_schedule_payload(),
    }
    defaults.update(ov)
    return ApplySpecification(**defaults)


def make_tweak_provenance(**ov: Any) -> TweakProvenance:
    defaults: dict[str, Any] = {
        "motivated_by_check_id":     "check_001",
        "motivated_by_grid_cell_id": None,
        "motivated_by_orientation":  None,
        "generation_basis":          "ProblemReport check 'shower_min_area' suggests room_resize.",
    }
    defaults.update(ov)
    return TweakProvenance(**defaults)


def make_tweak_option_light(tweak_id: str = "tweak_001", **ov: Any) -> TweakOption:
    """A valid LIGHT tweak (finish-schedule-only mutation)."""
    defaults: dict[str, Any] = {
        "tweak_id":             tweak_id,
        "tweak_category":       "finish_upgrade",
        "severity_tier":        "light",
        "affected_room_ids":    ("room_001",),
        "affected_grid_cells":  (),
        "description":          "You could upgrade the master bedroom flooring to premium vitrified tiles.",
        "cost_impact":          make_transparency_triple(),
        "space_impact":         make_space_impact(total_sqft_delta=0.0),
        "comfort_impact":       make_comfort_impact(direction="improves", magnitude="small"),
        "problem_report_links": ("check_001",),
        "recommendation_flag":  "optional",
        "apply_specification":  make_apply_specification_finish(),
        "provenance":           make_tweak_provenance(),
        "presented_count":      0,
    }
    defaults.update(ov)
    return TweakOption(**defaults)


def make_tweak_option_medium(tweak_id: str = "tweak_002", **ov: Any) -> TweakOption:
    """A valid MEDIUM tweak (subset-rerun mutation)."""
    defaults: dict[str, Any] = {
        "tweak_id":             tweak_id,
        "tweak_category":       "kitchen_reorient",
        "severity_tier":        "medium",
        "affected_room_ids":    ("room_kitchen",),
        "affected_grid_cells":  ("cell_001",),
        "description":          "You could move the kitchen to the east wall for direct morning light.",
        "cost_impact":          make_transparency_triple(),
        "space_impact":         make_space_impact(total_sqft_delta=0.0),
        "comfort_impact":       make_comfort_impact(),
        "problem_report_links": ("check_002",),
        "recommendation_flag":  "suggested",
        "apply_specification":  make_apply_specification_subset(),
        "provenance":           make_tweak_provenance(motivated_by_orientation="east_alignment", motivated_by_check_id=None, generation_basis="Orientation mismatch — kitchen N-facing in Chennai."),
        "presented_count":      0,
    }
    defaults.update(ov)
    return TweakOption(**defaults)


def make_tweak_option_set(**ov: Any) -> TweakOptionSet:
    defaults: dict[str, Any] = {
        "layout_id":                 "layout_a",
        "layout_archetype":          "cost_efficient",
        "source_problem_report_id":  "pr_layout_a",
        "tweaks":                    (make_tweak_option_light("tweak_001"), make_tweak_option_medium("tweak_002")),
        "overall_advisory_note":     "Two tweaks could improve comfort with small cost adjustments.",
    }
    defaults.update(ov)
    return TweakOptionSet(**defaults)


def make_apply_outcome(**ov: Any) -> ApplyOutcome:
    defaults: dict[str, Any] = {
        "apply_status":            "applied_successfully",
        "error_summary":           None,
        "new_layout_signature":    "sig_after_001",
        "new_problem_report_id":   "pr_after_001",
        "regression_detected":     False,
        "newly_critical_check_ids": (),
    }
    defaults.update(ov)
    return ApplyOutcome(**defaults)


def make_session_turn(**ov: Any) -> SessionTurn:
    defaults: dict[str, Any] = {
        "turn_id":             "turn_001",
        "iteration_index":     0,
        "timestamp_offset_ms": 1000,
        "presented_tweaks":    ("tweak_001", "tweak_002"),
        "user_action":         "accepted_tweak",
        "chosen_tweak_id":     "tweak_001",
        "apply_outcome":       make_apply_outcome(),
        "post_turn_status":    "open_for_user_input",
    }
    defaults.update(ov)
    return SessionTurn(**defaults)


def make_resolved_selection(**ov: Any) -> ResolvedSelection:
    defaults: dict[str, Any] = {
        "chosen_layout_id":         "layout_a",
        "chosen_layout_archetype":  "everyday_living",
        "applied_tweaks":           ("tweak_001",),
        "final_layout_signature":   "sig_final_001",
        "final_problem_report_id":  "pr_final_001",
        "total_cost_delta":         make_transparency_triple(),
        "total_space_delta":        make_space_impact(),
        "final_handoff_advisory":   "Final layout chosen with 1 tweak applied.",
    }
    defaults.update(ov)
    return ResolvedSelection(**defaults)


def make_advisory_flag(**ov: Any) -> AdvisoryFlag:
    defaults: dict[str, Any] = {
        "flag_id":       "flag_001",
        "kind":          "compatibility_ambiguous",
        "advisory_note": "One compatibility assertion came back ambiguous.",
        "related_ids":   ("tweak_001",),
    }
    defaults.update(ov)
    return AdvisoryFlag(**defaults)


def make_tradeoff_session(**ov: Any) -> TradeoffSession:
    defaults: dict[str, Any] = {
        "session_id":                  "sess_001",
        "source_selection_result_id":  "selres_001",
        "source_brief_signature":      "sig_brief_001",
        "source_plot_analysis_id":     "plot_an_001",
        "c3b_version":                 C3B_VERSION,
        "c3b_schema_version":          C3B_SESSION_SCHEMA_VERSION,
        "jurisdiction_profile_id":     "tn_cdbr_2019_chennai",
        "tweak_option_sets":           (make_tweak_option_set(),),
        "session_history":             (),
        "iteration_count":             0,
        "iteration_cap":               5,
        "current_status":              "open_for_user_input",
        "canonical_replay_signature":  "a" * 64,
        "presentation_signature":      "b" * 64,
        "schema_descriptor_digest":    "c" * 64,
        "resolved_selection":          None,
        "advisory_flags":              (),
        "mutation_envelopes":          (),
    }
    defaults.update(ov)
    return TradeoffSession(**defaults)


# ============================================================
# Bundle-level fixtures (Phase α / β / γ / δ / ε / ζ tests)
# ============================================================

def make_problem_check(check_id: str = "shower_min_length", **ov: Any):
    """Build a real C15 ProblemCheck."""
    from buildemup.components.c15.schema import (
        CheckEpistemicKind, CheckSeverity, CheckStatus, ProblemCheck,
    )
    defaults = {
        "check_id": check_id,
        "dimension_id": 7,
        "status": CheckStatus.FAIL,
        "severity": CheckSeverity.IMPORTANT,
        "epistemic_kind": CheckEpistemicKind.REGULATORY,
        "affected_room_ids": ("room_001",),
        "rule_citation": "TN CDBR Cl. 6.3.2",
        "why_it_matters": "Shower length below minimum hampers daily use.",
        "suggested_mitigation": None,
        "measurement": None,
    }
    defaults.update(ov)
    return ProblemCheck(**defaults)


def make_problem_report(
    *,
    checks: tuple = (),
    upstream_cache_key: str = "cache_layout_001",
    **ov: Any,
):
    """Build a real C15 ProblemReport."""
    from buildemup.components.c15.schema import (
        CoverageQuality, CulturalProfile, DimensionMaturity, DimensionSummary,
        ProblemReport, UnconventionalPatternHint,
    )
    # Build per-dimension summaries from actual check distribution
    from collections import defaultdict
    by_dim: dict[int, list] = defaultdict(list)
    for c in checks:
        by_dim[c.dimension_id].append(c)

    if checks:
        from buildemup.components.c15.schema import CheckStatus as _CS
        dim_summary_tuple = tuple(
            DimensionSummary(
                dimension_id=dim,
                dimension_name=f"dim_{dim}",
                n_applicable=len(cks),
                n_deferred=0,
                n_pass=sum(1 for c in cks if c.status == _CS.PASS),
                n_warn=sum(1 for c in cks if c.status == _CS.WARN),
                n_fail=sum(1 for c in cks if c.status == _CS.FAIL),
                maturity=DimensionMaturity.RUNNABLE,
            )
            for dim, cks in sorted(by_dim.items())
        )
    else:
        dim_summary_tuple = ()

    defaults = {
        "source_placed_candidate_signature": "sig_" + upstream_cache_key,
        "applicable_checks": tuple(sorted(checks, key=lambda c: c.check_id)),
        "deferred_checks": (),
        "dimension_summary": dim_summary_tuple,
        "dimensions_not_evaluated": ("acoustic_experience", "emotional_comfort"),
        "unconventional_pattern_hint": UnconventionalPatternHint(
            detected=False, suspected_patterns=(),
            confidence_caveat="", affected_check_ids=(),
        ),
        "cultural_profile_active": CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        "c13_advisory_flags": (),
        "c14_structural_flags": (),
        "c14_preference_flags": (),
        "c15_version": "v1.0.LOCKED",
        "c15_check_registry_version": 1,
        "advisory_schema_version": 1,
        "upstream_cache_key": upstream_cache_key,
        "coverage_quality": CoverageQuality.HIGH,
        "ratio_applicable": 0.95,
    }
    defaults.update(ov)
    return ProblemReport(**defaults)


def make_candidate_ranking(rank_position: int = 1, **ov: Any):
    """Build a real C16 CandidateRanking. rank_position is 1-indexed."""
    from buildemup.components.c16.contracts import CandidateRanking
    defaults = {
        "layout_signature": f"layout_sig_{rank_position:03d}",
        "rank_position": rank_position,
        "score": [0.92, 0.85, 0.78][rank_position - 1] if 1 <= rank_position <= 3 else 0.5,
        "selection_marker": rank_position == 1,
    }
    defaults.update(ov)
    return CandidateRanking(**defaults)


def make_selection_result(
    *,
    candidate_rankings: tuple = (),
    problem_reports: tuple = (),
    **ov: Any,
):
    """Build a real C16 SelectionResult."""
    from buildemup.components.c16.contracts import (
        SelectionAuditMetadata, SelectionReason, SelectionReplayIdentity,
        SelectionResult,
    )
    defaults = {
        "replay_identity": SelectionReplayIdentity(
            selected_layout_signature=(
                candidate_rankings[0].layout_signature
                if candidate_rankings else "sig_unknown"
            ),
            selector_version="v1.2.LOCKED",
            selection_reason=SelectionReason.RANKER_TOP,
            candidate_ranking_snapshot=candidate_rankings,
            upstream_problem_reports=problem_reports,
        ),
        "audit_metadata": SelectionAuditMetadata(
            selection_timestamp_utc="2026-01-01T00:00:00Z",
            human_override=None,
            selector_instance_id="test_selector",
            selection_machine_fingerprint="test_fp",
        ),
    }
    defaults.update(ov)
    return SelectionResult(**defaults)


def _make_default_room(room_id: str, function: str = "bedroom",
                       area_sqft: float = 120.0, orientation: str = "S",
                       bay_ids: tuple = ("bay_001",),
                       external_wall: bool = True):
    # Convert sqft → mm (assume square room for default fixture)
    # 1 sqft ≈ 92,903 mm²; side ≈ sqrt(area_sqft * 92903)
    import math
    side_mm = math.sqrt(area_sqft * 92903.04)
    return make_placed_room(
        room_id=room_id,
        room_function=function,
        geometry=make_room_geometry(width_mm=side_mm, depth_mm=side_mm),
        cardinal_orientation=orientation,
        has_external_wall=external_wall,
        adjacent_room_ids=(),
        structural_bay_ids=bay_ids,
    )


def make_bundle_3_layouts_happy_path(**ov):
    """Build a C3bInputBundle with 3 diverse layouts + ProblemReports
    that contain FAIL checks matching tweak patterns. Used by Phase α/β/γ
    happy-path tests."""
    from buildemup.components.c03b.contracts import C3bInputBundle
    from buildemup.components.c15.schema import CheckSeverity, CheckStatus

    # ProblemReport per layout — each has a fail check that maps to a tweak.
    # Real C15 check_ids use P{dim}.{idx} format; dimension_id must match.
    pr1_checks = (
        make_problem_check(
            check_id="P7.1",                 # D7 bathroom
            dimension_id=7,
            severity=CheckSeverity.IMPORTANT,
            affected_room_ids=("bath_001",),
            why_it_matters="The shower length is below the minimum needed for daily use.",
        ),
        make_problem_check(
            check_id="P6.1",                 # D6 kitchen
            dimension_id=6,
            severity=CheckSeverity.IMPORTANT,
            affected_room_ids=("kitchen_001",),
            why_it_matters="Kitchen orientation faces north, reducing morning light.",
        ),
    )
    pr2_checks = (
        make_problem_check(
            check_id="P8.1",                 # D8 storage
            dimension_id=8,
            severity=CheckSeverity.NICE_TO_HAVE,
            affected_room_ids=("master_001",),
            why_it_matters="Storage volume is below typical for the bedroom size.",
        ),
    )
    pr3_checks = (
        make_problem_check(
            check_id="P7.2",                 # D7 bathroom — wet zone stack
            dimension_id=7,
            severity=CheckSeverity.CRITICAL,
            affected_room_ids=("bath_001", "kitchen_001"),
            why_it_matters="Wet zone stacks across floors are misaligned; long plumbing runs.",
        ),
    )

    pr_list = (
        make_problem_report(checks=pr1_checks, upstream_cache_key="cache_l0"),
        make_problem_report(checks=pr2_checks, upstream_cache_key="cache_l1"),
        make_problem_report(checks=pr3_checks, upstream_cache_key="cache_l2"),
    )
    rankings = (
        make_candidate_ranking(rank_position=1, score=0.95),
        make_candidate_ranking(rank_position=2, score=0.80),
        make_candidate_ranking(rank_position=3, score=0.65),
    )
    sr = make_selection_result(
        candidate_rankings=rankings,
        problem_reports=pr_list,
    )

    # Placed rooms per layout (each layout has bath, kitchen, bedroom, master)
    # NOTE: RoomFunction is a Literal; valid values: living, dining, kitchen,
    # kitchen_utility, bedroom_master, bedroom_secondary, bath_full, bath_attached,
    # pooja, balcony, lobby, corridor, stair, lift_lobby, store, utility, etc.
    placed_rooms_per_layout = (
        (
            _make_default_room("bath_001", "bath_full", 35.0, "N",
                              bay_ids=("bay_001",)),
            _make_default_room("kitchen_001", "kitchen", 90.0, "N",
                              bay_ids=("bay_002",)),
            _make_default_room("bedroom_001", "bedroom_secondary", 120.0, "S",
                              bay_ids=("bay_003",)),
            _make_default_room("master_001", "bedroom_master", 180.0, "E",
                              bay_ids=("bay_004",)),
            _make_default_room("corridor_001", "corridor", 95.0, "NE",
                              bay_ids=("bay_005",), external_wall=False),
        ),
        (
            _make_default_room("bath_001", "bath_full", 40.0, "E",
                              bay_ids=("bay_001",)),
            _make_default_room("kitchen_001", "kitchen", 100.0, "E",
                              bay_ids=("bay_002",)),
            _make_default_room("master_001", "bedroom_master", 200.0, "S",
                              bay_ids=("bay_003",)),
        ),
        (
            _make_default_room("bath_001", "bath_full", 45.0, "W",
                              bay_ids=("bay_001",)),
            _make_default_room("kitchen_001", "kitchen", 110.0, "S",
                              bay_ids=("bay_002",)),
            _make_default_room("master_001", "bedroom_master", 220.0, "N",
                              bay_ids=("bay_003",)),
        ),
    )

    # Structural grid (shared shape across layouts)
    cells_per_layout = []
    cols_per_layout = []
    for i in range(3):
        cells = []
        cols = []
        for j, room in enumerate(placed_rooms_per_layout[i]):
            for bay_id in room.structural_bay_ids:
                # 4 distinct corner cols per bay (deterministic)
                col_ids = (
                    f"col_l{i}_b{j}_a", f"col_l{i}_b{j}_b",
                    f"col_l{i}_b{j}_c", f"col_l{i}_b{j}_d",
                )
                for cid in col_ids:
                    cols.append(make_grid_column(column_id=cid))
                cells.append(make_structural_grid_cell(
                    cell_id=bay_id,
                    is_load_bearing_perimeter=False,
                    corner_column_ids=col_ids,
                ))
        # Dedupe by cell_id and column_id
        seen_cells = set(); dedup_cells = []
        for c in cells:
            if c.cell_id not in seen_cells:
                seen_cells.add(c.cell_id); dedup_cells.append(c)
        seen_cols = set(); dedup_cols = []
        for c in cols:
            if c.column_id not in seen_cols:
                seen_cols.add(c.column_id); dedup_cols.append(c)
        cells_per_layout.append(tuple(dedup_cells))
        cols_per_layout.append(tuple(dedup_cols))

    grids_per_layout = tuple(
        make_structural_grid(
            grid_id=f"grid_l{i}",
            cells=cells_per_layout[i],
            columns=cols_per_layout[i],
        )
        for i in range(3)
    )
    riser_groups_per_layout = (
        (make_riser_group(
            riser_group_id="rg_001",
            served_room_ids=("bath_001",),
        ),),
        (),
        (),
    )
    doors_per_layout = (
        (make_door_placement(door_id="door_001", room_a_id="bedroom_001",
                            room_b_id="corridor_001"),),
        (),
        (),
    )

    bundle_defaults = dict(
        selection_result=sr,
        resolved_brief=make_resolved_brief(),
        plot_analysis=make_plot_analysis(),
        problem_reports=pr_list,
        placed_rooms_per_layout=placed_rooms_per_layout,
        structural_grids_per_layout=grids_per_layout,
        riser_groups_per_layout=riser_groups_per_layout,
        door_placements_per_layout=doors_per_layout,
    )
    bundle_defaults.update(ov)
    return C3bInputBundle(**bundle_defaults)


def make_bundle_preview_mode():
    """Bundle with extreme_case_status=preview_mode → applicability fails."""
    bundle = make_bundle_3_layouts_happy_path()
    import dataclasses
    return dataclasses.replace(
        bundle,
        resolved_brief=make_resolved_brief(extreme_case_status="preview_mode"),
    )


def make_bundle_high_ambiguity():
    """Bundle with LOW coverage_quality on one PR."""
    from buildemup.components.c15.schema import CoverageQuality
    import dataclasses
    bundle = make_bundle_3_layouts_happy_path()
    new_pr0 = dataclasses.replace(
        bundle.problem_reports[0],
        coverage_quality=CoverageQuality.LOW,
        ratio_applicable=0.30,    # match LOW per C15 § 14.3 derivation
    )
    new_prs = (new_pr0,) + bundle.problem_reports[1:]
    new_sr_replay = dataclasses.replace(
        bundle.selection_result.replay_identity,
        upstream_problem_reports=new_prs,
    )
    new_sr = dataclasses.replace(bundle.selection_result, replay_identity=new_sr_replay)
    return dataclasses.replace(bundle, problem_reports=new_prs, selection_result=new_sr)


def make_bundle_pareto_collapse():
    """Bundle where 3 rankings have nearly identical scores AND nearly
    identical room areas → diversity floors not met."""
    import dataclasses
    bundle = make_bundle_3_layouts_happy_path()
    new_rankings = (
        make_candidate_ranking(rank_position=1, score=0.90),
        make_candidate_ranking(rank_position=2, score=0.895),
        make_candidate_ranking(rank_position=3, score=0.89),
    )
    new_sr_replay = dataclasses.replace(
        bundle.selection_result.replay_identity,
        candidate_ranking_snapshot=new_rankings,
    )
    new_sr = dataclasses.replace(bundle.selection_result, replay_identity=new_sr_replay)
    # Make placed_rooms_per_layout identical for cross-layout sqft equality
    same_rooms = bundle.placed_rooms_per_layout[0]
    new_placed = (same_rooms, same_rooms, same_rooms)
    return dataclasses.replace(
        bundle,
        selection_result=new_sr,
        placed_rooms_per_layout=new_placed,
    )
