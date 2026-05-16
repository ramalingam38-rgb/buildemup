# C3b — Post-Layout Trade-off Negotiation
## Spec v0.2 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Predecessor:** v0.1 PROPOSED (S50 close).
**Composed from:** v0.1 PROPOSED + critique walk findings (S50 close → S51 open).
**Session:** S50 close.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone.

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale (v0.2)

v0.1 PROPOSED was a greenfield first draft (802 lines, 12 R-invariants).
The critique walk surfaced 13 numbered concerns. Verdict tally:

- **6 SPEC-AMENDMENTs** adopted in v0.2 (4 major architectural patches +
  2 small refinements)
- **4 new R-invariants** (R13–R16) supporting the amendments
- **8 new BACKLOG items** filed per Rule 9.2
- **3 NO ACTION** (1 already filed, 1 praise, 1 captured by existing § 0.1)

**The 6 v0.2 patches** address genuine architectural gaps, not philosophical
refinements. Per the C17 v0.2 precedent: only patch what is genuinely
actionable as spec change.

| # | Patch | Critique pt | Severity |
|---|---|---|---|
| 1 | **R13 Topology Invariance Invariant** (§ 7) | 1 | Major |
| 2 | **Phase β per-instance severity computation** (§ 3) | 2 | Major (defect in v0.1) |
| 3 | **`SubsetRerunRequest.downstream_impact_set` formalization** (§ 2.4) | 4 | Major |
| 4 | **R14 Regression Detection Invariant** (§ 7) | 6 | Major |
| 5 | **R15 Multi-Tweak Compatibility Check** (§ 7) | 3 | Small |
| 6 | **R16 Version Authority Invariant** (§ 7) + § 2.1 clarifying note | 11 | Small |
| 7 | **§ 2.8 `MutationEnvelope`** (NEW) — user-facing HEAVY rejection | 5 | Small |

**No restructure.** Output-contract types extended (§ 2.4, § 2.8) but not
removed or renamed. Phase pipeline keeps its 6-phase α–ζ shape; only
Phase β's step-4 logic is reworked.

---

## § 1 — Scope

§§ 1.1, 1.2, 1.3 — carried forward unchanged from v0.1.

### 1.4 — Applicability boundary — carried forward unchanged

---

## § 2 — Output contract

§§ 2.1, 2.2, 2.3, 2.5, 2.6, 2.7 — carried forward unchanged from v0.1,
with one **clarifying note added to § 2.1** per critique pt 11:

> **§ 2.1 clarifying note (NEW v0.2):** `TradeoffSession.session_history`
> is **append-only single-linear-history** in v1.0. At any session
> moment, exactly ONE layout state is authoritative (the latest applied
> state). Multi-branch sessions, parallel-universe exploration, and
> multi-user collaborative negotiation are v1.x work per
> `B-C3B-MUTATION-LINEAGE-AND-BRANCHING` (§ 9.2). Enforced by R16.

### 2.4 — `ApplySpecification` (PATCHED v0.2)

v0.1's `ApplySpecification` carried forward. **PATCHED:** the
`subset_rerun_payload` field now uses the **formalized
`SubsetRerunRequest` contract** below, not a free-form payload.

```
ApplySpecification
├── mutation_kind:                   Literal[
│       "geometry_local",
│       "subset_rerun",
│       "finish_schedule_only",
│   ]
├── geometry_local_payload:          GeometryLocalPayload | None
├── subset_rerun_payload:            SubsetRerunRequest | None   # FORMALIZED v0.2
└── finish_schedule_payload:         FinishSchedulePayload | None
```

### 2.4.1 — `SubsetRerunRequest` (FORMALIZED v0.2 — critique pt 4)

Per critique pt 4: v0.1's subset-rerun assumption was elegant but
under-specified. Layout pipelines contain hidden couplings (moving a
wet zone affects circulation, structure, ventilation, vertical
alignment, furniture fit, daylight, ranking score, problem detection).
v0.2 forces every tweak category to **upfront-declare its downstream
impact set**, not just the components to rerun.

