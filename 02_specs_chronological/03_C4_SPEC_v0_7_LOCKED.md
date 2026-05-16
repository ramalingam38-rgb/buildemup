# BuildemUp Component 4 (Plot Analysis) — SPEC v0.7 LOCKED

**Status:** **v0.7 LOCKED** by Ramalingam mid-S29 after walk of 6-item code-review critique. This document is the **patch delta** over v0.6 LOCKED — read v0.5 + v0.6 first, then this delta.

**Generated:** S29 mid-session, after C4 v0.6 SHIP and code-review critique round 2.
**Source critique:** 6-item document supplied by Ramalingam.

---

## § 13 — Rule-7 walk (v0.6 → v0.7)

### Verification gates run BEFORE this walk (Rule 7 prerequisites)

1. **Code-grep on existing codebase** (4 grepps across kb/, components/c04/, domain/):
   - `KB_VERSION` formats: 6+ co-existing styles in the codebase (`"v1.0"`, `"Wind_IS875_2026_v1"`, `"SoilSBC_IS1904_v1_2026"`, `"MultiCity_2026_Q2_v2"`, etc.). Real inconsistency confirmed for item #3.
   - City validation duplication: 3 sites (`climate_zone.py:26`, `climate_zone.py:39`, `plot_analysis.py:178`). Confirmed for item #4.
   - `Plot.__post_init__` width invariant: enforced at `3.0 ≤ width_m ≤ 60.0` line 103. Confirmed for item #5.
   - City normalization sites: 2 (`Plot.__post_init__:121`, `plot_analysis.py:177`). Confirmed for item #1.
2. **Web-research:** none required (no factual claims about external standards in this critique).

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| 1 | Hidden coupling between city normalization and KB keys | **PARTIALLY VALID — SPEC-AMENDMENT** + push back on framing |
| 2 | `WindContext.basic_speed_ms` lazy property = hidden dep | **VALID — SPEC-AMENDMENT** |
| 3 | `source_versions` lacks format validation | **VALID-BUT-BACKLOG (B-079)** |
| 4 | Duplicate city validation across 3 sites | **VALID — SPEC-AMENDMENT** |
| 5 | Aspect ratio relies on upstream `width_m > 0` | **MISFRAMED — PUSH BACK** + DOCUMENTED |
| 6 | Perf cap (1ms) too tight for CI variation | **PARTIALLY VALID — SPEC-AMENDMENT** |

