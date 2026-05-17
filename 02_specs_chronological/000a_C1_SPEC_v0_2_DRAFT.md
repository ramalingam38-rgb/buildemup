# Component 1 — Brief Capture Engine (v0.2 Specification — LOCKED)

**Status:** Locked spec. Ready to begin Session 1 of code.
**Target version:** Component 1 v0.1 (release version stays 0.1; this is spec v0.2)
**Supersedes:** `SPEC_v0.1.md` (previous draft)
**Component contract version:** 0.7.1 (already enforced by infrastructure)

---

## 0. What changed from SPEC_v0.1.md

SPEC_v0.1.md was reviewed and 10 drawbacks were flagged. All 10 accepted with triage:
- Drawbacks 1, 2, 4, 5, 6, 7, 8, 9, 10 → real logic/spec changes
- Drawback 3 → documentation-only (behaviour already correct)

User answered the 5 open questions. Key decisions:
- **Q1 currency**: INR only ✅
- **Q2 email/phone**: optional in v0.1, becomes required at billing stage (later component) ✅
- **Q3 save/resume**: localStorage + optional email-resume-link ✅
- **Q4 form UI**: I build it (minimal Tailwind HTML template) ✅
- **Q5 vastu**: three-tier — OFF / PARTIAL / FULL, default OFF, all INFO-level only ✅

This v0.2 spec reflects all 14 changes. Scope has **tightened**, not expanded.

---

## 1. Purpose & success criteria

### What Component 1 does (unchanged)

Captures the user's homebuilding brief — plot details, floor count, per-floor room composition, additional requirements, budget — and converts it into a validated `Brief` domain object that downstream components (especially Component 7 structural grid) consume via the `ComponentContract` system.

### What Component 1 does NOT do (unchanged + reinforced)

This is critical, because Component 7 took 4 months partly because we kept reopening scope. Component 1 v0.1 explicitly does **not**:

- Generate layouts (Component 4)
- Run feasibility analysis (Component 2)
- Produce trade-off recommendations (later component)
- Render 3D views (Phase B / v2)
- Handle interior selections, tiles, furniture (Phase C / v3)
- Produce CAD sheets or municipal documents (Phase D / v4)
- Use conversational LLM extraction (form-based only per Q1)
- Persist briefs in a database (localStorage + optional email only)
- Handle authentication, billing, lead-capture CRM (later component)

If during build I'm tempted to add any of the above, that's scope creep. Refuse and add to v0.2+ backlog.

### Success criteria for v0.1

1. User can submit a complete brief via a structured form
2. System shows user-stated setbacks AND NBC/DCR-compliant setbacks side-by-side
3. **Setback computation accounts for plot type (DETACHED/SEMI_DETACHED/CONTINUOUS)** *(new per Drawback 1)*
4. Output is a `Brief` domain object that passes `ComponentContract` validation when fed to Component 7
5. **Budget guidance comes from Component 7 cost engine, not a parallel rate card** *(new per Drawback 4)*
6. **Floor area estimate includes circulation factor (1.30)** *(new per Drawback 5)*
7. **Top 3 guidance messages surfaced prominently** *(new per Drawback 6)*
8. **Parking feasibility checked (plot width < 8m + stilt → STRONG_CONCERN)** *(new per Drawback 7)*
9. **Staircase auto-included for floors ≥ 2** *(new per Drawback 8)*
10. **Phased construction suggestion if budget < estimate** *(new per Drawback 9)*
11. **"ASSUMPTIONS USED" section in explain()** *(new per Drawback 10)*
12. **Vastu three-tier opt-in (OFF/PARTIAL/FULL)** *(new per Q5)*
13. **Save/resume via localStorage + optional email link** *(new per Q3)*
14. Soft-guide validation flags weird inputs without rejecting them
15. End-to-end test: Brief → Component 7 produces a valid structural output
16. Test coverage: ~45-55 tests (up from 35 due to new drawback coverage)

### Emotional outcome (unchanged)

After completing the brief, the user should feel: "I told the system what I want. It heard me. It understood my plot, my city's rules, and what's important to my family. Now I'm ready to see what's possible."

---

## 2. Domain shape

### 2.1 New domain objects

Five new dataclasses in the `domain/` layer. All immutable (`frozen=True`), validate in `__post_init__`.

#### `Plot` — plot details *(updated per Drawback 1)*
```
Plot
├── width_m: float          (street-facing dimension)
├── depth_m: float          (perpendicular to street)
├── facing: PlotFacing      (NORTH / EAST / SOUTH / WEST / NE / NW / SE / SW)
├── city: str               (lowercased, must be in supported_cities)
├── road_width_m: float     (abutting road width — drives setback rules)
├── corner_plot: bool       (default False; if True, two roads abut)
├── second_road_width_m: float | None  (only if corner_plot)
├── plot_type: PlotType     (DETACHED / SEMI_DETACHED / CONTINUOUS)  *(new — Drawback 1)*
└── soil_type_known: SoilType | None   (optional; if known, drives Component 7)
```

**Why plot_type matters (per Drawback 1):**
- DETACHED (default): plot has no shared walls with neighbours — needs setbacks on all 4 sides
- SEMI_DETACHED: shares ONE side wall with a neighbour — no setback on that side
- CONTINUOUS: shares BOTH side walls (row-house / Continuous Building Area in Chennai TNCDBR) — no side setbacks at all; only front + rear

