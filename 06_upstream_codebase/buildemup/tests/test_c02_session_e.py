"""
Component 2 Session E tests.

Coverage:
  - InputField + FeasibilityInput: 3-state pattern invariants
  - city_feasibility_defaults KB: validator + 6 cities
  - check_soil_type_practical/code_strict + compute_soil_type_gap
  - check_water_table_practical/code_strict + compute_water_table_gap
  - The downgrade rule: assumed HARDs → SOFT_WARN (user-approved principle)
  - Verified user data → strict severity preserved
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _build_brief(**overrides):
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    defaults = dict(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0, plot_type="detached",
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),
                 RoomRequirement(RoomType.KITCHEN, 1))),
        ),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    defaults.update(overrides)
    inp = BriefCaptureInput(**defaults)
    return BriefCaptureEngine().execute(inp).brief


# ─── InputField invariants ────────────────────────────────────────────

def test_input_field_verified_classmethod():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource, ConfidenceLevel,
    )
    f = InputField.verified("laterite", field_name="soil_type")
    assert f.value == "laterite"
    assert f.source == FieldSource.USER_PROVIDED_VERIFIED
    assert f.confidence_level == ConfidenceLevel.HIGH
    assert f.is_user_data_present is True
    print("PASS InputField.verified() builds correctly")


def test_input_field_unverified_classmethod():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource, ConfidenceLevel,
    )
    f = InputField.unverified(8.5, field_name="water_table")
    assert f.value == 8.5
    assert f.source == FieldSource.USER_PROVIDED_UNVERIFIED
    assert f.confidence_level == ConfidenceLevel.MEDIUM
    assert f.is_user_data_present is True
    print("PASS InputField.unverified() builds correctly")


def test_input_field_unknown_classmethod():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource, ConfidenceLevel,
    )
    f = InputField.unknown(field_name="soil_type")
    assert f.value is None
    assert f.source == FieldSource.USER_DOESNT_KNOW
    assert f.confidence_level == ConfidenceLevel.LOW
    assert f.is_user_data_present is False
    print("PASS InputField.unknown() builds correctly")


def test_input_field_not_asked_classmethod():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource,
    )
    f = InputField.not_asked(field_name="x")
    assert f.value is None
    assert f.source == FieldSource.NOT_ASKED
    assert f.is_user_data_present is False
    print("PASS InputField.not_asked() builds correctly")


def test_input_field_rejects_verified_with_none_value():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource,
    )
    try:
        InputField(value=None, source=FieldSource.USER_PROVIDED_VERIFIED)
        assert False, "should have raised"
    except ValueError:
        pass
    print("PASS InputField rejects VERIFIED with None value")


def test_input_field_rejects_unknown_with_value():
    """USER_DOESNT_KNOW MUST have value=None — contradictory otherwise."""
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource,
    )
    try:
        InputField(value=5.0, source=FieldSource.USER_DOESNT_KNOW)
        assert False
    except ValueError:
        pass
    print("PASS InputField rejects USER_DOESNT_KNOW with value (contradictory)")


def test_input_field_rejects_not_asked_with_value():
    from buildemup.components.c02.feasibility_input import (
        InputField, FieldSource,
    )
    try:
        InputField(value=5.0, source=FieldSource.NOT_ASKED)
        assert False
    except ValueError:
        pass
    print("PASS InputField rejects NOT_ASKED with value")


def test_field_source_has_4_states():
    from buildemup.components.c02.feasibility_input import FieldSource
    expected = {
        "user_provided_verified", "user_provided_unverified",
        "user_doesnt_know", "not_asked",
    }
    actual = {s.value for s in FieldSource}
    assert actual == expected
    print("PASS FieldSource has 4 states (verified, unverified, unknown, not_asked)")


def test_input_field_verification_priority_for_value():
    """Mapping rules from source to suggested verification priority."""
    from buildemup.components.c02.feasibility_input import (
        InputField, VerificationPriority,
    )
    f_verified = InputField.verified("x")
    assert f_verified.verification_priority_for_value == VerificationPriority.OPTIONAL

    f_unverified = InputField.unverified("x")
    assert f_unverified.verification_priority_for_value == VerificationPriority.IMPORTANT

    f_unknown = InputField.unknown()
    assert f_unknown.verification_priority_for_value == VerificationPriority.IMPORTANT
    print("PASS InputField verification_priority maps correctly per source")


# ─── FeasibilityInput defaults ────────────────────────────────────────

def test_feasibility_input_default_fields_all_not_asked():
    """All 6 optional fields default to NOT_ASKED."""
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, FieldSource,
    )
    brief = _build_brief()
    inp = FeasibilityInput(brief=brief)
    assert inp.soil_type.source == FieldSource.NOT_ASKED
    assert inp.water_table_depth_m.source == FieldSource.NOT_ASKED
    assert inp.distance_from_electric_line_m.source == FieldSource.NOT_ASKED
    assert inp.electric_line_type.source == FieldSource.NOT_ASKED
    assert inp.distance_from_water_course_m.source == FieldSource.NOT_ASKED
    assert inp.has_water_course_within_30m.source == FieldSource.NOT_ASKED
    print("PASS FeasibilityInput defaults — all optional fields NOT_ASKED")


def test_feasibility_input_can_partially_populate():
    """Can populate just one field and leave others as defaults."""
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField, FieldSource,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("laterite"),
    )
    assert inp.soil_type.value == "laterite"
    assert inp.soil_type.source == FieldSource.USER_PROVIDED_VERIFIED
    # Others still defaults
    assert inp.water_table_depth_m.source == FieldSource.NOT_ASKED
    print("PASS FeasibilityInput supports partial population")


# ─── city_feasibility_defaults KB ─────────────────────────────────────

def test_city_defaults_kb_loads_all_6_cities():
    from buildemup.utils.kb_rules_loader import load_rules, clear_cache
    clear_cache()
    data = load_rules("city_feasibility_defaults")
    cities = [k for k in data.keys() if not k.startswith("_")]
    assert set(cities) == {
        "chennai", "bangalore", "hyderabad", "mumbai", "pune", "delhi",
    }
    print("PASS city_feasibility_defaults KB has all 6 launch cities")


def test_city_defaults_pune_is_black_cotton():
    """Pune default is black_cotton (high-risk soil)."""
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("city_feasibility_defaults")
    assert data["pune"]["soil_type"] == "black_cotton"
    print("PASS Pune default soil = black_cotton (correct, high-risk)")


def test_city_defaults_bangalore_has_deep_water_table():
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("city_feasibility_defaults")
    assert data["bangalore"]["water_table_depth_m_postmonsoon"] >= 5.0
    print(f"PASS Bangalore water table deep "
          f"({data['bangalore']['water_table_depth_m_postmonsoon']}m post-monsoon)")


def test_city_defaults_mumbai_has_shallow_water_table():
    """Mumbai = coastal = water table near surface."""
    from buildemup.utils.kb_rules_loader import load_rules
    data = load_rules("city_feasibility_defaults")
    assert data["mumbai"]["water_table_depth_m_postmonsoon"] <= 2.0
    print(f"PASS Mumbai water table shallow "
          f"({data['mumbai']['water_table_depth_m_postmonsoon']}m post-monsoon)")


def test_city_defaults_validator_catches_missing_field():
    from buildemup.utils.kb_rules_loader import (
        _validate_city_feasibility_defaults, RuleSchemaError,
    )
    bad = {
        "_meta": {"_version": "test"},
        "chennai": {"soil_type": "x"},  # missing other required
    }
    try:
        _validate_city_feasibility_defaults(bad)
        assert False
    except RuleSchemaError:
        pass
    print("PASS city_defaults validator catches missing fields")


# ─── Soil type check (Practical) ──────────────────────────────────────

def test_soil_practical_low_risk_pass():
    """Verified laterite + small build → PASS."""
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("laterite"),
    )
    r = check_soil_type_practical(inp)
    assert r.severity.value == "pass"
    print("PASS soil practical PASSes for verified laterite")


def test_soil_practical_high_risk_verified_g3_hards():
    """Verified black_cotton + G+3 → HARD_FAIL (not downgraded)."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical,
    )
    brief = _build_brief(
        plot_width_m=15.0, plot_depth_m=20.0,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(2, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(3, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("black_cotton"),
    )
    r = check_soil_type_practical(inp)
    assert r.severity.value == "hard_fail"
    assert r.details["downgrade_applied"] is False  # verified, no downgrade
    assert r.confidence.value == "high"
    print("PASS verified black_cotton + G+3 → HARD (no downgrade)")


def test_soil_practical_assumed_hard_downgrades_to_soft():
    """Assumed (don't know + Pune default) + G+3 → would HARD → SOFT_WARN."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical,
    )
    brief = _build_brief(
        city="pune",  # default soil = black_cotton
        plot_width_m=15.0, plot_depth_m=20.0,
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(2, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
            FloorRequirement(3, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(brief=brief)  # All defaults
    r = check_soil_type_practical(inp)
    # Raw severity should be HARD_FAIL but final downgraded to SOFT_WARN
    assert r.details["raw_severity"] == "hard_fail"
    assert r.severity.value == "soft_warn"
    assert r.details["downgrade_applied"] is True
    assert r.confidence.value == "low"
    assert r.assumption_used is not None
    assert r.verification_recommendation is not None
    print("PASS assumed black_cotton + G+3 → HARD downgraded to SOFT_WARN "
          "with assumption disclosed")


def test_soil_practical_uses_city_default_when_unknown():
    """No user data → uses Pune default = black_cotton."""
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical,
    )
    brief = _build_brief(city="pune")
    inp = FeasibilityInput(brief=brief)
    r = check_soil_type_practical(inp)
    assert r.details["soil_type_used"] == "black_cotton"
    assert r.details["data_source"] == "not_asked"
    print("PASS soil practical uses city default when no user data")


def test_soil_practical_unverified_user_data_medium_confidence():
    """User-provided (unverified) → MEDIUM confidence."""
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.unverified("laterite"),
    )
    r = check_soil_type_practical(inp)
    assert r.confidence.value == "medium"
    assert r.verification_recommendation is not None
    print("PASS unverified user soil → MEDIUM confidence with verify rec")


# ─── Soil type check (Code-Strict) ────────────────────────────────────

def test_soil_code_strict_pass_for_single_floor():
    """G+0 → soil testing not strictly mandated by NBC."""
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_code_strict,
    )
    brief = _build_brief()  # Default = single floor
    inp = FeasibilityInput(brief=brief)
    r = check_soil_type_code_strict(inp)
    assert r.severity.value == "pass"
    print("PASS soil code_strict PASSes for single-floor (no test required)")


def test_soil_code_strict_pass_when_verified():
    """Multi-floor + verified soil → PASS."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_code_strict,
    )
    brief = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.verified("laterite"),
    )
    r = check_soil_type_code_strict(inp)
    assert r.severity.value == "pass"
    print("PASS soil code_strict PASSes for verified soil + G+1")


