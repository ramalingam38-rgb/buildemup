# MASTER_DOC v3.3 → v3.4 DELTA

**Generated:** end of Session 28, 2 May 2026.

This delta extends the master design narrative from v3.3 (post-S27 LOCK) to v3.4 (post-S28 SHIP + C4 v0.4 LOCK). Companion file: `MASTER_DOC_v3_2_TO_v3_3_DELTA.md` (preceding).

---

## § Δ.1 — Component shipping state

**At v3.3 (S27 close):** 3 of 17 components shipped (C1, C2, C7). C3a S8 LOCKED-but-not-yet-SHIPPED.

**At v3.4 (S28 close):** **4 of 17 components shipped**:
- C1 ✅ (Era 1)
- C2 ✅ (Era 1)
- C3a ✅ (S8 v1.2 SHIPPED — adjudicated end of S28 per `00_START_HERE/SESSION_28_S8_SHIP_DECLARATION.md`)
- C7 ✅ (Era 1)

Plus: **C4 SPEC v0.4 LOCKED** end of S28. Code build pending Session 29.

## § Δ.2 — Era 2 layout pipeline status (C4-C16)

The Era 2 layout pipeline begins with C4 (Plot Analysis). v3.4 marks the first LOCKED spec in Era 2:

| Component | State at v3.3 | State at v3.4 |
|---|---|---|
| C4 Plot Analysis | not started | **SPEC v0.4 LOCKED** (build-ready) |
| C5 Topology Selector | not started | not started (next after C4 code) |
| C6 Orientation Priority | not started | not started |
| C8-C16 (corridor, eval, etc.) | not started | not started |

C4 spec evolved through 4 versions in S28 alone:
- v0.1 DRAFT (initial)
- v0.2 PROPOSED (after 1st external critique walk: 13 valid-patches applied, 3 backlog)
- v0.3 PROPOSED (after web research caught NBC zone errors + Mumbai DCPR errors)
- **v0.4 LOCKED** (after 2nd external critique + code-grep + Path B + 4 hygiene + 5 self-critique)

Each iteration tightened a different verification surface. The full progression is preserved in `07_design_documents/buildemup_C4_SPEC_v0_*.md` for trace.

## § Δ.3 — Rule additions / refinements in S28

**NEW: Rule 9.2 — always-file-backlog directive.** Codified mid-session per Ramalingam: "Always file the backlog and you don't need to ask. Put it in the rules." Memory line 12. Effect: when a critique walk surfaces VALID-BUT-BACKLOG items, Claude files them as actual B-NNN entries immediately, without asking permission. Discard requires explicit Ramalingam direction otherwise.

**Rule 7 strengthened (operationally, not textually):** the v0.2 → v0.3 transition exposed that Claude was skipping the web-research half of Rule 7. Ramalingam's catch ("There was a rule that says to do web research too...") forced an explicit web-research pass which surfaced 4 substantive factual errors in v0.2's NBC climate zone treatment + Mumbai DCPR thresholds. v0.4 added a 4th verification surface — **upstream code-grep** — alongside external critique × 2, web research, and self-critique. Code-grep alone caught 4 more errors that would have caused `AttributeError` at module import. Going forward: code-grep is treated as mandatory Rule-7 surface for any spec referencing existing code contracts.

## § Δ.4 — Backlog inventory at v3.4

**At v3.3:** 53 active backlog entries (B-001 through B-056 issued, B-026 superseded into B-023).

**At v3.4:** **62 active backlog entries** (B-001 through B-072 issued, B-026 superseded into B-023, B-047 unused). 16 new this session:
- 4 audit-origin (B-057, B-058, B-059, B-060)
- 5 S8-critique-walk-origin (B-061 to B-065)
- 7 C4-spec-progression-origin (B-066 to B-072)

All filed per Rule 9.2. All OUT-of-scope for current builds.

## § Δ.5 — Patterns reinforced this session

**Pattern A (fix-as-bandage)** — applied during S8 conftest fix: rather than patch `live_server_e2e` with a one-off env override, the fix sets `C3A_TEST_MODE=1` at fixture setup so any future test using the fixture inherits correct state. Save/restore-prior-value pattern preserves test ordering.

