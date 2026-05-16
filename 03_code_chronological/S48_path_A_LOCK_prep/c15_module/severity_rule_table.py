"""
BuildemUp — Component 15 — Severity Rule Table (v1 complete)
================================================================

Per C15 SPEC v0.2 LOCKED § 5.2 + Inv P8/P15 + A4 (severity_basis
≥ 20 chars citing source).

Maps `(check_id, status, cultural_profile_or_None)` → CheckSeverity.
Phase σ of the orchestrator looks up severity for each ProblemCheck
after Phase ρ determines status.

This is the v1 full table covering all RUNNABLE checks in dims
1, 2, 3, 5, 6, 7. Purely-deferred checks (dim 4, 8, 9, 10, plus
P1.2, P1.4, P6.2/3/4, P7.4) have NO rules — they never emit a
non-NA status.

Per Inv P18 (≥20 char severity_basis): every rule's basis is at
least 20 characters; SeverityRule's __post_init__ enforces.
"""
from __future__ import annotations

from .contracts import CulturalProfile
from .schema import CheckSeverity, CheckStatus, SeverityRule


# =============================================================================
# Citation constants (>= 20 chars; Inv P18)
# =============================================================================

CITE_P11_FAIL = "Indian residential POE rule-of-thumb: circulation > 20% of carpet area is wasteful (architectural heuristic, not NBC)."
CITE_P11_WARN = "Indian residential POE rule-of-thumb: circulation 15-20% of carpet area is borderline."
CITE_P11_PASS = "Within architectural-heuristic acceptable range for residential circulation fraction."
CITE_P13_FAIL = "Neufert + Ching: habitable-room aspect ratio > 3:1 is functionally compromised."
CITE_P13_WARN = "Neufert + Ching: habitable-room aspect ratio 2.5-3:1 is borderline."
CITE_P13_PASS = "Aspect ratio within Neufert/Ching habitable-room guidance."

CITE_NBC_HAB_FAIL = "NBC 2016 Part 3 § 12.2 — habitable-room minimum area 9.5 m² (regulatory)."
CITE_NBC_HAB_PASS = "Meets NBC 2016 Part 3 § 12.2 habitable-room minimum area."
CITE_NBC_KIT_FAIL = "NBC 2016 Part 3 § 12.3 — kitchen minimum area 5.0 m² / 7.5 m² combined (regulatory)."
CITE_NBC_KIT_PASS = "Meets NBC 2016 Part 3 § 12.3 kitchen minimum area."
CITE_NBC_BATH_FAIL = "NBC 2016 Part 3 § 12.4 — bathroom 1.8 / WC 1.1 / combined 2.8 m² minima (regulatory)."
CITE_NBC_BATH_PASS = "Meets NBC 2016 Part 3 § 12.4 bathroom/WC minimum area."

CITE_NEUFERT_BED_FAIL = "Neufert + Ching: bedroom < 6 m² cannot accommodate queen bed + circulation."
CITE_NEUFERT_BED_WARN = "Neufert + Ching: bedroom below adequacy target (9 m² standard / 12 m² master)."
CITE_NEUFERT_BED_PASS = "Meets Neufert/Ching bedroom adequacy target."
CITE_LIVING_FAIL = "Indian residential POE: living below NBC habitable 9.5 m² (regulatory + functional fail)."
CITE_LIVING_WARN = "Indian residential POE: living below 12 m² baseline for typical 3-4 BHK family."
CITE_LIVING_PASS = "Meets Indian residential 12 m² living-room baseline target."

CITE_P31_FAIL = "Hillier 1984 space syntax: bedroom step-depth > 4 from entry is fatiguing."
CITE_P31_WARN = "Hillier 1984: bedroom step-depth 4 from entry is borderline."
CITE_P31_PASS = "Bedroom step-depth within Hillier 1984 ergonomic target (≤ 3)."
CITE_P32_WARN = "Hillier 1984/1987: public-to-private depth monotonicity inverted."
CITE_P32_PASS = "Hillier privacy gradient holds: bedrooms deeper than public rooms."
CITE_P33_WARN = "Standard residential adjacency: kitchen-dining should share wall or door."
CITE_P33_PASS = "Kitchen-dining adjacency holds; food-carry path is short."
CITE_P34_WARN = "Indian residential POE: pooja room accessible from public zone."
CITE_P34_PASS = "Pooja room within one step of public zone — appropriately accessible."

