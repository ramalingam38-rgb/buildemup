# C11A SPEC AMENDMENT v1.2 PROPOSED — multi-floor pipeline rework (B-NEW-T3 enabler #4 of 4)

**Component**: 11a (Topology Mutation Orchestration — SHIPPED at v1.0 LOCKED across multiple sessions; 10/17 Track 3 components, structurally complete with 3/4 Tier B operators wired before this amendment).
**Spec status**: **v1.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-v1.1 critique walk.
**Driver**: Spec #4 of 4, the largest. Completes the B-NEW-T3 spec sequence.

**v1.2 vs v1.1**: substantive critique-walk patches. **Two real behavioral changes** (Tier A/B operators now dispatch to ALL floors not just master; M8 target selection now hash-deterministic across all eligible floors instead of "first eligible"). Plus pre-flight validators (protocol + brief/source alignment), signature schema-version prefix, label-preserving family aggregation, refined M8 failure taxonomy, lineage `floor_label_affected` field, new property-test section, 5 new backlog items.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v1.2 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v1_2_LOCKED.md` (if approved as-is),
- `..._v1_3_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
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

**Per-floor operator dispatch — ALL FLOORS, slot-allocator-limited** (item 2 from v1.1 critique walk — substantive behavioral change vs v1.1):

For each `(operator, floor_label)` pair across the dwelling's floors, the orchestrator generates one mutation-attempt entry. The existing slot allocator at `family_slot_allocator.py` then naturally bounds total attempts per operator family per generation by its `slot_count`. The N×-floor inflation that "master-only" was avoiding is bounded by slot allocation, not by floor count.

**Attempt-generation order** (deterministic for cache reproducibility): for a given operator within a family, attempts are generated in `(operator_index, floor_index)` lexicographic order — operator M0 floor[0], M0 floor[1], ..., M0 floor[N-1], M2 floor[0], M2 floor[1], ..., etc. The slot allocator then takes the first `slot_count` of these. This means:
- Single-floor dwellings: existing behavior preserved (one floor → no inflation, slot allocator takes the operator attempts as before).
- Multi-floor dwellings: each operator can produce up to N attempts (one per floor), but the slot allocator caps total attempts at the same `slot_count` that single-floor briefs would use.

**Rationale for switching from master-only (v1.1) to all-floors (v1.2)**:
- Non-master floors can contain secondary-bath bottlenecks, circulation inefficiencies, wet-zone conflicts, and NBC violations that Tier A mutations are specifically designed to resolve.
- Restricting Tier A to master-only would freeze non-master-floor topology evolution permanently in multi-floor mode, creating search-space dead zones and artificial convergence bias toward master-floor-heavy layouts.
- C11b NSGA-II (downstream scoring component) would receive structurally under-explored populations.
- The slot allocator provides natural exploration-vs-exploitation tuning without needing master-floor restriction.

**Slot-budget tuning** filed as **B-C11A-5**: per-floor attempt weights (e.g., 70% master, 30% non-master) or generation-aware budgets when stress-fuzz / search-breadth telemetry shows the uniform `(operator_index, floor_index)` order produces undesirable bias. v1.2's uniform-order is the simplest baseline; weighted variants can be added without changing the contract.

### § 3.3 — Per-floor Tier B M6 / M7a / M7b execution

M6 (wet rotate), M7a (grid bay X scale), M7b (grid bay Y scale) are real single-floor operators (S39 + S40 wiring). In multi-floor mode:

Same dispatch shape as Tier A (per item 2 from v1.1 critique walk): applied to ALL floors, slot-allocator-limited. The Tier B regenerative cascade (C7→C8→C9→C10 for M7a/b; C10 re-run for M6) runs against the targeted floor's brief and produces a new per-floor `WetZonePlannedCandidate`; the wrapper is re-assembled via `with_floor_replaced`.

Each `(operator, floor_label)` pair produces one Tier B attempt; the slot allocator caps the total. Tier B per-attempt cost is significantly higher than Tier A (regenerative cascade), so slot allocator budgets for Tier B will need attention at build-session time — but this is the existing per-operator slot allocation working as designed, not a new mechanism.

