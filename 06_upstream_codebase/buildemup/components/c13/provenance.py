"""
BuildemUp — Component 13 — provenance
======================================

Per C13 SPEC v1.0 LOCKED § 10 + v0.4 C7 (pipeline conventions
documentation — typestate at v2.0+, mixed-result for pre-v2.0).

DoorPlacementProvenance bundles per-batch run metadata:
- c13_version + edge_protocol_version + advisory_schema_version
- cache_key (same as DoorPlacementBatchResult.cache_key)
- total_wallclock_seconds (batch end-to-end timing)
- candidates: tuple of CandidateProvenanceEntry (per-candidate
  outcome, phase reached, timing, door + advisory counts, optional
  failure record cross-reference)

Per v0.6 governance pattern (mirrored from C12): provenance is
shipped via a SEPARATE entry point `place_doors_with_provenance()`.
The LOCKED `DoorPlacementBatchResult` schema is NOT mutated.
Production code that does NOT need provenance uses `place_doors()`
(zero-overhead default).

Per Inv D7 byte-equal replay: per-candidate ordering is canonical
(lex-ASC by candidate_signature) so two provenance runs on the same
batch produce identical metadata structures (modulo wallclock).

NOTE on wallclock timing: wallclock fields are NOT cache-relevant.
Inv D7 (byte-equal replay) does NOT apply to timing values — they
are operational/observability data. Two replay runs may show
different wallclock_seconds; structural equality testing must
explicitly exclude these fields.

Per B-C13-PROVENANCE-SPLIT (filed for v1.x post-LOCK): in a future
amendment, provenance will split into ReplayProvenance +
OperationalTelemetry + DiagnosticWarnings. v1 ships the unified
struct because the splits aren't yet justified by production data
(same rationale as C12's B-C12-PROVENANCE-SPLIT).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .config import DoorPlacementConfig
from .errors import LocalPlacementError, PerCandidatePlacementError
from .orchestrator import (
    _build_failure_record,
    _classify_error_phase,
    _place_one,
    _resolve_entry_room_id,
)
from .schema import (
    DoorPlacementBatchResult,
    FailedDoorPlacement,
    FailureRecord,
    SuccessfulDoorPlacement,
)
from .telemetry import C13TelemetrySink, NullTelemetrySink
from .cache_keys import build_c13_cache_keys
from .versioning import (
    ADVISORY_SCHEMA_VERSION,
    C13_EDGE_PROTOCOL_VERSION,
    C13_VERSION,
)


# =============================================================================
# Per-candidate provenance entry
# =============================================================================

@dataclass(frozen=True)
class CandidateProvenanceEntry:
    """Per-candidate run metadata.

    Captures what happened to ONE candidate during the batch:
    success or failure, timing, last phase reached, output counts.

    Per Inv D7 caveat: wallclock_seconds is NOT cache-relevant or
    replay-deterministic. Structural equality must exclude this
    field.

    Fields:
      candidate_signature: provenance back to the source PlacedCandidate.
      outcome: "success" or "failure".
      wallclock_seconds: per-candidate timing (NOT replay-deterministic).
      phase_reached: last phase touched by the pipeline. For
          success: always "phaseF" (verification cleared). For
          failure: the phase that surfaced the error (per
          C13Phase enum from schema).
      n_rooms: count of rooms in the source PlacedCandidate.
      n_doors_placed: count of doors in the final placement
          (0 if failure).
      n_advisory_flags: count of advisory flags emitted (0 if
          failure surfaced before Phase B).
      failure_record: cross-reference to the FailureRecord present
          in DoorPlacementBatchResult.failed (None if outcome ==
          "success").
    """
    candidate_signature: str
    outcome: str
    wallclock_seconds: float
    phase_reached: str
    n_rooms: int
    n_doors_placed: int
    n_advisory_flags: int
    failure_record: Optional[FailureRecord] = None

    def __post_init__(self) -> None:
        if not self.candidate_signature:
            raise ValueError(
                "CandidateProvenanceEntry.candidate_signature must be non-empty."
            )
        if self.outcome not in ("success", "failure"):
            raise ValueError(
                f"CandidateProvenanceEntry.outcome must be 'success' or "
                f"'failure'; got {self.outcome!r}."
            )
        if self.wallclock_seconds < 0:
            raise ValueError(
                f"CandidateProvenanceEntry.wallclock_seconds must be >= 0; "
                f"got {self.wallclock_seconds}."
            )
        # Inv: failure_record present iff outcome == "failure".
        if self.outcome == "failure" and self.failure_record is None:
            raise ValueError(
                "CandidateProvenanceEntry.failure_record required when "
                "outcome == 'failure'."
            )
        if self.outcome == "success" and self.failure_record is not None:
            raise ValueError(
                "CandidateProvenanceEntry.failure_record must be None "
                "when outcome == 'success'."
            )


# =============================================================================
# Batch-level provenance
# =============================================================================

@dataclass(frozen=True)
class DoorPlacementProvenance:
    """Per-batch run metadata.

    Returned alongside DoorPlacementBatchResult by
    `place_doors_with_provenance()`. The standard `place_doors()`
    entry point does NOT emit provenance (zero-overhead default —
    matches C12 precedent + v0.1 § 10).

    Fields:
      c13_version: captured C13_VERSION at run time. Cross-check
          against DoorPlacementBatchResult.c13_version.
      c13_edge_protocol_version: captured at run time. Cross-check
          against DoorPlacementBatchResult.c13_edge_protocol_version.
      advisory_schema_version: captured at run time. Cross-check
          against DoorPlacementBatchResult.advisory_schema_version.
      cache_key: same as DoorPlacementBatchResult.cache_key
          (cross-check on identity).
      total_wallclock_seconds: batch end-to-end timing.
          NOT replay-deterministic — exclude from structural equality.
      candidates: per-candidate provenance entries, sorted lex-ASC
          by candidate_signature for canonical replay ordering.
      n_successful: count of SuccessfulDoorPlacement in the batch.
      n_failed: count of FailedDoorPlacement in the batch.
    """
    c13_version: str
    c13_edge_protocol_version: int
    advisory_schema_version: int
    cache_key: str
    total_wallclock_seconds: float
    candidates: tuple[CandidateProvenanceEntry, ...]
    n_successful: int
    n_failed: int

    def __post_init__(self) -> None:
        if not self.c13_version:
            raise ValueError(
                "DoorPlacementProvenance.c13_version must be non-empty."
            )
        if not self.cache_key:
            raise ValueError(
                "DoorPlacementProvenance.cache_key must be non-empty."
            )
        if self.total_wallclock_seconds < 0:
            raise ValueError(
                f"DoorPlacementProvenance.total_wallclock_seconds must be "
                f">= 0; got {self.total_wallclock_seconds}."
            )
        if self.n_successful < 0 or self.n_failed < 0:
            raise ValueError(
                f"DoorPlacementProvenance counts must be >= 0; got "
                f"n_successful={self.n_successful}, n_failed={self.n_failed}."
            )
        # Inv: candidates sorted lex-ASC by candidate_signature.
        sigs = [c.candidate_signature for c in self.candidates]
        if sigs != sorted(sigs):
            raise ValueError(
                f"DoorPlacementProvenance.candidates must be sorted "
                f"lex-ASC by candidate_signature; got {sigs}."
            )
        # Inv: success + failure counts match candidates breakdown.
        success_count = sum(
            1 for c in self.candidates if c.outcome == "success"
        )
        failure_count = sum(
            1 for c in self.candidates if c.outcome == "failure"
        )
        if success_count != self.n_successful:
            raise ValueError(
                f"DoorPlacementProvenance.n_successful={self.n_successful} "
                f"disagrees with candidates count {success_count}."
            )
        if failure_count != self.n_failed:
            raise ValueError(
                f"DoorPlacementProvenance.n_failed={self.n_failed} "
                f"disagrees with candidates count {failure_count}."
            )


# =============================================================================
# Public API: place_doors_with_provenance
# =============================================================================

def place_doors_with_provenance(
    *,
    placed_candidates: Iterable,
    config: DoorPlacementConfig,
    c12_cache_key: str,
) -> tuple[DoorPlacementBatchResult, DoorPlacementProvenance]:
    """C13 entry point with provenance.

    Same semantics as `place_doors()` but additionally returns a
    DoorPlacementProvenance carrying per-candidate timing + phase +
    outcome metadata.

    Per v0.1 § 10 + v0.4 C7. Provenance shipping mirrors C12's
    `place_and_align_with_provenance()` precedent.

    Args:
      placed_candidates: iterable of C12 PlacedCandidate (duck-typed).
      config: DoorPlacementConfig.
      c12_cache_key: PlacementBatchResult.cache_key from C12.

    Returns:
      (DoorPlacementBatchResult, DoorPlacementProvenance) tuple.
      The batch result is identical to what `place_doors()` would
      return for the same inputs (modulo wallclock-driven differences
      which are not output-defining — cache_key + door content are
      deterministic).

    Raises:
      Same as place_doors() — UpstreamSchemaDriftError always halts,
      C13ConfigurationError always halts, PerCandidatePlacementError
      only in strict_mode=True.
    """
    raw_sink = config.telemetry_sink
    if raw_sink is None:
        telemetry_sink: C13TelemetrySink = NullTelemetrySink()
    else:
        telemetry_sink = raw_sink  # type: ignore[assignment]

    cache_keys = build_c13_cache_keys(
        config=config,
        upstream_c12_cache_key=c12_cache_key,
    )

    # Materialize once so we can iterate twice without re-consuming.
    candidate_list = list(placed_candidates)

    successes: list[SuccessfulDoorPlacement] = []
    failures: list[FailedDoorPlacement] = []
    candidate_entries: list[CandidateProvenanceEntry] = []

    batch_start = time.monotonic()

    for placed_candidate in candidate_list:
        cand_start = time.monotonic()
        # Best-effort signature for failure attribution.
        sig = getattr(
            placed_candidate, "source_refined_candidate_signature",
            "unknown_candidate",
        )
        n_rooms = len(getattr(placed_candidate, "placed_rooms", ()))
        try:
            result = _place_one(
                placed_candidate, config, cache_keys, telemetry_sink,
            )
            cand_wallclock = time.monotonic() - cand_start
            if isinstance(result, SuccessfulDoorPlacement):
                successes.append(result)
                candidate_entries.append(CandidateProvenanceEntry(
                    candidate_signature=sig,
                    outcome="success",
                    wallclock_seconds=cand_wallclock,
                    phase_reached="phaseF",
                    n_rooms=n_rooms,
                    n_doors_placed=len(result.doors),
                    n_advisory_flags=len(result.advisory_flags),
                    failure_record=None,
                ))
            else:
                # FailedDoorPlacement from WARN-mode Phase F.
                failures.append(result)
                candidate_entries.append(CandidateProvenanceEntry(
                    candidate_signature=sig,
                    outcome="failure",
                    wallclock_seconds=cand_wallclock,
                    phase_reached=result.failure_record.phase,
                    n_rooms=n_rooms,
                    n_doors_placed=len(result.partial_doors),
                    n_advisory_flags=len(result.partial_advisory_flags),
                    failure_record=result.failure_record,
                ))
        except LocalPlacementError:
            # Always halt; provenance is incomplete and not returned.
            raise
        except PerCandidatePlacementError as e:
            cand_wallclock = time.monotonic() - cand_start
            if config.strict_mode:
                raise
            failure_record = _build_failure_record(sig, e)
            failed = FailedDoorPlacement(
                source_placed_candidate_signature=sig,
                failure_record=failure_record,
                partial_doors=(),
                partial_advisory_flags=(),
            )
            failures.append(failed)
            candidate_entries.append(CandidateProvenanceEntry(
                candidate_signature=sig,
                outcome="failure",
                wallclock_seconds=cand_wallclock,
                phase_reached=failure_record.phase,
                n_rooms=n_rooms,
                n_doors_placed=0,
                n_advisory_flags=0,
                failure_record=failure_record,
            ))

    total_wallclock = time.monotonic() - batch_start

    successes.sort(key=lambda s: s.source_placed_candidate_signature)
    failures.sort(key=lambda f: f.source_placed_candidate_signature)
    candidate_entries.sort(key=lambda e: e.candidate_signature)

    batch_result = DoorPlacementBatchResult(
        successful=tuple(successes),
        failed=tuple(failures),
        c13_version=C13_VERSION,
        c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
        advisory_schema_version=ADVISORY_SCHEMA_VERSION,
        cache_key=cache_keys.full_cache_key,
    )

    provenance = DoorPlacementProvenance(
        c13_version=C13_VERSION,
        c13_edge_protocol_version=C13_EDGE_PROTOCOL_VERSION,
        advisory_schema_version=ADVISORY_SCHEMA_VERSION,
        cache_key=cache_keys.full_cache_key,
        total_wallclock_seconds=total_wallclock,
        candidates=tuple(candidate_entries),
        n_successful=len(successes),
        n_failed=len(failures),
    )

    return batch_result, provenance


__all__ = [
    "CandidateProvenanceEntry",
    "DoorPlacementProvenance",
    "place_doors_with_provenance",
]
