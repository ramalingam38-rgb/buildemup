"""
BuildemUp — Component 15 — schema (output + typestate dataclasses)
===================================================================

Per C15 SPEC v0.2 LOCKED. Composed from:
- v0.1 § 1.2 (ProblemReport base shape)
- v0.1 § 1.3 (ProblemCheck dataclass)
- v0.1 § 1.4 (10 dimensions)
- v0.1 § 1.5 (check ID format P{dimension}.{check_index})
- v0.1 § 5 (typestate Successful / Failed + BatchResult)
- v0.2 A1 (RankerHint REMOVED; Inv P0 STRICTER)
- v0.2 A2 (epistemic_kind field added to ProblemCheck)
- v0.2 A3 (cultural_profile_active surfaced in ProblemReport)
- v0.2 A4 (severity_basis ≥ 20 chars enforced on SeverityRule)
- v0.2 A5 (applicable_checks + deferred_checks split)
- v0.2 A6 (dimensions_not_evaluated enumeration)
- v0.2 A7 (UnconventionalPatternHint)
- v0.2 A10 (DimensionSummary restructured)

All dataclasses are frozen for hash-stability + replay determinism
(Inv P2 byte-equal replay). Canonical orderings are enforced in
__post_init__ (Inv P3 / P7 / P9 / P12).

The typestate discipline (per v0.3 B11 inherited from C13/C14) means
downstream consumers MUST pattern-match on SuccessfulProblemAnalysis
vs FailedProblemAnalysis — mypy rejects access to .report on a
FailedProblemAnalysis. This enforces filtering at the type layer,
preventing WARN-mode-failed candidates from being misused as
successful results.

═══════════════════════════════════════════════════════════════════════
MOAT ENFORCEMENT (Inv P0, strengthened by v0.2 A1):
═══════════════════════════════════════════════════════════════════════
C15 NEVER computes a single number representing layout quality,
anywhere — not in a public API, not in a private helper, not in
telemetry, not in cache keys. The output of C15 is ALWAYS a
structured tuple of records.

The DimensionSummary in this module exposes COUNTS (n_pass, n_warn,
n_fail, n_applicable, n_deferred). These are descriptive integers,
NOT layout-quality scores. Per v0.2 A10, the structural split makes
arithmetic-scoring like "60% pass" awkward by design — UX consumers
would have to invent the formula intentionally.

No function or property in this module returns a `float` derived from
ProblemCheck status/severity values. The B-C15-MOAT-LINT CI rule (to
ship at v1.0) greps for such functions and fails the build if any
appear.
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal, Optional

from .contracts import CulturalProfile
from .errors import CheckRegistryError
from .versioning import (
    DIMENSIONS_NOT_EVALUATED_V1,
    MAX_DIMENSION_ID,
    MIN_DIMENSION_ID,
    MIN_SEVERITY_BASIS_LENGTH,
)


# =============================================================================
# CheckStatus enum (per v0.1 § 1.3)
# =============================================================================

class CheckStatus(StrEnum):
    """Per v0.1 § 1.3.

    The outcome of one check against one candidate. Per Inv P12 every
    registered check produces exactly one outcome; per A5 NOT_APPLICABLE
    outcomes route to ProblemReport.deferred_checks while PASS/WARN/FAIL
    outcomes route to ProblemReport.applicable_checks.

    Values:
      PASS: check ran and the layout satisfies it.
      WARN: check ran and the layout is borderline / a concern but
        not a hard fail. UX may render as yellow.
      FAIL: check ran and the layout violates it. UX render depends
        on epistemic_kind (regulatory FAIL = blocking; cultural_preference
        FAIL = "your family may have a preference here").
      NOT_APPLICABLE: check could not run — data dependency missing,
        cultural-profile mismatch, or scope-out (e.g., 2-room degenerate
        case for a multi-bedroom check). Inv P6 mandates a populated
        na_reason on every NOT_APPLICABLE record.

    A future v1.x may add `DEPRECATED` (Inv P14 ID stability →
    deprecated check_ids retain their IDs with deprecated status; per
    B-C15-DEPRECATED-STATUS post-LOCK polish backlog).
    """
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


# =============================================================================
# CheckSeverity enum (per v0.1 § 1.3)
# =============================================================================

class CheckSeverity(StrEnum):
    """Per v0.1 § 1.3.

    The severity of a check finding. Assigned by C15's severity-rule
    table (per Inv P8 + P15), NOT by the check itself. The mapping
    `(check_id, status, cultural_profile) → severity` is stable per
    Inv P15; changes bump C15_CHECK_REGISTRY_VERSION.

    Values:
      CRITICAL: safety, NBC compliance, structural concerns. Failing
        is non-negotiable. UX should make this prominent and blocking.
      IMPORTANT: significant lived-quality concern. Most users will
        care. UX shows as a clear concern but allows override.
      NICE_TO_HAVE: preference / optimization. Depends on user
        priorities. UX shows as advisory.

    Per v0.2 A2, severity is INDEPENDENT of epistemic_kind. A check
    can be epistemic_kind=cultural_preference with severity=IMPORTANT
    (e.g., a dedicated pooja room may be IMPORTANT under the Tamil
    multigenerational profile despite being culturally-rooted rather
    than regulatory).

    The CRITICAL severity does NOT imply REGULATORY epistemic_kind, nor
    vice versa. They are orthogonal axes — by design (A2 reviewer item
    3 specifically targets the confusion of "FAIL == defect").
    """
    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"


# =============================================================================
# CheckEpistemicKind enum (per v0.2 A2)
# =============================================================================

class CheckEpistemicKind(StrEnum):
    """Per v0.2 A2 (origin: reviewer items 2, 3, 12).

    Distinguishes the EPISTEMIC BASIS of a check. v0.1's ProblemCheck
    had status + severity but no signal distinguishing regulatory
    from cultural-preference checks. The reviewer correctly observed
    that this enables the "FAIL = objective defect" misreading.

    With this field, "bedroom below NBC minimum area" (REGULATORY,
    FAIL+CRITICAL) and "pooja room visual privacy" (CULTURAL_PREFERENCE,
    FAIL+IMPORTANT) can be visually distinguished by UX even though
    both are FAILs.

    Values:
      REGULATORY: Backed by codified law/standard: NBC India 2016,
        IS 456, IS 962, IS 11268, TNCDBR, etc. Failing has regulatory
        force. UX render: blocking / "this needs to be addressed for
        permit compliance."
      ARCHITECTURAL_HEURISTIC: Backed by published architectural design
        literature: Neufert, Ching, Hillier 1984/1987, residential POE
        corpus. Failing is a design concern grounded in evidence but
        not legally binding. UX render: "consider this — design
        literature suggests..."
      CULTURAL_PREFERENCE: Backed by cultural conventions tagged to
        the current cultural_profile. Indian residential context
        examples: dedicated pooja room, dining/kitchen separation,
        multigenerational privacy norms. Failing is a preference, not
        a defect. UX render: "your family may have a preference here."

    Each check_id in the registry has its epistemic_kind defined as a
    STABLE part of the check (Inv P15). The same check NEVER changes
    kind across versions — if the kind needs to change, the check is
    deprecated and a new check_id is introduced (per § 1.5
    numbering rules).
    """
    REGULATORY = "regulatory"
    ARCHITECTURAL_HEURISTIC = "architectural_heuristic"
    CULTURAL_PREFERENCE = "cultural_preference"


# =============================================================================
# Check ID format (per v0.1 § 1.5)
# =============================================================================

# Stable check IDs: P{dimension_id}.{check_index_within_dimension}
# - dimension_id: 1..10
# - check_index: 1..N within that dimension
# Examples: P1.1, P2.3, P10.5
_CHECK_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^P([1-9]|10)\.[1-9][0-9]*$"
)


def _validate_check_id(check_id: str, *, field_context: str) -> int:
    """Validate a check_id string and return the dimension_id.

    Per v0.1 § 1.5 numbering rules:
    - Pattern: P{1..10}.{1..N}
    - Once assigned, a check_id NEVER changes meaning (Inv P15).
    - Cross-dimension renumbering FORBIDDEN.

    Returns the dimension_id (1..10) parsed from the ID.

    Raises ValueError on malformed input. Callers wrap this in their
    domain-specific __post_init__.
    """
    if not isinstance(check_id, str):
        raise TypeError(
            f"{field_context} check_id must be str; got {type(check_id)}"
        )
    if not _CHECK_ID_PATTERN.match(check_id):
        raise ValueError(
            f"{field_context} check_id {check_id!r} violates the "
            f"P{{dimension_id}}.{{check_index}} format per v0.1 § 1.5. "
            f"Examples of valid IDs: P1.1, P2.3, P10.5."
        )
    # Extract dimension_id (the part between 'P' and the first '.').
    dim_str = check_id[1:].split(".", 1)[0]
    return int(dim_str)


# =============================================================================
# CoverageQuality enum (per v0.3 A12)
# =============================================================================

class CoverageQuality(StrEnum):
    """Per v0.3 A12 (deferred from S48 critique walks; landed via Path A).

    Report-level coverage signal. Distinguishes 'we evaluated most of
    the design space' from 'we could only see a fraction'.

    NOT a quality-of-layout signal. A quality-of-evaluation signal.

    Surfacing mandatory in UX render (per Design Principles v3.1
    Principle 5: confidence indicators).

    Derivation rule (per spec § 14.3, NEW):
      ratio = n_applicable / (n_applicable + n_deferred + n_unseen)
      where n_unseen = sum of v1-spec-defined check counts for each
      dimension in dimensions_not_evaluated.

      ratio >= 0.70 → HIGH
      0.40 <= ratio < 0.70 → MEDIUM
      ratio < 0.40 OR total == 0 → LOW

    Moat compliance: ratio is the ratio_applicable: float field on
    ProblemReport. It is DOCUMENTED-AS-EXCEPTION in moat_lint.py
    because (a) it measures coverage-of-evaluation, not
    quality-of-layout; (b) it is derived from registry + upstream
    data shape, never from per-check outputs; (c) it has a closed
    deterministic formula that never reads check status/severity.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# =============================================================================
