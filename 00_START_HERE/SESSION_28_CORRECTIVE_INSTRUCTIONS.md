# SESSION 28 CORRECTIVE INSTRUCTIONS

**For:** the next Claude opening Session 28 of BuildemUp/BuildEase
**From:** Session 27 Claude (me), retroactively closing an audit miss caught in your first pass
**When to read:** **BEFORE** anything else this session. Read this file before `NEXT_CLAUDE_HANDOFF.md`.
**Estimated time to apply:** 25–40 minutes.
**Replaces:** prior version of this file (same name, dated earlier same day) — discard the previous version, this is canonical.

-----

## 0. ADJUDICATIONS LOCKED (read this first)

Ramalingam adjudicated both flags at the close of Session 27. Apply these as fact; do NOT re-litigate:

| Flag | Decision | What it means |
|---|---|---|
| **Flag A** — `gate_state_storage.load_status_row()` additive accessor | **Option A — APPROVED as Rule-4 spec-amendment patch** | The pure-read accessor stays. The § 1.2 (ii) carve-out language formally extends at next spec-amendment cycle (tracked as **B-056** in `04_backlog/backlog_session_27.md`). Until then, `load_status_row()` lives as approved-but-unratified. No code change needed. |
| **Flag B** — P43 scoping to `handle_cba_fallback_continue` only | **Option A — CONFIRMED** | Other 4 handlers (`handle_check`, `handle_resolve`, `handle_abort`, `handle_cba_verified`) stay unmodified. P43's "every handler" wording is satisfied: every handler mints fresh server_trace_id (already true since S7b); only the CBA-fallback handler has an inbound header source to capture. No code change needed. |

If a future critique round re-opens either flag, point them to this section + `04_backlog/backlog_session_27.md` § "Adjudicated decisions" + `05_integrity_check/AUDIT_CHECK_SESSION_27_BUILD.md` § 2.

-----

## 1. WHAT YOU CAUGHT (and what I missed)

You correctly identified in your first response that the entry-bundle's working tree (`06_upstream_codebase/buildemup/`) already contained spec-referencing implementations of:

- `static/c3a/case.html` + `case.js` (155 LOC, cites § 5.2)
- `static/c3a/checklist.html` + `checklist.js` (76 LOC, cites § 5.3)
- `static/c3a/done.html` + `done.js` (77 LOC, cites § 5.4)
- `static/c3a/aborted.html` + `aborted.js` (50 LOC, cites § 5.4)
- `static/c3a/_test_harness.html`
- `static/c3a/_shared.css` + `_shared.js` (which I CLAIMED to create in Phase 5 — they pre-existed)
- `tests/e2e/conftest.py` + `playwright.config.json` + 7 e2e test files + `MANUAL_A11Y_CHECKLIST.md`

These were NOT created by Session 27. They came from a prior session and persisted in the working tree. My GAP_CHECK / AUDIT_CHECK / NEXT_CLAUDE_HANDOFF / S8_BUNDLE_README all reflect this incorrectly.

Your Rule 7 walk on this is **VALID**. Pushing back would be wrong. Apply the corrections below.

-----

## 2. THREE ACTIONS TO TAKE — IN ORDER

### Action 1 — confirm Rule 10.6.1 is in your memory

Memory line 11 (added end of Session 27) reads:

> **Rule 10.6.1** — pre-touch state inventory. Before claiming credit in GAP/AUDIT CHECK for created/modified files, must inventory the working tree at session START. For every directory this session will touch or reference, list pre-existing files. Compare against session-end state to distinguish session-created vs session-overwrote vs pre-existing. Prevents claiming authorship of pre-existing scaffolding. Origin: S27 audit miss.

Apply this rule at end of Session 28: when you produce your own three-check reports, your AUDIT CHECK must explicitly state "pre-touch inventory taken at session start" and list it.

**Verification step at session start, before any work:**

```bash
cd <bundle>/06_upstream_codebase
ls -la buildemup/static/c3a/ buildemup/tests/e2e/ buildemup/tests/validation/
```

