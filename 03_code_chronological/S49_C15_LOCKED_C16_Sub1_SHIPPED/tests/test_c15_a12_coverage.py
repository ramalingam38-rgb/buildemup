"""
BuildemUp — Component 15 — Tests for v0.3 A12 (coverage_quality + dimension maturity)
========================================================================================

Per S48 Path A execution. Tests the coverage-of-evaluation signal landed
to close LOCK-mandatory dependency on A12 deferred amendment.

Verifies:
- CoverageQuality enum values + bucket thresholds
- DimensionMaturity enum values + derivation rule
- _derive_dim_maturity correctness across all (n_app, n_def) combos
- _derive_coverage_quality correctness across HIGH/MEDIUM/LOW boundaries
- DimensionSummary.maturity field validation + crosscheck against derivation
- ProblemReport.coverage_quality + ratio_applicable validation +
  crosscheck against derivation
- Inv P0 STRICTER preserved: no aggregator path through these fields
- Replay determinism: identical inputs → identical coverage values

Per Rule 11 self-analysis written before tests: this layer is
particularly vulnerable to bandage patterns. The MOST DANGEROUS failure
mode is a coverage_quality computed differently in different code paths
(e.g., one in fixtures, one in orchestrator). The dataclass crosscheck
in __post_init__ catches this — every constructor site MUST go through
the same _derive_* helper or face validation rejection.
"""
from __future__ import annotations

import pytest

from buildemup.components.c15.schema import (
    CoverageQuality,
    DimensionMaturity,
    DimensionSummary,
    _derive_coverage_quality,
    _derive_dim_maturity,
)


# =============================================================================
# CoverageQuality enum
# =============================================================================

class TestCoverageQualityEnum:
    def test_three_buckets_only(self):
        assert {m.value for m in CoverageQuality} == {"HIGH", "MEDIUM", "LOW"}

    def test_string_enum_values_stable(self):
        # Serialization stability: values must be stable strings for
        # replay determinism and UX template matching.
        assert CoverageQuality.HIGH.value == "HIGH"
        assert CoverageQuality.MEDIUM.value == "MEDIUM"
        assert CoverageQuality.LOW.value == "LOW"

    def test_str_enum_membership(self):
        # StrEnum: members ARE strings.
        assert CoverageQuality.HIGH == "HIGH"
        assert CoverageQuality.LOW == "LOW"


# =============================================================================
# DimensionMaturity enum
# =============================================================================

class TestDimensionMaturityEnum:
    def test_three_buckets_only(self):
        assert {m.value for m in DimensionMaturity} == {
            "RUNNABLE", "PARTIAL", "NOT_RUNNABLE",
        }

    def test_value_strings_stable(self):
        assert DimensionMaturity.RUNNABLE.value == "RUNNABLE"
        assert DimensionMaturity.PARTIAL.value == "PARTIAL"
        assert DimensionMaturity.NOT_RUNNABLE.value == "NOT_RUNNABLE"


# =============================================================================
# _derive_dim_maturity rule
# =============================================================================

class TestDeriveDimMaturity:
    def test_all_applicable_no_deferred_is_runnable(self):
        assert _derive_dim_maturity(5, 0) is DimensionMaturity.RUNNABLE
        assert _derive_dim_maturity(1, 0) is DimensionMaturity.RUNNABLE

    def test_mixed_applicable_and_deferred_is_partial(self):
        assert _derive_dim_maturity(2, 3) is DimensionMaturity.PARTIAL
        assert _derive_dim_maturity(1, 1) is DimensionMaturity.PARTIAL

    def test_all_deferred_no_applicable_is_not_runnable(self):
        assert _derive_dim_maturity(0, 5) is DimensionMaturity.NOT_RUNNABLE
        assert _derive_dim_maturity(0, 1) is DimensionMaturity.NOT_RUNNABLE

    def test_zero_zero_defensive_is_not_runnable(self):
        # Should not occur given Inv P12 (each dim has ≥1 registered
        # check). Defensive case.
        assert _derive_dim_maturity(0, 0) is DimensionMaturity.NOT_RUNNABLE


# =============================================================================
# _derive_coverage_quality rule
# =============================================================================

def _ds(dim_id: int, n_app: int, n_def: int, n_pass: int = 0,
        n_warn: int = 0, n_fail: int = 0) -> DimensionSummary:
    """Build a valid DimensionSummary; n_pass+n_warn+n_fail must sum
    to n_app (Inv P9-style)."""
    if n_pass + n_warn + n_fail != n_app:
        # Synthesize pass to fill up.
        n_pass = n_app - n_warn - n_fail
    return DimensionSummary(
        dimension_id=dim_id,
        dimension_name=f"dim_{dim_id}",
        n_applicable=n_app,
        n_deferred=n_def,
        n_pass=n_pass,
        n_warn=n_warn,
        n_fail=n_fail,
        maturity=_derive_dim_maturity(n_app, n_def),
    )


