# BuildemUp Backlog — Session 29 Roll-up

**Generated at S29 close.** Authoritative additions/changes from Session 29 only. Pre-S29 entries (B-001..B-065) are carried in `backlog_session_28.md` and earlier files in this directory.

---

## Backlog items added in S29

### C4 lineage (B-066..B-084) — added across S29 critique cycles

| ID | Description | Origin (round) | Trigger | Effort |
|---|---|---|---|---:|
| B-066 | Polygon plots (v1: rectangular only; PlotShape.L_SHAPED / IRREGULAR are forward-compat enum values, no path supports them) | C4 v0.1 | new shape support requested | medium |
| B-067 | Per-month sun-path declination (currently solstice-only envelope) | C4 v0.6 walk #4 | hourly shading studies / daylight simulation needed | medium |
| B-068 | `effective_open_sides`: post-setback openness (currently RAW openness only) | C4 v0.6 walk #8 | C5/C6 layouts diverge raw vs post-setback assumptions | low–medium |
| B-069 | Composite-zone sub-classification (Mumbai coastal vs inland) | C4 v0.3 web research | climate-divergent heuristics observed | medium |
| B-070 | IMD wind-rose data per city (full directional + intensity distribution) | C4 v0.3 SC | full IMD data integration | medium |
| B-071 | Latitude-band city fallback for unknown cities | C4 v0.3 walk #3 | new-city support beyond v1 list | low |
| B-072 | C7 retrofit to consume PlotAnalysis.soil_estimate | C4 v0.4 | C7 modernization | medium |
| B-074 | MEDIUM_ROCK proper kPa value (real ~1000-1500 per IS 6403; currently 660) | v0.6 walk #2 | foundation-design accuracy review | low |
| B-075 | AspectClass enum + extreme-plot detection flag | v0.6 walk #4 | extreme plot UX surface | low |
| B-076 | Plot.corner_orientation input field (eliminates LEFT default for CONTINUOUS+corner) | v0.6 walk #5 | C1/C3a input contract update | medium |
| B-077 | Richer multi-state soil confidence model (currently LOW/MEDIUM/HIGH + free-text) | v0.6 walk #7 | foundation-tier features | medium |
| B-078 | System-wide trace_id lifecycle policy (UUID format, generation site, validation) | v0.6 walk #9 | observability infra | low |
| B-079 | System-wide KB_VERSION format policy (semantic versioning + content hash) | v0.7 walk #3 | KB audit/rollback requirement | medium |
| B-080 | Dynamic KB mutation re-validation (hot reload, admin tools, runtime monkey-patch) | v0.8 walk #2 | hot reload introduced | low–medium |
| B-081 | Performance test: rolling baseline OR env-configurable threshold | v0.8 walk #6 | CI infrastructure live | medium |
| B-082 | Structured kPa error fields on SoilEstimate (`approximation_error_pct`, `expected_range_kpa`) | v0.9 walk #2 | C5/C7 foundation-cost or risk consumes uncertainty band; resolve alongside B-074 | medium |
| B-083 | Sub-city soil zoning (`Plot.city_zone` / geo_hash input) | v0.9 walk #3 | foundation incident report, OR upstream input gains zoning, OR insurance/code requirement | medium-large |
| B-084 | Spec–code drift detection: executable spec format (JSON/YAML schema) + CI gate | v1.1 walk #5 | CI infrastructure live (shared trigger with B-081) | medium |

**18 items in C4 lineage.** Web-verified citations included where applicable (B-074, B-082, B-083).

### C5 lineage (B-085..B-093) — added across S29 design cycles

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---:|
| B-085 | ML topology scoring (House-GAN-style bubble-diagram refinement) | C5 v0.2 | corpus ≥2k labelled India residential plans | high |
| B-086 | More topology kinds (Hall-centric, U-shape, T-shape) | C5 v0.2 | real plot fails 4-topology fit | medium |
| B-087 | Multi-floor coordination (ground-floor topology constrains first-floor) | C5 v0.2 | 2-floor brief support added | medium |
| B-088 | Vastu integration in zone-band assignment | C5 v0.2 | Tier-2 customer demand | medium |
| B-089 | User-supplied topology preference (override candidate selection) | C5 v0.2 | architect-pro tier launch | low |
| B-090 | Recalibrate decision-table thresholds (Apr-17 architecture-doc values) | C5 v0.2 / DRAFT-Q 2 | empirical Indian market data, OR real-plot decision-table failure | low + data |
| B-091 | Climate-variant zone-band assignments per topology | C5 v0.2 / DRAFT-Q 5 | climate-divergent layout outcomes in user feedback | medium |
| B-092 | Promote BuildableEnvelope to public C2 output (or PlotAnalysis field). C2 currently computes inline in `hard_physics_checks.py:132`. | C5 v0.3 walk D2 | C5/C6/C8 layouts diverge between raw-plot-dim and post-setback-dim | medium |
| B-093 | Refine `CorridorSketch.approx_length_m` heuristics (post-setback-aware, aspect-ratio-scaled) | C5 v0.4 walk #7 | C8 reports inaccurate corridor sizing OR B-092 lands | low (depends on B-092) |

**9 items in C5 lineage.**

---

## S29 cumulative totals

- **Total new backlog items added in S29: 27** (B-066..B-084 = 18 from C4; B-085..B-093 = 9 from C5).
- **Pre-S29 backlog (B-001..B-065)** carried unchanged in earlier files.
- All items have explicit triggers per Rule 9.

---

## Verdict tracking — items NOT added (push-backs documented)

C4 push-backs (11 across S29): see specs § 15 in v0.6, v0.7, v0.8, v0.9, v1.0, v1.1.
C5 push-backs (39 across S29): see specs § 15 in v0.3 through v0.9.

**Total documented push-backs in S29: 50.**

---

## Triggers most likely to fire next

| Trigger | Activates | Probability |
|---|---|---|
| CI infrastructure lands | B-080, B-081, B-084 simultaneously | high (essential infra) |
| C5 code build (next session) | reveals if B-092 BuildableEnvelope is needed | high |
| First non-Tier-1 city user request | B-071 latitude-band fallback | medium |
| Architect-pro tier launch | B-089 user-override | low (pricing-tier-bound) |
| Empirical India market data acquisition | B-090 threshold recalibration, B-074 MEDIUM_ROCK kPa | low (data-bound) |
