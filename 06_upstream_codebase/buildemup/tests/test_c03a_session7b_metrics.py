"""S7b § 5.2 + § 8.1 — Instrumentation metrics tests (P22 + P30).

Five tests: each c3a handler emits one structured-log metric line per
invocation with the closed cardinality field set; metric emission
itself never raises (P22); error_class mapping follows the closed
vocabulary (P30).
"""
from __future__ import annotations

import json
import logging
import os
import unittest

from buildemup.api import c3a_endpoint


class _MetricCapture(logging.Handler):
    """Captures `c3a.endpoint` JSON metric lines into a list of dicts."""

    def __init__(self):
        super().__init__()
        self.metrics: list[dict] = []
        self.unmapped: list[dict] = []
        self.raw: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        self.raw.append(msg)
        # Metric lines are JSON with msg=c3a.endpoint or
        # msg=c3a.endpoint.unmapped_code.
        try:
            doc = json.loads(msg)
            if doc.get("msg") == "c3a.endpoint":
                self.metrics.append(doc)
            elif doc.get("msg") == "c3a.endpoint.unmapped_code":
                self.unmapped.append(doc)
        except (json.JSONDecodeError, AttributeError):
            pass  # non-JSON lines (e.g. plain hook errors)


def _wire_capture():
    cap = _MetricCapture()
    logger_obj = logging.getLogger("buildemup.c3a.endpoint")
    logger_obj.addHandler(cap)
    logger_obj.setLevel(logging.DEBUG)
    return cap, logger_obj


def _unwire(cap, logger_obj):
    logger_obj.removeHandler(cap)


class TestMetricEmissionAllHandlers(unittest.TestCase):
    """One INFO line per handler invocation; closed field set (P30)."""

    _EXPECTED_FIELDS = {
        "msg", "handler", "status", "duration_ms",
        "trace_id", "error_class",
    }

    def _assert_metric_shape(self, metric: dict, expected_handler: str):
        # Field set is exactly the closed P30 vocabulary
        self.assertEqual(set(metric.keys()), self._EXPECTED_FIELDS,
                         f"metric field drift: {metric.keys()}")
        # No PII / unbounded-cardinality fields
        for forbidden in ("session_token", "brief_token", "request_id",
                          "email", "user_email"):
            self.assertNotIn(forbidden, metric,
                             f"forbidden field {forbidden} in metric")
        self.assertEqual(metric["msg"], "c3a.endpoint")
        self.assertEqual(metric["handler"], expected_handler)
        self.assertIsInstance(metric["status"], int)
        self.assertIsInstance(metric["duration_ms"], int)
        self.assertGreaterEqual(metric["duration_ms"], 0)
        self.assertIsInstance(metric["trace_id"], str)
        self.assertIsNotNone(
            c3a_endpoint._TRACE_ID_RE.match(metric["trace_id"]),
        )

    def test_handle_check_emits_one_metric_with_correct_handler_name(self):
        """handle_check → 1 metric line with handler='check'."""
        cap, lg = _wire_capture()
        try:
            cap.metrics.clear()
            c3a_endpoint.handle_check(b"")  # 400 — empty body
            self.assertEqual(len(cap.metrics), 1,
                             f"expected 1 metric; got {cap.metrics!r}")
            self._assert_metric_shape(cap.metrics[0], "check")
            self.assertEqual(cap.metrics[0]["status"], 400)
        finally:
            _unwire(cap, lg)

    def test_handle_resolve_emits_one_metric_with_correct_handler_name(self):
        """handle_resolve → 1 metric line with handler='resolve'."""
        cap, lg = _wire_capture()
        try:
            cap.metrics.clear()
            c3a_endpoint.handle_resolve(b"")  # 400 — empty body
            self.assertEqual(len(cap.metrics), 1)
            self._assert_metric_shape(cap.metrics[0], "resolve")
        finally:
            _unwire(cap, lg)

    def test_metric_emission_is_best_effort_p22(self):
        """When the metric emit itself fails, the handler still returns.

        Patch the `_emit_handler_metric` to raise. Handler must still
        complete its return path without propagating the exception.
        This is P22 (instrumentation never raises out of handler).

        We verify this by patching `logger.info` to raise, then
        confirming the response returns normally. The wrapper's emit
        path is wrapped in try/except.
        """
        from unittest.mock import patch

        # Monkey-patch the LOGGER.info inside c3a_endpoint to raise
        # ONLY when the c3a.endpoint metric is being emitted (not for
        # general logger.info noise).
        original_info = c3a_endpoint.logger.info

        def _info_explodes(msg, *args, **kwargs):
            if isinstance(msg, str) and '"msg": "c3a.endpoint"' in msg:
                raise RuntimeError("metric emit failure for test")
            return original_info(msg, *args, **kwargs)

        with patch.object(c3a_endpoint.logger, "info",
                          side_effect=_info_explodes):
            # Should NOT raise — wrapper catches its own logger errors
            status, body = c3a_endpoint.handle_check(b"")
        # Handler still produced its normal 400
        self.assertEqual(status, 400)
        self.assertIn("trace_id", body)

    def test_classify_error_p30_closed_vocabulary(self):
        """All known codes map to one of the 7 closed `error_class` values.

        Closed set: ok, validation, unknown_token, lifecycle_violation,
        storage_busy, schema_version, internal.
        """
        valid_classes = frozenset({
            "ok", "validation", "unknown_token", "lifecycle_violation",
            "storage_busy", "schema_version", "internal",
        })
        # All mapped codes
        for code in c3a_endpoint._ERROR_CLASS_BY_CODE:
            cls = c3a_endpoint._classify_error(code, "trace_x", "test")
            self.assertIn(cls, valid_classes,
                          f"code {code!r} mapped to non-closed {cls!r}")
        # None → ok
        self.assertEqual(
            c3a_endpoint._classify_error(None, "t", "test"), "ok",
        )
        # Unmapped → internal
        self.assertEqual(
            c3a_endpoint._classify_error(
                "never_seen_xyz", "t", "test",
            ),
            "internal",
        )

    def test_unmapped_code_emits_separate_warning_with_raw_code(self):
        """P30: unmapped → metric stays 'internal'; raw code goes into a
        SEPARATE WARNING line so cardinality is bounded.

        Two-log-line invariant: one INFO metric (low cardinality) +
        one WARNING with the raw code. Routers can sample the metric
        and keep the WARNING.
        """
        cap, lg = _wire_capture()
        try:
            cap.metrics.clear()
            cap.unmapped.clear()
            # Direct call to the classifier — exercises the unmapped path
            cls = c3a_endpoint._classify_error(
                "totally_made_up_code", "trace_xyz", "test_handler",
            )
            self.assertEqual(cls, "internal")
            # Exactly one WARNING line containing the raw code
            self.assertEqual(len(cap.unmapped), 1,
                             f"expected 1 unmapped warning; got {cap.unmapped!r}")
            warning = cap.unmapped[0]
            self.assertEqual(warning["raw_code"], "totally_made_up_code")
            self.assertEqual(warning["handler"], "test_handler")
            self.assertEqual(warning["trace_id"], "trace_xyz")
        finally:
            _unwire(cap, lg)


if __name__ == "__main__":
    unittest.main()