```
SubsetRerunRequest
├── trigger_tweak_id:                str
├── trigger_tweak_category:          str   # one of § 2.3's 13 categories
│
├── components_to_rerun:             tuple[Literal[
│       "c4", "c5", "c6", "c7", "c8", "c9", "c10",
│       "c11a", "c11b", "c12", "c13", "c14", "c15",
│   ], ...]
│       The components that will execute. Strictly ordered lex-ASC
│       for replay determinism.
│
├── downstream_impact_set:           tuple[Literal[
│       "circulation_graph",          # C14 nodes/edges may change
│       "structural_grid",            # C7 columns/beams may shift
│       "wet_zone_stacks",            # C10 plumbing risers
│       "vertical_alignment",         # C12 inter-floor coherence
│       "furniture_fit",              # C9 sizer validation
│       "natural_light",              # C6 orientation effects
│       "cross_ventilation",          # C6 orientation effects
│       "problem_report",             # C15 will re-run
│       "ranking_score",              # C15 SelectionResult ordering
│       "topology_classification",    # C5 — if this fires, severity AUTO-PROMOTES to HEAVY (R13)
│       "finish_schedule",            # C16 input
│       "door_placement",             # C13 doors may relocate
│   ], ...]
│       MANDATORY. Empty tuple is invalid (constraint check in
│       __post_init__). Every tweak category has a static minimum
│       impact set declared in `TWEAK_CATEGORY_IMPACT_TABLE` (see
│       § 3 Phase β).
│
├── topology_invariance_check:       TopologyInvarianceResult
│       Per R13 (NEW v0.2) — predicted topology classification after
│       rerun MUST equal current topology classification. If predicted
│       differs, the tweak is reclassified HEAVY at generation time.
│
├── expected_completion_seconds:     float
│       Upper bound estimate for the subset rerun (LIGHT < 1s,
│       MEDIUM 1-10s typical, > 10s requires reclassification)
│
├── rerun_anchor:                    str
│       Domain-specific anchor describing the constraint preservation
│       (e.g. "wet_zone_eastward_with_structural_bay_lock")
│
└── compatibility_assertions:        tuple[CompatibilityAssertion, ...]
        Per R15 (NEW v0.2) — assertions verifying that this rerun
        won't conflict with previously-applied tweaks in the session.
        Checked by Phase ε before apply.
```

### 2.4.2 — `TopologyInvarianceResult` (NEW v0.2 — R13 support)

```
TopologyInvarianceResult
├── source_topology:                 Literal[
│       "no_corridor", "strip", "central_spine", "l_shape", "courtyard",
│   ]
├── predicted_topology:              Literal[<same literals>]
├── invariance_preserved:            bool
│       True iff source_topology == predicted_topology
├── prediction_basis:                Literal[
│       "structural_grid_invariant",      # bay topology unchanged
│       "circulation_pattern_invariant",  # corridor structure unchanged
│       "mutation_local_only",            # tweak doesn't touch topology-defining elements
│       "heuristic_strong",                # high confidence
│       "heuristic_weak",                  # low confidence — auto-promote to HEAVY
│   ]
└── advisory_note:                   str | None
        Populated when invariance_preserved == False, explaining
        why the tweak would alter topology and route to HEAVY.
```

### 2.4.3 — `CompatibilityAssertion` (NEW v0.2 — R15 support)

```
CompatibilityAssertion
├── against_applied_tweak_id:        str
│       References a tweak already applied earlier in this session
├── compatibility_kind:              Literal[
│       "spatial_overlap_check",      # do the affected rooms overlap?
│       "stack_alignment_check",      # do wet-zone stacks remain aligned?
│       "structural_continuity",      # do columns remain continuous?
│       "circulation_reachability",   # is every room still reachable?
│   ]
├── result:                          Literal["compatible", "conflicts", "ambiguous"]
└── advisory_note:                   str | None
        Populated for "conflicts" — what specifically conflicts and
        what the user could do (revert one, accept the conflict, etc.)
```

### 2.8 — `MutationEnvelope` (NEW v0.2 — critique pt 5)

When a user requests a tweak that C3b classifies as HEAVY (or detects
that their accumulated requests imply HEAVY), C3b emits a
`MutationEnvelope` instead of attempting the mutation. Per Principle 3
(advisory tone) + Principle 4 (user intervention checkpoints), the
envelope explains plain-English why the request is brief-level work
and routes the user to the right pipeline stage.

