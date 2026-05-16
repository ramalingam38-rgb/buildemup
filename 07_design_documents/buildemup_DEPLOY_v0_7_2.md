# BuildemUp Component 7 v0.7.2 — Deployment Notes

## Fresh deploy to Railway

1. Push `buildemup/` to your GitHub repo (`ramalingam38/buildease`)
2. In Railway: connect the repo (or let it auto-detect from existing config)
3. Railway auto-detects Python via `main.py` / `requirements.txt` /
   existing `Procfile`. If you have a startup script already, keep it.
4. The insights buffer is in-memory — NO volume mount needed for v0.7.2.
   Buffer resets on each deployment (this is intentional; patterns
   rebuild within 10 executions).
5. After deploy, verify: hit the URL, submit a test plan, check the
   output includes sections:
   - VALIDATION STATUS
   - ENGINEERING DEPTH (Level 2 — Frame-checked)
   - FRAME SANITY CHECK
   - GLOBAL STABILITY / DRIFT CHECK
   - TOP RECOMMENDATIONS
   - LEGAL & STATUTORY DISCLOSURES

After ~10 plans, outputs will also include:
   - PROACTIVE GUIDANCE (patterns from recent plans)

## Running locally in VS Code

Prerequisites: Python 3.10+ (tested on 3.12).

```bash
# From the repo root
cd buildemup

# Run the full test suite to verify everything works
for t in tests/test_*.py; do python "$t"; done

# Run a single example
python examples/run_c07_on_ne_30x40.py
```

Recommended VS Code extensions:
- Python (Microsoft)
- Pylance
- Python Test Explorer

## Environment variables

None required for v0.7.2. All KB values come from `kb_rules/*.json`
shipped with the code.

## Health check endpoint

If using a web framework, expose a `/healthz` that imports the engine
and runs a minimal test:

```python
from buildemup.components.c07_structural_grid import (
    StructuralGridEngine, StructuralGridInput
)

def healthz():
    try:
        StructuralGridEngine().execute(StructuralGridInput(
            envelope_width_m=8, envelope_depth_m=10, floors_above_ground=1,
        ))
        return "ok"
    except Exception as e:
        return f"error: {e}", 500
```

## Known v1 limitations (documented, not bugs)

- In-memory insights buffer resets on deploy restart
- 3 of 5 KB modules still in Python (soil / RCC / material rates queued
  for v0.8 migration)
- Frame sanity + drift share assumptions today but no explicit
  consistency assertion — queued for v0.8 lightweight check
- Component 1 (Brief Capture) not yet built — manual inputs via
  StructuralGridInput until Component 1 ships

## Support

Trace IDs appear in every output. If a user reports an issue,
ask for the trace ID — it points to the structured log entry.
