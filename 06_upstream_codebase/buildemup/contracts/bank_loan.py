"""
Bank loan partnership contract.

Phase 1 vision: integrate with SBI, HDFC, ICICI for home loan referrals
(₹5K-25K per successful loan). Banks need our project data to underwrite.

This contract defines what banks expect to receive from BuildEase for
a loan application:
  - Project cost breakdown they can verify
  - Construction timeline for disbursement schedule
  - Property type + location for risk assessment

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class LoanApplicationDataExport:
    """Project data formatted for bank loan underwriting.

    Banks need: cost breakdown, schedule, property info. Not user PII —
    that's collected by the bank directly via their KYC.
    """
    # Project identity (anonymous to bank — they get our project_id)
    project_id: str

    # Property info (bank uses for collateral assessment)
    property_city: str
    property_area: str | None
    plot_size_sqft: int
    built_up_area_sqft: int
    building_type: str
    floors_above_ground: int

    # Cost breakdown (the headline number for loan size)
    estimated_total_cost_rupees: float
    estimated_cost_low_rupees: float          # For risk-adjusted loan
    estimated_cost_high_rupees: float

    structural_cost_rupees: float = 0.0       # Roughly 35% of total
    finish_cost_rupees: float = 0.0           # Roughly 25%
    services_cost_rupees: float = 0.0         # Plumbing/electrical, ~20%
    contractor_overhead_rupees: float = 0.0   # ~10%
    contractor_profit_rupees: float = 0.0     # ~10%

    # Construction schedule (for disbursement)
    expected_duration_months: int = 0
    disbursement_milestones: tuple[str, ...] = ()
    # e.g., ("Foundation: 25%", "Structure: 35%", "Finishes: 30%", "Final: 10%")

    # Confidence + caveats (bank wants to see methodology)
    cost_confidence_level: str = ""           # HIGH/MEDIUM/LOW
    estimate_methodology: str = ""            # "BuildEase v0.4 — IS code based"
    source_trace_id: str = ""


class BankPartnerAdapter(Protocol):
    """Interface for bank loan partner integrations (SBI, HDFC, etc.)."""

    def submit_project_for_loan_check(
        self, data: LoanApplicationDataExport,
    ) -> str:
        """Submit for pre-qualification check; returns bank application ID."""
        ...

    def get_loan_eligibility(self, bank_app_id: str) -> dict:
        """Get bank's eligibility decision + max loan amount."""
        ...

    def initiate_user_loan_application(
        self, bank_app_id: str, user_contact: str,
    ) -> str:
        """Hand off to bank's actual loan flow with user."""
        ...
