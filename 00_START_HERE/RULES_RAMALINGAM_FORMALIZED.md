# RULES FORMALIZED BY RAMALINGAM — SESSION 23

These 5 rules supplement the Three Obligations and Five Patterns. They
govern handoff format and delivery discipline. Established in
Session 23 in response to specific Claude failures observed that
session.

---

## RULE 1 — Single integrity-checked zip

Every handoff is delivered as ONE zip file containing:
- All files from the previous handoff zip (preserved without loss)
- This session's conversation transcript or narrative
- All files produced this session

Before delivery, two checks must be run and reported to Ramalingam:

**Integrity check:** every file from the previous handoff zip is
present in the new zip and uncorrupted. No silent drops.

**Audit check:** every artifact this session produced (specs, code,
master doc updates, backlog updates, transcript) is present in the
new zip. Nothing forgotten.

Both check results reported BEFORE Ramalingam accepts the zip. He
should not have to verify; that's Claude's job.

**Rationale:** Session 23 delivered loose files and missed the
master doc bump until caught. A single integrity-checked zip prevents
this. Ramalingam should not be the QA layer.

---

## RULE 2 — Latest-only chat delivery + spec self-containment

Three sub-rules:

### 2a. Latest-only delivery during chat critique cycles

When iterating spec versions in chat (v0.1 → v0.2 → v0.3 → v1.0), each
patch round delivers ONLY the latest version, not all prior versions.

Example: round-1 critique applied → deliver only v0.2 (not v0.1 + v0.2).
Round-2 critique applied → deliver only v0.3 (not v0.1 + v0.2 + v0.3).
Lock decision → deliver only v1.0 LOCKED.

Ramalingam should not have to disambiguate which file is current.

NOTE: This rule applies to LIVE CHAT delivery during critique. The
handoff ZIP preserves chronological history (Rule 3) so the next
Claude can read the process linearly. These are different contexts.

### 2b. Spec self-containment

Spec files must include backlog items deferred during critique cycles
INSIDE the spec, with full deferral rationale and trigger conditions.
Not just a CHANGELOG one-liner; a dedicated section.

Pattern: see § 13.5 of `buildemup_S7a_SPEC_v1_0_LOCKED.txt`. The spec
is the source of truth and must be self-contained — readable in
isolation without cross-referencing the project backlog.

The project backlog file (`v0_2_backlog.md`) gets the items appended
as well per Obligation 3, but the spec carries full detail for
discoverability.

### 2c. Code is delivered consolidated

When code build is complete, deliver as a SINGLE consolidated `.py`
file with module boundary headers, the way the S6 bundle was
delivered. Not a tree of separate files in the chat.

The handoff zip preserves the file tree separately
(`06_upstream_codebase/`) so the next Claude has the deployable form;
the consolidated file is for review.

**Rationale:** Ramalingam reviews code visually. A consolidated file
with clear module boundaries is reviewable; a folder of separate
files is not.

---

## RULE 3 — Chronological order in zip

Files inside the handoff zip are organized in chronological creation
order so the next Claude can read the process linearly.

This is why the zip has numbered prefixes (`02_specs_chronological/`
files numbered 01 through 16, etc.). The next Claude should be able to
read the numbered files in order and reconstruct the project's
decision history without jumping around.

The Session 23 spec evolution (v0.1 → v0.2 → v0.3 → v1.0) is preserved
chronologically as files 13, 14, 15, 16 in `02_specs_chronological/`.
This is for the next Claude's understanding only — does NOT contradict
Rule 2a (which governs live chat delivery).

---

## RULE 4 — Actionable next-Claude instructions

The handoff file (`NEXT_CLAUDE_HANDOFF.md`) tells the next Claude
WHAT TO DO with concrete, actionable detail. Not just orientation.

Specifically:
- Numbered steps in execution order
- Concrete commands to run (`unzip`, `python -m unittest`)
- Specific file paths and line numbers where work is needed
- Pre-execution gates ("if X fails, STOP and tell Ramalingam")
- Done criteria (the 7-point checklist at session end)

The next Claude should be able to read the handoff and start working
without ambiguity about the next step.

**Anti-pattern:** orientation-only handoffs that say "read the spec
and start building" without specifying the build queue.

---

## RULE 5 — Don't skip session-end updates

This is implicit in Obligation 3 but worth making explicit because
Session 23 broke it:

Master doc bump + handoff update + backlog update happen at EVERY
session end. No exceptions. Even discussion-only sessions. Even
mid-build stops.

If Claude is mid-build and Ramalingam says "stop," Claude must:
1. Bump the master doc
2. Update the handoff with mid-build state
3. Update the backlog if items were logged

Then deliver the integrity-checked zip per Rule 1.

**Rationale:** Session 23 had a mid-build stop (Obligation 2 quality
threshold). Claude initially delivered handoff + workdir tarball
WITHOUT the master doc bump. Ramalingam caught it: "You know the rule
about handoff right." Rule 5 makes this non-skippable.

---

## RULE 6 — Status update at every session end

Every session must include an explicit status block answering three
questions:

1. **Project-wide:** How many of the 17 total components are completed?
   List each shipped component briefly + which are pending.

2. **This session:** What was completed in this session specifically?
   Specs locked, code built, documentation updated, decisions made.

3. **Still pending:** What remains for the next session AND for the
   broader project? Both immediate (next conversation) and long-range
   (post-current-component).

This status block goes in THREE places:
- The master doc § 4.X session entry (full detail)
- The NEXT_CLAUDE_HANDOFF.md (so the next Claude sees it on resume)
- The top of the chat-message that delivers the handoff zip (so
  Ramalingam sees it immediately, before opening the zip)

**Rationale:** at any moment Ramalingam should be able to glance at
the latest session and know exactly where the project stands. Without
this rule, the status is buried in narrative and requires reading
multiple files to reconstruct. With this rule, the answer is one
glance away.

The completion percentage is informative but not the goal — the goal
is honest state visibility for the solo founder making roadmap
decisions.

---

## ENFORCEMENT

Future sessions should be self-checking against these rules at session
end. Before delivering anything, run through:

- [ ] Single zip with previous + this session's everything? (Rule 1)
- [ ] Integrity check run and reported? (Rule 1)
- [ ] Audit check run and reported? (Rule 1)
- [ ] Spec backlog items in spec file, not just project backlog? (Rule 2b)
- [ ] Code consolidated for review? (Rule 2c)
- [ ] Files in chronological order in zip? (Rule 3)
- [ ] Handoff has numbered actionable steps? (Rule 4)
- [ ] Master doc + backlog + handoff all updated? (Rule 5)
- [ ] Status update (project-wide / this-session / pending) in master
      doc + handoff + chat-message delivery? (Rule 6)

If any answer is "no" — fix before delivery.

---

The chain holds.
