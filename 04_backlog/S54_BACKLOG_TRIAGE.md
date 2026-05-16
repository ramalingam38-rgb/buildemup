# S54 Backlog Triage — 4 Buckets + Findings

**Authored:** S54 (May 16, 2026), Ramalingam + Claude
**Status:** Triage complete; user-decision items resolved (see Decisions section below)
**Total raw entries audited:** ~339 across 24 files in `04_backlog/`
**After dedupe + close-detection:** ~247 open distinct items + 23 already CLOSED

## Order of work locked in S54

1. **Backlogs first** — close Bucket A (deploy-blockers) and then Bucket B (product-blockers)
2. **Then deploy** — to Render (free, since Railway trial expired) or equivalent, with all 17 components live (not the current C1+C2+C3a-only surface)
3. **Then write the detailed v1+ project plan** — covering completed/remaining/improvements/missing-modules, per user's explicit deferred request

## Tally

| Bucket | Count | Meaning |
|---|---|---|
| **A — Deploy-blocker** | 8 (4 pre-existing + 4 new) | Must close before any real user touches the product |
| **B — Product-blocker** | ~55 | Close before saying "v1 done" |
| **C — Polish** | ~14 | Refactors/cleanups; do after launch |
| **D — V2-deferred** | 28 | Explicitly future scope; do not touch in v1 |
| **Ambiguous** | ~143 | Trigger-driven; promote to B when trigger likely |
| **Already CLOSED** | 23 | Resolved in prior sessions |

## User-decision items resolved this session

| Item | Original tag | Resolved bucket | Why |
|---|---|---|---|
| **B-066** (polygon / L-shape plots) | v2-deferred candidate | **B (product-blocker)** | Hard-fails 5-10% of real Indian plots — that's a user-trust failure, not a v2 feature |
| **B-099** (Vastu FULL tier) | hard-blocking for FULL tier | **C (polish — hide from UI)** | Hide the FULL option in v1; ship in v1.1 with Vastu-expert reviewer |

---

## Bucket A — Deploy-blockers (8 items)

### Four NEW findings from S54 brief-form testing — TOP PRIORITY

| # | Item | What it is | Why deploy-blocker | Effort |
|---|---|---|---|---|
| **S54-001** | Wire C2 feasibility into `/api/brief/capture` | Brief endpoint runs C1 in isolation; C2 only fires if you hit a separate URL no UI calls | **Soul violation** — engine silently scoped 1,584-sqft brief to 438-sqft envelope, told user "budget is generous." Forbidden silent-override mode per Architecture v1 §2.4 | ~1 session |
| **S54-002** | Wire C3a extreme-case detector into `/api/brief/capture` | C3a intelligence exists but brief form doesn't invoke it; only reachable via separate `/api/c3a/*` URLs | Impossible briefs pass through with INFO-level "all good" — opposite of the transparency the project exists for | ~1 session (combined with S54-001) |
| **S54-003** | Fix `BIGGEST ISSUE` string truncation in C1 output | Output shows `"★ BIGGEST ISSUE: Critical: Front setback 0"` cut off mid-sentence; reproducible | Every brief output shows this; first-impression bug | 30 minutes |
| **S54-004** | Fix small-plot detached-setback rule (right side = 0.0m) | Output: `Side (R): 0.6m | required 0.0m | +0.6m` for detached plot — nonsensical | KB rule lookup bug in `kb_rules/setback_rules.json`; likely small-plot UDD-2026 row hitting wrong column | 1-2 hours |

**Note on S54-001 + S54-002:** these share root cause — `/api/brief/capture` runs ONLY C1 in isolation. The fix is one change: make the endpoint run C1 → C3a-detect → C2-feasibility as a chain. ONE well-designed PR closes both findings and is the single highest-leverage change in the entire backlog.

### Four pre-existing hard gates (named in backlog_session_53.md)

