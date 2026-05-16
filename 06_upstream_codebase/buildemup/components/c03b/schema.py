"""
C3b — Post-Layout Trade-off Negotiation — output schema
========================================================

Spec: C3b v0.4.LOCKED §§ 2 + 7. Build session: S52.

This module defines all C3b output dataclasses. Inputs live in
`contracts.py`. Phase functions (α–ζ) live in `phases/` (built in
S53–S55). Orchestrator lives in `orchestrator.py` (built S55).

Dataclass-level invariant enforcement:

  R3   Layout grounding         — TweakOption __post_init__: at least
                                  one of affected_room_ids /
                                  affected_grid_cells must be non-empty
  R4   Severity discipline      — TweakOption __post_init__: LIGHT cannot
                                  carry a subset_rerun_payload; MEDIUM
                                  must carry subset_rerun_payload with
                                  non-empty downstream_impact_set
  R5   Recommendation flag      — RecommendationFlag is a Literal enum
                                  (structural marker only)
  R8   Schema versioning        — TradeoffSession.c3b_schema_version
                                  must match constant
  R13  Topology invariance      — MEDIUM tweaks MUST carry
                                  TopologyInvarianceResult; if
                                  invariance_preserved is False, severity
                                  cannot be 'medium' (must be 'heavy')
  R15  Multi-tweak compatibility — MEDIUM tweaks MUST carry
                                  compatibility_assertions (may be empty
                                  if no prior tweaks)
  R16  Single-linear-history    — TradeoffSession.session_history is a
                                  tuple (append-only by immutability);
                                  current_status enum pins the lifecycle
  R2   Advisory-tone lint       — every user-facing string is linted at
                                  construction

Rule 11 self-analysis (worst issues hunted):
  1. Layout grounding (R3) checks NON-EMPTINESS, not VALID-ID. The valid-ID
     check requires the upstream PlacedRoom / StructuralGridCell set,
     which lives in Phase β at composition time. Documented; tests for
     the integration check live in test_phase_beta (later).
  2. Severity-tier ↔ mutation_kind coupling enforced AT CONSTRUCTION
     (R4) — the dataclass refuses inconsistent combos. Stronger than
     deferring to a separate validate() call.
  3. TopologyInvarianceResult is required for MEDIUM but optional for
     LIGHT (a finish change doesn't touch topology). Tests cover both.
  4. CompatibilityAssertions tuple may be empty when there are no
     prior applied tweaks — empty is valid (not the same as missing).
  5. MutationEnvelope is a SEPARATE top-level type, not embedded in
     TweakOption; HEAVY tweaks are not surfaced as TweakOptions per R4.
  6. AdvisoryFlag is intentionally lightweight (kind enum + advisory
     text); the C16 v1.2 LOCKED AdvisoryFlag has more fields but C3b
     doesn't consume them yet. Kept local for now; will lift if/when
     C3b feeds C16 advisories directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Optional, Tuple

from .advisory_lint import lint_advisory_text
from .versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    EXPECTED_LAYOUT_COUNT,
    ITERATION_CAP_DEFAULT,
    ITERATION_CAP_HARD_CEILING,
    MAX_REPRESENT_COUNT,
    MAX_TWEAKS_PER_LAYOUT,
    SESSION_HISTORY_HARD_CEILING,
    TWEAKS_PER_LAYOUT_HARD_CEILING,
    TWEAK_COST_IMPACT_CEILING_INR,
    TWEAK_SPACE_IMPACT_CEILING_SQFT,
)

# ----- Re-used utility / upstream types ---------------------------
from buildemup.utils.transparency import TransparencyTriple
from buildemup.components.c16.contracts import AttestedValue, AuthorityKind


# ============================================================
# § 1 — Discriminated enums (Literals)
# ============================================================

TweakCategory = Literal[
    "room_swap",
    "room_resize",
    "balcony_add",
    "balcony_remove",
    "door_relocate",
    "window_resize",
    "wet_zone_restage",
    "finish_upgrade",
    "finish_downgrade",
    "storage_add",
    "pooja_relocate",
    "kitchen_reorient",
    "utility_zone_carveout",
]
"""Per spec § 2.3. 13 categories. Used by static
TWEAK_CATEGORY_DEFAULT_SEVERITY in phase β."""

SeverityTier = Literal["light", "medium", "heavy"]
"""Per spec § 2.3 + § 3 Phase β step 4. HEAVY tweaks are never
surfaced as TweakOptions (filtered at Phase β step 4 final
assignment)."""

RecommendationFlag = Literal["suggested", "optional", "alternative"]
"""Per spec § 2.3 + R5. STRUCTURAL marker, not authoritative ranking.
'suggested' means tweak resolves critical/important ProblemReport
check; NOT 'Claude thinks you should do this'."""

MutationKind = Literal[
    "geometry_local",
    "subset_rerun",
    "finish_schedule_only",
]
"""Per spec § 2.4."""

LayoutArchetype = Literal[
    "cost_efficient",
    "everyday_living",
    "premium_design",
]
"""Per spec § 2.2 + Design Principles v3.1 § 5 Layout Triad."""

TopologyClassification = Literal[
    "no_corridor", "strip", "central_spine", "l_shape", "courtyard",
]
"""Per C5 v1.0 LOCKED + spec § 2.4.2."""

PredictionBasis = Literal[
    "structural_grid_invariant",
    "circulation_pattern_invariant",
    "mutation_local_only",
    "heuristic_strong",
    "heuristic_weak",
]
"""Per spec § 2.4.2. 'heuristic_weak' triggers auto-HEAVY safety bias."""

CompatibilityKind = Literal[
    "spatial_overlap_check",
    "stack_alignment_check",
    "structural_continuity",
    "circulation_reachability",
]
"""Per spec § 2.4.3 + R15."""

CompatibilityResult = Literal["compatible", "conflicts", "ambiguous"]
"""Per spec § 2.4.3."""

DownstreamComponent = Literal[
    "c4", "c5", "c6", "c7", "c8", "c9", "c10",
    "c11a", "c11b", "c12", "c13", "c14", "c15",
]
"""Per spec § 2.4.1. Lex-ASC sorted for replay determinism."""

DownstreamImpact = Literal[
    "circulation_graph",
    "structural_grid",
    "wet_zone_stacks",
    "vertical_alignment",
    "furniture_fit",
    "natural_light",
    "cross_ventilation",
    "problem_report",
    "ranking_score",
    "topology_classification",
    "finish_schedule",
    "door_placement",
]
"""Per spec § 2.4.1. 'topology_classification' impact forces R13
auto-promote to HEAVY."""

MutationClassification = Literal[
    "brief_level_change",
    "topology_level_change",
    "structural_level_change",
    "out_of_v1_scope",
    "constraint_violation",
]
"""Per spec § 2.8."""

SuggestedPathway = Literal[
    "step_back_to_brief",
    "accept_layout_as_is",
    "explore_alternative_layout",
    "defer_to_v2_feature",
]
"""Per spec § 2.8."""

UserAction = Literal[
    "accepted_tweak",
    "rejected_tweak",
    "no_action_continue",
    "finalized_layout_choice",
    "kicked_back_to_c3a",
    "abandoned_session",
]
"""Per spec § 2.5."""

ApplyStatus = Literal[
    "applied_successfully",
    "rerun_queued",
    "rerun_failed",
    "rejected_constraint_violation",
]
"""Per spec § 2.7 ApplyOutcome."""

SessionStatus = Literal[
    "open_for_user_input",
    "awaiting_subset_rerun",
    "resolved_selection_ready",
    "kicked_back_to_c3a",
    "abandoned_no_tweaks",
    "iteration_cap_reached",
]
"""Per spec § 2.1."""

ComfortDimension = Literal[
    "natural_light",
    "cross_ventilation",
    "privacy",
    "noise_isolation",
    "circulation_efficiency",
    "outdoor_connection",
    "storage_capacity",
    "vastu_alignment_opt_in",
    "fire_egress",
    "accessibility",
]
"""Per spec § 2.7 ComfortImpact."""

ComfortDirection = Literal["improves", "worsens", "mixed"]
ComfortMagnitude = Literal["small", "moderate", "significant"]


# ============================================================
# § 2 — TopologyInvarianceResult (R13 support — spec § 2.4.2)
# ============================================================

@dataclass(frozen=True)
class TopologyInvarianceResult:
    """Predicts whether a candidate MEDIUM tweak preserves C5
    topology classification. Attached to every MEDIUM tweak's
    SubsetRerunRequest (per R13).

    v0.6 amendment B3: graded divergence scoring (Optional). When
    populated, allows low-divergence topology changes to stay at
    MEDIUM tier instead of being forced to HEAVY. See severity.py
    promote_severity for the routing logic. When None, falls back
    to v0.5 boolean-only behavior.
    """
    source_topology:        TopologyClassification
    predicted_topology:     TopologyClassification
    invariance_preserved:   bool
    prediction_basis:       PredictionBasis
    advisory_note:          Optional[str] = None
    # v0.6 B3 — graded topology divergence
    topology_divergence_score: Optional[float] = None
    """[0.0, 1.0] — graded divergence between source and predicted
    topology. None when not computed (v0.5 boolean-only fallback)."""
    continuity_subscores: Optional[dict] = None
    """Optional per-dimension scores in [0.0, 1.0] keyed by:
       'circulation', 'structural', 'experiential', 'plumbing'.
       Each score: 1.0 = preserved, 0.0 = broken. None when not computed.
    """

    def __post_init__(self) -> None:
        # Internal consistency: invariance_preserved must match
        # source == predicted
        actual_match = self.source_topology == self.predicted_topology
        if self.invariance_preserved != actual_match:
            raise ValueError(
                f"TopologyInvarianceResult.invariance_preserved="
                f"{self.invariance_preserved} contradicts "
                f"source_topology={self.source_topology!r} vs "
                f"predicted_topology={self.predicted_topology!r}"
            )
        # heuristic_weak with invariance_preserved=True is a contract
        # violation — weak prediction should bias to HEAVY (caller
        # should not have generated this combination)
        if (
            self.prediction_basis == "heuristic_weak"
            and self.invariance_preserved
        ):
            raise ValueError(
                "TopologyInvarianceResult: prediction_basis='heuristic_weak' "
                "with invariance_preserved=True is invalid — weak prediction "
                "must safety-bias to HEAVY (invariance_preserved=False)"
            )
        # Advisory required when invariance broken
        if not self.invariance_preserved and not self.advisory_note:
            raise ValueError(
                "TopologyInvarianceResult: advisory_note required when "
                "invariance_preserved=False (explain why topology would alter)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="TopologyInvarianceResult.advisory_note",
            )
        # v0.6 B3 — divergence score range
        if self.topology_divergence_score is not None:
            if not (0.0 <= self.topology_divergence_score <= 1.0):
                raise ValueError(
                    f"TopologyInvarianceResult.topology_divergence_score must be "
                    f"in [0.0, 1.0]; got {self.topology_divergence_score}"
                )
            # Invariance-preserved sessions should have low divergence
            if self.invariance_preserved and self.topology_divergence_score > 0.0:
                raise ValueError(
                    f"TopologyInvarianceResult: invariance_preserved=True "
                    f"requires topology_divergence_score=0.0 or None; "
                    f"got {self.topology_divergence_score}"
                )
        # v0.6 B3 — continuity subscores
        if self.continuity_subscores is not None:
            if not isinstance(self.continuity_subscores, dict):
                raise ValueError(
                    f"TopologyInvarianceResult.continuity_subscores must be "
                    f"dict or None; got {type(self.continuity_subscores).__name__}"
                )
            expected_keys = {"circulation", "structural", "experiential", "plumbing"}
            actual_keys = set(self.continuity_subscores.keys())
            if not actual_keys.issubset(expected_keys):
                raise ValueError(
                    f"TopologyInvarianceResult.continuity_subscores has unknown "
                    f"keys {actual_keys - expected_keys}; allowed: {expected_keys}"
                )
            for k, v in self.continuity_subscores.items():
                if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                    raise ValueError(
                        f"TopologyInvarianceResult.continuity_subscores[{k!r}] "
                        f"must be in [0.0, 1.0]; got {v}"
                    )


# ============================================================
# § 3 — CompatibilityAssertion (R15 support — spec § 2.4.3)
# ============================================================

# v0.7 C1 — propagation-chain relationship kinds.
# Captures the structural / systemic reason one tweak propagates to
# another system. Closed enum for replay-determinism + audit.
PropagationRelationshipKind = Literal[
    "shares_wet_zone_chase",       # bathroom <-> bathroom (vertical riser)
    "shares_structural_bay",        # any <-> any (column-grid coupling)
    "shares_riser_stack",           # kitchen <-> bathroom (wet stack)
    "shares_load_path",             # column-touching or beam-spanning
    "shares_circulation_node",      # door-adjacent / corridor coupling
    "shares_external_envelope",     # external-wall change propagation
    "shares_vertical_alignment",    # multi-floor stack coupling
]


@dataclass(frozen=True)
class PropagationEdge:
    """v0.7 C1 — one link in a causal propagation chain attached to
    a CompatibilityAssertion.

    Captures: a change to from_system propagates to to_system via
    relationship_kind. Lets the renderer / advisor show users the
    WHY behind a conflict.

    Constraints:
      - from_system, to_system non-empty
      - relationship_kind in PropagationRelationshipKind enum
      - advisory_note R2 lint-clean, ≤ 200 chars
    """
    from_system:        str
    to_system:          str
    relationship_kind:  PropagationRelationshipKind
    advisory_note:      str

    def __post_init__(self) -> None:
        if not self.from_system:
            raise ValueError("PropagationEdge.from_system must be non-empty")
        if not self.to_system:
            raise ValueError("PropagationEdge.to_system must be non-empty")
        if self.from_system == self.to_system:
            raise ValueError(
                f"PropagationEdge.from_system == to_system "
                f"({self.from_system!r}); self-edges are not meaningful "
                f"propagation"
            )
        if not self.advisory_note:
            raise ValueError(
                "PropagationEdge.advisory_note must be non-empty"
            )
        if len(self.advisory_note) > 200:
            raise ValueError(
                f"PropagationEdge.advisory_note exceeds 200-char ceiling; "
                f"got {len(self.advisory_note)} chars"
            )
        lint_advisory_text(
            self.advisory_note,
            field_name="PropagationEdge.advisory_note",
        )


@dataclass(frozen=True)
class CompatibilityAssertion:
    """Asserts compatibility (or conflict) of a new tweak against an
    already-applied tweak earlier in the session.

    Empty `compatibility_assertions` is valid for the first MEDIUM
    tweak applied in a session (no prior tweaks to check).

    v0.7 C1 amendment: propagation_chain Optional field captures the
    causal hops a conflict travels through. When populated, included
    in canonical_replay_signature (genuine state, not advisory).
    """
    against_applied_tweak_id:   str
    compatibility_kind:         CompatibilityKind
    result:                     CompatibilityResult
    advisory_note:              Optional[str] = None
    # v0.7 C1 — causal propagation chain (Optional)
    propagation_chain:          Optional[Tuple[PropagationEdge, ...]] = None

    def __post_init__(self) -> None:
        if not self.against_applied_tweak_id:
            raise ValueError(
                "CompatibilityAssertion.against_applied_tweak_id "
                "must be non-empty"
            )
        # Advisory required when conflict (spec § 2.4.3)
        if self.result == "conflicts" and not self.advisory_note:
            raise ValueError(
                "CompatibilityAssertion: advisory_note required when "
                "result='conflicts' (must explain what conflicts + options)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="CompatibilityAssertion.advisory_note",
            )
        # v0.7 C1 — propagation_chain constraints when populated
        if self.propagation_chain is not None:
            if not isinstance(self.propagation_chain, tuple):
                raise ValueError(
                    f"CompatibilityAssertion.propagation_chain must be "
                    f"tuple or None; got {type(self.propagation_chain).__name__}"
                )
            if len(self.propagation_chain) == 0:
                raise ValueError(
                    "CompatibilityAssertion.propagation_chain must be None "
                    "or non-empty; got empty tuple"
                )
            # All edges must be PropagationEdge instances (frozen dataclass
            # __post_init__ guards their internal validity already)
            for i, edge in enumerate(self.propagation_chain):
                if not isinstance(edge, PropagationEdge):
                    raise ValueError(
                        f"CompatibilityAssertion.propagation_chain[{i}] "
                        f"must be PropagationEdge; got "
                        f"{type(edge).__name__}"
                    )


# ============================================================
# § 4 — SubsetRerunRequest (FORMALIZED v0.2 — spec § 2.4.1)
# ============================================================

@dataclass(frozen=True)
class SubsetRerunRequest:
    """Structured request to an external subset-rerun orchestrator
    (out of scope for C3b itself). Every MEDIUM tweak carries one of
    these inside its ApplySpecification.subset_rerun_payload.

    R13 + R15 enforcement converge here:
      - downstream_impact_set MUST be non-empty (R13/spec § 2.4.1)
      - topology_invariance_check MUST be set (R13)
      - compatibility_assertions MAY be empty (no prior tweaks)
    """
    trigger_tweak_id:        str
    trigger_tweak_category:  TweakCategory

    components_to_rerun:     Tuple[DownstreamComponent, ...]
    """Lex-ASC sorted for replay determinism."""

    downstream_impact_set:   Tuple[DownstreamImpact, ...]
    """Per R13/spec § 2.4.1: MANDATORY non-empty. The static minimum
    impact set per tweak category lives in TWEAK_CATEGORY_IMPACT_TABLE
    (Phase β). Lex-ASC sorted."""

    topology_invariance_check:   TopologyInvarianceResult
    expected_completion_seconds: float
    rerun_anchor:                str
    """Domain-specific constraint preservation, e.g.
    'wet_zone_eastward_with_structural_bay_lock'."""

    compatibility_assertions:    Tuple[CompatibilityAssertion, ...] = ()
    """Per R15. Empty when first MEDIUM tweak in session."""

    def __post_init__(self) -> None:
        if not self.trigger_tweak_id:
            raise ValueError(
                "SubsetRerunRequest.trigger_tweak_id must be non-empty"
            )
        # R13/spec § 2.4.1: downstream_impact_set is MANDATORY non-empty
        if not self.downstream_impact_set:
            raise ValueError(
                "SubsetRerunRequest.downstream_impact_set must be non-empty "
                "(R13 / spec § 2.4.1). Every MEDIUM tweak must declare "
                "what downstream coupling it touches."
            )
        # components_to_rerun also mandatory non-empty
        if not self.components_to_rerun:
            raise ValueError(
                "SubsetRerunRequest.components_to_rerun must be non-empty"
            )
        # Lex-ASC sort enforcement for replay determinism (R6)
        comp_list = list(self.components_to_rerun)
        if comp_list != sorted(comp_list):
            raise ValueError(
                f"SubsetRerunRequest.components_to_rerun must be lex-ASC "
                f"sorted; got {self.components_to_rerun!r}"
            )
        impact_list = list(self.downstream_impact_set)
        if impact_list != sorted(impact_list):
            raise ValueError(
                f"SubsetRerunRequest.downstream_impact_set must be lex-ASC "
                f"sorted; got {self.downstream_impact_set!r}"
            )
        # expected_completion_seconds bounds (per spec § 2.4.1):
        # > 10s requires reclassification — caller must have caught this
        if self.expected_completion_seconds <= 0:
            raise ValueError(
                f"SubsetRerunRequest.expected_completion_seconds must be "
                f"positive; got {self.expected_completion_seconds}"
            )
        if not self.rerun_anchor:
            raise ValueError(
                "SubsetRerunRequest.rerun_anchor must be non-empty"
            )


# ============================================================
# § 5 — KickBackPayload (spec § 2.8 — for brief-level kickback)
# ============================================================

@dataclass(frozen=True)
class KickBackPayload:
    """Structured request when MutationEnvelope.classification ==
    'brief_level_change'. Wraps the data C3a needs to revisit the
    brief.

    This composes with c03a.KickbackContext (the actual cross-component
    message) — KickBackPayload lives INSIDE the MutationEnvelope,
    KickbackContext is what the orchestrator hands to C3a."""
    target_brief_field:      Literal[
        "room_program", "floor_count", "plot_orientation",
        "extreme_case_revisit", "other",
    ]
    target_brief_field_advisory: str
    user_requested_change:   str
    proposed_change_summary: str

    def __post_init__(self) -> None:
        if not self.target_brief_field_advisory:
            raise ValueError(
                "KickBackPayload.target_brief_field_advisory must be non-empty"
            )
        if not self.user_requested_change:
            raise ValueError(
                "KickBackPayload.user_requested_change must be non-empty"
            )
        if not self.proposed_change_summary:
            raise ValueError(
                "KickBackPayload.proposed_change_summary must be non-empty"
            )
        lint_advisory_text(
            self.target_brief_field_advisory,
            field_name="KickBackPayload.target_brief_field_advisory",
        )
        lint_advisory_text(
            self.proposed_change_summary,
            field_name="KickBackPayload.proposed_change_summary",
        )


# ============================================================
# § 6 — MutationEnvelope (NEW v0.2 — spec § 2.8)
# ============================================================

@dataclass(frozen=True)
class MutationEnvelope:
    """When a user-requested change classifies as HEAVY (or implicit
    accumulated requests imply HEAVY), C3b emits a MutationEnvelope
    instead of attempting the mutation. Per Principle 3 (advisory) +
    Principle 4 (user intervention checkpoints).

    v0.5 amendment A6: speculative_preview_text added (Optional).
    Phase β populates with a text description of what the restructured
    layout would look like, so users can decide whether to step back
    to brief or accept the heavy-change pathway.
    """
    envelope_id:              str
    requested_change_summary: str
    classification:           MutationClassification
    why_not_a_tweak:          str
    suggested_pathway:        SuggestedPathway
    estimated_pathway_effort: str
    advisory_note:            str
    kick_back_payload:        Optional[KickBackPayload] = None
    # v0.5 A6 — speculative preview text (Optional)
    speculative_preview_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.envelope_id:
            raise ValueError("MutationEnvelope.envelope_id must be non-empty")
        if not self.requested_change_summary:
            raise ValueError(
                "MutationEnvelope.requested_change_summary must be non-empty"
            )
        # Spec § 2.8: kick_back_payload populated iff classification ==
        # "brief_level_change"
        if (
            self.classification == "brief_level_change"
            and self.kick_back_payload is None
        ):
            raise ValueError(
                "MutationEnvelope: kick_back_payload required when "
                "classification='brief_level_change'"
            )
        if (
            self.classification != "brief_level_change"
            and self.kick_back_payload is not None
        ):
            raise ValueError(
                f"MutationEnvelope: kick_back_payload must be None when "
                f"classification={self.classification!r} (only used for "
                f"'brief_level_change')"
            )
        # Lint all user-facing strings
        for field_name, text in [
            ("why_not_a_tweak",          self.why_not_a_tweak),
            ("estimated_pathway_effort", self.estimated_pathway_effort),
            ("advisory_note",            self.advisory_note),
        ]:
            if not text:
                raise ValueError(
                    f"MutationEnvelope.{field_name} must be non-empty"
                )
            lint_advisory_text(
                text, field_name=f"MutationEnvelope.{field_name}",
            )
        # v0.5 A6 — preview text is optional, but if populated, must lint clean
        if self.speculative_preview_text is not None:
            if not self.speculative_preview_text:
                raise ValueError(
                    "MutationEnvelope.speculative_preview_text must be None "
                    "or non-empty; got empty string"
                )
            lint_advisory_text(
                self.speculative_preview_text,
                field_name="MutationEnvelope.speculative_preview_text",
            )


# ============================================================
# § 7 — Supporting impact types (spec § 2.7)
# ============================================================

@dataclass(frozen=True)
class SpaceImpact:
    """Per-room sqft delta + total delta + advisory. Spec § 2.7."""
    per_room_sqft_delta:    Tuple[Tuple[str, float], ...]
    """(room_id, sqft_delta) — lex-ASC by room_id."""

    total_sqft_delta:       float
    total_carpet_area_after: AttestedValue
    """LOCALLY_DERIVED via Phase γ."""

    advisory_note:          str = ""

    def __post_init__(self) -> None:
        # Lex-ASC sort enforcement (R6)
        rooms_list = list(self.per_room_sqft_delta)
        sorted_rooms = sorted(rooms_list, key=lambda r: r[0])
        if rooms_list != sorted_rooms:
            raise ValueError(
                "SpaceImpact.per_room_sqft_delta must be lex-ASC by room_id"
            )
        # Spec § 6 ceiling: |total_sqft_delta| ≤ TWEAK_SPACE_IMPACT_CEILING
        if abs(self.total_sqft_delta) > TWEAK_SPACE_IMPACT_CEILING_SQFT:
            raise ValueError(
                f"SpaceImpact.total_sqft_delta |{self.total_sqft_delta}| "
                f"exceeds tweak ceiling {TWEAK_SPACE_IMPACT_CEILING_SQFT} "
                f"sqft. A tweak this large is brief-level, not layout-level."
            )
        # Authority discipline (R1)
        if self.total_carpet_area_after.authority != AuthorityKind.LOCALLY_DERIVED:
            raise ValueError(
                f"SpaceImpact.total_carpet_area_after must be "
                f"LOCALLY_DERIVED; got "
                f"{self.total_carpet_area_after.authority}"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note, field_name="SpaceImpact.advisory_note",
            )


@dataclass(frozen=True)
class ComfortImpact:
    """Qualitative comfort impact. Spec § 2.7.

    v0.5 amendment A7: 3 optional emotional-heuristic scores added.
    All Optional[float] in [0.0, 1.0]; default None means heuristic
    didn't fire / wasn't applicable. Used as tie-break signals in
    Phase β priority sort.
    """
    dimensions_affected:    Tuple[ComfortDimension, ...]
    direction:              ComfortDirection
    magnitude:              ComfortMagnitude
    advisory_note:          str = ""
    # v0.5 A7 — emotional layout heuristics (Optional, [0.0, 1.0])
    perceived_spaciousness:    Optional[float] = None
    arrival_impression:        Optional[float] = None
    family_gathering_comfort:  Optional[float] = None

    def __post_init__(self) -> None:
        if not self.dimensions_affected:
            raise ValueError(
                "ComfortImpact.dimensions_affected must be non-empty"
            )
        dims_list = list(self.dimensions_affected)
        if dims_list != sorted(dims_list):
            raise ValueError(
                "ComfortImpact.dimensions_affected must be lex-ASC sorted"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note, field_name="ComfortImpact.advisory_note",
            )
        for name, val in (
            ("perceived_spaciousness", self.perceived_spaciousness),
            ("arrival_impression", self.arrival_impression),
            ("family_gathering_comfort", self.family_gathering_comfort),
        ):
            if val is not None and not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"ComfortImpact.{name}={val} outside [0.0, 1.0]"
                )


# ============================================================
# § 8 — ApplySpecification (spec § 2.4) + payload types
# ============================================================

@dataclass(frozen=True)
class GeometryLocalPayload:
    """For mutation_kind='geometry_local' — LIGHT tweaks applied in-place."""
    new_room_function_assignments: Tuple[Tuple[str, str], ...] = ()
    """(room_id, new_function) for room_swap. Lex-ASC by room_id."""

    new_door_placements_replace:   Tuple[str, ...] = ()
    """door_ids to replace (door_relocate). Lex-ASC."""

    new_window_assignments:        Tuple[Tuple[str, int], ...] = ()
    """(wall_id, new_width_mm). Lex-ASC by wall_id."""

    advisory_note:                 str = ""

    def __post_init__(self) -> None:
        # Lex-ASC sort enforcement (R6)
        if list(self.new_room_function_assignments) != sorted(
            self.new_room_function_assignments, key=lambda x: x[0]
        ):
            raise ValueError(
                "GeometryLocalPayload.new_room_function_assignments "
                "must be lex-ASC by room_id"
            )
        if list(self.new_door_placements_replace) != sorted(
            self.new_door_placements_replace
        ):
            raise ValueError(
                "GeometryLocalPayload.new_door_placements_replace "
                "must be lex-ASC"
            )
        if list(self.new_window_assignments) != sorted(
            self.new_window_assignments, key=lambda x: x[0]
        ):
            raise ValueError(
                "GeometryLocalPayload.new_window_assignments "
                "must be lex-ASC by wall_id"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="GeometryLocalPayload.advisory_note",
            )


@dataclass(frozen=True)
class FinishSchedulePayload:
    """For mutation_kind='finish_schedule_only' — feeds C16 schedule
    update directly."""
    room_finish_overrides: Tuple[Tuple[str, str, str], ...]
    """(room_id, finish_element, new_finish_grade) tuples.
    Lex-ASC by (room_id, finish_element). Non-empty by construction."""

    advisory_note:         str = ""

    def __post_init__(self) -> None:
        if not self.room_finish_overrides:
            raise ValueError(
                "FinishSchedulePayload.room_finish_overrides must be non-empty"
            )
        rfo = list(self.room_finish_overrides)
        if rfo != sorted(rfo, key=lambda t: (t[0], t[1])):
            raise ValueError(
                "FinishSchedulePayload.room_finish_overrides must be lex-ASC "
                "by (room_id, finish_element)"
            )
        if self.advisory_note:
            lint_advisory_text(
                self.advisory_note,
                field_name="FinishSchedulePayload.advisory_note",
            )


@dataclass(frozen=True)
class ApplySpecification:
    """The structured mutation downstream components honor when a
    tweak is accepted. Spec § 2.4 + § 2.4.1 (formalized v0.2).

    R4 enforcement at construction:
      - mutation_kind='geometry_local'      → geometry_local_payload set,
                                                others None
      - mutation_kind='subset_rerun'        → subset_rerun_payload set,
                                                others None
      - mutation_kind='finish_schedule_only' → finish_schedule_payload set,
                                                others None
    """
    mutation_kind:              MutationKind
    geometry_local_payload:     Optional[GeometryLocalPayload] = None
    subset_rerun_payload:       Optional[SubsetRerunRequest] = None
    finish_schedule_payload:    Optional[FinishSchedulePayload] = None

    def __post_init__(self) -> None:
        kinds_set = {
            "geometry_local":       self.geometry_local_payload is not None,
            "subset_rerun":         self.subset_rerun_payload is not None,
            "finish_schedule_only": self.finish_schedule_payload is not None,
        }
        # Exactly one payload field must be set, matching mutation_kind
        n_set = sum(kinds_set.values())
        if n_set != 1:
            raise ValueError(
                f"ApplySpecification: exactly one payload field must be set; "
                f"got {n_set} (mutation_kind={self.mutation_kind!r}, "
                f"set fields: {[k for k, v in kinds_set.items() if v]})"
            )
        if not kinds_set[self.mutation_kind]:
            raise ValueError(
                f"ApplySpecification: mutation_kind={self.mutation_kind!r} "
                f"but corresponding payload field is None"
            )


# ============================================================
# § 9 — CheckProvenance (lightweight version for C3b)
# ============================================================

@dataclass(frozen=True)
class TweakProvenance:
    """Lightweight provenance for tweak generation.
    Per spec § 2.2 — every tweak traces back to which ProblemReport
    check OR which structural grid cell motivated it."""
    motivated_by_check_id:      Optional[str] = None
    motivated_by_grid_cell_id:  Optional[str] = None
    motivated_by_orientation:   Optional[str] = None
    generation_basis:           str = ""

    def __post_init__(self) -> None:
        # At least one motivation source required
        n_motivations = sum([
            self.motivated_by_check_id is not None,
            self.motivated_by_grid_cell_id is not None,
            self.motivated_by_orientation is not None,
        ])
        if n_motivations == 0:
            raise ValueError(
                "TweakProvenance: at least one motivation source required "
                "(check / grid cell / orientation)"
            )
        if not self.generation_basis:
            raise ValueError(
                "TweakProvenance.generation_basis must be non-empty"
            )


# ============================================================
# § 10 — TweakOption (spec § 2.3) — THE central user-facing unit
# ============================================================

@dataclass(frozen=True)
class TweakOption:
    """A single tweak suggestion attached to a layout.

    Enforces at construction:
      R3   layout grounding (affected_room_ids OR affected_grid_cells)
      R4   severity↔mutation_kind discipline
      R5   recommendation_flag is structural (Literal enum)
      R9   layout grounding non-emptiness
      R13  MEDIUM tweaks carry topology_invariance_check via SubsetRerunRequest
      R2   description / advisory text lint
    """
    tweak_id:               str
    tweak_category:         TweakCategory
    severity_tier:          SeverityTier

    affected_room_ids:      Tuple[str, ...]
    affected_grid_cells:    Tuple[str, ...]

    description:            str
    cost_impact:            TransparencyTriple
    space_impact:           SpaceImpact
    comfort_impact:         ComfortImpact

    problem_report_links:   Tuple[str, ...]
    recommendation_flag:    RecommendationFlag

    apply_specification:    ApplySpecification
    provenance:             TweakProvenance

    presented_count:        int = 0
    """How many times this tweak has been surfaced to the user.
    MAX_REPRESENT_COUNT (=2) is the don't-re-suggest ceiling."""

    def __post_init__(self) -> None:
        if not self.tweak_id:
            raise ValueError("TweakOption.tweak_id must be non-empty")

        # R4: severity 'heavy' must NEVER appear here (HEAVY is filtered
        # at Phase β step 4, surfaced via MutationEnvelope instead)
        if self.severity_tier == "heavy":
            raise ValueError(
                "TweakOption.severity_tier='heavy' is invalid — HEAVY tweaks "
                "are filtered at Phase β and surfaced as MutationEnvelope, "
                "not as TweakOptions (R4)"
            )

        # R3 + R9: layout grounding — at least one of room_ids / grid_cells
        if not self.affected_room_ids and not self.affected_grid_cells:
            raise ValueError(
                "TweakOption: at least one of affected_room_ids / "
                "affected_grid_cells must be non-empty (R3 + R9 layout "
                "grounding — every tweak must attach to a building element)"
            )

        # Lex-ASC sort enforcement (R6)
        if list(self.affected_room_ids) != sorted(self.affected_room_ids):
            raise ValueError(
                "TweakOption.affected_room_ids must be lex-ASC sorted"
            )
        if list(self.affected_grid_cells) != sorted(self.affected_grid_cells):
            raise ValueError(
                "TweakOption.affected_grid_cells must be lex-ASC sorted"
            )
        if list(self.problem_report_links) != sorted(self.problem_report_links):
            raise ValueError(
                "TweakOption.problem_report_links must be lex-ASC sorted"
            )

        # R4 severity↔mutation_kind coupling
        if self.severity_tier == "light":
            # LIGHT must use geometry_local or finish_schedule_only
            if self.apply_specification.mutation_kind == "subset_rerun":
                raise ValueError(
                    "TweakOption: severity_tier='light' cannot use "
                    "mutation_kind='subset_rerun' (R4 — LIGHT tweaks "
                    "never trigger pipeline rerun)"
                )
        elif self.severity_tier == "medium":
            # MEDIUM must use subset_rerun
            if self.apply_specification.mutation_kind != "subset_rerun":
                raise ValueError(
                    f"TweakOption: severity_tier='medium' must use "
                    f"mutation_kind='subset_rerun'; got "
                    f"{self.apply_specification.mutation_kind!r} (R4)"
                )
            # R13: MEDIUM must carry topology_invariance_check; if
            # invariance not preserved, severity should have been HEAVY
            srr = self.apply_specification.subset_rerun_payload
            assert srr is not None  # mutation_kind discipline guarantees this
            if not srr.topology_invariance_check.invariance_preserved:
                raise ValueError(
                    "TweakOption: severity_tier='medium' with "
                    "topology_invariance_check.invariance_preserved=False "
                    "is invalid — R13 mandates auto-promote to HEAVY when "
                    "topology would change"
                )

        # presented_count discipline
        if self.presented_count < 0:
            raise ValueError(
                f"TweakOption.presented_count must be >= 0; "
                f"got {self.presented_count}"
            )
        if self.presented_count > MAX_REPRESENT_COUNT:
            raise ValueError(
                f"TweakOption.presented_count={self.presented_count} "
                f"exceeds MAX_REPRESENT_COUNT={MAX_REPRESENT_COUNT} "
                f"(don't re-suggest a rejected tweak more than twice)"
            )

        # Cost-impact ceiling (spec § 6)
        if abs(self.cost_impact.exact_value) > TWEAK_COST_IMPACT_CEILING_INR:
            raise ValueError(
                f"TweakOption.cost_impact.exact_value "
                f"|₹{self.cost_impact.exact_value:,.0f}| exceeds tweak "
                f"ceiling ₹{TWEAK_COST_IMPACT_CEILING_INR:,.0f}. A tweak "
                f"this expensive is brief-level work, not a layout tweak."
            )

        # R2: lint user-facing text
        if not self.description:
            raise ValueError("TweakOption.description must be non-empty")
        lint_advisory_text(
            self.description, field_name="TweakOption.description",
        )


