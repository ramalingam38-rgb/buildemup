# MASTER DOC v3.12 → v3.13 — DELTA — S38 (Path α — full upstream amendments)

**Authored**: S38 (current session, in progress).
**Predecessor**: v3.12 (S37 close — C11a v1.0 LOCKED, C11b v1.0 LOCKED).
**Scope of this delta**: four upstream amendments shipped as PROPOSED to
satisfy the C11a v1.0 § 0.2 + Inv 24 LOCK gate (zero outstanding
upstream-amendment waivers). Per Ramalingam direction at S38 open,
**Path α confirmed** — full upstream design, not waiver, not stub.

---

## § 1 — Adjudication context (S38 open)

S37 close granted four `UpstreamAmendmentWaiver` tokens for B-NEW-J,
K, L, P. C11a § 0.2 caps active waivers at 3, so 4 waivers exceeds the
cap and fails Inv 24 (LOCK gate `len(active_waivers) ≤ 3`).

S38 surfaced the choice as a3-way: (a1) three amendments + 1 waiver,
(a2) all four amendments, (b) raise the cap. After honest pushback on
the previous Claude's "all XS, ~30 min each" estimate (B-NEW-P was
genuinely XS; K/L/J each required real design work), the choice was
re-presented as: (α) full upstream design, (β) stub-predicate
amendments, (γ) revert to waiver mechanism.

**Ramalingam adjudication: Path α — full upstream design.**

This delta captures the four amendments' shipping state.

---

## § 2 — Amendments shipped (this session)

### B-NEW-P — error severity classification (XS, mechanical)

**Spec**: `B_NEW_P_AMENDMENT_v0_1_PROPOSED.md`.
**Code**:
- `components/c10/errors.py` — ClassVar import, `_SeverityTier` Literal,
  6 explicit `severity_tier` lines (1 base + 5 overrides).
- `components/c09/errors.py` — same pattern (1 base + 2 overrides).
- `components/c08/errors.py` — three standalone error classes, each
  with explicit `severity_tier`.
**Scope correction**: mandate said "C7+C9+C10"; correct scope is
"C8+C9+C10" since C7 raises only stdlib `ValueError`/`KeyError`
(properly handled by C11a § 2.7's defensive default `"unknown"`
→ systemic).
**Tests**: `tests/test_severity_tier_classification.py` — **65 tests**.

### B-NEW-K — C7 staircase clearance (M, real spatial design)

**Spec**: `B_NEW_K_C7_AMENDMENT_v0_1_PROPOSED.md`.
**Code**: `components/c07/grid_generator.py`:
- `Staircase` frozen dataclass (origin, width, landing depth, anchor).
- `MIN_STAIRCASE_WIDTH_M = 0.9` and `MIN_STAIRCASE_LANDING_DEPTH_M = 0.9`
  constants (NBC 2016 Part 4 Table 3.1.4-G, flagged for B-150-equiv
  primary-source verification).
- `Grid.staircase: Optional[Staircase] = None` field with
  backwards-compat default.
- W9 invariant enforced in `Grid.__post_init__` when staircase set.
- `validate_staircase_clearance(grid, staircase)` predicate function —
  the callable C11a Tier A registers as `C7.staircase_clearance`.
**Tests**: `tests/test_c7_staircase_w9.py` — **22 tests**.
**Backlog**: B-NEW-K-impl (post-launch GridGenerator integration),
B-NEW-K-egress (C9/C10 integration).

### B-NEW-L — C8 entry approach Inv 21 (S, predicate-only)

**Spec**: `B_NEW_L_C8_AMENDMENT_v0_1_PROPOSED.md`.
**Code**: `components/c08/validator.py`:
- New helpers `_FACING_TO_EDGES` lookup table, `_iter_entry_endpoints`,
  `_facing_edge_label`.
- `validate_entry_approach(corridor_path, envelope_width_m,
  envelope_depth_m, plot_facing, *, epsilon_m)` predicate.
- Cardinal facings (N/S/E/W) require ENTRY on one specific edge.
- Intercardinal facings (NE/NW/SE/SW) accept either of two adjacent
  edges.
