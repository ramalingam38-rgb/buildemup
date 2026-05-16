"""
BuildemUp† — Multi-City Rate Providers
========================================

Rate providers for Bangalore, Hyderabad, Mumbai, Pune, Delhi.
Chennai lives in its own module (material_rates_chennai.py).

City cost multipliers vs Chennai baseline (2026 Q2):
  Chennai:    1.00  (baseline)
  Bangalore:  0.96  (slightly lower labour, similar materials)
  Hyderabad:  0.93  (lower land-related costs don't affect construction,
                     but labour is cheaper)
  Mumbai:     1.35  (highest — material premium, labour premium, permits)
  Pune:       1.08  (moderate — near Mumbai supply chain)
  Delhi:      1.15  (higher labour, steel premium, winter construction delays)

Each city has its own:
  - Steel rate (varies with distance from steel plants)
  - Cement rate (varies with distance from cement plants)
  - Labour rate (varies with local market)
  - Contractor margin range (city-specific practice)

Quarterly refresh discipline: all rates are Q2 2026. We update quarterly.

†= placeholder name marker.

KB_VERSION: "MultiCity_2026_Q2_v1"
"""
from __future__ import annotations
from dataclasses import dataclass

from buildemup.utils.rate_provider import RateProvider, MaterialRate


KB_VERSION = "MultiCity_2026_Q2_v2"
# v2 (2026-04-26): Bangalore 0.96→0.98 (parity with Chennai per direct cost
# research), Hyderabad 0.93→0.85 (research shows Hyderabad is genuinely the
# cheapest of the 6 launch cities, not 7% below Chennai but 15% below).
# Delhi multiplier may be understated (AECORD says ~1.40 vs current 1.15)
# but deferred to v0.9.4 session for focused attention.


# ─────────────────────────────────────────────────────────────────────────
# CITY COST MULTIPLIERS (vs Chennai baseline)
# ─────────────────────────────────────────────────────────────────────────
# Sources cross-referenced 2026-04-26:
#   Chennai (baseline): Bluemoon Construction ₹2100-2700 standard residential
#   Bangalore: 8 sources synthesized, midpoint ₹2200 (parity with Chennai)
#     - JSW Homes: same standard band as Chennai
#     - Stylfixx, Architects4Design, NoBroker, Relgrow, KM Infra, Sqft.expert
#     - Metromane: ₹1800-3000 standard
#   Hyderabad: 7 sources, midpoint ₹1900 (15% below Chennai)
#     - Navanaami: "significantly lower than Mumbai/Bangalore"
#     - V Build Infra ₹1500-2500
#     - NoBroker ₹1600-2700
#     - Grihashakti ₹1400-2000 standard
#     - Homebazaar: "lower compared to other cities"
#   Mumbai/Pune/Delhi: unchanged in v2; review queued for v0.9.4
CITY_COST_MULTIPLIER = {
    "chennai":   1.00,
    "bangalore": 0.98,   # v2: was 0.96, +0.02 per direct cost research
    "hyderabad": 0.85,   # v2: was 0.93, -0.08 per direct cost research
    "mumbai":    1.35,   # review queued for v0.9.4 (research suggests ~1.45)
    "pune":      1.08,
    "delhi":     1.15,   # review queued for v0.9.4 (research suggests ~1.40)
}

# Contractor margin ranges by city (from local trade surveys)
CITY_CONTRACTOR_MARGIN_PCT = {
    "chennai":   (8, 18, 12),    # (low, high, default)
    "bangalore": (10, 20, 14),
    "hyderabad": (8, 16, 12),
    "mumbai":    (15, 28, 20),   # Premium contractors
    "pune":      (12, 22, 16),
    "delhi":     (12, 24, 16),
}


# ─────────────────────────────────────────────────────────────────────────
# CITY-SPECIFIC BASE RATES (2026 Q2)
# ─────────────────────────────────────────────────────────────────────────
# Chennai = baseline, other cities scaled from Chennai + local adjustments.
# For materials like cement where distance matters, we use direct rates.

