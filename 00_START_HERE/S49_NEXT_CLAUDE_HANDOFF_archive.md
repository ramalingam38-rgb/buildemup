# NEXT_CLAUDE_HANDOFF.md — for S50

**Author:** Claude (S49)
**Date:** 2026-05-15
**Successor session:** S50

You are the next Claude. Read this first. The full session transcript
is the source of truth; this document is the navigation index.

---

## Where things stand at S49 close

### Track 3 canonical ledger

```
SHIPPED:  C1  C2  C7  C9  C10  C11a  C11b  C12  C13  C14  C15  (15/17)
          + C16 Sub-1 (foundational layer — 6 files, NOT v1.0 yet)
PENDING:  C16 Sub-2 onward → C16 v1.0 LOCK    (phases α-ζ)
          C17                                  (not specced)
```

### C16 Sub-1 SHIPPED files
- `buildemup/components/c16/__init__.py` — full module re-export
- `buildemup/components/c16/versioning.py` — pinned constants for v0.5 LOCK
- `buildemup/components/c16/errors.py` — two-tier hierarchy
- `buildemup/components/c16/contracts.py` — upstream contract types + enums
- `buildemup/components/c16/config.py` — RenderingConfig + R31a
- `buildemup/components/c16/cache_keys.py` — canonical JSON + R32 signatures
- `buildemup/components/c16/schema.py` — DualDrawingBundle + R19-R34 enforcement

255 C16 tests + 264 C15 tests = **519 / 519 cumulative passing.**

---

## What you (S50) almost certainly need to do

### Probable scope: C16 Sub-2 — Phase α (Geometric envelope assembly)

Phase α takes the upstream SelectionResult + jurisdiction profile, traverses
the geometry, computes the deterministic LocalBuildingFrame orientation per
R29 hierarchy (4-step), produces shared FloorGeometry tuples with stable
ElementIdentity hashes, and surfaces OrientationLock plausibility (R29d).

**Files to add in Sub-2:**
- `buildemup/components/c16/phases/__init__.py`
- `buildemup/components/c16/phases/alpha_envelope.py`
- `tests/test_c16/test_c16_phase_alpha.py` (target ≥ 25 tests)
- Optionally: `buildemup/components/c16/orientation.py` (orientation hierarchy
  computation) if it becomes too large to fit in alpha_envelope.py.

**Required-to-implement at Sub-2:**
- R7b: stable IDs via `compute_element_identity` actually CALLED at element
  construction time (not just available as a helper).
- R29 hierarchy steps 1-4 computing the 4 candidate orientations.
- R29d: OrientationLock plausibility — compare lock against the 4 candidates
  within EPSILON_ANGLE_DEG; raise OrientationLockMismatchError on miss.
- R19: coordinate-bounds check at every emitted element via
  `effective_plot_bounds` / `effective_building_bounds`.
- R33: emit ElementIdentity with `identity_generation = C16_IDENTITY_GENERATION`
  uniformly across the bundle.

### Required pre-build discipline (Rule 1 + Rule 11)

1. Open the existing C16 v0.5 LOCKED spec at
   `02_specs_chronological/S47_C16_specs/` (read v0.1 + v0.2-v0.5 deltas) BEFORE coding.
2. Read the S49 three-check results at `05_integrity_check/S49_three_check_results.md`
   for the inventory of what's already deferred to your session.
