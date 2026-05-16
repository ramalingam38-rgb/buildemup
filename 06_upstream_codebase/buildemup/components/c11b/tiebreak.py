"""
BuildemUp — Component 11b — tie-break fingerprint derivation
==============================================================

Per SPEC v1.1 LOCKED § 0.7.1 (deterministic tie-break) +
§ 0.7.1 W6-3 (HIGH-severity schema-version anchor fix).

The function ``_compute_tiebreak_fingerprint`` is computed ONCE at
``RefinedCandidate.__post_init__`` per spec W5-12 optimization. The
result is a 64-bit big-endian int used by NSGA-II survivor selection
as layer 2 of the lex-ASC tie-break key (see ``nsga2/selection.py``).

The W6-3 fix is the entire reason ``TIEBREAK_FINGERPRINT_SCHEMA_VERSION``
exists. Without it, a future change to ``CANONICAL_FP_PRECISION`` in
``utilities/canonical.py`` would silently corrupt cached fingerprints
at the same ``c11b_version``. See ``versioning.py`` for full rationale.
"""
from __future__ import annotations

import hashlib
from typing import Any

from buildemup.components.c11b.versioning import (
    TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
)
from buildemup.utilities.canonical import canonical_serialize


def _compute_tiebreak_fingerprint(refined_parameters: Any) -> int:
    """64-bit big-endian int from first 8 bytes of
    ``sha256(VERSION + canonical_serialize(refined_parameters))``.

    Per spec § 0.7.1 W6-3 (HIGH severity):

    The schema version is prepended to the payload BEFORE hashing.
    This makes the fingerprint explicitly dependent on the version,
    so changing ``canonical_serialize`` semantics WITHOUT bumping
    ``TIEBREAK_FINGERPRINT_SCHEMA_VERSION`` produces detectably
    different fingerprints (which then cache-miss correctly via
    ``EnvironmentFingerprint``).

    Without this version anchor (v0.6 behaviour), a silent
    ``canonical_serialize`` change in any upstream component (e.g.,
    C7 changing float precision) would produce different fingerprints
    AT THE SAME ``c11b_version``, silently corrupting cache integrity.

    Args:
        refined_parameters: any ``canonical_serialize``-able structure
            (typically the ``RefinedParameters`` of a candidate).

    Returns:
        64-bit big-endian int.
    """
    versioned_payload = (
        f"{TIEBREAK_FINGERPRINT_SCHEMA_VERSION}|"
        + canonical_serialize(refined_parameters)
    ).encode("utf-8")
    digest = hashlib.sha256(versioned_payload).digest()
    return int.from_bytes(digest[:8], byteorder="big")


__all__ = [
    "_compute_tiebreak_fingerprint",
]
