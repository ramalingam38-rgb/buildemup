# BuildemUp† Architecture: Component-by-Component Market Validation Report

**Date:** April 22, 2026  
**Status:** Validation complete — review and approve before coding begins  
**Important:** "BuildemUp†" is a **placeholder name** — flagged with † at every occurrence so we can globally find and rename later. Ramalingam is considering "Archimind" but it's already taken by a US AEC-AI company (archimind.io). Final name TBD.

---

## Purpose

This document stress-tests every one of the 18 components of the BuildemUp† architecture against the current state of the art in floor-plan AI, generative design research, and Indian residential construction practice. For each component we ask three questions:

1. **What did we propose?**
2. **What does the market/research actually do?**
3. **Verdict:** Are we matching state-of-art, improving on it, behind it, or missing something entirely?

The goal is to catch architectural mistakes *before* a single line of new code is written.

---

## TL;DR Verdict Table

| # | Component | Verdict | Action |
|---|---|---|---|
| 1 | Conversational Brief | ✅ Matches state-of-art (Maket pattern) | Build as planned |
| 2 | Feasibility (dual: working+regulatory) | ✅ Matches industry standard | Build as planned |
| 3 | Trade-off Negotiation | ⚠️ Ahead of market (genuinely novel) | Build as planned, monitor UX carefully |
| 4 | Plot Analysis | ✅ Matches Forma/Snaptrude/InQI | Build as planned |
| 5 | Topology Selector | ⚠️ Improving on market (5 topologies systematic) | Build as planned, this is a moat |
| 6 | Orientation Priority | ✅ Matches NZEB India standards | Build as planned |
| 7 | Structural Grid Engine | ✅ Matches Indian RCC practice (Devdas Menon, IS 456) | Build as planned, extra care needed |
| 8 | Corridor Design | ✅ Matches academic literature (Optimizer paper) | Build as planned |
| 9 | Room Sizer | ✅ Matches Neufert/Ching standards | Build as planned |
| 10 | Bathroom Router | ✅ Matches plumbing chase best practice | Build as planned |
| 11 | Placement Engine | ✅ Matches CSP+GA approach (state of art) | Build as planned |
| 12 | Vertical Alignment | ✅ Matches multi-floor coordination practice | Build as planned |
| 13 | Door Placement | ✅ Standard practice | Build as planned |
| 14 | Connection-Graph (quick) | ✅ Matches space syntax (Hillier) | Build as planned |
| 15 | **Layout Problem Finder** (was "Scorer") | 🎯 **Improving on market** — research validates rename | **Build as Problem Finder, not Scorer** |
| 16 | Space-Auditor (quick) | ✅ Standard practice | Build as planned |
| 17 | Layout Generator + Ranker (NSGA-II) | ✅ Matches academic gold standard | Build as planned, this is a moat |
| 18 | Dual-Drawing Renderer | ✅ Matches industry working/permit standard | Build as planned |

**Summary:** 14 components match state of art exactly. 3 components improve on the market in ways that could become competitive moats. 1 component (Trade-off Negotiation) is novel enough that we need to be careful about UX. **Zero components are behind.**

---

## Locked Decision #1: "Layout Problem Finder" replaces "Lived Quality Scorer"

Your instinct was correct, and the research strongly validates it.

**The core insight (yours, in plain words):** A layout can score 95/100 and still have generic problems — the same kind of problems we've been hitting (bathrooms with shower clipped at 6ft depth, transit through bedrooms, etc.). A high single number is too easy to dismiss. A list of 12 specific problems forces you to look at each one and decide: do I fix this, or do I accept it knowing the trade-off?

**Research backing this:**

1. **Mostafavi et al. (Floor plan generation: The interplay among data, machine, and designer, SAGE 2025)** — explicitly proposes a *hybrid quantitative + qualitative* evaluation scheme because single-score evaluation "fails to capture the more complex architectural qualities." The field is moving away from one number.

2. **Comparative floor-plan analysis literature (van Hoogdalem, van der Voordt 1985–1998)** — established 30+ years ago that comparative criterion-by-criterion analysis ("five typological floor plans were distinguished... three of the five work well") gives architects information they can act on, where a composite score does not.

