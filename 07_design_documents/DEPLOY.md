# BuildemUp v0.8 — Deployment Notes

Covers **Component 7 v0.7.2** (stable) + **Component 1 v0.1** (new this release).

## Fresh deploy to Railway

1. Push `buildemup/` to your GitHub repo (`ramalingam38/buildease`)
2. In Railway: connect the repo (or let it auto-detect from existing config)
3. Railway auto-detects Python via `main.py` / `requirements.txt`.
   No framework needed — Component 1 ships with a stdlib HTTP server.
4. Set the start command to:
   ```
   python -m buildemup.api.server
   ```
   This serves both the form UI and the API. Railway sets `PORT` env
   var automatically; the server reads it.
5. After deploy, verify:
   - Open the Railway URL in a browser — you should see the BuildemUp
     form at `/brief_form.html` (root `/` redirects there)
   - Fill in a test brief (defaults are reasonable) and submit
   - Output panel should show: top-3 recommendations, plot summary,
     compliance status, C7 cost, toggle for full report

## Running locally in VS Code

Prerequisites: Python 3.10+ (tested on 3.12). Zero pip dependencies.

```bash
# From the repo root
cd buildemup

# Run the full test suite to verify everything works
for t in tests/test_*.py; do python "$t"; done

# Start the server locally
python -m buildemup.api.server
# → visit http://localhost:8000/brief_form.html

# Or run a single Component 7 example directly
python examples/run_c07_on_ne_30x40.py
```

Recommended VS Code extensions:
- Python (Microsoft)
- Pylance
- Python Test Explorer

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | HTTP server port (Railway sets automatically) |
| `BUILDEMUP_HTTP_VERBOSE` | unset | Set to any value to enable stdlib http.server's request log |
| `BUILDEMUP_DB_PATH` | `/tmp/buildemup_briefs.db` | SQLite path for save/resume (v0.9 Session B) |
| `BUILDEMUP_BRIEF_TTL_DAYS` | `30` | Days before a saved brief expires (v0.9 Session B) |

No external services required (no Redis, no Postgres) — SQLite is
stdlib. **Caveat for Railway free/hobby tier**: `/tmp` is ephemeral
filesystem, so saved briefs get lost on container restart. The save
endpoint surfaces an `ephemeral_storage_warning` field for the user.
For production-grade durability, mount a persistent volume and point
`BUILDEMUP_DB_PATH` at it, OR swap to Postgres in v1.0.

## Routes exposed by the Component 1 HTTP server

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | 302 redirect to `/brief_form.html` |
| GET | `/brief_form.html` | Static form UI |
| GET | `/brief_form.js` | Form JavaScript |
| GET | `/brief_form.css` | Form styles |
| GET | `/api/vastu/partial-items` | JSON: 7 partial vastu items |
| POST | `/api/brief/capture` | JSON in, JSON out — runs the engine |
| POST | `/api/brief/save` | **v0.9** — Persist in-progress form, returns resume URL |
| GET | `/api/brief/resume?token=X` | **v0.9** — Fetch saved form by token |

CORS `Access-Control-Allow-Origin: *` is set on every response so the
form works if hosted separately from the API.

### POST /api/brief/save — request and response (v0.9)

Request body: arbitrary JSON dict (the in-progress form state). To
update an existing saved brief in place (so the resume URL stays the
same), include `existing_token` in the body alongside the form data.

```json
{ "plot_width_m": 12.0, "city": "chennai", "current_step": 2,
  "existing_token": "ff0f8450f5df108a6aba1eab" }
```

Response:
```json
{
  "ok": true,
  "token": "ff0f8450f5df108a6aba1eab",
  "resume_url": "https://your-host/?resume=ff0f8450f5df108a6aba1eab",
  "expires_at_utc": "2026-05-25T02:45:27.194894Z",
  "ephemeral_storage_warning": "On hobby/free tiers..."
}
```

### GET /api/brief/resume?token=X — response (v0.9)

```json
{
  "ok": true,
  "token": "ff0f8450f5df108a6aba1eab",
  "payload": { "plot_width_m": 12.0, "city": "chennai", "current_step": 2 }
}
```

404 if token missing/invalid/expired. 400 if token format is wrong.

### POST /api/brief/capture — request shape