def test_soil_code_strict_hard_fails_g1_unverified():
    """G+1 + unverified soil → HARD_FAIL."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_code_strict,
    )
    brief = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(
        brief=brief,
        soil_type=InputField.unverified("laterite"),
    )
    r = check_soil_type_code_strict(inp)
    assert r.severity.value == "hard_fail"
    assert r.verification_priority.value == "critical"
    print("PASS soil code_strict HARD_FAILs for unverified soil + G+1")


def test_soil_code_strict_hard_fails_g1_unknown():
    """G+1 + don't-know → HARD_FAIL."""
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_code_strict,
    )
    brief = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(brief=brief)
    r = check_soil_type_code_strict(inp)
    assert r.severity.value == "hard_fail"
    print("PASS soil code_strict HARD_FAILs for unknown soil + G+1")


# ─── Soil type gap ────────────────────────────────────────────────────

def test_soil_gap_none_for_single_floor():
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import compute_soil_type_gap
    brief = _build_brief()  # Single floor
    inp = FeasibilityInput(brief=brief)
    g = compute_soil_type_gap(inp)
    assert g is None
    print("PASS soil gap None for single-floor")


def test_soil_gap_none_when_verified():
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import compute_soil_type_gap
    brief = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(
        brief=brief, soil_type=InputField.verified("laterite"),
    )
    g = compute_soil_type_gap(inp)
    assert g is None
    print("PASS soil gap None when verified")


