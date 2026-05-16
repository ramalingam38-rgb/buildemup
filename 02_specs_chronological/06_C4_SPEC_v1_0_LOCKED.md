# BuildemUp Component 4 (Plot Analysis) — SPEC v1.0 LOCKED

**Status:** **v1.0 LOCKED** by Ramalingam mid-S29.

**Graduation milestone:** C4 has now survived 5 critique rounds (v0.5 → v0.6 → v0.7 → v0.8 → v0.9 → v1.0). The codebase has converged: most new critique items now resolve to either DUPLICATE (already filed in backlog), PUSH-BACK (documented and stable), or small SPEC-AMENDMENTS that the architecture absorbs cleanly. Promoting the major version reflects this stability.

**Generated:** S29, after C4 v0.9 SHIP and code-review critique round 5 (D1-D7).

---

## § 13 — Rule-7 walk (v0.9 → v1.0)

### Verification gates run BEFORE this walk (per amended Rule 7)

1. **Web-search (mandatory per Rule 7 amendment):**
   - **IEEE 754 cross-platform float determinism** (D1): randomascii.wordpress.com Bruce Dawson "Floating-Point Determinism" confirms answer is "yes and no in practice" — compiler optimization, library implementation, and FPU state can produce different results. CPython per PEP 754 inherits whatever the underlying C library provides. Tolerance comparison is standard best practice. D1 verified valid.
2. **Code-grep:**
   - **D6** (`Plot.__post_init__` corner_plot validation): confirmed at `domain/plot.py:132-141` — already raises `ValueError("corner_plot=True requires second_road_width_m to be set.")`. Critique is asserting an absence that doesn't exist.
   - **D4** (PREVAILING_WIND direction type checks): confirmed `verify_kb_consistency()` does NOT isinstance-check `primary_direction` / `monsoon_direction`. Real gap.
   - **D5** (BEARING_CAPACITY_BY_TYPE range check): confirmed only `SOIL_PROFILES` (city defaults) is range-checked at line 149; `BEARING_CAPACITY_BY_TYPE` has no equivalent. Real gap parallel to v0.6 §14.4.

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| D1 | Float-equality test fragile across platforms | **VALID — SPEC-AMENDMENT** |
| D2 | No upper bound on aspect_ratio | **DUPLICATE — already B-075** |
| D3 | Silent reliance on Plot.__post_init__ invariants | **DUPLICATE — push-back held since v0.6 (4 rounds)** |
| D4 | PREVAILING_WIND directions not type-validated | **VALID — SPEC-AMENDMENT** |
| D5 | BEARING_CAPACITY_BY_TYPE values not range-validated | **VALID — SPEC-AMENDMENT** |
| D6 | corner_plot validation missing | **MISFRAMED — PUSH BACK** (validation exists in Plot.__post_init__:132) |
| D7 | source_versions not version-locked atomically | **MISFRAMED — PUSH BACK** (no-op today or regression in B-080 future) |

**Tally:** 3 SPEC-AMENDMENTS · 2 DUPLICATES · 2 PUSH-BACKS · 0 NEW BACKLOG.

---

## § 14 — v1.0 SPEC-AMENDMENTS

### § 14.1 — Tolerance-based area_sqft test (D1)

**Spec § 7 amended.** `test_area_sqft_display_matches_textbook_at_40x60ft_boundary` switches from exact equality to tolerance:

```python
# Was:
assert pa.area_sqft == 2400.0
# Now:
assert abs(pa.area_sqft - 2400.0) < 1e-9
```

Rationale: per Rule-7 web verification (Bruce Dawson "Floating-Point Determinism"), exact float equality is fragile across compiler optimization paths, x87 vs SSE, and library variants. 1e-9 tolerance is ~10 orders of magnitude tighter than any plausible drift while remaining platform-robust.

### § 14.2 — verify_kb_consistency: type-check wind directions (D4)

**Spec § 4.4.2 amended.** Add isinstance check for both direction fields on each PREVAILING_WIND entry:

```python
# In verify_kb_consistency() — new sanity loop:
for city, wc in PREVAILING_WIND.items():
    for field_name in ("primary_direction", "monsoon_direction"):
        value = getattr(wc, field_name)
        if not isinstance(value, PlotOrientation):
            raise RuntimeError(
                f"KB drift: kb/wind_direction PREVAILING_WIND[{city!r}].{field_name} "
                f"= {value!r} (type {type(value).__name__}); "
                f"must be PlotOrientation enum."
            )
```