| # | Item | Effort | Needs human? |
|---|---|---|---|
| **B-220** | Full hydraulics depth in C10 (DFU loading, slope, vent stack, pipe sizing per NBC Part 9 + IS 1742) | Large | Yes — plumbing engineer |
| **B-237** | Cross-platform CI matrix (Mac/Windows/Linux) | Medium | No — Claude can set up GitHub Actions |
| **B-238** | Independent licensed Indian architect review | Medium (calendar; budget ₹15-40K) | **YES — only humans can do this; Claude cannot** |
| **B-150** | NBC clause primary-source verification against NBC 2016 Part 3 PDF | Small | Borderline — Claude can read PDF; architect sign-off preferred for legal defensibility |

---

## Bucket B — Product-blockers (~55 items, grouped by cluster)

| Cluster | Item count | Sample headline |
|---|---|---|
| C14 LOCK-mandatory | 4 | Lock betweenness/privacy/transit/edge formulas before C14 v1.0 |
| C15 LOCK-mandatory | 7 | Severity-rule-table, check-registry, cultural-profile, measurement-formulas, moat-lint |
| C16 LOCK-mandatory | ~17 | Envelope schema, section-cut rules, RWH overlay, compliance provenance, parking schema, PBT coverage, regression snapshots, dual-frame coordinate audit |
| C17 critique findings | 7 | Semantic-match layer, arithmetic-mismatch indicator, rate-sanity OCR defence, legitimate-premium disclaimer, contractor-response section, alternate-market refs |
| C13 v1.x polish (top 3) | 3 | Invariant-taxonomy grouping, adversarial integration corpus, window avoidance |
| C11a/C11b launch-complement | 6 | B-NEW-J-override (ships with C11a v1), B-NEW-T1.5, T3, Y-full, C11B purity spotcheck, C11B canonical golden tests |
| C12 critique-walk findings | 3 | Causal failure traceability, **B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority)**, spec-drift CI |
| Storage/production hardening | ~5 | SQLite FK enforcement, env-var name drift, prod startup cross-check, CSP+Cache-Control headers, hypothesis golden tests |
| C6 trust gap | 2 | Reconstruct 186 missing C6 production tests (B-127); bundle integrity check (B-128) |
| Compliance/KB correctness | ~5 | Mumbai+Pune stilt threshold (B-003), MEDIUM_ROCK kPa correction (B-074), NBC corridor verification (B-108), circulation factor reconcile (B-004) |
| Classification/UX bugs | ~5 | line_type population (B-002), excess_sqft population (B-010), SETBACK_INVALID classification (B-014), typed exception migration (B-013), CorridorTooNarrow graceful fallback (B-109) |
| **Promoted by user decision** | 1 | **B-066 (polygon / L-shape plots)** — moved from v2-deferred to product-blocker |

**Biggest single sub-cluster:** C14 + C15 + C16 LOCK-mandatory items (~28 items combined). These were filed at component v1.0 LOCK time as "must close before each component v1.0 ships."

---

## Bucket C — Polish (~14 items)

- **B-099 (Vastu FULL tier) — hide from UI** (user decision; ~10 min frontend tweak)
- B-S53-C7-LEGACY-DECISION — dispose of 951-LOC `c07_structural_grid.py`
- B-S53-PROVISIONAL-CLEANUP — delete `c10/__init__.PROVISIONAL_S53.py`
- B-S53-C1-CONSOLIDATE — fold `c01_brief_capture.py` into `c01/`
- B-S53-C2-SPEC-MOVE — move C2 spec to canonical path
- B-S53-TEST-DIRS-MISSING — reorganize C4/C5/C6/C8/C9 test files
- B-015 / B-021 / B-056 — spec wording fixes
- B-057 / B-059 — minor UI text fixes
- B-060 — docstring typo fix
- B-241 — CI lint rule for wall_segments
- B-245 — meta-process tooling

Total effort for Bucket C: ~1 focused session.

---

## Bucket D — v2-deferred (28 items, ignore for v1)