This is critical for accurate setback calculation. Chennai TNCDBR explicitly defines "Continuous Building Area" as a plot type with relaxed setbacks.

**Enum:**
```python
class PlotType(Enum):
    DETACHED = "detached"          # No shared walls — 4-side setbacks
    SEMI_DETACHED = "semi_detached" # Shared wall on one side — 3-side setbacks
    CONTINUOUS = "continuous"       # Row-house, CBA declared — front + rear only
```

**Constraints (validated in `__post_init__`):**
- `width_m`: 3.0–60.0
- `depth_m`: 3.0–60.0
- `road_width_m`: 1.5–30.0
- City must be in our 6 supported launch cities (Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi)
- If `corner_plot=True`, `second_road_width_m` is required
- `plot_type` defaults to DETACHED (safest, most common for standalone homes)

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
├── room_type: RoomType
├── count: int
├── min_size_sqm: float | None
└── preferred_size_sqm: float | None
```

#### `VastuPreference` — vastu opt-in *(new per Q5)*
```python
class VastuTier(Enum):
    OFF = "off"          # No vastu guidance
    PARTIAL = "partial"  # 7 core items
    FULL = "full"        # Everything in vastu_engine KB
```

**The 7 PARTIAL items (user-facing list, always shown so user knows what they're getting):**

```python
VASTU_PARTIAL_ITEMS = (
    "Main door direction (most important)",
    "Kitchen direction (southeast preferred)",
    "Master bedroom direction (southwest preferred)",
    "Pooja room direction (northeast preferred)",
    "Toilet/bathroom location (avoid northeast)",
    "Staircase direction (avoid northeast)",
    "Water tank location (underground northeast / overhead southwest)",
)
```

When user picks PARTIAL in form, we show them this list so they know exactly what they're opting into. No hidden behaviour.

**ALL tiers produce INFO-level guidance only — never STRONG_CONCERN.** Vastu is cultural preference, not building code. We never block on vastu.

#### `Brief` — top-level capture *(updated)*
```
Brief
├── plot: Plot
├── user_stated_setbacks: Setbacks
├── nbc_compliant_setbacks: Setbacks
├── floors: tuple[FloorRequirement, ...]
├── budget_range: BudgetRange
├── additional_requirements: tuple[str, ...]
├── soft_guidance: tuple[GuidanceMessage, ...]        (all messages)
├── top_guidance: tuple[GuidanceMessage, ...]         (top 3 for prominent display — new per Drawback 6)
├── vastu_preference: VastuTier                       (new per Q5)
├── user_email: str | None                            (new per Q2 — optional)
├── user_phone: str | None                            (new per Q2 — optional)
├── resume_token: str | None                          (new per Q3 — for save/resume)
├── assumptions_used: tuple[str, ...]                 (new per Drawback 10)
├── trace_id: str
└── kb_versions: dict[str, str]
```

#### Supporting types

- `Setbacks(front_m, rear_m, side_left_m, side_right_m)` — frozen dataclass
- `BudgetRange(min_lakhs: int, max_lakhs: int, currency: str = "INR")`
- `GuidanceMessage(severity, text, context, action_verb)` — soft-guide output
- `ComplianceSummary(is_compliant, violations, source_authority)`
- Enums: `PlotFacing`, `FloorUse`, `RoomType`, `PlotType`, `VastuTier`, `GuidanceSeverity`

### 2.2 Domain enforcement (already from v0.7.1)

`Brief`, `Plot`, `FloorRequirement`, `RoomRequirement` all added to `_DOMAIN_TYPE_NAMES` in `component_contract.py`. Downstream components consuming these will be enforced to use actual domain objects.

---

## 3. NBC + DCR setback rules *(updated per Drawback 1)*

### 3.1 Rule discovery (unchanged from v0.1)

NBC 2016 general + city DCRs govern. For v0.1:
- Chennai (TNCDBR 2019) — full implementation
- Other 5 cities — NBC general fallback with explicit disclosure

### 3.2 Setback computation logic *(updated)*

```python
def compute_compliant_setbacks(plot: Plot) -> tuple[Setbacks, str]:
    """Returns (compliant_setbacks, source_disclosure).

    v0.2: Plot type now drives setback shape:
    - CONTINUOUS: front + rear only (sides = 0)
    - SEMI_DETACHED: front + rear + one side
    - DETACHED: all four sides (default)
    """
    if plot.plot_type == PlotType.CONTINUOUS:
        return _continuous_plot_setbacks(plot)
    elif plot.plot_type == PlotType.SEMI_DETACHED:
        return _semi_detached_setbacks(plot)

    # DETACHED — full setbacks
    if plot.city == "chennai":
        return _chennai_tncdbr_setbacks(plot), "TNCDBR 2019"
    else:
        return _nbc_fallback_setbacks(plot), "NBC 2016 general (city DCR pending)"
