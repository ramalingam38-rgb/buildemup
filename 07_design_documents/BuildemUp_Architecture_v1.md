# BuildemUp Layout Engine — Complete Architecture
*Prepared for Ramalingam · Apr 20 2026 · grounded in 22 prior session transcripts, the existing knowledge base, and current research*

---

## How to read this document

This is a **discussion document, not a build plan.** It is meant to be argued with, marked up, and changed before a single line of code is touched. I have organised it so that you can read it in one sitting and have a clear opinion at the end of every section.

The document is structured in five parts:

> **Part 1 — Where we are today.** An honest inventory of what is built, what works, what is broken, and what is orphaned. No coding plan can be written without this.
>
> **Part 2 — The product principles that drive the architecture.** What BuildemUp is, what it is not, and the four user-facing promises that every component must serve.
>
> **Part 3 — The architecture itself.** Twelve components. For each one, I explain (a) what it does in plain English, (b) the research and theory behind it, (c) how the current code handles it, (d) the best-in-class approach from web research, and (e) how it talks to the other components.
>
> **Part 4 — Modern home considerations.** What 2026 Indian homeowners actually expect, and how the architecture reflects that without losing focus.
>
> **Part 5 — The order of work.** Honest sequencing. What to build first, what can wait, and where the risk is.

After Part 5 there are open questions for you to answer, listed in priority order.

---

# PART 1 — Where we are today

## 1.1 What is actually running on Railway right now

The live `/v3/generate` endpoint calls **three modules** in sequence: `room_rules.py`, `connection_graph.py`, `placement_engine.py`. Together that is roughly 3,800 lines of code. The pipeline does:

1. Read the brief (BHK + plot + city + facing).
2. For each floor, look up which rooms belong on that floor by BHK type.
3. Place rooms into north-to-south horizontal strips: public → service → circulation → private.
4. Inside each strip, place rooms left-to-right at fixed widths from a catalogue.
5. Run a graph check (8 rules) and a placement check.
6. Render to PNG via the `FloorPlanDrawingEngine` inside `server.py`.

That is the full path from request to rendered floor plan. Everything else in the codebase is either a helper to this path, or orphaned.

## 1.2 What is in the codebase but is *not* running

This is important because I need you to understand the state honestly before we agree on next steps.

| Module | Lines | Status | What I think we should do |
|---|---|---|---|
| `layout_optimizer.py` (the v2 monolith) | 7,262 | Orphaned. Has 44 scoring functions written but never called by `/v3/generate`. | Mine it for scoring ideas, then archive. |
| `engines/master_engine.py` and family | ~3,500 | Orphaned. Older architecture from March sessions. | Archive — superseded by the 3-module pipeline. |
| `optimizer/` package | 733 | Orphaned. | Archive. |
| `buildease_arch_intel.py` | 448 | 7 of 8 classes are stubs that return `75.0`. Only `AdjacencyGraph` is real. | Delete the stubs, keep `AdjacencyGraph`, rebuild the rest as proper components. |
| `renderer_bridge.py` (Style 2) | 346 | Built but never wired to `generate_v3.py`. Pipeline still routes through `server.py`'s old engine. | Wire it in — this is one of the highest-impact small fixes available. |
| `site_plan.py` | ~400 | Built. Generates compound wall + parking + gate. Not wired into `/v3/generate`. | Wire it in. |
| 6 knowledge modules in `knowledge/` (Ching, Neufert, Devdas Menon parametric, IS standards, CAD standards, graphic standards) | 4,618 | Real, professional, well-encoded. Imported by `buildease_kb_v2.py` but only ~10% of the rules are actually consulted by the pipeline. | Wire properly. This is one of the biggest missed assets. |
| 29 hand-curated research notes (Neufert, Ching, Alexander pattern language, NBC parts 4/8/9, IS456/875/962/1893, Murthy, Punmia, Varghese, etc.) | 14,731 | Read by Claude during code generation; not read by the running engine. | These are training-grade content. Use them. Section 3.12 has the plan. |

## 1.3 The fifteen known problems

I list these because they are the failure modes the architecture must prevent. They are not a to-do list — they are an honest record of where the engine has hurt you in the past. Each one has a corresponding component in Part 3 that solves it at the root.

> 1. Strip topology only. The engine cannot produce central-spine, courtyard, or L-shape layouts. On any plot under 25ft wide, the strip topology produces wasted corridors and cramped rooms.
> 2. Passage had no door logic originally. Fixed with P1–P5 conditions and `graph_geom_check`, but the fix is procedural, not principled.
> 3. Bathroom transit bug: bathrooms ended up between corridor and bedroom, forcing people to walk through the bath to enter the bedroom.
> 4. Car parking missing from rendered output. `site_plan.py` exists but is not wired.
> 5. The 30×40 dimensions are hardcoded inside `placement_engine.py` (`mw=10.0, cw=6.0, btw=3.0`). The `btw=3ft` violates NBC 1.2m bathroom minimum. The `cw=6ft` violates 2.4m habitable width minimum. This is the source of the 57sqft bedroom_3 bug.
> 6. L-shaped master bedroom is stored as two separate `PlacedRoom` entries with the same name. The space efficiency auditor counts each one independently and flags the smaller piece as a sub-minimum bedroom. The renderer originally drew a visible line between them.
> 7. Common bathroom shower not drawn at 6ft depth. Renderer threshold suppresses small-room labels.
> 8. Style 2 renderer never pushed to Railway.
> 9. Seven of eight architectural-intelligence classes are empty stubs returning constant scores.
> 10. Click-to-edit backend exists; UI does not.
> 11. The conversational "dream home" text gets dropped between brief input and generation — only structured BHK survives.
> 12. Railway-vs-local code drift. Bug fixes made locally without git commits get lost on next deploy.
> 13. BuildEase / BuildemUp branding is inconsistent across files.
> 14. The "drawing type" working/regulatory toggle silently falls back to Bangalore defaults for non-Bangalore cities.
> 15. Scoring measures technical validity (does the bedroom touch a bath? yes → 100). It does not measure lived quality (would a family actually like this layout? unknown).

## 1.4 The deepest single insight from the prior sessions

You said it on Apr 17, looking at a 20×30 first-floor design that had a wasted west corridor:

> *"Why didn't our engine see this as the best possible layout?"*

The answer the previous session gave is the most important sentence in this whole document:

> **The engine places rooms first and thinks about architecture second. It never considers topology — whether the floor should be a strip, a central spine, an L, or a courtyard — before it starts placing.**

Every component below is in service of inverting that. The engine must think about *how the floor wants to be organised* before it places a single room.

---

# PART 2 — Product principles

These are the things I have inferred from the 22 sessions and from your direct statements. I list them explicitly so we can argue about any I have got wrong before they shape the architecture.

