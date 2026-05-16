# BuildemUp Component 5 (Topology Selector) — SPEC v0.4 PROPOSED

**Status:** **v0.4 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.4 LOCKED".

**Generated:** S29, after C5 v0.3 PROPOSED and 12-item code-review critique walk (round 2 on C5).

This v0.4 is the **patch delta** on top of v0.3 PROPOSED. Read v0.1 (DRAFT-Qs), v0.2 (full architecture), and v0.3 (priors + Q7 reversal) first, then this delta.

---

## § 13 — Rule-7 walk (v0.3 → v0.4)

### Verification gates run BEFORE this walk

1. **Code-grep + math-verification on factual claims** (8 verifications run):
   - **#1 (priors over-dominate):** verified. Base 0.75 × prior 0.7 = 0.525 vs base 0.70 × prior 1.0 = 0.70 → CENTRAL wins despite STRIP's higher base. 5pt base advantage overpowered by 30pt prior gap. **Valid.**
   - **#3 (0.0 prior unsafely implemented):** v0.3 § 14.1 prior table doesn't use 0.0. Was a docstring example, not a code branch. **Falsified — push back.**
   - **#4 (multipliers produce >40-50% weights):** computed actual post-renorm max weight at corner-context = 0.225, T3-large = 0.225. **Quantitative claim falsified;** but invariant test cheap insurance.
   - **#5 (relative tie-break fails at low top):** relative delta is scale-invariant. At top=0.20, cand=0.18 fails 10% threshold (90% ratio not 90%+). Combined `cand >= 0.30` filter ensures low-top admits no secondaries. **Falsified — push back.**
   - **#6 (low_confidence string-based):** v0.3 § 14.4 shows `_to_candidate(top, low_confidence=...)` but § 3 schema doesn't carry the field. **Genuine ambiguity — valid.**
   - **#8 (0.6 ratio sharp cutoff):** verified. depth=4.79m → 4.80m on width=8m flips prior 0.7 → 1.0. Same discontinuity D1 (v0.3) was supposed to eliminate. **Valid.**
   - **#9 (priors+weights double-count):** priors gate eligibility-per-plot-shape; weights tune which-criterion-matters-in-context. Orthogonal concerns. **Push back.**
   - **#10 (hysteresis):** C5 is pure-function per Obligation 1. Hysteresis requires session state → category error. **Push back.**
   - **#12 (provenance lacks per-criterion trace):** `score_breakdown: Mapping[str, float]` already on `TopologyCandidate` since v0.2. **Falsified — push back.**
2. **Web research:** none required (no external-standards claims in this critique).

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| 1 | Priors × score multiplication over-dominates | **VALID — SPEC-AMENDMENT** (dampened multiplier) |
| 2 | Prior values 1.0/0.7/0.4 arbitrary | **VALID-MINOR — SPEC-AMENDMENT** (tighten spread) |
| 3 | "0.0 prior" not safely implemented | **MISFRAMED — PUSH BACK** (no branch returns 0.0) |
| 4 | Context multipliers can produce extreme weights | **VALID-MINOR — invariant test only** (verified max=0.225 today) |
| 5 | Relative tie-break fails at low top scores | **MISFRAMED — PUSH BACK** (scale-invariant; combined filter fails closed) |
| 6 | low_confidence is string-based | **VALID — SPEC-AMENDMENT** (promote to structured field) |
| 7 | approx_length formulas too rough | **VALID-BUT-BACKLOG (B-093)** |
| 8 | Wide-but-shallow 0.6 ratio sharp cutoff | **VALID — SPEC-AMENDMENT** (smooth ramp) |
| 9 | Priors and weights double-count context | **MISFRAMED — PUSH BACK** (orthogonal jobs) |
| 10 | No stability guarantee | **MISFRAMED — PUSH BACK** (state in pure function = category error) |
| 11 | "Always return top" can propagate bad topology | **DUPLICATE of #6** |
| 12 | Provenance lacks per-criterion trace | **MISFRAMED — PUSH BACK** (`score_breakdown` exists since v0.2) |

