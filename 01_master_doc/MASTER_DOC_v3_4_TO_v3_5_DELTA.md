# Master Design Narrative — v3.4 → v3.5 DELTA

**Predecessor**: `MASTER_DOC_v3_3_TO_v3_4_DELTA.md` (S28 close).
**Authoring session**: S30.
**Companion files**: `MASTER_DESIGN_NARRATIVE_v2_9.md` (last consolidated narrative); v3.0–v3.4 deltas (prior sessions).
**Reason for delta**: S30 SHIPPED C5 v1.0 + LOCKED C6 v0.5. Two components in one session — significant pipeline progress.

---

## § Δ.1 — Pipeline status: v3.4 (S28 close) → v3.5 (S30 close)

### At v3.4 (S28 close)

```
SHIPPED   (5 of 17): C1, C2, C3a, C4, C7
SPEC LOCKED (0):     —
PENDING   (12 of 17): C5 (next), C6, C8..C16, C3b
```

### At v3.5 (S30 close)

```
SHIPPED   (6 of 17): C1, C2, C3a, C4, C5, C7      ← +C5 (S30)
SPEC LOCKED (1 of 17): C6 v0.5 LOCKED — build-ready (D-066 Step 6 next)
PENDING   (10 of 17): C8..C16, C3b
```

**Net change**: +1 SHIPPED (C5), +1 LOCKED (C6), -2 PENDING.

---

## § Δ.2 — Era 2 layout pipeline: detailed component status

| Component | At v3.4 | At v3.5 |
|---|---|---|
| C4 Plot Analysis | SHIPPED v1.1 (S28) | unchanged |
| **C5 Topology Selector** | not started | **SHIPPED v1.0 (S30)** ✓ |
| **C6 Orientation Priority** | not started | **SPEC v0.5 LOCKED (S30)** ✓ |
| C8 Corridor Designer | not started | not started |
| C9..C16 | not started | not started |

---

## § Δ.3 — S30 narrative arc

### Pre-session state

S29 closed with C4 v1.1 SHIPPED and C5 v0.9 LOCKED (build-ready). The handoff artifact (`buildemup_handoff_v6_session_29.zip`) carried the locked spec, the pristine upstream codebase, and a full critique-walk record from C5's spec lineage.

### S30 phase 1 — C5 code build (D-066 Step 6)

Built C5 against v0.9 LOCKED spec following the D-066 build cycle. Three Q&A items resolved at session start (per-topology bedroom-fit table; runs_along convention for COURTYARD; test-fixture re-export pattern). Then implementation:

- 7 source files: `domain/floor_brief.py`, `components/c05/{__init__, schema, decision_table, scorers, zone_bands, select}.py`
- 7 test files: `test_c5_{select_topology, decision_table, scorers, zone_bands, immutability, failure_modes, stability}.py`
- 1 fixture file: `tests/validation/_c5_fixtures.py`
- Pre-existing placeholder test (`test_c5_consumes_plot_analysis.py`) auto-activated when `c05/__init__.py` landed

End-to-end smoke test passed at first run; iterative test debugging yielded final result **1539 passed / 1 skipped** (baseline was 1419/2 → C5 contributes +120 passing, -1 skipped).

### S30 phase 2 — C5 critique walk

Reviewer-supplied 10-item critique on C5 v0.9 + the consolidated `.py`. Walk verdicts:

- **5 SPEC-AMENDMENTS**: items requiring code changes pre-SHIP (Vastu 8-dir rule, global enumeration, entry-on-road hardening, DINING split, FULL hard-fail) — wait no, those were C6 walks. C5 walk: 0 amendments, 5 misframed pushbacks (bedroom overlap, corridor abstraction, blending dilution, tie-break, confidence binary), 5 backlog (incl. 2 new B-094, B-095).
- **C5 v1.0 SHIPPED** with consolidated `.py` review delivered.

### S30 phase 3 — C6 design from scratch

Three-question framing dialogue (Q1 meaning, Q2 Vastu scope, Q3 cardinality). Web research confirmed:
- "Meaning B" (functional priority per direction) is the right scope vs. "Meaning A" (massing rotation)
- C1's `VastuTier.{OFF, PARTIAL, FULL}` is the authoritative opt-in contract
- One refined candidate per C5 candidate (cardinality preservation)

Authored `C6_SPEC_v0_1_DRAFT.md` against this framing — 16 sections, 406 lines, 4 backlog items (B-097..B-100).

### S30 phase 4 — Four critique walks on C6 (v0.1 → v0.5)

| Walk | Drove | Amendments | New B-NNNs | Misframed |
|---|---|---|---|---|
| #1 (v0.1 → v0.2) | 12-item critique | 6 | 5 (B-101..B-105) | 3 |
| #2 (v0.2 → v0.3) | 12-item critique | 6 (incl. 1 reversal: DINING) | 0 | 3 |
| #3 (v0.3 → v0.4) | 12-item critique | 3 | 1 (B-106) | 8 |
| #4 (v0.4 → v0.5) | 10-item critique | 1 (signal_dominance) | 0 | 9 |

