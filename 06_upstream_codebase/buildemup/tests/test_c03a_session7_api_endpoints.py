"""Tests for Component 3a Session 7a — 5 API endpoints.

Covers S7a SPEC v1.0 LOCKED:
  § 8.1 TestCheckEndpoint
  § 8.2 TestResolveEndpoint
  § 8.3 TestAbortEndpoint
  § 8.4 TestCbaVerifiedEndpoint
  § 8.5 TestCbaFallbackEndpoint
  Plus § 8.7 P11 single-flight lock test (lives here because it
        wraps the handler around the lock).

P-invariants exercised:
  P2  request_id idempotency replay
  P3  terminal token → 200 with cached
  P7  is_done normalization + aborted/paused supplementary flags
  P9  1 MB body cap → 400
  P11 single-flight lock serialises concurrent /resolve
  P12 brief→session uniqueness via /check
  P15 terminal-replay advisory field session_status
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
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


def _cba_pause_case():
    cba_opt = _option(
        "EC_005_OPT_CBA",
        requires_action="EMAIL_CBA_CHECKLIST",
    )
    other = _option("EC_005_OPT_OTHER")
    return _case(
        ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED,
        options=(cba_opt, other),
    )


class _EndpointTestBase(unittest.TestCase):
    """Set up isolated storages + injected gate (so detector patches
    work) for handler tests.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gate_storage = GateStateStorage(
            db_path=os.path.join(self.tmpdir, "gate.db"),
        )
        self.brief_storage = BriefStorage(
            db_path=os.path.join(self.tmpdir, "brief.db"),
        )
        c3a_endpoint.reset_storages_for_tests(
            gate_storage=self.gate_storage,
            brief_storage=self.brief_storage,
        )

        self.gap = _make_gap_analysis()
        runner, calls = _make_runner(self.gap)
        self.runner = runner
        self.runner_calls = calls

        from buildemup.components.c03a_extreme_case_gate import (
            ExtremeCaseGate,
        )

        self._orig_make_gate = c3a_endpoint._make_gate

        def fake_make_gate(c2_runner=None):
            return ExtremeCaseGate(c2_runner=runner)

        c3a_endpoint._make_gate = fake_make_gate

        # No-op hooks (default — tests that need to observe them
        # patch _send_cba_checklist directly)
        self._orig_email = c3a_endpoint._send_cba_checklist
        self._orig_scheduler = c3a_endpoint._schedule_fallback_invitation
        c3a_endpoint._send_cba_checklist = lambda *a, **kw: None
        c3a_endpoint._schedule_fallback_invitation = lambda *a, **kw: None

    def tearDown(self):
        c3a_endpoint._make_gate = self._orig_make_gate
        c3a_endpoint._send_cba_checklist = self._orig_email
        c3a_endpoint._schedule_fallback_invitation = self._orig_scheduler
        c3a_endpoint.reset_storages_for_tests(
            gate_storage=None, brief_storage=None,
        )
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _save_brief(self) -> str:
        token, _ = self.brief_storage.save(_make_brief().to_dict())
        return token


# ─────────────────────────────────────────────────────────────────────
# § 5.1 / § 8.1 — /check
# ─────────────────────────────────────────────────────────────────────

