# S56 — Bucket C deferrals (require user decision before touching)

**Authored:** S56, May 16, 2026, Ramalingam + Claude
**Context:** Bucket C was attacked in S56 in parallel with the B-238 architect engagement packet. 7 items closed in-session. **6 items deferred** — listed here with the rationale for each. Each item is technically Bucket C "polish" but carries non-trivial risk that warrants a human-in-the-loop decision before action.

---

## Closed in S56 (for record)

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | B-S53-PROVISIONAL-CLEANUP | ✅ | Deleted `c10/__init__.PROVISIONAL_S53.py` + cleaned README pointer |
| 2 | B-060 | ✅ | Fixed `tests/e2e/__init__.py` docstring "7 files" → "8 files" |
| 3 | B-099 | ✅ | Hid Vastu FULL tier in `brief_form.html`; backend still accepts the value (HTML-commented with explicit B-099 + v1.1 reinstate breadcrumb) |
| 4 | B-057 | ✅ | Added `case-trace` element to `case.html`; populated trace_id in `case.js` on success render |
| 5 | B-059 | ✅ | Added dedicated `PER_CASE_LIMIT_REACHED` success message branch in `done.js` |
| 6 | B-241 | ✅ | New `scripts/wall_segments_lint_check.py` with allowlist + UTF-8-safe output + docstring-aware scrubbing. PASSes today. |

---

## Deferred — requires user decision

### Cluster A — LOCKED spec wording (B-015 / B-021 / B-056)

**Status:** NOT TOUCHED in S56.

**Why deferred:** All three target text inside LOCKED spec files. Editing a LOCKED spec in place would break the project's LOCK contract convention (LOCKs are immutable; amendments ship in a new versioned file).

The original backlog entries for these items explicitly say:
- B-015: "Trigger: next parent-spec revision (alongside B-021)"
- B-021: "Trigger: next parent-spec revision (alongside B-015)"
- B-056: "Formalise § 1.2 (ii) ... at next S8 spec-amendment cycle"

**Recommendation:** Bundle all three (plus any new wording-fix backlog items that surface in B-238 architect review) into the next C3a parent-spec amendment (call it `C3a_v0_2_2_AMENDMENT_LOCKED.md`). Authoring that amendment is ~2 hours of work but is best done after B-238 feedback arrives — the architect may surface additional spec-wording issues that should land in the same amendment.

**Decision needed from user:** "Wait for B-238 feedback and bundle into one C3a amendment" (recommended) OR "Author the amendment now in S57 and bundle B-238 findings later."

---

### Cluster B — B-S53-C7-LEGACY-DECISION (951-LOC monolithic file)

**Status:** NOT TOUCHED in S56.

**Why deferred:** `06_upstream_codebase/buildemup/components/c07_structural_grid.py` is the 951-LOC pre-amendment monolith. The current modular `c07/` folder supersedes it. The backlog gives two options:
- (a) Delete the legacy file
- (b) Keep with a deprecation breadcrumb

Grep found **9+ importers** referencing `c07_structural_grid` (test files mostly, plus `examples/`, `api/feasibility_endpoint.py`). Deletion would require updating each import; keeping requires a clean deprecation note.

**Decision needed from user:** "Delete (a)" — requires Claude to update 9+ import sites — OR "Keep with deprecation breadcrumb (b)" — purely additive comment at top of file.

**Recommendation:** Option (b). The legacy file isn't doing harm sitting there; cost of deletion is high (test surface touched); cost of keeping is one comment.

---

### Cluster C — B-S53-C1-CONSOLIDATE (fold `c01_brief_capture.py` into `c01/`)

**Status:** NOT TOUCHED in S56.

**Why deferred:** `c01_brief_capture.py` is the legacy hybrid orchestrator. Grep found **36+ importers** across `api/`, `domain/`, `tests/`, `examples/`. Consolidating the file into `c01/` would require updating every import path. The backlog itself notes "If anything in api/ or tests/ imports `c01_brief_capture` directly, those imports must be updated" — confirmed: many do.

**Effort assessment:** Medium-Large. ~36 file edits + test re-run for each. Risk of subtle behavior drift if the legacy orchestrator has API differences from the modular folder.

**Recommendation:** Defer to a dedicated session AFTER deploy or until something concrete breaks. Until then, the duplication is documentation overhead but not functional debt.

---

### Cluster D — B-S53-C2-SPEC-MOVE (move C2 spec docs to canonical path)

**Status:** NOT TOUCHED in S56.

**Why deferred:** `06_upstream_codebase/buildemup/docs/` contains C2 spec docs that should live in `02_specs_chronological/` per Rule 10. The move itself is trivial (~3 file moves). The risk: if any code reads spec docs from the `docs/` path (e.g., embedded help / link-checker / spec-drift-CI), the move breaks the reader.

**Recommendation:** A one-session pass that:
1. Greps for path references to `buildemup/docs/component2/`
2. Moves the files
3. Updates any pointers
4. Re-runs the bundle integrity check

~30 min, but worth checking before pulling the trigger. **Decision needed:** "Do this in S57" or "After B-238."

---

### Cluster E — B-S53-TEST-DIRS-MISSING (reorganize C4/C5/C6/C8/C9 test files)

**Status:** NOT TOUCHED in S56.

**Why deferred:** Currently C3b/C10/C11a/C11b/C12/C13/C14 use per-component `tests/test_cNN/` directories. C4/C5/C6/C8/C9 still use flat `tests/test_cNN_*.py` files.

**Risk:** pytest's test discovery is layout-sensitive. Moving files mid-run-bundle (4,468 tests passing today) risks accidentally orphaning fixtures, breaking `conftest.py` resolution, or causing duplicate test collection if both flat and per-dir layouts coexist mid-move.

**Effort:** Small-medium per component (~20-40 min each × 5 = ~2-3 hours total). But high-risk if done without a full sweep verify after each step.

**Recommendation:** Defer until BOTH (a) the master-orchestrator wiring is decided, since the test layout should mirror the production layout, AND (b) Bucket A is fully closed (post-B-238). Doing this now provides marginal benefit and could create accidental green-test regressions.

---

### Cluster F — B-245 (Rule 11 maturity-weighted scoring extension)

**Status:** NOT TOUCHED in S56.

**Why deferred:** Listed as "meta-process tooling, master_doc work, not spec." This is essentially a project-management instrumentation enhancement — useful, but not user-facing, not blocking, and substantial enough that it deserves its own session. Estimated effort: ~half-session.

**Recommendation:** Slot into a later session when Bucket A is closed and the deferred v1+ roadmap (Option C) is being authored — the maturity scoring will naturally surface inside that roadmap document anyway.

---

## Summary

| Cluster | Items | Recommended session |
|---|---|---|
| A — Spec wording | B-015, B-021, B-056 | S57+, bundled with B-238 architect feedback |
| B — C7 legacy | B-S53-C7-LEGACY-DECISION | Decision needed; recommend "keep + breadcrumb" |
| C — C1 consolidate | B-S53-C1-CONSOLIDATE | Defer until forced by deploy / breakage |
| D — C2 spec move | B-S53-C2-SPEC-MOVE | S57+ (30-min pass) |
| E — Test dirs | B-S53-TEST-DIRS-MISSING | Post-B-238, post-Bucket A close |
| F — Maturity scoring | B-245 | Slot into roadmap-authoring session (Option C) |

**Net:** 7 Bucket C items closed in S56, 6 deferred with rationale. Total Bucket C remaining: 6 (all with clear, low-risk paths to closure when scheduled).
