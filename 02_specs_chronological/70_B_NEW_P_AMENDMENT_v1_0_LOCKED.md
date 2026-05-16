# B-NEW-P amendment — error severity classification — v1.0 **LOCKED**

**Status**: **v1.0 LOCKED** by Ramalingam at S38, 09 May 2026.
**Predecessor**: v0.1 PROPOSED (S38).
**Authored**: S38.
**Required by**: C11a v1.0 LOCKED § 2.7 (severity-tier inversion of
control).

---

## § 0 — What this amendment adds

Each custom error class in C8 / C9 / C10 declares a `severity_tier`
ClassVar with a value in `Literal["per_candidate", "batch", "systemic"]`.
C11a's `DeepMutationPipeline` reads the ClassVar via
`getattr(type(e), "severity_tier", "unknown")` and routes exceptions
accordingly (per C11a § 2.7 catch logic).

No upstream behaviour changes. The ClassVar is read by C11a only;
existing C8/C9/C10 callers ignore it.

---

## § 1 — Scope

**Actual scope: C8 + C9 + C10.** C7 has no custom error classes (raises
stdlib `ValueError` / `KeyError` only); per C11a § 2.7's defensive
default `"unknown"` → systemic, C7's stdlib raises route safely
without code change. Documented for future B-NEW-P-c7classes
backlog work if/when per-candidate routing of C7 errors becomes
needed.

---

## § 2 — Per-class assignment

### C8 (`components/c08/errors.py`)

| Class | severity_tier | Rationale |
|---|---|---|
| `CorridorTooNarrowError` | `per_candidate` | Geometric infeasibility for a single corridor candidate |
| `CorridorSelfIntersectionError` | `systemic` | Programmer-error in dispatcher; halt the batch |
| `CorridorDispatchError` | `per_candidate` | Carries `candidate_index`; per-candidate dispatch failure |

### C9 (`components/c09/errors.py`)

| Class | severity_tier | Rationale |
|---|---|---|
| `RoomSizingError` (base) | `per_candidate` | Conservative default for the base class |
| `PerCandidateError` | `per_candidate` | Aggregated by orchestrator |
| `RoomSizingInfeasibleError` | inherits | Per-candidate (Inv 9 area) |
| `WidthInfeasibleError` | inherits | Per-candidate (Inv 17a) |
| `PackingInfeasibleError` | inherits | Per-candidate (Inv 10 + STRICT) |
| `WidthRiskyError` | inherits | Per-candidate (Inv 17b RISKY) |
| `GridOversizeError` | inherits | Per-candidate (Inv 18 OVERSIZED) |
| `BatchSizingInfeasibleError` | `batch` | All candidates failed; whole-batch error |
| `NBCConfidenceTooLow` | `systemic` | NBC table is shared across candidates; halts |

### C10 (`components/c10/errors.py`)

| Class | severity_tier | Rationale |
|---|---|---|
| `WetZonePlanError` (base) | `per_candidate` | Conservative default for the base class |
| `PerCandidateError` | `per_candidate` | Aggregated by orchestrator |
| `WetZoneInfeasibleError` | inherits | Per-candidate consolidated infeasibility |
| `PreClusteringInfeasibleError` | inherits | Per-candidate Phase 0.5 fail |
| `PoojaAdjacencyError` | inherits | Per-candidate Inv 6 |
| `RiserCountExceededError` | inherits | Per-candidate Inv 8 STRICT |
| `TrapArmDistanceExceededError` | inherits | Per-candidate Inv 11 |
| `WallCapacityExceededError` | inherits | Per-candidate Inv 17 |
| `ClusterIntegrityError` | inherits | Per-candidate Inv 13/14 |
| `BatchWetZoneInfeasibleError` | `batch` | All candidates failed; whole-batch error |
| `PlumbingConfidenceTooLow` | `systemic` | KB-shared confidence; halts |
| `KBVersionMismatchError` | `systemic` | KB-version drift; halts |
| `RemediationGraphError` | `systemic` | Phase 5 mutex graph bug; halts |

---

## § 3 — Tests

`tests/test_severity_tier_classification.py` — **65 tests, all
passing**.

---

## § 4 — Backlog filed

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-NEW-P-runtime-audit** | Extend C11a predicate-registry audit to verify all upstream error classes have valid `severity_tier` at C11a startup, not only static type-check time | post-launch | XS |
| **B-NEW-P-enum** | Migration consideration — convert `_SeverityTier` from `Literal` to `StrEnum` for runtime introspection | post-launch | XS |
| **B-NEW-P-c7classes** | Introduce custom C7 error classes (e.g., `GridGenerationError`) to replace stdlib raises with proper `severity_tier` annotations | when per-candidate routing of C7 errors becomes needed | S-M |

---

## § 5 — LOCK authority

**LOCKED v1.0 by Ramalingam at S38, 09 May 2026.**

---

**End of B-NEW-P v1.0 LOCKED.**