_CHENNAI_BASE_RATES = {
    "rcc": {
        "concrete_M20": {"rate": 6800, "unit": "cum", "var": 4.0,
                          "src": "Chennai RMC Q2 2026"},
        "concrete_M25": {"rate": 7500, "unit": "cum", "var": 4.0,
                          "src": "Chennai RMC Q2 2026"},
        "concrete_M30": {"rate": 8400, "unit": "cum", "var": 4.0,
                          "src": "Chennai RMC Q2 2026"},
        "steel_TMT_Fe500": {"rate": 72000, "unit": "tonne", "var": 8.0,
                             "src": "JSW/TATA Chennai Q2 2026"},
        "shuttering_labour": {"rate": 420, "unit": "sqm", "var": 10.0,
                               "src": "Chennai contractor avg"},
        "structural_labour": {"rate": 2800, "unit": "cum", "var": 12.0,
                               "src": "Chennai contractor avg"},
    },
    "masonry": {
        "brick_red_clay": {"rate": 8.5, "unit": "brick", "var": 10.0,
                            "src": "Chennai brick kilns 2026"},
        "cement_OPC53": {"rate": 395, "unit": "bag", "var": 6.0,
                         "src": "Chennai dealer Q2 2026"},
        "sand_river": {"rate": 2400, "unit": "cum", "var": 15.0,
                       "src": "Chennai sand suppliers 2026"},
        "masonry_labour": {"rate": 380, "unit": "sqm", "var": 12.0,
                           "src": "Chennai contractor avg"},
    },
    "plumbing": {
        "cpvc_pipe_15mm": {"rate": 145, "unit": "rmt", "var": 5.0,
                            "src": "Chennai plumbing dealer 2026"},
        "cpvc_pipe_20mm": {"rate": 210, "unit": "rmt", "var": 5.0,
                            "src": "Chennai plumbing dealer 2026"},
        "pvc_drain_110mm": {"rate": 320, "unit": "rmt", "var": 5.0,
                             "src": "Chennai plumbing dealer 2026"},
        "bathroom_set_jaquar_continental": {"rate": 30000, "unit": "bathroom",
                                             "var": 15.0,
                                             "src": "Jaquar 2026"},
        "kitchen_sink_set": {"rate": 8500, "unit": "set", "var": 10.0,
                             "src": "Hindware/Jaquar 2026"},
        "plumbing_labour": {"rate": 850, "unit": "point", "var": 10.0,
                            "src": "Chennai contractor avg"},
    },
    "electrical": {
        "wiring_per_point_basic": {"rate": 750, "unit": "point", "var": 12.0,
                                    "src": "Chennai contractor 2026"},
        "wiring_per_point_AC": {"rate": 2200, "unit": "point", "var": 10.0,
                                 "src": "Chennai contractor 2026"},
        "MCB_distribution_board": {"rate": 4500, "unit": "board", "var": 8.0,
                                    "src": "Havells dealer 2026"},
        "electrical_labour": {"rate": 85, "unit": "sqft", "var": 10.0,
                              "src": "Chennai contractor avg"},
    },
    "finish": {
        "vitrified_tile_mid": {"rate": 140, "unit": "sqft", "var": 20.0,
                                "src": "Chennai tile dealer + laying"},
        "wall_paint_emulsion": {"rate": 22, "unit": "sqft", "var": 8.0,
                                 "src": "Asian Paints + labour 2026"},
        "door_flush_main": {"rate": 45000, "unit": "door", "var": 20.0,
                             "src": "Chennai carpentry 2026"},
        "door_flush_internal": {"rate": 12000, "unit": "door", "var": 15.0,
                                 "src": "Chennai carpentry 2026"},
        "window_aluminium": {"rate": 850, "unit": "sqft", "var": 15.0,
                              "src": "Chennai aluminium fabricator 2026"},
        "waterproofing_bath": {"rate": 180, "unit": "sqft", "var": 8.0,
                                "src": "Pidilite Chennai 2026"},
    },
}


def _build_city_rates(city: str) -> dict:
    """Generate city rate catalog by scaling Chennai baseline + local adjustments."""
    mult = CITY_COST_MULTIPLIER.get(city, 1.0)
    rates = {}
    for category, items in _CHENNAI_BASE_RATES.items():
        rates[category] = {}
        for key, data in items.items():
            scaled_rate = data["rate"] * mult
            rates[category][key] = MaterialRate(
                name=f"{key} ({city.title()})",
                rate=round(scaled_rate, 2),
                unit=data["unit"],
                source=data["src"].replace("Chennai", city.title()),
                variability_pct=data["var"],
            )
    return rates


