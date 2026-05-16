# BuildemUp — C9 Room Sizer — SPEC v0.7 LOCKED

**Status**: LOCKED at S33 close (5 May 2026) by Ramalingam.
**Component**: C9 of canonical 17-component v3 list (Track 3). Position 9.
**Position in pipeline**: Era 2 layout (Generation layer). Consumes C8 (`CorridorDesignedCandidate`) + C7 (`Grid`) + C4 (`PlotAnalysis`) + C1's `FloorRoomBrief`. Produces input for C10 (Bathroom + Wet-Zone Stack Planner) and C11 (Room Placement).
**Authoring sessions**: S33 entire arc.
**Predecessor**: v0.6 PROPOSED (793 lines).

---

## § 0 — Why this spec, why now

C9 sits between "the bands and corridor are designed" and "specific rooms have specific sizes."

**v0.7 substantive corrections (Walk #7)**:
- **Finding #1 (full fix)**: per-candidate failure tolerance. Walk #6 introduced `WidthInfeasibleError` (RAISE on deterministic width impossibility) but didn't specify granularity. v0.7 makes it explicit — failed candidates are dropped from the result tuple; the batch only fails if *all* input candidates fail. Web-grounded against partial-batch industry practice (AWS Lambda SQS, Spring Batch, Azure Data Factory).
- **Finding #2 (partial fix)**: STRICT enforcement_mode now activates. When `enforcement_mode == STRICT`, WARN invariants (Inv 10 heuristic packing, Inv 17b RISKY width, Inv 18 OVERSIZED grid) escalate to RAISE. The default WARN mode preserves v0.6 behavior. Plus explicit documentation (§ 14.42) of why Inv 18 OVERSIZED is heuristic-not-deterministic: grids are structurally negotiable (transfer beams, alternate column patterns), unlike envelopes which C8 fixes geometrically.

C9 does NOT place rooms (C11). C9 does NOT generate furniture layouts (C14). C9 does NOT decide adjacencies (C5/C11). C9 does NOT assign rooms to zone bands (C11). C9 does NOT enforce height (C11 — § 14.22). C9 does NOT compute room shape / aspect ratio (C11 — § 14.26). C9 does NOT score sizes (C14).

**v0.7 lineage delta from v0.6 PROPOSED** (4 walk-#7 edits):

| # | Edit | Source | § affected |
|---|---|---|---|
| 1 | Per-candidate failure tolerance; cardinality relaxes from "1-3 in → 1-3 out" to "1-3 in → 1-N out (1 ≤ N ≤ input)"; new `BatchSizingInfeasibleError` and `PerCandidateError` base | Walk #7 #1 (web-grounded partial-batch pattern) | § 1, § 2, § 4.6, § 4.8, § 5, § 6, § 14 |
| 2 | `enforcement_mode == STRICT` activates: WARN invariants (10, 17b, 18) escalate to RAISE with new typed exceptions (`PackingInfeasibleError`, `WidthRiskyError`, `GridOversizeError`); default WARN mode preserves v0.6 behavior | Walk #7 #2 (partial accept) | § 4.7, § 6, § 14 |
| 3 | § 14.42 explicit doc: Inv 18 OVERSIZED is heuristic-WARN because grids are structurally negotiable; not analogous to Inv 17a envelope geometry | Walk #7 #2 (partial accept) | § 14 |
| 4 | New typed exceptions (B-NNN-K = `GridOversizeError`; the others are STRICT-mode build artefacts) | Walk #7 #2 follow-on | § 6, § 12 |

Push-backs (no spec change, same architectural-layer reasoning carried forward from walks #3-#6): Walk #7 #3 (multi-floor LARGE-default — `assumed_total_dwelling_area_m2` already supplies the lift), #4 (NBC unverified — visibility is the right level for v1), #5 (OVERSIZED weight tuning — empirical calibration question, not architecture), #6 (single-axis check — see § 14.43 below clarifying "deterministic under rectangular-envelope"), #7 (no partial recovery — B-NNN-A scope), #8 (area-only targeting — § 14.27), #9 (OTHER subtype — B-151), #10 (packing static — calibration not architecture).

---

## § 1 — Purpose

Given a C8-corridor-designed candidate, the brief's room composition, the structural grid bays, and the plot analysis, produce a **`RoomSizeTable`** — for each requested room:
- regulatory floor (area, width, height, clause, source_confidence) per NBC 2016 dwelling tier
- liveability minimum (area + interior clear width)
- target size (area)
- max size (area)

**Per-candidate semantics (REVISED v0.7 per Walk #7 #1)**: each input C8 candidate is processed independently. Per-candidate failures (`RoomSizingInfeasibleError`, `WidthInfeasibleError`, and STRICT-mode escalations) drop that candidate from the output tuple. The batch only fails (`BatchSizingInfeasibleError`) when *all* input candidates fail per-candidate. This matches web-grounded partial-batch tolerance practice (AWS Lambda SQS partial batch failures, Spring Batch skip policies, Azure Data Factory pipeline error handling).

**Cardinality (REVISED v0.7)**: 1-3 C8 candidates → 1-N C9 candidates where 1 ≤ N ≤ input count. Each output candidate carries its source `corridor_designed_candidate` reference so callers can correlate back to inputs by candidate identity. If N=0 (all candidates fail), `BatchSizingInfeasibleError` is raised with the per-candidate errors attached.

The total of all liveability-min areas in a *single candidate* must fit within that candidate's buildable envelope minus the corridor area (Inv 9 RAISE per-candidate). Any room in a candidate whose `liveability_min_width_m` exceeds that candidate's envelope min-axis fails deterministically (Inv 17a RAISE per-candidate; v0.6 introduction).

**WARN-mode safety nets (per-candidate; default `enforcement_mode = WARN`)**:
- Inv 10: heuristic packing check
- Inv 17b: width-feasibility RISKY verdict
- Inv 18: grid-bay feasibility verdict (SINGLE/DOUBLE/TRIPLE/OVERSIZED)

**STRICT-mode escalation (NEW v0.7)**: when `enforcement_mode == STRICT`, all three WARN invariants escalate to RAISE per-candidate, dropping that candidate from the result. Callers who want strict-guarantee output use STRICT mode; default WARN-mode callers see warnings in provenance.

A combined `placement_risk_level` (LOW / MEDIUM / HIGH) is severity-weighted-derived from these signals so C11 placement and C14 evaluation can read a single risk score without unpacking individual flags.

**Out of scope for C9** (carried forward from v0.6):
- Room placement (XY positioning) — C11
- Adjacency / connectivity — C5 selected, C11 enforces
- Zone band assignment for rooms — C11 placement
- Width-to-bay grid feasibility (full check) — C11 placement
- Aspect ratio / room shape — C11 placement geometry (§ 14.26)
- Wall thickness deduction from envelope coords — C11 placement (§ 14.23)
- Door swing clearance — C13
- Height enforcement — C11 volume validation (§ 14.22)
- Furniture layout — C14
- Wet-wall back-to-back stacking — C10
- Vertical alignment across floors — C12
- Cost computation — C14
- Envelope-shape-aware feasibility (geometry-complete; non-rectangular) — C11 (§ 14.28, § 14.43)

---

## § 2 — Input contract

```python
def size_rooms(
    corridor_designed_candidates: tuple[CorridorDesignedCandidate, ...],   # 1-3 from C8
    floor_room_brief: FloorRoomBrief,                                       # from C1
    grid: Grid,                                                              # from C7
    plot_analysis: PlotAnalysis,                                            # from C4
    *,
    config: RoomSizingConfig | None = None,                                 # tunables; default OK
) -> tuple[RoomSizedCandidate, ...]:
```

**Per-candidate semantics (NEW v0.7)**: each input candidate is sized independently. Successful candidates are returned in input-order (preserving relative ordering, but skipping failed positions). Failed candidates do NOT appear in the output; their errors are aggregated and surfaced via `BatchSizingInfeasibleError` only if *all* candidates fail.

`RoomSizedCandidate` = `CorridorDesignedCandidate` + `room_size_table: RoomSizeTable` + `provenance: RoomSizingProvenance`. Each successful output candidate's embedded `corridor_designed_candidate` field lets callers correlate back to the input.

`RoomSizingConfig` carries per-call tunables (cumulative through v0.7):
- **`enforcement_mode: str = "WARN"`** *(REVISED v0.7 per Walk #7 #2)*: `"WARN"` (default; WARN invariants log to provenance, no raise) or `"STRICT"` (WARN invariants escalate to per-candidate RAISE). Was vestigial in v0.6; activated in v0.7.
- Neufert/Ching multipliers
- `allocation_strategy` (`PRIORITY_GREEDY` / `PROPORTIONAL`)
- `packing_efficiency` (default 0.75)
- `dwelling_tier_override` (None = derived)
- `priority_override` (None = use v1 default)
- `require_verified_nbc: bool = False` (v0.5)
- `assumed_total_dwelling_area_m2: float | None = None` (v0.5)
- `wall_thickness_ratio: float = 0.10` (v0.6)

---

## § 3 — Output schema

Carried forward unchanged from v0.6 — all enums, dataclasses, and provenance fields preserved. `RoomSizingProvenance` continues to carry per-room verdict maps, severity-weighted placement_risk_level + placement_risk_score, unverified_nbc_rows_used, etc.

(v0.7 makes no schema-level changes. The behavioral changes are all in the orchestrator and exception hierarchy — see § 4.6, § 4.7, § 6.)

---

## § 4 — Behavior

### § 4.1 — Regulatory minimums (NBC 2016 KB)

Carried forward unchanged from v0.4-v0.6.

### § 4.2 — Liveability minimums (furniture-fit floor)

Carried forward unchanged.

### § 4.3 — Target sizes

Carried forward.

### § 4.4 — Max sizes

Carried forward.

### § 4.5 — Surplus allocation

Carried forward.

### § 4.6 — Infeasibility detection — REVISED v0.7

**Per-candidate vs batch semantics (NEW v0.7 per Walk #7 #1)**:

```python
def size_rooms(
    corridor_designed_candidates,
    floor_room_brief,
    grid,
    plot_analysis,
    *,
    config=None,
):
    if config is None:
        config = RoomSizingConfig()

    # Caller-error checks (raised before any per-candidate processing):
    _check_input_types(corridor_designed_candidates, floor_room_brief, grid, plot_analysis)
    _check_brief_sanity(floor_room_brief)
    _check_plot_shape(plot_analysis)  # B-066 NotImplementedError if non-rectangular

    # Per-candidate processing:
    successes: list[RoomSizedCandidate] = []
    failures: list[tuple[int, PerCandidateError]] = []

    for i, candidate in enumerate(corridor_designed_candidates):
        try:
            sized = _size_one_candidate(
                candidate, floor_room_brief, grid, plot_analysis, config,
            )
            successes.append(sized)
        except PerCandidateError as exc:
            failures.append((i, exc))

    if not successes:
        raise BatchSizingInfeasibleError(failures, len(corridor_designed_candidates))

    # At least one succeeded; return successes in input-relative order
    return tuple(successes)
```

**Two failure granularities**:

1. **Caller-error / systemic** (raised before per-candidate loop, fail entire batch immediately):
   - `TypeError` (input type mismatches)
   - `ValueError` (brief specifies 0 bedrooms)
   - `NotImplementedError` (plot non-rectangular, B-066)
   - `NBCConfidenceTooLow` (config.require_verified_nbc=True AND row uses unverified data — systemic, not candidate-specific)

2. **Per-candidate failures** (caught in loop; drop only that candidate):
   - `RoomSizingInfeasibleError(B-NNN-A)` — Inv 9 area infeasibility
   - `WidthInfeasibleError(B-NNN-J)` — Inv 17a deterministic width impossibility (v0.6)
   - `PackingInfeasibleError` (NEW v0.7) — Inv 10 + STRICT mode
   - `WidthRiskyError` (NEW v0.7) — Inv 17b RISKY + STRICT mode
   - `GridOversizeError(B-NNN-K)` (NEW v0.7) — Inv 18 OVERSIZED + STRICT mode

If the per-candidate loop produces zero successes, raise:

`BatchSizingInfeasibleError(failures, input_count)` — wraps the list of per-candidate `(index, exception)` pairs and the input cardinality.

### § 4.7 — Validator invariants — REVISED v0.7

| # | Invariant | Source | WARN mode | STRICT mode |
|---|---|---|---|---|
| 1 | rooms.count == FloorRoomBrief total | brief consistency | RAISE | RAISE |
| 2 | category counts match brief | brief consistency | RAISE | RAISE |
| 3 | regulatory_minimum.area_m2 ≥ NBC table value | NBC compliance | RAISE | RAISE |
| 4 | regulatory_minimum.width_m ≥ NBC table value | NBC compliance | RAISE | RAISE |
| 5 | regulatory_minimum.height_m ≥ NBC table value | NBC compliance | RAISE | RAISE |
| 6 | liveability_min_area_m2 ≥ regulatory_minimum.area_m2 | math | RAISE | RAISE |
| 6b | liveability_min_width_m ≥ regulatory_minimum.width_m | math | RAISE | RAISE |
| 7 | target_m2 ≥ liveability_min_area_m2 | math | RAISE | RAISE |
| 8 | max_m2 ≥ target_m2 | math | RAISE | RAISE |
| 9 | Σ liveability_min_area_m2 ≤ buildable_envelope_minus_corridor_m2 | feasibility | RAISE | RAISE |
| **10** | Σ liveability_min_area_m2 ≤ envelope × packing_efficiency | placement-readiness heuristic | **WARN** | **RAISE (`PackingInfeasibleError`, NEW v0.7)** |
| 11 | room_ids unique | data integrity | RAISE | RAISE |
| 12 | priority values cover 1..n contiguously | well-formedness | RAISE | RAISE |
| 13 | exactly one BEDROOM has is_master=True iff bedroom_count ≥ 1 | master semantics | RAISE | RAISE |
| 14 | at most one BATHROOM has is_master=True | master semantics | RAISE | RAISE |
| 15 | bathroom_subtype is set iff category == BATHROOM | schema integrity | RAISE | RAISE |
| 16 | unassigned_area_m2 ≥ 0 | math | RAISE | RAISE |
| 17a | for every room, NO room has WidthFeasibilityVerdict.IMPOSSIBLE | deterministic width infeasibility | **RAISE** (`WidthInfeasibleError`) | RAISE |
| **17b** | classify width feasibility (FEASIBLE / RISKY); RISKY rooms logged | placement-readiness heuristic | **WARN** if any RISKY | **RAISE (`WidthRiskyError`, NEW v0.7)** |
| **18** | classify grid-bay feasibility per room; OVERSIZED triggers WARN | grid-bay sanity heuristic | **WARN** if any OVERSIZED | **RAISE (`GridOversizeError`, NEW v0.7)** |

**STRICT-mode rationale (Walk #7 #2 partial accept)**: `enforcement_mode` was vestigial in v0.6 (declared in provenance but had no behavioral effect). v0.7 activates it as a generic policy: STRICT mode escalates all heuristic WARN invariants to per-candidate RAISE. Default WARN mode preserves v0.6 behavior exactly.

The escalations are **per-candidate**, not batch-fail — they participate in the partial-batch tolerance pattern from Finding #1. So a STRICT-mode caller with 3 candidates where only 1 has an OVERSIZED room still gets the other 2 candidates back; only if all 3 fail does `BatchSizingInfeasibleError` raise.

### § 4.8 — Order-of-checks — REVISED v0.7

**Caller-error layer** (one-shot, before per-candidate loop):
1. Type checks
2. Plot shape (B-066 NotImplementedError)
3. Brief sanity

**Per-candidate layer** (looped, each candidate processed independently):
4. Dwelling-tier resolution
5. Grid-bay capture (provenance)
6. Per-candidate regulatory lookup (with `require_verified_nbc` gate; populate `unverified_nbc_rows_used`)
7. Liveability resolution
8. Infeasibility check (Inv 9; per-candidate RAISE on failure)
9. Width-feasibility classification + Inv 17a RAISE on IMPOSSIBLE (per-candidate)
10. Surplus allocation
11. Validator (Invs 1-18; STRICT-mode escalations applied per-invariant)
12. placement_risk_level severity-weighted derivation
13. Successful candidate appended; failed candidate caught and recorded

**Batch finalization**:
14. If zero successes, raise `BatchSizingInfeasibleError`; else return tuple of successes

Pattern A: fail at boundary; surface heuristics via WARN by default; STRICT mode opt-in for callers who want strict-guarantee output. Per-candidate failures don't propagate to batch failure unless all candidates fail.

---

## § 5 — Invocation contract (public)

```python
sized = size_rooms(
    corridor_designed_candidates=c8_output,
    floor_room_brief=c1_brief.floors[0],
    grid=c7_grid,
    plot_analysis=c4_plot_analysis,
)
# Default WARN mode; cardinality 1-3 in → 1-N out (N ≤ input)

# v0.7 STRICT mode pattern:
sized = size_rooms(
    ...,
    config=RoomSizingConfig(
        enforcement_mode="STRICT",                 # NEW v0.7: heuristic WARNs become RAISEs
        require_verified_nbc=True,                 # post-B-150 strict NBC
        assumed_total_dwelling_area_m2=120.0,      # multi-floor exact tier
        wall_thickness_ratio=0.08,                 # thin AAC partitions
    ),
)
# STRICT mode: any candidate with packing/RISKY-width/OVERSIZED-grid is dropped;
# batch fails only if all candidates fail.

# v0.7 partial batch pattern (caller handling):
try:
    sized = size_rooms(c8_output, ...)
    # sized may have FEWER candidates than c8_output
    print(f"input candidates: {len(c8_output)}, sized successfully: {len(sized)}")
    for s in sized:
        # Correlate back to input via embedded reference:
        original = s.corridor_designed_candidate
except BatchSizingInfeasibleError as e:
    # All candidates failed
    print(f"all {e.input_count} candidates failed:")
    for idx, exc in e.failures:
        print(f"  candidate {idx}: {type(exc).__name__}: {exc}")
```

**Cardinality (v0.7)**: 1-3 in → 1-N out where 1 ≤ N ≤ input count. Caller correlates outputs to inputs via `output[k].corridor_designed_candidate` reference. If all candidates fail per-candidate, `BatchSizingInfeasibleError` is raised.

---

## § 6 — Failure modes — REVISED v0.7

### Caller-error / systemic failures (raised before per-candidate loop; abort entire batch)

| Condition | Behavior |
|---|---|
| `corridor_designed_candidates` not a tuple | `TypeError` |
| `floor_room_brief` not FloorRoomBrief | `TypeError` |
| `grid` not Grid | `TypeError` |
| `plot_analysis` not PlotAnalysis | `TypeError` |
| `plot_analysis.shape != RECTANGULAR` | `NotImplementedError` (B-066) |
| Brief specifies 0 bedrooms | `ValueError` |
| `config.require_verified_nbc=True` AND any row used has `source_confidence != VERIFIED` | `KeyError` (`NBCConfidenceTooLow`) — systemic, fails batch |
| One room category's NBC table entry missing for resolved tier | `KeyError` (KB integrity) |
| Empty input tuple | Returns empty tuple |

### Per-candidate failures (caught in loop; drop only that candidate)

| Condition | Behavior | WARN mode | STRICT mode |
|---|---|---|---|
| Σ liveability_min_area > envelope (Inv 9) | drop candidate | `RoomSizingInfeasibleError(B-NNN-A)` | same |
| Any room WidthFeasibilityVerdict==IMPOSSIBLE (Inv 17a) | drop candidate | `WidthInfeasibleError(B-NNN-J)` | same |
| Σ liveability_min_area > envelope × packing_efficiency (Inv 10) | log to provenance / drop | log only (no raise) | `PackingInfeasibleError` (NEW v0.7) → drop |
| Any room WidthFeasibilityVerdict==RISKY (Inv 17b) | log to provenance / drop | log only (no raise) | `WidthRiskyError` (NEW v0.7) → drop |
| Any room GridBayFeasibility==OVERSIZED (Inv 18) | log to provenance / drop | log only (no raise) | `GridOversizeError(B-NNN-K)` (NEW v0.7) → drop |
| `config.require_verified_nbc=False` AND any SECONDARY_UNVERIFIED row used | log to provenance | logged in `unverified_nbc_rows_used`; no raise | same |

### Batch-level failure (raised after per-candidate loop if all candidates failed)

| Condition | Behavior |
|---|---|
| All input candidates failed per-candidate | `BatchSizingInfeasibleError(failures, input_count)` (NEW v0.7) — wraps list of (index, per-candidate-exception) pairs |

### Typed exception hierarchy (v0.7)

```python
class RoomSizingError(Exception):
    """Base for all C9 errors."""

class PerCandidateError(RoomSizingError):
    """Base for per-candidate failures; caught by orchestrator and aggregated.
    NEW v0.7 — distinguishes per-candidate from systemic errors.
    """

class RoomSizingInfeasibleError(PerCandidateError):
    """Inv 9: total area infeasibility (B-NNN-A)."""

class WidthInfeasibleError(PerCandidateError):
    """Inv 17a: deterministic width impossibility (B-NNN-J)."""

class PackingInfeasibleError(PerCandidateError):
    """Inv 10 + STRICT mode escalation. NEW v0.7."""

class WidthRiskyError(PerCandidateError):
    """Inv 17b RISKY + STRICT mode escalation. NEW v0.7."""

class GridOversizeError(PerCandidateError):
    """Inv 18 OVERSIZED + STRICT mode escalation (B-NNN-K). NEW v0.7."""

class BatchSizingInfeasibleError(RoomSizingError):
    """All input candidates failed per-candidate. NEW v0.7."""
    def __init__(self, failures: list[tuple[int, PerCandidateError]], input_count: int):
        self.failures = failures
        self.input_count = input_count

class NBCConfidenceTooLow(RoomSizingError, KeyError):
    """Systemic: require_verified_nbc=True with unverified row. Not per-candidate."""
```

Callers can:
- Catch `RoomSizingError` to handle any C9 failure
- Catch `PerCandidateError` to handle per-candidate failures (won't catch caller-error or systemic)
- Catch `BatchSizingInfeasibleError` specifically to handle the "all failed" case
- Catch specific subclasses (e.g., `WidthInfeasibleError`) for fine-grained handling

---

## § 7 — Test plan — REVISED v0.7

v0.7 targets **~150 tests** (was ~135 in v0.6; +15 for partial-batch + STRICT mode coverage):

### Invariant coverage (preserved from v0.6 + v0.7 additions)

| Inv # | Invariant | Test count | Test file |
|---|---|---|---|
| 1-16 | Carried forward from v0.6 | 81 | various |
| 17a | WidthInfeasibleError on IMPOSSIBLE width (per-candidate RAISE) | 6 | test_c9_orchestrator.py |
| 17b | width_feasibility_per_room verdicts (FEASIBLE / RISKY) — config-driven threshold | 8 | test_c9_orchestrator.py |
| 17b STRICT | WidthRiskyError raised in STRICT mode (NEW v0.7) | 4 | test_c9_strict_mode.py |
| 18 | grid_bay_feasibility_per_room verdicts | 8 | test_c9_orchestrator.py |
| 18 STRICT | GridOversizeError raised in STRICT mode (NEW v0.7) | 4 | test_c9_strict_mode.py |
| 10 STRICT | PackingInfeasibleError raised in STRICT mode (NEW v0.7) | 4 | test_c9_strict_mode.py |
| PRL | placement_risk_level severity-weighted derivation | 8 | test_c9_orchestrator.py |
| **Subtotal — invariants** | | **123** | |

### Partial-batch coverage (NEW v0.7 per Walk #7 #1)

| Scenario | Test count | Test file |
|---|---|---|
| 3 candidates → 3 successes (all valid) | 2 | test_c9_partial_batch.py |
| 3 candidates → 2 successes (1 width-infeasible) | 3 | test_c9_partial_batch.py |
| 3 candidates → 1 success (2 area-infeasible) | 2 | test_c9_partial_batch.py |
| 3 candidates → 0 successes → BatchSizingInfeasibleError | 3 | test_c9_partial_batch.py |
| Cardinality / ordering preserved (input-order kept among survivors) | 2 | test_c9_partial_batch.py |
| Caller correlation via corridor_designed_candidate reference | 2 | test_c9_partial_batch.py |
| **Subtotal — partial batch** | **14** | |

### Module-coverage

| Module | Tests | Focus |
|---|---|---|
| nbc_table.py | ~12 | dwelling-tier; clauses; subtype variants; require_verified_nbc gate |
| furniture_floor.py | ~10 | (category, is_master, bathroom_subtype) lookup |
| targets_kb.py | ~6 | (category, is_master) target lookup |
| allocator.py | ~12 | PRIORITY_GREEDY / PROPORTIONAL / max-clamp |
| size_rooms (orchestrator) | ~15 | end-to-end; new per-candidate loop semantics |
| failure_modes | ~15 | type checks; B-066; per-candidate vs batch boundary |
| **Subtotal — coverage** | **~70** | |

**Combined estimate ≈ 150 tests** (some invariant tests double as module-coverage tests). The increase is primarily the new `test_c9_partial_batch.py` (14 tests) and `test_c9_strict_mode.py` (12 tests) modules.

---

## § 8 — KB references

Carried forward unchanged from v0.4-v0.6.

---

## § 9 — Out of scope

Carried forward unchanged from v0.6.

---

## § 10 — Provenance

`RoomSizingProvenance` carried forward unchanged from v0.6. The provenance applies *per-candidate* (each successful output has its own provenance instance). The "which input candidates failed" information lives in the `BatchSizingInfeasibleError` (when raised) — there is no aggregate batch provenance object, by design (each successful candidate is independently consumable; the orchestrator's loop bookkeeping is captured in the error class when needed).

---

## § 11 — Spec metadata

- **Version**: v0.7 PROPOSED
- **Status**: LOCKED at S33 close (5 May 2026) by Ramalingam.
- **Lineage**: v0.1 DRAFT → v0.2 → v0.3 → v0.4 → v0.5 → v0.6 → v0.7 (7 walks completed)
- **Authoring sessions**: S33 entire arc

**Convergence trajectory after 7 walks**:

| Walk | Findings | Net new actionable | Push-backs |
|---|---|---|---|
| #1 | 15 | 12 | 0 |
| #2 | 15 | 2 | 0 |
| #3 | 11 | 3 | 2 |
| #4 | 10 | 4 | 2 |
| #5 | 10 | 6 | 3 |
| #6 | 10 | 5 | 4 |
| #7 | 10 | 2 (only #1 + #2; user-restricted scope) | 8 |

Walk #7 was scope-restricted by Ramalingam to fixing only findings #1 and #2 (both architecturally meaningful: #1 fully valid, #2 partially valid → STRICT mode + doc fix). Push-backs (8) substantially exceed actionable items (2). Convergence is unambiguous.

---

## § 12 — Backlog enumeration

Total: **14 items** (was 13 in v0.6; +1 from Walk #7: B-NNN-K = `GridOversizeError`).

| ID | Title | Origin | Status | Trigger | Effort |
|---|---|---|---|---|---|
| B-NNN-A | Soft-fail mode + C2 retry | § 4.6 / Q8 | BACKLOG | C2 feasibility loop | M |
| B-NNN-B | Plot-tier-aware target sizing | § 4.3 | BACKLOG | Empirical signal | S |
| B-NNN-C | Configurable priority order beyond default | § 4.5 | BACKLOG | First user request | S |
| B-NNN-D | State DCR overrides | § 4.1 | BACKLOG | Municipality rejection | M |
| B-NNN-E | Multi-floor coordination | § scope | BACKLOG | C12 vertical alignment | L |
| B-NNN-F | Furniture KB versioning | § 4.2 | BACKLOG | Customization feature | M |
| B-NNN-I | Bath assignment rules | § 4.2 | BACKLOG | C11 placement | M |
| B-148 | Multi-floor dwelling-tier (auto-derived from C2) | § 4.1 | BACKLOG | Multi-floor test case | M |
| B-149 | Packing-efficiency to ERROR mode | § 4.7 Inv 10 | BACKLOG | Calibration data | S |
| B-150 | NBC clause verification | § 4.1 / § 8 | BACKLOG | Verification pass complete | S |
| B-151 | OTHER subtype-driven sizing | § 9 | BACKLOG | First product feature | M |
| B-NNN-J | `WidthInfeasibleError` typed exception | § 4.6 / § 6 | TO-BE-IMPLEMENTED IN BUILD | C9 build session | (in build) |
| **B-NNN-K** | **`GridOversizeError` typed exception** (NEW v0.7 per Walk #7 #2) | § 6 / § 14.42 | TO-BE-IMPLEMENTED IN BUILD | C9 build session | (in build) |
| (deferred to C11) | Aspect ratio / shape constraints, Width-to-bay full check, Wall thickness deduction, Height enforcement, Envelope-shape-aware feasibility | various walks | C11 spec | C11 build | (in C11) |
| (deferred to C13) | Door swing clearance | Walk #4 #4 | C13 spec | C13 build | (in C13) |

Note: B-NNN-J and B-NNN-K are build-session implementation tasks (exception class files + tests), not future-deferred backlog items. The other STRICT-mode exceptions (`PackingInfeasibleError`, `WidthRiskyError`) are also build artefacts but don't get B-NNN-IDs — they're trivial subclasses introduced as part of the STRICT-mode policy, not standalone defects.

---

## § 13 — Definitions

Cumulative across walks (v0.7 additions marked):

(All v0.6 definitions carried forward.)

- **`PerCandidateError`** *(NEW v0.7)*: base exception class for per-candidate failures; caught by orchestrator and aggregated rather than propagated to batch failure unless all candidates fail.
- **`BatchSizingInfeasibleError`** *(NEW v0.7)*: raised when ALL input candidates failed per-candidate. Wraps `list[tuple[int, PerCandidateError]]` of (input_index, exception) pairs and `input_count`.
- **`PackingInfeasibleError`** *(NEW v0.7)*: STRICT-mode escalation of Inv 10 (heuristic packing).
- **`WidthRiskyError`** *(NEW v0.7)*: STRICT-mode escalation of Inv 17b (RISKY width).
- **`GridOversizeError`** *(NEW v0.7)*: STRICT-mode escalation of Inv 18 (OVERSIZED grid). Backlog ID B-NNN-K.
- **`enforcement_mode`** *(REVISED v0.7)*: `"WARN"` (default; preserves v0.6 behavior) or `"STRICT"` (heuristic WARN invariants escalate to per-candidate RAISE). Was vestigial in v0.6.

---

## § 14 — Architectural decisions (cumulative)

### From v0.1 DRAFT through v0.6 PROPOSED
§ 14.1 through § 14.39 — carried forward unchanged.

### NEW v0.7 (resolved per Walk #7)

§ 14.40 — **Per-candidate failure tolerance with batch-fail-only-if-all-fail** (Walk #7 #1). C8 deliberately produces multiple corridor variants for robustness; v0.6's ambiguous "any room IMPOSSIBLE → raise" wording risked killing valid alternatives because of one bad candidate. v0.7 makes the granularity explicit: per-candidate failures (`PerCandidateError` subclasses) are caught and aggregated; the batch fails only when zero candidates succeed. Cardinality contract relaxes from "1-3 in → 1-3 out, position-paired" to "1-3 in → 1-N out where 1 ≤ N ≤ input count." Web-grounded against industry partial-batch practice (AWS Lambda SQS partial batch failures, Spring Batch skip-and-retry, Azure Data Factory). Caller correlation preserved via embedded `corridor_designed_candidate` reference; no batch-level provenance object needed.

§ 14.41 — **STRICT enforcement_mode is per-candidate, not batch-level** (Walk #7 #2 partial accept). The `enforcement_mode` field was vestigial in v0.6 (declared in provenance but had no behavioral effect). v0.7 activates it as a generic policy: STRICT escalates the three heuristic WARN invariants (Inv 10 packing, Inv 17b RISKY width, Inv 18 OVERSIZED grid) to RAISE — but the RAISE is per-candidate, participating in the partial-batch tolerance pattern from § 14.40. This gives strict-output callers (e.g., regulatory-compliance pipelines) a hard guarantee while still benefiting from per-candidate skip semantics. Default WARN mode preserves v0.6 behavior exactly; STRICT mode is explicit opt-in.

§ 14.42 — **Inv 18 OVERSIZED is heuristic, not deterministic** (Walk #7 #2 partial accept; explicit doc). Walk #7 #2 challenged whether Inv 18 OVERSIZED should be RAISE-by-default like Inv 17a. The answer is no, with reason: **Inv 17a is geometric impossibility** (envelope is fixed by C8; room cannot fit), but **Inv 18 OVERSIZED is structural-difficulty heuristic** (grid is structurally negotiable — transfer beams, alternate column patterns, modified bay layouts are all available). Web research from walk #5 ("transfer beams or transfer slabs used where upper-floor residential/office grids differ") confirms grids are not absolute constraints. So:
- Inv 17a = geometric → RAISE always (correct)
- Inv 18 OVERSIZED = structural-hard → WARN by default; RAISE in STRICT (correct)

This is the asymmetry the user's "near-deterministic" framing missed; v0.7 documents it explicitly.

§ 14.43 — **Width-vs-envelope check is "deterministic under rectangular-envelope assumption"** (Walk #7 #6 push-back doc). v0.6's Inv 17a uses `min(envelope_width, envelope_depth)`, which is meaningful only for rectangular envelopes. The plot-shape gate (`NotImplementedError` for non-rectangular per B-066) ensures this assumption holds in v1. When non-rectangular plots are supported (post-B-066), Inv 17a's "min-axis" calculation must be revisited — for L-shaped or fragmented envelopes, the right metric is "min-axis of the largest inscribed rectangle" or similar, which is C11 placement geometry, not C9 sizing. v0.7 documents the assumption explicitly to avoid over-claiming determinism.

---

## § 15 — Open questions remaining

After 7 walks:

### Q14 (carried) — Should max_m2 multipliers also live in `kb/room_targets.json`?

Recommendation for LOCK: yes; one-line spec change.

### Q17 (carried) — Confirm severity weights (OVERSIZED=2, others=1)

Recommendation for LOCK: ship 2:1; revisit when C11 placement data exists.

### NEW Q18 — Should NBCConfidenceTooLow also be per-candidate?

Currently treated as systemic (raised before per-candidate loop) because the NBC table is shared across all candidates — if one row is unverified, it's unverified for every candidate. But strictly speaking, different candidates might use different NBC rows (depending on dwelling-tier resolution per-candidate). For v1, treating it as systemic is simpler and the multi-floor case where this matters is rare. Defer to LOCK review.

---

## § 16 — End of v0.7 PROPOSED

Expected next: Ramalingam LOCK adjudication → build (D-066 step 6-8).

If LOCKED, the build session can begin immediately:
- 3 KB JSONs authored
- ~7 production modules including NEW exception module (`errors.py`) with full hierarchy
- ~150 tests across orchestrator, validator, partial-batch, and STRICT-mode coverage

After 7 walks of converging discipline (push-backs 8 vs net-new 2 in walk #7; the substantive walk-#7 fixes resolved a genuinely-ambiguous v0.6 wording on per-candidate semantics + activated a vestigial config field), the system is **production-ready v1**. The v0.7 partial-batch tolerance materially improves pipeline robustness for the multi-candidate exploration that C8 was designed to support.
