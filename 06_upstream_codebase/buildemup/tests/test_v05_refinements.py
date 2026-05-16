"""
v0.5 test suite — verifies all v0.5 changes work and don't regress v0.4.

Covers:
  A. Confidence rename (HIGH→WELL_CONSTRAINED, etc.) with back-compat aliases
  B. Engineer override flag with audit-field validation
  C. ComponentContract system + Component 7 contract registration
  D. Vastu separation disclosure (format_for_user with banner)
  E. get_data_freshness_report() and format_freshness_report()
  F. Strengthened banner ("RULE-BASED HEURISTIC", "NOT structural design")
  G. Load-combination + lateral-analysis simplification disclosure
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine, StructuralGridInput,
)
from buildemup.kb.building_types import BuildingType
from buildemup.utils.confidence import (
    Confidence, classify,
    WELL_CONSTRAINED_IS456_RULE, REGIONAL_TYPICAL_RATE,
    DEPENDS_ON_CHOICE_FINISH,
    HIGH_IS456_RULE, MEDIUM_REGIONAL_RATE, LOW_FINISH_CHOICE,  # back-compat
)
from buildemup.utils.component_contract import (
    all_contracts, get_contract, validate_input, validate_output,
    register_contract, ComponentContract, FieldSpec, required, optional,
)
from buildemup.utils.kb_versions import (
    get_data_freshness_report, format_freshness_report,
)
from buildemup.kb.vastu_engine import (
    check_vastu_compliance, RoomType, Direction,
)


# ─── A. Confidence rename ────────────────────────────────────────────────
def test_new_confidence_names_exist():
    """v0.5: descriptive names exist."""
    assert Confidence.WELL_CONSTRAINED.value == "WELL_CONSTRAINED"
    assert Confidence.REGIONAL_TYPICAL.value == "REGIONAL_TYPICAL"
    assert Confidence.DEPENDS_ON_CHOICE.value == "DEPENDS_ON_CHOICE"
    print(f"PASS new confidence names exist: WELL_CONSTRAINED, REGIONAL_TYPICAL, DEPENDS_ON_CHOICE")


def test_old_confidence_names_still_work_as_aliases():
    """v0.5 back-compat: HIGH/MEDIUM/LOW still work as aliases."""
    assert Confidence.HIGH == Confidence.WELL_CONSTRAINED
    assert Confidence.MEDIUM == Confidence.REGIONAL_TYPICAL
    assert Confidence.LOW == Confidence.DEPENDS_ON_CHOICE
    # Back-compat evidence objects also alias
    assert HIGH_IS456_RULE.level == Confidence.WELL_CONSTRAINED
    assert MEDIUM_REGIONAL_RATE.level == Confidence.REGIONAL_TYPICAL
    assert LOW_FINISH_CHOICE.level == Confidence.DEPENDS_ON_CHOICE
    print(f"PASS back-compat aliases work (HIGH→WELL_CONSTRAINED etc)")


def test_confidence_display_label_is_user_friendly():
    """display_label returns capitalised user-friendly form."""
    assert Confidence.WELL_CONSTRAINED.display_label() == "Well-constrained"
    assert Confidence.REGIONAL_TYPICAL.display_label() == "Regional typical"
    assert Confidence.DEPENDS_ON_CHOICE.display_label() == "Depends on your choices"
    print(f"PASS display_label is user-friendly")


def test_classify_returns_new_names():
    """classify() uses new descriptive names."""
    assert classify(4.0) == Confidence.WELL_CONSTRAINED
    assert classify(8.0) == Confidence.REGIONAL_TYPICAL
    assert classify(20.0) == Confidence.DEPENDS_ON_CHOICE
    print(f"PASS classify returns new names")


def test_confidence_disclaimer_in_explain():
    """v0.5: explain() must say confidence is NOT about engineering correctness."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "NOT about engineering correctness" in explanation
    print(f"PASS confidence disclaimer present in explain()")