**Tier B attempt-cost concern** filed as **B-C11A-5** alongside the Tier A slot-budget tuning concern — both are the same underlying "uniform per-floor attempt generation may need per-floor weighting" problem.

### § 3.4 — M8 (`m8_vert_rearr`) real implementation

M8 is the only Tier B operator that operates dwelling-wide. It swaps which floor hosts the master bedroom.

**Algorithm**:

1. Read `source` (a `MultiFloorWetZonePlannedCandidate`). Read `source.master_bedroom_floor_label` (the current master floor).
2. Compute candidate target floors: every floor in `source.floor_labels` EXCEPT the current master that has `bedroom_count >= 1` (per Spec #1 Inv MFDB-4 — the target floor must be able to host the master). Empty target set → M8 returns `MutationApplicationResult(valid=False, invalidity_reason="no_viable_master_target")`.
3. **Choose one target floor via deterministic hash** (item 3 from v1.1 critique walk — substantive behavioral change vs v1.1):

   ```python
   def _pick_m8_target(
       eligible_targets: tuple[str, ...],
       source_signature: str,
       generation: int,
       operator_index: int,
   ) -> str:
       """Deterministic pseudo-random selection across eligible targets.

       Uses a stable hash over (signature, generation, operator_index) to
       index into the eligible-target tuple. Determinism is preserved for
       cache reproducibility. Across generations and across structurally
       different candidates, the same eligible set will produce DIFFERENT
       targets — solving the v1.1 "first-eligible starvation" problem in
       3+ floor dwellings where only one alternative floor was ever
       explored.
       """
       seed = f"{source_signature}|gen={generation}|op={operator_index}"
       digest = hashlib.sha256(seed.encode("utf-8")).digest()
       index = int.from_bytes(digest[:8], "big") % len(eligible_targets)
       return eligible_targets[index]
   ```

   The `generation` and `operator_index` parameters thread through from the orchestrator's mutation-attempt loop. `operator_index` exists in `OPERATOR_METADATA`. `generation` may need a small plumbing addition if not currently in `config` — build-session detail. **Filed as build-session checklist item**, not a backlog item (it's required for the algorithm).
4. Construct the post-mutation `MultiFloorDwellingBrief` via Spec #1's `with_master_on(new_floor_label)`. This re-validates the target floor has bedroom_count ≥ 1.
5. For each floor whose `has_master_bedroom` flag flipped (the old master floor: True → False; the new master floor: False → True), re-run the C9→C10 cascade against the new per-floor brief. **Exactly two floors** are affected (in v1.2; see B-C11A-7 for future cross-floor cascades). The other floors' per-floor candidates are reused as-is.
6. Assemble the new `MultiFloorWetZonePlannedCandidate` via Spec #3's `with_master_on(new_floor_label, new_per_floor_candidates)`. Spec #3's `__post_init__` re-validates all 6 invariants (MFWZP-1 through 6), most importantly MFWZP-5 (exactly one master bedroom globally) and MFWZP-6 (declared master matches derived).
7. Return `MutationApplicationResult` with the new wrapper.