```

**For CONTINUOUS plots:**
- Side setbacks = 0 (required to match neighbour walls)
- Front setback = still required (driven by road width)
- Rear setback = 1.0m minimum (fire access + ventilation, per TNCDBR CBA rule)

**For SEMI_DETACHED plots:**
- One side setback = 0 (the shared side — user must specify which)
- Other side setback = as per detached rules
- Front + rear = as per detached rules

### 3.3 Chennai TNCDBR rules (same as SPEC_v0.1, unchanged)

### 3.4 Soft-guide messages from setback comparison (unchanged from v0.1)

### 3.5 KB structure for setbacks

`kb_rules/setback_rules.json` now includes:
```json
{
  "chennai": {
    "detached": { ... tier tables ... },
    "semi_detached": { ... },
    "continuous": {
      "front_m_by_road_width": { "3.0": 0.9, "7.0": 1.5, ... },
      "rear_m": 1.0,
      "side_m": 0.0,
      "_notes": "Continuous Building Area per TNCDBR 2019 s.35(1) Explanation 1(v)"
    }
  },
  "_fallback_nbc": { ... same tiers ... }
}
```

---

## 4. Per-floor room composition *(updated per Drawbacks 5, 8)*

### 4.1 Room types (unchanged from v0.1)

### 4.2 NBC minimum sizes (unchanged — loaded from JSON)

### 4.3 Circulation factor — NEW per Drawback 5

Total floor area ≠ sum of room areas. Walls, passages, landings add 25-35%.

```python
def estimate_floor_area_sqm(floor: FloorRequirement) -> float:
    """Estimate total floor area including circulation.

    Per Drawback 5: rooms don't fill 100% of floor — walls, passages,
    stairs take 25-35% in typical Indian residential.
    """
    CIRCULATION_FACTOR = 1.30  # Middle of 1.25-1.35 range

    total_room_area = 0.0
    for room in floor.rooms:
        # Use preferred if specified, else min_size, else NBC default
        size = (room.preferred_size_sqm
                or room.min_size_sqm
                or _nbc_min_size(room.room_type))
        total_room_area += room.count * size

    return total_room_area * CIRCULATION_FACTOR
```

This is exposed in `ASSUMPTIONS USED` section so users know we applied the factor.

### 4.4 Auto-staircase — NEW per Drawback 8

```python
def ensure_staircase_present(brief: Brief) -> tuple[Brief, list[GuidanceMessage]]:
    """If floors ≥ 2 and no staircase anywhere, add one to ground floor.

    Per Drawback 8: User may not explicitly add staircase. We auto-include
    with INFO message so layout doesn't break downstream.
    """
    total_floors_above_ground = len([f for f in brief.floors
                                     if f.floor_use == FloorUse.RESIDENTIAL]) - 1
    if total_floors_above_ground < 1:
        return brief, []  # Single-floor home, no staircase needed

    has_staircase = any(
        any(r.room_type == RoomType.STAIRCASE for r in f.rooms)
        for f in brief.floors
    )

    if not has_staircase:
        # Add to ground floor with INFO message
        message = GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text="Staircase was not specified. Added to ground floor automatically "
                 "using NBC minimum 5.5 sqm (including landing).",
            context="auto_staircase",
            action_verb="Adjust",
        )
        # ... add staircase to ground floor ...
        return updated_brief, [message]

    return brief, []
```

### 4.5 Parking feasibility — NEW per Drawback 7

```python
def check_parking_feasibility(brief: Brief) -> list[GuidanceMessage]:
    """Per Drawback 7: Plot width < 8m + stilt parking = parking won't fit.

    Car needs ~2.5m width + 0.5m circulation = 3.0m minimum usable width
    after setbacks. At 8m plot with 1m side setback each side = 6m
    internal = room for 2 cars. Below 8m = tight.
    """
    has_stilt = any(f.floor_use == FloorUse.STILT_PARKING for f in brief.floors)
    if not has_stilt:
        return []

    if brief.plot.width_m < 8.0:
        return [GuidanceMessage(
            severity=GuidanceSeverity.STRONG_CONCERN,
            text=f"Your plot width of {brief.plot.width_m}m is tight for stilt "
                 f"parking. After setbacks, you'll have about "
                 f"{brief.plot.width_m - brief.nbc_compliant_setbacks.side_left_m - brief.nbc_compliant_setbacks.side_right_m}m "
                 f"internal width. One car needs 2.5m + circulation. "
                 f"Consider: (a) surface parking in front setback, "
                 f"(b) single-car stilt only, "
                 f"(c) ground-floor parking (loses habitable space).",
            context="parking_feasibility",
            action_verb="Reconsider",
        )]
    return []
```

---

## 5. Budget range *(MAJOR UPDATE per Drawback 4)*

### 5.1 Single source of truth — NEW architecture

**Component 1 does NOT have its own cost engine.** It calls Component 7 in "cost-only mode" and uses Component 7's result.

```python
def estimate_budget_from_brief(brief: Brief) -> CostEstimate:
    """Per Drawback 4: Use Component 7's cost engine, don't duplicate.

    We build a temporary StructuralGridInput from the brief, run
    Component 7 in cost-estimation mode, and use its output.
    """
    temp_input = brief.to_structural_grid_input()
    c7_result = StructuralGridEngine().execute(temp_input)
    return CostEstimate(
        exact_value=c7_result.cost.exact_value,
        range_min=c7_result.cost.range_min,
        range_max=c7_result.cost.range_max,
        confidence=c7_result.cost.confidence,
        source="Component 7 structural + foundation cost engine",
    )
