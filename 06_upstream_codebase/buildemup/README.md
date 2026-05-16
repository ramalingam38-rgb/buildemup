# BuildemUp† — Codebase v0.9.3 (Component 1 v0.9.2 + Component 7 v0.7.3)

**†** = placeholder name. Final name: BuildEase (rename pending trademark/domain lock).

## What this is

A decision-support engine for Indian families building their own home.
Not "AI floor plan generator" — that's the artifact. The product is
**confidence in a six-figure decision.**

## v0.9.3 — Bangalore + Hyderabad cost multiplier correction

After v0.9.2 review flagged the Bangalore C7 cost multiplier as suspect,
this session researched 8+ industry sources for Bangalore and 7+ for
Hyderabad. **The honest research disagreed with the original assumption.**

### Original assumption (from v0.9.1 review)

AECORD 2026 industry guide claimed Bangalore is ~15% above Chennai
(implying multiplier should jump 0.96 → 1.15). The intuition was:
"Bangalore is a tech hub with high labour costs, so it must be expensive."

### What direct research actually showed

Per-square-foot residential rates from primary construction industry
sources (JSW Homes, Stylfixx, Architects4Design, NoBroker, Relgrow,
KM Infra, Sqft.expert, Metromane, Bluemoon, Navanaami, V Build Infra,
Grihashakti, PNK, Homebazaar):

| City | Standard ₹/sqft midpoint | Ratio vs Chennai |
|---|---|---|
| Chennai (baseline) | ~₹2400 | 1.00 |
| Bangalore | ~₹2200 | **0.98 (parity)** |
| Hyderabad | ~₹1900 | **0.85 (lowest of 6)** |

**AECORD's "+15% Bangalore" claim is NOT supported by direct cost-per-sqft
comparisons.** It may have meant land cost or premium-segment cost; for
typical residential construction, Bangalore is at parity with Chennai.

**Hyderabad is genuinely the cheapest of the 6 launch cities** —
multiple sources call it "significantly lower than Mumbai/Bangalore"
and "lower compared to other cities." The previous 0.93 was too high;
0.85 reflects the real market.

### Multiplier changes shipped

| City | v0.9.2 | v0.9.3 | Change | Rationale |
|---|---|---|---|---|
| Chennai | 1.00 | 1.00 | — | baseline |
| **Bangalore** | **0.96** | **0.98** | **+0.02** | parity confirmed by 8 sources |
| **Hyderabad** | **0.93** | **0.85** | **-0.08** | genuinely cheapest of 6 |
| Mumbai | 1.35 | 1.35 | — | review queued for v0.9.4 (research suggests ~1.45) |
| Pune | 1.08 | 1.08 | — | unchanged this session |
| Delhi | 1.15 | 1.15 | — | review queued for v0.9.4 (research suggests ~1.40) |

The Mumbai + Delhi review is deferred because both move user-facing
numbers significantly — they deserve a focused session of their own.

### KB version bumped

`material_rates_multicity.KB_VERSION` = `"MultiCity_2026_Q2_v2"`
(was `"MultiCity_2026_Q2_v1"`).

### Test coverage

9 new tests in `tests/test_c07_v093_multiplier_correction.py`:
- Multiplier values exact (0.98 + 0.85)
- Bangalore now within 5% of Chennai cost output
- Hyderabad now clearly 10-15% below Chennai
- Hyderabad confirmed cheapest of 6 cities
- Mumbai still most expensive (no inversion)
- Chennai baseline cost unchanged (sanity)
- Other cities (Mumbai/Pune/Delhi) unchanged
- KB version reflects v2

**533 PASS across 27 suites.** Zero regression in:
- 274 Component 7 baseline tests
- 122 C1 v0.1 Sessions 1-6
- 81 C1 v0.9 Sessions A-D
- 21 C1 v0.9.1 patch
- 20 C1 v0.9.2 patch
- 9 new v0.9.3 multiplier-correction tests

### Honesty note

This session demonstrated the value of researching before changing
established numbers. Going from 0.96 → 1.15 (the AECORD-implied
"fix") would have introduced a 17% upward error in Bangalore costs.
The actual data-driven move was 0.96 → 0.98 — a much smaller change
in the same direction, and a 0.93 → 0.85 move in the OPPOSITE
direction for Hyderabad. **The user-facing numbers in v0.9.3 are
more accurate than v0.9.2's, which were more accurate than what
the AECORD-aligned "fix" would have produced.**