# ============================================================
# § 11 — TweakOptionSet (spec § 2.2)
# ============================================================

@dataclass(frozen=True)
class TweakOptionSet:
    """Per-layout tweak suggestions. Spec § 2.2.

    Hard ceiling: TWEAKS_PER_LAYOUT_HARD_CEILING (=8). The soft target
    is MAX_TWEAKS_PER_LAYOUT (=6). Exceeding the hard ceiling raises;
    exceeding the soft target should have been bounded at Phase β."""
    layout_id:                  str
    layout_archetype:           LayoutArchetype
    source_problem_report_id:   str

    tweaks:                     Tuple[TweakOption, ...]
    """3-6 typical, hard ceiling 8. lex-ASC by tweak_id."""

    overall_advisory_note:      str

    def __post_init__(self) -> None:
        if not self.layout_id:
            raise ValueError("TweakOptionSet.layout_id must be non-empty")
        if not self.source_problem_report_id:
            raise ValueError(
                "TweakOptionSet.source_problem_report_id must be non-empty"
            )

        # Hard ceiling (spec § 6)
        if len(self.tweaks) > TWEAKS_PER_LAYOUT_HARD_CEILING:
            raise ValueError(
                f"TweakOptionSet: {len(self.tweaks)} tweaks exceeds hard "
                f"ceiling {TWEAKS_PER_LAYOUT_HARD_CEILING} for layout "
                f"{self.layout_id!r}"
            )

        # Lex-ASC by tweak_id (R6)
        tweak_ids = [t.tweak_id for t in self.tweaks]
        if tweak_ids != sorted(tweak_ids):
            raise ValueError(
                f"TweakOptionSet.tweaks must be lex-ASC sorted by "
                f"tweak_id; got {tweak_ids!r}"
            )

        # Unique tweak_ids within the set
        if len(set(tweak_ids)) != len(tweak_ids):
            raise ValueError(
                f"TweakOptionSet.tweaks: duplicate tweak_ids in layout "
                f"{self.layout_id!r}"
            )

        # R2 lint
        if not self.overall_advisory_note:
            raise ValueError(
                "TweakOptionSet.overall_advisory_note must be non-empty"
            )
        lint_advisory_text(
            self.overall_advisory_note,
            field_name="TweakOptionSet.overall_advisory_note",
        )


