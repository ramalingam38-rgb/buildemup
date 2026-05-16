"""
BuildemUp — Component 12 — provenance
======================================

Per C12 SPEC v1.0 LOCKED v0.3-A7 (operator class lineage preservation)
+ v0.6 governance.

PlacementProvenance bundles per-batch run metadata:
- env_fingerprint (C12 + inherited C11b hash)
- cache_key
- algorithm path (which slicing-tree cuts were taken, summarized)
- failure traces (cross-references to FailureRecord)
- timing info (wallclock)

Per B-C12-PROVENANCE-SPLIT (Walk #4 Item 9 backlog): in a future
amendment, provenance will split into ReplayProvenance +
OperationalTelemetry + DiagnosticWarnings. v1 ships the unified
struct because the splits aren't yet justified by production data.

DESIGN NOTE: PlacementProvenance is NOT added as a field on
PlacementBatchResult (which is LOCKED schema at v1.0). It's a
parallel data structure returned alongside the batch result via
``place_and_align_with_provenance()``. This keeps the v1.0 LOCKED
schema immutable while still shipping the production-useful
metadata surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .env_fingerprint import C12EnvironmentFingerprint
from .schema import FailureRecord


@dataclass(frozen=True)
class CandidateProvenanceEntry:
    """Per-candidate provenance details.

    Captures what happened to ONE candidate during the batch:
    success or failure, timing, algorithm path summary.
    """
    candidate_signature: str
    outcome: str  # "success" | "failure"
    wallclock_seconds: float
    phase_reached: str  # last phase reached (phase1, phase2, ...)
    n_rooms: int
    failure_record: FailureRecord | None = None


@dataclass(frozen=True)
class PlacementProvenance:
    """Per-batch run metadata.

    Returned alongside PlacementBatchResult by
    ``place_and_align_with_provenance()``. The standard
    ``place_and_align()`` entry point does NOT emit provenance
    (zero-overhead default).

    Fields:
      - c12_version: from versioning module (cross-check vs
        PlacementBatchResult.c12_version)
      - env_fingerprint: full C12EnvironmentFingerprint
      - cache_key: same as PlacementBatchResult.cache_key
      - total_wallclock_seconds: batch end-to-end timing
      - candidates: per-candidate provenance entries
      - failures: cross-reference to FailureRecord tuple
    """
    c12_version: str
    env_fingerprint: C12EnvironmentFingerprint
    cache_key: str
    total_wallclock_seconds: float
    candidates: tuple[CandidateProvenanceEntry, ...]
    failures: tuple[FailureRecord, ...]

    def __post_init__(self) -> None:
        if not self.c12_version:
            raise ValueError("PlacementProvenance.c12_version must be non-empty.")
        if not self.cache_key:
            raise ValueError("PlacementProvenance.cache_key must be non-empty.")
        if self.total_wallclock_seconds < 0:
            raise ValueError(
                f"PlacementProvenance.total_wallclock_seconds must be >= 0; "
                f"got {self.total_wallclock_seconds}."
            )


__all__ = [
    "CandidateProvenanceEntry",
    "PlacementProvenance",
]
