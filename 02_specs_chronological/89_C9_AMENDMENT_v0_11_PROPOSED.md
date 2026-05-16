# C9 SPEC AMENDMENT v0.11 PROPOSED — `has_master_bedroom` flag on `FloorRoomBrief` (B-NEW-T3 enabler #2 of 4)

**Component**: 9 (Room Sizing — SHIPPED at v0.7 LOCKED).
**Spec status**: **v0.11 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-v0.10 critique walk.
**Driver**: Spec #2 of 4 — directly required by Spec #1 (`MultiFloorDwellingBrief`) Inv MFDB-6 coupling contract.

**Note on v0.11 vs v0.10**: third documentation-polish round. **No schema or runtime changes.** Three single-paragraph patches + 2 new backlog filings + 1 typo fix. Functionally and structurally identical to v0.10.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v0.11 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v0_11_LOCKED.md` (if approved as-is),
- `..._v0_12_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

---

## § 0.1 — Delta from v0.10 → v0.11 (critique walk patches)

v0.10 PROPOSED received an external critique with 12 items. Reviewer noted
"v0.10 has entered convergence-hardening mode" and "LOCK READINESS: extremely
high. Remaining meaningful risk is no longer runtime correctness; it is
future architectural evolution pressure." Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| CRITICAL-1 (architecture depends on prose for correctness) | REJECT | None — already covered by B-C9-E |
| MAJOR-1 (trust-boundary fast-fail still hypothetical until Spec #4) | REJECT | None — properly owned by § 6 forward-pointer |
| MAJOR-2 (equality semantics overload) | PARTIAL ACCEPT | § 3.9 reader-warning + new B-C9-F |
| MAJOR-3 (semantic gravity) | REJECT | None — implicit re-tagging already done in v0.10 |
| MAJOR-4 (precedent-narrowing rule subjective) | PARTIAL ACCEPT | § 3.9 examples + new B-C9-G |
| MODERATE-1 (backlog as proto-specs) | REJECT | None — Rule 9 visibility is intentional |
| MODERATE-2 (master-suite centrality) | REJECT | None — covered by B-MFDB-J + B-C9-A |
| MODERATE-3 (fast-fail expensive in future distributed pipelines) | REJECT | None — post-v1 forward observation |
| MODERATE-4 (Spec #2 carrying architectural burden beyond scope) | REJECT | None — same class as Spec #1 B-MFDB-N |
| MINOR-1 (§ 2 header stale) | ACCEPT | § 2 — typo fix |
| MINOR-2 (descriptive vs normative tone mixing) | REJECT | None — non-actionable |
| MINOR-3 (architectural debt inventory growing) | REJECT | None — non-actionable |

**Net schema delta from v0.10**: NONE. Three single-paragraph patches +
2 new backlog filings (B-C9-F, B-C9-G) + 1 typo fix.

Nine rejects with reasoning preserved (most reviewer-self-acknowledged as
non-actionable).

**Convergence signal**: third consecutive round with NO schema changes.
v0.8 → v0.9, v0.9 → v0.10, v0.10 → v0.11 — all doc-only. Spec #2 has
fully converged at the runtime level.

---

## § 1 — Why this amendment exists

Spec #1 (`MultiFloorDwellingBrief` v0.5 LOCKED) defines `master_bedroom_floor_label` as the dwelling-level designation of which floor hosts the master bedroom. Per Inv MFDB-6, that designation is FLOOR-LEVEL ONLY; WHICH ROOM on the master floor is master is delegated to C9 via the `master_bedroom_selector` field (currently always `"first_bedroom"`).

For C11a's multi-floor pipeline (Spec #4) to drive C9 correctly, each per-floor C9 invocation must know whether THIS floor's bedroom #1 should be designated master. Without this signal, C9 would either:
- Always treat bedroom #1 as master (current v0.7 behaviour) — wrong for multi-floor; produces N master bedrooms in an N-floor dwelling, violating the canonical Spec #1 Inv MFDB-5.
- Never treat bedroom #1 as master — wrong for single-floor; breaks v1 backwards compat.

The cleanest signal at the per-floor C9 boundary is a flag on `FloorRoomBrief` itself, set by the C11a orchestrator (Spec #4) using Spec #1's `iter_floors_with_master_flag()` helper.

**This amendment adds that flag**, defaulting to `True` so all existing single-floor callers continue working byte-identical to v0.7.

**Systemic importance note** (MINOR-1 from v0.8 critique walk): the code diff for this amendment is small — one schema field, two line-edits, one constant bump. **The semantic surface is much larger than the line count suggests.** Before this amendment, master-room designation was self-contained in C9: every C9 invocation deterministically produced exactly one master bedroom and one master bathroom. After this amendment, master designation is a distributed-correctness concern — C9 trusts upstream orchestration (Spec #4) to set `has_master_bedroom` correctly per floor, and dwelling-level uniqueness (Spec #1 Inv MFDB-5) is enforced at a different layer entirely. Treat this amendment as architecturally foundational despite its small diff.

---

## § 2 — Delta from v0.7 → v0.11

| Item | v0.7 LOCKED | v0.11 PROPOSED |
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

### § 2.1 — `has_master_bedroom` field docstring (NEW in v0.9)

The field's runtime docstring (in `floor_brief.py`) MUST include:

```python
has_master_bedroom: bool = True
"""Whether THIS floor hosts the master bedroom (and en-suite master bathroom).

NATURE OF THIS FIELD (CRITICAL-1 from v0.8 critique walk):
This is **orchestration-contextual metadata, not an intrinsic floor
property.** A floor does not objectively "have a master bedroom" — that
designation is a dwelling-level decision (which floor of an N-floor
dwelling hosts the master bedroom). This field is the per-floor signal
the C11a orchestrator passes to C9 so room sizing knows whether to
designate bedroom #1 / bathroom #1 as master.

The field LIVES on FloorRoomBrief because that's the cleanest signal at
the C9 boundary, but its VALUE is set by orchestration upstream (Spec #4
constructs per-floor briefs from a MultiFloorDwellingBrief, using
``iter_floors_with_master_flag()`` per Spec #1 § 3.3).

DEFAULT (True): standalone FloorRoomBrief instances default to True
because they conventionally represent single-floor dwellings, where
the only floor IS the master floor by definition. This preserves
v0.7 byte-identical behaviour for every existing single-floor caller.

HASH PARTICIPATION (MINOR-2 from v0.8 critique walk): this field
participates in dataclass equality and hash. Two FloorRoomBriefs
identical except for has_master_bedroom are NOT equal and hash
differently. This propagates upward into MultiFloorDwellingBrief's
hash, which is why this amendment requires a C11A_CACHE_KEY_VERSION
bump per Spec #1 § 3.6 normalization-versioning contract.

CONTROLS BOTH BEDROOM AND BATHROOM MASTER DESIGNATION
(see § 3.4 for the en-suite coupling rationale).
"""
```

This docstring is normative; future C9 amendments touching the field MUST preserve the orchestration-contextual framing (CRITICAL-1) and the hash-participation note (MINOR-2).

---

## § 3 — Behavioral contract

### § 3.1 — Default (single-floor; existing callers)

`FloorRoomBrief(...)` without `has_master_bedroom` → field defaults to `True` → v0.7 behaviour preserved byte-identical:
- bedroom #1 → `is_master=True` (becomes "the master bedroom").
- bathroom #1 → `is_master=True` (becomes "the master bathroom" — en-suite convention).
- All other rooms: `is_master=False` (Inv 13/14 already ensure this for KITCHEN/LIVING/POOJA/UTILITY/OTHER).

Every existing single-floor test, fixture, and call site continues working without code changes.

**Default-True semantic acknowledgement** (MAJOR-1 from v0.8 critique walk):
the default `True` operationally preserves v0.7 behaviour but semantically
encodes the worldview "outside a `MultiFloorDwellingBrief` context, a
standalone `FloorRoomBrief` is assumed to represent a single-floor dwelling
and therefore hosts the master." This worldview holds in v1 — every
existing single-floor brief in fact hosts the master — but it's a
default-as-policy, not a default-as-no-op. Spec consumers writing
multi-floor briefs MUST set `has_master_bedroom` explicitly (typically
False on non-master floors), and the orchestrator (Spec #4) handles
this via `iter_floors_with_master_flag()` per Spec #1 § 3.3.

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

**Naming rationale** (MAJOR-2 from v0.8 critique walk): the field is
intentionally named from the bedroom perspective because the bedroom is
treated as the canonical source of master-suite identity. The bathroom's
master designation is **derivative** — a consequence of the en-suite
architectural pattern, not an independent decision. If the en-suite
coupling ever breaks (B-C9-A trigger condition), the canonical answer
will still be "follow the bedroom"; the bathroom's status will be
re-derived under whatever new rule applies. Naming from the canonical
side keeps the field's intent stable across future evolution.

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

### § 3.9 — `has_master_bedroom` is orchestration-contextual, not intrinsic (CRITICAL-1)

The `has_master_bedroom` field encodes a dwelling-relative decision
("which floor of this multi-floor dwelling hosts the master"), not an
intrinsic property of the floor itself. The same `FloorRoomBrief`
content (bedroom_count, bathroom_count, has_kitchen, etc.) can
legitimately exist as the master floor in one dwelling and a non-master
floor in another. The field is **orchestration-derived state embedded in
a domain dataclass**.

This is a deliberate layering choice — putting the signal at the
`FloorRoomBrief` level keeps C9's per-floor input self-describing and
avoids passing a separate "is this floor master?" parameter to every
C9 entry point. The trade-off is that `FloorRoomBrief` is no longer a
purely-intrinsic floor description; it now carries one
orchestration-contextual bit.

**Implications for spec consumers**:
- Do NOT cache `FloorRoomBrief` instances as if they were dwelling-independent canonical descriptions of a floor's content.
- Two floors with identical room composition but different `has_master_bedroom` values are NOT the same floor (per equality / hash semantics — see field docstring).
- Any future C9 amendment that promotes additional dwelling-context fields onto `FloorRoomBrief` should weigh layering blur against per-call signal clarity (the trade-off this amendment made).
- A future architecture refactor MAY split `FloorRoomBrief` into intrinsic-properties + orchestration-context-wrapper. That's filed as a forward-architecture concern, not a v1 blocker.

**Reuse safety clarifier** (MINOR-2 from v0.9 critique walk): the field is
orchestration-contextual, but it is also fully **deterministic and
structurally valid**. A `FloorRoomBrief` instance can be safely passed
between code paths, stored in collections, used in tests, and round-tripped
through equality checks — provided callers honour the field's actual
semantics. "Orchestration-contextual" means "its CORRECT VALUE depends on
dwelling context"; it does NOT mean "this dataclass is unsafe to reuse."

**Precedent narrowing** (CRITICAL-1 from v0.9 critique walk): this
amendment's acceptance of orchestration-contextual metadata in a domain
dataclass should NOT be interpreted as general permission to embed
arbitrary orchestration metadata into domain dataclasses. The trade-off
was accepted specifically because **master designation directly affects
room materialization semantics** (it determines which room receives the
master NBC sizing) and the per-floor C9 boundary is the cleanest place to
deliver that signal. Future proposals to add lineage tags, mutation
provenance, replay context, cascade annotations, or other
orchestration-derived fields onto `FloorRoomBrief` (or any other domain
dataclass) MUST justify the layering blur on the same grounds: the field
must directly affect the domain object's runtime behaviour, not merely
"travel with it for orchestration convenience." Bare convenience is NOT
sufficient justification.

**Worked examples for the precedent-narrowing rule** (MAJOR-4 from v0.10
critique walk): the "directly affect runtime behaviour" criterion is
inherently judgement-based; future proposals are likely to argue various
flavours of "but my field also affects behaviour." Two examples to
calibrate:

- **POSITIVE** — `has_master_bedroom` (this amendment): C9's
  `_materialise_rooms` reads the field and produces materially different
  output (different room with `is_master=True`, different NBC table
  lookup, different target_m2). The field's value DIRECTLY changes the
  domain object's primary computational behaviour. **Acceptable**.

- **NEGATIVE** — hypothetical `mutation_lineage_tag: str` proposal: a
  field that records "this brief was produced by mutation M5 from parent
  brief XYZ" so orchestrators can reconstruct lineage. Even though
  orchestration uses this field, C9's room-sizing math does not branch
  on it; the field exists purely for orchestration bookkeeping. The
  proposal's correct home is on the orchestration layer (e.g.,
  `MultiFloorWetZonePlannedCandidate.provenance`), NOT on the domain
  brief. **Not acceptable** under this rule.

The criterion to apply: "Does C9's (or the domain consumer's) computation
read this field and produce different output?" If the answer is no, the
field doesn't belong on the domain dataclass. When future proposals
accumulate enough debate, this convention may need formalising as
architecture-governance precedent (filed as B-C9-G).

**Equality-semantics overload acknowledgement** (MAJOR-2 from v0.10
critique walk): a consequence of `has_master_bedroom`'s hash and
equality participation is that two `FloorRoomBrief` instances with
identical room composition but different master flags are NOT equal.
Said another way:

```
brief_a = FloorRoomBrief(bedroom_count=2, ..., has_master_bedroom=True)
brief_b = FloorRoomBrief(bedroom_count=2, ..., has_master_bedroom=False)
brief_a != brief_b  # despite same physical floor topology
```

This is the correct behaviour given the field's hash participation
(otherwise C11a cache slots would collide). But it means **equality**
on `FloorRoomBrief` now answers the question "are these floors
topologically AND orchestrationally equivalent?" — NOT "are these
floors physically the same?" Future code paths that need
*physical-only* equivalence (deduplication of structurally-equal
floors across briefs, topology canonicalization, lineage clustering)
MUST NOT use `==` directly; they need a derived comparison that
ignores `has_master_bedroom`. A canonical
"physical-equivalence" helper is filed as B-C9-F. Until that lands,
callers should compare `dataclasses.replace(a, has_master_bedroom=True) == dataclasses.replace(b, has_master_bedroom=True)`
for physical-only equivalence — but treat that idiom as transitional
and prefer the future helper when it exists.

### § 3.10 — Trust boundary: C9 trusts upstream orchestration for master uniqueness (MAJOR-3)

Before this amendment, C9 was self-contained for master-room designation: every
invocation of `_materialise_rooms` deterministically produced exactly one
master bedroom and one master bathroom for any non-empty floor. After
this amendment, master-room production depends on `brief.has_master_bedroom`,
which is set by upstream orchestration.

**This is a transition from self-contained behaviour to distributed
correctness.** A bug in upstream orchestration (Spec #4) could cause:
- Zero master bedrooms across a multi-floor dwelling (if all floors get `has_master_bedroom=False`).
- Multiple master bedrooms across a multi-floor dwelling (if multiple floors get `has_master_bedroom=True`).
- Master bedroom on a floor with bedroom_count=0 (if `has_master_bedroom=True` but no bedrooms exist on that floor — produces no master bedroom but also no error from C9, just a silently empty master designation).

**C9 itself does NOT enforce dwelling-level master uniqueness.** That
invariant belongs to Spec #1 (Inv MFDB-5: exactly one floor canonically
designated as the master floor) and is the responsibility of the
orchestrator (Spec #4) to honour. C9 trusts that:

- The brief it receives has a correctly-set `has_master_bedroom` flag.
- Across all per-floor C9 invocations within a single dwelling, exactly one floor's brief will have `has_master_bedroom=True`.

**This trust boundary is intentional** — enforcing dwelling-level
invariants from inside C9 would require C9 to know about other floors
it doesn't otherwise see, which violates the per-floor encapsulation
that's been the C9 contract since v0.1.

Spec #4 (C11a Amendment v1.1) is expected to own the dwelling-level enforcement,
likely via a debug-mode assertion that verifies "exactly one master
bedroom emitted across all per-floor C9 results" before assembling the
multi-floor candidate. See § 6 forward-pointer.

**Assertion lifecycle expectation** (MAJOR-1 from v0.9 critique walk):
the Spec #4 assertion is intended to fail **immediately during multi-floor
candidate assembly**, before downstream scoring, caching, or persistence
occurs. This makes the trust boundary operationally meaningful: a
malformed orchestration that produces zero or multiple masters fails fast
with a diagnostic error, rather than silently propagating an invalid
candidate through C10 wet-zone planning, C11a signature derivation, cache
storage, or scoring. Spec #4's drafting MUST preserve this fast-fail
property; if Spec #4 chooses a different placement (e.g., post-cache
validation), the trust contract weakens and a critique-eligible gap
exists.

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
- **Dwelling-level "exactly one master bedroom emitted globally" debug assertion** (MODERATE-4 from v0.8 critique walk): C9 itself cannot enforce this (per § 3.10 trust boundary). **Spec #4 (C11a Amendment v1.1) is expected to own this assertion** — likely as a post-C9-fan-out check inside the multi-floor cascade, asserting that across all per-floor C9 results, exactly one room has `is_master=True AND category=BEDROOM`, AND that the assertion fires BEFORE downstream scoring / caching / persistence (see § 3.10 lifecycle expectation). This forward-pointer is normative for Spec #4 drafting, but uses "is expected to own" rather than "WILL own" to preserve Spec #4's freedom to choose alternative enforcement structures (different placement, different assertion shape, additional invariants). If Spec #4 omits this assertion entirely, this amendment's trust-boundary contract (§ 3.10) is weakly-enforced and a critique-eligible gap exists in Spec #4.

---

## § 7 — Backlog items deferred

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-C9-A** (NEW) | Split `has_master_bedroom: bool` into two flags `has_master_bedroom: bool` + `has_master_bathroom: bool` to support dwellings where master bedroom and master bathroom are on different floors (non-en-suite) | When a real-world brief surfaces a non-en-suite master arrangement (rare in residential; might appear in luxury / commercial paths) | Open (post-v1) |
| **B-C9-B** (NEW) | Reconsider field name (`has_master_bedroom` → `has_master_suite`) when the en-suite coupling becomes either documented or contested | When B-C9-A is approved OR when a future amendment splits the master designation more finely | Open (post-v1) |
| **B-C9-C** (NEW from v0.8 critique walk MAJOR-4) | Replace dataclass-hash-based cache identity with explicit cache-signature serialization. Currently every nested-field addition (FloorRoomBrief, MultiFloorDwellingBrief, future selectors) forces C11A_CACHE_KEY_VERSION churn via dataclass hash propagation. An explicit serializer would let cache identity track a curated subset of fields rather than every hash-participating field | When cache-version churn becomes burdensome (heuristic: ≥3 amendments per release cycle requiring cache-version bumps) OR when persisted cache lands and migration cost dominates | Open (post-v1) |
| **B-C9-D** (from v0.8 critique walk MODERATE-3 / MINOR-3, **trigger re-tagged in v0.10 critique walk MODERATE-3**) | Replace positional master-room derivation (`is_master = (i == 0)`) with structural derivation (adjacency / suite-graph / accessibility / explicit-id). Currently bedroom #1 / bathroom #1 are master by position; this is fine for the current architecture but couples master semantics to room-iteration order | **Action triggers** (any one): (a) Spec #1's `master_bedroom_selector` widens beyond `"first_bedroom"` (B-MFDB-I trigger), (b) C5/C7/C8 amendment introduces topology-driven room ordering that breaks the "bedroom #1 is positionally first AND should-be-master" coincidence, (c) accessibility / elder-suite / non-en-suite real-world brief surfaces (also triggers B-C9-A). **Strategic note**: the "post-v1" label on this item understates its importance — every additional spec that references the positional convention deepens the unwind cost. Promote priority if any of (a/b/c) appears in active scope, even pre-v1 | Open (priority-promote on action trigger) |
| **B-C9-E** (NEW from v0.9 critique walk MAJOR-2) | Architectural / protocol tests that bind prose-authoritative semantic constraints to runtime verification. v0.9+ relies heavily on prose-level normative contracts (orchestration-context framing, hash participation, future-amendment constraints, en-suite coupling). Future maintainers may update runtime behaviour without updating prose, or vice versa, causing prose/runtime drift | When prose/runtime drift is observed in practice OR when a code review process flags it as a quality concern OR when the codebase adopts general architectural-test infrastructure | Open (post-v1) |
| **B-C9-F** (NEW from v0.10 critique walk MAJOR-2) | Physical-equivalence helper for `FloorRoomBrief` — a function `is_physically_equivalent(a, b)` that compares two briefs ignoring `has_master_bedroom` (and any future orchestration-context fields). Lets deduplication, topology canonicalization, and lineage clustering operate on physical-only equivalence without re-implementing the comparison or relying on the transitional `dataclasses.replace` idiom | When deduplication / topology canonicalization / lineage clustering needs physical-only equivalence (likely first surfaces in C11a v1.1 cache or in a future stress-fuzz refactor) | Open (post-v1) |
| **B-C9-G** (NEW from v0.10 critique walk MAJOR-4) | Architecture-governance convention for "directly-affects-runtime-behaviour" criterion (see § 3.9 worked examples). Currently a judgement-based rule; as the codebase accumulates more contextual-field proposals, the rule may need formalising as a written convention with precedent catalogue and example-based interpretation guidelines | When ≥3 orchestration-contextual-field proposals reach review, OR when an architecture-review process formalises | Open (post-v1) |

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

- **v0.11 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v0.12 PROPOSED.
- After LOCK: spec drafting proceeds to **Spec #3 (`MultiFloorWetZonePlannedCandidate`)**.
- Code work: deferred until all four specs LOCKED.
- **Convergence note**: third consecutive round with NO schema or runtime changes (v0.8 → v0.9 → v0.10 → v0.11). Spec #2 has fully converged at the runtime level; remaining critique surface (per v0.10 reviewer assessment) is "future architectural evolution pressure," not runtime correctness.

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
| **B-C9-C** | Explicit cache-signature serialization (replace dataclass-hash identity) | v0.9 critique | Cache-version churn becomes burdensome OR persisted cache migration cost | OUT-OF-SCOPE | M (post-v1) |
| **B-C9-D** | Structural master-room derivation (replace positional `(i == 0)`) | v0.9 critique; trigger re-tagged in v0.10 | Selector widening / topology-driven ordering / accessibility brief (any) | OUT-OF-SCOPE; **priority-promote on action trigger** | M |
| **B-C9-E** | Architectural / protocol tests for prose-authoritative semantic constraints | v0.10 critique (MAJOR-2) | Prose/runtime drift observed OR codebase adopts arch-test infra | OUT-OF-SCOPE | M (post-v1) |
| **B-C9-F** | Physical-equivalence helper (`is_physically_equivalent` ignoring orchestration-context fields) | v0.11 critique (MAJOR-2) | Dedup / topology canonicalization / lineage clustering needs physical-only equivalence | OUT-OF-SCOPE | S (post-v1) |
| **B-C9-G** | Architecture-governance convention for "directly-affects-runtime-behaviour" criterion | v0.11 critique (MAJOR-4) | ≥3 contextual-field proposals OR formalised arch review | OUT-OF-SCOPE | S (post-v1) |
| B-208 | Per-bathroom subtype expansion (pre-existing) | C9 v0.7 history | future C9 amendment | UNAFFECTED | M (post-v1) |

**Summary**: smallest of the four B-NEW-T3 specs. One field, two line-edits, one constant bump. Seven C9-amendment-specific backlog items (B-C9-A through G). Pre-existing C9 backlog unaffected.

---

**End of C9 Amendment v0.11 PROPOSED.**
