# C12 — SPEC v0.4 PROPOSED — Walk #4 Amendments + LOCK Candidacy

**Component**: 12 (Multi-Floor Placement & Vertical Alignment Engine)

**Status**: v0.4 PROPOSED. **NOT LOCKED.** PENDING Ramalingam adjudication.

**Authority**: S43 Walk #4 external critique (18-item reviewer analysis). Reviewer's own final assessment: *"plausibly near LOCK territory for a deterministic v1 residential placement engine. The remaining risks are no longer 'missing-spec' risks."*

**Scope**: PATCH-NOW amendment set against v0.3 PROPOSED. **Two focused amendments** (Items 14, 15) + comprehensive backlog additions. Full v0.4 spec = v0.1 + v0.2 amendments + v0.3 amendments + this doc.

**Authored**: S43, post-Walk #4 critique.

---

## § 0.1 — Walk #4 verdict summary

| Item | Verdict | Section touched |
|------|---------|----------------|
| 1 (god-component) | DOCUMENTED | B-C12-COMPONENT-SPLIT-V2 (v0.2) |
| 2 (slicing bias) | DOCUMENTED + new backlog | B-C12-CSP-PLACEMENT + **B-C12-PLACEMENT-DIVERSITY-TELEMETRY** |
| 3 (circulation underpowered) | MISFRAMED | Generation is C8's job; C14 owns path quality |
| 4 (MFRA heuristic) | DOCUMENTED + new backlog | v0.2-A2 + **B-C12-MFRA-CONVERGENCE-TELEMETRY** |
| 5 (HARD/SOFT upstream) | PARTIAL — new backlog | C5 owns policy; C12 observes. **B-C12-ADJACENCY-COVERAGE-TELEMETRY** |
| 6 (rectangular-only) | DOCUMENTED + new backlog | B-C12-IRREGULAR-ENVELOPES (v0.1) + **B-C12-IRREGULAR-ENVELOPE-TELEMETRY** |
| 7 (doorway shallow) | PARTIAL — new backlog | Swing/clearance/direction → C13. Corner offset = **B-C12-DOORWAY-CORNER-OFFSET** |
| 8 (cache fragmentation) | DOCUMENTED + new backlog | v0.3-A6 + **B-C12-CACHE-DIFF-TOOLING** |
| 9 (provenance size) | VALID — new backlog | **B-C12-PROVENANCE-SPLIT** (parallels B-C11B-PROVENANCE-SPLIT) |
| 10 (determinism env-fragile) | DOCUMENTED + new backlog | v0.2-A4 + B-237 + **B-C12-DETERMINISTIC-KERNEL** |
| 11 (hidden policy engine) | VALID — new backlog | **B-C12-HEURISTIC-PROVENANCE** |
| 12 (MF floor-first) | DOCUMENTED | B-C12-COUPLED-MF-PLACEMENT (v0.2) |
| 13 (no space-quality opt) | MISFRAMED | C14 scoring scope |
| 14 (integration dep risk) | **VALID — v0.4 AMENDMENT A1** | Schema version probes at C12 ingress |
| 15 (room category fragility) | **VALID — v0.4 AMENDMENT A2** | Reviewer missed C9.RoomCategory enum exists; v0.4-A2 uses it + alias map for other_rooms |
| 16 (performance optimistic) | VALID — new backlog | **B-C12-PERFORMANCE-TELEMETRY** |
| 17 (test surface) | VALID — new backlog | Hypothesis already in project. **B-C12-PROPERTY-FUZZING** for build phase |
| 18 (long-term CSP) | DOCUMENTED | B-C12-CSP-PLACEMENT (v0.1) |

**Distribution: 2 v0.4 amendments / 10 new backlog / 6 DOCUMENTED-already-filed / 2 MISFRAMED / 2 PARTIAL (split).**

---

## § 0.2 — MISFRAMED-scope pushback

Two items asked C12 to absorb work that belongs elsewhere:

- **Item 3 (circulation generation)**: the reviewer's distinction "validation ≠ generation" is sharp, but circulation *generation* (corridor planning, path optimization) is C8's job — that's why we filed B-C8-CORRIDOR-ZONE-CONTRACT and shipped C8's `corridor_zones` derivation in S43. C12 reserves corridor zones (v0.2-A6) and verifies reachability. Path-length minimization heuristics and "doorway-to-doorway accessibility scoring" are C14 quality concerns, not C12 feasibility concerns.

