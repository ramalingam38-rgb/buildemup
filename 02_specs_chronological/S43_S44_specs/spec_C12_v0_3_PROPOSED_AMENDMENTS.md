# C12 — SPEC v0.3 PROPOSED — Walk #3 Self-walk

**Component**: 12 (Multi-Floor Placement & Vertical Alignment Engine)

**Status**: v0.3 PROPOSED. **NOT LOCKED.** PENDING Ramalingam adjudication.

**Authority**: S43 Walk #3 self-walk by author (no external reviewer this round). Per Rule 7, self-walks are valid when the previous external walk closed all CRITICAL items; v0.2 closed Items 1, 2, 9 (the three critical reviewer items). Walk #3 focuses on the 7 remaining Q-questions and the 5 self-audit concerns from v0.2 § 0.6.

**Scope**: PATCH-NOW amendment set against v0.2 PROPOSED. Carries the v0.2 amendment doc forward and adds Walk #3 resolutions.

**Authored**: S43, post-cross-component-dependency-LOCK (C8 + C9 amendments LOCKED + coded + tested at S43, all 3059 tests green).

---

## § 0.1 — Cross-component dependencies — RESOLVED

The two routed amendments from v0.2 ARE shipped:

- **B-C8-CORRIDOR-ZONE-CONTRACT** v0.1 LOCKED + coded + 11 tests passing. `CorridorDesignedCandidate.corridor_zones` derived property emits canonical-lex-ASC-sorted `CorridorZone` tuples. Conservative on tapered segments (uses max width).
- **B-C9-ADJACENCY-HINTS** v0.1 LOCKED + coded + 15 tests passing. `FloorRoomBrief.adjacency_hints: tuple[AdjacencyHint, ...] = ()` field with HARD/SOFT typing. Canonical ordering + duplicate detection enforced in `__post_init__`. Default empty tuple preserves byte-identical behaviour for every existing caller.

**Consequence**: v0.2 self-audit concerns #1 and #2 are CLOSED. C12 can safely depend on these upstream surfaces.

**Cross-component note**: B-C11A-CACHE-KEY-BUMP-ADJACENCY remains routed to C11a maintainers (triggered when adjacency_hints are actually populated in production; the empty-tuple default keeps existing caches valid until then).

---

## § 0.2 — Walk #3 PATCH-NOW amendment set

Eight focused amendments resolving 7 open questions + 3 self-audit concerns.

### Amendment v0.3-A1 — Q-1 resolution: CSP fallback opt-in only at v1

**Resolution**: at v1, only `placement_algorithm="slicing_kd_tree"` is shipped as a production path. `"csp_backtrack"` is filed as backlog item `B-C12-CSP-PLACEMENT` (already in v0.1 § 8) with explicit non-v1 scope.

**Rationale**: shipping two algorithms at v1 doubles the test surface, doubles the determinism-validation work, and the slicing-tree is sufficient for n ≤ 15 rooms (typical Indian residential floor). CSP becomes necessary when irregular envelopes enter production — at which point B-C12-IRREGULAR-ENVELOPES + B-C12-CSP-PLACEMENT ship together as a coherent v2.

**Spec change**: `PlacementConfig.placement_algorithm` becomes a `Literal["slicing_kd_tree"]` at v1 (single value, not an enum). `use_csp_fallback_on_slicing_failure` field is REMOVED from v1 (was a Q-1-conditional knob).

**Open question Q-1 RESOLVED.**

---

### Amendment v0.3-A2 — Q-3 resolution: MFRA retry bound stays constant

**Resolution**: `multi_floor_max_realign_iterations = 3` stays a flat constant at v1. Scaling with floor count is filed as `B-C12-ADAPTIVE-RETRY-BUDGET` (already in v0.1 § 8).

**Rationale**: combined with v0.2-A2's monotonic-δ convergence criterion + divergence abort, the retry budget is bounded by *progress* (δ_{n+1} < δ_n required), not just *count*. Flat 3 is fine because the abort triggers earlier on degenerate cases. Adaptive scaling is a performance optimization that needs production data to justify.

**Open question Q-3 RESOLVED.**

---

### Amendment v0.3-A3 — Q-5 partial resolution: HARD-adjacency catalog deferred to C5/KB

**Resolution**: the typing scheme (HARD vs SOFT) is shipped in v0.2-A5 + the C9 amendment. *Which specific adjacencies get HARD vs SOFT* is a domain-knowledge question that belongs in C5 (brief construction) or in KB rules, not in C12.

**Spec change**: C12 v0.3 documents that it CONSUMES `floor_room_brief.adjacency_hints` typed-as-HARD-or-SOFT but does NOT decide which pairings are HARD. The catalog of "kitchen↔dining is HARD in Indian residential" lives upstream.

**Cross-component note (no new backlog)**: C5 spec should document expected adjacency-hint generation policy when adjacency_hints are populated in production. Filed inline as guidance, not as a new B-* entry — this is C5's normal scope, not an amendment.

**Open question Q-5 RESOLVED (sufficient for v1 LOCK).**

