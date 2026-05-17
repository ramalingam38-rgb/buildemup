# 04 — Scope of Review

**Use:** This document defines what the architect WILL do and what they will NOT do. Send to selected architect AFTER engagement letter is signed; reference in the engagement letter itself by short paragraph.

---

## IN SCOPE

The architect will review the BuildEase / BuildemUp v1.0 candidate ruleset across these 7 spec layers:

### Layer 1 — Site-level rules (C1 brief capture, C2 feasibility, C4 plot analysis)

Specifically:
- **Setback rules** for residential plots in Tamil Nadu (TNCDBR), with secondary check against NBC 2016 Part 3 minimums.
- **FAR (Floor Area Ratio)** rules — base FAR, premium FAR mechanism, OFAR (Other FAR) where applicable.
- **Plot coverage** rules — maximum permitted ground coverage for residential.
- **Soil-class defaults** by city (Chennai, Bangalore, Mumbai, Hyderabad, Pune, Delhi-NCR, Kolkata, Ahmedabad, Pune, Jaipur).
- **Bearing capacity (SBC)** by soil class, particularly MEDIUM_ROCK = 1250 kPa (IS 6403), STIFF_CLAY values, BLACK_COTTON treatment depth.

### Layer 2 — Programming rules (C3a extreme-case detection, C3b negotiation)

Specifically:
- **Room count / floor count** plausibility for given plot + budget.
- **Budget envelope** sufficiency given declared room count and city construction rates.
- **Override mechanism** semantics — under what conditions an explicit homeowner override should pass past a feasibility hard-fail.

### Layer 3 — Layout rules (C5 topology, C6 orientation, C7 structural grid, C9 room sizer)

Specifically:
- **Topology** — how rooms are connected; basic adjacency expectations.
- **Orientation** — primary façade / approach direction relative to plot road frontage.
- **Structural grid** — typical column spacing, beam depths, IS 13920 stub-column rules for ductile detailing (Zone III/IV currently; Zone V is v2-deferred).
- **Staircase** — IS / NBC minimum landing depth, tread/riser ratios, location heuristics (centre vs side).
- **Room minimums** — habitable rooms, bathrooms, kitchens, utility per NBC Part 3.

### Layer 4 — Circulation rules (C8 corridor designer)

Specifically:
- **Corridor minimum width** — NBC 2016 Part 3 single-dwelling default of 0.9m, with NBC Part 4 fire-egress override for longer corridors / multi-unit.
- **CorridorTooNarrow** error semantics and graceful fallback behavior.

### Layer 5 — Wet-zone rules (C10 wet zones, includes B-220 hydraulics depth as separate engagement)

Specifically:
- **DFU (Drainage Fixture Unit)** loading assumptions per NBC Part 9 / IS 1742.
- **Wet-zone stack location** rules.
- **Rainwater harvesting** mandate per TNCDBR rule 7 (plot size threshold).
- **Sewage and septic** rules per TNCDBR rule 8/9.

### Layer 6 — Topology-mutation + door rules (C11a, C11b, C13)

Specifically:
- **Layout overrides** — when a homeowner explicitly says "I want this room here" against the optimizer's preference.
- **Door placements** — privacy gradient logic, window-avoidance, transit-bedroom definition.

### Layer 7 — Compliance + drawings (C15 problem finder, C16 dual drawings, C17 quote comparator)

Specifically:
- **Severity rule table** (35 entries) — categorization of violations as HARD_FAIL / SOFT_WARNING / INFO.
- **Check registry** (35 entries) — what each compliance check actually measures.
- **Cultural profile** — 3 v1 variants (default, Vastu-suppress, Vastu-elevate).
- **Drawing standards** — IS 962:1967 typography/sheet/pen-weight conformance.
- **Compliance provenance format** — how each compliance claim links back to its authoritative source (NBC clause, TNCDBR rule, etc.).
- **Quote comparison** — rate-sanity envelopes, arithmetic-mismatch detection, semantic-match domain ontology.

---

## OUT OF SCOPE

The architect will NOT be asked to:

- Validate any specific drawing or plan for a specific real plot. (We can include 1-2 example plans in the briefing pack for context, but the review is of the SYSTEM, not a specific output.)
- Re-derive or originate new architectural design philosophy. (We have a 17-component spec; architect's job is to validate/refine it.)
- Provide structural calculation verification. (Separate B-220-adjacent engagement.)
- Provide hydraulic calculation verification. (Separate B-220 engagement with plumbing engineer.)
- Engage with the software code itself. (Architects don't read Python; the review is at the spec level, not the implementation.)
- Sign any legal certification of the product. (Architect's name attached to product-release / commercial use is NOT part of this engagement.)
- Provide post-deployment liability. (The review is advisory, not a professional certification. This is clarified in the engagement letter explicitly.)

---

## DELIVERABLE

A 2-4 page written summary (in English) organized as follows:

1. **Top-line findings** — 5-10 bullets prioritizing what should change before v1 release.
2. **By-component findings** — section per component (C1 / C2 / C3a-b / C4 / C5 / C6 / C7 / C8 / C9 / C10 / C11a-b / C12 / C13 / C14 / C15 / C16 / C17), each with structured points: [clause/rule under review] → [issue identified] → [recommended change] → [reference/citation if any].
3. **Open questions** — things the architect couldn't decide without more information.
4. **General observations** — anything systemic that doesn't fit a specific component.

The structured review-question template in `07_review_question_template.md` provides a scaffold the architect can fill in if helpful — but if the architect prefers a free-form deliverable, that's fine too, as long as the same content is covered.

---

## TIME ESTIMATE

| Activity | Time |
|---|---|
| Read briefing pack (10 documents, ~80 pages total) | 4-5 hours |
| Fill in review-question template OR write equivalent | 2-3 hours |
| Mid-review clarification call (optional) | 1 hour |
| Polish and finalize written deliverable | 1 hour |
| End-engagement debrief call (optional) | 1 hour |
| **Total** | **6-10 hours, spread over 2-3 weeks** |

---

## SUCCESS DEFINITION

The engagement is successful when:
- The architect has identified 5-15 specific items that need refinement before v1 release. Higher counts (15-30) are also valuable — better to surface issues now.
- Each finding maps to at least one specific component / spec / rule, so it can be filed as a backlog item by Claude after the review.
- The architect feels comfortable putting their name on the engagement (i.e., the engagement was professionally conducted) even if not on the product.
- Ramalingam has enough clarity afterward to either (a) close v1 with confidence or (b) defer release until specific items are addressed.

If after review, the architect concludes "this product should not ship in current form," that's also a successful engagement — better to know before users do.
