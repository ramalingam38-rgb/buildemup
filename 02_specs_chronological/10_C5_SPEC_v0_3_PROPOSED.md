# BuildemUp Component 5 (Topology Selector) — SPEC v0.3 PROPOSED

**Status:** **v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.3 LOCKED".

**Generated:** S29, after C5 v0.2 PROPOSED and 10-item code-review critique walk.

This v0.3 is the **patch delta** on top of v0.2 PROPOSED. Read v0.1 (DRAFT-Qs) and v0.2 (full architecture) first, then this delta.

---

## § 13 — Rule-7 walk (v0.2 → v0.3)

### Verification gates run BEFORE this walk

1. **Code-grep on factual claims:**
   - **D2 ("buildable_bbox from C2/C4"):** confirmed C2 computes the buildable envelope **inline inside `hard_physics_checks.py`** — it is NOT exported as a public artifact. C5 cannot read it without a cross-component refactor. Files **B-092**.
   - **D4 (score normalization undefined):** spec § 4.2 weights are `(0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05)` summing exactly to 1.0; each criterion is in [0,1]. Weighted sum ∈ [0,1] mathematically. The clamp is defensive belt-and-braces. Critique factually wrong; pushback.
   - **D7:** matches B-091 description exactly. Already filed.
   - **D9:** v0.2 design already lists `climate_fit`, `open_side_count`, `aspect_ratio_fit` as 3 independent criteria. Critique describes them as 1.
2. **Web research:** none required (no external-standards claims).

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| D1 | Decision-table hard filter creates discontinuities | **VALID — SPEC-AMENDMENT** |
| D2 | Width-only thresholds ignore depth-after-setbacks | **PARTIALLY VALID — small SPEC-AMENDMENT + B-092** |
| D3 | Static weights wrong in extreme contexts | **VALID — SPEC-AMENDMENT** |
| D4 | Score normalization undefined | **MISFRAMED — PUSH BACK** (math holds when weights sum to 1) |
| D5 | Drop threshold 0.30 → can crash on edge plots | **VALID — SPEC-AMENDMENT (Q7 reversal)** |
| D6 | Tie-break absolute Δ → noise-sensitive | **VALID — SPEC-AMENDMENT** |
| D7 | Zone-band rigid; should flip per open_sides | **DUPLICATE — already B-091** |
| D8 | CorridorSketch missing length + connectivity | **VALID — SPEC-AMENDMENT** |
| D9 | Climate fit too generic for Indian micro-climates | **MISFRAMED — PUSH BACK** (3 separate criteria already; micro-climate is B-069) |
| D10 | Failure mode too aggressive (truncated text) | **DUPLICATE of D5** |

**Tally:** 5 SPEC-AMENDMENTS (D1, D3, D5, D6, D8) · 1 PARTIAL + BACKLOG (D2 → small in-table guard + B-092) · 2 DUPLICATES (D7, D10) · 2 PUSH-BACKS (D4, D9).

**Explicit Q7 reversal:** D5 reverses my own v0.1 → v0.2 Q7 adjudication ("hard RuntimeError on all-fail"). Reasoning in v0.3 § 14.5.

---

## § 14 — v0.3 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Decision table → soft priors (D1)

**v0.2 § 4.1 amended.** Replace hard-filter decision table with prior-weight assignment. ALL 4 topologies are generated; the decision-table branch assigns a multiplier on the score (1.0 = preferred, 0.7 = neutral, 0.4 = disfavoured but not dropped, 0.0 = structurally impossible).

```python
@dataclass(frozen=True)
class TopologyPriors:
    """Soft prior multipliers assigned by the decision-table branch."""
    strip: float
    central_spine: float
    l_shape: float
    courtyard: float

# v0.3 (D1): instead of returning a candidate set, the decision-table assigns
# priors. Final score = base_score × prior. ALL 4 candidates always enter
# scoring; priors smooth the transition across thresholds.
def assign_priors(plot: Plot, room_brief: FloorRoomBrief) -> tuple[TopologyPriors, str]:
    if plot.width_m >= _WIDE_THRESHOLD_M and room_brief.bedroom_count <= 2:
        return TopologyPriors(strip=1.0, central_spine=0.7, l_shape=0.4, courtyard=0.4), \
               "wide_few_bedrooms"
    if plot.width_m < _NARROW_THRESHOLD_M and room_brief.bedroom_count >= 2:
        return TopologyPriors(strip=0.4, central_spine=1.0, l_shape=0.4, courtyard=0.4), \
               "narrow_many_bedrooms"
    if plot.corner_plot:
        return TopologyPriors(strip=0.7, central_spine=0.4, l_shape=1.0, courtyard=0.4), \
               "corner"
    if plot.width_m >= _LARGE_W_THRESHOLD_M and plot.depth_m >= _LARGE_D_THRESHOLD_M:
        return TopologyPriors(strip=0.7, central_spine=0.4, l_shape=0.4, courtyard=1.0), \
               "large"
    return TopologyPriors(strip=1.0, central_spine=1.0, l_shape=0.4, courtyard=0.4), \
           "default_strip_or_central"
```

