"""
BuildemUp — Component 11a: Topology Mutation Layer — schema
============================================================

This module defines all enums, frozen dataclasses, and value objects for
C11a per SPEC v1.0 LOCKED (see 02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md
in the project handoff bundles).

**Sub-session 1 scope**: schema only. No logic. The runtime entry point
``mutate_topologies()`` and per-operator implementations land at
Sub-session 2+.

Spec pointer map (from CODING_MANDATE_C11A_C11B.md):
- Operator enum / tier / family   → § 2.1, § 2.2
- Family transition policy table  → § 2.2 (_OPERATOR_FAMILY_POLICY)
- Per-operator delta schemas      → § 2.5 (DeltaKey + OperatorExpectedDeltaSchema)
- Atomicity-by-construction       → § 0.1 (purity contract — see provenance.py)
- Tier B caching                  → § 0.3 (DeepMutationCacheKey — Sub-session 3)
- Pending-predicate sunset        → § 0.2 (UpstreamAmendmentWaiver — see this file)
- Quarantine fingerprint          → § 2.9
- Cache-relevant metadata         → § 2.5 (Inv 26)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, ClassVar, Final, Literal, Mapping, Optional


# =============================================================================
# § 2.1 — Operator enum (16 entries across 9 families)
# =============================================================================

# Type imports use string-quoted "Enum" to avoid forward-reference issues
# in tooling that reads dataclass annotations early.
import enum


class MutationOperator(str, enum.Enum):
    """C11a v1.0 SPEC § 2.1 — 16 base operators across 9 families.

    Operator names are stable string identifiers; `topology_variant_id`
    and provenance hashes depend on them, so they MUST NOT be renamed
    without bumping a major C11a version.
    """
    M0_BASE         = "m0_base"
    M1_HORIZ_FLIP   = "m1_horiz_flip"
    M2_VERT_FLIP    = "m2_vert_flip"
    M3A_STAIR_EAST  = "m3a_stair_east"
    M3B_STAIR_WEST  = "m3b_stair_west"
    M3C_STAIR_NE    = "m3c_stair_ne_corner"
    M4_CORRIDOR_INV = "m4_corridor_inv"
    M5_ZONE_SWAP    = "m5_public_private_swap"
    M6_WET_ROTATE   = "m6_wet_wall_rotate"
    M7A_GRID_3_3    = "m7a_grid_scale_3_3"
    M7B_GRID_2_7    = "m7b_grid_scale_2_7"
    M8_VERT_REARR   = "m8_master_floor_swap"
    M9A_ENTRY_CTR   = "m9a_entry_ne_center"
    M9B_ENTRY_W     = "m9b_entry_ne_corner_w"
    M9C_ENTRY_E     = "m9c_entry_ne_corner_e"
    M9D_ENTRY_OFF   = "m9d_entry_offset_ne"


# =============================================================================
# § 2.1 — Tier / Family / Family-transition policy enums
# =============================================================================


class MutationTier(str, enum.Enum):
    """SPEC § 2.1. Two-tier mutation architecture (v0.2 critique #1, #2).

    SHALLOW: operator-local, fast — runs without re-running upstream
        components. Per-operator mutator function takes the source
        topology and returns a mutated topology directly.
    REGENERATIVE: triggers DeepMutationPipeline — re-runs C9/C10 (and
        possibly C7/C8 for grid-scale operators like M7) with mutated
        inputs.
    """
    SHALLOW       = "shallow"
    REGENERATIVE  = "regenerative"


class MutationOperatorFamily(str, enum.Enum):
    """SPEC § 2.1. For per-family slot allocation (v0.2 critique #8)."""
    BASE      = "base"           # M0
    FLIP      = "flip"           # M1, M2
    STAIRCASE = "staircase"      # M3a/b/c
    CORRIDOR  = "corridor"       # M4
    ZONE      = "zone"           # M5
    WET_WALL  = "wet_wall"       # M6
    GRID      = "grid"           # M7a/b
    VERTICAL  = "vertical"       # M8
    ENTRY     = "entry"          # M9a-d


class TopologyFamilyTransitionPolicy(str, enum.Enum):
    """SPEC § 2.2. Whether an operator preserves the topology's source
    family (e.g., LinearSpine remains LinearSpine after M1 horizontal
    flip), transforms it (M4 corridor inversion converts spine→strip),
    or invalidates it (M5 zone swap on Courtyard topology breaks the
    courtyard family signature).
    """
    PRESERVES_FAMILY    = "preserves_family"
    TRANSFORMS_FAMILY   = "transforms_family"
    INVALIDATES_FAMILY  = "invalidates_family"


# =============================================================================
# § 2.2 — Per-operator family-transition policy table (v1.0 LOCKED Walk #5)
# =============================================================================
#
# Each operator's policy decides how output-family classification is
# computed downstream. M4 + M5 are TRANSFORMS_FAMILY per W#5 Q22
# adjudication ("M4 corridor inversion is TRANSFORMS, not INVALIDATES,
# because the room-graph is preserved").

_OPERATOR_FAMILY_POLICY: Final[Mapping[
    MutationOperator, TopologyFamilyTransitionPolicy,
]] = {
    MutationOperator.M0_BASE:         TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M1_HORIZ_FLIP:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M2_VERT_FLIP:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3A_STAIR_EAST:  TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3B_STAIR_WEST:  TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M3C_STAIR_NE:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M4_CORRIDOR_INV: TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
    MutationOperator.M5_ZONE_SWAP:    TopologyFamilyTransitionPolicy.TRANSFORMS_FAMILY,
    MutationOperator.M6_WET_ROTATE:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M7A_GRID_3_3:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M7B_GRID_2_7:    TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M8_VERT_REARR:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9A_ENTRY_CTR:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9B_ENTRY_W:     TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9C_ENTRY_E:     TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
    MutationOperator.M9D_ENTRY_OFF:   TopologyFamilyTransitionPolicy.PRESERVES_FAMILY,
}


# =============================================================================
# § 2.5 — DeltaKey enum (NEW v0.5 — canonical vocabulary, resolves critique #3)
# =============================================================================


class DeltaKey(str, enum.Enum):
    """SPEC § 2.5 v0.5 — canonical vocabulary for upstream-regeneration
    deltas. Hierarchical-namespace prevents semantic drift.

    Inv 28 (v0.5): every key in any OperatorExpectedDeltaSchema set
    MUST be a DeltaKey enum value; string literals raise
    OperatorRegistryError at startup.

    META_* keys are deliberately enum members but MUST NOT appear as
    expected/allowed deltas of any operator — they only appear in
    `forbidden_keys` to express cross-operator invariants ("no operator
    may change room count").
    """
    # geometry domain
    GEO_ROOM_AREA           = "geometry.room.area"
    GEO_ROOM_POSITION_X     = "geometry.room.position_x"
    GEO_ROOM_POSITION_Y     = "geometry.room.position_y"
    GEO_GRID_BAY_SIZE       = "geometry.grid.bay_size"
    GEO_STAIRCASE_POSITION  = "geometry.staircase.position"
    GEO_ENTRY_POSITION      = "geometry.entry.position"

    # adjacency domain
    ADJ_EDGES               = "adjacency.edges"
    ADJ_EDGES_ORIENTATION   = "adjacency.edges_orientation"

    # circulation domain
    CIRC_CORRIDOR_TOPOLOGY  = "circulation.corridor.topology"
    CIRC_PRIMARY_PATH       = "circulation.primary_path"
    CIRC_CORRIDOR_ROUTING   = "circulation.corridor.routing"

    # zoning domain
    ZONE_ASSIGNMENTS        = "zoning.assignments"
    ZONE_PRIVACY_PATTERN    = "zoning.privacy_pattern"

    # plumbing domain
    PLUMB_WET_WALL_ASSIGNMENT = "plumbing.wet_wall.assignment"
    PLUMB_TRAP_ARM_DISTANCES  = "plumbing.trap_arm.distances"
    PLUMB_RISER_GROUPS        = "plumbing.riser_groups"

    # multi-floor domain
    MULTI_MASTER_BR_FLOOR     = "multifloor.master_bedroom.floor"
    MULTI_FLOOR_ASSIGNMENT    = "multifloor.floor_assignment"

    # meta domain — used only in forbidden_keys per the docstring above.
    META_FIXTURE_TYPES        = "meta.fixture_types"
    META_ROOM_COUNT           = "meta.room_count"


# =============================================================================
# § 2.5 — OperatorExpectedDeltaSchema
# =============================================================================


@dataclass(frozen=True)
class OperatorExpectedDeltaSchema:
    """SPEC § 2.5 — declared upstream-delta scope per operator.

    `expected`: keys an operator's mutation IS expected to drive
    regeneration of (e.g., M1 expects GEO_ROOM_POSITION_X).
    `allowed_secondary`: keys whose change is ACCEPTABLE as a side
    effect (e.g., M1 may incidentally flip ADJ_EDGES_ORIENTATION).
    `forbidden`: keys that, if changed by an operator's deep
    regeneration, MUST cause the candidate to be rejected — these
    encode cross-operator invariants like "no operator changes room
    count" or "no operator changes fixture-type set".

    Inv 23 (v0.4): MutationLineageDepth classifier reads this schema
    to decide REGENERATIVE_TRANSFORM vs EMERGENT_REGENERATION vs
    REJECT.
    """
    expected: frozenset[DeltaKey]
    allowed_secondary: frozenset[DeltaKey]
    forbidden: frozenset[DeltaKey]


# =============================================================================
# § 2.2 — MutationOperatorMetadata
# =============================================================================


@dataclass(frozen=True)
class MutationOperatorMetadata:
    """SPEC § 2.2. Per-operator metadata registered in OPERATOR_METADATA.

    Sub-session 1 ships this dataclass and the registry constant; the
    full OPERATOR_METADATA table (with concrete delta schemas per
    operator per § 2.2 v0.5 table) lands at Sub-session 2 once
    operator implementations exist to validate against.
    """
    operator: MutationOperator
    tier: MutationTier
    family: MutationOperatorFamily
    family_transition_policy: TopologyFamilyTransitionPolicy
    requires_multi_floor: bool             # M8 only
    requires_grid_regen: bool              # M7 only
    expected_delta_schema: OperatorExpectedDeltaSchema    # § 2.2 v0.4
    cache_relevant_config_fields: tuple[str, ...]         # § 2.2 v0.4 critique #4


# =============================================================================
# § 2.3 — MutationLineageDepth + classifier (carried v0.3)
# =============================================================================


class MutationLineageDepth(str, enum.Enum):
    """SPEC § 2.3 v0.3 — tracks how far the output state has diverged
    from the source.

    SHALLOW_TRANSFORM: Tier A operator; same upstream state.
    REGENERATIVE_TRANSFORM: Tier B; upstream re-run, but operator-driven
        (delta ⊆ expected ∪ allowed_secondary).
    EMERGENT_REGENERATION: Tier B; upstream re-run produced effects
        BEYOND operator intent (delta exceeded expected ∪ allowed).
    """
    SHALLOW_TRANSFORM      = "shallow_transform"
    REGENERATIVE_TRANSFORM = "regenerative_transform"
    EMERGENT_REGENERATION  = "emergent_regeneration"


# =============================================================================
# § 2.7 — Severity tier audit (NEW v0.5 — F-v4-5 / critique #6)
# =============================================================================
# Inverts hardcoded exception lists. Each upstream error class declares
# its own severity tier (per B-NEW-P v1.0 LOCKED, S38). This module
# only declares the Literal type used for declared severity values;
# the audit function `validate_severity_classification_audit()` lives in
# the orchestrator (Sub-session 4).

_SeverityTier = Literal["per_candidate", "batch", "systemic"]


# =============================================================================
# § 0.1 — PurityAttestation + UPSTREAM_PURITY_REGISTRY (carried v0.4)
# =============================================================================


@dataclass(frozen=True)
class PurityAttestation:
    """SPEC § 0.1. A declaration that an upstream entry point is
    side-effect free for the purposes of C11a Tier B regeneration.

    Three purity classes:
      - "pure": no observable side effects on inputs or globals
      - "read_only_cache": reads from process-global cache; never
        writes during call (e.g., a memoized table)
      - "lazy_init_once": first call may set a process-global;
        subsequent calls pure (e.g., C10's _KB_VALIDATED flag)
    """
    component_id: str               # e.g., "C7" / "C9" / "C10"
    entry_point: str                # e.g., "GridGenerator.generate"
    purity_class: Literal[
        "pure",
        "read_only_cache",
        "lazy_init_once",
    ]
    attested_by: str                # owner component name; identifies signer
    attested_at_kb_version: str     # binds attestation to a specific upstream version


UPSTREAM_PURITY_REGISTRY: Final[tuple[PurityAttestation, ...]] = (
    PurityAttestation(
        component_id="C7",
        entry_point="GridGenerator.generate",
        purity_class="pure",
        attested_by="C7",
        attested_at_kb_version="v0.7.3+amend_v0.8",
    ),
    PurityAttestation(
        component_id="C9",
        entry_point="size_rooms",
        purity_class="pure",
        attested_by="C9",
        attested_at_kb_version="v0.1+S34",
    ),
    PurityAttestation(
        component_id="C10",
        entry_point="plan_wet_zones",
        purity_class="lazy_init_once",
        attested_by="C10",
        attested_at_kb_version="v1.0_S36",
    ),
    # C10's _KB_VALIDATED global qualifies as lazy_init_once — documented
    # via the entry above; not blocking.
)


# =============================================================================
# § 0.4 — MutationViabilityPredicate (carried v0.3+)
# =============================================================================


@dataclass(frozen=True)
class MutationViabilityPredicate:
    """SPEC § 0.4 + § 0.2. Tier A predicate registered by C11a as a
    callable gate over a candidate mutation.

    `_predicate_fn` is a runtime callable; the underscore prefix
    excludes it from canonical-serialize hashes (replay/cache keys
    must not depend on function identity).

    Sunset enforcement (§ 0.2):
    - If `pending_upstream=True` and `expires_at_version is None` →
      startup raises.
    - If current C11a version >= expires_at_version AND predicate
      still pending → startup escalating warning.
    - LOCK gate (Inv 24 v0.5): pending_upstream count - active waivers
      == 0; ≤ 3 active waivers.

    Per S38 amendments B-NEW-J/K/L/P all LOCKED, all v1.0 predicates
    ship with `pending_upstream=False`.
    """
    rule_owner: str                              # "C5" | "C7" | "C8" | "C9" | "C10"
    rule_id: str                                 # e.g., "privacy_zoning"
    description: str
    _predicate_fn: Callable[..., tuple[bool, Optional[str]]]  # excluded from serialize
    pending_upstream: bool = False
    expires_at_version: Optional[str] = None      # required if pending_upstream=True


# =============================================================================
# § 0.2 — UpstreamAmendmentWaiver + WAIVER_REGISTRY
# =============================================================================


@dataclass(frozen=True)
class UpstreamAmendmentWaiver:
    """SPEC § 0.2 v0.5 — allows C11a v1.0 LOCK to proceed despite a
    pending_upstream predicate, in exchange for an explicit, audit-
    logged grace window.

    Rules:
    - Maximum 3 active waivers at LOCK time (Inv 24 v0.5).
    - Each waiver has hard expiration ceiling: current_version +
      PATCH+2.
    - Waiver must be signed by Ramalingam (sole grant authority — Rule 8).
    """
    rule_owner: str
    rule_id: str
    waiver_reason: str                          # human-readable; written to provenance
    granted_by: str                              # name; for audit trail
    granted_at_iso: str                          # ISO 8601 timestamp
    grace_window_expires_at_version: str         # SemVer; hard ceiling
    inline_check_implementation: str             # docstring-style declaration


# Registry — at v1.0 LOCK time, this is empty: B-NEW-J/K/L/P all
# LOCKED, no pending upstream amendments require waivers.
WAIVER_REGISTRY: Final[tuple[UpstreamAmendmentWaiver, ...]] = ()


# =============================================================================
# § 2.9 — QuarantineFingerprint (NEW v0.5 — resolves critique #5)
# =============================================================================


@dataclass(frozen=True)
class QuarantineFingerprint:
    """SPEC § 2.9 v0.5 — captures the runtime-quarantined-operators set.

    When `RegistryValidationMode.WARN` is in effect (development /
    debugging), operators that fail registry validation are marked
    "quarantined" — removed from `enabled_operators` for the process
    lifetime.

    Replays with mismatched fingerprints REJECTED (Inv 29) — two runs
    with different quarantine states effectively executed different
    mutation systems.

    `fingerprint_hash`: SHA256 of the canonical-serialized
    (quarantined_operators, quarantine_reasons) tuple. The hash
    function lives in the orchestrator (Sub-session 4); this module
    only declares the schema.
    """
    quarantined_operators: tuple[MutationOperator, ...]    # sorted lex-ASC
    quarantine_reasons: tuple[tuple[str, str], ...]        # (operator_value, reason)
    fingerprint_hash: str                                  # SHA256 hex digest


# =============================================================================
# § 2.4 — Diagnostic telemetry (REVISED v0.3 — fidelity labeled)
# =============================================================================


@dataclass(frozen=True)
class MutationDiagnostics:
    """SPEC § 2.4. Diagnostic-only metrics. NOT used for scoring or
    selection; tracks operational health of the mutation layer.

    `novelty_estimator_fidelity` labels the quality of the current
    novelty estimator (low = Jaccard signature distance; medium /
    high reserved for future B-NEW-F enrichment).

    `_observational_runtime_ms` (in TopologyMutationProvenance) is
    excluded from replay hashes — observational only.
    """
    per_operator_yield: Mapping[MutationOperator, float]    # accepted / total
    per_family_yield:   Mapping[MutationOperatorFamily, float]
    family_spread_entropy: float                             # Shannon over output families
    duplicate_ratio: float                                   # deduped / accepted
    novelty_deficit_estimator: float                         # 1 - avg signature distance
    novelty_estimator_fidelity: Literal["low", "medium", "high"] = "low"
    deep_mutation_runtime_ms: int = 0                        # observational; NOT in replay hashes


# =============================================================================
# § 2.3 — MutationApplicationResult
# =============================================================================


@dataclass(frozen=True)
class MutationApplicationResult:
    """SPEC § 2.3. Per-operator application outcome.

    `rejection_invariant_id` is owner-prefixed for traceability
    (e.g., "C7_W9", "C5_privacy_zoning", "C8_Inv_21", "C10_Inv_5").

    `upstream_regeneration_delta`: tuple of DeltaKey enum values that
    changed during Tier B regeneration. Empty for Tier A (SHALLOW)
    operators.

    Per Spec #4 v1.6 § 3.8 (B-NEW-T3 #4): `floor_label_affected`
    carries the per-floor causality signal for multi-floor operator
    applications. None for:
      - single-floor briefs (no multi-floor concept),
      - M8 dwelling-level applications (master swap doesn't scope to
        one floor; the result wrapper carries the master transition).
    Set to the directly-mutated floor label for per-floor operators
    (M0-M7, M9) dispatched via the multi-floor pipeline. Lightweight
    version of the v1.1-critique-walk request; full ancestry chain
    filed as B-C11A-8.
    """
    operator: MutationOperator
    valid: bool
    invalidity_reason: Optional[str]
    topology_variant_id: Optional[str]
    rejection_invariant_id: Optional[str]
    source_family_id: str
    output_family_id: Optional[str]                      # may differ for TRANSFORMS_FAMILY
    family_transition_policy: TopologyFamilyTransitionPolicy
    lineage_depth: MutationLineageDepth                  # NEW v0.3
    upstream_regeneration_delta: tuple[DeltaKey, ...] = ()  # type-tightened v0.5
    floor_label_affected: Optional[str] = None            # Spec #4 v1.6 § 3.8
    # Spec #4 v1.6 self-review fix (S41 close, Pattern B): operators that
    # construct a new candidate (Tier B regenerative ops + M8 multi-floor
    # cascade) MUST attach the constructed artifact here, so downstream
    # consumers (C11b NSGA-II, scoring, persistence) can actually USE
    # the mutated output. Tier A SHALLOW operators (M0-M5, M9) leave this
    # None — their predicate-only contract doesn't construct a new
    # candidate. compare_exclude=True so structural equality on results
    # doesn't depend on candidate identity (which is itself recursive
    # and may not be hashable cheaply).
    output_candidate: Optional[Any] = field(
        default=None,
        compare=False,
        hash=False,
    )


# =============================================================================
# § 2.6 — Config enums + TopologyMutationConfig
# =============================================================================


class EnforcementMode(str, enum.Enum):
    """SPEC § 2.6. Per-batch invariant-enforcement strictness.

    STRICT: every per-candidate failure halts the batch.
    WARN: per-candidate failures are aggregated; batch continues if at
        least one candidate succeeded; only BatchAllNonBaseFailedError
        on full failure.
    """
    STRICT = "strict"
    WARN = "warn"


class ProvenanceVerbosity(str, enum.Enum):
    """SPEC § 2.4. Tiered provenance verbosity (v0.2 critique #9).

    SUMMARY: accepted/rejected/dedup counts only.
    PER_OP: per-operator counts + reasons (default).
    FULL: every attempt logged with full state (development / debug).
    """
    SUMMARY = "summary"
    PER_OP  = "per_op"
    FULL    = "full"


class RegistryValidationMode(str, enum.Enum):
    """SPEC § 2.6. Operator registry validation strictness at startup.

    STRICT (default, recommended for production): startup raises
        OperatorRegistryError on any inconsistency.
    WARN (development / CI debugging): logs structured warnings and
        marks affected operators as quarantined for that process
        lifetime.
    """
    STRICT = "strict"
    WARN   = "warn"


@dataclass(frozen=True)
class FamilySlotAllocation:
    """SPEC § 2.6 v0.2. Per-family slot reservation (v0.2 critique #8)."""
    family: MutationOperatorFamily
    reserved_slots: int = 1


def _default_enabled_operators() -> tuple[MutationOperator, ...]:
    return tuple(op for op in MutationOperator)


def _default_family_slot_allocations() -> tuple[FamilySlotAllocation, ...]:
    return (
        FamilySlotAllocation(MutationOperatorFamily.BASE,      1),
        FamilySlotAllocation(MutationOperatorFamily.FLIP,      1),
        FamilySlotAllocation(MutationOperatorFamily.STAIRCASE, 1),
        FamilySlotAllocation(MutationOperatorFamily.CORRIDOR,  1),
        FamilySlotAllocation(MutationOperatorFamily.ZONE,      1),
        FamilySlotAllocation(MutationOperatorFamily.WET_WALL,  1),
        FamilySlotAllocation(MutationOperatorFamily.GRID,      1),
        FamilySlotAllocation(MutationOperatorFamily.VERTICAL,  1),
        FamilySlotAllocation(MutationOperatorFamily.ENTRY,     1),
    )


@dataclass(frozen=True)
class TopologyMutationConfig:
    """SPEC § 2.6 v0.4 + v0.5 — public configuration surface for
    mutate_topologies(). Every field MUST carry metadata["cache_relevant"]
    per Inv 26 (NEW v0.4).

    cache_relevant=True means the field is part of DeepMutationCacheKey;
    cache_relevant=False means it changes presentation/diagnostics only.
    """
    # cache-relevant (affect mutation result):
    enabled_operators: tuple[MutationOperator, ...] = field(
        default_factory=_default_enabled_operators,
        metadata={"cache_relevant": True},
    )
    max_seeds_per_input: int = field(
        default=8,
        metadata={"cache_relevant": True},
    )
    family_slot_allocations: tuple[FamilySlotAllocation, ...] = field(
        default_factory=_default_family_slot_allocations,
        metadata={"cache_relevant": True},
    )
    deterministic_order: bool = field(
        default=True,
        metadata={"cache_relevant": True},
    )
    emit_base: bool = field(
        default=True,
        metadata={"cache_relevant": True},
    )
    deduplicate_by_signature: bool = field(
        default=True,
        metadata={"cache_relevant": True},
    )
    # cache-irrelevant (affect presentation only):
    enforcement_mode: EnforcementMode = field(
        default=EnforcementMode.WARN,
        metadata={"cache_relevant": False},
    )
    provenance_verbosity: ProvenanceVerbosity = field(
        default=ProvenanceVerbosity.PER_OP,
        metadata={"cache_relevant": False},
    )
    deep_mutation_cache_enabled: bool = field(
        default=True,
        metadata={"cache_relevant": False},
    )
    skip_pending_upstream_predicates: bool = field(
        default=False,
        metadata={"cache_relevant": False},
    )
    registry_validation_mode: RegistryValidationMode = field(
        default=RegistryValidationMode.STRICT,
        metadata={"cache_relevant": False},
    )
    # Spec #4 v1.6 § 3.4 + § 3.4.1 — generation counter for cyclic M8
    # target selection and Tier 2 (operator scheduling) determinism.
    # cache_relevant=False because cache identity is Tier 1 (structural)
    # only; generation participates in Tier 2 / Tier 3 dispatch but
    # NOT in cache keys (per the determinism tier-table). Same source
    # at any generation -> same cache slot.
    generation: int = field(
        default=0,
        metadata={"cache_relevant": False},
    )


# =============================================================================
# Spec #4 v1.6 — FloorImpact (multi-floor pipeline rework, B-NEW-T3 #4)
# =============================================================================
#
# Per Spec #4 v1.6 § 3.11: structured floor-level impact descriptor for
# cross-floor mutation effects. v1.4 (item 6 from v1.3 critique walk).
#
# v1.3's bare `frozenset[str]` couldn't distinguish:
#   - directly mutated floors (require full C9->C10 cascade re-run)
#   - transitively invalidated floors (require validation-only re-run)
#   - revalidation-required floors (constraints to re-check, no regen)
#
# These distinctions matter for cost: a cascade re-run is O(C9+C10);
# a validation-only re-run is O(constraint-check-set).


_FloorImpactKind = Literal["direct", "indirect"]


@dataclass(frozen=True)
class FloorImpact:
    """Structured floor-level impact descriptor for cross-floor mutation
    effects. Per Spec #4 v1.6 § 3.11.

    v1.4 contract:
      - kind: "direct" for floors the operator directly mutates;
        "indirect" for floors whose constraint relationships to
        directly-mutated floors require re-evaluation.
      - requires_cascade: True iff this floor's C9->C10 must re-run.
      - requires_validation_only: True iff this floor's per-floor WZPC
        is reused as-is but cross-floor constraints involving this
        floor must be re-checked.

    Convention: `requires_cascade XOR requires_validation_only` — a
    floor either gets full regeneration or just constraint re-check,
    never both, never neither. Direct kinds default to cascade=True;
    indirect kinds default to validation_only=True.

    Today's v1.6 implementation always returns `requires_cascade=True`
    for direct-mutation floors (per § 3.2 / § 3.3 per-floor dispatch
    and § 3.4 M8 cascade). When B-C11A-7 (cross-floor invalidation
    graph) lands, indirect/validation-only floors become populated
    without changing the abstraction.
    """
    label: str
    kind: _FloorImpactKind
    requires_cascade: bool
    requires_validation_only: bool


# -----------------------------------------------------------------------------
# Spec #4 v1.6 § 3.4 — Multi-floor invalidity_reason taxonomy extension.
# -----------------------------------------------------------------------------
#
# These string constants are appended to the existing v1 invalidity_reason
# taxonomy (carried on MutationApplicationResult.invalidity_reason). They
# are documented as a vocabulary, not enum-enforced — Tier B operator
# implementations construct them inline when constructing failed results.
#
# Per § 3.4:
#   - "no_viable_master_target": M8 found no eligible target floor.
#   - "c9_generation_failed": C9 raised on the new per-floor brief.
#   - "c10_validation_failed": C9 succeeded; C10 rejected.
#   - "orchestration_state_drift:mfwzpN" where N in 1..6: wrapper
#     construction failed at Spec #3 Inv MFWZP-N.

MULTI_FLOOR_INVALIDITY_REASONS: tuple[str, ...] = (
    "no_viable_master_target",
    "c9_generation_failed",
    "c10_validation_failed",
    "orchestration_state_drift:mfwzp1",
    "orchestration_state_drift:mfwzp2",
    "orchestration_state_drift:mfwzp3",
    "orchestration_state_drift:mfwzp4",
    "orchestration_state_drift:mfwzp5",
    "orchestration_state_drift:mfwzp6",
)


# =============================================================================
# Forward declarations / re-exports for downstream modules
# =============================================================================

__all__ = [
    # operator enums
    "MutationOperator",
    "MutationTier",
    "MutationOperatorFamily",
    "TopologyFamilyTransitionPolicy",
    "_OPERATOR_FAMILY_POLICY",
    # delta vocabulary
    "DeltaKey",
    "OperatorExpectedDeltaSchema",
    # operator metadata
    "MutationOperatorMetadata",
    # lineage classification
    "MutationLineageDepth",
    # purity contract
    "PurityAttestation",
    "UPSTREAM_PURITY_REGISTRY",
    # waiver
    "UpstreamAmendmentWaiver",
    "WAIVER_REGISTRY",
    # predicate
    "MutationViabilityPredicate",
    # quarantine
    "QuarantineFingerprint",
    # config
    "TopologyMutationConfig",
    "EnforcementMode",
    "ProvenanceVerbosity",
    "RegistryValidationMode",
    "FamilySlotAllocation",
    # diagnostics + per-op result
    "MutationDiagnostics",
    "MutationApplicationResult",
    # Spec #4 v1.6: multi-floor pipeline
    "FloorImpact",
    "MULTI_FLOOR_INVALIDITY_REASONS",
]
