## Session 24 ADDENDUM — backlog additions from code review

Added after Session 24 main work, in response to third-party code
review of `SESSION_24_CODE_FOR_REVIEW.py`. Disposition reasoning
in `09_conversation_artifacts/D067_PUSHBACK_CODE_REVIEW_RESPONSE.md`.

---

### B-044 — Storage-layer dependency-injection refactor

**Severity:** Low (v0.1) → Medium (multi-replica)
**Source:** Code review item #2

**Symptom (today):** `api/c3a_endpoint.py` uses module-level lazy
singletons (`_storage`, `_brief_storage`) reset by tests via
`reset_storages_for_tests`. Hidden state, not thread-safe across
multiple processes, no graceful migration path to
multi-instance deployment.

**Why deferred:** v0.1 deploys to single-Replit. The DI seam exists
(test reset). No measured pain.

**Proposed fix:** Refactor handler functions to take storage
instances as explicit parameters (or accept a dependencies-container
object). Migrate the test reset pattern to "pass test storage in"
rather than "reset module globals." 5 handlers × ~3 lines each ≈
15-20 LOC delta. Tests don't change semantically; just the injection
mechanism.

**Trigger:** When deploying to a multi-instance environment (Railway
multi-replica, k8s, ECS), OR when adding the C3a v0.2 architecture
refactor that subsumes items 1/6/13 from the same review.

**Effort:** 1 sub-session (refactor + verify all 253 c3a tests pass).

---

### B-045 — Defense-in-depth validation in `from_dict` methods

**Severity:** Low (v0.1) → Medium (multi-tenant or schema migration)
**Source:** Code review item #11

**Symptom (today):** `from_dict` classmethods on dataclasses
(GateState, Brief, ExtremeCase, etc.) assume correct structure and
types. Calls like `payload["case_id"]` raise KeyError on missing,
`EnumClass(payload[field])` raises ValueError on unknown enum, but
there is no centralized "validate this dict matches the schema"
step.

**Why this is OK at v0.1:** The trust boundary is the storage
layer. `from_dict` is only called from `storage.resume()` reading
data the SAME server wrote earlier with `to_dict()`. P8 (schema
versioning) gates incompatibility; P9 (size cap) gates DoS. No
external untrusted-input path reaches `from_dict` directly.

**Why this is fix-worthy long-term:**
- When schema migration arrives (B-040 in earlier backlog), the
  on-disk format will diverge from current dataclasses for some
  window. Centralized validation reduces the migration's surface
  area.
- Multi-tenant deployments may have shared storage where one
  tenant's corruption shouldn't crash another's session.
- Stronger types via `pydantic` or a custom validator would reduce
  the spread of `KeyError`/`ValueError` patterns in calling code.

**Proposed fix:** Either:
1. Add `pydantic` models alongside dataclasses (auto-validation +
   IDE introspection benefit).
2. Add a custom `_validate_dict_for_class(cls, data)` helper called
   at the top of every `from_dict`.

Choose during the C3a v0.2 architecture refactor.

**Trigger:** First schema migration (B-040), OR multi-tenant work,
OR observed production corruption in a `from_dict` call.

**Effort:** 1 sub-session if pydantic; 2 if custom validator (more
boilerplate).

---

### B-046 — API response versioning strategy

**Severity:** Low (v0.1) → Medium (external consumers)
**Source:** Code review item #12

**Symptom (today):** GateState has schema versioning (P8: explicit
`_schema_version` field, default "1", mismatched values rejected).
But the 5 API endpoint RESPONSES are not versioned. There is no
`/v1/api/...` prefix and no `response_version` field. Future
breaking changes to response shape would silently break clients.

**Why this is OK at v0.1:** The only API consumer is the BuildEase
frontend, shipped from the same repo. Changes are coordinated.

**Why this is fix-worthy long-term:**
- Mobile apps may want to call the API directly (different release
  cadence from web).
- Third-party tools (architect plug-ins, contractor integrations)
  may want to integrate.
- Multi-major-version API support is much easier with the prefix
  in place from day 1 of "we have external consumers."

**Proposed fix:** Two options:
1. **Add `/v1/api/...` URL prefix.** Lowest impact. Add now or at
   first breaking change.
2. **Add `"response_version": "1"` field to every response shape.**
   Self-describing without URL change.

Pragmatic recommendation: do (1) at the same time as the auth layer
(B-042) since both are URL-routing changes.

**Trigger:** First breaking change request, OR first external API
consumer onboarded, OR auth layer (B-042) implementation.

**Effort:** Small (~30 min) for URL prefix; small for response
field. Both are easy if done before clients start hardcoding the
unversioned URLs.

---

## Backlog count after Session 24 addendum

43 items total: B-001 through B-046, with B-026 superseded into B-023.

Recent additions:
- B-040 (Session 23) — schema migration layer
- B-041 (Session 23) — BriefStorage WAL retrofit + prune sweep
- B-042 (Session 23) — project-wide auth
- B-043 (Session 24) — gate_state_storage.save_existing rollback bug
- **B-044 (Session 24 addendum)** — storage-layer DI refactor
- **B-045 (Session 24 addendum)** — defense-in-depth from_dict validation
- **B-046 (Session 24 addendum)** — API response versioning strategy

---

## Items REJECTED from this review (NOT added to backlog)

These appeared in the code review but were dispositioned as REJECT
per D-067, with reasoning in the rebuttal document. Listed here so a
future Claude doesn't re-add them:

- **Item 3** (lock granularity) — moving COMPUTE outside the lock
  breaks the read-compute-write atomicity. Reviewer's framing
  conflates pessimistic locking with optimistic concurrency.
- **Item 10** (streaming JSON parsing for ≤ 1 MB payloads) — Pattern E.
- **Item 14** (silent business assumptions) — DETACHED default is
  explicitly documented in spec § 5.5; user timestamps are now
  validated per item 4 fix. Reviewer misread spec.

---

## Items DEFERRED to C3a v0.2 (NOT new backlog items)

These will be addressed during the C3a v0.2 architecture refactor
session, scheduled post-S8:
- Item 1 (handler over-coupling — extract service layer)
- Item 6 (response builder unification)
- Item 13 (monolithic file split)

The C3a v0.2 architecture refactor sub-session will be added to the
roadmap when S8 ships.
