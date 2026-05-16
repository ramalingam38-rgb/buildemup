"""
C3b — Post-Layout Trade-off Negotiation — canonical hashing (R6/R7/R8)
========================================================================

Spec: C3b v0.4.LOCKED § 7 R6/R7/R8. Build session: S52.

Three deterministic signatures pinning replay identity, presentation
identity, and schema shape:

  canonical_replay_signature  — R6  — byte-equal given same inputs +
                                       same user-action sequence
  presentation_signature      — R7  — derived (canonical as prefix)
  schema_descriptor_digest    — R8  — schema-version stable; invariant
                                       to data values

Inheritance pattern from C17 v0.3 LOCKED (which inherited from C16
v1.2 LOCKED). The C17 cache_keys module passed S51's R6 byte-equal
10-run replay test; C3b mirrors that pattern.

Per spec § 3 Phase δ:
  Compute canonical_replay_signature (R6), presentation_signature (R7),
  schema_descriptor_digest (R8) at session emit time. Re-compute at
  Phase ζ resolution.

Rule 11 self-analysis (worst issues hunted):
  1. _canon walks Python objects recursively. We round floats to 6
     decimals (CANONICAL_FLOAT_DECIMALS) to dodge ULP-level
     nondeterminism. Tested against random-seeded inputs in test_cache_keys.
  2. strict_mode IS part of canonical_replay_signature — running the
     same session in strict vs warn produces different signatures by
     design (warn may have collected per-tweak failures, strict may
     have halted earlier). Documented.
  3. schema_descriptor_digest is over dataclass FIELD NAMES + TYPES,
     not values. Adding a field bumps the digest; renaming bumps it;
     reordering DOES NOT (we sort fields lexicographically before hash).
  4. presentation_signature in v1.0 is a derived hash with the
     canonical_replay_signature as input — narrowed R15 (matches C17
     v0.3). v1.x may expand to encode presentation-only state
     (UI scroll position, etc.) separately; not v1.0.
  5. session_id is INCLUDED in canonical_replay_signature inputs
     because different sessions produce different signatures even
     for identical inputs — sessions are intentionally individuated.
     If we ever needed input-only fingerprinting (cache lookup), that
     would be a separate `compute_input_fingerprint` (not yet needed).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

from .versioning import (
    C3B_SESSION_SCHEMA_VERSION,
    C3B_VERSION,
    CANONICAL_FLOAT_DECIMALS,
    SIGNATURE_HEX_LENGTH,
)

# Schema introspection imports — must be evaluated at module load to
# stabilize schema_descriptor_digest across the process lifetime
from .schema import (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)


# ============================================================
# § 1 — Canonicalization helper
# ============================================================

def _canon(value: Any) -> Any:
    """Recursively canonicalize a Python value to a hash-friendly,
    deterministic representation:

      - dict   → sorted by key, then recursive _canon on values
      - tuple  → list (recursive _canon)
      - list   → list (recursive _canon)
      - set    → sorted list (recursive _canon)
      - float  → rounded to CANONICAL_FLOAT_DECIMALS (6)
      - bool   → bool (not int — JSON-distinct)
      - dataclass → asdict + recurse
      - enum   → its .value (StrEnum: the string)
      - None   → None
      - other  → its str() — last-resort; rare in our domain
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return round(value, CANONICAL_FLOAT_DECIMALS)
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    if isinstance(value, set):
        return sorted([_canon(v) for v in value], key=lambda x: str(x))
    if dataclasses.is_dataclass(value):
        # Convert the dataclass to a dict then canonicalize
        return _canon(dataclasses.asdict(value))
    # StrEnum/Enum
    if hasattr(value, "value") and not callable(value.value):
        return _canon(value.value)
    # Last resort
    return str(value)


def _sha256_hex(obj: Any) -> str:
    """Stable sha256 hex digest of a canonicalized object."""
    canonical = _canon(obj)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ============================================================
# § 2 — R6: canonical_replay_signature
# ============================================================

