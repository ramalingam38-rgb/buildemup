# MULTI-FLOOR DWELLING BRIEF SPEC v0.3 PROPOSED — domain dataclass for multi-floor residential briefs (B-NEW-T3 enabler #1 of 4)

**Component**: NEW domain dataclass (lives at `buildemup/domain/multi_floor_brief.py`).
**Spec status**: **v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: "we will go by path C... I want option b multi floor and let's get the spec locked first."
**Authored**: S40-continuation, post-v0.2 critique walk.
**Driver**: First of four locked specs needed before B-NEW-T3 can build.

---

## § 0 — LOCK declaration

**Pending.** Per Rule 8 (LOCK authority belongs to Ramalingam alone), Claude
NEVER self-declares LOCK. This file is `v0.3 PROPOSED`. After Ramalingam
adjudication, the next file in `02_specs_chronological/` will be either:
- `..._v0_3_LOCKED.md` (if approved as-is),
- `..._v0_4_PROPOSED.md` (if patches surfaced — Rule 8 patch-eligible
  until LOCK).

Critiques arriving between PROPOSED and LOCK remain patch-eligible → produce
v(N+1) PROPOSED, not backlog entries (per Rule 8 paragraph 4).

---

## § 0.1 — Delta from v0.2 → v0.3 (critique walk patches)

v0.2 PROPOSED received an external critique with 14 items. Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| CRITICAL-1 (nested FloorRoomBrief rewritten silently) | ACCEPT | § 2 docstring, § 3.1 explicit acknowledgement |
| CRITICAL-2 (runtime selector validation absent) | ACCEPT | § 2 schema (`__post_init__`); Inv MFDB-6 promoted to runtime-enforced |
| MAJOR-1 (normalization rules incomplete) | ACCEPT (clarification only) | § 2 docstring, § 3.1 — explicit non-aliasing scope |
| MAJOR-2 (two notions of identity unspecified per subsystem) | ACCEPT | § 3.5 — new per-subsystem canonicality table |
| MAJOR-3 (`iter_floors_with_master_flag` embeds orchestration policy) | PARTIAL — doc-only | § 3.3 — explicit "intentionally orchestration-oriented" |
| MAJOR-4 (pathological normalized labels permitted) | PARTIAL — doc + backlog | § 3.1 explicit; new B-MFDB-K |
| MODERATE-1 (hidden normalization dependency in helpers) | ACCEPT | § 3.3 wording |
| MODERATE-2 (no normalization-versioning contract) | ACCEPT | § 3.6 — cache-bump clause |
| MODERATE-3 (B-MFDB-I rationale inconsistent) | ACCEPT (moot after CRITICAL-2) | B-MFDB-I repurposed for v2 selector widening |
| MODERATE-4 (no cross-floor sanity warning) | ACCEPT | § 3.7 — explicit warning sentence |
| MINOR-1 (`field` import unused) | ACCEPT | § 2 — dropped |
| MINOR-2 (`selector` terminology) | REJECT | None — current name + docstring sufficient |
| MINOR-3 (`iter_floors_with_master_flag` name verbose) | REJECT | None — name precise |
| MINOR-4 (stray "v0.1" references) | ACCEPT | Throughout — replaced with "the current version" or version-specific where appropriate |
| MINOR-5 (no canonical non-livable-floor taxonomy) | BACKLOG ONLY | New B-MFDB-L |

**Selector error type choice**: `ValueError` (consistent with other invariants in `__post_init__`; explicit Ramalingam approval).

Three partial verdicts (MAJOR-3, MAJOR-4 partial; MODERATE-3 partial) and two full rejects (MINOR-2, MINOR-3) with reasoning preserved in § 4.

---

## § 1 — Why this spec exists

S40's empirical scope check for B-NEW-T3 (M8 multi-floor real upstream wiring) revealed that **multi-floor support does not exist in the codebase**:

- `FloorRoomBrief` (`buildemup/domain/floor_brief.py`) is single-floor — has `floor_label: str = "ground"` plus scalar room counts; no `is_multi_floor` flag, no `floors` collection, no master-bedroom-floor identifier.
- C11a's `_is_multi_floor()` orchestrator helper duck-types for either an `is_multi_floor` attribute or a `floors` collection on the brief — but the real `FloorRoomBrief` has neither, so it always returns False.
- C9's `_materialise_rooms` hardcodes `is_master = (i == 0)` for the first bedroom — correct for single-floor but wrong for multi-floor.

