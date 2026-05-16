# MULTI-FLOOR DWELLING BRIEF SPEC v0.1 PROPOSED — domain dataclass for multi-floor residential briefs (B-NEW-T3 enabler #1 of 4)

**Component**: NEW domain dataclass (lives at `buildemup/domain/multi_floor_brief.py`).
**Spec status**: **v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: "we will go by path C... I want option b multi floor and let's get the spec locked first."
**Authored**: S40-continuation, post-B-NEW-T3 scope discovery.
**Driver**: First of four locked specs needed before B-NEW-T3 can build. Foundational — the other three specs (C9 amendment v0.8, `MultiFloorWetZonePlannedCandidate`, C11a amendment v1.1) all depend on this type existing.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v0.1 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v0_1_LOCKED.md` (if approved as-is),
- `..._v0_2_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

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
1. C9 amendment v0.8 — adds `has_master_bedroom: bool = True` to
   `FloorRoomBrief` so per-floor C9 calls know whether to treat the first
   bedroom as master.
2. `MultiFloorWetZonePlannedCandidate` spec — output-side wrapper that holds
   per-floor `WetZonePlannedCandidate`s plus dwelling-level state.
3. C11a amendment v1.1 — pipeline becomes multi-floor-aware (orchestrator
   surface accepts multi-floor; signature/cache/lineage/operators all updated).

---

## § 2 — Schema

```python
from __future__ import annotations
from dataclasses import dataclass

from buildemup.domain.floor_brief import FloorRoomBrief


@dataclass(frozen=True)
class MultiFloorDwellingBrief:
    """Multi-floor residential dwelling brief.

    Wraps a tuple of single-floor FloorRoomBrief instances plus dwelling-
    level state (currently: which floor's bedrooms include the master).

    Single-floor dwellings continue to use ``FloorRoomBrief`` directly
    (this type is for multi-floor only — see Inv MFDB-1).

    Frozen + hashable for cache-key stability (C11a cache.py keys on
    structural signatures derived in part from the brief).
    """

    floors: tuple[FloorRoomBrief, ...]
    master_bedroom_floor_label: str

    def __post_init__(self) -> None:
        # Inv MFDB-1: multi-floor means at least 2 floors.
        if len(self.floors) < 2:
            raise ValueError(
                f"MultiFloorDwellingBrief requires len(floors) >= 2; "
                f"got {len(self.floors)}. Single-floor dwellings should "
                f"use FloorRoomBrief directly."
            )

        # Inv MFDB-2: floor labels must be unique.
        labels = [f.floor_label for f in self.floors]
        if len(set(labels)) != len(labels):
            raise ValueError(
                f"MultiFloorDwellingBrief: floor_label must be unique "
                f"across floors; got {labels!r}."
            )

        # Inv MFDB-3: master_bedroom_floor_label must be one of the floors.
        if self.master_bedroom_floor_label not in labels:
            raise ValueError(
                f"MultiFloorDwellingBrief: master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r} not in floor labels "
                f"{labels!r}."
            )

        # Inv MFDB-4: master floor must have at least 1 bedroom.
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

    # ----- Read helpers -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True for this type (Inv MFDB-1 enforces len >= 2).

        Exposed as a property so C11a's existing duck-typed
        ``_is_multi_floor()`` helper detects the type without needing
        an isinstance check.
        """
        return True

    def get_floor(self, label: str) -> FloorRoomBrief:
        """Return the floor brief for the given label.

        Raises KeyError if no floor has that label.
        """
        for f in self.floors:
            if f.floor_label == label:
                return f
        raise KeyError(
            f"MultiFloorDwellingBrief.get_floor({label!r}): no floor with "
            f"that label; available: "
            f"{[f.floor_label for f in self.floors]!r}"
        )

    @property
    def floor_labels(self) -> tuple[str, ...]:
        """Convenience: tuple of all floor labels in tuple order."""
        return tuple(f.floor_label for f in self.floors)

    # ----- Mutation helpers (return new instances; type is frozen) -----

    def with_master_on(self, new_floor_label: str) -> MultiFloorDwellingBrief:
        """Return a new MultiFloorDwellingBrief with master moved to the
        given floor. Used by M8 in C11a.

        Raises ValueError if the new floor label isn't one of the floors,
        or if the target floor has bedroom_count == 0.
        """
        if new_floor_label not in self.floor_labels:
            raise ValueError(
                f"with_master_on({new_floor_label!r}): not a floor label; "
                f"available: {self.floor_labels!r}"
            )
        # Re-construct so __post_init__ re-validates Inv MFDB-4.
        return MultiFloorDwellingBrief(
            floors=self.floors,
            master_bedroom_floor_label=new_floor_label,
        )
```

---

## § 3 — Behavioral contract

### § 3.1 — Construction