```json
{
  "plot_width_m": 12.0,
  "plot_depth_m": 15.0,
  "plot_facing": "N",
  "city": "chennai",
  "road_width_m": 9.0,
  "plot_type": "detached",
  "corner_plot": false,
  "user_setback_front_m": 1.5,
  "user_setback_rear_m": 1.5,
  "user_setback_side_left_m": 1.5,
  "user_setback_side_right_m": 1.5,
  "floors": [
    {
      "floor_number": 0,
      "floor_use": "residential",
      "rooms": [
        {"room_type": "living", "count": 1},
        {"room_type": "kitchen", "count": 1}
      ]
    },
    {
      "floor_number": 1,
      "floor_use": "residential",
      "rooms": [
        {"room_type": "bedroom_master", "count": 1},
        {"room_type": "bathroom_attached", "count": 1}
      ]
    }
  ],
  "budget_min_lakhs": 20,
  "budget_max_lakhs": 30,
  "vastu_preference": "partial"
}
```

### POST /api/brief/capture — response shape

```json
{
  "ok": true,
  "trace_id": "2a1cb0d93e42",
  "rendered_explain": "═══ YOUR BRIEF — captured for Chennai ═══ ...",
  "ready_for_downstream": true,
  "risk_level": "LOW",
  "risk_drivers": ["No critical or moderate concerns found"],
  "roadmap_position": {
    "current_step": 1,
    "current_name": "Brief Capture",
    "total_steps": 6,
    "steps_ahead": [
      {"n": 2, "name": "Feasibility check"},
      {"n": 3, "name": "Layout generation"},
      {"n": 4, "name": "Structural design"},
      {"n": 5, "name": "MEP & finishes"},
      {"n": 6, "name": "Procurement & contractor selection"}
    ],
    "disclaimer": "This is step 1 of 6 — directional planning input only..."
  },
  "top_guidance": [...],
  "soft_guidance_by_category": {
    "Compliance": [...],
    "Budget": [...],
    "Vastu (cultural)": [...]
  },
  "brief_summary": {
    "city": "chennai",
    ...
    "net_usable_low_sqm": 86.4,
    "net_usable_high_sqm": 97.2,
    ...
  },
  "all_in_cost_estimate_lakhs": {
    "low": 6.4,
    "typical": 8.7,
    "high": 11.3,
    "structural_share_typical": 0.40,
    "breakdown_pct": {
      "structure": 40,
      "finishing": 25,
      "mep": 15,
      "interior": 12,
      "miscellaneous": 8
    },
    "source": "Industry typical breakdown (AECORD 2026 + NBC industry guides)...",
    "disclaimer": "Do not treat as a quote — directional planning estimate."
  }
}
```

**v0.9.2 new fields (UX text patch):**
- `risk_label_with_context` (top-level) — `"LOW (minor issues, plan looks sound)"` etc. Plain-language tail prevents users reading bare "LOW" as "safe"
- `biggest_issue` (top-level) — single-string elevation of the most critical risk driver (string for MEDIUM/HIGH, `null` for LOW)
- `roadmap_position.next_step_cta` (added inside existing roadmap_position) — explicit next-component CTA
- `scope_caveat` (top-level) — "This output does NOT replace architect-led layout, structural drawings, or municipal plan approval"
- `powered_by` (top-level) — surfaces the engineering-model dependency (Component 7 + IS codes)
- `action_steps` (top-level) — list of 3-5 numbered action strings, branched by risk level + presence of compliance/budget concerns. Mirrors the explain() WHAT SHOULD YOU DO NOW? section.

**v0.9.1 new fields:**
- `risk_drivers` (top-level) — list of strings explaining WHY risk_level is LOW/MEDIUM/HIGH
- `roadmap_position` (top-level) — positions output as step 1 of 6 with all journey steps named
- `soft_guidance_by_category` (top-level) — messages grouped by category (Compliance / Parking / Vastu / Budget / Design / Other) for UI sectioning
- `all_in_cost_estimate_lakhs` (top-level) — cited 2.5× breakdown replacing v0.9's ×1.5-2.0 heuristic; includes industry-standard 40/25/15/12/8 percentage breakdown
- `brief_summary.net_usable_low_sqm` / `net_usable_high_sqm` — 80%/90% bounds replacing v0.9's single 85% point
- `brief_summary.compliance.dcr_disclosure` (added in v0.9 Session C, still here)
- `kb_versions` now correctly reads `_version` field (v0.9.1 bug fix — was reading legacy `kb_version` and showing v1 even when v3 was current)

**Truncated example continued (legacy fields still present):**

