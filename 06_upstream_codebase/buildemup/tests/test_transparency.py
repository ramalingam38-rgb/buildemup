"""Tests for Transparency Triple utility."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.utils.transparency import (
    TransparencyTriple,
    DerivationLine,
    Confidence,
    lakh,
)


def test_basic_range_calculation():
    """Range is correctly computed from exact value and uncertainty."""
    t = TransparencyTriple(
        label="Cost",
        exact_value=5_850_000.0,
        uncertainty_pct=10.0,
    )
    assert abs(t.low - 5_265_000.0) < 0.01
    assert abs(t.high - 6_435_000.0) < 0.01
    print(f"PASS basic range: {t.format_short()}")


def test_zero_uncertainty():
    """A precisely known value has range == exact value."""
    t = TransparencyTriple(
        label="Column count",
        exact_value=16,
        unit="cols",
        uncertainty_pct=0.0,
        confidence=Confidence.HIGH,
    )
    assert t.low == t.high == 16
    print(f"PASS zero uncertainty: {t.format_short()}")


def test_derivation_lines():
    """Derivation lines format correctly."""
    line = DerivationLine(
        label="Concrete (M25)",
        quantity=14.0,
        unit="cum",
        rate=7500,
        rate_unit="₹/cum",
        amount=105_000,
        source="Chennai 2026",
    )
    formatted = line.format_line()
    assert "Concrete" in formatted
    assert "14" in formatted
    assert "7,500" in formatted
    print(f"PASS derivation: {formatted}")


def test_full_report_format():
    """Full report combines short summary, derivation, and notes."""
    t = TransparencyTriple(
        label="Structural cost",
        exact_value=14_59_000,
        unit="₹",
        uncertainty_pct=8.0,
        confidence=Confidence.HIGH,
        derivation=[
            DerivationLine("Concrete (M25)", 55, "cum", 7500, "₹/cum", 4_12_500, "Chennai 2026"),
            DerivationLine("Steel TMT Fe500", 5.5, "tonne", 72_000, "₹/tonne", 3_96_000, "JSW 2026"),
            DerivationLine("Shuttering + labour", amount=6_50_000, source="trade rate Chennai"),
        ],
        notes=[
            "Steel rate fluctuates ±5% with market conditions",
            "Labour cost depends on contractor's scale of operation",
        ],
    )
    full = t.format_full()
    assert "Structural cost" in full
    assert "Breakdown" in full
    assert "Why the range exists" in full
    print("PASS full report format:")
    print(full)


def test_lakh_helper():
    """₹ to lakhs formatter."""
    assert lakh(5_850_000) == "₹58.5L"
    assert lakh(7_50_000) == "₹7.5L"
    print(f"PASS lakh helper: {lakh(5_850_000)}, {lakh(7_50_000)}")


def test_dict_serialization():
    """to_dict produces a clean machine-readable form."""
    t = TransparencyTriple(
        label="Plumbing cost",
        exact_value=2_85_000,
        unit="₹",
        uncertainty_pct=5.0,
        confidence=Confidence.HIGH,
    )
    d = t.to_dict()
    assert d["label"] == "Plumbing cost"
    assert d["exact_value"] == 2_85_000
    assert d["confidence"] == "WELL_CONSTRAINED"
    assert abs(d["low"] - 2_70_750.0) < 0.01
    print(f"PASS dict serialization: {d['label']} confidence={d['confidence']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing TransparencyTriple utility")
    print("=" * 60)
    test_basic_range_calculation()
    test_zero_uncertainty()
    test_derivation_lines()
    test_full_report_format()
    test_lakh_helper()
    test_dict_serialization()
    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