```

**Trade-off accepted**: Component 7 runs twice per end-to-end flow (once in Component 1 for budget guidance, once downstream for real). ~200ms overhead per request. Acceptable for brief-capture which takes minutes anyway. Guarantees budget number in Component 1's output matches Component 7's number exactly — no user trust loss.

### 5.2 Soft-guide validation

If user budget < 80% of Component 7 estimated:
- `STRONG_CONCERN`: *"Your budget of ₹{budget}L is below the ₹{est}L estimated for this design. See Top Recommendations for trade-off options."*
- **PLUS NEW per Drawback 9:** phased construction suggestion

### 5.3 Phased construction guidance — NEW per Drawback 9

```python
def suggest_phased_construction_if_needed(
    brief: Brief, c7_cost: CostEstimate
) -> list[GuidanceMessage]:
    """Per Drawback 9: If budget < estimate, suggest phased approach."""
    if brief.budget_range.max_lakhs * 100_000 < c7_cost.exact_value * 0.80:
        # Compute ground-floor-only cost (rough = 55% of full G+1)
        ground_only_cost = c7_cost.exact_value * 0.55
        return [GuidanceMessage(
            severity=GuidanceSeverity.INFO,
            text=f"Your budget (₹{brief.budget_range.max_lakhs}L) is below "
                 f"the ₹{c7_cost.exact_value/100_000:.0f}L estimate for full design. "
                 f"Consider phased construction: build ground floor now "
                 f"(~₹{ground_only_cost/100_000:.0f}L), with columns and "
                 f"foundation designed for future vertical expansion. "
                 f"Many Indian families build this way — it's a proven strategy.",
            context="phased_construction",
            action_verb="Consider",
        )]
    return []
```

---

## 6. Soft-guide validation — full philosophy *(updated per Drawback 6)*

Per Q3 = "soft guide" decision. Component 1 NEVER refuses input.

### 6.1 Three severity levels (unchanged)

- `INFO` — informational, neutral or positive
- `CONCERN` — something to think about, not blocking
- `STRONG_CONCERN` — likely a problem; user should reconsider but can override

### 6.2 Top 3 prioritisation — NEW per Drawback 6

```python
def compute_top_guidance(
    all_messages: list[GuidanceMessage]
) -> tuple[GuidanceMessage, ...]:
    """Extract top 3 messages for prominent display.

    Priority order:
    1. All STRONG_CONCERN first (most critical)
    2. Then CONCERN
    3. Then INFO (only if fewer than 3 of above)

    Within each severity, order by appearance (stable sort).
    """
    severity_order = {
        GuidanceSeverity.STRONG_CONCERN: 0,
        GuidanceSeverity.CONCERN: 1,
        GuidanceSeverity.INFO: 2,
    }
    sorted_msgs = sorted(all_messages,
                         key=lambda m: severity_order[m.severity])
    return tuple(sorted_msgs[:3])
```

`Brief` carries both `soft_guidance` (all) and `top_guidance` (top 3). explain() shows top_guidance prominently at top, then full list below collapsed-ish.

### 6.3 Full list of soft-guide triggers

**STRONG_CONCERN:**
- Setbacks below DCR minimum (Section 3)
- Budget below 80% of Component 7 estimate (Section 5)
- Parking feasibility fail (Section 4.5)
- Bathroom-to-bedroom ratio < 0.5 (weird)
- Plot aspect ratio > 4.0 (hard to lay out — also flagged in Component 7 structurally)

**CONCERN:**
- No master bedroom specified
- No kitchen on any floor
- Floors ≥ 3 with budget at lower end (complexity + cost risk)

**INFO:**
- Setbacks within compliance
- Phased construction suggestion (Section 5.3)
- Auto-staircase added (Section 4.4)
- Vastu guidance (if opted in — Section 7)
- "Your budget is generous" (if >150% of estimate)

---

## 7. Vastu integration *(NEW per Q5)*

### 7.1 Three-tier opt-in

User picks on form:
- **OFF** (default): no vastu mentioned anywhere
- **PARTIAL**: 7 items (listed in Section 2.1 — shown to user on form)
- **FULL**: everything in Component 7's `vastu_engine` KB

### 7.2 User-visible list

When user selects PARTIAL on form, show:
> **Partial vastu includes these 7 items:**
> 1. Main door direction (most important)
> 2. Kitchen direction (southeast preferred)
> 3. Master bedroom direction (southwest preferred)
> 4. Pooja room direction (northeast preferred)
> 5. Toilet/bathroom location (avoid northeast)
> 6. Staircase direction (avoid northeast)
> 7. Water tank location (underground northeast / overhead southwest)
>
> Full vastu adds 15+ more items including furniture placement, window directions, plot shape considerations.

### 7.3 Implementation

```python
def generate_vastu_guidance(
    brief: Brief,
) -> list[GuidanceMessage]:
    """Generate INFO-only vastu messages based on user's tier preference.

    NEVER produces STRONG_CONCERN or CONCERN — vastu is preference, not code.
    """
    if brief.vastu_preference == VastuTier.OFF:
        return []

    messages = []

    # PARTIAL + FULL both get these 7
    messages.extend(_partial_vastu_checks(brief))

    # FULL adds everything else
    if brief.vastu_preference == VastuTier.FULL:
        messages.extend(_full_vastu_checks(brief))

    return messages  # All INFO severity