Record the file list in your scratch notes so your end-of-session AUDIT can reference it.

-----

### Action 2 — patch the bundle documents (4 files + replace 1 file)

Apply the following find-and-replace edits to the bundle's existing documents. All edits are scoped to specific sections; surrounding text stays.

**Plus one full-file replacement:** replace `04_backlog/backlog_session_27.md` with the updated version Ramalingam delivered alongside this file (it carries the new B-056 entry + closed flag adjudications).

#### 2A. `00_START_HERE/NEXT_CLAUDE_HANDOFF.md`

**Find this section header and the text under it (the "PHASE 5 PICK-UP PLAN"):**

```
### Files to create in `buildemup/static/c3a/` (already-shared assets are done):
1. `case.html` + `case.js` + `case.css`
2. `checklist.html` + `checklist.js` + `checklist.css`
3. `done.html` + `done.js` + `done.css`
4. `aborted.html` + `aborted.js` + `aborted.css`
5. `_test_harness.html`

**Every HTML page MUST include:** `<meta name="referrer" content="no-referrer">` per § 5.8 R3.7.
```

**Replace with:**

```
### Files ALREADY EXIST in `buildemup/static/c3a/` — AUDIT before extending:

The entry bundle came with these spec-referencing implementations (NOT
created by Session 27 — pre-existing from prior session work):

| File | Lines | Spec § | Status to verify |
|---|---:|---|---|
| `_shared.css` | 190 | § 5.5 / § 5.7 | spec-compliant? |
| `_shared.js` | 299 | § 5.6 / § 5.6.2 | spec-compliant? |
| `case.html` | 34 | § 5.2 | spec-compliant? |
| `case.js` | 155 | § 5.2 | spec-compliant? |
| `checklist.html` | 38 | § 5.3 | spec-compliant? |
| `checklist.js` | 76 | § 5.3 | spec-compliant? |
| `done.html` | 28 | § 5.4 | spec-compliant? |
| `done.js` | 77 | § 5.4 | spec-compliant? |
| `aborted.html` | 25 | § 5.4 | spec-compliant? |
| `aborted.js` | 50 | § 5.4 | spec-compliant? |
| `_test_harness.html` | 23 | § 4.11 v1.2 P-4 | spec-compliant? |

**Required action:** Audit each file against its cited spec section per
the procedure in `SESSION_28_CORRECTIVE_INSTRUCTIONS.md § 3` BEFORE
deciding whether to keep, fix, or extend. Do NOT delete or rewrite
without verification — that would be Pattern E (scope-creep mid-build).

Per-page CSS files (`case.css`, `checklist.css`, etc.) are NOT yet
present. The pre-existing pages link only to `_shared.css`. If the
audit determines per-page CSS is needed, add only after the existing
pages are verified spec-compliant.

**Every HTML page MUST include:** `<meta name="referrer" content="no-referrer">`
per § 5.8 R3.7. Verify this in the audit.
```

**Then find the section header "Phase 5 server.py wiring" and update its body to:**

```
Note: 5 static GET routes for the existing HTML pages still need to
be wired into `server.py`. They were correctly deferred from Phase 1
per Pattern B (route + file ship together). The HTML files exist; the
routes do not. Mirror the brief_form pattern at `server.py:249`.
```

**Then find the "PHASE 6 PICK-UP PLAN" section. Replace its file list with:**