def test_cost_summary_uses_display_label_not_raw_enum():
    """Cost format_short uses 'Well-constrained' not 'WELL_CONSTRAINED'."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    summary = result.cost.format_short()
    # Should use display_label form, not raw enum value
    assert "Well-constrained" in summary or "Regional typical" in summary or "Depends on" in summary
    assert "WELL_CONSTRAINED" not in summary
    assert "REGIONAL_TYPICAL" not in summary
    print(f"PASS cost summary uses display_label: {summary[-40:]}")


# ─── B. Engineer override flag ───────────────────────────────────────────
def test_engineer_override_requires_audit_fields():
    """Setting override=True without audit fields must raise."""
    try:
        StructuralGridInput(
            envelope_width_m=10.0, envelope_depth_m=10.0,
            floors_above_ground=1, city="chennai",
            engineer_validated_override=True,
            # Missing engineer_name, license_no, validation_date
        )
        assert False, "Expected ValueError for missing audit fields"
    except ValueError as e:
        assert "engineer_name" in str(e)
        assert "engineer_license_no" in str(e)
        assert "engineer_validation_date" in str(e)
        print(f"PASS override requires audit fields")


def test_engineer_override_bypasses_severe_irregularity():
    """With override + valid audit, severe irregularity proceeds."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=4.0,  # 40% — severe
        re_entrant_corner_y_m=4.0,
        engineer_validated_override=True,
        engineer_name="Dr. Ramesh Krishnan",
        engineer_license_no="TN/SE/2018/4521",
        engineer_validation_date="2026-04-15",
    )
    result = StructuralGridEngine().execute(inp)  # Should NOT raise
    assert result.cost.exact_value > 0
    # Override warning must be in output
    has_override_warning = any(
        "ENGINEER OVERRIDE" in w or "engineer override" in w.lower()
        or "UNVERIFIED USER CLAIM" in w or "user claim" in w.lower()
        for w in result.all_warnings
    )
    assert has_override_warning, \
        f"Expected override or claim warning. Got: {result.all_warnings[:2]}"
    print(f"PASS engineer override bypasses severe irregularity")


def test_engineer_override_warning_mentions_engineer_attribution():
    """Override warning must show engineer name + license."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=4.0,
        re_entrant_corner_y_m=4.0,
        engineer_validated_override=True,
        engineer_name="Dr. Ramesh Krishnan",
        engineer_license_no="TN/SE/2018/4521",
        engineer_validation_date="2026-04-15",
    )
    result = StructuralGridEngine().execute(inp)
    warnings_text = " ".join(result.all_warnings)
    assert "Dr. Ramesh Krishnan" in warnings_text
    assert "TN/SE/2018/4521" in warnings_text
    assert "2026-04-15" in warnings_text
    print(f"PASS override warning includes engineer attribution + audit trail")


def test_no_override_still_refuses_severe():
    """Without override flag, severe irregularity still refused."""
    from buildemup.utils.errors import EnvelopeTooIrregularError
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=4.0,
        re_entrant_corner_y_m=4.0,
    )
    try:
        StructuralGridEngine().execute(inp)
        assert False, "Expected refusal without override"
    except EnvelopeTooIrregularError as e:
        # Refusal message must mention how to use override (old or new name)
        assert ("engineer_validated_override" in e.suggested_action
                or "user_claims_engineer_reviewed" in e.suggested_action)
        print(f"PASS severe irregularity still refused without override")


# ─── C. ComponentContract system ─────────────────────────────────────────
def test_component_7_contract_registered():
    """Component 7 must register its contract on import."""
    contract = get_contract("C07_structural_grid")
    assert contract is not None
    assert contract.version in ("0.5", "0.6"), f"Got version {contract.version}"
    assert len(contract.consumes) > 0
    assert len(contract.produces) > 0
    print(f"PASS C07 contract registered (v{contract.version}, "
          f"{len(contract.consumes)} consumed, {len(contract.produces)} produced)")


def test_real_input_validates_clean():
    """A valid StructuralGridInput must pass contract validation."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    violations = validate_input("C07_structural_grid", inp)
    assert violations == [], f"Unexpected violations: {violations}"
    print(f"PASS valid input validates clean")


def test_invalid_envelope_violates_contract():
    """An out-of-range envelope must show as a violation."""
    # We can't construct an invalid input via __post_init__ (that catches it)
    # so we make a duck-typed mock
    class FakeInput:
        envelope_width_m = 2.0  # Below >=5.0 constraint
        envelope_depth_m = 10.0
        floors_above_ground = 1
    violations = validate_input("C07_structural_grid", FakeInput())
    assert len(violations) > 0
    assert any("envelope_width_m" in v for v in violations)
    print(f"PASS invalid envelope flagged: {violations[0]}")


def test_real_output_validates_clean():
    """A real Component 7 output must pass output contract validation."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    violations = validate_output("C07_structural_grid", result)
    assert violations == [], f"Output violations: {violations}"
    print(f"PASS real output validates clean")


def test_contract_can_be_documented():
    """format_for_docs must produce readable contract documentation."""
    contract = get_contract("C07_structural_grid")
    docs = contract.format_for_docs()
    assert "C07_structural_grid" in docs
    assert "INPUT (consumes)" in docs
    assert "OUTPUT (produces)" in docs
    assert "envelope_width_m" in docs
    print(f"PASS contract documentation generates")


# ─── D. Vastu separation disclosure ──────────────────────────────────────
def test_vastu_format_has_separation_banner():
    """Vastu format must prominently warn it's separate from engineering."""
    report = check_vastu_compliance({
        RoomType.POOJA_ROOM: Direction.NORTHEAST,
        RoomType.KITCHEN: Direction.SOUTHEAST,
    })
    output = report.format_for_user()
    assert "separate from structural design" in output.lower()
    assert "do not modify" in output.lower() or "do NOT modify" in output
    assert "structural engineer" in output.lower()
    print(f"PASS Vastu format has separation banner")