def test_soil_gap_blocking_when_g1_unverified():
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import compute_soil_type_gap
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief(
        floors=(
            FloorRequirement(0, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.LIVING, 1),)),
            FloorRequirement(1, FloorUse.RESIDENTIAL,
                (RoomRequirement(RoomType.BEDROOM_MASTER, 1),)),
        ),
    )
    inp = FeasibilityInput(brief=brief)  # Unknown soil
    g = compute_soil_type_gap(inp)
    assert g is not None
    assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print("PASS soil gap BLOCKING for G+1 + unverified soil")


# ─── Water table check (Practical) ────────────────────────────────────

def test_water_table_practical_pass_when_deep():
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_water_table_practical,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        water_table_depth_m=InputField.verified(15.0),
    )
    r = check_water_table_practical(inp)
    assert r.severity.value == "pass"
    print("PASS water table practical PASSes for deep WT (15m verified)")


def test_water_table_practical_soft_warn_when_shallow():
    """Verified shallow → SOFT_WARN."""
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_water_table_practical,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        water_table_depth_m=InputField.verified(2.0),
    )
    r = check_water_table_practical(inp)
    assert r.severity.value == "soft_warn"
    print("PASS water table practical SOFT_WARNs for shallow WT (2m)")


def test_water_table_practical_uses_city_default_when_unknown():
    """No user data → uses Mumbai default (very shallow)."""
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_water_table_practical,
    )
    brief = _build_brief(city="mumbai")
    inp = FeasibilityInput(brief=brief)
    r = check_water_table_practical(inp)
    # Mumbai default = 0.5m post-monsoon (very shallow)
    assert r.confidence.value == "low"
    assert r.assumption_used is not None
    assert "Mumbai" in r.assumption_used
    print(f"PASS water table practical uses Mumbai city default "
          f"({r.details['water_table_depth_m']}m), LOW conf")