CITE_P51_FAIL = "Standard residential privacy: bedroom adjacent to main entry breaks privacy."
CITE_P51_PASS = "Bedrooms not directly adjacent to main entry; privacy preserved."
CITE_P52_WARN = "Hillier 1984 privacy gradient: master bedroom at step-depth < 3 is shallow."
CITE_P52_PASS = "Master bedroom at appropriate depth per Hillier privacy gradient."
CITE_P53_WARN = "Indian residential POE: master bedroom commonly has attached bathroom."
CITE_P53_PASS = "Master bedroom has attached/adjacent bathroom per Indian preference."
CITE_P54_WARN = "Indian residential POE: pooja room not directly visible from main entry."
CITE_P54_PASS = "Pooja room not directly visible from main entry; visual privacy preserved."
CITE_P55_WARN = "Acoustic-privacy heuristic: bedroom adjacent to entertainment room transmits noise."
CITE_P55_PASS = "No bedroom shares wall with entertainment rooms; acoustic privacy preserved."

CITE_P61_WARN = "Hillier 1984 betweenness; C14 BOTTLENECK_CONCENTRATION flag emitted upstream."
CITE_P61_PASS = "C14 emitted no bottleneck-concentration flags; circulation distributed."

CITE_P71_WARN = "Lifetime Homes Standard: bedroom-on-ground supports aging-in-place."
CITE_P71_PASS = "Lifetime Homes Standard met: at least one ground-floor bedroom."
CITE_P72_FAIL = "Lifetime Homes Standard: ground-floor toilet is critical for accessibility."
CITE_P72_PASS = "Lifetime Homes Standard met: ground-floor toilet present."
CITE_P73_FAIL = "Standard residential: primary daytime zones on ground minimizes stair traffic."
CITE_P73_PASS = "Living + kitchen both on ground floor; daily routines do not require stairs."

CITE_DEFERRED_DEFAULT = "Deferred check: severity not assigned because check did not run."


def _rule(cid: str, status: CheckStatus, sev: CheckSeverity, basis: str) -> SeverityRule:
    return SeverityRule(
        check_id=cid, status=status, cultural_profile=None,
        severity=sev, severity_basis=basis,
    )