def compute_canonical_replay_signature(
    *,
    session: TradeoffSession,
    strict_mode: str,
) -> str:
    """R6 byte-equal replay signature.

    Inputs to the hash:
      - session_id (intentional individuation)
      - C3B_VERSION + schema_version (R8 inheritance)
      - strict_mode (different mode → different replay)
      - all tweak_option_sets (canonicalized)
      - all session_history turns (R12 audit-trail discipline,
        BUT v0.5 R17: strategic_advisory_text excluded)
      - iteration_count + iteration_cap
      - current_status
      - resolved_selection (None or canonicalized)
      - advisory_flags
      - mutation_envelopes
      - medium_tweak_count_since_full_recompute (v0.5 A2 — affects
        future branching, so part of replay state)

    NOT included:
      - canonical_replay_signature itself (recursion)
      - presentation_signature, schema_descriptor_digest (derived)
      - SessionTurn.strategic_advisory_text (R17 — informational only,
        produced by external provider, must not affect replay sigs)
      - extension_metadata (R19 — research/experimental annotation
        channel, must not affect replay sigs)
    """
    # v0.5 R17 — strip strategic_advisory_text from each turn before
    # canonicalizing. Build a list of "signature-relevant turn" dicts.
    sig_turns = []
    for t in session.session_history:
        turn_dict = {
            "turn_id":              t.turn_id,
            "iteration_index":      t.iteration_index,
            "timestamp_offset_ms":  t.timestamp_offset_ms,
            "presented_tweaks":     t.presented_tweaks,
            "user_action":          t.user_action,
            "chosen_tweak_id":      t.chosen_tweak_id,
            "apply_outcome":        t.apply_outcome,
            "post_turn_status":     t.post_turn_status,
            # NOTE: strategic_advisory_text intentionally excluded (R17)
        }
        sig_turns.append(turn_dict)

    payload = {
        "session_id":                    session.session_id,
        "source_selection_result_id":    session.source_selection_result_id,
        "source_brief_signature":        session.source_brief_signature,
        "source_plot_analysis_id":       session.source_plot_analysis_id,
        "c3b_version":                   session.c3b_version,
        "c3b_schema_version":            session.c3b_schema_version,
        "jurisdiction_profile_id":       session.jurisdiction_profile_id,
        "strict_mode":                   strict_mode,
        "tweak_option_sets":             _canon(session.tweak_option_sets),
        "session_history":               _canon(sig_turns),
        "iteration_count":               session.iteration_count,
        "iteration_cap":                 session.iteration_cap,
        "current_status":                session.current_status,
        "resolved_selection":            _canon(session.resolved_selection),
        "advisory_flags":                _canon(session.advisory_flags),
        "mutation_envelopes":            _canon(session.mutation_envelopes),
        # v0.5 A2 — full-recompute counter affects future branching
        "medium_tweak_count_since_full_recompute": (
            session.medium_tweak_count_since_full_recompute
        ),
    }
    return _sha256_hex(payload)


# ============================================================
# § 3 — R7: presentation_signature
# ============================================================

def compute_presentation_signature(*, canonical_replay_signature: str) -> str:
    """R7 presentation signature.

    v1.0 narrowed R15: presentation_signature is a derived hash of the
    canonical_replay_signature plus a 'presentation' domain tag. This
    matches C17 v0.3's pattern.

    v1.x may extend to encode UI-specific state separately (B-C3B-
    DOWNSTREAM-RENDERER-BEHAVIORAL-CONTRACT in backlog § 9.2)."""
    if not canonical_replay_signature:
        raise ValueError(
            "compute_presentation_signature: canonical_replay_signature "
            "must be non-empty"
        )
    payload = {
        "canonical_replay": canonical_replay_signature,
        "presentation_v":   C3B_VERSION,
        "domain":           "c3b_presentation",
    }
    return _sha256_hex(payload)


# ============================================================
# § 4 — R8: schema_descriptor_digest
# ============================================================

_SCHEMA_DATACLASSES = (
    AdvisoryFlag,
    ApplyOutcome,
    ApplySpecification,
    CompatibilityAssertion,
    ComfortImpact,
    FinishSchedulePayload,
    GeometryLocalPayload,
    KickBackPayload,
    MutationEnvelope,
    ResolvedSelection,
    SessionTurn,
    SpaceImpact,
    SubsetRerunRequest,
    TopologyInvarianceResult,
    TradeoffSession,
    TweakOption,
    TweakOptionSet,
    TweakProvenance,
)


def _describe_dataclass(cls: type) -> dict:
    """Schema descriptor for ONE dataclass — its fields, sorted by name,
    each with its type annotation as a string. This is value-invariant
    by design (R8)."""
    fields = []
    for f in sorted(dataclasses.fields(cls), key=lambda x: x.name):
        # Use string-form of annotation; works for Literal[...] / tuple[...] etc.
        type_str = str(f.type) if not isinstance(f.type, str) else f.type
        fields.append({"name": f.name, "type": type_str})
    return {"name": cls.__name__, "fields": fields}


def compute_schema_descriptor_digest() -> str:
    """R8 schema descriptor digest.

    Stable across runs given the same set of dataclass definitions.
    Bumps when:
      - A field is added or removed
      - A field is renamed
      - A field's type annotation changes
    Does NOT bump when:
      - Field order in source changes (we sort)
      - Field values change
      - Dataclass docstrings change
    """
    descriptors = [
        _describe_dataclass(cls)
        for cls in sorted(_SCHEMA_DATACLASSES, key=lambda c: c.__name__)
    ]
    payload = {
        "schema_descriptors": descriptors,
        "schema_version":     C3B_SESSION_SCHEMA_VERSION,
        "component":          "c3b",
    }
    return _sha256_hex(payload)


# ============================================================
# § 5 — Convenience helpers for tests
# ============================================================

def is_valid_signature(sig: str) -> bool:
    """A signature is 64 hex chars (sha256)."""
    if not isinstance(sig, str) or len(sig) != SIGNATURE_HEX_LENGTH:
        return False
    try:
        int(sig, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "compute_canonical_replay_signature",
    "compute_presentation_signature",
    "compute_schema_descriptor_digest",
    "is_valid_signature",
    "_canon", "_sha256_hex",  # exposed for tests
]
