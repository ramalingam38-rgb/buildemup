# S48 Critique Walk — Backlog Delta

**Source:** Critique walk on S48 C15 complete bundle (20 items reviewed).
**Per Rule 9.2:** VALID-BACKLOG items filed without further permission.
**Per Rule 8:** All items below are filed entries; nothing is LOCKED.

This file is a DELTA. At next handoff it merges into the cumulative
`v0_2_backlog.md` master backlog file.

---

## New B-NNN entries (11)

### B-C15-SEMANTIC-VALIDATION-CORPUS
- **Description:** Separate semantic-correctness validation discipline from unit-test correctness. Architect-reviewed benchmark layouts, "would humans agree with this report?" evaluation sets, post-occupancy comparison studies.
- **Origin:** S48 critique walk item 1.
- **Trigger condition:** Becomes blocking when registry expands beyond 41 checks OR when first user-facing pilot ships.
- **S{N}-scope verdict:** Not in any S48-S52 implementation scope. Post-LOCK quality discipline.
- **Effort estimate:** Multi-week. 20 architect-reviewed reference layouts + agreement-rate evaluation harness.

### B-C15-DEFERRED-CHECK-TELEMETRY
- **Description:** Track which deferred dimensions users most frequently inspect; which missing upstream dependencies matter most; how often reports are dominated by deferred dimensions. Use telemetry to prioritize upstream engine work (windows, furniture-fit, orientation).
- **Origin:** S48 critique walk item 3.
- **Trigger condition:** Post-first-deployment. Until then, deferred-check value is theoretical.
- **S{N}-scope verdict:** Post-LOCK.
- **Effort estimate:** ~3 days (telemetry hook + dashboard). Cheap once a deployment exists.

### B-C15-LAYOUT-DIVERSITY-AUDIT
- **Description:** Periodic audit that different architectural styles can still succeed under C15: compact urban, courtyard, ritual procession, multigenerational segregation, hybrid live-work. Test that NSGA-II downstream does not converge on one dominant "AI-approved" morphology. Maintain a corpus of 5 architecturally-distinct reference layouts; assert each produces non-trivially different but mutually-respectable problem reports across registry versions.
- **Origin:** S48 critique walk item 5. **Literature reference:** Zhao & Li 2025 (PMC12233238) — "insufficient global optimization ability and easy loss of population diversity in building interior layout design" is peer-reviewed concern in residential layout optimization.
- **Trigger condition:** Becomes blocking when C17 ranker integration begins consuming C15 reports.
- **S{N}-scope verdict:** Pre-C17-integration. Should land before any optimization layer reads C15.
- **Effort estimate:** ~1 week — reference corpus curation + diversity-metric test harness.

### B-C15-DIMENSION-MATURITY-METADATA
- **Description:** Surface per-dimension maturity inside reports. Engine currently stronger in geometry/privacy/flow than light/storage/adaptability — structural asymmetry, not philosophical. Render as e.g. "Dim 4 (Natural Light): NOT-RUNNABLE at v1; future upstream extension."
- **Origin:** S48 critique walk item 6. **Absorbs into A12 amendment (deferred)** when A12 is processed at v1.0 LOCK preparation.
- **Trigger condition:** v1.0-LOCK preparation (per LOCK-trigger protocol).
- **S{N}-scope verdict:** Process at LOCK trigger.
- **Effort estimate:** ~1 day if absorbed into A12; standalone ~2 days.

### B-C15-ORCHESTRATOR-PURITY-AUDIT
- **Description:** Annual review that orchestrator phase functions stay pure dispatchers, not embedded evaluators. Enforce: orchestration coordinates; checks evaluate; governance configures; profiles specialize. Currently honored — Sub-5 orchestrator has 6 separated phase functions. Forward risk only.
- **Origin:** S48 critique walk item 9 (partially misframed — current state is honored; item is forward-looking).
- **Trigger condition:** Annual; or when orchestrator LOC grows >2x current 389 lines.
- **S{N}-scope verdict:** Post-LOCK governance.
- **Effort estimate:** Half-day per audit.

### B-C15-REGISTRY-VISUALIZATION-TOOLING
- **Description:** Dependency graphs, overlap maps, epistemic-kind breakdowns, profile applicability matrices, severity-distribution heatmaps. Governance without visibility eventually fails.
- **Origin:** S48 critique walk item 11. At 41 checks still cognitively tractable; matters at 70+.
- **Trigger condition:** Registry crosses 60 checks OR first registry-related governance dispute.
- **S{N}-scope verdict:** Post-LOCK polish.
- **Effort estimate:** ~1 week (interactive tooling).

### B-C15-PROFILE-COMPARISON-VIEWS
- **Description:** When profile-specific severity overrides land, UX must show comparative analysis ("compact urban: 2 warnings; Tamil multigen: 7 warnings"). Make profile differences inspectable, not hidden.
- **Origin:** S48 critique walk item 12. Currently dead code (all 6 enum members in INDIAN_PROFILES; no per-profile overrides exist).
- **Trigger condition:** When first profile-specific severity override is filed.
- **S{N}-scope verdict:** Post-trigger event; not pre-allocated.
- **Effort estimate:** ~3 days.