---

### Amendment v0.3-A4 — Q-7 resolution: C13 handoff surface verified

**Resolution**: the `SharedEdge` surface (room_a_id, room_b_id, axis, overlap_start_m, overlap_end_m, overlap_length_m, min_required_clear_width_m, doorway_feasible) is sufficient for C13 Door Placement. Verified by walking the C13 prospective contract:

- C13 needs: which pairs of rooms share a wall, on which axis, how much overlap is available, what the door size requirement is.
- C12 emits: exactly that surface, with feasibility pre-validated per Inv 12 + NBC 2016 minima.

No additional fields needed. C13 can stay a thin component (pick door positions on each feasible shared edge per architectural-style rules).

**Spec change**: documents in § 0 the C12→C13 contract: "C13 consumes PlacedCandidate.shared_edges and treats `doorway_feasible == False` edges as not-door-candidates."

**Open question Q-7 RESOLVED.**

---

### Amendment v0.3-A5 — Q-8 resolution: performance budget at 10s single / 30s multi

**Resolution**: v1 ships with `per_candidate_wallclock_seconds = 10.0` (single-floor) and per-multi-floor budget = `10.0 × num_floors + multi_floor_max_realign_iterations × 5.0` (15 + 30 = 45s for typical 3-floor with 3-retry max). These are starting points; production data will calibrate.

**Rationale**: NSGA-II in C11b gives C12 ~20-100 candidates per topology batch. At 10s each that's 3-15 minutes per batch in the worst case. Typical case (Indian residential, n ≤ 15 rooms, slicing-tree O(n log n) typical) should complete in <1s per candidate, leaving headroom.

**Spec change**: `PlacementConfig` adds `multi_floor_wallclock_seconds: float | None = None` — when None (default), derived as the formula above. Otherwise overrides explicitly.

**Open question Q-8 RESOLVED.**

---

### Amendment v0.3-A6 — Q-10 resolution: own cache key, inheriting C11b env tuple

