"""S8 § 3.1 — E2E suite (Tier 2, browser-driven).

Per BuildemUp C3a SPEC v1.2 LOCKED § 4: this directory hosts the
browser-driven Playwright tests + observability tests promoted from
validation per v1.2 P-1. ~26 tests across 8 files.

Tier 2 budget per P37: ≤75s hard cap.

All tests in this directory are tagged `@pytest.mark.e2e` so they
are NOT collected by default. Run with: `pytest -m e2e`.
"""
