"""
BuildemUp† — Legal & Statutory Disclosures (v0.6)
====================================================

Per user's Q2 decision, these disclosures appear IN EVERY OUTPUT (not
session-start or buried). Inline disclosure is harder to argue you
"didn't see" than a one-time dialog.

The five legal exposures being addressed:
  1. Use-and-validate disclaimer — must always accompany output
  2. No engineer endorsement — we never claim to verify engineers
  3. Limitation of liability — BuildemUp is decision support, not design
  4. PII handling — engineer data is session-only, never persisted
  5. Indian statutory context — stamped plan requirement for permits

These disclosures are non-negotiable. They appear regardless of:
  - Whether override flag is used
  - Whether KB data is fresh or stale
  - User's city or building type

†= placeholder name marker.
"""
from __future__ import annotations


# The master disclosure text. Shown in full in every `explain()` output.
LEGAL_STATUTORY_DISCLOSURES_TEXT = """LEGAL & STATUTORY DISCLOSURES

This estimate is decision-support only. It is NOT a structural
design, NOT a stamped plan, and NOT a construction document.

1. STRUCTURAL ENGINEER REQUIRED BEFORE CONSTRUCTION
   A licensed structural engineer must independently review and
   validate this design before any construction. Their stamped
   drawings supersede everything we produce. Do not begin
   construction based on this output alone.

2. MUNICIPAL PERMIT REQUIREMENT (India)
   Under most Indian municipal corporation rules (Chennai CMDA,
   Mumbai BMC, Delhi MCD, Bangalore BBMP, etc.), building plans
   must be stamped by a registered architect or structural engineer
   before a building permit is issued. THIS OUTPUT IS NOT A STAMPED
   PLAN. Submitting it to a municipal authority for permit will
   be rejected. Take it to your engineer first.

3. NO ENGINEER VERIFICATION OR ENDORSEMENT
   If you named an engineer in your inputs (user_claims_engineer_
   reviewed), BuildemUp has NOT verified that person's identity,
   license status, competence, or the fact of their review. We do
   not have a contractual relationship with any engineer. The
   engineer is your consultant, not ours. Claims are recorded for
   your audit trail only and labelled UNVERIFIED everywhere.

4. LIMITATION OF LIABILITY
   BuildemUp is provided "as-is" for planning and decision-support
   purposes only. We do not warrant that the output is complete,
   correct for your specific site conditions, or suitable for
   construction. You are solely responsible for engaging qualified
   professionals before acting on this output. BuildemUp is not
   liable for construction outcomes, cost overruns, or structural
   issues arising from use of this estimate.

5. DATA HANDLING
   Any engineer name/license/contact information you provide is
   used only within your active session. It is not stored in a
   persistent database and is not shared with any third party
   (including the named engineer). When you close this session,
   that information is not retained.

6. PRELIMINARY SOIL + LOAD ASSUMPTIONS
   The bearing capacity values, live loads, and seismic zone
   assumptions used here come from published typical values for
   your city. YOUR ACTUAL SITE may differ. A soil test (~₹15-25K)
   and engineer site visit are essential before final design."""


def format_legal_disclosures_block(mode: str = "full") -> str:
    """The legal block shown in every output.

    v0.7 addition per Drawback 4 review: support compact mode for
    users who find the 6-section block overwhelming. Default remains
    'full' per Q2 decision — compact is opt-in only.

    Args:
        mode: 'full' (default, all 6 sections) or 'compact' (3-line
              critical summary plus pointer).

    Returns:
        Formatted text block with borders.
    """
    if mode == "compact":
        return _format_compact()
    return _format_full()


def _format_full() -> str:
    """Full 6-section legal block (v0.6 default behaviour, unchanged)."""
    lines = ["─" * 70]
    for line in LEGAL_STATUTORY_DISCLOSURES_TEXT.split("\n"):
        lines.append(line)
    lines.append("─" * 70)
    return "\n".join(lines)


def _format_compact() -> str:
    """v0.7: Compact 3-point critical summary with pointer to full text.

    Preserves the legally-essential points without the 6-section
    verbosity. Users can still request full text by calling
    format_legal_disclosures_block(mode='full').
    """
    lines = [
        "─" * 70,
        "LEGAL & STATUTORY DISCLOSURES (compact — full text available on request)",
        "",
        "  1. This is NOT a stamped plan. Licensed structural engineer must",
        "     independently review before construction. Indian municipal permits",
        "     (CMDA / BMC / MCD / BBMP) require engineer-stamped drawings.",
        "",
        "  2. BuildemUp does NOT verify or endorse any engineer. Any engineer",
        "     name you provide is recorded for your audit trail only.",
        "",
        "  3. Provided as-is for planning. NOT liable for construction outcomes.",
        "     Engineer info is session-only, not stored. Soil test essential.",
        "",
        "  For full 6-section disclosure text, call format_legal_disclosures_block(",
        "  mode='full') or see /utils/legal_disclosures.py.",
        "─" * 70,
    ]
    return "\n".join(lines)


# Machine-readable version for JSON/API output
LEGAL_DISCLOSURES_DICT = {
    "version": "v0.6",
    "always_shown_in_output": True,
    "disclosures": [
        {
            "id": "engineer_required",
            "text": ("A licensed structural engineer must independently "
                     "review and validate this design before construction."),
        },
        {
            "id": "municipal_permit_requirement",
            "text": ("This output is NOT a stamped plan. Indian municipal "
                     "corporations require stamped plans for building permits."),
        },
        {
            "id": "no_engineer_endorsement",
            "text": ("BuildemUp does NOT verify or endorse any engineer "
                     "named by the user."),
        },
        {
            "id": "limitation_of_liability",
            "text": ("Provided as-is for planning only. Not liable for "
                     "construction outcomes."),
        },
        {
            "id": "pii_handling",
            "text": ("Engineer info is session-only. Not stored or shared."),
        },
        {
            "id": "soil_load_assumptions",
            "text": ("SBC and load values are typical regional values. "
                     "Your site may differ. Soil test essential."),
        },
    ],
}


# v0.6: PII handling hook
def purge_engineer_data(inp_dict: dict) -> dict:
    """Remove engineer PII from a dict (for logs, exports, traces).

    Per the PII handling commitment: engineer claim data is session-only.
    When anything leaves the session (logs, traces, exports), strip it.

    Args:
        inp_dict: dict possibly containing engineer_name, engineer_license_no,
                  engineer_validation_date, user_engineer_consultant.

    Returns:
        New dict with engineer fields removed (or replaced with '[REDACTED]').
    """
    PII_FIELDS = {
        "engineer_name",
        "engineer_license_no",
        "engineer_validation_date",
        "user_engineer_consultant",
        # Common variants
        "claimed_engineer_name",
        "claimed_engineer_license",
        "claimed_validation_date",
    }
    cleaned = dict(inp_dict)
    for field in list(cleaned.keys()):
        if field in PII_FIELDS:
            cleaned[field] = "[REDACTED]"
    return cleaned
