# BuildemUp† — Design Principles v3.1
## Permanent Addendum — Locked Before Implementation

**†** = placeholder name, marked everywhere for future global rename.

---

## 0. Document purpose

This addendum locks in seven product principles that emerged from the final review round. These principles must be honoured by every component during implementation. They are not optional refinements — they are the difference between a product users trust and one they don't.

This document is short by design. It is meant to be re-read at the start of every coding session.

---

## 1. The Product, in one sentence

BuildemUp† is a **decision-support engine for Indian families building their own home.**

The floor plan is the artifact. The real product is **confidence in a six-figure decision.**

---

## 2. The three asymmetries we exist to close

Every Indian family building a home faces three asymmetries:

| Asymmetry | What the user lacks | What we provide |
|---|---|---|
| **Information** (vs contractor) | Costs, materials, market rates | Quote Comparison, Contractor Pack, visible margin |
| **Expertise** (vs architect) | Codes, drawings, technical language | Plain-language reports, dual drawings, citations |
| **Emotional** (vs the decision) | Benchmarks, social proof, validation | Transparency Triple, confidence indicators, reassurance |

**Scope test:** if a feature doesn't close one of these three asymmetries, it doesn't belong in v1. This is our scope discipline.

---

## 3. The Seven Locked Principles

### Principle 1: Experience-driven explanations

Every `explain()` method talks to the user, not the engine.

| Engine-centric (BAD) | Experience-driven (GOOD) |
|---|---|
| "Privacy score: 7/10" | "When you open your front door, bedroom 1's door is visible from 15 feet away. A small screen near the entry would solve this for ~₹12,000." |
| "Pareto-optimal on cost dimension" | "This is the most cost-efficient layout in our exploration — ₹3-4L cheaper than the alternatives." |
| "Insufficient sqft for badminton court placement" | "A full badminton game would take up almost your entire terrace. You wouldn't have space left for a gym, garden, or seating." |

**Test:** Read it out loud. If it sounds like an engineer talking to another engineer, rewrite it.

---

### Principle 2: The Transparency Triple

**Every numeric output gets three things:**
1. **A range** reflecting honest uncertainty
2. **An exact midpoint** for users who want a single number
3. **The derivation** showing how we got there

**Example — cost output:**

```
ESTIMATED COST: ₹56L – ₹61L (mid-tier finish, Chennai 2026)
                Most likely: ₹58.5L
                Confidence: Medium (±9%)

Click to see breakdown:
  Structure (RCC frame):    ₹14.6L  ← from grid + IS 456 rates
  Masonry + plaster:        ₹9.2L   ← from wall area × 9" brick rate
  Plumbing:                 ₹4.8L   ← reduced 35% via stack alignment
  Electrical:               ₹5.1L   ← from fixture count × point rate
  Flooring (mid-tier):      ₹6.8L   ← vitrified tile @ ₹85/sqft
  Doors + windows:          ₹4.5L   ← schedule × unit rates
  Painting:                 ₹3.9L   ← surface area × spec
  Waterproofing:            ₹1.8L   ← bathroom + terrace area
  Site work + misc:         ₹2.4L
  ──────────────────────────
  Build cost subtotal:     ₹53.1L
  Reasonable margin (12%):  ₹6.4L  ← contractor margin (visible)
  ──────────────────────────
  Estimate (mid):          ₹58.5L  
  Estimate (range ±9%):    ₹56L – ₹61L

Variability drivers (why the range exists):
  • Tile choice swing: ±₹1.5L
  • Bathroom fittings tier: ±₹1L
  • Woodwork scope: ±₹1.5L
  • Contractor margin variation: ±₹2L
```

**Same pattern for room sizes:**

```
MASTER BEDROOM: 155–165 sqft (target 160 sqft)
  This range allows you to fine-tune during click-to-edit.
  Below 155: queen bed + walk-in access becomes tight.
  Above 165: wastes area that could go to balcony.
```

**Same pattern for timelines:**