## 2.1 What BuildemUp is

> **A floor plan engine that produces three honest layouts, with full cost transparency and contractor-question education, for Indian homeowners on plots 600–4000 sqft.**

The key words:

- **Honest.** The engine never silently overrides a user preference. If it cannot do what was asked, it says so and explains why. If it makes a trade-off, the trade-off is named.
- **Three layouts.** Not one. Not ten. Three, differentiated on a clear axis (privacy / light / cost), so the user has a real choice without analysis paralysis.
- **Full cost transparency.** The contractor margin line is visible by default. Materials, labour, finishes, and contractor markup are all separately shown. This is your moat — no other tool in the Indian market does this.
- **Contractor-question education.** Every output includes a printable PDF of "20 questions to ask your contractor about this house". This is the shareable hook. You said it cleanly: BuildemUp protects homeowners from opaque contractor pricing.
- **600–4000 sqft.** Not skyscrapers, not bungalows on 1-acre plots. The Indian middle-class home — which is what the country is actually building.

## 2.2 What BuildemUp is not (right now)

- Not a Vastu engine. Vastu is explicitly out for now per your decision. The engine uses circulation, sunlight, and ventilation as its three principles. Vastu can be added later as a fourth principle if you decide to.
- Not a free-form architectural sketch tool. The user does not draw walls. The engine generates layouts; the user clicks rooms to swap, resize, move, or delete.
- Not a contractor marketplace. The output PDF helps the user *talk to* contractors. It does not connect to them.
- Not a project management tool. Once the layout and BOQ are produced, BuildemUp's job is done.

## 2.3 The four promises every component must serve

Whatever component we build, it has to advance one of these four promises. If a component does not, it should not be built.

> **Promise 1 — "It will look like the home I imagined, only better."** The engine produces layouts the user feels is *better than what they imagined*, not just acceptable. This is the design bar.
>
> **Promise 2 — "It will tell me, in plain language, what each rupee buys me."** Cost transparency, with the contractor margin line visible by default.
>
> **Promise 3 — "It will protect me from the contractor I do not yet know how to talk to."** The output includes a contractor-question PDF and a working drawing labelled with every material so the user can verify on site.
>
> **Promise 4 — "It will be honest about what is and is not possible on my plot."** No silent compromises. No fake 100/100 scores. If the bedroom does not fit, the engine says so and offers a real choice.

## 2.4 The user–engine relationship (locked from prior sessions)

You agreed on this exact relationship pattern:

| User input type | Engine behaviour |
|---|---|
| **Hard rule** (NBC structural minimums, structural-grid feasibility) | Engine *refuses* and explains the rule the request violates. |
| **Strong preference** (Vastu, solar, "I want master bedroom on west") | Engine *obeys* and *warns* about the trade-off. |
| **Soft preference** ("I want it to feel open", "I like natural light") | Engine *quietly optimises* based on the brief. |
| **Anything else** | Engine fills with sensible defaults from the knowledge base. |

The forbidden mode — and this comes up repeatedly in your past frustrations — is **silent override**. The engine must never quietly do something different from what was asked without saying so.

---

# PART 3 — The architecture: twelve components

The engine has twelve components. Components 1, 2, and 3 already exist and work. Components 4–10 are new but well-defined. Components 11 and 12 are infrastructure layers around the engine, not part of the placement loop itself.

The **order of execution matters** and is the single most important thing in this whole document. Previous-Claude got this wrong on at least three occasions by placing rooms before deciding on topology, which is exactly what produced the layouts you found unsatisfactory. Here is the correct order:

```
1. CONVERSATIONAL BRIEF          → user's intent in their words
2. FEASIBILITY                   → does it physically fit?
3. TRADE-OFF NEGOTIATION         → user resolves conflicts
4. PLOT ANALYSIS                 → orientation, road, setbacks
5. TOPOLOGY SELECTOR             → strip / spine / L / courtyard
6. ORIENTATION PRIORITY ENGINE   → which face gets which zone
7. CORRIDOR DESIGN ENGINE        → corridor exists, where, how wide
8. PLOT-AWARE ROOM SIZER         → assign each room dimensions
9. PRE-PLACEMENT BATHROOM ROUTER → bathroom positions decided
10. PLACEMENT ENGINE             → place rooms (existing module)
11. DOOR PLACEMENT ENGINE        → which wall each door goes on
12. CONNECTION GRAPH (existing)  → check 4 morning paths, depths
13. SPACE EFFICIENCY AUDITOR     → no orphan space, no dead corridor
14. RENDERER                     → working drawing + regulatory drawing
```

I am going to walk through each of components 1–13 below. Component 14 (renderer) is largely solved by the existing `renderer_bridge.py` once it is wired in.

---

## Component 1 — Conversational Brief

### What it does

The user describes their dream home in their own words, in any combination of typed text, room-list clicks, voice, or photo upload. Claude (the LLM) extracts a structured brief, asks at most 4–5 clarifying questions, and confirms the brief back to the user before anything else runs.

### Why this design

You stated in the Apr 16 session, very clearly, that this is the most important part of the whole product, because *if BuildemUp misunderstands the brief, every layout it produces will be wrong, no matter how good the engine is.* I agree. The conversational brief is the input bottleneck — get it right and everything downstream becomes possible.

The research backs this. The research literature on AI floor plan tools converges on one finding: methodology acknowledges user expectations and translates them into realistic, adaptable plans. The hardest part is the *translation*. People do not think in room names and square feet. They think in:

> *"My parents need to be comfortable downstairs, and the kids need their own space upstairs near our bedroom but not in it, and I want the kitchen open to where we eat so I can see them while I cook."*

A form with checkboxes cannot capture that. A conversation can.

### Three layers of "understanding"

| Layer | Example | How extracted |
|---|---|---|
| **Facts** | "30×40 plot, north facing, 2 floors" | Direct extraction with a regex/LLM-pass. Easy. |
| **Preferences** | "Open kitchen", "kids need own space" | LLM interpretation against a vocabulary the system understands ("open" → kitchen+dining no door; "kids own space" → children bedrooms on same floor, away from master). |
| **Constraints** | "Bedrooms must be private" (unstated but always assumed) | Hardcoded from `room_rules.py`. The user does not say it; the engine knows it. |

### What the current engine does

The current engine takes `bhk="3bhk"` and ignores almost everything else. The conversational brief input was discussed but never built. This is one of the biggest missing pieces.

### Best-in-class approach

The current state of the art is the **constrained chat → JSON → engine** pattern, used by Maket.ai, Finch3D's enterprise tier, and the Text2FloorEdit research framework. The chat is bounded:

