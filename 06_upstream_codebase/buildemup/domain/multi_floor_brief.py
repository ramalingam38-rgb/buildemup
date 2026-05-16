"""
BuildemUp — MultiFloorDwellingBrief domain dataclass.

Per Spec #1 v0.5 LOCKED (`02_specs_chronological/85_MultiFloorDwellingBrief_SPEC_v0_5_LOCKED.md`).

First of four LOCKED specs enabling B-NEW-T3 (M8 multi-floor real upstream
wiring). Wraps a tuple of single-floor FloorRoomBrief instances plus
dwelling-level state (which floor's bedrooms include the master, and how
the master room within that floor is selected).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterator, Literal

from buildemup.domain.floor_brief import FloorRoomBrief


# Current version: only one selector strategy supported. The Literal type
# encodes the single-value constraint at the type level, AND __post_init__
# enforces it at runtime. Future amendments may widen this Literal
# (e.g., to "explicit_id" or "largest_area"); doing so will require a
# separate v0.X amendment + cache-key version bump.
MasterBedroomSelector = Literal["first_bedroom"]

# Tuple of all currently-permitted selector values. Single-element in the
# current version; widened in future amendments. Used for runtime validation
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

    NOTE on label normalization: floor labels are normalized at
    construction (lowercased, stripped, internal-whitespace collapsed to
    underscore). This protects cache and signature stability against
    trivial variants like "Ground" / "ground " / "ground floor". See
    § 3.1 of Spec #1 v0.5 for exact normalization rules and their
    deliberate non-coverage of semantic aliases.

    NOTE on identity-vs-display label conflation (MAJOR-2 from v0.3
    critique walk): ``floor_label`` currently serves BOTH as canonical
    identity key (cache, hash, equality, master comparison) AND as a
    human-readable display string. These goals diverge as systems mature
    (multilingual UI, localization, alias handling). v0.5 deliberately
    keeps the single-string design — splitting identity from display
    is a future migration concern, not a current correctness concern,
    but spec consumers should be aware that this conflation is known
    and will need addressing when UI-facing requirements grow.

    NOTE on nested-object rewrite (CRITICAL-1 from v0.2 critique walk):
    construction REWRITES nested FloorRoomBrief instances by
    reconstructing them with normalized labels. ``brief.floors[0]`` is
    NOT the same Python object as the FloorRoomBrief passed in.
    Furthermore, when normalization changes a label (e.g., "GROUND" →
    "ground"), the rewritten FloorRoomBrief is **not equal** to the
    original under standard dataclass equality and **hashes differently**.
    Concretely:

        floor = FloorRoomBrief(floor_label="GROUND", ...)
        my_set = {floor}
        brief = MultiFloorDwellingBrief(floors=(floor, ...), ...)
        # brief.floors[0] != floor          (different floor_label)
        # brief.floors[0] not in my_set     (different hash)

    Callers who hold references to the original FloorRoomBrief objects,
    OR who use them as keys in sets / dicts / lookup tables / lineage
    maps, MUST treat the wrapped versions as distinct entities. To avoid
    surprises: pre-normalize floor labels before constructing
    ``FloorRoomBrief`` instances, OR keep a separate mapping from your
    original objects to their wrapped counterparts via
    ``brief.get_floor(label)``.

    CANONICAL OWNERSHIP (CRITICAL-1 from v0.4 critique walk): after
    construction, the rewritten normalized floor briefs inside
    ``MultiFloorDwellingBrief.floors`` are the **canonical authoritative
    floor objects** for all downstream operations. Lineage systems,
    caches, mutation operators, signature derivation, and external
    registries MUST reference the wrapped instances (via
    ``brief.floors[i]``, ``brief.get_floor(label)``, or
    ``iter_floors_with_master_flag()``), NOT the original
    pre-construction `FloorRoomBrief` objects. Mixing the two forms
    risks identity/equality drift and divergent cache slots.

    NOTE on construction-vs-plausibility: construction success does NOT
    imply architectural plausibility. A brief whose floors all lack
    kitchens is structurally valid but architecturally degenerate.
    Cross-floor sanity is downstream's responsibility (C5 topology
    selection, C9 room sizing).
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

        # Inv MFDB-5 is a derivation contract; see § 3.2 of Spec #1.
        # It does not require runtime checks beyond what MFDB-3 + MFDB-4
        # already guarantee (the master_bedroom_floor_label points to
        # exactly one floor; floor_has_master() returns True for exactly
        # that floor and False for all others).

    # ----- Read helpers -----

    @property
    def is_multi_floor(self) -> bool:
        """Always True for this type (Inv MFDB-1 enforces len >= 2).

        Exposed as a property so C11a's existing duck-typed
        ``_is_multi_floor()`` helper detects the type without needing
        an isinstance check. See § 4 of Spec #1 for the transitional-
        compatibility note.
        """
        return True

    def get_floor(self, label: str) -> FloorRoomBrief:
        """Return the floor brief for the given label.

        Label is normalized before lookup so callers can pass the
        unnormalized form (public lookup helpers normalize inputs;
        stored identity remains exact normalized strings).
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
        Honours Inv MFDB-5 — exactly one floor is canonically designated
        as the master floor.

        Label is normalized before comparison (public lookup helpers
        normalize; stored identity remains exact normalized strings).

        SEMANTIC COUPLING NOTE (MAJOR-1 from v0.3 critique walk):
        this method's behaviour is normalization-dependent. The lookup
        chain is:

            floor_has_master(label)
                -> _normalize_label(label)
                    -> compare canonical strings

        Any future change to ``_normalize_label()`` semantics implicitly
        changes ``floor_has_master()`` semantics. This is the intended
        coupling — there is one canonical comparison strategy — but spec
        consumers should treat normalization changes as also changing
        master-derivation behaviour, and exercise the cache/signature
        version-bump contract (§ 3.6) accordingly.
        """
        return _normalize_label(label) == self.master_bedroom_floor_label

    def iter_floors_with_master_flag(
        self,
    ) -> Iterator[tuple[FloorRoomBrief, bool]]:
        """Iterate floors yielding ``(floor_brief, has_master_bedroom)``.

        DESIGN NOTE: this iteration helper is INTENTIONALLY orchestration-
        oriented. It zips the existing ``floors`` field with the canonical
        ``floor_has_master()`` derivation so downstream orchestration code
        (C9 amendment input prep, C11a per-floor pipeline loops) does not
        re-implement the pairing independently. This is layering-blur but
        the cost-of-not-doing-it (orchestration drift across multiple call
        sites re-implementing the same zip) outweighs the architectural
        purity gain. If a future amendment introduces a dedicated
        orchestration adapter layer, this method may be relocated there.

        FORWARD-COMPAT CAVEAT (MAJOR-3 from v0.3 critique walk): the
        ``(FloorRoomBrief, bool)`` payload shape is intentionally minimal
        for the current version. Future orchestration may need richer
        per-floor metadata at which point either:
        (a) the payload shape expands (potentially breaking callers), or
        (b) this method is supplemented/replaced by a richer iterator and
            this method becomes a thin compatibility shim.
        Spec consumers should NOT build infrastructure that assumes the
        2-tuple payload is permanent.

        The bool is True for exactly one floor per Inv MFDB-5. Iteration
        order matches ``self.floors`` tuple order (see § 3.5 of Spec #1).
        """
        for f in self.floors:
            yield f, self.floor_has_master(f.floor_label)

    # ----- Mutation helpers (return new instances; type is frozen) -----

    def with_master_on(self, new_floor_label: str) -> "MultiFloorDwellingBrief":
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

    SCOPE (MAJOR-1 from v0.2 critique walk):
    These rules ONLY protect against trivial whitespace/case variants.
    They do NOT canonicalize semantic aliases. The following are all
    DISTINCT labels under the current normalization:
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


__all__ = [
    "MultiFloorDwellingBrief",
    "MasterBedroomSelector",
    "_normalize_label",
    "_VALID_SELECTORS",
]