3. **Archistar's commercial PreCheck** — does *rule-by-rule reporting* against zoning/building codes, not a single compliance score. Their customers want to know exactly which rule failed.

4. **Architectural studio pedagogy research (2012)** — even in architecture education, the field has been pushing away from "grade-oriented" evaluation toward criterion-based assessment with explicit gap reporting.

**What this means for Component 15:**

- Renamed to **Layout Problem Finder** (not Scorer).
- Output is a **structured list of 30+ checks**, each with: status (pass / warn / fail), severity (critical / important / nice-to-have), the rule violated, the affected room(s), and a one-line "why this matters."
- We may *internally* compute a summary number for the ranker (Component 17) to use, but the user-facing output is the problem list.
- This becomes a moat: every competitor shows a score; we show a list of specific things wrong.

---

## Component-by-Component Validation

### Cluster A: Input & Planning (Components 1–4)

---

#### Component 1: Conversational Brief

**What we proposed:** Natural-language chat interface that extracts a structured JSON brief from the user (plot, rooms wanted, lifestyle hints, budget). Uses Claude API.

**What the market does:** Maket.ai reports that 90%+ of users instinctively try to interact with floor plans through natural language — typing "make the living room bigger" or "swap the kitchen and dining room." The chat → structured-spec → engine pattern is now industry-standard. Maket, Snaptrude, ArkDesign, Spacio all have it. Snaptrude even uses LLM agents that "analyze the site (zoning, setbacks, height limits, climate), generate a structured architectural program... assign dimensions based on building codes like IBC, ADA, and Neufert."

**Verdict: ✅ Matches state of art.**

**Action:** Build as planned. Use Claude API for v1 (per your Q5 answer). Build the corpus during real conversations to enable later fine-tune of Llama/Mistral 7B-13B via LoRA.

---

#### Component 2: Feasibility (runs twice — working setbacks + regulatory NBC setbacks)

**What we proposed:** Run the feasibility check twice — once with the user's actual setbacks (often 2ft on small TN plots) producing a "working drawing", once with full NBC 5/3/3 setbacks producing a "regulatory drawing" for permit submission. Show both.

**What the market does:** Industry standard distinguishes "Permit Set" (code compliance only, simplified) from "Construction/Working Set" (full detail). Multiple sources (Premier, METHOD, S3DA, MIK Architecture) confirm both sets are produced for any serious project. Indian sources (Infurnia) confirm the same for India: "Working drawings... give detailed dimensioned graphical information that can be used by a contractor" while "Submission drawings... must include precise information to determine whether the proposed work complies with all applicable regulations."

**Verdict: ✅ Matches industry standard exactly.**

**Action:** Build as planned. Per your Q7 answer — generate both, walk the user through one by one.

**Risk to monitor:** Some Indian small-plot homeowners *don't know* the distinction. When we show them both, the explanation must be clear: "this is what you can actually build" vs "this is what the municipality wants on paper."

---

#### Component 3: Trade-off Negotiation

**What we proposed:** When the user's brief is infeasible (e.g., "I want a 4BHK on 600 sqft"), the engine doesn't refuse — it proposes a structured negotiation: "On 600 sqft, we can fit 2BHK comfortably or 3BHK with very compact rooms. Which do you prefer?"

**What the market does:** Most competitors either silently refuse, silently overcompress rooms, or just generate an infeasible plan and leave the user to figure out what's wrong. TestFit comes closest with parametric "adjust the setback by 5 feet, watch hundreds of options reconfigure." But none of them have a structured *negotiation* layer for consumer users.

**Verdict: ⚠️ Ahead of market (genuinely novel for consumer tools).**

**Action:** Build as planned. This is a real differentiator but UX is critical — the negotiation must feel collaborative, not like the engine is rejecting the user.

**Risk to monitor:** If the negotiation feels like 20 questions, users will abandon. Keep it to 1–2 trade-off prompts max per session. Default to the most common compromise unless the user pushes back.

---

#### Component 4: Plot Analysis

**What we proposed:** Classify incoming plot into Tier 1 (600–2400 sqft, fully tuned), Tier 2 (2400–4000 sqft, good), Tier 3 (4000–8000 sqft, best-effort), out-of-range (refuse). Compute orientation, road-facing edge, neighboring buildings, FSI, setbacks per local code (Tamil Nadu CMDA/DTCP for v1).

