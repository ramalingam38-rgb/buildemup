"""S55 Batch 4 — C14 LOCK-mandatory closures.

Pins the 5 LOCK-mandatory items filed at C14 v0.2 LOCK + S47 build close.
Each item gets a documented decision (formula/contract/definition) with
a clear S55-pinned breadcrumb. Full C14 v1.0 LOCK still requires
architect+spec review of these pinned values — this module is the
canonical record of the S55 baseline.

  B-C14-BETWEENNESS-FORMULA-LOCK          → BETWEENNESS_FORMULA_ID
  B-C14-PRIVACY-GRADIENT-FORMULA-LOCK     → PRIVACY_GRADIENT_FORMULA_ID
  B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK   → TRANSIT_BEDROOM_DEFINITION
  B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION → PRIMARY_EDGE_SEMANTICS
  B-C14-PBT-LAYER-COVERAGE                → PBT_COVERAGE_MANIFEST (≥15 tests)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Tuple


C14_LOCK_VERSION: Final[str] = "v0.2.LOCKED+S55-formulas-pinned"


# ─────────────────────────────────────────────────────────────────────
# B-C14-BETWEENNESS-FORMULA-LOCK
# ─────────────────────────────────────────────────────────────────────


class BetweennessFormula(str, Enum):
    """Canonical formula identifiers for betweenness centrality.

    Pinned at S55 to NORMALIZED_BRANDES. Future amendments require
    KB_VERSION bump + regression-snapshot refresh.
    """
    NORMALIZED_BRANDES = "normalized_brandes"
    """Brandes 2001 single-source-shortest-path with normalization:
       BC(v) = 2 / ((n-1)(n-2)) * sum over s≠v≠t of σ(s,t|v)/σ(s,t)

       Where σ(s,t) is the number of shortest paths from s to t and
       σ(s,t|v) is those passing through v. Normalized to [0, 1]."""


BETWEENNESS_FORMULA_ID: Final[BetweennessFormula] = (
    BetweennessFormula.NORMALIZED_BRANDES
)
BETWEENNESS_FORMULA_CITATION: Final[str] = (
    "Brandes 2001, 'A Faster Algorithm for Betweenness Centrality', "
    "Journal of Mathematical Sociology 25(2):163-177"
)


# ─────────────────────────────────────────────────────────────────────
# B-C14-PRIVACY-GRADIENT-FORMULA-LOCK
# ─────────────────────────────────────────────────────────────────────


class PrivacyGradientFormula(str, Enum):
    """Privacy-gradient monotonicity formula identifiers.

    Pinned at S55 to MEAN_TRANSITIVE_DEGREE. Spec § 3.2: privacy
    gradient assigns a scalar in [0, 1] per room where 0 = most
    public (entry-adjacent) and 1 = most private (bedrooms,
    bathrooms reachable only through private corridor sequences).
    """
    MEAN_TRANSITIVE_DEGREE = "mean_transitive_degree"
    """For each room r: privacy(r) = depth_from_entry(r) /
       max_depth_in_graph. Depth measured via shortest connection-
       graph hop count. Monotonic: if room A is between entry and B,
       privacy(A) ≤ privacy(B). Floor in [0, 1]."""


PRIVACY_GRADIENT_FORMULA_ID: Final[PrivacyGradientFormula] = (
    PrivacyGradientFormula.MEAN_TRANSITIVE_DEGREE
)


# ─────────────────────────────────────────────────────────────────────
# B-C14-TRANSIT-BEDROOM-DEFINITION-LOCK
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TransitBedroomDefinition:
    """Full LOCK-pinned definition. Replaces the v0.2 A5 SKETCH.

    A bedroom counts as 'transit' if and only if:
      1. It carries a door to a non-circulation room that has NO
         alternate connection path to the same room not going through
         this bedroom. AND
      2. The non-circulation room downstream is itself habitable
         (not a closet/utility/storage).

    Practical reading: walking from any room to room R requires passing
    through the bedroom. This is a privacy / cultural violation we
    flag (Indian residential vernacular: bedrooms should not double
    as hallways).
    """
    requires_no_alternate_path: bool = True
    requires_downstream_habitable: bool = True
    excludes_closet_utility: bool = True
    excludes_storage: bool = True


TRANSIT_BEDROOM_DEFINITION: Final[TransitBedroomDefinition] = (
    TransitBedroomDefinition()
)


# ─────────────────────────────────────────────────────────────────────
# B-C14-PRIMARY-EDGE-SEMANTIC-FORMALIZATION
# ─────────────────────────────────────────────────────────────────────


class PrimaryEdgeSemantics(str, Enum):
    """Architectural semantics for 'primary edge' selection on a
    SharedEdge. Pinned at S55.
    """
    LONGEST_OVERLAP_WITHIN_AXIS = "longest_overlap_within_axis"
    """The primary edge between two rooms is the SharedEdge with the
    longest overlap_length_m where axis matches the rooms' dominant
    aspect direction. Tie-break: lex-ASC by (room_a_id, room_b_id).
    """


PRIMARY_EDGE_SEMANTICS: Final[PrimaryEdgeSemantics] = (
    PrimaryEdgeSemantics.LONGEST_OVERLAP_WITHIN_AXIS
)


# ─────────────────────────────────────────────────────────────────────
# B-C14-PBT-LAYER-COVERAGE — manifest of mandatory PBT IDs (≥15)
# ─────────────────────────────────────────────────────────────────────
#
# Per S47 critique walk: spec § 7 mandates ≥15 property-based tests
# covering all invariants. v0.2 BUILD shipped 0. This manifest is the
# canonical list; each entry must have a corresponding PBT in
# tests/test_c14/test_c14_property_based.py before C14 v1.0 LOCK.

C14_PBT_COVERAGE_MANIFEST: Final[Tuple[str, ...]] = (
    "pbt_betweenness_monotonic_under_node_removal",
    "pbt_betweenness_normalized_in_unit_interval",
    "pbt_privacy_gradient_monotonic_from_entry",
    "pbt_privacy_gradient_floor_zero_at_entry",
    "pbt_privacy_gradient_ceiling_one_at_deepest",
    "pbt_transit_bedroom_excludes_closets",
    "pbt_transit_bedroom_excludes_utilities",
    "pbt_transit_bedroom_requires_no_alternate_path",
    "pbt_primary_edge_canonical_lex_asc_tiebreak",
    "pbt_primary_edge_axis_match_preference",
    "pbt_graph_replay_byte_identical",
    "pbt_metrics_invariant_under_permutation",
    "pbt_advisory_set_canonical_order",
    "pbt_node_count_preserved_through_compute",
    "pbt_edge_count_preserved_through_compute",
)


def pbt_coverage_count() -> int:
    return len(C14_PBT_COVERAGE_MANIFEST)


__all__ = [
    "C14_LOCK_VERSION",
    # Betweenness
    "BetweennessFormula",
    "BETWEENNESS_FORMULA_ID",
    "BETWEENNESS_FORMULA_CITATION",
    # Privacy gradient
    "PrivacyGradientFormula",
    "PRIVACY_GRADIENT_FORMULA_ID",
    # Transit bedroom
    "TransitBedroomDefinition",
    "TRANSIT_BEDROOM_DEFINITION",
    # Primary edge
    "PrimaryEdgeSemantics",
    "PRIMARY_EDGE_SEMANTICS",
    # PBT coverage
    "C14_PBT_COVERAGE_MANIFEST",
    "pbt_coverage_count",
]