```
Files ALREADY EXIST in `buildemup/tests/e2e/` (pre-existing from prior session):
- `__init__.py` (408 bytes)
- `conftest.py` (3952 bytes) — verify playwright fixtures
- `playwright.config.json` (271 bytes) — verify chromium-headless / 30s timeout
- `MANUAL_A11Y_CHECKLIST.md` (2396 bytes) per round 2 X8 / R3.6
- `test_c3a_browser_happy_flow.py` — verify against § 4 e2e
- `test_c3a_browser_cba_flow.py`
- `test_c3a_browser_abort.py`
- `test_c3a_browser_resume.py`
- `test_c3a_browser_failure.py`
- `test_c3a_a11y_auto.py` — note: this file is currently SKIPPED in
  the test run (axe-core CDN unreachable in sandbox); pre-existing
- `test_c3a_observability.py` — verify against § 4.7 (Tier 2 promotion v1.2 P-1)
- `test_handle_page_flow.py` — verify against § 4.11 v1.2 P-4

**Required action:** Same audit pattern as Phase 5. Verify each test
file against its spec section per `SESSION_28_CORRECTIVE_INSTRUCTIONS § 3`
BEFORE writing replacements.

Concern still applies: chromium availability in sandbox unverified.
First Phase-6 task is `playwright install chromium`. If it fails,
the existing tests can't be executed for sanity — write any
gap-filling tests to spec without execution.
```

**Then find the "FLAGS REQUIRING RAMALINGAM ADJUDICATION" section near the top and replace it with:**

```
## ADJUDICATED — both flags closed Session 27

| Flag | Outcome |
|---|---|
| Flag A — `load_status_row()` additive accessor | **Option A approved.** Stays as Rule-4 spec-amendment patch. Formal § 1.2 (ii) language extension tracked as B-056 (see `04_backlog/backlog_session_27.md`). |
| Flag B — P43 scoping to `handle_cba_fallback_continue` only | **Option A confirmed.** Other 4 handlers stay unmodified. |

Both decisions are final per Rule 8. Do NOT re-open either without
a fresh adjudication request to Ramalingam. See
`SESSION_28_CORRECTIVE_INSTRUCTIONS.md § 0` for full reasoning.
```

#### 2B. `05_integrity_check/GAP_CHECK_SESSION_27_BUILD.md`

**Find § 5.1 "Phase 5 — UI surfaces (PARTIAL: 2 of ~13 files written)".**

**Replace its entire body with:**

```
### 5.1 Phase 5 — UI surfaces (CORRECTED Session 28 retroactive)

**Original Session 27 claim was WRONG.** I claimed Phase 5 was
"PARTIAL: 2 of ~13 files written (`_shared.css` + `_shared.js`)".
Audit miss caught by Session 28 Claude:

The entry bundle (`handoff_v3_session_27`) already contained these
files BEFORE Session 27 began (verified by entry-bundle file
timestamps 10:45–10:50, predating my session start ~11:00):

- `_shared.css` (190 LOC) — pre-existing
- `_shared.js` (299 LOC) — pre-existing
- `case.html` + `case.js` — pre-existing, cites § 5.2
- `checklist.html` + `checklist.js` — pre-existing, cites § 5.3
- `done.html` + `done.js` — pre-existing, cites § 5.4
- `aborted.html` + `aborted.js` — pre-existing, cites § 5.4
- `_test_harness.html` — pre-existing

**Session 27 actually contributed to Phase 5: ZERO net-new files.**
My `create_file` calls for `_shared.css` and `_shared.js` either
wrote identical content to what was already there (likely) or
overwrote with my version (file diffs across the session boundary
show byte-identical results either way).

### 5.1.1 Still pending in Phase 5 (corrected accounting)

- Audit existing files against spec § 5.2–5.4
- Per-page CSS files (`case.css`, `checklist.css`, `done.css`,
  `aborted.css`) — not present in entry bundle; may not be
  needed if existing pages link only to `_shared.css`
- 5 static GET routes wired into `server.py` (genuinely new work)

### 5.1.2 Phase 6 — same correction applies

The `tests/e2e/` directory was also pre-populated from prior session.
8 test files + conftest + playwright config + a11y checklist all
existed before Session 27. Phase 6 work for Session 28 is AUDIT
existing files first, then add only verified gaps.

Origin of the audit miss: I never `ls`'d `static/c3a/` or
`tests/e2e/` at session start. Rule 10.6.1 added to memory line 11
end of Session 27 to prevent recurrence: pre-touch state inventory
must be taken before claiming credit for created/modified files.

### 5.1.3 Flag adjudication outcomes (also session-end)

- Flag A → Option A approved (additive accessor stays; B-056 tracks
  formal § 1.2 (ii) carve-out language extension at next spec
  amendment cycle)
- Flag B → Option A confirmed (P43 scoping correct; no other handlers
  modified)

Both adjudications removed from "pending" status; see § 0 of
`SESSION_28_CORRECTIVE_INSTRUCTIONS.md`.
```