- The system prompt for Claude defines exactly what fields it must extract.
- Claude is forbidden from generating layouts itself — it only extracts the brief.
- Claude must ask at most 4–5 questions, only on missing fields, and must show a confirmation card.
- The output is a strict JSON schema the layout engine can consume.

### The interface

```json
{
  "plot": { "w_ft": 30, "d_ft": 40, "facing": "N",
            "city": "chennai", "pincode": "600028" },
  "floors": 2,
  "ground_floor_rooms": [
    { "type": "living_room" },
    { "type": "kitchen", "preferences": { "openness": "open_to_dining" } },
    { "type": "bedroom", "purpose": "parents", "attached_bath": true },
    { "type": "pooja_room" },
    { "type": "guest_wc" }
  ],
  "first_floor_rooms": [
    { "type": "master_bedroom", "attached_bath": true,
      "preferences": { "balcony": true } },
    { "type": "bedroom", "purpose": "child", "attached_bath": true,
      "qty": 2 },
    { "type": "home_office" },
    { "type": "family_lounge" }
  ],
  "terrace": [{ "type": "yoga_studio" }],
  "global_preferences": {
    "style_words": ["open", "modern", "warm"],
    "must_haves": ["solar_ready", "rainwater_harvesting"],
    "avoid": ["dark_corners"]
  },
  "confirmed_by_user_at": "2026-04-20T..."
}
```

This JSON is the contract. Everything downstream consumes it. Nothing downstream queries the user again.

### Build size: ~2 days

A frontend chat widget + a Claude system prompt + a JSON schema validator. The engine stays untouched.

---

## Component 2 — Feasibility (4-layer)

### What it does

Before any layout is generated, the feasibility module asks four questions in this order:

1. **Area:** Does the total sqft of requested rooms fit within usable building area after setbacks?
2. **Floor distribution:** Are the right rooms on the right floor? (e.g. parents on GF if requested.)
3. **Dimensional:** Even if sqft fits, can the rooms physically fit side-by-side within the plot width?
4. **NBC compliance:** Are all rooms above the legal minimum size?

The output is a structured report. If everything passes → straight to Component 4. If anything fails → pass to Component 3 (Trade-off Negotiation).

### Why all four layers matter

This came directly from your Apr 16 session. You correctly pointed out:

> *"On a 23.4ft wide plot, three bedrooms cannot fit side by side regardless of sqft."*

The current engine does Layer 1 (rough sqft check) only. It misses Layer 3 entirely. That is why on narrow plots it produces overflowing rows or cut-off rooms — it never asks "can these things actually sit next to each other?"

### What the current engine does

`feasibility.py` exists (483 lines), but only checks total sqft against built-up area. Layers 2, 3, and 4 are not implemented. The 4-layer framework was discussed in the Apr 16 session but never built.

### Best-in-class approach

Constraint Satisfaction Problems (CSP) literature has a clean answer here: arc-consistency before search. Before you try to find a layout, prove that each room *individually* can fit somewhere. If you cannot prove it, you do not search — you tell the user the constraint that fails.

For BuildemUp this means: every room has a `min_width_ft`, `min_depth_ft`, `min_sqft`. Run these against the plot's usable dimensions. If any one is impossible, name it and stop.

### The interface

```python
def check_feasibility(brief: Brief, city_rules: CityRules) -> FeasibilityReport:
    """
    Returns:
      FeasibilityReport(
        passes=False,
        layer1_area={'gf_over_sqft': 194, 'ff_over_sqft': 0},
        layer2_distribution={'conflicts': [...], 'suggestions': [...]},
        layer3_dimensional={'conflicts': ['3 bedrooms need 30ft of width on 23.4ft plot']},
        layer4_nbc={'violations': []},
        what_fails_first='layer3_dimensional',
        plain_english="On your 30×40 plot, the 23.4ft usable width allows 2 bedrooms side by side, not 3."
      )
    """
```

### Build size: ~3 days

The math is simple. The interface to the conversational layer (so trade-offs can be discussed) is the more interesting bit.

---

## Component 3 — Trade-off Negotiation

### What it does

When feasibility fails, this component does *not* refuse the brief. It explains what fails, in plain English, and presents a small number of choices the user can pick between. Each choice is a real architectural option, not a generic "make it smaller".

### Why this design

This is the heart of your product philosophy. From the Apr 16 session you said unambiguously:

> *"There should be trade off negotiation because it gives the user to decide how to manage this issue."*

That is correct. It is also what the research literature confirms: every professional tool generates and flags rather than blocks. Even the most advanced AI floor plan systems do not refuse to generate — they generate and apply a scoring/warning layer on top.

The protected-priority order you locked in is:

```
Bedrooms > Kitchen > Living > everything else
```

When suggesting trade-offs, the engine never suggests reducing bedrooms or kitchen first. It always suggests reducing or moving "everything else" before touching the protected rooms. This is your philosophy and it is the right one.

### What the current engine does

Nothing. There is no trade-off negotiation today.

### Best-in-class approach

The way Finch3D handles this is instructive: they show the user 3–5 alternative layouts each satisfying constraints differently, with live metrics (GFA / GIA / NIA / daylight) attached to each. The user picks, then refines. This is the right model for BuildemUp's negotiation step.

For BuildemUp, the negotiation interface is more constrained: it presents a single conflict at a time (the highest-priority one) with 3–4 specific resolution options. After the user picks, the engine re-runs feasibility and if there is still a conflict, asks the next one. This is gentler than dumping all conflicts at once.

### The interface

The negotiation is owned by the conversational layer, not by code. Component 3 is a *decision tree* the LLM walks through, with the feasibility report as input. The LLM picks the highest-priority conflict, generates 3–4 resolution options grounded in the actual plot, and asks the user. The user's choice is appended to the brief JSON, and feasibility re-runs.

### Build size: ~3 days

Most of the work is the LLM prompt that translates feasibility-report-into-options. The decision tree itself is small.

---

## Component 4 — Plot Analysis

### What it does

Reads the plot dimensions, road-facing direction, city, pincode, and computes:
- Usable building area after setbacks (front / side / rear from city rules).
- Plot type: corner, mid-street, end, irregular.
- Road position (which compass face).
- Sun path for the city (latitude-based) — which face gets morning sun, which gets harsh afternoon sun.
- Wind direction (from CITY_DATA).
- Climate zone (from CITY_DATA).
- Seismic zone (from CITY_DATA).

This output is a `PlotContext` object that every downstream component consumes.

### What the current engine does

This is partially in `feasibility.py` and partially hardcoded. It needs to be its own module with a clean output.

### Best-in-class approach

This is solved territory. Autodesk Forma's Site Automation does exactly this — generates building/circulation layouts within a site boundary using initial massing, then refines. The Indian-specific bit is the city rule database (FAR, setbacks, ground coverage) and the latitude-correct sun path. Both already exist in your CITY_DATA but need to be properly exposed.

