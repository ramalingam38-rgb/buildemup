# C7 SPEC AMENDMENT v0.9 LOCKED — `GridGenerator.generate()` target-bay kwargs (B-NEW-T2 enabler)

**Component**: 7 (Structural Grid Engine — SHIPPED at v0.8 LOCKED)
**Amendment status**: **v0.9 LOCKED.** Ramalingam directive: "Lock it and proceed" (S40).
**Authority**: Ramalingam directive (per `NEXT_CLAUDE_HANDOFF.md` § 3.3 + § 8.1 standing obligations: "C7 amendment is the only spec change, and that needs Ramalingam LOCK before code").
**Authored**: S40 open.
**Driver**: Unblocks B-NEW-T2 (M7a/M7b grid scale real upstream wiring) per S39 backlog § 2.

---

## § 0 — LOCK declaration

**v0.9 LOCKED at S40.** Ramalingam directive: "Lock it and proceed."
Per Rule 8 (LOCK authority belongs to Ramalingam alone), this declaration
constitutes the LOCK trigger. v0.9 PROPOSED contents are promoted to v0.9
LOCKED with no schema changes — both validation rules (preferred-set
membership; ≥2-bays-fits) accepted as proposed.

The PROPOSED text is preserved chronologically at file `78_..._v0_9_PROPOSED.md`
per Rule 3.

---

## § 1 — Why this amendment exists

C11a v1.0 LOCKED specifies M7a/M7b operators that change the grid bay size
(M7a → 3.3m, M7b → 2.7m; see C11a v1.0 § 2.2 operator metadata, expected delta
`{GEO_GRID_BAY_SIZE, GEO_ROOM_AREA}`).

The current `GridGenerator.generate(envelope_width_m, envelope_depth_m)` does
**not** accept a target bay size — bay sizes are auto-selected via
`_select_bay_size()` based on a sweet-spot (3.3m) heuristic. There is no
caller-side mechanism to force a specific bay size from `PREFERRED_BAY_SIZES_M`.

B-NEW-T2 needs that mechanism. This amendment is the smallest possible change
that unblocks B-NEW-T2 without disturbing any existing C7 caller.

---

## § 2 — Delta from v0.8 → v0.9

| Item | v0.8 LOCKED | v0.9 PROPOSED |
|---|---|---|
| `GridGenerator.generate()` signature | `(self, envelope_width_m: float, envelope_depth_m: float) -> Grid` | `(self, envelope_width_m: float, envelope_depth_m: float, *, target_bay_x_m: float \| None = None, target_bay_y_m: float \| None = None) -> Grid` |
| Bay size when no target given | `_select_bay_size(env_dim)` (auto, sweet-spot heuristic) | UNCHANGED — same auto-select |
| Bay size when target given | N/A (no kwarg existed) | Use the provided value directly, skipping `_select_bay_size`, after validation |
| `Grid` dataclass shape | unchanged | UNCHANGED |
| Wall segment behavior | unchanged | UNCHANGED |
| `_distribute_columns` | unchanged | UNCHANGED |
| All other C7 modules | unchanged | UNCHANGED |

**Schema, behaviour for default-args path, invariants W1-W8, test target,
failure modes, frozen-and-replace pattern: ALL UNCHANGED FROM v0.8.**

The change is strictly a non-breaking signature extension on a single method.

---

## § 3 — Behavioral contract for target-bay kwargs

### § 3.1 — Default path (kwargs omitted or `None`)

```python
g = GridGenerator().generate(env_w, env_d)
# OR equivalently:
g = GridGenerator().generate(env_w, env_d, target_bay_x_m=None, target_bay_y_m=None)
```

Behavior is **byte-identical to v0.8 LOCKED**: `_select_bay_size()` chooses
both bay sizes via the sweet-spot heuristic. Every C9/C8/C10 caller that
exists today goes through this path.

**Backwards compatibility guarantee**: every existing C7 test passes
unchanged. Every existing call site (C8, C9, C10, c11a `m6_wet_rotate_real`,
the 174 in-tree C7 tests, integration tests) continues working without code
changes.

### § 3.2 — Forced-target path (kwarg provided)

```python
g = GridGenerator().generate(env_w, env_d, target_bay_x_m=3.3, target_bay_y_m=3.3)
```

Validation rules (in this order; first failure raises):

1. **Preferred-set membership.** If `target_bay_x_m is not None`:
   `target_bay_x_m` MUST be a member of `PREFERRED_BAY_SIZES_M`
   (`[2.7, 3.0, 3.3, 3.6, 4.0, 4.5, 5.0]` from
   `buildemup/kb/rcc_design_rules.py:43`). Otherwise raise
   `ValueError(f"target_bay_x_m={target_bay_x_m!r} not in
   PREFERRED_BAY_SIZES_M={PREFERRED_BAY_SIZES_M}")`.
   Same for `target_bay_y_m`.

   **Rationale**: PREFERRED_BAY_SIZES_M is the canonical residential bay
   set per Indian construction practice and IS-456-derived span limits. The
   amendment must not let a caller silently inject non-canonical sizes that
   would break downstream cost estimation (`cost_estimator.py`),
   structural sizing (`structural_sizer.py`), or load combinations.

