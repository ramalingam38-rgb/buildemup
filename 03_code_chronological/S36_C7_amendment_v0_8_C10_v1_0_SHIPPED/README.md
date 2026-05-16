# S36 — C7 amendment v0.8 LOCKED + C10 v1.0 LOCKED + SHIPPED

S36 was the build session for C7 amendment v0.8 + C10 v1.0. The full
shipped codebase is in `06_upstream_codebase/buildemup/`.

S36-shipped files include:
- `utilities/__init__.py` and `utilities/canonical.py` — canonical_serialize utility
- `components/c07/wall_segment.py` — NEW (W1-W3 invariants, WallTag, WallAxis enums)
- `components/c07/grid_generator.py` — additive `wall_segments` field + canonical accessor + W8
- `components/c07/__init__.py` — re-exports
- `components/c10/` — full module set (errors, schema, provenance, kb_validator,
  scoring, occupancy, clustering, assignment, trap_arm, wet_zone_planner)
- `kb/plumbing_minimums.json` and `kb/plumbing_fixture_profiles.json`
- `tests/test_c7_wall_segment.py` (19 tests)
- `tests/_c10_fixtures.py`
- `tests/test_c10_schema.py` / `test_c10_kb_validator.py` /
  `test_c10_invariants.py` / `test_c10_phase_logic.py` /
  `test_c10_strict_mode.py` / `test_c10_replay.py`

Test count progression: 2155 (S35 close) → 2174 (after C7 amendment) → 2312 (after C10).

S37 then patched `wet_zone_planner.py` (item-7) and added tests in
`test_c10_kb_validator.py`, bringing the count to 2314.

See S37's separate dir for the patch.
