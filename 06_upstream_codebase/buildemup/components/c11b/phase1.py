"""
BuildemUp — Component 11b — Phase 1 per-topology NSGA-II loop
================================================================

Per SPEC v1.1 LOCKED:
- § 3 Phase 1 (REVISED v0.4, v0.5 W4-9 step ordering)
- § 0.6 (D-EV-1, D-EV-2) evaluator failure isolation + Inv 28 skip cap
- § 0.7 (D-PR-1) per-topology PRNG via SeedSequence

THE ORDERING IS SIGNIFICANT (W5-9 PATCH-NOW):

1. Resolve input artifact via ``_resolve_input_artifact`` (Inv 26).
2. Reject multi-floor IMMEDIATELY. NO signature derivation, NO PRNG,
   NO evaluator init has happened yet → cheap rejection.
3. Derive ``topology_signature`` via C11a's ``derive_canonical_signature``.
4. Build per-topology PRNG via SeedSequence.
5. Start wall-clock timer.
6. Initialize population (feasibility-aware).
7. NSGA-II loop with per-candidate evaluator skip cap (Inv 28).
8. Track ``longest_generation_seconds`` + ``skipped_candidates_total``.
9. Survivor selection via ``select_survivors`` with deterministic tie-break.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from buildemup.components.c11a.source_signature import derive_canonical_signature
from buildemup.components.c11b.bounds import compute_aspect_constraint_violation
from buildemup.components.c11b.config import LocalRefinementConfig
from buildemup.components.c11b.errors import EvaluatorContractError
from buildemup.components.c11b.evaluator import EvaluatorProtocol
from buildemup.components.c11b.initialization import (
    RoomSizeRequirement,
    feasibility_aware_init,
)
from buildemup.components.c11b.input_resolution import (
    _resolve_input_artifact,
    reject_if_multi_floor,
)
from buildemup.components.c11b.nsga2.operators import (
    polynomial_mutation,
    sbx_crossover,
)
from buildemup.components.c11b.nsga2.selection import select_survivors
from buildemup.components.c11b.prng import _build_per_topology_rng
from buildemup.components.c11b.schema import (
    ObjectiveVector,
    OperatorClass,
    RefinedCandidate,
    RefinedParameters,
    RoomDimension,
)
from buildemup.components.c11b.stagnation import compute_stagnation_signature_lite
from buildemup.components.c11b.telemetry import PerTopologyTelemetry
from buildemup.components.c11b.timeout import WallclockBudget


# =============================================================================
# Operator class mapping (C11a MutationOperator → C11b OperatorClass)
# =============================================================================


def _classify_operator(mtc: Any) -> OperatorClass:
    """Classify an MTC's single operator into the C11b ``OperatorClass``.

    Per § 0.3.1 worked-example table:
    - M0_BASE → ``M0_BASE``
    - M1-M5, M9 (Tier A SHALLOW) → ``TIER_A_SHALLOW``
    - M6, M7 (Tier B REGENERATIVE) → ``TIER_B_REGENERATIVE``
    - M8 (multi-floor) → ``M8_MULTI_FLOOR`` (rejected at v1, but mapping
      is provided for completeness).
    """
    op = mtc.applied_operators[0]
    op_name = op.value if hasattr(op, "value") else str(op)
    if op_name == "m0_base":
        return OperatorClass.M0_BASE
    if op_name.startswith("m6") or op_name.startswith("m7"):
        return OperatorClass.TIER_B_REGENERATIVE
    if op_name.startswith("m8"):
        return OperatorClass.M8_MULTI_FLOOR
    # M1, M2, M3a-c, M4, M5, M9a-d
    return OperatorClass.TIER_A_SHALLOW


# =============================================================================
# Parameter ↔ float-vector marshalling
# =============================================================================


def _params_to_vec(rp: RefinedParameters) -> tuple[float, ...]:
    out: list[float] = []
    for rd in rp.room_dimensions:
        out.append(rd.width_m)
        out.append(rd.depth_m)
    return tuple(out)


def _vec_to_params(
    vec: tuple[float, ...], rp_template: RefinedParameters
) -> RefinedParameters:
    """Rebuild RefinedParameters using the room_id ordering from
    rp_template (which is sorted lex-ASC)."""
    rds: list[RoomDimension] = []
    for i, rd in enumerate(rp_template.room_dimensions):
        w = vec[2 * i]
        d = vec[2 * i + 1]
        rds.append(RoomDimension(room_id=rd.room_id, width_m=w, depth_m=d))
    return RefinedParameters(room_dimensions=tuple(rds))


def _build_bounds_from_requirements(
    requirements: tuple[RoomSizeRequirement, ...],
    envelope_w: float,
    envelope_d: float,
    *,
    universal_max_multiplier: float = 2.5,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Build flat lower/upper bound vectors for SBX/polynomial mutation
    using ``derive_room_upper_bounds``."""
    from buildemup.components.c11b.bounds import derive_room_upper_bounds

    sorted_reqs = sorted(requirements, key=lambda r: r.room_id)
    lower: list[float] = []
    upper: list[float] = []
    total_min = sum(r.min_width_m * r.min_depth_m for r in sorted_reqs)
    for r in sorted_reqs:
        own_min = r.min_width_m * r.min_depth_m
        others_min = total_min - own_min
        uw, ud = derive_room_upper_bounds(
            r.room_id,
            r.category,
            r.min_width_m,
            r.min_depth_m,
            envelope_w,
            envelope_d,
            others_min,
            universal_max_multiplier=universal_max_multiplier,
        )
        lower.extend([r.min_width_m, r.min_depth_m])
        upper.extend([uw, ud])
    return tuple(lower), tuple(upper)


