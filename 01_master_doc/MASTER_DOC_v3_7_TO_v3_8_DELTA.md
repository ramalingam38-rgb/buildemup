# BuildemUp Master Doc — Δ v3.7 → v3.8

**Session**: S33 (5 May 2026)
**Authority**: This delta records S33 work. v3.8 is canonical going forward.

---

## Δ.0 — Pipeline state at S33 close

**Components SHIPPED**: 8 of 19 (unchanged from S32; same component set).

**LOCKED specs at S33 close**:
- ✅ **C8 v0.6 LOCKED** — amendment resolving B-129 N-aware taper-zone math
- ✅ **C9 v0.7 LOCKED** — production-ready spec; build deferred to S34

| # | Track 3 ID | Status | LOCKED spec | Tests |
|---|---|---|---|---|
| 1 | C1 (Brief Capture) | SHIPPED | v0.x | (in baseline) |
| 2 | C2 (Component KB Sketcher) | SHIPPED | v0.x | (in baseline) |
| 3 | C3a (Extreme-Case Gate) | SHIPPED | v0.2.1 | (in baseline) |
| 4 | C4 (Plot Analysis) | SHIPPED | v1.1 | (in baseline) |
| 5 | C5 (Topology Selector) | SHIPPED | v0.9 | (in baseline) |
| 6 | C6 (Orientation Refinement) | SHIPPED | v0.7 | **+275 tests S33-NEW (B-127 RESOLVED)** |
| 7 | C7 (Structural Grid) | SHIPPED | v0.x | (in baseline) |
| 8 | C8 (Corridor Designer) | SHIPPED | **v0.6 (was v0.5)** | 174 tests, +732 LOC from 12 patches |
| 9 | C9 (Room Sizer) | spec LOCKED | **v0.7 (NEW)** | spec only — build at S34 |

**Cumulative test count at S33 close**: **1988 passed / 1 skipped** (was: 1713 at S32 close).
- C6 added: 275 tests (B-127 reconstruction).
- C8 patches landed without any test additions (preserved at 174).

**Cumulative C8 LOC**: 4,148 (was: 3,416 at S32 close); +732 net from 12 patches.

---

## Δ.1 — C8 v0.6 spec amendment

**B-129 resolved**: § 4.3.1 truncation rule was internally inconsistent with Inv 20 in v0.5. v0.6 resolves with N-aware math:

```
max_allowed = length / (2 × max(1, n_tapered_ends))
```

This generalizes the prior "max 50%" rule — when a segment has 0 tapered ends, no cap applies; with 1 end, max 50%; with 2 ends, max 25% each. Eliminates the spec-vs-Inv-20 contradiction.

**Filed**: B-131 (code-side patch threading `n_tapered_ends`); resolved this same session.

**Spec file**: `02_specs_chronological/33_C8_SPEC_v0_6_LOCKED.md` (1,924 lines).

---

## Δ.2 — C8 code critique walk #1 + 12 patches landed

**Critique scope**: spec-fidelity walk against C8 v0.6 LOCKED spec. Document at `03_code_chronological/S33_C8_code_critique/c8_code_critique_walk_1_spec_fidelity.md` (517 lines).

**12 patches landed** (all backlog-traceable, all 1988/1 tests pass post-each-patch):

| # | Backlog | Spec § | File | Net LOC |
|---|---|---|---|---|
| 1 | B-142 | (cross-cutting) | NEW `tolerances.py` | +99 |
| 2 | B-131 | § 4.3.1 N-aware math | `width_selection.py` | +36 |
| 3 | B-141 | § 4.10 junction taper | `junction_propagation.py` | +45 |
| 4 | B-133 | § 6 typed errors | `errors.py` | +21 |
| 5 | B-135 | provenance | `corridor_designer.py` | (in +189) |
| 6 | B-137 | § 4.6 Inv 6 tagging | `validator.py` | (in +146) |
| 7 | B-144 | § 4.6 Inv 6 semantic | `validator.py` | (in +146) |
| 8 | B-134 | § 4.7 junction-snap | `topology_dispatch.py` | +290 |
| 9 | B-132 | § 4.8 grid-alignment | `validator.py` | (in +146) |
| 10 | B-136 | envelope handling | `area_accounting.py` | +172 |
| 11 | B-138 | ENTRY_STUB | `corridor_designer.py` | (in +189) |
| 12 | B-143 | § 4.6 Inv 14 | `validator.py` | (in +146) |

