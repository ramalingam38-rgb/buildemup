"""S55 Batch 4 — C6 trust-gap closures (B-127 + B-128).

B-127 — C6 production test reconstruction
==========================================
S31 build authored 186 C6 tests across 6 files; they did NOT survive
into the v8 bundle handoff. C6's public-API contract has been trusted
since via downstream consumers (C8 SHIP confirmed `prioritize_orientation`
+ `OrientedCandidate` + `OrientationPriority` work in production). But
the test-evidence gap remains — future critique walks against C6 lack
reproducible test fixtures.

This module ships:
  - C6_TEST_PLAN_MANIFEST: the 186 expected test names by file, sourced
    from C6 SPEC v0.7 § 7 test-plan.
  - C6_TEST_RECONSTRUCTION_STATUS: per-file landing status. v1.0 LOCK
    target = full reconstruction. S55 ships the manifest only.

B-128 — Bundle integrity check
==============================
Future bundles MUST executably verify the claimed test count actually
reproduces in the bundle's own tree. `bundle_integrity_protocol()`
documents the canonical check; `scripts/bundle_integrity_check.py` runs
it via subprocess.

The lesson — never trust a stated count without re-execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Tuple


# ─────────────────────────────────────────────────────────────────────
# B-127 — C6 test plan manifest
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class C6TestFileManifest:
    file_name: str
    expected_test_count: int
    coverage_area: str


C6_TEST_PLAN_MANIFEST: Final[Tuple[C6TestFileManifest, ...]] = (
    C6TestFileManifest(
        file_name="test_c6_failure_modes.py",
        expected_test_count=22,
        coverage_area="explicit raise paths + WARN-mode degradations",
    ),
    C6TestFileManifest(
        file_name="test_c6_schema.py",
        expected_test_count=35,
        coverage_area="OrientedCandidate + OrientationPriority dataclass invariants",
    ),
    C6TestFileManifest(
        file_name="test_c6_vastu_kb.py",
        expected_test_count=28,
        coverage_area="VastuTier table coverage + PARTIAL vs FULL behavior split",
    ),
    C6TestFileManifest(
        file_name="test_c6_signals.py",
        expected_test_count=24,
        coverage_area="wind / solar / acoustic signal classification",
    ),
    C6TestFileManifest(
        file_name="test_c6_optimizer.py",
        expected_test_count=42,
        coverage_area="orientation optimizer search + determinism + signature stability",
    ),
    C6TestFileManifest(
        file_name="test_c6_select.py",
        expected_test_count=35,
        coverage_area="selection-tier pruning + canonical lex-ASC tiebreak",
    ),
)


def c6_expected_test_count_total() -> int:
    """Total expected C6 production-test count per SPEC v0.7 § 7."""
    return sum(m.expected_test_count for m in C6_TEST_PLAN_MANIFEST)


@dataclass(frozen=True)
class C6TestReconstructionStatus:
    file_name: str
    status: str        # 'MANIFESTED' | 'PARTIAL' | 'COMPLETE'
    notes: str


C6_TEST_RECONSTRUCTION_STATUS: Final[Tuple[C6TestReconstructionStatus, ...]] = tuple(
    C6TestReconstructionStatus(
        file_name=m.file_name,
        status="MANIFESTED",
        notes=(
            f"S55 baseline — manifest pinned ({m.expected_test_count} tests "
            f"covering {m.coverage_area}). Body reconstruction is a follow-up "
            "build session per B-127."
        ),
    )
    for m in C6_TEST_PLAN_MANIFEST
)


# ─────────────────────────────────────────────────────────────────────
# B-128 — Bundle integrity check protocol
# ─────────────────────────────────────────────────────────────────────

BUNDLE_INTEGRITY_PROTOCOL: Final[str] = """\
B-128 Bundle Integrity Check Protocol (S55 baseline)

1. Clone the bundle's `06_upstream_codebase/` into an isolated working
   directory. Use a fresh venv to avoid host-side state leaks.

2. Set PYTHONPATH to include both `06_upstream_codebase/` and
   `06_upstream_codebase/buildemup/` (the c03b tests import
   `tests.test_c03b.fixtures.*`).

3. Run `python -m pytest 06_upstream_codebase/buildemup/tests -q` and
   record the exit code + final summary line.

4. Compare against the bundle's CLAIMED test count (from
   `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` or the most recent
   `S*_SESSION_LOG.md`). If counts diverge by more than 5 tests OR the
   exit code is non-zero, the bundle is INTEGRITY-FAILED — do NOT
   ship.

5. Any SHIPPED component whose production code is not in the upstream
   snapshot is an SHIP-claim violation; reject the bundle.

6. Adopt this as Rule 10.6 INTEGRITY CHECK protocol — mandatory before
   every handoff bundle.
"""


__all__ = [
    "C6TestFileManifest",
    "C6_TEST_PLAN_MANIFEST",
    "c6_expected_test_count_total",
    "C6TestReconstructionStatus",
    "C6_TEST_RECONSTRUCTION_STATUS",
    "BUNDLE_INTEGRITY_PROTOCOL",
]
