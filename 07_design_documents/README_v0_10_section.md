# BuildemUp† — Codebase v0.10 (Component 1 v0.9.2 + Component 2 v0.1 + Component 7 v0.7.3)

**†** = placeholder name. Final name: BuildEase (rename pending trademark/domain lock).

## What this is

A decision-support engine for Indian families building their own home.
Not "AI floor plan generator" — that's the artifact. The product is
**confidence in a six-figure decision.**

Three components ship today:

- **Component 1** (Brief Capture) — turn a homeowner's preferences into a
  validated, machine-readable Brief.
- **Component 2** (Feasibility) — turn the Brief into a structured
  buildability report with code-compliance gaps and cost trade-offs.
- **Component 7** (Cost Engine) — turn the Brief into a transparent
  cost estimate with city + spec multipliers.

C1 + C2 chain through a single API call: `POST /api/feasibility/run`.

## v0.10 — Component 2 v0.1 (Feasibility Engine) ships

After 10 dev sessions (A through J), Component 2 ships with the **dual-
design pattern**: every brief now produces TWO parallel feasibility
reports — Practical (what the user wants) vs Code-Strict (full NBC + DCR
compliance) — plus a structured Gap analysis showing exactly where the
two diverge.

### What Component 2 does

Takes a captured Brief plus optional verified-data fields, and produces a
**DesignGapAnalysis** containing both reports, all gaps, cost delta, and
prioritized action steps.

The output answers two questions a homeowner cannot answer alone:
1. *"Can I actually build this?"* (Practical lane)
2. *"What does the law strictly require, and what would full compliance
   cost me?"* (Code-Strict lane + cost delta)

### The dual-design pattern

This is the central architectural decision of v0.1. The user explicitly
approved it after we discussed alternatives (single-report-with-flags,
two-pass-with-different-thresholds, etc.).

For 6 of the 17 checks (setbacks, solar, cross-ventilation, soil, water
table, RWH), we run **two variants**: a `_practical` function and a
`_code_strict` function. When they diverge, a `Gap` is generated with
severity (MARGINAL / SIGNIFICANT / BLOCKING_IF_NOT_ACCEPTED / INFO_ONLY).

Each gap honestly tells the user: "your Practical choice is X, NBC
strictly requires Y. Cost delta to upgrade: ₹Z."

### The 3-state input pattern + downgrade rule

For fields the user might not know (soil type, water table, distance from
electric line, etc.), `FeasibilityInput` wraps each with a `FieldSource`:
`USER_PROVIDED_VERIFIED` / `USER_PROVIDED_UNVERIFIED` / `USER_DOESNT_KNOW`
/ `NOT_ASKED`.

**Critical rule (user-approved):** when an assumed city-default value
would HARD-fail a check, the severity is downgraded to SOFT_WARN. The
system never blocks a homeowner on a guess. But user-provided values —
even unverified — keep their strict outcome (because that's the user's
data, not ours).

### 17 of 18 v0.1 checks shipped

| Category | Count | Examples |
|---|---|---|
| Hard physics (unbranched) | 4 | envelope, floor stack, parking width, budget |
| Legal-only (unbranched) | 6 | FAR, ground coverage, fire access, electric line, water course, stilt mandate |
| Branched (Practical + Code-Strict + Gap) | 6 | setbacks, solar, ventilation, soil, water table, RWH |
| Info-only | 1 | approval complexity (simple/medium/complex tier + timeline) |
| **Deferred to v0.2** | **1** | room minimums (needs C1 RoomRequirement flag) |

### Scoring contract (locked)

Every report uses the same 0-100 scoring:
- Start at 100, deduct -5/-7/-10 for SOFT_WARN by LOW/MEDIUM/HIGH confidence
- Any HARD_FAIL **caps the score at 40 max** (regardless of how many)

The 40 cap is intentional: a single blocker means the design isn't
buildable as-stated. The exact score below 100 reflects warning load.

### New API endpoint

`POST /api/feasibility/run` — accepts the same JSON payload as the
existing `/api/brief/capture` plus optional `feasibility_input` section.
Returns:

```json
{
  "ok": true,
  "trace_id": "...",
  "feasibility_summary_text": "...20-line CLI summary...",
  "feasibility_full_text": "...full ~120-line report...",
  "feasibility_data": { ...full DesignGapAnalysis JSON... },
  "brief_summary": { ... },
  "errors": null
}
```

