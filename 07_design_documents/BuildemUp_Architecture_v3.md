# BuildemUp† — Architecture v3 (Delta from v2)

**†** = placeholder product name, marked everywhere for future global rename.

---

## 0. Document purpose

This document is the **delta from v2**, not a rewrite. For full component detail of unchanged components, refer to `BuildemUp_Architecture_v2.md`. This file captures only what changed based on the second critique round.

**Status: awaiting Ramalingam's feedback, after which we move to end-to-end walkthrough (no more critique cycles).**

---

## 1. Summary of changes from v2

| # | Change | Severity |
|---|---|---|
| 1 | Component 14 restructured — Hard/Soft evaluation split | **CRITICAL** |
| 2 | NEW Component 17: Quote Comparison Engine | **MAJOR** |
| 3 | Component 11a: Entry Door Mutation added (9th operator) | Major |
| 4 | Component 14.1 enhanced: Circulation Hierarchy scoring | Major |
| 5 | Component 14 new sub-category: Construction Feasibility checks | Major |
| 6 | NEW cross-cutting concern: Constraint Propagation | Major |
| 7 | NEW system-wide capability: Fast Mode / Deep Mode | Major |
| 8 | Component 15 (Ranker): new axes proposal | Medium |
| 9 | NSGA-II diversity preservation | Technical |
| 10 | Human-language problem reports (explicit mandate) | UX |

**Component count:** 16 → 17 (added Quote Comparison Engine)
**Cross-cutting concerns:** 2 → 3 (added Constraint Propagation)

---

## 2. Positioning statement (important — read first)

Ramalingam's stated goal: "combine all existing fragmented market products like Autodesk Revit."

**Honest calibration:** We are not trying to *be* Revit. Revit has 2000 engineers over 25 years. We have one solo founder. We cannot match Revit's feature surface.

**What we *are* doing:** Borrowing from Revit the things that serve non-professionals (parametric grid, structural checks, auto-BOQ, drawing consistency, clash detection in simplified form) and delivering something Revit fundamentally cannot — transparency and education for Indian homeowners.

**Our category is not "BIM software."** It is **"decision engine for Indian homebuyers"** (per the earlier critique, which was right).

