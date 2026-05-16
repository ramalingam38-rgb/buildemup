"""
BuildemUp — Component 15 — Sub-2 severity rule table tests
==============================================================

Per C15 SPEC v0.2 LOCKED Inv P8 / P15 + A4 (severity_basis citations):

- Every rule's severity_basis ≥ 20 chars (Inv P18 — enforced at
  schema construction; verified at table-build time here)
- Lookup semantics: profile-specific overrides default, both fall
  back to None
- Integrity check: each runnable check_id has rules for all three
  status (PASS/WARN/FAIL) under the default profile, OR has no
  rules at all (purely-deferred case)
- NOT_APPLICABLE status rejected on lookup
"""
from __future__ import annotations

import pytest

from buildemup.components.c15 import (
    C15_VERSION,
    CheckRegistryError,
    CheckSeverity,
    CheckStatus,
    CulturalProfile,
    MIN_SEVERITY_BASIS_LENGTH,
    SEVERITY_RULE_TABLE_V_SUB2,
    SeverityRule,
    build_registry,
    lookup_severity,
    verify_rule_table_integrity,
)
from buildemup.components.c15.severity_rule_table import (
    CITE_P11_FAIL,
    CITE_P11_PASS,
    CITE_P11_WARN,
    CITE_P13_FAIL,
    CITE_P13_PASS,
    CITE_P13_WARN,
)


# =============================================================================
# Table well-formedness
# =============================================================================

def test_table_is_tuple():
    assert isinstance(SEVERITY_RULE_TABLE_V_SUB2, tuple)


def test_table_non_empty_at_sub2():
    assert len(SEVERITY_RULE_TABLE_V_SUB2) > 0


def test_every_rule_is_severity_rule():
    for rule in SEVERITY_RULE_TABLE_V_SUB2:
        assert isinstance(rule, SeverityRule)


def test_every_rule_passes_min_severity_basis_length():
    # Inv P18: schema enforces ≥ 20 chars at construction. If any
    # rule's severity_basis is too short, construction would have
    # already failed. This is a belt-and-braces verification.
    for rule in SEVERITY_RULE_TABLE_V_SUB2:
        assert len(rule.severity_basis) >= MIN_SEVERITY_BASIS_LENGTH


def test_every_rule_check_id_pattern_valid():
    import re
    pat = re.compile(r"^P([1-9]|10)\.[1-9][0-9]*$")
    for rule in SEVERITY_RULE_TABLE_V_SUB2:
        assert pat.match(rule.check_id), (
            f"Rule check_id {rule.check_id!r} doesn't match the "
            f"expected P{{dim}}.{{idx}} pattern."
        )


def test_no_rule_has_not_applicable_status():
    # A5: NOT_APPLICABLE routes to DeferredCheck, NOT through
    # severity. Schema enforces this rejection at SeverityRule
    # construction; verify the table contains none anyway.
    for rule in SEVERITY_RULE_TABLE_V_SUB2:
        assert rule.status != CheckStatus.NOT_APPLICABLE


# =============================================================================
# Citation constants
# =============================================================================

def test_citation_constants_meet_min_length():
    for cite in [
        CITE_P11_FAIL,
        CITE_P11_WARN,
        CITE_P11_PASS,
        CITE_P13_FAIL,
        CITE_P13_WARN,
        CITE_P13_PASS,
    ]:
        assert len(cite) >= MIN_SEVERITY_BASIS_LENGTH


# =============================================================================
# lookup_severity
# =============================================================================

def test_lookup_finds_default_rule_when_profile_unspecified():
    sev = lookup_severity(
        SEVERITY_RULE_TABLE_V_SUB2,
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    )
    assert sev == CheckSeverity.IMPORTANT


def test_lookup_returns_pass_severity_for_pass_status():
    sev = lookup_severity(
        SEVERITY_RULE_TABLE_V_SUB2,
        check_id="P1.1",
        status=CheckStatus.PASS,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    )
    assert sev == CheckSeverity.NICE_TO_HAVE


def test_lookup_returns_warn_severity_for_warn_status():
    sev = lookup_severity(
        SEVERITY_RULE_TABLE_V_SUB2,
        check_id="P1.1",
        status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
    )
    assert sev == CheckSeverity.IMPORTANT


