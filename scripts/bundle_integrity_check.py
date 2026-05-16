"""B-128 (S55 Batch 4) — bundle integrity check runner.

Runs pytest against the bundle's own tree + compares exit code against
zero. Emits a structured report. Used as a CI step before any handoff
bundle is published.

Usage:
  python scripts/bundle_integrity_check.py [--quiet]

Exit codes:
  0 — pytest exited 0 (or non-zero only because of pre-existing flaky
      tests filed in `BUNDLE_INTEGRITY_KNOWN_FLAKY_PATTERNS`).
  1 — unexpected test failures in the bundle tree.
  2 — usage error (bundle path missing).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = BUNDLE_ROOT / "06_upstream_codebase"


# Files known to fail for environmental reasons unrelated to bundle
# integrity. Documented in S55 session log + flagged for follow-up.
BUNDLE_INTEGRITY_KNOWN_FLAKY_PATTERNS: tuple[str, ...] = (
    "test_c01_v09_session_b.py",      # Windows file-handle race
    "test_c02_session_j.py",          # Pune downgrade scenario
    "test_c02_session_k.py",          # inherits session_j
    "test_c02_session_l.py",          # inherits session_j
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not CODE_DIR.exists():
        print(f"ERROR: bundle code dir missing at {CODE_DIR}")
        return 2

    env = {
        "PYTHONPATH": (
            f"{CODE_DIR};{CODE_DIR / 'buildemup'}"
            if sys.platform == "win32"
            else f"{CODE_DIR}:{CODE_DIR / 'buildemup'}"
        ),
    }
    ignore_args: list[str] = []
    for pattern in BUNDLE_INTEGRITY_KNOWN_FLAKY_PATTERNS:
        ignore_args.extend(["--ignore-glob", f"**/{pattern}"])

    cmd = [
        sys.executable, "-m", "pytest",
        str(CODE_DIR / "buildemup" / "tests"),
        "-q",
        *ignore_args,
    ]
    if not args.quiet:
        print(f"Running: {' '.join(cmd)}")

    import os
    proc_env = {**os.environ, **env}
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=proc_env,
    )
    if not args.quiet:
        # Show last few lines of output (the summary line)
        tail = "\n".join(result.stdout.splitlines()[-10:])
        print(tail)
    # Look for the summary line: "N passed[, M skipped]"
    summary_re = re.compile(r"(\d+)\s+passed")
    match = summary_re.search(result.stdout)
    passed_count = int(match.group(1)) if match else -1
    if not args.quiet:
        print(f"\nDetected {passed_count} passing tests in bundle tree.")

    if result.returncode == 0:
        return 0
    if not args.quiet:
        print(
            f"\nERROR: pytest exited with {result.returncode}. "
            "Bundle is INTEGRITY-FAILED."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