Per Path C ("do things properly") + Option B ("full multi-floor support"), the codebase needs a real domain type to express the multi-floor concept.

**This spec defines that type.** Three downstream specs build on it:
1. C9 amendment v0.8 — adds `has_master_bedroom: bool = True` to `FloorRoomBrief`.
2. `MultiFloorWetZonePlannedCandidate` spec — output-side wrapper.
3. C11a amendment v1.1 — pipeline becomes multi-floor-aware.

---

## § 2 — Schema

```python
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterator, Literal

from buildemup.domain.floor_brief import FloorRoomBrief


# v0.3: only one selector strategy supported. The Literal type encodes
# the single-value constraint at the type level, AND __post_init__
# enforces it at runtime (CRITICAL-2 patch). Future amendments may widen
# this Literal (e.g., to "explicit_id" or "largest_area"); doing so will
# require a separate v0.X amendment + cache-key version bump.
MasterBedroomSelector = Literal["first_bedroom"]

# Tuple of all currently-permitted selector values. Single-element in
# v0.3; widened in future amendments. Used for runtime validation
# (Inv MFDB-6).
_VALID_SELECTORS: tuple[str, ...] = ("first_bedroom",)


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

    NOTE on master semantics (Inv MFDB-6): the wrapper identifies only
    WHICH FLOOR contains the master. WHICH ROOM on that floor is the
    master is delegated to the C9 room materialization convention via
    ``master_bedroom_selector``. The current version supports a single
    selector value (``"first_bedroom"``), runtime-enforced. The reserved
    field exists so v2 selectors can be added without breaking signatures.

    NOTE on label normalization (MAJOR-1 in v0.2 critique walk): floor
    labels are normalized at construction (lowercased, stripped, internal-
    whitespace collapsed to underscore). This protects cache and signature
    stability against trivial variants like "Ground" / "ground " /
    "ground floor". See § 3.1 for exact normalization rules and their
    deliberate non-coverage of semantic aliases (e.g., "first" vs "1F"
    remain distinct labels).

    NOTE on nested-object rewrite (CRITICAL-1 in v0.2 critique walk):
    construction REWRITES nested FloorRoomBrief instances by reconstructing
    them with normalized labels. ``brief.floors[0]`` is NOT the same Python
    object as the FloorRoomBrief passed in — it's a dataclass-replaced
    sibling. Callers who hold references to the original FloorRoomBrief
    objects MUST NOT assume identity preservation. Equality of contents
    holds (modulo the label normalization).

    NOTE on construction-vs-plausibility: construction success does NOT
    imply architectural plausibility (MODERATE-4 in v0.2 critique walk).
    A brief whose floors all lack kitchens is structurally valid but
    architecturally degenerate. Cross-floor sanity is downstream's
    responsibility (C5 topology selection, C9 room sizing).
    """

    floors: tuple[FloorRoomBrief, ...]
    master_bedroom_floor_label: str
    master_bedroom_selector: MasterBedroomSelector = "first_bedroom"

    def __post_init__(self) -> None:
        # ---- Normalize floor labels first, then validate.
        # Use object.__setattr__ since the dataclass is frozen.
        # NB (CRITICAL-1): this rewrites nested FloorRoomBrief instances
        # using dataclasses.replace; original objects are NOT preserved.
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

        # ---- Inv MFDB-6 RUNTIME GUARD (CRITICAL-2 patch):
        # selector must be one of the currently-permitted values.
        # Type-time narrowing via Literal is necessary but not sufficient
        # because runtime inputs may bypass the type checker (JSON,
        # fuzzing, dynamic code paths).
        if self.master_bedroom_selector not in _VALID_SELECTORS:
            raise ValueError(
                f"MultiFloorDwellingBrief: master_bedroom_selector="
                f"{self.master_bedroom_selector!r} not in valid selectors "
                f"{_VALID_SELECTORS!r}. Adding new selector values requires "
                f"a separate spec amendment + cache-key version bump."
            )

        # Inv MFDB-5 is a derivation contract; see § 3.2. It does not
        # require runtime checks beyond what MFDB-3 + MFDB-4 already
        # guarantee (the master_bedroom_floor_label points to exactly
        # one floor; floor_has_master() returns True for exactly that
        # floor and False for all others).

    # ----- Read helpers -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True for this type (Inv MFDB-1 enforces len >= 2).

        Exposed as a property so C11a's existing duck-typed
        ``_is_multi_floor()`` helper detects the type without needing
        an isinstance check. See § 4 for the transitional-compatibility note.
        """
        return True

    def get_floor(self, label: str) -> FloorRoomBrief:
        """Return the floor brief for the given label.

        Label is normalized before lookup so callers can pass the
        unnormalized form (MODERATE-1 — public lookup helpers normalize
        inputs; stored identity remains exact normalized strings).
        Raises KeyError if no floor has that label.

        Note (MAJOR-3 in v0.1 critique walk): this is O(n) over floors.
        For residential multi-floor (typically 1-4 floors, rarely > 6)
        this is fine. Lookup-map optimization is filed as B-MFDB-F.
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

        Centralizes the comparison so downstream code (C9 amendment, C11a
        orchestrator) does not re-implement the
        ``label == self.master_bedroom_floor_label`` check independently.
        Honours Inv MFDB-5 — exactly one floor returns True.

        Label is normalized before comparison (MODERATE-1 in v0.2 critique
        walk — public lookup helpers normalize; stored identity remains
        exact normalized strings).
        """
        return _normalize_label(label) == self.master_bedroom_floor_label

    def iter_floors_with_master_flag(
        self,
    ) -> Iterator[tuple[FloorRoomBrief, bool]]:
        """Iterate floors yielding ``(floor_brief, has_master_bedroom)``.

        DESIGN NOTE (MAJOR-3 in v0.2 critique walk): this iteration helper
        is INTENTIONALLY orchestration-oriented. It zips the existing
        ``floors`` field with the canonical ``floor_has_master()`` derivation
        so downstream orchestration code (C9 amendment input prep, C11a
        per-floor pipeline loops) does not re-implement the pairing
        independently. This is layering-blur but the cost-of-not-doing-it
        (orchestration drift across multiple call sites re-implementing the
        same zip) outweighs the architectural purity gain. If a future
        amendment introduces a dedicated orchestration adapter layer, this
        method may be relocated there.

        The bool is True for exactly one floor per Inv MFDB-5. Iteration
        order matches ``self.floors`` tuple order (see § 3.5).
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
        # Re-construct so __post_init__ re-validates Inv MFDB-4 and MFDB-6.
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

        NB (CRITICAL-1 in v0.2 critique walk): this is structural rewrite,
        not in-place mutation. The returned FloorRoomBrief is a different
        Python object than ``f``.
        """
        return replace(f, floor_label=_normalize_label(f.floor_label))


def _normalize_label(label: str) -> str:
    """Canonical floor-label normalization.

    Rules:
      1. Lowercase.
      2. Strip leading/trailing whitespace.
      3. Collapse internal whitespace runs to a single underscore.
      4. Reject empty (or all-whitespace) input.
      5. Reject non-string input.

    SCOPE (MAJOR-1 in v0.2 critique walk):
    These rules ONLY protect against trivial whitespace/case variants.
    They do NOT canonicalize semantic aliases. The following are all
    DISTINCT labels under v0.3 normalization:
      "first", "1F", "first_floor", "level_1", "fl1", "1st"
    Callers needing semantic-alias unification must canonicalize before
    construction.

    The character set is intentionally unrestricted (MAJOR-4 in v0.2
    critique walk): pathological strings like "@@@_floor" or "___" are
    valid normalized labels. Sanitization for downstream display is the
    consumer's responsibility (filed as B-MFDB-K).

    DETERMINISM CONTRACT (MODERATE-2 in v0.2 critique walk):
    This function's behaviour is part of the cache/signature protocol.
    Any change to normalization semantics in a future amendment REQUIRES
    a cache-key version bump (e.g., increment ``C11A_CACHE_KEY_VERSION``
    in C11a) so persisted/in-flight caches invalidate cleanly.

    Raises:
      TypeError if input is not a str.
      ValueError if the result is empty.
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

**Floor labels are normalized** at construction. Any of `"Ground"`,
`"ground "`, `"GROUND FLOOR"`, `" ground  floor "` becomes the canonical
`"ground_floor"`. Callers SHOULD pass already-normalized labels for clarity,
but the normalization is forgiving.

**Normalization scope is limited**: only whitespace and case variants are
unified. Semantic aliases (`"first"` vs `"1F"` vs `"first_floor"`) remain
distinct. If a caller needs alias unification (e.g., from a free-form
front-end input), the canonicalization must happen before construction.

**Character set is unrestricted**: pathological labels like `"@@@_floor"`
or `"___"` are structurally valid. They produce stable cache keys but ugly
display strings. Sanitization-for-display is the consumer's responsibility
(B-MFDB-K).

**Nested FloorRoomBrief instances are rewritten**: construction reconstructs
each floor via `dataclasses.replace` to apply label normalization. The
returned `MultiFloorDwellingBrief.floors[i]` is NOT the same Python object
as the i-th element of the input tuple. Equality of contents holds (modulo
label normalization). Callers MUST NOT rely on object identity.

**Construction success does NOT imply architectural plausibility.** A brief
whose floors all lack kitchens is valid by these invariants but degenerate
as a dwelling. Cross-floor sanity is downstream's responsibility.

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
# brief.floors[0] is NOT the same object as `ground` (rewritten for normalization).
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
    bedroom_count=0, bathroom_count=0,    # Non-livable floors are
    has_kitchen=False, has_living=False,  # PERMITTED (see § 3.7).
    has_pooja=False, has_utility=True,
    floor_label="terrace",
)
brief = MultiFloorDwellingBrief(
    floors=(ground, first, terrace_utility),
    master_bedroom_floor_label="first",
)
```