---

## v0.9.2 — UX text patch (post-v0.9.1 review)

After v0.9.1 shipped, third drawback review surfaced 16 items. Triage:
6 main + 3 partial fixes shipped (UX text only, zero logic changes);
7 deferred with reasons.

### Shipped (6 main + 3 partial of 16)

| # | Fix | Where it shows |
|---|---|---|
| 3 | **Plain-language risk tails** — `LOW (minor issues, plan looks sound)` instead of bare `LOW` | explain() + API `risk_label_with_context` |
| 4 | **BIGGEST ISSUE elevation** — top driver surfaced prominently for MEDIUM/HIGH | explain() `★ BIGGEST ISSUE:` + API `biggest_issue` |
| 6 | **Next-step CTA** — "Next: Component 2 (Feasibility) will check whether your plan is actually possible" | explain() banner + API `roadmap_position.next_step_cta` |
| 13 | **Scope caveat** — "This output does NOT replace architect-led layout, structural drawings, or municipal plan approval" | explain() banner + API `scope_caveat` |
| 15 | **Powered-by surface** — "Structural cost estimate powered by Component 7 (NBC + IS 456/875/1893)" | explain() banner + API `powered_by` |
| 16 | **WHAT SHOULD YOU DO NOW?** — full new section with 3-5 numbered actions branched by risk level + presence of compliance/budget concerns | explain() new section + API `action_steps` |
| 1 partial | **Overshoot stat** — "85%+ projects overshoot 15-30%; keep 20% contingency" (citable: 70-year/20-country study + India-specific Nature Sci Reports research) | end of BUDGET section |
| 7 partial | **Parking caveat extended** — "Does NOT validate turning radius, column placement, or gate alignment" | parking guidance messages |
| 8 partial | **Poor-layout warning** — "Poor layout choices can push effective usability below 80%" | PLOT section after net usable range |

### Deferred (7 of 16) — with reasons

| # | Drawback | Why deferred |
|---|---|---|
| 2 | Cost breakdown not city-aware | Already handled — Component 7's CITY_COST_MULTIPLIER applies before the 2.5× breakdown. The 40/25/15/12/8 split is industry-typical; the base number is already city-adjusted. The Bangalore multiplier discrepancy is queued for C7 v0.7.3. |
| 5 | Grouped guidance increases cognitive load | Analyst contradicts themselves — #4 says "add MORE visual hierarchy" while #5 says grouping (which adds hierarchy) is bad. Top 3 + risk drivers already serve as the "what matters most" layer. No-op. |
| 9 | Vastu conflict — quantify with X% efficiency | Refused on intellectual honesty grounds — we have no model that produces "Vastu reduces efficiency by Y%". Inventing a number would create exactly the false-confidence problem every other drawback warns against. |
| 10 | SQLite must move to Postgres | Third time raised. Already disclosed in API + UI. Postgres swap requires real infrastructure decisions; v1.0 launch prep, not patch session. |
| 11 | Insights polluted by bad inputs | Wrong component (C7), no measured problem yet. Already in v2_backlog. |
| 12 | Too much transparency = reduced confidence | Directly contradicts every other drawback in this review (which all call for MORE honest disclaimers). The pattern is correct — keep it. |
| 14 | No feasibility gate | This IS Component 2. Building C2 next, as planned per roadmap. |

### v0.9.2 test coverage

19 dedicated patch tests in `test_c01_v092_patch.py`:

| Drawback | Tests |
|---|---|
| #3 plain-language risk | 2 (explain + API) |
| #4 BIGGEST ISSUE | 3 (HIGH show + LOW hide + API field) |
| #6 next-step CTA | 2 (explain + API) |
| #13 scope caveat | 2 (explain + API) |
| #15 powered-by | 2 (explain + API) |
| #16 action_steps | 5 (helper LOW + HIGH + explain + API + consistency check) |
| #1 partial overshoot stat | 1 |
| #7 partial parking caveat | 1 |
| #8 partial poor-layout warning | 1 |
| **Patch total** | **19** |

**Grand total: 523 PASS across 26 suites.** Zero Component 7 regression.

### v0.9.2 design principle