Callers always construct via the dataclass constructor. The
`__post_init__` validation is the only guard; there is no factory function.

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
```

### § 3.2 — Invariants enforced (all in `__post_init__`)

| Inv ID | Rule | Failure mode |
|---|---|---|
| MFDB-1 | `len(floors) >= 2` | `ValueError` (single-floor must use `FloorRoomBrief`) |
| MFDB-2 | `floor_label` unique across floors | `ValueError` |
| MFDB-3 | `master_bedroom_floor_label ∈ floor labels` | `ValueError` |
| MFDB-4 | Master floor has `bedroom_count >= 1` | `ValueError` |

### § 3.3 — Read helpers

- `is_multi_floor` (property): always True. Lets C11a's `_is_multi_floor()` detect this type via `hasattr` without explicit isinstance.
- `get_floor(label) -> FloorRoomBrief`: lookup by label; raises `KeyError` if missing.
- `floor_labels` (property): tuple of labels in tuple order (preserves declared ordering — see § 3.5).

### § 3.4 — Mutation helper

- `with_master_on(new_floor_label) -> MultiFloorDwellingBrief`: returns a new
  instance with master moved. Re-runs `__post_init__` on the new instance,
  so the target floor's bedroom_count is re-validated. M8 in C11a uses this
  to compute the post-mutation brief.

This is the ONLY mutation helper; other shape changes (adding/removing a
floor, changing per-floor briefs) are out-of-scope for v1 (filed in § 7).

### § 3.5 — Floor ordering convention (recommended, not enforced)

The `floors` tuple SHOULD be ordered ground-up: ground floor first, then
ascending. This is convention only — there's no runtime check, because
floor "elevation" isn't a field and inferring it from labels is fragile
(e.g., "ground" vs. "first" vs. "1F" vs. "level_0").

C11a's pipeline does NOT depend on floor ordering for correctness — all
operations look up floors by label. The convention is for human readability
and stable signature derivation.

If a v2 commercial path needs explicit elevation, add `floor_elevation_m`
to `FloorRoomBrief` (filed in § 7 backlog).

### § 3.6 — Frozen + hashable

`@dataclass(frozen=True)` with a `tuple[FloorRoomBrief, ...]` field and
two scalar fields. Hashability follows from `FloorRoomBrief` being
frozen + hashable (already true in v0.1) and tuple/string being hashable.

Required for use as cache keys in C11a's `cache.py`.

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Identify master by floor `label` (string)** | ✅ | Reject: by index. Index breaks if floors tuple reorders. Label is stable. |
| **Master designation lives on the wrapper, not on `FloorRoomBrief`** | ✅ | Reject: `FloorRoomBrief.is_master_floor: bool`. Per-floor master flag duplicates info and risks divergence (two floors both with True). Wrapper-level single-source-of-truth is cleaner. (However, C9 still needs a per-call "is this floor the master" signal — that's the C9 v0.8 amendment, which uses `has_master_bedroom: bool = True` field. The wrapper computes the per-floor flag at orchestration time.) |
| **Min floors = 2** | ✅ | Reject: min = 1. Allowing single-floor multi-floor brief creates a "should I use the wrapper or not" decision at every call site. Sharper rule: multi-floor wrapper for multi-floor dwellings; single `FloorRoomBrief` otherwise. |
| **Frozen dataclass** | ✅ | Reject: mutable. C11a cache keys + signature stability require immutability. Mutation goes through `with_master_on()` which returns a new instance. |
| **`with_master_on` returns new instance** | ✅ | Reject: in-place. Frozen dataclass requires this; also matches `dataclasses.replace` idiom used elsewhere. |
| **No `add_floor` / `remove_floor` helpers in v1** | ✅ | Defer to v2. v1 covers "fixed dwelling shape, swap master" — that's all M8 needs. Schema-evolution is a v2 concern. |

---

## § 5 — Test plan

### § 5.1 — New test file

Create `buildemup/tests/test_domain_multi_floor_brief.py` with the following tests:

**Construction (happy path)**:
1. `test_two_floor_construction_succeeds`: typical G+1 with master on ground.
2. `test_three_floor_construction_succeeds`: G+2 dwelling.
3. `test_construction_with_master_on_first_floor`: non-default master placement.

**Invariant violations**:
4. `test_single_floor_raises`: `floors=(ground,)` → `ValueError` (Inv MFDB-1).
5. `test_empty_floors_raises`: `floors=()` → `ValueError` (Inv MFDB-1).
6. `test_duplicate_floor_labels_raises`: two floors with same label → `ValueError` (Inv MFDB-2).
7. `test_master_label_not_in_floors_raises`: master = "basement" but no basement floor → `ValueError` (Inv MFDB-3).
8. `test_master_floor_has_zero_bedrooms_raises`: master on a floor with `bedroom_count=0` → `ValueError` (Inv MFDB-4).

**Read helpers**:
9. `test_is_multi_floor_property_is_true`: confirms property.
10. `test_get_floor_returns_correct_brief`: `get_floor("ground")` returns ground brief.
11. `test_get_floor_unknown_label_raises_key_error`: `get_floor("nonexistent")` → `KeyError`.
12. `test_floor_labels_preserves_tuple_order`: confirms tuple-order preservation.

**Mutation helper**:
13. `test_with_master_on_returns_new_instance_with_swapped_master`: master swap.
14. `test_with_master_on_unknown_floor_raises`: unknown label → `ValueError`.
15. `test_with_master_on_target_with_zero_bedrooms_raises`: target floor has `bedroom_count=0` → `ValueError` (re-runs Inv MFDB-4).
16. `test_with_master_on_does_not_mutate_original`: original brief unchanged after `with_master_on`.

**Frozen + equality + hashability**:
17. `test_two_briefs_with_same_content_are_equal`: dataclass equality.
18. `test_brief_is_hashable_for_dict_and_set_use`: confirms hashable.
19. `test_attempted_field_mutation_raises_frozen_instance_error`: `brief.master_bedroom_floor_label = "first"` → `FrozenInstanceError`.

**C11a `_is_multi_floor()` integration sentinel**:
20. `test_c11a_is_multi_floor_returns_true_for_this_type`: `_is_multi_floor(brief)` returns True via the `is_multi_floor` property.

**Total**: ~20 tests.

### § 5.2 — Existing test regression

Zero existing tests reference this type (it's NEW). Full project must
remain at **2760 passed / 2 skipped / 0 regressions** after this spec
ships.

---

## § 6 — Out-of-scope (what this spec does NOT do)

Per Pattern E (scope creep), the following are explicitly NOT in scope for
v0.1, even though they're related:

- **C9 amendment v0.8**: `has_master_bedroom: bool = True` on `FloorRoomBrief`. **Filed as separate spec** (Spec #2 of 4 in the B-NEW-T3 sequence).
- **`MultiFloorWetZonePlannedCandidate`**: output-side wrapper. **Filed as separate spec** (Spec #3 of 4).
- **C11a amendment v1.1**: orchestrator + pipeline rework. **Filed as separate spec** (Spec #4 of 4).
- **C1 brief capture API for multi-floor**: how the user provides multi-floor briefs from the front-end. Out of scope for the topology pipeline; future C1 amendment.
- **Floor-elevation tracking** (`floor_elevation_m`): post-v1 commercial path.
- **Per-floor staircase landing constraints** (e.g., "stairs must land on the same x,y on each floor"): post-v1, requires C7 / C8 amendments.
- **Mid-level, mezzanine, basement floors**: v1 supports rectangular ground-up multi-floor only.
- **Non-residential dwelling types** (mixed-use, commercial): post-v1.

---

## § 7 — Backlog items deferred to post-v0.1

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-MFDB-A** | `floor_elevation_m` on `FloorRoomBrief` for explicit elevation tracking | When v2 commercial path needs floor heights | Open (post-v1) |
| **B-MFDB-B** | `add_floor` / `remove_floor` mutation helpers on `MultiFloorDwellingBrief` | When dwelling shape can change post-construction (probably never in v1; design-time only) | Open (post-v1) |
| **B-MFDB-C** | Per-floor staircase landing constraint (X,Y alignment across floors) | When multi-floor topologies need vertical circulation alignment | Open — requires C7 + C8 amendments |
| **B-MFDB-D** | C1 brief-capture API extension to construct multi-floor briefs from front-end input | When the brief-capture endpoint surfaces multi-floor option to users | Open — separate component (C1) |
| **B-MFDB-E** | Mid-level / basement / mezzanine floor support | v2 commercial path | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK declaration:

Spec v0.1 build scope (small):
- 1 new file: `buildemup/domain/multi_floor_brief.py` (~110 lines incl. docstrings).
- 1 new test file: `buildemup/tests/test_domain_multi_floor_brief.py` (~20 tests).
- No modifications to existing code.

Estimated build effort: ~30-45 minutes of code, BUT this build will not happen until Specs 2-3-4 are also LOCKED (per Ramalingam directive: "let's get the spec locked first and then we will see about building the code"). So this spec's code lands as part of the eventual unified B-NEW-T3 build session.

---

## § 9 — Status

- **v0.1 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- **Authority**: Rule 8 — LOCK authority belongs to Ramalingam alone.
  Claude does not self-declare LOCK.
- **Patch-eligibility**: any critique surfaced before LOCK produces v0.2
  PROPOSED, not backlog (Rule 8 paragraph 4).
- **After LOCK**: spec drafting proceeds to Spec #2 (C9 amendment v0.8 —
  `has_master_bedroom` flag on `FloorRoomBrief`).
- **Code work**: deferred until all four specs LOCKED.

---

## § 10 — Rule 9 backlog enumeration

Per Rule 9 (backlog visibility inside spec): every backlog item this spec
depends on, references, or creates is enumerated below with full metadata.
§ 7 above lists this spec's own deferral items (B-MFDB-A through E). The
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
Pre-existing backlog items unaffected. New deferral items (B-MFDB-A..E) all
post-v1.

---

**End of MultiFloorDwellingBrief Spec v0.1 PROPOSED.**
