"""
v0.4 trust-control tests.

Tests the new trust controls added in v0.4:
  - Severe regularity refusal (engine refuses, doesn't just warn)
  - SCWB heuristic clearly labeled as heuristic
  - KB versions pinned per output
  - Trace ID generated per output
  - Wind/seismic load comparison present
  - Confidence definitions visible in explain()
  - WHAT WE CHECK / WHAT WE DON'T CHECK section visible
  - Structural sensitivity present
  - Console JSON suppressed by default
"""
import sys
import os
import io
import contextlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.components.c07_structural_grid import (
    StructuralGridEngine,
    StructuralGridInput,
)
from buildemup.utils.errors import EnvelopeTooIrregularError, format_for_user
from buildemup.utils.logging import (
    new_trace_id, get_logger, summarize_trace, clear_trace_store,
)


# ─── Severe regularity refusal ───────────────────────────────────────────
def test_severe_regularity_is_refused():
    """A 40% re-entrant corner (>30% threshold) must be refused."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=4.0,  # 40% of 10m — severe
        re_entrant_corner_y_m=4.0,
    )
    engine = StructuralGridEngine()
    try:
        engine.execute(inp)
        assert False, "Expected refusal for 40% re-entrant corner"
    except EnvelopeTooIrregularError as e:
        assert "irregular" in str(e).lower() or "severe" in str(e).lower()
        assert e.suggested_action is not None
        assert "structural engineer" in e.suggested_action.lower()
        print(f"PASS severe re-entrant corner refused gracefully")


def test_moderate_regularity_warns_but_proceeds():
    """A 20% re-entrant corner (between 15% and 30%) warns but proceeds."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
        re_entrant_corner_x_m=2.0,  # 20% — moderate
        re_entrant_corner_y_m=2.0,
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)  # Should NOT raise
    assert result.structure.regularity.severity == "MODERATELY_IRREGULAR"
    assert result.structure.regularity.requires_detailed_analysis is True
    assert result.structure.regularity.requires_refusal is False
    print(f"PASS moderate corner warns + proceeds:")
    print(f"  Severity: {result.structure.regularity.severity}")
    print(f"  Reliability: {result.structure.seismic_reliability}")


def test_severe_aspect_ratio_is_refused():
    """A 7:1 aspect ratio plot must be refused."""
    inp = StructuralGridInput(
        envelope_width_m=5.0, envelope_depth_m=36.0,  # 7.2:1
        floors_above_ground=1, city="mumbai", seismic_zone="III",
    )
    engine = StructuralGridEngine()
    try:
        engine.execute(inp)
        assert False, "Expected refusal for 7:1 aspect ratio"
    except EnvelopeTooIrregularError:
        print(f"PASS severe aspect ratio (7:1) refused")


# ─── SCWB heuristic naming ───────────────────────────────────────────────
def test_scwb_check_is_labeled_heuristic():
    """SCWB output must include 'heuristic' label and disclaimer."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="mumbai", seismic_zone="III",
    )
    result = StructuralGridEngine().execute(inp)
    scwb = result.structure.scwb_heuristic
    assert scwb.get("is_heuristic") is True
    assert "disclaimer" in scwb
    assert "heuristic" in scwb["disclaimer"].lower()
    assert "moment capacity" in scwb["disclaimer"].lower()
    print(f"PASS SCWB clearly labeled as heuristic")


# ─── KB version pinning ──────────────────────────────────────────────────
def test_kb_versions_pinned_per_output():
    """Every output must carry the KB versions used to produce it."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.kb_versions
    # Must include the core KBs used
    assert "rcc_design_rules" in result.kb_versions
    assert "soil_foundation_rules" in result.kb_versions
    assert "load_estimation" in result.kb_versions
    assert "seismic_detailing" in result.kb_versions
    # Versions should be properly formatted strings
    for module, version in result.kb_versions.items():
        assert isinstance(version, str)
        assert len(version) > 0
    print(f"PASS KB versions pinned ({len(result.kb_versions)} modules)")
    for k, v in sorted(result.kb_versions.items())[:3]:
        print(f"  {k}: {v}")


