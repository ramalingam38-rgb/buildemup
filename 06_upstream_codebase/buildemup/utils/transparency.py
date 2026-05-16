"""
BuildemUp† — Transparency Triple Utility
==========================================

Implements Principle 2 from Design Principles v3.1:
Every numeric output gets THREE things:
  1. A range reflecting honest uncertainty
  2. An exact midpoint for users who want a single number
  3. The derivation showing how we got there

This is the most important user-trust utility in the whole codebase.
Every component MUST use this for any numeric output shown to users.

Confidence levels:
  HIGH    = engineering-verified (e.g., IS 456 column sizing)
  MEDIUM  = typical/modelled (e.g., assumed soil bearing)
  LOW     = variable/depends-on-contractor (e.g., labour rates)

†= placeholder name marker (BuildemUp† to be renamed later).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# Import the canonical Confidence enum (lives in confidence.py now)
from buildemup.utils.confidence import Confidence


@dataclass
class DerivationLine:
    """One line of the cost/quantity breakdown.

    Example:
      DerivationLine(
        label="Concrete (M25)",
        quantity=14.0,
        unit="cum",
        rate=7500,
        rate_unit="₹/cum",
        amount=105000,
        source="Chennai 2026 ready-mix avg",
      )
    """
    label: str
    quantity: float | None = None
    unit: str | None = None
    rate: float | None = None
    rate_unit: str | None = None
    amount: float = 0.0   # The ₹ value of this line (or quantity if no rate)
    source: str | None = None  # Where the rate/rule came from

    def format_line(self) -> str:
        """Human-readable single line. Used in user-facing reports."""
        # If we have quantity + rate, show the math
        if self.quantity is not None and self.rate is not None:
            qty_str = self._fmt_qty(self.quantity, self.unit)
            rate_str = f"₹{self.rate:,.0f}/{self.unit or 'unit'}"
            return f"  {self.label:<35} {qty_str} × {rate_str} = ₹{self.amount:,.0f}"
        # If only amount (e.g., a sub-total)
        return f"  {self.label:<35} {self._fmt_amount(self.amount)}"

    @staticmethod
    def _fmt_qty(q: float, unit: str | None) -> str:
        if q == int(q):
            return f"{int(q)} {unit or ''}"
        return f"{q:.1f} {unit or ''}"

    @staticmethod
    def _fmt_amount(a: float) -> str:
        if a >= 100_000:
            return f"₹{a/100_000:.2f}L"
        return f"₹{a:,.0f}"


@dataclass
class TransparencyTriple:
    """A numeric output with range, exact value, derivation, and confidence.

    This is the core trust-building primitive. Every cost, quantity,
    timeline, area, etc. shown to the user uses this.

    Args:
        label: What this number represents (e.g., "Estimated build cost").
        exact_value: The midpoint/best-estimate value (e.g., 5_850_000.0).
        unit: The unit (e.g., "₹", "sqft", "days", "cum").
        uncertainty_pct: ± percentage variability (e.g., 9.0 means ±9%).
        confidence: HIGH / MEDIUM / LOW.
        derivation: Ordered list of breakdown lines showing how we got here.
        notes: Optional list of variability drivers (why range exists).
    """
    label: str
    exact_value: float
    unit: str = "₹"
    uncertainty_pct: float = 10.0
    confidence: Confidence = Confidence.MEDIUM
    derivation: list[DerivationLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def low(self) -> float:
        """Lower bound of the range."""
        return self.exact_value * (1 - self.uncertainty_pct / 100.0)

    @property
    def high(self) -> float:
        """Upper bound of the range."""
        return self.exact_value * (1 + self.uncertainty_pct / 100.0)

    def format_short(self) -> str:
        """One-line summary. Used in dashboards.

        Example:  '₹56L–₹61L (most likely ₹58.5L) [Confidence: Regional typical]'
        """
        if self.unit == "₹":
            lo = self._fmt_lakhs(self.low)
            hi = self._fmt_lakhs(self.high)
            mid = self._fmt_lakhs(self.exact_value)
            return f"{lo}–{hi} (most likely {mid}) [Confidence: {self.confidence.display_label()}]"
        # Generic numeric
        return (
            f"{self.low:.1f}–{self.high:.1f} {self.unit} "
            f"(most likely {self.exact_value:.1f}) [Confidence: {self.confidence.display_label()}]"
        )

    def format_full(self) -> str:
        """Full multi-line presentation. Used in detailed reports.

        This is what the user sees when they click 'show breakdown'.
        """
        lines = [
            f"{self.label}: {self.format_short()}",
        ]
        if self.derivation:
            lines.append("")
            lines.append("Breakdown:")
            for d in self.derivation:
                lines.append(d.format_line())
        if self.notes:
            lines.append("")
            lines.append("Why the range exists:")
            for n in self.notes:
                lines.append(f"  • {n}")
        return "\n".join(lines)

    @staticmethod
    def _fmt_lakhs(value: float) -> str:
        if abs(value) >= 100_000:
            return f"₹{value/100_000:.1f}L"
        if abs(value) >= 1_000:
            return f"₹{value/1_000:.0f}K"
        return f"₹{value:.0f}"

    def to_dict(self) -> dict[str, Any]:
        """Machine-readable representation. Used by API/serialization."""
        return {
            "label": self.label,
            "exact_value": self.exact_value,
            "low": self.low,
            "high": self.high,
            "unit": self.unit,
            "uncertainty_pct": self.uncertainty_pct,
            "confidence": self.confidence.value,
            "derivation": [
                {
                    "label": d.label,
                    "quantity": d.quantity,
                    "unit": d.unit,
                    "rate": d.rate,
                    "rate_unit": d.rate_unit,
                    "amount": d.amount,
                    "source": d.source,
                }
                for d in self.derivation
            ],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransparencyTriple":
        """Reconstruct from dict produced by to_dict.

        Per S7a SPEC v1.0 LOCKED § 9.2 + § 9.4: round-trips structurally.
        `low` / `high` in the payload are derived from exact_value +
        uncertainty_pct and are recomputed on the new instance via
        properties — they are intentionally not stored as fields.
        """
        return cls(
            label=payload["label"],
            exact_value=payload["exact_value"],
            unit=payload.get("unit", "₹"),
            uncertainty_pct=payload.get("uncertainty_pct", 10.0),
            confidence=Confidence(payload.get("confidence", "REGIONAL_TYPICAL")),
            derivation=[
                DerivationLine(
                    label=d["label"],
                    quantity=d.get("quantity"),
                    unit=d.get("unit"),
                    rate=d.get("rate"),
                    rate_unit=d.get("rate_unit"),
                    amount=d.get("amount", 0.0),
                    source=d.get("source"),
                )
                for d in payload.get("derivation", [])
            ],
            notes=list(payload.get("notes", [])),
        )


def lakh(value_in_rupees: float) -> str:
    """Format ₹ as 'XL' shorthand. Common in user-facing text."""
    return f"₹{value_in_rupees/100_000:.1f}L"
