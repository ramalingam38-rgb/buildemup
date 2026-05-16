"""
BuildemUp — Component 14 — schema (output + typestate dataclasses)
===================================================================

Per C14 SPEC v0.2 LOCKED. Composed from:
- v0.1 § 1.2 (CirculationGraphReport base shape)
- v0.1 § 1.3 (CirculationFlag dataclass)
- v0.1 § 5 (typestate Successful / Failed + BatchResult)
- v0.2 A1 (raw_RA + real_RA + integration + graph_size_category)
- v0.2 A2 (Inv E3': EXTERNAL exclusion BOTH sides — enforced at construction)
- v0.2 A4 (Split CirculationFlagKind into Structural vs Preference)
- v0.2 A6 (TRUNCATION_META meta-flag added to BOTH enums; Inv E13')
- v0.2 A8 (category_coverage field + category_coverage_low structural flag;
   Inv E18)
- v0.2 A10 (default severity for preference flags is `info`)

All dataclasses are frozen for hash-stability + replay determinism
(Inv E7). Canonical orderings are enforced in __post_init__
(Inv E2 / E3' / E5).

The typestate discipline (per v0.3 B11 inherited from C13) means
downstream consumers MUST pattern-match on
SuccessfulCirculationAnalysis vs FailedCirculationAnalysis — mypy
rejects access to .report on a FailedCirculationAnalysis. This
enforces filtering at the type layer, preventing WARN-mode-failed
candidates from being misused as successful results.

Per v0.1 § 1.4 + v0.2 A4: C14 emits TWO flag-kind enums (Structural,
Preference) AND ALSO converts them into the C13 AdvisoryFlag schema
for downstream consumption via `c14_advisory_flags`. Downstream
consumers (C15) get a uniform `tuple[AdvisoryFlag, ...]` to walk
without needing to know whether a flag came from C13 or C14.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Literal, Optional, Union

# C13 types we re-use directly:
from buildemup.components.c13.schema import (
    AdvisoryFlag,
    AdvisorySeverity,
)

from .cache_keys import C14CacheKeys


# =============================================================================
# Flag-kind enums (per v0.2 A4 split + A6 truncation meta-flag)
# =============================================================================

# Per A6 / A4: the truncation meta-flag value is shared across both
# enums. C14 emits one TRUNCATION_META to whichever tuple was over-cap.
TRUNCATION_META_KIND_VALUE: Final[str] = "truncation_meta"


class StructuralCirculationFlagKind(StrEnum):
    """Per v0.2 A4. Structural flags are closer to universal pathologies
    (any layout where one room is the only path to all others is a
    concern regardless of cultural context).

    Per v0.2 A8: `CATEGORY_COVERAGE_LOW` is a STRUCTURAL flag emitted
    when `category_coverage < category_coverage_low_threshold` (Inv E18).

    Per v0.2 A6: `TRUNCATION_META` is emitted when density cap fires
    (Inv E13').

    Values:
      BOTTLENECK_CONCENTRATION: a single non-corridor room concentrates
        betweenness above threshold (over-reliance on one room as
        crossing point).
      DEAD_END_ISOLATION: a room is reachable only via a single
        non-corridor neighbor (degree-1 path) AND it's habitable.
      CATEGORY_COVERAGE_LOW (NEW v0.2 A8): upstream room-categorization
        coverage below threshold — downstream should verify quality.
      TRUNCATION_META (NEW v0.2 A6): more structural flags would have
        been emitted but the density cap (Inv E13') fired. Explanation
        template lists the count + stable enumeration of suppressed
        kinds.
    """
    BOTTLENECK_CONCENTRATION = "bottleneck_concentration"
    DEAD_END_ISOLATION = "dead_end_isolation"
    CATEGORY_COVERAGE_LOW = "category_coverage_low"
    TRUNCATION_META = TRUNCATION_META_KIND_VALUE


class PreferenceCirculationFlagKind(StrEnum):
    """Per v0.2 A4. Preference flags are culturally-loaded (a
    ceremonial-sequence home may DESIRE high depth; a studio doesn't
    have a privacy gradient).

    Per v0.2 A10: preference flags default to severity=info. Severity
    escalation belongs to C15.

    Per v0.2 A6: TRUNCATION_META appears here too (same string value
    as in StructuralCirculationFlagKind; emission goes to whichever
    tuple was over-cap).

    Values:
      TRANSIT_THROUGH_BEDROOM: a bedroom is on the canonical BFS
        shortest path between two non-bedroom rooms AND no avoidable
        alternate exists (per v0.2 A5 SKETCH definition).
      PRIVACY_GRADIENT_VIOLATION: a private room is SHALLOWER (smaller
        step-depth) than a public room — violates public→private
        monotonicity.
      EXCESSIVE_DEPTH: step_depth_from_entry exceeds configurable
        threshold (default 5; v0.1 § 1.3).
      TRUNCATION_META (NEW v0.2 A6): more preference flags would have
        been emitted but the density cap (Inv E13') fired.
    """
    TRANSIT_THROUGH_BEDROOM = "transit_through_bedroom"
    PRIVACY_GRADIENT_VIOLATION = "privacy_gradient_violation"
    EXCESSIVE_DEPTH = "excessive_depth"
    TRUNCATION_META = TRUNCATION_META_KIND_VALUE


# The union type C15/C17 consume:
CirculationFlagKind = Union[
    StructuralCirculationFlagKind,
    PreferenceCirculationFlagKind,
]


# =============================================================================
# Graph-size-category Literal (per v0.2 A1 Inv E17)
# =============================================================================

GraphSizeCategory = Literal["tiny", "small", "normal"]
"""Per v0.2 A1 Inv E17.

Categorizes node count for downstream consumption gates:
- "tiny"   = k ∈ {1, 2}: most metrics N/A
- "small"  = k == 3:     RRA defined but high-noise
- "normal" = k ≥ 4:      RRA bounded, reliable

Downstream consumers (C15, C17) SHOULD check graph_size_category
before consuming integration/RRA as authoritative signals.
"""

_VALID_GRAPH_SIZE_CATEGORY_VALUES: Final[frozenset[str]] = frozenset(
    {"tiny", "small", "normal"}
)


# =============================================================================
# CirculationFlag (per v0.1 § 1.3 with A4 enum union + A10 default-info)
# =============================================================================

@dataclass(frozen=True)
class CirculationFlag:
    """Per v0.1 § 1.3 + v0.2 A4 + v0.2 A10.

    A single circulation-quality flag emitted by C14.

    Fields:
      flag_kind: a value from StructuralCirculationFlagKind OR
          PreferenceCirculationFlagKind (Union). The tuple it ends up
          in (structural_flags vs preference_flags on
          CirculationGraphReport) discriminates which category emitted
          it.
      affected_room_id: the room this advisory pertains to. For
          TRUNCATION_META, may be the empty string (meta-flag has no
          single affected room).
      severity: info | warning | concern (re-using C13's
          AdvisorySeverity literal). Per v0.2 A10, default severity
          for preference flags is `info`; severity escalation belongs
          to C15.
      explanation_template: human-readable explanation key — C15 UX
          layer interpolates. For TRUNCATION_META, MUST include the
          suppressed-count + stable enumeration of suppressed kinds
          (per A6).
      deduplication_key: stable key for cap enforcement (typically
          `f"{flag_kind}:{affected_room_id}"`). Required non-empty.
    """
    flag_kind: CirculationFlagKind
    affected_room_id: str
    severity: AdvisorySeverity
    explanation_template: str
    deduplication_key: str

    def __post_init__(self) -> None:
        # flag_kind must be a recognized enum value — accept either enum
        # by checking membership in the union of allowed string values.
        if not isinstance(
            self.flag_kind,
            (StructuralCirculationFlagKind, PreferenceCirculationFlagKind),
        ):
            raise TypeError(
                f"CirculationFlag.flag_kind must be a "
                f"StructuralCirculationFlagKind or "
                f"PreferenceCirculationFlagKind value; got "
                f"{type(self.flag_kind).__name__}"
            )

        # affected_room_id is str (may be empty only for TRUNCATION_META).
        if not isinstance(self.affected_room_id, str):
            raise TypeError(
                f"CirculationFlag.affected_room_id must be str; got "
                f"{type(self.affected_room_id).__name__}"
            )
        if (
            not self.affected_room_id
            and str(self.flag_kind) != TRUNCATION_META_KIND_VALUE
        ):
            raise ValueError(
                "CirculationFlag.affected_room_id may be empty ONLY for "
                "TRUNCATION_META meta-flags."
            )

        # severity must be one of the AdvisorySeverity literals.
        if self.severity not in ("info", "warning", "concern"):
            raise ValueError(
                f"CirculationFlag.severity must be one of "
                f"'info' | 'warning' | 'concern'; got {self.severity!r}"
            )

        if not isinstance(self.explanation_template, str) or not self.explanation_template:
            raise ValueError(
                "CirculationFlag.explanation_template must be a non-empty str."
            )

        if not isinstance(self.deduplication_key, str) or not self.deduplication_key:
            raise ValueError(
                "CirculationFlag.deduplication_key must be a non-empty str."
            )


# =============================================================================
# CirculationGraphReport (per v0.1 § 1.2 + v0.2 A1/A4/A6/A8)
# =============================================================================

@dataclass(frozen=True)
class CirculationGraphReport:
    """Per v0.1 § 1.2 + v0.2 A1 (RA→RRA + graph_size_category) +
    v0.2 A4 (structural/preference split) + v0.2 A6 (truncation meta) +
    v0.2 A8 (category_coverage).

    Per-candidate circulation-graph analysis. Frozen for replay (Inv E7).

    Canonical sort enforcement in __post_init__:
    - Inv E2: nodes lex-ASC
    - Inv E3': edges lex-ASC, EXTERNAL excluded BOTH sides (handled at
      construction by orchestrator; schema verifies sort only)
    - Inv E4: primary_edges ⊆ edges
    - Inv E5: per-room metric tuples cover nodes exactly, lex-ASC

    Schema-level numeric invariants:
    - Inv E10: mean_depth ≤ max_depth ≤ len(nodes) - 1 (when k ≥ 2)
    - Inv E11': raw_relative_asymmetry ≥ 0 (no upper bound at small k)
    - Inv E11'': real_relative_asymmetry ∈ [0, ~1.5] for k ≥ 4;
      nan for k < 4
    - Inv E12': integration = 1 / real_relative_asymmetry when RRA > 0;
      inf when RRA == 0; nan for k < 4
    - Inv E17: graph_size_category consistent with len(nodes)
    - Inv E18: category_coverage ∈ [0, 1]

    NOTE on Inv E6 (step_depth_from_entry[main_entry_room_id] == 0):
    main_entry_room_id is upstream metadata not stored in this report.
    The schema enforces the derivable analog: exactly one room has
    step_depth == 0 in a non-empty, connected graph (per Inv E15
    inherited via C13 D13).

    NOTE on Inv E8 (upstream_advisory_flags == input.advisory_flags
    byte-identical): this is an assembly-time invariant verified by the
    orchestrator. Schema accepts any AdvisoryFlag tuple.

    NOTE on Inv E13' (flag density cap): the cap depends on the config's
    flag_density_factor, which the schema doesn't see. Enforced at
    flag emission (Phase δ in orchestrator). Schema accepts any flag
    counts.
    """
    source_placed_candidate_signature: str

    # ── Graph topology (Hillier permeability graph) ─────────────
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    primary_edges: tuple[tuple[str, str], ...]

    # ── Node-level metrics (per Hillier 1984) ───────────────────
    step_depth_from_entry: tuple[tuple[str, int], ...]
    connectivity: tuple[tuple[str, int], ...]
    betweenness_rank: tuple[tuple[str, int], ...]

    # ── Layout-level metrics (per v0.2 A1) ──────────────────────
    mean_depth: float
    max_depth: int
    raw_relative_asymmetry: float
    real_relative_asymmetry: float  # may be nan for k < 4
    integration: float              # may be nan for k < 4; inf when RRA==0
    graph_size_category: GraphSizeCategory

    # ── Quality flags (per v0.2 A4 split) ───────────────────────
    structural_flags: tuple[CirculationFlag, ...]
    preference_flags: tuple[CirculationFlag, ...]

    # ── AdvisoryFlag passthrough + augmentation (per v0.1 § 1.2) ─
    upstream_advisory_flags: tuple[AdvisoryFlag, ...]
    c14_advisory_flags: tuple[AdvisoryFlag, ...]

    # ── Category coverage (per v0.2 A8 Inv E18) ─────────────────
    category_coverage: float

    # ── Provenance (per Inv E16) ────────────────────────────────
    c14_version: str
    c14_metric_version: int
    advisory_schema_version: int

    # ── Cache keys (passed-through from orchestrator) ───────────
    cache_keys: C14CacheKeys

    def __post_init__(self) -> None:
        # ── source signature non-empty ──
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "CirculationGraphReport.source_placed_candidate_signature "
                "must be non-empty."
            )

        # ── Inv E2: nodes lex-ASC, unique ──
        if list(self.nodes) != sorted(self.nodes):
            raise ValueError(
                f"CirculationGraphReport violates Inv E2 — nodes must be "
                f"sorted lex-ASC; got {list(self.nodes)}."
            )
        if len(set(self.nodes)) != len(self.nodes):
            raise ValueError(
                f"CirculationGraphReport violates Inv E2 — nodes must be "
                f"unique; got duplicates in {list(self.nodes)}."
            )

        # ── Inv E3': edges sorted, valid endpoints, no EXTERNAL ──
        # (EXTERNAL exclusion is constructed by orchestrator; schema
        # verifies edges are sorted lex-ASC and endpoints are within
        # nodes.)
        if list(self.edges) != sorted(self.edges):
            raise ValueError(
                f"CirculationGraphReport violates Inv E3' — edges must be "
                f"sorted lex-ASC; got {list(self.edges)}."
            )
        node_set = frozenset(self.nodes)
        for a, b in self.edges:
            if a not in node_set or b not in node_set:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E3' — edge "
                    f"({a!r}, {b!r}) references unknown room_id (nodes: "
                    f"{list(self.nodes)})."
                )
            if a > b:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E3' — each edge "
                    f"must satisfy room_a <= room_b lex-ASC; got "
                    f"({a!r}, {b!r})."
                )

        # ── Inv E4: primary_edges ⊆ edges ──
        edge_set = set(self.edges)
        for pe in self.primary_edges:
            if pe not in edge_set:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E4 — primary edge "
                    f"{pe} is not in the edges set."
                )
        # primary_edges also sorted lex-ASC (canonical).
        if list(self.primary_edges) != sorted(self.primary_edges):
            raise ValueError(
                f"CirculationGraphReport violates Inv E4 — primary_edges "
                f"must be sorted lex-ASC; got {list(self.primary_edges)}."
            )

        # ── Inv E5: per-room metric tuples cover nodes exactly, lex-ASC ──
        for field_name in (
            "step_depth_from_entry",
            "connectivity",
            "betweenness_rank",
        ):
            metric_tuple = getattr(self, field_name)
            metric_room_ids = [r for r, _ in metric_tuple]
            if metric_room_ids != sorted(metric_room_ids):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E5 — "
                    f"{field_name} must be sorted lex-ASC by room_id; got "
                    f"{metric_room_ids}."
                )
            if tuple(metric_room_ids) != tuple(self.nodes):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E5 — "
                    f"{field_name} must cover nodes exactly; expected "
                    f"{list(self.nodes)}, got {metric_room_ids}."
                )

        # ── Inv E6 (analog): exactly one depth==0 entry in non-empty graph ──
        if self.nodes:
            zero_depth_count = sum(
                1 for _, d in self.step_depth_from_entry if d == 0
            )
            if zero_depth_count != 1:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E6 analog — "
                    f"exactly one room must have step_depth == 0 (the "
                    f"main entry); got {zero_depth_count} rooms with "
                    f"depth 0."
                )

        # ── Step-depth non-negative ──
        for room_id, depth in self.step_depth_from_entry:
            if depth < 0:
                raise ValueError(
                    f"CirculationGraphReport: step_depth for room {room_id!r} "
                    f"must be ≥ 0; got {depth}."
                )

        # ── Connectivity non-negative ──
        for room_id, deg in self.connectivity:
            if deg < 0:
                raise ValueError(
                    f"CirculationGraphReport: connectivity for room "
                    f"{room_id!r} must be ≥ 0; got {deg}."
                )

        # ── Betweenness rank ∈ [1, k] (1 = most-bottleneck) ──
        k = len(self.nodes)
        for room_id, rank in self.betweenness_rank:
            if not (1 <= rank <= max(1, k)):
                raise ValueError(
                    f"CirculationGraphReport: betweenness_rank for room "
                    f"{room_id!r} must be in [1, {k}]; got {rank}."
                )

        # ── Inv E10: mean_depth ≤ max_depth ≤ k-1 (when k ≥ 2) ──
        if k >= 2:
            if not (self.mean_depth <= self.max_depth + 1e-9):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E10 — "
                    f"mean_depth ({self.mean_depth}) must be ≤ max_depth "
                    f"({self.max_depth})."
                )
            if self.max_depth > k - 1:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E10 — max_depth "
                    f"({self.max_depth}) must be ≤ len(nodes)-1 ({k - 1})."
                )

        # ── Inv E11': raw_RA ≥ 0 ──
        # (We allow nan to permit degenerate single-node graphs where the
        # formula is undefined; orchestrator will emit nan in those cases.)
        from math import isnan, isinf
        if not isnan(self.raw_relative_asymmetry):
            if self.raw_relative_asymmetry < 0:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E11' — "
                    f"raw_relative_asymmetry must be ≥ 0; got "
                    f"{self.raw_relative_asymmetry}."
                )

        # ── Inv E11'': real_RA bounded for k ≥ 4, nan for k < 4 ──
        if k < 4:
            if not isnan(self.real_relative_asymmetry):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E11'' — for "
                    f"k < 4 (got k={k}), real_relative_asymmetry must be "
                    f"nan; got {self.real_relative_asymmetry}."
                )
        else:
            # Per Hillier-Hanson 1984 p.282: RRA "varying about 1, with
            # low values indicating more integration (in effect, less
            # distance to all the others) and high values more
            # segregation." Per MDPI Sustainability 2024 (Erbil
            # architecture-schools study) typical RRA range is 0–3.
            # Highly-segregated pathological layouts (deep linear
            # chains) can produce RRA > 3. We bound at 10 as a
            # generous-but-still-catches-bugs sanity check; the value
            # has no LOCKED meaning above ~3 but the formula is well-
            # defined as long as RA ≥ 0 and D(k) > 0 (both invariants
            # held by Phase γ).
            if (
                isnan(self.real_relative_asymmetry)
                or self.real_relative_asymmetry < 0
                or self.real_relative_asymmetry > 10.0
            ):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E11'' — for "
                    f"k ≥ 4 (got k={k}), real_relative_asymmetry must be "
                    f"in [0, 10]; got {self.real_relative_asymmetry}."
                )

        # ── Inv E12': integration ──
        if k < 4:
            if not isnan(self.integration):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E12' — for "
                    f"k < 4 (got k={k}), integration must be nan; got "
                    f"{self.integration}."
                )
        else:
            # integration ∈ [1, ∞) OR float('inf').
            # (Allow >= 0.0 actually — A1 says 1/RRA, and RRA may exceed
            #  1 at small k, yielding integration < 1. We use a soft
            #  lower bound of 0.0 + a hard upper bound of inf.)
            if (
                isnan(self.integration)
                or self.integration < 0
            ):
                raise ValueError(
                    f"CirculationGraphReport violates Inv E12' — for "
                    f"k ≥ 4 (got k={k}), integration must be in [0, ∞) "
                    f"or inf; got {self.integration}."
                )

        # ── Inv E17: graph_size_category consistent with k ──
        if self.graph_size_category not in _VALID_GRAPH_SIZE_CATEGORY_VALUES:
            raise ValueError(
                f"CirculationGraphReport violates Inv E17 — "
                f"graph_size_category must be one of "
                f"{sorted(_VALID_GRAPH_SIZE_CATEGORY_VALUES)}; got "
                f"{self.graph_size_category!r}."
            )
        expected_category = _category_for_node_count(k)
        if self.graph_size_category != expected_category:
            raise ValueError(
                f"CirculationGraphReport violates Inv E17 — "
                f"graph_size_category should be {expected_category!r} for "
                f"k={k}; got {self.graph_size_category!r}."
            )

        # ── Inv E18: category_coverage ∈ [0, 1] ──
        if not (0.0 <= self.category_coverage <= 1.0):
            raise ValueError(
                f"CirculationGraphReport violates Inv E18 — "
                f"category_coverage must be in [0, 1]; got "
                f"{self.category_coverage}."
            )

        # ── Inv E16: provenance triple non-empty / non-negative ──
        if not self.c14_version:
            raise ValueError(
                "CirculationGraphReport violates Inv E16 — c14_version "
                "must be non-empty."
            )
        if self.c14_metric_version < 0:
            raise ValueError(
                f"CirculationGraphReport violates Inv E16 — "
                f"c14_metric_version must be ≥ 0; got "
                f"{self.c14_metric_version}."
            )
        if self.advisory_schema_version < 0:
            raise ValueError(
                f"CirculationGraphReport violates Inv E16 — "
                f"advisory_schema_version must be ≥ 0; got "
                f"{self.advisory_schema_version}."
            )

        # ── Truncation-meta cardinality: at most ONE per tuple ──
        # (Per A6: a single TRUNCATION_META replaces the last slot. We
        # allow zero or one; never two.)
        for tup_name, tup in (
            ("structural_flags", self.structural_flags),
            ("preference_flags", self.preference_flags),
        ):
            trunc_count = sum(
                1 for f in tup
                if str(f.flag_kind) == TRUNCATION_META_KIND_VALUE
            )
            if trunc_count > 1:
                raise ValueError(
                    f"CirculationGraphReport violates Inv E13' — "
                    f"{tup_name} contains {trunc_count} TRUNCATION_META "
                    f"meta-flags; at most 1 is permitted per tuple."
                )


def _category_for_node_count(k: int) -> GraphSizeCategory:
    """Per v0.2 A1 Inv E17. Pure helper exposed for orchestrator reuse."""
    if k <= 2:
        return "tiny"
    if k == 3:
        return "small"
    return "normal"


# =============================================================================
# FailureRecord (per v0.1 § 5)
# =============================================================================

@dataclass(frozen=True)
class FailureRecord:
    """Per v0.1 § 5. Captures a per-candidate analysis failure.

    Fields:
      candidate_signature: provenance back to source SuccessfulDoorPlacement.
      error_type: class name of the PerCandidateCirculationError.
      error_message: str() of the underlying exception.
      phase: which phase produced the failure (alpha | beta | gamma |
        delta | epsilon | zeta).
    """
    candidate_signature: str
    error_type: str
    error_message: str
    phase: Literal["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]

    def __post_init__(self) -> None:
        if not self.candidate_signature:
            raise ValueError(
                "FailureRecord.candidate_signature must be non-empty."
            )
        if not self.error_type:
            raise ValueError("FailureRecord.error_type must be non-empty.")
        if self.phase not in (
            "alpha", "beta", "gamma", "delta", "epsilon", "zeta",
        ):
            raise ValueError(
                f"FailureRecord.phase must be one of "
                f"alpha|beta|gamma|delta|epsilon|zeta; got {self.phase!r}."
            )


# =============================================================================
# Typestate variants (per v0.1 § 5, mirroring C13 v0.3 B11)
# =============================================================================

@dataclass(frozen=True)
class SuccessfulCirculationAnalysis:
    """Typestate-discriminated successful result.

    Downstream consumers MUST pattern-match on this vs
    FailedCirculationAnalysis. mypy rejects access to .report on a
    FailedCirculationAnalysis — preventing WARN-mode-failed candidates
    from being misused as successful.

    Fields:
      source_placed_candidate_signature: provenance back to C13 input.
      report: the CirculationGraphReport (canonical-sorted, frozen).
    """
    source_placed_candidate_signature: str
    report: CirculationGraphReport

    def __post_init__(self) -> None:
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "SuccessfulCirculationAnalysis."
                "source_placed_candidate_signature must be non-empty."
            )
        # Consistency: report's signature must match.
        if (
            self.report.source_placed_candidate_signature
            != self.source_placed_candidate_signature
        ):
            raise ValueError(
                f"SuccessfulCirculationAnalysis: source signature "
                f"({self.source_placed_candidate_signature!r}) does not "
                f"match wrapped report signature "
                f"({self.report.source_placed_candidate_signature!r})."
            )


@dataclass(frozen=True)
class FailedCirculationAnalysis:
    """Typestate-discriminated failure result.

    For WARN-mode collection. Cannot be misused as a successful result
    because there is no `.report` field of type CirculationGraphReport.

    Fields:
      source_placed_candidate_signature: provenance back to C13 input.
      failure_record: the FailureRecord with phase + error_type +
        error_message.
      partial_report: optional partial CirculationGraphReport built
        before failure; DEBUG only.
    """
    source_placed_candidate_signature: str
    failure_record: FailureRecord
    partial_report: Optional[CirculationGraphReport] = None

    def __post_init__(self) -> None:
        if not self.source_placed_candidate_signature:
            raise ValueError(
                "FailedCirculationAnalysis."
                "source_placed_candidate_signature must be non-empty."
            )
        if (
            self.failure_record.candidate_signature
            != self.source_placed_candidate_signature
        ):
            raise ValueError(
                f"FailedCirculationAnalysis: source signature "
                f"({self.source_placed_candidate_signature!r}) does not "
                f"match failure_record signature "
                f"({self.failure_record.candidate_signature!r})."
            )


# =============================================================================
# CirculationAnalysisBatchResult (per v0.1 § 5)
# =============================================================================

@dataclass(frozen=True)
class CirculationAnalysisBatchResult:
    """Per v0.1 § 5. Top-level result of analyze_circulation().

    Typestate-discriminated: separate tuples for successful + failed
    analyses. NO general "results" field mixing them (mirrors C13's
    DoorPlacementBatchResult per v0.3 B11).

    Fields:
      successful: tuple of SuccessfulCirculationAnalysis, sorted lex-ASC
          by source_placed_candidate_signature for determinism.
      failed: tuple of FailedCirculationAnalysis, sorted lex-ASC by
          source_placed_candidate_signature.
      c14_version: version stamp (Inv E16).
      c14_metric_version: metric formula version stamp (Inv E16).
      advisory_schema_version: passed-through from C13 (Inv E16 / E9).
    """
    successful: tuple[SuccessfulCirculationAnalysis, ...]
    failed: tuple[FailedCirculationAnalysis, ...]
    c14_version: str
    c14_metric_version: int
    advisory_schema_version: int

    def __post_init__(self) -> None:
        # Sort enforcement (Inv E7 byte-equal replay).
        succ_keys = [
            s.source_placed_candidate_signature for s in self.successful
        ]
        if succ_keys != sorted(succ_keys):
            raise ValueError(
                f"CirculationAnalysisBatchResult: successful tuple must be "
                f"sorted lex-ASC by source signature; got {succ_keys}."
            )
        fail_keys = [
            f.source_placed_candidate_signature for f in self.failed
        ]
        if fail_keys != sorted(fail_keys):
            raise ValueError(
                f"CirculationAnalysisBatchResult: failed tuple must be "
                f"sorted lex-ASC by source signature; got {fail_keys}."
            )

        # No source-signature appears in BOTH successful and failed
        # (a candidate is either-or, never both).
        succ_set = set(succ_keys)
        for k in fail_keys:
            if k in succ_set:
                raise ValueError(
                    f"CirculationAnalysisBatchResult: source signature "
                    f"{k!r} appears in BOTH successful and failed tuples."
                )

        # Provenance triple (Inv E16).
        if not self.c14_version:
            raise ValueError(
                "CirculationAnalysisBatchResult violates Inv E16 — "
                "c14_version must be non-empty."
            )
        if self.c14_metric_version < 0:
            raise ValueError(
                f"CirculationAnalysisBatchResult violates Inv E16 — "
                f"c14_metric_version must be ≥ 0; got "
                f"{self.c14_metric_version}."
            )
        if self.advisory_schema_version < 0:
            raise ValueError(
                f"CirculationAnalysisBatchResult violates Inv E16 — "
                f"advisory_schema_version must be ≥ 0; got "
                f"{self.advisory_schema_version}."
            )


__all__ = [
    "TRUNCATION_META_KIND_VALUE",
    "StructuralCirculationFlagKind",
    "PreferenceCirculationFlagKind",
    "CirculationFlagKind",
    "GraphSizeCategory",
    "CirculationFlag",
    "CirculationGraphReport",
    "FailureRecord",
    "SuccessfulCirculationAnalysis",
    "FailedCirculationAnalysis",
    "CirculationAnalysisBatchResult",
    "_category_for_node_count",
]
