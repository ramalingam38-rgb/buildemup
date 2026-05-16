# Backlog additions — S52 C3b v0.6 BUILD critique walk Round 3

**Source:** Round 3 adversarial critique against C3b v0.6 LOCKED build
**Rule 7 web search:** 1 search executed (isovist visibility field spatial cognition)
**Pattern D rate:** 6/14 ≈ 43% — SHARP diminishing returns vs Round 2 (20%)
**Recommendation:** Round 4 not advised — Pattern D rate would likely exceed 50%

---

## Pattern D rate analysis

S52 critique-walk Pattern D progression:
- Round 1 (vs v0.4): 0/15 — first round, no priors
- Round 2 (vs v0.5): 3/15 = 20% — moderate
- Round 3 (vs v0.6): 6/14 ≈ 43% — sharp increase

This Pattern D rate confirms the userMemories Pattern D rule: "Round-2
critique escalation often yields diminishing returns." Round 3 confirms
the diminishing returns are now severe.

The 6 Pattern D items rejected in Round 3:
- Pt 32 (semantic drift) — addressed by v0.6 B1 extension_metadata
- Pt 35 (subset rerun fragility) — addressed by v0.5 A2 full-recompute
- Pt 37 (cultural intelligence) — already in backlog as
  B-C3B-AESTHETIC-HEURISTIC-CORPUS
- Pt 39 (cognitive saturation) — addressed by v0.5 A3 + A8
- Pt 40 (pre-construction-only) — routed to C15 at Round 2 Pt 29
- Pt 42 (multi-stakeholder) — verbatim repeat of Round 2 Pt 30

Round 4 is NOT recommended. If/when v0.6 sees a Round 4, the items
should focus on what's CHANGED since v0.6 LOCK, not re-derived
versions of the same architectural concerns.

---

## v1.x candidates (3 new C3b entries)

### B-C3B-EXPERIENTIAL-CONTINUITY-ISOVIST-COMPUTATION
**Origin:** S52 Round 3 critique Pt 33
**Web-research validation:** Isovist analyses are mathematically
well-defined and have been used in architectural research since the
1970s. Wikipedia summary cites isovist analyses for "determining
human behaviour in built environments based on spatial perception."
Multiple peer-reviewed sources (Springer, Wiener+Franz 2005,
Turner et al. 2001) document isovist-field algorithms.

**Description:** v0.6 B3 added `continuity_subscores["experiential"]`
as an Optional float field on TopologyInvarianceResult. This item
adds the COMPUTATION that populates it: an isovist-field delta
between source and predicted topology. Specifically:
  - Compute isovist from N sample vantage points (door centers
    + room centroids) for source and predicted topology
  - Measure delta in: visibility area, openness, jaggedness
  - Aggregate to a [0.0, 1.0] experiential continuity score
  - Populate continuity_subscores["experiential"]

**R6 safety:** isovist computation is purely geometric and
deterministic. Sample point selection must be deterministic
(documented sampling strategy). No ML involved.

**Trigger:** v1.x
**Effort:** M-L — algorithmic work + geometry library integration

### B-C3B-COMPATIBILITY-CAUSAL-GRAPH
**Origin:** S52 Round 3 critique Pt 34
**Description:** CompatibilityAssertion currently carries only a
free-form advisory_note. Add optional structured propagation chain:

```python
@dataclass(frozen=True)
class PropagationEdge:
    from_system: str   # e.g., "bathroom_relocation"
    to_system:   str   # e.g., "riser_stack"
    relationship: str  # e.g., "shares_wet_zone_chase"

@dataclass(frozen=True)  # adds field on existing class
class CompatibilityAssertion:
    ...existing fields...
    propagation_chain: Optional[tuple[PropagationEdge, ...]] = None
```

C3b emits the structured chain; visualization is downstream
renderer (C16/UI) work.

**Trigger:** v1.x
**Effort:** S — schema addition + chain-builder utility in
phases/severity.py + ~5 new tests

### B-C3B-GENERATIONAL-BOUNDARY-DESIGN
**Origin:** S52 Round 3 critique Pt 31
**Description:** As v0.x revisions accumulate, the compatibility
surface grows. v2 should introduce explicit "generation boundaries"
allowing controlled replay incompatibility between generations.

**Operational criteria pending (v2 design work):**
  - When does generation N transition to N+1? (proposed triggers:
    fundamental schema rewrite, R-invariant removal, semantic-engine
    swap)
  - What persists across generations? (proposed: ResolvedSelection
    output records — these are the "legal" artifacts; everything else
    is internal orchestration that can break)
  - What migration is required? (proposed: generation-to-generation
    translator services, not eternal backward-compat)

**Trigger:** v2 (architectural decision, not implementable until
v1.x telemetry surfaces real spec-gravity pain)
**Effort:** XL — major architectural design work

---

## v2 candidates (1 new + 1 existing-cross-reference)

### B-C3B-CLOSED-LOOP-FEEDBACK-LEARNING
**Origin:** S52 Round 3 critique Pt 41
**Description:** Closed-loop learning from real-world outcomes:
successful-home telemetry, user satisfaction, renovation history,
post-occupancy behavior, contractor feedback. Refines comfort
heuristics, circulation scoring, tweak prioritization over time.

**R6 determinism tension:** Active-learning loops are
fundamentally incompatible with byte-equal replay determinism
within a single epoch. Implementation requires either:
  (a) Frozen-model epochs (model versions identified by snapshot;
      replay produces same output as long as same model version),
  (b) Strategic-advisory-only application (model output goes to
      excluded-from-sig channels per R17 pattern), or
  (c) Relaxed-determinism mode (admit replay drift across model
      retrains; provide explicit migration path)

