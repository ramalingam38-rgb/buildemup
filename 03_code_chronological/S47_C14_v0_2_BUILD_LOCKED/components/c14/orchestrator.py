"""
BuildemUp — Component 14 — Orchestrator
========================================

Per C14 SPEC v0.2 LOCKED § 5 (failure modes) + § 3 (phase sequencing)
+ Inv E1 (one report per SuccessfulDoorPlacement) + Inv E8/E9 (upstream
advisory passthrough) + Inv E16 (provenance triple).

Two public entry points:

1. `analyze_circulation(...)`:
   Single-candidate orchestrator. Takes ONE SuccessfulDoorPlacement +
   its room_metadata + the upstream advisory_schema_version, runs the
   full α→β→γ→δ→ε→ζ pipeline, returns
   SuccessfulCirculationAnalysis | FailedCirculationAnalysis.

2. `analyze_circulation_batch(...)`:
   Batch orchestrator. Takes a DoorPlacementBatchResult + a metadata
   lookup, iterates over `batch.successful`, runs analyze_circulation
   per candidate, assembles a CirculationAnalysisBatchResult.

---

**Error tier handling per § 5:**

- `LocalCirculationError` (UpstreamSchemaDriftError, C14ConfigurationError):
  Always halts, regardless of `strict_mode`. These indicate a system-
  level inconsistency that no per-candidate WARN can recover from.

- `PerCandidateCirculationError` (EntryRoomNotFoundError,
  GraphInconsistencyError):
  STRICT mode (default) → raise immediately, batch halts.
  WARN mode → caught, packaged into FailedCirculationAnalysis, batch
  continues with the next candidate.

---

**Derivations from SuccessfulDoorPlacement:**

`placed_room_ids`: derived from `placement.doors` by collecting every
non-EXTERNAL endpoint. Sorted lex-ASC by `construct_graph_topology`.

`main_entry_room_id`: derived from the single door with
`is_main_entry=True` (Inv D6 from C13 guarantees exactly one). The
non-EXTERNAL endpoint of that door is the main entry room. If both
endpoints are non-EXTERNAL (an internal "main entry" between rooms),
the canonical room_b is used (lex-ASC tiebreak — Inv E7 determinism).

`primary_door_ids`: at v0.2 SKETCH, passed as empty frozenset() since
C13 v1.0's Door schema doesn't carry an `is_secondary` field. Filed
as `B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION` for v1.0 LOCK.
"""
from __future__ import annotations

from buildemup.components.c13.schema import (
    DoorPlacementBatchResult,
    SuccessfulDoorPlacement,
)

from .advisory_passthrough import assemble_advisory_bundle
from .cache_keys import (
    C14CacheKeys,
    config_signature_for,
    derive_c14_cache_keys,
)
from .config import CirculationConfig
from .contracts import (
    EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID,
    RoomMetadata,
)
from .errors import (
    EntryRoomNotFoundError,
    PerCandidateCirculationError,
    UpstreamSchemaDriftError,
)
from .flag_emission import emit_flags
from .graph_construction import construct_graph_topology
from .layout_metrics import compute_layout_metrics
from .node_metrics import compute_node_metrics
from .report_assembly import assemble_report, compute_category_coverage
from .schema import (
    CirculationAnalysisBatchResult,
    FailedCirculationAnalysis,
    FailureRecord,
    SuccessfulCirculationAnalysis,
)
from .versioning import (
    C14_METRIC_VERSION,
    C14_VERSION,
    EXPECTED_ADVISORY_SCHEMA_VERSION,
)


# =============================================================================
# Internal derivations
# =============================================================================

def _derive_placed_room_ids(
    placement: SuccessfulDoorPlacement,
) -> tuple[str, ...]:
    """Collect every non-EXTERNAL room endpoint from the doors."""
    room_ids: set[str] = set()
    for door in placement.doors:
        if door.room_a_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
            room_ids.add(door.room_a_id)
        if door.room_b_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
            room_ids.add(door.room_b_id)
    return tuple(sorted(room_ids))


