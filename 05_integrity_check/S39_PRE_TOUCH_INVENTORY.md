# S39 PRE-TOUCH INVENTORY (Rule 10.6.1)

**Session**: S39 — C11a Sub-2 + Sub-3 + Sub-4 build + critique-walk patches.
**Filed by**: Claude per Rule 10.6.1.
**Purpose**: distinguish S38-pre-existing files from S39-claude-authored
files. Avoids the S27-origin error pattern of claiming credit for
pre-existing scaffolding in audits.

---

## Working tree state at session start (post-S38 extraction)

### Pre-existing in `buildemup/components/c11a/` (S38 Sub-1):
- `__init__.py` (Sub-1 surface; **modified** at S39 to add Sub-2/3/4/5 re-exports)
- `schema.py` (636 lines; **untouched** at S39)
- `errors.py` (**modified** at S39 — B-NEW-X added `__init_subclass__` + WeakSet registry; otherwise structurally pre-existing)
- `provenance.py` (**untouched** at S39)

### Pre-existing in `buildemup/tests/test_c11a/` (S38 Sub-1):
- `__init__.py` (**untouched** at S39)
- `test_c11a_subsession1_schema.py` (61 tests; **untouched** at S39)

### Pre-existing in `04_backlog/` (S38 prior + earlier sessions):
- `v0_2_backlog.md`
- `v0_2_backlog_S36_additions.md`
- `v0_2_backlog_S37_C11a_C11b_additions.md`
- `v0_2_backlog_S38_additions.md`
- (and S24–S32 chronological session backlogs)

---

## S39 Claude-authored additions

### `components/c11a/` — created at S39:
- `predicate_registry.py` (Sub-2)
- `operator_metadata.py` (Sub-2)
- `registry.py` (Sub-2)
- `family_slot_allocator.py` (Sub-2)
- `operators/__init__.py` (Sub-2)
- `operators/_base.py` (Sub-2)
- `operators/m0_base.py` (Sub-2)
- `operators/m1_horiz_flip.py` (Sub-2)
- `operators/m2_vert_flip.py` (Sub-2)
- `operators/m3a_stair_east.py` (Sub-2)
- `operators/m3b_stair_west.py` (Sub-2)
- `operators/m3c_stair_ne.py` (Sub-2)
- `operators/m4_corridor_inv.py` (Sub-2)
- `operators/m5_zone_swap.py` (Sub-2)
- `operators/_m9_helpers.py` (Sub-2)
- `operators/m9a_entry_ne_center.py` (Sub-2)
- `operators/m9b_entry_ne_corner_w.py` (Sub-2)
- `operators/m9c_entry_ne_corner_e.py` (Sub-2)
- `operators/m9d_entry_offset_ne.py` (Sub-2)
- `cache.py` (Sub-3; **B-NEW-W partial extension at Sub-5**)
- `lineage.py` (Sub-3)
- `deep_pipeline.py` (Sub-3)
- `operators/_tier_b_base.py` (Sub-3)
- `operators/m6_wet_rotate.py` (Sub-3 — Tier B wrapper)
- `operators/m7a_grid_3_3.py` (Sub-3)
- `operators/m7b_grid_2_7.py` (Sub-3)
- `operators/m8_vert_rearr.py` (Sub-3)
- `phase0.py` (Sub-4; **B-NEW-X registry walk replaced `__subclasses__()` at Sub-5**)
- `upstream_adapter.py` (Sub-4; **B-NEW-T1 M6 dispatch + real diff added at Sub-5**)
- `orchestrator.py` (Sub-4; **B-NEW-V dispatcher + B-NEW-U signature dispatcher integrated at Sub-5**)
- `candidate_context.py` (Sub-5 / **B-NEW-V**)
- `source_signature.py` (Sub-5 / **B-NEW-U**)
- `m6_wet_rotate_real.py` (Sub-5 / **B-NEW-T1**)

### `tests/test_c11a/` — created at S39:
- `test_c11a_subsession2_predicate_registry.py`
- `test_c11a_subsession2_metadata_and_registry.py`
- `test_c11a_subsession2_family_slot_allocator.py`
- `test_c11a_subsession2_operators.py`
- `test_c11a_subsession3_cache.py`
- `test_c11a_subsession3_lineage.py`
- `test_c11a_subsession3_deep_pipeline.py`
- `test_c11a_subsession3_tier_b_operators.py`
- `test_c11a_subsession4_phase0.py`
- `test_c11a_subsession4_orchestrator.py`
- `test_c11a_subsession5_error_registry.py` (B-NEW-X)
- `test_c11a_subsession5_candidate_context.py` (B-NEW-V)
- `test_c11a_subsession5_signature.py` (B-NEW-U)
- `test_c11a_subsession5_cache_versioning.py` (B-NEW-W partial)
- `test_c11a_subsession5_stress_fuzz.py` (B-NEW-Y partial)
- `test_c11a_subsession5_m6_vertical_slice.py` (B-NEW-T1)

