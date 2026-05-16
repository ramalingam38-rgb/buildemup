# C3b — Post-Layout Trade-off Negotiation
## Spec v0.1 PROPOSED — Pending Ramalingam LOCK adjudication

**Status:** v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication (Rule 8).
**Session:** S50 close.
**Authoritative sources:**
- `MASTER_DESIGN_NARRATIVE_v2_9.md` § 8.2 "Component 3b — Post-Layout
  Trade-off Negotiation — DEFERRED" + § 5.3 parent Component 3 description
- `BuildemUp_Architecture_v3.md` § 13 data-flow diagram
- `buildemup_C3a_SPEC_v0_2_1a_LOCKED.md` § 10 "What's NOT in scope"
  cross-reference
- `BuildemUp_Design_Principles_v3_1.md` Principles 1 (experience-driven),
  3 (advisory tone), 4 (user intervention checkpoints)
**Predecessor:** none — C3b is greenfield, no v0.0 baseline.

> **Per Rule 8:** LOCK authority belongs to Ramalingam alone. This document
> is PROPOSED only.

> **Per Rule 9.4:** Critiques arriving between PROPOSED and LOCK remain
> patch-eligible.

---

## § 0 — Composition rationale

C3b is the **final unbuilt sub-component** in Track 3 canonical
(positions 1–17, with positions 3 and 11 each split into a/b
sub-components = 19 sub-components total). C3a was LOCKED at v0.2.1
(Session 17 era); C3b was deliberately deferred per master narrative:
*"Cannot be built before layouts can be generated."*

C16 v1.2 LOCKED at S49 close and C17 v0.3 LOCKED at S50 close. The
layout pipeline now exists end-to-end. C3b is dependency-unblocked.

### 0.1 — Mission framing

**C3b's purpose:** Once the user has seen the three ranked layouts
(Cost Efficient / Everyday Living / Premium Design from C15 Ranker),
**surface specific, layout-grounded tweaks** that the user might want
to apply before committing to one layout — and re-run the appropriate
subset of the pipeline to reflect those tweaks.

**C3b is NOT a layout regenerator.** It is a **user-driven mutation
negotiation layer** that operates on existing layouts. It takes the
problems C15 already identified, translates them into actionable
tweaks the user can accept or reject, and emits mutation requests
that selected downstream components honor.

**C3b inherits and applies Design Principles v3.1 Principle 4 (user
intervention checkpoints)** — the third explicit checkpoint, after
Topology Selection (Principle 4 ckpt 1) and Room Sizing (Principle 4
ckpt 2). C3b IS the post-layout checkpoint.

**C3b is bigger in scope than C3a.** C3a had 10 fixed Extreme Cases
operating on the brief. C3b operates on geometry — there are
indefinitely many situational tweaks possible, so C3b must use
**bounded tweak generation** (max N tweaks per layout) rather than
exhaustive case enumeration.

---

## § 1 — Scope

C3b consumes:
1. **SelectionResult** from C15 (3 ranked layouts: Cost Efficient,
   Everyday Living, Premium Design; the same structure C16 consumes)
2. **ProblemReport** per layout from C15 (the 30+ check problems C15
   identified per layout)
3. **Brief / ResolvedBrief** from C1 / C3a (for context — what the user
   originally wanted vs what they got)
4. **PlotAnalysis** from C4 (for orientation / climate / setback context)

C3b produces:
- A **`TradeoffSession`** — multi-turn, persistent, resumable session
  state (same SQLite + WAL pattern as C3a's `GateStateStorage` per
  Rule shared with C3a)
- Per layout, a **`TweakOptionSet`** — 3–6 specific tweak suggestions
  grounded in that layout's geometry + problems
- A **`ResolvedSelection`** — the final user choice of which layout +
  which tweaks they accept; this is what feeds forward into C16 Dual-
  Drawing Renderer

### 1.1 — What C3b IS

- A **structured-data emitter** producing tweak options, session
  state, and final user selection (no pixels, no UI — same scope
  discipline as C16 / C17 LOCKED)
- A **multi-turn user-facing flow** (similar to C3a's flow — present
  options → user picks → apply → re-evaluate → loop OR finalize)
- An **advisory layer** (Principle 3): tweaks are framed as
  *"You could do X — here's what changes if you do"* — NEVER
  *"You should do X"* or *"X is better"*
- **Layout-grounded:** every tweak references specific room IDs,
  wall IDs, door IDs, or structural grid cells from C12 / C13 / C7
  outputs. No free-floating suggestions.
- **Cost-transparent** (Principle 2 — Transparency Triple): every
  tweak's cost impact + space impact + comfort impact is range +
  midpoint + derivation

### 1.2 — What C3b IS NOT (scope boundary)

| Concern | C3b emits | Other component handles |
|---|---|---|
| Layout regeneration | mutation requests, not layouts | C11a (topology) / C11b (NSGA-II) / C12 (placement) |
| Topology change | NOT in scope — kicks back to C3a | C5 / C11a |
| Brief change | NOT in scope — kicks back to C3a | C3a |
| Structural redesign | NOT in scope — kicks back to brief | C7 |
| Layout problem detection | reads C15's ProblemReport — does not re-detect | C15 |
| Layout ranking | reads C15's SelectionResult — does not re-rank | C15 |
| Drawing rendering | passes selected layout forward | C16 |
| Quote comparison | passes selected layout forward | C17 |
| Multi-floor coordination | tweaks only within a floor; cross-floor tweaks marked HEAVY and rejected | C12 |
| Real-time UI | structured session state only | downstream frontend |

