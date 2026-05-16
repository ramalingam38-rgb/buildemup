# BuildemUp Master Doc — Δ v3.6 → v3.7

**Session**: S32 (4 May 2026)
**Authority**: This delta records S32 work. v3.7 is canonical going forward.

---

## Δ.0 — Pipeline state at S32 close

**Components SHIPPED**: 8 of 19 (was: 7 of 19 at S31 close).

| # | Track 3 ID | Status | LOCKED spec | Tests |
|---|---|---|---|---|
| 1 | C1 (Brief Capture) | SHIPPED | v0.x | (cumulative 1539 baseline includes) |
| 2 | C2 (Component KB Sketcher) | SHIPPED | v0.x | (in baseline) |
| 3 | C3a (Extreme-Case Gate) | SHIPPED | v0.2.1 | (in baseline) |
| 4 | C4 (Plot Analysis) | SHIPPED | v1.1 | (in baseline) |
| 5 | C5 (Topology Selector) | SHIPPED | v0.9 | (in baseline) |
| 6 | C6 (Orientation Refinement) | SHIPPED | v0.7 | **MISSING from upstream — see Δ.1** |
| 7 | C7 (Structural Grid) | SHIPPED | v0.x | (in baseline) |
| 8 | **C8 (Corridor Designer)** | **NEW SHIPPED** | **v0.5** | **+174 tests** |

**Cumulative test count at S32 close**: 1713 passed / 1 skipped (was: 1539 / 1 baseline).
- C8 added: 174 tests across 11 files.
- Adjusted SHIP target was ~1694 (per Doubt 3 resolution); exceeded by 19.

---

## Δ.1 — V8 bundle defect: C6 production code missing from upstream

**Discovered at S32 open** via empirical inspection of the v8 bundle's `06_upstream_codebase/`.

C6 v0.7 SHIPPED at S31 close, but production code never made it into the upstream snapshot. Only artifact present: a non-runnable consolidated review file at `03_code_chronological/S31_C6_v0_7_review/buildemup_c06_consolidated_v0_7.py`.

**The S31 INTEGRITY CHECK passed regardless** — claimed "tests baseline 1725/1 unchanged" without executing pytest against the bundle's own tree. Empirical re-test at S32 open: 1539 passed / 1 skipped (NOT 1725).

**S32 recovery action**: deployed C6 from review file at session open by splitting at the 6 FILE markers (no content modification). All C6 imports verified. Baseline preserved.

**Filed**:
- **B-127**: Reconstruct C6 production tests from SPEC v0.7 § 7 (186 tests claimed in review file header; not in any bundle artifact).
- **B-128**: Bundle integrity check should verify SHIPPED components have production code in upstream — adopted at S32 close (see Δ.5).

---

## Δ.2 — C8 v0.5 SHIPPED

