"""
v0.6 Phase 3 tests — trust + legal hardening.

Covers:
  - engineer_validated_override renamed to user_claims_engineer_reviewed
  - Back-compat: old name still works as alias
  - user_engineer_consultant session-only field
  - validation_status: PENDING ENGINEER VALIDATION in every output
  - UNVERIFIED USER CLAIM wording (never 'validated')
  - Engineering depth axis (LEVEL 1/2/3) separate from confidence
  - Freshness enforcement with 3-tier degradation
  - PII purge function
  - Legal & statutory disclosures block always in output
  - Frame sanity integrated into orchestrator output
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine, StructuralGridInput,
)
from buildemup.utils.engineering_depth import (
    EngineeringDepth, DepthIndicator,
    level_1_indicator, level_2_indicator,
)
from buildemup.utils.kb_versions import (
    enforce_freshness_and_get_action, should_degrade_confidence,
)
from buildemup.utils.legal_disclosures import (
    LEGAL_STATUTORY_DISCLOSURES_TEXT,
    format_legal_disclosures_block,
    purge_engineer_data,
    LEGAL_DISCLOSURES_DICT,
)
from buildemup.utils.confidence import Confidence


# ─── Rename + back-compat ────────────────────────────────────────────────
def test_new_field_name_works():
    """user_claims_engineer_reviewed is the new canonical field."""
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    )
    # New field defaults to False
    assert inp.user_claims_engineer_reviewed is False
    print("PASS user_claims_engineer_reviewed is the new canonical field")


def test_old_field_name_still_works_as_alias():
    """engineer_validated_override still works as a back-compat alias."""
    # Old name mirrors to new in __post_init__
    inp = StructuralGridInput(
        envelope_width_m=10, envelope_depth_m=10, floors_above_ground=1,
        re_entrant_corner_x_m=4, re_entrant_corner_y_m=4,  # severe irregular
        engineer_validated_override=True,   # old name
        engineer_name="Dr. X", engineer_license_no="TN/SE/1", 
        engineer_validation_date="2026-04-15",
    )
    # Should be mirrored to new name
    assert inp.user_claims_engineer_reviewed is True
    print("PASS engineer_validated_override aliased to user_claims_engineer_reviewed")


def test_new_and_old_field_both_accepted_in_engine():
    """Running engine with either field works."""
    # Run with new name
    inp_new = StructuralGridInput(
        envelope_width_m=10, envelope_depth_m=10, floors_above_ground=1,
        re_entrant_corner_x_m=4, re_entrant_corner_y_m=4,
        user_claims_engineer_reviewed=True,
        engineer_name="Dr. A", engineer_license_no="TN/SE/1",
        engineer_validation_date="2026-04-15",
    )
    result_new = StructuralGridEngine().execute(inp_new)
    # Run with old name
    inp_old = StructuralGridInput(
        envelope_width_m=10, envelope_depth_m=10, floors_above_ground=1,
        re_entrant_corner_x_m=4, re_entrant_corner_y_m=4,
        engineer_validated_override=True,
        engineer_name="Dr. B", engineer_license_no="TN/SE/2",
        engineer_validation_date="2026-04-15",
    )
    result_old = StructuralGridEngine().execute(inp_old)
    # Both should succeed
    assert result_new.cost.exact_value > 0
    assert result_old.cost.exact_value > 0
    print("PASS both old and new override field names accepted by engine")


def test_user_engineer_consultant_field_optional_session_only():
    """user_engineer_consultant is optional + never appears in output."""
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
        user_engineer_consultant="Dr. Krishnan, +91 98XXX",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    explanation = engine.explain(inp, result)
    # Must NEVER appear in user-facing output
    assert "Dr. Krishnan" not in explanation
    assert "98XXX" not in explanation
    print("PASS user_engineer_consultant is session-only (not in output)")


# ─── Validation status ───────────────────────────────────────────────────
def test_validation_status_pending_by_default():
    """Every output must have validation_status = PENDING ENGINEER VALIDATION."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = StructuralGridEngine().execute(inp)
    assert "PENDING ENGINEER VALIDATION" in result.validation_status
    assert result.validation_status.startswith("PENDING")
    print(f"PASS default status: {result.validation_status}")