SEVERITY_RULE_TABLE_V1: tuple[SeverityRule, ...] = tuple(sorted([
    # Dim 1 (P1.1 + P1.3 RUNNABLE)
    _rule("P1.1", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P11_PASS),
    _rule("P1.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P11_WARN),
    _rule("P1.1", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P11_FAIL),
    _rule("P1.3", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P13_PASS),
    _rule("P1.3", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P13_WARN),
    _rule("P1.3", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P13_FAIL),

    # Dim 2 (all 5 RUNNABLE)
    _rule("P2.1", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_NBC_HAB_PASS),
    _rule("P2.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_NBC_HAB_FAIL),
    _rule("P2.1", CheckStatus.FAIL, CheckSeverity.CRITICAL, CITE_NBC_HAB_FAIL),
    _rule("P2.2", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_NEUFERT_BED_PASS),
    _rule("P2.2", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_NEUFERT_BED_WARN),
    _rule("P2.2", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_NEUFERT_BED_FAIL),
    _rule("P2.3", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_NBC_KIT_PASS),
    _rule("P2.3", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_NBC_KIT_FAIL),
    _rule("P2.3", CheckStatus.FAIL, CheckSeverity.CRITICAL, CITE_NBC_KIT_FAIL),
    _rule("P2.4", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_NBC_BATH_PASS),
    _rule("P2.4", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_NBC_BATH_FAIL),
    _rule("P2.4", CheckStatus.FAIL, CheckSeverity.CRITICAL, CITE_NBC_BATH_FAIL),
    _rule("P2.5", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_LIVING_PASS),
    _rule("P2.5", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_LIVING_WARN),
    _rule("P2.5", CheckStatus.FAIL, CheckSeverity.CRITICAL, CITE_LIVING_FAIL),

    # Dim 3 (all 4 RUNNABLE)
    _rule("P3.1", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P31_PASS),
    _rule("P3.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P31_WARN),
    _rule("P3.1", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P31_FAIL),
    _rule("P3.2", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P32_PASS),
    _rule("P3.2", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P32_WARN),
    _rule("P3.2", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P32_WARN),
    _rule("P3.3", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P33_PASS),
    _rule("P3.3", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P33_WARN),
    _rule("P3.3", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P33_WARN),
    _rule("P3.4", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P34_PASS),
    _rule("P3.4", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P34_WARN),
    _rule("P3.4", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P34_WARN),

    # Dim 5 (all 5 RUNNABLE)
    _rule("P5.1", CheckStatus.PASS, CheckSeverity.IMPORTANT, CITE_P51_PASS),
    _rule("P5.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P51_FAIL),
    _rule("P5.1", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P51_FAIL),
    _rule("P5.2", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P52_PASS),
    _rule("P5.2", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P52_WARN),
    _rule("P5.2", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P52_WARN),
    _rule("P5.3", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P53_PASS),
    _rule("P5.3", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P53_WARN),
    _rule("P5.3", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P53_WARN),
    _rule("P5.4", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P54_PASS),
    _rule("P5.4", CheckStatus.WARN, CheckSeverity.NICE_TO_HAVE, CITE_P54_WARN),
    _rule("P5.4", CheckStatus.FAIL, CheckSeverity.NICE_TO_HAVE, CITE_P54_WARN),
    _rule("P5.5", CheckStatus.PASS, CheckSeverity.NICE_TO_HAVE, CITE_P55_PASS),
    _rule("P5.5", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P55_WARN),
    _rule("P5.5", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P55_WARN),

    # Dim 6 (P6.1 RUNNABLE only)
    _rule("P6.1", CheckStatus.PASS, CheckSeverity.IMPORTANT, CITE_P61_PASS),
    _rule("P6.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P61_WARN),
    _rule("P6.1", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P61_WARN),

    # Dim 7 (P7.1-P7.3 PARTIAL-RUNNABLE)
    _rule("P7.1", CheckStatus.PASS, CheckSeverity.IMPORTANT, CITE_P71_PASS),
    _rule("P7.1", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P71_WARN),
    _rule("P7.1", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P71_WARN),
    _rule("P7.2", CheckStatus.PASS, CheckSeverity.IMPORTANT, CITE_P72_PASS),
    _rule("P7.2", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P72_FAIL),
    _rule("P7.2", CheckStatus.FAIL, CheckSeverity.CRITICAL, CITE_P72_FAIL),
    _rule("P7.3", CheckStatus.PASS, CheckSeverity.IMPORTANT, CITE_P73_PASS),
    _rule("P7.3", CheckStatus.WARN, CheckSeverity.IMPORTANT, CITE_P73_FAIL),
    _rule("P7.3", CheckStatus.FAIL, CheckSeverity.IMPORTANT, CITE_P73_FAIL),

    # =========================================================================
    # CULTURAL-PROFILE-SPECIFIC OVERRIDES (v1, per A3 + B-C15-CULTURAL-PROFILE-V1-LOCK)
    # =========================================================================
    # Per v0.2 A3 + LOCK-mandatory B-C15-CULTURAL-PROFILE-V1-LOCK:
    # ≥3 sub-variants must produce MEASURABLY DIFFERENT outputs on the
    # same input. The differentiation lives at severity-rule level so
    # check logic stays single-source-of-truth.
    #
    # lookup_severity prefers (check_id, status, profile)-matched rules
    # over (check_id, status, None) defaults. Adding profile-matched
    # rules for these check_ids causes profile-specific severities.
    #
    # Sub-variants differentiated at v1:
    #   1. Tamil multigen → P3.4 + P5.4 pooja-related elevated to
    #      IMPORTANT (where default is NICE_TO_HAVE). Pooja room is a
    #      core multigenerational ritual focal point.
    #   2. Kerala courtyard → P3.4 pooja IMPORTANT (ritual procession
    #      depends on pooja-public-room flow); P5.4 visual privacy of
    #      pooja IMPORTANT. (Same as Tamil for pooja, justified by
    #      different cultural rationale.)
    #   3. NRI returnee → P5.3 attached bath on master IMPORTANT
    #      (where default is NICE_TO_HAVE). Western-suite norm
    #      documented in CulturalProfile.INDIAN_NRI_RETURNEE docstring.

    # --- Tamil multigen overrides ---
    SeverityRule(
        check_id="P3.4", status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Tamil multigen profile: pooja room accessibility "
                       "from public zone is IMPORTANT, not nice-to-have; "
                       "household-ritual focal point per A3 cultural lens.",
    ),
    SeverityRule(
        check_id="P3.4", status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Tamil multigen profile: pooja inaccessibility from "
                       "public zone is IMPORTANT, not nice-to-have; "
                       "household-ritual focal point per A3 cultural lens.",
    ),
    SeverityRule(
        check_id="P5.4", status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Tamil multigen profile: pooja visibility from main "
                       "entry erodes IMPORTANT ritual privacy in "
                       "multigenerational practice; A3 cultural lens.",
    ),
    SeverityRule(
        check_id="P5.4", status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Tamil multigen profile: pooja visibility from main "
                       "entry erodes IMPORTANT ritual privacy in "
                       "multigenerational practice; A3 cultural lens.",
    ),

    # --- Kerala courtyard overrides ---
    SeverityRule(
        check_id="P3.4", status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Kerala courtyard profile: ritual procession from "
                       "entry through public rooms to pooja is core "
                       "nalukettu pattern; pooja accessibility IMPORTANT.",
    ),
    SeverityRule(
        check_id="P3.4", status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Kerala courtyard profile: ritual procession requires "
                       "pooja accessibility from public zone; IMPORTANT "
                       "per nalukettu cultural pattern.",
    ),
    SeverityRule(
        check_id="P5.4", status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Kerala courtyard profile: pooja visual privacy from "
                       "main entry is IMPORTANT per nalukettu inner-sanctum "
                       "vs. outer-public zone distinction.",
    ),
    SeverityRule(
        check_id="P5.4", status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="Kerala courtyard profile: pooja visual privacy from "
                       "main entry is IMPORTANT per nalukettu inner-sanctum "
                       "vs. outer-public zone distinction.",
    ),

    # --- NRI returnee overrides ---
    SeverityRule(
        check_id="P5.3", status=CheckStatus.WARN,
        cultural_profile=CulturalProfile.INDIAN_NRI_RETURNEE,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="NRI returnee profile: master-suite-with-attached-bath "
                       "is the Western residential default the user is "
                       "returning from; IMPORTANT per A3 cultural lens.",
    ),
    SeverityRule(
        check_id="P5.3", status=CheckStatus.FAIL,
        cultural_profile=CulturalProfile.INDIAN_NRI_RETURNEE,
        severity=CheckSeverity.IMPORTANT,
        severity_basis="NRI returnee profile: master without attached bath "
                       "diverges from Western suite norm the user is "
                       "accustomed to; IMPORTANT per A3 cultural lens.",
    ),
], key=lambda r: (r.check_id, r.status.value, r.cultural_profile.value if r.cultural_profile else "")))


# Back-compat alias for Sub-2 tests
SEVERITY_RULE_TABLE_V_SUB2 = SEVERITY_RULE_TABLE_V1

# Sub-2 individual rule re-exports for back-compat (one example per status × P1.1 + P1.3)
P11_PASS_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.1" and r.status == CheckStatus.PASS)
P11_WARN_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.1" and r.status == CheckStatus.WARN)
P11_FAIL_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.1" and r.status == CheckStatus.FAIL)
P13_PASS_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.3" and r.status == CheckStatus.PASS)
P13_WARN_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.3" and r.status == CheckStatus.WARN)
P13_FAIL_DEFAULT = next(r for r in SEVERITY_RULE_TABLE_V1 if r.check_id == "P1.3" and r.status == CheckStatus.FAIL)


def lookup_severity(
    rule_table: tuple[SeverityRule, ...],
    *,
    check_id: str,
    status: CheckStatus,
    cultural_profile: CulturalProfile,
) -> CheckSeverity:
    from .errors import CheckRegistryError

    if status is CheckStatus.NOT_APPLICABLE:
        raise CheckRegistryError(
            f"lookup_severity called with status=NOT_APPLICABLE for check_id {check_id!r}; "
            f"NOT_APPLICABLE routes to DeferredCheck and bypasses severity lookup."
        )

    for rule in rule_table:
        if rule.check_id == check_id and rule.status == status and rule.cultural_profile == cultural_profile:
            return rule.severity
    for rule in rule_table:
        if rule.check_id == check_id and rule.status == status and rule.cultural_profile is None:
            return rule.severity

    raise CheckRegistryError(
        f"No severity rule found for (check_id={check_id!r}, status={status}, cultural_profile={cultural_profile})."
    )


def verify_rule_table_integrity(
    rule_table: tuple[SeverityRule, ...],
    *,
    registered_check_ids: frozenset[str],
) -> None:
    from .errors import CheckRegistryError

    by_id: dict[str, set[CheckStatus]] = {}
    for rule in rule_table:
        by_id.setdefault(rule.check_id, set())
        if rule.cultural_profile is None:
            by_id[rule.check_id].add(rule.status)

    for cid in registered_check_ids:
        if cid not in by_id:
            continue
        statuses = by_id[cid]
        required = {CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL}
        missing = required - statuses
        if missing:
            raise CheckRegistryError(
                f"Severity rule table incomplete for check_id {cid!r}: missing status(es) "
                f"{sorted(s.value for s in missing)}."
            )

    rule_ids = set(by_id.keys())
    orphans = rule_ids - registered_check_ids
    if orphans:
        raise CheckRegistryError(
            f"Severity rule table contains rules for un-registered check_id(s) {sorted(orphans)}."
        )


__all__ = [
    "SEVERITY_RULE_TABLE_V1",
    "SEVERITY_RULE_TABLE_V_SUB2",
    "P11_PASS_DEFAULT", "P11_WARN_DEFAULT", "P11_FAIL_DEFAULT",
    "P13_PASS_DEFAULT", "P13_WARN_DEFAULT", "P13_FAIL_DEFAULT",
    "CITE_P11_FAIL", "CITE_P11_WARN", "CITE_P11_PASS",
    "CITE_P13_FAIL", "CITE_P13_WARN", "CITE_P13_PASS",
    "CITE_DEFERRED_DEFAULT",
    "lookup_severity", "verify_rule_table_integrity",
]
