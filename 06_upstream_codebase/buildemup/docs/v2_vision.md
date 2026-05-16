# BuildemUp† — v2 Vision Document

**Purpose:** For every item we deferred from v1, this document captures
what "best in market" looks like when we actually build it. The v2
backlog tracks **what + when**. This document tracks **why it matters
competitively**.

This is not a prioritisation list. It's a competitive narrative document
for fundraising, hiring, and partnership conversations: *"here's where
we'll lead the market when these features land."*

---

## Reading guide

Each section follows this format:

- **What current tools do** — the existing market state
- **What v1 BuildEase does** — our shipped scope today (deliberately limited)
- **What v2 BuildEase will do** — the best-in-market vision
- **Why it matters competitively** — the moat this creates

---

## 1. Structural design depth

### What current tools do
Autodesk Revit / ETABS / STAAD do full structural design but require a
licensed structural engineer to operate. Time per project: 1-2 weeks.
Cost per project: ₹20-40K engineer fees. Inaccessible to general public.

Online "free" calculators exist but produce single-number outputs with
no explanation, no code citations, no sensitivity analysis. Not safe
for actual decisions.

### What v1 BuildEase does
Preliminary structural design per IS 456 + IS 13920 + IS 875:
- Column sizing, beam depth, slab thickness
- Foundation type selection (5 types: isolated/combined/strap/raft/pile)
- Wind + seismic load comparison
- IS 13920 ductile detailing for Zone III+
- Sensitivity analysis on cost AND structural inputs

Explicitly does NOT do: P-M interaction diagrams, frame analysis, beam
moment calculation, serviceability checks. These remain the structural
engineer's job at detailed design.

### What v2 BuildEase will do — best in market
**Full structural analysis engine integrated with the AI brain:**
- P-M interaction curves auto-generated for actual reinforcement layout
- Frame analysis with stiffness matrix (validates our preliminary sizing)
- Beam moment + shear envelope calculation
- Serviceability checks (deflection limits, crack width per IS 456 cl. 43)
- Time-based effects: creep, shrinkage, long-term deflection
- Pile group settlement interaction
- Differential settlement modeling for expansive soils

**Why it matters competitively:** This collapses the "preliminary →
detailed design" gap that currently requires a 1-2 week engineer
engagement. With v2, the engineer can review BuildEase's output rather
than starting from scratch — saving them 60% of their time and the user
50% of the fee. Engineer becomes our distribution channel, not our
competition.

---

## 2. Lateral analysis & seismic rigor

### What current tools do
Free tools: nothing. Paid tools (ETABS): full dynamic analysis but
requires expert operator + 1-2 weeks per project.

Most preliminary residential designs in India skip lateral analysis
entirely (relying on IS 1893 cl. 7.10.3 exemption for brick infill).
This is technically code-compliant but a gap in real-world safety.

### What v1 BuildEase does
- Static seismic analysis per IS 1893 simplified method
- Three-level regularity classification (REGULAR/MODERATE/SEVERE)
- Severe-irregularity refusal (engine declines without engineer review)
- SCWB heuristic clearly labeled as heuristic, not real moment check
- Wind vs seismic governing load comparison

### What v2 BuildEase will do — best in market
**Dynamic analysis embedded in the layout engine:**
- Modal analysis with first three vibration modes
- Response spectrum analysis per IS 1893 cl. 7.8
- Time-history analysis for severely irregular plans
- Torsional amplification calculation per IS 1893 cl. 7.9
- Real SCWB compliance with moment capacity calculation

**Why it matters competitively:** Today, irregular plans (L-shape, U-shape,
courtyards — common in Indian homes) effectively can't be costed
accurately by anyone except a structural engineer. v2 BuildEase will
cost them in 60 seconds. This unlocks the 30-40% of projects that have
non-rectangular geometry — currently underserved by every tool.

---

## 3. Foundation engineering

### What current tools do
Soil reports cost ₹15-25K and take 2 weeks. Foundation type selection
typically requires ground-truth soil test data first.

Pile foundations are designed manually by geotechnical engineers
(₹40-80K extra fee). 3D printed foundations don't exist yet.

### What v1 BuildEase does
- 5 foundation types automatically selected based on soil + load + plan
- City-specific soil profiles (7 cities)
- Pile capacity from IS 2911 catalog (preliminary sizing)
- Strap footing for property-line edge conditions
- Mumbai BMC permit warning, area-specific (Velachery marshy, etc.)

### What v2 BuildEase will do — best in market
**Geotechnical AI advisor:**
- Pile group settlement interaction with soil-structure modeling
- Skin friction vs end bearing breakdown using per-strata soil data
- Settlement differential prediction (expansive soils, layered soils)
- Integration with drone surveys (Phase 2 vision) for actual site soil
  scanning before foundation design
