"""
BuildemUp — Master Orchestration package (S56 MVP)
===================================================

Single-call pipeline that chains all 17 architectural components into one
flow:

  C1 brief → C2 feasibility → [C3a/C3b skipped in MVP — see follow-ups]
  → C4 plot analysis → C5 topology → C6 orientation → C7 structural grid
  → C8 corridor → C9 room sizer → C10 wet zones → C11a topology mutation
  → C11b NSGA refinement → C12 vertical placement → C13 doors
  → C14 connection graph → C15 problem finder → C16 dual drawings
  → C17 quote comparison (separate user-uploads-quote flow)

This is the **MVP master orchestrator** shipped in S56. Each pipeline
phase produces a structured PhaseResult so a downstream failure does
NOT lose upstream output. Some downstream phases (C16, C17) ship with
STUB-quality output because their upstream bundle assembly is non-trivial;
follow-up work is tracked in
`04_backlog/S57_MASTER_ORCHESTRATOR_FOLLOWUPS.md`.

Public surface:
    - MasterOrchestrator        — main class with .run(brief) method
    - MasterOrchestratorResult  — unified result dataclass
    - PhaseResult / PhaseStatus — per-phase result dataclass + enum
    - PIPELINE_PHASES           — canonical list of phase identifiers
"""
from __future__ import annotations

from buildemup.orchestration.phase_result import (
    PhaseResult,
    PhaseStatus,
    PIPELINE_PHASES,
)
from buildemup.orchestration.master_orchestrator import (
    MasterOrchestrator,
    MasterOrchestratorResult,
    MasterOrchestratorConfig,
)
from buildemup.orchestration.phase_payloads import serialize_phase_payload


__all__ = [
    "MasterOrchestrator",
    "MasterOrchestratorResult",
    "MasterOrchestratorConfig",
    "PhaseResult",
    "PhaseStatus",
    "PIPELINE_PHASES",
    "serialize_phase_payload",
]
