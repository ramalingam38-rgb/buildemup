# spec_C15_v0_1_PROPOSED.md

**Component 15 — Layout Problem Finder**
**Status:** v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.
**Authored:** S46 (post-C14 v0.2 LOCK)
**Authority chain:** v0.1 PROPOSED → critique walks → v1.0 LOCK
**Lineage:**
- BuildemUp_Component_Validation_Report.md (April 2026): Locked Decision #1 — "Layout Problem Finder" replaces "Lived Quality Scorer"
- C14 v0.2 LOCKED: "severity escalation belongs to C15" (A10)
- Academic grounding: van Hoogdalem & van der Voordt 1985-1998 (criterion-by-criterion comparative analysis); Mostafavi et al. SAGE 2025 (hybrid quantitative + qualitative); Center for Health Design POE Audit Tool methodology; POE literature 30+ years

---

## § 0 — Meta + scope boundary

### § 0.0 — IMPORTANT: C15 is heuristic problem-finding, not lived-experience truth

C15 produces a structured list of architectural concerns drawn from established residential-design checklists (POE literature, Neufert/Ching standards, NBC compliance, Indian residential conventions). Those concerns are heuristic signals. They DO NOT capture:

- Individual family preferences or lifestyles
- Cultural variations beyond C15's declared scope (§ 0.3)
- Long-term lifestyle evolution (children growing up, elder care)
- Aesthetic preferences (warm vs minimalist, traditional vs modern)
- Climate-specific micro-preferences
- Social meaning of spaces (the room where a grandmother chooses to sit)
- Future flexibility for unanticipated changes
- Acoustic, olfactory, tactile, or other non-visual dimensions of habitation

A layout flagged with many concerns may still be a great fit for one family; a layout flagged with zero concerns may still feel wrong to another family. Concerns are **inputs to a family's decision**, not **the decision itself**.

