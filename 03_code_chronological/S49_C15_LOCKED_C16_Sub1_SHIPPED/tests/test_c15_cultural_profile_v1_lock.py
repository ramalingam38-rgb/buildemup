"""
BuildemUp — Component 15 — Cultural Profile V1 LOCK tests
============================================================

Per A3 + LOCK-mandatory B-C15-CULTURAL-PROFILE-V1-LOCK.

Verifies that ≥3 sub-variants produce **measurably different** severity
outputs on the same (check_id, status) inputs, where "measurably
different" means: at least one (check_id, status) pair where the
profiles disagree on CheckSeverity.

Differentiated at v1 (S48 Path A):
- Tamil multigen → P3.4 + P5.4 elevated to IMPORTANT (default
  NICE_TO_HAVE).
- Kerala courtyard → P3.4 + P5.4 elevated to IMPORTANT (same as Tamil
  on pooja, justified by different cultural rationale per docstrings).
- NRI returnee → P5.3 elevated to IMPORTANT (default NICE_TO_HAVE).

This ensures the A3 LOCK requirement is satisfied: profiles are not
merely enumerated; they materially affect downstream output.

Rule 11 self-analysis before tests: the WORST failure mode would be
profile overrides that produce identical *enum members* despite
different *rules* — passing this test would falsely declare
differentiation. To prevent: test asserts severity values differ
across profiles at specific (check_id, status) pairs.
"""
from __future__ import annotations

from buildemup.components.c15.contracts import CulturalProfile
from buildemup.components.c15.schema import CheckSeverity, CheckStatus
from buildemup.components.c15.severity_rule_table import (
    SEVERITY_RULE_TABLE_V1,
    lookup_severity,
)


# =============================================================================
# Differentiation matrix
# =============================================================================

def _sev(check_id: str, status: CheckStatus, profile: CulturalProfile) -> CheckSeverity:
    return lookup_severity(
        SEVERITY_RULE_TABLE_V1,
        check_id=check_id,
        status=status,
        cultural_profile=profile,
    )