class TestCheckEndpoint(_EndpointTestBase):
    def test_check_no_blockers_returns_terminal_success(self):
        brief_token = self._save_brief()
        with _DetectorPatch([()]):  # no extreme cases
            body = json.dumps({
                "brief_token": brief_token,
                "request_id": "req-1",
            }).encode("utf-8")
            status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["ok"])
        self.assertFalse(response["has_blockers"])
        self.assertTrue(response["is_done"])
        self.assertFalse(response["aborted"])
        self.assertFalse(response["paused"])
        self.assertEqual(response["termination_reason"], "SUCCESS")
        self.assertIn("resolved_brief", response)
        self.assertEqual(response["next_step"], "PROCEED_TO_LAYOUT")

    def test_check_with_blockers_returns_first_case(self):
        brief_token = self._save_brief()
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        with _DetectorPatch([(case,)]):
            body = json.dumps({
                "brief_token": brief_token,
                "request_id": "req-1",
            }).encode("utf-8")
            status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["has_blockers"])
        self.assertFalse(response["is_done"])
        self.assertEqual(response["current_case"]["case_id"], "EC_005")
        self.assertGreaterEqual(response["remaining_blocker_count"], 1)
        self.assertEqual(response["next_step"], "USER_DECIDE")

    def test_check_unknown_brief_token_returns_410(self):
        body = json.dumps({
            "brief_token": "does-not-exist-token-xyz",
            "request_id": "req-1",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 410)
        self.assertFalse(response["ok"])

    def test_check_malformed_json_returns_400(self):
        status, response = c3a_endpoint.handle_check(b"{not valid json")
        self.assertEqual(status, 400)

    def test_check_missing_request_id_returns_400(self):
        brief_token = self._save_brief()
        body = json.dumps({"brief_token": brief_token}).encode("utf-8")
        status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 400)
        # Structured errors list per § 6.5
        self.assertEqual(
            [e["field"] for e in response["errors"]],
            ["request_id"],
        )
        self.assertEqual(response["errors"][0]["code"], "missing")

    def test_check_oversize_body_returns_400(self):
        # P9 — body > 1 MB
        brief_token = self._save_brief()
        # Build a body just over 1 MB
        oversized = "x" * (c3a_endpoint.REQUEST_BODY_LIMIT_BYTES + 100)
        body = json.dumps({
            "brief_token": brief_token,
            "request_id": "req-1",
            "padding": oversized,
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 400)
        self.assertEqual(response["errors"][0]["code"], "too_large")

    def test_check_idempotency_same_brief_token_and_request_id(self):
        """P12 — second /check with same (brief_token, request_id)
        returns the SAME session_token (not a new session)."""
        brief_token = self._save_brief()
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        with _DetectorPatch([(case,), (case,)]):  # detector called twice
            body = json.dumps({
                "brief_token": brief_token,
                "request_id": "req-shared",
            }).encode("utf-8")
            _s1, r1 = c3a_endpoint.handle_check(body)
            _s2, r2 = c3a_endpoint.handle_check(body)
        self.assertEqual(r1["session_token"], r2["session_token"])


# ─────────────────────────────────────────────────────────────────────
# § 5.2 / § 8.2 — /resolve  (most complex)
# ─────────────────────────────────────────────────────────────────────

class TestResolveEndpoint(_EndpointTestBase):
    def _start(self, cases_list) -> tuple[str, dict]:
        """Helper: drive /check, return (session_token, response)."""
        brief_token = self._save_brief()
        with _DetectorPatch(cases_list):
            body = json.dumps({
                "brief_token": brief_token,
                "request_id": "req-check",
            }).encode("utf-8")
            status, response = c3a_endpoint.handle_check(body)
        self.assertEqual(status, 200)
        return response["session_token"], response

    def test_resolve_terminates_with_success(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,), ()])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-resolve-1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([()]):  # post-decision: empty
            status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["is_done"])      # P7
        self.assertFalse(response["aborted"])     # P7
        self.assertFalse(response["paused"])      # P7
        self.assertEqual(response["termination_reason"], "SUCCESS")
        self.assertIn("resolved_brief", response)
        self.assertEqual(response["next_step"], "PROCEED_TO_LAYOUT")

    def test_resolve_continues_to_next_case(self):
        case_a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case_b = _case(ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED)
        session_token, check_resp = self._start([(case_a, case_b)])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([(case_b,)]):
            status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)
        self.assertFalse(response["is_done"])
        self.assertIn("current_case", response)
        self.assertEqual(response["next_step"], "USER_DECIDE")

    def test_resolve_pauses_for_cba_verification(self):
        """P10 — CBA pause path fires hooks AFTER save."""
        cba_case = _cba_pause_case()
        session_token, check_resp = self._start([(cba_case,)])
        head = check_resp["current_case"]
        cba_option_id = next(
            o["option_id"] for o in head["options"]
            if o.get("requires_action") == "EMAIL_CBA_CHECKLIST"
        )
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": cba_option_id,
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([(cba_case,)]):
            status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["is_done"])      # P7
        self.assertFalse(response["aborted"])
        self.assertTrue(response["paused"])       # P7
        self.assertEqual(
            response["termination_reason"], "CBA_VERIFICATION_PAUSED",
        )
        self.assertEqual(
            response["pause_reason"], "AWAITING_CBA_VERIFICATION",
        )
        self.assertIn("fallback_at", response)

    def test_resolve_unknown_session_token_returns_410(self):
        body = json.dumps({
            "session_token": "unknown-token-xyz1234567",
            "request_id": "req-1",
            "case_id": "EC_005",
            "chosen_option_id": "OPT_A",
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        status, _r = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 410)

    def test_resolve_terminal_token_returns_200_with_cached(self):
        """P3 — terminal token returns HTTP 200 with cached response.
        v0.1 had 410 for this; semantics flipped in v0.2.
        """
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,), ()])
        head = check_resp["current_case"]
        # First /resolve → terminal
        body1 = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([()]):
            status1, response1 = c3a_endpoint.handle_resolve(body1)
        self.assertEqual(status1, 200)
        self.assertTrue(response1["is_done"])
        # Second /resolve with DIFFERENT request_id → P3 + P15
        body2 = json.dumps({
            "session_token": session_token,
            "request_id": "req-r-NEW",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-02T08:00:00Z",
        }).encode("utf-8")
        status2, response2 = c3a_endpoint.handle_resolve(body2)
        self.assertEqual(status2, 200)   # NOT 410
        self.assertTrue(response2["is_done"])
        # P15: advisory field added
        self.assertEqual(
            response2.get("session_status"), "terminal_replay",
        )

    def test_resolve_invalid_option_id_returns_400(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,)])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": "NONEXISTENT_OPTION_ID",
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        status, _r = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 400)

    def test_resolve_missing_user_acknowledged_at_returns_400(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,)])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            # NO user_acknowledged_at
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 400)
        self.assertIn(
            "user_acknowledged_at",
            [e["field"] for e in response["errors"]],
        )

    def test_resolve_missing_request_id_returns_400(self):
        """P2 — request_id is required (server does not auto-generate)."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,)])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            # no request_id
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 400)
        self.assertIn(
            "request_id",
            [e["field"] for e in response["errors"]],
        )

    def test_resolve_duplicate_request_id_replays_cached_response(self):
        """P2 — duplicate request_id replays the cached response verbatim,
        WITHOUT calling the orchestrator a second time."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,), (case,)])
        # Note: detect_seq will only be consumed if orchestrator runs.
        # We arrange for ONE detect_seq element so a re-run would fail.
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-shared",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([(case,)]):  # ONE detection (post-decision)
            status1, response1 = c3a_endpoint.handle_resolve(body)
            # Replay — NO _DetectorPatch needed; orchestrator MUST not
            # be called.
            status2, response2 = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(response1, response2)

    def test_resolve_oversize_body_returns_400(self):
        body = b"x" * (c3a_endpoint.REQUEST_BODY_LIMIT_BYTES + 100)
        status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 400)
        self.assertEqual(response["errors"][0]["code"], "too_large")

    # ─── D-067 round 3 — code review item #4: strict ISO 8601 ────────
    # _validate_iso8601 rejects malformed timestamps at the API trust
    # boundary (P18), preventing silent propagation of bad data into
    # _add_24h_iso and stored decisions_so_far.

    def test_resolve_malformed_iso_timestamp_returns_400(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,)])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "not-a-real-timestamp",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 400)
        err = response["errors"][0]
        self.assertEqual(err["field"], "user_acknowledged_at")
        self.assertEqual(err["code"], "format")

    def test_resolve_iso_with_z_suffix_accepted(self):
        """The 'YYYY-MM-DDTHH:MM:SSZ' form is the canonical example
        in spec § 5.2 + S6 fixtures; must be accepted."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,), ()])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T12:00:00Z",
        }).encode("utf-8")
        with _DetectorPatch([()]):
            status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)

    def test_resolve_iso_with_offset_form_accepted(self):
        """ISO 8601 also allows '+HH:MM' offset form."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        session_token, check_resp = self._start([(case,), ()])
        head = check_resp["current_case"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-r1",
            "case_id": head["case_id"],
            "chosen_option_id": head["options"][0]["option_id"],
            "user_acknowledged_at": "2026-05-01T17:30:00+05:30",
        }).encode("utf-8")
        with _DetectorPatch([()]):
            status, response = c3a_endpoint.handle_resolve(body)
        self.assertEqual(status, 200)


