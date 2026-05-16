"""Tests for Component 3a Session 7a — hook ordering at /resolve.

Covers S7a SPEC v1.0 LOCKED § 8.8 TestHookOrdering:
  - test_hook_called_after_save_succeeds (P10)
  - test_hook_failure_does_not_corrupt_state (P10)
  - test_hook_NOT_recalled_on_idempotency_replay (P16 — round 2 #12)
  - test_terminal_replay_session_status_advisory_field (P15 — round 2 #7)

Hook ordering is the most subtle invariant in S7a: state IS the source
of truth, save happens FIRST, hooks are best-effort post-save. On
idempotency replay (duplicate request_id), the cached response is
returned verbatim WITHOUT re-firing hooks — the cached response IS
the proof the hook fired (or attempted to) the first time.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from buildemup.api import c3a_endpoint
from buildemup.utils.brief_storage import BriefStorage
from buildemup.utils.gate_state_storage import GateStateStorage

from buildemup.tests.test_c03a_session6_orchestrator_happy import (
    _DetectorPatch,
    _case,
    _make_brief,
    _make_gap_analysis,
    _make_runner,
    _option,
)
from buildemup.domain.extreme_case import ExtremeCaseId


def _make_cba_pause_case() -> object:
    """Build a case whose first option triggers CBA verification pause."""
    cba_opt = _option(
        "EC_005_OPT_CBA",
        recommended=False,
        requires_action="EMAIL_CBA_CHECKLIST",
        description="Verify if your plot is in a Continuous Building Area",
    )
    other_opt = _option("EC_005_OPT_OTHER")
    return _case(
        ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
        options=(cba_opt, other_opt),
    )


class _HookOrderTestBase(unittest.TestCase):
    """Sets up isolated storages + a real C2 runner mock + counter-based
    hook fakes. Each test gets a fresh tempdir.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gate_db = os.path.join(self.tmpdir, "gate.db")
        self.brief_db = os.path.join(self.tmpdir, "brief.db")
        self.gate_storage = GateStateStorage(db_path=self.gate_db)
        self.brief_storage = BriefStorage(db_path=self.brief_db)
        c3a_endpoint.reset_storages_for_tests(
            gate_storage=self.gate_storage,
            brief_storage=self.brief_storage,
        )

        # Inject hook fakes: counter + observed-state recorder
        self.email_calls: list[dict] = []
        self.scheduler_calls: list[dict] = []
        # The handler observed-state at the moment the hook fires:
        self.observed_storage_at_hook: list[bool] = []

        gate_storage_ref = self.gate_storage

        def fake_email(to_email, draft_token, fallback_at,
                       *, trace_id=None):
            # P10: at hook fire time, the saved state must already be
            # readable from storage (terminal). Record the assertion.
            try:
                state, last_req, last_resp = gate_storage_ref.resume(
                    draft_token,
                )
                self.observed_storage_at_hook.append(state.is_done)
            except Exception:
                self.observed_storage_at_hook.append(False)
            self.email_calls.append({
                "to_email": to_email,
                "draft_token": draft_token,
                "fallback_at": fallback_at,
            })
            return None

        def fake_scheduler(session_token, fire_at_unix, request_id,
                           *, trace_id=None):
            # S7b § 7.4 + § 8.7: scheduler hook signature changed from
            # (draft_token, fallback_at) to (session_token, fire_at_unix,
            # request_id, *, trace_id=None). The fake records under the
            # original `draft_token` / `fallback_at` keys to keep
            # downstream assertions stable; only the input shape moves.
            self.scheduler_calls.append({
                "draft_token": session_token,
                "fallback_at": fire_at_unix,
            })
            return None

        self._orig_email = c3a_endpoint._send_cba_checklist
        self._orig_scheduler = c3a_endpoint._schedule_fallback_invitation
        c3a_endpoint._send_cba_checklist = fake_email
        c3a_endpoint._schedule_fallback_invitation = fake_scheduler

        # Inject c2 runner — the orchestrator we use is constructed
        # inside the handler, so we need to patch _make_gate to provide
        # our fake runner instead.
        self.gap = _make_gap_analysis()
        runner, _calls = _make_runner(self.gap)
        self._orig_make_gate = c3a_endpoint._make_gate

        from buildemup.components.c03a_extreme_case_gate import (
            ExtremeCaseGate,
        )

        def fake_make_gate(c2_runner=None):
            return ExtremeCaseGate(c2_runner=runner)

        c3a_endpoint._make_gate = fake_make_gate

    def tearDown(self):
        c3a_endpoint._send_cba_checklist = self._orig_email
        c3a_endpoint._schedule_fallback_invitation = self._orig_scheduler
        c3a_endpoint._make_gate = self._orig_make_gate
        c3a_endpoint.reset_storages_for_tests(
            gate_storage=None, brief_storage=None,
        )
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _save_brief_to_storage(self) -> str:
        """Save a Brief and return the brief_token."""
        brief = _make_brief()
        token, _expires = self.brief_storage.save(brief.to_dict())
        return token

    def _start_session_to_cba_pause(self) -> tuple[str, str, dict]:
        """Drive a session via /check + /resolve to CBA pause; return
        (session_token, request_id_used, response_dict).
        """
        cba_case = _make_cba_pause_case()
        brief_token = self._save_brief_to_storage()

        # /check
        with _DetectorPatch([(cba_case,)]):
            check_body = json.dumps({
                "brief_token": brief_token,
                "request_id": "req-check-1",
            }).encode("utf-8")
            check_status, check_resp = c3a_endpoint.handle_check(check_body)
        self.assertEqual(check_status, 200)
        self.assertTrue(check_resp["has_blockers"])
        session_token = check_resp["session_token"]

        # /resolve picking the CBA option (option_id 0 is the cba opt)
        head = check_resp["current_case"]
        cba_option_id = next(
            o["option_id"] for o in head["options"]
            if o.get("requires_action") == "EMAIL_CBA_CHECKLIST"
        )
        with _DetectorPatch([(cba_case,)]):
            resolve_body = json.dumps({
                "session_token": session_token,
                "request_id": "req-resolve-1",
                "case_id": head["case_id"],
                "chosen_option_id": cba_option_id,
                "user_acknowledged_at": "2026-05-01T12:00:00Z",
            }).encode("utf-8")
            resolve_status, resolve_resp = c3a_endpoint.handle_resolve(
                resolve_body,
            )
        self.assertEqual(resolve_status, 200)
        return session_token, "req-resolve-1", resolve_resp