**What the market does:** Forma (formerly Spacemaker) does this at city scale — environmental simulations, shadow tracking, noise levels, optimal orientations. TestFit does it at parcel scale — setbacks, parking, density, "186 units, 279 parking, $1.2M, 18% ROI" instantly. Snaptrude does zoning + setbacks + height + climate. InQI does code-aware site plans. Nomic does AI Zoning Analysis.

**Verdict: ✅ Matches state of art for residential parcels.** We don't need to match Forma's scale (it's for developers planning whole neighborhoods), just the parcel-level analysis.

**Action:** Build as planned. The Tier 1/2/3 classification is unique to consumer context — competitors don't tier because they assume professional users who know what they're getting into.

---

### Cluster B: Topology & Geometry (Components 5–8)

---

#### Component 5: Topology Selector

**What we proposed:** Five topologies for v1 — No-corridor (<18ft width), Strip / single-loaded (22–35ft), Central spine / double-loaded (18–32ft), L-shape (corner plots), Courtyard (40ft+ with depth). Selector picks 2–3 candidates per plot based on width and shape.

**What the market does:** Most consumer tools (Maket, ArkDesign) generate one layout per request without explicit topology selection — they just optimize within an implicit topology and may generate variants by reshuffling rooms within the same topology. Academic literature (Mostafavi 2025, the "Optimizer" CSP+GA paper) treats topology as an emergent property of the placement, not a first-class input. Architecture professor literature (single-loaded vs double-loaded vs courtyard) treats topology as the *primary* design decision.

**Verdict: ⚠️ Improving on market.** Making topology a first-class systematic decision (rather than implicit / emergent) is a moat.

**Action:** Build as planned with five topologies. Validated mapping from previous turn:
```
Plot width    Default topology candidates
< 18ft        No-corridor only
18-22ft       No-corridor, Central spine
22-28ft       Strip, Central spine
28-35ft       Strip, Central spine, L (if corner)
35-45ft       Strip, L, Courtyard (if depth allows)
45ft+         Strip, L, Courtyard, Atrium variant
```

---

#### Component 6: Orientation Priority

**What we proposed:** Latitude-correct orientation per plot. For Bangalore N-facing example: N=living/balcony/office, E=kitchen/pooja/children, S=bedrooms, W=stair/store/utility. Adjusts by city.

**What the market does:** NZEB India guidance (validated reference for Indian climate-responsive design) confirms: "long facades of buildings oriented towards north-south are preferred. Buildings should be oriented with their longer axis (north–south) aligned perpendicular to the prevailing winds." Service cores in east/west as thermal buffer. Climate-responsive Indian architecture for warm-humid (Chennai, Mumbai) emphasizes cross-ventilation; hot-dry (Rajasthan) emphasizes thermal mass; moderate (Bangalore, Pune) is most flexible.

**Verdict: ✅ Matches NZEB India standards.**

**Action:** Build as planned. CITY_DATA (8 cities) is correctly populated for v1. Tamil Nadu cities (Chennai = warm-humid, Coimbatore = moderate, Madurai = hot-humid) need verification on first deployment.

**Note:** Vastu is explicitly EXCLUDED per your prior decision. This is the right call — Vastu would force suboptimal orientations in many TN plots and is contested even among believers. We use the *climate principles* that overlap with Vastu (E for kitchen makes sense climatically AND vastically, etc.) without buying into the framework.

---

#### Component 7: Structural Grid Engine [NEW component]

**What we proposed:** Generate a column grid first, then place rooms within the grid. Columns at 3–4m spacing typical for residential, max 7.5m. Standard sizes: 230×230mm for G+0, 230×300 for G+1, 300×300 for G+2.

**What the market does:** Indian residential RCC practice (Devdas Menon, IS 456:2000, IS 1893 for seismic): "For Residential building column spacing may not more than 4.50m centre to centre." Maximum span 7.5m, minimum 2.5m, ideal 5m. Practical column sizes match exactly: 230×230 for G+0, 230×300 for G+1, 300×300+ for G+2 and above. Column placement rule: "always plan a column layout on a grid... corners of building, where beams meet, equal distance between centres of two columns."

**Verdict: ✅ Matches Indian RCC structural design practice exactly.**

**Action:** Build as planned. This is the critical new component — every downstream placement depends on it. The structural grid must be generated FIRST (before rooms), then rooms slot into the grid bays.

**Risk to monitor:** Hidden columns inside rooms are a major lived-experience problem (you can't put furniture against the wall). The placement engine must minimize columns intruding into rooms — push them to wall corners, partition walls, or façade.

---

#### Component 8: Corridor Design

**What we proposed:** Topology-driven corridor: no-corridor topology has none, strip has single 3.5–4ft corridor on one side, central spine has 4ft corridor through center, L wraps the inside corner, courtyard has corridors around the void.

**What the market does:** The "Optimizer" paper (Floor plan generation through mixed CP-GA approach, 2020) describes inserting corridors *after* room placement: "circulating rooms" (living, dining, entrance, corridor) are connected via inserted circulation. Industry minimum corridor width is 36–42 inches (3–3.5ft) per ADA-equivalent standards. Indian residential practice: 3ft minimum, 3.5–4ft preferred.

**Verdict: ✅ Matches academic literature and practice.**

**Action:** Build as planned. Corridor design is *driven by* topology choice (Component 5), so the two are tightly coupled.

---

### Cluster C: Placement & Connection (Components 9–13)

---

#### Component 9: Room Sizer

**What we proposed:** Size each room based on (a) function (Neufert/Ching minimums), (b) priority (master bedroom > children's bedroom), (c) available area after deducting corridors and structural grid bays.

**What the market does:** Snaptrude assigns dimensions "based on building codes like IBC, ADA, and Neufert." Industry standard for residential: master bedroom 12×14 minimum (168 sqft), secondary bedroom 10×12 (120 sqft), bath 5×8 (40 sqft) for full bath / 4×6 (24 sqft) for half bath, kitchen 8×10 minimum (80 sqft) for compact. NBC 2016 minimums for India: habitable room 9.5 m² (~102 sqft), kitchen 5.0 m² (~54 sqft), bath 1.8 m² (~19 sqft).

**Verdict: ✅ Matches Neufert/IBC/NBC standards.**

**Action:** Build as planned. Use NBC 2016 as floor for rejection (Q6: refuse if below NBC), Neufert/Ching as preferred targets (warn if below preferred but above NBC).

---

#### Component 10: Bathroom Router

**What we proposed:** Route bathrooms so they share wet walls with kitchens or other bathrooms wherever possible, vertically align with bathrooms above/below.

**What the market does:** Plumbing chase design literature (ArchCareer, Al Syed Construction, Plumbing Concepts): "Architects should align bathrooms or wet areas vertically to create efficient chase cores." Standard chase width 600–1200mm. "Grouping kitchens and bathrooms along the same vertical line allows you to share stacks across units, reducing pipe runs, material costs, and potential leak points." A four-bedroom case study explicitly cites: "Align two full bathrooms back-to-back with a shared 6-inch wet wall, placing the powder room adjacent to the stack. Specify a 3-inch main stack."

**Verdict: ✅ Matches plumbing chase best practice exactly.**

**Action:** Build as planned. The 6-inch shared wet wall and stack alignment rules need to be hard constraints, not soft preferences — getting this wrong costs the homeowner real money in plumbing rework.

---

#### Component 11: Placement Engine

**What we proposed:** CSP-style assignment of rooms to grid cells, with constraints (room A adjacent to room B, room C not adjacent to room D, room E on east wall, etc.). Generate multiple solutions, then prune.

**What the market does:** This is *exactly* the "Optimizer" paper approach (Floor plan generation through mixed constraint programming - genetic optimization, ScienceDirect 2020):
> "The envelope is first decomposed into a grid designed based on architectural considerations and adapted to any envelope shape. The grid cells are then allocated to the specified rooms in a constraint programming framework... Various layouts respecting the constraints can be obtained for a given couple (plan envelope, specifications). Circulations are then drawn in the layouts and a final cell shuffle is performed through a genetic optimization algorithm."

There's also a 2023 paper (Residential complex design as a Constraint Satisfaction Problem) that does exactly this for Indian/global residential, with daylight and privacy as evaluable constraints, BFS for full search, DFS for larger search trees.

**Verdict: ✅ Matches academic state of art exactly.** Our planned approach is essentially identical to the published research.

**Action:** Build as planned. Grid → CSP cell assignment → cluster + score top solutions → insert corridors → optimize. Use BFS for small plots (≤3 bedrooms), DFS for larger.

---

#### Component 12: Vertical Alignment Engine [NEW component]

**What we proposed:** When a multi-floor design is generated, align stacks vertically: bathrooms above bathrooms, kitchens above wet areas, columns continuous floor-to-floor.

**What the market does:** Vertical chase practice: "Chases must stack properly across floors to avoid jogs and turns." Indian RCC structural design: columns must be continuous floor-to-floor (zigzag column placement is "absolutely wrong"). Plumbing risers must be continuous. HVAC chases must align.

**Verdict: ✅ Matches multi-floor coordination practice.**

**Action:** Build as planned. This component runs *after* the ground floor is placed, propagating constraints upward to upper floors. If the upper floor placement can't honor the alignment, the engine flags it as a problem (via Component 15 Problem Finder), not silently overrides.

---

#### Component 13: Door Placement

**What we proposed:** Place doors at the closest connection point between adjacent rooms, oriented to swing into the larger room, away from corridors.

**What the market does:** Standard architectural practice. ADA-equivalent door sizes: 36-inch primary, 32-inch secondary. Door swing rules: into private rooms (bedroom doors swing into bedroom), away from circulation. No door clearance conflicts (one door's swing arc cannot intersect another door's swing arc).

**Verdict: ✅ Standard practice.**

**Action:** Build as planned. This is mostly mechanical — connect adjacent rooms, place door, check clearances. The Layout Problem Finder will catch swing conflicts.

---

### Cluster D: Evaluation (Components 14–17)

---

#### Component 14: Connection-Graph Quick Check

**What we proposed:** Build adjacency graph, check that every room is reachable from the entrance, no orphan rooms, no transit through bedrooms.

**What the market does:** This is space syntax (Hillier & Hanson 1984). The "room connectivity graph" approach is well-established (de las Heras et al. 2014, Survey of Architectural Floor Plan Retrieval Technology 2025). BFS step depth from entrance to each room is the standard metric. "Transit rooms" (rooms you walk through to reach another room) are flagged automatically.

**Verdict: ✅ Matches space syntax standard practice.**

**Action:** Build as planned. This runs as a quick first filter before the expensive Layout Problem Finder. Layouts that fail basic connectivity are killed early.

---

#### Component 15: Layout Problem Finder (renamed from Scorer)

**What we proposed:** ~30 checks across the 10 lived-quality dimensions (no wasted space, room sizes match function, logical flow, natural light, privacy, no bottlenecks, first-floor living, outdoor connection, storage, multi-functional). Each check returns: status, severity, affected rooms, why it matters.

**What the market does:** Most existing tools either score (single number, opaque), or compliance-check (rule pass/fail without architectural reasoning). The 2025 Mostafavi paper explicitly proposes hybrid quantitative+qualitative evaluation. Archistar PreCheck does rule-by-rule reporting for *zoning compliance*, not lived quality. **Nobody appears to be doing systematic lived-quality problem-finding for residential layouts at the consumer level.**

**Verdict: 🎯 Improving on market significantly.** This becomes a primary moat.

**Action:** Build as Problem Finder, not Scorer. The 10 categories (validated by 9 sources in previous research turn) become the structure. Each category gets 3–5 specific checks. Total ~35 checks.

**Example check:**
```
Check: Bathroom shower length adequacy
Category: Room sizes match function
Severity: Important (not Critical)
Rule: Common bath shower needs 3.5ft minimum length when wall-mounted
Status: FAIL (current shower length: 2.8ft)
Affected: Common Bath (ground floor)
Why it matters: A shower under 3.5ft requires the user to tuck their elbows
                in to wash hair. Most adult users find this uncomfortable
                within 2 weeks of moving in. Consider increasing bathroom
                depth by 8 inches or moving shower to a different wall.
```

This is the experience that distinguishes us from a "95/100 score" tool.

---

#### Component 16: Space-Auditor Quick Check

**What we proposed:** Compute carpet area, built-up area, FSI used, % space wasted (corridors + dead corners), room-area-to-purpose ratios.

**What the market does:** Standard practice in feasibility tools. TestFit and Spacio compute density/yield metrics. For consumer use, the meaningful metrics are: usable carpet area %, hallway %, dead-space %, room-by-room area report.

**Verdict: ✅ Standard practice.**

**Action:** Build as planned. Output feeds into Component 17 Ranker as numerical inputs.

---

#### Component 17: Layout Generator + Ranker (NSGA-II)

**What we proposed:** Run the Generation pipeline (Components 5–13) multiple times to produce 4–9 candidate layouts. Use NSGA-II multi-objective optimization to pick the top 3 that maximize differentiation across (privacy, light, cost). User sees the 3 most-different good layouts.

**What the market does:** NSGA-II is the academic gold standard for architectural multi-objective optimization. Validated by:
- **Operative Generative Design using NSGA-II (ScienceDirect 2023)** — uses Pymoo framework for FAR / Non-Passive Zone / Best Oriented Surfaces / Usable Open Space trade-offs.
- **NSGA-II for high-rise residential layout (Springer)** — sunlight duration optimization.
- **NSGA-II for multi-objective building design under uncertainty (MDPI 2020, Indian Ahmedabad case)** — energy + comfort Pareto frontier.
- **Comprehensive review (PMC 2025)** — confirms NSGA-II "outperforms other contemporary multi-objective evolutionary algorithms... in preserving diversity of solution set and converging to true Pareto frontier."

The clustering approach (pick top 3 differentiated layouts, not top 3 best) is exactly what the "Optimizer" paper describes: "the layouts are clustered according to a custom metric... one element from each cluster is scored and the best three layouts are finally kept."

**Verdict: ✅ Matches academic gold standard.** This is also a moat — most consumer tools just give you one layout.

**Action:** Build as planned. Critical: your existing `layout_optimizer.py` (7262 lines, 44 scoring functions never called) must be revisited. Either we wire NSGA-II into it properly, or we rewrite the ranker as a clean module. Recommend rewriting — the orphaned 44 functions are technical debt.

---

### Cluster E: Output (Component 18)

---

#### Component 18: Dual-Drawing Renderer (Working + Regulatory)

**What we proposed:** For each chosen layout, render TWO sheets: (1) Working drawing with user's actual setbacks (often 2ft on small TN plots), (2) Regulatory drawing with full NBC 5/3/3 setbacks for permit submission. Same house geometry, different setback rendering.

**What the market does:** Industry standard distinguishes Permit Set (simplified, code-compliance focused) from Construction/Working Set (full detail). Almost all serious projects produce both. India follows the same pattern (Infurnia source confirms). What's *unusual* is doing it automatically from one model — most tools require the architect to redraw the permit set separately.

**Verdict: ✅ Matches industry standard, with operational improvement.**

**Action:** Build as planned. Per your Q7 answer — generate both, walk the user through one by one.

**Risk to monitor:** The visual difference between the two sheets must be obvious — different border colors, different title block. Otherwise users will confuse them and submit the wrong one to the municipality.

---

## What Changes in the Architecture

Concretely, four updates from this validation pass:

1. **Component 15 is renamed.** "Lived Quality Scorer" → **"Layout Problem Finder"**. Output is a list of ~35 specific problems, each with status / severity / affected rooms / why-it-matters. Internal score may exist for the Ranker, but is never user-facing.

2. **Component 11 reuses the published "Optimizer" pipeline.** Grid → CSP cell assignment → cluster top solutions → insert corridors → genetic refinement. We don't need to invent this — the literature gave us a working blueprint.

3. **Component 17 must rewrite, not extend, `layout_optimizer.py`.** The orphaned 7262-line file with 44 unused scoring functions is technical debt. Clean NSGA-II implementation in 800–1200 lines using Pymoo will be more maintainable.

4. **Component 7 (Structural Grid Engine) is confirmed as a *first-class* component, not derived.** The grid is generated *before* rooms, not after. Every downstream component depends on it.

---

## What Stays the Same

The 18-component architecture is correct as designed. No components removed, no components added. The execution order is correct:

```
PLANNING:    1 (Brief) → 2 (Feasibility×2) → 3 (Negotiate) → 4 (Plot Analysis)
GENERATION:  5 (Topology) → 6 (Orientation) → 7 (Grid) → 8 (Corridor) →
             9 (Room Size) → 10 (Bath Route) → 11 (Place) → 
             12 (Vertical Align) → 13 (Door) → loop produces 4-9 candidates
FAST EVAL:   14 (Conn Graph) → 15 (Problem Finder critical-subset) → 16 (Audit)
RANKING:     17 (NSGA-II Ranker) picks top 3
DEEP EVAL:   15 (Problem Finder full) on top 3
OUTPUT:      18 (Dual Drawing) renders working + regulatory for each
```

---

## Competitive Position

After this validation, here's how BuildemUp† stacks up against the named competitors:

| Tool | Audience | Region focus | Working+Permit dual? | Indian codes? | Problem-finder vs Score? | Cost transparency? |
|---|---|---|---|---|---|---|
| Forma (Autodesk) | Developers, urban | Global, mostly US/EU | No | No | Score | No |
| TestFit | Developers, real-estate | US | No | No | Score | Pro forma yes |
| Spacio | Architects | Global | Yes | No | Score | No |
| Maket | Architects + consumers | Global | No | No | Score | No |
| Snaptrude | Architects | Global, India home base | Partial | Limited | Score | No |
| ArkDesign | Architects | Global | No | No | Score | No |
| Archistar | Cities, governments | AU, US, CA | Yes (PreCheck) | No | Rule-by-rule (compliance only) | No |
| Hypar | Architects | Global | No | No | Score | No |
| InQI | Architects | US | No | No | Score | No |
| Finch3D | Architects | Global | No | No | Score | No |
| **BuildemUp†** | **Indian homeowners** | **TN, then India** | **Yes** | **Yes (NBC, IS, TNCDBR)** | **Problem Finder** | **Yes (margin visible)** |

We are not a TestFit/Forma competitor — they serve developers and architects. We are not a Maket competitor — they serve global users with no specific code grounding. We occupy a position no current tool occupies: **consumer-facing Indian residential AI floor planner with code grounding, lived-quality problem reporting, and cost transparency.**

The market gap is real. The architecture is sound.

---

## Open Questions Still Pending

These are decisions we deferred but still need to make before coding starts:

1. **Final name.** "BuildemUp†" is placeholder. "Archimind" is taken. Six alternatives proposed (Grihya, Nakshify, Basera, Pakka, Spashta, Planora). To be decided later per Ramalingam's request.

2. **Vernacular language for the conversational brief.** Tamil + English, or English-only for v1? Tamil voice input?

3. **Cost engine accuracy for Tier 2 plots (2400–4000 sqft).** Current city_data has 8 cities. Do we need more granular sub-region data (e.g., Coimbatore vs rural TN)?

4. **Click-to-edit (Q12: full move + swap + resize + delete) — does swap mean two rooms exchange positions, or one room swaps to a different size category?** Clarification needed before we build the interaction model.

5. **Mobile vs Desktop UX (Q13: both).** Same UI scaled, or two separate UIs? Desktop has more screen for the dual drawings + problem report side-by-side.

---

## Next Steps

1. **You review this report** and confirm/adjust any of the verdicts. If you disagree with any verdict ("matches state of art" / "improves on market" / etc.), tell me where I'm wrong.

2. **You answer the 5 open questions** above (or defer specific ones).

3. **I do the 30×40 3BHK end-to-end walkthrough** I previously promised — walking a real brief through all 18 components showing input/output/decisions per component, with the working+regulatory drawing pair, the 30+ check problem report, and which 3 candidates the ranker would pick.

4. **You approve the walkthrough**, OR tell me what's broken in it.

5. **Then we start coding** — Component 7 (Structural Grid Engine) first, because every downstream placement depends on it.

---

*End of validation report. BuildemUp† is a placeholder — search for † to find every occurrence for renaming.*