3. NEVER code Phase α without a written Sub-2 spec (or explicit scope note
   ratifying that you're implementing already-LOCKED v0.5 invariants).
4. Mandatory web search per Rule 11 — verify orientation hierarchy claims
   against IFC IfcLocalPlacement + Revit interop literature (already done
   in S49 — re-check your specific Phase α claims).
5. Apply pre-touch inventory (Rule 10.6.1) before starting.

---

## What you should NOT do at S50

1. **Do NOT** silently break the v0.5 LOCK contracts. Sub-1's schema.py
   types are LOCKED at the field-level for top-level types. Sub-envelope
   SKETCHES are intended to gain fields (additive — schema MINOR bump
   per R9). They are NOT intended to lose or rename fields.
2. **Do NOT** bump `C16_IDENTITY_GENERATION`. That's a v(N+1) MAJOR-bump
   ceremony per R33a, not a silent change.
3. **Do NOT** introduce UUIDs, system clock reads, locale reads, or
   environment-variable reads into any element-construction path (R7d).
4. **Do NOT** assume the schema.py SKETCH sub-envelopes are final shapes.
   `B-C16-ENVELOPE-SCHEMA-LOCK` (LOCK-mandatory at C16 v1.0) is when full
   pinning happens — likely Sub-3 or Sub-4 once Phase β/γ/δ have surfaced
   the actual required fields.

---

## Standing rules (re-read every session)

1. **Rule 1 — spec-first.** Never code before a LOCKED spec or explicit
   spec-ratification note. Draft → critique → lock → code.
2. **Rule 7 — critique-handling.** Web search MANDATORY every critique
   walk (≥ 1 search per round). Verdicts: VALID / BACKLOG / MISFRAMED /
   DOCUMENTED / SPEC-AMENDMENT. End with backlog roll-up.
3. **Rule 8 — LOCK authority.** Only Ramalingam declares LOCK. Always
   present as `vN PROPOSED. PENDING Ramalingam LOCK adjudication.`
4. **Rule 9 + 9.2 — backlog visibility.** Every backlog item in spec § 12.
   File VALID-BUT-BACKLOG items as B-NNN entries in
   `04_backlog/v0_2_backlog.md` immediately, without asking permission.
5. **Rule 10 — handoff bundle structure.** 10-dir layout. Numbering
   continues. New code dirs mirror prior code dirs.
6. **Rule 10.6 — three-check protocol.** GAP / AUDIT / INTEGRITY,
   documented in `05_integrity_check/`. Mandatory before every zip.
7. **Rule 10.6.1 — pre-touch inventory.** Before claiming credit, inventory
   the working tree at session start.
8. **Rule 10.7 — handoff timing.** When Ramalingam says "hand off,"
   first response is status block + three-check PLAN. Bundle only after
   confirmation.
9. **Rule 11 — vigorous self-analysis + web research.** Lead with worst
   issues. Bar = "next consumer can use output," not "tests pass."
10. **LOCK-trigger protocol.** When Ramalingam says "lock vN", process
    all deferred PROPOSED amendments + close v1.0-LOCK-mandatory backlog
    items + re-run three-check before surfacing vN.LOCK-CANDIDATE.
11. **Single-zip handoff rule.** Every handoff is ONE zip. Never surface
    loose files alongside.
12. **Cumulative-handoff rule.** Every handoff is cumulative. Clone prior
    session's complete bundle, layer this session's additions on top.
    Numbering continues across sessions.

---

## Five patterns to avoid (every session)

| Pattern | Description | S49 instance |
|---|---|---|
| A — fix-as-bandage | Patching a symptom not the cause | Avoided: canonical JSON `_is_already_canonical` was a flawed optimization — REMOVED entirely rather than patched |
| B — building-without-wiring | Shipping code with no caller / no integration | Avoided: every Sub-1 type re-exported via `__init__.py`; smoke-tested |
| C — scores-without-truth | Numbers without source authority | Avoided: AttestedValue R22 enforced for every authority kind |
| D — rules-on-rules | Rule additions without governance | Avoided: no new amendments to v0.5 LOCK during build |
| E — scope-creep-mid-build | Expanding the build scope mid-session | Notable: "Complete c16 build fully" was correctly scoped as Sub-1 fully (6 files), NOT full v1.0 — explicit reasoning in transcript. |

---

## Files of interest in this bundle

| Path | What it tells you |
|---|---|
| `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` | This file |
| `01_master_doc/` | Project narrative |
| `02_specs_chronological/S47_C16_specs/` | C16 v0.5 LOCKED spec (read v0.1 + v0.2-v0.5 deltas) |
| `02_specs_chronological/S49_C15_LOCK/` | C15 v1.0 LOCK ratification record |
| `03_code_chronological/S49_C15_LOCKED_C16_Sub1_SHIPPED/` | Code shipped this session |
| `04_backlog/v0_2_backlog.md` | Backlog (S49 added items prefixed S49-) |
| `05_integrity_check/S49_three_check_results.md` | Three-check protocol output (READ THIS FIRST) |
| `06_upstream_codebase/` | Reference C7/C9/C10/C12/C13/C14 (read-only) |
| `08_session_transcripts/` | S48 transcript (S49 transcript when it arrives) |

---

## Open questions to surface to Ramalingam at S50 start

1. Confirm Sub-2 scope: Phase α only, or Phase α + part of Phase β?
2. Confirm whether Sub-2 spec is required (Rule 1) or whether implementing
   already-LOCKED v0.5 invariants counts as ratified scope.
3. Any pre-S50 critique walks intended on the Sub-1 shipped code?
4. Should the `B-C16-ENVELOPE-SCHEMA-LOCK` decision (sub-envelope full
   pinning) happen DURING Sub-2/3 build, or stay deferred to v1.0 LOCK
   adjudication?

---

End of NEXT_CLAUDE_HANDOFF for S50.