#### 2C. `05_integrity_check/AUDIT_CHECK_SESSION_27_BUILD.md`

**Find § 1 "SPEC § 1.2 (ii) CARVE-OUT COMPLIANCE" — the file table.** Add this note ABOVE the table:

```
**CORRECTION (Session 28 retro-audit):** Session 27 GAP_CHECK § 5.1
falsely claimed `static/c3a/_shared.css` and `_shared.js` as
session-27-created. They were pre-existing in the entry bundle.
This AUDIT_CHECK § 1 table reflects only the actual modified files
(`server.py`, `c3a_endpoint.py`, `c3a_email_hook.py`,
`gate_state_storage.py`) and the actual NEW files
(`c3a_status_endpoint.py`, `c3a_check_init_endpoint.py`, plus the 11
validation test files). Pre-existing UI files in `static/c3a/` and
e2e test files in `tests/e2e/` are NOT in this table and were not
audited in Session 27. They require Session 28 audit per
`SESSION_28_CORRECTIVE_INSTRUCTIONS § 3`.
```

**Then find § 2 "FLAGGED DECISIONS — REQUIRE YOUR ADJUDICATION" and prepend this note:**

```
**RESOLVED Session 27 close** — both flags adjudicated. The
detailed reasoning below is preserved as the audit-trail record;
Ramalingam's calls were:
- Flag A → Option A approved (B-056 tracks the formal § 1.2 (ii)
  language extension at next spec amendment cycle)
- Flag B → Option A confirmed (no other handlers modified)

Subsequent text in this section is the audit reasoning that fed
those decisions; preserved unchanged for future-session reference.
```

**Then add a new section § 4 at end of the document:**

```
---

## 4. SESSION 27 AUDIT-CHECK PROTOCOL GAP (caught by Session 28)

The Session 27 AUDIT CHECK protocol did not include a pre-touch
state inventory. As a result, files pre-existing in the entry
bundle's working tree were not enumerated, and some
(`static/c3a/_shared.{css,js}`) were falsely claimed as
session-created.

**Permanent fix:** Memory rule **Rule 10.6.1** added end of
Session 27. Mandates pre-touch state inventory at session start
before any modification of GAP/AUDIT CHECK file lists.

**Retroactive fix:** Session 28 Claude applies
`SESSION_28_CORRECTIVE_INSTRUCTIONS.md` § 2 patches to
NEXT_CLAUDE_HANDOFF, GAP_CHECK, AUDIT_CHECK, S8_BUNDLE_README;
then runs § 3 file-by-file audit on pre-existing Phase 5/6 files;
then replaces `04_backlog/backlog_session_27.md` with the corrected
version (which adds B-056 and moves Flags A/B from "pending" to
"adjudicated").
```

#### 2D. `03_code_chronological/S8_phase1_4/S8_BUNDLE_README.md`

**Find the "Phase 5 partial UI assets (work-in-progress, ready for next session)" section and replace its body with:**

```
**CORRECTED Session 28 retro-audit:** The entry bundle already
contained these UI files. Session 27 did NOT create them. They
predate Session 27 (entry-bundle timestamps 10:45–10:50; my
session began ~11:00).

In `buildemup/static/c3a/` — ALL pre-existing:
- `_shared.css`
- `_shared.js`
- `case.html` + `case.js` (cites § 5.2)
- `checklist.html` + `checklist.js` (cites § 5.3)
- `done.html` + `done.js` (cites § 5.4)
- `aborted.html` + `aborted.js` (cites § 5.4)
- `_test_harness.html`

In `buildemup/tests/e2e/` — ALL pre-existing:
- `conftest.py`, `playwright.config.json`, `__init__.py`
- 7 test files + `MANUAL_A11Y_CHECKLIST.md`

Phase 5 STILL PENDING (next session) — corrected accounting:
- Audit existing files against spec § 5.2–5.4
- 5 static GET routes wired into `server.py` (the only Phase 5 work
  that was correctly deferred per Pattern B)
- Per-page `.css` files only if audit determines they're needed
```