The existing `/api/brief/capture` endpoint is **not touched** — backward
compatible. The new endpoint chains C1 + C2 in a single round trip.

### Test coverage

| Suite | Tests |
|---|---|
| v0.9.3 baseline (C1 + C7) | 534 |
| C2 Sessions A-F (domain + 17 checks) | 228 |
| C2 Session G (orchestrator) | 33 |
| C2 Session H (renderer + user guide) | 32 |
| C2 Session I (API endpoint + C1+C2 chained) | 32 |
| C2 Session J (20-scenario validation) | 12 |
| **Total** | **871** |

All tests run via `for t in buildemup/tests/test_*.py; do python "$t"; done`.
Zero regressions across 37 suites.

### 20-scenario validation suite

`tests/test_c02_session_j.py` runs 20 realistic builds spanning all 6
launch cities (Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi),
floor counts G+0 through G+3, plot sizes from tiny to 1200+ sqm, and
specific gap-surfacing tests. It auto-generates
`docs/c02_v0.1_validation_report.md` documenting expected vs actual
output for each scenario.

The validation suite caught **6 cases where my expected ranges were wrong**
mid-session — Chennai-centric setback assumptions don't match Hyderabad's
NBC, Code-Strict water_table HARDs more often than I assumed, Delhi's
stilt mandate fires earlier than I expected. **Updated expectations to
match reality** rather than hide the findings.

### Honesty note

**Most realistic briefs land at Code-Strict 40.** This is correct NBC
behavior, not a bug. `water_table_code_strict` HARD-fails on any
unverified water table + habitable ground floor (NBC Part 3 cl. 6.2),
and `soil_type_code_strict` HARD-fails on any G+1+ without verified soil
test (NBC + IS 1892). Most homeowners don't have these tests done at
brief-capture time.

The 40 cap is the system telling the user honestly: *"You can probably
build this, but to be NBC-bulletproof, get the verified data."* Best
case (S13: verified data + S-facing + G+0) scores 90/90 with 0 gaps.

This honest signal is **more useful** than a system that shows a generous
80/100 across the board. The score reflects the verification gap, and
the report tells the user exactly what to verify and what it costs.

### What's NOT in v0.1 (logged in `docs/v2_backlog.md`)

- Room minimums branching (needs C1 RoomRequirement flag)
- Cross-ventilation interior plot types
- Solar orientation precision (currently coarse 8-orientation heuristic)
- Refactor electric line + water course to FeasibilityInput pattern
- RWH cost regional refinement based on real builder data
- API: CORS tightening, rate limiting, auth
- Renderer: PDF generation, HTML output, internationalization
- Acceptance UI (interactive accept/reject loop on each gap)

### How to use it

```bash
# Run the server (stdlib only — no Flask/FastAPI dependency)
python -m buildemup.api.server

# POST a brief to get a feasibility report
curl -X POST http://localhost:8000/api/feasibility/run \
  -H "Content-Type: application/json" \
  -d @examples/sample_brief.json
```

The full user guide lives at `docs/c02_user_guide.md` — written for
homeowners, not developers, explaining how to read the report.

### File structure (Component 2)

```
buildemup/components/c02/
  __init__.py
  scoring.py                  # Scoring contract + score_contribution
  feasibility_input.py        # 3-state input pattern (FieldSource + InputField)
  hard_physics_checks.py      # 4 unbranched physics checks
  legal_only_checks.py        # 6 unbranched legal checks
  branched_checks.py          # setbacks + solar + ventilation (branched)
  site_input_checks.py        # soil + water table (branched + downgrade)
  sustainability_checks.py    # RWH + approval complexity
  orchestrator.py             # run_feasibility() — single public entry point
  renderer.py                 # text + JSON renderers

buildemup/api/
  feasibility_endpoint.py     # POST /api/feasibility/run handler

buildemup/kb_rules/
  city_feasibility_defaults.json    # city-typical soil + water table
  rwh_approval_rules.json           # RWH thresholds + approval tiers

buildemup/docs/
  c02_user_guide.md           # Homeowner-facing user guide
  c02_v0.1_release.md         # Engineering release notes
  c02_v0.1_validation_report.md  # Auto-generated, run-time
```

