# BuildemUp Master Doc — Delta v3.9 → v3.10

**Predecessor**: v3.9 (S34 close)
**Successor**: v3.10 (S35 close)
**Authored**: S35 close, post-LOCK directives.

---

## What changed in S35

### Spec arc (9 walks)

S35 was a discussion-only session — no code written. The session produced a 9-walk converging spec arc on two artefacts:

1. **C7 amendment** for B-212 (WallSegment emission): v0.2 PROPOSED → v0.3 → v0.4 → v0.5 LOCK CANDIDATE → v0.6 → v0.7 → **v0.8 LOCKED**.

2. **C10 spec** (Bathroom + Wet-Zone Stack Planner): v0.1 DRAFT → v0.2 PROPOSED → v0.3 → v0.4 → v0.5 → v0.6 → v0.7 → v0.8 → v0.9 → **v1.0 LOCKED**.

3. **2 KBs DRAFTed** to support C10:
   - `kb/plumbing_minimums.json` v1: 7 fixture rows + global slope constants. UPC/IPC sourced. Secondary_consensus pending B-222 primary-source verification.
   - `kb/plumbing_fixture_profiles.json` v2: 5 mapping rows + cross-KB version pinning.

### LOCK declarations at S35 Walk #9 close

Per Ramalingam directive, both specs LOCKED in single declaration:
- C7 amendment v0.8 LOCKED → resolves B-212.
- C10 v1.0 LOCKED → unblocked by B-212 resolution.

### Backlog progression

**Resolved across 9 walks**:
- B-218: RESOLVED-AS-MISFRAMED at S35 Walk #2 audit (grep verified `RoomSizedCandidate.corridor_designed_candidate.oriented_candidate` chain already exists)
- B-221: IMPLEMENTED in C10 v0.6 (RemediationHint dataclass)
- B-239: IMPLEMENTED in C10 v0.8 (cluster spatial-occupancy check via existing `liveability_min_width_m`)
- B-240: IMPLEMENTED in C7 v0.7 (canonical_serialize extracted to `buildemup.utilities`)
- B-243: IMPLEMENTED in C10 v0.9 (mutex DAG validation via `validate_remediation_graph()`)
- B-244: IMPLEMENTED in C10 v0.9 (horizontal-first routing convention)
- B-212: RESOLVED at S35 Walk #9 close (C7 amendment v0.8 LOCKED)

**Newly filed across 9 walks**:
- B-219, B-220 (CORRECTNESS-CRITICAL pre-launch), B-222 (CORRECTNESS-CRITICAL pre-launch), B-223, B-224, B-225, B-226, B-227, B-228, B-229, B-230, B-231, B-232, B-233, B-234a/b, B-235, B-236, B-237, B-238, B-241, B-242, B-245, B-246, B-247.

**Total open at S35 close**: 23 backlog items, 6-tier criticality classification.

### Rule 11 calibration data (8 walks of measurements)

| Walk | My audit | Reviewer | Self-coverage |
|---|---|---|---|
| 1 | 7 | 12 | 58% |
| 2 | 8 | 15 | 40% |
| 3 | 8 | 16 | 31% |
| 4 | 10 | 18 | 33% |
| 5 | 15 | 30 | 43% |
| 6 | 15 | 30 | 43% |
| 7 | (none) | 10 | 60% |
| 8 | 10 | 12 | 33% raw / 58% effective |
| 9 | (none) | 10 | 90% (most items already-filed-as-backlog) |

**4 real bugs caught at audit**: F-v4-4, F-v4-6, F-v6-1, F-v8-6 (the cluster-occupancy timing bug). Rule 11 + Rule 7 dual-audit pattern earned its keep.

### Architectural decisions of note

- **Q19 product-onboarding contract**: C10 default `scoring_profile="neutral"`; product layer prompts for explicit user choice. Avoids hidden Vastu bias while preserving Indian-family target market alignment.
- **Q29 Option B**: v1 LOCK on architectural completeness; B-220 (full hydraulics) + B-222 (KB primary-source verification) are pre-LAUNCH gates, not pre-LOCK gates. Production default `require_verified_plumbing=True`.
- **F-v8-6 fix**: Phase 0.5 + Phase 2.5 split (cluster-occupancy validation against final post-merge cluster composition, not intermediate state).
- **B-247 (NEW at LOCK)**: semantic conflict validation in retry coordinator beyond mutex DAG acyclicity. Post-v1; C2 retry-coordinator domain.

---

## What ships next session

**Build session begins immediately at S36 open.** No further spec walks.

- C7 amendment v0.8 build (~20 tests; unblocks C10 imports)
- C10 v1.0 build (~175 tests across 7 test files; 9 modules; 2 KB JSONs)
- Cumulative target: 2155 + ~20 + ~175 ≈ **2347 passed**

See `NEXT_CLAUDE_HANDOFF.md` for build-session start instructions.

---

## What remains beyond v1 LOCK

**CORRECTNESS-CRITICAL (pre-launch gates, must complete before public ship)**:
- B-220: Full hydraulic primitives + plumbing-engineer review
- B-222: Plumbing KB primary-source verification (NBC 2016 Part 9 + IS 1742 + state-specific Indian codes)

**Other open backlog**: 21 items across INFRASTRUCTURE / OPTIMIZATION / FEATURE / POLYGONAL / RESEARCH tiers. See `04_backlog/buildemup_v2_backlog_S35_walk_9.md`.

---

## Process notes for future sessions

- **Spec arc convergence took 9 walks**. The pattern (Rule 7 critique walk + Rule 11 self-audit per round) plateaued at ~30-60% self-coverage with reviewer consistently complementary.
- **Walks #7-#9 were past honest budget** per Obligation 3 — produced under directive each time. Future LOCK-readiness signals: reviewer count drop, items mostly already-filed-as-backlog, real-bug catch rate near zero.
- **B-237 + B-245** track Rule 11 metric improvements (severity-weighted scoring, ensure reviewer feeding latest spec content).

---

**End of v3.9 → v3.10 delta. S35 close.**
