"""
Component 2 — Feasibility domain types.

After v0.9.3 final shipped, Component 2 (Feasibility) checks whether a
captured Brief is physically + legally + practically achievable on the
user's plot. It produces TWO parallel reports:

  - PRACTICAL design: what fits the user's plot + budget + accepted
    compromises. May knowingly fall short of NBC recommendations.
  - CODE_STRICT design: what NBC + city DCRs strictly mandate.

Plus a DesignGapAnalysis that surfaces the gap and asks the user to
choose which design proceeds to Component 4 (layout).

This file contains ONLY domain types — no logic. Logic lives in
components/c02/.

Foundation built in Session A includes 8 review-driven additions:
  #1 score_contribution + score_breakdown for explainable scoring
  #2 is_feasible derived from blocking_issues (no drift)
  #5 confidence_reason on every CheckResult
  #6 verification_priority on every CheckResult
  #8 GapSeverity per Gap
  #9 DecisionSource for user_acceptable provenance
  #10 CheckCategory for grouped output
  #11 Unknown promoted to top-level report field
  #12 ActionStep linked to triggering check_ids

Deferred (with rationale):
  #3 check dependencies — premature; observe real check interactions first
  #4 DesignVariant gradient — analyst self-cancelled, current binary correct
  #7 doubts UI elaboration — already designed (Interpretation A)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Enums ─────────────────────────────────────────────────────────────

class DesignVariant(Enum):
    """Which feasibility lens this report represents.

    PRACTICAL means: what the user can actually build on their plot
    given their budget and accepted compromises. May include
    user-accepted setback relaxations, smaller-than-NBC rooms, etc.
    PRACTICAL is NOT illegal — it is user-adjusted within the bounds
    of acceptable compromise. Some compromises require formal
    municipal variance applications; some are routinely tolerated.
    Always confirm with a licensed local architect before construction.

    CODE_STRICT means: what NBC + city DCRs strictly mandate, with no
    user compromises. May exceed plot capacity or budget, but represents
    fully compliant design.
    """
    PRACTICAL = "practical"
    CODE_STRICT = "code_strict"


class CheckSeverity(Enum):
    """Outcome severity of a single feasibility check.

    HARD_FAIL → blocks the variant unless user explicitly accepts compromise.
    SOFT_WARN → advisory; reduces score but does not block.
    PASS → check satisfied; contributes to score positively.
    NOT_APPLICABLE → check did not apply to this brief (e.g.,
        stilt parking check on a no-parking brief).
    """
    HARD_FAIL = "hard_fail"
    SOFT_WARN = "soft_warn"
    PASS = "pass"
    NOT_APPLICABLE = "not_applicable"


class CheckCategory(Enum):
    """Coarse domain of a check, for grouped output (#10).

    Maps cleanly to the 18 v0.1 checks:
      COMPLIANCE: FAR, ground coverage, fire access, water course
      SPATIAL: envelope sufficiency, setbacks, room minimums, floor stack
      STRUCTURAL: soil type, water table
      USABILITY: parking width, solar, cross-ventilation
      COST: budget, RWH mandate, stilt mandate, approval complexity
      SAFETY: electric line clearance
    """
    COMPLIANCE = "compliance"
    SPATIAL = "spatial"
    STRUCTURAL = "structural"
    USABILITY = "usability"
    COST = "cost"
    SAFETY = "safety"


class ConfidenceLevel(Enum):
    """How much the check result can be trusted (#5).

    HIGH → user-provided + verified data, strict rule applied.
    MEDIUM → user-provided but unverified data.
    LOW → city-default assumed because user did not provide.

    Score weighting honours confidence: a HIGH-confidence SOFT_WARN
    penalises more than a LOW-confidence one because we trust the
    underlying data more.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationPriority(Enum):
    """How urgently the user should verify an assumed/unverified value (#6).

    CRITICAL → affects HARD_FAIL outcome; verify before any construction.
    IMPORTANT → affects feasibility score significantly.
    OPTIONAL → nice-to-have for higher confidence.
    """
    CRITICAL = "critical"
    IMPORTANT = "important"
    OPTIONAL = "optional"


class GapSeverity(Enum):
    """How big the gap between PRACTICAL and CODE_STRICT is for one check (#8).

    BLOCKING_IF_NOT_ACCEPTED → CODE_STRICT would HARD_FAIL; user must
        accept the compromise to proceed with PRACTICAL.
    SIGNIFICANT → 15%+ shortfall vs NBC norm; visible quality difference.
    MARGINAL → < 15% shortfall; small concession.
    INFO_ONLY → cost or timing differs but design is functionally same.
    """
    BLOCKING_IF_NOT_ACCEPTED = "blocking_if_not_accepted"
    SIGNIFICANT = "significant"
    MARGINAL = "marginal"
    INFO_ONLY = "info_only"


class DecisionSource(Enum):
    """Provenance of a user_acceptable decision on a Gap (#9).

    USER_EXPLICIT → user actively chose to accept/reject the compromise.
    SYSTEM_DEFAULT → system applied a default (e.g., "first run, accept
        compromises ≤ 10% shortfall by default; reject larger gaps").
    INFERRED_FROM_BRIEF → inferred from user's stated priorities or
        budget pressure (e.g., user has tight budget → accept smaller
        rooms by default).
    """
    USER_EXPLICIT = "user_explicit"
    SYSTEM_DEFAULT = "system_default"
    INFERRED_FROM_BRIEF = "inferred_from_brief"


# ─── Core types ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CheckResult:
    """Single check's outcome against the brief.

    All fields except the standard ones (id, name, severity, message,
    details) are review-driven additions:
      category: #10
      confidence_reason: #5
      score_contribution: #1 (negative penalty applied to score)
      verification_priority: #6
      common_doubts: from prior design (Interpretation A)
    """
    check_id: str
    check_name: str
    category: CheckCategory
    severity: CheckSeverity
    confidence: ConfidenceLevel
    confidence_reason: str | None
    score_contribution: int
    message: str
    details: dict[str, Any]
    assumption_used: str | None
    verification_recommendation: str | None
    verification_priority: VerificationPriority
    common_doubts: tuple[str, ...]

    def __post_init__(self) -> None:
        # Score contribution sign convention: penalties are negative.
        # PASS contributes 0 (baseline); SOFT_WARN/HARD_FAIL contribute
        # negative numbers. NOT_APPLICABLE contributes 0.
        if self.severity == CheckSeverity.PASS:
            object.__setattr__(self, "score_contribution",
                               max(0, self.score_contribution))
        elif self.severity == CheckSeverity.NOT_APPLICABLE:
            object.__setattr__(self, "score_contribution", 0)
        else:
            # SOFT_WARN and HARD_FAIL contributions must be ≤ 0
            object.__setattr__(self, "score_contribution",
                               min(0, self.score_contribution))

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "confidence_reason": self.confidence_reason,
            "score_contribution": self.score_contribution,
            "message": self.message,
            "details": dict(self.details) if self.details else {},
            "assumption_used": self.assumption_used,
            "verification_recommendation": self.verification_recommendation,
            "verification_priority": self.verification_priority.value,
            "common_doubts": list(self.common_doubts),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CheckResult":
        return cls(
            check_id=payload["check_id"],
            check_name=payload["check_name"],
            category=CheckCategory(payload["category"]),
            severity=CheckSeverity(payload["severity"]),
            confidence=ConfidenceLevel(payload["confidence"]),
            confidence_reason=payload.get("confidence_reason"),
            score_contribution=payload["score_contribution"],
            message=payload["message"],
            details=dict(payload.get("details", {})),
            assumption_used=payload.get("assumption_used"),
            verification_recommendation=payload.get(
                "verification_recommendation"
            ),
            verification_priority=VerificationPriority(
                payload["verification_priority"]
            ),
            common_doubts=tuple(payload.get("common_doubts", [])),
        )


@dataclass(frozen=True)
class Unknown:
    """A piece of information the system needed but the user didn't provide (#11).

    Promoted from per-check `assumption_used` strings to a top-level
    aggregated bucket. Single source of truth for "what we don't know,"
    avoiding duplication across multiple check assumptions.

    affects_check_ids: which checks were run with the assumed value.
    """
    field_name: str
    user_facing_question: str
    assumed_value: str
    affects_check_ids: tuple[str, ...]
    verification_recommendation: str
    priority: VerificationPriority

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "user_facing_question": self.user_facing_question,
            "assumed_value": self.assumed_value,
            "affects_check_ids": list(self.affects_check_ids),
            "verification_recommendation": self.verification_recommendation,
            "priority": self.priority.value,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Unknown":
        return cls(
            field_name=payload["field_name"],
            user_facing_question=payload["user_facing_question"],
            assumed_value=payload["assumed_value"],
            affects_check_ids=tuple(payload.get("affects_check_ids", [])),
            verification_recommendation=payload["verification_recommendation"],
            priority=VerificationPriority(payload["priority"]),
        )


@dataclass(frozen=True)
class ActionStep:
    """One actionable next step for the user (#12).

    triggering_check_ids: which checks generated this action. Lets the
    UI explain "why is this action recommended?" by showing the
    failed/warned checks behind it.

    priority: 1 = highest urgency, 5 = lowest.
    """
    step_text: str
    triggering_check_ids: tuple[str, ...]
    priority: int = 3

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "step_text": self.step_text,
            "triggering_check_ids": list(self.triggering_check_ids),
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ActionStep":
        return cls(
            step_text=payload["step_text"],
            triggering_check_ids=tuple(
                payload.get("triggering_check_ids", [])
            ),
            priority=payload.get("priority", 3),
        )


@dataclass(frozen=True)
class FeasibilityReport:
    """Single-variant feasibility report (PRACTICAL or CODE_STRICT).

    is_feasible is DERIVED from blocking_issues (#2 — never drifts out
    of sync). The dual-property pattern lets us distinguish strict
    feasibility from "feasible with user-accepted compromises".

    score_breakdown (#1) maps check_id → contribution, so the user can
    audit "why is this 72?" by seeing each check's penalty.
    """
    variant: DesignVariant
    overall_score: int                           # 0-100, see scoring contract
    score_breakdown: dict[str, int]              # check_id → contribution

    # Check results split by severity for easy access
    blocking_issues: tuple[CheckResult, ...]
    unaccepted_blocking_issues: tuple[CheckResult, ...]
    soft_warnings: tuple[CheckResult, ...]
    passed_checks: tuple[CheckResult, ...]
    not_applicable_checks: tuple[CheckResult, ...]

    # Cost (in INR — TransparencyTriple from C7)
    cost_estimate: Any   # TransparencyTriple — typed loosely to avoid C7 import

    # Aggregated unknowns and actions
    unknowns: tuple[Unknown, ...]
    action_steps: tuple[ActionStep, ...]

    @property
    def is_feasible(self) -> bool:
        """Strict feasibility — no user-accepted compromises counted."""
        return len(self.blocking_issues) == 0

    @property
    def is_feasible_with_user_acceptance(self) -> bool:
        """Feasible IF user accepts all currently-blocking compromises."""
        return len(self.unaccepted_blocking_issues) == 0

    @property
    def all_check_results(self) -> tuple[CheckResult, ...]:
        """Every CheckResult in this report (any severity)."""
        return (
            self.blocking_issues
            + self.soft_warnings
            + self.passed_checks
            + self.not_applicable_checks
        )

    @property
    def checks_by_category(self) -> dict[CheckCategory, tuple[CheckResult, ...]]:
        """Group all checks by their category for grouped rendering (#10)."""
        grouped: dict[CheckCategory, list[CheckResult]] = {}
        for c in self.all_check_results:
            grouped.setdefault(c.category, []).append(c)
        return {k: tuple(v) for k, v in grouped.items()}

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "variant": self.variant.value,
            "overall_score": self.overall_score,
            "score_breakdown": dict(self.score_breakdown),
            "blocking_issues": [
                c.to_dict() for c in self.blocking_issues
            ],
            "unaccepted_blocking_issues": [
                c.to_dict() for c in self.unaccepted_blocking_issues
            ],
            "soft_warnings": [c.to_dict() for c in self.soft_warnings],
            "passed_checks": [c.to_dict() for c in self.passed_checks],
            "not_applicable_checks": [
                c.to_dict() for c in self.not_applicable_checks
            ],
            # cost_estimate is a TransparencyTriple (typed loosely as Any
            # to avoid the C7 import at the domain layer). Per S7a SPEC
            # § 9.2, all dependent types own their own to_dict/from_dict.
            "cost_estimate": (
                self.cost_estimate.to_dict()
                if self.cost_estimate is not None else None
            ),
            "unknowns": [u.to_dict() for u in self.unknowns],
            "action_steps": [a.to_dict() for a in self.action_steps],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "FeasibilityReport":
        # Lazy import — domain layer must not have a top-level dep on
        # utils/transparency, but cost_estimate is TransparencyTriple.
        from buildemup.utils.transparency import TransparencyTriple
        return cls(
            variant=DesignVariant(payload["variant"]),
            overall_score=payload["overall_score"],
            score_breakdown=dict(payload.get("score_breakdown", {})),
            blocking_issues=tuple(
                CheckResult.from_dict(c)
                for c in payload.get("blocking_issues", [])
            ),
            unaccepted_blocking_issues=tuple(
                CheckResult.from_dict(c)
                for c in payload.get("unaccepted_blocking_issues", [])
            ),
            soft_warnings=tuple(
                CheckResult.from_dict(c)
                for c in payload.get("soft_warnings", [])
            ),
            passed_checks=tuple(
                CheckResult.from_dict(c)
                for c in payload.get("passed_checks", [])
            ),
            not_applicable_checks=tuple(
                CheckResult.from_dict(c)
                for c in payload.get("not_applicable_checks", [])
            ),
            cost_estimate=(
                TransparencyTriple.from_dict(payload["cost_estimate"])
                if payload.get("cost_estimate") is not None else None
            ),
            unknowns=tuple(
                Unknown.from_dict(u) for u in payload.get("unknowns", [])
            ),
            action_steps=tuple(
                ActionStep.from_dict(a)
                for a in payload.get("action_steps", [])
            ),
        )


@dataclass(frozen=True)
class Gap:
    """Difference between PRACTICAL and CODE_STRICT for one check (#8).

    severity quantifies how big the gap is.
    user_acceptable + decision_source track the decision provenance (#9):
      None = system hasn't asked yet (default state)
      True = user explicitly accepted this compromise
      False = user explicitly rejected (forces CODE_STRICT for this check)
    """
    check_id: str
    severity: GapSeverity
    practical_value: Any
    code_strict_value: Any
    impact_description: str
    user_acceptable: bool | None = None
    decision_source: DecisionSource = DecisionSource.SYSTEM_DEFAULT

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        # practical_value / code_strict_value are typed Any. They MUST
        # already be JSON-safe primitives by construction (per the
        # caller's discipline); we don't try to deeply encode arbitrary
        # objects here. If a non-JSON-safe value appears, json.dumps at
        # the storage layer will surface it loudly.
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "practical_value": self.practical_value,
            "code_strict_value": self.code_strict_value,
            "impact_description": self.impact_description,
            "user_acceptable": self.user_acceptable,
            "decision_source": self.decision_source.value,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Gap":
        return cls(
            check_id=payload["check_id"],
            severity=GapSeverity(payload["severity"]),
            practical_value=payload.get("practical_value"),
            code_strict_value=payload.get("code_strict_value"),
            impact_description=payload["impact_description"],
            user_acceptable=payload.get("user_acceptable"),
            decision_source=DecisionSource(
                payload.get("decision_source",
                            DecisionSource.SYSTEM_DEFAULT.value)
            ),
        )


@dataclass(frozen=True)
class DesignGapAnalysis:
    """Top-level Component 2 output combining both variants + gap.

    Contains the two reports plus a list of gaps. The user picks
    which design proceeds to Component 4 (layout) via
    chosen_design_path: PRACTICAL | CODE_STRICT.
    """
    practical_report: FeasibilityReport
    code_strict_report: FeasibilityReport
    gaps: tuple[Gap, ...]
    cost_delta_lakhs: float                     # code_strict - practical
    user_decisions_required: tuple[str, ...]    # human-readable Q's

    @property
    def has_meaningful_gap(self) -> bool:
        """True if the two reports differ in any check.

        When False, output should say 'Both designs identical for your
        brief — you got lucky' rather than rendering two reports.
        """
        return len(self.gaps) > 0

    @property
    def blocking_gaps(self) -> tuple[Gap, ...]:
        """Gaps that block CODE_STRICT but PRACTICAL accepts."""
        return tuple(g for g in self.gaps
                     if g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED)

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "practical_report": self.practical_report.to_dict(),
            "code_strict_report": self.code_strict_report.to_dict(),
            "gaps": [g.to_dict() for g in self.gaps],
            "cost_delta_lakhs": self.cost_delta_lakhs,
            "user_decisions_required": list(self.user_decisions_required),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "DesignGapAnalysis":
        return cls(
            practical_report=FeasibilityReport.from_dict(
                payload["practical_report"]
            ),
            code_strict_report=FeasibilityReport.from_dict(
                payload["code_strict_report"]
            ),
            gaps=tuple(
                Gap.from_dict(g) for g in payload.get("gaps", [])
            ),
            cost_delta_lakhs=payload["cost_delta_lakhs"],
            user_decisions_required=tuple(
                payload.get("user_decisions_required", [])
            ),
        )