# ============================================================
# § 12 — ApplyOutcome (spec § 2.7)
# ============================================================

@dataclass(frozen=True)
class ApplyOutcome:
    """Result of applying an accepted tweak. Spec § 2.7."""
    apply_status:            ApplyStatus
    error_summary:           Optional[str] = None
    new_layout_signature:    Optional[str] = None
    new_problem_report_id:   Optional[str] = None
    regression_detected:     bool = False
    """R14 — set True when post-rerun ProblemReport has more
    severity='critical' checks than pre-rerun."""

    newly_critical_check_ids: Tuple[str, ...] = ()
    """R14 — listing of the specific checks newly classified critical.
    Empty when regression_detected=False."""

    def __post_init__(self) -> None:
        # Lex-ASC sort (R6)
        if list(self.newly_critical_check_ids) != sorted(
            self.newly_critical_check_ids
        ):
            raise ValueError(
                "ApplyOutcome.newly_critical_check_ids must be lex-ASC sorted"
            )
        # Consistency: regression_detected ↔ non-empty newly_critical
        if self.regression_detected and not self.newly_critical_check_ids:
            raise ValueError(
                "ApplyOutcome: regression_detected=True requires "
                "newly_critical_check_ids to be non-empty (R14)"
            )
        if not self.regression_detected and self.newly_critical_check_ids:
            raise ValueError(
                "ApplyOutcome: newly_critical_check_ids must be empty "
                "when regression_detected=False"
            )
        # Failure status must carry an error_summary
        if self.apply_status == "rerun_failed" and not self.error_summary:
            raise ValueError(
                "ApplyOutcome.error_summary required when "
                "apply_status='rerun_failed'"
            )


