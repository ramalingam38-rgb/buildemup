# BuildemUp Component 5 (Topology Selector) — SPEC v0.7 PROPOSED

**Status:** **v0.7 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.7 LOCKED".

**Generated:** S29, after C5 v0.6 PROPOSED and 12-item code-review critique walk (round 5 on C5).

This v0.7 is the **patch delta** on top of v0.6 PROPOSED. Read v0.1–v0.6 first.

**★ Notable:** this round caught a genuine math defect (D2) that escaped v0.3 / v0.4 / v0.5 / v0.6 review. The defect: in v0.6 § 14.1, when `sum(branch_weights) > 1.0`, blended priors could exceed the [0, 1] range (e.g., strip=1.595 was achievable). v0.7 § 14.1 fixes via proper normalization.

---

## § 13 — Rule-7 walk (v0.6 → v0.7)

### Verification gates run BEFORE this walk

1. **Math + code-grep verification (5 checks run):**
   - **#1 (multi-branch dilution):** computed at boundary case wide_f=0.4, large_f=0.4 — blend produces strip=0.94/courtyard=0.82, single-branch dispatch produces 1.0/0.7. 20% spread compression. **The intended behavior of a blend at boundaries; not a defect.** Push back.
   - **#2 (clamp loses info):** computed at extreme case w_wide=1.0, w_large=0.7 — v0.6 § 14.1 produces blended strip = 1.595, **exceeding [0, 1] range**. The `min(1.0, sum)` only affects `w_default`, leaving raw weights in the blend formula. **Genuine math defect. Adopt fix.**
   - **#3 (default dominates):** at w=0.2/0.2, default=0.6 produces well-shaped distribution (strip=0.97, central=0.91). Default *should* dominate when no signal applies; that's what default means. Critique's `min(0.5, default)` cap creates non-conserved sum (0.9 total) without redistribution rule. Push back.
   - **#11 (all-zero edge case):** verified — v0.6 § 14.1 already includes `default_strip_or_central` in branches tuple; max-by-weight correctly identifies it. The case is explicit. Critique proposes cosmetic relabel only.
   - **#12 (cross-candidate consistency):** candidates ARE distinct TopologyKind values by construction (set of {STRIP, CENTRAL_SPINE, L_SHAPE, COURTYARD}). "Trivial variations of same topology" is mathematically impossible. Misframed.
2. **Web research:** none required — no external-standards claims invoked. Stating per Rule 7 amendment.

### Critique walk

