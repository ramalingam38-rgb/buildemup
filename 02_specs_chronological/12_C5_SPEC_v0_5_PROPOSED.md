# BuildemUp Component 5 (Topology Selector) — SPEC v0.5 PROPOSED

**Status:** **v0.5 PROPOSED. PENDING Ramalingam LOCK adjudication.** Per Rule 8, this version is not LOCKED until Ramalingam explicitly says "lock it" / "v0.5 LOCKED".

**Generated:** S29, after C5 v0.4 PROPOSED and 12-item code-review critique walk (round 3 on C5).

This v0.5 is the **patch delta** on top of v0.4 PROPOSED. Read v0.1–v0.4 first.

---

## § 13 — Rule-7 walk (v0.4 → v0.5)

### Verification gates run BEFORE this walk

1. **Math + code-grep verifications** (6 checks run):
   - **#1 (multiplicative still distorts):** verified. At base 0.85+ with prior gap 0.3, additive `0.85 × base + 0.15 × prior` caps prior swing at 0.045 vs v0.4 multiplicative's 0.135. **Valid.**
   - **#2 (lower prior floor 0.7 → 0.5):** would REVERSE v0.4 #2's tightening of {1.0, 0.7, 0.4} → {1.0, 0.85, 0.7}. Combined with v0.4 #1 dampening, 0.7 floor is correct. **Push back.**
   - **#5 (score_breakdown lacks weight/contribution):** code-grep confirmed `score_breakdown: Mapping[str, float]` — flat raw-score map only. To debug "why A beat B" need (raw, weight, contribution) per criterion. **Valid; sharper than #12 last round.**
   - **#6 (distribution shape uncontrolled):** sum=1.0 + max≤0.35 already implicitly bracket shape (min-mean ≥ ~0.108). Adding entropy bounds is solution looking for a problem. **Push back.**
   - **#7 (approx_length influences scoring):** corridor_overhead weight is 0.05 (lowest of 7 criteria). Max geometry-error impact = 0.05 of final score. "Dominates ranking" overstates. **Push back.**
   - **#10 (Python sort non-determinism):** verified. Stable sort preserves input order, but candidate generation order can shift between runs. Real concern. **Valid.**
2. **Web research:** none required (no external-standards claims).

### Critique walk