# ============================================================
# § 13 — SessionTurn (audit log unit — spec § 2.5)
# ============================================================

@dataclass(frozen=True)
class SessionTurn:
    """One turn of the negotiation session. Append-only.

    R12: every turn records the FULL presented_tweaks set the user saw,
    not just the chosen one. Audit trail is reproducible.

    R7d (no-time inheritance): timestamp_offset_ms is RELATIVE to
    session_id creation, not absolute wall-clock time. Replay-safe.

    v0.5 amendment A4: strategic_advisory_text added (Optional).
    Populated only when C3bRuntimeConfig.strategic_mode != "off".
    R17 invariant: this field MUST NOT be included in
    canonical_replay_signature input (see cache_keys.py).
    """
    turn_id:                 str
    iteration_index:         int
    timestamp_offset_ms:     int
    presented_tweaks:        Tuple[str, ...]
    """All tweak_ids the user could choose from. Lex-ASC sorted (R6)."""

    user_action:             UserAction
    chosen_tweak_id:         Optional[str] = None
    apply_outcome:           Optional[ApplyOutcome] = None
    post_turn_status:        SessionStatus = "open_for_user_input"
    # v0.5 A4 — strategic advisory text (Optional). When populated, must
    # NOT affect canonical_replay_signature (R17).
    strategic_advisory_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.turn_id:
            raise ValueError("SessionTurn.turn_id must be non-empty")
        if self.iteration_index < 0:
            raise ValueError(
                f"SessionTurn.iteration_index must be >= 0; "
                f"got {self.iteration_index}"
            )
        if self.timestamp_offset_ms < 0:
            raise ValueError(
                f"SessionTurn.timestamp_offset_ms must be >= 0 "
                f"(relative to session creation); got {self.timestamp_offset_ms}"
            )

        # Lex-ASC sort (R6) — R12 audit-trail discipline
        if list(self.presented_tweaks) != sorted(self.presented_tweaks):
            raise ValueError(
                "SessionTurn.presented_tweaks must be lex-ASC sorted"
            )

        # Q3 Level B invariant: chosen must be in presented (if any)
        if self.chosen_tweak_id is not None:
            if self.chosen_tweak_id not in self.presented_tweaks:
                raise ValueError(
                    f"SessionTurn.chosen_tweak_id={self.chosen_tweak_id!r} "
                    f"not in presented_tweaks={self.presented_tweaks!r} "
                    f"(Q3 Level B logging discipline)"
                )

        # user_action ↔ chosen_tweak_id coherence
        action_needs_choice = {"accepted_tweak", "rejected_tweak"}
        if self.user_action in action_needs_choice and self.chosen_tweak_id is None:
            raise ValueError(
                f"SessionTurn: user_action={self.user_action!r} requires "
                f"chosen_tweak_id (must reference what was accepted/rejected)"
            )
        if self.user_action not in action_needs_choice and self.chosen_tweak_id is not None:
            raise ValueError(
                f"SessionTurn: chosen_tweak_id must be None for "
                f"user_action={self.user_action!r}"
            )

        # apply_outcome ↔ user_action coherence
        if self.user_action == "accepted_tweak" and self.apply_outcome is None:
            raise ValueError(
                "SessionTurn: user_action='accepted_tweak' requires apply_outcome"
            )
        if self.user_action != "accepted_tweak" and self.apply_outcome is not None:
            raise ValueError(
                f"SessionTurn: apply_outcome must be None for "
                f"user_action={self.user_action!r}"
            )

        # v0.5 A4 — strategic advisory text must lint clean if populated
        if self.strategic_advisory_text is not None:
            if not self.strategic_advisory_text:
                raise ValueError(
                    "SessionTurn.strategic_advisory_text must be None or "
                    "non-empty; got empty string"
                )
            lint_advisory_text(
                self.strategic_advisory_text,
                field_name="SessionTurn.strategic_advisory_text",
            )


