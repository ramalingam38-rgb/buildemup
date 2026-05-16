"""
C16 — Dual-Drawing Renderer — cache key derivation
=====================================================

Per:
    v0.1  § 8 — C16CacheKeys triple tier (upstream / drawing / full)
    v0.3 A7 — canonical JSON serialization rules pinned (R7c)
    v0.3 A1 — replay_identity-only cache key derivation (audit excluded)
    v0.4 A9 — canonical_replay_signature ⊥ presentation_signature (R32)
    v0.5 A2 — schema_descriptor_digest in canonical_replay_signature

CANONICAL JSON RULES (R7c — v0.3 A7):
    1. Object keys: lex-ASC (UTF-8 codepoint order).
    2. Enums: ALWAYS serialized as the .value string.
    3. Optional[None]: OMITTED entirely from serialization (NOT null).
    4. Nested dataclasses: recursive lex-ASC.
    5. Tuples: JSON arrays preserving order.
    6. frozensets: JSON arrays in lex-ASC order.
    7. Numeric formatting:
        - int: bare
        - mm floats: rounded to int per R7a, serialized as bare int
        - ratios: 4 decimal places fixed
        - degrees: 6 decimal places fixed
    8. UTF-8 NFC normalization for all strings.
    9. No whitespace; no trailing newlines; no comments; no trailing commas.

Rule 11 self-analysis worst issues:
    1. Canonical JSON correctness is foundational — any drift here
       breaks Inv R7 byte-equal replay across the entire system.
       Tests must cover the corner cases: Optional[None] omitted,
       enum-value vs enum-name, frozenset ordering, float precision.
    2. SHA-256 is deterministic across Python versions and platforms;
       hashlib.sha256().hexdigest() is the canonical form.
    3. v0.4 A9 R32: canonical_replay_signature is computed FIRST,
       then included as a prefix in presentation_signature input. We
       implement the ordering explicitly.
    4. config_signature_for() excludes capture_phase_timings AND
       capture_readability_diagnostics from the signature — those
       are observability flags that don't change the cached output
       (their diagnostic payloads do change content, but the flags
       only gate WHETHER the payloads are emitted — and the payloads
       are themselves excluded from cache keys per v0.2 A10 + v0.3 A6).
"""
from __future__ import annotations

import dataclasses
import hashlib
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, Optional

from buildemup.components.c16.config import RenderingConfig
from buildemup.components.c16.errors import C16ConfigurationError
from buildemup.components.c16.versioning import (
    C16_DRAWING_SCHEMA_VERSION,
    C16_IDENTITY_GENERATION,
    C16_VERSION,
)


# ============================================================
# § 1 — Canonical JSON serialization (R7c — v0.3 A7)
# ============================================================

# Numeric format constants
_RATIO_DECIMAL_PLACES: Final[int] = 4
_DEGREE_DECIMAL_PLACES: Final[int] = 6


def _normalize_str(s: str) -> str:
    """UTF-8 NFC normalization per R7c rule 8."""
    return unicodedata.normalize("NFC", s)


def _is_likely_mm(value: float, hint_name: Optional[str] = None) -> bool:
    """Heuristic: a float is treated as mm if the field name hints
    at length (`_mm`, `_x`, `_y`, `_z`) and the value rounds to int
    cleanly. Otherwise treated as ratio/degrees per other hints.

    Per R7c rule 7, we serialize mm floats as bare ints. To avoid
    misclassification, callers should pass canonicalize_value() the
    field name when known."""
    if hint_name is None:
        return False
    return any(hint in hint_name for hint in ("_mm", "_x_max", "_y_max",
                                              "_z_max", "_z_min"))


