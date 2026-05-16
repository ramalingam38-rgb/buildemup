"""
BuildemUp — MultiFloorWetZonePlannedCandidate domain dataclass.

Per Spec #3 v0.3 LOCKED (`02_specs_chronological/94_MultiFloorWetZonePlannedCandidate_SPEC_v0_3_LOCKED.md`).

Third of four LOCKED specs enabling B-NEW-T3 (M8 multi-floor real upstream
wiring). Output-side counterpart to Spec #1 (`MultiFloorDwellingBrief`).
Holds per-floor WetZonePlannedCandidate instances + dwelling-level master
designation. Enforces cross-floor master-designation coherence at
construction (Inv MFWZP-5 / MFWZP-6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Iterator

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
    BUT see § 3.7 and the v0.3 framing refinement: the
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

    DUAL ROLE (CRITICAL-1 + MODERATE-3 from v0.2 critique walk; see § 3.10
    of Spec #3): this wrapper plays three architectural roles
    simultaneously — passive container, correctness authority (MFWZP-5/6),
    and aggregate root for downstream cache/signature/lineage systems.
    """

    floors: tuple[WetZonePlannedCandidate, ...]
    master_bedroom_floor_label: str

    # Implementation-level marker attribute (per S40-continuation handoff § 4):
    # C11a's `is_real_multi_floor_candidate(obj)` looks for this marker.
    # ClassVar so it is NOT a dataclass field — zero impact on equality,
    # hash, repr, or runtime contract. Keeps Spec #3 v0.3 LOCKED's
    # surface unchanged (no dataclass-machinery participation).
    __multi_floor_candidate__: ClassVar[bool] = True

    def __post_init__(self) -> None:
        # Normalize master_bedroom_floor_label using Spec #1's canonical
        # normalizer (re-imported to avoid duplicating the function).
        # Per-floor labels are NOT re-normalized here — they're already
        # canonical because the per-floor briefs were normalized when
        # the source MultiFloorDwellingBrief was constructed (Spec #1
        # § 3.1 nested-rewrite). We only validate consistency.
        normalized_master = _normalize_label(self.master_bedroom_floor_label)
        object.__setattr__(
            self, "master_bedroom_floor_label", normalized_master
        )

        # ---- Inv MFWZP-1: >=2 floors. Single-floor dwellings continue
        # using bare WetZonePlannedCandidate; this wrapper is multi-floor only.
        if len(self.floors) < 2:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate requires len(floors) "
                f">= 2; got {len(self.floors)}. Single-floor outputs should "
                f"use WetZonePlannedCandidate directly."
            )

        # ---- Inv MFWZP-4: every per-floor WetZonePlannedCandidate must be
        # an actual WetZonePlannedCandidate (not None, not a mock).
        # Done BEFORE label derivation so we don't AttributeError on bad input.
        for i, f in enumerate(self.floors):
            if not isinstance(f, WetZonePlannedCandidate):
                raise TypeError(
                    f"MultiFloorWetZonePlannedCandidate.floors[{i}] must be "
                    f"WetZonePlannedCandidate; got {type(f).__name__}."
                )

        # ---- Inv MFWZP-2: per-floor labels (derived from each WZPC's
        # room_sized_candidate.provenance.floor_label) must be unique.
        derived_labels = self._derive_floor_labels()
        if len(set(derived_labels)) != len(derived_labels):
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: per-floor labels must "
                f"be unique across floors; derived {derived_labels!r}."
            )

        # ---- Inv MFWZP-3: master_bedroom_floor_label in derived labels.
        if self.master_bedroom_floor_label not in derived_labels:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: "
                f"master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r} not in derived "
                f"per-floor labels {derived_labels!r}."
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
        # TRUTH-ARBITRATION POLICY (MAJOR-1 from v0.2 critique walk):
        # the emitted room graph is canonical truth; the wrapper-level
        # declaration is validated against the emitted state, not the
        # other way around. Construction REJECTS on disagreement rather
        # than silently adopting the emitted state's label.
        master_floor_label = self._floor_label_of_unique_master_bedroom()
        if master_floor_label != self.master_bedroom_floor_label:
            raise ValueError(
                f"MultiFloorWetZonePlannedCandidate: master bedroom found "
                f"on floor {master_floor_label!r} but wrapper declares "
                f"master_bedroom_floor_label="
                f"{self.master_bedroom_floor_label!r}. This indicates "
                f"upstream orchestration drift between the per-floor C9 "
                f"has_master_bedroom flags and the wrapper-level master "
                f"designation."
            )

    # ----- Read helpers (mirror Spec #1's interface) -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True (Inv MFWZP-1 enforces len >= 2)."""
        return True

    @property
    def floor_labels(self) -> tuple[str, ...]:
        """Tuple of per-floor labels in tuple order (derived from ancestry)."""
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
            f"floor with that label (normalized={normalized!r}); "
            f"available: {derived_labels!r}"
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
        self,
        new_floor_label: str,
        new_per_floor_candidates: tuple[WetZonePlannedCandidate, ...],
    ) -> "MultiFloorWetZonePlannedCandidate":
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
        the C9 -> C10 cascade with the new per-floor brief tuple before
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
        self,
        floor_label: str,
        new_wzpc: WetZonePlannedCandidate,
    ) -> "MultiFloorWetZonePlannedCandidate":
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
        ``floor_label: str`` directly as a top-level field. It is NOT
        nested under a ``floor_room_brief`` attribute — that was a v0.1
        spec error caught by empirical check before LOCK.

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
                    f"MultiFloorWetZonePlannedCandidate.floors[{i}]: "
                    f"cannot derive floor_label from ancestry chain "
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
            "MultiFloorWetZonePlannedCandidate."
            "_floor_label_of_unique_master_bedroom: no master bedroom "
            "found despite Inv MFWZP-5 having passed. Internal contract "
            "violation."
        )


__all__ = ["MultiFloorWetZonePlannedCandidate"]