| # | Critique | Verdict |
|---|---|---|
| 1 | Multiplicative still distorts; switch to additive | **VALID — SPEC-AMENDMENT** |
| 2 | Lower prior floor 0.7 → 0.5 | **MISFRAMED — PUSH BACK** (reverses v0.4 #2) |
| 3 | low_confidence has no downstream enforcement | **VALID — SPEC-AMENDMENT** (contract note in § 14.3) |
| 4 | Smooth ramp only on wide_few_bedrooms branch | **VALID — SPEC-AMENDMENT** (generalize) |
| 5 | score_breakdown lacks weight/contribution | **VALID — SPEC-AMENDMENT** (structured entry) |
| 6 | Distribution shape uncontrolled | **MISFRAMED — PUSH BACK** (sum+max already bracket shape) |
| 7 | approx_length leaks into scoring via corridor_overhead | **MISFRAMED — PUSH BACK** (max impact = 0.05) |
| 8 | No guard for "1 bedroom + huge plot" pathology | **VALID-MARGINAL — SPEC-AMENDMENT** (soft penalty in scorer) |
| 9 | No calibration loop (logging, override tracking) | **MISFRAMED — PUSH BACK** (out-of-scope; depends on B-080/B-081 infra) |
| 10 | No deterministic tie ordering | **VALID — SPEC-AMENDMENT** (secondary sort on enum value) |
| 11 | Three-layer interaction; need explain() utility | **MISFRAMED — PUSH BACK** (#5 amendment + provenance already provide trace) |
| 12 | No global consistency check (topology ↔ corridor ↔ zone_bands) | **VALID — SPEC-AMENDMENT** (validator after assembly) |

**Tally:** 5 SPEC-AMENDMENTS (#1, #4, #5, #10, #12) · 2 SPEC-AMENDMENT-MARGINAL (#3, #8) · **5 PUSH-BACKS** (#2, #6, #7, #9, #11) · 0 NEW BACKLOG · 0 DUPLICATES.

---

## § 14 — v0.5 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Additive prior blend (#1)

**v0.4 § 14.1 amended.** Replace dampened multiplicative with additive blend:

```python
# v0.4 (replaced):  final = base × (0.5 + 0.5 × prior)
# v0.5 (#1):        final = 0.85 × base + 0.15 × prior
#
# Why additive: with v0.4 multiplicative, max prior swing on a high base
# (0.9) is 0.9 × 0.5 × 0.3 = 0.135 — still able to flip rank against
# small-but-real base differences. Additive caps prior swing at
# 0.15 × 0.3 = 0.045 INDEPENDENT of base magnitude, preserving base-score
# rank dominance in the 0.05-0.15 base-difference band where most real
# decisions land.
#
# Verified numerically (S29 critique round 3):
#   case A=0.90/p=0.7, B=0.85/p=1.0:
#     v0.4 mult: A=0.7650, B=0.8500 → B wins by 0.085
#     v0.5 add:  A=0.8700, B=0.8725 → B wins by 0.0025 (essentially a tie)

_BASE_BLEND_WEIGHT  = 0.85   # base score weight in final
_PRIOR_BLEND_WEIGHT = 0.15   # prior weight in final  (sum = 1.0)

def apply_prior(base_score: float, prior: float) -> float:
    return _BASE_BLEND_WEIGHT * base_score + _PRIOR_BLEND_WEIGHT * prior
```

**Note on rank dominance:** with weights {0.85, 0.15} a candidate with strictly higher base score than a peer can still lose if the peer's prior is meaningfully better — but only when base-score difference is below `0.15 × max_prior_gap / 0.85 ≈ 0.053`. Below that band the priors guide; above it, base scores dominate. This is the intended balance.

### § 14.2 — Generalize smooth ramps to all decision-table thresholds (#4)

**v0.4 § 14.2 amended.** v0.4 only smoothed the wide_few_bedrooms branch's depth-ratio threshold. v0.5 generalizes the smoothing pattern to all four decision-table thresholds: width-wide (7.92m), width-narrow (6.71m), large-width (12.19m), large-depth (18.29m).

```python
# Smooth ramp utility — used at each decision-table threshold.
# Returns 1.0 when value >= high, 0.0 when value <= low, linear between.
def _smooth_ramp(value: float, low: float, high: float) -> float:
    if high <= low:                              # defensive (high should always > low)
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def assign_priors(plot: Plot, room_brief: FloorRoomBrief) -> tuple[TopologyPriors, str]:
    """v0.5 (#4): all four threshold checks use smooth ramps; no hard cutoffs.

    Each branch computes a 'membership factor' in [0, 1] for the rule it
    represents, then interpolates priors between the rule's preferred
    triplet and the default triplet (1.0, 1.0, 0.7, 0.7).

    Ramp widths:
      - wide threshold:    +/- 0.5 m  around 7.9248 m   (low=7.42, high=8.42)
      - narrow threshold:  +/- 0.5 m  around 6.7056 m   (low=6.21, high=7.21)
      - large width:       +/- 1.0 m  around 12.1920 m  (low=11.19, high=13.19)
      - large depth:       +/- 1.0 m  around 18.2880 m  (low=17.29, high=19.29)
      - shallow ratio (carried from v0.4 #8): low=0.5, high=0.8
    """
    # Membership factors
    wide_f       = _smooth_ramp(plot.width_m, 7.42, 8.42)
    narrow_f     = 1.0 - _smooth_ramp(plot.width_m, 6.21, 7.21)
    large_w_f    = _smooth_ramp(plot.width_m, 11.19, 13.19)
    large_d_f    = _smooth_ramp(plot.depth_m, 17.29, 19.29)
    shallow_f    = _smooth_ramp(plot.depth_m / max(plot.width_m, 1e-6), 0.5, 0.8)

    # Branch dispatch: highest-priority membership wins, but each branch
    # interpolates between its preferred priors and the default priors via
    # its own factor. This eliminates discontinuities at every threshold.
    is_corner = plot.corner_plot
    few_beds  = room_brief.bedroom_count <= 2
    many_beds = room_brief.bedroom_count >= 2

    # Default priors (used when no rule's membership is 1.0)
    default = TopologyPriors(strip=1.0, central_spine=1.0, l_shape=0.7, courtyard=0.7)

    if is_corner:
        # Corner is binary in the input contract (bool). No ramp; just dispatch.
        preferred = TopologyPriors(strip=0.85, central_spine=0.7, l_shape=1.0, courtyard=0.7)
        return preferred, "corner"

    if wide_f > 0 and few_beds:
        preferred = TopologyPriors(strip=1.0, central_spine=0.85, l_shape=0.7, courtyard=0.7)
        # Apply shallow-plot factor (carried from v0.4 #8)
        strip_p   = preferred.strip - (1.0 - shallow_f) * (preferred.strip - 0.7)
        central_p = preferred.central_spine + (1.0 - shallow_f) * (1.0 - preferred.central_spine)
        # Apply wide-threshold factor: blend between preferred and default
        return _interpolate_priors(default, preferred._replace_strip_central(strip_p, central_p), wide_f), \
               "wide_few_bedrooms" if wide_f >= 1.0 else "wide_transition"

    if narrow_f > 0 and many_beds:
        preferred = TopologyPriors(strip=0.7, central_spine=1.0, l_shape=0.7, courtyard=0.7)
        return _interpolate_priors(default, preferred, narrow_f), \
               "narrow_many_bedrooms" if narrow_f >= 1.0 else "narrow_transition"

    if large_w_f > 0 and large_d_f > 0:
        preferred = TopologyPriors(strip=0.85, central_spine=0.7, l_shape=0.7, courtyard=1.0)
        f = min(large_w_f, large_d_f)            # both must hold to be "large"
        return _interpolate_priors(default, preferred, f), \
               "large" if f >= 1.0 else "large_transition"

    return default, "default_strip_or_central"


def _interpolate_priors(a: TopologyPriors, b: TopologyPriors, f: float) -> TopologyPriors:
    """Linear interpolation: f=0 → a, f=1 → b."""
    return TopologyPriors(
        strip         = a.strip         + f * (b.strip - a.strip),
        central_spine = a.central_spine + f * (b.central_spine - a.central_spine),
        l_shape       = a.l_shape       + f * (b.l_shape - a.l_shape),
        courtyard     = a.courtyard     + f * (b.courtyard - a.courtyard),
    )
```

**Effect:** at width = 7.41m vs 7.42m, STRIP prior changes by ~0% (smooth ramp begins at 7.42). At width = 7.92m (the v0.4 hard threshold), wide_f = 0.5 — STRIP prior is interpolated halfway between default and preferred. At 8.42m, wide_f = 1.0 — full preferred priors. Smooth across the full ±0.5m band.

The corner branch remains binary because `plot.corner_plot` is a `bool` from the input contract — no continuous variable to interpolate. (When B-076 lands and `corner_orientation` becomes available, the corner branch will gain a directional signal.)

### § 14.3 — Structured `low_confidence` + downstream contract note (#3, #6 partial)

**v0.4 § 14.3 amended.** The `low_confidence: bool` field stays as defined in v0.4. Adding a **downstream consumer contract** docstring on the field:

```python
@dataclass(frozen=True)
class TopologyCandidate:
    ...
    low_confidence: bool  # v0.4 (#6); v0.5 adds downstream contract below
    ...

# === DOWNSTREAM CONSUMER CONTRACT (v0.5 # 3) ===
#
# When low_confidence == True, downstream components SHOULD adapt their
# behaviour to compensate. The expected behaviours below are advisory at
# C5 LOCK time and become BINDING when the corresponding component spec
# is drafted:
#
#   C6 (Orientation Priority Engine):
#     SHOULD expand orientation candidate exploration (consider more
#     compass-axis rotations) rather than committing to a single best
#     orientation.
#
#   C8 (Corridor Designer):
#     SHOULD prefer flexible corridor layouts (tolerate wider variance
#     in corridor width / position) over tight-fit optimization.
#
#   C9 (Placement Engine):
#     SHOULD relax soft placement constraints (e.g., room-size minimums
#     can flex by +/- 10%) to accommodate the underlying topology
#     uncertainty.
#
#   User-facing review report:
#     MUST surface a "low-confidence topology" warning to the user with
#     the candidate's justification field as explanation.
#
# C5 itself does NOT enforce these — they are downstream contract
# expectations that future component specs will pick up.
```

This addresses the "purely informational" framing of #3 while respecting that C5 cannot dictate downstream component behavior unilaterally. The contract is documented at the source so when C6/C8/C9 specs are drafted, the downstream behavior is already specified.

### § 14.4 — Structured `score_breakdown` with weight + contribution (#5)

**v0.2 § 3 / v0.4 § 14.3 amended.** Promote `score_breakdown` from `Mapping[str, float]` (raw scores only) to `Mapping[str, ScoreBreakdownEntry]` (raw, weight, contribution per criterion):

```python
@dataclass(frozen=True)
class ScoreBreakdownEntry:
    """Per-criterion score detail, exposed for debugging + tuning."""
    raw: float           # criterion score in [0, 1]
    weight: float        # effective weight after context multipliers (sum=1)
    contribution: float  # = raw × weight (this criterion's share of final)


@dataclass(frozen=True)
class TopologyCandidate:
    kind: TopologyKind
    score: float
    score_breakdown: Mapping[str, ScoreBreakdownEntry]    # v0.5 #5: structured
    zone_bands: Mapping[ZoneBand, PlotOrientation]
    corridor_sketch: CorridorSketch
    low_confidence: bool
    justification: str
    provenance: TopologyProvenance
```

**Invariant:** `sum(entry.contribution for entry in score_breakdown.values())` equals the base score (before prior blend) within float epsilon. New test: `test_score_breakdown_contributions_sum_to_base_score`.

**Backwards-compat note:** consumers needing only raw scores can read `entry.raw`; the structured form is a strict superset of v0.4. No callers exist yet (C6+ not built), so no migration cost.

### § 14.5 — Soft bedroom×topology penalty (#8)

**v0.2 § 4.2 amended (scorers).** Add a multiplicative penalty inside the bedroom_fit scorer for COURTYARD when `bedroom_count < 3`:

```python
def score_bedroom_fit(topology: TopologyKind, room_brief: FloorRoomBrief) -> float:
    """v0.5 (#8): COURTYARD requires functional justification (≥3 bedrooms)
    independent of plot size. A 1-bedroom T3 plot proposing a courtyard is
    functionally absurd — the courtyard becomes vacant, defeating its purpose.

    Soft penalty: bedroom_count < 3 → 0.5× the otherwise-computed score.
    Not a hard exclusion; if every other factor strongly favours COURTYARD,
    it can still be returned as a candidate (with low_confidence likely True).
    """
    base = _topology_base_bedroom_fit(topology, room_brief.bedroom_count)
    if topology == TopologyKind.COURTYARD and room_brief.bedroom_count < 3:
        return base * 0.5
    return base
```

**Test addition:** `test_courtyard_penalized_for_few_bedrooms_regardless_of_plot_size`.

### § 14.6 — Deterministic tie ordering (#10)

**v0.3 § 14.4 amended.** Add a secondary sort key when scores tie:

```python
# v0.4 sort:    scored.sort(key=lambda c: c.score, reverse=True)
# v0.5 sort:    scored.sort(
#                   key=lambda c: (-c.score, c.kind.value),
#                   reverse=False,
#               )
#
# Why kind.value secondary key:
#   - kind.value alphabetical order: central_spine < courtyard < l_shape < strip
#   - Mechanical, testable, no opinion-based priority
#   - Insertion-order independence (Python sort is stable but the input
#     order is determined by candidate generation; this guarantees the
#     same output regardless of generation-order quirks)

scored.sort(key=lambda c: (-c.score, c.kind.value))
```

**Test addition:** `test_ties_break_alphabetical_by_kind_value` — fabricate two candidates with identical scores; assert order is `(central_spine, courtyard)` regardless of the order they were created in.

### § 14.7 — Global consistency validator (#12)

**v0.2 § 5 amended.** New private function called at the end of candidate assembly, before returning the tuple:

```python
def _validate_candidate_consistency(c: TopologyCandidate) -> None:
    """v0.5 (#12): assert internal-consistency invariants between topology
    kind, corridor sketch, and zone-band assignment.

    Catches bugs introduced by future refactors where one of these three
    is updated without the others. Cheap defensive check; runs once per
    candidate at the end of select_topology().
    """
    expected_position = {
        TopologyKind.STRIP:         (CorridorPosition.NONE, CorridorPosition.CENTRAL),
        TopologyKind.CENTRAL_SPINE: (CorridorPosition.CENTRAL,),
        TopologyKind.L_SHAPE:       (CorridorPosition.L_BENT,),
        TopologyKind.COURTYARD:     (CorridorPosition.PERIMETER,),
    }
    if c.corridor_sketch.position not in expected_position[c.kind]:
        raise RuntimeError(
            f"candidate consistency violation: {c.kind.value} topology has "
            f"corridor position {c.corridor_sketch.position.value}, expected "
            f"one of {[p.value for p in expected_position[c.kind]]}"
        )

    expected_connectivity = {
        TopologyKind.STRIP:         ConnectivityType.LINEAR,
        TopologyKind.CENTRAL_SPINE: ConnectivityType.LINEAR,
        TopologyKind.L_SHAPE:       ConnectivityType.BRANCHED,
        TopologyKind.COURTYARD:     ConnectivityType.LOOP,
    }
    if c.corridor_sketch.connectivity_type != expected_connectivity[c.kind]:
        raise RuntimeError(
            f"candidate consistency violation: {c.kind.value} topology has "
            f"connectivity {c.corridor_sketch.connectivity_type.value}, expected "
            f"{expected_connectivity[c.kind].value}"
        )

    if not c.zone_bands:
        raise RuntimeError(f"{c.kind.value} candidate has empty zone_bands")
```

Integrates into `select_topology()`'s tail:

```python
candidates = tuple(_to_candidate(s, low_confidence=...) for s in scored[:n])
for c in candidates:
    _validate_candidate_consistency(c)         # v0.5 #12
return candidates
```

**Test additions:** `test_consistency_validator_passes_for_normal_candidates`, `test_consistency_validator_catches_topology_corridor_mismatch`.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — #2 (lower prior floor 0.7 → 0.5)

**Critique claim:** "Minimum prior = 0.7 means even structurally poor candidates retain 70% influence."

**Pushback:** the 0.7 floor was deliberately chosen in v0.4 #2 as the **upper boundary of a previous range** ({1.0, 0.7, 0.4}). v0.4 specifically TIGHTENED the spread to {1.0, 0.85, 0.7} to reduce prior dominance, in coordinated combination with v0.4 #1's dampening. The proposed 0.5 floor would *widen* the spread again, partially undoing v0.4 #2 — and combined with v0.5 #1's additive blend, the prior swing would be `0.15 × (1.0 - 0.5) = 0.075`, vs the current `0.15 × (1.0 - 0.7) = 0.045`. That's a 67% increase in prior influence — pulling against the goals of v0.4 #1 and v0.5 #1. Push back; floor stays at 0.7.

### Pushback B — #6 (distribution shape uncontrolled)

**Critique claim:** "sum=1, max≤0.35, but distribution shape not controlled."

**Pushback:** the existing two invariants together implicitly bracket distribution shape. With `sum = 1.0` and `max ≤ 0.35` over 7 criteria, the worst-case skew is one weight at 0.35 and the other 6 averaging `(1.0 - 0.35) / 6 ≈ 0.108` — already a fairly flat distribution. Adding entropy or `max - min` bounds is incremental hardening with no real failure mode it prevents. Push back.

### Pushback C — #7 (approx_length leaks into scoring)

**Critique claim:** "Inaccurate geometry → wrong scoring today."

**Pushback:** corridor_overhead has weight 0.05 — the lowest of 7 criteria. Even if `approx_length` were wildly wrong (say, off by 50%), the maximum impact on a candidate's final score is `0.05 × 0.5 = 0.025`. The other 95% of scoring comes from criteria using actual plot dimensions and brief data. The "wrong scoring today" framing overstates the actual influence by ~20×. B-093 will refine when B-092 lands. Push back.

### Pushback D — #9 (no calibration loop)

**Critique claim:** Add log decisions, track overrides, periodic adjustment.

**Pushback:** the proposed solution requires observability/analytics infrastructure (logging pipeline, override-tracking storage, periodic-job runner). None of that exists — single-developer project, no CI yet (per B-080/B-081 deferral notes). C5 cannot unilaterally build this infra. When CI/observability lands (the trigger for both B-080 and B-081), calibration becomes natural to add then; until then, this critique describes a feature whose dependency stack hasn't materialized. **No new backlog needed** because the work is implicit in the existing CI-infra triggers. Push back.

### Pushback E — #11 (need explain() utility)

**Critique claim:** Three-layer interaction (priors, weights, scoring) hard to reason about; need explain() debug utility.

**Pushback:** v0.5 #5's structured `score_breakdown` provides `(raw, weight, contribution)` per criterion. `provenance.candidate_decision_table_match` carries the branch-trace. Together these are the explain trace. Adding a separate `explain()` utility would be a presentation-layer wrapper — not a C5 design concern. Standalone debug formatters are a downstream/tooling responsibility. Push back.

---

## § 16 — Backlog roll-up (Rule 9)

### No new backlog items in v0.5

All amendments addressable in-spec; no items emerged that aren't covered by existing C5 backlog (B-085..B-093) or the deferred-CI-infra triggers (B-080, B-081).

### Pre-existing backlog (carried unchanged)

- **C5:** B-085, B-086, B-087, B-088, B-089, B-090, B-091, B-092, B-093.
- **C4:** B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, B-080, B-081, B-082, B-083, B-084.

---

## § 17 — What v0.5 LOCKS

1. **5 SPEC-AMENDMENTS** in code (§§ 14.1, 14.2, 14.4, 14.6, 14.7).
2. **2 marginal SPEC-AMENDMENTS** (§§ 14.3, 14.5).
3. **5 pushbacks** documented and held with explicit math/grep/scope verification (#2, #6, #7, #9, #11).
4. **0 new backlog items.** No duplicates.
5. Estimated delta: **~70 LOC source change + ~5 new tests** (mostly in `decision_table.py`, `select.py`, `scorers.py`, `schema.py`).
6. **Architecture identical to v0.4.** All changes are field/structure additions, mathematical-form changes, or defensive validators; no contract-breaking.

---

## § 18 — v0.5 verification at LOCK time (estimated)

- Tier 1: ~5 new tests bringing C5 total to ~46.
- Tier 2: 0 new.
- Production code: ~70 LOC across `decision_table.py`, `select.py`, `scorers.py`, `schema.py`.
- Existing v0.4-anticipated tests adjusted for: additive blend; smooth ramps on all thresholds; structured score_breakdown; deterministic tie order; consistency validator.

---

## § 19 — Cumulative C5 lineage

| Round | SPEC-AMENDMENTS | New backlog | Push-backs |
|---:|---:|---:|---:|
| v0.1 (DRAFT) | — | — | — |
| v0.2 (PROPOSED) | initial design | 7 (B-085..091) | — |
| v0.3 | 5 + 1 invariant + 1 Q7 reversal | 1 (B-092) | 2 |
| v0.4 | 4 + 1 invariant | 1 (B-093) | 5 |
| **v0.5** | **5 + 2 marginal** | **0** | **5** |
| **Total to v0.5** | **14 + 2 marginal** | **9** | **12** |

Pushback rate stable across v0.4 and v0.5 (5 of 12 each round). Backlog rate dropping (1 → 1 → 0). Architecture is converging on stability — most new critique items resolve to either valid amendments that the architecture absorbs cleanly, or pushbacks grounded in code-grep/math falsification.

---

## § 20 — Status

**v0.5 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per Rule 8, adjudication-window critiques arriving between PROPOSED and LOCK remain PATCH-eligible — additional concerns produce v0.6 PROPOSED, not backlog entries, until Ramalingam locks.

Per Rule 7 amended (S29): all 12 critique items verified via 6 independent checks (3 math + 3 code-grep) before this walk; no external-standards claims invoked, so web-search not required this round (per Rule 7's "if no factual claim, say so" clause).

Per Obligation 1: still no C5 code. Spec must LOCK before code build.