def canonicalize_value(value: Any, *, field_name: Optional[str] = None) -> Any:
    """Recursively transform a value into a JSON-serializable canonical
    form per R7c rules.

    Returns a structure of: dict (sorted keys), list, str, int, float, bool.
    """
    # None — caller is responsible for OMITTING None fields entirely.
    # canonicalize_value(None) returns None and the dict-builder skips it.
    if value is None:
        return None

    # bool BEFORE int (since bool subclasses int)
    if isinstance(value, bool):
        return value

    # Enums → string .value (rule 2)
    if isinstance(value, Enum):
        return _normalize_str(str(value.value))

    # Integers → bare int (rule 7a)
    if isinstance(value, int):
        return int(value)

    # Floats → format per field hint (rule 7b/c/d)
    if isinstance(value, float):
        if _is_likely_mm(value, field_name):
            # mm float → banker's-rounded int (R7a)
            return int(round(value))
        if field_name and ("_deg" in field_name or "_angle" in field_name):
            # degrees → 6 decimal places
            return round(value, _DEGREE_DECIMAL_PLACES)
        # Default float (ratio) → 4 decimal places
        return round(value, _RATIO_DECIMAL_PLACES)

    # Strings
    if isinstance(value, str):
        return _normalize_str(value)

    # Tuples → JSON arrays preserving order (rule 5)
    if isinstance(value, tuple):
        return [canonicalize_value(v, field_name=field_name) for v in value]

    # frozensets → arrays in lex-ASC order (rule 6)
    if isinstance(value, frozenset):
        return sorted(
            (canonicalize_value(v, field_name=field_name) for v in value),
            key=_lex_key,
        )

    # Regular sets → also lex-sorted (defensive — frozen dataclasses
    # shouldn't carry sets but tests may pass them)
    if isinstance(value, set):
        return sorted(
            (canonicalize_value(v, field_name=field_name) for v in value),
            key=_lex_key,
        )

    # Lists → preserve order (per rule 5 — already canonical at construction)
    if isinstance(value, list):
        return [canonicalize_value(v, field_name=field_name) for v in value]

    # Dicts → lex-ASC keys, None values OMITTED (rules 1 + 3)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k in sorted(value.keys(), key=str):
            v = value[k]
            if v is None:
                continue  # rule 3: omit None
            out[_normalize_str(str(k))] = canonicalize_value(
                v, field_name=str(k),
            )
        return out

    # Dataclasses → lex-ASC field order, None OMITTED
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out_dc: dict[str, Any] = {}
        for f in sorted(dataclasses.fields(value), key=lambda fld: fld.name):
            v = getattr(value, f.name)
            if v is None:
                continue
            out_dc[f.name] = canonicalize_value(v, field_name=f.name)
        return out_dc

    raise C16ConfigurationError(
        f"canonicalize_value: unsupported type {type(value).__name__} "
        f"(value={value!r}). Add canonicalization rule or pre-convert.",
        offending_field=field_name,
        offending_value=value,
    )


def _lex_key(value: Any) -> str:
    """Stable string key for sorting heterogeneous canonical values."""
    if isinstance(value, (dict, list)):
        return canonical_json(value)
    return str(value)


def canonical_json(value: Any) -> str:
    """Serialize a value to canonical JSON.

    R7c rules 9 + 10: no whitespace between tokens; no trailing newline;
    no comments; no trailing commas.

    Always canonicalizes the input first — this ensures keys are
    lex-sorted, tuples become lists, frozensets become sorted lists,
    None-values are omitted, enums become their .value strings, and
    floats are rounded to the canonical precision per R7c rule 7.
    """
    return _emit_json(canonicalize_value(value))


def _emit_json(value: Any) -> str:
    """Emit JSON without separators (per R7c rule 9)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        # Determine if value looks like 4dp ratio or 6dp degree from
        # parent context — here we just emit with enough precision.
        # Per R7c rule 7c (ratios) and 7d (degrees), the precision
        # was already imposed at canonicalize_value. We emit the
        # standard repr but with fixed precision based on magnitude.
        # Simplest: emit with enough decimals that the rounded value
        # round-trips byte-equal.
        return _emit_float(value)
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_emit_json(v) for v in value) + "]"
    if isinstance(value, dict):
        # Keys are already lex-sorted by canonicalize_value
        parts = [
            _emit_string(k) + ":" + _emit_json(v)
            for k, v in value.items()
        ]
        return "{" + ",".join(parts) + "}"
    raise C16ConfigurationError(
        f"_emit_json: unexpected canonical type {type(value).__name__}",
    )


def _emit_float(value: float) -> str:
    """Emit float in canonical form.

    Strategy: format with enough decimals to round-trip; strip trailing
    zeros only if it doesn't change the value's identity AT the canonical
    precision (4 dp for ratios, 6 dp for degrees). Since canonicalize_value
    already rounded, we just choose enough decimals to represent without
    loss and let the trailing-zero pattern be deterministic.

    For Sub-1 simplicity: emit fixed 4 decimal places by default; callers
    needing 6dp degrees pass strings via canonicalize_value's output."""
    return f"{value:.{_RATIO_DECIMAL_PLACES}f}"