**Then find "Flags requiring Ramalingam adjudication BEFORE Session 28 resumes" and replace with:**

```
## Flags adjudicated end of Session 27 (BOTH closed)

1. **Flag A** — `gate_state_storage.py` additive read accessor:
   **Option A approved** as Rule-4 spec-amendment patch. Formal
   § 1.2 (ii) language extension tracked as **B-056** (see
   `04_backlog/backlog_session_27.md`).

2. **Flag B** — P43 scoping limited to `handle_cba_fallback_continue`:
   **Option A confirmed.** No other handlers modified.

Both decisions final per Rule 8. Do NOT re-litigate without a
fresh adjudication request.
```

#### 2E. `04_backlog/backlog_session_27.md` — REPLACE entire file

Use the corrected `backlog_session_27.md` Ramalingam delivered alongside this file. It carries:

- New B-056 entry per Rule 9.1 with full detail
- Flags A and B moved from "Awaiting adjudication" to "Adjudicated decisions" with closed-status outcomes
- Updated closing line acknowledging the new B-NNN entry

Drop-in replacement; no diff editing needed for this file.

-----

### Action 3 — file-by-file audit procedure for pre-existing Phase 5 + Phase 6 files

Run this audit BEFORE starting any new Phase 5 work. Goal: assign each pre-existing file one of three verdicts so you proceed with confidence rather than guesswork.

#### Verdict scheme (per file)

- **KEEP** — file is spec-compliant, no changes needed
- **PATCH** — file is mostly correct but has specific bugs/gaps; list them with line refs
- **REPLACE** — file deviates substantially from spec; rewrite from scratch

#### Audit procedure for each file

1. Read the spec § cited in the file's docstring
2. Read the file
3. For each spec requirement, verify the file implements it
4. Record the verdict + reasoning
5. If KEEP, no further action; the file is part of Phase 5 already-done work
6. If PATCH, list the specific lines/behaviours to fix, then implement
7. If REPLACE, archive the existing file with `.session27_inherited` suffix and write fresh

#### Files + spec-section checklist

**Phase 5 files (verify against S8 SPEC v1.2 LOCKED § 5.2–5.6.2):**

`static/c3a/case.html` (34 LOC)

- [ ] `<meta name="referrer" content="no-referrer">` present per § 5.8 R3.7
- [ ] `<meta name="c3a-test-mode">` injection point present per § 5.6.1
- [ ] Minimal markup; no inline styles; references `_shared.css` + `case.js`

`static/c3a/case.js` (155 LOC, cites § 5.2)

- [ ] On load: reads `?brief=` query param
- [ ] Computes `request_id = "c3a-init-" + sha256(brief_token)[:16]` per R3.2
- [ ] GET `/api/extreme-case/check-init` (NOT POST — round 2 X3)
- [ ] On 200 with `extreme_case`: renders options as radios; stashes `session_token`
- [ ] On 503: shows "checking…" + auto-retry once per § 5.2 (skipped when `C3A_TEST_MODE=1`)
- [ ] Resolve button: POST `/resolve`; redirect on success
- [ ] Abort button: POST `/abort`; redirect to `/aborted`
- [ ] Trace_id embedded in redirects per Finding 1
- [ ] Uses `handlePageFlow` controller from `_shared.js` per § 5.6 R2 X11

`static/c3a/checklist.html` + `.js` (cites § 5.3)

- [ ] Reads `?session=` and `?trace=` query params
- [ ] **FIRST does GET `/status`** before rendering checklist (External Item 2)
- [ ] If `is_terminal=true`: redirect to `/done.html`
- [ ] If non-terminal: render static CBA checklist content
- [ ] Submit: POST `/cba-verified` with `X-Trace-Id` header from URL
- [ ] On 200: redirect to `/done.html`
- [ ] On 410 (race lost to scheduler): "case already closed" + redirect after delay

