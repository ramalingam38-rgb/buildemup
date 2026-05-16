# NEXT_CLAUDE_HANDOFF.md — S40-continuation → S41 (B-NEW-T3 BUILD SESSION)

**Authored**: end of S40-continuation, post-LOCK of all four B-NEW-T3 specs.
**To**: the next Claude beginning S41.
**Ramalingam's directive at handoff**: "Lock this and give me the handoff with everything that happened till now and **make sure the next Claude starts coding immediately without any further delay**."

This handoff is engineered for that directive. **Read this entire document before writing any code, then start coding.** The intent is zero discovery time at S41 start.

---

## § 1 — One-paragraph context

You are continuing BuildemUp, a decision-support engine for Indian families building their own homes. The project is at the inflection point where four critical specs have just been LOCKED across the S40-continuation session: `MultiFloorDwellingBrief v0.5`, `C9 Amendment v0.11`, `MultiFloorWetZonePlannedCandidate v0.3`, and `C11A Amendment v1.6`. Together these specs unlock M8 (the last remaining Tier B operator stub) and thread multi-floor support through every C11a pipeline stage. **Your job in S41 is to implement them.** The spec sequence is called B-NEW-T3.

---

## § 2 — Immediate-start checklist (FIRST 5 MINUTES OF S41)

Do these in order. Do not skip. Do not deliberate.

1. **Read `02_specs_chronological/85_MultiFloorDwellingBrief_SPEC_v0_5_LOCKED.md`** — Spec #1, ~370 lines. The input-side multi-floor brief.
2. **Read `02_specs_chronological/90_C9_AMENDMENT_v0_11_LOCKED.md`** — Spec #2, ~400 lines. Adds `has_master_bedroom: bool = True` to FloorRoomBrief; C9 honors it.
3. **Read `02_specs_chronological/94_MultiFloorWetZonePlannedCandidate_SPEC_v0_3_LOCKED.md`** — Spec #3, ~810 lines. Output-side wrapper with cross-floor invariants.
4. **Read `02_specs_chronological/101_C11A_AMENDMENT_v1_6_LOCKED.md`** — Spec #4, ~1200 lines. The pipeline-rework amendment. **This is the largest spec; budget the most reading time here.**
5. **Inventory existing code state** (Rule 10.6.1 pre-touch inventory):
   ```bash
   cd /home/claude/work/buildemup
   ls domain/floor_brief.py components/c11a/operators/m8_vert_rearr.py
   wc -l components/c11a/orchestrator.py
   grep -n "_is_multi_floor\|swap_master_floor" components/c11a/orchestrator.py components/c11a/operators/m8_vert_rearr.py
   pytest -q 2>&1 | tail -5  # baseline: 2760 passed / 2 skipped
   ```
6. **Start with Sub-1 of the build plan in § 5 below.** No further planning. Just begin.

If anything in steps 1-5 produces a surprise (an unexpected baseline test count, missing file, different API shape than the spec describes), STOP and investigate. The spec text is authoritative; if a reality-vs-spec drift exists, surface it and patch the spec via a v1.7 PROPOSED — do NOT silently work around it.

---

## § 3 — Project state snapshot (the absolute essentials)

- **Solo founder**: Ramalingam, Tamil Nadu, India.
- **Numbering**: Track 3 canonical (17 components). Specs locked: 10/17 components shipped at v1.0 baseline + the four B-NEW-T3 specs at S40-continuation.
- **Baseline tests** (pre-B-NEW-T3 build): **2760 passed / 2 skipped / 0 failed.** Do not regress this number; you will add ~67-72 new tests during B-NEW-T3 build.
- **Working tree**: `/home/claude/work/buildemup/`
- **GitHub**: `ramalingam38-rgb/buildease`
- **Production**: `buildease-production.up.railway.app`

