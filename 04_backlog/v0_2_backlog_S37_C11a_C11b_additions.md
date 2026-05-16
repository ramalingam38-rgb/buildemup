# Backlog additions — S37 close (C11a + C11b spec arcs)

**Authored at**: S37 close.
**Mirror of**: `04_backlog/v0_2_backlog.md` (canonical) — additions appended.
**Status**: filed per Rule 9.2.

---

## C11a v1.0 LOCKED — backlog items (10 new)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-A | C11a M7 grid-scale KB-driven set | W#1 Q11 | post-launch | XS |
| B-NEW-B | C11a cross-operator composition (v2) | W#1 Q3 | C11b stable + measured under-coverage | M |
| B-NEW-C | C11a abstract graph mutation operators (EvoArch-style) | W#1 Q14 | post-launch + B-238 review | L |
| B-NEW-D | C11a adaptive operator + slot scheduling | W#2 #6 + W#3 #2 | post-launch + measured yield-skew | M |
| B-NEW-E | C11a `FULL` verbosity provenance compaction | W#2 #9 | replay-snapshot size pressure | S |
| B-NEW-F | C11a QD-algorithm extension + semantic validity floor | W#2 #3,#12 + W#3 #12 | post-launch + B-238 review | L |
| B-NEW-G | C11a TopologySignature spatial expansion (circulation graph, axial depth, frontage refinement) | W#3 #4 | post-launch + measured signature collision rate | M |
| B-NEW-H | C11a `TopologyTransitionDescriptor` (richer family-transition lineage) | W#3 #9 | post-launch | S-M |
| B-NEW-I | C11a `BatchAllNonBaseFailedError` rolling failure-rate thresholds | W#3 #7 | observed alert noise | S |
| B-NEW-E2 | C11a Tier B incremental regen + cross-invocation cache | W#3 #1 deferred | post-launch + measured deep-mutation runtime pressure | L |
| B-NEW-M | C11a quantitative lineage extension | W#4 #6 | post-launch + measured emergent rate | M |
| B-NEW-N | C11a replay compatibility infrastructure | W#4 #8 | post-launch + first replay-snapshot incompat case | L |
| B-NEW-O | C11a `InvariantCapabilityRegistry` | W#4 #9 | invariant reference count > 30 | L |
| B-NEW-Q | C11a per-operator quarantine telemetry | W#4 #5 partial | post-launch operational | S |
| B-NEW-R | C11a `ComplexityScore` rubric (process tooling) | W#5 #4 | next major spec round | M |
| B-NEW-S | C5 amendment: TopologyFamilyDefinition split | W#5 #7 | post-launch + observed family-classification ambiguity | M |
| B-NEW-T | C11a `DeltaCauseDescriptor` causal lineage | W#5 #10 | post-launch + measured emergent ambiguity | M |
| B-NEW-U | C11a deterministic-parallel-semantics | W#5 #9 | scaling pressure | L |

---

## C11a upstream amendments (REQUIRED BEFORE C11a BUILD)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-NEW-J** | **C5 amendment: codify privacy zoning rule (bedrooms not on road-facing wall) as numbered invariant** | **W#3 #3** | **C11a v1 build** | **XS** |
| **B-NEW-K** | **C7 amendment: codify staircase clearance as W-numbered invariant** | **W#3 #3** | **C11a v1 build** | **XS** |
| **B-NEW-L** | **C8 amendment: codify entry-approach compatibility as numbered invariant** | **W#3 #3** | **C11a v1 build** | **XS** |
| **B-NEW-P** | **Upstream amendments: `severity_tier` ClassVar on every error class in C7/C9/C10** | **W#4 #10** | **C11a v1 build (also C11b v1 build)** | **XS** |

**WAIVER STATUS PER RAMALINGAM S37 GRANT**:
Per Ramalingam's S37 close confirmation, `UpstreamAmendmentWaiver`
tokens are GRANTED for B-NEW-J, B-NEW-K, B-NEW-L, B-NEW-P (4 waivers).

**Cap check**: C11a § 0.2 specifies max 3 active waivers at v1.0 LOCK time.
4 waivers would exceed the cap. Two of these (B-NEW-K, B-NEW-L) are
LOW-RISK because the inline checks they replace are well-defined in the
Walkthrough doc; the others (B-NEW-J, B-NEW-P) are MEDIUM-RISK.

**RECOMMENDATION FOR S38 CLAUDE**: at C11a build start, audit each
pending_upstream predicate. If 4 are still pending and Ramalingam's
intent was "all 4 waived to unblock", explicitly raise the cap to 4
in C11a as a PATCH amendment (small spec edit, not a full Walk #N).
Alternative: knock out B-NEW-K or B-NEW-L (XS effort each, ~30min) as
the first sub-task of S38, dropping pending count to 3 and respecting
the cap.

This sequencing decision should surface explicitly to Ramalingam at
S38 open.

---

## C11b v1.0 LOCKED — backlog items (8 new)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-NEW-V | C11b refinement scope expansion (door/window/furniture refinement) | v0.1 Q4 | post-launch + measured under-coverage | M |
| B-NEW-W | C11b hypervolume-based diversity metric | v0.1 Q5 | post-launch | M |
| B-NEW-X | C11b adaptive operator hyperparameters | future tuning needs | post-launch | M |
| B-NEW-Y | C11b cross-topology Pareto aggregation | v0.1 Q2 | C14 ranker observed insufficient | M |
| B-NEW-Z | C11b deterministic-parallel-NSGA-II | scaling pressure | post-launch | L |
| B-NEW-V2 | C11b per-room-category bound multipliers (KB-driven) | W#2 #3 | post-launch + KB support | M |
| B-NEW-V3 | C11b `objective_balance` output ordering | W#2 #7 | C14 normalization spec lands | S-M |
| B-NEW-V4 | C11b Dirichlet-based area partitioning for initialization | W#3 #2 | post-launch + measured Pareto-quality regression | M |
| B-NEW-V5 | Broader EA protocols (`DiversityMetricProtocol`, `SurvivorSelectionProtocol`) | W#3 #6 | alternate algorithm family becomes relevant | L |
| B-NEW-V6 | C11b cache memory budget LRU eviction policy | W#3 #8 | measured memory pressure | S-M |

---

## Cumulative S37 backlog summary

- **C11a additions**: 18 items (incl. 4 upstream amendments waived)
- **C11b additions**: 10 items
- **Total new at S37**: 28 items

**Existing items affected** (no new IDs):
- B-217 (polygonal envelopes) — affects C11a M9/M1/M2; affects C11b spatial assumptions
- B-220 (hydraulic primitives + plumbing-engineer review) — affects C11a M6 acceptance standard
- B-237 (cross-platform replay CI matrix + Decimal geometry) — required for C11a Inv 7 + C11b Inv 24 + EnvironmentFingerprint validation
- B-238 (independent architect review) — direct review target for C11a 9-operator catalog + C11b semantic caps + MAX_ROOM_ASPECT_RATIO

---

**End of S37 backlog additions.**