### The interface

```python
@dataclass
class PlotContext:
    plot_w_ft: float
    plot_d_ft: float
    facing: str                     # "N", "S", "E", "W", "NE", etc.
    usable_w_ft: float
    usable_d_ft: float
    setback_front_ft: float
    setback_side_ft: float
    setback_rear_ft: float
    plot_type: str                  # "corner", "mid_street", "end", "irregular"
    sun_path: SunPath               # morning_sun_face, harsh_face, soft_face
    wind: Wind                      # primary_direction, secondary
    climate_zone: str               # from CITY_DATA
    seismic_zone: str
    city_authority: str             # "CMDA", "BBMP", "BMC", etc.
    far_max: float
    ground_coverage_max: float
```

### Build size: ~1 day

Most of the data exists in `CITY_DATA`. This is wiring + the sun-path calculation.

---

## Component 5 — Topology Selector ★ critical

### What it does

This is the component whose absence caused most of your past frustration. Before any room is placed, the engine decides: **what topology should this floor have?**

Four candidate topologies:

| Topology | When to use | Visual |
|---|---|---|
| **Strip** | Wide plot, room count fits in one row | Public band → service band → circulation band → private band, north to south |
| **Central spine** | Narrow plot, multiple rooms need access from both sides | Corridor runs north-to-south through the centre, rooms flank east and west |
| **L-shape** | Corner plot, two streets, two entries possible | Rooms wrap an L-shaped corridor |
| **Courtyard** | Large plot (40×60+), needs internal light | Rooms surround a central open space |

The selector picks one (or two for comparison) based on plot dimensions, room count, and bedroom count.

### Why this is the single most important component

Quoting your Apr 17 session, after I drew a wasted-corridor first floor and you saw a better central-spine layout immediately:

> *"Why didn't our engine see this as the best possible layout?"*

The answer was, and is: because it never considered topology. It only knew "strip". The fix is this component.

### What the current engine does

`topology_selector.py` exists in the codebase as part of "Fix 1" from the Apr 17 session, with three options: NO_CORRIDOR, STRIP, CENTRAL_SPINE. L-shape and Courtyard are not implemented. The decision logic is also incomplete — it picks based on a small ruleset rather than evaluating multiple candidates.

### Best-in-class approach

The research literature converges on **generate-and-rank**. Generate 2–3 candidate topologies for the floor, score each against the brief, pick the best. This is exactly what House-GAN++ does at the topology level (different bubble diagrams produce different layouts) and what Finch3D does ("explore volume and populate that volume with plans").

For BuildemUp the decision rules are simpler than ML — they can be expressed as a small decision table:

```
if plot_w_ft >= 26 and bedroom_count_on_floor <= 2:
    candidates = [STRIP]
elif plot_w_ft < 22 and bedroom_count_on_floor >= 2:
    candidates = [CENTRAL_SPINE]
elif plot_type == "corner":
    candidates = [L_SHAPE, STRIP]
elif plot_w_ft >= 40 and plot_d_ft >= 60:
    candidates = [COURTYARD, STRIP]
else:
    candidates = [STRIP, CENTRAL_SPINE]   # try both, score, pick winner
```

When two candidates score similarly, both are passed downstream and we end up with two of the three layouts BuildemUp shows the user.

### The interface

```python
def select_topology(plot: PlotContext, floor_rooms: List[RoomReq]) -> List[Topology]:
    """
    Returns 1-3 candidate topologies, sorted by predicted suitability.
    Each candidate is fully described — corridor position, room zone assignments,
    structural-grid implications.
    """
```

### Build size: ~5 days

Each topology needs to be fully encoded — the strip already exists in `placement_engine.py`, central-spine exists in `general_placer.py`. L-shape and courtyard are new. Plus the scorer to rank candidates.

---

## Component 6 — Orientation Priority Engine

### What it does

Once topology is decided, this component decides which face of the building gets which zone. For a Bangalore north-facing plot, the answer is roughly:

| Face | Best for | Why |
|---|---|---|
| **N** (road, indirect light) | Living, balcony, home office | Soft consistent light, no glare |
| **E** (morning sun) | Kitchen, pooja, children bedrooms | Gentle warm light at the right hours |
| **S** (rear, strong summer sun) | Bedrooms (with shading), utility | Privacy + shaded morning light |
| **W** (harsh afternoon) | Staircase, store, utility | Spaces that don't need comfort |

This is your "Sunlight" principle from the 3-principles framework — it gets formalised here.

### Why latitude matters

The above table is correct for Bangalore (12°N). For Chennai (13°N) the difference is small. For Delhi (28°N) it changes meaningfully — sun is higher in summer, lower in winter, and the south face becomes harsher in summer than in Bangalore. The engine should use the city's latitude to compute the correct face-to-zone preferences, not hardcode Bangalore's pattern.

### What the current engine does

Hardcoded to Bangalore N-facing inside `room_rules.py` and `placement_engine.py`. Other facings/cities are stubbed.

### Best-in-class approach

Climate-aware design tools (Climate Consultant, Ladybug Tools) compute sun path from latitude and date. For BuildemUp we don't need full hourly simulation — a simplified "morning / midday / afternoon / evening" map per face per season is enough. The Neufert orientation rose in your research notes already provides this in tabulated form.

### The interface

```python
def get_orientation_preferences(plot: PlotContext) -> Dict[str, FacePreference]:
    """
    Returns for each face (N/S/E/W) and each room type a preference score:
      0   = avoid
      1-4 = acceptable to good
      5   = ideal
    """
```

### Build size: ~2 days

The data structure already exists in `room_rules.py`. Need to make it latitude-aware and pull the rest of the cities into the table.

---

## Component 7 — Corridor Design Engine

### What it does

Decides three things about every floor's circulation:
1. **Does a corridor exist on this floor?** Some floors don't need one (the GF of a 20×30 with one bedroom).
2. **Where is it?** Edge (along one wall), central (running through the middle), or L-shape (turning a corner).
3. **How wide?** Minimum 0.9m for service, 1.2m for primary circulation per Ching's hierarchy.

The corridor decision is made *before* rooms are placed because **the corridor decides where the staircase is, and the staircase decides where rooms can go.** Previous-Claude consistently got this backwards.

### Why this design

Quoting from the Apr 17 session, after you described the better 20×30 first-floor layout:

> *"Staircase first → it decides where the corridor is. Corridor next → it decides where bedrooms go. Bedrooms last → they fill the remaining space on each side."*

That is exactly right. The current engine does the opposite — places rooms first, treats corridor as leftover.

### What the current engine does

Corridor is hardcoded in `general_placer.py` to specific widths. Position depends on topology but is not really designed — it is a leftover strip after rooms are placed.

