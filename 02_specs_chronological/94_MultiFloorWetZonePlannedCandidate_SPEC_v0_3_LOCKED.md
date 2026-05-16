# MULTI-FLOOR WET-ZONE PLANNED CANDIDATE SPEC v0.3 LOCKED — output-side multi-floor wrapper (B-NEW-T3 enabler #3 of 4)

**Component**: NEW domain dataclass (lives at `buildemup/domain/multi_floor_candidate.py`).
**Spec status**: **v0.3 LOCKED.** Ramalingam directive: "Lock it and let's move on to next spec doc" (S40-continuation).
**Authority**: Ramalingam directive at S40-continuation. LOCK granted at v0.3 after two critique rounds (v0.1 schema-drift → v0.2; v0.2 → v0.3 architecture refinements). A third round was explicitly skipped because the reviewer's verdict on v0.3 was "very close to LOCK quality... very few remaining immediate structural flaws" and the critique surfaced zero spec-text patches.
**Authored**: S40-continuation, post-v0.2 critique walk.
**Driver**: Spec #3 of 4. Output-side counterpart to Spec #1 (`MultiFloorDwellingBrief`).

**v0.3 vs v0.2**: documentation-polish round addressing v0.2 critique items. **No schema or runtime changes.** Three single-paragraph patches (CRITICAL-1 dual-role acknowledgement → new § 3.10; MAJOR-1 emitted-room-graph-as-canonical-truth → § 3.2 MFWZP-6 commentary; MAJOR-4 framing refinement on MFWZP-5/6) + four new backlog filings (B-MFWZP-I through L). Functionally and structurally identical to v0.2.

**Note on this file vs file 93 (PROPOSED)**: file 93 preserves the PROPOSED text for chronological history per Rule 3. File 94 is the LOCKED version with status fields updated. Spec content (schema, invariants, behaviour, test plan) is identical between files.

---

## § 0 — LOCK declaration

**v0.3 LOCKED at S40-continuation per Ramalingam directive ("Lock it and let's move on to next spec doc").**

Per Rule 8 (LOCK authority belongs to Ramalingam alone), this declaration constitutes the LOCK trigger. v0.3 PROPOSED contents are promoted to v0.3 LOCKED with no further patches. The PROPOSED text is preserved chronologically at file 93 per Rule 3.

**Critique walk history**:
- v0.1 PROPOSED → empirical schema check caught ancestry-path bug (`provenance.floor_room_brief.floor_label` was wrong; correct is `provenance.floor_label`).
- v0.1 PROPOSED → v0.2 PROPOSED (schema-drift correction; three sites fixed in `_derive_floor_labels` body, error message, docstring).
- v0.2 PROPOSED → critique walk #1 → v0.3 PROPOSED (CRITICAL-1 dual-role acknowledgement; MAJOR-1 truth-arbitration policy; MAJOR-4 framing refinement; 4 new backlog items).
- v0.3 PROPOSED → critique walk #2 → **LOCKED**. Reviewer surfaced 14 items, all rejected as non-actionable observations or already-filed items. Reviewer's verdict: "very few remaining immediate structural flaws... a mature, internally self-consistent architecture spec."

**Convergence summary**: schema set in v0.1 (with one path-walk bug fixed in v0.2). v0.3 added documentation polish from the first proper critique walk. v0.4 was skipped because critique walk #2 surfaced zero spec-text patches — the natural LOCK point.

**Critique walk #2 actionable items** (zero spec changes, but two priority signals worth preserving):
- CRITICAL-1 priority signal: "B-MFWZP-I is not optional long-term. It is foundational governance infrastructure." File against `04_backlog/v0_2_backlog_S40_continuation_additions.md` post-LOCK if priority elevation desired.
- CRITICAL-2 priority signal: "the risk is deeper than documentation synchronization." Reinforces B-MFWZP-J; ditto post-LOCK filing.

