# C11A SPEC AMENDMENT v1.6 PROPOSED — multi-floor pipeline rework (B-NEW-T3 enabler #4 of 4)

**Component**: 11a (Topology Mutation Orchestration — SHIPPED at v1.0 LOCKED across multiple sessions; 10/17 Track 3 components, structurally complete with 3/4 Tier B operators wired before this amendment).
**Spec status**: **v1.6 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-v1.5 critique walk.
**Driver**: Spec #4 of 4, the largest. Completes the B-NEW-T3 spec sequence.

**v1.6 vs v1.5**: second consecutive doc-polish round (zero behavioral changes, zero algorithm changes). Five documentation patches — cache-vs-exploration identity anti-pattern guard-rail (§ 3.4.1); M8 2-floor-impact-is-optimization-not-invariant callout (§ 3.4); floor-label-as-identity overloading callout (§ 3.7); cross-spec coupling status note pointing to existing governance backlog items (§ 9); post-LOCK spec-restructure plan (§ 9). Three new backlog items (B-C11A-16 generation contract enforcement, B-C11A-17 canonical floor identity primitive, B-C11A-18 spec restructure into appendices). Reviewer's v1.5 verdict: "PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope" — v1.6 addresses the remaining doc-polish items reviewer flagged.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v1.6 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v1_6_LOCKED.md` (if approved as-is),
- `..._v1_7_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

---

## § 0.1 — Delta from v1.1 → v1.2 (critique walk patches)

v1.1 PROPOSED received an external critique with 15 items. Unlike Specs
#1-3's later critique rounds (which were dominated by maturity-signal
observations), this critique surfaced substantive behavioral patches —
v1.1 was a first-round draft and reviewer correctly flagged several real
design gaps. Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| 1 (`_is_multi_floor` duck-typing too permissive) | ACCEPT | § 3.1 — new `_validate_multi_floor_protocol()` pre-flight |
| 2 (master-floor-only freezes non-master topology evolution) | ACCEPT (behavioral change) | § 3.2 + § 3.3 — switch to ALL floors, slot-allocator-limited |
| 3 (deterministic first-eligible M8 = starvation) | ACCEPT (behavioral change) | § 3.4 — hash-based deterministic selection across all eligible targets |
| 4 (family aggregation loses floor-position semantics) | ACCEPT | § 3.7 — preserve label-family pairs (`multi_floor:ground=A\|first=B`) |
| 5 (signature recursion fragile under per-floor changes) | ACCEPT | § 3.5 — explicit `multi_floor_sig_schema=v1` prefix |
| 6 (`type().__name__` brittle) | BACKLOG ONLY | New B-C11A-6 |
| 7 (M8 2-floor assumption misses cross-floor cascades) | BACKLOG ONLY | New B-C11A-7 (gated on Spec #1 B-MFDB-C cross-floor constraints) |
| 8 (cache bump globally coarse-grained) | REJECT | None — already covered by Spec #2 B-C9-C |
| 9 (no brief/source alignment validation) | ACCEPT | § 3.1 — new `_validate_multi_floor_alignment()` pre-flight |
| 10 (lineage under-specified for compound mutations) | PARTIAL ACCEPT | § 3.8 — add `floor_label_affected: str \| None`; full ancestry chain filed as B-C11A-8 |
| 11 (no property/fuzz tests for orchestration invariants) | ACCEPT | § 5.1 — new property-test subsection |
| 12 (M8 failure taxonomy too coarse) | ACCEPT | § 3.4 — `c9_generation_failed` / `c10_validation_failed` / `orchestration_state_drift` |
| 13 (`with_floor_replaced` allocation churn) | BACKLOG ONLY | New B-C11A-9 |
| 14 (floor tuple order not globally canonicalized) | REJECT | None — already covered by Spec #1 B-MFDB-A (intentional design choice per Spec #1 § 3.5) |
| 15 (multi-floor orchestration before adjacency scoring) | REJECT | None — C11b scoring territory, not C11a orchestration |

**Net behavioral delta from v1.1**: TWO behavioral changes (items 2 and 3 above). Both materially affect how the search explores multi-floor candidates. **Net documentation delta**: 7 additional patches (items 1, 4, 5, 9, 10, 11, 12). **5 new backlog items**: B-C11A-5 through B-C11A-9.

Two rejects with reasoning preserved.

**Note on scope**: v1.1 → v1.2 is the largest critique-walk delta in the S40-continuation sequence. Unlike documentation-polish rounds on Specs #1-3, this round genuinely changes search behaviour (item 2 expands per-floor operator coverage, item 3 changes M8 target selection). The reviewer correctly caught two real design defects in the first-round draft.

---

## § 0.2 — Delta from v1.2 → v1.3 (critique walk patches)

v1.2 PROPOSED received a second-round external critique with 15 items. Reviewer caught real algorithmic bugs in v1.2's two behavioral changes — item 1's lex-order truncation creates floor-selection bias toward lower-index floors, and item 2's hash-modulo M8 selection does NOT mathematically guarantee target coverage (only cyclic exploration does). Two consecutive behavioral-change rounds is unusual; reviewer earned every behavioral patch this round.

Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| 1 (slot allocator lex-order bias toward lower floors) | ACCEPT (behavioral) | § 3.2 + § 3.3 — round-robin floor interleaving via `(operator_index, (floor_index + operator_index) mod num_floors)` |
| 2 (hash-modulo M8 selection doesn't guarantee coverage) | ACCEPT (behavioral) | § 3.4 — replace hash-modulo with cyclic `sorted_targets[(generation + operator_index) % N]` |
| 3 (lexical sort doesn't reflect elevation) | PARTIAL — clarification | § 3.7 — document lexical-sort is available-determinism; elevation-canonical ordering gated on Spec #1 B-MFDB-A |
| 4 (protocol validator misses semantic checks) | PARTIAL ACCEPT | § 3.1 — add `len(floor_labels) == len(floors)` check; other semantic checks redundant with Spec #1 invariants |
| 5 (alignment validation too strict on tuple order) | REJECT | None — Spec #1+#3 § 3.5 deliberately make tuple order significant; relaxation gated on B-MFDB-A |
| 6 (generation-dep M8 reproducibility ambiguous) | ACCEPT | § 3.4 + § 4 — separate "structural determinism" from "exploration determinism" |
| 7 (property test guarantees overstated) | ACCEPT | § 5.1.1 — reword as conditional / under successful operators only |
| 8 (lineage `floor_label_affected` insufficient) | REJECT | None — already filed as B-C11A-8 |
| 9 (Tier B all-floor compute amplification) | PARTIAL ACCEPT | § 3.3 — clarify per-attempt cost unchanged; file B-C11A-10 for adaptive Tier B quotas |
| 10 (orchestration + exploration policy mixed) | BACKLOG ONLY | New B-C11A-11 (strategy pattern extraction) |
| 11 (`type().__name__` detection still in spec) | ACCEPT | § 3.5 — use `__multi_floor_candidate__: bool = True` marker attribute; coordinated with Spec #3 build-session class-attribute add (hash-irrelevant implementation detail, does NOT violate Spec #3 LOCK) |
| 12 (`orchestration_state_drift` too broad) | ACCEPT | § 3.4 — refined invariant-specific variants (`orchestration_state_drift:mfwzp5`, etc.) |
| 13 (50 property-test examples too few) | PARTIAL ACCEPT | § 5.1.1 — bump to `max_examples=100`; file B-C11A-12 for nightly stress fuzzing |
| 14 (wrapper rebuild overhead quadratic) | REJECT | None — already filed as B-C11A-9 |
| 15 (no cross-floor consistency boundary) | ACCEPT | New § 3.11 — `affected_floor_set(operator, source)` abstraction |

**Net behavioral delta from v1.2**: TWO behavioral changes (items 1, 2). **Net documentation delta**: 9 additional patches (items 3, 4, 6, 7, 9, 11, 12, 13, 15). **3 new backlog items** (B-C11A-10, 11, 12). **1 backlog closure** (B-C11A-6 marker attribute lands in v1.3 build session). **1 reject** (item 5), **2 already-filed** (items 8, 14).

**Pattern recognition**: this is the second consecutive behavioral-change round on the C11a amendment. v1.1 → v1.2 changed dispatch (master-only → all-floors) and target selection (first-eligible → hash-modulo). v1.2 → v1.3 fixes algorithmic bugs in those v1.2 changes (lex-order bias → round-robin; hash-modulo non-coverage → cyclic). Reviewer correctly diagnosed that v1.2's behavioral changes were on the right axis but the specific algorithms had defects. v1.3's algorithms are mathematically stronger.

**Pattern A check** (the 5 patterns to avoid): items 1 and 2 are NOT bandage fixes on the original v1.2 changes — they replace the v1.2 algorithms entirely with mathematically-sound alternatives. Round-robin and cyclic-modulo are textbook patterns with provable properties (no starvation, deterministic coverage). This is the right shape of fix.

---

## § 0.3 — Delta from v1.3 → v1.4 (critique walk patches)

v1.3 PROPOSED received a third-round external critique with 12 items. Reviewer's overall verdict explicitly named the LOCK gate: "v1.3 is plausibly LOCK-worthy IF: operator-bias limitation is acknowledged explicitly OR full interleaving is added before LOCK. Everything else is reasonable backlog territory rather than pre-LOCK blocker territory." v1.4 implements full interleaving (the reviewer's preferred path; acknowledgment-only would ship a known fairness defect).

Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| 1 (operator-major truncation bias — the LOCK gate) | ACCEPT (behavioral) | § 3.2 + § 3.3 — full bipartite operator+floor interleaving via round-major outer loop |
| 2 (cyclic M8 creates evolutionary periodicity) | BACKLOG ONLY + DOC | § 3.4 acknowledgment; new B-C11A-13 (source-signature-stable-shuffle when C11b coordinates exploration pressure) |
| 3 (structural vs exploration determinism tier-table) | ACCEPT | New § 3.4.1 — explicit determinism tier-table; new B-C11A-14 (generation provenance in lineage) |
| 4 (family-ID lexical-label sensitivity) | REJECT | None — already documented in v1.3 § 3.7; canonical-ordering gated on Spec #1 B-MFDB-A (same dependency as v1.2 critique walk item 3) |
| 5 (multi-floor signature recursion cost) | BACKLOG ONLY | New B-C11A-15 (memoized signature caching) |
| 6 (`affected_floor_set` contract too coarse) | ACCEPT | § 3.11 — structured `FloorImpact` return type with `kind` + `requires_cascade` + `requires_validation_only` |
| 7 (property tests miss long-chain interactions) | PARTIAL ACCEPT | § 5.1.1 — add ONE 50-step stateful chain test in CI; nightly stress fuzzing already filed as B-C11A-12 |
| 8 (orchestration policy entanglement — promote B-C11A-11 before LOCK) | REJECT | None — strategy-pattern extraction is v2 architecture project; pre-LOCK timing is wrong; B-C11A-11 backlog remains |
| 9 (cache versioning coarse-grained) | REJECT | None — third re-raise of same backlog-covered concern (already covered by Spec #2 B-C9-C) |
| 10 (cross-spec invariant coupling needs integration tests) | ACCEPT | § 5.1 — add 3-4 cross-spec integration tests (Spec #1 → C9 → Spec #3 → C11a end-to-end) |
| 11 (M8 master relocation locally sufficient — circulation/adjacency/etc.) | REJECT | None — same concern class as v1.2 item 7 (already filed as B-C11A-7); v1.4 § 3.11 + `FloorImpact` provides the abstraction B-C11A-7 will extend |
| 12 (test descriptions and spec text inconsistencies) | ACCEPT | Terminology pass throughout |

**Net behavioral delta from v1.3**: ONE behavioral change (item 1 — the LOCK gate). **Net documentation/test delta**: 5 patches (items 3, 6, 7, 10, 12). **3 new backlog items** (B-C11A-13, 14, 15). **4 rejects** with reasoning preserved.

**Pattern recognition** (the third behavioral-change round):
- v1.1 → v1.2 changed dispatch + target selection.
- v1.2 → v1.3 fixed algorithmic correctness of v1.2's changes.
- v1.3 → v1.4 generalizes v1.3's fairness from floor-axis-only to bipartite operator+floor-axis.

This is a refinement chain, not a bandage chain. Each round replaces the previous algorithm with a mathematically-stronger one. Pattern-A check holds: v1.4's bipartite interleaving is a clean replacement of v1.3's operator-major loop, not a patch on top of it. Same complexity class (two nested loops), cleaner fairness property (**bounded imbalance ≤ 1, starvation-free** across both axes under truncation — see v1.5 wording correction in § 0.4 item 2).

**Convergence projection**: reviewer's verdict ("Everything else is reasonable backlog territory rather than pre-LOCK blocker territory") strongly suggests v1.4 is the final pre-LOCK round if item 1's bipartite interleaving holds up under a fourth-round critique. Three consecutive behavioral-change rounds is unusual; the spec is now at the point where remaining concerns are policy / governance / long-term evolution rather than algorithmic correctness.

---

## § 0.4 — Delta from v1.4 → v1.5 (critique walk patches)

v1.4 PROPOSED received a fourth-round external critique with 15 items. Reviewer's overall verdict explicitly named the two pre-LOCK issues: "**REAL PRE-LOCK ISSUES REMAINING: 1. `affected_floor_set()` semantic overload. 2. fairness wording overstated. Everything else is plausibly backlog-grade.**" Reviewer also gave the cleanest convergence signal yet: "Convergence assessment: VERY HIGH. Most likely trajectory: v1.5 PROPOSED, then LOCK."

Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| 1 (`affected_floor_set` API semantic overload — PRE-LOCK #1) | ACCEPT | § 3.11 — split into `direct_floor_label` + `new_master_floor_label` kwargs with mutual-exclusion validation |
| 2 (fairness wording "uniform" overstated — PRE-LOCK #2) | ACCEPT | § 3.2 + § 3.3 + § 4 + § 0.3 — replace "uniform under truncation" with "bounded imbalance ≤ 1, starvation-free" + explicit fairness theorem |
| 3 (partial-round positional advantage exists) | REJECT | None — reviewer-recommended Option A (accept bounded imbalance + document), which is exactly item 2's outcome; Options B + C filed as B-C11A-13 + future exploration-policy work |
| 4 (family-ID vs wrapper semantic divergence) | ACCEPT | § 3.7 — explicit semantic-divergence callout; rename suggestion rejected (term is entrenched across C11a codebase, doc is sufficient) |
| 5 (cyclic coverage test off-by-one) | ACCEPT | § 5.1 test #5 + § 5.1.1 test #23 + § 5.1 test #28 — N = `len(eligible_targets) = num_floors − 1` (or fewer if non-master floors lack bedrooms) |
| 6 (root-cause precision overstated in drift taxonomy) | ACCEPT | § 3.4 — caveat paragraph: invariant-specific variants narrow class, do NOT uniquely identify root cause |
| 7 (cyclic M8 periodicity) | REJECT | None — already filed as B-C11A-13 (reviewer-acknowledged) |
| 8 (M8 cross-floor cascade direct-only assumption) | REJECT | None — already addressed via v1.4's `FloorImpact`; remaining work belongs to B-C11A-7 (reviewer-acknowledged) |
| 9 (property tests can't prove evolutionary stability) | REJECT | None — already filed as B-C11A-12 (reviewer-acknowledged "Not pre-LOCK") |
| 10 (signature recursion cost) | REJECT | None — already filed as B-C11A-15 (reviewer-acknowledged) |
| 11 (wrapper rebuilding allocation churn) | REJECT | None — already filed as B-C11A-9 (reviewer-acknowledged) |
| 12 (orchestration policies hard-wired) | REJECT | None — already filed as B-C11A-11 (reviewer-acknowledged "Architecture-evolution concern only") |
| 13 (generation semantics critical global state, contract under-specified) | ACCEPT | New § 3.4.2 — explicit generation contract: lifecycle ownership, monotonicity guarantees, replay semantics, reset semantics |
| 14 (state-space explosion) | REJECT | None — reviewer-acknowledged "Expected evolutionary-system tradeoff"; filed B-C11A-5 + B-C11A-10 + C11b future work |
| 15 (mixed detection — marker + name-based) | REJECT | None — already filed as B-C11A-6 (reviewer-acknowledged "partially addressed") |

**Net delta from v1.4**: ZERO behavioral changes. **6 spec patches** (items 1, 2, 4, 5, 6, 13). **0 new backlog items** (all backlog-applicable items were already filed in previous rounds). **9 rejects** with reasoning preserved.

**Pattern recognition** (the first non-behavioral round since v1.1): the three-consecutive-behavioral-change run (v1.1 → v1.2 → v1.3 → v1.4) is over. Reviewer's algorithmic-correctness analysis has reached its natural endpoint: bipartite interleaving + cyclic M8 selection are mathematically sound; remaining concerns are contract precision (item 1), wording precision (item 2), conceptual clarification (items 4, 6, 13), and one test off-by-one (item 5). This matches the convergence pattern Specs #1, #2, #3 hit at their LOCK points — substantive rounds first, then a documentation-polish round, then LOCK.

**Pattern-A check**: zero algorithm changes in v1.5; all six patches are documentation, contract clarification, or test correction. No bandage opportunities.

---

## § 0.5 — Delta from v1.5 → v1.6 (critique walk patches)

v1.5 PROPOSED received a fifth-round external critique with 12 items. Reviewer's overall verdict: "**PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope. But: not yet 'future-proof at NSGA-II scale'.**" The framing is correct — every remaining concern reviewer raised is qualified by "for v1" vs "at NSGA-II scale." Reviewer's five named remaining concerns ("(1) deterministic fairness bias accumulation, (2) cyclic exploration resonance, (3) orchestration centralization, (4) shallow lineage provenance, (5) high cross-spec coupling") are ALL backlog-tracked items with appropriate triggers (NSGA-II / C11b / scale-related).

Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| 1 (operator fairness bias accumulation across generations) | REJECT spec change | Sharpen B-C11A-13 description in § 10 to capture reviewer's three concrete option proposals (operator-start rotation, stable-shuffle, per-generation offset). Reviewer-acknowledged: "Severity: MEDIUM-HIGH. Not a correctness bug. Potential long-term search-diversity degradation bug." Three consecutive behavioral-change rounds already done; pulling a fourth pre-NSGA-II is scope creep. |
| 2 (cyclic M8 resonance under population) | REJECT — already filed | None — B-C11A-13 already covers this. Reviewer-acknowledged: "The spec acknowledges it but defers to B-C11A-13. Severity: HIGH once NSGA-II lands. LOW-MEDIUM before population search exists." |
| 3 (generation contract under-enforced) | BACKLOG ONLY | New B-C11A-16 — optional validation-mode (monotonicity / duplicate-detection / lineage-generation assertions / replay-trace verification). Adding the validation state to C11a would be a behavioral change; deferred for cleaner scope. |
| 4 (cache vs exploration identity fragility) | ACCEPT partial — anti-pattern guard-rail | § 3.4.1 — add explicit anti-pattern callout: "cache identity is NOT a proxy for 'already explored.' Future orchestration layers must not conflate Tier 1 cache hits with Tier 3 exploration coverage." Reviewer's deeper proposal (`exploration_hash != structural_hash` distinct field) is documented in v1.5's tier-table already; the guard-rail makes the anti-pattern explicit. |
| 5 (wrapper rebuilding perf bottleneck) | REJECT — already filed | None — B-C11A-9 + B-C11A-15 already cover this. Fourth re-raise of same concern (v1.1 item 13, v1.3 item 5, v1.4 item 11). Reviewer-acknowledged: "Only backlog items exist." |
| 6 (floor labels overloaded as identity primitives) | ACCEPT partial + new backlog | § 3.7 — explicit callout that labels carry semantic + identity weight simultaneously, with Spec #1's `_normalize_label` handling character-level normalization (`"Ground"` / `"ground"` / `"GROUND"`) but NOT semantic equivalence (`"g"` / `"GF"`). New **B-C11A-17** for canonical floor identity primitive separate from display labels. |
| 7 (property tests don't model true search dynamics) | REJECT — already filed | None — B-C11A-12 (nightly stress fuzzing) already covers this. Reviewer's proposed tests (10k generation replay, population diversity entropy, cache collision stress, operator-frequency convergence, phase-lock detection) are all stress-fuzz territory. |
| 8 (orchestrator god-object) | REJECT — already filed | None — B-C11A-11 already covers this. Third re-raise (v1.2 item 10, v1.3 item 8, v1.5 item 8). Reviewer-acknowledged: "The spec already acknowledges this via B-C11A-11." |
| 9 (M8 2-floor assumption may fossilize psychologically) | ACCEPT doc patch | § 3.4 — add callout: "2-floor impact is an optimization assumption, NOT an architectural invariant." Reviewer's rename suggestion (`direct_impacts` vs `affected_floor_set`) rejected — abstraction is already named clearly; renaming ripples through consumers without semantic gain. |
| 10 (lineage model shallow for reproducibility) | REJECT — already filed | None — B-C11A-8 (full lineage extension) + B-C11A-14 (generation provenance) already cover this. Reviewer lists exactly the fields B-C11A-8+14 enumerate. |
| 11 (cross-spec coupling) | ACCEPT — cross-reference | § 9 — add cross-spec governance status note pointing to existing Spec #2 B-C9-G (architecture-governance convention) + Spec #3 B-MFWZP-J (cross-spec invariant registry). Reviewer's proposed "cross-spec invariant contracts / compatibility matrices / semantic version compatibility assertions / automated contract tests between specs" matches both backlog items. |
| 12 (spec complexity itself is risk) | ACCEPT partial + new backlog | § 9 — post-LOCK plan referencing spec-restructure-into-appendices direction. New **B-C11A-18** for spec restructure into normative / rationale / algorithm / invariants appendices + architecture/execution-flow/identity-system diagrams. Overlaps Spec #1 B-MFDB-N (spec restructure). |

**Net delta from v1.5**: ZERO behavioral changes. ZERO algorithm changes. **5 spec patches** (items 4, 6, 9, 11, 12). **3 new backlog items** (B-C11A-16, 17, 18). **7 rejects** with reasoning preserved (4 already-filed, 1 deferred to new backlog, 2 strategic).

**Pattern recognition** (second consecutive doc-polish round): the substantive design space is genuinely exhausted. v1.5 was doc-polish after three behavioral-change rounds; v1.6 is doc-polish after a doc-polish round. This matches the convergence shape Specs #1 (v0.4 → v0.5), #2 (v0.10 → v0.11), and #3 (v0.2 → v0.3) each hit before LOCK. Reviewer's verdict ("PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope") explicitly recognizes this.

**Pattern-A check**: zero algorithm changes in v1.6; all five patches are documentation guard-rails + cross-references + post-LOCK planning. No bandage opportunities — every reviewer-named "real" concern (the five at the end of their critique) is properly backlog-tracked with NSGA-II / C11b / scale triggers.

---

## § 1 — Why this amendment exists

Spec #1 (`MultiFloorDwellingBrief` v0.5 LOCKED) defines multi-floor input.
Spec #2 (C9 Amendment v0.11 LOCKED) makes per-floor master designation
correct. Spec #3 (`MultiFloorWetZonePlannedCandidate` v0.3 LOCKED) defines
the multi-floor output type with cross-floor invariants.

**But the C11a pipeline currently does not consume any of these types.**
Empirically verified (S40-continuation, pre-draft):

- C11a's `_is_multi_floor()` orchestrator helper (in `orchestrator.py:170`) duck-types for `is_multi_floor` attribute or `floors` collection on the brief. Spec #1's `MultiFloorDwellingBrief` exposes `is_multi_floor: bool = True` as a property, so the duck-type WILL detect the new type — but currently no upstream code passes a `MultiFloorDwellingBrief`, so the dispatch is dormant.
- C11a's M8 stub (`operators/m8_vert_rearr.py`) builds a `TierBInputMutation` with `new_master_bedroom_floor_label="swap_master_floor"` — a literal placeholder string, not a real swap. The Tier B pipeline cannot actually execute M8.
- C11a's `derive_canonical_signature` (in `source_signature.py:99`) is single-floor-only — assumes the source is a `WetZonePlannedCandidate`. It does not handle `MultiFloorWetZonePlannedCandidate`.
- C11a's cache (`cache.py`) keys are derived from `derive_canonical_signature` output + `C11A_CACHE_KEY_VERSION` (currently `"v1.0.0"`). Multi-floor wrappers would silently hash to the same cache slot as their first floor, causing cache collisions.
- C11a's lineage classifier (`lineage.py`) assumes single-floor source/result; family slot allocation (`family_slot_allocator.py`) similarly.

**This amendment threads multi-floor support through every C11a pipeline stage** so that:
1. The orchestrator accepts `MultiFloorDwellingBrief` as input AND `MultiFloorWetZonePlannedCandidate` as source candidate.
2. M8 (`m8_vert_rearr`) becomes real: builds a concrete master-floor-swap by reading the source wrapper's current master label, proposing the alternative floor, running C9→C10 cascade per affected floor, assembling a new `MultiFloorWetZonePlannedCandidate`.
3. Tier A operators (M0-M5, M9) execute per-floor against the brief that matches each per-floor candidate.
4. Tier B operators M6, M7a/M7b execute per-floor (already real per S39/S40 single-floor wiring; this amendment dispatches them to the right floor in a multi-floor context).
5. Signature derivation, cache identity, family slot allocation, and lineage classification all extend to multi-floor.

This is the largest spec in the B-NEW-T3 sequence. Estimated build effort: ~3-5 sessions of work after LOCK (this estimate matches the original S39 backlog entry that flagged B-NEW-T3 as "L" effort).

**Systemic importance** (mirroring Spec #2 § 1's framing): the diff for this amendment is moderately large — multiple files, new orchestrator-level dispatch, new pipeline-stage extensions. The semantic surface is even larger: this amendment is the operationalization point where the multi-floor architecture stops being a domain-types triplet and becomes a working pipeline. Bugs here propagate everywhere downstream.

---

## § 2 — Scope summary

| C11a stage | Currently | After this amendment |
|---|---|---|
| Orchestrator entry (`mutate_topologies`) | Accepts `floor_room_brief: FloorRoomBrief` | Accepts `floor_room_brief: FloorRoomBrief \| MultiFloorDwellingBrief` |
| `_is_multi_floor()` helper | Duck-types `is_multi_floor` attr; returns False for current `FloorRoomBrief` | UNCHANGED — already correctly detects Spec #1's wrapper via the `is_multi_floor: bool = True` property |
| Pre-flight `requires_multi_floor` gate (line 313) | Gates M8 out of single-floor batches | UNCHANGED — already correct |
| Per-floor expansion | None — single brief processed once | NEW: when input is `MultiFloorDwellingBrief`, expand to per-floor `FloorRoomBrief` instances (each with `has_master_bedroom` set per Spec #1's `iter_floors_with_master_flag()`); run C9→C10 cascade per floor; assemble result as `MultiFloorWetZonePlannedCandidate` |
| Tier A operators (M0-M5, M9) | Applied to single source | NEW: applied per-floor — each operator runs against the floor it targets; results re-assembled |
| Tier B M6, M7a, M7b | Real wiring exists, single-floor | NEW: dispatched per-floor in multi-floor context; use Spec #3's `with_floor_replaced(label, new_wzpc)` to produce result wrapper |
| Tier B M8 (`m8_vert_rearr`) | STUB with literal `"swap_master_floor"` string | NEW: real implementation; reads source's master label, picks alternative floor, runs C9→C10 on affected floors, uses Spec #3's `with_master_on(new_label, new_per_floor_candidates)` to produce result wrapper |
| `derive_canonical_signature` | Single-floor only | NEW: multi-floor dispatch — if source is `MultiFloorWetZonePlannedCandidate`, hash per-floor signatures + master label; else fall back to existing single-floor logic |
| `is_real_wet_zone_candidate` | Detects only `WetZonePlannedCandidate` | NEW: also detects `MultiFloorWetZonePlannedCandidate` |
| Cache identity | `derive_canonical_signature` + `C11A_CACHE_KEY_VERSION` | UNCHANGED interface; cache-key version bumped to `"v1.3.0"` (cumulative from Spec #2's `v1.1.0` + Spec #3's `v1.2.0` + this) |
| Family slot allocator | Single-floor source family | NEW: multi-floor source family is derived from per-floor families (canonical aggregation; details § 3.5) |
| Lineage classifier | Single-floor operator-effect classification | NEW: multi-floor lineage tracks per-floor operator effects + dwelling-level effect (M8 specifically) |

---

## § 3 — Behavioral contract

### § 3.1 — Orchestrator entry: input dispatch

`mutate_topologies(floor_room_brief=..., sources=..., grid=..., plot_analysis=..., config=...)` accepts EITHER:

- `FloorRoomBrief` (single-floor) — existing behaviour preserved byte-identical.
- `MultiFloorDwellingBrief` (Spec #1) — new behaviour.

Dispatch via the existing `_is_multi_floor()` helper at `orchestrator.py:170`, **wrapped by a new pre-flight protocol validator** (item 1 from v1.1 critique walk):

```python
def _validate_multi_floor_protocol(obj: Any) -> None:
    """Pre-flight: confirm obj satisfies the multi-floor protocol before
    pipeline entry. Hardens the duck-typed _is_multi_floor() against
    accidental misrouting (unrelated DTOs / test doubles / plugin objects
    with coincidental attribute names).

    Required:
      - obj.is_multi_floor is True (literal True, not just truthy).
      - obj.floor_labels exists and is iterable (tuple, list, frozenset).
      - obj.floors exists and is iterable with len() >= 2.

    Raises OrchestrationProtocolError with a clear diagnostic if any
    condition fails.
    """
    if getattr(obj, "is_multi_floor", None) is not True:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: is_multi_floor must be True; "
            f"got {getattr(obj, 'is_multi_floor', '<missing>')!r}"
        )
    if not hasattr(obj, "floor_labels"):
        raise OrchestrationProtocolError(
            "Multi-floor protocol violation: missing floor_labels attribute"
        )
    floors = getattr(obj, "floors", None)
    if floors is None:
        raise OrchestrationProtocolError(
            "Multi-floor protocol violation: missing floors attribute"
        )
    try:
        n = len(floors)
    except TypeError:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floors not measurable; "
            f"got {type(floors).__name__}"
        )
    if n < 2:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floors must have len >= 2; "
            f"got {n}"
        )
    # v1.3 (item 4 from v1.2 critique walk): cardinality check. Catches
    # impostors that have both attrs but with mismatched length. Other
    # semantic checks (unique labels, master ∈ labels, master floor has
    # bedroom_count ≥ 1) are redundant with Spec #1's MFDB-1 through
    # MFDB-4 invariants — a real MultiFloorDwellingBrief enforces them
    # at __post_init__. The cardinality check is the one semantic check
    # an impostor could plausibly violate AND that Spec #1 invariants
    # don't catch on a non-MFDB object.
    try:
        labels_len = len(obj.floor_labels)
    except TypeError:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floor_labels not measurable; "
            f"got {type(obj.floor_labels).__name__}"
        )
    if labels_len != n:
        raise OrchestrationProtocolError(
            f"Multi-floor protocol violation: floor_labels length "
            f"({labels_len}) != floors length ({n})"
        )