# ─── Water table check (Code-Strict) ──────────────────────────────────

def test_water_table_code_strict_hard_fails_unverified():
    """Habitable ground floor + unverified WT → HARD_FAIL."""
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_water_table_code_strict,
    )
    brief = _build_brief()  # Default residential ground floor
    inp = FeasibilityInput(brief=brief)
    r = check_water_table_code_strict(inp)
    assert r.severity.value == "hard_fail"
    print("PASS water table code_strict HARD_FAILs for unverified ground habitable")


def test_water_table_code_strict_pass_when_verified():
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        check_water_table_code_strict,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        water_table_depth_m=InputField.verified(12.0),
    )
    r = check_water_table_code_strict(inp)
    assert r.severity.value == "pass"
    print("PASS water table code_strict PASSes for verified WT")


# ─── Water table gap ──────────────────────────────────────────────────

def test_water_table_gap_blocking_when_unverified():
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        compute_water_table_gap,
    )
    from buildemup.domain.feasibility import GapSeverity
    brief = _build_brief()
    inp = FeasibilityInput(brief=brief)
    g = compute_water_table_gap(inp)
    assert g is not None
    assert g.severity == GapSeverity.BLOCKING_IF_NOT_ACCEPTED
    print("PASS water table gap BLOCKING when unverified + habitable ground")


def test_water_table_gap_none_when_verified():
    from buildemup.components.c02.feasibility_input import (
        FeasibilityInput, InputField,
    )
    from buildemup.components.c02.site_input_checks import (
        compute_water_table_gap,
    )
    brief = _build_brief()
    inp = FeasibilityInput(
        brief=brief,
        water_table_depth_m=InputField.verified(12.0),
    )
    g = compute_water_table_gap(inp)
    assert g is None
    print("PASS water table gap None when verified")


# ─── Downgrade rule (the user-approved principle) ─────────────────────

def test_downgrade_rule_applies_to_assumed_hard_only():
    """The 'don't HARD on a guess' rule applies ONLY when source is
    DOESNT_KNOW or NOT_ASKED, not when user provided value."""
    from buildemup.components.c02.feasibility_input import FieldSource
    from buildemup.components.c02.site_input_checks import (
        _maybe_downgrade_severity,
    )
    from buildemup.domain.feasibility import CheckSeverity

    # Assumed HARD → downgraded to SOFT
    new_sev, note = _maybe_downgrade_severity(
        CheckSeverity.HARD_FAIL, FieldSource.USER_DOESNT_KNOW,
    )
    assert new_sev == CheckSeverity.SOFT_WARN
    assert note is not None

    # Verified HARD → NOT downgraded
    new_sev, note = _maybe_downgrade_severity(
        CheckSeverity.HARD_FAIL, FieldSource.USER_PROVIDED_VERIFIED,
    )
    assert new_sev == CheckSeverity.HARD_FAIL
    assert note is None

    # Unverified HARD → NOT downgraded (user gave a value, even if unverified)
    new_sev, note = _maybe_downgrade_severity(
        CheckSeverity.HARD_FAIL, FieldSource.USER_PROVIDED_UNVERIFIED,
    )
    assert new_sev == CheckSeverity.HARD_FAIL
    assert note is None

    # SOFT_WARN never downgrades
    new_sev, note = _maybe_downgrade_severity(
        CheckSeverity.SOFT_WARN, FieldSource.USER_DOESNT_KNOW,
    )
    assert new_sev == CheckSeverity.SOFT_WARN
    assert note is None
    print("PASS downgrade rule applies only to assumed HARD_FAILs")