Polygon plots was here but **moved to Bucket B** by user decision. Items remaining: ML topology scoring, multi-floor orientation, 3D model export, BIM/IFC pilot, P-M interaction diagrams, strategic LLM negotiation, aesthetic heuristic corpus, multi-jurisdiction profiles, EvoArch/QD-algorithm research, settlement differential modeling, full IS 13920 Zone V, drone surveys, 3D printing, robotic execution, React Native app, AR overlay, supplier API integrations, 22-language i18n, and similar. See `buildemup_v2_backlog_S35_walk_9.md` for full list.

---

## Ambiguous (~143 items) — trigger-driven, promote when likely

Most are tagged "VALID-BUT-BACKLOG" with explicit triggers like "post first 50 production plans" or "post first user-support incident." Decide which triggers are likely in the next 3 months:

- First plot rejection
- First multi-floor brief
- First city outside 10 supported
- First Resend email failure
- First concurrent-session race
- First contractor-quote upload that fails
- First architect complaint (linked to B-238)

The items linked to triggers you pick get promoted to Bucket B. The rest stay deferred.

---

## Recommended order of attack

### Phase 1 — Close the new Bucket A items (the soul fixes) — ~1 week
1. **S54-001 + S54-002 combined** — wire `/api/brief/capture` to chain C1 → C3a-detect → C2-feasibility
2. **S54-003** — fix BIGGEST ISSUE truncation
3. **S54-004** — fix small-plot detached setback right-side bug

### Phase 2 — Engage the human-required gates — ~2 weeks
4. **B-238** — start finding licensed Indian architect (calendar-bound; ₹15-40K budget)
5. **B-150** — Claude + user spot-check 15 NBC claims in `kb_rules/*.json` against actual NBC 2016 PDF
6. **B-237** — set up cross-platform CI (GitHub Actions: Ubuntu + Windows + macOS matrix)

### Phase 3 — Close LOCK-mandatory clusters in Bucket B — ~1 month
7. C14 LOCK-mandatories (4 items)
8. C15 LOCK-mandatories (7 items)
9. C16 LOCK-mandatories (17 items)
10. C17 critique findings (7 items)

### Phase 4 — Production hardening + remaining Bucket B — ~1 month
11. Storage hardening, compliance/KB correctness, classification/UX bugs
12. C13 v1.x polish, C11a/b launch-complement items
13. B-066 polygon plots (large effort, slot near end since it touches C5/C7/C8)
14. C6 trust gap (reconstruct missing tests)

### Phase 5 — Deploy with all 17 components — when Bucket A + B done
15. Master orchestrator (Tier-1 #1 from earlier analysis) — wires C1 → C2 → C3a/C3b → C4 → ... → C17 as one pipeline
16. HTTP routes for C4-C17 (currently library-only)
17. UI surfaces for drawings (C16) and quote upload (C17)
18. Deploy to Render (or alternative)

### Phase 6 — DEFERRED: detailed v1+ roadmap planning
19. User-requested deliverable: completed / remaining / improvements / missing soul-modules (3D, interior, full CAD pack, municipal approval, construction-phase help, engineer-fee breakout, etc.)

---

## Open ambiguous items still needing user calls

When backlog work hits the ambiguous pile, user will need to decide which trigger conditions are likely in his 3-month horizon, then promote relevant items to Bucket B.

---

## Closed items (23) — listed for record, not actionable

B-026 (superseded), B-043 (S25), B-131-138, 141-144 (S33 patches), B-152 (spec-body folded), B-NEW-K-landingscale (S38 K-4 patch), B-NEW-V/U/W/Y-partial/T1/T2 (S39-S40 LANDED), B-S53-C7-WALL-SEGMENT-RESTORE, B-S53-C10-INIT-RESTORE (S53), B-218 (misframed), B-221, B-239, B-240, B-243, B-244 (C10 v0.6-v0.9 patches), B-212 (S35 W9), B-C16-DECOMPOSITION-DECISION-LOCK (S47 adjudicated), B-C15-RANKER-HINT-ACCESS-CONTROL (C15 v0.2 removed).

---

*This file is the single source of truth for S54 backlog state. Update inline as items move between buckets. Do NOT replace — append revision history if user makes further decisions.*