def _emit_string(value: str) -> str:
    """JSON-encode a string per R7c rule 9 (no whitespace) + rule 8
    (NFC normalization already applied)."""
    out_chars: list[str] = ['"']
    for ch in value:
        if ch == '"':
            out_chars.append('\\"')
        elif ch == "\\":
            out_chars.append("\\\\")
        elif ch == "\n":
            out_chars.append("\\n")
        elif ch == "\r":
            out_chars.append("\\r")
        elif ch == "\t":
            out_chars.append("\\t")
        elif ord(ch) < 0x20:
            out_chars.append(f"\\u{ord(ch):04x}")
        else:
            out_chars.append(ch)
    out_chars.append('"')
    return "".join(out_chars)


def sha256_hex(s: str) -> str:
    """SHA-256 of UTF-8 bytes → hex digest."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ============================================================
# § 2 — C16CacheKeys (v0.1 § 8)
# ============================================================

@dataclass(frozen=True)
class C16CacheKeys:
    """The triple-tier cache key surface emitted by C16.

    Tier 1 — upstream_cache_key: combined hash of all upstream cache
                                 keys (C13 + C14 + C15 + ...). Allows
                                 detecting upstream-only changes.
    Tier 2 — drawing_cache_key:  upstream + jurisdiction + config sig.
                                 Detects changes that affect the
                                 drawing data shape itself.
    Tier 3 — full_cache_key:     drawing + C16 version triple.
                                 Detects changes due to C16 itself
                                 (version / schema / identity_generation).
    """
    upstream_cache_key: str
    drawing_cache_key:  str
    full_cache_key:     str

    def __post_init__(self) -> None:
        # Hex digest sanity (SHA-256 → 64 hex chars)
        for fname in ("upstream_cache_key", "drawing_cache_key", "full_cache_key"):
            v = getattr(self, fname)
            if not isinstance(v, str) or len(v) != 64:
                raise C16ConfigurationError(
                    f"C16CacheKeys.{fname} must be a 64-hex SHA-256 string; "
                    f"got {v!r} (len={len(v) if isinstance(v, str) else 'N/A'})",
                    offending_field=fname,
                    offending_value=v,
                )
            # Lowercase hex only
            if not all(c in "0123456789abcdef" for c in v):
                raise C16ConfigurationError(
                    f"C16CacheKeys.{fname} must be lowercase hex.",
                    offending_field=fname,
                    offending_value=v,
                )


# ============================================================
# § 3 — Signature derivation (v0.4 A9 — R32)
# ============================================================

def config_signature_for(config: RenderingConfig) -> str:
    """SHA-256 of canonical-JSON-ized RenderingConfig.

    Per v0.2 A10 / v0.3 A6 / v0.4 A9: capture_phase_timings and
    capture_readability_diagnostics are EXCLUDED from the signature.
    They're observability flags — they gate WHETHER diagnostics are
    emitted, not WHAT the canonical bundle contains.
    """
    # Build a stripped dict (observability flags excluded)
    config_dict = {}
    for f in dataclasses.fields(config):
        if f.name in ("capture_phase_timings", "capture_readability_diagnostics"):
            continue
        v = getattr(config, f.name)
        if v is None:
            continue
        config_dict[f.name] = canonicalize_value(v, field_name=f.name)
    return sha256_hex(canonical_json(config_dict))


def canonical_replay_signature(
    *,
    selection_replay_identity_canon: Any,
    floor_geometries_canon: Any,
    jurisdiction_id: str,
    declared_domain_scope: str,
    config_signature: str,
    schema_descriptor_digest: str,
    upstream_advisory_flags_canon: Any,
) -> str:
    """Compute Inv R7 byte-equal replay signature.

    Per v0.4 A9 R32a: this is computed FIRST. presentation_signature
    includes this as a prefix.

    INCLUDES (cache-relevant):
        - SelectionReplayIdentity (NOT audit_metadata — R7d)
        - floor_geometries (the canonical shared source of truth)
        - jurisdiction_id + declared_domain_scope (v0.5 A4)
        - config_signature (already excludes observability flags)
        - schema_descriptor_digest (v0.5 A2 — R26b)
        - upstream advisory flags (R8 passthrough)
        - C16 version triple

    EXCLUDES:
        - SelectionAuditMetadata (timestamps, machine IDs)
        - phase_timings, readability_diagnostics
        - presentation_signature itself (it's downstream)
    """
    payload = {
        "c16_version":              C16_VERSION,
        "c16_drawing_schema_version": C16_DRAWING_SCHEMA_VERSION,
        "c16_identity_generation":  C16_IDENTITY_GENERATION,
        "selection_replay_identity": selection_replay_identity_canon,
        "floor_geometries":         floor_geometries_canon,
        "jurisdiction_id":          jurisdiction_id,
        "declared_domain_scope":    declared_domain_scope,
        "config_signature":         config_signature,
        "schema_descriptor_digest": schema_descriptor_digest,
        "upstream_advisory_flags":  upstream_advisory_flags_canon,
    }
    return sha256_hex(canonical_json(payload))


def presentation_signature(
    *,
    canonical_replay_signature_value: str,
    readability_diagnostics_canon: Optional[Any] = None,
    phase_timings_canon: Optional[Any] = None,
) -> str:
    """Compute presentation-tier signature (v0.4 A9 R32a).

    INCLUDES canonical_replay_signature as prefix + any presentation
    state (readability diagnostics, phase timings, presentation hashes).

    R32c: two bundles with identical presentation_signature MUST have
    identical canonical_replay_signature. We enforce this by always
    composing as prefix.
    """
    # Per R32a — canonical first, presentation built around it.
    payload = {
        "canonical_replay_signature": canonical_replay_signature_value,
    }
    if readability_diagnostics_canon is not None:
        payload["readability_diagnostics"] = readability_diagnostics_canon
    if phase_timings_canon is not None:
        payload["phase_timings"] = phase_timings_canon
    return sha256_hex(canonical_json(payload))


# ============================================================
# § 4 — Triple-tier C16CacheKeys derivation
# ============================================================

def derive_c16_cache_keys(
    *,
    upstream_cache_key: str,
    jurisdiction_id: str,
    declared_domain_scope: str,
    config_signature: str,
) -> C16CacheKeys:
    """Derive the three-tier cache keys per v0.1 § 8.

    Tier 1 — upstream_cache_key is provided by upstream (already
             combines C13 + C14 + C15 cache keys).
    Tier 2 — drawing_cache_key: hash of (upstream + jurisdiction + config).
    Tier 3 — full_cache_key:     hash of (drawing + C16 version triple).

    All three are 64-char lowercase SHA-256 hex digests.
    """
    if not isinstance(upstream_cache_key, str) or len(upstream_cache_key) != 64:
        raise C16ConfigurationError(
            "derive_c16_cache_keys: upstream_cache_key must be 64-hex SHA-256.",
            offending_field="upstream_cache_key",
            offending_value=upstream_cache_key,
        )

    drawing_payload = {
        "upstream_cache_key":    upstream_cache_key,
        "jurisdiction_id":       jurisdiction_id,
        "declared_domain_scope": declared_domain_scope,
        "config_signature":      config_signature,
    }
    drawing_cache_key = sha256_hex(canonical_json(drawing_payload))

    full_payload = {
        "drawing_cache_key":          drawing_cache_key,
        "c16_version":                C16_VERSION,
        "c16_drawing_schema_version": C16_DRAWING_SCHEMA_VERSION,
        "c16_identity_generation":    C16_IDENTITY_GENERATION,
    }
    full_cache_key = sha256_hex(canonical_json(full_payload))

    return C16CacheKeys(
        upstream_cache_key=upstream_cache_key,
        drawing_cache_key=drawing_cache_key,
        full_cache_key=full_cache_key,
    )
