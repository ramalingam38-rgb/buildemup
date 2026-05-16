# C11a v0.2 Backlog — S40 Additions

**Session**: S40 (B-NEW-T2 — M7a/M7b grid scale real upstream wiring).
**Filed by**: Claude per Rule 9.2.
**Format**: Mirrors `v0_2_backlog_S39_additions.md`.

---

## § 1 — Items LANDED at S40

### B-NEW-T2 — M7a/M7b real upstream wiring ✅ LANDED

- **Implementation**:
  - **C7 amendment v0.9 LOCKED** (file 79 in `02_specs_chronological/`):
    extended `GridGenerator.generate(env_w, env_d)` with optional
    keyword-only kwargs `target_bay_x_m: float | None = None` /
    `target_bay_y_m: float | None = None`. Validation: each must be in
    `PREFERRED_BAY_SIZES_M` and must satisfy
    `envelope_dim / target_bay >= 2.0`, else `ValueError`. Default
    args (or `None`) preserve v0.8 byte-identical behaviour.
  - `m7_grid_scale_real.py` (NEW): `regenerate_for_m7(source, grid_orig,
    floor_room_brief, plot_analysis, target_bay_m) ->
    WetZonePlannedCandidate`. Walks the C7→C8→C9→C10 cascade. Raises
    `M7NotViableError` (per_candidate severity) on any cascade-layer
    failure, with a `cascade_layer` attribute identifying which layer
    rejected the candidate (c7 / c8 / c9 / c10 / ancestry).
  - `upstream_adapter.py` extended:
    - `RealUpstreamRegenerator.regenerate(M7a/b)` dispatches into
      `regenerate_for_m7`. Synthetic sources raise NotImplementedError.
    - `compute_delta(M7a/b)` routes to new `_diff_m7_grid_scale`.
    - `_diff_m7_grid_scale` walks the ancestry chain to compare bay
      sizes (via `RoomSizingProvenance.grid_bay_max_m / min_m`),
      room areas, and wet-zone fields. Forbidden keys
      (META_ROOM_COUNT, META_FIXTURE_TYPES) are NOT emitted.
- **Tests**: 11 new C7 v0.9 tests in
  `buildemup/tests/test_c07_v0_9_target_bay_kwargs.py` (signature, validation,
  backwards-compat, keyword-only enforcement) + 18 new C11a tests in
  `tests/test_c11a/test_c11a_subsession6_m7_vertical_slice.py` (cascade
  success M7a/b, cascade failure M7NotViableError with layer attribution,
  Inv 17 atomicity, DeltaKey diff, RealUpstreamRegenerator dispatch,
  C7 amendment regression sentinel).
- **Origin**: S39 critique walk F5 / S39 backlog § 2.
- **Outcome**: Second Tier B operator family wired against real upstream
  (after M6 at S39). 2/4 Tier B operators now real. M8 still
  `NotImplementedError` per B-NEW-T3.
- **Validation discovery**: empirically discovered during build that
  `WetZonePlannedCandidate.room_sized_candidate.room_size_table` does
  NOT carry a `provenance.grid` field — the Grid object is only
  preserved as scalars on `RoomSizingProvenance.grid_bay_max_m` /
  `grid_bay_min_m`. Diff helper `_grid_from_wzpc` reads via these
  scalars (S39 Mistake #2 lesson reapplied — read schemas before
  guessing field names).

---

## § 2 — Items still pending (carried forward unchanged)

### B-NEW-T1.5 — Promote M6 rotation to a real C10 re-run

- Status unchanged. Carry-forward.

### B-NEW-T3 — M8 master-floor swap upstream wiring

- Status unchanged. **Now next priority for S41** — last remaining
  Tier B operator.
- Trigger: S40 close (now done).
- Effort: M (~2 days; rebuild `floor_room_brief` with master-floor
  swap, re-run C9 + C10 per floor).

### B-NEW-Y full — Long-horizon C11a stress fuzz

- Status unchanged from S39 (gated on T2 + T3). With T2 LANDED,
  the gate now reads "T3 only". Mutation chain accumulation tests
  using M1→M3a→M5→M9b on Tier A AND M6/M7 on Tier B become
  meaningful once T3 lands.

### B-NEW-W full — Cross-batch cache invalidation

- Status unchanged. Gated on B-NEW-E2 (process-lifetime cache, not yet filed).

### B-NEW-A — KB-driven bay set post-v1

- Status unchanged. Independent of B-NEW-T2 (this amendment uses the
  existing canonical set).

---

## § 3 — Items NOT created at S40

S40 was a tightly-scoped vertical slice per CODING_MANDATE policy.
The build did NOT surface any new backlog items. Pattern E (scope
creep mid-build) was avoided — no spelunking into C8/C9/C10 internals
beyond the cascade entry points.

The schema-drift issue with `_grid_from_wzpc` was caught by the
empirical smoke test BEFORE any tests were written; it's a fixed bug,
not a backlog item.

---

## § 4 — Summary

| Category | Count |
|---|---|
| Items LANDED at S40 | **1** (B-NEW-T2) |
| Spec amendments LOCKED at S40 | **1** (C7 v0.9) |
| Items still pending | **5** (B-NEW-T1.5, T3, Y full, W full, A) |
| New tests added at S40 | **29** (11 C7 v0.9 + 18 C11a subsession6) |
| Full project test count post-S40 | **2760 passed / 2 skipped** |
| C11a test count post-S40 | **324** |
| Tier B operators now real-wired | **2/4** (M6 at S39, M7a/M7b at S40) |
| Pending Tier B | **1** (M8 — B-NEW-T3, next priority for S41) |

---

**End of S40 Additions.**