### Best-in-class approach

Ching's circulation hierarchy from your `ching_fso.py` knowledge module is exactly the right framework:

| Type | Width | Character | Used for |
|---|---|---|---|
| Primary | min 1.2m | Open, visible, welcoming | Entry → living → dining |
| Secondary | min 0.9m | Private, away from public | Bedroom → bathroom |
| Service | min 0.75m | Functional, back-of-house | Kitchen → utility → back door |

The corridor design engine assigns one of these three types to each circulation segment, then sizes accordingly.

### The interface

```python
def design_corridors(topology: Topology, floor_rooms: List[RoomReq],
                     plot: PlotContext) -> CorridorPlan:
    """
    Returns:
      CorridorPlan(
        segments=[
          CorridorSegment(type='primary', x=0, y=12, w=23, d=4, serves=['living','passage']),
          CorridorSegment(type='secondary', x=2, y=18, w=3, d=8, serves=['bedroom_1','bath_1']),
        ],
        staircase_position=(x, y, w, d),
        total_circulation_sqft=92,
      )
    """
```

### Build size: ~4 days

Includes the staircase placement logic — staircase becomes a first-class structural element, not a generic room.

---

## Component 8 — Plot-Aware Room Sizer

### What it does

Each room has a `min`, `ideal`, and `max` size from the knowledge base. Until now the engine has used `ideal` everywhere, then truncated whatever overflows. This is wrong.

The correct approach: given the topology, the corridor plan, and the leftover area, the sizer assigns each room an *actual* size proportional to (a) its priority and (b) the available area, while respecting min and max.

### Why this design

The 90-sqft master bath that you correctly pointed out as "hotel-level luxury on a 20×30 plot" is exactly the failure this component fixes. The current engine gave the bath the full 18ft width because that is what the zone allowed. The correct behaviour is to *cap* the bath at its sensible max (7ft wide, ~50 sqft) and give the surplus back to the bedroom or to the next room.

You also said it cleanly:

> *"The splitter always protects the more important room first. Bedroom minimum is guaranteed before bathroom gets any space."*

This is a *priority-protected* sizer. The order is: bedrooms (Neufert minimum protected first) → kitchen → living → bath → corridor → utility → store. The first rooms in the priority order get their minimums met before later rooms get any allocation beyond their minimums.

### What the current engine does

`zone_splitter.py` does part of this for service-zone splits but is not generalised. Many room max-widths are still implicit in the placement code rather than data.

### Best-in-class approach

This is a *constrained allocation* problem with priorities. The clean formulation:

```
maximize: Σ priority(r) × size(r)
subject to:
  size(r) >= min(r)        for all r
  size(r) <= max(r)        for all r  
  Σ size(r) <= available_area
```

This can be solved with a greedy algorithm (allocate min to all → distribute surplus to highest-priority rooms first, capped at max) in O(n log n). No need for an LP solver for a problem this small.

### The interface

```python
def size_rooms(rooms: List[RoomReq], available: AvailableArea,
               priority: PriorityOrder) -> List[SizedRoom]:
    """
    Each SizedRoom has: name, w_ft, d_ft, position_hint
    Guarantees: size >= min for all rooms, or returns infeasibility report.
    """
```

### Build size: ~3 days

Including the auditor that confirms allocations sum correctly and no min-violations exist.

---

## Component 9 — Pre-Placement Bathroom Router

### What it does

Decides where each bathroom goes *before* any room is placed. This is "Fix 3" from the Apr 17 session.

Three rules:
1. **Private bathroom (master_bath)**: inside the master suite zone, accessed from master bedroom only, must have an external wall (for plumbing vent + window).
2. **Common bathroom**: opens to corridor directly, never inside any bedroom zone, must have a shower if the brief asked for one.
3. **Attached bedroom bathrooms**: placed on the *far side* of the bedroom from the corridor, so the path is `corridor → bedroom → bathroom`, never `corridor → bathroom → bedroom`.

### Why this design

The "bathroom transit bug" — bathroom ends up between corridor and bedroom — is one of the named failure modes. Routing bathrooms before placing other rooms prevents it from happening at all. This is a clean solution.

The component also enforces a structural constraint that `room_rules.py` cares about but no other component checks: bathrooms need plumbing access. On a 2-floor home, the common bathroom on FF should sit roughly above the kitchen or another bath on GF, so plumbing stacks vertically. This single rule reduces plumbing cost by 20–30%.

### What the current engine does

`bathroom_router.py` exists. It implements the three rules above. It is not yet plumbing-stack-aware.

### Best-in-class approach

In commercial AEC software (Revit MEP), plumbing stack alignment is a well-known optimisation. For BuildemUp the rule is simple: when placing a FF bathroom, prefer positions where there is a GF bathroom or kitchen directly below.

### The interface

```python
def route_bathrooms(rooms: List[SizedRoom], topology: Topology,
                    other_floor_layout: Optional[FloorPlan]) -> BathroomRouting:
    """
    Returns explicit position rules for each bathroom:
      bathroom_1 → 'east_of_bed1'
      common_bathroom → 'corridor_north_face'
      master_bath → 'inside_master_suite_west'
    """
```

### Build size: ~2 days (plumbing stack adds ~1 more)

---

## Component 10 — Placement Engine ★ existing, needs upgrades

### What it does

This is your current `placement_engine.py` (520 lines) plus `general_placer.py` (819 lines). It takes the topology, sizing, corridor plan, and bathroom routing — and actually places every room as a rectangle with `(x, y, w, d)`.

### What needs to change

The current engine does *all* the work — picks topology, sizes rooms, routes bathrooms, places. After Components 5–9 are extracted, the placement engine becomes much smaller and more reliable. It just executes a plan that has already been decided.

The remaining responsibilities:
- Translate the abstract plan into precise rectangles.
- Snap to the structural grid (from `parametric_layout.py`).
- Handle the edge cases of L-shaped rooms (the master-bedroom-as-two-rectangles bug).
- Output `List[PlacedRoom]` for the renderer.

### What the current engine does well — keep this

The `PlacedRoom` dataclass and the `(x, y, w, d, color, zone_type)` representation are clean and should stay. The connection to the `FloorPlanDrawingEngine` works.

### What the current engine does poorly — fix this

- 30×40 dimensions are hardcoded. After Components 4–8 run, these come from data, not constants.
- No structural-grid snapping. Rooms drift off the column lines that `parametric_layout.py` has computed.
- L-shaped rooms are stored as two `PlacedRoom` entries with the same name, breaking auditors. The fix from your Apr 20 session — render two adjacent same-named rectangles as one polygon, no internal line — should also apply at the data-model level: store an L-room as one entity with a polygon path, not two rectangles.

### Build size: ~3 days to refactor (code stays mostly intact, interfaces change)

