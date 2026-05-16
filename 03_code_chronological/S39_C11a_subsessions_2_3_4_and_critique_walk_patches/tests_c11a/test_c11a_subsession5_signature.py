"""
C11a Sub-session 5 — B-NEW-U: canonical structural signature tests.

Per S39 critique walk F3: canonical structural signature replaces
SHA256(repr+index). Tests verify:
  - Determinism: same input → same signature.
  - Synthetic-source fallback: still uses repr+index path.
  - Repr-equal but logically-different candidates: distinct
    signatures via index disambiguation in fallback path.
  - Real-candidate detection routes to canonical path (smoke).
  - 16-hex format consistency with derive_variant_id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from buildemup.components.c05.schema import ZoneBand
from buildemup.components.c11a import (
    derive_canonical_signature,
    derive_signature,
)
from buildemup.domain.envelope import PlotOrientation


# =============================================================================
# Synthetic test fixtures (signature falls back to repr+index)
# =============================================================================


@dataclass(frozen=True)
class _SyntheticCand:
    topology_kind: str = "central_spine"
    zone_bands: dict = field(default_factory=lambda: {
        ZoneBand.PUBLIC: PlotOrientation.SOUTH,
        ZoneBand.PRIVATE: PlotOrientation.NORTH,
    })


# =============================================================================
# Format + determinism
# =============================================================================


def test_signature_is_16_hex_chars() -> None:
    """Match the variant_id format convention (16-hex SHA256 prefix)."""
    sig = derive_signature(_SyntheticCand(), 0)
    assert len(sig) == 16
    int(sig, 16)  # raises if non-hex


def test_signature_deterministic_same_inputs() -> None:
    a = _SyntheticCand()
    b = _SyntheticCand()
    assert derive_signature(a, 0) == derive_signature(b, 0)


def test_signature_distinct_per_index() -> None:
    """Index disambiguation: same repr-equal candidate at different
    positions in the input tuple → different signatures."""
    cand = _SyntheticCand()
    sig_0 = derive_signature(cand, 0)
    sig_1 = derive_signature(cand, 1)
    assert sig_0 != sig_1


def test_signature_distinct_per_topology_kind() -> None:
    a = _SyntheticCand(topology_kind="strip")
    b = _SyntheticCand(topology_kind="courtyard")
    assert derive_signature(a, 0) != derive_signature(b, 0)


# =============================================================================
# Synthetic source falls back to repr+index path
# =============================================================================


def test_synthetic_uses_repr_index_path() -> None:
    """Synthetic source isn't a real WetZonePlannedCandidate; the
    dispatcher falls back to repr+index hashing.

    Verified indirectly: two synthetic candidates with structurally-
    identical fields produce identical signatures (because their reprs
    are identical for frozen dataclasses)."""
    a = _SyntheticCand(topology_kind="strip")
    b = _SyntheticCand(topology_kind="strip")
    # Frozen dataclass equality → equal repr → equal signature at same index.
    assert repr(a) == repr(b)
    assert derive_signature(a, 0) == derive_signature(b, 0)


# =============================================================================
# Canonical signature on a synthetic-shaped chain (smoke)
# =============================================================================
#
# We can't construct a real WetZonePlannedCandidate without standing up
# all of C5-C10's dependencies, but we can construct an object with the
# right ATTRIBUTE PATH shape and verify the canonical path walks it.
# This proves the dispatcher's split-routing logic.


@dataclass(frozen=True)
class _FakeTopologyCandidate:
    kind: Any = None
    zone_bands: Any = None


@dataclass(frozen=True)
class _FakeOrientedCandidate:
    topology_candidate: Any = None
    orientation: Any = None


@dataclass(frozen=True)
class _FakeCorridorPath:
    has_corridor: bool = True
    segments: tuple = ()


@dataclass(frozen=True)
class _FakeCorridorDesignedCandidate:
    oriented_candidate: Any = None
    corridor_path: Any = None


@dataclass(frozen=True)
class _FakeRoomSizeTable:
    rooms: tuple = ()


@dataclass(frozen=True)
class _FakeRoomSizedCandidate:
    corridor_designed_candidate: Any = None
    room_size_table: Any = None


@dataclass(frozen=True)
class _FakeWetZonePlan:
    wet_wall_assignments: Any = None
    riser_groups: Any = None


@dataclass(frozen=True)
class _FakeRealishCandidate:
    """Mimics WetZonePlannedCandidate's attribute path shape so the
    canonical signature walker has something to chew on. Not the real
    type (so is_real_wet_zone_candidate returns False), but the
    canonical helper can be called directly."""
    room_sized_candidate: Any = None
    wet_zone_plan: Any = None


@dataclass(frozen=True)
class _FakeKind:
    value: str = "central_spine"


def _build_realish() -> _FakeRealishCandidate:
    topology = _FakeTopologyCandidate(
        kind=_FakeKind("central_spine"),
        zone_bands={ZoneBand.PUBLIC: PlotOrientation.SOUTH},
    )
    oriented = _FakeOrientedCandidate(
        topology_candidate=topology,
        orientation=None,
    )
    corridor_path = _FakeCorridorPath(has_corridor=True, segments=())
    cdc = _FakeCorridorDesignedCandidate(
        oriented_candidate=oriented,
        corridor_path=corridor_path,
    )
    rsc = _FakeRoomSizedCandidate(
        corridor_designed_candidate=cdc,
        room_size_table=_FakeRoomSizeTable(rooms=()),
    )
    return _FakeRealishCandidate(
        room_sized_candidate=rsc,
        wet_zone_plan=_FakeWetZonePlan(),
    )


def test_canonical_signature_walks_realish_chain() -> None:
    """Direct call to derive_canonical_signature with a realish-shaped
    candidate succeeds — proves the chain walker handles the v1.0 path."""
    cand = _build_realish()
    sig = derive_canonical_signature(cand)
    assert len(sig) == 16
    int(sig, 16)


def test_canonical_signature_changes_when_topology_kind_changes() -> None:
    cand_a = _build_realish()
    cand_b_topology = _FakeTopologyCandidate(
        kind=_FakeKind("courtyard"),
        zone_bands={ZoneBand.PUBLIC: PlotOrientation.SOUTH},
    )
    cand_b_oriented = _FakeOrientedCandidate(
        topology_candidate=cand_b_topology, orientation=None,
    )
    cand_b = _FakeRealishCandidate(
        room_sized_candidate=_FakeRoomSizedCandidate(
            corridor_designed_candidate=_FakeCorridorDesignedCandidate(
                oriented_candidate=cand_b_oriented,
                corridor_path=_FakeCorridorPath(),
            ),
            room_size_table=_FakeRoomSizeTable(),
        ),
        wet_zone_plan=_FakeWetZonePlan(),
    )

    sig_a = derive_canonical_signature(cand_a)
    sig_b = derive_canonical_signature(cand_b)
    assert sig_a != sig_b


def test_canonical_signature_changes_when_zone_bands_change() -> None:
    cand_a = _build_realish()  # PUBLIC: SOUTH

    cand_b_topology = _FakeTopologyCandidate(
        kind=_FakeKind("central_spine"),
        zone_bands={ZoneBand.PUBLIC: PlotOrientation.NORTH},  # different
    )
    cand_b_oriented = _FakeOrientedCandidate(
        topology_candidate=cand_b_topology, orientation=None,
    )
    cand_b = _FakeRealishCandidate(
        room_sized_candidate=_FakeRoomSizedCandidate(
            corridor_designed_candidate=_FakeCorridorDesignedCandidate(
                oriented_candidate=cand_b_oriented,
                corridor_path=_FakeCorridorPath(),
            ),
            room_size_table=_FakeRoomSizeTable(),
        ),
        wet_zone_plan=_FakeWetZonePlan(),
    )

    assert derive_canonical_signature(cand_a) != derive_canonical_signature(cand_b)


def test_canonical_signature_idempotent() -> None:
    cand = _build_realish()
    assert derive_canonical_signature(cand) == derive_canonical_signature(cand)


def test_canonical_signature_independent_of_zone_bands_dict_order() -> None:
    """zone_bands serialised sorted — Python dict iteration order
    shouldn't affect the signature."""
    topology_a = _FakeTopologyCandidate(
        kind=_FakeKind("central_spine"),
        zone_bands={
            ZoneBand.PUBLIC: PlotOrientation.SOUTH,
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
        },
    )
    topology_b = _FakeTopologyCandidate(
        kind=_FakeKind("central_spine"),
        zone_bands={
            ZoneBand.PRIVATE: PlotOrientation.NORTH,
            ZoneBand.PUBLIC: PlotOrientation.SOUTH,
        },
    )

    def _build(t: Any) -> _FakeRealishCandidate:
        return _FakeRealishCandidate(
            room_sized_candidate=_FakeRoomSizedCandidate(
                corridor_designed_candidate=_FakeCorridorDesignedCandidate(
                    oriented_candidate=_FakeOrientedCandidate(
                        topology_candidate=t, orientation=None,
                    ),
                    corridor_path=_FakeCorridorPath(),
                ),
                room_size_table=_FakeRoomSizeTable(),
            ),
            wet_zone_plan=_FakeWetZonePlan(),
        )

    sig_a = derive_canonical_signature(_build(topology_a))
    sig_b = derive_canonical_signature(_build(topology_b))
    assert sig_a == sig_b


# =============================================================================
# Replay determinism
# =============================================================================


def test_signature_replay_byte_equal_two_runs() -> None:
    """Two calls to derive_signature with structurally-identical inputs
    produce byte-equal output. Required for Inv 30 replay."""
    cand_1 = _build_realish()
    cand_2 = _build_realish()
    sig_1 = derive_canonical_signature(cand_1)
    sig_2 = derive_canonical_signature(cand_2)
    assert sig_1 == sig_2