### 1.3 — Scope test (Design Principles v3.1 § 2)

C3b closes the **Emotional asymmetry** — gives the user explicit
agency over the final layout. Without C3b, the user is presented
with 3 take-it-or-leave-it layouts; with C3b, the user has a
structured way to ask *"can we change this one thing?"* before
committing.

### 1.4 — Applicability boundary (per C17 v0.3 § 1.4 precedent)

C3b v1.0 is designed for:
- Standard residential layouts that completed the full C4–C15 pipeline
  successfully (no Preview Mode, no Extreme Case unresolved)
- Multi-floor or single-floor layouts where C12 vertical alignment
  succeeded
- Layouts where C15's `ProblemReport` is `high_signal` or `moderate_signal`
  confidence (per C15 v1.0 LOCKED)

C3b v1.0 is NOT designed for (heuristic detection routes to
`requires_layout_regeneration`):
- Layouts produced under Preview Mode (per C3a) — C3b refuses to
  iterate on Preview Mode layouts; user must resolve the Extreme
  Case first
- Layouts where C15's `ProblemReport.overall_report_tier == "high_ambiguity"`
  — too much uncertainty in problems makes tweak generation unreliable
- Layouts where the 3 ranked options are too similar (Pareto-front
  collapse — see § 6 hard ceiling on diversity)

---

## § 2 — Output contract

C3b emits three top-level types. All fields canonically ordered for
replay determinism (R-inheritance from C16 LOCKED pattern).

### 2.1 — `TradeoffSession` (the session-state container)

```
TradeoffSession
├── session_id:                      str (uuid4)
├── source_selection_result_id:      str   (from C15)
├── source_brief_signature:          str   (from C1)
├── source_plot_analysis_id:         str   (from C4)
├── c3b_version:                     str   ("v0.1.PROPOSED")
├── c3b_schema_version:              int   (1)
├── jurisdiction_profile_id:         str
│
├── tweak_option_sets:               tuple[TweakOptionSet, ...]
│       One per layout (3 total: Cost Efficient, Everyday Living,
│       Premium Design). lex-ASC sort by layout_id.
│
├── session_history:                 tuple[SessionTurn, ...]
│       Each turn: which tweak presented, user response, apply
│       outcome. Append-only. Per Rule 9 (Q3 Level B logging from
│       C3a precedent).
│
├── iteration_count:                 int  (0-indexed)
├── iteration_cap:                   int  (default 5, hard ceiling 7)
│
├── current_status:                  Literal[
│       "open_for_user_input",
│       "awaiting_subset_rerun",
│       "resolved_selection_ready",
│       "kicked_back_to_c3a",       # heavy tweak requires brief change
│       "abandoned_no_tweaks",       # user accepts a layout as-is
│       "iteration_cap_reached",
│   ]
│
├── resolved_selection:              ResolvedSelection | None
│       Populated only when current_status == "resolved_selection_ready"
│
├── advisory_flags:                  tuple[AdvisoryFlag, ...]
│       R8 inheritance from C13/C14/C16
│
├── canonical_replay_signature:      str
├── presentation_signature:          str
└── schema_descriptor_digest:        str
```

### 2.2 — `TweakOptionSet` (per-layout tweak suggestions)

```
TweakOptionSet
├── layout_id:                       str   (from C15's SelectionResult)
├── layout_archetype:                Literal[
│       "cost_efficient",
│       "everyday_living",
│       "premium_design",
│   ]
├── source_problem_report_id:        str   (from C15)
│
├── tweaks:                          tuple[TweakOption, ...]
│       3–6 specific tweaks. lex-ASC sort by tweak_id. Hard ceiling 8
│       per layout (see § 6).
│
├── tweak_generation_provenance:     tuple[CheckProvenance, ...]
│       Per R-NEW — every tweak traces back to which ProblemReport
│       check OR which structural grid cell motivated it
│
└── overall_advisory_note:           str
        Per Principle 3: advisory framing of the option set.
        e.g. "Layout A (Cost Efficient) has 3 tweaks that could
              improve comfort with small cost adjustments, and 1
              tweak that's more substantial. None are required."
```

### 2.3 — `TweakOption` (the user-facing unit)

