# NEXT_CLAUDE_HANDOFF — S47 entry point

**Authored at**: S46 close (this is the handoff producing session).
**Authority**: Ramalingam directive at S46 close: *"Lock this and give me the handoff and make sure every file is in there and the next Claude should start building the code for both the locked docs immediately."*
**Bundle version**: handoff_v17_session_46.
**Coding mandate level**: EXPLICIT. Start building C14 + C15 code IMMEDIATELY.

---

## You (the next Claude — S47) — read this FIRST

Before doing ANYTHING:

1. Read `RULES_RAMALINGAM_FORMALIZED.md` (Rules 1-11). Especially Rules 7 (critique walks + backlog roll-up + web search), 8 (LOCK authority — NEVER self-LOCK), 9/9.2 (backlog discipline), 10/10.6/10.6.1/10.7 (handoff structure + three-check + pre-touch inventory), 11 (vigorous self-analysis + web search).
2. Read `THREE_OBLIGATIONS_AND_PATTERNS.md` (spec-first / context budget / handoff updates; 5 patterns to avoid).
3. Read `D-066_BUILD_CYCLE_RULE.md` (build cycle discipline).
4. **Read this handoff file completely.**
5. **Inventory the working tree per Rule 10.6.1** before claiming credit for any pre-existing file. The PRE_TOUCH_INVENTORY.md in `05_integrity_check/S46_close/` tells you exactly what S46 added vs what was pre-existing.

---

## State at S46 close (what you're inheriting)

### Components shipped (Track 3 canonical 17-component)

✅ **Through code, fully shipped (11/17):**
- C1, C2, C3a, C4, C5, C6, C7, C8, C9, C10, C11a, C11b, C12 v1.0
- **C13 v1.0** — IMPLEMENTATION LOCKED at S45 close. 16 production modules + 7 test modules + 217 C13 tests.

