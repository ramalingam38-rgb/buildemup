# AUDIT CHECK — C13 v1.0 LOCKED spec compliance

**Scope**: line-by-line audit of C13 LOCKED contracts against the
chronological delta chain (v0.1 + v0.2 + v0.3 + v0.4 + v0.5 + v0.6 + v0.7).

---

## 1. Version constants

| Constant | Locked value | Source spec | Status |
|---|---|---|---|
| C13_VERSION | "v1.0" | v0.1 § 1.3 | ✓ |
| C13_EDGE_PROTOCOL_VERSION | 1 | v0.4 C3 | ✓ |
| ADVISORY_SCHEMA_VERSION | 1 | v0.4 C8 | ✓ |
| MAX_DOORS_PER_ROOM_V1 | 2 | v0.4 C4 | ✓ |
| EXPECTED_C12_VERSION | "v1.0" | v0.1 § 1.3 | ✓ |
| EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION | 1 | v0.2 A10 | ✓ |
| EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION | 1 | v0.2 A10 | ✓ |
| DEFAULT_CORNER_OFFSET_M | 0.15 | v0.2 A2 | ✓ |
| DEFAULT_GRID_SNAP_M | 0.05 (inherited C12) | v0.2 A7 | ✓ |

## 2. Invariants D1-D23 (6 categories per v0.6 E1)

### HARD_LEGALITY
- D2 (door on doorway_feasible edge) — v0.1 § 4 — ✓
- D3 (clear_width ≥ NBC min) — v0.1 § 4 — ✓
- D11.1 (no bath-to-kitchen) — v0.4 C2 (NBC-grounded per web search) — ✓
- D11.2 (no through-bathroom) — v0.4 C2 — ✓
- D11.4 (master bedroom not into kitchen/bath) — v0.4 C2 — ✓

### CONDITIONAL_LEGALITY (Phase F evaluated per v0.6 E1)
- D11.3' (no through-kitchen WHEN alt exists) — v0.5 D2 narrowing — ✓
- D19 (ConditionalLegalityViolation provenance) — v0.6 E1 — ✓

### DETERMINISM
- D7 (byte-equal replay) — v0.1 § 4 + v0.2 A3+A7 + v0.3 B3 — ✓
- D8 (doors lex-ASC sorted) — v0.1 § 4 — ✓
- D12' (Phase D loop-free + tie-break) — v0.2 A4 + v0.3 B3 — ✓
- D20 (causal_context defaults None) — v0.6 E3 — ✓
- D21 (fast-revision preserves v1.0 contracts) — v0.6 E4 — ✓
- D23 (fast-revision = stabilization only) — v0.7 F3 — ✓

### GRAPH_INTEGRITY
- D13 (full-graph reachability) — v0.2 A9 — ✓
- D17 (primary-graph reachability for habitable) — v0.5 D6 — ✓
- D22 (Phase F is pure) — v0.7 F1 — ✓

### GEOMETRY
- D1' (min_doors ≤ doors ≤ max_doors ≤ 2) — v0.3 B8 + v0.4 C4 — ✓
- D4 (door fits within edge) — v0.1 § 4 — ✓
- D5 (no swing-arc overlap) — v0.1 § 4 — ✓
- D6 (exactly one main_entry=True) — v0.1 § 4 — ✓
- D9' (bathroom outswing doesn't conflict) — v0.2 A6 — ✓
- D10 (clear_width ≤ 1.5m) — v0.1 § 4 — ✓
- D14 (geometric_fidelity enum, APPROXIMATE default) — v0.3 B4 + v0.4 C6 — ✓
- D15 (secondary has primary first) — v0.4 C9 — ✓

### ADVISORY_HYGIENE
- D16 (advisory density ≤ n_rooms × 1.5, deduplicated) — v0.4 C1 — ✓
- D18 (advisory_cache_key contains geometry_cache_key prefix) — v0.5 D7 — ✓