**Walk-on-walk surfacing**:
- B-137 (BAND_ATTACHMENT tagging) revealed that the prior coarse adjacency check was semantically wrong → filed and resolved as B-144 (bay-proximity adjacency).
- B-132 (real grid-alignment measurement) surfaced B-145 (filed; deferred).

**Patch quality discipline**: every patch followed full pytest verification before claiming "tests green." 1988/1 maintained continuously throughout the 12-patch sequence.

---

## Δ.3 — C6 test corpus reconstructed (B-127 RESOLVED)

**Problem at S33 open**: C6 SHIPPED at S31 with 186 claimed tests, but tests never made it into v8 or v9 upstream snapshots. C8 imports from C6's public API worked fine (verified S32), but no test coverage existed in the bundle.

**S33 reconstruction approach**: rebuild test corpus from C6 SPEC v0.7 § 7 directly, not from claimed-but-missing files.

**Test files authored** (all S33-NEW; all passing):

| File | LOC | Tests collected | Coverage |
|---|---|---|---|
| `_c6_fixtures.py` | 72 | (helper) | shared fixtures |
| `test_c6_schema.py` | 480 | 45 | schema invariants |
| `test_c6_vastu_kb.py` | 287 | 54 (parametrized) | KB lookup correctness |
| `test_c6_signals.py` | 390 | 57 (parametrized) | signal computation |
| `test_c6_optimizer.py` | 553 | 52 | optimization paths |
| `test_c6_select.py` | 381 | 37 (parametrized) | selection logic |
| `test_c6_failure_modes.py` | 326 | 30 (parametrized) | error paths |
| **Total** | **2,489** | **275** | |

**Verification**: pytest collects 275 tests; all pass. Brings cumulative baseline from 1713 to 1988.

---

## Δ.4 — C9 spec arc (7 walks → v0.7 LOCKED)

**Authoring sequence**:
1. v0.1 DRAFT — initial schema from architecture-v2/v3 + worked example. 9 backlog placeholders B-NNN-A through B-NNN-I.
2. Walk #1 (Claude self-critique) — 15 findings, 2 HIGH-severity (NBC kitchen and NBC bathroom values were wrong in DRAFT).
3. v0.2 PROPOSED — `RegulatoryMinimum` triple, `DwellingSizeTier`, `is_master`, dropped `consumption_band`, packing-efficiency WARN, clause attributions.
4. Walk #2 (Ramalingam) — 15 findings (13 overlap walk #1; 2 net-new: B-148 multi-floor dwelling-tier, B-149 packing tightening). Plus B-150 NBC clause verification.
5. Walk #3 — 11 findings; CRITICAL #4: liveability ignored width (a 9.5 m² @ 2.4 m bedroom passes area but cannot fit furniture). 2 push-backs documented.
6. v0.3 PROPOSED — `liveability_min_width_m`, `BathroomSubtype`, `unassigned_area_m2`, multi-floor LARGE-pick, `kb/room_targets.json`, `packing_basis`.
7. Walk #4 — 10 findings; 4 actionable + 2 push-backs.
8. v0.4 PROPOSED — `NBCSourceConfidence`, `TierResolutionAccuracy`, `other_subtype`, Inv 17 (WARN width), Inv 18 (WARN grid-bay).
9. Walk #5 — 10 findings; 6 actionable + 3 push-backs.
10. v0.5 PROPOSED — `WidthFeasibilityVerdict`, `GridBayFeasibility`, `PlacementRiskLevel` (resolves B-152 into spec), `assumed_total_dwelling_area_m2`, `require_verified_nbc`.
11. Walk #6 — 10 findings; 5 actionable + 4 push-backs. **Substantive correction**: Walk-#5's WARN-on-IMPOSSIBLE was wrong; web-grounded fail-fast for deterministic-impossibility.
12. v0.6 PROPOSED — Inv 17 split (17a RAISE, 17b WARN); severity-weighted `placement_risk_level`; `wall_thickness_ratio` config; `unverified_nbc_rows_used` provenance; `RoomSizingError` base class with `WidthInfeasibleError` (B-NNN-J).
13. Walk #7 — 10 findings; user-restricted scope (only #1 + #2): 2 actionable + 8 push-backs.
14. **v0.7 LOCKED** — per-candidate failure tolerance with `BatchSizingInfeasibleError` and `PerCandidateError` base; STRICT mode activation (Inv 10/17b/18 escalations: `PackingInfeasibleError`, `WidthRiskyError`, `GridOversizeError` B-NNN-K); § 14.40-§ 14.43.