```
CONSTRUCTION TIMELINE: 4–5.5 months (target 4.5 months)
  Confidence: Medium (depends on monsoon, labour availability)
  Slowest milestone: foundation curing (28 days minimum, weather-dependent)
```

**Same pattern for material quantities, plumbing runs, anything numeric.**

**Why this matters:** A single number "₹58.5L" looks confident but backfires when reality comes in 15% different. A range with derivation:
- Honest about uncertainty
- Specific enough to verify
- Educational — user learns what drives cost
- Trust-building because we're not hiding our reasoning

---

### Principle 3: Advisory tone (not auditor tone)

The Quote Comparison Engine especially, but everywhere user-facing language appears. We are advising the user, not arming them for war with the contractor.

| Auditor tone (BAD) | Advisory tone (GOOD) |
|---|---|
| "DO NOT PAY LUMP SUM" | "It's safer to request a detailed breakdown for this item before proceeding." |
| "Overpayment: ₹1.15L" | "This appears higher than the typical market range (~₹1.85L expected for Jaquar Continental). Worth asking for the exact model list." |
| "Contractor is overcharging" | "This rate is above current Chennai market. You could mention this when discussing." |
| "MISSING FROM QUOTE" | "These items are typically needed but aren't listed. Worth confirming if they're included or will be charged later." |

**Why this matters:** Indian construction relationships run on mutual respect, not American-style consumer advocacy. The user has to work with this contractor for 4-6 months after signing. Confrontational language can break that relationship before it starts.

**What we keep:** specific numbers, market comparisons, exact suggestions. We just wrap them in respectful language.

---

### Principle 4: User intervention checkpoints

The pipeline is not a black box that runs end-to-end and produces "the answer." Three explicit checkpoints where the user can review, modify, or override:

**Checkpoint 1 — After Topology Selection (Component 5)**
> "Based on your plot, we suggest exploring 3 layout types: Central Spine (best for your rectangle), Courtyard (best for Chennai climate), and Strip (backup). You can:
> - Approve all 3 (recommended)
> - Drop one
> - Add one we didn't suggest
> [Approve / Modify]"

**Checkpoint 2 — After Room Sizing (Component 9)**
> "Here are the room sizes we've planned. Most are flexible by ±5–10 sqft.
> - Master bedroom: 160 sqft (your walk-in adds 50 more)
> - Living: 200 sqft  
> - [click to adjust any]
> [Looks good / Adjust]"

**Checkpoint 3 — After Initial Layout Preview (after Component 11b)**
> "Here are 3 quick concept layouts. Want us to optimise deeply (60 seconds, usually 20-30% better) or proceed with these?
> [Quick / Deep optimise]"

After Checkpoint 3, the pipeline runs to completion with the final 3 layouts.

**Implementation note:** Each checkpoint must save state so user can come back later. No forced single-session.

---

### Principle 5: Confidence indicators

Every output category gets a confidence level. Not all parts of the answer are equally certain.

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

**Three levels:** HIGH (engineering-verified), MEDIUM (typical/modelled), LOW (variable/depends on contractor).

**Why this matters:** Users can mentally weight different parts of the output. They know plumbing cost is reliable but contractor margin is a negotiation variable.

---

### Principle 6: Emotional reassurance

The user is making a once-in-a-lifetime decision with no benchmark. They need to know they are not alone and their choice is reasonable.

Every layout shown to user includes a reassurance line:

```
LAYOUT B — Best for Family
  ₹56L – ₹61L
  
  💡 This layout is commonly chosen by families of 5-7 members 
     on plots of similar size in Chennai. The ground-floor 
     bedroom + bath is especially valued by families who 
     expect parents to visit or move in.
```

```
LAYOUT C — Best for Experience
  ₹65L – ₹73L
  
  💡 The courtyard design is gaining popularity in Chennai for 
     its natural cooling. Families who choose it typically 
     prioritise long-term comfort over upfront cost.
```

**Test:** If the user reads this and feels validated rather than alone, we've done it right.

