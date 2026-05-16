"""
C3b — Post-Layout Trade-off Negotiation — input/integration contracts
======================================================================

Spec: C3b v0.4.LOCKED § 8. Build session: S52.

This module re-exports the UPSTREAM types C3b consumes, plus declares
the small set of C3b-internal supporting types that pin the input
shape. Output schema lives in `schema.py`.

Upstream surface (per spec § 8):

  C15 v1.0 LOCKED   → SelectionResult, ProblemReport       (real, imported)
  C16 v1.2 LOCKED   → AttestedValue, AuthorityKind,
                      CheckProvenance, JurisdictionProfile (real, imported)
  C7  v0.8 LOCKED   → StructuralGridCell, GridColumn       (stub, imported)
  C12 v1.0 LOCKED   → PlacedRoom, RoomGeometry             (stub, imported)
  C13 v1.0 LOCKED   → DoorPlacement                         (stub, imported)
  C10 v1.0 LOCKED   → RiserGroup                            (stub, imported)
  C4  v1.0 LOCKED   → PlotAnalysis                          (stub, imported)
  C3a v0.2.1 LOCKED → ResolvedBrief, KickbackContext        (stub, imported)
  utils             → TransparencyTriple, Confidence,
                      DerivationLine                        (real, imported)

In addition this module declares:

  C3bInputBundle             — the full input envelope C3b operates on
                                  (composes the upstream types)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Tuple

# ----- Real upstream (LOCKED, in-tree) ---------------------------
from buildemup.components.c15.schema import ProblemReport  # noqa: F401
from buildemup.components.c16.contracts import (  # noqa: F401
    AttestedValue,
    AuthorityKind,
    SelectionResult,
)

# ----- Stub upstream (in-tree as stubs covering consumed surface) -
from buildemup.components.c03a._c3b_shim import (  # noqa: F401
    KickbackContext,
    ResolvedBrief,
)
from buildemup.components.c04._c3b_shim import (  # noqa: F401
    CardinalDirection,
    ClimateZone,
    PlotAnalysis,
)
from buildemup.components.c07._c3b_shim import (  # noqa: F401
    GridColumn,
    StructuralGrid,
    StructuralGridCell,
)
from buildemup.components.c10._c3b_shim import (  # noqa: F401
    Riser,
    RiserGroup,
)
from buildemup.components.c12._c3b_shim import (  # noqa: F401
    PlacedRoom,
    RoomFunction,
    RoomGeometry,
)
from buildemup.components.c13._c3b_shim import (  # noqa: F401
    DoorKind,
    DoorPlacement,
    SwingDirection,
)

# ----- Real utilities ---------------------------------------------
from buildemup.utils.confidence import Confidence  # noqa: F401
from buildemup.utils.transparency import (  # noqa: F401
    DerivationLine,
    TransparencyTriple,
)


# ============================================================
# § 1 — C3bInputBundle
# ============================================================

@dataclass(frozen=True)
class C3bInputBundle:
    """The full envelope of upstream inputs C3b operates on. Phase α
    consumes this and produces the initial TradeoffSession skeleton.

    Per spec § 1: C3b consumes
      1. SelectionResult from C15 (3 ranked layouts + provenance)
      2. ProblemReport per layout from C15 (3 reports, layout-aligned)
      3. ResolvedBrief from C3a
      4. PlotAnalysis from C4
    plus:
      5. PlacedRooms     — geometry grounding for R3 invariant
      6. StructuralGrid  — bay context for severity computation
      7. DoorPlacements  — door grounding for door_relocate tweaks
      8. RiserGroups     — wet-zone stack context for restage tweaks
    """
    selection_result:    SelectionResult
    problem_reports:     Tuple[ProblemReport, ...]
    """3 ProblemReports, one per layout, aligned with
    selection_result.layouts order."""

    resolved_brief:      ResolvedBrief
    plot_analysis:       PlotAnalysis

    placed_rooms_per_layout:   Tuple[Tuple[PlacedRoom, ...], ...]
    """Per layout (3 entries), the placed rooms. Aligned with
    selection_result.layouts order."""

    structural_grids_per_layout:  Tuple[StructuralGrid, ...]
    door_placements_per_layout:   Tuple[Tuple[DoorPlacement, ...], ...]
    riser_groups_per_layout:      Tuple[Tuple[RiserGroup, ...], ...]

    def __post_init__(self) -> None:
        n_reports = len(self.problem_reports)
        n_layouts = len(self.placed_rooms_per_layout)
        n_grids = len(self.structural_grids_per_layout)
        n_doors = len(self.door_placements_per_layout)
        n_risers = len(self.riser_groups_per_layout)
        # All 5 layout-aligned tuples must match in length
        if not (n_reports == n_layouts == n_grids == n_doors == n_risers):
            raise ValueError(
                f"C3bInputBundle layout-aligned tuples must all have "
                f"the same length; got problem_reports={n_reports}, "
                f"placed_rooms={n_layouts}, grids={n_grids}, "
                f"doors={n_doors}, risers={n_risers}"
            )
        # Empty is allowed at the type level (Phase α decides via
        # applicability boundary)
        if n_reports == 0:
            return


# ============================================================
# § 2 — Surface marker
# ============================================================

C3B_CONTRACTS_VERSION: Final[str] = "v0.4.LOCKED.s52"


__all__ = [
    # Real upstream
    "ProblemReport",
    "SelectionResult",
    "AttestedValue", "AuthorityKind",
    # Stub upstream
    "ResolvedBrief", "KickbackContext",
    "PlotAnalysis", "CardinalDirection", "ClimateZone",
    "StructuralGrid", "StructuralGridCell", "GridColumn",
    "RiserGroup", "Riser",
    "PlacedRoom", "RoomFunction", "RoomGeometry",
    "DoorPlacement", "DoorKind", "SwingDirection",
    # Utilities
    "TransparencyTriple", "DerivationLine", "Confidence",
    # C3b internal
    "C3bInputBundle",
    "C3B_CONTRACTS_VERSION",
]
