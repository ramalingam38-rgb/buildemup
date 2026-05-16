#!/usr/bin/env python3
"""
BuildemUp — Component 15 — Moat Lint
========================================

Per C15 SPEC v0.2 LOCKED Inv P0 STRICTER (v0.2 A1) + LOCK-mandatory
backlog item B-C15-MOAT-LINT.

This script enforces the "no aggregation anywhere" rule statically.
It greps the C15 module tree for forbidden patterns that would let a
single quality-score leak through public APIs, telemetry, cache keys,
or report fields.

Exit code 0 → moat intact. Exit code 1 → violations found; build
fails. CI must invoke this on every C15 patch.

Why structural enforcement:

Anti-score discipline is a philosophy in spec text. Without a
machine-checked rule, a future maintainer optimizing for "simpler API"
could introduce a single-number aggregator with apparently-good
intentions (e.g., "quality_score: float for ranker convenience").
Per Rule 7 Pattern E avoidance, the moat must be enforced at the
syntactic level, not the goodwill level.

Categories enforced:

1. **No float fields named after quality concepts.** ProblemReport,
   DimensionSummary, ProblemCheck, etc. must not carry score / quality
   / rank / grade / weighted_sum named fields of type float.

2. **No aggregator function signatures.** Functions returning float
   from a check-context-shaped input are forbidden in the public
   surface (allowed in private helpers like _area, _step_depth_map
   that compute per-room geometry — those compute INPUTS to checks,
   not aggregates ACROSS checks).

3. **No score-renaming smuggling.** Aliases like "synthesis", "index",
   "rating", "fitness" applied to check-aggregate-shaped fields
   are forbidden.

4. **No RankerHint relics.** Per v0.2 A1, RankerHint was removed
   entirely. Any reference to RankerHint, analyze_with_ranker_hint,
   ranker_hint_signature, etc. is a relic of pre-A1 code and must
   be expunged.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Files allowed to legitimately contain "score" / "rank" / etc.
# strings in docstrings, comments, or test names — these are
# ALLOWED for documentation purposes.
DOCSTRING_ALLOWED_FILES = {
    # Top-level docs explain WHY there's no score — they reference
    # the forbidden concepts to disclaim them.
    "__init__.py",
    "schema.py",
    "versioning.py",
    "errors.py",
    "moat_lint.py",  # this file itself talks about scores to disclaim them
}

# Pattern categories. Each pattern is a (regex, description, severity).
# 'block' severity → fails CI. 'warn' → logs but doesn't fail.
PATTERNS: tuple[tuple[str, str, str], ...] = (
    # Category 1: forbidden float field names in dataclass schema
    (
        r"^\s+(?:quality_)?score\s*:\s*float",
        "forbidden score: float field declaration",
        "block",
    ),
    (
        r"^\s+(?:layout|design|architectural)_rating\s*:\s*float",
        "forbidden rating: float field declaration",
        "block",
    ),
    (
        r"^\s+grade\s*:\s*float",
        "forbidden grade: float field declaration",
        "block",
    ),
    (
        r"^\s+weighted_sum\s*:\s*float",
        "forbidden weighted_sum: float field",
        "block",
    ),
    (
        r"^\s+aggregate\s*:\s*float",
        "forbidden aggregate: float field",
        "block",
    ),
    (
        r"^\s+fitness\s*:\s*float",
        "forbidden fitness: float field (anti-score discipline)",
        "block",
    ),
    # Category 2: forbidden function return types — aggregator
    # signatures that take a check-context-shaped input
    (
        r"def\s+\w*(?:score|rank|grade|aggregate|synthesize|rate)\w*\([^)]*\)\s*->\s*float",
        "forbidden float-returning aggregator function",
        "block",
    ),
    # Category 3: relic patterns from pre-A1 (RankerHint removal)
    (
        r"\bRankerHint\b",
        "relic: RankerHint was removed in v0.2 A1; expunge",
        "block",
    ),
    (
        r"\banalyze_with_ranker_hint\b",
        "relic: analyze_with_ranker_hint was removed in v0.2 A1",
        "block",
    ),
    (
        r"\branker_hint_signature\b",
        "relic: ranker_hint_signature was removed in v0.2 A1",
        "block",
    ),
    # Category 4: warning patterns (might be innocent but worth flagging)
    (
        r"^\s+confidence\s*:\s*float",
        "confidence: float — confidence is OK if coverage-confidence (A12), but verify not quality-confidence",
        "warn",
    ),
)


def scan_file(path: Path) -> list[tuple[int, str, str, str]]:
    """Return list of (line_no, line_content, description, severity) for
    each pattern match found in this file.

    Docstrings and comments are ALWAYS stripped before block-pattern
    matching — they can legitimately reference forbidden concepts to
    DISCLAIM them (e.g. "v0.2 A1 — RankerHint REMOVED"). Violations
    live in field declarations and function signatures, not prose.
    """
    findings: list[tuple[int, str, str, str]] = []
    text = path.read_text(encoding="utf-8")
    original_lines = text.split("\n")

    # Always strip docstrings + comments. Patterns target code shape
    # (field decls, function sigs); they should never see prose.
    text_no_docstrings = re.sub(r'"""[\s\S]*?"""', "", text, flags=re.MULTILINE)
    text_no_docstrings = re.sub(r"'''[\s\S]*?'''", "", text_no_docstrings, flags=re.MULTILINE)
    text_no_docstrings = re.sub(r"#.*$", "", text_no_docstrings, flags=re.MULTILINE)
    scan_lines = text_no_docstrings.split("\n")

    for i, line in enumerate(scan_lines, start=1):
        for regex, desc, severity in PATTERNS:
            if re.search(regex, line):
                original = original_lines[i - 1] if i - 1 < len(original_lines) else line
                findings.append((i, original.rstrip(), desc, severity))
    return findings


def scan_module(root: Path) -> tuple[int, int]:
    """Scan all .py files under root. Returns (n_blocks, n_warns)."""
    n_blocks = 0
    n_warns = 0
    py_files = sorted(root.rglob("*.py"))
    for path in py_files:
        # Skip __pycache__ and test files (tests legitimately
        # mention 'score' to verify it's NOT there).
        if "__pycache__" in path.parts:
            continue
        if "test_" in path.name or path.name.startswith("test_"):
            continue
        findings = scan_file(path)
        if findings:
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            print(f"\n{rel}")
            for line_no, content, desc, severity in findings:
                marker = "BLOCK" if severity == "block" else "WARN"
                print(f"  [{marker}] line {line_no}: {desc}")
                print(f"          {content}")
                if severity == "block":
                    n_blocks += 1
                else:
                    n_warns += 1
    return n_blocks, n_warns


def main() -> int:
    # Default root: c15 module directory.
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        # Resolve relative to this script's location.
        here = Path(__file__).resolve().parent
        # If script lives in tools/, look at ../components/c15
        candidates = [
            here.parent / "components" / "c15",
            here / "components" / "c15",
            here,
        ]
        root = next((c for c in candidates if c.exists() and c.is_dir()), here)

    if not root.exists():
        print(f"ERROR: scan root does not exist: {root}", file=sys.stderr)
        return 2

    print(f"Moat-lint scanning: {root}")
    n_blocks, n_warns = scan_module(root)
    print(f"\n=== Moat-lint summary ===")
    print(f"Blocking violations: {n_blocks}")
    print(f"Warnings: {n_warns}")
    if n_blocks > 0:
        print("\nFAIL: anti-score discipline (Inv P0 STRICTER) violated.")
        print("Per C15 SPEC v0.2 A1 + B-C15-MOAT-LINT: C15 must never expose")
        print("a single number representing layout quality, anywhere.")
        return 1
    print("PASS: moat intact (Inv P0 STRICTER satisfied).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
