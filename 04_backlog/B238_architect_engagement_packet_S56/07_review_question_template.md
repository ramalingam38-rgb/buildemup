# 07 — Review Question Template

**For the reviewing architect.** You may either fill this in as your deliverable, OR ignore it and write free-form — whichever serves your judgment better. The questions are scaffolding, not a constraint.

**Format:** For each question, answer in one of four ways:
- **AGREE** — current behavior is correct as specified.
- **DISAGREE → recommend X** — current behavior is wrong; here's what it should be.
- **REFINE → adjust Y** — current behavior is correct in spirit but the specific value / formula / framing needs a specific adjustment.
- **UNSURE → need more info** — you can't decide without additional context (please specify what context you'd need).

For DISAGREE / REFINE answers, please cite the authority (NBC clause, TNCDBR rule, IS standard, your professional experience, etc.).

---

## Section A — Site-level rules (C1, C2, C4)

### A.1 — Setback defaults

For a typical 1500-2400 sq ft residential plot in Chennai, the current system applies these setbacks:
- **Front:** plot frontage dependent (typically 1.5m for small plots, 3m for larger)
- **Rear:** 1.0-1.5m
- **Side (L):** typically 0.6m for small plots
- **Side (R):** typically 0.6m for small plots (recent fix in S54 — was bugged to 0.0m)

**Q1:** Are these defaults aligned with current TNCDBR rule for residential plot size ≤ 2400 sq ft?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q2:** Should the side setback differ between L and R based on adjoining plot context (corner plot, abutting plot, road-facing flank)? Currently the system treats L and R symmetrically.
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q3:** When the plot exceeds 2400 sq ft, the setback rule scales to larger values. Have we caught the right plot-size thresholds for TNCDBR's tiered setback table?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### A.2 — FAR (Floor Area Ratio)

Current system applies base FAR of 1.5 for residential plots within Chennai Metropolitan Area (CMDA jurisdiction). Premium FAR mechanism allows up to 2.0 with TNCDBR-specified premium fee.

**Q4:** Is base FAR of 1.5 currently correct for CMDA residential plots ≤ 2400 sq ft?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q5:** Does the premium FAR mechanism (homeowner pays premium to exceed base FAR) actually exist for residential single-family plots in current TNCDBR? Or is premium FAR only available for commercial / mixed-use?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### A.3 — Soil defaults by city

The system has default soil class per city. Specifically:
- Chennai: STIFF_CLAY default (with locally-specified overrides)
- Bangalore: RESIDUAL_LATERITIC default
- Mumbai: COASTAL_FILL default
- Pune: STIFF_CLAY default (murrum) — recent change; user previously expected BLACK_COTTON
- Delhi-NCR: ALLUVIAL_CLAY default
- Hyderabad: WEATHERED_ROCK default

**Q6:** Are these city defaults reasonable starting points? Specifically, is Pune's default correctly STIFF_CLAY (murrum) or should it be BLACK_COTTON?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q7:** For MEDIUM_ROCK, the system uses bearing capacity 1250 kPa (IS 6403, typical of 1000-1500 range). Is this the right typical value for residential foundation design, or should it be more conservative (e.g., 1000 kPa)?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

---

## Section B — Programming + feasibility (C2, C3a, C3b)

### B.1 — Budget envelope

The system computes "budget-supported buildable area" given declared total budget and city construction rate. For Chennai G+1 in May 2026, rates assumed are:
- Basic finish: ~₹1,800/sqft
- Mid finish: ~₹2,400/sqft
- Premium finish: ~₹3,200/sqft

**Q8:** Are these per-sqft rates representative of May-2026 Chennai residential reality?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q9:** Should the per-sqft rate decompose differently? Currently it includes materials + labour + contractor margin in one number, with implicit engineer fee elsewhere. The product wants this UNBUNDLED. What's the right split for ~₹2,400/sqft?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer (we particularly want your numbers here):**

### B.2 — Extreme-case detection

The system flags a brief as an "extreme case" when stated room count vs. budget vs. plot size produce an impossible combination. Example: "I want 6 bedrooms in a 1500 sqft plot with ₹30 lakh budget."