# ─────────────────────────────────────────────────────────────────────
# § 5.3 / § 8.3 — /abort
# ─────────────────────────────────────────────────────────────────────

class TestAbortEndpoint(_EndpointTestBase):
    def test_abort_records_decision_log(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case,)]):
            check_status, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
        session_token = check_resp["session_token"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-abort-1",
            "reason": "I want to think about this",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_abort(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["is_done"])      # P7
        self.assertTrue(response["aborted"])      # P7
        self.assertFalse(response["paused"])      # P7
        self.assertTrue(response["saved_as_draft"])
        self.assertEqual(
            response["termination_reason"], "USER_ABORTED",
        )
        self.assertIn("decision_log", response)

    def test_abort_already_terminal_returns_200_with_cached(self):
        """P3 — abort on terminal session returns 200 with cached
        response (was 410 in v0.1; flipped in v0.2)."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case,), ()]):
            check_status, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
            session_token = check_resp["session_token"]
            head = check_resp["current_case"]
            # First take it to terminal SUCCESS via /resolve
            c3a_endpoint.handle_resolve(
                json.dumps({
                    "session_token": session_token,
                    "request_id": "req-r-succ",
                    "case_id": head["case_id"],
                    "chosen_option_id": head["options"][0]["option_id"],
                    "user_acknowledged_at": "2026-05-01T12:00:00Z",
                }).encode("utf-8")
            )
        # Now /abort on a terminal session
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-abort-NEW",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_abort(body)
        self.assertEqual(status, 200)             # NOT 410
        self.assertTrue(response["is_done"])
        # P15: advisory field
        self.assertEqual(
            response.get("session_status"), "terminal_replay",
        )

    def test_abort_duplicate_request_id_replays_cached_response(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case,)]):
            check_status, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
        session_token = check_resp["session_token"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-abort-shared",
        }).encode("utf-8")
        status1, r1 = c3a_endpoint.handle_abort(body)
        status2, r2 = c3a_endpoint.handle_abort(body)
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(r1, r2)


# ─────────────────────────────────────────────────────────────────────
# § 5.4 / § 8.4 — /cba-verified
# ─────────────────────────────────────────────────────────────────────

class TestCbaVerifiedEndpoint(_EndpointTestBase):
    def _drive_to_cba_pause(self) -> str:
        cba_case = _cba_pause_case()
        brief_token = self._save_brief()
        with _DetectorPatch([(cba_case,), (cba_case,)]):
            _s, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
            session_token = check_resp["session_token"]
            head = check_resp["current_case"]
            cba_option_id = next(
                o["option_id"] for o in head["options"]
                if o.get("requires_action") == "EMAIL_CBA_CHECKLIST"
            )
            c3a_endpoint.handle_resolve(json.dumps({
                "session_token": session_token,
                "request_id": "req-r-pause",
                "case_id": head["case_id"],
                "chosen_option_id": cba_option_id,
                "user_acknowledged_at": "2026-05-01T12:00:00Z",
            }).encode("utf-8"))
        return session_token

    def test_cba_verified_cba_confirmed_returns_continuous_restart(self):
        token = self._drive_to_cba_pause()
        body = json.dumps({
            "session_token": token,
            "request_id": "req-cba-1",
            "verification_result": "CBA_CONFIRMED",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_cba_verified(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["is_done"])
        self.assertTrue(response["brief_restarting"])
        self.assertEqual(
            response["next_step"],
            "RESTART_BRIEF_WITH_PLOT_TYPE_CONTINUOUS",
        )

    def test_cba_verified_not_cba_returns_original_proceed(self):
        token = self._drive_to_cba_pause()
        body = json.dumps({
            "session_token": token,
            "request_id": "req-cba-1",
            "verification_result": "NOT_CBA",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_cba_verified(body)
        self.assertEqual(status, 200)
        self.assertEqual(
            response["next_step"], "PROCEED_WITH_ORIGINAL_BRIEF",
        )

    def test_cba_verified_still_unsure_returns_manual_followup(self):
        token = self._drive_to_cba_pause()
        body = json.dumps({
            "session_token": token,
            "request_id": "req-cba-1",
            "verification_result": "STILL_UNSURE",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_cba_verified(body)
        self.assertEqual(status, 200)
        self.assertEqual(response["next_step"], "MANUAL_FOLLOWUP")

    def test_cba_verified_unknown_result_returns_400(self):
        token = self._drive_to_cba_pause()
        body = json.dumps({
            "session_token": token,
            "request_id": "req-cba-1",
            "verification_result": "MAYBE",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_cba_verified(body)
        self.assertEqual(status, 400)

    def test_cba_verified_on_non_paused_mid_flow_returns_409(self):
        """§ 5.4 lifecycle: non-terminal mid-flow → 409 CONFLICT."""
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case,)]):
            _s, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
        session_token = check_resp["session_token"]
        # NOT terminal — call /cba-verified directly
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-cba-1",
            "verification_result": "CBA_CONFIRMED",
        }).encode("utf-8")
        status, _r = c3a_endpoint.handle_cba_verified(body)
        self.assertEqual(status, 409)


# ─────────────────────────────────────────────────────────────────────
# § 5.5 / § 8.5 — /cba-fallback-continue
# ─────────────────────────────────────────────────────────────────────

class TestCbaFallbackEndpoint(_EndpointTestBase):
    def _drive_to_cba_pause(self) -> str:
        cba_case = _cba_pause_case()
        brief_token = self._save_brief()
        with _DetectorPatch([(cba_case,), (cba_case,)]):
            _s, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
            session_token = check_resp["session_token"]
            head = check_resp["current_case"]
            cba_option_id = next(
                o["option_id"] for o in head["options"]
                if o.get("requires_action") == "EMAIL_CBA_CHECKLIST"
            )
            c3a_endpoint.handle_resolve(json.dumps({
                "session_token": session_token,
                "request_id": "req-r-pause",
                "case_id": head["case_id"],
                "chosen_option_id": cba_option_id,
                "user_acknowledged_at": "2026-05-01T12:00:00Z",
            }).encode("utf-8"))
        return session_token

    def test_cba_fallback_resumes_with_detached_assumption(self):
        token = self._drive_to_cba_pause()
        body = json.dumps({
            "session_token": token,
            "request_id": "req-fb-1",
        }).encode("utf-8")
        status, response = c3a_endpoint.handle_cba_fallback_continue(body)
        self.assertEqual(status, 200)
        self.assertTrue(response["is_done"])
        self.assertTrue(response["brief_resuming"])
        self.assertEqual(response["assumed_plot_type"], "DETACHED")

    def test_cba_fallback_on_non_paused_mid_flow_returns_409(self):
        case = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case,)]):
            _s, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
        session_token = check_resp["session_token"]
        body = json.dumps({
            "session_token": session_token,
            "request_id": "req-fb-1",
        }).encode("utf-8")
        status, _r = c3a_endpoint.handle_cba_fallback_continue(body)
        self.assertEqual(status, 409)


# ─────────────────────────────────────────────────────────────────────
# P11 — Single-flight lock (§ 8.7 cross-cutting test)
# ─────────────────────────────────────────────────────────────────────

class TestSingleFlightLock(_EndpointTestBase):
    """P11 round 2 #15 — two threads call /resolve concurrently with
    different request_ids targeting the same case. The lock serialises
    them: exactly one mutates state (200), the other observes the
    post-mutation state and returns a deterministic 400 because its
    case_id is now stale (the head case has advanced).

    Without the lock, both could have advanced iteration_count
    simultaneously, producing inconsistent state (lost-update). With
    the lock, the final state shows iteration_count == 1 (one
    resolve), confirming the second worker did NOT silently commit a
    second mutation.
    """

    def test_single_flight_lock_serialises_concurrent_resolves(self):
        case_a = _case(ExtremeCaseId.EC_005_GROUND_COVERAGE_EXCEEDED)
        case_b = _case(ExtremeCaseId.EC_007_STILT_MANDATE_VIOLATED)
        brief_token = self._save_brief()
        with _DetectorPatch([(case_a, case_b)]):
            _s, check_resp = c3a_endpoint.handle_check(
                json.dumps({
                    "brief_token": brief_token,
                    "request_id": "req-c",
                }).encode("utf-8")
            )
        session_token = check_resp["session_token"]
        head = check_resp["current_case"]
        from buildemup.components.c03a import detector as _det_mod
        from unittest.mock import patch

        # After the winning resolve, the head case advances to case_b
        # (EC_007). The losing thread will then see that as the
        # current case and reject its stale (EC_005) case_id.
        seq = [(case_b,), ()]
        seq_lock = threading.Lock()

        def fake_detect(gap, brief):
            with seq_lock:
                if seq:
                    return seq.pop(0)
                return ()

        responses: list = []
        worker_errors: list = []

        def worker(req_id: str):
            try:
                body = json.dumps({
                    "session_token": session_token,
                    "request_id": req_id,
                    "case_id": head["case_id"],   # both target case_a
                    "chosen_option_id": head["options"][0]["option_id"],
                    "user_acknowledged_at": "2026-05-01T12:00:00Z",
                }).encode("utf-8")
                with patch.object(
                    _det_mod.ExtremeCaseDetector, "detect",
                    staticmethod(fake_detect),
                ):
                    status, response = c3a_endpoint.handle_resolve(body)
                responses.append((req_id, status, response))
            except Exception as e:
                worker_errors.append((req_id, type(e).__name__, str(e)))

        t1 = threading.Thread(target=worker, args=("req-A",))
        t2 = threading.Thread(target=worker, args=("req-B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(worker_errors, [],
                         f"workers raised: {worker_errors!r}")
        self.assertEqual(len(responses), 2)

        statuses = sorted(r[1] for r in responses)
        # Lock proof: exactly one 200 (the winner) and one 400 (the
        # loser, with stale case_id after observing post-mutation
        # state). NEVER two 200s, which would indicate concurrent
        # state mutation (lost update).
        self.assertEqual(
            statuses, [200, 400],
            f"expected one winner + one stale-rejected; got {statuses}",
        )
        # The 400 was due to case_id mismatch (proving the loser saw
        # post-A state — i.e., serialized execution).
        loser = next(r for r in responses if r[1] == 400)
        self.assertEqual(
            loser[2]["errors"][0]["code"], "invalid",
        )
        self.assertIn(
            "case_id mismatch",
            loser[2]["errors"][0]["message"],
        )

        # Final state: iteration_count == 1 (only ONE mutation
        # committed; the lock prevented lost-update).
        final_state, _last_req, _last_resp = self.gate_storage.resume(
            session_token,
        )
        self.assertEqual(final_state.iteration_count, 1)


if __name__ == "__main__":
    unittest.main()