```json
{
  ...
  "brief_summary": {
    "city": "chennai",
    "plot_width_m": 12.0,
    "plot_depth_m": 15.0,
    "plot_type": "detached",
    "plot_facing": "N",
    "plot_area_sqm": 180.0,
    "plot_area_sqft": 1937.5,
    "floor_count": 2,
    "floors_above_ground": 1,
    "has_stilt_parking": false,
    "total_built_area_sqft": 582,
    "budget_min_lakhs": 20,
    "budget_max_lakhs": 30,
    "vastu_preference": "partial",
    "compliance": {
      "is_setback_compliant": true,
      "source_authority": "TNCDBR 2019 (CMDA)",
      "violations": []
    },
    "soft_guidance_count": 10,
    "assumptions_count": 9
  },
  "c7_preview_cost_lakhs": 6.7,
  "c7_preview_cost_range_lakhs": [6.16, 7.24],
  "kb_versions": {
    "setback_rules": "Setbacks_India_2026_v1",
    "room_minimums": "RoomMinimums_India_2026_v1"
  },
  "resume_token": null
}
```

## Health check endpoint

The `/api/vastu/partial-items` endpoint is a safe, fast health check —
it returns 7 static items without calling the engine.

For a deeper check that validates Component 1 + Component 7 wiring:

```python
from buildemup.components.c01_brief_capture import (
    BriefCaptureEngine, BriefCaptureInput,
)
from buildemup.domain import (
    FloorRequirement, FloorUse, RoomRequirement, RoomType,
)

def healthz():
    try:
        output = BriefCaptureEngine().execute(BriefCaptureInput(
            plot_width_m=12.0, plot_depth_m=15.0, plot_facing="N",
            city="chennai", road_width_m=9.0,
            user_setback_front_m=1.5, user_setback_rear_m=1.5,
            user_setback_side_left_m=1.5, user_setback_side_right_m=1.5,
            floors=(FloorRequirement(
                floor_number=0, floor_use=FloorUse.RESIDENTIAL,
                rooms=(RoomRequirement(RoomType.LIVING, 1),),
            ),),
            budget_min_lakhs=15, budget_max_lakhs=25,
        ))
        return {"ok": True, "trace": output.trace_id}, 200
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500
```

## Known v1 limitations (documented, not bugs)

### Component 7
- In-memory insights buffer resets on deploy restart
- 3 of 5 KB modules still in Python (soil / RCC / material rates queued
  for v1.0 migration)
- Frame sanity + drift share assumptions today but no explicit
  consistency assertion — queued for v1.0 lightweight check

### Component 1 v0.9 (much smaller list — most v0.1 limitations fixed)

**Fixed in v0.9 (no longer applies):**
- ~~Save/resume browser-local only~~ → **v0.9 Session B**: SQLite-backed
  cross-device save with resume URL (30-day TTL)
- ~~5 of 6 city DCRs use NBC fallback~~ → **v0.9 Sessions C+D**: all 6
  launch cities have real DCR-backed setback rules

**Still queued:**
- **Conservative reads on 5 cities' setback values.** Mumbai/Delhi/
  Bangalore/Pune/Hyderabad tier values are best-available reads from
  cross-referenced secondary sources. Each city has `_disclosure_text`
  advising verification with the relevant authority. v1.0 should
  reconcile against authoritative printed publications.
- **Mumbai zone selector (Island City vs Suburbs)** — DCPR 2034 has
  different rules for Island City vs Suburbs. v0.9 defaults to SUBURBS
  with disclosure. Adding `Plot.mumbai_zone` enum is a clean v1.0
  domain extension.
- **Email-based resume link.** v0.9 ships URL-based cross-device save
  but no SMTP delivery. Adding email is real infrastructure
  (deliverability, bounces, SPF/DKIM) and pairs naturally with auth.
- **No form-level field validation feedback.** Next button only checks
  `required` fields; detailed per-field guidance is server-side after
  submit. v1.0 UX polish.
- **Not mobile-optimized.** Form works on mobile but layout isn't tuned.
  v1.0 UX pass.
- **No conversational/LLM input.** Form-based only per SPEC_v0.2 Q1.
  Conversational capture is v2 territory.
- **User email/phone stored session-only.** Collected in Brief domain
  object but not persisted in v0.9. Billing/auth pairs naturally with
  email-resume work above.
- **Bangalore very-large tier (>4000 sqm) unreachable through Plot
  domain** — Plot caps width/depth at 60m (3600 sqm cap). The 5m-all-sides
  tier is in KB and accessible to layout-engine consumers in v1.0+.

## Rollback

If Component 1 v0.9 causes unexpected issues in production, Component 7
remains independently deployable. Component 7 does not import anything
from Component 1 — the dependency is one-way (C1 → C7 for cost).

To roll back to pure Component 7:
1. Change start command to an older Component 7 entrypoint
2. The v0.7.2 test suite (274 tests) still passes standalone — verified
   in every Component 1 session that added tests across all of v0.9

## Support

Trace IDs appear in every output. If a user reports an issue,
ask for the trace ID — it points to the structured log entry. Component
1's trace_id is generated at the start of `BriefCaptureEngine.execute()`
and propagates through to Component 7 via the bridge call.