```

When the brief is detected as multi-floor:
1. `_validate_multi_floor_protocol(floor_room_brief)` runs first — fails fast on protocol drift.
2. The orchestrator derives the per-floor brief tuple via Spec #1's `iter_floors_with_master_flag()` helper, constructing `FloorRoomBrief(...)` instances with `has_master_bedroom` set correctly per floor.
3. Each source in `sources` is expected to be a `MultiFloorWetZonePlannedCandidate` (Spec #3 wrapper). **Per-source alignment is validated via a second pre-flight** (item 9 from v1.1 critique walk):

```python
def _validate_multi_floor_alignment(
    brief: Any, source: Any,
) -> None:
    """Pre-flight: confirm source's per-floor labels match brief's
    per-floor labels exactly (identity + order + count). Hardens against
    orchestration drift where source and brief came from different
    construction paths.

    Required:
      - source.floor_labels == brief.floor_labels (exact tuple equality;
        same labels, same order, same length).
      - source.master_bedroom_floor_label == brief.master_bedroom_floor_label.

    Raises OrchestrationAlignmentError with a clear diagnostic if any
    condition fails.
    """
    if source.floor_labels != brief.floor_labels:
        raise OrchestrationAlignmentError(
            f"Multi-floor alignment violation: source.floor_labels="
            f"{source.floor_labels!r} != brief.floor_labels="
            f"{brief.floor_labels!r}"
        )
    if source.master_bedroom_floor_label != brief.master_bedroom_floor_label:
        raise OrchestrationAlignmentError(
            f"Multi-floor alignment violation: source.master_bedroom_floor_label="
            f"{source.master_bedroom_floor_label!r} != brief.master_bedroom_floor_label="
            f"{brief.master_bedroom_floor_label!r}"
        )
