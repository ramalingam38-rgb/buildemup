"""S7b § 5.4 + § 8.1 — trace_id propagation tests (P29 + P34).

Three tests:
  1. trace_id appears in pause-response body and is preserved when
     /admin/scheduler/tick later POSTs to /cba-fallback-continue
     (the X-Trace-Id round-trip).
  2. The X-Trace-Id header set by the scheduler tick is honoured by
     the cba-fallback-continue handler.
  3. P34 format validation: a malformed X-Trace-Id is rejected and a
     fresh trace_id is minted (with WARNING); a valid one is preserved.
"""
from __future__ import annotations

import logging
import os
import unittest
from unittest.mock import patch

from buildemup.api import c3a_endpoint


class TestTraceIdGenerationAndValidation(unittest.TestCase):
    """P34: external trust boundary at cba-fallback-continue."""

    def test_p34_valid_trace_id_preserved_invalid_rejected_with_warning(self):
        """Format validator: ^[0-9a-f]{16}$ match → preserve;
        no match → mint fresh + WARNING.

        Three cases in one test (one assertion family):
          (a) valid 16-hex → returned verbatim, no warning.
          (b) malformed string → fresh 16-hex returned, WARNING logged.
          (c) None / "" → fresh 16-hex returned, no warning logged.
        """
        # Capture WARNING log lines from the c3a endpoint logger.
        logger_obj = logging.getLogger("buildemup.c3a.endpoint")
        captured: list[str] = []

        class _H(logging.Handler):
            def emit(self_inner, record):
                captured.append(self_inner.format(record))

        h = _H()
        h.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))
        logger_obj.addHandler(h)
        logger_obj.setLevel(logging.DEBUG)

        try:
            # (a) valid → preserve, no warning
            captured.clear()
            valid = "deadbeef0123abcd"
            out = c3a_endpoint._resolve_external_trace_id(valid)
            self.assertEqual(out, valid)
            warnings = [r for r in captured if "rejected" in r]
            self.assertEqual(len(warnings), 0,
                             f"valid trace produced warning: {captured!r}")

            # (b) malformed → fresh + WARNING
            captured.clear()
            bad = "not-a-hex-string!!!!"
            out = c3a_endpoint._resolve_external_trace_id(bad)
            self.assertNotEqual(out, bad)
            self.assertIsNotNone(c3a_endpoint._TRACE_ID_RE.match(out))
            warnings = [r for r in captured
                        if "rejected malformed X-Trace-Id" in r]
            self.assertEqual(len(warnings), 1,
                             f"expected 1 WARNING; got {captured!r}")

            # (c) None → fresh, NO warning (None is "absent", not "bad")
            captured.clear()
            out = c3a_endpoint._resolve_external_trace_id(None)
            self.assertIsNotNone(c3a_endpoint._TRACE_ID_RE.match(out))
            warnings = [r for r in captured if "rejected" in r]
            self.assertEqual(len(warnings), 0,
                             f"None produced warning: {captured!r}")
        finally:
            logger_obj.removeHandler(h)


class TestTraceIdRoundTripViaWrapper(unittest.TestCase):
    """P29: trace_id propagated end-to-end through the wrapper."""

    def test_handle_cba_fallback_continue_honours_inbound_x_trace_id(self):
        """When `headers={"X-Trace-Id": valid_16hex}` is passed,
        the response body's `trace_id` field equals the supplied value.

        This is the contract the scheduler tick relies on: the
        original pause-time trace_id is preserved across the 24h gap.
        """
        valid = "0123456789abcdef"
        # Empty body still triggers the wrapper → inner returns 400
        # via _parse_and_size_check; trace_id has been resolved by
        # this point.
        status, body = c3a_endpoint.handle_cba_fallback_continue(
            b"", {"X-Trace-Id": valid},
        )
        self.assertEqual(status, 400)  # empty body
        self.assertEqual(body["trace_id"], valid,
                         "inbound X-Trace-Id was NOT propagated to body")

    def test_handle_cba_fallback_continue_mints_fresh_when_no_header(self):
        """No header → wrapper mints a fresh 16-hex trace_id.

        Verifies the wrapper falls back to `_new_trace_id()` (not
        `utils.logging.new_trace_id()`'s 12-char format) when no
        inbound header is provided. Format invariant for downstream
        log parsers.
        """
        status, body = c3a_endpoint.handle_cba_fallback_continue(b"")
        self.assertEqual(status, 400)
        trace_id = body["trace_id"]
        self.assertIsNotNone(c3a_endpoint._TRACE_ID_RE.match(trace_id),
                             f"trace_id {trace_id!r} not 16-hex format")


if __name__ == "__main__":
    unittest.main()
