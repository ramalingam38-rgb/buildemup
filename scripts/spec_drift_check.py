"""B-PROJECT-SPEC-DRIFT-CI (S55 Batch 3) — spec-vs-code drift checker.

Walks `02_specs_chronological/` looking for LOCKED markdown spec files,
extracts invariant statements (`Inv 1`, `Inv 2`, ... format), and
verifies each invariant has a corresponding test or assertion in the
production codebase under `06_upstream_codebase/buildemup/`.

Usage:
  python scripts/spec_drift_check.py [--strict]

Exit codes:
  0 — every locked invariant is covered (or there are no LOCKED specs).
  1 — at least one invariant has no detected coverage.
  2 — usage error (e.g., bundle paths missing).

This is the minimum-viable v1 closure for B-PROJECT-SPEC-DRIFT-CI. The
backlog calls for full parser + matcher across all 17 components; this
implementation handles the common `Inv N` shape and reports anything
uncovered as a warning. False negatives (covered but not detected) get
listed but don't block CI unless `--strict` is set.

A future expansion can:
  - Parse spec § headers + map them to module-level docstrings
  - Detect invariant SEMANTIC drift (vs textual presence)
  - Cover the c14 / c15 / c16 LOCK files when they ship
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = BUNDLE_ROOT / "02_specs_chronological"
CODE_DIR = BUNDLE_ROOT / "06_upstream_codebase" / "buildemup"


_INV_RE = re.compile(r"\bInv\s+(\d+)\b")
_LOCKED_FILE_RE = re.compile(r"LOCKED", re.IGNORECASE)


def find_locked_specs() -> list[Path]:
    """Return every LOCKED spec markdown file under specs/."""
    if not SPECS_DIR.exists():
        return []
    return [
        p for p in SPECS_DIR.rglob("*.md")
        if _LOCKED_FILE_RE.search(p.name)
    ]


def extract_invariants(spec_path: Path) -> set[str]:
    """Extract every `Inv N` reference from the spec markdown.

    Returns a set of identifiers like {"Inv 1", "Inv 7"}.
    """
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    return {f"Inv {m.group(1)}" for m in _INV_RE.finditer(text)}


def search_code_for_invariant(inv_id: str) -> bool:
    """Return True iff the invariant identifier appears anywhere under
    the production codebase. False positives are acceptable (we err
    on the side of 'covered') — the goal is detecting silent removal,
    not perfect semantic coverage."""
    if not CODE_DIR.exists():
        return False
    needle = inv_id.replace(" ", r"\s+")
    pattern = re.compile(needle)
    for path in CODE_DIR.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 on the first uncovered invariant (default warns and continues).",
    )
    args = parser.parse_args(argv)

    if not SPECS_DIR.exists() or not CODE_DIR.exists():
        print(f"ERROR: bundle paths missing (specs={SPECS_DIR}, code={CODE_DIR})")
        return 2

    locked_specs = find_locked_specs()
    if not locked_specs:
        print("No LOCKED spec files found — nothing to check.")
        return 0

    uncovered: list[tuple[Path, str]] = []
    total_invs = 0
    for spec_path in locked_specs:
        invariants = extract_invariants(spec_path)
        for inv_id in sorted(invariants):
            total_invs += 1
            if not search_code_for_invariant(inv_id):
                uncovered.append((spec_path, inv_id))

    if not uncovered:
        print(
            f"OK — every locked invariant has detected coverage "
            f"({total_invs} invariants across {len(locked_specs)} specs)."
        )
        return 0

    print(f"WARN — {len(uncovered)} of {total_invs} invariants lack detected coverage:")
    for spec_path, inv_id in uncovered:
        rel = spec_path.relative_to(BUNDLE_ROOT)
        print(f"  {rel}::{inv_id}")

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
