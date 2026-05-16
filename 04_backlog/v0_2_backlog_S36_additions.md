# Backlog additions — S36 close (post-critique)

**Authored at**: S36 close, after external critique walk.
**Mirror of**: `04_backlog/v0_2_backlog.md` (canonical) — additions appended.
**Status**: filed per Rule 9.2 (Ramalingam approved at S36 close).

---

## New B-NNN entries (4)

| ID | Description | Origin | Trigger | Effort |
|---|---|---|---|---|
| B-248 | C10 wet-strip depth derived from C11 placement output. Replace hardcoded `_PROXY_DEPTH_M = 0.6` in `wet_zone_planner._wet_strip_bbox` with a fixture-profile + room-subtype + wall-orientation aware derivation, sourcing realistic bbox from C11. | S36 critique #2 | C11 v1 LOCK | M |
| B-249 | C10 wall-capacity uses fragmented usable spans. Replace `floor(wall.length_m / minimum_riser_spacing_m)` with `usable_wall_spans` model that excludes window/door openings, beam interruptions, and door clearances. Requires upstream "openings KB" — note: openings KB is itself an implicit dependency, flag separately if not yet filed. | S36 critique #3 | openings KB lands | M-L |
| B-250 | C10 KB validator: hot-reload, version-hash check, immutable runtime snapshots. Replace lazy `_KB_VALIDATED` global cache with checksum-validated reload-detection. Required before service-mode deployment; CLI/batch use is unaffected. | S36 critique #5 | service-mode deployment | S-M |
| B-251 | C10 strict-fallback removal SHIPPED at S37 (`_build_fixture_types_per_room` now raises `KBVersionMismatchError` instead of silent default). This entry tracks any post-ship hardening (e.g. fail-loud override flag, telemetry on raise frequency). | S36 critique #7 → S37 ship | post-launch observability | XS |

---

## Existing entry expansion (1)

**B-237** — already covers cross-platform replay CI matrix and Hypothesis property-based tests; **scope expansion confirmed at S36 critique #8**: add explicit float-quantization rules + `Decimal`/fixed-point arithmetic for core geometry primitives. No new ID; B-237 description should be updated next backlog-edit pass to mention this.

---

## Critique items NOT filed (verdicts from S36 critique walk)

| Critique # | Item | Verdict | Reason |
|---|---|---|---|
| 1 | Trap-arm modelling heuristic | **MISFRAMED** + DOCUMENTED | Already routed to B-220. C10 § 0 explicitly excludes hydraulic simulation. |
| 4 | No true hydraulic simulation | **MISFRAMED** | Literal restatement of C10 § 0 non-goal. Routed to B-220 + B-222. |
| 6 | Exception-driven control flow | **REJECTED-AS-CONSIDERED** | Pattern intentional, mirrors C9 § 14.40. PhaseResult refactor would diverge from C9 + invalidate SHIPPED tests for no measured win. |
| 9 | Search scalability | DOCUMENTED | B-217 (polygonal envelopes spatial partitioning) covers this. |
| 10 | Orthogonal geometry only | DOCUMENTED | B-217 + B-226 cover polygonal evolution. |

---

## Rule 8 reminder

These additions are filed per Ramalingam's S36-close direction
("I am ok with backlogs"). No spec LOCKs were re-opened; no
existing LOCKED specs were amended. Item 7 patched in S37
(landed at 2314 / 3 baseline; +2 tests).

---

**End of S36-close backlog additions.**
