# THREE OBLIGATIONS + FIVE PATTERNS

These are non-negotiable. The next Claude must follow these without exception.

---

## THE THREE OBLIGATIONS

### 1. Spec-first

Never write code before there is a LOCKED spec for what you're building. For S6, the spec IS already locked at v1.0 (see `02_specs_chronological/12_S6_SPEC_v1_0_LOCKED.txt`). Build from that.

For S7 (next after S6), follow the cycle: draft → critique → patch → lock → code → critique → patch → next.

### 2. Honest context reporting (single use)

Per Ramalingam's clarification at end of Session 21:

- **Do NOT** mention context budget casually.
- **Do NOT** use it to suggest stopping.
- **Do** tell Ramalingam straight ONCE if context is genuinely too low to complete the current step at the quality level of prior chats.
- This is a quality-protection signal, not a stop-prompting signal. He decides what to do with it.

### 3. Master doc + handoff updates at session end

Every session ends with:
- Update `MASTER_DESIGN_NARRATIVE.md` with what happened (Part 4 entry; relevant Part 8/9/11 updates; footer version bump)
- Update backlog if new items surfaced
- If Ramalingam calls for handoff: produce full handoff package with integrity check

---

## THE FIVE PATTERNS (NEVER FALL INTO)

### Pattern A — Fix-as-bandage

Symptom: code change addresses the immediate symptom without identifying the root cause.

Example: a test fails because of a race condition; you add a `time.sleep()` to make the test pass. The race is still there.

Counter: **always trace the failure to its root cause** before patching. If you don't have time to fix the root, log a backlog item explicitly naming the bandage.

### Pattern B — Building without wiring

Symptom: writing a module that compiles and tests in isolation but doesn't integrate with anything else.

Example: building S6 with mocked-out S5 calls, never verifying the real S5 contract.

Counter: **integration test before celebration**. Every new module must demonstrate it talks to its real upstream/downstream peers correctly.

### Pattern C — Scores without truth

Symptom: introducing metrics ("liveability score 72/100") that aren't traced to specific user-observable outcomes.

Example: a "code quality" score that doesn't predict real bugs.

Counter: **every metric must be tied to a user-visible outcome** with documented derivation. Otherwise it's a vanity score and may actively mislead.

### Pattern D — Rules on rules

Symptom: stacking constraint layers without simplifying. Each new edge case adds another conditional rather than refactoring the underlying logic.

Example: `if x: if y: if z: ... if w: ...` chains that nobody can audit.

Counter: **before adding a new rule, check if the existing rules can be simplified**. Sometimes the right move is to refactor backward, not patch forward.

### Pattern E — Scope creep mid-build (the most expensive)

Symptom: while implementing a locked spec, you decide to also fix a related issue you just noticed. The unscoped work bleeds into commits, tests, and reviews.

Example: while building S6, deciding to also refactor S3's option_generator because you noticed inefficiency.

Counter: **the locked spec is the only scope**. Any unrelated finding goes to the backlog, NOT into the current build. Defer ruthlessly.

---

## WHEN APPLYING THESE

When Ramalingam (or his critique source) flags an issue:

1. Identify which pattern (A through E) applies if any
2. State the verdict honestly: VALID / VALID-BUT-BACKLOG / INVALID
3. If applying D-067 pushback, name the specific pattern being protected against
4. Document the decision in the response so Ramalingam can override

The chain holds.
