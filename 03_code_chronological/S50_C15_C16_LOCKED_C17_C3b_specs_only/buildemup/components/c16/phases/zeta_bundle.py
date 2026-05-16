"""
C16 Phase ζ — Bundle assembly + signature stamping
======================================================

Per v0.5 LOCKED spec § 3 Phase ζ + v0.4 A9 (R32) + v0.5 A2 (R26b).

INPUT:
    - EnvelopeAssembly (Phase α)
    - WorkingDrawingModel (Phase γ)
    - PermitDrawingModel (Phase ε, post-attestation)
    - SelectionResult
    - JurisdictionProfile
    - RenderingConfig
    - upstream_cache_key (from upstream_inputs)
    - Optional PhaseTimings (observability)
    - Optional ReadabilityDiagnostics (observability)
    - Tuple of AdvisoryFlag (R8 passthrough)

PROCESSING:
    1. Compute SchemaDescriptor + its R26b digest
    2. Compute canonical_replay_signature (R7 byte-equal replay)
    3. Compute presentation_signature (R32a — canonical as prefix)
    4. Derive C16CacheKeys (triple-tier)
    5. Construct DualDrawingBundle — this fires R20 / R24 / R33b
       at __post_init__

OUTPUT:
    DualDrawingBundle (with R20 / R24 / R33b enforced).
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from buildemup.components.c16.cache_keys import (
    canonical_json,
    canonical_replay_signature,
    canonicalize_value,
    config_signature_for,
    derive_c16_cache_keys,
    presentation_signature,
    sha256_hex,
)
from buildemup.components.c16.config import RenderingConfig
from buildemup.components.c16.contracts import (
    JurisdictionProfile,
    SelectionResult,
)
from buildemup.components.c16.schema import (
    AdvisoryFlag,
    DualDrawingBundle,
    PermitDrawingModel,
    PhaseTimings,
    ReadabilityDiagnostics,
    SchemaDescriptor,
    WorkingDrawingModel,
    compute_schema_descriptor_digest,
)
from buildemup.components.c16.versioning import (
    C16_DRAWING_SCHEMA_VERSION,
    C16_IDENTITY_GENERATION,
    C16_VERSION,
)
from buildemup.components.c16.phases.alpha_envelope import EnvelopeAssembly


def execute_phase_zeta(
    *,
    envelope:             EnvelopeAssembly,
    working_model:        WorkingDrawingModel,
    permit_model:         PermitDrawingModel,
    selection_result:     SelectionResult,
    jurisdiction_profile: JurisdictionProfile,
    config:               RenderingConfig,
    upstream_cache_key:   str,
    upstream_advisory_flags: tuple[AdvisoryFlag, ...] = (),
    phase_timings:        Optional[PhaseTimings] = None,
    readability_diagnostics: Optional[ReadabilityDiagnostics] = None,
) -> DualDrawingBundle:
    """Phase ζ main entry point."""

    # 1. SchemaDescriptor + R26b digest
    descriptor = SchemaDescriptor(
        c16_version=C16_VERSION,
        c16_drawing_schema_version=C16_DRAWING_SCHEMA_VERSION,
        c16_identity_generation=C16_IDENTITY_GENERATION,
        jurisdiction_id=jurisdiction_profile.jurisdiction_id,
        declared_domain_scope=jurisdiction_profile.declared_domain_scope,
    )
    schema_digest = compute_schema_descriptor_digest(descriptor)

    # 2. Canonical replay signature (R7 byte-equal — R7d: no time/env)
    selection_identity_canon = canonicalize_value(selection_result.replay_identity)
    floor_geos_canon = canonicalize_value(envelope.floor_geometries)
    flags_canon = canonicalize_value(upstream_advisory_flags)
    config_sig = config_signature_for(config)

    crs = canonical_replay_signature(
        selection_replay_identity_canon=selection_identity_canon,
        floor_geometries_canon=floor_geos_canon,
        jurisdiction_id=jurisdiction_profile.jurisdiction_id,
        declared_domain_scope=jurisdiction_profile.declared_domain_scope,
        config_signature=config_sig,
        schema_descriptor_digest=schema_digest,
        upstream_advisory_flags_canon=flags_canon,
    )

    # 3. Presentation signature (R32a — canonical as prefix)
    timings_canon = (
        canonicalize_value(phase_timings) if phase_timings is not None else None
    )
    diag_canon = (
        canonicalize_value(readability_diagnostics)
        if readability_diagnostics is not None else None
    )
    ps = presentation_signature(
        canonical_replay_signature_value=crs,
        readability_diagnostics_canon=diag_canon,
        phase_timings_canon=timings_canon,
    )

    # 4. C16CacheKeys triple-tier
    # If upstream didn't supply a cache key (test fixtures often pass ""),
    # synthesize one deterministically from the selection signature so
    # derive_c16_cache_keys() has a valid 64-hex input.
    if not upstream_cache_key or len(upstream_cache_key) != 64:
        upstream_cache_key = sha256_hex(
            selection_result.replay_identity.selected_layout_signature
        )

    cache_keys = derive_c16_cache_keys(
        upstream_cache_key=upstream_cache_key,
        jurisdiction_id=jurisdiction_profile.jurisdiction_id,
        declared_domain_scope=jurisdiction_profile.declared_domain_scope,
        config_signature=config_sig,
    )

    # Per Inv R8 — advisory flags are passed THROUGH byte-identically.
    # Sort canonically for replay (Inv R7c).
    sorted_flags = tuple(sorted(
        upstream_advisory_flags,
        key=lambda f: (f.source_component, f.flag_id),
    ))

    # Source selection signature: per v0.3 A1 R7, the canonical hash of
    # replay_identity (NOT including audit metadata).
    source_selection_signature = sha256_hex(
        canonical_json(selection_result.replay_identity)
    )

    # 5. Construct DualDrawingBundle — fires R20 / R24 / R33b
    return DualDrawingBundle(
        source_selection_signature=source_selection_signature,
        selection_audit_metadata=selection_result.audit_metadata,
        c16_version=C16_VERSION,
        c16_drawing_schema_version=C16_DRAWING_SCHEMA_VERSION,
        jurisdiction_profile_id=jurisdiction_profile.jurisdiction_id,
        declared_domain_scope=jurisdiction_profile.declared_domain_scope,
        floor_geometries=envelope.floor_geometries,
        local_building_frame=envelope.local_building_frame,
        geospatial_reference=envelope.geospatial_reference,
        working_drawing_model=working_model,
        permit_drawing_model=permit_model,
        upstream_advisory_flags=sorted_flags,
        cache_keys=cache_keys,
        canonical_replay_signature=crs,
        presentation_signature=ps,
        schema_descriptor_digest=schema_digest,
        phase_timings=phase_timings,
        readability_diagnostics=readability_diagnostics,
    )
