"""
BuildemUp — Component 11b — environment fingerprint
=====================================================

Per SPEC v1.1 LOCKED § 0.3 (carried v1.0) + § 0.7.1 W6-3 addition.

Captures the run-time tuple that determines TIER-1 byte-equal replay
equivalence (Inv 29):

- ``numpy_version``: changes → no byte-equality across NumPy versions
- ``python_version``: same logic for Python builtin RNG state
- ``platform_machine`` / ``platform_system``: CPU/OS-dependent FP
- ``c11b_version``: changes invalidate cache cleanly (§ 0.3.3)
- ``numpy_blas_info_summary``: BLAS variant affects vector ops
- ``master_seed``: NEW v0.4 D-PR-1; replay-tier tests detect changes
- ``tiebreak_fingerprint_schema_version``: NEW v0.7 W6-3 (HIGH-severity
  fix) — closes the silent-drift hole at the same c11b_version

``fingerprint_hash`` is a SHA256 over the canonical-serialized tuple
used as the cache key root.
"""
from __future__ import annotations

import hashlib
import platform
import sys
from dataclasses import dataclass

import numpy as np

from buildemup.components.c11b.versioning import (
    C11B_VERSION,
    TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
)
from buildemup.utilities.canonical import canonical_serialize


def _capture_blas_summary() -> str:
    """Best-effort BLAS summary. NumPy's API for this has churned;
    fall back to "unknown" if anything raises."""
    try:
        cfg = np.show_config(mode="dicts")
        if not isinstance(cfg, dict):
            return "unknown"
        build_deps = cfg.get("Build Dependencies", {}) or {}
        blas = build_deps.get("blas", {}) or {}
        return str(blas.get("name", "unknown"))
    except Exception:
        return "unknown"


@dataclass(frozen=True)
class EnvironmentFingerprint:
    """Carries the env tuple used for TIER-1 replay equivalence."""
    numpy_version: str
    python_version: str
    platform_machine: str
    platform_system: str
    c11b_version: str
    numpy_blas_info_summary: str
    master_seed: int  # NEW v0.4 D-PR-1
    tiebreak_fingerprint_schema_version: int  # NEW v0.7 W6-3
    fingerprint_hash: str

    def matches(self, other: "EnvironmentFingerprint") -> bool:
        """Strict equality on every captured field (excluding the
        derived ``fingerprint_hash`` which is a function of the
        others)."""
        return (
            self.numpy_version == other.numpy_version
            and self.python_version == other.python_version
            and self.platform_machine == other.platform_machine
            and self.platform_system == other.platform_system
            and self.c11b_version == other.c11b_version
            and self.numpy_blas_info_summary == other.numpy_blas_info_summary
            and self.master_seed == other.master_seed
            and self.tiebreak_fingerprint_schema_version
            == other.tiebreak_fingerprint_schema_version
        )


def capture_environment_fingerprint(*, master_seed: int) -> EnvironmentFingerprint:
    """Phase 0 helper — captures the env tuple at run start.

    The ``master_seed`` argument is required because it's part of the
    cache-key contract (NEW v0.4 D-PR-1). Callers pass
    ``config.master_seed``.
    """
    numpy_version = np.__version__
    python_version = sys.version.split()[0]
    machine = platform.machine() or "unknown"
    system = platform.system() or "unknown"
    blas = _capture_blas_summary()

    payload_dict = {
        "numpy_version": numpy_version,
        "python_version": python_version,
        "platform_machine": machine,
        "platform_system": system,
        "c11b_version": C11B_VERSION,
        "numpy_blas_info_summary": blas,
        "master_seed": master_seed,
        "tiebreak_fingerprint_schema_version": TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
    }
    canon = canonical_serialize(payload_dict)
    fph = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    return EnvironmentFingerprint(
        numpy_version=numpy_version,
        python_version=python_version,
        platform_machine=machine,
        platform_system=system,
        c11b_version=C11B_VERSION,
        numpy_blas_info_summary=blas,
        master_seed=master_seed,
        tiebreak_fingerprint_schema_version=TIEBREAK_FINGERPRINT_SCHEMA_VERSION,
        fingerprint_hash=fph,
    )


__all__ = [
    "EnvironmentFingerprint",
    "capture_environment_fingerprint",
]