# =============================================================================
# Evaluator orchestration (Inv 28 skip cap)
# =============================================================================


def _evaluate_population(
    population: tuple[RefinedCandidate, ...],
    evaluator: EvaluatorProtocol,
    config: LocalRefinementConfig,
) -> tuple[tuple[RefinedCandidate, ...], int]:
    """Per § 0.6 (D-EV-1, D-EV-2): per-candidate ``EvaluatorContractError``
    is skip-and-continue up to Inv 28 cap; non-contract exception →
    systemic wrap.

    Returns (evaluated_population, skipped_count).
    """
    evaluated: list[RefinedCandidate] = []
    skipped = 0
    # Inv 28 (spec § 0.0c): cap is computed against config.pop_size
    # (the stable constant), NOT len(population). This makes the cap
    # invariant across initial-eval vs offspring-eval, matching the
    # literal spec text "max(1, int(pop_size * config.evaluator_skip_cap_fraction))".
    skip_cap = max(1, int(config.pop_size * config.evaluator_skip_cap_fraction))

    for candidate in population:
        # Constraint-violation augmentation: aspect ratio HARD (Inv 22).
        try:
            objective_vector = evaluator.evaluate(candidate)
        except EvaluatorContractError:
            skipped += 1
            if skipped > skip_cap:
                raise EvaluatorContractError(
                    f"C11b: per-candidate evaluator failure cap exceeded "
                    f"({skipped} > {skip_cap} on pop_size={config.pop_size}, "
                    f"fraction={config.evaluator_skip_cap_fraction:.2f}); "
                    f"upgrading to systemic per Inv 28."
                )
            continue
        except Exception as exc:
            raise EvaluatorContractError(
                f"C11b: systemic evaluator failure (non-contract exception): "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        # Add aspect-ratio constraint violations to evaluator's reading.
        aspect_violation_total = 0.0
        for rd in candidate.refined_parameters.room_dimensions:
            aspect_violation_total += compute_aspect_constraint_violation(
                rd.width_m, rd.depth_m
            )
        augmented = ObjectiveVector(
            values=objective_vector.values,
            constraint_violations=(
                objective_vector.constraint_violations + aspect_violation_total
            ),
        )
        evaluated.append(replace(candidate, objective_vector=augmented))
    return tuple(evaluated), skipped


# =============================================================================
# Phase 1 result struct
# =============================================================================


@dataclass(frozen=True)
class _PerTopologyResult:
    """Internal result of one topology's NSGA-II loop."""
    refined_candidates: tuple[RefinedCandidate, ...]
    telemetry: PerTopologyTelemetry
    resolved_objective_count: int


# =============================================================================
# Public phase 1 entry point
# =============================================================================


def refine_one_topology(
    mtc: Any,
    topology_index: int,
    requirements: tuple[RoomSizeRequirement, ...],
    envelope_w: float,
    envelope_d: float,
    evaluator: EvaluatorProtocol,
    config: LocalRefinementConfig,
) -> _PerTopologyResult:
    """Run NSGA-II on one ``MutatedTopologyCandidate``. Returns a struct
    with the per-topology Pareto-ordered output + telemetry.

    Spec § 3 Phase 1 ordering (W5-9):
    1. Resolve input artifact (Inv 26).
    2. Reject multi-floor IMMEDIATELY (W5-9).
    3. Derive topology_signature.
    4. Build per-topology PRNG.
    5. Start wall-clock budget.
    6. Initialize feasibility-aware population.
    7. NSGA-II loop with skip cap.
    """
    # Step 1 — input artifact resolution.
    artifact = _resolve_input_artifact(mtc)

    # Step 2 — multi-floor rejection BEFORE any expensive work.
    reject_if_multi_floor(artifact, topology_index)

    # Step 3 — signature derivation (only after MF rejection passes).
    topology_signature = derive_canonical_signature(artifact)

    # Step 4 — per-topology PRNG.
    rng = _build_per_topology_rng(
        config.master_seed, topology_index, topology_signature
    )

    # Step 5 — start wall-clock budget.
    budget = WallclockBudget(
        config.per_topology_wallclock_seconds, topology_index
    )

    operator_class = _classify_operator(mtc)

    # Step 6 — initialize.
    initial_params = feasibility_aware_init(
        requirements,
        envelope_w,
        envelope_d,
        rng,
        pop_size=config.pop_size,
        permutations_per_candidate=config.permutations_per_candidate,
        init_max_retries=config.init_max_retries,
        universal_max_multiplier=config.universal_max_multiplier,
    )

    # Wrap into RefinedCandidates via the helper constructor.
    population = tuple(
        RefinedCandidate.from_operator_class(
            operator_class=operator_class,
            refined_parameters=rp,
            source_topology_candidate_signature=topology_signature,
        )
        for rp in initial_params
    )

    lower, upper = _build_bounds_from_requirements(
        requirements,
        envelope_w,
        envelope_d,
        universal_max_multiplier=config.universal_max_multiplier,
    )

    # Step 7 — NSGA-II loop.
    skipped_total = 0
    resolved_objective_count = 0
    stable_count = 0
    prior_sig_hash: str | None = None

    completed_gens = 0

    # Initial evaluation.
    budget.check(gen=0, max_gen=config.max_generations)
    budget.open_generation()
    population, sk = _evaluate_population(population, evaluator, config)
    skipped_total += sk
    if population and population[0].objective_vector is not None:
        resolved_objective_count = len(population[0].objective_vector.values)
    budget.close_generation()

    for gen in range(1, config.max_generations + 1):
        budget.check(gen=gen, max_gen=config.max_generations)
        budget.open_generation()

        # Reproduction: SBX + polynomial mutation. Pair parents
        # sequentially (rng-shuffled order).
        if len(population) < 2:
            break

        parent_indices = list(range(len(population)))
        rng.shuffle(parent_indices)
        offspring_params: list[RefinedParameters] = []
        for i in range(0, len(parent_indices) - 1, 2):
            a_idx = parent_indices[i]
            b_idx = parent_indices[i + 1]
            a_vec = _params_to_vec(population[a_idx].refined_parameters)
            b_vec = _params_to_vec(population[b_idx].refined_parameters)
            c1, c2 = sbx_crossover(
                a_vec,
                b_vec,
                lower,
                upper,
                rng,
                eta_c=config.sbx_eta_c,
                crossover_probability=config.crossover_rate,
            )
            c1 = polynomial_mutation(
                c1,
                lower,
                upper,
                rng,
                eta_m=config.polynomial_eta_m,
                mutation_probability=config.mutation_rate,
            )
            c2 = polynomial_mutation(
                c2,
                lower,
                upper,
                rng,
                eta_m=config.polynomial_eta_m,
                mutation_probability=config.mutation_rate,
            )
            template = population[a_idx].refined_parameters
            offspring_params.append(_vec_to_params(c1, template))
            offspring_params.append(_vec_to_params(c2, template))

        offspring = tuple(
            RefinedCandidate.from_operator_class(
                operator_class=operator_class,
                refined_parameters=op,
                source_topology_candidate_signature=topology_signature,
            )
            for op in offspring_params
        )
        offspring, sk = _evaluate_population(offspring, evaluator, config)
        skipped_total += sk

        # Survivor selection: combined pool, NSGA-II rank+crowding+tiebreak.
        combined = population + offspring
        population = select_survivors(combined, config.pop_size)

        # Stagnation check.
        sig = compute_stagnation_signature_lite(
            population, gen, config.stagnation_config
        )
        if sig.metric_used == "pairwise_distance":
            if sig.composite_hash == prior_sig_hash:
                stable_count += 1
            else:
                stable_count = 1
            prior_sig_hash = sig.composite_hash
            if stable_count >= config.convergence_stable_gens:
                completed_gens = gen
                budget.close_generation()
                break

        completed_gens = gen
        budget.close_generation()

    # Truncate to pareto_output_size for the final emitted slice.
    output = population[: config.pareto_output_size]

    telemetry = PerTopologyTelemetry(
        topology_index=topology_index,
        completed_generations=completed_gens,
        longest_generation_seconds=budget.longest_generation_seconds,
        skipped_candidates_total=skipped_total,
    )

    return _PerTopologyResult(
        refined_candidates=output,
        telemetry=telemetry,
        resolved_objective_count=resolved_objective_count,
    )


__all__ = [
    "refine_one_topology",
    "_PerTopologyResult",
    "_classify_operator",
]
