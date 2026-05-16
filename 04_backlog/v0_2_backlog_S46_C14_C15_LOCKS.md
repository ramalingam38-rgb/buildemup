# v0_2_backlog_S46_C14_C15_LOCKS.md

**Backlog roll-up at S46 close.**
**Authored:** S46 close, post-C14 + C15 v0.2 LOCKs.
**Scope:** Cumulative C14 + C15 backlog as locked at S46. Inherited project-scope items from prior sessions noted but not re-enumerated (see prior backlog files in `04_backlog/`).

---

## Summary

| Component | LOCK-mandatory | Fast-revision | Data-unlock | Annual audits | Post-LOCK polish | Project-scope | Routed | TOTAL |
|---|---|---|---|---|---|---|---|---|
| C14 | 4 | 1 | 0 | 0 | 4 | 3 | 1 | **13** |
| C15 | 7 | 0 | 4 | 4 | 6 | 3 | 2 | **26** |
| **Combined (de-duped project-scope)** | **11** | **1** | **4** | **4** | **10** | **3** | **3** | **36** |

---

## C14 v0.2 LOCKED backlog (13 items)

### LOCK-mandatory (4)

| ID | Description | Effort |
|---|---|---|
| B-C14-BETWEENNESS-FORMULA-LOCK | Pin exact betweenness formula | S |
| B-C14-PRIVACY-GRADIENT-FORMULA-LOCK | Pin exact privacy-gradient monotonicity formula | S |
| B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK | Pin full transit-bedroom definition (A5 ships SKETCH; full LOCK still required) | S |
| B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION | Pin primary-edge architectural semantics | S |

### Fast-revision window (1)

| ID | Description | Effort |
|---|---|---|
| B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS | Cross-floor circulation metrics; bumped from post-v1.0 → 90-day window per A11 | L |

### Post-LOCK polish (4)

| ID | Description | Effort |
|---|---|---|
| B-C14-CACHE-SPLIT-IF-DIVERGENT | Split full_cache_key into geometry/advisory if divergent use case emerges | M |
| B-C14-ISOVIST-SUPPORT | Sight-line / isovist analysis | M |
| B-C14-METRIC-ACCRETION-AUDIT | Annual audit per A9 gate | S |
| B-C14-CONFIDENCE-BANDS-METRIC-RELIABILITY | Confidence bands / statistical reliability metadata; finer-grained than graph_size_category | M |

### Project-scope (3)

| ID | Description | Effort |
|---|---|---|
| B-PROJECT-PIPELINE-METADATA-CONTRACT | Convention for "upstream metadata threaded as params" | M |
| B-PROJECT-ADVISORY-UNIFICATION | Unify C14 + C15 + C16 advisories under versioned registry | L |
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | Cross-component metric-interpretation consistency | L |

### Routed (1)

| ID | Description | Routed to |
|---|---|---|
| B-C12-CATEGORY-NORMALIZATION-GOVERNANCE | Room-category normalization coordination | C12 maintainer |

---

## C15 v0.2 LOCKED backlog (26 items)

### LOCK-mandatory (7)

| ID | Description | Effort |
|---|---|---|
| B-C15-SEVERITY-RULE-TABLE-LOCK | Pin severity rules + severity_basis per rule | M |
| B-C15-CHECK-REGISTRY-LOCK | Pin the ~35-41 check set + epistemic_kind per check | L |
| B-C15-CULTURAL-PROFILE-V1-LOCK | Pin cultural_profile API + ≥3 sub-variants | M |
| B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK | Pin every runnable check's measurement formula | L |
| B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK | Pin unconventional-pattern detection rules | M |
| B-C15-MOAT-LINT | CI lint enforcing no numeric aggregation in C15 | S |
| B-C15-CULTURAL-PROFILE-COVERAGE | ≥3 sub-variants ship at LOCK with measurable behavioral differences | M |

### Data-dependency unlocks (4)