- **Item 13 (space-quality optimization)**: residual-space metrics, compactness, experiential flow are C14 scoring. Local geometric improvement / post-placement nudging is a re-frame of Walk #2 Item 12 (MISFRAMED there too) — that would have C12 re-do C11b's NSGA-II work.

Partial-MISFRAMED on Items 5 and 7:

- **Item 5 (HARD/SOFT upstream)**: reviewer's "fallback heuristics when hints are sparse" would have C12 invent adjacency policy — exactly what v0.3-A3 pushed upstream to C5/KB. The diagnostics half ("adjacency-quality validation") is genuinely a C12 telemetry concern → new backlog.

- **Item 7 (doorway shallow)**: swing arcs, clearance, circulation direction are all C13 Door Placement scope (C13's whole reason for existing). The corner-proximity check ("door too close to wall corner is unusable") is a genuine C12 SharedEdge concern → new backlog.

---

## § 0.3 — Walk #4 PATCH-NOW amendments (2)

### Amendment v0.4-A1 — Schema version probes at C12 ingress (Item 14)

**Adds**: § 3 Phase 0 step 4 (schema-version probe).

**New text**:

```python
# C12 declares the expected upstream schema versions it was compiled against:
EXPECTED_C8_CORRIDOR_ZONE_SCHEMA_VERSION: Final[int] = 1
EXPECTED_C9_ADJACENCY_HINT_SCHEMA_VERSION: Final[int] = 1
EXPECTED_FLOOR_ROOM_BRIEF_SCHEMA_VERSION: Final[int] = 1

class UpstreamSchemaDriftError(LocalPlacementError):
    """Raised at Phase 0 when an upstream component's schema version
    differs from what C12 was built against. Prevents silent
    cross-component contract drift.

    Severity: systemic. Halts the batch."""

# In Phase 0 step 4:
#
# Assert that the schema version constants on the upstream amendment
# surfaces match C12's expected values:
#   - CorridorDesignedCandidate exposes CORRIDOR_ZONE_SCHEMA_VERSION
#     (added by the C8 amendment at LOCK time, currently absent at
#     v0.1 — see § 0.4 below for the routed amendment)
#   - FloorRoomBrief exposes ADJACENCY_HINT_SCHEMA_VERSION (same)
#
# If either upstream constant is absent OR doesn't match the expected
# value, raise UpstreamSchemaDriftError.
```

**Rationale**: when C8 or C9 amendments evolve post-v1 (e.g., volumetric corridor zones replace rectangular ones, or PREFERRED/AVOID adjacency kinds get added), C12 must detect the schema drift instead of silently consuming incompatible data. The probe is cheap (compile-time constant comparison) and catches the issue at the contract boundary, not deep inside placement logic.

**Cross-component dependency**: requires C8 and C9 to expose their schema version constants. Filed as routed amendments below (§ 0.4).

---

### Amendment v0.4-A2 — RoomCategory resolution with alias map (Item 15)

**Replaces**: v0.2-A9 doorway-feasibility room-category derivation + v0.3-A8 self-audit concern #3 resolution.

**Discovery from Walk #4 code grep**: `buildemup.components.c09.RoomCategory` enum **already exists** and is exported from C9's `__init__.py`. The reviewer's Item 15 partly missed this. Fragility is real only for `FloorRoomBrief.other_rooms: tuple[str, ...]` (open-ended user-provided strings).

**New text**:

```python
# C12 uses C9's existing RoomCategory enum for standard categories.
# For the open-ended other_rooms tuple, C12 applies a documented
# alias-map normalization at ingress:

from buildemup.components.c09 import RoomCategory

_OTHER_ROOMS_ALIAS_MAP: Final[dict[str, str]] = {
    "guest_bedroom": "guest_bedroom",
    "guest-bedroom": "guest_bedroom",
    "guest room": "guest_bedroom",
    "guestbedroom": "guest_bedroom",
    "GuestBedroom": "guest_bedroom",
    "study": "study",
    "study_room": "study",
    "study-room": "study",
    "balcony": "balcony",
    "store": "store",
    "storage": "store",
    "servant": "servant",
    "servant_quarter": "servant",
    # ... documented per C5 brief conventions
}

def _normalize_other_room_category(raw: str) -> str:
    """Canonicalize an other_rooms string via the alias map.

    Falls back to ``raw.strip().lower().replace(' ', '_').replace('-', '_')``
    for unknown values. Logs the unknown value for telemetry (per
    B-C12-PERFORMANCE-TELEMETRY).
    """
    if raw in _OTHER_ROOMS_ALIAS_MAP:
        return _OTHER_ROOMS_ALIAS_MAP[raw]
    return raw.strip().lower().replace(' ', '_').replace('-', '_')

def _doorway_minimum_for_pair(cat_a: str, cat_b: str) -> float:
    """NBC 2016 doorway minimum derivation for a shared-edge pair.

    Priority order (matches v0.2-A9):
      - main entrance → 1.00 m
      - bedroom (any subtype) → 0.90 m
      - bathroom / wc / toilet → 0.75 m
      - general fallback → 0.75 m
    """
    # ... uses RoomCategory enum + normalized other_rooms strings
```

**Spec change in § 2.2 PlacedRoom / SharedEdge** schema: `category` field on `PlacedRoom` is typed as `str` (the post-normalization canonical form), with documented values matching RoomCategory + alias-map outputs.

**Rationale**: the reviewer correctly identified that "guest_bedroom" / "guest-bedroom" / "guest room" / "GuestBedroom" can all leak in via `other_rooms`. The alias map captures the common variants explicitly; the fallback string normalization (lowercase, underscore-separated) handles unforeseen inputs deterministically. C12 emits a canonical string downstream, so C13/C14 don't have to redo this work.

**Open question Q-15 — wait, Q-15 doesn't exist; Item 15 is reviewer numbering.** No spec Q-question affected.

---

## § 0.4 — Routed upstream amendments (cross-component)

The schema-version probes in Amendment A1 require C8 and C9 to expose schema version constants. Two thin amendments:

### B-C8-SCHEMA-VERSION-CONSTANT (ROUTED to C8 maintainer)

**Scope**: add `CORRIDOR_ZONE_SCHEMA_VERSION: Final[int] = 1` constant to `buildemup.components.c08.schema`. Surface as part of the public `__all__`.

**Effort**: trivial (one line + export + test).

**Trigger**: before C12 v1 LOCK (i.e., this needs to ship alongside the C12 LOCK signal).

---

### B-C9-SCHEMA-VERSION-CONSTANT (ROUTED to C9 / domain maintainer)

**Scope**: add `ADJACENCY_HINT_SCHEMA_VERSION: Final[int] = 1` constant to `buildemup.domain.adjacency_hint`. Surface as part of the public `__all__`.

**Effort**: trivial (one line + export + test).

**Trigger**: before C12 v1 LOCK.

---

These two are small enough that I'll code them along with C12 v1 implementation (treat as part of the C12 build session) unless you direct otherwise.

---

## § 0.5 — New backlog items (10 + 2 routed)

Telemetry-heavy because the reviewer's verdict pattern was "the spec is structurally fine; add observability so we can tune it."

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| **B-C12-PLACEMENT-DIVERSITY-TELEMETRY** | Per-batch metric tracking the structural diversity of slicing-tree outputs (e.g., bisection-axis distribution, room-ordering entropy). Surfaces the "slicing-tree bias" the reviewer (Item 2) flagged. | Walk #4 Item 2 | After v1 ships; when production data shows N≥100 batches available for analysis | S |
| **B-C12-MFRA-CONVERGENCE-TELEMETRY** | Track retry success distribution: histogram of (retries-to-convergence) + (delta-progression per retry) across batches. Validates the monotonic-δ heuristic empirically. | Walk #4 Item 4 | After v1 ships with multi-floor production traffic | S |
| **B-C12-ADJACENCY-COVERAGE-TELEMETRY** | Per-batch metric: count of (HARD adjacency hints satisfied / total) and (SOFT hints satisfied / total). Surfaces upstream hint-quality issues without C12 making policy decisions. | Walk #4 Item 5 | When adjacency_hints population begins (currently empty default at v1) | S |
| **B-C12-IRREGULAR-ENVELOPE-TELEMETRY** | Track percentage of rejected plots due to rectangular-only envelope assumption. Accelerates B-C12-IRREGULAR-ENVELOPES trigger evaluation. | Walk #4 Item 6 | Day-1 of v1 production deployment | S |
| **B-C12-DOORWAY-CORNER-OFFSET** | Reject shared edges where the doorway would land within 0.15m of a room corner (NBC convention for door swing clearance). Currently SharedEdge.doorway_feasible only checks overlap length; corner proximity is a separate concern. | Walk #4 Item 7 (the genuine C12-scope half) | When first "unusable door near corner" production complaint surfaces OR if C13 reports >5% door-rejection rate on C12-flagged feasible edges | S |
| **B-C12-CACHE-DIFF-TOOLING** | Centralized cache-key diff diagnostics tooling: when two cache lookups should match but don't, surface which cache_relevant field differs. Parallels B-C11B-CACHE-TIERS. | Walk #4 Item 8 | When cache hit rate < 50% OR when first production cache-mismatch debug ticket | S-M |
| **B-C12-PROVENANCE-SPLIT** | Split PlacementProvenance into ReplayProvenance + OperationalTelemetry + DiagnosticWarnings. Parallels B-C11B-PROVENANCE-SPLIT (HIGH priority on C11b side; same trigger applies here). | Walk #4 Item 9 | Any c12_version MINOR/MAJOR bump | M |
| **B-C12-DETERMINISTIC-KERNEL** | Deterministic geometry-kernel abstraction layer: isolate FP-sensitive operations (overlap computation, area calculation, distance) behind a kernel interface that can be swapped to a deterministic-FP variant (e.g., rational arithmetic, fixed-point). | Walk #4 Item 10 | When cross-platform replay mismatch is observed AND B-237 CI matrix cannot rule out FP semantics | M-L |
| **B-C12-HEURISTIC-PROVENANCE** | Make placement heuristics traceable in provenance: record which heuristic decisions (slicing axis choice, room iteration order, tie-break paths) were taken, so downstream consumers can audit policy embedded in geometry. | Walk #4 Item 11 | When architectural-style configurability becomes a product requirement | M |
| **B-C12-PERFORMANCE-TELEMETRY** | Track actual room-count distributions + wallclock-per-candidate histograms; surface when production room counts exceed v1's n≤15 assumption. | Walk #4 Item 16 | Day-1 of v1 production deployment | S |
| **B-C12-PROPERTY-FUZZING** | Hypothesis-based property tests for placement invariants (Inv 1-13). Generate random room sets, envelopes, adjacency hints; assert invariants always hold. Hypothesis is already a project dependency (test_c11a_subsession5_stress_fuzz, test_c4_property_based). | Walk #4 Item 17 | During C12 v1 build phase (concurrent with example-based tests) | S |
| **B-DOMAIN-ROOM-CATEGORY-ENUM** | Cross-component canonical RoomCategory enum unifying all callers (currently lives in C9). v0.4-A2 alias map is a C12-local mitigation; the long-term fix is to canonicalize at the domain layer so other_rooms strings get enum-typed at brief-construction time (C5/C9). | Walk #4 Item 15 (the unsolved half) | When room-category drift causes a cross-component bug OR when KB rules begin consuming room types | M |

Plus 2 routed upstream amendments (§ 0.4 above):

| ID | Description | Trigger |
|---|---|---|
| B-C8-SCHEMA-VERSION-CONSTANT (ROUTED) | Add `CORRIDOR_ZONE_SCHEMA_VERSION = 1` to C8 schema | Before C12 v1 LOCK |
| B-C9-SCHEMA-VERSION-CONSTANT (ROUTED) | Add `ADJACENCY_HINT_SCHEMA_VERSION = 1` to domain adjacency_hint | Before C12 v1 LOCK |

**Total new items: 12 (10 C12-local + 1 domain-layer + 2 routed thin amendments).**

---

## § 0.6 — Self-audit on v0.4 (Rule 11)

1. **No new self-audit concerns surfaced.** v0.4 amendments are surgical; both have small implementation surface (UpstreamSchemaDriftError is one new class + Phase 0 step 4; RoomCategory resolution is one helper function + an alias map).

2. **Backlog growth is meaningful but acknowledged.** v0.4 takes backlog from 18 → 30 items. That's a real signal that C12 has accreted post-v1 work. The reviewer's final assessment frames this correctly: "remaining risks are no longer 'missing-spec' risks. They are now primarily: scalability risks, architectural-quality risks, heuristic-quality risks, long-term maintainability risks." Backlog growth is the right place for those — they're real, they have triggers, they're tracked.

3. **Cross-component dependency surface is now 5 contracts** (CorridorDesignedCandidate, FloorRoomBrief, RoomCategory, NBC 2016 doorway minima, env fingerprint pattern). v0.4-A1 schema probes catch drift at the contract boundary. B-C12-INTEGRATION-AMENDMENT-COVERAGE remains the integration-test commitment for v1 build.

4. **Web research check**: property-based testing for invariant-heavy systems verified as standard practice (Hypothesis literature, Nelhage 2017, MacIver). Hypothesis already in project. v0.4 backlog item B-C12-PROPERTY-FUZZING leverages existing tooling.

5. **LOCK candidacy**: v0.4 closes the two reviewer-flagged spec-deltas (Items 14, 15) and resolves all 4 of v0.2's self-audit concerns (now closed across v0.2 + v0.3 + v0.4). Zero CRITICAL items open. Zero functional bugs identified across 4 walks.

---

## § 0.7 — Updated complexity budget

| Subsystem | v0.1 | v0.2 | v0.3 | v0.4 |
|---|---|---|---|---|
| Public types | 6 | 6 | 6 | 6 |
| Failure types | 9 | 10 | 10 | 11 (+ UpstreamSchemaDriftError) |
| Configuration fields | 10 | 9 | 9 | 9 |
| Invariants | 10 | 13 | 13 | 13 |
| Sub-phases | 5 | 6 | 6 | 6 (+ step 4 in Phase 0) |
| Open questions | 12 | 7 | 1 | 1 |
| Backlog items | 11 | 18 | 18 | 30 |

**Weighted complexity** (per B-C11B-COMPLEXITY-BUDGET-V2 metric):
- Invariants: 13 × 1 = 13
- Failure types: 11 × 2 = 22
- Replay: 2 × 3 = 6
- Telemetry: 5 × 0.5 = 2.5

**Total: 43.5.** Up from v0.3's 41.5; well under the 100 split-trigger. **C12 v0.4 is comfortably inside the complexity envelope.**

---

## § 0.8 — LOCK candidacy assessment

**v0.4 IS a LOCK candidate.** Cumulative criteria check:

| Criterion | Status |
|---|---|
| All HIGH/CRITICAL reviewer items addressed | ✅ (v0.2 closed Items 1, 2, 9; v0.4 closed Items 14, 15) |
| All self-audit concerns resolved or backlogged | ✅ (v0.2 audit closed across v0.2 + v0.3 + v0.4) |
| Cross-component dependencies coded + tested | ✅ (S43: C8 + C9 amendments shipped, 3059 tests green) |
| Open questions resolved or backlog-only | ✅ (11 of 12 resolved; Q-6 is backlog-only) |
| Complexity budget within envelope | ✅ (43.5 vs 100 trigger) |
| Web-research verification on factual claims | ✅ (NBC 2016 doorway minima v0.2; PBT literature v0.4) |
| Reviewer's own LOCK-candidacy verdict | ✅ ("plausibly near LOCK territory") |

**Remaining gates before LOCK**:

1. **Your explicit LOCK signal** ("lock it" / "v0.4 LOCKED").
2. **Or one final walk if desired** — Walk #5 by another external reviewer, or self-walk on the new backlog items.

**Post-LOCK plan (S44+ build session)**:

- Code the 2 routed thin amendments (C8 + C9 schema version constants) first — trivial, 2 lines + 2 tests each.
- Build C12 v1 implementation: ~25 production files mirroring C11b structure, target ~150 tests (including 5-10 property-based tests per B-C12-PROPERTY-FUZZING).
- Run integration suite covering the C8/C9 amendment composition (B-C12-INTEGRATION-AMENDMENT-COVERAGE).
- Target: 3059 baseline → ~3210 (3059 + ~150 C12 + 2 + 2 = ~3213).
- Estimated effort: 2 sessions (S44 + S45 + buffer) — comparable to C11b S42's single-session build given C12's larger surface and integration-test commitment.

---

**End of C12 SPEC v0.4 PROPOSED — Walk #4 amendment doc + LOCK candidacy.**

**Status reminder**: PENDING Ramalingam LOCK adjudication per Rule 8. v0.4 is the most plausible LOCK target across all 4 walks. Three explicit paths from here:

1. **"Lock C12 v0.4 and code"** — proceed to S44 build session.
2. **"Walk #5 first"** — one more external (or self-) walk for completeness before LOCK.
3. **"Patch X first then LOCK"** — surgical patch on any specific concern (e.g., wanting B-C12-PROPERTY-FUZZING upgraded from backlog to v0.4-A3).

My recommendation: **(1)**. Reviewer's own framing and the verdict distribution support direct LOCK. Property-based testing during build is the right time to add it (concurrent with example-based tests during S44 implementation), not pre-LOCK.