### B-C15-UPSTREAM-CONFIDENCE-PROPAGATION
- **Description:** Consume C14 `category_coverage: float` + C13 `GeometricFidelity` into C15 confidence layer. If upstream signals low confidence, C15 visibly reduces its own confidence. Currently ignored — code-grep confirms zero references to `category_coverage` in C15 modules.
- **Origin:** S48 critique walk item 13. **Reviewer correct, code-verified gap.**
- **Trigger condition:** Combines with A12 amendment (deferred). Process at v1.0-LOCK preparation alongside coverage_quality field.
- **S{N}-scope verdict:** Process at LOCK trigger.
- **Effort estimate:** ~2 days. Schema field + propagation through Phase π + tests.

### B-C15-PERFORMANCE-TELEMETRY
- **Description:** Per-check timing, hotspot detection, lazy evaluation for deferred UX sections, registry-level complexity budgets. Currently 209 tests run in 0.22s — not a problem yet. Becomes real when windows/furniture-fit engines land and dim 4/8/9/10 wake up.
- **Origin:** S48 critique walk item 17.
- **Trigger condition:** First registered check >100ms p99 latency, OR registry crosses 60 checks.
- **S{N}-scope verdict:** Post-LOCK.
- **Effort estimate:** ~3 days. Telemetry decorator + dashboard.

### B-C15-EXPLANATION-TEMPLATE-LIBRARY
- **Description:** Structured templates for `why_it_matters` + `suggested_mitigation` prose. Citation registry already exists in `severity_rule_table.py` (CITE_* constants). Need extension to per-status prose templates so explanation style stays consistent across 20+ runnable checks.
- **Origin:** S48 critique walk item 18.
- **Trigger condition:** Pre-LOCK polish.
- **S{N}-scope verdict:** v0.8-v0.9 polish walks.
- **Effort estimate:** ~2 days.

### B-C15-SEVERITY-CHANGE-GOVERNANCE-PRE-LOCK ⚠ LOCK-MANDATORY
- **Description:** Add § 14.2 NEW to spec: Severity-Change Governance Gate. Every severity-rule-table change requires changelog entry citing source-shift (e.g., "Lifetime Homes Standard 2019 → 2024 update"), backward-compat review against ≥3 reference layouts, registry-version bump. Mirrors § 14.1 check-addition gate. Process: spec amendment only at amendment time; subsequent rule edits then pay the documentation cost.
- **Origin:** S48 critique walk item 7 ("severity governance is value governance"). v0.3 A11 amendment proposed → withdrawn per Ramalingam choice (b) → re-filed as LOCK-mandatory.
- **Trigger condition:** **Must close before v1.0 LOCK.** Processed at LOCK trigger per LOCK-trigger protocol.
- **S{N}-scope verdict:** v1.0-LOCK preparation.
- **Effort estimate:** ~0.5 day (spec-only change).

---

## Scope extensions to existing items (3)

### B-C15-CHECK-ACCRETION-AUDIT — extended
- **Original scope:** Annual audit reviewing new check additions for redundancy/value.
- **Extension:** Also include **check-retirement** reviews. Periodic pruning, not just gating accretion. "Check retirement" becomes formal governance path.
- **Origin:** S48 critique walk item 2 (misframed as "registry too large" — current 41 is spec-mandated; real concern is unbounded future growth without retirement path).

### B-C15-CULTURAL-PROFILE-COVERAGE — extended
- **Original scope:** ≥3 Indian sub-variants produce measurably different outputs (A3 LOCK-mandatory).
- **Extension:** Periodic profile-parity audits — per-profile dimension coverage matrix; profile divergence diff tooling; explicit rationale for profile-specific deviations.
- **Origin:** S48 critique walk item 4 (drift asymmetry between profiles over time).

### B-C15-MOAT-AUDIT — extended
- **Original scope:** Annual audit of anti-score discipline (Inv P0 enforcement).
- **Extension:** Broaden audit scope from "no aggregator" only to spec-intent fidelity broadly — cultural explicitness, uncertainty visibility, heuristic framing. "Does implementation still embody the philosophical safeguards?"
- **Origin:** S48 critique walk item 10 (spec-intent drift in mature systems).

---

## Project-scope items (routed outside C15 B-NNN namespace)

### P-UX-PROBLEM-REPORT-RENDERING-DISCIPLINE
- **Description:** UX layer renders ProblemReport in a way that preserves the architecture's safeguards. Backend nuance can be destroyed in seconds by a frontend rendering "12 problems found". Treat UX framing as architectural infrastructure, not presentation polish.
- **Origin:** S48 critique walk item 15.
- **Owner:** Project-scope (not C15 component).

---

## Summary tally

| Category | Count |
|---|---|
| New C15 B-NNN items | 11 |
| Existing C15 items extended | 3 |
| Project-scope items routed out | 1 |
| **Net additions to C15 backlog** | **11 new + 3 extensions** |

**C15 cumulative backlog after this walk:** 26 (v0.2 LOCK) + 11 = **37 items**.

**C15 LOCK-mandatory items inventory:** 7 (pre-existing per spec § 12) + 1 (B-C15-SEVERITY-CHANGE-GOVERNANCE-PRE-LOCK, filed today) = **8 LOCK-mandatory**.

**Items processed at LOCK trigger** per BuildemUp LOCK-trigger protocol:
- 8 LOCK-mandatory backlog items
- All standing PROPOSED amendments (currently A12 only)
- Three-check protocol re-run (gap / audit / integrity)
- Then surface vN.LOCK-CANDIDATE for Ramalingam adjudication

---

*End of S48 critique-walk backlog delta.*