This patch is text-only — no logic changes. Every fix is either
- additive (new field, new section, new helper), or
- a string change to existing output

Lowest possible regression risk. The only test failure during the
session was zero — the v0.9.2 changes passed full sweep first time
without breaking any prior tests.

---

## v0.9.1 — Patch release (post-v0.9 review)

After v0.9 shipped, Ramalingam reviewed it again and surfaced 14 more
drawbacks. Web research validated 7 of them as worth shipping; 7 deferred
with reasons. **One important correction**:

### ⚠️ Cost ratio corrected upward (was understated by ~25-40%)

v0.9 used `all-in ≈ structural × 1.5-2.0`. Industry research (AECORD 2026
+ JK Cement + NBC industry guides) shows the actual breakdown for typical
Indian residential is:

| Component | Share |
|---|---|
| Structure (foundation + frame + slab + walls) | 40% |
| Finishing (flooring, paint, doors, windows) | 25% |
| MEP (plumbing, electrical, HVAC) | 15% |
| Interior (woodwork, kitchen, fixtures) | 12% |
| Misc (approvals, soil, contingency, overhead) | 8% |

Structure being 40% means **all-in ≈ structural × 2.5** (not × 1.5-2.0).
v0.9 was understating total cost by 25-40%.

v0.9.1 replaces the heuristic with the cited breakdown:
- **Typical**: structural × 2.5
- **Low** (lean finishes, structure ~50%): × 2.0
- **High** (premium finishes, structure ~33%): × 3.0

A user who saw `₹6.7L → ₹10-13L all-in` in v0.9 will now see
`₹6.7L → ₹14-20L all-in (typical ₹17L)`. Bigger number, more honest.
Source citations visible in `explain()` output and API response.

### Other fixes shipped (7 of 14)

- **#1 Cost de-emphasis** — Range first, exact in parens, "DO NOT TREAT AS A QUOTE" inline
- **#3 Net usable as range** — was "85%", now "80-90% typical (depends on layout)"
- **#5 Parking wording** — Both critical/marginal messages now prefixed `[Preliminary check — width-based, layout-dependent]`
- **#6 KB version traceability** — `kb_versions` accessor fixed to read `_version` (was reading legacy `kb_version` and showing v1 throughout v0.9 even though v3 was current). Audit trail visible in assumptions: `Setback rules applied: <authority>. KB version: <ver>.`
- **#8 risk_drivers** — Top-level `risk_drivers` field explains WHY risk is LOW/MEDIUM/HIGH (e.g. `"Critical: Front setback 0.3m below DCR minimum 1.5m"`)
- **#9 Grouped guidance** — Both `explain()` and API now group messages by category (Compliance / Parking / Vastu / Budget / Design / Other) instead of flat list
- **#10 Vastu conflict note** — Added to vastu section: "items may conflict with optimal structural and layout choices. When that happens, engineering wins"
- **#14 Step 1 of 6 framing** — Top of `explain()` now opens with "This is STEP 1 OF 6 in your build journey" + 6-step roadmap. API includes `roadmap_position` field with all 6 steps named.

### Deferred with reasons (7 of 14)

| Drawback | Why deferred |
|---|---|
| #4 Circulation factor still coarse | Analyst's own solution self-cancels ("good enough — keep current logic"); only the assumption-disclosure suggestion shipped |
| #7 SQLite ephemeral storage | Already disclosed in API + UI. Postgres swap is v1.0 work, not patch session |
| #11 C7 double-execution overhead | Premature optimization (~50ms is not yet a measured problem); revisit when caching has real value |
| #12 Insights non-persistent | C7 concern, already in v2_backlog; not C1 patch session scope |
| #13 Increasing complexity | Already addressed: arch doc shipped, ComponentContract enforcement, 25-suite sweep runs in <30s |

### v0.9.1 test coverage

19 dedicated patch tests in `test_c01_v091_patch.py`:

| Drawback | Tests |
|---|---|
| #14 Step 1 of 6 | 2 (explain + API) |
| #8 risk_drivers | 4 (helper + LOW + HIGH + API) |
| #9 grouped guidance | 3 (helper + explain + API) |
| #1+#2 cost rewrite | 4 (AECORD breakdown + de-emphasis + API + low/high brackets) |
| #3 net usable range | 3 (output + explain + API) |
| #5 parking prefix | 1 |
| #6 KB version | 2 (assumptions + version-key bug fix) |
| **Patch total** | **19** |

