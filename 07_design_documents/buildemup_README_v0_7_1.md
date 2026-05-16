# BuildemUp† — Codebase v0.7.1

**†** = placeholder name. Final name: BuildEase (rename pending trademark/domain lock).

## What this is

A decision-support engine for Indian families building their own home.
Not "AI floor plan generator" — that's the artifact. The product is
**confidence in a six-figure decision.**

## v0.7.1 — What changed (Triaged Drawback Closure)

The v0.7 review flagged 6 new drawbacks. After careful triage, we
executed 3 real v1 issues and correctly deferred 3 that were either
theoretical or premature optimization for launch stage.

### Executed (real v1 value)

- **Drawback 5 — Drift realism (beam + infill factors).** Lateral
  stiffness now includes `BEAM_CONTRIBUTION_FACTOR = 1.3` (moment-frame
  rigidity) and `INFILL_CONTRIBUTION_FACTOR_WITH_WALLS = 1.5` (URM
  infill). Threaded `has_infill_walls` through the drift check with
  default True (typical Indian residential). Result: G+1 drift
  ~20% → ~10% of code limit (halved = more realistic). Prevents
  systematic false-alarm flagging of typical buildings.

- **Drawback 3 — Domain-only contract enforcement.** `validate_input()`
  now rejects raw dicts or primitives for fields declared as domain
  types (Building, Envelope, Floor, etc.). Container types like
  `tuple[Floor, ...]` handled correctly. Future components cannot
  drift away from the domain layer — architecturally prevented.

- **Drawback 4 — Single-source rules (JSON authoritative).**
  `kb/seismic_detailing.py` and `kb/load_estimation.py` now load ALL
  numeric constants from `kb_rules/*.json` at module-import time.
  Public constant names unchanged for back-compat. Dual-source drift
  is structurally impossible — Python reads from JSON, so they cannot
  diverge. Parity tests kept as safety net against accidental
  reintroduction of parallel literals.

### Deferred to v2 (correctly out of scope for launch)

- **Drawback 1 — Unified StructuralModel object.** Theoretical
  consistency risk only; stiffness and strength come from the same
  cross-section, so frame-sanity SAFE + drift SAFE is physically
  consistent. ~1000 lines of refactor for no real benefit.

- **Drawback 2 — Simulation-based dynamic recommendations.** Would
  mean Component 7 calls itself recursively with varied inputs. 5-10×
  slower per execution for marginal gain over threshold-based approach.
  Premature optimization.

- **Drawback 6 — Insights → feedback loop.** Needs production data
  we don't have yet. Building a solution to a theoretical problem
  before having real users.

## v0.7 — What changed (6 Drawbacks Closure Release)

The v0.6 review gave the most positive verdict yet — "first truly
production-grade release" — while flagging 6 system-level drawbacks.
v0.7 closes all six. Before coding, verified IS 1893 drift limits and
IS 456 serviceability via targeted research.

### Drawback 1 — Global Stability / Drift Check

- **`components/c07/global_stability.py`** — IS 1893:2016 cl. 7.11.1.1
  (seismic drift limit 0.004h) + IS 456 serviceability (wind sway
  H/500). Uses cracked-section factor 0.7·Igross per IS 1893:2016
  cl. 6.4.3. Computes per-storey lateral stiffness
  k = Σ(12·E·Ie/h³), drift = V/K, classifies SAFE/WARNING/FAIL.
- Wired into orchestrator with FAIL warnings at top of all_warnings.
- Smoke-tested: G+1 residential 300mm columns = 20% of limit (SAFE);
  G+3 with 230mm columns = 522% of limit (FAIL, correctly flagged).

### Drawback 2 — Rich Domain (worked example)

- **`Building.total_imposed_load_kn()`** — aggregates live loads
  across floors. Previously computed inline; now domain-owned.
- **`Building.validate_for_structural_analysis()`** — returns issue
  list; empty = valid. Catches severe aspect ratio.
- Full rich-domain migration deferred to v0.8.

### Drawback 3 — Rule Migration (2nd of 5 modules)

- **`kb_rules/load_rules.json`** extracted from `kb/load_estimation.py`.
  Dead loads, live loads, concentrated loads, wall loads, safety
  factors.