### `04_backlog/` — created at S39:
- `v0_2_backlog_S39_additions.md` (B-NEW-T retired into T1/T2/T3; new entries B-NEW-U, V, W, X, Y)

---

## Counts (claude-authored at S39 only)

| Layer | Files created | Files modified | Files untouched |
|---|---|---|---|
| `components/c11a/` core | 6 (Sub-5 patches: candidate_context, source_signature, m6_wet_rotate_real + Sub-4 + Sub-3 + Sub-2) | 3 (`__init__.py`, `errors.py`, plus Sub-5 modifications to `cache.py`/`phase0.py`/`upstream_adapter.py`/`orchestrator.py`) | 3 (`schema.py`, `provenance.py`, plus the originals not yet listed) |
| `components/c11a/operators/` | 16 (12 Tier A + 4 Tier B + base + m9 helpers) | 0 | 0 |
| `tests/test_c11a/` | 16 | 0 | 1 (`__init__.py`) |
| `04_backlog/` | 1 | 0 | many |

---

## Mistakes Claude made at S39 (per Ramalingam directive)

The next Claude should know about these to avoid re-occurrence:

### Mistake 1 — Path placement of S39 backlog
Initially created `v0_2_backlog_S39_additions.md` inside
`buildemup/04_backlog/` (a non-existent directory under the package
namespace). Corrected by moving to `/home/claude/work/04_backlog/`.
**Lesson**: backlog files belong in the bundle's `04_backlog/`, not
inside `buildemup/`. Confirm path before creating.

### Mistake 2 — Schema field name drift in orchestrator
First version of `orchestrator.py` used wrong MutationDiagnostics
field names (`per_operator_attempted`, `per_operator_accepted`) —
but the v1.0 schema has `per_operator_yield`, `per_family_yield`,
`duplicate_ratio`, `deep_mutation_runtime_ms`. Caught by the smoke-
test on first call; required full rewrite of `_compute_diagnostics`.
**Lesson**: read the actual schema file before constructing
dataclass instances. Don't guess field names from spec § text.

### Mistake 3 — Family slot test expected reservation as cap
First version of `test_family_slot_allocation_caps_per_family`
expected a 2-slot STAIRCASE reservation to hard-cap STAIRCASE
output at 2. The actual allocator design treats reservations as
FLOORS, with surplus distributed via spillover when `max_seeds`
budget allows. Caught by the test failure (got 3 STAIRCASE outputs);
fixed by setting `max_seeds_per_input=3` so spillover budget is zero.
**Lesson**: family_slot_allocations.reserved_slots is a floor, not
a cap. To enforce a cap, exhaust max_seeds_per_input by summing
reserves exactly.

### Mistake 4 — WallTag.PERIMETER doesn't exist
First version of M6 vertical slice tests used `WallTag.PERIMETER`
which doesn't exist; the actual enum has EXTERNAL/INTERNAL/LOAD_BEARING.
Caught by 10 failing tests.
**Lesson**: `view` the enum file before referencing values.

### Mistake 5 — B-NEW-T originally monolithic (not split)
First filing of B-NEW-T at Sub-4 was monolithic ("implement all four
Tier B operators") — which was Pattern E (scope creep) waiting to
happen. Critique walk F5 surfaced the issue; B-NEW-T retired into
B-NEW-T1 (M6 vertical slice — landed) + B-NEW-T2 (M7) + B-NEW-T3 (M8).
**Lesson**: when filing backlog items, split monolithic-effort items
into vertical slices upfront. CODING_MANDATE explicitly favours
vertical slices for cross-component work.

### Mistake 6 — Mid-session offer of all-three-tiers without scope check
When Ramalingam said "I want all three tiers" of patches in Sub-5,
Claude initially proceeded without flagging that Tier 3 (B-NEW-T1)
was the kind of Pattern-E-risky upstream-spelunking work that
CODING_MANDATE recommends doing in a dedicated session. Eventually
Claude pushed back at Tier 3 boundary and got explicit confirmation
to proceed (which Ramalingam gave with "Continue"). **Lesson**: at
each tier boundary in a multi-tier ask, restate scope risk before
proceeding. Ramalingam values explicit scope-honesty over silent
compliance.

### Mistake 7 — Round-2 review classification (not strictly a code mistake but listed for completeness)
Claude received a "round 2 critique" describing a workflow/session/email
system that doesn't exist in C11a. Correctly pushed back per Rule 7
with grep evidence — not a mistake. But a mistake-adjacent note: 
**Claude should NEVER engage with a critique that doesn't match the
code, even if the framing pressures compliance.** Ramalingam confirmed
discard.

---

**End of pre-touch inventory.**