**Effect:** at width = 7.91m vs 7.92m, the score for STRIP changes from `base × 1.0` → `base × 0.7` instead of "single STRIP candidate" → "STRIP + CENTRAL_SPINE candidates set". Smooth transition.

L-shape on a non-corner plot still scores poorly because `corner_fit = 0` independently in the scorer (§ 4.2). Courtyard on a small plot scores poorly because `width_fit = 0`. Priors prevent these from spuriously winning while letting them participate when they're genuinely competitive.

### § 14.2 — Wide-but-shallow guard (D2 — small in-table fix)

**v0.2 § 4.1 amended.** Add a single defensive guard for the "wide_few_bedrooms" branch:

```python
# Wide-but-shallow plot pathology: width ≥ 7.92m but depth < 0.6×width
# means STRIP topology has nowhere to put the public→service→circulation
# →private bands. Demote STRIP from prior=1.0 to prior=0.7 in this case.
if plot.width_m >= _WIDE_THRESHOLD_M and room_brief.bedroom_count <= 2:
    if plot.depth_m < 0.6 * plot.width_m:
        return TopologyPriors(strip=0.7, central_spine=1.0, l_shape=0.4, courtyard=0.4), \
               "wide_few_bedrooms_but_shallow"
    return TopologyPriors(strip=1.0, central_spine=0.7, l_shape=0.4, courtyard=0.4), \
           "wide_few_bedrooms"
```

Reads `plot.width_m` and `plot.depth_m` directly because the buildable envelope is not yet a C2 public output (B-092). Documented limitation: the 0.6 ratio is on RAW dimensions, not post-setback. C5 v1 trusts that for typical residential setbacks (3-5m total) the relative ratio is preserved. Filed as B-092 below.

### § 14.3 — Context-aware weight multipliers (D3)

**v0.2 § 4.2 amended.** Base weights stay; per-context multipliers adjust them. Multipliers normalize back to sum=1.0 by per-criterion proportional rebalancing.

```python
BASE_WEIGHTS = MappingProxyType({
    "width_fit":         0.25,
    "bedroom_fit":       0.20,
    "open_side_count":   0.15,
    "climate_fit":       0.15,
    "corner_fit":        0.10,
    "aspect_ratio_fit":  0.10,
    "corridor_overhead": 0.05,
})

def context_weight_multipliers(plot: Plot, tier: PlotTier) -> dict[str, float]:
    """Per-context multipliers BEFORE renormalization to sum=1."""
    m = {k: 1.0 for k in BASE_WEIGHTS}
    if plot.corner_plot:
        m["corner_fit"]        = 2.0   # boost: corner_fit must be decisive on corner plots
        m["width_fit"]         = 0.6   # reduce: width matters less when L-shape is in play
    if tier == PlotTier.T3_LARGE:
        m["width_fit"]         = 0.5   # reduce: large plots fit any topology width-wise
        m["corridor_overhead"] = 2.0   # boost: corridor cost matters on big plots
        m["climate_fit"]       = 1.5   # boost: courtyard becomes a real option
    if tier == PlotTier.T1_COMPACT:
        m["bedroom_fit"]       = 1.5   # boost: tight plots → bedroom packing dominates
    return m

def effective_weights(plot: Plot, tier: PlotTier) -> Mapping[str, float]:
    mults = context_weight_multipliers(plot, tier)
    raw = {k: BASE_WEIGHTS[k] * mults[k] for k in BASE_WEIGHTS}
    total = sum(raw.values())
    return MappingProxyType({k: v / total for k, v in raw.items()})
```