def _derive_main_entry_room_id(
    placement: SuccessfulDoorPlacement,
) -> str:
    """Per C13 Inv D6: exactly one door has is_main_entry=True.

    The non-EXTERNAL endpoint of that door is the main entry room.
    If both endpoints are non-EXTERNAL (a degenerate inner "main
    entry"), the lex-ASC-smaller endpoint is the main entry per
    Inv E7 deterministic tiebreak.

    Raises EntryRoomNotFoundError if no door has is_main_entry=True
    (defensive — C13 should already enforce this).
    """
    main_doors = [d for d in placement.doors if d.is_main_entry]
    if not main_doors:
        raise EntryRoomNotFoundError(
            f"No door with is_main_entry=True in placement "
            f"{placement.source_placed_candidate_signature!r}."
        )
    main_door = main_doors[0]
    if main_door.room_a_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        # canonical room_a < room_b ordering means if room_a is non-
        # EXTERNAL, it's the lex-ASC-smaller endpoint.
        return main_door.room_a_id
    if main_door.room_b_id != EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
        return main_door.room_b_id
    raise EntryRoomNotFoundError(
        f"Main entry door in placement "
        f"{placement.source_placed_candidate_signature!r} has BOTH "
        f"endpoints == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID — "
        f"impossible per C13 contract."
    )


def _build_cache_keys(
    *,
    placement: SuccessfulDoorPlacement,
    config: CirculationConfig,
) -> C14CacheKeys:
    """Compose C14 cache keys from upstream C13 + this config."""
    c13_full_key = placement.cache_keys.full_cache_key
    cfg_sig = config_signature_for(
        flag_density_factor=config.flag_density_factor,
        betweenness_threshold=config.betweenness_threshold,
        excessive_depth_threshold=config.excessive_depth_threshold,
        category_coverage_low_threshold=(
            config.category_coverage_low_threshold
        ),
    )
    return derive_c14_cache_keys(
        c13_cache_key=c13_full_key,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        config_signature=cfg_sig,
    )


# =============================================================================
# Per-phase wrapper that maps exceptions to FailureRecord
# =============================================================================

def _run_pipeline(
    *,
    placement: SuccessfulDoorPlacement,
    room_metadata: tuple[RoomMetadata, ...],
    config: CirculationConfig,
    advisory_schema_version: int,
) -> SuccessfulCirculationAnalysis:
    """Run all six phases for one candidate; returns Successful... .

    On per-candidate failures, raises a PerCandidateCirculationError.
    On schema drift or config errors, raises a LocalCirculationError.
    The caller handles dispatch.
    """
    signature = placement.source_placed_candidate_signature

    # ── Pre-flight: schema-drift check (Inv E9) ────────────────────
    if advisory_schema_version != EXPECTED_ADVISORY_SCHEMA_VERSION:
        raise UpstreamSchemaDriftError(
            f"C14 expects ADVISORY_SCHEMA_VERSION="
            f"{EXPECTED_ADVISORY_SCHEMA_VERSION}; got "
            f"{advisory_schema_version} from upstream C13. "
            f"Coordinate version bump or pin upstream."
        )

    # ── Derive structural inputs ──────────────────────────────────
    placed_room_ids = _derive_placed_room_ids(placement)
    main_entry_room_id = _derive_main_entry_room_id(placement)

    # ── Phase α: graph construction ───────────────────────────────
    topology = construct_graph_topology(
        doors=placement.doors,
        placed_room_ids=placed_room_ids,
        primary_door_ids=frozenset(),  # SKETCH per B-C14-PRIMARY-EDGE-...
        main_entry_room_id=main_entry_room_id,
    )

    # ── Phase β: node metrics ─────────────────────────────────────
    node_metrics = compute_node_metrics(
        topology=topology, main_entry_room_id=main_entry_room_id,
    )

    # ── Phase γ: layout metrics ───────────────────────────────────
    layout_metrics = compute_layout_metrics(
        node_metrics=node_metrics,
        main_entry_room_id=main_entry_room_id,
        nodes=topology.nodes,
    )

    # ── Phase δ-prep: category coverage (used by Phase δ AND ζ) ───
    category_coverage = compute_category_coverage(
        nodes=topology.nodes, metadata=room_metadata,
    )

    # ── Phase δ: flag emission ────────────────────────────────────
    emitted_flags = emit_flags(
        topology=topology,
        node_metrics=node_metrics,
        metadata=room_metadata,
        config=config,
        category_coverage=category_coverage,
        main_entry_room_id=main_entry_room_id,
    )

    # ── Phase ε: advisory passthrough ─────────────────────────────
    advisory_bundle = assemble_advisory_bundle(
        upstream_advisory_flags=placement.advisory_flags,
        structural_flags=emitted_flags.structural_flags,
        preference_flags=emitted_flags.preference_flags,
    )

    # ── Phase ζ: report assembly ──────────────────────────────────
    cache_keys = _build_cache_keys(placement=placement, config=config)
    report = assemble_report(
        source_placed_candidate_signature=signature,
        topology=topology,
        node_metrics=node_metrics,
        layout_metrics=layout_metrics,
        emitted_flags=emitted_flags,
        advisory_bundle=advisory_bundle,
        category_coverage=category_coverage,
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=advisory_schema_version,
        cache_keys=cache_keys,
    )

    return SuccessfulCirculationAnalysis(
        source_placed_candidate_signature=signature,
        report=report,
    )


