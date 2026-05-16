# NEXT_CLAUDE_HANDOFF — S49

**From:** S48 (Path A LOCK-prep + critique walks).
**To:** S49 (or whichever session next picks up BuildemUp).
**Status at handoff close:** C15 at v0.3.LOCK-CANDIDATE.

---

## Read these first, in order

1. **`02_specs_chronological/S48_C15_specs/c15_v0_3_PROPOSED_amendments.md`** —
   v0.3 amendment bundle: § 14.2 severity governance gate + A12
   coverage_quality field. PROPOSED, not LOCKED.

2. **`02_specs_chronological/S48_C15_specs/c15_v1_LOCK_seals.md`** —
   Triple seal: severity rule table, check registry, measurement
   formulas. Pinned values + change protocols.

3. **`05_integrity_check/S48_three_check_results.md`** — full audit
   showing all 8 LOCK-mandatory items closed + A12 processed +
   three-check protocol PASS.

4. **`09_conversation_artifacts/LOCK_trigger_protocol.md`** — STANDING
   project policy. Every future "lock" trigger from Ramalingam invokes
   this protocol before LOCK declaration.

5. **`08_session_transcripts/S48_critique_walk_record.md`** — both
   critique walks (item 7 walk #1 → § 14.2; item 8 walk #1 → A12;
   etc.) with pushback rationale.

---

## Standing project state

### Track 3 canonical (17 components, ~19 sub-components)

**LOCKED + shipped:** C1, C2, C3a, C4, C5, C6, C7, C8, C9, C10, C11a,
C11b, C12, C13, C14 (15 sub-components).

**At LOCK-CANDIDATE — Ramalingam adjudication pending:** **C15 v0.3.LOCK-CANDIDATE.**

**Spec LOCKED, build not started:** C16 v0.5 (S47).

**Not yet specced:** C17 (Ranker + NSGA-II), C18 (Dual-Drawing
Renderer — C16 is also dual-drawing; reconcile numbering at C17 spec
time).

### S48 session ledger

- **Critique walks (2):** 24 items reviewed total → 15 new B-NNN
  items filed + 3 scope extensions + 2 PROPOSED amendments
  (A11 withdrawn → re-filed as LOCK-mandatory; A12 deferred → landed
  via Path A).
- **Path C → Path A reversal:** Ramalingam initially chose Path C
  (freeze v0.2-PENDING-LOCK) then reversed: "Execute the deferred
  lock mandatory items first."
- **Path A execution:** All 8 LOCK-mandatory items + A12 closed in
  one session. 264 tests passing (was 209).
- **LOCK-trigger protocol established** (memory edit #14): when
  Ramalingam says "lock", Claude processes deferred PROPOSED
  amendments + LOCK-mandatory backlog + three-check protocol BEFORE
  surfacing LOCK-CANDIDATE.

---

## Immediate next decision for S49

**The next action depends entirely on Ramalingam's adjudication on
v0.3.LOCK-CANDIDATE:**

### Path X — Ramalingam locks v0.3 (most likely)
- Mark C15 v1.0 LOCKED. Update master doc.
- Begin C16 build per the C16 v0.5 LOCKED spec.
- C16 Sub-1 scope plan inherited from S48 close:
  - `versioning.py` (~80 LOC), `errors.py` (~150), `contracts.py`
    (~250), `config.py` (~80), `cache_keys.py` (~200), `schema.py`
    (~800).
  - ~1,500 LOC + ~120 tests targeted.
  - Read C16 v0.5 LOCKED spec at
    `02_specs_chronological/S47_C16_specs/spec_C16_v0_5_LOCKED.md`
    + 4 delta files first (Rule 1 spec-first non-negotiable).

### Path Y — Ramalingam returns patches
- Produce v0.4.LOCK-CANDIDATE addressing patches.
- Re-run three-check protocol.
- Loop until LOCK or deferral.

### Path Z — Ramalingam defers LOCK
- C15 stays at v0.3.LOCK-CANDIDATE. Begin C16 build anyway (parallel).
- C16 work may surface additional C15 amendments → process at
  eventual LOCK trigger.

---

## Open standing items NOT closed by Path A

These were filed during S48 critique walks but are **post-LOCK
discipline**, not LOCK-mandatory:

| Item | Owner |
|---|---|
| B-C15-SEMANTIC-VALIDATION-CORPUS | Post-first-deployment |
| B-C15-DEFERRED-CHECK-TELEMETRY | Post-first-deployment |
| B-C15-LAYOUT-DIVERSITY-AUDIT | Pre-C17-integration |
| B-C15-ORCHESTRATOR-PURITY-AUDIT | Annual |
| B-C15-REGISTRY-VISUALIZATION-TOOLING | When registry > 60 checks |
| B-C15-PROFILE-COMPARISON-VIEWS | When profile overrides expand |
| B-C15-UPSTREAM-CONFIDENCE-PROPAGATION | v1.x candidate |
| B-C15-PERFORMANCE-TELEMETRY | When >100ms p99 latency |
| B-C15-EXPLANATION-TEMPLATE-LIBRARY | Pre-deployment polish |
| B-C15-CHECK-INTERACTION-ANNOTATIONS | v0.8-v0.9 polish |
| B-C15-PROFILE-ANTI-STEREOTYPE-AUDIT | Annual |
| B-C15-CONTEXTUAL-WARNING-PRIORITIZATION | Post-first-deployment |
| B-C15-POE-FEEDBACK-LOOP | Multi-year |
| B-C15-PATTERN-SPLIT-LEVEL-DATA | v2 upstream extension |
| B-C15-PATTERN-RITUAL-PROCESSION-DATA | v2 upstream extension |
| B-C15-PATTERN-MULTIGEN-SEGREGATION-DATA | v2 upstream extension |

Full backlog in `04_backlog/S48_critique_walk_backlog_delta.md`.

---

## Memory edits to be aware of

- #14: **BuildemUp LOCK-trigger protocol** — every "lock" invokes
  pre-LOCK processing protocol.

---

## Rules / patterns to honor (every session)

- **Rule 1:** Spec-first. Never code before a LOCKED spec.
- **Rule 7:** Critique handling. Web search mandatory ≥1 per walk;
  grep code for code claims; push back when wrong.
- **Rule 8:** LOCK authority belongs to Ramalingam alone. Never
  self-declare LOCK.
- **Rule 9 / 9.2:** Backlog visibility inside spec § 12; file
  VALID-BUT-BACKLOG without permission.
- **Rule 10 / 10.6 / 10.6.1 / 10.7:** Canonical 10-directory bundle;
  three-check protocol on every handoff; pre-touch inventory before
  claiming credit; first response = status block + plan, not
  assembly.
- **Rule 11:** Vigorous self-analysis + web research on every spec /
  code creation, amendment, AND critique walk.
- **5 Patterns to avoid:** A fix-as-bandage, B building-without-wiring,
  C scores-without-truth, D rules-on-rules, E scope-creep-mid-build.

---

## Test verification (run before claiming any code change)

```bash
cd /home/claude/code/buildemup
python3 -m pytest tests/test_c15/ -q       # must pass: 264
python3 tools/moat_lint.py components/c15  # must PASS (0 violations)
python3 tools/cultural_profile_parity_audit.py  # must show a3_lock_pass: true
```

---

*End of S49 handoff doc.*
