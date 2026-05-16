# C9 SPEC AMENDMENT v0.8 PROPOSED — `has_master_bedroom` flag on `FloorRoomBrief` (B-NEW-T3 enabler #2 of 4)

**Component**: 9 (Room Sizing — SHIPPED at v0.7 LOCKED).
**Spec status**: **v0.8 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-Spec-#1 LOCK.
**Driver**: Spec #2 of 4 — directly required by Spec #1 (`MultiFloorDwellingBrief`) Inv MFDB-6 coupling contract. Without this amendment, multi-floor briefs cannot drive correct C9 master-room designation.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v0.8 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v0_8_LOCKED.md` (if approved as-is),
- `..._v0_9_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

---

## § 1 — Why this amendment exists

Spec #1 (`MultiFloorDwellingBrief` v0.5 LOCKED) defines `master_bedroom_floor_label` as the dwelling-level designation of which floor hosts the master bedroom. Per Inv MFDB-6, that designation is FLOOR-LEVEL ONLY; WHICH ROOM on the master floor is master is delegated to C9 via the `master_bedroom_selector` field (currently always `"first_bedroom"`).

For C11a's multi-floor pipeline (Spec #4) to drive C9 correctly, each per-floor C9 invocation must know whether THIS floor's bedroom #1 should be designated master. Without this signal, C9 would either:
- Always treat bedroom #1 as master (current v0.7 behaviour) — wrong for multi-floor; produces N master bedrooms in an N-floor dwelling, violating the canonical Spec #1 Inv MFDB-5.
- Never treat bedroom #1 as master — wrong for single-floor; breaks v1 backwards compat.

The cleanest signal at the per-floor C9 boundary is a flag on `FloorRoomBrief` itself, set by the C11a orchestrator (Spec #4) using Spec #1's `iter_floors_with_master_flag()` helper.

**This amendment adds that flag**, defaulting to `True` so all existing single-floor callers continue working byte-identical to v0.7.

---

## § 2 — Delta from v0.7 → v0.8

| Item | v0.7 LOCKED | v0.8 PROPOSED |
|---|---|---|
| `FloorRoomBrief` schema | 8 fields (bedroom_count, bathroom_count, has_kitchen, has_living, has_pooja, has_utility, other_rooms, floor_label) | 9 fields — adds `has_master_bedroom: bool = True` |
| `_materialise_rooms` bedroom loop (line 498) | `is_master = (i == 0)` | `is_master = (i == 0) and brief.has_master_bedroom` |
| `_materialise_rooms` bathroom loop (line 548) | `is_master = (i == 0)` | `is_master = (i == 0) and brief.has_master_bedroom` |
| `C11A_CACHE_KEY_VERSION` (in `c11a/cache.py`) | `"v1.0.0"` | `"v1.1.0"` (per Spec #1 § 3.6 normalization-versioning contract — adding a hash-participating field to a nested-in-multi-floor dataclass requires cache-key bump) |
| All other C9 logic | unchanged | UNCHANGED |
| Inv 13 / Inv 14 (is_master only valid on BEDROOM/BATHROOM) | Runtime-enforced in `RoomSizeRequirement.__post_init__` | UNCHANGED |
| nbc_table lookup keys `(tier, category, is_master, bathroom_subtype)` | unchanged | UNCHANGED |
| All other components (C5, C8, C10, C11a operators) | consume FloorRoomBrief but don't read is_master | UNAFFECTED — default `True` preserves behaviour for any consumer |

**Total diff**: 1 schema field + 2 line-changes in C9 + 1 constant bump.

---

## § 3 — Behavioral contract

### § 3.1 — Default (single-floor; existing callers)

`FloorRoomBrief(...)` without `has_master_bedroom` → field defaults to `True` → v0.7 behaviour preserved byte-identical:
- bedroom #1 → `is_master=True` (becomes "the master bedroom").
- bathroom #1 → `is_master=True` (becomes "the master bathroom" — en-suite convention).
- All other rooms: `is_master=False` (Inv 13/14 already ensure this for KITCHEN/LIVING/POOJA/UTILITY/OTHER).

Every existing single-floor test, fixture, and call site continues working without code changes.

### § 3.2 — Multi-floor (master floor)

A `FloorRoomBrief` with `has_master_bedroom=True` (default) on the master floor → byte-identical to v0.7 single-floor:
- bedroom #1 master, bathroom #1 master, etc.

Constraint: the master floor MUST have `bedroom_count >= 1` (already enforced by Spec #1 Inv MFDB-4). C9 amendment does not enforce this independently — Spec #1 is the gatekeeper.

### § 3.3 — Multi-floor (non-master floor)

A `FloorRoomBrief` with `has_master_bedroom=False` on a non-master floor → no master designation:
- ALL bedrooms: `is_master=False` (line 498 short-circuits via the `and` clause).
- ALL bathrooms: `is_master=False` (line 548 same).

This is the corrective behaviour for multi-floor: in a 3-floor dwelling, exactly ONE floor has `has_master_bedroom=True`; the other two have `False`. C9 outputs ZERO is_master rooms on the non-master floors and the conventional 1 master bedroom + 1 master en-suite bathroom on the master floor.

### § 3.4 — Master bathroom coupling (en-suite convention)

The `has_master_bedroom: bool` flag controls BOTH:
- Whether bedroom #1 receives `is_master=True`.
- Whether bathroom #1 receives `is_master=True`.

This reflects Indian residential convention: the master bathroom is en-suite to the master bedroom; both belong on the same floor or neither does. The flag's name (`has_master_bedroom`) is slightly imprecise for this dual role — Spec #1 v0.5 LOCKED explicitly references this name (§ 1, § 0.1, § 2 docstring, § 3.2 MFDB-6 row), so this amendment honours that commitment. An alternative name like `has_master_suite` would be more accurate; it's deferred to a future amendment if/when split flags become necessary (filed as B-C9-A in § 7).

### § 3.5 — `nbc_table` lookups remain valid

`nbc_table.lookup_nbc_minimum(tier, category, is_master, bathroom_subtype)` is unaffected. The lookup keys still cover `is_master ∈ {True, False}` for both BEDROOM and BATHROOM categories. No NBC/IS rows added or removed. The amendment changes WHO is master (depending on the floor brief), not WHAT a master room's minimum is.

### § 3.6 — Inv 13 / Inv 14 sentinel: `is_master=True` ONLY valid on BEDROOM/BATHROOM

Already runtime-enforced in `RoomSizeRequirement.__post_init__`. The amendment doesn't touch this; the existing guard catches any future bug that accidentally lifts the flag onto a non-BEDROOM/BATHROOM room.

### § 3.7 — Backwards compatibility (single-floor unchanged)

The default value `has_master_bedroom=True` makes this amendment **non-breaking**:

- Every existing `FloorRoomBrief(...)` construction: gets the default `True`, behaves identically.
- Every existing single-floor C9 test: passes unchanged.
- Every existing C5/C8/C10 consumer: sees a `FloorRoomBrief` with one extra field that doesn't affect their logic.
- Every existing brief-capture endpoint output: gets the default.

The only consumer that READS `has_master_bedroom` is `_materialise_rooms` in C9. Adding the field is purely additive at the consumption side.

### § 3.8 — Cache-key version bump (Spec #1 § 3.6 contract)

Per Spec #1 § 3.6 normalization-versioning contract paragraph 4: "Any future spec amendment that adds new fields to MultiFloorDwellingBrief that participate in equality / hash" requires bumping `C11A_CACHE_KEY_VERSION`.

`FloorRoomBrief` is nested inside `MultiFloorDwellingBrief.floors: tuple[FloorRoomBrief, ...]`. Adding a field to `FloorRoomBrief` changes its hash, which propagates up through the tuple to the wrapper's hash, which feeds the C11a cache key derivation. Therefore:

- `c11a/cache.py` line 68: `C11A_CACHE_KEY_VERSION: str = "v1.0.0"` → `"v1.1.0"`.
- One-line change. No cache-content migration needed since C11a's cache is currently in-memory + process-lifetime only (per S39 backlog — process-lifetime cache itself is not yet filed as B-NEW-E2). Persisted-cache migration is out-of-scope.

If/when persisted cache lands, the bump from `v1.0.0` → `v1.1.0` will trigger clean invalidation per Spec #1 § 3.6 contract step 1.

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Field name `has_master_bedroom: bool`** | ✅ | Reject: `is_master_floor`, `has_master_suite`, `floor_hosts_master`. Spec #1 v0.5 LOCKED explicitly references `has_master_bedroom` four times. Honouring locked-spec commitments. Imprecision (the flag controls both bedroom AND bathroom) noted in § 3.4. |
| **Default `True`** | ✅ | Reject: default `False`. Default-True preserves byte-identical v0.7 behaviour for every existing single-floor caller; default-False would require touching every existing FloorRoomBrief construction site. The "wrong default" choice trades 0 migrations for hundreds. |
| **Single flag controls both bedroom AND bathroom master** | ✅ | Reject: split into `has_master_bedroom` + `has_master_bathroom`. Indian residential convention couples them (en-suite). Splitting adds complexity for no current real-world need. Forward-compat: B-C9-A files the split for if it's ever needed. |
| **Modify `_materialise_rooms` lines 498 + 548 only** | ✅ | Reject: separate dispatch path / strategy pattern for "master designation strategy." Two-line edit beats indirection layer for a coupling that's currently deterministic. |
| **C11A_CACHE_KEY_VERSION bumped to v1.1.0** | ✅ | Reject: leave at v1.0.0. Spec #1 § 3.6 contract paragraph 4 explicitly requires the bump for any field-addition to a hash-participating nested type. |
| **No new C9 invariants** | ✅ | Reject: add an "Inv 15: at most one floor has has_master_bedroom=True across a multi-floor brief." That invariant belongs to Spec #1 (MFDB-5) which is the dwelling-level contract; C9 only sees one floor at a time and cannot enforce a cross-floor invariant. Layering correctly. |
| **No NBC/IS table changes** | ✅ | Reject: add per-floor adjusted master-minimum rules. C9's NBC table already covers `(tier, BEDROOM, is_master=True, ...)` correctly. The amendment changes WHO is master, not their minimum. No table changes. |
| **No C5/C8/C10 amendments needed** | ✅ | Reject: cascade amendments through every brief consumer. Empirically verified: C5 reads scalar fields only; C8 doesn't consume the brief; C10 reads scalars only. None reads is_master semantics from the brief. The amendment is strictly C9-internal. |

---

## § 5 — Test plan

### § 5.1 — Test additions to `buildemup/tests/test_c9_orchestrator.py` (or new file `test_c09_v0_8_master_bedroom_flag.py`)

8 tests:

1. `test_floor_room_brief_default_has_master_bedroom_is_true`: construction without the flag → field is True. Backwards-compat sentinel.
2. `test_floor_room_brief_accepts_has_master_bedroom_false`: explicit `has_master_bedroom=False` construction succeeds.
3. `test_floor_room_brief_with_master_true_produces_master_bedroom`: `has_master_bedroom=True`, bedroom_count=2 → bedroom #1 has `is_master=True`, bedroom #2 has `is_master=False`. (Existing behaviour sentinel.)
4. `test_floor_room_brief_with_master_false_produces_no_master_bedroom`: `has_master_bedroom=False`, bedroom_count=2 → both bedrooms have `is_master=False`.
5. `test_floor_room_brief_with_master_true_produces_master_bathroom`: `has_master_bedroom=True`, bathroom_count=2 → bathroom #1 has `is_master=True`, bathroom #2 has `is_master=False`. (Existing en-suite behaviour sentinel.)
6. `test_floor_room_brief_with_master_false_produces_no_master_bathroom`: `has_master_bedroom=False`, bathroom_count=2 → both bathrooms have `is_master=False`.
7. `test_brief_with_master_false_and_zero_bedrooms_produces_no_rooms`: edge case — `has_master_bedroom=False, bedroom_count=0` → 0 bedroom rooms (the flag is irrelevant when there are no bedrooms; sanity sentinel that the flag short-circuit doesn't break empty-bedroom path).
8. `test_brief_equality_includes_has_master_bedroom`: two briefs identical except for `has_master_bedroom` are NOT equal (hash-participation sentinel — supports the cache-key bump rationale).

### § 5.2 — Existing C9 test regression

All current ~80 C9-related tests must pass unchanged. Default `True` preserves single-floor behaviour byte-identical.

### § 5.3 — C11a cache-key version sentinel

1 test in `buildemup/tests/test_c11a/test_c11a_subsession5_candidate_context.py` (or wherever cache-key tests live):

9. `test_c11a_cache_key_version_is_v1_1_0`: confirms the constant value. Sentinel against accidental regression.

### § 5.4 — Total

**~9 new tests**. Existing test count after this amendment: **2760 + 9 = 2769** (no regressions allowed).

---

## § 6 — Out-of-scope

- **Spec #3** (`MultiFloorWetZonePlannedCandidate`): output-side wrapper; not affected by the brief-level flag.
- **Spec #4** (C11a Amendment v1.1): orchestrator pipeline rework. C11a sets `has_master_bedroom` per floor by reading Spec #1's `iter_floors_with_master_flag()` and constructing per-floor `FloorRoomBrief` instances accordingly. That construction logic is in Spec #4, not here.
- **Per-bathroom subtype expansion** (B-208): unrelated; previously-known C9 limitation, untouched by this amendment.
- **Master suite splitting** (`has_master_bedroom` + `has_master_bathroom` separate flags): deferred to B-C9-A.
- **Multiple master bedrooms / dual masters**: deferred per Spec #1 § 6 (B-MFDB-J).
- **Dwelling-level "exactly one master floor" cross-validation**: belongs in Spec #1 (MFDB-5); not C9's concern.
- **C5 / C8 / C10 amendments**: empirically not needed (none read `is_master` from the brief).

---

## § 7 — Backlog items deferred

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-C9-A** (NEW) | Split `has_master_bedroom: bool` into two flags `has_master_bedroom: bool` + `has_master_bathroom: bool` to support dwellings where master bedroom and master bathroom are on different floors (non-en-suite) | When a real-world brief surfaces a non-en-suite master arrangement (rare in residential; might appear in luxury / commercial paths) | Open (post-v1) |
| **B-C9-B** (NEW) | Reconsider field name (`has_master_bedroom` → `has_master_suite`) when the en-suite coupling becomes either documented or contested | When B-C9-A is approved OR when a future amendment splits the master designation more finely | Open (post-v1) |

Pre-existing C9 backlog (B-208 per-bathroom subtype expansion etc.) unaffected.

---

## § 8 — Build-session readiness

Build scope (when all four specs LOCK):

- `buildemup/domain/floor_brief.py`: 1 field added (~3 lines of code + docstring update).
- `buildemup/components/c09/room_sizer.py`: 2 line edits (lines 498 and 548).
- `buildemup/components/c11a/cache.py`: 1 constant bump (line 68).
- `buildemup/tests/test_c09_v0_8_master_bedroom_flag.py` (new): ~8 tests.
- `buildemup/tests/test_c11a/...` (existing test file): 1 cache-version sentinel test.

**Estimated effort**: ~20-30 minutes. Smallest of the four B-NEW-T3 specs.

---

## § 9 — Status

- **v0.8 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v0.9 PROPOSED.
- After LOCK: spec drafting proceeds to **Spec #3 (`MultiFloorWetZonePlannedCandidate`)**.
- Code work: deferred until all four specs LOCKED.

---

## § 10 — Rule 9 backlog enumeration

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| **Spec #1** | `MultiFloorDwellingBrief` v0.5 LOCKED | S40-cont discovery | DONE | LOCKED | DONE |
| **Spec #2** | This amendment | Spec #1 Inv MFDB-6 coupling | LOCK pending | IN-FLIGHT | S |
| **Spec #3** | `MultiFloorWetZonePlannedCandidate` | Multi-floor output type | After Spec #2 LOCKs | NEXT | M |
| **Spec #4** | C11a Amendment v1.1 — multi-floor pipeline rework | Specs #1-3 LOCKED | After Spec #3 | LARGE | L |
| **B-NEW-T3** | M8 multi-floor real upstream wiring | All 4 specs LOCKED | All four LOCK | GATED | L (post-LOCK) |
| **B-C9-A** | Split master flag into bedroom + bathroom variants | This amendment | Real-world non-en-suite case | OUT-OF-SCOPE this amendment | S (post-v1) |
| **B-C9-B** | Reconsider field name when en-suite coupling becomes contested | This amendment | B-C9-A approval | OUT-OF-SCOPE this amendment | trivial (post-v1) |
| B-208 | Per-bathroom subtype expansion (pre-existing) | C9 v0.7 history | future C9 amendment | UNAFFECTED | M (post-v1) |

**Summary**: smallest of the four B-NEW-T3 specs. One field, two line-edits, one constant bump. Two new backlog items (B-C9-A, B-C9-B) for forward-compat. Pre-existing C9 backlog unaffected.

---

**End of C9 Amendment v0.8 PROPOSED.**
