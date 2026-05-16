# B-NEW-J — C5 privacy zoning rule — v1.0 **LOCKED**

**Status**: **v1.0 LOCKED** by Ramalingam at S38, 09 May 2026.
**Predecessor**: v0.1 PROPOSED.
**Authored**: S38.
**Required by**: C11a v1.0 LOCKED § 3.4 — Tier A predicate matrix
`C5.privacy_zoning` for M2 / M5 operators.

**Launch-complement requirement**: B-NEW-J-override (defined in § 6)
is escalated to "must ship at the same release window as B-NEW-J's
production enforcement, not deferred indefinitely". See Walk #2 and
Walk #4 critique adjudications.

---

## § 0 — What this amendment adds

C5 already emits `TopologyCandidate.zone_bands: Mapping[ZoneBand,
PlotOrientation]` carrying the band-to-direction assignment. What
was missing: a named numbered invariant + callable predicate
enforcing "PRIVATE band must not face the road".

This amendment:

1. Adds invariant § 14.10 (NEW v1) to C5: privacy zoning rule.
2. Adds `validate_privacy_zoning(zone_bands, plot_facing)` predicate
   in `components/c05/zone_bands.py`.

---

## § 1 — The rule

For every `TopologyCandidate`, the compass direction assigned to
the PRIVATE band MUST NOT face the road (i.e., the plot's facing
direction).

**Cardinal facings** (N/S/E/W) define a single forbidden direction.
**Intercardinal facings** (NE/NW/SE/SW) define a forbidden set of
THREE directions: the intercardinal itself plus its two adjacent
cardinals (corner plot exposure logic).

**Vacuous-pass**: `zone_bands` lacking PRIVATE entry returns
`(True, None)`.

**Mode**: RAISE (Tier A predicate; per-candidate via C11a's mutation
rejection rule).

**Architectural rationale**: Indian residential typology
consistently locates private spaces (bedrooms) away from the road.
The rule lives at C5 because (a) it operates at zoning intent before
per-room sizing happens, and (b) C11a's M2 / M5 operators mutate at
the zoning level. Per-room "bedroom-on-road-wall" checks at C9/C10
are stricter follow-up captured in B-NEW-J-roomlevel.

---

## § 2 — Predicate contract

```python
def validate_privacy_zoning(
    zone_bands: Mapping[ZoneBand, PlotOrientation],
    plot_facing: PlotOrientation,
) -> tuple[bool, str | None]
```

C11a Tier A registers as `MutationViabilityPredicate(rule_owner="C5",
rule_id="privacy_zoning", _predicate_fn=validate_privacy_zoning,
pending_upstream=False)`.

---

## § 3 — Tests

`tests/test_c5_privacy_zoning.py` — **22 tests, all passing**.
Includes a smoke test that exhaustively iterates **all 32 default
zone-band outputs** from C5's `default_zone_bands(kind, facing)` —
confirming C5's existing design is internally consistent with the
new rule.

---

## § 4 — Numbered invariant

C5 SPEC § 14.10 (NEW v1): "Privacy zoning: in any
TopologyCandidate, `zone_bands[ZoneBand.PRIVATE]` MUST NOT lie in
the road-facing direction set derived from `plot_facing`."

Mode: RAISE (per-candidate via Tier A predicate).

---

## § 5 — Files modified

| File | Change |
|---|---|
| `components/c05/zone_bands.py` | Add `validate_privacy_zoning()` + `_ROAD_FACING_FORBIDDEN` lookup; `__all__` updated |
| `tests/test_c5_privacy_zoning.py` | New test file — 22 tests |

---

## § 6 — Backlog filed (with B-NEW-J-override escalation)

| ID | Description | Trigger | Effort |
|---|---|---|---|
| **B-NEW-J-override** | **Launch-complement** — `brief.layout_overrides: LayoutOverrides` field carrying named-rule bypass tokens (e.g., `accept_road_facing_private_band: bool = False`). C11a's predicate registry consults overrides before firing the predicate. **Must ship at the same release window as B-NEW-J's production enforcement.** Owned by C1 (brief schema) + C11a (registry consultation). When implemented, MUST follow B-meta-rule-taxonomy framework (no one-off override mechanism) | C11a launch-complement | S-M |
| **B-NEW-J-roomlevel** | Per-room privacy check at C9/C10 — even with PRIVATE band correctly oriented, individual bedroom windows shouldn't front the road | post-launch + B-238 architect review | M |
| **B-NEW-J-acoustic** | Acoustic isolation rule (kitchen/utility next to bedroom) | post-launch | S-M |

---

## § 7 — LOCK authority

**LOCKED v1.0 by Ramalingam at S38, 09 May 2026, with explicit
B-NEW-J-override launch-complement requirement acknowledged.**

---

**End of B-NEW-J v1.0 LOCKED.**