---

## § 0.1 — Delta from v0.2 → v0.3 (critique walk patches)

v0.2 PROPOSED received an external critique with 14 items. Reviewer noted
"this is a strong spec" and "LOCK READINESS: high" but recommended at
least one additional critique round because "this spec introduces
genuinely new architecture behaviour, not merely mirrored structure."
Verdicts:

| Item | Verdict | Patch site |
|---|---|---|
| CRITICAL-1 (wrapper as dual-role passive container + correctness authority) | ACCEPT | New § 3.10; new B-MFWZP-I (invariant-placement principle) |
| CRITICAL-2 (three correctness layers create synchronization fragility) | BACKLOG ONLY | New B-MFWZP-J (cross-spec invariant registry) |
| MAJOR-1 (wrapper owns truth arbitration — emitted-room-graph as canonical) | ACCEPT | § 3.2 MFWZP-6 commentary |
| MAJOR-2 (ancestry-chain dependency fragile) | BACKLOG ONLY | New B-MFWZP-K (`WetZonePlannedCandidate.floor_label` property in future C10 amendment) |
| MAJOR-3 (wrapper centralizes cache identity) | REJECT | None — reviewer-acknowledged "probably unavoidable" |
| MAJOR-4 ("invalid states unreachable" partial) | ACCEPT | § 2 docstring + § 3.2 + class docstring framing refinement |
| MAJOR-5 (mutation asymmetry → conceptual load) | BACKLOG ONLY | New B-MFWZP-L (mutation taxonomy) |
| MODERATE-1 (mirror of Spec #1 risks asymmetric drift) | REJECT | None — reviewer-acknowledged "probably acceptable" |
| MODERATE-2 (depends on stable label normalization) | REJECT | None — already covered by Spec #1 § 3.6 normalization-versioning contract |
| MODERATE-3 (wrapper acts like aggregate root) | ACCEPT (combined w/ CRITICAL-1) | § 3.10 explicitly names the role |
| MODERATE-4 (derived state preferred over duplicate) | REJECT | None — already documented in § 4 design choices |
| MINOR-1 (trust-boundary moved Spec #4 → Spec #3) | REJECT | None — already explicit in § 1, § 3.2, § 3.9 |
| MINOR-2 (helpers resemble orchestration APIs) | REJECT | None — already covered by § 3.3 / Spec #1 patterns |
| MINOR-3 (cache-version churn pattern expanding) | REJECT | None — already covered by Spec #2 B-C9-C |
| MINOR-4 (cross-spec prose synchronization burden) | REJECT | None — non-actionable maturity signal |

**Net schema delta from v0.2**: NONE. v0.3 adds zero new fields, helpers,
runtime logic, validations, or tests. Three single-paragraph patches +
four new backlog filings.

Eight rejects with reasoning preserved. Three backlog-only items
(B-MFWZP-J, K, L). Four spec-text patches (CRITICAL-1+MODERATE-3 share
§ 3.10 site).

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
    assertion that Spec #2 v0.11 § 3.10 forward-pointed to Spec #4 —
    BUT see § 3.7 and the v0.3 framing refinement below: the
    construction-time guarantee covers **master-designation coherence**
    only, NOT broader architectural plausibility.

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
because it makes the **master-designation-coherence** invalid states
structurally unreachable.

**Framing refinement** (MAJOR-4 from v0.2 critique walk): the
"structurally unreachable" guarantee covers **master-designation
coherence ONLY**, not broader architectural plausibility. A wrapper
whose floors all lack kitchens, whose accessibility is impossible, whose
plumbing is non-circulating, or whose suite-graph is disconnected can
still be successfully constructed — Inv MFWZP-1 through MFWZP-6 don't
catch any of those. Spec consumers MUST NOT interpret
"valid `MultiFloorWetZonePlannedCandidate`" as "architecturally
plausible dwelling." The narrower master-designation guarantee is what
construction enforces; broader sanity is downstream's responsibility
(C11a scoring, post-pipeline validation). See § 3.7 for the
construction-vs-plausibility separation.

**Truth-arbitration policy** (MAJOR-1 from v0.2 critique walk): when
MFWZP-6 reconciles `master_bedroom_floor_label` (wrapper-level
declaration) against the per-floor C9 emitted state (which floor's
bedroom #1 actually has `is_master=True`), **the emitted room graph is
canonical truth**. The wrapper-level declaration is validated against
the emitted state, not the other way around. If they disagree, MFWZP-6
rejects construction with a `ValueError` — the wrapper does NOT silently
adopt the emitted state's floor label as the new `master_bedroom_floor_label`,
because doing so would mask orchestration bugs in upstream
`iter_floors_with_master_flag()` consumption. This policy MUST be
preserved through future amendments. If a future selector strategy
introduces ambiguity about "what counts as the authoritative master,"
the resolution belongs in a separate amendment that explicitly
re-adjudicates the truth source — not in silent wrapper behaviour.

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

### § 3.10 — The wrapper's dual role: passive container + correctness authority + aggregate root (CRITICAL-1 + MODERATE-3)

`MultiFloorWetZonePlannedCandidate` plays three architectural roles
simultaneously, and v0.3 documents this explicitly to prevent future
amendments from accidentally expanding (or contracting) any of them
without deliberate review:

1. **Passive container** (the role v0.1 emphasized): holds per-floor
   `WetZonePlannedCandidate` instances and dwelling-level master
   designation. Provides read access (`get_floor`, `floor_labels`,
   `iter_floors_with_master_flag`).
2. **Correctness authority** (the role MFWZP-5 + MFWZP-6 add): enforces
   cross-floor master-designation coherence at construction. This
   hardens what Spec #2 v0.11 § 3.10 forward-pointed to Spec #4
   orchestrator validation, by making the invalid state structurally
   unreachable rather than runtime-rejectable.
3. **Aggregate root** (a label borrowed from DDD): the wrapper IS the
   identity of the multi-floor whole for downstream systems. C11a cache
   keys, signature derivation, lineage classification, and equality
   semantics ALL bind to the wrapper instance, not to its constituent
   per-floor candidates. Mutation operations return new wrappers, not
   detached per-floor candidates.

The dual/triple role is intentional. It is also a precedent for future
amendments to be cautious about. Specifically:

- **Adding cross-floor invariants** (extending role #2): every new
  invariant beyond MFWZP-5/6 expands the wrapper's correctness-authority
  surface. The bar for adding one is: "this invariant cannot be enforced
  meaningfully at any other layer" (per-floor C9, orchestration-level
  Spec #4, downstream scoring). Convenience is NOT sufficient
  justification (mirrors Spec #2 v0.11 § 3.9 precedent-narrowing rule).
- **Adding metadata fields** (extending role #1): each new field that
  participates in equality/hash propagates into cache identity and
  forces a `C11A_CACHE_KEY_VERSION` bump per Spec #1 § 3.6 contract.
  Each new field that does NOT participate in equality/hash creates
  identity asymmetry (two wrappers compare equal but carry different
  metadata) which has its own correctness implications.
- **Adding mutation helpers** (extending role #3): each new helper
  defines a new mutation category. The current set (`with_floor_replaced`
  for single-floor ops, `with_master_on` for dwelling-level ops) covers
  the M1-M9 operator family. Future operators that don't fit either
  shape need a new helper with explicit lineage classification semantics
  (mirrors Spec #1 § 3.5 reorder-operator clause).

**Architectural-principle backlog item** (filed as B-MFWZP-I from
v0.2 critique walk CRITICAL-1): a future amendment may formalise
"which invariants belong on the wrapper type itself, versus the
orchestrator, versus downstream validation?" as a written principle.
For v0.3 the answer is captured implicitly via the bullets above and
the precedent set by MFWZP-5/6 (master-designation coherence is the
ONLY cross-floor invariant the wrapper enforces; everything else is
per-floor or downstream).

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
| **B-MFWZP-I** (NEW from v0.2 critique walk CRITICAL-1) | Formalise "which invariants belong on the wrapper type itself, versus the orchestrator, versus downstream validation?" as a written architectural principle. Currently captured implicitly in Spec #3 v0.3 § 3.10 + the precedent that MFWZP-5/6 are the only cross-floor invariants the wrapper enforces. As more cross-floor invariants surface (across all four B-NEW-T3 specs), formalising the placement principle becomes useful | When ≥2 additional cross-floor invariants are proposed for inclusion on this wrapper or sibling wrappers | Open (post-v1) |
| **B-MFWZP-J** (NEW from v0.2 critique walk CRITICAL-2) | Cross-spec invariant registry / centralized architectural invariant documentation. Multi-floor correctness is now distributed across Specs #1 (declarative), #2 (per-floor materialization), #3 (output-side global), and #4 (orchestration). The architecture relies on prose synchronization across these specs; future changes to selector / floor-label / topology / mutation semantics may fracture the correctness chain subtly | When ≥1 cross-spec semantic-drift bug is discovered in practice, OR when codebase adopts ADR / invariant-registry infrastructure (see also Spec #1 B-MFDB-N spec restructure, Spec #2 B-C9-G governance convention — overlapping concerns) | Open (post-v1) |
| **B-MFWZP-K** (NEW from v0.2 critique walk MAJOR-2) | Promote ancestry-walk to canonical interface property: add `floor_label: str` as a `@property` on `WetZonePlannedCandidate` itself (in C10) that encapsulates the `room_sized_candidate.provenance.floor_label` walk. Spec #3's `_derive_floor_labels` then reads `f.floor_label` instead of walking ancestry. Reduces fragility when C10's provenance schema evolves (the v0.1 schema-drift bug demonstrated this fragility concretely) | When a future C10 amendment opens (any reason); add the property as a side-improvement | Open — addressed via future C10 amendment |
| **B-MFWZP-L** (NEW from v0.2 critique walk MAJOR-5) | Formal mutation taxonomy — categorize all C11a operators by mutation scope (local single-floor / cascading per-floor / dwelling-level / orchestration-wide). Currently Spec #3 has two mutation helpers (`with_floor_replaced` for M1-M7/M9 single-floor ops; `with_master_on` for M8 dwelling-level). Future operators that don't fit either shape would force ad-hoc helpers with unclear semantics | When a future operator is proposed that doesn't fit either existing helper, OR when ≥3 mutation helpers exist on the wrapper | Open (post-v1) |

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

- **v0.3 LOCKED at S40-continuation per Ramalingam directive.**
- Authority: Rule 8 — LOCK authority belongs to Ramalingam alone.
- After LOCK: spec drafting proceeds to **Spec #4 (C11a Amendment v1.1)** — the largest of the four — in this same session.
- Code work: deferred until Spec #4 LOCKED.

**Spec #3 of 4 — DONE.** One remaining: C11a Amendment v1.1 (the large pipeline-rework spec).

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

**Summary**: third of four B-NEW-T3 specs. Output-side mirror of Spec #1 with cross-floor hardening (MFWZP-5/6 enforce what Spec #2 § 3.10 forward-pointed to Spec #4). Twelve forward-compat backlog items (B-MFWZP-A through L), all post-v1. v0.3 added 4 new items (I, J, K, L) from v0.2 critique walk.

---

**End of MultiFloorWetZonePlannedCandidate Spec v0.3 LOCKED.**

**Spec #3 of 4 in the B-NEW-T3 sequence — LOCKED.** Next: Spec #4 (C11a Amendment v1.1 — multi-floor pipeline rework, the LARGE one).