- Vacuous-pass on `has_corridor=False` and on paths without ENTRY
  endpoints.
- `__all__` updated.
**Tests**: `tests/test_c8_inv21_entry_approach.py` — **21 tests**.
**Design discipline**: Inv 21 is exposed only as the C11a Tier A
predicate; `validate_corridor_path` (the existing C8 batch validator)
intentionally does NOT call it — Inv 21 is a mutation-time check,
not a corridor-construction-time check. C5/C8 produce candidates per
their own design defaults (which already satisfy Inv 21 by
construction in v0.6 LOCKED).
**Backlog**: B-NEW-L-rotated (polygonal envelopes), B-NEW-L-multi-entry
(service entries).

### B-NEW-J — C5 privacy zoning (S, predicate-only)

**Spec**: `B_NEW_J_C5_AMENDMENT_v0_1_PROPOSED.md`.
**Code**: `components/c05/zone_bands.py`:
- `_ROAD_FACING_FORBIDDEN` lookup table mapping plot.facing →
  forbidden direction set.
- `validate_privacy_zoning(zone_bands, plot_facing)` predicate.
- Cardinal facings forbid the single matching cardinal direction.
- Intercardinal facings forbid the intercardinal + two adjacent
  cardinals (corner plot exposure logic).
- Vacuous-pass on missing PRIVATE entry.
- `__all__` updated.
**Tests**: `tests/test_c5_privacy_zoning.py` — **22 tests** including a
smoke test that exhaustively checks all `default_zone_bands(kind,
facing)` combinations against the rule (4 topology kinds × 8 facings =
32 combinations) — **all pass, confirming C5's existing design is
internally consistent with the new rule**.
**Backlog**: B-NEW-J-roomlevel (per-room privacy at C9/C10),
B-NEW-J-acoustic (kitchen-bedroom adjacency rule).

---

## § 3 — Cumulative numbers (S38 in-progress)

|Metric|S37 close|S38 in-progress|Δ|
|---|---|---|---|
|Components shipped (code)|10/17|10/17|—|
|Test count (excl. e2e)|2290 / 2 skipped|2420 / 2 skipped|+130|
|Active waivers (vs C11a § 0.2 cap=3)|4 (over cap)|0|−4|
|Pending-upstream predicates blocking C11a build|4|0|−4|
|Files modified|—|6 production + 4 new tests|—|
|Spec docs added (PROPOSED)|—|4|+4|

---

## § 4 — Inv 24 LOCK gate state

C11a § 0.2 / Inv 24 reads:

    pending_upstream_predicate_count - len(active_waivers) == 0
    AND len(active_waivers) ≤ 3

After this session's work (assuming Ramalingam LOCKs the four PROPOSED
amendments):
- pending_upstream_predicate_count = 0 (all four are real callable
  predicates)
- len(active_waivers) = 0
- Both gate clauses pass.

**Status**: gate ready for C11a build. Waiting on Ramalingam LOCK
adjudication of the four PROPOSED amendments before C11a Sub-session 1
starts.

---

## § 5 — Sub-session bookkeeping

Per D-066 build cycle rule, this session continues until Ramalingam
says "stop" or "hand off". Honest budget assessment at this point:
the four amendments consumed ~2/3 of the session-1 budget. Remaining
budget could support C11a Sub-session 1 start (`schema.py` +
`errors.py` + `provenance.py` + waiver/purity registries) IF
Ramalingam confirms LOCK on the four PROPOSED amendments now —
otherwise we end here, await LOCK adjudication, and resume in S39.

---

## § 6 — Open questions for Ramalingam

1. **LOCK adjudication on the 4 PROPOSED amendments?** All four ship
   with their own spec docs (`B_NEW_*_AMENDMENT_v0_1_PROPOSED.md`),
   passing tests, and full suite green. Any LOCK iteration becomes
   v0.2 PROPOSED, etc.
2. **Continue to C11a Sub-session 1 in this session?** Budget allows
   it if LOCK is granted on the amendments now. Otherwise hand off and
   resume S39.
3. **Memory refresh timing?** Default plan: refresh at session close.

---

**End of v3.12 → v3.13 delta.** Awaiting Ramalingam adjudication on §6
items.