```
MutationEnvelope
├── envelope_id:                     str
├── requested_change_summary:        str
│       Plain-English of what the user asked for.
│       e.g. "Add another bedroom to the first floor"
│
├── classification:                  Literal[
│       "brief_level_change",         # → kick back to C3a
│       "topology_level_change",      # → would require C5/C11a rerun
│       "structural_level_change",    # → would require C7 redesign
│       "out_of_v1_scope",            # → v2+ feature
│       "constraint_violation",       # → NBC / structural / hard-constraint blocker
│   ]
│
├── why_not_a_tweak:                 str
│       Per Principle 3 advisory tone. Explains why this isn't
│       achievable at the C3b layer.
│       e.g. "Adding a bedroom changes the room count, which we
│             configured at the brief stage. We can step back to
│             the brief, update the room composition, and re-run
│             the layout pipeline from there — typically 60 seconds."
│
├── suggested_pathway:               Literal[
│       "step_back_to_brief",         # restart C3a
│       "accept_layout_as_is",         # finalize current layout
│       "explore_alternative_layout", # pick a different one of the 3
│       "defer_to_v2_feature",
│   ]
│
├── estimated_pathway_effort:        str
│       Plain-English effort estimate.
│       e.g. "Stepping back to the brief takes 1-2 minutes of your
│             time, plus 60 seconds for the system to re-run."
│
├── kick_back_payload:               KickBackPayload | None
│       Populated when classification == "brief_level_change". Contains
│       the structured request for C3a (which brief field to revisit,
│       what context to surface).
│
└── advisory_note:                   str
        Wrap-up plain-English line, Principle 3 advisory tone.
        Test: read it out loud; if it sounds like an engineer talking
        to another engineer, rewrite.
```

`MutationEnvelope` is surfaced as part of `SessionTurn` when the user's
requested action triggers HEAVY classification, or when `KickbackContext`
is built for the `kicked_back_to_c3a` status.

---

## § 3 — Phase pipeline (Phase β PATCHED v0.2)

§§ 3 Phase α, γ, δ, ε, ζ — carried forward unchanged from v0.1.

### Phase β — Tweak generation per layout (PATCHED v0.2)

v0.1's Phase β step 4 was: *"Apply severity filter: classify each
candidate tweak as LIGHT, MEDIUM, or HEAVY (static category →
severity mapping)."* Per critique pt 2, this is a defect — the same
tweak category can be different severity in different contexts
(door in load-bearing wall vs partition; room_resize within a single
bay vs across bays).

**v0.2 Phase β step 4 (REVISED — per-instance severity computation):**

For every candidate tweak, severity is computed in three stages:

**Stage 4.1 — Default severity from category lookup.**

```
TWEAK_CATEGORY_DEFAULT_SEVERITY:
  finish_upgrade / finish_downgrade        → "light"
  door_relocate / window_resize            → "light"  (default; context can promote)
  balcony_add / balcony_remove             → "light"  (default; context can promote)
  storage_add / utility_zone_carveout      → "medium"
  room_swap                                → "medium"
  room_resize                              → "medium"  (default; context can promote)
  pooja_relocate                           → "medium"
  kitchen_reorient                         → "medium"
  wet_zone_restage                         → "medium"
```

**Stage 4.2 — Context-aware adjustment.**

For each candidate tweak, compute the **context vector**:

| Factor | Source | Promotes severity if... |
|---|---|---|
| Load-bearing wall involvement | C7 structural grid | tweak affects a wall marked load-bearing OR within 300mm of a column |
| Circulation graph impact | C14 CirculationGraphReport | tweak adds/removes a graph node or edge |
| Wet-zone stack interaction | C10 RiserGroup output | tweak affects a room with a riser OR adjacent to one |
| Structural-bay boundary crossing | C7 grid cells | room_resize that crosses a bay boundary |
| Topology classification | C5 topology selector output | per R13 — if predicted topology differs from source |
| External-wall change | C16 envelope schema | tweak alters the building envelope |

**Promotion rules:**
- Any single factor crossing threshold → promote by 1 tier (LIGHT → MEDIUM, or MEDIUM → HEAVY)
- Two or more factors triggering → promote MEDIUM tweaks to HEAVY directly
- Topology classification mismatch (R13) → AUTO-PROMOTE to HEAVY regardless of other factors

**Stage 4.3 — Final severity assignment.**

If `final_severity == "heavy"`:
- Tweak is REMOVED from `TweakOptionSet.tweaks` (not surfaced)
- A `MutationEnvelope` is generated for this tweak with
  `classification == "topology_level_change"` (or `"structural_level_change"`
  based on which factor promoted it) and is buffered for later use IF the
  user explicitly requests something matching this pattern.

If `final_severity == "medium"`:
- Tweak is surfaced
- Its `ApplySpecification.subset_rerun_payload` is built with the
  formalized `SubsetRerunRequest` (§ 2.4.1) — `downstream_impact_set`
  must be non-empty
- `TopologyInvarianceResult` is computed and attached