**Q10:** What are the most common "impossible briefs" homeowners actually bring to you, and does our extreme-case logic catch them?
**Your answer (open-ended):**

---

## Section C — Layout rules (C5, C6, C7, C9)

### C.1 — Structural grid (C7)

Currently uses a 3.5m × 3.5m column grid as a default for residential single-family G+1 with conventional RCC frame. Stub-column rules per IS 13920 for ductile detailing in Zone III/IV.

**Q11:** Is 3.5m × 3.5m a reasonable default column spacing for residential single-family G+1?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q12:** Should staircase be allowed to interrupt the column grid, or should the grid wrap around the staircase? Currently the system tries to align the grid first, then place staircase.
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### C.2 — Orientation (C6)

The system uses Vastu-aware orientation with three cultural-profile variants:
- DEFAULT (no Vastu weighting; pure functional orientation)
- VASTU_SUPPRESS (lower weight on Vastu factors)
- VASTU_ELEVATE (higher weight on Vastu factors)

**Q13:** Should Vastu orientation be a tier the homeowner explicitly opts into, or should it be the default in TN/Chennai?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q14:** Note: B-099 (Vastu FULL tier) is being hidden in v1 UI until v1.1 with separate Vastu-expert review. Is that the right cautious move, or should v1 ship without any Vastu mention at all?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### C.3 — Room minimums (C9)

Currently uses NBC 2016 Part 3 minimum room dimensions (9.5 sqm habitable, 1.8m bath, etc.) with per-city overrides where local body byelaws exceed NBC minimum.

**Q15:** Are these NBC minimums sufficient defaults, or do you find yourself routinely advising larger minimums for habitable-bedroom dignity (i.e., NBC minimum yields a room too small to actually furnish)?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

---

## Section D — Circulation (C8)

### D.1 — Corridor width

Currently `CorridorDesignConfig.regulatory_min_width_m = 0.9`. NBC Part 3 single-dwelling default. NBC Part 4 fire-egress can require 1.0m+ for longer corridors / multi-unit. Callers must override.

**Q16:** For single-family residential single-dwelling-unit with corridor length ≤ 6m, is 0.9m the right minimum?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q17:** When does NBC Part 4 fire-egress override kick in for single-family? The system currently leaves this to the caller; should there be an automatic threshold (e.g., corridor length > 8m forces 1.0m)?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

---

## Section E — Wet zones (C10)

### E.1 — Stack location

C10 places wet-zone stacks (kitchen sink, bathroom WC) along a stacking line that maintains alignment across floors for G+1+. Default stacking strategy is "minimize stack count."

**Q18:** Does "minimize stack count" align with current Indian residential plumbing practice, or do you see real homes use multiple stacks to avoid kitchen-above-bathroom moisture penetration?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### E.2 — RWH (Rainwater Harvesting)

TNCDBR rule 7 mandates RWH for plots ≥ 200 sqm. System currently flags the requirement and provisions a 300L tank as default.

**Q19:** Is 300L the right default RWH capacity, or should it scale with roof area?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

---

## Section F — Topology mutation + doors (C11a, C11b, C13)

### F.1 — Layout overrides

The system allows a homeowner to explicitly override topology decisions (e.g., "I want the kitchen on the south, not the optimizer's pick"). The override mechanism has 3 named-rule bypass tokens scaffolded.

**Q20:** What's the most common architectural argument a homeowner brings that should genuinely override the optimizer's preference? (We want to make sure the override mechanism allows it.)
**Your answer (open-ended):**

### F.2 — Transit-bedroom

A bedroom is flagged as "transit" if walking to another room requires passing through it. The check excludes paths to closets/utility/storage.

