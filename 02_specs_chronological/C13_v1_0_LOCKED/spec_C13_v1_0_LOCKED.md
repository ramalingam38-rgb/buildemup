# C13 SPEC v1.0 LOCKED — Door Placement Engine

**LOCK authority**: Ramalingam directive S44 *"Lock it and give me the handoff"* (path c).
**LOCK date**: 2026-05-13 (S44 continuation segment, post-walk-#8 refusal).
**Composed normative spec** = v0.1 PROPOSED base + v0.2/v0.3/v0.4/v0.5/v0.6/v0.7 deltas
(see chronological spec files in `02_specs_chronological/`).

---

## What this document IS

A short LOCKED marker. The full normative spec is composed from the chronological
delta chain. This marker:

- Records LOCK authority + date
- Enumerates the LOCKED contracts (invariants, schemas, version constants)
- Names the LOCK-precondition path that was waived in choosing (c)
- Documents the v1.0 baseline for the post-LOCK fast-revision window (E4+F3)

---

## LOCKED contracts at v1.0

### Version constants

| Constant | Value | Source |
|---|---|---|
| `C13_VERSION` | `"v1.0"` | v0.1 § 1.3 |
| `C13_EDGE_PROTOCOL_VERSION` | `1` | v0.4 C3 |
| `ADVISORY_SCHEMA_VERSION` | `1` | v0.4 C8 |
| `MAX_DOORS_PER_ROOM_V1` | `2` | v0.4 C4 |
| `EXPECTED_C12_VERSION` | `"v1.0"` | v0.1 § 1.3 |
| `EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION` | `1` | v0.2 A10 |
| `EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION` | `1` | v0.2 A10 |
| `DEFAULT_CORNER_OFFSET_M` | `0.15` | v0.2 A2 / v0.4 C1 |
| `DEFAULT_GRID_SNAP_M` | inherited from C12 (`0.05`) | v0.2 A7 |

### Invariants (23 total, 6 categories per v0.6 E1)

**HARD_LEGALITY** (single-edge NBC vetoes):
- D2 — Every door sits on a doorway_feasible SharedEdge
- D3 — clear_width_m ≥ edge.min_required_clear_width_m
- D11.1 — No door connects bathroom directly to kitchen (NBC)
- D11.2 — No primary circulation routes THROUGH bathroom (NBC)
- D11.4 — Master bedroom door doesn't open directly to kitchen/bathroom (NBC)

**CONDITIONAL_LEGALITY** (graph-context-sensitive; Phase F evaluated):
- D11.3' — No through-kitchen routing when alternate route exists
- D19 — D11.3' violations carry ConditionalLegalityViolation provenance

**DETERMINISM**:
- D7 — Byte-equal replay across runs
- D8 — doors tuple sorted lex-ASC
- D12' — Phase D loop-free + tie-break deterministic
- D20 — AdvisoryFlag.causal_context defaults to None at v1.0
- D21 — Fast-revision patches preserve v1.0 contracts
- D23 — Fast-revision patches are bug-fix + stabilization scope only

**GRAPH_INTEGRITY**:
- D13 — All rooms reachable from main entry via door-induced graph (full)
- D17 — Habitable rooms reachable via PRIMARY-door graph (not secondary-only)
- D22 — Phase F is pure (verification only)

**GEOMETRY**:
- D1' — min_doors ≤ doors per room ≤ max_doors (≤ 2 at v1)
- D4 — Door fits within edge: position + width ≤ overlap_length_m
- D5 — No two doors have overlapping swing arcs
- D6 — Exactly one door has is_main_entry=True
- D9' — Bathroom outswing doors don't conflict with adjacent traversal
- D10 — clear_width_m ≤ 1.5m sanity bound
- D14 — geometric_fidelity ∈ Enum, default APPROXIMATE
- D15 — Secondary door's room has primary door first

**ADVISORY_HYGIENE**:
- D16 — AdvisoryFlag density ≤ n_rooms × 1.5; deduplicated per (room, category)
- D18 — advisory_cache_key always contains geometry_cache_key prefix

### Schema contracts

- `Door` (frozen dataclass, 9 fields including hinge_side, leaf_thickness_m, geometric_fidelity)
- `AdvisoryFlag` (frozen, with reserved `causal_context: Optional[CausalContext] = None`)
- `CausalContext` (reserved sentinel class; semantic intent docstring locked per F2)
- `SuccessfulDoorPlacement` vs `FailedDoorPlacement` (typestate discriminated union)
- `DoorPlacementBatchResult` (separate `successful` + `failed` tuples)
- `ConditionalLegalityViolation` (provenance for D19)
- `C13CacheKeys` (geometry / advisory / full split)
- `C13ConsumesFromC12Edge` (Protocol abstraction over C12 SharedEdge)
- `RoomDoorPreference` (caller-supplied for B8 secondary doors)

### Algorithm phases (LOCKED order + semantics)

- Phase A — per-room primary door selection (room-importance priority simplified to 3-tier per B6: entry > corridor-adjacent > lex-ASC)
- Phase B — swing direction assignment (bathroom-preferred-inward unless area < 4m², per A6)
- Phase C — position along edge (corner_offset_m default 0.15m, grid-snapped per A7)
- Phase D — bounded CSP-lite conflict resolution (max 5 iterations, visited-state hashing, total-order tie-break)
- Phase E — canonical output assembly + cache key generation
- Phase F — pure verification (D11.3'/D13/D17/D19 evaluation; NO mutation per D22)

---

## LOCK-precondition path WAIVED in choosing (c)

Path (a) would have required, before LOCK:
1. C14 v0.1 sketch per D11 + E2 composability validation
2. End-to-end example (C12 → C13 → C14 → C15) for one 4-room compact layout
3. Adversarial integration corpus
4. Walk #6.5 operational validation

By choosing path (c), these are deferred to **post-LOCK 90-day
fast-revision window** (E4) **with stabilization-only constraint** (F3).

**Implication**: if C14 build surfaces composability gaps in AdvisoryFlag
semantics or in the C13↔C14 contract surface, those fixes ship as
v1.0.x patches within the 90-day window OR require v1.1 spec walks
(if outside stabilization scope per F3).

---

## What this LOCK does NOT mean

Per walk #7 reviewer + walk #8 reviewer self-recognition:

> "LOCK is architecture freeze for MVP, not problem space exhausted."

Expected v1.1 amendments after telemetry collection:
- Empirical recalibration of D16 advisory density bound (currently n_rooms × 1.5)
- A1's removed weighted multipliers may reappear in C14 (not C13) as scoring weights
- D11.3' alternate-path semantics may need refinement based on real layout corpus
- Phase D convergence telemetry may reveal CSP-lite quality concerns

These are NOT LOCK breakages — they are the empirical maturation cycle
the architecture explicitly designs for.

---

## Cumulative walk summary

| Walk | Yield | Reversals | Character |
|---|---|---|---|
| #2 | 10 amendments | 0 | Foundation + amendments |
| #3 | 12 amendments | 3 (boundary correction) | C13/C14 boundary surfaced |
| #4 | 11 amendments | 1 partial (NBC veto revival) | Operational maturity |
| #5 | 4 amendments + 10 polish | 0 | First diminishing-returns inflection |
| #6 | 4 amendments + 7 polish | 0 | Sustained inflection; LOCK-CANDIDATE declared |
| #7 | 3 amendments + 4 polish | 0 | Pattern E warning surfaced |
| #8 | REFUSED (push back) | 0 | Walk-loop exit enforced per v0.7 commitment |

Total: 44 amendments composed into v1.0 LOCKED + 35 v1.x backlog items.

---

**LOCKED. Next session (S45+) work: per `NEXT_CLAUDE_HANDOFF.md`.**
