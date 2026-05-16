# BuildemUp v0.2 Backlog — S35 Walk #9 Close

**Status**: Final at S35 close. Both specs LOCKED.
**Total open**: 23.
**Total resolved across spec arc**: 7.

---

## CORRECTNESS-CRITICAL (pre-launch gates) — 2

| ID | Description | Origin | Effort |
|---|---|---|---|
| **B-220** | Full hydraulic primitives (DFU loading, slope feasibility, vent stack compatibility, sizing). Plumbing-engineer review pass. **Pre-launch hard gate.** | S35 Walk #2 | L |
| **B-222** | Plumbing KB primary-source verification against NBC 2016 Part 9 + IS 1742 + state-specific Indian codes. Replace `secondary_consensus`/`secondary_unverified` source-confidence flags with `primary_verified`. **Pre-launch hard gate.** | S35 Walk #2 | M |

Production default: `WetZonePlanConfig.require_verified_plumbing=True` until both complete.

---

## INFRASTRUCTURE (post-v1 platform work) — 9

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-219 | Deterministic-replay tests with hash snapshots; calibrate Q24/Q31/Q37/Q45 ad-hoc thresholds | S35 Walk #2 | XS |
| B-224 | `RegulatoryConfidenceFramework` unified verification governance across NBC, plumbing, fire code, Vastu | S35 Walk #3 | L |
| B-234a | Plumbing-KB registry validator tooling (auto-detect orphan refs, schema migration tests) | S35 Walk #4 → split at #6 | S |
| B-234b | Semantic-integrity validator depth (cross-source consistency vs NBC/IS, beyond plausible-range checks) | S35 Walk #6 | M |
| B-236 | `scoring_profile_explicitly_set: bool` telemetry flag (production observability for Q19 product-onboarding contract compliance) | S35 Walk #5 (F-v6-6) | XS |
| B-237 | Test-suite modernisation: Hypothesis property-based testing, scenario generators, replay snapshot compression, debug-mode runtime shuffle, **cross-platform CI replay matrix** (Walk #9 #6 scope expansion) | S35 Walk #6 + #9 | M |
| B-238 | Independent architect review (separate from B-220 plumbing-engineer) for cultural rules + spatial logic + adversarial floor plans | S35 Walk #6 (meta) | M |
| B-241 | CI lint rule: forbid `.wall_segments` direct iteration outside snapshot/test modules | S35 Walk #8 | XS |
| B-245 | Rule 11 maturity-weighted scoring extension. Track architectural ambiguity / correctness-critical-unresolved / invariant instability / replay nondeterminism. Master_doc work, not spec. | S35 Walk #8 (meta) | XS |

---

## OPTIMIZATION (post-ship tuning) — 4

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-213 | Adaptive `max_risers` formula based on envelope width + wet-room count | S35 Walk #1 | S |
| B-216 | `adjacency_threshold_m` default tuning post-C11 placement data | S35 Walk #2 | XS |
| B-223 | Performance hardening: memoised score cache, complexity metrics in provenance, `max_wall_assignments_per_cluster` | S35 Walk #3 | M |
| B-228 | Adaptive `wall_reuse_penalty` proportional to wall occupancy ratio + plumbing load benefit | S35 Walk #4 | S |

---

## FEATURE (v2+) — 5

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-225 | Multi-anchor RiserGroup support — schema forward-compat shipped at C10 v0.7 (`anchors: tuple[RiserAnchor, ...]` w/ v1 invariant len==1); v2 work removes invariant + multi-anchor placement logic | S35 Walk #3 → #6 (effort reduced) | S |
| B-227 | `kb/plumbing_fixture_profiles.json` extension for luxury bathrooms (bidet, dual-sink kitchens, modern utility) | S35 Walk #4 | XS |
| B-229 | DFU-aware wall capacity (interim cluster-capacity-weight shipped at C10 v0.8; full DFU = v2 with B-220 plumbing-engineer review) | S35 Walk #4 → #7 (interim shipped) | M |
| B-232 | Probable-fixture-zone heuristic — KB or convention for fixture-zone-within-room (dual-bound shipped at v0.8 + per-fixture factors shipped at v0.9; calibration future) | S35 Walk #5 → #7/#8 (partial shipped) | M |
| **B-246** | Move `LIKELY_BOUND_FACTORS_BY_FIXTURE` from C10 module constant to plumbing_minimums.json KB (Q45 deferral) | S35 Walk #8 (Q45 at LOCK) | XS |

---

## POLYGONAL (B-066 era) — 5

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-217 | Three-tier wall classification (EXTERNAL / SERVICE_CORE / INTERIOR); SERVICE_CORE promoted to v2 | S35 Walk #2 → #3 | M |
| B-226 | `acceptable_wall_sets` polygonal pruning (dominance, axis filter, max cap) | S35 Walk #3 | S |
| B-231 | Wall lookup O(1) optimisation (precomputed dict) | S35 Walk #5 | XS |
| B-235 | WallTag domain split (topology / structural / placement) | S35 Walk #5 | S |
| B-242 | `WallSegment.usable_wall_spans` to model wall fragmentation (doors, windows, shafts) | S35 Walk #8 | M |

---

## RESEARCH (v3+) — 2

| ID | Description | Origin | Effort |
|---|---|---|---|
| B-230 | Full MCS/MUS infeasibility diagnosis engine — research-grade implementation per IIS / QuickXplain literature | S35 Walk #4 | XL |
| B-233 | Proper orthogonal routing graph for `symbolic_bend_estimate` — wall penetrations, vertical offsets, fixture orientation; supersedes v1 horizontal-first heuristic | S35 Walk #5 → #8 | L |

---

## NEW at LOCK (S35 Walk #9) — 1

| ID | Description | Origin | Effort |
|---|---|---|---|
| **B-247** | Semantic conflict validation for `RemediationHint` retry orchestration: beyond v1.0's mutex DAG acyclicity check, ensure jointly-applied hints don't create downstream infeasibility (transactional simulation + rollback-safe plans). C2 retry-coordinator domain. | S35 Walk #9 reviewer #7 | M |

---

## DORMANT — 2

| ID | Description | Status |
|---|---|---|
| B-214 | Per-bathroom subtype propagation through C10 | Depends on B-208 (not yet active) |
| B-215 | Refine "minimum stack-fit length" (v1: 1.5m heuristic) | Rolls into B-220 plumbing-engineer review |

---

## RESOLVED across spec arc — 7

| ID | Description | Resolution |
|---|---|---|
| B-218 | C8 oriented_candidate ref preservation | RESOLVED-AS-MISFRAMED at S35 Walk #2 audit (grep verified embedded chain already exists) |
| B-221 | Structured `RemediationHint` for retry orchestration | IMPLEMENTED in C10 v0.6 |
| B-239 | Cluster spatial-occupancy check via `liveability_min_width_m` | IMPLEMENTED in C10 v0.8 (zero C9 amendment cost) |
| B-240 | Extract `canonical_serialize` to `buildemup.utilities` shared module | IMPLEMENTED in C7 amendment v0.7 |
| B-243 | Mutex DAG validation via `validate_remediation_graph()` | IMPLEMENTED in C10 v0.9 |
| B-244 | Document v1 symbolic_bend_estimate routing convention (horizontal-first) | IMPLEMENTED in C10 v0.9 |
| **B-212** | C7 WallSegment emission (C10 LOCK BLOCKER) | **RESOLVED at S35 Walk #9 close (C7 amendment v0.8 LOCKED)** |

---

## Status summary

| Tier | Open |
|---|---|
| CORRECTNESS-CRITICAL | 2 |
| INFRASTRUCTURE | 9 |
| OPTIMIZATION | 4 |
| FEATURE | 5 |
| POLYGONAL | 5 |
| RESEARCH | 2 |
| LOCK-NEW (B-247) | 1 |
| DORMANT | 2 |

**Total open**: 23 (excluding 2 dormant). With dormants: 25.
**Total resolved across S35 spec arc**: 7.

**Pre-launch gate status**: 2 CORRECTNESS-CRITICAL items (B-220, B-222) must complete before public ship. v1 LOCK proceeded without them per Q29 Option B.

---

**End of backlog v0.2 — S35 Walk #9 close. Both specs LOCKED.**