**Total: 23 invariants composed into v1.0 LOCKED. All sourced + traceable. ✓**

## 3. Reversals tracked

| Reversal | From | To | Walk | Reason |
|---|---|---|---|---|
| A1 → B1 | v0.2 weighted-shortest-path | v0.3 simple BFS + AdvisoryFlag | #3 | C13/C14 boundary correction |
| D11 → B2 | v0.2 hard invariant | v0.3 soft AdvisoryFlag | #3 | C13/C14 boundary correction |
| A8 → B6 | v0.2 9-tier semantic priority | v0.3 3-tier structural | #3 | C13/C14 boundary correction |
| (partial) B2 → C2 | v0.3 soft AdvisoryFlag only | v0.4 narrow NBC-grounded vetoes D11.1-4 | #4 | Web search verified NBC code grounds |

All reversals are documented in v0.3 + v0.4 spec rationale.

## 4. Schema contracts

- Door dataclass: 9 fields including hinge_side (v0.2 A3), leaf_thickness_m (v0.2 A3), geometric_fidelity (v0.3 B4 + v0.4 C6) — ✓
- AdvisoryFlag with causal_context reserved field (v0.6 E3 + v0.7 F2 semantic intent docstring) — ✓
- CausalContext sentinel class with LOCKED semantic intent (v0.7 F2) — ✓
- Typestate API: SuccessfulDoorPlacement vs FailedDoorPlacement (v0.3 B11) — ✓
- DoorPlacementBatchResult with separate successful + failed tuples (v0.3 B11) — ✓
- ConditionalLegalityViolation for D19 (v0.6 E1) — ✓
- C13CacheKeys (geometry/advisory/full split per v0.4 C10 + v0.5 D7) — ✓
- C13ConsumesFromC12Edge Protocol (v0.3 B5 + v0.4 C3 versioning) — ✓
- RoomDoorPreference (v0.3 B8 + v0.4 C4 bounds) — ✓

## 5. Algorithm phases LOCKED

- Phase A: 3-tier priority (entry > corridor-adjacent > lex-ASC) per v0.3 B6 — ✓
- Phase B: bathroom-preferred-inward unless area < 4m² per v0.2 A6 — ✓
- Phase C: corner_offset_m=0.15 + grid-snapped per v0.2 A2+A7 — ✓
- Phase D: bounded CSP-lite (max_iter=5, visited-state hashing, total-order tie-break) per v0.2 A4 + v0.3 B3+B9 — ✓
- Phase E: canonical assembly + split cache keys per v0.4 C10 + v0.5 D7 — ✓
- Phase F: pure verification, D22 enforced per v0.7 F1; evaluates D11.3'/D13/D17/D19 per v0.2 A9 + v0.5 D2+D6+D7 — ✓

## 6. Process amendments

- PROCESS-AMENDMENT (v0.4): LOCK deferred until C14 v0.1 sketch — WAIVED in path (c)
- D11 minimum C14 sketch scope (v0.5 + v0.6 E2 composability criteria) — DEFERRED to 90-day window
- D15 MVP-LOCK scope freeze (v0.5) — APPLIED
- E4 90-day fast-revision window (v0.6) — APPLIED
- F3 stabilization-only constraint (v0.7) — APPLIED

## 7. Open routed amendments NOT in this LOCK

- B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (routed C12 v1.1 from v0.2 A5; decoupled from C13 LOCK via B5 Protocol)
- B-C9-ROOM-DOOR-PREFERENCES (C9 extension for caller-supplied RoomDoorPreference; v0.4 Q8 standing)

Both are tracked in `04_backlog/`.

---

## AUDIT verdict: COMPLIANT

Every LOCKED contract traces to a source spec amendment. Reversals
documented. Schema fields enumerable. Algorithm phases bounded.
Process amendments applied or explicitly waived with reasoning.
No silent decisions detected.