```

This guards against (e.g.) a brief constructed from one user input being paired with a source produced from a different brief — a real risk in test scaffolding and in any future API that decouples brief construction from candidate persistence.

4. After both validators pass, per-operator dispatch runs against the wrapper as a single logical source.

**Errors**: `OrchestrationProtocolError` and `OrchestrationAlignmentError` are new exception types in `buildemup/components/c11a/errors.py`. Both inherit from a base `OrchestrationError`. Build-session work; not part of this spec's runtime contract beyond their existence.

### § 3.2 — Per-floor Tier A operator execution

Tier A operators (M0-M5, M9) currently take a `source` (`WetZonePlannedCandidate`) and a `tier_a_context`. In multi-floor mode:

For each candidate in `sources` (a `MultiFloorWetZonePlannedCandidate`):
  For each per-floor `WetZonePlannedCandidate` in `candidate.floors`:
    Apply the operator to that per-floor candidate (existing single-floor logic).
    Collect the result.
  Re-assemble as a new `MultiFloorWetZonePlannedCandidate` via Spec #3's `with_floor_replaced(label, new_wzpc)` helper — replacing only the floor that was actually mutated.

**Critical**: Tier A operators mutate ONE FLOOR per application. M2-bump (e.g., bump bathroom east) operates on one floor's wet-zone plan; other floors are unchanged. The result wrapper preserves master designation and reuses non-target floors as-is.

**Attempt-generation order — bipartite interleaving** (v1.4, addressing v1.3's operator-major bias):

v1.3 used round-robin floor interleaving per operator. While this fixed v1.2's floor-axis bias (lower-index floors over-mutated), the **operator-major outer loop preserved operator-axis bias** under slot truncation:

```
v1.3 generation order (4 operators, 4 floors, slot_count=6):
  M0:F0, M0:F1, M0:F2, M0:F3,      # M0 takes 4 slots
  M2:F1, M2:F2,                    # M2 takes 2 slots; M3 + M4 starved
```

Under truncation: M0 gets 4 attempts, M2 gets 2, M3/M4 get zero. Floor axis was uniform within M0; operator axis was not.

v1.4's bipartite interleaving uses a **round-major outer loop** with `(operator, floor)` pairs distributed across each round, with operator-index-rotated floor offsets to preserve floor fairness:

```python
def _generate_per_floor_attempts(
    operators_in_family: tuple[MutationOperator, ...],
    floor_labels: tuple[str, ...],
) -> tuple[tuple[MutationOperator, str], ...]:
    """v1.4 (item 1 from v1.3 critique walk): full bipartite
    operator+floor interleaving. Eliminates operator-bias under
    slot truncation (which v1.3's operator-major loop preserved).

    Algorithm: round-major outer loop. In each round k (k from 0 to
    num_floors-1), emit one (operator, floor) attempt for every
    operator. Floor index for operator at operator_index i in round k
    is (i + k) mod num_floors — preserves v1.3's per-operator floor
    rotation, but now distributed across rounds rather than
    concentrated.

    Mathematical property: under slot truncation at slot_count S,
    each (operator, floor) pair appears once if S >= num_operators *
    num_floors; otherwise the first S pairs distribute uniformly
    across both axes. Truncation bias is bounded by 1 per axis-pair.
    """
    attempts: list[tuple[MutationOperator, str]] = []
    n_floors = len(floor_labels)
    n_operators = len(operators_in_family)
    for round_idx in range(n_floors):
        for operator_index, operator in enumerate(operators_in_family):
            floor_index = (operator_index + round_idx) % n_floors
            attempts.append((operator, floor_labels[floor_index]))
    return tuple(attempts)
```

Effect on the same `(4 operators, 4 floors, slot_count=6)` scenario:

```
v1.4 generation order:
  # round 0:
  M0:F0, M2:F1, M3:F2, M4:F3,
  # round 1:
  M0:F1, M2:F2,                    # truncated at 6
```

Under truncation: M0 gets 2 attempts, M2 gets 2, M3 gets 1, M4 gets 1. All operators represented; floor distribution also bounded across the truncated set ({F0, F1, F2, F3} → each gets at most 1 attempt from round 0, plus F1 and F2 from round 1 → final counts: F0=1, F1=2, F2=2, F3=1).

**Fairness theorem under bipartite interleaving** (v1.5, item 2 from v1.4 critique walk — replaces v1.4's "both axes uniform" wording with mathematically-precise bounded-imbalance statement):

Let `n_ops = num_operators`, `n_fl = num_floors`, `S = slot_count`. Define `K_op(i)` as the number of attempts assigned to operator `i` after truncation at S, and `K_fl(j)` as the number assigned to floor `j`. Then:

- **Per-operator bound**: `floor(S / n_ops) ≤ K_op(i) ≤ ceil(S / n_ops)` for all i. **Imbalance** between any two operators is ≤ 1.
- **Per-floor bound**: `floor(S / n_fl) ≤ K_fl(j) ≤ ceil(S / n_fl)` for all j. **Imbalance** between any two floors is ≤ 1.
- **Starvation-free**: for `S ≥ max(n_ops, n_fl)`, every operator AND every floor gets at least 1 attempt. v1.4's bipartite round-major scheme guarantees this constructively because round 0 alone emits one `(operator, floor)` pair for each `(i, (i mod n_fl))` — covering every operator at least once, and every floor at least once (modulo `n_fl`).
- **NOT uniform**: when `S` is not divisible by `n_ops` (or `n_fl`), the distribution has bounded imbalance ≤ 1. Earlier operators in round-major iteration order receive the ceiling-share when partial rounds occur. v1.4's wording "both axes uniform under truncation" overstated this; v1.5 corrects to "bounded imbalance ≤ 1, starvation-free."

**Worked example** (item 2 reviewer's case): 5 operators, 3 floors, S=7. Round 0 emits 5 pairs (every operator, with rotated floor). Round 1 emits 5 more; truncation cuts at S=7, so round 1 contributes the first 2 pairs. Final distribution:
- Operators: {2, 2, 1, 1, 1} (imbalance = 1 ✓)
- Floors: {2, 3, 2} (imbalance = 1 ✓)

No starvation; bounded imbalance ≤ 1 on both axes.

**Partial-round positional advantage** (item 3 from v1.4 critique walk, reviewer-acknowledged not pre-LOCK): the round-major iteration order assigns the partial-round slots to earlier operators in iteration order. This is a deterministic positional advantage of at most 1 slot per operator. Reviewer's Option A (accept bounded imbalance + document) is the chosen v1.x approach; Options B (stable-shuffle rounds by source_signature) and C (round-start offset rotates by generation) are filed as B-C11A-13 + future exploration-policy work for when C11b NSGA-II coordination requires tighter fairness.

**Single-floor briefs**: when `n_fl == 1`, the round loop iterates once and emits one attempt per operator. Existing single-floor behavior preserved byte-identical.

**Why this matters for evolutionary search**: under slot pressure, v1.3's operator-major order could systematically prevent certain mutation families from being explored, causing search convergence bias toward early-operator families' topology classes. v1.4's bipartite interleaving guarantees every operator gets representation within ±1 slot of the average, eliminating starvation while accepting a bounded positional advantage — which is the right property for evolutionary diversity at v1 scope.

**Rationale chain across the three behavioral-change rounds**:
- v1.1 (master-only) — froze non-master-floor evolution. Fixed in v1.2.
- v1.2 (all-floors lex-order) — biased toward lower-index floors under truncation. Fixed in v1.3.
- v1.3 (operator-major round-robin floor rotation) — fixed floor axis, biased toward early operators under truncation. Fixed in v1.4.
- v1.4 (bipartite round-major interleaving) — bounded imbalance ≤ 1 on both axes; starvation-free under truncation.

Reviewer-named "LOCK gate" for v1.3 → v1.4 — addressed; precision-corrected in v1.5.

**Further refinements** (per-floor attempt weighting; adjacency-aware floor prioritization; operator-priority weighting based on observed valid-result rates; partial-round positional-advantage breaking via stable-shuffle or offset rotation) filed as B-C11A-5 + B-C11A-13.

### § 3.3 — Per-floor Tier B M6 / M7a / M7b execution

M6 (wet rotate), M7a (grid bay X scale), M7b (grid bay Y scale) are real single-floor operators (S39 + S40 wiring). In multi-floor mode:

Same dispatch shape as Tier A (per v1.1 critique walk item 2 + v1.2 critique walk item 1): applied to ALL floors with round-robin interleaving, slot-allocator-limited. The Tier B regenerative cascade (C7→C8→C9→C10 for M7a/b; C10 re-run for M6) runs against the targeted floor's brief and produces a new per-floor `WetZonePlannedCandidate`; the wrapper is re-assembled via `with_floor_replaced`.

Each `(operator, floor_label)` pair produces one Tier B attempt; the slot allocator caps the total. **Per-attempt cost is unchanged from single-floor** (v1.2 critique walk item 9 clarification): a Tier B attempt costs one regenerative cascade regardless of whether the source is single-floor or multi-floor — the cascade runs against ONE floor's brief, producing ONE new per-floor candidate, plus a cheap wrapper rebuild via `with_floor_replaced`. **Total Tier B cost per generation is `slot_count × per_attempt_cost`**, with `slot_count` set at the same value single-floor briefs would use. Multi-floor briefs do NOT scale Tier B cost by floor count.

What DOES change: multi-floor briefs generate `num_floors × num_tier_b_operators` candidate attempts before slot truncation, vs `num_tier_b_operators` for single-floor. Slot allocator then truncates to `slot_count` regardless. The round-robin interleaving (§ 3.2) ensures the truncation doesn't bias toward specific floors.

**Adaptive Tier B quota tuning** (dynamic per-generation compute budgets, adaptive operator throttling, generation-aware Tier B slot adjustment) filed as **B-C11A-10** when profiling shows real bottlenecks. The slot allocator already provides the budget knob; B-C11A-10 is about making it adaptive based on observed cost.

**Per-floor attempt weighting** (uniform round-robin vs weighted variants like 70% master / 30% non-master) filed as **B-C11A-5** alongside the Tier A concern.

### § 3.4 — M8 (`m8_vert_rearr`) real implementation

M8 is the only Tier B operator that operates dwelling-wide. It swaps which floor hosts the master bedroom.

**Algorithm**:

1. Read `source` (a `MultiFloorWetZonePlannedCandidate`). Read `source.master_bedroom_floor_label` (the current master floor).
2. Compute candidate target floors: every floor in `source.floor_labels` EXCEPT the current master that has `bedroom_count >= 1` (per Spec #1 Inv MFDB-4 — the target floor must be able to host the master). Empty target set → M8 returns `MutationApplicationResult(valid=False, invalidity_reason="no_viable_master_target")`.
3. **Choose one target floor via deterministic cyclic exploration** (item 3 from v1.1 critique walk + item 2 from v1.2 critique walk):

   v1.2 used `hash(signature + generation + operator_index) % N` for target selection. v1.2 critique walk item 2 correctly identified that this does NOT mathematically guarantee target coverage — hash modulo can repeatedly map to the same target across consecutive generations, leaving other eligible targets unexplored probabilistically.

   v1.3's cyclic exploration provides a **deterministic coverage guarantee**: across `N` consecutive distinct generations, all `N` eligible targets are visited exactly once.

   ```python
   def _pick_m8_target(
       eligible_targets: tuple[str, ...],
       generation: int,
       operator_index: int,
   ) -> str:
       """v1.3 (item 2 from v1.2 critique walk): deterministic cyclic
       exploration. Replaces v1.2's hash-modulo which lacked coverage
       guarantee.

       Mathematical property: for N eligible targets and any K consecutive
       distinct generation values, the visited target set has size
       min(K, N). At K = N, all eligible targets are visited exactly
       once.

       Eligible targets are PRE-SORTED (Spec #1's floor_tuple ordering
       drives the ancestry; v1.3 § 3.7's discussion of label-ordering
       semantics applies) to ensure cross-process determinism.
       """
       sorted_targets = sorted(eligible_targets)
       index = (generation + operator_index) % len(sorted_targets)
       return sorted_targets[index]
   ```

   The `source_signature` parameter (used in v1.2's hash) is no longer needed for target selection — generation + operator_index provides sufficient determinism with stronger coverage properties. The signature still drives cache identity (per § 3.5), but it doesn't drive target choice anymore. **This is a strictly stronger algorithm** than v1.2's hash-modulo.

4. Construct the post-mutation `MultiFloorDwellingBrief` via Spec #1's `with_master_on(new_floor_label)`. This re-validates the target floor has bedroom_count ≥ 1.
5. For each floor whose `has_master_bedroom` flag flipped (the old master floor: True → False; the new master floor: False → True), re-run the C9→C10 cascade against the new per-floor brief. **Exactly two floors** are affected (in v1.6; see B-C11A-7 for future cross-floor cascades; see § 3.11 for the `affected_floor_set` abstraction that makes this expandable).

   **Architectural framing** (NEW in v1.6 per item 9 from v1.5 critique walk): the "exactly two floors affected" property is an **optimization assumption**, NOT an **architectural invariant**. The assumption holds today because no cross-floor structural constraints exist in the pipeline yet (no vertical wet-stack alignment, no plumbing column coupling, no staircase landing relationships, no acoustic zoning). When B-C11A-7 (cross-floor cascade invalidation graph) lands — gated on Spec #1 B-MFDB-C — the M8 cascade may legitimately need to invalidate floors beyond the two master-flag-flipping floors. The `affected_floor_set` abstraction (§ 3.11) is the extension point; the FloorImpact structured return type already supports `kind="indirect"` + `requires_validation_only=True` for transitively-affected floors. Future maintainers MUST NOT treat "two floors" as a structural property of M8 — it is a current-state efficiency artifact of an under-constrained dwelling model.
6. Assemble the new `MultiFloorWetZonePlannedCandidate` via Spec #3's `with_master_on(new_floor_label, new_per_floor_candidates)`. Spec #3's `__post_init__` re-validates all 6 invariants (MFWZP-1 through 6).
7. Return `MutationApplicationResult` with the new wrapper.

**Determinism semantics — structural vs exploration** (item 6 from v1.2 critique walk):

v1.2's docs said "deterministic for cache reproducibility" but generation-dependent target selection means same `source_signature` + same operator can produce different outputs across generations. This caused legitimate concern about what "deterministic" actually meant.

v1.3 explicitly separates two determinism concepts:

- **Structural determinism**: given the same input `(source, generation, operator_index, config)`, M8 produces byte-identical output. Cache keys are derived from `derive_canonical_signature(source)` which depends only on structural content, not on generation. So: identical inputs at any generation → identical signature → identical cache slot. The cache reproducibility property holds at the structural level.
- **Exploration determinism**: across different generations on the same `source`, M8 deliberately produces DIFFERENT outputs (different target floors). This is INTENTIONAL — the cyclic algorithm guarantees coverage across N generations. If exploration determinism collapsed to structural determinism (same generation → same output as previous generation on same source), the search would never explore alternative targets.

These two determinism notions don't conflict; they operate at different levels. Cache hits work when the SAME `(source, generation, operator_index)` recurs (e.g., replay debugging, deterministic re-runs). Cache misses correctly occur when generation advances on the same source (e.g., evolutionary exploration), because the orchestrator IS attempting to produce a structurally-different candidate.

**Cyclic-algorithm periodicity acknowledgment** (v1.4, item 2 from v1.3 critique walk):

The cyclic algorithm `sorted_targets[(generation + operator_index) % N]` creates **deterministic periodicity** — for an N-floor dwelling, generations `g, g+N, g+2N, ...` all visit the same target. This is acceptable for v1.x because:
1. Coverage within N consecutive generations is the property that matters most for v1 scope (no starvation).
2. Cache identity is decoupled from generation (per the structural-determinism rule above); periodicity in target selection does NOT produce cache collision artifacts.
3. C11b NSGA-II (which would suffer from phase-locked exploration synchronizing across population members) is not yet wired.

When C11b NSGA-II coordinates exploration pressure across population members, the cyclic algorithm's predictability may produce evolutionary resonance — many candidates with the same generation counter targeting the same floor simultaneously. The upgrade path is `stable_shuffle(targets, source_signature)` then `index = generation % N`, which preserves determinism + coverage while breaking phase-locking via per-candidate permutation. Filed as **B-C11A-13**.

### § 3.4.1 — Determinism tier-table (NEW in v1.4 per item 3 from v1.3 critique walk)

v1.3 introduced the conceptual structural-vs-exploration distinction but didn't enumerate which downstream systems rely on which tier. v1.4 makes the dependencies explicit:

| Tier | Property | Depends on | Used by |
|---|---|---|---|
| **Tier 1: Structural identity determinism** | Same `(source structural content)` → same canonical signature. Generation-independent. Source-tuple-order-dependent (per Spec #1 + Spec #3 § 3.5 deliberate design). | Spec #1 brief normalization (§ 3.1), Spec #3 ancestry walk (§ 3.3), this amendment's `multi_floor_sig_schema=v1` prefix (§ 3.5). | C11a cache identity (signature → cache slot), Spec #3 equality semantics, lineage source-family identity, C11b candidate-equality checks (when scoring wires up). |
| **Tier 2: Operator scheduling determinism** | Same `(source, generation, operator_index, config)` → same operator sequence + same M8 target + same per-floor attempt order. Generation-dependent but stable for fixed generation values. | Tier 1 + this amendment's `_generate_per_floor_attempts` (§ 3.2) + `_pick_m8_target` (§ 3.4). | Deterministic replay debugging, regression-test reproducibility, evolutionary-run determinism under fixed seed. |
| **Tier 3: Evolutionary trajectory determinism** | NOT structurally deterministic — different generations on the same source intentionally produce different outputs (different target floors, different per-floor attempt order under truncation). | Generation parameter advancing across the search; orchestrator's generation-counter contract with the caller. | C11b NSGA-II exploration pressure (when wired); search-space breadth coverage. |

**System-to-tier dependencies**:
- **C11a cache** depends only on Tier 1. Cache hits work under generation-independent reproducibility (same source content → same cache slot).
- **Replay debugging** depends on Tier 2. Reproducing a specific orchestration trace requires the same `(source, generation, operator_index)`; the cache-hit-on-same-source guarantee is insufficient because the OPERATOR SEQUENCE matters.
- **C11b NSGA-II** (when wired) will explicitly depend on Tier 3. Search-space coverage requires generation variance to produce different mutations on the same source.
- **Cross-spec integration tests** (§ 5.1 v1.4 additions) verify Tier 1 + Tier 2; Tier 3 is a property of the search loop, not of any single mutation invocation.

**Why this tier-table matters now**: when C11b wires up exploration pressure, the question "does this candidate need re-mutation?" must be answered against Tier 3 semantics, not Tier 1. Failing to distinguish would either cause cache thrashing (re-mutating already-explored candidates because Tier 1 cache misses) or search stagnation (re-using cached mutations because Tier 1 cache hits, missing Tier 3 exploration). The tier-table is the contract C11b binds against.

**Anti-pattern guard-rail** (NEW in v1.6 per item 4 from v1.5 critique walk):

**Future orchestration layers MUST NOT treat cache identity as a proxy for "already explored."** The cache identity (Tier 1, derived from `derive_canonical_signature(source)`) tells you: "this exact structural content was seen before in this process." It does NOT tell you: "this exploration path has been visited" or "this trajectory has been searched."

Different exploration trajectories CAN collapse onto identical cache slots — for example, two candidates produced by different operator sequences may have structurally-identical wrappers even though they came from different lineage paths. A Tier 3 consumer reading "cache hit" as "no need to re-mutate" would incorrectly skip exploration of unique trajectories that happen to coincide in cache identity.

The correct contract:
- **Tier 1 cache hit** means: "skip the *computation* — we already have the canonical signature on file." Use for: cache reuse for derived properties, equality checks, dedup of structurally-identical outputs.
- **Tier 3 exploration state** means: "this trajectory has been visited." Use for: search-coverage tracking, evolutionary diversity pressure, NSGA-II population management.

These two states are DIFFERENT and must remain so. Conflating them is the canonical anti-pattern that B-C11A-13 (source-signature-stable-shuffle), B-C11A-14 (generation provenance in lineage), and the future C11b exploration-tracking infrastructure together prevent. Until those land, the contract is: **structural identity is for caching; lineage chain + generation history is for exploration tracking. They share NO identity field and SHOULD NOT.**

If a future amendment introduces an `exploration_hash` field distinct from the canonical signature, that field belongs in the lineage record (per B-C11A-14's extension scope), not on the wrapper itself. The wrapper's identity remains structural-only.

**Generation provenance in lineage metadata** (reviewer suggestion for richer Tier 3 reproducibility) filed as **B-C11A-14**.

**Failure modes** (refined per v1.1 critique walk item 12 + v1.2 critique walk item 12 — v1.2's `orchestration_state_drift` was too broad for invariant-specific root-cause diagnostics):

| `invalidity_reason` | When it fires |
|---|---|
| `no_viable_master_target` | No eligible target floor (all non-master floors have `bedroom_count=0`). |
| `c9_generation_failed` | C9 raised on the new per-floor brief (e.g., NBC infeasibility on the new master floor). |
| `c10_validation_failed` | C9 succeeded but C10 wet-zone planning rejected the cascade result. |
| `orchestration_state_drift:mfwzp1` | Spec #3's MFWZP-1 (≥2 floors) failed at wrapper construction. Indicates upstream provided <2 floors. |
| `orchestration_state_drift:mfwzp2` | Spec #3's MFWZP-2 (per-floor labels unique, derived) failed. Indicates floor_label drift or duplicates after M8 cascade. |
| `orchestration_state_drift:mfwzp3` | Spec #3's MFWZP-3 (master ∈ derived labels) failed. Indicates M8 picked a target that's not in the cascade-output labels (orchestration bug). |
| `orchestration_state_drift:mfwzp4` | Spec #3's MFWZP-4 (instances are WZPCs) failed. Type-level bug in the cascade output assembly. |
| `orchestration_state_drift:mfwzp5` | Spec #3's MFWZP-5 (exactly one master bedroom globally) failed. Most likely root cause: C9 didn't honor `has_master_bedroom` flag on the new brief. |
| `orchestration_state_drift:mfwzp6` | Spec #3's MFWZP-6 (declared master matches derived) failed. Most likely root cause: C9 honored the flag but the wrapper-level master label drifted from what cascade produced. |

The structured-variant taxonomy enables precise telemetry/anomaly clustering in production. Pattern matching on `invalidity_reason.startswith("orchestration_state_drift:")` still works as a catch-all for orchestration-bug detection without losing root-cause granularity.

**Root-cause precision caveat** (NEW in v1.5 per item 6 from v1.4 critique walk):

Invariant-specific drift variants **narrow the failure class but do NOT uniquely identify root cause**. A single `orchestration_state_drift:mfwzp5` failure can originate from multiple distinct root causes — C9 ignoring the `has_master_bedroom` flag on one of the affected briefs, stale wrapper reuse if the orchestrator mistakenly passed an old per-floor candidate, duplicate floor replacement if `with_floor_replaced` was called twice on the same label, cascade corruption if C9/C10 produced inconsistent output between the two affected floors, or a bad floor mutation upstream that the cascade then propagated. The `:mfwzpN` suffix names WHICH cross-floor invariant failed, not WHY it failed.

The taxonomy is therefore a **failure-class signal** for production telemetry and anomaly clustering, not a root-cause oracle. Operators relying on `:mfwzpN` for debugging should treat it as "narrow the search space to causes that can violate MFWZP-N" rather than "the cause is X."

Future improvements that would add genuine root-cause precision:
- **Generation provenance** in the lineage record (B-C11A-14) — tells you WHEN the drift first appeared in the search trajectory.
- **Operator provenance** in the lineage record (B-C11A-14) — tells you which operator's application produced the drifted state.
- **Floor ancestry tracing** (B-C11A-8) — tells you the upstream per-floor candidate lineage that led to the assembly.
- **Mutation-chain metadata** (B-C11A-8) — tells you the full operator sequence applied to reach this state.

Together these would allow `(invalidity_reason, lineage_chain)` debugging where the invariant variant narrows the failure class and the lineage chain identifies the root cause within that class. v1.5's taxonomy is the foundation; the lineage-chain extension is post-v1 work.

### § 3.4.2 — Generation contract (NEW in v1.5 per item 13 from v1.4 critique walk)

v1.4 introduced generation as a critical input to operator scheduling (§ 3.2 bipartite interleaving and § 3.4 M8 cyclic target selection). v1.4 critique walk item 13 correctly flagged that generation lifecycle / ownership / monotonicity / replay semantics were under-specified. v1.5 formalizes the contract:

**Ownership**: `generation` is provided by the **caller** of `mutate_topologies` — typically the C11b search loop (when wired) or a test driver. C11a does NOT own generation state; it is a parameter, not a globally-managed value.

**Monotonicity** (recommended but not enforced): callers SHOULD pass strictly-increasing generation values across consecutive `mutate_topologies` invocations within a single search run. Specifically:
- Generation 0 is the search's starting point.
- Each subsequent call passes generation = previous_generation + 1 (typical) or any value strictly greater than the highest generation seen in any source candidate's lineage (if generation skipping is required for branching/sharding).

C11a does NOT validate monotonicity — the contract is advisory because legitimate use cases exist for non-monotonic generation values (e.g., parallel sharded search where shards have independent generation counters; replay debugging where specific generation values are reproduced).

**Replay semantics**: given the same `(source, generation, operator_index, config)`, `mutate_topologies` produces byte-identical output. This is the Tier 2 (operator scheduling determinism) guarantee from § 3.4.1. Reproducing a specific orchestration trace requires capturing all four inputs; capturing only `(source, config)` is insufficient because the cyclic M8 target and bipartite interleaving order both depend on `generation` and `operator_index`.

**Reset semantics**: generation = 0 is a valid starting state; nothing in C11a's contract distinguishes "first call ever" from "generation 0 after a reset." Callers can reset by passing generation = 0 again. This is intentional — supports test scenarios that need to re-run from a known starting point.

**Source-vs-call generation distinction**: a `MultiFloorWetZonePlannedCandidate` source carries no intrinsic generation value; generation is associated with the MUTATION CALL, not the source. The same source can be mutated at generation N and again at generation N+10; both calls are valid, both produce deterministic outputs, and the outputs may differ (per Tier 3 exploration determinism).

**Why v1.5 formalizes this**: when C11b NSGA-II wires up, multiple population members will hit `mutate_topologies` in parallel with potentially overlapping generation values. The contract lets C11b's authors reason about cache reuse (Tier 1 — generation-independent), replay reproducibility (Tier 2 — fixed-generation), and exploration breadth (Tier 3 — generation-varying) without ambiguity.

**Future contract extensions** (filed as B-C11A-14 — generation provenance in lineage metadata): adding `generation: int` and `operator_index: int` fields to lineage entries would make the full `(source, generation, operator_index)` triple recoverable from any candidate's lineage, enabling full Tier 2 reproducibility without requiring the caller to track generation values externally.

### § 3.5 — Signature derivation extension

`derive_canonical_signature(source)` (in `source_signature.py:99`) currently assumes `source` is a `WetZonePlannedCandidate`. Amendment:

```python
def derive_canonical_signature(source: Any) -> str:
    # NEW: multi-floor dispatch.
    if is_real_multi_floor_candidate(source):
        return _derive_multi_floor_canonical_signature(source)
    # Existing single-floor logic UNCHANGED below.
    ...
