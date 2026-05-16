# NEXT_CLAUDE_HANDOFF.md

**Read this first. Do not skim.**

You are the Claude opening **S39**. Your immediate-next task is to
**continue C11a v1.0 build at Sub-session 2** per CODING_MANDATE.
Sub-session 1 is shipped (schema + errors + provenance, 61 tests, all
green). Four upstream amendments — B-NEW-P / K / L / J — are LOCKED
v1.0 by Ramalingam at S38. The Inv 24 LOCK gate passes (zero pending
upstream predicates, zero active waivers).

---

## § 1 — What S38 shipped

### Upstream amendments (Path α — full upstream design, per Ramalingam)

| Amendment | Status | Tests | Files modified |
|---|---|---|---|
| **B-NEW-P** v1.0 LOCKED | ✅ | 65 | `c08/errors.py`, `c09/errors.py`, `c10/errors.py` (severity_tier ClassVar) |
| **B-NEW-K** v1.0 LOCKED **(includes K-4 patch)** | ✅ | 27 | `c07/grid_generator.py` (Staircase + W9 + landing-scales-with-width) |
| **B-NEW-L** v1.0 LOCKED | ✅ | 21 | `c08/validator.py` (Inv 21 entry approach) |
| **B-NEW-J** v1.0 LOCKED **(B-NEW-J-override at launch-complement)** | ✅ | 22 | `c05/zone_bands.py` (privacy zoning) |

### C11a Sub-session 1 (CODING_MANDATE Step 2 first chunk)

| Module | Lines | Purpose |
|---|---|---|
| `components/c11a/schema.py` | ~470 | All enums (16 operators / 2 tiers / 9 families / 20 DeltaKeys / etc), frozen dataclasses, registries (`UPSTREAM_PURITY_REGISTRY`, `WAIVER_REGISTRY`), config |
| `components/c11a/errors.py` | ~190 | Full error hierarchy with `severity_tier` ClassVars |
| `components/c11a/provenance.py` | ~120 | `TopologyMutationProvenance` + `MutatedTopologyCandidate` with v1-invariant `__post_init__` guards |
| `components/c11a/__init__.py` | ~80 | 33 public names re-exported |
| `tests/test_c11a/test_c11a_subsession1_schema.py` | ~530 | **61 tests** |

### Test count progression

| Stage | Count |
|---|---|
| S37 close baseline | 2290 / 2 skipped |
| After B-NEW-P + K + L + J | 2420 (+130) |
| After K-4 patch | 2425 (+5) |
| **After C11a Sub-session 1** | **2486 / 2 skipped** |

---

## § 2 — Your immediate next step (S39 Sub-session 2)

Per **CODING_MANDATE_C11A_C11B.md** Step 2 decomposition:

> Sub-session 2: Tier A operators (M0/M1/M2/M3/M4/M5/M9 — shallow, no
> upstream re-run); per-family slot allocation; basic test coverage

### Concrete deliverables for Sub-session 2

1. **`components/c11a/operators/`** package with:
   - `m0_base.py` — identity operator (always-valid base)
   - `m1_horiz_flip.py` — horizontal flip (Tier A SHALLOW)
   - `m2_vert_flip.py` — vertical flip (Tier A SHALLOW)
   - `m3a_stair_east.py`, `m3b_stair_west.py`, `m3c_stair_ne.py`
     — staircase repositioning. Calls C7's `validate_staircase_clearance`
     predicate (B-NEW-K v1.0 LOCKED) before accepting.
   - `m4_corridor_inv.py` — corridor inversion (TRANSFORMS_FAMILY)
   - `m5_zone_swap.py` — public/private zone swap. Calls C5's
     `validate_privacy_zoning` predicate (B-NEW-J v1.0 LOCKED).
   - `m9a/b/c/d_entry_*.py` — entry repositioning. Calls C8's
     `validate_entry_approach` predicate (B-NEW-L v1.0 LOCKED).
