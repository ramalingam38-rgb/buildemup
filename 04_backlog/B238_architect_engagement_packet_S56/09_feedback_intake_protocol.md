# 09 — Feedback Intake Protocol

**Purpose:** When the architect's written deliverable arrives, this is how to process it so nothing falls through the cracks. Designed to be executed by Claude (next session) with Ramalingam in the loop.

---

## Pre-intake: prepare the workspace

Before opening the deliverable:

1. Save the architect's PDF / markdown / Word deliverable to:
   `04_backlog/B238_architect_review_findings_S[N].md` (where N is the next session number)
2. If the deliverable arrives as a PDF, extract the text into the markdown file. Keep the original PDF alongside for reference.
3. Open a fresh git branch named `b238-architect-feedback-S[N]` so all post-review work is isolated.

---

## Intake step 1 — Catalog every finding

For each distinct finding in the architect's deliverable, create a row in this table (save as `04_backlog/B238_FINDINGS_LOG_S[N].md`):

| # | Section | Architect's verbatim finding | Severity | Affected component(s) | S55 LOCK closure validated/refined? | Filed as backlog item ID | Status |
|---|---|---|---|---|---|---|---|

**Severity** uses 3 tiers, set by Claude after reading the finding:
- **SHIP-BLOCKING** — must fix before v1 release.
- **SHIP-AWARE** — should be fixed before v1 release; not strictly blocking if explicitly accepted.
- **POST-V1** — defer to v1.1 with explicit rationale.

**Affected component(s)** lists the C1-C17 components the finding touches.

**S55 LOCK closure validated/refined** records the link back to S55-pinned baselines. Possible values:
- "VALIDATES C14-betweenness — no change"
- "REFINES C15-severity-rule-table → change rule #12 from SOFT to HARD"
- "INVALIDATES C16-section-cut-rules — needs full rework"
- "NEW — outside S55 LOCK scope, new finding"

**Filed as backlog item ID** is the next-available B-### number.

---

## Intake step 2 — Convert to backlog items

For each row in the findings log:

1. Create a new backlog entry in `04_backlog/v0_2_backlog_S[N]_B238_architect_review_additions.md`.
2. Use this format:

```markdown
### B-### — [Short title from architect's finding]

**Severity:** SHIP-BLOCKING / SHIP-AWARE / POST-V1
**Source:** B-238 architect review S[N] (deliverable section [X.Y])
**Affected components:** C##, C##
**S55 LOCK linkage:** [validates / refines / invalidates / new]

**Architect's finding (verbatim):**
> [Quote the architect's words exactly. Don't paraphrase.]

**Translation to actionable change:**
[Claude rewrites the finding as a concrete change. Be specific: what file, what line, what new value, what new test.]

**Acceptance criteria:**
- [ ] Specific change X landed at file:line
- [ ] Test added/updated to cover the new behavior
- [ ] Spec doc updated and version-bumped if applicable
- [ ] No regression in existing test surface

**Effort estimate:** [Small <2h / Medium 2-8h / Large 8h+ / Cluster — needs subdivision]

**Open questions for Ramalingam:**
- [ ] [Any decision the architect didn't fully resolve, framed as a binary choice]
```

3. Promote each entry into a bucket:
   - SHIP-BLOCKING items → **Bucket A** (pre-launch hard gate)
   - SHIP-AWARE items → **Bucket B** (product blocker)
   - POST-V1 items → **Bucket D** (v2 deferred)

4. If the architect's finding directly addresses an existing S55-pinned LOCK closure (e.g., refines betweenness formula choice), also update the relevant `lock_closures_s55.py` file to record the architect's input + bump the version string from `+S55-formulas-pinned` to `+S57-architect-validated`.

---

## Intake step 3 — Update master doc

Add a new section to the master doc delta (`01_master_doc/MASTER_DOC_v3_17_TO_v3_18_DELTA.md` or whatever the next version is):

```markdown
### B-238 architect review feedback (received S[N], May 2026)

**Reviewer:** [Architect name + COA registration number] — [date received]

**Deliverable summary:** N findings filed, M ship-blocking, P ship-aware, Q post-v1.

**Key validations (no change required):**
- [List items the architect explicitly endorsed]

**Key refinements (specific changes pending):**
- [List items the architect refined, with their B-### backlog refs]

**Key disagreements (explicit decision to NOT act):**
- [List items where Ramalingam + Claude decided to NOT follow the architect's recommendation, with explicit reasoning. This is critical for transparency — disagreement is okay, hidden disagreement is not.]

**Net effect on S55 LOCK closures:**
- C14: [validated / refined → version bump / invalidated]
- C15: [validated / refined → version bump / invalidated]
- C16: [validated / refined → version bump / invalidated]
```

