# Backlog additions — S52 C3b v0.4 BUILD critique walk

**Source:** S52 adversarial critique against BUILD PROPOSED (post-LOCK spec, pre-LOCK build)
**Rule 7 web search:** 1 search executed (generative floor plan diversity literature)
**Pattern D audit:** 4 items rejected/misframed before filing (pts 4, 9, 12, 13)
**Net additions:** 9 new B-NNN entries below

---

## v1.x candidates (7)

### B-C3B-FATIGUE-TELEMETRY-AND-COMPRESSION
**Origin:** S52 critique pt 1
**Description:** Add telemetry for interaction-duration, reversal-frequency, hesitation,
abandoned-comparison-cards. Once data exists, implement "decision compression":
merge multiple Phase β tweaks into themed bundles ("space-optimized" /
"budget-optimized" / "privacy-optimized") rather than presenting each tweak
individually.
**Trigger:** post-Chennai launch (need telemetry corpus first)
**v1.x scope:** instrumentation only; compression UX is later
**Effort:** S — 2 sessions for telemetry hooks; M — 3-4 sessions for compression UX
**Determinism note:** telemetry must NOT affect canonical_replay_signature

### B-C3B-CONTINUOUS-DIMENSION-DELTA-CHECK
**Origin:** S52 critique pt 2 (extends R14)
**Description:** R14 only catches CRITICAL-tier transitions on C15 ProblemReport.
Track *numeric* deltas on each C15 dimension (ventilation, daylight, circulation,
plumbing-efficiency, structural-complexity) and surface "this tweak degrades
ventilation by 18%" advisories even when no check fails outright.
**Trigger:** v1.x, after C15 emits per-dimension numeric scores
**Effort:** M
**Dependency:** C15 v1.x dimension-score emission

### B-C3B-SPECULATIVE-PREVIEW-MODE
**Origin:** S52 critique pt 5
**Description:** Currently, HEAVY tweaks immediately surface as MutationEnvelope
("step back to brief"). Add a `speculative_preview` mode: generate a quick
visual/textual preview of what the heavy change would look like *before* forcing
kick-back. Extends KickBackPayload schema with `preview_artifacts` field.
**Trigger:** v1.x
**Effort:** M — needs lightweight layout-preview pipeline

### B-C3B-SEMANTIC-COMPATIBILITY-CONTRACTS
**Origin:** S52 critique pt 6
**Description:** Replace strict EXPECTED_C15_VERSION == observed equality with
min-version-with-feature-flag pattern. Add adapter shims for backward-compatible
upstream evolution. Define semantic compatibility contracts per upstream
component (which fields C3b actually reads, which can drift).
**Trigger:** before C15 v1.1 ships
**Effort:** M — design + 1 implementation pass per upstream
**Risk if not done:** every C15/C16/C12 minor version bump breaks C3b

### B-C3B-EMOTIONAL-LAYOUT-HEURISTICS
**Origin:** S52 critique pt 7 (complements existing B-C3B-EMPATHY-LAYER-V1X)
**Description:** Beyond reassurance lines (the existing empathy backlog item),
add heuristic scoring for: perceived spaciousness, arrival impression sequence,
guest-prestige flow, family-gathering comfort. Use as soft signals in
TweakOption ranking + Phase ζ handoff advisory.
**Trigger:** v1.x
**Effort:** L — needs architect-reviewed corpus for heuristic calibration

### B-C3B-PERIODIC-FULL-COHERENCE-RECHECK
**Origin:** S52 critique pt 8
**Description:** Subset reruns optimize for speed but accumulate architectural
fragmentation. Add `full_recompute_threshold` config knob (default: every 3
MEDIUM tweaks). When crossed, force a full C12/C13/C14/C15 recompute and
surface coherence-drift advisory.
**Trigger:** v1.x — straightforward; mostly orchestrator work
**Effort:** S-M
**Determinism:** threshold must be in canonical_replay_signature input

### B-C3B-OSCILLATION-DETECTION-AND-SUMMARY
**Origin:** S52 critique pt 11
**Description:** Detect oscillation patterns in session_history (accept-then-
reject-then-accept of same category). Surface "you appear to be balancing X vs Y"
summaries with explicit compromise frontiers. Uses existing SessionTurn data;
no new infrastructure.
**Trigger:** v1.x
**Effort:** S — pattern detection + UI template

---

## v2 candidates (3)

