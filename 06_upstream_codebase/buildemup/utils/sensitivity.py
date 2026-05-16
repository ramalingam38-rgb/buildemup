"""
BuildemUp† — Sensitivity Analysis
===================================

For any cost estimate, shows: "if steel rate changes ±10%, cost changes ₹X."

This answers real contractor-negotiation questions:
  - "What if steel prices rise before my construction starts?"
  - "What if I pick premium tiles?"
  - "What if my contractor charges the high margin?"

Decision-support value: user can ask "what-if" questions without
re-running the whole engine.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass

from buildemup.utils.transparency import TransparencyTriple, DerivationLine


@dataclass(frozen=True)
class SensitivityLine:
    """One row of sensitivity analysis."""
    driver_name: str             # e.g., "Steel rate"
    driver_variability_pct: float # e.g., 8.0 (±8%)
    impact_on_total_rupees: float # ₹ impact of this ± variation
    impact_pct_of_total: float    # % of total cost this represents

    def format_line(self) -> str:
        sign = "±"
        if self.impact_on_total_rupees >= 100_000:
            impact_str = f"{sign}₹{self.impact_on_total_rupees/100_000:.2f}L"
        else:
            impact_str = f"{sign}₹{self.impact_on_total_rupees:,.0f}"
        return (
            f"  {self.driver_name:<28} "
            f"{sign}{self.driver_variability_pct:.0f}% "
            f"→ {impact_str} ({self.impact_pct_of_total:.1f}% of total)"
        )


@dataclass(frozen=True)
class SensitivityReport:
    """Complete sensitivity analysis for a cost."""
    cost_label: str
    total_exact: float
    lines: tuple[SensitivityLine, ...]
    notes: list[str]

    def format_full(self) -> str:
        lines = [
            f"SENSITIVITY ANALYSIS — {self.cost_label}",
            f"  Base estimate: ₹{self.total_exact/100_000:.2f}L",
            "",
            "  Impact of each driver changing:",
        ]
        for line in self.lines:
            lines.append(line.format_line())
        if self.notes:
            lines.append("")
            lines.append("  Notes:")
            for n in self.notes:
                lines.append(f"    • {n}")
        return "\n".join(lines)


def compute_sensitivity(cost: TransparencyTriple) -> SensitivityReport:
    """Given a cost TransparencyTriple, produce sensitivity lines.

    For each DerivationLine that has a quantity + rate, compute the
    impact if that rate changes by its implicit variability.
    """
    total = cost.exact_value
    sensitivity_lines: list[SensitivityLine] = []

    # Known variability percentages for common inputs.
    # This is where we translate "steel rate" → "±8% variability".
    known_variability = {
        "concrete": 4.0,
        "steel": 8.0,
        "shuttering": 10.0,
        "labour": 12.0,
        "cement": 6.0,
        "sand": 15.0,
        "brick": 10.0,
        "tile": 20.0,     # Tile choice varies a lot
        "paint": 8.0,
        "door": 20.0,
        "window": 15.0,
        "foundation": 10.0,
    }

    for line in cost.derivation:
        if line.amount <= 0:
            continue

        # Match the derivation line to a known variability by keyword
        variability = _infer_variability(line.label, known_variability)

        # Impact = ±variability × line amount
        impact = line.amount * (variability / 100.0)
        impact_pct_of_total = (line.amount / total) * 100.0 if total > 0 else 0.0

        sensitivity_lines.append(SensitivityLine(
            driver_name=line.label,
            driver_variability_pct=variability,
            impact_on_total_rupees=round(impact, 0),
            impact_pct_of_total=round(impact_pct_of_total, 1),
        ))

    # Sort by impact (biggest drivers first)
    sensitivity_lines.sort(key=lambda sl: sl.impact_on_total_rupees, reverse=True)

    notes = [
        "Biggest drivers are at the top — watch these during construction.",
        "Combined worst case (all drivers at +max simultaneously) is rare.",
        "Contractor margin variability (±6%) applies on top of these.",
    ]

    return SensitivityReport(
        cost_label=cost.label,
        total_exact=total,
        lines=tuple(sensitivity_lines),
        notes=notes,
    )


def _infer_variability(line_label: str, known: dict[str, float]) -> float:
    """Look up variability by keyword matching."""
    label_lower = line_label.lower()
    for keyword, variability in known.items():
        if keyword in label_lower:
            return variability
    return 8.0  # Default if no keyword matches
