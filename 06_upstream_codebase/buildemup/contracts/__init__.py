"""
BuildemUp† — Downstream Consumer Contracts
============================================

Stub interfaces for v0.4. These are the data shapes that other parts
of the BuildEase platform will consume:

  - Contractor marketplace (Phase 1, month 5-6 per vision doc)
  - Material supplier ordering (Phase 1, month 5-6)
  - Bank loan applications (Phase 2 partnership)
  - Government permit/approval data (Phase 2 PMAY integration)
  - User project tracking dashboard (Phase 1)

Each contract is a Protocol describing what consumers expect to receive,
not an implementation. v0.4 ships the interfaces only; real adapters
come later when the marketplace/supplier/bank integrations launch.

Why stubs now: defining the contract shapes early prevents Component 7
(and future components) from accidentally producing outputs that can't
be consumed by Phase 2 integrations. Catches design bugs before they
cost a refactor.

†= placeholder name marker.
"""