# DimensionMaturity enum (per v0.3 A12, absorbs B-C15-DIMENSION-MATURITY-METADATA)
# =============================================================================

class DimensionMaturity(StrEnum):
    """Per v0.3 A12. Absorbs B-C15-DIMENSION-MATURITY-METADATA
    (S48 critique walk #1 item 6).

    Per-dimension structural maturity at the C15 v1 envelope. Surfaces
    the structural asymmetry that engine is stronger in
    geometry/privacy/flow (dims 1/2/3/5) than light/storage/adaptability
    (dims 4/8/9/10) — not philosophically, structurally.

    Computed from registered check status × emitted DeferredCheck count
    per dimension. Deterministic and replay-stable.

    Values:
      RUNNABLE: all registered checks for this dim produced
        applicable (PASS/WARN/FAIL) outcomes on this candidate.
      PARTIAL: some checks runnable, some deferred for upstream
        data reasons (e.g., dim 7 has 3 PARTIAL-RUNNABLE checks
        that need floor_metadata + 1 always-DEFERRED check).
      NOT_RUNNABLE: ALL checks for this dim emitted NOT_APPLICABLE
        on this candidate (e.g., dim 4 Natural Light has zero
        runnable checks at v1 — placeholder for upstream
        extensions).

    Derivation rule (per spec § 14.3, NEW):
      n_app == 0 AND n_def > 0 → NOT_RUNNABLE
      n_app > 0 AND n_def == 0 → RUNNABLE
      n_app > 0 AND n_def > 0  → PARTIAL
      n_app == 0 AND n_def == 0 → NOT_RUNNABLE
        (dim emitted nothing — shouldn't happen given Inv P12, but
         defensive).
    """
    RUNNABLE = "RUNNABLE"
    PARTIAL = "PARTIAL"
    NOT_RUNNABLE = "NOT_RUNNABLE"


def _derive_dim_maturity(n_app: int, n_def: int) -> "DimensionMaturity":
    """Per v0.3 A12 spec § 14.3. Deterministic; replay-stable.
    Module-level so registry/orchestrator can call without cycle."""
    if n_app > 0 and n_def == 0:
        return DimensionMaturity.RUNNABLE
    if n_app > 0 and n_def > 0:
        return DimensionMaturity.PARTIAL
    return DimensionMaturity.NOT_RUNNABLE


