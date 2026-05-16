# MULTI-FLOOR WET-ZONE PLANNED CANDIDATE SPEC v0.2 PROPOSED — output-side multi-floor wrapper (B-NEW-T3 enabler #3 of 4)

**Component**: NEW domain dataclass (lives at `buildemup/domain/multi_floor_candidate.py`).
**Spec status**: **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
**Authority**: Ramalingam directive at S40-continuation: spec-first, four-spec sequence for B-NEW-T3.
**Authored**: S40-continuation, post-empirical-schema-check.
**Driver**: Spec #3 of 4. Output-side counterpart to Spec #1 (`MultiFloorDwellingBrief`).

**v0.2 vs v0.1**: schema-drift correction. v0.1 asserted the ancestry path `f.room_sized_candidate.provenance.floor_room_brief.floor_label`, but empirical schema check (S40-cont, post-PROPOSED-deliver) found the correct path is `f.room_sized_candidate.provenance.floor_label` — `RoomSizingProvenance` carries `floor_label` directly as a string field (line 5 of its dataclass), not via a nested `floor_room_brief` reference. Three sites corrected: `_derive_floor_labels` body, the error message it raises, and one docstring reference.

This is a near-identical pattern to the S40 grid_scale schema-drift near-miss (initial `_grid_from_wzpc` assumed `room_size_table.provenance.grid` which doesn't exist; fixed before tests written). The lesson — empirical schema check before LOCK — was applied here in time to catch the bug pre-LOCK rather than mid-build.

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

## § 1 — Why this spec exists

Spec #1 defines `MultiFloorDwellingBrief` (the input). Spec #2 extends `FloorRoomBrief` with `has_master_bedroom` so per-floor C9 invocations produce correct master designation. After per-floor C9 + C10 run, the output is a tuple of per-floor `WetZonePlannedCandidate` instances — but Spec #4's pipeline needs to treat that tuple as a single coherent multi-floor candidate, with cache identity, equality semantics, mutation semantics, and lineage all defined at the dwelling level.

**This spec defines that output type.**

The wrapper mirrors Spec #1's structural pattern (frozen dataclass, tuple of per-floor instances, dwelling-level master designation, canonical helpers, 6 invariants). Differences vs Spec #1 are concentrated in cross-floor validation (the wrapper enforces "exactly one master bedroom emitted globally" at construction — this is the v0.11 Spec #2 § 3.10 trust-boundary assertion, hardened from "Spec #4 is expected to own" to "Spec #3 type-construction owns").

**Spec #4 dependency**: the C11a v1.1 amendment will use this type as the per-batch element when multi-floor briefs flow through `mutate_topologies`. Lineage classification, signature derivation, and cache keys all consume `MultiFloorWetZonePlannedCandidate.__hash__` / `__eq__`.

---

## § 2 — Schema

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator

from buildemup.components.c10.schema import WetZonePlannedCandidate
from buildemup.components.c09.schema import RoomCategory
from buildemup.domain.multi_floor_brief import _normalize_label


@dataclass(frozen=True)
class MultiFloorWetZonePlannedCandidate:
    """Output-side multi-floor wrapper.

    Holds per-floor WetZonePlannedCandidate instances + dwelling-level
    master designation. Mirrors the structural pattern of Spec #1's
    MultiFloorDwellingBrief (input side); see Spec #1 for the symmetric
    invariants and helpers.

    The wrapper enforces (at construction) the cross-floor invariant
    that "exactly one master bedroom is emitted globally across all
    per-floor candidates" (Inv MFWZP-5). This hardens the trust-boundary
    assertion that Spec #2 v0.11 § 3.10 forward-pointed to Spec #4.

    Frozen + hashable for cache identity (C11a `cache.py` keys on
    structural signatures derived from the multi-floor candidate).

    NOTE on canonical ownership (mirrors Spec #1 § 3.9):
    after construction, the per-floor WetZonePlannedCandidate instances
    inside ``floors`` are the canonical authoritative per-floor objects
    for downstream operations. Lineage systems, caches, mutation
    operators, and signature derivation MUST reference the wrapped
    instances (via ``candidate.floors[i]``, ``candidate.get_floor(label)``,
    or ``iter_floors_with_master_flag()``), NOT pre-construction
    references. This wrapper does NOT rewrite per-floor candidates —
    they are stored as-is — but the wrapper IS the canonical identity
    for the multi-floor whole.

    NOTE on construction-vs-plausibility (mirrors Spec #1 § 3.7):
    construction success does NOT imply architectural plausibility.
    A wrapper holding per-floor candidates whose wet-zone plans are
    technically valid but combine nonsensically at the dwelling level
    (e.g., master suite on a floor with no kitchen access on any floor
    in the dwelling) is structurally valid but degenerate. Cross-floor
    sanity beyond Inv MFWZP-5 is downstream's responsibility (C11a
    scoring, post-pipeline validation).

    NOTE on identity vs topology (mirrors Spec #1 § 3.5):
    tuple ordering of ``floors`` is structural identity (affects
    equality, hash, cache slots) but topologically inert (the pipeline
    looks up floors by label, not by index). Callers should construct
    floors in the same order as the source MultiFloorDwellingBrief's
    ``floors`` tuple to avoid cache fragmentation; ground-up convention
    recommended but not enforced.
    """

    floors: tuple[WetZonePlannedCandidate, ...]
    master_bedroom_floor_label: str

    def __post_init__(self) -> None:
        # Normalize master_bedroom_floor_label using Spec #1's canonical
        # normalizer (re-imported to avoid duplicating the function).
        # Per-floor labels are NOT re-normalized here — they're already
        # canonical because the per-floor briefs were normalized when
        # the source MultiFloorDwellingBrief was constructed (Spec #1
        # § 3.1 nested-rewrite). We only validate consistency.
        normalized_master = _normalize_label(self.master_bedroom_floor_label)
        object.__setattr__(self, "master_bedroom_floor_label", normalized_master)

        # ---- Inv MFWZP-1: ≥2 floors. Single-floor dwellings continue
        # using bare WetZonePlannedCandidate; this wrapper is multi-floor only.
        if len(self.floors) < 2:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate requires len(floors) >= 2; "
                f"got {len(self.floors)}. Single-floor outputs should use "
                f"WetZonePlannedCandidate directly."
            )

        # ---- Inv MFWZP-2: per-floor labels (derived from each WZPC's
        # room_sized_candidate.provenance...brief.floor_label) must be unique.
        derived_labels = self._derive_floor_labels()
        if len(set(derived_labels)) != len(derived_labels):
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: per-floor labels must "
                f"be unique across floors; derived {derived_labels!r}."
            )

        # ---- Inv MFWZP-3: master_bedroom_floor_label ∈ derived labels.
        if self.master_bedroom_floor_label not in derived_labels:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r} not in derived per-floor "
                f"labels {derived_labels!r}."
            )

        # ---- Inv MFWZP-4: every per-floor WetZonePlannedCandidate must be
        # an actual WetZonePlannedCandidate (not None, not a mock).
        for i, f in enumerate(self.floors):
            if not isinstance(f, WetZonePlannedCandidate):
                raise TypeError(
                    f"MultiFloorWetZonePlannedCandidate.floors[{i}] must be "
                    f"WetZonePlannedCandidate; got {type(f).__name__}."
                )

        # ---- Inv MFWZP-5: exactly one master bedroom emitted globally.
        # This is the hardened trust-boundary assertion from Spec #2 v0.11
        # § 3.10 — moved from "Spec #4 is expected to own" to
        # "Spec #3 enforces at construction".
        master_bedroom_count = self._count_global_master_bedrooms()
        if master_bedroom_count != 1:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: expected exactly one "
                f"master bedroom across all per-floor candidates; got "
                f"{master_bedroom_count}. master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r}, derived per-floor "
                f"labels={derived_labels!r}."
            )

        # ---- Inv MFWZP-6: the unique master bedroom MUST be on the
        # floor named by master_bedroom_floor_label (consistency between
        # the wrapper-level designation and the per-floor C9 output).
        master_floor_label = self._floor_label_of_unique_master_bedroom()
        if master_floor_label != self.master_bedroom_floor_label:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: master bedroom found on "
                f"floor {master_floor_label!r} but wrapper declares "
                f"master_bedroom_floor_label={self.master_bedroom_floor_label!r}. "
                f"This indicates upstream orchestration drift between the "
                f"per-floor C9 has_master_bedroom flags and the wrapper-level "
                f"master designation."
            )

    # ----- Read helpers (mirror Spec #1's interface) -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True (Inv MFWZP-1 enforces len >= 2)."""
        return True

    @property
    def floor_labels(self) -> tuple[str, ...]:
        """Tuple of per-floor labels in tuple order (derived, cached on
        first call via lru_cache or computed each time — implementation
        choice deferred to build session).
        """
        return self._derive_floor_labels()

    def get_floor(self, label: str) -> WetZonePlannedCandidate:
        """Return the per-floor WetZonePlannedCandidate for the given label.

        Label is normalized before lookup (mirrors Spec #1 § 3.3 public-
        helpers-normalize convention). Raises KeyError if no floor has
        that label.

        O(n) over floors. Lookup-map optimization filed as B-MFWZP-A.
        """
        normalized = _normalize_label(label)
        derived_labels = self._derive_floor_labels()
        for i, lbl in enumerate(derived_labels):
            if lbl == normalized:
                return self.floors[i]
        raise KeyError(
            f"MultiFloorWetZonePlannedCandidate.get_floor({label!r}): no "
            f"floor with that label (normalized={normalized!r}); available: "
            f"{derived_labels!r}"
        )

    def floor_has_master(self, label: str) -> bool:
        """Canonical derivation: does the given floor host the master
        bedroom? Mirrors Spec #1's helper of the same name.
        """
        return _normalize_label(label) == self.master_bedroom_floor_label

    def iter_floors_with_master_flag(
        self,
    ) -> Iterator[tuple[WetZonePlannedCandidate, bool]]:
        """Iterate per-floor candidates yielding ``(wzpc, has_master)``.

        DESIGN NOTE (mirrors Spec #1 MAJOR-3 acknowledgement):
        intentionally orchestration-flavoured. Lets downstream code (C11a
        v1.1 lineage classifier, signature derivation, scoring) avoid
        re-implementing the pairing.

        FORWARD-COMPAT CAVEAT (mirrors Spec #1): the ``(WZPC, bool)``
        payload may need to grow (richer metadata) in future amendments;
        callers should NOT build infrastructure assuming the 2-tuple is
        permanent.
        """
        derived_labels = self._derive_floor_labels()
        for i, f in enumerate(self.floors):
            yield f, (derived_labels[i] == self.master_bedroom_floor_label)

    # ----- Mutation helpers -----

    def with_master_on(
        self, new_floor_label: str, new_per_floor_candidates: tuple[WetZonePlannedCandidate, ...],
    ) -> MultiFloorWetZonePlannedCandidate:
        """Return a new MultiFloorWetZonePlannedCandidate with master moved
        to the given floor.

        UNLIKE Spec #1's `with_master_on` (which only changes the master
        label and reuses existing per-floor briefs), this wrapper's version
        REQUIRES a new tuple of per-floor candidates because changing the
        master designation means the affected floors' has_master_bedroom
        flags changed, which means C9 must be re-run on those floors,
        which means the per-floor WetZonePlannedCandidate instances are
        DIFFERENT.

        The caller (Spec #4 M8 operator) is responsible for re-running
        the C9→C10 cascade with the new per-floor brief tuple before
        invoking this helper.

        This is why M8 is the only Tier B operator that produces a wrapper
        change at the dwelling level; all other operators (M1-M7, M9)
        change a single floor and produce a wrapper that reuses untouched
        floors and replaces only the affected one.

        Re-runs `__post_init__` so all 6 invariants are re-validated on
        the new instance.
        """
        return MultiFloorWetZonePlannedCandidate(
            floors=new_per_floor_candidates,
            master_bedroom_floor_label=_normalize_label(new_floor_label),
        )

    def with_floor_replaced(
        self, floor_label: str, new_wzpc: WetZonePlannedCandidate,
    ) -> MultiFloorWetZonePlannedCandidate:
        """Return a new wrapper with one floor's WetZonePlannedCandidate
        replaced. Used by single-floor operators (M1-M7, M9) which only
        affect one floor.

        Master designation is preserved. Per-floor label is preserved
        (the new WZPC must have the same floor_label as the old one;
        validated by `__post_init__` rerun via Inv MFWZP-2).
        """
        normalized = _normalize_label(floor_label)
        derived_labels = self._derive_floor_labels()
        new_floors = list(self.floors)
        replaced = False
        for i, lbl in enumerate(derived_labels):
            if lbl == normalized:
                new_floors[i] = new_wzpc
                replaced = True
                break
        if not replaced:
            raise ValueError(
                f"with_floor_replaced({floor_label!r}): no floor with that "
                f"label; available: {derived_labels!r}"
            )
        return MultiFloorWetZonePlannedCandidate(
            floors=tuple(new_floors),
            master_bedroom_floor_label=self.master_bedroom_floor_label,
        )

    # ----- Internal helpers -----

    def _derive_floor_labels(self) -> tuple[str, ...]:
        """Walk per-floor WZPC ancestry to extract floor_label from each.

        Path: ``WZPC.room_sized_candidate.provenance.floor_label``

        Empirically verified (S40-cont): ``RoomSizingProvenance`` carries
        ``floor_label: str`` directly as a top-level field (alongside
        ``derived_at``, ``plot_analysis_trace_id``, ``dwelling_size_tier``,
        etc.). It is NOT nested under a ``floor_room_brief`` attribute —
        that was a v0.1 spec error caught by empirical check before LOCK.

        The label is already-normalized: per-floor briefs were normalized
        when the source ``MultiFloorDwellingBrief`` was constructed (Spec
        #1 § 3.1 nested-rewrite), and the per-floor brief's normalized
        ``floor_label`` was carried into ``RoomSizingProvenance`` by C9
        when it derived provenance from the brief. So derived labels
        reaching this method are canonical and need no re-normalization.
        """
        labels = []
        for i, f in enumerate(self.floors):
            try:
                labels.append(f.room_sized_candidate.provenance.floor_label)
            except AttributeError as e:
                raise ValueError(
                    f"MultiFloorWetZonePlannedCandidate.floors[{i}]: cannot "
                    f"derive floor_label from ancestry chain "
                    f"(room_sized_candidate.provenance.floor_label). "
                    f"Underlying error: {e}"
                )
        return tuple(labels)

    def _count_global_master_bedrooms(self) -> int:
        """Count rooms with category=BEDROOM AND is_master=True across
        all per-floor candidates.

        Per Spec #2 v0.11 Inv 13: is_master=True is only valid on BEDROOM
        and BATHROOM. This counter ignores BATHROOM masters (they're
        en-suite to the bedroom master and don't count for the
        "exactly one master bedroom globally" invariant).
        """
        count = 0
        for f in self.floors:
            rst = f.room_sized_candidate.room_size_table
            for room in rst.rooms:
                if room.is_master and room.category == RoomCategory.BEDROOM:
                    count += 1
        return count

    def _floor_label_of_unique_master_bedroom(self) -> str:
        """Find the floor label of the (unique by Inv MFWZP-5) master
        bedroom. Caller MUST verify Inv MFWZP-5 first.
        """
        derived_labels = self._derive_floor_labels()
        for i, f in enumerate(self.floors):
            rst = f.room_sized_candidate.room_size_table
            for room in rst.rooms:
                if room.is_master and room.category == RoomCategory.BEDROOM:
                    return derived_labels[i]
        # Should be unreachable if Inv MFWZP-5 holds.
        raise RuntimeError(
            "MultiFloorWetZonePlannedCandidate._floor_label_of_unique_master_bedroom: "
            "no master bedroom found despite Inv MFWZP-5 having passed. "
            "Internal contract violation."
        )