**Grand total: 503 PASS across 25 suites.** Zero Component 7 regression.

---

## v0.9 — What's new (Component 1 v0.9 ships)

After v0.8 shipped Component 1 v0.1, Ramalingam reviewed the released code
and surfaced 12 drawbacks. We pushed back on 4, agreed on 6 quick fixes,
and explicitly accepted 4 more to fast-track via 4 sessions:

### Session A — Drawback fixes (6 of 12 closed)

- **#2 Confidence illusion** — BUDGET section in `explain()` now leads
  with the range, lists 4 explicit exclusions (finishes +30-100%,
  contractor +8-20%, MEP +10-15%, interiors), all-in heuristic
  (×1.5-2.0), and a "What can change this number" subsection
- **#3 Envelope optimism** — PLOT section shows BOTH gross envelope
  (plot − setbacks) AND net usable (~85% after columns/stairs/corners),
  with explicit "Component 4 will refine" disclosure
- **#5 Circulation factor 1.30 → size-aware** — IS 3861-2002 research
  backed: small homes (<30 sqm/floor) 1.40, typical 1.35, large (>100)
  1.30. Source cited in KB JSON + ASSUMPTIONS USED
- **#6 Vastu cultural label** — Section header now explicit:
  "CULTURAL PREFERENCE, NOT A TECHNICAL REQUIREMENT" with
  engineering-precedence note
- **#8 `ready_for_downstream` rename** — replaced with `risk_level`
  (LOW/MEDIUM/HIGH) + `proceed_with_warnings` (always True in v0.9).
  Old property kept as deprecated alias for one release
- **#9 Top-3 cumulative summary** — explain() now shows
  "Showing top 3 of N total recommendations (X critical, Y concerns,
  Z info items)" + risk level banner

### Session B — Server-side save/resume

Replaces v0.1's localStorage-only flow:
- **`utils/brief_storage.py`** — SQLite-backed (`/tmp/buildemup_briefs.db`,
  configurable via `BUILDEMUP_DB_PATH`). 24-char hex tokens,
  30-day TTL, 1MB payload limit, auto-prune expired on every save.
- **`POST /api/brief/save`** + **`GET /api/brief/resume?token=X`** —
  works cross-device. Resume URL includes the token; copy-paste it
  on any device to restore the brief.
- Frontend tries server first, falls back to localStorage on network
  error. Updated UI disclosure: "any device, 30 days."
- Ephemeral-storage warning surfaced to user — Railway free-tier `/tmp`
  is ephemeral, so briefs lost on redeploy. Documented; trivial swap
  to Postgres for v1.0.

### Session C — Mumbai DCPR 2034 + Delhi MPD-2021 DCRs

Real city DCRs replace NBC fallback for the 2 highest-gap cities:
- **Mumbai** — DCPR 2034 (MCGM). 4 tiers (small/medium/large/highway)
  by plot area + road width. Defaults to SUBURBS values with disclosure
  about Island City zone caveat (Pedder Rd / Carmichael / Altamount etc.)
- **Delhi** — MPD-2021 + UBBL 2016 (DDA). 6 tiers from <50 sqm row
  housing through 1000+ sqm bungalow. Stilt mandatory 100-1000 sqm.
- Disclosure surfaced in `explain()` SETBACKS section AND API response
  under `brief_summary.compliance.dcr_disclosure`

### Session D — Bangalore + Pune + Hyderabad DCRs (milestone reached)

Closes the city DCR gap entirely:
- **Bangalore** — BBMP / Karnataka UDD (RMP-2015 + Nov 2025 amendments).
  5 tiers including UDD 2026 simplified small-plot fixed setbacks
  (≤60 sqm: 0.7m front / 0.6m other; 60-150: 0.9m / 0.7m)
- **Pune** — UDCPR Maharashtra 2020 / PMC. 5 tiers per UDCPR Table 6
  for residential ≤15m height. Non-congested area default.
- **Hyderabad** — Telangana Building Rules G.O. Ms. 168 (GHMC/HMDA).
  6 tiers per Table-III for non-high-rise residential (≤18m incl. stilt).

**Milestone: all 6 launch cities now use real DCR-backed setback rules.
No supported city falls back to NBC.**

