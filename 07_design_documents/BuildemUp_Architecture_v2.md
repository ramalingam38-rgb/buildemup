# BuildemUp† — Architecture v2 (Complete Component Design)

**†** = placeholder product name, marked everywhere for future global rename.
Every occurrence of `BuildemUp†` in this document must be found and replaced when we pick the final name.

---

## 0. Document purpose

This document is the complete design specification for the BuildemUp† AI floor-plan engine. It replaces the v1 architecture document after the critique round that identified three structural flaws (limited exploration space, missing furniture realism, fragmented evaluation). 

This is a design document, not code. It describes every component's purpose, inputs, outputs, internal functions, how it works step by step, and what makes it differentiated in the market. The file is meant to be read end-to-end, critiqued, and revised before any code is written.

**Status: awaiting Ramalingam's feedback. No coding until this is signed off.**

---

## 1. Example plot (used throughout this document)

Every worked example in this document uses the same real brief, so we can see the whole pipeline end-to-end on one plot.

**Plot:**
- 30 × 40 ft = 1,200 sqft
- NE-facing (road on the NE side, 30ft frontage on NE)
- Location: Chennai (warm-humid climate zone, CMDA jurisdiction)

**Ground Floor requirements:**
- 2 bedrooms, each with attached bathroom
- Living hall
- Kitchen with open dining area in the living hall, near the kitchen
- Store room
- Utility area
- Pooja room
- Guest washroom accessible from the living hall

**First Floor requirements:**
- Master bedroom with attached bath AND walk-in wardrobe
- 2 bedrooms, each with attached bathroom
- Home office
- Balcony
- Family lounge

**Terrace requirements:**
- Gym / yoga studio
- Space for garden
- Games area — table tennis, badminton if possible

**Why this is a good test case:**
- Deliberately ambitious for a 1,200 sqft plot — the engine will need Trade-off Negotiation heavily
- Badminton court (20×44 = 880 sqft) will not fit — engine must detect and negotiate
- NE-facing means morning sun on NE side; Chennai warm-humid means cross-ventilation is critical; SW afternoon sun needs protection
- 5 bedrooms + walk-in + 5 attached baths + 1 guest wash = 6 bathrooms total — wet-zone stacking becomes complex
- Multi-floor (G+1 + terrace utility) exercises vertical alignment

**Math at a glance:**
- Working envelope (2ft setbacks): 26 × 36 = 936 sqft per floor
- Regulatory envelope (CMDA 5ft front, 3ft sides/rear): 22 × 34 = 748 sqft per floor
- Chennai FAR 1.5 allows max ~1,800 sqft built
- Working G+1 = 1,872 sqft (72 over FAR — needs minor adjustment)
- Regulatory G+1 = 1,496 sqft (comfortably under FAR but tight on room count)

---

## 2. Architecture overview

### The three layers

```
LAYER 1 — UNDERSTANDING         (Components 1–4)
  Goal: solve the right problem.
  Output: validated structured brief + feasibility envelopes.

LAYER 2 — GENERATION            (Components 5–13)
  Goal: produce many valid layouts.
  Output: 60+ candidate layouts across 3 topologies.

LAYER 3 — EVALUATION + OUTPUT   (Components 14–16)
  Goal: pick the best 3, deliver them beautifully.
  Output: 3 ranked layouts + working + regulatory drawings + contractor pack.
```

### The 16 components

| # | Component | Layer | Status vs v1 |
|---|---|---|---|
| 1 | Conversational Brief | Understanding | Unchanged |
| 2 | Feasibility (×2) | Understanding | Unchanged |
| 3 | Trade-off Negotiation | Understanding | Unchanged |
| 4 | Plot Analysis | Understanding | Unchanged |
| 5 | Topology Selector | Generation | Unchanged |
| 6 | Orientation Priority | Generation | Climate-zone aware |
| 7 | Structural Grid Engine | Generation | Unchanged |
| 8 | Corridor Design | Generation | Unchanged |
| 9 | Room Sizer | Generation | **+ furniture envelope** |
| 10 | Bathroom + Wet-Zone Stack Planner | Generation | Unchanged |
| 11a | **Topology Mutation Layer** | Generation | **NEW** |
| 11b | Local NSGA-II Refinement | Generation | Renamed from 11 |
| 12 | Vertical Alignment Engine | Generation | **+ staircase alignment** |
| 13 | Door Placement | Generation | Unchanged |
| 14 | **Unified Evaluation Engine** | Evaluation | **MERGED + NEW metrics** |
| 15 | Ranker | Evaluation | Unchanged |
| 16 | Dual-Drawing Renderer | Output | **+ interactive link** |

### Two cross-cutting concerns (not components, but deliverables)

- **Contractor Defence Layer** — auto-generated document pack for the contractor
- **Resilience Layer** — graceful failure modes across every component

### The core loop (the most important diagram in the document)

```
Brief → Feasibility → Topology Selector picks 3 topologies
                          │
        For EACH topology:
                          ▼
            ┌──────────────────────────────┐
            │  Rule-based initial layout   │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ Topology Mutation (8 global) │  ← NEW
            │   → 6–8 valid global seeds   │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ Local NSGA-II Refinement     │
            │   → 30 generations, pop 50   │
            │   → Pareto-optimal survivors │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ Unified Evaluation Engine    │  ← MERGED
            │ - Graph, Spatial, Cost       │
            │ - Furniture fit (NEW)        │
            │ - Experience (NEW)           │
            │ - Problem report             │
            └──────────────┬───────────────┘
                           ▼
                  Top 3 per topology
                           │
       (9 candidates across 3 topologies)
                           ▼
                  Ranker picks final 3
                   (maximally different)
                           ▼
             Dual-drawing renderer + Contractor pack
```

---

## 3. Core design principles

These principles apply to every component. They are what makes this architecture distinctive.

**3.1 Topology-first.** We pick the topology *before* we place rooms. Topology determines how rooms relate to each other; placement is downstream. Most AI tools invert this and suffer for it.

**3.2 Structural grid before rooms.** Columns are located before any room, so walls can align with structure. Most AI tools place rooms freely and fail when a structural engineer reviews them.

**3.3 Generate many, pick the best.** Every layout shown to the user has been selected from ~60 candidates via Pareto-optimal ranking. Never the first layout we find.

**3.4 Problem list, not score.** User sees specific named problems with specific suggestions. Sub-scores exist for internal ranking, but no rolled-up number is shown.

**3.5 Explainability per component.** Every component has an `explain()` method that tells the user *why* it made the decisions it made. This is what separates BuildemUp† from a black box.

**3.6 Indian-family-specific optimisation.** Six objectives nobody else has:
1. Contractor-transparent cost in ₹
2. Pooja-room placement quality
3. Multi-generational living score
4. Bathroom-to-bedroom practicality
5. Wet-zone grouping cost efficiency
6. Tamil climate comfort (cross-vent + thermal buffering)

**3.7 Fail gracefully.** Every component has a defined failure mode that the user can understand and act on. No black-box errors.

---

## 4. LAYER 1 — Understanding

### Component 1: Conversational Brief

**Status:** Unchanged.

**Purpose:** Turn a natural conversation with the user into a structured brief the engine can use. Handle ambiguity, ask clarifying questions, detect hidden constraints.

**Inputs:** None (entry point).

**Outputs:**
- A `Brief` object containing plot dimensions, room list, hard constraints, soft preferences, budget, and inferred context

**Internal functions:**
```python
class ConversationalBrief:
    def start_conversation()
    def extract_entities(user_message)  # Claude API → structured fields
    def ask_follow_up(missing_field)    # Natural clarifying question
    def detect_hidden_constraints(text) # "parents will visit" → GF bedroom
    def confirm_brief(brief)            # Show user the JSON as plain English
    def detect_conflicts(brief)         # 3BHK in 400sqft etc.
    def save_brief(brief)               # Persist for later retrieval
    def explain()                       # "Here's how I understood you"
```

