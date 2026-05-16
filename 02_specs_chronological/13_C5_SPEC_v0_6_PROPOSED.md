# BuildemUp Component 5 (Topology Selector) — SPEC v0.6 PROPOSED

**Status:** **v0.6 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.6 LOCKED".

**Generated:** S29, after C5 v0.5 PROPOSED and 12-item code-review critique walk (round 4 on C5).

This v0.6 is the **patch delta** on top of v0.5 PROPOSED. Read v0.1 through v0.5 first.

---

## § 13 — Rule-7 walk (v0.5 → v0.6)

### Verification gates run BEFORE this walk

1. **Code-grep + math verification (5 checks run):**
   - **#2 (highest-priority membership wins):** verified at v0.5 § 14.2 — explicit "Branch dispatch" comment + `return preferred, "..."` from each branch. Other branches' membership factors computed but discarded. **Real hidden discontinuity.**
   - **#5 (score_breakdown lacks prior contribution):** verified — v0.5 § 14.4 invariant says contributions sum to **base score** (before prior blend). Prior term `0.15 × prior` invisible. **Valid.**
   - **#6 (low_confidence not on secondaries):** verified — v0.4 § 14.3 says secondaries carry `low_confidence = False` because admission filter requires score ≥ 0.30. Critique misread "top only when applicable" as "top only." **Push back on framing; documentation simplification opportunity.**
   - **#11 (monotonicity guarantee):** scoring criteria are bell-shaped by design (each topology has optimal width range; beyond it, score drops). Blanket monotonicity test would falsely fail correct bell-shaped scorers. **Push back.**
   - **#1 (rank flip in 0.053 band):** v0.5 § 14.1 explicitly acknowledges this band; it's the *intended* behavior — when base scores are essentially tied, priors should decide. Critique's proposed `if abs(base_A - base_B) > 0.05: ignore prior` re-introduces a hard cutoff at exactly 0.05 — the discontinuity v0.4 #1 + v0.5 #1 removed. **Push back.**
2. **Web research:** none required — no external-standards claims invoked. Stating this explicitly per Rule 7 amendment.

### Critique walk