```

Where `is_real_multi_floor_candidate` (v1.3 — replaces v1.2's name-based detection per item 11 from v1.2 critique walk) uses a marker-attribute pattern:

```python
def is_real_multi_floor_candidate(source: Any) -> bool:
    """Detect whether source is a MultiFloorWetZonePlannedCandidate.

    v1.3: uses the __multi_floor_candidate__ class-attribute marker
    instead of type().__name__ + module-path matching. Marker pattern is
    refactor-safe, subclass-friendly, and proxy-compatible.

    The marker is a CLASS attribute (not a dataclass field), so it does
    NOT participate in dataclass equality, hash, or repr. Spec #3 v0.3
    LOCKED's runtime contract is unaffected — the marker is a
    hash-irrelevant implementation detail added to the wrapper class.

    Coordinated with Spec #3 build-session: adds
        __multi_floor_candidate__: bool = True
    as a class attribute on MultiFloorWetZonePlannedCandidate. This is
    NOT an amendment to Spec #3 LOCKED; the class attribute is
    implementation-level, transparent to the spec's behavioral contract
    (Inv MFWZP-1 through 6, helpers, mutation semantics).
    """
    return getattr(source, "__multi_floor_candidate__", False) is True
```

**v1.2's name-based detection** (`type().__name__ == "MultiFloorWetZonePlannedCandidate"` + module-path match) is REPLACED by the marker-attribute lookup. The name-based fallback is dropped — a marker-only check is cleaner and the marker provides the explicit declaration that name-checking only approximated.

**Existing single-floor `is_real_wet_zone_candidate`** (in `candidate_context.py:338`) keeps its current name-based detection in v1.3. Migration to marker-attribute for the single-floor wrapper is filed as the residual scope of **B-C11A-6** — same pattern, but Spec #3 (multi-floor) is the higher-leverage candidate to migrate first because multi-floor detection is foundational to the new orchestration paths.

And `_derive_multi_floor_canonical_signature` computes:

```python
parts: list[str] = []
parts.append(f"multi_floor_sig_schema=v1")   # NEW in v1.2: explicit
                                              # wrapper-level schema version
parts.append(f"multi_floor=true")
parts.append(f"master_floor={source.master_bedroom_floor_label}")
for floor_label, per_floor_wzpc in zip(source.floor_labels, source.floors):
    per_floor_sig = derive_canonical_signature(per_floor_wzpc)  # recurse
    parts.append(f"floor[{floor_label}]={per_floor_sig}")
serialised = "|".join(parts)
return sha256(serialised.encode("utf-8")).hexdigest()[:16]
```

**Rationale**: structural-only canonical signature, mirrors single-floor `derive_canonical_signature`'s 16-hex-char SHA256 output. Includes master designation so M8 mutations produce distinct signatures from M0-M7/M9 mutations even if per-floor signatures coincidentally match.

**Schema-version prefix** (item 5 from v1.1 critique walk): the explicit `multi_floor_sig_schema=v1` prefix decouples the wrapper-level signature schema from the per-floor signature schema. If a future amendment changes how per-floor signatures are computed (e.g., adding new structural fields), the wrapper-level signature can stay stable at schema=v1 IFF the per-floor signature changes are also covered by a per-floor schema-version mechanism. Conversely, if the wrapper-level aggregation logic changes (e.g., a future amendment adds floor-elevation to the multi-floor signature), the wrapper-level schema bumps to v2 without forcing per-floor signature recomputation. Either dimension can evolve independently, preventing the "single change cascades globally" problem v1.1 reviewer flagged.

`C11A_CACHE_KEY_VERSION` bumps remain the coarse-grained mechanism (per § 3.6); the schema-version prefix is a finer-grained signal for downstream lineage / equivalence / diff tooling that wants to reason about which schema produced a given signature.

### § 3.6 — Cache identity

`C11A_CACHE_KEY_VERSION` (in `cache.py:68`) bumps from `"v1.1.0"` (post-Spec-#2) → `"v1.3.0"` (cumulative jump: Spec #3 LOCKED bumped to v1.2.0, this amendment to v1.3.0).

**Why a 2-step jump instead of v1.2.0 → v1.3.0**: Spec #3's LOCKED text references "Initial bump for this spec: bumping from Spec #2's v1.1.0 to v1.2.0." But the bump only takes effect at build time (when the code lands), and Specs #3 + #4 are built in the same B-NEW-T3 session. Practical decision: bump directly to v1.3.0 in one step (this amendment's build session) covering both the new wrapper type (Spec #3) and the multi-floor pipeline (this amendment). Documented here for build-session reference.

`derive_cache_key()` (in `cache.py:231`) interface UNCHANGED — it consumes `derive_canonical_signature` output, which extends transparently via § 3.5.

### § 3.7 — Family slot allocator extension

`family_slot_allocator.py` currently allocates Tier A/B slots per source candidate. The allocator reads per-candidate family ID (from `candidate_context`).

In multi-floor mode: each per-floor candidate has its own family ID; the wrapper's family is the **label-preserving aggregation** of per-floor families (item 4 from v1.1 critique walk). Aggregation rule:

```python
def multi_floor_family_id(wrapper: MultiFloorWetZonePlannedCandidate) -> str:
    pairs = sorted(
        (label, get_family_id(f))
        for label, f in zip(wrapper.floor_labels, wrapper.floors)
    )
    payload = "|".join(f"{label}={family_id}" for label, family_id in pairs)
    return f"multi_floor:{payload}"