### Convergence signal

| Walk | Findings | Net new actionable | Push-backs |
|---|---|---|---|
| #1 | 15 | 12 | 0 |
| #2 | 15 | 2 | 0 |
| #3 | 11 | 3 | 2 |
| #4 | 10 | 4 | 2 |
| #5 | 10 | 6 | 3 |
| #6 | 10 | 5 | 4 |
| #7 | 10 | 2 | **8** |

Push-backs ≥ net-new actionable in walk #7 → LOCK was the right call.

### C9 final spec metadata

- 17 sections (§ 0 through § 16)
- 43 architectural decisions (§ 14.1 through § 14.43)
- 18 validator invariants (Inv 17a RAISE, Inv 17b WARN, Inv 18 WARN with STRICT escalation)
- ~150 test target for build session
- 14 backlog items at LOCK (B-148, B-149, B-150, B-151, B-NNN-J, B-NNN-K + 8 from v0.1-DRAFT placeholders, minus B-NNN-G consolidated into B-148; B-152 closed-into-spec at v0.5)

---

## Δ.5 — Backlog growth across S33

| ID | Title | Origin | Status |
|---|---|---|---|
| B-130 | Sweep-line refactor of `area_accounting.py` | C8 walk #1 | OPEN |
| B-131 | N-aware `n_tapered_ends` threading | C8 walk #1 | RESOLVED via patch |
| B-132 | Real grid-alignment measurement | C8 walk #1 | RESOLVED via patch (surfaced B-145) |
| B-133 | Typed `CorridorSelfIntersectionError` | C8 walk #1 | RESOLVED via patch |
| B-134 | Junction-snap normalization | C8 walk #1 | RESOLVED via patch |
| B-135 | Upstream trace IDs threading | C8 walk #1 | RESOLVED via patch |
| B-136 | Envelope-overflow narrowing | C8 walk #1 | RESOLVED via patch |
| B-137 | BAND_ATTACHMENT tagging | C8 walk #1 | RESOLVED via patch (surfaced B-144) |
| B-138 | ENTRY_STUB construction | C8 walk #1 | RESOLVED via patch |
| B-139 | (deferred patch follow-on) | C8 walk #1 | OPEN |
| B-140 | (deferred patch follow-on; partner of B-130 sweep-line) | C8 walk #1 | OPEN |
| B-141 | Junction taper accumulation cap | C8 walk #1 | RESOLVED via patch |
| B-142 | NEW centralized `tolerances.py` module | C8 walk #1 | RESOLVED via patch |
| B-143 | Inv 14 explicit defensive check | C8 walk #1 | RESOLVED via patch |
| B-144 | Inv 6 bay-proximity adjacency | C8 walk #1 (surfaced by B-137) | RESOLVED via patch |
| B-145 | (surfaced by B-132) | C8 walk #1 | OPEN |
| B-146 | (walk-on-walk follow-on) | C8 walk #1 | OPEN |
| B-147 | (walk-on-walk follow-on) | C8 walk #1 | OPEN |
| B-148 | Multi-floor dwelling-tier (whole-dwelling auto-derived from C2) | C9 walk #2 | OPEN |
| B-149 | Packing-efficiency tightening to ERROR mode | C9 walk #2 | OPEN |
| B-150 | NBC clause verification against authoritative PDF | C9 walk #2 | OPEN |
| B-151 | OTHER subtype-driven sizing | C9 walk #3 | OPEN |
| ~~B-152~~ | ~~Combined placement_risk_level~~ | C9 walk #4; **CLOSED** at v0.5 | RESOLVED in spec body |
| B-NNN-J | `WidthInfeasibleError` typed exception class | C9 walk #6 | TO-BE-IMPLEMENTED IN BUILD |
| B-NNN-K | `GridOversizeError` typed exception class | C9 walk #7 | TO-BE-IMPLEMENTED IN BUILD |

