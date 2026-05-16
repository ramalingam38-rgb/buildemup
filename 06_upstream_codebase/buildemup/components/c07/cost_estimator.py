"""
BuildemUp† — Component 7d: Cost Estimator
===========================================

Single responsibility: calculate structural cost using the
RateProvider abstraction.

This uses dependency injection — give it any RateProvider (Chennai,
Bangalore, mock) and it produces a properly-sourced TransparencyTriple.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass

from buildemup.utils.rate_provider import RateProvider
from buildemup.utils.transparency import (
    TransparencyTriple,
    DerivationLine,
    Confidence,
)
from buildemup.components.c07.structural_sizer import SizedStructure
from buildemup.components.c07.foundation_engine import FoundationDesign


class StructuralCostEstimator:
    """Calculates structural cost via RateProvider."""

    def __init__(self, rate_provider: RateProvider):
        """Initialize with a rate provider.

        Args:
            rate_provider: concrete implementation (e.g., ChennaiRateProvider)
        """
        self.provider = rate_provider

    def estimate(
        self,
        structure: SizedStructure,
        foundation: FoundationDesign,
    ) -> TransparencyTriple:
        """Estimate structural cost.

        Returns a TransparencyTriple with range, exact, derivation, confidence.
        """
        # Frame cost (columns, beams, slabs)
        frame_concrete_cum = structure.total_concrete_cum - foundation.total_concrete_cum
        if frame_concrete_cum < 0:
            frame_concrete_cum = structure.total_concrete_cum  # Safety
        frame_steel_kg = structure.total_steel_tonnes * 1000 - foundation.total_steel_kg
        if frame_steel_kg < 0:
            frame_steel_kg = structure.total_steel_tonnes * 1000

        # Rates from the provider (city-agnostic)
        concrete_rate = self.provider.get_rate("rcc", f"concrete_{structure.concrete_grade}")
        steel_rate = self.provider.get_rate("rcc", "steel_TMT_Fe500")
        shutter_rate = self.provider.get_rate("rcc", "shuttering_labour")
        labour_rate = self.provider.get_rate("rcc", "structural_labour")

        # Frame cost breakdown
        frame_concrete_cost = frame_concrete_cum * concrete_rate.rate
        frame_steel_cost = (frame_steel_kg / 1000) * steel_rate.rate

        # Shuttering: ~12 sqm per cum concrete typical for residential
        shutter_area = structure.total_concrete_cum * 12.0
        shutter_cost = shutter_area * shutter_rate.rate

        # Labour
        labour_cost = structure.total_concrete_cum * labour_rate.rate

        # Foundation cost (separately tracked)
        foundation_concrete_cost = foundation.total_concrete_cum * concrete_rate.rate
        foundation_steel_cost = (foundation.total_steel_kg / 1000) * steel_rate.rate
        foundation_labour_cost = foundation.total_concrete_cum * labour_rate.rate

        total_cost = (
            frame_concrete_cost + frame_steel_cost +
            shutter_cost + labour_cost +
            foundation_concrete_cost + foundation_steel_cost +
            foundation_labour_cost
        )

        # v0.4: use brand/grade in labels where available so user sees
        # 'Ramco or Ultratech OPC 53 (IS 12269)' instead of generic 'cement'
        concrete_label = f"Frame concrete ({structure.concrete_grade})"
        if concrete_rate.brand or concrete_rate.is_code:
            parts = [structure.concrete_grade]
            if concrete_rate.brand:
                parts.insert(0, concrete_rate.brand)
            if concrete_rate.is_code:
                parts.append(f"per {concrete_rate.is_code}")
            concrete_label = f"Frame concrete — {' '.join(parts)}"

        steel_label = "Frame steel (TMT Fe500)"
        if steel_rate.brand or steel_rate.grade or steel_rate.is_code:
            parts = []
            if steel_rate.brand:
                parts.append(steel_rate.brand)
            if steel_rate.grade:
                parts.append(steel_rate.grade)
            if steel_rate.is_code:
                parts.append(f"per {steel_rate.is_code}")
            steel_label = f"Frame steel — {' '.join(parts)}"

        derivation = [
            DerivationLine(
                label=concrete_label,
                quantity=round(frame_concrete_cum, 1),
                unit="cum",
                rate=concrete_rate.rate,
                rate_unit=f"₹/{concrete_rate.unit}",
                amount=frame_concrete_cost,
                source=concrete_rate.source,
            ),
            DerivationLine(
                label=steel_label,
                quantity=round(frame_steel_kg / 1000, 2),
                unit="tonne",
                rate=steel_rate.rate,
                rate_unit=f"₹/{steel_rate.unit}",
                amount=frame_steel_cost,
                source=steel_rate.source,
            ),
            DerivationLine(
                label="Shuttering + formwork",
                quantity=round(shutter_area, 0),
                unit="sqm",
                rate=shutter_rate.rate,
                rate_unit=f"₹/{shutter_rate.unit}",
                amount=shutter_cost,
                source=shutter_rate.source,
            ),
            DerivationLine(
                label="RCC casting labour",
                quantity=round(structure.total_concrete_cum, 1),
                unit="cum",
                rate=labour_rate.rate,
                rate_unit=f"₹/{labour_rate.unit}",
                amount=labour_cost,
                source=labour_rate.source,
            ),
            DerivationLine(
                label=f"Foundation ({foundation.type}) — concrete",
                quantity=round(foundation.total_concrete_cum, 1),
                unit="cum",
                rate=concrete_rate.rate,
                rate_unit=f"₹/{concrete_rate.unit}",
                amount=foundation_concrete_cost,
                source=concrete_rate.source,
            ),
            DerivationLine(
                label=f"Foundation ({foundation.type}) — steel",
                quantity=round(foundation.total_steel_kg / 1000, 2),
                unit="tonne",
                rate=steel_rate.rate,
                rate_unit=f"₹/{steel_rate.unit}",
                amount=foundation_steel_cost,
                source=steel_rate.source,
            ),
            DerivationLine(
                label="Foundation labour",
                amount=foundation_labour_cost,
                source=labour_rate.source,
            ),
        ]

        return TransparencyTriple(
            label="Structural cost (RCC frame + foundation)",
            exact_value=total_cost,
            unit="₹",
            uncertainty_pct=8.0,  # Material ±5%, labour ±10%, blended ±8%
            confidence=Confidence.HIGH,
            derivation=derivation,
            notes=[
                "Steel rate fluctuates ±8% with international iron ore prices",
                "Labour rate varies ±10% by contractor scale",
                "Concrete rate stable ±4% from major RMC suppliers",
                "Excludes contractor margin (typically "
                f"+{self.provider.contractor_margin_range_pct()[0]:.0f}% "
                f"to +{self.provider.contractor_margin_range_pct()[1]:.0f}%)",
                f"Rates valid for {self.provider.city_name} "
                f"(KB version: {self.provider.kb_version})",
            ],
        )
