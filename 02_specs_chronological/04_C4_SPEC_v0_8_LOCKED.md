# BuildemUp Component 4 (Plot Analysis) — SPEC v0.8 LOCKED

**Status:** **v0.8 LOCKED** by Ramalingam mid-S29 after walk of 10-item code-review critique round 3. Patch delta over v0.7 LOCKED — read v0.5, v0.6, v0.7 first.

**Generated:** S29 mid-session, after C4 v0.7 SHIP and code-review critique round 3.
**Source critique:** 10-item document supplied by Ramalingam.

---

## § 13 — Rule-7 walk (v0.7 → v0.8)

### Verification gates run BEFORE this walk

1. **Code-grep on existing codebase** (5 grepps):
   - `kb/wind_load.py` imports: stdlib only (`__future__`, `dataclasses`). It is a leaf KB. **No circular-import risk** with wind_direction in any direction.
   - `WindContext.city` consumers: code-grep across `components/c04/*.py` and `__init__.py` shows the field is **never read by any consumer**, only mentioned in a docstring of `climate_zone.py`. Confirmed dead metadata.
   - `_APPROXIMATED_USER_INPUT_NOTES` location: confirmed in `components/c04/soil_estimator.py:46` (logic layer), not in `kb/soil_city_defaults.py` (data layer).
   - `derive()` size: ~80 LOC including 36-line docstring + 4 LOC final return + 9 single-call sections + 8 LOC validation. Linear orchestration, no branching.
2. **Web research:** none required this round.

### Critique walk

| # | Critique summary | Verdict |
|---|---|---|
| 1 | Module-load coupling between wind_direction ↔ wind_load | **MISFRAMED — PUSH BACK** |
| 2 | `verify_kb_consistency()` static-import-only | **VALID-BUT-BACKLOG (B-080)** + DOCUMENTED |
| 3 | Provenance versions lack format integrity | **DUPLICATE — already B-079** |
| 4 | aspect_ratio relies on upstream invariant | **DUPLICATE — already DOCUMENTED in v0.7 § 14.3** |
| 5 | `normalize_city()` not enforced at KB definition boundaries | **VALID — SPEC-AMENDMENT** |
| 6 | Perf test absolute threshold (3ms) | **VALID-BUT-BACKLOG (B-081)** |
| 7 | `WindContext.city` is redundant data | **VALID — SPEC-AMENDMENT** |
| 8 | Soil approximation policy in logic layer | **VALID — SPEC-AMENDMENT** |
| 9 | No semantic cross-KB consistency tests | **MISFRAMED — PUSH BACK** |
| 10 | `derive()` is a "god function" | **MISFRAMED — PUSH BACK** |