def _phase_of_error(error: PerCandidateCirculationError) -> str:
    """Map error type → phase for FailureRecord.

    Conservative mapping: errors raised during input derivation or
    Phase α belong to "alpha"; GraphInconsistencyError raised by
    Phase γ assembly belong to "gamma". v0.2 SKETCH uses class-based
    mapping and falls back to "alpha". A precise per-phase exception
    tag is a v0.3 refinement.
    """
    name = type(error).__name__
    if name == "EntryRoomNotFoundError":
        return "alpha"
    if name == "GraphInconsistencyError":
        return "gamma"  # Phase γ raises if metric pipeline misbehaves
    return "alpha"


# =============================================================================
# Public API — single-candidate
# =============================================================================

def analyze_circulation(
    *,
    placement: SuccessfulDoorPlacement,
    room_metadata: tuple[RoomMetadata, ...],
    advisory_schema_version: int,
    config: CirculationConfig | None = None,
    strict_mode: bool = True,
) -> SuccessfulCirculationAnalysis | FailedCirculationAnalysis:
    """Analyze circulation for ONE SuccessfulDoorPlacement.

    Per C14 SPEC v0.2 LOCKED § 5 (STRICT/WARN dispatch) + Inv E1
    (exactly one report per placement) + Inv E16 (provenance triple).

    Inputs:
      placement: one SuccessfulDoorPlacement from C13.
      room_metadata: tuple of RoomMetadata for the rooms in this
        placement (caller responsibility — C14 doesn't have access
        to C12's metadata source).
      advisory_schema_version: from C13's DoorPlacementBatchResult.
        MUST equal EXPECTED_ADVISORY_SCHEMA_VERSION or
        UpstreamSchemaDriftError is raised (LocalCirculationError —
        always halts).
      config: optional CirculationConfig (defaults applied if None).
      strict_mode: True → raise PerCandidateCirculationError;
        False → catch + collect into FailedCirculationAnalysis.

    Returns:
      SuccessfulCirculationAnalysis on success.
      FailedCirculationAnalysis when strict_mode=False and a
        PerCandidateCirculationError occurred.

    Raises:
      UpstreamSchemaDriftError (LocalCirculationError) — always.
      C14ConfigurationError (LocalCirculationError) — always (raised
        by CirculationConfig.__post_init__ for invalid thresholds).
      PerCandidateCirculationError — only when strict_mode=True.
    """
    cfg = config or CirculationConfig()
    try:
        return _run_pipeline(
            placement=placement,
            room_metadata=room_metadata,
            config=cfg,
            advisory_schema_version=advisory_schema_version,
        )
    except PerCandidateCirculationError as e:
        if strict_mode:
            raise
        # WARN-mode: package failure record
        return FailedCirculationAnalysis(
            source_placed_candidate_signature=(
                placement.source_placed_candidate_signature
            ),
            failure_record=FailureRecord(
                candidate_signature=(
                    placement.source_placed_candidate_signature
                ),
                error_type=type(e).__name__,
                error_message=str(e),
                phase=_phase_of_error(e),
            ),
            partial_report=None,
        )


