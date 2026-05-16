"""
BuildemUp — Component 11b — schema (RefinedCandidate + RefinedParameters)
==========================================================================

Per SPEC v1.1 LOCKED:

- § 2.1 schema additions across v0.4-v0.7 (capability flags, tiebreak
  fingerprint, source signature, output ordering fields)
- § 0.3.1 worked example table (capability flag derivation per operator
  class)
- § 0.3.1 W6-1 hard-assertion 3-flag equality + ``from_operator_class``
  helper + ``capability_mode`` derived property
- § 0.7.1 ``tiebreak_fingerprint`` precompute via
  ``_compute_tiebreak_fingerprint`` in ``__post_init__``
- § 0.9 (v1.0 carried): ``output_sequence_is_quality_ranked`` +
  ``output_sequence_strategy`` (Inv 23 — quality-ranked MUST be False
  at v1)

W6-1 enforcement: the 3-flag equality invariant is a HARD assertion in
``__post_init__`` (not test-only). Per F-v6-3: ``tiebreak_fingerprint``
is set via ``object.__setattr__`` because the dataclass is frozen.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Literal

from buildemup.components.c11b.errors import InvariantViolationError
from buildemup.components.c11b.tiebreak import _compute_tiebreak_fingerprint


# =============================================================================
# § 0.3.1 — OperatorClass (capability-flag derivation source)
# =============================================================================


class OperatorClass(str, enum.Enum):
    """Classification of an upstream operator (C11a) for capability-flag
    derivation per spec § 0.3.1 worked-example table.

    The class is determined by C11a's ``MutationApplicationResult`` —
    Tier (SHALLOW vs REGENERATIVE) plus operator identity (M0 identity,
    M8 multi-floor):

    - TIER_A_SHALLOW: M1-M5, M9 — predicate-only, no new geometry
    - TIER_B_REGENERATIVE: M6, M7 — Tier B regenerative pipeline
    - M0_BASE: identity mutation (single-floor or multi-floor wrapper)
    - M8_MULTI_FLOOR: vertical rearrangement (rejected at v1 — but the
      flag derivation still works for completeness)

    NOTE: this enum is C11b-internal; the upstream
    ``MutationOperator`` enum lives in C11a. The mapping from upstream
    operator → ``OperatorClass`` is done by ``from_operator_class``
    helpers below.
    """
    TIER_A_SHALLOW = "tier_a_shallow"
    TIER_B_REGENERATIVE = "tier_b_regenerative"
    M0_BASE = "m0_base"
    M8_MULTI_FLOOR = "m8_multi_floor"


def _capability_flags_for_operator_class(
    operator_class: OperatorClass,
) -> tuple[bool, bool, bool]:
    """Return ``(geometry_materialized, placement_safe,
    requires_transform_resolution)`` per spec § 0.3.1 worked-example
    table.

    At v1 the three flags collapse to 2 effective states:
    - Tier A SHALLOW: (False, False, True) — predicate verdict only
    - Tier B / M0 / M8: (True, True, False) — geometry materialized
    """
    if operator_class == OperatorClass.TIER_A_SHALLOW:
        return (False, False, True)
    # Tier B, M0_BASE, M8_MULTI_FLOOR all carry materialized geometry.
    return (True, True, False)


# =============================================================================
# § 2.1 — ObjectiveVector (carried v1.0 surface)
# =============================================================================


@dataclass(frozen=True)
class ObjectiveVector:
    """The evaluator's output for one candidate.

    ``values`` is a tuple of ``(objective_name, score)`` pairs in stable
    order (the evaluator commits to ordering at construction). Lower is
    better by NSGA-II convention.

    ``constraint_violations`` is a scalar ≥ 0; 0 means feasible.
    Used by NSGA-II-CDP (Constrained Dominance Principle): a feasible
    candidate dominates an infeasible one regardless of objective
    values; among two infeasible candidates the lower
    ``constraint_violations`` dominates.
    """
    values: tuple[tuple[str, float], ...]
    constraint_violations: float = 0.0

    def __post_init__(self) -> None:
        if self.constraint_violations < 0.0:
            raise InvariantViolationError(
                f"ObjectiveVector.constraint_violations must be >= 0; "
                f"got {self.constraint_violations}."
            )


# =============================================================================
# § 2.1 — RefinedParameters (the per-candidate parameter vector)
# =============================================================================


@dataclass(frozen=True)
class RoomDimension:
    """One room's refined dimensions in metres."""
    room_id: str
    width_m: float
    depth_m: float

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.depth_m <= 0.0:
            raise InvariantViolationError(
                f"RoomDimension {self.room_id} requires positive dims; "
                f"got width={self.width_m}, depth={self.depth_m}."
            )


@dataclass(frozen=True)
class RefinedParameters:
    """The per-candidate parameter vector C11b NSGA-II refines.

    At v1, parameter scope is room dimensions only (per CODING_MANDATE:
    "Geometric parameter refinement (room dims only at v1)"). Future
    expansion (orientation, wet-zone offsets) is post-v1.

    Stored as a tuple sorted lex-ASC by ``room_id`` so that
    ``canonical_serialize`` produces a deterministic key for the W6-3
    tie-break fingerprint.
    """
    room_dimensions: tuple[RoomDimension, ...]

    def __post_init__(self) -> None:
        # Stable lex-ASC ordering by room_id is required for canonical
        # serialization → deterministic tiebreak_fingerprint.
        ids = [r.room_id for r in self.room_dimensions]
        if ids != sorted(ids):
            raise InvariantViolationError(
                f"RefinedParameters.room_dimensions must be sorted lex-ASC "
                f"by room_id; got order {ids}."
            )
        if len(set(ids)) != len(ids):
            raise InvariantViolationError(
                f"RefinedParameters.room_dimensions has duplicate room_ids; "
                f"got {ids}."
            )