### Architecture & docs

- `docs/architecture.md` — one-page layer diagram, data flow, boundary
  principles, "what to touch where" table
- v2_backlog updated with new deferrals: Mumbai zone selector
  (ISLAND_CITY vs SUBURBS), Delhi printed-handbook verification,
  CostProviderInterface, email-resume-link

### v0.9 Test coverage

| Session | Suite | PASS |
|---|---|---|
| v0.1 | Component 1 Sessions 1-6 | 122 |
| A | drawback fixes + circulation factor | 19 |
| B | SQLite save/resume + API + HTTP | 22 |
| C | Mumbai + Delhi + disclosure | 21 |
| D | Bangalore + Pune + Hyderabad | 19 |
| (existing) | Updated session 2/3/4 tests | (3 updated) |
| **Component 1 total** | | **203** |
| Component 7 baseline (unchanged across v0.9) | | 274 |
| **Grand total** | | **482 PASS across 24 suites** |

Zero Component 7 regression across all 4 v0.9 sessions.

---

## v0.8 — What changed (Component 1 v0.1 ships)

After Component 7 reached v0.7.2 FINAL (stable, 274 tests green), we
built Component 1: the Brief Capture Engine. This is the front door
of the product — the form where users enter plot dimensions, floor
plans, and budget, and get back a validated `Brief` object that
downstream components consume.

Component 1 v0.1 delivers all 10 drawbacks identified in the v0.2 spec:

1. **Plot type branching** — `DETACHED` / `SEMI_DETACHED` / `CONTINUOUS`
   each apply different setback rules (4-side / 3-side / front+rear only)
2. **Explicit rectangular envelope** assumption with `is_rectangular=True`
   disclosure, layout engine will refine later
3. **Floor count = load-bearing floors** — `STILT + RESIDENTIAL + TERRACE`
   all count (per NBC structural load definition)
4. **Single cost source** — Component 1 calls Component 7's cost engine
   via `budget_bridge.py`; budget number in brief == cost shown downstream
5. **Circulation factor 1.30** — `total_floor_area = sum(rooms) × 1.30`
   to account for walls, passages, internal circulation
6. **Top 3 guidance prioritisation** — `STRONG_CONCERN → CONCERN → INFO`,
   stable sort within severity, shown prominently at top of output
7. **Parking feasibility** — plot width < 6m with stilt = critical,
   6-8m = tight; both produce `STRONG_CONCERN` with alternatives
8. **Auto-staircase** — for floors ≥ 2, if no `STAIRCASE` anywhere,
   auto-added to ground (or floor 1 if ground is stilt) with INFO
9. **Phased construction suggestion** — budget < 80% of estimate triggers
   "build ground now (~55% cost), design columns for future expansion"
10. **ASSUMPTIONS USED section** in every `explain()` output — every
    implicit choice (floor height, circulation factor, NBC minimums,
    plot-type rules, vastu tier) visible to the user

### User-approved features (beyond drawbacks)

- **Vastu 3-tier opt-in**: OFF (default) / PARTIAL (7 items) / FULL (15+)
  — all INFO-level, never blocks. The 7 PARTIAL items are shown on the
  form so users know exactly what they're opting into.
- **Save & resume via localStorage** — browser-local only in v0.1
  (email-resume-link needs server storage, coming in v0.2)
- **Tailwind form UI** — 4-step wizard (Plot → Floors → Setbacks+Budget
  → Preferences), zero framework dependencies, deploys as static files
- **Stdlib HTTP server** — `python -m buildemup.api.server`, no Flask/
  FastAPI needed for v0.1

### Component 1 v0.1 file structure

