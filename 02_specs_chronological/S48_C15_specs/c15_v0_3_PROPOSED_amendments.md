# C15 Spec — v0.3 Amendment Bundle (Path A LOCK preparation)

**Status:** v0.3 PROPOSED — pending Ramalingam LOCK adjudication.
**Origin:** S48 Path A execution. Closes LOCK-mandatory item
B-C15-SEVERITY-CHANGE-GOVERNANCE-PRE-LOCK + adopts deferred A12
amendment.

This document is the diff against v0.2 LOCKED. Two amendments:

- **A11** — § 14.2 NEW: Severity-Change Governance Gate
- **A12** — `coverage_quality` field on `ProblemReport` + per-dimension
  maturity on `DimensionSummary`

---

## A11 — § 14.2 NEW: Severity-Change Governance Gate

### Rationale

Per S48 critique walk #1 item 7 + walk #2 item 11: with `RankerHint`
removed (A1) and aggregator authority blocked (Inv P0 STRICTER),
severity-rule mappings are now the *de facto* value layer of C15.
Changing a check's severity from WARN to FAIL doesn't just change one
output line — it changes which layouts C17's downstream ranker
considers unacceptable, which profiles surface different concerns, and
which architectural patterns the moat audits as "punished by the
system."

Mirrors § 14.1 (check-addition gate, A8/A9 in v0.2). Without this gate
severity edits ship as one-line table changes without governance
overhead — a future maintainer optimizing for "simpler defaults" can
quietly retune the value layer.

### § 14.2 text

> **§ 14.2 — Severity-Change Governance Gate.**
>
> Every change to `severity_rule_table.SEVERITY_RULE_TABLE_V1`
> (severity reassignments, severity_basis citation updates, status
> mapping extensions) requires the following before merge:
>
> **a. Changelog entry.** Each rule change carries a changelog entry
> citing the source-shift motivating the change. Acceptable sources:
> updated NBC clause, updated Lifetime Homes Standard / DDIG guidance,
> updated Neufert revision, published architectural-research finding,
> or domain-expert review record. "Reviewer felt severity was off" is
> NOT acceptable without a corroborating source.
>
> **b. Backward-compatibility review.** Each rule change must be
> evaluated against the v1 reference layout corpus (defined under
> B-C15-LAYOUT-DIVERSITY-AUDIT). The review records: how many
> reference layouts change their problem count, which dimensions are
> affected, whether any reference layout flips from "advisor-clean"
> to "advisor-blocked". A regression that flips a previously-clean
> reference layout requires explicit Ramalingam sign-off and is
> recorded in the spec § 12 backlog roll-up.
>
> **c. Registry version bump (Inv P15 extension).** Severity-rule
> changes increment `severity_rule_table.SEVERITY_TABLE_VERSION` and
> propagate into the C15 registry version. Replay determinism (Inv
> P2) thus distinguishes pre-change vs. post-change reports.
>
> **d. Impact analysis annotation.** Each rule change records the
> number of registered checks affected, the cultural profiles
> affected, and whether the change introduces or removes
> profile-specific behavior.
>
> **e. Pre-LOCK requirement (this §).** All severity-rule changes
> between v0.3 PROPOSED and v1.0 LOCK carry full governance
> documentation as defined in (a)–(d). Post-LOCK severity changes
> follow this gate without exception.

### Cache impact

NOT cache-relevant. § 14.2 is process-only. It does not alter schema,
serialization shape, or report contents. Existing
`SEVERITY_TABLE_VERSION` already flows into cache keys (Inv P15);
§ 14.2 enforces *that the version bump happens* but adds no new
inputs to cache key composition.

---

## A12 — `coverage_quality` field on `ProblemReport` + per-dimension maturity

### Rationale

Per S48 critique walk #1 items 6 + 8 (DOCUMENTED + PROPOSED) and
walk #2 items 3 + 10 (same concern in different framing). When 21 of
41 checks are DEFERRED (no window data, no envelope polygon, no
furniture-fit data), a user reading "3 problems found" sees what
looks like a high-confidence report. They cannot tell that 51% of the
analytic surface is silent due to upstream data limitations, not
absence of problems.

Surfacing coverage at report level + per-dimension level lets the UX
distinguish "we evaluated 9 of 10 dimensions thoroughly and found 3
problems" from "we evaluated 4 of 10 dimensions; the other 6 are
deferred for data reasons; here are 3 problems within what we could
see."