**Q21:** Is the "transit-bedroom is bad" assumption universally valid in Indian residential vernacular, or are there legitimate cases (e.g., daughter's room with attached pooja niche; ancestral plot conversions) where this is intentional?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

---

## Section G — Compliance + drawings (C15, C16)

### G.1 — Severity rule table

C15 contains a 35-entry table classifying compliance violations as HARD_FAIL, SOFT_WARNING, or INFO. Examples:
- Setback violation: HARD_FAIL
- FAR exceeded: HARD_FAIL
- Room below NBC minimum: HARD_FAIL
- Corridor below regulatory: HARD_FAIL
- Vastu non-conformance: INFO (unless VASTU_ELEVATE profile, then SOFT_WARNING)
- Wet-zone-above-habitable: SOFT_WARNING

**Q22:** Looking at this severity classification approach: are any of the HARD_FAIL items actually fixable at design-amendment stage (and thus should be SOFT_WARNING)? Are any SOFT_WARNING items actually deal-breakers (should be HARD_FAIL)?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### G.2 — Cultural profile variants

C15 has 3 cultural-profile variants (default / vastu-suppress / vastu-elevate). Each variant maps to which checks fire and at what severity.

**Q23:** Are 3 variants enough, or should there be more (e.g., separate variant for Tamil-Brahmin convention vs. Tamil-Mukulam convention vs. cross-cultural)?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

### G.3 — Drawing standards (C16)

C16 produces dual drawings (working + permit) conforming to IS 962:1967 (line weights, typography, sheet size). The permit drawing format follows TNCDBR submittable conventions.

**Q24:** Is IS 962:1967 still the right rendering standard, or has a more current IS / NBC drawing convention superseded it?
[ ] AGREE / [ ] DISAGREE → recommend / [ ] REFINE → adjust / [ ] UNSURE
**Your answer:**

**Q25:** For CMDA / DTCP submission, what does your office's submittable drawing look like that ours might be missing? (We have 4 envelope schemas: floor plan working, floor plan permit, section view, elevation.)
**Your answer (open-ended):**

---

## Section H — Quote comparison (C17)

### H.1 — Rate sanity

C17 compares a contractor's quote line items against canonical city rates. It flags rates as ABOVE_REFERENCE_RANGE, AT_REFERENCE, or BELOW_REFERENCE_RANGE. There's also a "rate sanity flag" for ≤0.1× or ≥10× reference.

**Q26:** When you've seen contractor quotes deviate from market rates, what fraction of deviations have a legitimate explanation (premium materials, project complexity, contractor's specialization) vs. opportunistic? Our system tries to acknowledge legitimate premium but defaults to flagging.
**Your answer (open-ended):**

---

## Section I — Open-ended

### I.1 — Missing layers

**Q27:** What architectural decision does the system NOT currently make that any competent architect would absolutely make? (We have 17 components; we want to know what an 18th would be.)
**Your answer (open-ended):**

### I.2 — Wrong abstractions

**Q28:** Is there any part of the framing — what the system calls a "rule," a "fact," a "constraint," a "soft-warning," a "topology" — that mis-names or mis-categorizes something that architects actually think about differently?
**Your answer (open-ended):**

### I.3 — What you'd cut

**Q29:** If you had to cut three components from this 17-component system for a leaner v1 release, which three would you cut, and why?
**Your answer (open-ended):**

### I.4 — What you'd ship more of

**Q30:** Conversely: where would you DEEPEN the existing logic before shipping v1? (e.g., "C10 wet zones is too thin; needs DFU loading depth before v1" — note: this is also being addressed as B-220 in a parallel engagement with a plumbing engineer.)
**Your answer (open-ended):**

---

## Section J — Final sign-off

**Q-FINAL-1:** With the current state described in this packet, would you be comfortable sending this product to a real homeowner — say, your own cousin or close family member — as their primary decision-support tool?
[ ] YES / [ ] YES WITH SPECIFIC CHANGES / [ ] NO
**Reasoning:**

**Q-FINAL-2:** Top 3 things to fix before v1 release, ordered by your priority:
1. 
2. 
3. 

**Q-FINAL-3:** Top 3 things you would defer to v1.1 with confidence (i.e., absent in v1 is acceptable):
1. 
2. 
3. 

**Q-FINAL-4:** Anything you want to say that none of these questions surfaced:
**Your answer:**

---

## After you fill this in

Submit this completed template (or your free-form equivalent) as the engagement deliverable. Ramalingam + Claude will read every line, log every finding as a backlog item, decide which to act on before v1, and respond with a written acknowledgment of each point — including the ones we choose not to act on, with reasoning.

Thank you for the review.
