"""
C16 — Dual-Drawing Renderer — RenderingConfig
================================================

Per:
    v0.2 A6 — RenderingConfig schema fleshed out
    v0.3 A6 — capture_readability_diagnostics flag
    v0.3 A8 — coordinate bounds moved INTO RenderingConfig
    v0.4 A7 — hard ceilings override RenderingConfig (R31a)
    v0.5 A4 — hard ceilings re-pinned, NOT overridable

Rule 11 self-analysis worst issue: v0.3 A8 moved bounds INTO config,
but v0.5 A4 effectively re-pinned them as non-overridable hard
ceilings. The reconciliation: config can declare TIGHTER bounds than
hard ceiling, never LOOSER. Effective bound = MIN(config, ceiling).
A config that declares looser bounds raises C16ConfigurationError at
construction time (fail fast — R31a).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, FrozenSet, Literal

from buildemup.components.c16.errors import C16ConfigurationError
from buildemup.components.c16.versioning import (
    HARD_CEILING_BUILDING_X_MM,
    HARD_CEILING_BUILDING_Y_MM,
    HARD_CEILING_BUILDING_Z_MAX_MM,
    HARD_CEILING_BUILDING_Z_MIN_MM,
    HARD_CEILING_PLOT_X_MM,
    HARD_CEILING_PLOT_Y_MM,
)


# Default mandatory section cuts (v0.2 A8 / R23)
_DEFAULT_MANDATORY_SECTION_CUTS: Final[FrozenSet[str]] = frozenset({
    "entry", "staircase", "wet_zone",
})

# Default suppression precedence (v0.2 A6) — suppressed FIRST → LAST
_DEFAULT_SUPPRESSION_PRECEDENCE: Final[tuple[str, ...]] = (
    "decorative",
    "secondary_dim",
    "primary_dim",
    "structural",
    "compliance",
)


# ============================================================
# § 1 — Coordinate bounds (v0.3 A8 + v0.4 A7 + v0.5 A4 — R31a)
# ============================================================

@dataclass(frozen=True)
class CoordinateBoundsPolicy:
    """Per-project coordinate range guards.

    Defaults tuned for Indian residential (200m plot, 50m building).
    Per R31a, these MAY declare TIGHTER bounds than HARD_CEILING_*
    but MUST NOT exceed them. Effective bound = MIN(this, ceiling).

    Attempt to declare bounds LOOSER than hard ceiling raises
    C16ConfigurationError at construction (R31a — fail fast).
    """
    plot_x_max_mm:       int = 200_000        # 200 m east-west
    plot_y_max_mm:       int = 200_000        # 200 m north-south
    building_x_max_mm:   int =  50_000        # 50 m building dimension
    building_y_max_mm:   int =  50_000
    building_z_min_mm:   int =  -5_000        # basement
    building_z_max_mm:   int =  50_000        # high-rise upper bound

    def __post_init__(self) -> None:
        # R31a — config bounds NEVER exceed hard ceilings
        checks = (
            ("plot_x_max_mm",      self.plot_x_max_mm,      HARD_CEILING_PLOT_X_MM,        "≤"),
            ("plot_y_max_mm",      self.plot_y_max_mm,      HARD_CEILING_PLOT_Y_MM,        "≤"),
            ("building_x_max_mm",  self.building_x_max_mm,  HARD_CEILING_BUILDING_X_MM,    "≤"),
            ("building_y_max_mm",  self.building_y_max_mm,  HARD_CEILING_BUILDING_Y_MM,    "≤"),
            ("building_z_max_mm",  self.building_z_max_mm,  HARD_CEILING_BUILDING_Z_MAX_MM, "≤"),
        )
        for name, value, ceiling, _ in checks:
            if value > ceiling:
                raise C16ConfigurationError(
                    f"CoordinateBoundsPolicy.{name}={value} exceeds "
                    f"HARD_CEILING ({ceiling}). Per R31a, hard ceilings "
                    f"cannot be overridden via RenderingConfig. For larger "
                    f"domains, declare a different jurisdiction.",
                    offending_field=name,
                    offending_value=value,
                )
        # z_min has DIFFERENT direction (more negative is "worse")
        if self.building_z_min_mm < HARD_CEILING_BUILDING_Z_MIN_MM:
            raise C16ConfigurationError(
                f"CoordinateBoundsPolicy.building_z_min_mm="
                f"{self.building_z_min_mm} below HARD_CEILING "
                f"({HARD_CEILING_BUILDING_Z_MIN_MM}). R31a.",
                offending_field="building_z_min_mm",
                offending_value=self.building_z_min_mm,
            )

        # Internal consistency: max > min
        if self.building_z_max_mm <= self.building_z_min_mm:
            raise C16ConfigurationError(
                f"CoordinateBoundsPolicy: building_z_max_mm "
                f"({self.building_z_max_mm}) must exceed building_z_min_mm "
                f"({self.building_z_min_mm}).",
                offending_field="building_z_max_mm",
                offending_value=self.building_z_max_mm,
            )

        # Positive dims
        if self.plot_x_max_mm <= 0 or self.plot_y_max_mm <= 0:
            raise C16ConfigurationError(
                "CoordinateBoundsPolicy plot dimensions must be positive.",
                offending_field="plot_x_max_mm/plot_y_max_mm",
                offending_value=(self.plot_x_max_mm, self.plot_y_max_mm),
            )
        if self.building_x_max_mm <= 0 or self.building_y_max_mm <= 0:
            raise C16ConfigurationError(
                "CoordinateBoundsPolicy building dimensions must be positive.",
                offending_field="building_x_max_mm/building_y_max_mm",
                offending_value=(self.building_x_max_mm, self.building_y_max_mm),
            )


# ============================================================
# § 2 — RenderingConfig (v0.2 A6 + extensions)
# ============================================================

@dataclass(frozen=True)
class RenderingConfig:
    """Knobs for drawing rendering.

    Precedence order (v0.2 A6):
        1. Explicit RenderingConfig field
        2. JurisdictionProfile recommended default (applied upstream)
        3. C16 hard-coded fallback (built-in here)

    Per v0.2 A6 / permit safety: even if
    `include_furniture_footprints_in_permit=True` is configured,
    permit-mode rendering force-overrides to False. The flag exists
    for symmetry but is functionally pinned.
    """

    # Scale targets (TNCDBR rule 8 compliance)
    working_drawing_scale: Literal["1:50", "1:75"] = "1:50"
    permit_drawing_scale:  Literal["1:100", "1:150", "1:200"] = "1:100"

    # Annotation density (suppression heuristic input)
    annotation_density:    Literal["full", "medium", "sparse"] = "full"

    # Multi-floor composition
    multi_floor_composition: Literal[
        "per_floor_separate", "stacked_layout"
    ] = "per_floor_separate"

    # Furniture display (working vs permit)
    include_furniture_footprints_in_working: bool = True
    include_furniture_footprints_in_permit:  bool = False

    # Section cuts (R23)
    mandatory_section_cuts: FrozenSet[str] = field(
        default_factory=lambda: _DEFAULT_MANDATORY_SECTION_CUTS,
    )

    # Suppression precedence (suppress earlier items first)
    suppression_precedence: tuple[str, ...] = field(
        default_factory=lambda: _DEFAULT_SUPPRESSION_PRECEDENCE,
    )

    # Conflict resolution (deterministic per R7)
    annotation_conflict_policy: Literal[
        "lex_asc_id_wins", "suppress_both"
    ] = "lex_asc_id_wins"

    # Coordinate bounds (v0.3 A8; R31a-gated via CoordinateBoundsPolicy)
    coordinate_bounds: CoordinateBoundsPolicy = field(
        default_factory=CoordinateBoundsPolicy,
    )

    # Observability (v0.2 A10 + v0.3 A6) — both EXCLUDED from cache keys
    capture_phase_timings:           bool = False
    capture_readability_diagnostics: bool = False

    def __post_init__(self) -> None:
        # Permit-mode safety: documented intent. The boolean exists for
        # symmetry, but downstream Phase δ MUST force-override to False.
        # We don't reject construction; we just document via this check.
        # (If you want a hard rejection, file as backlog.)
        _ = self.include_furniture_footprints_in_permit  # noqa: F841

        # Validate suppression_precedence is well-formed
        if not self.suppression_precedence:
            raise C16ConfigurationError(
                "RenderingConfig.suppression_precedence must be non-empty.",
                offending_field="suppression_precedence",
                offending_value=self.suppression_precedence,
            )
        if len(set(self.suppression_precedence)) != len(self.suppression_precedence):
            raise C16ConfigurationError(
                "RenderingConfig.suppression_precedence must have unique entries.",
                offending_field="suppression_precedence",
                offending_value=self.suppression_precedence,
            )

        # Validate mandatory_section_cuts entries (R23)
        valid_cuts = {"entry", "staircase", "wet_zone"}
        unknown = set(self.mandatory_section_cuts) - valid_cuts
        if unknown:
            raise C16ConfigurationError(
                f"RenderingConfig.mandatory_section_cuts has unknown values: "
                f"{sorted(unknown)}. Valid: {sorted(valid_cuts)}.",
                offending_field="mandatory_section_cuts",
                offending_value=self.mandatory_section_cuts,
            )


# ============================================================
# § 3 — Helpers
# ============================================================

def effective_plot_bounds(
    config: RenderingConfig,
) -> tuple[int, int]:
    """Effective plot bounds: MIN(config, hard ceiling). Per R31a."""
    return (
        min(config.coordinate_bounds.plot_x_max_mm, HARD_CEILING_PLOT_X_MM),
        min(config.coordinate_bounds.plot_y_max_mm, HARD_CEILING_PLOT_Y_MM),
    )


def effective_building_bounds(
    config: RenderingConfig,
) -> tuple[int, int, int, int]:
    """Effective building bounds: (x_max, y_max, z_min, z_max).
    z_min uses MAX (less-negative) — per R31a, config CANNOT loosen
    basement depth either."""
    return (
        min(config.coordinate_bounds.building_x_max_mm,
            HARD_CEILING_BUILDING_X_MM),
        min(config.coordinate_bounds.building_y_max_mm,
            HARD_CEILING_BUILDING_Y_MM),
        max(config.coordinate_bounds.building_z_min_mm,
            HARD_CEILING_BUILDING_Z_MIN_MM),
        min(config.coordinate_bounds.building_z_max_mm,
            HARD_CEILING_BUILDING_Z_MAX_MM),
    )