**Net S33 backlog additions**: 24 entries; 12 RESOLVED via S33 patches; 1 CLOSED into spec; 11 OPEN for future sessions.

---

## Δ.6 — Critical decisions worth carrying forward

### From C9 spec arc (architectural patterns)

These patterns established in C9 v0.7 are likely useful for C10/C11/C12 specs:

1. **Typed exception hierarchy with per-candidate vs systemic distinction** (§ 14.40). When pipeline components produce multiple candidates, separate "this candidate failed" from "the input is malformed." `PerCandidateError` base + `BatchInfeasibleError` for "all failed" pattern.

2. **Severity-weighted risk aggregation** (§ 14.36). When multiple WARN signals exist, weight them by deterministic-vs-heuristic severity rather than count flat.

3. **Configurable enforcement modes** (§ 14.41). STRICT vs WARN as a generic policy escalates heuristic WARNs to RAISEs without changing default behavior.

4. **Source-confidence tagging** (§ 14.24). When using values from secondary sources (NBC, code references), tag each row with confidence (VERIFIED / SECONDARY_CONSENSUS / SECONDARY_UNVERIFIED). Surface unverified usage in provenance even when not strict-blocking.

5. **Per-candidate vs batch-level provenance** (§ 14.40). Each candidate carries its own provenance; batch-level info lives in failure exceptions, not a separate object.

### From C8 patch arc

1. **Centralize tolerances** (B-142 / `tolerances.py`). Reuse across modules avoids drift.

2. **Fail-fast on deterministic impossibility, WARN on heuristic risk** (§ 14.35 of C9 echoing the spirit of C8's discipline).

3. **Walk-on-walk surfacing**: when a patch lands, run another walk over the patched code. B-137→B-144 and B-132→B-145 are examples.

---

## Δ.7 — What S34 should do next

C9 build session is the natural next step:

1. **Read spec**: `02_specs_chronological/41_C9_SPEC_v0_7_LOCKED.md`
2. **Author 3 KB JSONs** under `kb/`: `nbc_room_minimums.json`, `furniture_floor.json`, `room_targets.json`
3. **Author 7+ production modules** under `components/c09/`: `__init__.py`, `errors.py`, `schema.py`, `nbc_table.py`, `furniture_floor.py`, `targets_kb.py`, `allocator.py`, `validator.py`, `room_sizer.py`
4. **Author ~150 tests** matching § 7 invariant→test mapping (including new partial-batch and STRICT-mode test modules)
5. **Verify baseline**: 1988 + ~150 = ~2138 target

C8 walks #2 (code quality) and #3 (test coverage adequacy) — deferred to a separate session after C9 build.

C3b — pending.

---

## Δ.8 — Pytest baseline at S33 close

```
1988 passed, 1 skipped, 1415 warnings, 52 subtests passed in 60.60s
```

**Composition**: 1713 baseline (preserved through 12 C8 patches) + 275 new C6 tests.

B-128 protocol re-executed at session close. All 12 C8 patches verified non-regressing.

---

## Δ.9 — End of v3.7 → v3.8 delta

v3.8 is canonical going forward. Next master doc delta: v3.8 → v3.9 at S34 close.