**How it works (step by step):**
1. Open with a natural greeting
2. Let the user describe their plot and wants in their own words
3. Call Claude API with a prompt that extracts plot, rooms, constraints, budget into a JSON schema
4. For any required field still missing, ask a natural follow-up (not a form)
5. Detect hidden signals: "parents visit" → GF bedroom needed; "kids" → study/play space hint; "work from home" → home office
6. Show user the extracted brief in plain English and let them correct
7. Flag internal conflicts (want X but budget/size doesn't allow) but don't solve them here — that's Component 3's job

**Worked example (NE 30×40 plot):**

```
User: "I have a 30x40 site facing NE in Chennai. On ground floor I 
       want two bedrooms with attached bathrooms, a living hall with 
       open dining near the kitchen, store room, utility, pooja, 
       and a guest washroom in the living hall. On first floor I want 
       one master bedroom with attached bath and walk-in wardrobe, 
       two more bedrooms with attached baths, a home office, balcony, 
       and family lounge. On the terrace I want a gym or yoga studio, 
       garden space, and games area for table tennis and badminton 
       if possible."

Engine extracts:
  plot:
    width: 30 ft
    depth: 40 ft  
    facing: NE
    city: Chennai
    frontage_side: NE  (inferred — 30ft on NE road)
  floors: [GF, FF, Terrace]
  rooms_gf:
    - bedroom_1 (attached_bath: true)
    - bedroom_2 (attached_bath: true)
    - living_hall
    - kitchen (open_dining: true)
    - store
    - utility
    - pooja
    - guest_wash (access: from_living)
  rooms_ff:
    - master_bedroom (attached_bath: true, walk_in: true)
    - bedroom_3 (attached_bath: true)
    - bedroom_4 (attached_bath: true)
    - home_office
    - balcony
    - family_lounge
  rooms_terrace:
    - gym_or_yoga
    - garden_space
    - games_area (items: [table_tennis, badminton_if_possible])
  inferred:
    total_bedrooms: 5
    total_baths: 6 (5 attached + 1 guest)
    dwellers_estimated: 5-7 adults (large family or multi-gen)

Engine detects potential conflict:
  "Badminton needs 20×44 ft playing area (880 sqft). Your terrace 
   usable area will be approximately 900 sqft. That's only the 
   badminton court with no room for gym, yoga, garden, or anything 
   else. Table tennis needs 15×19 (285 sqft) plus clearance — that 
   fits. Want me to propose options for the terrace?"

Engine asks:
  "One question before I proceed — what's your construction budget, 
   roughly? This affects material and finish choices."

User: "Around 60 lakhs"

Engine confirms brief, saves, passes to Feasibility.
```

**What makes it unique:** Western AI tools don't know to ask about visiting parents or flag pooja-to-toilet adjacency as a cultural issue. The brief extractor is trained specifically on Indian family vocabulary and living patterns.

---

### Component 2: Feasibility (runs twice — working + regulatory)

**Status:** Unchanged.

**Purpose:** Compute the buildable envelope using two different setback rule sets, so the user can see the cost of code compliance vs. the working reality.

**Inputs:**
- Plot dimensions, orientation, city (from Brief)

**Outputs:**
- `WorkingEnvelope` — using user's real setbacks (typically 2ft all sides)
- `RegulatoryEnvelope` — using CMDA/DTCP setbacks
- FAR allowance
- Side-by-side cost comparison of the two

**Internal functions:**
```python
class FeasibilityEngine:
    def load_city_rules(city)                    # CMDA / DTCP / other
    def compute_setbacks(plot, rule_set)
    def compute_FAR_allowance(plot, zone)
    def compute_buildable_polygon(plot, setbacks)
    def compare_envelopes(working, regulatory)   # Returns cost delta
    def flag_violations(working, regulatory)     # Where working is illegal
    def explain()                                # Plain English summary
```

**How it works:**
1. Load the regulatory rule set for the city (Chennai → CMDA CDR-2019 + 2025 amendments)
2. Apply regulatory setbacks — front/sides/rear per rule
3. Separately apply working setbacks — typically 2ft all sides
4. Compute buildable polygon for each
5. Compute FAR allowance for the zone
6. Compare: how many sqft does compliance cost? What's the material/labour delta?
7. Flag any dimension where working violates code (warn, don't block — user may still want to see)

**Worked example (NE 30×40 plot):**

```
REGULATORY ENVELOPE (CMDA 2019):
  Front (NE): 5 ft setback
  Sides (NW, SE): 3 ft setback each
  Rear (SW): 3 ft setback
  Buildable polygon: 22 × 34 ft = 748 sqft per floor
  FAR: 1.5 → max built area = 1,800 sqft
  G+1 possible: 1,496 sqft (within FAR)

WORKING ENVELOPE (user's 2ft setbacks):
  All sides: 2 ft
  Buildable polygon: 26 × 36 ft = 936 sqft per floor
  G+1: 1,872 sqft (72 sqft over FAR — needs trim to 1,800)
  
DELTA:
  Working gives 188 sqft more per floor (25% more built area)
  Estimated construction cost delta: ₹7.5L more built, but ₹7.5L more 
  asset value
  Regulatory compliance cost: approval straightforward, no scrutiny risk
  Working setbacks: approval requires neighbour NOC or regularisation

VIOLATIONS FLAGGED:
  - Working front setback (2ft) violates CMDA 5ft minimum for 
    residential on ≥20ft road — requires regularisation

PARKING REQUIREMENT (Chennai 2025 amendments):
  Plot ≤ 3,200 sqft: 2 cars + 2 two-wheelers mandatory
  Can be stilt parking (often doesn't count in FAR)
```

**What makes it unique:** Showing both envelopes side-by-side with the cost delta is the moat. Most platforms produce only one set. User sees the cost of going legal.

---

### Component 3: Trade-off Negotiation

**Status:** Unchanged (but heavily exercised by this example brief).

**Purpose:** When the brief has internal conflicts, surface them in plain English and propose options. Never silently override the user.

**Inputs:**
- Brief (from Component 1)
- Both envelopes (from Component 2)

**Outputs:**
- List of `Conflict` objects, each with: description, options (2–4), recommendation, estimated cost/space impact
- Revised brief (after user chooses)

**Internal functions:**
```python
class TradeOffNegotiator:
    def detect_conflicts(brief, envelope)
    def propose_options(conflict)          # 2-4 paths forward
    def estimate_impact(option)            # cost + sqft + quality
    def rank_options(options)              # Recommendation ordering
    def present_to_user(conflicts)         # Plain English UI
    def apply_user_choice(brief, choices)  # Revise brief
    def explain()
```

**How it works:**
1. Run room-by-room space accounting: sum minimum sqft for every requested room
2. Compare against buildable envelope × floors
3. For each conflict, generate 2–4 alternative options
4. Estimate cost and quality impact of each option
5. Present to user, wait for choice, revise brief

**Worked example (NE 30×40 plot):**

```
CONFLICT 1: Terrace badminton won't fit
  Badminton needs 20×44 = 880 sqft including run-off
  Terrace usable area: ~900 sqft
  If badminton, no room for anything else on terrace
  
  Options:
  A) Drop badminton. Keep gym+yoga+garden+table tennis. (recommended)
  B) Shrink badminton to half-court (still impractical).
  C) Use terrace only for badminton. No gym/garden/TT on terrace.
  D) Keep badminton aspiration as future expansion if neighbour plot 
     is combined.

CONFLICT 2: Room count vs. floor area (ground floor)
  Requested GF rooms + minimum areas:
    Living (180) + Kitchen (80) + Dining-open (shared) + BR1 (110) + 
    Bath1 (30) + BR2 (110) + Bath2 (30) + Pooja (30) + Store (40) + 
    Utility (40) + GuestWash (20) + Staircase (60) + Entry/Corridor (40)
    Total: ~770 sqft
  Regulatory envelope GF: 748 sqft
  Working envelope GF: 936 sqft
  
  Options:
  A) Use working envelope (2ft setbacks) — requires CMDA 
     regularisation but fits with 160 sqft to spare. (recommended)
  B) Use regulatory envelope — need to trim 22 sqft; suggest 
     smaller store (30 instead of 40) + smaller utility (30 instead 
     of 40), + absorb guest wash into bathroom 2 space.
  C) Use regulatory envelope — drop GuestWash, shared one on FF. 
     (not recommended — user specifically wants guest wash on GF.)

CONFLICT 3: Walk-in wardrobe on FF is tight
  MBR (150) + walk-in (40) + MBR bath (35) + BR3 (110) + Bath3 (30) + 
  BR4 (110) + Bath4 (30) + Home office (100) + Family lounge (120) + 
  Balcony (60) + Staircase (60) + Corridor (40)
  Total: ~885 sqft
  Working envelope FF: 936 sqft (tight but fits, 51 sqft margin)
  Regulatory envelope FF: 748 sqft (doesn't fit by 137 sqft)
  
  Same as conflict 2 — working envelope recommended.

CONFLICT 4: Parking not mentioned in brief
  CMDA 2025 requires 2 cars + 2 two-wheelers parking.
  Options:
  A) Stilt parking under GF (reduces FAR usage, increases total 
     project height). Recommended.
  B) Open compound parking at front setback (often insufficient area).
  C) Reduce to 1 car + 2 two-wheelers and apply for variance.

USER RECOMMENDED PATH:
  Accept 1A, 2A, 4A. This means:
  - Use working envelope with CMDA regularisation
  - Stilt parking → actual structure becomes Stilt + G + 1 + Terrace
  - All rooms fit with reasonable margin
  - Drop terrace badminton, keep gym+yoga+garden+table tennis
```

**What makes it unique:** Most tools error out on infeasible briefs. We negotiate. This is enormous for consumer trust — the user feels heard, not blocked.

---

### Component 4: Plot Analysis

**Status:** Unchanged.

**Purpose:** Classify the plot, detect special features (corner, sloped, setback-sensitive), and set the quality tier expectation.

**Inputs:** Revised brief + envelopes.

**Outputs:**
- `PlotAnalysis` with: tier (T1/T2/T3), shape classification, corner status, orientation details, climate zone, soil estimate, road width, neighbour context

**Internal functions:**
```python
class PlotAnalyzer:
    def classify_tier(sqft)              # T1 600-2400, T2 2400-4000, T3 4000+
    def detect_shape(plot)               # rectangular, L-shaped, irregular
    def detect_corner_status(plot)       # corner / middle
    def compute_sun_path(lat, lng)       # annual solar exposure on each face
    def load_climate_zone(city)          # NBC 5 zones
    def estimate_soil(city, area)        # for foundation cost estimate
    def check_road_width(plot)           # affects setback calc + parking
    def explain()
```

**Worked example (NE 30×40 plot):**
```
PLOT ANALYSIS:
  Tier: T1 (600-2400 sqft — fully supported range)
  Shape: Rectangular (30×40)
  Corner: No (assumed middle plot with NE road only)
  Orientation: NE-facing (main road on NE side)
  Climate zone (NBC): Warm-humid (Chennai)
  Sun path:
    NE wall: morning sun 6-10 AM (gentle, OK for bedrooms/living)
    SE wall: late morning sun (moderate)
    SW wall: afternoon sun 2-6 PM (HARSH — protect or use for utility)
    NW wall: evening sun (minimal in summer)
  Soil estimate: Clay-rich, bearing capacity 10-12 T/sqm typical Chennai 
                 → standard isolated footing OK
  Road width: Not specified by user — ASK (affects setback rule tier 
              in CMDA)
```

**What makes it unique:** Climate zone mapping (NBC 5 zones) drives downstream orientation choices; this is typically hard-coded or ignored in Western tools.

---

## 5. LAYER 2 — Generation

### Component 5: Topology Selector

**Status:** Unchanged.

**Purpose:** Pick 2–3 of the 5 topologies most likely to succeed on this plot + brief. Each will be carried through the rest of the pipeline in parallel.

**Inputs:** Plot envelope, room list, orientation.

**Outputs:** List of 2–3 `TopologySelection` objects with fit scores.

**Internal functions:**
```python
class TopologySelector:
    def score_no_corridor(plot, rooms)
    def score_strip(plot, rooms)
    def score_central_spine(plot, rooms)
    def score_l_shape(plot, rooms, corner_status)
    def score_courtyard(plot, rooms)
    def check_hard_requirements(topology, plot)
    def select_top_k(scores, k=3)
    def explain()
```

**Worked example (NE 30×40 plot):**
```
Plot: 26×36 working envelope
Room count: 13 GF + 11 FF + terrace

Scores:
  No-corridor: REJECT (width 30ft > 18ft threshold AND room count 
                       too high)
  Strip: 4/10 (depth/width ratio 1.2 is below ideal 2.0+; single-
                loaded corridor wastes area with this many rooms)
  Central spine: 8/10 (26ft width allows 4ft corridor + 11ft rooms each 
                        side; 13 rooms GF fit with 4 on each side of 
                        corridor plus staircase)
  L-shape: 3/10 (not a corner plot; L-shape better for corner plots 
                  with two-street access)
  Courtyard: 6/10 (1200 sqft plot is borderline for courtyard; 
                    warm-humid climate favours courtyard for 
                    ventilation; small courtyard 6x8 possible)

Selected:
  Primary: Central Spine (8/10)
  Secondary: Courtyard (6/10)  
  Tertiary: Strip (4/10)

All three will go through the full generation loop. May the best plan win.
```

**What makes it unique:** Explicit topology naming + multi-topology parallel exploration. Most AI tools are topology-agnostic.

---

### Component 6: Orientation Priority (climate-zone aware)

**Status:** Changed — now keyed on NBC climate zone, not hard-coded to Bangalore.

**Purpose:** Given plot orientation and climate zone, produce a preference table for where each room type should ideally go (N, S, E, W, NE, NW, SE, SW).

**Inputs:** Plot orientation, climate zone from Component 4.

**Outputs:** `OrientationPreferences` — a table mapping room type → preferred wall/corner.

**Internal functions:**
```python
class OrientationPreference:
    def load_climate_rules(zone)              # NBC 5 zones: hot-dry, 
                                              # warm-humid, moderate, 
                                              # cold, composite
    def compute_preferences(orientation, zone, room_types)
    def get_ideal_position(room_type)         # Returns ranked list
    def get_avoid_position(room_type)         # Returns rooms that SHOULDN'T 
                                              # go here
    def explain()
```

**How it works:**
1. Load climate rules (Chennai = warm-humid → emphasise cross-ventilation, shade SW, use NE for morning-facing rooms)
2. Build preference table: every room type has a ranked list of preferred orientations
3. The placement engine uses this as a scoring input, not a hard rule

**Worked example (NE 30×40, Chennai warm-humid):**
```
CLIMATE RULES APPLIED:
  Long axis preference: N-S (minimises E-W solar load)
  SW exposure: minimise (utility/service/garage/store preferred)
  NE/N: maximise (morning sun good for bedrooms, living)
  Cross-ventilation axis: E-W (prevailing sea breeze from E in Chennai)
  Courtyard benefit: HIGH (warm-humid cooling mechanism)

ROOM PREFERENCES (ranked for NE-facing 30×40 in Chennai):
  Living hall:       NE (1st) > N (2nd) > E (3rd)
  Kitchen:           NE (1st) > N (2nd) > E (3rd) — good morning light
                     Avoid SW (heat + fire risk combo)
  Pooja:             NE (1st) > E (2nd) — traditional + morning sun
  Master bedroom:    S or SW preferred IF shaded
                     W acceptable IF protected
                     Avoid: direct NE (too much guest traffic)
  Kids bedrooms:     E (morning light for studies) > NE > N
  Guest wash:        central or W side (service zone)
  Utility:           SW (1st) — thermal buffer against afternoon sun
  Store:             SW (1st) or W (2nd) — no natural light needed
  Staircase:         Center or W side
  Home office:       N or NE (glare-free light for screens)
  Family lounge:     NW or N (afternoon/evening gathering)
  Balcony:           NE or N (morning sun, cooler evenings)
  Terrace garden:    SE or E (morning sun, shade by noon)
  Gym/yoga:          NE or E (morning light; cross-vent important)
```

**What makes it unique:** Five-zone NBC climate awareness + Tamil-specific rules (Chennai prevailing E breeze). Western tools don't have this at all.

---

### Component 7: Structural Grid Engine

**Status:** Unchanged from v1. Foundational component — blocks everything downstream until it runs.

**Purpose:** Decide where columns go BEFORE any room is placed. Rooms will then be sized as multiples of the grid.

**Inputs:** Buildable envelope, floor count, soil data.

**Outputs:** `StructuralGrid` — 2D array of column positions, beam spans, foundation type.

**Internal functions:**
```python
class StructuralGridEngine:
    def compute_optimal_grid(envelope, floors)        # Devdas Menon method
    def validate_span(grid)                           # ≤ 4.5m RCC residential
    def align_with_setbacks(grid, envelope)           # Perimeter cols on setback line
    def propagate_to_upper_floors(grid)               # Vertical stacking
    def select_foundation_type(soil, grid)            # Isolated / combined / raft
    def estimate_concrete_steel(grid, floors)         # Back-of-envelope BOQ
    def explain()
```

**How it works:**
1. Given envelope and floors, compute optimal column spacing using parametric grid method (shorter spans = smaller beams + more cols; longer spans = fewer cols but deeper beams)
2. For G+1+terrace residential, optimal grid is typically 3.0–3.7m
3. Align perimeter columns with setback lines
4. Validate: all spans ≤ 4.5m for RCC economy
5. Propagate to upper floors — column grid must be identical (no offsets)
6. Select foundation type based on soil (Chennai clay → isolated footing typical)

**Worked example (NE 30×40, working envelope 26×36):**
```
ENVELOPE: 7.92m × 10.97m
FLOORS: Stilt (parking) + G + 1 + Terrace = 3 structural floors
OPTIMAL GRID: 3.0m × 3.65m

Column positions (meters from NE corner):
  Row 0 (NE edge):     (0, 0), (3.0, 0), (6.0, 0), (7.92, 0)
  Row 1:               (0, 3.65), (3.0, 3.65), (6.0, 3.65), (7.92, 3.65)
  Row 2:               (0, 7.30), (3.0, 7.30), (6.0, 7.30), (7.92, 7.30)
  Row 3 (SW edge):     (0, 10.97), (3.0, 10.97), (6.0, 10.97), (7.92, 10.97)

Total columns: 16 (4×4 grid)
Max span: 3.65m (well below 4.5m RCC economy limit)
Foundation: Isolated footings, 1.5m × 1.5m × 0.3m each
Rough quantities:
  Concrete: ~55 cum (foundation + columns + beams + slab for 3 floors)
  Steel: ~5.5 tonnes
  Estimated structural cost (Chennai 2026 rates): ₹22L

VERTICAL PROPAGATION:
  Every floor uses identical 4×4 grid.
  Columns must stack perfectly — no offsets allowed.
  This constrains where staircases, walls, and wet areas can go.
```

**What makes it unique:** Running structural grid BEFORE rooms. 95% of AI tools do this after room layout (or skip it), producing plans that structural engineers reject.

---

### Component 8: Corridor Design

**Status:** Unchanged from v1.

**Purpose:** Given topology and grid, design the circulation corridor. Corridor is reserved before rooms are placed.

**Inputs:** Topology (from 5), Structural Grid (from 7), orientation preferences (from 6).

**Outputs:** `CorridorPath` — polyline showing corridor route, width, entry-exit points, passage-door rules.

**Internal functions:**
```python
class CorridorDesigner:
    def design_no_corridor(envelope, rooms)
    def design_strip(envelope, grid)
    def design_central_spine(envelope, grid)
    def design_l_shape(envelope, grid)
    def design_courtyard(envelope, grid)
    def validate_min_width(corridor)              # NBC: 0.9m interior residential
    def generate_passage_doors(corridor, rooms)   # P1-P5 logic from earlier
    def explain()
```

**Worked example (NE 30×40, Central Spine topology):**
```
TOPOLOGY: Central Spine (double-loaded corridor)
GRID: 4×4 cols at 3.0 × 3.65m

Corridor design:
  Runs N-S (aligned with grid row 2, from NE to SW)
  Width: 1.2m (4 ft) — above NBC minimum 0.9m
  Length: 10.97m
  Entry: from main door on NE facade
  Vertical connector: staircase at center (between cols [1,1] and [2,2])
  
Passage door rules:
  Main entry: 1.0m double door (luxury feel)
  Room-to-corridor: 0.8m single door each
  No direct door from corridor to bathroom (privacy)
  Kitchen has 0.9m door + pass-through window to dining
```

---

### Component 9: Room Sizer (with furniture envelope) [CHANGED]

**Status:** Changed — now uses furniture-fit as the lower bound, not just NBC minimum.

**Purpose:** Assign a minimum and target size to every room, based on NBC + actual furniture + clearance requirements.

**Inputs:** Room list, buildable envelope, grid.

**Outputs:** `RoomSizeTable` — min/target/max sqft for each room.

**Internal functions:**
```python
class RoomSizer:
    def load_nbc_minimums(room_type)
    def load_furniture_envelope(room_type)       # Neufert-based
    def compute_min_size(room_type)              # max(nbc_min, furniture_min)
    def compute_target_size(room_type, budget)
    def compute_max_size(room_type)              # Prevents wasteful oversize
    def allocate_remaining_area(rooms, envelope) # Distribute leftover sqft
    def explain()
```

**Furniture envelope examples (the NEW part):**
```
MASTER BEDROOM (user wants walk-in wardrobe):
  Required furniture:
    - Queen bed 5 × 6.5 ft = 32.5 sqft
    - Side tables 2 × (1.5 × 1.5) = 4.5 sqft
    - Wardrobe entry to walk-in: 3 × 2 ft access
  Clearance:
    - 3 ft at foot of bed
    - 2.5 ft at sides of bed
    - 4 ft in walk-in (both sides + walking)
  NBC min: 9.5 sqm = 102 sqft
  Furniture min (this configuration): 140 sqft
  FINAL MIN: 140 sqft (walk-in separately accounted at 40 sqft)

KIDS BEDROOM:
  Required: Single bed 3 × 6.5 + study table 4 × 2 + wardrobe 4 × 2
  Clearance: 2.5 ft around bed, 2 ft at study
  NBC min: 7.5 sqm = 80 sqft
  Furniture min: 100 sqft
  FINAL MIN: 100 sqft

KITCHEN (open to dining):
  Required: L or U counter 10 ft run + fridge 2.5 ft + prep 4 ft
  Clearance: 4 ft working aisle between counter and island/opposite wall
  NBC min: 5 sqm = 54 sqft
  Furniture min: 85 sqft (for L-shape with island)
  FINAL MIN: 85 sqft

POOJA ROOM:
  Required: Altar 2 × 3 + seated prayer 4 × 4 + storage cabinet
  Clearance: open front, 2 ft around altar
  NBC min: none (not a habitable room)
  Furniture min: 30 sqft
  FINAL MIN: 30 sqft
```

**Worked example (NE 30×40 complete sizing):**
```
GROUND FLOOR (target working envelope 936 sqft):
  Living hall:    min 180, target 200
  Kitchen:        min 85,  target 100 (incl. open dining portion)
  Dining (open):  shared with living — no separate sqft
  BR1:           min 100, target 110
  Bath1:         min 30,  target 35
  BR2:           min 100, target 110  
  Bath2:         min 30,  target 35
  Pooja:         min 30,  target 35
  Store:         min 30,  target 40
  Utility:       min 30,  target 40
  Guest wash:    min 18,  target 22
  Staircase:     60 (fixed)
  Entry/corridor:40 (fixed)
  TOTAL min:     733 sqft  (fits in 936 with 203 sqft slack)
  TOTAL target:  827 sqft  (fits in 936 with 109 sqft slack)

FIRST FLOOR (target 936 sqft):
  MBR:           min 140, target 160
  Walk-in:       min 40,  target 50
  MBR bath:      min 35,  target 45
  BR3:           min 100, target 110
  Bath3:         min 30,  target 35
  BR4:           min 100, target 110
  Bath4:         min 30,  target 35
  Home office:   min 85,  target 100
  Family lounge: min 120, target 140
  Balcony:       min 50,  target 70
  Staircase:     60 (fixed)
  Corridor:      40 (fixed)
  TOTAL min:     830 sqft  (fits in 936 with 106 sqft slack)
  TOTAL target:  955 sqft  (over by 19 sqft — reduce lounge to 121 
                            or MBR to 141)
```

**What makes it unique:** Furniture-fit as the minimum, not NBC. NBC says bedroom can be 80 sqft; we say if you want a queen bed and wardrobe to actually fit, it's 100. This is what saves users from unlivable "compliant" plans.

---

### Component 10: Bathroom + Wet-Zone Stack Planner

**Status:** Unchanged from v1.

**Purpose:** Group all wet areas (bathrooms, kitchen, utility) along vertical stacks to minimise plumbing runs and enable clean multi-floor alignment.

**Inputs:** Room sizes, grid, orientation.

**Outputs:** `WetZonePlan` — designated wet walls, stack positions, chase widths, vertical alignment targets.

**Internal functions:**
```python
class WetZonePlanner:
    def identify_wet_rooms(rooms)
    def design_wet_walls(wet_rooms, grid)         # Cluster along shared walls
    def plan_vertical_stacks(wet_walls, floors)   # Align floor-to-floor
    def size_chases(stacks)                       # Per pipe count
    def minimise_horizontal_runs(layout)          # IPC 10ft shower max
    def estimate_plumbing_cost(stacks, length)
    def explain()
```

**Worked example (NE 30×40):**
```
WET ROOMS:
  GF: Bath1, Bath2, GuestWash, Kitchen, Utility (5 wet rooms)
  FF: MBR bath, Bath3, Bath4 (3 wet rooms)

WET WALL DESIGN (Central Spine topology):
  Primary wet wall: runs N-S, 1 grid east of center
  - Bath1 (GF) stacks with Bath3 (FF) — shared wall
  - Bath2 (GF) stacks with Bath4 (FF) — shared wall
  - Guest wash (GF) stacks with MBR bath (FF) — shared wall (BUT mbr 
    bath is typically larger; needs wider chase)
  
  Secondary wet wall: runs E-W, SW quadrant
  - Kitchen (GF) sink wall
  - Utility (GF) washing machine area
  (No FF counterpart — OK, terminates at GF ceiling with vent)

CHASES:
  Main stack chase: 8" wide × 10" deep, runs full height
  Branch chases per bathroom: 6" × 8"
  Kitchen+utility chase: 6" × 8", terminates above GF ceiling

HORIZONTAL RUNS:
  Max shower-to-stack distance: 2.5 m (well under IPC 10ft limit)

ESTIMATED PLUMBING COST (Chennai 2026 rates):
  Aligned stacks (this plan): ₹2.8L
  If bathrooms NOT aligned: ₹3.8L (+₹1L)
  Savings from stack discipline: ₹1L = ~30% of plumbing scope
```

---

### Component 11a: Topology Mutation Layer [NEW]

**Status:** NEW. This is the most important addition in v2.

**Purpose:** Before local NSGA-II refinement, explore globally different structural variants. This is what addresses the "limited exploration space" flaw.

**Inputs:** One rule-based starting layout per topology (from the base placement logic).

**Outputs:** 6–8 globally-mutated valid layouts per topology, which then each feed into local NSGA-II.

**The 8 global mutation operators:**

1. **Horizontal flip (E↔W)** — mirror the plan left-to-right
2. **Vertical flip (N↔S)** — mirror front-to-back (public↔private zones swap)
3. **Staircase relocation** — center / east wall / west wall / corner (4 positions)
4. **Corridor inversion** — central to edge, or vice versa
5. **Public/private zone swap** — reverse which zone is at the front
6. **Wet-wall rotation (90°)** — N/S/E/W variants
7. **Grid scaling** — try 3.0m / 3.3m / 3.6m column spacing
8. **Vertical rearrangement** — which rooms on GF vs FF (e.g., master on GF vs FF)

**Internal functions:**
```python
class TopologyMutator:
    def mutate_all(base_layout)                    # Returns 8-12 seeds
    def horizontal_flip(layout)
    def vertical_flip(layout)
    def relocate_staircase(layout, position)       # 4 positions
    def invert_corridor(layout)
    def swap_zones(layout)
    def rotate_wet_wall(layout, target_wall)       # N/S/E/W
    def scale_grid(layout, target_grid_m)          # 3.0, 3.3, 3.6
    def rearrange_floors(layout, assignment)       # Master GF vs FF
    def filter_invalid(mutations)                  # Drop hard-constraint 
                                                   # violations
    def explain()
```

**How it works:**
1. Take the rule-based initial layout for this topology
2. Apply each of the 8 mutation operators (some produce multiple variants)
3. Filter out mutations that violate hard constraints (user's explicit requirements, NBC, structural)
4. Return 6–8 valid seeds
5. Each seed then goes into local NSGA-II

**Worked example (NE 30×40, Central Spine topology):**
```
BASE LAYOUT:
  Staircase: center (between grid rows 1-2)
  Corridor: N-S central
  Public zone: NE (living at entrance)
  Private zone: SW (bedrooms at back)
  Wet wall: west side (between grid cols 1-2)
  Grid: 3.0m × 3.65m
  Master on FF (per user brief)

MUTATIONS GENERATED:
  M1: Horizontal flip (E↔W)
      → Staircase still center, but wet wall moves to EAST side
      → Kitchen moves from NW to NE corner (near entry)
      → VALID; proceeds
  
  M2: Vertical flip (N↔S)
      → Public zone to SW (back), private to NE (front, near entry)
      → Bedrooms face road; violates privacy
      → INVALID; rejected
  
  M3a: Staircase to east wall
      → Frees up center for larger living
      → But crowds east-side bathroom stack
      → VALID with reduced bath2 size; proceeds
  
  M3b: Staircase to west wall
      → Mirror of M3a
      → VALID; proceeds
  
  M3c: Staircase at NE corner
      → Awkward entry flow (stair visible from front door)
      → VALID but low quality; proceeds (let NSGA-II judge)
  
  M4: Corridor inversion (central → edge)
      → Corridor against east wall
      → All rooms open to west side
      → Reduces cross-ventilation (Chennai warm-humid penalty)
      → VALID with climate penalty; proceeds
  
  M5: Zone swap
      → Same as M2; INVALID
  
  M6: Wet wall rotation (west → south)
      → Kitchen moves to south, bathrooms to south wall
      → Afternoon sun heats bathrooms (unpleasant)
      → VALID with climate penalty; proceeds
  
  M7a: Grid scaled to 3.3m
      → Slightly larger rooms, but total envelope fixed
      → Might exceed FAR; recalculate
      → VALID with adjusted sizes; proceeds
  
  M7b: Grid scaled to 2.7m
      → Smaller rooms, but furniture fit becomes tight
      → Some rooms fall below furniture min
      → INVALID; rejected
  
  M8: Vertical rearrangement (master on GF)
      → User brief explicitly wants master on FF
      → INVALID; rejected

VALID SEEDS PROCEEDING TO NSGA-II:
  Base, M1, M3a, M3b, M3c, M4, M6, M7a
  → 8 seeds
```

**What makes it unique:** Nobody else does this. It's the single biggest quality improvement in the architecture. Without it, we explore 30 layouts total; with it, 60+.

---

### Component 11b: Local NSGA-II Refinement

**Status:** Renamed from "Placement Engine" v1. This is the local optimisation that runs on each mutated seed from 11a.

**Purpose:** Fine-tune each seed through 30 generations of NSGA-II genetic algorithm, producing Pareto-optimal variants.

**Inputs:** 6–8 globally-mutated seed layouts per topology.

**Outputs:** 3–5 Pareto-optimal variants per seed → ~20–40 variants per topology → ~60–120 total across 3 topologies.

**Internal functions:**
```python
class NSGAIIRefiner:
    def setup_problem(seed, objectives)              # Pymoo Problem class
    def define_objectives()                          # The 6 Indian objectives
    def local_perturbation(layout)                   # Shift wall 1 grid, swap, etc.
    def crossover(parent_a, parent_b)                # Merge layouts
    def mutation(layout, probability)
    def evaluate(population)                         # Score all on 6 objectives
    def run_generations(n=30, pop_size=50)
    def extract_pareto_front(final_population)
    def explain()
```

**The 6 objectives (minimise each, except quality which we maximise):**

1. **Cost** (₹, minimise) — actual material + labour cost using city rates
2. **Pooja placement quality** (0-10, maximise) — NE/E position, not adjacent to toilet, ventilated, size adequate
3. **Multi-generational score** (0-10, maximise) — GF bedroom exists, bathroom accessible without stairs, ramp-friendly entry
4. **Bathroom-to-bedroom practicality** (0-10, maximise) — every bedroom has bath access without crossing public space
5. **Wet-zone efficiency** (₹, minimise) — total plumbing cost given stack alignment
6. **Tamil climate comfort** (0-10, maximise) — cross-vent path exists, SW shaded, NE morning sun to living

**How Pareto filtering works:**

For two variants A and B:
- A *dominates* B if A is at least as good on every objective AND strictly better on at least one
- Variants that are not dominated by any other are "Pareto-optimal"
- We keep only these

**Worked example (NE 30×40, 8 seeds → NSGA-II):**
```
SEED M1 (horizontal flip):
  Generation 0 (initial population of 50, variations of M1):
    Pop member     Cost(L)  Pooja  MultiGen  BathPrac  WetCost(L)  Climate
    M1-base        42.5     8      7         9         2.8         8
    M1-v1          42.4     8      7         9         2.9         8
    M1-v2          42.7     9      7         9         2.8         8
    M1-v3          42.3     8      7         10        2.7         8
    M1-v4          43.0     7      8         9         2.8         9
    ... (46 more)
  
  After 30 generations, Pareto front (5 variants):
    Best-cost:     41.9L cost, 8 pooja, 7 multigen, 9 bathprac, 2.7 wet, 8 climate
    Best-pooja:    42.4L cost, 10 pooja, 7 multigen, 9 bathprac, 2.8 wet, 8 climate
    Best-multigen: 42.5L cost, 8 pooja, 9 multigen, 10 bathprac, 2.8 wet, 8 climate
    Best-climate:  42.8L cost, 8 pooja, 7 multigen, 9 bathprac, 2.8 wet, 10 climate
    Balanced:      42.3L cost, 9 pooja, 8 multigen, 10 bathprac, 2.8 wet, 9 climate

  (Variants that were dominated — e.g., 42.7L cost with 7 pooja — 
   dropped because some other variant beats them on everything.)

REPEAT FOR EACH SEED:
  M1 → 5 Pareto-optimal variants
  M3a → 4 variants
  M3b → 4 variants
  M3c → 2 variants (low quality, mostly dominated)
  M4 → 3 variants
  M6 → 3 variants
  M7a → 5 variants
  Base → 5 variants
  TOTAL: 31 variants across this one topology

REPEAT FOR COURTYARD TOPOLOGY: +25 variants
REPEAT FOR STRIP TOPOLOGY: +18 variants

GRAND TOTAL: 74 Pareto-optimal variants across 3 topologies.
These go to the Unified Evaluation Engine for full scoring and ranking.
```

---

### Component 12: Vertical Alignment Engine [CHANGED]

**Status:** Changed — now aligns columns, bathrooms, stacks, AND staircases across floors (was only bathrooms + columns in v1).

**Purpose:** Ensure multi-floor integrity — what's on GF must support what's on FF, and what stacks must stack cleanly.

**Inputs:** All per-floor layouts.

**Outputs:** Aligned multi-floor layout, or list of alignment violations that force redesign.

**Internal functions:**
```python
class VerticalAlignmentEngine:
    def check_column_alignment(gf, ff, terrace)       # Must stack perfectly
    def check_bathroom_alignment(gf, ff)              # Wet stack integrity
    def check_staircase_alignment(gf, ff)             # Physical continuity
    def check_plumbing_stacks(wet_zones)
    def detect_load_path_violations(gf_walls, ff_walls)  # Beam transfer risk
    def suggest_corrections(violations)
    def explain()
```

**Worked example (NE 30×40):**
```
ALIGNMENT CHECK:
  Columns: GF=16, FF=16, Terrace-supporting=16 ✓ 
           All at identical positions ✓
  
  Bathrooms:
    GF Bath1 center: (4.5m, 8.0m) — aligned with FF Bath3 center: (4.5m, 8.0m) ✓
    GF Bath2 center: (7.5m, 8.0m) — aligned with FF Bath4 center: (7.5m, 8.0m) ✓
    GF Guest wash: (1.5m, 5.0m) — FF MBR bath: (1.5m, 5.0m) ✓
    (MBR bath is 45 sqft; guest wash is 22 sqft; chase sized for MBR.)
  
  Staircase: 
    GF position: (4.5m, 5.5m) to (6.0m, 8.0m)
    FF position: (4.5m, 5.5m) to (6.0m, 8.0m) ✓ identical
    Terrace access: staircase continues to reach terrace ✓
  
  Plumbing stacks:
    Main stack: runs vertically through west wet wall ✓
    Branch alignment: all bathroom drains connect within 2m horizontal ✓
    Kitchen + utility: local stack, terminates at GF slab ceiling ✓
  
  Load path:
    All FF interior walls land on either GF column or GF beam ✓
    Exception: FF family lounge east wall cantilevers 0.5m beyond GF 
    living east wall → needs beam transfer
    → FIX: either move family lounge wall to align, OR add transfer beam 
    (₹35K cost). Tool recommends alignment.

NO ALIGNMENT VIOLATIONS REMAIN.
```

---

### Component 13: Door Placement

**Status:** Unchanged.

**Purpose:** Place doors in each wall with correct swing direction, clearance, and privacy considerations.

**Inputs:** Final layout + corridor + wet-zone plan.

**Outputs:** `DoorSchedule` — list of doors with type, width, swing direction, threshold.

**Internal functions:**
```python
class DoorPlacer:
    def assign_door_types(rooms)                  # Main, internal, service
    def place_door_position(room, wall)           # Corner vs center
    def compute_swing_direction(room, corridor)   # Into room typically
    def check_clearance(door, furniture)          # 0.9m swing arc free
    def check_privacy_line_of_sight(door, layout) # No bedroom visible from entry
    def generate_door_schedule()
    def explain()
```

---

## 6. LAYER 3 — Evaluation + Output

### Component 14: Unified Evaluation Engine [MERGED + NEW metrics]

**Status:** MAJOR CHANGE. Merged from v1 components 14, 15, 16 (connection graph, problem finder, fast subset) into one engine. NEW: furniture-fit metrics, experience metrics.

**Purpose:** Take any layout and produce complete evaluation: graph metrics, spatial metrics, cost metrics, furniture-fit metrics, experience metrics, problem report.

**Inputs:** A single layout + brief + climate zone + city cost table.

**Outputs:** 
- `EvaluationReport` with category sub-scores (used for ranking)
- `ProblemReport` with categorised problem list (shown to user)

**The six evaluation categories:**

**14.1 Graph metrics** — adjacency and circulation
```python
def compute_graph_metrics(layout):
    - build adjacency graph (rooms = nodes, doors = edges)
    - compute BFS step-depth from entry to every room
    - compute betweenness centrality (which rooms are crossing points?)
    - compute isovist from key standing positions
    - detect privacy-gradient violations (step-depth monotonicity)
```

**14.2 Spatial metrics** — geometry quality
```python
def compute_spatial_metrics(layout):
    - compute total wasted area (unassigned + awkward corners)
    - detect dead-space L-corners (<15 sqft, no function)
    - check corridor width at every segment (≥0.9m NBC, ≥1.2m target)
    - compute floor-area ratio used vs allowed
    - check room aspect ratios (bedrooms ideally 1:1.2 to 1:1.5)
```

**14.3 Cost metrics** — real ₹ using city rates
```python
def compute_cost_metrics(layout, city):
    - compute built-up area per floor
    - apply Chennai 2026 rates: civil ₹1800-2400/sqft depending on spec
    - compute plumbing cost based on wet-zone alignment
    - compute electrical cost based on room count + complexity
    - compute finishing cost based on user-specified spec tier
    - add contractor margin (visible line, typically 12-18%)
    - return: total, per-floor, per-category breakdown
```

**14.4 Furniture-fit metrics [NEW]** — can real furniture actually fit?
```python
def compute_furniture_fit(layout):
    for each room:
        load standard furniture set for that room type
        run 2D packing to place furniture with clearances
        if doesn't fit: flag with specific reason 
            ("wardrobe needs 2ft depth — available wall is 1.8ft")
        if fits marginally: flag tight clearance
            ("bed-to-wardrobe clearance is 2ft; Neufert recommends 2.5ft")
        return furniture layout drawing + issue list
```

**14.5 Experience metrics [NEW]** — perceptual qualities
```python
def compute_experience_metrics(layout):
    - entry reveal: isovist from 2ft inside front door
    - visual openness: average isovist area in public zone
    - privacy gradient: step-depth monotonicity public→private
    - awkward-space count (L-corners, narrow strips)
    - threshold quality: every room-to-room transition has proper door/opening
    - ceiling-height opportunities: where can we do double-height or vault?
```

**14.6 Problem report generation**
```python
def generate_problem_report(evaluations):
    # Categorises ALL issues from 14.1-14.5 into user-facing categories:
    categories = [
        "WASTED SPACE",
        "ROOM SIZES",
        "FLOW",
        "LIGHT",
        "PRIVACY",
        "FURNITURE FIT",
        "EXPERIENCE",
        "COST",
        "CODE COMPLIANCE"
    ]
    # Output is a categorised list, NOT a single score.
```

**Worked example — Problem Report for one final layout (NE 30×40, Layout 1):**
```
╔══════════════════════════════════════════════════════════════╗
║   LAYOUT 1 — Central Spine — Optimised for multigen + cost   ║
║   Estimated cost: ₹58.2L (including 15% contractor margin)   ║
╚══════════════════════════════════════════════════════════════╝

✓ WASTED SPACE                              [PASS]
  No dead corners or orphan areas detected.

⚠ ROOM SIZES                                [1 issue]
  • Bath2 is 30 sqft (NBC minimum). Target was 35 sqft.
    Reason: absorbed 5 sqft by BR2 to improve furniture fit.
    Action: accept, or reduce BR2 by 5 sqft to restore bath.

✓ FLOW                                      [PASS]
  All rooms within 4 steps of entry.
  No bottleneck corridors (min width 1.2m everywhere).

⚠ LIGHT                                     [1 issue]
  • Guest wash has no external window.
    Reason: interior position (wet-stack priority).
    Action: add mechanical exhaust + LED daylight fixture.

⚠ PRIVACY                                   [1 issue]
  • BR1 door partially visible from main entrance 
    (15ft line of sight through corridor).
    Action: add 3ft privacy screen near entry foyer 
    (₹12,000 additional).

✓ FURNITURE FIT                             [PASS all 11 rooms]
  Standard furniture fits with Neufert clearances in every room.

⚠ EXPERIENCE                                [1 issue]
  • Entry reveal score: 6/10. Door opens toward staircase railing 
    directly. 
    Suggestion: staircase 2ft east (tested as Layout 2 variant); 
    or, accept and add feature wall behind staircase.

✓ COST                                      [within budget]
  ₹58.2L vs ₹60L budget.
  Contractor margin line: ₹7.6L (visible).

✓ CODE COMPLIANCE                           [PASS]
  NBC 2016, IS 456, IS 875, CMDA 2019 + 2025 amendments all 
  satisfied on working envelope with 2ft setbacks.
  Note: working setbacks require CMDA regularisation.

SUMMARY: 4 issues to review across 9 categories. 
         No blockers.
```

**What makes it unique:**
1. Problem list, not score — user sees specific problems
2. Furniture-fit as mandatory check — nobody else does this
3. Experience metrics via isovist — PhD-level spatial quality measurement
4. Cost breakdown with contractor margin visible — our moat
5. Unified engine — everything in one pass, no duplicated work

---

### Component 15: Ranker

**Status:** Unchanged.

**Purpose:** Given ~74 Pareto-optimal candidates from Layer 2, pick the final 3 to show the user. These 3 must be *maximally different* on the user-visible axes (privacy, light, cost) — not just the top 3 scorers.

**Inputs:** All Pareto candidates with their evaluation reports.

**Outputs:** Top 3 layouts, each labelled with its differentiator.

**Internal functions:**
```python
class LayoutRanker:
    def project_to_user_axes(layouts)               # Collapse to 3D: 
                                                    # privacy/light/cost
    def find_extremes(layouts, axes)
    def maximize_differentiation(candidates, k=3)   # Pick 3 most different
    def label_each_layout(top_3)                    # "Best for privacy" etc.
    def explain()
```

**Worked example (NE 30×40):**
```
Input: 74 Pareto-optimal candidates across 3 topologies.

Projection to user axes:
  - Privacy score (0-10)
  - Natural light score (0-10)
  - Cost (₹ Lakh)

Finding extremes:
  Best privacy: Layout C-17 (9.5/10 privacy, 7 light, ₹59L)
  Best light: Layout SP-03 (7 privacy, 9.5 light, ₹57L)
  Best cost: Layout SP-11 (8 privacy, 8 light, ₹54L)

Maximally different 3:
  Layout A (Central Spine, C-17): "Best for privacy"
  Layout B (Strip, SP-03): "Most natural light"  
  Layout C (Strip, SP-11): "Most cost-efficient"

Each layout shown with its problem report from Component 14.
User picks one, then goes to click-to-edit.
```

---

### Component 16: Dual-Drawing Renderer [CHANGED]

**Status:** Changed — now outputs working drawing PDF + regulatory drawing PDF + interactive link.

**Purpose:** Final deliverable. Same house rendered twice — for contractor (detailed) and for approval authority (code-compliant simplified).

**Inputs:** One chosen layout + both envelopes + brief.

**Outputs:**
- Working Drawing PDF (for contractor) — full dimensioned detail
- Regulatory Drawing PDF (for CMDA/DTCP) — simplified, code-focused
- Interactive shareable link (for showing family + getting feedback)
- BOQ + cost breakdown
- Construction sequence suggestion

**Internal functions:**
```python
class DualDrawingRenderer:
    def render_working_drawing(layout)              # Contractor detail level
    def render_regulatory_drawing(layout)           # CMDA submission level
    def render_bom_and_cost(layout)                 # Full BOQ
    def render_furniture_layout(layout)             # Overlay showing fit
    def generate_interactive_link(layout)           # Web-viewable
    def generate_construction_sequence(layout)      # Suggested build order
    def explain()
```

**Output structure:**
```
/output-package/
  ├── drawings/
  │    ├── working-drawing.pdf       (15-25 pages — for contractor)
  │    ├── regulatory-drawing.pdf    (5-8 pages — for CMDA submission)
  │    └── furniture-layout.pdf      (show furniture actually fits)
  ├── cost/
  │    ├── boq.xlsx                  (bill of quantities)
  │    ├── cost-breakdown.pdf        (with contractor margin line visible)
  │    └── comparison-table.pdf      (working vs regulatory cost delta)
  ├── contractor-pack/  ← from Contractor Defence Layer
  │    ├── decision-rationale.pdf    (why each choice was made)
  │    ├── indian-code-citations.pdf (NBC + IS + CMDA references)
  │    ├── contractor-questions.pdf  (20 questions to pre-empt disputes)
  │    └── construction-sequence.pdf (suggested build order)
  └── share-link.txt                  (public URL for family review)
```

---

## 7. Cross-cutting concerns

### 7.1 Contractor Defence Layer

**Status:** NEW — approved for v1.

**Purpose:** Auto-generated document pack that defends the design against common contractor pushback. The family hands this to the contractor along with the drawings.

**Scope:**
1. **Decision rationale document** — for every non-obvious design choice, explain why. "The kitchen is NE, not SE, because in Chennai warm-humid climate the morning sun reduces mould risk — this is per NBC 2016 Part 8 passive design recommendations."
2. **Indian code citations** — every material spec, every clearance, every setback, with citation. "Column size 230×450 per IS 456:2000 Table 18."
3. **Contractor questions** (the 20 most common) — pre-empt arguments. "If the contractor says [X], the correct response is [Y], citing [Z]."
4. **Construction sequence** — suggested build order so the contractor can't claim "I can't do it in that sequence."

**Why this matters:** Our target user is a non-technical family. The contractor has informational advantage. This pack neutralises that advantage. The family walks in prepared.

**This is BuildemUp†'s moat at execution time.** No other AI tool generates contractor-defence documentation.

---

### 7.2 Resilience Layer

**Status:** Cross-cutting — applies to every component.

**Purpose:** Graceful failure modes. When something can't produce a valid output, it tells the user what went wrong and what to do.

**Failure modes to handle:**

| Scenario | Graceful response |
|---|---|
| Plot too small for all rooms | Component 3 proposes cuts (not error) |
| All topologies fail for this plot | Show diagnostic: which constraints conflict |
| NSGA-II produces no valid survivors | Fall back to rule-based only, warn user |
| User-edited layout breaks structural grid | Show warning + restore option |
| Two user-dragged rooms overlap | Auto-resolve by snapping, show notification |
| User edits create NBC violation | Warn, don't block; show the rule being broken |
| Out-of-range plot (<600 or >8000 sqft) | Refuse politely, explain tier system |
| Contradictory user input | Escalate to Trade-off Negotiator (Component 3) |

**Every component must implement its own failure handling in a way that never shows the user a black-box error.**

---

## 8. Data flow summary

```
  USER INPUT (chat)
         │
         ▼
  [1] Conversational Brief
         │ produces: Brief
         ▼
  [2] Feasibility (×2)
         │ produces: WorkingEnvelope + RegulatoryEnvelope
         ▼
  [3] Trade-off Negotiation (if conflicts)
         │ produces: RevisedBrief
         ▼
  [4] Plot Analysis
         │ produces: PlotAnalysis (tier, climate, sun path)
         ▼
  [5] Topology Selector
         │ produces: 3 TopologySelections
         ▼
  [6] Orientation Priority
         │ produces: OrientationPreferences (per climate zone)
         ▼
  [7] Structural Grid Engine
         │ produces: StructuralGrid (column positions)
         ▼
  [8] Corridor Design
         │ produces: CorridorPath per topology
         ▼
  [9] Room Sizer (+ furniture envelope)
         │ produces: RoomSizeTable (min/target/max with furniture)
         ▼
  [10] Wet-Zone Stack Planner
         │ produces: WetZonePlan (stacks, wet walls)
         ▼
  [11a] Topology Mutation Layer  ← NEW
         │ produces: 6-8 seeds per topology
         ▼
  [11b] Local NSGA-II Refinement
         │ produces: ~74 Pareto-optimal candidates across 3 topologies
         ▼
  [12] Vertical Alignment Engine
         │ produces: multi-floor-aligned layouts
         ▼
  [13] Door Placement
         │ produces: DoorSchedule
         ▼
  [14] Unified Evaluation Engine  ← MERGED
         │ produces: EvaluationReport + ProblemReport for each
         ▼
  [15] Ranker
         │ produces: Top 3 layouts, maximally different
         ▼
  USER PICKS ONE
         │
         ▼
  [16] Dual-Drawing Renderer
         │ produces: Working PDF + Regulatory PDF + Interactive link 
         │           + BOQ + Contractor Pack
         ▼
  DELIVERED TO USER
```

---

## 9. What's unique (the moat)

When BuildemUp† launches, this is what nobody else has:

1. **Topology-first, grid-first generation pipeline** — architecturally honest method
2. **Topology mutation layer** — 8 global operators explore real design alternatives
3. **Furniture-fit as a mandatory check** — Neufert-based 2D packing per room
4. **Six Indian-family optimisation objectives** — pooja, multigen, bathroom practicality, wet-zone ₹ cost, Tamil climate, contractor margin
5. **Problem list instead of single score** — specific issues, specific suggestions
6. **Dual envelope (working + regulatory)** — with visible cost delta
7. **Dual drawings (contractor + CMDA)** — nobody else does both for Indian context
8. **Contractor defence layer** — document pack that arms the family against information asymmetry
9. **Climate-zone-aware orientation rules** — NBC 5 zones, not a one-size-fits-all
10. **Transparent contractor margin line** — visible by default, user can compare quotes
11. **Interactive shareable link output** — family can review and edit, not just a PDF
12. **Explain-yourself-per-component** — engine tells user *why* every decision was made

Of these, #4, #7, #8, #10 are the hardest for a Western AI tool to replicate, because they require specific domain knowledge of Indian construction, culture, and contractor dynamics. That's our durable advantage.

---

## 10. Open questions (your feedback welcome)

Before we start coding, I'd like your input on the following:

1. **Topology Mutation Layer** — do the 8 operators feel right? Would you add any, or drop any? (Hot-take candidates I considered but didn't include: room-wise rotation, single-room mirroring, entry-door relocation.)

2. **Six optimisation objectives** — are these the right six for v1? Specifically, should we add a seventh for "future expansion capability" (can they build upward later, or knock a wall)?

3. **Contractor defence layer** — I've scoped this as 4 documents. Too much? Too little? Should it include a quote-comparison template (where they paste a contractor's quote and we highlight overcharging)?

4. **Evaluation engine — should we show ANY aggregate number?** Today I have sub-scores per category but no single "overall." Some users may want one for quick comparison. Or do we strictly refuse?

5. **Ranker's "maximally different" approach** — do you agree with 3 layouts optimised for {privacy, light, cost}? Or should the 3 dimensions be different (e.g., {space-efficient, family-friendly, luxurious})?

6. **The example plot** — this brief is ambitious. Part of its value is exercising Trade-off Negotiation. Are you OK with the engine flagging badminton as unfeasible and some rooms as tight?

7. **Deferred for later / not in v1:**
   - Learning from user edits (Component 19, v2)
   - 3D walkthrough rendering (v2)
   - Solar panel layout optimisation (v2)
   - Prefab/precast tier support (v3)
   - BIM/IFC export (v3)

---

## Appendix A: Component count comparison (v1 vs v2)

| Version | Component count | Notes |
|---|---|---|
| v1 | 18 | Scorer + Problem Finder + Connection Graph + fast subset fragmented |
| **v2** | **16 (+2 cross-cutting)** | Evaluation merged; Topology Mutation added; cleaner structure |

## Appendix B: Known open technical questions

- **Which NSGA-II library?** Pymoo is the standard; confirmed. Version to pin: 0.6.x.
- **Which 2D packing library for furniture fit?** `rectpack` or custom. Need to evaluate.
- **Isovist computation** — `visvalingamwyatt` or `shapely`-based custom. Need to confirm performance.
- **City rate table maintenance** — manual for now (Chennai, Bangalore, Mumbai). Later: scraper from published government rate sheets.
- **Tamil Nadu CMDA regularisation rules** — need to verify the 2025 amendment text matches what's in our knowledge base.

---

**END OF DOCUMENT**

**Waiting for Ramalingam's feedback before any code is written or any walkthrough is produced.**

