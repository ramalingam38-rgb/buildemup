# Backlog Session 31 — C8 v0.5 LOCK additions

**Session**: S31 (post C6 SHIP, C8 v0.5 LOCKED at session close)
**Pre-S31 max**: B-107
**Post-S31 max**: B-126
**Net adds**: 19 items (B-108 through B-126)

All items mirrored from C8 v0.5 LOCKED § 12 — spec is canonical, this is project-level visibility per Rule 9.

## Summary table

| ID | Origin | Title | Trigger |
|---|---|---|---|
| B-108 | C8 v0.1 § 3 / § 11 | Primary-source verification of NBC corridor minimum | Pre-prod |
| B-109 | C8 v0.1 § 4.3 | CorridorTooNarrowError graceful fallback | First user case |
| B-110 | C8 v0.2 § 4.5 | C5 ↔ C8 length-drift integration test | C8 SHIPs |
| B-111 | C8 v0.1 § 4.2 | Rotated structural grid support | B-066 / C7 capability |
| B-112 | C8 v0.1 § 8 | TNCDBR rule 42 + city-specific overrides | Local rule mismatch |
| B-113 | C8 v0.1 § 3 inv 3 | Diagonal corridor segments | Architectural signal |
| B-114 | C8 v0.1 § 9 | Multi-floor vertical corridor coordination | C12 ships |
| B-115 | C8 v0.1 § 4.3 | Variable-width within single segment | Aesthetic signal |
| B-116 | C8 v0.2 § 14.1 | Per-room ZoneBandEnvelope refinement | C9 LOCK / room-fit failures |
| B-117 | C8 v0.2 § 4.3 | Cross-segment width interaction model | Aesthetic signal |
| B-118 | C8 v0.2 walk #1 | Area-budget-aware corridor sizing | Empirical infeasibility |
| B-119 | C8 v0.3 § 14.16 | Band-importance-weighted strip allocation | C9 / C11a signals |
| B-120 | C8 v0.3 § 14.14 | Polygon-union via shapely fallback | B-113 / diagonal segments |
| B-121 | C8 v0.3 § 14.12 | Junction transition segments / fillets | B-113 / aesthetic signal |
| B-122 | C8 v0.3 § 14.15 | Empirical thresholds for consumption_band | 50+ production plans |
| B-123 | C8 v0.4 § 14.19 / § 14.20 | Width-scoring + taper-length calibration | 50+ production plans |
| B-124 | C8 v0.4 § 14.20 | Width-interpolation impl in junction regions | C8 build session |
| B-125 | C8 v0.4 § 14.21 | Envelope-symmetry weight calibration | 20+ production plans |
| B-126 | C8 v0.5 walk #4 | Caller-side retry helper for CorridorDispatchError | First pipeline orchestrator |

## Origin-by-walk distribution

- v0.1 DRAFT: 7 items (B-108, B-109, B-111, B-112, B-113, B-114, B-115)
- v0.2 PROPOSED (walk #1): 4 items (B-110, B-116, B-117, B-118)
- v0.3 PROPOSED (walk #2): 4 items (B-119, B-120, B-121, B-122)
- v0.4 PROPOSED (walk #3): 3 items (B-123, B-124, B-125)
- v0.5 PROPOSED (walk #4): 1 item (B-126)
- v0.5 LOCKED (walk #5): 0 new items (reviewer confirmation only)

## Trigger categories

- **Build-time** (next session): B-124
- **Empirical-calibration-pending**: B-108, B-122, B-123, B-125
- **Component-gated** (other component must ship first): B-114 (C12), B-116 (C9), B-126 (orchestrator)
- **Capability-gated** (B-066 / B-113 chain): B-111, B-120, B-121
- **Field-signal-pending** (real user/plan signal): B-109, B-115, B-117, B-119, B-121
- **Production-trigger** (post-deployment): B-110, B-112, B-118