- 7 typed accessors + schema validation (safety factors ≥ 1.0).
- 7 parity tests verify JSON == Python exactly.

### Drawback 4 — Legal Compact Mode

- **`format_legal_disclosures_block(mode='full'|'compact')`**.
  Default stays `full` (Q2 back-compat). Compact = 3-point summary
  + pointer to full text (67% shorter).

### Drawback 5 — Action-Layer Recommendations

- **`Recommendation`** dataclass with CRITICAL/IMPORTANT/OPTIONAL
  priorities. Attached to all 4 sensitivity drivers.
  Threshold-based: span 3.8m → 4.6m crossing 4m beam-depth tier
  triggers `[IMPORTANT] Keep longest span under 4.0m`.
- `format_recommendations_only()` compressed view, wired into
  `explain()` as TOP RECOMMENDATIONS section.

### Drawback 6 — Insights Loop

- **`utils/insights.py`** — weekly aggregation over structured logs.
  Text + CSV output. Tracks execution counts, top warnings, cost
  distribution, refusal reasons, per-city counts, frame sanity
  outcomes, confidence distribution.
- Simple counting — no ML (v2 scope).

## v0.6 — What changed (Trust + Legal Hardening Release)

The v0.5 review (4th review document) proposed 6 structural and 6
codebase fixes. After web research and a 3-question architectural
discussion, v0.6 ships the most legally-careful release in the
project. Theme: BuildemUp is decision-support, not engineer
replacement, with PENDING ENGINEER VALIDATION on every output.

### Phase 1 — Real engineering

- **Frame sanity engine** (`components/c07/frame_sanity.py`) — Hardy
  Cross moment distribution + IS 456 cl. 39.6 Bresler interaction with
  the REAL formula (αn interpolated 1.0→2.0 per code, NOT the simplified
  M/Mu+P/Pu the document proposed). Per-column SAFE/WARNING/FAIL
  classification. LEVEL 2 sanity check, NOT LEVEL 3 design.
- **Load combinations** (`components/c07/load_combinations.py`) —
  5 governing combos per Indian practice. Wind+EQ never combined per
  IS practice (verified by web research). Method disclosure explicit.
- **Real IS 1904 soil bearing capacity** (`kb/soil_classification.py`) —
  12 soil classes with REAL IS 1904 ranges. Hard rock 450-3300 kN/m²
  (conservative floor + real ceiling). Black cotton flagged expansive.
  Reclaimed fill requires pile. Every output: "Actual SBC must be
  confirmed via soil test" disclaimer.
- **Extended sensitivity** from 2 drivers (soil + load) to 4 drivers
  (+ longest span, + material grade upgrade).

### Phase 2 — Architecture

- **Config-driven rules pilot** (`kb_rules/seismic_rules.json` +
  `utils/kb_rules_loader.py`) — schema validation, caching, 8 typed
  accessor functions. Replaces ONLY the read layer, not the logic.
  Parity test verifies JSON values exactly equal Python constants;
  caught a real bug on first run (Zone III steel% 1.2 in JSON vs 1.5
  in Python).
- **Domain layer** (`/domain/` package) — Building, BuildingMeta,
  Envelope, Floor, FloorType, Column, ColumnLocation, DomainGrid.
  Lightweight dumb dataclasses with validation. Components import
  these instead of redefining their own shapes.
- **ComponentContract enforcement** — auto-discovery test scans all
  c{NN}_*.py files and asserts each has a registered contract. Fails
  build with helpful error message if missing. The "CI rule" that
  prevents assumption drift across all 17 future components.

### Phase 3 — Trust + legal hardening

- **Engineer override rename** — `engineer_validated_override` →
  `user_claims_engineer_reviewed`. Old name still works as back-compat
  alias. Reframed as user-claim only — BuildemUp does NOT verify or
  endorse engineers. Audit-fields error: "We record name/license/date
  for the user's audit trail. The engineer is your own consultant."
- **Validation status** on every output: `PENDING ENGINEER VALIDATION`.
  With user-claim variant: `PENDING ENGINEER VALIDATION (user claims
  engineer reviewed — UNVERIFIED)`. BuildemUp can NEVER transition out
  of "pending" — only the engineer's stamp can.