**Tally:** 4 SPEC-AMENDMENTS (#1, #2, #4, #6). 1 BACKLOG-ONLY (#3). 1 DOCUMENTED-ONLY with PUSH-BACK (#5).

---

## § 14 — v0.7 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — Centralize `normalize_city` + `validate_city` (items 1 + 4)

**Spec § 5 module layout amended:** add two helpers to existing `components/c04/climate_zone.py` (the natural home — already does city-keyed lookups):

```python
# components/c04/climate_zone.py

def normalize_city(city: str) -> str:
    """Canonical city normalization. Single source of truth.

    Returns a stripped, lowercase city name. Used at all C4 read sites
    (defense in depth — Plot.__post_init__ already does this for the
    Plot.city field; this helper makes the contract explicit and
    available to call sites that may receive non-Plot inputs).
    """
    if not isinstance(city, str):
        raise TypeError(f"city must be str; got {type(city).__name__}")
    return city.strip().lower()


def validate_city(city: str) -> str:
    """Normalize city and verify membership in CITY_GEOGRAPHY.

    Returns the normalized city name. Raises ValueError if the
    normalized name is not a supported city.

    Single source of truth for the city-validation pattern that v0.6
    repeated across 3 sites (plot_analysis.py:178, climate_zone:26,
    climate_zone:39).
    """
    normalized = normalize_city(city)
    if normalized not in CITY_GEOGRAPHY:
        raise ValueError(
            f"city '{normalized}' missing from CITY_GEOGRAPHY; check "
            f"kb/city_geography.py against domain.plot.SUPPORTED_CITIES"
        )
    return normalized
```

**Refactor sites** (3 places, all internal — no contract change):
- `plot_analysis.py:177-181` (~5 LOC) → `city = validate_city(plot.city)`
- `climate_zone.py:lookup_climate_zone` body (~5 LOC) → use `validate_city(city)`
- `climate_zone.py:lookup_latitude` body (~5 LOC) → use `validate_city(city)`

**Pushback retained on framing of item #1:** the v0.6 design WAS already fail-fast (`SUPPORTED_CITIES` is normalized → set-difference catches case mismatches). The refactor is for DRY/maintainability, not correctness.

### § 14.2 — Eager `WindContext.basic_speed_ms` (item 2)

**Spec § 3 `WindContext` dataclass amended** (lazy property → stored field):

```python
@dataclass(frozen=True)
class WindContext:
    """City wind characterisation.

    v0.7 (walk #2): `basic_speed_ms` is now a STORED field, not a lazy
    property. The IS-875 wind speed is resolved once at PREVAILING_WIND
    construction (module load) and frozen on the dataclass, eliminating
    the runtime hidden import. Single-source-of-truth for wind speeds
    is preserved (kb.wind_load is still the canonical KB; it's just
    consulted at module load instead of at every property access).

    `city` field is retained as documentary metadata.
    """
    primary_direction: PlotOrientation
    monsoon_direction: PlotOrientation
    city: str
    basic_speed_ms: float                        # NEW v0.7: stored, not property
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    # NOTE: No @property basic_speed_ms anymore. Removed in v0.7 walk #2.
```

**Spec § 4.6 `kb/wind_direction.py` amended:** import `BASIC_WIND_SPEED_MS` at module top; populate `basic_speed_ms=float(BASIC_WIND_SPEED_MS[city])` for each WindContext. Module-load coupling between `kb.wind_direction` and `kb.wind_load` is intentional and acceptable (both are mandatory KBs for v1).

**Test addition:** `test_wind_context_basic_speed_ms_is_stored_field_not_property` — uses `inspect.getattr_static` to confirm it's no longer a property descriptor.

### § 14.3 — Item 5 docstring note (DOCUMENTED, no code change)

**Spec § 4.1 amended** (docstring clarification, no behavior change):

```python
# In plot_analysis.derive() docstring:
"""
...
UPSTREAM INVARIANTS C4 RELIES ON (per domain/plot.py Plot.__post_init__):
  - 3.0 ≤ plot.width_m ≤ 60.0      (width-zero mechanically impossible)
  - 3.0 ≤ plot.depth_m ≤ 60.0
  - 1.5 ≤ plot.road_width_m ≤ 30.0
  - plot.city normalized + ∈ SUPPORTED_CITIES
These are NOT re-validated in C4 (single source of truth for plot
invariants is the Plot constructor). dataclasses.replace() re-runs
__post_init__, so post-construction modification is also covered.
"""
```

**Pushback retained:** code-grep confirmed Plot.__post_init__:103 enforces `3.0 ≤ width_m ≤ 60.0`. `dataclasses.replace()` DOES re-run `__post_init__` (Python stdlib documented behavior). The only "bypass" path is `object.__new__ + object.__setattr__`, which defeats any layer of validation equally — so re-validating in C4 doesn't help.

### § 14.4 — Perf cap relaxation (item 6)

**Spec § 7 perf test amended:**

| | v0.5 | v0.6 | v0.7 |
|---|---:|---:|---:|
| Cap | 10 ms | 1 ms | **3 ms** |
| Samples | 100 | 1000 | 1000 |
| Headroom over measured p95 (0.015 ms) | 666× | 66× | **200×** |

3 ms is loose enough to absorb CI runner variability (typical 5-15× slower than dev hosts) while still catching meaningful regressions (a 100× slowdown still trips the test). Configurable-per-environment is over-engineering for current scale (single-developer project, no CI infrastructure yet).

Test rename: `test_derive_completes_under_1ms_for_typical_plot` → `test_derive_completes_under_3ms_for_typical_plot`.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — item #1 framing ("inconsistent instead of fail-fast")

**Critique claim:** "If any KB introduces inconsistent casing/format, behavior becomes inconsistent instead of fail-fast."

**Pushback:** v0.6 design IS already fail-fast. `domain.plot.SUPPORTED_CITIES` is normalized (lowercase strings). `verify_kb_consistency()` does `required = set(SUPPORTED_CITIES); missing = required - set(kb_keys)`. Any cased KB key (e.g., `"Chennai"` instead of `"chennai"`) lands in `missing` and raises `RuntimeError` at module-import time. Set-difference comparison is case-sensitive in Python. So the "becomes inconsistent" framing is incorrect. The DRY refactor is still worth doing for maintainability — that's why the verdict is SPEC-AMENDMENT, not full PUSH-BACK.

### Pushback B — item #5 (aspect ratio fragility)

**Critique claim:** "If upstream validation changes or is bypassed, division-by-zero risk appears."

**Pushback:** Code-grep at `domain/plot.py:103` confirms `Plot.__post_init__` enforces `3.0 ≤ width_m ≤ 60.0`. Two paths:

1. **"Validation changes":** that's a coordinated upstream change. C4's defensive width-zero check would still pass under any plausible bound relaxation (`[1.0, 60.0]`, `[0.5, 60.0]`, etc.) — it would only catch the case where bounds are relaxed all the way to allow zero, which is a deliberate upstream decision C4 should respect.
2. **"Bypassed":** `dataclasses.replace()` re-runs `__post_init__` (Python stdlib documented). Only `object.__new__` + `object.__setattr__` truly bypasses, at which point any defensive check anywhere is irrelevant.

Adding `width_m > 0` in C4 creates two-place maintenance for one invariant with zero scenario where C4's check fires before Plot's. Push back stands. Documentation note added per § 14.3.

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog item

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-079 | System-wide KB_VERSION format policy. Codebase has 6+ co-existing format styles. Choose canonical format (semver vs name-stamped, e.g., `"v1.0"` vs `"Wind_IS875_2026_v1"`) and align all 14+ KBs. Optional: include content-hash for stronger provenance. C4's 4 KBs are part of this sweep, not a unilateral fix. | v0.7 walk #3 | observability/audit requirement surfaces, OR a downstream consumer needs format guarantees | OUT (v0.7) | ~30 LOC + cross-component sweep |

### Pre-existing backlog (carried unchanged)

B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, plus B-001..B-065 (pre-S28).

---

## § 17 — What v0.7 LOCKS

If LOCKED:

1. Four SPEC-AMENDMENTS land in code (sections § 14.1, § 14.2, § 14.4 — § 14.3 is doc-only).
2. One new backlog item filed (B-079).
3. Two pushbacks documented and held (items #1 framing, #5).
4. Estimated code delta: ~40 LOC source change + ~10 LOC test additions.
5. **Architecture: identical to v0.6.** No new modules. Function additions to existing `climate_zone.py`. One field addition to `WindContext` (with corresponding @property removal, net no field count change).

---

## § 18 — v0.7 verification at LOCK time (estimated)

- Tier 1: ~3-4 new tests (validate_city × 2, normalize_city × 1, basic_speed_ms-is-field × 1).
- Tier 2: 0 new.
- Production code: ~40 LOC across schema.py, climate_zone.py, wind_direction.py, plot_analysis.py.
- Existing 1402 tests re-run + ~4 new = ~1406 expected passing.

---

## § 19 — Status

**v0.7 LOCKED** by Ramalingam mid-S29.
