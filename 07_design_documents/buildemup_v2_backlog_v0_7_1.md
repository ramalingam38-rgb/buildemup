# BuildemUp† — v2 Backlog

**Purpose:** Explicit, tracked list of features deliberately deferred from v1.
Each item has a **trigger** that makes it move from "deferred" to "must-do."

This document is the single source of truth for "we know about this and chose
not to do it, here's why and when we will."

**v2 vision document:** for the competitive narrative ("what best-in-market
looks like for each of these"), see `docs/v2_vision.md`. This file tracks
**what + when**; the vision doc tracks **why it matters competitively**.

---

## v0.4 update

After v0.4 (trust controls + building-type architecture + platform readiness
scaffolding), the backlog is **smaller** in raw count but **deeper** in
quality. Items below are deliberately tracked so that "best in market when
we get there" is always remembered.

---

## Format

Each item has:
- **Item** — what it is
- **Origin** — when/why we first considered deferring
- **Status** — DEFERRED / IN-PROGRESS / DONE
- **Trigger** — the specific event that flips this to must-do
- **Estimated effort** — rough sizing for planning

---

## Structural engineering deferrals

### 1. Full P-M interaction diagrams for column design
- **Origin:** v0.3 review feedback (item 3, "column design still approximate")
- **Status:** DEFERRED
- **Trigger:** A licensed structural engineer reviewing our outputs flags that
  P-M curves are needed for honest decision-support. Or: enterprise customer
  requests detailed reinforcement design.
- **Estimated effort:** 2-3 weeks. Requires column reinforcement layout
  (longitudinal bars + ties), interaction chart generation, automated check.
- **Why not v1:** P-M curves are detailed-design-stage work. Our output is
  preliminary sizing — the real reinforcement layout happens with the
  structural engineer's drawings. Adding this would put us in territory we
  shouldn't claim.

### 2. Full IS 13920 for Zone V cities
- **Origin:** v0.3 scope decision
- **Status:** DEFERRED (Zone V refused with graceful error)
- **Trigger:** Decision to target NE India, Bhuj/Kutch region, Andaman, or
  any Zone V city.
- **Estimated effort:** 2 weeks. Mostly extending existing IS 13920 module
  with stricter rules (higher response reduction, lateral force checks,
  capacity design).
- **Why not v1:** No business case for Zone V markets in launch (our 6
  cities are all Zone II-IV).

### 3. Settlement differential modeling
- **Origin:** v0.3 review feedback (item 4, "foundation logic still binary")
- **Status:** DEFERRED
- **Trigger:** First customer complaint about cracks in walls due to
  differential settlement, OR expansion to expansive-soil regions
  (Maharashtra black cotton, Madhya Pradesh).
- **Estimated effort:** 3-4 weeks. Requires proper soil mechanics
  (consolidation, immediate vs long-term settlement).
- **Why not v1:** For uniform soil and isolated/raft foundations, differential
  settlement is rarely the binding constraint. Pile foundations (which
  inherently resist differential settlement) are already supported.

### 4. Time-based effects (creep, shrinkage, long-term deflection)
- **Origin:** v0.3 review feedback (item 6, "no time-based effects")
- **Status:** DEFERRED
- **Trigger:** Move into G+5 or higher buildings (where long-term deflection
  begins to matter), or large-span (>6m) commercial work.
- **Estimated effort:** 2-3 weeks.
- **Why not v1:** Negligible for G+2 residential with bays ≤ 4.5m.

### 5. Wall continuity / transfer beam check (full implementation)
- **Origin:** v0.3 review feedback (item 5, "load path complexity")
- **Status:** STUB ONLY (warning generated, no actual check)
- **Trigger:** Component 11 (Topology Mutation) is built — at that point
  we know the wall layout per floor and can check wall-stack continuity.
- **Estimated effort:** 1 week (once Component 11 exists).
- **Why not v1:** Requires the room/wall data structure that Component 9
  produces. Premature without Component 9.

### 6. Lateral analysis — full frame sway calculation
- **Origin:** v0.3 review feedback (item 2, "no lateral load distribution")
- **Status:** PARTIAL — IS 875 Part 3 wind load done, regularity check done
- **Trigger:** Customer complaints about visible sway, OR expansion to G+3+
  buildings, OR Zone V.
- **Estimated effort:** 2-3 weeks. Requires frame analysis with stiffness
  matrix or simplified equivalent static method.
- **Why not v1:** For regular G+2 residential with brick infill walls,
  IS 1893 cl. 7.10 permits simplified analysis (which we do). Real sway
  analysis only matters when irregularity is high.

---

## Codebase / architecture deferrals

### 7. Pydantic schemas (vs current dataclass+validation)
- **Origin:** v0.3 review feedback (item 2, "implicit contracts")
- **Status:** DEFERRED — using dataclass + `__post_init__` validation
- **Trigger:** First inter-module integration bug caused by silent type
  drift, OR adding 5+ more components (when manual validation becomes
  too much).
- **Estimated effort:** 2-3 days for migration + dependency add.
- **Why not v1:** Dataclass + post-init gives 80% of value with zero
  dependency. Pydantic adds a 5MB dependency for the remaining 20%.

### 8. YAML/JSON external config system
- **Origin:** v0.2 + v0.3 reviews (no non-developer editors yet)
- **Status:** DEFERRED
- **Trigger:** Hiring a non-developer (analyst, BD person, structural
  engineer reviewer) who needs to edit rates without touching code.
- **Estimated effort:** 1-2 weeks for clean migration.
- **Why not v1:** All editors are developers right now. Python dicts are
  type-checked, IDE-friendly, and version-control-clean.

### 9. Performance caching / memoization
- **Origin:** v0.2 + v0.3 reviews
- **Status:** DEFERRED
- **Trigger:** Component 11b (NSGA-II) is built and profiling shows
  Component 7 is the bottleneck.
- **Estimated effort:** 1 week. `functools.lru_cache` on grid generation,
  cost estimation, soil lookup.
- **Why not v1:** Component 7 runs in milliseconds. NSGA-II isn't built
  yet. Premature.

### 10. Pipeline integration tests
- **Origin:** v0.3 review feedback (item 8)
- **Status:** DEFERRED
- **Trigger:** Component 1 (Conversational Brief) is built — at that point
  we have a real input → Component 7 pipeline to test end-to-end.
- **Estimated effort:** 3-4 days.

### 11. Structured logging — actual usage in components
- **Origin:** v0.3 — utility built, not yet plumbed in
- **Status:** UTILITY DONE, INSTRUMENTATION PENDING
- **Trigger:** First debugging session where we wish we had logs.
- **Estimated effort:** 1-2 days to instrument all Component 7 sub-modules.

### 12. ComponentOutput base class — actual usage
- **Origin:** v0.3 — utility built, not yet adopted
- **Status:** UTILITY DONE, ADOPTION PENDING
- **Trigger:** When we ship Component 1 onwards — easier to make all new
  outputs inherit than retrofit.
- **Estimated effort:** Built into Component 1 from start (no migration).

---

## Cost / economics deferrals

### 13. Full Monte Carlo variability propagation
- **Origin:** v0.2 + v0.3 reviews
- **Status:** DEFERRED — sensitivity analysis added instead
- **Trigger:** Customer asks for probabilistic outputs ("90% chance cost is
  below ₹15L"), OR enterprise customer requires risk-quantified estimates.
- **Estimated effort:** 1-2 weeks (NumPy Monte Carlo, ~10K iterations).
- **Why not v1:** Sensitivity analysis (already shipped in v0.3) gives
  80% of the user-decision value at 5% of the effort.

### 14. Real-time supplier rate scraping
- **Origin:** v0.3 review feedback (item 5, "RateProvider still shallow")
- **Status:** DEFERRED — manual quarterly refresh
- **Trigger:** When manual refresh becomes a bottleneck (5+ cities, weekly
  market volatility).
- **Estimated effort:** 4-6 weeks. Real engineering work — scraping legal
  questions, supplier API agreements, validation pipeline.
- **Why not v1:** Quarterly manual updates are fine for 6 cities. Steel
  prices don't move that fast.

### 15. Time-of-year cost variation
- **Origin:** v0.3 review feedback (item 5)
- **Status:** DEFERRED — current rates are annual averages
- **Trigger:** Customer reports significant cost surprise due to monsoon
  or festival-season labour shortage.
- **Estimated effort:** 2 weeks. Add seasonality multipliers per city.
- **Why not v1:** Variability is captured in our ±% ranges. Seasonality is
  a refinement, not a missing feature.

---

## How to use this document

**At the start of every coding session:** read this file. If today's work
hits a trigger condition, that item moves from DEFERRED to IN-PROGRESS.

**At the end of every quarterly review:** check if any triggers are now
met. Move accordingly.

**When making a scope decision:** consult this list. If a request matches
something here with status DEFERRED, the answer is "not in v1, here's why."

---

## Items moved out of backlog (now in v0.3 production)

These were initially deferred but completed in v0.3:
- ✅ IS 13920 ductile detailing (Zone III + Zone IV) — was "trigger: Mumbai"
- ✅ IS 875 Part 3 wind load — was "trigger: coastal Mumbai"
- ✅ Pile foundation sizing — was "trigger: Mumbai reclaimed soil"
- ✅ Strap footing — was "trigger: tight urban plots"
- ✅ Slenderness ratio check — was "easy win, defer briefly"
- ✅ Geometric regularity gate — was "trigger: irregular topology shipped"
- ✅ Sensitivity analysis — was "trigger: decision-support quality"
- ✅ Multi-city rates (5 new cities) — was "trigger: market expansion"
- ✅ RateProvider min/max — was "trigger: honest variability"
- ✅ Error taxonomy — was "trigger: user-facing error quality"
- ✅ Confidence framework — was "trigger: consistency across modules"
- ✅ Stress test suite — was "trigger: edge case bugs found"

Each of these had a "v2 trigger" that was reached during the Mumbai
expansion decision. Keeping this list visible to remember that triggers
do fire, and we should respect them.

---

## Items moved out of backlog (now in v0.4 production)

These were either explicitly deferred or surfaced by the v0.3 review,
and completed in v0.4 — the "trust controls + platform readiness" release:

### Block A — Trust controls
- ✅ Three-level regularity (REGULAR/MODERATE/SEVERE) — was binary
- ✅ Severe-regularity refusal in orchestrator — was "warn but proceed"
- ✅ SCWB renamed to heuristic everywhere — was implied authority
- ✅ Wind + seismic load combination check — was siloed
- ✅ Centralised KB version registry with LAST_UPDATED — was scattered
- ✅ `format_for_user(error)` — never leaks internals — was missing
- ✅ `summarize_trace(trace_id)` for human-readable logs — was JSON only
- ✅ Per-output `kb_versions` + `trace_id` for reproducibility
- ✅ Prominent "PRELIMINARY DESIGN" banner at TOP of explain — was buried
- ✅ Explicit "WHAT WE CHECK / DON'T CHECK" disclosure section
- ✅ Reproducibility footer with KB versions + trace ID
- ✅ Confidence definitions visible in explain output
- ✅ Console JSON suppressed by default (clean user output)
- ✅ Structural sensitivity (soil + load) — was cost-only

### Block B — Building-type architecture
- ✅ `BuildingType` enum + `BUILDING_TYPE_REGISTRY` — was hardcoded residential
- ✅ 8 types architecturally supported (industrial/warehouse excluded)
- ✅ Per-type importance factor (educational/healthcare = 1.5×)
- ✅ Per-type IS 13920 mandate for important buildings
- ✅ Stubbed types refused gracefully via `UnsupportedConfigurationError`
- ✅ Per-type max floor enforcement
- ✅ Building type shown in explain output

### Block C — Platform readiness
- ✅ Brand/grade/IS-code on `MaterialRate` (e.g., "Ramco/Ultratech OPC 53 IS 12269")
- ✅ BOM-style derivation labels in cost output
- ✅ Vastu engine stub (5 high-impact rules, opt-in)
- ✅ Downstream consumer contract stubs (contractor / supplier / bank)
- ✅ Book-to-code pipeline pattern (folder structure + worked example)
- ✅ v2 vision document (`docs/v2_vision.md`)

These items represented the "controlling trust" pivot from the v0.3
review. The headline insight: **"You are now in the danger zone of
credibility"** — the goal of v0.4 was not adding capability but
controlling perceived authority. Mission accomplished.

---

## Items moved out of backlog (now in v0.5 production)

The v0.4 review was the most positive yet but identified seven specific
drawbacks. v0.5 closed all of them that were not deferred:

### Trust + perception fixes
- ✅ Confidence levels renamed: HIGH/MEDIUM/LOW → WELL_CONSTRAINED /
  REGIONAL_TYPICAL / DEPENDS_ON_CHOICE. Old names kept as aliases.
  Critical disclaimer added: confidence is about input certainty, NOT
  engineering correctness.
- ✅ Banner language strengthened: "RULE-BASED HEURISTIC ESTIMATE" /
  "NOT structural design" — was "Preliminary Design Estimate" which
  could still imply design authority.
- ✅ Load combination simplification disclosed in WHAT WE DON'T CHECK
  (we compare governing wind vs governing seismic, not full IS 875
  Part 5 matrix).
- ✅ Sensitivity scope limitation disclosed (soil + load only, not
  span variation or material strength).

### Architecture / scalability
- ✅ `ComponentContract` system — explicit input/output schemas with
  validation. Lightweight (no Pydantic). Component 7 registered.
  Prevents assumption drift across components 1-17.
- ✅ Engineer-validated override flag — preserves severe-irregularity
  refusal but adds audit-traceable bypass for engineer-validated plans
  (requires name, license, validation date).
- ✅ Vastu separation disclosure — `format_for_user()` always prepends
  prominent banner that Vastu is cultural preference, NOT engineering,
  and structural changes need engineer review.
- ✅ `get_data_freshness_report()` — surfaces how stale each KB module
  is (90-day cadence for rates, 365-day for codes). No more silent
  shipping of stale data.

### Items the v0.4 review flagged but we deferred to v2
The v0.4 review's three remaining drawbacks are deferred:
- **Frame analysis** (still no true structural analysis) — same answer
  as before. P-M curves, frame stiffness, dynamic response are detailed-
  design work. Disclosed in WHAT WE DON'T CHECK. v2 vision.
- **Pile foundation depth** (still conceptual) — adding fake skin-friction
  numbers would be worse than disclosure. Deferred. v2 vision.
- **Probabilistic confidence** (still rule-based) — Monte Carlo gives
  marginal improvement at significant complexity cost. Sensitivity
  analysis covers 80% of the value. Deferred. v2 vision.

These three are not bugs to fix — they are correct v1 boundaries with
clear v2 paths.

## Done in v0.6 (Trust + Legal Hardening Release)

v0.6 was the most legally-careful release in the project. Major theme:
positioning BuildemUp correctly as decision-support, never as an
engineer-replacement, with clear PENDING ENGINEER VALIDATION on every
output and explicit disclosures in every explain().

### Phase 1 — Real engineering
- ✅ Frame sanity engine (`components/c07/frame_sanity.py`) — Hardy
  Cross moment distribution + IS 456 cl. 39.6 Bresler interaction with
  the REAL formula (αn interpolated 1.0→2.0 per code). Outputs SAFE/
  WARNING/FAIL classification. Method disclosure honest: LEVEL 2 sanity
  check, NOT LEVEL 3 design.
- ✅ Load combinations (`components/c07/load_combinations.py`) — 5-combo
  set per Indian practice. Wind+EQ never combined per IS practice
  (verified by web research). Method disclosure explicit.
- ✅ Real IS 1904 soil bearing capacity (`kb/soil_classification.py`)
  with 12 soil classes. Hard rock 450-3300 kN/m² (real range, not
  document's wrong values). Black cotton flagged expansive. Reclaimed
  fill requires pile. Every output includes "Actual SBC must be
  confirmed via soil test" disclaimer.
- ✅ Extended sensitivity from 2 drivers (soil, load) to 4 drivers
  (+span, +material grade).

### Phase 2 — Architecture
- ✅ Config-driven rules pilot (`kb_rules/seismic_rules.json` +
  `utils/kb_rules_loader.py`). Schema validation, caching, 8 typed
  accessor functions. Parity test caught real bug on first run (Zone
  III steel% was 1.2 in JSON vs 1.5 in Python — exactly why parity
  test exists).
- ✅ Domain layer (`/domain/` package): Building, BuildingMeta,
  Envelope, Floor, FloorType, Column, ColumnLocation, DomainGrid.
  Lightweight dumb dataclasses with validation. Components import
  these instead of redefining shapes.
- ✅ ComponentContract enforcement test — auto-discovers all top-level
  c{NN}_*.py files and asserts each has registered contract. Fails
  build with helpful error if missing. The "CI rule".

### Phase 3 — Trust + legal hardening
- ✅ Renamed `engineer_validated_override` → `user_claims_engineer_reviewed`.
  Old name still works as back-compat alias. Audit-fields error
  message reframed: "We do NOT verify engineer claims, but record
  name/license/date for the user's audit trail. The engineer is your
  own consultant; BuildemUp does not verify or endorse them."
- ✅ Added `user_engineer_consultant: str` optional session-only field.
  Never appears in output.
- ✅ `validation_status: "PENDING ENGINEER VALIDATION"` on every output.
  With user-claim variant: "PENDING ENGINEER VALIDATION (user claims
  engineer reviewed — UNVERIFIED)". BuildemUp itself can NEVER
  transition out of "pending" — only the engineer's stamp can.
- ✅ Warning text rewrite: "⚠ ENGINEER OVERRIDE ACTIVE" → "⚠ UNVERIFIED
  USER CLAIM" with explicit text about no verification, no endorsement.
- ✅ Engineering depth axis (`utils/engineering_depth.py`) —
  EngineeringDepth enum LEVEL_1_RULE_BASED / LEVEL_2_FRAME_CHECKED /
  LEVEL_3_ENGINEER_DESIGNED. v0.6 outputs are LEVEL_2. LEVEL_3 is
  engineer-only by design (no `level_3_indicator()` function exists).
- ✅ Freshness enforcement (`utils/kb_versions.py` extended) — 3-tier:
  <cadence=OK, cadence-to-2×=WARN_DEGRADE_CONFIDENCE, >2×=BLOCK_STALE.
  When WARN, confidence degrades one level (WELL_CONSTRAINED→
  REGIONAL_TYPICAL).
- ✅ Legal & statutory disclosures (`utils/legal_disclosures.py`) —
  6-section block in every explain() output (per Q2 decision (a)):
  structural engineer required, Indian municipal permit requirement
  (CMDA/BMC/MCD/BBMP named, "stamped plan" emphasized), no engineer
  endorsement, limitation of liability, PII handling session-only,
  preliminary soil+load assumptions caveat.
- ✅ PII handling: `purge_engineer_data(dict)` redacts engineer name/
  license/date/consultant before logging or export. Original dict
  unchanged (returns new dict).
- ✅ Frame sanity wired into orchestrator output. Per-column Bresler
  interaction shown. Worst 3 columns surfaced if WARN/FAIL.

### Items the v0.6 review identified but deferred to v2
- **Full IS 875 Part 5 load combination matrix** — we ship 5 governing
  combos that cover residential adequately. Full matrix (with
  directional + torsional) is detailed-design work for engineer.
- **Incremental rule migration to JSON** — only seismic_rules done in
  v0.6. Remaining order per migration recipe: load_estimation →
  soil_foundation_rules → rcc_design_rules → material_rates. Each
  follows the 5-step recipe: create JSON, write loader, replace read
  layer only (not logic), parity test old==new, schema validation.
- **3D frame analysis** — same answer as v0.4/v0.5: detailed-design
  scope. v2 vision tracks this.

## Done in v0.7 (6 Drawbacks Closure Release)

The v0.6 review gave the most positive verdict yet ("first truly
production-grade release") but flagged 6 system-level drawbacks. v0.7
closes all six. After research to verify IS 1893 drift limits + IS 456
serviceability + cracked-section factors match code exactly.

### Drawback 1 — Global Stability / Drift Check ✅
- `components/c07/global_stability.py` — IS 1893:2016 cl. 7.11.1.1
  (0.004h drift limit) + IS 456 serviceability (H/500 sway).
- Lateral stiffness k = Σ(12·E·Ie/h³) with cracked-section factor
  0.7·Igross per IS 1893:2016 cl. 6.4.3.
- Per-storey SAFE/WARNING/FAIL classification.
- Base shear estimator per IS 1893 cl. 7.6 (V_B = A_h × W).
- Wired into orchestrator with FAIL warnings surfaced prominently.
- Smoke-tested: G+1 residential = 20% of limit (SAFE); G+3 undersized
  = 522% of limit (FAIL, correctly flagged).

### Drawback 2 — Rich Domain (Partial) ✅
- `Building.total_imposed_load_kn()` — aggregates live loads across
  floors. Previously computed inline in Component 7, now domain-owned
  so future Component 13 (MEP) doesn't duplicate the calculation.
- `Building.validate_for_structural_analysis()` — returns issue list
  (empty = valid). Catches severe aspect ratio, zero habitable floors,
  tiny envelope.
- Full rich-domain migration deferred to v0.8 when other components
  exist and can benefit from the pattern together.

### Drawback 3 — Rule Migration (2nd of 5 modules) ✅
- `kb_rules/load_rules.json` extracted from `kb/load_estimation.py`.
  Includes dead loads, live loads by floor type, concentrated loads,
  wall loads, partial safety factors.
- Schema validation enforces live loads > 0 AND safety factors ≥ 1.0.
- 7 typed accessors in `kb_rules_loader.py`.
- 7 parity tests verify JSON == Python constants exactly.
- Remaining modules to migrate (flagged for v0.7.1 / v0.8):
  soil_foundation_rules, rcc_design_rules, material_rates.

### Drawback 4 — Legal Compact Mode ✅
- `format_legal_disclosures_block(mode='full'|'compact')` — default
  remains 'full' per Q2 decision (back-compat preserved).
- Compact mode: 3-point summary + pointer to full text (~820 chars
  vs 2490 full = 67% shorter).
- Critical points retained in compact: not-a-stamped-plan, no engineer
  endorsement, session-only PII.

### Drawback 5 — Action-Layer Recommendations ✅
- `Recommendation` dataclass with CRITICAL/IMPORTANT/OPTIONAL priority.
- Attached to all 4 sensitivity drivers (soil, load, span, material).
- Threshold-based: e.g., span 3.8m → 4.6m crossing 4m beam-depth tier
  triggers `[IMPORTANT] Keep longest span under 4.0m`.
- `top_recommendations` property ranks by priority.
- `format_recommendations_only()` compressed view.
- Wired into `explain()` as TOP RECOMMENDATIONS section.

### Drawback 6 — Insights Loop ✅
- `utils/insights.py` with `aggregate_logs()`, `InsightsReport`
  dataclass, `run_weekly_report()` CLI.
- Text + CSV output formats.
- Aggregates: execution counts, top warnings, cost distribution
  (min/p25/p50/p75/max), refusal reasons, per-city counts, frame
  sanity outcomes, confidence distribution.
- Simple counting — no ML / anomaly detection (v2 scope).

### Items the v0.7 review identified but deferred
- **Full rich-domain migration** — 1 method done as worked example.
  Full migration in v0.8 when Components 1/4/8/13 exist.
- **3 remaining rule migrations** — soil, RCC, material rates.
  Queued for v0.7.1/v0.8 (follows same 5-step recipe).
- **ML-based insights** — simple counting sufficient for launch.
- **Full 3D frame analysis / P-delta** — engineer's ETABS scope.

## Done in v0.7.1 (3 of 6 Drawbacks from v0.7 Review)

After the v0.7 review flagged 6 new drawbacks, we triaged them carefully
rather than executing all 6 reflexively. Three were genuine v1 issues,
three were either theoretical or premature optimization for our stage.

### Triage decision (locked)

**Executed (real v1 value):**
- Drawback 3 — Domain-only contract enforcement
- Drawback 4 — Single-source rules (JSON authoritative)
- Drawback 5 — Drift realism (beam + infill factors)

**Deferred to v2 (correctly out of scope for launch):**
- Drawback 1 — Unified StructuralModel. Theoretical risk only;
  stiffness and strength come from the same cross-section, so
  inconsistency between frame sanity and drift check is not a real
  physics hazard. ~1000+ lines of refactor for no real benefit.
- Drawback 2 — Simulation-based dynamic recommendations. Would mean
  Component 7 calls itself recursively with varied inputs. 5-10× slower
  per execution for marginal improvement over threshold-based
  recommendations. Premature optimization.
- Drawback 6 — Insights → feedback loop. Requires production data
  we don't have yet. Building a solution to a theoretical problem
  before having real users.

### Drawback 5 — Drift Realism ✅
- `BEAM_CONTRIBUTION_FACTOR = 1.3` (moment-frame rigidity from
  beam-column continuity).
- `INFILL_CONTRIBUTION_FACTOR_WITH_WALLS = 1.5` (URM infill walls,
  typical Indian residential per IS 1893:2016 infill provisions).
- `INFILL_CONTRIBUTION_FACTOR_NO_WALLS = 1.0` for open stilt / soft
  storey cases.
- Threaded `has_infill_walls` parameter through `check_storey_drift()`
  and `run_global_stability_check()`. Default True.
- Updated method disclosure to explicitly list factors.
- Result: G+1 residential drift ~20% → ~10% (halved = more realistic).
  Open-stilt correctly shows higher drift (soft-storey signal).

### Drawback 3 — Domain-Only Contracts ✅
- `_DOMAIN_TYPE_NAMES` set with Building / Envelope / Floor / Column /
  ColumnLocation / DomainGrid / BuildingMeta / FloorType.
- `_is_domain_type_name()` detector handles plain types AND container
  wrappers: `tuple[Floor, ...]`, `list[Column]`, `Optional[Envelope]`.
- `_check_is_domain_object()` rejects raw dicts, primitives, None.
- Integrated into `validate_input()` — contracts with domain types
  fail with clear message pointing to the v0.7.1 enforcement rule.
- Future Components 1, 4, 8 etc. cannot ship with dict-shaped inputs.

### Drawback 4 — Single-Source Rules (JSON Authoritative) ✅
- `kb/seismic_detailing.py`: all 11 numeric constants now load from
  `kb_rules/seismic_rules.json` at module import time via
  `_SEISMIC = _load_rules("seismic_rules")`.
- `kb/load_estimation.py`: all 14 numeric constants now load from
  `kb_rules/load_rules.json` via `_LOADS = _load_rules("load_rules")`.
- Public constant names unchanged — downstream code still uses
  `SEISMIC_ZONE_FACTORS["III"]` and `SAFETY_FACTORS["dead_load"]`.
- Dual-source drift now structurally impossible: Python reads from
  JSON, so they literally cannot diverge.
- Parity tests kept as regression safety net — they'll catch anyone
  who accidentally reintroduces a parallel Python literal.

### Remaining rule migrations (still 3 to go)
- `kb/soil_foundation_rules.py` → `kb_rules/soil_rules.json`
- `kb/rcc_design_rules.py` → `kb_rules/rcc_rules.json`
- `kb/material_rates_*.py` → `kb_rules/material_rates.json`
Follow same 5-step recipe. Not urgent (seismic + loads were the
highest-volume / most-changed modules). Queue for v0.8 or when the
next code update is needed.