- **Warning rewrite** — "⚠ ENGINEER OVERRIDE ACTIVE" → "⚠ UNVERIFIED
  USER CLAIM" with explicit "BuildemUp has NOT verified this claim —
  we do not endorse, contact, or verify any engineer".
- **Engineering depth axis** (`utils/engineering_depth.py`) — orthogonal
  to confidence. LEVEL_1_RULE_BASED / LEVEL_2_FRAME_CHECKED /
  LEVEL_3_ENGINEER_DESIGNED. v0.6 ships LEVEL 2. LEVEL 3 is
  engineer-only by design (no `level_3_indicator()` function exists).
- **Freshness enforcement** (`utils/kb_versions.py`) — 3-tier:
  <cadence=OK, cadence-to-2×=WARN_DEGRADE_CONFIDENCE (drops confidence
  one level), >2×=BLOCK_STALE.
- **Legal & statutory disclosures** (`utils/legal_disclosures.py`) —
  6-section block in every `explain()` output (per Q2 inline-everywhere
  decision): structural engineer required, Indian municipal permit
  requirement (CMDA/BMC/MCD/BBMP, "stamped plan" emphasized), no
  engineer endorsement, limitation of liability, PII handling
  session-only, preliminary soil+load assumptions caveat.
- **PII handling** — `purge_engineer_data(dict)` redacts engineer
  name/license/date/consultant before any logging or export. Returns
  new dict; original unchanged. Engineer fields are session-only.

## Test coverage

- **13 test suites** (was 12 after v0.7)
- **254 PASS markers** (was 235 after v0.7; +19 in v0.7.1)
- All multi-city differentials verified
- Stress tests: 30 random configurations, no crashes
- 17 trust-control tests + 14 building-type tests + **24 v0.5 refinement tests**

## Cities supported in launch v1

Chennai • Bangalore • Hyderabad • Mumbai • Pune • Delhi

## Building types supported

| Type | Status |
|---|---|
| Residential single-family | ✅ FULLY IMPLEMENTED |
| Residential multi-family | 🔧 STUBBED (graceful refusal) |
| Commercial office | 🔧 STUBBED |
| Retail | 🔧 STUBBED |
| Mixed-use | 🔧 STUBBED |
| Educational (importance 1.5×) | 🔧 STUBBED |
| Healthcare (importance 1.5×) | 🔧 STUBBED |
| Hospitality | 🔧 STUBBED |
| Industrial / warehouse | ❌ EXCLUDED FROM SCOPE |

## Project structure (v0.5)

```
buildemup/
├── components/
│   ├── c07_structural_grid.py        Component 7 orchestrator (with contract)
│   └── c07/                          Sub-modules
├── kb/                               KNOWLEDGE BASE (10 modules)
│   ├── building_types.py             Type registry (8 types)
│   ├── rcc_design_rules.py           IS 456 + Devdas Menon
│   ├── soil_foundation_rules.py      Soil + water table per city
│   ├── load_estimation.py            IS 875 loads + safety factors
│   ├── seismic_detailing.py          IS 13920 + 3-level regularity
│   ├── wind_load.py                  IS 875 Part 3 + load combination
│   ├── pile_foundation.py            IS 2911 pile sizing + cost
│   ├── material_rates_chennai.py     Chennai 2026 + brand/grade
│   ├── material_rates_multicity.py   5 other cities
│   └── vastu_engine.py               Opt-in Vastu (5 rules)
├── utils/                            UTILITIES (11 modules)
│   ├── transparency.py               Transparency Triple
│   ├── confidence.py                 v0.5: descriptive names
│   ├── errors.py                     Error taxonomy + format_for_user
│   ├── logging.py                    JSON logging + trace summarisation
│   ├── component_base.py             ComponentOutput base class
│   ├── component_contract.py         ⬅️ NEW v0.5: schema enforcement
│   ├── rate_provider.py              Abstract + brand/grade fields
│   ├── sensitivity.py                Cost sensitivity
│   ├── structural_sensitivity.py     Soil + load sensitivity
│   └── kb_versions.py                v0.5: + freshness report
├── contracts/                        Downstream consumer stubs
├── book_to_code/                     Knowledge pipeline pattern
├── tests/                            7 test suites, 98+ tests
│   ├── test_transparency.py
│   ├── test_grid_generator.py
│   ├── test_c07_structural_grid.py
│   ├── test_multicity_and_stress.py
│   ├── test_v04_trust_controls.py
│   ├── test_v04_block_b_building_types.py
│   └── test_v05_refinements.py       ⬅️ NEW v0.5
├── examples/
└── docs/
    ├── v2_backlog.md                 Planning view (what + when)
    └── v2_vision.md                  Competitive narrative (why it matters)
```

