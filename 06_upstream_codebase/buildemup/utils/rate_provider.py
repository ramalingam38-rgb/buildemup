"""
BuildemUp† — Rate Provider Abstraction
========================================

Abstract interface for material rate lookup. Enables:
  - Swapping Chennai rates for Bangalore/Mumbai/etc. without code changes
  - Testing with mock rates
  - Versioning rates by quarter/year

The concrete implementation for Chennai is in material_rates_chennai.
Future: material_rates_bangalore, material_rates_mumbai, etc.

†= placeholder name marker.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialRate:
    """One material rate with min/max/median + brand/grade specificity.

    rate = median/typical value (what we use for point estimates).
    rate_min = low end (budget contractor, bulk purchase, favourable timing).
    rate_max = high end (premium contractor, small qty, unfavourable timing).
    variability_pct = derived if not provided: (max-min)/(2×median) × 100.

    v0.4: brand/grade/IS-code/supplier added so output can become
    user-actionable BOM ('take this list to your supplier'):
        MaterialRate(
            name="Cement",
            brand="Ultratech",
            grade="OPC 53",
            is_code="IS 12269",
            supplier_type="dealer",
            rate=395, unit="bag", source="Chennai dealer Q2 2026",
        )
    All these fields default to empty for backwards compat with simpler usage.
    """
    name: str
    rate: float                              # Median/typical value
    unit: str
    source: str
    variability_pct: float = 5.0
    notes: str = ""
    rate_min: float | None = None
    rate_max: float | None = None
    # v0.4: brand/grade/IS-code/supplier for user-actionable BOM
    brand: str = ""                          # e.g., "Ultratech", "JSW", "Tata"
    grade: str = ""                          # e.g., "OPC 53", "Fe500D", "M25"
    is_code: str = ""                        # e.g., "IS 12269", "IS 1786"
    supplier_type: str = ""                  # e.g., "dealer", "RMC plant", "fabricator"

    def __post_init__(self):
        if self.rate_min is None:
            derived_min = self.rate * (1 - self.variability_pct / 100.0)
            object.__setattr__(self, 'rate_min', round(derived_min, 2))
        if self.rate_max is None:
            derived_max = self.rate * (1 + self.variability_pct / 100.0)
            object.__setattr__(self, 'rate_max', round(derived_max, 2))

    @property
    def actual_variability_pct(self) -> float:
        if self.rate_min is None or self.rate_max is None:
            return self.variability_pct
        spread = (self.rate_max - self.rate_min) / 2.0
        return round((spread / self.rate) * 100.0, 1) if self.rate else 0.0

    @property
    def display_name(self) -> str:
        """User-facing name like 'Ultratech OPC 53 (Cement)'."""
        if self.brand and self.grade:
            return f"{self.brand} {self.grade}"
        if self.brand:
            return f"{self.brand} {self.name}"
        if self.grade:
            return f"{self.name} {self.grade}"
        return self.name

    def format_bom_line(self, quantity: float) -> str:
        """Format as a BOM line like 'Ultratech OPC 53 — 480 bags — ₹395 — ₹1,89,600'."""
        total = quantity * self.rate
        is_code_part = f" ({self.is_code})" if self.is_code else ""
        return (
            f"{self.display_name}{is_code_part} — "
            f"{quantity:.0f} {self.unit} — "
            f"₹{self.rate:,.0f}/{self.unit} — "
            f"₹{total:,.0f}"
        )


class RateProvider(ABC):
    """Abstract base for city-specific rate lookup."""

    @property
    @abstractmethod
    def city_name(self) -> str:
        """Human-readable city name."""
        ...

    @property
    @abstractmethod
    def kb_version(self) -> str:
        """Version string, e.g., 'Chennai_2026_Q2_v1'."""
        ...

    @abstractmethod
    def get_rate(self, category: str, key: str) -> MaterialRate:
        """Look up a material rate.

        Args:
            category: 'rcc', 'masonry', 'plumbing', 'electrical', 'finish'
            key: specific material key within the category

        Returns:
            MaterialRate object with the current price and source.

        Raises:
            KeyError if category or key not found.
        """
        ...

    @abstractmethod
    def contractor_margin_range_pct(self) -> tuple[float, float]:
        """Return (low_pct, high_pct) typical contractor margin for this city."""
        ...

    @abstractmethod
    def contractor_margin_default_pct(self) -> float:
        """Default contractor margin to use in our estimates."""
        ...