📋 **Spec LOCKED but NO CODE YET (2/17):**
- **C14 v0.2 LOCKED** at S46 (this is YOUR build target #1)
- **C15 v0.2 LOCKED** at S46 (this is YOUR build target #2)

⏳ **Pending future spec drafts (2/17):**
- C16, C17

### Test posture

**3489 passed / 3 skipped / 0 failed** at S45 close, inherited unchanged at S46 close (this session did not touch any tests).

**Run from `06_upstream_codebase/buildemup/`:**
```
python -m pytest -q
```
**Expected first action at S47 start: verify the test count is 3489/3/0 in your environment before writing any new code.**

If the count differs, surface the discrepancy to Ramalingam immediately — do not proceed with C14/C15 work until baseline is established.

### Backlog state

Cumulative C14 + C15 backlog at LOCK: **36 items** (de-duped project-scope). 
- 11 LOCK-mandatory
- 1 fast-revision-window (B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS, 90-day clock)
- 4 data-dependency unlocks (route to upstream future engines)
- 4 annual audits
- 10 post-LOCK polish
- 3 project-scope (de-duped)
- 3 routed to other components

Full tabular roll-up: `04_backlog/v0_2_backlog_S46_C14_C15_LOCKS.md`. Read this BEFORE starting C14 build.

---

## YOUR EXPLICIT MANDATE (Ramalingam-verbatim)

> "the next Claude should start building the code for both the locked docs immediately"

You are to build:
1. **C14 v1.0 implementation** from `02_specs_chronological/S46_C14_C15_specs/spec_C14_v0_2_LOCKED.md`
2. **C15 v1.0 implementation** from `02_specs_chronological/S46_C14_C15_specs/spec_C15_v0_2_LOCKED.md`

C14 BEFORE C15 (C15 consumes C14's CirculationGraphReport).

Each `_LOCKED.md` file is a thin reference; the binding spec is the combination of `_v0_1_PROPOSED.md` + `_v0_2_PROPOSED_DELTA.md`. Read all four files (two per component).

---

## Recommended build order (5-6 + 5-6 sub-sessions)

### C14 build first (estimated 4-5 sub-sessions to v1.0 shipped)

**C14 architecture summary (from LOCKED spec):**
- Consumes `DoorPlacementBatchResult` from C13
- Builds adjacency graph from doors (node = room, edge = door)
- Computes Hillier 1984/1987 metrics: step-depth, connectivity, betweenness, mean_depth, raw_RA, RRA, integration
- Emits CirculationGraphReport with **STRUCTURAL** + **PREFERENCE** flag tuples (separate enums — A4 amendment)
- Per-candidate, read-only
- ~116 tests target

**Sub-session decomposition:**

| Sub-session | Modules | Test focus | Target count |
|---|---|---|---|
| Sub 1 | `__init__.py`, `versioning.py`, `errors.py`, `contracts.py`, `cache_keys.py`, `config.py`, `schema.py` (CirculationGraphReport, CirculationFlag x2 enums) | Foundational | +40 |
| Sub 2 | `graph_construction.py` (Phase α), `node_metrics.py` (Phase β — BFS + connectivity + betweenness) | Per-phase units | +20 |
| Sub 3 | `layout_metrics.py` (Phase γ — mean_depth + raw_RA + RRA + integration + graph_size_category), `flag_emission.py` (Phase δ — Structural + Preference + truncation_meta), `assembly.py` (Phase ε + ζ — passthrough + report assembly) | Per-phase units | +25 |
| Sub 4 | `orchestrator.py`, `provenance.py`, `telemetry.py` | Orchestrator + provenance + PBT | +30 |
| Sub 5 | Adversarial integration corpus (`test_c14_adversarial_integration_corpus.py`) + LOCK readiness | Integration | +11 |

**Critical C14 invariants to nail (from LOCKED spec):**
- Inv E3' — EXTERNAL exclusion BOTH sides of edge tuple
- Inv E11' / E11'' / E17 — raw_RA unbounded, RRA bounded for k≥4 with `nan` for k<4, graph_size_category emitted
- Inv E13' — truncation meta-flag accommodation when density cap fires
- Inv E18 — category_coverage populated

**Watch out for:**
- B-C12-EDGE-DENSITY (routed from S45 C13 work): C12's slicing_kd_tree typically produces 0 shared edges in multi-room layouts. C14 will mostly emit empty graphs when run on real C12 → C13 output. Use hub-and-spoke synthetic fixtures, OR mark integration tests as "blocked on C12 fix."

### C15 build second (estimated 5-6 sub-sessions to v1.0 shipped)

**C15 architecture summary (from LOCKED spec):**
- Consumes C12 PlacedCandidate + C13 SuccessfulDoorPlacement + C14 SuccessfulCirculationAnalysis
- Runs ~35-41 structured checks across 10 dimensions
- Per check: status (pass/warn/fail/N/A), severity, epistemic_kind (regulatory / architectural_heuristic / cultural_preference), affected rooms, rule citation, why-it-matters
- **NEVER produces a single layout-quality score (Inv P0 STRENGTHENED by A1).** C17 owns aggregation.
- Cultural profile REQUIRED (no default; ≥3 sub-variants at LOCK)
- ~214 tests target

**Sub-session decomposition:**

| Sub-session | Modules | Test focus | Target count |
|---|---|---|---|
| Sub 1 | `__init__.py`, `versioning.py`, `errors.py`, `contracts.py`, `cultural_profile.py` (enum + per-profile config), `severity_rule_table.py` (skeleton; severity_basis required), `schema.py` (ProblemCheck w/ epistemic_kind, ProblemReport w/ applicable + deferred + dimensions_not_evaluated + unconventional_pattern_hint), `cache_keys.py` | Foundational | +50 |
| Sub 2 | `check_registry.py` (skeleton declaring all ~35-41 checks with stable IDs + epistemic_kind), `na_reason.py` (structured NA reasons + data-dependency mapping) | Registry + NA | +30 |
| Sub 3 | Per-dimension check implementations (D1: no wasted space; D2: room sizes; D3: logical flow; D5: privacy; D6: no bottlenecks) | Per-dimension units | +40 |
| Sub 4 | Per-dimension check implementations (D4: natural light NA, D7: first-floor living partial, D8: outdoor connection partial, D9: storage NA, D10: multi-functional NA) + `unconventional_pattern_detection.py` | Per-dimension units | +30 |
| Sub 5 | `report_assembly.py` (dimension_summary restructured per A10; applicable + deferred split per A5; dimensions_not_evaluated per A6; unconventional_pattern_hint per A7), `orchestrator.py`, `provenance.py`, `telemetry.py` | Assembly + orchestrator | +40 |
| Sub 6 | `B-C15-MOAT-LINT` CI rule + adversarial integration corpus + LOCK readiness | Integration | +24 |

**Critical C15 invariants to nail (from LOCKED spec):**
- **Inv P0 STRENGTHENED** — C15 NEVER computes any single number representing layout quality, anywhere. Implement B-C15-MOAT-LINT (CI grep rule) FIRST and run it against your own code at every sub-session.
- Inv P17 — cultural_profile REQUIRED (raise MissingMetadataError if absent)
- Inv P18 — severity_basis ≥ 20 chars on every (check_id, status) → severity mapping; module load enforces
- Inv P19 — dimensions_not_evaluated non-empty at every report

**Watch out for:**
- The 4 LOCK-mandatory items needing pin during build: severity rule table, check registry, cultural profile API (≥3 sub-variants), measurement formulas. These will surface naturally during sub-sessions. File v0.3+ PROPOSED_DELTAs as critique walks emerge.
- B-C15-MOAT-LINT (LOCK-mandatory) is the structural enforcement of Inv P0. Build it first; never skip it.

---

## Build verification gates per sub-session

Each sub-session MUST end with:

1. **Full test suite passes** — `python -m pytest -q` shows 0 failures
2. **Test count progression on track** — within ±10 of target
3. **No new lint/import errors** — `python -c 'from buildemup.components.c14 import *'` succeeds (etc.)
4. **B-C15-MOAT-LINT passes for C15 work** — no numeric aggregation functions in C15 module
5. **Master doc delta updated** — log incremental progress in `01_master_doc/` (delta naming continues from `MASTER_DOC_v3_13_S38_CLOSE.md` chain; consider writing `MASTER_DOC_v3_14_TO_v3_15_DELTA.md` to resume the series)
6. **`NEXT_CLAUDE_HANDOFF.md` updated** even within a session — capture state for next sub-session

---

## Five patterns to avoid (mapped to C14/C15 context)

### Pattern A — fix-as-bandage
**C14/C15 risk**: When real C12 → C13 → C14 corpus testing produces empty graphs (B-C12-EDGE-DENSITY), DO NOT silently change C14's flag thresholds to "make it work." Surface as a fixture-design decision OR route the issue back to C12.

### Pattern B — building-without-wiring
**C14/C15 risk**: C14 produces CirculationGraphReport; C15 consumes it. Do NOT ship C14 v1.0 without verifying C15 can consume the actual output type. Wire end-to-end smoke test at C14 Sub 5.

### Pattern C — scores-without-truth
**C15 risk**: This is THE pattern C15 is designed to avoid. **No single score, ever.** If you find yourself tempted to add an aggregate-quality-number field "just for convenience," STOP. That violates Inv P0. C17 reads `ProblemReport.checks` and computes its own aggregate.

### Pattern D — rules-on-rules
**C14/C15 risk**: The temptation to add a new metric/check "because it's easy." C14 A9 + C15 A8 codify the metric-addition gate. Honor the gate. Every new check is architectural debt unless proven otherwise.

### Pattern E — scope-creep-mid-build (MOST EXPENSIVE)
**C14/C15 risk**: Walks #1+#2 already showed C14 and C15 at the diminishing-returns boundary. Pre-implementation refinement is foreseen-need, not actual-need. BUILD THE SPEC AS LOCKED. Surface real implementation findings as v0.3+ critique walks DURING build. Do not pre-emptively re-amend.

---

## C13 fast-revision-window items (carry-forward)

Per the C13 v1.0 LOCK (S44 path c) + S45 implementation LOCK, several items are in the 90-day fast-revision window:

- B-C13-STRUCTURAL-PHASE-TAGGING — improve `_classify_error_phase()` to be structural rather than message-prefix introspection
- B-C13-CONDITIONAL-LEGALITY-CATEGORY-FREEZE — pin which invariants are HARD vs CONDITIONAL
- C13 walk #6.5 (composability) — was deferred at S44 path c; should be addressed before window closes

If C14 build surfaces a C13 composability gap, file as composability-flag in this window. Otherwise, this is a separate stream from your C14/C15 mandate.

---

## What's in this handoff bundle

```
handoff_v17_session_46/
├── 00_START_HERE/
│   ├── NEXT_CLAUDE_HANDOFF.md          ← YOU ARE HERE
│   ├── RULES_RAMALINGAM_FORMALIZED.md  ← READ FIRST
│   ├── THREE_OBLIGATIONS_AND_PATTERNS.md
│   ├── D-066_BUILD_CYCLE_RULE.md
│   ├── S44_continuation_close_NEXT_CLAUDE_HANDOFF_archive.md  ← prior session's handoff
│   ├── ... (archived NEXT_CLAUDE_HANDOFFs from S37-S44)
│   └── (other context-setting files from prior bundle)
├── 01_master_doc/                       ← prior master doc chain (no S46 delta — Rule 3 deviation noted)
├── 02_specs_chronological/
│   ├── 01-106_*.md                     ← prior LOCKED specs (C4-C11b)
│   ├── S43_S44_specs/                  ← prior C12 spec evolution
│   ├── S44_continuation_C13_specs/     ← C13 v0.1-v0.7 + v1.0 LOCKED spec
│   └── S46_C14_C15_specs/              ← THIS SESSION'S CONTRIBUTION
│       ├── spec_C14_v0_1_PROPOSED.md   ← 553 lines, foundational
│       ├── spec_C14_v0_2_PROPOSED_DELTA.md ← 385 lines, 12 amendments
│       ├── spec_C14_v0_2_LOCKED.md     ← thin reference summarizing LOCK
│       ├── spec_C15_v0_1_PROPOSED.md   ← 760 lines, foundational
│       ├── spec_C15_v0_2_PROPOSED_DELTA.md ← 485 lines, 10 amendments
│       └── spec_C15_v0_2_LOCKED.md     ← thin reference summarizing LOCK
├── 03_code_chronological/
│   ├── ... (S30-S44 prior code shipments)
│   ├── S45_C13_v1_0_SHIPPED/           ← C13 v1.0 implementation reference
│   │   ├── README.md
│   │   ├── C13_README_from_bundle.md
│   │   └── c13_v1_0_bundle_s45.zip
│   └── S46_C14_C15_LOCKED_spec_only/   ← marker for spec-only LOCK
│       └── README.md
├── 04_backlog/
│   ├── ... (prior session backlog files)
│   └── v0_2_backlog_S46_C14_C15_LOCKS.md  ← cumulative C14+C15 backlog (36 items)
├── 05_integrity_check/
│   ├── S44_continuation_close/         ← prior three-check
│   └── S46_close/                      ← THIS SESSION'S three-check
│       ├── PRE_TOUCH_INVENTORY.md
│       ├── GAP_CHECK.md
│       ├── AUDIT_CHECK.md
│       └── INTEGRITY_CHECK.md
├── 06_upstream_codebase/
│   └── buildemup/                      ← REPLACED with S46-close working tree
│       ├── components/
│       │   ├── c01/ ... c12/           ← prior components, unchanged
│       │   └── c13/                    ← S45 C13 v1.0 production (16 modules)
│       │   (NO c14/ or c15/ — YOUR mandate to create)
│       └── tests/
│           ├── test_c01/ ... test_c12/ ← prior tests
│           └── test_c13/               ← S45 C13 v1.0 tests (7 modules, 217 tests)
│           (NO test_c14/ or test_c15/ — YOUR mandate to create)
├── 07_design_documents/                ← intact
├── 08_session_transcripts/             ← intact (S46 transcript not added)
└── 09_conversation_artifacts/          ← intact
```

---

## Session-opener checklist (S47)

When you start:

1. ✅ Declare context budget honestly (Rule 2 — this session deviated by not declaring; you should)
2. ✅ Read this handoff completely
3. ✅ Read RULES_RAMALINGAM_FORMALIZED.md
4. ✅ Run pre-touch inventory of working tree (Rule 10.6.1)
5. ✅ Run baseline test suite: `python -m pytest -q` in `06_upstream_codebase/buildemup/`. Expect 3489/3/0. Surface deviation immediately if not.
6. ✅ Read the four spec files (`spec_C14_v0_1_PROPOSED.md`, `spec_C14_v0_2_PROPOSED_DELTA.md`, `spec_C15_v0_1_PROPOSED.md`, `spec_C15_v0_2_PROPOSED_DELTA.md`) PLUS the two LOCKED references
7. ✅ Read the cumulative backlog file
8. ✅ Read the integrity check artifacts to understand exactly what S46 added vs inherited
9. ✅ Begin C14 Sub 1 (foundational layer)

---

## Final notes from S46 Claude

Three things to be aware of:

1. **The moat is C15 Inv P0.** Do not weaken it during implementation. The whole product differentiation strategy hangs on "we show problems, not scores." Implement B-C15-MOAT-LINT first and let it gate every C15 sub-session.

2. **C14's small-graph math.** Inv E11' + E11'' + E17 are unusually careful. The raw Hillier 1984 RA formula yields values > 1.0 for k=3 graphs. C14 v0.2 fixes this via RRA (Hillier 1987). Implement BOTH; expose `graph_size_category` so downstream consumers gate on graph size before trusting RRA.

3. **B-C12-EDGE-DENSITY is a real blocker for integration testing.** C12's slicing_kd_tree typically emits 0 shared edges for multi-room layouts, so naive `C12 → C13 → C14` pipelines produce empty graphs. Your options: hub-and-spoke synthetic fixtures, OR direct C13 SuccessfulDoorPlacement construction bypassing C12. The S45 C13 corpus tests took the hub-and-spoke path; mirror that.

You're set up well. Build cleanly, stay within scope, and surface real implementation findings via v0.3+ walks (not pre-emptive amendments). Ramalingam's locking pattern has been consistent: walk once or twice, then LOCK when diminishing returns surface.

— S46 Claude