Catches KB corruption that bypasses the dataclass type annotation (Python doesn't enforce annotations at runtime).

**Test addition:** `test_kb_drift_detected_for_non_plotorientation_wind_direction` — monkeypatch a string into `primary_direction`, verify RuntimeError.

### § 14.3 — verify_kb_consistency: range-check per-SoilType kPa (D5)

**Spec § 4.4.2 amended.** Parallel to the existing v0.6 §14.4 loop on `SOIL_PROFILES`:

```python
# In verify_kb_consistency() — new sanity loop:
from buildemup.kb.soil_city_defaults import BEARING_CAPACITY_BY_TYPE
for soil_type, kpa in BEARING_CAPACITY_BY_TYPE.items():
    if not (10.0 <= kpa <= 2000.0):
        raise RuntimeError(
            f"KB drift: kb/soil_city_defaults BEARING_CAPACITY_BY_TYPE"
            f"[{soil_type.value}] = {kpa} kPa out of plausible "
            f"residential range [10, 2000]."
        )
```

**Test addition:** `test_kb_drift_detected_for_out_of_range_per_soil_type_kpa` — monkeypatch an invalid kPa, verify RuntimeError.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — D6 (corner_plot validation absence)

**Critique claim:** "Code assumes second_road_width_m exists but does not validate."

**Pushback:** `Plot.__post_init__` at `domain/plot.py:132-141` enforces THREE invariants on this:

```python
if self.corner_plot:
    if self.second_road_width_m is None:
        raise ValueError("corner_plot=True requires second_road_width_m to be set.")
    if not 1.5 <= self.second_road_width_m <= 30.0:
        raise ValueError(f"second_road_width_m {…}m out of range.")
elif self.second_road_width_m is not None:
    raise ValueError("second_road_width_m given but corner_plot=False.")
```

The validation is tighter than the critique's proposed fix (which only handles the None case). Re-validating in C4 = two-place maintenance for one invariant, with no scenario where C4's check fires before Plot's. Same family as recurring D3 push-back: assuming an absence of upstream validation that exists.

### Pushback B — D7 (atomic version-locking)

**Critique claim:** Cache `_KB_VERSIONS = MappingProxyType(kb_versions())` at module load to avoid mixed KB versions in hot-reload / partial-deploy.

**Pushback:** The proposed change has opposite consequences depending on world state:

| World | Caching at module load |
|---|---|
| **Today** (static KBs) | Returns same dict every call. Micro-perf gain, no correctness change. |
| **B-080 future** (dynamic KBs) | Versions freeze even when KBs change. **Active correctness regression.** |

The "hot-reload / partial deploy" scenario the critique invokes is the literal trigger for B-080. Implementing now means undoing later. Pattern E (scope creep). Push back.

---

## § 16 — Backlog roll-up (Rule 9)

### Cumulative backlog (no new items in v1.0)

| ID | Description | Origin |
|---|---|---|
| B-066 | Polygon plots | C4 v0.1 |
| B-067 | Per-month sun-path declination | C4 critique #4 |
| B-068 | effective_open_sides (post-setback) | C4 critique #8 |
| B-069 | Composite-zone sub-classification | C4 v0.3 web research |
| B-070 | IMD wind-rose per city | C4 v0.3 SC |
| B-071 | Latitude-band city fallback | C4 v0.3 critique #3 |
| B-072 | C7 retrofit to consume PlotAnalysis.soil_estimate | C4 v0.4 Path B |
| B-074 | MEDIUM_ROCK proper kPa value | v0.6 walk #2 |
| B-075 | AspectClass enum + extreme-plot detection | v0.6 walk #4 |
| B-076 | Plot.corner_orientation input field | v0.6 walk #5 |
| B-077 | Richer multi-state soil confidence model | v0.6 walk #7 |
| B-078 | System-wide trace_id lifecycle policy | v0.6 walk #9 |
| B-079 | System-wide KB_VERSION format policy | v0.7 walk #3 |
| B-080 | Dynamic KB mutation re-validation | v0.8 walk #2 |
| B-081 | Perf-test rolling baseline / env-configurable | v0.8 walk #6 |
| B-082 | Structured kPa error fields on SoilEstimate | v0.9 walk #2 |
| B-083 | Sub-city soil zoning | v0.9 walk #3 |

Plus B-001..B-065 pre-S28.

**Net new backlog this round: zero.** This is a milestone — the critique pipeline is no longer surfacing genuinely new architectural concerns.

---

## § 17 — Cumulative S29 lineage

| Round | SPEC-AMENDMENTS | New backlog | Push-backs |
|---:|---:|---:|---:|
| v0.5 (build) | 6 (CG fixes) | — | — |
| v0.6 | 5 | 5 (B-074..078) | 2 |
| v0.7 | 4 | 1 (B-079) | 2 |
| v0.8 | 3 | 2 (B-080, 081) | 3 |
| v0.9 | 1 | 2 (B-082, 083) | 2 |
| **v1.0** | **3** | **0** | **2** |
| **Total** | **22** | **10** | **11** |

10 new backlog items · 11 push-backs documented · 22 SPEC-AMENDMENTS landed.

---

## § 18 — v1.0 verification at LOCK time

- Tests passing: target ~1417 (was 1415 at v0.9 LOCK; +2 new drift tests).
- Production code: ~15 LOC source change in `kb/city_geography.py` + ~2 LOC in `test_c4_plot_analysis.py`.
- Existing 1415 tests re-run + 2 new = 1417 expected passing.

---

## § 19 — Status

**v1.0 LOCKED** by Ramalingam mid-S29. C4 ships at major version 1.0. Architecture stable, backlog properly filed, push-backs documented. Ready for downstream consumers (C5 onward).
