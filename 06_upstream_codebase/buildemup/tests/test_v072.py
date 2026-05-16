"""
v0.7.2 tests — Insights feedback loop (v0.7.1 review Deferred #3 reopened).

Scope (narrow):
  - In-memory ring buffer records execution signatures
  - Top-N warning aggregation surfaces patterns
  - Meaningful-signal threshold (10 minimum) prevents noise
  - Buffer is thread-safe
  - Proactive guidance integrated into Component 7 output
  - Deploy-safe: defensive error handling in recording path
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from buildemup.utils.insights_buffer import (
    InsightsBuffer, ExecutionSignature, ProactiveGuidance,
    get_insights_buffer, reset_insights_buffer_for_testing,
    build_signature_from_result,
    _MIN_EXECUTIONS_FOR_INSIGHTS, _MIN_OCCURRENCE_RATE,
)


def _make_signature(city="chennai", warnings=("warning1",),
                    frame="SAFE", drift="SAFE") -> ExecutionSignature:
    return ExecutionSignature(
        timestamp="2026-04-23T10:00:00",
        city=city,
        seismic_zone="II",
        floors_above_ground=1,
        warnings=warnings,
        frame_sanity_result=frame,
        global_stability_result=drift,
        has_refusal=False,
        cost_bucket_lakhs=15,
        validation_status_variant="standard",
    )


# ─── A. Buffer basics ────────────────────────────────────────────────────
def test_empty_buffer_has_no_signal():
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    guidance = buf.get_proactive_guidance()
    assert guidance.total_executions_seen == 0
    assert guidance.has_meaningful_signal is False
    print("PASS empty buffer: no signal")


def test_buffer_records_and_retrieves():
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    for i in range(5):
        buf.record(_make_signature())
    assert buf.size() == 5
    snapshot = buf.snapshot()
    assert len(snapshot) == 5
    print(f"PASS buffer holds {buf.size()} signatures")


def test_buffer_ring_caps_at_max_size():
    """Buffer is bounded — old entries dropped when full."""
    reset_insights_buffer_for_testing()
    buf = InsightsBuffer(maxsize=10)
    for i in range(50):
        buf.record(_make_signature(warnings=(f"w_{i}",)))
    assert buf.size() == 10  # Never exceeds maxsize
    snapshot = buf.snapshot()
    # Should hold the LAST 10 entries (w_40 through w_49)
    last_warning = snapshot[-1].warnings[0]
    assert last_warning == "w_49"
    first_warning = snapshot[0].warnings[0]
    assert first_warning == "w_40"
    print(f"PASS buffer capped at maxsize, retains latest entries")


def test_buffer_is_thread_safe():
    """Concurrent recording must not corrupt buffer."""
    import threading
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()

    def worker():
        for i in range(100):
            buf.record(_make_signature())

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    # 10 threads × 100 records = 1000, but buffer maxsize 200, capped at 200
    assert buf.size() == 200
    print(f"PASS thread-safe: 10 threads × 100 records = buffer at {buf.size()}")


# ─── B. Meaningful signal threshold ──────────────────────────────────────
def test_minimum_executions_threshold():
    """Below MIN threshold, has_meaningful_signal is False."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    for i in range(_MIN_EXECUTIONS_FOR_INSIGHTS - 1):
        buf.record(_make_signature())
    guidance = buf.get_proactive_guidance()
    assert guidance.has_meaningful_signal is False
    # One more tips us over threshold
    buf.record(_make_signature())
    guidance = buf.get_proactive_guidance()
    assert guidance.has_meaningful_signal is True
    print(f"PASS signal threshold at {_MIN_EXECUTIONS_FOR_INSIGHTS} executions")


def test_below_threshold_user_message_explains():
    """User-facing message tells you signal will activate later."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    for i in range(3):
        buf.record(_make_signature())
    guidance = buf.get_proactive_guidance()
    assert "Not enough history" in guidance.user_message
    assert str(_MIN_EXECUTIONS_FOR_INSIGHTS) in guidance.user_message
    print("PASS below-threshold message is helpful")


# ─── C. Top-N pattern aggregation ────────────────────────────────────────
def test_common_warnings_ranked():
    """Most frequent warning surfaces first."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    # 15 executions with "soil test" common, "wind" less so
    for i in range(15):
        warns = ("soil test recommended",)
        if i < 8:
            warns = warns + ("wind exposure uncertain",)
        buf.record(_make_signature(warnings=warns))
    guidance = buf.get_proactive_guidance()
    # Most frequent must appear first
    assert guidance.top_warnings[0][0] == "soil test recommended"
    assert guidance.top_warnings[0][1] == 15
    # Second most frequent
    assert guidance.top_warnings[1][0] == "wind exposure uncertain"
    assert guidance.top_warnings[1][1] == 8
    print(f"PASS top warnings ranked: "
          f"{guidance.top_warnings[0][0][:20]}={guidance.top_warnings[0][1]}x")