- Liquefaction susceptibility for coastal/reclaimed sites

**Why it matters competitively:** When Phase 2 drones provide actual
soil data, our foundation engine becomes the first geotechnical advisor
that doesn't require a $500/hour consultant. Banks underwriting home
loans will trust our foundation cost estimate more than a generic
20%-of-construction guess.

---

## 4. Cost transparency depth

### What current tools do
Contractor: bundled quote ("₹85 lakhs total — take it or leave it").
Architect: rough per-sqft estimate. Online calculators: single number
with no methodology.

### What v1 BuildEase does
- Itemised cost breakdown by category (structural, masonry, finish, etc.)
- Brand/grade/IS-code annotations (cement = "Ramco or Ultratech OPC 53")
- Rate sources cited per material
- Sensitivity analysis: top 3 cost drivers + ±impact
- Confidence levels (HIGH/MEDIUM/LOW) explained inline

### What v2 BuildEase will do — best in market
**Bill-of-materials with live supplier integration:**
- Real-time rates from Ultratech / JSW / ACC partner APIs
- Brand selection based on user budget tier (economy/standard/premium/luxury)
- Volume discounts surfaced (e.g., "If you order 480 bags, ₹15K savings")
- Multi-quote comparison (3 supplier quotes side-by-side)
- Construction-week-level cash flow projection
- Monte Carlo cost simulation (95% confidence interval, not point estimate)

**Why it matters competitively:** Per the vision doc, contractor
overhead + profit on a ₹25L job = ₹6.28L. v2 BuildEase shows users
this BEFORE they sign anything. The supplier integration converts our
estimate into actual orders — turning BuildEase into the procurement
layer, not just the planning layer.

---

## 5. Knowledge base scale

### What current tools do
Most tools embed 1-2 codes in proprietary code. Updates lag the actual
codes by 3-5 years. No traceability of which version of which code
produced a given output.

### What v1 BuildEase does
- 8 modules covering IS 456, IS 875 (Parts 1, 2, 3), IS 1893, IS 13920,
  IS 2911, soil profiles, material rates
- KB version pinned per output for reproducibility
- LAST_UPDATED timestamps per module
- Trace ID per output to debug discrepancies

### What v2 BuildEase will do — best in market
**Living knowledge base of 100+ books + codes** (per vision doc slide 4):
- Book-to-code pipeline automated via Gemini API
- Quarterly refresh of all material rates + state PWD schedules
- NBC 2016 fully encoded (all 12 parts)
- All city municipal bylaws (FAR, setback, height) auto-updated
- Vastu Shastra texts (Manasara, Mayamata) — opt-in compliance check
- ECBC 2017 (energy code) for commercial buildings
- Audit log for every rule change (which code update triggered it)

**Why it matters competitively:** No competitor maintains a fresh
knowledge base at this scale. Once BuildEase has 100+ codes encoded
with quarterly refresh, the data moat is decade-deep. New entrants
would need 3+ years to replicate.

---

## 6. Building type coverage

### What current tools do
Most Indian floor plan tools target either residential OR commercial,
rarely both. Mixed-use, healthcare, educational require custom design.

### What v1 BuildEase does
- Fully implemented: residential single-family
- Architecturally supported: 8 types (residential single+multi-family,
  commercial office, retail, mixed-use, educational, healthcare,
  hospitality)
- Industrial / warehouse explicitly excluded (out of scope)
- Per-type importance factor (educational/healthcare = 1.5×)
- Per-type IS 13920 mandate (important buildings always ductile)
- Stubbed types refused gracefully with helpful message

### What v2 BuildEase will do — best in market
**Full multi-building-type platform:**
- All 8 architecturally-supported types fully implemented
- Per-type live load library (IS 875 Part 2 complete)
- Per-type fire safety rules (NBC 2016 Part 4 fully)
- ECBC 2017 for commercial buildings (energy efficiency)
- Multi-use floor logic for mixed-use (commercial below, residential above)
- Healthcare-specific MEP (medical gas, isolation rooms, lift specs)
- Educational-specific safety (corridor widths per NBC Part 9)

**Why it matters competitively:** A single platform that handles every
non-industrial building type from 600-sqft house to 30-room school is
unprecedented in India. This unlocks SMB/institutional segments
(schools, clinics, small hotels, mixed-use) that currently can't get
quick estimates anywhere.

---

## 7. Decision-support intelligence

### What current tools do
Calculators give numbers. Architects give opinions. Neither explains
the trade-offs in a way that lets a non-expert family make confident
decisions.

