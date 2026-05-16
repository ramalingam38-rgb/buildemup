"""
BuildemUp† — Building domain object.

Top-level structure description shared across components.

Composition:
  Building
    ├── meta (BuildingMeta — type, location, user info)
    ├── envelope (Envelope — buildable footprint)
    ├── floors (tuple of Floor — per-storey)
    └── grid (DomainGrid — column positions; optional, may be None
              before Component 7 has run)

Components consume Building (or parts of it) and produce additional
artefacts. Building itself never holds engineering OUTPUTS — only
INPUTS. Component outputs go in their own dataclasses.

†= placeholder name marker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from buildemup.domain.envelope import Envelope
from buildemup.domain.floor import Floor
from buildemup.domain.grid import DomainGrid


@dataclass(frozen=True)
class BuildingMeta:
    """Project-level metadata.

    Decoupled from Envelope so the same building shape can be re-priced
    in different cities without rebuilding the geometry.
    """
    project_id: str = ""              # e.g., "BE-2026-04-12345"
    city: str = "chennai"
    area: str | None = None           # Sub-area, e.g., "Velachery"
    seismic_zone: str = "II"
    building_type: str = "residential_single_family"
    user_name: str = ""               # Optional, may be empty

    # v0.6: status field for "PENDING ENGINEER VALIDATION" framing
    # Set in Phase 3.
    validation_status: str = "PENDING_ENGINEER_VALIDATION"


@dataclass(frozen=True)
class Building:
    """Top-level shared building object.

    Used as the input contract for all engineering components.
    Components may also use sub-objects directly (e.g., Component 7
    needs Envelope + Floors + grid_info).
    """
    meta: BuildingMeta
    envelope: Envelope
    floors: tuple[Floor, ...]
    grid: DomainGrid | None = None    # None until Component 7 has run

    def __post_init__(self):
        if not self.floors:
            raise ValueError("Building must have at least 1 floor")
        # Floor numbers should be unique
        floor_nums = [f.floor_number for f in self.floors]
        if len(set(floor_nums)) != len(floor_nums):
            raise ValueError(
                f"Floor numbers must be unique. Got {floor_nums}."
            )

    @property
    def floors_above_ground(self) -> int:
        """Count of floors above ground (excludes stilt + terrace)."""
        from buildemup.domain.floor import FloorType
        return sum(1 for f in self.floors
                   if f.floor_type not in (
                       FloorType.STILT_PARKING, FloorType.TERRACE,
                       FloorType.WATER_TANK_ROOF,
                   ))

    @property
    def has_stilt_parking(self) -> bool:
        from buildemup.domain.floor import FloorType
        return any(f.floor_type == FloorType.STILT_PARKING for f in self.floors)

    @property
    def has_terrace_access(self) -> bool:
        from buildemup.domain.floor import FloorType
        return any(f.floor_type == FloorType.TERRACE for f in self.floors)

    @property
    def has_water_tank(self) -> bool:
        from buildemup.domain.floor import FloorType
        return any(f.floor_type == FloorType.WATER_TANK_ROOF for f in self.floors) \
               or any(f.has_water_tank for f in self.floors)

    @property
    def total_built_up_sqm(self) -> float:
        """Sum of net floor area across all floors above stilt/terrace."""
        from buildemup.domain.floor import FloorType
        return sum(
            self.envelope.net_area_sqm for f in self.floors
            if f.floor_type not in (
                FloorType.STILT_PARKING, FloorType.TERRACE,
                FloorType.WATER_TANK_ROOF,
            )
        )

    def with_grid(self, grid: DomainGrid) -> "Building":
        """Return a new Building with grid attached. Immutable update."""
        return Building(
            meta=self.meta,
            envelope=self.envelope,
            floors=self.floors,
            grid=grid,
        )

    # ─── v0.7: Rich-domain methods (worked example per review Drawback 2) ──
    # The v0.6 review noted domain layer was too passive. Rather than a
    # big-bang conversion of every domain object, we start with one
    # high-value method as a pattern to follow for v0.8+ migration.
    #
    # Why this one first: `total_imposed_load_kn` is used by BOTH Component 7
    # (structural sizing) AND Component 13 (MEP load balancing, future).
    # Putting it in the domain layer prevents future drift.

    def total_imposed_load_kn(self) -> float:
        """Sum of live loads across all floors (rich-domain computation).

        Live load = effective_live_load_knsqm × floor_net_area_sqm,
        aggregated across all floors including stilt parking and terrace
        (because their loads do count, even if areas are different).

        This is a WORKED EXAMPLE of rich-domain per v0.6 Drawback 2.
        Previously Component 7 computed this inline; now the domain
        object owns the logic so Component 13 (future MEP) gets the
        same answer without duplicating the calculation.

        Returns:
            Total unfactored live load in kN across entire building.
        """
        total = 0.0
        for floor in self.floors:
            area_sqm = self.envelope.net_area_sqm
            load_knsqm = floor.effective_live_load_knsqm
            total += load_knsqm * area_sqm
        return total

    def validate_for_structural_analysis(self) -> list[str]:
        """Rich-domain validation: returns list of issues, empty if valid.

        Per v0.7 review Drawback 2: domain objects should enforce their
        own invariants, not defer to external validators. This method
        returns human-readable issues rather than raising — caller
        decides whether to refuse or warn.

        Returns:
            List of issue strings. Empty list = ready for structural analysis.
        """
        issues = []
        # Must have at least one non-stilt, non-terrace floor
        if self.floors_above_ground == 0:
            issues.append(
                "Building has no floors above ground — structural analysis "
                "needs at least one habitable floor."
            )
        # Envelope must be validated (Envelope validates itself in __post_init__,
        # but we re-check for the business-level validity here)
        if self.envelope.area_sqm < 25:
            issues.append(
                f"Envelope area {self.envelope.area_sqm:.0f} sqm is very small "
                f"for structural analysis. Minimum practical: 25 sqm."
            )
        # Aspect ratio check (IS 1893 irregularity)
        if self.envelope.aspect_ratio > 6.0:
            issues.append(
                f"Aspect ratio {self.envelope.aspect_ratio:.1f} > 6.0 is "
                f"severely irregular per IS 1893. Special detailing required."
            )
        return issues