If `final_severity == "light"`:
- Tweak is surfaced
- Its `ApplySpecification.geometry_local_payload` or
  `finish_schedule_payload` is built directly

**Stage 4.4 — Bounded selection (unchanged from v0.1):**

If more than 6 candidate tweaks remain, prioritize by:
(a) tweak addresses critical problem, (b) tweak is LIGHT severity,
(c) tweak's recommendation_flag is "suggested". Max 6 surfaced per layout.

---

## § 4 — Error tiers (small additions v0.2)

§§ 4.1, 4.2 carried forward from v0.1, with **two new errors added**:

### 4.1 — `LocalTradeoffError` — additions

- `TopologyInvarianceProbeError` (NEW v0.2) — Phase β step 4.2 couldn't
  determine `TopologyInvarianceResult.prediction_basis` confidently. The
  candidate tweak is auto-classified as HEAVY by default (safety bias).

### 4.2 — `PerTweakError` — additions

- `DownstreamImpactSetMissingError` (NEW v0.2) — a MEDIUM tweak's
  `SubsetRerunRequest.downstream_impact_set` is empty. Hard error per
  the § 2.4.1 contract.
- `CompatibilityAssertionFailedError` (NEW v0.2) — Phase ε apply step
  found a `CompatibilityAssertion.result == "conflicts"` against an
  already-applied tweak. STRICT halts; WARN surfaces the conflict to
  the user with options.

---

## § 5 — Versioning (PATCHED v0.2)

```python
C3B_VERSION = "v0.2.PROPOSED"
C3B_SESSION_SCHEMA_VERSION = 2     # BUMP from v0.1 (additive — MINOR per R9)
C3B_IDENTITY_GENERATION = 1

# Unchanged from v0.1:
SUPPORTED_JURISDICTIONS = {"tn_cdbr_2019"}
SUPPORTED_DOMAIN_SCOPES = {"residential_v1"}
EXPECTED_C15_VERSION = "v1.0.LOCKED"
EXPECTED_C16_VERSION = "v0.5.LOCKED"
EXPECTED_C7_VERSION  = "v0.8.LOCKED"
EXPECTED_C12_VERSION = "v1.0.LOCKED"
EXPECTED_C13_VERSION = "v1.0.LOCKED"

ITERATION_CAP_DEFAULT = 5
ITERATION_CAP_HARD_CEILING = 7
MAX_TWEAKS_PER_LAYOUT = 6
MAX_REPRESENT_COUNT = 2
```

**Schema-version bump 1 → 2** because v0.2 ADDS:
- `SubsetRerunRequest.downstream_impact_set` field (MANDATORY, non-empty)
- `SubsetRerunRequest.topology_invariance_check` field
- `SubsetRerunRequest.compatibility_assertions` field
- `TopologyInvarianceResult` type
- `CompatibilityAssertion` type
- `MutationEnvelope` type
- § 2.1 single-linear-history clarifying note

Per R9 inheritance: ADDITIVE fields → MINOR bump. v0.1 was never LOCKED
or released; no consumer compatibility burden.

---

## § 6 — Hard ceilings — carried forward unchanged from v0.1

---

## § 7 — R-invariants (R13–R16 ADDED v0.2 — 16 total)

R1–R12 from v0.1 carry forward unchanged. R13–R16 are NEW.

### 7.1 — R13 — Topology Invariance Invariant (NEW v0.2 — critique pt 1)

> **R13 — MEDIUM tweaks MUST preserve C5's topology classification.**
>
> For every candidate tweak classified as MEDIUM, Phase β step 4
> MUST compute a `TopologyInvarianceResult` predicting the topology
> classification after the subset rerun. If `predicted_topology !=
> source_topology`, the tweak is AUTO-PROMOTED to HEAVY and removed
> from `TweakOptionSet.tweaks`.
>
> **Rationale (critique pt 1):** v0.1's MEDIUM tier risked becoming
> a "shadow layout generator" by accumulating mutation power that
> effectively duplicates C11a/C11b/C12 in fragmented form. R13 enforces
> the topological integrity boundary structurally: a tweak that would
> alter topology is BY DEFINITION a topology change, not a tweak, and
> must be routed back to C5/C11a via the kick-back-to-C3a pathway.
>
> **Enforcement:** at tweak generation time. The `TopologyInvarianceResult`
> is attached to every MEDIUM tweak's `SubsetRerunRequest` (§ 2.4.1).
> Phase ε's apply step verifies invariance one more time before
> committing the rerun.
>
> **Edge case:** If `TopologyInvarianceResult.prediction_basis ==
> "heuristic_weak"`, the tweak is auto-promoted to HEAVY by safety
> bias. We never gamble with topology preservation.

