"""
BuildemUp — Component 10 — Wet-Zone Stack Planner — PACKAGE INIT (PROVISIONAL)

⚠️  This __init__.py is a PROVISIONAL OVERRIDE of the LOCKED c10/__init__.py
preserved at __init__.LOCKED.py.

REASON: The real C10 modules (wet_zone_planner.py, scoring.py, assignment.py,
occupancy.py) import from buildemup.components.c07.wall_segment, which is
missing from the S52 handoff bundle (lost between S36 and S52).

WHEN c07/wall_segment.py is restored to this tree:
  1. Delete this provisional __init__.py
  2. Rename __init__.LOCKED.py → __init__.py
  3. Re-run pytest to verify the full C10 LOCKED contract

Until then, c10/_c3b_shim.py provides the minimum contract surface for C3b.
"""