```

### 7.4 Vastu KB reuse

Uses Component 7's existing `kb/vastu_engine.py`. No duplication. Component 1 just filters / selects which items to surface based on tier.

---

## 8. Save/resume *(NEW per Q3)*

### 8.1 Architecture — browser localStorage primary, email link backup

**Primary save mechanism:**
- User fills part of the form, clicks "Save & Continue Later"
- JS serializes in-progress form state to JSON
- Stored in browser `localStorage` under key `buildemup_brief_{resume_token}`
- User sees: "Your progress is saved on this browser. Clear cookies = lose progress."

**Backup email link:**
- If user provides email, we send them a link: `https://your-app/resume?token={resume_token}`
- Token is 12-char random string stored alongside brief in localStorage
- If user switches devices, they click the email link, which pulls the brief from... wait, email-backed resume means we need server-side storage.

**Honest re-assessment:** Email-resume-link requires server-side storage (even if just temporary). Options:
- (a) Send the full serialized brief in the email link as a base64 payload (works, but URL size limits + email privacy)
- (b) Store the brief server-side keyed by token (needs minimal backing — Redis / SQLite / even a file)
- (c) Drop email-resume for v0.1, localStorage only

**My recommendation after re-think: (c) localStorage only for v0.1.** Email-resume needs server-side state which contradicts our "no DB in v0.1" constraint. We can do email-resume properly in Component 1 v0.2 when we add auth.

**If user provides email in v0.1, we store it in the Brief but don't send a resume link — we use it later for lead-capture / billing notifications.**

### 8.2 Implementation

```python
# Python side — session endpoint
@endpoint("/api/brief/save")
def save_brief_state(form_state: dict, token: str | None) -> dict:
    """Save happens client-side in localStorage. This endpoint is a no-op
    for v0.1 but reserved for v0.2 when we add server-side persistence."""
    if token is None:
        token = generate_resume_token()
    return {"resume_token": token, "saved_at": now()}

# JavaScript side (form UI)
function saveBriefLocal(formState, token) {
    if (!token) token = crypto.randomUUID().slice(0, 12);
    localStorage.setItem(`buildemup_brief_${token}`, JSON.stringify(formState));
    return token;
}
```

### 8.3 Limitations we disclose to user

Form shows above "Save & Continue Later" button:
> *"Progress is saved on this browser only. Clear browser data or switch devices = progress lost. Cross-device save is coming in v0.2."*

---

## 9. Form UI template *(NEW per Q4)*

### 9.1 Scope

I build a **minimal** Tailwind HTML form. Not designed-by-committee, but functional and looks like a real product. User (Ramalingam) hosts it on Railway alongside the Python engine.

### 9.2 Tech choices

- HTML + Tailwind CSS (via CDN) — no build step, deploys as static files
- Vanilla JS (no React/Vue) — keeps it deploy-anywhere
- POSTs form data to `/api/brief/capture` endpoint
- Renders Component 1's `explain()` output as formatted HTML below the form

### 9.3 What the form looks like

```
[Logo / BuildemUp title]

Step 1 of 4: Your plot
  Plot width (m): [_____]
  Plot depth (m): [_____]
  Facing: [dropdown: N/E/S/W/NE/NW/SE/SW]
  City: [dropdown: 6 supported cities]
  Plot type: [radio: Detached / Semi-detached / Continuous]
  Road width (m): [_____]
  [checkbox] Corner plot (abuts 2 roads)

Step 2 of 4: What you want on each floor
  How many floors? [dropdown: G / G+1 / G+2 / G+3]
  [For each floor, show composition with defaults filled]
  [Auto-staircase indicator for ≥2 floors: INFO badge]

Step 3 of 4: Your setbacks & budget
  Front setback (m): [_____ compliant: 1.5m]
  Rear setback (m): [_____ compliant: 1.5m]
  Side setbacks... [shown conditionally based on plot_type]
  Budget range: [min __ L] to [max __ L]
  [INFO: "Budget guidance uses our Component 7 cost engine"]

Step 4 of 4: Optional preferences
  Vastu: [radio: Off / Partial (7 items listed) / Full (15+ items)]
  Additional notes: [textarea]
  Email (optional): [_____]
  Phone (optional): [_____]

[Save & Continue Later]  [Submit Brief]
```

### 9.4 What gets delivered

- `static/brief_form.html` — the form
- `static/brief_form.js` — validation + localStorage save/resume
- `static/brief_form.css` — minimal Tailwind overrides
- `api_handler.py` — Python endpoint `/api/brief/capture` that calls BriefCaptureEngine

### 9.5 What's NOT in v0.1 form

- Mobile-responsive polish (works on mobile but not designed for it yet)
- Progress indicator beyond step counter
- Field-level validation feedback (only form-level)
- Multi-language support
- Dark mode
- Accessibility beyond basic semantic HTML

These are v0.2 form UX improvements.

---

## 10. Output shape & downstream handoff

### 10.1 Brief → Component 7 conversion *(updated per Drawbacks 2, 3)*