# ============================================================
# § 14 — ResolvedSelection (spec § 2.6)
# ============================================================

@dataclass(frozen=True)
class ResolvedSelection:
    """Final output to C16. Spec § 2.6."""
    chosen_layout_id:          str
    chosen_layout_archetype:   LayoutArchetype
    applied_tweaks:            Tuple[str, ...]
    final_layout_signature:    str
    final_problem_report_id:   Optional[str] = None
    total_cost_delta:          Optional[TransparencyTriple] = None
    total_space_delta:         Optional[SpaceImpact] = None
    final_handoff_advisory:    str = ""

    def __post_init__(self) -> None:
        if not self.chosen_layout_id:
            raise ValueError(
                "ResolvedSelection.chosen_layout_id must be non-empty"
            )
        if not self.final_layout_signature:
            raise ValueError(
                "ResolvedSelection.final_layout_signature must be non-empty"
            )
        # Lex-ASC sort (R6)
        if list(self.applied_tweaks) != sorted(self.applied_tweaks):
            raise ValueError(
                "ResolvedSelection.applied_tweaks must be lex-ASC sorted"
            )
        if not self.final_handoff_advisory:
            raise ValueError(
                "ResolvedSelection.final_handoff_advisory must be non-empty"
            )
        lint_advisory_text(
            self.final_handoff_advisory,
            field_name="ResolvedSelection.final_handoff_advisory",
        )