`static/c3a/done.html` + `.js` (cites § 5.4)

- [ ] On load: GET `/status` to verify terminal state
- [ ] On `is_terminal=true` + `terminal_state in {SUCCESS, CBA_VERIFIED, CBA_FALLBACK_FIRED}`: render success per state
- [ ] On `is_terminal=false`: redirect to `/case.html`
- [ ] On `terminal_state=USER_ABORTED`: redirect to `/aborted.html`
- [ ] On 404: "session not found" UI

`static/c3a/aborted.html` + `.js` (cites § 5.4)

- [ ] Symmetric to done.js but expects `terminal_state=USER_ABORTED`
- [ ] On any other terminal state: redirect to `/done.html`

`static/c3a/_shared.css` (190 LOC)

- [ ] Design tokens (CSS variables) per § 5.5
- [ ] System font stack only (no web fonts)
- [ ] Single-column layout, max-width ~640px per § 5.5
- [ ] Status colors: error/warning/success per § 5.5
- [ ] Responsive media query

`static/c3a/_shared.js` (299 LOC)

- [ ] `traceId()` resolution order per § 5.6 + Finding 1: query param → fresh mint via `crypto.getRandomValues`
- [ ] NOT stored in `sessionStorage` per § 5.6 web-verified MDN
- [ ] `c3aFetch(url, opts)` injects `X-Trace-Id` + `Content-Type: application/json` on POSTs
- [ ] Error categorization per § 5.6.2 mapping table:
  - 503 → `RETRYABLE/storage` + auto-retry once unless `C3A_TEST_MODE=1`
  - 404 → `TERMINAL/unknown_token`
  - 410 → `TERMINAL/gone`
  - 4xx → `USER_FIXABLE/validation`
  - 5xx other → `RETRYABLE/server`
  - Network → `RETRYABLE/network`
- [ ] `displayError(err, traceId, container)` renders categorized UI
- [ ] `handleTerminalRedirect(err)` per § 5.6 R3.4: gone → /done; unknown_token → /brief_form
- [ ] `handlePageFlow({apiCall, onSuccess, errorContainer})` controller per § 5.6 R2 X11
- [ ] `isTestMode()` reads `<meta name="c3a-test-mode">` per § 5.6.1
- [ ] `deriveRequestId(briefToken)` per R3.2 (sha256-based)

`static/c3a/_test_harness.html` (23 LOC)

- [ ] Loads `_shared.js`
- [ ] Exposes `handlePageFlow` to window scope for v1.2 P-4 tests
- [ ] NOT served in production (verify served only when `C3A_TEST_MODE=1`)

**Phase 6 files (verify against S8 SPEC v1.2 LOCKED § 4.7 + § 4.11 e2e + § 4 Tier 2):**

`tests/e2e/conftest.py`

- [ ] Playwright fixtures: browser session-scoped, context/page function-scoped
- [ ] `c3a_test_environment` fixture combining all per § 4 e2e

`tests/e2e/playwright.config.json`

- [ ] Chromium-only
- [ ] Headless
- [ ] 30s timeout

`tests/e2e/test_c3a_browser_happy_flow.py`

- [ ] @pytest.mark.e2e
- [ ] Walks happy path: case.html → resolve → done.html
- [ ] Verifies trace_id propagation across redirects

`tests/e2e/test_c3a_browser_cba_flow.py`

- [ ] @pytest.mark.e2e
- [ ] CBA-pause path: case.html → resolve → checklist.html → cba-verified → done.html

`tests/e2e/test_c3a_browser_abort.py`

- [ ] @pytest.mark.e2e
- [ ] Abort path: case.html → abort → aborted.html

`tests/e2e/test_c3a_browser_resume.py`

- [ ] @pytest.mark.e2e
- [ ] 24h-later resume from email link: directly to checklist.html with token+trace