2. **At-least-2-bays-fits.** If `target_bay_x_m is not None`:
   `envelope_width_m / target_bay_x_m >= 2.0` MUST hold. Otherwise raise
   `ValueError(f"envelope_width_m={envelope_width_m} too small for
   target_bay_x_m={target_bay_x_m}: need ≥ 2 bays per axis")`. Same for y.

   **Rationale**: `_select_bay_size()` only ever returns a bay size that
   yields ≥2 bays (its bay_count loop runs `(2, 3, 4, 5)`). The existing C7
   invariants (W1–W8) and downstream consumers (column distribution,
   corridor design, room sizing) implicitly assume ≥2 bays per axis. The
   target-bay path must preserve this invariant.

3. **Envelope minimum.** UNCHANGED from v0.8: `envelope_width_m >= 5.0`
   AND `envelope_depth_m >= 5.0`, else `ValueError`. (Already in v0.8 line
   329-334.)

If all validations pass: skip `_select_bay_size()` for the axis whose target
is provided; use the provided value as `bay_x` / `bay_y`. The downstream
steps (`_distribute_columns`, `_build_columns`, `_build_wall_segments`) run
unchanged.

### § 3.3 — Mixed mode (one kwarg provided, the other `None`)

```python
g = GridGenerator().generate(env_w, env_d, target_bay_x_m=3.3)
# target_bay_y_m=None → y axis auto-selects as before.
```

Supported. The forced-target path runs for x; the default path runs for y.
This is not used by M7a/M7b in practice (they pass both equal), but the API
is symmetric and shouldn't reject the asymmetric case without reason.

### § 3.4 — Resulting `Grid`

The returned `Grid` carries `bay_x_m == target_bay_x_m` and
`bay_y_m == target_bay_y_m` when those kwargs are given. This is the
caller-observable contract that B-NEW-T2 depends on.

---

## § 4 — Why kwargs (not positional or new method)

Three considered alternatives, with rationale for the chosen option:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Keyword-only `*, target_bay_*_m=None`** (CHOSEN) | Non-breaking; opt-in; explicit at call site; defaults preserve v0.8 behavior. | Slightly longer signature. | ✅ ADOPT |
| B. Positional after the two existing positional args | Shorter to call. | Risk of accidental positional usage breaking semantics; less self-documenting. | ❌ Rejected. |
| C. New method `generate_with_bay_sizes(env_w, env_d, bx, by)` | Strict separation. | Two methods doing nearly the same thing; doubles surface; future M7-like operators would need yet another method. | ❌ Rejected. |

The keyword-only-with-default option is the standard Python "additive API
extension" pattern.

---

## § 5 — Test plan (S40 ship scope)

S40 (this session) ships the following new tests for v0.9:

### § 5.1 — Inside C7's existing test module (`buildemup/tests/test_c07/`)

If the amendment lands, the following test additions go alongside existing C7
tests (or in a new `test_c07_grid_generator_v0_9_target_bay.py` if scope is
preferable):

1. **`test_target_bay_x_m_3_3_uses_provided_value`**: pass
   `target_bay_x_m=3.3`, confirm `grid.bay_x_m == 3.3`.
2. **`test_target_bay_y_m_2_7_uses_provided_value`**: same for y.
3. **`test_both_targets_used`**: both kwargs given.
4. **`test_target_bay_not_in_preferred_set_raises`**: pass
   `target_bay_x_m=3.5` (not in PREFERRED_BAY_SIZES_M); expect `ValueError`.
5. **`test_envelope_too_small_for_target_bay_raises`**: pass envelope
   width 6m with `target_bay_x_m=3.3` (yields 6/3.3 ≈ 1.8 bays, < 2);
   expect `ValueError`.
6. **`test_default_kwargs_match_v0_8_behavior`** (regression sentinel):
   call `generate(8.0, 8.0)` without kwargs, snapshot the result; call
   `generate(8.0, 8.0, target_bay_x_m=None, target_bay_y_m=None)`; assert
   identical (Grid equality).

### § 5.2 — Existing C7 test regression

All current 174 C7 tests must continue passing unchanged. **Zero regressions.**

### § 5.3 — C8/C9/C10 integration regression

The C7 amendment ripples through the cascade. C8/C9/C10 test suites must
continue passing unchanged. Full project test count of **2731 passed / 2
skipped / 0 regressions** is the contract.

---

## § 6 — Out-of-scope (what this amendment does NOT do)