The product wins on four axes Revit ignores:
1. Cost transparency (not Revit's audience)
2. Contractor defence (not Revit's problem)
3. Indian cultural context (not Revit's focus)
4. Non-professional UX (explicitly the opposite of Revit)

This positioning should guide every scope decision from here on.

---

## 3. CRITICAL: Component 14 restructured — Hard/Soft split

### The v2 bug

v2's Unified Evaluation Engine treated structural validity alongside cost and comfort in the same objective vector. Under NSGA-II Pareto filtering, a structurally invalid layout with great cost could survive because "Pareto-optimal on cost dimension."

That's a real correctness bug. A layout with a column in the middle of a bedroom cannot be a valid survivor regardless of how good its cost is.

### The v3 fix: two-stage evaluation

```
Stage 1: HARD CONSTRAINT CHECKER (binary pass/fail)
  ↓ if any fail, layout DISCARDED (not ranked)
  
Stage 2: SOFT OBJECTIVE SCORING (optimisation via NSGA-II)
  ↓ only layouts that passed Stage 1 get scored here
  ↓ ranked on multi-objective Pareto front
```

### Stage 1 — Hard Constraints (must all pass)

```python
class HardConstraintChecker:
    def check_structural_alignment(layout, grid) -> bool
    def check_nbc_compliance(layout) -> bool
    def check_furniture_fit_minimum(layout) -> bool
    def check_plumbing_feasibility(layout) -> bool
    def check_vertical_alignment(layout) -> bool
    def check_load_path_continuity(layout) -> bool
    def check_fire_egress(layout) -> bool         # Distance to exit
    def check_ventilation_minimum(layout) -> bool # Every room has a window or mech vent
    def check_external_wall_rule(layout) -> bool  # Bedrooms must touch external wall
    
    def validate_all(layout) -> ValidationResult
        # Returns pass/fail + specific failure reasons
```

### Stage 2 — Soft Objectives (optimised)

```python
class SoftObjectiveScorer:
    def score_cost(layout) -> float              # ₹
    def score_pooja_placement(layout) -> float   # 0-10
    def score_multigen(layout) -> float          # 0-10
    def score_bath_practicality(layout) -> float # 0-10
    def score_wet_zone_efficiency(layout) -> ₹   # plumbing cost
    def score_climate_comfort(layout) -> float   # 0-10
    def score_light(layout) -> float             # 0-10 NEW explicit
    def score_privacy(layout) -> float           # 0-10 NEW explicit
    def score_circulation_hierarchy(layout) -> float # 0-10 NEW
    def score_experience(layout) -> float        # 0-10
    
    def run_nsga2(population) -> ParetoFront
```

### Impact on the pipeline

Before NSGA-II runs, every candidate is filtered through Hard Constraint Checker. Failed candidates don't even enter the population. This:
- Makes NSGA-II 2–3x faster (smaller population)
- Eliminates a class of correctness bugs
- Cleaner semantics: "good for your wallet" and "structurally valid" are not the same question

---

## 4. NEW: Component 17 — Quote Comparison Engine

### Why this deserves component status

This is the single highest-value consumer feature we can build. Users upload a contractor's quote; we extract items, compare against our BOQ, flag discrepancies.

Value to user: saves ₹1L–5L per project, gives them confidence in negotiation.
Value to product: generates word-of-mouth — "I saved ₹3 lakh thanks to this tool."
Differentiation: nobody else does this. Not Revit, not Maket, not Finch, not Forma, not Archistar.

### Component 17: Quote Comparison Engine

**Status:** NEW.

**Purpose:** User uploads a contractor quote (PDF, image, or Excel). Engine extracts the BOQ, compares against our estimate for their layout, and produces a discrepancy report.

**Inputs:**
- User's chosen final layout (from Component 16)
- Our BOQ and cost estimate (from Component 14 cost metrics)
- Contractor's quote (user-uploaded, any format)

**Outputs:**
- `DiscrepancyReport` — line-by-line comparison with flags
- Suggested counter-offer language
- Contractor-credibility score

**Internal functions:**
```python
class QuoteComparisonEngine:
    def ingest_quote(file) -> RawQuote        # OCR + parse PDF/image/xlsx
    def extract_items(raw_quote) -> ItemList  # Claude API extracts line items
    def match_to_our_boq(quote_items, our_boq) -> MatchedTable
    def flag_overpricing(matched_table) -> List[Flag]
    def flag_missing_items(our_boq, quote_items) -> List[Flag]
    def flag_lump_sums(quote_items) -> List[Flag]  # "Sundries: ₹2L" = suspicious
    def flag_unexplained_markups(matched_table) -> List[Flag]
    def compute_credibility_score(quote) -> float
    def generate_counter_offer(discrepancies) -> CounterOfferDraft
    def explain()
```

**How it works:**

1. User uploads contractor quote file (any format)
2. OCR + Claude API parse into structured line items (material, quantity, unit, rate, total)
3. Match each quote item to our BOQ line (fuzzy match: "TMT 8mm" matches "Steel TMT 8mm Fe500")
4. For each matched pair, compute price delta:
   - `> +20%`: OVERPRICING flag (red)
   - `+5% to +20%`: HIGH PRICE (amber)
   - `-20% to +5%`: FAIR (green)
   - `< -20%`: UNDERPRICED (amber — often means low quality)
5. Detect missing items (our BOQ has steel but quote doesn't — contractor plans to skip?)
6. Detect unexplained lump sums ("miscellaneous: ₹1.5L" = 5% of project = suspicious)
7. Generate counter-offer: "The quote lists TMT at ₹85/kg but Chennai market rate is ₹68/kg. Request ₹68/kg or equivalent Fe500 substitute."
8. Contractor credibility score: 0–100 based on line-item accuracy, completeness, and reasonable rates

**Worked example (NE 30×40, user receives contractor quote of ₹72L):**

```
QUOTE COMPARISON REPORT

Our estimate:          ₹58.2L
Contractor quote:      ₹72.0L
Delta:                 +₹13.8L (+23.7%)
Credibility score:     58/100 (Medium concern)

LINE-ITEM BREAKDOWN (showing top discrepancies):

⚠ STEEL TMT 8mm-25mm
  Quote: ₹85/kg × 5,500 kg = ₹4.68L
  Market: ₹68/kg (Chennai 2026)
  Overpayment: ₹0.94L
  Action: Request ₹68/kg, cite JSW/TATA current list price.

⚠ CEMENT OPC 53
  Quote: ₹450/bag × 850 bags = ₹3.83L
  Market: ₹395/bag
  Overpayment: ₹0.47L
  Action: Request market rate; offer to buy direct.

🚩 "MISCELLANEOUS / SUNDRIES"
  Quote lists ₹1.8L without breakdown
  Typical misc ≤ 2% of total = ₹1.2L max
  This item is 2.5% of total and unexplained
  Action: ASK FOR ITEMISED BREAKDOWN before signing.

🚩 BATHROOM FITTINGS
  Quote lumps: "bathroom fittings Jaquar: ₹3L"
  Our BOQ: 6 bathrooms × Jaquar mid-tier = ₹1.8L
  Overpayment: ₹1.2L OR contractor selecting premium without disclosure
  Action: Request brand + model for every fitting.

⚠ MISSING FROM QUOTE:
  - Waterproofing for 2 bathrooms on FF (₹30K)
  - Electrical conduiting for home office extra points (₹8K)
  - Utility area plumbing riser (₹15K)
  These will be "extras" charged later. Request inclusion upfront.

✓ FAIR PRICING ON:
  - Concrete works (₹18.2L vs our ₹17.9L — 1.7% over, acceptable)
  - Tile work (within 5%)
  - Labour (within market range)

RECOMMENDED COUNTER-OFFER:
  Total: ₹62.5L (ours ₹58.2L + reasonable contractor margin 7%)
  Potential savings: ₹9.5L

NEGOTIATION LANGUAGE (for you to use):
  "Thank you for the quote. I'd like to discuss a few items:
   - Steel and cement rates should match current Chennai market.
   - Please itemise the ₹1.8L miscellaneous line.
   - Please specify brand and model for all bathroom and 
     electrical fittings.
   - The quote is missing waterproofing for 2 FF bathrooms and 
     electrical conduiting for home office — please include 
     or confirm these won't be charged later as extras.
   Based on market rates and a 7% contractor margin, I'm 
   comfortable at ₹62.5L. Happy to discuss."
```

**What makes this unique:** Nothing like this exists. Closest analogy is medical bill auditing services, but for construction. This alone could be a standalone product.

**v1 scope decision:** Include. This is the most shareable feature in the entire product. The virality upside justifies the complexity.

---

## 5. Component 11a — Entry Door Mutation added

Updated mutation operators from 8 to 9:

1. Horizontal flip (E↔W)
2. Vertical flip (N↔S)
3. Staircase relocation (4 positions)
4. Corridor inversion
5. Public/private zone swap
6. Wet-wall rotation
7. Grid scaling
8. Vertical rearrangement (GF vs FF room assignment)
9. **NEW: Entry door relocation** — for NE-facing plot, try entry at NE-center, NE-corner-E, NE-corner-W, offset-NE. Each produces different circulation, privacy, and visual experience.

**Why this matters for Arjun's 30×40:**
- Entry at NE-center: direct view of living, staircase on right
- Entry at NE-corner-W: entry corridor to living, more privacy, stair hidden
- Entry at NE-corner-E: entry near kitchen (unusual but efficient for small plots)
- Entry offset-NE: diagonal reveal, more dramatic (Alexander's "Entry Transition" pattern)

---

## 6. Component 14.1 enhancement — Circulation Hierarchy

v2's graph metrics computed BFS step-depth and betweenness but didn't separate the three path types. v3 adds explicit path classification.

### New sub-component: CirculationAnalyzer

```python
class CirculationAnalyzer:
    def identify_primary_path(layout)    # Entry → living → dining
    def identify_secondary_paths(layout) # Living → bedrooms, living → pooja
    def identify_service_paths(layout)   # Kitchen → utility, bath access
    
    def detect_path_overlap(primary, secondary, service)
    def detect_cross_traffic(paths)      # Where paths cross inappropriately  
    def detect_private_public_conflicts(paths)  # Service crossing private zone
    
    def score_circulation_hierarchy()    # 0-10 based on clean separation
    def explain()
```

### Scoring logic

```
10/10: Primary, secondary, service paths are fully separated
8/10:  One minor intersection (e.g., service crosses edge of secondary)
6/10:  Service crosses public zone (kitchen-to-utility path through living)
4/10:  Private zone requires crossing public space (master bedroom via living)
2/10:  Multiple crossings; plan is circulation chaos
```

### Worked example (NE 30×40, Layout 1 Central Spine):

```
CIRCULATION HIERARCHY ANALYSIS:

Primary path (entry → living → dining):
  NE door → foyer (2m) → living (open) → dining (open to living)
  Length: 4.5m, no doors, no crossings
  Score contribution: 10/10

Secondary paths:
  Living → BR1: living → corridor → BR1 door (one crossing into 
                 corridor, clean)
  Living → BR2: same pattern, clean
  Living → pooja: direct from living (no corridor needed)
  Living → guest wash: from living to wash, one door
  Score contribution: 9/10

Service paths:
  Kitchen → utility: kitchen back door → utility (adjacent, no cross)
  Kitchen → dining: through open pass-through, no conflict with primary
  Bathroom access: from corridor, doesn't cross public
  Score contribution: 10/10

Overlaps detected: 1
  - Guest wash access from living partially overlaps with primary path
  - Impact: minor, can be mitigated with screen

Cross-traffic: None detected

Private-public conflicts: None detected

OVERALL CIRCULATION HIERARCHY: 9/10
```

---

## 7. Component 14 — Construction Feasibility sub-checks

New sub-category in Unified Evaluation Engine.

```python
class ConstructionFeasibilityChecker:
    def check_beam_continuity(layout, grid) -> List[Issue]
        # FF walls must land on GF beams or columns, not mid-slab
    
    def check_slab_casting_sequence(layout) -> SequencePlan
        # Continuous pour per floor, identify pour breaks
    
    def check_staircase_shuttering(layout) -> List[Issue]
        # Access for formwork, sufficient working space below
    
    def check_waterproofing_continuity(layout) -> List[Issue]
        # Every wet area has continuous membrane, no gaps at joints
    
    def check_cantilever_limits(layout) -> List[Issue]
        # Cantilevers < 1.5m, proper back-span, depth adequate
    
    def check_service_access_during_construction(layout) -> List[Issue]
        # Can MEP contractors access chases during build?
    
    def generate_construction_warnings(layout) -> Report
```

**Worked example for NE 30×40 Layout 1:**
```
CONSTRUCTION FEASIBILITY:

✓ Beam continuity: All FF walls land on GF beams or columns.
✓ Slab casting: GF slab = 1 pour (~30 cum), FF slab = 1 pour, terrace = 1 pour.
  Each pour within 4-hour concrete working time.
⚠ Staircase shuttering: Landing at mid-floor requires special prop 
  arrangement. Contractor note added to package.
✓ Waterproofing: All wet areas bounded by continuous membrane; 
  chase penetrations sealed per IS 2645.
✓ Cantilever: FF balcony 1.2m cantilever, back-span 3.0m (ratio 1:2.5 
  OK), beam depth 350mm sufficient.
⚠ Service access: FF wet chase accessible only from corridor — 
  contractor must route MEP before plastering. Note added.
```

---

## 8. NEW cross-cutting concern: Constraint Propagation

### Why cross-cutting (not a component)

Constraint propagation is not a deliverable the user sees. It's a capability used by many components: rule-based placement enforces it, NSGA-II mutation repairs violations, evaluation verifies it. Making it a "component" bloats the architecture; making it a cross-cutting concern reflects how it actually works.

### Where it applies

| Component | Constraints propagated |
|---|---|
| 7 Grid | Column-on-setback, span ≤ 4.5m |
| 8 Corridor | Min width 0.9m, connects all rooms |
| 9 Sizer | Furniture fit minimums |
| 10 Wet-Zone | Bathroom on wet wall, stack alignment |
| 11a Mutation | Invalid mutations filtered out |
| 11b NSGA-II | Crossover/mutation repair for constraint violations |
| 12 Vertical | Column stacking, load path continuity |
| 14 Hard Check | All above, plus NBC, fire egress, ventilation |

### Implementation pattern

```python
class ConstraintEngine:
    """Shared constraint-propagation utilities used by many components."""
    
    def propagate_wet_wall(layout, wet_rooms)
    def propagate_external_wall_rule(layout, bedrooms)
    def propagate_column_alignment(layout, grid)
    def propagate_corridor_connectivity(layout, corridor)
    
    def repair_violation(layout, violation) -> Optional[RepairedLayout]
        # Tries to fix; returns None if unfixable
    
    def validate(layout) -> List[Violation]
    
    def explain(violation)
```

### Impact

- NSGA-II produces fewer invalid offspring (mutation/crossover repair inline)
- Rule-based placement fails fast when constraints can't be satisfied
- Fewer Pareto candidates need Stage 1 rejection (they never existed)
- Overall pipeline: 40–60% faster by our estimate

---

## 9. NEW system-wide capability: Fast Mode / Deep Mode

### The UX problem

v2's full pipeline takes 30–90 seconds on good hardware. For a first-time visitor just exploring, that's too long. For a serious user who wants the best layout, it's fine.

### The solution

Two modes, user-selectable:

**Fast Mode** (< 3 seconds):
- Skip Topology Mutation (11a)
- Skip full NSGA-II; use 5 generations of smaller population (20)
- Run only Hard Constraint Checker (no Soft scoring)
- Output: 3 decent-quality layouts

**Deep Mode** (60–90 seconds):
- Full pipeline as specified in v2 + v3
- 3 topologies × 6-8 mutations × 30 generations
- Full Hard + Soft evaluation
- Output: 3 Pareto-optimal, maximally-different layouts

### UX flow

```
First interaction after brief is confirmed:
  → System runs Fast Mode in background while user reviews brief
  → Shows 3 quick layouts ("initial concepts") in 3-5 sec
  → Banner: "These are quick concepts. Want us to deeply optimise? 
             Takes 60 seconds, usually produces 20-30% better layouts."
  → User clicks "Deep optimise" → Deep Mode runs
  → Result: polished 3 final layouts
```

This lets users taste the product immediately, then opt into full power.

### Implementation

```python
class ModeSelector:
    def run_pipeline(brief, mode: Literal["fast", "deep"]) -> List[Layout]
```

Every component has a `mode` parameter. Components honour it by reducing iterations, skipping sub-checks, or using cached results.

---

## 10. Component 15 (Ranker) — new axes

### The v2 proposal

Privacy / Light / Cost. Good, but requires architectural literacy to interpret.

### The v3 proposal

**Budget / Family / Experience**

- **Budget-focused:** cheapest viable layout, maximises sqft-per-rupee, minimises frills. For users building on tight budget.
- **Family-focused:** best for daily family life — strong privacy gradient, clean circulation, multigen-friendly, storage-rich. For users optimising lived experience.
- **Experience-focused:** best for feel and impression — entry reveal, openness, light, visual interest. For users optimising aesthetic/emotional quality.

### Why this is better

- Each dimension is immediately meaningful to a non-architect
- The three are genuinely different ("Balanced" from another suggestion isn't)
- Maps cleanly to user self-identity: "I'm buying for my family" vs "I'm building my dream home"
- Marketing-friendly: "Three layouts, one for every priority"

### Worked example for NE 30×40:

```
FINAL THREE LAYOUTS PRESENTED:

Layout A: "Best for Budget"
  ₹54.8L (₹3.4L under estimate)
  Central Spine topology
  Slightly smaller master; simpler finishes;
  Fewer mutations on optimised side

Layout B: "Best for Family"
  ₹58.5L
  Central Spine topology (different variant)
  Strong privacy gradient, parents' bedroom GF,
  Wet-zone tight, flow 10/10

Layout C: "Best for Experience"
  ₹61.2L
  Courtyard topology
  Double-height foyer, central light well,
  Experience score 9.5/10
```

---

## 11. NSGA-II — diversity preservation

Technical refinement only. Applied inside Component 11b.

```python
def select_next_generation(population, fitness, target_size):
    # Standard NSGA-II uses non-dominated sorting + crowding distance.
    # We add:
    # 1. Diversity penalty: if two survivors are too similar 
    #    (layout DNA distance < threshold), penalise one
    # 2. Niching: cluster Pareto front into regions, ensure each 
    #    cluster contributes at least one survivor
    # Result: the final 20 survivors are genuinely different, 
    # not 20 variations of the same local optimum
```

---

## 12. Problem Reports — explicit human-language mandate

Every Problem Report entry must:

1. Name the issue in plain English (not "Privacy score 7")
2. Explain where it is (room/wall/door)
3. Suggest a concrete fix with cost if applicable
4. Cite the source when meaningful (Neufert, NBC, climate rule)

**Bad (v2-style):** "Entry reveal score: 6/10"

**Good (v3 mandate):** "When you open your front door, you see the staircase railing 3 feet away. A better entry experience gives a diagonal view into the living room. We suggest shifting the staircase 2 feet east (see Layout 2) or adding a decorative wall behind the staircase (₹18,000)."

This applies across every component's `explain()` method.

---

## 13. Updated data flow (v3)

```
  USER INPUT (chat)
         │
         ▼
  ┌────────────── MODE SELECTOR ─────────────┐
  │  Fast Mode  OR  Deep Mode                │
  └───────┬──────────────────────┬───────────┘
          │                      │
          ▼ (both modes continue through...)
  [1] Conversational Brief
  [2] Feasibility (×2)
  [3] Trade-off Negotiation
  [4] Plot Analysis
  [5] Topology Selector
  [6] Orientation Priority
  [7] Structural Grid Engine
  [8] Corridor Design
  [9] Room Sizer (+ furniture)
  [10] Wet-Zone Stack Planner
  [11a] Topology Mutation (skip if Fast)
  [11b] NSGA-II (5 gen if Fast, 30 gen if Deep)
  [12] Vertical Alignment
  [13] Door Placement
         │
         ▼
  ┌────── Component 14: Unified Evaluation ──────┐
  │                                              │
  │  Stage 1: HARD CONSTRAINTS (pass/fail)       │
  │    ├─ Structural alignment                   │
  │    ├─ NBC compliance                         │
  │    ├─ Furniture fit minimum                  │
  │    ├─ Plumbing feasibility                   │
  │    ├─ External wall rules                    │
  │    ├─ Fire egress + ventilation              │
  │    └─ Construction feasibility               │
  │                                              │
  │  Stage 2: SOFT OBJECTIVES (optimised)        │
  │    ├─ Graph + Circulation Hierarchy          │
  │    ├─ Spatial + Experience                   │
  │    ├─ Cost (₹, city rates)                   │
  │    ├─ 6 Indian objectives                    │
  │    └─ Produces ProblemReport                 │
  └──────────────────┬───────────────────────────┘
                     │
                     ▼
  [15] Ranker (Budget / Family / Experience)
                     │
                     ▼
             USER PICKS ONE
                     │
                     ▼
  [16] Dual-Drawing Renderer
                     │
                     ▼
         USER RECEIVES CONTRACTOR QUOTE
                     │
                     ▼
  [17] Quote Comparison Engine  ← NEW
                     │
                     ▼
  Empowered user negotiates with contractor
```

Cross-cutting concerns active throughout:
- Constraint Propagation (Components 7, 8, 10, 11, 12, 14)
- Contractor Defence (Component 16 + Component 17)
- Resilience (every component)

---

## 14. Open questions (updated from v2)

Answered in v3:
- ✓ Contractor defence scope: 4 docs + Quote Comparison (now Component 17)
- ✓ Aggregate score: explicitly refused; problem reports only
- ✓ Ranker axes: Budget / Family / Experience

Still open (need your input):

1. **Fast Mode layout count** — 3 layouts or 1 "quick concept" layout in Fast Mode? One might be less overwhelming; three preserves choice.

2. **Quote Comparison input format** — PDF only (simplest), or PDF + image (more work but more accessible)? Contractors in India often send quotes as WhatsApp images of handwritten sheets. Supporting image uploads is a significant accessibility win but requires OCR reliability.

3. **Layout DNA representation** — do you want me to document the internal encoding for implementation, or leave it for the coding phase?

4. **Fast vs Deep default** — which mode runs first when a new user submits a brief? I've proposed Fast Mode first (background), but "deep on demand" could be reversed.

5. **Construction warnings severity** — should we show all warnings (minor + major) or only issues that materially affect the contractor's work?

---

## 15. What we're NOT adding in v3 (honest scope discipline)

The critique made several suggestions I'm explicitly deferring:

1. **Learning from user behaviour** → v2 of the product (Component 19)
2. **Real-time feedback loop during edits** → v2 of the product
3. **3D walkthrough rendering** → v2 of the product
4. **Layout DNA caching** → implementation detail, not architectural
5. **Smart home / EV charging integration** → v2/v3 of the product

Each of these is valuable. None of them belongs in v1. Shipping v1 to real users and learning from their actual use matters more than perfecting the architecture.

---

## 16. Final architecture count (v3)

| Category | Count |
|---|---|
| **Components** | 17 (16 in v2 + Quote Comparison) |
| **Cross-cutting concerns** | 3 (Contractor Defence, Resilience, Constraint Propagation) |
| **System-wide capabilities** | 1 (Fast/Deep Mode selector) |

---

## 17. What's unique (updated moat list)

Of the 13 unique properties we now have:

1. Topology-first, grid-first generation
2. Topology mutation layer (9 operators including entry)
3. Furniture-fit as mandatory check
4. Six Indian-family optimisation objectives
5. Hard/Soft constraint split (correctness guarantee)
6. Problem list instead of single score
7. Dual envelope with cost delta
8. Dual drawings (contractor + CMDA)
9. Contractor Defence Layer
10. **Quote Comparison Engine** ← strongest individual feature
11. Climate-zone-aware orientation
12. Visible contractor margin
13. Interactive shareable link output

**Of these, #10 (Quote Comparison) is the single biggest differentiator.** It's the feature most likely to generate viral word-of-mouth. It's also the one hardest to replicate because it requires Indian cost knowledge, contractor-practice awareness, and trust from users to share financial documents.

---

## 18. Next step

We should stop critiquing and start walking through. One more critique cycle will produce one more v4, and we'll still not have code.

My strong recommendation: **next, we do the 30×40 NE-facing end-to-end walkthrough**. I trace your brief through all 17 components, show every input and output at each step, produce the 3 final layouts, their problem reports, the dual drawings (sketched), the contractor pack, and a sample Quote Comparison run.

After that walkthrough, if nothing structural is broken, we start coding Component 7 (Structural Grid Engine) — the foundation of everything downstream.

**Your call. Ready to walkthrough, or one more critique first?**

---

**END OF DOCUMENT**

*v3 delta from v2 complete. Total 17 components + 3 cross-cutting concerns + Fast/Deep mode.*