# =============================================================================
# Public API — batch
# =============================================================================

def analyze_circulation_batch(
    *,
    batch: DoorPlacementBatchResult,
    room_metadata_by_signature: dict[str, tuple[RoomMetadata, ...]],
    config: CirculationConfig | None = None,
    strict_mode: bool = True,
) -> CirculationAnalysisBatchResult:
    """Analyze circulation for every SuccessfulDoorPlacement in batch.

    Per C14 SPEC v0.2 LOCKED § 5 (typestate parallels
    DoorPlacementBatchResult).

    Inputs:
      batch: C13's DoorPlacementBatchResult.
      room_metadata_by_signature: dict keyed by
        source_placed_candidate_signature; each value is the
        RoomMetadata tuple for that candidate.
      config: optional CirculationConfig.
      strict_mode: STRICT halts on first per-candidate error; WARN
        collects errors and continues.

    Returns:
      CirculationAnalysisBatchResult with successful/failed tuples
      sorted lex-ASC by signature (Inv E7 byte-equal replay).

    Raises:
      UpstreamSchemaDriftError — always halts (batch + all subsequent
        candidates dropped).
      C14ConfigurationError — always halts.
      PerCandidateCirculationError — only when strict_mode=True.
    """
    cfg = config or CirculationConfig()
    successful: list[SuccessfulCirculationAnalysis] = []
    failed: list[FailedCirculationAnalysis] = []

    for placement in batch.successful:
        sig = placement.source_placed_candidate_signature
        if sig not in room_metadata_by_signature:
            # Missing metadata for this candidate. Treat as
            # GraphInconsistencyError-equivalent: defensive against
            # caller contract drift.
            from .errors import GraphInconsistencyError
            err = GraphInconsistencyError(
                f"No room_metadata provided for candidate {sig!r}."
            )
            if strict_mode:
                raise err
            failed.append(FailedCirculationAnalysis(
                source_placed_candidate_signature=sig,
                failure_record=FailureRecord(
                    candidate_signature=sig,
                    error_type=type(err).__name__,
                    error_message=str(err),
                    phase="alpha",
                ),
                partial_report=None,
            ))
            continue

        result = analyze_circulation(
            placement=placement,
            room_metadata=room_metadata_by_signature[sig],
            advisory_schema_version=batch.advisory_schema_version,
            config=cfg,
            strict_mode=strict_mode,
        )
        if isinstance(result, SuccessfulCirculationAnalysis):
            successful.append(result)
        else:
            failed.append(result)

    # Sort tuples by signature lex-ASC for Inv E7 determinism.
    successful.sort(key=lambda s: s.source_placed_candidate_signature)
    failed.sort(key=lambda f: f.source_placed_candidate_signature)

    return CirculationAnalysisBatchResult(
        successful=tuple(successful),
        failed=tuple(failed),
        c14_version=C14_VERSION,
        c14_metric_version=C14_METRIC_VERSION,
        advisory_schema_version=batch.advisory_schema_version,
    )


__all__ = [
    "analyze_circulation",
    "analyze_circulation_batch",
]
