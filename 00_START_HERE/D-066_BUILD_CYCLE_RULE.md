# D-066 — THE BUILD CYCLE RULE

Locked end of Session 21 by Ramalingam. Refined to D-066 v2 same session per his clarification.

This is the contract every C3a session and beyond must follow.

---

## THE EIGHT-STEP CYCLE

For every session from S6 onward:

```
1. SPEC DRAFT
   ↓
   Claude writes buildemup_S{N}_SPEC_v0_1_DRAFT.txt
   based on parent spec sections + integration surface

2. SPEC ANALYSIS
   ↓
   Ramalingam takes draft to external critique source
   Claude WAITS

3. PATCH SPEC
   ↓
   Critique returns N drawbacks
   Claude analyses each: VALID / VALID-BUT-BACKLOG / INVALID
   Patches what's valid; logs what's deferred; pushes back where appropriate (D-067)
   Produces buildemup_S{N}_SPEC_v0_2_DRAFT.txt

4. CRITIQUE ROUND 2/3 IF NEEDED
   ↓
   Repeat 2-3 until critique returns clean OR Ramalingam decides to lock

5. FINAL LOCK
   ↓
   Ramalingam says "lock"
   Claude produces buildemup_S{N}_SPEC_v1_0_LOCKED.txt

6. CODE
   ↓
   Claude builds source + test files
   Runs tests until they pass
   Delivers as consolidated .py to Ramalingam

7. CODE ANALYSIS
   ↓
   Ramalingam takes code to external critique source
   Claude WAITS

8. PATCH CODE
   ↓
   Code-critique returns N drawbacks
   Claude analyses each, patches what's valid, pushes back (D-067) where appropriate
   Re-runs tests
   Delivers patched code

   ↓

   MOVE TO NEXT BUILD (S{N+1})
   Loop back to step 1
```

---

## CONTINUATION DISCIPLINE

- **Continue building until Ramalingam says stop.**
- The decision to stop is **HIS**, not Claude's.
- Build cycles do NOT end at session boundaries.
- Build cycles do NOT end because the conversation is "long."

## CLAUDE'S RESPONSIBILITIES

- ✅ Suggest the next sensible step within the cycle
- ✅ Be honest about what's done and what's pending
- ✅ Apply D-067 pushback when critique would force YAGNI/Pattern E surgery
- ❌ Do NOT suggest handoff
- ❌ Do NOT mention context budget casually
- ❌ Do NOT use context as a stop-prompting signal

## THE ONE EXCEPTION (CONTEXT QUALITY)

If at any point during building Claude judges that **context is genuinely too low to complete the current step at the quality level of prior chats** — Claude tells Ramalingam straight, ONCE:

> "Context is now insufficient to do S{N} code/spec at the quality of this chat — you should hand off after this step."

This is a quality-protection signal, not a stop-prompting signal. Claude is honest about it once when it matters; doesn't repeat it.

## HANDOFF TRIGGER

Handoff happens **only when Ramalingam explicitly says "now hand off"** or equivalent.

When that happens, Claude produces (per **D-068 principle + D-069 format**):

**Format:** ONE single zip file (`handoff_S{N}.zip` or similar).

**Contents (chronologically organized):**
1. `00_START_HERE/` — orientation files (NEXT_CLAUDE_HANDOFF.md, obligations, build cycle rule)
2. `01_master_doc/` — full master doc updated with everything done across all conversations (chronological)
3. `02_specs_chronological/` — every spec file (drafts + locked) in chronological order
4. `03_code_chronological/` — every code file (built + patched) organized by session
5. `04_backlog/` — full backlog
6. `05_integrity_check/` — file-by-file inventory + verification + checksums

**NOT a giant consolidated .md** — exceeds download limits.
**NOT a folder of loose files** — cumbersome to pass around.
**ONE zip.** User extracts and reads at leisure.

The zip is the single canonical deliverable. Pass the zip to the next Claude or extract it yourself; either works.

---

## D-067 — CRITIQUE PUSHBACK RULE (extension)

When the latest critique round would force:
- **(a)** Pattern E surgery for hypothetical future need
- **(b)** Optimisation for cases that don't currently exist
- **(c)** Overcorrection with hostile mechanisms (caller-frame inspection in tests, graceful degradation that masks invariant violations, rule engines for trivial named predicates)

Claude **pushes back transparently**, citing prior decisions (D-065) and YAGNI principles. Pushback is documented in the response so Ramalingam can override if he disagrees.

Examples already on record (from B-027 code-critique round 2):
- D3 (caller-frame inspection enforcement) — REJECTED: hostile to test fixtures
- D5 (graceful degradation on missing dispatch) — REJECTED: would mask programmer bugs
- D7 (rule engine for 3 named predicates) — REJECTED: YAGNI

These three were rejected and logged transparently in the backlog so the decision is visible.

---

The chain holds.
