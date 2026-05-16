"""Tests for Component 3a Session 7a — GateState serialization.

Covers S7a SPEC v1.0 LOCKED § 8.6 TestSerialization:
  - test_gate_state_round_trips_for_all_termination_reasons (P1)
  - test_gate_state_round_trips_with_typed_banner_events
  - test_gate_state_round_trips_with_failed_option_ids (frozenset)
  - test_gate_state_round_trips_with_per_case_iteration_counts
    (asserts MappingProxyType after rehydration)
  - test_schema_version_absent_loads_as_v1 (P8)
  - test_schema_version_explicit_mismatch_rejected (P8)
  - test_deterministic_json_serialization (P14)
"""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from types import MappingProxyType

from buildemup.components.c03a.gate_state import (
    DifferentPlotPromotionEvent,
    GateState,
    GateTerminationReason,
    SchemaVersionError,
    TransitionBannerEvent,
)
from buildemup.components.c03a_extreme_case_gate import ExtremeCaseGate
from buildemup.tests.test_c03a_session6_orchestrator_happy import (
    _DetectorPatch,
    _case,
    _make_brief,
    _make_gap_analysis,
    _make_runner,
)
from buildemup.domain.extreme_case import (
    BriefMode,
    CounterfactualSummary,
    ExtremeCaseId,
    ExtremeDecisionLog,
    PreviewModeAcknowledgment,
    ResolvedBrief,
)


def _gate_for_test():
    gap = _make_gap_analysis()
    runner, _ = _make_runner(gap)
    return ExtremeCaseGate(c2_runner=runner), gap


def _build_state_for_reason(reason: GateTerminationReason) -> GateState:
    """Build a real GateState that ends in the requested termination reason.

    SUCCESS, USER_ABORTED, and CBA_VERIFICATION_PAUSED have natural
    paths through the orchestrator. PREVIEW_MODE, MAX_ITERATIONS,
    PER_CASE_LIMIT are exercised via dataclasses.replace() over a real
    SUCCESS state because the orchestrator's full setup for those
    paths is involved and not necessary to demonstrate round-trip.
    The structural equivalence test (P1) is the same regardless.
    """
    gate, _ = _gate_for_test()

    if reason == GateTerminationReason.SUCCESS:
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        with _DetectorPatch([(case,), ()]):
            s0 = gate.start(session_id="t-success", brief=_make_brief())
            return gate.apply_user_decision(
                state=s0, case_id=case.case_id,
                chosen_option_id=case.options[0].option_id,
                user_acknowledged_at="2026-05-01T12:00:00Z",
            )

    if reason == GateTerminationReason.USER_ABORTED:
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        with _DetectorPatch([(case,)]):
            s0 = gate.start(session_id="t-abort", brief=_make_brief())
            return gate.apply_user_abort(s0)

    # For the remaining 4 reasons, take a real terminal state and
    # synthetically rebuild with the desired reason. The serialization
    # contract is reason-agnostic at to_dict/from_dict level.
    base = _build_state_for_reason(GateTerminationReason.SUCCESS)
    if reason == GateTerminationReason.PREVIEW_MODE:
        # Build a synthetic ResolvedBrief in PREVIEW mode
        rb_orig = base.final_resolved_brief
        assert rb_orig is not None
        # Need at least one unresolved blocker + one relaxed_constraint
        # + a PreviewModeAcknowledgment
        unresolved = base.remaining_cases[:1] or (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
        )
        if not unresolved:
            unresolved = (
                _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
            )
        # Build a fresh ExtremeCase to act as unresolved blocker
        unresolved = (
            _case(ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE),
        )
        ack = PreviewModeAcknowledgment(
            user_acknowledged_at="2026-05-01T12:00:00Z",
            acknowledgment_text=(
                "I understand this layout is for preview only and "
                "cannot be built without first resolving the listed "
                "blockers."
            ),
            user_session_id="user-sess-1",
        )
        # Use replace which preserves frozen dataclass invariants.
        # ResolvedBrief.__post_init__ validates PREVIEW invariants
        # so we must satisfy them.
        synthetic_rb = ResolvedBrief(
            original_brief=rb_orig.original_brief,
            revised_brief=rb_orig.revised_brief,
            decision_log=replace(
                rb_orig.decision_log,
                aborted=True,
                abort_reason="USER_CHOSE_PREVIEW_MODE",
            ),
            final_feasibility=rb_orig.final_feasibility,
            mode=BriefMode.PREVIEW,
            is_layout_ready=True,
            counterfactuals=rb_orig.counterfactuals,
            unresolved_blockers=unresolved,
            relaxed_constraints=("AREA_VS_ENVELOPE",),
            preflight_summary=rb_orig.preflight_summary,
            preview_mode_acknowledgment=ack,
        )
        return replace(
            base,
            termination_reason=GateTerminationReason.PREVIEW_MODE,
            final_resolved_brief=synthetic_rb,
        )

    if reason == GateTerminationReason.MAX_ITERATIONS_REACHED:
        return replace(
            base,
            termination_reason=GateTerminationReason.MAX_ITERATIONS_REACHED,
        )

    if reason == GateTerminationReason.PER_CASE_LIMIT_REACHED:
        return replace(
            base,
            termination_reason=GateTerminationReason.PER_CASE_LIMIT_REACHED,
        )

    if reason == GateTerminationReason.CBA_VERIFICATION_PAUSED:
        return replace(
            base,
            termination_reason=GateTerminationReason.CBA_VERIFICATION_PAUSED,
            # CBA pause has no final_resolved_brief — caller saw the
            # pause response, not a finalized brief
            final_resolved_brief=None,
        )

    raise ValueError(f"unexpected reason: {reason!r}")


