# BuildemUp — Architecture Overview (v0.9)

One-page map of how the codebase fits together. Kept deliberately short —
the source of truth is the code, not this doc.

## Layer diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — API (HTTP)                                                │
│  ────────────────────────────────────────────────────────────────    │
│  buildemup/api/                                                      │
│    server.py           stdlib http.server, no framework deps         │
│    brief_endpoint.py   JSON in → BriefCaptureEngine → JSON out       │
└───────────────────┬──────────────────────────────────────────────────┘
                    │ calls
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — COMPONENTS (business logic, orchestrators)                │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│   Component 1 — Brief Capture         Component 7 — Structural Grid  │
│   ───────────────────────────         ──────────────────────────     │
│   c01_brief_capture.py                c07_structural_grid.py         │
│     (BriefCaptureEngine)                (StructuralGridEngine)       │
│                                                                      │
│   c01/                                kb/ (per-domain modules)       │
│   ├ setback_calculator.py             ├ material_rates_*.py          │
│   ├ room_composer.py                  ├ vastu_engine.py              │
│   ├ parking_feasibility.py            ├ soil_types.py                │
│   ├ vastu_filter.py                   └ ...                          │
│   ├ budget_bridge.py ─────────────────┐                              │
│   ├ phased_construction.py             │ calls C7 for cost           │
│   ├ soft_guide_engine.py               │ (single source of truth)    │
│   └ assumptions_log.py                 │                             │
│                                       ◄┘                             │
│                                                                      │
│   Dependency is one-way: C1 → C7. C7 does not import from C1.        │
└───────────────────┬──────────────────────────────────────────────────┘
                    │ consume + produce
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — DOMAIN (frozen dataclasses, validation only)              │
│  ────────────────────────────────────────────────────────────────    │
│  buildemup/domain/                                                   │
│  ── Component 1 types ──              ── Component 7 types ──        │
│    plot.py          (Plot)               building.py                 │
│    setbacks.py      (Setbacks)           envelope.py                 │
│    floor_requirement.py                  floor.py                    │
│    brief.py         (Brief, Budget,      column.py                   │
│                      CostEstimate,       grid.py (DomainGrid)        │
│                      Vastu*, Guidance*)                              │
│                                                                      │
│  Domain types are DUMB: dataclasses with __post_init__ validation.   │
│  No business logic. No KB lookups. No I/O.                           │
│                                                                      │
│  21 types registered in component_contract._DOMAIN_TYPE_NAMES —      │
│  downstream components are forced to consume real domain objects,    │
│  not raw dicts.                                                      │
└───────────────────┬──────────────────────────────────────────────────┘
                    │ backed by
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — KNOWLEDGE & INFRASTRUCTURE                                │
│  ────────────────────────────────────────────────────────────────    │
│  buildemup/kb_rules/ (JSON — single source, v0.6+ pattern)           │
│    setback_rules.json       6 cities, all real DCRs (no NBC fallback):│
│                             Chennai TNCDBR · Mumbai DCPR 2034 ·       │
│                             Delhi MPD-2021 · Bangalore BBMP/UDD ·     │
│                             Pune UDCPR · Hyderabad GHMC G.O. 168      │
│    room_minimums.json       NBC 2016 Part 3 + circulation factor     │
│    seismic_rules.json       IS 1893 (C7 migrated in v0.7)            │
│    load_rules.json          IS 875 (C7 migrated in v0.7)             │
│                                                                      │
│  buildemup/utils/                                                    │
│    component_contract.py    v0.7.1 domain-type enforcement           │
│    kb_rules_loader.py       JSON load + schema validate + cache      │
│    legal_disclosures.py     v0.6 mandatory block                     │
│    logging.py               trace_id generation                      │
│    insights_buffer.py       C7 proactive guidance (v0.7.2)           │
└──────────────────────────────────────────────────────────────────────┘
```

## Data flow — a single brief submit

```
User fills form in browser
    │
    ▼