def test_pile_kb_version_added_when_pile_used():
    """Pile foundation KB version should appear only when pile is used."""
    inp_pile = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="kolkata", seismic_zone="III",
    )
    result_pile = StructuralGridEngine().execute(inp_pile)
    assert result_pile.foundation.type == "pile"
    assert "pile_foundation" in result_pile.kb_versions

    inp_iso = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result_iso = StructuralGridEngine().execute(inp_iso)
    assert "pile_foundation" not in result_iso.kb_versions
    print(f"PASS pile_foundation KB version added only for pile foundations")


# ─── Trace ID ────────────────────────────────────────────────────────────
def test_trace_id_generated_per_execute():
    """Each execute() must generate a unique trace_id."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    result1 = engine.execute(inp)
    result2 = engine.execute(inp)
    assert result1.trace_id
    assert result2.trace_id
    assert result1.trace_id != result2.trace_id
    print(f"PASS each execute generates unique trace_id:")
    print(f"  Run 1: {result1.trace_id}")
    print(f"  Run 2: {result2.trace_id}")


def test_summarize_trace_returns_event_history():
    """summarize_trace should return chronological events for a trace."""
    clear_trace_store()
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    summary = summarize_trace(result.trace_id)
    assert result.trace_id in summary
    assert "execute_start" in summary
    assert "execute_complete" in summary
    print(f"PASS summarize_trace produces narrative")


# ─── Wind/seismic load comparison ────────────────────────────────────────
def test_lateral_load_comparison_present():
    """Every output must include the wind vs seismic comparison."""
    inp = StructuralGridInput(
        envelope_width_m=10.0, envelope_depth_m=10.0,
        floors_above_ground=2, city="mumbai", seismic_zone="III",
    )
    result = StructuralGridEngine().execute(inp)
    cmp = result.structure.lateral_load_comparison
    assert cmp is not None
    assert cmp["governing_load"] in ("wind", "seismic")
    assert cmp["wind_force_kn"] > 0
    assert cmp["seismic_force_kn"] > 0
    print(f"PASS lateral comparison: {cmp['governing_load']} governs "
          f"(wind={cmp['wind_force_kn']:.0f} kN, "
          f"seismic={cmp['seismic_force_kn']:.0f} kN)")


# ─── Confidence definitions visible ──────────────────────────────────────
def test_confidence_definitions_in_explain():
    """explain() must show what HIGH/MEDIUM/LOW mean."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    result = engine.execute(inp)
    explanation = engine.explain(inp, result)
    assert "Well-constrained:" in explanation
    assert "Regional typical:" in explanation
    assert "Depends on your choices:" in explanation
    assert "Indian codes" in explanation  # Well-constrained definition reference
    # v0.5: confidence levels must NOT use HIGH/MEDIUM/LOW words in legend
    # (those are misleading per v0.4 review)
    assert "HIGH:" not in explanation
    assert "MEDIUM:" not in explanation
    assert "LOW:" not in explanation
    # v0.5: must disclose what confidence is NOT about
    assert "engineering correctness" in explanation.lower()
    print(f"PASS v0.5 confidence labels (descriptive) visible in explain()")


# ─── WHAT WE CHECK / WE DON'T CHECK section ──────────────────────────────
def test_what_we_check_section_visible():
    """explain() must show explicit boundary disclosure."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    assert "WHAT THIS ESTIMATE COVERS" in explanation
    assert "WE DO NOT CHECK" in explanation
    assert "frame analysis" in explanation.lower() or "P-M" in explanation
    print(f"PASS WHAT WE CHECK / DON'T CHECK section present")


# ─── Prominent banner at TOP ─────────────────────────────────────────────
def test_preliminary_banner_at_top():
    """The strengthened v0.5 banner must appear in the first ~15 lines."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    engine = StructuralGridEngine()
    explanation = engine.explain(inp, engine.execute(inp))
    first_lines = explanation.split("\n")[:15]
    first_block = "\n".join(first_lines)
    # v0.5 stronger language
    assert "RULE-BASED HEURISTIC" in first_block
    assert "NOT structural design" in first_block
    assert "LICENSED STRUCTURAL ENGINEER" in first_block
    print(f"PASS v0.5 strengthened banner at TOP of explain")


