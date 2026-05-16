# spec_C15_v0_2_PROPOSED_DELTA.md

**Component 15 — Layout Problem Finder**
**Status:** v0.2 PROPOSED_DELTA. PENDING Ramalingam LOCK adjudication.
**Authored:** S46 (post-critique-walk-#1)
**Reads as a delta on top of:** spec_C15_v0_1_PROPOSED.md
**Origin:** Critique walk #1 on v0.1 PROPOSED, dated S46.

---

## Walk #1 summary

External reviewer produced 20 items. Verdict distribution:

- 10 VALID-AS-PATCH (incorporated as A1-A10 below)
- 2 VALID-BUT-BACKLOG (new B-NNN, see § 12)
- 8 DOCUMENTED (praise or already-addressed)

Self-analysis surfaced 3 issues in v0.1 the reviewer flagged obliquely:
- (a) RankerHint INSIDE C15 was a structural seed for the very score-leakage the spec warns against — folds with reviewer item 1 → A1
- (b) Cultural profile defaulting was an ossification trap → folds with reviewer item 4 → A3
- (c) dimension_summary tuple invited score-by-arithmetic → A10

The reviewer's central thesis (item 20) — "C15's risks are socio-technical, not algorithmic" — is accepted as the framing for v0.2. Amendments target structural prevention of the socio-technical risks where possible, governance where structural prevention is infeasible.

---

## A1 — Remove RankerHint from C15 entirely

**Origin:** Reviewer item 1 + self-analysis (a).

**Problem:** v0.1 § 11 introduced `analyze_with_ranker_hint()` returning ProblemReport + RankerHint, where RankerHint carries C15-internal aggregate scores for C17 NSGA-II consumption. The reviewer correctly observes this places the "score seed" *inside* C15 itself. Even with module-access guards (B-C15-RANKER-HINT-ACCESS-CONTROL filed at v0.1), once a latent score exists, organizational gravity pulls it outward over time.

The structural fix is stronger than governance: **don't compute a score in C15 at all.**

**Amendment:**

Delete from v0.1 § 11:
- `analyze_with_ranker_hint()` entry point
- `RankerHint` type
- The "is_ranker_internal" flag concept
- All references to "internal aggregate" in C15

Inv P0 strengthens:

> **Inv P0 (v0.2 STRICTER).** C15 NEVER computes a single number representing layout quality, anywhere — not in a public API, not in a private helper, not in telemetry, not in cache keys. The output of C15 is always a structured tuple of ProblemCheck records. Any consumer (C17 ranker, UX, analytics) that wants an aggregate computes it themselves from the structured records. C15 holds no aggregation logic.

C17's responsibility expands: C17 reads `ProblemReport.checks`, applies its OWN weighting scheme (which MAY vary by cultural_profile, optimization mode, or user preference), and computes its OWN aggregate for NSGA-II input. C17 owns the score; C15 stays descriptive.

A CI lint rule (filed as **B-C15-MOAT-LINT** below) enforces structurally: grep C15 module for any function returning `float`, `int`, or `tuple[float, ...]` from a check-aggregation context. Should match zero outside cache-key hashing.

**Cache-relevant:** YES (public API surface changed → bump C15_VERSION).

---

## A2 — Add `epistemic_kind` field to ProblemCheck

**Origin:** Reviewer items 2, 3, 12.

**Problem:** v0.1 ProblemCheck has status + severity but no signal that distinguishes the EPISTEMIC BASIS of a check. "Bedroom below NBC minimum area" and "pooja room visual privacy" both appear as FAIL+IMPORTANT. The user has no structural cue to know that one is regulatory and the other is cultural preference. This is what enables the reviewer's items 3 (objective-defect framing) and 12 (soft-regulation drift).

**Amendment:**

Add to `ProblemCheck`:

```python
class CheckEpistemicKind(StrEnum):
    REGULATORY = "regulatory"
        # Backed by codified law/standard: NBC India 2016, IS 456,
        # IS 962, IS 11268, TNCDBR, etc. Failing has regulatory force.
    ARCHITECTURAL_HEURISTIC = "architectural_heuristic"
        # Backed by published architectural design literature:
        # Neufert, Ching, Hillier 1984/1987, residential POE corpus.
        # Failing is a design concern grounded in evidence but not
        # legally binding.
    CULTURAL_PREFERENCE = "cultural_preference"
        # Backed by cultural conventions tagged to the current
        # cultural_profile. Indian residential context examples:
        # dedicated pooja room, dining/kitchen separation,
        # multigenerational privacy norms. Failing is a preference,
        # not a defect.

@dataclass(frozen=True)
class ProblemCheck:
    # ... existing fields ...
    epistemic_kind: CheckEpistemicKind
```

Each check_id in the registry has its `epistemic_kind` defined as a STABLE part of the check. Same check never changes kind across versions (Inv P15 covers this).

UX consequence: regulatory FAILs render as blocking, architectural-heuristic FAILs render as "consider this," cultural-preference FAILs render as "your family may have a preference here." Three visually distinct categories prevent the reviewer's "FAIL = objective defect" misreading.

**Cache-relevant:** YES (schema change → bump C15_VERSION).

---

## A3 — Cultural profile is REQUIRED, no default; sub-variants supported

**Origin:** Reviewer items 4, 16 + self-analysis (b).

**Problem:** v0.1 § 11 specified `cultural_profile` with implicit default `indian_middle_class`. The reviewer correctly observes this default will harden into "the system's idea of a proper home" — and that "Indian middle-class" is itself enormously heterogeneous (Tamil multigen, Bangalore startup apartments, Kerala courtyard, Mumbai compact, village self-built, NRI returnee).

**Amendment:**

`cultural_profile` becomes a REQUIRED parameter of every C15 entry point. No default. Callers MUST select a profile.

The profile API supports sub-variants:

```python
class CulturalProfile(StrEnum):
    INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN = "in_mc_tamil_multigen"
    INDIAN_MIDDLE_CLASS_KERALA_COURTYARD = "in_mc_kerala_courtyard"
    INDIAN_MIDDLE_CLASS_COMPACT_URBAN = "in_mc_compact_urban"
    INDIAN_MIDDLE_CLASS_GENERIC = "in_mc_generic"        # least opinionated
    INDIAN_LOWER_INCOME_INCREMENTAL = "in_li_incremental"
    INDIAN_NRI_RETURNEE = "in_nri_returnee"
    # v2+ expansion: non-Indian variants
```

At v1.0 LOCK, **at least 3 sub-variants** must be defined with measurable differences in:
- Which checks apply (some checks are profile-gated)
- Which severity mappings apply (per A4)
- Which `cultural_preference` epistemic_kind checks emit `not_applicable` vs `fail`

Add Inv P17 NEW:

> P17: `analysis_request.cultural_profile` MUST be explicitly provided. C15 raises `MissingMetadataError` (per § 4) if the field is absent. No default profile exists.

The ProblemReport also carries the active profile in its provenance:

```python
ProblemReport:
    # ... existing fields ...
    cultural_profile_active: CulturalProfile   # makes the choice auditable
```

UX consumers MUST render the active profile prominently: "Evaluated under: Indian middle-class Tamil multigenerational profile." This makes the lens explicit and lets families opt to re-evaluate under a different profile.

Filed: **B-C15-CULTURAL-PROFILE-V1-LOCK** (already LOCK-mandatory at v0.1) — v0.2 amends scope to require ≥3 sub-variants at LOCK.

**Cache-relevant:** YES (different profiles produce different reports → profile is part of cache key).

---

## A4 — Severity rule table requires source citation per mapping

**Origin:** Reviewer item 8.

**Problem:** v0.1 § 5.2 sketched the severity rule table as `(check_id, status) → severity`. The reviewer correctly observes that severity assignment IS political — encoding regulatory, class, cultural, and lifestyle assumptions. v0.1's centralization concentrates that bias without making it auditable.

**Amendment:**

Severity rule table entries now require `severity_basis`:

```python
@dataclass(frozen=True)
class SeverityRule:
    check_id: str
    status: CheckStatus
    cultural_profile: CulturalProfile | None  # None = applies to all profiles
    severity: CheckSeverity
    severity_basis: str
        # Required: citation. Examples:
        # "NBC India 2016 §6.2.1 (minimum bedroom area)"
        # "Neufert 4th ed, p.78 (shower wall-mount ergonomics)"
        # "Cultural convention: Tamil pooja room visibility norms,
        #  per Karthikeyan 2017"
        # If severity_basis is empty or unclear, the rule fails
        # registration at module load (LocalProblemError).
```

Inv P18 NEW:

> P18: Every severity rule has a populated `severity_basis` string. Empty strings or strings shorter than 20 characters fail registration. Module load enforces this via CheckRegistryError (existing in § 4).

The severity_basis text is queryable per check via a new `explain_severity(check_id)` API entry — used by UX for the "why this severity" disclosure.

Filed: **B-C15-SEVERITY-AUDIT** — annual review of severity_basis citations to detect stale references (cited NBC clauses that have been superseded; obsolete cultural conventions).

**Cache-relevant:** YES (severity changes affect output, severity_basis is part of registry → bump C15_CHECK_REGISTRY_VERSION).

---

## A5 — ProblemReport default view surfaces RUNNABLE+PARTIAL; NA in sub-view

**Origin:** Reviewer item 6.

**Problem:** v0.1 returned all ~35-41 checks in one `checks` tuple regardless of status. At v1, ~15 are expected to emit NOT_APPLICABLE due to missing upstream data. The reviewer correctly observes this dilutes the signal: users see "8 PASS, 3 WARN, 1 FAIL, 29 NOT_APPLICABLE" and the report feels incomplete rather than insightful.

**Amendment:**

Restructure ProblemReport:

```python
@dataclass(frozen=True)
class ProblemReport:
    source_placed_candidate_signature: str

    # ── Primary deliverable (RUNNABLE checks only) ─────────────
    applicable_checks: tuple[ProblemCheck, ...]
        # Checks whose status ∈ {pass, warn, fail}. Sorted lex-ASC.

    # ── Incomplete-analysis sub-view ───────────────────────────
    deferred_checks: tuple[DeferredCheck, ...]
        # Checks that emitted NOT_APPLICABLE. Each carries:
        #   - check_id, dimension_id
        #   - na_reason (structured: which upstream data was missing)
        #   - blocking_backlog_item: str  (e.g., "B-C15-WINDOW-DATA")
        # UX renders as: "Checks deferred — missing upstream data: [list]"
        # NOT counted alongside applicable_checks in status summaries.

    # ── Dimensions not evaluated by C15 at all ─────────────────
    dimensions_not_evaluated: tuple[str, ...]
        # See A6 for full content. Surfaced here for completeness.

    # ... rest of report (cultural_profile_active per A3,
    #     unconventional pattern hint per A7, provenance, etc.) ...
```

`DeferredCheck` is NOT a `ProblemCheck` — it's a lighter record indicating "we'd check X but can't." UX shows it as a "future improvement" rather than a current concern.

Inv P12 (every registered check produces exactly one record) is preserved but routes registered checks to either `applicable_checks` OR `deferred_checks`, never both.

**Cache-relevant:** YES (schema change → bump C15_VERSION).

---

## A6 — Add `dimensions_not_evaluated` enumeration

**Origin:** Reviewer item 10.

**Problem:** v0.1's 10 dimensions imply coverage of "lived quality" but explicitly DON'T cover (per § 0.0) emotional comfort, family habits, future adaptability, sunlight mood, acoustic experience, etc. The reviewer correctly observes that a long checklist psychologically feels authoritative even when admitting heuristic limits in prose.

**Amendment:**

ProblemReport now carries `dimensions_not_evaluated: tuple[str, ...]` enumerating categories of habitation C15 explicitly DOES NOT evaluate, with at least the following entries at v1.0:

```python
DIMENSIONS_NOT_EVALUATED_V1: Final[tuple[str, ...]] = (
    "emotional_comfort_and_memory_of_place",
    "long_term_family_habit_evolution",
    "acoustic_experience_inside_rooms",
    "olfactory_experience",
    "tactile_material_quality",
    "social_relationships_supported_by_layout",
    "ritual_and_ceremonial_use_specifics",
    "sunlight_mood_throughout_day_and_year",
    "future_adaptability_unanticipated_changes",
    "aesthetic_taste_traditional_vs_modern",
)
```

This is **part of the report**, not buried in spec prose. UX consumers MUST render these in a "what we don't check" section. Makes incompleteness visible at the artifact level.

Inv P19 NEW:

> P19: ProblemReport.dimensions_not_evaluated is non-empty at every report. Empty = bug, fails report construction.

**Cache-relevant:** YES (schema change → bump C15_VERSION).

---

## A7 — Unconventional pattern hint + confidence reduction

**Origin:** Reviewer item 11.

**Problem:** v0.1 has no signal for "this layout is unconventional in ways C15's checks may incorrectly flag." Reviewer correctly identifies courtyard-centered, split-level, ritual-procession, compact-incremental, and adaptive mixed-use homes as patterns C15 will likely punish.

**Amendment:**

Add to ProblemReport:

```python
@dataclass(frozen=True)
class UnconventionalPatternHint:
    detected: bool
    suspected_patterns: tuple[str, ...]
        # E.g., ("courtyard_centered", "split_level_circulation")
    confidence_caveat: str
        # Consumer-readable note: "This layout shows patterns that
        # C15's standard checks may incorrectly flag. Treat the
        # following problems with reduced confidence."
    affected_check_ids: tuple[str, ...]
        # Which checks are flagged-but-likely-misapplied due to
        # the unconventional pattern.

ProblemReport:
    # ...
    unconventional_pattern_hint: UnconventionalPatternHint
```

Detection rules at v1 (sketch, refined by walks):
- `courtyard_centered`: > 3 habitable rooms with primary adjacency to a single non-habitable central room (the courtyard)
- `split_level_circulation`: floor metadata indicates non-zero z-offset between adjacent rooms on same nominal floor
- `ritual_procession`: graph path from entry shows monotonic step-depth increase through ≥ 4 rooms with explicit ritual-category rooms (foyer, pooja, sanctum)
- `compact_incremental`: total carpet area < 600 sqft AND room count ≥ 4 (high density per room)
- `multigenerational_segregation`: ≥ 2 master-class bedrooms separated by step-depth ≥ 3 (acoustic/visual buffer pattern)

When hint detected, UX presents the report WITH a banner: "This layout uses [pattern]; standard checks may not apply. Concerns below should be considered with reduced confidence."

Filed: **B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK** (v1.0-LOCK-MANDATORY, M effort) — pin the exact detection rules.

**Cache-relevant:** YES (schema change + new computation → bump C15_VERSION + C15_CHECK_REGISTRY_VERSION).

---

## A8 — Metric-addition gate for new checks (mirror C14 v0.2 A9)

**Origin:** Reviewer items 7, 15, 18.

**Problem:** v0.1 had `B-C15-CHECK-REGISTRY-LOCK` as LOCK-mandatory but no formal gate for *post*-LOCK check additions. The reviewer correctly identifies check accretion as C15's largest long-term architectural risk.

**Amendment:**

Add new § 14.1 (mirroring C14 v0.2 A9) titled "Check-addition governance gate":

> ## § 14.1 — Check-addition governance gate (post-LOCK)
>
> After v1.0 LOCK, adding any new check to C15 requires passing a three-criterion gate. The proposal must demonstrate:
>
> 1. **Architectural justification.** Why this check belongs at C15 and not elsewhere (regulatory checks could route to a separate compliance layer; furniture-fit checks belong in a furniture engine; ranking concerns belong at C17). C15 is the layout-problem-finder layer; if the check is about consumption, cost, or behavior, it routes elsewhere.
>
> 2. **Downstream UX usefulness evidence.** At least one UX surface (consumer-facing or analyst-facing) must commit to rendering the new check distinctly. "Might be useful someday" fails this gate. Checks that would just be one more line in an already-long list without distinct UX treatment fail.
>
> 3. **No-overlap proof.** The new check does not substantially overlap with an existing check. If a similar check exists, the proposal must either: (a) extend the existing check's measurement formula, or (b) make a case for *why* the new check captures something the existing one cannot.
>
> Plus: every new check increases C15's registry size. The gate is enforced at critique-walk time. Backlog item **B-C15-CHECK-ACCRETION-AUDIT** commits to annual review of all checks against these criteria.

**Cache-relevant:** NO (governance only).

---

## A9 — Explicit optimization-pressure acknowledgment

**Origin:** Reviewer item 9 + connected to A1.

**Problem:** Even with A1 moving aggregation to C17, the reviewer correctly observes that *upstream layout generation will optimize against C15's implicit values*. Future layouts produced by C12 + C11 will converge toward patterns that minimize C15 problem flags. This is unavoidable IF C15 outputs influence ranking. The reviewer's warning: avoid score UX, but optimization bias remains.

**Amendment:**

Add new paragraph to § 0.5 (moat preservation contract):

> **Optimization pressure disclosure.** C15 outputs feed C17 ranker. C17 internally weights checks to produce NSGA-II input. This means upstream layout generation (C11/C12) WILL be optimized against C15's implicit values, even though users never see scores.
>
> C15 cannot prevent this; the alternative (don't feed C15 outputs to any optimization layer) defeats the product's purpose. What C15 can guarantee is:
> - **Transparency**: Every check, severity, and its citation are inspectable per A4.
> - **Locality**: Aggregation lives at C17, not C15 (A1). The "value model" is visible at one place, not distributed.
> - **Plurality**: C17 supports multiple weighting schemes via cultural_profile (A3). No single canonical "good layout" definition is enforced.
> - **Optionality**: C17 ranking can be bypassed; C15 outputs are useful standalone for inspection without optimization.
>
> The optimization pressure exists. Making it visible is the moat.

**Cache-relevant:** NO (documentation only).

---

## A10 — dimension_summary restructured to avoid score-by-arithmetic

**Origin:** Self-analysis (c) + reviewer item 6.

**Problem:** v0.1 `dimension_summary: (dimension_id, n_pass, n_warn, n_fail, n_na)` invited UX consumers to compute ratios like "60% pass" or "weighted dimension score = pass×3 + warn×2 + fail×0" — score-by-arithmetic. The reviewer's item 6 also notes the equation of NA with other statuses dilutes signal.

**Amendment:**

Replace v0.1 `DimensionSummary` with:

```python
@dataclass(frozen=True)
class DimensionSummary:
    dimension_id: int
    dimension_name: str

    # ── Data availability (separate concern) ───────────────────
    n_applicable: int      # how many checks ran
    n_deferred: int        # how many emitted NA

    # ── Within-applicable status breakdown ─────────────────────
    n_pass: int
    n_warn: int
    n_fail: int

    # Inv: n_pass + n_warn + n_fail == n_applicable
    # Inv: n_applicable + n_deferred == total registered checks for this dimension
```

UX consumers can render two separate visualizations:
- Data coverage: "8 of 10 checks ran (80% applicable)"
- Within-applicable: "Of 8 applicable, 6 pass, 1 warn, 1 fail"

But NOT: "60% overall quality." The structural split makes arithmetic-scoring awkward (consumers would have to invent it intentionally), where the v0.1 schema invited it (consumers would do it incidentally).

**Cache-relevant:** YES (schema change → bump C15_VERSION).

---

## A11 — New backlog items + amended existing ones

### New backlog items filed this walk

| ID | Description | Origin | Trigger | S{N}-scope | Effort |
|---|---|---|---|---|---|
| B-C15-MOAT-LINT | CI lint rule grep-checking C15 module for any function returning numeric aggregates from check-contexts; enforces A1 structurally | A1 | LOCK-mandatory | C15 v1.0 | S |
| B-C15-UX-FRAMING-GOVERNANCE | UX-layer presentation governance: render checks as "design considerations" not "problems"; epistemic_kind visual differentiation; cultural profile prominence | Reviewer #3, #12 | post-LOCK | C15 v1.x | M |
| B-C15-CLASS-BIAS-AUDIT | Continuous audit detecting whether the default profile assumptions (e.g., dedicated pooja room, dining separation, certain room-size minimums) systematically disadvantage non-aspirational layouts | Reviewer #16 | post-LOCK ongoing | C15 v1.x | S |
| B-C15-SEVERITY-AUDIT | Annual review of severity_basis citations for staleness (superseded NBC clauses, obsolete conventions) | A4 | post-LOCK annual | C15 v1.x | S |
| B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK | Pin the exact detection rules for unconventional patterns + their affected check lists | A7 | LOCK-mandatory | C15 v1.0 | M |
| B-C15-CHECK-ACCRETION-AUDIT | Annual audit per A8 gate | A8 | post-LOCK annual | C15 v1.x | S |
| B-C15-CULTURAL-PROFILE-COVERAGE | Ensure ≥ 3 sub-variants ship at v1.0 LOCK with measurable behavioral differences | A3 | LOCK-mandatory | C15 v1.0 | M |

### Existing backlog items amended

- **B-C15-CULTURAL-PROFILE-V1-LOCK** — scope amended to require ≥3 sub-variants at LOCK (per A3).
- **B-C15-MOAT-AUDIT** — scope amended: with A1's structural removal of RankerHint, audit shifts from "verify no score leaks" (post-hoc) to "verify the lint rule (B-C15-MOAT-LINT) is enforced and not bypassed."
- **B-C15-RANKER-HINT-ACCESS-CONTROL** — **OBSOLETE**, deleted from backlog. RankerHint no longer exists per A1.

---

## § 12 — Backlog (full roll-up after v0.2)

Combining v0.1's 19 items minus 1 obsolete (B-C15-RANKER-HINT-ACCESS-CONTROL) + v0.2's 7 new = **25 cumulative items**.

### LOCK-mandatory (must close before v1.0 LOCK) — now 7

| ID | Description |
|---|---|
| B-C15-SEVERITY-RULE-TABLE-LOCK | Pin severity rules + severity_basis per rule (per A4) |
| B-C15-CHECK-REGISTRY-LOCK | Pin the ~35-41 check set + epistemic_kind per check (per A2) |
| B-C15-CULTURAL-PROFILE-V1-LOCK | Pin cultural_profile API + ≥ 3 sub-variants (amended per A3) |
| B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK | Pin every runnable check's measurement formula |
| B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK | Pin unconventional-pattern detection rules (per A7) |
| B-C15-MOAT-LINT | CI lint enforcing no numeric aggregation in C15 (per A1) |
| B-C15-CULTURAL-PROFILE-COVERAGE | ≥3 sub-variants ship at LOCK with measurable behavioral differences (per A3) |

### Data-dependency unlocks (post-LOCK, route to upstream) — 4

(Unchanged from v0.1.)

### Moat-preservation governance — 2

(Updated per A1.)

### Post-LOCK polish — 5

(v0.1's 4 + B-C15-UX-FRAMING-GOVERNANCE per v0.2 A11.)

### Annual audits — 3

| ID | Description |
|---|---|
| B-C15-MOAT-AUDIT | Audit lint enforcement |
| B-C15-SEVERITY-AUDIT | Severity-basis citation review |
| B-C15-CHECK-ACCRETION-AUDIT | Three-criterion gate review (per A8) |
| B-C15-CLASS-BIAS-AUDIT | Continuous class-bias detection (per A11) |

### Project-scope (v2.x) — 3

(Unchanged from v0.1.)

### Routed to other components — 2

(Unchanged from v0.1.)

**Spec § 12 v0.2 summary: 25 cumulative items, 7 LOCK-mandatory.**

---

## § 14.2 — LOCK readiness UPDATED after v0.2

**Architectural maturity at v0.2 PROPOSED:** SKETCH with one cycle of patches. The moat strengthened structurally (A1) rather than only by governance. Three epistemic categories now distinguish regulatory / heuristic / cultural-preference (A2). Cultural profile required, not defaulted (A3). NA signal-dilution fixed (A5). Incompleteness visible at the schema level (A6). Optimization pressure disclosed explicitly (A9). Check accretion gated (A8).

**Empirical maturity:** Still ZERO. C15 has not been built.

**Anticipated LOCK path:**

Path (a) — quick LOCK: Lock v0.2 as the SKETCH-level spec. Walks #2+ refine during implementation phase.

Path (b) — walk #2 first: continue critique on v0.2 before LOCK.

**Recommendation:** Path (a). v0.2 substantially addresses the structural concerns the walk surfaced. Adding a third walk on v0.2 risks the bureaucratization spiral C14 walk #2 warned against, especially given this walk's items 15, 18, 20 already signaled it. Pattern E (scope-creep-mid-build) caution applies.

The reviewer's strongest items (1 RankerHint, 2 epistemic mixing, 9 optimization pressure) have structural remedies in v0.2. The remaining items (3 framing, 12 soft-regulation, 17-20 meta-observations) are either UX governance backlog or accepted philosophical observations that no amendment can dissolve.

---

**END OF v0.2 PROPOSED_DELTA. PENDING Ramalingam LOCK adjudication.**
