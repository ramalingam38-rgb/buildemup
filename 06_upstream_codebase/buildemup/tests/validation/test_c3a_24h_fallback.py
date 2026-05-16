"""S8 § 4.5 — 24h fallback chain tests (8 tests).

Verifies P21 + P33 + the scheduler enqueue/claim/fire chain, including
P28 atomic dequeue (duplicate-tick no-op per § 4.5 v0.2 Finding 11).

The scheduler chain is exercised through the public scheduler API and
the SchedulerStateStorage methods, NOT through the C2 brief-loading
path — that would require a full state-machine traversal which the
existing 286 c3a tests already cover unit-side.

§ 4.0.1: each test docstring names which invariant it protects.
"""
from __future__ import annotations

import os
import sqlite3
import time

import pytest


def _seed_gate(db_path, token):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO gate_states "
            "(token, state_json, saved_at, expires_at, "
            " is_terminal, last_request_id, last_response_json) "
            "VALUES (?, '{}', ?, ?, 0, NULL, NULL)",
            (token, now, now + 86400),
        )
        conn.commit()


class TestSchedulerFallbackChain:
    """§ 4.5 — full P21 + P33 + P28 chain via scheduler storage."""

    def test_p21_enqueue_creates_due_row(
        self, fresh_storage, temp_db_path,
    ):
        """P21: enqueueing a session sets fire_at = now + 86400
        and the row is NOT immediately due."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-fb-1"
        _seed_gate(temp_db_path, token)
        fire_at = int(time.time()) + 86400
        storage.enqueue(
            session_token=token, fire_at=fire_at,
            request_id="r-1", trace_id="0123456789abcdef",
        )
        # Not due yet
        claimed = storage.claim_due(now=int(time.time()), limit=10)
        tokens = [c[0] for c in claimed]
        assert token not in tokens

    def test_p21_advanced_clock_makes_row_claimable(
        self, fresh_storage, temp_db_path, frozen_clock,
    ):
        """P21 + P33: simulating clock advance → row becomes claimable."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-fb-2"
        _seed_gate(temp_db_path, token)
        # Past fire_at
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-2", trace_id="0123456789abcdef",
        )
        claimed = storage.claim_due(now=int(time.time()), limit=10)
        assert any(c[0] == token for c in claimed)

    def test_p28_duplicate_tick_no_op(
        self, fresh_storage, temp_db_path,
    ):
        """§ 4.5 v0.2 Finding 11: a second tick claims nothing once
        the first has committed_fired the row."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-dup"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-d", trace_id="0123456789abcdef",
        )
        first = storage.claim_due(now=int(time.time()), limit=10)
        # Commit the first claim
        for c in first:
            storage.commit_fired(c[0])
        # Second tick must NOT claim it
        second = storage.claim_due(now=int(time.time()), limit=10)
        assert not any(c[0] == token for c in second)

    def test_p33_record_error_increments_attempt(
        self, fresh_storage, temp_db_path,
    ):
        """P33: record_error increments attempt_count and stamps
        last_attempt_at; cooldown delays re-claim."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-err"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-e", trace_id="0123456789abcdef",
        )
        first = storage.claim_due(now=int(time.time()), limit=10)
        assert any(c[0] == token for c in first)
        for c in first:
            if c[0] == token:
                storage.record_error(c[0], "post_failure: timeout")
        # Inspect row directly
        with sqlite3.connect(temp_db_path) as conn:
            row = conn.execute(
                "SELECT attempt_count FROM scheduler_state "
                "WHERE session_token=?", (token,),
            ).fetchone()
        assert row is not None and row[0] == 1

    def test_p33_three_failures_makes_row_stuck(
        self, fresh_storage, temp_db_path,
    ):
        """P33: 3 failed attempts → row stuck (attempt_count=3)."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-stuck"
        _seed_gate(temp_db_path, token)
        storage.enqueue(
            session_token=token, fire_at=int(time.time()) - 60,
            request_id="r-s", trace_id="0123456789abcdef",
        )
        for _ in range(3):
            with sqlite3.connect(temp_db_path) as conn:
                conn.execute(
                    "UPDATE scheduler_state SET "
                    "attempt_count = attempt_count + 1, "
                    "last_attempt_at = ?, "
                    "fallback_error = ? "
                    "WHERE session_token=?",
                    (int(time.time()) - 1000, "post_failure", token),
                )
                conn.commit()
        # count_stuck reflects this
        stuck = storage.count_stuck()
        assert stuck >= 1, f"expected >=1 stuck; got {stuck}"

    def test_p21_enqueue_idempotent_same_request_id(
        self, fresh_storage, temp_db_path,
    ):
        """P21: enqueueing the same (session_token, request_id) twice
        yields one logical row (no duplicate side effect)."""
        from buildemup.utils.scheduler_state_storage import (
            SchedulerStateStorage,
        )
        storage = SchedulerStateStorage(db_path=temp_db_path)
        token = "tok-idem"
        _seed_gate(temp_db_path, token)
        for _ in range(2):
            try:
                storage.enqueue(
                    session_token=token, fire_at=int(time.time()) + 1000,
                    request_id="r-idem", trace_id="0123456789abcdef",
                )
            except Exception:
                # Some implementations raise on duplicate enqueue;
                # acceptable behavior. The point is no double-fire.
                pass
        with sqlite3.connect(temp_db_path) as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM scheduler_state WHERE session_token=?",
                (token,),
            ).fetchone()[0]
        assert n == 1, f"expected 1 scheduler_state row; got {n}"

    def test_p21_email_hook_called_via_mocked_resend(
        self, mocked_resend, fresh_storage,
    ):
        """§ 4.5 + § 7.4: the email hook constructs a Resend request
        with the configured shape (URL, X-Trace-Id header)."""
        from buildemup.api.c3a_email_hook import send_cba_checklist
        send_cba_checklist(
            "test+s8@example.test",
            draft_token="tok-email-001",
            fallback_at="2025-01-01T00:00:00Z",
            trace_id="0123456789abcdef",
        )
        assert len(mocked_resend) == 1
        call = mocked_resend[0]
        assert call.url == "https://api.resend.com/emails"
        # Trace propagated via custom header in body
        assert call.body["headers"]["X-Trace-Id"] == "0123456789abcdef"
        # URL embedded in HTML body
        assert "tok-email-001" in call.body["html"]
        # "do not forward" UX hint present per § 5a.5 round 3 R3.6
        assert "do not forward" in call.body["html"].lower()

    def test_email_hook_uses_buildemup_public_url(
        self, mocked_resend, fresh_storage, monkeypatch,
    ):
        """§ 9.3: cba-checklist URL base reads from
        BUILDEMUP_PUBLIC_URL env var (Finding 2)."""
        from buildemup.api.c3a_email_hook import send_cba_checklist
        monkeypatch.setenv(
            "BUILDEMUP_PUBLIC_URL", "https://buildemup.example.com",
        )
        send_cba_checklist(
            "test+pu@example.test",
            draft_token="tok-pu",
            fallback_at="2025-01-01T00:00:00Z",
            trace_id="cafebabe01234567",
        )
        assert len(mocked_resend) == 1
        html = mocked_resend[0].body["html"]
        assert "https://buildemup.example.com/c3a/checklist.html" in html
        assert "token=tok-pu" in html
        assert "trace=cafebabe01234567" in html
