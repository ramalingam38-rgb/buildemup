# S47 — C14 v0.2 BUILD LOCKED

**Component:** C14 — Connection-Graph Quality Engine
**Status:** v0.2 BUILD LOCKED at S47 (Ramalingam directive, 2026-05-14)
**Spec authority:** spec_C14_v0_2_LOCKED.md at S46 (this directory mirrors that LOCK with implemented code)

## Contents

`components/c14/` — 14 production modules, ~4,188 lines

| Module | Role |
|---|---|
| `versioning.py` | C14_VERSION constants, schema version |
| `errors.py` | Error hierarchy (LocalC14Error, PerLayoutCirculationError) |
| `contracts.py` | Type contracts shared with C13/C15 |
| `config.py` | C14Config with STRICT/WARN modes |
| `cache_keys.py` | C14CacheKeys tier composition |
| `schema.py` | CirculationFlag, CirculationGraphReport (~612 lines) |
| `graph_construction.py` | Phase α — graph build from C13 door geometry |
| `node_metrics.py` | Phase β — BFS depth + Brandes betweenness centrality |
| `layout_metrics.py` | Phase γ — Hillier 1984 MD/RA + Krüger-Vieira 2012 D(k) + RRA + integration |
| `flag_emission.py` | Phase δ — 6 detectors + A6 truncation cap |
| `advisory_passthrough.py` | Phase ε — byte-identical C13 advisory passthrough |
| `report_assembly.py` | Phase ζ — final assembly |
| `orchestrator.py` | Public entry point — STRICT/WARN dispatch |
| `__init__.py` | Module exports |

`tests/test_c14/` — 5 test suites (175 tests total)

| Suite | Tests | Coverage |
|---|---|---|
| `test_c14_foundational_layer.py` | 78 | schema + invariants + frozen dataclass |
| `test_c14_sub2_phase_alpha_beta.py` | 25 | graph + node metrics |
| `test_c14_sub3_phase_gamma.py` | 19 | Hillier RRA, Brandes integration |
| `test_c14_sub4_phases_delta_epsilon_zeta.py` | 30 | detectors + passthrough + assembly |
| `test_c14_sub5_orchestrator.py` | 23 | STRICT/WARN dispatch, batch behavior |

## 4 in-build amendments absorbed into LOCK

1. **Schema E11'' upper bound widened 2.0 → 10.0** — Hillier 1984 / MDPI 2024 confirms typical RRA range 0-3 with pathological deeper values
2. **Main-entry exemption from DEAD_END_ISOLATION false positive** — main entries should never trip dead-end isolation detector
3. **category_coverage_low emission moved to FIRST** in structural order — cap was eating meta-signal
4. **Cache-key call signature fix** — alignment with C13/C15 cache_keys composition pattern

## Test result at LOCK

3664 passed / 3 skipped / 0 failed (was 3489 at S46 close → +175 from C14)
Stable across 3 consecutive runs in S47 build sub-sessions.

## Critique walk (Rule 7)

External 11-item analysis walked at S47. Verdicts:
- 1 strong VALID (Item 8 PBT layer missing — shipped 0, spec mandated ≥15)
- 4 VALID-BUT-BACKLOG
- 3 DOCUMENTED (already-filed backlog)
- 4 MISFRAMED (lex-bias, Brandes scaling residential, cache versioning, geometric grounding)

6 new backlog items filed.

## LOCK chain

v0.1 PROPOSED (S46) → v0.2 PROPOSED-DELTA (S46) → v0.2 LOCKED SPEC (S46) → **v0.2 LOCKED BUILD (S47, this directory)**
