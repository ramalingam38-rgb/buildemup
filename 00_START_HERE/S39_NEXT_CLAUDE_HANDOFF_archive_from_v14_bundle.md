# NEXT CLAUDE HANDOFF — Session 40 (B-NEW-T2 priority)

**For**: the next Claude.
**From**: Claude at end of S39.
**Status**: 2731 passed / 2 skipped / 0 regressions. C11a alone = 306 tests.
**Your priority**: **B-NEW-T2 (M7a/M7b grid scale real upstream wiring)**.

This handoff is structured so you can start coding immediately. Read
sections 1-4 in order; you should NOT need to ask Ramalingam any
clarifying questions before starting.

---

## 1. CONTEXT (one-paragraph)

C11a's job is per-batch deterministic mutation of wet-zoned topology
candidates. It's stateless, single-threaded (Inv 30), no I/O. Sub-1
through Sub-5 + critique-walk patches all shipped at S38/S39. **One
Tier B operator (M6 wet-rotate) is now wired against real C10
infrastructure via post-process rotation (B-NEW-T1, S39).** Your
priority is to wire **M7a (grid scale 3.3m bays) and M7b (grid scale
2.7m bays)** against the real C7→C8→C9→C10 upstream cascade. This is
the largest Tier B wiring effort.

---

## 2. THE FIRST THING YOU MUST DO

Before writing any code:

