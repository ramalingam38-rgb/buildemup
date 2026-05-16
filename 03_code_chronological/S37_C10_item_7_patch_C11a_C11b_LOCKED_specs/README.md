# S37 — C10 item-7 patch + C11a/C11b LOCKED specs

## What's here
- `wet_zone_planner_S37_patched.py` — full file with item-7 patch applied
- `test_c10_kb_validator_S37.py` — full test file with the 2 new tests

## What's NOT here
- C11a code (LOCKED in spec only; build pending — see CODING_MANDATE)
- C11b code (LOCKED in spec only; build pending — see CODING_MANDATE)

## The patch in detail

`_build_fixture_types_per_room` no longer falls back silently when a
profile row is missing. Raises `KBVersionMismatchError` with chained
`KeyError` preserving original lookup error. Inv 16 violations now
surface immediately rather than being masked.

Test count: 2312 → 2314 passed / 3 skipped.

See `01_master_doc/MASTER_DOC_v3_11_TO_v3_12_DELTA.md` for the full
session narrative.