### What v1 BuildEase does
- Sensitivity analysis: "if X changes by Y%, cost changes by Z"
- Structural sensitivity: "if soil tests weaker, foundation upgrades to X"
- Confidence levels with explanations
- "What we check / What we don't check" explicit boundary
- Reproducibility footer (KB versions + trace ID)

### What v2 BuildEase will do — best in market
**Conversational AI advisor backed by the engine:**
- Plain-language Q&A: "Why is my Mumbai estimate higher than my
  cousin's Bangalore one?" → "Mumbai uses pile foundation due to
  reclaimed soil, plus 1.35× material multiplier, plus IS 13920 steel
  uplift. Detailed comparison: ..."
- "What if" multi-scenario analysis: "Show me 3 layouts ranging from
  cost-optimal to premium-finish"
- Trade-off visualization: cost vs comfort vs Vastu compliance, on one
  chart
- Personalised contractor questions: "Here are 12 specific questions
  to ask your contractor about steel, given your design uses Fe500D"

**Why it matters competitively:** This is the asymmetry the original
BuildEase vision was built to close — emotional asymmetry vs the
decision itself. A conversational advisor that knows IS code AND
understands the family's tradeoffs is something no current tool offers.

---

## 8. Phase 2 — Machine integration

### What current tools do
Manual construction. Drawings handed to contractor, who interprets
them. Errors and rework are routine.

### What v1 BuildEase does
Nothing in Phase 2 territory yet. v1 stops at: blueprint + cost +
plain-language advice.

### What v2 BuildEase will do — best in market (Year 2-5 per vision doc)

**Drone surveys → BuildEase Digital Twin:**
- 30-minute drone scan replaces 2-day survey
- Automatic site topography + boundary verification
- Existing structure detection (for renovations)

**3D concrete printing integration:**
- BuildEase design → printer instructions directly (no manual conversion)
- Wall geometries optimised for printability
- Material list scoped for printer-compatible mixes

**Robotic execution:**
- Brick-laying robots: 1000 bricks/hour vs 500/day manual
- Rebar fixing robots: 10× faster than manual
- Daily drone monitoring vs random spot-checks

**Why it matters competitively:** Per the vision doc, this is the
65%-faster, 40%-cheaper outcome. v2 BuildEase isn't just a planning
tool — it becomes the operating system for automated construction in
India. This is the moat that takes 5-10 years for any competitor to
replicate.

---

## 9. Internationalisation

### What current tools do
Mostly English-only. A few have Hindi support. None handle the 22
official Indian languages.

### What v1 BuildEase does
English-only output. i18n string-key architecture is in place but no
translations done yet.

### What v2 BuildEase will do — best in market
- Hindi (Phase 1 month 4-5 per vision doc)
- Tamil, Telugu, Kannada, Marathi, Bengali (Phase 1 stretch)
- All 22 official languages by Phase 2
- Voice input/output for low-literacy users (especially rural)

**Why it matters competitively:** 60%+ of the target market is more
comfortable in their native language than English. Any competitor that
ships English-only ceiling-caps at the top 30%.

---

## 10. Mobile-first product

### What current tools do
Desktop-only or mobile-as-afterthought. Architect deliverables are
print-formatted PDFs that don't read on phones.

### What v1 BuildEase does
Engine outputs structured data; presentation layer is currently
desktop-formatted text. Mobile UI deferred.

### What v2 BuildEase will do — best in market
- React Native app (iOS + Android)
- Native swipe-through floor plans
- Pinch-zoom 3D model
- Offline mode for site walkthroughs
- AR overlay (point camera at plot, see virtual house)

**Why it matters competitively:** Most Indian families use mobile-first.
Competitors stuck in desktop-formatted PDFs are invisible to the
audience that needs them most.

---

## How we use this document

**Fundraising conversations:** "Here's where v1 stops, here's where v2
takes us. Each item has a clear path from where we are to where we'll
be."

**Hiring conversations:** "If you join, here's what you'll get to build
that no one else in India is building."

**Partnership conversations:** "If you integrate now, here's the platform
you'll be on top of by year 3."

**Internal scope discipline:** When we're tempted to scope-creep into
v2 work during v1, we point at this document and say "no, that's v2,
here's why v1 ships without it."

---

## Linked documents

- `docs/v2_backlog.md` — what + when (the planning view)
- `book_to_code/README.md` — how the knowledge base scales
- `contracts/` — how v1 outputs feed v2 platform integrations

---

†= placeholder name marker (current codebase says "BuildemUp†"; will
become "BuildEase" once trademark/domain is locked).
