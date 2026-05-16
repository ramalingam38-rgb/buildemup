# AUDIT CHECK — S37 spec-compliance line-by-line

**Authored at**: S37 close handoff assembly.

## C11a v1.0 LOCKED — spec audit

| Item | Expected | Actual | Status |
|---|---|---|---|
| File location | `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md` | present | ✓ |
| LOCKED banner | top-of-file HTML comment block | present | ✓ |
| 16 mutation operators (M0_BASE through M9D_ENTRY_OFF) | enum complete | confirmed in § 2.1 | ✓ |
| 30 invariants (Inv 1-30) | all numbered | confirmed in § 4 | ✓ |
| Two-tier execution architecture | Tier A + Tier B + DeepMutationPipeline | § 0 + § 3.4 + § 3.5 | ✓ |
| `MutationLegalityResponsibilityMatrix` | C5/C7/C8/C9/C10 ownership | § 0.4 | ✓ |
| `UpstreamAmendmentWaiver` mechanism | max 3 active at LOCK | § 0.2 + Inv 24 | ✓ |
| `DeltaKey` enum | 18 entries hierarchical | § 2.5 | ✓ |
| `QuarantineFingerprint` + replay rule | Inv 29 | § 2.9 | ✓ |
| `severity_tier` ClassVar inversion | requires B-NEW-P | § 2.7 | ✓ |
| `MutationLineageDepth` enum | SHALLOW/REGEN/EMERGENT | § 2.3 | ✓ |
| `PurityAttestation` + UPSTREAM_PURITY_REGISTRY | source-constant | § 0.1 | ✓ |
| Single-threaded contract at v1 | Inv 30 | § 0.3 (concurrency) | ✓ |
| F-v5-2 patch (META_* keys clarified) | applied inline | confirmed in § 2.5 | ✓ |
| F-v5-3 patch (per-field cache discipline scoped) | applied inline | confirmed in § 6 | ✓ |
| Test target ~205 (post-patches) | numeric reconciled | § 6 says 2314+205≈2519 | ✓ |

## C11b v1.0 LOCKED — spec audit

| Item | Expected | Actual | Status |
|---|---|---|---|
| File location | `02_specs_chronological/69_C11b_SPEC_v1_0_LOCKED.md` | present | ✓ |
| LOCKED banner | top-of-file HTML comment block | present | ✓ |
| NSGA-II-CDP algorithm | Deb 2002 standard | § 0.5 | ✓ |
| 25 invariants (Inv 1-25) | all numbered | § 4 | ✓ |
| `EvaluatorProtocol` minimal contract | 1 method + PurityAttestation + identity/version hashes | § 0.4 / § 0.7 | ✓ |
| `StubEvaluator` geometry-correlated | compactness/aspect_variance/envelope_efficiency | § 0.5 (revised v0.2) | ✓ |
| Feasibility-aware sequential allocation | 3 permutations per candidate | § 0.7 (revised v0.3) | ✓ |
| `StagnationConfig` adaptive cadence | O(N) every gen, full O(N²) every 5 gens | § 0.8 | ✓ |
| `output_sequence_is_quality_ranked: bool` always False at v1 | § 0.9 | ✓ |
| `DominanceSorterProtocol` abstraction | sort only, doc'd scope | § 0.10 | ✓ |
| `EnvironmentFingerprint` extended | + c11b_version + numpy_blas_info_summary | § 0.3 | ✓ |
| `MAX_ROOM_ASPECT_RATIO=3.0` HARD via CDP | Inv 22 | § 0.6 | ✓ |
| `SEMANTIC_CAP_BY_CATEGORY` | bathroom 1.8×, kitchen 1.5× | § 0.6 | ✓ |
| Test target ~190 | numeric reconciled | § 6 says 2519+190≈2709 | ✓ |

## Item-7 patch on C10 — spec compliance

| Item | Expected | Actual | Status |
|---|---|---|---|
| Patch site | `_build_fixture_types_per_room` | confirmed in patched file | ✓ |
| New behaviour | raises `KBVersionMismatchError` chained from `KeyError` | confirmed | ✓ |
| New tests | `TestStrictFallbackRemoval` class | confirmed in test file | ✓ |
| Test count | 2312 → 2314 | matches Phase 0 baseline | ✓ |

## Backlog enumeration audit

| Source | Count expected | Count documented | Status |
|---|---|---|---|
| C11a additions (W#1 + W#2 + W#3 + W#4 + W#5) | 18 (incl 4 upstream) | 18 in S37 backlog file | ✓ |
| C11b additions (W#1 + W#2 + W#3) | 10 | 10 in S37 backlog file | ✓ |
| Pre-existing carries (B-217, B-220, B-237, B-238) | listed | listed | ✓ |
| Waiver flag for B-NEW-J/K/L/P (4 vs cap of 3) | flagged | flagged with recommendation | ✓ |

## Verdict
**ALL SPEC-COMPLIANCE CHECKS PASS.**

Notable: 4-vs-3 waiver cap reconciliation is documented but unresolved
— this is by design (Ramalingam decision needed at S38 open).