---

## Component 11 — Door Placement Engine

### What it does

For every room, decides which wall its door goes on, where on that wall, and which way it swings.

### Why this matters

Doors are not decorative. A door on the wrong wall:
- Blocks a window's light.
- Forces furniture into bad positions.
- Creates visual privacy violations (line-of-sight from front door into bedroom).
- Breaks the connection graph (the room is now connected to a different neighbour than the engine thinks).

### What the current engine does

`general_placer.py` has door-position hints inside `room_rules.py` ("door on south wall, never east/west"). These are partially honoured. There is no dedicated component that does this systematically, and no door-swing-conflict checker.

### Best-in-class approach

The space syntax literature (Hillier, Hanson) shows that door position has more effect on movement patterns than wall position. The standard algorithm:

```
for each room R:
  candidates = walls(R) that adjoin a corridor or another room R needs to connect to
  filter: wall must be at least 0.9m wide (door + clearance)
  filter: wall must not block a window if window already placed
  filter: door swing must not conflict with door swings of adjacent rooms
  pick: the candidate that minimises step-depth from entry to R via this door
```

### The interface

```python
def place_doors(rooms: List[PlacedRoom], corridor: CorridorPlan,
                rules: Dict[str, RoomRule]) -> List[Door]:
    """
    Each Door has: room_id, wall_face, position_along_wall, width_ft, swing_direction
    """
```

### Build size: ~3 days

---

## Component 12 — Connection Graph ★ existing

### What it does

Reads the placed rooms and doors, builds a graph where nodes are rooms and edges are doors, and runs the checks you and previous-Claude designed:
- Step depth from front door (BFS).
- 4 simultaneous morning paths (parents, master, children, guest WC).
- Line-of-sight visual privacy.
- Acoustic isolation (bedrooms not next to staircase, kitchen, or each other badly).
- Transit-room check (no bedroom is a passthrough).

This module exists (`connection_graph.py`, 917 lines) and works. Score is 100/100 on good layouts and 35/100 on deliberately bad ones. It is the most mature component in the system.

### What needs to change

Two upgrades:

1. **Take real doors as input, not inferred ones.** Right now it infers doors from shared walls. Once Component 11 produces actual doors, the graph should consume those.