**Resolution**: C12 builds its own cache key as `sha256(c11b_env_fingerprint || c12_config_cache_relevant_fields)`. Cache-key participation: same partition pattern as C11b (cache_relevant=True fields participate; cache_irrelevant=False fields don't).

**Rationale**: piggybacking C11b's cache risks cache-poisoning if C12 logic changes without a C11b version bump. Owning the C12-side key with the env fingerprint as a prefix keeps the dependency explicit.

**Spec change**: adds `C12_VERSION: Final[str] = "v1.0"` constant (parallels C11b's pattern); adds a new `c12_cache_key()` method on `PlacementBatchResult`; adds a partition sentinel test for v0.4 LOCK candidacy. `PlacementConfig` fields get explicit `cache_relevant` metadata flags.

**Open question Q-10 RESOLVED.**

---

### Amendment v0.3-A7 — Q-12 resolution: M8 stays M8 in provenance

**Resolution**: when MFRA absorbs an M8-originated multi-floor candidate, the provenance chain records `OperatorClass.M8_MULTI_FLOOR` faithfully (no re-classification to M0_BASE). Downstream consumers (C13, C14) read the original operator class for diagnostic purposes; they don't need to know whether it's "really" M0 now.

**Rationale**: provenance lossy-ness breaks debugging. Keep the lineage.

**Spec change**: documents in § 3 Phase 2 that `MultiFloorPlacedCandidate.source_multifloor_candidate_signature` preserves the upstream operator class as a substring of the canonical signature.

**Open question Q-12 RESOLVED.**

---

### Amendment v0.3-A8 — Self-audit concerns 3 + 4 resolved

**Self-audit concern #3** (doorway-feasibility room-category enum):

**Resolution**: C12 reads room category strings directly from `FloorRoomBrief` field semantics:
- `bedroom_count`, `bathroom_count` → "bedroom" / "bathroom" categories
- `has_kitchen`, `has_living`, `has_pooja`, `has_utility` → those literal strings as categories
- `other_rooms: tuple[str, ...]` → the literal strings (study, guest, etc. — caller-provided)

NBC-2016 doorway-width derivation uses a fallback chain on these strings. No new shared enum needed at v1; if room-category enum unification ships later (cross-component KB work), the chain converts cleanly.

**Self-audit concern #4** (CANONICAL_FP_PRECISION dependency, do we need C12_PLACEMENT_SCHEMA_VERSION?):

**Resolution**: NOT NEEDED AT v1. C12 doesn't compute a tiebreak_fingerprint (the C11b W6-3 concern doesn't apply). C12 consumes `RefinedCandidate.tiebreak_fingerprint` but doesn't re-hash any geometric structure into a cache key beyond what's in the env fingerprint + config tuple. The CANONICAL_FP_PRECISION dependency is just for coordinate snapping (canonicalization rule #4 in v0.2-A4) — a single-purpose consumption, not a fingerprint contract.

If C12 EVER computes its own geometric fingerprint (e.g., for placed-candidate cache lookup), the W6-3 pattern applies and `C12_PLACEMENT_SCHEMA_VERSION` becomes mandatory. Filed inline as a future guard, not a v1 ship requirement.

**Self-audit concerns 3, 4 CLOSED.**

---

## § 0.3 — Remaining open questions (1 of 12)

| Q | Status | Resolution path |
|---|--------|----------------|
| Q-6 (non-rectangular envelopes) | OPEN | Backlog-only via B-C12-IRREGULAR-ENVELOPES; not a v1 ship requirement. Q-6 stays OPEN at v1 LOCK; v2 spec arc reopens it. |

**Resolved at v0.3: 7 of 12** (Q-1, Q-3, Q-5, Q-7, Q-8, Q-10, Q-12). **Resolved at v0.2: 4 of 12** (Q-2, Q-4, Q-9, Q-11). **Total resolved: 11 of 12.** Q-6 stays OPEN by design (backlog-only).

This is **LOCK candidacy territory.** Per the C11b precedent (v0.7 had ~3 open questions at LOCK; v0.6 had 4-5), one OPEN-but-backlog-only question is well below the LOCK-blocking threshold.

---

## § 0.4 — Self-audit on v0.3 (Rule 11)

Worst issues first:

1. **No new self-audit concerns surfaced this walk.** v0.2 audit issues 1, 2 closed by the C8/C9 amendments landing. Issues 3, 4 closed by Amendment A8. Issue 5 (component-split deferral) stays a stable backlog item; weighted complexity grew to ~52 vs the 100 trigger.

2. **Walk #3 was a self-walk — no external reviewer.** Per Rule 7 guidance, external critique remains valuable BEFORE LOCK. If you want a final external walk on v0.3 PROPOSED before LOCK adjudication, that's Walk #4 territory. Otherwise v0.3 → LOCK is supportable.

3. **Cross-component test coverage of C8/C9 amendments needs integration tests.** The amendment tests cover unit-level behaviour (26 new tests pass). A C12 integration test that builds a CorridorDesignedCandidate, derives zones, builds a FloorRoomBrief with hints, and runs the full place_and_align flow is needed at v1 LOCK to verify the contracts compose. Filed as B-C12-INTEGRATION-AMENDMENT-COVERAGE — a v1-ship blocker.

4. **Rule 11 web-research check**: no new external claims in this walk beyond what's already cited in v0.1 (Knecht & König 2010, Regateiro 2012). NBC 2016 doorway widths verified in v0.2 amendment notes. No re-research needed.

5. **No functional bugs**. Amendments are deltas to scope/configuration/defaults, not algorithm changes.

---

## § 0.5 — Updated complexity budget

| Subsystem | v0.1 | v0.2 | v0.3 |
|---|---|---|---|
| Public types | 6 | 6 | 6 |
| Failure types | 9 | 10 (+ Circulation) | 10 |
| Configuration fields | 10 | 9 (− repair_mode) | 9 |
| Invariants | 10 | 13 (+ Inv 11, 12, 13) | 13 |
| Sub-phases | 5 | 6 (+ Phase 1b) | 6 |
| Open questions | 12 | 7 | 1 |
| Backlog items | 11 | 18 (5 new + 2 routed) | 18 |

**Weighted complexity** (per B-C11B-COMPLEXITY-BUDGET-V2 metric):
- Invariants: 13 × 1 = 13
- Failure types: 10 × 2 = 20
- Replay: 2 × 3 = 6 (env fingerprint + future C12_VERSION)
- Telemetry: 5 × 0.5 = 2.5

**Total: 41.5.** Up from v0.2's 38.5; well under the 100 split-trigger. Reservoir intact.

---

## § 0.6 — Status

**v0.3 PROPOSED.** PENDING Ramalingam LOCK adjudication per Rule 8.

**Distance from v1 LOCK candidacy**: minimal. Remaining work before LOCK:

1. **B-C12-INTEGRATION-AMENDMENT-COVERAGE** integration test suite (~10 tests verifying C8 corridor_zones + C9 adjacency_hints flow into placement correctly). Estimated effort: S (small).
2. **Walk #4 external critique** (optional but recommended): one final external pass on v0.3 PROPOSED catches anything Walk #3 self-walking missed.
3. **Your LOCK signal** OR explicit "Walk #4 first then LOCK" direction.

**Code path** (post-LOCK, S44+):
- C12 v1 implementation: ~25 production files (mirroring C11b's structure), ~150 tests.
- Estimated: 2-3 sessions (S44 + S45 + buffer), comparable to C11b's S42 single-session build.

**Total component status after S43**:
- C1-C10, C11a, C11b ✅ shipped (12 of 17)
- C12 v0.3 PROPOSED (this doc) — closest to v1 LOCK in the unshipped half
- C13-C17 ⏳ pending

---

**End of C12 SPEC v0.3 PROPOSED — Walk #3 self-walk doc.**

**Status reminder**: PENDING Ramalingam LOCK adjudication. C8 + C9 amendments are ALREADY LOCKED + coded + tested. C12 LOCK + code blocked only by your explicit "lock it" signal (or "Walk #4 first").