### § 3.2 — Invariants

Six invariants total. MFDB-1 through MFDB-4 and MFDB-6 are runtime-enforced
in `__post_init__`. MFDB-5 is a derivation contract — guaranteed by
MFDB-3 + MFDB-4 + the canonical `floor_has_master()` helper.

| Inv ID | Rule | Enforcement |
|---|---|---|
| **MFDB-1** | `len(floors) >= 2` | Runtime (`ValueError`) — single-floor must use `FloorRoomBrief` directly |
| **MFDB-2** | `floor_label` unique across floors (post-normalization) | Runtime (`ValueError`) |
| **MFDB-3** | `master_bedroom_floor_label ∈ floor labels` (post-normalization) | Runtime (`ValueError`) |
| **MFDB-4** | Master floor has `bedroom_count >= 1` | Runtime (`ValueError`) |
| **MFDB-5** | Exactly one floor has master bedroom (the one matching `master_bedroom_floor_label`); all others do NOT | Derivation contract — `floor_has_master()` is the single source of truth. Guaranteed by MFDB-3 + MFDB-4 + helper implementation. |
| **MFDB-6** | Master designation is FLOOR-LEVEL ONLY in v0.3; WHICH ROOM on the master floor is the master is delegated to C9 via `master_bedroom_selector` (only `"first_bedroom"` permitted in v0.3). RUNTIME-ENFORCED — invalid selectors raise `ValueError` (CRITICAL-2 patch from v0.2 critique walk) | Runtime (`ValueError`) AND coupling contract — C9 amendment v0.8 honours this by treating "first bedroom on a floor with `has_master_bedroom=True`" as master. v2 selectors require a separate amendment + cache-key bump. |