def test_validation_status_with_claim_labelled_unverified():
    """When user claims engineer review, status includes UNVERIFIED marker."""
    inp = StructuralGridInput(
        envelope_width_m=10, envelope_depth_m=10, floors_above_ground=1,
        re_entrant_corner_x_m=4, re_entrant_corner_y_m=4,
        user_claims_engineer_reviewed=True,
        engineer_name="Dr. X", engineer_license_no="TN/SE/1",
        engineer_validation_date="2026-04-15",
    )
    result = StructuralGridEngine().execute(inp)
    # Must still say PENDING + UNVERIFIED somewhere
    assert "PENDING ENGINEER VALIDATION" in result.validation_status
    assert ("UNVERIFIED" in result.validation_status
            or "unverified" in result.validation_status.lower())
    print(f"PASS claim labelled unverified: {result.validation_status}")


def test_validation_status_appears_in_explain():
    """explain() must display the validation status prominently."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "VALIDATION STATUS" in explanation
    assert "PENDING ENGINEER VALIDATION" in explanation
    print("PASS validation status appears in explain()")


# ─── Warning text uses "claim" never "validated" ─────────────────────────
def test_warning_says_unverified_user_claim():
    """When override is used, warning uses UNVERIFIED USER CLAIM wording."""
    inp = StructuralGridInput(
        envelope_width_m=10, envelope_depth_m=10, floors_above_ground=1,
        re_entrant_corner_x_m=4, re_entrant_corner_y_m=4,
        user_claims_engineer_reviewed=True,
        engineer_name="Dr. A", engineer_license_no="TN/SE/1",
        engineer_validation_date="2026-04-15",
    )
    result = StructuralGridEngine().execute(inp)
    first_warning = result.all_warnings[0]
    # Must say "UNVERIFIED USER CLAIM", must NOT say "ENGINEER OVERRIDE ACTIVE"
    # (old wording implied we had endorsed)
    assert "UNVERIFIED" in first_warning
    assert "USER" in first_warning
    assert "NOT verified" in first_warning or "not verified" in first_warning.lower()
    print("PASS warning uses UNVERIFIED USER CLAIM wording")


# ─── Engineering depth axis ──────────────────────────────────────────────
def test_engineering_depth_enum_has_three_levels():
    """Engineering depth has exactly three levels: 1, 2, 3."""
    levels = [EngineeringDepth.LEVEL_1_RULE_BASED,
              EngineeringDepth.LEVEL_2_FRAME_CHECKED,
              EngineeringDepth.LEVEL_3_ENGINEER_DESIGNED]
    assert len(set(levels)) == 3
    # Each has display label
    for level in levels:
        assert level.display_label()
        assert level.user_description()
    print(f"PASS engineering depth has 3 levels: "
          f"{[l.display_label() for l in levels]}")


def test_engineering_depth_separate_from_confidence():
    """Engineering depth is orthogonal to confidence level."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = StructuralGridEngine().execute(inp)
    # Cost has a confidence level AND output has an engineering_depth
    assert result.cost.confidence in (
        Confidence.WELL_CONSTRAINED, Confidence.REGIONAL_TYPICAL, Confidence.DEPENDS_ON_CHOICE,
    )
    assert result.engineering_depth is not None
    # The two axes are independent data types
    assert not isinstance(result.cost.confidence, EngineeringDepth)
    print(f"PASS confidence ({result.cost.confidence.display_label()}) "
          f"and depth ({result.engineering_depth.level.display_label()}) independent")


def test_v06_output_is_level_2_frame_checked():
    """v0.6 with frame sanity integrated = LEVEL 2."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = StructuralGridEngine().execute(inp)
    assert result.engineering_depth.level == EngineeringDepth.LEVEL_2_FRAME_CHECKED
    print("PASS v0.6 output is LEVEL 2 FRAME-CHECKED")


def test_level_3_never_returned_by_buildemup():
    """BuildemUp must NEVER produce LEVEL 3 output — that's engineer-only."""
    # Sanity: there is no level_3_indicator() function exposed
    from buildemup.utils import engineering_depth as ed
    assert not hasattr(ed, "level_3_indicator"), \
        "BuildemUp must not produce LEVEL 3 — that's engineer-only"
    print("PASS no level_3_indicator() function (engineer-only by design)")