```python
def to_structural_grid_input(self) -> StructuralGridInput:
    """Convert Brief into Component 7's StructuralGridInput.

    v0.2 explicit behaviour (per Drawbacks 2, 3):

    Drawback 2 (envelope):
      - Compute rectangular envelope assuming clean subtraction of setbacks
      - Record assumption: is_rectangular=True
      - Layout engine (Component 4) may refine this later

    Drawback 3 (floor count):
      - floors_above_ground counts ALL load-bearing floors:
          * STILT_PARKING counted (it's a load-bearing structural level)
          * RESIDENTIAL counted
          * TERRACE slab counted (it carries water tank + live load)
      - Only explicitly-void floors are excluded (none in v0.1)
    """
    # v0.2 Drawback 2: explicit rectangular assumption
    envelope_width_m = (
        self.plot.width_m
        - self.nbc_compliant_setbacks.side_left_m
        - self.nbc_compliant_setbacks.side_right_m
    )
    envelope_depth_m = (
        self.plot.depth_m
        - self.nbc_compliant_setbacks.front_m
        - self.nbc_compliant_setbacks.rear_m
    )

    # v0.2 Drawback 3: count load-bearing floors correctly
    # STILT + RESIDENTIAL above ground + TERRACE all count
    floors_above_ground = sum(
        1 for f in self.floors
        if f.floor_use in (
            FloorUse.STILT_PARKING,
            FloorUse.RESIDENTIAL,
            FloorUse.TERRACE_ACCESSIBLE,
            FloorUse.TERRACE_INACCESSIBLE,
        ) and f.floor_number > 0  # Ground floor (floor 0) is baseline
    )

    return StructuralGridInput(
        envelope_width_m=envelope_width_m,
        envelope_depth_m=envelope_depth_m,
        floors_above_ground=floors_above_ground,
        city=self.plot.city,
        seismic_zone=_city_to_seismic_zone(self.plot.city),
        has_infill_walls=True,  # default; user could override in v0.2
        user_claims_engineer_reviewed=False,  # Component 1 doesn't capture this
    )
```

### 10.2 Component 1 output

`BriefCaptureOutput` *(updated)*:
```
BriefCaptureOutput
├── brief: Brief
├── user_form_input: BriefFormInput
├── soft_guidance: tuple[GuidanceMessage, ...]
├── top_guidance: tuple[GuidanceMessage, ...]          (new per Drawback 6)
├── compliance_summary: ComplianceSummary
├── assumptions_used: tuple[str, ...]                  (new per Drawback 10)
├── c7_preview_cost: CostEstimate                      (new per Drawback 4)
├── trace_id: str
├── kb_versions: dict[str, str]
├── ready_for_downstream: bool
└── resume_token: str | None
```

### 10.3 explain() output *(updated — ASSUMPTIONS section added)*

```
══════════════════════════════════════════════════════════════════════
YOUR BRIEF — captured for {plot.city}
══════════════════════════════════════════════════════════════════════

[TOP 3 RECOMMENDATIONS — NEW per Drawback 6]
──────────────────────────────────────────────────────────────────────
PLEASE REVIEW THESE FIRST:
  1. [STRONG_CONCERN] {message}
  2. [CONCERN] {message}
  3. [INFO] {message}
──────────────────────────────────────────────────────────────────────

PLOT
  Dimensions: {width}m × {depth}m = {area} sqm
  Plot type: {detached/semi-detached/continuous}  [NEW per Drawback 1]
  ...

SETBACKS
  Your stated setbacks vs. {source} compliant:
  {table as before, but now respects plot_type:
   - CONTINUOUS shows only front + rear
   - SEMI_DETACHED shows only 3 sides}

FLOOR COMPOSITION
  ...
  Total estimated built-up area: {x} sqft
    [Based on room sizes × circulation factor 1.30 — NEW per Drawback 5]

BUDGET
  Your range: ₹{min}L – ₹{max}L
  Estimated via Component 7: ₹{c7_est}L [NEW per Drawback 4]
  {if mismatch: STRONG_CONCERN + phased construction suggestion}

{if vastu_preference != OFF:}
  VASTU GUIDANCE ({tier} tier)
  ──────────────────────────────────────────────────────────────────
  {list of vastu items as INFO messages}

COMPLETE SOFT GUIDANCE ({n} items)
  {all messages grouped by severity}

──────────────────────────────────────────────────────────────────────
ASSUMPTIONS USED — NEW per Drawback 10
──────────────────────────────────────────────────────────────────────
  • Floor-to-floor height: 3.0m (NBC typical residential)
  • Envelope assumed rectangular (layout engine will refine)
  • Circulation factor: 1.30 (rooms + walls + passages + stairs)
  • NBC minimum room sizes applied where user didn't specify
  • Construction rates: basic {city} finish via Component 7 cost engine
  • Staircase auto-added for floors ≥ 2 if not specified
  • Plot type: {detached/semi-detached/continuous}
  {if CONTINUOUS:} Side setbacks = 0 per CBA rule
  {if vastu != OFF:} Vastu guidance: {tier} tier

──────────────────────────────────────────────────────────────────────
NEXT STEPS
──────────────────────────────────────────────────────────────────────
{if ready_for_downstream}
  Your brief is ready. Next: layout generation (Component 4, coming soon)
  will show what's possible on this plot.
{else}
  Please review the STRONG_CONCERN items above. You can:
  - Adjust your inputs and re-submit
  - Accept the concerns and proceed

──────────────────────────────────────────────────────────────────────
LEGAL & STATUTORY DISCLOSURES
──────────────────────────────────────────────────────────────────────
{full legal block from v0.6}

REPRODUCIBILITY
  Trace ID: {trace_id}
  KB versions: {kb_versions}
  Resume token: {resume_token or "not saved"}
══════════════════════════════════════════════════════════════════════
```

---

## 11. ComponentContract declaration *(updated)*