### § 3.3 — Read helpers

| Helper | Purpose | Normalization behaviour |
|---|---|---|
| `is_multi_floor` (property, always `True`) | Lets C11a's duck-typed `_is_multi_floor()` detect this type without explicit isinstance | n/a |
| `get_floor(label) -> FloorRoomBrief` | Lookup by label; raises `KeyError` if missing. O(n); see B-MFDB-F | Normalizes input |
| `floor_labels` (property) | Tuple of normalized labels in tuple order | Returns stored canonical form |
| `floor_has_master(label) -> bool` | Canonical master derivation | Normalizes input |
| `iter_floors_with_master_flag()` | INTENTIONALLY orchestration-oriented; yields `(floor, has_master)` for canonical per-floor loops | n/a (uses stored canonical labels) |

**Public lookup helpers normalize inputs**; stored identity (the strings
in `floor_labels` and `master_bedroom_floor_label`) remains exact canonical
form. This means callers can pass `"GROUND"`, `"ground "`, etc. to
`get_floor` / `floor_has_master` / `with_master_on` without explicit
pre-normalization, but reading back from `floor_labels` gives them the
canonical form.

### § 3.4 — Mutation helper

- `with_master_on(new_floor_label) -> MultiFloorDwellingBrief`: returns a
  new instance with master moved. Re-runs `__post_init__` on the new
  instance, so the target floor's bedroom_count is re-validated AND the
  selector is re-validated. M8 in C11a uses this to compute the
  post-mutation brief.

This is the ONLY mutation helper; other shape changes are out-of-scope
for v1.

### § 3.5 — Floor ordering semantics

