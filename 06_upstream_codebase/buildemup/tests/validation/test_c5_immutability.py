"""Validation tests for C5 dataclass immutability + MappingProxyType wrappers.

Per C5 SPEC v0.9 LOCKED § 7 (test plan).
"""
from __future__ import annotations

import dataclasses
from types import MappingProxyType

import pytest

from buildemup.components.c05 import (
    LOW_CONFIDENCE_THRESHOLD,
    MIN_CANDIDATE_ADMISSION_THRESHOLD,
    select_topology,
)
from buildemup.components.c05.schema import (
    CorridorSketch,
    ScoreBreakdownEntry,
    TopologyCandidate,
    TopologyKind,
    TopologyPriors,
    TopologyProvenance,
)
from buildemup.tests.validation._c5_fixtures import (
    bangalore_40x60,
    chennai_30x40,
    make_plot_analysis,
    medium_brief,
)


# ─── Frozen dataclass invariants ──────────────────────────────────────────


def test_topology_candidate_is_frozen():
    """TopologyCandidate must be a frozen dataclass."""
    assert dataclasses.is_dataclass(TopologyCandidate)
    pa = make_plot_analysis(chennai_30x40())
    candidate = select_topology(pa, medium_brief())[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.score = 0.5                                # type: ignore[misc]


def test_corridor_sketch_is_frozen():
    pa = make_plot_analysis(chennai_30x40())
    candidate = select_topology(pa, medium_brief())[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.corridor_sketch.nominal_width_m = 2.0      # type: ignore[misc]


def test_score_breakdown_entry_is_frozen():
    pa = make_plot_analysis(chennai_30x40())
    candidate = select_topology(pa, medium_brief())[0]
    entry = next(iter(candidate.score_breakdown.values()))
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.raw = 0.5                                       # type: ignore[misc]


def test_topology_provenance_is_frozen():
    pa = make_plot_analysis(chennai_30x40())
    candidate = select_topology(pa, medium_brief())[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.provenance.derived_at = 0.0                 # type: ignore[misc]


def test_topology_priors_is_frozen():
    p = TopologyPriors(strip=1.0, central_spine=1.0, l_shape=0.7, courtyard=0.7)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.strip = 0.5                                          # type: ignore[misc]


# ─── MappingProxyType invariants ──────────────────────────────────────────


def test_score_breakdown_is_mappingproxytype():
    """SC-1 immutability — consumers can't mutate the breakdown dict."""
    pa = make_plot_analysis(bangalore_40x60())
    candidate = select_topology(pa, medium_brief())[0]
    assert isinstance(candidate.score_breakdown, MappingProxyType)
    with pytest.raises(TypeError):
        candidate.score_breakdown["new_criterion"] = ScoreBreakdownEntry(
            raw=0.5, weight=0.1, contribution_raw=0.05, contribution_final=0.0425
        )                                                     # type: ignore[index]


def test_zone_bands_is_mappingproxytype():
    pa = make_plot_analysis(bangalore_40x60())
    candidate = select_topology(pa, medium_brief())[0]
    assert isinstance(candidate.zone_bands, MappingProxyType)
    with pytest.raises(TypeError):
        from buildemup.components.c05.schema import ZoneBand
        from buildemup.domain.envelope import PlotOrientation
        candidate.zone_bands[ZoneBand.PUBLIC] = PlotOrientation.NORTH  # type: ignore[index]


def test_branch_weights_is_mappingproxytype():
    pa = make_plot_analysis(bangalore_40x60())
    candidate = select_topology(pa, medium_brief())[0]
    assert isinstance(candidate.provenance.branch_weights, MappingProxyType)
    with pytest.raises(TypeError):
        candidate.provenance.branch_weights["new_branch"] = 0.5    # type: ignore[index]


def test_top_contributors_is_tuple():
    """top_contributors is a tuple — frozen by Python's tuple immutability."""
    pa = make_plot_analysis(bangalore_40x60())
    candidate = select_topology(pa, medium_brief())[0]
    assert isinstance(candidate.top_contributors, tuple)


# ─── Named-constants invariants (v0.9 § 14.1 #7) ──────────────────────────


def test_low_confidence_uses_named_constant():
    """v0.9 § 14.1: select.py source must not contain 0.30 inline literal
    outside the constant declarations.

    Inspects the source text to ensure no stray 0.30 literal was reintroduced.
    """
    import importlib.util
    spec = importlib.util.find_spec("buildemup.components.c05.select")
    assert spec is not None and spec.origin is not None
    with open(spec.origin) as f:
        src = f.read()
    # Allow 0.30 ONLY in the constant declarations + comments. We strip out
    # known-allowed lines and check no `0.30` literal remains.
    lines = src.splitlines()
    offenders = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Allow constant declarations
        if "LOW_CONFIDENCE_THRESHOLD: float = 0.30" in line:
            continue
        if "MIN_CANDIDATE_ADMISSION_THRESHOLD: float = 0.30" in line:
            continue
        # Allow comments / docstrings (lines that are entirely or mostly
        # comments/docstrings)
        if stripped.startswith("#"):
            continue
        # Detect bare 0.30 in code
        if "0.30" in line and "0.300" not in line:
            offenders.append(f"L{i}: {line}")
    assert not offenders, "0.30 literal in select.py outside constants:\n" + "\n".join(offenders)


def test_admission_threshold_uses_named_constant():
    """Same check, focused on the secondary admission filter."""
    # Already covered by test_low_confidence_uses_named_constant since both
    # constants are in the same file. Verify both constants exist + are 0.30.
    assert LOW_CONFIDENCE_THRESHOLD == 0.30
    assert MIN_CANDIDATE_ADMISSION_THRESHOLD == 0.30


def test_thresholds_have_distinct_names_even_when_equal():
    """v0.9 § 14.1: two constants are declared separately (not aliases),
    so future divergence is a single-line edit."""
    import buildemup.components.c05.select as select_mod
    # They must be distinct module-level attributes (not the same object).
    # In Python, immutable floats CAN be cached/interned, so identity check
    # would be unreliable. We instead check both names exist as separate
    # module-level bindings.
    assert hasattr(select_mod, "LOW_CONFIDENCE_THRESHOLD")
    assert hasattr(select_mod, "MIN_CANDIDATE_ADMISSION_THRESHOLD")
    # And that the source explicitly assigns each (separate declarations).
    import importlib.util
    spec = importlib.util.find_spec("buildemup.components.c05.select")
    assert spec is not None and spec.origin is not None
    with open(spec.origin) as f:
        src = f.read()
    assert "LOW_CONFIDENCE_THRESHOLD: float = 0.30" in src
    assert "MIN_CANDIDATE_ADMISSION_THRESHOLD: float = 0.30" in src


# ─── Cross-immutability via tuple-of-candidates ─────────────────────────


def test_select_topology_returns_a_tuple():
    pa = make_plot_analysis(chennai_30x40())
    result = select_topology(pa, medium_brief())
    assert isinstance(result, tuple)