| # | Critique | Verdict |
|---|---|---|
| 1 | Multi-branch blend dilutes signal | **MISFRAMED — PUSH BACK** (intended behavior; sharpening = winner-take-all again) |
| 2 | Branch-weight clamp loses info | **VALID — SPEC-AMENDMENT (math defect fix)** |
| 3 | Default dominates when signals weak | **MISFRAMED — PUSH BACK** (default should dominate when no signal; proposed cap breaks weight conservation) |
| 4 | Prior system disconnected from scoring distribution | **MISFRAMED — PUSH BACK** (recurring v0.5 #1 shape; opaque nonlinearity) |
| 5 | score_breakdown lacks ordering | **VALID-MARGINAL — SPEC-AMENDMENT** (top_contributors field) |
| 6 | Tie-break via corridor_overhead noisy | **MISFRAMED — PUSH BACK** (composite averages, doesn't reduce noise) |
| 7 | Zone-band validation lacks functional checks | **VALID-BUT-BACKLOG (B-091 territory)** |
| 8 | Bedroom penalty only on COURTYARD; extend | **VALID — SPEC-AMENDMENT** |
| 9 | Binary low_confidence; need continuous score | **MISFRAMED — PUSH BACK** (`score: float` already continuous; bool is contract signal) |
| 10 | Provenance branch_label only shows dominant | **VALID-MARGINAL — SPEC-AMENDMENT** (multi-branch provenance) |
| 11 | All-zero edge case not explicit | **MISFRAMED — PUSH BACK** (already handled correctly) |
| 12 | No cross-candidate consistency check | **MISFRAMED — PUSH BACK** (candidates distinct by construction) |

**Tally:** 2 SPEC-AMENDMENTS (#2, #8) · 2 MARGINAL (#5, #10) · 1 BACKLOG-NOTED (#7 → B-091) · **7 PUSH-BACKS** (#1, #3, #4, #6, #9, #11, #12) · 0 NEW BACKLOG · 0 DUPLICATES.

---

## § 14 — v0.7 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Branch-weight normalization (#2 — math defect fix)

**v0.6 § 14.1 amended.** Replace `branch_total = min(1.0, sum)` with proper normalization that preserves proportional influence when raw branch weights exceed 1.0.

```python
# v0.6 (replaced):
#   branch_total = min(1.0, w_corner + w_wide + w_narrow + w_large)
#   w_default    = 1.0 - branch_total
#   blended      = Σ(w_i × P_i) + w_default × P_default
#   ← BUG: when raw sum > 1.0, w_default becomes 0 BUT raw weights still
#     used in blend. Total weight on priors > 1.0 → priors can exceed [0, 1].
#     Worked example v0.6: w_wide=1.0, w_large=0.7 → strip = 1.595.
#
# v0.7 (#2): proper normalization. When raw sum > 1.0, scale ALL branch
# weights down proportionally so they sum to 1.0; w_default = 0.
# When raw sum <= 1.0, leave branches alone; w_default takes the remainder.

raw_total = w_corner + w_wide + w_narrow + w_large

if raw_total > 1.0:
    # Normalize branch weights to sum to exactly 1.0 (no default contribution)
    scale = 1.0 / raw_total
    w_corner *= scale
    w_wide   *= scale
    w_narrow *= scale
    w_large  *= scale
    w_default = 0.0
else:
    # Branches under-allocate; default fills the remainder
    w_default = 1.0 - raw_total

# Now sum(w_corner, w_wide, w_narrow, w_large, w_default) == 1.0 exactly.
# Blended priors are guaranteed in [0, 1] (each P_i is in [0, 1] and
# weights sum to 1.0 → convex combination).

blended = TopologyPriors(
    strip         = w_corner*P_corner.strip + ... + w_default*P_default.strip,
    central_spine = ...,
    l_shape       = ...,
    courtyard     = ...,
)
```

**Verification (re-run v0.6's worked example):** w_wide=1.0, w_large=0.7 → raw_total=1.7 → scale=0.588. Renormalized: w_wide=0.588, w_large=0.412, w_default=0.

Blended strip = 0.588 × 1.0 + 0.412 × 0.85 = 0.588 + 0.350 = **0.938** (was 1.595).

All priors in [0, 1]. ✓

**Test additions:**
- `test_priors_always_in_unit_range_under_any_branch_weights` — Hypothesis-test over all (plot_w, plot_d, bedroom_count, corner) combinations. Asserts every prior in [0, 1].
- `test_branch_weights_always_sum_to_one_post_normalization` — invariant test on the `w_*` totals.
- `test_v0_6_blowup_case_now_bounded` — explicit regression: w_wide=1.0, w_large=0.7 case, assert blended priors ≤ 1.0.

### § 14.2 — Per-topology bedroom-fit minimums (#8)

**v0.6 § 14.2 amended.** Extend the smooth bedroom penalty from COURTYARD-only to all four topologies, with per-topology `min_bedrooms` thresholds:

```python
# v0.6 (replaced): only COURTYARD got bedroom-count penalty
#   if topology == TopologyKind.COURTYARD:
#       factor = min(1.0, room_brief.bedroom_count / 3.0)
#
# v0.7 (#8): each topology has a minimum-viable bedroom count.
# Below the min, score is smoothly attenuated.
#
# Rationale:
#   STRIP: min=1     (single-row layout works for any bedroom count)
#   CENTRAL_SPINE: min=2  (dual-flank design assumes ≥2 bedrooms; for 1-bed,
#                          the corridor + single-side flank is wasteful)
#   L_SHAPE: min=2   (L-shape has two arms; one arm with one room is awkward)
#   COURTYARD: min=3 (courtyard requires ≥3 bedrooms to justify the open core)

_TOPOLOGY_MIN_BEDROOMS: Mapping[TopologyKind, int] = MappingProxyType({
    TopologyKind.STRIP:         1,
    TopologyKind.CENTRAL_SPINE: 2,
    TopologyKind.L_SHAPE:       2,
    TopologyKind.COURTYARD:     3,
})


def score_bedroom_fit(topology: TopologyKind, room_brief: FloorRoomBrief) -> float:
    base = _topology_base_bedroom_fit(topology, room_brief.bedroom_count)
    min_beds = _TOPOLOGY_MIN_BEDROOMS[topology]
    factor = min(1.0, room_brief.bedroom_count / float(min_beds))
    return base * factor
```

**Effect:**

| topology | bedrooms=1 | =2 | =3 | =4 |
|---|---:|---:|---:|---:|
| STRIP | 1.000 | 1.000 | 1.000 | 1.000 |
| CENTRAL_SPINE | 0.500 | 1.000 | 1.000 | 1.000 |
| L_SHAPE | 0.500 | 1.000 | 1.000 | 1.000 |
| COURTYARD | 0.333 | 0.667 | 1.000 | 1.000 |

(Numbers above are *factor* values; actual base bedroom_fit is multiplied by these.)

The "1 bedroom + huge plot → courtyard" pathology v0.5 #8 originally addressed is preserved (factor 0.333). New behavior adds the same shape to CENTRAL_SPINE and L_SHAPE — a 1-bedroom plot will see those topologies attenuated by 0.5.

**Test additions:**
- `test_bedroom_fit_factor_per_topology_table` — exhaustive over the 4 topologies × 5 bedroom counts (1..5).
- `test_strip_no_bedroom_penalty_at_any_count` — STRIP min=1 means no attenuation ever.

### § 14.3 — top_contributors derived field (#5 marginal)

**v0.6 § 14.3 amended.** Add a derived `top_contributors` tuple on `TopologyCandidate` listing the top-2 criterion names by contribution magnitude:

```python
@dataclass(frozen=True)
class TopologyCandidate:
    kind: TopologyKind
    score: float
    score_breakdown: Mapping[str, ScoreBreakdownEntry]
    top_contributors: tuple[str, ...]                 # NEW v0.7 #5
    zone_bands: Mapping[ZoneBand, PlotOrientation]
    corridor_sketch: CorridorSketch
    low_confidence: bool
    justification: str
    provenance: TopologyProvenance


def _compute_top_contributors(
    score_breakdown: Mapping[str, ScoreBreakdownEntry],
    n: int = 2,
) -> tuple[str, ...]:
    """v0.7 #5: top-N criterion names by contribution magnitude.
    Used for at-a-glance debugging and UI summary surfaces.

    Ties broken by alphabetical order on criterion name (deterministic).
    """
    sorted_entries = sorted(
        score_breakdown.items(),
        key=lambda kv: (-kv[1].contribution, kv[0]),
    )
    return tuple(name for name, _ in sorted_entries[:n])
```

**Test addition:** `test_top_contributors_lists_top_two_by_contribution`.

This is purely a derived-output convenience; no scoring math affected. The same information is in `score_breakdown` — `top_contributors` saves consumers from sorting at every read site.

### § 14.4 — Multi-branch provenance (#10 marginal)

**v0.6 § 14.1 amended.** Replace single-string `branch_label` on `TopologyProvenance` with a multi-branch weight map:

```python
@dataclass(frozen=True)
class TopologyProvenance:
    derived_at: float
    plot_analysis_trace_id: str
    candidate_decision_table_match: str   # carries v0.2 form: "blend_<dominant>@<weight>"
    branch_weights: Mapping[str, float]   # NEW v0.7 #10 — full breakdown
```

`branch_weights` carries each branch's contribution weight (post-normalization per v0.7 § 14.1):

```python
# Example provenance trace:
# plot.width_m = 12.0, depth_m = 18.0, bedrooms = 1, corner = False
# → wide_f=1.0, large_f=0.5*0.5=0.25 (avg of large_w_f, large_d_f)
# raw_total = 1.0 + 0.25 = 1.25 → normalize: wide=0.8, large=0.2, default=0.0
#
# candidate_decision_table_match = "blend_wide_few_bedrooms@0.80"
# branch_weights = MappingProxyType({
#     "wide_few_bedrooms":    0.80,
#     "large":                0.20,
#     "narrow_many_bedrooms": 0.00,
#     "corner":               0.00,
#     "default":              0.00,
# })
```

The `candidate_decision_table_match` string keeps the v0.2/v0.6 single-dominant-branch form for backwards-compat with any existing log-grep tooling. `branch_weights` is the structured complete trace.

**Test addition:** `test_branch_weights_sum_to_one_in_provenance`.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — #1 (multi-branch dilution / over-smoothing)

**Critique claim:** when wide_f=0.4 and large_f=0.4, blend "flattens" priors; signal lost.

**Pushback:** verified numerically. At that boundary case, blend produces strip=0.94/courtyard=0.82 (spread 0.24); single-branch dispatch produces 1.0/0.7 (spread 0.30). 20% flattening — but this **is the intended behavior of a blend at boundaries.** A plot at width=12.0m / 1 bedroom is *genuinely indecisive at the prior level* (qualifies for both wide and large rules). The blend correctly reflects this.

The proposed fix (softmax sharpening, `priors^γ`) re-introduces winner-take-all dynamics — exactly the discontinuity v0.6 #2 was designed to remove. **Recurring proposal:** v0.6 critique #10 was the same shape, also pushed back.

The base-score scoring layer (with weights summing to 1.0, criteria in [0, 1]) makes the actual call when priors are close. Push back.

### Pushback B — #3 (default dominates when signals weak)

**Critique claim:** at w_wide=0.2, w_large=0.2, w_default=0.6 means default dominates "too aggressively." Proposed: cap `w_default = min(0.5, 1 - branch_total)`.

**Pushback:** at weak signals (0.2/0.2), the default *should* dominate — that's the literal definition of "default." If no rule strongly applies, fall back. Numerical check: w_default=0.6 produces strip=0.97, central=0.91, l_shape=0.70, courtyard=0.76 — well-shaped distribution favoring the default's natural preferences (strip and central).

The proposed cap creates a non-conserved weight sum: at branch_total=0.4, capped default=0.5, total=0.9 — missing 0.1 with no specified redistribution. Breaks the `sum(weights) = 1.0` invariant that v0.7 § 14.1 just established. Push back.

### Pushback C — #4 (prior system disconnected from scoring distribution)

**Critique claim:** make prior weight adaptive: `prior_weight = f(score_variance)`. When candidates close → increase prior; when far → reduce.

**Pushback:** this is the same shape as v0.5 #1 critique (`prior_weight = min(0.15, base_gap × 2)`) — already pushed back as opaque nonlinearity. Adaptive blends mean the same input plot+brief produces different prior influence depending on what the *other* candidates score, breaking analytical reasoning ("if I increase corner_fit weight, what happens to the L-shape's final score?" becomes unanswerable without the full candidate set).

The current 0.85/0.15 fixed blend is intentionally simple, predictable, and analytically tractable. Push back.

### Pushback D — #6 (corridor_overhead tie-break noisy)

**Critique claim:** `corridor_overhead` is heuristic-on-heuristic (built from approx_length); composite `0.7*corridor_overhead + 0.3*aspect_ratio_fit` reduces noise.

**Pushback:** averaging two heuristics doesn't reduce noise — it compounds them. Both `corridor_overhead` and `aspect_ratio_fit` are computed from the same plot dimensions; their errors are correlated. The composite would be *more* sensitive to dimension-error than either alone.

Furthermore, ties on continuous floats are rare in practice; the tie-break exists for the edge case, not as a primary scoring component. Adding "only if difference > epsilon" is hysteresis — same shape as v0.4 #10 (already pushed back as state-in-pure-function). Push back.

### Pushback E — #9 (binary low_confidence too coarse)

**Critique claim:** replace `low_confidence: bool` with `confidence_score ∈ [0, 1]` (continuous).

**Pushback:** continuous confidence already exists — `candidate.score` itself is in [0, 1] and IS the topology's confidence. The `low_confidence: bool` flag is a pre-computed contract signal for downstream components per v0.5 § 14.3 (C6 expand orientation, C8 increase corridor flexibility, C9 relax placement constraints, UI surface warning).

A continuous score requires every consumer to define its own threshold, scattering threshold policy across the codebase. The bool flag concentrates the threshold in one place (here, at 0.30) where it can be tuned coherently. Consumers can still read `candidate.score` if they need finer granularity. Push back.

### Pushback F — #11 (all-branch-weights-zero edge case)

**Critique claim:** if all branches yield 0 weight, system silently collapses to default. Need explicit `provenance = "no_signal_default"` marker.

**Pushback:** verified by code-grep. v0.6 § 14.1 (carried into v0.7 § 14.1) includes `default_strip_or_central` in the `branches` tuple passed to `max(branches, key=weight)`. When all branch weights = 0, `w_default = 1.0`, and the max-by-weight correctly identifies default as dominant, producing `branch_label = "blend_default_strip_or_central@1.00"`.

The case is already explicit. The critique's proposed `"no_signal_default"` label is a cosmetic relabeling that adds no behavioral information. Push back.

### Pushback G — #12 (no cross-candidate consistency check)

**Critique claim:** "candidates may be trivial variations of same topology"; ensure they're meaningfully distinct.

**Pushback:** candidates ARE distinct `TopologyKind` values by construction. The candidate set is drawn from the 4-element set `{STRIP, CENTRAL_SPINE, L_SHAPE, COURTYARD}` and only one entry per kind ever enters the scored list. "Trivial variations of same topology" is mathematically impossible — a returned tuple cannot contain two STRIP candidates, two COURTYARD candidates, etc.

If the critique meant "candidates with similar zone-band layouts," that's also impossible: zone-band assignment is deterministic per topology kind (per v0.2 § 4.3 / v0.6 § 14.7), so two candidates of different kinds always have different zone-band shapes. Push back.

---

## § 16 — Backlog roll-up (Rule 9)

### No new backlog items in v0.7

All amendments addressable in-spec; #7 (zone-band functional checks) maps to existing **B-091** (Climate-variant zone-band assignments).

### Pre-existing backlog (carried unchanged)

- **C5:** B-085, B-086, B-087, B-088, B-089, B-090, B-091, B-092, B-093.
- **C4:** B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081, B-082, B-083, B-084.

---

## § 17 — What v0.7 LOCKS

1. **2 SPEC-AMENDMENTS** in code (§§ 14.1, 14.2). § 14.1 fixes the v0.6 math defect that allowed priors to exceed [0, 1] range.
2. **2 marginal SPEC-AMENDMENTS** (§§ 14.3, 14.4) for explainability + provenance.
3. **7 pushbacks** documented and held with explicit math/grep/scope verification (#1, #3, #4, #6, #9, #11, #12).
4. **0 new backlog items.** No duplicates.
5. Estimated delta: **~25 LOC source change + ~5 new tests** (mostly in `decision_table.py`, `select.py`, `scorers.py`, `schema.py`).
6. **Architecture identical to v0.6.** Math defect repair is internal; field additions are forward-compat; no contract-breaking.

---

## § 18 — v0.7 verification at LOCK time (estimated)

- Tier 1: ~5 new tests bringing C5 total to ~56.
- Tier 2: 0 new.
- Production code: ~25 LOC across `decision_table.py`, `select.py`, `scorers.py`, `schema.py`.
- Existing v0.6-anticipated tests adjusted for: branch-weight normalization (proper sum=1); per-topology bedroom min; top_contributors derived field; multi-branch provenance.

---

## § 19 — Cumulative C5 lineage

| Round | SPEC-AMENDMENTS | New backlog | Push-backs | Reversals | Notable |
|---:|---:|---:|---:|---:|---|
| v0.1 (DRAFT) | — | — | — | — | DRAFT-Qs surfaced |
| v0.2 (PROPOSED) | initial design | 7 | — | — | DRAFT-Qs adjudicated |
| v0.3 | 5 + 1 invariant | 1 | 2 | 1 (Q7) | Soft priors landed |
| v0.4 | 4 + 1 invariant | 1 | 5 | — | Dampened multiplier |
| v0.5 | 5 + 2 marginal | 0 | 5 | — | Additive blend |
| v0.6 | 4 + 1 marginal + 1 doc | 0 | 6 | 1 (#10) | Multi-branch blend |
| **v0.7** | **2 + 2 marginal** | **0** | **7** | **0** | **★ math defect found + fixed** |
| **Total to v0.7** | **20 + 4 marginal** | **9** | **25** | **2** | |

**Pushback rate:** 2 → 5 → 5 → 6 → **7** (steady climb; recurring critiques predominate).
**Backlog rate:** 7 → 1 → 1 → 0 → 0 → **0** (stable at zero for 3 rounds running).
**Genuine new defects per round:** 0 → 0 → 0 → 0 → **1** (v0.7 caught the v0.6 § 14.1 math bug).

---

## § 20 — Status

**v0.7 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per Rule 8, adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.8 PROPOSED, not backlog entries, until Ramalingam locks.

Per Rule 7 amended (S29): all 12 critique items verified via 5 independent checks (3 math + 2 code-grep) before this walk; no external-standards claims invoked, so web-search not required this round (per Rule 7's "if no factual claim, say so" clause).

Per Obligation 1: still no C5 code. Spec must LOCK before code build.

**Round-7 observation worth flagging:** pushback rate at 58% (7 of 12) is the highest yet, but this round caught a real math bug (D2) that escaped 4 previous rounds of review. The critique cycle produces high noise but occasionally still catches real issues. Recommend: continue critique cycles only if you suspect undiscovered defects; otherwise this v0.7 may be the right LOCK point and the architecture is ready for code build.