Floor ordering in the `floors` tuple has **two distinct properties**:

1. **Topological correctness**: NONE. The pipeline does NOT depend on
   floor ordering for correctness — all operations look up floors by label.
   Reordering `(ground, first)` to `(first, ground)` produces a brief that
   yields the same downstream pipeline behaviour for any per-floor or
   dwelling-level operation.

2. **Structural identity**: YES. Tuple ordering DOES affect dataclass
   equality, hash value, and consequently any cache key or signature
   derived from the brief. `(ground, first)` and `(first, ground)` are
   NOT equal as `MultiFloorDwellingBrief` instances and produce different
   hashes.

**Per-subsystem canonicality** (MAJOR-2 patch from v0.2 critique walk):

| Subsystem | Identity used | Why |
|---|---|---|
| Python equality (`brief_a == brief_b`) | Structural | Standard `@dataclass(eq=True)` — full field-tuple comparison including `floors` order |
| Python hashing (`hash(brief)`) | Structural | Frozen dataclass uses `__hash__` derived from `__eq__` |
| C11a cache keys | Structural | Cache keys are computed via `derive_signature()` → hash; structural identity is what we WANT for cache stability (different float orders = different cache slot) |
| C11a signature derivation | Structural | Same as above |
| Pipeline orchestration correctness | Topological | Operators look up floors by label, not by index — reordering doesn't change behaviour |
| Lineage classification (Tier A/B operator detection) | Topological | A mutation that reorders floors WITHOUT changing master/labels is functionally a no-op despite producing a hash-different brief; classifier MUST detect this if it ever happens (currently doesn't, since no operator reorders) |
| User-facing display | Topological | Callers use `floor_labels` / `iter_floors_with_master_flag()`, not raw tuple position |

The split is **intentional** for v0.3. Callers are expected to construct
floors in a consistent order (ground-up convention recommended) which
makes structural identity match topological identity in practice. If a
future commercial path needs canonicalization, the cleanest path is
adding `floor_elevation_m` to `FloorRoomBrief` and canonicalizing tuple
ordering on construction (B-MFDB-A).

### § 3.6 — Frozen + hashable + normalization-versioning contract

`@dataclass(frozen=True)` with a `tuple[FloorRoomBrief, ...]` field, two
scalar string fields (one a Literal). Hashability follows from
`FloorRoomBrief` being frozen + hashable (already true) and tuple/string/
Literal being hashable.

Required for use as cache keys in C11a's `cache.py`.

**Normalization-versioning contract** (MODERATE-2 patch from v0.2 critique
walk): the `_normalize_label()` function's behaviour is part of the
cache/signature protocol. Any change to its semantics — adding hyphen
collapse, changing whitespace handling, supporting unicode normalization
forms, etc. — REQUIRES bumping `C11A_CACHE_KEY_VERSION` (or equivalent
cache-key version constant in C11a) in the same amendment that changes
the normalization. Without the bump, persisted cache entries would
silently drift away from their canonical keys.

This contract applies to:
- Any future spec amendment that touches `_normalize_label()`.
- Any future spec amendment that adds new fields to
  `MultiFloorDwellingBrief` that participate in equality / hash.

### § 3.7 — Non-livable floors are permitted

A floor with `bedroom_count=0`, `bathroom_count=0`, no kitchen, no living
room, no pooja, etc. is **valid** in `MultiFloorDwellingBrief`. Such floors
are common in real Indian residential dwellings: terraces, utility floors,
water-tank floors, parking floors.

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

**Construction success does NOT imply architectural plausibility**
(MODERATE-4 patch from v0.2 critique walk). Future developers MUST NOT
assume that a successfully-constructed `MultiFloorDwellingBrief` is a
sensible dwelling. It is only a structurally-valid combination of floors
and a master designation.

### § 3.8 — No canonical serialization in v0.3

This spec does NOT define a canonical serialization format (JSON, msgpack,
protobuf, SQL row, etc.). The current version is for in-memory domain-object
use only.

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
| **Master designation lives on the wrapper, not on `FloorRoomBrief`** | ✅ | Reject: `FloorRoomBrief.is_master_floor: bool`. Per-floor master flag duplicates info and risks divergence. Wrapper-level single-source-of-truth is cleaner. |
| **Master is FLOOR-level + reserved selector field for v2 room-level** | ✅ | Reject: omit selector field; rely on undocumented C9 first-bedroom convention. Hidden coupling fails Pattern C. The reserved `master_bedroom_selector: Literal["first_bedroom"]` makes the v0.3 selector explicit and gives v2 a non-breaking extension path. |
| **Selector runtime-validated, not just type-narrowed** | ✅ | Reject: rely on Literal type-narrowing alone. Runtime inputs from JSON, fuzzing, dynamic code paths bypass the type checker. One-line `__post_init__` guard is trivial. |
| **Min floors = 2** | ✅ | Reject: min = 1. Allowing single-floor multi-floor brief creates a "should I use the wrapper or not" decision at every call site. |
| **Frozen dataclass** | ✅ | Reject: mutable. Cache keys + signature stability require immutability. |
| **`with_master_on` returns new instance** | ✅ | Reject: in-place. Frozen requires this. |
| **Floor labels normalized at construction** | ✅ | Reject: leave labels raw. Cache fragmentation from `"Ground"` vs `"ground"` is real and one-line normalization eliminates it cheaply. |
| **Normalization rewrites nested FloorRoomBrief** | ✅ | Reject: leave nested labels raw (only normalize wrapper-level master_label). That would create asymmetric label semantics — wrapper canonical, nested raw — and complicate `floor_has_master()` / `get_floor()` / Inv MFDB-2 uniqueness. The nested-rewrite is honest and explicit (CRITICAL-1 acknowledgement); object-identity loss is documented. |
| **Normalization scope: whitespace/case only, NOT semantic aliases** | ✅ | Reject: aggressive aliasing (`first` ≡ `1F` ≡ `first_floor`). Slippery slope; every alias added is a cultural choice. v0.3 keeps the scope tight; consumers can canonicalize aliases before construction if they need to. |
| **Character set unrestricted** | ✅ | Reject: regex-enforced ASCII. Future Indian-language labels (Tamil, Hindi, Devanagari) shouldn't be pre-empted by a v0.3 regex choice. Consumers sanitize for display (B-MFDB-K). |
| **`floor_has_master(label)` helper as canonical derivation** | ✅ | Reject: let downstream code re-implement the comparison ad hoc. Centralization prevents orchestration drift. |
| **`iter_floors_with_master_flag()` helper, intentionally orchestration-flavoured** | ✅ | Reject: leave the loop pattern to each caller. Same orchestration-drift argument; cheap helper. **Architectural caveat acknowledged**: the helper introduces minor layering blur (domain object exposes orchestration-shape iteration); accepted because the alternative is N call sites re-implementing the same zip. |
| **Duck-typing via `is_multi_floor` property is transitional, not permanent** | ✅ | Reject: define a formal `Protocol` now. C11a v1.1 (Spec #4) is the right place for protocol typing. |
| **No `add_floor` / `remove_floor` / `has_floor` / etc. helpers in v1** | ✅ | Defer to v2. v1 covers "fixed dwelling shape, swap master." `has_floor` is one line (`label in brief.floor_labels`); `iter_floors_with_master_flag` name is precise (rejecting MINOR-3 rename). |
| **Selector field name `master_bedroom_selector` (rejecting "reserved discriminator")** | ✅ | Reject: rename to "reserved_selector_discriminator". Adds verbosity without clarity; docstring explains the v0.3-single-value reality. |

---

## § 5 — Test plan

### § 5.1 — New test file

Create `buildemup/tests/test_domain_multi_floor_brief.py`. Test budget grew
to ~44 tests in v0.3 (up from 41 in v0.2; net +3 from CRITICAL-2 runtime
selector validation, CRITICAL-1 nested-identity sentinel, MAJOR-1
normalization-scope sentinel).

**Construction (happy path)**:
1. `test_two_floor_construction_succeeds`
2. `test_three_floor_construction_succeeds`
3. `test_construction_with_master_on_first_floor`
4. `test_construction_with_utility_terrace_floor` (non-livable floor permitted)
5. `test_default_selector_value_is_first_bedroom`

**Invariant violations**:
6. `test_single_floor_raises` (Inv MFDB-1)
7. `test_empty_floors_raises` (Inv MFDB-1)
8. `test_duplicate_floor_labels_raises` (Inv MFDB-2)
9. `test_duplicate_via_normalization_raises` (Inv MFDB-2 post-normalization)
10. `test_master_label_not_in_floors_raises` (Inv MFDB-3)
11. `test_master_floor_has_zero_bedrooms_raises` (Inv MFDB-4)
12. **`test_invalid_selector_value_raises`** (Inv MFDB-6 runtime — CRITICAL-2 patch): `master_bedroom_selector="banana"` → `ValueError`.
13. **`test_empty_string_selector_raises`** (Inv MFDB-6 runtime): `master_bedroom_selector=""` → `ValueError`.
14. **`test_with_master_on_re_validates_selector`**: original brief built with valid selector; if internal state could ever drift, `with_master_on` re-runs `__post_init__` and would catch it. (Sanity sentinel.)

**Label normalization**:
15. `test_label_normalization_lowercase`
16. `test_label_normalization_strip_whitespace`
17. `test_label_normalization_collapse_internal_whitespace`
18. `test_master_label_normalized_during_construction`
19. `test_empty_label_raises`
20. `test_whitespace_only_label_raises`
21. `test_non_string_label_raises_type_error`
22. **`test_normalization_does_NOT_unify_semantic_aliases`** (MAJOR-1 sentinel): `"first"` ≠ `"1F"` ≠ `"first_floor"` even after normalization.
23. **`test_pathological_labels_are_accepted`** (MAJOR-4 explicit): `"@@@_floor"` is a valid normalized label.

**Read helpers**:
24. `test_is_multi_floor_property_is_true`
25. `test_get_floor_returns_correct_brief`
26. `test_get_floor_normalizes_input`
27. `test_get_floor_unknown_label_raises_key_error`
28. `test_floor_labels_preserves_tuple_order`
29. `test_floor_has_master_returns_true_for_master_floor`
30. `test_floor_has_master_returns_false_for_non_master_floor`
31. `test_floor_has_master_normalizes_input`
32. `test_iter_floors_with_master_flag_yields_exactly_one_true` (Inv MFDB-5 sentinel)
33. `test_iter_floors_with_master_flag_preserves_tuple_order`

**Mutation helper**:
34. `test_with_master_on_returns_new_instance_with_swapped_master`
35. `test_with_master_on_normalizes_input`
36. `test_with_master_on_unknown_floor_raises`
37. `test_with_master_on_target_with_zero_bedrooms_raises`
38. `test_with_master_on_does_not_mutate_original`
39. `test_with_master_on_preserves_selector_value`

**Frozen + equality + hashability**:
40. `test_two_briefs_with_same_content_are_equal`
41. `test_brief_is_hashable_for_dict_and_set_use`
42. `test_attempted_field_mutation_raises_frozen_instance_error`
43. `test_briefs_with_different_floor_order_are_not_equal` (MAJOR-2 — structural ≠ topological)

**Nested-object-identity sentinel** (CRITICAL-1 patch from v0.2 critique walk):
44. **`test_nested_floor_brief_is_rewritten_not_preserved`**: original `FloorRoomBrief` instance is NOT preserved at `brief.floors[i]`; only contents (modulo normalization) match. `id(original) != id(brief.floors[i])` after construction.

**C11a integration sentinel**:
45. `test_c11a_is_multi_floor_returns_true_for_this_type`

**Total**: 45 tests.

### § 5.2 — Existing test regression

Zero existing tests reference this type (it's NEW). Full project must
remain at **2760 passed / 2 skipped / 0 regressions** after this spec
ships.

---

## § 6 — Out-of-scope (what this spec does NOT do)

Per Pattern E (scope creep):

- **C9 amendment v0.8**: filed as Spec #2 of 4.
- **`MultiFloorWetZonePlannedCandidate`**: filed as Spec #3 of 4.
- **C11a amendment v1.1**: filed as Spec #4 of 4.
- **C1 brief-capture API for multi-floor**: future C1 amendment.
- **Floor-elevation tracking** (`floor_elevation_m`): post-v1 commercial path.
- **Per-floor staircase landing constraints**: post-v1, requires C7 + C8 amendments.
- **Mid-level, mezzanine, basement floors**: v1 supports rectangular ground-up multi-floor only.
- **Non-residential dwelling types**: post-v1.
- **Multiple master bedrooms / dual masters / owner suites**: v0.3 supports exactly ONE master designation globally per dwelling.
- **Semantic-alias normalization** (`first` ≡ `1F` ≡ `first_floor`): post-v1 if needed.
- **Character-set restrictions for floor_label**: deliberately unconstrained in v0.3.
- **Canonical serialization format** (JSON / API payload / persistence): deferred to a later amendment.
- **Canonical taxonomy of non-livable-floor categories** (utility / terrace / parking / mechanical): deferred (B-MFDB-L).

---

## § 7 — Backlog items deferred

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-MFDB-A** | `floor_elevation_m` on `FloorRoomBrief`; enables tuple-order canonicalization | v2 commercial path | Open (post-v1) |
| **B-MFDB-B** | `add_floor` / `remove_floor` mutation helpers | When dwelling shape can change post-construction | Open (post-v1) |
| **B-MFDB-C** | Per-floor staircase landing constraint (X,Y alignment) | Multi-floor topologies needing vertical circulation alignment | Open — requires C7 + C8 amendments |
| **B-MFDB-D** | C1 brief-capture API extension for multi-floor input | C1 endpoint surfaces multi-floor option | Open — separate component |
| **B-MFDB-E** | Mid-level / basement / mezzanine support | v2 commercial path | Open (post-v1) |
| **B-MFDB-F** | Lookup-map optimization (O(1) `get_floor()`) | Stress-fuzz hot-path cost OR commercial path with >= 10 floors | Open (post-v1) |
| **B-MFDB-G** | Migrate C11a `_is_multi_floor()` from duck-typed to formal Protocol | C11a v1.1 (Spec #4) drafts protocol typing | Open — addressed in Spec #4 |
| **B-MFDB-H** | Domain exception strategy when types become user-facing | C1 endpoint exposes domain types directly | Open (post-v1, gated on B-MFDB-D) |
| **B-MFDB-I** (REPURPOSED) | Widen `_VALID_SELECTORS` enum when v2 selectors land (`"explicit_id"`, `"largest_area"`); cache-key bump in same amendment | When v2 master-selection strategy becomes a real product requirement | Open (post-v1) |
| **B-MFDB-J** | Multi-master / dual-master / owner-suite support | v2 luxury / multi-family path | Open (post-v1) |
| **B-MFDB-K** (NEW) | Sanitization rules for pathological labels (display vs identity separation) | When labels become user-facing display strings (not just identity keys) | Open (post-v1, gated on B-MFDB-D) |
| **B-MFDB-L** (NEW) | Canonical taxonomy of non-livable-floor categories (utility/terrace/parking/mechanical) | When downstream classification needs the distinction (likely C5 or new component) | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK:

- 1 new file: `buildemup/domain/multi_floor_brief.py` (~190 lines incl. docstrings; up from ~165 in v0.2 because of CRITICAL-2 runtime selector validation, expanded module docstring, normalization-versioning contract).
- 1 new test file: `buildemup/tests/test_domain_multi_floor_brief.py` (~45 tests).
- No modifications to existing code.

Estimated build effort: ~45-60 minutes of code, BUT this build will not
happen until Specs 2-3-4 are also LOCKED. Code lands as part of the
eventual unified B-NEW-T3 build session.

---

## § 9 — Status

- **v0.3 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v0.4 PROPOSED.
- After LOCK: spec drafting proceeds to Spec #2 (C9 Amendment v0.8).
- Code work: deferred until all four specs LOCKED.

---

## § 10 — Rule 9 backlog enumeration

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| **B-NEW-T3** | M8 multi-floor real upstream wiring | S39 walk F5 | All four specs LOCKED | GATED (4 specs) | L |
| **B-NEW-T3-PRE** | Multi-floor schema gate (this 4-spec sequence) | S40-cont discovery | Specs 1-4 LOCKED | IN-FLIGHT — Spec #1 of 4 | M |
| Spec #2 | C9 Amendment v0.8 — `has_master_bedroom` flag | Same discovery | Spec #1 LOCKED | NEXT after this LOCKs | S |
| Spec #3 | `MultiFloorWetZonePlannedCandidate` domain spec | Same discovery | Spec #1 + #2 LOCKED | After #2 | M |
| Spec #4 | C11a Amendment v1.1 — multi-floor pipeline rework | Same discovery | Specs #1-3 LOCKED | Last in sequence; LARGE | L |
| B-NEW-T1.5 | Promote M6 to real C10 re-run (independent) | S39 Sub-5 | Future C10 amendment | Out-of-scope | M |
| B-NEW-Y full | Mutation chain accumulation (multi-floor stress-fuzzes once T3 lands) | S39 Sub-5 | After B-NEW-T3 complete | Gated | M |

**Summary**: foundation of a 4-spec sequence for B-NEW-T3. v0.3 added 2
new deferral items (B-MFDB-K, B-MFDB-L). Repurposed 1 (B-MFDB-I).

---

**End of MultiFloorDwellingBrief Spec v0.3 PROPOSED.**
