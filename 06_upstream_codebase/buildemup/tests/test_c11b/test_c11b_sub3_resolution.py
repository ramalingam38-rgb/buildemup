"""Sub-3 tests: input artifact resolution (Inv 26), W6-6 typed
accessor, MF rejection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from buildemup.components.c11b import MultiFloorRefinementNotSupportedError
from buildemup.components.c11b.errors import EvaluatorContractError
from buildemup.components.c11b.input_resolution import (
    _is_multi_floor_artifact,
    _resolve_input_artifact,
    get_primary_application_result,
    reject_if_multi_floor,
)


# ── lightweight stand-ins for upstream types ───────────────────────────


@dataclass
class FakeApplicationResult:
    output_candidate: Any = None


@dataclass
class FakeMTC:
    source_candidate: Any
    application_results: tuple


def _mtc_with(output_candidate: Any, source_candidate: Any = "source_stub") -> FakeMTC:
    return FakeMTC(
        source_candidate=source_candidate,
        application_results=(FakeApplicationResult(output_candidate=output_candidate),),
    )


# ── W6-6 typed accessor ────────────────────────────────────────────────


def test_w6_6_accessor_returns_single_result():
    mtc = _mtc_with(output_candidate="art")
    result = get_primary_application_result(mtc)
    assert result.output_candidate == "art"


def test_w6_6_accessor_raises_when_len_not_one_empty():
    mtc = FakeMTC(source_candidate="s", application_results=())
    with pytest.raises(EvaluatorContractError, match="exactly one"):
        get_primary_application_result(mtc)


def test_w6_6_accessor_raises_when_len_not_one_multiple():
    mtc = FakeMTC(
        source_candidate="s",
        application_results=(FakeApplicationResult(), FakeApplicationResult()),
    )
    with pytest.raises(EvaluatorContractError, match="exactly one"):
        get_primary_application_result(mtc)


# ── _resolve_input_artifact worked-example table (Inv 26) ─────────────


def test_resolve_input_tier_a_uses_source_when_output_none():
    """Tier A SHALLOW (M1-M5, M9): output_candidate is None →
    refine from source_candidate."""
    mtc = _mtc_with(output_candidate=None, source_candidate="src_artifact")
    assert _resolve_input_artifact(mtc) == "src_artifact"


def test_resolve_input_tier_b_uses_output_candidate():
    """Tier B (M6, M7) populates output_candidate."""
    mtc = _mtc_with(output_candidate="rebuilt_artifact")
    assert _resolve_input_artifact(mtc) == "rebuilt_artifact"


def test_resolve_input_m0_with_output_candidate():
    """M0_BASE (single-floor or MF wrapper) → use output_candidate
    per S41 self-review fix."""
    mtc = _mtc_with(output_candidate="m0_output")
    assert _resolve_input_artifact(mtc) == "m0_output"


def test_resolve_input_singleton_violation_raises():
    """Inv 26 audit-tier contract: len != 1 → defensive raise."""
    mtc = FakeMTC(source_candidate="s", application_results=())
    with pytest.raises(EvaluatorContractError):
        _resolve_input_artifact(mtc)


# ── MF rejection (W5-9 ordering) ───────────────────────────────────────


class FakeMultiFloorArtifact:
    """Marker-attribute object identified as multi-floor by C11a's
    ``is_real_multi_floor_candidate`` per Spec #4 v1.6 § 3.5
    (v1.3 marker-attribute pattern).

    The marker is a CLASS attribute ``__multi_floor_candidate__ = True``.
    """

    __multi_floor_candidate__ = True


def test_is_multi_floor_artifact_detects_marker():
    art = FakeMultiFloorArtifact()
    # The detector is provided by C11a; this should return True.
    assert _is_multi_floor_artifact(art) is True


def test_is_multi_floor_artifact_false_for_simple():
    assert _is_multi_floor_artifact("plain_string") is False


def test_reject_if_multi_floor_raises_on_mf():
    art = FakeMultiFloorArtifact()
    with pytest.raises(MultiFloorRefinementNotSupportedError):
        reject_if_multi_floor(art, topology_index=3)


def test_reject_if_multi_floor_passes_on_single_floor():
    reject_if_multi_floor("plain_artifact", topology_index=0)  # no raise


def test_reject_message_carries_topology_index():
    art = FakeMultiFloorArtifact()
    with pytest.raises(
        MultiFloorRefinementNotSupportedError, match="topology_index=5"
    ):
        reject_if_multi_floor(art, topology_index=5)
