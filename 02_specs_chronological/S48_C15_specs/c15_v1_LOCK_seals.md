# C15 v1 LOCK Seals — Triple Seal Document

**Status:** v0.3 PROPOSED LOCK seals — PENDING Ramalingam LOCK adjudication.
**Closes:** B-C15-SEVERITY-RULE-TABLE-LOCK, B-C15-CHECK-REGISTRY-LOCK,
B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK.
**Origin:** S48 Path A execution.

This document is the formal seal of the three artifacts that v0.3 →
v1.0 LOCK depends on. Once Ramalingam locks v0.3, these three frozen
descriptors become governance-mandatory baselines: changes after LOCK
require Inv P15 (registry version bump) + § 14.1 (check-addition gate,
A8/A9) + § 14.2 (severity-change gate, this v0.3) governance.

---

## Seal 1 — Severity Rule Table v1 (B-C15-SEVERITY-RULE-TABLE-LOCK)

### What is sealed

`severity_rule_table.SEVERITY_RULE_TABLE_V1` — the canonical
`(check_id, status, cultural_profile_or_None) → CheckSeverity` map
plus the 10 cultural-profile-specific override rules added at S48 Path
A (B-C15-CULTURAL-PROFILE-V1-LOCK).

### Rule count

| Section | Count |
|---|---|
| Dim 1 default rules (P1.1 + P1.3) | 6 |
| Dim 2 default rules (P2.1-2.5) | 15 |
| Dim 3 default rules (P3.1-3.4) | 12 |
| Dim 5 default rules (P5.1-5.5) | 15 |
| Dim 6 default rules (P6.1) | 3 |
| Dim 7 default rules (P7.1-7.3) | 9 |
| **Cultural profile-specific (S48)** | **10** |
| **Total at v1 seal** | **70** |

### Default-rule audit

Every RUNNABLE check has 3 default rules (PASS / WARN / FAIL).
Deferred checks have 0 rules — they bypass severity lookup. The
`verify_rule_table_integrity` function (already in module) enforces
this invariant against the registered check_id set.

### Profile-override audit (B-C15-CULTURAL-PROFILE-V1-LOCK)

| Profile | Override check_ids | Total override rules |
|---|---|---|
| INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN | P3.4, P5.4 | 4 |
| INDIAN_MIDDLE_CLASS_KERALA_COURTYARD | P3.4, P5.4 | 4 |
| INDIAN_NRI_RETURNEE | P5.3 | 2 |
| **Total** | | **10** |

Three other profiles (COMPACT_URBAN, GENERIC, LOWER_INCOME_INCREMENTAL)
inherit defaults. Per A3 LOCK test: at least 3 distinct severity
signatures across the 6 profiles on the differentiating-pair set.

### Citation integrity audit

All 70 rules carry `severity_basis` strings of ≥ 20 characters (Inv
P18, A4). Sources cited:
- NBC 2016 Part 3 §§ 12.2-12.4 (regulatory minimums)
- Neufert + Ching (architectural-heuristic + ergonomic standards)
- Hillier 1984 / 1987 (space syntax, step-depth, betweenness)
- Lifetime Homes Standard (accessibility heuristics)
- Indian residential POE (post-occupancy field practice)
- A3 cultural-lens rationale per profile docstring

### Post-LOCK change discipline

Any future change to SEVERITY_RULE_TABLE_V1 requires § 14.2 governance
(this v0.3 amendment): changelog with source citation, backward-compat
review against v1 reference layouts, registry version bump, impact
annotation.

### Seal artifact

`SEVERITY_TABLE_VERSION` (referenced by Inv P15 cache-key composition)
pinned at **v1** as of v0.3 LOCK candidate. SEVERITY_RULE_TABLE_V_SUB2
back-compat alias preserved.

---

## Seal 2 — Check Registry v1 (B-C15-CHECK-REGISTRY-LOCK)

### What is sealed

`registry.build_registry()` — the canonical 41-check registry
spanning 10 dimensions per spec § 1.4.

### Registry contents

| Dim | Module | RUNNABLE | DEFERRED | Total |
|---|---|---|---|---|
| 1 | dim01_no_wasted_space | 2 (P1.1, P1.3) | 2 (P1.2, P1.4) | 4 |
| 2 | dim02_room_sizes | 5 (P2.1-P2.5) | 0 | 5 |
| 3 | dim03_logical_flow | 4 (P3.1-P3.4) | 0 | 4 |
| 4 | dim_deferred (natural_light) | 0 | 4 | 4 |
| 5 | dim05_privacy | 5 (P5.1-P5.5) | 0 | 5 |
| 6 | dim06_no_bottlenecks | 1 (P6.1) | 3 (P6.2-P6.4) | 4 |
| 7 | dim07_first_floor_living | 3 PARTIAL (P7.1-P7.3) | 1 (P7.4) | 4 |
| 8 | dim_deferred (outdoor) | 0 | 4 | 4 |
| 9 | dim_deferred (storage) | 0 | 4 | 4 |
| 10 | dim_deferred (multi_functional) | 0 | 3 | 3 |
| **Total** | | **20** | **21** | **41** |

### Registry invariants verified at LOCK

- **Inv P12:** every registered check produces exactly one
  ProblemCheck or DeferredCheck per candidate. Verified by
  `test_c15_orchestrator_integration.test_invariant_p12_one_record_per_check`.
- **Inv P3:** check_id format `P{dim}.{idx}`; lex-ASC ordering enforced
  in ProblemReport. Verified by foundational tests.
- **Inv P14:** check IDs are stable across versions (deprecation
  protocol per future v1.x is the only retirement path).

### Post-LOCK change discipline

