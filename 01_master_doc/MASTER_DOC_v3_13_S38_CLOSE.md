# MASTER DOC v3.13 — S38 CLOSE — FINAL

**Predecessor**: v3.12 (S37 close).
**Authored**: S38 close, May 9 2026.
**Scope**: complete S38 — Path α adjudication, 4 upstream amendments
LOCKED v1.0 (incl. K-4 patch), C11a Sub-session 1 shipped, 4 critique
walks consumed.

---

## § 1 — Status snapshot

| Metric | S37 close | **S38 close** | Δ |
|---|---|---|---|
| Components shipped (code) | 10/17 | 10/17 + C11a partial | +partial |
| Test count (excl. e2e) | 2290 / 2 skipped | **2486 / 2 skipped** | **+196** |
| C11a build progress | 0/4 sub-sessions | **1/4 sub-sessions** | +25% |
| Active waivers | 4 (over cap) | **0** | −4 |
| Pending-upstream predicates | 4 | **0** | −4 |
| Inv 24 LOCK gate | FAIL | **PASS** | flipped |
| Open questions | 0 | 0 | — |
| Backlog items | 51 | **59** | +8 (Walks #1-#4) |
| LOCKED amendments (S38) | — | **4** | +4 |

---

## § 2 — Amendments LOCKED v1.0

### B-NEW-P — error severity classification

- **Status**: v1.0 LOCKED at S38, May 9 2026.
- **Scope**: C8 + C9 + C10 custom error classes get `severity_tier:
  ClassVar[Literal["per_candidate","batch","systemic"]]`. C7 not
  in scope (raises stdlib only; defensive default in C11a § 2.7
  routes "unknown" → systemic).
- **Tests**: 65 in `tests/test_severity_tier_classification.py`.
- **Backlog filed**: B-NEW-P-runtime-audit (post-launch),
  B-NEW-P-enum (post-launch), B-NEW-P-c7classes (S-M).

### B-NEW-K — C7 staircase clearance W9 invariant (incl. K-4 patch)

- **Status**: v1.0 LOCKED at S38, May 9 2026. **Patch v0.1 → v0.2 → v1.0
  applied** (K-4: landing depth scales with width per NBC).
- **Scope**: `Staircase` frozen dataclass + `Grid.staircase` field
  (default None, backwards-compat) + W9 4-sub-condition invariant
  + `validate_staircase_clearance` predicate.
- **W9-b (post K-4)**: `landing_depth_m >= max(width_m,
  MIN_STAIRCASE_LANDING_DEPTH_M)`.
- **Tests**: 27 in `tests/test_c7_staircase_w9.py` (includes 5
  K-4-specific).
- **Backlog filed**: B-NEW-K-impl (post-launch GridGenerator
  integration), B-NEW-K-shape (post-launch climb_direction etc),
  B-NEW-K-egress (post-launch C9/C10 integration).

### B-NEW-L — C8 entry approach Inv 21

- **Status**: v1.0 LOCKED at S38, May 9 2026.
- **Scope**: `validate_entry_approach` predicate exposed via
  `components/c08/validator.py`. Cardinal facings require single edge;
  intercardinal facings accept either of two adjacent edges.
- **Design discipline**: Inv 21 is C11a Tier A predicate ONLY —
  `validate_corridor_path` does NOT call it.
- **Tests**: 21 in `tests/test_c8_inv21_entry_approach.py`.
- **Backlog filed**: B-NEW-L-rotated, B-NEW-L-multi-entry.

### B-NEW-J — C5 privacy zoning rule (with override at launch-complement)

- **Status**: v1.0 LOCKED at S38, May 9 2026. **B-NEW-J-override
  escalated to launch-complement** (Walk #2 + Walk #4 finding).
- **Scope**: `validate_privacy_zoning(zone_bands, plot_facing)` in
  `components/c05/zone_bands.py`. Cardinal facings forbid single
  cardinal; intercardinal facings forbid 3-direction set
  (intercardinal + adjacent cardinals).
- **Smoke test verified**: all 32 default zone_bands × facing
  combinations from C5's `default_zone_bands(kind, facing)` pass —
  C5's existing design is internally consistent.
- **Tests**: 22 in `tests/test_c5_privacy_zoning.py`.
- **Backlog filed**: **B-NEW-J-override** (launch-complement, not
  deferred indefinitely; must ship same release window as C11a
  production), B-NEW-J-roomlevel, B-NEW-J-acoustic.

---

## § 3 — Critique walks summary

Four walks completed; full responses in
`02_specs_chronological/74-77_*.md`.

| Walk | Verdicts | New backlog | New v1.0 changes |
|---|---|---|---|
| #1 | 11 + 1 self-surfaced (K-4) | 5 items | 0 (K-4 deferred to round 2) |
| #2 | 12 + 2 corrections to W#1 | 4 items | 0 |
| #3 | 13 + 1 correction to W#2 | 2 (consolidated from 6) | 0 |
| #4 | 13 endorsements + 1 metadata adjust | 0 | 0 |

**Total new backlog from S38 walks**: ~8 items (8 distinct IDs
filed; some absorbed into B-meta-rule-taxonomy).

The Walk #4 reviewer endorsed Walk #3's convergence-recognition.
**The K-4 patch was quadruply corroborated** before adjudication.

---

## § 4 — C11a build state

### Sub-session 1 (S38) — SHIPPED

- `components/c11a/schema.py` — 16 operators, 2 tiers, 9 families,
  20 DeltaKeys, 3 family transition policies, MutationOperatorMetadata,
  MutationLineageDepth (3), PurityAttestation + 3-entry registry,
  UpstreamAmendmentWaiver + empty registry, MutationViabilityPredicate,
  QuarantineFingerprint, TopologyMutationConfig (11 fields, all carry
  `cache_relevant` metadata per Inv 26), EnforcementMode,
  ProvenanceVerbosity, RegistryValidationMode, FamilySlotAllocation,
  MutationDiagnostics, MutationApplicationResult.
- `components/c11a/errors.py` — full hierarchy with `severity_tier`
  ClassVars: TopologyMutationError → PerCandidateError → 3 subclasses;
  BatchAllNonBaseFailedError; OperatorRegistryError,
  DeepMutationPurityContractError, PendingUpstreamPredicateError,
  SeverityClassificationAuditError, InvariantViolationError.
- `components/c11a/provenance.py` — TopologyMutationProvenance +
  MutatedTopologyCandidate with v1-invariant `__post_init__` guards
  (single operator, consistent op-vs-result).
- `components/c11a/__init__.py` — 33 public names re-exported.
- `tests/test_c11a/test_c11a_subsession1_schema.py` — **61 tests**:
  enum coverage, family-policy table coverage, DeltaKey namespacing,
  registry shape, dispatch pattern verification, dataclass invariants,
  spec-counts self-consistency.

### Sub-sessions 2, 3, 4 — PENDING

Per CODING_MANDATE Step 2:
- **Sub-session 2 (S39 NEXT)**: Tier A operators M0/M1/M2/M3a/b/c/M4/
  M5/M9a/b/c/d + per-family slot allocation + operator metadata table
  with concrete DeltaKey schemas + `validate_operator_registry()`
  + Tier A predicate registry binding upstream predicates.
- **Sub-session 3**: Tier B operators (M6/M7a/b/M8) +
  DeepMutationPipeline + caching + lineage classification.
- **Sub-session 4**: full integration; replay tests; quarantine
  fingerprint hashing; purity contract test discipline; final test
  count target.

Cumulative C11a target at LOCK ship: ~205 tests per § 6 v0.5.

---

## § 5 — Inv 24 LOCK gate state at S38 close

```
pending_upstream_predicate_count = 0    (B-NEW-J/K/L/P all LOCKED)
len(active_waivers)               = 0    (WAIVER_REGISTRY = ())
Both clauses of Inv 24 v0.5 PASS.
```

C11a v1.0 LOCK gate is **gate-ready**. Final LOCK of C11a itself
happens after Sub-sessions 2-4 ship a complete `mutate_topologies()`
with passing tests.

---

## § 6 — What remains after S38

| Track | Status |
|---|---|
| C11a v1.0 build | 1 of 4 sub-sessions done |
| C11b v1.0 build | LOCKED spec, 0 of 3 sub-sessions done |
| Pre-launch hard gates | B-220 (hydraulics), B-237 (cross-platform CI), B-238 (architect review), B-150-equiv (NBC primary verification) — all unchanged |
| Other remaining components | C12-C17 + C3b — unchanged |

---

## § 7 — Risks at S38 close

1. **B-NEW-J-override is launch-complement debt** — if C11a v1 ships
   without it, the privacy_zoning predicate biases mutation search
   against legitimate luxury/view typologies. Tracked in B-NEW-J spec
   § 6 + LOCK statement.
2. **Backlog growth** — 8 new items from S38 walks. Per Walk #3+#4
   discipline, consolidated into B-meta-rule-taxonomy where possible.
   Future walks risk accumulating governance debt; B-meta-backlog-roadmap
   filed for periodic consolidation review.
3. **Secondary-source NBC grounding** — B-150-equiv pre-launch hard
   gate covers this; not a v1 LOCK blocker.

---

**End of MASTER DOC v3.13.**
