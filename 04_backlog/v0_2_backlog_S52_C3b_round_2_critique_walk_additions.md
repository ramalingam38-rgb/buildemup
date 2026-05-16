# Backlog additions — S52 C3b v0.5 BUILD critique walk Round 2

**Source:** Round 2 adversarial critique against C3b v0.5 LOCKED build
**Rule 7 web search:** 1 search executed (event sourcing append-only vs REPLACE)
**Pattern D audit:** 3 items rejected as repeats of S52 Round 1
**Pattern D rate:** 3/15 = 20% (moderate; round still worth doing)
**Web research validation:** Pt 22 web-confirmed; ESAA paper (LLM-agent
   state replay) cited as direct precedent for event-sourced persistence

---

## v1.x candidates (6 new C3b entries)

### B-C3B-LINT-SEVERITY-TIERS
**Origin:** S52 Round 2 critique Pt 17 + Pt 18 (folded)
**Description:** Current advisory_lint is binary (banned → raise). Add a
3-tier system: WARN (logged, allowed), REVIEW_NEEDED (flagged, allowed
with audit log), HARD_BLOCK (raise as today). Replaces some current
HARD_BLOCK substrings with WARN where coercive intent is ambiguous
(e.g., "best" in "best-suited for your priorities").
**Also addresses:** Substring false positives (Pt 18 — token-aware
matching to prevent harmless word collisions like "rejected" matching
"unrejected_status").
**Trigger:** v1.x
**Effort:** M (token-aware matcher + tier enum + 30+ updated lint tests)
**Determinism:** Tier upgrades MUST NOT affect canonical_replay_signature
(text content is part of the sig, but tier classification is not)

### B-C3B-LATENCY-TELEMETRY-FIRST
**Origin:** S52 Round 2 critique Pt 19
**Description:** Before any latency optimization work, instrument the
phase pipeline with per-phase timing. Capture data over real sessions
(launch + first month). Optimization decisions (async precomputation,
incremental graph-diff, preview-fast/verify-later) MUST follow
telemetry, not architectural speculation.
**Rule 11 self-analysis:** Current smoke tests run end-to-end in <100ms.
There is no evidence of a latency problem at v1.0 scale. Building
optimization for hypothetical latency violates Anti-pattern 1
(bandaging without root-cause data) + Anti-pattern 5 (scope-creep).
**Trigger:** instrument before launch; optimize only if data justifies
**Effort:** S (telemetry); M-L (any subsequent optimization, conditional)

### B-C3B-GRADED-TOPOLOGY-DIVERGENCE
**Origin:** S52 Round 2 critique Pt 20
**Description:** Current TopologyInvarianceResult.invariance_preserved
is boolean. Add `topology_divergence_score: float ∈ [0,1]` measuring
graded divergence across 4 continuity dimensions: circulation,
structural, experiential, plumbing. Allow MEDIUM-tier when divergence
score < 0.3 (low-risk perturbation) even if invariance technically
broken. Hard-block remains for score ≥ 0.7.
**Implementation note:** Heuristic per-dimension scoring; no ML
required. Backward-compatible with existing boolean field.
**Trigger:** v1.x
**Effort:** M (4 dimensions × continuity heuristic; ~20 new tests)

### B-C3B-EVENT-SOURCED-PERSISTENCE
**Origin:** S52 Round 2 critique Pt 22
**Web-research validation:** Standard pattern for safety-critical
mutable state. Microsoft Azure Architecture Center, Redpanda guides,
ESAA paper (LLM-agent state replay) all confirm append-only event log
+ periodic snapshot + cryptographic checkpoint hash as the canonical
implementation. R6 byte-equal replay is compatible by construction
(events are the replay source, not derived state).
**Description:** Replace current `INSERT OR REPLACE INTO c3b_sessions`
single-row pattern with:
  1. Append-only `c3b_events` table (event_id, session_id, event_type,
     payload_json, sequence_number, checkpoint_hash)
  2. Periodic snapshot table `c3b_snapshots` for fast-resume
  3. Checkpoint hash chain so corruption is detected at resume time
  4. Replay rebuilds session from events; snapshot just speeds it up
**Why this is real and not paranoia:** Current single-row REPLACE means
a partial write produces a deserializable but semantically corrupt
session that loads silently. Append-only + checkpoint hash makes
corruption detectable.
**Trigger:** v1.x (before launch — housing sessions span days/weeks
across multiple family members)
**Effort:** L — 2-3 sessions for storage rewrite + checkpoint logic
+ migration path from v0.5 schema

### B-C3B-ESCALATION-CONFIRMATION-DIALOG
**Origin:** S52 Round 2 critique Pt 23
**Description:** Currently MutationEnvelope IS the response — user
sees "this is heavy, here's the preview." Add a CONFIRMATION step:
"This change is structural. Would you like to see what it would look
like before deciding?" Uses A6's `speculative_preview_text` as the
opt-in bait. Reduces perceived flow interruption.
**Builds on:** v0.5 A6 (already shipped)
**Trigger:** v1.x
**Effort:** S — extends apply_user_action with a new branch
"confirm_envelope_preview"; preserves R6 determinism

### B-C3B-METADATA-EXTENSION-CHANNEL
**Origin:** S52 Round 2 critique Pt 27
**Description:** Add a single `extension_metadata: Optional[dict[str,
str]] = None` field on TradeoffSession, explicitly excluded from
`canonical_replay_signature` (same R17 pattern as A4 strategic
advisory). Research and experimental modules can attach annotations
without touching invariants.
**Constrained scope:** ONE field, dict-of-strings only, excluded from
canonical sig, included in presentation sig. NOT a general "anything
goes" escape hatch.
**Trigger:** v1.x
**Effort:** S — single field + R-invariant test that the field
doesn't affect canonical sig