POST /api/brief/capture {JSON}
    │
    ▼ api/brief_endpoint.handle_brief_capture()
Parse JSON → BriefCaptureInput (primitives)
    │
    ▼ BriefCaptureEngine.execute()
      ├── parse strings → domain objects (Plot, Setbacks, VastuTier)
      ├── compute_compliant_setbacks()  → KB: setback_rules.json
      ├── check_setback_compliance()
      ├── ensure_staircase_present()    → auto-add if ≥2 floors
      ├── check_parking_feasibility()
      ├── generate_vastu_guidance()     → 0/7/15 INFO messages
      ├── budget_bridge.call_component_7_for_cost()
      │     └──► Brief.to_structural_grid_input()  [Drawbacks 2+3]
      │           └──► StructuralGridEngine.execute()
      │                 └──► result.cost ─── back up ◄─┘
      ├── compare_budget_to_estimate()
      ├── suggest_phased_construction_if_needed()
      ├── compute_top_guidance(n=3)     → Drawback 6
      ├── compute_risk_level()          → Drawback 8 (v0.9)
      ├── build_assumptions_list()      → Drawback 10
      └── assemble Brief + BriefCaptureOutput
    │
    ▼
explain() renders 11 sections
    │
    ▼
{"ok": true, "risk_level": "LOW", "c7_preview_cost": ..., "brief_summary": ...}
    │
    ▼
Browser renders result panel
```

## Boundary principles (don't break these)

1. **Component 7 never imports Component 1.** Dependency is strictly
   one-way. Violations surface immediately in Python import graph.

2. **Domain objects don't call KB or components.** If you need to enrich
   a domain object with business logic, do it in a component method —
   not on the dataclass.

3. **KB files are single-source.** If a Python constant exists that
   duplicates a KB value (e.g., `NBC_MINIMUM_ROOM_SIZES_SQM`), a parity
   test must enforce equality.

4. **ComponentContract.consumes/produces are the API.** Adding a field
   requires updating the contract. Removing a field requires a
   deprecation cycle (see `ready_for_downstream` in v0.9 — property
   alias retained for one release).

5. **No framework dependencies for core.** `domain/`, `components/`, and
   `kb_rules/` have zero third-party imports. `api/` uses stdlib only.
   SQLite (planned v0.9 Session B) is stdlib too.

## What to touch where

| If you're changing... | Go to | Don't touch |
|---|---|---|
| Setback rules | `kb_rules/setback_rules.json` | anything else |
| Room size minimums | `kb_rules/room_minimums.json` + parity test | anything else |
| Vastu guidance text | `components/c01/vastu_filter.py` | `VASTU_PARTIAL_ITEMS` in domain |
| Cost calculation | `kb/material_rates_*.py` (C7) | anything in C1 |
| Budget comparison logic | `components/c01/budget_bridge.py` | C7 |
| Form UI | `static/brief_form.{html,js,css}` | Python code |
| API response shape | `api/brief_endpoint.py` + contract + tests | engine |
| New domain type | `domain/<name>.py` + `domain/__init__.py` + `_DOMAIN_TYPE_NAMES` | anywhere else |

## Testing pyramid

- **21 test suites, 416 PASS** as of v0.9 Session A
- Component 7 baseline stays green across every v0.9 change
- Parity tests: Python constants match KB JSON byte-for-byte
- Contract tests: v0.7.1 domain enforcement catches dict-shaped fakes
- End-to-end tests: full HTTP server boots on ephemeral port, accepts
  POST, returns valid JSON

Run all:
```
for t in buildemup/tests/test_*.py; do python "$t"; done
```

## File counts (v0.9)

- Domain types: **21** enforced
- KB JSON modules: **4** (setback + room + seismic + load)
- C1 sub-modules: **8** + 1 orchestrator
- C7 is feature-complete at v0.7.2
- Static files: 3 (HTML/JS/CSS)
- API handlers: 2 (brief + vastu-items)
- Total test count: **416 PASS**