def test_vastu_format_disabled_returns_disabled_message():
    """When opted out, format must say so cleanly without scoring."""
    report = check_vastu_compliance({}, enabled=False)
    output = report.format_for_user()
    assert "DISABLED" in output or "disabled" in output
    # Even disabled, separation banner must appear
    assert "separate from structural" in output.lower()
    print(f"PASS Vastu disabled state handled cleanly")


# ─── E. Data freshness report ────────────────────────────────────────────
def test_freshness_report_shows_all_modules():
    """All 8 KB modules must appear in freshness report."""
    report = get_data_freshness_report()
    module_names = [m["module"] for m in report["modules"]]
    assert "rcc_design_rules" in module_names
    assert "soil_foundation_rules" in module_names
    assert "material_rates_chennai" in module_names
    assert "material_rates_multicity" in module_names
    assert len(report["modules"]) >= 8
    print(f"PASS freshness report covers {len(report['modules'])} modules")


def test_freshness_report_flags_stale_modules():
    """A 6-month-old date must flag quarterly rate modules as stale."""
    # Simulate a future date 200 days after the LAST_UPDATED
    report = get_data_freshness_report("2026-11-15")
    # Quarterly modules (90-day cadence) should be stale at 200+ days
    stale = report["stale_modules"]
    assert "material_rates_chennai" in stale
    assert "material_rates_multicity" in stale
    assert report["all_fresh"] is False
    print(f"PASS staleness detection works ({len(stale)} stale at +200 days)")


def test_freshness_report_format_human_readable():
    """format_freshness_report produces readable text."""
    text = format_freshness_report()
    assert "Freshness Report" in text
    assert "fresh" in text.lower() or "stale" in text.lower()
    print(f"PASS freshness report formats readably")


# ─── F. Strengthened banner ──────────────────────────────────────────────
def test_strengthened_banner_in_explain():
    """v0.5 banner must contain stronger language."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "RULE-BASED HEURISTIC" in explanation
    assert "NOT structural design" in explanation
    assert "LICENSED STRUCTURAL ENGINEER" in explanation
    print(f"PASS v0.5 strengthened banner present")


# ─── G. Load combination + lateral analysis disclosure ──────────────────
def test_load_combination_simplification_disclosed():
    """The 'WHAT WE DON'T CHECK' section must mention IS 875 Part 5 limitation."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "IS 875 Part 5 load combination" in explanation
    assert "Directional + torsional" in explanation
    print(f"PASS load combination simplification disclosed")


def test_sensitivity_scope_disclosed():
    """v0.5: must disclose that sensitivity is soil + load only, not span/material."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "Span variation" in explanation
    assert "soil + load only" in explanation
    print(f"PASS sensitivity scope limitation disclosed")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.5 Test Suite — Trust + Architecture Refinements")
    print("=" * 70)
    print()
    print("--- A. Confidence rename ---")
    test_new_confidence_names_exist()
    test_old_confidence_names_still_work_as_aliases()
    test_confidence_display_label_is_user_friendly()
    test_classify_returns_new_names()
    test_confidence_disclaimer_in_explain()
    test_cost_summary_uses_display_label_not_raw_enum()
    print()
    print("--- B. Engineer override flag ---")
    test_engineer_override_requires_audit_fields()
    test_engineer_override_bypasses_severe_irregularity()
    test_engineer_override_warning_mentions_engineer_attribution()
    test_no_override_still_refuses_severe()
    print()
    print("--- C. ComponentContract system ---")
    test_component_7_contract_registered()
    test_real_input_validates_clean()
    test_invalid_envelope_violates_contract()
    test_real_output_validates_clean()
    test_contract_can_be_documented()
    print()
    print("--- D. Vastu separation disclosure ---")
    test_vastu_format_has_separation_banner()
    test_vastu_format_disabled_returns_disabled_message()
    print()
    print("--- E. Data freshness report ---")
    test_freshness_report_shows_all_modules()
    test_freshness_report_flags_stale_modules()
    test_freshness_report_format_human_readable()
    print()
    print("--- F. Strengthened banner ---")
    test_strengthened_banner_in_explain()
    print()
    print("--- G. Disclosure additions ---")
    test_load_combination_simplification_disclosed()
    test_sensitivity_scope_disclosed()
    print()
    print("=" * 70)
    print("ALL v0.5 TESTS PASSED")
    print("=" * 70)