Any check addition requires § 14.1 (A8/A9 governance gate). Any
check retirement requires the protocol filed under
B-C15-CHECK-ACCRETION-AUDIT extension (S48 walk #1 item 2).

### Seal artifact

`C15_CHECK_REGISTRY_VERSION` pinned at **1** as of v0.3 LOCK candidate.

---

## Seal 3 — Measurement Formulas v1 (B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK)

### What is sealed

Every threshold, ratio, and constant used by RUNNABLE checks across
dims 1-7 + the pattern detectors.

### Threshold inventory

#### Dim 1 (no wasted space)

| Constant | Value | Source citation |
|---|---|---|
| P1.1 circulation-fraction WARN threshold | 0.15 (15%) | Indian residential POE rule-of-thumb |
| P1.1 circulation-fraction FAIL threshold | 0.20 (20%) | Indian residential POE rule-of-thumb |
| P1.3 aspect-ratio WARN threshold | 2.5 | Neufert + Ching habitable-room guidance |
| P1.3 aspect-ratio FAIL threshold | 3.0 | Neufert + Ching habitable-room guidance |

#### Dim 2 (room sizes)

| Constant | Value | Source citation |
|---|---|---|
| P2.1 habitable-room min area | 9.5 m² | NBC 2016 Part 3 § 12.2 (regulatory) |
| P2.2 kitchen min area | 5.0 m² | NBC 2016 Part 3 § 12.3 (regulatory) |
| P2.2 combined kitchen-dining min | 7.5 m² | NBC 2016 Part 3 § 12.3 |
| P2.3 bathroom min area | 1.8 m² | NBC 2016 Part 3 § 12.4 (regulatory) |
| P2.3 WC min area | 1.1 m² | NBC 2016 Part 3 § 12.4 |
| P2.3 combined bathroom min | 2.8 m² | NBC 2016 Part 3 § 12.4 |
| P2.4 bedroom Neufert FAIL | 6.0 m² | Neufert + Ching (queen-bed + circulation) |
| P2.4 bedroom Neufert WARN (standard) | 9.0 m² | Neufert + Ching adequacy |
| P2.4 bedroom Neufert WARN (master) | 12.0 m² | Neufert + Ching master |
| P2.5 living-room baseline | 12.0 m² | Indian residential POE for 3-4 BHK |

#### Dim 3 (logical flow)

| Constant | Value | Source |
|---|---|---|
| P3.1 step-depth FAIL | > 4 from entry | Hillier 1984 space syntax |
| P3.1 step-depth WARN | == 4 from entry | Hillier 1984 |
| P3.1 step-depth PASS target | ≤ 3 from entry | Hillier 1984 ergonomic |

#### Dim 5 (privacy)

| Constant | Value | Source |
|---|---|---|
| P5.2 master step-depth WARN | < 3 | Hillier 1984 privacy gradient |

#### Dim 7 (first-floor living)

(Threshold-free; checks are presence/absence of floor-mapped rooms.)

#### Pattern detector thresholds (new — sealed today)

| Constant | Value | Source |
|---|---|---|
| COMPACT_INCREMENTAL_AREA_THRESHOLD_M2 | 55.74 | 600 sqft per UNCONVENTIONAL_PATTERN_NAMES docstring |
| COMPACT_INCREMENTAL_ROOM_COUNT_MIN | 4 | UNCONVENTIONAL_PATTERN_NAMES docstring |
| courtyard_centered habitable neighbors | ≥ 4 | UNCONVENTIONAL_PATTERN_NAMES docstring |

#### Coverage quality thresholds (new — sealed today)

| Constant | Value | Source |
|---|---|---|
| CoverageQuality HIGH threshold | ratio ≥ 0.70 | v0.3 A12 § 14.3 derivation rule |
| CoverageQuality MEDIUM threshold | 0.40 ≤ ratio < 0.70 | v0.3 A12 § 14.3 derivation rule |
| CoverageQuality LOW threshold | ratio < 0.40 OR total == 0 | v0.3 A12 § 14.3 |

### Post-LOCK change discipline

Threshold changes are NOT free. Each requires:
1. § 14.1 governance if new check addition; § 14.2 if existing.
2. Updated citation in `CITE_*` constant + audit that ≥ 20 char (Inv
   P18).
3. Registry version bump (Inv P15).
4. Backward-compat review against B-C15-LAYOUT-DIVERSITY-AUDIT
   reference corpus (when that ships post-LOCK).

### Seal artifact

All threshold constants frozen as module-level `Final[...]` and
named with their numeric value in the constant identifier where
possible (e.g., COMPACT_INCREMENTAL_AREA_THRESHOLD_M2 is named
explicitly). Audit traceability: grep the codebase for any
threshold-shaped literal not bound to a `Final[]` constant → flag
for documentation.

---

## Unified governance triple after these three seals

| Artifact | Version pin | Change protocol |
|---|---|---|
| Severity rule table | SEVERITY_TABLE_VERSION = v1 | § 14.2 gate |
| Check registry | C15_CHECK_REGISTRY_VERSION = 1 | § 14.1 gate |
| Measurement formulas | thresholds in `Final[]` constants | § 14.1 (additions) / § 14.2 (severity-coupled changes) |

These three seal together comprise the **value layer** of C15 at v1
LOCK. Per S48 critique-walk-2 item 11, this is the de facto "value
engine" of the component — the algorithm machinery (orchestrator
phases, check protocol, registry traversal) is value-neutral; the
seals define what C15 cares about.

---

## Status banner

**v0.3 PROPOSED LOCK seals. PENDING Ramalingam LOCK adjudication.**

Per BuildemUp LOCK-trigger protocol: locking v0.3 spec + these three
seals + closing remaining LOCK-mandatory items advances the spec to
v1.0.LOCK-CANDIDATE state.

---

*End of v1 LOCK triple seal document.*