```python
@component_contract(
    component_id="C01_brief_capture",
    version="0.1",
    description="Captures user homebuilding brief, validates against NBC/DCR, "
                "uses Component 7 cost engine for budget guidance.",
    consumes=(
        # Plot
        required("plot_width_m", "float", "Plot width facing street", "3.0..60.0"),
        required("plot_depth_m", "float", "Plot depth", "3.0..60.0"),
        required("plot_facing", "str", "N/E/S/W/NE/NW/SE/SW"),
        required("city", "str", "One of 6 supported cities"),
        required("road_width_m", "float", "Abutting road width", "1.5..30.0"),
        required("plot_type", "str", "DETACHED/SEMI_DETACHED/CONTINUOUS"),  # NEW
        optional("corner_plot", "bool"),
        optional("second_road_width_m", "float"),
        # Setbacks
        required("user_setback_front_m", "float"),
        required("user_setback_rear_m", "float"),
        required("user_setback_side_left_m", "float"),
        required("user_setback_side_right_m", "float"),
        # Floors
        required("floors", "list", "List of FloorRequirement specs"),
        # Budget
        required("budget_min_lakhs", "int"),
        required("budget_max_lakhs", "int"),
        # Optional
        optional("additional_requirements", "list"),
        optional("soil_type_known", "str"),
        optional("vastu_preference", "str", "OFF/PARTIAL/FULL"),  # NEW
        optional("user_email", "str"),                            # NEW
        optional("user_phone", "str"),                            # NEW
        optional("resume_token", "str"),                          # NEW
    ),
    produces=(
        required("brief", "Brief", "Validated brief domain object"),
        required("soft_guidance", "tuple"),
        required("top_guidance", "tuple"),                         # NEW
        required("compliance_summary", "ComplianceSummary"),
        required("assumptions_used", "tuple"),                     # NEW
        required("c7_preview_cost", "CostEstimate"),               # NEW
        required("trace_id", "str"),
        required("kb_versions", "dict"),
        required("ready_for_downstream", "bool"),
        optional("resume_token", "str"),                           # NEW
    ),
)
class BriefCaptureEngine:
    ...
```

---

## 12. File structure *(updated)*

```
buildemup/
├── domain/
│   ├── plot.py                    [NEW]  Plot, PlotType, PlotFacing, Setbacks
│   ├── floor_requirement.py       [NEW]  FloorRequirement, RoomRequirement, FloorUse, RoomType
│   ├── brief.py                   [NEW]  Brief, BudgetRange, GuidanceMessage,
│                                          ComplianceSummary, VastuTier, CostEstimate
│   └── __init__.py                [MODIFIED]  Export new types + add to _DOMAIN_TYPE_NAMES
├── components/
│   ├── c01_brief_capture.py       [NEW]  Orchestrator: BriefCaptureEngine
│   └── c01/
│       ├── __init__.py
│       ├── form_validator.py      [NEW]  Form input validation
│       ├── setback_calculator.py  [NEW]  NBC/DCR setback computation
│       ├── room_composer.py       [NEW]  Room composition + circulation + auto-staircase
│       ├── budget_bridge.py       [NEW]  Calls Component 7 for budget (Drawback 4)
│       ├── soft_guide_engine.py   [NEW]  Generates GuidanceMessage list + top 3
│       ├── parking_feasibility.py [NEW]  Parking check (Drawback 7)
│       ├── phased_construction.py [NEW]  Phased suggestion (Drawback 9)
│       ├── vastu_filter.py        [NEW]  Partial/Full vastu filtering
│       └── assumptions_log.py     [NEW]  Tracks assumptions for Drawback 10
├── kb_rules/
│   ├── setback_rules.json         [NEW]  Per-city + per-plot-type DCR setback rules
│   └── room_minimums.json         [NEW]  NBC room minimum sizes
├── utils/
│   └── kb_rules_loader.py         [MODIFIED]  Add loaders for new files
├── static/                        [NEW — for form UI]
│   ├── brief_form.html
│   ├── brief_form.js
│   └── brief_form.css
├── api/                           [NEW]
│   └── brief_endpoint.py
├── tests/
│   └── test_c01_brief_capture.py  [NEW]  ~50 tests
└── docs/
    └── component1/
        ├── SPEC_v0.1.md           [SUPERSEDED]
        └── SPEC_v0.2.md           [THIS DOC — LOCKED]
```

Estimated total new code: **~2000-2500 lines** (up from 1500-2000 due to drawback fixes + form UI).

---

## 13. Test plan *(updated — ~50 tests)*

### A. Domain object validation (~10 tests)
- Plot validates dimensions / city / plot_type
- Plot rejects out-of-range
- Plot requires second_road_width if corner_plot
- FloorRequirement validates room composition
- RoomRequirement applies NBC minimums when None
- Brief assembly happens correctly
- Setbacks dataclass immutability
- BudgetRange validation
- VastuTier enum validation (new)
- PlotType enum validation (new)

### B. Setback calculation (~10 tests)
- Chennai TNCDBR for each size tier (4 tests)
- NBC fallback for Mumbai
- Corner plot uses wider road for front
- Setback comparison flags non-compliance
- **Plot type CONTINUOUS → side setbacks = 0** (new per Drawback 1)
- **Plot type SEMI_DETACHED → one side = 0** (new)
- Setback messages include source authority