def test_engineering_depth_in_explain():
    """explain() must show engineering depth section."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "ENGINEERING DEPTH" in explanation
    assert "Level 2" in explanation or "LEVEL_2" in explanation
    print("PASS engineering depth shown in explain()")


# ─── Freshness enforcement ───────────────────────────────────────────────
def test_freshness_ok_at_current_date():
    """At current date, KB should be fresh."""
    result = enforce_freshness_and_get_action()
    assert result["action"] == "OK"
    print(f"PASS freshness OK at current date")


def test_freshness_warns_at_6_months():
    """6 months past update, quarterly rate modules warn."""
    # Our KB last_updated = 2026-04-01. 180 days later = 2026-09-28
    # Quarterly cadence = 90 days. 180 > 90 means rates are past cadence.
    # Block threshold = 2x cadence = 180 days. So 180 days + a bit should WARN.
    result = enforce_freshness_and_get_action("2026-09-15")
    # At +167 days (166 > 90), rates should be WARN (not yet past 180)
    assert result["action"] == "WARN_DEGRADE_CONFIDENCE"
    print(f"PASS freshness WARN at +167 days")


def test_freshness_blocks_at_very_stale():
    """Over 2x cadence = BLOCK severity."""
    # +200 days: quarterly (90) is 2× past, should BLOCK
    # But 200 < 365*2=730 for yearly modules, so only rate modules block
    result = enforce_freshness_and_get_action("2026-12-15")
    # At +258 days, quarterly rates (cadence 90) are over 2× cadence (180) → BLOCK
    assert result["action"] == "BLOCK_STALE"
    print(f"PASS freshness BLOCK at +258 days")


def test_should_degrade_confidence_helper():
    """Simple bool helper works."""
    assert should_degrade_confidence() is False   # Current date: fresh
    assert should_degrade_confidence("2026-09-15") is True   # Stale
    print("PASS should_degrade_confidence helper works")


def test_freshness_in_orchestrator_output():
    """Orchestrator output includes freshness_action."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = StructuralGridEngine().execute(inp)
    assert result.freshness_action in ("OK", "WARN_DEGRADE_CONFIDENCE", "BLOCK_STALE")
    print(f"PASS freshness_action in output: {result.freshness_action}")


# ─── PII handling ────────────────────────────────────────────────────────
def test_purge_engineer_data_removes_pii():
    """purge_engineer_data redacts engineer fields from dicts."""
    d = {
        "normal_field": "ok",
        "engineer_name": "Dr. X",
        "engineer_license_no": "TN/SE/1",
        "engineer_validation_date": "2026-04-15",
        "user_engineer_consultant": "Consultant info",
    }
    purged = purge_engineer_data(d)
    assert purged["normal_field"] == "ok"
    assert purged["engineer_name"] == "[REDACTED]"
    assert purged["engineer_license_no"] == "[REDACTED]"
    assert purged["engineer_validation_date"] == "[REDACTED]"
    assert purged["user_engineer_consultant"] == "[REDACTED]"
    # Original dict unchanged (purge returns new dict)
    assert d["engineer_name"] == "Dr. X"
    print("PASS purge_engineer_data redacts PII (new dict, original unchanged)")


def test_purge_engineer_data_handles_empty_dict():
    """Purging an empty dict returns empty dict, no crash."""
    assert purge_engineer_data({}) == {}
    print("PASS purge_engineer_data handles empty dict")


def test_purge_engineer_data_handles_common_variants():
    """Variants like claimed_engineer_name also redacted."""
    d = {
        "claimed_engineer_name": "Dr. X",
        "claimed_engineer_license": "TN/SE/1",
        "claimed_validation_date": "2026-04-15",
    }
    purged = purge_engineer_data(d)
    assert purged["claimed_engineer_name"] == "[REDACTED]"
    assert purged["claimed_engineer_license"] == "[REDACTED]"
    assert purged["claimed_validation_date"] == "[REDACTED]"
    print("PASS purge handles claimed_* variant field names")


# ─── Legal & statutory disclosures ───────────────────────────────────────
def test_legal_disclosures_block_has_all_six_sections():
    """Six numbered sections per v0.6 design."""
    text = LEGAL_STATUTORY_DISCLOSURES_TEXT
    assert "1. STRUCTURAL ENGINEER REQUIRED" in text
    assert "2. MUNICIPAL PERMIT REQUIREMENT" in text
    assert "3. NO ENGINEER VERIFICATION" in text
    assert "4. LIMITATION OF LIABILITY" in text
    assert "5. DATA HANDLING" in text
    assert "6. PRELIMINARY SOIL + LOAD ASSUMPTIONS" in text
    print("PASS all 6 legal disclosure sections present")


def test_legal_disclosures_mentions_indian_municipal_permits():
    """Indian statutory context must be explicit."""
    text = LEGAL_STATUTORY_DISCLOSURES_TEXT
    assert "Indian" in text
    # At least one municipal corporation named
    municipalities = ["CMDA", "BMC", "MCD", "BBMP"]
    assert any(m in text for m in municipalities)
    assert "stamped plan" in text.lower()
    print("PASS Indian municipal permit requirement disclosed")


