"""S7b § 7.2 + § 8.1 + § 8.6 — Resend email hook tests.

Four tests, all HTTP-mocked via `unittest.mock.patch` on
`urllib.request.urlopen`. Per § 7.4 contract, the hook MUST NOT
raise; it logs and returns None on every failure mode. Tests verify:

  1. Successful POST → no log error, request constructed correctly
     (Authorization header, X-Trace-Id, JSON body shape).
  2. Missing RESEND_API_KEY → logs WARNING, returns without HTTP call.
  3. URLError (network failure) → swallowed; returns None.
  4. Non-2xx response → swallowed; returns None.
"""
from __future__ import annotations

import json
import logging
import os
import unittest
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import MagicMock, patch

from buildemup.api import c3a_email_hook


class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[tuple[str, str]] = []
        self.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))

    def emit(self, record):
        self.records.append((record.levelname, self.format(record)))


def _wire():
    h = _CapturingHandler()
    h.setLevel(logging.DEBUG)
    lg = logging.getLogger("buildemup.c3a.email_hook")
    lg.addHandler(h)
    lg.setLevel(logging.DEBUG)
    return h, lg


def _unwire(h, lg):
    lg.removeHandler(h)


class _FakeResp:
    """Minimal urlopen response stand-in."""
    def __init__(self, status: int = 200, body: bytes = b""):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestResendEmailHook(unittest.TestCase):
    """Production wiring against the Resend transactional API."""

    def setUp(self):
        self._snapshot = {
            k: os.environ.get(k) for k in (
                "RESEND_API_KEY", "RESEND_FROM",
            )
        }
        self.handler, self.logger = _wire()

    def tearDown(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _unwire(self.handler, self.logger)

    def _request_built_by_hook(self, urlopen_mock):
        """Pull the urllib Request that was passed to urlopen."""
        self.assertEqual(urlopen_mock.call_count, 1)
        req = urlopen_mock.call_args[0][0]
        return req

    def test_successful_post_constructs_correct_request(self):
        """Happy path: 200 from Resend → INFO log, no error.

        Verifies the Authorization Bearer header is present, the JSON
        body has `from`/`to`/`subject`/`html`, and the X-Trace-Id
        custom header (in the JSON `headers` field per Resend's API)
        carries the supplied trace_id.
        """
        os.environ["RESEND_API_KEY"] = "re_test_apikey_12345"
        with patch.object(
            urllib.request, "urlopen", return_value=_FakeResp(status=200),
        ) as mock_open:
            c3a_email_hook.send_cba_checklist(
                "user@example.com", "tok_abcdef1234", "2026-01-02T00:00:00Z",
                trace_id="0123456789abcdef",
            )

        req = self._request_built_by_hook(mock_open)
        # Authorization header is in the urllib Request
        self.assertEqual(req.headers["Authorization"],
                         "Bearer re_test_apikey_12345")
        self.assertEqual(req.headers["Content-type"],
                         "application/json")
        # JSON body shape
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["to"], ["user@example.com"])
        self.assertIn("subject", body)
        self.assertIn("html", body)
        # trace_id propagated as Resend custom-header field
        self.assertEqual(body["headers"]["X-Trace-Id"], "0123456789abcdef")
        # Success log line
        info_lines = [r for lvl, r in self.handler.records if lvl == "INFO"]
        self.assertTrue(any("send_cba_checklist: ok" in l for l in info_lines))
        # No WARNING / ERROR
        bad = [r for lvl, r in self.handler.records
               if lvl in ("WARNING", "ERROR")]
        self.assertEqual(bad, [],
                         f"unexpected non-success log lines: {bad!r}")

    def test_missing_resend_api_key_logs_warning_no_http_call(self):
        """No API key → WARNING log; urlopen NOT called.

        The scheduler 24h fallback (P21) is the reliability layer, so
        a missing key shouldn't block the user-facing response. We
        log loudly so operators notice.
        """
        os.environ.pop("RESEND_API_KEY", None)
        with patch.object(urllib.request, "urlopen") as mock_open:
            c3a_email_hook.send_cba_checklist(
                "u@example.com", "tok_1234", "iso", trace_id="abc",
            )

        # No HTTP call
        mock_open.assert_not_called()
        # WARNING log line about missing key
        warn_lines = [r for lvl, r in self.handler.records
                      if lvl == "WARNING"]
        self.assertTrue(
            any("RESEND_API_KEY not set" in l for l in warn_lines),
            f"expected RESEND_API_KEY warning; got {warn_lines!r}",
        )

    def test_urlerror_swallowed_does_not_raise(self):
        """Network failure → URLError caught; function returns None."""
        os.environ["RESEND_API_KEY"] = "re_test_apikey_12345"
        with patch.object(
            urllib.request, "urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            # Must NOT raise — § 7.4 contract
            result = c3a_email_hook.send_cba_checklist(
                "u@example.com", "tok_1234", "iso", trace_id="abc",
            )
        self.assertIsNone(result)
        # WARNING with the network failure
        warn_lines = [r for lvl, r in self.handler.records
                      if lvl == "WARNING"]
        self.assertTrue(
            any("network failure" in l for l in warn_lines),
            f"expected network-failure warning; got {warn_lines!r}",
        )

    def test_non_2xx_response_swallowed_does_not_raise(self):
        """Resend 4xx/5xx → log WARNING, return None.

        Resend's API can return 422 for malformed payloads, 429 for
        rate limits, etc. The hook treats all non-2xx the same way:
        log and move on. Scheduler fallback covers reliability.
        """
        os.environ["RESEND_API_KEY"] = "re_test_apikey_12345"
        with patch.object(
            urllib.request, "urlopen", return_value=_FakeResp(status=422),
        ):
            result = c3a_email_hook.send_cba_checklist(
                "u@example.com", "tok_1234", "iso", trace_id="abc",
            )
        self.assertIsNone(result)
        warn_lines = [r for lvl, r in self.handler.records
                      if lvl == "WARNING"]
        self.assertTrue(
            any("non-2xx response" in l for l in warn_lines),
            f"expected non-2xx warning; got {warn_lines!r}",
        )


if __name__ == "__main__":
    unittest.main()