2. **`components/c11a/operator_metadata.py`** — `OPERATOR_METADATA` dict
   with concrete entries per § 2.2 v0.5 table:
   - Each entry: `MutationOperatorMetadata(operator, tier, family,
     family_transition_policy, requires_multi_floor, requires_grid_regen,
     expected_delta_schema, cache_relevant_config_fields)`
   - The per-operator delta schemas per spec § 2.2 v0.5 table (M1
     expects `{GEO_ROOM_POSITION_X}`, allows `{ADJ_EDGES_ORIENTATION}`,
     forbids `{GEO_ROOM_AREA, META_FIXTURE_TYPES}`, etc.)
3. **`components/c11a/registry.py`** — `validate_operator_registry()`
   per § 2.8 with **Inv 28** enforcement (every key in
   `OperatorExpectedDeltaSchema` MUST be a `DeltaKey` enum value;
   string literals raise `OperatorRegistryError` at startup).
4. **`components/c11a/predicate_registry.py`** — Tier A
   `MutationViabilityPredicate` registry binding upstream predicates:
   - `C7.staircase_clearance` → `validate_staircase_clearance`
   - `C8.entry_approach` → `validate_entry_approach`
   - `C5.privacy_zoning` → `validate_privacy_zoning`
   - `C9.Inv_4`, `C10.Inv_3`, etc. — see C11a § 3.4 predicate matrix
5. **`components/c11a/family_slot_allocator.py`** — per-family slot
   allocation per § 3 Phase 1 (deterministic, lex-ASC family order,
   spillover to surplus families).
6. **Tests** — target ~80 tests for Sub-session 2:
   - ~32 per-operator (per § 6 v0.4 carry: 3 happy + 1 invalidation
     for M3 family, 4+1 for M9, 1 each for M0/M1/M2/M4/M5)
   - ~10 family slot allocation
   - ~10 registry validation (Inv 28, missing-operator, conflicting-tier)
   - ~10 predicate registry (Tier A bindings, pending_upstream=False
     for all v1.0 predicates per Inv 24 satisfied)
   - ~18 misc (e.g., operator-metadata table coverage,
     `_OPERATOR_FAMILY_POLICY` consistency with `OPERATOR_METADATA`)

### What Sub-session 2 does NOT include

- **NO Tier B (DeepMutationPipeline)** — that's Sub-session 3.
- **NO `mutate_topologies()` orchestration** — that's Sub-session 4.
- **NO replay/quarantine fingerprint** — that's Sub-session 4.
- **NO C11b** — that's Step 3.

---

## § 3 — Standing protocol obligations

These apply to **every session, including discussion-only**. Read
these in `RULES_RAMALINGAM_FORMALIZED.md` and
`THREE_OBLIGATIONS_AND_PATTERNS.md` (in this directory). Quick
reference:

1. **Spec-first discipline** (Rule 7): never code before a LOCKED spec.
   For Sub-session 2 the LOCKED spec is C11a v1.0
   (`02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md`); you do NOT
   need a fresh spec round.
2. **Honest context budget** declared at session start. D-066 says
   keep going until Ramalingam says "stop"/"hand off"; do NOT stop
   unilaterally on context.
3. **Master doc + NEXT_CLAUDE_HANDOFF.md updated at every session
   end.** This document is **self-perpetuating**: at S39 close, you
   will produce the v14 handoff with a fresh `NEXT_CLAUDE_HANDOFF.md`
   for S40. Mirror this document's structure.
4. **Rule 8 — LOCK authority is Ramalingam's alone.** Never
   self-declare LOCK. Always present specs as "vN PROPOSED. PENDING
   Ramalingam LOCK adjudication." Wait for explicit "lock it".
5. **Rule 9.2 — file backlog items immediately** when a critique walk
   surfaces VALID-BUT-BACKLOG; don't ask permission.
6. **Rule 10.6 — three-check protocol** before any handoff zip:
   GAP CHECK + AUDIT CHECK + INTEGRITY CHECK in `05_integrity_check/`.
7. **Rule 10.6.1 — pre-touch state inventory** before claiming credit
   for created/modified files.

---

## § 4 — Critical state at S38 close (do not redo)

### Inv 24 LOCK gate state
```
pending_upstream_predicate_count = 0
len(active_waivers) = 0
Both clauses pass.
```

### `WAIVER_REGISTRY`
Empty tuple `()` — confirmed at v1.0 LOCK time. Defined in
`components/c11a/schema.py`. Per Inv 24, this is **required** to be
empty (or ≤3) at LOCK; any future amendment that adds a waiver
re-adjudicates the gate.