def _derive_coverage_quality(
    dim_summaries: "tuple[DimensionSummary, ...]",
) -> "tuple[CoverageQuality, float]":
    """Per v0.3 A12 § 14.3 derivation rule. Deterministic;
    replay-stable.

    Numerator: sum(n_applicable across dim_summaries).
    Denominator: sum(n_applicable + n_deferred across dim_summaries).

    Inv P12 guarantees the denominator equals total registered checks
    (41 at v1). The `dimensions_not_evaluated` field is a SEPARATE
    out-of-scope disclosure and is NOT part of the coverage ratio
    (those categories aren't in the registry).

    Ratio thresholds: ≥0.70 HIGH, ≥0.40 MEDIUM, else LOW.
    Total==0 edge case → LOW with ratio=0.0.
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


# =============================================================================
# SeverityRule (per v0.2 A4)
# =============================================================================

@dataclass(frozen=True)
class SeverityRule:
    """Per v0.2 A4. A single (check_id, status, cultural_profile) →
    severity mapping with a CITED basis.

    The severity assignment is political — encoding regulatory, class,
    cultural, and lifestyle assumptions. v0.1's centralization
    concentrated that bias invisibly. v0.2 A4 makes the basis
    AUDITABLE by requiring a citation per rule.

    Fields:
      check_id: the check this rule applies to. Must match the
        P{dimension}.{check_index} format.
      status: the CheckStatus this rule maps from.
      cultural_profile: optional. None means the rule applies to all
        profiles. A specific profile means this rule only applies when
        that profile is active.
      severity: the assigned severity.
      severity_basis: REQUIRED citation. Per Inv P18, minimum
        MIN_SEVERITY_BASIS_LENGTH (20) characters. Examples:
        - "NBC India 2016 §6.2.1 (minimum bedroom area)"
        - "Neufert 4th ed, p.78 (shower wall-mount ergonomics)"
        - "Cultural convention: Tamil pooja room visibility norms,
           per Karthikeyan 2017"

    Empty or short severity_basis fails registration with
    ValueError (which the registry loader will wrap as
    CheckRegistryError per Inv P18).

    Frozen + hashable. The rule table's CONTENT hash contributes to
    cache keys (cache-relevant per A4).
    """
    check_id: str
    status: CheckStatus
    cultural_profile: Optional[CulturalProfile]
    severity: CheckSeverity
    severity_basis: str

    def __post_init__(self) -> None:
        # check_id format validation.
        _validate_check_id(self.check_id, field_context="SeverityRule")

        # status must be a CheckStatus member.
        if not isinstance(self.status, CheckStatus):
            raise TypeError(
                f"SeverityRule.status must be CheckStatus; "
                f"got {type(self.status)}"
            )
        # NOT_APPLICABLE outcomes route to DeferredCheck per A5;
        # severity-grading them is meaningless and structurally wrong.
        if self.status is CheckStatus.NOT_APPLICABLE:
            raise CheckRegistryError(
                f"SeverityRule.status cannot be NOT_APPLICABLE; per A5, "
                f"NOT_APPLICABLE outcomes route to DeferredCheck (no "
                f"severity grade). Offender: {self.check_id!r}"
            )

        # cultural_profile may be None OR a CulturalProfile member.
        if (
            self.cultural_profile is not None
            and not isinstance(self.cultural_profile, CulturalProfile)
        ):
            raise TypeError(
                f"SeverityRule.cultural_profile must be CulturalProfile "
                f"or None; got {type(self.cultural_profile)}"
            )

        # severity must be a CheckSeverity member.
        if not isinstance(self.severity, CheckSeverity):
            raise TypeError(
                f"SeverityRule.severity must be CheckSeverity; "
                f"got {type(self.severity)}"
            )

        # severity_basis: REQUIRED, min length per Inv P18.
        # Per A4 LOCKED: violations raise CheckRegistryError (not
        # ValueError) — they're registry-build defects that must
        # halt LOCAL load, distinct from per-candidate input issues.
        if not isinstance(self.severity_basis, str):
            raise TypeError(
                f"SeverityRule.severity_basis must be str; "
                f"got {type(self.severity_basis)}"
            )
        if len(self.severity_basis) < MIN_SEVERITY_BASIS_LENGTH:
            raise CheckRegistryError(
                f"SeverityRule.severity_basis violates Inv P18 — "
                f"must be at least {MIN_SEVERITY_BASIS_LENGTH} chars; "
                f"got {len(self.severity_basis)} chars: "
                f"{self.severity_basis!r}"
            )


# =============================================================================
# ProblemCheck (per v0.1 § 1.3 + v0.2 A2)
# =============================================================================

@dataclass(frozen=True)
class ProblemCheck:
    """Per v0.1 § 1.3 + v0.2 A2.

    One check's outcome for one candidate, status ∈ {PASS, WARN, FAIL}.
    NOT_APPLICABLE outcomes route to DeferredCheck per A5 — they do
    NOT appear here.

    Fields:
      check_id: stable ID per § 1.5 (P{dimension}.{check_index}).
      dimension_id: 1..10 (per § 1.4). Must equal the dimension parsed
        from check_id (consistency check at __post_init__).
      status: PASS / WARN / FAIL. NOT_APPLICABLE rejected — use
        DeferredCheck instead.
      severity: assigned by the severity-rule table (Inv P8 + P15).
        Severity is INDEPENDENT of epistemic_kind (per A2 note).
      epistemic_kind: REGULATORY / ARCHITECTURAL_HEURISTIC /
        CULTURAL_PREFERENCE. Per A2, stable per check_id (Inv P15).
      affected_room_ids: tuple, sorted lex-ASC (Inv P7). Subset of the
        candidate's placed_room_ids (orchestrator verifies).
      rule_citation: NBC clause / Neufert page / design heuristic
        source for this CHECK (distinct from severity_basis — which
        cites the SEVERITY ASSIGNMENT specifically; per A4).
      why_it_matters: 1-2 sentence consumer-readable text. UX renders.
      suggested_mitigation: optional textual hint. None when no
        useful hint can be offered (better to be silent than
        prescriptive when uncertain).
      measurement: optional structured measurement (e.g.,
        {"shower_length_m": 0.85}) for debugging / UX detail.

    Frozen. Hashable. Replay-stable (Inv P2 byte-equal).

    Per Inv P0 (v0.2 A1 STRICTER): no method on ProblemCheck returns
    a numeric "quality score" derived from status/severity. The check
    is a DESCRIPTIVE record, not an aggregation input.
    """
    check_id: str
    dimension_id: int
    status: CheckStatus
    severity: CheckSeverity
    epistemic_kind: CheckEpistemicKind
    affected_room_ids: tuple[str, ...]
    rule_citation: str
    why_it_matters: str
    suggested_mitigation: Optional[str]
    measurement: Optional[dict[str, float | int | str]] = None

    def __post_init__(self) -> None:
        # check_id format + dimension consistency.
        parsed_dim = _validate_check_id(
            self.check_id, field_context="ProblemCheck"
        )

        # dimension_id type + range.
        if not isinstance(self.dimension_id, int) or isinstance(
            self.dimension_id, bool
        ):
            raise TypeError(
                f"ProblemCheck.dimension_id must be int (not bool); "
                f"got {type(self.dimension_id)}"
            )
        if not (MIN_DIMENSION_ID <= self.dimension_id <= MAX_DIMENSION_ID):
            raise ValueError(
                f"ProblemCheck.dimension_id must be in "
                f"[{MIN_DIMENSION_ID}, {MAX_DIMENSION_ID}]; "
                f"got {self.dimension_id}"
            )
        if self.dimension_id != parsed_dim:
            raise ValueError(
                f"ProblemCheck.dimension_id ({self.dimension_id}) "
                f"disagrees with dimension parsed from check_id "
                f"{self.check_id!r} (which is {parsed_dim})"
            )

        # status: must be PASS / WARN / FAIL. NOT_APPLICABLE rejected
        # because A5 routes those to DeferredCheck.
        if not isinstance(self.status, CheckStatus):
            raise TypeError(
                f"ProblemCheck.status must be CheckStatus; "
                f"got {type(self.status)}"
            )
        if self.status is CheckStatus.NOT_APPLICABLE:
            raise ValueError(
                "ProblemCheck.status cannot be NOT_APPLICABLE; per v0.2 "
                "A5, not-applicable outcomes route to DeferredCheck, "
                "not ProblemCheck."
            )

        # severity: must be CheckSeverity.
        if not isinstance(self.severity, CheckSeverity):
            raise TypeError(
                f"ProblemCheck.severity must be CheckSeverity; "
                f"got {type(self.severity)}"
            )

        # epistemic_kind: must be CheckEpistemicKind (per A2).
        if not isinstance(self.epistemic_kind, CheckEpistemicKind):
            raise TypeError(
                f"ProblemCheck.epistemic_kind must be CheckEpistemicKind "
                f"(per v0.2 A2); got {type(self.epistemic_kind)}"
            )

        # affected_room_ids: tuple of unique non-empty strings, sorted
        # lex-ASC (Inv P7). Empty tuple is permitted for layout-wide
        # checks (e.g., FAR utilization — applies to whole layout, not
        # specific rooms).
        if not isinstance(self.affected_room_ids, tuple):
            raise TypeError(
                f"ProblemCheck.affected_room_ids must be tuple; "
                f"got {type(self.affected_room_ids)}"
            )
        for rid in self.affected_room_ids:
            if not isinstance(rid, str) or not rid:
                raise ValueError(
                    f"ProblemCheck.affected_room_ids must contain "
                    f"non-empty strings; got {self.affected_room_ids!r}"
                )
        if list(self.affected_room_ids) != sorted(self.affected_room_ids):
            raise ValueError(
                f"ProblemCheck.affected_room_ids must be sorted lex-ASC "
                f"(Inv P7); got {self.affected_room_ids!r}"
            )
        if len(set(self.affected_room_ids)) != len(self.affected_room_ids):
            raise ValueError(
                f"ProblemCheck.affected_room_ids must be unique; "
                f"got {self.affected_room_ids!r}"
            )

        # rule_citation: REQUIRED, non-empty.
        if not isinstance(self.rule_citation, str):
            raise TypeError(
                f"ProblemCheck.rule_citation must be str; "
                f"got {type(self.rule_citation)}"
            )
        if not self.rule_citation:
            raise ValueError(
                "ProblemCheck.rule_citation must be non-empty — every "
                "check must cite its rule source"
            )

        # why_it_matters: REQUIRED, non-empty.
        if not isinstance(self.why_it_matters, str):
            raise TypeError(
                f"ProblemCheck.why_it_matters must be str; "
                f"got {type(self.why_it_matters)}"
            )
        if not self.why_it_matters:
            raise ValueError(
                "ProblemCheck.why_it_matters must be non-empty"
            )

        # suggested_mitigation: None OR non-empty string.
        if self.suggested_mitigation is not None:
            if not isinstance(self.suggested_mitigation, str):
                raise TypeError(
                    f"ProblemCheck.suggested_mitigation must be str or "
                    f"None; got {type(self.suggested_mitigation)}"
                )
            if not self.suggested_mitigation:
                raise ValueError(
                    "ProblemCheck.suggested_mitigation must be None or "
                    "non-empty (don't pass empty string)"
                )

        # measurement: None OR dict[str, float|int|str].
        if self.measurement is not None:
            if not isinstance(self.measurement, dict):
                raise TypeError(
                    f"ProblemCheck.measurement must be dict or None; "
                    f"got {type(self.measurement)}"
                )
            for k, v in self.measurement.items():
                if not isinstance(k, str) or not k:
                    raise ValueError(
                        f"ProblemCheck.measurement keys must be "
                        f"non-empty str; got key {k!r}"
                    )
                # bool is allowed by int (subclass); we reject it
                # explicitly since {"is_ground": True} is not a
                # measurement, it's a flag.
                if isinstance(v, bool):
                    raise TypeError(
                        f"ProblemCheck.measurement values must be "
                        f"float/int/str, not bool; got bool for key {k!r}"
                    )
                if not isinstance(v, (float, int, str)):
                    raise TypeError(
                        f"ProblemCheck.measurement values must be "
                        f"float/int/str; got {type(v)} for key {k!r}"
                    )


# =============================================================================
# DeferredCheck (per v0.2 A5)
# =============================================================================

@dataclass(frozen=True)
class DeferredCheck:
    """Per v0.2 A5.

    A check that emitted NOT_APPLICABLE because its data dependency
    was missing. Routes to ProblemReport.deferred_checks — NOT
    counted alongside applicable_checks in status summaries.

    UX renders deferred_checks as: "Checks deferred — missing
    upstream data: [list]" → presented as "future improvement"
    rather than current concern.

    Fields:
      check_id: stable ID per § 1.5.
      dimension_id: 1..10.
      na_reason: structured reason. Examples:
        - "window_data_unavailable"
        - "furniture_fit_data_unavailable"
        - "floor_metadata_unavailable"
        - "envelope_orientation_unavailable"
        - "cultural_profile_mismatch"
        - "scope_out_degenerate_room_count"
      blocking_backlog_item: the B-NNN backlog entry that, when closed,
        unblocks this check. UX may link to it. Empty string permitted
        when the deferral isn't tracking a specific backlog item
        (e.g., scope-out cases).

    Frozen + hashable. DeferredCheck is intentionally LIGHTER than
    ProblemCheck — it has no severity, no rule_citation, no
    suggested_mitigation. It says "we'd check this but can't," not
    "here's a finding."
    """
    check_id: str
    dimension_id: int
    na_reason: str
    blocking_backlog_item: str

    def __post_init__(self) -> None:
        # check_id format + dimension consistency.
        parsed_dim = _validate_check_id(
            self.check_id, field_context="DeferredCheck"
        )

        if not isinstance(self.dimension_id, int) or isinstance(
            self.dimension_id, bool
        ):
            raise TypeError(
                f"DeferredCheck.dimension_id must be int (not bool); "
                f"got {type(self.dimension_id)}"
            )
        if not (MIN_DIMENSION_ID <= self.dimension_id <= MAX_DIMENSION_ID):
            raise ValueError(
                f"DeferredCheck.dimension_id must be in "
                f"[{MIN_DIMENSION_ID}, {MAX_DIMENSION_ID}]; "
                f"got {self.dimension_id}"
            )
        if self.dimension_id != parsed_dim:
            raise ValueError(
                f"DeferredCheck.dimension_id ({self.dimension_id}) "
                f"disagrees with dimension parsed from check_id "
                f"{self.check_id!r} (which is {parsed_dim})"
            )

        # na_reason: REQUIRED non-empty (Inv P6).
        if not isinstance(self.na_reason, str):
            raise TypeError(
                f"DeferredCheck.na_reason must be str; "
                f"got {type(self.na_reason)}"
            )
        if not self.na_reason:
            raise ValueError(
                "DeferredCheck.na_reason must be non-empty per Inv P6"
            )

        # blocking_backlog_item: str (may be empty for scope-out cases).
        if not isinstance(self.blocking_backlog_item, str):
            raise TypeError(
                f"DeferredCheck.blocking_backlog_item must be str; "
                f"got {type(self.blocking_backlog_item)}"
            )


# =============================================================================
# UnconventionalPatternHint (per v0.2 A7)
# =============================================================================

# The five v1 detection-pattern names (per A7). Stable strings —
# part of the report contract. Pinned by
# B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK (LOCK-mandatory, v1.0).
UNCONVENTIONAL_PATTERN_NAMES: Final[frozenset[str]] = frozenset({
    "courtyard_centered",
    "split_level_circulation",
    "ritual_procession",
    "compact_incremental",
    "multigenerational_segregation",
})
"""Per v0.2 A7. The five v1 pattern names C15 detects.