# ─── Structural sensitivity present ──────────────────────────────────────
def test_structural_sensitivity_present():
    """Output must include structural sensitivity (soil + load)."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    assert result.structural_sensitivity is not None
    assert len(result.structural_sensitivity.scenarios) >= 2
    drivers = [s.driver_name for s in result.structural_sensitivity.scenarios]
    assert any("soil" in d.lower() for d in drivers)
    assert any("load" in d.lower() for d in drivers)
    print(f"PASS structural sensitivity present:")
    for s in result.structural_sensitivity.scenarios:
        print(f"  {s.driver_name}: {s.scenario_label}")


# ─── Console JSON suppressed by default ──────────────────────────────────
def test_no_json_logs_in_console_by_default():
    """Running execute() should NOT emit JSON log lines to stdout."""
    inp = StructuralGridInput(
        envelope_width_m=8.0, envelope_depth_m=10.0,
        floors_above_ground=1, city="chennai", seismic_zone="II",
    )
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        StructuralGridEngine().execute(inp)
    output = captured.getvalue()
    # Check no JSON log lines (recognisable pattern '"event":')
    assert '"event":' not in output, \
        f"JSON logs leaked to stdout: {output[:200]}"
    print(f"PASS console quiet by default (no JSON log spam)")


# ─── format_for_user works for typed and untyped errors ──────────────────
def test_format_for_user_handles_typed_errors():
    """format_for_user must produce user-safe dicts for typed errors."""
    err = EnvelopeTooIrregularError(
        technical_message="aspect 7.2",
        user_message="Your plot is too elongated.",
        suggested_action="Engage structural engineer.",
    )
    formatted = format_for_user(err)
    assert formatted["title"] == "Your plot shape needs an engineer"
    assert formatted["category"] == "user_actionable"
    assert formatted["is_user_facing_safe"] is True
    print(f"PASS format_for_user works for typed errors")


def test_format_for_user_handles_unexpected_errors():
    """format_for_user must NOT leak internals for unexpected errors."""
    err = ValueError("internal stack trace details")
    formatted = format_for_user(err)
    assert formatted["category"] == "internal"
    assert formatted["is_user_facing_safe"] is False
    # User message must NOT contain the technical detail
    assert "stack trace" not in formatted["message"]
    assert ("us, not you" in formatted["message"].lower()
            or "unexpected issue" in formatted["message"].lower())
    print(f"PASS format_for_user safely handles unexpected errors")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.4 Trust Control Tests")
    print("=" * 70)
    print()
    print("--- Severe regularity refusal ---")
    test_severe_regularity_is_refused()
    test_moderate_regularity_warns_but_proceeds()
    test_severe_aspect_ratio_is_refused()
    print()
    print("--- SCWB heuristic naming ---")
    test_scwb_check_is_labeled_heuristic()
    print()
    print("--- KB version pinning ---")
    test_kb_versions_pinned_per_output()
    test_pile_kb_version_added_when_pile_used()
    print()
    print("--- Trace ID + summarisation ---")
    test_trace_id_generated_per_execute()
    test_summarize_trace_returns_event_history()
    print()
    print("--- Lateral load comparison ---")
    test_lateral_load_comparison_present()
    print()
    print("--- User-facing visibility ---")
    test_confidence_definitions_in_explain()
    test_what_we_check_section_visible()
    test_preliminary_banner_at_top()
    print()
    print("--- Structural sensitivity ---")
    test_structural_sensitivity_present()
    print()
    print("--- Logging hygiene ---")
    test_no_json_logs_in_console_by_default()
    print()
    print("--- Error formatting ---")
    test_format_for_user_handles_typed_errors()
    test_format_for_user_handles_unexpected_errors()
    print()
    print("=" * 70)
    print("ALL v0.4 TRUST CONTROL TESTS PASSED")
    print("=" * 70)
