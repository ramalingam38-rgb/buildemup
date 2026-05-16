# Backlog additions — Session 30 (S30)

**Session scope**: C5 v0.9 LOCKED → C5 v1.0 SHIPPED; C6 designed from scratch → v0.5 LOCKED across 4 critique walks.

**Session B-NNN range**: B-094 → B-106 (13 new items).

**Pre-S30 max B-NNN**: B-093.

---

## Items filed during S30

### From C5 critique walk (v0.9 → ship)

| ID    | Description                                                                                                          | Origin                  | Trigger                                                                | S30-scope verdict     | Effort |
|-------|----------------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------------------------------------------|------------------------|--------|
| B-094 | Orthogonalize `width_fit` vs `aspect_ratio_fit` — partial overlap on plot dimensions creates double-counting risk  | C5 walk item 9 (S30)    | When B-090 yields ≥ 50 datapoints; check residual correlation > 0.7    | OUT (pre-empirical)    | S      |
| B-095 | `FloorRoomBrief` enrichment for downstream components — add room types (master/guest), per-room sizes, adjacency    | C5 walk item 10 (S30)   | When C6 or C9 are scoped; coordinate with C1 brief flow                | OUT (downstream concern)| M      |

### From C6 v0.1 DRAFT (new component)

| ID    | Description                                                                                                          | Origin                  | Trigger                                                                | S30-scope verdict     | Effort |
|-------|----------------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------------------------------------------|------------------------|--------|
| B-096 | Externally expose 8-direction output (currently 8-dir adopted internally for Vastu, output stays 4-dir)              | C6 v0.1 § 9             | When downstream consumers ask for 8-dir externally                     | OUT (internal-adopted) | M      |
| B-097 | Multi-floor per-floor orientation — each floor independently oriented                                                | C6 v0.1 § 9             | When C9/C10 introduce multi-floor placement                            | OUT (single-floor v1)  | L      |
| B-098 | HOT_DRY and COLD climate zones — currently reserved (no v1 city maps to them)                                        | C6 v0.1 § 9             | When a v1 city maps to either                                          | OUT (no use case)      | S      |
| B-099 | Populate `vastu_engine` KB for FULL tier — currently FULL hard-fails until populated (C6 § 14.8)                     | C6 v0.1 § 9             | **HARD-BLOCKING**: FULL tier raises NotImplementedError until B-099    | OUT (KB work)          | M      |
| B-100 | Building massing rotation engine ("Meaning A" of orientation, distinct from C6's functional priority)                | C6 v0.1 § 9             | When non-rectangular plots arrive (also gated by B-066)                | OUT (no use case)      | L      |

### From C6 v0.2 critique walk

| ID    | Description                                                                                                          | Origin                  | Trigger                                                                | S30-scope verdict     | Effort |
|-------|----------------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------------------------------------------|------------------------|--------|
| B-101 | Signal interaction terms (sun×wind cooling effect, vastu×road alignment) replacing pure linear blend                 | C6 v0.2 walk item 1     | When B-090 yields ≥ 50 datapoints; check fit residuals                 | OUT (pre-empirical)    | M      |
| B-102 | Location-aware wind & continuous climate scaling — extend C4 `PlotAnalysis` with prevailing_wind, humidity, etc.    | C6 v0.2 walk item 2     | When B-090 reveals city-level variance > zone-level                    | OUT (C4 territory)     | L      |
| B-103 | Dynamic hysteresis threshold = f(confidence, aspect_ratio, climate_strength)                                         | C6 v0.2 walk item 4     | Post-B-090; same gate as B-101                                         | OUT (pre-empirical)    | S      |
| B-104 | Entropy- or variance-based confidence metric (v0.4 § 14.15 baseline = margin-clamped)                                | C6 v0.2 walk item 8     | When real-world feedback shows margin-clamped misleads                 | OUT (v1.x improvement) | S      |
| B-105 | C6 ↔ C8 layout-feasibility feedback loop — iterative re-scoring of orientation against corridor feasibility          | C6 v0.2 walk item 11    | After C8 ships and is stable                                           | OUT (post-C8)          | L      |

### From C6 v0.3 critique walk

(none filed — verdict: 0 new B-NNNs)

### From C6 v0.4 critique walk

| ID    | Description                                                                                                          | Origin                  | Trigger                                                                | S30-scope verdict     | Effort |
|-------|----------------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------------------------------------------|------------------------|--------|
| B-106 | SERVICE-band-only secondary-road bonus on corner plots — soft preference for service-entry on secondary road        | C6 v0.4 walk item 9     | (a) corner-plot share of v1 production usage exceeds 25%, OR (b) ≥ 5 user complaints about service entry placement | OUT (post-deployment empirical) | S |

### From C6 v0.5 critique walk

(none filed — verdict: 0 new B-NNNs; only one amendment: signal_dominance interpretability layer integrated into spec)

---

## Roll-up summary

| Source | Count | IDs |
|---|---|---|
| C5 walk (S30) | 2 | B-094, B-095 |
| C6 v0.1 DRAFT | 5 | B-096, B-097, B-098, B-099, B-100 |
| C6 v0.2 walk | 5 | B-101, B-102, B-103, B-104, B-105 |
| C6 v0.3 walk | 0 | — |
| C6 v0.4 walk | 1 | B-106 |
| C6 v0.5 walk | 0 | — |
| **Total** | **13** | **B-094 through B-106** |

All 13 items appended to canonical `v0_2_backlog.md` per Rule 9 ("spec is canonical; project backlog file mirrors").

---

## Hard-blocking items (subset of above)

Of the 13 new items, **one is hard-blocking**:

- **B-099** — `vastu_engine` KB. Until populated, C6's FULL Vastu tier raises `NotImplementedError("FULL tier requires vastu_engine KB; B-099. Use PARTIAL.")`. OFF and PARTIAL tiers remain fully functional. B-099 mechanically pressures KB population (C6 § 14.8 design decision, reaffirmed across 4 critique walks).

The other 12 are deferred-but-non-blocking (calibration / future-feature / post-empirical territory).