### 7.2 — R14 — Regression Detection Invariant (NEW v0.2 — critique pt 6)

> **R14 — A MEDIUM rerun that increases critical-tier ProblemReport
> issues is a regression and MUST be surfaced.**
>
> When Phase ε completes a MEDIUM subset rerun and the new C15
> `ProblemReport` has MORE `severity == "critical"` checks than the
> original `ProblemReport`, the apply step:
>
> 1. Marks the tweak's apply outcome as `regression_detected`
> 2. Adds an `AdvisoryFlag` to the `TradeoffSession` with kind
>    `regression_after_apply` listing the specific newly-critical checks
> 3. Surfaces an automatic "undo this tweak" option in the next
>    `TweakOptionSet`, with `recommendation_flag == "suggested"` and
>    a description like *"This tweak introduced [N] new critical
>    issues. You could undo it and try a different approach."*
> 4. Does NOT auto-revert. The user retains agency (Principle 4).
>
> **Rationale (critique pt 6):** Local tweak optimization can produce
> globally worse layouts. Without regression detection, C3b would
> silently drift layouts away from Pareto optimality. R14 makes
> regression visible as a first-class event.
>
> **Enforcement:** at Phase ε's `apply_outcome` computation, by
> comparing pre-rerun and post-rerun `ProblemReport` critical-counts.

### 7.3 — R15 — Multi-Tweak Compatibility Check (NEW v0.2 — critique pt 3)

> **R15 — Before applying any tweak, multi-tweak compatibility MUST
> be checked against already-applied tweaks in the session.**
>
> When the user accepts a tweak, Phase ε runs the
> `CompatibilityAssertion[]` from § 2.4.3 against every previously-
> applied tweak in `session_history`. The four assertion kinds:
> spatial_overlap, stack_alignment, structural_continuity,
> circulation_reachability.
>
> Resolution:
> - **All "compatible":** apply proceeds normally.
> - **Any "conflicts":** apply is BLOCKED; user is surfaced the
>   conflict with three options:
>     (a) revert the earlier conflicting tweak
>     (b) abandon this new tweak
>     (c) ask C3b to find an alternative tweak that achieves the
>         same goal without conflict
> - **Any "ambiguous" + no "conflicts":** apply proceeds with a
>   `compatibility_ambiguous` advisory flag for downstream surfacing.
>
> **Rationale (critique pt 3):** Tweak interactions are highly
> non-independent. v0.1 treated tweaks independently, risking
> constraint-accumulation chaos. R15 makes interaction-aware apply
> the structural default.
>
> **Note:** v1.0 ships pairwise compatibility checks. v1.x adds a
> formal dependency/conflict graph via
> `B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH` for N-way reasoning.

### 7.4 — R16 — Version Authority Invariant (NEW v0.2 — critique pt 11)

> **R16 — At any session moment, exactly ONE layout state is
> authoritative: the latest applied state in `session_history`.**
>
> v1.0 ships **single-linear-history.** No branching, no
> parallel-universe exploration, no multi-user collaborative
> negotiation. The `session_history` tuple is append-only and
> totally ordered.
>
> **Properties:**
> - Authoritative layout state at iteration N = state after applying
>   the chosen tweak from `session_history[N]` (if accepted) or
>   state at N-1 (if rejected / no_action / abandoned).
> - Replay reconstructs lineage deterministically from
>   `session_history` (R11 inheritance).
> - "Undo this tweak" (per R14) is implemented as
>   `user_action == "accepted_tweak"` with a synthetic revert tweak,
>   not as state mutation.
> - Multi-branching / multi-user negotiation deferred to
>   `B-C3B-MUTATION-LINEAGE-AND-BRANCHING` (§ 9.2).
>
> **Rationale (critique pt 11):** v0.1's append-only session history
> implied linear ordering but didn't make it an explicit invariant.
> Critique pt 11 raised valid questions (which version is authoritative?
> can users branch? can users revert to iteration 2?). v0.2 answers
> these definitively for v1.0: one state, latest-applied, undo-via-
> revert-tweak.

### 7.5 — Banned-phrase template (R2 EXPANDED v0.2)

R2 banned-phrase list inherits from C17 v0.3 R2 list, with v0.2
additions for C3b-specific risks:

**Banned in v0.2 additions:**
- "the system decided" (suggests no agency)
- "we'll auto-fix" (suggests imposition)
- "you have to" (suggests no choice)
- "perfect tweak" / "best tweak" (suggests authoritative ranking)
- "tweak failed" → use "tweak couldn't apply"
- "rejected" (as a verb the user faces) → use "couldn't be surfaced as a tweak"

---

## § 8 — Upstream dependencies — carried forward unchanged from v0.1

---

## § 9 — Backlog

### 9.1 — v1.0 LOCK-mandatory — carried forward from v0.1 (7 items)

(see v0.1 § 9.1: phase implementations, test coverage parity,
subset-rerun orchestrator contract, advisory-tone lint, tweak-generation
coverage calibration, session persistence WAL retrofit, Q3 Level B
audit replay tests.)

**v0.2 addition:** `B-C3B-SUBSET-RERUN-ORCHESTRATOR-CONTRACT` scope
expanded to include the formalized `downstream_impact_set` per § 2.4.1.
The orchestrator MUST honor the upfront-declared impact set, not its
own internal heuristic determination of what to rerun.

### 9.2 — DEFERRED (8 from v0.1 + 8 NEW v0.2 = 16 items)

**Carried forward from v0.1 (8 items):**

(LLM-driven tweak generation, multi-city patterns, cross-floor tweaks,
empathy layer, tweak interaction detection, replay diffing tool, legal
review, bandit prioritization.)

**NEW v0.2 (8 items):**

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| `B-C3B-FORMAL-MUTATION-ENVELOPE-GRAPH` | Build a formal mutation-envelope graph at v1.x to replace the heuristic context-aware adjustment in Phase β step 4.2. Graph nodes = mutation operators × geometric contexts; edges = severity-promotion transitions; enables proof-based severity reasoning, not heuristic | v0.1 critique pt 1 | v1.x rigor work | L |
| `B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH` | Replace v1.0's pairwise compatibility checks (R15) with formal dependency/conflict graph for N-way tweak interaction reasoning. Especially important for sessions with 4+ accepted tweaks | v0.1 critique pt 3 | v1.x after pairwise data accumulates | L |
| `B-C3B-REGRESSION-DETECTION` (PROPER FILING) | v0.1 § 11 mentioned this as a critique pre-emption but didn't file it. v0.2 makes regression detection an R14 invariant; this backlog item covers the post-launch calibration of regression thresholds (when does "more critical issues" cross from noise to meaningful regression) | v0.1 § 11 + v0.1 critique pt 6 | Post-launch monitoring | M |
| `B-C3B-GRADUATED-FINALIZATION-NUDGES` | Beyond the iteration cap hard stop, v1.x adds graduated UX nudges encouraging finalization once user has explored 3+ tweaks. Tied to confidence-to-finalize heuristics per critique pt 7 | v0.1 critique pt 7 | v1.x UX | M |
| `B-C3B-DOWNSTREAM-RENDERER-BEHAVIORAL-CONTRACT` | Mirrors C17 v0.3 backlog item. C3b is UI-sensitive (sequencing, side-by-side comparison, undo affordances, mutation history visibility shape decisions). Renderer-side minimum behavioral obligations should be specified | v0.1 critique pt 9 | Before first user-facing release | M |
| `B-C3B-TRADEOFF-COMMUNICATION-DESIGN` | Cost / space / comfort impacts are surfaced structurally per Principle 2, but users struggle with multi-dimensional tradeoffs. Long-term: dedicated philosophy + research on tradeoff communication | v0.1 critique pt 10 | v1.x UX research | L |
| `B-C3B-MUTATION-LINEAGE-AND-BRANCHING` | v1.x extension of R16 — adds branching session history (parallel exploration), version naming, "save this state and try something else" flow, multi-user collaborative negotiation | v0.1 critique pt 11 | v1.x | XL |
| `B-C3B-NEGOTIATION-OPERATING-SYSTEM-EVOLUTION` | Long-term observation track: if C3b becomes the most-used component (plausible per critique pt 13), future versions may require conversational interface, persistent negotiation memory, emotional-state handling. Not a v1.x item, but tracking it as architectural awareness | v0.1 critique pt 13 | Long-term v2+ | XL |

### 9.3 — Summary

| Category | Count |
|---|---|
| LOCK-mandatory (v0.1 set) | 7 |
| DEFERRED (v0.1 era) | 8 |
| DEFERRED (NEW v0.2) | 8 |
| **Total tracked** | **23** |

---

## § 10 — Test plan (v0.2 additions)

v0.1's ~210-test target stands. v0.2 adds these test files for the new
invariants and types:

| New test file | Count | Purpose |
|---|---|---|
| `test_c3b_r13_topology_invariance.py` | ~15 (NEW v0.2) | R13 — TopologyInvarianceResult correctly predicts; auto-promote to HEAVY when predicted topology differs; heuristic_weak forces HEAVY |
| `test_c3b_r14_regression_detection.py` | ~12 (NEW v0.2) | R14 — when subset rerun increases critical checks, advisory flag fires; "undo this tweak" appears in next option set |
| `test_c3b_r15_multi_tweak_compatibility.py` | ~15 (NEW v0.2) | R15 — pairwise compatibility check fires; "conflicts" blocks apply with 3-option resolution; "ambiguous" surfaces advisory |
| `test_c3b_r16_version_authority.py` | ~8 (NEW v0.2) | R16 — single-linear-history enforced; latest-applied is authoritative; replay reconstructs lineage |
| `test_c3b_per_instance_severity.py` | ~20 (NEW v0.2) | Phase β step 4 — context-aware adjustment promotes severity correctly; door in load-bearing wall → MEDIUM; room_resize crossing bay → HEAVY; etc. |
| `test_c3b_mutation_envelope.py` | ~10 (NEW v0.2) | § 2.8 MutationEnvelope generated for HEAVY rejections; kick_back_payload populated correctly; banned-phrase lint catches accusatory language |
| `test_c3b_subset_rerun_request_contract.py` | ~10 (NEW v0.2) | § 2.4.1 — downstream_impact_set is mandatory non-empty; topology_invariance_check populated; expected_completion_seconds within bounds |

