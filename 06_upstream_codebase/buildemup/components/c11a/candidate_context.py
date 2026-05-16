"""
BuildemUp — Component 11a — strict candidate-context extractor (B-NEW-V)
=========================================================================

Per S39 critique walk F4: the orchestrator's previous
``_build_tier_a_context`` walked multiple fallback attribute paths
(e.g., ``topology_candidate.zone_bands`` → ``source_candidate.zone_bands``
→ ``zone_bands``) and silently fell back to None on miss. That hid
schema-drift bugs.

This module provides:

  * ``CandidateContextSchemaError`` — raised when a real
    ``WetZonePlannedCandidate`` is missing a required attribute path.
    Distinguishable from "no value at all" — schema drift fails loud.

  * ``extract_tier_a_context_from_candidate(candidate, grid, plot_analysis)``
    — single canonical extractor walking the v1.0 ancestry chain:

      WetZonePlannedCandidate
        └─ room_sized_candidate: RoomSizedCandidate
             └─ corridor_designed_candidate: CorridorDesignedCandidate
                  ├─ oriented_candidate: OrientedCandidate
                  │    └─ topology_candidate: TopologyCandidate
                  │         └─ zone_bands: Mapping[ZoneBand, PlotOrientation]
                  └─ corridor_path: CorridorPath

    A miss anywhere on this chain → ``CandidateContextSchemaError``.
    Sub-4 tests using ``_FakeWetZoneCandidate`` deliberately bypass
    this strict path; only production code calling
    ``mutate_topologies()`` with real ``WetZonePlannedCandidate``
    inputs goes through here.

  * ``extract_tier_a_context_lenient`` — kept as the orchestrator's
    fallback for synthetic-source-candidate compatibility (Sub-4
    tests, not production). Walks the multi-fallback paths from the
    previous design. Production callers should use the strict variant.

== When to use which ==

* Production / real candidates: ``extract_tier_a_context_from_candidate``
  (strict — surfaces schema drift loud).
* Tests with synthetic sources: ``extract_tier_a_context_lenient``
  (lenient — duck types).

The orchestrator dispatches between them based on whether the source
is a real ``WetZonePlannedCandidate`` instance: if yes → strict; if
no → lenient. This keeps the common path strict while preserving
test-fixture compatibility.
"""
from __future__ import annotations

from typing import Any, Optional

from buildemup.components.c11a.errors import TopologyMutationError
from buildemup.components.c11a.operators._base import TierAOperatorContext


# =============================================================================
# Error class — schema drift detection
# =============================================================================


class CandidateContextSchemaError(TopologyMutationError):
    """B-NEW-V (S39 critique walk F4).

    Raised when a real ``WetZonePlannedCandidate`` is missing a required
    attribute on the v1.0 ancestry chain. The previous duck-typed
    fallback walk would silently fall back to None on schema drift,
    hiding bugs; this class makes drift fail-loud.

    Severity: per_candidate. The orchestrator catches this and surfaces
    affected candidates as per-candidate invalid; the batch continues.
    """

    severity_tier = "per_candidate"


# =============================================================================
# Strict path constants — v1.0 LOCKED ancestry chain
# =============================================================================
#
# Each tuple is the dotted path from a ``WetZonePlannedCandidate`` to
# the named field. Verified against the v1.0 schemas at S39 critique
# walk close (see B-NEW-V backlog entry).


_PATH_ZONE_BANDS = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "oriented_candidate",
    "topology_candidate",
    "zone_bands",
)

_PATH_TOPOLOGY_KIND = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "oriented_candidate",
    "topology_candidate",
    "kind",
)

_PATH_CORRIDOR_PATH = (
    "room_sized_candidate",
    "corridor_designed_candidate",
    "corridor_path",
)


# =============================================================================
# Strict extractor (production path)
# =============================================================================


def _walk_strict_path(
    root: Any,
    path: tuple[str, ...],
    *,
    required: bool = True,
) -> Any:
    """Walk ``path`` from ``root``; raise ``CandidateContextSchemaError``
    on miss when required.

    Args:
        root: object to start walking from
        path: tuple of attribute names
        required: if True, miss → raise. If False, miss → return None
            (used for optional fields like staircase).

    Raises:
        CandidateContextSchemaError if required and any segment misses.
    """
    cur = root
    for i, segment in enumerate(path):
        if not hasattr(cur, segment):
            if required:
                consumed = ".".join(path[:i])
                consumed_repr = (
                    f"<{type(root).__name__}>" if i == 0
                    else f"<{type(cur).__name__}>"
                )
                raise CandidateContextSchemaError(
                    f"WetZonePlannedCandidate is missing attribute "
                    f"'{segment}' at path "
                    f"'{'.'.join(path)}' (consumed: '{consumed}', "
                    f"current type: {consumed_repr}). v1.0 ancestry "
                    f"chain expects: room_sized_candidate → "
                    f"corridor_designed_candidate → ... — see B-NEW-V."
                )
            return None
        cur = getattr(cur, segment)
        if cur is None:
            if required:
                raise CandidateContextSchemaError(
                    f"WetZonePlannedCandidate path "
                    f"'{'.'.join(path[:i+1])}' resolved to None "
                    f"(expected non-None)."
                )
            return None
    return cur