```

**Rationale**: a multi-floor candidate's family encodes which family is assigned to which floor, not just the multiset of families. Sorted by label (not by family) ensures deterministic ordering while preserving label-family pairing. Example:

| Wrapper | Family ID |
|---|---|
| ground=A, first=B (master on ground) | `multi_floor:first=B\|ground=A` |
| ground=B, first=A (master on first) | `multi_floor:first=A\|ground=B` |

These two wrappers are architecturally distinct (different family on each floor) and now produce distinct family IDs. **v1.1's sorted-family aggregation** (`multi_floor:A,B` for both) would have collapsed them — false equivalence, incorrect slot pooling, evolutionary diversity collapse on multi-floor briefs. **v1.2's label-preserving aggregation** prevents this.

The `multi_floor:` prefix prevents accidental collision with single-floor family IDs. Sort key is the floor label (alphabetical) for cross-process determinism; sort by family would create cache instability when multiple labels share a family.

**Lexical-sort caveat** (item 3 from v1.2 critique walk):

Alphabetical sorting (`basement, first, ground, second`) may not reflect actual elevation order (`basement, ground, first, second`). With heterogeneous label conventions (`L1, roof, mezzanine, podium`), lexical sort produces output that's deterministic but architecturally arbitrary.

**v1.3 position**: lexical sort is the **available-determinism** choice. Elevation-based canonical ordering would require explicit floor-elevation metadata, which Spec #1 v0.5 LOCKED **deliberately deferred** to **B-MFDB-A** (`floor_elevation_m: float | None` field, gated on commercial-path / multi-floor scoring needs). Until B-MFDB-A lands, the only canonicalization signal available is the floor label string itself, and lexical sort is the deterministic option.

Implications:
- Family-ID equality across runs is preserved as long as label strings are stable (which they are, post-Spec #1 § 3.1 normalization).
- Family-ID does NOT semantically reflect elevation order. Family-ID is a structural identity token, not a human-readable architectural description. Downstream consumers reading family-IDs for diagnostic purposes should use the label-family pairs (`ground=A|first=B`) as displayed and NOT infer elevation from sort order.
- When B-MFDB-A lands and per-floor elevation metadata becomes available, the family-ID derivation can switch from lexical-sort to elevation-sort in a coordinated amendment. The current lexical-sort is forward-compatible — the wrapper-level signature schema-version prefix (`multi_floor_sig_schema=v1` per § 3.5) can bump to v2 when the sort key changes, signaling cache invalidation cleanly.

**Semantic divergence: family identity ≠ structural identity** (NEW in v1.5 per item 4 from v1.4 critique walk):

Family identity (this section) and structural identity (canonical signature, § 3.5) are **deliberately different identity systems** serving different purposes. Future maintainers MUST NOT conflate them.

| Identity system | Tuple-order semantics | Purpose | Used by |
|---|---|---|---|
| **Canonical signature** (§ 3.5) | Tuple order is significant (different orderings produce different signatures). Per Spec #1 + Spec #3 § 3.5 deliberate design. | Cache identity; structural equality; cross-process determinism for the same wrapper content. | C11a cache, Spec #3 `__eq__` / `__hash__`, lineage source-family identity. |
| **Family ID** (this section) | Tuple order is canonicalized away (sorted by label). Different orderings of the same label-family pairs produce the same family ID. | Slot-allocation grouping; evolutionary diversity pressure; pooling structurally-equivalent candidates for breadth exploration. | C11a family slot allocator, generation-level family pooling. |

**Why these systems intentionally diverge**: cache identity needs to distinguish `[ground=A, first=B]` from `[ground=B, first=A]` because they're structurally different dwellings (different families on different floors). Slot allocation needs to **group** them under different family-IDs (since they ARE different label-family pairings), but the SORT KEY for the family-ID derivation is the label (not the family) — so `[ground=A, first=B]` and `[first=B, ground=A]` (same label-family pairs, different tuple-order constructions) produce the SAME family-ID for slot allocation, even though they produce DIFFERENT canonical signatures.

**The practical effect**: if a hypothetical orchestrator path produced the same multi-floor wrapper via two different tuple-order constructions (which it shouldn't — tuple order is canonical per Spec #3, but hypothetically), they would be DIFFERENT cache entries but the SAME family for slot-allocation purposes. This is intentional — slot allocation aggregates across structurally-equivalent topologies for breadth pressure; caching distinguishes them for replay reproducibility.

**Why the term "family identity" is preserved across the codebase**: `MutationOperatorFamily` enum, `family_slot_allocator.py`, lineage classifier's family-transition terminology — the term is entrenched. Reviewer-suggested internal renames ("slot-allocation family", "exploration family") would ripple through unchanged code without semantic gain. This documentation callout achieves the same clarity by naming the divergence explicitly rather than renaming.

**Future amendment guidance**: if a future amendment introduces a third identity system (e.g., a "lineage cluster" or "topology equivalence class"), it MUST be documented here with the same tuple-order-semantics + purpose + consumers grid above. Treating identity systems implicitly is how subtle correctness bugs propagate across architectural layers (per Spec #2 v0.11 § 3.10 and Spec #3 v0.3 § 3.10's analogous warnings).

**Floor labels carry semantic + identity weight simultaneously** (NEW in v1.6 per item 6 from v1.5 critique walk):

Floor labels are doing TWO jobs in the current architecture:
1. **Display semantics** (user-facing): `"ground"`, `"first"`, `"second"` are meaningful to readers; `"basement"` carries architectural meaning beyond ordering; `"mezzanine"` / `"podium"` / `"roof"` are domain-specific terms.
2. **Identity primitives** (machine-facing): sort keys for family-ID derivation, derived per-floor labels for ancestry walks, equality keys for `MFWZP-2` (uniqueness invariant), hash inputs for canonical signatures.

These two jobs have different requirements. Display semantics want human-readable strings; identity primitives want stable canonical IDs that survive label changes (re-labeling `"ground"` → `"GF"` should NOT invalidate caches or break lineage if the underlying floor structure is identical).

**Current normalization coverage** (Spec #1 § 3.1 `_normalize_label`): handles character-level normalization (`"Ground"` → `"ground"`, `"  ground  "` → `"ground"`, `"first floor"` → `"first_floor"`). Does NOT handle semantic equivalence (`"g"` / `"GF"` / `"ground"` are all separate identifiers; `"floor 1"` and `"first"` are separate identifiers; `"L1"` and `"first"` are separate identifiers).

**Practical consequence today**: re-labeling a dwelling's floors (e.g., user changes display labels from `"ground"`/`"first"` to `"floor_0"`/`"floor_1"`) produces:
- Different canonical signatures (cache misses across the re-labeling).
- Different family IDs (slot allocator treats them as different families).
- Different lineage records (the per-floor ancestry chains differ).

For v1 scope this is acceptable — re-labeling is rare and the cache miss is correct (re-labeling IS a structural change at the identity layer, even if the topology is semantically identical). For future scope where label-vs-identity separation matters (commercial paths with standardized floor identifiers, persistent storage where labels evolve, multi-user systems where label conventions differ), filed as **B-C11A-17**: introduce a canonical floor identity primitive (e.g., `floor_uid` or `canonical_floor_index`) independent from display labels. Labels then become presentation metadata only.

The trigger for B-C11A-17 is "first concrete consumer needs label-independent floor identity" — likely either Spec #1's `floor_elevation_m` work (B-MFDB-A) when elevation-based canonical ordering replaces lexical sort, OR persistence-layer work where label evolution becomes a real workflow concern.

### § 3.8 — Lineage classifier extension

`lineage.py`'s classifier currently tracks (source-family → result-family) transitions per operator application. In multi-floor mode:

- Tier A / B M0-M7/M9 (per-floor operators): the family transition is at the per-floor level (the affected floor's family changes); the wrapper's aggregate family also changes (per § 3.7). Lineage records: `operator=M_X, floor_label_affected=L, per_floor_transition=(F1 → F2), wrapper_transition=(W1 → W2)`.
- M8 (dwelling-level operator): the family transition is at the dwelling level. `floor_label_affected=None` (M8 is dwelling-wide, not per-floor). Per-floor families are PRESERVED (the same per-floor brief contents, just with `has_master_bedroom` flipped — which changes the per-floor WZPC but typically not the per-floor family ID, since family ID derives from topology kind + zone bands + structural features, not master designation). The wrapper's transition is `(W1 → W2)` reflecting the master swap.

**Lineage `floor_label_affected: str | None` field** (item 10 from v1.1 critique walk, lightweight version): added to multi-floor lineage entries. Distinguishes single-floor operator effects (label = the affected floor) from dwelling-level effects (label = None). This is the minimum useful per-floor causality signal for downstream NSGA-II explainability and debugging. **Full ancestry-chain extension** (floor ancestry IDs, mutation provenance chains, master-transition events, per-floor generation counters) filed as **B-C11A-8** when explainability tooling needs the richer model.

`MutationLineageDepth` (existing enum) extends to multi-floor naturally — `SHALLOW_TRANSFORM` and `DEEP_TRANSFORM` apply per the existing single-floor semantics, just at the wrapper level.

### § 3.9 — Spec #2 v0.11 § 3.10 trust-boundary assertion — owned where?

Spec #2 v0.11 § 3.10 forward-pointed to this amendment: "Spec #4 (C11a Amendment v1.1) is expected to own this assertion — likely as a post-C9-fan-out check inside the multi-floor cascade, asserting that across all per-floor C9 results, exactly one room has `is_master=True AND category=BEDROOM`."

Spec #3 v0.3 LOCKED then **hardened** this: MFWZP-5 and MFWZP-6 enforce the assertion at `MultiFloorWetZonePlannedCandidate.__post_init__` — the bad state is structurally unreachable.

**Where v1.x ends up**: this amendment does NOT add a redundant assertion. Spec #3's construction-time guard fires before any cache/scoring/persistence path, satisfying the fast-fail lifecycle Spec #2 v0.11 § 3.10 required. The pipeline-level orchestrator behaviour is: if the wrapper constructor raises (because of orchestration drift), wrap the failure as a `MutationApplicationResult(valid=False, invalidity_reason="orchestration_state_drift:mfwzpN")` where `mfwzpN` is the specific MFWZP-N invariant that fired (per the v1.3 refined drift taxonomy in § 3.4) and continue to the next operator attempt. This is the failure mode listed in § 3.4 step 7.

**This satisfies the v0.11 forward-pointer.** Spec #2's trust-boundary contract is met by the combination of (a) Spec #3 construction-time enforcement + (b) this amendment's failure-mode handling at the pipeline boundary.

### § 3.10 — Backwards compatibility: every existing single-floor caller works unchanged

The default behaviour for `FloorRoomBrief` input is byte-identical to v1.0:

- `_is_multi_floor(FloorRoomBrief(...))` returns False (no `is_multi_floor` attribute, no `floors` collection).
- All existing pipeline stages take the single-floor branch.
- M0-M7, M9 dispatch single-floor (existing).
- M8 gated out via `requires_multi_floor=True` metadata + the existing line-313 check.
- Signature derivation falls back to single-floor logic.
- Cache keys ARE different (because `C11A_CACHE_KEY_VERSION` bumped) — single-floor candidates cached under v1.1.0 will not match cache slots under v1.3.0. This is the v1.3.0 invalidation effect; persisted cache (which doesn't exist yet) would need re-population, in-memory cache invalidates cleanly on process restart.

Every existing C11a test must pass unchanged modulo cache-key-version-sensitive tests (which adjust to v1.3.0 directly).

### § 3.11 — `affected_floor_set(operator, source)` abstraction (NEW in v1.3 per item 15 from v1.2 critique walk; refined in v1.4 per item 6 from v1.3 critique walk; further refined in v1.5 per item 1 from v1.4 critique walk — split API kwargs)

v1.3 introduced the abstraction layer. v1.4 refines its return type from `frozenset[str]` to `frozenset[FloorImpact]` — preserving the same v1.4 behaviour but enabling future cross-floor extensions to express "transitively invalidated, validation only" vs "directly mutated, cascade required" distinctions.

```python
@dataclass(frozen=True)
class FloorImpact:
    """Structured floor-level impact descriptor for cross-floor
    mutation effects. v1.4 (item 6 from v1.3 critique walk).

    v1.3's bare `frozenset[str]` couldn't distinguish:
      - directly mutated floors (require full C9→C10 cascade re-run)
      - transitively invalidated floors (require validation-only re-run)
      - revalidation-required floors (constraints to re-check, no
        regeneration)

    These distinctions matter for cost: a cascade re-run is O(C9+C10);
    a validation-only re-run is O(constraint-check-set). Without the
    distinction, future cross-floor amendments would force full
    cascades for every affected floor, even when only validation is
    needed — over-regeneration that scales poorly.

    v1.4 contract:
      - kind: "direct" for floors the operator directly mutates;
        "indirect" for floors whose constraint relationships to
        directly-mutated floors require re-evaluation.
      - requires_cascade: True iff this floor's C9→C10 must re-run.
      - requires_validation_only: True iff this floor's per-floor WZPC
        is reused as-is but cross-floor constraints involving this
        floor must be re-checked.

    Today's v1.4 implementation always returns `requires_cascade=True`
    for direct-mutation floors (per § 3.2 / § 3.3 per-floor dispatch
    and § 3.4 M8 cascade). When B-C11A-7 (cross-floor invalidation
    graph) lands, indirect/validation-only floors become populated
    without changing the abstraction.
    """
    label: str
    kind: Literal["direct", "indirect"]
    requires_cascade: bool
    requires_validation_only: bool


