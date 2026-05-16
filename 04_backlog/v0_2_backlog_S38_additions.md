# v0.2 Backlog — S38 Additions

**Source**: S38 critique walks + amendment specs.
**Authored**: S38 close, May 9 2026.
**Per Rule 9.2**: filed immediately when surfaced; no permission asked.
**Per Rule 9** (visibility inside spec): each amendment's spec § 6/§ 8 enumerates
its own backlog items; this file is the project-wide mirror.

---

## § 1 — From B-NEW-P v1.0 LOCKED amendment

### B-NEW-P-runtime-audit
- **Description**: Extend C11a's predicate-registry audit at startup to verify
  every upstream error class referenced by Tier B has a valid `severity_tier`
  ClassVar — not just at static-type-check time. Walk #2 finding: Python
  runtime accepts `e.severity_tier = "SYSTEM"` without intrinsic enforcement;
  test_severity_tier_classification.py catches typos in already-listed classes
  but not in newly-added ones.
- **Origin**: B-NEW-P spec § 4 + S38 Walk #2 F1.
- **Trigger**: post-launch C11a audit extension.
- **S{N} verdict**: out of scope for v1; defensive default (`"unknown"` →
  systemic) preserves correctness even if a future contributor mis-spells.
- **Effort**: XS.

### B-NEW-P-enum
- **Description**: Migrate `_SeverityTier` from `Literal[...]` to a `StrEnum`
  subclass for runtime introspection (`_SeverityTier.__members__`,
  `is _SeverityTier.SYSTEMIC` patterns). Trade-off: forces all comparison
  sites to stop using bare-string equality.
- **Origin**: B-NEW-P spec § 4 + S38 Walk #1 F1.
- **Trigger**: post-launch consideration.
- **Effort**: XS.

### B-NEW-P-c7classes
- **Description**: Introduce custom C7 error classes (e.g.,
  `GridGenerationError`, `SpanInfeasibleError`) to replace stdlib raises with
  proper `severity_tier` annotations. Today C7 raises `ValueError`/`KeyError`
  only, which fall to C11a § 2.7's defensive systemic default — safe but
  conservative.
- **Origin**: B-NEW-P spec § 1 + S38 Walk #1 F2.
- **Trigger**: when per-candidate routing of C7 errors becomes operationally
  needed (e.g., a known C7 ValueError category warrants per-candidate retry).
- **Effort**: S-M.

---

## § 2 — From B-NEW-K v1.0 LOCKED amendment (incl. K-4 patch)

### B-NEW-K-impl
- **Description**: Plumb staircase position through `GridGenerator.generate()`
  so C7 emits `Grid` instances with concrete staircase footprints rather than
  callers passing one in retroactively. Today `Grid.staircase` defaults None;
  W9 only fires when explicitly set.
- **Origin**: B-NEW-K spec § 1 (scope discipline).
- **Trigger**: post-launch + C11a M3a/b/c mutation surface stable
  (Sub-session 2 ships M3a/b/c).
- **Effort**: M.

### B-NEW-K-shape
- **Description**: Extend Staircase model with `climb_direction: WallAxis`,
  `shape: StairShape` enum (STRAIGHT / L / U / SPIRAL),
  `riser_height_m`, `tread_depth_m`. Today the rectangle abstraction ignores
  these — a footprint can pass W9 while encoding impossible climb geometry.
  Reviewer-flagged in S38 Walks #1 / #3 + B-NEW-K spec § 1.
- **Origin**: B-NEW-K spec § 6 + S38 Walk #1 F K-1, K-3.
- **Trigger**: post-launch + B-NEW-K-impl shipped.
- **Effort**: M-L.

### B-NEW-K-egress
- **Description**: Egress-clearance-in-front-of-staircase check. Requires
  C9/C10 room-layout integration to verify approach/landing isn't blocked by
  furniture or doorway conflicts.
- **Origin**: B-NEW-K spec § 1 (explicitly deferred) + S38 Walk #1 F K-2.
- **Trigger**: post-launch + B-238 architect review.
- **Effort**: M-L.

### B-NEW-K-landingscale
- **Status**: **CLOSED — fixed in K-4 patch, LOCKED v1.0 at S38.**
- Originally filed at Walk #1; superseded by the K-4 patch.

---

## § 3 — From B-NEW-L v1.0 LOCKED amendment

### B-NEW-L-rotated
- **Description**: Inv 21 generalisation for non-axis-aligned envelopes
  (B-217 polygonal envelope work). Entry approach defined relative to
  rotated plot edges rather than axis-aligned `envelope_width_m` /
  `envelope_depth_m`.
- **Origin**: B-NEW-L spec § 4 + S38 design discipline.
- **Trigger**: post-launch + B-217.
- **Effort**: M.

### B-NEW-L-multi-entry
- **Description**: Multi-entry-door support. Some residential typologies have
  a service entry distinct from the main entry; Inv 21 currently treats all
  ENTRY-kind endpoints as the main entry.
- **Origin**: B-NEW-L spec § 6 + S38 Walk #1 F L-2.
- **Trigger**: post-launch + observed need.
- **Effort**: S-M.