---

## Intake step 4 — Acknowledge to architect

Write a response email to the architect (Ramalingam sends, Claude drafts) within 7 days of receipt:

```
Dear [Architect name],

Thank you for the written deliverable received [DATE]. We have processed it
in full.

OVERALL: [N] findings logged. [M] will be addressed before v1 release. [P]
will be addressed in v1.1. [Q] we have decided to maintain the current
position on; reasoning is summarized below for each.

ITEMS WE ARE ACTING ON IMMEDIATELY:
1. [Architect finding short title] — [our planned action] — target close: [date]
2. ...

ITEMS WE ARE DEFERRING TO V1.1:
1. [Architect finding short title] — [why deferring]
2. ...

ITEMS WE ARE NOT ACTING ON, WITH REASONING:
1. [Architect finding short title] — [our reasoning for not acting]
2. ...

ONE FOLLOW-UP QUESTION:
[If any specific finding needs clarification, ask now. Single round.]

Final payment of ₹[AMOUNT] will be released via [UPI/NEFT] within 5 working
days, against your invoice.

Thank you again for the engagement.

Best,
Ramalingam
```

---

## Intake step 5 — Optional debrief call

If the engagement letter allowed an optional end-debrief call:

1. Send a calendar invite for a 60-min call.
2. Use the call to discuss any items in the "ITEMS WE ARE NOT ACTING ON" category — these are the ones where reasonable people might disagree, and the architect's verbal reasoning is valuable.
3. Take written notes; add anything substantive as addendum to `04_backlog/B238_FINDINGS_LOG_S[N].md`.

---

## Intake step 6 — Close the loop in code

After all SHIP-BLOCKING items are addressed:

1. Update each S55-pinned LOCK closure module (`c14/lock_closures_s55.py`, `c15/lock_closures_s55.py`, `c16/lock_closures_s55.py`) with a top-of-file comment:
   ```python
   # S57: Updated post-B-238 architect review.
   # Architect validation received [DATE]; refinements applied per
   # 04_backlog/v0_2_backlog_S57_B238_architect_review_additions.md.
   # Module version: vX.Y-locked
   ```

2. Bump each component's spec version from "vX.Y LOCKED" to "vX.Y+1 LOCKED" if architect feedback caused a substantive change.

3. Bump the C14 / C15 / C16 module-level `C14_LOCK_VERSION` / `C15_LOCK_VERSION` / `C16_LOCK_VERSION` from `+S55-formulas-pinned` to `+S57-architect-validated`.

4. Run the full test sweep. Expect ~50-100 new test cases to land covering the architect-validated changes.

5. Confirm green on the full bundle (4,468+ tests).

---

## Intake step 7 — Update NEXT_CLAUDE_HANDOFF

Update `00_START_HERE/NEXT_CLAUDE_HANDOFF.md` to reflect:
- B-238 has been CLOSED (or "received and processed")
- Bucket A is now [N] items (B-220 remains; B-238 closed)
- The S55-pinned LOCK closures are now architect-validated
- The Option C deliverable (detailed v1+ roadmap) is now unblocked

---

## What NOT to do at intake

- **Don't argue with findings in writing back to the architect** (except via the single follow-up question round). Disagreement is fine; documenting it internally is fine; debating with the architect after deliverable is unprofessional.
- **Don't silently ignore findings.** Every finding gets a row in the findings log. Every row gets a disposition.
- **Don't promote every SHIP-AWARE item to Bucket A.** That defeats the prioritization. Trust the severity classification.
- **Don't skip the acknowledgment email.** The architect needs to see their work was received and read.
- **Don't release final payment before processing.** Process first, then pay. Protects against shoddy deliverables and signals professional reciprocity.

---

## Estimated effort

| Step | Time |
|---|---|
| Pre-intake setup | 30 min |
| Step 1 — catalog findings | 1-2 hours (depends on finding count) |
| Step 2 — convert to backlog items | 2-3 hours |
| Step 3 — update master doc | 30 min |
| Step 4 — acknowledge to architect | 30 min |
| Step 5 — debrief call (optional) | 60 min |
| Step 6 — close loop in code | 4-8 hours (subset of total v1 work; spreads over multiple sessions) |
| Step 7 — update handoff | 15 min |

**One full Claude session** to do Steps 1-5; Step 6 spreads across multiple subsequent sessions as each finding is addressed.
