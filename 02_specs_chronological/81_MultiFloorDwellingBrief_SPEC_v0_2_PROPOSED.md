# MULTI-FLOOR DWELLING BRIEF SPEC v0.2 PROPOSED — domain dataclass for multi-floor residential briefs (B-NEW-T3 enabler #1 of 4)

**Component**: NEW domain dataclass (lives at `buildemup/domain/multi_floor_brief.py`).
**Spec status**: **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: "we will go by path C... I want option b multi floor and let's get the spec locked first."
**Authored**: S40-continuation, post-B-NEW-T3 scope discovery + post-v0.1 critique walk.
**Driver**: First of four locked specs needed before B-NEW-T3 can build. Foundational — the other three specs (C9 amendment v0.8, `MultiFloorWetZonePlannedCandidate`, C11a amendment v1.1) all depend on this type existing.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v0.2 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v0_2_LOCKED.md` (if approved as-is),
- `..._v0_3_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

---

## § 0.1 — Delta from v0.1 → v0.2 (critique walk patches)

v0.1 PROPOSED received an external critique with 14 items (4 CRITICAL/MAJOR
spec patches accepted, 5 MODERATE, 4 minor). Verdicts and patches landed:

| Item | Verdict | Patch site |
|---|---|---|
| CRITICAL-1 (master is floor-level only) | ACCEPT | New `master_bedroom_selector` reserved field; new Inv MFDB-6 |
| CRITICAL-2 (no "exactly one master" invariant) | ACCEPT | New Inv MFDB-5; new `floor_has_master(label)` helper |
| MAJOR-1 (label normalization) | ACCEPT | Normalize-at-construction via `object.__setattr__` in `__post_init__` |
| MAJOR-2 (ordering wording inconsistency) | ACCEPT | § 3.5 rewritten |
| MAJOR-3 (`get_floor` O(n)) | PARTIAL | Backlog file (B-MFDB-F); no schema change |
| MAJOR-4 (no livability validation) | ACCEPT (clarifying) | Explicit "non-livable floors permitted" + new § 3.7 + utility-floor example |
| MODERATE-1 (duck-typing fragility) | ACCEPT | Transitional-compat note in § 4; backlog B-MFDB-G |
| MODERATE-2 (no master-flag iteration helper) | ACCEPT | New `iter_floors_with_master_flag()` helper |
| MODERATE-3 (error msg representation leakage) | REJECT (file only) | Backlog B-MFDB-H |
| MODERATE-4 (no serialization contract) | ACCEPT | New § 3.8 "no canonical serialization in v0.1" |
| MINOR-1 (`with_master_on` naming) | REJECT | None |
| MINOR-2 (singleton master assumption) | ACCEPT | § 6 non-goal addition |
| MINOR-3 (`has_floor` convenience) | REJECT | None |
| MINOR-4 (non-residential floor example) | ACCEPT | Merged into MAJOR-4 patch |

Three rejects, all push-backs documented in their respective sections.

---

## § 1 — Why this spec exists

S40's empirical scope check for B-NEW-T3 (M8 multi-floor real upstream wiring)
revealed that **multi-floor support does not exist in the codebase**:

- `FloorRoomBrief` (`buildemup/domain/floor_brief.py`) is single-floor — has
  `floor_label: str = "ground"` plus scalar room counts; no `is_multi_floor`
  flag, no `floors` collection, no master-bedroom-floor identifier.
- C11a's `_is_multi_floor()` orchestrator helper duck-types for either an
  `is_multi_floor` attribute or a `floors` collection on the brief — but the
  real `FloorRoomBrief` has neither, so it always returns False.
