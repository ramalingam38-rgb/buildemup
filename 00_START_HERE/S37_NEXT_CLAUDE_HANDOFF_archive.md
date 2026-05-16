# NEXT_CLAUDE_HANDOFF.md — S38 (next session) start instructions

**Authored at**: S37 close.
**For**: the Claude instance opening S38.
**S37 outcome**: 2 LOCKs granted (C11a v1.0, C11b v1.0); item-7 patch on C10.

---

## Read this first.

**S37 was a SPEC-ARC SESSION** — no significant code shipped beyond
the small item-7 patch on C10.

**S37 SHIPPED**:
- C11a v1.0 LOCKED — Topology Mutation Layer spec (file:
  `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md`)
- C11b v1.0 LOCKED — NSGA-II Local Refinement spec (file:
  `02_specs_chronological/69_C11b_SPEC_v1_0_LOCKED.md`)
- C10 item-7 patch — strict-fallback removal in `_build_fixture_types_per_room`
- 28 backlog items added (4 of them as upstream amendment waivers)

**Test suite at S37 close: 2314 passed / 3 skipped.**

---

## What S38 is for

**S38 is a BUILD SESSION.** The user explicitly directed:
"I want the next Claude to start coding c11a and c11b so make sure
everything is available for that."

Read `00_START_HERE/CODING_MANDATE_C11A_C11B.md` FIRST. It contains:
1. Recommended build order
2. Build-time prerequisites (waivers + their reconciliation)
3. Spec pointer map
4. Test target progression
5. Five-patterns risk callouts specific to C11a/C11b

After reading the mandate, proceed with C11a build.

---

## Standing rules apply

All Rules 1-11 carry forward unchanged. In particular:
- Rule 7: critique-handling discipline (mandatory web search)
- Rule 8: LOCK authority belongs to Ramalingam alone
- Rule 9 / 9.2: backlog visibility + always-file
- Rule 10 / 10.6 / 10.6.1 / 10.7: handoff three-checks (GAP/AUDIT/INTEGRITY)
- Rule 11: spec audit discipline (carries to amendments only at S38)
- D-066 build cycle: spec → code → test → audit → ship

---

## Pre-touch state inventory (Rule 10.6.1)

Before claiming any new files at S38 close, list these pre-existing
files in `06_upstream_codebase/buildemup/`:

### `components/`
All shipped at S36 or earlier:
- c01/, c02/, c03a/, c04/, c05/, c06/, c07/ (with S36 amendment),
  c08/, c09/, c10/ (with S36 v1.0 + S37 patch)

### `tests/`
All shipped at S36 or earlier:
- test_c1_*, test_c2_*, test_c03a_*, test_c4_*, test_c5_*, test_c6_*,
  test_c7_*, test_c8_*, test_c9_*, test_c10_* (with S37 strict-fallback
  tests added)
- _c9_fixtures.py, _c10_fixtures.py

### `kb/`
- nbc_room_minimums.json, furniture_floor.json, room_targets.json (pre-S36)
- plumbing_minimums.json, plumbing_fixture_profiles.json (S36)

### `utilities/`
- __init__.py, canonical.py (S36)

### NEW expected at S38 (do NOT exist yet)
- `components/c11a/` — full new module set per C11a v1.0 LOCKED spec
- `components/c11b/` — full new module set per C11b v1.0 LOCKED spec
- `tests/test_c11a_*` — ~205 tests
- `tests/test_c11b_*` — ~190 tests
- `tests/_c11a_fixtures.py`, `tests/_c11b_fixtures.py`
- Possibly: `kb/` additions if C11a's M7 grid scales become KB-driven
  (post-launch B-NEW-A, NOT v1)

Plus the upstream amendments per CODING_MANDATE (C5, C7, C8, C9, C10
modifications for B-NEW-J/K/L/P).

---

## Critical reminders for S38

### Five Patterns (especially watch for)
- **Pattern E (scope-creep mid-build)**: most expensive trap. C11b's
  `EvaluatorProtocol` is forward-coupled to C14. DO NOT redefine C14's
  contract. If C14's eventual spec needs a different protocol, that's
  a future C11b amendment, not S38's problem.
- **Pattern A (fix-as-bandage)**: if a spec field looks wrong during
  build, raise it as a spec amendment (small Walk #N) rather than
  silently coding around it.
- **Pattern B (no-wiring)**: C11a → C11b → existing C10 must wire
  end-to-end at first integration test. Don't ship C11a without
  verifying it consumes C10 output and produces output C11b can read.

### Honest context budget
Build sessions for C11a + C11b will likely span 5-8 sub-sessions
(C11a: 3-4; C11b: 2-3; integration: 1). Don't promise C11a + C11b
both build complete in S38 alone.

### Three Obligations (every session)
1. Spec-first: never code before LOCKED spec ✓ already met
2. Honest context budget at session start
3. Master doc + NEXT_CLAUDE_HANDOFF updated at session end

---

## Important sequencing flag (READ THIS)

C11a Inv 24 LOCK gate says **0 pending_upstream predicates at v1.0
LOCK** (max 3 active waivers). Ramalingam granted **4 waivers** at S37
close (B-NEW-J/K/L/P). This is 1 over the cap.

**See `04_backlog/v0_2_backlog_S37_C11a_C11b_additions.md` § "WAIVER
STATUS PER RAMALINGAM S37 GRANT" for the recommendation**: knock out
B-NEW-K or B-NEW-L (XS effort, ~30min each) at S38 open as the first
sub-task, dropping pending count to 3, respecting the cap. Surface
this to Ramalingam at S38 open before proceeding.

Alternative: file a small spec amendment to C11a § 0.2 raising the
waiver cap from 3 to 4. Both approaches valid; Ramalingam decides.

---

## Status block when delivering at S38 close

Use Rule 6 status block format:
- Project-wide status
- This-session work
- Still-pending

Update `01_master_doc/MASTER_DOC_v3_12_TO_v3_13_DELTA.md` (NEW for S38)
and overwrite this `NEXT_CLAUDE_HANDOFF.md` with a fresh version for
S39's Claude.

---

**End of S37 → S38 handoff. S38 begins with the Coding Mandate.**