## Real engine output (NE 30×40 Chennai, v0.5 banner)

```
╔════════════════════════════════════════════════════════════════════╗
║                  ⚠  RULE-BASED HEURISTIC ESTIMATE  ⚠               ║
║                    This is NOT structural design.                  ║
║              It is a preliminary cost & sizing estimate            ║
║                produced by applying Indian-code rules              ║
║                  (IS 456, IS 875, IS 13920) to your inputs.        ║
║                                                                    ║
║              A LICENSED STRUCTURAL ENGINEER must produce           ║
║            final drawings before any construction begins.          ║
║              Their analysis (frame analysis, P-M diagrams,         ║
║                moment capacity) supersedes our estimate.           ║
╚════════════════════════════════════════════════════════════════════╝

Building type: Residential — single family home

Cost: ₹11.8L–₹13.9L (most likely ₹12.8L) [Confidence: Well-constrained]

Confidence shown above means:
  Well-constrained:        Computed from Indian codes (IS 456, IS 875).
  Regional typical:        Modelled from typical regional values.
  Depends on your choices: Depends on contractor / supplier / finish choice.
NOTE: Confidence is about INPUT certainty + model stability —
NOT about engineering correctness. Even 'Well-constrained' values
need engineer validation at detailed design.

[... structural details, sensitivity, warnings, WHAT WE CHECK section ...]
```

## Engineer override example

For severely irregular plans (aspect ratio > 6:1 or re-entrant corner > 30%):

```python
inp = StructuralGridInput(
    envelope_width_m=10.0, envelope_depth_m=10.0,
    floors_above_ground=1, city="mumbai", seismic_zone="III",
    re_entrant_corner_x_m=4.0, re_entrant_corner_y_m=4.0,  # 40% — severe
    engineer_validated_override=True,
    engineer_name="Dr. Ramesh Krishnan",
    engineer_license_no="TN/SE/2018/4521",
    engineer_validation_date="2026-04-15",
)
result = engine.execute(inp)
# Proceeds with prominent attribution banner showing engineer validated this
```

Without override: refusal with helpful message about how to obtain
engineer validation and re-submit.

## Component contract example

```python
from buildemup.utils.component_contract import (
    get_contract, validate_input, validate_output, format_all_contracts
)

# See all registered contracts
print(format_all_contracts())

# Validate before/after a component call
violations = validate_input("C07_structural_grid", my_input)
violations = validate_output("C07_structural_grid", result)
```

## Running the tests

```bash
python buildemup/tests/test_transparency.py
python buildemup/tests/test_grid_generator.py
python buildemup/tests/test_c07_structural_grid.py
python buildemup/tests/test_multicity_and_stress.py
python buildemup/tests/test_v04_trust_controls.py
python buildemup/tests/test_v04_block_b_building_types.py
python buildemup/tests/test_v05_refinements.py
python buildemup/examples/run_c07_on_ne_30x40.py
```

## Next components

1. ✅ Component 7 — Structural Grid (engineering-grade complete)
2. ⏳ Component 1 — Conversational Brief (Claude API integration)

The `ComponentContract` system from v0.5 means Component 1 will register
its contract on day one. No more silent assumption drift.

## Contract

**Ramalingam:** catch engine-centric drift, trust UX instincts, push back
on scope creep, confirm before architectural changes.

**Claude:** read existing KB before writing, apply 7 principles, document
failure modes, boring correct over clever fast, no black-box errors,
NEVER code before user confirmation on scope changes.