# ============================================================
# § 15 — AdvisoryFlag (lightweight, C3b-local)
# ============================================================

AdvisoryFlagKind = Literal[
    "regression_after_apply",        # R14
    "compatibility_ambiguous",        # R15 ambiguous (not conflict)
    "iteration_cap_warning_nudge",    # approaching cap
    "topology_invariance_weak_basis", # heuristic_weak — promoted to HEAVY
    "pareto_diversity_floor_borderline",
    # v0.5 A2 — periodic full-coherence recheck
    "full_coherence_recheck_triggered",
    # v0.5 A3 — oscillation pattern detection
    "oscillation_pattern_detected",
    # v0.5 A5 — continuous dimension delta regression (numeric, sub-CRITICAL)
    "dimension_score_regression",
]


@dataclass(frozen=True)
class AdvisoryFlag:
    """Surface-level advisory attached to a TradeoffSession.
    Lightweight; C3b doesn't need C16's full AdvisoryFlag surface."""
    flag_id:        str
    kind:           AdvisoryFlagKind
    advisory_note:  str
    related_ids:    Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.flag_id:
            raise ValueError("AdvisoryFlag.flag_id must be non-empty")
        if not self.advisory_note:
            raise ValueError("AdvisoryFlag.advisory_note must be non-empty")
        if list(self.related_ids) != sorted(self.related_ids):
            raise ValueError(
                "AdvisoryFlag.related_ids must be lex-ASC sorted"
            )
        lint_advisory_text(
            self.advisory_note, field_name="AdvisoryFlag.advisory_note",
        )