**Pattern B (building-without-wiring)** — avoided in C4 spec: the placeholder `test_c5_does_not_import_plot_directly` test is SKIPPED until `c05/` exists, rather than being deleted-and-forgotten. Forward-compat hook with explicit activation gate.

**Pattern C (scores-without-truth)** — N/A this session.

**Pattern D (rules-on-rules)** — managed: Rule 9.2 added cleanly without inventing meta-rules. Memory at 12 lines (was 11).

**Pattern E (scope-creep-mid-build)** — actively avoided: C7 retrofit (B-072) explicitly deferred rather than touching shipped Era 1 code mid-Era-2 spec work.

## § Δ.6 — Cross-cutting decisions adjudicated

Adjudications received from Ramalingam during S28, all recorded with verbatim quotes:

| Adjudication | Verbatim | Recorded in |
|---|---|---|
| Flag A (load_status_row) → Option A | "approve option A" (S27 end + S28 confirm) | SESSION_28_CORRECTIVE_INSTRUCTIONS.md |
| Flag B (P43 scoping) → Option A | "yes, option A" | SESSION_28_CORRECTIVE_INSTRUCTIONS.md |
| Rule 9.2 codification | "Always file the backlog and you don't need to ask. Put it in the rules." | memory line 12 + master doc here |
| Path B for C4 v0.3→v0.4 | "It's path B" | C4 v0.4 spec § 13 |
| C4 v0.4 LOCK | "Lock this spec and give me the handoff" | C4 v0.4 spec header + § 11 |
| S8 v1.2 SHIP | "Finish the s8 ship and the hand off look alright you can proceed" | SESSION_28_S8_SHIP_DECLARATION.md |

## § Δ.7 — Session 28 deliverables snapshot

**Code (4 files in upstream tree):**
- `buildemup/api/server.py` — Phase 5 patches
- `buildemup/tests/e2e/conftest.py` — Phase 6 fixture
- `buildemup/tests/validation/test_c3a_static_serving.py` — NEW Phase 5 test file
- `buildemup/DEPLOY.md` — Phase 7

**Specs (4 new C4 versions):**
- v0.1 DRAFT, v0.2 PROPOSED, v0.3 PROPOSED, v0.4 LOCKED

**Bundle bookkeeping (8 files):**
- SESSION_28_S8_SHIP_DECLARATION.md
- MASTER_DOC_v3_3_TO_v3_4_DELTA.md (this file)
- backlog_session_28.md
- AUDIT_REPORT_PHASE_5_6_FILES_SESSION_28.md
- GAP/AUDIT/INTEGRITY_CHECK_SESSION_28_BUILD.md (3 files)
- 30_buildemup_C4_SPEC_v0_4_LOCKED.md (promoted to specs_chronological)

**Net test count change:** +9 (143 validation tests now, was 134).

## § Δ.8 — Open items at v3.4

| Item | Type | Disposition |
|---|---|---|
| C4 code build | next-session work | NEXT_CLAUDE_HANDOFF.md targets this |
| C4 KB_VERSION one-line additions to existing wind_load.py + soil_foundation_rules.py | tiny dependency for C4 build | Will be done at C4 build time per spec § 4.4.2 |
| S8 metric-attribution gap (c3a_endpoint.py:233-240) | known limitation | Documented in spec § 4.7; deferred to "C3a v0.2 architecture refactor" backlog territory |
| 16 S28 backlog items | OUT-of-scope | Tracked; none block current builds |
| Memory line cleanup (lines 7+9, 8+10 duplicates per pretouch inventory) | low-priority hygiene | Carry forward |

## § Δ.9 — Master doc state at v3.4

The narrative is consistent. No structural rewrite needed. v3.4 is incrementally built on v3.3 by applying this delta. Next consolidated narrative could roll up at v4.0 if scope expands materially (e.g., C4-C8 all shipped).

---

**Master doc at v3.4. C3a complete (Era 1 + S8). C4 LOCKED, build-ready.**