2. **Add an integration value computation.** Step depth tells you how far each room is from the entry. Integration value (from Hillier's space syntax) tells you how *central* each room is — i.e. how easily reachable from any other room. Living rooms should have the highest integration. The research is unambiguous: layouts where living rooms are highly integrated feel more habitable. This is a single extra computation on the graph and gives the scorer a much more discriminating signal than "bedroom is at depth 3 ✓".

### Best-in-class approach

The space syntax literature (Hillier 1984, plus the recent SSPT 2026 paper) shows that the right metric for layout quality is **public-space dominance**: the living/entry/dining rooms should have the highest integration values, and the difference between public-room integration and private-room integration should be large. SSPT uses this as a reward signal for reinforcement-learning floor-plan training. For BuildemUp it is the right scoring metric.

### The interface

The existing one is fine. The output adds an `integration_values` field per room.

### Build size: ~2 days for the upgrade

---

## Component 13 — Space Efficiency Auditor

### What it does

After everything is placed, audit:
- **Orphan space**: any sqft not assigned to a room or corridor — flag it.
- **Dead corridor**: corridor segments that connect to nothing useful at one end — flag.
- **Corridor-to-room ratio**: should be 8–15% of total sqft. Above 15% is wasteful.
- **Wall-to-room ratio**: total wall area should be < 22% of total sqft.
- **Plot efficiency score**: usable room area / built-up area, shown to the user as a selling point.

### Why this design

You suggested this directly in the Apr 17 session as "Idea 1 — Plot Efficiency Score (visible to client)". It becomes a competitive differentiator: clients can see that BuildemUp designs are 8–12% more efficient than industry average.

### What the current engine does

Partial. There is a space auditor that catches orphan space and dead corridors. The plot-efficiency score is not yet exposed.

### Best-in-class approach

This is straightforward computational geometry. Total polygon area − sum of room polygons = orphan area. The trick is presenting it as a *positive* (BuildemUp efficiency vs industry average) rather than a list of problems.

### Build size: ~2 days


---

# PART 4 — Modern home considerations (2026)

You asked specifically about how modern homes are built, what 2026 buyers expect, the direction the industry is moving, and which advanced technologies in concrete, electrical, plumbing, etc. should be considered. Here is what the research actually says, organised so you can decide which of these to bake into the architecture and which to leave for later.

I want to be direct about one thing first: **most of these are not core to the floor plan engine.** The engine's job is to produce a great floor plan with good cost transparency. The technologies below are layered on top — as upsells, education content, or BOQ options. I will mark each as `[CORE]` (must be in the architecture from day one) or `[LAYER]` (can be added as a feature later).

## 4.1 What 2026 Indian buyers actually expect

The research shows convergence on a few themes. I am summarising the source material here, not adding my opinion:

**Smart home is no longer luxury — it is baseline.** Indian buyers in 2026 evaluate properties partly on smart-home readiness. Specifically: Matter 2.0 wireless automation (no rewiring), biometric door locks, video door phones, motion sensors, contextual AI that adjusts air/humidity/light per occupancy. `[LAYER — show as ready/not-ready in BOQ]`

**Sustainability is mandatory, not optional.** Solar-integrated tiles or balcony railings, greywater recycling (50% shower water reused for flushing), rainwater harvesting (mandatory in many states), biophilic LED green walls. Tied to India's net-zero 2070 goal. `[CORE — solar-ready and rainwater-ready should be checked in feasibility]`

**Open plan is ending; "broken plan" is replacing it.** The era of fully open floor plans is fading. Glass partitions and movable bookshelves create quiet WFH zones. Spice/wet kitchens (smaller, heavy-duty) are separated from social/pristine kitchens. `[CORE — affects room rules: kitchen now sometimes has two rooms]`

**Earthy palettes replacing cold greys.** Terracotta, sage green, ochre, warm beige. Athangudi tiles, wooden jalis. `[LAYER — affects BOQ finish options]`

**WFH is permanent.** Smart study/work rooms with soundproofing and hidden tech are now standard requests. `[CORE — home_office is a first-class room type, not an "extra"]`

**Curved furniture, multi-functional pieces, mezzanine storage, cloffices.** `[LAYER — affects interior design, not floor plan]`

## 4.2 Construction technology — direction of travel

These are the directions the industry is moving. Some are relevant to BuildemUp's BOQ; some are too early-stage for residential.

**Precast / prefab concrete (Magicrete-style):** Bathroom pods, wall panels, hollow-core slabs, prefab staircases. 50% faster construction, 90% less waste, IS-compliant. APAC fastest-growth region. Enables a new BuildemUp product tier: "prefab-ready" homes that can be priced 25–35% lower than fully cast-in-situ. `[LAYER — important upsell for v2]`

**Self-healing concrete with hybrid capsules:** 75–90% crack-healing efficiency. Currently used in bridges, nuclear, offshore. Residential adoption is still 3–5 years out. `[LAYER — mention in education PDF, not in BOQ yet]`

**UHPC (ultra-high-performance concrete) and carbon-reinforced concrete:** Enable slimmer slabs and longer spans. Currently expensive — only relevant for premium tier. `[LAYER]`

**Low-carbon and geopolymer concrete:** Europe-driven, spreading in India for ESG-conscious buyers. `[LAYER — add as a finish option in BOQ]`

**3D construction printing for complex precast shapes:** Curved walls, custom facade panels. `[LAYER — luxury tier only]`

**Digital twins and AR walkthroughs:** Pre-construction 3D walkthroughs so the client sees the house before bricks are laid. Reduces material waste, eliminates "this is not what I imagined" complaints. `[CORE — should be a feature in v2 — Three.js or WebXR walkthrough of the generated layout]`

**BIM + precast integration:** Now an operational requirement for any commercial project. For residential, BIM is overkill. BuildemUp's DXF output is enough. `[Skip — BIM is not residential-relevant]`

## 4.3 MEP (mechanical, electrical, plumbing) — what to integrate

The MEP services market is growing 10.5% CAGR globally and faster in APAC. The trends that matter for BuildemUp:

**Modular MEP / prefab plumbing stacks:** Bathroom pods come pre-plumbed. Wall panels come pre-wired. This is residential-feasible now in India. Affects BuildemUp because: if the engine knows the user is choosing prefab, plumbing-stack alignment between floors becomes a *required* output, not a nice-to-have. `[CORE — Component 9 already considers stack alignment]`

**Smart electrical (Matter 2.0):** Wireless automation, no rewiring. Buyers expect it. The architecture implication is small: BuildemUp should produce an "electrical plan layer" on the floor plan showing recommended switch positions, sensor positions, and Matter-hub location. `[LAYER — v2]`

**Greywater recycling, low-flow fixtures, rainwater harvesting:** Greywater systems reuse 50% shower water for flushing. Rainwater is mandated in many Indian states. The engine should:
- Detect from CITY_DATA whether rainwater is mandatory.
- Reserve a sump/tank position in the site plan.
- Note in the BOQ whether the client has opted for greywater.
`[CORE — affects site plan generator]`

**EV charging, solar-integrated balcony railings:** Mainstream by 2026. Site plan should reserve EV-charging conduit position and the BOQ should include solar-ready wiring as an option. `[LAYER — affects site plan, not floor plan]`

**Indoor air quality monitoring, contextual AI HVAC:** Sensors + automation. Affects HVAC sizing in the BOQ but not the floor plan layout. `[LAYER]`

**HVAC humidity and air-quality control:** The trend is invisible technology. Affects ducting paths if HVAC is centralised. For most Indian residential homes (3-tonne split AC, individual room units), no impact on floor plan. `[Skip — split AC is fine for residential]`

## 4.4 What this means for BuildemUp's roadmap

I would suggest the following allocation of these into versions:

| Feature | Version | Why |
|---|---|---|
| Open/broken kitchen as room option | v1 | Affects core room rules |
| WFH room as first-class type | v1 | Affects room rules |
| Solar-ready wiring in BOQ | v1 | Trivially additive |
| Rainwater sump in site plan | v1 | Affects site plan |
| Plumbing-stack alignment between floors | v1 | Affects bathroom router (Component 9) |
| Prefab/precast tier | v2 | Real upsell, needs separate cost model |
| Smart-home electrical layer (Matter readiness) | v2 | Needs separate visualisation layer |
| EV charging position | v2 | Affects site plan, simple addition |
| Greywater system as BOQ option | v2 | Simple BOQ addition |
| 3D walkthrough (digital twin) | v2 | Three.js or WebXR walkthrough |
| Self-healing concrete option | v3 | Education PDF for now |
| UHPC slim-slab option | v3 | Premium tier |
| BIM export for commercial-sized residential | Skip | Not the market |

The point is: most of the "modern home" content goes into the **education layer** (the contractor-question PDF, the construction-glossary PDF) rather than into the floor plan engine. The engine itself stays focused.

---

# PART 5 — The order of work

This is the build sequence I recommend, with honest size estimates and risk markers.

## 5.1 Phase 1 — Architecture foundations (weeks 1–4)

The goal of Phase 1 is: **produce 3 differentiated layouts that the user genuinely prefers to a contractor's hand sketch, on plots from 600 to 4000 sqft.** Nothing else.

| Order | Component | Build days | Risk |
|---|---|---|---|
| 1 | Plot Analysis (Component 4) | 1 | Low — mostly wiring existing CITY_DATA |
| 2 | Topology Selector (Component 5) | 5 | Medium — L-shape and courtyard topologies are new |
| 3 | Orientation Priority Engine (Component 6) | 2 | Low — data already mostly exists in `room_rules.py` |
| 4 | Corridor Design Engine (Component 7) | 4 | Medium — staircase placement is the tricky part |
| 5 | Plot-Aware Room Sizer (Component 8) | 3 | Low — straightforward greedy allocation |
| 6 | Pre-Placement Bathroom Router (Component 9) | 2 | Low — partially exists |
| 7 | Refactor Placement Engine (Component 10) | 3 | Medium — risk of breaking existing 100/100 layouts |
| 8 | Door Placement Engine (Component 11) | 3 | Medium — door-swing collision logic |
| 9 | Upgrade Connection Graph (Component 12) | 2 | Low — extension of existing module |
| 10 | Upgrade Space Auditor (Component 13) | 2 | Low — extension of existing |
| 11 | Wire `renderer_bridge.py` properly | 1 | Low — module exists, just wiring |
| 12 | Wire `site_plan.py` into `/v3/generate` | 1 | Low — module exists, just wiring |

**Total Phase 1: ~29 working days, call it 5–6 calendar weeks** with testing, regression catching, and the inevitable surprises.

The order is critical. Topology Selector before Corridor before Sizer before Bathroom Router before Placement before Doors before Graph. If you swap any of these you reintroduce the failure modes from sections 1.3–1.4.

## 5.2 Phase 2 — Conversational brief and trade-offs (weeks 5–7)

| Order | Component | Build days |
|---|---|---|
| 13 | Conversational Brief (Component 1) | 5 |
| 14 | Feasibility 4-layer (Component 2) | 3 |
| 15 | Trade-off Negotiation (Component 3) | 3 |
| 16 | Confirmation card UI | 2 |

Phase 2 lets users actually describe their dream home and have the engine ask clarifying questions. By end of Phase 2, the engine produces a layout from a free-form chat, which is what you said is the most important user-facing capability.

## 5.3 Phase 3 — Cost engine and contractor questions (weeks 7–9)

This is the part that makes BuildemUp commercially differentiated.

- Wire the existing cost engine into the new pipeline.
- Make contractor margin line visible by default.
- Generate the contractor-question PDF from the layout (e.g. "How will you waterproof the south-facing master bath?", "What is the M-grade of concrete for the staircase?").
- Generate the education-glossary PDF (one page per construction term used in the BOQ).

## 5.4 Phase 4 — Click-to-edit (weeks 9–12)

Every component above produces immutable output. The user looks at the layout and accepts it. Phase 4 makes it editable: click a room → resize, swap, delete, move. The backend is half-built; the UI is missing entirely.

This is genuinely 3 weeks of work because every edit must re-run Components 12 and 13 (graph + auditor) and re-render. The user expects sub-second feedback.

## 5.5 Phase 5 — DXF export, working drawing, regulatory drawing (weeks 12–14)

The user needs a downloadable DXF for their structural engineer and contractor. They need a "working drawing" (with their preferred 2ft setbacks instead of NBC's 5/3/3) and a "regulatory drawing" (with NBC setbacks for the building approval).

Both already partially exist. Phase 5 is making them properly distinct outputs with consistent labelling.

## 5.6 What happens after Phase 5

This is where the corpus / fine-tune side project becomes interesting. After ~50 paying users, you will have ~200–500 (brief, layout, edit-history, BOQ) tuples with real human feedback. That is the dataset you fine-tune a Llama or Mistral 7B on, to make the conversational layer cheaper than running Claude API calls. The corpus structure I would set up *now*, even before any paying users:

```
corpus/
  decisions/        — (prompt, layout-decision, reasoning) triples extracted from current sessions
  plans/            — labelled floor plans (input brief + output rooms + scores)
  rules/            — code-to-prose translations (each room rule explained as it would be to a homebuyer)
  dialogues/        — full architect-style Q&A transcripts from current sessions
```

The 22 conversation transcripts you sent are a solid seed for `decisions/` and `dialogues/`. The 29 research notes are a solid seed for `rules/`. The current floor plans (PNG + PlacedRoom JSON) are a seed for `plans/`. None of this is wasted work — it is the corpus foundation.

## 5.7 What I would NOT build

To be explicit about what is *not* in the plan:

- **3D rendering/walkthrough.** v2 at the earliest. The 2D layout is the priority.
- **Voice input.** v2. Text is fine for v1.
- **Multi-language UI.** v2. English Tamil-English mix is fine for v1.
- **Vastu engine.** Not without you explicitly asking for it. You said it is excluded for now.
- **Contractor marketplace / quote-matching.** Not in scope. BuildemUp gives the user the questions and the BOQ; finding the contractor is the user's job.
- **Project management or construction tracking.** Not in scope.
- **BIM or commercial-building support.** Not the market.

---

# Open questions for you

These are the things I need an answer on, in priority order. I have grouped them so you can answer in batches.

## Critical (block Phase 1)

> **Q1 — Tamil Nadu first?** You mentioned this earlier. Should the Phase 1 city support be Tamil Nadu only (Chennai CMDA + DTCP areas), or all 8 cities in CITY_DATA? My recommendation: Tamil Nadu only for v1, since you are there and can validate plans on real plots. Add other cities in v2.
>
> **Q2 — Which plot sizes must Phase 1 handle perfectly?** I would propose four: 20×30, 30×40, 30×50, 40×60. Anything outside this range gets a "Phase 1 best-effort" warning. Acceptable?
>
> **Q3 — How many topologies for Phase 1?** All four (strip, central spine, L, courtyard), or just the two we know we need (strip + central spine) for the four plot sizes above? L and courtyard are bigger builds. My recommendation: strip + central spine for Phase 1, L for Phase 2, courtyard never (too rare in the 600–4000 sqft range).
>
> **Q4 — What is the "good layout" benchmark?** I have inferred from the Apr 17 sessions that you want "better than what the user imagined". How do we test this? Show the engine output vs a contractor's hand sketch to 5 friends and see which they prefer? Or do you have an internal benchmark already?

## Important (block Phase 2)

> **Q5 — Conversational input — Claude API or self-hosted?** Claude API costs roughly ₹3–8 per generated brief. Self-hosted (Llama 7B) costs ~₹0 per brief but needs the GPU rental and the corpus to fine-tune on. I would say: Claude API for the first 100 paying users, then switch.
>
> **Q6 — Clarifying questions limit.** Is 4–5 questions still right? Some users might want zero questions (their brief is detailed). Some might want more. My recommendation: max 5, but Claude can ask 0 if the brief is unambiguous.
>
> **Q7 — Trade-off negotiation — one conflict at a time, or all at once?** I think one at a time, but you said both options are valid. Need a decision.

## Helpful (block Phase 3)

> **Q8 — Contractor margin — visible by default, or visible-on-toggle?** I have assumed visible by default per your stated philosophy. Confirm?
>
> **Q9 — Contractor-question PDF — generic or layout-specific?** Generic (20 questions every homeowner should ask) is easier. Layout-specific (questions derived from this user's specific design) is far more valuable. My recommendation: hybrid — 15 generic + 5 layout-specific.
>
> **Q10 — Modern home features in v1 BOQ.** I propose v1 BOQ includes: solar-ready wiring (₹), rainwater sump (₹), greywater system (₹ option), Matter-2.0-ready electrical (₹). Anything else you want in v1?

## Nice to have

> **Q11 — Branding.** BuildemUp or BuildEase? Lock one and rename everywhere.
>
> **Q12 — Click-to-edit scope for v1.** Just resize and delete? Or also move and swap? Resize-only is much simpler.
>
> **Q13 — Mobile vs desktop.** Is the v1 user on a laptop or a phone? Affects the UI design entirely.

---

## Closing note

I have tried to ground every claim above in either (a) something you and previous-Claude already decided in one of the 22 sessions, (b) a piece of code that actually exists in the codebase, or (c) a research source from this round of web research. Where I have made my own recommendation, I have marked it.

The architecture has 13 components in execution order. The first 12 are the layout engine. Component 13 is the auditor. Phase 1 builds all of them in 5–6 weeks. Phase 2 adds the conversational brief. Phase 3 adds cost transparency. Phase 4 adds click-to-edit. Phase 5 adds the proper outputs.

Nothing in this document should be built until you have read it carefully and answered at least Q1–Q4. After that I will produce the workflow mockup (clickable HTML, no engine behind it) so you can see what the user journey actually feels like — and only after you sign off on the mockup will any code get touched.