# ============================================================
# § 16 — TradeoffSession (the top-level container — spec § 2.1)
# ============================================================

@dataclass(frozen=True)
class TradeoffSession:
    """The full negotiation session state.

    Per spec § 2.1 v0.2 clarifying note + R16:
      session_history is append-only single-linear-history in v1.0.
      Multi-branch / parallel-universe / multi-user is v1.x.

    Per R8: c3b_schema_version must match C3B_SESSION_SCHEMA_VERSION.
    """
    session_id:                     str
    source_selection_result_id:     str
    source_brief_signature:         str
    source_plot_analysis_id:        str
    c3b_version:                    str
    c3b_schema_version:             int
    jurisdiction_profile_id:        str

    tweak_option_sets:              Tuple[TweakOptionSet, ...]
    session_history:                Tuple[SessionTurn, ...]
    iteration_count:                int
    iteration_cap:                  int
    current_status:                 SessionStatus

    canonical_replay_signature:     str
    presentation_signature:         str
    schema_descriptor_digest:       str

    resolved_selection:             Optional[ResolvedSelection] = None
    advisory_flags:                 Tuple[AdvisoryFlag, ...] = ()
    mutation_envelopes:             Tuple[MutationEnvelope, ...] = ()
    """HEAVY tweaks generated during Phase β that got buffered for
    later use (e.g., user later asks something matching the pattern)."""

    # v0.5 A2 — periodic full-coherence recheck counter. Increments on
    # each MEDIUM tweak applied; resets on resolution. When crosses
    # full_recompute_threshold, the next subset_rerun is escalated to
    # a full recompute and a "full_coherence_recheck_triggered"
    # advisory is emitted.
    medium_tweak_count_since_full_recompute: int = 0

    # v0.6 B1 — extension metadata channel. Dict-of-strings for
    # research / experimental modules. R19: this field MUST NOT be
    # included in canonical_replay_signature (excluded in cache_keys).
    # Constraints (enforced in __post_init__):
    #   - ≤ 32 keys
    #   - each value ≤ 2048 chars
    #   - all keys + values lint-clean per R2 advisory_lint
    extension_metadata: Optional[dict] = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("TradeoffSession.session_id must be non-empty")
        if not self.source_selection_result_id:
            raise ValueError(
                "TradeoffSession.source_selection_result_id must be non-empty"
            )

        # R8 schema-version pin
        if self.c3b_schema_version != C3B_SESSION_SCHEMA_VERSION:
            raise ValueError(
                f"TradeoffSession.c3b_schema_version={self.c3b_schema_version} "
                f"!= C3B_SESSION_SCHEMA_VERSION={C3B_SESSION_SCHEMA_VERSION} "
                f"(R8 schema-version pin)"
            )

        # Version string pin
        if not self.c3b_version.startswith("v"):
            raise ValueError(
                f"TradeoffSession.c3b_version must look like 'vX.Y.Z'; "
                f"got {self.c3b_version!r}"
            )

        # iteration discipline
        if self.iteration_count < 0:
            raise ValueError(
                f"TradeoffSession.iteration_count must be >= 0; "
                f"got {self.iteration_count}"
            )
        if not (1 <= self.iteration_cap <= ITERATION_CAP_HARD_CEILING):
            raise ValueError(
                f"TradeoffSession.iteration_cap must be in [1, "
                f"{ITERATION_CAP_HARD_CEILING}]; got {self.iteration_cap}"
            )

        # v0.5 A2 — full-recompute counter discipline
        if self.medium_tweak_count_since_full_recompute < 0:
            raise ValueError(
                f"TradeoffSession.medium_tweak_count_since_full_recompute "
                f"must be >= 0; got {self.medium_tweak_count_since_full_recompute}"
            )

        # v0.5 R18 — counter resets on terminal resolution
        if self.current_status in (
            "resolved_selection_ready",
            "abandoned_no_tweaks",
            "kicked_back_to_c3a",
        ) and self.medium_tweak_count_since_full_recompute != 0:
            raise ValueError(
                f"TradeoffSession R18 invariant violated: "
                f"medium_tweak_count_since_full_recompute="
                f"{self.medium_tweak_count_since_full_recompute} must be 0 "
                f"when current_status={self.current_status!r}"
            )

        # session_history hard ceiling
        if len(self.session_history) > SESSION_HISTORY_HARD_CEILING:
            raise ValueError(
                f"TradeoffSession.session_history exceeds hard ceiling "
                f"{SESSION_HISTORY_HARD_CEILING}; got {len(self.session_history)}"
            )

        # v0.6 B1 — extension_metadata constraints
        if self.extension_metadata is not None:
            if not isinstance(self.extension_metadata, dict):
                raise ValueError(
                    f"TradeoffSession.extension_metadata must be dict or None; "
                    f"got {type(self.extension_metadata).__name__}"
                )
            if len(self.extension_metadata) > 32:
                raise ValueError(
                    f"TradeoffSession.extension_metadata exceeds 32-key ceiling; "
                    f"got {len(self.extension_metadata)} keys"
                )
            for k, v in self.extension_metadata.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError(
                        f"TradeoffSession.extension_metadata must be dict[str, str]; "
                        f"got key {type(k).__name__}={k!r}, "
                        f"value {type(v).__name__}={v!r}"
                    )
                if len(v) > 2048:
                    raise ValueError(
                        f"TradeoffSession.extension_metadata[{k!r}] value exceeds "
                        f"2048-char ceiling; got {len(v)} chars"
                    )
                # R2 advisory_lint discipline on both keys and values.
                # Conservative: use HARD_BLOCK tier only (B2 tiers don't
                # apply here — extension metadata is for machine readers).
                lint_advisory_text(
                    k, field_name=f"TradeoffSession.extension_metadata key {k!r}",
                )
                lint_advisory_text(
                    v, field_name=f"TradeoffSession.extension_metadata[{k!r}]",
                )

        # R16: session_history is append-only by iteration_index
        # (lex-ascending — incrementing turn order)
        for i, turn in enumerate(self.session_history):
            if turn.iteration_index != i:
                # Allow gaps for rejected/no_action turns that don't
                # increment iteration_count — but iteration_index of
                # each turn must equal its position in history
                # (single-linear-history discipline)
                raise ValueError(
                    f"TradeoffSession.session_history[{i}].iteration_index "
                    f"={turn.iteration_index} != position {i} "
                    f"(R16 single-linear-history discipline)"
                )

        # tweak_option_sets lex-ASC by layout_id
        layout_ids = [s.layout_id for s in self.tweak_option_sets]
        if layout_ids != sorted(layout_ids):
            raise ValueError(
                "TradeoffSession.tweak_option_sets must be lex-ASC by "
                "layout_id"
            )

        # current_status ↔ resolved_selection coherence
        if (
            self.current_status == "resolved_selection_ready"
            and self.resolved_selection is None
        ):
            raise ValueError(
                "TradeoffSession: current_status='resolved_selection_ready' "
                "requires resolved_selection to be populated"
            )

        # advisory_flags lex-ASC by flag_id (R6)
        flag_ids = [f.flag_id for f in self.advisory_flags]
        if flag_ids != sorted(flag_ids):
            raise ValueError(
                "TradeoffSession.advisory_flags must be lex-ASC by flag_id"
            )

        # mutation_envelopes lex-ASC by envelope_id (R6)
        envelope_ids = [e.envelope_id for e in self.mutation_envelopes]
        if envelope_ids != sorted(envelope_ids):
            raise ValueError(
                "TradeoffSession.mutation_envelopes must be lex-ASC by "
                "envelope_id"
            )