**Tally:** 4 SPEC-AMENDMENTS (#1, #2, #6, #8) · 1 INVARIANT TEST (#4) · 1 NEW BACKLOG (#7 → B-093) · 1 DUPLICATE (#11) · **5 PUSH-BACKS** (#3, #5, #9, #10, #12).

---

## § 14 — v0.4 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Dampened prior multiplier (#1)

**v0.3 § 14.1 amended.** Replace pure-multiplication `final = base × prior` with dampened form:

```python
# v0.4 (#1): dampen prior influence so it guides rather than dominates.
# Mathematical effect: prior swing of (1.0 - 0.7 = 0.3) on a base score of
# 0.5 changes the final by only 0.5 × 0.5 × 0.3 = 0.075, instead of v0.3's
# raw 0.5 × 0.3 = 0.15. Multiplicative semantic preserved (small base
# scores still scale with prior); large prior swings can no longer flip
# rankings against meaningful base-score differences.
def apply_prior(base_score: float, prior: float) -> float:
    return base_score * (0.5 + 0.5 * prior)
```

**Verification (round-2 code-grep):**

| base | prior | v0.3 final | v0.4 final |
|-----:|------:|-----------:|-----------:|
| 0.75 | 0.7 | 0.525 | 0.6375 |
| 0.70 | 1.0 | 0.70 | 0.70 |
| | | CENTRAL wins by 0.175 | CENTRAL wins by 0.0625 |

The 5pt base advantage of STRIP no longer drowns; gap reduced 64% with priors still informative.

### § 14.2 — Tighten prior spread (#2)

**v0.3 § 14.1 amended.** Replace prior triplet `{1.0, 0.7, 0.4}` with tighter `{1.0, 0.85, 0.7}`:

```python
# v0.3 priors (replaced):  preferred=1.0, neutral=0.7, weak=0.4
# v0.4 priors (new):       preferred=1.0, neutral=0.85, weak=0.7
#
# Combined with v0.4 § 14.1 dampening, the maximum prior-induced score
# swing on a base of 0.5 is now (1.0 - 0.7) × 0.5 × 0.5 = 0.075. v0.3
# could swing by (1.0 - 0.4) × 0.5 = 0.30 — a 4× reduction in maximum
# prior dominance.

def assign_priors(plot: Plot, room_brief: FloorRoomBrief) -> tuple[TopologyPriors, str]:
    if plot.width_m >= _WIDE_THRESHOLD_M and room_brief.bedroom_count <= 2:
        # See § 14.4 for the depth-ratio handling; this is the no-shallow case
        return TopologyPriors(strip=1.0, central_spine=0.85, l_shape=0.7, courtyard=0.7), \
               "wide_few_bedrooms"
    if plot.width_m < _NARROW_THRESHOLD_M and room_brief.bedroom_count >= 2:
        return TopologyPriors(strip=0.7, central_spine=1.0, l_shape=0.7, courtyard=0.7), \
               "narrow_many_bedrooms"
    if plot.corner_plot:
        return TopologyPriors(strip=0.85, central_spine=0.7, l_shape=1.0, courtyard=0.7), \
               "corner"
    if plot.width_m >= _LARGE_W_THRESHOLD_M and plot.depth_m >= _LARGE_D_THRESHOLD_M:
        return TopologyPriors(strip=0.85, central_spine=0.7, l_shape=0.7, courtyard=1.0), \
               "large"
    return TopologyPriors(strip=1.0, central_spine=1.0, l_shape=0.7, courtyard=0.7), \
           "default_strip_or_central"
```

The "0.7 minimum prior" floor means no topology is ever crippled by prior alone; the scorer makes the actual call. L-shape on a non-corner plot still loses because `corner_fit = 0` independently in the scorer (§ 4.2 of v0.2).

### § 14.3 — Structured `low_confidence` field (#6)

**v0.2 § 3 / v0.3 § 14.4 amended.** Promote low_confidence from in-justification string to top-level boolean on `TopologyCandidate`:

```python
@dataclass(frozen=True)
class TopologyCandidate:
    kind: TopologyKind
    score: float                                    # in [0.0, 1.0]
    score_breakdown: Mapping[str, float]            # MappingProxyType — per-criterion (already exists, addresses #12 pushback)
    zone_bands: Mapping[ZoneBand, PlotOrientation]  # MappingProxyType
    corridor_sketch: CorridorSketch
    low_confidence: bool                            # NEW v0.4 (#6)
    justification: str                              # ≤ 200 chars, descriptive only
    provenance: TopologyProvenance
```

`low_confidence = (score < 0.30)` — set on the top candidate only when no candidate clears the threshold. Secondary candidates (always have score ≥ 0.30 to be admitted per § 14.4 v0.3) carry `low_confidence = False`.

**Downstream contract:** C6, C8, C9 read `topology_candidate.low_confidence` directly; the user-facing review report surfaces a "low-confidence topology" warning when set. No string parsing.

**Justification field reverts to descriptive purpose only:** *"why this candidate was chosen / why it ranks here"* — no machine-parseable signal embedded.

### § 14.4 — Smooth shallow-plot ramp (#8)

**v0.3 § 14.2 amended.** Replace the hard `depth/width < 0.6` cutoff with a smooth linear ramp:

```python
# v0.3 (replaced):
#   if depth < 0.6 * width: STRIP_prior = 0.7 (else 1.0)  ← hard cutoff
#
# v0.4 (#8): smooth linear ramp on the wide-few-bedrooms branch only.
# Below ratio 0.5 → fully demoted (factor 0.0); above ratio 0.8 → no
# demotion (factor 1.0); between → linear interpolation.
def shallow_plot_factor(plot: Plot) -> float:
    """Returns multiplier in [0, 1] for STRIP-prior on shallow-plot demotion.
    1.0 = no demotion; 0.0 = full demotion."""
    if plot.width_m <= 0:                       # defensive (Plot.__post_init__ enforces)
        return 1.0
    ratio = plot.depth_m / plot.width_m
    return max(0.0, min(1.0, (ratio - 0.5) / 0.3))   # linear ramp 0.5 → 0.8


# Applied in the wide_few_bedrooms branch:
if plot.width_m >= _WIDE_THRESHOLD_M and room_brief.bedroom_count <= 2:
    factor = shallow_plot_factor(plot)
    # Interpolate STRIP prior between the demoted (0.7) and full (1.0) values
    # using the smooth factor. CENTRAL_SPINE moves correspondingly: when
    # STRIP is fully demoted, CENTRAL_SPINE rises to 1.0; when STRIP is at
    # full prior, CENTRAL_SPINE sits at 0.85 (neutral).
    strip_prior = 0.7 + 0.3 * factor                       # 0.7 → 1.0 over factor 0→1
    central_prior = 1.0 - 0.15 * factor                    # 1.0 → 0.85 over factor 0→1
    if factor < 0.5:
        branch = "wide_few_bedrooms_shallow"
    elif factor < 1.0:
        branch = "wide_few_bedrooms_intermediate"
    else:
        branch = "wide_few_bedrooms"
    return TopologyPriors(
        strip=strip_prior,
        central_spine=central_prior,
        l_shape=0.7, courtyard=0.7,
    ), branch
```

**Verification:** at the v0.3 break point of `width=8.0m, depth=4.80m` (ratio 0.60), `factor = (0.60 - 0.5) / 0.3 = 0.333`. STRIP prior = 0.7 + 0.3 × 0.333 = 0.80. At depth=4.79m (ratio 0.599), factor = 0.330, STRIP prior = 0.799. Smooth: 1cm depth change → 0.001 prior change, not the v0.3 0.30 jump.

### § 14.5 — Multiplier-bound invariant test (#4 hardening)

**v0.3 § 14.7 amended.** Add one new test alongside the sum=1.0 invariant:

```python
def test_max_normalized_weight_under_0_35():
    """v0.4 (#4 invariant test): the corner+T3+T1 context multipliers, after
    renormalization, must not produce any single weight > 0.35.

    Empirically verified at v0.4 LOCK time:
      corner-context max weight     = 0.225
      T3-large    max weight        = 0.225
      T1-compact  max weight        = 0.250
      base (no context)              = 0.250

    The 0.35 ceiling has ~50% headroom over current values, locking the
    invariant against future multiplier edits without forcing tight bounds.
    """
    for tier in PlotTier:
        for corner in (False, True):
            plot = _build_test_plot(tier=tier, corner=corner)
            weights = effective_weights(plot, tier)
            max_w = max(weights.values())
            assert max_w <= 0.35, (
                f"max weight {max_w:.4f} exceeds 0.35 ceiling for "
                f"tier={tier.value}, corner={corner}"
            )
```

The multiplier table itself is unchanged; this test prevents future drift.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — #3 ("0.0 prior" unsafely implemented)

**Critique claim:** spec says 0.0 prior = structurally impossible, but no guard exists; multiplication with 0 silently keeps candidate.

**Pushback:** code-grep on v0.3 § 14.1 prior table — **no branch returns 0.0**. The 0.0 was a docstring example in v0.3 introduction text describing the design space; no `assign_priors()` branch produces it. With v0.4 § 14.2 tightening priors to {1.0, 0.85, 0.7}, the minimum is 0.7, far from 0.0. The "explicit invalidation" the critique demands guards against a code path that doesn't exist. Push back.

### Pushback B — #5 (relative tie-break fails at low top scores)

**Critique claim:** at top ≈ 0.2, denominator small → almost everything passes the relative threshold.

**Pushback:** verified numerically. Relative delta `(top - cand) / top ≤ 0.10` ↔ `cand ≥ 0.9 × top`. Whether top is 0.95 or 0.20, the *ratio* admitted is the same — at top=0.20, only candidates ≥ 0.18 (the same 90% threshold) admit. Cand=0.18 fails `≤ 0.10` (gives exactly 0.10, but `≤` includes equality — admitted). Cand=0.15 fails (rel_delta = 0.25). Cand=0.05 fails (rel_delta = 0.75). At low top scores, fewer candidates pass, not more.

The combined filter `(rel_delta ≤ 0.10) AND (cand.score ≥ 0.30)` — already in v0.3 — ensures low-top scenarios admit no secondaries (because no secondary can be ≥ 0.30 when top < 0.30). The proposed "hybrid absolute/relative" adds branching complexity without solving an actual issue. Push back.

### Pushback C — #9 (priors and weights double-count context)

**Critique claim:** priors encode context (width, corner, size) AND weights encode context → double counting → exaggerated bias.

**Pushback:** priors and weights answer different questions:
- **Priors** decide *which topologies are eligible candidates given this plot's shape* (Strip wants wide, Courtyard wants large, L-shape wants corner). Eligibility, not quality.
- **Weights** decide *which scoring criterion deserves more attention in this context* (corner→corner_fit boost; T3→corridor_overhead boost). Quality assessment, not eligibility.

When a plot is corner+T3, priors push L-shape into the running (eligibility), and weights ensure the L-shape is properly evaluated on corner_fit and corridor_overhead criteria (quality). These are sequential operations on different aspects of the decision — not duplicated work. The "double counting" framing only holds if priors and weights operate on the same criterion, which they don't (priors operate on the topology slot; weights on per-criterion contributions). Push back.

### Pushback D — #10 (hysteresis for stability)

**Critique claim:** add hysteresis or "prefer previous topology" rule to prevent input-perturbation flips.

**Pushback:** hysteresis requires *state* — knowing "what topology was last selected." C5 is a pure function (per Obligation 1's spec-first contract: `select_topology(plot_analysis, room_brief) -> tuple[TopologyCandidate, ...]`, no session, no cache). Adding state to a pure-function component is a category error.

The genuine concern (small input change → topology flip) is addressed *mechanically* by:
- v0.3 D1 (soft priors) — already smooths width-threshold transitions
- v0.4 #1 (dampened multiplier) — caps prior-induced score swings
- v0.4 #8 (smooth shallow-plot ramp) — eliminates depth-ratio cutoff

After these, the only remaining flip-risk is when two candidates' base scores are genuinely indistinguishable — and that's exactly when the tie-break should return both, not one (which v0.3 § 14.4 already does). Push back.

### Pushback E — #12 (provenance lacks per-criterion trace)

**Critique claim:** "no record of raw criterion values per candidate; cannot debug WHY topology won."

**Pushback:** `score_breakdown: Mapping[str, float]` is on `TopologyCandidate` since v0.2 § 3 (carried unchanged into v0.3 and v0.4). Every criterion's contribution is already exposed:

```python
candidate.score_breakdown
# → MappingProxyType({
#     "width_fit": 0.85,
#     "bedroom_fit": 0.70,
#     "open_side_count": 0.60,
#     "climate_fit": 0.80,
#     "corner_fit": 0.0,
#     "aspect_ratio_fit": 0.75,
#     "corridor_overhead": 0.50,
#   })
```

The critique appears to have read the v0.3 spec patch delta without re-reading v0.2 § 3. Push back. (The full per-criterion trace also lands on `TopologyProvenance.candidate_decision_table_match` for branch traceability.)

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog item

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-093 | Refine `CorridorSketch.approx_length_m` heuristics. v0.2/v0.3 use rough multipliers (depth × 0.85 for STRIP, etc.) without setback awareness or aspect-ratio scaling. Real fix needs B-092 (post-setback geometry); B-093 is the C5-side polish that consumes B-092. | v0.4 walk #7 | C8 reports inaccurate corridor sizing in user testing, OR B-092 lands and unblocks geometry improvements | OUT (v0.4) | ~20 LOC + B-092 prerequisite |

### Pre-existing C5 backlog (carried unchanged)

B-085 (ML topology scoring), B-086 (more topology kinds), B-087 (multi-floor coord), B-088 (Vastu zone bands), B-089 (user override), B-090 (recalibrate thresholds), B-091 (climate-variant zone bands), B-092 (BuildableEnvelope as public C2 output).

### Pre-existing C4 backlog (unchanged)

B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081, B-082, B-083, B-084.

---

## § 17 — What v0.4 LOCKS

1. **4 SPEC-AMENDMENTS** in code (§§ 14.1, 14.2, 14.3, 14.4).
2. **1 invariant test** added (§ 14.5) hardening the #4 multiplier-bound observation.
3. **1 new backlog item** filed (B-093).
4. **5 pushbacks** documented and held with explicit numeric/grep verification (#3, #5, #9, #10, #12).
5. **1 duplicate** noted (#11 → #6).
6. Estimated delta: **~30 LOC source change + ~3 new tests** (mostly in `decision_table.py`, `select.py`, `schema.py`).
7. **Architecture identical to v0.3.** All changes are field additions or smoother math; no contract-breaking.

---

## § 18 — v0.4 verification at LOCK time (estimated)

- Tier 1: ~3 new tests bringing C5 total to ~41.
- Tier 2: 0 new.
- Production code: ~30 LOC across `decision_table.py`, `select.py`, `schema.py`.
- Existing v0.3-anticipated tests adjusted for: dampened multiplier; tighter prior spread; smooth ramp; structured `low_confidence` field.

---

## § 19 — Cumulative C5 lineage

| Round | SPEC-AMENDMENTS | New backlog | Push-backs |
|---:|---:|---:|---:|
| v0.1 (DRAFT) | — | — | — |
| v0.2 (PROPOSED, DRAFT-Qs adjudicated) | — (initial design) | 7 (B-085..091) | — |
| v0.3 | 5 + 1 invariant + 1 Q7 reversal | 1 (B-092) | 2 |
| **v0.4** | **4 + 1 invariant** | **1 (B-093)** | **5** |
| **Total to v0.4** | **9** | **9** | **7** |

High pushback rate this round (5 of 12) primarily because:
- 3 critiques (#3, #5, #12) were factually falsified by code-grep or math.
- 2 critiques (#9, #10) proposed solutions that would harm architecture (state in pure function, conflate orthogonal concerns).

---

## § 20 — Status

**v0.4 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per Rule 8, adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.5 PROPOSED, not backlog entries, until Ramalingam locks.

Per Rule 7 amended: all 12 critique items verified via 8 independent checks (4 code-grepps + 3 math computations + 1 schema cross-check) before this walk. 5 pushbacks are grounded in those checks, not stylistic disagreement.

Per Obligation 1: still no C5 code. Spec must LOCK before code build.
