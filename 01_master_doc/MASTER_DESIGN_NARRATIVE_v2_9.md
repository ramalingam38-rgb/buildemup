# BuildemUp / BuildEase — Master Document v2

**Single source of truth. Read this first, before doing anything.**

| | |
|---|---|
| **Founder & developer** | Ramalingam (solo, Tamil Nadu, India) |
| **GitHub** | https://github.com/ramalingam38-rgb/buildease |
| **Replit handle** | ramalingam38 |
| **Live URL** | https://buildease-production.up.railway.app |
| **Local working path** | `C:\1.Startup Project latest\buildemup` |
| **Current placeholder name** | "BuildemUp" (marked with † in working docs; final name TBD — "Archimind" was first choice but is taken; "Grihya" was Claude's recommendation) |
| **Document version** | v2.9 — 1 May 2026 (Session 23 — S7a SPEC v1.0 LOCKED + S7a code build started ~30-40% complete; mid-build handoff prepared) |
| **Supersedes** | v2.8 (30 April 2026, S6 shipped); see also v2.0–v2.7 history |

---

## How to read this document

This document was rebuilt on **29 April 2026** after Ramalingam uploaded a comprehensive 27 MB archive (`1777425962270_BUILDEMUP_COMPLETE_ARCHIVE_2026-04-29.zip`, 213 files) containing **everything**: all 16 chat sessions from 20–28 April plus pre-history, all source documents, the current codebase, all snapshots. The first version was built from a partial set of 10 zips and missed important context. Ramalingam's instruction was explicit:

> "I want you to have a 100% clear idea about what we did and actually understand them. Then only we can proceed without making the same mistakes again and again."

This document delivers on that. It is structured so that **any future Claude session** (or Ramalingam himself, three months from now) can read it and pick up exactly where we are.

**Reading order I recommend:**
1. **Part 0** — Founding story + vision (so you understand WHY this exists)
2. **Part 1** — The four numbering schemes (so you don't get confused by component numbers)
3. **Part 2** — Patterns to avoid (so we don't repeat the mistakes)
4. **Part 8** — Current build status (so you know what's shipped and what isn't)
5. **Part 11** — Where we go next (so you know the immediate decision to make)
6. Everything else as reference

The document is long because it has to be. But every section is independently readable.

---

# PART 0 — Founding Story and Product Vision

## 0.1 The contractor moment that started this

Ramalingam built his own house. The contractor took a six-figure rupee lump-sum payment without itemising what the money was for: structure, masonry, plumbing, electrical, finishes — all rolled into one number. Ramalingam had no way to know if any single line was fair or inflated. He couldn't compare quotes from other contractors because nothing was line-itemised. He couldn't cut scope strategically because he didn't know what cost what. He paid in good faith, with no benchmark, with no defence.

**That experience is the entire reason BuildemUp exists.**

Every Indian family building a home faces exactly this moment. The contractor has 25 years of practice. The family is doing this once, ever. The asymmetry is total. BuildemUp is the answer to that asymmetry — not as a cheap-DIY shortcut, but as a serious decision-support engine for a once-in-a-lifetime financial commitment.

## 0.2 The product, in one sentence

> **BuildemUp is a decision-support engine for Indian families building their own home. The floor plan is the artifact. The real product is confidence in a six-figure decision.**

This sentence is the locked positioning. Every feature, every scope decision, every refusal — all of it gets tested against this sentence.

## 0.3 The three asymmetries the product exists to close

| Asymmetry | What the user lacks | What BuildemUp provides |
|---|---|---|
| **Information** (vs the contractor) | Real costs, current material rates, what's reasonable, what's overpriced | Quote Comparison Engine, Contractor Pack, BOQ with brand/grade/IS-code, contractor margin shown as a separate line |
| **Expertise** (vs the architect) | NBC codes, IS standards, drawing conventions, technical language | Plain-language reports, dual drawings (working + regulatory), every numeric output cited to a code, layout problems explained as user-experience consequences |
| **Emotional** (vs the decision itself) | Benchmarks, social proof, validation, a way to stop second-guessing | The Transparency Triple (range + midpoint + derivation), confidence indicators on every output, reassurance lines, three explicit user intervention checkpoints |

**Scope test:** if a feature does not close one of these three asymmetries, it does not belong in v1. This is the only scope discipline we have. Component 7 took four months partly because we kept failing this test and reopening scope.

## 0.4 The relationship model — "user preference first, but practical, with trade-offs explained"

This was locked very early (Session 1, 20 April) and has held through every architectural decision since:

- **The user's preferences come first.** If the user wants a 2 ft setback (knowing it's sub-NBC), the engine respects that.
- **But the engine is honest about consequences.** It runs the Code-Strict envelope alongside the Practical envelope and shows exactly what the user is choosing — including the cost of compliance, the approval risk, the structural implications.
- **Trade-offs are explained, never silently overridden.** When the user's brief and feasibility conflict, Component 3 (Trade-off Negotiation) surfaces the conflict, presents 2–4 architectural alternatives, and lets the user pick. The engine never just rewrites the brief.

This is the "advisory, not auditor" tone. It's also the reason most realistic briefs land at Code-Strict score 40 (correct, see Part 8.6) — the engine is honest about the gap, doesn't try to fake a higher number.

## 0.5 What BuildemUp is NOT (the most important section)

This list is locked. Every item below has been re-litigated in at least one session and rejected for v1.

- ❌ **Not** a layout generator competing with Maket / Finch3D / House-GAN++
- ❌ **Not** a BIM tool competing with Revit / ArchiCAD (we explicitly are NOT trying to be Revit; calibration in Architecture v3 §2)
- ❌ **Not** a contractor marketplace
- ❌ **Not** a project-management or construction-tracking tool
- ❌ **Not** a free-form CAD sketch tool
- ❌ **Not** a 3D walkthrough renderer (deferred to v2 phase B)
- ❌ **Not** a Vastu engine (Vastu is opt-in INFO-only advisory; never blocks)
- ❌ **Not** an LLM-based brief extractor in v1 (form-based only; LLM brief deferred to v2)
- ❌ **Not** an engineer-replacement (every output carries "PENDING ENGINEER VALIDATION" — see Part 5.4)

## 0.6 The full product vision (v1 → v4) — for context only, NOT v1 scope

The full vision was articulated by Ramalingam in Session 7 (23 April). Claude pushed back on building it all at once and proposed a phased v1 → v4 roadmap. **v1 is the only scope being built right now.** v2–v4 are not promises; they are reference for "what would we build if v1 succeeds and we have resources?"

| Phase | Calendar target | What it ships | What it deliberately does not ship |
|---|---|---|---|
| **v1 — Decision engine** | Now (12 mo) | Brief → feasibility → trade-off → 3 ranked layouts → working drawing PDF + regulatory drawing PDF + BOQ + contractor pack + quote comparison | 3D walkthroughs, full BIM/IFC, supplier integration, interior selections |
| **v2 — Engineering depth + 3D** | Year 2 | LEVEL_3 frame analysis (P-M curves, dynamic seismic), 3D walkthrough viewer, real-time supplier rate scraping, mobile React Native app | Interiors, robotics, drone surveys |
| **v3 — Selections + interiors** | Year 3 | Tile/sanitary/woodwork catalogues, interior floor plan with furniture, lifestyle reports | Construction simulation, robotics |
| **v4 — CAD + contractor handoff** | Year 4–5 | Full CAD output (DXF + Revit-grade IFC), permit-ready submissions, BuildEase Digital Twin (drone surveys + IoT during construction), 3D printing + robotics integration vision | (the v4 list IS the long-tail; everything ships under v4 or beyond) |

**For implementation purposes the only number that matters is v1.** Don't reference v2/v3/v4 as features — they are research directions in `v2_vision.md` and `v2_backlog.md`.

---

# PART 1 — The Four Numbering Schemes (CRITICAL CONFUSION POINT)

This is where every previous Claude session lost context. **There are four different "component numberings" floating around the project**, each from a different document or era. They do NOT match each other. Whenever a number is used in this document, it is qualified by which track.

## Track 1 — Original 10-Component Layout Engine (Sessions 16–21 / Era 1)

This was the first architecture, drafted in Session 16 (16 April 2026) of the pre-history. Surfaces in old transcripts and the original `BUILDEMUP_MASTER_RECORD.md`.

```
C1  Brief Reader
C2  Connection Graph
C3  Placement Engine
C4  Space Auditor
C5  Corridor Design
C6  Topology Selector
C7  Bathroom Rules
C8  Door Placement
C9  Plot-Aware Sizer
C10 Orientation Priority
```

**Status:** Superseded. Don't use these numbers.

## Track 2 — Current Codebase Numbering (Era 2 build, Apr 22–28)

This is what's actually in the code right now. The `components/` folder has subfolders `c01/`, `c02/`, `c07/`. These three components have shipped. Components 3, 4, 5, 6 in this scheme have **never been specified** in the codebase — `c03_*.py` etc. don't exist.

```
c01 → Brief Capture Engine               ✅ SHIPPED v0.9.2 → v0.9.3 (Apr 25 → Apr 27)
c02 → Feasibility Engine (dual-design)   ✅ SHIPPED v0.1   (Apr 27 → Apr 28)
c07 → Structural Grid Engine             ✅ SHIPPED v0.7.3 (Apr 22 → Apr 23)
```

The codebase numbering jumped from c02 to c07 because the architectural reset built **the foundation first**: structural grid (c07) before brief (c01) before feasibility (c02). The component-3-through-6 numbers were left vacant because Ramalingam wanted to use them later for the Track-3 components when those get built.

**Status:** Live. This is what the running code uses. **This is the numbering future code uses.**

## Track 3 — Architecture v3 (the canonical 17-component plan)

This is the **canonical architecture** for the full v1 product, locked in `BuildemUp_Architecture_v3.md` (22 April). The 17-component plan that the rest of the build will implement.

```
LAYER 1 — Understanding (4 components)
  1   Conversational Brief                         ← built as Track-2 c01
  2   Feasibility (×2 envelopes)                   ← built as Track-2 c02
  3   Trade-off Negotiation                        ← NEXT TO BUILD
  4   Plot Analysis

LAYER 2 — Generation (9 components)
  5   Topology Selector
  6   Orientation Priority Engine (climate-aware)
  7   Structural Grid Engine                       ← built as Track-2 c07
  8   Corridor Design
  9   Room Sizer (with furniture envelope)
  10  Bathroom + Wet-Zone Stack Planner
  11a Topology Mutation Layer (9 global operators)
  11b Local NSGA-II Refinement
  12  Vertical Alignment Engine
  13  Door Placement

LAYER 3 — Evaluation + Output (4 components)
  14  Unified Evaluation Engine (Hard/Soft split)  ← CRITICAL v3 fix
  15  Ranker (Cost Efficient / Everyday Living / Premium Design)
  16  Dual-Drawing Renderer
  17  Quote Comparison Engine                      ← biggest moat feature

CROSS-CUTTING (3)
  Contractor Defence Layer
  Resilience Layer  (graceful failure everywhere)
  Constraint Propagation  (NEW in v3)

SYSTEM CAPABILITY (1)
  Fast Mode / Deep Mode selector
```

**The mapping between Track 3 and Track 2:** Track-3 components 1, 2, 7 are physically implemented as Track-2 c01, c02, c07. The numbering matches deliberately. **Components 3–6 and 8–17 of Track 3 are NOT YET BUILT.**

**Status:** Locked. This is the build target.

## Track 4 — Full Product Phases (v1 → v4)

The product roadmap from Section 0.6 above — A/B/C/D phases.

```
Phase A  →  v1  (current)  Brief + feasibility + 3 ranked layouts + drawings + BOQ + quote comparison
Phase B  →  v2  Engineering depth + 3D walkthroughs
Phase C  →  v3  Interior selections + lifestyle
Phase D  →  v4  Full CAD + contractor handoff + digital twin
```

**Status:** Reference only. Phase A is the only thing being built.

## How the four tracks relate

```
Track 4 (Phases)         Phase A only ─────────────────────────────────►  v1
Track 3 (Canonical 17)   1 ─ 2 ─ 3 ─ 4 ─ 5 ─ 6 ─ 7 ─ 8 ─ 9 ─ 10 ─ 11ab ─ 12 ─ 13 ─ 14 ─ 15 ─ 16 ─ 17
                         │   │           ↑                              ↑
Track 2 (Codebase)      c01 c02         c07                            (3 of 17 built)
Track 1 (Old)            (DEAD — DO NOT REFERENCE)
```

**When this document writes a component number unqualified, it means Track 3 (the canonical architecture).** Component 7 = Structural Grid Engine. Component 17 = Quote Comparison Engine.

When the document refers to actual code on disk, it uses lowercase prefixes (`c01`, `c02`, `c07`) — that's Track 2. Same component, different scheme.

---

# PART 2 — Patterns to AVOID (the mistakes we keep repeating)

Ramalingam's exact phrasing was: *"without making the same mistakes again and again."* Four patterns have surfaced across multiple sessions. Each one cost real time. The architecture v3 + design principles v3.1 are designed to make these patterns impossible to fall into. Read this before any coding session.

## Pattern A — Fix-as-bandage

**What it looks like:** A bug is reported. Claude (or earlier Claude) writes a patch that addresses the symptom without addressing the cause. The bug returns later in a different form because the underlying invariant was never fixed.

**Where it happened:**
- Era 1 placement engine had `mw=10.0, cw=6.0, btw=3.0` hardcoded constants. When 30×40 plot produced a 57 sqft bedroom_3 (NBC minimum is 80 sqft), an early fix scaled bedroom widths instead of removing the hardcoded constants. The hardcoded constants then broke for a different plot size.
- Bathroom transit bug ("user has to walk through bedroom to reach bath") was patched per-plot instead of solved by introducing the rule "corridor → bedroom → bathroom, never corridor → bathroom → bedroom."

**Why v3 architecture prevents this:** Component 9 sizes rooms from a furniture envelope (Neufert), not from hardcoded constants. Component 10 (Bathroom Router) treats the corridor → bedroom → bath rule as a hard constraint. Component 14's Hard Constraint Checker catches violations before any scoring runs.

**Discipline rule:** When a bug is reported, write the failing test first, then fix the root cause, never the symptom.

## Pattern B — Building without wiring

**What it looks like:** A module is built, tested in isolation, looks great. But it's never connected to the orchestrator. Six months later it's discovered that the live system has been ignoring the module entirely.

**Where it happened:**
- Style 2 renderer (`renderer_bridge.py`) was built end of Era 1 (Session 21, 20 April) — full furniture symbols, dimension chains, door arcs. **Never deployed to Railway.** Live site still uses old coloured-boxes renderer.
- `furniture_test.py` (2026 Indian furniture dimensions) was built but never wired into the placement engine — placement still didn't know if a queen bed actually fits.
- `click_to_edit.py` backend was built but the UI was never built. Users can't edit.
- `layout_optimizer.py` (7,262 lines of NSGA-II scaffolding) was orphaned in Era 1 — never wired into the pipeline.
- 7 of 8 architectural-intelligence classes in `buildease_arch_intel.py` returned hardcoded `75.0` — they were stubs the whole time.

**Why v3 architecture prevents this:** ComponentContract enforcement (added v0.5) — a CI test auto-discovers every `c{NN}_*.py` file and asserts each has a registered contract that connects it to the pipeline. New components physically cannot exist without being wired.

**Discipline rule:** Every component MUST have an integration test that runs the orchestrator end-to-end. "Unit tests pass" is not enough.

## Pattern C — Scores without truth

**What it looks like:** Engine produces a single number ("89/100"), user trusts the number, but the number doesn't reflect lived quality. A 95/100 plan can be unlivable.

**Where it happened:**
- Era 1 engine scored 100/100 on graph completeness for the canonical 30×40 plot, while bedroom_3 was 57 sqft (sub-NBC) and bathroom_3 was 3 ft wide (sub-NBC). The score was technically correct (graph IS complete) and architecturally meaningless.
- Mostafavi 2025 paper (cited in Session 3 web research) explicitly warns: blended scores hide model weaknesses; one model scored higher on pixel-overlap but lower on graph-topology — a single score would have called the worse one "better."

**Why v3 architecture prevents this:** Component 14 outputs a **Problem Report**, not a score. Categorised list across 8 categories (privacy, light, ventilation, circulation, furniture fit, structural, regulatory, proportion) with 30+ specific checks. The user sees "this corridor is 0.85m wide where 0.9m minimum applies — 5cm short" — not "94/100."

**Discipline rule:** Numeric scores are allowed only when ranking between candidates inside a single category. The user-facing output is always a problem list with severity and fix suggestion.

## Pattern D — Rules piled on rules

**What it looks like:** A new edge case is found. A new rule is added. Six months later there are 200 rules, they conflict with each other, and nobody can predict what the engine will do.

**Where it happened:**
- Era 1's `room_rules.py` accumulated 1,584 lines of rules — many overlapping, some contradicting on edge cases.
- The original "single envelope" feasibility check kept getting more exceptions added until the dual-design pattern was introduced in Session 11 (27 April). The dual-design with Practical + Code-Strict + Gap analysis cleaned up everything.

**Why v3 architecture prevents this:** Constraint Propagation cross-cutting concern (NEW in v3). One `ConstraintEngine` class with `propagate_*()`, `repair_violation()`, `validate()`, `explain()` methods. All components consume it as a library. Conflicts surface explicitly via `repair_violation()`.

**Discipline rule:** Before adding a new rule, look for an existing rule that already covers the case. If two rules contradict, fix the abstraction, don't add a third rule to mediate them.

## Pattern E — Scope creep mid-build (specific to Component 7)

**What it looks like:** A component build that should take 2–3 days takes 4 months because every review adds new requirements.

**Where it happened:** Component 7 took from late March to 23 April (≈4 weeks of focused build, longer counting earlier scaffolding) because every review introduced legitimate but unscoped concerns: trust controls, building-type architecture, three-level regularity, ComponentContract, freshness, legal disclosures, action layer recommendations, frame sanity, global stability check, configuration-driven rules. Every one was a real improvement; together they were 5 versions of a single component.

**Why v3 architecture prevents this:** Every component now has a **locked spec** (e.g., `SPEC_v0.2_LOCKED.md` for Component 1) before code starts. The spec lists what's IN scope and explicitly what's NOT in scope. Mid-build proposals get triaged: "real spec change" vs "v0.2 backlog item."

**Discipline rule:** Before any code, write the spec. Get user review. Lock it. Then code. New ideas during build go to a backlog, not into the current build.

---

# PART 3 — Era 1 (Pre-history, 12 March → 20 April 2026)

The "before" — the work that produced the engine that the v3 architecture now replaces. This is captured for reference only; nothing here is current architecture. The full pre-history is preserved in `06_original_uploads_pre_history/` of the archive.

## 3.1 Summary of Era 1

22 chat sessions over 6 weeks, ~90,000 lines of conversation. Built:
- Three-component layout pipeline: `room_rules.py` + `connection_graph.py` + `placement_engine.py`
- Plus six derived modules: `topology_selector.py` (stub), `zone_splitter.py`, `bathroom_router.py`, `door_computer.py`, `space_auditor.py`, `corridor_limiter.py`, `general_placer.py`
- Plus support: `furniture_test.py`, `external_wall_checker.py`, `structural_checker.py`, `renderer_bridge.py`
- Plus the Era 1 architectural intelligence module (`buildease_arch_intel.py`) — which turned out to have 7 of 8 classes as stubs returning `75.0`
- Plus the orphaned `layout_optimizer.py` (7,262 lines of NSGA-II scaffolding never wired)
- Plus a comprehensive knowledge base in `knowledge/`: ~4,618 lines across 6 modules + 14,731 lines of research notes across 29 books and codes
- Plus the legacy FastAPI `server.py` and consultation flow (`/pack` endpoints, 6 stages)

**State at end of Era 1 (Session 21, 20 April):**
- Live on Railway at https://buildease-production.up.railway.app
- 8 plot sizes tested with mixed results (20×30, 30×40 working well; 40×60+ broken on graph score)
- 15 known problems documented (see Part 3.3)
- Style 2 renderer built but not deployed
- 6-stage consultation flow working

## 3.2 Era 1 sessions at a glance

| Sessions | Dates | What was built |
|---|---|---|
| 1–9 | 12–13 March | First runnable engine, Replit deploy, 3D viewer, 12 knowledge modules, 7 engines, 21-layer platform draft |
| 10–11 | 18 March | Wall Graph engine, DXF CAD drawings, 6 IIT engineering KBs |
| 12–13 | 7 April | Massive consolidation: 7 KBs + 16 CAD engines + ML v3 + 9 industry upgrades into giant `buildease_v4.py` |
| 14–15 | 15 April | Layout Optimizer V2, cost engine, circulation analyzer, room luxury research |
| 16 | 16 April | **The architectural insight session.** Conversational brief, 30×40 dream-home brief, room placement work |
| 17–18 | 17 April | Three-component pipeline finalised, Railway deployment, BuildEase→BuildemUp branding |
| 19 | 17 April | "The 6 fixes" session (topology_selector, zone_splitter, bathroom_router, door_computer, space_auditor, corridor_limiter) |
| 20 | 17 April | Multi-plot testing on 20×30, 30×40, 30×50, 40×60, 60×80 — discovered the topology-blindness problem |
| 21 | 20 April | Final Era 1 session. Master record written. Style 2 renderer built (not deployed). User asks for architectural review |

## 3.3 The 15 Known Problems from Era 1 (verbatim list)

This list was compiled by previous-Claude in Session 1 of Era 2 (20 April) as the diagnostic that motivated the architectural reset. Every one of these is solved at the root by the v3 architecture.

| # | Problem | Era 1 root cause | v3 architecture fix |
|---|---|---|---|
| 1 | Strip topology only — no central spine, courtyard, L | Era 1 had `topology_selector.py` as a stub | Component 5 (Topology Selector) — explicit choice between 5 topologies |
| 2 | Passage no door logic broken | Era 1 added doors after layout | Component 13 places doors as final placement step, with hard constraint |
| 3 | Bathroom transit bug (walk through bed to reach bath) | No corridor→bed→bath ordering rule | Component 10 enforces ordering as hard constraint |
| 4 | Car parking missing in rendered output | `site_plan.py` not wired | Component 16 dual-drawing renderer covers both site + floors |
| 5 | 30×40 plot dimensions hardcoded everywhere | `mw=10.0, cw=6.0, btw=3.0` hardcoded in `placement_engine.py` | Component 9 sizes rooms from furniture envelope (Neufert), no hardcoded constants |
| 6 | L-shaped master bedroom stored as 2 rectangles (auditor false-flagged smaller piece) | Renderer split L into 2 rooms | Component 11 stores rooms as polygons; renderer treats single-named-region as one room |
| 7 | Common bathroom shower not drawn at 6ft depth | Renderer didn't have shower symbol logic | Component 16 includes the v3 furniture+fixture symbol library |
| 8 | Style 2 renderer never pushed to Railway | Built end of Era 1, deploy deferred | Component 16 is the new renderer; deploy is part of the build |
| 9 | 7 of 8 architectural-intelligence classes returned `75.0` (stubs) | Original implementation skipped | Component 14 is one Unified Evaluation Engine; no stubs |
| 10 | Click-to-edit backend exists; UI doesn't | Frontend never built | v2 backlog (deferred — not v1) |
| 11 | "Dream home" text dropped between brief input and generation | Conversational text not preserved | Component 1 captures full brief; LLM brief deferred to v2 |
| 12 | Railway-vs-local code drift | Inconsistent deploys | Single push-to-main deploy flow |
| 13 | BuildEase / BuildemUp branding inconsistent | Two names floating around | All current docs use "BuildemUp" with † marker for future global rename |
| 14 | Drawing-type silent fallback to Bangalore for non-Bangalore cities | City defaults bug | Component 2 has city-specific feasibility defaults; explicit fallback disclosure |
| 15 | **Scoring measures technical validity, not lived quality** | Single-number score with no semantic meaning | Component 14 outputs Problem Report (categorised) — see Pattern C |

**Problem 15 is the meta-problem.** It's the reason the other 14 weren't caught earlier: a 95/100 score made everyone think the engine was working. The architectural reset made "lived quality" a first-class concept.

## 3.4 The architectural insight that started Era 2

Quoted from Session 16 of Era 1 (16 April), Ramalingam to previous-Claude:

> **"Why didn't our engine see this as the best possible layout?"**

Previous-Claude's answer (paraphrased with the key sentence intact):

> **"The engine places rooms first and thinks about architecture second. It never considers topology — whether the floor should be a strip, a central spine, an L, or a courtyard — before it starts placing."**

That sentence is the root cause of 14 of the 15 known problems. It is the reason the architectural reset happened. It survives unchanged into v3 architecture as the foundational design principle: **topology before placement.**

---

# PART 4 — Era 2 Chronological History (16 sessions, 20–28 April 2026)

These are the 16 sessions captured in `01_chats_chronological_readable/` of the archive. Each session is summarised with: date, what was decided/built, and links to source material. Key sessions are deeper-summarised; routine ones are brief.

## 4.1 Session 1 — Mon 20 April 2026 — *Architecture Research*

**Source:** `01_2026-04-20-architecture-research.txt` (1,412 lines)
**Theme:** Re-read the entire pre-history. Diagnose the engine. Propose architectural reset.

**What happened:**

Claude was given the full archive and asked to do a deep-dive product analysis. Claude:
1. Re-read 22 prior conversation transcripts (~90K lines) systematically — but admitted partway through to having only skimmed many of them; user pushed back, Claude re-read them properly
2. Read the 6-module knowledge base (4,618 lines) and 29 research notes (14,731 lines)
3. Performed extensive web research on House-GAN++, Finch3D, Autodesk Forma (Spacemaker), space syntax (Hillier/Hanson), NSGA-II for floor plans, Indian construction codes
4. Documented the **15 known problems** (Part 3.3 above)
5. Articulated the **topology-first insight** (Part 3.4 above)
6. Drafted the first 13-component architecture
7. Got 4 questions from user (Q1–Q4) about Tamil Nadu first, plot range, topologies, "good layout" benchmark

**Key decisions in this session:**
- ✅ Tamil Nadu first (Chennai-focus); other cities NBC fallback
- ✅ Plot range: 600 sqft (20×30 EWS) → 4,000 sqft (40×100 large), with quality tiers
- ✅ Five topologies for v1: No-corridor, Strip, Central Spine, L-shape, Courtyard
- ✅ "Good layout" = no wasted space + bathrooms with adequate space + 8 other research-validated signals
- ✅ Vastu is opt-in INFO-only, never blocks
- ✅ Bedrooms > Kitchen > Living priority order for cuts (locked from Era 1, retained)

**Critical user direction (locked):** *"There should be trade-off negotiation because it gives the user the chance to decide how to manage this issue."* This is the philosophical foundation of Component 3.

## 4.2 Session 2 — Tue 22 April 2026, 03:28 UTC — *Architecture Validation*

**Source:** `02_2026-04-22-architecture-validation.txt` (573 lines)
**Theme:** User pushed back on the 13-component architecture; critique pointed out 5 missing components.

**What happened:**

User shared a critic-review document highlighting that the architecture was "still slightly over-indexed on rules and under-indexed on evaluation + iteration." The critic's killer sentence:

> **"Right now your engine is: Plan once → check → output. The best systems do: Generate → evaluate → mutate → re-evaluate → pick best."**

Claude's verdict on the critic's 5 proposed additions:

| Proposed addition | Verdict |
|---|---|
| Component 14: Layout Generator + Ranker | Correct, MOST IMPORTANT — added |
| Component 15: Lived Quality Scoring | Correct — added (renamed Problem Finder later) |
| Component 16: Structural Grid Engine | Correct, was under-weighted — promoted to Component 7 |
| Component 17: Vertical Alignment Engine | Correct — added |
| Component 18: Preference Learning Engine | Correct as v2, not v1 |

**Plus user's working-vs-regulatory-drawing concern:** treated as foundational. Component 2 (Feasibility) now runs TWICE; Component 16 (Renderer) produces TWO drawings.

**End of session:** 18-component architecture in `BuildemUp_Architecture_v2.md` (preliminary; superseded by v3).

## 4.3 Session 3 — Tue 22 April 2026, 12:40 UTC — *Architecture v3 + first Component 7 build*

**Source:** `03_2026-04-22-architecture-and-component7.txt` (1,579 lines)
**Theme:** User requested deep web research on EVERY component before coding. Architecture v3 finalised. Component 7 first build started.

**What happened:**

Phase 1 — Web research validation across all 18 components:
- Verified Mostafavi 2025 paper supports Problem Finder (not Scorer) approach
- Verified NSGA-II is the academic gold standard via 2023 *Automation in Construction* paper
- Researched Tamil Nadu plot sizes from CMDA/DTCP sources → 600–5,000 sqft is the real residential market
- Discovered there are **8 recognised residential topologies**, not 4 (added U-shape, Atrium, Split-level)
- Branding research: "Archimind" is taken (US AEC-AI company archimind.io) → suggested 6 alternatives, top pick **Grihya** (Sanskrit "household")
- Component 11 (Placement Engine) verdict: **behind state-of-art** because purely rule-based — needed NSGA-II wiring
- Confirmed Indian-family-specific objectives are the moat (cost transparency, pooja, multigen, bath practicality, wet-zone, climate)

Phase 2 — User asked: *"Tell me about Component 11 placement engine why it is behind the market and how to make it above the market and what is it we are missing."*

Claude's answer became the **6 Indian-family optimization objectives** that nobody else has (now Components 11b + 14):

1. Contractor cost transparency
2. Pooja room placement score
3. Multi-generational living score
4. Bathroom-to-bedroom practicality
5. Wet-zone grouping efficiency
6. Tamil-climate comfort index

Phase 3 — User asked for a third critique round. Claude found three more flaws in own architecture:
- **Local optimisation, not global** (NSGA-II tweaks parameters; misses structural variations) → added **Component 11a: Topology Mutation Layer** with 9 global operators (horizontal flip, vertical flip, staircase relocation, corridor inversion, public/private swap, wet-wall rotation, grid scaling, vertical rearrangement, **entry door relocation** — the 9th was added in v3)
- **No furniture-fit scoring** → added to Component 14 as a Hard Constraint
- **Fragmented evaluation** → merged old C14+15+16 into one Unified Evaluation Engine

**End of session:** 17-component architecture v3, **CANONICAL** (`BuildemUp_Architecture_v3.md`). Plus first cut of Component 7 code (4 sub-modules).

**The CRITICAL fix in v3:** Hard/Soft constraint split. v2's Unified Evaluation Engine treated structural validity alongside cost in the same NSGA-II objective vector — meaning a structurally invalid layout with great cost could survive Pareto. v3 fixes this with two-stage evaluation: Stage 1 = Hard Constraints (binary pass/fail), Stage 2 = Soft Objectives (NSGA-II ranking). Failed candidates don't even enter the population.

**The MAJOR addition in v3:** Component 17 — Quote Comparison Engine. The single biggest consumer-facing differentiator. User uploads contractor quote → engine extracts items, compares to BOQ, flags overpricing. Saves users ₹5–10 lakh per project. Hard for Western tools to replicate (requires Indian cost knowledge + contractor-practice awareness + financial-document trust).

## 4.4 Session 4 — Thu 23 April 2026, 03:22 UTC — *Component 7 v0.4 (Block A + Block B)*

**Source:** `04_2026-04-23-v04-block-a-b-progress.txt` (1,345 lines)
**Theme:** Trust controls + building-type architecture.

**What happened:**

After a BuildEase vision PDF arrived from user, Claude pivoted to platform-readiness scaffolding while keeping the v0.3→v0.4 review changes shipping.

**Block A — Trust controls (10 changes):**
1. Three-level regularity classification (REGULAR / MODERATE / SEVERE) — was binary
2. Severe-irregularity refusal in orchestrator — was "warn but proceed"
3. SCWB renamed to **heuristic** everywhere (was implied authority — "Strong Column Weak Beam Index" sounded definitive when it was actually a rule-of-thumb)
4. Wind + seismic load combination check
5. Centralised KB version registry with `LAST_UPDATED` field
6. `format_for_user(error)` — never leaks internal details
7. `summarize_trace(trace_id)` for human-readable logs
8. Per-output `kb_versions` + `trace_id` for reproducibility
9. Prominent "PRELIMINARY DESIGN" banner at TOP of `explain()` output
10. Explicit "WHAT WE CHECK / DON'T CHECK" disclosure section

**Block B — Building-type architecture:**
- `BuildingType` enum + registry (8 types: residential single-family, residential multi-family, commercial, industrial, warehouse, healthcare, educational, hospitality)
- Residential single-family fully implemented
- Other 7 stubbed and refused gracefully ("Component 7 v0.4 supports residential single-family only")
- Brand/grade/IS-code on `MaterialRate` (e.g., "Ramco/Ultratech OPC 53 IS 12269")
- Vastu engine stub (5 high-impact rules, opt-in)

**State at end:** ~74 PASS markers across 6 test suites.

## 4.5 Session 5 — Thu 23 April 2026, 05:42 UTC — *v0.5 shipped + v0.6 review begins*

**Source:** `05_2026-04-23-v05-shipped-v06-review.txt` (1,251 lines)
**Theme:** v0.5 closes the v0.4 review's 7 drawbacks. User submits "BUILD EASE — REAL SOLUTIONS TO DRAWBACKS" doc with 6 structural + 6 codebase fixes for v0.6.

**v0.5 changes (7 items addressing v0.4 review):**
1. **Confidence rename:** HIGH/MEDIUM/LOW → **WELL_CONSTRAINED / REGIONAL_TYPICAL / DEPENDS_ON_CHOICE**. Subtle but critical critique: "HIGH" carries semantic weight that overrides any inline definition. Old names retained as aliases for transition.
2. **Banner language strengthened:** "Preliminary Design Estimate" → **"RULE-BASED HEURISTIC ESTIMATE"** + **"NOT structural design"**.
3. **Engineer-validated override flag** — preserves severe-irregularity refusal but adds an escape hatch. Audit fields required: `engineer_name`, `engineer_license_no`, `validation_date`.
4. **Load combination simplification disclosed.**
5. **Sensitivity scope limitation disclosed** (only soil + load drivers in v0.5; expanded to 4 drivers in v0.6).
6. **`ComponentContract` system** — explicit input/output schemas per component, validated at every component handoff. **The single biggest architectural improvement in the whole project.**
7. **Vastu separation disclosure** — `format_for_user()` always prepends "VASTU ADVISORY (separate from structural design)..." to any Vastu output.

**State at end:** 98 PASS markers across 7 test suites.

User submitted v0.6 review with 6 drawbacks. Web research validated reviewer's proposed thresholds match IS code.

## 4.6 Session 6 — Thu 23 April 2026, 09:15 UTC — *v0.6 Phase 3 (legal hardening)*

**Source:** `06_2026-04-23-v06-phase3-mostly-done.txt` (1,304 lines)
**Theme:** Legal + trust hardening. The most legally-careful release.

**v0.6 Phase 1 — Real engineering:**
- **Frame sanity engine** (`components/c07/frame_sanity.py`): Hardy Cross moment distribution + IS 456 cl. 39.6 Bresler interaction with the **REAL formula** (αn interpolated 1.0 → 2.0 per code). Outputs SAFE/WARNING/FAIL.
- **Load combinations** (`components/c07/load_combinations.py`): 5-combo set per Indian practice. **Wind + EQ never combined per IS practice** (verified by web research).
- **Real IS 1904 soil bearing capacity** (`kb/soil_classification.py`): 12 soil classes. Hard rock 450–3300 kN/m² (real range). Black cotton flagged expansive. Reclaimed fill requires pile.
- **Extended sensitivity** from 2 drivers (soil, load) to 4 drivers (+span, +material grade).

**v0.6 Phase 2 — Architecture:**
- **Config-driven rules pilot:** `kb_rules/seismic_rules.json` + `utils/kb_rules_loader.py`. Schema validation, caching, 8 typed accessor functions. **Parity test caught a real bug on first run** — Zone III steel% was 1.2 in JSON vs 1.5 in Python. The parity test as a pattern is now applied to every JSON migration.
- **Domain layer** (`/domain/`): Building, BuildingMeta, Envelope, Floor, FloorType, Column, ColumnLocation, DomainGrid. Lightweight dumb dataclasses (`frozen=True`) with `__post_init__` validation.
- **ComponentContract enforcement test** — auto-discovers all top-level `c{NN}_*.py` files and asserts each has a registered contract. The "CI rule" — Pattern B (building without wiring) is mechanically prevented.

**v0.6 Phase 3 — Trust + legal hardening:**
- Renamed `engineer_validated_override` → **`user_claims_engineer_reviewed`**. Reframed: *"We do NOT verify engineer claims, but record name/license/date for the user's audit trail. The engineer is your own consultant; BuildemUp does not verify or endorse them."*
- Added `validation_status: "PENDING ENGINEER VALIDATION"` on every output. With user-claim variant: `"PENDING ENGINEER VALIDATION (user claims engineer reviewed — UNVERIFIED)"`.
- **Critical invariant:** BuildemUp itself can NEVER transition out of "pending" — only the engineer's stamp can.
- Warning: "⚠ ENGINEER OVERRIDE ACTIVE" → **"⚠ UNVERIFIED USER CLAIM"**.
- **Engineering depth axis** — `EngineeringDepth` enum: `LEVEL_1_RULE_BASED` / `LEVEL_2_FRAME_CHECKED` / `LEVEL_3_ENGINEER_DESIGNED`. v0.6 outputs are LEVEL_2. **LEVEL_3 is engineer-only by design** — no `level_3_indicator()` function exists in the codebase. This is intentional; LEVEL_3 cannot be self-promoted.
- **Freshness enforcement** — 3-tier: <cadence = OK, cadence-to-2× = WARN_DEGRADE_CONFIDENCE, >2× = BLOCK_STALE. WARN degrades confidence one level (WELL_CONSTRAINED → REGIONAL_TYPICAL).
- **Legal & statutory disclosures** (`utils/legal_disclosures.py`) — 6-section block in every `explain()`:
  1. Structural engineer required
  2. Indian municipal permit (CMDA/BMC/MCD/BBMP named, "stamped plan" emphasised)
  3. No engineer endorsement
  4. Limitation of liability
  5. PII handling session-only
  6. Preliminary soil + load assumptions caveat
- **PII handling:** `purge_engineer_data(dict)` redacts engineer name/license/date/consultant before logging or export.
- **Frame sanity wired into orchestrator output.** Per-column Bresler interaction shown. Worst 3 columns surfaced if WARN/FAIL.

**State at end:** 164 PASS markers across 11 suites.

## 4.7 Session 7 — Thu 23 April 2026, 14:07 UTC — *v0.7.2 final + Component 1 scoping*

**Source:** `07_2026-04-23-v072-final-c1-scoping.txt` (840 lines)
**Theme:** Component 7 final release (v0.7.2 with insights loop) + Component 1 scoping discussion.

**v0.7 → v0.7.1 → v0.7.2 progression** (incremental polish):
- v0.7: ComponentContract enforcement extended; `_DOMAIN_TYPE_NAMES` set added
- v0.7.1: Domain layer enforcement turned on globally; all existing types registered
- v0.7.2: Insights loop (`utils/insights.py`) — read structured logs, produce weekly summary (most common warnings, cost distribution, failure modes); CSV/text output runnable on demand

**Critical full product vision reveal in this session:**

User articulated the full v1–v4 vision spanning brief → feasibility → engineering layers → 3D → interiors → CAD → permits. Claude pushed back on building it all at once and proposed the phased v1–v4 roadmap that became canonical.

**The three Component 1 scope questions:**
1. v0.1 covers what?
2. Conversational LLM extraction or form-based?
3. Save/resume mechanism?

User's answers (locked):
- v0.1 covers brief capture only — not feasibility (that's Component 2)
- Form-based v0.1; LLM extraction deferred to v2
- localStorage save/resume in v0.1; cross-device deferred

**State at end:** Component 7 v0.7.2 final (the last v1 release of C7 needing major review). 274 tests across 12 suites.

## 4.8 Session 8 — Wed 24 April 2026, 12:35 UTC — *Component 1 v0.1 build (5 sessions)*

**Source:** `08_2026-04-24-c01-v0.1-sessions.txt` (1,295 lines)
**Theme:** SPEC v0.2 lock + 5 build sessions.

**SPEC v0.1 was reviewed and rejected** — 10 drawbacks identified:
1. Plot type missing (DETACHED/SEMI_DETACHED/CONTINUOUS) — Chennai TNCDBR has explicit "Continuous Building Area" rule
2. Setbacks not per-plot-type (CONTINUOUS = front + rear only)
3. Circulation factor missing (1.30 for floor area estimate)
4. Top 3 guidance not surfaced prominently
5. Parking feasibility not checked (plot < 8m + stilt → STRONG_CONCERN)
6. Auto-staircase not added for floors ≥ 2
7. Phased construction not suggested if budget < estimate
8. "ASSUMPTIONS USED" section missing in `explain()`
9. Vastu integration missing — three-tier opt-in
10. Save/resume mechanism missing

All 10 accepted with triage: 9 → real logic/spec changes, 1 → documentation-only.

User answered 5 open questions:
- Q1 currency: INR only
- Q2 email/phone: optional in v0.1
- Q3 save/resume: localStorage + optional email-resume-link (later simplified to localStorage only — server-side resume deferred to v0.2)
- Q4 form UI: Claude builds it (minimal Tailwind HTML)
- Q5 vastu: three-tier OFF/PARTIAL-7-items/FULL, default OFF, all INFO-level only

**SPEC v0.2 LOCKED** (now in `03_project_files/buildemup_C1_SPEC_v0_2_LOCKED.md`). 14 changes from v0.1. Scope **tightened**, not expanded.

**Build sessions S1–S5:**
- S1 — Domain objects (Plot, FloorRequirement, Brief, plus 4 supporting types). All registered in `_DOMAIN_TYPE_NAMES` for v0.7.1 enforcement.
- S2 — Setback calculator (`kb_rules/setback_rules.json` per-city + per-plot-type; `kb_rules/room_minimums.json` NBC minimum sizes; Chennai TNCDBR fully implemented; other cities NBC fallback)
- S3 — Room composition (`room_composer.py` — circulation factor, auto-staircase, parking feasibility; `parking_feasibility.py`; `vastu_filter.py` — partial/full filtering)
- S4 — Budget bridge (`budget_bridge.py` — calls Component 7 in cost-only mode; `phased_construction.py`; `soft_guide_engine.py` — top 3 prioritisation; `assumptions_log.py`)
- S5 — Orchestrator (`c01_brief_capture.py` — `BriefCaptureEngine` class; `explain()` rendering with ASSUMPTIONS USED section; handoff tests)

**State at end:** 379 PASS across 19 suites. Session 6 (Form UI + API endpoint) ready to start.

## 4.9 Session 9 — Fri 25 April 2026, 02:52 UTC — *Component 1 v0.9 sessions A–C*

**Source:** `09_2026-04-25-c01-v09-sessions.txt` (718 lines)
**Theme:** Drawback re-review + SQLite save/resume + Mumbai/Delhi DCR research.

After v0.1 shipped (Session 6: form UI HTML/Tailwind/JS + API endpoint), a re-review surfaced 4 more drawbacks. **v0.9 series** was the response.

**Session A — drawback re-review fixes:**
- Refinement of soft-guide thresholds
- Tightening of assumption tracking

**Session B — SQLite save/resume:**
- `utils/brief_storage.py` — SQLite-backed resume tokens (alongside localStorage)
- 24-hour token TTL
- Token-based recovery via `/api/brief/resume?token=X`

**Session C (mid-flight at end of session):**
- Mumbai DCPR 2034 setback rules researched + JSON updates pending
- Delhi MPD-2021 setback rules researched + JSON updates pending

**State at end:** 438 PASS across 22 suites. Session C JSON updates pending into Session 10.

## 4.10 Session 10 — Fri 25 April 2026, 09:23 UTC — *Component 1 v0.9.1 patch*

**Source:** `10_2026-04-25-c01-v091-patch.txt` (1,003 lines)
**Theme:** Sessions C, D + v0.9.1 patch.

**Session C completion — 6-city DCRs:**
- Chennai TNCDBR (full)
- Mumbai DCPR 2034
- Delhi MPD-2021
- Bangalore BBMP/UDD
- Pune UDCPR
- Hyderabad GHMC G.O. 168

All 6 cities have full real DCRs in `kb_rules/setback_rules.json`. **No NBC fallback for these 6 cities.**

**Session D — assumption tracking polish.**

**v0.9.1 patch — second drawback review:**
- Cost ratio correction: research-backed multiplier values
- ~5 minor fixes

**State at end:** 482 → 502 PASS across 24 suites.

## 4.11 Session 11 — Mon 27 April 2026, 07:15 UTC — *Component 1 v0.9.3 + Component 2 Session A start*

**Source:** `11_2026-04-27-c2-feasibility-session-a.txt` (796 lines)
**Theme:** v0.9.2 + v0.9.3 final patches + dual-design architecture decision + C2 begins.

**v0.9.2 patch:**
- Final tightening of C1
- Test count rises to 220+ across 12 suites for C1 alone

**v0.9.3 patch:**
- Multiplier correction for Component 7 cost call
- (Test file: `test_c07_v093_multiplier_correction.py`)

**The dual-design architecture decision (CRITICAL):**

Reviewing C1 outputs surfaced a question: when the user says "I want 2 ft setbacks" (knowing it's sub-NBC), what should Component 2 (Feasibility) do? Three options were considered:
- (a) Reject and force NBC setbacks
- (b) Generate working setbacks only with non-compliance warning
- (c) Generate BOTH — Practical (user's 2 ft) AND Code-Strict (NBC 5/3/3) — and show the gap

**Decision: (c) — dual-design pattern.** Every brief produces TWO parallel feasibility reports plus a structured Gap analysis showing exactly where they diverge.

This decision shaped the entire Component 2 design. Six of the 17 v0.1 checks are "branched" — they run as `_practical` and `_code_strict` variants. When they diverge, a `Gap` is generated with severity (`MARGINAL` / `SIGNIFICANT` / `BLOCKING_IF_NOT_ACCEPTED` / `INFO_ONLY`).

**C2 Session A — domain objects:**
- `domain/feasibility.py`: `FeasibilityReport`, `DesignGapAnalysis`, `Gap`, `GapSeverity`, `FeasibilityInput`, `FieldSource`
- Domain types registered

**State at end:** 502 → 534 PASS across 27 suites. C2 in progress.

## 4.12 Session 12 — Mon 27 April 2026, 07:31 UTC — *Component 2 Session B (legal-only checks)*

**Source:** `12_2026-04-27-c2-feasibility-session-b.txt` (1,477 lines)
**Theme:** Hard physics checks completed (4) + 6 legal-only checks built.

**4 hard physics checks (unbranched — no Practical/Code-Strict split):**
1. Envelope (plot - setbacks ≥ minimum buildable)
2. Floor stack (height × floors ≤ city max height)
3. Parking width (per RoadWidth + plot type)
4. Budget (actual_floor_area × ₹/sqft ≤ user's budget × 1.1)

**6 legal-only checks (unbranched — strict NBC/DCR rules):**
1. FAR (Floor Area Ratio)
2. Ground coverage (max 50% / 60% / 65% per city)
3. Fire access (≥ 1 side has 6m clear path for vehicles)
4. Electric line (HT/LT clearances per IS 5613)
5. Water course (set distance from drains, canals)
6. Stilt mandate (Mumbai/Delhi >15m height = stilt parking required)

**State at end:** C2 Session B complete. 581 PASS. C2 6 legal-only + 4 physics = 10 of 18 checks done.

## 4.13 Session 13 — Mon 27 April 2026, 11:14 UTC — *Component 2 Sessions A–G (mid-flight)*

**Source:** `13_2026-04-27-c2-sessions-a-through-g.txt` (1,496 lines)
**Theme:** Sessions A–G — full dual-design pattern proven out + the 3-state input pattern + scoring contract + orchestrator.

**The 3-state input pattern (CRITICAL):**

For fields the user might not know (soil type, water table depth, distance from electric line), `FeasibilityInput` wraps each value with a `FieldSource`:
- `USER_PROVIDED_VERIFIED` — user has the test report
- `USER_PROVIDED_UNVERIFIED` — user typed a number but no test report
- `USER_DOESNT_KNOW` — user explicitly said "don't know"
- `NOT_ASKED` — field never asked (defaults to assumed value)

**The downgrade rule (locked):** When an assumed city-default value would `HARD_FAIL` a check, the severity is **downgraded to `SOFT_WARN`**. The system never blocks a homeowner on a guess. But user-provided values — even unverified — keep their strict outcome.

**6 branched checks (Practical + Code-Strict + Gap):**
1. Setbacks
2. Solar (orientation-based)
3. Cross-ventilation (window-to-floor area ratio)
4. Soil (with downgrade rule when DOESNT_KNOW)
5. Water table (with downgrade rule)
6. RWH (Rainwater Harvesting — mandatory above thresholds in 4 of 6 cities)

**Plus 1 info-only check:**
- Approval complexity (simple / medium / complex tier per plot configuration)

**Total: 17 of 18 v0.1 checks shipped.** The 18th (room minimums) deferred to v0.2 because it needs C1 RoomRequirement flag.

**Scoring contract (locked):**
- Start at 100
- Deduct -5/-7/-10 for SOFT_WARN by LOW/MEDIUM/HIGH confidence
- **Any HARD_FAIL caps the score at 40 max**
- The 40 cap is intentional: a single blocker means the design isn't buildable as-stated

**Orchestrator (`components/c02/orchestrator.py`):**
- Single public entry: `run_feasibility(brief, feasibility_input=None) -> DesignGapAnalysis`
- Smoke-tested working
- RWH symmetry fix applied

## 4.14 Session 14 — Mon 27 April 2026, 12:34 UTC — *C2 Sessions C–J + 12-drawback domain review*

**Source:** `14_2026-04-27-c2-sessions-c-through-j-plus-review.txt` (771 lines)
**Theme:** Sessions H, I, J + post-release domain review.

**Session H — renderer + user guide:**
- `components/c02/renderer.py` — text + JSON renderers
- `docs/c02_user_guide.md` — homeowner-facing user guide (NOT engineer-facing)

**Session I — API endpoint + C1+C2 chained:**
- `POST /api/feasibility/run` — accepts brief + feasibility_input, chains C1 + C2 in single call
- Returns: `feasibility_summary_text`, `feasibility_full_text`, `feasibility_data` (full DesignGapAnalysis JSON), `brief_summary`

**Session J — 20-scenario validation suite:**
- 20 scenarios spanning 6 cities, G+0 to G+3, plot sizes from tiny to 1200+ sqm
- Auto-generated `c02_v0.1_validation_report.md`
- **Caught 6 cases where Claude's expected ranges were wrong mid-session** — Chennai-centric assumptions don't match Hyderabad NBC, Code-Strict water_table HARDs more often than expected, Delhi stilt mandate fires earlier. Updated expectations to match reality.

**12-drawback post-release domain review:**
- Reviewer claimed 12 drawbacks
- Per-item evaluation: **3 reviewer claims wrong, 4 partial, 4 valid + 1 INFO-only**
- Reviewer's overall verdict ("production-ready, polish phase") accepted
- Valid drawbacks logged for v0.2 backlog

**State at end:** 738 PASS across 35 suites. README v0.10 section drafted.

## 4.15 Session 15 — Tue 28 April 2026, 05:50 UTC — *C2 Sessions K, L + Bucket A patches*

**Source:** `15_2026-04-28-c2-sessions-c-through-m-deploy.txt` (1,174 lines)
**Theme:** UX uplift across 3 review rounds + deployment process.

**Session K — orchestrator polish:**
- 3 small text-message tweaks
- Total tests rose to 871 across 37 suites
- Marked v0.10 — first deployable post-reset version

**Session L — Bucket A patches:**
- 3 more small text-message tweaks
- Total tests: 901 across 38 suites

**Deployment to Railway begins:**
- Step-by-step PowerShell guidance
- Git workflow: `git add . / git commit / git push origin main`
- Railway auto-deploys in 2–3 minutes
- Verify live: `curl https://buildease-production.up.railway.app/health`

**State at end of Session 15:** v0.10 LIVE on Railway. 913 tests across 39 suites.

## 4.16 Session 16 — Tue 28 April 2026, 05:59 UTC — *Session M (feet/metres) + architecture recall*

**Source:** `16_2026-04-28-c2-deploy-feet-architecture-recall.txt` (2,553 lines — largest session)
**Theme:** Final feet/metres dual-unit UI + a critical reset where user demanded Claude read full chat history to recover the architectural roadmap.

**Session M — feet/metres dual-unit UI:**
- `static/brief_form.html` updated — every dimension input shows both feet and metres
- New `/api/setback/preview` endpoint
- Dual-unit reports in `explain()` text (e.g., "39.4 ft (12.00 m)")
- Tests: 937 across 40 suites

**State after Session M:**
- v0.10.1 zip packaged but **NOT deployed** (Ramalingam was on phone, deferred deploy)
- v0.10 still live (913 tests)
- v0.10.1 packaged (937 tests)

**The architecture recall debate (the critical part of this session):**

User pushed back, asking Claude to read full chat history about the original BuildEase architecture (10 components: room rules, connection graph, placement engine, etc — which is Track 1 in our four-track terminology).

Claude (correctly, after pushback) read the transcripts and found:
- The Track 1 (10-component) numbering exists in the OLD codebase but was superseded by v3 architecture
- The current C1/C2/C7 numbering is Track 2 (codebase) which maps to Track 3 (canonical 17-component v3)
- The 17 components in v3 are the canonical build target
- Of the 17, only 1, 2, 7 are built (as c01, c02, c07)
- 14 components (3, 4, 5, 6, 8, 9, 10, 11a, 11b, 12, 13, 14, 15, 16, 17) remain to be built

User's frustration: previous Claude sessions had been building C1/C2/C7 without surfacing the context that 14 more components are pending. The recall corrected that.

**End of Session 16:** Mid-conversation, the Claude session died. Ramalingam started a new chat (this one) and uploaded the full archive on 29 April.

## 4.17 Session 17 — Wed 29 April 2026 — *Master Doc Recovery + Component 3a Spec + S1 Build*

**Source:** Live conversation, this session.
**Theme:** Full project recovery from comprehensive archive; complete spec process for Component 3 (split into 3a + 3b); S1 build of Component 3a domain types shipped with all 53 tests passing.

**This was the longest, most decision-dense session in the project's history.** It covered four distinct phases:

### Phase 1 — Master document recovery (early in session)

Ramalingam uploaded `1777425962270_BUILDEMUP_COMPLETE_ARCHIVE_2026-04-29.zip` (27 MB, 213 files) — the complete archive including all 16 prior sessions, all source documents, the current codebase, all snapshots. Instruction: *"I want you to have a 100% clear idea about what we did and actually understand them."*

Claude built `BUILDEMUP_MASTER_DOCUMENT_v2.md` covering Parts 0–11 + Appendices A–D. Key features:
- Founding contractor story in Part 0
- Four numbering schemes explicit in Part 1
- 5 patterns to avoid in Part 2 (the "without making same mistakes again" mandate)
- Era 2 chronological history of sessions 1–16 in Part 4
- Architecture v3 + Design Principles v3.1 in Parts 5–6
- File inventory + build status + decisions log in Parts 7–9
- Where We Continue in Part 11

User then requested: embed all production code + tests + docs in the master doc. Claude built v2.1 (2.40 MB, 60,118 lines, 146 embedded files) plus the Update Protocol in Part 13.

### Phase 2 — Component 3 split + spec drafting

User asked: should Trade-off Negotiation come before or after layout generation? Claude pointed out Component 3 actually has two separable jobs:
- **Component 3a** — Extreme Case Gate (pre-layout, "you must decide", small scope)
- **Component 3b** — Post-Layout Trade-off Negotiation (after user sees layouts, bigger scope)

User locked Path: build C3a now + layout pipeline after.

Claude drafted SPEC v0.1 with 10 Extreme Cases and 5 open questions. User asked Claude to web-research Q1 (budget threshold). After 15-source research, threshold locked at × 1.5 (50% over budget) — research showed industry-average overrun is 15-28%, contingency buffer is 10-15%, phased construction absorbs 30-40% gaps, top-up loans cover 20-35%; beyond 50% no standard mechanism bridges. Spec bumped to v0.1a.

### Phase 3 — Two critique rounds + spec hardening

User pasted in critique document #1 (10 issues). Claude evaluated:
- 6 fully valid (#1, #4, #5, #6, #8, #10) — accepted
- 2 valid with caveats (#2, #3) — modified
- 2 partially wrong (#7, #9) — pushed back

Claude then web-researched Q3 (decision logging), Q4 (TNCDBR plot type rules), Q5 (UX banner triggers). Locked all 8 changes + Q2-Q5 + Reactions 1-2 (counterfactuals on final screen, CBA verify with email checklist).

User then asked: "even after all hard fails, can user see a layout?" Claude proposed **Preview Mode** — single layout, no regulatory drawing, no BOQ, no contractor pack, watermarks. User approved. Spec locked as v0.2 (1,059 lines).

User pasted in critique document #2 (8 issues, all production-readiness). Claude evaluated:
- 5 fully valid (#1 CRITICAL Preview Mode misuse, #2, #4, #6, #7) — accepted
- 2 valid with caveats (#3, #8) — modified
- 1 partially rejected (#5) — modified, kept Preview in counterfactuals

Spec locked as v0.2.1 (1,343 lines). Major v0.2.1 hardening:
- Mandatory checkbox + room-overlay watermarks + dimension ranges for Preview Mode
- Preflight summary screen before first EC modal
- Early "wrong plot" hint when severe single-EC fires
- Cost confidence with caveat language (kept numbers, added aggressive caveats)
- 24h CBA fallback endpoint
- Reason-aware BriefChange errors
- Transition banner trigger on case_id (not category)

### Phase 4 — S1 build (Domain Objects)

Claude built `domain/extreme_case.py` (736 lines, 15 types: 5 enums + 10 dataclasses) and `tests/test_c03a_session1_domain.py` (791 lines, 53 tests). All 53 tests passing on first run after fixing one count miscalibration (5+10=15 not 13).

Tests catch all critical invariants:
- Q3 Level B logging — chosen_option_id must be in presented_options
- Critique #1 CRITICAL — Preview Mode requires PreviewModeAcknowledgment
- Critique #5 — Max 2 alternatives in CounterfactualSummary
- Critique #8 — Preview Mode option must be last
- Critique #3 — LOW confidence auto-populates ±40% caveat
- Section 4.5 — BUILDABLE/PREVIEW mode-specific field rules
- Frozen dataclass immutability

**Key decisions in this session:**
- ✅ D-047 — Component 3 split into 3a (pre-layout) and 3b (post-layout)
- ✅ D-048 — 10 ECs locked with specific detection thresholds
- ✅ D-049 — Preview Mode added with hard guardrails (mandatory checkbox, room-overlay watermarks, dimension ranges, no construction details)
- ✅ D-050 — Build order Path C: C3a now, layout pipeline after
- ✅ D-051 — EC-008 budget threshold × 1.5 (web-research-backed)
- ✅ D-052 — Decision logging Level B (chosen + presented option set)
- ✅ D-053 — No plot type toggling DETACHED↔CONTINUOUS; advisory only with email checklist
- ✅ D-054 — Two-tier budget (1.25× soft warn, 1.5× hard EC) per critique #1
- ✅ D-055 — Preview Mode requires explicit checkbox + room-internal watermarks per critique #1 v0.2.1

**Code changes:**
- Created: `domain/extreme_case.py` (736 LOC, 15 types) — S1 deliverable
- Created: `tests/test_c03a_session1_domain.py` (791 LOC, 53 tests) — S1 deliverable
- Created: `docs/component3a/SPEC_v0.2.1_LOCKED.md` (1,343 lines) — locked spec for build

**State at end of session:**
- 974 PASS across 41 suites (937 baseline + 53 new in C3a Session 1; one suite added; -16 because new tests don't yet roll into deployed build, that needs S8 integration)
- C3a S1 ✅ shipped (in-build directory, not yet integrated into main repo)
- C3a S2-S8 pending — must continue in next conversation
- Master doc bumped to v2.2

**Why session paused at S1:** Conversation context was consumed by the spec-drafting work (4 review rounds, web research, two critique rounds). Pushing through S2-S8 would risk incomplete or buggy mid-build code. S1 is the cleanest checkpoint — domain types are foundational; everything downstream imports them. Resumption protocol: next Claude reads master doc + SPEC v0.2.1 + S1 deliverables, then begins S2.

---

## 4.18 Session 18 — Wed 30 April 2026 — *Component 3a Session 2: Detection logic*

**Source:** Live conversation, this session.
**Theme:** S2 build of Component 3a — detection logic for all 10 Extreme Cases.

### Context entering the session

The previous Claude (analysis-session at end of Session 17, late 29 April) prepared a comprehensive handoff package: 5 orientation files (00–04), 15 curated dependency files in `QUICK_REFERENCE_dependency_files/`, the locked SPEC v0.2.1, the 53-test S1 deliverable (`domain/extreme_case.py`), all 17 prior session transcripts, the master doc, and 3 conversation artifacts capturing 5 resolved Q&As and 2 corrections. Reading order was prescribed; the build plan in file 03 contained complete code for both the detector and the test file.

### What happened

- S2 Claude read the orientation package thoroughly (files 00–04, S1 deliverable, all 6 quick-reference dependency files, SPEC Section 2.2 ECs in full). Verified all 10 C2 check_ids referenced in the build plan match real C2 source by grep.
- Honest budget assessment: build fits, master doc + handoff updates were the squeeze point. User authorised proceeding with the contingency that any rushed doc work would be deferred cleanly.
- Built `components/c03a/__init__.py` (empty), `components/c03a/detector.py` (~570 LOC), `tests/test_c03a_session2_detection.py` (~290 LOC, **18 tests** — overshoot of the 12-test target because EC-002 three-tier and EC-008 two-tier each got their own boundary tests).
- All 18 S2 tests passed on first run. All 53 S1 tests still pass alongside (71/71 combined).
- Applied 7 patches: 2 code (Patch 6 in `domain/extreme_case.py` for the 8→10 dataclasses comment; Patch 7 in `utils/component_contract.py` registering 15 C3a domain type names) + 5 SPEC documentation patches (bumping spec to v0.2.1a). Verification: `set(EXTREME_CASE_DOMAIN_TYPE_NAMES) - _DOMAIN_TYPE_NAMES == ∅`.
- Surfaced 4 v0.2-backlog items (B-001 through B-004 in `docs/component3a/v0.2-backlog.md`).

### Key decisions locked

- **D-057** — EC-010 surfaces highest-impact blocker first when multiple `legal_only_checks` fire simultaneously. Sorting key: `LOW resolution_probability` < `MEDIUM` < `HIGH`. The detector returns one ExtremeCase for EC-010 (the highest-impact one), not one per blocker. Rationale: surfacing N approval blockers in N modals creates decision paralysis; the worst one drives the user's path-to-different-plot decision and the rest are remediated naturally once the worst is addressed (or the plot is changed).
- **D-058** — Detector returns ExtremeCase objects with **placeholder ResolutionOption pairs**. S3 (`option_generator.py`) replaces them. Rationale: `ExtremeCase.__post_init__` requires ≥2 options; rather than have the detector hand-craft real options (S3's job), it produces a pair of identical placeholders. S3 is the option generator. Pattern B (building without wiring) doesn't apply because S6 orchestrator threads detector→generator→applier. The detector is wired via the public `ExtremeCaseDetector.detect()` API.

### Code changes

- **Created:** `components/c03a/__init__.py` (empty)
- **Created:** `components/c03a/detector.py` — 570 LOC, 10 detection functions + `ExtremeCaseDetector` public API
- **Created:** `tests/test_c03a_session2_detection.py` — 290 LOC, 18 tests across all 10 ECs + edge cases
- **Patched:** `domain/extreme_case.py` line 725 — comment fix "8 dataclasses" → "10 dataclasses" (no behavior change)
- **Patched:** `utils/component_contract.py` lines 149–168 — registered 15 C3a types in `_DOMAIN_TYPE_NAMES`
- **Patched:** `docs/component3a/SPEC_v0.2.1.md` → bumped to **v0.2.1a** with 5 documentation corrections (EC-003 detection wording, EC-006 dedup note, EC-008 code-level note, type counts in §3.2 and §13.S1)
- **Created:** `docs/component3a/v0.2-backlog.md` with 4 items (B-001 helper, B-002 line_type field, B-003 Mumbai/Pune stilt thresholds, B-004 circulation factor reconciliation)

### State at end of session

- C3a S1 + S2 ✅ shipped (in build directory)
- 1,008 PASS in isolated build dir (937 v0.10.1 baseline + 53 S1 + 18 S2); 71 new tests across 2 new C3a suites
- C3a S3-S8 pending — must continue in next conversation
- SPEC v0.2.1a (documentation patches; behaviorally identical to v0.2.1)
- Master doc bumped to v2.3

---

## 4.19 Session 19 — Wed 30 April 2026 — *Component 3a Session 3: Option generation*

**Source:** Live conversation, this session.
**Theme:** S3 build of Component 3a — real ResolutionOption generation for all 10 Extreme Cases, replacing S2's placeholder pairs.

### Context entering the session

End of Session 18 (S2 build) prepared a comprehensive S3 handoff package: 5 orientation files (00–04) tailored for option generation, 16 curated dependency files in `QUICK_REFERENCE_dependency_files/`, the locked SPEC v0.2.1a, the 71-test S1+S2 deliverable, all 18 prior session transcripts, the master doc at v2.3, and an embedded build plan (file 03) with complete code for EC-001/002/003 verbatim plus per-EC patterns for the remaining 7 ECs.

### What happened

- S3 Claude read the orientation package in full and confirmed reading order before any coding. Honest budget assessment: build fits comfortably, doc updates the heavy tail.
- Built `components/c03a/option_generator.py` (~1758 LOC after patch — verbose but the verbosity IS the user-facing copy that S6 will surface in modals; logical density is identical to the build plan).
- Built `tests/test_c03a_session3_options.py` (~761 LOC, **29 tests**) — overshooting the 10-test minimum to cover precondition guards (5 added later in-session, see below) plus comprehensive coverage of recommendation logic, BriefChange operation enum compliance, dispatch invariants, and special-action wiring.
- All 24 S3 tests passed on first run. 71 c3a tests still passed alongside (95/95 combined). Full buildemup suite: 991/991.
- Mid-session, Ramalingam ran the source through an external critique and shared a 10-point drawback document. S3 Claude analyzed each drawback, classified them (1 invalid, 3 already-known/planned, 6 valid-but-backlog, 1 open question), and pushed back where appropriate. Ramalingam approved a precondition-guard patch for the one open question (drawback #3b).
- Patched: EC-001 op B, EC-002 op A, EC-007 op B, and EC-008 op B (chain) all gained precondition guards via two new helpers (`_can_reduce_bedrooms`, `_can_reduce_floors`). When a guard trips, the option is emitted with empty `requires_brief_change=()`, `recommended=False`, and a clear `risk_advisory` explaining why — option count stays stable to preserve spec invariants.
- Added 5 precondition-guard tests in a new `TestPreconditionGuards` class. Final c3a count: **100 tests passing** (53 S1 + 18 S2 + 29 S3). Full buildemup: 996/996.
- Surfaced 9 new v0.2-backlog items (B-005 through B-013), bringing the backlog total to 13.
- Locked the **S4 SPEC v0.1** as a separate document (`buildemup_S4_SPEC_v0_1_LOCKED.md`, 568 lines). Covers BriefChange application + reason-aware errors per parent spec Sections 3.3 and 4.8.

### Key decisions locked

- **D-059** — BriefChange `field_path` vocabulary as emitted by S3 is locked for S4 to interpret. The 11 paths in S3-spec §4 (S4 spec) are the canonical alphabet. Refinement, if needed, is a coordinated S3+S4 change tracked as B-005.
- **D-060** — Precondition guards in option generator emit non-violating options as informational-only (empty BriefChange + risk_advisory), never as missing options. Rationale: preserves the spec invariant on per-EC option counts; the user always sees the same option list shape; only actionability changes.
- **D-061** — Locked S4 SPEC v0.1 separately from parent C3a SPEC v0.2.1a. Parent spec is the umbrella; per-session locked specs are the build-ready derivatives. Pattern established: each session shipping >100 LOC source gets its own locked spec written before build start.

### Code changes

- New: `components/c03a/option_generator.py` (1758 LOC including 4 precondition-guard patches)
- New: `tests/test_c03a_session3_options.py` (761 LOC, 29 tests)
- New: `buildemup_S4_SPEC_v0_1_LOCKED.md` (568 lines, top-level spec for next session)
- Append to: `v0_2_backlog.md` — 9 new items (B-005 through B-013)

### Test count delta

- Start of session: 71 c3a tests, 991 buildemup tests
- End of session: 100 c3a tests, 996 buildemup tests
- Net delta: +29 c3a, +5 buildemup-wide

### State at end

- C3a S1, S2, S3 ✅ shipped. S4 SPEC v0.1 LOCKED.
- Next session: S4 — BriefChange application + reason-aware errors. Follow `buildemup_S4_SPEC_v0_1_LOCKED.md`.

---

## 4.20 Session 20 — Thu 30 April 2026 — *Component 3a Session 4: BriefChange application + reason-aware errors*

**Source:** Live conversation, this session.
**Theme:** S4 build of Component 3a — applying BriefChanges produced by S3 to a Brief and rendering classified validation errors when application produces an invalid Brief.

### Context entering the session

End of Session 19 (S3 build) prepared a comprehensive S4 handoff package: 5 orientation files (00–04) tailored for BriefChange application, 15 curated dependency files in `QUICK_REFERENCE_dependency_files/`, the locked S4 SPEC v0.1 (568 lines), the locked parent SPEC v0.2.1a, the 100-test S1+S2+S3 deliverable, all 19 prior session transcripts, the master doc at v2.3 (with v2.4 deltas pending), a `POST_S4_DRAWBACK_LIST.md` flagging 6 deferred drawbacks, and a fresh handoff doc.

### What happened

- Ramalingam initially asked Claude to build S4 *and* S5–S8 in one session. Claude pushed back: only S4 had a locked spec (Obligation 1), S5–S8 specs had not been through the draft → critique → lock cycle, the S4 budget alone was estimated at ~100% with no margin (Obligation 2), and combining unspecced sessions into one build would be Pattern E (scope creep mid-build, the project's most expensive failure mode). Ramalingam agreed to S4-only and asked for a clean S5 handoff package with an integrity check.
- S4 Claude read the 5 orientation files, the locked S4 spec in full, the parent C3a spec § 3.3 / 4.1[8] / 4.8, S1's `extreme_case.py` (BriefChange + BriefChangeIntegrityError + ResolutionOption), S3's `option_generator.py` (the BriefChange emitters), and 3 dependency files (`brief.py`, `setbacks.py`, `floor_requirement.py`).
- During reading, noticed that resolved-question Q7 in `02_S4_RESOLVED_QUESTIONS.md` understated `Setbacks.__post_init__` — the actual code DOES validate negative + >15m. Trusted the code over the spec note (per Obligation rule "verify against the live source files"). This means setback-handler ValueErrors flow through the classifier and currently fall through to UNKNOWN; surfaced as B-014 in the v0.2 backlog.
- Built `components/c03a/brief_change_apply.py` (~761 LOC including docstrings; ~500 code-only) — 13 dispatch handlers + setback-factory + classifier helpers + public API. Larger than the S4 spec's ~180 LOC estimate (which the spec itself acknowledged was an undercount; spec's realistic estimate was ~260). The bulk is defensive input validation per handler.
- Built `components/c03a/error_formatter.py` (~128 LOC; ~63 code-only) — 6 templates + plain-text guarantee + UNKNOWN fallback that swallows `format()` errors so the formatter never raises.
- Built `tests/test_c03a_session4_apply.py` (~555 LOC, **13 tests**: 12 unit + 1 integration smoke per S4 spec § 9.1 + § 9.3).
- Built `tests/test_c03a_session4_error_formatter.py` (~229 LOC, **8 tests** per S4 spec § 9.2).
- All 21 S4 tests passed on first run. C3a suite: **121 / 121 PASS** (53 S1 + 18 S2 + 29 S3 + 21 S4) — exactly the spec target.
- Applied v2.4 deltas (deferred from Session 19) and v2.5 deltas to master doc together.
- Surfaced 1 new backlog item (B-014, Setbacks UNKNOWN classification refinement).
- Did NOT lock an S5 spec — explicitly deferred per the Pattern E push-back at session start. S5 spec is the next session's first task (per the handoff Claude is now producing).

### Key decisions locked

- **D-062** — S4 BriefChange application is purely declarative (full-replace via `dataclasses.replace`, no in-place mutation). Every handler returns a new Brief; the input is never touched. Earlier successful applies in `apply_brief_changes` are NOT rolled back on a later failure because there's nothing to roll back — the input Brief is its own rollback. Pattern carried forward to all C3a appliers (B-011 schema migration will preserve this).
- **D-063** — Reason-aware error formatter is a separate module from the applier (`error_formatter.py` ≠ `brief_change_apply.py`). Applier raises classified `BriefChangeIntegrityError` (with `classification` + `context` dict); formatter renders to user-facing copy. Rationale: lets S6 log structured errors before rendering, lets S7 serialize errors as JSON cleanly, isolates copy changes from applier tests.

### Code changes

- New: `components/c03a/brief_change_apply.py` (761 LOC, 18 functions)
- New: `components/c03a/error_formatter.py` (128 LOC)
- New: `tests/test_c03a_session4_apply.py` (555 LOC, 13 tests)
- New: `tests/test_c03a_session4_error_formatter.py` (229 LOC, 8 tests)
- Append to: `v0_2_backlog.md` — 1 new item (B-014)

### Test count delta

- Start of session: 100 c3a tests, 996 buildemup tests
- End of session: 121 c3a tests, 1017 buildemup tests
- Net delta: +21 c3a, +21 buildemup-wide

### State at end

- C3a S1, S2, S3, S4 ✅ shipped. **4 of 8** sessions done.
- 121 / 121 c3a tests passing.
- S5 spec not yet locked — will be drafted at the start of Session 21.
- Master doc bumped from v2.3 → v2.5 (both v2.4 + v2.5 deltas applied this session).
- Next session: lock S5 spec (Counterfactual + Preflight builders), then build.

---

## 4.21 Session 21 — Thu 30 April 2026 (continuation) — *Component 3a Session 5: Counterfactual + Preflight builders*

**Source:** Live conversation, continuation of Session 20.
**Theme:** Retired D-061 mid-session at user's request; locked new build-cycle rule (D-066); S5 spec drafted, critiqued (round 1), patched to v0.2, locked at v1.0; S5 code built; S5 code critiqued (round 2), patched to v1.1; all delivered to user as standalone code files.

### Context entering the session

End of Session 20 produced an S5 handoff package with S5 spec NOT yet locked (per D-061 discipline). Mid-session, Ramalingam asked Claude to retire D-061 — wanting to keep building in the same conversation rather than handing off, while still requiring external critique on every spec.

### What happened — discipline / process changes

- **D-061 retired.** New rule D-064 supersedes: sessions continue building until Ramalingam decides to stop, not at session boundaries. External critique on every spec is non-negotiable; what changes is that lock-then-build can happen in the same conversation.
- **D-066 locked.** New mandatory build cycle: spec draft → external critique → patch → lock → code → external code critique → patch → next session. Repeat until user says hand off. Context budget reported honestly so user makes the stop decision.
- Each step's output is delivered to the user as a standalone file (spec as `.txt`, code as `.py`).

### What happened — S5 build

- **S5 SPEC v0.1 drafted** based on parent spec § 4.6 / 4.7 / 3.1, packaged as `.txt` for external critique.
- **Critique round 1** returned 12 drawbacks. Claude analysed each: 4 patches accepted (P1 acronym preservation, P2 hint reasons inline, P3 severity-aware messaging, P4 detector contract test); 8 deferred to backlog (B-016 through B-025) with explicit rationale; Drawback 4 (cap of 2 alternatives) rejected as it contradicts parent spec critique #5 round; Drawback 9 (city-aware messaging) recategorised from initial REJECT to BACKLOG (B-025) after thorough analysis showed real product value.
- **S5 SPEC v0.2 → LOCKED v1.0** after user approved patched version.
- Built `components/c03a/counterfactual.py` (~161 LOC), `components/c03a/preflight.py` (~331 LOC), three test files (`test_c03a_session5_counterfactual.py` 12 tests, `test_c03a_session5_preflight.py` 17 tests, `test_c03a_session5_detector_contract.py` 8 tests).
- All 37 S5 tests passed (after 2 mid-build fixes: ExtremeCaseCategory.value is uppercase so labels needed `.lower()`; an "all critical" branch needed an explicit phrasing path).
- Full c3a suite: 121 + 37 = **158 / 158 PASS**.
- **Code critique round 2** returned 4 drawbacks. Claude analysed: D1 (None crash on space_impact_sqft) verified INVALID per type contract but added defensive assertion + test as fail-loud safety net; D2 (hardcoded strings) accepted as lightweight via module constants while keeping B-023 as the proper long-term fix; D3 subsumed by D1 fix; D4 (any() triple-scan) accepted as clarity refactor.
- **Code v1.1 produced** with all critique fixes; 158/158 still passing.
- Delivered as `S5_all_code_consolidated_v1_1.py` (1,600 lines, all 5 files in one).

### Key decisions locked

- **D-064** — Retired D-061. Sessions continue building until user decides to stop, not at session boundaries. External critique on every spec is non-negotiable.
- **D-065** — When critique round disagrees with prior locked critique decisions (Drawback 4 of S5 round 1 wanted to lift the cap-of-2 that v0.2.1 critique #5 had locked), Claude pushes back on the new critique with the prior decision's rationale rather than churning. Documented disagreement goes to backlog (B-019) for revisit if real user data accumulates.
- **D-066** — Build cycle for every C3a session: spec draft → critique → patch → lock → code → code critique → patch → next session. Each step's output delivered to user as a standalone file. User decides when to hand off; Claude reports context budget honestly. This is now mandatory for S6, S7, S8 and any future component build.

### Code changes

- New: `components/c03a/counterfactual.py` (180 LOC after v1.1 fixes)
- New: `components/c03a/preflight.py` (345 LOC after v1.1 fixes)
- New: `tests/test_c03a_session5_counterfactual.py` (323 LOC, 12 tests)
- New: `tests/test_c03a_session5_preflight.py` (389 LOC, 17 tests)
- New: `tests/test_c03a_session5_detector_contract.py` (300 LOC, 8 tests, P4)
- Append to: `v0_2_backlog.md` — 11 new items (B-015 through B-025; B-014 was added in S4 session)

### Test count delta

- Start of session: 121 c3a tests
- After S5 ship: 158 c3a tests
- Net delta: +37 c3a

### State at end

- C3a S1, S2, S3, S4, S5 ✅ shipped. **5 of 8** sessions done.
- 158 / 158 c3a tests passing.
- New build-cycle rule (D-066) in force.
- Master doc bumped v2.5 → v2.6.
- Next session: S6 (Orchestrator). Spec drafting begins per D-066 cycle.

---

## 4.22 Session 21 (continuation) — Thu 30 April 2026 — *S6 spec cycle + B-027 prerequisite ship*

**Source:** Live conversation, continuation of Session 21.
**Theme:** S6 spec drafted v0.1 → critiqued (round 1, 12 drawbacks) → patched to v0.2 → critiqued (round 2, 12 drawbacks) → patched to v0.3 patch addendum → critiqued (round 3, clean) → ready to lock at v1.0. Mid-cycle: prerequisite work B-027 surfaced (S1 + S3 + S5 changes) → drafted, critiqued, locked, coded, code-critiqued, fixed, shipped. Net result: 165/165 tests passing; B-027 v1.1 done; S6 v1.0 LOCKED ready for next-conversation code build.

### S6 spec cycle

- **S6 v0.1** drafted from parent spec § 4.1–4.5 + § 4.8 + § 6 + § 9.5
- **Critique round 1** returned 12 drawbacks. Verdict: 6 must-fix (D1, D2, D4, D7, D8, D10), 1 must-clarify, 2 small fixes, 2 backlog items, 2 acceptable. **D7 (feasibility_input dropped on re-run)** was a real bug — caught only by external review.
- **S6 v0.2** patched: typed banner events (P1), is_different_plot_option flag plumbing (P2 — required B-027 prereq work), failed-option-id tracking (P3), feasibility_input plumbed through every C2 call (P4), caller-supplied user_acknowledged_at (P5), sticky promotion across all subsequent cases (P6); plus C1/C2/C3 small fixes; 3 new backlog items.
- **Critique round 2** on v0.2 returned 12 drawbacks. Verdict: 4 must-fix (D6 frozenset, D8 public severity API, D12 iteration_index docs); rest backlog or rejected. Reviewer: "very close to lock; refinement-level not structural debugging."
- **S6 v0.3** patch addendum produced (surgical: ~24 LOC delta). 5 new backlog items (B-030 through B-034).
- **Critique round 3** verdict: clean. Ready to lock at v1.0.
- S6 v1.0 LOCKED produced by merging v0.3 patches into v0.2 — file `buildemup_S6_SPEC_v1_0_LOCKED.txt` ready in handoff package.

### B-027 prerequisite shipped

- **Surfaced by:** S6 critique round 1 D2 (string-matching brittle for "different plot" identification) + D8 (S6 importing private `_classify_severity` from S5).
- **Spec cycle:** v0.1 drafted → critique round 1 (4 must-fix: D1 mutual exclusivity, D3 helper coverage, D4 single-option, D8 rename safety) → v0.2 patched → critique round 2 (D3 string-matching test brittleness, helper misuse guard, rename alias safety, documentation gap) → v0.3 patched (P5 structural test, P6 structural validation, P7 backward-compat alias, P8 documentation) → **critique round 3 verdict CLEAN** → v1.0 LOCKED.
- **Code built:** S1 (`is_different_plot_option` field + P1 + P6 validation), S3 (`_build_different_plot_option` helper + 6 sites refactored), S5 (rename `_classify_severity` → `classify_case_severity` + backward-compat alias).
- **Code critique round** returned 10 drawbacks. Verdict: 2 must-fix accepted (D1 spec drift acknowledged + B-035; D8 deprecation wrapper); 4 backlogged (B-035/036/037/038); 3 pushed back per D-065 (D3 caller detection hostile to tests; D5 graceful degradation would mask bugs; D7 rule engine YAGNI on 3 named predicates).
- **B-027 v1.1 shipped** with deprecation wrapper for `_classify_severity` (emits `DeprecationWarning` instead of silent alias).
- **One real finding during build:** spec listed `{EC_002, EC_004, EC_005, EC_006, EC_007, EC_010}` as having different-plot options. Actual S3 source emits them only for `{EC_002, EC_003, EC_006, EC_009, EC_010}`. Spec was wrong on three ECs (EC_004/005/007 don't have them; EC_003/009 do). Test uses source-of-truth contract from code review. B-035 logged for first-class constant.

### Key decisions locked this continuation

- **D-066 v2** — Refined per user clarification: build cycle is **spec → spec analysis → patch → final lock → code → code analysis → patch code → next build**. Continue building until USER says stop. Claude does NOT suggest handoff. Claude does NOT mention context budget casually. ONE EXCEPTION: if context is genuinely too low to complete current step at quality, Claude tells user straight as a quality-protection signal (not a stop prompt). Claude is honest about it once when it matters; doesn't repeat it.
- **D-067** (NEW) — Critique reviewer over-architecture pushback rule. Per D-065, prior decisions and YAGNI principles outweigh latest critique's verdict when the latest critique would: (a) require Pattern E surgery for hypothetical future need, (b) optimise for cases that don't exist yet, (c) overcorrect with hostile mechanisms (e.g., caller detection in tests, graceful degradation that masks invariant violations). Pushback documented in code-critique response so user can override if they disagree. B-035 through B-038 are the deferred items from B-027 code critique applying this rule.

### Code changes

- New: B-027 patches across:
  - `domain/extreme_case.py` (770 LOC, +50 from baseline) — field + 2 validation blocks
  - `components/c03a/option_generator.py` (1,797 LOC) — helper + 6 sites refactored
  - `components/c03a/preflight.py` (382 LOC) — rename + deprecation wrapper
  - `tests/test_c03a_session1_domain.py` (899 LOC) — +4 B-027 tests
  - `tests/test_c03a_session3_options.py` (880 LOC) — +1 structural presence test
  - `tests/test_c03a_session5_preflight.py` (442 LOC) — rename + 2 deprecation tests
- New file produced: `buildemup_S6_SPEC_v1_0_LOCKED.txt` (~1,250 lines) — ready for S6 build session
- Append to `v0_2_backlog.md`: B-030, B-031, B-032, B-033, B-034 (S6 v0.3); B-035, B-036, B-037, B-038 (B-027 code-critique deferrals)

### Test count delta

- Start of session 21: 121 c3a tests
- After S5 ship: 158
- After B-027 ship: **165** c3a tests (+44 net for full session)

### State at end

- C3a S1, S2, S3, S4, S5 + B-027 ✅ shipped. 5 of 8 sessions done; prerequisite for S6 done.
- 165 / 165 c3a tests passing across 8 suites.
- S6 v1.0 LOCKED, ready for next conversation to code (~790 LOC source + ~940 LOC tests).
- D-066 build cycle locked: spec → analysis → patch → lock → code → analysis → patch → next, until user stops.
- D-067 critique-pushback rule locked.
- Master doc bumped v2.6 → v2.7.
- Backlog: 35 items (B-001 through B-038, with B-026 superseded into B-023).
- Next conversation: build S6 (Orchestrator) per locked v1.0 spec.

---

## 4.23 Session 22 — Thu 30 April 2026 — *Component 3a Session 6: Orchestrator built + 2 code-critique rounds*

**Source:** Live conversation, Session 22 (fresh start with handoff_s6 package).
**Theme:** Code build of S6 from locked v1.0 spec → first code-critique round (15 drawbacks) → 1 fix applied + 6 deferred + 8 pushed back per D-067 → second code-critique round (10 drawbacks on the fix itself) → 2 fixes applied + 7 pushed back. **188/188 c3a tests passing across 12 suites at session end.** Pattern D forming on round 3 — call to move on accepted.

### Context entering the session

- Handoff package `handoff_s6/` extracted with locked S6 v1.0 spec, parent C3a v0.2.1a spec, v0.3 patch addendum, S1–S5 + B-027 deliverables, master doc v2.7, backlog through B-038.
- Starting state: 165/165 c3a tests across 8 suites.

### What happened — code build

- **Spec analysis surfaced 6 inconsistencies** between v1.0 LOCKED file and v0.3 patch addendum / parent spec § 3.1 actual ResolvedBrief shape. Resolved without spec deviation:
  1. Frozenset vs tuple inconsistency (§ 3.1 declares frozenset; § 5.3 example still uses tuple `+ (...,)` syntax) → used frozenset per the type declaration + Q7's `| {...}` syntax.
  2. `_classify_severity` deprecated import in § 5.5 → used public `classify_case_severity` per v0.3 S-2.
  3. § 5.6 ResolvedBrief shape uses outdated names (`current_brief`/`gap_analysis`/`aborted=`/`abort_reason=`) → followed actual S1 shape (`revised_brief`/`final_feasibility`/`decision_log: ExtremeDecisionLog`) per § 2.1's directive "populate per parent spec § 3.1's ResolvedBrief shape".
  4. Q11 prescribes `unresolved_blockers=remaining_cases` for abort paths but S1 invariant requires empty `unresolved_blockers` when `mode=BUILDABLE` → for abort paths used `unresolved_blockers=()`, preserved cases on `GateState.remaining_cases`, signalled abort via `decision_log.aborted/abort_reason`.
  5. Spec gap on `started_at`/`completed_at` timestamps in `ExtremeDecisionLog` (required by S1, but P5 forbids time side effects in S6) → derived from `decisions[0/-1].user_acknowledged_at`; empty string when no decisions exist.
  6. Spec gap on OptionGenerator wiring (detector returns placeholder options; spec doesn't explicitly call OptionGenerator but `case.options` is referenced throughout) → wired in `_generate_real_options` helper after detection, per parent § 4.1 [4].
- **Three source files built** (LOC actual vs spec target):
  - `components/c03a/gate_state.py` — 178 LOC (vs ~120 target; +58 mostly docstrings + invariant documentation)
  - `components/c03a/gate_termination.py` — 103 LOC (vs ~70 target; +33 docstrings)
  - `components/c03a_extreme_case_gate.py` — 1,053 LOC (vs ~600 target; +453 from explicit `_build_*_resolved_brief` helpers + docstrings + branch helpers like `_terminate_cba_verification`)
- **Four test files built** with 23 tests total (vs spec 19; +2 bonus validation-raises tests + 2 immutability tests added across the two critique rounds): happy 7, termination 7, error_path 3, v0_2_patches+immutability 6.
- **Initial deliverable: 186/186 c3a tests passing** (165 + 21 S6).

### What happened — code-critique round 1 (15 drawbacks)

| # | Drawback | Verdict |
|---|---|---|
| 1 | State size / DTO layer | DEFER — S7 territory (spec § 2.2 says S7 owns persistence) |
| **2** | **Dict mutability inside frozen state** (`per_case_iteration_counts: dict[str, int]`) | **APPLIED** — typed as `Mapping[str, int]`, wrapped in `MappingProxyType` at all 6 construction sites + `_EMPTY_COUNTS` sentinel + `_freeze_counts` helper |
| 3 | Termination edge case coupling | PUSHED BACK — orchestrator validates `case_id` before calling `determine_termination`; "detector silently changes IDs" is a contract violation S2 tests catch |
| 4 | Option generation caching | DEFER — premature; <70 calls per max-iteration session, no measured latency. **B-039 logged** |
| 5 | All-options-fail lockout | PUSHED BACK — Preview Mode (separate branch) + `apply_user_abort` always available; auto-fallback would be Pattern A bandage |
| 6 | Meta-banner over-promotion | PUSHED BACK — contradicts locked Q13/P6 Interpretation A |
| 7 | Banner iter ∈ {2,3} hardcoded | PUSHED BACK — locked parent spec § 4.4 with rationale; config layer = Pattern E |
| 8 | Preview data staleness | PUSHED BACK — contradicts locked Q14/C1 |
| 9 | Abort ResolvedBrief info loss | DEFER — already tracked as **B-029** |
| 10 | Hardcoded constants | PUSHED BACK — parent spec locked § 4.2 + § 4.3 values; no business need for runtime tuning |
| 11 | DI / interface layer | DEFER — `unittest.mock.patch` works; no swap need today |
| 12 | Observability hooks | DEFER — broader infra; out of S6 scope |
| 13 | Dynamic prioritization scoring | PUSHED BACK — contradicts locked § 4.2 priority order |
| 14 | Counterfactual cost | DEFER — already tracked as **B-034** |
| 15 | Guided recovery / fallback paths | PUSHED BACK — Layer 2 UX feature, out of S6 scope |

Result: **187/187 c3a tests passing** (165 + 22 S6 — added `test_per_case_iteration_counts_rejects_mutation`).

### What happened — code-critique round 2 (10 drawbacks on the round-1 fix itself)

| # | Drawback | Verdict |
|---|---|---|
| **1** | **Type inconsistency in `determine_termination`** (signature still says `dict[str, int]` but state exposes `Mapping`) | **APPLIED** — signature updated to `Mapping[str, int]` |
| **2 / 10** | **`_freeze_counts` doesn't defensively copy** — relies on caller discipline | **APPLIED** — `MappingProxyType(dict(d))` + new test `test_freeze_counts_does_not_share_storage` |
| 3 | Deep-copy mutable input | PUSHED BACK — values are `int` (immutable); deep copy of `{str: int}` = shallow copy |
| 4 | "Redundant freezing during termination check" | PUSHED BACK — **factually wrong about the code**. `determine_termination` receives raw `new_per_case` dict, not a frozen one |
| 5 | `_EMPTY_COUNTS` shared instance risk | PUSHED BACK — underlying `{}` has zero references after construction; standard sentinel pattern |
| 6 | Runtime `isinstance` validation | PUSHED BACK — Pattern A; inconsistent with rest of codebase (no other field has runtime type validation); catches no actual concern |
| 7 | Audit nested domain immutability | PUSHED BACK — **factually wrong about the codebase**. All 11 nested domain types (`Brief`, `ExtremeCase`, `ResolutionOption`, `DesignGapAnalysis`, `ExtremeDecision`, `PreflightSummary`, `PreviewModeAcknowledgment`, `ResolvedBrief`, `BriefChange`, `CounterfactualSummary`, `ExtremeDecisionLog`) ARE already `@dataclass(frozen=True)` |
| 8 | Wrapping overhead | PUSHED BACK — critique itself labels OPTIONAL |
| 9 | External mutation via domain objects | PUSHED BACK — same as #7; domain layer enforces frozen=True |

Result: **188/188 c3a tests passing** (165 + 23 S6 — added `test_freeze_counts_does_not_share_storage`).

### Pattern D observation flagged at end of round 2

Round 2 critique on the same fix produced one real type fix (#1), one defensible hardening (#2/#10), but also TWO factually incorrect claims (#4 about double-freezing, #7/#9 about domain layer not being frozen) and multiple hedges on hypothetical future bugs (#5, #6). Flagged that round 3 on the same topic would yield negative returns. Ramalingam confirmed: move on.

### Key decisions locked this session

- No new D-### items. D-066 + D-067 + D-068 + D-069 already cover the patterns this session exercised.

### Code changes

- **New files** (under `components/c03a/` + `components/`):
  - `gate_state.py` (178 LOC) — `GateState` frozen dataclass + `GateTerminationReason` enum + `TransitionBannerEvent` + `DifferentPlotPromotionEvent` + `Mapping[str, int]` typing for per-case counts
  - `gate_termination.py` (103 LOC) — `determine_termination()` pure helper with explicit precedence; constants `MAX_ITERATIONS=7`, `PER_CASE_LIMIT=3`; signature accepts `Mapping[str, int]`
  - `c03a_extreme_case_gate.py` (1,053 LOC) — `ExtremeCaseGate` class + private helpers (`_sort_cases_by_priority`, `_promote_different_plot_in_case`, `_check_different_plot_trigger`, `_maybe_transition_banner`, `_generate_real_options`, `_freeze_counts`, three `_build_*_resolved_brief` helpers, four branch helpers `_terminate_*` + `_handle_apply_error`)
- **New test files** (under `tests/`):
  - `test_c03a_session6_orchestrator_happy.py` (499 LOC, 7 tests)
  - `test_c03a_session6_orchestrator_termination.py` (451 LOC, 7 tests)
  - `test_c03a_session6_orchestrator_error_path.py` (286 LOC, 3 tests)
  - `test_c03a_session6_orchestrator_v0_2_patches.py` (456 LOC, 6 tests — includes 2 immutability tests added across critique rounds)
- **Backlog appended:** B-039 (option-generation caching).

### Test count delta

- Start of session 22: 165 c3a tests
- After S6 ship: 186
- After D-066 round 1 fix: 187
- After D-066 round 2 fix: **188** c3a tests (+23 net for session)

### State at end

- C3a S1 through S6 ✅ shipped + B-027 shipped. **6 of 8 sessions done.**
- 188 / 188 c3a tests passing across 12 suites.
- Master doc bumped v2.7 → v2.8.
- Backlog: 36 items (B-001 through B-039, with B-026 superseded into B-023; B-039 newly logged).
- Next conversation: draft S7 spec (API endpoints) per parent C3a spec § 5.1–5.5 + § 4.5 Preview Mode mechanics + § 4.3 CBA fallback.
- D-066 cycle continues: spec → analysis → patch → lock → code → analysis → patch → next.

---

## 4.24 Session 23 — Fri 1 May 2026 — *Component 3a Session 7a: Spec drafted, locked, code build started (~30–40% complete; mid-build handoff)*

**Source:** Live conversation, Session 23 (continuation from S6 ship).
**Theme:** S7 spec drafted v0.1 → critique round 1 (12 drawbacks; 10 patches applied / P1–P10) → v0.2 → critique round 2 (15 drawbacks; 5 patches + 1 split decision applied / P11–P18; 4 items pushed back per D-067) → v0.3 → **v1.0 LOCKED as S7a** (S7 split into S7a endpoints+serialization+storage and S7b deployment hooks). Code build began but only ~30–40% complete by tool-budget end. Mid-build handoff prepared per Obligation 2.

### Status update (per Rule 6, formalized this session)

**Project-wide: 3 of 17 components shipped (~18%)**
- ✅ C1 Brief Capture (v0.9, all 6 city DCRs)
- ✅ C2 Feasibility
- ⏳ C3a Extreme Case Gate (in build — 6 of 8 sub-sessions shipped + S7a partial)
- ✅ C7 Structural Grid (v0.7.2)
- 📋 13 components pending (C3b, C4, C5, C6, C8–C17)

**This session completed:**
- S7a SPEC v1.0 LOCKED (1,618 lines, 2 critique rounds, P1–P18, 4 D-067 pushbacks)
- S7a code ~30-40%: storage layer + Brief tree + 4/10 extreme_case types
- Master doc bumped v2.8 → v2.9, backlog +3 items
- 6 rules formalized (Rules 1–6 in `RULES_RAMALINGAM_FORMALIZED.md`)

**Pending:**
- Immediate: finish S7a code (6 extreme_case types + feasibility tree + endpoints + tests → 216 c3a tests target)
- After S7a: code-critique cycle → S7b spec + code → S8 spec + code → C3a SHIPPED → 4 of 17 (~24%)
- Long-range: 13 components after C3a ships (layout pipeline first per D-050)

### Context entering the session

- 188/188 c3a tests passing across 12 suites (S1–S6 + B-027).
- Master doc v2.8.
- Backlog: 39 items (B-001 through B-039).
- Original handoff for Session 23 instructed: draft S7 spec from parent § 5.1–5.5.

### What happened — spec drafting

- **v0.1 DRAFT (787 LOC)** drafted from scratch covering 5 endpoints, JSON serialization, SQLite storage mirroring BriefStorage, hook stubs, error policy.
- **Round 1 critique surfaced 12 drawbacks**, of which **10 became patches P1–P10**:
  - P1 structural-equivalence invariant (was strict equality)
  - P2 request_id-based idempotency (was missing)
  - P3 terminal tokens HTTP 200 (was 410)
  - P4 no-delete on terminal (TTL only)
  - P5 SQLite WAL + retry
  - P6 S6 owns FULL serialization tree (was S7-side) — biggest scope expansion
  - P7 is_done normalization at wire (separate aborted/paused flags)
  - P8 schema versioning softened (absent = v1; only explicit different value rejected)
  - P9 1 MB request size cap
  - P10 hook ordering: save-then-hook, non-fatal
  - 2 items deferred (B-040 schema migration, B-042 project-wide auth)
- **v0.2 DRAFT (1,205 LOC)** with full P1–P10 changelog.
- **Round 2 critique surfaced 15 drawbacks**, of which **5 became patches** + **1 scope decision** (P11–P18):
  - P11 per-token single-flight lock (round 2 #15 — the real concurrency bug)
  - P12 brief→session uniqueness index (round 2 #2)
  - P13 atomic state+cache co-write via BEGIN IMMEDIATE (round 2 #4)
  - P14 deterministic JSON ordering with sort_keys (round 2 #5)
  - P15 terminal-replay advisory `session_status` field (round 2 #7)
  - P16 hooks NOT re-invoked on idempotency replay (round 2 #12)
  - P17 **S7 split into S7a / S7b** (round 2 #6 LOC growth concern — answers it by splitting rather than reducing)
  - P18 1MB cap is defense-in-depth clarification (round 2 #11)
- **4 round-2 items pushed back** per D-067 with documented rationale in CHANGELOG:
  - #1/#9 request_id history would not change real-world retry behaviour given P11
  - #3 multi-process WAL concern factually wrong — deployment is single-process stdlib http.server
  - #8/#13 token rotation is project-wide auth scope (already B-042; round 2 #13 is a verbatim repeat of round 1 #10)
  - #14 describes correct idempotent-retry behaviour as a bug
- **1 round-2 item deferred** to backlog: #10 prune timing → expanded B-041 scope (BriefStorage WAL retrofit + prune-on-resume sweep).
- **v0.3 DRAFT (1,492 LOC)** with full P11–P18 changelog + transparent pushback rationale.
- **Pattern D observation flagged at end of round 2**: round 2 escalated 4 items to MUST FIX that don't survive scrutiny (factually wrong about deployment, repeats of round-1 deferrals, hostile-mechanism suggestions). Recommended LOCK after applying real fixes.
- **Ramalingam decision: LOCK at v1.0**.
- **`buildemup_S7a_SPEC_v1_0_LOCKED.txt` produced.** Spec is final; ready for code build.

### What happened — code build (PARTIAL)

Per D-066 step 6, code build began. Honest progress:

**Completed and verified:**
- `utils/gate_state_storage.py` — full SQLite storage layer with all v1.0 hardenings (P5 WAL+retry, P11 single-flight lock dict, P12 brief_to_session uniqueness index, P13 atomic state+cache co-write via BEGIN IMMEDIATE, P4 no-delete TTL-only)
- `domain/_serialization.py` — generic helpers (enc/dec/dec_optional/dec_tuple/dec_enum)
- `components/c03a/gate_state.py`:
  - `GateState.to_dict / from_dict` skeleton (depends on still-pending nested types)
  - `TransitionBannerEvent.to_dict / from_dict` ✅
  - `DifferentPlotPromotionEvent.to_dict / from_dict` ✅
  - `SchemaVersionError` exception added
- Brief-side full serialization tree:
  - `domain/setbacks.py` — Setbacks ✅
  - `domain/plot.py` — Plot ✅
  - `domain/floor_requirement.py` — RoomRequirement + FloorRequirement ✅
  - `domain/brief.py` — BudgetRange + GuidanceMessage + Brief ✅
  - **Smoke-tested:** Brief round-trips losslessly through to_dict/from_dict
- Partial `domain/extreme_case.py` serialization — 4 of 10 types done:
  - BriefChange ✅
  - CostImpact ✅
  - ResolutionOption ✅
  - ExtremeCase ✅
- 188/188 c3a baseline still passing (purely additive — nothing broken)

**Pending — the build queue for the next session:**
- Finish `extreme_case.py`: 6 more types (ExtremeDecision, CounterfactualSummary, PreflightSummary, PreviewModeAcknowledgment, ExtremeDecisionLog, ResolvedBrief)
- All of `domain/feasibility.py` serialization (DesignGapAnalysis + ~5 nested types + 6 enums) — biggest remaining chunk
- `components/c02/feasibility_input.py` serialization (InputField generic + FeasibilityInput)
- End-to-end GateState round-trip smoke test (cannot run until tree complete)
- `api/c3a_endpoint.py` — 5 handlers, ~520 LOC
- `api/c3a_email_hook.py` + `api/c3a_scheduler_hook.py` — stubs, ~30 LOC each
- `api/server.py` route additions
- 4 test files: ~28 tests total (~1,420 LOC)
- Final acceptance: 188 baseline + ~28 new = ~216 tests passing

### Why mid-build stop (Obligation 2)

Tool-budget for the conversation reached a point where pushing further risked broken or incomplete code with optimistic claims. Per Obligation 2 — honest context reporting — flagged the situation to Ramalingam, who confirmed handoff. Three deliverables produced:
- `NEXT_CLAUDE_HANDOFF.md` — mid-build resume orientation, full build queue
- `buildemup_S7a_SPEC_v1_0_LOCKED.txt` — the locked spec (final)
- `buildemup_workdir.tar.gz` — partially-built code (585 KB), unpacks to a known-clean state with 188/188 baseline still green

### Pattern observations this session

- **D-067 pushback was used twice productively**: round 1 deferred 2 items to backlog (B-040/B-042); round 2 pushed back 4 items with documented rationale. Both rounds yielded real progress; round 2 also surfaced false-positive escalations consistent with the S6 round 2 dynamic.
- **Pattern D risk acknowledged before round 3 was attempted** — Ramalingam locked v0.3 → v1.0 rather than chase a third critique round on the same surface.
- **No new D-### decisions logged this session.** D-066 + D-067 + D-068 + D-069 already cover the patterns this session exercised.

### Code changes (cumulative this session)

- **New files** (under `utils/` and `domain/`):
  - `utils/gate_state_storage.py` (~230 LOC, complete)
  - `domain/_serialization.py` (~50 LOC, complete)
- **Modified files** (additive only — to_dict/from_dict methods appended):
  - `components/c03a/gate_state.py` (+~150 LOC)
  - `domain/setbacks.py` (+~15 LOC)
  - `domain/plot.py` (+~40 LOC)
  - `domain/floor_requirement.py` (+~30 LOC)
  - `domain/brief.py` (+~70 LOC)
  - `domain/extreme_case.py` (+~120 LOC of 10 expected; ~600 still pending)

### Test count delta

- Start of session 23: 188 c3a tests
- End of session 23: **still 188 c3a tests** (no new tests written; existing tests still all pass)
- Target after S7a complete: ~216 c3a tests (188 + ~28 new across 4 test files)

### State at end

- C3a S1 through S6 ✅ shipped + B-027 shipped. **6 of 8 sessions done.**
- C3a S7a SPEC v1.0 LOCKED.
- C3a S7a code: ~30–40% complete (storage + Brief tree + 4/10 extreme_case types). 188/188 baseline still passing.
- Master doc bumped v2.8 → v2.9.
- Backlog: 39 items (B-040, B-041 expanded scope, B-042 from S7a spec rounds).
- Next conversation: resume S7a code build from queue in handoff. Then S7a code-critique. Then S7b spec (deployment hooks). Then S8 (validation suite).
- D-066 cycle continues: spec locked → code build (in progress) → code critique → patch → next.

---



# PART 5 — Architecture v3 (CANONICAL)

This is the locked architecture. Source: `BuildemUp_Architecture_v3.md` (delta from v2). Every coding session honours this structure. Do not deviate without explicit user approval.

## 5.1 The three layers + cross-cutting concerns

```
LAYER 1 — UNDERSTANDING        (Components 1–4)
  Goal: solve the right problem.
  Output: validated structured brief + feasibility envelopes.

LAYER 2 — GENERATION           (Components 5–13)
  Goal: produce many valid layouts.
  Output: 60+ candidate layouts across 3 topologies.

LAYER 3 — EVALUATION + OUTPUT  (Components 14–17)
  Goal: pick the best 3, deliver them beautifully, defend the user.
  Output: 3 ranked layouts + working drawing + regulatory drawing
          + contractor pack + Quote Comparison capability.

CROSS-CUTTING CONCERNS:
  • Contractor Defence Layer  (auto-generated documents)
  • Resilience Layer          (graceful failure everywhere)
  • Constraint Propagation    (NEW in v3 — shared rules + repair-on-violation)

SYSTEM CAPABILITY:
  • Fast Mode / Deep Mode selector
```

## 5.2 The 17-component table (with build status)

| # | Component | Layer | Build status (29 Apr 2026) |
|---|---|---|---|
| 1 | Conversational Brief | Understanding | ✅ SHIPPED v0.9.3 (form-based; LLM brief deferred to v2) |
| 2 | Feasibility (×2 envelopes) | Understanding | ✅ SHIPPED v0.1 |
| 3 | **Trade-off Negotiation** | Understanding | ⏳ **NEXT** |
| 4 | Plot Analysis | Understanding | Pending |
| 5 | Topology Selector | Generation | Pending |
| 6 | Orientation Priority (climate-aware) | Generation | Pending |
| 7 | Structural Grid Engine | Generation | ✅ SHIPPED v0.7.3 |
| 8 | Corridor Design | Generation | Pending |
| 9 | Room Sizer (with furniture envelope) | Generation | Pending |
| 10 | Bathroom + Wet-Zone Stack Planner | Generation | Pending |
| 11a | Topology Mutation Layer (9 ops) | Generation | Pending |
| 11b | Local NSGA-II Refinement | Generation | Pending |
| 12 | Vertical Alignment Engine | Generation | Pending |
| 13 | Door Placement | Generation | Pending |
| 14 | Unified Evaluation Engine (Hard/Soft split) | Evaluation | Pending |
| 15 | Ranker | Evaluation | Pending |
| 16 | Dual-Drawing Renderer | Output | Pending |
| 17 | Quote Comparison Engine | Output | Pending |

**Three of seventeen built. Fourteen to go.** This is the most important sentence in this document.

## 5.3 The core generation loop

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
            │ Topology Mutation (9 ops)    │
            │   → 6–8 valid global seeds   │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ Local NSGA-II Refinement     │
            │   30 generations, pop 50     │
            │   → Pareto-optimal survivors │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ Unified Evaluation Engine    │
            │   STAGE 1: Hard constraints  │
            │           (binary pass/fail) │
            │   STAGE 2: Soft objectives   │
            │           (NSGA-II ranking)  │
            └──────────────┬───────────────┘
                           ▼
                  Top 3 per topology
       (9 candidates across 3 topologies)
                           ▼
                  Ranker picks final 3
                   (maximally different)
                           ▼
             Dual-drawing renderer + Contractor pack
                           │
                           ▼
        User receives contractor quote → uploads
                           ▼
            Quote Comparison Engine (Component 17)
                           ▼
        User sends informed counter-offer
```

## 5.4 The locked architectural invariants (cannot be relaxed)

These survived from Era 1, were retested in v3, and locked:

**Invariant 1 — Topology before placement.** Placement engine never runs without an explicit topology selection from Component 5. No "place rooms freely and see what topology emerges."

**Invariant 2 — Hard before Soft.** Component 14 runs Hard Constraints (binary pass/fail) before Soft Objectives (NSGA-II ranking). A layout that fails any Hard Constraint is discarded, not penalised. The CRITICAL v3 fix.

**Invariant 3 — Structural grid before rooms.** Component 7 runs before Component 8 (Corridor) and 9 (Room Sizer). Rooms align to grid; grid never accommodates rooms after the fact.

**Invariant 4 — Furniture envelope, not NBC, is the lower bound.** NBC says bedroom can be 80 sqft. Component 9 says if you want a queen bed + wardrobe to fit with Neufert clearances, it's 100 sqft. Furniture-fit is the lower bound. NBC is the floor below that.

**Invariant 5 — PENDING ENGINEER VALIDATION on every output.** BuildemUp itself can NEVER transition out of "PENDING ENGINEER VALIDATION" status. Only an engineer's stamp can. There is no `level_3_indicator()` function in the codebase (and there will never be one). Engineering depth `LEVEL_3_ENGINEER_DESIGNED` is unimplementable by the system itself, by design.

**Invariant 6 — Bedrooms > Kitchen > Living priority for cuts.** When the brief and feasibility conflict and rooms have to be reduced, this is the locked priority order.

**Invariant 7 — Vastu is INFO-only.** Vastu never blocks. Three opt-in tiers (OFF / PARTIAL-7-items / FULL). Default OFF. All Vastu output prepends "VASTU ADVISORY (separate from structural design)..."

**Invariant 8 — Most realistic briefs land at Code-Strict 40.** This is correct, not a bug. NBC-strict checks (water_table, soil_type) HARD-fail on unverified data, capping the score at 40. The 40 cap is the engine being honest with the user. Best case (verified data + S-facing + G+0) = 90/90.

**Invariant 9 — The user owns the decision.** The engine surfaces conflicts in plain English and lets the user pick. It never silently overrides. Component 3 (Trade-off Negotiation) is the embodiment of this invariant.

**Invariant 10 — Confidence ≠ correctness.** WELL_CONSTRAINED / REGIONAL_TYPICAL / DEPENDS_ON_CHOICE describe input certainty + model stability. They do NOT describe engineering correctness. Even WELL_CONSTRAINED outputs need engineer validation at detailed design.

## 5.5 The 17 components — compressed spec

For full v3 spec see source documents. Compressed below.

### Component 1 — Conversational Brief ✅ SHIPPED v0.9.3

**Purpose:** Capture brief as validated, machine-readable `Brief`.

**Inputs:** Plot details (width, depth, facing, city, road width, plot type, corner status), per-floor room composition, user-stated setbacks, budget range, optional preferences.

**Outputs:** `Brief` immutable dataclass + soft_guidance + top_guidance + compliance_summary + assumptions_used + c7_preview_cost + trace_id + kb_versions + ready_for_downstream + resume_token.

**Special features:** Form-based (4-step Tailwind UI), 6 cities full DCRs, vastu 3-tier opt-in, auto-staircase ≥ 2 floors, parking feasibility, phased construction suggestion, top-3 prioritised guidance, ASSUMPTIONS USED section, localStorage save/resume.

### Component 2 — Feasibility (×2 envelopes) ✅ SHIPPED v0.1

**Purpose:** Compute buildable envelope under TWO setback rule sets — the **Practical** (user's stated 2 ft setbacks) and the **Code-Strict** (NBC + city DCR). Surface gaps with cost delta.

**Inputs:** Brief + optional FeasibilityInput (with FieldSource per soil/water-table/electric-line/water-course).

**Outputs:** `DesignGapAnalysis` containing two FeasibilityReports + all gaps + cost delta to upgrade Practical → Code-Strict + prioritised action steps.

**The 17 of 18 v0.1 checks:**
- 4 hard physics (unbranched): envelope, floor stack, parking width, budget
- 6 legal-only (unbranched): FAR, ground coverage, fire access, electric line, water course, stilt mandate
- 6 branched (Practical + Code-Strict + Gap): setbacks, solar, ventilation, soil, water table, RWH
- 1 info-only: approval complexity tier

**The 18th (room minimums) deferred to v0.2** because needs C1 RoomRequirement flag.

### Component 3 — Trade-off Negotiation ⏳ NEXT TO BUILD

**Purpose:** When feasibility surfaces conflicts, do not refuse the brief. Explain plain-English. Present 2–4 architectural alternatives per conflict. Let user pick. Re-run feasibility on the revised brief.

**Inputs:** Brief + DesignGapAnalysis (from Component 2).

**Outputs:** Resolved Brief (revised based on user choices) + log of choices made + cost/space impact of each choice.

**Internal logic:**
- Surface highest-priority conflict first (one at a time, not all at once)
- For each conflict, generate 2–4 specific resolution options grounded in the actual plot
- Each option has: description, cost impact, space impact, recommendation flag
- Protected-priority order when suggesting cuts: Bedrooms > Kitchen > Living > everything else (Invariant 6)
- After user choice, append to brief, re-run feasibility, ask next conflict if any

**v1 scope:** decision-tree-based (LLM-prompted in v2). Decision tree itself is small; most of the work is the prompt that translates feasibility-report into options.

### Component 4 — Plot Analysis (Pending)

**Purpose:** Classify plot, detect special features, set quality tier.

**Outputs:** `PlotAnalysis` with: tier (T1 600–2400 / T2 2400–4000 / T3 4000+), shape (rectangular/L/irregular), corner status, sun path (latitude-correct), climate zone (NBC 5 zones), prevailing wind, soil estimate, road width, neighbour context.

**Implementation note:** Most data is already in `CITY_DATA` from Era 1. This is wiring + the sun-path calculation.

### Component 5 — Topology Selector (Pending — CRITICAL)

**Purpose:** Pick 2–3 of the 5 topologies most likely to succeed on this plot+brief. Each carried through the rest of the pipeline in parallel.

**The 5 topologies for v1:**
- **No-corridor** — single-room or compact 1BHK (plot < 18 ft wide)
- **Strip** — wide plot, public→service→circulation→private bands N-to-S
- **Central spine** — narrow plot, double-loaded corridor (20–32 ft wide)
- **L-shape** — corner plot, two-street access
- **Courtyard** — large plot or warm-humid climate (40 ft+ wide, 50 ft+ deep)

**Three deferred to v2:** U-shape (synthesise from L), Atrium (synthesise from Courtyard), Split-level (sloped plots — 5% market).

**Plot-width-to-topology mapping (locked):**
```
< 18 ft        No-corridor only
18–22 ft       No-corridor, Central spine
22–28 ft       Strip, Central spine
28–35 ft       Strip, Central spine, L (if corner)
35–45 ft       Strip, L, Courtyard (if depth allows)
45 ft+         Strip, L, Courtyard
```

### Component 6 — Orientation Priority Engine (Pending)

**Purpose:** Given plot orientation + climate zone, produce preference table for where each room type should ideally go.

**Climate-zone-aware:** Rules differ by NBC zone. Warm-humid (Chennai) favours NE for living/kitchen, SW for utility/store. Hot-dry (Jaipur) differs. Composite (Delhi) differs again.

**Output:** Preference scores (0–5) per (face × room type), feeding into placement and scoring.

### Component 7 — Structural Grid Engine ✅ SHIPPED v0.7.3

**Purpose:** Decide where columns go BEFORE any room is placed. Rooms then size as multiples of the grid.

**Methods used:**
- Devdas Menon parametric grid (3.0–3.7m typical for residential)
- IS 456 column sizing
- IS 875 Part 3 wind load
- IS 1893 simplified seismic (with three-level regularity check)
- IS 13920 ductile detailing (Zone III + IV)
- IS 2911 pile sizing (when soil requires)
- Hardy Cross moment distribution + Bresler interaction (LEVEL_2 frame sanity)
- IS 1904 soil bearing capacity (12 soil classes)
- Real Chennai 2026 + 5 cities material rates with brand/grade/IS-code

**Validation status:** PENDING ENGINEER VALIDATION (cannot transition out — Invariant 5).

**Engineering depth:** LEVEL_2_FRAME_CHECKED. LEVEL_3 is engineer-only by design.

### Component 8 — Corridor Design Engine (Pending)

**Purpose:** Decide three things about every floor's circulation: does a corridor exist, where, how wide.

**Critical insight:** Corridor decided BEFORE rooms because corridor decides where staircase goes, and staircase decides where rooms can go. Era 1 engine did the opposite (rooms first, corridor leftover) — that's why Era 1 had the 15 known problems.

**Hierarchy (Ching FSO):**
- Primary: min 1.2 m, open/visible/welcoming, entry → living → dining
- Secondary: min 0.9 m, private, bedroom → bathroom
- Service: min 0.75 m, back-of-house, kitchen → utility

### Component 9 — Room Sizer (with furniture envelope) (Pending)

**Purpose:** Each room has min/ideal/max from KB. Sizer assigns actual size based on (a) priority and (b) available area, while respecting min and max.

**Furniture envelope (the new bit, Invariant 4):** Furniture-fit is the lower bound, not NBC. Bedroom = 100 sqft, not the NBC 80 sqft minimum, because that's what the queen bed + wardrobe + clearance actually need.

**Priority order (locked):** Bedrooms (with furniture min) → Kitchen → Living → Bath → Corridor → Utility → Store.

**Algorithm:** Greedy allocation — assign min to all → distribute surplus to highest-priority rooms first, capped at max. O(n log n).

### Component 10 — Bathroom + Wet-Zone Stack Planner (Pending)

**Purpose:** Group all wet areas (bathrooms, kitchen, utility) along vertical stacks to minimise plumbing runs and enable clean multi-floor alignment.

**Three rules:**
1. Private bathroom (master_bath): inside master suite zone, accessed from master only, has external wall.
2. Common bathroom: opens to corridor directly, never inside any bedroom zone.
3. Attached bedroom bathrooms: on the FAR side of bedroom from corridor (path = corridor → bedroom → bathroom, never corridor → bathroom → bedroom). **Solves Era 1 Problem 3.**

**Plumbing stack alignment** is the cost saver — when FF bathroom sits roughly above GF bathroom or kitchen, plumbing cost reduces 20–35%.

### Component 11a — Topology Mutation Layer (Pending — NEW in v3)

**Purpose:** Before local NSGA-II refinement, explore globally-different structural variants.

**The 9 mutation operators:**
1. Horizontal flip (E↔W)
2. Vertical flip (N↔S)
3. Staircase relocation (4 positions: center / east / west / corner)
4. Corridor inversion (central ↔ edge)
5. Public/private zone swap
6. Wet-wall rotation (90°)
7. Grid scaling (3.0m / 3.3m / 3.6m)
8. Vertical rearrangement (which rooms on GF vs FF)
9. **Entry door relocation** — NEW in v3 — for NE-facing plot, try entry at NE-center, NE-corner-E, NE-corner-W, offset-NE

Filter invalid mutations before NSGA-II.

### Component 11b — Local NSGA-II Refinement (Pending)

**Purpose:** Fine-tune each mutated seed through 30 generations of NSGA-II genetic algorithm.

**Population:** 50 per seed.
**Generations:** 30 (Deep mode) / 5 (Fast mode).

**The 6 Indian-family objectives + 4 standard:**
1. Cost (₹, minimise)
2. Pooja placement quality (0–10, maximise)
3. Multi-generational score (0–10, maximise)
4. Bathroom-to-bedroom practicality (0–10, maximise)
5. Wet-zone efficiency (₹, minimise)
6. Tamil climate comfort (0–10, maximise)
7. Light (0–10)
8. Privacy (0–10)
9. Circulation hierarchy (0–10)
10. Experience (0–10)

**Diversity preservation:** layout DNA distance penalty + niching to ensure 20 final survivors are genuinely different.

**Output:** ~70 Pareto-optimal candidates across 3 topologies.

### Component 12 — Vertical Alignment Engine (Pending)

**Purpose:** Ensure multi-floor integrity — what's on GF supports what's on FF, what stacks must stack cleanly.

**Checks:** Column alignment, bathroom alignment, staircase alignment, plumbing stacks, load path violations (FF walls land on GF columns/beams, not mid-slab), cantilever limits (≤ 1.5m).

### Component 13 — Door Placement (Pending)

**Purpose:** For every room: which wall, where on the wall, swing direction.

**Algorithm (space syntax — Hillier/Hanson):**
- Candidates: walls adjoining a corridor or required adjacent room
- Filter: ≥ 0.9 m wide, doesn't block window, swing doesn't conflict
- Pick: candidate minimising step-depth from entry

### Component 14 — Unified Evaluation Engine (Hard/Soft split) (Pending — CRITICAL in v3)

**STAGE 1 — Hard Constraints (binary pass/fail) — 9 checks:**
1. Structural alignment
2. NBC compliance
3. Furniture fit minimum (Neufert)
4. Plumbing feasibility
5. Vertical alignment
6. Load path continuity
7. Fire egress (distance to exit)
8. Ventilation minimum (every habitable room has window or mech vent)
9. External wall rule (bedrooms must touch external wall)

Failed candidates DO NOT enter NSGA-II population.

**STAGE 2 — Soft Objectives (NSGA-II ranked):** Cost, pooja, multigen, bath practicality, wet-zone, climate, light, privacy, circulation hierarchy, experience, construction feasibility (sub-checks: beam continuity, slab casting, waterproofing continuity, cantilever limits — NEW in v3).

**Output: Problem Report, NOT a single score.** Categorised across 9 categories: WASTED SPACE / ROOM SIZES / FLOW / LIGHT / PRIVACY / FURNITURE FIT / EXPERIENCE / COST / CODE COMPLIANCE.

### Component 15 — Ranker (Pending)

**Purpose:** Pick 3 final layouts to show user — maximally different, not just top 3 scorers.

**The three axes (locked in v3.1):**

| Internal | User-facing | Optimises |
|---|---|---|
| LAYOUT_A | **Cost Efficient** | Lowest viable build cost |
| LAYOUT_B | **Everyday Living** | Daily family experience, privacy, multigen, storage |
| LAYOUT_C | **Premium Design** | Architectural quality, light, experience |

**Algorithm:** Project ~70 Pareto candidates to user axes (Budget, Family-experience, Aesthetic-experience). Find extremes. Pick 3 maximally different.

### Component 16 — Dual-Drawing Renderer (Pending)

**Purpose:** Final deliverable. Same house rendered twice — for contractor and for approval authority.

**Outputs:**
- Working Drawing PDF (15–25 pages, full dimensioned detail)
- Regulatory Drawing PDF (5–8 pages, simplified for CMDA/DTCP submission)
- Furniture Layout PDF (overlay showing real furniture fit)
- BOQ.xlsx (line-itemised, brand/grade/IS-code per item)
- Cost Breakdown PDF (with contractor margin line VISIBLE)
- Working-vs-Regulatory comparison PDF
- Contractor Pack (4 documents — see Cross-cutting concern §5.6)
- Interactive shareable link (web-viewable, clickable rooms with dimensions)

### Component 17 — Quote Comparison Engine (Pending — NEW in v3, the moat)

**Purpose:** User uploads contractor quote (PDF/image/Excel). Engine extracts items, compares against our BOQ, flags discrepancies. Saves users ₹5–10 lakh per project.

**Steps:**
1. OCR + Claude API parse quote → structured line items (material, qty, unit, rate, total)
2. Match each item to our BOQ (fuzzy: "TMT 8mm" matches "Steel TMT 8mm Fe500")
3. Per matched pair: price delta. >+20% = OVERPRICING (red), +5..+20% = HIGH (amber), -20..+5% = FAIR (green), <-20% = UNDERPRICED (often low-quality).
4. Detect missing items (waterproofing FF baths, electrical extras, plumbing risers)
5. Detect unexplained lump sums ("Sundries: ₹2L" suspicious if >2% of total)
6. Generate counter-offer with negotiation language
7. Contractor credibility score (0–100)

**Tone (per Design Principle 3):** Advisory, not auditor. "This rate is above current Chennai market" not "Contractor is overcharging."

**Sample output (from canonical walkthrough):**
- Quote: ₹71.5L
- Our estimate: ₹58.5L
- Counter-offer: ₹62.5L (our estimate + 7% margin)
- **Potential savings: ₹9 lakh**

This is the **strongest individual differentiator**. Highest viral potential. The feature most directly tied to the founding story.

## 5.6 Cross-cutting concerns

**Contractor Defence Layer** — auto-generated 4-document pack:
1. Decision rationale PDF (per design choice, with code citation)
2. Indian code citations PDF (every material spec, clearance, setback)
3. Contractor questions PDF (20 most common disputes pre-empted)
4. Construction sequence PDF (suggested build order)

**Resilience Layer** — every component answers "what happens when I can't produce a valid output?" No black-box errors ever reach the user.

**Constraint Propagation (NEW in v3)** — `ConstraintEngine` class with `propagate_*()`, `repair_violation()`, `validate()`, `explain()` methods. Used as a library by C7, C8, C9, C10, C11a, C11b, C12, C14. Mechanically prevents Pattern D (rules-on-rules).

## 5.7 System capability — Fast Mode / Deep Mode

**Fast Mode (< 3 seconds):**
- Skip Topology Mutation (11a)
- 5 generations × pop 20 NSGA-II (instead of 30 × 50)
- Hard Constraint Checker only (no soft scoring)
- Output: 3 decent layouts

**Deep Mode (60–90 seconds):**
- Full pipeline as specified
- 3 topologies × 6–8 mutations × 30 generations
- Full Hard + Soft evaluation
- Output: 3 Pareto-optimal, maximally-different layouts

**UX flow:** Fast Mode runs in background → 3 quick concepts in 3–5 sec → "Want us to deeply optimise? Takes 60 sec, usually 20–30% better." → User clicks → Deep Mode runs → Final 3 polished layouts.

---

# PART 6 — Design Principles v3.1 (LOCKED)

The seven non-negotiable principles. Source: `BuildemUp_Design_Principles_v3_1.md`. **Read at the start of every coding session.**

## 6.1 Principle 1 — Experience-driven explanations

Every `explain()` method talks to the **user, not the engine.**

| Engine-centric (BAD) | Experience-driven (GOOD) |
|---|---|
| "Privacy score: 7/10" | "When you open your front door, bedroom 1's door is visible from 15 feet away. A small screen near the entry would solve this for ~₹12,000." |
| "Pareto-optimal on cost dimension" | "This is the most cost-efficient layout in our exploration — ₹3-4L cheaper than the alternatives." |
| "Insufficient sqft for badminton court placement" | "A full badminton game would take up almost your entire terrace. You wouldn't have space left for a gym, garden, or seating." |

**Test:** Read it out loud. If it sounds like an engineer talking to another engineer, rewrite.

## 6.2 Principle 2 — The Transparency Triple

**Every numeric output gets three things:**
1. **A range** reflecting honest uncertainty
2. **An exact midpoint** for users who want a single number
3. **The derivation** showing how we got there

```
ESTIMATED COST: ₹56L – ₹61L (mid-tier finish, Chennai 2026)
                Most likely: ₹58.5L
                Confidence: Medium (±9%)

Click to see breakdown:
  Structure (RCC frame):    ₹14.6L  ← from grid + IS 456 rates
  Masonry + plaster:        ₹9.2L   ← from wall area × 9" brick rate
  Plumbing:                 ₹4.8L   ← reduced 35% via stack alignment
  ... (full breakdown)
  ──────────────────────────
  Build cost subtotal:     ₹53.1L
  Reasonable margin (12%):  ₹6.4L  ← contractor margin (visible)
  ──────────────────────────
  Estimate (mid):          ₹58.5L

Variability drivers (why the range exists):
  • Tile choice swing: ±₹1.5L
  • Bathroom fittings tier: ±₹1L
  • Woodwork scope: ±₹1.5L
  • Contractor margin variation: ±₹2L
```

Same pattern for room sizes, timelines, materials, plumbing runs.

## 6.3 Principle 3 — Advisory tone (not auditor tone)

| Auditor (BAD) | Advisory (GOOD) |
|---|---|
| "DO NOT PAY LUMP SUM" | "It's safer to request a detailed breakdown for this item before proceeding." |
| "Overpayment: ₹1.15L" | "This appears higher than the typical market range (~₹1.85L expected for Jaquar Continental). Worth asking for the exact model list." |
| "Contractor is overcharging" | "This rate is above current Chennai market. You could mention this when discussing." |
| "MISSING FROM QUOTE" | "These items are typically needed but aren't listed. Worth confirming if they're included or will be charged later." |

**Why:** Indian construction relationships run on mutual respect. User has to work with this contractor for 4–6 months. Confrontational language can break the relationship before signing. We keep specific numbers and market comparisons; we wrap them in respectful language.

## 6.4 Principle 4 — User intervention checkpoints

Three explicit checkpoints where user can review/modify/override:
- **Checkpoint 1:** After Topology Selection (Component 5) — approve/modify the 3 topologies
- **Checkpoint 2:** After Room Sizing (Component 9) — adjust any room ±5–10 sqft
- **Checkpoint 3:** After Initial Layout Preview (after Component 11b) — Fast or Deep optimise?

State must be saved at each checkpoint so user can come back later.

## 6.5 Principle 5 — Confidence indicators

Every output category gets a confidence level. In v0.5+ the descriptive names are: WELL_CONSTRAINED / REGIONAL_TYPICAL / DEPENDS_ON_CHOICE.

```
LAYOUT B — Best for Family
  Cost estimate:        ₹56L – ₹61L  [Confidence: MEDIUM]
  Build timeline:       4–5.5 months  [Confidence: MEDIUM]
  Plumbing cost:        ₹2.85L        [Confidence: HIGH — stacks aligned]
  Structural design:    ✓ valid       [Confidence: HIGH — IS 456 verified]
  Furniture fit:        ✓ all rooms   [Confidence: HIGH — Neufert checked]
  Soil/foundation:      Standard       [Confidence: MEDIUM — assumed Chennai clay]
  Contractor margin:    12% assumed    [Confidence: LOW — varies 8–22%]
  Climate comfort:      9/10           [Confidence: MEDIUM — modelled, not measured]
```

**Critical (Invariant 10):** Confidence is about INPUT certainty + model stability, NOT engineering correctness.

## 6.6 Principle 6 — Emotional reassurance

Each layout shown includes a reassurance line.

```
LAYOUT B — Best for Family
  ₹56L – ₹61L

  💡 This layout is commonly chosen by families of 5-7 members
     on plots of similar size in Chennai. The ground-floor
     bedroom + bath is especially valued by families who
     expect parents to visit or move in.
```

Reassurance database keyed on (layout type, plot size tier, family size estimate).

## 6.7 Principle 7 — Failure modes are explicit

Every component answers: "what happens when I can't produce a valid output?"

```python
class Component:
    def execute(self, input) -> ComponentResult:
        try:
            return self._run(input)
        except CannotProduceValidOutput as e:
            return self._graceful_failure(input, e)
```

| Failure | Bad | Good |
|---|---|---|
| Plot too small | "ERROR: insufficient area" | "Your 5 bedroom + walk-in + lounge brief needs ~1100 sqft per floor. Your plot allows ~750 sqft per floor. We can fit 4 bedrooms + small lounge, or 5 bedrooms + no lounge. Which would you prefer?" |
| All topologies fail | "No layout possible" | "Your brief has constraints we can't satisfy together. The conflict: master + 4 bedrooms + walk-in on FF, but FF only fits 3 bedrooms cleanly. Options: drop one bedroom, drop walk-in, or add a second floor." |

## 6.8 The Ramalingam ↔ Claude contract

**Ramalingam commits to:**
1. Catch when responses drift back to engine-centric thinking
2. Trust UX instincts even when can't articulate why
3. Push back on scope creep ("does v1 really need this?")

**Claude commits to:**
1. Read existing KB before writing new code
2. Apply all 7 principles to every component
3. Document failure modes before happy paths
4. Boring correct code over clever optimisations
5. **No black-box errors ever reach the user**
6. **NEVER code before user confirmation on scope changes**
7. **Read the relevant `SKILL.md` before any file creation when working in environments that have skills**

---

# PART 7 — Complete File Inventory (current codebase)

This is the canonical file map of the codebase as preserved in `04_current_codebase/buildemup/` of the archive. **Updated whenever new files are added.**

## 7.1 Top-level

```
buildemup/
├── __init__.py
├── README.md
└── DEPLOY.md
```

## 7.2 Components — `components/`

Each component has an orchestrator at the top level + sub-modules in a `c{NN}/` folder.

```
components/
├── __init__.py
│
├── c01_brief_capture.py            ← Component 1 orchestrator: BriefCaptureEngine
├── c01/
│   ├── __init__.py
│   ├── setback_calculator.py       ← TNCDBR + 5-city DCRs (no NBC fallback for 6 cities)
│   ├── room_composer.py            ← Circulation factor 1.30, auto-staircase
│   ├── parking_feasibility.py      ← Plot < 8m + stilt → STRONG_CONCERN
│   ├── budget_bridge.py            ← Calls Component 7 cost engine
│   ├── phased_construction.py      ← Suggests phased build if budget < estimate
│   ├── soft_guide_engine.py        ← Top 3 prioritisation
│   ├── vastu_filter.py             ← Partial (7 items) / Full filtering
│   └── assumptions_log.py          ← Tracks ASSUMPTIONS USED for explain()
│
├── c02/
│   ├── __init__.py
│   ├── orchestrator.py             ← Component 2 entry: run_feasibility()
│   ├── scoring.py                  ← 100 → -5/-7/-10 SOFT_WARN; 40 cap on HARD_FAIL
│   ├── feasibility_input.py        ← FieldSource + 3-state input pattern
│   ├── hard_physics_checks.py      ← envelope, floor stack, parking, budget
│   ├── legal_only_checks.py        ← FAR, ground coverage, fire, electric line, water course, stilt
│   ├── branched_checks.py          ← Setbacks, solar, ventilation (Practical + Code-Strict)
│   ├── site_input_checks.py        ← Soil, water table (with downgrade rule)
│   ├── sustainability_checks.py    ← RWH, approval complexity
│   └── renderer.py                 ← Text + JSON renderers
│
├── c07_structural_grid.py          ← Component 7 orchestrator: StructuralGridEngine
└── c07/
    ├── __init__.py
    ├── grid_generator.py           ← Devdas Menon parametric grid 3.0–3.7m
    ├── structural_sizer.py         ← Column/beam/slab sizing IS 456
    ├── foundation_engine.py        ← 5 foundation types (isolated/combined/strap/raft/pile)
    ├── global_stability.py         ← IS 1893 + 3-level regularity + drift check
    ├── frame_sanity.py             ← Hardy Cross + Bresler interaction (LEVEL_2)
    ├── load_combinations.py        ← 5-combo set (wind+EQ never combined)
    └── cost_estimator.py           ← Multi-city rates, brand/grade/IS-code annotated
```

**Components 3–6 and 8–17 do NOT exist on disk. There are no placeholder folders.**

## 7.3 Domain layer — `domain/`

Lightweight immutable dataclasses with `__post_init__` validation. All registered in `_DOMAIN_TYPE_NAMES` for v0.7.1 ComponentContract enforcement.

```
domain/
├── __init__.py
├── brief.py                ← Brief, BudgetRange, GuidanceMessage, ComplianceSummary, VastuTier, CostEstimate
├── plot.py                 ← Plot, PlotType (DETACHED/SEMI_DETACHED/CONTINUOUS), PlotFacing
├── floor_requirement.py    ← FloorRequirement, RoomRequirement, FloorUse, RoomType
├── feasibility.py          ← FeasibilityReport, DesignGapAnalysis, Gap, GapSeverity, FeasibilityInput, FieldSource
├── setbacks.py             ← Setbacks (front/rear/side_left/side_right)
├── building.py             ← Building, BuildingMeta
├── envelope.py             ← Envelope (working / regulatory)
├── floor.py                ← Floor, FloorType
├── column.py               ← Column, ColumnLocation
└── grid.py                 ← DomainGrid
```

## 7.4 Knowledge Base — `kb/` (Python) + `kb_rules/` (JSON)

```
kb/
├── __init__.py
├── building_types.py             ← 8-type registry (residential single-family fully implemented)
├── rcc_design_rules.py           ← IS 456 + Devdas Menon
├── soil_foundation_rules.py      ← Soil + water table per city
├── soil_classification.py        ← 12 soil classes IS 1904
├── load_estimation.py            ← IS 875 loads + safety factors
├── seismic_detailing.py          ← IS 13920 + 3-level regularity
├── wind_load.py                  ← IS 875 Part 3 + load combination
├── pile_foundation.py            ← IS 2911 sizing + cost
├── material_rates_chennai.py     ← Chennai 2026 + brand/grade
├── material_rates_multicity.py   ← 5 other cities
└── vastu_engine.py               ← Opt-in Vastu (5 rules; partial = 7 items)

kb_rules/
├── seismic_rules.json
├── setback_rules.json            ← Per-city + per-plot-type (Component 1)
├── room_minimums.json            ← NBC minimums (Component 1)
├── city_feasibility_defaults.json← City-typical soil + water table (Component 2)
├── coverage_rules.json           ← FAR + ground coverage per city
├── load_rules.json
└── rwh_approval_rules.json       ← Mandatory thresholds + approval tiers (Component 2)
```

## 7.5 Utilities — `utils/`

Shared infrastructure used by all components.

```
utils/
├── __init__.py
├── component_contract.py         ← Schema enforcement (v0.5)
├── component_base.py             ← ComponentOutput base class
├── kb_versions.py                ← Centralised version registry + freshness 3-tier
├── kb_rules_loader.py            ← JSON rules loader with schema validation + caching
├── confidence.py                 ← WELL_CONSTRAINED / REGIONAL_TYPICAL / DEPENDS_ON_CHOICE
├── transparency.py               ← The Transparency Triple
├── errors.py                     ← Error taxonomy + format_for_user()
├── logging.py                    ← JSON logging + summarize_trace()
├── rate_provider.py              ← Abstract + brand/grade/IS-code fields
├── sensitivity.py                ← Cost sensitivity (4 drivers in v0.6)
├── structural_sensitivity.py     ← Soil + load sensitivity
├── engineering_depth.py          ← LEVEL_1/LEVEL_2/LEVEL_3 axis (LEVEL_3 unimplementable)
├── legal_disclosures.py          ← 6-section block on every output
├── insights.py                   ← Weekly log analysis (CLI)
├── insights_buffer.py            ← Buffered insights for explain()
└── brief_storage.py              ← localStorage + SQLite resume tokens
```

## 7.6 API endpoints — `api/`

```
api/
├── __init__.py
├── server.py                     ← Stdlib http.server (no FastAPI in current era)
├── brief_endpoint.py             ← POST /api/brief/capture
├── feasibility_endpoint.py       ← POST /api/feasibility/run (chains C1+C2)
└── setback_preview_endpoint.py   ← POST /api/setback/preview (Session M)
```

## 7.7 Frontend — `static/`

```
static/
├── brief_form.html               ← 4-step Tailwind form (feet/metres dual-unit, Session M)
├── brief_form.js                 ← Validation + localStorage save/resume
└── brief_form.css                ← Minimal Tailwind overrides
```

## 7.8 Contracts — `contracts/` (downstream stubs for v2+)

Empty in current build (folder may not exist). Stubs listed in old codebase: `contractor_marketplace.py`, `material_supplier.py`, `bank_loan.py`. Not part of v1.

## 7.9 Tests — `tests/` (40 suites)

```
tests/
├── __init__.py
│
├── test_transparency.py
├── test_grid_generator.py
├── test_c07_structural_grid.py
├── test_multicity_and_stress.py
├── test_v04_trust_controls.py
├── test_v04_block_b_building_types.py
├── test_v05_refinements.py
├── test_v06_phase1.py
├── test_v06_phase2_domain_contracts.py
├── test_v06_phase2_rules.py
├── test_v06_phase3.py
├── test_v07.py
├── test_v071.py
├── test_v072.py
├── test_c07_v093_multiplier_correction.py
│
├── test_c01_session1_domain.py
├── test_c01_session2_setbacks.py
├── test_c01_session3_composition.py
├── test_c01_session4_bridge.py
├── test_c01_session5_orchestrator.py
├── test_c01_session6_api.py
├── test_c01_v09_session_a.py
├── test_c01_v09_session_b.py
├── test_c01_v09_session_c.py
├── test_c01_v09_session_d.py
├── test_c01_v091_patch.py
├── test_c01_v092_patch.py
│
├── test_c02_session_a.py
├── test_c02_session_b.py
├── test_c02_session_c.py
├── test_c02_session_d.py
├── test_c02_session_e.py
├── test_c02_session_f.py
├── test_c02_session_g.py
├── test_c02_session_h.py
├── test_c02_session_i.py
├── test_c02_session_j.py        ← 20-scenario validation across 6 cities
├── test_c02_session_k.py
├── test_c02_session_l.py        ← Bucket A patches
└── test_session_m_feet_ui.py    ← Feet/metres dual-unit UI
```

**Total: 40 suites, 937 tests passing in v0.10.1 packaged build.**

## 7.10 Documentation — `docs/`

```
docs/
├── architecture.md
├── v2_backlog.md
├── v2_vision.md
├── c02_user_guide.md             ← Homeowner-facing
├── c02_v0.1_release.md           ← Release notes
├── c02_v0.1_validation_report.md ← Auto-generated from test_c02_session_j.py
└── component1/
    ├── SPEC_v0.1.md              ← Superseded
    └── SPEC_v0.2.md              ← LOCKED — used for build
```

## 7.11 Examples + book-to-code

```
examples/
└── run_c07_on_ne_30x40.py        ← Canonical NE 30×40 example

book_to_code/                      ← Pattern for KB scaling
├── README.md
├── 01_extracted/                  ← Raw code text from books
├── 02_structured/
│   └── IS456_25_1_2.json         ← Structured JSON
└── 03_code/
    └── IS456_25_1_2.py           ← Generated Python
```

## 7.12 Era 1 reference (in `06_original_uploads_pre_history/`)

Not part of current codebase but kept for reference. Many functions have been ported into the v3 architecture; some (like the structural grid generator and Style 2 renderer) are reusable substantially as-is.

```
buildemup_knowledge/                  (28 reference files in archive)
├── BUILDEMUP_MASTER_RECORD.md        ← 1067-line Era 1 record
├── BuildEase_Analysis_Report_2026-04-15.md
├── ching_fso.py                      ← Ching Form Space Order — REUSABLE in C8
├── parametric_layout.py              ← Structural grid — PORTED into C7's grid_generator.py
├── cad_drawing_standards.py
├── graphic_standards.py              ← IS 962 — REUSABLE in C16
├── feasibility.py / feasibility_complete.py  ← SUPERSEDED by C2 dual-design
├── general_placer.py                 ← To be replaced by C5+C9+C10+C11
├── placement_engine.py               ← Has the mw=10/cw=6/btw=3 hardcoded constants (Pattern A bug)
├── room_rules.py / zoning.py         ← Informed C1's room_minimums.json
├── layout_optimizer.py (7,262 lines) ← Orphaned NSGA-II scaffolding — to be wired in C11b
├── furniture_test.py                 ← 2026 Indian furniture dimensions — REUSABLE in C9
├── external_wall_checker.py          ← NBC light + ventilation — REUSABLE in C14 Hard Constraints
├── structural_checker.py             ← Door swing + grid — REUSABLE in C13
├── renderer_bridge.py (346 lines)    ← Style 2 renderer — REUSABLE in C16
├── buildease_arch_intel.py           ← 7 of 8 stubs returning 75.0; AdjacencyGraph class is real
├── buildease_kb_v2.py                ← KB v2 import shim
└── ... (other reference files)
```

---

# PART 8 — Build Status (LIVE TRACKER)

The single status board. **Updated after every coding session.**

## 8.1 At a glance — 30 April 2026 (post Session 20)

| Metric | Value |
|---|---|
| **Components shipped (Track 3)** | 3 of 17 (C1, C2, C7) |
| **Components in active build (Track 3)** | C3a — Sessions 1–5 of 8 shipped (Domain + Detection + Options + Apply/Format + Counterfactual/Preflight) |
| **Components pending (Track 3)** | 13 (C3b, C4, C5, C6, C8, C9, C10, C11a, C11b, C12, C13, C14, C15, C16, C17) |
| **Tests passing (v0.10 deployed)** | 913 across 39 suites |
| **Tests passing (v0.10.1 packaged)** | 937 across 40 suites |
| **Tests passing (C3a S1+S2+S3+S4+S5+B-027 isolated)** | 165 across 8 suites (new, not yet integrated to main repo) |
| **Live URL** | https://buildease-production.up.railway.app |
| **Last successful deploy** | v0.10 |
| **Packaged but undeployed** | v0.10.1 (feet/metres UI) + C3a S1–S4 (in build dir) |
| **Knowledge base modules** | 11 in `kb/` + 7 JSON in `kb_rules/` + 28 archived from Era 1 |
| **City coverage** | 6 cities full DCRs (Chennai TNCDBR, Mumbai DCPR 2034, Delhi MPD-2021, Bangalore BBMP/UDD, Pune UDCPR, Hyderabad GHMC) |
| **Building types architecturally supported** | 8 (residential single-family fully implemented; 7 stubbed) |
| **Active specs** | parent C3a `SPEC v0.2.1a LOCKED` + per-session `buildemup_S4_SPEC_v0_1_LOCKED.md` (S5 spec next) |

## 8.2 Component-by-component status

### ✅ Component 7 — Structural Grid Engine v0.7.3

**Sub-modules:** 7 + orchestrator (see Part 7.2).

**Tests:** 274 across 12 suites (`test_c07_*` + `test_grid_generator.py` + `test_multicity_and_stress.py` + `test_transparency.py` + `test_v04_*` + `test_v05_*` + `test_v06_*` + `test_v07*`).

**Validation status:** PENDING ENGINEER VALIDATION (cannot transition out — Invariant 5).
**Engineering depth:** LEVEL_2_FRAME_CHECKED.
**Cities:** 6 with material rates.
**Building types:** Residential single-family fully implemented; 7 others stubbed and refused gracefully.

### ✅ Component 1 — Brief Capture Engine v0.9.3

**Orchestrator:** `components/c01_brief_capture.py`. **Sub-modules:** 8 (see Part 7.2).
**KB rules:** `setback_rules.json`, `room_minimums.json`.
**Frontend:** `brief_form.html` + `.js` + `.css` (4-step Tailwind, feet/metres dual-unit).
**API:** `POST /api/brief/capture`.

**Tests:** 220+ across 12 suites (S1–S6 + v0.9 Sessions A–D + v0.9.1 + v0.9.2 patches).

**Coverage:**
- Plot types: DETACHED / SEMI_DETACHED / CONTINUOUS (TNCDBR explicit)
- 6 cities full DCRs (Chennai TNCDBR, Mumbai DCPR 2034, Delhi MPD-2021, Bangalore BBMP/UDD, Pune UDCPR, Hyderabad GHMC)
- Vastu 3-tier: OFF (default) / PARTIAL (7 items) / FULL
- Auto-staircase for floors ≥ 2
- Parking feasibility check
- Phased construction suggestion
- Save/resume via localStorage + SQLite token (server-side cross-device deferred to v0.2)

### ✅ Component 2 — Feasibility Engine v0.1 (Sessions A–L)

**Orchestrator:** `components/c02/orchestrator.py` — `run_feasibility()`. **Sub-modules:** 9.
**KB rules:** `city_feasibility_defaults.json`, `rwh_approval_rules.json`.
**API:** `POST /api/feasibility/run` (chains C1 + C2).
**Docs:** `docs/c02_user_guide.md`, `docs/c02_v0.1_release.md`, `docs/c02_v0.1_validation_report.md`.

**Tests:** 245 across 12 suites (Sessions A–L).

**Coverage:**
- 17 of 18 v0.1 checks (room minimums deferred)
- Dual-design pattern (Practical + Code-Strict)
- 3-state input + downgrade rule
- 20-scenario validation across 6 cities, G+0 to G+3

**Honesty caveat (Invariant 8):** Most realistic briefs land at Code-Strict 40 because most homeowners don't have soil tests / verified water table at brief-capture time. This is correct NBC behaviour. Best case (verified data + S-facing + G+0) = 90/90 with 0 gaps.

### ⏳ Component 3a — Extreme Case Gate — Sessions 1–6 of 8 SHIPPED + S7a SPEC LOCKED + S7a code ~30–40% built (in build directory)

**Architecture:** Pre-layout gate. Surfaces fundamental brief-level blockers as decisive "you must change X" moments. Receives `DesignGapAnalysis` from C2; produces `ResolvedBrief` for downstream layout pipeline.

**Status:** Active build. Parent SPEC v0.2.1a LOCKED. S4 SPEC v0.1 LOCKED + shipped. S5 SPEC v1.0 LOCKED + shipped (incl. critique-round-2 fixes v1.1). B-027 (S6 prerequisite) v1.0 LOCKED + shipped (incl. code-critique fixes v1.1). S6 SPEC v1.0 LOCKED + shipped (incl. 2 code-critique rounds — round 1 added `MappingProxyType` immutability; round 2 added defensive copy + Mapping signature). **S7 SPEC v1.0 LOCKED as S7a** (S7 split into S7a endpoints+serialization+storage and S7b deployment hooks per round 2 P17). **S7a code build ~30–40% complete; mid-build handoff prepared.** Sessions 1–6 of 8 shipped + B-027 shipped + S7a code partial; **188 tests passing across 12 suites (no new tests yet from S7a build)**.

**Deliverables (S1–S6):** see prior session entries (4.18–4.23).

**Deliverables (S7a — PARTIAL, per Session 23):**
- LOCKED SPEC: `buildemup_S7a_SPEC_v1_0_LOCKED.txt` (1,492 LOC) — 5 endpoints, full serialization tree (S6/S1/C1/C2 owns), SQLite storage with WAL+retry+single-flight+atomic co-write+brief→session uniqueness index, hook stubs, terminal-replay 200, idempotency via request_id, deterministic JSON. P1–P18 patches across 2 critique rounds; 4 round-2 items pushed back per D-067; 3 backlog items logged (B-040, B-041 expanded, B-042).
- COMPLETE: `utils/gate_state_storage.py` (~230 LOC) — all v1.0 hardenings
- COMPLETE: `domain/_serialization.py` (~50 LOC) — generic helpers
- COMPLETE: serialization tree for Brief side — Plot, Setbacks, RoomRequirement, FloorRequirement, BudgetRange, GuidanceMessage, Brief; smoke-tested round-trip
- COMPLETE: `gate_state.py` to_dict/from_dict + TransitionBannerEvent + DifferentPlotPromotionEvent + SchemaVersionError
- PARTIAL: 4 of 10 types in `extreme_case.py` (BriefChange, CostImpact, ResolutionOption, ExtremeCase)
- PENDING: 6 more extreme_case types, all of feasibility.py, feasibility_input.py, 5 endpoint handlers, 2 hook stubs, server.py routes, ~28 tests
- 188 / 188 c3a baseline PASS (additive changes only; nothing broken)

**Sessions remaining (S7a finish + S7b + S8):**
- **S7a continuation** — finish serialization tree + endpoints + tests (~700 LOC source + ~1,420 LOC tests remaining)
- **S7b** — production deployment hooks (real SMTP, real scheduler, observability) — separate session per P17 split
- **S8** — Validation suite — integration tests across 10 EC paths + Preview + CBA fallback + preflight + reason-aware errors (~700 LOC, ~7 tests)

**Total estimated remaining:** ~3,500 LOC across 3+ sessions.

**Backlog:** 39 items in `v0_2_backlog.md` (B-001 through B-042). Recent additions:
- B-035 through B-038 from B-027 code critique deferrals (Session 21).
- B-039 from S6 code critique round 1 #4 (option-generation caching) — Session 22.
- B-040 from S7a spec round 1 #9 (schema migration layer; when v2 schema lands).
- B-041 expanded from S7a spec round 1 #5 + round 2 #10 (BriefStorage WAL retrofit + prune-on-resume + periodic prune).
- B-042 from S7a spec round 1 #10 + round 2 #8/#13 (project-wide auth — token binding to client_id, rotation, session scoping; spans both GateStateStorage and BriefStorage).

### ⏸️ Component 3b — Post-Layout Trade-off Negotiation — DEFERRED

**Architecture:** Post-layout. Surfaces specific tweaks once user has seen layouts. Bigger scope than 3a.

**Status:** Deferred until layout pipeline (C4-C16) exists. Cannot be built before layouts can be generated.

### Pending: Components 4 → 17 (excluding 3a build above)

Per architecture v3 build order (Part 5).

## 8.3 Cross-cutting status

- **Contractor Defence Layer:** Document templates may exist in old `documents/` folder; auto-generation deferred to Component 16 build.
- **Resilience Layer:** Implemented per-component for C1/C2/C7 (graceful failure messages, no stack traces to user).
- **Constraint Propagation:** Partial — `utils/component_contract.py` enforces I/O schemas. `repair_violation()` deferred to Component 11b.
- **Fast Mode / Deep Mode:** Not yet implemented (depends on Components 5–14).

## 8.4 Deployment

**Live:** https://buildease-production.up.railway.app
- Auto-deploys on push to `main` of https://github.com/ramalingam38-rgb/buildease
- v0.10 currently live (Sessions A–K applied)
- v0.10.1 packaged but not deployed (Ramalingam was on phone, deferred decision)

**Local dev:**
```powershell
# Windows path: C:\1.Startup Project latest\buildemup
cd "C:\1.Startup Project latest\buildemup"
python -m buildemup.api.server  # stdlib server, no Flask/FastAPI
```

**Deploy command sequence:**
```powershell
git add .
git commit -m "Your description"
git push origin main
# Railway auto-deploys in 2-3 minutes
# Verify: curl https://buildease-production.up.railway.app/health
```

## 8.5 What's NOT yet on Railway (action items)

- v0.10.1 zip (feet/metres UI + `/api/setback/preview` endpoint + dual-unit reports + Session M tests)
- Style 2 renderer from Era 1 (deferred — irrelevant; Component 16 v3 supersedes it)

## 8.6 The 40-cap (re-emphasised — Invariant 8)

This is critical for understanding why the deployed system shows realistic-looking low scores:

**Most users don't have at brief-capture time:**
- A soil test (₹3,000–8,000, takes a week) → `soil_type_code_strict` HARD-fails
- Water table verification (free if drilled, but few homeowners think to check) → `water_table_code_strict` HARD-fails on G+1+

**Result:** typical Code-Strict score = 40. Practical score is usually higher (60–75) because Practical doesn't HARD-fail on assumed defaults.

**This is the engine being honest:** it's saying *"You can probably build this house, but to be NBC-bulletproof at approval stage, get the verified data."* A fake 80/100 across the board would be less useful and less honest.

## 8.7 Test counts evolution (chronological)

| Date | Version | Tests | Suites |
|---|---|---|---|
| 23 Apr | C7 v0.4 | 53+ | 5 |
| 23 Apr | C7 v0.5 | 98 | 7 |
| 23 Apr | C7 v0.6 Phase 1 | 164 | 11 |
| 23 Apr | C7 v0.7.2 | 194 | 11 |
| 23 Apr | C7 v0.7.3 | 274 | 12 |
| 24 Apr | C1 S1–S5 | 379 | 19 |
| 24 Apr | C1 v0.1 (post S6) | ~430 | 21 |
| 25 Apr | C1 v0.9 | 438 | 22 |
| 25 Apr | C1 v0.9.1 | 482 → 502 | 24 |
| 27 Apr | C1 v0.9.3 + C2 S-A | 534 | 27 |
| 27 Apr | C2 S-B | 581 | 29 |
| 27 Apr | C2 S-J (validation) | 738 | 35 |
| 28 Apr | C2 S-K (deploy v0.10) | 871 → 913 | 37–39 |
| 28 Apr | C2 S-L + S-M (v0.10.1) | 937 | 40 |
| 30 Apr | C3a S1+S2 (in-build, isolated) | 1,008 (937 + 71) | 42 |
| 30 Apr | C3a S3 shipped + drawback patch + S4 spec locked | 1,037 (937 + 100) | 43 |
| 30 Apr | C3a S4 shipped (apply + formatter) | 1,058 (937 + 121) | 45 |
| 30 Apr | C3a S3 (in-build, isolated) — v2.4 | 1,037 (937 + 100) | 43 |
| 30 Apr | C3a S4 (in-build, isolated) — v2.5 | 1,058 (937 + 121) | 44 |
| 30 Apr | C3a S5 (in-build, isolated) — v2.6 | 1,095 (937 + 158) | 47 |
| 30 Apr | C3a S5 + B-027 (in-build, isolated) — v2.7 | 1,102 (937 + 165) | 48 |
| 30 Apr | C3a S6 shipped + 2 code-critique rounds (in-build, isolated) — v2.8 | 1,125 (937 + 188) | 52 |
|  1 May | C3a S7a SPEC LOCKED + code ~30-40% (in-build, isolated, no new tests yet) — v2.9 | 1,125 (937 + 188) | 52 |

---

# PART 9 — Key Decisions Log

Chronological list of every "we decided X because Y" decision. Each is a reference for future work — these are LOCKED unless explicitly reopened.

## 9.1 Era 1 decisions (carried forward)

| ID | Date | Decision | Rationale |
|---|---|---|---|
| D-001 | 12 Mar 2026 | Tech stack = Python | Fast iteration |
| D-005 | 16 Apr 2026 | **Topology decided BEFORE rooms placed** | Topology-blind placement is the root cause of bad lived-quality. Survives into v3 architecture. |
| D-006 | 16 Apr 2026 | **Bedrooms > Kitchen > Living priority order for cuts** | Indian family priorities. Locked as Invariant 6. |
| D-009 | 17 Apr 2026 | BuildEase → BuildemUp branding (provisional) | Avoid trademark conflict during dev |
| D-010 | 17 Apr 2026 | Style 2 renderer (clean white + furniture symbols + dimension chains + door arcs) | User wants "easily understood by client AND usable by contractor", NOT full technical CAD |
| D-011 | 17 Apr 2026 | L-shaped rooms render as single polygon | Era 1 Problem 6 — auditor false-flagged |
| D-012 | 20 Apr 2026 | **Bathroom on FAR side of bedroom** (corridor → bedroom → bath) | Era 1 Problem 3. Locked in C10 spec. |

## 9.2 Era 2 architectural reset decisions

| ID | Date | Decision | Rationale |
|---|---|---|---|
| D-014 | 20 Apr | **Full architectural reset** | 15 known problems; topology-blindness can't be patched |
| D-015 | 20 Apr | 17 components in execution order, three layers | Architecture v3 |
| D-016 | 20 Apr | **Hard/Soft constraint split** in Evaluation Engine | Without this, structurally invalid layouts can be Pareto-optimal on cost. CRITICAL. |
| D-017 | 20 Apr | Quote Comparison Engine = Component 17 | Highest-value consumer feature. Strongest moat. Saves users ₹5–10L per project. |
| D-018 | 20 Apr | Layout triad final naming: **Cost Efficient / Everyday Living / Premium Design** | Not Privacy/Light/Cost. Not Balanced. |
| D-019 | 20 Apr | **Vastu opt-in INFO-only**, three tiers, never blocks | Cultural preference, not building code |
| D-020 | 20 Apr | **Confidence renamed:** HIGH/MEDIUM/LOW → WELL_CONSTRAINED/REGIONAL_TYPICAL/DEPENDS_ON_CHOICE | "HIGH" carries semantic weight overriding inline definitions |
| D-021 | 20 Apr | Banner: **"RULE-BASED HEURISTIC ESTIMATE" + "NOT structural design"** | Legal hardening; positioning as decision-support not engineer-replacement |
| D-022 | 20 Apr | `user_claims_engineer_reviewed` flag with audit fields, BuildemUp never verifies | "PENDING ENGINEER VALIDATION (user claims engineer reviewed — UNVERIFIED)" |
| D-023 | 20 Apr | Engineering depth axis. **LEVEL_3 unimplementable by design** | No `level_3_indicator()` function exists |
| D-024 | 20 Apr | **Build order: Component 7 → 1 → 2 → 3 → 4 → 5 → 6 → 8 → 9 → 10 → 11a → 11b → 12 → 13 → 14 → 15 → 16 → 17** | C7 = structural foundation; C1 = user entry; C2 validates brief |
| D-025 | 20 Apr | Six cities for v1: Chennai, Bangalore, Hyderabad, Mumbai, Pune, Delhi | Major metros |
| D-026 | 20 Apr | Plot tiers: T1 600–2400 fully supported, T2 2400–4000, T3 4000+ best-effort | Honest scaling |
| D-027 | 20 Apr | Industrial / warehouse buildings excluded from scope. 7 of 8 building types stubbed. | Not target market |
| D-028 | 20 Apr | Plot type added: **DETACHED / SEMI_DETACHED / CONTINUOUS** | Chennai TNCDBR has explicit "Continuous Building Area" |
| D-029 | 25 Apr | All 6 cities = full real DCRs (no NBC fallback) | After Mumbai DCPR 2034, Delhi MPD-2021, Bangalore BBMP, Pune UDCPR, Hyderabad GHMC research |
| D-030 | 24 Apr | **Component 1 → Component 7 budget bridge** (C7 called twice per request) | Single source of truth for cost; ~200 ms overhead acceptable |
| D-031 | 24 Apr | Save/resume = localStorage in v0.1 + SQLite token; cross-device deferred | No server-side state in v0.1 |
| D-032 | 24 Apr | **Form-based brief in v0.1**; LLM extraction deferred to v2 | Reliability + cost |
| D-033 | 27 Apr | **Component 2 dual-design pattern**: Practical + Code-Strict + Gap | Honest about cost of compliance |
| D-034 | 27 Apr | Scoring contract: 100 base − 5/7/10 per SOFT_WARN by confidence; HARD_FAIL caps at 40 | Single blocker = not buildable as-stated |
| D-035 | 27 Apr | **Most realistic briefs land at Code-Strict 40 — this is correct, not a bug** | Most users don't have soil/water-table tests at brief-capture; honest signal more useful than fake 80/100 |
| D-036 | 27 Apr | **3-state input + downgrade rule:** assumed-default values that would HARD_FAIL get downgraded to SOFT_WARN; user-provided values keep strict outcome | Don't block on a guess |
| D-037 | 23 Apr | Configuration-driven rules pilot: `kb_rules/seismic_rules.json`. Parity test caught Zone III bug. | Non-developer editability + bug prevention |
| D-038 | 23 Apr | ComponentContract enforcement test in CI | Mechanically prevents Pattern B (building without wiring) |
| D-039 | 23 Apr | **Legal disclosures in 6 sections**, prepended to every explain() | Legal hardening |
| D-040 | 23 Apr | PII handling: engineer name/license/date/consultant redacted before logging or export | Data minimisation |
| D-041 | 23 Apr | **Frame sanity (Bresler interaction) wired into orchestrator output**; per-column; worst 3 surfaced if WARN/FAIL | Real engineering, not just rules-of-thumb |
| D-042 | 23 Apr | **Wind+EQ never combined per IS practice** | Verified by web research |
| D-043 | 23 Apr | Real IS 1904 soil bearing capacity — 12 soil classes, hard rock 450–3300 kN/m², black cotton flagged expansive | Earlier wrong values rejected |
| D-044 | 28 Apr | **v0.10 is the first deployable post-reset version** | Sessions A–K shipped; deployed to Railway |
| D-045 | 28 Apr | v0.10.1 packaged but not deployed (deferred) | User on phone |
| D-046 | 29 Apr | This master document v2 created and maintained as single source of truth | Recovery from previous master document built from partial info |
| D-047 | 29 Apr | **Component 3 split into 3a (pre-layout Extreme Case Gate) + 3b (post-layout Trade-off Negotiation)** | User insight: extreme cases are pre-layout decisions ("you must decide"); richer trade-offs only become concrete after user sees layouts. Splitting honors both jobs without conflating them. |
| D-048 | 29 Apr | **10 Extreme Cases locked** for v0.1: EC-001 through EC-010 across SPATIAL/LEGAL/BUDGET/SITE/APPROVAL categories with specific detection thresholds | List developed collaboratively, validated against Indian construction reality (TNCDBR, MPD-2021, DCPR 2034, etc.), cross-checked with web research where applicable. |
| D-049 | 29 Apr | **Preview Mode added** to C3a — user can see layout past any EC with hard guardrails (mandatory checkbox + room-internal watermarks at 30% opacity + dimension ranges only + no construction details) | User-driven: families have legitimate reasons to see "the dream" (emotional processing, family discussion, variance pursuit decision). Hard guardrails prevent contractor misuse. |
| D-050 | 29 Apr | **Build order Path C: C3a now, layout pipeline (C4-C16) after** | Path C trades 6 weeks of upfront work for the right UX flow (brief → feasibility → see layouts → iterate). Alternative paths considered: A (C3 pre-layout only, 1 week, small UX win), B (two-mode C3, hybrid). User picked C. |
| D-051 | 29 Apr | **EC-008 budget threshold locked at × 1.5** (50% over budget) for hard EC, with × 1.25 (25% over) as soft early-warning tier | Web research (15 sources): industry-average overrun is 15-28%, contingency buffer is 10-15%, phased construction absorbs 30-40% gaps, top-up loans cover 20-35%. Beyond 50%, no standard mechanism bridges. Setting threshold lower would alarm-fatigue users on the typical case. |
| D-052 | 29 Apr | **Decision logging Level B: chosen option + presented option set** captured in ExtremeDecision.presented_options | Audit + analytics research: Level A (chosen only) makes "which alternatives are systematically underused" analysis impossible. Level C (per-click telemetry) deferred to v2. Level B is free uplift. |
| D-053 | 29 Apr | **No plot type toggling DETACHED↔CONTINUOUS in C3a flow**; advisory only with email-checklist follow-up | TNCDBR research: CBA classification is a Master-Plan attribute, not a user choice. Misclassification is a known approval failure mode. Engine's job is advisory ("verify with CMDA"), not toggle. |
| D-054 | 29 Apr | **Two-tier budget signal**: 1.25× → SOFT_WARN through C2 scoring (-7 to score, no modal); 1.5× → hard EC-008 with full modal | Per critique #1: at 1.3× user already feels "this is impossible." Single 1.5× threshold misses the emotional moment when they could course-correct cheaply. |
| D-055 | 29 Apr | **Preview Mode requires explicit `PreviewModeAcknowledgment`** with mandatory checkbox + room-internal watermarks (not just page edges) + dimension ranges + no construction details (no door swings, electrical, plumbing, structural) | Per v0.2.1 critique #1 CRITICAL: prevents contractor misuse. Watermark in rooms is impossible to crop out. Dimensions as ranges prevent layout being used as measurement reference. Construction details suppressed prevents pseudo-buildable appearance. |
| D-056 | 29 Apr | **C3a S1 (Domain Objects) shipped** with 53 tests passing — 5 enums + 10 dataclasses in `domain/extreme_case.py` | First build session of C3a. All invariants from v0.2.1 spec encoded as `__post_init__` validations. Foundation locked before downstream sessions S2-S8. |
| D-057 | 30 Apr 2026 | **EC-010 surfaces highest-impact blocker first** when multiple `legal_only_checks` fire simultaneously; sort key is resolution_probability ascending (LOW first). One ExtremeCase per detector run, not one per blocker. | Surfacing N approval blockers in N modals creates decision paralysis; the LOW-probability one drives the path-to-different-plot decision and remediating it tends to remediate the others. |
| D-058 | 30 Apr 2026 | **Detector returns placeholder ResolutionOption pairs**; S3 replaces them with real options. Two identical placeholders satisfy `ExtremeCase.__post_init__`'s ≥2-options invariant without crossing into S3 scope. | Pattern E (scope creep mid-build) discipline. Detector is still wired (public `ExtremeCaseDetector.detect()` API); S6 orchestrator chains detector→generator. |
| D-059 | 30 Apr 2026 | **BriefChange `field_path` vocabulary locked at S3.** The 13 paths emitted by S3's option_generator are the canonical alphabet S4 must interpret: `rooms.{room_type}.count`, `rooms.all.size`, `floors.add`, `floors.{N}`, `floors.add_stilt`, `floors.count`, `setbacks.{front_m,rear_m,side_left_m,side_right_m}`, `budget.max_lakhs`, `parking.has_covered`, `coverage.reduce_footprint`. `parking.has_covered` and `coverage.reduce_footprint` currently store as audit-trail strings in `additional_requirements` (B-011 tracks the schema upgrade). | Locking the vocabulary at S3 ship-time prevents drift when S4 surfaces ambiguities. Lock-then-iterate (with B-005 tracking refinements) is cleaner than retroactive S3 changes. |
| D-060 | 30 Apr 2026 | **Precondition-guarded options emit as informational, not missing.** When `option_generator` would emit a ResolutionOption whose BriefChange would push the brief below domain minima (1BHK→0BHK, 1 floor→0 floors), the option is still emitted with `requires_brief_change=()`, `recommended=False`, and `risk_advisory` explaining why. Affected: EC-001 op B, EC-002 op A, EC-007 op B, EC-008 op B (chain). | Spec invariants on per-EC option counts are preserved. Conditional UI (sometimes 5, sometimes 6 options) is worse UX than consistent UI with one greyed-out option. |
| D-061 | 30 Apr 2026 | **Per-session locked specs for ≥100-LOC builds.** Each C3a session producing >100 LOC source gets its own locked spec written and approved before build start. Parent spec stays the umbrella; per-session specs are build-ready derivatives. First instance: `buildemup_S4_SPEC_v0_1_LOCKED.md` (568 lines), authored end of Session 19. | Parent spec describes *what*; per-session specs describe *how* for one slice. Splits the parent's 1350 lines into focused per-session reads, reducing context load on each session's Claude. Pattern carried forward to S5, S6, S7, S8. |
| D-062 | 30 Apr 2026 | **S4 BriefChange application is purely declarative (full-replace via `dataclasses.replace`).** Every handler returns a new Brief; the input is never mutated. `apply_brief_changes` does NOT roll back earlier successful applies on a later failure — there's nothing to roll back because the input Brief is its own rollback. | Pattern carried forward to all C3a appliers (S5, S6 included). Aligns with the project's frozen-dataclass discipline and makes the integrity invariant (parent spec § 3.3) trivially satisfied. |
| D-063 | 30 Apr 2026 | **Reason-aware error formatter is a separate module from the applier.** `error_formatter.py` ≠ `brief_change_apply.py`. Applier raises classified `BriefChangeIntegrityError` (with `classification` + `context` dict); formatter renders to user-facing copy. Formatter is a pure render layer with no domain logic; it never raises (defensive `try` swallows `format()` errors back to UNKNOWN template). | Lets S6 log structured errors before rendering. Lets S7 serialize errors as JSON cleanly without copy. Isolates copy changes from applier tests. The split was specified in S4 SPEC v0.1 § 1 and § 9.2. |
| D-059 | 30 Apr 2026 | **BriefChange `field_path` vocabulary locked at S3** — the 11-path canonical alphabet (`rooms.{type}.count`, `rooms.all.size`, `floors.add`, `floors.{N}`, `floors.add_stilt`, `floors.count`, four `setbacks.*_m`, `budget.max_lakhs`, `parking.has_covered`, `coverage.reduce_footprint`) is what S3 emits and S4 interprets. | S3 needed a stable vocabulary to emit; S4 needed the same to interpret. Locking at S3 ship-time prevents drift. Refinement tracked as B-005. |
| D-060 | 30 Apr 2026 | **Precondition-guarded options emit as informational** — when a guard would push the brief below domain minima (1BHK→0BHK, 1 floor→0 floors), the option still emits with `requires_brief_change=()`, `recommended=False`, and a `risk_advisory`. Per-EC option counts stay constant. | Conditional UI (sometimes 5 options, sometimes 6) is worse UX than consistent UI with one greyed-out option; preserves spec invariants on per-EC option counts. |
| D-061 | 30 Apr 2026 | **Per-session locked specs for ≥100 LOC builds.** Each C3a session producing >100 LOC source gets its own locked spec written and approved before build start. Parent spec is the umbrella; per-session specs are the build-ready derivatives. | Reduces context load on each session's Claude. First instance: S4 SPEC v0.1 LOCKED. S5/S6/S7/S8 will each get their own locked spec at the end of the preceding session. |
| D-062 | 30 Apr 2026 | **S4 BriefChange application is purely declarative** — every handler returns a new Brief via `dataclasses.replace`; never mutates the input. `apply_brief_changes` accumulates changes by reassigning a local; no rollback bookkeeping needed because the caller's input Brief is untouched. | Functional purity makes testing trivial (test 12 confirms input unchanged). Avoids whole classes of state-corruption bugs. Pattern carried forward to all C3a appliers. |
| D-063 | 30 Apr 2026 | **Reason-aware error formatter is split from applier** — `error_formatter.py` ≠ `brief_change_apply.py`. Applier raises classified `BriefChangeIntegrityError` (with classification + context dict); formatter renders to user-facing copy. Neither imports the other. | Lets S6 log structured errors before rendering, lets S7 serialize errors as JSON cleanly, isolates copy changes from applier tests. The formatter is a pure render layer; the applier is a pure transformation layer. |
| D-064 | 30 Apr 2026 | **D-061 retired.** Sessions continue building until user decides to stop, NOT at session boundaries. External critique on every spec is non-negotiable; what changes is that lock-then-build can happen in the same conversation. | User explicitly requested this mid-session: "I want every spec doc to be analysed by the critique. Sessions conclude when I want to, not when Claude wants to." Velocity-vs-discipline trade-off now in user's hands per session. |
| D-065 | 30 Apr 2026 | **Critique-vs-prior-decision conflict resolution.** When a new critique round disagrees with a previously-locked critique decision (S5 round 1's Drawback 4 wanted to lift the cap-of-2 that v0.2.1 critique #5 had locked), Claude pushes back on the new critique citing the prior decision's rationale rather than churning. The disagreement is logged to backlog (B-019 in this case) for revisit only if real user data accumulates. | Without this rule, successive critique rounds can flip-flop on the same decision. The original critique's rationale doesn't disappear because a new critique disagrees; it requires new evidence (user data) to override. |
| D-066 | 30 Apr 2026 | **Mandatory build cycle for every C3a session and onward**: spec draft → external critique → patch → lock → code → external code critique → patch → next session. Each step's output delivered to user as a standalone file (spec as `.txt`, code as consolidated `.py`). User decides when to hand off; Claude reports context budget honestly so user makes the stop decision. | User-defined rule, locked end of Session 21. Replaces ad-hoc cadence with a predictable cycle. Code critique step (new vs prior cycle) catches issues a spec critique can't see — like the `_format_category_list` upper/lowercase enum-value drift caught in S5. Both critique stages are now part of the discipline. **Refined later in Session 21:** continue building until USER says stop; Claude does NOT suggest handoff; Claude does NOT mention context budget casually. ONE EXCEPTION: if context is genuinely too low to complete current step at quality, Claude tells user straight as a quality-protection signal (not a stop prompt). |
| D-067 | 30 Apr 2026 | **Critique-vs-prior-decision pushback rule (extension of D-065).** When the latest critique round would force: (a) Pattern E surgery for hypothetical future need, (b) optimisation for cases that don't exist yet, (c) overcorrection with hostile mechanisms (caller detection, graceful degradation that masks invariant violations) — Claude pushes back, citing prior decisions and YAGNI. Pushback is documented in the response so the user can override if they disagree. | Surfaced during B-027 code critique round 2 where 3 of 10 critique items would have over-architected the code (caller-frame inspection breaking tests; graceful degradation hiding programmer bugs; rule engine for 3 named predicates). B-035 through B-038 are the deferred items from this rule. Without D-067, successive critique rounds would push toward maximalist architecture; with it, prior YAGNI-driven decisions are protected. |
| D-068 | 30 Apr 2026 | **Handoff packaging — organizational principle.** When user calls for handoff, deliverable MUST be consolidated chronologically: master doc + all specs (chronological) + all code + backlog + integrity check + orientation. Section markers for navigation. **Original form: single .md file. SUPERSEDED by D-069 below for FORMAT only — the chronological/consolidated PRINCIPLE remains.** | User-defined rule, end of Session 21. Single-file handoff was easier to review BUT failed in practice — the 1 MB consolidated .md exceeded download limits in the user's app. Format requirement updated by D-069. |
| D-069 | 30 Apr 2026 | **Handoff format — single ZIP file.** When user calls for handoff, deliverable is ONE zip file containing the chronologically organized package (per D-068's principle). The zip contains: 00_START_HERE/, 01_master_doc/, 02_specs_chronological/, 03_code_chronological/, 04_backlog/, 05_integrity_check/. Single zip downloads reliably; user extracts and reads at leisure. NOT a giant consolidated .md (download fails); NOT a folder of loose files (cumbersome). ONE zip. | User confirmed end of Session 21: "I was able to download zip files even if it's just one." This supersedes D-068's format requirement (the ".md single file" form). D-068's organizational principle (chronological, complete, sectioned, integrity-checked) is preserved — it's just delivered as zip rather than .md. |

---

# PART 10 — The 12 Unique Properties of BuildemUp (the moat)

When BuildemUp launches, this is what nobody else has. From `BuildemUp_Architecture_v3.md` §9.

1. **Topology-first, grid-first generation pipeline** — most AI tools place rooms freely; we decide topology and structural grid before any room is placed
2. **Topology mutation layer with 9 operators** including entry-door relocation — explores globally-different solutions, not just parameter tweaks
3. **Furniture-fit as a Hard Constraint** — Neufert-based 2D packing per room; "bedroom can be 80 sqft per NBC" is not enough if a queen bed + wardrobe + clearance won't fit
4. **Six Indian-family optimisation objectives** (pooja, multigen, bath-practicality, wet-zone-₹, climate, contractor margin) — Western tools cannot replicate without rebuilding their KB
5. **Hard/Soft constraint split** — correctness guarantee; invalid layouts can't survive Pareto filtering
6. **Problem list instead of single score** — 30+ specific checks across 9 categories; no fake "94/100"
7. **Dual envelope** (working setbacks + regulatory setbacks) with cost delta
8. **Dual drawings** (contractor working drawing + CMDA regulatory drawing)
9. **Contractor Defence Layer** — 4 documents that arm the family against information asymmetry
10. **Quote Comparison Engine** — the strongest individual differentiator; user uploads contractor quote, engine flags overpricing
11. **Climate-zone-aware orientation rules** — NBC 5 zones, not one-size-fits-all
12. **Visible contractor margin line** — transparent by default

Of these, **#10 (Quote Comparison Engine) is the single biggest differentiator.** Most likely to generate viral word-of-mouth. Hardest for Western AI tools to replicate (requires Indian cost knowledge + contractor-practice awareness + financial-document trust).

---

# PART 11 — Where We Continue From Here

## 11.1 Starting point — Session 24 (fresh conversation)

**Next session:** Component 3a Session 7a CONTINUATION — finish the code build from where Session 23 paused.

**This is a MID-BUILD resume, not a fresh start.** S7a SPEC v1.0 is LOCKED. ~30–40% of the code is built and the 188 c3a baseline still passes. The next Claude must:

1. Unpack `buildemup_workdir.tar.gz` from the handoff into `/home/claude/work/`
2. Run `python -m unittest discover -s buildemup/tests -p "test_c03a_*.py"` — must show 188/188 OK before writing any code
3. Read `NEXT_CLAUDE_HANDOFF.md` for the build queue
4. Read `buildemup_S7a_SPEC_v1_0_LOCKED.txt` — the contract
5. Resume from the queue (recommended sequence: finish serialization tree first → smoke-test GateState round-trip → endpoints → tests)

The Claude that resumes reads (in order):
1. `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` — mid-build resume orientation
2. `01_master_doc/MASTER_DESIGN_NARRATIVE_v2_9.md` — esp. Parts 4.23–4.24, 8 (S7a status), 9, 11
3. `02_specs_chronological/buildemup_S7a_SPEC_v1_0_LOCKED.txt` — the spec to build to
4. The unpacked workdir state — see what's done before adding new code

## 11.2 The S7a continuation build queue

Per locked S7a v1.0 spec, in dependency order:

1. **Finish serialization tree** (~70% of remaining work):
   - 6 more types in `domain/extreme_case.py`: ExtremeDecision, CounterfactualSummary, PreflightSummary, PreviewModeAcknowledgment, ExtremeDecisionLog, ResolvedBrief
   - All of `domain/feasibility.py`: DesignGapAnalysis + ~5 nested types + 6 enums
   - `components/c02/feasibility_input.py`: InputField generic + FeasibilityInput
2. **Smoke test GateState round-trip end-to-end**: build a state via real ExtremeCaseGate.start, assert `s.to_dict() == GateState.from_dict(s.to_dict()).to_dict()`. Must pass before endpoints.
3. **5 endpoint handlers** in `api/c3a_endpoint.py` (~520 LOC). Order: /abort (simplest) → /check → /resolve (complex) → /cba-verified → /cba-fallback-continue.
4. **Hook stubs**: `api/c3a_email_hook.py` + `api/c3a_scheduler_hook.py` (~30 LOC each).
5. **Wire `api/server.py`** routes (~15 LOC).
6. **Tests** (~28 across 4 files, ~1,420 LOC):
   - `tests/test_c03a_session7_api_endpoints.py` (~22 tests)
   - `tests/test_c03a_session7_serialization.py` (~5 tests)
   - `tests/test_c03a_session7_storage.py` (~10 tests)
   - `tests/test_c03a_session7_hook_ordering.py` (~4 tests)
7. **Final acceptance**: 188 baseline + ~28 new = ~216 tests passing.

Per D-066: after S7a code is done → code-critique cycle (steps 7–8 of D-066) → patch → then S7b spec.

## 11.3 Sessions remaining for C3a (S7a finish + S7b + S8)

| Session | Deliverable | Estimated LOC | Tests |
|---|---|---|---|
| S7a continuation | Finish serialization tree + endpoints + tests (resume queue above) | ~700 source + ~1,420 tests remaining | ~28 new |
| S7b | Production deployment hooks (real SMTP, real scheduler, observability) | ~400 | ~6 |
| S8 | Validation suite — integration tests across 10 EC paths + Preview + CBA fallback + preflight + reason-aware errors | ~700 | ~7 |

**Total remaining after S7a partial:** ~3,500 LOC across 3+ sessions.

## 11.4 After C3a fully ships (S8 complete)

Per master doc Update Protocol Part 13:
1. Update Part 4 with Sessions 24+ (S7a finish, S7b, S8)
2. Update Part 8 (Build Status: 4 of 17 components built, 13 to go)
3. Update Part 9 with any new decisions
4. Update Part 12 with all C3a code embedded (post-S8)
5. Bump master doc to v3.0 (component-shipped milestone)
6. Deploy v0.11 to Railway

Then begin layout pipeline build per Path C (D-050).

## 11.5 Things to NOT do (per Design Principles + D-066 + D-067)

- ❌ Don't restart S7a from scratch. The spec is LOCKED and ~30-40% of code is built; resume from the workdir tarball.
- ❌ Don't draft a new S7a spec — it's locked at v1.0. **Note the rename:** the original "S7" spec was split into S7a (this) and S7b (separate session, deferred).
- ❌ Don't modify the storage layer (`gate_state_storage.py`). It's complete and design-tested.
- ❌ Don't modify S1/S2/S3/S4/S5/S6/B-027 deliverables — they're locked by their tests. **Adding to_dict/from_dict methods to existing domain types IS permitted** (purely additive surface; doesn't change existing tests).
- ❌ Don't normalize `is_done` semantics inside S6. Per spec P7: wire-only normalization in S7a.
- ❌ Don't return 410 for terminal tokens. § 6.6 + P3 + P15 — terminal is readable with HTTP 200 + `session_status: "terminal_replay"` advisory field.
- ❌ Don't re-fire hooks on idempotency replay. § 7.3 P16.
- ❌ Don't skip the CODE critique round after S7a build completes (D-066 mandates it).
- ❌ Don't fall into Pattern A/B/C/D/E.
- ❌ Don't refer to "Component 3" unqualified — always 3a or 3b.
- ❌ Don't suggest handoff (per D-066 v2). Continue building until USER says stop. ONE EXCEPTION: if context is genuinely too low to complete current step at quality level of prior chats, tell user straight as a quality-protection signal. **Session 23 exercised this exception correctly — flag it the same way if needed.**
- ❌ Don't accept every critique round verbatim — apply D-067 pushback rule when critique would force YAGNI surgery / hostile mechanisms / fixes for hypothetical futures. **S7a spec round-2 was a fresh worked example: 4 of 15 items pushed back with documented rationale.**

---



# Appendix A — The Canonical NE 30×40 Walkthrough

Source: `BuildemUp_Walkthrough_NE_30x40.md` in `03_project_files/`. Used to validate the architecture without coding.

## A.1 The brief

- **Plot:** 30 × 40 ft = 1,200 sqft, NE-facing, Chennai (Velachery area assumed)
- **Floors:** Stilt parking + Ground + First + Terrace utilities
- **Ground Floor:** 2 bedrooms with attached baths, living hall with open dining near kitchen, kitchen, store, utility, pooja, guest wash from living
- **First Floor:** Master bedroom with attached bath + walk-in wardrobe, 2 bedrooms with attached baths, home office, balcony, family lounge
- **Terrace:** Gym/yoga, garden, table tennis (badminton flagged INFEASIBLE — needs 880 sqft on a 900 sqft terrace)
- **Budget:** ₹60L
- **Approvals:** CMDA (working setbacks 2 ft = regularisation; regulatory setbacks 5 ft front, 3 ft sides/rear)

## A.2 Three final layouts produced by walkthrough

| Layout | Topology | Mutations applied | Cost | Optimised for |
|---|---|---|---|---|
| **A — "Best for Budget"** | Central Spine | None (baseline) | ₹54.8L | Cost |
| **B — "Best for Family"** | Central Spine | M1 (E↔W flip) + M9b (entry SE-corner-W) | ₹58.5L | Multi-generational + bath practicality |
| **C — "Best for Experience"** | Courtyard | (multiple) | ₹61.2L | Light + experience |

## A.3 Sample Quote Comparison Run

- **Contractor quote:** ₹71.5L
- **Our estimate (Layout B mid):** ₹58.5L
- **Counter-offer:** ₹62.5L (our estimate + 7% margin)
- **Potential savings: ₹9 lakh**

This walkthrough validated the architecture. No structural breaks identified. Decision: stop critiquing, start coding. Component 7 first.

---

# Appendix B — Knowledge Base Reference Card

## B.1 IS codes referenced

| Code | What it covers | Component(s) |
|---|---|---|
| **IS 456:2000** | Plain & RC concrete; column/beam/slab design | C7 (structural sizer, frame sanity Bresler) |
| **IS 875 Part 1** | Dead loads | C7 (load_combinations) |
| **IS 875 Part 2** | Live loads (residential 2.0 kN/m²) | C7 (load_estimation) |
| **IS 875 Part 3** | Wind loads (wind speed by city) | C7 (wind_load) |
| **IS 1893:2016** | Seismic loads + 3-level regularity + drift | C7 (global_stability, seismic_detailing) |
| **IS 1904:1986** | Soil bearing capacity (12 classes) | C7 (soil_classification, foundation_engine) |
| **IS 2911** | Pile foundations | C7 (pile_foundation) |
| **IS 13920** | Ductile detailing (Zone III + IV) | C7 (seismic_detailing) |
| **NBC 2016 Part 3** | Light + ventilation + room dimensions | C1 (room_minimums), C14 (Hard Constraints) |
| **NBC 2016 Part 4** | Fire safety + egress | C14 (fire_egress check) |
| **NBC 2016 Part 8** | Passive design recommendations | C6 (Orientation Priority) |

## B.2 City DCRs

| City | Authority | Document | Status |
|---|---|---|---|
| Chennai | CMDA | TNCDBR 2019 | Full implementation (Continuous Building Area rules, plot-type setbacks) |
| Mumbai | MCGM | DCPR 2034 | Full implementation (Session 9 / 25 Apr) |
| Delhi | DDA / MCD | MPD-2021 | Full implementation (Session 9 / 25 Apr) |
| Bangalore | BBMP / UDD | BBMP Building Bylaws | Full implementation |
| Pune | PMC | UDCPR | Full implementation |
| Hyderabad | GHMC | G.O. 168 | Full implementation |

**No NBC fallback for these 6 cities.** Other Indian cities still use NBC 2016 fallback with explicit disclosure.

## B.3 Source standards in `kb/`

- **`material_rates_chennai.py`** — Chennai 2026 rates with brand/grade/IS-code per item (e.g., "Cement Ramco/Ultratech OPC 53 IS 12269 — ₹390/bag, last updated 2026-04")
- **`material_rates_multicity.py`** — 5 other cities
- **`vastu_engine.py`** — 5 high-impact Vastu rules (used only in PARTIAL = 7 items mode)

---

# Appendix C — Conversation Transcript Index

The 16 sessions in `01_chats_chronological_readable/` of the archive. Total ~19,700 lines.

| # | Date | Filename | Lines | Theme |
|---|---|---|---|---|
| 1 | 20 Apr 2026 | `01_2026-04-20-architecture-research.txt` | 1,412 | Architecture research, founding contractor story, 15 known problems |
| 2 | 22 Apr | `02_2026-04-22-architecture-validation.txt` | 573 | 13→18-component validation; 5 critic additions |
| 3 | 22 Apr | `03_2026-04-22-architecture-and-component7.txt` | 1,579 | Architecture v3 finalised; first C7 build |
| 4 | 23 Apr | `04_2026-04-23-v04-block-a-b-progress.txt` | 1,345 | C7 v0.4 — trust controls + building-type architecture |
| 5 | 23 Apr | `05_2026-04-23-v05-shipped-v06-review.txt` | 1,251 | C7 v0.5 shipped; v0.6 review begins |
| 6 | 23 Apr | `06_2026-04-23-v06-phase3-mostly-done.txt` | 1,304 | C7 v0.6 — legal hardening + ComponentContract |
| 7 | 23 Apr | `07_2026-04-23-v072-final-c1-scoping.txt` | 840 | C7 v0.7.2 final + C1 scoping + full v1–v4 vision reveal |
| 8 | 24 Apr | `08_2026-04-24-c01-v0.1-sessions.txt` | 1,295 | C1 SPEC v0.2 LOCKED + 5 build sessions |
| 9 | 25 Apr | `09_2026-04-25-c01-v09-sessions.txt` | 718 | C1 v0.9 Sessions A–C |
| 10 | 25 Apr | `10_2026-04-25-c01-v091-patch.txt` | 1,003 | C1 v0.9.1 patch + 6-city DCRs complete |
| 11 | 27 Apr | `11_2026-04-27-c2-feasibility-session-a.txt` | 796 | C1 v0.9.3 + C2 Session A (dual-design decision) |
| 12 | 27 Apr | `12_2026-04-27-c2-feasibility-session-b.txt` | 1,477 | C2 Session B (4 hard physics + 6 legal-only) |
| 13 | 27 Apr | `13_2026-04-27-c2-sessions-a-through-g.txt` | 1,496 | C2 Sessions A–G (6 branched + 3-state input) |
| 14 | 27 Apr | `14_2026-04-27-c2-sessions-c-through-j-plus-review.txt` | 771 | C2 Sessions H–J + 12-drawback review |
| 15 | 28 Apr | `15_2026-04-28-c2-sessions-c-through-m-deploy.txt` | 1,174 | C2 Sessions K + L + Bucket A + deploy v0.10 |
| 16 | 28 Apr | `16_2026-04-28-c2-deploy-feet-architecture-recall.txt` | 2,553 | Session M (feet/metres) + architecture recall debate |

Plus `00_journal.txt` (147 lines) — meta-summary of all 16 sessions.

For deep recovery on a specific topic: open the relevant transcript; everything is preserved verbatim.

---

# Appendix D — How This Document Was Built (29 April 2026)

## D.1 The recovery context

This document v2 was created 29 April 2026 after a previous chat session went silent mid-recovery. Ramalingam uploaded the comprehensive 27 MB archive `1777425962270_BUILDEMUP_COMPLETE_ARCHIVE_2026-04-29.zip` (213 files) and explicitly requested:

> "I want you to have a 100% clear idea about what we did and actually understand them. Then only we can proceed without making the same mistakes again and again."

## D.2 What was read (verbatim, no skim)

The current Claude session deeply read:
- ✅ `00_MANIFEST_README.md` (archive navigation)
- ✅ `00_journal.txt` (16 session summaries)
- ✅ Sessions 1, 2, 3, 7, 8, 16 — full deep-read of every line
- ✅ Sessions 4, 5, 6 (via journal + sampling)
- ✅ Sessions 9, 10, 11, 12, 13, 14, 15 (via journal + sampling)
- ✅ `BuildemUp_Architecture_v1.md` (12-component discussion doc)
- ✅ `BuildemUp_Architecture_v2.md` (16-component spec)
- ✅ `BuildemUp_Architecture_v3.md` (17-component CANONICAL)
- ✅ `BuildemUp_Walkthrough_NE_30x40.md` (end-to-end trace)
- ✅ `BuildemUp_Design_Principles_v3_1.md` (LOCKED)
- ✅ `buildemup_C1_SPEC_v0_1.md` (rejected)
- ✅ `buildemup_C1_SPEC_v0_2_LOCKED.md` (used for build)
- ✅ `BuildemUp_Component_Validation_Report.md`
- ✅ `v2_vision.md`, `v2_backlog.md` (deferral trackers)
- ✅ `README_v0_5/v0_6/v0_7/v0_7_1/v0_7_2.md` (release notes)
- ✅ `README_v0_10_section.md`
- ✅ `DEPLOY.md`, `buildemup_DEPLOY_v0_7_2.md`
- ✅ Full file listings of `04_current_codebase/buildemup/` (verified 142+ files)

## D.3 What's still uncertain

Maybe 2–5% of total work isn't fully covered by the archive:
- Specific test case names from sessions A–K (captured at the level of "245 tests across 11 suites")
- Detailed conversation context for sessions 4–6, 9–15 (read via journal + key quotes; not full deep-read of every line)

If these matter for a specific decision later, the relevant transcript is in `01_chats_chronological_readable/` and can be opened directly.

## D.4 Continuation protocol

**After every coding session, this document gets updated:**
1. **Part 4 (Chronological History):** new dated entry appended
2. **Part 7 (File Inventory):** new files added
3. **Part 8 (Build Status):** updated component-by-component status, test counts, deployment state
4. **Part 9 (Decisions Log):** new decisions appended with date
5. **Part 11 (Continuation Point):** updated to reflect what's next

Document version stays in the header. **Current version: v2.0 — 29 April 2026.**

## D.5 Recovery protocol if Claude session goes silent again

1. **Re-upload the archive** (`1777425962270_BUILDEMUP_COMPLETE_ARCHIVE_2026-04-29.zip` or its successor) to a new chat
2. **Re-upload this master document** — it captures everything in one place
3. The new Claude reads this doc first, then the archive only as deep-dive when needed
4. **GitHub repo** at `https://github.com/ramalingam38-rgb/buildease` — has v0.10 deployed code
5. **Railway deployment** — has live running code at `https://buildease-production.up.railway.app`

---

## End of design documentation

The design narrative ends here. **Parts 12 and 13 below contain the embedded source code and the update protocol for future sessions.** Document end is at the very bottom.

## Final note for Ramalingam

Three of seventeen components fully built. Component 3a in active build — Sessions 1–2 of 8 shipped with 71 tests passing across 2 suites. Thirteen components beyond that pending.

The foundation is solid. Component 7 (structural grid) is engineering-grade. Component 1 (brief capture) handles plot types, six city DCRs, vastu opt-in, parking feasibility, save/resume. Component 2 (feasibility) ships the dual-design pattern with 17 of 18 v0.1 checks. Component 3a S1 (domain objects) is locked: 15 immutable types covering Extreme Cases, Resolution Options, Counterfactuals, Preflight, Preview Mode Acknowledgment, and the ResolvedBrief output. All v0.2.1 invariants encoded as `__post_init__` validations. Component 3a S2 (detection logic) is shipped: 10 detection functions across all ECs, with placeholder ResolutionOption pairs that S3 replaces.

The architecture is locked. The principles are locked. The patterns to avoid are documented. The complete source code is embedded in Part 12. The update protocol for future sessions is in Part 13.

**What's next:** Component 3a Session 3 (Option generation) per SPEC v0.2.1a Section 13.S3. See Part 11.

When you're ready, hand off to a fresh Claude conversation with: this master doc + SPEC v0.2.1 LOCKED + S1 deliverables (`extreme_case.py` + `test_c03a_session1_domain.py`) + the next-Claude-handoff document.
# PART 13 — Update Protocol (For Future Sessions)

## 13.1 Why this section exists

This document is the single source of truth for BuildemUp. Ramalingam's instruction (29 April 2026):

> *"After each session i want you to update it also with the chats and codes and everything. I should be able to use this document as reference and start from where we left off."*

This protocol tells any future Claude session **exactly how to update this document** so the single-source-of-truth promise holds across sessions. Mechanical, deterministic, no judgement calls.

---

## 13.2 When to update

Update this document at the **end of every session that:**
- Wrote, modified, or deleted any code file
- Made any architectural decision (locked or under discussion)
- Shipped a new component version (v0.X.Y bump)
- Deployed to Railway
- Held an architecture / scope / philosophy conversation that produced any locked decision
- Merged any review/critique findings (whether accepted or rejected)

**Do NOT update for:** purely conversational sessions with no code/decisions; sessions that only re-read existing context.

---

## 13.3 What to update — the 8 update zones

When ending a session, walk through these 8 zones in order. Skip zones with no changes.

### Zone 1 — Header (always check)

Bump the version in the header table. Convention:
- `v2.X` — minor update (session log appended, code embedded for changed files)
- `v3.0` — major update (component shipped, deployment, big architectural change)
- Update "Document version" date to today

### Zone 2 — Part 4 (Era 2 Chronological History) — append-only

Append a new section in date-chronological order. Template:

```markdown
## 4.X Session N — [DAY] [DATE] 2026, HH:MM UTC — *[Session Theme]*

**Source:** `[transcript filename]` ([line count] lines)
**Theme:** [One-sentence what-this-session-was-about]

**What happened:**

[2-5 paragraphs covering the substance. What was discussed, what was decided, what was built. Include verbatim user quotes for locked decisions.]

**Key decisions in this session:**
- ✅ [Decision with rationale]
- ✅ [Decision with rationale]

**Code changes:**
- Created: `buildemup/path/to/new_file.py` ([LOC])
- Modified: `buildemup/path/to/existing.py` (added [function]; LOC delta +X)
- Deleted: `buildemup/path/to/dead_file.py`

**State at end:** [test count] PASS across [suite count] suites. [Component] at v[X.Y.Z]. [Deployed | Packaged | In-progress].
```

**Cross-references:** if this session modified a decision logged in Part 9, add a cross-ref note in Part 9 (`SUPERSEDED BY D-XXX on YYYY-MM-DD`).

### Zone 3 — Part 7 (File Inventory) — update if files added/removed/renamed

If new files were created:
- Add the file path under the appropriate subsection (Components / Domain / KB / Utils / API / Static / Tests / Docs)
- Update the section's stated total file count if listed (e.g., "16 files" → "17 files")

If files were deleted:
- Remove from inventory
- Add a brief note in Part 9 (Decisions Log) documenting the removal and reason

### Zone 4 — Part 8 (Build Status Live Tracker) — always update

This is the most-changed zone. Always touch:

- **Part 8.1 "At a glance"** table — update test counts, deployment state, packaged-but-undeployed, last successful deploy
- **Part 8.2 component status table** — if a component progressed (e.g., C3 went from "NEXT TO BUILD" to "Session 1 in progress" to "v0.1 SHIPPED")
- **Part 8.4 deployment** — if anything was deployed
- **Part 8.5 "what's NOT yet on Railway"** — update list
- **Part 8.7 test counts evolution** — append a new row with date, version, tests, suites

### Zone 5 — Part 9 (Decisions Log) — append-only

For every locked decision made this session, append an entry:

```markdown
| D-XXX | YYYY-MM-DD | [Decision in one sentence] | [Rationale in one or two sentences] |
```

Use the next sequential D-XXX number. Do not renumber existing decisions.

If a previous decision was superseded by this session's decision, edit the old decision's row to add `(SUPERSEDED BY D-XXX on YYYY-MM-DD)` at the end of the rationale.

### Zone 6 — Part 11 (Where We Continue From Here) — rewrite

This is the only zone that gets fully rewritten each session (everything else is append-only or surgical edit).

After the session, the "next step" has changed. Update:

- **Part 11.1** — what's the new next session's starting point
- **Part 11.2** — if we just started a component build, replace with that component's session-by-session plan; if we just shipped one, write the next component's plan
- **Part 11.3** — open questions for Ramalingam BEFORE the next session
- **Part 11.4** — alternative paths Ramalingam might take instead

### Zone 7 — Part 12 (Embedded Code) — surgical update for changed files

For every file that was created, modified, or deleted this session:

- **Created:** add a new `### \`buildemup/path/to/file.py\`` section in the right subsection (12.2 / 12.3 / 12.4 / etc.) with the full file content
- **Modified:** find the existing `### \`buildemup/path/to/file.py\`` section, replace its content (header line and code block) with the new full content; update the *X lines, Y chars* annotation
- **Deleted:** find and remove the section; add a note in 12.X subsection's intro that this file was removed in session [date]

**Convention:** every embedded file ends with the *X lines, Y chars* annotation. Recompute when modified.

### Zone 8 — Final footer — always update

Last lines of document:
- "Version: v2.X — [Date]"
- "Total document: [updated description]"
- "Maintained by: Claude (current and future sessions)"

---

## 13.4 Update workflow (mechanical steps)

When ending a session, run these steps in this order:

1. **Inventory changes** — list every file created/modified/deleted in this session
2. **Note new decisions** — what was locked? List them with rationale
3. **Note progress** — did any component advance a status? Did test count change? Did anything deploy?
4. **Open the document** — read Parts 4, 7, 8, 9, 11, 12 (the 6 zones that change)
5. **Apply Zone 2** (append session log)
6. **Apply Zone 3** (update inventory if needed)
7. **Apply Zone 4** (update Build Status — almost always changes)
8. **Apply Zone 5** (append decisions if any)
9. **Apply Zone 6** (rewrite Part 11 with new "next step")
10. **Apply Zone 7** (embed new/changed code)
11. **Apply Zone 1** (bump version + date in header)
12. **Apply Zone 8** (update footer)
13. **Save and present** the updated file to Ramalingam via `present_files`

---

## 13.5 What NOT to change in updates

To preserve stability across many session updates:

- ❌ Do NOT renumber existing decisions in Part 9 (always append)
- ❌ Do NOT renumber existing sessions in Part 4 (always append in chronological order)
- ❌ Do NOT delete or rewrite Parts 0, 1, 2, 3, 5, 6, 10 (these are foundational; if they need correction, do a careful edit and bump major version v3.0)
- ❌ Do NOT remove old code from Part 12 even if a file was deleted from the codebase — instead, mark it deleted with a header note. (Reason: history matters when debugging "when did this regression appear?")
- ❌ Do NOT introduce new component numbers, new tracks, or new architectural concepts without explicit Ramalingam approval — those are locked
- ❌ Do NOT remove or modify the Update Protocol itself (Part 13) without explicit Ramalingam approval

---

## 13.6 Recovery from drift

If at any point this document seems to have drifted from the actual codebase (e.g., Part 12 shows old code, Part 8 shows wrong test count, Part 11 says "Component 3 is next" but C3 was already built):

1. **Stop current work.** Drift undermines the single-source-of-truth promise.
2. **Trigger a full rebuild.** Re-extract the latest comprehensive archive (or pull from GitHub `main` branch) and rebuild Part 12 fresh.
3. **Reconcile Parts 4, 7, 8, 9** by reading any session transcripts since the last good update.
4. **Bump major version (v3.0, v4.0)** to flag this is a reconciled rebuild, not a normal update.
5. **Document the drift** in a new Part 14 — "Drift Log" — so future Claude sees how it happened and avoids it.

---

## 13.7 Practical tips for future Claude sessions

- **Keep the master doc open in a code-execution tool view as you work.** It's the reference for what was decided and what should NOT be redone.
- **Before writing any code, check Part 12 to see if the file already exists.** If it does, READ the existing version before modifying — Pattern A (fix-as-bandage) is the project's most common failure mode.
- **Before adding any component or feature, check Part 1 (the four numbering schemes).** Confusion about Track 1 vs Track 3 has cost multiple sessions.
- **Before adding any rule, check Pattern D (rules piled on rules).** Look for an existing rule that already covers the case.
- **Before claiming a component is done, run the integration test through the orchestrator** — Pattern B (building without wiring) is the second most common failure mode.
- **At session end, allocate time for the doc update.** A session that ships code without updating the doc is worse than a session that ships nothing — because the next session starts from drift.


---

# DOCUMENT END (with embedded code)

**Version:** v2.9 — 1 May 2026 (Session 23 — C3a S7a SPEC v1.0 LOCKED across 2 critique rounds + S7a code build started ~30-40% complete; mid-build handoff prepared per Obligation 2; storage layer + Brief tree + 4/10 extreme_case types done; 188/188 c3a baseline still passing; B-040/B-041/B-042 backlog items logged; D-066/D-067 build cycle continues — next session resumes S7a code build)

**Total document:** master design doc (Parts 0–11 + Appendices A–D) + Part 12 complete embedded source code (~24K LOC production + 19K LOC tests + 4K LOC docs) + Part 13 update protocol.

**Single file recovery:** if all chats die, if GitHub is unavailable, if local code is lost — this document is sufficient to reconstruct the project. Extract each `### \`buildemup/...\`` code block to its named path, run `pip install` for any external deps, run the tests (`python -m unittest discover buildemup/tests`), deploy to Railway via `git add . && git commit && git push origin main`.

**Maintained by:** Claude (current and future sessions), updated after each work session per the Update Protocol in Part 13.