# ============================================================
# § 17 — Public surface
# ============================================================

SCHEMA_MODULE_VERSION: Final[str] = "v0.4.LOCKED.s52"


__all__ = [
    # Enums (Literals exported for type annotations)
    "TweakCategory", "SeverityTier", "RecommendationFlag",
    "MutationKind", "LayoutArchetype", "TopologyClassification",
    "PredictionBasis", "CompatibilityKind", "CompatibilityResult",
    "DownstreamComponent", "DownstreamImpact",
    "MutationClassification", "SuggestedPathway",
    "UserAction", "ApplyStatus", "SessionStatus",
    "ComfortDimension", "ComfortDirection", "ComfortMagnitude",
    "AdvisoryFlagKind",
    # Output dataclasses
    "TopologyInvarianceResult",
    "CompatibilityAssertion",
    "PropagationEdge", "PropagationRelationshipKind",
    "SubsetRerunRequest",
    "KickBackPayload",
    "MutationEnvelope",
    "SpaceImpact", "ComfortImpact",
    "GeometryLocalPayload", "FinishSchedulePayload",
    "ApplySpecification",
    "TweakProvenance",
    "TweakOption", "TweakOptionSet",
    "ApplyOutcome",
    "SessionTurn",
    "ResolvedSelection",
    "AdvisoryFlag",
    "TradeoffSession",
    # Marker
    "SCHEMA_MODULE_VERSION",
]
