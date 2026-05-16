# C11A SPEC AMENDMENT v1.1 PROPOSED — multi-floor pipeline rework (B-NEW-T3 enabler #4 of 4)

**Component**: 11a (Topology Mutation Orchestration — SHIPPED at v1.0 LOCKED across multiple sessions; 10/17 Track 3 components, structurally complete with 3/4 Tier B operators wired before this amendment).
**Spec status**: **v1.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-Spec-#3 LOCK.
**Driver**: Spec #4 of 4, the largest. Wires the multi-floor types (Specs #1+#3) and the C9 master flag (Spec #2) through the C11a pipeline. Completes the B-NEW-T3 spec sequence; unlocks the build of M8's real upstream wiring (the last remaining Tier B operator stub).

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v1.1 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v1_1_LOCKED.md` (if approved as-is),
- `..._v1_2_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

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

Dispatch via the existing `_is_multi_floor()` helper at `orchestrator.py:170` (no code change — Spec #1's `is_multi_floor` property already drives the correct branch).

When the brief is multi-floor:
1. The orchestrator derives the per-floor brief tuple via Spec #1's `iter_floors_with_master_flag()` helper, constructing `FloorRoomBrief(...)` instances with `has_master_bedroom` set correctly per floor.
2. The orchestrator expects each source in `sources` to be a `MultiFloorWetZonePlannedCandidate` (Spec #3 wrapper) whose per-floor labels match the brief's floor labels.
3. Per-operator dispatch runs against the wrapper as a single logical source; per-operator implementations decide whether to operate per-floor (M0-M7, M9) or dwelling-level (M8).

### § 3.2 — Per-floor Tier A operator execution

Tier A operators (M0-M5, M9) currently take a `source` (`WetZonePlannedCandidate`) and a `tier_a_context`. In multi-floor mode:

For each candidate in `sources` (a `MultiFloorWetZonePlannedCandidate`):
  For each per-floor `WetZonePlannedCandidate` in `candidate.floors`:
    Apply the operator to that per-floor candidate (existing single-floor logic).
    Collect the result.
  Re-assemble as a new `MultiFloorWetZonePlannedCandidate` via Spec #3's `with_floor_replaced(label, new_wzpc)` helper — replacing only the floor that was actually mutated.

**Critical**: Tier A operators mutate ONE FLOOR per application. M2-bump (e.g., bump bathroom east) operates on one floor's wet-zone plan; other floors are unchanged. The result wrapper preserves master designation and reuses non-target floors as-is.

**Floor selection for Tier A operators**: in v1.1, Tier A operators are applied **only to the master floor** of the dwelling. Rationale: Tier A operators are wet-zone-focused, and the master floor's wet zones (master bedroom + en-suite master bathroom) are the dwelling's most architecturally constrained. Applying Tier A to every floor would inflate the search space N× without proportional value. **Filed for revisit as B-C11A-1** (post-v1: Tier A multi-floor expansion to non-master floors when adjacency-aware scoring lands).

### § 3.3 — Per-floor Tier B M6 / M7a / M7b execution

M6 (wet rotate), M7a (grid bay X scale), M7b (grid bay Y scale) are real single-floor operators (S39 + S40 wiring). In multi-floor mode:

Same dispatch shape as Tier A: applied to the master floor only in v1.1. The Tier B regenerative cascade (C7→C8→C9→C10 for M7a/b; C10 re-run for M6) runs against the master floor's brief and produces a new per-floor `WetZonePlannedCandidate`; the wrapper is re-assembled via `with_floor_replaced`.

**M6 / M7a / M7b multi-floor expansion**: same B-C11A-1 trigger.

### § 3.4 — M8 (`m8_vert_rearr`) real implementation

M8 is the only Tier B operator that operates dwelling-wide. It swaps which floor hosts the master bedroom.

**Algorithm**:

1. Read `source` (a `MultiFloorWetZonePlannedCandidate`). Read `source.master_bedroom_floor_label` (the current master floor).
2. Compute candidate target floors: every floor in `source.floor_labels` EXCEPT the current master that has `bedroom_count >= 1` (per Spec #1 Inv MFDB-4 — the target floor must be able to host the master). Empty target set → M8 returns `MutationApplicationResult(valid=False, invalidity_reason="no_viable_master_target")`.
3. Choose one target floor. Strategy: **deterministic — pick the first eligible floor in floor-tuple order** (consistent with Spec #1's recommended ground-up convention; deterministic for cache reproducibility). Filed as **B-C11A-2** if non-deterministic / exploration-driven target selection becomes useful.
4. Construct the post-mutation `MultiFloorDwellingBrief` via Spec #1's `with_master_on(new_floor_label)`. This re-validates the target floor has bedroom_count ≥ 1.
5. For each floor whose `has_master_bedroom` flag flipped (the old master floor: True → False; the new master floor: False → True), re-run the C9→C10 cascade against the new per-floor brief. **Exactly two floors** are affected. The other floors' per-floor candidates are reused as-is.
6. Assemble the new `MultiFloorWetZonePlannedCandidate` via Spec #3's `with_master_on(new_floor_label, new_per_floor_candidates)`. Spec #3's `__post_init__` re-validates all 6 invariants (MFWZP-1 through 6), most importantly MFWZP-5 (exactly one master bedroom globally) and MFWZP-6 (declared master matches derived).
7. Return `MutationApplicationResult` with the new wrapper.

**Failure modes** (each surfaces as `invalidity_reason` in the result):
- `no_viable_master_target` — no eligible target floor (all non-master floors have bedroom_count=0).
- `c9_c10_cascade_failed` — C9 or C10 raised an exception on the new per-floor brief (e.g., NBC infeasibility on the new master floor).
- `cross_floor_invariant_violated` — Spec #3's `__post_init__` rejected the assembled wrapper. This SHOULD NOT happen if steps 1-5 executed correctly; if it does, it indicates an orchestration drift bug. Caught here as a fail-fast guard.

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

Where `is_real_multi_floor_candidate` mirrors `is_real_wet_zone_candidate` (in `candidate_context.py:338`) — checks `type().__name__ == "MultiFloorWetZonePlannedCandidate"` and module path matches `domain.multi_floor_candidate`.

And `_derive_multi_floor_canonical_signature` computes:

```python
parts: list[str] = []
parts.append(f"multi_floor=true")
parts.append(f"master_floor={source.master_bedroom_floor_label}")
for floor_label, per_floor_wzpc in zip(source.floor_labels, source.floors):
    per_floor_sig = derive_canonical_signature(per_floor_wzpc)  # recurse
    parts.append(f"floor[{floor_label}]={per_floor_sig}")
serialised = "|".join(parts)
return sha256(serialised.encode("utf-8")).hexdigest()[:16]
```

**Rationale**: structural-only canonical signature, mirrors single-floor `derive_canonical_signature`'s 16-hex-char SHA256 output. Includes master designation so M8 mutations produce distinct signatures from M0-M7/M9 mutations even if per-floor signatures coincidentally match.

### § 3.6 — Cache identity

`C11A_CACHE_KEY_VERSION` (in `cache.py:68`) bumps from `"v1.1.0"` (post-Spec-#2) → `"v1.3.0"` (cumulative jump: Spec #3 LOCKED bumped to v1.2.0, this amendment to v1.3.0).

**Why a 2-step jump instead of v1.2.0 → v1.3.0**: Spec #3's LOCKED text references "Initial bump for this spec: bumping from Spec #2's v1.1.0 to v1.2.0." But the bump only takes effect at build time (when the code lands), and Specs #3 + #4 are built in the same B-NEW-T3 session. Practical decision: bump directly to v1.3.0 in one step (this amendment's build session) covering both the new wrapper type (Spec #3) and the multi-floor pipeline (this amendment). Documented here for build-session reference.

`derive_cache_key()` (in `cache.py:231`) interface UNCHANGED — it consumes `derive_canonical_signature` output, which extends transparently via § 3.5.

### § 3.7 — Family slot allocator extension

`family_slot_allocator.py` currently allocates Tier A/B slots per source candidate. The allocator reads per-candidate family ID (from `candidate_context`).

In multi-floor mode: each per-floor candidate has its own family ID; the wrapper's family is the **canonical aggregation** of per-floor families. Aggregation rule:

```python
def multi_floor_family_id(wrapper: MultiFloorWetZonePlannedCandidate) -> str:
    per_floor_family_ids = sorted(
        get_family_id(f) for f in wrapper.floors
    )
    return "multi_floor:" + ",".join(per_floor_family_ids)
```

**Rationale**: a multi-floor candidate's family is the multiset of its per-floor families. Sorted order ensures structural determinism. The `multi_floor:` prefix prevents accidental collision with single-floor family IDs.

### § 3.8 — Lineage classifier extension

`lineage.py`'s classifier currently tracks (source-family → result-family) transitions per operator application. In multi-floor mode:

- Tier A / B M0-M7/M9 (per-floor operators): the family transition is at the per-floor level (the affected floor's family changes); the wrapper's aggregate family also changes (per § 3.7). Lineage records: `operator=M_X, floor_label=L, per_floor_transition=(F1 → F2), wrapper_transition=(W1 → W2)`.
- M8 (dwelling-level operator): the family transition is at the dwelling level. Per-floor families are PRESERVED (the same per-floor brief contents, just with `has_master_bedroom` flipped — which changes the per-floor WZPC but typically not the per-floor family ID, since family ID derives from topology kind + zone bands + structural features, not master designation). The wrapper's transition is `(W1 → W2)` reflecting the master swap.

`MutationLineageDepth` (existing enum) extends to multi-floor naturally — `SHALLOW_TRANSFORM` and `DEEP_TRANSFORM` apply per the existing single-floor semantics, just at the wrapper level.

### § 3.9 — Spec #2 v0.11 § 3.10 trust-boundary assertion — owned where?

Spec #2 v0.11 § 3.10 forward-pointed to this amendment: "Spec #4 (C11a Amendment v1.1) is expected to own this assertion — likely as a post-C9-fan-out check inside the multi-floor cascade, asserting that across all per-floor C9 results, exactly one room has `is_master=True AND category=BEDROOM`."

Spec #3 v0.3 LOCKED then **hardened** this: MFWZP-5 and MFWZP-6 enforce the assertion at `MultiFloorWetZonePlannedCandidate.__post_init__` — the bad state is structurally unreachable.

**Where v1.1 ends up**: this amendment does NOT add a redundant assertion. Spec #3's construction-time guard fires before any cache/scoring/persistence path, satisfying the fast-fail lifecycle Spec #2 v0.11 § 3.10 required. The pipeline-level orchestrator behaviour is: if the wrapper constructor raises (because of orchestration drift), wrap the failure as a `MutationApplicationResult(valid=False, invalidity_reason="cross_floor_invariant_violated")` and continue to the next operator attempt. This is the failure mode listed in § 3.4 step 7.

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

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Reuse existing `_is_multi_floor()` duck-type helper** | ✅ | Reject: rewrite to isinstance against MultiFloorDwellingBrief. Spec #1's `is_multi_floor: bool = True` property was deliberately designed for this — using the duck-type preserves the protocol-style boundary documented in Spec #1 v0.5 § 4 and B-MFDB-G. |
| **Tier A / Tier B M6/M7a/M7b applied to master floor ONLY in v1.1** | ✅ | Reject: apply to all floors. N× search-space inflation without proportional value in v1; adjacency-aware multi-floor scoring is post-v1. Filed as B-C11A-1. Reject also: skip Tier A entirely on multi-floor briefs. That would forfeit M0-M5/M9 mutations on multi-floor dwellings — too restrictive. Master-floor-only is the middle path. |
| **M8 target-floor selection deterministic (first eligible in tuple order)** | ✅ | Reject: random or scoring-driven selection. Determinism is critical for cache reproducibility and lineage classification. Non-deterministic / exploration-driven selection filed as B-C11A-2. |
| **M8 affects exactly TWO floors (old master + new master), reuse the rest** | ✅ | Reject: re-run C9→C10 on every floor on every M8 invocation. Unnecessary work; per-floor briefs only differ on the two affected floors. The C11a cache will naturally hit on un-affected floors' cached results, but explicit reuse via `with_floor_replaced`-style logic is cheaper. |
| **Multi-floor canonical signature = per-floor signatures + master label, joined + hashed** | ✅ | Reject: include per-floor briefs in signature. The per-floor wrappers ALREADY incorporate brief identity (via their existing single-floor signature derivation); duplicating would inflate hash collisions. Reject also: skip the master label in the signature. M8 mutations produce structurally identical per-floor candidates (the same per-floor WZPCs, just with different has_master_bedroom flags on the underlying briefs); the master label is the distinguishing structural feature. |
| **`C11A_CACHE_KEY_VERSION` bump v1.1.0 → v1.3.0 (skip v1.2.0)** | ✅ | Reject: two-step bump (v1.1.0 → v1.2.0 at Spec #3 build, then v1.2.0 → v1.3.0 at Spec #4 build). Specs #3 and #4 ship in the same B-NEW-T3 build session; a two-step bump just produces a transient version that never sees production. Single-step bump is cleaner. |
| **Multi-floor family ID = sorted concatenation of per-floor families, prefixed "multi_floor:"** | ✅ | Reject: derive from wrapper structure directly (without aggregating per-floor families). The whole point of family IDs is to group structurally-equivalent candidates for slot allocation; ignoring per-floor families would force every multi-floor candidate into its own family bucket, defeating slot pooling. Reject also: unsorted concatenation. Order-dependence would create false-distinct families for topologically-equivalent wrappers with different floor tuple ordering (Spec #3 § 3.5 acknowledges this isn't canonicalized). |
| **Spec #2 v0.11 § 3.10 trust boundary owned by Spec #3 construction guard + pipeline failure-mode handler, NOT a redundant v1.1-level assertion** | ✅ | Reject: add a redundant assertion in `mutate_topologies` post-C9 fan-out. Redundant assertions on already-unreachable states are noise; Spec #3 MFWZP-5/6 already make the bad state structurally impossible. The pipeline boundary's job is to handle the `ValueError` that Spec #3 raises (as `cross_floor_invariant_violated`), not to re-prove the invariant. |

---

## § 5 — Test plan

### § 5.1 — New test files / additions

**8 new tests** in a new file `buildemup/tests/test_c11a/test_subsession7_multi_floor.py`:

1. `test_orchestrator_accepts_multi_floor_brief`: `mutate_topologies` with a `MultiFloorDwellingBrief` doesn't error out.
2. `test_orchestrator_dispatches_per_floor_for_tier_a`: a single Tier A operator (e.g., M2) applied to a 2-floor candidate produces a wrapper where only the master floor's per-floor candidate changed.
3. `test_orchestrator_dispatches_per_floor_for_tier_b_m6_m7`: same shape for M6, M7a, M7b.
4. `test_m8_real_execution_produces_wrapper_with_master_swapped`: M8 applied to a 2-floor candidate (master on ground) produces a new wrapper with master on first.
5. `test_m8_target_floor_selection_is_deterministic_first_eligible`: M8 applied twice to the same source produces the same target; M8 on a 3-floor dwelling picks the first non-master floor with bedroom_count >= 1.
6. `test_m8_no_viable_target_returns_invalid`: M8 on a 2-floor dwelling where the non-master floor has bedroom_count=0 returns `valid=False, invalidity_reason="no_viable_master_target"`.
7. `test_m8_cascade_failure_returns_invalid_with_reason`: simulate C9/C10 failure on the new master floor; M8 returns `valid=False, invalidity_reason="c9_c10_cascade_failed"`.
8. `test_cross_floor_invariant_violation_is_caught_as_pipeline_failure`: force a scenario where the assembled wrapper would fail MFWZP-5 (e.g., by mocking C9 to produce zero masters on both affected floors); M8 returns `valid=False, invalidity_reason="cross_floor_invariant_violated"`.

**5 new tests** in `buildemup/tests/test_c11a/test_subsession5_candidate_context.py` (existing file):

9. `test_is_real_multi_floor_candidate_detects_wrapper_type`.
10. `test_derive_canonical_signature_multi_floor_dispatch`.
11. `test_derive_canonical_signature_multi_floor_includes_master_label`.
12. `test_derive_canonical_signature_multi_floor_recursive_per_floor`: changing one floor's underlying topology changes the wrapper's signature.
13. `test_c11a_cache_key_version_is_v1_3_0`: bumped from v1.1.0 (Spec #2 baseline).

**3 new tests** in `buildemup/tests/test_c11a/test_subsession4_family_slot_allocator.py` (existing file):

14. `test_family_id_multi_floor_aggregation`: wrapper's family ID is `"multi_floor:F1,F2"` where F1, F2 are sorted per-floor families.
15. `test_family_id_multi_floor_deterministic_under_floor_reorder`: even if the tuple order differs, the family ID is the same (because of the sort).
16. `test_family_id_single_floor_unchanged`: existing single-floor family ID derivation is unaffected.

**2 new tests** for the lineage classifier extension:

17. `test_lineage_classifier_per_floor_operator_tracks_floor_label`.
18. `test_lineage_classifier_m8_dwelling_level_no_per_floor_family_change`.

**Total**: **18 new tests**.

### § 5.2 — Existing test regression

Per § 3.10 backwards-compat guarantee: every existing C11a test must pass unchanged modulo the cache-key-version constant tests, which adjust to v1.3.0 directly.

Project total after Spec #2 + #3 + #4 build: **2769 + 18 = 2787 passed / 2 skipped / 0 regressions**.

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

- **Tier A / Tier B M6 / M7a / M7b applied to non-master floors**: v1.1 restricts to master floor only; B-C11A-1 covers expansion.
- **Non-deterministic M8 target floor selection** (random, scoring-driven, exploration): v1.1 picks first eligible; B-C11A-2.
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
| **B-C11A-1** (NEW) | Tier A / Tier B M6/M7a/M7b multi-floor expansion to non-master floors. v1.1 applies operators only to the master floor; non-master floors get no Tier A/B mutation in multi-floor mode. Expansion adds operator applications per non-master floor with appropriate slot allocation | When adjacency-aware multi-floor scoring lands (likely C11b NSGA-II amendment) OR when stress fuzz / search-space breadth concerns require multi-floor exploration | Open (post-v1) |
| **B-C11A-2** (NEW) | Non-deterministic / exploration-driven M8 target-floor selection. v1.1 picks first eligible deterministically; future search may benefit from exploring all candidate targets (one M8 application per non-master floor) or stochastic selection | When dwelling search-space depth becomes a real bottleneck OR when C11b explorer wants multi-target M8 expansion | Open (post-v1) |
| **B-C11A-3** (NEW) | M8 multi-step / N-floor rearrangement (general permutation of master designation across ≥3 floors via multi-step M8 application). v1.1's M8 is a single swap | When ≥3-floor luxury / commercial paths surface requiring multi-floor master complexity | Open (post-v1) |
| **B-C11A-4** (NEW) | Multi-floor cache hit/miss telemetry. Per-floor cache hits for un-affected floors during M8 should be observable; currently the cache observability is implicit in the single-floor cache hit count | When cache-tuning becomes a real perf concern | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK (and assuming all four specs are LOCKED — this amendment is the last):

**Files modified**:

- `buildemup/domain/floor_brief.py`: add `has_master_bedroom: bool = True` (per Spec #2). ~3 lines + docstring.
- `buildemup/components/c09/room_sizer.py`: 2 line-edits at lines 498 and 548 (per Spec #2).
- `buildemup/components/c11a/cache.py`: bump `C11A_CACHE_KEY_VERSION` to `"v1.3.0"`.
- `buildemup/components/c11a/source_signature.py`: add multi-floor dispatch in `derive_canonical_signature`; add `_derive_multi_floor_canonical_signature` helper.
- `buildemup/components/c11a/candidate_context.py`: add `is_real_multi_floor_candidate`.
- `buildemup/components/c11a/orchestrator.py`: add per-floor expansion logic in `mutate_topologies`; add Tier A / B per-floor dispatch helpers.
- `buildemup/components/c11a/operators/m8_vert_rearr.py`: replace stub with real `_build_m8_mutation`.
- `buildemup/components/c11a/family_slot_allocator.py`: add multi-floor family aggregation.
- `buildemup/components/c11a/lineage.py`: add multi-floor lineage extension.

**Files created**:

- `buildemup/domain/multi_floor_brief.py` (per Spec #1, ~210 lines).
- `buildemup/domain/multi_floor_candidate.py` (per Spec #3, ~250 lines).
- `buildemup/components/c11a/m8_floor_swap_real.py` (this amendment, ~150 lines).
- `buildemup/tests/test_domain_multi_floor_brief.py` (per Spec #1, ~45 tests).
- `buildemup/tests/test_domain_multi_floor_candidate.py` (per Spec #3, ~35 tests).
- `buildemup/tests/test_c11a/test_subsession7_multi_floor.py` (this amendment, ~8 tests).
- `buildemup/tests/_multi_floor_fixtures.py` (helper, no tests).

**Tests added**: Spec #2 (~9) + Spec #3 (~35) + this amendment (~18) = **~62 new tests**.

**Test count after build**: 2760 baseline + 62 = **2822 passed**, modulo any test-count drift.

**Estimated build effort**: ~3-5 sessions of focused work. Largest item is C11a orchestrator multi-floor expansion + M8 real wiring + signature/cache/lineage extensions. Spec #1 + #3 file creation is mechanical (specs are precise). Spec #2 is trivial.

---

## § 9 — Status

- **v1.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v1.2 PROPOSED.
- After LOCK: **B-NEW-T3 build can begin** (all four specs LOCKED).

---

## § 10 — Rule 9 backlog enumeration

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| Spec #1 | `MultiFloorDwellingBrief` v0.5 LOCKED | DONE | DONE | DONE | DONE |
| Spec #2 | C9 Amendment v0.11 LOCKED | DONE | DONE | DONE | DONE |
| Spec #3 | `MultiFloorWetZonePlannedCandidate` v0.3 LOCKED | DONE | DONE | DONE | DONE |
| **Spec #4** | This amendment | Specs #1+2+3 LOCKED | LOCK pending | IN-FLIGHT | L |
| B-NEW-T3 | M8 multi-floor real upstream wiring | All 4 specs LOCKED | After this LOCKs | GATED — build session begins | L |
| B-C11A-1 | Tier A/B multi-floor expansion to non-master floors | This amendment | Adjacency scoring OR search-space concerns | OUT-OF-SCOPE this amendment | M (post-v1) |
| B-C11A-2 | Non-deterministic M8 target selection | This amendment | Search depth bottleneck | OUT-OF-SCOPE | S (post-v1) |
| B-C11A-3 | M8 multi-step / N-floor rearrangement | This amendment | ≥3-floor luxury / commercial paths | OUT-OF-SCOPE | M (post-v1) |
| B-C11A-4 | Multi-floor cache telemetry | This amendment | Cache-tuning perf concerns | OUT-OF-SCOPE | S (post-v1) |

**Summary**: largest of the four B-NEW-T3 specs. Threads multi-floor through every C11a pipeline stage. Four new backlog items (B-C11A-1 through 4). After LOCK, the B-NEW-T3 build session begins — the largest implementation work item in S41+.

---

**End of C11a Amendment v1.1 PROPOSED.**
