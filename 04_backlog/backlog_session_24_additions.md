## Session 24 backlog additions

### B-043 — `gate_state_storage.save_existing` rollback bug masks TokenNotFoundError

**Severity:** Medium (correct exception type does not propagate; surface
behavior is wrong but no data corruption).

**Discovered:** Session 24 (S7a code build), via test
`test_save_existing_unknown_token_raises` in
`tests/test_c03a_session7_storage.py` (test was REMOVED after
discovery per the handoff's DO-NOT-MODIFY rule for the storage layer;
this backlog item replaces it).

**Symptom:** When `GateStateStorage.save_existing()` is called with an
unknown token, the UPDATE statement returns rowcount=0. The error path
manually rolls back the transaction then raises `TokenNotFoundError`.
However, the outer `except Exception` clause in the same function then
attempts a second rollback via `_execute_with_retry(conn, "ROLLBACK")`,
which fails with `sqlite3.OperationalError: cannot rollback - no
transaction is active`. This second exception masks the original
`TokenNotFoundError`, so the caller sees a SQLite error instead of the
intended typed exception.

**Reproducer (currently absent from the test suite — re-add post-fix):**
```python
def test_save_existing_unknown_token_raises(self):
    state = _build_initial_state()
    with self.assertRaises(TokenNotFoundError):
        self.storage.save_existing(
            "nonexistent-token-12345678",
            state, request_id="r1", response={"x": 1},
        )
```
This test currently observes `sqlite3.OperationalError` instead of
`TokenNotFoundError`.

**Why not fixed in Session 24:** The handoff explicitly forbids
modifying `gate_state_storage.py` in the S7a code build (it is marked
"complete + design-tested" upstream). Per Obligation 1 (spec-first)
and the locked contract, surgical edits to a "locked" module require
their own spec cycle. The cleanest path is S7b (deployment hardening)
or a dedicated bug-fix mini-session.

**Proposed fix:** in `save_existing`, hoist the `raise
TokenNotFoundError` ABOVE the manual rollback so the outer except
performs the single rollback:

```python
# Inside save_existing, after _execute_with_retry returns the cursor:
if cur.rowcount == 0:
    # Don't manually rollback; let the outer except clause handle it.
    raise TokenNotFoundError(
        f"save_existing: token not found: {token!r}"
    )
_execute_with_retry(conn, "COMMIT")
```

The `except Exception: _execute_with_retry(conn, "ROLLBACK"); raise`
clause then fires once and propagates `TokenNotFoundError` cleanly.

**Effort:** ~5 lines + re-add the deleted test. Sub-30-minute fix.

**Trigger:** S7b (deployment hardening session) is the natural home,
OR a dedicated 30-minute fix-up session before S7b if it blocks
production traffic. Currently NOT blocking — the bug only surfaces
when a stale `session_token` is sent to a mutating endpoint after the
TTL has pruned its row, which is a rare edge case in v0.1.

---

## Backlog count after Session 24

40 items total: B-001 through B-043, with B-026 superseded into B-023.

Recent additions:
- B-040 (Session 23) — schema migration layer
- B-041 (Session 23) — BriefStorage WAL retrofit + prune sweep
- B-042 (Session 23) — project-wide auth
- B-043 (Session 24) — gate_state_storage.save_existing rollback bug

---

## Session 24 — items considered but NOT added

- **C4 from code-critique** (two concurrent /check calls with same
  brief_token + request_id can both reach gate.start, wasting one
  gate_states write). Considered Pattern E if "fixed" via
  pre-acquisition lock; P12 logical uniqueness is preserved. Not a
  correctness bug. NOT added; documented in Session 24 transcript
  for future reference.
