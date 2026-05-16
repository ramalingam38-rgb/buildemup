"""
BuildemUp — Component 15 — contracts (cultural profile + threaded metadata)
============================================================================

Per C15 SPEC v0.2 LOCKED (v0.1 § 1.1 + § 11 + v0.2 A3 + A6 + A7).

This module provides:

1. **CulturalProfile** — StrEnum of cultural lenses C15 applies to
   determine which checks run, which severity rules apply, and which
   `cultural_preference` checks emit `not_applicable`. Per v0.2 A3:
   REQUIRED parameter, no default. ≥3 sub-variants at v1.0 LOCK must
   produce MEASURABLY DIFFERENT outputs on the same input layout.

   At v0.2 LOCK SKETCH, the enum is defined; per-profile differentiated
   check behavior lives in Sub-2+ when checks are wired. The enum
   itself is part of the LOCKED contract.

2. **FloorInfo** — per-floor metadata struct used by Dimension 7
   (first-floor living) checks. PARTIAL at v1: not all callers
   thread this yet; missing data → check emits not_applicable per
   Inv P6.

3. **ProblemAnalysisMetadata** — the per-candidate metadata bundle
   threaded into C15's orchestrator entry points (per v0.1 § 11). The
   metadata is NOT encoded in C14's LOCKED schema; the orchestrator
   accepts it as a separate parameter (mirroring the C14 pattern
   tracked by B-PROJECT-PIPELINE-METADATA-CONTRACT).

Per v0.2 A6 + Inv P19: the v1 baseline of `dimensions_not_evaluated`
lives in `versioning.DIMENSIONS_NOT_EVALUATED_V1`. ProblemAnalysisMetadata
does NOT carry it — the constant is emitted into the report directly
to make incompleteness visible without per-call customization.

Frozen for hash-stability + replay determinism (Inv P2 byte-equal).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


# =============================================================================
# CulturalProfile (per v0.2 A3)
# =============================================================================

class CulturalProfile(StrEnum):
    """Per v0.2 A3.

    The cultural lens under which C15 evaluates a layout. REQUIRED
    parameter of every C15 entry point; **no default exists** (Inv P17).
    Missing cultural_profile → MissingMetadataError.

    The string values use short ASCII identifiers (`in_mc_*`, `in_li_*`,
    `in_nri_*`) to support stable serialization, stable cache-key
    contribution, and unambiguous logging. The Enum NAMES use the
    long-form spec phrasing for human readability.

    At v0.2 LOCK SKETCH, six profiles are enumerated:

      INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN
          Tamil Nadu multigenerational household pattern. Strong
          preference for: dedicated pooja room, sit-down floor seating
          compatibility, monsoon-aware ventilation, separate kitchen +
          dining (no open-plan), guest room near entry.

      INDIAN_MIDDLE_CLASS_KERALA_COURTYARD
          Kerala nalukettu / courtyard tradition. Strong preference for:
          central courtyard with surrounding rooms, cross-ventilation
          through the courtyard, ritual procession routes from entry
          through public rooms to inner sanctum.

      INDIAN_MIDDLE_CLASS_COMPACT_URBAN
          Bangalore/Mumbai compact urban apartment-style residential.
          Tolerates: open-plan living/dining, smaller pooja niche
          instead of dedicated room, kitchen on the public side.

      INDIAN_MIDDLE_CLASS_GENERIC
          Least opinionated. Treats most Indian residential conventions
          as `nice_to_have` rather than `important`. Used when family
          preferences aren't strongly tilted to any sub-variant.

      INDIAN_LOWER_INCOME_INCREMENTAL
          Incremental-construction pattern: house built in phases as
          budget allows. Tolerates partial layouts, exterior rooms
          added later, non-canonical room counts. Per v0.2 A11
          B-C15-CLASS-BIAS-AUDIT: this profile exists specifically to
          avoid the default-profile assumption that all homes follow
          aspirational middle-class room programs.

      INDIAN_NRI_RETURNEE
          NRI / diaspora returnee pattern. Strong preference for:
          Western-style master suite with attached bath, study/home
          office room, sometimes open-plan kitchen.

    All six are valid at v0.2. Per B-C15-CULTURAL-PROFILE-COVERAGE
    (LOCK-mandatory, v1.0), ≥3 sub-variants must produce MEASURABLY
    DIFFERENT outputs on the same input layout. The differentiation
    happens at the CHECK level (Sub-2+), not at the enum level here.

    Cache-relevant: YES. The active profile is part of the report's
    cache key composition (per v0.2 A3 cache-relevance flag).

    Future expansion (v2.x) per B-C15-CULTURAL-PROFILE-EXPANSION:
    regional Indian variants (Bengali, Punjabi, Marathi, etc.) and
    eventually non-Indian variants (US suburban, EU apartment, etc.).
    """
    INDIAN_MIDDLE_CLASS_TAMIL_MULTIGEN = "in_mc_tamil_multigen"
    INDIAN_MIDDLE_CLASS_KERALA_COURTYARD = "in_mc_kerala_courtyard"
    INDIAN_MIDDLE_CLASS_COMPACT_URBAN = "in_mc_compact_urban"
    INDIAN_MIDDLE_CLASS_GENERIC = "in_mc_generic"
    INDIAN_LOWER_INCOME_INCREMENTAL = "in_li_incremental"
    INDIAN_NRI_RETURNEE = "in_nri_returnee"


# Set of valid cultural-profile string values, for input validation.
VALID_CULTURAL_PROFILE_VALUES: Final[frozenset[str]] = frozenset(
    p.value for p in CulturalProfile
)
"""All legal CulturalProfile string values. Used by orchestrator at
ingress to validate metadata before any check evaluation.