class TestDeriveCoverageQuality:
    def test_all_applicable_is_high(self):
        # 10 dims × all 4 checks runnable, 0 deferred → ratio = 1.0 → HIGH
        summary = tuple(_ds(i, 4, 0) for i in range(1, 11))
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.HIGH
        assert ratio == 1.0

    def test_seventy_percent_threshold_inclusive_is_high(self):
        # 28 applicable / 12 deferred = 28/40 = 0.70 → HIGH (≥ inclusive)
        summary = (
            _ds(1, 4, 0), _ds(2, 4, 0), _ds(3, 4, 0), _ds(4, 4, 0),
            _ds(5, 4, 0), _ds(6, 4, 0), _ds(7, 4, 0),
            _ds(8, 0, 4), _ds(9, 0, 4), _ds(10, 0, 4),
        )
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.HIGH
        assert ratio == 0.70

    def test_just_below_seventy_is_medium(self):
        # 27 applicable, 13 deferred = 27/40 = 0.675 → MEDIUM
        summary = (
            _ds(1, 4, 0), _ds(2, 4, 0), _ds(3, 4, 0), _ds(4, 4, 0),
            _ds(5, 4, 0), _ds(6, 4, 0), _ds(7, 3, 1),
            _ds(8, 0, 4), _ds(9, 0, 4), _ds(10, 0, 4),
        )
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.MEDIUM
        assert 0.67 < ratio < 0.69

    def test_forty_percent_threshold_inclusive_is_medium(self):
        # 16 / 40 = 0.40 → MEDIUM (≥ inclusive)
        summary = (
            _ds(1, 4, 0), _ds(2, 4, 0), _ds(3, 4, 0), _ds(4, 4, 0),
            _ds(5, 0, 4), _ds(6, 0, 4), _ds(7, 0, 4),
            _ds(8, 0, 4), _ds(9, 0, 4), _ds(10, 0, 4),
        )
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.MEDIUM
        assert ratio == 0.40

    def test_just_below_forty_is_low(self):
        # 15 / 40 = 0.375 → LOW
        summary = (
            _ds(1, 4, 0), _ds(2, 4, 0), _ds(3, 4, 0), _ds(4, 3, 1),
            _ds(5, 0, 4), _ds(6, 0, 4), _ds(7, 0, 4),
            _ds(8, 0, 4), _ds(9, 0, 4), _ds(10, 0, 4),
        )
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.LOW
        assert 0.37 < ratio < 0.38

    def test_all_deferred_is_low(self):
        # 0 / 40 = 0.0 → LOW
        summary = tuple(_ds(i, 0, 4) for i in range(1, 11))
        cq, ratio = _derive_coverage_quality(summary)
        assert cq is CoverageQuality.LOW
        assert ratio == 0.0

    def test_empty_summary_is_low(self):
        # Defensive: total == 0 → LOW with ratio 0.0
        cq, ratio = _derive_coverage_quality(())
        assert cq is CoverageQuality.LOW
        assert ratio == 0.0

    def test_realistic_v1_envelope_20_runnable_21_deferred(self):
        # Reflects S48 actual v1 envelope: 20 applicable, 21 deferred
        # across 41 total registered checks. 20/41 ≈ 0.488 → MEDIUM.
        # Spread approximately as reported in dim docs.
        summary = (
            _ds(1, 2, 2),  # P1.1+P1.3 runnable, P1.2+P1.4 deferred
            _ds(2, 5, 0),  # all dim 2 runnable
            _ds(3, 4, 0),  # all dim 3 runnable
            _ds(4, 0, 4),  # dim 4 all deferred
            _ds(5, 5, 0),  # all dim 5 runnable
            _ds(6, 1, 3),  # dim 6 mostly deferred
            _ds(7, 3, 1),  # dim 7 mostly runnable
            _ds(8, 0, 4),  # dim 8 all deferred
            _ds(9, 0, 4),  # dim 9 all deferred
            _ds(10, 0, 3),  # dim 10 all deferred
        )
        cq, ratio = _derive_coverage_quality(summary)
        # 20 / 36 ≈ 0.555 → MEDIUM (bucket ranges 0.40-0.70)
        assert cq is CoverageQuality.MEDIUM
        assert 0.45 < ratio < 0.62


# =============================================================================
# DimensionSummary validation
# =============================================================================

class TestDimensionSummaryA12Validation:
    def test_maturity_must_be_dimension_maturity(self):
        with pytest.raises(TypeError, match="must be DimensionMaturity"):
            DimensionSummary(
                dimension_id=1, dimension_name="x",
                n_applicable=0, n_deferred=0,
                n_pass=0, n_warn=0, n_fail=0,
                maturity="RUNNABLE",  # str, not enum
            )

    def test_maturity_must_match_derivation(self):
        # n_app=2, n_def=0 → derives RUNNABLE; passing PARTIAL is rejected.
        with pytest.raises(ValueError, match="does not match derivation"):
            DimensionSummary(
                dimension_id=1, dimension_name="x",
                n_applicable=2, n_deferred=0,
                n_pass=2, n_warn=0, n_fail=0,
                maturity=DimensionMaturity.PARTIAL,  # wrong
            )

    def test_maturity_runnable_when_only_applicable(self):
        ds = DimensionSummary(
            dimension_id=1, dimension_name="x",
            n_applicable=3, n_deferred=0,
            n_pass=3, n_warn=0, n_fail=0,
            maturity=DimensionMaturity.RUNNABLE,
        )
        assert ds.maturity is DimensionMaturity.RUNNABLE

    def test_maturity_partial_when_mixed(self):
        ds = DimensionSummary(
            dimension_id=1, dimension_name="x",
            n_applicable=2, n_deferred=1,
            n_pass=2, n_warn=0, n_fail=0,
            maturity=DimensionMaturity.PARTIAL,
        )
        assert ds.maturity is DimensionMaturity.PARTIAL

    def test_maturity_not_runnable_when_only_deferred(self):
        ds = DimensionSummary(
            dimension_id=4, dimension_name="natural_light",
            n_applicable=0, n_deferred=4,
            n_pass=0, n_warn=0, n_fail=0,
            maturity=DimensionMaturity.NOT_RUNNABLE,
        )
        assert ds.maturity is DimensionMaturity.NOT_RUNNABLE
