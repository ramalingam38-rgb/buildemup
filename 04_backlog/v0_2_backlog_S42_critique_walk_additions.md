# v0.2 Backlog — S42 critique-walk additions

**Origin:** S42 external critique walk on C11b S42-shipped code (the 20-item
"genuine drawbacks / risks" document Ramalingam shared mid-S42).

**Verdict distribution (full walk):**
- DOCUMENTED-or-already-BACKLOG: 14 / 20 (items 1, 2, 3, 5, 8, 10, 12, 13, 14, 15, 18, 19, 20; partial 11)
- MISFRAMED-scope: 3 / 20 (items 6, 7, 17 — out-of-scope for C11b v1; belong to C12/C14/KB)
- VALID-BUT-NEW-BACKLOG: 4 / 20 (items 4, 9, 11, 16 — filed below)

**Spec-amendment count: 0.** Per Rule 8 (LOCK authority belongs to
Ramalingam alone), C11b SPEC v1.1 LOCKED is not amended by this walk.
The four new items below are backlog entries, not spec changes.

---

## New backlog items (S42 critique walk)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C11B-PURITY-SPOTCHECK** | Optional runtime evaluator-purity verification loop: periodically re-evaluate a sample of cached/elite candidates and compare hashed outputs; raise `EvaluatorPurityContractError` on mismatch. Currently `EvaluatorPurityContractError` is declared (`errors.py`) but no enforcement loop exists — purity is a contract on the evaluator implementer, not runtime-checked. The class hierarchy is in place; mitigation is opt-in periodic re-evaluation gated by a `purity_spotcheck_frequency: int = 0` config knob (0 = disabled at v1). | S42 critique #4 | When C14 production evaluator integration begins OR when a replay-divergence bug is suspected | S |
| **B-C11B-CANONICAL-GOLDEN-TESTS** | Add a canonical-serialization golden-test corpus + property-based fuzz tests against `_compute_tiebreak_fingerprint`. Also: store the canonical payload (or its sha256) in provenance for post-hoc auditability. The W6-3 `TIEBREAK_FINGERPRINT_SCHEMA_VERSION` anchor catches *intentional* serialization drift; this item adds observability for *unintentional* drift (e.g., a third party silently flips `CANONICAL_FP_PRECISION` between releases). | S42 critique #9 | When `CANONICAL_FP_PRECISION` is touched by any upstream component OR when the first cross-version replay-mismatch is reported in production | S |
| **B-C11B-MEMORY-PRESSURE** | Memory-aware survivor management: compressed candidate storage, evaluator-result deduplication, candidate-vector pools, optional memory-aware truncation. Currently the C11b pipeline retains `pop_size × max_generations` candidate objects in the worst case (offspring+parent pool) plus provenance; at pop_size=100 / max_gen=100 with ~10 rooms each candidate is ~kilobytes, total <100 MB — comfortably below process limits at v1. Trigger is a real-world signal, not a v1 worry. | S42 critique #11 | When measured RAM usage of `run_local_refinement` exceeds 1 GB on production briefs OR when pop_size > 500 / room_count > 50 enters production | M |
| **B-C11B-FAILURE-SCHEMA-V2** | Replace `failure_summaries: tuple[str, ...]` with a structured failure record: `tuple[FailureRecord, ...]` where each `FailureRecord` carries `topology_index: int`, `failure_code: enum`, `subsystem: enum`, `severity: enum`, `message: str`, `cause_type: str`. Enables aggregation, search, classification, and downstream telemetry dashboards. The v1 string form is a known shortcut for shipping speed; structured form is the right shape for observability. | S42 critique #16 | When operations builds C11b failure-analytics tooling OR when production runs produce >100 failures/day requiring batch triage | S-M |

---

## Existing backlog items the critique re-discovered (no action — already filed)

For completeness — these critique items mapped 1:1 to existing
backlog entries:

| Critique # | Existing backlog item(s) | Notes |
|---|---|---|
| 1 (3-obj pathology) | B-NEW-V5 / B-C11B-DOERR-TIEBREAK / B-C11B-HYPERVOLUME-WARN | NSGA-III migration trigger; Doerr 2024 frequency-based tie-break; hypervolume-regression warning |
| 2 (O(N²) sort) | B-C11B-TIER2-SCALING | Bashir 2025 ND-trees; trigger N≥500 or TIER-2 >5min |
| 3 (coarse timeout) | B-C11B-TIMEOUT-V2 + B-C11B-TIMEOUT-COMPLEXITY | Per-evaluation watchdogs + complexity-aware budget |
| 5 (init bias) | B-NEW-V4 | Dirichlet allocation (Zhang et al. 2024) |
| 8 (multi-floor rejection) | B-C11B-MF | Deferred until C12 MF placement OR C14 MF scoring lands |
| 10 (insertion-order tie-break) | B-NEW-Z (deterministic-parallel-NSGA-II) | Layer-3 fallback documented in `selection.py` |
| 12 (replay env-fragile) | B-237 | CI matrix expansion across (NumPy, BLAS, machine) tuples |
| 13 (crowding degeneracy) | B-C11B-DOERR-TIEBREAK + B-NEW-V5 | Doerr 2024 truthful crowding distance |
| 14 (stagnation false-convergence) | (DOCUMENTED only — § 0.8 trade-off; no new item) | Spec acknowledges centroid-variance is an 80% solution; full pairwise every Nth gen is the explicit mitigation |
| 15 (sequential orchestrator) | B-NEW-Z | Deterministic-parallel-NSGA-II |
| 18 (truncation discards diversity) | (DOCUMENTED — `pareto_output_size` configurable) | Novelty archive remains speculative without production signal |
| 19 (scalar constraint aggregation) | (DOCUMENTED — standard NSGA-II-CDP per Deb 2002) | Lexicographic-constraint is post-v1 |
| 20 (provenance schema growth) | B-C11B-PROVENANCE-SPLIT (HIGH priority) | Tightened to "any c11b_version MINOR/MAJOR bump" |

---

## Misframed items — explicit pushback

These three the reviewer asks C11b to do work that the spec already
routes elsewhere:

**Critique #6 (geometric feasibility only area-level):** Spec § 0.2
defines "area-feasible" as `sum(room_area) ≤ envelope_area`, NOT
geometric embeddability. Inv 18 enforces this. Geometric placement is
C12's responsibility (placement layer); C11b refining geometry would
violate the component boundary established at Track 3 design time. Not
a backlog item; not a v2 candidate.

**Critique #7 (only aspect-ratio HARD constraint):** Circulation
width, daylight, wet-zone adjacency, door clearances, structural spans,
ventilation, and privacy are not C11b parameters at v1. Circulation /
adjacency live in C12; daylight / ventilation / structure live in C14
(scoring) or in KB-rule layers. Aspect-ratio is the ONE HARD constraint
that's genuinely a refinement-time concern because it directly bounds
the parameter vector (`width_m`, `depth_m`). Not a backlog item.

**Critique #17 (synthetic evaluator not realistic):** `StubEvaluator`
is explicitly synthetic per spec § 0.5; the whole point of
`EvaluatorProtocol` is structural typing so a real domain evaluator
plugs in without C11b changes. Real evaluators are C14's responsibility
(scoring/critique layer). Calling out StubEvaluator's synthetic-ness is
calling out a feature.