Cache-relevant: derived from the enum; bumps with CulturalProfile
membership."""


# =============================================================================
# FloorInfo (per v0.1 § 1.1 + § 0.4 PARTIAL data envelope for Dim 7)
# =============================================================================

@dataclass(frozen=True)
class FloorInfo:
    """Per v0.1 § 1.1 / § 0.4.

    Per-floor metadata threaded into C15's orchestrator entry point.
    Used by Dimension 7 (first-floor living) checks; missing/empty
    floor_metadata → all Dim-7 checks emit not_applicable with
    `na_reason="floor_metadata_unavailable"` and route to
    B-C15-FLOOR-METADATA backlog.

    Fields:
      floor_id: stable per-floor identifier (e.g., "ground", "first",
        "second"). Lex-ASC sortable; orchestrator uses sort order to
        determine canonical floor sequence.
      is_ground: True iff this floor is at grade level (no stairs to
        reach from outside). At v1 exactly one floor per layout should
        carry is_ground=True; multi-entry-grade designs (e.g.,
        split-level on a slope) violate this and emit a
        `compact_incremental` or `split_level_circulation` hint
        (per v0.2 A7).
      has_entry: True iff this floor carries the main_entry_room_id.
        Exactly one floor per layout should be True.
      room_ids: tuple of room_ids placed on this floor. Sorted lex-ASC
        for replay determinism (Inv P2). Must be subset of the
        candidate's placed_room_ids.

    Frozen. Inv P2 / P5: read-only after construction; never mutated.
    """
    floor_id: str
    is_ground: bool
    has_entry: bool
    room_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        # Defensive: floor_id must be non-empty for canonical sorts.
        if not isinstance(self.floor_id, str):
            raise TypeError(
                f"FloorInfo.floor_id must be str; got {type(self.floor_id)}"
            )
        if not self.floor_id:
            raise ValueError(
                "FloorInfo.floor_id must be a non-empty string"
            )

        # Defensive: bool checks. dataclasses don't validate types at
        # construction; we do.
        if not isinstance(self.is_ground, bool):
            raise TypeError(
                f"FloorInfo.is_ground must be bool; got {type(self.is_ground)}"
            )
        if not isinstance(self.has_entry, bool):
            raise TypeError(
                f"FloorInfo.has_entry must be bool; got {type(self.has_entry)}"
            )

        # room_ids: tuple, all strings, sorted lex-ASC, unique.
        if not isinstance(self.room_ids, tuple):
            raise TypeError(
                f"FloorInfo.room_ids must be tuple; got {type(self.room_ids)}"
            )
        for rid in self.room_ids:
            if not isinstance(rid, str):
                raise TypeError(
                    f"FloorInfo.room_ids entries must be str; "
                    f"got {type(rid)} in {self.room_ids!r}"
                )
            if not rid:
                raise ValueError(
                    "FloorInfo.room_ids must contain non-empty strings"
                )

        if list(self.room_ids) != sorted(self.room_ids):
            raise ValueError(
                f"FloorInfo.room_ids must be sorted lex-ASC for replay "
                f"determinism; got {self.room_ids!r}"
            )

        if len(set(self.room_ids)) != len(self.room_ids):
            raise ValueError(
                f"FloorInfo.room_ids must be unique; got {self.room_ids!r}"
            )


# =============================================================================
# ProblemAnalysisMetadata (per v0.1 § 11 + v0.2 A3 + A6 + A7)
# =============================================================================

@dataclass(frozen=True)
class ProblemAnalysisMetadata:
    """Per v0.1 § 11. Per-candidate metadata bundle threaded into C15's
    orchestrator entry.

    Per the recurring pipeline-metadata pattern (B-PROJECT-PIPELINE-
    METADATA-CONTRACT), upstream-derived metadata that C14's LOCKED
    schema does NOT encode is carried as a separate parameter into
    C15's entry point.

    Fields:
      cultural_profile (REQUIRED per A3 / Inv P17): the cultural lens.
        Empty/None at metadata construction is NOT permitted — the
        StrEnum has no None member. Callers MUST select a profile.

      placed_room_ids: tuple of room_ids in the candidate, sorted
        lex-ASC. Per Inv P7 every affected_room_ids tuple in the
        eventual ProblemReport must be a subset of this. Defensive
        copy of C12 PlacedCandidate's room IDs.

      room_categories: per-room category strings (e.g., "bedroom",
        "kitchen"). Required non-empty for every placed_room_id;
        missing → MissingMetadataError. Inv P13: checks tagged
        culturally-loaded may emit NOT_APPLICABLE with
        na_reason="cultural_profile_mismatch" when this dict's
        categories don't match what the check's cultural-profile
        scope expects.

      main_entry_room_id: which room owns the main entry. Must be in
        placed_room_ids. Mirrors C14's contract.

      floor_metadata: optional per-floor metadata; empty at v1 if
        upstream doesn't supply it. Dim 7 checks emit not_applicable
        with na_reason pointing to B-C15-FLOOR-METADATA when this is
        empty.

    Frozen. The metadata's identity contributes to C15's cache key
    composition (cultural_profile is cache-relevant; floor_metadata
    is cache-relevant when populated; room_categories is cache-relevant
    when checks consume it).

    NOT carried here (designed deliberately):
      - window placement (Dim 4 — routed to B-C15-WINDOW-DATA)
      - furniture/fixture placement (Dim 9/10 — routed to
        B-C15-FURNITURE-FIT-DATA)
      - envelope orientation (Dim 8 — routed to
        B-C15-ENVELOPE-ORIENTATION)
      Their absence at v1 produces honest NOT_APPLICABLE per Inv P6.
    """
    cultural_profile: CulturalProfile
    placed_room_ids: tuple[str, ...]
    room_categories: dict[str, str]
    main_entry_room_id: str
    floor_metadata: tuple[FloorInfo, ...] = ()

    def __post_init__(self) -> None:
        # cultural_profile must be a CulturalProfile enum member
        # (per A3 / Inv P17). StrEnum equality with strings is
        # permitted, but we require the enum type for type safety.
        if not isinstance(self.cultural_profile, CulturalProfile):
            raise TypeError(
                f"ProblemAnalysisMetadata.cultural_profile must be a "
                f"CulturalProfile member (per v0.2 A3 Inv P17); got "
                f"{type(self.cultural_profile)}"
            )

        # placed_room_ids: tuple of unique non-empty strings, sorted.
        if not isinstance(self.placed_room_ids, tuple):
            raise TypeError(
                f"ProblemAnalysisMetadata.placed_room_ids must be tuple; "
                f"got {type(self.placed_room_ids)}"
            )
        if not self.placed_room_ids:
            raise ValueError(
                "ProblemAnalysisMetadata.placed_room_ids must be non-empty"
            )
        for rid in self.placed_room_ids:
            if not isinstance(rid, str) or not rid:
                raise ValueError(
                    f"ProblemAnalysisMetadata.placed_room_ids must contain "
                    f"non-empty strings; got {self.placed_room_ids!r}"
                )
        if list(self.placed_room_ids) != sorted(self.placed_room_ids):
            raise ValueError(
                f"ProblemAnalysisMetadata.placed_room_ids must be sorted "
                f"lex-ASC (Inv P2 replay); got {self.placed_room_ids!r}"
            )
        if len(set(self.placed_room_ids)) != len(self.placed_room_ids):
            raise ValueError(
                f"ProblemAnalysisMetadata.placed_room_ids must be unique; "
                f"got {self.placed_room_ids!r}"
            )

        # room_categories: dict whose keys cover placed_room_ids.
        if not isinstance(self.room_categories, dict):
            raise TypeError(
                f"ProblemAnalysisMetadata.room_categories must be dict; "
                f"got {type(self.room_categories)}"
            )
        # Keys must be a SUPERSET-or-equal of placed_room_ids; extra
        # entries are tolerated (defensive — upstream may include
        # placeholder entries) but missing entries are not.
        rid_set = set(self.placed_room_ids)
        cat_keys = set(self.room_categories.keys())
        missing = rid_set - cat_keys
        if missing:
            raise ValueError(
                f"ProblemAnalysisMetadata.room_categories must cover every "
                f"placed_room_id; missing entries for: {sorted(missing)!r}"
            )
        for k, v in self.room_categories.items():
            if not isinstance(k, str) or not k:
                raise ValueError(
                    f"ProblemAnalysisMetadata.room_categories keys must be "
                    f"non-empty strings; got key {k!r}"
                )
            if not isinstance(v, str):
                raise TypeError(
                    f"ProblemAnalysisMetadata.room_categories values must "
                    f"be str; got {type(v)} for key {k!r}"
                )

        # main_entry_room_id: must be in placed_room_ids.
        if not isinstance(self.main_entry_room_id, str):
            raise TypeError(
                f"ProblemAnalysisMetadata.main_entry_room_id must be str; "
                f"got {type(self.main_entry_room_id)}"
            )
        if not self.main_entry_room_id:
            raise ValueError(
                "ProblemAnalysisMetadata.main_entry_room_id must be "
                "non-empty"
            )
        if self.main_entry_room_id not in rid_set:
            raise ValueError(
                f"ProblemAnalysisMetadata.main_entry_room_id "
                f"{self.main_entry_room_id!r} must appear in "
                f"placed_room_ids {sorted(rid_set)!r}"
            )

        # floor_metadata: tuple of FloorInfo, possibly empty at v1.
        if not isinstance(self.floor_metadata, tuple):
            raise TypeError(
                f"ProblemAnalysisMetadata.floor_metadata must be tuple; "
                f"got {type(self.floor_metadata)}"
            )
        for fi in self.floor_metadata:
            if not isinstance(fi, FloorInfo):
                raise TypeError(
                    f"ProblemAnalysisMetadata.floor_metadata entries must "
                    f"be FloorInfo; got {type(fi)}"
                )
        # Floor IDs unique + sorted (Inv P2 determinism).
        floor_ids = tuple(fi.floor_id for fi in self.floor_metadata)
        if list(floor_ids) != sorted(floor_ids):
            raise ValueError(
                f"ProblemAnalysisMetadata.floor_metadata must be sorted "
                f"by floor_id lex-ASC; got order {floor_ids!r}"
            )
        if len(set(floor_ids)) != len(floor_ids):
            raise ValueError(
                f"ProblemAnalysisMetadata.floor_metadata floor_ids must "
                f"be unique; got {floor_ids!r}"
            )
        # Every room in floor_metadata.room_ids must be in placed_room_ids.
        # And no room may appear in more than one floor.
        seen_rooms_across_floors: set[str] = set()
        for fi in self.floor_metadata:
            for rid in fi.room_ids:
                if rid not in rid_set:
                    raise ValueError(
                        f"FloorInfo {fi.floor_id!r} references room "
                        f"{rid!r} not in placed_room_ids"
                    )
                if rid in seen_rooms_across_floors:
                    raise ValueError(
                        f"Room {rid!r} appears in multiple floors of "
                        f"floor_metadata; a room belongs to exactly one "
                        f"floor"
                    )
                seen_rooms_across_floors.add(rid)


__all__ = [
    "CulturalProfile",
    "VALID_CULTURAL_PROFILE_VALUES",
    "FloorInfo",
    "ProblemAnalysisMetadata",
]