---

## § 4 — From B-NEW-J v1.0 LOCKED amendment (override at launch-complement)

### B-NEW-J-override ⭐ ESCALATED to launch-complement
- **Description**: `brief.layout_overrides: LayoutOverrides` field carrying
  named-rule bypass tokens (e.g., `accept_road_facing_private_band: bool =
  False`). C11a's predicate registry consults overrides before firing the
  predicate. Without this, B-NEW-J biases C11a's mutation search against
  legitimate luxury / view typologies — sea-facing bedrooms, premium frontage
  homes, etc.
- **Origin**: B-NEW-J spec § 6 + S38 Walks #2 + #4.
- **Trigger**: **Must ship at the same release window as B-NEW-J's production
  enforcement (when C11a v1 ships in production).** Not deferred indefinitely.
- **Owner**: C1 (brief schema) + C11a (predicate registry consultation).
- **Constraint**: When implemented, MUST follow B-meta-rule-taxonomy
  framework (no one-off override mechanism).
- **Effort**: S-M.

### B-NEW-J-roomlevel
- **Description**: Per-room privacy check at C9/C10 — even if PRIVATE band is
  correctly oriented, individual bedroom rooms shouldn't have a primary
  window facing the road. Stricter than zone-band-level rule.
- **Origin**: B-NEW-J spec § 6 + S38 Walk #1 F J-1.
- **Trigger**: post-launch + B-238 architect review.
- **Effort**: M.

### B-NEW-J-acoustic
- **Description**: Acoustic isolation rule — kitchen/utility next to bedroom
  → flag (orthogonal to road-facing rule).
- **Origin**: B-NEW-J spec § 6 + S38 Walk #1 brainstorm.
- **Trigger**: post-launch.
- **Effort**: S-M.

---

## § 5 — Meta-governance items (consolidated from Walks #2-#4)

### B-meta-rule-taxonomy ⭐ HIGH strategic importance
- **Description**: Formalize a hard / soft / preference / style /
  user-conditioned predicate taxonomy. Includes: (a) `PredicateClass` enum on
  `MutationViabilityPredicate`, (b) override-precedence rules, (c) registry
  conflict-detection categories, (d) integration with C11b NSGA-II constraint
  handling. **B-NEW-J-override + B-meta-predicate-conflict-detector +
  B-meta-c11b-constraint-handling all become concrete instances.** Generative-
  design literature (verified S38 Walk #4 search) confirms rule-governance is
  an open BIM problem at industry scale.
- **Origin**: S38 Walks #2 F2 + #3 F2/F3/F6/F9 + #4 F2/F4/F10 endorsements.
- **Trigger** (revised Walk #4): **v1 LOCK + first concrete override
  implementation (B-NEW-J-override)**.
- **Effort**: M-L.

### B-meta-c11b-constraint-handling
- **Description**: Choose a NSGA-II constraint-handling strategy (penalty /
  feasibility-based / progressive hardening / RBF surrogate) appropriate for
  BuildemUp's hard/soft predicate mix. Decide at C11b integration time.
- **Origin**: S38 Walk #3 F10 + Walk #4 F3 + NSGA-II constraint-handling
  literature.
- **Trigger**: C11b implementation begins (after C11a v1 ships).
- **Effort**: M.

### B-meta-backlog-roadmap
- **Description**: Periodic backlog-cluster review to detect overlapping
  future semantic systems. File only when a parent's cluster grows beyond 3
  items (already true for K-* and J-*; watch L-*).
- **Origin**: S38 Walk #2 F4 + Walk #3 F4.
- **Trigger**: when K-/J-/L-* cluster review needed.
- **Effort**: M-LT.

### B-meta-predicate-fidelity-monitoring
- **Description**: At C11a integration time, measure downstream rejection
  rate per Tier A predicate. If a predicate's false-positive rate (passes
  mutation viability but fails at C9/C10) exceeds threshold (TBD), file for
  realism enrichment. Prevents Pareto pollution from weak-predictor
  upstream filters.
- **Origin**: S38 Walk #2 F5 + Walk #3 F5/F11 + Walk #4 F5.
- **Trigger**: C11a integration time.
- **Effort**: M-LT.

### B-meta-predicate-conflict-detector
- **Description**: Extend C11a's predicate-registry audit to: (a) detect
  duplicate (rule_owner, rule_id) pairs, (b) detect predicates with
  overlapping rule_ids across different owners, (c) visualize the predicate
  graph by rule_owner cluster.
- **Origin**: S38 Walk #2 F7.
- **Trigger**: post-launch.
- **Effort**: M.

---

## § 6 — Summary

| Category | Count |
|---|---|
| Closed (resolved in S38) | 1 (B-NEW-K-landingscale → K-4 patch) |
| Per-amendment-spec items | 9 (P/K/L/J family) |
| **Launch-complement items** | **1 (B-NEW-J-override)** |
| Meta-governance items | 5 |
| **Total new IDs filed at S38** | **15** |
| Cumulative project backlog (estimate) | ~59 (was 51 + 8 net new — K-landingscale closed) |

---

**End of v0.2 Backlog — S38 Additions.**