**Implementation:** A small reassurance database keyed on (layout type, plot size tier, family size estimate). Phrases drawn from this database, not hand-coded per layout.

---

### Principle 7: Failure modes are explicit

Every component answers: "what happens when I can't produce a valid output?"

No black-box errors ever reach the user.

**Pattern:**

```python
class Component:
    def execute(self, input) -> ComponentResult:
        try:
            return self._run(input)
        except CannotProduceValidOutput as e:
            return self._graceful_failure(input, e)
    
    def _graceful_failure(self, input, error) -> UserMessage:
        # Returns a user-readable explanation of why we couldn't 
        # proceed and what they can do about it.
        # Never a stack trace, never a black box.
```

**Examples:**

| Failure | Bad response | Good response |
|---|---|---|
| Plot too small for all rooms | "ERROR: insufficient area" | "Your 5 bedroom + walk-in + lounge brief needs ~1100 sqft per floor. Your plot allows ~750 sqft per floor. We can fit 4 bedrooms + small lounge, or 5 bedrooms + no lounge. Which would you prefer?" |
| All topologies fail | "No layout possible" | "Your brief has constraints we can't satisfy together. The conflict: you want master + 4 bedrooms + walk-in on FF, but FF only fits 3 bedrooms cleanly. Options: drop one bedroom, drop walk-in, or add a second floor." |
| NSGA-II finds no Pareto survivors | "Optimisation failed" | "We explored 70 layouts and none scored well across all your priorities. The biggest blocker: your budget (₹40L) is below realistic build cost for this brief (~₹55L). Options: increase budget, reduce scope, or use lower-tier finishes." |

---

## 4. Implementation mandates

These apply to every component as we code:

1. **Pure Python, testable in isolation.** Every component is a class with clear input/output contracts. Unit tests cover normal, edge, failure cases.

2. **Apply the Transparency Triple to every numeric output.** Range + exact + derivation. No exceptions.

3. **`explain()` method talks to user, not engine.** Run the read-aloud test.

4. **Indian context in the knowledge layer, not hand-waved.** Real IS code citations, real NBC clauses, real Chennai 2026 rates with sources.

5. **Use existing KB modules.** Read `kb/parametric_layout.py`, `kb/cad_books_standards.py`, etc. before writing new logic. Don't duplicate.

6. **Boring correct over clever fast.** No micro-optimisations until we know the bottlenecks. Prove correctness first.

7. **Failure mode designed before happy path.** Write the graceful failure response before the main logic.

---

## 5. The Layout Triad (final naming)

Locked names for the three final layouts:

| Internal name | User-facing name | What it optimises |
|---|---|---|
| LAYOUT_A | **Cost Efficient** | Lowest viable build cost, standard finishes |
| LAYOUT_B | **Everyday Living** | Daily family experience, privacy, multigen |
| LAYOUT_C | **Premium Design** | Architectural quality, experience, light |

These names work because:
- Non-architect understands them immediately
- Each clearly different from the others (no "balanced")
- Maps to user identity ("I'm building for my family" / "I'm building my dream")
- Marketing-ready

---

## 6. What we are NOT changing

These principles do not modify the 17-component architecture. They modify *how* each component presents its output and handles its failures. The structural design stays as documented in `BuildemUp_Architecture_v3.md`.

---

## 7. The contract between us (Ramalingam ↔ Claude)

Three things we both commit to throughout implementation:

**Ramalingam:**
1. Catch when responses drift back to engine-centric thinking
2. Trust your instincts on user experience even when you can't articulate why
3. Push back on scope creep ("does v1 really need this?")

**Claude:**
1. Read existing KB before writing new code
2. Apply all 7 principles to every component
3. Document failure modes before happy paths
4. Boring correct code over clever optimisations
5. No black-box errors ever reach the user

---

## 8. Ready signal

This addendum is now part of the permanent design. It will be referenced by every coding session.

**Next step:** Begin coding Component 7 (Structural Grid Engine).

---

**END OF ADDENDUM**

*Locked. Read before every implementation session.*
