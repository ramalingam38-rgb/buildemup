"""S8 § 3.1 — Validation suite (Tier 1, in-process API tests).

Per BuildemUp C3a SPEC v1.2 LOCKED § 4: this directory hosts the
in-process integration tests that exercise the C3a state machine
through its HTTP surface. ~52 tests across 8 files (test_c3a_*.py).

Tier 1 budget per P37: ≤30s hard cap; ~27s steady-state target with
3s buffer (post-LOCK PL2 enforcement after 3 consecutive runs >25s).
"""