`tests/e2e/test_c3a_browser_failure.py`

- [ ] @pytest.mark.e2e
- [ ] Error UX rendering for 503 / 410 / 4xx / network

`tests/e2e/test_c3a_a11y_auto.py`

- [ ] 5 axe-core scans per § 4 e2e
- [ ] Currently skipped due to axe-core CDN unreachable in sandbox — verify skip is correct, NOT a code error

`tests/e2e/test_c3a_observability.py` (Tier 2 promotion per v1.2 P-1)

- [ ] @pytest.mark.e2e
- [ ] /health response shape
- [ ] Metric line schema (closed P30 vocabulary)
- [ ] Trace_id propagation through metric lines (P43 client/server decoupling)

`tests/e2e/test_handle_page_flow.py` (per v1.2 P-4)

- [ ] @pytest.mark.e2e
- [ ] 3 tests: success path, TERMINAL dispatch, USER_FIXABLE dispatch
- [ ] Uses `_test_harness.html`

`tests/e2e/MANUAL_A11Y_CHECKLIST.md`

- [ ] Per round 2 X8 / R3.6
- [ ] Documents the manual a11y checks that complement axe-core auto

#### After audit complete

Produce a single summary table in your scratch notes / next handoff:

```
| File | Verdict | Notes |
|---|---|---|
| _shared.css | KEEP / PATCH / REPLACE | (1-line reason) |
| _shared.js | … | … |
| case.html | … | … |
... etc
```

Then proceed with:

- KEEP files: integrate as-is into your Phase 5 deliverable list
- PATCH files: implement the listed fixes
- REPLACE files: archive old as `<file>.session27_inherited`, write fresh

**Only after this audit is complete can you decide whether the
remaining Phase 5 work is "5 static routes + maybe per-page CSS"
(small) or "rewrite N files + add routes" (substantial).**

-----

## 4. SUMMARY — YOUR FIRST ACTIONS THIS SESSION

(Updated; flags adjudicated, no Ramalingam-wait step.)

1. **Read this file** (you're doing it)
2. **Confirm Rule 10.6.1 in memory line 11** (one tool call)
3. **Run pre-touch inventory** — `ls -la` on `static/c3a/`, `tests/e2e/`, `tests/validation/` and record the file lists
4. **Apply the document patches in § 2A–2D** above (4 file edits, ~10 min)
5. **Replace `04_backlog/backlog_session_27.md`** with the corrected version (drop-in)
6. **Run the file-by-file audit in § 3** above for the 11 pre-existing Phase 5 files + 9 pre-existing Phase 6 files (~25–30 min)

**Then** — flags A and B are already locked, so you proceed directly to Phase 5 work:

- Implement KEEP / PATCH / REPLACE outcomes from the audit
- Wire 5 static GET routes into `server.py`
- Add per-page `.css` files only if your audit determined they're needed

Move on through Phases 6 and 7 per the original handoff plan.

-----

## 5. WHY THIS HAPPENED (lessons embedded in Rule 10.6.1)

Session 27 Claude jumped into Phase 1 work after reading the spec without ever inventorying the pre-existing state of the directories that work would touch. The audit at session end then compared "things I changed in this session" to spec — but never compared "things present in working tree" to spec.

Rule 10.6.1 plus § 4 verification step ("at session start, ls the directories you'll touch") prevents this from recurring.

Apply the same discipline to your own Session 28 audit: at session end, your three-check protocol must include "pre-touch inventory was taken at start of session and is reconciled with end-of-session state."

-----

## 6. SESSION 27 AUDIT-MISS ROOT CAUSE — for your records

- Memory line 11 (Rule 10.6.1) — permanent fix
- This file — retroactive correction for Session 27 bundle
- Updated `04_backlog/backlog_session_27.md` carries B-056 (formal § 1.2 (ii) carve-out language extension at next spec amendment cycle)
- After your Session 28 work integrates cleanly, fold the retroactive corrections back into a clean v5 bundle so future sessions don't see two versions of these documents

The chain holds.
