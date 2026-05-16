# C3b v0.5 LOCKED — Spec amendment over v0.4
**Session:** S52
**Predecessor:** v0.4 LOCKED at S50
**Adjudication mode:** LOCK delegated to Claude by Ramalingam directive
  ("when you make spec amendments consider it locked and build the code")
**Lock authority:** Rule 8 LOCK-by-explicit-delegation (not self-declaration)

---

## § 0 — Provenance and scope

This v0.5 amendment integrates 9 items routed from the S52 critique walk
into v1.0 scope per Ramalingam directive ("go with b") expanding v1.0
from a minimal post-LOCK build to a v1.0-with-resilience build.

**What v0.5 is NOT:**
- v0.5 is not v1.1. The version increment marks scope expansion within
  v1.0, not a maturity bump.
- v0.5 is not invalidation of v0.4. Every v0.4 invariant (R1–R16),
  contract, and phase signature is preserved.
- v0.5 does not relax R6 byte-equal replay determinism in the default
  path. The strategic-layer hook is OPT-IN and gated by config.

**What v0.5 IS:**
- Additive amendments to phases ε, ζ, and orchestrator
- Two new invariants (R17, R18)
- One new optional config field (`strategic_mode`)
- Three patches to existing modules (versioning, alpha, severity)
- Backlog promotion of 8 v1.x items + 1 v2 item with bifurcation

---

## § 1 — New v1.0 amendments (9 total)

### A1 — Semantic compatibility contracts (was B-C3B-SEMANTIC-COMPATIBILITY-CONTRACTS)

**Replaces:** exact-equality version pin in `check_upstream_versions`
**New behavior:** declare `MIN_C{n}_VERSION` per upstream. Acceptance is
"observed >= min". UpstreamSchemaDriftError fires only when observed is
*below* min OR when a known-incompatible version is detected.

**New constants in versioning.py:**
- `MIN_C15_VERSION = "v1.0.LOCKED"` (acceptance floor)
- `MIN_C16_VERSION = "v1.2.LOCKED"`
- `KNOWN_INCOMPATIBLE_C15_VERSIONS = ()` (placeholder for future)
- `EXPECTED_C15_VERSION` kept as alias for backward-compat

**Phase α change:**
`check_upstream_versions` uses `_version_at_or_above(observed, MIN_C15_VERSION)`
helper. The helper does lexicographic parsing of version strings of the
form `v<major>.<minor>.<status>`.

**Invariant impact:** R6 byte-equal replay determinism is preserved — the
minimum-version check produces the same boolean output for the same
observed input.

---

### A2 — Periodic full-coherence recheck (was B-C3B-PERIODIC-FULL-COHERENCE-RECHECK)

**New:** after every N MEDIUM tweaks (default N=3), the orchestrator
forces a full upstream recompute rather than a subset rerun.

**New config field:** `full_recompute_threshold: int = 3`
  (hard floor 1, hard ceiling = iteration_cap; defaults to 3)
**New session field:** `medium_tweak_count_since_full_recompute: int = 0`
**New advisory_kind:** `"full_coherence_recheck_triggered"`

**Phase ε change:**
When `_apply_medium_tweak_emit_rerun` runs, increment
`medium_tweak_count_since_full_recompute`. When it crosses
`full_recompute_threshold`, the emitted SubsetRerunRequest is upgraded
to mark all downstream components for rerun (functionally identical to
the rerun the orchestrator would request after a full re-layout).

**Invariant impact:** R6 preserved — threshold check is deterministic.
R14 regression detection still fires after the recheck.

**Phase ζ change:** The full-recompute counter resets when
`resolved_selection` is built.

---

### A3 — Oscillation detection and summary (was B-C3B-OSCILLATION-DETECTION-AND-SUMMARY)

**New:** Phase ε detects oscillation patterns in `session_history`.

**Pattern detection rules:**
1. Accept-then-reject of the SAME tweak_id within 3 turns
2. Accept tweak of category X, then accept tweak of contradictory
   category Y, where (X,Y) ∈ KNOWN_CONTRADICTORY_PAIRS
3. Reject 3 consecutive tweaks of the same category

**Known contradictory pairs (v1.0 seed list):**
```
("balcony_add", "balcony_remove")
("finish_upgrade", "finish_downgrade")
("kitchen_reorient", "kitchen_reorient")   # different reorient on same room
```

**New AdvisoryFlag.kind:** `"oscillation_pattern_detected"`
**Advisory note template:** "You appear to be balancing X vs Y. You could
take a moment to decide which matters more and finalize on that priority."

**Invariant impact:** R6 preserved — pattern detection is deterministic
function of session_history.

---

### A4 — Strategic negotiation layer hook (was B-C3B-STRATEGIC-NEGOTIATION-LAYER, v2 → v1.0 OPT-IN)