Absorbs B-C15-DIMENSION-MATURITY-METADATA (walk #1 item 6).

### Schema changes

**New enum `CoverageQuality`** (in `schema.py`):

```python
class CoverageQuality(StrEnum):
    """Report-level coverage signal. Distinguishes 'we evaluated
    most of the design space' from 'we could only see a fraction'.
    NOT a quality-of-layout signal; a quality-of-evaluation signal.
    Surfacing is mandatory in UX render (per Principle 5 of Design
    Principles v3.1: confidence indicators)."""

    HIGH = "HIGH"           # ratio_applicable ≥ 0.70
    MEDIUM = "MEDIUM"       # 0.40 ≤ ratio_applicable < 0.70
    LOW = "LOW"             # ratio_applicable < 0.40
```

**New enum `DimensionMaturity`** (in `schema.py`):

```python
class DimensionMaturity(StrEnum):
    """Per-dimension structural maturity at the C15 v1 envelope.
    Surfaces the structural asymmetry that engine is stronger in
    geometry/privacy/flow than light/storage/adaptability — not
    philosophically, structurally."""

    RUNNABLE = "RUNNABLE"
    """All registered checks for this dim are runnable on current
    upstream data shape."""

    PARTIAL = "PARTIAL"
    """Some checks runnable, some deferred for upstream data
    reasons."""

    NOT_RUNNABLE = "NOT_RUNNABLE"
    """All checks deferred at v1 envelope; dimension is a
    placeholder for upstream extensions."""
```

**New fields on `DimensionSummary`:**

```python
@dataclass(frozen=True)
class DimensionSummary:
    ...existing fields...
    maturity: DimensionMaturity
    """v0.3 A12. Surfaces per-dimension structural maturity."""

    n_applicable: int
    """v0.3 A12. Count of RUNNABLE checks emitted in this dim."""

    n_deferred: int
    """v0.3 A12. Count of DEFERRED checks emitted in this dim."""
```

**New fields on `ProblemReport`:**

```python
@dataclass(frozen=True)
class ProblemReport:
    ...existing fields...
    coverage_quality: CoverageQuality
    """v0.3 A12. Report-level coverage signal. NOT a layout
    quality score; a coverage signal. Inv P0 STRICTER preserved:
    coverage_quality is computed from registry shape + upstream
    data shape, NOT from any check outputs."""

    ratio_applicable: float
    """v0.3 A12. Exact ratio used to derive coverage_quality.
    Bounded in [0.0, 1.0]. Provenance: n_applicable across
    dim_summaries / (n_applicable + n_deferred + dimensions
    in dimensions_not_evaluated × spec-defined check counts).
    Note: this float is a coverage-of-evaluation signal, NOT a
    quality-of-layout signal — moat-lint allows this exact field
    name by exception (documented in moat_lint.py PATTERNS
    docstring)."""
```

### Derivation rule (deterministic)

```python
def _derive_coverage_quality(
    dim_summaries: tuple[DimensionSummary, ...],
) -> tuple[CoverageQuality, float]:
    """Per § 14.3 (NEW). Deterministic; replay-stable.

    Numerator: sum(n_applicable for s in dim_summaries).
    Denominator: sum(n_applicable + n_deferred for s in dim_summaries).

    Inv P12 guarantees dim_summaries covers all 10 dimensions exactly
    once and that every registered check produces exactly one record;
    so the denominator equals the spec-mandated registered-check
    count (41 at v1 envelope) — no separate "unseen" term required.

    The `dimensions_not_evaluated` field is a SEPARATE disclosure
    mechanism (Inv P19 / A6) for habitation categories C15 doesn't
    address at all; it is NOT part of the coverage ratio because
    those categories aren't in the registry.

    Ratio threshold: 0.70 → HIGH; 0.40 → MEDIUM; else LOW.
    """
    n_app = sum(s.n_applicable for s in dim_summaries)
    n_def = sum(s.n_deferred for s in dim_summaries)
    total = n_app + n_def
    if total == 0:
        return (CoverageQuality.LOW, 0.0)
    ratio = n_app / total
    if ratio >= 0.70:
        return (CoverageQuality.HIGH, ratio)
    if ratio >= 0.40:
        return (CoverageQuality.MEDIUM, ratio)
    return (CoverageQuality.LOW, ratio)
```

### Cache impact

**Cache-relevant.** Schema change → `DRAWING_SCHEMA_VERSION` (sic;
C15 uses `PROBLEM_REPORT_SCHEMA_VERSION`) bumps. New fields enter
the report serialization. Cache keys at the semantic_identity tier
change; replay_signature tier changes. Existing cached reports
become invalid (acceptable — pre-LOCK).

### Moat impact

`ratio_applicable: float` would normally trip moat-lint as a
warning under PATTERN[10] (`confidence: float`). The field is
DOCUMENTED-AS-EXCEPTION in `moat_lint.py` because:
- it measures coverage-of-evaluation, not quality-of-layout
- it is derived from registry + upstream data shape, NOT from any
  per-check output
- it has a deterministic formula that NEVER reads check status

The exception is encoded as a comment-anchor allowlist in
`moat_lint.py` (see Step-9 update below).

### Backward compatibility

v0.2 callers of `ProblemReport.__init__` will break — new
mandatory fields. Acceptable: pre-LOCK, no external callers exist
yet (C15 is unreleased). C16 (next consumer) will be authored
against v0.3 schema directly.

---

## § 12 — Backlog reconciliation under v0.3

The following items are CLOSED by this amendment bundle:

| Item | Closed by |
|---|---|
| B-C15-SEVERITY-CHANGE-GOVERNANCE-PRE-LOCK | A11 § 14.2 |
| B-C15-DIMENSION-MATURITY-METADATA (walk #1 item 6) | A12 DimensionMaturity field |

The following items REMAIN open (LOCK-mandatory before v1.0):

- B-C15-CULTURAL-PROFILE-V1-LOCK
- B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK
- B-C15-CHECK-REGISTRY-LOCK
- B-C15-SEVERITY-RULE-TABLE-LOCK
- B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
- B-C15-CULTURAL-PROFILE-COVERAGE
- B-C15-MOAT-LINT (closed by Step 1 of S48 Path A execution)

---

## Status banner

**v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**

Per BuildemUp LOCK-trigger protocol (memory #14): when Ramalingam
says "lock C15 v0.3", Claude re-runs three-check, surfaces
v0.3.LOCK-CANDIDATE, and Ramalingam adjudicates LOCK.

---

*End of v0.3 amendment bundle.*