Per Rule 9 (backlog visibility) and Pattern E (scope creep), the following
are explicitly NOT in scope for v0.9:

- **B-NEW-A** (KB-driven bay set post-v1) — orthogonal; widens the bay set
  itself, not the API. Not gated on this amendment.
- **B-237** (cross-platform CI replay matrix) — open backlog from v0.8.
  Unaffected.
- **B-241** (`.wall_segments` lint rule) — unaffected.
- **B-242** (`WallSegment.usable_wall_spans`) — unaffected.
- **Polygonal envelopes** (B-066 et al.) — unaffected. v0.9 amendment
  preserves the rectangular-only assumption identical to v0.8.

---

## § 7 — Open backlog (carry forward UNCHANGED from v0.8)

| ID | Description | Trigger | Status |
|---|---|---|---|
| B-231 | Wall lookup O(1) optimisation for polygonal envelopes | Post B-066 | Open (unchanged) |
| B-235 | WallTag domain split | When 5+ tags exist | Open (unchanged) |
| B-237 | Test-suite modernisation; cross-platform CI replay matrix | Post v1 ship | Open (unchanged) |
| B-241 | CI lint rule for `.wall_segments` direct iteration | Post v1 ship | Open (unchanged) |
| B-242 | `WallSegment.usable_wall_spans` for fragmentation modeling | Post v1 ship | Open (unchanged) |

No new C7 backlog items are created by v0.9.

---

## § 8 — Build-session readiness

After Ramalingam LOCK declaration:

C7 amendment v0.9 build scope (small):
- 1 method signature extension (`GridGenerator.generate`, lines ~316).
- 1 small validation block (preferred-set + at-least-2-bays).
- 1 small dispatch tweak (skip `_select_bay_size` when target provided).
- 6 new tests in `tests/test_c07/`.

Estimated build effort: ~30-45 minutes of code, plus the M7 cascade build
(~3-4 hours, the bulk of S40).

---

## § 9 — Status

- **v0.9 LOCKED at S40 per Ramalingam directive ("Lock it and proceed").**
- **Authority**: Rule 8 — LOCK authority belongs to Ramalingam alone.
- **Build proceeds**: code work begins on the C7 method, then M7 cascade,
  then tests, then end-of-session GAP/AUDIT/INTEGRITY.

---

## § 10 — Rule 9 backlog enumeration

Per Rule 9 (backlog visibility inside spec): every backlog item this
amendment depends on, references, or creates is enumerated below with full
metadata, regardless of whether it pre-existed. § 7 above lists the C7-side
pre-existing backlog. The table below adds the C11a-side cross-component
items relevant to this amendment.

| ID | Description | Origin | Trigger | S40-scope verdict | Effort |
|---|---|---|---|---|---|
| **B-NEW-T2** | M7a/M7b real upstream wiring through C7→C8→C9→C10 cascade. Direct trigger for this amendment. | S39 critique walk F5 (split from monolithic B-NEW-T) | C7 v0.9 LOCKED | **IN-SCOPE for S40** | L (~3-4 days; this amendment unblocks the C7 layer) |
| B-NEW-T1.5 | Promote M6 post-process rotation to real C10 re-run via `WetWallRotationHint`. NOT triggered by C7 v0.9. | S39 Sub-5 scope decision | Future C10 amendment (out-of-scope here) | **OUT-OF-SCOPE** for S40 | M (~2 days, in a future session) |
| B-NEW-T3 | M8 master-floor swap real upstream wiring. Independent of C7 v0.9 (operates on C9/C10 multi-floor briefs). | S39 Sub-5 (split from B-NEW-T) | After B-NEW-T2 lands | **OUT-OF-SCOPE** for S40 | M (~2 days, S41+) |
| B-NEW-Y full | Mutation chain accumulation tests (T2-gated). | S39 Sub-5 partial | After B-NEW-T2 lands | **OUT-OF-SCOPE** for S40 (the partial in S39 covers Tier A) | M |
| B-NEW-W full | Cross-batch cache invalidation (B-NEW-E2-gated). | S39 critique walk F7 | When B-NEW-E2 is filed | **OUT-OF-SCOPE** for S40 | M |
| B-NEW-A | KB-driven bay set post-v1 (widens PREFERRED_BAY_SIZES_M itself). NOT triggered by C7 v0.9 (which uses the existing set). | S39 walk Q11 (W#5) | Post-v1 commercial path | **OUT-OF-SCOPE** for S40 | S |
| B-231, B-235, B-237, B-241, B-242 | Pre-existing C7 backlog (unaffected). | C7 v0.7 / v0.8 history | Various | UNCHANGED | various |

**Summary**: this amendment IS the v0.9 surface-level prerequisite for one
single backlog item — **B-NEW-T2**. All other related items are explicitly
out-of-scope for S40 per Pattern E (scope creep mid-build).

---

**End of C7 Amendment v0.9 PROPOSED.**