1. `view /mnt/skills/public/<applicable>/SKILL.md` for any skills the
   environment surfaces (per Claude's standing tool-discovery rule).
   Then continue:

2. **Inventory pre-touch state** per Rule 10.6.1. The C11a code at
   `buildemup/components/c11a/` is the working tree from S39 close.
   You will TOUCH `upstream_adapter.py` (extending M7 dispatch),
   ADD `m7_grid_scale_real.py`, and possibly TOUCH C7
   (`grid_generator.py`) for a small amendment. List these in your
   pre-touch inventory before changing anything.

3. **Read the relevant spec sections** before coding:
   - `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md` § 2.5 (DeltaKey vocabulary), § 2.2 (operator metadata for M7), § 3.5 (DeepMutationPipeline contract)
   - `04_backlog/v0_2_backlog_S39_additions.md` — full B-NEW-T2 description with cascade hints

4. **Run tests** to confirm green starting state:
   ```
   cd /home/claude/work
   python3 -m pytest buildemup/tests/test_c11a/ -q
   ```
   Should show 306 passed.

---

## 3. THE B-NEW-T2 IMPLEMENTATION SPECIFICATION

### 3.1 What M7a / M7b do (semantic)

- **M7a_GRID_3_3**: regenerate the candidate with grid bay sizes set to **3.3m × 3.3m**.
- **M7b_GRID_2_7**: regenerate with bay sizes **2.7m × 2.7m**.

These are TRANSFORMS_FAMILY operators (they change `output_family_id`
to `transformed_from_<source>`) per § 2.2 metadata.

### 3.2 The full cascade you must wire

```
M7a/b TierBInputMutation
  → C7.GridGenerator().generate(envelope_w, envelope_d, target_bay_x_m=X, target_bay_y_m=X)
  → new Grid
  → C8.design_corridors([oriented_candidate], new_grid, plot_analysis)
  → CorridorDesignedCandidate
  → C9.size_rooms([cdc], floor_room_brief, new_grid, plot_analysis)
  → RoomSizedCandidate
  → C10.plan_wet_zones([rsc], floor_room_brief, new_grid, plot_analysis)
  → WetZonePlannedCandidate (this is the Tier B output)
```

### 3.3 The C7 amendment you need to make

**Critical issue**: `c07.grid_generator.GridGenerator.generate()` has
signature `generate(self, envelope_width_m, envelope_depth_m) -> Grid`
— there is NO `target_bay_x_m` parameter. Bay size is auto-selected
via `_select_bay_size()` (closest to 3.3m sweet spot).

**Your amendment**: extend the signature to:
```python
def generate(
    self,
    envelope_width_m: float,
    envelope_depth_m: float,
    *,
    target_bay_x_m: float | None = None,
    target_bay_y_m: float | None = None,
) -> Grid:
```

When `target_bay_x_m` is provided AND in `PREFERRED_BAY_SIZES_M`
(`[2.7, 3.0, 3.3, 3.6, 4.0, 4.5, 5.0]`, defined at
`buildemup/kb/rcc_design_rules.py:43`), skip `_select_bay_size()` and
use the provided value directly. Same for `target_bay_y_m`.

This is a **NON-BREAKING C7 amendment** — existing callers that pass
two positional args still get auto-select. File this amendment in the
backlog as **C7 amendment v0.9** (extending v0.8 LOCKED).

**File the amendment under § 12** as a v1.0+ C7 amendment per Rule 9
backlog visibility. Its trigger is "B-NEW-T2 wiring." Before locking
the amendment, run a Rule 8 check with Ramalingam — DO NOT self-LOCK.

### 3.4 The new file you must create

Create `buildemup/components/c11a/m7_grid_scale_real.py` mirroring
the structure of `m6_wet_rotate_real.py` (which you have as reference).
Public API:

```python
def regenerate_for_m7(
    source: WetZonePlannedCandidate,
    grid_orig: Grid,
    floor_room_brief: FloorRoomBrief,
    plot_analysis: PlotAnalysis,
    target_bay_m: float,   # 3.3 for M7a, 2.7 for M7b
) -> WetZonePlannedCandidate:
    """B-NEW-T2: regenerate the candidate with new grid bay size.
    Cascade: C7 → C8 → C9 → C10. Raises M7NotViableError on cascade
    failure (per_candidate severity)."""
```

```python
class M7NotViableError(PerCandidateError):
    """Raised when M7 cascade fails (e.g., new grid too small for
    rooms, corridor design fails, or wet-zone plan infeasible)."""
    severity_tier = "per_candidate"
```

### 3.5 RealUpstreamRegenerator dispatch

In `upstream_adapter.py` `regenerate()`, replace the M7a/b
NotImplementedError block with dispatch into `regenerate_for_m7`:

```python
if operator in (MutationOperator.M7A_GRID_3_3, MutationOperator.M7B_GRID_2_7):
    from buildemup.components.c10.schema import WetZonePlannedCandidate
    from buildemup.components.c11a.m7_grid_scale_real import (
        M7NotViableError, regenerate_for_m7,
    )
    if not isinstance(source, WetZonePlannedCandidate):
        raise NotImplementedError(...)  # synthetic-source guard
    target_bay = 3.3 if operator == MutationOperator.M7A_GRID_3_3 else 2.7
    try:
        return regenerate_for_m7(
            source, self._grid, self._floor_room_brief,
            self._plot_analysis, target_bay,
        )
    except M7NotViableError:
        raise
```

### 3.6 compute_delta extension

Add an M7 branch to `_diff_m7_grid_scale` next to `_diff_m6_wet_rotate`
in `upstream_adapter.py`. Compare:
- `GEO_GRID_BAY_SIZE`: source.grid.bay_x_m vs regen.grid.bay_x_m differ → set
- `GEO_ROOM_AREA`: any room area differs (likely after re-tile)
- `PLUMB_RISER_GROUPS`: rebuilt under new wall positions
- Forbidden keys M7 must NOT produce: `META_ROOM_COUNT`,
  `META_FIXTURE_TYPES` (Inv 17 atomicity)

Use the metadata table for expected/forbidden:
```python
metadata = OPERATOR_METADATA[MutationOperator.M7A_GRID_3_3]
expected = metadata.expected_delta_schema.expected
forbidden = metadata.expected_delta_schema.forbidden
```

If forbidden keys appear → that's a lineage-classify REJECT, NOT a
diff issue. The diff returns the actual deltas; lineage classifier
handles forbidden enforcement.

---

## 4. TESTING STRATEGY

### 4.1 What's already there (use as reference)

- `tests_c11a/test_c11a_subsession5_m6_vertical_slice.py` — 17 tests.
  Mirror this structure for M7. Tests synthetic-but-real-shape data.

### 4.2 What you must add

Create `tests_c11a/test_c11a_subsession6_m7_vertical_slice.py` with at
minimum:

1. **Cascade-success test**: feed real `WetZonePlannedCandidate`
   constructed via the C5→C6→C7→C8→C9→C10 chain at default bay sizes;
   M7a regenerates → result is a valid `WetZonePlannedCandidate` with
   `grid.bay_x_m == 3.3`, `grid.bay_y_m == 3.3`.

2. **Cascade-failure test**: feed a small-envelope candidate where
   `2.7m bays` would result in an envelope smaller than the room
   requirements; M7b should raise `M7NotViableError`.

3. **Inv 17 atomicity test**: M7 regeneration MUST NOT change
   `META_ROOM_COUNT` (room count stays equal). This is the forbidden
   delta. If C9.size_rooms drops a room because new grid can't fit it,
   that's a test-passing scenario where M7 is per-candidate-rejected
   (not an "M7 changed room count" — it's "M7 was infeasible").

4. **DeltaKey diff test**: regenerate, call `_diff_m7_grid_scale` —
   confirm `GEO_GRID_BAY_SIZE` is in result.

5. **RealUpstreamRegenerator dispatch test**: confirm M7a + M7b reach
   `regenerate_for_m7`; M8 still raises NotImplementedError per B-NEW-T3.

6. **C7 amendment regression**: confirm `GridGenerator.generate(w, d)`
   without target args still auto-selects (existing C7 tests must
   still pass).

### 4.3 Constructing real WetZonePlannedCandidate for tests

This is the hardest part of B-NEW-T2 — building a real test fixture.
You have two options:

- **Option A (recommended)**: piggyback on existing C10 tests at
  `buildemup/tests/test_c10/`. They build real `WetZonePlannedCandidate`
  fixtures via the full upstream chain. Import their helpers or
  duplicate the construction.
- **Option B**: build a minimal fixture in your test file by calling
  the real entry points (`c5.derive_topologies()` →
  `c6.orient_candidates()` → `c7.GridGenerator().generate()` →
  `c8.design_corridors()` → `c9.size_rooms()` → `c10.plan_wet_zones()`).
  More work but isolated.

Look at `test_c10` first. The pattern is well-established.

### 4.4 Standard sanity check

After every meaningful change:
```
cd /home/claude/work
python3 -m pytest buildemup/tests/test_c11a/ -q --tb=short
```
Should show 306 + N passed (N = your new tests).

Then full project:
```
python3 -m pytest buildemup/tests/ --ignore=buildemup/tests/e2e -q --tb=no
```
Must show **2731 + N passed, 2 skipped**. **ZERO regressions** is the
contract.

---

## 5. WHAT TO WATCH FOR (mistakes to avoid)

Per Ramalingam's directive to capture S39 mistakes (see
`05_integrity_check/S39_PRE_TOUCH_INVENTORY.md` § "Mistakes Claude
made at S39"):

1. **Don't guess schema field names** from spec § text — `view` the
   actual schema file and copy field names exactly. (S39 mistake #2:
   Claude used `per_operator_attempted` when actual field is
   `per_operator_yield`.)

2. **family_slot_allocations.reserved_slots is a FLOOR, not a CAP.**
   To enforce a cap, exhaust max_seeds_per_input by summing reserves
   exactly. (S39 mistake #3.)

3. **`view` enums before referencing values.** WallTag is
   {EXTERNAL, INTERNAL, LOAD_BEARING}, NOT PERIMETER. (S39 mistake #4.)

4. **Don't file monolithic backlog items.** B-NEW-T was originally
   monolithic; vertical slices (T1/T2/T3) are the right granularity.
   (S39 mistake #5.)

5. **At each tier boundary in multi-tier work, restate scope risk.**
   Pattern E (scope creep mid-build) is the most expensive failure
   mode. If you find yourself spelunking C7/C8/C9/C10 internals deeper
   than expected, STOP and report progress before continuing. (S39
   mistake #6.)

6. **Reject critique walks that don't match the code.** Use grep
   evidence per Rule 7. Don't engage with hallucinated reviews even
   under pressure. (S39 mistake #7 — round-2 review of a workflow
   system that doesn't exist.)

7. **Backlog files belong in `04_backlog/`, NOT inside `buildemup/`.**
   (S39 mistake #1.)

---

## 6. RULES YOU MUST FOLLOW

These are the standing Ramalingam rules (full text in
`00_START_HERE/RULES_RAMALINGAM_FORMALIZED.md`). Quick reminders:

- **Rule 7 — critique handling**: web search ≥1 per critique walk, grep
  for code claims, push back when wrong. Use verdicts: VALID / BACKLOG /
  MISFRAMED / DOCUMENTED / SPEC-AMENDMENT.
- **Rule 8 — LOCK authority**: belongs to Ramalingam. NEVER self-declare
  "vN LOCKED." Always present as "vN PROPOSED. PENDING Ramalingam LOCK
  adjudication." Wait for explicit "lock it."
- **Rule 9 — backlog visibility inside spec**: every backlog item the
  spec depends on must be enumerated in spec § 12 with ID, description,
  origin, trigger, S{N}-scope verdict, effort estimate.
- **Rule 9.2 — always-file-backlog directive**: when a critique surfaces
  VALID-BUT-BACKLOG items, file them in
  `04_backlog/v0_2_backlog.md` immediately, without asking permission.
- **Rule 10 — handoff bundle structure**: 10-directory layout,
  numbering continues across sessions, never invent new top-level dirs.
- **Rule 10.6 — three-check protocol** (GAP / AUDIT / INTEGRITY) before
  any handoff zip.
- **Rule 10.6.1 — pre-touch state inventory** before claiming credit.
- **Rule 10.7 — handoff timing**: when Ramalingam says "hand off,"
  first response is status block + three-check plan. No bundle assembly
  until Ramalingam confirms.

---

## 7. WORKING ENVIRONMENT REMINDER

- **Working tree**: `/home/claude/work/buildemup/` — writable. (May not
  exist yet in your fresh session; if you need to extract this bundle,
  unzip `03_code_chronological/S39_C11a_subsessions_2_3_4_and_critique_walk_patches.zip`
  into `/home/claude/work/buildemup/components/c11a/` and
  `/home/claude/work/buildemup/tests/test_c11a/` respectively.)
- **C11a code drop-in**: `03_code_chronological/S39_C11a_subsessions_2_3_4_and_critique_walk_patches/components_c11a/`
  → goes to `/home/claude/work/buildemup/components/c11a/`.
- **C11a tests drop-in**: `.../tests_c11a/` → goes to
  `/home/claude/work/buildemup/tests/test_c11a/`.
- **Upstream codebase** (read-only reference): in `06_upstream_codebase/`
  of this bundle. Use to view C7/C8/C9/C10 source.
- **Spec**: `02_specs_chronological/66_C11a_SPEC_v1_0_LOCKED.md`.

---

## 8. EXPECTED SESSION OUTCOME

By session end, you should deliver:

1. ✅ C7 amendment v0.9 PROPOSED (extending generate() with optional
   target_bay_*_m args). PENDING Ramalingam LOCK before code lands.
2. ✅ `m7_grid_scale_real.py` shipped with `regenerate_for_m7` +
   `M7NotViableError`.
3. ✅ `upstream_adapter.py` extended for M7a/M7b dispatch + diff.
4. ✅ `test_c11a_subsession6_m7_vertical_slice.py` with ≥6 tests covering
   cascade success/failure, Inv 17 atomicity, diff, dispatch, C7
   regression.
5. ✅ Full project: 2731 + N passed, zero regressions.
6. ✅ Three-check trio for S40 in `05_integrity_check/`.
7. ✅ Backlog update: B-NEW-T2 → LANDED. B-NEW-T1.5 + B-NEW-T3 + B-NEW-Y
   full + B-NEW-W full still pending (carry forward).
8. ✅ `NEXT_CLAUDE_HANDOFF.md` updated for S41 (your handoff to the
   NEXT next Claude — likely B-NEW-T3 priority).

---

## 9. IF YOU GET STUCK

**Symptoms of being stuck**:
- More than 30 minutes spelunking a single upstream component
- Test failures you can't diagnose after 2-3 attempts
- Cascade error that surfaces deep in C8 or C9 internals

**Action**: STOP. Report status to Ramalingam with:
- What you tried
- The exact error / line
- Three options for next move (e.g., "(a) stub the failing layer, (b)
  ask Ramalingam, (c) defer to T2.5")

Pattern E (scope creep mid-build) is the most expensive failure mode.
A 30-minute progress report beats 4 hours of going-it-alone.

---

## 10. STANDING OBLIGATIONS (every session)

Per `00_START_HERE/THREE_OBLIGATIONS_AND_PATTERNS.md`:

1. **Spec-first discipline**: never code before LOCKED spec. For
   B-NEW-T2 there's no NEW spec needed — the C11a v1.0 LOCKED spec
   already covers M7. The C7 amendment is the only spec change, and
   that needs Ramalingam LOCK before code.
2. **Honest context budget** declared at session start.
3. **Master doc + NEXT_CLAUDE_HANDOFF.md updated at session end.**

---

**Your priority is B-NEW-T2. Start now.**

— Claude (S39 close)