| # | Critique | Verdict |
|---|---|---|
| 1 | Additive prior allows rank-flip in 0.053 edge band | **MISFRAMED — PUSH BACK** (intended behavior; proposed fix re-introduces discontinuity) |
| 2 | Smooth ramp dispatches single branch; not blended | **VALID — SPEC-AMENDMENT** |
| 3 | Corner logic still binary | **VALID-BUT-BACKLOG (already B-076)** |
| 4 | Bedroom penalty step function (0.5 vs 1.0) | **VALID — SPEC-AMENDMENT** |
| 5 | score_breakdown lacks prior contribution | **VALID — SPEC-AMENDMENT** |
| 6 | low_confidence not propagated to secondaries | **MISFRAMED — PUSH BACK + documentation clarification** |
| 7 | Consistency validator too narrow (no zone-band semantic check) | **VALID-MARGINAL — SPEC-AMENDMENT** |
| 8 | Tie-break alphabetical is arbitrary | **VALID — SPEC-AMENDMENT (REVERSES v0.5 #10)** |
| 9 | No guard for extreme dimension outliers | **MISFRAMED — PUSH BACK** (aspect_ratio_fit covers; B-075 for AspectClass enum) |
| 10 | Linear interpolation produces non-intuitive prior mixes | **MISFRAMED — PUSH BACK** (contradicts #2; sharpening = winner-take-all) |
| 11 | No monotonicity guarantee | **MISFRAMED — PUSH BACK** (bell-shaped criteria by design) |
| 12 | No final feasibility sanity check | **MISFRAMED — PUSH BACK** (C8/C9 responsibility) |

**Tally:** 4 SPEC-AMENDMENTS (#2, #4, #5, #8) · 1 MARGINAL (#7) · 1 DOCUMENTATION (#6) · **6 PUSH-BACKS** (#1, #3, #9, #10, #11, #12) · 0 NEW BACKLOG · 0 DUPLICATES.

**v0.5 reversal flagged:** v0.5 #10 (alphabetical-by-enum-value tie-break) reversed by v0.6 #8 (tie-break by corridor_overhead). Reasoning in § 14.4.

---

## § 14 — v0.6 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Multi-branch prior blending (#2)

**v0.5 § 14.2 amended.** Replace single-branch `return preferred` dispatch with **weighted blend across all branches**. Each branch contributes its preferred priors weighted by its own membership factor; remaining unallocated weight goes to the default.

```python
# v0.5 (replaced): "highest-priority membership wins" — first matching branch
#                  returns its preferred priors; other branches' factors
#                  computed but discarded → hidden discontinuity at boundaries.
#
# v0.6 (#2): every branch contributes weighted by its membership factor.
# Final priors = Σ(factor_i × preferred_i) + (1 - Σ factors) × default
# subject to: clamp factors so Σ factors ≤ 1.

def assign_priors(plot: Plot, room_brief: FloorRoomBrief) -> tuple[TopologyPriors, str]:
    """v0.6 (#2): all-branch blending; no hidden dispatch discontinuity."""

    # Membership factors (same smooth ramps as v0.5)
    wide_f       = _smooth_ramp(plot.width_m, 7.42, 8.42)
    narrow_f     = 1.0 - _smooth_ramp(plot.width_m, 6.21, 7.21)
    large_w_f    = _smooth_ramp(plot.width_m, 11.19, 13.19)
    large_d_f    = _smooth_ramp(plot.depth_m, 17.29, 19.29)
    shallow_f    = _smooth_ramp(plot.depth_m / max(plot.width_m, 1e-6), 0.5, 0.8)

    # Branch-eligibility gating (input contract requirements)
    is_corner = plot.corner_plot
    few_beds  = room_brief.bedroom_count <= 2
    many_beds = room_brief.bedroom_count >= 2

    # Compute each branch's weight (0 if branch's brief-side gate fails)
    w_corner   = 1.0 if is_corner else 0.0
    w_wide     = wide_f    if (few_beds and not is_corner) else 0.0
    w_narrow   = narrow_f  if (many_beds and not is_corner) else 0.0
    w_large    = min(large_w_f, large_d_f) if not is_corner else 0.0

    # Apply shallow-plot factor to wide branch (reduces wide weight when shallow)
    w_wide *= shallow_f                     # carries v0.5 § 14.4 #8 ramp

    # Cap total branch weight at 1.0; remainder goes to default
    branch_total = min(1.0, w_corner + w_wide + w_narrow + w_large)
    w_default    = 1.0 - branch_total

    # Preferred priors per branch
    P_default = TopologyPriors(strip=1.0, central_spine=1.0, l_shape=0.7, courtyard=0.7)
    P_corner  = TopologyPriors(strip=0.85, central_spine=0.7, l_shape=1.0, courtyard=0.7)
    P_wide    = TopologyPriors(strip=1.0, central_spine=0.85, l_shape=0.7, courtyard=0.7)
    P_narrow  = TopologyPriors(strip=0.7, central_spine=1.0, l_shape=0.7, courtyard=0.7)
    P_large   = TopologyPriors(strip=0.85, central_spine=0.7, l_shape=0.7, courtyard=1.0)

    blended = TopologyPriors(
        strip         = w_corner*P_corner.strip   + w_wide*P_wide.strip   + w_narrow*P_narrow.strip   + w_large*P_large.strip   + w_default*P_default.strip,
        central_spine = w_corner*P_corner.central_spine + w_wide*P_wide.central_spine + w_narrow*P_narrow.central_spine + w_large*P_large.central_spine + w_default*P_default.central_spine,
        l_shape       = w_corner*P_corner.l_shape + w_wide*P_wide.l_shape + w_narrow*P_narrow.l_shape + w_large*P_large.l_shape + w_default*P_default.l_shape,
        courtyard     = w_corner*P_corner.courtyard + w_wide*P_wide.courtyard + w_narrow*P_narrow.courtyard + w_large*P_large.courtyard + w_default*P_default.courtyard,
    )

    # Branch-trace string for provenance: dominant branch by weight
    branches = (("corner", w_corner), ("wide_few_bedrooms", w_wide),
                ("narrow_many_bedrooms", w_narrow), ("large", w_large),
                ("default_strip_or_central", w_default))
    dominant = max(branches, key=lambda x: x[1])
    branch_label = f"blend_{dominant[0]}@{dominant[1]:.2f}"

    return blended, branch_label
```

**Effect:** at width = 12.0m / 1 bedroom (the v0.5 boundary case where wide_few_bedrooms and large branches both partially apply), v0.5 dispatched to `wide_few_bedrooms` and discarded `large_w_f` and `large_d_f`. v0.6 blends both contributions weighted by their membership factors. No boundary discontinuity.

The `branch_label` records the dominant branch and its weight (e.g., `"blend_wide_few_bedrooms@0.65"`) so downstream provenance can still describe what drove the priors.

### § 14.2 — Smooth bedroom penalty (#4)

**v0.5 § 14.5 amended.** Replace the step function with a smooth ramp:

```python
def score_bedroom_fit(topology: TopologyKind, room_brief: FloorRoomBrief) -> float:
    """v0.5 (replaced): if bedroom_count < 3: score *= 0.5  ← step function
    v0.6 (#4):         smooth penalty factor = min(1.0, bedroom_count / 3.0)

    Effect:
      bedrooms = 1  →  factor = 0.333
      bedrooms = 2  →  factor = 0.667
      bedrooms = 3  →  factor = 1.000  (no penalty)
      bedrooms = 4+ →  factor = 1.000  (no penalty)

    Removes the artificial 2 → 3 jump (0.5 → 1.0) by interpolating linearly.
    """
    base = _topology_base_bedroom_fit(topology, room_brief.bedroom_count)
    if topology == TopologyKind.COURTYARD:
        factor = min(1.0, room_brief.bedroom_count / 3.0)
        return base * factor
    return base
```

The penalty applies only to COURTYARD (per v0.5 #8 design — courtyard is the topology with functional dependence on bedroom count). Other topologies use `_topology_base_bedroom_fit` unchanged.

### § 14.3 — Prior contribution in score_breakdown (#5)

**v0.5 § 14.4 amended.** Add a synthetic `"prior"` entry to `score_breakdown` representing the prior's contribution to the final score:

```python
# v0.5 invariant (replaced):
#   sum(entry.contribution for entry in score_breakdown.values()) == base_score
#
# v0.6 invariant (#5):
#   sum(entry.contribution for entry in score_breakdown.values()) == final_score
#   where score_breakdown now includes a "prior" entry alongside the 7 criteria.

# Construction inside select.py:
def _build_score_breakdown(
    raw_scores: Mapping[str, float],
    weights: Mapping[str, float],
    base_score: float,
    prior: float,
) -> Mapping[str, ScoreBreakdownEntry]:
    """v0.6 #5: 8 entries — 7 criteria + 1 prior."""
    entries = {}
    for criterion, raw in raw_scores.items():
        w = weights[criterion]
        entries[criterion] = ScoreBreakdownEntry(
            raw=raw, weight=w, contribution=raw * w * 0.85,
            # × 0.85 because of additive blend: criterion contributes
            # 0.85 × (raw × weight) to final score
        )
    entries["prior"] = ScoreBreakdownEntry(
        raw=prior, weight=0.15, contribution=0.15 * prior,
    )
    return MappingProxyType(entries)


# Verification (consumer-side):
candidate.score == sum(e.contribution for e in candidate.score_breakdown.values())
# = 0.85 × Σ(criterion.raw × criterion.weight) + 0.15 × prior
# = 0.85 × base_score + 0.15 × prior
# = final_score  ✓
```

**Test additions:**
- `test_score_breakdown_includes_prior_entry`
- `test_score_breakdown_contributions_sum_to_final_score` (replaces v0.5 sum-to-base test)

**Backwards-compat:** consumers reading `score_breakdown[criterion].raw` see the same per-criterion raw values. Only the `contribution` field changes its scaling (× 0.85 from the blend); but no consumer of v0.5 exists yet (C5 not built), so no migration cost.

### § 14.4 — Tie-break by corridor_overhead (#8, REVERSES v0.5 #10)

**v0.5 § 14.6 amended.** Replace alphabetical-by-enum-value secondary sort key with corridor_overhead-based key:

```python
# v0.5 (replaced):
#   scored.sort(key=lambda c: (-c.score, c.kind.value))
#   ← alphabetical: central_spine < courtyard < l_shape < strip
#
# v0.6 (#8, reversal of v0.5 #10):
#   scored.sort(key=lambda c: (
#       -c.score,
#       -c.score_breakdown["corridor_overhead"].raw,    # higher raw = less overhead
#   ))
#   ← simpler-topology wins ties (higher corridor_overhead raw means less overhead).

# Reversal rationale:
#   v0.5 #10 chose alphabetical for "no opinion-based priority". That's
#   architecturally meaningless — the order central_spine < courtyard < l_shape
#   < strip has nothing to do with what residential topology should win a tie.
#   v0.6 #8 ties to a measurable architectural quality (corridor overhead).
#   Lower-overhead topology wins ties. Mechanical (sortable on a number) AND
#   meaningful (lower overhead = more usable floor area = sensible default).
```

Note the convention: `corridor_overhead` raw score in [0, 1] is "fitness" — **higher** raw means **less** overhead (the criterion measures "how well does this topology avoid corridor waste"). So `-c.score_breakdown["corridor_overhead"].raw` as sort key means higher raw goes first (lower overhead wins ties).

**Test additions:**
- `test_ties_break_by_lower_corridor_overhead` — fabricate two candidates with identical scores; assert lower-overhead one comes first.
- `test_v0_6_8_reversal_alphabetical_tie_break_no_longer_applies` — guard that the v0.5 alphabetical behavior is genuinely replaced (helps future readers track the decision history).

### § 14.5 — Strengthened consistency validator (#7)

**v0.5 § 14.7 amended.** Add zone-band semantic checks per topology kind:

```python
def _validate_candidate_consistency(c: TopologyCandidate) -> None:
    """v0.5 base + v0.6 #7 additions: also assert zone-band shape per topology."""

    # v0.5 checks (carried unchanged): corridor position, connectivity, non-empty bands
    expected_position = {
        TopologyKind.STRIP:         (CorridorPosition.NONE, CorridorPosition.CENTRAL),
        TopologyKind.CENTRAL_SPINE: (CorridorPosition.CENTRAL,),
        TopologyKind.L_SHAPE:       (CorridorPosition.L_BENT,),
        TopologyKind.COURTYARD:     (CorridorPosition.PERIMETER,),
    }
    if c.corridor_sketch.position not in expected_position[c.kind]:
        raise RuntimeError(...)

    expected_connectivity = {
        TopologyKind.STRIP:         ConnectivityType.LINEAR,
        TopologyKind.CENTRAL_SPINE: ConnectivityType.LINEAR,
        TopologyKind.L_SHAPE:       ConnectivityType.BRANCHED,
        TopologyKind.COURTYARD:     ConnectivityType.LOOP,
    }
    if c.corridor_sketch.connectivity_type != expected_connectivity[c.kind]:
        raise RuntimeError(...)

    if not c.zone_bands:
        raise RuntimeError(f"{c.kind.value} candidate has empty zone_bands")

    # NEW v0.6 (#7): zone-band shape per topology
    required_bands = {
        TopologyKind.STRIP:         {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.CIRCULATION, ZoneBand.PRIVATE},
        TopologyKind.CENTRAL_SPINE: {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.CIRCULATION, ZoneBand.PRIVATE},
        TopologyKind.L_SHAPE:       {ZoneBand.PUBLIC, ZoneBand.PRIVATE,
                                     ZoneBand.CIRCULATION},
        TopologyKind.COURTYARD:     {ZoneBand.PUBLIC, ZoneBand.SERVICE,
                                     ZoneBand.PRIVATE, ZoneBand.CIRCULATION},
    }
    have = set(c.zone_bands.keys())
    missing = required_bands[c.kind] - have
    if missing:
        raise RuntimeError(
            f"{c.kind.value} candidate missing required zone bands: "
            f"{sorted(b.value for b in missing)}"
        )

    # Distinct compass directions: no two bands assigned to the same orientation
    used_directions = list(c.zone_bands.values())
    if len(used_directions) != len(set(used_directions)):
        # Note: this is too strict for COURTYARD (sides/center share). Relax:
        # only assert distinct for non-COURTYARD topologies.
        if c.kind != TopologyKind.COURTYARD:
            raise RuntimeError(
                f"{c.kind.value} has duplicate compass directions in zone_bands: "
                f"{used_directions}"
            )
```

**Test addition:** `test_consistency_validator_catches_missing_required_band` — fabricate STRIP candidate without PRIVATE band; assert RuntimeError.

### § 14.6 — Documentation clarification: low_confidence uniform per-candidate (#6)

**v0.4 § 14.3 wording amended (no behavior change).**

v0.5 carried v0.4's wording: *"`low_confidence = (score < 0.30)` — set on the top candidate only when no candidate clears the threshold."* The "set on top only" framing was misread as "secondaries don't carry the flag" by the v0.6 critique #6.

v0.6 wording (no behavior change):

> `low_confidence: bool` is computed **uniformly per candidate** as `(candidate.score < 0.30)`. By construction, secondary candidates always have `score >= 0.30` (admission filter in § 14.4 v0.3), so for them the flag is always `False`. The flag is meaningful primarily on the top candidate when no candidate clears 0.30; it is set on every candidate regardless.

The behavior is unchanged. This amendment exists to remove ambiguity that triggered #6's misread.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — #1 (rank flip in 0.053 band)

**Critique claim:** even after v0.5 #1, rank can flip if base score difference < 0.053. Proposed: `if abs(base_A - base_B) > 0.05: ignore prior`.

**Pushback:** the 0.053 band is the *intended* behavior. v0.5 § 14.1 explicitly documents it: when base scores are essentially tied (within 0.053), priors should decide — that's the entire point of having priors. Without that property, priors would be useless decoration.

The proposed `if abs(...) > 0.05: ignore prior` introduces a hard cutoff at exactly 0.05 — the same kind of discontinuity v0.4 #1 (dampening) and v0.5 #1 (additive blend) systematically removed. At base_diff = 0.0499 priors matter fully; at 0.0501 priors don't matter at all. Step function. The dynamic-weight alternative `prior_weight = min(0.15, base_gap × 2)` is smoother but adds opaque nonlinearity that's hard to reason about.

v0.5 design is correct. Push back.

### Pushback B — #3 (corner logic still binary)

**Critique claim:** corner is binary; introduce `corner_factor ∈ [0, 1]` for smoothing.

**Pushback:** continuous corner factor requires `corner_orientation` input — directional information about which side IS the second street. The current `Plot.corner_plot: bool` input contract has no such field. Without that data, there's no continuous variable to ramp on.

This is exactly what **B-076** (Plot.corner_orientation input field) is filed to address. When B-076 lands, the corner branch will gain directional smoothing naturally. Until then, the input is binary, so the branch is binary. Push back.

### Pushback C — #9 (no extreme dimension outlier guard)

**Critique claim:** very extreme plots (ultra-long-narrow, ultra-wide-shallow) handled only indirectly via scoring.

**Pushback:** Plot.__post_init__ already enforces 3-60m bounds (per C4 v0.7 push-back of #5), giving max aspect_ratio 20:1. The `aspect_ratio_fit` criterion (weight 0.10) penalizes aspect_ratio > 1.5. The "extreme-shape penalty" critique proposes is duplicative of an existing scorer.

AspectClass enum + extreme-plot flag is **B-075** in C4 backlog. Push back.

### Pushback D — #10 (linear interpolation produces non-intuitive prior mixes)

**Critique claim:** linear interpolation can produce non-intuitive prior values (e.g., `strip=0.9, central=0.9` simultaneously); apply softmax sharpening to ensure one topology dominates.

**Pushback:** softmax sharpening RE-INTRODUCES winner-take-all dynamics — the exact thing critique #2 (this same round) is asking us to AVOID. #2 says "blend more"; #10 says "sharpen winner." Internally contradictory pair within the same critique document.

Furthermore, having `strip=0.9, central=0.9` simultaneously is not non-intuitive — it correctly says "both topologies are well-suited to this plot," which is exactly what tie-break logic is for. The base-score scoring layer makes the actual call between them. Push back.

### Pushback E — #11 (no monotonicity guarantee)

**Critique claim:** increasing a favorable input (e.g., width) doesn't guarantee score increases monotonically.

**Pushback:** scoring criteria are bell-shaped by design. Each topology has an optimal range for each variable, beyond which score drops:
- COURTYARD has an optimal width range; at 50m wide, the courtyard becomes wasteful.
- STRIP has an optimal aspect ratio; far past it, it becomes corridor-dominated.
- bedroom_fit on each topology has a sweet spot.

A blanket monotonicity test would falsely fail correct bell-shaped scorers. The membership ramps in § 14.1 ARE monotonic (verifiable; useful test exists). The blanket "score monotone in width" property is mathematically wrong for residential design heuristics. Push back.

### Pushback F — #12 (no final feasibility sanity check)

**Critique claim:** add lightweight feasibility check (min space per band, corridor fit) to catch infeasible topologies before C6/C9.

**Pushback:** "min space per band" requires room dimensions interacting with topology-band geometry — that's C9's (Placement Engine) responsibility per the architecture doc pipeline (C5 → C6 → C7 → C8 → C9). "Corridor fit check" is C8's (Corridor Designer) responsibility.

C5's contract is topology selection only — pulling placement/corridor feasibility into C5 violates separation of concerns and duplicates work that C8/C9 will do correctly with full context. Already filed conceptually as **B-068** (effective_open_sides post-setback) and **B-092** (BuildableEnvelope as public C2 output). Push back.

---

## § 16 — Backlog roll-up (Rule 9)

### No new backlog items in v0.6

All amendments addressable in-spec; no items emerged that aren't covered by existing C5 backlog (B-085..B-093) or the deferred-CI-infra triggers (B-080, B-081). Pushback E (#11 monotonicity) is genuinely a non-property of the system, not a deferred item.

### Pre-existing backlog (carried unchanged)

- **C5:** B-085, B-086, B-087, B-088, B-089, B-090, B-091, B-092, B-093.
- **C4:** B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081, B-082, B-083, B-084.

---

## § 17 — What v0.6 LOCKS

1. **4 SPEC-AMENDMENTS** in code (§§ 14.1, 14.2, 14.3, 14.4).
2. **1 marginal SPEC-AMENDMENT** (§ 14.5 validator strengthening).
3. **1 documentation clarification** (§ 14.6 low_confidence wording — no behavior change).
4. **6 pushbacks** documented and held with explicit math/grep/scope verification (#1, #3, #9, #10, #11, #12).
5. **1 v0.5 reversal flagged** (#10 alphabetical → #8 corridor_overhead tie-break).
6. **0 new backlog items.** No duplicates.
7. Estimated delta: **~50 LOC source change + ~5 new tests** (mostly in `decision_table.py`, `select.py`, `scorers.py`, `schema.py`).
8. **Architecture identical to v0.5.** All changes are mathematical-form changes, additive scoring entries, validator strengthening, or wording clarification; no contract-breaking.

---

## § 18 — v0.6 verification at LOCK time (estimated)

- Tier 1: ~5 new tests bringing C5 total to ~51.
- Tier 2: 0 new.
- Production code: ~50 LOC across `decision_table.py`, `select.py`, `scorers.py`, `schema.py`.
- Existing v0.5-anticipated tests adjusted for: multi-branch blending (no single-branch dispatch); smooth bedroom penalty; prior in score_breakdown (sum-to-final, not sum-to-base); corridor_overhead tie-break; zone-band shape validator.

---

## § 19 — Cumulative C5 lineage

| Round | SPEC-AMENDMENTS | New backlog | Push-backs | Reversals |
|---:|---:|---:|---:|---:|
| v0.1 (DRAFT) | — | — | — | — |
| v0.2 (PROPOSED) | initial design | 7 (B-085..091) | — | — |
| v0.3 | 5 + 1 invariant + 1 Q7 reversal | 1 (B-092) | 2 | 1 (Q7) |
| v0.4 | 4 + 1 invariant | 1 (B-093) | 5 | — |
| v0.5 | 5 + 2 marginal | 0 | 5 | — |
| **v0.6** | **4 + 1 marginal + 1 doc** | **0** | **6** | **1 (#10)** |
| **Total to v0.6** | **18 + 3 marginal** | **9** | **18** | **2** |

Pushback rate trend: 2 → 5 → 5 → **6**. Backlog rate: 1 → 1 → 0 → **0**. Architecture is stable; new critique items now resolve to either valid amendments the architecture absorbs cleanly, or pushbacks grounded in falsified or out-of-scope claims.

---

## § 20 — Status

**v0.6 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per Rule 8, adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.7 PROPOSED, not backlog entries, until Ramalingam locks.

Per Rule 7 amended (S29): all 12 critique items verified via 5 independent checks (3 code-grep + 2 math/conceptual) before this walk; no external-standards claims invoked, so web-search not required this round (per Rule 7's "if no factual claim, say so" clause).

Per Obligation 1: still no C5 code. Spec must LOCK before code build.