def test_top_n_caps_at_three():
    """Only top 3 common warnings surfaced (bounded)."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    # 15 executions, each with 5 unique warnings
    for i in range(15):
        warns = tuple(f"warning_{j}" for j in range(5))
        buf.record(_make_signature(warnings=warns))
    guidance = buf.get_proactive_guidance()
    # Only 3 surface (the top 3 by count)
    assert len(guidance.top_warnings) <= 3
    print(f"PASS top-N capped at 3 (got {len(guidance.top_warnings)})")


def test_rare_warnings_excluded():
    """Warnings below MIN_OCCURRENCE_RATE are filtered out."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    # 20 executions: common in all, rare in just one
    for i in range(20):
        warns = ("everyone has this",)
        if i == 0:
            warns = warns + ("appears only once",)
        buf.record(_make_signature(warnings=warns))
    guidance = buf.get_proactive_guidance()
    warning_texts = [w[0] for w in guidance.top_warnings]
    assert "everyone has this" in warning_texts
    assert "appears only once" not in warning_texts  # 5% < 20% threshold
    print("PASS rare warnings filtered below 20% threshold")


def test_city_distribution_tracked():
    """top_cities tracks per-city counts."""
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    for i in range(10):
        buf.record(_make_signature(city="chennai"))
    for i in range(6):
        buf.record(_make_signature(city="bangalore"))
    for i in range(4):
        buf.record(_make_signature(city="mumbai"))
    guidance = buf.get_proactive_guidance()
    assert guidance.top_cities[0] == ("chennai", 10)
    assert guidance.top_cities[1] == ("bangalore", 6)
    print(f"PASS city distribution: {guidance.top_cities}")


def test_frame_sanity_distribution_tracked():
    reset_insights_buffer_for_testing()
    buf = get_insights_buffer()
    for i in range(8):
        buf.record(_make_signature(frame="SAFE"))
    for i in range(4):
        buf.record(_make_signature(frame="WARNING"))
    guidance = buf.get_proactive_guidance()
    assert guidance.frame_sanity_distribution["SAFE"] == 8
    assert guidance.frame_sanity_distribution["WARNING"] == 4
    print(f"PASS frame sanity distribution: {guidance.frame_sanity_distribution}")


# ─── D. Orchestrator integration ─────────────────────────────────────────
def test_orchestrator_populates_proactive_guidance():
    """Every execute() result has proactive_guidance field."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    engine = StructuralGridEngine()
    result = engine.execute(StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    ))
    assert result.proactive_guidance is not None
    print("PASS orchestrator populates proactive_guidance")


def test_orchestrator_records_to_buffer():
    """Each execute() call adds to the insights buffer."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    buf = get_insights_buffer()
    assert buf.size() == 0
    engine = StructuralGridEngine()
    engine.execute(StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    ))
    assert buf.size() == 1
    engine.execute(StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    ))
    assert buf.size() == 2
    print(f"PASS each execute adds to buffer (size={buf.size()})")


def test_buffer_fills_up_and_guidance_activates():
    """After ≥ MIN executions, guidance becomes meaningful."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    engine = StructuralGridEngine()
    # First execution: no meaningful signal
    first = engine.execute(StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    ))
    assert first.proactive_guidance.has_meaningful_signal is False

    # Fill buffer
    for i in range(_MIN_EXECUTIONS_FOR_INSIGHTS):
        engine.execute(StructuralGridInput(
            envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
        ))

    # Now should have signal
    nth = engine.execute(StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
    ))
    assert nth.proactive_guidance.has_meaningful_signal is True
    print(f"PASS guidance activates after {_MIN_EXECUTIONS_FOR_INSIGHTS} executions")


def test_explain_shows_proactive_guidance_when_signal_exists():
    """explain() renders PROACTIVE GUIDANCE section when signal is present."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    engine = StructuralGridEngine()
    # Fill buffer
    for i in range(_MIN_EXECUTIONS_FOR_INSIGHTS + 2):
        engine.execute(StructuralGridInput(
            envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
        ))
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = engine.execute(inp)
    exp = engine.explain(inp, result)
    assert "PROACTIVE GUIDANCE" in exp
    assert "patterns from recent plans" in exp
    print("PASS explain() shows PROACTIVE GUIDANCE section")