```

---

## § 3 — Behavioral contract

### § 3.1 — Construction

Callers always construct via the dataclass constructor. The
`__post_init__` enforces 6 invariants; no factory function.

The wrapper is built by Spec #4's C11a orchestrator after per-floor
C9→C10 cascades complete. Construction order (canonical):

```python
# Spec #4 orchestrator pseudocode (illustrative; actual Spec #4 may differ):
mfb = MultiFloorDwellingBrief(...)  # Spec #1
per_floor_wzpcs = []
for floor_brief, has_master in mfb.iter_floors_with_master_flag():
    per_floor_brief = dataclasses.replace(floor_brief, has_master_bedroom=has_master)
    rsc = c09.size_rooms(..., per_floor_brief, ...)
    wzpc = c10.plan_wet_zones(rsc, per_floor_brief, ...)
    per_floor_wzpcs.append(wzpc[0])  # one candidate per floor
candidate = MultiFloorWetZonePlannedCandidate(
    floors=tuple(per_floor_wzpcs),
    master_bedroom_floor_label=mfb.master_bedroom_floor_label,
)
```

**Per-floor labels are derived, not declared.** Each WZPC's ancestry
chain (`room_sized_candidate.provenance.floor_room_brief.floor_label`)
provides the canonical floor label. The wrapper does NOT take a separate
`floor_labels` tuple — that would risk drift between the declared and
the derived. Construction validates that the derived set is unique
(Inv MFWZP-2) and that `master_bedroom_floor_label` matches one of them
(Inv MFWZP-3).

### § 3.2 — Invariants

Six invariants total. All runtime-enforced in `__post_init__`.

| Inv ID | Rule | Failure |
|---|---|---|
| **MFWZP-1** | `len(floors) >= 2` | `ValueError` (single-floor uses bare `WetZonePlannedCandidate`) |
| **MFWZP-2** | Per-floor labels (derived from ancestry) are unique | `ValueError` |
| **MFWZP-3** | `master_bedroom_floor_label ∈ derived labels` | `ValueError` |
| **MFWZP-4** | All `floors[i]` are `WetZonePlannedCandidate` instances | `TypeError` |
| **MFWZP-5** | Exactly one master bedroom emitted globally across all per-floor candidates (room with `is_master=True AND category=BEDROOM`) | `ValueError` — **hardens** the Spec #2 v0.11 § 3.10 trust-boundary assertion from "Spec #4 is expected to own" to "Spec #3 enforces at construction" |
| **MFWZP-6** | The unique master bedroom is on the floor named by `master_bedroom_floor_label` (wrapper-level designation matches per-floor C9 output) | `ValueError` — catches orchestration drift between Spec #1's `iter_floors_with_master_flag()` output and the wrapper's master declaration |

**Inv MFWZP-5 + MFWZP-6 are the hardening of Spec #2's trust boundary.**
Where Spec #2 v0.11 § 3.10 says "C9 trusts upstream orchestration to set
`has_master_bedroom` correctly per floor" and § 6 says "Spec #4 is
expected to own the assertion before downstream scoring/caching/persistence,"
Spec #3 instead enforces both at the moment the multi-floor candidate
type is constructed. This is **stronger** than Spec #2's forward-pointer
because it makes the bad state structurally unreachable.

### § 3.3 — Read helpers (mirror Spec #1)

| Helper | Purpose | Normalization |
|---|---|---|
| `is_multi_floor` (property) | Always True; lets duck-typing detect multi-floor output | n/a |
| `floor_labels` (property) | Tuple of derived per-floor labels in tuple order | Returns canonical (already-normalized) |
| `get_floor(label)` | Lookup by label; KeyError if missing. O(n) | Normalizes input |
| `floor_has_master(label)` | Canonical master derivation (= comparison) | Normalizes input |
| `iter_floors_with_master_flag()` | Canonical per-floor iteration with master flag | n/a |

### § 3.4 — Mutation helpers — TWO operations

Unlike Spec #1 which has only `with_master_on`, Spec #3 distinguishes
two mutation shapes:

- **`with_floor_replaced(label, new_wzpc)`**: single-floor mutation.
  Used by M1-M7, M9 (per-floor operators). Only one floor changes;
  master designation preserved; non-target floors reused as-is.
- **`with_master_on(new_label, new_per_floor_candidates)`**:
  dwelling-level mutation. Used by M8 only. Master designation moves;
  master AND new-master floor's per-floor candidates BOTH change
  (because their `has_master_bedroom` flags flipped, requiring C9 re-runs).

The asymmetry is intentional: M8 can NOT be expressed as a single
`with_floor_replaced` because TWO floors change (the previous master
floor's brief now has `has_master_bedroom=False`, the new master floor's
brief now has `has_master_bedroom=True`). The caller (Spec #4 M8 operator)
must run C9→C10 on both affected floors before invoking
`with_master_on`.

### § 3.5 — Floor ordering semantics (mirror Spec #1 § 3.5)

Same canonicality split as Spec #1: tuple ordering is structurally
identity-significant (affects equality, hash, cache slots) but
topologically inert (the pipeline looks up floors by label, not by
index). Callers should construct in the same order as the source
`MultiFloorDwellingBrief.floors` tuple to avoid cache fragmentation.

**No reorder operator exists in the current spec set.** Same forward-compat
clause as Spec #1: any future reorder-capable operator requires explicit
lineage classification semantics.

### § 3.6 — Frozen + hashable + cache-versioning contract

`@dataclass(frozen=True)`. Hashability follows from `WetZonePlannedCandidate`
being frozen + hashable (already true) and tuple/string being hashable.

This wrapper participates in C11a's cache identity. Per Spec #1 § 3.6
contract paragraph 4: "any future spec amendment that adds new fields to
MultiFloorDwellingBrief that participate in equality/hash" requires
`C11A_CACHE_KEY_VERSION` bump. The same contract applies symmetrically
to this wrapper — any future amendment that adds fields to
`MultiFloorWetZonePlannedCandidate` (or modifies how derived floor
labels are computed) requires a cache-key bump.

**Initial bump for this spec**: bumping from Spec #2's `v1.1.0` to
`v1.2.0` to reflect the new wrapper type entering cache identity. Spec #4
build session executes the bump.

### § 3.7 — No canonical serialization in v0.1

Same disclaimer as Spec #1 § 3.8. No JSON / msgpack / persistence format
defined. Future amendment when persistence becomes real.

### § 3.8 — Reading guide (mirror Spec #1 § 0.2)

The spec mixes four kinds of content (normative invariants, behavioural
specification, rationale + design choices, forward-compat / future
migration). See § 4 for design rationale and § 7 for forward-compat
backlog. The 6 invariants in § 3.2 + the mutation-helper contract in §
3.4 are the load-bearing normative bits.

### § 3.9 — Symmetry with Spec #1 (intentional)

This spec is intentionally structured as the output-side mirror of
Spec #1. The parallel architecture means:

- Same 6-invariant pattern (counts match, conceptual roles align).
- Same canonical ownership / nested-object framing.
- Same canonicality table for equality vs topology.
- Same `iter_floors_with_master_flag()` orchestration helper.
- Same forward-compat reorder-operator clause.

Where Spec #3 DIVERGES from Spec #1:

- **Cross-floor invariant (MFWZP-5/6)**: Spec #1 has only intra-brief
  invariants; Spec #3 enforces dwelling-level master uniqueness. This
  is because the OUTPUT must be valid-by-construction — the input only
  needs to be parseable, the output must be coherent.
- **Two mutation helpers vs one**: Spec #1's `with_master_on` only
  changes a label; Spec #3's needs full per-floor candidate replacement
  for the M8 case. Spec #3 also has `with_floor_replaced` for M1-M7/M9
  single-floor ops.
- **Per-floor labels derived vs declared**: Spec #1's labels live on the
  per-floor `FloorRoomBrief.floor_label` directly; Spec #3's labels are
  walked through the WZPC ancestry chain.
- **No `master_bedroom_selector` field**: this wrapper inherits selector
  semantics transitively (the selector lived on Spec #1's brief; per-floor
  briefs flowing through C9 carry the selector forward; the wrapper just
  records WHICH FLOOR was master, not HOW the master room was selected).

---

## § 4 — Design choices considered

| Choice | Picked | Alternatives rejected |
|---|---|---|
| **Mirror Spec #1 structure** | ✅ | Reject: invent new helper / invariant patterns. Symmetry between input and output reduces cognitive load and prevents drift. |
| **Per-floor labels derived from ancestry, not declared** | ✅ | Reject: take a separate `floor_labels` tuple. Risks drift between declared and derived. The ancestry chain IS the source of truth; declaring duplicate state invites bugs. |
| **MFWZP-5 (exactly one master) enforced at construction** | ✅ | Reject: defer to Spec #4 orchestrator-level assertion (the original Spec #2 v0.11 § 3.10 forward-pointer). Type-construction enforcement is structurally stronger — invalid states become unreachable. This UPGRADES the trust boundary from runtime-fail to construct-fail. |
| **MFWZP-6 (master location matches declaration)** | ✅ | Reject: derive `master_bedroom_floor_label` from the per-floor master, eliminating MFWZP-6 entirely. Rejected because the field is declarative — it makes the wrapper's identity self-describing without needing to walk ancestry. MFWZP-6 catches orchestration-drift between Spec #1's `iter_floors_with_master_flag()` output and the wrapper construction. |
| **Two mutation helpers (`with_master_on` + `with_floor_replaced`)** | ✅ | Reject: one unified helper. The shapes are genuinely different (M8 changes 2+ floors; M1-M7/M9 change 1 floor); a unified helper would have a confusing signature with optional args. Splitting matches operator family boundaries. |
| **Frozen dataclass** | ✅ | Reject: mutable. Cache identity + signature stability requires immutability. |
| **`master_bedroom_floor_label` normalized at construction** | ✅ | Reject: leave raw. Spec #1 normalizes; Spec #3 must match for cache compatibility. Per-floor labels are NOT re-normalized — they're already canonical from Spec #1's nested-rewrite. |
| **No `master_bedroom_selector` field on the wrapper** | ✅ | Reject: duplicate the selector field. The selector lives on Spec #1's brief, propagates through C9, lives in the per-floor WZPC's ancestry. Re-storing on the wrapper is duplication; querying via ancestry is the canonical path. |
| **`with_floor_replaced` for single-floor operators (not just M8)** | ✅ | Reject: only define `with_master_on` for M8 and force callers to construct a new wrapper from scratch for M1-M7/M9. The latter shifts boilerplate into every operator. The helper centralizes the pattern. |
| **No provenance field in v0.1** | ✅ | Reject: add `MultiFloorCandidateProvenance` field carrying mutation lineage / source brief signature / parent. C11a v1.1 (Spec #4) already owns lineage tracking via existing C11a infrastructure (CandidateContext, lineage classifier). Re-inventing it here would create duplicate lineage state. Spec #4 will extend C11a's existing lineage to handle multi-floor; this wrapper stays a passive container. |

---

## § 5 — Test plan

### § 5.1 — New test file

Create `buildemup/tests/test_domain_multi_floor_candidate.py`. ~35 tests:

**Construction (happy path)**:
1. `test_two_floor_construction_succeeds_with_master_on_ground`.
2. `test_three_floor_construction_succeeds`.
3. `test_construction_with_master_on_first_floor`.

**Invariant violations**:
4. `test_single_floor_raises` (Inv MFWZP-1).
5. `test_empty_floors_raises` (Inv MFWZP-1).
6. `test_duplicate_floor_labels_raises` (Inv MFWZP-2 — construct two WZPCs with same floor_label briefs).
7. `test_master_label_not_in_floors_raises` (Inv MFWZP-3).
8. `test_non_wzpc_in_floors_tuple_raises` (Inv MFWZP-4).
9. `test_zero_master_bedrooms_globally_raises` (Inv MFWZP-5 — all floors built with `has_master_bedroom=False`).
10. `test_two_master_bedrooms_globally_raises` (Inv MFWZP-5 — two floors with master).
11. `test_master_label_disagrees_with_actual_master_floor_raises` (Inv MFWZP-6).

**Read helpers**:
12. `test_is_multi_floor_property_true`.
13. `test_floor_labels_returns_derived_tuple`.
14. `test_get_floor_returns_correct_wzpc`.
15. `test_get_floor_normalizes_input`.
16. `test_get_floor_unknown_label_raises_key_error`.
17. `test_floor_has_master_returns_true_for_master_floor`.
18. `test_floor_has_master_returns_false_for_non_master_floor`.
19. `test_floor_has_master_normalizes_input`.
20. `test_iter_floors_with_master_flag_yields_one_true_total`.
21. `test_iter_floors_with_master_flag_preserves_tuple_order`.

**Mutation helpers**:
22. `test_with_floor_replaced_replaces_one_floor`.
23. `test_with_floor_replaced_preserves_master_designation`.
24. `test_with_floor_replaced_unknown_label_raises`.
25. `test_with_floor_replaced_does_not_mutate_original`.
26. `test_with_floor_replaced_normalizes_input`.
27. `test_with_master_on_returns_new_instance_with_swapped_master`.
28. `test_with_master_on_re_validates_all_invariants`.
29. `test_with_master_on_normalizes_input`.

**Frozen + equality + hash**:
30. `test_two_candidates_with_same_content_are_equal`.
31. `test_candidate_is_hashable`.
32. `test_attempted_field_mutation_raises_frozen_instance_error`.
33. `test_candidates_with_different_floor_order_are_not_equal` (structural ≠ topological).

**Symmetry sentinel**:
34. `test_iter_floors_with_master_flag_round_trips_with_spec_1`: construct from a `MultiFloorDwellingBrief`, run cascade, verify `iter_floors_with_master_flag` on Spec #3 wrapper produces the SAME `(floor, has_master)` pairing as Spec #1's helper produced on the brief side.

**Trust-boundary hardening sentinel**:
35. `test_construction_fail_fast_for_zero_master_no_silent_propagation`: explicitly verify Inv MFWZP-5 fires BEFORE any cache/scoring path, by constructing a candidate that would have zero masters and confirming the exception fires at construction (not later).

### § 5.2 — Existing test regression

Zero existing tests reference this type (NEW). Full project must remain
at **2769 passed / 2 skipped / 0 regressions** (post-Spec-#2 baseline)
after this spec ships in build session.

---

## § 6 — Out-of-scope

- **Spec #4 (C11a Amendment v1.1)**: orchestrator pipeline rework. Spec #4 USES this type as the multi-floor candidate; this spec doesn't define the pipeline.
- **Multi-floor lineage tracking**: deferred to Spec #4 (C11a's existing lineage infrastructure extends to multi-floor).
- **Multi-floor scoring**: deferred. Scoring takes the wrapper as input; C11b NSGA-II will operate on `MultiFloorWetZonePlannedCandidate` once it ships.
- **Persistence / serialization**: post-v1.
- **Floor-elevation tracking**: same as Spec #1 (B-MFDB-A).
- **Reorder-capable operators**: same forward-compat clause as Spec #1 § 3.5.
- **Multiple master bedrooms / dual masters**: post-v1 (Spec #1 B-MFDB-J).
- **Strict-mode lookup helpers**: same as Spec #1 (B-MFDB-M).
- **Provenance field on the wrapper**: deferred. C11a v1.1 owns lineage.

---

## § 7 — Backlog items deferred

| ID | Description | Trigger | Status |
|---|---|---|---|
| **B-MFWZP-A** | Lookup-map optimization (O(1) `get_floor()` via cached `dict[label, idx]`) | Stress fuzz hot-path cost OR commercial path with ≥10 floors | Open (post-v1) |
| **B-MFWZP-B** | Add `provenance` field to wrapper for dwelling-level lineage / mutation chain (currently delegated to C11a v1.1's existing infrastructure) | If C11a v1.1's existing lineage proves insufficient for multi-floor (likely OK — single-floor lineage extends naturally) | Open — addressed in Spec #4 |
| **B-MFWZP-C** | Canonical serialization format (JSON / msgpack / etc.) | When persistence becomes real (e.g., distributed orchestration, post-v1 commercial) | Open (post-v1) |
| **B-MFWZP-D** | Strict-mode variants of `get_floor` / `floor_has_master` (mirror Spec #1 B-MFDB-M) | Same trigger as Spec #1 B-MFDB-M | Open (post-v1) |
| **B-MFWZP-E** | Reorder-capable operator support (mirror Spec #1's reorder-operator clause) | When a future operator reorders floors | Open (post-v1) |
| **B-MFWZP-F** | Topology-equivalence helper (mirror Spec #1 B-MFDB-O) | When dedup of structurally-distinct-but-topologically-equivalent candidates becomes a real need | Open (post-v1) |
| **B-MFWZP-G** | Architecture-governance test suite for prose-authoritative semantic constraints (mirror Spec #2 B-C9-E + Spec #1 governance concerns) | When prose/runtime drift observed OR codebase adopts arch-test infra | Open (post-v1) |
| **B-MFWZP-H** | `iter_floors_with_master_flag` payload expansion (mirror Spec #1 forward-compat caveat) | When orchestration metadata expands (lineage, provenance, topology context) | Open (post-v1) |

---

## § 8 — Build-session readiness

After Ramalingam LOCK:

- 1 new file: `buildemup/domain/multi_floor_candidate.py` (~250 lines incl. docstrings).
- 1 new test file: `buildemup/tests/test_domain_multi_floor_candidate.py` (~35 tests).
- `c11a/cache.py` line 68: `C11A_CACHE_KEY_VERSION: str = "v1.1.0"` → `"v1.2.0"` (cumulative bump from Spec #2's v1.1.0).
- No modifications to any other existing code.

Estimated build effort: ~60-90 minutes. Larger than Spec #2 (more helpers, more invariants, ancestry-walking logic) but smaller than Spec #4.

---

## § 9 — Status

- **v0.2 PROPOSED. PENDING Ramalingam LOCK adjudication.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- Patch-eligibility: critique surfaced before LOCK produces v0.3 PROPOSED.
- After LOCK: spec drafting proceeds to **Spec #4 (C11a Amendment v1.1)** — the largest of the four.
- Code work: deferred until all four specs LOCKED.
- **v0.1 → v0.2 was a schema-drift correction.** No critique walks have run yet on this spec — unlike Specs #1 (5 rounds) and #2 (4 rounds). Whether to LOCK at v0.2 immediately or run at least one critique walk first is a Ramalingam decision; see § 10.1 below.

---

## § 10.1 — LOCK timing recommendation

The user's prior directive ("Do the patches and lock it and move in to the next spec doc") was issued before the schema-drift bug was discovered. The bug is now fixed in v0.2.

**Two paths**:

1. **LOCK at v0.2 now**: defensible because Spec #3 closely mirrors Spec #1's converged shape (5 rounds of critique already absorbed via mirroring), and the empirical schema-drift check has run. Risk: critique walks reliably surface real issues — Spec #1 v0.1 had the master-floor-semantics-underpowered critical bug; Spec #2 v0.8 had the orchestration-contextual-metadata critical bug; Spec #3 v0.1 had the schema-drift bug. Inductive expectation: ≥1 more substantive issue likely exists.
2. **Run at least one critique walk on v0.2 first**: more conservative; consistent with the established pattern. v0.3 might converge in 1-2 rounds rather than the 4-5 of earlier specs.

**Lean**: option 2. The schema-drift bug just demonstrated that critique-light convergence isn't safe even when mirroring an already-LOCKED sibling spec. But this is a Ramalingam call.

---

## § 10 — Rule 9 backlog enumeration

| ID | Description | Origin | Trigger | S40-cont scope verdict | Effort |
|---|---|---|---|---|---|
| Spec #1 | `MultiFloorDwellingBrief` v0.5 LOCKED | DONE | DONE | DONE | DONE |
| Spec #2 | C9 Amendment v0.11 LOCKED | DONE | DONE | DONE | DONE |
| **Spec #3** | This spec | Spec #2 LOCK | LOCK pending | IN-FLIGHT | M |
| Spec #4 | C11a Amendment v1.1 — multi-floor pipeline rework | Specs #1-3 LOCKED | After this LOCKs | NEXT after this LOCKs; LARGE | L |
| B-NEW-T3 | M8 multi-floor real upstream wiring | All 4 specs LOCKED | All four LOCK | GATED | L (post-LOCK) |
| B-MFWZP-A through H | This spec's own deferrals | This spec | various | OUT-OF-SCOPE this spec | various (post-v1) |

**Summary**: third of four B-NEW-T3 specs. Output-side mirror of Spec #1 with cross-floor hardening (MFWZP-5/6 enforce what Spec #2 § 3.10 forward-pointed to Spec #4). Eight forward-compat backlog items (B-MFWZP-A through H), all post-v1.

---

**End of MultiFloorWetZonePlannedCandidate Spec v0.2 PROPOSED.**
