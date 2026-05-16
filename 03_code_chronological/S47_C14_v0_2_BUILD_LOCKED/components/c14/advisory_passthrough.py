"""
BuildemUp — Component 14 — Phase ε: advisory passthrough + conversion
======================================================================

Per C14 SPEC v0.2 LOCKED § 3 Phase ε + Inv E8 (byte-identical upstream
passthrough) + Inv E9 (C14-emitted advisories conform to
ADVISORY_SCHEMA_VERSION).

Phase ε produces two AdvisoryFlag tuples:

1. `upstream_advisory_flags`: byte-identical passthrough of the
   `advisory_flags` field from the incoming SuccessfulDoorPlacement
   (Inv E8). C14 NEVER mutates C13's output.

2. `c14_advisory_flags`: AdvisoryFlag representations of C14's own
   CirculationFlag emissions, for downstream consumers that want a
   uniform `tuple[AdvisoryFlag, ...]` to walk.

---

**SPEC TENSION SURFACED AT S47 BUILD TIME — MISFRAMED finding:**

The v0.1 § 1.4 text says:

> "C14's flag kinds are categorically different (circulation/graph)
>  from C13's (geometric/safety). [...] The c14_advisory_flags field
>  in CirculationGraphReport is typed as AdvisoryFlag (C13's type) —
>  the C14 advisories are CirculationFlag *converted into*
>  AdvisoryFlag at emission."

However C13's `AdvisoryFlagKind` is a FROZEN Literal of 6 LOCKED
strings (per C13 v0.4 C8 ADVISORY_SCHEMA_VERSION):

  - "through_private_routing"
  - "through_bathroom_routing"
  - "through_pooja_routing"
  - "long_corridor_route"
  - "minimal_clearance_door"
  - "bathroom_outswing_emergency_clearance"

C14's flag kinds (`bottleneck_concentration`, `dead_end_isolation`,
`transit_through_bedroom`, `privacy_gradient_violation`,
`excessive_depth`, `category_coverage_low`, `truncation_meta`) are
NOT in C13's set. AdvisoryFlag's __post_init__ would reject all of
them.

**Resolution at v0.2 SKETCH:** `c14_advisory_flags` is emitted as an
EMPTY tuple. Downstream consumers (C15) get the FULL signal via the
structural_flags + preference_flags tuples on CirculationGraphReport
(which carry CirculationFlag, not AdvisoryFlag). The c14_advisory_flags
field remains in the schema for forward-compatibility with the
eventual unification (`B-PROJECT-ADVISORY-UNIFICATION` already filed
in v0.1 § 12).

**Backlog item filed (to be surfaced in handoff):**
`B-C14-ADVISORY-CONVERSION-CONTRACT-LOCK` (LOCK-mandatory, S effort):
v1.0 LOCK must resolve whether to (a) extend C13's
ADVISORY_SCHEMA_VERSION with C14-specific kinds, (b) keep
c14_advisory_flags as a separate `tuple[CirculationFlag, ...]`
typed field (schema bump for C14), or (c) drop the field entirely.

This is a SKETCH choice at v0.2 — it changes no LOCKED contract,
preserves Inv E7 (byte-equal replay: empty tuples are byte-equal),
and unblocks the build. If v0.3 critique walks reject the SKETCH
choice, that's a spec amendment.
"""
from __future__ import annotations

from dataclasses import dataclass

from buildemup.components.c13.schema import AdvisoryFlag

from .schema import CirculationFlag


# =============================================================================
# Output: AdvisoryBundle
# =============================================================================

@dataclass(frozen=True)
class AdvisoryBundle:
    """Phase ε output: two AdvisoryFlag tuples.

    Frozen for replay determinism.
    """
    upstream_advisory_flags: tuple[AdvisoryFlag, ...]
    c14_advisory_flags: tuple[AdvisoryFlag, ...]


# =============================================================================
# Phase ε main entry
# =============================================================================

def assemble_advisory_bundle(
    *,
    upstream_advisory_flags: tuple[AdvisoryFlag, ...],
    structural_flags: tuple[CirculationFlag, ...],
    preference_flags: tuple[CirculationFlag, ...],
) -> AdvisoryBundle:
    """Phase ε: assemble the two AdvisoryFlag tuples.

    Per v0.1 § 3 Phase ε + Inv E8 + Inv E9.

    Inputs:
      upstream_advisory_flags: the `advisory_flags` field from the
        incoming SuccessfulDoorPlacement. Byte-identical passthrough
        (Inv E8).
      structural_flags / preference_flags: C14's own emissions from
        Phase δ. Currently NOT converted to AdvisoryFlag because of
        the spec tension documented in the module docstring — see
        B-C14-ADVISORY-CONVERSION-CONTRACT-LOCK in the backlog.

    Returns:
      AdvisoryBundle:
        upstream_advisory_flags: byte-identical passthrough
        c14_advisory_flags: empty tuple at v0.2 SKETCH (forward-compat
          for the future unification)
    """
    # ── Inv E8: byte-identical passthrough ────────────────────────
    # tuple equality + immutability means this IS byte-identical.
    # Defensive validation: input must be a tuple of AdvisoryFlag.
    if not isinstance(upstream_advisory_flags, tuple):
        raise TypeError(
            f"upstream_advisory_flags must be a tuple; got "
            f"{type(upstream_advisory_flags).__name__}."
        )
    for flag in upstream_advisory_flags:
        if not isinstance(flag, AdvisoryFlag):
            raise TypeError(
                f"every upstream_advisory_flag must be an AdvisoryFlag; "
                f"got {type(flag).__name__}."
            )

    # ── c14_advisory_flags: empty at v0.2 SKETCH ──────────────────
    # See module docstring for the rationale. Per Inv E9, this empty
    # tuple trivially "conforms" to ADVISORY_SCHEMA_VERSION (there are
    # no flags to violate the schema).
    c14_advisory_flags: tuple[AdvisoryFlag, ...] = ()

    # `structural_flags` and `preference_flags` are accepted as
    # parameters so that v0.3+ amendments can re-enable the conversion
    # without changing the call signature. At v0.2 they're not used
    # (silenced parameter pattern — explicit binding for clarity).
    _ = structural_flags  # acknowledged-unused at v0.2
    _ = preference_flags  # acknowledged-unused at v0.2

    return AdvisoryBundle(
        upstream_advisory_flags=upstream_advisory_flags,
        c14_advisory_flags=c14_advisory_flags,
    )


__all__ = [
    "AdvisoryBundle",
    "assemble_advisory_bundle",
]
