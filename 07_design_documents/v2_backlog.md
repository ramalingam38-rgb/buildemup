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

## Done in v0.7.2 (Insights Feedback Loop — FINAL Component 7 Release)

User directive: close the insights loop NOW (v0.7.1 review had deferred
it), then move to Component 1. No more review cycles on Component 7.

### Insights Feedback Loop (Deferred #3 from v0.7.1 — REOPENED and closed)

- `utils/insights_buffer.py` — thread-safe in-memory ring buffer
  (maxsize=200) of `ExecutionSignature` objects. Resets on deployment
  restart; patterns rebuild in ~10 executions. Zero ops overhead.
- `ExecutionSignature` — lightweight pattern fingerprint (NO PII):
  city, zone, floors, warnings (≤10 × 80 chars), frame sanity result,
  drift result, cost bucket in lakhs, validation variant.
- `ProactiveGuidance` dataclass with `has_meaningful_signal` flag.
  Surfaces top-3 warnings + city distribution + frame/drift outcomes.
- Thresholds: `MIN_EXECUTIONS_FOR_INSIGHTS = 10` (prevents noise),
  `MIN_OCCURRENCE_RATE = 0.20` (warning must appear in ≥20% of plans).
- Wired into `StructuralGridOutput.proactive_guidance`. `explain()`
  shows "PROACTIVE GUIDANCE (patterns from recent plans)" section
  only when signal is meaningful; gracefully omitted otherwise.
- Defensive try/except around record() so insights failures never
  crash user requests.
- 18 tests in `tests/test_v072.py` (all pass first run): buffer
  basics, signal threshold, top-N aggregation, orchestrator
  integration, signature builder edge cases, thread-safety
  (10 threads × 100 records).

### Component 7 = DONE

v0.3 → v0.7.2 across 6 review cycles. Every cycle surfaced real
improvements. After v0.7.2, Component 7 is:

- Structurally defensible (IS 456/1893/13920 + realistic drift model)
- Legally hardened (PENDING ENGINEER VALIDATION everywhere)
- Decision-oriented (threshold-based action layer with CRITICAL /
  IMPORTANT / OPTIONAL priorities)
- Self-improving (proactive guidance from recent execution patterns)
- Architecturally locked (domain-only contracts enforced, single-
  source rules via JSON)

**274 PASS across 14 test suites.** No more review cycles on
Component 7 until real user signal changes priorities.

### Items DEFERRED to v2 (LOCKED — no more debate)

These are real v2 items, not bugs:

- **Unified StructuralModel** — same-cross-section invariant makes
  today's system physically consistent. Full model is v2 scope.
  Catch via: simple consistency assertion layer (added or skipped
  in v0.8 depending on signal).
- **Simulation-based recommendations** — threshold-based is fine
  for launch. Revisit if production data shows thresholds miss
  important cases.
- **Persistent insights storage** — in-memory is fine for v1.
  Railway volumes or cloud DB in v0.8+ when cross-deployment
  patterns become valuable.
- **ML-based anomaly detection on logs** — need production data
  first. Not before 1000+ real executions.
- **3 remaining rule migrations** (soil, RCC, material rates) —
  queue for v0.8. Not urgent.
- **Full 3D frame analysis / P-delta** — engineer's ETABS scope.

### Next: Component 1 (Brief Capture)

Per user directive. Component 1 feeds Component 7. With
ComponentContract enforcement in place (v0.7.1), the handshake
between them is architecturally clean by construction.

---

## v0.8 update — Component 1 v0.1 shipped

Component 1 (Brief Capture Engine) v0.1 is complete. All 10 drawbacks
from SPEC_v0.2 were addressed in code. 122 new tests added, all pass.
274-test Component 7 baseline still fully green — zero regression.

### What shipped in Component 1 v0.1 (for reference)

- Domain objects (`Plot`, `Setbacks`, `FloorRequirement`, `Brief`, etc.)
- Setback calculator with plot-type branching (DETACHED / SEMI_DETACHED /
  CONTINUOUS) and Chennai TNCDBR full + NBC fallback for 5 cities
- Room composer with circulation factor 1.30 + auto-staircase enforcement
- Parking feasibility check (width-based)
- Vastu 3-tier opt-in (OFF / PARTIAL 7 items / FULL 15+ items), INFO-only
- Budget bridge to Component 7 (single source of truth for cost)
- Phased construction suggestion (55% ground-only rule)
- Top-3 guidance prioritisation
- ASSUMPTIONS USED transparency section
- BriefCaptureEngine orchestrator with explain() rendering 11 sections
- ComponentContract declaration with 13 new domain types enforced
- 4-step Tailwind form (HTML/vanilla JS/CSS), stdlib HTTP server
- localStorage save/resume with browser-local token