class TestRoundTripAllTerminationReasons(unittest.TestCase):
    """P1 + P14 — every GateState round-trips losslessly via to_dict /
    from_dict and JSON.dumps with sort_keys=True.

    Spec § 8.6: parametrised over all 6 GateTerminationReason values;
    asserts STRUCTURAL EQUIVALENCE per P1.
    """

    def _assert_round_trip(self, state: GateState) -> None:
        d = state.to_dict()
        s = json.dumps(d, sort_keys=True, ensure_ascii=False)
        rehydrated = GateState.from_dict(json.loads(s))
        self.assertEqual(rehydrated.to_dict(), d)

    def test_round_trip_SUCCESS(self):
        self._assert_round_trip(
            _build_state_for_reason(GateTerminationReason.SUCCESS)
        )

    def test_round_trip_PREVIEW_MODE(self):
        self._assert_round_trip(
            _build_state_for_reason(GateTerminationReason.PREVIEW_MODE)
        )

    def test_round_trip_USER_ABORTED(self):
        self._assert_round_trip(
            _build_state_for_reason(GateTerminationReason.USER_ABORTED)
        )

    def test_round_trip_MAX_ITERATIONS_REACHED(self):
        self._assert_round_trip(
            _build_state_for_reason(
                GateTerminationReason.MAX_ITERATIONS_REACHED,
            )
        )

    def test_round_trip_PER_CASE_LIMIT_REACHED(self):
        self._assert_round_trip(
            _build_state_for_reason(
                GateTerminationReason.PER_CASE_LIMIT_REACHED,
            )
        )

    def test_round_trip_CBA_VERIFICATION_PAUSED(self):
        self._assert_round_trip(
            _build_state_for_reason(
                GateTerminationReason.CBA_VERIFICATION_PAUSED,
            )
        )


class TestRoundTripBannerEvents(unittest.TestCase):
    def test_round_trip_with_typed_banner_events(self):
        # Build a state and inject a TransitionBannerEvent + meta_banner
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        gate, _ = _gate_for_test()
        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="t-banners", brief=_make_brief())
        s = replace(
            s,
            transition_banner=TransitionBannerEvent(
                previous_case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
                new_case_id=case.case_id,
                previous_chosen_option_id="EC_001_OPT_A",
                previous_chosen_option_description="Drop the smallest bedroom",
                iteration=2,
            ),
            meta_banner=DifferentPlotPromotionEvent(
                trigger="EC002_AND_EC006_COFIRE",
                triggered_at_iteration=2,
            ),
        )
        d = s.to_dict()
        rehydrated = GateState.from_dict(json.loads(
            json.dumps(d, sort_keys=True),
        ))
        self.assertEqual(rehydrated.to_dict(), d)
        self.assertIsInstance(rehydrated.transition_banner,
                              TransitionBannerEvent)
        self.assertIsInstance(rehydrated.meta_banner,
                              DifferentPlotPromotionEvent)


class TestRoundTripFailedOptionIds(unittest.TestCase):
    def test_round_trip_with_failed_option_ids_frozenset(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        gate, _ = _gate_for_test()
        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="t-failed", brief=_make_brief())
        s = replace(
            s,
            failed_option_ids_for_current_case=frozenset(
                ["OPT_A", "OPT_B", "OPT_C"]
            ),
            last_error_message="user-facing message",
            last_error_option_id="OPT_C",
        )
        d = s.to_dict()
        # Wire format: list, sorted
        self.assertEqual(
            d["failed_option_ids_for_current_case"],
            ["OPT_A", "OPT_B", "OPT_C"],
        )
        rehydrated = GateState.from_dict(json.loads(
            json.dumps(d, sort_keys=True),
        ))
        # Rehydrated: frozenset (NOT a list)
        self.assertIsInstance(
            rehydrated.failed_option_ids_for_current_case, frozenset,
        )
        self.assertEqual(
            rehydrated.failed_option_ids_for_current_case,
            frozenset({"OPT_A", "OPT_B", "OPT_C"}),
        )