**Tally:** 3 SPEC-AMENDMENTS (#5, #7, #8) · 2 BACKLOG (#2 → B-080, #6 → B-081) · 2 DUPLICATES (#3, #4) · 3 PUSH-BACKS (#1, #9, #10).

---

## § 14 — v0.8 SPEC-AMENDMENTS (the patch delta)

### § 14.1 — KB key normalization enforcement (item 5)

**Spec § 4.4.2 `verify_kb_consistency()` amended** to add a new step BEFORE the existing presence/range checks:

```python
def verify_kb_consistency() -> None:
    # ── NEW v0.8 § 14.1: every KB key must be already-normalized ──
    # Catches whitespace / casing errors at module load even if a
    # mismatched-but-internally-consistent format would slip past the
    # presence check (e.g., if SUPPORTED_CITIES itself ever drifts).
    from buildemup.components.c04.climate_zone import normalize_city
    for kb_name, kb_keys in (
        ("city_geography",      list(CITY_GEOGRAPHY.keys())),
        ("wind_load",           list(BASIC_WIND_SPEED_MS.keys())),
        ("soil_city_defaults",  list(SOIL_PROFILES.keys())),
        ("wind_direction",      list(PREVAILING_WIND.keys())),
    ):
        for key in kb_keys:
            if key != normalize_city(key):
                raise RuntimeError(
                    f"KB drift: kb/{kb_name} has non-normalized city key "
                    f"{key!r} (normalize_city → {normalize_city(key)!r}). "
                    f"All KB keys must be lowercase, stripped."
                )
    # ── existing presence + range checks unchanged ──
```

**Test addition:** `test_kb_drift_detected_for_non_normalized_key` — monkeypatch a KB to inject `"Chennai"` (uppercase), verify RuntimeError.

### § 14.2 — Remove `WindContext.city` field (item 7)

**Spec § 3 `WindContext` dataclass amended** (drop the redundant field):

```python
@dataclass(frozen=True)
class WindContext:
    """City wind characterisation.

    v0.8 (walk #7): `city` field removed. It was introduced in v0.5 as
    the lookup key for the `basic_speed_ms` lazy property. v0.7 made
    `basic_speed_ms` a stored field, leaving `city` as dead metadata.
    Code-grep confirmed no consumer read it. Removing eliminates the
    key/field consistency risk (PREVAILING_WIND["chennai"] could have
    had city="delhi" without anyone noticing).
    """
    primary_direction: PlotOrientation
    monsoon_direction: PlotOrientation
    basic_speed_ms: float
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    # NOTE: no `city` field. The dict key in PREVAILING_WIND IS the city.
```

**Spec § 4.6 `kb/wind_direction.py` amended:** drop `city=` kwarg from each WindContext construction.

**Test addition:** `test_wind_context_does_not_carry_city_field` — assert `"city"` not in `WindContext.__dataclass_fields__`.

### § 14.3 — Move soil approximation notes to KB layer (item 8)

**Spec § 4.7.1 `kb/soil_city_defaults.py` amended** (new export):

```python
APPROXIMATION_NOTES_BY_SOIL_TYPE: dict[SoilType, str] = {
    SoilType.MEDIUM_ROCK: (
        "medium_rock_approximated_to_soft_rock_660kpa_underestimate_b074"
    ),
}
```

**Spec § 4.7.2 `components/c04/soil_estimator.py` amended:** drop the local `_APPROXIMATED_USER_INPUT_NOTES` table; import `APPROXIMATION_NOTES_BY_SOIL_TYPE` from the KB and read from it. Behaviour preserved bit-for-bit.

**Test additions:** existing `test_soil_estimate_user_input_medium_rock_carries_b074_breadcrumb` continues to pass; add 1 test that confirms the table is now KB-sourced.

---

## § 15 — Pushbacks (where critique is wrong)

### Pushback A — item #1 (module-load coupling)

**Critique claim:** wind_direction → wind_load module-load import = "hard coupling, future circular dependency will break import-time execution."

**Pushback:** Code-grep confirmed `kb/wind_load.py` imports only stdlib (`__future__`, `dataclasses`). It is a leaf KB. A circular dependency between wind_load and wind_direction would require explicitly making wind_load import wind_direction — that is a deliberate code change, not an "accidental" failure.

This concern is the inverse of v0.6 walk #2, which flagged the *previous* design (lazy `@property` doing runtime imports) as a "hidden dependency" and demanded eager resolution. Both designs have tradeoffs; we already adjudicated. The proposed "wind_resolver" layer is functionally identical indirection — adds a file, changes nothing semantically. **Push back stands; no oscillation.**

### Pushback B — item #9 (cross-KB semantic tests)

**Critique claim:** "KBs can be internally valid but collectively inconsistent."

**Pushback:** Each KB cites an authoritative external source:
- `city_geography.py` → NBC 2016 Part 8 Section 1, §§ 2.2.21-2.2.24 + 3.2.2
- `wind_load.py` → IS 875 Part 3
- `wind_direction.py` → IMD station climatology (per-city)
- `soil_city_defaults.py` → IS 6403 / IS 1904 + IS 1893

A "Chennai is warm-humid AND has SW monsoon" coherence test reduces to either:
- Tautologically restating source data (test passes by definition), OR
- Encoding domain intuition (less rigorous than the cited sources).

The right guardrail is source-citation discipline at the KB level — already in place. Programmatic checks would either be self-confirming or would replace authoritative documents with an expert's hunch. **Push back stands.**

### Pushback C — item #10 (god-function refactor)

**Critique claim:** derive() is becoming a god function, should split into geometry/climate/soil/context pipelines.

**Pushback:** Code-grep on derive():

| Section | LOC |
|---|---:|
| Docstring | 36 |
| Validation | 8 |
| Tier + dimensions | 4 |
| Sun path (1 call) | 2 |
| Climate zone (1 call) | 2 |
| Wind (1 dict lookup) | 2 |
| Soil (1 call) | 2 |
| Road class (1 call) | 1 |
| Neighbour context (1 call) | 1 |
| Provenance + return | 22 |
| **Total** | ~80 |

Each compute step is already in its own module; derive() does ONE function call per step plus assembly. Four sub-pipelines would create files containing one function call each — premature abstraction. SRP is about cohesion, not line count: derive() has a single responsibility — compose validated input + KB lookups into a frozen PlotAnalysis. Real refactor trigger = branching logic or 200+ LOC; current state is 80 with zero branches. **Push back stands.**

---

## § 16 — Backlog roll-up (Rule 9)

### New backlog items

| ID | Description | Origin | Trigger | Scope verdict | Effort |
|---|---|---|---|---|---:|
| B-080 | Dynamic KB mutation: re-validate via verify_kb_consistency() (or content-hash pinning) when KBs are mutated outside module-load. Also document "static KBs only" architectural assumption explicitly. | v0.8 walk #2 | hot reload introduced, OR admin/tooling that mutates KB dicts at runtime, OR test fixtures that monkey-patch KBs with mismatched values | OUT (v0.8) | ~15 LOC + spec note |
| B-081 | Performance test: rolling baseline (last-N-runs median ± stddev) OR env-configurable threshold (when CI infra makes the latter principled rather than an escape hatch). | v0.8 walk #6 | CI infrastructure live (GitHub Actions, dedicated runner, or scheduled benchmark job) | OUT (v0.8) | ~30 LOC + CI integration |

### Pre-existing backlog (unchanged)

B-066, B-067, B-068, B-069, B-070, B-071, B-072, B-074, B-075, B-076, B-077, B-078, B-079, plus B-001..B-065.

---

## § 17 — What v0.8 LOCKS

1. Three SPEC-AMENDMENTS in code (sections § 14.1, § 14.2, § 14.3).
2. Two new backlog items filed (B-080, B-081).
3. Three pushbacks documented and held (#1, #9, #10).
4. Two duplicates noted and not re-filed (#3 → B-079, #4 → DOCUMENTED in v0.7).
5. Estimated delta: ~30 LOC source + ~25 LOC tests.
6. Architecture identical to v0.7. One field removal (`WindContext.city`) — no consumer reads it (code-grep confirmed).

---

## § 18 — v0.8 verification at LOCK time (estimated)

- Tier 1: ~3 new tests (KB-key normalization drift, WindContext field removal, KB-sourced approximation table).
- Tier 2: 0 new.
- Production code: ~30 LOC across schema.py, kb/wind_direction.py, kb/soil_city_defaults.py, components/c04/soil_estimator.py, kb/city_geography.py.
- Existing 1408 tests re-run + ~3 new = ~1411 expected passing.

---

## § 19 — Status

**v0.8 LOCKED** by Ramalingam mid-S29.