---

## v2 candidates (3 new + 1 reframed)

### B-C3B-DYNAMIC-DEPENDENCY-LEARNING
**Origin:** S52 Round 2 critique Pt 24
**Description:** Static TWEAK_CATEGORY_IMPACT_TABLE is auditable and
deterministic. v2 enhancement: learn rerun propagation patterns
statistically from prior sessions. Hybrid implementation: static
table as safety floor; dynamic layer expands the impact set when
evidence supports it.
**Determinism tension:** Same pattern as B-C3B-STRATEGIC-NEGOTIATION-LLM-
PROVIDER from S52 Round 1 — requires relaxed-determinism mode for
the learned layer; static layer remains R6-safe.
**Trigger:** v2 (post-launch — requires telemetry corpus)
**Effort:** XL

### B-C3B-MULTI-STAKEHOLDER-NEGOTIATION
**Origin:** S52 Round 2 critique Pt 30
**Reference:** v0.4 spec § 2.1 already documents the single-linear-
history deferral. This formalizes the v2 work.
**Description:** Multi-branch / parallel-universe / multi-user
negotiation. Stakeholder-aware negotiation graphs tracking preference
ownership, conflict intensity, compromise history. Generate consensus
candidates + compromise Pareto fronts. Collaborative session support.
**Trigger:** v2
**Effort:** XL — major design work; affects schema, persistence,
canonical-sig definition, R16 single-linear-history invariant

### B-C15-FUTURE-ADAPTABILITY-DIMENSION (cross-component)
**Origin:** S52 Round 2 critique Pt 29
**Description:** Add a new C15 lived-quality dimension for "future
adaptability": flexible rooms, partition potential, expansion corridors,
utility access flexibility. C3b would consume the score in tweak
ranking, not own it.
**Component routing:** C15 (the layout-quality scorer), not C3b.
Cross-referenced here so we don't lose the C3b-relevant consumption
path.
**Trigger:** v1.x for C15
**Effort:** M for C15; S for C3b consumption

---

## Items REJECTED as Pattern D repeats

### Pt 16 — Strict determinism vs evolution
Verbatim repeat of S52 Round 1 Pt 10. Addressed in v0.5 via A4 + R17:
strategic_advisory_text excluded from canonical_replay_signature.
This is mechanically the "behaviorally equivalent but internally
evolved" replay the reviewer wants.

### Pt 21 — Pairwise compatibility scaling
Pattern D repeat: at v1.0 ceilings (MAX_TWEAKS_PER_LAYOUT=6,
ITERATION_CAP_DEFAULT=3 post-A8), theoretical max applied tweaks per
session is ~3, giving 3 pairwise checks. The reviewer's "12 tweaks →
dozens of relationships" scenario can't happen. The v2 collaborative-
negotiation case is already filed as B-C3B-MUTATION-CONFLICT-
DEPENDENCY-GRAPH (S52 Round 1).
**Annotation:** existing backlog item augmented with the "conflict-
domain segmentation" framing for v2 design work.

### Pt 25 — Human negotiation irrationality
Pattern D repeat of S52 Round 1 Pt 11. v0.5 A3 ships oscillation
detection (3 patterns: accept-then-reject within 3 turns,
contradictory categories, 3 consecutive rejects). Already addressed.

---

## Items REJECTED as out-of-scope

### Pt 28 — UX over-complexity
This is renderer / UI layer scope (downstream of C3b), not engine
scope. C3b emits structured data; what's user-visible is the
renderer's call. The technical surface (subset_rerun_payload,
compatibility_assertions) is INTERNAL by design — users see
descriptions and advisories only, both R2 lint-clean.

---

## Existing-item annotations (no new backlog entries)

### B-C3B-AESTHETIC-HEURISTIC-CORPUS (annotated)
S52 Round 1 entry. Annotation: add explicit style enumeration for
when v2 corpus build starts:
  - Contemporary
  - Chettinad-inspired
  - Minimalist
  - Luxury modern
  - Tropical
  - Courtyard-centric
Source: S52 Round 2 critique Pt 26 framing.

### B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH (annotated)
v0.4 deferred entry. Annotation: design with explicit conflict-domain
segmentation:
  - Structural conflicts
  - Aesthetic conflicts
  - Circulation conflicts
  - Budget conflicts
  - Services (plumbing/electrical) conflicts
Source: S52 Round 2 critique Pt 21 framing.

---

## Round-2 verdict on BUILD-LOCK status

NONE of the 15 items invalidates the v0.5 BUILD LOCK.

Pattern D rate (3/15 = 20%) is moderate — the round produced 6 net-new
v1.x items, 2 v2 items, and 1 cross-component (C15) item, which is
worthwhile yield. But the 3 verbatim repeats of S52 Round 1 are a
signal that we are approaching diminishing returns; a Round 3 against
v0.5 would likely have a higher repeat rate.

C3b v0.5 remains LOCKED (by Ramalingam delegation per spec § 6).
Build remains shipped. New backlog items documented for v1.x / v2.

**Tally:** 6 v1.x · 2 v2 · 1 cross-component · 3 rejected (Pattern D)
· 1 rejected (out-of-scope) · 2 annotations on existing items
