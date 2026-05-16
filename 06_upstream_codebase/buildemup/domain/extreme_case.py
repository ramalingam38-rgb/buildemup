"""
BuildemUp† — Component 3a (Extreme Case Gate) domain objects.

Per SPEC_v0.2.1 Section 3 — captures all data structures needed to detect,
surface, and resolve extreme cases that block layout generation.

This module is built BEFORE the layout pipeline. Component 3a runs after
Component 2 (Feasibility) when C2 produces blocking gaps. It surfaces
those blockers to the user one at a time, lets them pick a resolution
option, applies the change, and re-runs C2 until either:
  - all blockers are resolved (mode=BUILDABLE), or
  - the user explicitly chooses Preview Mode (mode=PREVIEW).

Structure:
  ExtremeCase            : a single blocker with options for resolution
  ResolutionOption       : one option a user can pick to resolve a case
  CostImpact             : Transparency Triple (low/mid/high) for option cost
  BriefChange            : an atomic mutation to apply to a Brief
  ExtremeDecision        : record of one user choice (chosen + presented set)
  ExtremeDecisionLog     : full record of all decisions in this run
  CounterfactualSummary  : "what other options would have done" — for family discussion
  PreflightSummary       : non-blocking summary shown before first EC modal
  PreviewModeAcknowledgment : audit record of user's explicit Preview consent
  ResolvedBrief          : final output → forwarded to layout pipeline

Plus 5 enums:
  ExtremeCaseCategory    : SPATIAL / LEGAL / BUDGET / SITE / APPROVAL
  ExtremeCaseId          : EC_001 through EC_010
  ResolutionProbability  : HIGH / MEDIUM / LOW / N/A (used only for EC-010)
  BriefMode              : BUILDABLE | PREVIEW
  CostConfidence         : HIGH / MEDIUM / LOW (drives caveat language)

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ═════════════════════════════════════════════════════════════════════════
# Enums (5 total)
# ═════════════════════════════════════════════════════════════════════════

class ExtremeCaseCategory(str, Enum):
    """Top-level category. Drives priority order in the orchestrator:
    LEGAL → SITE → APPROVAL → SPATIAL → BUDGET (per Section 4.2).
    """
    SPATIAL = "SPATIAL"   # brief literally won't fit the envelope
    LEGAL = "LEGAL"       # design violates code; no layout choice can fix
    BUDGET = "BUDGET"     # no layout makes the numbers work
    SITE = "SITE"         # the site itself fights the brief
    APPROVAL = "APPROVAL" # won't get permitted regardless of layout


class ExtremeCaseId(str, Enum):
    """One per locked extreme case (Section 2.2)."""
    EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE = "EC_001"
    EC_002_PLOT_WIDTH_INSUFFICIENT = "EC_002"
    EC_003_NO_PARKING_POSITION = "EC_003"
    EC_004_FAR_EXCEEDED = "EC_004"
    EC_005_GROUND_COVERAGE_EXCEEDED = "EC_005"
    EC_006_PRACTICAL_ENVELOPE_BELOW_BUILDABLE = "EC_006"
    EC_007_STILT_MANDATE_VIOLATED = "EC_007"
    EC_008_BUDGET_CATASTROPHICALLY_LOW = "EC_008"
    EC_009_SOIL_REQUIRES_PILE_BUDGET_LOW = "EC_009"
    EC_010_APPROVAL_BLOCKER = "EC_010"


class ResolutionProbability(str, Enum):
    """Per critique #4: only used for EC-010 subtypes. Drives the
    framing line and option set (HIGH/MEDIUM use 'often resolvable' tone;
    LOW recommends 'different plot' first).
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_APPLICABLE = "N/A"


class BriefMode(str, Enum):
    """The mode the ResolvedBrief flows downstream in.

    BUILDABLE — all blockers resolved; layout pipeline runs normally.
    PREVIEW   — user explicitly bypassed one or more blockers via the
                Preview Mode option. Layout pipeline must read mode and
                relax constraints accordingly. Renderer (Component 16)
                must produce reduced output with watermarks (Section 4.5).
    """
    BUILDABLE = "BUILDABLE"
    PREVIEW = "PREVIEW"