class TestHookOrdering(_HookOrderTestBase):
    def test_hook_called_after_save_succeeds(self):
        """P10 — hook is called only after the save succeeds. The
        observed_storage_at_hook list captures whether the saved state
        was already readable + terminal at the moment the hook fired.
        """
        session_token, _req_id, response = self._start_session_to_cba_pause()
        self.assertTrue(response["is_done"])
        self.assertTrue(response["paused"])
        self.assertEqual(
            response["termination_reason"], "CBA_VERIFICATION_PAUSED",
        )
        # Hooks fired exactly once each
        self.assertEqual(len(self.email_calls), 1)
        self.assertEqual(len(self.scheduler_calls), 1)
        # P10: at hook fire time, state was already saved AND terminal
        self.assertEqual(self.observed_storage_at_hook, [True])
        # Hook called with right shape
        self.assertEqual(
            self.email_calls[0]["draft_token"], session_token,
        )

    def test_hook_failure_does_not_corrupt_state(self):
        """P10 rationale — hook raising must not roll back the state.

        Replace email hook with one that raises. State must still be
        saved correctly; response still returned.
        """
        def raising_hook(to_email, draft_token, fallback_at,
                         *, trace_id=None):
            raise RuntimeError("SMTP server unreachable (test)")

        c3a_endpoint._send_cba_checklist = raising_hook

        # Run the same flow — should NOT raise out of the handler
        session_token, _req_id, response = self._start_session_to_cba_pause()
        self.assertTrue(response["is_done"])
        # State persisted despite hook failure
        state, last_req, last_resp = self.gate_storage.resume(session_token)
        self.assertTrue(state.is_done)
        self.assertEqual(last_req, "req-resolve-1")
        self.assertEqual(last_resp, response)

    def test_hook_NOT_recalled_on_idempotency_replay(self):
        """P16 round 2 #12 — duplicate request_id replays cached
        response WITHOUT re-firing the hook.
        """
        session_token, req_id, response_first = (
            self._start_session_to_cba_pause()
        )
        # Verify hook fired exactly once after first call
        self.assertEqual(len(self.email_calls), 1)
        self.assertEqual(len(self.scheduler_calls), 1)

        # Replay: same request_id, same body shape. Detector patch
        # NOT needed — the handler must short-circuit before calling
        # the orchestrator.
        cba_case = _make_cba_pause_case()
        head_dict = response_first  # we'll rebuild request from it
        # Construct same body (case_id is now... the case we just
        # finished is already terminal so the cached response replays
        # regardless of body details, but using the same body matches
        # client behavior).
        body = json.dumps({
            "session_token": session_token,
            "request_id": req_id,
            "case_id": "EC_005",
            "chosen_option_id": "EC_005_OPT_CBA",
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        replay_status, replay_resp = c3a_endpoint.handle_resolve(body)
        self.assertEqual(replay_status, 200)
        # Verbatim cached response (P2)
        self.assertEqual(replay_resp, response_first)
        # P16: hooks NOT re-fired
        self.assertEqual(len(self.email_calls), 1)
        self.assertEqual(len(self.scheduler_calls), 1)


class TestTerminalReplayAdvisory(_HookOrderTestBase):
    """P15 round 2 #7 — terminal-replay advisory field appears on
    SECOND call to a mutating endpoint with a now-terminal token, and
    is NOT present on the first terminal response.
    """

    def test_terminal_replay_session_status_advisory_field(self):
        # Drive to terminal CBA pause
        session_token, req_id, first_response = (
            self._start_session_to_cba_pause()
        )
        # First terminal response has NO session_status field
        self.assertNotIn("session_status", first_response)

        # Second call with a DIFFERENT request_id (so P2 replay does
        # NOT short-circuit; we hit the P3+P15 terminal path instead).
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-resolve-NEW",   # different from req_id
            "case_id": "EC_005",
            "chosen_option_id": "EC_005_OPT_CBA",
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)
        # P15: advisory field present
        self.assertEqual(response.get("session_status"), "terminal_replay")
        # And the rest of the response matches the cached one
        # (apart from the added advisory field)
        for k, v in first_response.items():
            self.assertEqual(response[k], v,
                             f"field {k!r} differs on terminal replay")

    def test_terminal_replay_does_not_re_fire_hooks(self):
        """Belt-and-braces: terminal-replay path also doesn't re-fire
        hooks (independent of P16 idempotency replay).
        """
        session_token, req_id, _first = (
            self._start_session_to_cba_pause()
        )
        self.assertEqual(len(self.email_calls), 1)

        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-resolve-NEW",   # new id → terminal path
            "case_id": "EC_005",
            "chosen_option_id": "EC_005_OPT_CBA",
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        c3a_endpoint.handle_resolve(body)
        # No additional hook fires
        self.assertEqual(len(self.email_calls), 1)
        self.assertEqual(len(self.scheduler_calls), 1)


if __name__ == "__main__":
    unittest.main()