def affected_floor_set(
    operator: MutationOperator,
    source: MultiFloorWetZonePlannedCandidate,
    *,
    direct_floor_label: str | None = None,
    new_master_floor_label: str | None = None,
) -> frozenset[FloorImpact]:
    """Return the set of FloorImpact entries describing how the given
    operator's application affects each floor.

    v1.5 contract (item 1 from v1.4 critique walk — disambiguates v1.4's
    overloaded `target_floor_label` parameter that meant different things
    for per-floor vs dwelling-wide operators):

      - Per-floor operators (M0-M7, M9): caller passes
        `direct_floor_label=L` where L is the floor the operator was
        dispatched against. Returns {FloorImpact(L, "direct",
        cascade=True, validation_only=False)}.
        `new_master_floor_label` MUST be None.

      - M8 (dwelling-wide): caller passes
        `new_master_floor_label=L` where L is the floor M8 is moving the
        master designation TO. Returns {
            FloorImpact(source.master_bedroom_floor_label, "direct",
                        cascade=True, validation_only=False),  # old master
            FloorImpact(L, "direct", cascade=True,
                        validation_only=False),  # new master
        } — the two floors whose has_master_bedroom flag flips. Both
        need full C9→C10 cascade because their bedroom-vs-bathroom
        master designation changes.
        `direct_floor_label` MUST be None.

    Validation rule: exactly one of `direct_floor_label` and
    `new_master_floor_label` must be provided. Which one is determined
    by the operator's class:
      - operator.requires_multi_floor=False → direct_floor_label
      - operator.requires_multi_floor=True → new_master_floor_label

    Raises OrchestrationProtocolError if both are None or both are set,
    or if the wrong one is set for the operator's class.

    **Why v1.5 split this**: v1.4 used a single `target_floor_label`
    kwarg that meant "directly-mutated floor" for per-floor operators
    but "destination master floor" for M8. v1.4 critique walk item 1
    correctly flagged this as contract ambiguity: future operators or
    refactors could accidentally pass old-master instead of new-master,
    assume target_floor_label == only directly-mutated floor (true for
    per-floor but FALSE for M8 — old master is also directly mutated),
    or misuse the kwarg in operators with different semantics. Splitting
    into two explicit kwargs makes the contract self-documenting.

    Future contract extensions (when cross-floor constraints land per
    B-C11A-7) populate FloorImpact entries with kind="indirect" and
    requires_validation_only=True for floors whose constraints involve
    a directly-mutated floor but whose own per-floor WZPC is reused.

    Convention: `requires_cascade XOR requires_validation_only` — a
    floor either gets full regeneration or just constraint re-check,
    never both, never neither. Direct kinds default to cascade=True;
    indirect kinds default to validation_only=True.
    """
    metadata = OPERATOR_METADATA[operator]

    # v1.5 (item 1): validate exactly-one-kwarg-set, matching operator class.
    if metadata.requires_multi_floor:
        if new_master_floor_label is None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: new_master_floor_label required for "
                f"multi-floor operator {operator}"
            )
        if direct_floor_label is not None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: direct_floor_label MUST be None for "
                f"multi-floor operator {operator}; got {direct_floor_label!r}"
            )
        # M8 today; future multi-floor operators extend here.
        return frozenset({
            FloorImpact(
                label=source.master_bedroom_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
            FloorImpact(
                label=new_master_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
        })
    else:
        if direct_floor_label is None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: direct_floor_label required for "
                f"per-floor operator {operator}"
            )
        if new_master_floor_label is not None:
            raise OrchestrationProtocolError(
                f"affected_floor_set: new_master_floor_label MUST be None "
                f"for per-floor operator {operator}; got "
                f"{new_master_floor_label!r}"
            )
        # Per-floor operators: M0-M7, M9.
        return frozenset({
            FloorImpact(
                label=direct_floor_label,
                kind="direct",
                requires_cascade=True,
                requires_validation_only=False,
            ),
        })
```

**Hardcoded "exactly two floors affected"** (current § 3.4 step 5) becomes a SPECIFIC CASE of the general contract: `affected_floor_set(M8, source, new_master_floor_label=L)` returns two `FloorImpact(kind="direct", requires_cascade=True)` entries (old master + new master L). The orchestrator uses these to decide which floors need cascade re-runs vs which can be reused as-is. v1.5's implementation has exactly the same runtime behaviour as v1.4 (every affected floor has `requires_cascade=True`); v1.5's split-kwarg API just makes the contract self-documenting.

**Why this refinement now**: when B-C11A-7 cross-floor invalidation graph lands, the orchestrator will need to know "do I run a full cascade on this floor, or just re-check constraints?" Without `FloorImpact.requires_cascade`, the only safe default is full cascade — which over-regenerates. With `FloorImpact`, B-C11A-7's extension is one switch from `requires_cascade=True` to `requires_validation_only=True` for transitively-affected floors. The contract is forward-compatible.

**Consumers in v1.5**:
- § 3.4 step 5 (M8 cascade re-run): iterates the `FloorImpact` set, runs cascade on floors with `requires_cascade=True`, runs constraint validation on floors with `requires_validation_only=True` (no such floors today, but the loop is structured for them). Calls `affected_floor_set(M8, source, new_master_floor_label=L)`.
- § 3.2 / § 3.3 (per-floor operators): use `affected_floor_set(operator, source, direct_floor_label=L)` to confirm exactly one `FloorImpact(L, "direct", cascade=True)` is returned before calling `with_floor_replaced(L, new_wzpc)`.

The abstraction is THIN — runtime behaviour unchanged from v1.4, future-amendment ergonomics significantly improved by the structured return type, contract clarity improved by the v1.5 split-kwarg API.

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Reuse existing `_is_multi_floor()` duck-type helper, hardened with `_validate_multi_floor_protocol()` pre-flight** | ✅ | Reject: rewrite to isinstance against MultiFloorDwellingBrief. Spec #1's `is_multi_floor: bool = True` property was deliberately designed for this — using the duck-type preserves the protocol-style boundary documented in Spec #1 v0.5 § 4 and B-MFDB-G. **v1.2 update**: added the pre-flight validator to harden against accidental misrouting (item 1 from v1.1 critique walk). |
| **Tier A / Tier B M6/M7a/M7b applied to ALL FLOORS with bipartite operator+floor interleaving, slot-allocator-limited** | ✅ | Reject (REVERSED FROM v1.1; REFINED FROM v1.2; FURTHER REFINED FROM v1.3): apply only to master floor (v1.1) OR all floors in lex-order (v1.2) OR all floors with operator-major round-robin floor rotation (v1.3). **v1.1's "master-only" was wrong** (v1.1 critique walk item 2). **v1.2's "all-floors lex-order" had floor-axis bias** (v1.2 critique walk item 1). **v1.3's "operator-major round-robin" had operator-axis bias** (v1.3 critique walk item 1). **v1.4's "bipartite round-major interleaving"** achieves bounded imbalance ≤ 1 on both axes under slot truncation, starvation-free. Mathematical property: each operator gets `floor(S/n_ops)` to `ceil(S/n_ops)` slots; each floor gets `floor(S/n_fl)` to `ceil(S/n_fl)` slots. **v1.5 wording correction** (v1.4 critique walk item 2): "uniform" was overstated — actual property is "bounded imbalance ≤ 1, starvation-free." Partial-round positional advantage of ≤ 1 slot per operator exists; filed for future breakup as B-C11A-13. |
| **M8 target-floor selection: deterministic cyclic exploration `sorted_targets[(generation + operator_index) % N]`** | ✅ | Reject (REVERSED FROM v1.1; REVERSED FROM v1.2): pick first eligible (v1.1) OR hash-modulo (v1.2). **v1.1's "first-eligible" caused starvation** in 3+ floor dwellings (v1.1 critique walk item 3). **v1.2's "hash-modulo" did NOT mathematically guarantee target coverage** (v1.2 critique walk item 2) — hash collisions could repeatedly map to the same target probabilistically. **v1.3's cyclic exploration** provides a deterministic coverage guarantee: across N consecutive distinct generations, all N eligible targets are visited exactly once. Replaces hash-modulo with a strictly stronger algorithm. The source_signature dependency drops out of target selection (still used for cache identity per § 3.5). |
| **M8 affects exactly TWO floors (old master + new master), reuse the rest** | ✅ | Reject: re-run C9→C10 on every floor on every M8 invocation. Unnecessary work; per-floor briefs only differ on the two affected floors. **v1.1 footnote remains true in v1.2**: when cross-floor constraints land (Spec #1 B-MFDB-C and related), this assumption gets tested. Filed B-C11A-7 for the dependency-invalidation graph if/when cross-floor cascades become real. |
| **Multi-floor canonical signature = `multi_floor_sig_schema=v1` prefix + per-floor signatures + master label, joined + hashed** | ✅ | Reject: include per-floor briefs in signature. The per-floor wrappers ALREADY incorporate brief identity (via their existing single-floor signature derivation); duplicating would inflate hash collisions. Reject also: skip the master label in the signature. M8 mutations produce structurally identical per-floor candidates (the same per-floor WZPCs, just with different has_master_bedroom flags on the underlying briefs); the master label is the distinguishing structural feature. **v1.2 update**: explicit `multi_floor_sig_schema=v1` prefix (item 5) decouples wrapper-level signature versioning from per-floor signature versioning. |
| **`C11A_CACHE_KEY_VERSION` bump v1.1.0 → v1.3.0 (skip v1.2.0)** | ✅ | Reject: two-step bump (v1.1.0 → v1.2.0 at Spec #3 build, then v1.2.0 → v1.3.0 at Spec #4 build). Specs #3 and #4 ship in the same B-NEW-T3 build session; a two-step bump just produces a transient version that never sees production. Single-step bump is cleaner. **v1.2 update**: hierarchical cache versioning (per-component / per-schema independent versions) deferred to Spec #2 B-C9-C overlap (cross-spec concern). |
| **Multi-floor family ID = label-preserving aggregation: `multi_floor:ground=A\|first=B`** | ✅ | Reject (REVERSED FROM v1.1): sorted-by-family aggregation (`multi_floor:A,B`). **v1.1's sorted-family was wrong** (item 4 from v1.1 critique walk) — collapsed architecturally-distinct configurations like `[ground=A, first=B]` and `[ground=B, first=A]` into the same family ID, causing false equivalence + incorrect slot pooling + evolutionary diversity collapse. **v1.2's label-preserving aggregation** sorts by label for determinism while preserving the label-family pairing. |
| **Spec #2 v0.11 § 3.10 trust boundary owned by Spec #3 construction guard + pipeline failure-mode handler, NOT a redundant v1.x-level assertion** | ✅ | Reject: add a redundant assertion in `mutate_topologies` post-C9 fan-out. Redundant assertions on already-unreachable states are noise; Spec #3 MFWZP-5/6 already make the bad state structurally impossible. The pipeline boundary's job is to handle the `ValueError` that Spec #3 raises (as `orchestration_state_drift`, per the v1.2 refined failure taxonomy), not to re-prove the invariant. |
| **M8 failure taxonomy: `no_viable_master_target` / `c9_generation_failed` / `c10_validation_failed` / `orchestration_state_drift:mfwzp1..6`** | ✅ | Reject (REFINED FROM v1.1; further refined FROM v1.2): single coarse `c9_c10_cascade_failed` (v1.1) OR single bucket `orchestration_state_drift` (v1.2). **v1.2's single `orchestration_state_drift` bucket was too broad** (v1.2 critique walk item 12) — collapsed MFWZP-1 through MFWZP-6 invariant failures into one category, losing root-cause telemetry. **v1.3's invariant-specific variants** (`orchestration_state_drift:mfwzp5` etc.) preserve diagnostic granularity. Pattern matching on `invalidity_reason.startswith("orchestration_state_drift:")` still works as catch-all for orchestration bugs. |
| **Pre-flight brief/source alignment validator (`_validate_multi_floor_alignment`)** | ✅ | Reject (NEW IN v1.2): rely on implicit "labels match" expectation. v1.1 said source labels "must match" brief labels but never said HOW that match is verified. A drifted source-vs-brief would produce silent wrong mutations. The explicit pre-flight (item 9 from v1.1 critique walk) catches drift before mutation dispatch. |
| **Lineage `floor_label_affected: str \| None` field** | ✅ | Reject: omit per-floor causality from lineage. v1.1's lineage extension said "operator=M_X, floor_label=L" inline but didn't define the field as part of the lineage data model. v1.2 adds it as an explicit field. **Lightweight version** of the v1.1 critique item 10 request; full ancestry chain filed as B-C11A-8. |
| **Property tests for orchestration invariants** | ✅ | Reject (NEW IN v1.2): rely only on example-based tests. Multi-floor orchestration has combinatorial state interactions (floor ordering × mutation ordering × cache recursion × lineage aggregation); example tests miss combinatorial edge cases (item 11 from v1.1 critique walk). **v1.3 refinements** (v1.2 critique walk items 7 + 13): property tests reworded as conditional / under-successful-operators-only (since operators may legitimately return invalid); `max_examples` bumped from 50 to 100. |
| **Marker-attribute candidate detection (`__multi_floor_candidate__: bool = True` class attribute)** | ✅ | Reject (NEW IN v1.3, replaces v1.2's name-based): `type().__name__ == "MultiFloorWetZonePlannedCandidate"` + module-path matching. **v1.2's name-based detection was brittle** (v1.2 critique walk item 11) — breaks under refactor / subclass / proxy. **v1.3's marker-attribute** is refactor-safe, subclass-friendly, proxy-compatible. The marker is a class attribute (NOT a dataclass field), so it's hash-irrelevant and does NOT violate Spec #3 v0.3 LOCKED's runtime contract. |
| **`affected_floor_set(operator, source)` returns `frozenset[FloorImpact]` (structured)** | ✅ | Reject (NEW IN v1.3; REFINED IN v1.4): hardcode "exactly two floors affected" in M8 step 5 (pre-v1.3), OR return `frozenset[str]` (v1.3). **v1.2's hardcoded assumption was future-incompatible** (v1.2 critique walk item 15). **v1.3's bare `frozenset[str]`** couldn't express direct-mutation vs transitive-invalidation distinctions (v1.3 critique walk item 6) — every affected floor would force full cascade when B-C11A-7 lands, over-regenerating. **v1.4's `frozenset[FloorImpact]`** uses a structured return type with `kind` + `requires_cascade` + `requires_validation_only` fields. v1.4 runtime behaviour is identical to v1.3 (every direct-mutation floor has `requires_cascade=True`); the structured type just makes B-C11A-7's extension additive. |
| **Determinism tier-table (§ 3.4.1)** | ✅ | Reject (NEW IN v1.4): leave structural-vs-exploration distinction at the conceptual level (v1.3 had only the concept, not the tier-to-system mapping). **v1.3's conceptual split was useful but ambiguous** (v1.3 critique walk item 3) — downstream systems' tier dependencies weren't enumerated, leading to potential confusion ("does C11a cache rely on structural or exploration determinism?"). **v1.4's tier-table** explicitly maps Tier 1 (structural identity) / Tier 2 (operator scheduling) / Tier 3 (evolutionary trajectory) to specific downstream systems and their dependencies. The table is the contract C11b will bind against. |

---

## § 5 — Test plan

### § 5.1 — New test files / additions

**8 new tests** in a new file `buildemup/tests/test_c11a/test_subsession7_multi_floor.py`:

1. `test_orchestrator_accepts_multi_floor_brief`: `mutate_topologies` with a `MultiFloorDwellingBrief` doesn't error out.
2. `test_orchestrator_dispatches_per_floor_for_tier_a`: a Tier A operator (e.g., M2) applied to a 2-floor candidate produces a wrapper where exactly the targeted floor's per-floor candidate changed; the orchestrator dispatches M2 to multiple floor targets across the slot allocator's budget per v1.4 bipartite interleaving (test parameterizes over both targeted floors and asserts each produces a wrapper modifying exactly that floor).
3. `test_orchestrator_dispatches_per_floor_for_tier_b_m6_m7`: same shape for M6, M7a, M7b — all-floors dispatch with bipartite interleaving, slot-allocator-limited.
4. `test_m8_real_execution_produces_wrapper_with_master_swapped`: M8 applied to a 2-floor candidate (master on ground) produces a new wrapper with master on first.
5. `test_m8_target_floor_selection_is_cyclic_deterministic` (v1.5 wording correction per item 5 from v1.4 critique walk — fixes off-by-one): M8 applied twice at the same `(generation, operator_index)` produces the same target (determinism). M8 on a 3-floor dwelling visits each eligible non-master target exactly once across **N = len(eligible_targets) distinct generation values**. For a 3-floor dwelling with master on ground and bedrooms on both non-master floors, **N = 2** (NOT 3 — eligible targets exclude the current master). For a 4-floor dwelling with master on ground and bedrooms on all 3 non-master floors, **N = 3**. The general rule: `N = num_floors - 1` when all non-master floors have bedroom_count ≥ 1; fewer when some non-master floors lack bedrooms. Test parameterizes over (num_floors, bedroom_count_per_floor) combinations.
6. `test_m8_no_viable_target_returns_invalid`: M8 on a 2-floor dwelling where the non-master floor has bedroom_count=0 returns `valid=False, invalidity_reason="no_viable_master_target"`.
7. `test_m8_c9_generation_failed_returns_invalid_with_reason`: simulate C9 failure on the new master floor; M8 returns `valid=False, invalidity_reason="c9_generation_failed"`.
8. `test_m8_orchestration_state_drift_mfwzp5_caught_as_pipeline_failure`: force a scenario where the assembled wrapper would fail MFWZP-5 (e.g., by mocking C9 to produce zero masters on both affected floors); M8 returns `valid=False, invalidity_reason="orchestration_state_drift:mfwzp5"`. Additional parameterized test cases cover each MFWZP-N variant (MFWZP-1 through MFWZP-6).

**5 new tests** in `buildemup/tests/test_c11a/test_subsession5_candidate_context.py` (existing file):

9. `test_is_real_multi_floor_candidate_detects_wrapper_type`.
10. `test_derive_canonical_signature_multi_floor_dispatch`.
11. `test_derive_canonical_signature_multi_floor_includes_master_label`.
12. `test_derive_canonical_signature_multi_floor_recursive_per_floor`: changing one floor's underlying topology changes the wrapper's signature.
13. `test_c11a_cache_key_version_is_v1_3_0`: bumped from v1.1.0 (Spec #2 baseline).

**3 new tests** in `buildemup/tests/test_c11a/test_subsession4_family_slot_allocator.py` (existing file):

14. `test_family_id_multi_floor_aggregation`: wrapper's family ID is `"multi_floor:first=F2|ground=F1"` where F1 is ground's family and F2 is first's family (label-preserving aggregation per v1.2 item 4, sort by label per v1.3 item 3).
15. `test_family_id_multi_floor_deterministic_under_floor_reorder`: even if the tuple order differs, the family ID is the same (because of the sort).
16. `test_family_id_single_floor_unchanged`: existing single-floor family ID derivation is unaffected.

**2 new tests** for the lineage classifier extension:

17. `test_lineage_classifier_per_floor_operator_tracks_floor_label`.
18. `test_lineage_classifier_m8_dwelling_level_no_per_floor_family_change`.

**4 new cross-spec integration tests** in `buildemup/tests/test_integration/test_b_new_t3_pipeline.py` (NEW file, NEW in v1.4 per item 10 from v1.3 critique walk):

These tests exercise the full B-NEW-T3 pipeline end-to-end: Spec #1 → C9 → C10 → Spec #3 → C11a. Component-local tests alone don't catch cross-spec semantic drift (e.g., a future change to Spec #1's floor-label normalization that breaks Spec #3's ancestry walk; a future change to C9's master-flag handling that breaks C11a's M8 cascade).

25. `test_b_new_t3_full_pipeline_2_floor_no_mutation`: construct a 2-floor `MultiFloorDwellingBrief` (master on ground); fan out to per-floor `FloorRoomBrief` via `iter_floors_with_master_flag`; run C9 per floor; run C10 per floor; assemble `MultiFloorWetZonePlannedCandidate`; verify all 6 invariants MFWZP-1 through 6 hold. **Asserts cross-spec semantic continuity without C11a involvement.**
26. `test_b_new_t3_full_pipeline_with_m8_mutation`: same setup as #25, but feed the assembled wrapper into `mutate_topologies` with `force_operator=M8`; verify the M8 result wrapper has master on the OTHER floor; assert all invariants hold; assert lineage records the dwelling-level transition; assert the resulting wrapper's `derive_canonical_signature` is distinct from the input's.
27. `test_b_new_t3_full_pipeline_with_tier_a_mutation`: feed the wrapper into `mutate_topologies` with `force_operator=M2`; verify only the targeted floor's WZPC changed; verify the wrapper's master designation is preserved across the mutation; verify lineage records the per-floor transition with correct `floor_label_affected`.
28. `test_b_new_t3_full_pipeline_3_floor_master_cycle` (v1.5 wording correction per item 5): construct 3-floor brief (master on ground). With master on ground, eligible targets = {first, second} → **N = 2** (not 3 — current master is excluded). Apply M8 across 2 distinct generations and verify cyclic target-selection covers both eligible non-master floors exactly once. Then apply M8 to one of the resulting wrappers (which has master on a different floor); its eligible targets are again 2 floors but a different set. Verify across multiple M8 applications that (a) each intermediate wrapper passes MFWZP-5 (exactly one master globally), (b) the cyclic algorithm produces deterministic target sequences given fixed `(generation, operator_index)` inputs, (c) no starvation: every eligible target is reached eventually.

**Total**: **18 + 4 = 22 new example-based tests** PLUS new property-test subsection (see § 5.1.1 below).

### § 5.1.1 — Property tests (NEW in v1.2 per item 11 from v1.1 critique walk; refined in v1.3 per items 7 + 13 from v1.2 critique walk)

Example-based tests alone are insufficient for orchestration invariants
because multi-floor state interactions are combinatorial (floor
ordering × mutation ordering × cache recursion × lineage aggregation ×
invariant preservation). Add **~5 property tests** in
`buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py`
using Hypothesis (if available in the project; otherwise parameterized
exhaustive small-state tests).

**Property reformulations** (item 7 from v1.2 critique walk): v1.2 phrased property tests as unconditional guarantees ("all eligible targets covered," "invariants preserved under arbitrary sequences"). Reviewer correctly flagged that operators may legitimately return `valid=False`, breaking unconditional preservation. v1.3 reformulates as conditional / under-successful-operators-only:

19. **Signature determinism**: for any valid `MultiFloorWetZonePlannedCandidate`, `derive_canonical_signature(c)` returns the same string across N invocations within the same process. Property: idempotent + pure. (No conditional needed — purity holds unconditionally.)
20. **Family-ID determinism**: for any valid wrapper, `multi_floor_family_id(c)` is invariant under tuple permutations that produce the same label-family pairing set. Property: deterministic under permutations preserving label-family pairs. (Conditional: requires preserving the pairing set — not all permutations.)
21. **Master-uniqueness preservation across SUCCESSFUL operator sequences** (REWORDED in v1.3): starting from a valid wrapper, for any sequence of operator applications where each application returns `valid=True`, the resulting wrapper has MFWZP-5 (exactly one master bedroom globally) holding at every step. Operator applications returning `valid=False` are skipped (their `invalidity_reason` is logged but doesn't break the chain). Property: **conditional** invariant preservation — under successful operators only.
22. **Cache-key stability under structurally-equivalent reconstruction**: constructing two `MultiFloorWetZonePlannedCandidate` instances from the same set of per-floor candidates + same master label produces identical cache keys. Property: structural equality → cache key equality. (No conditional needed.)
23. **M8 cyclic target-selection coverage** (REWORDED in v1.3 + v1.5 off-by-one correction per item 5 from v1.4 critique walk): applying M8 to the same source across **N distinct generation values where N = len(eligible_targets)** visits every eligible target exactly once. Note: eligible_targets EXCLUDES the current master floor, so for a num_floors-floor dwelling, **N = num_floors − 1** when all non-master floors are eligible (have bedroom_count ≥ 1); fewer when some non-master floors lack bedrooms. Property: **deterministic coverage** under cyclic exploration. The cyclic algorithm provides this as a mathematical guarantee, not a statistical property.
24. **50-step stateful mutation chain preserves invariants** (NEW in v1.4 per item 7 from v1.3 critique walk): starting from a valid 3-floor `MultiFloorWetZonePlannedCandidate`, apply a sequence of 50 random operator selections (uniform across M0, M2, M3, M4, M5, M6, M7a, M7b, M8, M9, skipping operators returning `valid=False`). After every successful step, assert MFWZP-1 through MFWZP-6 hold on the current wrapper. The chain models longer-running evolutionary trajectories than single-step properties — catches accumulated-state-divergence bugs (lineage drift, cache aliasing, wrapper reconstruction accumulation, stale family aggregation) that single-step property tests miss. This is one CI-affordable stateful test; **nightly stress fuzzing with 100+ step chains** filed as **B-C11A-12**.

Hypothesis-style generators for multi-floor candidates: use the fixture helper
at `buildemup/tests/_multi_floor_fixtures.py` (added per § 5.3) parameterized
over (floor_count: 2..4, master_floor_index: 0..floor_count-1, per_floor_topology_seed: int).

**Property-test acceptance gate** (item 13 from v1.2 critique walk): bumped to `max_examples=100` for CI runs (was `max_examples=50` in v1.2). Combinatorial state space is large enough that 50 examples may miss edge interactions; 100 provides more coverage without significantly slowing CI. **Nightly stress fuzzing** infrastructure with `max_examples=1000` + long mutation-chain testing filed as **B-C11A-12** when the stress-fuzz framework becomes available in the project.

### § 5.2 — Existing test regression

Per § 3.10 backwards-compat guarantee: every existing C11a test must pass unchanged modulo the cache-key-version constant tests, which adjust to v1.3.0 directly.

Project total after Spec #2 + #3 + #4 build: **2769 + 22 + ~5 property tests = 2796 passed / 2 skipped / 0 regressions** (approximate; property test count is conservative — Hypothesis may generate more under-the-hood examples, but pytest reports them as 1 test each; 4 of the 22 example-based tests are the new cross-spec integration tests in `test_b_new_t3_pipeline.py`).

### § 5.3 — Test fixtures

Multi-floor test fixtures don't yet exist (S40-continuation memory note). The build session must add a fixture helper, likely at `buildemup/tests/_multi_floor_fixtures.py`:

```python
def make_two_floor_brief_with_master_on(label: str = "ground") -> MultiFloorDwellingBrief: ...
def make_three_floor_brief_with_master_on(label: str = "ground") -> MultiFloorDwellingBrief: ...
def run_multi_floor_c9_c10_pipeline(brief: MultiFloorDwellingBrief, ...) -> MultiFloorWetZonePlannedCandidate: ...
```

This fixture helper is build-session work, not part of this spec; flagged here for build-session visibility.

---

## § 6 — Out-of-scope

- **Per-floor exploration policy refinement** (weighted attempts, generation-aware budgets, adjacency-aware floor prioritization): v1.2 applies Tier A/B to all floors uniformly; B-C11A-1 + B-C11A-5 cover refinements.
- **Non-deterministic / stochastic M8 target selection** (random, scoring-driven, exploration beyond hash-determinism): v1.2 uses hash-deterministic selection across all eligible targets; further variants filed as B-C11A-2 (largely-reduced scope).
- **M8 multi-step swaps** (sequential rearrangement of N floors): v1.1's M8 is a single swap.
- **Multi-floor adjacency / circulation / vertical alignment scoring**: post-v1 (related Spec #1 B-MFDB-C).
- **Multi-floor C5 topology selection**: out of scope; C5 currently operates per-floor at brief-capture time and is upstream of C11a.
- **C11b NSGA-II multi-floor scoring**: scoring component, not orchestration; consumes the wrappers this amendment produces.
- **Persisted cache migration v1.1.0 → v1.3.0**: cache is in-memory only currently; no migration needed.
- **Spec restructure into normative/rationale appendices** (Spec #1 B-MFDB-N, Spec #2 B-C9-G overlapping): post-v1.
- **Architectural test infrastructure** (Spec #2 B-C9-E, Spec #3 B-MFWZP-G overlapping): post-v1.

---

## § 7 — Backlog items deferred

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-C11A-1** (NEW) | Tier A / Tier B M6/M7a/M7b multi-floor expansion to non-master floors. **NOTE**: in v1.2 this item is partially addressed — Tier A/B now apply to ALL floors, slot-allocator-limited (no longer master-only). What remains for B-C11A-1: refined per-floor exploration policy when adjacency-aware scoring lands or when stress fuzz shows uniform per-floor attempt order produces undesirable bias | When adjacency-aware multi-floor scoring lands (likely C11b NSGA-II amendment) OR when stress fuzz / search-space breadth telemetry shows bias | Open (partial in v1.2; further refinement post-v1) |
| **B-C11A-2** (NEW) | **NOTE**: in v1.2 this item is REDUCED scope — M8 target selection is now hash-deterministic across all eligible targets, solving the original "first-eligible starvation" concern. What remains for B-C11A-2: non-deterministic / true-random / scoring-driven target selection if hash-determinism proves insufficient for evolutionary diversity | When dwelling search-space depth becomes a real bottleneck despite hash-based exploration OR when C11b explorer wants stochastic M8 target mixing | Open (largely addressed in v1.2; full reduction post-v1) |
| **B-C11A-3** (NEW) | M8 multi-step / N-floor rearrangement (general permutation of master designation across ≥3 floors via multi-step M8 application). v1.2's M8 is still a single swap per application | When ≥3-floor luxury / commercial paths surface requiring multi-floor master complexity | Open (post-v1) |
| **B-C11A-4** (NEW) | Multi-floor cache hit/miss telemetry. Per-floor cache hits for un-affected floors during M8 should be observable | When cache-tuning becomes a real perf concern | Open (post-v1) |
| **B-C11A-5** (NEW from v1.1 critique walk item 2) | Per-floor attempt weighting for slot-budget tuning. v1.2 generates per-floor attempts in uniform `(operator_index, floor_index)` order; weighted variants (e.g., 70% master / 30% non-master, or generation-aware budgets) can be added without changing the contract. Useful if uniform order produces evolutionary bias | When stress-fuzz / search-breadth telemetry shows uniform-order bias OR when C11b scoring telemetry shows master-floor over-exploration | Open (post-v1) |
| **B-C11A-6** (NEW from v1.1 critique walk item 6; LARGELY ADDRESSED in v1.3 per v1.2 critique walk item 11) | Replace name-based detection with marker-attribute or formal Protocol/ABC. **v1.3 lands the marker-attribute fix for multi-floor wrapper** (`__multi_floor_candidate__` on Spec #3's class). Residual scope for B-C11A-6: extend the marker-attribute migration to `is_real_wet_zone_candidate` (single-floor C10 wrapper) and any future detection sites, OR migrate to formal Protocol typing project-wide (overlaps Spec #1 B-MFDB-G) | When single-floor detection breaks in practice OR project-wide Protocol migration | Open — multi-floor scope landed in v1.3; single-floor + Protocol-wide remaining |
| **B-C11A-7** (NEW from v1.1 critique walk item 7; PARTIALLY ADDRESSED in v1.4) | M8 cross-floor cascade invalidation graph. v1.2's M8 assumes exactly two floors change (old master + new master). When vertical wet-stack constraints / plumbing alignment / circulation coupling / adjacency scoring land (Spec #1 B-MFDB-C and related), untouched floors may become indirectly invalidated by an M8 swap. **v1.4 adds the `FloorImpact` structured return type** (§ 3.11 refinement) that B-C11A-7's expansion will populate with `kind="indirect", requires_validation_only=True` for transitively-affected floors. The abstraction layer is fully ready; B-C11A-7's residual scope is just populating it with real cross-floor logic when constraints arrive | When Spec #1 B-MFDB-C (per-floor staircase landing constraints) lands OR when any cross-floor structural constraint enters the pipeline | Open — gated on B-MFDB-C; v1.3 + v1.4 added abstraction layers |
| **B-C11A-8** (NEW from v1.1 critique walk item 10) | Full multi-floor lineage extension: floor ancestry IDs, mutation provenance chains, master-transition events, per-floor generation counters. v1.2's minimum addition is `floor_label_affected: str \| None` only | When NSGA-II explainability tooling needs the richer model OR when debugging multi-floor evolution becomes a real workflow concern | Open (post-v1) |
| **B-C11A-9** (NEW from v1.1 critique walk item 13) | Wrapper-reassembly allocation churn reduction. Repeated `with_floor_replaced()` calls in long evolutionary runs may produce avoidable allocation overhead. Options: batched floor-replacement APIs, structural sharing / persistent data structures, builder-style assembly before final immutable freeze | When perf telemetry shows allocation overhead is a real bottleneck during large evolutionary runs | Open (post-v1) |
| **B-C11A-10** (NEW from v1.2 critique walk item 9) | Adaptive Tier B quota tuning. v1.3 documents that Tier B per-attempt cost is unchanged from single-floor (one cascade per attempt) and total cost is bounded by `slot_count × per_attempt_cost`. But: adaptive per-generation compute budgets, operator throttling based on observed cost, or dynamic Tier B slot adjustment could improve perf on long evolutionary runs. The slot allocator is the budget knob today; this item makes the knob adaptive | When perf profiling shows Tier B compute is a bottleneck OR when C11b NSGA-II adds cost-aware operator selection | Open (post-v1) |
| **B-C11A-11** (NEW from v1.2 critique walk item 10) | Strategy-pattern extraction for orchestration policies. v1.3 embeds floor-selection / M8-target-selection / attempt-budget policies inline in the orchestrator (`_generate_per_floor_attempts`, `_pick_m8_target`). Extracting `FloorSelectionPolicy` / `M8TargetPolicy` / `AttemptBudgetPolicy` as pluggable strategy interfaces would improve modularity and let C11b coordinate exploration policy across components. Significant abstraction layer; scope-creep for v1.3 build. **v1.4 reviewer pressed for pre-LOCK promotion; rejected per scope-creep rationale** | When C11b NSGA-II lands and needs to coordinate exploration policy with C11a OR when multiple alternative exploration policies need to be A/B-tested in production | Open (post-v1) |
| **B-C11A-12** (NEW from v1.2 critique walk item 13) | Nightly stress fuzzing for orchestration invariants. v1.3 bumps property-test `max_examples=100` for CI but combinatorial state space (floor permutations × operator sequences × regeneration paths × lineage interactions) needs higher coverage than CI can afford. Nightly stress fuzzing with `max_examples=1000` + long mutation-chain testing (e.g., 50-100 sequential operator applications) catches rare edge interactions. **v1.4 adds one 50-step stateful chain test in CI** (item 7 from v1.3 critique walk); the 100+ step nightly version remains in this backlog item | When stress-fuzz framework becomes available in the project OR when rare orchestration failures are observed in production search runs | Open (post-v1) |
| **B-C11A-13** (NEW from v1.3 critique walk item 2; SCOPE EXPANDED in v1.6 per v1.5 critique walk items 1 + 2) | Three exploration-fairness breakers (any one of the three suffices; pick based on integration complexity at trigger time):<br>(a) Source-signature-stable-shuffle M8 target selection — replaces cyclic `sorted_targets[(generation + operator_index) % N]` with `permutation = stable_shuffle(targets, source_signature); index = generation % N`. Breaks per-candidate phase-locking.<br>(b) Operator-start-index rotation by generation — `start = generation % n_ops` for bipartite interleaving. Prevents low-index operators accumulating systematic +1-slot advantage across thousands of generations.<br>(c) Per-generation cyclic operator offset — composes with (b). Distributes operator-axis bias across generations rather than accumulating it.<br>All three preserve determinism + coverage + replay reproducibility. Without one of these, v1.6's bipartite interleaving + cyclic M8 selection accumulate deterministic positional bias over long evolutionary runs | When C11b NSGA-II coordinates exploration pressure across population members OR when empirical search runs show resonance / accumulated bias / phase-locked exploration patterns | Open (post-v1) |
| **B-C11A-14** (NEW from v1.3 critique walk item 3) | Generation provenance in lineage metadata. v1.4's lineage model has `floor_label_affected: str \| None` per v1.2 item 10 (lightweight). Adding `generation: int` + `operator_index: int` to lineage entries would enable Tier 3 (evolutionary trajectory) reproducibility — replay debugging would have full operator-scheduling context, not just structural identity | When debugging multi-floor evolution becomes a workflow concern OR when explainability tooling needs trajectory replay | Open (post-v1); overlaps B-C11A-8 |
| **B-C11A-15** (NEW from v1.3 critique walk item 5) | Memoized per-floor signature caching for multi-floor `derive_canonical_signature`. v1.4's recursive signature derivation costs `O(num_floors × signature_depth)` per call; called from cache + orchestration + lineage. Memoizing per-floor signatures on the immutable wrapper (lazy field, invalidated only on floor mutation, which mutations already do via `with_floor_replaced`) would amortize the cost. Merkle-style aggregation is the structural-sharing variant | When perf profiling shows signature derivation is a bottleneck OR when persistence layer needs per-floor signature reuse for cache locality | Open (post-v1); overlaps B-C11A-9 (wrapper allocation reduction) |
| **B-C11A-16** (NEW from v1.5 critique walk item 3) | Optional generation-contract validation mode. v1.5 § 3.4.2 formalizes the generation contract (ownership, monotonicity, replay, reset) but explicitly does NOT enforce monotonicity / uniqueness / lineage consistency. Add a `validate_generation_contract=True` config flag (or similar) that enables: (a) monotonicity checks — fail-fast if a call's generation value is ≤ any previously-seen generation in the search run; (b) duplicate detection within a session; (c) lineage-generation assertions — assert that lineage `generation` field matches the call's generation parameter; (d) replay-trace verification hooks for deterministic-replay debugging. Without this, callers can silently violate the contract; with it, contract violations fail-fast at the orchestrator boundary | When debugging reveals contract violations in practice OR when production traces show non-monotonic generation values OR when replay-debugging infrastructure becomes a real workflow | Open (post-v1) |
| **B-C11A-17** (NEW from v1.5 critique walk item 6) | Canonical floor identity primitive separate from display labels. Today, floor labels do two jobs simultaneously — display semantics ("ground", "first", "mezzanine") AND machine identity (sort keys, cache identity, family ID derivation, ancestry equality). Spec #1 `_normalize_label` handles character-level variation but not semantic equivalence: `"g"` / `"GF"` / `"ground"` are three distinct identifiers even when they describe the same architectural floor. Introduce `floor_uid: str` (UUID-like) or `canonical_floor_index: int` (elevation-ordered) independent from display labels. Labels become presentation metadata only. Removes the cache-miss-on-relabeling fragility for systems where labels evolve | When Spec #1 B-MFDB-A (`floor_elevation_m`) lands and elevation-ordered canonical sort replaces lexical sort, OR when persistence layer surfaces label-evolution as a real workflow concern, OR when multi-user / commercial path needs label-independent floor identity | Open (post-v1); coordinates with Spec #1 B-MFDB-A |
| **B-C11A-18** (NEW from v1.5 critique walk item 12) | Spec restructure into normative contracts + appendices + diagrams. v1.6 is ~1100 lines and includes five critique-walk delta sections (§ 0.1 through § 0.5). At this scale, spec complexity itself becomes a defect source — future maintainers may misunderstand subtle contracts, patch locally without seeing global invariants, increase onboarding cost. Restructure into: normative contracts (the locked behavioral specification), rationale appendix (design choices considered + reversal histories), algorithm appendix (interleaving, cyclic selection, FloorImpact), invariants appendix (cross-spec invariants + identity systems), orchestration semantics appendix (Tier 1/2/3 determinism + generation contract), architecture/execution-flow/identity-system diagrams. Overlaps Spec #1 B-MFDB-N (spec restructure into normative/rationale/forward-compat sections) — could be done as one cross-spec restructure project | When project enters maintenance mode (post-v1 LOCK, before significant new architectural amendments) OR when onboarding cost becomes a measurable workflow concern OR when a major refactor needs the spec as authoritative reference and current 1100-line form impedes navigation | Open (post-v1); overlaps Spec #1 B-MFDB-N |

---

## § 8 — Build-session readiness

After Ramalingam LOCK (and assuming all four specs are LOCKED — this amendment is the last):

**Files modified**:

- `buildemup/domain/floor_brief.py`: add `has_master_bedroom: bool = True` (per Spec #2). ~3 lines + docstring.
- `buildemup/components/c09/room_sizer.py`: 2 line-edits at lines 498 and 548 (per Spec #2).
- `buildemup/components/c11a/cache.py`: bump `C11A_CACHE_KEY_VERSION` to `"v1.3.0"`.
- `buildemup/components/c11a/source_signature.py`: add multi-floor dispatch in `derive_canonical_signature`; add `_derive_multi_floor_canonical_signature` helper with `multi_floor_sig_schema=v1` prefix (v1.2 item 5).
- `buildemup/components/c11a/candidate_context.py`: add `is_real_multi_floor_candidate` using **marker-attribute lookup** `getattr(obj, "__multi_floor_candidate__", False) is True` (v1.3 item 11).
- `buildemup/components/c11a/orchestrator.py`: add per-floor expansion logic in `mutate_topologies`; add Tier A / B per-floor dispatch helpers with **bipartite operator+floor interleaving** via round-major `_generate_per_floor_attempts` (v1.4 item 1); add `_validate_multi_floor_protocol()` with cardinality check (v1.3 item 4) and `_validate_multi_floor_alignment()` pre-flights; add `affected_floor_set(operator, source) -> frozenset[FloorImpact]` abstraction with **structured FloorImpact return type** (v1.4 item 6).
- `buildemup/components/c11a/operators/m8_vert_rearr.py`: replace stub with real `_build_m8_mutation` using **cyclic deterministic target selection** `sorted_targets[(generation + operator_index) % N]` (v1.3 item 2). NO SHA256 dependency — simpler than v1.2's hash-modulo.
- `buildemup/components/c11a/family_slot_allocator.py`: add multi-floor family aggregation with label-preserving pairs (v1.2 item 4).
- `buildemup/components/c11a/lineage.py`: add multi-floor lineage extension with `floor_label_affected: str | None` field (v1.2 item 10).
- `buildemup/components/c11a/errors.py`: add `OrchestrationError` base + `OrchestrationProtocolError` + `OrchestrationAlignmentError` (v1.2 items 1 + 9).
- `buildemup/components/c11a/schema.py`: add `FloorImpact` frozen dataclass (v1.4 item 6); extend `MutationApplicationResult.invalidity_reason` taxonomy with **invariant-specific drift variants** `orchestration_state_drift:mfwzp1` through `mfwzp6` (v1.3 item 12), plus `c9_generation_failed`, `c10_validation_failed`, `no_viable_master_target`.
- **Spec #3 coordinated build addition** (v1.3 item 11): add `__multi_floor_candidate__: bool = True` as a **class attribute** (NOT a dataclass field) on `MultiFloorWetZonePlannedCandidate`. This is implementation-level — Spec #3 v0.3 LOCKED's runtime contract (invariants MFWZP-1 through 6, helpers, mutation semantics, equality, hash) is unchanged. The class attribute does NOT participate in dataclass equality or hash.
- **Plumbing**: if `generation` is not currently in `config` or threaded through the operator-attempt loop, add it (v1.3 item 2 requirement — cyclic algorithm needs it). Build-session detail.

**Files created**:

- `buildemup/domain/multi_floor_brief.py` (per Spec #1, ~210 lines).
- `buildemup/domain/multi_floor_candidate.py` (per Spec #3, ~250 lines).
- `buildemup/components/c11a/m8_floor_swap_real.py` (this amendment, ~150 lines).
- `buildemup/tests/test_domain_multi_floor_brief.py` (per Spec #1, ~45 tests).
- `buildemup/tests/test_domain_multi_floor_candidate.py` (per Spec #3, ~35 tests).
- `buildemup/tests/test_c11a/test_subsession7_multi_floor.py` (this amendment, ~18 tests).
- `buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py` (v1.2 item 11 + v1.4 item 7, ~6 property tests including the 50-step stateful chain test).
- `buildemup/tests/test_integration/test_b_new_t3_pipeline.py` (v1.4 item 10, ~4 cross-spec integration tests).
- `buildemup/tests/_multi_floor_fixtures.py` (helper, no tests).

**Tests added**: Spec #2 (~9) + Spec #3 (~35) + this amendment (~18 example-based + ~4 integration + ~6 property tests) = **~72 new tests**.

**Test count after build**: 2760 baseline + 72 = **~2832 passed**, modulo any test-count drift.

**Estimated build effort**: ~3-5 sessions of focused work. v1.4's bipartite interleaving + FloorImpact + tier-table + integration tests add modest implementation complexity vs v1.3. Largest items remain C11a orchestrator multi-floor expansion + M8 real wiring + signature/cache/lineage extensions.

---

## § 9 — Status

- **v1.6 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v1.7 PROPOSED.
- After LOCK: **B-NEW-T3 build can begin** (all four specs LOCKED).
- **Convergence note**: v1.5 was the first non-behavioral-change round since v1.1. v1.6 is the **second consecutive doc-polish round** — five documentation patches addressing reviewer's v1.5 concerns about cache/exploration identity guard-rails, M8 2-floor optimization framing, floor-label identity overloading, cross-spec coupling visibility, and spec-complexity management. Three new backlog items (B-C11A-16, 17, 18) — generation contract enforcement, canonical floor identity primitive, spec restructure. Zero behavioral changes, zero algorithm changes. Reviewer's v1.5 verdict ("PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope") explicitly recognized this convergence shape. The five concerns reviewer named at the end of the v1.5 critique ("deterministic fairness bias accumulation, cyclic exploration resonance, orchestration centralization, shallow lineage provenance, high cross-spec coupling") are all backlog-tracked items with NSGA-II / C11b / scale-related triggers.

- **Cross-spec governance status** (NEW in v1.6 per item 11 from v1.5 critique walk): C11a v1.6 tightly couples Spec #1 + Spec #2 + Spec #3 + C9 + C10 + future C11b. Semantic drift in any of those can cascade. **Cross-spec governance is intentionally NOT owned by this amendment** — that responsibility lives in:
  - **Spec #2 B-C9-G** (architecture-governance convention for "directly-affects-runtime-behaviour" criterion): owns the principle for when contextual fields can land in domain types across components.
  - **Spec #3 B-MFWZP-J** (cross-spec invariant registry / centralized architectural invariant documentation): owns the cross-spec invariant synchronization concern reviewer raised.
  - **Spec #1 B-MFDB-N** (spec restructure into normative/rationale/forward-compat appendices): owns the spec-complexity management concern reviewer raised.

  Reviewer's v1.5 critique item 11 proposed cross-spec invariant contracts / compatibility matrices / semantic version compatibility assertions / automated contract tests between specs — these all map cleanly to B-MFWZP-J's scope. v1.6 does NOT re-file these in C11a's backlog (would duplicate); cross-references them here so the governance trail is visible from this spec's status.

- **Post-LOCK plan** (NEW in v1.6 per item 12 from v1.5 critique walk): v1.6 is ~1100 lines, including five critique-walk delta sections (§ 0.1 through § 0.5). Reviewer correctly flagged that spec complexity itself becomes a defect source at this scale. Post-LOCK restructure direction: **B-C11A-18** filed for spec-restructure into normative contracts + rationale appendix + algorithm appendix + invariants appendix + orchestration semantics appendix + architecture/execution-flow/identity-system diagrams. Overlaps Spec #1 B-MFDB-N (cross-spec restructure work). NOT pre-LOCK — restructure pre-LOCK would delay B-NEW-T3 build; restructure post-LOCK with the locked spec content frozen is the safer ordering.

---

## § 10 — Rule 9 backlog enumeration

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| Spec #1 | `MultiFloorDwellingBrief` v0.5 LOCKED | DONE | DONE | DONE | DONE |
| Spec #2 | C9 Amendment v0.11 LOCKED | DONE | DONE | DONE | DONE |
| Spec #3 | `MultiFloorWetZonePlannedCandidate` v0.3 LOCKED | DONE | DONE | DONE | DONE |
| **Spec #4** | This amendment | Specs #1+2+3 LOCKED | LOCK pending | IN-FLIGHT | L |
| B-NEW-T3 | M8 multi-floor real upstream wiring | All 4 specs LOCKED | After this LOCKs | GATED — build session begins | L |
| B-C11A-1 | Tier A/B multi-floor exploration policy (partial in v1.2) | This amendment | Adjacency scoring OR search-space bias telemetry | OUT-OF-SCOPE this amendment (partial) | M (post-v1) |
| B-C11A-2 | Non-deterministic M8 target (largely addressed in v1.2 via hash) | This amendment | If hash-determinism proves insufficient | OUT-OF-SCOPE (largely addressed) | S (post-v1) |
| B-C11A-3 | M8 multi-step / N-floor rearrangement | This amendment | ≥3-floor luxury / commercial paths | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-4 | Multi-floor cache telemetry | This amendment | Cache-tuning perf concerns | OUT-OF-SCOPE | S (post-v1) |
| B-C11A-5 | Per-floor attempt weighting | v1.2 critique | Search-breadth telemetry shows bias | OUT-OF-SCOPE | S (post-v1) |
| B-C11A-6 | Marker-attribute / Protocol replacement for `type().__name__` detection | v1.2 critique | Name-based detection breaks in practice | OUT-OF-SCOPE | S (post-v1) |
| B-C11A-7 | M8 cross-floor cascade invalidation graph | v1.2 critique | Spec #1 B-MFDB-C lands | OUT-OF-SCOPE — gated on B-MFDB-C | M (post-v1) |
| B-C11A-8 | Full multi-floor lineage extension | v1.2 critique | NSGA-II explainability tooling | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-9 | Wrapper allocation-churn reduction | v1.2 critique | Perf telemetry | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-10 | Adaptive Tier B quota tuning | v1.3 critique | Perf profiling shows Tier B compute bottleneck | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-11 | Strategy-pattern extraction for orchestration policies | v1.3 critique | C11b NSGA-II coordination OR multi-policy A/B-testing | OUT-OF-SCOPE | L (post-v1) |
| B-C11A-12 | Nightly stress fuzzing for orchestration invariants | v1.3 critique | Stress-fuzz framework available OR rare prod failures observed | OUT-OF-SCOPE (v1.4 adds CI 50-step stateful test) | M (post-v1) |
| B-C11A-13 | Source-signature-stable-shuffle M8 selection (break cyclic periodicity); also covers partial-round positional-advantage breaking via round-start offset rotation per v1.4 critique item 3 | v1.4 critique | C11b coordinates exploration pressure | OUT-OF-SCOPE | S (post-v1) |
| B-C11A-14 | Generation provenance in lineage metadata | v1.4 critique | NSGA-II explainability / trajectory replay | OUT-OF-SCOPE; overlaps B-C11A-8 | S (post-v1) |
| B-C11A-15 | Memoized per-floor signature caching | v1.4 critique | Perf profiling shows signature derivation bottleneck | OUT-OF-SCOPE; overlaps B-C11A-9 | M (post-v1) |
| B-C11A-16 | Optional generation-contract validation mode | v1.5 critique | Debugging reveals contract violations OR replay-debugging workflow | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-17 | Canonical floor identity primitive separate from display labels | v1.5 critique | Spec #1 B-MFDB-A lands OR persistence layer surfaces label-evolution | OUT-OF-SCOPE; coordinates with Spec #1 B-MFDB-A | M (post-v1) |
| B-C11A-18 | Spec restructure into normative + appendices + diagrams | v1.5 critique | Maintenance mode / onboarding-cost concern / major refactor needs spec as ref | OUT-OF-SCOPE; overlaps Spec #1 B-MFDB-N | L (post-v1) |

**Summary**: largest of the four B-NEW-T3 specs. Threads multi-floor through every C11a pipeline stage. **18 total backlog items** (B-C11A-1 through 18) across five critique-walk rounds; v1.6 adds 3 new items (B-C11A-16, 17, 18) — generation contract enforcement, canonical floor identity, spec restructure. v1.6's five spec patches are all documentation/contract guard-rails (zero behavioral changes, zero algorithm changes) — second consecutive doc-polish round after the three-round behavioral-change run completed at v1.4. Reviewer's v1.5 verdict ("PRETTY CLOSE TO LOCK-WORTHY for v1 operational scope") explicitly recognized this convergence shape. After LOCK, the B-NEW-T3 build session begins — the largest implementation work item in S41+.

---

**End of C11a Amendment v1.6 PROPOSED.**