### C. Room composition + NBC minimums (~8 tests)
- Default 2BHK G+1 template loads
- User-overridden room sizes applied
- NBC minimums applied when user doesn't specify
- Bathroom auto-count from bedrooms
- **Staircase auto-added for ≥2 floors** (new per Drawback 8)
- **Total built area uses circulation_factor 1.30** (new per Drawback 5)
- Floor area estimate matches hand-calculated case
- Staircase override with warning

### D. Budget estimation via Component 7 (~6 tests)
- **Estimated cost matches Component 7 output exactly** (new per Drawback 4)
- Soft-guide STRONG_CONCERN when budget < 80% of C7 estimate
- Soft-guide INFO when budget aligns
- **Phased construction suggestion when under budget** (new per Drawback 9)
- Component 7 not called if budget parsing fails (graceful degradation)
- Trace IDs correlate between Component 1 and Component 7

### E. Soft-guide message generation (~6 tests)
- STRONG_CONCERN for setback violation
- STRONG_CONCERN for parking feasibility fail (new per Drawback 7)
- CONCERN for missing master bedroom
- INFO for compliant setbacks
- **Top 3 prioritisation** (new per Drawback 6)
- Messages always include action verb + source

### F. Vastu integration (~5 tests)
- VastuTier.OFF produces no messages
- VastuTier.PARTIAL produces exactly 7 categories of messages
- VastuTier.FULL produces 15+ messages
- All vastu messages are INFO severity (never STRONG_CONCERN)
- Vastu uses Component 7's kb/vastu_engine (no duplication)

### G. Component 1 → Component 7 handshake (~5 tests)
- Brief.to_structural_grid_input() produces valid input
- Component 7 accepts it without error
- **floors_above_ground counts stilt + residential + terrace** (new per Drawback 3)
- **Envelope computed with explicit rectangular assumption** (new per Drawback 2)
- Round-trip city/zone preserved

### H. ComponentContract enforcement (~4 tests)
- Component 1 contract registered correctly
- Brief domain type enforced when consumed downstream
- Form input validates against contract
- Plot as domain object enforced

### I. Assumptions tracking (~3 tests — new per Drawback 10)
- All key assumptions captured in assumptions_used
- explain() renders ASSUMPTIONS USED section
- Assumptions list order stable

### J. Save/resume (~3 tests)
- resume_token generated correctly
- localStorage serialization round-trip
- User email stored in Brief if provided

**Target total: ~50 tests** (up from 35 in v0.1 spec).

---

## 14. What's deferred to v0.2+ (locked, reinforced)

All items from SPEC_v0.1 Section 11, plus:

- **Email-resume-link** (needs server-side storage — v0.2)
- **Cross-device save/resume** (needs auth — v0.2+)
- **Mobile-optimised form** (v0.2 UX pass)
- **Field-level form validation** (v0.2 UX pass)
- **Multi-language form** (v2)
- **Conversational LLM input** (v2 per Q1)
- **5 of 6 city DCRs full implementation** (Chennai full, others NBC fallback)
- **Vastu in the vastu_engine KB beyond current Component 7 scope** (v2)
- **Contact form / lead capture CRM** (separate auth component)

---

## 15. Sequence of work (locked)

If this spec is approved, the build sequence is:

1. **Session 1**: Domain objects (Plot, FloorRequirement, RoomRequirement, Brief, VastuTier, PlotType) + test suite skeleton (sections A, I). Register domain types in v0.7.1 enforcement.
2. **Session 2**: Setback calculator + setback_rules.json + room_minimums.json + parity tests (sections B, C partial).
3. **Session 3**: Room composer + circulation factor + auto-staircase + parking feasibility + vastu filter (sections C full, E partial, F, parking).
4. **Session 4**: Budget bridge to Component 7 + phased construction + soft-guide prioritisation + assumptions tracker (sections D, E full, G, I).
5. **Session 5**: BriefCaptureEngine orchestrator + explain() rendering + handoff tests (sections G, H).
6. **Session 6**: Form UI (HTML/JS/CSS) + API endpoint + end-to-end test.
7. **Session 7**: Packaging v0.1 release (zip, README, deploy notes).

7 sessions = realistic. Compared to Component 7's 4 months across 12+ sessions with constant scope reopening, this is disciplined.

---

## 16. Success signal (what "v0.1 done" looks like)

- All ~50 tests pass on final run
- Component 7 baseline 274 tests still green (no regression)
- End-to-end smoke test: fill form → submit → Brief produced → Brief.to_structural_grid_input() → Component 7 executes successfully
- User can save & resume via localStorage
- User sees Top 3 recommendations prominently
- User sees ASSUMPTIONS USED section in every output
- User sees correct setbacks for their plot_type
- If user opts PARTIAL vastu, they see exactly the 7 items listed (no more, no less)
- Deployable to Railway alongside Component 7

---

## 17. What I will NOT do during build

Commitments from me:

1. I will not add any item from "v0.2+ deferred" to v0.1 without explicit user approval
2. I will not skip tests to ship faster
3. I will not rewrite Component 7 to "make it fit Component 1" — if handoff breaks, I fix Component 1
4. I will not change the spec mid-build without pausing for user approval
5. I will not reopen the 10 drawbacks — they're decided, we execute

---

**End of SPEC v0.2. Ready to start Session 1: Domain Objects.**

**User confirmation required before code starts.**
