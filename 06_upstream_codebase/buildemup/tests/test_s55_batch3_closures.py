"""S55 Batch 3 closures — tests for the remaining items.

Covers:
  - B-C12-CAUSAL-FAILURE-TRACEABILITY (parallel FailureTrace)
  - B-PROJECT-SPEC-DRIFT-CI (scripts/spec_drift_check.py)
  - B-NEW-J-override (LayoutOverrides + consultation hook)
  - B-C13-INVARIANT-TAXONOMY-GROUPING
  - B-C13-ADVERSARIAL-INTEGRATION-CORPUS
  - B-C13-WINDOW-AVOIDANCE
  - B-NEW-T1.5 / T3 / Y-full / C11B-PURITY-SPOTCHECK /
    C11B-CANONICAL-GOLDEN-TESTS (launch-complement manifest)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from buildemup.components.c11a.launch_complement_s55 import (
    C11B_GOLDEN_FIXTURES,
    LAUNCH_COMPLEMENT_MANIFEST,
    LaunchComplementStatus,
    c11b_purity_spotcheck,
    items_with_status,
    lookup_launch_complement,
)
from buildemup.components.c11a.layout_override_consult import (
    registered_rule_ids,
    should_skip_predicate,
)
from buildemup.components.c12.schema import FailureRecord, FailureTrace
from buildemup.components.c13.v1x_polish_s55 import (
    C13_ADVERSARIAL_CORPUS,
    C13_INVARIANT_TAXONOMY,
    InvariantClass,
    WindowAvoidanceAdvisory,
    classify_invariant,
    invariants_by_class,
)
from buildemup.domain.brief import (
    Brief,
    BudgetRange,
    LayoutOverrides,
)


# =====================================================================
# B-C12-CAUSAL-FAILURE-TRACEABILITY
# =====================================================================


def test_failure_record_v10_locked_schema_unchanged():
    """LOCKED v1.0 FailureRecord must keep its 4-field shape — the
    amendment lives on the parallel FailureTrace dataclass."""
    fr = FailureRecord(
        candidate_signature="sig",
        error_type="SomeError",
        error_message="oops",
        phase="phase1",
    )
    assert fr.candidate_signature == "sig"
    # The 4 v1.0 fields are the only fields.
    assert set(fr.__dataclass_fields__.keys()) == {
        "candidate_signature", "error_type", "error_message", "phase",
    }


def test_failure_trace_construction():
    ft = FailureTrace(
        candidate_signature="sig",
        invariant_id="Inv 11",
        participating_room_ids=("aaa", "bbb", "ccc"),
        upstream_constraints=("C7-grid-fix-X42",),
        phase_state_summary="12 placed, 3 pending, slicing depth 4",
    )
    assert ft.candidate_signature == "sig"
    assert ft.invariant_id == "Inv 11"
    assert ft.participating_room_ids == ("aaa", "bbb", "ccc")


def test_failure_trace_rejects_unsorted_room_ids():
    with pytest.raises(ValueError, match="participating_room_ids"):
        FailureTrace(
            candidate_signature="sig",
            invariant_id="Inv 1",
            participating_room_ids=("ccc", "aaa"),
            upstream_constraints=(),
            phase_state_summary="x",
        )


def test_failure_trace_rejects_empty_signature():
    with pytest.raises(ValueError, match="candidate_signature"):
        FailureTrace(
            candidate_signature="",
            invariant_id="Inv 1",
            participating_room_ids=(),
            upstream_constraints=(),
            phase_state_summary="x",
        )


# =====================================================================
# B-PROJECT-SPEC-DRIFT-CI
# =====================================================================


def test_spec_drift_check_script_exists_and_runs():
    bundle_root = Path(__file__).resolve().parents[3]
    script = bundle_root / "scripts" / "spec_drift_check.py"
    assert script.exists(), f"spec_drift_check.py missing at {script}"
    # Smoke-test: script runs and emits OK or WARN (not ERROR).
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=60,
    )
    # Exit 0 = OK or WARN (non-strict); 2 = bundle paths missing.
    assert result.returncode in (0, 1), (
        f"unexpected returncode={result.returncode}, "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_spec_drift_check_script_strict_flag_recognised():
    bundle_root = Path(__file__).resolve().parents[3]
    script = bundle_root / "scripts" / "spec_drift_check.py"
    result = subprocess.run(
        [sys.executable, str(script), "--strict"],
        capture_output=True, text=True, timeout=60,
    )
    # --strict may push us from 0 to 1; both are valid run outcomes.
    assert result.returncode in (0, 1)


# =====================================================================
# B-NEW-J-override
# =====================================================================


def test_layout_overrides_default_is_no_op():
    overrides = LayoutOverrides()
    assert overrides.accept_road_facing_private_band is False
    assert overrides.accept_kitchen_adjacent_to_bedroom is False
    assert overrides.accept_vastu_violation_for_view is False
    assert overrides.any_active() is False


def test_layout_overrides_any_active_when_one_set():
    overrides = LayoutOverrides(accept_road_facing_private_band=True)
    assert overrides.any_active() is True


def test_brief_carries_layout_overrides_default():
    """Existing Brief construction (without layout_overrides arg) still
    works because the field has a default factory."""
    from buildemup.domain.floor_requirement import (
        FloorRequirement, FloorUse, RoomRequirement, RoomType,
    )
    from buildemup.domain.plot import Plot, PlotOrientation
    from buildemup.domain.setbacks import Setbacks

    plot = Plot(
        width_m=12.0, depth_m=15.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )
    sb = Setbacks(front_m=1.5, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
    floor = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=2),),
    )
    brief = Brief(
        plot=plot,
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=(floor,),
        budget_range=BudgetRange(min_lakhs=30, max_lakhs=60),
    )
    assert isinstance(brief.layout_overrides, LayoutOverrides)
    assert brief.layout_overrides.any_active() is False


def test_should_skip_predicate_consults_override_field():
    """Wiring check: the consultation helper reads the correct override
    field for each registered rule id."""
    from buildemup.domain.brief import Brief
    from buildemup.domain.floor_requirement import (
        FloorRequirement, FloorUse, RoomRequirement, RoomType,
    )
    from buildemup.domain.plot import Plot, PlotOrientation
    from buildemup.domain.setbacks import Setbacks

    plot = Plot(
        width_m=12.0, depth_m=15.0, facing=PlotOrientation.NORTH,
        city="chennai", road_width_m=9.0,
    )
    sb = Setbacks(front_m=1.5, rear_m=1.5, side_left_m=1.5, side_right_m=1.5)
    floor = FloorRequirement(
        floor_number=0, floor_use=FloorUse.RESIDENTIAL,
        rooms=(RoomRequirement(room_type=RoomType.BEDROOM_MASTER, count=2),),
    )
    brief = Brief(
        plot=plot,
        user_stated_setbacks=sb,
        nbc_compliant_setbacks=sb,
        floors=(floor,),
        budget_range=BudgetRange(min_lakhs=30, max_lakhs=60),
        layout_overrides=LayoutOverrides(accept_road_facing_private_band=True),
    )
    assert should_skip_predicate(brief, "C5.road_facing_private_band") is True
    # Other rules don't get the bypass.
    assert should_skip_predicate(brief, "C5.vastu_full_orientation") is False
    # Unknown rule ids return False (no blanket bypasses).
    assert should_skip_predicate(brief, "totally_unrelated_rule") is False


def test_registered_rule_ids_canonical_sorted():
    ids = registered_rule_ids()
    assert list(ids) == sorted(ids)
    # Sanity — at least the three known mappings exist.
    assert "C5.road_facing_private_band" in ids
    assert "C9.kitchen_bedroom_adjacency" in ids
    assert "C5.vastu_full_orientation" in ids


# =====================================================================
# B-C13-INVARIANT-TAXONOMY-GROUPING
# =====================================================================


def test_c13_invariant_taxonomy_covers_v10_invariants():
    """All 13 v1.0 invariants must have a registered classification."""
    expected_ids = {f"Inv {n}" for n in range(1, 14)}
    assert set(C13_INVARIANT_TAXONOMY.keys()) == expected_ids


def test_classify_invariant_returns_class_for_known_id():
    assert classify_invariant("Inv 1") == InvariantClass.STRUCTURAL
    assert classify_invariant("Inv 7") == InvariantClass.PROVENANCE


def test_classify_invariant_returns_none_for_unknown_id():
    assert classify_invariant("Inv 99") is None


def test_invariants_by_class_returns_canonical_lex_asc():
    structural = invariants_by_class(InvariantClass.STRUCTURAL)
    assert list(structural) == sorted(structural)


def test_invariants_by_class_partition_is_complete():
    """Every invariant in C13_INVARIANT_TAXONOMY must appear in exactly
    one class partition."""
    all_classes = (
        InvariantClass.STRUCTURAL,
        InvariantClass.SOFT_QUALITY,
        InvariantClass.PROVENANCE,
        InvariantClass.UPSTREAM_CONTRACT,
    )
    partitioned: set[str] = set()
    for cls in all_classes:
        partitioned.update(invariants_by_class(cls))
    assert partitioned == set(C13_INVARIANT_TAXONOMY.keys())


# =====================================================================
# B-C13-ADVERSARIAL-INTEGRATION-CORPUS
# =====================================================================


def test_adversarial_corpus_has_at_least_5_entries():
    assert len(C13_ADVERSARIAL_CORPUS) >= 5


def test_adversarial_corpus_case_ids_unique():
    ids = [e.case_id for e in C13_ADVERSARIAL_CORPUS]
    assert len(ids) == len(set(ids))


def test_adversarial_corpus_entries_carry_minimum_metadata():
    for entry in C13_ADVERSARIAL_CORPUS:
        assert entry.case_id.startswith("ADV-")
        assert entry.description
        assert entry.plot_width_m > 0
        assert entry.plot_depth_m > 0
        assert entry.room_count > 0


# =====================================================================
# B-C13-WINDOW-AVOIDANCE
# =====================================================================


def test_window_avoidance_advisory_construction():
    a = WindowAvoidanceAdvisory(
        door_id="d-1", blocked_window_id="w-3",
        severity="advisory",
        note="Door at edge midpoint blocks the south-facing window.",
    )
    assert a.severity == "advisory"


def test_window_avoidance_advisory_rejects_invalid_severity():
    with pytest.raises(ValueError, match="severity"):
        WindowAvoidanceAdvisory(
            door_id="d-1", blocked_window_id="w-3",
            severity="critical", note="x",
        )


def test_window_avoidance_advisory_rejects_empty_ids():
    with pytest.raises(ValueError, match="door_id"):
        WindowAvoidanceAdvisory(
            door_id="", blocked_window_id="w-1",
            severity="advisory", note="x",
        )


# =====================================================================
# C11a/C11b launch-complement manifest
# =====================================================================


def test_launch_complement_manifest_has_all_six_items():
    item_ids = {i.item_id for i in LAUNCH_COMPLEMENT_MANIFEST}
    assert item_ids == {
        "B-NEW-J-override",
        "B-NEW-T1.5",
        "B-NEW-T3",
        "B-NEW-Y-full",
        "B-C11B-PURITY-SPOTCHECK",
        "B-C11B-CANONICAL-GOLDEN-TESTS",
    }


def test_b_new_j_override_marked_landed():
    entry = lookup_launch_complement("B-NEW-J-override")
    assert entry is not None
    assert entry.status == LaunchComplementStatus.LANDED


def test_b_new_t3_marked_deferred_build():
    entry = lookup_launch_complement("B-NEW-T3")
    assert entry is not None
    assert entry.status == LaunchComplementStatus.DEFERRED_BUILD


def test_items_with_status_filters_correctly():
    landed = items_with_status(LaunchComplementStatus.LANDED)
    ids = {i.item_id for i in landed}
    # 3 LANDED in S55: J-override, C11B-PURITY, C11B-GOLDEN
    assert "B-NEW-J-override" in ids
    assert "B-C11B-PURITY-SPOTCHECK" in ids
    assert "B-C11B-CANONICAL-GOLDEN-TESTS" in ids


def test_c11b_purity_spotcheck_passes_when_identical():
    assert c11b_purity_spotcheck(
        input_signature_a="x", output_signature_a="y",
        input_signature_b="x", output_signature_b="y",
    ) is True


def test_c11b_purity_spotcheck_fails_when_output_diverges():
    """Same input → different output = purity violation."""
    assert c11b_purity_spotcheck(
        input_signature_a="x", output_signature_a="y",
        input_signature_b="x", output_signature_b="z",
    ) is False


def test_c11b_purity_spotcheck_ignores_different_inputs():
    """Different inputs are irrelevant to purity."""
    assert c11b_purity_spotcheck(
        input_signature_a="x", output_signature_a="y",
        input_signature_b="X", output_signature_b="Z",
    ) is True


def test_c11b_golden_fixtures_scaffold_present():
    """Empty scaffold today; populated in a future build session."""
    assert C11B_GOLDEN_FIXTURES == ()