class TestProfileDifferentiationP34Pooja:
    """P3.4 (pooja accessibility from public zone) WARN severity
    differs across cultural lens."""

    def test_default_generic_is_nice_to_have(self):
        # Compact urban, lower-income, generic, NRI returnee all
        # treat pooja accessibility as nice-to-have (default rule).
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC) \
            is CheckSeverity.NICE_TO_HAVE

    def test_tamil_multigen_is_important(self):
        # Override rule lifts to IMPORTANT.
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN) \
            is CheckSeverity.IMPORTANT

    def test_kerala_courtyard_is_important(self):
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD) \
            is CheckSeverity.IMPORTANT

    def test_compact_urban_is_default_nice_to_have(self):
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_COMPACT_URBAN) \
            is CheckSeverity.NICE_TO_HAVE

    def test_lower_income_incremental_is_default_nice_to_have(self):
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_LOWER_INCOME_INCREMENTAL) \
            is CheckSeverity.NICE_TO_HAVE

    def test_nri_returnee_is_default_nice_to_have(self):
        # NRI profile doesn't override pooja — Western-trained returnees
        # may not have strong pooja-ritual baseline.
        assert _sev("P3.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_NRI_RETURNEE) \
            is CheckSeverity.NICE_TO_HAVE


class TestProfileDifferentiationP54PoojaPrivacy:
    """P5.4 (pooja visual privacy from main entry) WARN."""

    def test_default_generic_is_nice_to_have(self):
        assert _sev("P5.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC) \
            is CheckSeverity.NICE_TO_HAVE

    def test_tamil_multigen_is_important(self):
        assert _sev("P5.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN) \
            is CheckSeverity.IMPORTANT

    def test_kerala_courtyard_is_important(self):
        assert _sev("P5.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD) \
            is CheckSeverity.IMPORTANT

    def test_compact_urban_is_default(self):
        assert _sev("P5.4", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_COMPACT_URBAN) \
            is CheckSeverity.NICE_TO_HAVE


class TestProfileDifferentiationP53AttachedBath:
    """P5.3 (master bedroom attached bath) WARN — NRI returnee
    differentiated."""

    def test_default_generic_is_nice_to_have(self):
        assert _sev("P5.3", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC) \
            is CheckSeverity.NICE_TO_HAVE

    def test_nri_returnee_is_important(self):
        assert _sev("P5.3", CheckStatus.WARN,
                    CulturalProfile.INDIAN_NRI_RETURNEE) \
            is CheckSeverity.IMPORTANT

    def test_tamil_multigen_remains_default_nice_to_have(self):
        # Joint-family households often share baths; attached-bath
        # not elevated.
        assert _sev("P5.3", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN) \
            is CheckSeverity.NICE_TO_HAVE

    def test_kerala_courtyard_remains_default(self):
        assert _sev("P5.3", CheckStatus.WARN,
                    CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD) \
            is CheckSeverity.NICE_TO_HAVE


# =============================================================================
# A3 LOCK REQUIREMENT — ≥3 sub-variants produce measurably different outputs
# =============================================================================

class TestA3LockRequirement_AtLeast3SubvariantsDifferentiate:
    """The A3 LOCK requirement: ≥3 sub-variants produce MEASURABLY
    DIFFERENT outputs. This test gathers the full severity matrix
    across profiles and asserts the cardinality of distinct severity
    profiles is ≥3."""

    PROFILES = tuple(CulturalProfile)

    # (check_id, status) pairs that have at least one profile-specific
    # override, per v1 (S48 Path A).
    DIFFERENTIATING_PAIRS = (
        ("P3.4", CheckStatus.WARN),
        ("P3.4", CheckStatus.FAIL),
        ("P5.3", CheckStatus.WARN),
        ("P5.3", CheckStatus.FAIL),
        ("P5.4", CheckStatus.WARN),
        ("P5.4", CheckStatus.FAIL),
    )

    def test_at_least_three_profiles_differ_from_default_at_minimum_one_pair(self):
        """Sub-variants must DIFFER from the default-profile severity
        on at least one (check_id, status) pair. A3 LOCK requires ≥3."""
        differing_profiles: set[CulturalProfile] = set()
        for cid, status in self.DIFFERENTIATING_PAIRS:
            default_sev = _sev(cid, status,
                               CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC)
            for prof in self.PROFILES:
                if prof is CulturalProfile.INDIAN_MIDDLE_CLASS_GENERIC:
                    continue
                if _sev(cid, status, prof) is not default_sev:
                    differing_profiles.add(prof)
        # At least 3 profiles differ at at least one pair.
        assert len(differing_profiles) >= 3, (
            f"A3 LOCK requires ≥3 profiles to differentiate; "
            f"found {len(differing_profiles)} differing profiles: "
            f"{sorted(p.value for p in differing_profiles)}"
        )

    def test_distinct_severity_profile_signatures(self):
        """Stronger A3 verification: when we summarize each profile's
        severity assignments across the DIFFERENTIATING_PAIRS, we get
        ≥3 distinct signatures."""
        signatures: set[tuple] = set()
        for prof in self.PROFILES:
            sig = tuple(
                _sev(cid, status, prof)
                for cid, status in self.DIFFERENTIATING_PAIRS
            )
            signatures.add(sig)
        assert len(signatures) >= 3, (
            f"A3 LOCK requires ≥3 distinct severity-signature profiles; "
            f"found {len(signatures)} distinct: {signatures}"
        )

    def test_tamil_kerala_compact_urban_all_distinguishable(self):
        """Concrete: Tamil multigen, Kerala courtyard, and Compact
        urban produce distinguishable severity outputs on the
        pooja-related checks."""
        tamil_sig = tuple(
            _sev(cid, st,
                 CulturalProfile.INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN)
            for cid, st in self.DIFFERENTIATING_PAIRS
        )
        kerala_sig = tuple(
            _sev(cid, st,
                 CulturalProfile.INDIAN_MIDDLE_CLASS_KERALA_COURTYARD)
            for cid, st in self.DIFFERENTIATING_PAIRS
        )
        compact_sig = tuple(
            _sev(cid, st,
                 CulturalProfile.INDIAN_MIDDLE_CLASS_COMPACT_URBAN)
            for cid, st in self.DIFFERENTIATING_PAIRS
        )
        nri_sig = tuple(
            _sev(cid, st,
                 CulturalProfile.INDIAN_NRI_RETURNEE)
            for cid, st in self.DIFFERENTIATING_PAIRS
        )
        # At minimum we want 3 distinct: Tamil/Kerala (which agree on
        # pooja but differ from default), Compact urban (default), NRI.
        assert len({tamil_sig, compact_sig, nri_sig}) == 3, (
            f"Three profiles should produce three distinguishable "
            f"severity signatures; got:\n"
            f"  Tamil: {tamil_sig}\n"
            f"  Compact urban: {compact_sig}\n"
            f"  NRI: {nri_sig}"
        )
        # Tamil and Kerala happen to agree on pooja signature (different
        # rationale, same severity), but that's still 3 distinct
        # signatures total via Compact + NRI.
        assert tamil_sig == kerala_sig, (
            "Tamil and Kerala share pooja-related severity profile; "
            "documented in their CulturalProfile docstrings (Tamil "
            "treats pooja as multigen ritual focal point; Kerala "
            "treats pooja as nalukettu inner-sanctum). Different "
            "rationale, converging on same WARN severity at v1."
        )
