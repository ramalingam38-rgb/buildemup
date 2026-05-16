"""
BuildemUp† — Brief domain object (Component 1 top-level output).

Per SPEC_v0.2 Section 2.1 — captures everything we need about the user's
homebuilding intent, with compliance checks and soft-guide messages.

Structure:
  Brief
    ├── plot                       : Plot
    ├── user_stated_setbacks       : Setbacks (what user wants)
    ├── nbc_compliant_setbacks     : Setbacks (what the DCR requires)
    ├── floors                     : tuple[FloorRequirement, ...]
    ├── budget_range               : BudgetRange (min/max lakhs INR)
    ├── additional_requirements    : tuple[str, ...]
    ├── soft_guidance              : all GuidanceMessage
    ├── top_guidance               : top 3 GuidanceMessage (Drawback 6)
    ├── vastu_preference           : VastuTier (Q5)
    ├── user_email / user_phone    : optional (Q2)
    ├── resume_token               : optional (Q3)
    ├── assumptions_used           : tuple[str, ...] (Drawback 10)
    ├── trace_id
    └── kb_versions

This file also defines the supporting types:
  - VastuTier         : OFF / PARTIAL / FULL
  - BudgetRange       : min/max in lakhs INR
  - GuidanceSeverity  : INFO / CONCERN / STRONG_CONCERN
  - GuidanceMessage   : one soft-guide message
  - ComplianceSummary : setback compliance overview
  - CostEstimate      : budget output from Component 7 (Drawback 4)

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from buildemup.domain.exceptions import (
    BudgetValidationError,
    FloorCountTooLowError,
)
from buildemup.domain.plot import Plot
from buildemup.domain.setbacks import Setbacks
from buildemup.domain.floor_requirement import FloorRequirement, FloorUse


# ─────────────────────────────────────────────────────────────────────────
# Vastu (Q5 — three-tier opt-in)
# ─────────────────────────────────────────────────────────────────────────
class VastuTier(str, Enum):
    """Vastu guidance level user picks on the form.

    All tiers produce INFO-severity messages only — vastu is a cultural
    preference, never a building-code requirement. Component 1 never
    blocks or downgrades based on vastu.
    """
    OFF = "off"          # No vastu guidance (default)
    PARTIAL = "partial"  # 7 core items (see VASTU_PARTIAL_ITEMS)
    FULL = "full"        # Everything in vastu_engine KB


# The 7 PARTIAL vastu items, shown to the user on the form so they
# know exactly what they're opting into. No hidden behaviour.
VASTU_PARTIAL_ITEMS: tuple[str, ...] = (
    "Main door direction (most important)",
    "Kitchen direction (southeast preferred)",
    "Master bedroom direction (southwest preferred)",
    "Pooja room direction (northeast preferred)",
    "Toilet/bathroom location (avoid northeast)",
    "Staircase direction (avoid northeast)",
    "Water tank location (underground northeast / overhead southwest)",
)


# ─────────────────────────────────────────────────────────────────────────
# Budget
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class BudgetRange:
    """User's construction budget range in lakhs INR.

    v0.1 hardcodes INR per Q1. Currency field retained for v0.2
    international support without breaking changes.
    """
    min_lakhs: int
    max_lakhs: int
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.min_lakhs < 1:
            raise BudgetValidationError(
                f"budget min_lakhs={self.min_lakhs} is implausibly low. "
                f"Minimum ₹1L for even basic G-only construction."
            )
        if self.max_lakhs < self.min_lakhs:
            raise BudgetValidationError(
                f"budget max_lakhs ({self.max_lakhs}) < "
                f"min_lakhs ({self.min_lakhs})."
            )
        if self.max_lakhs > 10_000:
            # 10 crore (1000 lakh) cap for v0.1 — mansion tier
            raise ValueError(
                f"budget max_lakhs={self.max_lakhs} exceeds ₹100Cr cap. "
                f"Commercial / ultra-luxury beyond v0.1 scope."
            )
        if self.currency != "INR":
            raise ValueError(
                f"v0.1 supports INR only. Got: {self.currency}"
            )

    @property
    def min_rupees(self) -> int:
        return self.min_lakhs * 100_000

    @property
    def max_rupees(self) -> int:
        return self.max_lakhs * 100_000

    def describe(self) -> str:
        return f"₹{self.min_lakhs}L – ₹{self.max_lakhs}L INR"

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "min_lakhs": self.min_lakhs,
            "max_lakhs": self.max_lakhs,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "BudgetRange":
        return cls(
            min_lakhs=payload["min_lakhs"],
            max_lakhs=payload["max_lakhs"],
            currency=payload.get("currency", "INR"),
        )


# ─────────────────────────────────────────────────────────────────────────
# Cost estimate (from Component 7 per Drawback 4)
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CostEstimate:
    """Cost estimate returned by Component 7 for budget guidance.

    Per SPEC_v0.2 Section 5.1 Drawback 4 fix:
    Component 1 does NOT have its own cost engine. It delegates to
    Component 7's cost module and wraps the result in this type.
    """
    exact_value: float           # Component 7's point estimate (INR)
    range_min: float             # Lower bound of Component 7's range
    range_max: float             # Upper bound of Component 7's range
    confidence: str              # "HIGH" / "MEDIUM" / "LOW" from Component 7
    source: str                  # e.g., "Component 7 cost engine"

    def __post_init__(self) -> None:
        if self.range_min > self.exact_value:
            raise ValueError(
                f"CostEstimate range_min ({self.range_min}) > "
                f"exact_value ({self.exact_value})."
            )
        if self.range_max < self.exact_value:
            raise ValueError(
                f"CostEstimate range_max ({self.range_max}) < "
                f"exact_value ({self.exact_value})."
            )
        if self.exact_value <= 0:
            raise ValueError(
                f"CostEstimate exact_value must be > 0: {self.exact_value}"
            )


# ─────────────────────────────────────────────────────────────────────────
# Guidance (soft-guide messages per SPEC Section 6)
# ─────────────────────────────────────────────────────────────────────────
class GuidanceSeverity(str, Enum):
    """Three-tier severity for soft-guide messages."""
    INFO = "info"
    CONCERN = "concern"
    STRONG_CONCERN = "strong_concern"


@dataclass(frozen=True)
class GuidanceMessage:
    """One soft-guide message shown to the user.

    Phrasing rules (SPEC_v0.2 Section 6):
      - Always second-person ("Your front setback of...")
      - Always include source/reason (action_verb = what to do)
      - Never use "must" / "cannot" — use "may not" / "consider"
    """
    severity: GuidanceSeverity
    text: str                    # The message shown to user
    context: str                 # Short tag, e.g., "setback_violation"
    action_verb: str             # One of: "Consider", "Adjust", "Reconsider",
                                 #         "Review", "Increase", "Reduce"

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("GuidanceMessage text cannot be empty.")
        if not self.context.strip():
            raise ValueError("GuidanceMessage context cannot be empty.")

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "text": self.text,
            "context": self.context,
            "action_verb": self.action_verb,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GuidanceMessage":
        return cls(
            severity=GuidanceSeverity(payload["severity"]),
            text=payload["text"],
            context=payload["context"],
            action_verb=payload["action_verb"],
        )


# ─────────────────────────────────────────────────────────────────────────
# Compliance summary
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ComplianceSummary:
    """High-level compliance overview (setback focus for v0.1)."""
    is_setback_compliant: bool
    setback_violations: tuple[str, ...]     # Human-readable violation messages
    source_authority: str                    # e.g., "TNCDBR 2019"


# ─────────────────────────────────────────────────────────────────────────
# Brief (top-level)
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Brief:
    """Top-level output of Component 1.

    Feeds into Component 7 (and later Component 4 layout) via
    to_structural_grid_input() method.
    """
    plot: Plot
    user_stated_setbacks: Setbacks
    nbc_compliant_setbacks: Setbacks
    floors: tuple[FloorRequirement, ...]
    budget_range: BudgetRange
    additional_requirements: tuple[str, ...] = ()
    soft_guidance: tuple[GuidanceMessage, ...] = ()
    top_guidance: tuple[GuidanceMessage, ...] = ()
    vastu_preference: VastuTier = VastuTier.OFF
    user_email: str | None = None
    user_phone: str | None = None
    resume_token: str | None = None
    assumptions_used: tuple[str, ...] = ()
    trace_id: str = ""
    kb_versions: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.floors) < 1:
            raise FloorCountTooLowError(
                "Brief requires at least one floor (ground floor)."
            )
        if len(self.floors) > 4:
            # Ground + G+3 = 4 floors max in v0.1
            raise ValueError(
                f"Brief has {len(self.floors)} floors — v0.1 max is "
                f"G+3 (4 floors total). Taller buildings need high-rise "
                f"review (NBC Part 4 fire safety), out of scope."
            )

        # Floor numbers must be 0, 1, 2, 3, ... contiguous
        expected_numbers = set(range(len(self.floors)))
        actual_numbers = {f.floor_number for f in self.floors}
        if actual_numbers != expected_numbers:
            raise ValueError(
                f"Floor numbers must be contiguous starting at 0. "
                f"Expected {sorted(expected_numbers)}, got "
                f"{sorted(actual_numbers)}."
            )

        # Only top floor can be TERRACE_*
        for i, f in enumerate(self.floors):
            if f.floor_use in (
                FloorUse.TERRACE_ACCESSIBLE, FloorUse.TERRACE_INACCESSIBLE
            ) and i != len(self.floors) - 1:
                raise ValueError(
                    f"TERRACE floor at position {i} — terrace can only "
                    f"be the top floor."
                )

        # Only ground floor (0) can be STILT_PARKING
        for f in self.floors:
            if (f.floor_use == FloorUse.STILT_PARKING
                    and f.floor_number != 0):
                raise ValueError(
                    f"STILT_PARKING must be ground floor (floor_number=0). "
                    f"Got floor_number={f.floor_number}."
                )

        # top_guidance should be a subset of soft_guidance (if both given)
        # We don't strictly enforce — just a sanity note for reviewers.

    @property
    def has_stilt_parking(self) -> bool:
        """True if ground floor is stilt parking."""
        return any(
            f.floor_use == FloorUse.STILT_PARKING for f in self.floors
        )

    @property
    def total_floors_above_ground(self) -> int:
        """Count of floors ABOVE ground (floor_number > 0).

        Used by Component 7 as floors_above_ground after terrace
        handling in to_structural_grid_input().

        Per Drawback 3 clarification: this counts terrace too because
        terrace is load-bearing.
        """
        return sum(1 for f in self.floors if f.floor_number > 0)

    def describe(self) -> str:
        """One-liner for logs."""
        return (
            f"Brief: {self.plot.describe()} | "
            f"{len(self.floors)} floors | "
            f"Budget {self.budget_range.describe()} | "
            f"Vastu: {self.vastu_preference.value}"
        )

    # ─── S7a serialization ───────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "plot": self.plot.to_dict(),
            "user_stated_setbacks": self.user_stated_setbacks.to_dict(),
            "nbc_compliant_setbacks": self.nbc_compliant_setbacks.to_dict(),
            "floors": [f.to_dict() for f in self.floors],
            "budget_range": self.budget_range.to_dict(),
            "additional_requirements": list(self.additional_requirements),
            "soft_guidance": [g.to_dict() for g in self.soft_guidance],
            "top_guidance": [g.to_dict() for g in self.top_guidance],
            "vastu_preference": self.vastu_preference.value,
            "user_email": self.user_email,
            "user_phone": self.user_phone,
            "resume_token": self.resume_token,
            "assumptions_used": list(self.assumptions_used),
            "trace_id": self.trace_id,
            "kb_versions": dict(self.kb_versions) if self.kb_versions else {},
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Brief":
        return cls(
            plot=Plot.from_dict(payload["plot"]),
            user_stated_setbacks=Setbacks.from_dict(
                payload["user_stated_setbacks"]
            ),
            nbc_compliant_setbacks=Setbacks.from_dict(
                payload["nbc_compliant_setbacks"]
            ),
            floors=tuple(
                FloorRequirement.from_dict(f) for f in payload["floors"]
            ),
            budget_range=BudgetRange.from_dict(payload["budget_range"]),
            additional_requirements=tuple(
                payload.get("additional_requirements", [])
            ),
            soft_guidance=tuple(
                GuidanceMessage.from_dict(g)
                for g in payload.get("soft_guidance", [])
            ),
            top_guidance=tuple(
                GuidanceMessage.from_dict(g)
                for g in payload.get("top_guidance", [])
            ),
            vastu_preference=VastuTier(
                payload.get("vastu_preference", "OFF")
            ),
            user_email=payload.get("user_email"),
            user_phone=payload.get("user_phone"),
            resume_token=payload.get("resume_token"),
            assumptions_used=tuple(payload.get("assumptions_used", [])),
            trace_id=payload.get("trace_id", ""),
            kb_versions=dict(payload.get("kb_versions") or {}),
        )

    # ─── Component 7 handoff (Drawbacks 2 + 3) ───────────────────────────
    def to_structural_grid_input(self) -> "StructuralGridInput":  # type: ignore  # noqa
        """Convert Brief into Component 7's StructuralGridInput.

        Per SPEC_v0.2 Section 10.1:

        Drawback 2 (envelope):
          Compute rectangular envelope = plot dimensions MINUS the
          NBC-compliant setbacks on each side. Assumes rectangular
          buildable area — layout engine (Component 4, later) may
          refine this. The `is_rectangular=True` assumption is
          recorded in brief.assumptions_used for transparency.

        Drawback 3 (floor count):
          floors_above_ground = number of floors ABOVE the ground
          slab. In Component 7's terms:
            - Ground floor (floor_number=0) is always counted as
              the baseline structural level.
            - Every floor with floor_number > 0 counts as
              "above ground" — this includes STILT_PARKING,
              RESIDENTIAL, TERRACE_ACCESSIBLE, TERRACE_INACCESSIBLE.
            - Component 7 uses this to compute column loads, drift, etc.
          For a G+1 brief: 2 floors total, floors_above_ground=1.
          For a stilt+G+1 brief (3 floors): floors_above_ground=2.

        Seismic zone derived from plot.city via CITY_TO_SEISMIC_ZONE.

        Returns:
          StructuralGridInput ready for StructuralGridEngine.execute().
        """
        # Imported here to avoid circular import at module load time
        from buildemup.components.c07_structural_grid import (
            StructuralGridInput,
        )
        from buildemup.components.c01.budget_bridge import (
            get_seismic_zone_for_city,
        )
        from buildemup.domain.floor_requirement import FloorUse

        # Drawback 2: rectangular envelope derived from plot - setbacks.
        # If the result is too small or negative, we cap at Component 7's
        # minimum (5m × 5m per its __post_init__ check). This is a
        # defensive floor — the soft-guide engine will separately warn the
        # user that their plot + setbacks leaves very little buildable
        # area.
        envelope_width_m = max(
            5.0,
            self.plot.width_m
            - self.nbc_compliant_setbacks.side_left_m
            - self.nbc_compliant_setbacks.side_right_m,
        )
        envelope_depth_m = max(
            5.0,
            self.plot.depth_m
            - self.nbc_compliant_setbacks.front_m
            - self.nbc_compliant_setbacks.rear_m,
        )

        # Drawback 3: count floors ABOVE ground (floor_number > 0).
        # All floor_uses count as load-bearing — stilt, residential,
        # and both terrace variants.
        floors_above_ground = sum(
            1 for f in self.floors if f.floor_number > 0
        )

        # Stilt detection for Component 7's has_stilt_parking flag
        has_stilt = any(
            f.floor_use == FloorUse.STILT_PARKING for f in self.floors
        )

        # Seismic zone from city
        seismic_zone = get_seismic_zone_for_city(self.plot.city)

        return StructuralGridInput(
            envelope_width_m=float(envelope_width_m),
            envelope_depth_m=float(envelope_depth_m),
            floors_above_ground=int(floors_above_ground),
            city=self.plot.city,
            seismic_zone=seismic_zone,
            has_stilt_parking=has_stilt,
            has_terrace_access=any(
                f.floor_use == FloorUse.TERRACE_ACCESSIBLE
                for f in self.floors
            ),
            has_water_tank=True,  # default — most Indian residential
            plot_facing=self.plot.facing.value,
            # v0.1 of Component 1 doesn't capture these — defaults:
            terrain_category="urban",
            re_entrant_corner_x_m=0.0,
            re_entrant_corner_y_m=0.0,
            is_property_line_edge=False,
            user_claims_engineer_reviewed=False,
        )