**This is the only item with an R6 tension. Resolution:**

**v0.5 ships a strategic-mode HOOK, not the layer itself.** The hook is:
- A new `strategic_mode: Literal["off", "advisory_only"] = "off"` config
  field
- A new optional `strategic_advisory_text: Optional[str]` field on
  SessionTurn (None when strategic_mode == "off")
- When `strategic_mode == "advisory_only"`, an extension point
  (`strategic_advisory_provider: Optional[Callable]` on
  C3bRuntimeConfig) can populate `strategic_advisory_text` per turn.
  The advisory is INFORMATIONAL ONLY — it does NOT alter session state,
  does NOT affect canonical_replay_signature, does NOT change Phase ε
  branching.

**R6 preservation rule:**
- `canonical_replay_signature` MUST NOT include
  `strategic_advisory_text` in its input
- Tests verify: two sessions with different strategic_advisory_text
  values but otherwise identical state produce identical
  canonical_replay_signature
- `presentation_signature` MAY include it (presentation is allowed to
  vary by render-time additions)

**v0.5 ships the hook + invariant tests. The actual LLM-driven strategic
advisory provider is still v2 backlog.**

**Invariant impact:** R6 explicitly preserved by hook contract. New R17
invariant added below to enforce.

---

### A5 — Continuous dimension delta check (was B-C3B-CONTINUOUS-DIMENSION-DELTA-CHECK)

**Problem:** R14 catches CRITICAL-tier *transitions* but misses gradual
degradation that stays under CRITICAL severity.

**v0.5 amendment:** R14 is augmented with a complementary numeric-delta
check WHERE C15 provides per-dimension scores. If C15 does not provide
them (v1.0 baseline), the check no-ops gracefully.

**Implementation:**
- `complete_subset_rerun` checks if `post_pr` has a
  `dimension_score_snapshot` attribute (attribute lookup, not
  attribute requirement — defensive)
- If yes, computes per-dimension delta vs `pre_pr`. Any dimension
  degrading by ≥ `DIMENSION_DEGRADATION_THRESHOLD_PCT` (default 15%)
  fires a `"dimension_score_regression"` AdvisoryFlag
- If C15 doesn't emit scores, the check is a no-op

**New constant:** `DIMENSION_DEGRADATION_THRESHOLD_PCT = 15.0`
**New AdvisoryFlag.kind:** `"dimension_score_regression"`

**Backward compat:** zero — C15 v1.0 doesn't emit these, so the check
no-ops. C15 v1.1+ can ship them and C3b picks them up automatically.

---

### A6 — Speculative preview mode (was B-C3B-SPECULATIVE-PREVIEW-MODE)

**Problem:** HEAVY tweaks immediately surface as MutationEnvelope with
"step back" framing. Some users would prefer to see what the change
*would* look like before committing.

**v0.5 amendment:** MutationEnvelope gains an optional
`speculative_preview_text: Optional[str] = None` field. Phase β
populates it with a brief plain-English description of what the
restructured layout would look like at a topology/structural level.

**Field is OPTIONAL** — if Phase β can't synthesize a meaningful
preview, leaves it None. No new pipeline infrastructure needed; the
preview is text-based for v1.0.

**Phase β change:** when MutationEnvelope is built, populate
`speculative_preview_text` with a generated description.

**Invariant impact:** R6 preserved — preview text is deterministic
function of inputs.

---

### A7 — Emotional layout heuristics (was B-C3B-EMOTIONAL-LAYOUT-HEURISTICS, partial v1.0)

**v0.5 ships seed heuristics, not full architect corpus.** The full
corpus stays in v1.x.

**v0.5 amendment:** Three coarse heuristic scores added to ComfortImpact:
- `perceived_spaciousness: Optional[float]` (0.0–1.0)
- `arrival_impression: Optional[float]` (0.0–1.0)
- `family_gathering_comfort: Optional[float]` (0.0–1.0)

All Optional → backward-compat. Phase β heuristics that touch these
populate them; others leave None. Used as TIE-BREAK signal in priority
sort.

---

### A8 — Fatigue brake (was B-C3B-FATIGUE-TELEMETRY-AND-COMPRESSION, partial v1.0)

**v0.5 ships the cap-lowering option, not the telemetry.** Telemetry
stays v1.x backlog. Cap-lowering ships now.