**5 patterns to avoid** (Ramalingam's standing constants):
- **A** fix-as-bandage (most relevant to flag if you find yourself patching v1.x algorithms on top of v1.x without replacing them)
- **B** building-without-wiring
- **C** scores-without-truth
- **D** rules-on-rules
- **E** scope-creep-mid-build (**MOST EXPENSIVE — the build session is scoped to B-NEW-T3 only; do NOT pick up tangential backlog items**)

---

## § 4 — What the four LOCKED specs collectively require (the build target)

Three new domain files, one new C11a M8 file, ~9 modified files, ~67-72 new tests. Final state:

### Files to CREATE (new files)

| File | From spec | Approx LOC | Approx tests |
|---|---|---|---|
| `buildemup/domain/multi_floor_brief.py` | Spec #1 | ~210 | ~45 |
| `buildemup/domain/multi_floor_candidate.py` | Spec #3 | ~250 | ~35 |
| `buildemup/components/c11a/m8_floor_swap_real.py` | Spec #4 | ~150 | (part of below) |
| `buildemup/tests/test_domain_multi_floor_brief.py` | Spec #1 | — | ~45 |
| `buildemup/tests/test_domain_multi_floor_candidate.py` | Spec #3 | — | ~35 |
| `buildemup/tests/test_c11a/test_subsession7_multi_floor.py` | Spec #4 | — | ~18 |
| `buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py` | Spec #4 | — | ~6 (incl 50-step stateful chain) |
| `buildemup/tests/test_integration/test_b_new_t3_pipeline.py` | Spec #4 | — | ~4 |
| `buildemup/tests/_multi_floor_fixtures.py` | Spec #4 | — | 0 (helpers) |

### Files to MODIFY

| File | Change | From spec |
|---|---|---|
| `buildemup/domain/floor_brief.py` | Add `has_master_bedroom: bool = True` field | Spec #2 |
| `buildemup/components/c09/room_sizer.py` | Lines 498 + 548: `is_master = (i == 0) and brief.has_master_bedroom` | Spec #2 |
| `buildemup/components/c11a/cache.py` | Bump `C11A_CACHE_KEY_VERSION` "v1.0.0" → "v1.3.0" | Spec #4 |
| `buildemup/components/c11a/source_signature.py` | Add multi-floor dispatch + `_derive_multi_floor_canonical_signature` with `multi_floor_sig_schema=v1` prefix | Spec #4 |
| `buildemup/components/c11a/candidate_context.py` | Add `is_real_multi_floor_candidate` using **marker-attribute lookup** `getattr(obj, "__multi_floor_candidate__", False) is True` | Spec #4 |
| `buildemup/components/c11a/orchestrator.py` | Add per-floor expansion in `mutate_topologies`; bipartite `_generate_per_floor_attempts`; `_validate_multi_floor_protocol()` + `_validate_multi_floor_alignment()` pre-flights; `affected_floor_set(...) -> frozenset[FloorImpact]` abstraction with split kwargs (`direct_floor_label` / `new_master_floor_label`) | Spec #4 |
| `buildemup/components/c11a/operators/m8_vert_rearr.py` | Replace stub with real impl using **cyclic deterministic target selection** `sorted_targets[(generation + operator_index) % N]` | Spec #4 |
| `buildemup/components/c11a/family_slot_allocator.py` | Multi-floor family aggregation with label-preserving pairs `multi_floor:ground=A\|first=B` | Spec #4 |
| `buildemup/components/c11a/lineage.py` | Multi-floor lineage with `floor_label_affected: str \| None` field | Spec #4 |
| `buildemup/components/c11a/errors.py` | Add `OrchestrationError` + `OrchestrationProtocolError` + `OrchestrationAlignmentError` | Spec #4 |
| `buildemup/components/c11a/schema.py` | Add `FloorImpact` frozen dataclass; extend `MutationApplicationResult.invalidity_reason` taxonomy with `orchestration_state_drift:mfwzp1..6`, `c9_generation_failed`, `c10_validation_failed`, `no_viable_master_target` | Spec #4 |

### One Spec #3 build-coordination addition

Add `__multi_floor_candidate__: bool = True` as a **class attribute** (NOT a dataclass field) on `MultiFloorWetZonePlannedCandidate`. This is implementation-level — does NOT change Spec #3 v0.3 LOCKED's runtime contract (no dataclass equality / hash / repr impact). C11a's `is_real_multi_floor_candidate` looks for this marker.

---

## § 5 — Recommended build subdivision (sub-sessions)

The full build is ~3-5 sessions of focused work. Recommended subdivision so each sub-session lands a coherent, test-green chunk:

### **Sub-1 (S41): Domain types + Spec #2 + smoke tests** (~1 session)

**Goal**: Specs #1 + #2 + Spec #3 structural shell shipped; all 89 new domain tests passing; existing 2760 tests still green.

1. Create `buildemup/domain/multi_floor_brief.py` per Spec #1 § 3 + § 4 (~210 LOC). Implement: `FloorRoomBrief` extension reference, `MultiFloorDwellingBrief` dataclass with `floors: tuple[FloorRoomBrief, ...]`, `master_bedroom_floor_label: str`, `master_bedroom_selector: Literal["first_bedroom"] = "first_bedroom"`. All 6 invariants MFDB-1 through MFDB-6 in `__post_init__`. Helpers: `is_multi_floor` (property → True), `get_floor`, `floor_labels`, `floor_has_master`, `iter_floors_with_master_flag`, `with_master_on`. Module function `_normalize_label`. Normalization at construction via `object.__setattr__`.
2. Modify `buildemup/domain/floor_brief.py`: add `has_master_bedroom: bool = True` field per Spec #2 § 3.
3. Modify `buildemup/components/c09/room_sizer.py` lines 498 + 548 per Spec #2 § 3.7 (the `is_master = (i == 0) and brief.has_master_bedroom` line).
4. Create `buildemup/domain/multi_floor_candidate.py` per Spec #3 § 3 + § 4 (~250 LOC). All 6 invariants MFWZP-1 through MFWZP-6 in `__post_init__`. `_derive_floor_labels` walks `f.room_sized_candidate.provenance.floor_label` (this path is empirically-verified — see Spec #3's v0.2 schema-drift fix). Helpers: `with_floor_replaced(label, new_wzpc)` and `with_master_on(new_label, new_per_floor_candidates)`. **Add `__multi_floor_candidate__: bool = True` class attribute** (NOT a dataclass field).
5. Create the three test files for domains: `test_domain_multi_floor_brief.py` (~45 tests), `test_domain_multi_floor_candidate.py` (~35 tests), and the Spec #2-related 9 new C9 tests in the existing C9 test file.
6. Run full test suite. Target: **2760 + 89 = 2849 passed / 2 skipped / 0 failed.**

### **Sub-2 (S42): C11a signature + cache + family aggregation + lineage + errors** (~1 session)

**Goal**: All non-orchestrator C11a multi-floor support shipped; orchestrator changes deferred to Sub-3.

1. Modify `buildemup/components/c11a/errors.py`: `OrchestrationError` base + `OrchestrationProtocolError` + `OrchestrationAlignmentError`.
2. Modify `buildemup/components/c11a/schema.py`: `FloorImpact` frozen dataclass + invalidity_reason taxonomy extension.
3. Modify `buildemup/components/c11a/candidate_context.py`: `is_real_multi_floor_candidate(source: Any) -> bool` using marker-attribute lookup.
4. Modify `buildemup/components/c11a/cache.py`: bump `C11A_CACHE_KEY_VERSION` to `"v1.3.0"`. (Single-step bump from `"v1.0.0"`, covers Specs #3 + #4.)
5. Modify `buildemup/components/c11a/source_signature.py`: multi-floor dispatch + `_derive_multi_floor_canonical_signature` per Spec #4 § 3.5. Include `multi_floor_sig_schema=v1` prefix.
6. Modify `buildemup/components/c11a/family_slot_allocator.py`: `multi_floor_family_id` with label-preserving aggregation `multi_floor:ground=A|first=B`. Sort by label, NOT by family.
7. Modify `buildemup/components/c11a/lineage.py`: add `floor_label_affected: str | None` field.
8. Add the 5 + 3 + 2 = 10 unit tests in existing C11a test files (signature, candidate_context, family_slot_allocator, lineage).
9. Run full test suite. Target: 2849 + 10 = **~2859 passed.**

### **Sub-3 (S43): C11a orchestrator + M8 real impl + integration + property tests** (~1-2 sessions, largest)

**Goal**: B-NEW-T3 build complete.

1. Plumbing: thread `generation: int` through the orchestrator's mutation-attempt loop if not already in `config`. Required by Spec #4 § 3.4 cyclic M8 algorithm.
2. Modify `buildemup/components/c11a/orchestrator.py`:
   - Add `_validate_multi_floor_protocol(obj)` pre-flight with cardinality check.
   - Add `_validate_multi_floor_alignment(brief, source)` pre-flight.
   - Add `_generate_per_floor_attempts(operators_in_family, floor_labels)` — bipartite round-major interleaving per Spec #4 § 3.2 (round 0: M0:F0, M2:F1, M3:F2, M4:F3; round 1: M0:F1, M2:F2, ...).
   - Add per-floor expansion logic in `mutate_topologies` when input is `MultiFloorDwellingBrief`.
   - Add `affected_floor_set(operator, source, *, direct_floor_label=None, new_master_floor_label=None) -> frozenset[FloorImpact]` per Spec #4 § 3.11. **Split kwargs (not the v1.4 single `target_floor_label`) — operator class determines which kwarg is required.**
3. Replace `buildemup/components/c11a/operators/m8_vert_rearr.py` stub: real `_build_m8_mutation` using cyclic deterministic target selection `sorted_targets[(generation + operator_index) % N]`. NO SHA256 (the v1.2 hash-modulo was replaced by v1.3+ cyclic — simpler).
4. (Optional) Extract the M8 real logic into `buildemup/components/c11a/m8_floor_swap_real.py` (~150 LOC) for clarity.
5. Create `buildemup/tests/_multi_floor_fixtures.py` with helpers: `make_two_floor_brief_with_master_on(label)`, `make_three_floor_brief_with_master_on(label)`, `run_multi_floor_c9_c10_pipeline(brief, ...)`.
6. Create `buildemup/tests/test_c11a/test_subsession7_multi_floor.py` (~18 example-based tests per Spec #4 § 5.1).
7. Create `buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py` (~6 property tests including the 50-step stateful chain per Spec #4 § 5.1.1). Use Hypothesis if available; parameterized-exhaustive otherwise. `max_examples=100`.
8. Create `buildemup/tests/test_integration/test_b_new_t3_pipeline.py` (~4 cross-spec integration tests per Spec #4 § 5.1, tests #25-28).
9. Run full test suite. Target: ~2859 + ~28 = **~2832 passed** (the final B-NEW-T3 build state; ~2832 instead of higher count due to some duplication between subsession counts).

Once Sub-3 is green, **B-NEW-T3 build is complete**. The 11th Tier B operator (M8 multi-floor real upstream wiring) is shipped.

---

## § 6 — The critical algorithms (cheat sheet so you don't have to re-read 1200 lines)

### **Bipartite operator+floor interleaving** (Spec #4 § 3.2, the v1.4 LOCK gate)

```python
def _generate_per_floor_attempts(
    operators_in_family: tuple[MutationOperator, ...],
    floor_labels: tuple[str, ...],
) -> tuple[tuple[MutationOperator, str], ...]:
    attempts: list[tuple[MutationOperator, str]] = []
    n_floors = len(floor_labels)
    n_operators = len(operators_in_family)
    for round_idx in range(n_floors):
        for operator_index, operator in enumerate(operators_in_family):
            floor_index = (operator_index + round_idx) % n_floors
            attempts.append((operator, floor_labels[floor_index]))
    return tuple(attempts)
```

Round-major outer loop. **Fairness property**: bounded imbalance ≤ 1 on both operator and floor axes under slot truncation, starvation-free.

### **Cyclic M8 target selection** (Spec #4 § 3.4, the v1.3 fix)

```python
def _pick_m8_target(
    eligible_targets: tuple[str, ...],
    generation: int,
    operator_index: int,
) -> str:
    sorted_targets = sorted(eligible_targets)
    index = (generation + operator_index) % len(sorted_targets)
    return sorted_targets[index]
```

**Mathematical guarantee**: across N consecutive distinct generations (where `N = len(eligible_targets) = num_floors - 1` when all non-master floors have bedrooms; fewer otherwise), all N eligible targets are visited exactly once.

### **Multi-floor canonical signature** (Spec #4 § 3.5)

```python
parts = ["multi_floor_sig_schema=v1", "multi_floor=true",
         f"master_floor={source.master_bedroom_floor_label}"]
for floor_label, per_floor_wzpc in zip(source.floor_labels, source.floors):
    parts.append(f"floor[{floor_label}]={derive_canonical_signature(per_floor_wzpc)}")
return sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
```

### **Family ID aggregation** (Spec #4 § 3.7)

```python
pairs = sorted(
    (label, get_family_id(f))
    for label, f in zip(wrapper.floor_labels, wrapper.floors)
)
payload = "|".join(f"{label}={family_id}" for label, family_id in pairs)
return f"multi_floor:{payload}"
```

Sort by LABEL (not by family). Label-preserving.

### **`affected_floor_set` split-kwarg API** (Spec #4 § 3.11)

```python
def affected_floor_set(
    operator, source, *,
    direct_floor_label: str | None = None,
    new_master_floor_label: str | None = None,
) -> frozenset[FloorImpact]:
    # Per-floor operator: direct_floor_label required; new_master_floor_label MUST be None.
    # M8: new_master_floor_label required; direct_floor_label MUST be None.
    # Wrong kwarg for operator class → OrchestrationProtocolError.
```

### **M8 failure taxonomy** (Spec #4 § 3.4)

| `invalidity_reason` | When |
|---|---|
| `no_viable_master_target` | No eligible target floor |
| `c9_generation_failed` | C9 raised on new per-floor brief |
| `c10_validation_failed` | C9 succeeded; C10 rejected |
| `orchestration_state_drift:mfwzp1..6` | Wrapper construction failed at MFWZP-N |

### **MFDB invariants** (Spec #1 § 3.2)

1. ≥2 floors. 2. Unique normalized floor labels. 3. master_bedroom_floor_label ∈ floor_labels. 4. Master floor has bedroom_count ≥ 1. 5. master_bedroom_selector ∈ allowed values (just `"first_bedroom"` at v1). 6. All floors have well-formed FloorRoomBrief (delegated to FloorRoomBrief's own validation).

### **MFWZP invariants** (Spec #3 § 3.2)

1. ≥2 floors. 2. Per-floor labels unique + match derived. 3. Declared master ∈ derived labels. 4. All instances are WZPCs. 5. **Exactly one master bedroom emitted globally** (the C9-cross-floor hardening). 6. Declared master floor matches emitted master.

---

## § 7 — What NOT to do (scope discipline)

- **DO NOT promote backlog items.** B-C11A-1 through 18 are all post-v1. Even if they look easy. Even if the reviewer flagged them. Spec LOCKs are canonical; scope creep mid-build is Pattern E (most expensive).
- **DO NOT add the operator-fairness-bias-breaker (B-C11A-13) into v1 build.** Reviewer pushed hard in v1.5/v1.6 critique walks. Already filed. The cyclic algorithm is correct for v1 scope.
- **DO NOT extract strategy patterns (B-C11A-11).** Tempting at build time. Filed for when C11b lands.
- **DO NOT add full lineage ancestry (B-C11A-8) or generation provenance (B-C11A-14).** v1 ships `floor_label_affected: str | None` only.
- **DO NOT introduce canonical floor identity (B-C11A-17) or memoized signatures (B-C11A-15).** Filed for trigger conditions that haven't fired.
- **DO NOT modify Spec #3 LOCKED beyond the `__multi_floor_candidate__: bool = True` class attribute.** That's an implementation-level addition that doesn't touch the spec's runtime contract.
- **DO NOT touch the single-floor `is_real_wet_zone_candidate` name-based detection.** B-C11A-6 filed for that migration. Leave it.

If you find a real bug in a LOCKED spec while implementing (e.g., schema-drift like the one caught in Spec #3 v0.1 → v0.2), STOP coding. Produce a v(N+1) PROPOSED spec amendment, get Ramalingam adjudication, then resume. Don't silently work around.

---

## § 8 — Inventory of artifacts in this handoff

- **`02_specs_chronological/`** — 24 files (78-101). Full chronological history of every PROPOSED + LOCKED revision across all 4 specs + their critique walks. Files 80-85: Spec #1 evolution. Files 86-90: Spec #2 evolution. Files 91-94: Spec #3 evolution. Files 95-101: Spec #4 evolution. **For build, focus on the four LOCKED files: 85, 90, 94, 101.**
- **`04_backlog/`** — 2 files. `v0_2_backlog_S40_additions.md` (pre-S40-continuation) and `v0_2_backlog_S40_continuation_additions.md` (post-LOCK signals from this session, including the 18 B-C11A-* items).
- **`05_integrity_check/`** — the three-check artifacts (gap / audit / integrity) from this S40-continuation handoff. Read these to understand what was promised vs delivered in this session.
- **`07_design_documents/`** — `S40_continuation_session_summary.md` — the narrative of what happened in S40-continuation.
- **`00_START_HERE/`** — `NEXT_CLAUDE_HANDOFF.md` (this file).

---

## § 9 — Ramalingam's working style (the stuff that's not in any spec)

Direct and challenge-oriented. Asks "do you agree?" and expects reasoned responses, not compliance. Runs external critiques against locked specs before build starts and treats critique rounds as quality control. Prefers honest scope estimates over optimistic ones. Corrects your approach when needed. Brief one-line directives are common ("lock it", "yes to both", "do the patches and lock it").

**Standing obligations every session** (including discussion-only):
1. **Spec-first discipline**: never code before a LOCKED spec. Always draft → critique → lock → then code.
2. **Honest context budget** declared at session start.
3. **Master doc + `NEXT_CLAUDE_HANDOFF.md` updated at every session end.** This document is self-perpetuating — every Claude produces a fresh version for the next.

---

## § 10 — One last thing

After Sub-3 completes and all ~2832 tests are green, produce S41 → S42 handoff (or S41 → S{whatever} depending on how the sub-sessions split). The B-NEW-T3 spec sequence was the largest spec-design effort in the project so far (6 rounds on the C11a amendment alone). The build is straightforward by comparison — but only if you stay on-scope. Spec text is authoritative; you have it; go.

**Start with Sub-1 step 1: read Spec #1 LOCKED. Then step 2. Then step 3. Then step 4. Then step 5 inventory. Then code.**

— S40-continuation Claude