Trajectory: amendments halved each round; new B-NNNs collapsed; same items re-raised across multiple rounds without new evidence (confirmed convergence).

### S30 phase 5 — LOCK + handoff

C6 v0.5 LOCKED at S30 close. This handoff bundle (`buildemup_handoff_v7_session_30.zip`) packages the SHIPPED C5 + the LOCKED C6 spec for next session's build cycle.

---

## § Δ.4 — Architectural decisions of note

### C5 (cumulative through SHIP)

- 7-criterion weighted scoring (width_fit, bedroom_fit, open_side_count, climate_fit, corner_fit, aspect_ratio_fit, corridor_overhead)
- Multi-branch prior blending with v0.7 normalization fix
- Per-topology min bedrooms (STRIP=1, CS=2, L_SHAPE=2, COURTYARD=3)
- Smooth ramps for all four thresholds (wide / narrow / large_w / large_d)
- Top always returned; secondaries gated by 0.30 threshold + 0.10/0.15 relative deltas
- Tie-break secondary key: `-corridor_overhead.raw` (higher raw = less overhead)

### C6 (LOCKED at v0.5)

- Refines each C5 candidate's `zone_bands` via global permutation enumeration (≤ 24 non-COURTYARD, ≤ 256 COURTYARD)
- Three contributing signals (sun, wind, vastu); road as hard constraint not soft signal
- 8-direction internal Vastu computation with weighted-average aggregation to 4-direction output (cardinal=1.0, intercardinals=0.5 each, normalized by sum 2.0)
- 5-tier deterministic tie-break (total_score → Hamming-to-seed → LIVING → BEDROOM → lex)
- Margin-clamped confidence with MIN_DENOM=0.1
- `signal_dominance` interpretability layer (max/sum of weights_raw, threshold 0.45 for "dominant" classification)
- FULL Vastu tier hard-fails until B-099 KB populated (4-round-reaffirmed design decision)

---

## § Δ.5 — Backlog state

```
At v3.4 (S28 close)  : up to B-093 (across all backlog files)
At v3.5 (S30 close)  : up to B-106 (+ 13 new in S30: B-094 → B-106)
```

13 new items: 2 from C5 walk (B-094, B-095), 5 from C6 v0.1 (B-096..B-100), 5 from C6 v0.2 walk (B-101..B-105), 0 from C6 v0.3 walk, 1 from C6 v0.4 walk (B-106), 0 from C6 v0.5 walk.

**One hard-blocking item**: B-099 (FULL Vastu KB). All others deferred-but-non-blocking.

---

## § Δ.6 — Three obligations status (per memory rules)

1. **Spec-first** ✓ — C6 NEVER had code before LOCKED spec; 5 spec versions before LOCK.
2. **Honest context budget** ✓ — session was substantial (C5 build + walk + 4 C6 walks + LOCK + handoff) but stayed within budget; no skipped checks or deferred-without-flagging items.
3. **Master doc + handoff updates** ✓ — this delta + bundle assembly per Rule 10.

---

## § Δ.7 — Pattern discipline

- **Pattern A (fix-as-bandage)**: avoided. One C5 fix during build (guardrail comment containing forbidden substring) was a genuine rephrase, not a bandage. C6 had one v0.3 reversal (DINING) which was honest spec correction, not bandage.
- **Pattern B (building-without-wiring)**: avoided. C5 smoke-tested end-to-end before any test was written; full pipeline test through every test addition.
- **Pattern C (scores-without-truth)**: avoided. Every score computation in C5 has invariant tests (v0.8 § 14.1, v0.9 § 14.2/3 verifiers).
- **Pattern D (rules-on-rules)**: avoided. C6 walks deliberately routed many critiques to backlog rather than amending spec speculatively.
- **Pattern E (scope-creep-mid-build)**: avoided. C5 build had Q1/Q2/Q3 resolved BEFORE coding. C6 walks deferred adjacency/interaction/secondary-road items rather than expanding mid-spec.

---

## § Δ.8 — Next session (S31) starting state

**Recommended next move**: D-066 Step 6 for C6 — code build against v0.5 LOCKED spec.

- Working dir: `/home/claude/work/buildemup/` (copied from v7 bundle's `06_upstream_codebase/`)
- Spec to build against: `02_specs_chronological/22_C6_SPEC_v0_5_LOCKED.md`
- Pre-touch state inventory required (Rule 10.6.1) — `c06/` directory does not yet exist; clean greenfield.
- Test baseline at S31 start: 1539 passed / 1 skipped (verified at S30 close — see `05_integrity_check/S30_three_check_report.md`).
- Implementation surface: `domain/` and `components/c06/` packages, plus `tests/validation/test_c6_*.py` test files.

After C6 SHIPS, the next pipeline component is **C8 Corridor Designer** (referenced as downstream consumer of C5 + C6 outputs).

---

## § Δ.9 — Narrative consistency

This delta is incremental on v3.4 — no structural rewrite needed. v3.5 is v3.4 + this delta applied. Next consolidated narrative would roll up at v4.0 if scope expands materially (e.g., C5–C8 all shipped).