### B-C3B-EXPERIENTIAL-DIVERSITY-FLOORS
**Origin:** S52 critique pt 3 + pt 15
**Description:** Current Pareto-diversity floors (cost-spread 15%, sqft-spread
10%) are geometric. Add experiential-diversity floors via latent embeddings of
human-perceived qualities (privacy, openness, family-interaction-rhythm).
**Web-research citation:** Mostafavi et al. 2025 (SAGE) confirms graph+
behavioral embeddings outperform geometric-only metrics for floor-plan diversity
assessment.
**Trigger:** v2 — requires ML corpus + behavioral simulation
**Effort:** XL — research project scale

### B-C3B-STRATEGIC-NEGOTIATION-LAYER
**Origin:** S52 critique pt 10
**Description:** Move beyond rule-based caps. Multi-step negotiation forecasting:
estimate future-regret-risk, lock-in consequences, expansion conflicts. Optimize
across full-session trajectories.
**Determinism tension:** STRATEGIC PLANNING IS NOT COMPATIBLE WITH R6 BYTE-EQUAL
REPLAY. If lifted into v1.x, REQUIRES a spec amendment establishing a "relaxed
determinism mode" for non-replayable strategic exploration. R6 must continue to
hold for the rule-based deterministic mode.
**Trigger:** v2
**Effort:** XL — LLM integration + eval harness + replay-mode bifurcation

### B-C3B-AESTHETIC-HEURISTIC-CORPUS
**Origin:** S52 critique pt 15
**Description:** Architect-reviewed corpus of aesthetic heuristics (visual
framing, sightline harmony, sunlight movement, proportional rhythm).
Incorporate as soft scoring in Phase β ranking.
**Trigger:** v2 — requires architect-reviewer corpus build
**Effort:** XL

---

## Spec § 9.2 clarifications (no backlog entries — documentation only)

### Pt 4 — Long-horizon preference memory (REJECTED, scope)
Preference evolution is C3a's domain, not C3b. C3b operates within a single
brief-resolution session. Cross-session preference learning lives at the Memory
layer or C3a v1.x. Adding to C3b would violate Anti-pattern 5 (scope-creep).

### Pt 9 — History computational cost (REJECTED, scale)
iteration_cap=5 hard=7, max-tweaks-per-layout=6 hard=8. Total session-history
state is bounded at kilobytes. SQLite WAL handles trivially. R6 replay is fast
because state is small. Event-sourcing/checkpointing is solving a problem we
don't have at v1.0 scale. Revisit only if the iteration cap is ever lifted.

### Pt 14 — Post-construction feedback (REJECTED, scope)
Post-occupancy feedback pipeline is a product-wide capability, not a C3b
component. Belongs at the BuildEase product/platform layer per the v2 vision
doc § 7. C3b would *consume* refined heuristics but doesn't own collection.

---

## Items REJECTED as misframed (Pattern D)

### Pt 12 — Cultural subjectivity
C15 has CulturalProfile enum with 6 Indian-household archetypes. C3b consumes
this via the brief. Multi-cultural conditioning already exists. Reviewer
apparently didn't read the C15 contract.

### Pt 13 — Explainability too technical
R2 banned-phrase advisory_lint is exactly this. 32 banned phrases enforced
across 29 tests. MutationEnvelope.why_not_a_tweak field translates engine
language to user language ("touches load_bearing_wall_involvement" →
"this is a structural change rather than a layout tweak"). Reviewer apparently
didn't read the implementation.

---

## Critical architectural tension surfaced

**For your awareness, not for filing:** items 10 (strategic negotiation) and the
spec's R6 byte-equal replay determinism contract are in direct conflict.
Strategic forecasting / regret-estimation is by nature non-deterministic
(probabilistic, may use sampling). If we ever lift the strategic-layer backlog
item into v1.x, the spec needs a v0.5 amendment establishing a relaxed-
determinism mode, with R6 holding only for the rule-based deterministic mode.

This is the kind of cross-cutting concern worth flagging at LOCK adjudication
because LOCK signs you up to R6 as a hard invariant, which constrains future
strategic-intelligence work.

---

## Verdict on BUILD-LOCK readiness

NONE of the 15 items is a v1.0 BUILD-LOCK blocker.
- 7 items route to v1.x backlog
- 2 items route to v2 backlog (with 1 architectural-tension flag)
- 2 items rejected as misframed (already addressed in code)
- 2 items rejected as scope (belong to C3a or product layer, not C3b)
- 2 items rejected as scale (problem doesn't exist at v1.0 ceilings)

C3b v0.4 BUILD remains PROPOSED, pending Ramalingam adjudication per Rule 8.
