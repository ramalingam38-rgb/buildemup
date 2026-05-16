"""Tier-1 guardrail tests for C5+ usage of PlotAnalysis.

Per SPEC v0.5 LOCKED § 7. SKIPPED at module level until c05/ exists,
to avoid building features without consumers (Pattern B). Activated
automatically when c05/ ships.

These tests enforce that C5 onward consumes PlotAnalysis rather than
re-deriving from raw plot — the "single source of truth" invariant
that motivates C4.
"""
from __future__ import annotations

import importlib.util

import pytest

# Module-level skip: no point running these until C5 is built.
if importlib.util.find_spec("buildemup.components.c05") is None:
    pytest.skip(
        "C5 not yet implemented — guardrail tests deferred. "
        "Activates automatically when buildemup/components/c05/ exists.",
        allow_module_level=True,
    )


def test_c5_does_not_import_plot_directly():
    """C5 source files MUST NOT import domain.plot.Plot directly.

    Negative-import test: C5 must consume PlotAnalysis (C4's output),
    not raw Plot.
    """
    import pkgutil
    import buildemup.components.c05 as c05_pkg
    forbidden = {"from buildemup.domain.plot import", "from buildemup.domain import plot"}
    offenders: list[str] = []
    for mod_info in pkgutil.walk_packages(c05_pkg.__path__, prefix="buildemup.components.c05."):
        spec = importlib.util.find_spec(mod_info.name)
        if spec is None or spec.origin is None:
            continue
        with open(spec.origin) as f:
            src = f.read()
        for pat in forbidden:
            if pat in src:
                offenders.append(f"{mod_info.name} contains '{pat}'")
    assert not offenders, "C5 must not import Plot directly:\n" + "\n".join(offenders)


def test_stub_c5_consumer_reads_plot_analysis_without_recomputation():
    """Smoke-test: a C5-shaped consumer can read everything it needs from
    PlotAnalysis without touching plot.* directly."""
    import time
    from buildemup.components.c04 import derive
    from buildemup.tests.validation._c4_fixtures import chennai_30x40, make_brief

    pa = derive(make_brief(chennai_30x40()), now=time.time())

    # A stub C5 consumer pattern: reads only PlotAnalysis fields.
    def stub_c5(plot_analysis) -> dict:
        return {
            "tier": plot_analysis.tier.value,
            "climate": plot_analysis.climate_zone.value,
            "open_facades": plot_analysis.neighbour_context.raw_facade_count,
            "soil_kpa": plot_analysis.soil_estimate.bearing_capacity_kpa,
            "summer_alt": plot_analysis.sun_path.summer_solstice_noon_alt,
        }
    bundle = stub_c5(pa)
    assert bundle["tier"] == "T1"
    assert bundle["climate"] == "warm_humid"
    assert bundle["open_facades"] == 4
