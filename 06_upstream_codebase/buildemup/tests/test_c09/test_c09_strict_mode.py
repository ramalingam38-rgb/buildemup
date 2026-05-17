"""C9 STRICT-mode escalation tests.

Per C9 SPEC v0.7 LOCKED § 7 + § 14.41.

In STRICT mode, three WARN-tier signals escalate to per-candidate hard-fails:
  - Inv 10 packing → PackingInfeasibleError
  - Inv 17b RISKY width → WidthRiskyError
  - Inv 18 OVERSIZED grid → GridOversizeError

These tests exercise the validator directly (orchestrator-level integration is
covered in test_c9_orchestrator.py). Twelve tests total, four per escalation.
"""
from __future__ import annotations

import pytest

from buildemup.components.c09 import (
    EnforcementMode,
    GridOversizeError,
    PackingInfeasibleError,
    RoomCategory,
    WidthFeasibilityVerdict,
    WidthRiskyError,
)
from buildemup.components.c09.validator import run_invariants
from buildemup.tests._c9_fixtures import make_regulatory, make_room


# Helper: build a 1-bedroom room set that we can manipulate.
def _single_master_br(*, liveability_min_area_m2: float = 13.0,
                      liveability_min_width_m: float = 3.3,
                      target_m2: float = 14.9, max_m2: float = 23.84):
    return (
        make_room(
            room_id="BEDROOM_1", priority=1, is_master=True,
            liveability_min_area_m2=liveability_min_area_m2,
            liveability_min_width_m=liveability_min_width_m,
            target_m2=target_m2, max_m2=max_m2,
        ),
    )


def _all_feasible(rooms):
    return {r.room_id: WidthFeasibilityVerdict.FEASIBLE for r in rooms}


# ---------------------------------------------------------------------------
# Inv 10 — STRICT escalation: PackingInfeasibleError
# ---------------------------------------------------------------------------


def test_strict_packing_raises_when_total_min_exceeds_capacity():
    """Σ liv_min > envelope * packing → STRICT raises."""
    rooms = _single_master_br(liveability_min_area_m2=13.0)
    with pytest.raises(PackingInfeasibleError, match="Inv 10"):
        run_invariants(
            rooms=rooms, bedroom_count=1, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=_all_feasible(rooms),
            bay_max_m=3.0, envelope_minus_corridor_m2=15.0,  # 15 * 0.75 = 11.25 < 13
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )


def test_warn_packing_does_not_raise_logs_warning():
    """Same scenario but WARN mode: warning surfaces in outcome, no raise."""
    rooms = _single_master_br()
    out = run_invariants(
        rooms=rooms, bedroom_count=1, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=_all_feasible(rooms),
        bay_max_m=3.0, envelope_minus_corridor_m2=15.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
        candidate_index=0,
    )
    assert out.heuristic_packing_check_warning is True


def test_strict_packing_at_boundary_does_not_raise():
    """Σ liv_min == envelope * packing exactly: no warning, no raise."""
    rooms = _single_master_br(liveability_min_area_m2=15.0,
                              target_m2=15.0, max_m2=24.0)
    # envelope * 0.75 = 15 == liv_min → no warning
    out = run_invariants(
        rooms=rooms, bedroom_count=1, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=_all_feasible(rooms),
        bay_max_m=3.0, envelope_minus_corridor_m2=20.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
        candidate_index=0,
    )
    assert out.heuristic_packing_check_warning is False


def test_strict_packing_error_carries_metadata():
    rooms = _single_master_br()
    try:
        run_invariants(
            rooms=rooms, bedroom_count=1, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=_all_feasible(rooms),
            bay_max_m=3.0, envelope_minus_corridor_m2=15.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=4,
        )
    except PackingInfeasibleError as exc:
        assert exc.candidate_index == 4
        assert exc.packing_efficiency == 0.75
        assert exc.total_liveability_min_area_m2 == 13.0
        assert exc.packing_capacity_m2 == pytest.approx(11.25)


# ---------------------------------------------------------------------------
# Inv 17b — STRICT escalation: WidthRiskyError
# ---------------------------------------------------------------------------


def test_strict_width_risky_raises():
    rooms = _single_master_br()
    width_verdicts = {"BEDROOM_1": WidthFeasibilityVerdict.RISKY}
    with pytest.raises(WidthRiskyError, match="Inv 17b"):
        run_invariants(
            rooms=rooms, bedroom_count=1, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )


def test_warn_width_risky_does_not_raise_only_logs():
    rooms = _single_master_br()
    width_verdicts = {"BEDROOM_1": WidthFeasibilityVerdict.RISKY}
    out = run_invariants(
        rooms=rooms, bedroom_count=1, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=width_verdicts,
        bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
        candidate_index=0,
    )
    assert out.width_feasibility_per_room["BEDROOM_1"] == WidthFeasibilityVerdict.RISKY