**Modules built** (11 of 11 production files):
1. `__init__.py` — public re-exports.
2. `schema.py` — dataclasses, enums, constants per § 3. Includes the schema-deviation per Δ.4.
3. `errors.py` — 3 exception types per § 6 / § 14.17 / § 14.23.
4. `spatial_model.py` — directional-strip ZoneBandEnvelope derivation per § 4.0 + corner overlap resolution per § 14.10.
5. `grid_alignment.py` — `derive_grid_lines()` per § 4.2 / § 14.9 + edge-snap with envelope-symmetry secondary per § 4.2.1.
6. `width_selection.py` — scored asymmetric selection per § 4.3 / § 14.19 + taper-zone resolution per § 4.3.1.
7. `topology_dispatch.py` — STRIP / CENTRAL_SPINE / L_SHAPE / COURTYARD per § 4.1 + defensive ≥ 2-distinct-cardinal-directions check per § 6.
8. `junction_propagation.py` — 3 modes (JUNCTION_LOCAL_ONLY default, GLOBAL_MAX_INHERITANCE, INDEPENDENT_WIDTHS) per § 4.10.
9. `area_accounting.py` — segment decomposition + union via 1cm rasterization (documented v1 simplification vs spec's O(N³ log N) sweep-line; correctness verified against spec cases).
10. `validator.py` — 20 invariants tiered ALL-PATHS / HAS-CORRIDOR-ONLY per § 4.6.
11. `corridor_designer.py` — public orchestrator per § 5.

**Test files** (11 of 9 planned — split for clarity):
- `test_c8_schema.py` (33 tests)
- `test_c8_topology_dispatch.py` (21)
- `test_c8_grid_quantization.py` (21)
- `test_c8_validator.py` (18)
- `test_c8_widths_and_taper.py` (15)
- `test_c8_spatial_model.py` (15)
- `test_c8_spatial_feasibility.py` (11)
- `test_c8_has_corridor_flag.py` (11)
- `test_c8_failure_modes.py` (10)
- `test_c8_area_accounting.py` (10)
- `test_c8_geometric_connectivity.py` (9)
- Total: **174 tests** (target was ~155).

**Verification cases reproduced exactly**:
- Spec § 4.3 worked-example table on all 7 C7 bay sizes (`test_c8_grid_quantization.py`).
- Spec § 4.8 1m taper 1.0→1.5 = 1.25 m² (`test_c8_area_accounting.py`).
- Spec § 4.8 L-shape v0.3 case = 7.000 m² (`test_c8_area_accounting.py`).
- Spec § 4.10 worked example: BRANCH end gets junction-max width with truncated taper (`test_c8_widths_and_taper.py`).

**End-to-end pipeline**: C4 → C5 → C6 → C7 → C8 runs cleanly on the bangalore_40x60 fixture; 3 candidates in, 3 designed corridors out, all valid.

---

## Δ.3 — Track 3 denominator confirmed: 19

Per the S31 Doubt 5 resolution. All status-block summaries this session use "X of 19" framing. Old "X of 17" labels in carried-forward documents (v7 and earlier) remain as historical record per § Δ.0 of v3.5→v3.6 delta.

---

## Δ.4 — Spec defect surfaced + S32 implementation deviation

**Issue** (filed as **B-129**): Spec § 4.3.1 truncation rule (`taper_zone_m ≤ length / 2`) conflicts with Inv 20 (`constant_middle_length ≥ length / 2`) on the spec's own § 4.10 worked example.

The BRANCH segment in § 4.10 (length=5m, single junction at start, taper=3.3m → truncated to 2.5m by § 4.3.1) yields `middle = 5 - 2.5 = 2.5m`, which equals length/2. Marginal pass for single-end-tapered case. But for two-end-tapered case at the same length, both invariants cannot simultaneously hold.

**S32 deviation** (made the build LOCKABLE while preserving spec intent):
The schema's Inv 20 check counts only **actual** tapers (ends where `start_width != constant_width` OR `end_width != constant_width`), not 2× always.
- For one-end-tapered segment: middle = length - 1×taper.
- For two-end-tapered segment: middle = length - 2×taper.

This matches the spec's worked-example *intent* (one-end taper, middle preserved) while keeping Inv 20 strictly satisfiable.

**Resolution path**: v0.6 PROPOSED amendment; Ramalingam adjudicates per Rule 8.

---

## Δ.5 — Adopted: B-128 EXECUTABLE integrity-check protocol

S31 INTEGRITY CHECK was a shallow check (claimed test count without executing pytest against the bundle's tree). This shipped a defective v8 bundle. Adopting B-128 as a permanent process improvement starting S32 close:

**New mandatory step in Rule 10.6 INTEGRITY CHECK protocol**:
> Before bundle delivery, clone the assembled `06_upstream_codebase/` into a temp directory, run `pytest`, confirm the claimed test count actually reproduces. Any SHIPPED component whose production code is not in the upstream snapshot is a SHIP-claim violation that must be resolved before bundle delivery.

S32 v9 bundle assembly will execute this check; result documented in `05_integrity_check/03_integrity_check_S32.md`.

---

## Δ.6 — Backlog deltas

**S32 additions**: B-127, B-128, B-129. Pre-S32 max: B-126. **New canonical max: B-129**.

**B-127** — Reconstruct C6 production tests from SPEC v0.7 § 7 (M effort; trigger: post-C8 SHIP).
**B-128** — Bundle integrity check should verify SHIPPED components have production code in upstream (S effort; ADOPTED at S32 close per Δ.5).
**B-129** — Spec § 4.3.1 truncation rule conflicts with Inv 20 (S effort; trigger: next C8 spec amendment cycle; v0.6 PROPOSED needed).

---

## Δ.7 — Process patterns observed this session

- **Pattern B (build-without-wiring) avoided**: deployed C6 before touching C8, verified imports first.
- **Pattern C (scores-without-truth) avoided**: empirically established the actual baseline (1539, NOT 1725) before claiming any cumulative count.
- **Rule 8 honored**: implementation deviation (Δ.4) does not self-LOCK; filed as B-129 for Ramalingam adjudication.
- **Rule 9.2 honored**: B-127, B-128, B-129 filed without permission needed.

---

**End of v3.7 delta. Master doc canonical going forward.**
