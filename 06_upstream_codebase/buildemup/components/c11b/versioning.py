"""
BuildemUp — Component 11b — versioning constants
==================================================

Per SPEC v1.1 LOCKED § 0.3.4 (SemVer rules) + § 0.7.1 (W6-3 tie-break
fingerprint schema version) + § 0.3.4 W6-8 (machine-readable policy
version).

THIS MODULE CENTRALIZES ALL THREE VERSION CONSTANTS so that the W6-1 /
W6-3 / W6-8 fixes are auditable at a glance. Ramalingam's S42 directive:
"versioning.py owning all three version constants together (C11B_VERSION,
TIEBREAK_FINGERPRINT_SCHEMA_VERSION, SEMVER_POLICY_VERSION) makes the
W6-1 / W6-3 / W6-8 fixes auditable at a glance."

Bump rules (spec § 0.3.4):
- Removing a public type / field / invariant → MAJOR (vN -> v(N+1).0)
- Adding an invariant / failure type / cache_relevant flip / changed
  default that affects output identity → MINOR (vN.M -> vN.(M+1))
- Telemetry-only / new enum value on non-cache field / prose-only
  wording → PATCH (vN.M.P -> vN.M.(P+1))
"""
from __future__ import annotations

from typing import Final


# =============================================================================
# § 0.3.4 — C11B_VERSION (the canonical component version string)
# =============================================================================

C11B_VERSION: Final[str] = "v1.1"
"""The LOCKED C11b version string. Per spec § 0.3.4:
- v1.0 LOCKED at S37 (SUPERSEDED — v0.4 PATCH-NOW F-v4-6 bumped to v1.1
  to reflect schema growth: capability flags, tiebreak_fingerprint,
  three new invariants 26-29, etc.)
- v1.1 LOCKED at S41 close per Ramalingam authority.

Captured into ``EnvironmentFingerprint.c11b_version`` so cache lookups
invalidate cleanly when this string changes. A v1.0 cache entry
deserializes-miss under v1.1 (no in-place migration; old entries are
GC'd by normal eviction)."""


# =============================================================================
# § 0.7.1 W6-3 — TIEBREAK_FINGERPRINT_SCHEMA_VERSION (HIGH-severity fix)
# =============================================================================

TIEBREAK_FINGERPRINT_SCHEMA_VERSION: Final[int] = 1
"""Version of the tie-break fingerprint derivation schema.

Per spec § 0.7.1 W6-3 (HIGH-severity Walk #6 fix):

THE BUG THIS GUARDS AGAINST:
``utilities/canonical.py`` currently holds only ``CANONICAL_FP_PRECISION
= 6`` and exposes no version constant. If a future amendment to C7 or
any other component changes ``CANONICAL_FP_PRECISION`` for a legitimate
reason, the contributor would NOT bump ``C11B_VERSION`` (because
C11b code didn't change). Every cached ``tiebreak_fingerprint`` would
silently drift — same key, different content — corrupting cache
integrity at the SAME ``c11b_version``. This is a stealth correctness
bug that prior Rule 11 passes did not catch.

THE FIX:
``_compute_tiebreak_fingerprint`` prepends this constant to the payload
BEFORE hashing. ``EnvironmentFingerprint`` captures this version. Cache
lookups include this field, so runs under version=1 cannot collide
with runs under version=2 even if everything else matches.

BUMP RULE (must be documented in commit message):
- Increment when ``canonical_serialize`` semantics change in a way
  that affects ``RefinedParameters`` serialization (float precision,
  field ordering, normalization).
- Increment when the derivation function in ``tiebreak.py`` changes
  (different hash, different byte count, different mixing).
- Do NOT increment for non-affecting changes elsewhere in the codebase.
"""


# =============================================================================
# § 0.3.4 W6-8 — SEMVER_POLICY_VERSION (replaces doc-presence meta-test)
# =============================================================================

SEMVER_POLICY_VERSION: Final[int] = 1
"""Version of the SemVer policy documented in spec § 0.3.4.

Per spec § 0.3.4 W6-8: replaces the v0.6 doc-presence meta-test
("SemVer table exists in § 0.3.4") with a constant-presence test.
The constant value IS the contract; the documentation prose is
documentation only — it can refactor without breaking CI.

BUMP RULE:
- Increment when the bump-criteria table itself changes meaning
  (e.g., adding a new column, redefining what counts as MAJOR vs MINOR).
- Do NOT increment for spec prose refactors that preserve the rules.
"""


__all__ = [
    "C11B_VERSION",
    "TIEBREAK_FINGERPRINT_SCHEMA_VERSION",
    "SEMVER_POLICY_VERSION",
]
