# BuildemUp LOCK-Trigger Protocol

**Established:** S48.
**Status:** Standing project policy.
**Scope:** Applies to every spec LOCK event in BuildemUp going forward — not just C15.

---

## Trigger phrase

When Ramalingam types "**lock**" (or equivalent: "lock it", "vN LOCKED", "lock C15", etc.) in reference to a spec version, Claude MUST follow this protocol BEFORE marking anything LOCKED.

Per Rule 8, **LOCK authority belongs to Ramalingam alone**. This protocol describes the preprocessing Claude does so Ramalingam adjudicates on a complete, integrated candidate — not the raw stand-alone "lock" call.

---

## Protocol steps

When LOCK trigger is heard, Claude performs in order:

### Step 1 — Process every deferred PROPOSED amendment

Every amendment that was previously PROPOSED but deferred (not yet adopted, not yet rejected) is now processed:
- Integrate the amendment into the spec text
- Update affected code/schema if cache-relevant
- Update affected tests
- Verify integration doesn't break invariants

Current standing deferred amendments (as of S48 close):
- **A12** (coverage_quality field on ProblemReport + per-dimension maturity) — cache-relevant; schema change

### Step 2 — Close every v1.0-LOCK-mandatory backlog item

Every item with LOCK-mandatory flag is resolved:
- Spec amendment landed if the item is a spec-shape requirement
- Code/tests landed if implementation is required
- Documentation landed if process-only

Current LOCK-mandatory inventory for C15 (8 items):
1. B-C15-SEVERITY-RULE-TABLE-LOCK
2. B-C15-CHECK-REGISTRY-LOCK
3. B-C15-CULTURAL-PROFILE-V1-LOCK (≥3 sub-variants per A3)
4. B-C15-CHECK-MEASUREMENT-FORMULAS-LOCK
5. B-C15-UNCONVENTIONAL-PATTERN-DETECTION-LOCK
6. B-C15-MOAT-LINT
7. B-C15-CULTURAL-PROFILE-COVERAGE
8. **B-C15-SEVERITY-CHANGE-GOVERNANCE-PRE-LOCK** (filed S48 via critique walk)

### Step 3 — Re-run three-check protocol (Rule 10.6)

Against the now-extended spec+code:
- **(a) GAP CHECK** — promised vs. delivered
- **(b) AUDIT CHECK** — spec-compliance line-by-line with decisions surfaced
- **(c) INTEGRITY CHECK** — files present/non-empty/tests green

All three required; missing any = LOCK candidate is incomplete.

### Step 4 — Surface vN.LOCK-CANDIDATE for Ramalingam adjudication

Claude returns a status message of the form:

> "vN.LOCK-CANDIDATE ready. Processed [list of amendments]. Closed [list of LOCK-mandatory items]. Three-check headlines: [results]. **Pending your final LOCK adjudication.**"

Ramalingam either:
- Confirms with "locked" / "vN LOCKED" → spec moves to LOCKED state
- Returns patches → Claude produces v(N+1).LOCK-CANDIDATE, loop
- Defers → spec stays at v(N).LOCK-CANDIDATE state, no LOCK

---

## What Claude must NOT do

- Self-declare LOCK (Rule 8 absolute)
- Skip Steps 1-3 because "the spec already looks ready"
- Treat "lock" as a casual word — it always triggers this protocol
- Ask Ramalingam permission to start processing — the trigger phrase IS the permission

---

## Origin

S48 conversation, post-critique-walk:
> Ramalingam: "Defer for now but when I say lock do all this before officially locking it ok"
> Claude: Confirmed protocol restated.
> Memory edit #14: BuildemUp LOCK-trigger protocol filed.

---

*End of LOCK-trigger protocol.*