```
TweakOption
├── tweak_id:                        str   (canonical)
├── tweak_category:                  Literal[
│       "room_swap",                # swap two room functions within bay
│       "room_resize",              # resize within existing structural grid
│       "balcony_add",              # add balcony (carves from interior)
│       "balcony_remove",           # remove balcony (gives back interior)
│       "door_relocate",            # move door to different wall
│       "window_resize",            # enlarge/shrink window opening
│       "wet_zone_restage",         # move bath/kitchen to align stacks (calls C10)
│       "finish_upgrade",           # finish-schedule change (calls C16)
│       "finish_downgrade",         # finish-schedule change (calls C16)
│       "storage_add",              # add closet/utility (carves from room)
│       "pooja_relocate",           # move pooja per Vastu/climate
│       "kitchen_reorient",         # rotate kitchen for ventilation
│       "utility_zone_carveout",    # add laundry / storage from corridor
│   ]
│
├── severity_tier:                   Literal["light", "medium", "heavy"]
│       LIGHT  → no pipeline rerun; mutation applied directly to layout
│                geometry + finish schedule (e.g. finish change, door swap)
│       MEDIUM → partial pipeline rerun (C9 sizer + C12 placement OR
│                C10 wet-zone restage + C13 doors)
│       HEAVY  → rejected at tweak-generation time; would require
│                topology change (C11a) OR brief change (C3a) — never
│                surfaced as user-acceptable
│
├── affected_room_ids:               tuple[str, ...]
│       Room IDs from C12's PlacedRoom outputs that this tweak modifies
│
├── affected_grid_cells:             tuple[str, ...]
│       Structural grid cell IDs from C7 that this tweak modifies
│       (empty for pure finish/door tweaks)
│
├── description:                     str
│       Plain-English description per Principle 1 (talks to user, not
│       engine). Advisory tone per Principle 3.
│       e.g. "Move the kitchen to the east wall — currently it's
│             on the north wall with low morning light. East gives
│             you direct morning sun, slightly better cross-ventilation,
│             and aligns the cooking area with traditional Vastu
│             (if you care about Vastu, which is opt-in)."
│
├── cost_impact:                     TransparencyTriple
│       Range + midpoint + derivation, in ₹. Can be negative (savings).
│       Confidence per § 2.10 (HIGH for finish changes, MEDIUM for
│       structural-bay-respecting tweaks, LOW for layout-mutating ones)
│
├── space_impact:                    SpaceImpact
│       Per-room sqft delta + total sqft delta + advisory note
│
├── comfort_impact:                  ComfortImpact
│       Qualitative: better natural light / better ventilation /
│       reduced privacy / etc. Tied to specific ProblemReport checks
│       this tweak would resolve or worsen.
│
├── problem_report_links:            tuple[str, ...]
│       Which C15 ProblemReport check IDs this tweak addresses
│
├── recommendation_flag:             Literal[
│       "suggested",      # tweak resolves a critical/important problem
│       "optional",       # tweak addresses a minor problem
│       "alternative",    # tweak is a stylistic/preference choice
│   ]
│       Per Principle 3: NEVER "recommended" / "you should." The
│       flag is a structural marker, not a verdict.
│
├── apply_specification:             ApplySpecification
│       The structured mutation that downstream components honor
│       when this tweak is accepted.
│
└── provenance:                      CheckProvenance
```

### 2.4 — `ApplySpecification` (the structured mutation)

```
ApplySpecification
├── mutation_kind:                   Literal[
│       "geometry_local",            # LIGHT tier — applied to layout in-place
│       "subset_rerun",              # MEDIUM tier — emits SubsetRerunRequest
│       "finish_schedule_only",      # LIGHT tier — modifies C16 schedule only
│   ]
├── geometry_local_payload:          GeometryLocalPayload | None
│       For "geometry_local": which rooms swap, which door moves where,
│       resulting new RoomPlacement / DoorPlacement.
├── subset_rerun_payload:            SubsetRerunPayload | None
│       For "subset_rerun": which components must re-run, with what
│       parameters. e.g. {"components": ["c10", "c12", "c13"],
│                          "anchor": "wet_zone_eastward"}
└── finish_schedule_payload:         FinishSchedulePayload | None
        For "finish_schedule_only": which rooms get which finish change.
        Feeds directly to C16's WorkingDrawingModel.finish_schedule.
```

### 2.5 — `SessionTurn` (audit log per Q3 Level B inheritance from C3a)

```
SessionTurn
├── turn_id:                         str
├── iteration_index:                 int   (0-indexed, same as iteration_count)
├── timestamp_offset_ms:             int   (relative to session_id creation; R7d no-time)
├── presented_tweaks:                tuple[str, ...]   # tweak_ids shown to user
├── user_action:                     Literal[
│       "accepted_tweak",
│       "rejected_tweak",
│       "no_action_continue",
│       "finalized_layout_choice",
│       "kicked_back_to_c3a",
│       "abandoned_session",
│   ]
├── chosen_tweak_id:                 str | None
├── apply_outcome:                   ApplyOutcome | None
│       For "accepted_tweak" — what happened after apply
│       (geometry_local applied / subset_rerun queued / failed)
└── post_turn_status:                str   (matches TradeoffSession.current_status)
```

### 2.6 — `ResolvedSelection` (the final output to C16)

```
ResolvedSelection
├── chosen_layout_id:                str
├── chosen_layout_archetype:         Literal[
│       "cost_efficient",
│       "everyday_living",
│       "premium_design",
│   ]
├── applied_tweaks:                  tuple[str, ...]   # tweak_ids
├── final_layout_signature:          str               # post-tweak layout hash
├── final_problem_report_id:         str | None
│       If MEDIUM tweaks were applied, this is the re-run C15
│       ProblemReport ID. If only LIGHT tweaks (or none), inherits
│       original C15 ProblemReport.
├── total_cost_delta:                TransparencyTriple
│       Sum of applied tweaks' cost impacts
├── total_space_delta:               SpaceImpact
└── final_handoff_advisory:          str
        Plain-English summary for the user before C16 renders.
        e.g. "You picked the Everyday Living layout with 2 tweaks:
              kitchen moved east (small cost saving), powder room
              added near entry (₹35K addition). Total: ₹15K saving
              vs original Everyday Living. We'll generate the
              working and regulatory drawings now."
```

### 2.7 — Supporting types (`SpaceImpact`, `ComfortImpact`, `ApplyOutcome`)