C15 produces a problem LIST, never a SCORE. This is a moat decision (per Validation Report Locked Decision #1) and is enforced as Inv P0 below.

### § 0.1 — What C15 IS

C15 ingests, per candidate:
- C12 PlacedCandidate (geometry: room positions, dimensions, envelope, shared edges)
- C13 SuccessfulDoorPlacement (doors + advisory flags)
- C14 SuccessfulCirculationAnalysis (circulation graph + structural/preference flags)

…and produces:
- ProblemReport — a structured list of ProblemCheck records, each carrying:
  - Stable check_id (P{dimension}.{check_index})
  - Status (pass / warn / fail / not_applicable)
  - Severity (critical / important / nice_to_have)
  - Affected room_ids
  - Rule citation (NBC clause, Neufert standard, or design heuristic source)
  - Why-it-matters explanation (1-2 sentence consumer-readable text)
  - Optional suggested-mitigation hint

C15 organizes ~35 checks across 10 dimensions (§ 1.4). Each dimension covers one aspect of residential lived quality validated by published architectural research.

### § 0.2 — What C15 IS NOT

Tight boundary. C15 does NOT:

- Produce a single quality score user-facing (Inv P0)
- Rank candidates against each other (that's C17 ranker)
- Modify the layout (read-only consumer)
- Re-verify C13 invariants (D11.1, D13, D17 — those are HARD; C15 trusts prior verification)
- Re-compute C14 graph metrics (passes through C14's report)
- Optimize, backtrack, or suggest layout mutations (suggestions are textual hints in the check record, not actionable mutations)
- Compute construction cost (that's C17 cost-aware ranking + cost telemetry, separate concern)
- Verify NBC compliance as a binary gate (NBC compliance IS a check dimension, but failing a check produces a problem record, not a layout rejection)
- Render drawings (that's C18)
- Run any externally-facing evaluation (C15 is internal; consumer-facing UX consumes the ProblemReport)

If a future change tries to add a user-facing score or layout-modification capability to C15, the spec walk must FIRST route the responsibility elsewhere (cost → C17, mutation → upstream operator, score → never).

### § 0.3 — Cultural context declaration (product scope)

BuildemUp's product scope per project mission: decision-support engine for Indian families building their own homes. C15 v1 ships with checks calibrated for **Indian middle-class residential construction context**. Specifically:

- NBC India 2016 + IS 456 + IS 962 + IS 11268 + TNCDBR (Tamil Nadu) compliance references
- Indian residential conventions: separate kitchen + dining, dedicated pooja room, multigenerational living, sit-down floor seating compatibility, monsoon-aware ventilation patterns
- Indian middle-class budget calibration (2-5 BHK, 600-2400 sqft typical)
- NOT calibrated for: studios, co-living, hostels, Western open-plan apartments, commercial conversions, non-Indian residential conventions

This is product scope, not architectural flaw. Future regional expansion (Western/SE-Asian/Japanese contexts) would be a v2+ component variant, not a v1 amendment. Filed: **B-PROJECT-LEGALITY-LAYERING** (carried over from C14 v0.2 backlog).

### § 0.4 — Data envelope declaration

A key v0.1 honesty discipline: C15's check coverage depends on UPSTREAM data availability. The current pipeline (C12 + C13 + C14) provides geometry + doors + circulation graph. It does NOT provide:

- Window placement (needed for natural-light checks)
- Furniture / fixture placement (needed for storage, multi-functional, furniture-fit checks)
- Vertical envelope detail (needed for first-floor-living checks beyond floor metadata)
- Climate / orientation data (needed for ventilation and solar-gain checks)
- Construction-tier specification (needed for cost-aware checks)

v0.1 spec defines the FULL output schema (all 10 dimensions, all ~35 checks). But the v1 IMPLEMENTATION coverage will be PARTIAL — only checks whose data dependencies are met by current C12+C13+C14 outputs will produce non-`not_applicable` results. Other checks emit `status=not_applicable` with a structured reason indicating the missing data dependency.

This is honest. v1 ships partial; future upstream extensions activate the remaining checks. No silent failures.

### § 0.5 — Moat-preservation contract

**Inv P0** (declared here, enforced throughout the spec): C15 NEVER exposes a single layout-quality score to any consumer outside the C15 module itself.

Internal implementation MAY compute aggregate scores for C17 ranker (e.g., weighted sum of check severities for NSGA-II input). Such internal scores live in a SEPARATE return value (`RankerHint`), are clearly labeled as ranker-internal, and are flagged `is_ranker_internal=True`. They MUST NOT be surfaced by the UX, MUST NOT be persisted in user-facing logs, and MUST NOT be returned by any public API except the dedicated `analyze_with_ranker_hint()` entry.

The public `analyze_problems()` entry returns the ProblemReport only. No single number. This is the moat per Locked Decision #1.

### § 0.6 — Dependency direction

```
C12 → C13 → C14 → C15 → C17 (ranker, consumes ProblemReport + RankerHint)
                  ↘
                  C18 (renderer, consumes ProblemReport for annotation overlays)
```

C15 has READ access to C12 PlacedCandidate, C13 SuccessfulDoorPlacement, and C14 SuccessfulCirculationAnalysis. C15 does NOT modify any of these. C15 has NO read access to C11/below.

### § 0.7 — Cache scope

C15 cache key composes:
- `c14_full_cache_key` (input cache key from C14)
- `C15_VERSION`
- `C15_CHECK_REGISTRY_VERSION` (bumped when check semantics change, even if the check set doesn't grow)

C15 is NEW at v2.0 per the v0.4-C7 pipeline convention. It ships with **typestate**: `SuccessfulProblemAnalysis` / `FailedProblemAnalysis`. Same pattern C13 / C14 ship.

---

## § 1 — Schema (consumed + produced)

### § 1.1 — Input: what C15 reads

C15 consumes a triple `(c12_candidate, c13_placement, c14_report)` per layout, plus shared metadata:

```python
# C12 input (read-only, geometry):
PlacedCandidate:
  - source_refined_candidate_signature: str
  - placed_rooms: tuple[PlacedRoom, ...]
  - shared_edges: tuple[SharedEdge, ...]
  - envelope_width_m / envelope_depth_m
  - placement_algorithm

# C13 input (read-only, doors + advisories):
SuccessfulDoorPlacement:
  - doors: tuple[Door, ...]
  - advisory_flags: tuple[AdvisoryFlag, ...]
  - geometric_fidelity (APPROXIMATE at v1)
  - cache_keys

# C14 input (read-only, circulation graph + flags):
SuccessfulCirculationAnalysis:
  - report: CirculationGraphReport (full graph + metrics + structural + preference flags)
  - cache_keys

# Threaded metadata (from upstream orchestration, mirroring C13/C14):
  - placed_room_ids: tuple[str, ...]
  - room_categories: dict[str, str]
  - main_entry_room_id: str
  - floor_metadata: dict[str, FloorInfo]  # NEW for C15 — see § 0.4
  - cultural_profile: CulturalProfile      # NEW for C15 — Indian default
```

Inv P5: every input is treated as read-only. Mutation of any input object is a hard error at C15.

### § 1.2 — Output: ProblemReport

```python
@dataclass(frozen=True)
class ProblemReport:
    """Per-candidate problem-finding output.

    NEVER carries a single quality score (Inv P0). The `checks` tuple
    is the deliverable. RankerHint is a separate, opt-in return type
    exposed only via the `analyze_with_ranker_hint()` entry point.
    """
    source_placed_candidate_signature: str

    # ── The deliverable ────────────────────────────────────────
    checks: tuple[ProblemCheck, ...]
        # All ~35 checks. Sorted lex-ASC by check_id (Inv P3).

    # ── Dimension summaries (counts only — NO scores) ──────────
    dimension_summary: tuple[DimensionSummary, ...]
        # Per dimension: (dimension_id, n_pass, n_warn, n_fail, n_na)
        # No weighted score, no aggregate. Counts only.

    # ── Aggregated upstream flag passthrough ───────────────────
    c13_advisory_flags: tuple[AdvisoryFlag, ...]    # byte-identical to C13
    c14_structural_flags: tuple[CirculationFlag, ...]  # byte-identical to C14
    c14_preference_flags: tuple[CirculationFlag, ...]  # byte-identical to C14

    # ── Provenance ─────────────────────────────────────────────
    c15_version: str
    c15_check_registry_version: int
    advisory_schema_version: int                      # from C13 chain
    upstream_cache_key: str                           # C14 full cache key
```

### § 1.3 — ProblemCheck record

```python
class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"   # data dependency missing

class CheckSeverity(StrEnum):
    CRITICAL = "critical"     # safety, NBC compliance, structural — failing is non-negotiable
    IMPORTANT = "important"   # significant lived-quality concern — most users will care
    NICE_TO_HAVE = "nice_to_have"  # preference / optimization — depends on user priorities

@dataclass(frozen=True)
class ProblemCheck:
    check_id: str                      # stable ID, e.g., "P2.3" (§ 1.5)
    dimension_id: int                  # 1..10
    status: CheckStatus
    severity: CheckSeverity
    affected_room_ids: tuple[str, ...] # sorted lex-ASC
    rule_citation: str                 # NBC clause / Neufert page / design heuristic source
    why_it_matters: str                # 1-2 sentence consumer text
    suggested_mitigation: str | None   # optional textual hint
    measurement: dict[str, float | int | str] | None
        # Optional structured measurement (e.g., {"shower_length_m": 0.85})
        # for debugging / UX detail rendering
    na_reason: str | None              # populated iff status == NOT_APPLICABLE,
                                        # explains which data dependency was missing
```

Frozen dataclass. Hashable. Replay-stable (Inv P2).

### § 1.4 — The 10 dimensions

Per Validation Report Locked Decision #1, the 10 dimensions of residential lived quality (validated by 9 sources in the project's prior research) are:

| ID | Dimension | Primary academic source | Data dependency status at v1 |
|----|-----------|-------------------------|-------------------------------|
| 1 | No wasted space | Neufert; FAR analysis literature | RUNNABLE (C12 geometry) |
| 2 | Room sizes match function | Neufert; Ching "Architecture: Form, Space, Order" | RUNNABLE (C12 geometry + room_categories) |
| 3 | Logical flow | Hillier 1984/1987; van Hoogdalem 1985 | RUNNABLE (C14 graph) |
| 4 | Natural light | Reinhart 2014 daylighting; LEED IEQc8 | PARTIAL — requires window placement (B-C15-WINDOW-DATA) |
| 5 | Privacy | Altman 1975; Hillier 1984 privacy gradient | RUNNABLE (C14 graph + room_categories) |
| 6 | No bottlenecks | Hillier 1984 betweenness; circulation engineering | RUNNABLE (C14 graph) |
| 7 | First-floor living | Lifetime Homes Standard (UK); accessibility lit | PARTIAL — requires floor_metadata |
| 8 | Outdoor connection | Biophilic design (Kellert 2008); residential POE | PARTIAL — requires window placement + envelope orientation |
| 9 | Storage | Neufert; Ching; Indian residential POE | NOT-RUNNABLE — requires furniture/fixture placement |
| 10 | Multi-functional | Adaptive housing lit (Brand 1994 "How Buildings Learn") | NOT-RUNNABLE — requires furniture-fit data |

Of 10 dimensions: **5 fully runnable at v1**, **3 partial (some checks runnable)**, **2 not runnable** (all checks emit `status=NOT_APPLICABLE` with structured na_reason).

This is the honest data envelope. v1 ships transparent partial coverage. Future upstream extensions (window placement engine, furniture-fit engine) unlock the remaining dimensions WITHOUT changing C15's check schema.

### § 1.5 — Check ID system

Stable IDs: `P{dimension_id}.{check_index_within_dimension}`.

- Dimension 1 has checks P1.1, P1.2, P1.3, P1.4
- Dimension 2 has checks P2.1, P2.2, P2.3, P2.4, P2.5
- ... etc.

Numbering rules (P-invariant prefix in § 2):
- Once assigned, a check_id NEVER changes meaning.
- Deprecated checks retain their ID with `status=DEPRECATED` (not in v0.1 enum but reserved).
- New checks get new IDs at the END of their dimension's sequence.
- Cross-dimension renumbering FORBIDDEN.

This makes UX, regression tests, and downstream consumers stable across C15 versions.

#### Sample check IDs per dimension (illustrative, not exhaustive — v0.1 SKETCH only locks the SHAPE)

**Dimension 1 — No wasted space:**
- P1.1: Corridor area as fraction of total carpet area (NBC ≤ 12%)
- P1.2: Dead-corner detection (L-corners < 1.5 m² with no functional assignment)
- P1.3: Aspect-ratio sanity (rooms with extreme width:depth > 3:1)
- P1.4: Built-up-to-FAR utilization (over- or under-utilization of allowed FAR)

**Dimension 2 — Room sizes match function:**
- P2.1: Bedroom min area (master ≥ 12 m², standard ≥ 9 m² per Neufert)
- P2.2: Kitchen counter-length adequacy (depends on appliances; v1 uses width proxy)
- P2.3: Bathroom shower length adequacy (≥ 1.07 m wall-mounted, per Indian residential POE)
- P2.4: Living room min area for family size (3-4 BHK ≥ 18 m²)
- P2.5: Dining seating clearance (≥ 0.9 m around table; v1 uses room width proxy)

**Dimension 3 — Logical flow:**
- P3.1: Step-depth from main_entry to bedrooms ≤ 3 (consumes C14)
- P3.2: Public-to-private depth monotonicity (consumes C14 preference flags)
- P3.3: Kitchen-to-dining adjacency (direct or single-corridor mediated)
- P3.4: Pooja room access from public zone (cultural — Indian context)

**Dimension 4 — Natural light:**
- P4.1: Window per habitable room (NBC requires; v1 NOT_APPLICABLE pending window data)
- P4.2: Window-to-floor-area ratio per room (LEED IEQ; NOT_APPLICABLE)
- P4.3: Cross-ventilation availability per room (NOT_APPLICABLE)
- P4.4: North-facing window for habitable rooms in hot climates (NOT_APPLICABLE)

**Dimension 5 — Privacy:**
- P5.1: Bedroom not on direct sight-line from main_entry (consumes C13 + C14)
- P5.2: Master bedroom step-depth ≥ 3 (Hillier-style privacy gradient)
- P5.3: Bathroom-bedroom direct adjacency (some users prefer, some don't — preference)
- P5.4: Pooja room visual privacy from non-family circulation
- P5.5: Sleeping vs entertainment zone separation (multigen consideration)

**Dimension 6 — No bottlenecks:**
- P6.1: Single-room betweenness concentration (consumes C14 BOTTLENECK_CONCENTRATION flag)
- P6.2: Corridor width ≥ 0.9 m at every segment (NBC)
- P6.3: Doorway clear-width ≥ 0.75 m (NBC; mostly enforced at C13, redundancy check)
- P6.4: Emergency egress path length (consumes C13 + envelope)

**Dimension 7 — First-floor living:**
- P7.1: At least one bedroom on ground floor (Lifetime Homes; PARTIAL — needs floor metadata)
- P7.2: At least one toilet on ground floor (PARTIAL)
- P7.3: Living + kitchen on ground floor (PARTIAL)
- P7.4: Step-free entry from outside (PARTIAL — needs envelope detail)

**Dimension 8 — Outdoor connection:**
- P8.1: Habitable room with direct outdoor view (PARTIAL — needs window data)
- P8.2: Balcony / terrace adjacency to living (NOT_APPLICABLE at v1)
- P8.3: Garden / courtyard visibility from public zone (NOT_APPLICABLE)
- P8.4: Outdoor drying space (Indian residential POE; NOT_APPLICABLE)

**Dimension 9 — Storage:**
- P9.1: Built-in wardrobe per bedroom (NOT_APPLICABLE — furniture data)
- P9.2: Kitchen overhead + base storage (NOT_APPLICABLE)
- P9.3: Common-area storage (closet near entry, foyer storage) (NOT_APPLICABLE)
- P9.4: Outdoor / utility storage (NOT_APPLICABLE)

**Dimension 10 — Multi-functional:**
- P10.1: Living room flexibility (movable furniture; floor space ratio) (NOT_APPLICABLE)
- P10.2: Bedroom dual-use (study + sleep) feasibility (NOT_APPLICABLE)
- P10.3: Convertible spaces (dining ↔ home office) (NOT_APPLICABLE)

**Total: 41 sample check IDs across 10 dimensions.** v0.1 spec commits to the SHAPE; exact rules + thresholds + measurement formulas are refined across critique walks toward v1.0 LOCK.

Estimate at v1: ~20 RUNNABLE checks, ~6 PARTIAL, ~15 NOT_APPLICABLE (waiting on upstream extensions). That's an honest v1 baseline.

---

## § 2 — Invariants (P-prefix)

C15 invariants use prefix **P** (for "Problem Finder") to distinguish from C13's D and C14's E.

| ID | Description |
|---|---|
| P0 | **MOAT PRESERVATION.** Public `analyze_problems()` API NEVER returns a single layout-quality score. Internal RankerHint is exposed only via the dedicated `analyze_with_ranker_hint()` entry, clearly labeled, and not user-facing. |
| P1 | Every input SuccessfulCirculationAnalysis produces exactly one ProblemReport (or one FailedProblemAnalysis). |
| P2 | **Byte-equal replay determinism.** Same input triple → identical ProblemReport. Check evaluation order is fixed (lex-ASC by check_id). |
| P3 | `ProblemReport.checks` sorted lex-ASC by `check_id`. |
| P4 | Every emitted `ProblemCheck.check_id` belongs to the registered check set for the current `C15_CHECK_REGISTRY_VERSION`. No ad-hoc checks. |
| P5 | **Read-only consumer.** No mutation of any input object (C12 / C13 / C14). |
| P6 | `status == NOT_APPLICABLE` always carries a populated `na_reason`. |
| P7 | `affected_room_ids` always a subset of input `placed_room_ids` and sorted lex-ASC. |
| P8 | `severity` is determined by C15's severity-rule table (§ 5.2), not by the check itself. C15 owns severity (per C14 v0.2 A10 deferral). |
| P9 | `dimension_summary` counts agree with `checks` breakdown by dimension. |
| P10 | Upstream advisory passthroughs (`c13_advisory_flags`, `c14_structural_flags`, `c14_preference_flags`) byte-identical to inputs. C15 does NOT mutate upstream signals. |
| P11 | **No invariant re-verification.** C15 does NOT re-check Inv D11.1, D13, D17, E3, etc. If they passed upstream, C15 trusts them. |
| P12 | **Check density bound.** `len(checks) == |registered_checks_for_version|` exactly. Every registered check produces exactly one ProblemCheck (even if NOT_APPLICABLE). No silent omissions. |
| P13 | **Cultural-context awareness.** Checks tagged as culturally-loaded (e.g., P3.4 pooja access, P5.4 pooja privacy) emit `status=NOT_APPLICABLE` with reason="cultural_profile_mismatch" when the input cultural_profile doesn't match the check's declared scope. |
| P14 | **Cache-key composability.** `upstream_cache_key == c14_input.cache_keys.full_cache_key`. ProblemReport cache key changes iff C14 output changes OR C15 version/registry changes. |
| P15 | **Severity-rule stability.** The severity assigned to a given (check_id, status) pair is deterministic and version-stamped. Changes require `C15_CHECK_REGISTRY_VERSION` bump. |
| P16 | **Provenance triple stability.** `(c15_version, c15_check_registry_version, advisory_schema_version)` all populated, non-empty/non-negative, and consistent with upstream chain. |

---

## § 3 — Phases

C15's algorithmic structure: a sequential pass through the check registry. No iteration, no backtracking, no optimization.

### Phase π — Ingress + metadata resolution
- Receive (c12_candidate, c13_placement, c14_report, metadata).
- Resolve effective `cultural_profile` (default: indian_middle_class).
- Validate input typestate (SuccessfulDoorPlacement + SuccessfulCirculationAnalysis required; failed inputs → C15 produces FailedProblemAnalysis early).

### Phase ρ — Check registry traversal
- Iterate registered checks in lex-ASC check_id order (Inv P2 + P12).
- For each check: resolve its data dependency, compute status, populate ProblemCheck record.
- A check that lacks its data dependency emits `status=NOT_APPLICABLE` with `na_reason` per Inv P6.

### Phase σ — Severity assignment
- For each ProblemCheck, look up severity from the severity-rule table (§ 5.2) based on (check_id, status, cultural_profile).
- Severity is deterministic per Inv P8 + P15.

### Phase τ — Dimension summary aggregation
- For each dimension 1..10: count checks by status (pass/warn/fail/na).
- Populate `dimension_summary` tuple.

### Phase υ — Upstream passthrough
- Copy `c13_advisory_flags` byte-identically.
- Copy `c14_structural_flags`, `c14_preference_flags` byte-identically.
- Inv P10 enforced.

### Phase φ — Report assembly + (optional) RankerHint generation
- Build ProblemReport with canonical sorts (Inv P3).
- Stamp provenance triple (Inv P16).
- If called via `analyze_with_ranker_hint()`: ALSO build RankerHint with internal aggregate (severity-weighted sum). Otherwise: RankerHint is NOT computed (zero-overhead default).

---

## § 4 — Errors

C15 error hierarchy mirrors C13/C14 two-tier:

- `ProblemAnalysisError` — base
- `LocalProblemError` — always halts
  - `UpstreamSchemaDriftError` — C12/C13/C14 input shape mismatch
  - `C15ConfigurationError` — bad config
  - `CheckRegistryError` — registry inconsistency at module load
- `PerCandidateProblemError` — strict-mode raise OR WARN-mode collect
  - `MissingMetadataError` — required threaded metadata absent (e.g., room_categories empty)
  - `InconsistentInputError` — C12/C13/C14 outputs disagree on room set (defensive)

No NBC-style vetoes at C15 — checks emit problem records, not exceptions.

---

## § 5 — Failure modes + severity rules

### § 5.1 — Strict vs WARN dispatch (same pattern as C13/C14)

- `strict_mode=True` → PerCandidateProblemError raises immediately.
- `strict_mode=False` (WARN) → caught, packaged into FailedProblemAnalysis, batch continues.
- LocalProblemError always halts.

Typestate output: `SuccessfulProblemAnalysis` carries ProblemReport; `FailedProblemAnalysis` carries FailureRecord + optional partial report.

### § 5.2 — Severity-rule table

Per Inv P8 + P15: C15 owns severity assignment. Severity is determined by (check_id, status, cultural_profile) per a stable rule table.

v0.1 SKETCH locks the SHAPE of the rule table; specific rules per check are refined across walks.

```python
# Sketch — refined by critique walks
SEVERITY_RULES_V1: Final[dict[str, dict[CheckStatus, CheckSeverity]]] = {
    # P1.1 (corridor area %) — exceeding NBC limit is IMPORTANT
    "P1.1": {
        CheckStatus.FAIL: CheckSeverity.IMPORTANT,
        CheckStatus.WARN: CheckSeverity.NICE_TO_HAVE,
        ...
    },
    # P2.1 (bedroom min area) — below NBC is CRITICAL (safety/regulatory)
    "P2.1": {
        CheckStatus.FAIL: CheckSeverity.CRITICAL,
        CheckStatus.WARN: CheckSeverity.IMPORTANT,
        ...
    },
    # P5.2 (master bedroom privacy depth) — preference; nice_to_have at worst
    "P5.2": {
        CheckStatus.FAIL: CheckSeverity.NICE_TO_HAVE,
        ...
    },
    # ... etc
}
```

Severity rules locked at v1.0 LOCK. Changes between v1.0 and any v2.0 require `C15_CHECK_REGISTRY_VERSION` bump per Inv P15.

Filed: **B-C15-SEVERITY-RULE-TABLE-LOCK** (v1.0-LOCK-MANDATORY, M effort).

---

## § 6 — Performance budget

Per-candidate: ≤ 1.5s for ~40 checks. Each check is O(k) at worst (k = room count). Total per-candidate: O(n × k) where n = check count.

Per-batch (50 candidates): ≤ 15s wallclock total at default config.

Configurable via `ProblemFinderConfig.per_candidate_wallclock_seconds`.

---

## § 7 — Testing strategy

Mirroring the C13/C14 pattern:

- **Foundational layer**: dataclass validation, schema canonical sorts, frozen/hashable, severity-rule lookups, check-ID uniqueness. Target: 50 tests.
- **Per-dimension units**: one test file per dimension, exercising every check at every status. Target: ~100 tests (10 dimensions × ~10 tests).
- **Orchestrator + provenance**: end-to-end + WARN/STRICT + version threading. Target: 25 tests.
- **Moat enforcement**: Inv P0 — verify no public path returns a score; verify RankerHint is opt-in only. Target: 8 tests.
- **PBT**: ≥20 PBTs covering P1-P16 invariants + adversarial generators (empty room set, all-NA case, all-PASS case, all-FAIL case).
- **Adversarial integration corpus**: pipe REAL C12 → C13 → C14 → C15 for the 7 scenarios from C13's corpus. Target: 11 tests.

Total target: **≥ 214 tests** at v1.0 LOCK.

---

## § 8 — Cache keys

```python
@dataclass(frozen=True)
class C15CacheKeys:
    c14_full_cache_key: str           # passthrough
    check_registry_cache_key: str     # hash(c14_full + C15_VERSION
                                      #       + C15_CHECK_REGISTRY_VERSION
                                      #       + cultural_profile_id
                                      #       + severity_rule_table_hash)
    full_cache_key: str               # same as check_registry_cache_key at v0.1
```

Per Inv P14 + C14 v0.2 cache discipline: any C14 cache change propagates; any C15 registry change bumps registry key. Cache-key compatibility tests run at LOCK.

---

## § 9 — Telemetry

Three event types proposed at v0.1:

```python
@dataclass(frozen=True)
class CheckEvaluatedEvent:
    candidate_signature: str
    check_id: str
    status: CheckStatus
    severity: CheckSeverity
    wallclock_seconds: float

@dataclass(frozen=True)
class DimensionSummaryEvent:
    candidate_signature: str
    dimension_id: int
    n_pass: int
    n_warn: int
    n_fail: int
    n_na: int

@dataclass(frozen=True)
class ProblemAnalysisCompleteEvent:
    candidate_signature: str
    success: bool
    n_checks_total: int
    n_pass: int
    n_warn: int
    n_fail: int
    n_na: int
    wallclock_seconds: float
```

`C15TelemetrySink` Protocol + Null + InMemory impls — mirror C13/C14.

No mandatory day-1 event analogous to C13's PhaseDConvergenceEvent. C15 has no convergence.

---

## § 10 — Provenance

Same pattern as C13/C14:

```python
def analyze_problems_with_provenance(
    *,
    c14_batch: CirculationAnalysisBatchResult,
    metadata: dict[str, ProblemAnalysisMetadata],
    config: ProblemFinderConfig,
) -> tuple[ProblemAnalysisBatchResult, ProblemAnalysisProvenance]:
    ...
```

Provenance carries per-candidate wallclock, check counts, phase reached, outcome. Wallclock not replay-deterministic; structural fields are (per Inv P2).

---

## § 11 — Public API

```python
def analyze_problems(
    *,
    c14_batch: CirculationAnalysisBatchResult,
    metadata: dict[str, ProblemAnalysisMetadata],
    config: ProblemFinderConfig,
) -> ProblemAnalysisBatchResult:
    """Standard entry. Returns batch result. NEVER returns a score
    (Inv P0)."""
    ...

def analyze_problems_with_provenance(...) -> tuple[...]:
    """Entry with operational provenance metadata."""
    ...

def analyze_with_ranker_hint(
    *,
    c14_batch: CirculationAnalysisBatchResult,
    metadata: dict[str, ProblemAnalysisMetadata],
    config: ProblemFinderConfig,
) -> tuple[ProblemAnalysisBatchResult, tuple[RankerHint, ...]]:
    """RANKER-INTERNAL entry. Returns ProblemReport tuple PLUS a
    RankerHint tuple containing internal aggregate scores for C17
    NSGA-II input. RankerHint.is_ranker_internal == True.

    MUST NOT be exposed to user-facing UX layers. Inv P0 enforcement:
    the runtime should never see a RankerHint outside the C15→C17
    pipeline."""
    ...
```

`ProblemAnalysisMetadata` carries `(cultural_profile, floor_metadata, optional window/furniture data when available)`.

---

## § 12 — Backlog (existing + new from this spec)

### LOCK-mandatory (must close before v1.0 LOCK)

| ID | Description | Effort |
|---|---|---|
| B-C15-SEVERITY-RULE-TABLE-LOCK | Pin severity rules for every (check_id, status) pair | M |
| B-C15-CHECK-REGISTRY-LOCK | Pin the exact ~35 check set, IDs, dimension assignments, and academic citations | L |
| B-C15-CULTURAL-PROFILE-V1-LOCK | Pin the v1 cultural_profile API + indian_middle_class default profile | M |
| B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK | Pin every runnable check's measurement formula | L |

### Data-dependency unlocks (post-LOCK, route to upstream)

| ID | Description | Effort | Routed to |
|---|---|---|---|
| B-C15-WINDOW-DATA | Window placement engine upstream (unlocks Dim 4, partial Dim 8) | L | new upstream component |
| B-C15-FURNITURE-FIT-DATA | Furniture-fit engine upstream (unlocks Dim 9 + 10) | L | new upstream component |
| B-C15-FLOOR-METADATA | Floor metadata threading (unlocks Dim 7) | M | C12 / orchestrator |
| B-C15-ENVELOPE-ORIENTATION | Envelope orientation + climate data (unlocks remaining Dim 8) | M | C12 / orchestrator |

### Moat-preservation governance

| ID | Description | Effort |
|---|---|---|
| B-C15-MOAT-AUDIT | Annual audit verifying no public path leaks a single score (Inv P0); CI lint that detects accidental score-shaped public returns | S |
| B-C15-RANKER-HINT-ACCESS-CONTROL | Module-private guard ensuring RankerHint only reachable from C17 import path | S |

### Post-LOCK polish

| ID | Description | Effort |
|---|---|---|
| B-C15-LOCALIZATION | i18n for why_it_matters + suggested_mitigation text | M |
| B-C15-CHECK-EXPLAIN-API | UX-facing "explain this check in more detail" API | S |
| B-C15-DEPRECATED-STATUS | Add CheckStatus.DEPRECATED for retired checks | S |
| B-C15-CULTURAL-PROFILE-EXPANSION | Beyond indian_middle_class: regional Indian variants, eventually non-Indian | L |

### Project-scope (v2.x)

| ID | Description | Effort |
|---|---|---|
| B-PROJECT-METRIC-INTERPRETATION-GOVERNANCE | (carried from C14 v0.2) Cross-component metric-interpretation consistency | L |
| B-PROJECT-ADVISORY-UNIFICATION | (carried from C14 v0.2) Unify advisories under versioned registry | L |
| B-PROJECT-LEGALITY-LAYERING | (carried from C14 v0.2) Separate universal / regional / cultural rules | L |

### Routed to other components

| ID | Description | Routed to |
|---|---|---|
| B-C13-FUTURE-WINDOW-PLACEMENT | Coordinate window placement contract with C15 (when window engine exists) | C13 maintainer |
| B-C14-METRIC-EXPOSURE-FOR-C15 | C14 already exposes graph metrics; verify no NEW C15 needs require C14 amendment | C14 maintainer |

**Spec § 12 summary: 4 LOCK-mandatory + 4 data-dependency + 2 moat-governance + 4 post-LOCK polish + 3 project-scope + 2 routed = 19 cumulative items.**

---

## § 13 — End-to-end examples (continuing from C14 v0.1 § 13)

### Example 1 — Compact 2-room (entry + bedroom)

**C12 → C13 → C14**: from C14 § 13 Example 1.

**C15 input**: 1 SuccessfulCirculationAnalysis; metadata: cultural_profile=indian_middle_class, floor_metadata={floor_1: {is_ground: True, has_entry: True}}.

**C15 output (proposed shape)**:
```
ProblemReport:
  checks = (
    P1.1: pass    (corridor area = 0% — no corridors)
    P1.2: pass    (no dead corners)
    P1.3: pass    (aspect ratios OK)
    P1.4: warn    (FAR utilization low — small footprint)
    P2.1: warn    (bedroom 14 m² — meets standard but tight for master)
    P2.2: not_applicable  (no kitchen — degenerate 2-room)
    P2.3: not_applicable  (no bathroom)
    P2.4: not_applicable  (no living room)
    P3.1: pass    (bedroom step-depth = 1, well within ≤ 3)
    P3.2: not_applicable  (only 1 habitable room — no gradient)
    ...
    P4.x: not_applicable for all (window data unavailable)
    P9.x: not_applicable for all (furniture data unavailable)
    P10.x: not_applicable for all (furniture data unavailable)
  )
  dimension_summary:
    dim 1: 3 pass, 1 warn, 0 fail, 0 na
    dim 2: 1 warn, 3 na
    dim 3: 1 pass, 3 na
    ...
```

UX consumes this and shows ~5 actionable concerns + flags missing data dependencies.

### Example 2 — Standard 4-room (entry + living + kitchen + bedroom, hub-and-spoke)

**C12 → C13 → C14**: from C14 § 13 Example 2 (with assumed living-as-hub topology).

**C15 input**: 1 SuccessfulCirculationAnalysis with C14 BOTTLENECK_CONCENTRATION flag on living_01.

**C15 output (proposed shape, abbreviated)**:
```
ProblemReport:
  checks = (
    P1.1: pass    (corridor area minimal)
    P2.1: pass    (bedroom meets min area)
    P2.4: pass    (living room 18 m²)
    P3.1: pass    (bedroom step-depth = 2)
    P3.3: pass    (kitchen-dining adjacency direct)
    P5.2: warn    (master step-depth only 2 — privacy gradient shallow)
    P6.1: warn    (consumes C14 bottleneck flag on living — living is the hub)
    P6.2: pass    (corridor widths OK)
    P7.1: pass    (bedroom on ground floor)
    P7.2: not_applicable  (no bathroom data at v1)
    P7.3: pass    (living + kitchen ground floor)
    P4.x: not_applicable for all
    P9.x, P10.x: not_applicable for all
  )
  dimension_summary: ~ 6 pass, 2 warn, 0 fail, ~25 na
```

Two warnings surface: shallow privacy gradient + living-as-hub bottleneck. Both are NICE_TO_HAVE or IMPORTANT, not CRITICAL. Family decides if those bother them.

### Example 3 — Multi-floor with shared vertical stack

**C12 → C13 → C14**: from C14 § 13 Example 3 (GF + FF, each with its own circulation graph).

**C15 input**: 2 SuccessfulCirculationAnalysis (one per floor). C15 v0.1 processes each floor independently (per C14 v0.1 multi-floor scope) BUT also surfaces multi-floor-relevant checks where data is available.

**C15 output (proposed shape, abbreviated)**:
```
GF ProblemReport:
  P7.1: pass    (at least one bedroom on GF? — no, GF has entry + living only)
  Actually re-examining: P7.1 status depends on PROGRAM, not single-floor check.
  P7.1 lives in the CROSS-FLOOR scope. v0.1 emits not_applicable for now.

FF ProblemReport:
  P3.1: warn    (master bedroom step-depth from FF stair-landing = 3, but
                  effective depth from BUILDING entry is much higher;
                  v0.1 doesn't have cross-floor metric, emits warn with
                  caveat in why_it_matters)
```

C15 v0.1 has the SAME multi-floor limitation as C14 v0.1 (per-floor independent). Cross-floor checks (P7.1, P7.2, P7.3, P3.1 effective depth) emit `not_applicable` with na_reason="cross_floor_metric_required" until B-C14-MULTI-FLOOR-CROSS-FLOOR-METRICS lands during C14's 90-day fast-revision window — which then unblocks B-C15-MULTI-FLOOR-DERIVED-CHECKS (filed below).

Filed (added to § 12): **B-C15-MULTI-FLOOR-DERIVED-CHECKS** (post-C14-multi-floor, M effort) — when C14 ships cross-floor metrics, C15 unlocks the corresponding checks.

---

## § 14 — LOCK readiness

**Architectural maturity at v0.1 PROPOSED:** SKETCH. Sufficient to validate the C14/C15 boundary and unblock C15 implementation planning. NOT sufficient for C15 LOCK — that requires:

1. ⏳ Critique walks #1-N to refine
2. ⏳ All 4 LOCK-mandatory backlog items closed (severity table, check registry, cultural profile API, measurement formulas)
3. ⏳ End-to-end pipeline runnable: C12 → C13 → C14 → C15 with at least 20 RUNNABLE checks
4. ⏳ Adversarial integration corpus C15-specific (mirroring C13/C14 corpus)

**Empirical maturity:** ZERO. C15 has not been built.

**Anticipated path:**

Path (a) — quick LOCK as SKETCH: Lock v0.1 to unblock structural reasoning. Pre-implementation refinement via v0.2+ walks.

Path (b) — continue walks: One critique walk on v0.1 before LOCK.

**Recommendation:** Path (a) — same pattern that worked for C13 and C14. v0.1 is a SKETCH; the walks ARE the refinement; locking the sketch is the gate that unblocks substantive work.

---

**END OF v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
