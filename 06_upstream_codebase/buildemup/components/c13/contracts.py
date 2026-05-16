"""
BuildemUp — Component 13 — contracts (Protocol abstractions)
=============================================================

Per C13 SPEC v1.0 LOCKED, composed from:
- v0.2 A5 (routed C12 v1.1 amendment for edge_type)
- v0.3 B5 (Protocol abstraction decoupling C13 from raw C12 schema)
- v0.4 C3 (C13_EDGE_PROTOCOL_VERSION + semantic-conformance PBTs)

The Protocol abstraction is the architectural backbone of C13's
release-train decoupling from C12. v0.3 B5 rationale:

> "v0.2's direct schema reference is replaced by structural typing.
> A future C12 v1.2 amendment that adds, say, acoustic_isolation_db
> to SharedEdge does NOT trigger a C13 amendment because that field
> isn't in the Protocol."

C13 binds against C13ConsumesFromC12Edge — not the raw C12.SharedEdge
dataclass. This module also provides C12V10EdgeAdapter for the v1.0
SharedEdge schema (which lacks edge_type), keeping C13 buildable
before B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (v0.2 A5) ships in C12 v1.1.

When C12 v1.1 lands with native SharedEdge.edge_type, callers may pass
real C12 v1.1 SharedEdge instances directly (structural typing) and
the adapter becomes optional.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Protocol, runtime_checkable


# =============================================================================
# EdgeType enum (per C13 v0.2 A5 / v0.3 B5)
# =============================================================================

class EdgeType(Enum):
    """Per C13 v0.2 A5 + v0.3 B5. Categorization of shared-edge
    relationship to the building envelope.

    INTERNAL: edge between two interior rooms (the v1.0 SharedEdge
        default; no envelope adjacency).

    EXTERNAL_ENVELOPE: edge touches the envelope perimeter. Required
        for main-entry door placement (Phase A entry-room selection
        prefers EXTERNAL_ENVELOPE edges).

    SERVICE: service-entry or utility-access boundary (e.g., back door
        to utility yard). v1 treats these as candidates for secondary
        doors on utility / kitchen rooms.

    BALCONY: semi-external (balcony / verandah). Door placement permitted
        but main entry SHOULD NOT route through balcony at v1 (cultural
        + weather-egress conventions).

    Routed to C12 as B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT (HIGH priority,
    additive MINOR bump to C12 v1.1). Until C12 v1.1 lands, C13 uses
    C12V10EdgeAdapter to assign edge_type to v1.0 SharedEdge instances.
    """
    INTERNAL = "internal"
    EXTERNAL_ENVELOPE = "external_envelope"
    SERVICE = "service"
    BALCONY = "balcony"


# =============================================================================
# C13ConsumesFromC12Edge — the canonical Protocol C13 binds against
# =============================================================================

@runtime_checkable
class C13ConsumesFromC12Edge(Protocol):
    """The fields C13 reads from C12's SharedEdge contract.

    Frozen at C13 v1.0 LOCK. Future C12 SharedEdge additions don't
    break C13 unless they change THESE fields' SEMANTICS (in which
    case C13_EDGE_PROTOCOL_VERSION bumps per v0.4 C3).

    Per v0.3 B5: structural typing replaces direct C12 dataclass
    reference. Any object with these attributes (and matching
    semantics) satisfies the Protocol — duck typing at the type
    layer.

    Per v0.4 C3 C13_EDGE_PROTOCOL_VERSION semantics:
    - Field NAMES are LOCKED at v1.0
    - Field SEMANTICS are LOCKED at v1.0; semantic change → version bump
    - New fields added to upstream are IGNORED (Protocol doesn't widen)

    Semantic-conformance PBTs (per v0.4 C3): ≥1 PBT per Protocol field
    verifies the upstream C12 implementation conforms to documented
    semantics across 3+ adversarial generators.
    """

    @property
    def room_a_id(self) -> str:
        """The lex-ASC-first room id of the two rooms sharing this edge.
        Per C12 SharedEdge invariant: room_a_id < room_b_id."""
        ...

    @property
    def room_b_id(self) -> str:
        """The lex-ASC-second room id of the two rooms sharing this edge."""
        ...

    @property
    def axis(self) -> Literal["vertical", "horizontal"]:
        """Which axis the shared wall runs along. Matches C12 SharedEdge.axis."""
        ...

    @property
    def overlap_start_m(self) -> float:
        """Start of the overlap interval along the edge axis (m).
        Grid-snapped per C12 v0.2-A4 / DEFAULT_GRID_SNAP_M."""
        ...

    @property
    def overlap_end_m(self) -> float:
        """End of the overlap interval along the edge axis (m).
        Grid-snapped. End - start == overlap_length_m."""
        ...

    @property
    def overlap_length_m(self) -> float:
        """Length of the shared edge available for door placement (m).
        Determines max door position + clear_width."""
        ...

    @property
    def min_required_clear_width_m(self) -> float:
        """NBC 2016 doorway minimum for the room-category pair (m).
        Per C12 v0.2-A9 / v0.4-A2. Door clear_width_m MUST be >= this."""
        ...

    @property
    def doorway_feasible(self) -> bool:
        """True iff this edge can accommodate an NBC-compliant doorway
        (length >= min_required_clear_width_m + corner_offset budget).
        C13 treats False edges as ineligible for door placement."""
        ...

    @property
    def edge_type(self) -> EdgeType:
        """Per v0.3 B5 + v0.2 A5. Categorization of envelope-relationship.

        For C12 v1.0 SharedEdge instances (which lack this field), use
        C12V10EdgeAdapter to compute the value (default INTERNAL,
        EXTERNAL_ENVELOPE if room_b_id == 'EXTERNAL' placeholder).

        Once C12 v1.1 ships native edge_type, callers may pass real
        SharedEdge instances directly (structural typing handles both)."""
        ...


# =============================================================================
# C12 v1.0 adapter — keeps C13 buildable before C12 v1.1 ships
# =============================================================================

# Placeholder room_id signaling envelope-boundary edges in C12 v1.0
# (per v0.1 § 3.1 step 2 original sentinel approach). C12 v1.0
# placement does not natively emit such edges; this is a forward-
# compat placeholder for caller-injected envelope adapter scenarios
# (e.g., test harnesses constructing synthetic envelope edges).
EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID: str = "EXTERNAL"


class C12V10EdgeAdapter:
    """Adapter wrapping a C12 v1.0 SharedEdge (which has no edge_type).

    Per v0.3 B5 Protocol-decoupling: C13 binds against
    C13ConsumesFromC12Edge. C12 v1.0 SharedEdge structurally satisfies
    8 of 9 Protocol fields but lacks edge_type. This adapter computes
    edge_type from the wrapped instance:

    - room_b_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID → EXTERNAL_ENVELOPE
    - otherwise → INTERNAL

    Once B-C12-EXTERNAL-EDGE-TYPE-AMENDMENT lands in C12 v1.1, native
    SharedEdge.edge_type will be available and this adapter becomes
    optional (or upgraded to passthrough).

    The adapter is INTENTIONALLY NOT a frozen dataclass — it's a
    lightweight proxy that forwards attribute access. Hashing /
    equality semantics are delegated to the underlying instance via
    __hash__ + __eq__ delegation.

    Per v0.4 C3 protocol-version semantics: this adapter ships at
    C13_EDGE_PROTOCOL_VERSION = 1. A future C12 v1.1 that changes
    edge_type meaning will bump both the C12 version and (potentially)
    C13_EDGE_PROTOCOL_VERSION; the adapter would migrate accordingly.
    """

    __slots__ = ("_underlying",)

    def __init__(self, underlying: object) -> None:
        """Wrap a C12 v1.0 SharedEdge.

        Validates that the underlying object exposes the 8 v1.0
        SharedEdge attributes the Protocol depends on (excluding
        edge_type, which the adapter supplies).
        """
        required = (
            "room_a_id",
            "room_b_id",
            "axis",
            "overlap_start_m",
            "overlap_end_m",
            "overlap_length_m",
            "min_required_clear_width_m",
            "doorway_feasible",
        )
        missing = [attr for attr in required if not hasattr(underlying, attr)]
        if missing:
            raise TypeError(
                f"C12V10EdgeAdapter: underlying object missing required "
                f"C12 v1.0 SharedEdge attributes: {missing!r}."
            )
        object.__setattr__(self, "_underlying", underlying)

    @property
    def room_a_id(self) -> str:
        return self._underlying.room_a_id  # type: ignore[attr-defined]

    @property
    def room_b_id(self) -> str:
        return self._underlying.room_b_id  # type: ignore[attr-defined]

    @property
    def axis(self) -> Literal["vertical", "horizontal"]:
        return self._underlying.axis  # type: ignore[attr-defined]

    @property
    def overlap_start_m(self) -> float:
        return self._underlying.overlap_start_m  # type: ignore[attr-defined]

    @property
    def overlap_end_m(self) -> float:
        return self._underlying.overlap_end_m  # type: ignore[attr-defined]

    @property
    def overlap_length_m(self) -> float:
        return self._underlying.overlap_length_m  # type: ignore[attr-defined]

    @property
    def min_required_clear_width_m(self) -> float:
        return self._underlying.min_required_clear_width_m  # type: ignore[attr-defined]

    @property
    def doorway_feasible(self) -> bool:
        return self._underlying.doorway_feasible  # type: ignore[attr-defined]

    @property
    def edge_type(self) -> EdgeType:
        """Per v0.3 B5 + v0.2 A5 adapter logic.

        If room_b_id matches the EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID
        sentinel, the edge is treated as EXTERNAL_ENVELOPE.

        Otherwise INTERNAL is returned. v1.0 SharedEdge does not
        emit SERVICE / BALCONY classifications; those require C12 v1.1.
        """
        if self.room_b_id == EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID:
            return EdgeType.EXTERNAL_ENVELOPE
        return EdgeType.INTERNAL

    def __repr__(self) -> str:
        return (
            f"C12V10EdgeAdapter(room_a_id={self.room_a_id!r}, "
            f"room_b_id={self.room_b_id!r}, edge_type={self.edge_type.value!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, C12V10EdgeAdapter):
            return NotImplemented
        return self._underlying == other._underlying

    def __hash__(self) -> int:
        # Mirror the underlying's hash for cache-key stability.
        return hash(self._underlying)


__all__ = [
    "EdgeType",
    "C13ConsumesFromC12Edge",
    "C12V10EdgeAdapter",
    "EXTERNAL_ENVELOPE_PLACEHOLDER_ROOM_ID",
]