**v0.5 amendment:**
- `ITERATION_CAP_DEFAULT` changes from 5 → 3
- `ITERATION_CAP_HARD` stays 7
- Existing iteration_cap_warning_nudge AdvisoryFlag wording softened to
  surface earlier ("You've made good progress — you could finalize now
  or continue tweaking")

**Migration:** Existing tests use `C3bRuntimeConfig()` defaults; the
default changes from 5 to 3. Tests that need 5 must override explicitly.

---

### A9 — Experiential diversity floor (was B-C3B-EXPERIENTIAL-DIVERSITY-FLOORS, partial v1.0)

**v0.5 ships a coarse experiential floor, not ML embeddings.** ML
embeddings stay v2.

**v0.5 amendment:** `check_pareto_diversity` gains a fourth check —
"functional-archetype diversity":
- Count distinct top-level archetypes across the 3 layouts
- If fewer than 2 distinct archetypes represented (e.g., all 3 layouts
  are "cost_efficient" variants), trip the diversity floor

**Phase α change:** archetype-diversity floor is checked alongside
existing cost-spread and sqft-spread floors. Any one floor passing =
diversity OK.

---

## § 2 — New invariants

### R17 — Strategic advisory text MUST NOT affect canonical_replay_signature

**Statement:** Two TradeoffSession instances that are identical except
for `strategic_advisory_text` on any SessionTurn MUST produce identical
`canonical_replay_signature`.

**Enforcement:** `compute_canonical_replay_signature` explicitly
excludes `strategic_advisory_text` from the canonicalized input.
A dedicated test asserts this.

**Origin:** A4 strategic-layer hook + R6 byte-equal replay preservation.

---

### R18 — Full-recompute counter resets on resolution

**Statement:** When `current_status` transitions to
`resolved_selection_ready` or `abandoned_no_tweaks`,
`medium_tweak_count_since_full_recompute` MUST be set to 0.

**Enforcement:** Phase ζ sets the counter to 0 when constructing the
resolved_selection. Phase ε resets it on abandoned_session and
kicked_back_to_c3a branches.

**Origin:** A2 periodic full-coherence recheck.

---

## § 3 — Backward compatibility statement

v0.4 → v0.5 amendments are **strictly additive** in the data schema
direction:
- TradeoffSession gains 2 fields (both with defaults)
- ComfortImpact gains 3 Optional fields
- MutationEnvelope gains 1 Optional field
- SessionTurn gains 1 Optional field
- C3bRuntimeConfig gains 2 fields (both with defaults)

All v0.4-shaped stored sessions remain deserializable.
**C3B_SESSION_SCHEMA_VERSION bumps from 2 → 3.**
session_storage.py rejects v0.4 stored sessions at load (per Rule 11
self-analysis pt 5 in v0.4 session_storage). Caller migrates or aborts.

---

## § 4 — Test parity requirements

v0.5 BUILD must include:
- A1: 4 tests (min-version accepts, accepts-equal, rejects-below,
  known-incompatible)
- A2: 5 tests (threshold counter, threshold crossing, advisory fires,
  reset on resolve, reset on abandon)
- A3: 6 tests (accept-then-reject pattern, contradictory-pair pattern,
  3-consecutive-reject pattern, advisory text, no false positive on
  clean history)
- A4: 4 tests (strategic_mode off no-op, advisory_only populates text,
  R17 invariant test, R17 test under persistence roundtrip)
- A5: 3 tests (no-score graceful no-op, regression detected, threshold
  boundary)
- A6: 2 tests (preview text populated for HEAVY, optional preserved when
  None)
- A7: 3 tests (Optional fields default None, populated when heuristic
  fires, tie-break ordering)
- A8: 2 tests (default cap is 3, advisory text softer wording)
- A9: 3 tests (single-archetype trips floor, two-archetype passes,
  cross-check with existing cost/sqft floors)

**Target additions:** ~32 new tests. Expected total: 382 + 32 ≈ 414.

---

## § 5 — What stays in backlog after v0.5

- `B-C3B-FATIGUE-TELEMETRY` (cap-lowering done, telemetry pending) — v1.x
- `B-C3B-EMOTIONAL-LAYOUT-FULL-CORPUS` (3 seed heuristics done, full
  architect corpus pending) — v1.x
- `B-C3B-EXPERIENTIAL-DIVERSITY-ML-EMBEDDINGS` (coarse floor done, ML
  embeddings pending) — v2
- `B-C3B-STRATEGIC-NEGOTIATION-LLM-PROVIDER` (hook shipped, LLM provider
  pending) — v2
- `B-C3B-AESTHETIC-HEURISTIC-CORPUS` (untouched) — v2

---

## § 6 — LOCK declaration

**v0.5 LOCKED by Ramalingam directive S52** ("when you make spec
amendments consider it locked").

This is NOT Claude self-declaring LOCK. This is Claude executing a LOCK
on Ramalingam's behalf under explicit delegation, with the full record
of what was changed and why preserved here.

Per Rule 8 footnote: such delegation is auditable. Ramalingam retains
the right to declare this LOCK invalid and re-open v0.5 PROPOSED for
re-adjudication.
