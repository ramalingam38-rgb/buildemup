"""
C16 — Dual-Drawing Renderer — error hierarchy
================================================

Per v0.1 § 4 + v0.3 A5 + v0.5 A5.

TWO-TIER design (mirrors C13 / C14 / C15):

    LocalDrawingError       — always halts regardless of strict_mode.
                              Indicates a config/contract problem that
                              cannot be salvaged by partial output.

    PerLayoutDrawingError   — STRICT mode raises; WARN mode collects
                              into FailedDrawingRender.failure_record
                              and the batch continues.

This split mirrors the spec § 5 failure-mode contract: local errors
are global problems (jurisdiction not supported, config invalid)
while per-layout errors are problems with one specific layout that
the orchestrator can quarantine without taking the whole batch down.
"""

from __future__ import annotations

from typing import Any, Optional


# ============================================================
# § 1 — BASE
# ============================================================

class DrawingRenderError(Exception):
    """Root of the C16 error hierarchy.

    Never raised directly. Always raised as one of the two-tier
    subtypes below so that orchestrator routing (STRICT vs WARN) is
    unambiguous.
    """


# ============================================================
# § 2 — LOCAL (always-halt) tier
# ============================================================

class LocalDrawingError(DrawingRenderError):
    """Always halts. Indicates a contract/config problem that cannot
    be salvaged. Bypasses strict_mode/WARN-mode entirely.

    Subtypes describe SHAPE of the local failure:
        UpstreamSchemaDriftError        — C7/C9/C10/C12/C13/C14/C15
                                          version mismatch or schema
                                          shape we don't recognize.
        C16ConfigurationError           — RenderingConfig invalid
                                          (e.g. bound exceeds hard
                                          ceiling per v0.5 A4 / R31a).
        JurisdictionNotSupportedError   — jurisdiction outside
                                          SUPPORTED_JURISDICTIONS.
        OrientationLockMismatchError    — v0.5 A5 / R29d:
                                          OrientationLock implausible
                                          against current geometry.
    """