Renormalization preserves the invariant that `sum(weights) == 1.0` (preserves the D4 push-back's correctness guarantee).

**Test addition:** `test_effective_weights_sum_to_one_for_all_contexts` (Hypothesis: any plot+tier combo).

### § 14.4 — Soft drop + always-return-top (D5, **Q7 reversal**)

**v0.2 § 4.4 + § 4.5 amended.** Combined into one section.

```python
def select_candidates(scored: list[ScoredCandidate]) -> tuple[TopologyCandidate, ...]:
    """v0.3 (D5, Q7 reversal): always return at least one candidate; threshold
    filters secondary candidates only.

    Reversal rationale: v0.2 § 4.5 chose hard-fail RuntimeError borrowing C4's
    fail-fast philosophy. That was wrong. C4's fail-fast guards DATA correctness
    (KB drift = wrong building); C5's would guard against SCORING confidence
    (no candidate scored ≥ 0.30). Scoring confidence is observability, not
    correctness. Always return the best available; surface low-confidence as
    a flag on the candidate, not a crash.
    """
    if not scored:
        # Decision-table always produces 4 candidates (priors > 0). This branch
        # is genuinely unreachable; defensive only.
        raise RuntimeError("no candidates produced — decision-table bug")

    scored.sort(key=lambda c: c.score, reverse=True)
    top = scored[0]
    out = [_to_candidate(top, low_confidence=top.score < 0.30)]

    # Tie-break (D6: relative): include 2nd if (top.score - 2nd.score) / top.score ≤ 0.10
    # AND 2nd.score >= 0.30. Include 3rd if 2nd was included AND relative_delta ≤ 0.15
    # AND 3rd.score >= 0.30.
    if len(scored) >= 2 and scored[1].score >= 0.30:
        if top.score > 0 and (top.score - scored[1].score) / top.score <= 0.10:
            out.append(_to_candidate(scored[1], low_confidence=False))
            if len(scored) >= 3 and scored[2].score >= 0.30:
                if (top.score - scored[2].score) / top.score <= 0.15:
                    out.append(_to_candidate(scored[2], low_confidence=False))

    return tuple(out)
```

**Effect:** RuntimeError on "all candidates < 0.30" is gone. The top candidate always returns, with `low_confidence=True` flag on its `justification` field when score < 0.30. Downstream (C6, C8, C9) can read this flag and surface it in the user-facing review report.

### § 14.5 — Relative tie-break (D6)

Combined into § 14.4 above. Switch from absolute `top - cand ≤ 0.10` to relative `(top - cand) / top ≤ 0.10`. Defensive guard `top.score > 0` prevents div-zero (only triggers in the unreachable empty-scored branch).

### § 14.6 — CorridorSketch additional fields (D8)

**v0.2 § 3 amended.** `CorridorSketch` gains two fields:

```python
class ConnectivityType(str, Enum):
    LINEAR    = "linear"     # Strip, Central Spine — corridor with two endpoints
    BRANCHED  = "branched"   # L-shape — two arms meeting at a junction
    LOOP      = "loop"       # Courtyard — corridor wraps around the open space


@dataclass(frozen=True)
class CorridorSketch:
    position: CorridorPosition
    nominal_width_m: float
    runs_along: PlotOrientation
    approx_length_m: float                # NEW v0.3 (D8)
    connectivity_type: ConnectivityType   # NEW v0.3 (D8)
```

Connectivity is fully determined by topology kind (Strip/Central Spine = LINEAR; L-shape = BRANCHED; Courtyard = LOOP). `approx_length_m` is computed from topology + plot dims:

| Topology | approx_length_m formula |
|---|---|
| STRIP | 0 (no corridor; rooms accessed directly) when CorridorPosition.NONE; else `plot.depth_m × 0.85` |
| CENTRAL_SPINE | `plot.depth_m × 0.85` |
| L_SHAPE | `(plot.width_m + plot.depth_m) × 0.5` (sum of two arms' usable lengths) |
| COURTYARD | `2 × (plot.width_m + plot.depth_m) × 0.4` (inner perimeter) |

The 0.85 / 0.5 / 0.4 multipliers approximate the post-setback usable run; refined by C8.

### § 14.7 — Math invariant test (D4 push-back hardening)

**v0.2 § 7 amended.** Adds one test that codifies the D4 mathematical invariant:

```python
def test_scoring_weights_sum_to_one_in_all_contexts():
    """v0.3 (D4 pushback hardening): the score-clamping argument depends on
    weights summing to 1.0. Hypothesis-test that it holds for any plot context.
    """
    # exhaustive over PlotTier values + corner_plot True/False
    for tier in PlotTier:
        for corner in (False, True):
            plot = _build_test_plot(tier=tier, corner=corner)
            weights = effective_weights(plot, tier)
            assert abs(sum(weights.values()) - 1.0) < 1e-9
```

Mathematical correctness regression-locked; if a future weight tweak breaks the invariant, the test catches it before scoring math drifts.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — D4 (score normalization)

**Critique claim:** "No guarantee weighted sum stays within range."

**Pushback:** weights = `(0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05)`, sum = 1.0 exact. Each criterion ∈ [0,1] per spec § 4.2. Therefore weighted sum ∈ [0,1] mathematically. The clamp is defensive belt-and-braces (catches future bugs where someone makes a criterion return > 1 by accident).

The proposed Option A (`sum(weighted) / sum(weights)`) reduces to `sum(weighted)` when `sum(weights) == 1.0` — same numerical result, additional division overhead. The proposed Option B (min-max normalize across candidates) actively makes things worse: a single very-bad candidate would inflate the apparent score of merely-bad candidates, and absolute scores lose meaning (the 0.30 low-confidence flag wouldn't survive).

v0.3 § 14.7 adds an invariant test that locks the sum=1.0 property so future weight edits can't break the math silently. **No code change to the math itself; pushback stands.**

### Pushback B — D9 (climate-fit oversimplification)

**Critique claim:** Climate is a "single climate flag" influencing scoring; should combine with `open_sides` and `aspect_ratio`.

**Pushback:** v0.2 § 4.2 already lists `climate_fit`, `open_side_count`, and `aspect_ratio_fit` as **three independent weighted criteria**. Each contributes its own signal to the final score, observable in `score_breakdown`. The proposed fix (combine into composite) reduces 3 independent signals to 1 — actively less debuggable.

The genuine micro-climate concern (Mumbai coastal vs Pune inland behaving differently) is real but is **B-069** (Composite-zone sub-classification, already filed in C4 backlog). When B-069 lands, `ClimateZone` gains sub-classes and `climate_fit` automatically benefits from finer granularity without C5 spec changes. **No change in v0.3.**

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog item

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-092 | Promote BuildableEnvelope to a public C2 output (or PlotAnalysis field). C2 currently computes `env_w = plot.width_m - setback_left - setback_right` and `env_d = plot.depth_m - setback_front - setback_rear` inline inside `hard_physics_checks.py`; not exported. C5 (and any future component needing post-setback geometry) is forced either to re-derive — DRY violation, B-072 anti-pattern — or to use raw plot dims as an approximation. | v0.3 walk D2 | C5/C6/C8 layouts diverge between raw-plot-dim and post-setback-dim assumptions in user testing, OR another component needs post-setback geometry | OUT (v0.3) | ~30 LOC + cross-component coordination + test alignment |

### Pre-existing C5 backlog (carried)

B-085 (ML topology scoring), B-086 (more topology kinds), B-087 (multi-floor coord), B-088 (Vastu zone bands), B-089 (user override), B-090 (recalibrate thresholds), B-091 (climate-variant zone bands).

### Pre-existing C4 backlog (unchanged)

B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081, B-082, B-083, B-084.

---

## § 17 — What v0.3 LOCKS

1. **5 SPEC-AMENDMENTS** in code (§§ 14.1, 14.2, 14.3, 14.4–14.5, 14.6).
2. **1 invariant test** added (§ 14.7) hardening the D4 pushback.
3. **1 explicit Q7 adjudication reversal** (D5 / § 14.4): RuntimeError-on-all-fail removed; `low_confidence` flag carries the signal instead.
4. **1 new backlog item** filed (B-092).
5. **2 pushbacks** documented and held (D4, D9).
6. **3 duplicates / collapses** noted: D7 → B-091, D10 → D5, D2-deeper → B-092.
7. Estimated delta: **~50 LOC source change + ~6 new tests** (mostly in `decision_table.py`, `scorers.py`, `select.py`, `schema.py`).
8. **Architecture identical to v0.2.** Field additions on `CorridorSketch` are forward-compat; no contract-breaking.

---

## § 18 — v0.3 verification at LOCK time (estimated)

- Tier 1: ~6 new tests bringing total to ~38.
- Tier 2: 0 new.
- Production code: ~50 LOC across `decision_table.py`, `scorers.py`, `select.py`, `schema.py`.
- Existing v0.2-anticipated tests adjusted for: priors instead of candidate-set; relative tie-break thresholds; CorridorSketch new fields; low_confidence flag instead of RuntimeError.

---

## § 19 — Status

**v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per Rule 8, adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.4 PROPOSED, not backlog entries, until Ramalingam locks.

Per Rule 7 amended (S29): all factual claims in the critique were verified via code-grep (4 grepps) before this walk; D2's claim about a buildable_bbox in C2/C4 was **falsified** (the math is inline in hard_physics_checks; no public artifact); D4's claim about score normalization was **falsified mathematically** (weights sum to 1, criteria in [0,1] → weighted sum in [0,1]). Walk verdicts are grounded in those checks.
