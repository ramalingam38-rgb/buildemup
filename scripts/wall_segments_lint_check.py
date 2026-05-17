"""B-241 (S56) — CI lint: forbid direct `.wall_segments` iteration.

Production code MUST go through `Grid.wall_segments_canonical()` per the
C7 W8 invariant (see `02_specs_chronological/60_C7_AMENDMENT_v0_8_LOCKED.md`
§ 3 W8). Iterating `Grid.wall_segments` directly preserves storage order
rather than canonical (axis, lex) order, so different code paths can
disagree on iteration sequence and produce non-reproducible outputs.

This script walks production Python files under
`06_upstream_codebase/buildemup/` and flags any direct `.wall_segments`
access (i.e., not `wall_segments_canonical`, not `wall_segments_used`,
not a string-keyed dictionary access).

Allowed direct-access sites (allowlisted, since they DEFINE the canonical
form rather than consume it):

  - components/c07/grid_generator.py — defines wall_segments_canonical()
  - components/c07/wall_segment.py    — defines the schema
  - utilities/canonical.py            — implements canonicalisation
  - tests/                            — snapshot + replay tests
  - tests/test_c7_wall_segment.py     — direct-iteration tests

Usage:
  python scripts/wall_segments_lint_check.py [--strict]

Exit codes:
  0 — no forbidden access detected, or all sites are allowlisted
  1 — at least one disallowed direct-access site found and --strict set
  2 — bundle root not found
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = BUNDLE_ROOT / "06_upstream_codebase" / "buildemup"

# Match `.wall_segments` NOT followed by an alphanumeric-or-underscore
# (which would make it part of a longer identifier like
# `wall_segments_canonical` or `wall_segments_used`).
_DIRECT_ACCESS_RE = re.compile(r"\.wall_segments\b(?!_)")

# Sites that DEFINE the canonical form — direct access is the point.
_ALLOWLIST_RELATIVE_PATHS = {
    "components/c07/grid_generator.py",
    "components/c07/wall_segment.py",
    "utilities/canonical.py",
}

# Directories whose direct access is allowed wholesale.
_ALLOWLIST_DIRS = (
    "tests/",
)


def _is_allowlisted(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/")
    if norm in _ALLOWLIST_RELATIVE_PATHS:
        return True
    for prefix in _ALLOWLIST_DIRS:
        if norm.startswith(prefix):
            return True
    return False


def _strip_strings_and_comments(text: str) -> str:
    """Return source text with string literals and comments blanked out.

    Triple-quoted strings (docstrings) and single/double-quoted strings
    are replaced with spaces so their content does not match the lint
    regex. Line endings preserved so line numbers still align.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        # Triple-quoted string
        if text[i:i + 3] in ('"""', "'''"):
            quote = text[i:i + 3]
            out.append("   ")  # placeholder for the open quote
            i += 3
            while i < n and text[i:i + 3] != quote:
                # preserve newlines so line numbers don't shift
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            # closing quote
            if i < n:
                out.append("   ")
                i += 3
            continue
        # Single-line string
        if ch in ('"', "'"):
            quote = ch
            out.append(" ")
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            if i < n:
                out.append(" ")
                i += 1
            continue
        # Line comment
        if ch == "#":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def scan() -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    if not CODE_DIR.is_dir():
        print(f"ERROR: bundle code dir not found at {CODE_DIR}",
              file=sys.stderr)
        sys.exit(2)
    for path in CODE_DIR.rglob("*.py"):
        rel = path.relative_to(CODE_DIR).as_posix()
        if _is_allowlisted(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        scrubbed = _strip_strings_and_comments(text)
        orig_lines = text.splitlines()
        for lineno, scrub_line in enumerate(scrubbed.splitlines(), start=1):
            if _DIRECT_ACCESS_RE.search(scrub_line):
                orig = orig_lines[lineno - 1] if lineno - 1 < len(orig_lines) \
                    else scrub_line
                findings.append((rel, lineno, orig.strip()))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any finding present (CI mode)")
    args = parser.parse_args()

    # Windows consoles can default to cp1252; force UTF-8 on stdout/stderr
    # so non-ASCII characters in a flagged line don't crash the report.
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is not None:
            try:
                reconf(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    findings = scan()

    if not findings:
        print("wall_segments_lint_check: PASS — no forbidden direct"
              " `.wall_segments` access in production code paths.")
        return 0

    print(f"wall_segments_lint_check: {len(findings)} finding(s):")
    for rel, lineno, line in findings:
        print(f"  {rel}:{lineno}: {line}")
    print()
    print("Fix: replace `<grid>.wall_segments` with"
          " `<grid>.wall_segments_canonical()` per C7 W8 invariant"
          " (02_specs_chronological/60_C7_AMENDMENT_v0_8_LOCKED.md § 3).")
    print("If the call site genuinely needs storage order rather than"
          " canonical order, allowlist it explicitly in"
          " scripts/wall_segments_lint_check.py.")

    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
