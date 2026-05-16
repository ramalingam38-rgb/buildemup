# NEXT_CLAUDE_HANDOFF — S45 entry point

**Authored at**: S44 continuation close (2026-05-13).
**Authority**: Ramalingam directive *"Lock it and give me the handoff"* (path c per walk #7+#8 decision).
**Bundle version**: handoff_v17_session_44.

---

## You (the next Claude) — read this FIRST

Before doing anything:

1. **Read `00_START_HERE/RULES_RAMALINGAM_FORMALIZED.md`** (Rules 1-11, especially Rule 8 LOCK authority, Rule 10 handoff structure, Rule 10.6 three-check, Rule 11 vigorous self-analysis + web search).
2. **Read `00_START_HERE/THREE_OBLIGATIONS_AND_PATTERNS.md`** (spec-first / context budget / handoff updates; 5 patterns to avoid).
3. **Read the latest C12 LOCKED spec**: `02_specs_chronological/spec_C12_v1_0_LOCKED.md`.
4. **Read the latest C13 LOCKED spec**: `02_specs_chronological/spec_C13_v1_0_LOCKED.md`. This is a SHORT marker; full normative spec is composed from v0.1 + v0.2-v0.7 deltas in the same directory.
5. **Read this handoff (the current document).**
6. **Inventory the working tree per Rule 10.6.1** before claiming credit for any pre-existing file.

---

## State at S44 close

### Components shipped (Track 3 canonical 17-component v3)

✓ C1, C2, C3a, C4, C5, C6, C7, C8, C9, C10, C11a, C11b, **C12 v1.0 LOCKED** (full build complete).
✓ **C13 v1.0 LOCKED** (spec only — NO production code yet).

⏳ Pending: C14, C15, C16, C17.

### Test posture

**3272 passed / 3 skipped / 0 failed** at S44 close. No regression. Full run 78s.

### C13 LOCK summary

- 23 invariants D1-D23 organized in 6 categories (HARD_LEGALITY, CONDITIONAL_LEGALITY, DETERMINISM, GRAPH_INTEGRITY, GEOMETRY, ADVISORY_HYGIENE)
- Typestate API (SuccessfulDoorPlacement / FailedDoorPlacement)
- C13ConsumesFromC12Edge Protocol abstraction (decouples C13 from raw C12 schema)
- 6 algorithm phases (A-F); Phase F is pure-verification per D22
- 90-day post-LOCK fast-revision window (E4 + F3 stabilization-only constraint)
- 35 v1.x polish-deferred backlog items consolidated in `04_backlog/v0_2_backlog_S44_C13_v1x_polish_rollup.md`

### Path (c) LOCK decision — what was waived

Path (a) prerequisites (C14 v0.1 sketch + composability validation + end-to-end example + walk #6.5) were waived. Their effective deadline is now the **90-day fast-revision window**: if C14 build surfaces composability gaps, fix via v1.0.x patch (stabilization-only per F3) or queue for v1.1 (feature-expansion).

---

## S45 work priorities (suggested order)

### 1. C13 v1 build (PRIMARY)

C13 v1.0 spec is LOCKED but has zero production code. Build sequence:

**Foundational** (mirror C12 pattern):
- `components/c13/versioning.py` — C13_VERSION, C13_EDGE_PROTOCOL_VERSION, ADVISORY_SCHEMA_VERSION + expected upstream versions
- `components/c13/errors.py` — LocalPlacementError / PerCandidatePlacementError hierarchy (8-10 failure types)
- `components/c13/schema.py` — Door, AdvisoryFlag (with reserved causal_context), CausalContext sentinel, Successful/FailedDoorPlacement typestate, DoorPlacementBatchResult, ConditionalLegalityViolation, C13CacheKeys
- `components/c13/contracts.py` — C13ConsumesFromC12Edge Protocol
- `components/c13/config.py` — DoorPlacementConfig with v1 LOCKED defaults

**Support**:
- `components/c13/cache_keys.py` — split cache (geometry/advisory/full per D18 prefix rule)
- `components/c13/telemetry.py` — DoorPlacementEvent + PhaseDConvergenceEvent

**Algorithmic** (Phases A-F):
- `components/c13/edge_selection.py` — Phase A (3-tier priority B6)
- `components/c13/swing_assignment.py` — Phase B (bathroom-preferred-inward, A6)
- `components/c13/position_selection.py` — Phase C (corner_offset 0.15m, grid-snapped)
- `components/c13/conflict_resolution.py` — Phase D (bounded CSP-lite, B3 visited-state + total-order tie-break)
- `components/c13/assembly.py` — Phase E (canonical assembly + cache keys)
- `components/c13/verification.py` — Phase F (PURE per D22; D11.3'/D13/D17/D19 checks)
- `components/c13/orchestrator.py` — Phase A→F pipeline

**Tests**:
- Foundational, support, each algorithmic layer
- 27 PBT floor: 23 invariants + 3 failure-trigger + 5 adversarial + 3 adversarial-stacking + 3 semantic-conformance (per v0.4 C3)
- Integration test composing C12 SharedEdges → C13 doors

### 2. Adversarial integration corpus (recommended before/during build)

`B-C13-ADVERSARIAL-INTEGRATION-CORPUS` (walk #6 item). Generate random compact layouts (n=3-8 rooms, envelope tightly fitting), run full C13 pipeline, detect oscillation/loops/non-determinism.

### 3. C12 v1.1 amendment (parallel work)

`B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT` (HIGH priority routed). Add `edge_type: EdgeType` enum to C12 SharedEdge (INTERNAL / EXTERNAL_ENVELOPE / SERVICE / BALCONY). Decoupled from C13 via Protocol; C13 binds against a sentinel placeholder until C12 v1.1 ships. Full spec walk required (not a quick patch — reviewer warned in C13 v0.4).

### 4. C14 v0.1 sketch

D11 minimum scope checklist (with E2 composability validation):
- § 0 purpose + boundary mirror of C13 § 0.5
- § 1 inputs: DoorPlacementResult + AdvisoryFlag tuple + DoorPlacementProvenance
- § 2 layout_quality_band scoring output (GOOD/ACCEPTABLE/COMPROMISED per B-C14-LAYOUT-QUALITY-BAND)
- § 3 worked example flow (C12 → C13 → C14 trace for 4-room compact layout)
- § 4 composability validation per E2 (a-d questions answered)

### 5. v1.x polish backlog (within 30 days post-LOCK)

Top priority: `B-C13-INVARIANT-TAXONOMY-GROUPING` (flagged 3 walks deep as critical for cognitive tractability).

---

## Operating obligations (every session, including this one)

Per non-negotiable obligations (Rule 6):
1. **Spec-first discipline** — never code before LOCKED spec. Always: draft → critique → lock → then code.
2. **Honest context budget** declared at session start.
3. **Master doc + NEXT_CLAUDE_HANDOFF.md updated at session end.**

Per Rule 11: **vigorous self-analysis + web research** on every spec/code creation, amendment, AND critique walk.

Per Rule 10.7: **handoff timing** — when Ramalingam says "hand off", first response is status block + three-check plan + bundle structure plan. No bundle assembly until confirmed.

---

## Pattern E warning (active)

The C13 spec-walk loop reached convergence at walks #5-#7 and was explicitly refused at walk #8 per Pattern E discipline. **Do not re-enter abstract spec-walk loops for components that have already reached LOCK-candidate status across 2+ consecutive walks.**

If a future external critique arrives on LOCKED C12 or LOCKED C13:
- VALID structural concerns → file as v1.x backlog OR route to v1.1 spec walk
- Polish/governance concerns → file as v1.x backlog
- DO NOT produce v1.0.x or v0.X delta documents in response to abstract reviewer critiques unless they identify a LOCK-blocking correctness defect

---

## Cumulative project state

- Sessions completed: ~44 (S0 through S44 continuation close).
- Components LOCKED: 14 of 17.
- Test count: 3272 (steadily growing component by component).
- Backlog total across all components: ~150+ items (35 of those are C13-scope).

You are roughly **85% through the v1 component build**. The architecturally-hardest decisions (boundary clarifications, typestate APIs, NBC compliance grounding) are done. Remaining components (C14-C17) build on this foundation.

---

**Welcome to S45. Read the bundle, inventory the tree, and build C13 v1.**