Detection rules at v1 (sketch, refined by walks):
- courtyard_centered: > 3 habitable rooms with primary adjacency to a
  single non-habitable central room (the courtyard).
- split_level_circulation: floor metadata indicates non-zero z-offset
  between adjacent rooms on same nominal floor.
- ritual_procession: graph path from entry shows monotonic step-depth
  increase through ≥ 4 rooms with explicit ritual-category rooms.
- compact_incremental: total carpet area < 600 sqft AND room count ≥ 4.
- multigenerational_segregation: ≥ 2 master-class bedrooms separated
  by step-depth ≥ 3.

When ANY pattern is detected, UX presents the report with a banner
reducing confidence on the flagged check_ids.
"""


@dataclass(frozen=True)
class UnconventionalPatternHint:
    """Per v0.2 A7.

    Signals that a layout shows unconventional patterns C15's standard
    checks may incorrectly flag. UX renders the affected checks
    "with reduced confidence."

    Fields:
      detected: True iff at least one pattern was detected.
      suspected_patterns: tuple of pattern names from
        UNCONVENTIONAL_PATTERN_NAMES, sorted lex-ASC. Empty iff
        detected=False.
      confidence_caveat: consumer-readable explanatory note. Required
        non-empty iff detected=True; empty string iff detected=False
        (orchestrator constructs the appropriate caveat).
      affected_check_ids: which checks should be presented with
        reduced confidence. Sorted lex-ASC. May be empty if the
        pattern is informational only (e.g., compact_incremental
        flags the whole report's audience, not specific checks).

    Frozen + hashable. Replay-stable.
    """
    detected: bool
    suspected_patterns: tuple[str, ...]
    confidence_caveat: str
    affected_check_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        # detected: bool only.
        if not isinstance(self.detected, bool):
            raise TypeError(
                f"UnconventionalPatternHint.detected must be bool; "
                f"got {type(self.detected)}"
            )

        # suspected_patterns: tuple of strings, sorted lex-ASC, unique,
        # all from UNCONVENTIONAL_PATTERN_NAMES.
        if not isinstance(self.suspected_patterns, tuple):
            raise TypeError(
                f"UnconventionalPatternHint.suspected_patterns must be "
                f"tuple; got {type(self.suspected_patterns)}"
            )
        for p in self.suspected_patterns:
            if not isinstance(p, str):
                raise TypeError(
                    f"UnconventionalPatternHint.suspected_patterns "
                    f"entries must be str; got {type(p)}"
                )
            if p not in UNCONVENTIONAL_PATTERN_NAMES:
                raise ValueError(
                    f"UnconventionalPatternHint.suspected_patterns "
                    f"entry {p!r} not in registered pattern names; "
                    f"valid: {sorted(UNCONVENTIONAL_PATTERN_NAMES)!r}"
                )
        if list(self.suspected_patterns) != sorted(self.suspected_patterns):
            raise ValueError(
                f"UnconventionalPatternHint.suspected_patterns must be "
                f"sorted lex-ASC; got {self.suspected_patterns!r}"
            )
        if len(set(self.suspected_patterns)) != len(self.suspected_patterns):
            raise ValueError(
                f"UnconventionalPatternHint.suspected_patterns must be "
                f"unique; got {self.suspected_patterns!r}"
            )

        # detected vs suspected_patterns consistency.
        if self.detected and not self.suspected_patterns:
            raise ValueError(
                "UnconventionalPatternHint: detected=True requires "
                "non-empty suspected_patterns"
            )
        if not self.detected and self.suspected_patterns:
            raise ValueError(
                "UnconventionalPatternHint: detected=False requires "
                "empty suspected_patterns"
            )

        # confidence_caveat: str. Required non-empty iff detected.
        if not isinstance(self.confidence_caveat, str):
            raise TypeError(
                f"UnconventionalPatternHint.confidence_caveat must be "
                f"str; got {type(self.confidence_caveat)}"
            )
        if self.detected and not self.confidence_caveat:
            raise ValueError(
                "UnconventionalPatternHint: detected=True requires "
                "non-empty confidence_caveat"
            )
        if not self.detected and self.confidence_caveat:
            raise ValueError(
                "UnconventionalPatternHint: detected=False requires "
                "empty confidence_caveat (orchestrator constructs "
                "appropriate value)"
            )

        # affected_check_ids: tuple of valid check_ids, sorted lex-ASC,
        # unique. May be empty.
        if not isinstance(self.affected_check_ids, tuple):
            raise TypeError(
                f"UnconventionalPatternHint.affected_check_ids must be "
                f"tuple; got {type(self.affected_check_ids)}"
            )
        for cid in self.affected_check_ids:
            _validate_check_id(
                cid, field_context="UnconventionalPatternHint"
            )
        if list(self.affected_check_ids) != sorted(self.affected_check_ids):
            raise ValueError(
                f"UnconventionalPatternHint.affected_check_ids must be "
                f"sorted lex-ASC; got {self.affected_check_ids!r}"
            )
        if len(set(self.affected_check_ids)) != len(
            self.affected_check_ids
        ):
            raise ValueError(
                f"UnconventionalPatternHint.affected_check_ids must be "
                f"unique; got {self.affected_check_ids!r}"
            )


# =============================================================================
# DimensionSummary (per v0.2 A10 — restructured from v0.1)
# =============================================================================

@dataclass(frozen=True)
class DimensionSummary:
    """Per v0.2 A10 (origin: self-analysis (c) + reviewer item 6).

    v0.1's summary `(dimension_id, n_pass, n_warn, n_fail, n_na)`
    invited score-by-arithmetic. v0.2 A10 splits data availability
    (n_applicable, n_deferred) from within-applicable status
    (n_pass, n_warn, n_fail) — making aggregate-scoring awkward.

    UX consumers render two separate visualizations:
    - Data coverage: "8 of 10 checks ran (80% applicable)"
    - Within-applicable: "Of 8 applicable, 6 pass, 1 warn, 1 fail"

    But NOT: "60% overall quality." The structural split prevents the
    incidental score-by-arithmetic that v0.1 invited.

    Fields:
      dimension_id: 1..10.
      dimension_name: human-readable label (e.g., "Logical flow").
        Stable per dimension_id; embedded in registry. UX renders this.

      n_applicable: how many checks in this dimension produced an
        applicable outcome (PASS/WARN/FAIL).
      n_deferred: how many emitted NOT_APPLICABLE (→ DeferredCheck).

      n_pass: applicable-and-PASS count.
      n_warn: applicable-and-WARN count.
      n_fail: applicable-and-FAIL count.

    Invariants enforced at __post_init__:
    - n_pass + n_warn + n_fail == n_applicable
    - Every count is non-negative.
    - dimension_id in legal range.
    - dimension_name non-empty.

    Per Inv P0: this dataclass exposes COUNTS only. No weighted sum,
    no ratio, no "score" field. Counts are descriptive, not
    aggregative.
    """
    dimension_id: int
    dimension_name: str
    n_applicable: int
    n_deferred: int
    n_pass: int
    n_warn: int
    n_fail: int
    maturity: "DimensionMaturity"
    """v0.3 A12 (absorbs B-C15-DIMENSION-MATURITY-METADATA). Surfaces
    per-dimension structural maturity. Computed from n_applicable +
    n_deferred via _derive_dim_maturity. NOT a quality signal;
    a coverage signal."""

    def __post_init__(self) -> None:
        if not isinstance(self.dimension_id, int) or isinstance(
            self.dimension_id, bool
        ):
            raise TypeError(
                f"DimensionSummary.dimension_id must be int (not bool); "
                f"got {type(self.dimension_id)}"
            )
        if not (MIN_DIMENSION_ID <= self.dimension_id <= MAX_DIMENSION_ID):
            raise ValueError(
                f"DimensionSummary.dimension_id must be in "
                f"[{MIN_DIMENSION_ID}, {MAX_DIMENSION_ID}]; "
                f"got {self.dimension_id}"
            )

        if not isinstance(self.dimension_name, str):
            raise TypeError(
                f"DimensionSummary.dimension_name must be str; "
                f"got {type(self.dimension_name)}"
            )
        if not self.dimension_name:
            raise ValueError(
                "DimensionSummary.dimension_name must be non-empty"
            )

        # All counts non-negative ints (not bool).
        for fname in (
            "n_applicable", "n_deferred", "n_pass", "n_warn", "n_fail",
        ):
            v = getattr(self, fname)
            if not isinstance(v, int) or isinstance(v, bool):
                raise TypeError(
                    f"DimensionSummary.{fname} must be int (not bool); "
                    f"got {type(v)}"
                )
            if v < 0:
                raise ValueError(
                    f"DimensionSummary.{fname} must be non-negative; "
                    f"got {v}"
                )

        # Invariant: n_pass + n_warn + n_fail == n_applicable.
        if self.n_pass + self.n_warn + self.n_fail != self.n_applicable:
            raise ValueError(
                f"DimensionSummary invariant violation per v0.2 A10: "
                f"n_pass ({self.n_pass}) + n_warn ({self.n_warn}) + "
                f"n_fail ({self.n_fail}) = "
                f"{self.n_pass + self.n_warn + self.n_fail}, must equal "
                f"n_applicable ({self.n_applicable})"
            )

        # v0.3 A12: maturity must be DimensionMaturity AND must match
        # the derivation from (n_applicable, n_deferred). Crosscheck
        # ensures construction sites stay honest — a constructor that
        # passes maturity=RUNNABLE while n_deferred > 0 is a bug.
        if not isinstance(self.maturity, DimensionMaturity):
            raise TypeError(
                f"DimensionSummary.maturity must be DimensionMaturity "
                f"(v0.3 A12); got {type(self.maturity)}"
            )
        expected_maturity = _derive_dim_maturity(
            self.n_applicable, self.n_deferred
        )
        if self.maturity is not expected_maturity:
            raise ValueError(
                f"DimensionSummary.maturity ({self.maturity}) does not "
                f"match derivation from "
                f"(n_applicable={self.n_applicable}, "
                f"n_deferred={self.n_deferred}); "
                f"expected {expected_maturity} per v0.3 A12 § 14.3 "
                f"derivation rule"
            )


# =============================================================================
# ProblemReport (per v0.1 § 1.2 + v0.2 A1/A2/A3/A5/A6/A7/A10)
# =============================================================================

# Phase enum literal for FailureRecord.phase (per v0.1 § 3 phases).
# π = pi, ρ = rho, σ = sigma, τ = tau, υ = upsilon, φ = phi. Spelled
# out for ASCII safety.
PhaseLiteral = Literal["pi", "rho", "sigma", "tau", "upsilon", "phi"]


@dataclass(frozen=True)
class ProblemReport:
    """Per-candidate problem-finding output.

    Per Inv P0 (v0.2 A1 STRICTER): NEVER carries a single quality
    score. The applicable_checks + deferred_checks tuples are the
    deliverable. dimension_summary exposes COUNTS, not scores.

    Per v0.2 A5: applicable_checks + deferred_checks split; deferred
    are NOT mixed in with status summaries.

    Per v0.2 A6: dimensions_not_evaluated enumerates categories C15
    explicitly DOES NOT cover (emotional comfort, acoustic experience,
    etc.). Surfaced at the report level, not buried in spec prose.

    Per v0.2 A7: unconventional_pattern_hint signals when standard
    checks may not apply.

    Per v0.2 A3: cultural_profile_active records which profile was
    used. Auditable.

    Fields:
      source_placed_candidate_signature: provenance back to C13/C14.

      # The deliverable (per A5):
      applicable_checks: tuple of ProblemCheck (status ∈ PASS/WARN/FAIL).
        Sorted lex-ASC by check_id (Inv P3).
      deferred_checks: tuple of DeferredCheck (status = NOT_APPLICABLE).
        Sorted lex-ASC by check_id (Inv P3).

      # Per-dimension breakdown (per A10):
      dimension_summary: tuple of DimensionSummary, one per dimension
        present in the report. Sorted by dimension_id ascending.

      # Incompleteness disclosure (per A6 + Inv P19):
      dimensions_not_evaluated: non-empty tuple (Inv P19) of category
        names C15 doesn't check. Defaults to DIMENSIONS_NOT_EVALUATED_V1
        at the orchestrator level.

      # Unconventional layout warning (per A7):
      unconventional_pattern_hint: always present (may be detected=False).

      # Cultural profile audit trail (per A3):
      cultural_profile_active: which CulturalProfile was active for
        this evaluation.

      # Upstream advisory passthrough (Inv P10, byte-identical):
      # C13/C14 type imports are deferred to orchestrator wiring;
      # at v0.2 LOCK SKETCH the schema accepts tuple[object, ...] so
      # the test layer can construct reports without instantiating
      # actual C13/C14 advisory types. Inv P10 is enforced at
      # orchestrator level (Phase υ) where the tuples are copied
      # byte-identically from upstream.
      c13_advisory_flags: tuple[object, ...]
      c14_structural_flags: tuple[object, ...]
      c14_preference_flags: tuple[object, ...]

      # Provenance triple (Inv P16):
      c15_version: str
      c15_check_registry_version: int
      advisory_schema_version: int

      # Chain-cache key (Inv P14):
      upstream_cache_key: str
        # C14 full_cache_key passthrough — when this changes, our
        # cache invalidates automatically.

    Frozen. Hashable iff all dict-containing fields are frozen/
    hashable (note: ProblemCheck.measurement is dict, which is
    unhashable — so ProblemReport itself is NOT hashable in the
    Python sense. Replay-determinism is still achievable via canonical
    serialization, which the test layer exercises.)
    """
    source_placed_candidate_signature: str

    applicable_checks: tuple[ProblemCheck, ...]
    deferred_checks: tuple[DeferredCheck, ...]

    dimension_summary: tuple[DimensionSummary, ...]

    dimensions_not_evaluated: tuple[str, ...]
    unconventional_pattern_hint: UnconventionalPatternHint
    cultural_profile_active: CulturalProfile

    c13_advisory_flags: tuple[object, ...]
    c14_structural_flags: tuple[object, ...]
    c14_preference_flags: tuple[object, ...]

    c15_version: str
    c15_check_registry_version: int
    advisory_schema_version: int
    upstream_cache_key: str

    # v0.3 A12 (deferred from S48 critique walks; landed via Path A).
    # Coverage-of-evaluation signal. NOT a quality-of-layout signal.
    # See CoverageQuality docstring for moat compliance rationale.
    coverage_quality: CoverageQuality
    """v0.3 A12. HIGH / MEDIUM / LOW per spec § 14.3 derivation."""

    ratio_applicable: float
    """v0.3 A12. Exact ratio in [0.0, 1.0] used to derive
    coverage_quality. Provenance: n_applicable across dimensions
    / (n_applicable + n_deferred + spec-defined check counts for
    dimensions in dimensions_not_evaluated). Moat compliance: this
    float is a coverage-of-evaluation signal, NOT a quality-of-layout
    signal. Documented-as-exception in moat_lint.py PATTERNS."""

    def __post_init__(self) -> None:
        # source signature.
        if not isinstance(self.source_placed_candidate_signature, str):
            raise TypeError(
                f"ProblemReport.source_placed_candidate_signature must "
                f"be str; got "
                f"{type(self.source_placed_candidate_signature)}"
            )
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "ProblemReport.source_placed_candidate_signature must "
                "be non-empty"
            )

        # applicable_checks: tuple, sorted by check_id (Inv P3), unique.
        if not isinstance(self.applicable_checks, tuple):
            raise TypeError(
                f"ProblemReport.applicable_checks must be tuple; "
                f"got {type(self.applicable_checks)}"
            )
        for chk in self.applicable_checks:
            if not isinstance(chk, ProblemCheck):
                raise TypeError(
                    f"ProblemReport.applicable_checks must contain "
                    f"ProblemCheck instances; got {type(chk)}"
                )
        applicable_ids = [c.check_id for c in self.applicable_checks]
        if applicable_ids != sorted(applicable_ids):
            raise ValueError(
                f"ProblemReport.applicable_checks must be sorted "
                f"lex-ASC by check_id (Inv P3); got order {applicable_ids}"
            )
        if len(set(applicable_ids)) != len(applicable_ids):
            raise ValueError(
                f"ProblemReport.applicable_checks contains duplicate "
                f"check_id; ids: {applicable_ids}"
            )

        # deferred_checks: tuple, sorted, unique.
        if not isinstance(self.deferred_checks, tuple):
            raise TypeError(
                f"ProblemReport.deferred_checks must be tuple; "
                f"got {type(self.deferred_checks)}"
            )
        for d in self.deferred_checks:
            if not isinstance(d, DeferredCheck):
                raise TypeError(
                    f"ProblemReport.deferred_checks must contain "
                    f"DeferredCheck instances; got {type(d)}"
                )
        deferred_ids = [d.check_id for d in self.deferred_checks]
        if deferred_ids != sorted(deferred_ids):
            raise ValueError(
                f"ProblemReport.deferred_checks must be sorted lex-ASC "
                f"by check_id (Inv P3); got order {deferred_ids}"
            )
        if len(set(deferred_ids)) != len(deferred_ids):
            raise ValueError(
                f"ProblemReport.deferred_checks contains duplicate "
                f"check_id; ids: {deferred_ids}"
            )

        # No check_id appears in BOTH applicable_checks AND
        # deferred_checks (Inv P12: each registered check produces
        # exactly one record).
        applicable_set = set(applicable_ids)
        for did in deferred_ids:
            if did in applicable_set:
                raise ValueError(
                    f"ProblemReport: check_id {did!r} appears in BOTH "
                    f"applicable_checks and deferred_checks; per "
                    f"Inv P12 each registered check produces exactly "
                    f"one record"
                )

        # dimension_summary: tuple of DimensionSummary, dimension_ids
        # unique, sorted ascending by dimension_id.
        if not isinstance(self.dimension_summary, tuple):
            raise TypeError(
                f"ProblemReport.dimension_summary must be tuple; "
                f"got {type(self.dimension_summary)}"
            )
        for ds in self.dimension_summary:
            if not isinstance(ds, DimensionSummary):
                raise TypeError(
                    f"ProblemReport.dimension_summary must contain "
                    f"DimensionSummary instances; got {type(ds)}"
                )
        dim_ids = [ds.dimension_id for ds in self.dimension_summary]
        if dim_ids != sorted(dim_ids):
            raise ValueError(
                f"ProblemReport.dimension_summary must be sorted by "
                f"dimension_id ascending; got {dim_ids}"
            )
        if len(set(dim_ids)) != len(dim_ids):
            raise ValueError(
                f"ProblemReport.dimension_summary contains duplicate "
                f"dimension_id; ids: {dim_ids}"
            )

        # Inv P9 (dimension_summary counts agree with checks breakdown):
        # For each dimension represented in dim_summary, the counts
        # must match the actual content of applicable_checks and
        # deferred_checks for that dimension.
        applicable_by_dim: dict[int, dict[str, int]] = {}
        for chk in self.applicable_checks:
            d = applicable_by_dim.setdefault(
                chk.dimension_id, {"pass": 0, "warn": 0, "fail": 0}
            )
            if chk.status is CheckStatus.PASS:
                d["pass"] += 1
            elif chk.status is CheckStatus.WARN:
                d["warn"] += 1
            elif chk.status is CheckStatus.FAIL:
                d["fail"] += 1
            else:
                # ProblemCheck.__post_init__ already rejects
                # NOT_APPLICABLE here, but defensive.
                raise ValueError(
                    f"ProblemReport: unexpected check status "
                    f"{chk.status!r} in applicable_checks"
                )
        deferred_by_dim: dict[int, int] = {}
        for d in self.deferred_checks:
            deferred_by_dim[d.dimension_id] = (
                deferred_by_dim.get(d.dimension_id, 0) + 1
            )
        for ds in self.dimension_summary:
            expected_breakdown = applicable_by_dim.get(
                ds.dimension_id, {"pass": 0, "warn": 0, "fail": 0}
            )
            expected_deferred = deferred_by_dim.get(ds.dimension_id, 0)
            if ds.n_pass != expected_breakdown["pass"]:
                raise ValueError(
                    f"ProblemReport Inv P9 violation: "
                    f"dimension_summary[dim={ds.dimension_id}].n_pass = "
                    f"{ds.n_pass} but actual count in applicable_checks "
                    f"is {expected_breakdown['pass']}"
                )
            if ds.n_warn != expected_breakdown["warn"]:
                raise ValueError(
                    f"ProblemReport Inv P9 violation: "
                    f"dimension_summary[dim={ds.dimension_id}].n_warn = "
                    f"{ds.n_warn} but actual count in applicable_checks "
                    f"is {expected_breakdown['warn']}"
                )
            if ds.n_fail != expected_breakdown["fail"]:
                raise ValueError(
                    f"ProblemReport Inv P9 violation: "
                    f"dimension_summary[dim={ds.dimension_id}].n_fail = "
                    f"{ds.n_fail} but actual count in applicable_checks "
                    f"is {expected_breakdown['fail']}"
                )
            if ds.n_applicable != (
                expected_breakdown["pass"]
                + expected_breakdown["warn"]
                + expected_breakdown["fail"]
            ):
                raise ValueError(
                    f"ProblemReport Inv P9 violation: "
                    f"dimension_summary[dim={ds.dimension_id}].n_applicable "
                    f"= {ds.n_applicable} but sum of pass+warn+fail "
                    f"counts = "
                    f"{expected_breakdown['pass'] + expected_breakdown['warn'] + expected_breakdown['fail']}"
                )
            if ds.n_deferred != expected_deferred:
                raise ValueError(
                    f"ProblemReport Inv P9 violation: "
                    f"dimension_summary[dim={ds.dimension_id}].n_deferred "
                    f"= {ds.n_deferred} but actual count in "
                    f"deferred_checks is {expected_deferred}"
                )

        # Inv P19: dimensions_not_evaluated non-empty.
        if not isinstance(self.dimensions_not_evaluated, tuple):
            raise TypeError(
                f"ProblemReport.dimensions_not_evaluated must be tuple; "
                f"got {type(self.dimensions_not_evaluated)}"
            )
        if not self.dimensions_not_evaluated:
            raise ValueError(
                "ProblemReport.dimensions_not_evaluated violates Inv "
                "P19 — must be non-empty per v0.2 A6"
            )
        for d in self.dimensions_not_evaluated:
            if not isinstance(d, str) or not d:
                raise ValueError(
                    f"ProblemReport.dimensions_not_evaluated entries "
                    f"must be non-empty strings; got "
                    f"{self.dimensions_not_evaluated!r}"
                )
        if list(self.dimensions_not_evaluated) != sorted(
            self.dimensions_not_evaluated
        ):
            raise ValueError(
                f"ProblemReport.dimensions_not_evaluated must be sorted "
                f"lex-ASC (Inv P2 replay determinism); got "
                f"{self.dimensions_not_evaluated!r}"
            )
        if len(set(self.dimensions_not_evaluated)) != len(
            self.dimensions_not_evaluated
        ):
            raise ValueError(
                f"ProblemReport.dimensions_not_evaluated must be unique; "
                f"got {self.dimensions_not_evaluated!r}"
            )

        # unconventional_pattern_hint: must be UnconventionalPatternHint.
        if not isinstance(
            self.unconventional_pattern_hint, UnconventionalPatternHint
        ):
            raise TypeError(
                f"ProblemReport.unconventional_pattern_hint must be "
                f"UnconventionalPatternHint; got "
                f"{type(self.unconventional_pattern_hint)}"
            )

        # cultural_profile_active: must be CulturalProfile member.
        if not isinstance(self.cultural_profile_active, CulturalProfile):
            raise TypeError(
                f"ProblemReport.cultural_profile_active must be "
                f"CulturalProfile (per v0.2 A3); got "
                f"{type(self.cultural_profile_active)}"
            )

        # advisory passthroughs: must be tuples (content opaque at
        # schema level; Inv P10 byte-equality enforced at orchestrator).
        for fname in (
            "c13_advisory_flags",
            "c14_structural_flags",
            "c14_preference_flags",
        ):
            v = getattr(self, fname)
            if not isinstance(v, tuple):
                raise TypeError(
                    f"ProblemReport.{fname} must be tuple; "
                    f"got {type(v)}"
                )

        # Provenance triple (Inv P16).
        if not isinstance(self.c15_version, str):
            raise TypeError(
                f"ProblemReport.c15_version must be str; "
                f"got {type(self.c15_version)}"
            )
        if not self.c15_version:
            raise ValueError(
                "ProblemReport.c15_version violates Inv P16 — must be "
                "non-empty"
            )
        if not isinstance(self.c15_check_registry_version, int) or isinstance(
            self.c15_check_registry_version, bool
        ):
            raise TypeError(
                f"ProblemReport.c15_check_registry_version must be int "
                f"(not bool); got {type(self.c15_check_registry_version)}"
            )
        if self.c15_check_registry_version < 0:
            raise ValueError(
                f"ProblemReport.c15_check_registry_version violates "
                f"Inv P16 — must be ≥ 0; got "
                f"{self.c15_check_registry_version}"
            )
        if not isinstance(self.advisory_schema_version, int) or isinstance(
            self.advisory_schema_version, bool
        ):
            raise TypeError(
                f"ProblemReport.advisory_schema_version must be int "
                f"(not bool); got {type(self.advisory_schema_version)}"
            )
        if self.advisory_schema_version < 0:
            raise ValueError(
                f"ProblemReport.advisory_schema_version violates "
                f"Inv P16 — must be ≥ 0; got "
                f"{self.advisory_schema_version}"
            )

        # upstream_cache_key (Inv P14).
        if not isinstance(self.upstream_cache_key, str):
            raise TypeError(
                f"ProblemReport.upstream_cache_key must be str; "
                f"got {type(self.upstream_cache_key)}"
            )
        if not self.upstream_cache_key:
            raise ValueError(
                "ProblemReport.upstream_cache_key violates Inv P14 — "
                "must be non-empty"
            )

        # v0.3 A12: coverage_quality must be CoverageQuality enum.
        if not isinstance(self.coverage_quality, CoverageQuality):
            raise TypeError(
                f"ProblemReport.coverage_quality must be CoverageQuality "
                f"(v0.3 A12); got {type(self.coverage_quality)}"
            )

        # v0.3 A12: ratio_applicable must be float in [0.0, 1.0].
        if not isinstance(self.ratio_applicable, float):
            raise TypeError(
                f"ProblemReport.ratio_applicable must be float "
                f"(v0.3 A12); got {type(self.ratio_applicable)}"
            )
        if not (0.0 <= self.ratio_applicable <= 1.0):
            raise ValueError(
                f"ProblemReport.ratio_applicable must be in [0.0, 1.0] "
                f"(v0.3 A12); got {self.ratio_applicable}"
            )

        # v0.3 A12 crosscheck: coverage_quality must match the bucket
        # derived from ratio_applicable. Prevents construction-site
        # bugs (e.g. coverage_quality=HIGH with ratio_applicable=0.2).
        if self.ratio_applicable >= 0.70:
            expected_cq = CoverageQuality.HIGH
        elif self.ratio_applicable >= 0.40:
            expected_cq = CoverageQuality.MEDIUM
        else:
            expected_cq = CoverageQuality.LOW
        if self.coverage_quality is not expected_cq:
            raise ValueError(
                f"ProblemReport.coverage_quality ({self.coverage_quality}) "
                f"does not match bucket derived from ratio_applicable="
                f"{self.ratio_applicable:.4f}; expected {expected_cq} "
                f"per v0.3 A12 § 14.3 derivation rule"
            )


# =============================================================================
# FailureRecord (per v0.1 § 5)
# =============================================================================

@dataclass(frozen=True)
class FailureRecord:
    """Per v0.1 § 5. Captures a per-candidate analysis failure.

    Fields:
      candidate_signature: provenance back to source C14
        SuccessfulCirculationAnalysis.
      error_type: class name of the PerCandidateProblemError.
      error_message: str() of the underlying exception.
      phase: which phase produced the failure (pi / rho / sigma /
        tau / upsilon / phi).
    """
    candidate_signature: str
    error_type: str
    error_message: str
    phase: PhaseLiteral

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_signature, str):
            raise TypeError(
                f"FailureRecord.candidate_signature must be str; "
                f"got {type(self.candidate_signature)}"
            )
        if not self.candidate_signature:
            raise ValueError(
                "FailureRecord.candidate_signature must be non-empty"
            )

        if not isinstance(self.error_type, str):
            raise TypeError(
                f"FailureRecord.error_type must be str; "
                f"got {type(self.error_type)}"
            )
        if not self.error_type:
            raise ValueError(
                "FailureRecord.error_type must be non-empty"
            )

        if not isinstance(self.error_message, str):
            raise TypeError(
                f"FailureRecord.error_message must be str; "
                f"got {type(self.error_message)}"
            )

        if self.phase not in (
            "pi", "rho", "sigma", "tau", "upsilon", "phi"
        ):
            raise ValueError(
                f"FailureRecord.phase must be one of "
                f"pi|rho|sigma|tau|upsilon|phi; got {self.phase!r}"
            )


# =============================================================================
# Typestate variants (per v0.1 § 5, mirroring C13 v0.3 B11 / C14)
# =============================================================================

@dataclass(frozen=True)
class SuccessfulProblemAnalysis:
    """Typestate-discriminated successful result.

    Downstream consumers MUST pattern-match on this vs
    FailedProblemAnalysis. Static type checkers reject access to
    .report on a FailedProblemAnalysis — preventing WARN-mode-failed
    candidates from being misused as successful.

    Fields:
      source_placed_candidate_signature: provenance back to upstream.
      report: the ProblemReport (canonical-sorted, frozen).
    """
    source_placed_candidate_signature: str
    report: ProblemReport

    def __post_init__(self) -> None:
        if not isinstance(self.source_placed_candidate_signature, str):
            raise TypeError(
                f"SuccessfulProblemAnalysis."
                f"source_placed_candidate_signature must be str; "
                f"got {type(self.source_placed_candidate_signature)}"
            )
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "SuccessfulProblemAnalysis."
                "source_placed_candidate_signature must be non-empty"
            )
        if not isinstance(self.report, ProblemReport):
            raise TypeError(
                f"SuccessfulProblemAnalysis.report must be ProblemReport; "
                f"got {type(self.report)}"
            )
        # Consistency: report's signature must match the wrapper.
        if (
            self.report.source_placed_candidate_signature
            != self.source_placed_candidate_signature
        ):
            raise ValueError(
                f"SuccessfulProblemAnalysis: source signature "
                f"({self.source_placed_candidate_signature!r}) does not "
                f"match wrapped report signature "
                f"({self.report.source_placed_candidate_signature!r})"
            )


@dataclass(frozen=True)
class FailedProblemAnalysis:
    """Typestate-discriminated failure result.

    For WARN-mode collection. Cannot be misused as a successful result
    because there is no `.report` field of type ProblemReport.

    Fields:
      source_placed_candidate_signature: provenance back to upstream.
      failure_record: the FailureRecord with phase + error_type +
        error_message.
      partial_report: optional partial ProblemReport built before
        failure; DEBUG only. Per the typestate contract, downstream
        consumers SHOULD NOT use this except for diagnostics — using
        it as if it were a complete report would subvert the typestate
        discipline.
    """
    source_placed_candidate_signature: str
    failure_record: FailureRecord
    partial_report: Optional[ProblemReport] = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_placed_candidate_signature, str):
            raise TypeError(
                f"FailedProblemAnalysis."
                f"source_placed_candidate_signature must be str; "
                f"got {type(self.source_placed_candidate_signature)}"
            )
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "FailedProblemAnalysis."
                "source_placed_candidate_signature must be non-empty"
            )
        if not isinstance(self.failure_record, FailureRecord):
            raise TypeError(
                f"FailedProblemAnalysis.failure_record must be "
                f"FailureRecord; got {type(self.failure_record)}"
            )
        if (
            self.failure_record.candidate_signature
            != self.source_placed_candidate_signature
        ):
            raise ValueError(
                f"FailedProblemAnalysis: source signature "
                f"({self.source_placed_candidate_signature!r}) does not "
                f"match failure_record signature "
                f"({self.failure_record.candidate_signature!r})"
            )
        if self.partial_report is not None and not isinstance(
            self.partial_report, ProblemReport
        ):
            raise TypeError(
                f"FailedProblemAnalysis.partial_report must be "
                f"ProblemReport or None; got {type(self.partial_report)}"
            )


# =============================================================================
# ProblemAnalysisBatchResult (per v0.1 § 5)
# =============================================================================

@dataclass(frozen=True)
class ProblemAnalysisBatchResult:
    """Per v0.1 § 5. Top-level result of analyze_problems().

    Typestate-discriminated: separate tuples for successful + failed
    analyses. NO general "results" field mixing them (mirrors C13/C14).

    Fields:
      successful: tuple of SuccessfulProblemAnalysis, sorted lex-ASC
          by source_placed_candidate_signature.
      failed: tuple of FailedProblemAnalysis, sorted lex-ASC by
          source_placed_candidate_signature.
      c15_version: version stamp (Inv P16).
      c15_check_registry_version: registry version stamp (Inv P16).
      advisory_schema_version: passed-through from C14 chain (Inv P16).

    Per Inv P0 (v0.2 A1): no batch-level aggregate score. Consumers
    that want batch-level summaries compute them from successful/
    failed tuples themselves.
    """
    successful: tuple[SuccessfulProblemAnalysis, ...]
    failed: tuple[FailedProblemAnalysis, ...]
    c15_version: str
    c15_check_registry_version: int
    advisory_schema_version: int

    def __post_init__(self) -> None:
        # Sort enforcement (Inv P2 byte-equal replay).
        if not isinstance(self.successful, tuple):
            raise TypeError(
                f"ProblemAnalysisBatchResult.successful must be tuple; "
                f"got {type(self.successful)}"
            )
        for s in self.successful:
            if not isinstance(s, SuccessfulProblemAnalysis):
                raise TypeError(
                    f"ProblemAnalysisBatchResult.successful must "
                    f"contain SuccessfulProblemAnalysis; got {type(s)}"
                )
        succ_keys = [
            s.source_placed_candidate_signature for s in self.successful
        ]
        if succ_keys != sorted(succ_keys):
            raise ValueError(
                f"ProblemAnalysisBatchResult: successful tuple must be "
                f"sorted lex-ASC by source signature; got {succ_keys}"
            )

        if not isinstance(self.failed, tuple):
            raise TypeError(
                f"ProblemAnalysisBatchResult.failed must be tuple; "
                f"got {type(self.failed)}"
            )
        for f in self.failed:
            if not isinstance(f, FailedProblemAnalysis):
                raise TypeError(
                    f"ProblemAnalysisBatchResult.failed must contain "
                    f"FailedProblemAnalysis; got {type(f)}"
                )
        fail_keys = [
            f.source_placed_candidate_signature for f in self.failed
        ]
        if fail_keys != sorted(fail_keys):
            raise ValueError(
                f"ProblemAnalysisBatchResult: failed tuple must be "
                f"sorted lex-ASC by source signature; got {fail_keys}"
            )

        # No source-signature appears in BOTH successful and failed.
        succ_set = set(succ_keys)
        for k in fail_keys:
            if k in succ_set:
                raise ValueError(
                    f"ProblemAnalysisBatchResult: source signature "
                    f"{k!r} appears in BOTH successful and failed tuples"
                )

        # Provenance triple (Inv P16).
        if not isinstance(self.c15_version, str):
            raise TypeError(
                f"ProblemAnalysisBatchResult.c15_version must be str; "
                f"got {type(self.c15_version)}"
            )
        if not self.c15_version:
            raise ValueError(
                "ProblemAnalysisBatchResult violates Inv P16 — "
                "c15_version must be non-empty"
            )
        if not isinstance(self.c15_check_registry_version, int) or isinstance(
            self.c15_check_registry_version, bool
        ):
            raise TypeError(
                f"ProblemAnalysisBatchResult.c15_check_registry_version "
                f"must be int (not bool); got "
                f"{type(self.c15_check_registry_version)}"
            )
        if self.c15_check_registry_version < 0:
            raise ValueError(
                f"ProblemAnalysisBatchResult violates Inv P16 — "
                f"c15_check_registry_version must be ≥ 0; got "
                f"{self.c15_check_registry_version}"
            )
        if not isinstance(self.advisory_schema_version, int) or isinstance(
            self.advisory_schema_version, bool
        ):
            raise TypeError(
                f"ProblemAnalysisBatchResult.advisory_schema_version "
                f"must be int (not bool); got "
                f"{type(self.advisory_schema_version)}"
            )
        if self.advisory_schema_version < 0:
            raise ValueError(
                f"ProblemAnalysisBatchResult violates Inv P16 — "
                f"advisory_schema_version must be ≥ 0; got "
                f"{self.advisory_schema_version}"
            )


__all__ = [
    # enums
    "CheckStatus",
    "CheckSeverity",
    "CheckEpistemicKind",
    # phase literal type
    "PhaseLiteral",
    # severity rule
    "SeverityRule",
    # records
    "ProblemCheck",
    "DeferredCheck",
    # hint + summary
    "UNCONVENTIONAL_PATTERN_NAMES",
    "UnconventionalPatternHint",
    "DimensionSummary",
    # report
    "ProblemReport",
    # typestate
    "FailureRecord",
    "SuccessfulProblemAnalysis",
    "FailedProblemAnalysis",
    "ProblemAnalysisBatchResult",
    # re-exports for convenience (callers can also import from versioning)
    "DIMENSIONS_NOT_EVALUATED_V1",
]