def test_lookup_rejects_not_applicable_status():
    with pytest.raises(CheckRegistryError, match="NOT_APPLICABLE"):
        lookup_severity(
            SEVERITY_RULE_TABLE_V_SUB2,
            check_id="P1.1",
            status=CheckStatus.NOT_APPLICABLE,
            cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        )


def test_lookup_raises_on_unknown_check_id():
    with pytest.raises(CheckRegistryError, match="No severity rule"):
        lookup_severity(
            SEVERITY_RULE_TABLE_V_SUB2,
            check_id="P9.99",
            status=CheckStatus.FAIL,
            cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC,
        )


def test_lookup_profile_specific_overrides_default():
    """If a profile-specific rule exists, lookup returns it instead
    of the default. Build a small mini-table to verify."""
    default_rule = SeverityRule(
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="default basis citation reference adequate length",
    )
    specific_rule = SeverityRule(
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.CRITICAL,
        severity_basis="profile-specific basis citation reference adequate length",
    )
    mini_table = (default_rule, specific_rule)
    sev = lookup_severity(
        mini_table,
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
    )
    assert sev == CheckSeverity.CRITICAL


def test_lookup_falls_back_to_default_when_profile_not_in_table():
    default_rule = SeverityRule(
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="default basis citation reference adequate length",
    )
    specific_rule = SeverityRule(
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.CRITICAL,
        severity_basis="profile-specific basis citation reference adequate length",
    )
    mini_table = (default_rule, specific_rule)
    # Lookup for a profile NOT in mini_table → default
    sev = lookup_severity(
        mini_table,
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
    )
    assert sev == CheckSeverity.IMPORTANT


# =============================================================================
# verify_rule_table_integrity
# =============================================================================

def test_integrity_passes_for_sub2_table_against_sub2_registry():
    reg = build_registry()
    # No exception expected.
    verify_rule_table_integrity(
        SEVERITY_RULE_TABLE_V_SUB2,
        registered_check_ids=frozenset(reg.ids()),
    )


def test_integrity_passes_for_purely_deferred_checks():
    """P1.2 and P1.4 are purely-deferred at Sub-2 (DEP_*-blocked, always
    emit DeferredCheck). They appear in the registry but have NO rules
    in the table — case (b) per the integrity-check contract. This
    should pass."""
    reg = build_registry()
    # Confirm the registered set includes the purely-deferred checks.
    assert "P1.2" in reg.ids()
    assert "P1.4" in reg.ids()
    # Confirm the rule table has no rules for them.
    rule_ids = {r.check_id for r in SEVERITY_RULE_TABLE_V_SUB2}
    assert "P1.2" not in rule_ids
    assert "P1.4" not in rule_ids
    # Integrity still passes (purely-deferred is allowed).
    verify_rule_table_integrity(
        SEVERITY_RULE_TABLE_V_SUB2,
        registered_check_ids=frozenset(reg.ids()),
    )


def test_integrity_rejects_orphan_rules():
    """A rule for an unregistered check_id is an orphan. The
    integrity check must surface this."""
    orphan_rule = SeverityRule(
        check_id="P9.99",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="orphan rule for unregistered check ID demo",
    )
    table_with_orphan = SEVERITY_RULE_TABLE_V_SUB2 + (orphan_rule,)
    # P9.99 is not in any registry; integrity should complain.
    with pytest.raises(CheckRegistryError, match="orphans|un-registered"):
        verify_rule_table_integrity(
            table_with_orphan,
            registered_check_ids=frozenset({"P1.1", "P1.3"}),
        )


def test_integrity_rejects_incomplete_runnable_check_rules():
    """If a check has SOME default rules but is missing one of
    PASS/WARN/FAIL, integrity must complain — that's a partial
    runnable that the orchestrator can't grade fully."""
    only_fail = SeverityRule(
        check_id="P1.1",
        status=CheckStatus.FAIL,
        cultural_profile=None,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="only FAIL rule provided here, missing pass + warn",
    )
    incomplete_table = (only_fail,)
    with pytest.raises(CheckRegistryError, match="incomplete"):
        verify_rule_table_integrity(
            incomplete_table,
            registered_check_ids=frozenset({"P1.1"}),
        )
