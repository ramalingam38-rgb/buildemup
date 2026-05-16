"""
BuildemUp — Component 15 — Sub-2 registry tests
==================================================

Per C15 SPEC v0.2 LOCKED Inv P2/P3/P4/P12:

- CheckRegistry: lex-ASC sort, uniqueness, _check_id_set consistency
- make_registry: sorts arbitrary input, surfaces duplicates
- build_registry: includes all currently-implemented checks
- contains / get / ids / __iter__ / __len__ all behave correctly
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from buildemup.components.c15 import (
    Check,
    CheckContext,
    CheckEpistemicKind,
    CheckRegistry,
    CheckRegistryError,
    CulturalProfile,
    build_registry,
    make_registry,
)


@dataclass(frozen=True)
class _TestCheck:
    """Inline test check — minimal implementation of the Check protocol."""
    check_id: str
    dimension_id: int = 1
    epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
    data_dependencies: tuple[str, ...] = ()
    cultural_scope: frozenset[CulturalProfile] | None = None

    def evaluate(self, context: CheckContext):
        return None


# =============================================================================
# make_registry
# =============================================================================

def test_make_registry_happy_path_single_check():
    reg = make_registry([_TestCheck(check_id="P1.1")])
    assert len(reg) == 1
    assert reg.ids() == ("P1.1",)


def test_make_registry_sorts_input_lex_asc():
    # Caller passes in arbitrary order; registry sorts.
    reg = make_registry([
        _TestCheck(check_id="P2.5"),
        _TestCheck(check_id="P1.1", dimension_id=1),
        _TestCheck(check_id="P10.1", dimension_id=10),
    ])
    # Note: lex-ASC means "P10.1" < "P1.1" < "P2.5" because '0' < '.' < '2'
    # — but the actual ordering depends on standard string lex comparison.
    # Let's check what Python gives us.
    expected = tuple(sorted(["P2.5", "P1.1", "P10.1"]))
    assert reg.ids() == expected


def test_make_registry_rejects_duplicate_check_ids():
    with pytest.raises(CheckRegistryError, match="duplicate"):
        make_registry([
            _TestCheck(check_id="P1.1"),
            _TestCheck(check_id="P1.1"),
        ])


def test_make_registry_rejects_empty_check_id():
    with pytest.raises(CheckRegistryError):
        make_registry([_TestCheck(check_id="")])


def test_make_registry_rejects_non_int_dimension_id():
    @dataclass(frozen=True)
    class BadCheck:
        check_id: str = "P1.1"
        dimension_id: str = "one"  # type: ignore[assignment]
        epistemic_kind: CheckEpistemicKind = CheckEpistemicKind.ARCHITECTURAL_HEURISTIC
        data_dependencies: tuple[str, ...] = ()
        cultural_scope: frozenset[CulturalProfile] | None = None
        def evaluate(self, context: CheckContext): return None
    with pytest.raises(CheckRegistryError, match="dimension_id"):
        make_registry([BadCheck()])  # type: ignore[list-item]


def test_make_registry_empty_input_is_valid():
    reg = make_registry([])
    assert len(reg) == 0
    assert reg.ids() == ()


# =============================================================================
# CheckRegistry — direct construction defenses
# =============================================================================

def test_registry_rejects_non_tuple_checks():
    with pytest.raises(TypeError, match="tuple"):
        CheckRegistry(
            checks=[_TestCheck(check_id="P1.1")],  # type: ignore[arg-type]
            _check_id_set=frozenset(["P1.1"]),
        )


def test_registry_rejects_unsorted_checks():
    with pytest.raises(CheckRegistryError, match="sorted lex-ASC"):
        CheckRegistry(
            checks=(_TestCheck(check_id="P2.1"), _TestCheck(check_id="P1.1")),
            _check_id_set=frozenset(["P1.1", "P2.1"]),
        )


def test_registry_rejects_mismatched_check_id_set():
    with pytest.raises(CheckRegistryError, match="_check_id_set mismatch"):
        CheckRegistry(
            checks=(_TestCheck(check_id="P1.1"),),
            _check_id_set=frozenset(["P1.1", "P9.9"]),  # extra
        )


def test_registry_is_frozen():
    reg = make_registry([_TestCheck(check_id="P1.1")])
    with pytest.raises(FrozenInstanceError):
        reg.checks = ()  # type: ignore[misc]


# =============================================================================
# CheckRegistry — query API
# =============================================================================

def test_registry_contains_returns_true_for_registered():
    reg = make_registry([_TestCheck(check_id="P1.1"), _TestCheck(check_id="P2.1", dimension_id=2)])
    assert reg.contains("P1.1") is True
    assert reg.contains("P2.1") is True


def test_registry_contains_returns_false_for_unregistered():
    reg = make_registry([_TestCheck(check_id="P1.1")])
    assert reg.contains("P9.9") is False


def test_registry_get_returns_registered_check():
    c1 = _TestCheck(check_id="P1.1")
    c2 = _TestCheck(check_id="P2.1", dimension_id=2)
    reg = make_registry([c1, c2])
    assert reg.get("P1.1") is c1
    assert reg.get("P2.1") is c2


def test_registry_get_raises_on_unregistered():
    reg = make_registry([_TestCheck(check_id="P1.1")])
    with pytest.raises(CheckRegistryError, match="not registered"):
        reg.get("P9.9")


def test_registry_iteration_is_lex_asc():
    reg = make_registry([
        _TestCheck(check_id="P3.1", dimension_id=3),
        _TestCheck(check_id="P1.1"),
        _TestCheck(check_id="P2.1", dimension_id=2),
    ])
    iter_ids = [c.check_id for c in reg]
    assert iter_ids == sorted(iter_ids)


def test_registry_len_matches_check_count():
    reg = make_registry([
        _TestCheck(check_id="P1.1"),
        _TestCheck(check_id="P1.2"),
        _TestCheck(check_id="P1.3"),
    ])
    assert len(reg) == 3


# =============================================================================
# build_registry — canonical C15 registry
# =============================================================================

def test_build_registry_returns_check_registry():
    reg = build_registry()
    assert isinstance(reg, CheckRegistry)


def test_build_registry_contains_all_dim_checks():
    """C15 build complete: registry now ships all 41 checks across
    10 dimensions (Sub-2 shipped dim 1 only; Sub-3+ added dims 2-10)."""
    reg = build_registry()
    expected_count = 41
    assert len(reg) == expected_count, (
        f"Expected {expected_count} registered checks across 10 dimensions; got {len(reg)}."
    )
    # Spot-check dim 1 still present
    for cid in ("P1.1", "P1.2", "P1.3", "P1.4"):
        assert reg.contains(cid)
    # Spot-check other dims present
    for cid in ("P2.1", "P3.1", "P5.1", "P6.1", "P7.1", "P10.3"):
        assert reg.contains(cid)


def test_build_registry_all_checks_satisfy_check_protocol():
    reg = build_registry()
    for c in reg:
        assert isinstance(c, Check), (
            f"Registered check {c.check_id!r} does not satisfy Check "
            f"protocol — missing required attribute or method."
        )


def test_build_registry_check_ids_match_dimension_ids():
    """check_id 'P{N}.{M}' implies dimension_id == N."""
    reg = build_registry()
    for c in reg:
        prefix = c.check_id.split(".")[0]
        expected_dim = int(prefix.lstrip("P"))
        assert c.dimension_id == expected_dim


def test_build_registry_is_deterministic():
    reg1 = build_registry()
    reg2 = build_registry()
    assert reg1.ids() == reg2.ids()