def extract_tier_a_context_from_candidate(
    candidate: Any,
    grid: Any,
    plot_analysis: Any,
) -> TierAOperatorContext:
    """Strict extractor for real ``WetZonePlannedCandidate`` inputs.

    Walks the v1.0 ancestry chain. Schema drift on any required field
    raises ``CandidateContextSchemaError`` so the orchestrator can
    catch + surface per-candidate.

    Args:
        candidate: a real ``WetZonePlannedCandidate``.
        grid: C7 ``Grid`` from orchestrator parameter.
        plot_analysis: C4 ``PlotAnalysis`` from orchestrator parameter.

    Returns:
        Fully-populated ``TierAOperatorContext``.

    Raises:
        CandidateContextSchemaError on missing required attributes.
    """
    # Required: zone_bands, corridor_path. The Tier A operators that
    # need them (M2, M5, M9 family) raise pre-condition errors if
    # absent — but the strict path detects schema drift earlier.
    zone_bands = _walk_strict_path(candidate, _PATH_ZONE_BANDS)
    corridor_path = _walk_strict_path(candidate, _PATH_CORRIDOR_PATH)

    # Optional / from grid + plot_analysis (these aren't on the candidate
    # ancestry chain — they're separate orchestrator parameters).
    envelope_width_m = getattr(grid, "envelope_width_m", None)
    envelope_depth_m = getattr(grid, "envelope_depth_m", None)
    staircase = getattr(grid, "staircase", None)

    plot_facing = _extract_plot_facing(plot_analysis)

    return TierAOperatorContext(
        grid=grid,
        staircase=staircase,
        envelope_width_m=envelope_width_m,
        envelope_depth_m=envelope_depth_m,
        plot_facing=plot_facing,
        zone_bands=zone_bands,
        corridor_path=corridor_path,
    )


def extract_topology_kind_strict(candidate: Any) -> str:
    """Strict topology-kind extractor. Walks the v1.0 ancestry chain.

    Returns:
        The topology kind value as a string (e.g., "central_spine").

    Raises:
        CandidateContextSchemaError on missing required attributes.
    """
    kind = _walk_strict_path(candidate, _PATH_TOPOLOGY_KIND)
    return getattr(kind, "value", str(kind))


def _extract_plot_facing(plot_analysis: Any) -> Optional[Any]:
    """Plot facing has two acceptable canonical paths since
    ``PlotAnalysis`` may carry the envelope.facing OR a top-level
    plot_facing (depending on caller). Both are strict — neither is
    a fallback for missing schema."""
    if hasattr(plot_analysis, "envelope"):
        envelope = plot_analysis.envelope
        if envelope is not None and hasattr(envelope, "facing"):
            return envelope.facing
    if hasattr(plot_analysis, "plot_facing"):
        return plot_analysis.plot_facing
    return None


# =============================================================================
# Lenient extractor (test-fixture compatibility)
# =============================================================================


def extract_tier_a_context_lenient(
    source: Any,
    grid: Any,
    plot_analysis: Any,
) -> TierAOperatorContext:
    """Duck-typed extractor for synthetic sources (Sub-4 test fixtures).

    Walks multiple fallback attribute paths and falls back silently
    to None on miss. Use ONLY when the caller is a test fixture that
    can't construct a real ``WetZonePlannedCandidate``. Production
    callers should use ``extract_tier_a_context_from_candidate``.

    Kept for backwards-compatibility with the pre-B-NEW-V orchestrator
    behaviour and the existing Sub-4 test suite.
    """
    envelope_width_m = getattr(grid, "envelope_width_m", None)
    envelope_depth_m = getattr(grid, "envelope_depth_m", None)
    staircase = getattr(grid, "staircase", None)

    plot_facing = _extract_plot_facing(plot_analysis)

    zone_bands = None
    for path in (
        _PATH_ZONE_BANDS,
        ("topology_candidate", "zone_bands"),
        ("source_candidate", "zone_bands"),
        ("zone_bands",),
    ):
        cur: Any = source
        ok = True
        for seg in path:
            cur = getattr(cur, seg, None)
            if cur is None:
                ok = False
                break
        if ok and cur is not None:
            zone_bands = cur
            break

    corridor_path = None
    for path in (
        _PATH_CORRIDOR_PATH,
        ("corridor_path",),
        ("corridor_designed_candidate", "corridor_path"),
        ("source_candidate", "corridor_path"),
    ):
        cur = source
        ok = True
        for seg in path:
            cur = getattr(cur, seg, None)
            if cur is None:
                ok = False
                break
        if ok and cur is not None:
            corridor_path = cur
            break

    return TierAOperatorContext(
        grid=grid,
        staircase=staircase,
        envelope_width_m=envelope_width_m,
        envelope_depth_m=envelope_depth_m,
        plot_facing=plot_facing,
        zone_bands=zone_bands,
        corridor_path=corridor_path,
    )