### Component 1 v0.2 queue — deferred to next release

These were explicitly deferred from v0.1 per SPEC_v0.2 Section 14:

- **Email-resume-link cross-device save** — needs server-side storage.
  Pair with auth/billing component when we build that. **Trigger:** when
  user-retention data shows significant drop-off at save-and-return points,
  OR when the auth component ships.

- **Full 5 non-Chennai city DCRs** — Bangalore, Hyderabad, Mumbai, Pune,
  Delhi currently use NBC fallback. Each needs its city-specific setback
  rule tables added to `setback_rules.json`. **Trigger:** v0.1 live user
  data shows ≥10 users per city from that list (or v1 launch decision —
  whichever comes first).

- **Mobile-optimized form UX** — current form works on mobile but isn't
  tuned for it. Needs responsive step indicator, larger tap targets, and
  probably consolidating steps 3+4 on small screens. **Trigger:** mobile
  traffic > 30% of form sessions.

- **Field-level validation feedback** — current form only validates on
  Next-button click (required fields) and on submit (server-side). v0.2
  should add inline hints: "Budget too low for plot size — expect
  STRONG_CONCERN on submit." **Trigger:** friction data from v0.1 shows
  users iterating submit → fix → resubmit loop.

- **Additional requirements as structured input** — currently a free-text
  textarea. v0.2 could offer a checklist of common requests (solar,
  elderly-friendly, pet-friendly, home office, rainwater harvesting)
  that map to structured fields Component 4 (layout) can consume.
  **Trigger:** Component 4 scoping — the layout engine needs structured
  requirement input anyway.

- **Multi-language form UI** — English only in v0.1. Tamil first (home
  market), then Hindi. **Trigger:** regional user data from v0.1 launch.

- **Conversational / LLM-based brief capture** — free-text "tell me
  about your dream home" that extracts structured brief via LLM.
  Explicitly deferred to v2 per Q1 decision in SPEC_v0.2. **Trigger:**
  v1 product-market fit established; separate R&D track.

### Component 1 v0.1 known limitations (not bugs)

All documented in `DEPLOY.md`. Summary:
- Save/resume is localStorage-only
- 5 of 6 cities use NBC fallback (Chennai TNCDBR full)
- No mobile-specific tuning
- No inline validation feedback
- No conversational input
- User email/phone stored session-only

### Next: Component 2 or Component 4?

Component 7 (structural) is stable. Component 1 (brief capture) is live.
The downstream question is now **what does the user see after submitting
the brief?** Two candidates:

- **Component 2 (Feasibility)** — checks whether the brief is physically
  achievable on the plot. Rough area estimate vs available envelope,
  flag impossibilities (8 rooms on 60 sqm), surface budget/spec trade-offs.
  *Low-hanging fruit; mostly rules on top of what Component 1 + Component
  7 already compute.*

- **Component 4 (Layout)** — generate actual floor plan candidates that
  satisfy the brief. Much bigger scope — spatial reasoning, adjacency
  graphs, room-placement constraints, Vastu/circulation/privacy scoring.

**Recommendation: Component 2 first.** It's 2-3 sessions of work, closes
the obvious gap between "your brief is captured" and "here's what's
possible," and exercises the Component 1 → downstream contract pattern
that Component 4 (much bigger) will rely on. **Trigger for Component 4:**
Component 2 shipped + live users asking "OK but where do the rooms go?"

---

## v0.9 progress update — Sessions A, B, C complete

The "v0.2 queue" partially shipped early in v0.9 after Ramalingam pushed
back on 4 of the deferral decisions. Status as of v0.9 Session C:

### Shipped in v0.9
- **Session A — drawback fixes**: 6 of 12 review drawbacks closed
  (#2 budget framing, #3 envelope transparency, #4+#6 wording fixes,
  #5 size-aware circulation factor with IS 3861-2002 backing,
  #8 risk_level rename, #9 top-3 cumulative summary). 18 new tests.
- **Session B — server save/resume**: SQLite-backed cross-device save,
  30-day TTL, resume URL works on any device. Replaces v0.1 localStorage-
  only flow. 22 new tests.
- **Session C — Mumbai DCPR 2034 + Delhi MPD-2021**: Real city DCRs
  added with disclosure text rendered inline in explain() and exposed
  in API response. 21 new tests. Schema validator made data-driven so
  remaining cities just need JSON additions. **3 of 6 cities now have
  real DCRs** (Chennai TNCDBR + Mumbai DCPR + Delhi MPD).

### Still queued for v0.9 Session D
- **Bangalore RMP/BBMP setback rules** — currently NBC fallback
- **Pune PMC setback rules** — currently NBC fallback
- **Hyderabad GHMC setback rules** — currently NBC fallback

After Session D, all 6 launch cities have real DCRs (no NBC fallbacks
for supported cities). Session E packages v0.9 release.

### New deferrals identified during v0.9 work

**Mumbai zone selector (Island City vs Suburbs)** — DCPR 2034 has
different setback rules for Island City (south of Mahim/Sion) vs
Suburbs (rest of MCGM). v0.9 defaults to SUBURBS values (most homebuilders
fall there). Adding `Plot.mumbai_zone: ISLAND_CITY | SUBURBS` is a clean
v1.0 addition. **Trigger**: ≥5 Mumbai users from Island City addresses,
OR explicit user request.

**Delhi setback table verification against printed DDA handbook** —
v0.9 values are conservative reads of the publicly-available secondary
sources (Tron Homes, AssetYogi, Prithu, South Delhi Prime). The exact
Clause 4.4.3 table is in the printed DDA handbook. Values may be off by
±0.5-1m vs the printed schedule. v1.0 should verify against an authoritative
source. Disclosure already says "verify with DDA before construction" —
appropriate caveat. **Trigger**: first Delhi user reports a discrepancy
OR before public Delhi launch.

**CostProviderInterface abstraction (Drawback #1 from review)** —
Component 1 is tightly coupled to Component 7 for cost. Premature to
abstract now since there's only one cost provider. **Trigger**: when a
second cost provider is needed (external partner quote integration,
multi-provider rate cards). Then extract `CostProviderInterface` and
make C7 the default implementation. Until then, the direct call is fine.

**Email-based resume link** — v0.9 Session B ships URL-based cross-device
save, but no email delivery. Adding SMTP is real infrastructure
(deliverability, bounces, SPF/DKIM). When it's worth that cost, it's
worth auth too — natural pairing with v1.0 user accounts component.

---

## v0.9 Session D shipped

Session D delivered all 3 remaining city DCRs:

- **Bangalore** — BBMP / Karnataka UDD (RMP-2015 + Nov 2025 amendments).
  5 tiers from very-small (<60 sqm fixed 0.7m setbacks per UDD 2026) to
  very-large (>4000 sqm = 5m all sides per BBMP).
- **Pune** — UDCPR Maharashtra 2020 / PMC. 5 tiers per UDCPR Table 6
  marginal distances. Non-congested area default with disclosure.
- **Hyderabad** — Telangana Building Rules G.O. Ms. 168 / GHMC.
  6 tiers from G.O. 168 Table-III for non-high-rise residential (≤18m).

19 new tests + 1 milestone test (`test_no_city_falls_back_to_nbc_after_session_d`).
482 PASS across 24 suites.

**Milestone reached: all 6 launch cities now have real DCR-backed setback
rules.** No supported city falls back to NBC.

### Conservative-read caveat (carries to all 5 v0.9 cities)

Mumbai/Delhi/Bangalore/Pune/Hyderabad tier values are best-available reads
from secondary sources cross-referenced across multiple reputable building
guides. Each city has `_disclosure_text` advising the user to verify with
the relevant authority (MCGM/DDA/BBMP/PMC/GHMC) before construction. v1.0+
verification work should reconcile against authoritative printed
publications and zonal plans.

### Bangalore very-large tier unreachable in v0.9

The BBMP rule for plots >4000 sqm (5m all sides) lives in the KB but isn't
reachable through the Plot domain (capped at 60m × 60m = 3600 sqm). This
tier becomes accessible when downstream layout components consume the
setback rules directly. Not a bug — appropriate for v0.9 single-family
scope.

---

## v0.9 Session E plan (next)

**Goal:** Package v0.9 release.

1. Bump README.md to v0.9 with a "What's new in v0.9" section covering
   all four sessions:
   - 6 review drawbacks closed (A)
   - Cross-device server save/resume (B)
   - All 6 cities real DCRs (C+D)
2. Update DEPLOY.md for new SQLite endpoint + env vars
3. Final test sweep + verify zip contents from clean extract
4. Build buildemup_v0.9.0_with_c1_v0.9.zip

After Session E ships, Component 1 v0.9 is locked. Next opens Component 2
(Feasibility) per SPEC_v0.2 roadmap.

---

## v0.9.1 patch shipped

After v0.9 release, second drawback review surfaced 14 items. Web research
+ analysis approved 7 for shipping; 7 deferred with reasons.

### Shipped (7 of 14)

| # | Drawback | Status |
|---|---|---|
| 1+2 | Cost framing precision + multiplier | ✅ Replaced ×1.5-2.0 with cited 2.5× (AECORD 2026 industry breakdown 40/25/15/12/8) |
| 3 | Net usable as range | ✅ 85% → 80-90% range with low/high fields in API |
| 5 | Parking width-only check | ✅ Both messages prefixed `[Preliminary check — width-based, layout-dependent]` |
| 6 | DCR rule version-tagging | ✅ `kb_versions` accessor fixed (was reading legacy `kb_version` showing v1 throughout v0.9). Audit trail in assumptions |
| 8 | risk_level oversimplifies | ✅ New `risk_drivers` field explains WHY |
| 9 | Soft-guidance volume | ✅ Grouped by category in explain() + API |
| 10 | Vastu separation note | ✅ "may conflict with optimal structural and layout choices. Engineering wins" |
| 14 | "Confidence" aspirational | ✅ "STEP 1 OF 6" banner in explain(), `roadmap_position` in API |

### Deferred (7 of 14)

| # | Drawback | Why deferred |
|---|---|---|
| 4 | Circulation factor still coarse | Analyst self-cancels: "good enough — keep current logic". Only assumption-disclosure suggestion shipped |
| 7 | SQLite ephemeral storage | Already disclosed in API + UI. Postgres swap is v1.0 work |
| 11 | C7 double-execution overhead | Premature optimization (~50ms not measured as problem). Trigger: when caching has measured value |
| 12 | Insights non-persistent | C7 concern, already in v2_backlog. Out of C1 patch scope |
| 13 | Increasing complexity | Already addressed (arch doc, ComponentContract, 25-suite sweep <30s). Real complexity threshold not reached |

### Real bug caught during patch work

`_collect_kb_versions()` was reading `kb_version` key, but Sessions C/D added
`_version` keys when bumping setback rules to v3. Result: API has been
showing setback_rules at "Setbacks_India_2026_v1" throughout v0.9 even
though v3 was the actual loaded data. Now fixed: accessor prefers
`_version`, falls back to `kb_version` for back-compat.

This wasn't in the drawback list — surfaced while implementing #6.

### Cost ratio correction — user-facing impact

For a typical Chennai G+1 brief (108 sqm built):
- v0.9 said: structural ₹6.7L → all-in ~₹10-13L (×1.5-2.0)
- v0.9.1 says: structural ₹6.7L → all-in ~₹14-20L (typical ₹17L)

The difference is ~40% upward. Honest correction. Some users who saw
v0.9 numbers will be surprised. Documented prominently in README.

### Tests

19 new tests in `test_c01_v091_patch.py` cover all 7 fixes + the kb_version
bug fix. All pass first run.

**Sweep: 503 PASS across 25 suites. 0 fails. Zero Component 7 regression.**

### Bangalore cost multiplier minor discrepancy (v1.0 follow-up)

AECORD 2026 says Bangalore is ~15% above Chennai for construction cost.
C7's CITY_COST_MULTIPLIER has Bangalore at 0.96× Chennai (4% LOWER).
Direction is wrong by ~20 percentage points.

Discovered during the v0.9.1 cost research but **not fixed in v0.9.1**
because:
1. C7 is the cost engine; touching its multipliers requires Component 7
   regression testing, not a Component 1 patch session
2. Need second source confirming AECORD before changing established C7 numbers
3. Locking C7 v0.7.2 FINAL has held steady for 3+ release cycles

Trigger for fix: dedicated C7 v0.7.3 release reviewing all 6 city
multipliers against AECORD + at least one other industry source. Estimate:
1 session.

---

## v0.9.2 patch shipped

Third drawback review (post-v0.9.1) surfaced 16 items. Triage shipped 6
main + 3 partial (UX text only); 7 deferred with reasons.

### Shipped (9 of 16)
- **#3** Plain-language risk tails — `LOW (minor issues, plan looks sound)`
- **#4** BIGGEST ISSUE elevation for MEDIUM/HIGH risk
- **#6** Next-step CTA — "Component 2 (Feasibility) will check..."
- **#13** Scope caveat — "does NOT replace architect-led layout..."
- **#15** Powered-by surface — Component 7 + IS codes named
- **#16** WHAT SHOULD YOU DO NOW? — 3-5 numbered actions branched by risk
- **#1 partial** Industry overshoot stat (citation: Propeller Aero 70-yr study + Nature Sci Reports India research)
- **#7 partial** Parking msg extended — turning radius / columns / gates
- **#8 partial** Net usable poor-layout warning — drops below 80%

### Deferred (7 of 16)
- **#2** city-aware breakdown — already handled (CITY_COST_MULTIPLIER applies before 2.5×). Bangalore discrepancy queued for C7 v0.7.3.
- **#5** less grouping — analyst contradicts #4 (more hierarchy). No-op.
- **#9** quantify Vastu conflict (X%) — refused, no model produces this number, would be fake precision
- **#10** Postgres swap — third time raised, v1.0 infrastructure work
- **#11** insights polluting filter — C7 concern, no measured problem
- **#12** confidence statement vs warnings — contradicts pattern of every other review's "more honest disclaimers" call
- **#14** feasibility gate — this IS Component 2. Building next.

### Test coverage
19 new tests, all pass first run. **523 PASS across 26 suites.**

### Design principle for v0.9.2
Text-only patch. No logic changes. All additive (new fields, new sections,
new helper) or pure string updates. Zero regressions in the full sweep.

### Honest framing of v0.9.x stretch
Three patch sessions (v0.9.1 → v0.9.2) totalling 38 fixes shipped + 21
deferred — driven by three rounds of drawback reviews. The pattern that
worked: web research before empirical claims, refuse fake precision,
push back on contradictory drawbacks, defer when work belongs in
v1.0 / future component. Honest disclaimers > false confidence.

---

## Up next per user direction

1. **C7 v0.7.3 — Bangalore cost multiplier fix.** AECORD 2026 says
   Bangalore is ~15% above Chennai; current multiplier is 0.96× (4%
   below). Direction is wrong by ~20pp. 1-session work.
2. **Component 2 — Feasibility Engine.** The biggest valid drawback in
   v0.9.2 review (#14) is solved by C2 existing, not patching C1.
   Estimated 2-3 sessions.

---

## v0.9.3 shipped — Bangalore + Hyderabad cost multiplier correction

After v0.9.2 review flagged Bangalore C7 multiplier as suspect, this
session researched 8+ Bangalore + 7+ Hyderabad industry sources for
direct per-sqft cost data. **Research disagreed with AECORD's claim.**

### Honest finding

| City | v0.9.2 | v0.9.3 | Direction | Rationale |
|---|---|---|---|---|
| Bangalore | 0.96 | 0.98 | +0.02 | Parity with Chennai (8 sources) |
| Hyderabad | 0.93 | 0.85 | -0.08 | Cheapest of 6 (7 sources) |

The AECORD claim of "+15% Bangalore vs Chennai" was not supported by
direct per-sqft cost data. The "fix" the v0.9.1 reviewer assumed (push
Bangalore from 0.96 to ~1.15) would have introduced a +17% pricing
error. Real data showed near-parity, which is now reflected.

Hyderabad direction surprised both reviewer and developer — research
clearly showed it as the cheapest of 6 cities (multiple sources
described it as "significantly lower" than Bangalore/Mumbai). The
previous 0.93 was overstated; 0.85 reflects market reality.

KB bumped to `MultiCity_2026_Q2_v2`. 9 new tests, all green.

---

## v0.9.4 queued: Mumbai + Delhi multiplier review

During v0.9.3 research, I noticed two more cities likely need
correction but deserved their own focused session because both
move user-facing numbers significantly:

### Mumbai

Current: 1.35×
Research suggests: ~1.45× (Mumbai sources show ₹3000-4000+/sqft
vs Chennai baseline ~₹2400/sqft = 1.4-1.55× ratio)

Direction: UP. The current 1.35 may be slightly understated.
Combined with the contractor margin (20% Mumbai vs 12% Chennai),
the effective ratio in C7 output is already ~1.6× which roughly
matches market reality. **May not need adjustment** — needs a
focused investigation that compares the C7 effective output to
direct market quotes.

### Delhi

Current: 1.15×
Research suggests: ~1.40× (multiple sources show Delhi at
₹2700-3500/sqft vs Chennai ₹2400 = 1.13-1.46× ratio)

Direction: UP. Likely understated. The Homebazaar comparison
puts Delhi at 1.38× Chennai which is meaningfully above the
current 1.15.

### Why deferred

These changes move user-facing numbers more than the v0.9.3 changes
did. A Delhi user seeing a 25% jump in their cost estimate after
this fix needs to be expected and disclosed. Both deserve a focused
v0.9.4 session with:
- Tighter source verification (more than the 8 sources used for v0.9.3)
- Comparison of C7 effective output (multiplier × contractor margin)
  against actual market quotes
- README/DEPLOY notice that v0.9.3 → v0.9.4 will significantly change
  Delhi cost numbers
- Possibly: Mumbai stays put, only Delhi changes

Trigger: queued for the session after Component 2 (Feasibility) ships
OR if user feedback flags Delhi cost as off.
