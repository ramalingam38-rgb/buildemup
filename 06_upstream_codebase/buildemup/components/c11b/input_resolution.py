"""
BuildemUp — Component 11b — input artifact resolution
=======================================================

Per SPEC v1.1 LOCKED:

- § 0.3 ``_resolve_input_artifact`` — the ONLY path for reading the
  input artifact in Phase 1 (Inv 26).
- § 0.3.1 worked-example table over operator classes.
- § 0.3.2 W6-6 ``get_primary_application_result`` typed accessor —
  wraps the brittle tuple indexing that B-C11A-MTC-SINGLETON will
  eventually eliminate.
- § 3 Phase 1 step 2 (W5-9 ordering): MF rejection happens IMMEDIATELY
  after artifact resolution, BEFORE signature derivation, PRNG, etc.

DISCIPLINE (W6-6): all C11b code accessing the application result MUST
use ``get_primary_application_result(mtc)`` rather than
``mtc.application_results[0]``. Direct indexing is a code-review
violation pattern.
"""
from __future__ import annotations

from typing import Any, TypeAlias

from buildemup.components.c11a.candidate_context import (
    is_real_multi_floor_candidate,
)
from buildemup.components.c11a.provenance import MutatedTopologyCandidate
from buildemup.components.c11a.schema import MutationApplicationResult
from buildemup.components.c11b.errors import (
    EvaluatorContractError,
    MultiFloorRefinementNotSupportedError,
)


# § 0.3.2 W6-6 — type alias documenting the v1 contract
PrimaryApplicationResult: TypeAlias = MutationApplicationResult
"""Type alias documenting that v1 MTC carries exactly one
application result (per C11a ``__post_init__`` assertion).
Once B-C11A-MTC-SINGLETON ships, this alias points to the
type-honest singleton field."""


def get_primary_application_result(
    mtc: MutatedTopologyCandidate,
) -> PrimaryApplicationResult:
    """W6-6 typed accessor for the single application result on an MTC
    at v1. Wraps the tuple-indexing brittleness that
    B-C11A-MTC-SINGLETON will eventually eliminate.

    Raises:
        EvaluatorContractError: if the MTC violates the singleton
            contract (defensive — mirrors C11a's ``__post_init__``
            enforcement).
    """
    if len(mtc.application_results) != 1:
        raise EvaluatorContractError(
            f"C11b: MutatedTopologyCandidate must carry exactly one "
            f"application result at v1; got "
            f"{len(mtc.application_results)}. See B-C11A-MTC-SINGLETON."
        )
    return mtc.application_results[0]


def _is_multi_floor_artifact(artifact: Any) -> bool:
    """Whether the resolved artifact is a real multi-floor wrapper.

    Reuses C11a's ``is_real_multi_floor_candidate`` (marker-attribute
    detection per Spec #4 v1.6 § 3.5)."""
    return is_real_multi_floor_candidate(artifact)


def _resolve_input_artifact(mtc: MutatedTopologyCandidate) -> Any:
    """Per Inv 26: deterministic resolution of the topology artifact
    C11b refines from a ``MutatedTopologyCandidate``.

    Rule:
      - Enforce len==1 via ``get_primary_application_result``.
      - If ``result.output_candidate is not None``: use it (Tier B
        regenerative ops M6/M7; M8 multi-floor; M0 single-/multi-floor
        — all populate ``output_candidate`` per S41 self-review fix).
      - Else: use ``mtc.source_candidate`` (Tier A SHALLOW M1-M5, M9 —
        predicate-only ops that emit verdicts without constructing new
        geometry; v1 of C11b refines the unchanged source).
    """
    result = get_primary_application_result(mtc)
    if result.output_candidate is not None:
        return result.output_candidate
    return mtc.source_candidate


def reject_if_multi_floor(artifact: Any, topology_index: int) -> None:
    """W5-9 ordering helper: raise ``MultiFloorRefinementNotSupportedError``
    if the artifact is multi-floor. Called IMMEDIATELY after
    ``_resolve_input_artifact`` and BEFORE any signature / PRNG /
    evaluator work."""
    if _is_multi_floor_artifact(artifact):
        raise MultiFloorRefinementNotSupportedError(
            f"C11b v1 does not support multi-floor refinement; "
            f"topology_index={topology_index} resolved to a real "
            f"MultiFloorWetZonePlannedCandidate. See B-C11B-MF for "
            f"the post-v1 expansion path."
        )


__all__ = [
    "PrimaryApplicationResult",
    "get_primary_application_result",
    "_is_multi_floor_artifact",
    "_resolve_input_artifact",
    "reject_if_multi_floor",
]