```
SpaceImpact
├── per_room_sqft_delta:             tuple[tuple[str, float], ...]
│       (room_id, sqft_delta) — lex-ASC by room_id
├── total_sqft_delta:                float
├── total_carpet_area_after:         AttestedValue (LOCALLY_DERIVED)
└── advisory_note:                   str

ComfortImpact
├── dimensions_affected:             tuple[Literal[
│       "natural_light",
│       "cross_ventilation",
│       "privacy",
│       "noise_isolation",
│       "circulation_efficiency",
│       "outdoor_connection",
│       "storage_capacity",
│       "vastu_alignment_opt_in",
│       "fire_egress",
│       "accessibility",
│   ], ...]
├── direction:                       Literal["improves", "worsens", "mixed"]
├── magnitude:                       Literal["small", "moderate", "significant"]
└── advisory_note:                   str

ApplyOutcome
├── apply_status:                    Literal[
│       "applied_successfully",
│       "rerun_queued",
│       "rerun_failed",
│       "rejected_constraint_violation",
│   ]
├── error_summary:                   str | None
├── new_layout_signature:            str | None
└── new_problem_report_id:           str | None
```

---

## § 3 — Phase pipeline

C3b uses the same 6-phase α–ζ pattern as C16 / C17 LOCKED for uniformity.

### Phase α — Session canonicalization + applicability check

INPUT: SelectionResult (from C15), Brief, PlotAnalysis.
PROCESSING:
1. Validate `SelectionResult.layouts` is exactly 3 (Cost Efficient,
   Everyday Living, Premium Design).
2. Check § 1.4 applicability boundary: Preview Mode? high_ambiguity
   ProblemReport? Pareto collapse?
3. If any applicability check fails → emit `TradeoffSession` with
   `current_status = "abandoned_no_tweaks"` and an explicit advisory
   note explaining why C3b can't iterate.
4. Otherwise → build canonical `TradeoffSession` skeleton with `iteration_count = 0`.

OUTPUT: `TradeoffSession` (skeleton) OR early-exit.

### Phase β — Tweak generation per layout

INPUT: 3 layouts, 3 ProblemReports, PlotAnalysis.
PROCESSING (per layout, in parallel logical order):
1. **Read ProblemReport.** Find checks marked `severity in {critical,
   important}` that have a known tweak pattern (e.g.,
   "shower_length_below_minimum" → suggests `room_resize` or
   `door_relocate`).
