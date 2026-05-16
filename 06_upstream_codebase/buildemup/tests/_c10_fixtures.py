"""
BuildemUp† — C10 test fixtures.

Shared fixture builders for C10 tests. Mirrors `_c9_fixtures.py` style.
Re-uses run_c8_pipeline + size_rooms to produce a realistic
RoomSizedCandidate tuple.

†= placeholder name marker.
"""
from __future__ import annotations

from typing import Tuple

from buildemup.components.c09 import size_rooms
from buildemup.components.c09.schema import RoomSizedCandidate
from buildemup.tests._c9_fixtures import run_c8_pipeline


def run_c9_pipeline() -> Tuple[
    Tuple[RoomSizedCandidate, ...], object, object, object,
]:
    """Run C5..C9 and return (room_sized_candidates, brief, grid, plot_analysis)."""
    cdc, brief, grid, plot_analysis = run_c8_pipeline()
    rsc_tuple = size_rooms(cdc, brief, grid, plot_analysis)
    return rsc_tuple, brief, grid, plot_analysis


__all__ = ["run_c9_pipeline"]