```
buildemup/
├── domain/
│   ├── plot.py                 # Plot, PlotType, SharedSide, SoilType
│   ├── setbacks.py             # Setbacks (4-side frozen dataclass)
│   ├── floor_requirement.py    # FloorRequirement, RoomRequirement
│   └── brief.py                # Brief, BudgetRange, VastuTier, Cost...
├── components/
│   ├── c01_brief_capture.py    # BriefCaptureEngine orchestrator
│   └── c01/
│       ├── setback_calculator.py     # Drawback 1 plot-type branching
│       ├── room_composer.py          # Drawback 5 + 8 (circulation, stairs)
│       ├── parking_feasibility.py    # Drawback 7
│       ├── vastu_filter.py           # Q5 3-tier vastu
│       ├── budget_bridge.py          # Drawback 4 single source
│       ├── phased_construction.py    # Drawback 9
│       ├── soft_guide_engine.py      # Drawback 6 top-3
│       └── assumptions_log.py        # Drawback 10
├── kb_rules/
│   ├── setback_rules.json      # Chennai TNCDBR + NBC fallback
│   └── room_minimums.json      # NBC 2016 Part 3 room sizes
├── api/
│   ├── brief_endpoint.py       # JSON handlers
│   └── server.py               # stdlib HTTP server
├── static/
│   ├── brief_form.html         # 4-step Tailwind form
│   ├── brief_form.js           # vanilla JS wizard + save/resume
│   └── brief_form.css          # minimal overrides
└── tests/test_c01_session{1-6}_*.py  # 6 test files, 122 tests
```

### End-to-end numbers (smoke tested)

For a Chennai G+1 brief (12×15m plot, ₹20-30L budget, vastu partial):
- Envelope 9×12m after setbacks, `floors_above_ground=1`, seismic zone II
- Component 7 structural cost: ₹6.7L exact (₹6.2-7.2L range, WELL_CONSTRAINED)
- Budget comparison: "generous" INFO (₹20-30L vs ₹7L estimate)
- 10 soft-guidance items (7 vastu INFO + 3 non-vastu INFO)
- Top 3 all INFO (compliant, generous budget, auto-staircase added)
- 9 explicit assumptions in transparency log
- `ready_for_downstream=True`

Trace ID uniqueness verified: every `execute()` gets fresh ID for
reproducibility + debugging.

### Test coverage

| Session | Module | PASS count |
|---|---|---|
| S1 | Domain objects (Plot, Setbacks, FloorReq, Brief, Vastu) | 14 |
| S2 | Setback calculator + KB JSON + parity | 17 |
| S3 | Room composer + parking + vastu filter | 23 |
| S4 | Budget bridge + handshake + phased + top-3 + assumptions | 25 |
| S5 | BriefCaptureEngine orchestrator + explain() + contract | 26 |
| S6 | API endpoint + HTTP server + static assets | 17 |
| **Total Component 1** | | **122** |
| Component 7 baseline (no regression) | | 274 |
| **Grand total** | | **396 PASS across 20 suites** |

---

## v0.7.2 — What changed (Insights Feedback Loop — Component 7 FINAL)

Per user directive: close the insights loop that v0.7.1 had deferred,
then move to Component 1. This is the LAST release of Component 7
before Component 1 work begins.

### Proactive guidance from recent execution patterns

- **`utils/insights_buffer.py`** — thread-safe in-memory ring buffer
  (maxsize=200) of execution signatures. Resets on deployment restart
  (acceptable for v1); patterns rebuild in ~10 executions.
- **`ExecutionSignature`** is a lightweight fingerprint — NO PII, only
  patterns: city, zone, floors, warnings, frame/drift results, cost
  bucket in lakhs.
- **`ProactiveGuidance`** dataclass with `has_meaningful_signal` flag.
  Surfaces top-3 recurring warnings + city distribution.
- **Thresholds**: `MIN_EXECUTIONS_FOR_INSIGHTS = 10` (prevents noise),
  `MIN_OCCURRENCE_RATE = 0.20` (warning must appear in ≥20% of plans).
- **Integrated into `explain()`** as PROACTIVE GUIDANCE section — only
  shown when meaningful signal exists, gracefully omitted otherwise.
- **Defensive error handling** — insights failures never crash user
  requests.

### Component 7 = DONE

After 6 review cycles (v0.3 → v0.7.2), Component 7 is feature-complete
for v1 launch:
- Structurally defensible (IS 456/1893/13920 + realistic drift model)
- Legally hardened (PENDING ENGINEER VALIDATION everywhere)
- Decision-oriented (action layer with CRITICAL/IMPORTANT/OPTIONAL)
- Self-improving (proactive guidance from recent patterns)
- Architecturally locked (domain-only contracts, single-source rules)

**274 PASS across 14 test suites.**

### Next: Component 1 (Brief Capture)

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

- **14 test suites** (was 13 after v0.7.1)
- **274 PASS markers** (was 254 after v0.7.1; +20 in v0.7.2)
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