| ID | Description | Effort | Routed to |
|---|---|---|---|
| B-C15-WINDOW-DATA | Window placement engine upstream (Dim 4, partial Dim 8) | L | new upstream component |
| B-C15-FURNITURE-FIT-DATA | Furniture-fit engine upstream (Dim 9 + 10) | L | new upstream component |
| B-C15-FLOOR-METADATA | Floor metadata threading (Dim 7) | M | C12 / orchestrator |
| B-C15-ENVELOPE-ORIENTATION | Envelope orientation + climate data (rest of Dim 8) | M | C12 / orchestrator |

### Annual audits (4)

| ID | Description | Effort |
|---|---|---|
| B-C15-MOAT-AUDIT | Audit lint enforcement | S |
| B-C15-SEVERITY-AUDIT | severity_basis citation staleness review | S |
| B-C15-CHECK-ACCRETION-AUDIT | Three-criterion gate review per A8 | S |
| B-C15-CLASS-BIAS-AUDIT | Class-bias detection; scope amended walk #2 to cover data-availability bias (item 14) | S |

### Post-LOCK polish (6)

| ID | Description | Effort |
|---|---|---|
| B-C15-UX-FRAMING-GOVERNANCE | UX-layer presentation governance: render as "design considerations"; epistemic_kind visual differentiation; profile prominence | M |
| B-C15-LOCALIZATION | i18n for why_it_matters + suggested_mitigation | M |
| B-C15-CHECK-EXPLAIN-API | UX-facing "explain this check" API | S |
| B-C15-DEPRECATED-STATUS | CheckStatus.DEPRECATED for retired checks | S |
| B-C15-CULTURAL-PROFILE-EXPANSION | Beyond Indian variants | L |
| B-C15-EVIDENCE-QUALITY-TAXONOMY | Taxonomy ranking severity_basis citation strength | M |

### Project-scope (3 — inherited from C14)

| ID | Description | Effort |
|---|---|---|
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | Cross-component metric interpretation | L |
| B-PROJECT-ADVISORY-UNIFICATION | Unify advisories under versioned registry | L |
| B-PROJECT-LEGALITY-LAYERING | Separate universal / regional / cultural rules | L |

### Routed (2)

| ID | Description | Routed to |
|---|---|---|
| B-C13-FUTURE-WINDOW-PLACEMENT | Window placement contract w/ C15 (when engine exists) | C13 maintainer |
| B-C14-METRIC-EXPOSURE-FOR-C15 | Verify no new C15 needs require C14 amendment | C14 maintainer |

---

## Cross-component project-scope items (de-duped, 3)

These were created at C14 v0.2 and inherited by C15 v0.2. Single canonical reference:

| ID | Description | Effort |
|---|---|---|
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | Cross-component metric-interpretation consistency (was filed at C14 walk #1, reinforced at C15 walk #1) | L |
| B-PROJECT-ADVISORY-UNIFICATION | Unify C14 + C15 + C16 advisories under versioned registry | L |
| B-PROJECT-LEGALITY-LAYERING | Separate universal / regional / cultural rules (originally C14, reinforced at C15 § 0.3) | L |

Total project-scope: **3 unique items** (counted once, not twice).

---

## Obsolete / removed items

- **B-C15-RANKER-HINT-ACCESS-CONTROL** — deleted per C15 v0.2 A1 (RankerHint removed from C15 entirely; aggregation moved to C17)

---

## Items deferred to C16 / C17

None at S46. C14 + C15 are spec-only at S46 close; C16 + C17 specs not yet drafted.

---

## Reading notes for next Claude (S47)

1. The **LOCK-mandatory items (11 total: 4 C14 + 7 C15)** must close before either component reaches v1.0 LOCK. They are EXPECTED to surface during implementation, NOT before. v0.3+ critique walks during build refine them.

2. The **fast-revision window item (B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS)** must be addressed within 90 days of C14 v0.2 LOCK. If the window closes without it, it becomes a v2.0 breaking change.

3. The **data-dependency unlocks (4 C15 items)** are NOT blockers for C15 v1.0; they unlock additional check categories that ship as NOT_APPLICABLE at v1.0. Future upstream extensions (window engine, furniture engine) activate these without changing C15's schema.

4. The **annual audits** are post-LOCK governance discipline. Schedule them; document outcomes back to backlog file.

5. The **routed items (3 total)** belong to other component maintainers. C14/C15 implementation does NOT block on them, but coordination should happen as those components evolve.