- C9's `_materialise_rooms` hardcodes `is_master = (i == 0)` for the first
  bedroom — correct for single-floor but wrong for multi-floor (in a multi-
  floor dwelling, exactly ONE floor's bedrooms include "the master").

Per Path C ("do things properly") + Option B ("full multi-floor support, not
single-floor candidates with multi-floor brief context"), the codebase needs
a real domain type to express the multi-floor concept.

**This spec defines that type.** Three downstream specs build on it:
1. C9 amendment v0.8 — adds `has_master_bedroom: bool = True` to `FloorRoomBrief` so per-floor C9 calls know whether to treat the first bedroom as master.
2. `MultiFloorWetZonePlannedCandidate` spec — output-side wrapper that holds per-floor `WetZonePlannedCandidate`s plus dwelling-level state.
3. C11a amendment v1.1 — pipeline becomes multi-floor-aware (orchestrator surface accepts multi-floor; signature/cache/lineage/operators all updated).

---

## § 2 — Schema

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator, Literal

from buildemup.domain.floor_brief import FloorRoomBrief


# v0.1: only one selector strategy supported. The Literal type encodes
# the single-value constraint at the type level. Future amendments may
# widen this Literal (e.g., to "explicit_id" or "largest_area"); doing
# so will require a separate v0.X amendment + cache-key version bump.
MasterBedroomSelector = Literal["first_bedroom"]


@dataclass(frozen=True)
class MultiFloorDwellingBrief:
    """Multi-floor residential dwelling brief.

    Wraps a tuple of single-floor FloorRoomBrief instances plus dwelling-
    level state: which floor's bedrooms include the master, and how the
    master room within that floor is selected.

    Single-floor dwellings continue to use ``FloorRoomBrief`` directly
    (this type is for multi-floor only — see Inv MFDB-1).

    Frozen + hashable for cache-key stability (C11a cache.py keys on
    structural signatures derived in part from the brief).

    Note on master semantics (Inv MFDB-6): in v0.1 the wrapper identifies
    only WHICH FLOOR contains the master. WHICH ROOM on that floor is the
    master is delegated to the C9 room materialization convention via
    ``master_bedroom_selector``. v0.1 supports a single selector value
    (``"first_bedroom"``), matching the existing C9 ``is_master = (i == 0)``
    convention. The reserved field exists so v2 selectors (e.g., explicit
    room ID, largest area) can be added without breaking signatures.

    Note on label normalization (MAJOR-1 patch): floor labels are normalized
    at construction (lowercased, stripped, internal-whitespace collapsed to
    underscore). This protects cache and signature stability against trivial
    variants like "Ground" / "ground " / "ground floor". See § 3.1 for the
    canonical normalization function.
    """

    floors: tuple[FloorRoomBrief, ...]
    master_bedroom_floor_label: str
    master_bedroom_selector: MasterBedroomSelector = "first_bedroom"

    def __post_init__(self) -> None:
        # ---- MAJOR-1 patch: normalize floor labels first, then validate.
        # Use object.__setattr__ since the dataclass is frozen.
        normalized_floors = tuple(
            self._normalize_floor(f) for f in self.floors
        )
        normalized_master = _normalize_label(self.master_bedroom_floor_label)
        object.__setattr__(self, "floors", normalized_floors)
        object.__setattr__(self, "master_bedroom_floor_label", normalized_master)

        # ---- Inv MFDB-1: multi-floor means at least 2 floors.
        if len(self.floors) < 2:
            raise ValueError(
                f"MultiFloorDwellingBrief requires len(floors) >= 2; "
                f"got {len(self.floors)}. Single-floor dwellings should "
                f"use FloorRoomBrief directly."
            )

        # ---- Inv MFDB-2: floor labels must be unique (post-normalization).
        labels = [f.floor_label for f in self.floors]
        if len(set(labels)) != len(labels):
            raise ValueError(
                f"MultiFloorDwellingBrief: floor_label must be unique "
                f"across floors after normalization; got {labels!r}."
            )

        # ---- Inv MFDB-3: master_bedroom_floor_label must be one of the floors.
        if self.master_bedroom_floor_label not in labels:
            raise ValueError(
                f"MultiFloorDwellingBrief: master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r} not in floor labels "
                f"{labels!r}."
            )

        # ---- Inv MFDB-4: master floor must have at least 1 bedroom.
        master_floor = next(
            f for f in self.floors
            if f.floor_label == self.master_bedroom_floor_label
        )
        if master_floor.bedroom_count < 1:
            raise ValueError(
                f"MultiFloorDwellingBrief: master floor "
                f"{self.master_bedroom_floor_label!r} has bedroom_count="
                f"{master_floor.bedroom_count}; need >= 1 to host the "
                f"master bedroom."
            )

        # Inv MFDB-5 and MFDB-6 are derivation contracts; see § 3.2.
        # They do not require runtime checks beyond what the fields above
        # already enforce — but they are documented invariants that
        # downstream code MUST honour (C11a orchestrator, C9 amendment).

    # ----- Read helpers -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True for this type (Inv MFDB-1 enforces len >= 2).

        Exposed as a property so C11a's existing duck-typed
        ``_is_multi_floor()`` helper detects the type without needing
        an isinstance check. See § 4 / MODERATE-1 for the transitional-
        compatibility note.
        """
        return True

    def get_floor(self, label: str) -> FloorRoomBrief:
        """Return the floor brief for the given label.

        Label is normalized before lookup so callers can pass the
        unnormalized form. Raises KeyError if no floor has that label.

        Note (MAJOR-3 acknowledgement): this is O(n) over floors. For
        residential multi-floor (typically 1-4 floors, rarely > 6) this
        is fine. A lookup-map optimization is filed as B-MFDB-F
        (trigger: stress fuzz hot-path cost OR commercial path with
        >= 10 floors).
        """
        normalized = _normalize_label(label)
        for f in self.floors:
            if f.floor_label == normalized:
                return f
        raise KeyError(
            f"MultiFloorDwellingBrief.get_floor({label!r}): no floor with "
            f"that label (normalized={normalized!r}); available: "
            f"{[f.floor_label for f in self.floors]!r}"
        )

    @property
    def floor_labels(self) -> tuple[str, ...]:
        """Convenience: tuple of all (normalized) floor labels in tuple order."""
        return tuple(f.floor_label for f in self.floors)

    def floor_has_master(self, label: str) -> bool:
        """Canonical derivation: does the given floor host the master bedroom?

        CRITICAL-2 patch: centralizes the comparison so downstream code
        (C9 amendment, C11a orchestrator) does not re-implement the
        ``label == self.master_bedroom_floor_label`` check independently.
        Honours Inv MFDB-5 — exactly one floor returns True.

        Label is normalized before comparison.
        """
        return _normalize_label(label) == self.master_bedroom_floor_label

    def iter_floors_with_master_flag(
        self,
    ) -> Iterator[tuple[FloorRoomBrief, bool]]:
        """Iterate floors yielding ``(floor_brief, has_master_bedroom)``.

        MODERATE-2 patch: canonical iterator for the C11a orchestrator's
        per-floor execution loop. The bool is True for exactly one floor
        per Inv MFDB-5.

        Iteration order matches ``self.floors`` tuple order (see § 3.5
        on ordering semantics).
        """
        for f in self.floors:
            yield f, self.floor_has_master(f.floor_label)

    # ----- Mutation helpers (return new instances; type is frozen) -----

    def with_master_on(self, new_floor_label: str) -> MultiFloorDwellingBrief:
        """Return a new MultiFloorDwellingBrief with master moved to the
        given floor. Used by M8 in C11a.

        New label is normalized. Raises ValueError if (after normalization)
        the new floor label isn't one of the floors, or if the target
        floor has bedroom_count == 0.
        """
        normalized = _normalize_label(new_floor_label)
        if normalized not in self.floor_labels:
            raise ValueError(
                f"with_master_on({new_floor_label!r}): not a floor label "
                f"(normalized={normalized!r}); available: {self.floor_labels!r}"
            )
        # Re-construct so __post_init__ re-validates Inv MFDB-4.
        return MultiFloorDwellingBrief(
            floors=self.floors,
            master_bedroom_floor_label=normalized,
            master_bedroom_selector=self.master_bedroom_selector,
        )

    # ----- Internal helpers -----

    @staticmethod
    def _normalize_floor(f: FloorRoomBrief) -> FloorRoomBrief:
        """Normalize a floor's label without mutating other fields.

        Frozen FloorRoomBrief requires dataclasses.replace.
        """
        from dataclasses import replace
        return replace(f, floor_label=_normalize_label(f.floor_label))


def _normalize_label(label: str) -> str:
    """Canonical floor-label normalization.

    Rules (MAJOR-1 patch):
      1. Lowercase.
      2. Strip leading/trailing whitespace.
      3. Collapse internal whitespace runs to a single underscore.
      4. Reject empty (or all-whitespace) input.

    This produces stable cache/signature keys: "Ground", "ground ",
    "GROUND FLOOR", "  ground  floor  " all → "ground_floor".

    Raises ValueError if the result is empty.
    """
    if not isinstance(label, str):
        raise TypeError(
            f"floor_label must be str; got {type(label).__name__}: {label!r}"
        )
    stripped = label.strip().lower()
    if not stripped:
        raise ValueError(
            f"floor_label cannot be empty or whitespace-only; got {label!r}"
        )
    # Collapse internal whitespace runs to single underscore.
    parts = stripped.split()
    return "_".join(parts)
```

---

## § 3 — Behavioral contract

### § 3.1 — Construction

Callers always construct via the dataclass constructor. The
`__post_init__` validation is the only guard; there is no factory function.

**Floor labels are normalized** at construction (MAJOR-1 patch). Any of
`"Ground"`, `"ground "`, `"GROUND FLOOR"`, `" ground  floor "` becomes
the canonical `"ground_floor"`. Callers SHOULD pass already-normalized
labels for clarity, but the normalization is forgiving.

Example (typical G+1 dwelling, master on ground):

```python
ground = FloorRoomBrief(
    bedroom_count=2, bathroom_count=1,
    has_kitchen=True, has_living=True,
    has_pooja=False, has_utility=False,
    floor_label="ground",
)
first = FloorRoomBrief(
    bedroom_count=2, bathroom_count=1,
    has_kitchen=False, has_living=False,
    has_pooja=False, has_utility=False,
    floor_label="first",
)
brief = MultiFloorDwellingBrief(
    floors=(ground, first),
    master_bedroom_floor_label="ground",
)
# brief.master_bedroom_selector defaults to "first_bedroom".
```

Example (G+2 with utility floor, master on first floor):

```python
ground = FloorRoomBrief(
    bedroom_count=1, bathroom_count=1,
    has_kitchen=True, has_living=True,
    has_pooja=False, has_utility=False,
    floor_label="ground",
)
first = FloorRoomBrief(
    bedroom_count=2, bathroom_count=1,    # master will be the first
    has_kitchen=False, has_living=False,  # bedroom on this floor.
    has_pooja=False, has_utility=False,
    floor_label="first",
)
terrace_utility = FloorRoomBrief(
    bedroom_count=0, bathroom_count=0,        # MAJOR-4 / MINOR-4 patch:
    has_kitchen=False, has_living=False,      # non-livable floors are
    has_pooja=False, has_utility=True,        # PERMITTED (see § 3.7).
    floor_label="terrace",
)
brief = MultiFloorDwellingBrief(
    floors=(ground, first, terrace_utility),
    master_bedroom_floor_label="first",
)
```

### § 3.2 — Invariants

Six invariants total. MFDB-1 through MFDB-4 are runtime-enforced in
`__post_init__`. MFDB-5 and MFDB-6 are derivation/coupling contracts —
canonical statements of intent that downstream specs (C9 amendment,
C11a v1.1) MUST honour.

| Inv ID | Rule | Enforcement |
|---|---|---|
| **MFDB-1** | `len(floors) >= 2` | Runtime (`ValueError`) — single-floor must use `FloorRoomBrief` directly |
| **MFDB-2** | `floor_label` unique across floors (post-normalization) | Runtime (`ValueError`) |
| **MFDB-3** | `master_bedroom_floor_label ∈ floor labels` (post-normalization) | Runtime (`ValueError`) |
| **MFDB-4** | Master floor has `bedroom_count >= 1` | Runtime (`ValueError`) |
| **MFDB-5** | Exactly one floor has master bedroom (the one matching `master_bedroom_floor_label`); all others do NOT | Derivation contract — `floor_has_master()` is the single source of truth. Downstream code MUST derive from this method, not re-implement comparison. |
| **MFDB-6** | Master designation is FLOOR-LEVEL ONLY in v0.1; WHICH ROOM on the master floor is the master is delegated to C9 via `master_bedroom_selector="first_bedroom"` (the only v0.1 value) | Coupling contract — C9 amendment v0.8 honours this by treating "first bedroom on a floor with `has_master_bedroom=True`" as master. v2 selectors require a separate amendment + cache-key bump. |

### § 3.3 — Read helpers

| Helper | Purpose |
|---|---|
| `is_multi_floor` (property, always `True`) | Lets C11a's duck-typed `_is_multi_floor()` detect this type without explicit isinstance |
| `get_floor(label) -> FloorRoomBrief` | Lookup by label (label normalized before lookup); raises `KeyError` if missing. O(n); see B-MFDB-F |
| `floor_labels` (property) | Tuple of normalized labels in tuple order |
| **`floor_has_master(label) -> bool`** (CRITICAL-2 patch) | Canonical derivation; downstream code MUST use this rather than re-implement comparison |
| **`iter_floors_with_master_flag()`** (MODERATE-2 patch) | Iterator yielding `(floor, has_master)` pairs; canonical for orchestrator per-floor loops |

### § 3.4 — Mutation helper

- `with_master_on(new_floor_label) -> MultiFloorDwellingBrief`: returns a
  new instance with master moved. Re-runs `__post_init__` on the new
  instance, so the target floor's bedroom_count is re-validated. M8 in
  C11a uses this to compute the post-mutation brief.

This is the ONLY mutation helper; other shape changes (adding/removing a
floor, changing per-floor briefs) are out-of-scope for v1 (filed in § 7).

### § 3.5 — Floor ordering semantics (MAJOR-2 patch — REWRITTEN)

Floor ordering in the `floors` tuple has **two distinct properties**:

1. **Topological correctness**: NONE. C11a's pipeline does NOT depend on
   floor ordering for correctness — all operations look up floors by label.
   Reordering `(ground, first)` to `(first, ground)` produces a brief that
   yields the same downstream pipeline behaviour for any per-floor or
   dwelling-level operation.

2. **Structural identity**: YES. Tuple ordering DOES affect dataclass
   equality, hash value, and consequently any cache key or signature
   derived from the brief. `(ground, first)` and `(first, ground)` are
   NOT equal as `MultiFloorDwellingBrief` instances and produce different
   hashes, even though they're topologically identical.

This is intentional. v0.1 does not canonicalize ordering pre-hash because:
- Inferring "natural" elevation order from labels is fragile (`"ground"`
  vs `"first"` vs `"1F"` vs `"level_0"` etc.).
- Adding `floor_elevation_m` is post-v1 commercial path (B-MFDB-A).
- Callers are expected to construct floors in a consistent order
  (ground-up convention recommended) which makes the structural-identity
  issue moot in practice.

**Recommended convention** (NOT enforced): order floors ground-up
(ground, first, second, ..., terrace). Callers consistent with this
convention will not see ordering-induced cache fragmentation.

If a future commercial path needs canonicalization, the cleanest path is
to add `floor_elevation_m` to `FloorRoomBrief` and canonicalize tuple
ordering on construction. That's filed as B-MFDB-A.

### § 3.6 — Frozen + hashable

`@dataclass(frozen=True)` with a `tuple[FloorRoomBrief, ...]` field, two
scalar string fields (one a Literal). Hashability follows from
`FloorRoomBrief` being frozen + hashable (already true) and tuple/string/
Literal being hashable.

Required for use as cache keys in C11a's `cache.py`.

### § 3.7 — Non-livable floors are permitted (MAJOR-4 patch — NEW SECTION)

A floor with `bedroom_count=0`, `bathroom_count=0`, no kitchen, no
living room, no pooja, etc. is **valid** in `MultiFloorDwellingBrief`.
Such floors are common in real Indian residential dwellings: terraces,
utility floors, water-tank floors, parking floors.

Constraints (already enforced via existing invariants):
- The MASTER floor (the one matching `master_bedroom_floor_label`) MUST
  have `bedroom_count >= 1` (Inv MFDB-4). All other floors may be empty
  shells.
- Floor labels must still be unique (Inv MFDB-2).

The brief itself does NOT impose minimum-livability rules at the dwelling
level (e.g., "must have at least one kitchen across all floors"). That
kind of cross-floor sanity check is downstream's responsibility (C9 may
reject specific configurations; C5 topology selection may filter
non-livable-overall briefs). This spec keeps domain definitions and
livability heuristics separated.

### § 3.8 — No canonical serialization in v0.1 (MODERATE-4 patch — NEW SECTION)

This spec does NOT define a canonical serialization format
(JSON, msgpack, protobuf, SQL row, etc.). v0.1 is for in-memory
domain-object use only.

Persistence and API serialization are deferred. Once they're needed
(e.g., when C1 brief-capture submits multi-floor briefs over HTTP, or
when cache state survives process restarts), a separate amendment will
define the canonical format including:
- tuple ordering preservation,
- selector field migration,
- cross-version compatibility windows,
- canonical labeling on serialize/deserialize round-trip.

This non-binding clause prevents accidental implicit serialization
contracts from solidifying via ad-hoc usage.

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Identify master by floor `label` (string)** | ✅ | Reject: by index. Index breaks if floors tuple reorders. Label is stable. |
| **Master designation lives on the wrapper, not on `FloorRoomBrief`** | ✅ | Reject: `FloorRoomBrief.is_master_floor: bool`. Per-floor master flag duplicates info and risks divergence (two floors both with True). Wrapper-level single-source-of-truth is cleaner. C9 still needs a per-call signal — that's Spec #2's `has_master_bedroom: bool = True` field, computed at orchestration time via `iter_floors_with_master_flag()`. |
| **Master is FLOOR-level + reserved selector field for v2 room-level** (CRITICAL-1 patch) | ✅ | Reject: omit selector field; rely on undocumented C9 first-bedroom convention. Hidden coupling fails Pattern C (scores-without-truth). The reserved `master_bedroom_selector: Literal["first_bedroom"]` makes the v0.1 selector explicit and gives v2 (e.g., explicit-room-id, largest-area) a non-breaking extension path. Single-value Literal type encodes the v0.1 constraint at the type level. |
| **Min floors = 2** | ✅ | Reject: min = 1. Allowing single-floor multi-floor brief creates a "should I use the wrapper or not" decision at every call site. Sharper rule: multi-floor wrapper for multi-floor dwellings; single `FloorRoomBrief` otherwise. |
| **Frozen dataclass** | ✅ | Reject: mutable. C11a cache keys + signature stability require immutability. Mutation goes through `with_master_on()` which returns a new instance. |
| **`with_master_on` returns new instance** | ✅ | Reject: in-place. Frozen dataclass requires this; also matches `dataclasses.replace` idiom used elsewhere. |
| **Floor labels normalized at construction** (MAJOR-1 patch) | ✅ | Reject: leave labels raw; document a convention. Cache fragmentation from `"Ground"` vs `"ground"` is real and one-line of `__post_init__` normalization eliminates it cheaply. Reject: enforce strict format (e.g., regex). The normalize-and-accept approach is forgiving for the C1 brief-capture API and still produces stable downstream keys. |
| **`floor_has_master(label)` helper as canonical derivation** (CRITICAL-2 patch) | ✅ | Reject: let downstream code re-implement `label == brief.master_bedroom_floor_label` ad hoc. Centralization prevents orchestration drift across C9 amendment + C11a amendment + future code. |
| **`iter_floors_with_master_flag()` helper** (MODERATE-2 patch) | ✅ | Reject: leave the loop pattern to each caller. Same orchestration-drift argument as above; cheap helper. |
| **Duck-typing via `is_multi_floor` property is transitional, not permanent** (MODERATE-1 patch) | ✅ | Reject: define a formal `Protocol` now. C11a v1.1 (Spec #4) is the right place for protocol typing; doing it here pre-empts that spec's design. v0.2 documents the transitional nature explicitly. |
| **No `add_floor` / `remove_floor` / `has_floor` / etc. helpers in v1** | ✅ | Defer to v2. v1 covers "fixed dwelling shape, swap master" — that's all M8 needs. Schema-evolution + extra convenience are v2 concerns. `has_floor` is one line (`label in brief.floor_labels`); not worth a method. |

---

## § 5 — Test plan

### § 5.1 — New test file

Create `buildemup/tests/test_domain_multi_floor_brief.py` with the following tests:

**Construction (happy path)**:
1. `test_two_floor_construction_succeeds`: typical G+1 with master on ground.
2. `test_three_floor_construction_succeeds`: G+2 dwelling.
3. `test_construction_with_master_on_first_floor`: non-default master placement.
4. `test_construction_with_utility_terrace_floor`: G+1+terrace where terrace has bedroom_count=0 (MAJOR-4 / MINOR-4 patch).
5. `test_default_selector_value_is_first_bedroom` (CRITICAL-1 patch): explicit field default check.

**Invariant violations**:
6. `test_single_floor_raises`: `floors=(ground,)` → `ValueError` (Inv MFDB-1).
7. `test_empty_floors_raises`: `floors=()` → `ValueError` (Inv MFDB-1).
8. `test_duplicate_floor_labels_raises`: two floors with same label → `ValueError` (Inv MFDB-2).
9. `test_duplicate_via_normalization_raises`: `"Ground"` and `"ground"` both passed → `ValueError` (Inv MFDB-2 post-normalization).
10. `test_master_label_not_in_floors_raises`: master = "basement" but no basement floor → `ValueError` (Inv MFDB-3).
11. `test_master_floor_has_zero_bedrooms_raises`: master on a floor with `bedroom_count=0` → `ValueError` (Inv MFDB-4).

**Label normalization** (MAJOR-1 patch):
12. `test_label_normalization_lowercase`: `"GROUND"` → `"ground"`.
13. `test_label_normalization_strip_whitespace`: `" ground "` → `"ground"`.
14. `test_label_normalization_collapse_internal_whitespace`: `"ground  floor"` → `"ground_floor"`.
15. `test_master_label_normalized_during_construction`: pass master = `"GROUND"`, observe stored = `"ground"`.
16. `test_empty_label_raises`: `floor_label=""` → `ValueError`.
17. `test_whitespace_only_label_raises`: `floor_label="   "` → `ValueError`.
18. `test_non_string_label_raises_type_error`: `floor_label=123` → `TypeError`.

**Read helpers**:
19. `test_is_multi_floor_property_is_true`: confirms property.
20. `test_get_floor_returns_correct_brief`: `get_floor("ground")` returns ground brief.
21. `test_get_floor_normalizes_input`: `get_floor("GROUND")` returns ground brief (post-normalization match).
22. `test_get_floor_unknown_label_raises_key_error`: `get_floor("nonexistent")` → `KeyError`.
23. `test_floor_labels_preserves_tuple_order`: confirms tuple-order preservation.
24. `test_floor_has_master_returns_true_for_master_floor` (CRITICAL-2 patch).
25. `test_floor_has_master_returns_false_for_non_master_floor` (CRITICAL-2 patch).
26. `test_floor_has_master_normalizes_input` (CRITICAL-2 patch).
27. `test_iter_floors_with_master_flag_yields_exactly_one_true` (MODERATE-2 patch — also Inv MFDB-5 sentinel).
28. `test_iter_floors_with_master_flag_preserves_tuple_order` (MODERATE-2 patch).

**Mutation helper**:
29. `test_with_master_on_returns_new_instance_with_swapped_master`: master swap.
30. `test_with_master_on_normalizes_input`: `with_master_on("FIRST")` → stored as `"first"`.
31. `test_with_master_on_unknown_floor_raises`: unknown label → `ValueError`.
32. `test_with_master_on_target_with_zero_bedrooms_raises`: target floor has `bedroom_count=0` → `ValueError` (re-runs Inv MFDB-4).
33. `test_with_master_on_does_not_mutate_original`: original brief unchanged after `with_master_on`.
34. `test_with_master_on_preserves_selector_value`: selector survives the operation.

**Frozen + equality + hashability**:
35. `test_two_briefs_with_same_content_are_equal`: dataclass equality.
36. `test_brief_is_hashable_for_dict_and_set_use`: confirms hashable.
37. `test_attempted_field_mutation_raises_frozen_instance_error`: `brief.master_bedroom_floor_label = "first"` → `FrozenInstanceError`.
38. `test_briefs_with_different_floor_order_are_not_equal` (MAJOR-2 patch sentinel): `(ground, first)` ≠ `(first, ground)` even though topologically identical.

**C11a `_is_multi_floor()` integration sentinel**:
39. `test_c11a_is_multi_floor_returns_true_for_this_type`: `_is_multi_floor(brief)` returns True via the `is_multi_floor` property.

**Selector field**:
40. `test_explicit_selector_first_bedroom_accepted` (CRITICAL-1 patch).
41. `test_unknown_selector_value_rejected_by_type_checker_or_runtime` (CRITICAL-1 patch — note: at v0.1 the Literal narrowing is type-time only; runtime accepts other strings unless we add a guard. Test confirms current behaviour and documents the limitation).

**Total**: 41 tests (up from 20 in v0.1; the increase is concentrated in
normalization, master-derivation helpers, selector field, and ordering
sentinels).

### § 5.2 — Existing test regression

Zero existing tests reference this type (it's NEW). Full project must
remain at **2760 passed / 2 skipped / 0 regressions** after this spec
ships.

---

## § 6 — Out-of-scope (what this spec does NOT do)

Per Pattern E (scope creep), the following are explicitly NOT in scope for
v0.2, even though they're related:

- **C9 amendment v0.8**: `has_master_bedroom: bool = True` on `FloorRoomBrief`. **Filed as separate spec** (Spec #2 of 4 in the B-NEW-T3 sequence).
- **`MultiFloorWetZonePlannedCandidate`**: output-side wrapper. **Filed as separate spec** (Spec #3 of 4).
- **C11a amendment v1.1**: orchestrator + pipeline rework. **Filed as separate spec** (Spec #4 of 4).
- **C1 brief capture API for multi-floor**: how the user provides multi-floor briefs from the front-end. Out of scope for the topology pipeline; future C1 amendment.
- **Floor-elevation tracking** (`floor_elevation_m`): post-v1 commercial path.
- **Per-floor staircase landing constraints** (e.g., "stairs must land on the same x,y on each floor"): post-v1, requires C7 / C8 amendments.
- **Mid-level, mezzanine, basement floors**: v1 supports rectangular ground-up multi-floor only.
- **Non-residential dwelling types** (mixed-use, commercial): post-v1.
- **Multiple master bedrooms / dual masters / owner suites** (MINOR-2 non-goal): v0.1 supports exactly ONE master designation globally per dwelling. Multi-master support is post-v1; would require widening the wrapper schema (set instead of single label) and revising Inv MFDB-5.
- **Runtime selector validation beyond Literal type-narrowing**: v0.1 relies on the `Literal["first_bedroom"]` for type-time narrowing; mypy/pyright will reject other strings, but runtime construction with `master_bedroom_selector="anything_else"` will succeed silently. Adding runtime validation of the selector against an enum is filed as B-MFDB-I.

---

## § 7 — Backlog items deferred to post-v0.2

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-MFDB-A** | `floor_elevation_m` on `FloorRoomBrief` for explicit elevation tracking (also enables tuple-order canonicalization) | When v2 commercial path needs floor heights | Open (post-v1) |
| **B-MFDB-B** | `add_floor` / `remove_floor` mutation helpers on `MultiFloorDwellingBrief` | When dwelling shape can change post-construction (probably never in v1; design-time only) | Open (post-v1) |
| **B-MFDB-C** | Per-floor staircase landing constraint (X,Y alignment across floors) | When multi-floor topologies need vertical circulation alignment | Open — requires C7 + C8 amendments |
| **B-MFDB-D** | C1 brief-capture API extension to construct multi-floor briefs from front-end input | When the brief-capture endpoint surfaces multi-floor option to users | Open — separate component (C1) |
| **B-MFDB-E** | Mid-level / basement / mezzanine floor support | v2 commercial path | Open (post-v1) |
| **B-MFDB-F** (NEW from MAJOR-3) | Lookup-map optimization: precompute `Mapping[label, FloorRoomBrief]` in `__post_init__` for O(1) `get_floor()` | Stress fuzz shows hot-path cost OR commercial path with >= 10 floors | Open (post-v1) |
| **B-MFDB-G** (NEW from MODERATE-1) | Migrate C11a's `_is_multi_floor()` from duck-typed `hasattr`/`is_multi_floor` to a formal `MultiFloorDwellingBriefProtocol` | When C11a amendment v1.1 (Spec #4) drafts protocol typing | Open — addressed in Spec #4 |
| **B-MFDB-H** (NEW from MODERATE-3) | Domain exception strategy for user-facing API surfaces (label representation, localization) | When domain types become directly user-facing through the C1 endpoint | Open (post-v1, gated on B-MFDB-D) |
| **B-MFDB-I** (NEW from § 6 last bullet) | Runtime validation of `master_bedroom_selector` against an enum/whitelist (not just Literal type-narrowing) | When v2 selectors are added (e.g., `"explicit_id"`, `"largest_area"`); the v0.1 single-value Literal makes this a no-op for now | Open (post-v1) |
| **B-MFDB-J** (NEW from MINOR-2 non-goal acknowledgement) | Multi-master / dual-master / owner-suite support (widen master designation from single label to set) | When v2 luxury / multi-family path requires it | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK declaration:

Spec v0.2 build scope (small, slightly larger than v0.1):
- 1 new file: `buildemup/domain/multi_floor_brief.py` (~165 lines incl.
  docstrings; up from ~110 in v0.1 because of normalization, helpers, and
  the selector field).
- 1 new test file: `buildemup/tests/test_domain_multi_floor_brief.py`
  (~41 tests).
- No modifications to existing code.

Estimated build effort: ~45-60 minutes of code, BUT this build will not
happen until Specs 2-3-4 are also LOCKED (per Ramalingam directive: "let's
get the spec locked first and then we will see about building the code").
So this spec's code lands as part of the eventual unified B-NEW-T3 build
session.

---

## § 9 — Status

- **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- **Authority**: Rule 8 — LOCK authority belongs to Ramalingam alone.
  Claude does not self-declare LOCK.
- **Patch-eligibility**: any critique surfaced before LOCK produces v0.3
  PROPOSED, not backlog (Rule 8 paragraph 4).
- **After LOCK**: spec drafting proceeds to Spec #2 (C9 amendment v0.8 —
  `has_master_bedroom` flag on `FloorRoomBrief`).
- **Code work**: deferred until all four specs LOCKED.

---

## § 10 — Rule 9 backlog enumeration

Per Rule 9 (backlog visibility inside spec): every backlog item this spec
depends on, references, or creates is enumerated below with full metadata.
§ 7 above lists this spec's own deferral items (B-MFDB-A through J). The
table below adds the cross-spec items relevant to this spec's role in the
B-NEW-T3 sequence.

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| **B-NEW-T3** | M8 multi-floor real upstream wiring. The spec's ultimate driver. | S39 critique walk F5 (split from B-NEW-T) | All four B-NEW-T3 specs LOCKED | **GATED**: needs all four specs (this one + #2 + #3 + #4) before code | L (~3-5 days build, post all-four-LOCK) |
| **B-NEW-T3-PRE** | Multi-floor schema gate (this spec sequence) | S40-continuation discovery (FloorRoomBrief is single-floor) | Specs 1-4 LOCKED | **IN-FLIGHT** — this is Spec #1 of 4 | M (~2-4 message rounds per spec, 4 specs total) |
| Spec #2 | C9 Amendment v0.8 — `has_master_bedroom: bool = True` on `FloorRoomBrief` | Same discovery | Spec #1 LOCKED | **NEXT** after this LOCKs | S |
| Spec #3 | `MultiFloorWetZonePlannedCandidate` domain spec | Same discovery | Spec #1 + #2 LOCKED | After Spec #2 | M |
| Spec #4 | C11a Amendment v1.1 — multi-floor pipeline rework | Same discovery | Specs #1-3 LOCKED | Last in sequence; LARGE | L |
| B-NEW-T1.5 | Promote M6 to real C10 re-run (independent) | S39 Sub-5 | Future C10 amendment | Out-of-scope for B-NEW-T3 sequence | M |
| B-NEW-Y full | Mutation chain accumulation (multi-floor stress-fuzzes once T3 lands) | S39 Sub-5 partial | After B-NEW-T3 complete | Gated on B-NEW-T3 | M |

**Summary**: this spec is the foundation of a 4-spec sequence for B-NEW-T3.
Pre-existing backlog items unaffected. v0.2 added 5 new deferral items
(B-MFDB-F, G, H, I, J), all post-v1.

---

**End of MultiFloorDwellingBrief Spec v0.2 PROPOSED.**