### `UPSTREAM_PURITY_REGISTRY`
Three attestations:
- C7 `GridGenerator.generate` → `pure`
- C9 `size_rooms` → `pure`
- C10 `plan_wet_zones` → `lazy_init_once`

### B-NEW-J-override is launch-complement, not deferred-indefinitely
Per S38 Walks #2 + #4: B-NEW-J's privacy_zoning predicate fires
unconditionally because no user-override mechanism exists in C1
brief schema. **B-NEW-J-override** must ship at the same release
window as B-NEW-J's production enforcement (when C11a v1 ships in
production). Owner: C1 (brief schema) + C11a (registry consultation).
When implemented, MUST follow B-meta-rule-taxonomy framework — no
one-off override mechanism.

### B-NEW-K landing depth uses K-4 patch
W9-b is `landing_depth_m >= max(width_m, MIN_STAIRCASE_LANDING_DEPTH_M)`
NOT a fixed 0.9m floor. Patched in S38 after triple corroboration
across Walks #1-#3. NBC 2016 verified via secondary sources;
B-150-equiv pre-launch verification still pending.

---

## § 5 — Where to find things

| You need... | Look in... |
|---|---|
| What S38 changed | `01_master_doc/MASTER_DOC_v3_12_TO_v3_13_DELTA.md` |
| C11a v1.0 LOCKED spec | `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md` |
| The 4 LOCKED upstream amendments | `02_specs_chronological/70-73_*_v1_0_LOCKED.md` |
| The 4 walk responses | `02_specs_chronological/74-77_S38_Walk_*.md` |
| Operator enum + DeltaKey + frozen schemas | `06_upstream_codebase/buildemup/components/c11a/schema.py` |
| C11a errors with severity_tier ClassVars | `06_upstream_codebase/buildemup/components/c11a/errors.py` |
| Sub-session 1 tests | `06_upstream_codebase/buildemup/tests/test_c11a/` |
| Backlog (51 items + new S38 items) | `04_backlog/v0_2_backlog_S38_additions.md` |
| Three-check results | `05_integrity_check/S38_INTEGRITY_CHECK.md` |
| CODING_MANDATE | (carried from v12) `00_START_HERE/CODING_MANDATE_C11A_C11B.md` |

---

## § 6 — Pre-flight checklist for the next Claude

Before writing any code at S39:

- [ ] Read this document fully.
- [ ] Read `CODING_MANDATE_C11A_C11B.md` Step 2 ("C11a v1.0 build")
      and the Spec pointer map.
- [ ] Read `RULES_RAMALINGAM_FORMALIZED.md` (full) and
      `THREE_OBLIGATIONS_AND_PATTERNS.md` (full).
- [ ] Read C11a v1.0 LOCKED spec end-to-end (especially § 2 Contract,
      § 3 Behaviour Phase 1, § 3.4 Tier A predicate orchestration).
- [ ] Run pre-touch state inventory (Rule 10.6.1) on the directories
      Sub-session 2 will touch:
      `06_upstream_codebase/buildemup/components/c11a/` (already has
      `schema.py`, `errors.py`, `provenance.py`, `__init__.py` — DO
      NOT claim authorship of these in your S39 GAP/AUDIT CHECK).
- [ ] Verify the test baseline: `cd 06_upstream_codebase &&
      python3 -m pytest buildemup/tests/ -q --ignore=buildemup/tests/e2e
      --tb=no` should report **2486 passed / 2 skipped**.
- [ ] Begin Sub-session 2 per § 2 above.

---

## § 7 — End-of-session handoff protocol (Rule 10.7)

When Ramalingam says "hand off" at S39 close, your **first response**
is the status block + three-check **plan**. No bundle assembly until
Ramalingam confirms or corrects. Only then assemble, run checks,
deliver zip — with status block carrying results at top of delivery
message.

The bundle directory layout is fixed (10 dirs as listed in § 5
above). Number files chronologically across the project (don't reset
per session).

---

**End of NEXT_CLAUDE_HANDOFF.md (S38 → S39). Authored S38, May 9 2026.**
