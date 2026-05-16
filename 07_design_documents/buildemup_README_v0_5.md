# BuildemUp† — Codebase v0.5

**†** = placeholder name. Final name: BuildEase (rename pending trademark/domain lock).

## What this is

A decision-support engine for Indian families building their own home.
Not "AI floor plan generator" — that's the artifact. The product is
**confidence in a six-figure decision.**

## v0.5 — What changed

The v0.4 review was the most positive yet ("strategically correct,
not just an upgrade"), but identified seven specific drawbacks. v0.5
closed them.

### Trust + perception fixes

- **Confidence rename** — `HIGH/MEDIUM/LOW` → `WELL_CONSTRAINED /
  REGIONAL_TYPICAL / DEPENDS_ON_CHOICE`. The v0.4 review's most
  subtle critique: "HIGH" carries semantic weight that overrides any
  inline definition. The new descriptive names + explicit disclaimer
  ("confidence is about INPUT certainty, NOT engineering correctness")
  fix this. Old names retained as aliases for back-compat.
- **Banner language strengthened** — "RULE-BASED HEURISTIC ESTIMATE",
  "NOT structural design", "LICENSED STRUCTURAL ENGINEER must produce
  final drawings". The v0.4 banner said "Preliminary Design Estimate"
  which could still imply design authority.
- **Load combination simplification disclosed** in WHAT WE DON'T CHECK
  (we check governing wind vs governing seismic, not full IS 875 Part 5
  matrix).
- **Sensitivity scope limitation disclosed** (soil + load only, not
  span variation or material strength).

### Architecture / scalability

- **`ComponentContract` system** — the v0.4 reviewer's #1 codebase
  priority. Explicit input/output schemas per component, validated at
  handoff. Component 7 contract registered. Prevents assumption drift
  across the 17 future components. Lightweight (no Pydantic).
- **Engineer-validated override flag** — preserves severe-irregularity
  refusal but adds escape hatch for engineer-validated plans. Requires
  audit fields (engineer_name, engineer_license_no, validation_date).
  Override is logged + warning surfaced prominently in output.
- **Vastu separation disclosure** — Vastu's `format_for_user()` always
  prepends prominent banner: "VASTU ADVISORY (separate from structural
  design) — Do NOT modify the structural layout based on Vastu without
  consulting your structural engineer."
- **`get_data_freshness_report()`** — surfaces how stale each KB module
  is. Quarterly cadence for rates, yearly for codes. No silent shipping
  of stale data.

### What v0.4 critiques we deferred to v2 (correctly)

The v0.4 review's remaining three drawbacks are NOT bugs — they are
correct v1 boundaries that v2 will close:

- **Frame analysis** (no true structural analysis) — disclosed in WHAT
  WE DON'T CHECK; v2 vision Section 1
- **Pile foundation depth** (still conceptual) — adding fake numbers
  would be worse than disclosure; v2 vision Section 3
- **Probabilistic confidence** (still rule-based) — sensitivity gives
  80% of value; v2 vision Section 7

## Test coverage

- **7 test suites** (was 6 in v0.4)
- **98 PASS markers** (was 74 in v0.4)
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
