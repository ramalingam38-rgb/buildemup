# Component 1 — Brief Capture Engine (v0.1 Specification)

**Status:** Draft for user lock-in. No code until this doc is approved.
**Target version:** Component 1 v0.1
**Component contract version:** 0.7.1 (already enforced by infrastructure)
**Author:** This spec is the result of a single locked-scope conversation with Ramalingam.

---

## 1. Purpose & success criteria

### What Component 1 does

Component 1 captures the user's homebuilding brief — plot details, floor count, per-floor room composition, additional requirements, budget — and converts it into a validated `Brief` domain object that downstream components (especially Component 7 structural grid) consume via the `ComponentContract` system.

### What Component 1 does NOT do

This is critical, because Component 7 took 4 months partly because we kept reopening scope. Component 1 v0.1 explicitly does **not**:

- Generate layouts (that's Component 4)
- Run feasibility analysis (that's Component 2)
- Produce trade-off recommendations (that's a later component)
- Render 3D views (Phase B / v2)
- Handle interior selections, tiles, furniture (Phase C / v3)
- Produce CAD sheets or municipal documents (Phase D / v4)
- Use conversational LLM extraction (deferred per Q1 = form-based)

If during build I'm tempted to add any of the above to "make Component 1 more complete," that's scope creep. Refuse and add to v0.2+ backlog.

### Success criteria for v0.1

1. User can submit a complete brief via a structured form
2. System shows both user-stated setbacks AND NBC/DCR-compliant setbacks side-by-side
3. Output is a `Brief` domain object that passes `ComponentContract` validation when fed to Component 7
4. Soft-guide validation flags weird inputs without rejecting them
5. End-to-end test: Brief → Component 7 produces a valid structural output
6. Test coverage: ~30-40 tests across input validation, NBC setback rules, brief assembly, downstream handoff

### Emotional outcome (per user vision)

After completing the brief, the user should feel: "I told the system what I want. It heard me. It understood my plot constraints and what's legal in my city. Now I'm ready for the system to show me what's possible."

---

## 2. Domain shape

### 2.1 New domain objects

Three new dataclasses in the `domain/` layer. All immutable (`frozen=True`), validate in `__post_init__`.

#### `Plot` — plot details
```
Plot
├── width_m: float          (street-facing dimension)
├── depth_m: float          (perpendicular to street)
├── facing: PlotFacing      (NORTH / EAST / SOUTH / WEST / NE / NW / SE / SW)
├── city: str               (lowercased, must be in supported_cities)
├── road_width_m: float     (abutting road width — drives setback rules)
├── corner_plot: bool       (default False; if True, two roads abut)
├── second_road_width_m: float | None  (only if corner_plot)
└── soil_type_known: SoilType | None   (optional; if known, drives Component 7)
```

**Why these fields?** They map directly to what the user's plot plan / sale deed contains, AND they're what NBC/DCR rules need to compute compliant setbacks. Nothing extra.

**Constraints (validated in `__post_init__`):**
- `width_m`: 3.0–60.0 (3m is sub-plot edge case for narrow lanes; 60m is mansion territory — beyond, refer to architect)
- `depth_m`: 3.0–60.0
- `road_width_m`: 1.5–30.0 (1.5m is service-lane edge case; 30m is arterial road)
- City must be in our 6 supported launch cities (Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi) — same as Component 7
- If `corner_plot=True`, `second_road_width_m` is required

#### `FloorRequirement` — what user wants on each floor
```
FloorRequirement
├── floor_number: int       (0=ground, 1=first, 2=second, etc.)
├── floor_use: FloorUse     (RESIDENTIAL / STILT_PARKING / TERRACE_ACCESSIBLE / TERRACE_INACCESSIBLE)
├── rooms: tuple[RoomRequirement, ...]
└── notes: str              (free-text user notes for this floor)
```

#### `RoomRequirement` — room within a floor
```
RoomRequirement
├── room_type: RoomType     (BEDROOM_MASTER / BEDROOM_REGULAR / BATHROOM_ATTACHED /
│                            BATHROOM_COMMON / KITCHEN / LIVING / DINING / POOJA /
│                            BALCONY / UTILITY / STORE / STAIRCASE)
├── count: int              (e.g., 2 bedrooms)
├── min_size_sqm: float | None  (None = use NBC minimum)
└── preferred_size_sqm: float | None  (user's preferred size, if any)
```

**Why this granularity?** It captures user intent (3 bedrooms, 1 master + 2 regular) without forcing them to specify dimensions they don't know. The system has NBC minimums (e.g., bedroom ≥ 9.5 sqm per NBC 2016 Part 3) that get applied if `min_size_sqm` is None.

#### `Brief` — top-level capture
```
Brief
├── plot: Plot
├── user_stated_setbacks: Setbacks       (what user wants/expects)
├── nbc_compliant_setbacks: Setbacks     (computed by us per city DCR)
├── floors: tuple[FloorRequirement, ...] (in order: ground, first, second, ...)
├── budget_range: BudgetRange            (min_lakhs, max_lakhs, currency='INR')
├── additional_requirements: tuple[str, ...]  (free-text user notes)
├── soft_guidance: tuple[GuidanceMessage, ...]  (computed warnings, non-blocking)
├── trace_id: str                        (for log correlation)
└── kb_versions: dict[str, str]          (NBC + DCR versions used)
```

#### Supporting types

- `Setbacks(front_m, rear_m, side_left_m, side_right_m)` — frozen dataclass
- `BudgetRange(min_lakhs: int, max_lakhs: int, currency: str = "INR")`
- `GuidanceMessage(severity: 'INFO' | 'CONCERN' | 'STRONG_CONCERN', text: str, context: str)` — soft-guide output
- Enums: `PlotFacing`, `FloorUse`, `RoomType`

### 2.2 Reuse from existing domain layer

Existing types we keep using as-is:
- `BuildingMeta`
- `Envelope` — derived from Plot.width × Plot.depth minus setbacks
- `FloorType` (existing in `kb/load_estimation.py`) — we map our `FloorUse` to it for Component 7 handoff

### 2.3 Domain-only contracts (already enforced from v0.7.1)

The Component 1 contract will declare:
- `consumes`: primitives (the form fields), NOT domain objects (because input is from user form)
- `produces`: `Brief` (a domain object)

Since `Brief` is in `_DOMAIN_TYPE_NAMES` (we'll add it), downstream components consuming `Brief` will be enforced to use the actual domain object, not raw dicts.

---

## 3. NBC + DCR setback rules

### 3.1 The rule discovery problem

NBC 2016 gives general setback principles. **Actual binding setback rules come from city Development Control Rules (DCRs)**, which differ significantly:

| City | Governing rule | Our reference for v0.1 |
|---|---|---|
| Chennai | TNCDBR 2019 (CMDA) | Public PDF + chennairealties.in |
| Bangalore | BBMP RMP 2015 (amended 2026) | Karnataka urban dev notification |
| Hyderabad | GHMC Building Rules 2012 | GHMC notification |
| Mumbai | DCPR 2034 | MCGM PDF |
| Pune | UDCPR 2020 | Maharashtra urban dev portal |
| Delhi | DDA UBBL 2016 | DDA portal |

**For v0.1**, we'll implement Chennai (TNCDBR 2019) in full as the reference implementation, plus a generic "NBC fallback" rule for the other 5 cities. The other 5 cities will get a v0.2 update with proper DCR rules.

This is honest and disclosed: the user sees "City: Mumbai — using NBC general guidelines (Mumbai DCPR coming in v0.2)" rather than us pretending to know Mumbai-specific rules we don't.

### 3.2 Setback computation logic

```
def compute_compliant_setbacks(plot: Plot) -> tuple[Setbacks, str]:
    """Returns (compliant_setbacks, source_disclosure)."""
    if plot.city == "chennai":
        return _chennai_tncdbr_setbacks(plot), "TNCDBR 2019"
    else:
        return _nbc_fallback_setbacks(plot), "NBC 2016 general (city DCR pending)"
```

#### Chennai (TNCDBR 2019) rules — non-high-rise, ≤16 dwellings, ≤300 sqm

Based on `road_width_m` and `building_height_m` (we estimate height = floors × 3m for setback purposes):

| Plot type | Front | Rear | Side (per side) |
|---|---|---|---|
| Plot ≤ 50 sqm AND road < 7m | 0 (Continuous Building Area applies if declared) | 1.0m | 1.0m |
| Plot 50–150 sqm | 0.9m | 0.7m | 0.7m (one side) |
| Plot 150–300 sqm, height ≤9m | 1.5m | 1.5m | 1.5m |
| Plot 150–300 sqm, height 9–18.3m | 1.5m | 1.5m | 1.5m + 0.5m per extra storey |
| Plot >300 sqm, height ≤9m | 1.5m | 1.5m | 1.5m on each side |
| Plot >300 sqm, height >9m | scales with road width (3m if road ≥9m) | 1.5–3.0m | 1.5–3.0m |

Front setback can be increased by road-widening reservation (we don't know this yet — disclose as "subject to road-widening line check at municipal office").

#### NBC fallback (for non-Chennai v0.1)

Conservative defaults based on NBC 2016 + InfraLens compilation:
- Front: max(3.0m, road_width / 4) — typical residential
- Rear: 2.0m
- Side: 1.5m each side (detached)

These are CONSERVATIVE on purpose — actual DCRs may allow less, never more. So compliant_setbacks is an upper bound until v0.2.

### 3.3 Soft-guide messages from setback comparison

When user-stated setbacks < NBC-compliant:
- Severity `STRONG_CONCERN`
- Message: "Your front setback of {user}m is less than the {compliant}m required by {source}. Building this way may not get municipal approval. Consider increasing front setback to {compliant}m, or reducing built-up area."

When user-stated setbacks > NBC-compliant by > 50%:
- Severity `INFO`
- Message: "Your stated setback of {user}m is more than the {compliant}m minimum. You're losing {diff_sqm} sqm of buildable area. This is your choice — many users prefer extra setback for green space or future expansion."

When user-stated setbacks are within 10% of compliant:
- Severity `INFO`
- Message: "Setbacks are within municipal compliance. Final approval requires sanction from {city} corporation."

### 3.4 KB structure for setbacks

A new file `kb_rules/setback_rules.json` following the same single-source pattern as v0.7.1:

```json
{
  "_meta": {
    "kb_version": "Setbacks_India_2026_v1",
    "source_standards": [
      "Tamil Nadu Combined Development and Building Rules 2019 (Chennai)",
      "Bangalore RMP 2015 (amended 2026)",
      "NBC 2016 Part 3 (general fallback)"
    ],
    "last_updated": "2026-04-23"
  },
  "chennai": {
    "_authority": "TNCDBR 2019 (CMDA)",
    "non_high_rise_under_300sqm": {
      "tier_under_50sqm": { ... },
      "tier_50_to_150sqm": { ... },
      ...
    }
  },
  "bangalore": { ... },
  "_fallback_nbc": { ... }
}
```

Loaded by a new `kb_rules_loader.py` accessor: `get_setback_rules(city) -> dict`.

---

## 4. Per-floor room composition

### 4.1 Room types we support in v0.1

Limited and clear set — matches what an Indian residential brief actually contains:

**Sleeping/private:**
- BEDROOM_MASTER (1 expected, with attached bath)
- BEDROOM_REGULAR (0–4 expected)
- BATHROOM_ATTACHED (paired with bedrooms)
- BATHROOM_COMMON (1–2 expected)

**Living areas:**
- LIVING (1 typical, sometimes combined with dining)
- DINING (often separate in larger homes)
- KITCHEN (1 typical)

**Functional:**
- POOJA (cultural — common in Indian homes)
- BALCONY (0–4)
- UTILITY (washing/drying area)
- STORE (storage)
- STAIRCASE (computed automatically, not user-specified — but user can override)

**Floor-level:**
- STILT_PARKING (whole-floor designation, no individual rooms)
- TERRACE_ACCESSIBLE (accessible terrace, may have water tank, garden)

### 4.2 NBC minimum sizes (loaded from JSON)

Per NBC 2016 Part 3 (validated against InfraLens compilation):

| Room type | NBC minimum | Typical recommended |
|---|---|---|
| BEDROOM_MASTER | 9.5 sqm | 12.0 sqm |
| BEDROOM_REGULAR | 7.5 sqm | 10.0 sqm |
| BATHROOM_ATTACHED | 1.8 sqm | 3.0 sqm |
| BATHROOM_COMMON | 2.8 sqm (combined WC+bath) | 3.5 sqm |
| KITCHEN | 5.0 sqm | 7.0 sqm |
| LIVING | 9.5 sqm | 14.0 sqm |
| DINING | 6.0 sqm | 9.0 sqm |
| POOJA | 1.5 sqm | 2.0 sqm |
| BALCONY | 1.5 sqm | 3.0 sqm |
| UTILITY | 2.0 sqm | 4.0 sqm |
| STORE | 1.5 sqm | 3.0 sqm |
| STAIRCASE | 5.5 sqm (incl. landing) | 7.0 sqm |

Loaded from `kb_rules/room_minimums.json`.

### 4.3 What the form offers

For each floor, user picks:

```
Floor 0 (Ground Floor) — Use: [STILT_PARKING / RESIDENTIAL]
  If RESIDENTIAL:
    Room composition (pick what you want, system adds counts):
      [+] Bedroom (Master)        [count: 0/1]
      [+] Bedroom (Regular)       [count: 0-4]
      [+] Bathroom (Attached)     [count: auto from master+bedrooms]
      [+] Bathroom (Common)       [count: 0-2]
      [+] Kitchen                 [count: 0-1]
      [+] Living                  [count: 0-1]
      [+] Dining                  [count: 0-1]
      [+] Pooja                   [count: 0-1]
      [+] Balcony                 [count: 0-4]
      [+] Utility                 [count: 0-1]
      [+] Store                   [count: 0-1]
    Floor notes: [free text]

Floor 1 (First Floor) — Use: [RESIDENTIAL]
  ... same options ...

Floor 2 (Second Floor) — Use: [RESIDENTIAL / TERRACE_ACCESSIBLE]
  ...
```

**Defaults that auto-fill** (so the user doesn't see a blank form):
- Ground floor: 1 Living, 1 Kitchen, 1 Common Bathroom (typical Indian)
- First floor: 1 Master Bedroom + 1 Attached Bath, 1 Bedroom + 1 Common Bath
- Top floor: 1 Terrace Accessible (with water tank space)

Defaults are the "typical 2BHK G+1" template. User edits as desired.

---

## 5. Budget range

### 5.1 Format

```
BudgetRange(min_lakhs=20, max_lakhs=30, currency="INR")
```

User enters two numbers (in lakhs) representing their construction-cost budget range. Currency hardcoded to INR for v0.1.

### 5.2 Soft-guide validation

After Brief is fully assembled, we estimate built-up area (sum of floor areas after setbacks) and apply a rough rate:

- Chennai/Bangalore basic: ₹1,800–2,200 per sqft
- Mumbai/Pune basic: ₹2,200–2,800 per sqft
- Delhi basic: ₹1,800–2,400 per sqft
- Hyderabad basic: ₹1,700–2,100 per sqft

(These are construction-only rates — not including land, interiors, furniture. Per Component 7 cost estimator's existing rate provider.)

**Soft-guide cases:**

If user budget < 80% of minimum estimated cost:
- `STRONG_CONCERN`: "Your budget of ₹{budget}L is below the ₹{est_min}L minimum estimated for {built_area} sqft of construction in {city}. Consider: (a) reducing built area, (b) using basic finishes, (c) increasing budget, or (d) phased construction starting with ground floor."

If user budget within ±20% of estimated range:
- `INFO`: "Your budget aligns with typical {city} basic-finish construction. Final cost depends on finishes and engineer's design."

If user budget > 150% of estimated:
- `INFO`: "Your budget is generous for the floor area. You have room for premium finishes, better windows, or hidden costs. Some users prefer to keep margin for interior work later."

---

## 6. Soft-guide validation — full philosophy

Per Q3 = "soft guide" decision. Component 1 NEVER refuses input. It produces:

- A valid `Brief` (always)
- A list of `GuidanceMessage` with three severity levels:
  - `INFO` — informational, neutral or positive
  - `CONCERN` — something to think about, not blocking
  - `STRONG_CONCERN` — likely a problem; user should reconsider but can override

Examples of `STRONG_CONCERN` (must show prominently):
- Setbacks below DCR minimum
- Budget below 80% of minimum estimated cost
- Plot too narrow for required car parking
- Floor count exceeds reasonable for plot size (e.g., G+3 on 600 sqft plot)
- Bathroom-to-bedroom ratio < 0.5 (weird ratio)

Examples of `CONCERN`:
- No master bedroom specified (most users want one)
- No kitchen on any floor (was this intentional?)
- Stilt parking but plot < 30 ft wide (parking will be tight)

Examples of `INFO`:
- Setbacks within compliance
- Typical room ratios
- Helpful suggestions

**Phrasing rules:**
- Always second-person ("Your front setback of...")
- Always include the source/reason ("...required by TNCDBR 2019")
- Always offer an action ("Consider increasing to {x}m, or reducing built area")
- Never use "must" / "cannot" — use "may not get approval" / "consider"
- Always include the trace_id at the end of the brief output for support

---

## 7. Output shape & downstream handoff

### 7.1 Brief → Component 7 conversion

A method on `Brief`:

```python
def to_structural_grid_input(self) -> StructuralGridInput:
    """Convert Brief into Component 7's StructuralGridInput.

    Maps:
      - plot.width_m, plot.depth_m → envelope_width_m, envelope_depth_m
        (after subtracting NBC-compliant setbacks)
      - floors above ground (excluding ground & terrace) → floors_above_ground
      - plot.city → city
      - seismic zone derived from city (lookup table, same as Component 7)
      - has_infill_walls=True (typical residential, default)
      - user_claims_engineer_reviewed=False (Component 1 doesn't capture this)
    """
```

This conversion is the key handshake. The ComponentContract validation from v0.7.1 will catch any drift between Brief shape and what Component 7 expects.

### 7.2 What Component 1 produces

`BriefCaptureOutput`:
```
BriefCaptureOutput
├── brief: Brief                       (the validated, assembled brief)
├── user_form_input: BriefFormInput    (raw input echoed for transparency)
├── soft_guidance: tuple[GuidanceMessage, ...]
├── compliance_summary: ComplianceSummary  (setback comparison, key concerns)
├── trace_id: str
├── kb_versions: dict[str, str]
└── ready_for_downstream: bool         (False if STRONG_CONCERN unresolved)
```

`ready_for_downstream` is informational — even if False, downstream consumers can still proceed if user explicitly overrides. We never block.

### 7.3 explain() output

Component 1's `explain()` produces a user-facing rendering similar in style to Component 7:

```
══════════════════════════════════════════════════════════════════════
YOUR BRIEF — captured for {plot.city}
══════════════════════════════════════════════════════════════════════

PLOT
  Dimensions: {width}m × {depth}m = {area} sqm
  Facing: {facing}
  Road width: {road_width}m
  {if corner_plot: "Corner plot, second road: {x}m"}

SETBACKS
  Your stated setbacks vs. {source} compliant:
                Your input    Compliant    Difference
    Front:        {x}m          {y}m         {diff}
    Rear:         {x}m          {y}m         {diff}
    Side (L):     {x}m          {y}m         {diff}
    Side (R):     {x}m          {y}m         {diff}

  Compliance: {COMPLIANT / NON-COMPLIANT}
  {if non-compliant: STRONG_CONCERN messages}

FLOOR COMPOSITION
  Total floors: G+{n}
  Total estimated built-up area: ~{x} sqft

  Ground Floor: {use}
    Rooms: {summary}
  First Floor: {use}
    Rooms: {summary}
  ...

BUDGET
  Your range: ₹{min}L – ₹{max}L
  Estimated for this design ({city} basic finish): ₹{est_min}L – ₹{est_max}L
  {if mismatch: STRONG_CONCERN message}

──────────────────────────────────────────────────────────────────────
SOFT GUIDANCE ({n} concerns to review)
──────────────────────────────────────────────────────────────────────
[STRONG_CONCERN] {message1}
[CONCERN] {message2}
[INFO] {message3}

──────────────────────────────────────────────────────────────────────
NEXT STEPS
──────────────────────────────────────────────────────────────────────
{if ready_for_downstream}
  Your brief is ready. Next: layout generation will show what's possible
  on this plot with your composition.
{else}
  Please review the [STRONG_CONCERN] items above. You can:
  - Adjust your inputs and re-submit
  - Accept the concerns and proceed (you'll see warnings throughout)

──────────────────────────────────────────────────────────────────────
LEGAL & STATUTORY DISCLOSURES
──────────────────────────────────────────────────────────────────────
{full legal block from v0.6}

REPRODUCIBILITY
  Trace ID: {trace_id}
  KB versions: {kb_versions}
══════════════════════════════════════════════════════════════════════
```

---

## 8. ComponentContract declaration

```python
@component_contract(
    component_id="C01_brief_capture",
    version="0.1",
    description="Captures user homebuilding brief, validates against NBC/DCR.",
    consumes=(
        required("plot_width_m", "float", "Plot width facing street", "5.0..60.0"),
        required("plot_depth_m", "float", "Plot depth", "3.0..60.0"),
        required("plot_facing", "str", "N/E/S/W/NE/NW/SE/SW"),
        required("city", "str", "One of 6 supported cities"),
        required("road_width_m", "float", "Abutting road width", "1.5..30.0"),
        optional("corner_plot", "bool"),
        optional("second_road_width_m", "float"),
        required("user_setback_front_m", "float", "User-stated front setback"),
        required("user_setback_rear_m", "float", "User-stated rear setback"),
        required("user_setback_side_left_m", "float", "User-stated left side setback"),
        required("user_setback_side_right_m", "float", "User-stated right side setback"),
        required("floors", "list", "List of FloorRequirement specs"),
        required("budget_min_lakhs", "int", "Minimum budget in lakhs INR"),
        required("budget_max_lakhs", "int", "Maximum budget in lakhs INR"),
        optional("additional_requirements", "list", "Free-text user notes"),
        optional("soil_type_known", "str", "If user knows soil type"),
    ),
    produces=(
        required("brief", "Brief", "Validated brief domain object"),
        required("soft_guidance", "tuple", "Tuple of GuidanceMessage"),
        required("compliance_summary", "ComplianceSummary"),
        required("trace_id", "str"),
        required("kb_versions", "dict"),
        required("ready_for_downstream", "bool"),
    ),
)
class BriefCaptureEngine:
    ...
```

Note: `consumes` are primitives (form fields). `produces` includes `Brief` which IS a domain type — so anyone consuming Component 1's output is enforced (via v0.7.1) to use the actual domain object.

---

## 9. File structure

```
buildemup/
├── domain/
│   ├── plot.py                    [NEW]  Plot, PlotFacing, Setbacks
│   ├── floor_requirement.py       [NEW]  FloorRequirement, RoomRequirement, RoomType, FloorUse
│   ├── brief.py                   [NEW]  Brief, BudgetRange, GuidanceMessage,
│                                          ComplianceSummary
│   └── __init__.py                [MODIFIED]  Export new types
├── components/
│   ├── c01_brief_capture.py       [NEW]  Orchestrator: BriefCaptureEngine
│   └── c01/
│       ├── __init__.py
│       ├── form_validator.py      [NEW]  Form input validation
│       ├── setback_calculator.py  [NEW]  NBC/DCR setback computation
│       ├── room_composer.py       [NEW]  Room composition validation + defaults
│       ├── budget_estimator.py    [NEW]  Rough cost estimate from brief
│       └── soft_guide_engine.py   [NEW]  Generates GuidanceMessage list
├── kb_rules/
│   ├── setback_rules.json         [NEW]  Per-city DCR setback rules
│   └── room_minimums.json         [NEW]  NBC room minimum sizes
├── utils/
│   └── kb_rules_loader.py         [MODIFIED]  Add loaders + validators for new files
├── tests/
│   └── test_c01_brief_capture.py  [NEW]  ~30-40 tests
└── docs/
    └── component1/
        └── SPEC_v0.1.md           [THIS DOC]
```

Estimated total new code: ~1500-2000 lines (plus tests).

---

## 10. Test plan

Test sections, target ~35 tests total:

### A. Domain object validation (~8 tests)
- Plot validates dimensions
- Plot rejects out-of-range
- Plot requires second_road_width if corner_plot
- FloorRequirement validates room composition
- RoomRequirement applies NBC minimums when None
- Brief assembly happens correctly
- Setbacks dataclass immutability
- BudgetRange validation

### B. Setback calculation (~8 tests)
- Chennai TNCDBR for plot ≤50 sqm (small, narrow road)
- Chennai TNCDBR for plot 50–150 sqm
- Chennai TNCDBR for plot 150–300 sqm
- Chennai TNCDBR for plot >300 sqm
- NBC fallback for Mumbai (until v0.2)
- Corner plot uses wider road for front
- Setback comparison flags non-compliance correctly

### C. Room composition + NBC minimums (~6 tests)
- Default 2BHK G+1 template loads
- User-overridden room sizes applied
- NBC minimums applied when user doesn't specify
- Bathroom auto-count from bedrooms
- Staircase auto-included
- Total built area computed correctly

### D. Budget estimation (~5 tests)
- Estimated cost roughly matches per-city rates
- Soft-guide STRONG_CONCERN when budget too low
- Soft-guide INFO when budget aligns
- Soft-guide INFO when budget generous
- Estimate handles G-only (no upper floors)

### E. Soft-guide message generation (~5 tests)
- STRONG_CONCERN for setback violation
- CONCERN for missing master bedroom
- INFO for compliant setbacks
- Messages always include action verb
- Messages always include source reference

### F. Component 1 → Component 7 handshake (~5 tests)
- Brief.to_structural_grid_input() produces valid input
- Component 7 accepts it without error
- Round-trip city/zone preserved
- Floor count translated correctly
- Setbacks subtracted from envelope correctly

### G. ComponentContract enforcement (~3 tests)
- Component 1 contract registered correctly
- Brief domain type enforced when consumed downstream
- Form input validates against contract

---

## 11. What's deferred to v0.2+ (locked)

Items I will NOT add to v0.1, even if tempted:

- **Conversational LLM input** (per Q1) — form is v1; conversational v2
- **5 of 6 city DCRs** — Chennai full, others use NBC fallback in v0.1
- **Feasibility analysis** — that's Component 2
- **Trade-off recommendations** — separate component
- **Layout generation** — Component 4
- **3D rendering** — v2 (Phase B)
- **Interior selections** — v3 (Phase C)
- **CAD export** — v4 (Phase D)
- **Vastu checks** — Component 7 already has vastu_engine; we may use it for guidance but not block
- **Phased construction planning** — mention in soft-guide, don't model
- **Multi-block / group developments** — single block only
- **Commercial/mixed-use** — residential only
- **Plot subdivision** — single plot only
- **Soil test recommendations** — Component 7 handles this; we just pass through
- **Persistent storage of briefs** — in-memory only (like insights buffer); no DB

Add to `docs/v2_backlog.md` as "Component 1 v0.2 candidates."

---

## 12. Sequence of work (locked)

If this spec is approved, the build sequence is:

1. **Session 1**: Domain objects + test suite skeleton (no engine logic yet)
2. **Session 2**: Setback calculator + KB JSON files + parity tests
3. **Session 3**: Room composer + budget estimator + soft-guide engine
4. **Session 4**: BriefCaptureEngine orchestrator + explain() rendering + Component 7 handshake
5. **Session 5**: Final tests, fix edge cases, package v0.1

5 sessions = manageable. If we hit the 4-month Component-7 spiral again, something went wrong with scope discipline.

---

## 13. Open questions for the user (must answer before code)

1. **Currency handling**: I'm hardcoding INR for v0.1. Confirm you don't need other currencies.
2. **User identity**: Component 1 collects no user-identifying info (no name, email, phone). Confirm OK — we can add in v0.2 if needed for CRM/lead gen.
3. **Save/resume**: Component 1 v0.1 is stateless — user fills the form, gets output, done. No save/resume mid-form. Confirm OK for v0.1.
4. **Form vs API**: I'll build the engine + ComponentContract. The actual web form (HTML/JS) is presentation-layer work — same as how Component 7 today doesn't have its own UI. Are you handling the form UI separately, or do you want me to include a minimal form template?
5. **Vastu integration**: Component 7's KB has `vastu_engine`. Do you want Component 1 to surface vastu hints (e.g., "for east-facing plot, kitchen typically southeast") as INFO-level guidance? Or skip vastu entirely in Component 1 and let Component 4 (layout) handle it?

Answer these 5, then code starts.

---

**End of spec.** Total: 12 sections + 5 open questions for user lock-in.