class TestRoundTripPerCaseIterationCounts(unittest.TestCase):
    def test_round_trip_with_per_case_iteration_counts_mappingproxy(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        gate, _ = _gate_for_test()
        with _DetectorPatch([(case,)]):
            s = gate.start(session_id="t-counts", brief=_make_brief())
        s = replace(
            s,
            per_case_iteration_counts=MappingProxyType(
                {"EC_001": 2, "EC_005": 1}
            ),
        )
        d = s.to_dict()
        # Wire format: plain dict
        self.assertEqual(
            d["per_case_iteration_counts"], {"EC_001": 2, "EC_005": 1},
        )
        rehydrated = GateState.from_dict(json.loads(
            json.dumps(d, sort_keys=True),
        ))
        # Rehydrated: MappingProxyType
        self.assertIsInstance(
            rehydrated.per_case_iteration_counts, MappingProxyType,
        )
        # Mutation rejected
        with self.assertRaises(TypeError):
            rehydrated.per_case_iteration_counts["EC_999"] = 999


class TestSchemaVersioning(unittest.TestCase):
    """P8 — _schema_version absent OR == "1" loads; explicit different rejected."""

    def test_schema_version_absent_loads_as_v1(self):
        s = _build_state_for_reason(GateTerminationReason.SUCCESS)
        d = s.to_dict()
        # Strip the version field
        del d["_schema_version"]
        rehydrated = GateState.from_dict(d)
        self.assertEqual(rehydrated.to_dict()["_schema_version"], "1")

    def test_schema_version_explicit_v1_loads(self):
        s = _build_state_for_reason(GateTerminationReason.SUCCESS)
        d = s.to_dict()
        d["_schema_version"] = "1"
        # Should not raise
        rehydrated = GateState.from_dict(d)
        self.assertEqual(rehydrated.to_dict(), s.to_dict())

    def test_schema_version_explicit_mismatch_rejected(self):
        s = _build_state_for_reason(GateTerminationReason.SUCCESS)
        d = s.to_dict()
        d["_schema_version"] = "2"  # unsupported future version
        with self.assertRaises(SchemaVersionError):
            GateState.from_dict(d)


class TestDeterministicJSON(unittest.TestCase):
    """P14 round 2 #5 — sort_keys=True yields byte-identical output
    for the same logical state."""

    def test_deterministic_json_serialization(self):
        s = _build_state_for_reason(GateTerminationReason.SUCCESS)
        d = s.to_dict()
        # Re-serialize the same dict twice: bytes must match.
        s1 = json.dumps(d, sort_keys=True, ensure_ascii=False)
        s2 = json.dumps(d, sort_keys=True, ensure_ascii=False)
        self.assertEqual(s1, s2)
        # Also: a round-trip dict should serialize byte-identically.
        rehydrated = GateState.from_dict(json.loads(s1))
        s3 = json.dumps(
            rehydrated.to_dict(), sort_keys=True, ensure_ascii=False,
        )
        self.assertEqual(s1, s3)


class TestCounterfactualSummaryNestedTuples(unittest.TestCase):
    """Verify the tuple-of-tuples → list-of-lists handling roundtrips."""

    def test_nested_tuples_in_alternatives_round_trip(self):
        cf = CounterfactualSummary(
            case_id=ExtremeCaseId.EC_001_TOTAL_AREA_EXCEEDS_ENVELOPE,
            chosen_option_id="OPT_A",
            chosen_outcome="Removed bedroom 3",
            alternatives=(
                ("OPT_B", "Reduce living size",
                 "Living would have been 8 sqm smaller"),
                ("OPT_C", "Cut budget",
                 "Quality tier would have dropped"),
            ),
        )
        d = cf.to_dict()
        # alternatives in JSON: list-of-lists
        self.assertIsInstance(d["alternatives"], list)
        self.assertIsInstance(d["alternatives"][0], list)
        rehydrated = CounterfactualSummary.from_dict(
            json.loads(json.dumps(d, sort_keys=True))
        )
        # Back to tuple-of-tuples
        self.assertIsInstance(rehydrated.alternatives, tuple)
        self.assertIsInstance(rehydrated.alternatives[0], tuple)
        self.assertEqual(rehydrated.to_dict(), d)


if __name__ == "__main__":
    unittest.main()