class CostConfidence(str, Enum):
    """Per critique #9 + v0.2.1 critique #3.

    Drives caveat language in CostImpact. We do NOT hide numbers when
    confidence is LOW (rejected proposal) — we show numbers AND aggressive
    caveats so the user can sanity-check against friends/contractors but
    knows the engine isn't sure.

    HIGH    — backed by C7 cost engine output, ±15%
    MEDIUM  — engineering rule of thumb, ±25%
    LOW     — rough estimate, ±40%; UI surfaces "this could shift" language
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @property
    def uncertainty_pct(self) -> int:
        """Default uncertainty range for this confidence level."""
        return {
            CostConfidence.HIGH: 15,
            CostConfidence.MEDIUM: 25,
            CostConfidence.LOW: 40,
        }[self]

    @property
    def default_caveat_language(self) -> Optional[str]:
        """Default caveat phrase. UI prepends this to the cost range."""
        if self == CostConfidence.LOW:
            return "this could shift ±40% — soil/finishes/labour rates not yet specified"
        if self == CostConfidence.MEDIUM:
            return "approximately — exact cost depends on choices not yet made"
        return None  # HIGH needs no caveat


# ═════════════════════════════════════════════════════════════════════════
# Atomic value types (3 total)
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BriefChange:
    """A discrete, applicable change to a Brief.

    Per critique #7 pushback: BriefChange is intentionally atomic. The
    cascade of dependent fields (FAR, area, cost) happens through C2's
    full re-run after BriefChange is applied. Component 3a does NOT
    duplicate C2's logic.

    Integrity invariant (Section 3.3): apply_brief_change() must produce
    a Brief that passes Brief.__post_init__ validation. If validation
    fails, BriefChangeIntegrityError is raised — the malformed Brief
    never reaches C2.

    Fields:
        field_path  — dotted path into Brief, e.g. "rooms.bedroom_3"
                      or "budget.target_inr"
        operation   — one of "DELETE", "SET", "INCREMENT"
        new_value   — value for SET/INCREMENT; ignored for DELETE
        description — human-readable summary, e.g. "Remove bedroom 3"
    """
    field_path: str
    operation: str
    new_value: Any
    description: str

    _ALLOWED_OPS = ("DELETE", "SET", "INCREMENT")

    def __post_init__(self):
        if not self.field_path:
            raise ValueError("BriefChange.field_path must be non-empty")
        if self.operation not in self._ALLOWED_OPS:
            raise ValueError(
                f"BriefChange.operation must be one of {self._ALLOWED_OPS}; "
                f"got {self.operation!r}"
            )
        if not self.description:
            raise ValueError("BriefChange.description must be non-empty")

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "field_path": self.field_path,
            "operation": self.operation,
            "new_value": self.new_value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "BriefChange":
        return cls(
            field_path=payload["field_path"],
            operation=payload["operation"],
            new_value=payload.get("new_value"),
            description=payload["description"],
        )


@dataclass(frozen=True)
class CostImpact:
    """Transparency Triple for cost (Design Principle 2 + critique #9).

    v0.2.1 update (per critique #3): when confidence == LOW, caveat_language
    and uncertainty_pct are populated so UI can surface aggressive caveats.
    Numbers are NEVER hidden — we show them WITH the caveat.

    Fields:
        low_inr / midpoint_inr / high_inr — the Triple
        confidence — drives caveat language strength
        derivation — one-sentence explanation of where the numbers come from
        caveat_language — UI-ready caveat phrase, populated for LOW (and MED)
        uncertainty_pct — explicit ± percentage for LOW confidence display
    """
    low_inr: int
    midpoint_inr: int
    high_inr: int
    confidence: CostConfidence
    derivation: str
    # v0.2.1 additions:
    caveat_language: Optional[str] = None
    uncertainty_pct: Optional[int] = None

    def __post_init__(self):
        if not (self.low_inr <= self.midpoint_inr <= self.high_inr):
            raise ValueError(
                f"CostImpact must satisfy low <= midpoint <= high; got "
                f"({self.low_inr}, {self.midpoint_inr}, {self.high_inr})"
            )
        if not self.derivation:
            raise ValueError("CostImpact.derivation must be non-empty")

    @classmethod
    def build(cls, low: int, mid: int, high: int, confidence: CostConfidence,
              derivation: str) -> "CostImpact":
        """Convenience factory — auto-fills caveat_language and uncertainty_pct
        from confidence level. Use this in option_generator.py.
        """
        return cls(
            low_inr=low,
            midpoint_inr=mid,
            high_inr=high,
            confidence=confidence,
            derivation=derivation,
            caveat_language=confidence.default_caveat_language,
            uncertainty_pct=confidence.uncertainty_pct,
        )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "low_inr": self.low_inr,
            "midpoint_inr": self.midpoint_inr,
            "high_inr": self.high_inr,
            "confidence": self.confidence.value,
            "derivation": self.derivation,
            "caveat_language": self.caveat_language,
            "uncertainty_pct": self.uncertainty_pct,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CostImpact":
        return cls(
            low_inr=payload["low_inr"],
            midpoint_inr=payload["midpoint_inr"],
            high_inr=payload["high_inr"],
            confidence=CostConfidence(payload["confidence"]),
            derivation=payload["derivation"],
            caveat_language=payload.get("caveat_language"),
            uncertainty_pct=payload.get("uncertainty_pct"),
        )


# ═════════════════════════════════════════════════════════════════════════
# Resolution option + extreme case (the heart of the user-facing surface)
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ResolutionOption:
    """One option offered to the user for a given ExtremeCase.

    Per case there are typically 2-6 options (incl. Preview Mode last,
    "different plot" when triggered, and proceed-anyway for non-legal ECs).

    Fields:
        option_id           — stable identifier, e.g. "EC_001_OPT_A_DROP_LOWEST_PRIORITY"
        description         — one sentence, plain English
        impact_summary      — short consequence statement
                              ("Saves ~120 sqft, results in 2BHK + study")
        cost_impact         — None for options with no cost change
                              (Preview Mode, "look for different plot")
        space_impact_sqft   — signed delta from current brief
        recommended         — whether this option is the engine's recommendation
                              (multiple options may be recommended for different
                               reasons, with reasons distinguished by recommendation_reason)
        recommendation_reason — one-line explanation of why this option is recommended
                              ("best fit if shortfall < 200 sqft")
        requires_brief_change — atomic changes to apply if user picks this
                                (empty for Preview Mode and pure-action options)
        requires_action     — non-brief-mutation actions:
                              "EMAIL_CBA_CHECKLIST" | "PAUSE_FOR_USER_VERIFICATION" | None
        risk_advisory       — additional warning text
                              ("Sub-NBC: approval will need variance")
        is_preview_mode     — True for the Preview Mode option only
        is_different_plot_option — True for "look for a different plot"
                              options. Mutually exclusive with is_preview_mode.
                              When True: requires_brief_change MUST be ()
                              and requires_action MUST be None (different-plot
                              abandons the brief; doesn't modify it).
                              Added by B-027 v1.0 to remove S6's string-
                              matching dependency.
    """
    option_id: str
    description: str
    impact_summary: str
    cost_impact: Optional[CostImpact]
    space_impact_sqft: int
    recommended: bool
    recommendation_reason: Optional[str]
    requires_brief_change: tuple[BriefChange, ...]
    requires_action: Optional[str]
    risk_advisory: Optional[str]
    is_preview_mode: bool = False
    is_different_plot_option: bool = False

    def __post_init__(self):
        if not self.option_id:
            raise ValueError("ResolutionOption.option_id must be non-empty")
        if not self.description:
            raise ValueError("ResolutionOption.description must be non-empty")
        if not self.impact_summary:
            raise ValueError("ResolutionOption.impact_summary must be non-empty")
        if self.recommended and not self.recommendation_reason:
            raise ValueError(
                f"ResolutionOption {self.option_id}: when recommended=True, "
                f"recommendation_reason must be set"
            )
        if self.is_preview_mode and self.requires_brief_change:
            raise ValueError(
                f"ResolutionOption {self.option_id}: Preview Mode option "
                f"must not have brief changes (it sets a flag, not mutations)"
            )
        # B-027 P1: mutual exclusivity between Preview Mode and different-plot
        if self.is_preview_mode and self.is_different_plot_option:
            raise ValueError(
                f"ResolutionOption {self.option_id!r}: cannot be both "
                f"is_preview_mode=True and is_different_plot_option=True "
                f"(mutually exclusive strategies)"
            )
        # B-027 P6: structural constraints when is_different_plot_option=True.
        # Different-plot means abandon-this-brief; therefore it cannot modify
        # the brief or trigger an in-app action.
        if self.is_different_plot_option:
            if self.requires_brief_change != ():
                raise ValueError(
                    f"ResolutionOption {self.option_id!r}: when "
                    f"is_different_plot_option=True, requires_brief_change "
                    f"must be empty (different-plot abandons the brief; "
                    f"it doesn't modify it). Got: "
                    f"{self.requires_brief_change!r}"
                )
            if self.requires_action is not None:
                raise ValueError(
                    f"ResolutionOption {self.option_id!r}: when "
                    f"is_different_plot_option=True, requires_action "
                    f"must be None (different-plot has no in-app action). "
                    f"Got: {self.requires_action!r}"
                )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "option_id": self.option_id,
            "description": self.description,
            "impact_summary": self.impact_summary,
            "cost_impact": (
                self.cost_impact.to_dict()
                if self.cost_impact is not None else None
            ),
            "space_impact_sqft": self.space_impact_sqft,
            "recommended": self.recommended,
            "recommendation_reason": self.recommendation_reason,
            "requires_brief_change": [
                bc.to_dict() for bc in self.requires_brief_change
            ],
            "requires_action": self.requires_action,
            "risk_advisory": self.risk_advisory,
            "is_preview_mode": self.is_preview_mode,
            "is_different_plot_option": self.is_different_plot_option,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ResolutionOption":
        return cls(
            option_id=payload["option_id"],
            description=payload["description"],
            impact_summary=payload["impact_summary"],
            cost_impact=(
                CostImpact.from_dict(payload["cost_impact"])
                if payload.get("cost_impact") is not None else None
            ),
            space_impact_sqft=payload["space_impact_sqft"],
            recommended=payload.get("recommended", False),
            recommendation_reason=payload.get("recommendation_reason"),
            requires_brief_change=tuple(
                BriefChange.from_dict(bc)
                for bc in payload.get("requires_brief_change", [])
            ),
            requires_action=payload.get("requires_action"),
            risk_advisory=payload.get("risk_advisory"),
            is_preview_mode=payload.get("is_preview_mode", False),
            is_different_plot_option=payload.get(
                "is_different_plot_option", False
            ),
        )


@dataclass(frozen=True)
class ExtremeCase:
    """A single blocker presented to the user for resolution.

    Built by ExtremeCaseDetector + OptionGenerator. Surfaced in the UI
    one case at a time per Section 6.

    Fields:
        case_id                 — which of the 10 ECs this is
        category                — top-level category (drives priority order)
        blocking_gap_ids        — which C2 gap IDs from DesignGapAnalysis
                                  drove this detection
        user_facing_message     — filled-in message template, ready to display
        framing_line            — psychological framing line shown above options
                                  (per critique #8: "trade-offs are necessary")
        resolution_probability  — for EC-010 only; N/A elsewhere
        options                 — 2-6 ResolutionOptions
        detected_at_iteration   — 0 for first run, increments per loop
        transition_banner       — populated only when iter ∈ [2,3] AND
                                  case_id changed from previous resolved case
                                  (v0.2.1 critique #8: case_id, not category)
    """
    case_id: ExtremeCaseId
    category: ExtremeCaseCategory
    blocking_gap_ids: tuple[str, ...]
    user_facing_message: str
    framing_line: str
    resolution_probability: ResolutionProbability
    options: tuple[ResolutionOption, ...]
    detected_at_iteration: int
    transition_banner: Optional[str] = None

    def __post_init__(self):
        if len(self.options) < 2:
            raise ValueError(
                f"ExtremeCase {self.case_id.value}: must have at least 2 "
                f"options; got {len(self.options)}"
            )
        if not self.user_facing_message:
            raise ValueError(
                f"ExtremeCase {self.case_id.value}: user_facing_message required"
            )
        if not self.framing_line:
            raise ValueError(
                f"ExtremeCase {self.case_id.value}: framing_line required "
                f"(psychological layer per critique #8)"
            )
        if self.detected_at_iteration < 0:
            raise ValueError(
                f"ExtremeCase {self.case_id.value}: detected_at_iteration "
                f"must be >= 0; got {self.detected_at_iteration}"
            )
        # Preview Mode option, if present, must be last (Section 6 UI rule)
        preview_indices = [i for i, opt in enumerate(self.options)
                           if opt.is_preview_mode]
        if preview_indices and preview_indices[0] != len(self.options) - 1:
            raise ValueError(
                f"ExtremeCase {self.case_id.value}: Preview Mode option "
                f"must be the LAST option in the option set (Section 6)"
            )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id.value,
            "category": self.category.value,
            "blocking_gap_ids": list(self.blocking_gap_ids),
            "user_facing_message": self.user_facing_message,
            "framing_line": self.framing_line,
            "resolution_probability": self.resolution_probability.value,
            "options": [o.to_dict() for o in self.options],
            "detected_at_iteration": self.detected_at_iteration,
            "transition_banner": self.transition_banner,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ExtremeCase":
        return cls(
            case_id=ExtremeCaseId(payload["case_id"]),
            category=ExtremeCaseCategory(payload["category"]),
            blocking_gap_ids=tuple(payload["blocking_gap_ids"]),
            user_facing_message=payload["user_facing_message"],
            framing_line=payload["framing_line"],
            resolution_probability=ResolutionProbability(
                payload["resolution_probability"]
            ),
            options=tuple(
                ResolutionOption.from_dict(o) for o in payload["options"]
            ),
            detected_at_iteration=payload["detected_at_iteration"],
            transition_banner=payload.get("transition_banner"),
        )


# ═════════════════════════════════════════════════════════════════════════
# Decision logging (Q3 Level B: chosen + full presented option set)
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ExtremeDecision:
    """Record of one user choice on one ExtremeCase.

    Per Q3 (Level B logging): we capture both the chosen_option_id AND
    the full presented_options set. This enables future analytics like
    "which alternatives are systematically underused?" without per-option
    click telemetry (deferred to v2).

    Fields:
        case_id              — which case this decision was for
        chosen_option_id     — the option_id user picked
        chosen_option_description — snapshot for audit
                                    (presented_options is also kept, but
                                     description is duplicated here for
                                     readability when scanning logs)
        presented_options    — FULL option set the user saw at the time
        user_acknowledged_at — ISO 8601 timestamp
        iteration_index      — 0, 1, 2, ... within the C3a session
    """
    case_id: ExtremeCaseId
    chosen_option_id: str
    chosen_option_description: str
    presented_options: tuple[ResolutionOption, ...]
    user_acknowledged_at: str
    iteration_index: int

    def __post_init__(self):
        # Sanity check: chosen_option_id must be in presented_options
        ids = [opt.option_id for opt in self.presented_options]
        if self.chosen_option_id not in ids:
            raise ValueError(
                f"ExtremeDecision: chosen_option_id {self.chosen_option_id!r} "
                f"not in presented_options {ids!r}"
            )
        if self.iteration_index < 0:
            raise ValueError(
                f"ExtremeDecision.iteration_index must be >= 0; "
                f"got {self.iteration_index}"
            )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id.value,
            "chosen_option_id": self.chosen_option_id,
            "chosen_option_description": self.chosen_option_description,
            "presented_options": [
                o.to_dict() for o in self.presented_options
            ],
            "user_acknowledged_at": self.user_acknowledged_at,
            "iteration_index": self.iteration_index,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ExtremeDecision":
        return cls(
            case_id=ExtremeCaseId(payload["case_id"]),
            chosen_option_id=payload["chosen_option_id"],
            chosen_option_description=payload["chosen_option_description"],
            presented_options=tuple(
                ResolutionOption.from_dict(o)
                for o in payload["presented_options"]
            ),
            user_acknowledged_at=payload["user_acknowledged_at"],
            iteration_index=payload["iteration_index"],
        )


# ═════════════════════════════════════════════════════════════════════════
# Counterfactual + Preflight + Preview acknowledgment (v0.2.1 additions)
# ═════════════════════════════════════════════════════════════════════════

# Default framing line used in CounterfactualSummary per critique #5.
# Surfaces above the alternatives list to prevent regret/decision paralysis.
DEFAULT_COUNTERFACTUAL_FRAMING = (
    "These were valid alternatives at the time. "
    "There is no single 'correct' choice."
)


@dataclass(frozen=True)
class CounterfactualSummary:
    """Per Reaction 1 + v0.2.1 critique #5: shown on final ResolvedBrief
    screen so families can discuss alternatives.

    v0.2.1 changes:
        - Max 2 alternatives per decision (was unlimited; decision-paralysis risk)
        - framing_line shown above alternatives ("there is no single correct choice")
        - Preview Mode STAYS in alternatives, formatted neutrally (rejected
          critique's hide-Preview proposal — honesty over comfort)

    Fields:
        case_id              — which case this counterfactual is for
        chosen_option_id     — what user actually picked
        chosen_outcome       — description of what their choice did
        alternatives         — max 2 tuples of (option_id, description, "would have" outcome)
        framing_line         — defaults to DEFAULT_COUNTERFACTUAL_FRAMING
    """
    case_id: ExtremeCaseId
    chosen_option_id: str
    chosen_outcome: str
    alternatives: tuple[tuple[str, str, str], ...]
    framing_line: str = DEFAULT_COUNTERFACTUAL_FRAMING

    _MAX_ALTERNATIVES = 2

    def __post_init__(self):
        if len(self.alternatives) > self._MAX_ALTERNATIVES:
            raise ValueError(
                f"CounterfactualSummary: max {self._MAX_ALTERNATIVES} "
                f"alternatives per decision (v0.2.1 critique #5); "
                f"got {len(self.alternatives)}"
            )
        for alt in self.alternatives:
            if len(alt) != 3:
                raise ValueError(
                    f"CounterfactualSummary.alternatives entry must be "
                    f"(option_id, description, would_have_text); got {alt!r}"
                )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id.value,
            "chosen_option_id": self.chosen_option_id,
            "chosen_outcome": self.chosen_outcome,
            # tuple[tuple[str, str, str], ...] → list[list[str]] for JSON
            "alternatives": [list(alt) for alt in self.alternatives],
            "framing_line": self.framing_line,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "CounterfactualSummary":
        return cls(
            case_id=ExtremeCaseId(payload["case_id"]),
            chosen_option_id=payload["chosen_option_id"],
            chosen_outcome=payload["chosen_outcome"],
            alternatives=tuple(
                # JSON list-of-lists → tuple-of-tuples
                tuple(alt) for alt in payload.get("alternatives", [])
            ),
            framing_line=payload.get(
                "framing_line", DEFAULT_COUNTERFACTUAL_FRAMING
            ),
        )


@dataclass(frozen=True)
class PreflightSummary:
    """v0.2.1 NEW (per critique #2 + #4).

    Shown BEFORE the first EC modal as a non-blocking summary screen.
    Sets correct expectation that multiple constraints exist and they
    interact ("fixing one may affect others").

    Per critique #4: when ANY of {EC-006 severe, EC-010 LOW probability,
    EC-002 physical tier} is present, an early non-blocking "wrong plot"
    hint is also surfaced — plants reality before user invests effort
    in iterating.

    Fields:
        total_blocker_count  — N
        blocker_categories   — unique categories present (deduped)
        summary_message      — UI-ready text, e.g. "We found 3 constraints..."
        early_plot_hint      — populated only when severe single-EC fires;
                               None otherwise
    """
    total_blocker_count: int
    blocker_categories: tuple[ExtremeCaseCategory, ...]
    summary_message: str
    early_plot_hint: Optional[str] = None

    def __post_init__(self):
        if self.total_blocker_count < 1:
            raise ValueError(
                f"PreflightSummary.total_blocker_count must be >= 1 "
                f"(only built when blockers exist); got {self.total_blocker_count}"
            )
        if not self.summary_message:
            raise ValueError("PreflightSummary.summary_message required")

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "total_blocker_count": self.total_blocker_count,
            "blocker_categories": [
                c.value for c in self.blocker_categories
            ],
            "summary_message": self.summary_message,
            "early_plot_hint": self.early_plot_hint,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PreflightSummary":
        return cls(
            total_blocker_count=payload["total_blocker_count"],
            blocker_categories=tuple(
                ExtremeCaseCategory(c)
                for c in payload["blocker_categories"]
            ),
            summary_message=payload["summary_message"],
            early_plot_hint=payload.get("early_plot_hint"),
        )


@dataclass(frozen=True)
class PreviewModeAcknowledgment:
    """v0.2.1 NEW (per critique #1 — CRITICAL Preview Mode misuse risk).

    Mandatory acknowledgment record persisted in ExtremeDecisionLog when
    user proceeds with Preview Mode. The acknowledgment text is captured
    verbatim so the audit trail proves the user explicitly understood
    the Preview was not buildable.

    The user_session_id ties this to the broader session log. If a Preview
    Mode layout is ever shared with a contractor and an issue arises, this
    record is the audit trail that the user explicitly acknowledged the
    layout was non-buildable.

    Fields:
        user_acknowledged_at  — ISO 8601 timestamp
        acknowledgment_text   — exact text shown to user (not paraphrased)
        user_session_id       — for cross-system audit
    """
    user_acknowledged_at: str
    acknowledgment_text: str
    user_session_id: str

    def __post_init__(self):
        if not self.user_acknowledged_at:
            raise ValueError(
                "PreviewModeAcknowledgment.user_acknowledged_at required "
                "(audit invariant)"
            )
        if not self.acknowledgment_text:
            raise ValueError(
                "PreviewModeAcknowledgment.acknowledgment_text required "
                "(audit invariant — must capture exact text user saw)"
            )
        if not self.user_session_id:
            raise ValueError(
                "PreviewModeAcknowledgment.user_session_id required "
                "(audit invariant)"
            )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "user_acknowledged_at": self.user_acknowledged_at,
            "acknowledgment_text": self.acknowledgment_text,
            "user_session_id": self.user_session_id,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PreviewModeAcknowledgment":
        return cls(
            user_acknowledged_at=payload["user_acknowledged_at"],
            acknowledgment_text=payload["acknowledgment_text"],
            user_session_id=payload["user_session_id"],
        )


# ═════════════════════════════════════════════════════════════════════════
# Decision log + final output (ResolvedBrief)
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ExtremeDecisionLog:
    """Full record of all decisions in one C3a session.

    Possible abort_reasons:
        "USER_ABORTED"               — user clicked "Save and exit"
        "MAX_ITERATIONS_REACHED"     — hit 7-iteration cap
        "PER_CASE_LIMIT_REACHED"     — same case_id fired 3 times
        "USER_CHOSE_PREVIEW_MODE"    — user elected to bypass via Preview
                                       (note: this is NOT a true abort —
                                        ResolvedBrief.is_layout_ready=True
                                        because PREVIEW is a valid output mode)
        "AWAITING_CBA_VERIFICATION"  — user picked "verify CBA" option;
                                       brief paused as draft, email sent

    Fields:
        started_at        — ISO 8601 timestamp (when first EC was surfaced)
        completed_at      — ISO 8601; None if aborted mid-flow
        decisions         — chronological tuple of every choice made
        iterations_used   — count of C2 re-runs triggered
        aborted           — True if any abort_reason set; False on clean finish
        abort_reason      — see list above
    """
    started_at: str
    completed_at: Optional[str]
    decisions: tuple[ExtremeDecision, ...]
    iterations_used: int
    aborted: bool
    abort_reason: Optional[str] = None

    def __post_init__(self):
        if self.aborted and not self.abort_reason:
            raise ValueError(
                "ExtremeDecisionLog: aborted=True requires abort_reason"
            )
        if not self.aborted and self.abort_reason:
            raise ValueError(
                f"ExtremeDecisionLog: abort_reason set ({self.abort_reason!r}) "
                f"but aborted=False; this is inconsistent"
            )
        if self.iterations_used < 0:
            raise ValueError(
                f"ExtremeDecisionLog.iterations_used must be >= 0; "
                f"got {self.iterations_used}"
            )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "decisions": [d.to_dict() for d in self.decisions],
            "iterations_used": self.iterations_used,
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ExtremeDecisionLog":
        return cls(
            started_at=payload["started_at"],
            completed_at=payload.get("completed_at"),
            decisions=tuple(
                ExtremeDecision.from_dict(d)
                for d in payload.get("decisions", [])
            ),
            iterations_used=payload["iterations_used"],
            aborted=payload["aborted"],
            abort_reason=payload.get("abort_reason"),
        )


@dataclass(frozen=True)
class ResolvedBrief:
    """Final output of Component 3a. Forwarded to layout pipeline.

    Two modes:
        BUILDABLE — all blockers resolved; layout pipeline runs normally
        PREVIEW   — user chose Preview Mode for one or more blockers;
                    layout pipeline reads relaxed_constraints and
                    skips those checks. Renderer (C16) reads mode and
                    produces reduced output (Section 4.5):
                      - 1 layout, not 3
                      - dimensions as ranges, not exact
                      - watermarks INSIDE rooms (not just page edges)
                      - no door swings, electrical, plumbing, structural
                      - no BOQ, no regulatory drawing, no contractor pack

    Fields (all immutable):
        original_brief                    — what came in from C1
        revised_brief                     — what goes to layout (may equal
                                             original if Preview Mode used
                                             with no resolutions)
        decision_log                      — full audit trail
        final_feasibility                 — last C2 result;
                                             empty gaps in BUILDABLE mode,
                                             unresolved blockers in PREVIEW mode
        mode                              — BUILDABLE or PREVIEW
        is_layout_ready                   — True iff (mode==BUILDABLE and not aborted)
                                             OR mode==PREVIEW (preview is valid output)
        counterfactuals                   — per Reaction 1; for family discussion
        unresolved_blockers               — Preview Mode only; cases user bypassed
        relaxed_constraints               — Preview Mode only; constraint names
                                             downstream layout pipeline must skip
        preflight_summary                 — populated when ECs were found
                                             (not present if happy path, no ECs)
        preview_mode_acknowledgment       — populated only in PREVIEW mode;
                                             audit record of explicit consent
    """
    original_brief: Any   # Brief — forward ref to avoid circular import
    revised_brief: Any    # Brief
    decision_log: ExtremeDecisionLog
    final_feasibility: Any  # DesignGapAnalysis — forward ref
    mode: BriefMode
    is_layout_ready: bool
    counterfactuals: tuple[CounterfactualSummary, ...]
    unresolved_blockers: tuple[ExtremeCase, ...]
    relaxed_constraints: tuple[str, ...]
    # v0.2.1 additions:
    preflight_summary: Optional[PreflightSummary] = None
    preview_mode_acknowledgment: Optional[PreviewModeAcknowledgment] = None

    def __post_init__(self):
        # Mode-mode consistency invariants
        if self.mode == BriefMode.PREVIEW:
            if not self.unresolved_blockers:
                raise ValueError(
                    "ResolvedBrief: mode=PREVIEW requires unresolved_blockers "
                    "to be non-empty (Preview Mode exists to bypass blockers)"
                )
            if not self.relaxed_constraints:
                raise ValueError(
                    "ResolvedBrief: mode=PREVIEW requires relaxed_constraints "
                    "to be non-empty (downstream pipeline reads this list)"
                )
            if self.preview_mode_acknowledgment is None:
                raise ValueError(
                    "ResolvedBrief: mode=PREVIEW requires "
                    "preview_mode_acknowledgment (v0.2.1 critique #1)"
                )
        else:  # BUILDABLE
            if self.unresolved_blockers:
                raise ValueError(
                    "ResolvedBrief: mode=BUILDABLE must not have "
                    "unresolved_blockers; got "
                    f"{len(self.unresolved_blockers)}"
                )
            if self.relaxed_constraints:
                raise ValueError(
                    "ResolvedBrief: mode=BUILDABLE must not have "
                    "relaxed_constraints; got {self.relaxed_constraints!r}"
                )
            if self.preview_mode_acknowledgment is not None:
                raise ValueError(
                    "ResolvedBrief: mode=BUILDABLE must not have "
                    "preview_mode_acknowledgment"
                )

        # is_layout_ready consistency
        if self.mode == BriefMode.PREVIEW and not self.is_layout_ready:
            raise ValueError(
                "ResolvedBrief: mode=PREVIEW always implies "
                "is_layout_ready=True (Preview is a valid layout output mode)"
            )
        if self.decision_log.aborted and self.is_layout_ready:
            # Exception: USER_CHOSE_PREVIEW_MODE is not a true abort
            valid_aborted_with_layout = (
                self.decision_log.abort_reason == "USER_CHOSE_PREVIEW_MODE"
            )
            if not valid_aborted_with_layout:
                raise ValueError(
                    "ResolvedBrief: aborted decision_log inconsistent with "
                    f"is_layout_ready=True (abort_reason="
                    f"{self.decision_log.abort_reason!r})"
                )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "original_brief": self.original_brief.to_dict(),
            "revised_brief": self.revised_brief.to_dict(),
            "decision_log": self.decision_log.to_dict(),
            "final_feasibility": self.final_feasibility.to_dict(),
            "mode": self.mode.value,
            "is_layout_ready": self.is_layout_ready,
            "counterfactuals": [
                c.to_dict() for c in self.counterfactuals
            ],
            "unresolved_blockers": [
                b.to_dict() for b in self.unresolved_blockers
            ],
            "relaxed_constraints": list(self.relaxed_constraints),
            "preflight_summary": (
                self.preflight_summary.to_dict()
                if self.preflight_summary is not None else None
            ),
            "preview_mode_acknowledgment": (
                self.preview_mode_acknowledgment.to_dict()
                if self.preview_mode_acknowledgment is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ResolvedBrief":
        # Lazy imports to avoid circular layering: ResolvedBrief is in
        # extreme_case.py but original_brief/revised_brief are Brief and
        # final_feasibility is DesignGapAnalysis.
        from buildemup.domain.brief import Brief
        from buildemup.domain.feasibility import DesignGapAnalysis
        return cls(
            original_brief=Brief.from_dict(payload["original_brief"]),
            revised_brief=Brief.from_dict(payload["revised_brief"]),
            decision_log=ExtremeDecisionLog.from_dict(
                payload["decision_log"]
            ),
            final_feasibility=DesignGapAnalysis.from_dict(
                payload["final_feasibility"]
            ),
            mode=BriefMode(payload["mode"]),
            is_layout_ready=payload["is_layout_ready"],
            counterfactuals=tuple(
                CounterfactualSummary.from_dict(c)
                for c in payload.get("counterfactuals", [])
            ),
            unresolved_blockers=tuple(
                ExtremeCase.from_dict(b)
                for b in payload.get("unresolved_blockers", [])
            ),
            relaxed_constraints=tuple(
                payload.get("relaxed_constraints", [])
            ),
            preflight_summary=(
                PreflightSummary.from_dict(payload["preflight_summary"])
                if payload.get("preflight_summary") is not None else None
            ),
            preview_mode_acknowledgment=(
                PreviewModeAcknowledgment.from_dict(
                    payload["preview_mode_acknowledgment"]
                )
                if payload.get("preview_mode_acknowledgment") is not None
                else None
            ),
        )


# ═════════════════════════════════════════════════════════════════════════
# Custom exceptions
# ═════════════════════════════════════════════════════════════════════════

class BriefChangeIntegrityError(Exception):
    """Raised by apply_brief_change() when the resulting Brief fails
    Brief.__post_init__ validation. Per Section 3.3 integrity invariant:
    we never let a malformed Brief reach C2.

    Per critique #7 (v0.2.1 fix): this error carries a `classify()` method
    that returns one of a known set of validation failure types, plus a
    `context` dict with relevant numeric data. The error_formatter uses
    these to build user-facing reason text (Section 4.8).
    """
    def __init__(self, message: str, classification: str = "UNKNOWN",
                 context: Optional[dict] = None):
        super().__init__(message)
        self._classification = classification
        self.context = context or {}

    def classify(self) -> str:
        """Return classification string. Known classifications:
            BEDROOM_COUNT_BELOW_MIN
            BUDGET_BELOW_THRESHOLD
            FAR_EXCEEDED_BY_CHANGE
            ROOM_AREA_BELOW_NBC_MIN
            FLOOR_COUNT_BELOW_MIN
            UNKNOWN
        """
        return self._classification


# ═════════════════════════════════════════════════════════════════════════
# _DOMAIN_TYPE_NAMES registration (for utils/component_contract.py v0.7.1)
#
# All 15 types must be registered (5 enums + 10 dataclasses). Listed here
# for the component_contract enforcement test to discover.
# ═════════════════════════════════════════════════════════════════════════

EXTREME_CASE_DOMAIN_TYPE_NAMES = (
    # 5 enums
    "ExtremeCaseCategory",
    "ExtremeCaseId",
    "ResolutionProbability",
    "BriefMode",
    "CostConfidence",
    # 10 dataclasses
    "BriefChange",
    "CostImpact",
    "ResolutionOption",
    "ExtremeCase",
    "ExtremeDecision",
    "ExtremeDecisionLog",
    "CounterfactualSummary",
    "PreflightSummary",
    "PreviewModeAcknowledgment",
    "ResolvedBrief",
)