**Revised v1.0 LOCK test target: ~300 tests** (up from v0.1's ~210).

---

## § 11 — v0.1 critique walk verdicts (NEW v0.2 — audit trail per Rule 7)

The 13 numbered points from the v0.1 critique walk:

| # | Theme | Verdict | Disposition in v0.2 |
|---|---|---|---|
| **1** | Shadow layout generator risk | **SPEC-AMENDMENT — major** | **R13 Topology Invariance Invariant** (§ 7.1) + `TopologyInvarianceResult` (§ 2.4.2) + Phase β step 4 auto-promote-to-HEAVY rule. Plus `B-C3B-FORMAL-MUTATION-ENVELOPE-GRAPH` for v1.x rigor. |
| **2** | LIGHT/MEDIUM/HEAVY partition category-static, not context-sensitive | **SPEC-AMENDMENT — major (v0.1 defect)** | **Phase β step 4 reworked** (§ 3) — 3-stage severity computation: default category → context-aware adjustment (6 factors) → final assignment. Replaces v0.1's static category-lookup. |
| **3** | Tweak interactions under-specified | **SPEC-AMENDMENT (small) + BACKLOG** | **R15 Multi-Tweak Compatibility Check** (§ 7.3) + `CompatibilityAssertion` type (§ 2.4.3). Plus `B-C3B-MUTATION-CONFLICT-DEPENDENCY-GRAPH` for v1.x N-way reasoning. |
| **4** | Subset-rerun orchestration harder than spec assumes | **SPEC-AMENDMENT — major** | **`SubsetRerunRequest` formalized** (§ 2.4.1) — every tweak category MUST upfront-declare its `downstream_impact_set`; orchestrator contract becomes formal, not heuristic. |
| **5** | User expectation escalation under-addressed | **SPEC-AMENDMENT (small)** | **§ 2.8 `MutationEnvelope`** (NEW) — when user requests something HEAVY, structured response with classification + why-not-a-tweak + suggested-pathway. Plain-English advisory per Principle 3. |
| **6** | Local optimization degrades global quality | **SPEC-AMENDMENT** | **R14 Regression Detection Invariant** (§ 7.2) — subset rerun that increases critical checks fires advisory + auto-surfaces "undo this tweak" in next option set. Plus `B-C3B-REGRESSION-DETECTION` proper filing for post-launch threshold calibration. |
| 7 | Negotiation loop fatigue | **BACKLOG** | `B-C3B-GRADUATED-FINALIZATION-NUDGES` filed § 9.2 — iteration cap is hard stop; graduated nudges are v1.x UX work. |
| 8 | Preferences are mostly explicit, not implicit/emotional | **NO ACTION (already filed)** | `B-C3B-LLM-DRIVEN-TWEAK-GENERATION` (v0.1 backlog) already covers this. |
| 9 | C3b is UI-sensitive | **BACKLOG** | `B-C3B-DOWNSTREAM-RENDERER-BEHAVIORAL-CONTRACT` filed § 9.2 — mirrors C17 v0.3 precedent. |
| 10 | Users struggle with multi-dimensional tradeoffs | **BACKLOG** | `B-C3B-TRADEOFF-COMMUNICATION-DESIGN` filed § 9.2. |
| **11** | Temporal ownership / version lineage | **SPEC-AMENDMENT (small)** | **R16 Version Authority Invariant** (§ 7.4) + § 2.1 single-linear-history clarifying note. Plus `B-C3B-MUTATION-LINEAGE-AND-BRANCHING` for v1.x branching. |
| 12 | Praise: first-class user intervention | **NO ACTION** | Captured by § 0.1 mission framing. |
| 13 | C3b may become most-used component | **BACKLOG** | `B-C3B-NEGOTIATION-OPERATING-SYSTEM-EVOLUTION` filed § 9.2 — long-term architectural awareness. |

**Totals:** 6 SPEC-AMENDMENTs + 4 new R-invariants (R13–R16) + 8 backlog
items + 3 NO ACTION = 13 of 13 verdicted.

### 11.1 — Honest meta-comment

The v0.1 critique was **substantive but disciplined.** Unlike the C17
v0.1 critique (12 SPEC-AMENDMENTs needed — major restructure), this
critique surfaced fewer but more architecturally significant issues:
4 of the 6 amendments are major architectural strengthenings (R13
topology invariance, per-instance severity, SubsetRerunRequest
formalization, R14 regression detection). These were genuine v0.1
defects, not philosophical refinements.

The reviewer's strongest insight (and worth recording): **"C3b is the
first component where human preference evolution becomes part of the
computational architecture itself."** This framing should govern future
C3b evolution — and is partly why R13/R14/R15/R16 collectively
emphasize *protecting the user from their own local-optimization
drift* (R14), *protecting topology integrity from accumulating tweaks*
(R13), *protecting tweak applies from each other* (R15), and
*protecting the session from version-state ambiguity* (R16).

C3b v0.1 → v0.2 added 4 R-invariants. C17 v0.1 → v0.2 added 6
R-invariants. Both are early-spec evolutions; later versions are
expected to add fewer.

---

## § 12 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK time per the C15/C16/C17 pattern.)

---

## § 13 — LOCK adjudication request (Rule 8)

**This document is C3b v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**

For Ramalingam to LOCK v0.2, please confirm:

1. **R13 Topology Invariance Invariant** (§ 7.1) — MEDIUM tweaks must
   preserve C5 topology classification; topology-altering tweaks
   auto-promote to HEAVY. Prevents shadow layout generation.
2. **R14 Regression Detection Invariant** (§ 7.2) — subset rerun that
   increases critical-tier checks fires advisory + undo option.
3. **R15 Multi-Tweak Compatibility Check** (§ 7.3) — pairwise
   compatibility assertions checked before every apply. v1.0 pairwise;
   v1.x N-way via backlog.
4. **R16 Version Authority Invariant** (§ 7.4) — single-linear-history
   in v1.0; branching is v1.x.
5. **Phase β step 4 reworked** (§ 3) — per-instance severity
   computation replaces static category lookup.
6. **`SubsetRerunRequest` formalized** (§ 2.4.1) — mandatory
   `downstream_impact_set`; orchestrator contract becomes formal.
7. **§ 2.8 `MutationEnvelope`** (NEW) — structured user-facing
   communication for HEAVY rejections.
8. **§ 9.2 8 new backlog items** — all filed.
9. **§ 11 13/13 critique-walk verdicts** — audit trail complete.

If yes to all: **state "C3b v0.2 LOCKED"** OR (more likely given the
scale of changes): **run another critique walk** before LOCK.

If corrections needed: state which sections need patches; I'll
compose v0.3 PROPOSED.

**Convergence projection:**

| Round | Patches | Backlog | Status |
|---|---|---|---|
| v0.1 critique → v0.2 | 6 SPEC-AMENDMENTs (4 major + 2 small) | 8 | This document |
| v0.2 critique (if any) | predicted 2–4 SPEC-AMENDMENTs | ≤ 4 | Expected v0.3 |
| v0.3 critique | predicted 0–1 | ≤ 2 | LOCK candidate |

Following the C17 trajectory pattern (12 → 4 → 0 amendments across 3
rounds), C3b should LOCK around v0.3. v0.2 is unlikely to LOCK
directly — there are still likely to be a few more architectural
refinements as the spec converges.

---

**END OF C3b v0.2 PROPOSED — PENDING Ramalingam LOCK**