class UpstreamSchemaDriftError(LocalDrawingError):
    """An upstream component's output schema doesn't match what C16
    expects. Common triggers:
        - C13_VERSION on output != EXPECTED_C13_VERSION
        - C15 ProblemReport missing fields C16 needs for provenance
        - C7 wall graph not in canonical sorted order

    This is ALWAYS a contract bug — fix upstream or bump EXPECTED_*."""

    def __init__(
        self,
        message: str,
        *,
        upstream_component: str,
        expected_version: Optional[str] = None,
        observed_version: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.upstream_component = upstream_component
        self.expected_version = expected_version
        self.observed_version = observed_version


class C16ConfigurationError(LocalDrawingError):
    """RenderingConfig or JurisdictionProfile constructed with values
    C16 cannot honor — e.g. coordinate bounds beyond HARD_CEILING_*
    (v0.5 A4 / R31a), unsupported scale literals, unsupported
    declared_domain_scope (R31b).

    NOTE: per v0.5 A4 — even attempts to declare bounds beyond hard
    ceiling raise THIS at config construction, not at render time.
    Fail fast."""

    def __init__(
        self,
        message: str,
        *,
        offending_field: Optional[str] = None,
        offending_value: Any = None,
    ) -> None:
        super().__init__(message)
        self.offending_field = offending_field
        self.offending_value = offending_value


class JurisdictionNotSupportedError(LocalDrawingError):
    """JurisdictionProfile.jurisdiction_id not in
    SUPPORTED_JURISDICTIONS (currently: only 'tn_cdbr_2019')."""

    def __init__(
        self,
        message: str,
        *,
        requested_jurisdiction: str,
        supported: frozenset[str],
    ) -> None:
        super().__init__(message)
        self.requested_jurisdiction = requested_jurisdiction
        self.supported = supported


class OrientationLockMismatchError(LocalDrawingError):
    """v0.5 A5 / R29d: OrientationLock.locked_x_axis_orientation_deg
    is not within EPSILON_ANGLE_DEG of ANY of the four hierarchy
    candidates computed from current geometry.

    A mismatch indicates the building geometry has changed so much
    since the lock was set that the lock no longer makes sense.
    Manual review required — C16 will not silently re-derive."""

    def __init__(
        self,
        message: str,
        *,
        locked_orientation_deg: float,
        candidate_orientations_deg: tuple[float, ...],
        epsilon_deg: float,
    ) -> None:
        super().__init__(message)
        self.locked_orientation_deg = locked_orientation_deg
        self.candidate_orientations_deg = candidate_orientations_deg
        self.epsilon_deg = epsilon_deg


# ============================================================
# § 3 — PER-LAYOUT (strict-raise / warn-collect) tier
# ============================================================

class PerLayoutDrawingError(DrawingRenderError):
    """STRICT mode → raised; WARN mode → caught + collected into
    FailedDrawingRender.failure_record. Batch continues in WARN mode.

    Subtypes describe SHAPE of the per-layout failure:
        MissingUpstreamDataError    — required upstream field is
                                      None / empty / unparseable.
        GeometryInconsistencyError  — geometry violates Inv R19-R24
                                      (bounds, referential integrity).
        ComplianceProvenanceError   — Inv R15 / R22 / R25 / R30
                                      violation (compliance claim
                                      without proper upstream trace
                                      or wrong authority kind).
    """


class MissingUpstreamDataError(PerLayoutDrawingError):
    """A required upstream field is None or empty for the layout
    we're trying to render. Common triggers:
        - SelectionResult.replay_identity.selected_layout_signature is ""
        - C13 emitted zero doors but the layout has rooms
        - C12 didn't emit floor elevations for a multi-floor design

    STRICT raises; WARN catches → partial bundle marked
    UNSAFE_FOR_SUBMISSION."""

    def __init__(
        self,
        message: str,
        *,
        missing_field: str,
        upstream_component: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.missing_field = missing_field
        self.upstream_component = upstream_component


class GeometryInconsistencyError(PerLayoutDrawingError):
    """Geometry violates one or more of:
        R19  — coordinate outside HARD_CEILING_* or RenderingConfig bounds
        R20  — geometry parity (working vs permit geometry_ref mismatch)
        R23  — section cut fallback degenerate (no valid offset exists)
        R24a — geometry_ref does not resolve to any FloorGeometry
        R24b — orphan FloorGeometry (no overlay references it)
        R24c — duplicate geometry_id

    The specific sub-clause violated is recorded on the exception
    for downstream filtering and reporting."""

    def __init__(
        self,
        message: str,
        *,
        invariant_id: str,                # e.g. "R24a", "R20", "R23"
        offending_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.invariant_id = invariant_id
        self.offending_ids = offending_ids


class ComplianceProvenanceError(PerLayoutDrawingError):
    """A ComplianceAttestation field violates the provenance-discipline
    contract:

        R15  — claim without ANY upstream CheckProvenance entry.
        R22  — AttestedValue with wrong authority/source/note combo
               (LOCALLY_DERIVED with non-empty upstream_source, or
               UPSTREAM_AUTHORITATIVE with empty upstream_source, etc.)
        R25  — submission_readiness influenced by a non-
               UPSTREAM_AUTHORITATIVE value.
        R30a — legal_completeness derived from anything other than
               UPSTREAM_AUTHORITATIVE entries.

    This error means: C16 was about to silently become a shadow
    compliance engine. The pre-LOCK governance work in v0.2 A5 /
    v0.3 A5 / v0.4 A5 exists precisely to surface this at every
    boundary."""

    def __init__(
        self,
        message: str,
        *,
        invariant_id: str,
        attested_field: Optional[str] = None,
        authority_observed: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.invariant_id = invariant_id
        self.attested_field = attested_field
        self.authority_observed = authority_observed