def test_legal_disclosures_mentions_no_engineer_endorsement():
    """Must explicitly state BuildemUp doesn't verify engineers."""
    text = LEGAL_STATUTORY_DISCLOSURES_TEXT
    assert "NOT verified" in text or "not verified" in text.lower()
    # Must NOT claim we have a contractual relationship
    assert "contractual relationship" in text.lower()
    print("PASS no-engineer-endorsement disclosure present")


def test_legal_disclosures_in_every_explain_output():
    """Legal disclosures appear in every explain() — per Q2 decision (a)."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "LEGAL & STATUTORY DISCLOSURES" in explanation
    assert "STRUCTURAL ENGINEER REQUIRED BEFORE CONSTRUCTION" in explanation
    print("PASS legal disclosures appear in explain()")


def test_legal_disclosures_machine_readable_dict():
    """Machine-readable version exists for API/JSON output."""
    assert LEGAL_DISCLOSURES_DICT["always_shown_in_output"] is True
    assert len(LEGAL_DISCLOSURES_DICT["disclosures"]) == 6
    for d in LEGAL_DISCLOSURES_DICT["disclosures"]:
        assert d["id"]
        assert d["text"]
    print(f"PASS machine-readable disclosures dict "
          f"({len(LEGAL_DISCLOSURES_DICT['disclosures'])} items)")


def test_legal_disclosures_block_formatting():
    """format_legal_disclosures_block returns bordered text."""
    block = format_legal_disclosures_block()
    assert "─" * 70 in block   # Border lines
    assert "LEGAL & STATUTORY DISCLOSURES" in block
    print("PASS legal disclosures formatted with borders")


# ─── Frame sanity in orchestrator output ─────────────────────────────────
def test_frame_sanity_populated_in_output():
    """v0.6 result.frame_sanity populated with valid report."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = StructuralGridEngine().execute(inp)
    assert result.frame_sanity is not None
    assert len(result.frame_sanity.columns) > 0
    assert result.frame_sanity.overall_result.value in ("SAFE", "WARNING", "FAIL")
    print(f"PASS frame sanity populated: {result.frame_sanity.overall_result.value}")


def test_frame_sanity_shown_in_explain():
    """explain() surfaces frame sanity section."""
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "FRAME SANITY CHECK" in explanation
    assert "IS 456 cl. 39.6" in explanation
    print("PASS frame sanity section in explain()")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.6 Phase 3 Tests — Trust + Legal Hardening")
    print("=" * 70)
    print()
    print("--- Field rename + back-compat ---")
    test_new_field_name_works()
    test_old_field_name_still_works_as_alias()
    test_new_and_old_field_both_accepted_in_engine()
    test_user_engineer_consultant_field_optional_session_only()
    print()
    print("--- Validation status ---")
    test_validation_status_pending_by_default()
    test_validation_status_with_claim_labelled_unverified()
    test_validation_status_appears_in_explain()
    print()
    print("--- Warning text ---")
    test_warning_says_unverified_user_claim()
    print()
    print("--- Engineering depth axis ---")
    test_engineering_depth_enum_has_three_levels()
    test_engineering_depth_separate_from_confidence()
    test_v06_output_is_level_2_frame_checked()
    test_level_3_never_returned_by_buildemup()
    test_engineering_depth_in_explain()
    print()
    print("--- Freshness enforcement ---")
    test_freshness_ok_at_current_date()
    test_freshness_warns_at_6_months()
    test_freshness_blocks_at_very_stale()
    test_should_degrade_confidence_helper()
    test_freshness_in_orchestrator_output()
    print()
    print("--- PII handling ---")
    test_purge_engineer_data_removes_pii()
    test_purge_engineer_data_handles_empty_dict()
    test_purge_engineer_data_handles_common_variants()
    print()
    print("--- Legal & statutory disclosures ---")
    test_legal_disclosures_block_has_all_six_sections()
    test_legal_disclosures_mentions_indian_municipal_permits()
    test_legal_disclosures_mentions_no_engineer_endorsement()
    test_legal_disclosures_in_every_explain_output()
    test_legal_disclosures_machine_readable_dict()
    test_legal_disclosures_block_formatting()
    print()
    print("--- Frame sanity integration ---")
    test_frame_sanity_populated_in_output()
    test_frame_sanity_shown_in_explain()
    print()
    print("=" * 70)
    print("ALL v0.6 PHASE 3 TESTS PASSED")
    print("=" * 70)
