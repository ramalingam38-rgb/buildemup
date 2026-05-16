# C9 / FloorRoomBrief — Amendment for C12 Consumption — v0.1

**Component**: C9 Room Sizer / `domain/floor_brief.py` `FloorRoomBrief`

**Origin**: Filed as `B-C9-ADJACENCY-HINTS` in C12 v0.2 PROPOSED Walk #2 amendments (S43). C12 v1 LOCK candidacy depends on this amendment landing.

**Status**: v0.1 PROPOSED → **LOCKED via S43 directive** (Ramalingam: "Let's do the dependencies on c8&c9 and code that also" — interpreted as combined LOCK + code authorization for both routed dependencies).

**Authority**: S43 author's draft; LOCK by Ramalingam's S43 directive cited above.

**Scope**: minimal-surface addition. Default empty tuple preserves byte-identical behaviour for existing callers (no test regression).

---

## § 1 — Motivation

C12 v0.2 Amendment A5 introduced a HARD/SOFT typing scheme for adjacency hints (e.g., kitchen↔dining = HARD, study↔library = SOFT). C12's slicing-tree placement consumes these hints to reject placements that violate HARD adjacencies and to bias placements toward satisfying SOFT ones.

Adjacency knowledge is naturally an **input** to layout (cultural / functional / brief-derived), not an output. The cleanest home is `FloorRoomBrief` — already shared across C5 / C8 / C9 / C12, already per-floor.

This amendment adds a typed `adjacency_hints` field to `FloorRoomBrief` with a default empty tuple for backward compatibility.

---

## § 2 — Contract addition

### § 2.1 — New schema types

```python
class AdjacencyConstraintKind(str, enum.Enum):
    """v1 two-level typing per C12 v0.2 Amendment A5.

    HARD = critical functional/cultural adjacency; violation → C12
           rejects the placement.
    SOFT = preference; violation → C14 scores down, C12 doesn't reject.

    Reviewer-suggested four-level enum (HARD/SOFT/PREFERRED/AVOID)
    is over-engineered for v1; two levels cover the genuine
    architectural distinction. PREFERRED/AVOID can be added in a
    future amendment without breaking v1 (additive enum extension).
    """
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class AdjacencyHint:
    """One pairwise adjacency hint between two rooms on the same floor.

    Identified by ``room_a_id`` and ``room_b_id``; canonical form
    requires room_a_id < room_b_id lex-ASC (validated in __post_init__).
    """
    room_a_id: str
    room_b_id: str
    kind: AdjacencyConstraintKind
    weight: float = 1.0  # for SOFT only; ignored when HARD

    def __post_init__(self) -> None:
        if not self.room_a_id or not self.room_b_id:
            raise ValueError("AdjacencyHint requires non-empty room ids.")
        if self.room_a_id == self.room_b_id:
            raise ValueError(
                f"AdjacencyHint requires distinct rooms; "
                f"got {self.room_a_id!r} twice."
            )
        if self.room_a_id > self.room_b_id:
            raise ValueError(
                f"AdjacencyHint requires canonical order "
                f"room_a_id < room_b_id; got {self.room_a_id!r} > "
                f"{self.room_b_id!r}. Construct as "
                f"AdjacencyHint(room_a_id={self.room_b_id!r}, "
                f"room_b_id={self.room_a_id!r}, ...)"
            )
        if self.weight < 0.0:
            raise ValueError(
                f"AdjacencyHint.weight must be >= 0; got {self.weight}."
            )
```

### § 2.2 — Field addition on FloorRoomBrief

```python
@dataclass(frozen=True)
class FloorRoomBrief:
    # ... existing fields unchanged ...
    has_master_bedroom: bool = True

    # NEW v0.1 amendment for B-C9-ADJACENCY-HINTS:
    adjacency_hints: tuple[AdjacencyHint, ...] = ()
    """Per-floor adjacency hints consumed by C12 placement.

    Default empty tuple preserves byte-identical behaviour for every
    existing single-floor caller (no test regression).

    Canonical ordering invariant (enforced in __post_init__):
    sorted lex-ASC by (room_a_id, room_b_id) so the brief's hash is
    deterministic across ordering permutations of the same hint set.
    """
```

---

## § 3 — Behavioural contract

- **Default behaviour unchanged**: `FloorRoomBrief(...)` constructed without `adjacency_hints` yields `adjacency_hints == ()` — exactly the current behaviour. No upstream caller change required.
- **Canonical hint ordering** is enforced in `__post_init__`: the tuple must be sorted lex-ASC by `(room_a_id, room_b_id)` so that two briefs with the same hint set in different order hash identically.
- **Duplicate detection**: two `AdjacencyHint`s on the same `(room_a_id, room_b_id)` pair raise `ValueError`. The same pair cannot be both HARD and SOFT.

---

## § 4 — Invariants

- **Inv D**: Every `AdjacencyHint` has `room_a_id < room_b_id` lex-ASC.
- **Inv E**: `FloorRoomBrief.adjacency_hints` is sorted lex-ASC by `(room_a_id, room_b_id)`.
- **Inv F**: No two `AdjacencyHint`s in the same brief share the same `(room_a_id, room_b_id)` pair.
- **Inv G**: `AdjacencyHint.weight >= 0.0`.

---

## § 5 — Test coverage targets

- ~5 construction tests: HARD/SOFT enum values; canonical-order enforcement; duplicate detection; same-room rejection; negative-weight rejection.
- ~3 brief-integration tests: default empty tuple preserves equality; sorted-tuple-required enforcement; duplicate-pair raises.
- ~2 backward-compat tests: existing FloorRoomBrief construction without `adjacency_hints` yields `() == ()`; existing brief hash/equality unchanged.

---

## § 6 — Backward compatibility

- No existing FloorRoomBrief fields modified or removed.
- `adjacency_hints: tuple = ()` is purely additive. Existing constructors continue to work because the new field has a default.
- Existing FloorRoomBrief hash/equality semantics extend cleanly (empty tuple vs empty tuple equal; non-empty changes hash, as expected).

---

## § 7 — Cache-key considerations (cross-component note)

C11a's cache-key version (`C11A_CACHE_KEY_VERSION`) currently captures FloorRoomBrief's contribution. Adding a new field to a frozen dataclass changes the hash. C11a SHOULD bump its cache-key version on adopting this amendment.

Filed inline as `B-C11A-CACHE-KEY-BUMP-ADJACENCY` (ROUTED to C11a maintainers; trigger: this amendment's code lands).

---

## § 8 — Status

**LOCKED via S43 directive.** Ready for code application.

Cross-component dependency: C12 v1 LOCK depends on this amendment + the C8 amendment landing.