# ─────────────────────────────────────────────────────────────────────────
# CITY-SPECIFIC OVERRIDES (where simple scaling isn't accurate)
# ─────────────────────────────────────────────────────────────────────────
# Mumbai steel rates are higher due to proximity to JSW Vijayanagar/Maharashtra plants
# and premium demand. We override specific rates where local data differs.
_CITY_OVERRIDES = {
    "mumbai": {
        "rcc": {
            "steel_TMT_Fe500": MaterialRate(
                name="TMT bars Fe500 (Mumbai)",
                rate=78000,   # Higher than Chennai base 72000
                unit="tonne",
                source="JSW Mumbai dealer Q2 2026",
                variability_pct=8.0,
                notes="Mumbai steel carries ~8% premium vs south India",
            ),
            "structural_labour": MaterialRate(
                name="RCC casting labour (Mumbai)",
                rate=4200,   # Much higher than Chennai 2800
                unit="cum",
                source="Mumbai contractor avg 2026",
                variability_pct=12.0,
                notes="Mumbai construction labour significantly costlier",
            ),
        },
        "masonry": {
            "masonry_labour": MaterialRate(
                name="Masonry labour (Mumbai)",
                rate=580,   # Higher than Chennai 380
                unit="sqm",
                source="Mumbai contractor avg 2026",
                variability_pct=12.0,
            ),
        },
    },
    "delhi": {
        "rcc": {
            "concrete_M25": MaterialRate(
                name="Ready-mix concrete M25 (Delhi)",
                rate=8200,   # Delhi premium vs Chennai 7500
                unit="cum",
                source="Delhi RMC Q2 2026",
                variability_pct=5.0,
                notes="Winter slowdown (Nov-Jan) affects supply",
            ),
        },
    },
    "bangalore": {
        "masonry": {
            "sand_river": MaterialRate(
                name="M-sand (Bangalore — river sand banned)",
                rate=2100,
                unit="cum",
                source="Bangalore M-sand 2026",
                variability_pct=12.0,
                notes="Karnataka river sand banned; use M-sand (manufactured)",
            ),
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────
# GENERIC CITY RATE PROVIDER CLASS
# ─────────────────────────────────────────────────────────────────────────
class _CityRateProvider(RateProvider):
    """Generic RateProvider that takes a city name and looks up rates."""

    def __init__(self, city: str):
        if city not in CITY_COST_MULTIPLIER:
            raise KeyError(
                f"Unsupported city: {city}. "
                f"Supported: {list(CITY_COST_MULTIPLIER.keys())}"
            )
        self._city = city
        self._rates = _build_city_rates(city)
        # Apply local overrides
        for cat, items in _CITY_OVERRIDES.get(city, {}).items():
            for key, rate_obj in items.items():
                self._rates[cat][key] = rate_obj

    @property
    def city_name(self) -> str:
        return self._city.title()

    @property
    def kb_version(self) -> str:
        return f"{self._city.title()}_2026_Q2_v1"

    def get_rate(self, category: str, key: str) -> MaterialRate:
        if category not in self._rates:
            raise KeyError(f"Unknown category: {category}")
        if key not in self._rates[category]:
            raise KeyError(f"Unknown key '{key}' in '{category}'")
        return self._rates[category][key]

    def contractor_margin_range_pct(self) -> tuple[float, float]:
        low, high, _ = CITY_CONTRACTOR_MARGIN_PCT[self._city]
        return (float(low), float(high))

    def contractor_margin_default_pct(self) -> float:
        _, _, default = CITY_CONTRACTOR_MARGIN_PCT[self._city]
        return float(default)


# ─────────────────────────────────────────────────────────────────────────
# PUBLIC FACTORY FUNCTION
# ─────────────────────────────────────────────────────────────────────────
def get_rate_provider(city: str) -> RateProvider:
    """Get a rate provider for any supported city.

    Usage:
        provider = get_rate_provider("mumbai")
        steel_rate = provider.get_rate("rcc", "steel_TMT_Fe500")

    Supported cities: chennai, bangalore, hyderabad, mumbai, pune, delhi.
    """
    city_key = city.lower().strip()
    # Chennai uses the more detailed standalone provider
    if city_key == "chennai":
        from buildemup.kb.material_rates_chennai import ChennaiRateProvider
        return ChennaiRateProvider()
    return _CityRateProvider(city_key)


# Convenience instances
class BangaloreRateProvider(_CityRateProvider):
    def __init__(self): super().__init__("bangalore")


class HyderabadRateProvider(_CityRateProvider):
    def __init__(self): super().__init__("hyderabad")


class MumbaiRateProvider(_CityRateProvider):
    def __init__(self): super().__init__("mumbai")


class PuneRateProvider(_CityRateProvider):
    def __init__(self): super().__init__("pune")


class DelhiRateProvider(_CityRateProvider):
    def __init__(self): super().__init__("delhi")
