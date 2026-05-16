# S46_C14_C15_LOCKED_spec_only — README

**Session:** S46 (BuildemUp, this iteration)
**Status:** C14 v0.2 + C15 v0.2 SPECS LOCKED by Ramalingam at S46 close.
**Code:** NOT YET WRITTEN. This directory is a marker for spec-only LOCK; implementation begins at S47.

---

## What was LOCKED at S46

Two specs reached SKETCH-level LOCK (analog of C13's v0.6 path c LOCK):

1. **C14 v0.2 LOCKED** — Connection-Graph Quality Engine
   - 2 spec files in `02_specs_chronological/S46_C14_C15_specs/`:
     - `spec_C14_v0_1_PROPOSED.md` (553 lines)
     - `spec_C14_v0_2_PROPOSED_DELTA.md` (385 lines)
   - LOCKED reference: `spec_C14_v0_2_LOCKED.md`
   - 13 cumulative backlog items (4 LOCK-mandatory)

2. **C15 v0.2 LOCKED** — Layout Problem Finder
   - 2 spec files in `02_specs_chronological/S46_C14_C15_specs/`:
     - `spec_C15_v0_1_PROPOSED.md` (760 lines)
     - `spec_C15_v0_2_PROPOSED_DELTA.md` (485 lines)
   - LOCKED reference: `spec_C15_v0_2_LOCKED.md`
   - 26 cumulative backlog items (7 LOCK-mandatory)

---

## Why spec-only LOCK at this session

S46 was a spec-focused session. Ramalingam's directives traced:

- S46 start: "Lock this build" (re: C13 v1.0 implementation, locking the S45 ship)
- After C14 v0.1 + v0.2 walks: "Lock this and let's move on to c15 spec doc"
- After C15 v0.1 + v0.2 walks: "Lock this and give me the handoff and make sure every file is in there and the next Claude should start building the code for both the locked docs immediately"

The session shipped 4 spec documents (~2,183 lines of spec content) + 4 critique walks (2 per component) + 38 cumulative backlog items.

NO C14 or C15 production code was written this session. That's the explicit mandate for S47.

---

## Implementation reading order for S47

Next Claude should:

1. **Read `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` FIRST** for the coding mandate.
2. **Read `00_START_HERE/RULES_RAMALINGAM_FORMALIZED.md`** — especially Rules 7 (critique walks), 8 (LOCK authority), 9/9.2 (backlog discipline), 10/10.6/10.7 (handoff structure), 11 (vigorous self-analysis + web search).
3. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C14_v0_2_LOCKED.md`** — the LOCKED state of C14, with implementation pointers.
4. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C14_v0_1_PROPOSED.md`** — foundational v0.1.
5. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C14_v0_2_PROPOSED_DELTA.md`** — 12 amendments layered.
6. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C15_v0_2_LOCKED.md`** — the LOCKED state of C15.
7. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C15_v0_1_PROPOSED.md`** — foundational v0.1.
8. **Read `02_specs_chronological/S46_C14_C15_specs/spec_C15_v0_2_PROPOSED_DELTA.md`** — 10 amendments layered.
9. **Read `04_backlog/v0_2_backlog_S46_C14_C15_LOCKS.md`** — combined backlog table.
10. **Inventory the working tree** per Rule 10.6.1 before claiming credit for any pre-existing file.

---

## Build order suggestion (per S47 NEXT_CLAUDE_HANDOFF mandate)

C14 should be built BEFORE C15 because C15 consumes `CirculationGraphReport` from C14. Suggested decomposition:

### C14 build (estimated 4-5 sub-sessions)

- Sub 1: schema + errors + contracts + versioning + cache_keys (foundational)
- Sub 2: Phase α (graph construction) + Phase β (node-level metrics: BFS step-depth, connectivity, betweenness)
- Sub 3: Phase γ (layout-level metrics: mean_depth, raw_RA, RRA, integration) + Phase δ (Structural + Preference flag emission) + Phase ε + ζ (passthrough + assembly)
- Sub 4: Orchestrator + provenance + telemetry + PBT
- Sub 5: Adversarial integration corpus + LOCK readiness check

### C15 build (estimated 5-6 sub-sessions)

- Sub 1: schema + errors + contracts + cultural_profile API + severity rule table scaffolding
- Sub 2: Check registry (skeleton for 35-41 checks; ~20 RUNNABLE, ~15 NOT_APPLICABLE at v1)
- Sub 3: Per-dimension check implementations (D1: no wasted space; D2: room sizes; D3: logical flow; D5: privacy; D6: no bottlenecks)
- Sub 4: Remaining runnable dimensions + unconventional pattern detection
- Sub 5: ProblemReport assembly + dimension_summary + deferred_checks + telemetry + provenance
- Sub 6: Adversarial integration corpus + B-C15-MOAT-LINT + LOCK readiness check

---

## What's NOT in this directory

No `.py` files. No `tests/`. This directory is intentionally code-empty.

The future S47_C14_v1_0_SHIPPED/ and S{N}_C15_v1_0_SHIPPED/ directories will hold the implementation artifacts when shipped.