# ─── Integration ──────────────────────────────────────────────────────

def test_session_a_b_c_d_e_checks_run_together():
    """All checks across A-E coexist."""
    from buildemup.components.c02.feasibility_input import FeasibilityInput
    from buildemup.components.c02.site_input_checks import (
        check_soil_type_practical, check_water_table_practical,
    )
    brief = _build_brief()
    inp = FeasibilityInput(brief=brief)
    soil = check_soil_type_practical(inp)
    wt = check_water_table_practical(inp)
    # Both should be valid CheckResults (don't care about severity here)
    assert soil.check_id == "soil_type_practical"
    assert wt.check_id == "water_table_practical"
    print("PASS Session E checks integrate (soil + water table run cleanly)")


def test_v0_9_3_baseline_unaffected_by_session_e():
    from buildemup.components.c01_brief_capture import (
        BriefCaptureEngine, BriefCaptureInput,
    )
    from buildemup.domain import (
        FloorRequirement, RoomRequirement, FloorUse, RoomType,
    )
    inp = BriefCaptureInput(
        plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
        city="chennai", road_width_m=9.0,
        user_setback_front_m=1.5, user_setback_rear_m=1.5,
        user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
        floors=(FloorRequirement(0, FloorUse.RESIDENTIAL,
            (RoomRequirement(RoomType.LIVING, 1),)),),
        budget_min_lakhs=20, budget_max_lakhs=30,
    )
    out = BriefCaptureEngine().execute(inp)
    assert out.risk_level == "LOW"
    print("PASS v0.9.3 baseline unaffected by Session E")


if __name__ == "__main__":
    print("=" * 70)
    print("Component 2 — Session E (3-state Input + Soil + Water Table)")
    print("=" * 70)
    print()

    print("--- InputField invariants ---")
    test_input_field_verified_classmethod()
    test_input_field_unverified_classmethod()
    test_input_field_unknown_classmethod()
    test_input_field_not_asked_classmethod()
    test_input_field_rejects_verified_with_none_value()
    test_input_field_rejects_unknown_with_value()
    test_input_field_rejects_not_asked_with_value()
    test_field_source_has_4_states()
    test_input_field_verification_priority_for_value()
    print()

    print("--- FeasibilityInput defaults ---")
    test_feasibility_input_default_fields_all_not_asked()
    test_feasibility_input_can_partially_populate()
    print()

    print("--- city_feasibility_defaults KB ---")
    test_city_defaults_kb_loads_all_6_cities()
    test_city_defaults_pune_is_black_cotton()
    test_city_defaults_bangalore_has_deep_water_table()
    test_city_defaults_mumbai_has_shallow_water_table()
    test_city_defaults_validator_catches_missing_field()
    print()

    print("--- Soil type (Practical) ---")
    test_soil_practical_low_risk_pass()
    test_soil_practical_high_risk_verified_g3_hards()
    test_soil_practical_assumed_hard_downgrades_to_soft()
    test_soil_practical_uses_city_default_when_unknown()
    test_soil_practical_unverified_user_data_medium_confidence()
    print()

    print("--- Soil type (Code-Strict) ---")
    test_soil_code_strict_pass_for_single_floor()
    test_soil_code_strict_pass_when_verified()
    test_soil_code_strict_hard_fails_g1_unverified()
    test_soil_code_strict_hard_fails_g1_unknown()
    print()

    print("--- Soil type gap ---")
    test_soil_gap_none_for_single_floor()
    test_soil_gap_none_when_verified()
    test_soil_gap_blocking_when_g1_unverified()
    print()

    print("--- Water table (Practical) ---")
    test_water_table_practical_pass_when_deep()
    test_water_table_practical_soft_warn_when_shallow()
    test_water_table_practical_uses_city_default_when_unknown()
    print()

    print("--- Water table (Code-Strict) ---")
    test_water_table_code_strict_hard_fails_unverified()
    test_water_table_code_strict_pass_when_verified()
    print()

    print("--- Water table gap ---")
    test_water_table_gap_blocking_when_unverified()
    test_water_table_gap_none_when_verified()
    print()

    print("--- Downgrade rule (user-approved principle) ---")
    test_downgrade_rule_applies_to_assumed_hard_only()
    print()

    print("--- Integration ---")
    test_session_a_b_c_d_e_checks_run_together()
    test_v0_9_3_baseline_unaffected_by_session_e()
    print()

    print("=" * 70)
    print("ALL COMPONENT 2 SESSION E TESTS PASSED")
    print("=" * 70)