def test_explain_omits_proactive_guidance_when_no_signal():
    """explain() skips the section when buffer is too small."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    engine = StructuralGridEngine()
    inp = StructuralGridInput(envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1)
    result = engine.execute(inp)    # first one: buffer has 1 entry
    exp = engine.explain(inp, result)
    assert "PROACTIVE GUIDANCE" not in exp
    print("PASS explain() omits PROACTIVE GUIDANCE when no signal")


# ─── E. Signature builder ────────────────────────────────────────────────
def test_build_signature_from_real_result():
    """build_signature_from_result extracts fields from Component 7 output."""
    reset_insights_buffer_for_testing()
    from buildemup.components.c07_structural_grid import (
        StructuralGridEngine, StructuralGridInput,
    )
    inp = StructuralGridInput(
        envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
        city="chennai", seismic_zone="II",
    )
    result = StructuralGridEngine().execute(inp)
    sig = build_signature_from_result(inp, result)
    assert sig.city == "chennai"
    assert sig.seismic_zone == "II"
    assert sig.floors_above_ground == 1
    assert sig.frame_sanity_result in ("SAFE", "WARNING", "FAIL")
    assert sig.global_stability_result in ("SAFE", "WARNING", "FAIL")
    assert sig.has_refusal is False
    assert sig.cost_bucket_lakhs > 0
    print(f"PASS signature extracted correctly: {sig.city} zone {sig.seismic_zone}, "
          f"cost ₹{sig.cost_bucket_lakhs}L")


def test_build_signature_handles_missing_fields_gracefully():
    """Defensive: degenerate input doesn't crash the builder."""
    class FakeInp: pass
    class FakeResult: pass
    sig = build_signature_from_result(FakeInp(), FakeResult())
    # Should use defaults, not crash
    assert sig.city == "unknown"
    assert sig.frame_sanity_result == "UNKNOWN"
    print("PASS signature builder defensively handles missing fields")


def test_signature_warnings_truncated_and_bounded():
    """Warnings in signatures are truncated to 80 chars and limited to 10."""
    class FakeInp:
        city = "chennai"
        seismic_zone = "II"
        floors_above_ground = 1
    class FakeResult:
        validation_status = "PENDING"
        all_warnings = [
            "x" * 200,  # Long warning
        ] * 20  # And too many
        cost = None
        frame_sanity = None
        global_stability = None
    sig = build_signature_from_result(FakeInp(), FakeResult())
    assert len(sig.warnings) <= 10
    for w in sig.warnings:
        assert len(w) <= 80
    print(f"PASS warnings bounded: {len(sig.warnings)} entries, ≤80 chars each")


if __name__ == "__main__":
    print("=" * 70)
    print("v0.7.2 Tests — Insights Feedback Loop")
    print("=" * 70)
    print()
    print("--- A. Buffer basics ---")
    test_empty_buffer_has_no_signal()
    test_buffer_records_and_retrieves()
    test_buffer_ring_caps_at_max_size()
    test_buffer_is_thread_safe()
    print()
    print("--- B. Meaningful signal threshold ---")
    test_minimum_executions_threshold()
    test_below_threshold_user_message_explains()
    print()
    print("--- C. Top-N pattern aggregation ---")
    test_common_warnings_ranked()
    test_top_n_caps_at_three()
    test_rare_warnings_excluded()
    test_city_distribution_tracked()
    test_frame_sanity_distribution_tracked()
    print()
    print("--- D. Orchestrator integration ---")
    test_orchestrator_populates_proactive_guidance()
    test_orchestrator_records_to_buffer()
    test_buffer_fills_up_and_guidance_activates()
    test_explain_shows_proactive_guidance_when_signal_exists()
    test_explain_omits_proactive_guidance_when_no_signal()
    print()
    print("--- E. Signature builder ---")
    test_build_signature_from_real_result()
    test_build_signature_handles_missing_fields_gracefully()
    test_signature_warnings_truncated_and_bounded()
    print()
    print("=" * 70)
    print("ALL v0.7.2 TESTS PASSED")
    print("=" * 70)