**Failure modes** (refined per item 12 from v1.1 critique walk — v1.1's `c9_c10_cascade_failed` was too coarse for diagnostics during large search runs):

| `invalidity_reason` | When it fires |
|---|---|
| `no_viable_master_target` | No eligible target floor (all non-master floors have `bedroom_count=0`). |
| `c9_generation_failed` | C9 raised on the new per-floor brief (e.g., NBC infeasibility on the new master floor — bedroom sizing impossible at min-NBC + bay constraints). Distinct from C10 because it indicates an upstream sizing problem, often actionable via different operator selection. |
| `c10_validation_failed` | C9 succeeded but C10 wet-zone planning rejected the cascade result (e.g., wet-zone band assignment infeasible after the C9-resized rooms). |
| `orchestration_state_drift` | Spec #3's `__post_init__` rejected the assembled wrapper (MFWZP-5 or MFWZP-6 fires at construction time). SHOULD NOT happen if steps 1-5 executed correctly; indicates an orchestration bug. Caught here as a fail-fast guard. Maps to what v1.1 called `cross_floor_invariant_violated`. |

`c9_c10_cascade_failed` (v1.1's coarse name) is replaced by the two split entries above. Pipeline observability + downstream telemetry get more actionable signal.

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

### § 3.8 — Lineage classifier extension

`lineage.py`'s classifier currently tracks (source-family → result-family) transitions per operator application. In multi-floor mode:

- Tier A / B M0-M7/M9 (per-floor operators): the family transition is at the per-floor level (the affected floor's family changes); the wrapper's aggregate family also changes (per § 3.7). Lineage records: `operator=M_X, floor_label_affected=L, per_floor_transition=(F1 → F2), wrapper_transition=(W1 → W2)`.
- M8 (dwelling-level operator): the family transition is at the dwelling level. `floor_label_affected=None` (M8 is dwelling-wide, not per-floor). Per-floor families are PRESERVED (the same per-floor brief contents, just with `has_master_bedroom` flipped — which changes the per-floor WZPC but typically not the per-floor family ID, since family ID derives from topology kind + zone bands + structural features, not master designation). The wrapper's transition is `(W1 → W2)` reflecting the master swap.

**Lineage `floor_label_affected: str | None` field** (item 10 from v1.1 critique walk, lightweight version): added to multi-floor lineage entries. Distinguishes single-floor operator effects (label = the affected floor) from dwelling-level effects (label = None). This is the minimum useful per-floor causality signal for downstream NSGA-II explainability and debugging. **Full ancestry-chain extension** (floor ancestry IDs, mutation provenance chains, master-transition events, per-floor generation counters) filed as **B-C11A-8** when explainability tooling needs the richer model.

`MutationLineageDepth` (existing enum) extends to multi-floor naturally — `SHALLOW_TRANSFORM` and `DEEP_TRANSFORM` apply per the existing single-floor semantics, just at the wrapper level.

### § 3.9 — Spec #2 v0.11 § 3.10 trust-boundary assertion — owned where?

Spec #2 v0.11 § 3.10 forward-pointed to this amendment: "Spec #4 (C11a Amendment v1.1) is expected to own this assertion — likely as a post-C9-fan-out check inside the multi-floor cascade, asserting that across all per-floor C9 results, exactly one room has `is_master=True AND category=BEDROOM`."

Spec #3 v0.3 LOCKED then **hardened** this: MFWZP-5 and MFWZP-6 enforce the assertion at `MultiFloorWetZonePlannedCandidate.__post_init__` — the bad state is structurally unreachable.

**Where v1.x ends up**: this amendment does NOT add a redundant assertion. Spec #3's construction-time guard fires before any cache/scoring/persistence path, satisfying the fast-fail lifecycle Spec #2 v0.11 § 3.10 required. The pipeline-level orchestrator behaviour is: if the wrapper constructor raises (because of orchestration drift), wrap the failure as a `MutationApplicationResult(valid=False, invalidity_reason="orchestration_state_drift")` and continue to the next operator attempt. This is the failure mode listed in § 3.4 step 7.

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
| **Reuse existing `_is_multi_floor()` duck-type helper, hardened with `_validate_multi_floor_protocol()` pre-flight** | ✅ | Reject: rewrite to isinstance against MultiFloorDwellingBrief. Spec #1's `is_multi_floor: bool = True` property was deliberately designed for this — using the duck-type preserves the protocol-style boundary documented in Spec #1 v0.5 § 4 and B-MFDB-G. **v1.2 update**: added the pre-flight validator to harden against accidental misrouting (item 1 from v1.1 critique walk). |
| **Tier A / Tier B M6/M7a/M7b applied to ALL FLOORS, slot-allocator-limited** | ✅ | Reject (REVERSED FROM v1.1): apply only to master floor. **v1.1's "master-only" was wrong** (item 2 from v1.1 critique walk) — non-master floors can have secondary-bath bottlenecks, circulation inefficiencies, wet-zone conflicts, and NBC violations that Tier A is designed to resolve. Master-only would freeze non-master-floor topology evolution permanently. The N×-floor inflation v1.1 was avoiding is bounded by the existing slot allocator (`slot_count`), so all-floors works without unbounded combinatorics. Filed B-C11A-5 for per-floor attempt weighting if uniform order produces bias. |
| **M8 target-floor selection: deterministic hash-based across all eligible targets** | ✅ | Reject (REVERSED FROM v1.1): pick first eligible in tuple order. **v1.1's "first-eligible" was wrong** (item 3 from v1.1 critique walk) — in 3+ floor dwellings, only one alternative floor was ever explored; remaining eligible floors became unreachable unless upstream ordering changed. Hash-deterministic selection across `(source_signature, generation, operator_index)` preserves determinism (critical for cache reproducibility) while solving starvation. Reject also: pure random / non-deterministic selection (breaks cache reproducibility). Reject also: one M8 application per eligible target (inflates slot consumption N×). Hash-deterministic is the right middle path. |
| **M8 affects exactly TWO floors (old master + new master), reuse the rest** | ✅ | Reject: re-run C9→C10 on every floor on every M8 invocation. Unnecessary work; per-floor briefs only differ on the two affected floors. **v1.1 footnote remains true in v1.2**: when cross-floor constraints land (Spec #1 B-MFDB-C and related), this assumption gets tested. Filed B-C11A-7 for the dependency-invalidation graph if/when cross-floor cascades become real. |
| **Multi-floor canonical signature = `multi_floor_sig_schema=v1` prefix + per-floor signatures + master label, joined + hashed** | ✅ | Reject: include per-floor briefs in signature. The per-floor wrappers ALREADY incorporate brief identity (via their existing single-floor signature derivation); duplicating would inflate hash collisions. Reject also: skip the master label in the signature. M8 mutations produce structurally identical per-floor candidates (the same per-floor WZPCs, just with different has_master_bedroom flags on the underlying briefs); the master label is the distinguishing structural feature. **v1.2 update**: explicit `multi_floor_sig_schema=v1` prefix (item 5) decouples wrapper-level signature versioning from per-floor signature versioning. |
| **`C11A_CACHE_KEY_VERSION` bump v1.1.0 → v1.3.0 (skip v1.2.0)** | ✅ | Reject: two-step bump (v1.1.0 → v1.2.0 at Spec #3 build, then v1.2.0 → v1.3.0 at Spec #4 build). Specs #3 and #4 ship in the same B-NEW-T3 build session; a two-step bump just produces a transient version that never sees production. Single-step bump is cleaner. **v1.2 update**: hierarchical cache versioning (per-component / per-schema independent versions) deferred to Spec #2 B-C9-C overlap (cross-spec concern). |
| **Multi-floor family ID = label-preserving aggregation: `multi_floor:ground=A\|first=B`** | ✅ | Reject (REVERSED FROM v1.1): sorted-by-family aggregation (`multi_floor:A,B`). **v1.1's sorted-family was wrong** (item 4 from v1.1 critique walk) — collapsed architecturally-distinct configurations like `[ground=A, first=B]` and `[ground=B, first=A]` into the same family ID, causing false equivalence + incorrect slot pooling + evolutionary diversity collapse. **v1.2's label-preserving aggregation** sorts by label for determinism while preserving the label-family pairing. |
| **Spec #2 v0.11 § 3.10 trust boundary owned by Spec #3 construction guard + pipeline failure-mode handler, NOT a redundant v1.x-level assertion** | ✅ | Reject: add a redundant assertion in `mutate_topologies` post-C9 fan-out. Redundant assertions on already-unreachable states are noise; Spec #3 MFWZP-5/6 already make the bad state structurally impossible. The pipeline boundary's job is to handle the `ValueError` that Spec #3 raises (as `orchestration_state_drift`, per the v1.2 refined failure taxonomy), not to re-prove the invariant. |
| **M8 failure taxonomy: `no_viable_master_target` / `c9_generation_failed` / `c10_validation_failed` / `orchestration_state_drift`** | ✅ | Reject (REFINED FROM v1.1): single coarse `c9_c10_cascade_failed`. **v1.1's coarse taxonomy was wrong** (item 12 from v1.1 critique walk) — hid C9 vs C10 vs orchestration-drift root causes from observability. v1.2's split provides actionable diagnostics for large search runs. |
| **Pre-flight brief/source alignment validator (`_validate_multi_floor_alignment`)** | ✅ | Reject (NEW IN v1.2): rely on implicit "labels match" expectation. v1.1 said source labels "must match" brief labels but never said HOW that match is verified. A drifted source-vs-brief would produce silent wrong mutations. The explicit pre-flight (item 9 from v1.1 critique walk) catches drift before mutation dispatch. |
| **Lineage `floor_label_affected: str \| None` field** | ✅ | Reject: omit per-floor causality from lineage. v1.1's lineage extension said "operator=M_X, floor_label=L" inline but didn't define the field as part of the lineage data model. v1.2 adds it as an explicit field. **Lightweight version** of the v1.1 critique item 10 request; full ancestry chain filed as B-C11A-8. |
| **Property tests for orchestration invariants** | ✅ | Reject (NEW IN v1.2): rely only on example-based tests. Multi-floor orchestration has combinatorial state interactions (floor ordering × mutation ordering × cache recursion × lineage aggregation); example tests miss combinatorial edge cases (item 11 from v1.1 critique walk). |

---

## § 5 — Test plan

### § 5.1 — New test files / additions

**8 new tests** in a new file `buildemup/tests/test_c11a/test_subsession7_multi_floor.py`:

1. `test_orchestrator_accepts_multi_floor_brief`: `mutate_topologies` with a `MultiFloorDwellingBrief` doesn't error out.
2. `test_orchestrator_dispatches_per_floor_for_tier_a`: a single Tier A operator (e.g., M2) applied to a 2-floor candidate produces a wrapper where only the master floor's per-floor candidate changed.
3. `test_orchestrator_dispatches_per_floor_for_tier_b_m6_m7`: same shape for M6, M7a, M7b.
4. `test_m8_real_execution_produces_wrapper_with_master_swapped`: M8 applied to a 2-floor candidate (master on ground) produces a new wrapper with master on first.
5. `test_m8_target_floor_selection_is_hash_deterministic`: M8 applied twice to the same source at the same generation produces the same target (determinism); M8 on a 3-floor dwelling across multiple generations covers all eligible non-master targets within G iterations (where G ≥ eligible count) — no starvation.
6. `test_m8_no_viable_target_returns_invalid`: M8 on a 2-floor dwelling where the non-master floor has bedroom_count=0 returns `valid=False, invalidity_reason="no_viable_master_target"`.
7. `test_m8_c9_generation_failed_returns_invalid_with_reason`: simulate C9 failure on the new master floor; M8 returns `valid=False, invalidity_reason="c9_generation_failed"`.
8. `test_m8_orchestration_state_drift_caught_as_pipeline_failure`: force a scenario where the assembled wrapper would fail MFWZP-5 (e.g., by mocking C9 to produce zero masters on both affected floors); M8 returns `valid=False, invalidity_reason="orchestration_state_drift"`.

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

**Total**: **18 new example-based tests** PLUS new property-test subsection (see § 5.1.1 below).

### § 5.1.1 — Property tests (NEW in v1.2 per item 11 from v1.1 critique walk)

Example-based tests alone are insufficient for orchestration invariants
because multi-floor state interactions are combinatorial (floor
ordering × mutation ordering × cache recursion × lineage aggregation ×
invariant preservation). Add **~5 property tests** in
`buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py`
using Hypothesis (if available in the project; otherwise parameterized
exhaustive small-state tests):

19. **Signature determinism**: for any valid `MultiFloorWetZonePlannedCandidate`, `derive_canonical_signature(c)` returns the same string across N invocations within the same process. Property: idempotent + pure.
20. **Family-ID determinism**: for any valid wrapper, `multi_floor_family_id(c)` is invariant under tuple reordering that produces the same label-family pairing set. Property: deterministic under permutations.
21. **Master-uniqueness preservation across operator sequences**: starting from a valid wrapper, applying any sequence of (M0, M1, ..., M9) operators (each succeeding, skipping those returning invalid) produces a wrapper where MFWZP-5 still holds — exactly one master bedroom globally. Property: invariant preservation.
22. **Cache-key stability under structurally-equivalent reconstruction**: constructing two `MultiFloorWetZonePlannedCandidate` instances from the same set of per-floor candidates + master label produces identical cache keys. Property: structural equality → cache key equality.
23. **M8 target-selection distribution across generations**: applying M8 to the same source across G generations (varying `generation` parameter) covers all eligible targets within G iterations (where G ≥ number of eligible targets). Property: no starvation under deterministic-hash selection.

Hypothesis-style generators for multi-floor candidates: use the fixture helper
at `buildemup/tests/_multi_floor_fixtures.py` (added per § 5.3) parameterized
over (floor_count: 2..4, master_floor_index: 0..floor_count-1, per_floor_topology_seed: int).

**Property-test acceptance gate**: all property tests must pass with at least 50 randomly-generated examples each. Hypothesis `max_examples=50` (or equivalent enumeration count if using parameterized tests).

### § 5.2 — Existing test regression

Per § 3.10 backwards-compat guarantee: every existing C11a test must pass unchanged modulo the cache-key-version constant tests, which adjust to v1.3.0 directly.

Project total after Spec #2 + #3 + #4 build: **2769 + 18 + ~5 property tests = 2792 passed / 2 skipped / 0 regressions** (approximate; property test count is conservative — Hypothesis may generate more under-the-hood examples, but pytest reports them as 1 test each).

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
| **B-C11A-6** (NEW from v1.1 critique walk item 6) | Replace `type().__name__` / module-path detection (in `is_real_wet_zone_candidate` and `is_real_multi_floor_candidate`) with a marker-attribute pattern or formal Protocol/ABC. Current name-based detection is brittle under refactor / subclass / proxy. Cleanest fix: add `__multi_floor_candidate__: bool = True` class attribute on Spec #3's wrapper (small Spec #3 amendment) OR migrate to formal Protocol typing (Spec #1 B-MFDB-G overlapping) | When name-based detection actually breaks in practice OR when codebase migrates to formal Protocol typing generally | Open (post-v1) |
| **B-C11A-7** (NEW from v1.1 critique walk item 7) | M8 cross-floor cascade invalidation graph. v1.2's M8 assumes exactly two floors change (old master + new master). When vertical wet-stack constraints / plumbing alignment / circulation coupling / adjacency scoring land (Spec #1 B-MFDB-C and related), untouched floors may become indirectly invalidated by an M8 swap. A dependency-invalidation graph would mark dependent floors as dirty and re-run their cascades | When Spec #1 B-MFDB-C (per-floor staircase landing constraints) lands OR when any cross-floor structural constraint enters the pipeline | Open — gated on B-MFDB-C |
| **B-C11A-8** (NEW from v1.1 critique walk item 10) | Full multi-floor lineage extension: floor ancestry IDs, mutation provenance chains, master-transition events, per-floor generation counters. v1.2's minimum addition is `floor_label_affected: str \| None` only | When NSGA-II explainability tooling needs the richer model OR when debugging multi-floor evolution becomes a real workflow concern | Open (post-v1) |
| **B-C11A-9** (NEW from v1.1 critique walk item 13) | Wrapper-reassembly allocation churn reduction. Repeated `with_floor_replaced()` calls in long evolutionary runs may produce avoidable allocation overhead. Options: batched floor-replacement APIs, structural sharing / persistent data structures, builder-style assembly before final immutable freeze | When perf telemetry shows allocation overhead is a real bottleneck during large evolutionary runs | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK (and assuming all four specs are LOCKED — this amendment is the last):

**Files modified**:

- `buildemup/domain/floor_brief.py`: add `has_master_bedroom: bool = True` (per Spec #2). ~3 lines + docstring.
- `buildemup/components/c09/room_sizer.py`: 2 line-edits at lines 498 and 548 (per Spec #2).
- `buildemup/components/c11a/cache.py`: bump `C11A_CACHE_KEY_VERSION` to `"v1.3.0"`.
- `buildemup/components/c11a/source_signature.py`: add multi-floor dispatch in `derive_canonical_signature`; add `_derive_multi_floor_canonical_signature` helper with `multi_floor_sig_schema=v1` prefix (v1.2 item 5).
- `buildemup/components/c11a/candidate_context.py`: add `is_real_multi_floor_candidate`.
- `buildemup/components/c11a/orchestrator.py`: add per-floor expansion logic in `mutate_topologies`; add Tier A / B per-floor dispatch helpers; add `_validate_multi_floor_protocol()` (v1.2 item 1) and `_validate_multi_floor_alignment()` (v1.2 item 9) pre-flights.
- `buildemup/components/c11a/operators/m8_vert_rearr.py`: replace stub with real `_build_m8_mutation` using hash-deterministic target selection (v1.2 item 3).
- `buildemup/components/c11a/family_slot_allocator.py`: add multi-floor family aggregation with label-preserving pairs (v1.2 item 4).
- `buildemup/components/c11a/lineage.py`: add multi-floor lineage extension with `floor_label_affected: str | None` field (v1.2 item 10).
- `buildemup/components/c11a/errors.py`: add `OrchestrationError` base + `OrchestrationProtocolError` + `OrchestrationAlignmentError` (v1.2 items 1 + 9).
- `buildemup/components/c11a/schema.py`: extend `MutationApplicationResult.invalidity_reason` enum (or string-union) to include `c9_generation_failed`, `c10_validation_failed`, `orchestration_state_drift`, `no_viable_master_target` (v1.2 item 12).
- **Plumbing**: if `generation` is not currently in `config` or threaded through the operator-attempt loop, add it (v1.2 item 3 requirement). Build-session detail.

**Files created**:

- `buildemup/domain/multi_floor_brief.py` (per Spec #1, ~210 lines).
- `buildemup/domain/multi_floor_candidate.py` (per Spec #3, ~250 lines).
- `buildemup/components/c11a/m8_floor_swap_real.py` (this amendment, ~150 lines).
- `buildemup/tests/test_domain_multi_floor_brief.py` (per Spec #1, ~45 tests).
- `buildemup/tests/test_domain_multi_floor_candidate.py` (per Spec #3, ~35 tests).
- `buildemup/tests/test_c11a/test_subsession7_multi_floor.py` (this amendment, ~18 tests).
- `buildemup/tests/test_c11a/test_subsession7_multi_floor_properties.py` (v1.2 item 11, ~5 property tests).
- `buildemup/tests/_multi_floor_fixtures.py` (helper, no tests).

**Tests added**: Spec #2 (~9) + Spec #3 (~35) + this amendment (~18 example-based + ~5 property tests) = **~67 new tests**.

**Test count after build**: 2760 baseline + 67 = **~2827 passed**, modulo any test-count drift.

**Estimated build effort**: ~3-5 sessions of focused work. v1.2's substantive changes (all-floors Tier A/B, hash-based M8 target) add modest implementation complexity vs v1.1 but no new files. Largest items remain C11a orchestrator multi-floor expansion + M8 real wiring + signature/cache/lineage extensions.

---

## § 9 — Status

- **v1.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v1.3 PROPOSED.
- After LOCK: **B-NEW-T3 build can begin** (all four specs LOCKED).
- **Convergence note**: v1.1 → v1.2 was the largest delta in the S40-continuation spec sequence — two real behavioral changes (Tier A/B all-floors; M8 hash-based target) + 7 documentation/validation patches + 5 new backlog items. Reviewer correctly caught real design defects in the first-round draft; this is exactly what critique walks exist to do.

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

**Summary**: largest of the four B-NEW-T3 specs. Threads multi-floor through every C11a pipeline stage. v1.2 adds 5 new backlog items (B-C11A-5 through 9) on top of v1.1's 4 (B-C11A-1 through 4). After LOCK, the B-NEW-T3 build session begins — the largest implementation work item in S41+.

---

**End of C11a Amendment v1.2 PROPOSED.**