def test_strict_width_feasible_does_not_raise():
    rooms = _single_master_br()
    out = run_invariants(
        rooms=rooms, bedroom_count=1, bathroom_count=0,
        has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=_all_feasible(rooms),
        bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
        candidate_index=0,
    )
    assert out.width_feasibility_per_room["BEDROOM_1"] == WidthFeasibilityVerdict.FEASIBLE


def test_strict_width_risky_error_carries_room_ids():
    rooms = (
        make_room(room_id="BR1", priority=1, is_master=True),
        make_room(room_id="BR2", priority=2, is_master=False,
                  liveability_min_area_m2=9.5, liveability_min_width_m=3.0,
                  target_m2=10.2, max_m2=16.32,
                  regulatory=make_regulatory(area_m2=9.5, width_m=2.4)),
    )
    width_verdicts = {
        "BR1": WidthFeasibilityVerdict.RISKY,
        "BR2": WidthFeasibilityVerdict.FEASIBLE,
    }
    try:
        run_invariants(
            rooms=rooms, bedroom_count=2, bathroom_count=0,
            has_kitchen=False, has_living=False, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=80.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=2,
        )
    except WidthRiskyError as exc:
        assert exc.candidate_index == 2
        assert exc.risky_room_ids == ("BR1",)


# ---------------------------------------------------------------------------
# Inv 18 — STRICT escalation: GridOversizeError
# ---------------------------------------------------------------------------


def test_strict_grid_oversize_raises():
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False,
                  liveability_min_area_m2=16.7, liveability_min_width_m=10.0,  # 10 > 3*3.0
                  target_m2=18.6, max_m2=46.5,
                  regulatory=make_regulatory(area_m2=9.5, width_m=3.6)),
    )
    width_verdicts = {"LIVING_1": WidthFeasibilityVerdict.FEASIBLE}
    with pytest.raises(GridOversizeError, match="Inv 18"):
        run_invariants(
            rooms=rooms, bedroom_count=0, bathroom_count=0,
            has_kitchen=False, has_living=True, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=200.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=0,
        )


def test_warn_grid_oversize_only_logs():
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False,
                  liveability_min_area_m2=16.7, liveability_min_width_m=10.0,
                  target_m2=18.6, max_m2=46.5,
                  regulatory=make_regulatory(area_m2=9.5, width_m=3.6)),
    )
    width_verdicts = {"LIVING_1": WidthFeasibilityVerdict.FEASIBLE}
    out = run_invariants(
        rooms=rooms, bedroom_count=0, bathroom_count=0,
        has_kitchen=False, has_living=True, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=width_verdicts,
        bay_max_m=3.0, envelope_minus_corridor_m2=200.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.WARN,
        candidate_index=0,
    )
    from buildemup.components.c09.schema import GridBayFeasibility
    assert out.grid_bay_feasibility_per_room["LIVING_1"] == GridBayFeasibility.OVERSIZED


def test_strict_grid_oversize_error_carries_metadata():
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False,
                  liveability_min_area_m2=16.7, liveability_min_width_m=10.0,
                  target_m2=18.6, max_m2=46.5,
                  regulatory=make_regulatory(area_m2=9.5, width_m=3.6)),
    )
    width_verdicts = {"LIVING_1": WidthFeasibilityVerdict.FEASIBLE}
    try:
        run_invariants(
            rooms=rooms, bedroom_count=0, bathroom_count=0,
            has_kitchen=False, has_living=True, has_pooja=False, has_utility=False,
            other_rooms_count=0, width_verdicts=width_verdicts,
            bay_max_m=3.0, envelope_minus_corridor_m2=200.0,
            packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
            candidate_index=1,
        )
    except GridOversizeError as exc:
        assert exc.candidate_index == 1
        assert exc.oversized_room_ids == ("LIVING_1",)
        assert exc.bay_max_m == 3.0


def test_strict_grid_triple_bay_does_not_raise():
    """TRIPLE_BAY (within 3 × bay) is yellow but does not escalate to error in STRICT."""
    rooms = (
        make_room(room_id="LIVING_1", category=RoomCategory.LIVING, priority=1,
                  is_master=False,
                  liveability_min_area_m2=16.7, liveability_min_width_m=8.0,  # 6 < 8 <= 9
                  target_m2=18.6, max_m2=46.5,
                  regulatory=make_regulatory(area_m2=9.5, width_m=3.6)),
    )
    width_verdicts = {"LIVING_1": WidthFeasibilityVerdict.FEASIBLE}
    # No raise.
    out = run_invariants(
        rooms=rooms, bedroom_count=0, bathroom_count=0,
        has_kitchen=False, has_living=True, has_pooja=False, has_utility=False,
        other_rooms_count=0, width_verdicts=width_verdicts,
        bay_max_m=3.0, envelope_minus_corridor_m2=200.0,
        packing_efficiency=0.75, enforcement_mode=EnforcementMode.STRICT,
        candidate_index=0,
    )
    from buildemup.components.c09.schema import GridBayFeasibility
    assert out.grid_bay_feasibility_per_room["LIVING_1"] == GridBayFeasibility.TRIPLE_BAY