2. **Read structural grid (C7 output via C16's `geometry_ref`).** Find
   grid cells that are under-utilized (e.g., corridor wider than
   necessary) — suggest `utility_zone_carveout`.
3. **Read orientation (C4 PlotAnalysis).** Find rooms whose function
   doesn't match orientation (e.g., kitchen on north wall in Chennai)
   — suggest `kitchen_reorient`.
4. **Apply severity filter:** classify each candidate tweak as LIGHT,
   MEDIUM, or HEAVY. HEAVY tweaks are NOT surfaced (would require
   topology change or brief change).
5. **Bounded selection:** if more than 6 candidate tweaks remain,
   prioritize by (a) tweak addresses critical problem, (b) tweak is
   LIGHT severity, (c) tweak's recommendation_flag is "suggested."
   Max 6 surfaced per layout.
6. **Per Principle 1:** generate plain-English `description` for each
   tweak. Per Principle 3: advisory tone, banned-phrase lint.

OUTPUT: 3 `TweakOptionSet`s (one per layout).

### Phase γ — Cost + space + comfort impact computation

INPUT: tweaks from Phase β, RateProvider, layout geometry.
PROCESSING (per tweak):
1. **Cost impact:** delegate to C7 cost estimator (for structural-bay
   changes) + RateProvider (for finish changes) + C10 (for wet-zone
   restage cost). Output: `TransparencyTriple`.
2. **Space impact:** compute per-room sqft delta from `ApplySpecification`
   geometry payload.
3. **Comfort impact:** map tweak → `ComfortImpact` via the affected
   `ProblemReport` checks (a tweak that resolves
   "kitchen_north_facing_low_light" → improves natural_light).
4. **Recommendation flag:** "suggested" if tweak resolves
   critical+important check; "optional" for minor checks; "alternative"
   for stylistic preferences.

OUTPUT: `TweakOptionSet`s populated with full impact data.

### Phase δ — User-facing presentation rendering

INPUT: full `TradeoffSession` with populated tweaks.
PROCESSING:
1. Lex-ASC sort within each `TweakOptionSet.tweaks` by `tweak_id`.
2. Set `TradeoffSession.current_status = "open_for_user_input"`.
3. Compute `canonical_replay_signature` (R6 inheritance — byte-equal
   on replay), `presentation_signature` (R7 — canonical as prefix),
   `schema_descriptor_digest` (R8 inheritance).
4. Persist session to SQLite (WAL mode, per S6 ownership inheritance
   from C3a precedent).

OUTPUT: `TradeoffSession` ready for downstream UI consumption.

### Phase ε — User-turn handling (called on each user response)

INPUT: `TradeoffSession` + `UserAction` (accept / reject / finalize / abandon).
PROCESSING:
1. Validate `chosen_tweak_id` is in current presented set (per Q3
   Level B logging inheritance — chosen must be in presented).
2. Append `SessionTurn` to `session_history`.
3. **Branch on `user_action`:**
   - `accepted_tweak` LIGHT → apply mutation in-place to layout
     geometry / finish schedule, regenerate `TweakOptionSet` for that
     layout (some old tweaks may no longer apply; some new ones may
     emerge), increment `iteration_count`, return updated session.
   - `accepted_tweak` MEDIUM → emit `SubsetRerunRequest` to
     orchestrator (C9 / C10 / C12 / C13 subset), set
     `current_status = "awaiting_subset_rerun"`. Caller invokes rerun
     orchestrator; on completion, calls back into C3b with new
     SelectionResult, which restarts at Phase β with `iteration_count + 1`.
   - `accepted_tweak` HEAVY → should not occur (HEAVY tweaks are not
     surfaced); if it does, `LocalTradeoffError`.
   - `rejected_tweak` → no mutation; tweak retained in option set with
     `presented_count` incremented (don't re-suggest same tweak more
     than 2× per session).
   - `no_action_continue` → no mutation; iteration_count stays.
   - `finalized_layout_choice` → construct `ResolvedSelection`, set
     `current_status = "resolved_selection_ready"`. Session complete.
   - `kicked_back_to_c3a` → set `current_status = "kicked_back_to_c3a"`.
     C3a is re-invoked with the current ResolvedBrief plus a `KickbackContext`
     describing why C3b decided the user's tweak request needed brief change.
   - `abandoned_session` → set `current_status = "abandoned_no_tweaks"`,
     `resolved_selection` populated with the user's original layout
     choice and zero applied tweaks.
4. **Iteration cap:** if `iteration_count >= iteration_cap` (default 5,
   hard ceiling 7), force `current_status = "iteration_cap_reached"`
   with advisory: *"You've explored 5 tweak rounds. You can finalize
   one of these layouts now, or step back to your brief if you want
   to change the project scope."* Per Principle 3.

OUTPUT: updated `TradeoffSession`.

### Phase ζ — Resolution + handoff signing

INPUT: `TradeoffSession` in `"resolved_selection_ready"` state.
PROCESSING:
1. Compute `ResolvedSelection.final_layout_signature` (post-tweak hash).
2. If MEDIUM tweaks applied, fetch the re-run `ProblemReport`'s ID
   into `final_problem_report_id`.
3. Sum `cost_impact`s across applied tweaks → `total_cost_delta`.
4. Sum `space_impact`s → `total_space_delta`.
5. Generate `final_handoff_advisory` (plain-English summary).
6. Compute final `canonical_replay_signature` (R6), `presentation_signature`
   (R7), `schema_descriptor_digest` (R8).

OUTPUT: `TradeoffSession.resolved_selection` populated; session
ready for C16 Dual-Drawing Renderer to consume.

---

## § 4 — Error tiers (mirrors C16 / C17 LOCKED two-tier hierarchy)

### 4.1 — `LocalTradeoffError` (always halts)
- `UpstreamSchemaDriftError` — SelectionResult doesn't match C15 v1.0 LOCKED schema
- `C3bConfigurationError` — bad jurisdiction / iteration cap config
- `ApplicabilityBoundaryError` — layouts fail § 1.4 (Preview Mode / high_ambiguity)
- `SessionPersistenceError` — SQLite WAL write failure (inherits S6 BriefStorage hardening)
- `SubsetRerunOrchestrationError` — orchestrator rerun failed; session enters terminal `"abandoned_no_tweaks"` state with explicit advisory

### 4.2 — `PerTweakError` (STRICT raises / WARN collects)
- `TweakGenerationError` — can't generate a candidate for a problem-report check
- `ImpactComputationError` — cost / space / comfort impact computation failed (e.g., RateProvider lookup failed for the wet-zone restage)
- `ConstraintViolationError` — apply would violate a hard constraint (e.g., NBC minimum bath area) — tweak is removed from option set BEFORE surfacing to user
- `RecommendationFlagAmbiguityError` — can't classify a tweak as suggested/optional/alternative

---

## § 5 — Versioning

```python
C3B_VERSION = "v0.1.PROPOSED"
C3B_SESSION_SCHEMA_VERSION = 1
C3B_IDENTITY_GENERATION = 1

SUPPORTED_JURISDICTIONS = {"tn_cdbr_2019"}
SUPPORTED_DOMAIN_SCOPES = {"residential_v1"}

EXPECTED_C15_VERSION = "v1.0.LOCKED"
EXPECTED_C16_VERSION = "v0.5.LOCKED"   # runtime; spec v1.2 LOCKED
EXPECTED_C7_VERSION  = "v0.8.LOCKED"
EXPECTED_C12_VERSION = "v1.0.LOCKED"
EXPECTED_C13_VERSION = "v1.0.LOCKED"

ITERATION_CAP_DEFAULT = 5
ITERATION_CAP_HARD_CEILING = 7
MAX_TWEAKS_PER_LAYOUT = 6
MAX_REPRESENT_COUNT = 2    # how many times a single rejected tweak can be re-surfaced
```

R9 inheritance from C15/C16/C17: ADDITIVE field bumps SCHEMA_VERSION
MINOR; removal/rename requires MAJOR.

---

## § 6 — Hard ceilings

| Field | Hard ceiling | Rationale |
|---|---|---|
| `TweakOptionSet.tweaks` per layout | 6 | Choice paralysis threshold per UX research; aligns with C3a's option-count discipline |
| Iteration count per session | 7 | Session ends and forces finalization |
| `MAX_REPRESENT_COUNT` | 2 | Don't re-suggest a rejected tweak more than twice |
| `SessionTurn.session_history` length | 50 | Defensive ceiling; iteration cap of 7 normally bounds this |
| Cost impact magnitude | ±₹20 lakh per tweak | A tweak that exceeds this is not a "tweak" — it's a brief change; force kick-back to C3a |
| Space impact magnitude | ±150 sqft per tweak | Same rationale — bigger changes are brief-level, not layout-level |
| Pareto-diversity floor for applicability | layouts must differ by ≥ 10% sqft OR ≥ 15% cost OR ≥ 3 different topology selections | If 3 layouts are too similar, C3b refuses to iterate (§ 1.4) |

Hard ceilings raise `LocalTradeoffError`; never silently truncated.

---

## § 7 — R-invariants (initial set — 12)

C3b inherits the C16/C17 LOCKED invariant patterns (R6 byte-equal
replay, R7 canonical as prefix, R8 public schema versioning, etc.).
Initial v0.1 invariant set:

| Invariant | Statement |
|---|---|
| **R1** | Every numeric output wrapped in `AttestedValue` (R22 inheritance from C16) — cost_impact, space_impact deltas, etc. |
| **R2** | Every `description`, `advisory_note`, `final_handoff_advisory` string MUST pass advisory-tone lint. Banned-phrase list inherits from C17 v0.3 R2 (no "should", "must do", "wrong choice", "better", "worse", "bad", "problem", "fix") — replaced with "could", "may", "consider", "alternative", "different result" |
| **R3** | Layout grounding (NEW for C3b) — every `TweakOption.affected_room_ids` and `affected_grid_cells` MUST reference valid IDs in the upstream SelectionResult. No free-floating tweaks. |
| **R4** | Severity tier discipline — LIGHT tweaks NEVER trigger pipeline rerun; MEDIUM tweaks ALWAYS trigger subset rerun; HEAVY tweaks are NEVER surfaced (filtered at Phase β step 4) |
| **R5** | Recommendation flag is structural, not authoritative — `"suggested"` means *tweak resolves a critical/important ProblemReport check*, NOT *Claude thinks you should do this* |
| **R6** | `canonical_replay_signature` byte-equal on replay (R7 inheritance from C16) — given same SelectionResult + same Brief + same PlotAnalysis + same iteration-count + same user-action-sequence, byte-equal session |
| **R7** | `presentation_signature` has canonical as prefix (R32a inheritance) |
| **R8** | `TradeoffSession` schema is public versioned API (R37 inheritance) — MINOR additive, MAJOR breaking, deprecation policy applies |
| **R9** | Architectural primacy (R36 inheritance) — every tweak MUST attach to a building element (room, wall, door, grid cell). No "abstract" tweaks (e.g., "improve flow" without specifying which rooms/doors) |
| **R10** | Semantic compression discipline (R39 inheritance from C16) — new fields on `TweakOption` MUST justify themselves against geometry-grounding OR replay determinism OR Principle 2 transparency. No free-floating metadata. |
| **R11** | Determinism boundary (R35 inheritance) — same upstream inputs + same user-action-sequence → byte-equal session replay |
| **R12** | Q3 Level B logging discipline (inherited from C3a v0.2.1) — every `SessionTurn.presented_tweaks` records the FULL option set the user saw, not just what they chose. Audit trail is reproducible. |

### 7.1 — Advisory-tone template (R2 enforcement reference)

The `description`, `advisory_note`, `final_handoff_advisory` strings
are generated from templates with banned-phrase lint:

**Allowed phrasings:**
- "You could move the kitchen to the east wall — this would give
  you direct morning light and may improve cross-ventilation."
- "This tweak would add a powder room near the entry. Cost impact:
  ~₹30K–₹40K. Space impact: takes ~25 sqft from the corridor."
- "An alternative: keep the layout as-is. The current placement is
  workable; this tweak is optional."

**Banned phrasings (R2 lint):**
- "should", "must", "ought to", "need to", "have to"
- "better", "worse", "wrong", "right choice"
- "bad", "problem", "fix" (use "consideration", "tweak", "address")
- "recommend", "recommend you" (the `recommendation_flag` enum carries
  the signal structurally; user-facing text doesn't reinforce it)

---

## § 8 — Upstream dependencies

| Dependency | Locked version | Used for |
|---|---|---|
| C15 (Layout Problem Finder) | v1.0 LOCKED | SelectionResult (3 ranked layouts), ProblemReport per layout |
| C16 (Dual-Drawing Renderer) | v1.2 LOCKED | downstream consumer of ResolvedSelection |
| C7 (Structural Grid) | v0.8 LOCKED | grid cells, structural cost estimator for tweak cost impact |
| C12 (Vertical Alignment / Placement) | v1.0 LOCKED | PlacedRoom IDs, geometry for tweak grounding |
| C13 (Door Placement) | v1.0 LOCKED | Door IDs for door_relocate tweaks |
| C10 (Wet-Zone Stack Planner) | LOCKED | wet-zone restage subset rerun |
| C4 (Plot Analysis) | LOCKED | orientation, climate context for kitchen_reorient / pooja_relocate tweaks |
| C3a (Extreme Case Gate) | v0.2.1 LOCKED | kick-back target when HEAVY tweak detected |
| `RateProvider` (utility) | concrete impls | cost impact derivation |
| `TransparencyTriple` (utility) | existing | cost_impact format |
| `AttestedValue` (from C16 contracts) | LOCKED | provenance discipline |
| Session storage (SQLite WAL) | inherits S6 ownership pattern from C3a | persistent multi-turn session |

**Subset-rerun orchestrator** — for MEDIUM tweaks, C3b emits a
`SubsetRerunRequest` that an external orchestrator handles. The
orchestrator is OUT OF SCOPE for C3b itself; C3b only emits the
structured request. This is the same pattern as C17 v0.3 excluding
the OCR parser.

---

## § 9 — Backlog (initial — Rule 9)

### 9.1 — v1.0 LOCK-mandatory (must close before LOCK)

| ID | Description | Effort |
|---|---|---|
| `B-C3B-PHASE-IMPLEMENTATIONS` | Implement all 6 phases (α–ζ) | L |
| `B-C3B-TEST-COVERAGE-PARITY` | ≥180 tests across phases + orchestrator + PBT layer ≥15 + 5-scenario adversarial corpus + Q3 Level B audit replay | L |
| `B-C3B-SUBSET-RERUN-ORCHESTRATOR-CONTRACT` | Define the SubsetRerunRequest schema + orchestrator API; ensure C9/C10/C12/C13 can be invoked as a subset (without re-running the whole pipeline) | M |
| `B-C3B-ADVISORY-TONE-LINT` | Automated lint of all user-facing strings (R2 enforcement) against expanded banned-phrase list | S |
| `B-C3B-TWEAK-GENERATION-COVERAGE-CALIBRATION` | Test corpus of 20+ real layouts × ProblemReports with known applicable tweaks; ensure generation finds ≥80% of obvious tweaks | M |
| `B-C3B-SESSION-PERSISTENCE-WAL-RETROFIT` | SQLite WAL mode + retry + corruption recovery, mirroring C3a's GateStateStorage hardening | M |
| `B-C3B-Q3-LEVEL-B-AUDIT-REPLAY-TESTS` | Verify every SessionTurn's presented_tweaks record reproduces the chosen-from-presented invariant under replay | S |

### 9.2 — DEFERRED post-LOCK

| ID | Description | Trigger |
|---|---|---|
| `B-C3B-LLM-DRIVEN-TWEAK-GENERATION` | v2 enhancement — LLM proposes tweaks based on natural-language brief + layout, beyond rule-based pattern matching | v2 phase |
| `B-C3B-MULTI-CITY-TWEAK-PATTERNS` | City-specific tweak templates (Mumbai monsoon, Delhi heat, Bangalore moderate climate) | post-Chennai launch |
| `B-C3B-CROSS-FLOOR-TWEAKS` | Currently rejected as HEAVY; v1.x may surface cross-floor tweaks (e.g., "swap ground floor and first floor utility placements") with vertical-alignment-aware logic | v1.x |
| `B-C3B-EMPATHY-LAYER-V1X` | Per Principle 6 (emotional reassurance) — add reassurance lines ("families on similar plots often choose these tweaks") to each TweakOption | v1.x |
| `B-C3B-TWEAK-INTERACTION-DETECTION` | When two accepted tweaks conflict (e.g., user accepts both "kitchen east" and "pooja east" — only one corner) — surface and resolve | v1.x |
| `B-C3B-REPLAY-DIFFING-TOOL` | Tool that takes two session replays and surfaces what differed (useful for QA + user "what changed" trace) | v1.x |
| `B-C3B-LEGAL-REVIEW-PROCESS` | Same precedent as C17 — legal review of advisory language before first launch | Before launch |
| `B-C3B-BANDIT-TWEAK-PRIORITIZATION` | Post-launch: learn which tweaks users actually accept; prioritize Phase β surfacing accordingly (bandit + cold-start safety) | post-launch |

### 9.3 — Summary

| Category | Count |
|---|---|
| LOCK-mandatory | 7 |
| DEFERRED | 8 |
| **Total tracked** | **15** |

---

## § 10 — Test plan

Target at v1.0 LOCK:

| Test file | Count | Purpose |
|---|---|---|
| `test_c3b_versioning.py` | ~8 | constants, expected upstream versions |
| `test_c3b_errors.py` | ~15 | two-tier hierarchy |
| `test_c3b_contracts.py` | ~25 | output dataclass shapes + post_init validation |
| `test_c3b_phase_alpha.py` (canonicalization + applicability) | ~15 | Preview Mode rejection, high_ambiguity rejection, Pareto-collapse rejection, happy path |
| `test_c3b_phase_beta.py` (tweak generation) | ~30 | per-problem-check tweak patterns, severity filtering, bounded selection, kitchen-reorient, pooja-relocate, wet-zone-restage |
| `test_c3b_phase_gamma.py` (impact computation) | ~20 | cost/space/comfort impact derivation, recommendation flag classification |
| `test_c3b_phase_delta.py` (presentation) | ~10 | lex-ASC sort, signature determinism |
| `test_c3b_phase_epsilon.py` (user-turn handling) | ~25 | accept LIGHT / accept MEDIUM / reject / no-action / finalize / kickback / abandon / iteration-cap |
| `test_c3b_phase_zeta.py` (resolution) | ~10 | ResolvedSelection assembly, cost/space delta totals |
| `test_c3b_orchestrator.py` | ~15 | STRICT vs WARN, multi-turn flow, persistence + resume |
| `test_c3b_pbt.py` (PBT layer) | ~15 | property-based: signature determinism, severity-tier invariance, replay byte-equal |
| `test_c3b_adversarial_corpus.py` (5 scenarios) | ~10 | (1) Pareto-collapsed layouts, (2) all-HEAVY-needed tweaks, (3) user rejects everything, (4) iteration-cap reached, (5) subset rerun fails |
| `test_c3b_advisory_tone_lint.py` | ~10 | R2 enforcement — banned phrases caught |
| `test_c3b_q3_level_b_replay.py` | ~8 | audit invariant: chosen_tweak_id always in presented_tweaks |
| **Total** | **~210** | |

---

## § 11 — Critique walk readiness (Rule 7)

Initial critique-walk surfaces I'd expect, with pre-emptive notes:

| Likely critique | Pre-emptive position |
|---|---|
| "C3b is doing too much — split tweak generation, mutation application, session state into separate components?" | They're tightly coupled (the chosen tweak's apply spec must match the generator's assumptions). Splitting would create R3 violations. § 8's subset-rerun orchestrator is the natural seam — not internal C3b splits. |
| "Why does C3b need iteration_cap? Just let user iterate forever." | Per Principle 3 + Principle 4 — at iteration 5-7 the user is past tweak decisions and into scope changes. Force kick-back to C3a or finalize. Same discipline as C3a's iter cap. |
| "MEDIUM tweaks (subset rerun) — won't this make the system feel slow?" | Subset rerun is by definition a strict subset of C4-C16 (typically just C9 + C12 + C13, not C11a/C11b). Should be <5 sec. Test corpus must verify this empirically. |
| "Recommendation flag isn't actually used per Principle 3?" | Per § 2.3 / R5 — the flag is structural (which tweak resolves which severity of ProblemReport check), NOT authoritative. User-facing text never says "we recommend" — the flag is metadata for downstream graduated-disclosure rendering only. |
| "How does C3b handle the case where re-running C12 produces a layout that's now WORSE than the original (re-evaluation regression)?" | Phase ε branch: if subset_rerun produces a layout whose C15 ProblemReport has more critical-tier issues than the original, the orchestrator returns the rerun result with an `advisory_flag`, and C3b's next-turn presentation includes an "undo this tweak" option. Filed as `B-C3B-REGRESSION-DETECTION`. |
| "Why is kitchen_reorient a tweak category but bedroom_reorient is not?" | Kitchen has strong climate / Vastu / ventilation grounding; bedroom orientation is mostly user preference. v1.0 includes the clearly-rule-grounded tweaks; user-preference tweaks are v1.x via `B-C3B-LLM-DRIVEN-TWEAK-GENERATION`. |

---

## § 12 — Three-check protocol (Rule 10.6) — at LOCK time

(To be filled at LOCK time per the C15/C16/C17 pattern.)

---

## § 13 — LOCK adjudication request (Rule 8)

**This document is C3b v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**

C3b follows the same multi-round PROPOSED → critique → LOCK pattern
as C15 (3 rounds), C16 (3 rounds), and C17 (3 rounds). v0.1 LOCK is
unusual — typically a critique round produces v0.2 PROPOSED before
LOCK. The path I expect:

1. **You read v0.1 PROPOSED + run a critique walk.**
2. I respond with patches → **v0.2 PROPOSED** + per-point verdicts table.
3. Possibly another critique → **v0.3 PROPOSED** or directly LOCK.
4. **LOCK.** Then code begins per § 9.1 LOCK-mandatory backlog.

To LOCK v0.1 as-is (which would skip the critique round), confirm:

1. **§ 1 scope** — C3b IS post-layout user-driven tweak negotiation;
   C3b is NOT a layout regenerator, topology mutator, or brief changer.
2. **§ 1.4 applicability boundary** — C3b refuses to iterate on
   Preview Mode layouts, high_ambiguity ProblemReports, or Pareto-collapsed
   layout sets.
3. **§ 2 output contract** — `TradeoffSession` / `TweakOptionSet` /
   `TweakOption` / `ResolvedSelection` are the right shape.
4. **§ 2.3 13 tweak categories** — covers v1.0 tweak space without
   bleeding into topology / brief / structural territory.
5. **§ 2.3 three severity tiers** — LIGHT (no rerun) / MEDIUM (subset
   rerun) / HEAVY (rejected, kick-back to C3a) — correct partition.
6. **§ 3 6-phase pipeline** — α canonicalization → β tweak generation →
   γ impact computation → δ presentation → ε user-turn handling → ζ resolution.
7. **§ 7 invariants** — R1–R12 are correct as initial set.
8. **§ 8 upstream dependencies** — C15 (SelectionResult + ProblemReport),
   C16 (downstream), C7/C10/C12/C13 (subset rerun), C3a (kick-back target).
9. **§ 9 backlog** — 7 LOCK-mandatory + 8 deferred.

If yes to all: **state "C3b v0.1 LOCKED"** (unusual direct LOCK).

If corrections needed: state which sections need patches; I'll
compose v0.2 PROPOSED.

**My recommendation: do a critique walk first.** C3b v0.1 introduces
several genuinely-new architectural decisions (severity-tier
partition, subset-rerun orchestrator contract, recommendation-flag
discipline, kick-back-to-C3a pathway) that benefit from external
critique. Expect v0.2 or v0.3 before LOCK — same pattern as C17.

---

**END OF C3b v0.1 PROPOSED — PENDING Ramalingam LOCK**
