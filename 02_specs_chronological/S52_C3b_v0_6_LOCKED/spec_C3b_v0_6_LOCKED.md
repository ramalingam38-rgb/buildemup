# C3b v0.6 LOCKED — Spec amendment over v0.5
**Session:** S52 (same session as v0.4→v0.5)
**Predecessor:** v0.5 LOCKED (S52, delegated)
**Adjudication mode:** LOCK delegated to Claude by Ramalingam directive
  ("patch the v1.0-feasible items from this round into a v0.6 build,
  same delegation pattern as v0.5")
**Lock authority:** Rule 8 LOCK-by-explicit-delegation

---

## § 0 — Provenance and scope

This v0.6 amendment integrates 4 items from the S52 Round 2 critique
walk into v1.0 scope per Ramalingam directive. The other 4 Round-2
items remain in v1.x / v2 backlog.

**What v0.6 is:**
- Additive amendments to schema, advisory_lint, phases/severity,
  session_storage
- Two new invariants (R19, R20)
- One re-pattern of existing storage architecture (event-sourced
  augmentation, not replacement of v0.5 single-row store)
- Three patches to existing modules

**What v0.6 is NOT:**
- v0.6 is not v1.0 GA. The increment marks resilience hardening.
- v0.6 is not a relaxation of any v0.4/v0.5 invariant. R6 byte-equal
  replay determinism is preserved; R17 + R18 are unchanged.

---

## § 1 — New v1.0 amendments (4 total)

### B1 — Metadata extension channel
**Was:** B-C3B-METADATA-EXTENSION-CHANNEL (Round 2 Pt 27)

**Spec change:** Add `extension_metadata: Optional[dict[str, str]] = None`
to TradeoffSession. Excluded from canonical_replay_signature (same R17
pattern as A4 strategic advisory). Research and experimental modules
can attach annotations without touching invariants.

**Constraints:**
- Dict-of-strings only (no nested types — keeps serialization simple
  and JSON-stable for the storage layer)
- Each key + value must lint-clean per R2 advisory_lint
- Maximum 32 keys per session (ceiling to prevent abuse)
- Each value ≤ 2048 chars

**Invariant impact:** R6 preserved by exclusion. New R19 enforces the
field's exclusion from canonical_replay_signature.

---

### B2 — Advisory lint severity tiers
**Was:** B-C3B-LINT-SEVERITY-TIERS (Round 2 Pt 17 + Pt 18 folded)

**Problem:** Current advisory_lint is binary — every banned substring
hard-raises. Some banned phrases ("best", "perfect", "wrong") are
genuinely coercive in context but also appear in benign uses
("an option that's well-suited..." vs "best-suited").

**Spec change:** 3-tier lint system:
- HARD_BLOCK — raises AdvisoryLintError immediately
- REVIEW_NEEDED — allows the text, attaches a `LintAuditEntry` to
  audit log; surfaces in test mode for human review
- WARN — allows silently, captured in audit log only

**Token-aware matching:** Banned substrings now require word-boundary
matches (e.g., regex `\brejected\b`) rather than naive substring
search. Prevents "unrejected_status" → "rejected" false positive.

**Tier reassignment from v0.5 (CONSERVATIVE — most stay HARD_BLOCK):**

HARD_BLOCK (coercive intent unambiguous):
  "you must", "you have to", "you should",
  "system decided", "the system has chosen",
  "this is the best choice", "this is the wrong choice",
  "rejected" (in context "tweak rejected"),
  "failed", "tweak failed",
  "score: X/10", "metric: X"  (technical leakage)

REVIEW_NEEDED (context-dependent):
  "best" (alone, not "best choice"),
  "wrong" (alone, not "wrong choice"),
  "perfect"

WARN (mostly historical paranoia, allow with audit):
  bare "should" in non-coercive constructions
    ("you should consider" stays HARD_BLOCK,
     "the kitchen should be roomy" gets WARN)
  bare "must" similar

**v0.6 SHIPS a conservative tier mapping. Tightening happens v1.x
based on advisory_audit_log telemetry.**

**Invariant impact:** R6 preserved — tier resolution is deterministic
function of input text. WARN/REVIEW entries don't affect
canonical_replay_signature; HARD_BLOCK still raises.

---

### B3 — Graded topology divergence
**Was:** B-C3B-GRADED-TOPOLOGY-DIVERGENCE (Round 2 Pt 20)

**Problem:** TopologyInvarianceResult.invariance_preserved is boolean.
Small topology perturbations that preserve usability + construction
viability get forced to HEAVY anyway.

**Spec change:** Add to TopologyInvarianceResult:
- `topology_divergence_score: Optional[float] = None` in [0.0, 1.0]
- `continuity_subscores: Optional[dict[str, float]] = None`
  with keys "circulation", "structural", "experiential", "plumbing"

**Severity routing change in severity.py:**
- If `topology_classification_change=True` AND
  `topology_divergence_score < TOPOLOGY_DIVERGENCE_MEDIUM_CAP` (0.3):
  - Treat as MEDIUM-tier (not HEAVY) — low-risk perturbation
  - Promote the existing `circulation_graph_impact` factor by 1 weight
- Else if `topology_classification_change=True` AND
  `topology_divergence_score >= TOPOLOGY_DIVERGENCE_HEAVY_FLOOR` (0.7):
  - Stay HEAVY (current behavior)
- In-between (0.3 ≤ score < 0.7):
  - Stay HEAVY (current behavior; conservative)

**Backward compat:** Score is Optional. When None, current
boolean-only logic applies. Existing tests unchanged.

**New constants:**
- `TOPOLOGY_DIVERGENCE_MEDIUM_CAP: float = 0.3`
- `TOPOLOGY_DIVERGENCE_HEAVY_FLOOR: float = 0.7`

**Invariant impact:** R6 preserved — score is deterministic from
heuristic. Existing R13 (topology change = HEAVY) is RELAXED to
"topology change with divergence_score ≥ 0.3 = HEAVY". v0.4 callers
that don't populate the score get exact old behavior.

---

### B4 — Event-sourced persistence layer (the big one)
**Was:** B-C3B-EVENT-SOURCED-PERSISTENCE (Round 2 Pt 22)

**Problem:** v0.5 storage uses INSERT OR REPLACE single-row pattern.
Partial writes can produce deserializable but semantically corrupt
sessions that load silently. Web research validates append-only event
sourcing as the canonical safety-critical-state pattern.

**Design decision — augment, don't replace:** v0.6 adds an event log
alongside the v0.5 single-row store. The single-row store remains the
fast-path for reads; the event log is the corruption-detection +
forensic source. Both are written atomically per turn within the same
SQLite WAL transaction.

This is more conservative than full event-sourcing (which would derive
state from events on every read). v0.6 ships:
- New `c3b_events` table (append-only, one row per state transition)
- New `c3b_snapshots` table (periodic full-session-state snapshots)
- Checkpoint hash chain on the event log
- Corruption detection at load time:
  - Compute canonical_replay_signature of loaded session
  - Compute hash chain over the events that produced it
  - Mismatch → CorruptionDetectedError with recovery suggestion

**Schema (v0.6 schema_version = 4):**

```sql
CREATE TABLE c3b_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,        -- 'session_created', 'turn_applied',
                                      -- 'rerun_completed', 'finalized'
    event_payload_json TEXT NOT NULL,
    parent_checkpoint_hash TEXT NOT NULL,
    this_checkpoint_hash TEXT NOT NULL,
    timestamp_offset_ms INTEGER NOT NULL,
    UNIQUE(session_id, sequence_number)
);

CREATE TABLE c3b_snapshots (
    session_id TEXT PRIMARY KEY,
    last_sequence_number INTEGER NOT NULL,
    snapshot_payload_json TEXT NOT NULL,
    snapshot_checkpoint_hash TEXT NOT NULL
);
```

**Checkpoint hash chain:**
```
this_checkpoint_hash = sha256(
    parent_checkpoint_hash + event_id +
    event_type + canonical_payload
)
```
First event in a session has parent = "0" * 64.

**Load-time corruption detection (R20):**
On session load:
1. Read snapshot
2. Read events with sequence_number > snapshot.last_sequence_number
3. Reconstruct expected_checkpoint_hash by walking the event chain
4. Compare against stored this_checkpoint_hash of the latest event
5. Mismatch → raise CorruptionDetectedError

**Backward compat:** v0.5 stored sessions cannot be loaded by v0.6
without migration. v0.6 ships a migration helper that rebuilds the
event log from a v0.5 session as a single "migrated_from_v0_5" event.
v0.5 schema_version=3 sessions raise SessionPersistenceError with a
"run migration" hint.

**Invariant impact:**
- R6 byte-equal replay determinism preserved — events are deterministic
  function of inputs
- R8 schema_version bumps 3 → 4
- New R20 enforces checkpoint-hash chain integrity
- Storage performance: 2 writes per turn (events + snapshot) instead
  of 1. Acceptable given iteration_cap=3 means ≤ 3 turns per session.

**This is the largest change in v0.6. If implementation runs into
unforeseen blockers, v0.6 ships with B1+B2+B3 only and B4 stays in
backlog. Build proceeds in B1→B2→B3→B4 order with checkpoint testing
between each.**

---

## § 2 — New invariants

### R19 — extension_metadata MUST NOT affect canonical_replay_signature

**Statement:** Two TradeoffSession instances differing only in
`extension_metadata` MUST produce identical canonical_replay_signature.

**Enforcement:** cache_keys.py excludes the field. Dedicated test
asserts the invariant.

---

### R20 — Event log checkpoint hash chain integrity

**Statement:** For any session in the c3b_events table, the
this_checkpoint_hash of every event MUST equal the deterministic
hash computed from its parent_checkpoint_hash + event_id + event_type
+ canonical event_payload. Load-time check refuses sessions whose
hash chain is broken.

**Enforcement:** session_storage._verify_event_chain raises
CorruptionDetectedError on hash mismatch. Dedicated tests verify
chain integrity and corruption detection.

---

## § 3 — Backward compatibility statement

v0.5 → v0.6:
- TradeoffSession gains 1 Optional field (extension_metadata)
- TopologyInvarianceResult gains 2 Optional fields (divergence + subscores)
- advisory_lint API gains tier-aware variants; original API preserved
  as `is_advisory_clean(text)` returning HARD_BLOCK | (REVIEW_NEEDED |
  WARN) ⇒ True
- Storage: schema_version 3 → 4. v0.5 sessions need migration helper.

**C3B_SESSION_SCHEMA_VERSION bumps from 3 → 4.**

---

## § 4 — Test parity requirements

v0.6 BUILD must include:
- B1: 4 tests (default None, max 32 keys, max 2048 chars, R19 invariant)
- B2: 8 tests (HARD_BLOCK passthrough, REVIEW_NEEDED audit, WARN audit,
  word-boundary matching, "rejected" in compound word doesn't fire,
  every existing description template still lint-clean at HARD_BLOCK
  level)
- B3: 6 tests (None score → boolean fallback, low divergence → MEDIUM,
  mid divergence → HEAVY, high divergence → HEAVY, subscores
  validation, severity context integration)
- B4: 10 tests (event-write on turn, snapshot-write at iteration_cap,
  chain integrity, load-time corruption detection, recovery
  suggestion, v0.5 migration, schema_version=3 rejection with
  hint, snapshot fast-path, replay determinism over storage roundtrip,
  CorruptionDetectedError surface)

**Target additions:** ~28 new tests. Expected total: 415 + 28 ≈ 443.

---

## § 5 — What stays in backlog after v0.6

Not promoted in this round:
- B-C3B-LATENCY-TELEMETRY-FIRST (v1.x — telemetry-dependent)
- B-C3B-ESCALATION-CONFIRMATION-DIALOG (v1.x — small but better with
  UI design context we don't have)
- B-C3B-DYNAMIC-DEPENDENCY-LEARNING (v2)
- B-C3B-MULTI-STAKEHOLDER-NEGOTIATION (v2)
- B-C15-FUTURE-ADAPTABILITY-DIMENSION (cross-component, C15 scope)

All v1.x items from S52 Round 1 that didn't make v0.5 (fatigue
telemetry, dimension delta calibration, emotional layout full corpus)
remain in backlog. v0.5 partial implementations stay as documented.

---

## § 6 — LOCK declaration

**v0.6 LOCKED by Ramalingam directive S52** ("patch the v1.0-feasible
items from this round into a v0.6 build, same delegation pattern as
v0.5").

Audit trail preserved here. Ramalingam retains the right to declare
this LOCK invalid and re-open v0.6 PROPOSED.

**Implementation note:** Build proceeds in B1→B2→B3→B4 order. If B4
turns out to be blocked, v0.6 ships with B1+B2+B3 and B4 stays in
backlog. This is documented now to avoid mid-build scope ambiguity.