Approach (a) is least disruptive but requires snapshot infrastructure.
Approach (b) limits learning to advisory text only.

**Cross-reference:** Related to but distinct from
B-C3B-DYNAMIC-DEPENDENCY-LEARNING (Round 2 Pt 24) which addresses
static impact tables specifically.

**Trigger:** v2 (post-launch — requires significant telemetry corpus)
**Effort:** XL

---

## Items REJECTED as Pattern D / out-of-scope / anti-pattern

### Pt 32 — Semantic interpretation drift
v0.6 B1 (extension_metadata channel) is the existing mechanism for
attaching versioned metadata to a session without affecting
canonical_replay_signature. Callers can stamp
`{"heuristic_engine_version": "comfort_v3.2"}` today.
**Action:** Document this convention in spec § 7.6.

### Pt 35 — Subset rerun fragility
Already addressed in v0.5 A2 (full_recompute_threshold counter with
default=3 MEDIUM tweaks → forced full recompute). The reviewer's
"force occasional canonical rebuilds" IS A2.

### Pt 36 — Advisory language reduces decision velocity
TweakOption.recommendation_flag (existing enum:
STRONGLY_RECOMMENDED / OPTION_TO_CONSIDER / etc) already carries
calibrated confidence. The "interaction mode" element is UX scope.

### Pt 37 — Cultural spatial intelligence
Pattern D repeat of S52 Round 2 Pt 26 + S52 Round 1 backlog item.
Already filed as B-C3B-AESTHETIC-HEURISTIC-CORPUS (v2) with
regional style enumeration.
**Action:** Annotate that existing entry with Round 3 framings:
  - Tamil family patterns
  - Kerala courtyard logic
  - Japanese compact living
  - Gulf hospitality planning

### Pt 38 — Research-mode invariant relaxation
ANTI-PATTERN. Relaxing invariants globally for "research mode" is
exactly the escape-hatch pattern that erodes safety. v0.6 B1
extension_metadata is the SAFE form of this (excluded-from-sig
metadata channel for research annotations).

Anti-pattern 4 in userMemories: Rules-on-rules → layering escape
hatches without addressing why invariants exist.

### Pt 39 — Long-session cognitive saturation
Largely addressed:
  - v0.5 A8: iteration_cap default 5→3 (reduces fatigue exposure)
  - v0.5 A3: oscillation detection (catches indecision loops +
    reversal patterns)
"Top 3 meaningful differences" is renderer scope.
**Action:** Annotate existing B-C3B-FATIGUE-TELEMETRY backlog with
the "decision simplification mode" framing.

### Pt 40 — Pre-construction-only optimization
Pattern D — already routed at Round 2 Pt 29 to C15 as
B-C15-FUTURE-ADAPTABILITY-DIMENSION. Lifecycle adaptability is a
property of the LAYOUT, scored by C15; C3b consumes the score.

### Pt 42 — Multi-stakeholder negotiation
VERBATIM Pattern D repeat of S52 Round 2 Pt 30. Already filed as
B-C3B-MULTI-STAKEHOLDER-NEGOTIATION (v2).

### Pt 44 — Spatial cognition engine
CATEGORY, not item. The pieces of "spatial cognition" are individual
backlog items, each filed separately:
  - Aesthetic corpus (filed)
  - Experiential continuity / isovist (filed this round)
  - Future adaptability (filed at C15 via Round 2)
  - Multi-stakeholder (filed)
  - Closed-loop learning (filed this round)
Document as v2/v3 strategic direction in buildemup_v2_vision.md.

---

## Existing-item annotations

### B-C3B-AESTHETIC-HEURISTIC-CORPUS (annotated again)
Cumulative annotations from S52 rounds 1, 2, 3:
- Style enumeration: Contemporary, Chettinad, Minimalist,
  Luxury Modern, Tropical, Courtyard-centric (Round 2)
- Regional patterns: Tamil family, Kerala courtyard, Japanese
  compact, Gulf hospitality (Round 3 Pt 37)
- Experiential dimensions (Round 3 Pt 43): spatial drama,
  natural-light choreography, framed views, emotional arrival
  sequences, serenity gradients

### B-C3B-FATIGUE-TELEMETRY (annotated)
S52 Round 1 entry. Round 3 annotation: when telemetry surfaces real
fatigue patterns, add a "decision simplification mode" that:
  - Detects user-fatigue signals (rapid back-and-forth, abandonment-
    near-finalization, comparison overload)
  - Offers "top 3 meaningful differences" condensed view
  - Provides milestone checkpoints with low-friction resume

---

## Round-3 verdict on BUILD-LOCK status

NONE of the 14 items invalidates the v0.6 BUILD LOCK.

Round 3 produced 3 net-new v1.x items, 1 net-new v2 item, and 2
annotations on existing items. Yield is positive but Pattern D
rate (43%) is high enough that I recommend:

1. **No Round 4 against v0.6.** Diminishing returns are now severe.
2. **If a future round is wanted, focus on what's CHANGED** since
   v0.6 LOCK rather than re-deriving the same architectural
   concerns from a different framing.
3. **C3b v0.6 remains LOCKED** (by Ramalingam delegation per spec
   § 6). Build remains shipped at 450 tests passing.

**Tally:** 3 v1.x · 1 v2 · 2 annotations · 7 rejected (5 Pattern D
 + 1 anti-pattern + 1 category-not-item)