# =============================================================================
# § 2.1 — RefinedCandidate (the C11b output unit)
# =============================================================================


@dataclass(frozen=True)
class RefinedCandidate:
    """One refined candidate produced by C11b's NSGA-II loop.

    Carries:
    - Refined parameters (room dimensions at v1).
    - Capability flags derived from the source C11a operator class
      (W5-5 → W6-1 hard-asserted).
    - Tie-break fingerprint (W5-12 precomputed at ``__post_init__``,
      W6-3 version-anchored).
    - Source topology signature for the tie-break layer 1 key.
    - Output ordering contract fields (v1.0 § 0.9 carried,
      Inv 23: quality-ranked MUST be False at v1).
    - Optional ``objective_vector`` populated after the evaluator runs
      (None during initialization).

    PER F-v6-3 (frozen dataclass gotcha): ``tiebreak_fingerprint`` is
    set via ``object.__setattr__`` in ``__post_init__`` because the
    dataclass is frozen. The user must NOT pass it at construction —
    use ``field(default=0)`` then overwrite. We accept user-passed
    values too (recomputed if it doesn't match, for safety).
    """
    refined_parameters: RefinedParameters
    source_topology_candidate_signature: str
    geometry_materialized: bool
    placement_safe: bool
    requires_transform_resolution: bool
    # Quality-ranked contract (v1.0 § 0.9, Inv 23).
    output_sequence_is_quality_ranked: bool = False
    output_sequence_strategy: Literal["diversity_order"] = "diversity_order"
    # Optional objective vector; populated by the evaluator post-init.
    objective_vector: ObjectiveVector | None = None
    # Pareto rank (set during NSGA-II sorting); -1 means "not yet ranked".
    pareto_rank: int = -1
    crowding_distance: float = 0.0
    # F-v6-3: set via object.__setattr__ in __post_init__.
    tiebreak_fingerprint: int = field(default=0)

    def __post_init__(self) -> None:
        # W6-1 HARD ASSERTION: 3-flag equality invariant.
        # placement_safe == geometry_materialized AND
        # requires_transform_resolution == NOT geometry_materialized.
        if self.placement_safe != self.geometry_materialized:
            raise InvariantViolationError(
                f"RefinedCandidate W6-1 violation: placement_safe="
                f"{self.placement_safe} must equal geometry_materialized="
                f"{self.geometry_materialized}. At v1 these two flags "
                f"are co-determined; future placement-aware Tier A "
                f"operators may decouple them, but that requires a spec "
                f"amendment, not silent construction of invalid combos."
            )
        if self.requires_transform_resolution != (not self.geometry_materialized):
            raise InvariantViolationError(
                f"RefinedCandidate W6-1 violation: requires_transform_resolution="
                f"{self.requires_transform_resolution} must equal "
                f"NOT geometry_materialized (={not self.geometry_materialized}). "
                f"At v1 Tier A operators imply pending transform; Tier B "
                f"and M0 carry materialized geometry directly."
            )
        # Inv 23: quality-ranked MUST be False at v1.
        if self.output_sequence_is_quality_ranked is not False:
            raise InvariantViolationError(
                f"RefinedCandidate Inv 23 violation: "
                f"output_sequence_is_quality_ranked MUST be False at v1 "
                f"(diversity ordering only). v2 requires B-NEW-V3."
            )
        # F-v6-3: precompute the tie-break fingerprint via
        # object.__setattr__ because the dataclass is frozen.
        computed = _compute_tiebreak_fingerprint(self.refined_parameters)
        if self.tiebreak_fingerprint == 0:
            object.__setattr__(self, "tiebreak_fingerprint", computed)
        elif self.tiebreak_fingerprint != computed:
            # Caller passed a stale or wrong fingerprint — recompute
            # silently rather than trust user input. (This protects
            # against deserialization-then-version-bump scenarios.)
            object.__setattr__(self, "tiebreak_fingerprint", computed)

    # § 0.3.1 W6-1 derived property — read-only capability_mode label
    @property
    def capability_mode(self) -> Literal["PREDICATE_ONLY", "MATERIALIZED"]:
        """Read-only convenience label for logging / debug / downstream
        consumers. Returns "PREDICATE_ONLY" iff NOT
        ``geometry_materialized``. Not stored in the dataclass."""
        if not self.geometry_materialized:
            return "PREDICATE_ONLY"
        return "MATERIALIZED"

    # § 0.3.1 W6-1 helper constructor — documented construction path
    @classmethod
    def from_operator_class(
        cls,
        operator_class: OperatorClass,
        refined_parameters: RefinedParameters,
        source_topology_candidate_signature: str,
        *,
        objective_vector: ObjectiveVector | None = None,
        pareto_rank: int = -1,
        crowding_distance: float = 0.0,
    ) -> "RefinedCandidate":
        """Build a ``RefinedCandidate`` with capability flags derived
        from the upstream operator class per § 0.3.1.

        This is the DOCUMENTED construction path. Direct construction
        with manually-passed flags is allowed but discouraged —
        ``__post_init__`` will reject invalid combos via W6-1.
        """
        gm, ps, rtr = _capability_flags_for_operator_class(operator_class)
        return cls(
            refined_parameters=refined_parameters,
            source_topology_candidate_signature=source_topology_candidate_signature,
            geometry_materialized=gm,
            placement_safe=ps,
            requires_transform_resolution=rtr,
            objective_vector=objective_vector,
            pareto_rank=pareto_rank,
            crowding_distance=crowding_distance,
        )


__all__ = [
    "OperatorClass",
    "ObjectiveVector",
    "RoomDimension",
    "RefinedParameters",
    "RefinedCandidate",
    "_capability_flags_for_operator_class",
]
