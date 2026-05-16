"""
B-004 — circulation factor alignment between C1, C2, C3a.

Pre-fix: C2 used 1.35, C3a used 1.30. C1 + KB use 1.35 typical.
Fix: align C3a to 1.35 so all three components use the same default.
"""
from __future__ import annotations


def test_c2_and_c3a_use_same_circulation_factor():
    """C2's hard_physics_checks.CIRCULATION_FACTOR and C3a's
    detector.CIRCULATION_FACTOR must match.
    """
    from buildemup.components.c02.hard_physics_checks import (
        CIRCULATION_FACTOR as C2_FACTOR,
    )
    from buildemup.components.c03a.detector import (
        CIRCULATION_FACTOR as C3A_FACTOR,
    )
    assert C2_FACTOR == C3A_FACTOR, (
        f"C2 ({C2_FACTOR}) and C3a ({C3A_FACTOR}) circulation factors "
        f"diverged. Per B-004, these must match (1.35 typical)."
    )


def test_circulation_factor_matches_kb_typical():
    """The hardcoded constants should match the KB-declared typical value."""
    import json
    from pathlib import Path
    from buildemup.components.c02.hard_physics_checks import CIRCULATION_FACTOR

    kb_path = (
        Path(__file__).parent.parent / "kb_rules" / "room_minimums.json"
    )
    kb = json.loads(kb_path.read_text(encoding="utf-8"))
    kb_typical = kb["circulation_factor"]["value"]
    assert CIRCULATION_FACTOR == kb_typical, (
        f"Hardcoded CIRCULATION_FACTOR ({CIRCULATION_FACTOR}) drifted from "
        f"KB typical ({kb_typical}). Update one or the other."
    )