def extract_topology_kind_lenient(source: Any) -> str:
    """Duck-typed topology-kind extractor for synthetic sources."""
    for path in (
        _PATH_TOPOLOGY_KIND,
        ("topology_kind",),
        ("source_topology_kind",),
        ("topology_candidate", "kind"),
        ("source_candidate", "kind"),
        ("kind",),
    ):
        cur = source
        ok = True
        for seg in path:
            cur = getattr(cur, seg, None)
            if cur is None:
                ok = False
                break
        if ok and cur is not None:
            return getattr(cur, "value", str(cur))
    return "unknown"


# =============================================================================
# Dispatcher — strict if real WetZonePlannedCandidate, else lenient
# =============================================================================


def is_real_wet_zone_candidate(source: Any) -> bool:
    """Detect whether ``source`` is a real ``WetZonePlannedCandidate``.

    Avoids importing C10 at module load (keeps C11a's dependency
    surface narrow). Checks for the exact class via ``type().__name__``
    + module path — if either matches, it's the real type.
    """
    cls = type(source)
    if cls.__name__ != "WetZonePlannedCandidate":
        return False
    return cls.__module__.endswith("c10.schema")


def is_real_multi_floor_candidate(source: Any) -> bool:
    """Detect whether ``source`` is a real
    ``MultiFloorWetZonePlannedCandidate`` (Spec #3 v0.3 LOCKED).

    Per Spec #4 v1.6 § 3.5 (v1.3 — replaces v1.2's name-based detection
    per item 11 from v1.2 critique walk): marker-attribute lookup
    pattern. The marker is a CLASS attribute on
    ``MultiFloorWetZonePlannedCandidate`` (added at build time
    coordinated with Spec #3; NOT a dataclass field, so it does NOT
    participate in dataclass equality, hash, or repr).

    Refactor-safe, subclass-friendly, and proxy-compatible — any
    object that explicitly opts in via the class attribute is
    recognised as a multi-floor candidate.
    """
    return getattr(source, "__multi_floor_candidate__", False) is True


def extract_tier_a_context(
    source: Any,
    grid: Any,
    plot_analysis: Any,
    *,
    require_strict: bool = False,
) -> TierAOperatorContext:
    """Dispatch to strict or lenient extractor based on source type.

    Args:
        source: candidate (real or synthetic).
        grid: C7 Grid from orchestrator.
        plot_analysis: C4 PlotAnalysis from orchestrator.
        require_strict: if True, force strict extraction even on
            synthetic sources (used by tests verifying schema drift
            detection).

    Returns:
        ``TierAOperatorContext``.

    Raises:
        ``CandidateContextSchemaError`` if (a) source is a real
        WetZonePlannedCandidate with missing attributes, or
        (b) ``require_strict=True`` and source doesn't match the
        v1.0 ancestry chain.
    """
    if require_strict or is_real_wet_zone_candidate(source):
        return extract_tier_a_context_from_candidate(source, grid, plot_analysis)
    return extract_tier_a_context_lenient(source, grid, plot_analysis)


def extract_topology_kind(source: Any) -> str:
    """Dispatcher mirror for topology kind extraction."""
    if is_real_wet_zone_candidate(source):
        try:
            return extract_topology_kind_strict(source)
        except CandidateContextSchemaError:
            # Real candidate with broken chain — fall back to "unknown"
            # rather than batch-halt. The orchestrator's per-candidate
            # error-handling will surface the schema issue elsewhere
            # via the context extractor's strict raise.
            return "unknown"
    return extract_topology_kind_lenient(source)


__all__ = [
    "CandidateContextSchemaError",
    "extract_tier_a_context_from_candidate",
    "extract_tier_a_context_lenient",
    "extract_tier_a_context",
    "extract_topology_kind_strict",
    "extract_topology_kind_lenient",
    "extract_topology_kind",
    "is_real_wet_zone_candidate",
    "is_real_multi_floor_candidate",
]
