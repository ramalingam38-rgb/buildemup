# Orientation Note for the Reviewing Architect

**Welcome.** This 2-page note prepares you for the review engagement before the rest of the briefing pack arrives.

---

## What you're reviewing

A software system that produces architectural design decisions for Indian single-family residential homes. The system is named **BuildEase** (placeholder name; final TBD). It is at the v1.0 release-candidate stage.

**You are not reviewing a building.** You are reviewing the LOGIC that produces buildings — rules, formulas, defaults, decision frameworks. The deliverable from you is a written critique of those rules: where they are right, where they are wrong, where they are too rigid, where they are too loose, where they miss something obvious.

**You are not reviewing the software code.** You will not be shown Python. You will be shown specification documents — markdown text, mostly diagrams in words with the occasional table. These specs describe the architectural reasoning that the software encodes.

---

## What the system does (one paragraph)

A homeowner — typically a non-architect, non-engineer Indian family — enters their plot details (size, city, soil, road frontage), their family composition (rooms, floors, family members), and their budget. The system produces:

1. A feasibility report: "Can you build what you want, where you want, for the money you have?"
2. A negotiation interface for the impossible cases: "Your budget supports 3 bedrooms, you wanted 4 — here are the trade-offs."
3. A plot analysis: setbacks, FAR, soil-corrected foundation depths, plot coverage.
4. A topology: which rooms connect to which.
5. An orientation: which façade faces the road.
6. A structural grid: where columns go.
7. A corridor: how to move between rooms.
8. Room sizes, all minimums respected.
9. Wet-zone placements: kitchens, bathrooms, utility.
10. Topology mutations: alternative layouts the family can pick from.
11. Vertical alignment: G+1 stacking, staircase placement.
12. Door placements.
13. A connection graph: who is adjacent to whom.
14. A problem-finder: things that violate compliance or convention.
15. Two output drawings: a working drawing for construction reference, and a permit drawing for plan submission.
16. A quote comparator: when the family receives contractor quotes, this checks them against canonical rates per city.

That's 17 components. Each is locked at a v1.0 (or v0.9 / v0.2 / v1.1) specification. The combined system is currently at the spec-frozen, code-implemented, test-green stage. **What we need is your eyes on the SPECS.**

---

## What kind of homes

- **Plot size:** typically 1500-2400 sq ft. Smallest supported: 1200 sq ft. Largest: 4500 sq ft. Above 4500 routes to v2 scope.
- **Construction:** G+1 (ground + first) is the primary target. Ground-only and G+2 are supported but secondary.
- **Family unit:** single-family residential, owner-occupied. Not rentals, not commercial, not high-rise.
- **Cities:** Chennai (primary), Bangalore, Mumbai, Pune, Hyderabad, Kolkata, Ahmedabad, Delhi-NCR, Jaipur, plus a default for "other Indian city."
- **Soil scenarios:** clay (soft / stiff / black cotton), sand, rock (soft / medium / hard), residual / lateritic.
- **Regulatory:** TNCDBR (primary), NBC 2016 (national overlay), local body byelaws (mentioned but not deeply integrated).

---

## Why this product exists (the soul statement)

The founder (Ramalingam) built his own home as a non-architect homeowner. The experience surfaced a structural problem: contractors, architects, and engineers in India bundle their fees, materials, labour, and margins into a single number presented to the homeowner. The homeowner cannot see what they are paying for. Information asymmetry between the professional service provider and the homeowner is the largest cost driver in residential self-build, often larger than material price inflation.

**BuildEase exists to break that bundle apart.** Materials, engineer fees, contractor margin, labour, and timeline are surfaced separately. Compliance decisions are made transparently. Design trade-offs are made visible.

**The reason this review matters:** if the system itself encodes the same opaqueness that the founder is trying to fix — if the rules are hidden, the defaults are guesses, or the framing assumes the homeowner can't handle complexity — the product fails its soul.

**Push back hard on anything that smells of that.** Your dissent is more useful to us than your endorsement.

---

## What we want from you

A 2-4 page written summary, structured as:

1. **Top-line findings** — 5-10 priority points
2. **By-component findings** — specific clauses you disagree with
3. **Open questions** — things you couldn't decide without more info
4. **General observations**

You can write this in your own voice. If you prefer a structured template, one is provided in `Review_Question_Template.md` (in the specs zip). Either is fine.

Time estimate: 4-5 hours of reading + 2-3 hours of writing. Plus optional mid-review call (1 hour) and end debrief (1 hour). 6-10 hours total spread over 2-3 weeks.

---

## What we DON'T want

- **Don't redesign anything.** We have specs that have settled over 50+ work sessions. We need critique, not reorigination.
- **Don't validate everything as fine to ship without comment.** If you can't find anything to push back on, that's a signal we picked the wrong reviewer — not that the system is perfect.
- **Don't hold back because the founder is non-architect.** He'll receive your full feedback through Claude (the software collaborator), be briefed on each point, and decide what to act on. Bluntness saves time.

---

## Questions to ask before starting

If anything in the briefing pack is unclear, ask. The founder + Claude can answer follow-ups in real time. There is no "stupid question" — your time matters more than ours.

Welcome to the review.
